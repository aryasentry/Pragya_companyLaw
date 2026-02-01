"""Show actual database schema"""
from db_config import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    tables = ['chunks_identity', 'chunks_content', 'chunk_retrieval_rules', 
              'chunk_refusal_policy', 'chunk_lifecycle', 'chunk_versioning', 
              'chunk_embeddings', 'chunk_governance', 'chunk_relationships']
    
    for table in tables:
        print(f"\n{'='*60}")
        print(f"TABLE: {table}")
        print('='*60)
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)
        for row in cur.fetchall():
            print(f"  {row['column_name']:30} {row['data_type']:20} {row['is_nullable']}")
    
    cur.close()
