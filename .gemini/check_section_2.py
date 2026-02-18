"""
Check if Section 2 (definitions) is in the database
"""
import sys
sys.path.insert(0, r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')

from db_config import get_db_connection

print("=" * 70)
print("CHECKING SECTION 2 IN DATABASE")
print("=" * 70)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # Check all sections in database
    cur.execute("""
        SELECT DISTINCT section, document_type, COUNT(*) as chunk_count
        FROM chunks_identity
        WHERE document_type = 'act'
        GROUP BY section, document_type
        ORDER BY section
    """)
    
    sections = cur.fetchall()
    
    print(f"\nTotal ACT sections in database: {len(sections)}")
    print("\nFirst 10 sections:")
    for i, row in enumerate(sections[:10], 1):
        print(f"  {i}. Section {row['section']}: {row['chunk_count']} chunks")
    
    # Specifically check Section 2
    cur.execute("""
        SELECT chunk_id, chunk_role
        FROM chunks_identity
        WHERE section = '002' AND document_type = 'act'
    """)
    
    section_2_chunks = cur.fetchall()
    
    print(f"\n{'='*70}")
    if section_2_chunks:
        print(f"✓ Section 2 EXISTS: {len(section_2_chunks)} chunks")
        for chunk in section_2_chunks[:5]:
            print(f"  - {chunk['chunk_id']} ({chunk['chunk_role']})")
    else:
        print("✗ Section 2 NOT FOUND in database!")
        print("\n🚨 CRITICAL: Section 2 (definitions) must be ingested!")
        print("\nTo fix:")
        print("1. Find section_002_act.txt file")
        print("2. Upload via admin UI with:")
        print("   - Type: act")
        print("   - Section: 002")
        print("   - Category: companies_act")
    
    # Check what sections ARE available
    print(f"\n{'='*70}")
    print("Available sections:")
    for row in sections:
        if row['section']:
            print(f"  Section {row['section']}: {row['chunk_count']} chunks")
    
    cur.close()

print("\n" + "=" * 70)
