# Complete Query-to-Answer Pipeline Flow

## 🔄 **End-to-End Query Processing Flow**

### **Overview:**
```
User Query → Query Analysis → Retrieval Strategy → Database/Vector Search → 
Context Building → LLM Prompting → Answer Generation → Response Formatting → User
```

---

## 📊 **Detailed Step-by-Step Flow**

### **PHASE 1: Query Reception & Routing**

#### Step 1: User Submits Query
**Location**: Frontend (`app/src/app/user/page.tsx`)
```
User types: "What is memorandum definition?"
↓
Frontend sends POST to /api/query
```

#### Step 2: API Route Handler
**Location**: `app/src/app/api/query/route.ts`
```typescript
POST /api/query
↓
Forwards to Flask backend: http://localhost:5000/query
```

#### Step 3: Flask Backend Receives Query
**Location**: `companies_act_2013/app_faiss.py`
```python
@app.route('/query', methods=['POST'])
def query_endpoint():
    user_query = request.json.get('query')
    ↓
    Calls: retrieval_service.query(user_query)
```

---

### **PHASE 2: Query Analysis & Strategy Selection**

#### Step 4: Query Analysis
**Location**: `retrieval_service_faiss.py` → `query()` method (line 295)

```python
# 4a. Log the query
logger.info(f"Query: {user_query}")

# 4b. Detect query type
is_definition_query = any(keyword in query.lower() for keyword in [
    'definition', 'define', 'meaning', 'means', 'what is', 'what does'
])

# 4c. Check for section number
section_match = re.search(r'section\s+(\d+)', query.lower())
```

**Decision Tree:**
```
Is it a definition query?
├─ YES → Go to Step 5 (Definition Path)
└─ NO → Is it a section query?
    ├─ YES → Go to Step 6 (Section Path)
    └─ NO → Go to Step 7 (General Path)
```

---

### **PHASE 3: Retrieval Strategy Execution**

#### **PATH A: Definition Query** (Steps 5a-5e)

**Step 5a: Extract Term**
```python
# Extract the term being defined
term_patterns = [
    r'definition\s+of\s+(["\'']?)(\w+(?:\s+\w+)*)\1',
    r'define\s+(["\'']?)(\w+(?:\s+\w+)*)\1',
    r'what\s+is\s+(?:a\s+|an\s+)?(["\'']?)(\w+(?:\s+\w+)*)\1'
]

# Example: "What is memorandum definition?"
# Extracts: term = "memorandum"
```

**Step 5b: Search Section 2 (Definitions)**
```python
# Direct database query to Section 002
with get_db_connection() as conn:
    cur.execute("""
        SELECT ci.chunk_id
        FROM chunks_identity ci
        JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
        WHERE ci.section = '002'
        AND ci.document_type = 'act'
        AND LOWER(cc.text) LIKE %s
        LIMIT 5
    """, (f'%{term.lower()}%',))
```

**Step 5c: Retrieve Chunk Details**
```python
definition_chunks = [row['chunk_id'] for row in cur.fetchall()]
# Example: ['002_act_001', '002_act_002']

chunk_details = self.get_chunk_details(definition_chunks)
# Fetches full text, metadata from database
```

**Step 5d: Skip to Answer Generation**
```python
# Go directly to Step 8 (no vector search needed)
```

---

#### **PATH B: Section Query** (Steps 6a-6d)

**Step 6a: Extract Section Number**
```python
section_num = section_match.group(1).zfill(3)
# Example: "section 17" → "017"
```

**Step 6b: Direct Section Lookup**
```python
with get_db_connection() as conn:
    cur.execute("""
        SELECT ci.chunk_id
        FROM chunks_identity ci
        WHERE ci.section = %s
        ORDER BY 
            CASE WHEN ci.chunk_role = 'parent' THEN 0 ELSE 1 END,
            ci.chunk_id
        LIMIT %s
    """, (section_num, top_k))
```

**Step 6c: Hybrid Search (Section + Vector)**
```python
# Get section chunks
chunk_ids = [row['chunk_id'] for row in cur.fetchall()]

# ALSO do vector search for related documents
vector_results = self.search_vectors(user_query, top_k)

# Combine both results
all_chunks = direct_chunks + vector_chunks
```

**Step 6d: Go to Answer Generation**
```python
# Proceed to Step 8
```

---

#### **PATH C: General Query** (Steps 7a-7c)

**Step 7a: Vector Search**
```python
vector_results = self.search_vectors(user_query, top_k)
# Uses FAISS to find semantically similar chunks
```

**Step 7b: Get Chunk Details**
```python
chunk_ids = [r['chunk_id'] for r in vector_results]
chunk_details = self.get_chunk_details(chunk_ids)
```

**Step 7c: Optional Relationships**
```python
if include_relationships:
    for chunk_id in chunk_details[:3]:
        relationships = self.get_chunk_relationships(chunk_id)
```

---

### **PHASE 4: Vector Search Details** (Used in Paths B & C)

#### Step 7a.1: Generate Query Embedding
**Location**: `search_vectors()` method (line 90)
```python
# Call Ollama to embed the query
response = requests.post(
    f"{OLLAMA_BASE_URL}/api/embeddings",
    json={
        'model': EMBEDDING_MODEL,  # qwen3-embedding:0.6b
        'prompt': query
    }
)

query_embedding = np.array(response.json()['embedding'])
# Returns: 1024-dimensional vector
```

#### Step 7a.2: FAISS Search
```python
# Load FAISS index
index = faiss.read_index('vector_store/faiss_index.bin')

# Search for similar vectors
distances, indices = index.search(
    query_embedding.reshape(1, -1), 
    top_k
)
```

#### Step 7a.3: Map to Chunk IDs
```python
# Load metadata mapping
with open('vector_store/metadata.json') as f:
    metadata = json.load(f)

# Get chunk IDs from indices
results = [
    {
        'chunk_id': metadata[idx]['chunk_id'],
        'similarity_score': 1 - (distances[0][i] / 2)  # Convert distance to similarity
    }
    for i, idx in enumerate(indices[0])
]
```

---

### **PHASE 5: Context Building**

#### Step 8: Build Context from Chunks
**Location**: `generate_answer()` method (line 163)

```python
context_parts = []
citations = []

for chunk in context_chunks:
    doc_type = chunk['document_type'].upper()
    section = chunk['section']
    title = chunk.get('title', '')
    text = chunk['text']
    
    citation = f"Section {section}"
    context_parts.append(f"[{doc_type}] {citation}: {title}\n{text}")
    citations.append(citation)

# Combine and limit size
context = "\n\n---\n\n".join(context_parts)[:8000]
```

**Example Context:**
```
[ACT] Section 002: Definitions
(56) "memorandum" means the memorandum of association...

---

[ACT] Section 004: Memorandum
The memorandum of a company shall state...
```

---

### **PHASE 6: LLM Prompting**

#### Step 9: Build Governance-Grade Prompt
**Location**: `generate_answer()` method (line 180)

```python
prompt = f"""You are a LEGAL COMPLIANCE ASSISTANT for the Companies Act, 2013 (India).

CRITICAL RULES - FOLLOW STRICTLY:
1. ONLY use information from the SOURCE DOCUMENTS below
2. NEVER add information not present in the sources
3. CITE the exact section number from the sources
4. If the question asks for a DEFINITION, provide ONLY the statutory definition
5. DO NOT mix definitions with procedures, forms, or rules unless asked
6. If sources don't contain the answer, say "The provided sources do not contain information about [topic]"

USER QUESTION:
{query}

SOURCE DOCUMENTS:
{context}

ANSWER STRUCTURE:

**[Main Answer Title]**

[Provide the direct answer from the sources - NO elaboration beyond what's written]

**Legal Reference:**
- Section [X]: [Exact provision or summary from source]

**Scope Notes:**
[ONLY if relevant - mention what this section does NOT cover]

FORMATTING RULES:
- Use **bold** for section numbers and key terms
- Use bullet points for lists
- Keep paragraphs short (2-3 sentences max)
- DO NOT quote entire sections verbatim
- DO NOT add procedural details unless the question asks for them

VALIDATION CHECKLIST (verify before responding):
✓ Every fact is from the source documents
✓ Section numbers match the sources exactly
✓ No information added from general knowledge
✓ Answer scope matches question scope (definition ≠ procedure)

WELL-FORMATTED MARKDOWN ANSWER:"""
```

---

### **PHASE 7: LLM Answer Generation**

#### Step 10: Call Ollama LLM
**Location**: `generate_answer()` method (line 224)

```python
response = requests.post(
    f"{OLLAMA_BASE_URL}/api/generate",
    json={
        'model': LLM_MODEL,  # qwen2.5:1.5b
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': 0.5,      # Balanced creativity
            'top_p': 0.9,            # Nucleus sampling
            'num_predict': 1024      # Max tokens
        }
    },
    timeout=60  # 60 second timeout
)
```

#### Step 11: Extract Answer
```python
if response.status_code == 200:
    answer_text = response.json().get('response', '')
    
    # Extract citations from answer
    citations_in_answer = re.findall(
        r'\*\*Section\s+(\d+(?:\(\d+\))?)\*\*',
        answer_text
    )
```

---

### **PHASE 8: Response Formatting**

#### Step 12: Format Final Response
**Location**: `query()` method (line 355 or 420)

```python
return {
    'answer': answer_result['answer'],
    'citations': answer_result['citations'],
    'retrieved_chunks': [
        {
            'chunk_id': chunk['chunk_id'],
            'section': chunk['section'],
            'document_type': chunk['document_type'],
            'text': chunk['text'][:500] + '...',
            'title': chunk['title'],
            'compliance_area': chunk['compliance_area'],
            'priority': chunk['priority'],
            'authority_level': chunk['authority_level'],
            'citation': chunk['citation'],
            'similarity_score': score_map.get(chunk['chunk_id'], 1.0)
        }
        for chunk in chunk_details
    ],
    'relationships': []  # Optional
}
```

---

### **PHASE 9: Response Delivery**

#### Step 13: Flask Returns to Next.js
**Location**: `app_faiss.py`
```python
return jsonify(result), 200
```

#### Step 14: Next.js API Route Forwards
**Location**: `app/src/app/api/query/route.ts`
```typescript
return NextResponse.json(data)
```

#### Step 15: Frontend Displays
**Location**: `app/src/app/user/page.tsx`
```typescript
// Display answer
<div>{result.answer}</div>

// Display source documents
{result.retrieved_chunks.map(chunk => (
    <SourceCard chunk={chunk} />
))}
```

---

## ⏱️ **Performance Metrics**

| Phase | Step | Typical Time | Bottleneck? |
|-------|------|--------------|-------------|
| 1 | API Routing | <100ms | No |
| 2 | Query Analysis | <10ms | No |
| 3 | Retrieval | 100-500ms | Sometimes |
| 4 | Vector Search | 50-200ms | No |
| 5 | Context Building | <50ms | No |
| 6 | Prompt Building | <10ms | No |
| 7 | LLM Generation | 2-60s | **YES** |
| 8 | Response Format | <50ms | No |
| 9 | Delivery | <100ms | No |

**Total**: 2-60 seconds (dominated by LLM)

---

## 🎯 **Optimization Points**

### **Current Optimizations:**
1. ✅ Definition queries → Direct DB (skip vector search)
2. ✅ Section queries → Direct lookup first
3. ✅ Incremental FAISS indexing
4. ✅ Context size limiting (8000 chars)
5. ✅ Governance-grade prompting

### **Potential Future Optimizations:**
1. Cache common queries
2. Parallel LLM calls for multi-part queries
3. Streaming responses
4. Pre-compute embeddings for common questions
5. Smart context truncation for large sections

---

## 🔍 **Debug Points**

To debug issues, check logs at each phase:

```python
# Phase 2: Query Analysis
logger.info(f"Query: {user_query}")
logger.info(f"Detected: {'definition' if is_definition_query else 'section' if section_match else 'general'}")

# Phase 3: Retrieval
logger.info(f"Found {len(chunks)} chunks")

# Phase 4: Vector Search
logger.info(f"Vector search returned {len(results)} results")

# Phase 7: LLM
logger.info(f"LLM response: {len(answer)} chars")
```

---

## 📝 **Summary**

**Total Steps**: 15
**Total Phases**: 9
**Critical Path**: Query → Analysis → Retrieval → LLM → Response
**Bottleneck**: LLM generation (2-60s)
**Optimizations**: Definition/section shortcuts, governance prompting

**System is fully operational!** 🚀
