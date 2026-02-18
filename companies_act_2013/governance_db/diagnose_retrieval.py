"""
Diagnose RAG Retrieval Issues
Check database, FAISS, and retrieval pipeline
"""
from db_config import get_db_connection
import os
import numpy as np

def check_database():
    """Check if database has chunks"""
    print("=" * 70)
    print("1. CHECKING DATABASE")
    print("=" * 70)
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Check total chunks
            cursor.execute("SELECT COUNT(*) as count FROM chunks_identity")
            total = cursor.fetchone()['count']
            print(f"✓ Total chunks in database: {total}")
            
            if total == 0:
                print("❌ DATABASE IS EMPTY! No chunks found.")
                print("   You need to ingest documents first.")
                return False
            
            # Check parent chunks
            cursor.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'parent'")
            parents = cursor.fetchone()['count']
            print(f"✓ Parent chunks: {parents}")
            
            # Check child chunks
            cursor.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'child'")
            children = cursor.fetchone()['count']
            print(f"✓ Child chunks: {children}")
            
            # Check embeddings
            cursor.execute("SELECT COUNT(*) as count FROM chunk_embeddings WHERE enabled = true")
            embedded = cursor.fetchone()['count']
            print(f"✓ Chunks with embeddings enabled: {embedded}")
            
            # Check sample sections
            cursor.execute("""
                SELECT DISTINCT section 
                FROM chunks_identity 
                WHERE section IS NOT NULL 
                ORDER BY section 
                LIMIT 10
            """)
            sections = cursor.fetchall()
            print(f"✓ Sample sections: {', '.join([s['section'] for s in sections])}")
            
            # Check Section 149 specifically
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM chunks_identity 
                WHERE section = '149'
            """)
            s149 = cursor.fetchone()['count']
            print(f"✓ Section 149 chunks: {s149}")
            
            if s149 == 0:
                print("⚠️  Section 149 not found - independent director query will fail!")
            
            print()
            return True

def check_faiss_index():
    """Check if FAISS index exists and is valid"""
    print("=" * 70)
    print("2. CHECKING FAISS INDEX")
    print("=" * 70)
    
    index_path = "faiss_index.bin"
    metadata_path = "faiss_metadata.pkl"
    
    if not os.path.exists(index_path):
        print(f"❌ FAISS index not found: {index_path}")
        print("   You need to build the FAISS index first.")
        return False
    
    print(f"✓ FAISS index exists: {index_path}")
    print(f"  Size: {os.path.getsize(index_path) / 1024:.2f} KB")
    
    if not os.path.exists(metadata_path):
        print(f"❌ FAISS metadata not found: {metadata_path}")
        return False
    
    print(f"✓ FAISS metadata exists: {metadata_path}")
    print(f"  Size: {os.path.getsize(metadata_path) / 1024:.2f} KB")
    
    # Try to load FAISS index
    try:
        import faiss
        import pickle
        
        index = faiss.read_index(index_path)
        print(f"✓ FAISS index loaded successfully")
        print(f"  Vectors in index: {index.ntotal}")
        print(f"  Vector dimension: {index.d}")
        
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        print(f"✓ Metadata loaded successfully")
        print(f"  Chunk IDs in metadata: {len(metadata)}")
        
        if index.ntotal == 0:
            print("❌ FAISS index is EMPTY! No vectors found.")
            return False
        
        if index.ntotal != len(metadata):
            print(f"⚠️  Mismatch: {index.ntotal} vectors but {len(metadata)} metadata entries")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error loading FAISS index: {e}")
        return False

def check_ollama():
    """Check if Ollama is running"""
    print("=" * 70)
    print("3. CHECKING OLLAMA")
    print("=" * 70)
    
    import requests
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama is running")
            print(f"  Available models: {len(models)}")
            
            # Check for required models
            model_names = [m['name'] for m in models]
            
            if 'qwen2.5:1.5b' in model_names:
                print("  ✓ LLM model (qwen2.5:1.5b) found")
            else:
                print("  ⚠️  LLM model (qwen2.5:1.5b) NOT found")
            
            if 'nomic-embed-text' in model_names or 'qwen3-embedding:0.6b' in model_names:
                print("  ✓ Embedding model found")
            else:
                print("  ⚠️  Embedding model NOT found")
            
            print()
            return True
        else:
            print(f"❌ Ollama returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama at http://localhost:11434")
        print("   Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def test_embedding_generation():
    """Test if embeddings can be generated"""
    print("=" * 70)
    print("4. TESTING EMBEDDING GENERATION")
    print("=" * 70)
    
    import requests
    
    try:
        test_text = "What are the requirements for appointing an independent director?"
        
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                'model': 'qwen3-embedding:0.6b',
                'prompt': test_text
            },
            timeout=10
        )
        
        if response.status_code == 200:
            embedding = response.json().get('embedding', [])
            print(f"✓ Embedding generated successfully")
            print(f"  Dimension: {len(embedding)}")
            print(f"  Sample values: {embedding[:5]}")
            print()
            return True
        else:
            print(f"❌ Embedding generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return False

def test_vector_search():
    """Test if vector search works"""
    print("=" * 70)
    print("5. TESTING VECTOR SEARCH")
    print("=" * 70)
    
    try:
        from retrieval_service_faiss import RetrievalServiceFAISS
        
        retriever = RetrievalServiceFAISS()
        print("✓ Retrieval service initialized")
        
        # Test query
        query = "independent director"
        print(f"\nTesting query: '{query}'")
        
        # Generate embedding
        import requests
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                'model': 'qwen3-embedding:0.6b',
                'prompt': query
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to generate embedding for query")
            return False
        
        query_embedding = np.array(response.json()['embedding'], dtype='float32')
        print(f"✓ Query embedding generated: dimension {len(query_embedding)}")
        
        # Search FAISS
        import faiss
        import pickle
        
        index = faiss.read_index("faiss_index.bin")
        with open("faiss_metadata.pkl", 'rb') as f:
            metadata = pickle.load(f)
        
        query_vector = query_embedding.reshape(1, -1)
        distances, indices = index.search(query_vector, 15)
        
        print(f"✓ Vector search completed")
        print(f"  Found {len(indices[0])} results")
        print(f"  Top 5 similarity scores: {distances[0][:5]}")
        
        # Get chunk IDs
        chunk_ids = [metadata[idx] for idx in indices[0] if idx < len(metadata)]
        print(f"  Chunk IDs: {chunk_ids[:5]}")
        
        if len(chunk_ids) == 0:
            print("❌ No chunks found in vector search!")
            return False
        
        # Check if chunks exist in database
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT chunk_id, section, title
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    WHERE ci.chunk_id = ANY(%s)
                    LIMIT 5
                """, (chunk_ids[:5],))
                results = cursor.fetchall()
                
                print(f"\n✓ Found {len(results)} chunks in database:")
                for r in results:
                    print(f"  - {r['chunk_id']}: Section {r['section']} - {r['title']}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error in vector search: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostics"""
    print("\n" + "=" * 70)
    print("RAG RETRIEVAL DIAGNOSTICS")
    print("=" * 70)
    print()
    
    results = {
        'database': check_database(),
        'faiss': check_faiss_index(),
        'ollama': check_ollama(),
        'embedding': test_embedding_generation(),
        'search': test_vector_search()
    }
    
    print("=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component.upper()}: {'PASS' if status else 'FAIL'}")
    
    print()
    
    if all(results.values()):
        print("✅ ALL CHECKS PASSED!")
        print("   The system should be working. Check Flask logs for errors.")
    else:
        print("❌ SOME CHECKS FAILED!")
        print("\nRECOMMENDED ACTIONS:")
        
        if not results['database']:
            print("1. Ingest documents: python pipeline_full.py")
        if not results['faiss']:
            print("2. Build FAISS index: python build_faiss_index.py")
        if not results['ollama']:
            print("3. Start Ollama: ollama serve")
        if not results['embedding']:
            print("4. Pull embedding model: ollama pull qwen3-embedding:0.6b")
    
    print()

if __name__ == '__main__':
    main()
