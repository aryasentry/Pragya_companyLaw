"""
Drop all governance tables and enums
Run this to clean the database before re-initialization
"""
import os
from db_config import get_db_connection

def drop_all():
    """Drop all tables and enums"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Drop all tables (CASCADE will handle dependencies)
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")
                cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        
        print("✅ All tables and enums dropped successfully")
        return True
    
    except Exception as e:
        print(f"❌ Drop failed: {e}")
        return False

if __name__ == '__main__':
    print("🗑️  Dropping all governance database objects...")
    if drop_all():
        print("\n✅ Database cleaned. Run python setup.py to reinitialize.")
    else:
        print("\n❌ Failed to clean database.")
