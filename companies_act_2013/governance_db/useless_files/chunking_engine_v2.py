"""
Hierarchical chunking engine - splits parent text into child chunks
Respects parent-child relationships with overlap for context preservation
"""
import re
from typing import List, Dict, Any, Optional
from ingestion_service import generate_chunk_id, update_chunk_text
from db_config import get_db_connection
from datetime import datetime

def hierarchical_chunk(
    parent_chunk_id: str,
    text: str,
    max_chars: int = 1000,
    overlap: int = 100,
    created_by: str = 'system'
) -> tuple[bool, str, List[str]]:
    """
    Split long text into overlapping child chunks
    
    Args:
        parent_chunk_id: Parent chunk identifier
        text: Full text to split
        max_chars: Maximum characters per child chunk
        overlap: Overlap characters between consecutive chunks
        created_by: Username of creator
    
    Returns:
        (success, message, list of child chunk IDs)
    """
    # If text fits in one chunk, no splitting needed
    if len(text) <= max_chars:
        return True, "Text fits in single chunk, no splitting required", []
    
    # First, update parent chunk text
    success, msg = update_chunk_text(parent_chunk_id, text, updated_by=created_by)
    if not success:
        return False, f"Failed to update parent text: {msg}", []
    
    # Get parent chunk metadata
    parent_metadata = _get_parent_metadata(parent_chunk_id)
    if not parent_metadata:
        return False, f"Parent chunk not found: {parent_chunk_id}", []
    
    # Split text into sentences for better boundary detection
    sentences = _split_into_sentences(text)
    
    # Create child chunks with overlap
    child_chunks = []
    current_chunk = ""
    overlap_buffer = ""
    chunk_index = 0
    
    for sentence in sentences:
        # Check if adding sentence exceeds limit
        if len(current_chunk) + len(sentence) > max_chars and current_chunk:
            # Save current chunk
            child_chunks.append({
                'text': current_chunk.strip(),
                'index': chunk_index
            })
            
            # Calculate overlap for next chunk
            overlap_buffer = _get_overlap_text(current_chunk, overlap)
            current_chunk = overlap_buffer + " " + sentence
            chunk_index += 1
        else:
            current_chunk += " " + sentence
    
    # Add last chunk if not empty
    if current_chunk.strip():
        child_chunks.append({
            'text': current_chunk.strip(),
            'index': chunk_index
        })
    
    # Insert child chunks into database
    child_ids = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for chunk_data in child_chunks:
                    child_id = generate_chunk_id()
                    
                    # 1️⃣ Insert into chunks_identity
                    cursor.execute("""
                        INSERT INTO chunks_identity (
                            chunk_id, chunk_role, parent_chunk_id, document_type,
                            authority_level, binding, act, section, sub_section
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        child_id,
                        'child',
                        parent_chunk_id,
                        parent_metadata['document_type'],
                        parent_metadata['authority_level'],
                        parent_metadata['binding'],
                        parent_metadata['act'],
                        parent_metadata['section'],
                        parent_metadata['sub_section']
                    ))
                    
                    # 2️⃣ Insert into chunks_content
                    cursor.execute("""
                        INSERT INTO chunks_content (chunk_id, text)
                        VALUES (%s, %s)
                    """, (child_id, chunk_data['text']))
                    
                    # 3️⃣ Insert into chunk_lifecycle
                    cursor.execute("""
                        INSERT INTO chunk_lifecycle (chunk_id, status)
                        VALUES (%s, %s)
                    """, (child_id, 'DRAFT'))
                    
                    # 4️⃣ Copy retrieval rules from parent
                    cursor.execute("""
                        INSERT INTO chunk_retrieval_rules (chunk_id, priority, requires_parent_law)
                        SELECT %s, priority, requires_parent_law
                        FROM chunk_retrieval_rules
                        WHERE chunk_id = %s
                    """, (child_id, parent_chunk_id))
                    
                    # 5️⃣ Copy refusal policy from parent
                    cursor.execute("""
                        INSERT INTO chunk_refusal_policy (
                            chunk_id, can_answer_standalone, must_reference_parent_law, refuse_if_parent_missing
                        )
                        SELECT %s, can_answer_standalone, must_reference_parent_law, refuse_if_parent_missing
                        FROM chunk_refusal_policy
                        WHERE chunk_id = %s
                    """, (child_id, parent_chunk_id))
                    
                    # 6️⃣ Copy administrative data
                    cursor.execute("""
                        INSERT INTO chunk_administrative (chunk_id, issued_by, notification_number, source_type, document_language)
                        SELECT %s, issued_by, notification_number, source_type, document_language
                        FROM chunk_administrative
                        WHERE chunk_id = %s
                    """, (child_id, parent_chunk_id))
                    
                    # 7️⃣ Insert audit entry
                    cursor.execute("""
                        INSERT INTO chunk_audit (chunk_id, uploaded_by, uploaded_at)
                        VALUES (%s, %s, %s)
                    """, (child_id, created_by, datetime.now()))
                    
                    # 8️⃣ Copy source information
                    cursor.execute("""
                        INSERT INTO chunk_source (chunk_id, path, url)
                        SELECT %s, path, url
                        FROM chunk_source
                        WHERE chunk_id = %s
                    """, (child_id, parent_chunk_id))
                    
                    # 9️⃣ Enable embeddings for child chunks
                    cursor.execute("""
                        INSERT INTO chunk_embeddings (chunk_id, enabled)
                        VALUES (%s, %s)
                    """, (child_id, True))  # Child chunks ARE embedded
                    
                    # 🔟 Create parent-child relationship
                    cursor.execute("""
                        INSERT INTO chunk_relationships (
                            from_chunk_id, to_chunk_id, relationship
                        ) VALUES (%s, %s, %s)
                    """, (parent_chunk_id, child_id, 'part_of'))
                    
                    # 1️⃣1️⃣ Link siblings (sequential relationship)
                    if child_ids:  # If there's a previous child
                        cursor.execute("""
                            INSERT INTO chunk_relationships (
                                from_chunk_id, to_chunk_id, relationship
                            ) VALUES (%s, %s, %s)
                        """, (child_ids[-1], child_id, 'precedes'))
                    
                    child_ids.append(child_id)
        
        return True, f"Created {len(child_ids)} child chunks", child_ids
    
    except Exception as e:
        return False, f"Database error: {str(e)}", []

def _get_parent_metadata(parent_chunk_id: str) -> Optional[Dict[str, Any]]:
    """Fetch parent chunk metadata"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT document_type, authority_level, binding, act, section, sub_section
                    FROM chunks_identity
                    WHERE chunk_id = %s
                """, (parent_chunk_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
    except Exception as e:
        print(f"Error fetching parent metadata: {e}")
        return None

def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex"""
    # Split on periods, exclamation marks, question marks followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def _get_overlap_text(text: str, overlap_chars: int) -> str:
    """Get last N characters of text for overlap"""
    if len(text) <= overlap_chars:
        return text
    
    # Try to cut at word boundary
    overlap = text[-overlap_chars:]
    first_space = overlap.find(' ')
    if first_space != -1:
        return overlap[first_space:].strip()
    return overlap

def get_child_chunks(parent_chunk_id: str) -> List[Dict[str, Any]]:
    """Retrieve all child chunks for a given parent"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ci.chunk_id, cc.text, ce.enabled as embeddings_enabled
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    WHERE ci.parent_chunk_id = %s
                    ORDER BY ci.chunk_id
                """, (parent_chunk_id,))
                return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error retrieving child chunks: {e}")
        return []
