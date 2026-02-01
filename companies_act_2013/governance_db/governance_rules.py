"""
Governance rules and validation logic
"""
from typing import Dict, Any

# Document type to binding mapping (from chunk_format.txt)
# NOTE: Notifications are binding ONLY IF they:
#   - Bring sections into force
#   - Grant exemptions
#   - Amend applicability
# This is determined at ingestion time based on notification content/type
BINDING_RULES = {
    'act': True,
    'rule': True,
    'regulation': True,
    'order': True,  # Statutory orders are binding
    'notification': True,  # Default True (admin can override based on notification type)
    'circular': False,
    'sop': False,
    'form': False,
    'guideline': False,
    'practice_note': False,
    'commentary': False,
    'textbook': False,
    'qa_book': False
}

# Document type to retrieval priority mapping (from chunk_format.txt)
PRIORITY_RULES = {
    'act': '1',
    'rule': '1',
    'regulation': '2',
    'notification': '2',
    'order': '2',
    'circular': '2',
    'sop': '3',
    'form': '3',
    'guideline': '3',
    'practice_note': '4',
    'commentary': '4',
    'textbook': '4',
    'qa_book': '4'
}

# Authority level mapping
AUTHORITY_LEVEL_RULES = {
    'act': 'statutory',
    'rule': 'statutory',
    'regulation': 'statutory',
    'order': 'interpretive',
    'notification': 'interpretive',
    'circular': 'interpretive',
    'sop': 'procedural',
    'form': 'procedural',
    'guideline': 'procedural',
    'practice_note': 'commentary',
    'commentary': 'commentary',
    'textbook': 'commentary',
    'qa_book': 'commentary'
}

def get_binding_status(document_type: str) -> bool:
    """Determine if document type is binding"""
    return BINDING_RULES.get(document_type, False)

def get_retrieval_priority(document_type: str) -> str:
    """Get retrieval priority for document type"""
    return PRIORITY_RULES.get(document_type, '4')

def get_authority_level(document_type: str) -> str:
    """Get authority level for document type"""
    return AUTHORITY_LEVEL_RULES.get(document_type, 'commentary')

def get_refusal_policy(document_type: str, priority: str) -> Dict[str, bool]:
    """
    Determine refusal policy based on document type and priority
    
    Priority 1 (Acts/Rules): Can answer standalone
    Priority 2 (Circulars/Notifications): Must reference parent law
    Priority 3-4: Can answer standalone but with context
    """
    if priority == '1':
        return {
            'can_answer_standalone': True,
            'must_reference_parent_law': False,
            'refuse_if_parent_missing': False
        }
    elif priority == '2':
        return {
            'can_answer_standalone': False,
            'must_reference_parent_law': True,
            'refuse_if_parent_missing': True
        }
    else:
        return {
            'can_answer_standalone': True,
            'must_reference_parent_law': False,
            'refuse_if_parent_missing': False
        }

def requires_parent_law(priority: str) -> bool:
    """Check if document requires parent law for retrieval"""
    return priority == '2'

def validate_chunk_input(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate chunk input data
    
    Returns: (is_valid, error_message)
    """
    required_fields = ['document_type']
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    document_type = data['document_type']
    if document_type not in BINDING_RULES:
        return False, f"Invalid document_type: {document_type}"
    
    # Validate chunk_role if provided
    if 'chunk_role' in data:
        if data['chunk_role'] not in ['parent', 'child']:
            return False, f"Invalid chunk_role: {data['chunk_role']}"
    
    # Validate parent_chunk_id consistency
    if data.get('chunk_role') == 'parent' and data.get('parent_chunk_id'):
        return False, "Parent chunks cannot have parent_chunk_id"
    
    if data.get('chunk_role') == 'child' and not data.get('parent_chunk_id'):
        return False, "Child chunks must have parent_chunk_id"
    
    return True, ""

def validate_relationship(from_chunk_type: str, relationship: str, to_chunk_type: str) -> tuple[bool, str]:
    """
    Validate if relationship is semantically correct
    
    Returns: (is_valid, error_message)
    """
    # Bidirectional relationship pairs
    bidirectional_pairs = {
        'clarifies': 'clarified_by',
        'proceduralises': 'proceduralised_by',
        'implements': 'implemented_by',
        'amends': 'amended_by',
        'supersedes': 'superseded_by'
    }
    
    # Specific rules (can be extended)
    if relationship == 'implements':
        # Only procedural docs can implement statutory docs
        if from_chunk_type not in ['sop', 'form', 'guideline']:
            return False, f"{from_chunk_type} cannot implement other documents"
        if to_chunk_type not in ['act', 'rule', 'regulation']:
            return False, f"Can only implement statutory documents"
    
    if relationship == 'amends':
        # Generally same level documents
        if from_chunk_type not in ['act', 'rule', 'regulation', 'notification']:
            return False, f"{from_chunk_type} cannot amend other documents"
    
    return True, ""
