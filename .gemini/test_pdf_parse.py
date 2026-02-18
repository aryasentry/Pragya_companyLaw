"""
Quick diagnostic script to test PDF parsing
"""
import sys
from pathlib import Path

sys.path.insert(0, r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')

from pdf_parser import parse_document

# Test the actual file
test_file = r"C:\Users\kalid\OneDrive\Documents\RAG2\Pragya_companyLaw\companies_act_2013\data\non_binding\qa_book\splitFAQ.pdf"

print(f"Testing: {test_file}")
print(f"File exists: {Path(test_file).exists()}")

if Path(test_file).exists():
    result = parse_document(test_file)
    print(f"\nResult type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    
    if isinstance(result, dict):
        text = result.get('text')
        print(f"\nText is None: {text is None}")
        print(f"Text length: {len(text) if text else 0}")
        
        if text:
            print(f"\nFirst 500 chars:")
            print(text[:500])
        else:
            print("\n❌ NO TEXT EXTRACTED!")
    else:
        print(f"\n❌ Result is not a dict: {result}")
else:
    print("\n❌ FILE NOT FOUND!")
