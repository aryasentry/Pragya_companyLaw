# Governance RAG System

PostgreSQL-based governance-grade RAG implementation for Companies Act 2013.

## Architecture

- **Parent-Child Chunking**: Parents store metadata (NOT embedded), children store text (embedded)
- **Governance Controls**: Binding status, retrieval priorities, refusal policies
- **Legal Safety**: Refuses answers without authoritative sources
- **Audit Trail**: Complete lineage tracking with approval workflow
- **Ollama Integration**: Local LLM (qwen2.5:1.5b) and embeddings (qwen3-embedding:0.6b)

## Database Schema

15 normalized tables with 5 enums:
- `chunks_identity` - Immutable core identity
- `chunks_content` - Editable text content (includes citation)
- `chunk_relationships` - Graph of legal dependencies
- `chunk_refusal_policy` - Anti-hallucination rules
- `chunk_lifecycle` - DRAFT → ACTIVE → RETIRED states
- ... and 10 more specialized tables

## Quick Start

### 1. Prerequisites

**Docker PostgreSQL** (already running):
```bash
docker ps | grep pg-db
# Should show: pg-db running on port 5432
```

**pgAdmin** (already running):
```bash
docker ps | grep pgadmin
# Should show: pgadmin running on port 5050
# Access at: http://localhost:5050
# Email: arya@gmail.com
# Password: admin123
```

**Ollama** with models:
```bash
ollama list
# Should show:
# qwen3-embedding:0.6b
# qwen2.5:1.5b
```

### 2. Install Python Dependencies

```bash
cd governance_db
pip install -r requirements.txt
```

### 3. Configure Environment

The `.env` file is already created with your Docker settings:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=testdb
DB_USER=arya
DB_PASSWORD=secret123

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_LLM_MODEL=qwen2.5:1.5b
```

### 4. Initialize Database

```bash
python setup.py
```

This will:
- ✅ Test PostgreSQL connection
- ✅ Test Ollama connection
- ✅ Create all 15 tables
- ✅ Verify schema integrity

### 5. Test Chunking (WITHOUT Embedding)

```bash
python test_chunking.py
```

This will:
1. Create a parent chunk (CSR Circular example)
2. Add full text content (stored for archival/audit, NEVER used for retrieval)
3. Split into child chunks (1000 char limit with 100 char overlap - optimal for legal text)
4. Verify schema compliance with chunk_format.txt
5. Display all data in terminal

**Expected Output:**
```
🧪 GOVERNANCE RAG - CHUNKING TEST SUITE
🔌 Testing database connection...
✅ Connected to PostgreSQL...
📝 Testing parent chunk creation...
✅ Parent chunk created: chunk_abc123...
✂️ Testing hierarchical chunking...
✅ Created 5 child chunks:
   1. chunk_abc123_c01
   2. chunk_abc123_c02
   ...
✅ Testing schema compliance...
✅ PASS: Parent chunk correctly NOT embedded
✅ ALL TESTS COMPLETED
```

## Usage

### Admin Workflow

#### 1. Create Parent Chunk
```python
from ingestion_service import create_parent_chunk

input_data = {
    'document_type': 'act',
    'act': 'Companies Act 2013',
    'section': '123',
    'title': 'Section 123: Provision Title',
    'compliance_area': 'Corporate Governance'
}

success, message, chunk_id = create_parent_chunk(input_data, 'admin@example.com')
print(f"Created: {chunk_id}")
```

#### 2. Add Text Content
```python
from ingestion_service import update_chunk_text

text = "Full section text here..."
success, msg = update_chunk_text(chunk_id, text, updated_by='admin@example.com')
```

#### 3. Split into Child Chunks
```python
from chunking_engine_v2 import hierarchical_chunk

success, msg, child_ids = hierarchical_chunk(
    parent_chunk_id=chunk_id,
    text=text,
    max_chars=1000,
    overlap=100,
    created_by='admin@example.com'
)
print(f"Created {len(child_ids)} child chunks")
```

#### 4. Generate Embeddings (Child Chunks Only)
```python
from embedding_worker import embed_child_chunks

success, msg, count = embed_child_chunks(chunk_id)
print(f"Embedded {count} chunks")
```

#### 5. Approve for Production
```python
from api_governance import approve_chunk_endpoint

# Changes status from DRAFT → ACTIVE
```

### User Search

```python
from retrieval_service_v2 import retrieve_with_governance

results = retrieve_with_governance(
    query="What are the penalties for non-compliance?",
    top_k=5,
    enforce_refusal=True
)

if results['refusal_triggered']:
    print(f"Refused: {results['refusal_reason']}")
else:
    for chunk in results['results']:
        print(chunk['text'])
        print(chunk['parent_metadata'])
```

## API Endpoints

### Admin Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/governance/chunks/create` | POST | Create parent chunk |
| `/api/governance/chunks/{id}/text` | PATCH | Update text |
| `/api/governance/chunks/{id}/split` | POST | Split into children |
| `/api/governance/chunks/{id}/embed` | POST | Generate embeddings |
| `/api/governance/chunks/{id}/approve` | POST | Approve chunk |
| `/api/governance/chunks/{id}` | GET | Get chunk details |
| `/api/governance/chunks` | GET | List chunks (with filters) |

### User Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/governance/search` | POST | Search with refusal policy |
| `/api/governance/search/anchor` | GET | Search by Act/Section |
| `/api/governance/chunks/active` | GET | Get active chunks |

## Governance Rules

### Binding Status
- **Binding**: act, rule, regulation
- **Non-binding**: notification, circular, guideline, faq, commentary

### Retrieval Priority
1. Acts (highest)
2. Rules, Regulations, Notifications
3. Circulars, Guidelines
4. FAQs, Commentary (lowest)

### Refusal Policies

| Priority | Can Answer Standalone | Must Reference Parent | Refuse if Missing |
|----------|----------------------|----------------------|-------------------|
| 1 (Acts) | ✅ Yes | ❌ No | ❌ No |
| 2 (Rules) | ❌ No | ✅ Yes (Act) | ✅ Yes |
| 3 (Circulars) | ❌ No | ✅ Yes (Rule) | ✅ Yes |
| 4 (Commentary) | ❌ No | ✅ Yes (Rule) | ✅ Yes |

## Key Features

### ✅ Parent Chunks Never Embedded
Parent chunks store metadata only. Child chunks are embedded for retrieval.

### ✅ Hierarchical Relationships
- `part_of`: Child belongs to parent
- `implements`: Rule implements Act
- `supersedes`: New version replaces old
- `precedes`: Sequential order

### ✅ Anti-Hallucination
Refusal policies prevent answering from insufficient sources.

### ✅ Temporal Awareness
Chunks track `date_issued`, `effective_from`, `effective_to` for point-in-time queries.

### ✅ Versioning
Full version history with lineage tracking.

## Database Constraints

### Immutable Fields (chunks_identity)
- chunk_id
- chunk_role
- parent_chunk_id
- document_type
- binding
- authority_level

### Editable Fields (chunks_content)
- title
- text
- summary
- compliance_area

### Lifecycle States
- **DRAFT**: Under review
- **ACTIVE**: Approved for retrieval
- **RETIRED**: Superseded/deprecated
- **ARCHIVED**: Historical record

## Example: Full Ingestion Pipeline

```python
# Step 1: Admin creates parent chunk
input_data = {
    'document_type': 'rule',
    'act': 'Companies Act 2013',
    'section': '456',
    'title': 'Rule 456: Corporate Governance Requirements',
    'issued_by': 'Ministry of Corporate Affairs',
    'notification_number': 'GSR 123(E)',
    'date_issued': '2023-01-15',
    'effective_from': '2023-04-01'
}

success, msg, chunk_id = create_parent_chunk(input_data, 'admin@mca.gov.in')

# Step 2: Add text
text = "Rule 456: Every company shall comply with..."
update_chunk_text(chunk_id, text, updated_by='admin@mca.gov.in')

# Step 3: Split into child chunks
success, msg, child_ids = hierarchical_chunk(chunk_id, text, max_chars=1000)

# Step 4: Embed children
embed_child_chunks(chunk_id)

# Step 5: Approve
# (Use API endpoint or direct DB update)

# Step 6: User searches
results = retrieve_with_governance("What are governance requirements?")
```

## Troubleshooting

### Database Connection Errors
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Verify database exists
psql -U postgres -l | grep companies_act_governance
```

### Embedding Errors
```bash
# Install sentence-transformers
pip install sentence-transformers

# Or use OpenAI (requires API key in .env)
OPENAI_API_KEY=sk-...
```

### Missing Tables
```bash
# Re-run initialization
python init_db.py
```

## License

MIT
