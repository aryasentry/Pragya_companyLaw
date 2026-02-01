"""
Simplified ingestion service for batch processing
Uses structured chunk naming like ca2013_act_s001
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from db_config import get_db_connection
from governance_rules import (
    get_binding_status,
    get_retrieval_priority,
    get_authority_level,
    get_refusal_policy,
    requires_parent_law
)

def generate_structured_chunk_id(
    document_type: str,
    section_number: Optional[str] = None,
    sub_section: Optional[str] = None,
    index: Optional[int] = None,
    file_ext: Optional[str] = None
) -> str:
    """
    Generate structured chunk ID following pattern from final_chunks.json
    
    Examples:
        ca2013_act_s001_html (parent for section 1 HTML file)
        ca2013_act_s001_txt (parent for section 1 TXT file)
        ca2013_circular_s001_pdf1 (first PDF circular)
        ca2013_circular_s001_pdf1_c1 (child chunk 1 of first PDF)
    
    Args:
        document_type: Type of document (act, circular, notification, etc.)
        section_number: Section number (e.g., '001', '042')
        sub_section: Subsection identifier
        index: Child chunk index
        file_ext: File extension (html, txt, pdf) for disambiguating multiple files
    
    Returns:
        Structured chunk ID
    """
    # Base: statute code + document type
    parts = ['ca2013', document_type]
    
    # Add section if provided
    if section_number:
        parts.append(f's{section_number}')
    
    # Add subsection if provided
    if sub_section:
        parts.append(f'ss{sub_section}')
    
    # Add file extension if provided (to handle multiple files)
    if file_ext:
        parts.append(file_ext)
    
    # Add index if provided (for child chunks)
    if index is not None:
        parts.append(f'c{index}')
    
    return '_'.join(parts)

def create_parent_chunk_simple(
    document_type: str,
    title: Optional[str] = None,
    section_number: Optional[str] = None,
    compliance_area: Optional[str] = None,
    citation: Optional[str] = None,
    file_ext: Optional[str] = None,
    **kwargs
) -> str:
    """
    Simplified parent chunk creation for batch ingestion
    
    Args:
        document_type: Type of document (required)
        title: Document title
        section_number: Section number for structured ID
        compliance_area: Compliance area
        citation: Source citation
        file_ext: File extension (html, txt, pdf) to disambiguate multiple files
        **kwargs: Additional optional fields
    
    Returns:
        chunk_id of created parent chunk
    """
    # Generate structured chunk ID
    chunk_id = generate_structured_chunk_id(
        document_type=document_type,
        section_number=section_number,
        file_ext=file_ext
    )
    
    # Apply governance rules
    binding = get_binding_status(document_type)
    priority = get_retrieval_priority(document_type)
    authority_level = get_authority_level(document_type)
    refusal_policy = get_refusal_policy(document_type, priority)
    requires_parent = requires_parent_law(priority)
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. Insert into chunks_identity
            cursor.execute("""
                INSERT INTO chunks_identity (
                    chunk_id, chunk_role, parent_chunk_id, document_type,
                    authority_level, binding, section
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                chunk_id,
                'parent',
                None,
                document_type,
                authority_level,
                binding,
                section_number
            ))
            
            # 2. Insert into chunks_content
            cursor.execute("""
                INSERT INTO chunks_content (
                    chunk_id, title, compliance_area, citation
                ) VALUES (%s, %s, %s, %s)
            """, (
                chunk_id,
                title,
                compliance_area,
                citation
            ))
            
            # 3. Insert into chunk_retrieval_rules
            cursor.execute("""
                INSERT INTO chunk_retrieval_rules (
                    chunk_id, priority, requires_parent_law
                ) VALUES (%s, %s, %s)
            """, (
                chunk_id,
                priority,
                requires_parent
            ))
            
            # 4. Insert into chunk_refusal_policy
            cursor.execute("""
                INSERT INTO chunk_refusal_policy (
                    chunk_id, can_answer_standalone, must_reference_parent_law,
                    refuse_if_parent_missing
                ) VALUES (%s, %s, %s, %s)
            """, (
                chunk_id,
                not requires_parent,
                requires_parent,
                refusal_policy['refuse_if_parent_missing']
            ))
            
            # 5. Insert into chunk_lifecycle
            cursor.execute("""
                INSERT INTO chunk_lifecycle (
                    chunk_id, status
                ) VALUES (%s, %s)
            """, (chunk_id, 'ACTIVE'))
            
            # 6. Insert into chunk_versioning
            cursor.execute("""
                INSERT INTO chunk_versioning (
                    chunk_id, version
                ) VALUES (%s, %s)
            """, (chunk_id, '1.0'))
            
            # 7. Insert into chunk_lineage
            cursor.execute("""
                INSERT INTO chunk_lineage (chunk_id)
                VALUES (%s)
            """, (chunk_id,))
            
            # 8. Insert into chunk_administrative
            cursor.execute("""
                INSERT INTO chunk_administrative (chunk_id)
                VALUES (%s)
            """, (chunk_id,))
            
            # 9. Insert into chunk_audit
            cursor.execute("""
                INSERT INTO chunk_audit (chunk_id)
                VALUES (%s)
            """, (chunk_id,))
            
            # 10. Insert into chunk_source
            cursor.execute("""
                INSERT INTO chunk_source (chunk_id)
                VALUES (%s)
            """, (chunk_id,))
            
            # 11. Insert into chunk_temporal
            cursor.execute("""
                INSERT INTO chunk_temporal (
                    chunk_id
                ) VALUES (%s)
            """, (chunk_id,))
            
            # 12. Insert into chunk_embeddings (embedding disabled for parent)
            cursor.execute("""
                INSERT INTO chunk_embeddings (
                    chunk_id, enabled
                ) VALUES (%s, %s)
            """, (chunk_id, False))
            
            conn.commit()
    
    return chunk_id

def update_chunk_text_simple(chunk_id: str, full_text: str, citation: Optional[str] = None):
    """
    Update parent chunk with full text content
    
    Args:
        chunk_id: Chunk ID to update
        full_text: Full text content (archival only, never for retrieval)
        citation: Optional citation to update
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if citation:
                cursor.execute("""
                    UPDATE chunks_content
                    SET text = %s, citation = %s
                    WHERE chunk_id = %s
                """, (full_text, citation, chunk_id))
            else:
                cursor.execute("""
                    UPDATE chunks_content
                    SET text = %s
                    WHERE chunk_id = %s
                """, (full_text, chunk_id))
            
            conn.commit()
