-- ============================================
-- GOVERNANCE DATABASE SCHEMA (FINAL)
-- Companies Act 2013 - Legal RAG System
-- ============================================

-- ============================================
-- ENUM TYPES
-- ============================================

CREATE TYPE chunk_role_enum AS ENUM ('parent', 'child');

CREATE TYPE document_type_enum AS ENUM (
  'act',
  'rule',
  'regulation',
  'order',
  'notification',
  'circular',
  'sop',
  'form',
  'guideline',
  'practice_note',
  'commentary',
  'textbook',
  'qa_book',
  'schedule',
  'register',
  'return',
  'qa',
  'other'
);

CREATE TYPE authority_level_enum AS ENUM (
  'statutory',
  'interpretive',
  'procedural',
  'commentary'
);

CREATE TYPE relationship_type_enum AS ENUM (
  'part_of',
  'precedes',
  'clarifies',
  'proceduralises',
  'proceduralised_by',
  'implements',
  'implemented_by',
  'amends',
  'amended_by',
  'supersedes',
  'superseded_by'
);

CREATE TYPE lifecycle_status_enum AS ENUM ('DRAFT', 'ACTIVE', 'RETIRED');

CREATE TYPE retrieval_priority_enum AS ENUM ('1', '2', '3', '4');

-- ============================================
-- 1. CHUNKS — IDENTITY (IMMUTABLE)
-- ============================================
CREATE TABLE chunks_identity (
  chunk_id TEXT PRIMARY KEY,
  chunk_role chunk_role_enum NOT NULL,
  parent_chunk_id TEXT REFERENCES chunks_identity(chunk_id),
  document_type document_type_enum NOT NULL,
  authority_level authority_level_enum NOT NULL,
  binding BOOLEAN NOT NULL,
  act TEXT,
  section TEXT,
  sub_section TEXT,
  page_number INTEGER,
  created_at TIMESTAMP DEFAULT now(),
  CONSTRAINT parent_child_consistency CHECK (
    (chunk_role = 'parent' AND parent_chunk_id IS NULL)
    OR
    (chunk_role = 'child' AND parent_chunk_id IS NOT NULL)
  )
);

CREATE INDEX idx_parent_chunk ON chunks_identity(parent_chunk_id);
CREATE INDEX idx_document_type ON chunks_identity(document_type);
CREATE INDEX idx_section ON chunks_identity(section);
CREATE INDEX idx_section_priority ON chunks_identity(section, chunk_id);
CREATE INDEX idx_binding_section ON chunks_identity(binding, section) WHERE binding = true;
CREATE INDEX idx_doctype_section ON chunks_identity(document_type, section);
CREATE INDEX idx_chunk_role ON chunks_identity(chunk_role);
CREATE INDEX idx_identity_covering ON chunks_identity(chunk_id, section, document_type, chunk_role, authority_level, binding, parent_chunk_id);
CREATE INDEX idx_section_lookup ON chunks_identity(section, chunk_role, chunk_id);
CREATE INDEX idx_parent_child_lookup ON chunks_identity(parent_chunk_id, chunk_id) WHERE parent_chunk_id IS NOT NULL;

-- ============================================
-- 2. CHUNKS — EDITABLE CONTENT
-- ============================================
CREATE TABLE chunks_content (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  title TEXT,
  compliance_area TEXT,
  text TEXT,
  summary TEXT,
  citation TEXT,
  updated_by TEXT,
  updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_compliance_area ON chunks_content(compliance_area);
CREATE INDEX idx_content_text_gin ON chunks_content USING gin(to_tsvector('english', text));
CREATE INDEX idx_content_title_gin ON chunks_content USING gin(to_tsvector('english', title));

-- ============================================
-- 3. LEGAL ANCHORS
-- ============================================
CREATE TABLE chunk_legal_anchors (
  chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  anchor TEXT,
  PRIMARY KEY (chunk_id, anchor)
);

-- ============================================
-- 4. KEYWORDS
-- ============================================
CREATE TABLE chunk_keywords (
  chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  keyword TEXT,
  PRIMARY KEY (chunk_id, keyword)
);

-- ============================================
-- 5. RELATIONSHIPS GRAPH
-- ============================================
CREATE TABLE chunk_relationships (
  from_chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  relationship relationship_type_enum NOT NULL,
  to_chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  created_by TEXT,
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (from_chunk_id, relationship, to_chunk_id)
);

-- ============================================
-- 6. RETRIEVAL CONTROLS
-- ============================================
CREATE TABLE chunk_retrieval_rules (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  priority retrieval_priority_enum NOT NULL,
  requires_parent_law BOOLEAN DEFAULT false,
  allowed_query_types TEXT[] DEFAULT '{}'
);

CREATE INDEX idx_retrieval_priority ON chunk_retrieval_rules(priority);

-- ============================================
-- 7. REFUSAL POLICY
-- ============================================
CREATE TABLE chunk_refusal_policy (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  can_answer_standalone BOOLEAN NOT NULL,
  must_reference_parent_law BOOLEAN NOT NULL,
  refuse_if_parent_missing BOOLEAN NOT NULL
);

-- ============================================
-- 8. TEMPORAL VALIDITY
-- ============================================
CREATE TABLE chunk_temporal (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  date_issued DATE,
  effective_from DATE,
  effective_to DATE
);

CREATE INDEX idx_temporal_dates ON chunk_temporal(effective_from, effective_to);

-- ============================================
-- 9. LIFECYCLE MANAGEMENT
-- ============================================
CREATE TABLE chunk_lifecycle (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  status lifecycle_status_enum NOT NULL,
  retired_on DATE,
  retired_reason TEXT
);

CREATE INDEX idx_lifecycle_status ON chunk_lifecycle(status);
CREATE INDEX idx_lifecycle_active ON chunk_lifecycle(status) WHERE status = 'ACTIVE';

-- ============================================
-- 10. VERSIONING
-- ============================================
CREATE TABLE chunk_versioning (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  version TEXT NOT NULL,
  supersedes_chunk_id TEXT REFERENCES chunks_identity(chunk_id),
  superseded_by_chunk_id TEXT REFERENCES chunks_identity(chunk_id)
);

-- ============================================
-- 11. EMBEDDING TRACKING
-- ============================================
CREATE TABLE chunk_embeddings (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL,
  model TEXT,
  vector_id TEXT,
  embedded_at TIMESTAMP
);

CREATE INDEX idx_embeddings_enabled ON chunk_embeddings(enabled);

-- ============================================
-- 12. LINEAGE & INTEGRITY
-- ============================================
CREATE TABLE chunk_lineage (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  parent_document_id TEXT,
  checksum TEXT,
  source_hash_verified BOOLEAN
);

-- ============================================
-- 13. ADMINISTRATIVE METADATA
-- ============================================
CREATE TABLE chunk_administrative (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  issued_by TEXT,
  notification_number TEXT,
  source_type TEXT,
  document_language TEXT,
  copyright_status TEXT CHECK (copyright_status IN ('copyrighted', 'public_domain', NULL)),
  copyright_attribution TEXT
);

-- ============================================
-- 14. AUDIT LOG
-- ============================================
CREATE TABLE chunk_audit (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  uploaded_by TEXT,
  uploaded_at TIMESTAMP,
  approved_by TEXT,
  approved_at TIMESTAMP
);

-- ============================================
-- 15. SOURCE REFERENCES
-- ============================================
CREATE TABLE chunk_source (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  path TEXT,
  url TEXT
);

-- ============================================
-- 16. ADMIN AUDIT LOG (Vision Batch Ingestion)
-- ============================================
CREATE TABLE admin_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action TEXT NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'INGEST', 'VISION_UPLOADED', 'VISION_EXTRACTED')),
  document_id TEXT,
  document_type TEXT,
  performed_by TEXT DEFAULT 'admin',
  performed_at TIMESTAMP DEFAULT now(),
  details TEXT,
  status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING', 'PENDING_APPROVAL', 'REJECTED', 'PROCESSING', 'APPROVED')),
  file_path TEXT,
  extracted_data JSONB,
  batch_id UUID,
  vision_model TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_admin_audit_status ON admin_audit_log(status);
CREATE INDEX idx_admin_audit_batch ON admin_audit_log(batch_id);
CREATE INDEX idx_admin_audit_performed_at ON admin_audit_log(performed_at DESC);

-- ============================================
-- STATISTICS UPDATE (run after schema creation)
-- ============================================
ANALYZE chunks_identity;
ANALYZE chunks_content;
ANALYZE chunk_temporal;
ANALYZE chunk_administrative;
ANALYZE chunk_retrieval_rules;
ANALYZE chunk_embeddings;
ANALYZE chunk_lifecycle;
