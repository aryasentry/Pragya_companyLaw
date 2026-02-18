"""
Flask API endpoints for governance-grade RAG system
Integrates with Next.js admin panel
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from ingestion_service import (
    create_parent_chunk,
    update_chunk_text,
    get_chunk_details
)
from chunking_engine_v2 import hierarchical_chunk, get_child_chunks
from embedding_worker import embed_child_chunks, embed_single_chunk, batch_embed_pending
from companies_act_2013.governance_db.useless_files.retrieval_service_v2 import (
    retrieve_with_governance,
    get_chunk_by_legal_anchor,
    get_active_chunks_by_date
)
from db_config import get_db_connection

# Create blueprint
api_governance = Blueprint('api_governance', __name__, url_prefix='/api/governance')

# ============= ADMIN ENDPOINTS =============

@api_governance.route('/chunks/create', methods=['POST'])
def create_chunk_endpoint():
    """
    Create a new parent chunk
    
    Request body:
    {
        "document_type": "act|rule|regulation|notification|circular|guideline|faq|commentary",
        "act": "Companies Act 2013",
        "section": "123",
        "title": "Section title",
        "uploaded_by": "admin@example.com",
        ... (other optional fields)
    }
    """
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Extract uploader
    uploaded_by = data.pop('uploaded_by', 'unknown')
    
    # Create parent chunk
    success, message, chunk_id = create_parent_chunk(data, uploaded_by)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'chunk_id': chunk_id
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@api_governance.route('/chunks/<chunk_id>/text', methods=['PATCH'])
def update_chunk_text_endpoint(chunk_id: str):
    """
    Update text content for a chunk
    
    Request body:
    {
        "text": "Full section text...",
        "updated_by": "admin@example.com"
    }
    """
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Text is required'}), 400
    
    text = data['text']
    updated_by = data.get('updated_by', 'unknown')
    
    success, message = update_chunk_text(chunk_id, text, updated_by=updated_by)
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@api_governance.route('/chunks/<chunk_id>/split', methods=['POST'])
def split_chunk_endpoint(chunk_id: str):
    """
    Split parent chunk into child chunks
    
    Request body:
    {
        "text": "Full text to split",
        "max_chars": 1000,
        "overlap": 100,
        "created_by": "admin@example.com"
    }
    """
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Text is required'}), 400
    
    text = data['text']
    max_chars = data.get('max_chars', 1000)
    overlap = data.get('overlap', 100)
    created_by = data.get('created_by', 'system')
    
    success, message, child_ids = hierarchical_chunk(
        chunk_id, text, max_chars, overlap, created_by
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'child_count': len(child_ids),
            'child_ids': child_ids
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@api_governance.route('/chunks/<chunk_id>/embed', methods=['POST'])
def embed_chunk_endpoint(chunk_id: str):
    """
    Generate embeddings for chunk's children
    
    Request body:
    {
        "model_name": "all-MiniLM-L6-v2" (optional)
    }
    """
    data = request.json or {}
    model_name = data.get('model_name')
    
    success, message, count = embed_child_chunks(chunk_id, model_name)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'embedded_count': count
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 400

@api_governance.route('/chunks/<chunk_id>/approve', methods=['POST'])
def approve_chunk_endpoint(chunk_id: str):
    """
    Approve chunk (change status from DRAFT to ACTIVE)
    
    Request body:
    {
        "approved_by": "admin@example.com"
    }
    """
    data = request.json
    approved_by = data.get('approved_by', 'unknown')
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Update lifecycle status
                cursor.execute("""
                    UPDATE chunk_lifecycle
                    SET status = 'ACTIVE', updated_at = %s
                    WHERE chunk_id = %s
                """, (datetime.now(), chunk_id))
                
                # Update audit trail
                cursor.execute("""
                    UPDATE chunk_audit
                    SET approved_by = %s, approved_at = %s
                    WHERE chunk_id = %s
                """, (approved_by, datetime.now(), chunk_id))
        
        return jsonify({
            'success': True,
            'message': f'Chunk {chunk_id} approved'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_governance.route('/chunks/<chunk_id>', methods=['GET'])
def get_chunk_endpoint(chunk_id: str):
    """Get full chunk details"""
    chunk_data = get_chunk_details(chunk_id)
    
    if chunk_data:
        return jsonify({
            'success': True,
            'chunk': chunk_data
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Chunk not found'
        }), 404

@api_governance.route('/chunks/<chunk_id>/children', methods=['GET'])
def get_chunk_children_endpoint(chunk_id: str):
    """Get all child chunks for a parent"""
    children = get_child_chunks(chunk_id)
    
    return jsonify({
        'success': True,
        'parent_chunk_id': chunk_id,
        'child_count': len(children),
        'children': children
    }), 200

@api_governance.route('/chunks', methods=['GET'])
def list_chunks_endpoint():
    """
    List chunks with filters
    
    Query params:
    - document_type: Filter by type
    - status: Filter by lifecycle status
    - binding: Filter by binding status
    - limit: Number of results (default 50)
    - offset: Pagination offset
    """
    document_type = request.args.get('document_type')
    status = request.args.get('status')
    binding = request.args.get('binding')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        ci.chunk_id,
                        ci.chunk_role,
                        ci.document_type,
                        ci.binding,
                        ci.act,
                        ci.section,
                        cc.title,
                        cl.status,
                        caud.uploaded_at,
                        caud.approved_at
                    FROM chunks_identity ci
                    LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    LEFT JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
                    LEFT JOIN chunk_audit caud ON ci.chunk_id = caud.chunk_id
                    WHERE 1=1
                """
                params = []
                
                if document_type:
                    query += " AND ci.document_type = %s"
                    params.append(document_type)
                
                if status:
                    query += " AND cl.status = %s"
                    params.append(status)
                
                if binding is not None:
                    query += " AND ci.binding = %s"
                    params.append(binding.lower() == 'true')
                
                query += " ORDER BY caud.uploaded_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                chunks = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'count': len(chunks),
            'chunks': chunks
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============= USER QUERY ENDPOINTS =============

@api_governance.route('/search', methods=['POST'])
def search_endpoint():
    """
    Search with governance enforcement
    
    Request body:
    {
        "query": "User question",
        "top_k": 5,
        "enforce_refusal": true
    }
    """
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query = data['query']
    top_k = data.get('top_k', 5)
    enforce_refusal = data.get('enforce_refusal', True)
    
    results = retrieve_with_governance(query, top_k, enforce_refusal)
    
    return jsonify({
        'success': True,
        'query': query,
        **results
    }), 200

@api_governance.route('/search/anchor', methods=['GET'])
def search_by_anchor_endpoint():
    """
    Search by legal reference (e.g., Act, Section)
    
    Query params:
    - act: Act name
    - section: Section number
    - sub_section: Sub-section (optional)
    """
    act = request.args.get('act')
    section = request.args.get('section')
    sub_section = request.args.get('sub_section')
    
    if not act or not section:
        return jsonify({'error': 'Act and section are required'}), 400
    
    chunk = get_chunk_by_legal_anchor(act, section, sub_section)
    
    if chunk:
        return jsonify({
            'success': True,
            'chunk': chunk
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'No matching chunk found'
        }), 404

@api_governance.route('/chunks/active', methods=['GET'])
def get_active_chunks_endpoint():
    """
    Get all active chunks (optionally for specific date)
    
    Query params:
    - date: Effective date (YYYY-MM-DD format, optional)
    """
    date_str = request.args.get('date')
    effective_date = None
    
    if date_str:
        try:
            effective_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    chunks = get_active_chunks_by_date(effective_date)
    
    return jsonify({
        'success': True,
        'count': len(chunks),
        'chunks': chunks
    }), 200

# ============= BACKGROUND JOBS =============

@api_governance.route('/jobs/embed-pending', methods=['POST'])
def embed_pending_job():
    """Background job to embed all pending chunks"""
    data = request.json or {}
    batch_size = data.get('batch_size', 50)
    
    success, message, count = batch_embed_pending(batch_size)
    
    return jsonify({
        'success': success,
        'message': message,
        'embedded_count': count
    }), 200
