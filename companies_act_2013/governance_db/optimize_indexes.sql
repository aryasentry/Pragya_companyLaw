-- Database Performance Optimization for RAG Retrieval
-- Add missing indexes to speed up chunk retrieval queries

-- ============================================
-- ANALYSIS: Current Query Performance Issues
-- ============================================

/*
Current retrieval query joins 6 tables:
1. chunks_identity (ci) - PRIMARY
2. chunks_content (cc) - JOIN
3. chunk_temporal (ct) - LEFT JOIN
4. chunk_administrative (ca) - LEFT JOIN
5. chunk_retrieval_rules (crr) - LEFT JOIN
6. chunk_embeddings (ce) - LEFT JOIN

WHERE clause: ci.chunk_id = ANY(%s)
ORDER BY: crr.priority, ci.section

PROBLEM: Missing indexes on foreign key joins!
*/

-- ============================================
-- RECOMMENDED INDEXES
-- ============================================

-- 1. Index on chunks_content.chunk_id (already PRIMARY KEY - OK)
-- 2. Index on chunk_temporal.chunk_id (already PRIMARY KEY - OK)
-- 3. Index on chunk_administrative.chunk_id (already PRIMARY KEY - OK)
-- 4. Index on chunk_retrieval_rules.chunk_id (already PRIMARY KEY - OK)
-- 5. Index on chunk_embeddings.chunk_id (already PRIMARY KEY - OK)

-- ✅ All foreign key columns are already indexed via PRIMARY KEY!

-- However, we can add composite indexes for ORDER BY optimization:

-- Index for ORDER BY crr.priority, ci.section
CREATE INDEX IF NOT EXISTS idx_section_priority 
ON chunks_identity(section, chunk_id);

-- Index for binding + section queries (common pattern)
CREATE INDEX IF NOT EXISTS idx_binding_section 
ON chunks_identity(binding, section) 
WHERE binding = true;

-- Index for document_type + section (for type-specific queries)
CREATE INDEX IF NOT EXISTS idx_doctype_section 
ON chunks_identity(document_type, section);

-- Index for chunk_role (to quickly filter parent vs child)
CREATE INDEX IF NOT EXISTS idx_chunk_role 
ON chunks_identity(chunk_role);

-- Index for compliance_area (for filtering by topic)
CREATE INDEX IF NOT EXISTS idx_compliance_area 
ON chunks_content(compliance_area);

-- Index for lifecycle status (to exclude RETIRED chunks)
CREATE INDEX IF NOT EXISTS idx_lifecycle_active 
ON chunk_lifecycle(status) 
WHERE status = 'ACTIVE';

-- Composite index for temporal queries (effective date range)
CREATE INDEX IF NOT EXISTS idx_temporal_dates 
ON chunk_temporal(effective_from, effective_to);

-- Index for text search (if using LIKE or full-text search)
-- Note: For better performance, consider using PostgreSQL full-text search
CREATE INDEX IF NOT EXISTS idx_content_text_gin 
ON chunks_content USING gin(to_tsvector('english', text));

-- Index for title search
CREATE INDEX IF NOT EXISTS idx_content_title_gin 
ON chunks_content USING gin(to_tsvector('english', title));

-- ============================================
-- QUERY OPTIMIZATION: Covering Index
-- ============================================

/*
A "covering index" includes all columns needed by a query,
so PostgreSQL doesn't need to access the table at all.

For our main retrieval query, we could create:
*/

-- Covering index for common retrieval patterns
-- (This may be overkill, but useful for read-heavy workloads)
CREATE INDEX IF NOT EXISTS idx_identity_covering 
ON chunks_identity(chunk_id, section, document_type, chunk_role, authority_level, binding, parent_chunk_id);

-- ============================================
-- STATISTICS UPDATE
-- ============================================

-- Update table statistics for better query planning
ANALYZE chunks_identity;
ANALYZE chunks_content;
ANALYZE chunk_temporal;
ANALYZE chunk_administrative;
ANALYZE chunk_retrieval_rules;
ANALYZE chunk_embeddings;
ANALYZE chunk_lifecycle;

-- ============================================
-- VACUUM (Optional - for maintenance)
-- ============================================

-- Remove dead rows and update statistics
-- Run this periodically, not during peak hours
-- VACUUM ANALYZE chunks_identity;
-- VACUUM ANALYZE chunks_content;

-- ============================================
-- QUERY PERFORMANCE TESTING
-- ============================================

/*
Test query performance before and after indexes:

EXPLAIN ANALYZE
SELECT 
    ci.chunk_id,
    ci.parent_chunk_id,
    ci.section,
    ci.document_type,
    ci.chunk_role,
    ci.authority_level,
    ci.binding,
    cc.text,
    cc.title,
    cc.compliance_area,
    cc.citation,
    ct.date_issued,
    ct.effective_from,
    ct.effective_to,
    ca.issued_by,
    ca.notification_number,
    crr.priority,
    ce.model AS embedding_model,
    ce.embedded_at
FROM chunks_identity ci
JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
LEFT JOIN chunk_temporal ct ON ci.chunk_id = ct.chunk_id
LEFT JOIN chunk_administrative ca ON ci.chunk_id = ca.chunk_id
LEFT JOIN chunk_retrieval_rules crr ON ci.chunk_id = crr.chunk_id
LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
WHERE ci.chunk_id = ANY(ARRAY['ca2013_act_s001_p001', 'ca2013_act_s002_p001'])
ORDER BY crr.priority, ci.section;

Expected improvement:
- Before: ~50-100ms for 15 chunks
- After: ~10-20ms for 15 chunks
*/

-- ============================================
-- ADDITIONAL OPTIMIZATIONS
-- ============================================

-- 1. Partial index for active chunks only
CREATE INDEX IF NOT EXISTS idx_active_chunks 
ON chunks_identity(chunk_id) 
WHERE chunk_id IN (
    SELECT chunk_id FROM chunk_lifecycle WHERE status = 'ACTIVE'
);

-- 2. Index for section-based lookups (very common in your system)
CREATE INDEX IF NOT EXISTS idx_section_lookup 
ON chunks_identity(section, chunk_role, chunk_id);

-- 3. Index for parent-child relationships
CREATE INDEX IF NOT EXISTS idx_parent_child_lookup 
ON chunks_identity(parent_chunk_id, chunk_id) 
WHERE parent_chunk_id IS NOT NULL;

-- ============================================
-- MATERIALIZED VIEW (Advanced - Optional)
-- ============================================

/*
For extremely fast reads, create a materialized view that pre-joins all tables.
This is useful if your data doesn't change frequently.

CREATE MATERIALIZED VIEW mv_chunk_details AS
SELECT 
    ci.chunk_id,
    ci.parent_chunk_id,
    ci.section,
    ci.document_type,
    ci.chunk_role,
    ci.authority_level,
    ci.binding,
    cc.text,
    cc.title,
    cc.compliance_area,
    cc.citation,
    ct.date_issued,
    ct.effective_from,
    ct.effective_to,
    ca.issued_by,
    ca.notification_number,
    crr.priority,
    ce.model AS embedding_model,
    ce.embedded_at
FROM chunks_identity ci
JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
LEFT JOIN chunk_temporal ct ON ci.chunk_id = ct.chunk_id
LEFT JOIN chunk_administrative ca ON ci.chunk_id = ca.chunk_id
LEFT JOIN chunk_retrieval_rules crr ON ci.chunk_id = crr.chunk_id
LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id;

-- Create index on materialized view
CREATE INDEX idx_mv_chunk_id ON mv_chunk_details(chunk_id);
CREATE INDEX idx_mv_section ON mv_chunk_details(section);

-- Refresh materialized view after data changes
-- REFRESH MATERIALIZED VIEW mv_chunk_details;

Then query becomes:
SELECT * FROM mv_chunk_details WHERE chunk_id = ANY(%s);

Performance: ~2-5ms (90% faster!)
Tradeoff: Must refresh view after data changes
*/

-- ============================================
-- SUMMARY
-- ============================================

/*
RECOMMENDED ACTIONS (in order of impact):

HIGH IMPACT:
1. ✅ Run this script to add indexes
2. ✅ Run ANALYZE to update statistics
3. ✅ Test query performance with EXPLAIN ANALYZE

MEDIUM IMPACT:
4. Consider materialized view for read-heavy workloads
5. Add full-text search indexes if doing text searches

LOW IMPACT:
6. Periodic VACUUM ANALYZE for maintenance
7. Monitor query performance over time

EXPECTED RESULTS:
- Chunk retrieval: 50-100ms → 10-20ms (5x faster)
- Section lookups: 20-50ms → 5-10ms (4x faster)
- Overall RAG query: 6-9s → 5-7s (15-20% faster)
*/
