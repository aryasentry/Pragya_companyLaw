"""
Monitored batch ingestion - processes sections in batches with verification
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

from folder_analyzer import scan_raw_directory, DocumentMetadata
from ingestion_service_simple import create_parent_chunk_simple, update_chunk_text_simple
from chunking_engine_simple import hierarchical_chunk
from db_config import get_db_connection

class IngestionStats:
    def __init__(self):
        self.lock = Lock()
        self.total_documents = 0
        self.successful_ingestions = 0
        self.failed_ingestions = 0
        self.skipped_documents = 0
        self.failed_files = []
        self.start_time = None
        self.end_time = None
    
    def increment_success(self):
        with self.lock:
            self.successful_ingestions += 1
    
    def increment_failure(self, file_path: str, error: str):
        with self.lock:
            self.failed_ingestions += 1
            self.failed_files.append({"file": file_path, "error": error})
    
    def increment_skip(self):
        with self.lock:
            self.skipped_documents += 1

def verify_database_state(section_range: str) -> Dict[str, Any]:
    """Verify database state and return statistics"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        stats = {
            "section_range": section_range,
            "timestamp": datetime.now().isoformat(),
            "tables": {}
        }
        
        # Count chunks
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'parent'")
        parent_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'child'")
        child_count = cur.fetchone()['count']
        
        stats["parent_chunks"] = parent_count
        stats["child_chunks"] = child_count
        stats["total_chunks"] = parent_count + child_count
        
        # Check for ID clashes
        cur.execute("SELECT chunk_id, COUNT(*) as count FROM chunks_identity GROUP BY chunk_id HAVING COUNT(*) > 1")
        clashes = cur.fetchall()
        stats["id_clashes"] = len(clashes)
        if clashes:
            stats["clash_details"] = [{"chunk_id": c['chunk_id'], "count": c['count']} for c in clashes]
        
        # Table row counts
        tables = [
            'chunks_identity', 'chunks_content', 'chunk_legal_anchors', 'chunk_keywords',
            'chunk_relationships', 'chunk_retrieval_rules', 'chunk_refusal_policy',
            'chunk_temporal', 'chunk_lifecycle', 'chunk_versioning', 'chunk_embeddings',
            'chunk_lineage', 'chunk_administrative', 'chunk_audit', 'chunk_source'
        ]
        
        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            stats["tables"][table] = count
        
        # Sample recent chunk IDs
        cur.execute("SELECT chunk_id FROM chunks_identity WHERE chunk_role = 'parent' ORDER BY chunk_id DESC LIMIT 5")
        stats["recent_parent_ids"] = [row['chunk_id'] for row in cur.fetchall()]
        
        cur.execute("SELECT chunk_id FROM chunks_identity WHERE chunk_role = 'child' ORDER BY chunk_id DESC LIMIT 5")
        stats["recent_child_ids"] = [row['chunk_id'] for row in cur.fetchall()]
        
        cur.close()
        return stats

def print_verification_report(stats: Dict[str, Any]):
    """Print verification report"""
    print("\n" + "="*70)
    print(f"DATABASE VERIFICATION - {stats['section_range']}")
    print("="*70)
    print(f"\n📊 Chunk Counts:")
    print(f"   Parents:  {stats['parent_chunks']:5}")
    print(f"   Children: {stats['child_chunks']:5}")
    print(f"   Total:    {stats['total_chunks']:5}")
    
    if stats['id_clashes'] > 0:
        print(f"\n⚠️  ID CLASHES FOUND: {stats['id_clashes']}")
        for clash in stats['clash_details']:
            print(f"   {clash['chunk_id']}: {clash['count']} duplicates")
    else:
        print(f"\n✓ No ID clashes - all unique")
    
    print(f"\n📋 Table Row Counts:")
    for table, count in stats['tables'].items():
        print(f"   {table:25} {count:5} rows")
    
    print(f"\n🔍 Recent Parent Chunks:")
    for chunk_id in stats['recent_parent_ids']:
        print(f"   {chunk_id}")
    
    print(f"\n🔍 Recent Child Chunks:")
    for chunk_id in stats['recent_child_ids']:
        print(f"   {chunk_id}")
    
    print("="*70 + "\n")

def ingest_single_document(
    metadata: DocumentMetadata,
    pdf_counters: Dict[str, int],
    pdf_lock: Lock,
    stats: IngestionStats
) -> bool:
    """Ingest a single document with error handling"""
    try:
        from pdf_parser import parse_document
        
        # Parse document
        result = parse_document(metadata.file_path)
        text = result.get('text') if isinstance(result, dict) else result
        
        if not text or len(text.strip()) < 10:
            stats.increment_skip()
            return False
        
        # Determine file extension for unique ID
        file_ext = Path(metadata.file_path).suffix.lower().replace('.', '')
        
        # Handle PDF numbering for multiple PDFs
        if file_ext == 'pdf':
            counter_key = f"{metadata.section_number}_{metadata.document_type}"
            with pdf_lock:
                pdf_counters[counter_key] = pdf_counters.get(counter_key, 0) + 1
                pdf_counter = pdf_counters[counter_key]
            file_ext = f"pdf{pdf_counter}"
        
        # Create parent chunk
        parent_id = create_parent_chunk_simple(
            document_type=metadata.document_type,
            title=metadata.title,
            section_number=metadata.section_number,
            compliance_area=metadata.compliance_area,
            citation=f"Source: {metadata.file_path.replace(chr(92), '/')}",
            file_ext=file_ext,
            binding=metadata.is_binding
        )
        
        # Update parent with full text
        update_chunk_text_simple(parent_id, text)
        
        # Create child chunks
        child_ids = hierarchical_chunk(
            parent_chunk_id=parent_id,
            text=text,
            max_chars=1000,
            overlap_chars=100
        )
        
        stats.increment_success()
        return True
        
    except Exception as e:
        stats.increment_failure(metadata.file_path, str(e))
        return False

def batch_ingest_monitored(
    sections: List[str],
    max_workers: int = 4,
    verification_interval: int = 5
):
    """
    Ingest documents in batches with periodic verification
    
    Args:
        sections: List of section numbers to process
        max_workers: Number of parallel workers
        verification_interval: Verify DB every N sections
    """
    # Scan raw directory
    print("📁 Scanning raw directory...")
    raw_dir = Path(__file__).parent.parent / "raw"
    all_documents = scan_raw_directory(str(raw_dir))
    
    # Filter documents by sections
    if sections:
        documents = [d for d in all_documents if d.section_number in sections]
    else:
        documents = all_documents
    
    print(f"📄 Found {len(documents)} documents to ingest")
    print(f"⚙️  Using {max_workers} parallel workers")
    print(f"🔍 Verifying database every {verification_interval} sections\n")
    
    # Group documents by section
    sections_dict = {}
    for doc in documents:
        if doc.section_number not in sections_dict:
            sections_dict[doc.section_number] = []
        sections_dict[doc.section_number].append(doc)
    
    section_numbers = sorted(sections_dict.keys())
    
    # Create log directory
    log_dir = Path("verification_logs")
    log_dir.mkdir(exist_ok=True)
    
    # Process sections in batches
    all_stats = []
    batch_num = 1
    
    for i in range(0, len(section_numbers), verification_interval):
        batch_sections = section_numbers[i:i+verification_interval]
        batch_documents = []
        for sec in batch_sections:
            batch_documents.extend(sections_dict[sec])
        
        print(f"\n{'='*70}")
        print(f"BATCH {batch_num}: Sections {batch_sections[0]} to {batch_sections[-1]}")
        print(f"{'='*70}")
        print(f"Processing {len(batch_documents)} documents...")
        
        # Initialize stats
        stats = IngestionStats()
        stats.total_documents = len(batch_documents)
        stats.start_time = time.time()
        
        # Shared counters
        pdf_counters = {}
        pdf_lock = Lock()
        
        # Parallel ingestion
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    ingest_single_document,
                    doc,
                    pdf_counters,
                    pdf_lock,
                    stats
                ): doc for doc in batch_documents
            }
            
            with tqdm(total=len(batch_documents), desc=f"Batch {batch_num}") as pbar:
                for future in as_completed(futures):
                    pbar.update(1)
        
        stats.end_time = time.time()
        elapsed = stats.end_time - stats.start_time
        
        # Print batch summary
        print(f"\n✓ Batch {batch_num} Complete:")
        print(f"   Successful: {stats.successful_ingestions}")
        print(f"   Failed:     {stats.failed_ingestions}")
        print(f"   Skipped:    {stats.skipped_documents}")
        print(f"   Time:       {elapsed:.2f}s")
        print(f"   Rate:       {stats.successful_ingestions/elapsed:.2f} docs/sec")
        
        if stats.failed_files:
            print(f"\n⚠️  Failed files:")
            for fail in stats.failed_files[:5]:
                print(f"   {fail['file']}: {fail['error']}")
        
        # Verify database
        section_range = f"{batch_sections[0]} to {batch_sections[-1]}"
        db_stats = verify_database_state(section_range)
        print_verification_report(db_stats)
        
        # Save verification log
        log_file = log_dir / f"verification_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_data = {
            "batch_number": batch_num,
            "sections": batch_sections,
            "ingestion_stats": {
                "total": stats.total_documents,
                "successful": stats.successful_ingestions,
                "failed": stats.failed_ingestions,
                "skipped": stats.skipped_documents,
                "elapsed_seconds": elapsed,
                "rate_docs_per_sec": stats.successful_ingestions/elapsed if elapsed > 0 else 0,
                "failed_files": stats.failed_files
            },
            "database_stats": db_stats
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"📝 Verification log saved: {log_file}\n")
        
        all_stats.append(log_data)
        batch_num += 1
        
        # Pause for review if there are issues
        if db_stats['id_clashes'] > 0 or stats.failed_ingestions > 0:
            print("⚠️  Issues detected! Please review before continuing.")
            response = input("Continue to next batch? (y/n): ")
            if response.lower() != 'y':
                print("Stopping ingestion.")
                break
    
    # Final summary
    print("\n" + "="*70)
    print("INGESTION COMPLETE")
    print("="*70)
    
    total_success = sum(s['ingestion_stats']['successful'] for s in all_stats)
    total_failed = sum(s['ingestion_stats']['failed'] for s in all_stats)
    total_skipped = sum(s['ingestion_stats']['skipped'] for s in all_stats)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Batches processed:  {len(all_stats)}")
    print(f"   Total successful:   {total_success}")
    print(f"   Total failed:       {total_failed}")
    print(f"   Total skipped:      {total_skipped}")
    
    # Final DB verification
    final_stats = verify_database_state("ALL SECTIONS")
    print_verification_report(final_stats)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitored batch ingestion')
    parser.add_argument('--sections', nargs='+', help='Specific sections to process (e.g., 001 002 003)')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--interval', type=int, default=5, help='Verify DB every N sections')
    parser.add_argument('--start', type=str, help='Start from section (e.g., 001)')
    parser.add_argument('--end', type=str, help='End at section (e.g., 043)')
    
    args = parser.parse_args()
    
    # Determine sections to process
    if args.sections:
        sections = args.sections
    elif args.start and args.end:
        start_num = int(args.start)
        end_num = int(args.end)
        sections = [f"{i:03d}" for i in range(start_num, end_num + 1)]
    elif args.start:
        start_num = int(args.start)
        sections = [f"{i:03d}" for i in range(start_num, 44)]
    else:
        # Process first 5 sections by default
        sections = [f"{i:03d}" for i in range(1, 6)]
    
    print(f"🚀 Starting monitored ingestion")
    print(f"📍 Sections: {sections[0]} to {sections[-1]} ({len(sections)} sections)")
    print(f"⚙️  Workers: {args.workers}")
    print(f"🔍 Verification interval: every {args.interval} sections\n")
    
    batch_ingest_monitored(
        sections=sections,
        max_workers=args.workers,
        verification_interval=args.interval
    )
