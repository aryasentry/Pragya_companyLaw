# Two-Phase Retrieval Implementation

## Overview
Implemented a two-phase retrieval system for better user experience:

### Phase 1: Direct Section Lookup (Immediate - <100ms)
- Detects section numbers in query (e.g., "section 2(6)")
- Returns statutory ACT sections immediately
- Provides instant answer to user

### Phase 2: Semantic Search (Background - 2-5s)
- Searches across ALL document types (ACT, FAQ, commentary, etc.)
- Uses vector similarity for comprehensive results
- Returns additional relevant documents

## Implementation Plan

### Backend Changes (Flask API)

1. **Add new endpoint**: `/api/query/direct`
   - Returns immediate section lookup
   - Fast response (<100ms)

2. **Modify existing endpoint**: `/api/query`
   - Add `phase` parameter: 'direct', 'semantic', or 'all'
   - Support two-phase retrieval

3. **Update `retrieval_service_faiss.py`**:
   - Add `phase` parameter to `query()` method
   - Implement phase-based logic

### Frontend Changes (User Page)

1. **Immediate Display**:
   - Show direct section lookup results instantly
   - Display loading indicator for semantic results

2. **Background Fetch**:
   - Fetch semantic results in background
   - Append to existing results when ready

3. **UI Updates**:
   - Section for "Direct Lookup" (immediate)
   - Section for "Related Documents" (semantic, loads after)

## Files to Modify

1. `companies_act_2013/app_faiss.py` - Add `/api/query/direct` endpoint
2. `companies_act_2013/governance_db/retrieval_service_faiss.py` - Add phase support
3. `app/src/app/user/page.tsx` - Implement two-phase UI
4. `app/src/components/SectionResults.tsx` - Support grouped results

## Quick Implementation (Simpler Approach)

Instead of modifying the complex query method, let's:
1. Keep existing `/api/query` as-is
2. Add new `/api/query/section/{section_num}` for direct lookup
3. Frontend calls both endpoints in parallel
4. Display direct results first, semantic results second

This is cleaner and doesn't break existing functionality!
