"""
Flask API for Admin Ingestion Workflow

Endpoints:
- POST   /api/admin/ingest/upload          Upload + start processing
- GET    /api/admin/ingest/jobs            List active jobs
- GET    /api/admin/ingest/<job_id>        Get job preview
- PATCH  /api/admin/ingest/<job_id>        Update preview (admin edits)
- POST   /api/admin/ingest/<job_id>/approve  Approve and commit
- DELETE /api/admin/ingest/<job_id>        Cancel job
- GET    /api/admin/ingest/compliance-areas  Get compliance area options
- GET    /api/admin/ingest/section/<num>    Get section info
"""
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from companies_act_2013.governance_db.useless_files.admin_ingest_service import (
    start_ingestion,
    get_job,
    get_job_preview,
    update_job_preview,
    approve_and_commit,
    delete_job,
    list_active_jobs,
    get_compliance_areas,
    get_section_info,
    TEMP_DIR
)

app = Flask(__name__)
CORS(app)

# Config
UPLOAD_FOLDER = TEMP_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'png', 'jpg', 'jpeg', 'tiff', 'html'}

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/api/admin/ingest/upload', methods=['POST'])
def upload_and_start():
    """
    Upload a document and start the ingestion process.
    
    Form data:
    - file: The document file
    - document_type: Type of document (circular, notification, etc.)
    - section_number: Section number (e.g., "003")
    - compliance_areas: JSON array of compliance areas
    """
    # Check file
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {ALLOWED_EXTENSIONS}'}), 400
    
    # Get metadata
    document_type = request.form.get('document_type')
    section_number = request.form.get('section_number')
    compliance_areas = request.form.getlist('compliance_areas')
    
    if not document_type:
        return jsonify({'error': 'document_type is required'}), 400
    if not section_number:
        return jsonify({'error': 'section_number is required'}), 400
    if not compliance_areas:
        compliance_areas = ['General Provisions']
    
    # Save file temporarily
    filename = secure_filename(file.filename)
    file_path = UPLOAD_FOLDER / filename
    
    # Handle duplicates
    if file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        counter = 1
        while file_path.exists():
            file_path = UPLOAD_FOLDER / f"{stem}_{counter}{suffix}"
            counter += 1
    
    file.save(str(file_path))
    
    # Start ingestion
    result = start_ingestion(
        file_path=str(file_path),
        document_type=document_type,
        section_number=section_number,
        compliance_areas=compliance_areas
    )
    
    return jsonify(result), 202


@app.route('/api/admin/ingest/jobs', methods=['GET'])
def list_jobs():
    """List all active (non-completed) jobs"""
    jobs = list_active_jobs()
    return jsonify({'jobs': jobs, 'count': len(jobs)})


@app.route('/api/admin/ingest/<job_id>', methods=['GET'])
def get_preview(job_id):
    """Get job preview data"""
    preview = get_job_preview(job_id)
    
    if 'error' in preview and preview['error'] == 'Job not found':
        return jsonify(preview), 404
    
    return jsonify(preview)


@app.route('/api/admin/ingest/<job_id>', methods=['PATCH'])
def update_preview(job_id):
    """
    Update preview data (admin edits).
    
    JSON body can include:
    - title: New title
    - summary: New summary
    - keywords: New keywords array
    - compliance_areas: New compliance areas
    - parsed_text: Edited text (if admin corrects OCR errors)
    """
    updates = request.get_json()
    
    if not updates:
        return jsonify({'error': 'No updates provided'}), 400
    
    result = update_job_preview(job_id, updates)
    
    if 'error' in result:
        status = 404 if result['error'] == 'Job not found' else 400
        return jsonify(result), status
    
    return jsonify(result)


@app.route('/api/admin/ingest/<job_id>/approve', methods=['POST'])
def approve_job(job_id):
    """Approve the job and commit to database"""
    result = approve_and_commit(job_id)
    
    if 'error' in result:
        status = 404 if result['error'] == 'Job not found' else 400
        return jsonify(result), status
    
    return jsonify(result), 202


@app.route('/api/admin/ingest/<job_id>', methods=['DELETE'])
def cancel_job(job_id):
    """Cancel/delete a job"""
    success = delete_job(job_id)
    
    if not success:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({'message': 'Job cancelled', 'job_id': job_id})


@app.route('/api/admin/ingest/compliance-areas', methods=['GET'])
def compliance_areas():
    """Get list of valid compliance areas"""
    return jsonify({'compliance_areas': get_compliance_areas()})


@app.route('/api/admin/ingest/section/<section_number>', methods=['GET'])
def section_info(section_number):
    """Get information about a section (existing documents, relationships)"""
    info = get_section_info(section_number)
    return jsonify(info)


@app.route('/api/admin/ingest/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'service': 'admin_ingest',
        'upload_folder': str(UPLOAD_FOLDER),
        'allowed_extensions': list(ALLOWED_EXTENSIONS)
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Max size: 50MB'}), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("ADMIN INGESTION API")
    print("=" * 70)
    print(f"\nUpload folder: {UPLOAD_FOLDER}")
    print(f"Allowed extensions: {ALLOWED_EXTENSIONS}")
    print("\nEndpoints:")
    print("  POST   /api/admin/ingest/upload")
    print("  GET    /api/admin/ingest/jobs")
    print("  GET    /api/admin/ingest/<job_id>")
    print("  PATCH  /api/admin/ingest/<job_id>")
    print("  POST   /api/admin/ingest/<job_id>/approve")
    print("  DELETE /api/admin/ingest/<job_id>")
    print("  GET    /api/admin/ingest/compliance-areas")
    print("  GET    /api/admin/ingest/section/<num>")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
