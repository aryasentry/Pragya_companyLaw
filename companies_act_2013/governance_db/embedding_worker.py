"""
Embedding worker - generates vector embeddings for child chunks ONLY
Parent chunks are NEVER embedded (stored as metadata)
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from db_config import get_db_connection

# Lazy import for performance
_embedding_model = None
_embedding_dimension = None

def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model, _embedding_dimension
    
    if _embedding_model is None:
        # Use Ollama for embeddings
        import requests
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model_name = os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b')
        
        # Test Ollama connection
        try:
            response = requests.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                _embedding_model = 'ollama'
                _embedding_dimension = 1024  # qwen3-embedding:0.6b dimension
                print(f"Loaded Ollama embedding model: {model_name} (dim={_embedding_dimension})")
            else:
                raise ConnectionError("Ollama server not responding")
        except Exception as e:
            print(f"Failed to connect to Ollama: {e}")
            raise
    
    return _embedding_model

def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding vector for text using Ollama"""
    model = get_embedding_model()
    
    try:
        import requests
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model_name = os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b')
        
        response = requests.post(
            f"{ollama_url}/api/embeddings",
            json={
                'model': model_name,
                'prompt': text
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['embedding']
        else:
            print(f"Ollama API error: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def embed_child_chunks(parent_chunk_id: str, model_name: Optional[str] = None) -> tuple[bool, str, int]:
    """
    Generate embeddings for all child chunks of a parent
    Only processes chunks where embeddings are enabled
    
    Args:
        parent_chunk_id: Parent chunk identifier
        model_name: Override default embedding model
    
    Returns:
        (success, message, count of embedded chunks)
    """
    try:
        # Get all child chunks
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ci.chunk_id, cc.text, ce.enabled
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    WHERE ci.parent_chunk_id = %s
                      AND ci.chunk_role = 'child'
                      AND ce.enabled = TRUE
                      AND cc.text IS NOT NULL
                """, (parent_chunk_id,))
                
                child_chunks = cursor.fetchall()
        
        if not child_chunks:
            return True, "No child chunks to embed", 0
        
        # Generate embeddings
        embedded_count = 0
        model = get_embedding_model()
        model_name = model_name or os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for chunk in child_chunks:
                    chunk_id = chunk['chunk_id']
                    text = chunk['text']
                    
                    # Generate embedding
                    embedding = generate_embedding(text)
                    if embedding is None:
                        print(f"Failed to embed chunk {chunk_id}")
                        continue
                    
                    # Store embedding
                    cursor.execute("""
                        UPDATE chunk_embeddings
                        SET 
                            model_name = %s,
                            vector_id = %s,
                            embedding_dimension = %s,
                            generated_at = %s
                        WHERE chunk_id = %s
                    """, (
                        model_name,
                        f"{chunk_id}_embedding",
                        len(embedding),
                        datetime.now(),
                        chunk_id
                    ))
                    
                    # TODO: Store actual vector in FAISS index
                    # FAISS is already installed and optimal for this use case
                    # Vector will be stored with chunk_id as key for fast retrieval
                    
                    embedded_count += 1
        
        return True, f"Embedded {embedded_count} child chunks", embedded_count
    
    except Exception as e:
        return False, f"Embedding error: {str(e)}", 0

def embed_single_chunk(chunk_id: str, force: bool = False) -> tuple[bool, str]:
    """
    Embed a single chunk (child only)
    
    Args:
        chunk_id: Chunk identifier
        force: Re-embed even if already embedded
    
    Returns:
        (success, message)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Verify chunk is a child and embedding is enabled
                cursor.execute("""
                    SELECT ci.chunk_role, cc.text, ce.enabled, ce.vector_id
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    WHERE ci.chunk_id = %s
                """, (chunk_id,))
                
                result = cursor.fetchone()
                if not result:
                    return False, f"Chunk not found: {chunk_id}"
                
                chunk_data = dict(result)
                
                # Validate
                if chunk_data['chunk_role'] != 'child':
                    return False, "Only child chunks can be embedded"
                
                if not chunk_data['enabled']:
                    return False, "Embeddings disabled for this chunk"
                
                if not chunk_data['text']:
                    return False, "No text to embed"
                
                if chunk_data['vector_id'] and not force:
                    return False, "Chunk already embedded (use force=True to re-embed)"
                
                # Generate embedding
                embedding = generate_embedding(chunk_data['text'])
                if embedding is None:
                    return False, "Failed to generate embedding"
                
                # Store embedding metadata
                model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
                cursor.execute("""
                    UPDATE chunk_embeddings
                    SET 
                        model_name = %s,
                        vector_id = %s,
                        embedding_dimension = %s,
                        generated_at = %s
                    WHERE chunk_id = %s
                """, (
                    model_name,
                    f"{chunk_id}_embedding",
                    len(embedding),
                    datetime.now(),
                    chunk_id
                ))
        
        return True, f"Successfully embedded chunk: {chunk_id}"
    
    except Exception as e:
        return False, f"Embedding error: {str(e)}"

def get_unembed_chunks(limit: int = 100) -> List[Dict[str, Any]]:
    """Get child chunks that need embedding"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ci.chunk_id, cc.text, ci.parent_chunk_id
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    WHERE ci.chunk_role = 'child'
                      AND ce.enabled = TRUE
                      AND ce.vector_id IS NULL
                      AND cc.text IS NOT NULL
                    LIMIT %s
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching unembedded chunks: {e}")
        return []

def batch_embed_pending(batch_size: int = 50) -> tuple[bool, str, int]:
    """
    Background worker to embed all pending chunks
    
    Args:
        batch_size: Number of chunks to process in one batch
    
    Returns:
        (success, message, total embedded)
    """
    pending = get_unembed_chunks(limit=batch_size)
    if not pending:
        return True, "No pending chunks to embed", 0
    
    total_embedded = 0
    for chunk in pending:
        success, msg = embed_single_chunk(chunk['chunk_id'])
        if success:
            total_embedded += 1
        else:
            print(f"Failed to embed {chunk['chunk_id']}: {msg}")
    
    return True, f"Embedded {total_embedded}/{len(pending)} chunks", total_embedded
