"""Quick script to check chunk counts"""
from db_config import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # Count chunks
    cur.execute("SELECT COUNT(*) FROM chunks_identity WHERE chunk_role = 'child'")
    child_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) FROM chunks_identity WHERE chunk_role = 'parent'")
    parent_count = cur.fetchone()['count']
    
    # Count with summaries
    cur.execute("SELECT COUNT(*) FROM chunks_content WHERE summary IS NOT NULL AND summary != ''")
    summary_count = cur.fetchone()['count']
    
    # Count keywords
    cur.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_keywords")
    keyword_count = cur.fetchone()['count']
    
    # Count relationships
    cur.execute("SELECT COUNT(*) FROM chunk_relationships")
    relationship_count = cur.fetchone()['count']
    
    # Sample chunks
    cur.execute("SELECT chunk_id, document_type, section FROM chunks_identity WHERE chunk_role = 'parent' LIMIT 5")
    samples = cur.fetchall()
    
    print("="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    print(f"Parent chunks:        {parent_count}")
    print(f"Child chunks:         {child_count}")
    print(f"Total chunks:         {parent_count + child_count}")
    print(f"With summaries:       {summary_count}")
    print(f"With keywords:        {keyword_count}")
    print(f"Relationships:        {relationship_count}")
    print("\nSample parent chunks:")
    for s in samples:
        print(f"  {s['chunk_id']} | {s['document_type']} | Section {s['section']}")
    print("="*60)
    
    cur.close()
