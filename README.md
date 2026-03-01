# Companies Act 2013 Legal RAG System

A comprehensive Retrieval-Augmented Generation (RAG) system for the Companies Act, 2013 (India). This system enables semantic search and question-answering over legal documents including acts, rules, regulations, circulars, notifications, and other governance-related materials.

## Table of Contents

- [Theory & Background](#theory--background)
- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Database Schema](#database-schema)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Ingestion Pipeline](#ingestion-pipeline)
- [Retrieval System](#retrieval-system)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Theory & Background

### What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that enhances Large Language Model (LLM) responses by first retrieving relevant information from a knowledge base, then using that information to ground the LLM's response. This approach addresses several critical limitations of standalone LLMs:

1. **Hallucination**: LLMs can generate factually incorrect information. RAG constrains responses to retrieved facts.
2. **Knowledge Cutoff**: LLMs have training data limits. RAG allows access to fresh, up-to-date information.
3. **Attribution**: RAG provides source references, enabling verification of generated responses.
4. **Domain Specificity**: Legal, medical, and technical domains require precise terminology that general LLMs may mishandle.

### Why RAG for Legal Documents?

Legal documents present unique challenges that make RAG particularly valuable:

- **Volume**: The Companies Act 2013 has ~500 sections across 29 chapters, plus rules, regulations, and notifications.
- **Complexity**: Legal language is precise; minor wording changes alter meaning significantly.
- **Interconnectedness**: Sections reference other sections, rules, and schedules.
- **Authority Hierarchy**: Not all documents carry equal legal weight (Acts > Rules > Circulars).
- **Temporal Aspects**: Laws are amended, superseded, or retired over time.

### The Governance Layer

This system implements a **governance layer** on top of RAG to ensure legal accuracy:

- **Binding vs. Non-Binding**: Distinguishes statutory documents from guidance materials.
- **Priority Ordering**: Ensures higher-authority documents are prioritized in retrieval.
- **Refusal Policies**: Prevents answering from non-binding documents alone when binding documents exist.
- **Relationship Mapping**: Tracks how documents relate (amends, clarifies, implements, etc.).

### Hierarchical Chunking Strategy

Legal documents require special chunking strategies:

- **Parent Chunks**: Full document representation for context
- **Child Chunks**: Smaller segments (1000 chars) for precise retrieval
- **Overlap**: 100-character overlap maintains context between chunks
- **Metadata Inheritance**: Child chunks inherit document properties from parents

### Vector Embeddings

The system uses dense vector embeddings (1024-dimensional) to capture semantic meaning:

- **Embedding Model**: qwen3-embedding:0.6b (local Ollama model)
- **Similarity Metric**: Inner product (cosine similarity after normalization)
- **Threshold**: 0.5 similarity score filters out irrelevant results

### Hybrid Retrieval

The system combines multiple retrieval strategies:

1. **Direct Lookup**: When users specify section numbers, queries bypass vector search
2. **Definition Priority**: Queries about definitions prioritize Section 2
3. **Vector Search**: Semantic similarity for natural language queries
4. **Relationship Expansion**: Optionally includes related documents

## Overview

This is a legal knowledge management system designed specifically for corporate law compliance in India. It processes various types of legal documents, creates structured chunks, builds semantic embeddings, and provides an intelligent question-answering interface.

### Supported Document Types

| Document Type | Binding | Priority | Authority Level |
|--------------|---------|----------|-----------------|
| Act | Yes | 1 | Statutory |
| Rule | Yes | 1 | Statutory |
| Regulation | Yes | 1 | Statutory |
| Order | Yes | 2 | Interpretive |
| Notification | Yes | 2 | Interpretive |
| Circular | No | 2 | Interpretive |
| Schedule | Yes | 2 | Interpretive |
| SOP | No | 3 | Procedural |
| Form | No | 3 | Procedural |
| Guideline | No | 3 | Procedural |
| Practice Note | No | 4 | Commentary |
| Commentary | No | 4 | Commentary |
| Textbook | No | 4 | Commentary |
| QA Book | No | 4 | Commentary |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                         │
│                      (Port 3000 - React/TS)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask API Server (FastAPI)                   │
│                     (Port 5000 - Python/Flask)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│   PostgreSQL Database    │     │       FAISS Vector Store     │
│   (Port 5432)           │     │   (Local file-based index)   │
│   - chunks_identity      │     │   - metadata.json            │
│   - chunks_content       │     │   - faiss_index.bin          │
│   - 14 more tables...    │     │                             │
└─────────────────────────┘     └─────────────────────────────┘
              │
              ▼
┌─────────────────────────┐
│      Ollama Server      │
│  (Port 11434)           │
│  - qwen2.5:1.5b (LLM)   │
│  - qwen3-embedding:0.6b │
│  - qwen2-vl:7b (Vision) │
└─────────────────────────┘
```

## Directory Structure

```
RAG/
├── app/                              # Next.js frontend application
│   ├── src/                         # React source code
│   ├── public/                      # Static assets
│   ├── package.json                 # Node.js dependencies
│   └── start.bat                    # Startup script
│
├── companies_act_2013/
│   ├── governance_db/               # Core Python backend
│   │   ├── schema.sql               # Database schema (16 tables)
│   │   ├── db_config.py             # PostgreSQL connection
│   │   ├── init_db.py               # Database initialization
│   │   │
│   │   ├── # Ingestion Components
│   │   ├── pdf_parser.py            # PDF text extraction
│   │   ├── ocr_utils.py             # OCR for scanned PDFs
│   │   ├── chunking_engine_simple.py # Hierarchical chunking
│   │   ├── ingestion_service_simple.py # Chunk creation
│   │   ├── reference_extractor.py   # Cross-reference extraction
│   │   ├── summarize_and_keywords.py # LLM summarization
│   │   ├── unified_ingest_full.py   # Complete ingestion pipeline
│   │   ├── pipeline_full.py         # CLI for ingestion
│   │   │
│   │   ├── # Retrieval Components
│   │   ├── build_faiss_index.py     # Vector index builder
│   │   ├── retrieval_service_faiss.py # Hybrid retrieval
│   │   ├── governance_rules.py       # Document governance rules
│   │   ├── diagnose_retrieval.py    # Retrieval diagnostics
│   │   │
│   │   ├── # Utilities
│   │   ├── vision_extract.py        # Document metadata extraction
│   │   ├── embedding_worker.py      # Background embedding
│   │   ├── verify_db.py            # Database verification
│   │   ├── drop_all.py             # Database cleanup
│   │   │
│   │   ├── # SQL Migrations
│   │   ├── migrate_admin_audit.sql
│   │   ├── migrate_admin_audit_add_processing.sql
│   │   ├── optimize_indexes.sql
│   │   │
│   │   └── vector_store/            # FAISS index storage
│   │       ├── faiss_index.bin
│   │       └── metadata.json
│   │
│   └── app_faiss.py                # Flask API server
│
├── .venv/                           # Python virtual environment
├── requirements.txt                # Python dependencies
├── commands.md                     # Common commands reference
└── companiesactpdf.pdf             # Source PDF (if available)
```

## Database Schema

The system uses PostgreSQL with 16 interconnected tables. See `companies_act_2013/governance_db/schema.sql` for the complete schema.

### Core Tables

| Table | Description |
|-------|-------------|
| `chunks_identity` | Immutable core metadata (ID, type, section, binding) |
| `chunks_content` | Editable content (title, text, summary, citation) |
| `chunk_legal_anchors` | Legal text anchors/references |
| `chunk_keywords` | Extracted keywords for filtering |
| `chunk_relationships` | Cross-document relationships graph |
| `chunk_retrieval_rules` | Priority and query type rules |
| `chunk_refusal_policy` | Answer generation policies |
| `chunk_temporal` | Effective dates and validity |
| `chunk_lifecycle` | DRAFT/ACTIVE/RETIRED status |
| `chunk_versioning` | Version tracking |
| `chunk_embeddings` | Embedding model metadata |
| `chunk_lineage` | Source document tracking |
| `chunk_administrative` | Issued by, notification number |
| `chunk_audit` | Upload/approval tracking |
| `chunk_source` | File paths and URLs |
| `admin_audit_log` | Vision ingestion audit |

### Indexes

The schema includes optimized indexes for:
- Section-based lookups
- Document type filtering
- Full-text search (GIN)
- Parent-child relationships
- Priority ordering

## Features

### 1. Document Processing
- **PDF Parsing**: Extract text using pypdf
- **OCR Fallback**: Tesseract-based OCR for scanned documents
- **Multiple Format Support**: PDF, TXT, HTML
- **Vision Extraction**: AI-powered metadata extraction from PDFs

### 2. Hierarchical Chunking
- Parent chunks represent full documents
- Child chunks split for better retrieval (max 1000 chars)
- Overlapping chunks (100 char overlap) for context
- Structured chunk IDs: `ca2013_act_s001`, `ca2013_act_s001_c1`

### 3. Content Enrichment
- **Summaries**: LLM-generated 1-2 sentence summaries
- **Keywords**: 5-8 important keywords per chunk
- **Cross-References**: Automatic extraction of section references

### 4. Relationship Mapping
- Links between Acts, Rules, Notifications, Circulars
- Relationship types: clarifies, implements, proceduralises, amends, supersedes
- Bidirectional relationship tracking

### 5. Governance Rules
- Binding vs non-binding document classification
- Priority-based retrieval (1=statutory, 4=commentary)
- Authority level assignment
- Refusal policies for dependent documents

### 6. Hybrid Retrieval
- **Vector Search**: FAISS semantic similarity
- **Direct Lookup**: Section number queries
- **Definition Queries**: Special handling for Section 2
- **Relationship Expansion**: Include related documents

### 7. Answer Generation
- Context-aware LLM generation
- Citation extraction
- Source document tracking

## Prerequisites

### Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| PostgreSQL | 14+ | Primary database |
| Ollama | Latest | Local LLM & embeddings |

### Python Dependencies

```
requests
beautifulsoup4
lxml
pypdf
ollama
sentence-transformers
langchain
langchain-community
langchain-ollama
faiss-cpu
llama-index
llama-index-vector-stores-faiss
llama-index-embeddings-huggingface
llama-index-embeddings-ollama
llama-index-llms-ollama
psycopg2-binary
python-dotenv
flask
flask-cors
numpy
PyMuPDF
google-generativeai
```

### Node.js Dependencies

```
next: 16.1.6
react: 19.2.3
react-dom: 19.2.3
pg: 8.18.0
tailwindcss: 4
typescript: 5
```

## Installation

### 1. Database Setup (PostgreSQL)

```bash
# Using Docker (recommended)
docker run --name pg-db \
  --network pg-net \
  -e POSTGRES_USER=arya \
  -e POSTGRES_PASSWORD=secret123 \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  -d postgres:16

# Create database
docker exec -it pg-db createdb -U arya testdb
```

### 2. Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file in `companies_act_2013/governance_db/`:

```env
DB_NAME=testdb
DB_USER=arya
DB_PASSWORD=secret123
DB_HOST=localhost
DB_PORT=5432

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_LLM_MODEL=qwen2.5:1.5b
```

### 4. Initialize Database

```bash
cd companies_act_2013/governance_db
python init_db.py
```

### 5. Start Ollama

```bash
# Pull required models
ollama pull qwen2.5:1.5b
ollama pull qwen3-embedding:0.6b
ollama pull qwen2-vl:7b

# Start Ollama server
ollama serve
```

## Running the System

### Option 1: Full Stack

```bash
# Terminal 1: Start PostgreSQL (if using Docker)
docker start pg-db

# Terminal 2: Start Ollama
ollama serve

# Terminal 3: Start Flask API
cd companies_act_2013
python app_faiss.py

# Terminal 4: Start Next.js Frontend
cd app
npm run dev
```

### Option 2: Backend Only

```bash
# Start Flask API only (for API-based access)
cd companies_act_2013
python app_faiss.py
```

### Option 3: Ingestion Pipeline Only

```bash
# Initialize database
cd companies_act_2013/governance_db
python init_db.py

# Run full ingestion pipeline
cd companies_act_2013/governance_db
python pipeline_full.py --file <path_to_document> --type <document_type> --section <section_number>

# Example:
python pipeline_full.py --file ./data/companies_act/section_001/Act/companies_act_2013.pdf --type act --section 001
```

## Ingestion Pipeline

### Processing Stages

1. **Parsing**: Extract text from PDF/TXT/HTML
2. **Chunking**: Create parent and child chunks
3. **Summarization**: Generate LLM summaries
4. **Keywords**: Extract keywords
5. **Relationships**: Map cross-references
6. **Embedding**: Build FAISS vector index

### Chunk ID Structure

```
ca2013_{document_type}_s{section}_{file_ext}
ca2013_act_s001_pdf1           # Parent chunk
ca2013_act_s001_pdf1_c1        # Child chunk 1
ca2013_circular_s001_html      # Circular document
```

### Command-Line Options

```bash
python pipeline_full.py \
  --file <path> \              # Input file path (required)
  --type <type> \              # Document type (required)
  --category <cat> \            # companies_act or non_binding
  --section <num> \             # Section number (001-043)
  --skip-embed \                # Skip embedding generation
```

## Retrieval System

### Query Types

1. **Definition Queries**: Automatically prioritizes Section 2 (definitions)
2. **Section Queries**: Direct lookup by section number
3. **Semantic Queries**: Vector similarity search
4. **Hybrid Queries**: Combines direct lookup + vector search

### Retrieval Flow

```
User Query
    │
    ├─── Definition Query? ──► Search Section 2 ──► Return definitions
    │
    ├─── Section Number? ──► Direct DB lookup ──► + Vector search for supplements
    │
    └─── Semantic Query ──► FAISS Vector Search ──► Get top-k chunks
                              │
                              ▼
                        PostgreSQL Metadata
                              │
                              ▼
                        LLM Generation
                              │
                              ▼
                        Formatted Answer
```

## API Endpoints

### Flask API (app_faiss.py)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Submit question |
| `/health` | GET | Health check |
| `/search` | POST | Direct search |

### Next.js Frontend (app/)

| Route | Description |
|-------|-------------|
| `/` | Main search interface |
| `/admin` | Document ingestion |
| `/results` | Search results |

## Environment Variables

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_NAME` | testdb | Database name |
| `DB_USER` | arya | Database user |
| `DB_PASSWORD` | secret123 | Database password |
| `DB_HOST` | localhost | Database host |
| `DB_PORT` | 5432 | Database port |

### Ollama

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama API base |
| `OLLAMA_EMBEDDING_MODEL` | qwen3-embedding:0.6b | Embedding model |
| `OLLAMA_LLM_MODEL` | qwen2.5:1.5b | Generation model |
| `OLLAMA_VISION_MODEL` | qwen2-vl:7b | Vision model |

### Vision Extraction

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_MAX_PDF_PAGES` | 3 | Max pages for metadata |
| `VISION_MAX_TEXT_CHARS` | 30000 | Max text chars |

## Troubleshooting

### Common Issues

#### 1. "psycopg2 not found"

```bash
# Activate virtual environment
.venv\Scripts\activate

# Reinstall psycopg2
pip install psycopg2-binary
```

#### 2. "FAISS index not found"

```bash
# Build new index
cd companies_act_2013/governance_db
python build_faiss_index.py
```

#### 3. "Ollama connection refused"

```bash
# Start Ollama
ollama serve

# Or pull model explicitly
ollama pull qwen2.5:1.5b
ollama pull qwen3-embedding:0.6b
```

#### 4. "Database connection failed"

```bash
# Check PostgreSQL is running
docker ps

# Or start PostgreSQL
docker start pg-db

# Test connection
psql -h localhost -U arya -d testdb
```

#### 5. "No chunks found in retrieval"

```bash
# Verify database has data
cd companies_act_2013/governance_db
python verify_db.py

# Re-run ingestion if needed
python pipeline_full.py --file <document_path> --type act --section 001
```

### Diagnostic Commands

```bash
# Check database state
cd companies_act_2013/governance_db
python verify_db.py

# Check FAISS index
python -c "import json; print(len(json.load(open('vector_store/metadata.json'))))"

# Test retrieval
python retrieval_service_faiss.py
```

## Performance Notes

- **Embedding Dimension**: 1024
- **Chunk Size**: 1000 characters (child chunks)
- **Overlap**: 100 characters
- **Top-K Retrieval**: 15 chunks (configurable)
- **Similarity Threshold**: 0.5

## License

This project is for educational and research purposes. The Companies Act, 2013 documents are government works subject to applicable copyright laws in India.
