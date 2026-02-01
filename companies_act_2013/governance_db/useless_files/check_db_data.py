"""Check actual data and values in database"""
from db_config import get_db_connection

def check_database_data():
    """Check actual data values in database"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print("="*70)
        print("ACTUAL DATABASE DATA INSPECTION")
        print("="*70)
        
        # 1. Sample Parent Chunk - Full Details
        print("\n📋 SAMPLE PARENT CHUNK (ca2013_act_s001_html):")
        print("-"*70)
        cur.execute("""
            SELECT ci.chunk_id, ci.chunk_role, ci.parent_chunk_id, ci.document_type,
                   ci.authority_level, ci.binding,
                   cc.text, cc.citation, cc.summary, cc.title, cc.compliance_area,
                   ctr.priority, ctr.requires_parent_law,
                   crp.can_answer_standalone, crp.must_reference_parent_law,
                   cl.status,
                   cv.version,
                   ce.enabled as embedding_enabled, ce.model as embedding_model
            FROM chunks_identity ci
            LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            LEFT JOIN chunk_retrieval_rules ctr ON ci.chunk_id = ctr.chunk_id
            LEFT JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
            LEFT JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
            LEFT JOIN chunk_versioning cv ON ci.chunk_id = cv.chunk_id
            LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
            WHERE ci.chunk_id = 'ca2013_act_s001_html'
            LIMIT 1
        """)
        
        parent = cur.fetchone()
        if parent:
            print(f"Chunk ID: {parent['chunk_id']}")
            print(f"Role: {parent['chunk_role']}")
            print(f"Document Type: {parent['document_type']}")
            print(f"Authority Level: {parent['authority_level']}")
            print(f"Binding: {parent['binding']}")
            print(f"Priority: {parent['priority']}")
            print(f"Requires Parent Law: {parent['requires_parent_law']}")
            print(f"Status: {parent['status']}")
            print(f"Version: {parent['version']}")
            print(f"Embedding Enabled: {parent['embedding_enabled']}")
            print(f"Model: {parent['embedding_model']}")
            print(f"Title: {parent['title']}")
            print(f"Compliance Area: {parent['compliance_area']}")
            print(f"Citation: {parent['citation'][:100]}..." if parent['citation'] else "None")
            print(f"Text Preview: {parent['text'][:200]}..." if parent['text'] else "None")
        
        # 2. Sample Child Chunk - Full Details
        print("\n📋 SAMPLE CHILD CHUNK (ca2013_act_s001_html_c1):")
        print("-"*70)
        cur.execute("""
            SELECT ci.chunk_id, ci.chunk_role, ci.parent_chunk_id, ci.document_type,
                   ci.binding,
                   cc.text, cc.citation,
                   ctr.priority,
                   crp.can_answer_standalone,
                   ce.enabled as embedding_enabled
            FROM chunks_identity ci
            LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            LEFT JOIN chunk_retrieval_rules ctr ON ci.chunk_id = ctr.chunk_id
            LEFT JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
            LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
            WHERE ci.chunk_id = 'ca2013_act_s001_html_c1'
            LIMIT 1
        """)
        
        child = cur.fetchone()
        if child:
            print(f"Chunk ID: {child['chunk_id']}")
            print(f"Role: {child['chunk_role']}")
            print(f"Parent: {child['parent_chunk_id']}")
            print(f"Priority: {child['priority']}")
            print(f"Binding: {child['binding']}")
            print(f"Can Answer Standalone: {child['can_answer_standalone']}")
            print(f"Embedding Enabled: {child['embedding_enabled']}")
            print(f"Text Length: {len(child['text']) if child['text'] else 0} chars")
            print(f"Text Preview: {child['text'][:300]}..." if child['text'] else "None")
        
        # 3. Relationships
        print("\n🔗 CHUNK RELATIONSHIPS (First 10):")
        print("-"*70)
        cur.execute("""
            SELECT from_chunk_id, to_chunk_id, relationship
            FROM chunk_relationships
            ORDER BY from_chunk_id
            LIMIT 10
        """)
        
        for rel in cur.fetchall():
            print(f"{rel['from_chunk_id']} --[{rel['relationship']}]--> {rel['to_chunk_id']}")
        
        # 4. Document Type Distribution
        print("\n📊 DOCUMENT TYPE DISTRIBUTION:")
        print("-"*70)
        cur.execute("""
            SELECT document_type, COUNT(*) as count
            FROM chunks_identity
            WHERE chunk_role = 'parent'
            GROUP BY document_type
            ORDER BY count DESC
        """)
        
        for row in cur.fetchall():
            print(f"  {row['document_type']:15} {row['count']:4} documents")
        
        # 5. Binding vs Non-Binding
        print("\n⚖️  BINDING STATUS:")
        print("-"*70)
        cur.execute("""
            SELECT ci.binding, COUNT(*) as count
            FROM chunks_identity ci
            WHERE ci.chunk_role = 'parent'
            GROUP BY ci.binding
        """)
        
        for row in cur.fetchall():
            status = "Binding" if row['binding'] else "Non-Binding"
            print(f"  {status:15} {row['count']:4} documents")
        
        # 6. Priority Distribution
        print("\n🎯 PRIORITY DISTRIBUTION:")
        print("-"*70)
        cur.execute("""
            SELECT priority, COUNT(*) as count
            FROM chunk_retrieval_rules ctr
            WHERE ctr.chunk_id IN (SELECT chunk_id FROM chunks_identity WHERE chunk_role = 'parent')
            GROUP BY priority
            ORDER BY priority
        """)
        
        for row in cur.fetchall():
            print(f"  Priority {row['priority']:10} {row['count']:4} documents")
        
        # 7. Embedding Status
        print("\n🧮 EMBEDDING STATUS:")
        print("-"*70)
        cur.execute("""
            SELECT 
                SUM(CASE WHEN chunk_role = 'parent' THEN 1 ELSE 0 END) as parents,
                SUM(CASE WHEN chunk_role = 'child' THEN 1 ELSE 0 END) as children
            FROM chunks_identity ci
            JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
            WHERE ce.enabled = true
        """)
        
        emb = cur.fetchone()
        print(f"  Parents enabled:  {emb['parents']:4}")
        print(f"  Children enabled: {emb['children']:4}")
        
        # 8. Sample Text Lengths
        print("\n📏 TEXT LENGTH STATISTICS:")
        print("-"*70)
        cur.execute("""
            SELECT 
                ci.chunk_role,
                AVG(LENGTH(cc.text)) as avg_length,
                MIN(LENGTH(cc.text)) as min_length,
                MAX(LENGTH(cc.text)) as max_length
            FROM chunks_identity ci
            JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE cc.text IS NOT NULL
            GROUP BY ci.chunk_role
        """)
        
        for row in cur.fetchall():
            print(f"  {row['chunk_role']:7} Avg: {int(row['avg_length']):5} chars  "
                  f"Min: {int(row['min_length']):5}  Max: {int(row['max_length']):6}")
        
        # 9. Recent Chunks with Full Metadata
        print("\n📌 RECENT 5 PARENT CHUNKS (Full Metadata):")
        print("-"*70)
        cur.execute("""
            SELECT ci.chunk_id, ci.document_type, ci.authority_level,
                   ci.binding, ctr.priority,
                   cl.status, cv.version,
                   LENGTH(cc.text) as text_length
            FROM chunks_identity ci
            LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            LEFT JOIN chunk_retrieval_rules ctr ON ci.chunk_id = ctr.chunk_id
            LEFT JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
            LEFT JOIN chunk_versioning cv ON ci.chunk_id = cv.chunk_id
            WHERE ci.chunk_role = 'parent'
            ORDER BY ci.chunk_id DESC
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            binding = "✓ Binding" if row['binding'] else "✗ Non-Binding"
            print(f"{row['chunk_id']:35} | {row['document_type']:12} | {binding:14} | "
                  f"{row['priority']:10} | {row['authority_level']:12} | "
                  f"v{row['version']} | {row['text_length']:5} chars")
        
        cur.close()

if __name__ == "__main__":
    check_database_data()
