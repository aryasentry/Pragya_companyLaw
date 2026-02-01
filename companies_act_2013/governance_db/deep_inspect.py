"""Deep inspection of database values and content"""
from db_config import get_db_connection

def deep_inspect():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print("="*80)
        print("DEEP DATABASE CONTENT INSPECTION")
        print("="*80)
        
        # 1. Show actual text from a binding parent chunk
        print("\n📄 ACTUAL BINDING PARENT TEXT (ca2013_act_s001_html):")
        print("-"*80)
        cur.execute("""
            SELECT cc.text, cc.citation, cc.title, cc.compliance_area
            FROM chunks_content cc
            WHERE cc.chunk_id = 'ca2013_act_s001_html'
        """)
        parent = cur.fetchone()
        if parent:
            print(f"Title: {parent['title']}")
            print(f"Compliance Area: {parent['compliance_area']}")
            print(f"Citation: {parent['citation']}")
            print(f"\nFull Text (first 800 chars):")
            print(parent['text'][:800] if parent['text'] else "None")
        
        # 2. Show actual child chunk text
        print("\n\n📄 ACTUAL CHILD CHUNK TEXT (ca2013_act_s001_html_c1):")
        print("-"*80)
        cur.execute("""
            SELECT cc.text, ci.parent_chunk_id
            FROM chunks_content cc
            JOIN chunks_identity ci ON cc.chunk_id = ci.chunk_id
            WHERE cc.chunk_id = 'ca2013_act_s001_html_c1'
        """)
        child = cur.fetchone()
        if child:
            print(f"Parent: {child['parent_chunk_id']}")
            print(f"\nFull Text:")
            print(child['text'])
        
        # 3. Check governance rules for binding chunks
        print("\n\n🔒 GOVERNANCE RULES - BINDING CHUNKS:")
        print("-"*80)
        cur.execute("""
            SELECT ci.chunk_id, ci.document_type, ci.authority_level, ci.binding,
                   ctr.priority, ctr.requires_parent_law,
                   crp.can_answer_standalone, crp.must_reference_parent_law,
                   crp.refuse_if_parent_missing
            FROM chunks_identity ci
            JOIN chunk_retrieval_rules ctr ON ci.chunk_id = ctr.chunk_id
            JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
            WHERE ci.binding = true AND ci.chunk_role = 'parent'
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            print(f"\nChunk: {row['chunk_id']}")
            print(f"  Type: {row['document_type']} | Authority: {row['authority_level']}")
            print(f"  Priority: {row['priority']} | Requires Parent Law: {row['requires_parent_law']}")
            print(f"  Can Answer Standalone: {row['can_answer_standalone']}")
            print(f"  Must Reference Parent Law: {row['must_reference_parent_law']}")
            print(f"  Refuse if Parent Missing: {row['refuse_if_parent_missing']}")
        
        # 4. Check governance rules for non-binding chunks
        print("\n\n📖 GOVERNANCE RULES - NON-BINDING CHUNKS:")
        print("-"*80)
        cur.execute("""
            SELECT ci.chunk_id, ci.document_type, ci.authority_level, ci.binding,
                   ctr.priority, ctr.requires_parent_law,
                   crp.can_answer_standalone, crp.must_reference_parent_law,
                   crp.refuse_if_parent_missing
            FROM chunks_identity ci
            JOIN chunk_retrieval_rules ctr ON ci.chunk_id = ctr.chunk_id
            JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
            WHERE ci.binding = false AND ci.chunk_role = 'parent'
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            print(f"\nChunk: {row['chunk_id']}")
            print(f"  Type: {row['document_type']} | Authority: {row['authority_level']}")
            print(f"  Priority: {row['priority']} | Requires Parent Law: {row['requires_parent_law']}")
            print(f"  Can Answer Standalone: {row['can_answer_standalone']}")
            print(f"  Must Reference Parent Law: {row['must_reference_parent_law']}")
            print(f"  Refuse if Parent Missing: {row['refuse_if_parent_missing']}")
        
        # 5. Show temporal data if any exists
        print("\n\n📅 TEMPORAL VALIDITY DATA:")
        print("-"*80)
        cur.execute("""
            SELECT ct.chunk_id, ct.date_issued, ct.effective_from, ct.effective_to,
                   ci.document_type
            FROM chunk_temporal ct
            JOIN chunks_identity ci ON ct.chunk_id = ci.chunk_id
            LIMIT 5
        """)
        
        count = 0
        for row in cur.fetchall():
            count += 1
            print(f"{row['chunk_id']:35} | {row['document_type']:12} | "
                  f"Issued: {row['date_issued']} | Effective: {row['effective_from']} to {row['effective_to']}")
        
        if count == 0:
            print("No temporal data stored yet")
        
        # 6. Show legal anchors
        print("\n\n⚓ LEGAL ANCHORS:")
        print("-"*80)
        cur.execute("""
            SELECT chunk_id, act, section, sub_section
            FROM chunks_identity
            WHERE act IS NOT NULL
            LIMIT 10
        """)
        
        count = 0
        for row in cur.fetchall():
            count += 1
            print(f"{row['chunk_id']:35} | Act: {row['act']} | "
                  f"Section: {row['section']} | Sub: {row['sub_section']}")
        
        if count == 0:
            print("No legal anchor data found")
        
        # 7. Show embedding configuration
        print("\n\n🧮 EMBEDDING CONFIGURATION:")
        print("-"*80)
        cur.execute("""
            SELECT ce.chunk_id, ce.enabled, ce.model, ce.vector_id,
                   ci.chunk_role, ci.document_type
            FROM chunk_embeddings ce
            JOIN chunks_identity ci ON ce.chunk_id = ci.chunk_id
            WHERE ce.enabled = true
            LIMIT 10
        """)
        
        for row in cur.fetchall():
            print(f"{row['chunk_id']:35} | {row['chunk_role']:6} | "
                  f"Enabled: {row['enabled']} | Model: {row['model']} | Vector: {row['vector_id']}")
        
        # 8. Show relationship graph sample
        print("\n\n🔗 RELATIONSHIP GRAPH SAMPLE (Parent-Child & Sequential):")
        print("-"*80)
        cur.execute("""
            SELECT cr.from_chunk_id, cr.relationship, cr.to_chunk_id
            FROM chunk_relationships cr
            WHERE cr.from_chunk_id LIKE 'ca2013_act_s001_html%'
            ORDER BY cr.from_chunk_id, cr.relationship
            LIMIT 15
        """)
        
        for row in cur.fetchall():
            print(f"{row['from_chunk_id']:30} --[{row['relationship']:8}]--> {row['to_chunk_id']}")
        
        # 9. Lifecycle status distribution
        print("\n\n🔄 LIFECYCLE STATUS DISTRIBUTION:")
        print("-"*80)
        cur.execute("""
            SELECT cl.status, COUNT(*) as count
            FROM chunk_lifecycle cl
            GROUP BY cl.status
            ORDER BY count DESC
        """)
        
        for row in cur.fetchall():
            print(f"  {row['status']:15} {row['count']:5} chunks")
        
        # 10. Version information
        print("\n\n📦 VERSION INFORMATION:")
        print("-"*80)
        cur.execute("""
            SELECT cv.version, COUNT(*) as count
            FROM chunk_versioning cv
            GROUP BY cv.version
            ORDER BY cv.version
        """)
        
        for row in cur.fetchall():
            print(f"  Version {row['version']:10} {row['count']:5} chunks")
        
        cur.close()

if __name__ == "__main__":
    deep_inspect()
