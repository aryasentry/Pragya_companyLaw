import psycopg2
from db_config import DB_CONFIG
import json

# Check database
print("=== DATABASE CHECK ===")
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("""
    SELECT chunk_id, section, chunk_role, document_type 
    FROM chunks_identity 
    WHERE section = '001' 
    ORDER BY chunk_id
""")

db_results = cur.fetchall()
print(f"\nSection 1 chunks in PostgreSQL: {len(db_results)}")
for r in db_results[:5]:
    print(f"  {r[0]} | Section {r[1]} | {r[2]} | {r[3]}")

# Check FAISS metadata
print("\n=== FAISS INDEX CHECK ===")
with open('vector_store/metadata.json') as f:
    metadata = json.load(f)

section_1_faiss = [m for m in metadata if m.get('section') == '001']
print(f"\nSection 1 chunks in FAISS: {len(section_1_faiss)}")
for m in section_1_faiss[:5]:
    print(f"  {m['chunk_id']}")

# Test search
print("\n=== SEARCH TEST ===")
from retrieval_service_faiss import GovernanceRetriever

retriever = GovernanceRetriever()
results = retriever.search_vectors("what is section 1", top_k=10)

print(f"\nSearch results for 'what is section 1':")
for r in results:
    print(f"  Section {r.get('section')} | Score: {r['similarity_score']:.2%} | {r['chunk_id']}")

conn.close()
