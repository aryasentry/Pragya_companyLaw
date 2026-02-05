"""
Flask API Server for Companies Act 2013 RAG System
Uses FAISS + PostgreSQL retrieval
Handles all operations: Query, Upload, Ingest, Pipeline Management
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename

# Add governance_db to path
sys.path.insert(0, str(Path(__file__).parent / 'governance_db'))

from retrieval_service_faiss import GovernanceRetriever

app = Flask(__name__)
CORS(app)

# Initialize retriever
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("Initializing GovernanceRetriever...")
try:
    retriever = GovernanceRetriever()
    logger.info("Retriever initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize retriever: {e}")
    retriever = None


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    if retriever is None:
        return jsonify({
            'status': 'error',
            'message': 'Retriever not initialized'
        }), 500
    
    return jsonify({
        'status': 'healthy',
        'service': 'Companies Act 2013 RAG API',
        'vectors_loaded': len(retriever.metadata),
        'embedding_model': 'qwen3-embedding:0.6b',
        'llm_model': 'qwen2.5:1.5b'
    })


@app.route('/api/query', methods=['POST'])
def query():
    """
    Query endpoint for RAG system
    
    Request body:
    {
        "query": "user question",
        "top_k": 5,  // optional
        "include_relationships": false  // optional
    }
    """
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Retriever not initialized'
        }), 500
    
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing query parameter'
            }), 400
        
        user_query = data['query']
        top_k = data.get('top_k', 15)
        include_relationships = data.get('include_relationships', False)
        
        logger.info(f"Query received: '{user_query}' (top_k={top_k})")
        
        # Perform retrieval
        result = retriever.query(
            user_query, 
            top_k=top_k,
            include_relationships=include_relationships
        )
        
        return jsonify({
            'success': True,
            'result': {
                'synthesized_answer': result['answer'],
                'answer_citations': result['citations'],
                'retrieved_sections': result['retrieved_chunks'],
                'relationships': result.get('relationships', [])
            }
        })
    
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Error processing query: {error_msg}")
        logger.debug(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


# Pipeline status tracking
pipeline_status = {
    'running': False,
    'current_file': None,
    'stage': None,
    'message': None,
    'logs': []
}

@app.route('/api/pipeline/status', methods=['GET'])
def get_pipeline_status():
    """Get current pipeline processing status"""
    return jsonify(pipeline_status)


@app.route('/api/pipeline/update', methods=['POST'])
def update_pipeline_status():
    """Update pipeline status (called by upload route)"""
    global pipeline_status
    try:
        data = request.get_json()
        
        # Update status
        if 'running' in data:
            pipeline_status['running'] = data['running']
        if 'current_file' in data:
            pipeline_status['current_file'] = data['current_file']
        if 'stage' in data:
            pipeline_status['stage'] = data['stage']
        if 'message' in data:
            pipeline_status['message'] = data['message']
        if 'logs' in data:
            pipeline_status['logs'] = data['logs']
        
        logger.info(f"Pipeline status updated: {pipeline_status['stage']} - {pipeline_status['message']}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating pipeline status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/upload', methods=['POST'])
def upload_document():
    """Upload document and run full processing pipeline"""
    global pipeline_status
    
    try:
        # Get file and metadata
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        metadata_str = request.form.get('metadata', '{}')
        
        import json
        metadata = json.loads(metadata_str)
        
        # Extract metadata
        doc_type = metadata.get('documentType', 'other')
        category = metadata.get('category', 'non_binding')
        section = metadata.get('section', '')
        
        # Save file to data folder
        base_path = Path(__file__).parent / 'data'
        
        if category == 'companies_act' and section:
            section_padded = section.zfill(3)
            doc_type_folder = doc_type.capitalize()
            save_path = base_path / 'companies_act' / f'section_{section_padded}' / doc_type_folder
        else:
            doc_type_folder = doc_type.capitalize()
            save_path = base_path / 'non_binding' / doc_type_folder
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        filename = secure_filename(file.filename)
        file_path = save_path / filename
        file.save(str(file_path))
        
        logger.info(f"File saved: {file_path}")
        
        # Update pipeline status
        pipeline_status.update({
            'running': True,
            'current_file': filename,
            'stage': 'Starting',
            'message': f'Processing {doc_type} {section}',
            'logs': []
        })
        
        # Run pipeline
        python_exe = sys.executable
        pipeline_script = Path(__file__).parent / 'governance_db' / 'pipeline_full.py'
        
        cmd = [
            python_exe,
            str(pipeline_script),
            '--file', str(file_path),
            '--type', doc_type,
            '--category', category
        ]
        
        if section:
            cmd.extend(['--section', section.zfill(3)])

                
        logger.info(f"Running pipeline: {' '.join(cmd)}")
        
        # Execute pipeline with real-time output streaming
        import subprocess as sp
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
        
        output_lines = []
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            
            # Parse stage updates
            if line.startswith('STAGE:'):
                stage = line.split(':', 1)[1]
                pipeline_status.update({
                    'running': True,
                    'stage': stage,
                    'message': f'{stage} - {filename}',
                    'progress': 0,
                    'logs': output_lines[-20:]
                })
                logger.info(f"Pipeline stage: {stage}")
            
            # Parse progress updates for embeddings
            elif line.startswith('PROGRESS:Embeddings:'):
                try:
                    progress = int(line.split(':')[2])
                    pipeline_status.update({
                        'progress': progress
                    })
                except:
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            pipeline_status.update({
                'running': False,
                'stage': 'Completed',
                'message': 'Pipeline completed successfully',
                'logs': output_lines[-20:]
            })
            logger.info(f"Pipeline completed: {filename}")
            
            return jsonify({
                'success': True,
                'data': {
                    'filePath': str(file_path),
                    'message': 'Document fully processed',
                    'output': '\n'.join(output_lines)
                }
            })
        else:
            error_output = '\n'.join(output_lines)
            pipeline_status.update({
                'running': False,
                'stage': 'Failed',
                'message': f'Pipeline failed: {error_output[-200:]}'
            })
            logger.error(f"Pipeline failed: {error_output}")
            
            return jsonify({
                'success': False,
                'error': f'Pipeline failed: {error_output}'
            }), 500
    
    except Exception as e:
        pipeline_status.update({
            'running': False,
            'stage': 'Failed',
            'message': str(e)
        })
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/ingest', methods=['POST'])
def ingest_document():
    """Ingest document from form data or text content"""
    global pipeline_status
    
    try:
        # Parse multipart form data
        metadata_str = request.form.get('metadata', '{}')
        import json
        metadata = json.loads(metadata_str)
        
        # Extract metadata
        doc_type = metadata.get('documentType', 'other')
        is_binding = metadata.get('isBinding', False)
        section = metadata.get('section', '')
        input_type = metadata.get('inputType', 'text')
        text_content = metadata.get('textContent', '')
        
        # Determine category
        category = 'companies_act' if is_binding else 'non_binding'
        
        # Save file to data folder
        base_path = Path(__file__).parent / 'data'
        
        if category == 'companies_act' and section:
            section_padded = section.zfill(3)
            doc_type_folder = doc_type.capitalize()
            save_path = base_path / 'companies_act' / f'section_{section_padded}' / doc_type_folder
        else:
            doc_type_folder = doc_type.capitalize()
            save_path = base_path / 'non_binding' / doc_type_folder
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save file
        if input_type == 'pdf' and 'file' in request.files:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file_path = save_path / filename
            file.save(str(file_path))
        else:
            # Text content
            filename = f"section_{section.zfill(3) if section else '000'}_{doc_type}.txt"
            file_path = save_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
        
        logger.info(f"File saved: {file_path}")
        
        # Update pipeline status
        pipeline_status.update({
            'running': True,
            'current_file': filename,
            'stage': 'Starting',
            'message': f'Processing {doc_type} Section {section}',
            'logs': []
        })
        
        # Run pipeline
        python_exe = sys.executable
        pipeline_script = Path(__file__).parent / 'governance_db' / 'pipeline_full.py'
        
        cmd = [
            python_exe,
            str(pipeline_script),
            '--file', str(file_path),
            '--type', doc_type,
            '--category', category
        ]
        
        if section:
            cmd.extend(['--section', section.zfill(3)])
        
        logger.info(f"Running pipeline: {' '.join(cmd)}")
        
        # Execute pipeline with real-time output streaming
        import subprocess as sp
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
        
        output_lines = []
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            
            # Parse stage updates
            if line.startswith('STAGE:'):
                stage = line.split(':', 1)[1]
                pipeline_status.update({
                    'running': True,
                    'stage': stage,
                    'message': f'{stage} - {filename}',
                    'progress': 0,
                    'logs': output_lines[-20:]
                })
                logger.info(f"Pipeline stage: {stage}")
            
            # Parse progress updates for embeddings
            elif line.startswith('PROGRESS:Embeddings:'):
                try:
                    progress = int(line.split(':')[2])
                    pipeline_status.update({
                        'progress': progress
                    })
                except:
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            pipeline_status.update({
                'running': False,
                'stage': 'Completed',
                'message': 'Pipeline completed successfully',
                'logs': output_lines[-20:]
            })
            logger.info(f"Pipeline completed: {filename}")
            
            return jsonify({
                'success': True,
                'data': {
                    'filePath': str(file_path),
                    'message': 'Document fully processed: Parsed → Chunked → Summarized → Keywords → Relationships',
                    'output': '\n'.join(output_lines)
                }
            })
        else:
            error_output = '\n'.join(output_lines)
            pipeline_status.update({
                'running': False,
                'stage': 'Failed',
                'message': f'Pipeline failed: {error_output[-200:]}'
            })
            logger.error(f"Pipeline failed: {error_output}")
            
            return jsonify({
                'success': False,
                'error': f'Pipeline failed: {error_output}'
            }), 500
    
    except Exception as e:
        pipeline_status.update({
            'running': False,
            'stage': 'Failed',
            'message': str(e)
        })
        logger.error(f"Ingest error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/chunk/<chunk_id>', methods=['GET'])
def get_chunk(chunk_id):
    """Get full chunk details by ID"""
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Retriever not initialized'
        }), 500
    
    try:
        chunks = retriever.get_chunk_details([chunk_id])
        
        if not chunks:
            return jsonify({
                'success': False,
                'error': f'Chunk {chunk_id} not found'
            }), 404
        
        chunk = chunks[0]
        
        return jsonify({
            'success': True,
            'chunk': {
                'chunk_id': chunk['chunk_id'],
                'parent_id': chunk['parent_chunk_id'],
                'section': chunk['section'],
                'document_type': chunk['document_type'],
                'text': chunk['text'],
                'title': chunk['title'],
                'compliance_area': chunk['compliance_area'],
                'issued_by': chunk.get('issued_by'),
                'date_issued': chunk['date_issued'].isoformat() if chunk.get('date_issued') else None,
                'citation': chunk['citation'],
                'priority': chunk.get('priority'),
                'authority_level': chunk['authority_level'],
                'binding': chunk['binding']
            }
        })
    
    except Exception as e:
        logger.error(f"Error fetching chunk: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/relationships/<chunk_id>', methods=['GET'])
def get_relationships(chunk_id):
    """Get relationships for a chunk"""
    if retriever is None:
        return jsonify({
            'success': False,
            'error': 'Retriever not initialized'
        }), 500
    
    try:
        logger.info(f"API call: /api/relationships/{chunk_id}")
        relationships = retriever.get_chunk_relationships(chunk_id)
        
        return jsonify({
            'success': True,
            'chunk_id': chunk_id,
            'relationships': [
                {
                    'type': rel['relationship_type'],
                    'target': rel['target_chunk_id'],
                    'confidence': float(rel['confidence_score']) if rel['confidence_score'] else 0,
                    'metadata': rel['metadata']
                }
                for rel in relationships
            ]
        })
    
    except Exception as e:
        logger.error(f"Error fetching relationships: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("Companies Act 2013 RAG API Server")
    print("="*70)
    print("Backend: Flask + FAISS + PostgreSQL")
    print("Embeddings: qwen3-embedding:0.6b (1024-dim)")
    print("LLM: qwen2.5:1.5b")
    print("="*70 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
