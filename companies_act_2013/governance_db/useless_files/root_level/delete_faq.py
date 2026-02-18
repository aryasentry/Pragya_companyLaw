import sys
sys.path.insert(0, 'governance_db')
from db_config import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # Check what will be deleted
        print("=== Chunks to be deleted ===")
        cur.execute("""
            SELECT i.chunk_id, i.chunk_role, i.document_type
            FROM chunks_identity i
            WHERE i.chunk_id LIKE '%qa_book%'
            ORDER BY i.chunk_id
        """)
        
        chunks = cur.fetchall()
        print(f"Found {len(chunks)} chunks to delete")
        for chunk in chunks[:5]:
            print(f"  {chunk['chunk_id']}")
        if len(chunks) > 5:
            print(f"  ... and {len(chunks) - 5} more")
        
        if len(chunks) == 0:
            print("No FAQ chunks found.")
            exit(0)
        
        # Confirm
        print(f"\n⚠️  About to delete {len(chunks)} chunks")
        confirm = input("Type 'DELETE' to confirm: ")
        
        if confirm != 'DELETE':
            print("❌ Cancelled")
            exit(0)
        
        # Delete
        print("\n🗑️  Deleting...")
        cur.execute("DELETE FROM chunks_identity WHERE chunk_id LIKE '%qa_book%'")
        cur.execute("DELETE FROM chunk_relationships WHERE from_chunk_id LIKE '%qa_book%' OR to_chunk_id LIKE '%qa_book%'")
        cur.execute("DELETE FROM chunk_keywords WHERE chunk_id LIKE '%qa_book%'")
        
        conn.commit()
        print(f"✅ Deleted {len(chunks)} chunks")
