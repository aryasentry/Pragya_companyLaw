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

# Load env from app/.env.local if present (for GEMINI_API_KEY etc.)
_env_local = Path(__file__).resolve().parent.parent / 'app' / '.env.local'
if _env_local.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_local)
    except ImportError:
        pass

sys.path.insert(0, str(Path(__file__).parent / 'governance_db'))

from retrieval_service_faiss import GovernanceRetriever

app = Flask(__name__)
CORS(app)

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Data folder: existing data/ and uploads/ for vision batch
BASE_PATH = Path(__file__).parent
DATA_ROOT = BASE_PATH / 'data'
UPLOADS_DIR = DATA_ROOT / 'uploads'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

logger.info("Initializing GovernanceRetriever...")
try:
    retriever = GovernanceRetriever()
    logger.info("Retriever initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize retriever: {e}")
    retriever = None

@app.route('/api/health', methods=['GET'])
def health():
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

pipeline_status = {
    'running': False,
    'current_file': None,
    'stage': None,
    'message': None,
    'logs': []
}

@app.route('/api/pipeline/status', methods=['GET'])
def get_pipeline_status():
    return jsonify(pipeline_status)

@app.route('/api/pipeline/update', methods=['POST'])
def update_pipeline_status():
    global pipeline_status
    try:
        data = request.get_json()
        
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
    global pipeline_status
    
    try:

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        metadata_str = request.form.get('metadata', '{}')
        
        import json
        metadata = json.loads(metadata_str)
        
        doc_type = metadata.get('documentType', 'other')
        category = metadata.get('category', 'non_binding')
        section = metadata.get('section', '')
        
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
        
        pipeline_status.update({
            'running': True,
            'current_file': filename,
            'stage': 'Starting',
            'message': f'Processing {doc_type} {section}',
            'logs': []
        })
        
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
        
        import subprocess as sp
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
        
        output_lines = []
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            
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
    global pipeline_status
    
    try:

        metadata_str = request.form.get('metadata', '{}')
        import json
        metadata = json.loads(metadata_str)
        
        doc_type = metadata.get('documentType', 'other')
        is_binding = metadata.get('isBinding', True)
        section = metadata.get('section', '')
        input_type = metadata.get('inputType', 'text')
        text_content = metadata.get('textContent', '')
        
        category = 'companies_act' if is_binding else 'non_binding'
        
        base_path = Path(__file__).parent / 'data'
        
        if category == 'companies_act' and section:
            section_padded = section.zfill(3)
            doc_type_folder = doc_type.capitalize()
            save_path = base_path / 'companies_act' / f'section_{section_padded}' / doc_type_folder
        else:
            doc_type_folder = doc_type.capitalize()
            save_path = base_path / 'non_binding' / doc_type_folder
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        if input_type == 'pdf' and 'file' in request.files:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file_path = save_path / filename
            file.save(str(file_path))
        else:

            filename = f"section_{section.zfill(3) if section else '000'}_{doc_type}.txt"
            file_path = save_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
        
        logger.info(f"File saved: {file_path}")
        
        pipeline_status.update({
            'running': True,
            'current_file': filename,
            'stage': 'Starting',
            'message': f'Processing {doc_type} Section {section}',
            'logs': []
        })
        
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
        
        import subprocess as sp
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
        
        output_lines = []
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            
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

# ----- Background RAG job queue -----
import queue as _queue
import threading

_rag_queue: _queue.Queue = _queue.Queue()
_rag_jobs: dict = {}          # audit_id (str) -> status dict
_rag_jobs_lock = threading.Lock()

# Maps pipeline STAGE: output to rough % progress
_STAGE_PROGRESS = {
    'Starting': 5,
    'Parsing': 15,
    'Chunking': 35,
    'Summarizing': 55,
    'Relationships': 70,
    'Building Embeddings': 85,
    'Completed': 100,
    'Failed': 0,
}

BINDING_TYPES = {
    'act', 'rule', 'regulation', 'order', 'notification', 'schedule',
    'circular', 'form', 'register', 'return'
}

def _normalize_ingest_fields(meta: dict, doc_type_hint: str | None = None):
    """Fill defaults so RAG can run even when some fields are missing."""
    doc_type = (meta.get('documentType') or doc_type_hint or 'other')
    doc_type = str(doc_type).strip().lower() or 'other'

    raw_section = str(meta.get('section') or meta.get('sectionNumber') or '').strip()
    section = raw_section.zfill(3) if raw_section.isdigit() else None

    is_binding_val = meta.get('isBinding')
    if is_binding_val is None:
        is_binding = doc_type in BINDING_TYPES
    else:
        is_binding = bool(is_binding_val)

    # If section is missing, fall back to non_binding so pipeline won't abort.
    category = 'companies_act' if (is_binding and section) else 'non_binding'
    return doc_type, section, category, is_binding

def _rag_update(audit_id: str, **kwargs):
    """Thread-safe update of a job's status dict."""
    with _rag_jobs_lock:
        job = _rag_jobs.setdefault(audit_id, {})
        job.update(kwargs)
        stage = kwargs.get('stage')
        if stage:
            job['progress'] = _STAGE_PROGRESS.get(stage, job.get('progress', 0))

def _rag_worker():
    """Daemon thread: processes approved documents one at a time from the queue."""
    while True:
        job = _rag_queue.get()
        audit_id = job['audit_id']
        try:
            _rag_update(audit_id, stage='Starting', message='Initializing pipeline...', started_at=datetime.now().isoformat())
            python_exe = sys.executable
            pipeline_script = Path(__file__).parent / 'governance_db' / 'pipeline_full.py'
            doc_type = (job.get('doc_type') or 'other').lower()
            category = job.get('category') or 'non_binding'
            section_arg = job.get('section')
            if category == 'companies_act' and not section_arg:
                logger.warning(f"[RAG queue] {audit_id[:8]}.. missing section, defaulting to '000'")
                section_arg = '000'
            cmd = [
                python_exe, str(pipeline_script),
                '--file', job['file_path'],
                '--type', doc_type,
                '--category', category,
                '--skip-embed',
            ]
            if section_arg:
                cmd.extend(['--section', section_arg])

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1
            )
            output_lines = []
            for line in proc.stdout:
                line = line.rstrip()
                output_lines.append(line)
                if line.startswith('STAGE:'):
                    stage = line.split(':', 1)[1].strip()
                    _rag_update(audit_id, stage=stage, message=f'{stage}...')
                    logger.info(f"[RAG queue] {audit_id[:8]}.. stage={stage}")
            proc.wait()

            if proc.returncode == 0:
                _rag_update(audit_id, stage='Completed', message='RAG pipeline complete',
                            completed_at=datetime.now().isoformat(), logs=output_lines[-30:])
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE admin_audit_log SET status = 'SUCCESS', details = 'RAG pipeline complete' WHERE id = %s::uuid",
                            (audit_id,)
                        )
                logger.info(f"[RAG queue] {audit_id[:8]}.. COMPLETE")
            else:
                err_snippet = '\n'.join(output_lines[-10:])
                _rag_update(audit_id, stage='Failed', message='Pipeline failed',
                            completed_at=datetime.now().isoformat(), logs=output_lines[-30:])
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s::uuid",
                            (f'RAG failed: {err_snippet[:300]}', audit_id)
                        )
                logger.error(f"[RAG queue] {audit_id[:8]}.. FAILED")
        except Exception as exc:
            logger.exception(f'RAG worker error for {audit_id}: {exc}')
            _rag_update(audit_id, stage='Failed', message=str(exc)[:300],
                        completed_at=datetime.now().isoformat())
        finally:
            _rag_queue.task_done()
            # Recompute queue positions for remaining queued jobs
            with _rag_jobs_lock:
                pos = 1
                for info in _rag_jobs.values():
                    if info.get('stage') == 'Queued':
                        info['message'] = f'Position {pos} in queue'
                        pos += 1

# Start background RAG worker (daemon so it exits when Flask exits)
_rag_thread = threading.Thread(target=_rag_worker, daemon=True, name='rag-worker')
_rag_thread.start()
logger.info("Background RAG worker started")

# ----- Embedding rebuild trigger -----
_embed_lock = threading.Lock()
_embed_running = False

def _run_embedding_build(sections=None, limit=None):
    """Run build_faiss_index.build_vector_database in a background thread."""
    global _embed_running
    with _embed_lock:
        if _embed_running:
            logger.info("Embedding build already running; skipping new request")
            return False
        _embed_running = True
    def _task():
        global _embed_running
        try:
            from governance_db import build_faiss_index
            build_faiss_index.build_vector_database(sections=sections, limit=limit)
            logger.info("Embedding rebuild complete")
        except Exception as exc:
            logger.exception(f"Embedding rebuild failed: {exc}")
        finally:
            with _embed_lock:
                _embed_running = False
    threading.Thread(target=_task, daemon=True, name='embed-build').start()
    return True

@app.route('/api/admin/build-embeddings', methods=['POST'])
def trigger_embeddings():
    """Trigger incremental FAISS rebuild (runs in background)."""
    try:
        data = request.get_json() or {}
        sections = data.get('sections')
        limit = data.get('limit')
        started = _run_embedding_build(sections=sections, limit=limit)
        if not started:
            return jsonify({'success': False, 'error': 'Embedding build already running'}), 409
        return jsonify({'success': True, 'message': 'Embedding rebuild started'})
    except Exception as e:
        logger.error(f"Embedding trigger error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ----- Vision batch ingestion -----
import uuid
import json as json_module

def _get_audit_db():
    from db_config import get_db_connection
    return get_db_connection

@app.route('/api/admin/batch-upload', methods=['POST'])
def batch_upload():
    """Save multiple files to uploads/ and create PENDING audit entries for vision processing."""
    try:
        vision_model = request.form.get('visionModel', 'ollama_qwen3_vl')
        files = request.files.getlist('files') or request.files.getlist('file')
        files = [f for f in files if f and f.filename]
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        logger.info(f"Batch upload: received {len(files)} file(s): {[f.filename for f in files]}")
        batch_id = str(uuid.uuid4())
        results = []
        with _get_audit_db()() as conn:
            with conn.cursor() as cur:
                for f in files:
                    if not f.filename:
                        continue
                    name = secure_filename(f.filename)
                    unique = f"{uuid.uuid4().hex}_{name}"
                    dest = UPLOADS_DIR / unique
                    f.save(str(dest))
                    rel_path = str(dest.relative_to(BASE_PATH)) if dest.is_relative_to(BASE_PATH) else str(dest)
                    cur.execute(
                        """INSERT INTO admin_audit_log (action, document_id, status, file_path, batch_id, vision_model, details)
                         VALUES ('VISION_UPLOADED', %s, 'PENDING', %s, %s::uuid, %s, %s)""",
                        (unique, rel_path, batch_id, vision_model, f'Batch upload: {name}')
                    )
                    results.append({'id': unique, 'filename': name, 'path': rel_path})
        return jsonify({'success': True, 'data': {'batchId': batch_id, 'files': results}})
    except Exception as e:
        logger.error(f"Batch upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Per-file timeout for vision extraction (seconds); stuck items are marked FAILED
VISION_PROCESS_TIMEOUT = int(os.getenv("VISION_PROCESS_TIMEOUT", "90"))


def _process_one_vision_file(rid, full_path_str, vision_model):
    """Run vision extraction for one file; returns (success, normalized_dict or error_detail)."""
    from vision_extract import (
        extract_metadata_with_vision,
        normalize_extracted_to_form_data,
        _fallback_text_metadata,
    )
    extracted = extract_metadata_with_vision(full_path_str, vision_model)
    if not extracted:
        # Fallback: support plain text uploads even if vision is unavailable
        suffix = Path(full_path_str).suffix.lower()
        if suffix in (".txt", ".md"):
            try:
                from vision_extract import _fallback_text_metadata
                extracted = _fallback_text_metadata(full_path_str)
            except Exception:
                return False, "Vision extraction failed"
        else:
            return False, "Vision extraction failed"
    normalized = normalize_extracted_to_form_data(extracted)
    return True, normalized


@app.route('/api/admin/process-vision', methods=['POST'])
def process_vision():
    """Process PENDING vision uploads: mark as PROCESSING, run extraction with timeout, then PENDING_APPROVAL or FAILED."""
    import concurrent.futures
    try:
        from vision_extract import normalize_extracted_to_form_data
        data = request.get_json() or {}
        batch_id = data.get('batchId')
        limit = data.get('limit', 50)
        timeout_sec = min(int(data.get('timeout', VISION_PROCESS_TIMEOUT)), 300)
        with _get_audit_db()() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, file_path, vision_model FROM admin_audit_log
                     WHERE action = 'VISION_UPLOADED'
                     AND (status = 'PENDING' OR (status = 'PROCESSING' AND performed_at < now() - interval '2 minutes'))
                     AND (batch_id = %s::uuid OR %s IS NULL)
                     ORDER BY performed_at ASC LIMIT %s""",
                    (batch_id, batch_id, limit)
                )
                rows = cur.fetchall()
        processed = 0
        for row in rows:
            rid, file_path, vision_model = row['id'], row['file_path'], row['vision_model'] or 'ollama_qwen3_vl'
            full_path = BASE_PATH / file_path if not Path(file_path).is_absolute() else Path(file_path)
            if not full_path.exists():
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE admin_audit_log SET status = 'FAILED', details = 'File not found'
                                       WHERE id = %s""", (rid,))
                continue
            # Mark as PROCESSING (queue tag) so UI shows "processing"
            with _get_audit_db()() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE admin_audit_log SET status = 'PROCESSING', details = 'Extracting metadata...'
                           WHERE id = %s""", (rid,)
                    )
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(_process_one_vision_file, rid, str(full_path), vision_model)
                    ok, result = future.result(timeout=timeout_sec)
            except concurrent.futures.TimeoutError:
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s""",
                            (f"Timeout after {timeout_sec}s (vision model may be unavailable)", rid)
                        )
                logger.warning(f"Vision timeout ({timeout_sec}s) for audit id {rid}")
                continue
            except Exception as e:
                err_msg = str(e)[:500]
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s""",
                                    (f"Error: {err_msg}", rid))
                logger.exception(f"Vision error for {rid}")
                continue
            if ok and isinstance(result, dict):
                doc_type = result.get('documentType') or 'other'
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE admin_audit_log SET action = 'VISION_EXTRACTED', status = 'PENDING_APPROVAL',
                               extracted_data = %s, document_type = %s, details = %s WHERE id = %s""",
                            (json_module.dumps(result), doc_type, f'Extracted with {vision_model}', rid)
                        )
                processed += 1
            else:
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s""",
                                    (result if isinstance(result, str) else "Vision extraction failed", rid))
        return jsonify({'success': True, 'data': {'processed': processed, 'total': len(rows)}})
    except Exception as e:
        logger.error(f"Process vision error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/retry-vision', methods=['POST'])
def retry_vision():
    """Reset FAILED vision entries to PENDING and run extraction again (one or more audit IDs)."""
    import concurrent.futures
    try:
        from vision_extract import normalize_extracted_to_form_data
        data = request.get_json() or {}
        audit_ids = data.get('auditIds') or ([data.get('auditId')] if data.get('auditId') else [])
        if not audit_ids:
            return jsonify({'success': False, 'error': 'auditId or auditIds required'}), 400
        timeout_sec = min(int(data.get('timeout', VISION_PROCESS_TIMEOUT)), 300)
        processed = 0
        for aid in audit_ids:
            if not aid:
                continue
            with _get_audit_db()() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT id, file_path, vision_model FROM admin_audit_log
                         WHERE id = %s::uuid AND status = 'FAILED' AND file_path IS NOT NULL""",
                        (aid,)
                    )
                    row = cur.fetchone()
            if not row:
                continue
            rid, file_path, vision_model = row['id'], row['file_path'], row['vision_model'] or 'ollama_qwen3_vl'
            full_path = BASE_PATH / file_path if not Path(file_path).is_absolute() else Path(file_path)
            if not full_path.exists():
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE admin_audit_log SET details = 'File not found (cannot retry)' WHERE id = %s""", (rid,))
                continue
            with _get_audit_db()() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE admin_audit_log SET status = 'PROCESSING', details = 'Retrying extraction...' WHERE id = %s""",
                        (rid,)
                    )
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(_process_one_vision_file, rid, str(full_path), vision_model)
                    ok, result = future.result(timeout=timeout_sec)
            except concurrent.futures.TimeoutError:
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s""",
                            (f"Timeout after {timeout_sec}s", rid)
                        )
                continue
            except Exception as e:
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s""",
                                    (str(e)[:500], rid))
                continue
            if ok and isinstance(result, dict):
                doc_type = result.get('documentType') or 'other'
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE admin_audit_log SET action = 'VISION_EXTRACTED', status = 'PENDING_APPROVAL',
                               extracted_data = %s, document_type = %s, details = %s WHERE id = %s""",
                            (json_module.dumps(result), doc_type, f'Extracted with {vision_model}', rid)
                        )
                processed += 1
            else:
                with _get_audit_db()() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE admin_audit_log SET status = 'FAILED', details = %s WHERE id = %s""",
                                    (result if isinstance(result, str) else "Vision extraction failed", rid))
        return jsonify({'success': True, 'data': {'processed': processed, 'requested': len(audit_ids)}})
    except Exception as e:
        logger.exception("Retry vision error")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/approve-vision', methods=['POST'])
def approve_vision():
    """Move file from uploads to data/ by type/section and ENQUEUE for background RAG."""
    try:
        data = request.get_json() or {}
        audit_id = data.get('auditId')
        metadata = data.get('metadata')  # optional admin overrides
        if not audit_id:
            return jsonify({'success': False, 'error': 'auditId required'}), 400
        ok, resp = _approve_and_enqueue(audit_id, metadata)
        if not ok:
            return jsonify({'success': False, 'error': resp}), 400 if 'not found' in resp.lower() else 500
        return jsonify({'success': True, 'data': resp})
    except Exception as e:
        logger.error(f"Approve vision error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _approve_and_enqueue(audit_id: str, metadata_override: dict | None = None):
    """Shared helper to approve one audit row and enqueue RAG. Returns (ok, data_or_error)."""
    with _get_audit_db()() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id, file_path, extracted_data, document_type, status
                          FROM admin_audit_log WHERE id = %s::uuid AND status = 'PENDING_APPROVAL'""", (audit_id,))
            row = cur.fetchone()
    if not row:
        return False, "Audit entry not found or not pending approval"

    rid = str(row['id'])
    file_path, extracted_data, doc_type = row['file_path'], row['extracted_data'], row['document_type']
    full_path = BASE_PATH / file_path if not Path(file_path).is_absolute() else Path(file_path)
    if not full_path.exists():
        return False, "File not found in uploads"

    meta_src = metadata_override or extracted_data
    if not isinstance(meta_src, dict):
        try:
            meta_src = json_module.loads(meta_src) if meta_src else {}
        except Exception:
            meta_src = metadata_override or {}

    doc_type, section, category, is_binding = _normalize_ingest_fields(meta_src, doc_type)
    save_path = DATA_ROOT / ('companies_act' if category == 'companies_act' else 'non_binding')
    if category == 'companies_act':
        save_path = save_path / f'section_{section}' / doc_type.capitalize()
    else:
        save_path = save_path / doc_type.capitalize()
    save_path.mkdir(parents=True, exist_ok=True)
    dest = save_path / full_path.name
    if dest.resolve() == full_path.resolve():
        dest = save_path / (uuid.uuid4().hex + full_path.suffix)
    shutil.move(str(full_path), str(dest))

    with _get_audit_db()() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE admin_audit_log SET status = 'APPROVED', document_id = %s, details = 'Queued for RAG pipeline' WHERE id = %s::uuid",
                (str(dest), rid)
            )

    queue_pos = _rag_queue.qsize() + 1
    _rag_update(rid, stage='Queued', message=f'Position {queue_pos} in queue',
                queued_at=datetime.now().isoformat(), filename=dest.name, progress=0)
    _rag_queue.put({
        'audit_id': rid,
        'file_path': str(dest),
        'doc_type': doc_type,
        'category': category,
        'section': section,
    })
    logger.info(f"Enqueued RAG job for {dest.name} (position {queue_pos})")
    return True, {
        'filePath': str(dest),
        'auditId': rid,
        'queuePosition': queue_pos,
        'message': f'Queued for RAG processing (position {queue_pos})'
    }


@app.route('/api/admin/approve-vision-bulk', methods=['POST'])
def approve_vision_bulk():
    """
    Approve multiple PENDING_APPROVAL audit ids and enqueue each for RAG.
    Body: { auditIds: [..], metadataMap?: {auditId: {overrides}} }
    """
    try:
        data = request.get_json() or {}
        audit_ids = data.get('auditIds') or []
        metadata_map = data.get('metadataMap') or {}
        if not audit_ids:
            return jsonify({'success': False, 'error': 'auditIds required'}), 400
        results = []
        errors = []
        for aid in audit_ids:
            ok, resp = _approve_and_enqueue(aid, metadata_map.get(aid))
            if ok:
                results.append(resp)
            else:
                errors.append({'auditId': aid, 'error': resp})
        return jsonify({'success': True, 'data': {'approved': results, 'errors': errors}})
    except Exception as e:
        logger.error(f"Approve vision bulk error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/rag-status', methods=['GET'])
def get_rag_status():
    """Return live RAG job queue status. Optional ?auditIds=id1,id2 to filter."""
    filter_ids = None
    raw = request.args.get('auditIds', '').strip()
    if raw:
        filter_ids = set(i.strip() for i in raw.split(',') if i.strip())
    with _rag_jobs_lock:
        jobs = {
            k: dict(v) for k, v in _rag_jobs.items()
            if filter_ids is None or k in filter_ids
        }
    return jsonify({
        'success': True,
        'data': {
            'jobs': jobs,
            'queueSize': _rag_queue.qsize(),
        }
    })


@app.route('/api/admin/reject-vision', methods=['POST'])
def reject_vision():
    """Mark audit entry as REJECTED."""
    try:
        data = request.get_json() or {}
        audit_id = data.get('auditId')
        if not audit_id:
            return jsonify({'success': False, 'error': 'auditId required'}), 400
        with _get_audit_db()() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE admin_audit_log SET status = 'REJECTED', details = COALESCE(details, '') || '; Rejected by admin'
                               WHERE id = %s::uuid AND status = 'PENDING_APPROVAL' RETURNING id""", (audit_id,))
                if cur.rowcount == 0:
                    return jsonify({'success': False, 'error': 'Not found or not pending'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/audit', methods=['GET'])
def get_audit():
    """List admin audit log (vision + manual) from DB."""
    try:
        action = request.args.get('action', 'all')
        status = request.args.get('status', 'all')
        search = request.args.get('search', '').strip()
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 10)), 100)
        with _get_audit_db()() as conn:
            with conn.cursor() as cur:
                conditions = []
                params = []
                if action and action != 'all':
                    conditions.append("action = %s")
                    params.append(action)
                if status and status != 'all':
                    conditions.append("status = %s")
                    params.append(status)
                if search:
                    conditions.append("(details ILIKE %s OR document_id ILIKE %s OR document_type ILIKE %s)")
                    params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
                where = (" AND " + " AND ".join(conditions)) if conditions else ""
                params_count = list(params)
                params.extend([limit, (page - 1) * limit])
                cur.execute(
                    f"""SELECT id, action, document_id, document_type, performed_by, performed_at, details, status,
                               file_path, extracted_data, batch_id, vision_model
                        FROM admin_audit_log WHERE 1=1 {where}
                        ORDER BY performed_at DESC LIMIT %s OFFSET %s""",
                    params
                )
                rows = cur.fetchall()
                cur.execute(f"SELECT COUNT(*) AS c FROM admin_audit_log WHERE 1=1 {where}", params_count)
                total = cur.fetchone()['c']
        def row_to_entry(r):
            return {
                'id': str(r['id']),
                'action': r['action'],
                'documentId': r['document_id'] or '',
                'documentType': (r['document_type'] or 'other'),
                'performedBy': r['performed_by'] or 'admin',
                'performedAt': (r['performed_at'].isoformat() if r['performed_at'] else ''),
                'details': r['details'] or '',
                'status': r['status'],
                'filePath': r['file_path'],
                'extractedData': r['extracted_data'] if isinstance(r['extracted_data'], dict) else (json_module.loads(r['extracted_data']) if r['extracted_data'] else None),
                'batchId': str(r['batch_id']) if r['batch_id'] else None,
                'visionModel': r['vision_model'],
            }
        return jsonify({
            'success': True,
            'data': [row_to_entry(r) for r in rows],
            'pagination': {'page': page, 'limit': limit, 'total': total, 'totalPages': (total + limit - 1) // limit or 1}
        })
    except Exception as e:
        logger.error(f"Audit list error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chunk/<chunk_id>', methods=['GET'])
def get_chunk(chunk_id):
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
