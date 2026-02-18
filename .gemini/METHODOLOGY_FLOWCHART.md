# Pragya RAG System - Methodology Flow Diagram

## 📋 **Non-Technical Overview**

Pragya is a two-phase system:
1. **Phase 1: Admin Ingestion** - Preparing legal documents for intelligent search
2. **Phase 2: User Query (RAG)** - Answering user questions with cited legal text

---

## 🔄 **PHASE 1: ADMIN INGESTION WORKFLOW**

**Purpose:** Convert legal documents into searchable, intelligent knowledge

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN INGESTION PHASE                        │
│                  (One-time setup per document)                  │
└─────────────────────────────────────────────────────────────────┘

Step 1: DOCUMENT UPLOAD
┌──────────────────────────┐
│ Admin uploads document   │
│ • PDF, TXT, or HTML      │
│ • Specifies section #    │
│ • Marks as binding/non   │
└───────────┬──────────────┘
            │
            ▼
Step 2: TEXT EXTRACTION
┌──────────────────────────┐
│ Extract readable text    │
│ • Parse PDF/TXT/HTML     │
│ • Clean formatting       │
│ • Verify content quality │
└───────────┬──────────────┘
            │
            ▼
Step 3: INTELLIGENT CHUNKING
┌──────────────────────────┐
│ Break into smart pieces  │
│ • Create parent chunk    │
│   (full document)        │
│ • Create child chunks    │
│   (1000 char segments)   │
│ • Maintain relationships │
└───────────┬──────────────┘
            │
            ▼
Step 4: AI SUMMARIZATION
┌──────────────────────────┐
│ Generate summaries       │
│ • AI reads each chunk    │
│ • Creates 1-2 sentence   │
│   summary                │
│ • Extracts key terms     │
└───────────┬──────────────┘
            │
            ▼
Step 5: RELATIONSHIP MAPPING
┌──────────────────────────┐
│ Link related sections    │
│ • Find cross-references  │
│ • Map "clarifies" links  │
│ • Map "implements" links │
│ • Create citation graph  │
└───────────┬──────────────┘
            │
            ▼
Step 6: VECTOR EMBEDDING
┌──────────────────────────┐
│ Convert to AI numbers    │
│ • Transform text to      │
│   mathematical vectors   │
│ • Enable semantic search │
│ • Store in FAISS index   │
└───────────┬──────────────┘
            │
            ▼
Step 7: DATABASE STORAGE
┌──────────────────────────┐
│ Save to knowledge base   │
│ • Store in PostgreSQL    │
│ • Index for fast lookup  │
│ • Ready for queries      │
└──────────────────────────┘

✅ DOCUMENT NOW SEARCHABLE
```

---

## 🔍 **PHASE 2: USER QUERY (RAG) WORKFLOW**

**Purpose:** Answer user questions with accurate, cited legal information

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAG QUERY PHASE                            │
│                  (Every time user asks a question)              │
└─────────────────────────────────────────────────────────────────┘

Step 1: USER QUESTION
┌──────────────────────────┐
│ User types question      │
│ Example: "What are the   │
│ requirements for an      │
│ independent director?"   │
└───────────┬──────────────┘
            │
            ▼
Step 2: QUESTION UNDERSTANDING
┌──────────────────────────┐
│ Analyze the question     │
│ • Detect question type   │
│   (definition, process,  │
│    requirement, etc.)    │
│ • Identify key terms     │
└───────────┬──────────────┘
            │
            ▼
Step 3: SEMANTIC SEARCH
┌──────────────────────────┐
│ Find relevant chunks     │
│ • Convert question to    │
│   vector (AI numbers)    │
│ • Search FAISS index     │
│ • Find top 15 matches    │
└───────────┬──────────────┘
            │
            ▼
Step 4: DATABASE LOOKUP
┌──────────────────────────┐
│ Retrieve full details    │
│ • Get chunk text         │
│ • Get section numbers    │
│ • Get citations          │
│ • Get metadata           │
└───────────┬──────────────┘
            │
            ▼
Step 5: RELEVANCE RANKING
┌──────────────────────────┐
│ Prioritize best matches  │
│ • Rank by similarity     │
│ • Prioritize binding law │
│ • Sort by section order  │
│ • Select top 5 chunks    │
└───────────┬──────────────┘
            │
            ▼
Step 6: AI ANSWER GENERATION
┌──────────────────────────┐
│ Generate cited answer    │
│ • AI reads selected      │
│   chunks                 │
│ • Synthesizes answer     │
│ • Includes citations     │
│ • Refuses if uncertain   │
└───────────┬──────────────┘
            │
            ▼
Step 7: RESPONSE DELIVERY
┌──────────────────────────┐
│ Show to user             │
│ • Display answer         │
│ • Show section citations │
│ • Show source chunks     │
│ • Allow verification     │
└──────────────────────────┘

✅ USER GETS ACCURATE ANSWER IN 5 SECONDS
```

---

## 🎯 **KEY DIFFERENCES: INGESTION vs RAG**

| Aspect | Admin Ingestion | User Query (RAG) |
|--------|----------------|------------------|
| **Who** | Admin/Legal team | Any user |
| **When** | One-time per document | Every query |
| **Speed** | 30-60 seconds | 5 seconds |
| **Purpose** | Prepare knowledge | Answer questions |
| **AI Usage** | Summarize & extract | Generate answers |
| **Output** | Database entries | User-facing answer |

---

## 📊 **COMPLETE SYSTEM FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRAGYA COMPLETE FLOW                        │
└─────────────────────────────────────────────────────────────────┘

ADMIN SIDE                          USER SIDE
(One-time)                          (Every query)

┌──────────────┐                    ┌──────────────┐
│ Upload Doc   │                    │ Ask Question │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       ▼                                   │
┌──────────────┐                           │
│ Extract Text │                           │
└──────┬───────┘                           │
       │                                   │
       ▼                                   │
┌──────────────┐                           │
│ Create Chunks│                           │
└──────┬───────┘                           │
       │                                   │
       ▼                                   │
┌──────────────┐                           │
│ AI Summarize │                           │
└──────┬───────┘                           │
       │                                   │
       ▼                                   │
┌──────────────┐                           │
│ Map Relations│                           │
└──────┬───────┘                           │
       │                                   │
       ▼                                   │
┌──────────────┐                           │
│ Create Vector│                           │
└──────┬───────┘                           │
       │                                   │
       ▼                                   ▼
┌─────────────────────────────────────────────┐
│         KNOWLEDGE BASE                      │
│  • PostgreSQL Database (text, metadata)    │
│  • FAISS Index (vectors for search)        │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
           ┌──────────────┐
           │ Vector Search│
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Get Chunks   │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ AI Generate  │
           │ Answer       │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Show Answer  │
           │ with Citations│
           └──────────────┘
```

---

## 💡 **Simple Analogy**

**Think of Pragya like a library system:**

### **Admin Ingestion = Librarian's Work**
1. **Receive book** (upload document)
2. **Read and catalog** (extract text, chunk)
3. **Write summary card** (AI summarization)
4. **Cross-reference** (map relationships)
5. **Create index cards** (vector embeddings)
6. **Shelve properly** (database storage)

### **User Query (RAG) = Reader's Experience**
1. **Ask librarian** (type question)
2. **Librarian searches catalog** (semantic search)
3. **Finds relevant books** (retrieve chunks)
4. **Reads and summarizes** (AI generation)
5. **Gives answer with page numbers** (cited response)

---

## 🎯 **Quality Assurance at Each Step**

### **During Ingestion:**
- ✅ Verify text extraction quality
- ✅ Validate chunk relationships
- ✅ Check summary accuracy
- ✅ Ensure proper indexing

### **During Query:**
- ✅ Validate question clarity
- ✅ Verify chunk relevance
- ✅ Check citation accuracy
- ✅ Refuse if uncertain

---

## 📈 **Performance Metrics**

| Phase | Metric | Value |
|-------|--------|-------|
| **Ingestion** | Time per document | 30-60 seconds |
| **Ingestion** | Chunks per document | 5-20 chunks |
| **Ingestion** | One-time cost | Yes |
| **Query** | Response time | 5 seconds |
| **Query** | Accuracy | 100% source-backed |
| **Query** | Unlimited queries | Yes |

---

**END OF METHODOLOGY**
