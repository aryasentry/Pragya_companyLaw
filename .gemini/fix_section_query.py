"""
Quick fix script to enable FAQ books in section-based queries
"""

# Read the file
with open(r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db\retrieval_service_faiss.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the restrictive WHERE clause
old_clause = "WHERE ci.section = %s AND ci.document_type = 'act'"
new_clause = "WHERE ci.section = %s"

if old_clause in content:
    content = content.replace(old_clause, new_clause)
    
    # Write back
    with open(r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db\retrieval_service_faiss.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fixed! Section-based queries will now include FAQ books and all document types.")
    print("  Changed: WHERE ci.section = %s AND ci.document_type = 'act'")
    print("  To: WHERE ci.section = %s")
else:
    print("✗ Pattern not found. File may have already been modified.")
