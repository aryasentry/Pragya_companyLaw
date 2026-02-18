"""
Test Governance-Grade RAG Improvements
Tests definition query detection and Section 2 prioritization
"""
import sys
sys.path.insert(0, r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')

from retrieval_service_faiss import RetrievalServiceFAISS

print("=" * 70)
print("GOVERNANCE-GRADE RAG TEST")
print("=" * 70)

# Initialize service
service = RetrievalServiceFAISS()

# Test queries
test_queries = [
    "What is the definition of memorandum?",
    "Define company",
    "Meaning of director",
    "What does associate company mean?"
]

for i, query in enumerate(test_queries, 1):
    print(f"\n{i}. Testing: {query}")
    print("-" * 70)
    
    try:
        result = service.query(query, top_k=5)
        
        # Check retrieved sections
        sections = set()
        for chunk in result.get('retrieved_chunks', []):
            section = chunk.get('section', 'N/A')
            sections.add(section)
        
        print(f"✓ Retrieved sections: {', '.join(sorted(sections))}")
        
        # Check if Section 2 is prioritized
        if '002' in sections:
            print(f"✓ Section 2 (definitions) found - CORRECT!")
        else:
            print(f"✗ Section 2 NOT found - may need adjustment")
        
        # Show answer preview
        answer = result.get('answer', '')
        preview = answer[:200] + '...' if len(answer) > 200 else answer
        print(f"\nAnswer preview:\n{preview}")
        
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print("\nExpected: All queries should retrieve Section 002 (definitions)")
print("If not, check that Section 2 chunks are ingested in the database.")
