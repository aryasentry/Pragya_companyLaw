"""
Generate summaries and extract keywords for chunks using Ollama LLM
"""
import json
import requests
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from datetime import datetime
from db_config import get_db_connection

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "qwen2.5:1.5b"

# Processing configuration
BATCH_SIZE = 50
MAX_WORKERS = 4  # Fewer workers for LLM calls to avoid overload

class SummaryStats:
    """Thread-safe statistics tracking"""
    def __init__(self):
        self.lock = Lock()
        self.total_processed = 0
        self.summaries_generated = 0
        self.keywords_extracted = 0
        self.failures = 0
        self.start_time = datetime.now()
    
    def increment_processed(self):
        with self.lock:
            self.total_processed += 1
    
    def increment_summaries(self):
        with self.lock:
            self.summaries_generated += 1
    
    def increment_keywords(self, count: int):
        with self.lock:
            self.keywords_extracted += count
    
    def increment_failures(self):
        with self.lock:
            self.failures += 1
    
    def get_stats(self) -> Dict:
        with self.lock:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return {
                'total_processed': self.total_processed,
                'summaries_generated': self.summaries_generated,
                'keywords_extracted': self.keywords_extracted,
                'failures': self.failures,
                'elapsed_seconds': elapsed,
                'rate_per_sec': self.total_processed / elapsed if elapsed > 0 else 0
            }

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
                    "temperature": 0.3,  # Lower temperature for more focused output
                    "num_predict": 200   # Limit output length
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            print(f"Ollama API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None

def generate_summary(text: str) -> Optional[str]:
    """Generate a concise summary of the text"""
    if not text or len(text) < 50:
        return None
    
    # Truncate very long texts for summary generation
    text_sample = text[:2000] if len(text) > 2000 else text
    
    prompt = f"""Summarize the following legal text in 1-2 concise sentences. Focus on the key legal provisions and requirements.

Text:
{text_sample}

Summary:"""
    
    return call_ollama_generate(prompt)

def extract_keywords(text: str, chunk_id: str) -> List[str]:
    """Extract relevant keywords from the text"""
    if not text or len(text) < 20:
        return []
    
    # Truncate very long texts for keyword extraction
    text_sample = text[:1500] if len(text) > 1500 else text
    
    prompt = f"""Extract 5-8 important keywords or key phrases from this legal text. Focus on legal terms, concepts, and entities.
Return ONLY the keywords separated by commas, nothing else.

Text:
{text_sample}

Keywords:"""
    
    response = call_ollama_generate(prompt)
    
    if not response:
        return []
    
    # Parse keywords from response
    keywords = [kw.strip() for kw in response.split(',')]
    # Clean and filter keywords
    keywords = [kw for kw in keywords if kw and len(kw) > 2 and len(kw) < 50]
    # Limit to 10 keywords
    return keywords[:10]

def process_chunk(chunk_data: Dict, stats: SummaryStats) -> bool:
    """Process a single chunk to generate summary and keywords"""
    chunk_id = chunk_data['chunk_id']
    text = chunk_data['text']
    
    try:
        # Generate summary
        summary = generate_summary(text)
        
        # Extract keywords
        keywords = extract_keywords(text, chunk_id)
        
        # Update database
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Update summary if generated
            if summary:
                cur.execute("""
                    UPDATE chunks_content
                    SET summary = %s, updated_at = now()
                    WHERE chunk_id = %s
                """, (summary, chunk_id))
                stats.increment_summaries()
            
            # Insert keywords if extracted
            if keywords:
                # Delete existing keywords first
                cur.execute("DELETE FROM chunk_keywords WHERE chunk_id = %s", (chunk_id,))
                
                # Insert new keywords
                for keyword in keywords:
                    cur.execute("""
                        INSERT INTO chunk_keywords (chunk_id, keyword)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (chunk_id, keyword))
                
                stats.increment_keywords(len(keywords))
            
            cur.close()
        
        stats.increment_processed()
        
        # Print progress
        if stats.total_processed % 10 == 0:
            current_stats = stats.get_stats()
            print(f"✓ Processed {current_stats['total_processed']} chunks | "
                  f"Summaries: {current_stats['summaries_generated']} | "
                  f"Keywords: {current_stats['keywords_extracted']} | "
                  f"Rate: {current_stats['rate_per_sec']:.2f}/sec")
        
        return True
        
    except Exception as e:
        print(f"✗ Error processing {chunk_id}: {e}")
        stats.increment_failures()
        return False

def fetch_chunks_without_summary(limit: Optional[int] = None) -> List[Dict]:
    """Fetch chunks that don't have summaries yet"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT ci.chunk_id, cc.text
            FROM chunks_identity ci
            JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE ci.chunk_role = 'parent'
            AND (cc.summary IS NULL OR cc.summary = '')
            AND cc.text IS NOT NULL
            ORDER BY ci.chunk_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        chunks = cur.fetchall()
        cur.close()
        
        return [{'chunk_id': c['chunk_id'], 'text': c['text']} for c in chunks]

def fetch_chunks_without_keywords(limit: Optional[int] = None) -> List[Dict]:
    """Fetch chunks that don't have keywords yet"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT ci.chunk_id, cc.text
            FROM chunks_identity ci
            JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE ci.chunk_role = 'parent'
            AND cc.text IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM chunk_keywords ck 
                WHERE ck.chunk_id = ci.chunk_id
            )
            ORDER BY ci.chunk_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        chunks = cur.fetchall()
        cur.close()
        
        return [{'chunk_id': c['chunk_id'], 'text': c['text']} for c in chunks]

def run_summarization(workers: int = MAX_WORKERS, limit: Optional[int] = None):
    """Run summarization and keyword extraction for all parent chunks"""
    
    print("="*70)
    print("SUMMARIZATION & KEYWORD EXTRACTION")
    print("="*70)
    
    # Check Ollama availability
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code != 200:
            print("✗ Ollama is not running! Start it with: ollama serve")
            return
        print(f"✓ Ollama is running at {OLLAMA_BASE_URL}")
    except Exception as e:
        print(f"✗ Cannot connect to Ollama: {e}")
        return
    
    # Fetch chunks to process
    print("\nFetching chunks without summaries/keywords...")
    chunks_to_process = fetch_chunks_without_summary(limit)
    
    if not chunks_to_process:
        print("✓ All parent chunks already have summaries!")
        
        # Check for keywords
        chunks_for_keywords = fetch_chunks_without_keywords(limit)
        if not chunks_for_keywords:
            print("✓ All parent chunks already have keywords!")
            return
        else:
            print(f"Found {len(chunks_for_keywords)} chunks without keywords")
            chunks_to_process = chunks_for_keywords
    
    print(f"Found {len(chunks_to_process)} parent chunks to process")
    print(f"Using {workers} workers for LLM calls\n")
    
    # Initialize statistics
    stats = SummaryStats()
    
    # Process chunks in parallel
    print("Processing chunks...")
    print("-"*70)
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_chunk, chunk, stats): chunk
            for chunk in chunks_to_process
        }
        
        for future in as_completed(futures):
            chunk = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"✗ Unexpected error for {chunk['chunk_id']}: {e}")
                stats.increment_failures()
    
    # Final statistics
    print("\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    
    final_stats = stats.get_stats()
    print(f"Total Processed:      {final_stats['total_processed']}")
    print(f"Summaries Generated:  {final_stats['summaries_generated']}")
    print(f"Keywords Extracted:   {final_stats['keywords_extracted']}")
    print(f"Failures:             {final_stats['failures']}")
    print(f"Time Elapsed:         {final_stats['elapsed_seconds']:.2f}s")
    print(f"Processing Rate:      {final_stats['rate_per_sec']:.2f} chunks/sec")
    
    # Verify database
    print("\n" + "="*70)
    print("DATABASE VERIFICATION")
    print("="*70)
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Count summaries
        cur.execute("""
            SELECT COUNT(*) as count
            FROM chunks_content
            WHERE summary IS NOT NULL AND summary != ''
        """)
        summary_count = cur.fetchone()['count']
        print(f"Chunks with summaries: {summary_count}")
        
        # Count keywords
        cur.execute("SELECT COUNT(DISTINCT chunk_id) as count FROM chunk_keywords")
        keyword_count = cur.fetchone()['count']
        print(f"Chunks with keywords:  {keyword_count}")
        
        # Total keywords
        cur.execute("SELECT COUNT(*) as count FROM chunk_keywords")
        total_keywords = cur.fetchone()['count']
        print(f"Total keywords:        {total_keywords}")
        
        # Sample summary
        cur.execute("""
            SELECT ci.chunk_id, cc.summary
            FROM chunks_identity ci
            JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE cc.summary IS NOT NULL AND cc.summary != ''
            LIMIT 1
        """)
        sample = cur.fetchone()
        if sample:
            print(f"\nSample Summary ({sample['chunk_id']}):")
            print(f"  {sample['summary']}")
        
        # Sample keywords
        cur.execute("""
            SELECT chunk_id, keyword
            FROM chunk_keywords
            WHERE chunk_id = %s
        """, (sample['chunk_id'] if sample else None,))
        keywords = cur.fetchall()
        if keywords:
            kw_list = [k['keyword'] for k in keywords]
            print(f"\nSample Keywords ({sample['chunk_id']}):")
            print(f"  {', '.join(kw_list)}")
        
        cur.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate summaries and keywords for chunks")
    parser.add_argument('--workers', type=int, default=MAX_WORKERS, 
                        help=f'Number of parallel workers (default: {MAX_WORKERS})')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of chunks to process (for testing)')
    
    args = parser.parse_args()
    
    run_summarization(workers=args.workers, limit=args.limit)
