"""
Migration: Add Copyright Attribution Fields
Adds copyright_status and copyright_attribution to chunk_administrative table
"""
from db_config import get_db_connection

def migrate_add_copyright_fields():
    """Add copyright attribution fields to chunk_administrative table"""
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            print("Adding copyright fields to chunk_administrative table...")
            
            # Add copyright_status column
            cursor.execute("""
                ALTER TABLE chunk_administrative 
                ADD COLUMN IF NOT EXISTS copyright_status TEXT 
                CHECK (copyright_status IN ('copyrighted', 'public_domain', NULL))
            """)
            
            # Add copyright_attribution column
            cursor.execute("""
                ALTER TABLE chunk_administrative 
                ADD COLUMN IF NOT EXISTS copyright_attribution TEXT
            """)
            
            conn.commit()
            print("✅ Copyright fields added successfully!")
            
            # Show sample of updated schema
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'chunk_administrative'
                ORDER BY ordinal_position
            """)
            
            print("\nUpdated chunk_administrative schema:")
            for row in cursor.fetchall():
                print(f"  - {row['column_name']}: {row['data_type']}")

if __name__ == '__main__':
    print("🔄 Running Copyright Attribution Migration...")
    print("=" * 60)
    migrate_add_copyright_fields()
    print("=" * 60)
    print("✅ Migration completed successfully!")
