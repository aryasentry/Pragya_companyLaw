"""
Check FAISS metadata for FAQ chunks
"""
import json
from pathlib import Path

metadata_file = Path(r"c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db\vector_store\metadata.json")

if metadata_file.exists():
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print("=" * 70)
    print(f"FAISS INDEX: {len(metadata)} total vectors")
    print("=" * 70)
    
    # Count by document type
    doc_types = {}
    for item in metadata:
        dt = item.get('document_type', 'unknown')
        doc_types[dt] = doc_types.get(dt, 0) + 1
    
    print("\nDocument types in FAISS index:")
    for dt, count in sorted(doc_types.items()):
        print(f"  {dt}: {count} chunks")
    
    # Find FAQ chunks
    faq_chunks = [m for m in metadata if m.get('document_type') == 'qa_book']
    
    print(f"\n✓ Found {len(faq_chunks)} FAQ book chunks in FAISS index")
    
    if faq_chunks:
        print("\nSample FAQ chunks:")
        for i, chunk in enumerate(faq_chunks[:5], 1):
            print(f"\n{i}. {chunk['chunk_id']}")
            print(f"   Section: {chunk.get('section', 'None')}")
            print(f"   Text preview: {chunk.get('text', '')[:150]}...")
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS:")
    print("=" * 70)
    if faq_chunks:
        if faq_chunks[0].get('section') is None or faq_chunks[0].get('section') == '':
            print("❌ PROBLEM: FAQ chunks have NO section number!")
            print("   This is why section-based queries don't find them.")
            print("\n✅ SOLUTION: Use vector search (semantic) instead of section lookup")
        else:
            print("✓ FAQ chunks have section numbers")
    else:
        print("❌ NO FAQ chunks found in FAISS index!")
        print("   They may not have been embedded yet.")
else:
    print(f"❌ Metadata file not found: {metadata_file}")
