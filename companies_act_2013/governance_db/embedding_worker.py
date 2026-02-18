import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from db_config import get_db_connection

_embedding_model = None
_embedding_dimension = None

def get_embedding_model():
    global _embedding_model, _embedding_dimension
    
    if _embedding_model is None:

        import requests
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model_name = os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b')
        
        try:
            response = requests.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                _embedding_model = 'ollama'
                _embedding_dimension = 1024
                print(f"Loaded Ollama embedding model: {model_name} (dim={_embedding_dimension})")
            else:
                raise ConnectionError("Ollama server not responding")
        except Exception as e:
            print(f"Failed to connect to Ollama: {e}")
            raise
    
    return _embedding_model

def generate_embedding(text: str) -> Optional[List[float]]:
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
    try:

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
                        UPDATE chunk_embeddings
                        SET 
                            model_name = %s,
                            vector_id = %s,
                            embedding_dimension = %s,
                            generated_at = %s
                        WHERE chunk_id = %s
    Embed a single chunk (child only)
    
    Args:
        chunk_id: Chunk identifier
        force: Re-embed even if already embedded
    
    Returns:
        (success, message)
                    SELECT ci.chunk_role, cc.text, ce.enabled, ce.vector_id
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    WHERE ci.chunk_id = %s
                    UPDATE chunk_embeddings
                    SET 
                        model_name = %s,
                        vector_id = %s,
                        embedding_dimension = %s,
                        generated_at = %s
                    WHERE chunk_id = %s
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
    Background worker to embed all pending chunks
    
    Args:
        batch_size: Number of chunks to process in one batch
    
    Returns:
        (success, message, total embedded)