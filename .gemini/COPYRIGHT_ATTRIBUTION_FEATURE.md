# Copyright Attribution Feature - Implementation Guide

**Date:** February 10, 2026  
**Feature:** Copyright Attribution for Document Ingestion  
**Status:** ✅ Implemented  
**SME Requirement:** Legal Counsel & CFO Feedback

---

## 📋 **Overview**

This feature allows administrators to mark documents with copyright attribution during ingestion, addressing the legal requirement to properly attribute copyrighted materials and distinguish them from public domain content.

---

## 🎯 **Business Requirement**

As per SME (Subject Matter Expert) feedback from Legal Counsel:

> **Copyrighted Documents**: Must display "Courtesy by [Source/Publisher]"  
> **Public Domain Documents**: Must display "General Public" for open-access materials

This ensures legal compliance and proper attribution for all ingested documents.

---

## 🏗️ **Implementation Details**

### **1. Database Schema Changes**

**Table:** `chunk_administrative`

**New Fields:**
```sql
copyright_status TEXT CHECK (copyright_status IN ('copyrighted', 'public_domain', NULL))
copyright_attribution TEXT
```

**Field Descriptions:**
- `copyright_status`: Enum field indicating whether document is copyrighted or public domain
- `copyright_attribution`: Text field storing the attribution string (e.g., "Courtesy by Ministry of Corporate Affairs" or "General Public")

**Migration:**
- Run `migrate_copyright_fields.py` to add fields to existing database
- Fields are nullable to support existing documents without copyright information

---

### **2. TypeScript Types**

**File:** `app/src/types/admin.ts`

**New Type:**
```typescript
export type CopyrightStatus = 'copyrighted' | 'public_domain';
```

**Updated Interface:**
```typescript
export interface IngestionFormData {
  // ... existing fields ...
  
  // Copyright Attribution
  copyrightStatus?: CopyrightStatus;
  copyrightAttribution?: string;
}
```

---

### **3. Admin UI - Ingestion Form**

**File:** `app/src/components/admin/IngestionForm.tsx`

**New Section:** "Section 5: Copyright Attribution"

**Features:**
- Radio button selection for copyright status (Copyrighted / Public Domain)
- Auto-fill attribution text based on selection:
  - **Copyrighted**: Pre-fills "Courtesy by " for user to complete
  - **Public Domain**: Auto-fills "General Public" (read-only)
- Contextual help text and guidelines
- Visual feedback with orange highlighting for selected option

**User Experience:**
1. Admin selects copyright status
2. Attribution field appears with appropriate placeholder/default
3. For copyrighted content, admin completes the attribution (e.g., "Courtesy by MCA")
4. For public domain, field is auto-filled and locked

---

### **4. Backend Processing**

#### **Ingestion Service**

**File:** `companies_act_2013/governance_db/ingestion_service_simple.py`

**Function:** `create_parent_chunk_simple()`

**Changes:**
- Accepts `copyright_status` and `copyright_attribution` via `**kwargs`
- Stores values in `chunk_administrative` table during parent chunk creation

```python
copyright_status = kwargs.get('copyright_status')
copyright_attribution = kwargs.get('copyright_attribution')

cursor.execute("""
    INSERT INTO chunk_administrative (
        chunk_id, copyright_status, copyright_attribution
    ) VALUES (%s, %s, %s)
    ON CONFLICT (chunk_id) DO UPDATE SET
        copyright_status = EXCLUDED.copyright_status,
        copyright_attribution = EXCLUDED.copyright_attribution
""", (chunk_id, copyright_status, copyright_attribution))
```

#### **Chunking Engine**

**File:** `companies_act_2013/governance_db/chunking_engine_simple.py`

**Changes:**
1. **`get_parent_metadata()`**: Retrieves copyright fields from parent chunk
2. **`create_child_chunk()`**: Propagates copyright attribution from parent to child chunks

**Inheritance Logic:**
- Child chunks automatically inherit copyright status and attribution from their parent
- Ensures consistent copyright information across all chunks of a document

---

## 📝 **Usage Guide**

### **For Administrators**

#### **Ingesting a Copyrighted Document:**

1. Navigate to Admin Panel → Ingestion
2. Fill in document details (type, section, content, etc.)
3. In "Copyright Attribution" section:
   - Select **"Copyrighted"**
   - Enter attribution: `Courtesy by [Publisher Name]`
   - Example: `Courtesy by Ministry of Corporate Affairs`
4. Submit document

#### **Ingesting a Public Domain Document:**

1. Navigate to Admin Panel → Ingestion
2. Fill in document details
3. In "Copyright Attribution" section:
   - Select **"Public Domain"**
   - Attribution auto-fills to "General Public"
4. Submit document

#### **Ingesting Without Copyright Info:**

- Leave copyright status unselected
- Fields will be NULL in database
- Can be updated later if needed

---

## 🔄 **Data Flow**

```
Admin Form
    ↓
Frontend (Next.js)
    ↓ (POST /api/admin/ingest)
Backend API (Flask)
    ↓
Ingestion Service (Python)
    ↓
Database (PostgreSQL)
    ├─ Parent Chunk: copyright fields stored
    └─ Child Chunks: copyright fields inherited
```

---

## 🗄️ **Database Migration**

### **For Existing Databases:**

Run the migration script to add copyright fields:

```bash
cd companies_act_2013/governance_db
python migrate_copyright_fields.py
```

**What it does:**
- Adds `copyright_status` column with CHECK constraint
- Adds `copyright_attribution` column
- Both fields are nullable (existing records unaffected)
- Shows updated schema after migration

### **For New Databases:**

- Copyright fields are included in `schema.sql`
- No migration needed - run `init_db.py` as usual

---

## 📊 **Retrieval & Display**

### **Current Status:**
- ✅ Copyright fields stored in database
- ✅ Inherited by child chunks
- ⏳ **Next Step:** Display copyright attribution in query results

### **Planned Enhancement:**

When displaying query results, show copyright attribution:

```python
# In retrieval_service_faiss.py
def get_chunk_details(chunk_ids):
    # ... existing query ...
    # Add to SELECT:
    a.copyright_status,
    a.copyright_attribution
    
    # Add to FROM:
    LEFT JOIN chunk_administrative a ON ci.chunk_id = a.chunk_id
```

**Frontend Display:**
```tsx
{chunk.copyright_attribution && (
  <div className="text-xs text-gray-500 italic mt-2">
    {chunk.copyright_attribution}
  </div>
)}
```

---

## ✅ **Testing Checklist**

### **Database:**
- [ ] Run migration on existing database
- [ ] Verify columns added successfully
- [ ] Test INSERT with copyright fields
- [ ] Test UPDATE of copyright fields
- [ ] Verify child chunks inherit copyright from parent

### **Admin UI:**
- [ ] Copyright section appears in ingestion form
- [ ] Radio buttons work correctly
- [ ] "Copyrighted" selection shows editable text field
- [ ] "Public Domain" selection auto-fills and locks field
- [ ] Form validation works
- [ ] Submit sends copyright data to backend

### **Backend:**
- [ ] API receives copyright fields
- [ ] Ingestion service stores copyright in database
- [ ] Child chunks inherit copyright from parent
- [ ] Existing documents without copyright still work

### **End-to-End:**
- [ ] Ingest copyrighted document with attribution
- [ ] Ingest public domain document
- [ ] Verify data in database
- [ ] Verify child chunks have same copyright as parent

---

## 📚 **Examples**

### **Example 1: Copyrighted MCA Notification**

**Input:**
- Document Type: Notification
- Copyright Status: Copyrighted
- Copyright Attribution: "Courtesy by Ministry of Corporate Affairs"

**Database:**
```sql
SELECT chunk_id, copyright_status, copyright_attribution 
FROM chunk_administrative 
WHERE chunk_id = 'ca2013_notification_s001';

-- Result:
-- chunk_id: ca2013_notification_s001
-- copyright_status: copyrighted
-- copyright_attribution: Courtesy by Ministry of Corporate Affairs
```

### **Example 2: Public Domain Act**

**Input:**
- Document Type: Act
- Copyright Status: Public Domain
- Copyright Attribution: "General Public"

**Database:**
```sql
SELECT chunk_id, copyright_status, copyright_attribution 
FROM chunk_administrative 
WHERE chunk_id = 'ca2013_act_s001';

-- Result:
-- chunk_id: ca2013_act_s001
-- copyright_status: public_domain
-- copyright_attribution: General Public
```

### **Example 3: Legacy Document (No Copyright Info)**

**Input:**
- Document Type: Rule
- Copyright Status: (not selected)

**Database:**
```sql
SELECT chunk_id, copyright_status, copyright_attribution 
FROM chunk_administrative 
WHERE chunk_id = 'ca2013_rule_s001';

-- Result:
-- chunk_id: ca2013_rule_s001
-- copyright_status: NULL
-- copyright_attribution: NULL
```

---

## 🚀 **Future Enhancements**

### **Phase 1: Display (Immediate)**
- [ ] Show copyright attribution in query results
- [ ] Add copyright filter in search
- [ ] Display copyright in document viewer

### **Phase 2: Bulk Operations**
- [ ] Bulk update copyright for existing documents
- [ ] Import copyright info from CSV
- [ ] Copyright status dashboard

### **Phase 3: Advanced Features**
- [ ] Copyright expiry tracking
- [ ] License type field (CC BY, CC BY-SA, etc.)
- [ ] Copyright holder contact information
- [ ] Automatic copyright detection from document metadata

---

## 📞 **Support & Questions**

**For Issues:**
- Check database migration ran successfully
- Verify schema has copyright columns
- Check browser console for frontend errors
- Review Flask logs for backend errors

**Common Issues:**

**Issue:** Copyright fields not appearing in form  
**Solution:** Clear browser cache, rebuild Next.js app

**Issue:** Migration fails  
**Solution:** Check database connection, verify user has ALTER TABLE permissions

**Issue:** Child chunks don't have copyright  
**Solution:** Verify `get_parent_metadata()` includes copyright fields in SELECT

---

## 📄 **Files Modified**

### **Database:**
- `schema.sql` - Added copyright columns
- `migrate_copyright_fields.py` - Migration script (new)

### **Backend:**
- `ingestion_service_simple.py` - Store copyright in parent chunks
- `chunking_engine_simple.py` - Inherit copyright in child chunks

### **Frontend:**
- `app/src/types/admin.ts` - Added CopyrightStatus type
- `app/src/components/admin/IngestionForm.tsx` - Added copyright UI section
- `app/src/app/admin/page.tsx` - Pass copyright to backend

---

## ✅ **Completion Status**

**Implemented:**
- ✅ Database schema updated
- ✅ Migration script created
- ✅ TypeScript types defined
- ✅ Admin UI form section added
- ✅ Backend ingestion updated
- ✅ Child chunk inheritance implemented
- ✅ Documentation completed

**Pending:**
- ⏳ Display copyright in query results
- ⏳ Copyright filter in search
- ⏳ Bulk update tool

---

**Feature Status:** ✅ **Ready for Testing**  
**Next Steps:** Run migration, test ingestion, implement display in query results

---

**END OF DOCUMENTATION**
