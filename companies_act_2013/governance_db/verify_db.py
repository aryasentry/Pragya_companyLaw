from db_config import get_db_connection

def verify_chunks():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'parent'")
        parent_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'child'")
        child_count = cur.fetchone()['count']
        
        print(f"Parents: {parent_count}")
        print(f"Children: {child_count}\n")
        
        print("Sample Parent IDs:")
        cur.execute("SELECT chunk_id FROM chunks_identity WHERE chunk_role = 'parent' ORDER BY chunk_id LIMIT 10")
        for row in cur.fetchall():
            print(f"  {row['chunk_id']}")
        
        print("\nSample Child IDs:")
        cur.execute("SELECT chunk_id FROM chunks_identity WHERE chunk_role = 'child' ORDER BY chunk_id LIMIT 10")
        for row in cur.fetchall():
            print(f"  {row['chunk_id']}")
        
        print("\nChecking for ID clashes...")
        cur.execute("SELECT chunk_id, COUNT(*) as count FROM chunks_identity GROUP BY chunk_id HAVING COUNT(*) > 1")
        clashes = cur.fetchall()
        if clashes:
            print("CLASHES FOUND:")
            for clash in clashes:
                print(f"  {clash['chunk_id']}: {clash['count']} duplicates")
        else:
            print("No ID clashes - all unique")
        
        print("\nTable Row Counts:")
        tables = ['chunks_identity', 'chunks_content', 'chunk_legal_anchors', 'chunk_keywords',
                  'chunk_relationships', 'chunk_retrieval_rules', 'chunk_refusal_policy',
                  'chunk_temporal', 'chunk_lifecycle', 'chunk_versioning', 'chunk_embeddings',
                  'chunk_lineage', 'chunk_administrative', 'chunk_audit', 'chunk_source']
        
        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            print(f"  {table:25} {count:5} rows")
        
        cur.close()

if __name__ == "__main__":
    verify_chunks()
