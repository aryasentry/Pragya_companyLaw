"""Check database tables"""
from db_config import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"  - {table['table_name']}")
