"""
Full Document Processing Pipeline  
Upload -> Save to Data folder -> Ingest to DB -> Chunk -> Summarize -> Keywords -> Relationships -> Embed (optional)
"""

import os
import sys
import shutil
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from folder_analyzer import DocumentMetadata
from unified_ingest_full import ingest_single_document_unified, UnifiedStats
from build_faiss_index import build_vector_database as build_embeddings
from threading import Lock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Document type to priority mapping (lowercase)
DOC_TYPE_PRIORITY = {
    # Priority 1: Primary statutory sources
    'act': 1,
    'rule': 1,
    
    # Priority 2: Secondary statutory sources
    'regulation': 2,
    'order': 2,
    'notification': 2,
    'schedule': 2,
    
    # Priority 3: Official guidance
    'circular': 3,
    'form': 3,
    'register': 3,
    'return': 3,
    'sop': 3,
    'guideline': 3,
    
    # Priority 4: Informational/reference
    'qa': 4,
    'other': 4,
    'practice_note': 4,
    'commentary': 4,
    'textbook': 4,
}


def ingest_document(file_path: str, doc_type: str, section: str = None, priority: int = 4, skip_embed: bool = False):
    """
    Ingest single document: Chunk -> Summarize -> Keywords -> Relationships
    """
    # Determine binding status (use lowercase for consistency)
    is_binding = doc_type.lower() in ['act', 'rule', 'regulation', 'order', 'notification', 'schedule', 'circular', 'form', 'register', 'return']
    binding_note = 'Statutory document' if is_binding else 'Informational/guidance'
    file_type = Path(file_path).suffix.lower().lstrip('.') or 'txt'
    
    # Create metadata object
    metadata = DocumentMetadata(
        file_path=file_path,
        document_type=doc_type.lower(),
        section_number=section,
        is_binding=is_binding,
        binding_note=binding_note,
        file_type=file_type
    )
    
    # Initialize stats and locks for thread-safe processing
    stats = UnifiedStats()
    pdf_counters = {}
    pdf_lock = Lock()
    
    # Run full ingestion pipeline with progress updates
    print("STAGE:Parsing", flush=True)
    logger.info("Parsing document content...")
    
    print("STAGE:Chunking", flush=True)
    logger.info("Creating parent chunk and hierarchical chunks...")
    
    print("STAGE:Summarizing", flush=True)
    logger.info("Generating summaries and extracting keywords...")
    
    print("STAGE:Relationships", flush=True)
    logger.info("Creating relationships to related sections...")
    
    try:
        success = ingest_single_document_unified(
            metadata=metadata,
            pdf_counters=pdf_counters,
            pdf_lock=pdf_lock,
            stats=stats,
            skip_html=True,
            generate_summaries=True
        )
        
        if success:
            logger.info("Ingestion completed successfully")
            logger.info(f"Successful ingestions: {stats.successful_ingestions}")
            logger.info(f"Summaries generated: {stats.summaries_generated}")
            logger.info(f"Keywords extracted: {stats.keywords_extracted}")
            logger.info(f"Relationships created: {stats.relationships_created}")
            
            print("STAGE:Completed", flush=True)
        else:
            logger.error("Ingestion returned False - check file content and database connection")
            raise Exception("Ingestion returned False")
            
    except Exception as e:
        logger.error(f"Ingestion error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise Exception(f"Ingestion failed: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Full document processing pipeline')
    parser.add_argument('--file', required=True, help='Path to uploaded file')
    parser.add_argument('--type', required=True, help='Document type (Act, Rule, Circular, etc.)')
    parser.add_argument('--category', default='companies_act', 
                       help='Document category: companies_act or non_binding')
    parser.add_argument('--section', help='Section number (001-043) for companies_act documents')
    parser.add_argument('--skip-embed', action='store_true', 
                       help='Skip embedding generation (for batch processing)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.category not in ['companies_act', 'non_binding']:
        logger.error(f"Invalid category: {args.category}")
        sys.exit(1)
    
    if args.category == 'companies_act' and not args.section:
        logger.error("Section required for companies_act documents")
        sys.exit(1)
    
    if args.type not in DOC_TYPE_PRIORITY:
        logger.warning(f"Unknown document type '{args.type}', defaulting to priority 4")
    
    # Get priority
    priority = DOC_TYPE_PRIORITY.get(args.type, 4)
    
    logger.info("=" * 60)
    logger.info(f"Processing: {Path(args.file).name}")
    logger.info(f"Category: {args.category}")
    logger.info(f"Type: {args.type} (Priority {priority})")
    if args.section:
        logger.info(f"Section: {args.section}")
    logger.info("=" * 60)
    
    try:
        # Step 1: Move file to Data folder structure
        logger.info("Step 1: Moving to Data folder...")
        data_dir = Path(__file__).parent.parent / 'data'
        
        if args.category == 'companies_act':
            if not args.section:
                logger.error("Section required for companies_act documents")
                sys.exit(1)
            dest_dir = data_dir / 'companies_act' / f'section_{args.section}' / args.type
        else:
            dest_dir = data_dir / 'non_binding' / args.type
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_name = Path(args.file).name
        data_path = dest_dir / file_name
        
        # Move file (not copy, since it's from temp uploads)
        shutil.move(args.file, data_path)
        logger.info(f"Saved to: {data_path}")
        
        # Step 2: Full ingestion pipeline
        logger.info("Step 2: Full ingestion pipeline...")
        ingest_document(
            file_path=str(data_path),
            doc_type=args.type,
            section=args.section,
            priority=priority,
            skip_embed=args.skip_embed
        )
        
        # Step 3: Build embeddings (optional)
        if not args.skip_embed:
            print("STAGE:Building Embeddings", flush=True)
            logger.info("Step 3: Building FAISS embeddings...")
            try:
                build_embeddings()
                logger.info("Embeddings updated")
            except Exception as embed_error:
                logger.error(f"Embedding failed: {embed_error}")
                import traceback
                logger.error(traceback.format_exc())
                raise Exception(f"Embedding failed: {embed_error}")
        else:
            logger.info("Skipping embeddings (batch later)")
        
        print("STAGE:Completed", flush=True)
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED")
        logger.info("=" * 60)
        logger.info(f"File: {file_name}")
        logger.info(f"Location: {data_path}")
        logger.info("Ingested -> Chunked -> Summarized -> Keywords -> Relationships")
        if not args.skip_embed:
            logger.info("Embedded")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
