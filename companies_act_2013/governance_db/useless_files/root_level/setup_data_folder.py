"""
Setup Data folder structure for document uploads
Matches admin panel document types with proper priority assignments
"""
from pathlib import Path

# Base data directory
DATA_DIR = Path(__file__).parent / "data"

# Document types with priority (1=highest, 4=lowest)
DOC_TYPES_WITH_PRIORITY = {
    'companies_act': {
        'Act': 1,
        'Rule': 1,
        'Regulation': 2,
        'Order': 2,
        'Notification': 2,
        'Circular': 3,
        'Form': 3,
        'Schedule': 2,
        'Register': 3,
        'Return': 3,
        'Q&A': 4,
        'Others': 4
    },
    'non_binding': {
        'SOP': 3,
        'Guideline': 3,
        'Practice Note': 4,
        'Commentary': 4,
        'Textbook': 4,
        'Q&A': 4,
        'Others': 4
    }
}

def get_priority_mapping():
    """Get flat mapping of document type to priority"""
    priority_map = {}
    for category in DOC_TYPES_WITH_PRIORITY.values():
        priority_map.update(category)
    return priority_map

def create_data_structure():
    """Create data folder structure for uploads"""
    print("Creating Data folder structure...")
    print("=" * 70)
    
    # Create base folders
    for doc_category, doc_types in DOC_TYPES_WITH_PRIORITY.items():
        base_path = DATA_DIR / doc_category
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create section folders for companies_act
        if doc_category == 'companies_act':
            for section_num in range(1, 44):
                section_name = f"section_{section_num:03d}"
                
                for doc_type, priority in doc_types.items():
                    folder_path = base_path / section_name / doc_type
                    folder_path.mkdir(parents=True, exist_ok=True)
            
            print(f"✅ {doc_category}:")
            print(f"   - Created 43 sections")
            print(f"   - Document types: {', '.join(doc_types.keys())}")
            for doc_type, priority in doc_types.items():
                print(f"     • {doc_type} (Priority {priority})")
        else:
            # Create type folders for non-binding
            for doc_type, priority in doc_types.items():
                folder_path = base_path / doc_type
                folder_path.mkdir(parents=True, exist_ok=True)
            
            print(f"\n✅ {doc_category}:")
            print(f"   - Document types: {', '.join(doc_types.keys())}")
            for doc_type, priority in doc_types.items():
                print(f"     • {doc_type} (Priority {priority})")
    
    print("\n" + "=" * 70)
    print(f"📁 Data structure created at: {DATA_DIR.absolute()}")
    print("=" * 70)

if __name__ == "__main__":
    create_data_structure()
