import os
import json
import faiss
import numpy as np
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from db_config import get_db_connection

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b')
EMBEDDING_DIM = 1024  
VECTOR_DB_PATH = Path(__file__).parent / "vector_store"
INDEX_FILE = VECTOR_DB_PATH / "faiss_index.bin"
METADATA_FILE = VECTOR_DB_PATH / "metadata.json"

class GovernanceVectorDB:
    
    def __init__(self):
        self.index = None
        self.metadata = []  
        self.chunk_id_to_idx = {}
        
        VECTOR_DB_PATH.mkdir(exist_ok=True)
    
    def generate_embedding(self, text: str, max_retries: int = 3) -> Optional[np.ndarray]:
        import time
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/embeddings",
                    json={'model': EMBEDDING_MODEL, 'prompt': text},
                    timeout=60  
                )
                
                if response.status_code == 200:
                    embedding = response.json()['embedding']
                    return np.array(embedding, dtype=np.float32)
                elif response.status_code == 500:
                    print(f"[WARNING] Ollama 500 error (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2 ** attempt) 
                    continue
                else:
                    print(f"Ollama error: {response.status_code}")
                    return None
            
            except requests.exceptions.Timeout:
                print(f"[WARNING] Timeout (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)
                continue
            except Exception as e:
                print(f"Error generating embedding: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        
        print(f"Failed after {max_retries} attempts")
        return None
    
    def create_index(self):

        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        print(f"Created FAISS index (dim={EMBEDDING_DIM}, type=IndexFlatIP)")
    
    def load_index(self) -> bool:
        if INDEX_FILE.exists() and METADATA_FILE.exists():
            self.index = faiss.read_index(str(INDEX_FILE))
            
            with open(METADATA_FILE, 'r') as f:
                self.metadata = json.load(f)
            
            for idx, meta in enumerate(self.metadata):
                self.chunk_id_to_idx[meta['chunk_id']] = idx
            
            print(f"Loaded FAISS index: {len(self.metadata)} vectors")
            return True
        
        return False
    
    def save_index(self):
        faiss.write_index(self.index, str(INDEX_FILE))
        
        with open(METADATA_FILE, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        print(f"Saved FAISS index: {INDEX_FILE}")
        print(f"Saved metadata: {METADATA_FILE}")
    
    def add_chunk(self, chunk_id: str, text: str, metadata: Dict[str, Any]):
        embedding = self.generate_embedding(text)
        if embedding is None:
            return False
        
        faiss.normalize_L2(embedding.reshape(1, -1))
        
        self.index.add(embedding.reshape(1, -1))
        
        idx = len(self.metadata)
        self.metadata.append({
            'chunk_id': chunk_id,
            'idx': idx,
            **metadata
        })
        self.chunk_id_to_idx[chunk_id] = idx
        
        return True
    
    def batch_add_chunks(self, chunks: List[Dict]):
        """Add multiple chunks efficiently"""
        import time
        embeddings = []
        valid_chunks = []
        total = len(chunks)
        
        print(f"[INFO] Generating embeddings for {total} chunks...")
        print(f"PROGRESS:Embeddings:0", flush=True)
        
        for i, chunk in enumerate(chunks):
            if i % max(1, total // 20) == 0 or i % 10 == 0:
                progress = int(((i + 1) / total) * 100)
                print(f"PROGRESS:Embeddings:{progress}", flush=True)
            
            embedding = self.generate_embedding(chunk['text'])
            if embedding is not None:
                embeddings.append(embedding)
                valid_chunks.append(chunk)
                time.sleep(0.05)  
            else:
                print(f"[WARNING] Skipping chunk {chunk['chunk_id']} (embedding failed)")
        
        print(f"PROGRESS:Embeddings:100", flush=True)
        
        if not embeddings:
            print("[WARNING] No valid embeddings generated")
            return
        
        embeddings_matrix = np.vstack(embeddings).astype(np.float32)
        faiss.normalize_L2(embeddings_matrix)
        
        start_idx = len(self.metadata)
        self.index.add(embeddings_matrix)
        
        for i, chunk in enumerate(valid_chunks):
            idx = start_idx + i
            self.metadata.append({
                'chunk_id': chunk['chunk_id'],
                'idx': idx,
                'parent_id': chunk.get('parent_id'),
                'section': chunk.get('section'),
                'document_type': chunk.get('document_type'),
                'authority_level': chunk.get('authority_level'),
                'binding': chunk.get('binding'),
                'title': chunk.get('title'),
                'compliance_area': chunk.get('compliance_area')
            })
            self.chunk_id_to_idx[chunk['chunk_id']] = idx
        
        print(f"Added {len(valid_chunks)} chunks to index")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar chunks"""
        query_embedding = self.generate_embedding(query)
        if query_embedding is None:
            return []
        
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        scores, indices = self.index.search(query_embedding.reshape(1, -1), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['score'] = float(score)
                results.append(result)
        
        return results


def build_vector_database(sections: Optional[List[str]] = None, limit: Optional[int] = None):

    print("="*70)
    print("BUILDING GOVERNANCE VECTOR DATABASE")
    print("="*70)
    
    vdb = GovernanceVectorDB()
    
    if vdb.load_index():
        print(f"[INFO] Loaded existing index with {len(vdb.metadata)} vectors")
        print("[INFO] Adding new chunks to existing index...")
    else:
        print("[INFO] Creating new FAISS index...")
        vdb.create_index()
    
    print("\n[INFO] Fetching unembedded child chunks from PostgreSQL...")
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT 
                ci.chunk_id,
                ci.parent_chunk_id,
                ci.section,
                ci.document_type,
                ci.authority_level,
                ci.binding,
                cc.text,
                cc.title,
                cc.compliance_area
            FROM chunks_identity ci
            JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
            WHERE ci.chunk_role = 'child'
              AND cc.text IS NOT NULL
              AND LENGTH(cc.text) > 50
              AND (ce.embedded_at IS NULL OR ce.enabled = FALSE)
        """
        
        params = []
        if sections:
            query += " AND ci.section = ANY(%s)"
            params.append(sections)
        
        query += " ORDER BY ci.section, ci.chunk_id"
        
        cur.execute(query, params)
        chunks = cur.fetchall()
        cur.close()
    
    print(f"[INFO] Found {len(chunks)} new chunks to embed", flush=True)
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) 
                FROM chunk_embeddings 
                WHERE embedded_at IS NOT NULL AND enabled = TRUE
            """)
            already_embedded = cur.fetchone()[0]
            cur.close()
        
        if already_embedded > 0:
            print(f"[INFO] Skipping {already_embedded} already-embedded chunks (incremental mode)")
    except Exception as e:
        print(f"[WARNING] Could not count existing embeddings: {e}")
        already_embedded = 0
    
    if limit and len(chunks) > limit:
        print(f"[INFO] Limiting to first {limit} chunks for testing")
        chunks = chunks[:limit]
    
    if not chunks:
        print("[WARNING] No chunks to embed")
        return
    
    print(f"[INFO] Preparing chunk data...")
    chunk_data = []
    try:
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                'chunk_id': chunk['chunk_id'],
                'parent_id': chunk['parent_chunk_id'],
                'section': chunk['section'],
                'document_type': chunk['document_type'],
                'authority_level': chunk['authority_level'],
                'binding': chunk['binding'],
                'text': chunk['text'],
                'title': chunk['title'],
                'compliance_area': chunk['compliance_area']
            })
        print(f"[INFO] Prepared {len(chunk_data)} chunks for embedding", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to prepare chunk data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[INFO] Building FAISS index...", flush=True)
    vdb.batch_add_chunks(chunk_data)
    
    print(f"\n[INFO] Saving vector database...")
    vdb.save_index()
    
    print(f"\n[INFO] Updating embedding status in PostgreSQL...")
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        for chunk in chunk_data:
            cur.execute("""
                UPDATE chunk_embeddings
                SET 
                    enabled = TRUE,
                    model = %s,
                    vector_id = %s,
                    embedded_at = %s
                WHERE chunk_id = %s
            """, (
                EMBEDDING_MODEL,
                chunk['chunk_id'],
                datetime.now(),
                chunk['chunk_id']
            ))
        
        cur.close()
    
    print("\n" + "="*70)
    print("VECTOR DATABASE BUILD COMPLETE")
    print("="*70)
    print(f"[INFO] Total vectors: {len(vdb.metadata)}")
    print(f"[INFO] Index file: {INDEX_FILE}")
    print(f"[INFO] Metadata file: {METADATA_FILE}")
    print(f"[INFO] Ready for semantic search")
    print("="*70)
    print("STAGE:Completed", flush=True)


def test_search(query: str, top_k: int = 3):
    vdb = GovernanceVectorDB()
    
    if not vdb.load_index():
        print("No index found. Run build_vector_database() first.")
        return
    
    print(f"\n[SEARCH] Searching: '{query}'")
    print("="*70)
    
    results = vdb.search(query, top_k)
    
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] Score: {result['score']:.4f}")
        print(f"    Chunk: {result['chunk_id']}")
        print(f"    Section: {result['section']}")
        print(f"    Type: {result['document_type']} | {result['authority_level']}")
        print(f"    Area: {result['compliance_area']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Build FAISS vector database')
    parser.add_argument('--sections', nargs='+', help='Specific sections to embed')
    parser.add_argument('--limit', type=int, help='Limit number of chunks to embed')
    parser.add_argument('--test', type=str, help='Test search with query')
    
    args = parser.parse_args()
    
    if args.test:
        test_search(args.test)
    else:
        build_vector_database(sections=args.sections, limit=args.limit)
