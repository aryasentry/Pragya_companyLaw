"""Batch ingestion of all raw documents into database"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from folder_analyzer import scan_raw_directory, DocumentMetadata, get_statistics
from pdf_parser import parse_document
from ingestion_service_simple import create_parent_chunk_simple, update_chunk_text_simple
from chunking_engine_simple import hierarchical_chunk

class IngestionStats:
    """Track ingestion progress (thread-safe)"""
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.failed_files = []
        self.start_time = datetime.now()
        self.lock = Lock()  # Thread safety
    
    def record_success(self):
        with self.lock:
            self.success += 1
    
    def record_failure(self, file_path: str, error: str):
        with self.lock:
            self.failed += 1
            self.failed_files.append({'file': file_path, 'error': error})
    
    def record_skip(self):
        with self.lock:
            self.skipped += 1
    
    def get_summary(self) -> Dict:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            'total_documents': self.total,
            'successful': self.success,
            'failed': self.failed,
            'skipped': self.skipped,
            'elapsed_seconds': elapsed,
            'docs_per_second': self.success / elapsed if elapsed > 0 else 0,
            'failed_files': self.failed_files
        }

def ingest_single_document(metadata: DocumentMetadata, stats: IngestionStats, pdf_counters: Dict[str, int], pdf_lock: Lock) -> bool:
    """
    Ingest a single document into database (thread-safe).
    
    Args:
        metadata: Document metadata
        stats: Stats tracker (thread-safe)
        pdf_counters: Dictionary to track PDF numbers per section+type
        pdf_lock: Lock for pdf_counters access
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse document
        parsed = parse_document(metadata.file_path)
        
        if not parsed['text']:
            print(f"  ⚠ No text extracted from {Path(metadata.file_path).name}")
            stats.record_skip()
            return False
        
        # For PDFs, add a counter to handle multiple files (thread-safe)
        file_ext = metadata.file_type
        if file_ext == 'pdf':
            counter_key = f"{metadata.section_number or 'none'}_{metadata.document_type}"
            with pdf_lock:
                pdf_counters[counter_key] = pdf_counters.get(counter_key, 0) + 1
                file_ext = f"pdf{pdf_counters[counter_key]}"
        
        # Normalize file path (use forward slashes for cross-platform compatibility)
        normalized_path = metadata.file_path.replace('\\', '/')
        
        # Create parent chunk with minimal metadata
        parent_chunk_id = create_parent_chunk_simple(
            document_type=metadata.document_type,
            title=f"Section {metadata.section_number} - {metadata.document_type}" if metadata.section_number else f"{metadata.document_type.title()} Document",
            section_number=metadata.section_number,
            compliance_area=None,  # We don't have this from folder structure
            citation=f"Source: {metadata.file_path.replace(chr(92), '/')}",  # Use forward slashes
            file_ext=file_ext  # Add file extension/number to avoid duplicates
        )
        
        # Update parent with full text
        update_chunk_text_simple(
            chunk_id=parent_chunk_id,
            full_text=parsed['text'],
            citation=f"Source: {metadata.file_path.replace(chr(92), '/')}"  # Use forward slashes
        )
        
        # Create child chunks with hierarchical chunking
        child_chunks = hierarchical_chunk(
            parent_chunk_id=parent_chunk_id,
            text=parsed['text'],
            max_chars=1000,
            overlap_chars=100
        )
        
        print(f"  ✓ {Path(metadata.file_path).name}: Parent + {len(child_chunks)} children")
        stats.record_success()
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"  ✗ Error ingesting {Path(metadata.file_path).name}: {error_msg}")
        stats.record_failure(metadata.file_path, error_msg)
        return False

def batch_ingest(
    raw_dir: str,
    limit_sections: Optional[List[str]] = None,
    limit_count: Optional[int] = None,
    save_stats: bool = True,
    max_workers: int = 4
) -> IngestionStats:
    """
    Batch ingest documents from raw directory with parallel processing.
    
    Args:
        raw_dir: Root directory to scan
        limit_sections: Only process these sections (e.g., ['001', '002'])
        limit_count: Maximum number of documents to process
        save_stats: Save statistics to JSON file
        max_workers: Number of parallel workers (default: 4)
        
    Returns:
        IngestionStats object
    """
    print("=" * 60)
    print("BATCH DOCUMENT INGESTION")
    print("=" * 60)
    
    # Scan directory
    print(f"\nScanning {raw_dir}...")
    all_documents = scan_raw_directory(raw_dir)
    
    # Filter by sections if specified
    if limit_sections:
        all_documents = [
            d for d in all_documents 
            if d.section_number in limit_sections
        ]
        print(f"Filtered to sections: {', '.join(limit_sections)}")
    
    # Apply count limit if specified
    if limit_count:
        all_documents = all_documents[:limit_count]
        print(f"Limited to first {limit_count} documents")
    
    stats = IngestionStats()
    stats.total = len(all_documents)
    
    # Show initial statistics
    doc_stats = get_statistics(all_documents)
    print(f"\nDocuments to process: {stats.total}")
    print(f"  Binding: {doc_stats['binding_count']}")
    print(f"  PDFs: {doc_stats['by_file_format'].get('pdf', 0)}")
    print(f"  TXTs: {doc_stats['by_file_format'].get('txt', 0)}")
    print(f"  HTMLs: {doc_stats['by_file_format'].get('html', 0)}")
    print()
    
    # Process documents with progress bar and parallel workers
    print(f"\nProcessing documents with {max_workers} parallel workers...")
    pdf_counters = {}  # Track PDF numbers per section+type
    pdf_lock = Lock()  # Lock for pdf_counters
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(ingest_single_document, doc, stats, pdf_counters, pdf_lock): doc 
            for doc in all_documents
        }
        
        # Process completed tasks with progress bar
        for future in tqdm(as_completed(futures), total=len(futures), desc="Ingesting"):
            try:
                future.result()
            except Exception as e:
                doc = futures[future]
                print(f"  ✗ Unexpected error for {Path(doc.file_path).name}: {e}")
                stats.record_failure(doc.file_path, str(e))
    
    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    
    summary = stats.get_summary()
    print(f"\nTotal documents: {summary['total_documents']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Time: {summary['elapsed_seconds']:.2f} seconds")
    print(f"Rate: {summary['docs_per_second']:.2f} docs/sec")
    
    if summary['failed_files']:
        print(f"\nFailed files ({len(summary['failed_files'])}):")
        for item in summary['failed_files'][:10]:  # Show first 10
            print(f"  - {Path(item['file']).name}: {item['error'][:100]}")
        if len(summary['failed_files']) > 10:
            print(f"  ... and {len(summary['failed_files']) - 10} more")
    
    # Save statistics to file
    if save_stats:
        stats_file = f"ingestion_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        print(f"\n✓ Stats saved to {stats_file}")
    
    return stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch ingest documents into database')
    parser.add_argument('--raw-dir', default=r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\raw',
                        help='Raw directory to scan')
    parser.add_argument('--sections', nargs='+', 
                        help='Limit to specific sections (e.g., --sections 001 002)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of documents to process')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only section_001')
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of parallel workers (default: 4)')
    
    args = parser.parse_args()
    
    # Test mode: only section_001
    if args.test:
        print("TEST MODE: Processing section_001 only\n")
        batch_ingest(
            raw_dir=args.raw_dir,
            limit_sections=['001'],
            save_stats=True,
            max_workers=args.workers
        )
    else:
        # Full ingestion
        batch_ingest(
            raw_dir=args.raw_dir,
            limit_sections=args.sections,
            limit_count=args.limit,
            save_stats=True,
            max_workers=args.workers
        )
