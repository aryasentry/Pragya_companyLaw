# Compliance Areas in RAG Pipeline - Complete Guide

**Date:** February 12, 2026  
**Topic:** Understanding Compliance Areas  
**Purpose:** Categorization, filtering, and user navigation

---

## 📋 **What Are Compliance Areas?**

**Compliance areas** are **categorical tags** that classify legal documents by their **subject matter** or **functional domain** within the Companies Act, 2013.

Think of them as **topic labels** that help organize and filter legal content.

---

## 🎯 **Purpose in the RAG Pipeline**

### **1. Content Categorization**
Compliance areas organize documents into logical business domains:

```
Example:
- Section 149 → "Board of Directors"
- Section 135 → "Corporate Social Responsibility"
- Section 2(20) → "Definitions"
- Section 73 → "Deposits and Loans"
```

### **2. User Navigation**
Helps users find related content:

```
User searches: "director requirements"
System can filter by: compliance_area = "Board of Directors"
Returns: All director-related sections together
```

### **3. Contextual Retrieval**
Improves RAG accuracy by grouping related chunks:

```
Query: "What are CSR obligations?"
System prioritizes: compliance_area = "Corporate Social Responsibility"
Better context: All CSR-related sections retrieved together
```

### **4. Frontend Display**
Allows UI to show document categories:

```tsx
<div className="compliance-badge">
  {chunk.compliance_area}
</div>
```

---

## 🗂️ **Common Compliance Areas**

Based on the Companies Act, 2013 structure:

### **Corporate Governance:**
- Board of Directors
- Board Meetings
- Audit and Auditors
- Internal Controls
- Secretarial Standards

### **Financial:**
- Share Capital
- Deposits and Loans
- Accounts and Financial Statements
- Dividends
- Investments

### **Compliance & Reporting:**
- Annual Returns
- Registers and Records
- Inspection and Investigation
- Compromises and Arrangements

### **Corporate Actions:**
- Incorporation
- Mergers and Amalgamations
- Winding Up
- Removal of Names

### **Stakeholder Relations:**
- Shareholders Rights
- Corporate Social Responsibility
- Related Party Transactions
- Insider Trading

### **Specialized:**
- Producer Companies
- Nidhi Companies
- Government Companies
- Listed Companies

### **General:**
- Definitions
- General Provisions
- Penalties and Prosecutions
- Miscellaneous

---

## 💾 **Database Schema**

### **Storage:**
```sql
CREATE TABLE chunks_content (
  chunk_id TEXT PRIMARY KEY,
  title TEXT,
  compliance_area TEXT,  -- ← Stored here
  text TEXT,
  summary TEXT,
  citation TEXT
);
```

### **Example Data:**
```sql
INSERT INTO chunks_content VALUES (
  'ca2013_act_s149_p001',
  'Independent Directors',
  'Board of Directors',  -- ← Compliance area
  'Every listed company shall have...',
  'Requirements for independent directors',
  'Section 149(4)'
);
```

---

## 🔄 **Data Flow**

### **1. Ingestion (Admin UI):**
```
Admin fills form:
├─ Document Type: Act
├─ Section: 149
├─ Compliance Area: "Board of Directors"  ← Admin selects
└─ Text: "Every listed company..."

↓

Stored in chunks_content table
```

### **2. Retrieval (Query):**
```
User query: "independent director requirements"

↓

Vector search finds chunks

↓

Database returns:
{
  chunk_id: "ca2013_act_s149_p001",
  section: "149",
  compliance_area: "Board of Directors",  ← Retrieved
  text: "Every listed company...",
  title: "Independent Directors"
}

↓

Frontend displays compliance area badge
```

### **3. Display (Frontend):**
```tsx
{chunks.map(chunk => (
  <div key={chunk.chunk_id}>
    <span className="badge">{chunk.compliance_area}</span>
    <h3>{chunk.title}</h3>
    <p>{chunk.text}</p>
  </div>
))}
```

---

## 🎨 **Frontend Usage**

### **Current Implementation:**

**In `admin.ts`:**
```typescript
export interface IngestionFormData {
  // ...
  complianceArea: string;  // Required field
  // ...
}
```

**In `IngestionForm.tsx`:**
```tsx
<input
  type="text"
  value={formData.complianceArea}
  onChange={(e) => handleChange('complianceArea', e.target.value)}
  placeholder="e.g., Board of Directors"
  required
/>
```

**Validation:**
```typescript
if (!formData.complianceArea) {
  newErrors.complianceArea = 'Compliance area is required';
}
```

---

## 🔍 **Retrieval Service Usage**

### **Current Code:**
```python
# retrieval_service_faiss.py
def get_chunk_details(self, chunk_ids: List[str]) -> List[Dict]:
    query = """
        SELECT 
            ci.chunk_id,
            ci.section,
            cc.text,
            cc.title,
            cc.compliance_area,  -- ← Retrieved
            cc.citation
        FROM chunks_identity ci
        JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
        WHERE ci.chunk_id = ANY(%s)
    """
```

### **Response Format:**
```json
{
  "retrieved_chunks": [
    {
      "chunk_id": "ca2013_act_s149_p001",
      "section": "149",
      "compliance_area": "Board of Directors",
      "title": "Independent Directors",
      "text": "Every listed company shall...",
      "similarity_score": 0.92
    }
  ]
}
```

---

## 📊 **Use Cases**

### **1. Filtered Search**
```python
# Future enhancement: Filter by compliance area
def query_by_compliance_area(query: str, area: str):
    """
    Search within specific compliance area
    """
    cursor.execute("""
        SELECT chunk_id FROM chunks_content
        WHERE compliance_area = %s
        AND text ILIKE %s
    """, (area, f'%{query}%'))
```

### **2. Related Documents**
```python
# Find all documents in same compliance area
def get_related_by_compliance(chunk_id: str):
    """
    Get related chunks from same compliance area
    """
    cursor.execute("""
        SELECT c2.chunk_id, c2.title
        FROM chunks_content c1
        JOIN chunks_content c2 ON c1.compliance_area = c2.compliance_area
        WHERE c1.chunk_id = %s AND c2.chunk_id != %s
    """, (chunk_id, chunk_id))
```

### **3. Compliance Dashboard**
```python
# Show document count by compliance area
def get_compliance_stats():
    """
    Get statistics by compliance area
    """
    cursor.execute("""
        SELECT 
            compliance_area,
            COUNT(*) as doc_count
        FROM chunks_content
        GROUP BY compliance_area
        ORDER BY doc_count DESC
    """)
```

---

## 🚀 **Future Enhancements**

### **1. Compliance Area Dropdown**
Instead of free text, provide predefined options:

```tsx
const COMPLIANCE_AREAS = [
  'Board of Directors',
  'Corporate Social Responsibility',
  'Share Capital',
  'Accounts and Financial Statements',
  // ... etc
];

<select value={formData.complianceArea}>
  {COMPLIANCE_AREAS.map(area => (
    <option key={area} value={area}>{area}</option>
  ))}
</select>
```

### **2. Compliance Area Filter in Search**
```tsx
<div className="search-filters">
  <input type="text" placeholder="Search..." />
  <select>
    <option value="">All Areas</option>
    <option value="Board of Directors">Board of Directors</option>
    <option value="CSR">Corporate Social Responsibility</option>
  </select>
</div>
```

### **3. Compliance Area Badges**
```tsx
<div className="chunk-card">
  <span className="compliance-badge bg-blue-100 text-blue-800">
    {chunk.compliance_area}
  </span>
  <h3>{chunk.title}</h3>
  <p>{chunk.text}</p>
</div>
```

### **4. Compliance Area Navigation**
```tsx
<nav className="compliance-nav">
  <h3>Browse by Compliance Area</h3>
  <ul>
    <li><a href="/compliance/board">Board of Directors (45)</a></li>
    <li><a href="/compliance/csr">CSR (12)</a></li>
    <li><a href="/compliance/accounts">Accounts (38)</a></li>
  </ul>
</nav>
```

### **5. Smart Compliance Detection**
```python
def auto_detect_compliance_area(section: str, title: str, text: str):
    """
    Use LLM to automatically suggest compliance area
    """
    prompt = f"""
    Based on this legal section, suggest the most appropriate compliance area:
    
    Section: {section}
    Title: {title}
    Text: {text[:500]}
    
    Choose from: {', '.join(COMPLIANCE_AREAS)}
    """
    # Call LLM for suggestion
```

---

## 📝 **Best Practices**

### **1. Consistent Naming**
✅ Use: "Board of Directors"  
❌ Avoid: "BOD", "Board", "Directors"

### **2. Specific but Not Too Granular**
✅ Use: "Corporate Social Responsibility"  
❌ Avoid: "CSR - Section 135 - Spending Requirements"

### **3. User-Friendly Labels**
✅ Use: "Share Capital"  
❌ Avoid: "EQUITY_CAPITAL_MGMT"

### **4. Hierarchical Structure (Future)**
```
Corporate Governance
├─ Board of Directors
├─ Board Meetings
└─ Audit and Auditors

Financial Management
├─ Share Capital
├─ Deposits and Loans
└─ Dividends
```

---

## 🎯 **Summary**

### **What Compliance Areas Do:**

1. **Categorize** documents by subject matter
2. **Enable filtering** in search and retrieval
3. **Improve context** for RAG answers
4. **Organize UI** with badges and navigation
5. **Support analytics** (document counts, trends)

### **Where They're Used:**

- ✅ **Database:** `chunks_content.compliance_area`
- ✅ **Admin UI:** Required field in ingestion form
- ✅ **Retrieval:** Returned with chunk details
- ✅ **Frontend:** Can be displayed as badges/filters
- ✅ **Analytics:** Can group documents for reporting

### **Current Status:**

- ✅ **Stored** in database
- ✅ **Required** during ingestion
- ✅ **Retrieved** with chunks
- ⏳ **Not yet displayed** in query results (future enhancement)
- ⏳ **Not yet filterable** in search (future enhancement)

---

## 🔧 **Quick Reference**

### **Add Compliance Area to New Document:**
```typescript
// Admin form
formData.complianceArea = "Board of Directors"
```

### **Query by Compliance Area:**
```sql
SELECT * FROM chunks_content 
WHERE compliance_area = 'Board of Directors'
```

### **Display in Frontend:**
```tsx
<span className="badge">{chunk.compliance_area}</span>
```

---

**Compliance areas are a powerful organizational tool that makes your RAG system more navigable, filterable, and user-friendly!** 🎯

---

**END OF DOCUMENTATION**
