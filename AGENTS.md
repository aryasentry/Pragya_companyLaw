# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Pragya Company Law CompanyGPT - A RAG (Retrieval-Augmented Generation) application for querying India's Companies Act, 2013. The system uses semantic search over chunked legal documents with LLM-generated answers.

## Architecture

**Two-tier architecture:**
- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 (`app/`)
- **Backend**: Flask + Python (`companies_act_2013/`)

**RAG Pipeline:**
1. `chunking_engine.py` - Processes raw PDFs/text into structured chunks with LLM-generated metadata
2. `build_embeddings.py` - Creates FAISS vector index from chunks
3. `retrieval_pipeline_simple.py` - Handles semantic search + LLM answer generation
4. `app.py` - Flask API server exposing `/api/query` and `/api/health`

**LLM/Embedding Models (via Ollama):**
- Embeddings: `qwen3-embedding:0.6b`
- LLM: `qwen2.5:1.5b`

**Data flow:**
```
User Query → Next.js API → Flask Backend → FAISS Search → Ollama LLM → Response
```

## Development Commands

### Prerequisites
- Node.js 18+
- Python 3.8+
- Ollama running locally (`http://localhost:11434`)

### First-time Setup
```bash
# Frontend dependencies
cd app
npm install

# Backend dependencies (use project venv)
.venv\Scripts\pip install -r requirements.txt
```

### Running the Application

**Option 1: Batch script (Windows)**
```bash
cd app
start.bat
```

**Option 2: Manual (two terminals)**

Terminal 1 - Flask backend:
```bash
cd companies_act_2013
..\.venv\Scripts\python.exe app.py
```

Terminal 2 - Next.js frontend:
```bash
cd app
npm run dev
```

### Health Checks
- Flask: `http://localhost:5000/api/health`
- Next.js + Flask: `http://localhost:3000/api/health`

### Rebuilding Vector Store
If chunks change, rebuild embeddings:
```bash
cd companies_act_2013
..\.venv\Scripts\python.exe build_embeddings.py
```

### Processing New Sections
To chunk additional sections of the Act:
```bash
cd companies_act_2013
..\.venv\Scripts\python.exe chunking_engine.py
```
Edit `main()` in `chunking_engine.py` to specify section range.

## Key Files

### Backend (`companies_act_2013/`)
- `app.py` - Flask server, initializes `GovernanceRetriever`
- `retrieval_pipeline_simple.py` - Core RAG logic, FAISS search, LLM prompting
- `chunking_engine.py` - Document processing, metadata extraction
- `chunks/chunks_final.json` - Processed document chunks
- `vector_store/` - FAISS index and metadata

### Frontend (`app/src/`)
- `app/page.tsx` - Main search interface
- `app/api/query/route.ts` - Proxies to Flask backend
- `components/SynthesizedAnswer.tsx` - Renders LLM response with markdown
- `components/SectionResults.tsx` - Displays retrieved legal sections

## Important Patterns

### Chunk Structure
Each chunk in `chunks_final.json` has:
- `chunk_id` - Unique identifier (e.g., `ca2013_act_s007`)
- `document_type` - "act", "rules", "circulars", etc.
- `section` - Section number of the Companies Act
- `text` - Full text content
- `citation` - Legal citation string
- `compliance_area` - Category (e.g., "Company Incorporation")

### API Contract
POST `/api/query` expects:
```json
{ "query": "string" }
```
Returns:
```json
{
  "success": true,
  "result": {
    "synthesized_answer": "...",
    "answer_citations": ["Section 7", ...],
    "retrieved_sections": [...]
  }
}
```

## Environment Variables

Create `app/.env.local`:
```
FLASK_API_URL=http://localhost:5000
```
