"""
Admin Ingestion Service - Staged Approval Workflow

Flow:
1. Admin uploads document + selects metadata (doc_type, section, compliance_area)
2. System parses PDF/OCR in background
3. System generates summary + keywords
4. Admin sees preview and can edit
5. On approval: commit to DB, create relationships, embed

API Endpoints (for Next.js admin panel):
- POST /api/admin/ingest/upload     → Upload + parse + preview
- GET  /api/admin/ingest/{job_id}   → Get job status/preview
- PATCH /api/admin/ingest/{job_id}  → Edit preview data
- POST /api/admin/ingest/{job_id}/approve → Commit to DB
- DELETE /api/admin/ingest/{job_id} → Cancel/discard
"""
import os
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

from db_config import get_db_connection


# ============================================================================
# CONFIGURATION
# ============================================================================

RAW_DIR = Path(__file__).parent.parent / "raw"
TEMP_DIR = Path(__file__).parent / "ingest_temp"
TEMP_DIR.mkdir(exist_ok=True)

# Document type to relationship mapping
RELATIONSHIP_RULES = {
    'rule': 'implements',
    'regulation': 'implements',
    'notification': 'implements',
    'circular': 'clarifies',
    'order': 'implements',
    'guideline': 'clarifies',
    'sop': 'proceduralises',
    'form': 'proceduralises',
    'schedule': 'proceduralises',
    'register': 'proceduralises',
    'return': 'proceduralises',
}

# Compliance areas
COMPLIANCE_AREAS = [
    "Company Incorporation",
    "Corporate Governance",
    "Share Capital & Debentures",
    "Prospectus & Capital Raising",
    "Board Meetings & Resolutions",
    "Accounts & Audit",
    "Deposits",
    "Directors & KMP",
    "Related Party Transactions",
    "Corporate Social Responsibility",
    "Mergers & Amalgamations",
    "Winding Up & Dissolution",
    "NCLT Proceedings",
    "Inspection & Investigation",
    "Producer Companies",
    "Nidhis",
    "Compromises & Arrangements",
    "Foreign Companies",
    "Government Companies",
    "Tribunal & Appellate",
    "Penalties & Prosecution",
    "General Provisions",
]


class JobStatus(str, Enum):
    PENDING = "pending"           # Just created
    PARSING = "parsing"           # PDF/OCR in progress
    GENERATING = "generating"     # Summary/keywords in progress
    READY = "ready"               # Preview ready for admin
    APPROVED = "approved"         # Admin approved, committing
    COMMITTED = "committed"       # Saved to DB
    EMBEDDING = "embedding"       # Creating embeddings
    COMPLETE = "complete"         # All done
    FAILED = "failed"             # Error occurred
    CANCELLED = "cancelled"       # Admin cancelled


@dataclass
class IngestJob:
    """Represents an ingestion job in progress"""
    job_id: str
    status: JobStatus
    created_at: str
    
    # Admin inputs
    document_type: str
    section_number: str
    compliance_areas: List[str]
    file_path: str
    file_name: str
    
    # Parsed data (filled during processing)
    parsed_text: Optional[str] = None
    parsed_at: Optional[str] = None
    parse_method: Optional[str] = None  # 'pdf', 'ocr', 'text'
    
    # Generated data (filled during processing)
    title: Optional[str] = None
    summary: Optional[str] = None
    keywords: List[str] = None
    generated_at: Optional[str] = None
    
    # Relationship info
    target_act_chunk_id: Optional[str] = None
    relationships_to_create: List[Dict] = None
    existing_relationships: List[Dict] = None
    
    # Final outputs
    chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = None
    committed_at: Optional[str] = None
    embedded_at: Optional[str] = None
    
    # Error info
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


# In-memory job storage (use Redis in production)
_jobs: Dict[str, IngestJob] = {}
_jobs_lock = threading.Lock()

# Background executor
_executor = ThreadPoolExecutor(max_workers=4)


# ============================================================================
# JOB MANAGEMENT
# ============================================================================

def create_job(
    file_path: str,
    document_type: str,
    section_number: str,
    compliance_areas: List[str]
) -> IngestJob:
    """Create a new ingestion job"""
    job_id = str(uuid.uuid4())[:8]
    
    job = IngestJob(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=datetime.now().isoformat(),
        document_type=document_type,
        section_number=section_number,
        compliance_areas=compliance_areas,
        file_path=file_path,
        file_name=Path(file_path).name,
        keywords=[],
        relationships_to_create=[],
        existing_relationships=[],
        child_chunk_ids=[],
    )
    
    with _jobs_lock:
        _jobs[job_id] = job
    
    return job


def get_job(job_id: str) -> Optional[IngestJob]:
    """Get job by ID"""
    with _jobs_lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **updates) -> Optional[IngestJob]:
    """Update job fields"""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)
        return job


def delete_job(job_id: str) -> bool:
    """Delete/cancel a job"""
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].status = JobStatus.CANCELLED
            # Clean up temp files if any
            return True
        return False


# ============================================================================
# PARSING
# ============================================================================

def parse_document(file_path: str) -> Dict[str, Any]:
    """
    Parse a document (PDF, image, or text).
    Returns: {'text': str, 'method': str, 'pages': int}
    """
    from pdf_parser import parse_document as pdf_parse
    from ocr_utils import ocr_image, ocr_pdf
    
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    result = {
        'text': '',
        'method': 'unknown',
        'pages': 0,
        'error': None
    }
    
    try:
        if ext == '.pdf':
            # Try text extraction first
            parsed = pdf_parse(str(file_path))
            text = parsed.get('text', '') if isinstance(parsed, dict) else parsed
            
            if text and len(text.strip()) > 100:
                result['text'] = text
                result['method'] = 'pdf_text'
                result['pages'] = parsed.get('pages', 1) if isinstance(parsed, dict) else 1
            else:
                # Fall back to OCR
                text = ocr_pdf(str(file_path))
                result['text'] = text
                result['method'] = 'pdf_ocr'
                
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            # Image - use OCR
            text = ocr_image(str(file_path))
            result['text'] = text
            result['method'] = 'ocr'
            
        elif ext in ['.txt', '.text']:
            # Plain text
            with open(file_path, 'r', encoding='utf-8') as f:
                result['text'] = f.read()
            result['method'] = 'text'
            
        elif ext == '.html':
            # HTML - extract text
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                result['text'] = soup.get_text(separator='\n')
            result['method'] = 'html'
            
        else:
            result['error'] = f"Unsupported file type: {ext}"
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


# ============================================================================
# SUMMARY & KEYWORDS GENERATION
# ============================================================================

def generate_summary_and_keywords(text: str, document_type: str) -> Dict[str, Any]:
    """Generate summary and keywords using LLM"""
    import requests
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen2.5:1.5b"
    
    result = {
        'title': '',
        'summary': '',
        'keywords': [],
        'error': None
    }
    
    if not text or len(text) < 50:
        result['error'] = "Text too short for analysis"
        return result
    
    text_sample = text[:3000] if len(text) > 3000 else text
    
    # Generate title + summary + keywords in one call
    prompt = f"""Analyze this legal document and provide:
1. A short title (max 10 words)
2. A 2-sentence summary of key provisions
3. 5-7 specific legal keywords (not generic terms)

Document type: {document_type}

Text:
{text_sample}

Respond in this exact JSON format:
{{"title": "...", "summary": "...", "keywords": ["...", "..."]}}
"""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 300}
            },
            timeout=60
        )
        
        if response.status_code == 200:
            raw_response = response.json().get('response', '')
            
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    result['title'] = parsed.get('title', '')
                    result['summary'] = parsed.get('summary', '')
                    result['keywords'] = parsed.get('keywords', [])
                except json.JSONDecodeError:
                    # Fallback: extract manually
                    result['summary'] = raw_response[:500]
                    
    except Exception as e:
        result['error'] = str(e)
    
    return result


# ============================================================================
# RELATIONSHIP CHECKING
# ============================================================================

def check_existing_relationships(section_number: str, document_type: str) -> Dict[str, Any]:
    """
    Check what relationships already exist for this section.
    Returns Act chunk ID and existing relationships.
    """
    result = {
        'act_chunk_id': None,
        'existing_chunks': [],
        'existing_relationships': [],
        'missing_relationships': []
    }
    
    section_padded = section_number.zfill(3)
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Find Act chunk for this section
        cur.execute("""
            SELECT chunk_id, cc.title
            FROM chunks_identity ci
            LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE ci.section = %s
            AND ci.document_type = 'act'
            AND ci.chunk_role = 'parent'
            LIMIT 1
        """, (section_padded,))
        
        act = cur.fetchone()
        if act:
            result['act_chunk_id'] = act['chunk_id']
        
        # Find all chunks in this section
        cur.execute("""
            SELECT ci.chunk_id, ci.document_type, cc.title
            FROM chunks_identity ci
            LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE ci.section = %s
            AND ci.chunk_role = 'parent'
            ORDER BY ci.document_type
        """, (section_padded,))
        
        result['existing_chunks'] = [
            {'chunk_id': r['chunk_id'], 'type': r['document_type'], 'title': r['title']}
            for r in cur.fetchall()
        ]
        
        # Find existing relationships
        if result['act_chunk_id']:
            cur.execute("""
                SELECT cr.from_chunk_id, cr.relationship, cr.to_chunk_id,
                       ci.document_type
                FROM chunk_relationships cr
                JOIN chunks_identity ci ON cr.from_chunk_id = ci.chunk_id
                WHERE cr.to_chunk_id = %s
            """, (result['act_chunk_id'],))
            
            result['existing_relationships'] = [
                {
                    'from': r['from_chunk_id'],
                    'type': r['document_type'],
                    'relationship': r['relationship']
                }
                for r in cur.fetchall()
            ]
        
        cur.close()
    
    return result


def determine_relationships_to_create(
    new_chunk_id: str,
    document_type: str,
    section_number: str,
    text: str
) -> List[Dict]:
    """
    Determine what relationships should be created for a new chunk.
    Combines document-type rules + text-extracted references.
    """
    from reference_extractor import extract_and_create_relationships, extract_references, resolve_reference_to_chunk_id
    
    relationships = []
    section_padded = section_number.zfill(3)
    
    # 1. Document-type based relationship (e.g., circular → clarifies → act)
    rel_type = RELATIONSHIP_RULES.get(document_type)
    if rel_type:
        # Find Act chunk
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE section = %s AND document_type = 'act' AND chunk_role = 'parent'
                LIMIT 1
            """, (section_padded,))
            act = cur.fetchone()
            cur.close()
            
            if act:
                relationships.append({
                    'from_chunk_id': new_chunk_id,
                    'to_chunk_id': act['chunk_id'],
                    'relationship': rel_type,
                    'source': 'document_type_rule',
                    'description': f"{document_type} → {rel_type} → Act Section {section_number}"
                })
    
    # 2. Text-extracted references
    refs = extract_references(text, section_number)
    for ref in refs:
        if ref.confidence >= 0.5:
            target = resolve_reference_to_chunk_id(ref, section_number)
            if target:
                relationships.append({
                    'from_chunk_id': new_chunk_id,
                    'to_chunk_id': target,
                    'relationship': ref.relationship,
                    'source': 'text_extraction',
                    'description': f"References {ref.ref_type} {ref.ref_number}",
                    'confidence': ref.confidence
                })
    
    return relationships


# ============================================================================
# MAIN WORKFLOW FUNCTIONS
# ============================================================================

def start_ingestion(
    file_path: str,
    document_type: str,
    section_number: str,
    compliance_areas: List[str]
) -> Dict[str, Any]:
    """
    Start the ingestion process. Returns job info immediately,
    processing happens in background.
    """
    # Create job
    job = create_job(file_path, document_type, section_number, compliance_areas)
    
    # Start background processing
    _executor.submit(_process_job_background, job.job_id)
    
    return {
        'job_id': job.job_id,
        'status': job.status.value,
        'message': 'Ingestion started. Poll /api/admin/ingest/{job_id} for status.'
    }


def _process_job_background(job_id: str):
    """Background processing: parse → generate → ready for review"""
    job = get_job(job_id)
    if not job:
        return
    
    try:
        # Step 1: Parse document
        update_job(job_id, status=JobStatus.PARSING)
        
        parse_result = parse_document(job.file_path)
        
        if parse_result.get('error'):
            update_job(job_id, 
                       status=JobStatus.FAILED, 
                       error=f"Parse error: {parse_result['error']}")
            return
        
        update_job(job_id,
                   parsed_text=parse_result['text'],
                   parse_method=parse_result['method'],
                   parsed_at=datetime.now().isoformat())
        
        # Step 2: Generate summary and keywords
        update_job(job_id, status=JobStatus.GENERATING)
        
        gen_result = generate_summary_and_keywords(
            parse_result['text'], 
            job.document_type
        )
        
        update_job(job_id,
                   title=gen_result.get('title', job.file_name),
                   summary=gen_result.get('summary', ''),
                   keywords=gen_result.get('keywords', []),
                   generated_at=datetime.now().isoformat())
        
        # Step 3: Check existing relationships
        rel_info = check_existing_relationships(job.section_number, job.document_type)
        
        update_job(job_id,
                   target_act_chunk_id=rel_info['act_chunk_id'],
                   existing_relationships=rel_info['existing_relationships'])
        
        # Step 4: Generate preview chunk_id
        preview_chunk_id = generate_chunk_id(
            job.document_type,
            job.section_number,
            job.file_name
        )
        
        # Step 5: Determine relationships to create
        relationships = determine_relationships_to_create(
            preview_chunk_id,
            job.document_type,
            job.section_number,
            parse_result['text']
        )
        
        update_job(job_id,
                   chunk_id=preview_chunk_id,
                   relationships_to_create=relationships,
                   status=JobStatus.READY)
        
    except Exception as e:
        update_job(job_id, status=JobStatus.FAILED, error=str(e))


def generate_chunk_id(document_type: str, section_number: str, file_name: str) -> str:
    """Generate a unique chunk ID"""
    section_padded = section_number.zfill(3)
    
    # Clean filename
    clean_name = Path(file_name).stem.lower()
    clean_name = ''.join(c if c.isalnum() or c == '-' else '-' for c in clean_name)
    clean_name = clean_name[:30]  # Limit length
    
    # Check for duplicates
    base_id = f"ca2013_{document_type}_s{section_padded}_{clean_name}"
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_id LIKE %s", 
                    (f"{base_id}%",))
        count = cur.fetchone()['count']
        cur.close()
    
    if count > 0:
        return f"{base_id}_{count + 1}"
    return base_id


def get_job_preview(job_id: str) -> Dict[str, Any]:
    """Get the preview data for admin review"""
    job = get_job(job_id)
    if not job:
        return {'error': 'Job not found'}
    
    return {
        'job_id': job.job_id,
        'status': job.status.value,
        'file_name': job.file_name,
        'document_type': job.document_type,
        'section_number': job.section_number,
        'compliance_areas': job.compliance_areas,
        
        # Parsed data
        'parsed_text': job.parsed_text,
        'parse_method': job.parse_method,
        'text_length': len(job.parsed_text) if job.parsed_text else 0,
        
        # Generated data (editable by admin)
        'title': job.title,
        'summary': job.summary,
        'keywords': job.keywords,
        
        # Relationship info
        'chunk_id': job.chunk_id,
        'target_act_chunk_id': job.target_act_chunk_id,
        'relationships_to_create': job.relationships_to_create,
        'existing_relationships': job.existing_relationships,
        
        # Error if any
        'error': job.error
    }


def update_job_preview(job_id: str, updates: Dict) -> Dict[str, Any]:
    """Admin edits the preview data"""
    job = get_job(job_id)
    if not job:
        return {'error': 'Job not found'}
    
    if job.status != JobStatus.READY:
        return {'error': f'Cannot edit job in status: {job.status.value}'}
    
    # Allowed editable fields
    editable = ['title', 'summary', 'keywords', 'compliance_areas', 'parsed_text']
    
    for key, value in updates.items():
        if key in editable:
            update_job(job_id, **{key: value})
    
    return get_job_preview(job_id)


def approve_and_commit(job_id: str) -> Dict[str, Any]:
    """Admin approves - commit to database and start embedding"""
    job = get_job(job_id)
    if not job:
        return {'error': 'Job not found'}
    
    if job.status != JobStatus.READY:
        return {'error': f'Cannot approve job in status: {job.status.value}'}
    
    update_job(job_id, status=JobStatus.APPROVED)
    
    # Start commit process in background
    _executor.submit(_commit_job_background, job_id)
    
    return {
        'job_id': job_id,
        'status': 'approved',
        'message': 'Committing to database...'
    }


def _commit_job_background(job_id: str):
    """Background: commit to DB, create relationships, embed"""
    from ingestion_service_simple import create_parent_chunk_simple, update_chunk_text_simple
    from chunking_engine_simple import hierarchical_chunk
    from embedding_worker import embed_child_chunks
    
    job = get_job(job_id)
    if not job:
        return
    
    try:
        update_job(job_id, status=JobStatus.COMMITTED)
        
        # Step 1: Create parent chunk
        parent_id = create_parent_chunk_with_data(
            chunk_id=job.chunk_id,
            document_type=job.document_type,
            section_number=job.section_number,
            title=job.title,
            summary=job.summary,
            keywords=job.keywords,
            compliance_areas=job.compliance_areas,
            text=job.parsed_text,
            file_path=job.file_path
        )
        
        update_job(job_id, chunk_id=parent_id, committed_at=datetime.now().isoformat())
        
        # Step 2: Create relationships
        for rel in job.relationships_to_create:
            create_relationship(
                rel['from_chunk_id'].replace(job.chunk_id, parent_id),  # Update if ID changed
                rel['to_chunk_id'],
                rel['relationship']
            )
        
        # Step 3: Create child chunks
        child_ids = hierarchical_chunk(
            parent_chunk_id=parent_id,
            text=job.parsed_text,
            max_chars=1000,
            overlap_chars=100
        )
        
        update_job(job_id, child_chunk_ids=child_ids)
        
        # Step 4: Create embeddings
        update_job(job_id, status=JobStatus.EMBEDDING)
        
        embed_child_chunks(parent_id)
        
        update_job(job_id, 
                   status=JobStatus.COMPLETE,
                   embedded_at=datetime.now().isoformat())
        
        # Step 5: Copy file to raw folder
        copy_to_raw_folder(job)
        
    except Exception as e:
        update_job(job_id, status=JobStatus.FAILED, error=str(e))


def create_parent_chunk_with_data(
    chunk_id: str,
    document_type: str,
    section_number: str,
    title: str,
    summary: str,
    keywords: List[str],
    compliance_areas: List[str],
    text: str,
    file_path: str
) -> str:
    """Create a parent chunk with all metadata"""
    section_padded = section_number.zfill(3)
    
    # Determine binding status
    binding = document_type in ['act', 'rule', 'regulation', 'order', 'notification']
    
    # Determine authority level
    authority_map = {
        'act': 'statutory',
        'rule': 'statutory',
        'regulation': 'statutory',
        'notification': 'statutory',
        'order': 'statutory',
        'circular': 'interpretive',
        'guideline': 'interpretive',
        'sop': 'procedural',
        'form': 'procedural',
        'register': 'procedural',
        'return': 'procedural',
        'schedule': 'statutory',
    }
    authority = authority_map.get(document_type, 'procedural')
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # 1. Insert identity
        cur.execute("""
            INSERT INTO chunks_identity (
                chunk_id, chunk_role, document_type, authority_level,
                binding, act, section
            ) VALUES (%s, 'parent', %s, %s, %s, 'Companies Act 2013', %s)
        """, (chunk_id, document_type, authority, binding, section_padded))
        
        # 2. Insert content
        cur.execute("""
            INSERT INTO chunks_content (
                chunk_id, title, compliance_area, text, summary, citation
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            chunk_id, 
            title, 
            ', '.join(compliance_areas),
            text,
            summary,
            f"Companies Act, 2013 — Section {section_number} — {document_type.title()}"
        ))
        
        # 3. Insert keywords
        for keyword in keywords:
            cur.execute("""
                INSERT INTO chunk_keywords (chunk_id, keyword)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (chunk_id, keyword))
        
        # 4. Insert source
        cur.execute("""
            INSERT INTO chunk_source (chunk_id, path)
            VALUES (%s, %s)
        """, (chunk_id, file_path))
        
        # 5. Insert lifecycle (ACTIVE)
        cur.execute("""
            INSERT INTO chunk_lifecycle (chunk_id, status)
            VALUES (%s, 'ACTIVE')
        """, (chunk_id,))
        
        # 6. Insert embeddings tracking (enabled for later)
        cur.execute("""
            INSERT INTO chunk_embeddings (chunk_id, enabled)
            VALUES (%s, FALSE)
        """, (chunk_id,))
        
        # 7. Insert audit
        cur.execute("""
            INSERT INTO chunk_audit (chunk_id, uploaded_by, uploaded_at, approved_by, approved_at)
            VALUES (%s, 'admin', NOW(), 'admin', NOW())
        """, (chunk_id,))
        
        cur.close()
    
    return chunk_id


def create_relationship(from_id: str, to_id: str, relationship: str) -> bool:
    """Create a relationship in the database"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chunk_relationships (from_chunk_id, to_chunk_id, relationship, created_by)
                VALUES (%s, %s, %s, 'admin_ingest')
                ON CONFLICT DO NOTHING
            """, (from_id, to_id, relationship))
            created = cur.rowcount > 0
            cur.close()
            return created
    except Exception as e:
        print(f"Error creating relationship: {e}")
        return False


def copy_to_raw_folder(job: IngestJob):
    """Copy the uploaded file to the appropriate raw folder"""
    import shutil
    
    section_padded = job.section_number.zfill(3)
    target_dir = RAW_DIR / f"section_{section_padded}" / job.document_type
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / job.file_name
    
    # Avoid overwriting
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    
    shutil.copy2(job.file_path, target_path)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_compliance_areas() -> List[str]:
    """Return list of valid compliance areas"""
    return COMPLIANCE_AREAS


def get_section_info(section_number: str) -> Dict[str, Any]:
    """Get information about a section"""
    rel_info = check_existing_relationships(section_number, 'any')
    
    return {
        'section_number': section_number,
        'has_act': rel_info['act_chunk_id'] is not None,
        'act_chunk_id': rel_info['act_chunk_id'],
        'existing_documents': rel_info['existing_chunks'],
        'total_documents': len(rel_info['existing_chunks']),
        'relationship_count': len(rel_info['existing_relationships'])
    }


def list_active_jobs() -> List[Dict]:
    """List all non-completed jobs"""
    with _jobs_lock:
        return [
            {
                'job_id': j.job_id,
                'status': j.status.value,
                'file_name': j.file_name,
                'document_type': j.document_type,
                'section': j.section_number,
                'created_at': j.created_at
            }
            for j in _jobs.values()
            if j.status not in [JobStatus.COMPLETE, JobStatus.CANCELLED, JobStatus.FAILED]
        ]


# ============================================================================
# CLI FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Admin Ingestion Service CLI')
    parser.add_argument('--file', type=str, help='File to ingest')
    parser.add_argument('--type', type=str, default='circular', help='Document type')
    parser.add_argument('--section', type=str, default='001', help='Section number')
    parser.add_argument('--compliance', type=str, nargs='+', default=['General Provisions'], help='Compliance areas')
    parser.add_argument('--auto-approve', action='store_true', help='Auto-approve without review')
    
    args = parser.parse_args()
    
    if not args.file:
        # Demo mode
        print("=" * 70)
        print("ADMIN INGESTION SERVICE - Demo")
        print("=" * 70)
        print("\nAvailable compliance areas:")
        for i, area in enumerate(COMPLIANCE_AREAS, 1):
            print(f"  {i:2}. {area}")
        
        print("\nUsage:")
        print("  python admin_ingest_service.py --file path/to/doc.pdf --type circular --section 003")
        print("\nAPI Endpoints:")
        print("  POST   /api/admin/ingest/upload     - Start ingestion")
        print("  GET    /api/admin/ingest/{job_id}   - Get preview")
        print("  PATCH  /api/admin/ingest/{job_id}   - Edit preview")
        print("  POST   /api/admin/ingest/{job_id}/approve - Commit")
        print("  DELETE /api/admin/ingest/{job_id}   - Cancel")
        
    else:
        print(f"\n📄 Starting ingestion for: {args.file}")
        print(f"   Type: {args.type}")
        print(f"   Section: {args.section}")
        print(f"   Compliance: {args.compliance}")
        
        # Start job
        result = start_ingestion(args.file, args.type, args.section, args.compliance)
        job_id = result['job_id']
        print(f"\n✓ Job created: {job_id}")
        
        # Poll until ready
        print("\n⏳ Processing...")
        while True:
            job = get_job(job_id)
            if not job:
                print("Job not found!")
                break
            
            print(f"   Status: {job.status.value}")
            
            if job.status == JobStatus.READY:
                break
            elif job.status == JobStatus.FAILED:
                print(f"\n❌ Error: {job.error}")
                break
            
            time.sleep(1)
        
        # Show preview
        if job.status == JobStatus.READY:
            preview = get_job_preview(job_id)
            
            print("\n" + "=" * 70)
            print("PREVIEW FOR ADMIN REVIEW")
            print("=" * 70)
            print(f"\n📋 Title: {preview['title']}")
            print(f"\n📝 Summary:\n{preview['summary']}")
            print(f"\n🏷️  Keywords: {', '.join(preview['keywords'])}")
            print(f"\n📊 Text length: {preview['text_length']} chars")
            print(f"   Parse method: {preview['parse_method']}")
            print(f"\n🔗 Relationships to create:")
            for rel in preview['relationships_to_create']:
                print(f"   • {rel['description']}")
            
            if args.auto_approve:
                print("\n" + "=" * 70)
                print("AUTO-APPROVING...")
                approve_result = approve_and_commit(job_id)
                
                # Wait for completion
                while True:
                    job = get_job(job_id)
                    print(f"   Status: {job.status.value}")
                    if job.status in [JobStatus.COMPLETE, JobStatus.FAILED]:
                        break
                    time.sleep(1)
                
                if job.status == JobStatus.COMPLETE:
                    print(f"\n✅ COMPLETE!")
                    print(f"   Chunk ID: {job.chunk_id}")
                    print(f"   Child chunks: {len(job.child_chunk_ids)}")
