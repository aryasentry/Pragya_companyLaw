"""
Core ingestion service - DB-first approach
Handles creation of parent chunks with minimal input
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
    requires_parent_law,
    validate_chunk_input
)

def generate_chunk_id() -> str:
    """Generate unique chunk ID"""
    return f"chunk_{uuid.uuid4().hex[:16]}"

def create_parent_chunk(input_data: Dict[str, Any], uploaded_by: str) -> tuple[bool, str, Optional[str]]:
    """
    Create a parent chunk with minimal input from admin
    
    Args:
        input_data: {
            'document_type': str (required),
            'act': str (optional),
            'section': str (optional),
            'sub_section': str (optional),
            'title': str (optional),
            'compliance_area': str (optional),
            'issued_by': str (optional),
            'notification_number': str (optional),
            'source_path': str (optional),
            'source_url': str (optional),
            'date_issued': str (optional),
            'effective_from': str (optional),
            'parent_document_id': str (optional)
        }
        uploaded_by: str - username/email of uploader
    
    Returns:
        (success, message, chunk_id)
    """
    # Validate input
    is_valid, error_msg = validate_chunk_input(input_data)
    if not is_valid:
        return False, error_msg, None
    
    # Generate chunk ID
    chunk_id = generate_chunk_id()
    
    # Extract required fields
    document_type = input_data['document_type']
    
    # Apply governance rules
    binding = get_binding_status(document_type)
    priority = get_retrieval_priority(document_type)
    authority_level = get_authority_level(document_type)
    refusal_policy = get_refusal_policy(document_type, priority)
    requires_parent = requires_parent_law(priority)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 1️⃣ Insert into chunks_identity (IMMUTABLE)
                cursor.execute("""
                    INSERT INTO chunks_identity (
                        chunk_id, chunk_role, parent_chunk_id, document_type,
                        authority_level, binding, act, section, sub_section, page_number
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    chunk_id,
                    'parent',
                    None,  # Parent chunks have no parent
                    document_type,
                    authority_level,
                    binding,
                    input_data.get('act'),
                    input_data.get('section'),
                    input_data.get('sub_section'),
                    input_data.get('page_number')
                ))
                
                # 2️⃣ Insert into chunks_content (EDITABLE)
                cursor.execute("""
                    INSERT INTO chunks_content (
                        chunk_id, title, compliance_area, text, summary, citation
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    chunk_id,
                    input_data.get('title'),
                    input_data.get('compliance_area'),
                    None,  # Parent text: archival/audit/citation ONLY (never used for retrieval, never sent to LLM)
                    None,  # Summary will be generated later
                    input_data.get('citation')
                ))
                
                # 3️⃣ Insert into chunk_lifecycle
                cursor.execute("""
                    INSERT INTO chunk_lifecycle (chunk_id, status)
                    VALUES (%s, %s)
                """, (chunk_id, 'DRAFT'))
                
                # 4️⃣ Insert into chunk_retrieval_rules
                cursor.execute("""
                    INSERT INTO chunk_retrieval_rules (
                        chunk_id, priority, requires_parent_law
                    ) VALUES (%s, %s, %s)
                """, (chunk_id, priority, requires_parent))
                
                # 5️⃣ Insert into chunk_refusal_policy
                cursor.execute("""
                    INSERT INTO chunk_refusal_policy (
                        chunk_id, can_answer_standalone,
                        must_reference_parent_law, refuse_if_parent_missing
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    chunk_id,
                    refusal_policy['can_answer_standalone'],
                    refusal_policy['must_reference_parent_law'],
                    refusal_policy['refuse_if_parent_missing']
                ))
                
                # 6️⃣ Insert into chunk_administrative
                cursor.execute("""
                    INSERT INTO chunk_administrative (
                        chunk_id, issued_by, notification_number, source_type, document_language
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    chunk_id,
                    input_data.get('issued_by'),
                    input_data.get('notification_number'),
                    input_data.get('source_type'),
                    input_data.get('document_language', 'en')
                ))
                
                # 7️⃣ Insert into chunk_audit
                cursor.execute("""
                    INSERT INTO chunk_audit (
                        chunk_id, uploaded_by, uploaded_at
                    ) VALUES (%s, %s, %s)
                """, (chunk_id, uploaded_by, datetime.now()))
                
                # 8️⃣ Insert into chunk_source
                cursor.execute("""
                    INSERT INTO chunk_source (chunk_id, path, url)
                    VALUES (%s, %s, %s)
                """, (
                    chunk_id,
                    input_data.get('source_path'),
                    input_data.get('source_url')
                ))
                
                # 9️⃣ Insert into chunk_embeddings (parent = disabled)
                cursor.execute("""
                    INSERT INTO chunk_embeddings (chunk_id, enabled)
                    VALUES (%s, %s)
                """, (chunk_id, False))  # Parent chunks are NEVER embedded
                
                # 🔟 Insert into chunk_lineage
                cursor.execute("""
                    INSERT INTO chunk_lineage (chunk_id, parent_document_id)
                    VALUES (%s, %s)
                """, (chunk_id, input_data.get('parent_document_id')))
                
                # 1️⃣1️⃣ Insert into chunk_temporal (if dates provided)
                cursor.execute("""
                    INSERT INTO chunk_temporal (
                        chunk_id, date_issued, effective_from, effective_to
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    chunk_id,
                    input_data.get('date_issued'),
                    input_data.get('effective_from'),
                    input_data.get('effective_to')
                ))
                
                # 1️⃣2️⃣ Insert into chunk_versioning
                cursor.execute("""
                    INSERT INTO chunk_versioning (chunk_id, version)
                    VALUES (%s, %s)
                """, (chunk_id, input_data.get('version', '1.0')))
        
        return True, f"Parent chunk created successfully: {chunk_id}", chunk_id
    
    except Exception as e:
        return False, f"Database error: {str(e)}", None

def update_chunk_text(chunk_id: str, text: str, page_number: Optional[int] = None, updated_by: Optional[str] = None) -> tuple[bool, str]:
    """
    Update text content for a chunk (parent or child)
    Safe to call multiple times - overwrites previous text
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Update text in chunks_content
                cursor.execute("""
                    UPDATE chunks_content
                    SET text = %s, updated_by = %s, updated_at = %s
                    WHERE chunk_id = %s
                """, (text, updated_by, datetime.now(), chunk_id))
                
                # Update page_number if provided
                if page_number is not None:
                    cursor.execute("""
                        UPDATE chunks_identity
                        SET page_number = %s
                        WHERE chunk_id = %s
                    """, (page_number, chunk_id))
                
                if cursor.rowcount == 0:
                    return False, f"Chunk not found: {chunk_id}"
                
                return True, f"Text updated for chunk: {chunk_id}"
    
    except Exception as e:
        return False, f"Database error: {str(e)}"

def get_chunk_details(chunk_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full chunk details from all tables"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        ci.*,
                        cc.title, cc.compliance_area, cc.text, cc.summary,
                        cl.status,
                        crr.priority, crr.requires_parent_law,
                        crp.can_answer_standalone, crp.must_reference_parent_law,
                        ca.issued_by, ca.notification_number,
                        caud.uploaded_by, caud.uploaded_at, caud.approved_by, caud.approved_at,
                        cs.path, cs.url
                    FROM chunks_identity ci
                    LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    LEFT JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
                    LEFT JOIN chunk_retrieval_rules crr ON ci.chunk_id = crr.chunk_id
                    LEFT JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
                    LEFT JOIN chunk_administrative ca ON ci.chunk_id = ca.chunk_id
                    LEFT JOIN chunk_audit caud ON ci.chunk_id = caud.chunk_id
                    LEFT JOIN chunk_source cs ON ci.chunk_id = cs.chunk_id
                    WHERE ci.chunk_id = %s
                """, (chunk_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
    
    except Exception as e:
        print(f"Error retrieving chunk: {e}")
        return None
