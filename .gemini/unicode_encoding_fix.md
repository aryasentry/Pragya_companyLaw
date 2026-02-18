# Unicode Encoding Fix for Admin Document Ingestion

## Problem Summary

When ingesting documents through the admin interface, the pipeline was failing with:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4e6' in position 0: character maps to <undefined>
```

This occurred because:
1. **Emoji characters** (📦, ⚠️, 🔨, etc.) were used in `build_faiss_index.py` print statements
2. **Windows console** uses `cp1252` encoding by default, which cannot display emoji characters
3. **Flask subprocess** was capturing output without specifying UTF-8 encoding

## Files Modified

### 1. `companies_act_2013/governance_db/build_faiss_index.py`
**Changes:** Replaced all emoji characters with text equivalents

| Line | Before | After |
|------|--------|-------|
| 51 | `⚠️  Ollama 500 error` | `[WARNING] Ollama 500 error` |
| 59 | `⚠️  Timeout` | `[WARNING] Timeout` |
| 158 | `⚠️ No valid embeddings` | `[WARNING] No valid embeddings` |
| 226 | `📦 Loaded existing index` | `[INFO] Loaded existing index` |
| 227 | `⚠️  This will ADD new chunks` | `[WARNING] This will ADD new chunks` |
| 233 | `📊 Fetching child chunks` | `[INFO] Fetching child chunks` |
| 276 | `⚠️  No chunks to embed` | `[WARNING] No chunks to embed` |
| 295 | `🔨 Building FAISS index` | `[INFO] Building FAISS index` |
| 299 | `💾 Saving vector database` | `[INFO] Saving vector database` |
| 303 | `📝 Updating embedding status` | `[INFO] Updating embedding status` |
| 328-331 | `📊📁🔍` emojis | `[INFO]` prefix |
| 343 | `🔍 Searching` | `[SEARCH] Searching` |

### 2. `companies_act_2013/app_faiss.py`
**Changes:** Added UTF-8 encoding to subprocess calls

**Line 233:** (in `/api/admin/upload` endpoint)
```python
# Before
process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, bufsize=1)

# After
process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
```

**Line 382:** (in `/api/admin/ingest` endpoint)
```python
# Before
process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, bufsize=1)

# After
process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
```

## Technical Details

### Subprocess Encoding Parameters
- **`encoding='utf-8'`**: Forces UTF-8 encoding for stdout/stderr streams
- **`errors='replace'`**: Replaces unencodable characters with `?` instead of raising errors
- This ensures compatibility across different Windows console configurations

### Why This Fixes the Issue
1. **Removed emoji characters** eliminates the root cause of encoding errors
2. **UTF-8 encoding** ensures any future special characters are handled properly
3. **Error replacement** provides graceful degradation if encoding issues occur

## Testing Checklist

After these changes, test the following:
- ✅ Upload PDF document via admin interface
- ✅ Ingest text content via admin interface
- ✅ Verify pipeline status updates display correctly
- ✅ Check that logs are readable in the admin UI
- ✅ Confirm FAISS index builds successfully
- ✅ Verify no Unicode errors in console output

## Admin Flow Overview

```
Frontend (Next.js)
  └─> /api/admin/ingest (Next.js API Route)
       └─> http://localhost:5000/api/admin/ingest (Flask)
            └─> pipeline_full.py (subprocess)
                 └─> build_faiss_index.py
                      └─> FAISS index creation
```

## Related Files (Not Modified)

### Frontend
- `app/src/components/admin/IngestionForm.tsx` - Form UI for document ingestion
- `app/src/components/admin/PipelineStatus.tsx` - Real-time pipeline status display
- `app/src/app/admin/page.tsx` - Admin page container
- `app/src/app/api/admin/ingest/route.ts` - Next.js API proxy

### Backend
- `companies_act_2013/governance_db/pipeline_full.py` - Main pipeline orchestrator
- `companies_act_2013/governance_db/unified_ingest_full.py` - Document ingestion logic
- `companies_act_2013/governance_db/retrieval_service_faiss.py` - FAISS retrieval service

## Notes

- The fix is **backward compatible** - no changes to API contracts or database schema
- **Console output** is now more Windows-friendly with `[INFO]`, `[WARNING]`, `[SEARCH]` prefixes
- **UTF-8 encoding** is now enforced at the subprocess level, preventing future encoding issues
