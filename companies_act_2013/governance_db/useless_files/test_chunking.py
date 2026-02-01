"""
Test script for chunking and database storage
Tests parent-child chunking workflow WITHOUT embedding
Validates schema compliance with chunk_format.txt
"""
import os
import sys
from datetime import datetime, date
from pprint import pprint

# Add governance_db to path
sys.path.insert(0, os.path.dirname(__file__))

from ingestion_service import create_parent_chunk, update_chunk_text, get_chunk_details
from chunking_engine_v2 import hierarchical_chunk, get_child_chunks
from db_config import get_db_connection

def test_database_connection():
    """Test PostgreSQL connection"""
    print("🔌 Testing database connection...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                print(f"✅ Connected to PostgreSQL: {version['version'][:50]}...")
                return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_create_parent_chunk():
    """Test creating a parent chunk following chunk_format.txt schema"""
    print("\n📝 Testing parent chunk creation...")
    
    # Sample data matching chunk_format.txt structure
    input_data = {
        # Identity
        'document_type': 'circular',
        'act': 'Companies Act, 2013',
        'section': '135',
        'sub_section': None,
        'page_number': None,
        
        # Content
        'title': 'CSR General Circular – Clarification on Schedule VII',
        'compliance_area': 'Corporate Social Responsibility',
        
        # Administrative
        'issued_by': 'Ministry of Corporate Affairs',
        'notification_number': 'General Circular No. 02/2024',
        'source_type': 'Gazette',
        'document_language': 'en',
        
        # Temporal
        'date_issued': '2024-01-22',
        'effective_from': '2024-01-22',
        
        # Source
        'source_path': 'raw/companies_act/section_135/circulars/csr_gc_02_2024.pdf',
        'source_url': 'https://mca.gov.in/...',
        
        # Versioning
        'version': 'v1.0'
    }
    
    success, message, chunk_id = create_parent_chunk(input_data, 'admin_arya')
    
    if success:
        print(f"✅ Parent chunk created: {chunk_id}")
        return chunk_id
    else:
        print(f"❌ Failed to create parent chunk: {message}")
        return None

def test_update_chunk_text(chunk_id: str):
    """Test updating chunk text"""
    print(f"\n📄 Testing text update for {chunk_id}...")
    
    full_text = """MINISTRY OF CORPORATE AFFAIRS
NOTIFICATION

General Circular No. 02/2024
22nd January 2024

Subject: Clarification on Corporate Social Responsibility (CSR) under Section 135

In exercise of the powers conferred under Section 135 of the Companies Act, 2013, the Ministry of Corporate Affairs hereby clarifies the following:

1. ELIGIBLE CSR EXPENDITURE

1.1 Only expenditures directly linked to Schedule VII activities shall qualify as CSR expenditure. Administrative overheads shall not exceed 5% of total CSR expenditure.

1.2 CSR projects must demonstrate clear social impact and align with at least one area specified in Schedule VII of the Companies Act, 2013.

2. REPORTING REQUIREMENTS

2.1 Companies must file CSR reports in Form CSR-2 within the prescribed timelines as per Rule 8 of Companies (CSR Policy) Rules, 2014.

2.2 The CSR Committee shall monitor implementation of CSR activities and ensure compliance with applicable regulations.

3. INTERPRETATION OF SCHEDULE VII

3.1 Schedule VII items shall be interpreted broadly to promote social welfare objectives.

3.2 Activities that contribute to inclusive growth and sustainable development shall be considered eligible CSR activities, provided they align with one or more areas specified in Schedule VII.

3.3 Companies may undertake collaborative CSR projects with other companies, subject to individual reporting of contributions.

4. MONITORING AND COMPLIANCE

4.1 The Board of Directors shall ensure that CSR expenditure meets statutory requirements and is properly documented.

4.2 Impact assessment of CSR projects with outlays exceeding Rs. 1 crore shall be conducted through independent agencies.

This circular shall come into force with immediate effect and shall apply to all companies covered under Section 135 of the Companies Act, 2013."""

    success, message = update_chunk_text(chunk_id, full_text, updated_by='admin_arya')
    
    if success:
        print(f"✅ Text updated successfully")
        return True
    else:
        print(f"❌ Failed to update text: {message}")
        return False

def test_hierarchical_chunking(parent_chunk_id: str):
    """Test splitting parent into child chunks"""
    print(f"\n✂️ Testing hierarchical chunking for {parent_chunk_id}...")
    
    # Get parent text
    parent_details = get_chunk_details(parent_chunk_id)
    if not parent_details or not parent_details.get('text'):
        print("❌ No text found in parent chunk")
        return None
    
    text = parent_details['text']
    
    success, message, child_ids = hierarchical_chunk(
        parent_chunk_id=parent_chunk_id,
        text=text,
        max_chars=1000,  # Optimal for legal text (preserves semantic units)
        overlap=100,
        created_by='admin_arya'
    )
    
    if success:
        print(f"✅ Created {len(child_ids)} child chunks:")
        for i, child_id in enumerate(child_ids, 1):
            print(f"   {i}. {child_id}")
        return child_ids
    else:
        print(f"❌ Chunking failed: {message}")
        return None

def test_schema_compliance(parent_chunk_id: str, child_ids: list):
    """Verify database structure matches chunk_format.txt"""
    print(f"\n✅ Testing schema compliance with chunk_format.txt...")
    
    # Fetch parent chunk with all relationships
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get full parent chunk data
                cursor.execute("""
                    SELECT 
                        ci.chunk_id,
                        ci.chunk_role,
                        ci.parent_chunk_id,
                        ci.document_type,
                        ci.authority_level,
                        ci.binding,
                        ci.act,
                        ci.section,
                        ci.sub_section,
                        ci.page_number,
                        cc.title,
                        cc.compliance_area,
                        cc.text,
                        cc.summary,
                        cc.citation,
                        crr.priority::text as priority,
                        crr.requires_parent_law,
                        crp.can_answer_standalone,
                        crp.must_reference_parent_law,
                        crp.refuse_if_parent_missing,
                        ct.date_issued,
                        ct.effective_from,
                        ct.effective_to,
                        cl.status,
                        cv.version,
                        ce.enabled as embedding_enabled,
                        ca.issued_by,
                        ca.notification_number,
                        ca.source_type,
                        ca.document_language,
                        caud.uploaded_by,
                        caud.uploaded_at,
                        caud.approved_by,
                        caud.approved_at,
                        cs.path,
                        cs.url
                    FROM chunks_identity ci
                    LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                    LEFT JOIN chunk_retrieval_rules crr ON ci.chunk_id = crr.chunk_id
                    LEFT JOIN chunk_refusal_policy crp ON ci.chunk_id = crp.chunk_id
                    LEFT JOIN chunk_temporal ct ON ci.chunk_id = ct.chunk_id
                    LEFT JOIN chunk_lifecycle cl ON ci.chunk_id = cl.chunk_id
                    LEFT JOIN chunk_versioning cv ON ci.chunk_id = cv.chunk_id
                    LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                    LEFT JOIN chunk_administrative ca ON ci.chunk_id = ca.chunk_id
                    LEFT JOIN chunk_audit caud ON ci.chunk_id = caud.chunk_id
                    LEFT JOIN chunk_source cs ON ci.chunk_id = cs.chunk_id
                    WHERE ci.chunk_id = %s
                """, (parent_chunk_id,))
                
                parent_data = dict(cursor.fetchone())
                
                # Check required fields from chunk_format.txt
                required_fields = {
                    'chunk_id': parent_data.get('chunk_id'),
                    'chunk_role': parent_data.get('chunk_role'),
                    'document_type': parent_data.get('document_type'),
                    'authority_level': parent_data.get('authority_level'),
                    'binding': parent_data.get('binding'),
                    'act': parent_data.get('act'),
                    'section': parent_data.get('section'),
                    'title': parent_data.get('title'),
                    'compliance_area': parent_data.get('compliance_area'),
                    'priority': parent_data.get('priority'),
                    'requires_parent_law': parent_data.get('requires_parent_law'),
                    'can_answer_standalone': parent_data.get('can_answer_standalone'),
                    'must_reference_parent_law': parent_data.get('must_reference_parent_law'),
                    'refuse_if_parent_missing': parent_data.get('refuse_if_parent_missing'),
                    'status': parent_data.get('status'),
                    'embedding_enabled': parent_data.get('embedding_enabled'),
                    'issued_by': parent_data.get('issued_by'),
                    'notification_number': parent_data.get('notification_number')
                }
                
                print("\n📊 Parent Chunk Schema Validation:")
                print("=" * 60)
                for field, value in required_fields.items():
                    status = "✅" if value is not None else "⚠️"
                    print(f"{status} {field}: {value}")
                
                # Verify child chunks
                print(f"\n📦 Child Chunks ({len(child_ids)} total):")
                print("=" * 60)
                
                for i, child_id in enumerate(child_ids[:2], 1):  # Show first 2
                    cursor.execute("""
                        SELECT 
                            ci.chunk_id,
                            ci.chunk_role,
                            ci.parent_chunk_id,
                            cc.text,
                            ce.enabled as embedding_enabled
                        FROM chunks_identity ci
                        LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                        LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                        WHERE ci.chunk_id = %s
                    """, (child_id,))
                    
                    child_data = dict(cursor.fetchone())
                    print(f"\nChild {i}: {child_data['chunk_id']}")
                    print(f"  Role: {child_data['chunk_role']}")
                    print(f"  Parent: {child_data['parent_chunk_id']}")
                    print(f"  Text Length: {len(child_data['text']) if child_data['text'] else 0} chars")
                    print(f"  Embedding Enabled: {child_data['embedding_enabled']}")
                
                # Check relationships
                cursor.execute("""
                    SELECT relationship, to_chunk_id
                    FROM chunk_relationships
                    WHERE from_chunk_id = %s
                """, (parent_chunk_id,))
                
                relationships = cursor.fetchall()
                print(f"\n🔗 Relationships ({len(relationships)} total):")
                for rel in relationships[:5]:  # Show first 5
                    print(f"  {rel['relationship']}: {rel['to_chunk_id']}")
                
                # Verify governance rules
                print("\n⚖️ Governance Rules:")
                print("=" * 60)
                print(f"Priority: {parent_data['priority']} (2 = Rules/Notifications)")
                print(f"Can Answer Standalone: {parent_data['can_answer_standalone']}")
                print(f"Must Reference Parent Law: {parent_data['must_reference_parent_law']}")
                print(f"Refuse if Parent Missing: {parent_data['refuse_if_parent_missing']}")
                
                # Parent chunk should NOT be embedded
                print(f"\n🚫 Parent Embedding Check:")
                print(f"Enabled: {parent_data['embedding_enabled']} (should be False)")
                if parent_data['embedding_enabled'] == False:
                    print("✅ PASS: Parent chunk correctly NOT embedded")
                else:
                    print("❌ FAIL: Parent chunk should not be embedded!")
                
                return True
                
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def test_query_child_chunks_by_parent(parent_chunk_id: str):
    """Test retrieving child chunks (simulates child_chunk_ids field)"""
    print(f"\n🔍 Testing child chunk retrieval...")
    
    children = get_child_chunks(parent_chunk_id)
    
    print(f"Found {len(children)} child chunks:")
    for i, child in enumerate(children, 1):
        print(f"  {i}. {child['chunk_id']} (embedded: {child['embeddings_enabled']})")
    
    return children

def run_all_tests():
    """Run complete test suite"""
    print("=" * 80)
    print("🧪 GOVERNANCE RAG - CHUNKING TEST SUITE")
    print("=" * 80)
    
    # Test 1: Database connection
    if not test_database_connection():
        print("\n❌ Database connection failed. Exiting...")
        return
    
    # Test 2: Create parent chunk
    parent_chunk_id = test_create_parent_chunk()
    if not parent_chunk_id:
        print("\n❌ Parent chunk creation failed. Exiting...")
        return
    
    # Test 3: Update text
    if not test_update_chunk_text(parent_chunk_id):
        print("\n❌ Text update failed. Exiting...")
        return
    
    # Test 4: Hierarchical chunking
    child_ids = test_hierarchical_chunking(parent_chunk_id)
    if not child_ids:
        print("\n❌ Chunking failed. Exiting...")
        return
    
    # Test 5: Schema compliance
    test_schema_compliance(parent_chunk_id, child_ids)
    
    # Test 6: Query child chunks
    test_query_child_chunks_by_parent(parent_chunk_id)
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print(f"\nParent Chunk ID: {parent_chunk_id}")
    print(f"Child Chunks: {len(child_ids)}")
    print("\n💡 Next Steps:")
    print("   1. Verify data in pgAdmin (http://localhost:5050)")
    print("   2. Run embedding test: python test_embedding.py")
    print("   3. Test retrieval: python test_retrieval.py")

if __name__ == '__main__':
    run_all_tests()
