"""
Check database for FAQ book chunks
"""
import sys
sys.path.append(r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')

from db_config import get_db_connection

print("=" * 70)
print("CHECKING FAQ BOOK CHUNKS IN DATABASE")
print("=" * 70)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # Check if FAQ chunks exist
    cur.execute("""
        SELECT 
            ci.chunk_id,
            ci.section,
            ci.document_type,
            ci.chunk_role,
            cc.title,
            LEFT(cc.text, 200) as text_preview,
            ce.embedded_at
        FROM chunks_identity ci
        JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
        LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
        WHERE ci.document_type = 'qa_book'
        ORDER BY ci.chunk_id
        LIMIT 30
    """)
    
    faq_chunks = cur.fetchall()
    
    print(f"\n✓ Found {len(faq_chunks)} FAQ book chunks\n")
    
    if faq_chunks:
        print("Sample FAQ chunks:")
        print("-" * 70)
        for i, chunk in enumerate(faq_chunks[:5], 1):
            print(f"\n{i}. Chunk ID: {chunk['chunk_id']}")
            print(f"   Section: {chunk['section']}")
            print(f"   Role: {chunk['chunk_role']}")
            print(f"   Title: {chunk['title']}")
            print(f"   Embedded: {chunk['embedded_at']}")
            print(f"   Text: {chunk['text_preview']}...")
    
    # Check section 002 specifically
    print("\n" + "=" * 70)
    print("CHECKING SECTION 002 (or 2) CHUNKS")
    print("=" * 70)
    
    cur.execute("""
        SELECT 
            ci.chunk_id,
            ci.section,
            ci.document_type,
            ci.chunk_role,
            cc.title,
            LEFT(cc.text, 150) as text_preview
        FROM chunks_identity ci
        JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
        WHERE ci.section IN ('002', '2', '02')
        ORDER BY 
            CASE 
                WHEN ci.document_type = 'act' THEN 0
                WHEN ci.document_type = 'qa_book' THEN 1
                ELSE 2
            END,
            ci.chunk_id
    """)
    
    section_chunks = cur.fetchall()
    
    print(f"\n✓ Found {len(section_chunks)} chunks for section 002/2\n")
    
    for chunk in section_chunks:
        print(f"- {chunk['chunk_id']}: {chunk['document_type']} ({chunk['chunk_role']})")
        print(f"  Section: {chunk['section']}")
        print(f"  Title: {chunk['title']}")
        print(f"  Text: {chunk['text_preview']}...")
        print()
    
    # Check what sections FAQ chunks have
    print("=" * 70)
    print("FAQ CHUNK SECTIONS")
    print("=" * 70)
    
    cur.execute("""
        SELECT DISTINCT section, COUNT(*) as count
        FROM chunks_identity
        WHERE document_type = 'qa_book'
        GROUP BY section
        ORDER BY section
    """)
    
    sections = cur.fetchall()
    print(f"\nFAQ chunks are tagged with these sections:")
    for row in sections:
        print(f"  Section {row['section']}: {row['count']} chunks")
    
    cur.close()

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
