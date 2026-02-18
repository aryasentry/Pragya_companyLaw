

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

-- 1️⃣ CHUNKS — IDENTITY (IMMUTABLE)
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

-- 2️⃣ CHUNKS — EDITABLE CONTENT
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

-- 3️⃣ LEGAL ANCHORS
CREATE TABLE chunk_legal_anchors (
  chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  anchor TEXT,
  PRIMARY KEY (chunk_id, anchor)
);

-- 4️⃣ KEYWORDS
CREATE TABLE chunk_keywords (
  chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  keyword TEXT,
  PRIMARY KEY (chunk_id, keyword)
);

-- 5️⃣ RELATIONSHIPS GRAPH
CREATE TABLE chunk_relationships (
  from_chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  relationship relationship_type_enum NOT NULL,
  to_chunk_id TEXT REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  created_by TEXT,
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (from_chunk_id, relationship, to_chunk_id)
);

-- 6️⃣ RETRIEVAL CONTROLS
CREATE TABLE chunk_retrieval_rules (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  priority retrieval_priority_enum NOT NULL,
  requires_parent_law BOOLEAN DEFAULT false,
  allowed_query_types TEXT[] DEFAULT '{}'
);

-- 7️⃣ REFUSAL POLICY
CREATE TABLE chunk_refusal_policy (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  can_answer_standalone BOOLEAN NOT NULL,
  must_reference_parent_law BOOLEAN NOT NULL,
  refuse_if_parent_missing BOOLEAN NOT NULL
);

-- 8️⃣ TEMPORAL VALIDITY
CREATE TABLE chunk_temporal (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  date_issued DATE,
  effective_from DATE,
  effective_to DATE
);

-- 9️⃣ LIFECYCLE MANAGEMENT
CREATE TABLE chunk_lifecycle (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  status lifecycle_status_enum NOT NULL,
  retired_on DATE,
  retired_reason TEXT
);

-- 🔟 VERSIONING
CREATE TABLE chunk_versioning (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  version TEXT NOT NULL,
  supersedes_chunk_id TEXT REFERENCES chunks_identity(chunk_id),
  superseded_by_chunk_id TEXT REFERENCES chunks_identity(chunk_id)
);

-- 1️⃣1️⃣ EMBEDDING TRACKING
CREATE TABLE chunk_embeddings (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL,
  model TEXT,
  vector_id TEXT,
  embedded_at TIMESTAMP
);

-- 1️⃣2️⃣ LINEAGE & INTEGRITY
CREATE TABLE chunk_lineage (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  parent_document_id TEXT,
  checksum TEXT,
  source_hash_verified BOOLEAN
);

-- 1️⃣3️⃣ ADMINISTRATIVE METADATA
CREATE TABLE chunk_administrative (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  issued_by TEXT,
  notification_number TEXT,
  source_type TEXT,
  document_language TEXT,
  copyright_status TEXT CHECK (copyright_status IN ('copyrighted', 'public_domain', NULL)),
  copyright_attribution TEXT
);

-- 1️⃣4️⃣ AUDIT LOG
CREATE TABLE chunk_audit (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  uploaded_by TEXT,
  uploaded_at TIMESTAMP,
  approved_by TEXT,
  approved_at TIMESTAMP
);

-- 1️⃣5️⃣ SOURCE REFERENCES
CREATE TABLE chunk_source (
  chunk_id TEXT PRIMARY KEY REFERENCES chunks_identity(chunk_id) ON DELETE CASCADE,
  path TEXT,
  url TEXT
);

-- Create indexes for common queries
CREATE INDEX idx_lifecycle_status ON chunk_lifecycle(status);
CREATE INDEX idx_embeddings_enabled ON chunk_embeddings(enabled);
CREATE INDEX idx_retrieval_priority ON chunk_retrieval_rules(priority);
