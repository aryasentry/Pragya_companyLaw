"""
Simplified hierarchical chunking for batch ingestion
Splits parent text into child chunks with structured IDs
"""
import re
from typing import List
from db_config import get_db_connection
from datetime import datetime

def generate_child_chunk_id(parent_id: str, index: int) -> str:
    """
    Generate child chunk ID based on parent ID
    
    Example: ca2013_act_s001 -> ca2013_act_s001_c1
    
    Args:
        parent_id: Parent chunk ID (e.g., ca2013_act_s001)
        index: Child chunk index (1-based)
    
    Returns:
        Child chunk ID
    """
    return f"{parent_id}_c{index}"

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    # Simple sentence splitting (can be improved with nltk)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def hierarchical_chunk(
    parent_chunk_id: str,
    text: str,
    max_chars: int = 1000,
    overlap_chars: int = 100
) -> List[str]:
    """
    Split long text into overlapping child chunks with structured IDs
    
    Args:
        parent_chunk_id: Parent chunk identifier (e.g., ca2013_act_s001)
        text: Full text to split
        max_chars: Maximum characters per child chunk
        overlap_chars: Overlap characters between consecutive chunks
    
    Returns:
        List of child chunk IDs created
    """
    # If text is short, no child chunks needed
    if len(text) <= max_chars:
        return []
    
    # Get parent metadata for child chunks
    parent_metadata = get_parent_metadata(parent_chunk_id)
    if not parent_metadata:
        print(f"Warning: Parent chunk {parent_chunk_id} not found in database")
        return []
    
    # Split text into sentences
    sentences = split_into_sentences(text)
    
    # Create child chunks
    child_chunk_ids = []
    child_index = 1
    current_chunk = ""
    overlap_buffer = ""
    
    for sentence in sentences:
        # Add sentence to current chunk
        if current_chunk:
            current_chunk += " " + sentence
        else:
            current_chunk = sentence
        
        # Check if chunk exceeds max size
        if len(current_chunk) >= max_chars:
            # Create child chunk
            child_id = create_child_chunk(
                parent_chunk_id=parent_chunk_id,
                child_index=child_index,
                text=current_chunk,
                parent_metadata=parent_metadata
            )
            
            if child_id:
                child_chunk_ids.append(child_id)
                
                # Create relationship: child part_of parent
                create_relationship(child_id, parent_chunk_id, 'part_of')
                
                # Create relationship: child precedes next child (will be added later)
                if child_index > 1:
                    prev_child_id = child_chunk_ids[-2]
                    create_relationship(prev_child_id, child_id, 'precedes')
                
                # Prepare overlap for next chunk
                overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
                current_chunk = overlap_text
                child_index += 1
            else:
                print(f"Failed to create child chunk {child_index}")
                break
    
    # Handle remaining text
    if len(current_chunk.strip()) > overlap_chars:
        child_id = create_child_chunk(
            parent_chunk_id=parent_chunk_id,
            child_index=child_index,
            text=current_chunk,
            parent_metadata=parent_metadata
        )
        
        if child_id:
            child_chunk_ids.append(child_id)
            create_relationship(child_id, parent_chunk_id, 'part_of')
            
            if child_index > 1:
                prev_child_id = child_chunk_ids[-2]
                create_relationship(prev_child_id, child_id, 'precedes')
    
    return child_chunk_ids

def get_parent_metadata(parent_chunk_id: str) -> dict:
    """Get parent chunk metadata"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    i.document_type,
                    i.authority_level,
                    i.binding,
                    i.section,
                    c.title,
                    c.compliance_area,
                    r.priority,
                    r.requires_parent_law,
                    rp.can_answer_standalone,
                    rp.must_reference_parent_law,
                    rp.refuse_if_parent_missing
                FROM chunks_identity i
                JOIN chunks_content c ON i.chunk_id = c.chunk_id
                JOIN chunk_retrieval_rules r ON i.chunk_id = r.chunk_id
                JOIN chunk_refusal_policy rp ON i.chunk_id = rp.chunk_id
                WHERE i.chunk_id = %s
            """, (parent_chunk_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None

def create_child_chunk(
    parent_chunk_id: str,
    child_index: int,
    text: str,
    parent_metadata: dict
) -> str:
    """Create a child chunk with structured ID"""
    child_id = generate_child_chunk_id(parent_chunk_id, child_index)
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. chunks_identity
            cursor.execute("""
                INSERT INTO chunks_identity (
                    chunk_id, chunk_role, parent_chunk_id, document_type,
                    authority_level, binding, section
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    chunk_role = EXCLUDED.chunk_role,
                    parent_chunk_id = EXCLUDED.parent_chunk_id,
                    document_type = EXCLUDED.document_type,
                    authority_level = EXCLUDED.authority_level,
                    binding = EXCLUDED.binding,
                    section = EXCLUDED.section
            """, (
                child_id,
                'child',
                parent_chunk_id,
                parent_metadata['document_type'],
                parent_metadata['authority_level'],
                parent_metadata['binding'],
                parent_metadata['section']
            ))
            
            # 2. chunks_content
            cursor.execute("""
                INSERT INTO chunks_content (
                    chunk_id, title, compliance_area, text
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    compliance_area = EXCLUDED.compliance_area,
                    text = EXCLUDED.text
            """, (
                child_id,
                parent_metadata.get('title'),
                parent_metadata.get('compliance_area'),
                text
            ))
            
            # 3. chunk_retrieval_rules
            cursor.execute("""
                INSERT INTO chunk_retrieval_rules (
                    chunk_id, priority, requires_parent_law
                ) VALUES (%s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    priority = EXCLUDED.priority,
                    requires_parent_law = EXCLUDED.requires_parent_law
            """, (
                child_id,
                parent_metadata['priority'],
                parent_metadata.get('requires_parent_law', False)
            ))
            
            # 4. chunk_refusal_policy
            cursor.execute("""
                INSERT INTO chunk_refusal_policy (
                    chunk_id, can_answer_standalone, must_reference_parent_law,
                    refuse_if_parent_missing
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    can_answer_standalone = EXCLUDED.can_answer_standalone,
                    must_reference_parent_law = EXCLUDED.must_reference_parent_law,
                    refuse_if_parent_missing = EXCLUDED.refuse_if_parent_missing
            """, (
                child_id,
                parent_metadata['can_answer_standalone'],
                parent_metadata['must_reference_parent_law'],
                parent_metadata['refuse_if_parent_missing']
            ))
            
            # 5. chunk_lifecycle
            cursor.execute("""
                INSERT INTO chunk_lifecycle (chunk_id, status)
                VALUES (%s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    status = EXCLUDED.status
            """, (child_id, 'ACTIVE'))
            
            # 6. chunk_versioning
            cursor.execute("""
                INSERT INTO chunk_versioning (
                    chunk_id, version
                ) VALUES (%s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    version = EXCLUDED.version
            """, (child_id, '1.0'))
            
            # 7. chunk_lineage
            cursor.execute("""
                INSERT INTO chunk_lineage (chunk_id)
                VALUES (%s)
                ON CONFLICT (chunk_id) DO NOTHING
            """, (child_id,))
            
            # 8. chunk_administrative
            cursor.execute("""
                INSERT INTO chunk_administrative (chunk_id)
                VALUES (%s)
                ON CONFLICT (chunk_id) DO NOTHING
            """, (child_id,))
            
            # 9. chunk_audit
            cursor.execute("""
                INSERT INTO chunk_audit (chunk_id)
                VALUES (%s)
                ON CONFLICT (chunk_id) DO NOTHING
            """, (child_id,))
            
            # 10. chunk_source
            cursor.execute("""
                INSERT INTO chunk_source (chunk_id)
                VALUES (%s)
                ON CONFLICT (chunk_id) DO NOTHING
            """, (child_id,))
            
            # 11. chunk_temporal
            cursor.execute("""
                INSERT INTO chunk_temporal (chunk_id)
                VALUES (%s)
                ON CONFLICT (chunk_id) DO NOTHING
            """, (child_id,))
            
            # 12. chunk_embeddings (enabled for children)
            cursor.execute("""
                INSERT INTO chunk_embeddings (
                    chunk_id, enabled
                ) VALUES (%s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    enabled = EXCLUDED.enabled
            """, (child_id, True))
            
            conn.commit()
    
    return child_id

def create_relationship(from_chunk_id: str, to_chunk_id: str, relationship_type: str):
    """Create a relationship between chunks"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chunk_relationships (
                    from_chunk_id, to_chunk_id, relationship, created_at
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (from_chunk_id, relationship, to_chunk_id) DO UPDATE SET
                    created_at = EXCLUDED.created_at
            """, (from_chunk_id, to_chunk_id, relationship_type, datetime.now()))
            
            conn.commit()
