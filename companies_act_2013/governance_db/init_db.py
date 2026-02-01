"""
Database initialization script
Run this to create all tables in PostgreSQL
"""
import os
from db_config import get_db_connection

def init_database():
    """Initialize database from schema.sql"""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
        
        print("✅ Database initialized successfully")
        print("📊 Created 15 tables:")
        print("   - chunks_identity (immutable)")
        print("   - chunks_content (editable)")
        print("   - chunk_legal_anchors")
        print("   - chunk_keywords")
        print("   - chunk_relationships")
        print("   - chunk_retrieval_rules")
        print("   - chunk_refusal_policy")
        print("   - chunk_temporal")
        print("   - chunk_lifecycle")
        print("   - chunk_versioning")
        print("   - chunk_embeddings")
        print("   - chunk_lineage")
        print("   - chunk_administrative")
        print("   - chunk_audit")
        print("   - chunk_source")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == '__main__':
    print("Initializing governance database...")
    init_database()
