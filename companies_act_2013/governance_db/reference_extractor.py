"""
Reference Extractor - Automatic Cross-Section Relationship Detection
Extracts legal references from document text and creates relationships in PostgreSQL

Usage:
    from reference_extractor import extract_and_create_relationships
    
    # During ingestion
    relationships_created = extract_and_create_relationships(
        chunk_id='ca2013_circular_xyz',
        text='...as per Section 45 of the Act...',
        document_type='circular',
        current_section='003'
    )
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from db_config import get_db_connection

# Regex patterns for legal references
REFERENCE_PATTERNS = {
    # Section references: "Section 45", "section 45(2)", "Sections 45 and 46"
    'section': [
        r'[Ss]ection\s+(\d+)(?:\s*\((\d+)\))?',
        r'[Ss]ections?\s+(\d+)(?:\s*,\s*(\d+))*(?:\s+and\s+(\d+))?',
        r'[Ss]ec\.\s*(\d+)',
    ],
    
    # Sub-section: "sub-section (2)", "Sub-Section (3)(a)"
    'sub_section': [
        r'[Ss]ub-?[Ss]ection\s*\((\d+)\)(?:\s*\(([a-z])\))?',
    ],
    
    # Rule references: "Rule 7", "Rules 3, 4 and 5"
    'rule': [
        r'[Rr]ule\s+(\d+)(?:\s*\((\d+)\))?',
        r'[Rr]ules?\s+(\d+)(?:\s*,\s*(\d+))*(?:\s+and\s+(\d+))?',
    ],
    
    # Notification references: "S.O. 1234(E)", "G.S.R. 567"
    'notification': [
        r'S\.O\.\s*(\d+)\s*\(?E?\)?',
        r'G\.S\.R\.\s*(\d+)\s*\(?E?\)?',
        r'[Nn]otification\s+[Nn]o\.\s*(\d+)',
    ],
    
    # Circular references: "Circular No. 16/2013", "General Circular No. 32/2014"
    'circular': [
        r'[Cc]ircular\s+[Nn]o\.\s*(\d+)(?:/(\d{4}))?',
        r'[Gg]eneral\s+[Cc]ircular\s+[Nn]o\.\s*(\d+)(?:/(\d{4}))?',
    ],
    
    # Form references: "Form INC-4", "Form No. MGT-7"
    'form': [
        r'[Ff]orm\s+([A-Z]{2,4}-?\d+)',
        r'[Ff]orm\s+[Nn]o\.\s*([A-Z]{2,4}-?\d+)',
    ],
    
    # Schedule references: "Schedule I", "Schedule III"
    'schedule': [
        r'[Ss]chedule\s+([IVXLCDM]+|\d+)',
    ],
}

# Context phrases that indicate relationship type
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
    """Represents a legal reference extracted from text"""
    ref_type: str           # 'section', 'rule', 'notification', etc.
    ref_number: str         # '45', '7', '1234', etc.
    sub_ref: Optional[str]  # '(2)', '(a)', etc.
    relationship: str       # 'references', 'amends', 'clarifies', etc.
    context: str            # Surrounding text for verification
    confidence: float       # 0.0 to 1.0
    target_chunk_id: Optional[str] = None  # Resolved chunk ID


def extract_references(text: str, current_section: str) -> List[ExtractedReference]:
    """
    Extract all legal references from text.
    
    Args:
        text: Document text to analyze
        current_section: Current section number (to exclude self-references)
    
    Returns:
        List of ExtractedReference objects
    """
    references = []
    current_sec_int = int(current_section) if current_section else 0
    
    for ref_type, patterns in REFERENCE_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Get reference number
                ref_number = match.group(1)
                sub_ref = match.group(2) if match.lastindex >= 2 else None
                
                # Skip self-references for sections
                if ref_type == 'section':
                    try:
                        if int(ref_number) == current_sec_int:
                            continue
                    except ValueError:
                        pass
                
                # Get context (100 chars before and after)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]
                
                # Determine relationship type from context
                relationship = _determine_relationship(context)
                
                # Calculate confidence based on context clarity
                confidence = _calculate_confidence(context, ref_type, relationship)
                
                references.append(ExtractedReference(
                    ref_type=ref_type,
                    ref_number=ref_number,
                    sub_ref=sub_ref,
                    relationship=relationship,
                    context=context,
                    confidence=confidence
                ))
    
    # Deduplicate
    return _deduplicate_references(references)


def _determine_relationship(context: str) -> str:
    """Determine relationship type from surrounding context"""
    context_lower = context.lower()
    
    # Check for specific relationship indicators
    for rel_type, patterns in RELATIONSHIP_INDICATORS.items():
        for pattern in patterns:
            if re.search(pattern, context_lower):
                return rel_type
    
    # Default to 'references' for general mentions
    return 'references'


def _calculate_confidence(context: str, ref_type: str, relationship: str) -> float:
    """Calculate confidence score for extracted reference"""
    confidence = 0.5  # Base confidence
    
    # Higher confidence for explicit relationship indicators
    if relationship != 'references':
        confidence += 0.2
    
    # Higher confidence for formal references
    formal_indicators = ['pursuant', 'accordance', 'provisions of', 'under section']
    if any(ind in context.lower() for ind in formal_indicators):
        confidence += 0.2
    
    # Lower confidence for ambiguous context
    ambiguous_indicators = ['may', 'might', 'could', 'similar to']
    if any(ind in context.lower() for ind in ambiguous_indicators):
        confidence -= 0.1
    
    return min(1.0, max(0.0, confidence))


def _deduplicate_references(refs: List[ExtractedReference]) -> List[ExtractedReference]:
    """Remove duplicate references, keeping highest confidence"""
    seen = {}
    for ref in refs:
        key = (ref.ref_type, ref.ref_number, ref.sub_ref)
        if key not in seen or ref.confidence > seen[key].confidence:
            seen[key] = ref
    return list(seen.values())


def resolve_reference_to_chunk_id(ref: ExtractedReference, current_section: str) -> Optional[str]:
    """
    Resolve an extracted reference to an actual chunk_id in the database.
    
    Args:
        ref: The extracted reference
        current_section: Current document's section
    
    Returns:
        chunk_id if found, None otherwise
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        if ref.ref_type == 'section':
            # Look for Act chunk with this section number
            section_padded = ref.ref_number.zfill(3)
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'act'
                AND section = %s
                AND chunk_role = 'parent'
                LIMIT 1
            """, (section_padded,))
            
        elif ref.ref_type == 'rule':
            # Look for Rule chunk
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'rule'
                AND chunk_role = 'parent'
                AND chunk_id LIKE %s
                LIMIT 1
            """, (f'%rule%{ref.ref_number}%',))
            
        elif ref.ref_type == 'notification':
            # Look for Notification chunk by S.O./G.S.R. number
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'notification'
                AND chunk_role = 'parent'
                AND (chunk_id LIKE %s OR chunk_id LIKE %s)
                LIMIT 1
            """, (f'%{ref.ref_number}%', f'%so-{ref.ref_number}%'))
            
        elif ref.ref_type == 'circular':
            # Look for Circular chunk
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'circular'
                AND chunk_role = 'parent'
                AND chunk_id LIKE %s
                LIMIT 1
            """, (f'%circular%{ref.ref_number}%',))
            
        elif ref.ref_type == 'form':
            # Look for Form chunk
            form_name = ref.ref_number.lower().replace('-', '')
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'form'
                AND chunk_role = 'parent'
                AND LOWER(REPLACE(chunk_id, '-', '')) LIKE %s
                LIMIT 1
            """, (f'%{form_name}%',))
            
        elif ref.ref_type == 'schedule':
            # Look for Schedule chunk
            cur.execute("""
                SELECT chunk_id FROM chunks_identity
                WHERE document_type = 'schedule'
                AND chunk_role = 'parent'
                AND chunk_id LIKE %s
                LIMIT 1
            """, (f'%schedule%{ref.ref_number}%',))
        
        else:
            cur.close()
            return None
        
        result = cur.fetchone()
        cur.close()
        
        return result['chunk_id'] if result else None


def create_relationship_in_db(
    from_chunk_id: str,
    to_chunk_id: str,
    relationship: str,
    confidence: float = 1.0
) -> bool:
    """
    Create a relationship in the database.
    
    Args:
        from_chunk_id: Source chunk
        to_chunk_id: Target chunk
        relationship: Relationship type
        confidence: Extraction confidence (for logging)
    
    Returns:
        True if created, False if already exists or error
    """
    # Map our relationship types to the DB enum
    RELATIONSHIP_MAP = {
        'references': 'clarifies',      # Generic reference → clarifies
        'amends': 'amends',
        'clarifies': 'clarifies',
        'implements': 'implements',
        'proceduralises': 'proceduralises',
        'supersedes': 'supersedes',
    }
    
    db_relationship = RELATIONSHIP_MAP.get(relationship, 'clarifies')
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO chunk_relationships (from_chunk_id, to_chunk_id, relationship, created_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (from_chunk_id, to_chunk_id, db_relationship, f'auto_extract:{confidence:.2f}'))
            
            created = cur.rowcount > 0
            cur.close()
            return created
            
    except Exception as e:
        print(f"Error creating relationship: {e}")
        return False


def extract_and_create_relationships(
    chunk_id: str,
    text: str,
    document_type: str,
    current_section: str,
    min_confidence: float = 0.5
) -> Dict[str, int]:
    """
    Main entry point: Extract references from text and create relationships.
    
    Args:
        chunk_id: The chunk being processed
        text: Document text
        document_type: Type of document ('circular', 'notification', etc.)
        current_section: Section number this document relates to
        min_confidence: Minimum confidence to create relationship
    
    Returns:
        Dict with counts: {'extracted': N, 'resolved': N, 'created': N}
    """
    stats = {'extracted': 0, 'resolved': 0, 'created': 0, 'relationships': []}
    
    # Step 1: Extract references from text
    references = extract_references(text, current_section)
    stats['extracted'] = len(references)
    
    # Step 2: Resolve and create relationships
    for ref in references:
        if ref.confidence < min_confidence:
            continue
        
        # Resolve to actual chunk_id
        target_chunk_id = resolve_reference_to_chunk_id(ref, current_section)
        
        if target_chunk_id:
            stats['resolved'] += 1
            ref.target_chunk_id = target_chunk_id
            
            # Create relationship
            if create_relationship_in_db(chunk_id, target_chunk_id, ref.relationship, ref.confidence):
                stats['created'] += 1
                stats['relationships'].append({
                    'from': chunk_id,
                    'to': target_chunk_id,
                    'type': ref.relationship,
                    'ref': f"{ref.ref_type} {ref.ref_number}",
                    'confidence': ref.confidence
                })
    
    return stats


def analyze_document_references(text: str, section: str) -> Dict:
    """
    Analyze a document's references without creating relationships.
    Useful for preview/validation before ingestion.
    
    Args:
        text: Document text
        section: Current section number
    
    Returns:
        Analysis report
    """
    references = extract_references(text, section)
    
    # Group by type
    by_type = {}
    for ref in references:
        if ref.ref_type not in by_type:
            by_type[ref.ref_type] = []
        by_type[ref.ref_type].append({
            'number': ref.ref_number,
            'sub_ref': ref.sub_ref,
            'relationship': ref.relationship,
            'confidence': ref.confidence,
            'context': ref.context[:100] + '...' if len(ref.context) > 100 else ref.context
        })
    
    return {
        'total_references': len(references),
        'by_type': by_type,
        'high_confidence': len([r for r in references if r.confidence >= 0.7]),
        'relationships_preview': [
            f"{r.ref_type} {r.ref_number} → {r.relationship}"
            for r in references if r.confidence >= 0.5
        ]
    }


# CLI for testing
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Extract legal references from text')
    parser.add_argument('--file', type=str, help='Text file to analyze')
    parser.add_argument('--text', type=str, help='Direct text input')
    parser.add_argument('--section', type=str, default='001', help='Current section number')
    parser.add_argument('--chunk-id', type=str, help='Chunk ID (required for creating relationships)')
    parser.add_argument('--doc-type', type=str, default='circular', help='Document type')
    parser.add_argument('--create', action='store_true', help='Actually create relationships in DB')
    parser.add_argument('--min-confidence', type=float, default=0.5, help='Minimum confidence threshold')
    
    args = parser.parse_args()
    
    # Get text
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        # Demo text
        text = """
        As per Section 45 of the Companies Act, 2013, read with Rule 7 of the 
        Companies (Acceptance of Deposits) Rules, 2014, as amended by S.O. 1234(E), 
        the company shall file Form DPT-3 within the prescribed time limit.
        
        This circular clarifies the provisions of Section 73 and Section 74 
        pursuant to the notification G.S.R. 567 dated 01.04.2014.
        
        Reference is also made to General Circular No. 16/2013 and Schedule III.
        """
    
    print("=" * 70)
    print("REFERENCE EXTRACTOR - Analysis")
    print("=" * 70)
    
    # Analyze
    analysis = analyze_document_references(text, args.section)
    
    print(f"\n📊 Found {analysis['total_references']} references:")
    print(f"   High confidence (≥0.7): {analysis['high_confidence']}")
    
    print(f"\n📋 By Type:")
    for ref_type, refs in analysis['by_type'].items():
        print(f"\n   {ref_type.upper()}:")
        for ref in refs:
            conf_indicator = "✓" if ref['confidence'] >= 0.7 else "?"
            print(f"      {conf_indicator} {ref['number']} → {ref['relationship']} (confidence: {ref['confidence']:.2f})")
    
    print(f"\n🔗 Relationships Preview:")
    for rel in analysis['relationships_preview']:
        print(f"   • {rel}")
    
    # Create relationships if requested
    if args.create and args.chunk_id:
        print(f"\n" + "=" * 70)
        print("CREATING RELATIONSHIPS IN DATABASE")
        print("=" * 70)
        
        stats = extract_and_create_relationships(
            chunk_id=args.chunk_id,
            text=text,
            document_type=args.doc_type,
            current_section=args.section,
            min_confidence=args.min_confidence
        )
        
        print(f"\n✓ Extracted: {stats['extracted']}")
        print(f"✓ Resolved:  {stats['resolved']}")
        print(f"✓ Created:   {stats['created']}")
        
        if stats['relationships']:
            print(f"\n📝 Created relationships:")
            for rel in stats['relationships']:
                print(f"   {rel['from']} --[{rel['type']}]--> {rel['to']}")
    
    print("\n" + "=" * 70)
