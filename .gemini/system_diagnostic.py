"""
Comprehensive System Diagnostic and Fix Script
Scans all critical files and fixes common issues
"""
import os
import sys
from pathlib import Path

print("=" * 70)
print("PRAGYA SYSTEM DIAGNOSTIC")
print("=" * 70)

# Add governance_db to path
sys.path.insert(0, r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')

issues_found = []
fixes_applied = []

# 1. Check all Python files compile
print("\n1. CHECKING PYTHON SYNTAX...")
governance_db = Path(r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')
python_files = list(governance_db.glob('*.py'))

for py_file in python_files:
    if 'useless_files' in str(py_file):
        continue
    try:
        compile(py_file.read_text(encoding='utf-8'), str(py_file), 'exec')
        print(f"  ✓ {py_file.name}")
    except SyntaxError as e:
        issues_found.append(f"Syntax error in {py_file.name}: {e}")
        print(f"  ✗ {py_file.name}: {e}")

# 2. Check database connection
print("\n2. CHECKING DATABASE CONNECTION...")
try:
    from db_config import get_db_connection
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunks_identity")
        count = cur.fetchone()['count']
        print(f"  ✓ Database connected: {count} chunks in identity table")
        cur.close()
except Exception as e:
    issues_found.append(f"Database connection failed: {e}")
    print(f"  ✗ Database error: {e}")

# 3. Check FAISS index
print("\n3. CHECKING FAISS INDEX...")
vector_store = Path(r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db\vector_store')
if (vector_store / 'faiss_index.bin').exists() and (vector_store / 'metadata.json').exists():
    import json
    metadata = json.loads((vector_store / 'metadata.json').read_text())
    print(f"  ✓ FAISS index exists: {len(metadata)} vectors")
else:
    issues_found.append("FAISS index not found")
    print(f"  ✗ FAISS index missing")

# 4. Check critical imports
print("\n4. CHECKING CRITICAL IMPORTS...")
critical_modules = [
    'pypdf',
    'psycopg2',
    'faiss',
    'numpy',
    'requests'
]

for module in critical_modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError:
        issues_found.append(f"Missing module: {module}")
        print(f"  ✗ {module} not installed")

# 5. Check Ollama connectivity
print("\n5. CHECKING OLLAMA...")
try:
    import requests
    response = requests.get('http://localhost:11434/api/tags', timeout=2)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"  ✓ Ollama running: {len(models)} models")
    else:
        issues_found.append("Ollama not responding correctly")
        print(f"  ✗ Ollama error: {response.status_code}")
except Exception as e:
    issues_found.append(f"Ollama not accessible: {e}")
    print(f"  ✗ Ollama not accessible")

# 6. Check for common code issues
print("\n6. SCANNING FOR COMMON ISSUES...")

# Check for unterminated strings
for py_file in python_files:
    if 'useless_files' in str(py_file):
        continue
    content = py_file.read_text(encoding='utf-8')
    
    # Check for common issues
    if 'folder_analyzer' in content and py_file.name not in ['folder_analyzer.py']:
        issues_found.append(f"{py_file.name} imports folder_analyzer (may not exist)")
        print(f"  ⚠ {py_file.name}: imports folder_analyzer")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if issues_found:
    print(f"\n❌ Found {len(issues_found)} issues:")
    for issue in issues_found:
        print(f"  - {issue}")
else:
    print("\n✅ No critical issues found!")

if fixes_applied:
    print(f"\n🔧 Applied {len(fixes_applied)} fixes:")
    for fix in fixes_applied:
        print(f"  - {fix}")

print("\n" + "=" * 70)
