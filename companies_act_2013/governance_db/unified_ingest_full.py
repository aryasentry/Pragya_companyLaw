"""
Unified Ingestion Pipeline with Relationship Handling & Summarization
- Chunks documents (skip HTML)
- Handles relationships with validation
- Generates summaries and keywords
- Monitors progress with verification
"""
import os
import sys
import time
import json
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from folder_analyzer import scan_raw_directory, DocumentMetadata
from ingestion_service_simple import create_parent_chunk_simple, update_chunk_text_simple
from chunking_engine_simple import hierarchical_chunk
from db_config import get_db_connection
from reference_extractor import extract_and_create_relationships

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "qwen2.5:1.5b"

# Allowed relationship types (validation whitelist)
ALLOWED_RELATIONSHIPS = {
    "clarifies", "proceduralises", "implements",
    "amends", "supersedes", "part_of", "precedes"
}

# Document type to relationship mapping (governance rules)
RELATIONSHIP_RULES = {
    'rule': 'implements',           # Rules implement Acts
    'regulation': 'implements',     # Regulations implement Acts
    'notification': 'implements',   # Notifications implement Acts
    'circular': 'clarifies',        # Circulars clarify Acts
    'order': 'implements',          # Orders implement Acts
    'guideline': 'clarifies',       # Guidelines clarify Acts
    'sop': 'proceduralises',        # SOPs proceduralise Acts
    'form': 'proceduralises',       # Forms proceduralise Acts
    'schedule': 'proceduralises',   # Schedules proceduralise Acts
}

class UnifiedStats:
    """Thread-safe statistics tracking"""
    def __init__(self):
        self.lock = Lock()
        # Ingestion stats
        self.total_documents = 0
        self.successful_ingestions = 0
        self.failed_ingestions = 0
        self.skipped_documents = 0
        self.html_skipped = 0
        self.failed_files = []
        # Summary stats
        self.summaries_generated = 0
        self.keywords_extracted = 0
        self.summary_failures = 0
        # Relationship stats
        self.relationships_created = 0
        self.relationship_errors = 0
        # Timing
        self.start_time = None
        self.end_time = None
    
    def increment_success(self):
        with self.lock:
            self.successful_ingestions += 1
    
    def increment_failure(self, file_path: str, error: str):
        with self.lock:
            self.failed_ingestions += 1
            self.failed_files.append({"file": file_path, "error": error})
    
    def increment_skip(self, is_html: bool = False):
        with self.lock:
            self.skipped_documents += 1
            if is_html:
                self.html_skipped += 1
    
    def increment_summaries(self):
        with self.lock:
            self.summaries_generated += 1
    
    def increment_keywords(self, count: int):
        with self.lock:
            self.keywords_extracted += count
    
    def increment_summary_failures(self):
        with self.lock:
            self.summary_failures += 1
    
    def increment_relationships(self, count: int = 1):
        with self.lock:
            self.relationships_created += count
    
    def increment_relationship_errors(self):
        with self.lock:
            self.relationship_errors += 1

def call_ollama_generate(prompt: str, model: str = LLM_MODEL) -> Optional[str]:
    """Call Ollama API to generate text"""
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        return None
    except Exception as e:
        return None

def generate_summary(text: str) -> Optional[str]:
    """Generate a concise summary of the text"""
    if not text or len(text) < 50:
        return None
    
    text_sample = text[:2000] if len(text) > 2000 else text
    
    prompt = f"""Summarize the following legal text in 1-2 concise sentences. Focus on the key legal provisions and requirements.

Text:
{text_sample}

Summary:"""
    
    return call_ollama_generate(prompt)

def extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords from the text"""
    if not text or len(text) < 20:
        return []
    
    text_sample = text[:1500] if len(text) > 1500 else text
    
    prompt = f"""Extract 5-8 important keywords or key phrases from this legal text. Focus on legal terms, concepts, and entities.
Return ONLY the keywords separated by commas, nothing else.

Text:
{text_sample}

Keywords:"""
    
    response = call_ollama_generate(prompt)
    
    if not response:
        return []
    
    keywords = [kw.strip() for kw in response.split(',')]
    keywords = [kw for kw in keywords if kw and len(kw) > 2 and len(kw) < 50]
    return keywords[:10]

def validate_relationship_rules(chunk_id: str, document_type: str, relationships: Dict) -> List[str]:
    """Validate chunk against relationship rules"""
    errors = []
    
    # Rule 1: Child chunks MUST NOT have legal relationships
    if '_c' in chunk_id and any(chunk_id.endswith(f'_c{i}') for i in range(1, 10)):
        if any(relationships.values()):
            errors.append(f"Child chunk {chunk_id} has relationships")
        return errors  # Skip other validations for child chunks
    
    # Rule 2: Document-type enforcement
    if document_type == 'act':
        if relationships.get('clarifies') or relationships.get('proceduralises') or relationships.get('implements'):
            errors.append(f"Act chunk {chunk_id} should not have forward clarifies/proceduralises/implements")
    
    elif document_type == 'rule':
        if relationships.get('clarifies') or relationships.get('amends'):
            errors.append(f"Rule chunk {chunk_id} should not clarify or amend")
    
    elif document_type == 'circular':
        if relationships.get('implements') or relationships.get('proceduralises'):
            errors.append(f"Circular chunk {chunk_id} should not implement or proceduralise")
    
    elif document_type == 'notification':
        if relationships.get('clarifies') or relationships.get('proceduralises'):
            errors.append(f"Notification chunk {chunk_id} should not clarify or proceduralise")
    
    elif document_type in ['sop', 'form']:
        if relationships.get('clarifies') or relationships.get('implements') or relationships.get('amends'):
            errors.append(f"{document_type} chunk {chunk_id} should only proceduralise")
    
    elif document_type == 'commentary':
        if any(relationships.values()):
            errors.append(f"Commentary chunk {chunk_id} should have no relationships")
    
    # Rule 3: Validate relationship types against whitelist
    for rel_type in relationships.keys():
        if rel_type not in ALLOWED_RELATIONSHIPS:
            errors.append(f"Unknown relationship type '{rel_type}' in {chunk_id}")
    
    return errors

def process_summary_and_keywords(chunk_id: str, text: str, stats: UnifiedStats):
    """Generate and save summary + keywords for a chunk"""
    try:
        # Generate summary
        summary = generate_summary(text)
        
        # Extract keywords
        keywords = extract_keywords(text)
        
        # Update database
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Update summary
            if summary:
                cur.execute("""
                    UPDATE chunks_content
                    SET summary = %s, updated_at = now()
                    WHERE chunk_id = %s
                """, (summary, chunk_id))
                stats.increment_summaries()
            
            # Insert keywords
            if keywords:
                cur.execute("DELETE FROM chunk_keywords WHERE chunk_id = %s", (chunk_id,))
                
                for keyword in keywords:
                    cur.execute("""
                        INSERT INTO chunk_keywords (chunk_id, keyword)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (chunk_id, keyword))
                
                stats.increment_keywords(len(keywords))
            
            cur.close()
        
        return True
        
    except Exception as e:
        stats.increment_summary_failures()
        return False

def create_relationships_for_chunk(chunk_id: str, section_number: str, document_type: str, stats: UnifiedStats):
    """Create relationships for a chunk based on document type and section"""
    try:
        # Only create relationships for non-Act documents
        if document_type == 'act':
            return True
        
        # Get relationship type for this document type
        relationship = RELATIONSHIP_RULES.get(document_type)
        if not relationship:
            return True  # Unknown document type, skip
        
        # Find Act chunk in same section
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Get Act chunk for this section
            cur.execute("""
                SELECT chunk_id
                FROM chunks_identity
                WHERE section = %s
                AND document_type = 'act'
                AND chunk_role = 'parent'
                LIMIT 1
            """, (section_number,))
            
            act_chunk = cur.fetchone()
            
            if not act_chunk:
                # No Act chunk found, skip relationship creation
                return True
            
            act_chunk_id = act_chunk['chunk_id']
            
            # Create relationship: this_chunk -> relationship -> act_chunk
            cur.execute("""
                INSERT INTO chunk_relationships (from_chunk_id, to_chunk_id, relationship)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (chunk_id, act_chunk_id, relationship))
            
            if cur.rowcount > 0:
                stats.increment_relationships()
            
            cur.close()
        
        return True
        
    except Exception as e:
        stats.increment_relationship_errors()
        return False

def ingest_single_document_unified(
    metadata: DocumentMetadata,
    pdf_counters: Dict[str, int],
    pdf_lock: Lock,
    stats: UnifiedStats,
    skip_html: bool = True,
    generate_summaries: bool = True
) -> bool:
    """Ingest a single document with full processing"""
    try:
        logger.info(f"Starting ingestion for: {metadata.file_path}")
        
        # Skip HTML files if requested
        if skip_html and metadata.file_path.lower().endswith('.html'):
            logger.info("Skipping HTML file")
            stats.increment_skip(is_html=True)
            return False
        
        from pdf_parser import parse_document
        
        # Parse document
        logger.info("Parsing document...")
        result = parse_document(metadata.file_path)
        text = result.get('text') if isinstance(result, dict) else result
        
        if not text or len(text.strip()) < 10:
            logger.warning(f"Text too short or empty: {len(text) if text else 0} chars")
            stats.increment_skip()
            return False
        
        logger.info(f"Parsed {len(text)} characters")
        
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
        logger.info(f"Creating parent chunk with type={metadata.document_type}, section={metadata.section_number}")
        parent_id = create_parent_chunk_simple(
            document_type=metadata.document_type,
            title=metadata.title,
            section_number=metadata.section_number,
            compliance_area=metadata.compliance_area,
            citation=f"Source: {metadata.file_path.replace(chr(92), '/')}",
            file_ext=file_ext,
            binding=metadata.is_binding
        )
        
        logger.info(f"Parent chunk created: {parent_id}")
        
        # Update parent with full text
        logger.info("Updating parent chunk with text...")
        update_chunk_text_simple(parent_id, text)
        
        # Generate summary and keywords for parent chunk
        if generate_summaries:
            logger.info("Generating summary and keywords...")
            process_summary_and_keywords(parent_id, text, stats)
        
        # Create relationships based on document type
        logger.info("Creating relationships...")
        create_relationships_for_chunk(
            parent_id, 
            metadata.section_number, 
            metadata.document_type, 
            stats
        )
        
        # Extract cross-references from text and create relationships
        logger.info("Extracting cross-references...")
        ref_stats = extract_and_create_relationships(
            chunk_id=parent_id,
            text=text,
            document_type=metadata.document_type,
            current_section=metadata.section_number,
            min_confidence=0.5
        )
        stats.increment_relationships(ref_stats['created'])
        
        # Create child chunks
        logger.info("Creating child chunks...")
        child_ids = hierarchical_chunk(
            parent_chunk_id=parent_id,
            text=text,
            max_chars=1000,
            overlap_chars=100
        )
        
        logger.info(f"Ingestion successful! Created {len(child_ids)} child chunks")
        stats.increment_success()
        return True
        
    except Exception as e:
        import traceback
        logger.error(f"Ingestion failed for {metadata.file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        stats.increment_failure(metadata.file_path, str(e))
        return False

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
        
        # Count summaries
        cur.execute("SELECT COUNT(*) as count FROM chunks_content WHERE summary IS NOT NULL AND summary != ''")
        stats["chunks_with_summaries"] = cur.fetchone()['count']
        
        # Count keywords
        cur.execute("SELECT COUNT(DISTINCT chunk_id) as count FROM chunk_keywords")
        stats["chunks_with_keywords"] = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM chunk_keywords")
        stats["total_keywords"] = cur.fetchone()['count']
        
        # Count relationships
        cur.execute("SELECT COUNT(*) as count FROM chunk_relationships")
        stats["total_relationships"] = cur.fetchone()['count']
        
        # Check for ID clashes
        cur.execute("SELECT chunk_id, COUNT(*) as count FROM chunks_identity GROUP BY chunk_id HAVING COUNT(*) > 1")
        clashes = cur.fetchall()
        stats["id_clashes"] = len(clashes)
        
        # Sample recent chunks
        cur.execute("SELECT chunk_id FROM chunks_identity WHERE chunk_role = 'parent' ORDER BY chunk_id DESC LIMIT 5")
        stats["recent_parent_ids"] = [row['chunk_id'] for row in cur.fetchall()]
        
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
    
    print(f"\n📝 Content Enrichment:")
    print(f"   With summaries: {stats['chunks_with_summaries']:5}")
    print(f"   With keywords:  {stats['chunks_with_keywords']:5}")
    print(f"   Total keywords: {stats['total_keywords']:5}")
    
    print(f"\n🔗 Relationships:")
    print(f"   Total: {stats['total_relationships']:5}")
    
    if stats['id_clashes'] > 0:
        print(f"\n⚠️  ID CLASHES FOUND: {stats['id_clashes']}")
    else:
        print(f"\n✓ No ID clashes")
    
    print(f"\n🔍 Recent Parent Chunks:")
    for chunk_id in stats['recent_parent_ids']:
        print(f"   {chunk_id}")
    
    print("="*70 + "\n")

def unified_batch_ingest(
    sections: List[str],
    max_workers: int = 8,
    verification_interval: int = 5,
    skip_html: bool = True,
    generate_summaries: bool = True
):
    """
    Unified ingestion with relationships and summaries
    
    Args:
        sections: List of section numbers to process
        max_workers: Number of parallel workers
        verification_interval: Verify DB every N sections
        skip_html: Skip HTML files to avoid duplicates
        generate_summaries: Generate summaries and keywords
    """
    # Scan raw directory
    print("📁 Scanning raw directory...")
    raw_dir = Path(__file__).parent.parent / "raw"
    all_documents = scan_raw_directory(str(raw_dir), skip_html=skip_html)
    
    # Filter documents by sections
    if sections:
        documents = [d for d in all_documents if d.section_number in sections]
    else:
        documents = all_documents
    
    html_count = sum(1 for d in all_documents if d.file_path.lower().endswith('.html'))
    
    print(f"📄 Found {len(documents)} documents to ingest")
    if skip_html and html_count > 0:
        print(f"⏭️  Skipping {html_count} HTML files (duplicates)")
    print(f"⚙️  Using {max_workers} parallel workers")
    print(f"📝 Summary generation: {'ON' if generate_summaries else 'OFF'}")
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
        stats = UnifiedStats()
        stats.total_documents = len(batch_documents)
        stats.start_time = time.time()
        
        # Shared counters
        pdf_counters = {}
        pdf_lock = Lock()
        
        # Parallel ingestion
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    ingest_single_document_unified,
                    doc,
                    pdf_counters,
                    pdf_lock,
                    stats,
                    skip_html,
                    generate_summaries
                ): doc for doc in batch_documents
            }
            
            with tqdm(total=len(batch_documents), desc=f"Batch {batch_num}") as pbar:
                for future in as_completed(futures):
                    pbar.update(1)
        
        stats.end_time = time.time()
        elapsed = stats.end_time - stats.start_time
        
        # Print batch summary
        print(f"\n✓ Batch {batch_num} Complete:")
        print(f"   Successful:  {stats.successful_ingestions}")
        print(f"   Failed:      {stats.failed_ingestions}")
        print(f"   Skipped:     {stats.skipped_documents} (HTML: {stats.html_skipped})")
        if generate_summaries:
            print(f"   Summaries:   {stats.summaries_generated}")
            print(f"   Keywords:    {stats.keywords_extracted}")
        print(f"   Relationships: {stats.relationships_created}")
        print(f"   Time:        {elapsed:.2f}s")
        print(f"   Rate:        {stats.successful_ingestions/elapsed:.2f} docs/sec")
        
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
                "html_skipped": stats.html_skipped,
                "summaries_generated": stats.summaries_generated,
                "keywords_extracted": stats.keywords_extracted,
                "summary_failures": stats.summary_failures,
                "relationships_created": stats.relationships_created,
                "relationship_errors": stats.relationship_errors,
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
    
    # Final summary
    print("\n" + "="*70)
    print("UNIFIED INGESTION COMPLETE")
    print("="*70)
    
    total_success = sum(s['ingestion_stats']['successful'] for s in all_stats)
    total_failed = sum(s['ingestion_stats']['failed'] for s in all_stats)
    total_skipped = sum(s['ingestion_stats']['skipped'] for s in all_stats)
    total_summaries = sum(s['ingestion_stats']['summaries_generated'] for s in all_stats)
    total_keywords = sum(s['ingestion_stats']['keywords_extracted'] for s in all_stats)
    total_relationships = sum(s['ingestion_stats']['relationships_created'] for s in all_stats)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Batches processed:    {len(all_stats)}")
    print(f"   Total successful:     {total_success}")
    print(f"   Total failed:         {total_failed}")
    print(f"   Total skipped:        {total_skipped}")
    print(f"   Summaries generated:  {total_summaries}")
    print(f"   Keywords extracted:   {total_keywords}")
    print(f"   Relationships created: {total_relationships}")
    
    # Final DB verification
    final_stats = verify_database_state("ALL SECTIONS")
    print_verification_report(final_stats)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified ingestion with relationships and summaries')
    parser.add_argument('--sections', nargs='+', help='Specific sections to process')
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--interval', type=int, default=5, help='Verify DB every N sections')
    parser.add_argument('--start', type=str, help='Start from section (e.g., 001)')
    parser.add_argument('--end', type=str, help='End at section (e.g., 043)')
    parser.add_argument('--skip-html', action='store_true', default=True, help='Skip HTML files (default: True)')
    parser.add_argument('--no-summaries', action='store_true', help='Skip summary generation')
    
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
        # Process all sections by default
        sections = [f"{i:03d}" for i in range(1, 44)]
    
    print(f"🚀 Starting UNIFIED ingestion pipeline")
    print(f"📍 Sections: {sections[0]} to {sections[-1]} ({len(sections)} sections)")
    print(f"⚙️  Workers: {args.workers}")
    print(f"🔍 Verification interval: every {args.interval} sections")
    print(f"⏭️  Skip HTML: {args.skip_html}")
    print(f"📝 Generate summaries: {not args.no_summaries}\n")
    
    unified_batch_ingest(
        sections=sections,
        max_workers=args.workers,
        verification_interval=args.interval,
        skip_html=args.skip_html,
        generate_summaries=not args.no_summaries
    )
