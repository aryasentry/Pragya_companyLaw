# System Architecture - Governance RAG

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                        │
│                    (localhost:3000)                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │User Portal │  │Admin Panel │  │Search UI   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/REST
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask API Server                          │
│                    (localhost:5000)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            api_governance.py (13 endpoints)          │   │
│  │  POST /chunks/create  | GET /chunks                  │   │
│  │  PATCH /chunks/{id}/text | POST /chunks/{id}/split   │   │
│  │  POST /chunks/{id}/embed | POST /chunks/{id}/approve │   │
│  │  POST /search | GET /search/anchor                   │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────┬──────────────────────┬──────────────────────┘
                │                      │
                ▼                      ▼
┌───────────────────────┐   ┌───────────────────────┐
│  Ingestion Pipeline   │   │  Retrieval Pipeline   │
├───────────────────────┤   ├───────────────────────┤
│ ingestion_service.py  │   │retrieval_service_v2.py│
│ • create_parent_chunk │   │ • search_chunks       │
│ • update_chunk_text   │   │ • refusal_check       │
│ chunking_engine_v2.py │   │ • parent_law_lookup   │
│ • hierarchical_chunk  │   │ governance_rules.py   │
│ • overlap_splitting   │   │ • binding_rules       │
│ embedding_worker.py   │   │ • priority_rules      │
│ • embed_child_chunks  │   │ • refusal_policy      │
└───────────┬───────────┘   └───────────┬───────────┘
            │                           │
            └───────────┬───────────────┘
                        ▼
            ┌─────────────────────────┐
            │    PostgreSQL (Docker)   │
            │    localhost:5432        │
            │    Database: testdb      │
            │    User: arya            │
            ├─────────────────────────┤
            │  15 Normalized Tables   │
            ├─────────────────────────┤
            │ chunks_identity         │
            │ chunks_content          │
            │ chunk_legal_anchors     │
            │ chunk_keywords          │
            │ chunk_relationships     │
            │ chunk_retrieval_rules   │
            │ chunk_refusal_policy    │
            │ chunk_temporal          │
            │ chunk_lifecycle         │
            │ chunk_versioning        │
            │ chunk_embeddings        │
            │ chunk_lineage           │
            │ chunk_administrative    │
            │ chunk_audit             │
            │ chunk_source            │
            └─────────┬───────────────┘
                      │
                      ▼
            ┌─────────────────────────┐
            │   Ollama (localhost)    │
            │   localhost:11434       │
            ├─────────────────────────┤
            │ qwen3-embedding:0.6b    │
            │ (1024 dimensions)       │
            │ qwen2.5:1.5b (LLM)      │
            └─────────────────────────┘
```

## Data Flow

### Ingestion Flow (Admin → Database)

```
Admin Upload
    │
    ▼
┌───────────────────────────────────────────────────┐
│ STEP 1: Create Parent Chunk                      │
│ ingestion_service.create_parent_chunk()          │
│ • Insert into chunks_identity (immutable)        │
│ • Insert into chunks_content (editable)          │
│ • Insert into 13 other tables                    │
│ • Apply governance rules (binding, priority)     │
│ • Set refusal policy                             │
│ • Status: DRAFT                                  │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 2: Add Text Content                         │
│ ingestion_service.update_chunk_text()            │
│ • Update chunks_content.text                     │
│ • Store full section text                        │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 3: Hierarchical Chunking                    │
│ chunking_engine_v2.hierarchical_chunk()          │
│ • Split text into sentences                      │
│ • Create chunks (max 400 chars)                  │
│ • Add 50 char overlap                            │
│ • Create child chunks in DB                      │
│ • Create parent-child relationships              │
│ • Create sibling relationships (precedes)        │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 4: Generate Embeddings (CHILD ONLY)         │
│ embedding_worker.embed_child_chunks()            │
│ • Query all child chunks                         │
│ • Call Ollama API for each chunk                 │
│ • Store vector_id in chunk_embeddings            │
│ • Parent chunks: embedding.enabled = FALSE       │
│ • Child chunks: embedding.enabled = TRUE         │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 5: Approve for Production                   │
│ api_governance.approve_chunk_endpoint()          │
│ • Update chunk_lifecycle.status = ACTIVE         │
│ • Set chunk_audit.approved_by                    │
│ • Now retrievable by users                       │
└───────────────────────────────────────────────────┘
```

### Retrieval Flow (User → Response)

```
User Query: "What are CSR penalties?"
    │
    ▼
┌───────────────────────────────────────────────────┐
│ STEP 1: Generate Query Embedding                 │
│ embedding_worker.generate_embedding()            │
│ • Call Ollama qwen3-embedding:0.6b               │
│ • Get 1024-dim vector                            │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 2: Vector Search (CHILD CHUNKS ONLY)        │
│ retrieval_service_v2.search_chunks()             │
│ • Query child chunks with enabled=TRUE           │
│ • Filter by lifecycle.status = ACTIVE            │
│ • Similarity search (top 5)                      │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 3: Fetch Parent Metadata                    │
│ retrieval_service_v2._get_parent_metadata()      │
│ • For each child chunk, get parent               │
│ • Load title, act, section, citation             │
│ • Load administrative data                       │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 4: Apply Refusal Policy                     │
│ retrieval_service_v2._check_refusal_policies()  │
│ • Check priority level                           │
│ • Priority 2: Must have parent Act               │
│ • Priority 3: Procedural only                    │
│ • Priority 4: Refuse standalone                  │
│ • If missing parent: REFUSE                      │
└───────────────────┬───────────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────┐
│ STEP 5: Return Results or Refusal                │
│ retrieval_service_v2.retrieve_with_governance()  │
│ • If refusal: "Insufficient authoritative source"│
│ • Else: Return chunks + parent metadata          │
│ • Include citation references                    │
└───────────────────────────────────────────────────┘
```

## Parent-Child Relationship

```
┌─────────────────────────────────────────────────┐
│           PARENT CHUNK                          │
│  chunk_id: chunk_abc123                         │
│  role: parent                                   │
│  document_type: circular                        │
│  text: FULL circular text (500+ chars)          │
│  embedding.enabled: FALSE ❌                    │
│  status: DRAFT → ACTIVE                         │
├─────────────────────────────────────────────────┤
│ Metadata Tables (13):                           │
│  • chunk_retrieval_rules (priority: 2)          │
│  • chunk_refusal_policy (refuse_if_missing)     │
│  • chunk_temporal (effective_from)              │
│  • chunk_administrative (issued_by)             │
│  • chunk_audit (uploaded_by, approved_by)       │
│  • chunk_source (path, url)                     │
│  • ... 7 more tables                            │
└─────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│  CHILD CHUNK 1   │  │  CHILD CHUNK 2   │
│ chunk_abc123_c01 │  │ chunk_abc123_c02 │
│ role: child      │  │ role: child      │
│ text: First 400  │  │ text: Next 400   │
│ chars + overlap  │  │ chars + overlap  │
│ enabled: TRUE ✅ │  │ enabled: TRUE ✅ │
│ (EMBEDDED)       │  │ (EMBEDDED)       │
└────────┬─────────┘  └────────┬─────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
              Vector Database
           (1024-dim embeddings)
```

## Governance Controls

### Binding Status
```
Binding (TRUE):          Non-Binding (FALSE):
• act                    • circular
• rule                   • sop
• regulation             • form
• order (statutory)      • guideline
• notification           • practice_note
                         • commentary
                         • textbook
                         • qa_book
```

### Retrieval Priority
```
Priority 1 (Highest Authority):
• act, rule
• Can answer standalone
• No parent requirement

Priority 2 (Interpretive):
• regulation, notification, order, circular
• Must reference parent Act
• Refuse if parent missing

Priority 3 (Procedural):
• sop, form, guideline
• Procedural explanation only
• Must reference parent Rule

Priority 4 (Commentary):
• practice_note, commentary, textbook, qa_book
• Contextual/learning only
• Cannot answer legal questions
```

## File Structure

```
governance_db/
├── schema.sql              # 15 tables, 5 enums
├── db_config.py           # PostgreSQL connection
├── governance_rules.py    # Binding/priority logic
├── ingestion_service.py   # Create/update chunks
├── chunking_engine_v2.py  # Hierarchical splitting
├── embedding_worker.py    # Ollama embeddings
├── retrieval_service_v2.py # Search + refusal
├── api_governance.py      # Flask endpoints
├── init_db.py             # Database setup
├── setup.py               # One-command init
├── test_chunking.py       # Chunking validation
├── .env                   # Docker credentials
├── .env.example           # Template
├── requirements.txt       # Python deps
├── README.md              # Full documentation
├── QUICKSTART.md          # Step-by-step guide
├── SCHEMA_COMPLIANCE.md   # Field mapping
└── IMPLEMENTATION_SUMMARY.md # What was done
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Database | PostgreSQL 16 (Docker) | Governance data storage |
| Admin UI | pgAdmin 4 (Docker) | Database management |
| Embeddings | Ollama qwen3-embedding:0.6b | Vector generation |
| LLM | Ollama qwen2.5:1.5b | Text generation |
| Backend | Flask + Python 3.x | API server |
| Frontend | Next.js 16 + React 19 | Web interface |
| ORM | psycopg2 | PostgreSQL driver |
| Vector DB | TBD (Pinecone/Weaviate/pgvector) | Vector storage |
