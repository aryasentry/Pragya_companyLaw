"""
Retrieval service - governance-grade search with refusal policy enforcement
Only retrieves child chunks, fetches parent metadata, enforces legal safety
"""
from typing import List, Dict, Any, Optional
from db_config import get_db_connection
from datetime import date

def search_chunks(
    query_embedding: List[float],
    top_k: int = 10,
    document_types: Optional[List[str]] = None,
    min_priority: Optional[int] = None,
    require_active: bool = True,
    require_binding: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    Search for relevant chunks using vector similarity
    
    Args:
        query_embedding: Vector embedding of user query
        top_k: Number of results to return
        document_types: Filter by document types
        min_priority: Minimum priority level (1=highest)
        require_active: Only return ACTIVE chunks
        require_binding: Filter by binding status
    
    Returns:
        List of matching chunks with parent metadata
    """
    # TODO: Replace with actual vector search (Pinecone/Weaviate/pgvector)
    # For now, return chunks based on filters only
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build query
                query = """
                    SELECT 
                        ci.chunk_id,
                        ci.parent_chunk_id,
                        ci.document_type,
                        ci.authority_level,
                        ci.binding,
                        ci.act,
                        ci.section,
                        cc.text,
                        crr.priority,
                        crr.requires_parent_law,
                        crp.can_answer_standalone,
                        crp.must_reference_parent_law,
                        crp.refuse_if_parent_missing,
                        ce.vector_id
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_retrieval_rules crr ON ci.chunk_id = crr.chunk_id
                    JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
                    JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
                    WHERE ci.chunk_role = 'child'
                      AND ce.enabled = TRUE
                      AND ce.vector_id IS NOT NULL
                """
                
                params = []
                
                if require_active:
                    query += " AND cl.status = 'ACTIVE'"
                
                if document_types:
                    placeholders = ','.join(['%s'] * len(document_types))
                    query += f" AND ci.document_type IN ({placeholders})"
                    params.extend(document_types)
                
                if min_priority is not None:
                    query += " AND crr.priority >= %s"
                    params.append(min_priority)
                
                if require_binding is not None:
                    query += " AND ci.binding = %s"
                    params.append(require_binding)
                
                query += f" LIMIT %s"
                params.append(top_k)
                
                cursor.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]
                
                # Fetch parent metadata for each result
                enriched_results = []
                for result in results:
                    parent_data = _get_parent_metadata(result['parent_chunk_id'])
                    result['parent_metadata'] = parent_data
                    enriched_results.append(result)
                
                return enriched_results
    
    except Exception as e:
        print(f"Search error: {e}")
        return []

def retrieve_with_governance(
    query: str,
    top_k: int = 5,
    enforce_refusal: bool = True
) -> Dict[str, Any]:
    """
    High-level retrieval with refusal policy enforcement
    
    Args:
        query: User question
        top_k: Number of results
        enforce_refusal: Apply refusal policies
    
    Returns:
        {
            'results': List of chunks,
            'refusal_triggered': bool,
            'refusal_reason': str,
            'parent_laws': List of parent law references
        }
    """
    # TODO: Generate query embedding
    # For now, use placeholder
    query_embedding = [0.0] * 384  # Placeholder
    
    # Search chunks
    chunks = search_chunks(query_embedding, top_k=top_k, require_active=True)
    
    if not chunks:
        return {
            'results': [],
            'refusal_triggered': False,
            'refusal_reason': None,
            'parent_laws': []
        }
    
    # Apply refusal policies
    if enforce_refusal:
        refusal_check = _check_refusal_policies(chunks)
        if refusal_check['should_refuse']:
            return {
                'results': [],
                'refusal_triggered': True,
                'refusal_reason': refusal_check['reason'],
                'parent_laws': refusal_check['missing_parents']
            }
    
    # Collect parent law references
    parent_laws = _collect_parent_laws(chunks)
    
    return {
        'results': chunks,
        'refusal_triggered': False,
        'refusal_reason': None,
        'parent_laws': parent_laws
    }

def _get_parent_metadata(parent_chunk_id: str) -> Optional[Dict[str, Any]]:
    """Fetch parent chunk full details"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        ci.*,
                        cc.title,
                        cc.compliance_area,
                        cc.text as parent_text,
                        cc.summary,
                        ca.issued_by,
                        ca.notification_number,
                        cs.url
                    FROM chunks_identity ci
                    LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    LEFT JOIN chunk_administrative ca ON ci.chunk_id = ca.chunk_id
                    LEFT JOIN chunk_source cs ON ci.chunk_id = cs.chunk_id
                    WHERE ci.chunk_id = %s
                """, (parent_chunk_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
    except Exception as e:
        print(f"Error fetching parent: {e}")
        return None

def _check_refusal_policies(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check if refusal policies should trigger
    
    Rules:
    - Priority 2 (Rules/Notifications): Refuse if parent Act missing
    - Priority 3 (Circulars/Guidelines): Refuse if parent Rule missing
    - Priority 4 (Commentary): Always refuse standalone
    """
    for chunk in chunks:
        priority = chunk['priority']
        requires_parent = chunk['requires_parent_law']
        refuse_if_missing = chunk['refuse_if_parent_missing']
        
        if refuse_if_missing and requires_parent:
            # Check if parent law exists
            parent_id = chunk['parent_chunk_id']
            parent_meta = chunk.get('parent_metadata')
            
            if not parent_meta:
                return {
                    'should_refuse': True,
                    'reason': f"Insufficient authoritative source: Missing parent law for priority {priority} document",
                    'missing_parents': [parent_id]
                }
            
            # For priority 2, check if there's a parent Act
            if priority == 2:
                parent_act = _find_parent_act(parent_id)
                if not parent_act:
                    return {
                        'should_refuse': True,
                        'reason': "Cannot answer without primary legislation (Act)",
                        'missing_parents': [parent_id]
                    }
    
    return {'should_refuse': False, 'reason': None, 'missing_parents': []}

def _find_parent_act(chunk_id: str) -> Optional[str]:
    """Traverse relationships to find parent Act"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if current chunk is an Act
                cursor.execute("""
                    SELECT document_type FROM chunks_identity WHERE chunk_id = %s
                """, (chunk_id,))
                result = cursor.fetchone()
                
                if result and result['document_type'] == 'act':
                    return chunk_id
                
                # Look for 'implements' relationship pointing to an Act
                cursor.execute("""
                    SELECT target_chunk_id
                    FROM chunk_relationships
                    WHERE source_chunk_id = %s
                      AND relationship_type = 'implements'
                """, (chunk_id,))
                
                related = cursor.fetchone()
                if related:
                    return _find_parent_act(related['target_chunk_id'])
        
        return None
    except Exception as e:
        print(f"Error finding parent act: {e}")
        return None

def _collect_parent_laws(chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Collect all parent law references for citation"""
    parent_laws = []
    seen = set()
    
    for chunk in chunks:
        parent_meta = chunk.get('parent_metadata')
        if parent_meta:
            parent_id = parent_meta['chunk_id']
            if parent_id not in seen:
                parent_laws.append({
                    'chunk_id': parent_id,
                    'title': parent_meta.get('title'),
                    'act': parent_meta.get('act'),
                    'section': parent_meta.get('section'),
                    'document_type': parent_meta.get('document_type'),
                    'url': parent_meta.get('url')
                })
                seen.add(parent_id)
    
    return parent_laws

def get_chunk_by_legal_anchor(act: str, section: str, sub_section: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve chunk by exact legal reference"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT ci.*, cc.text, cc.title, cc.summary
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
                    WHERE ci.act = %s
                      AND ci.section = %s
                      AND cl.status = 'ACTIVE'
                """
                params = [act, section]
                
                if sub_section:
                    query += " AND ci.sub_section = %s"
                    params.append(sub_section)
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                return dict(result) if result else None
    except Exception as e:
        print(f"Error fetching by anchor: {e}")
        return None

def get_active_chunks_by_date(effective_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Get chunks effective on a specific date"""
    if effective_date is None:
        effective_date = date.today()
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ci.chunk_id, cc.title, ci.act, ci.section
                    FROM chunks_identity ci
                    JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
                    LEFT JOIN chunk_temporal ct ON ci.chunk_id = ct.chunk_id
                    WHERE cl.status = 'ACTIVE'
                      AND (ct.effective_from IS NULL OR ct.effective_from <= %s)
                      AND (ct.effective_to IS NULL OR ct.effective_to >= %s)
                """, (effective_date, effective_date))
                
                return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching by date: {e}")
        return []
