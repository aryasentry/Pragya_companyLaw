"""
UNIFIED DOCUMENT PROCESSING PIPELINE
Upload → Save to Data folder → Ingest to DB → Chunk → Summarize → Embed

Usage:
    python pipeline_full.py --file path/to/file.pdf --type act --section 007
"""

import argparse
import sys
from pathlib import Path
import shutil
import subprocess

# Add governance_db to path
sys.path.insert(0, str(Path(__file__).parent / 'governance_db'))

from governance_db.unified_ingest_full import ingest_single_document_unified, UnifiedStats
from governance_db.build_faiss_index import build_vector_database
import psycopg2
from threading import Lock

def save_to_data_folder(file_path: str, doc_type: str, section: str) -> Path:
    """Save uploaded file to Data folder with proper structure"""
    print(f"\n📁 Saving file to Data folder...")
    
    file_path = Path(file_path)
    section_folder = f"section_{int(section):03d}"
    
    # Determine destination
    data_base = Path(__file__).parent / "data" / "companies_act"
    dest_folder = data_base / section_folder / doc_type
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    # Create unique filename
    dest_file = dest_folder / f"{section_folder}_{doc_type}{file_path.suffix}"
    
    # Copy file
    shutil.copy2(file_path, dest_file)
    
    print(f"✅ Saved to: {dest_file}")
    return dest_file

def ingest_document(file_path: Path, doc_type: str, section: str) -> dict:
    """Ingest document into PostgreSQL database"""
    print(f"\n📊 Ingesting into database...")
    
    from governance_db.unified_ingest_full import DocumentMetadata
    
    stats = UnifiedStats()
    pdf_counters = {}
    pdf_lock = Lock()
    
    metadata = DocumentMetadata(
        file_path=str(file_path),
        section_number=section.zfill(3),
        document_type=doc_type,
        pdf_instance=None
    )
    
    success = ingest_single_document_unified(
        metadata=metadata,
        pdf_counters=pdf_counters,
        pdf_lock=pdf_lock,
        stats=stats,
        skip_html=True,
        generate_summaries=True
    )
    
    if success:
        print(f"✅ Ingested: {stats.chunks_created} chunks, {stats.summaries_generated} summaries")
        return {
            'success': True,
            'chunks': stats.chunks_created,
            'summaries': stats.summaries_generated
        }
    else:
        print(f"❌ Ingestion failed")
        return {'success': False, 'error': 'Ingestion failed'}

def embed_new_chunks(limit: int = None):
    """Build/update FAISS embeddings for new chunks"""
    print(f"\n🔨 Building embeddings...")
    
    build_vector_database(sections=None, limit=limit)
    
    print(f"✅ Embeddings updated")

def run_full_pipeline(file_path: str, doc_type: str, section: str, skip_embedding: bool = False):
    """Run complete pipeline"""
    print("=" * 70)
    print("UNIFIED DOCUMENT PROCESSING PIPELINE")
    print("=" * 70)
    print(f"File: {file_path}")
    print(f"Type: {doc_type}")
    print(f"Section: {section}")
    print("=" * 70)
    
    # Step 1: Save to Data folder
    saved_file = save_to_data_folder(file_path, doc_type, section)
    
    # Step 2: Ingest to database
    result = ingest_document(saved_file, doc_type, section)
    
    if not result['success']:
        print("\n❌ Pipeline failed at ingestion step")
        return False
    
    # Step 3: Build embeddings (optional - can be batched)
    if not skip_embedding:
        embed_new_chunks()
    else:
        print("\n⏭️  Skipping embedding (run build_faiss_index.py manually)")
    
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE")
    print("=" * 70)
    return True

def main():
    parser = argparse.ArgumentParser(description='Process uploaded document through full pipeline')
    parser.add_argument('--file', required=True, help='Path to uploaded file')
    parser.add_argument('--type', required=True, choices=['act', 'rules', 'notifications', 'circulars', 'orders', 'forms', 'schedules'], help='Document type')
    parser.add_argument('--section', required=True, help='Section number (1-43)')
    parser.add_argument('--skip-embed', action='store_true', help='Skip embedding step (faster)')
    
    args = parser.parse_args()
    
    # Validate file exists
    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    # Validate section
    try:
        section_num = int(args.section)
        if section_num < 1 or section_num > 43:
            print(f"❌ Section must be between 1 and 43")
            sys.exit(1)
    except ValueError:
        print(f"❌ Invalid section number: {args.section}")
        sys.exit(1)
    
    # Run pipeline
    success = run_full_pipeline(
        file_path=args.file,
        doc_type=args.type,
        section=args.section,
        skip_embedding=args.skip_embed
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
