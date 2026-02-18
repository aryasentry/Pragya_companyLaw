import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from db_config import get_db_connection

REFERENCE_PATTERNS = {

    'section': [
        r'[Ss]ection\s+(\d+)(?:\s*\((\d+)\))?',
        r'[Ss]ections?\s+(\d+)(?:\s*,\s*(\d+))*(?:\s+and\s+(\d+))?',
        r'[Ss]ec\.\s*(\d+)',
    ],
    
    'sub_section': [
        r'[Ss]ub-?[Ss]ection\s*\((\d+)\)(?:\s*\(([a-z])\))?',
    ],
    
    'rule': [
        r'[Rr]ule\s+(\d+)(?:\s*\((\d+)\))?',
        r'[Rr]ules?\s+(\d+)(?:\s*,\s*(\d+))*(?:\s+and\s+(\d+))?',
    ],
    
    'notification': [
        r'S\.O\.\s*(\d+)\s*\(?E?\)?',
        r'G\.S\.R\.\s*(\d+)\s*\(?E?\)?',
        r'[Nn]otification\s+[Nn]o\.\s*(\d+)',
    ],
    
    'circular': [
        r'[Cc]ircular\s+[Nn]o\.\s*(\d+)(?:/(\d{4}))?',
        r'[Gg]eneral\s+[Cc]ircular\s+[Nn]o\.\s*(\d+)(?:/(\d{4}))?',
    ],
    
    'form': [
        r'[Ff]orm\s+([A-Z]{2,4}-?\d+)',
        r'[Ff]orm\s+[Nn]o\.\s*([A-Z]{2,4}-?\d+)',
    ],
    
    'schedule': [
        r'[Ss]chedule\s+([IVXLCDM]+|\d+)',
    ],
}

RELATIONSHIP_INDICATORS = {
    'amends': [
        r'amended\s+by',
        r'as\s+amended',
        r'amendment\s+to',
        r'substituted\s+by',
        r'omitted\s+by',
        r'inserted\s+by',
    ],
    'clarifies': [
        r'clarified\s+(?:by|in|vide)',
        r'clarification',
        r'explained\s+in',
        r'interpretation',
    ],
    'implements': [
        r'in\s+pursuance\s+of',
        r'pursuant\s+to',
        r'in\s+exercise\s+of',
        r'under\s+(?:the\s+)?powers',
        r'empowered\s+by',
    ],
    'proceduralises': [
        r'procedure\s+for',
        r'form\s+for',
        r'manner\s+of',
        r'prescribed\s+in',
    ],
    'supersedes': [
        r'superseded\s+by',
        r'replaced\s+by',
        r'in\s+supersession\s+of',
    ],
    'references': [
        r'as\s+per',
        r'subject\s+to',
        r'notwithstanding',
        r'in\s+accordance\s+with',
        r'referred\s+to\s+in',
        r'mentioned\s+in',
        r'specified\s+in',
        r'provided\s+in',
    ],
}

@dataclass
class ExtractedReference:
    ref_type: str
    ref_number: str
    sub_ref: Optional[str]
    relationship: str
    context: str
    confidence: float
    target_chunk_id: Optional[str] = None

def extract_references(text: str, current_section: str) -> List[ExtractedReference]:
    references = []
    current_sec_int = int(current_section) if current_section else 0
    
    for ref_type, patterns in REFERENCE_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):

                ref_number = match.group(1)
                sub_ref = match.group(2) if match.lastindex >= 2 else None
                
                if ref_type == 'section':
                    try:
                        if int(ref_number) == current_sec_int:
                            continue
                    except ValueError:
                        pass
                
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]
                
                relationship = _determine_relationship(context)
                
                confidence = _calculate_confidence(context, ref_type, relationship)
                
                references.append(ExtractedReference(
                    ref_type=ref_type,
                    ref_number=ref_number,
                    sub_ref=sub_ref,
                    relationship=relationship,
                    context=context,
                    confidence=confidence
                ))
    
    return _deduplicate_references(references)

def _determine_relationship(context: str) -> str:
    context_lower = context.lower()
    
    for rel_type, patterns in RELATIONSHIP_INDICATORS.items():
        for pattern in patterns:
            if re.search(pattern, context_lower):
                return rel_type
    
    return 'references'

def _calculate_confidence(context: str, ref_type: str, relationship: str) -> float:
    confidence = 0.5
    
    if relationship != 'references':
        confidence += 0.2
    
    formal_indicators = ['pursuant', 'accordance', 'provisions of', 'under section']
    if any(ind in context.lower() for ind in formal_indicators):
        confidence += 0.2
    
    ambiguous_indicators = ['may', 'might', 'could', 'similar to']
    if any(ind in context.lower() for ind in ambiguous_indicators):
        confidence -= 0.1
    
    return min(1.0, max(0.0, confidence))

def _deduplicate_references(refs: List[ExtractedReference]) -> List[ExtractedReference]:
    seen = {}
    for ref in refs:
        key = (ref.ref_type, ref.ref_number, ref.sub_ref)
        if key not in seen or ref.confidence > seen[key].confidence:
            seen[key] = ref
    return list(seen.values())

def resolve_reference_to_chunk_id(ref: ExtractedReference, current_section: str) -> Optional[str]:
    """Resolve a reference to an actual chunk ID in the database"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        if ref.ref_type == 'section':
            section_padded = ref.ref_number.zfill(3)
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'act'
                AND section = %s
                AND chunk_role = 'parent'
                LIMIT 1
            """, (section_padded,))
            
            result = cur.fetchone()
            cur.close()
            return result['chunk_id'] if result else None
        
        # For other reference types, return None for now
        cur.close()
        return None

def create_relationship(from_chunk_id: str, to_chunk_id: str, relationship: str, confidence: float) -> bool:
    """Create a relationship in the database"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chunk_relationships (source_chunk_id, target_chunk_id, relationship_type, confidence_score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (from_chunk_id, to_chunk_id, relationship, confidence))
            cur.close()
        return True
    except Exception:
        return False

def extract_and_create_relationships(
    chunk_id: str,
    text: str,
    document_type: str,
    current_section: Optional[str] = None,
    min_confidence: float = 0.5
) -> Dict[str, int]:
    """Extract references from text and create relationships"""
    
    references = extract_references(text, current_section or '')
    
    stats = {
        'extracted': len(references),
        'resolved': 0,
        'created': 0
    }
    
    for ref in references:
        if ref.confidence < min_confidence:
            continue
        
        target_chunk_id = resolve_reference_to_chunk_id(ref, current_section or '')
        
        if target_chunk_id:
            stats['resolved'] += 1
            
            if create_relationship(chunk_id, target_chunk_id, ref.relationship, ref.confidence):
                stats['created'] += 1
    
    return stats