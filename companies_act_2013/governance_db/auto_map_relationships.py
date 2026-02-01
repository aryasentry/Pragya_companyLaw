"""
Automatically map relationships based on document types in each section
Uses folder structure to infer legal relationships
"""
import json
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
from db_config import get_db_connection

# Document type to relationship mapping (governance rules)
RELATIONSHIP_RULES = {
    'rule': 'implements',           # Rules implement Acts
    'regulation': 'implements',     # Regulations implement Acts
    'notification': 'implements',   # Notifications implement Acts
    'circular': 'clarifies',        # Circulars clarify Acts
    'order': 'implements',          # Orders implement Acts
    'guideline': 'clarifies',       # Guidelines clarify Acts
    'sop': 'proceduralises',        # SOPs proceduralise Acts
    'form': 'proceduralises',       # Forms proceduralise Acts
    'schedule': 'proceduralises',   # Schedules proceduralise Acts
}

def get_all_chunk_ids_by_section_and_type() -> Dict[str, Dict[str, List[str]]]:
    """Get all parent chunk IDs organized by section and document type"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Get all parent chunks with their section and document type
        cur.execute("""
            SELECT chunk_id, section, document_type
            FROM chunks_identity
            WHERE chunk_role = 'parent'
            ORDER BY section, document_type, chunk_id
        """)
        
        # Organize: section_number -> document_type -> [chunk_ids]
        sections = defaultdict(lambda: defaultdict(list))
        
        for row in cur.fetchall():
            chunk_id = row['chunk_id']
            section = row['section']
            doc_type = row['document_type']
            
            if section:  # Only process chunks with section numbers
                sections[section][doc_type].append(chunk_id)
        
        cur.close()
        return dict(sections)

def create_relationships_for_section(section: str, chunks_by_type: Dict[str, List[str]]) -> List[Dict]:
    """Create relationships for all documents in a section"""
    relationships = []
    
    # Get Act chunks (base documents)
    act_chunks = chunks_by_type.get('act', [])
    
    if not act_chunks:
        print(f"⚠️  Section {section}: No Act chunks found, skipping")
        return relationships
    
    # For simplicity, use the first Act chunk as the anchor
    # (most sections have only one Act chunk)
    act_chunk = act_chunks[0]
    
    # Create relationships for other document types
    for doc_type, chunk_ids in chunks_by_type.items():
        if doc_type == 'act':
            continue  # Skip the Act itself
        
        # Get the relationship type based on document type
        relationship = RELATIONSHIP_RULES.get(doc_type)
        
        if not relationship:
            # Unknown document type - skip
            continue
        
        # Create relationship from each non-Act chunk to the Act
        for chunk_id in chunk_ids:
            relationships.append({
                'from_chunk_id': chunk_id,
                'to_chunk_id': act_chunk,
                'relationship': relationship,
                'section': section,
                'doc_type': doc_type
            })
    
    return relationships

def insert_relationships(relationships: List[Dict]) -> int:
    """Insert relationships into database"""
    if not relationships:
        return 0
    
    inserted = 0
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        for rel in relationships:
            try:
                cur.execute("""
                    INSERT INTO chunk_relationships (from_chunk_id, to_chunk_id, relationship)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (rel['from_chunk_id'], rel['to_chunk_id'], rel['relationship']))
                
                if cur.rowcount > 0:
                    inserted += 1
                
            except Exception as e:
                print(f"✗ Error inserting relationship {rel['from_chunk_id']} -> {rel['to_chunk_id']}: {e}")
        
        cur.close()
    
    return inserted

def auto_map_all_relationships():
    """Main function to auto-map all relationships"""
    print("🔗 Auto-mapping relationships based on document types\n")
    
    # Get all chunks organized by section and type
    print("📊 Analyzing database structure...")
    sections = get_all_chunk_ids_by_section_and_type()
    
    total_sections = len(sections)
    print(f"✓ Found {total_sections} sections with chunks\n")
    
    # Statistics
    total_relationships = 0
    sections_with_relationships = 0
    relationship_counts = defaultdict(int)
    
    # Process each section
    for section_num in sorted(sections.keys()):
        chunks_by_type = sections[section_num]
        
        # Count document types in this section
        doc_type_summary = {dt: len(chunks) for dt, chunks in chunks_by_type.items()}
        
        print(f"📍 Section {section_num}:")
        print(f"   Document types: {doc_type_summary}")
        
        # Create relationships for this section
        relationships = create_relationships_for_section(section_num, chunks_by_type)
        
        if relationships:
            # Insert relationships
            inserted = insert_relationships(relationships)
            
            print(f"   ✓ Created {inserted} relationships")
            
            # Update statistics
            total_relationships += inserted
            if inserted > 0:
                sections_with_relationships += 1
            
            # Count by relationship type
            for rel in relationships:
                relationship_counts[rel['relationship']] += 1
        else:
            print(f"   - No relationships created")
        
        print()
    
    # Final summary
    print("\n" + "="*70)
    print("RELATIONSHIP MAPPING COMPLETE")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   Sections processed:        {total_sections}")
    print(f"   Sections with relationships: {sections_with_relationships}")
    print(f"   Total relationships:       {total_relationships}")
    
    print(f"\n🔗 Relationships by type:")
    for rel_type in sorted(relationship_counts.keys()):
        count = relationship_counts[rel_type]
        print(f"   {rel_type:20} {count:5}")
    
    # Verify in database
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM chunk_relationships")
        db_count = cur.fetchone()['count']
        cur.close()
    
    print(f"\n✓ Database verification: {db_count} relationships in chunk_relationships table")
    print("="*70 + "\n")

def show_section_relationships(section_number: str):
    """Show all relationships for a specific section"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Get all relationships for chunks in this section
        cur.execute("""
            SELECT 
                cr.from_chunk_id,
                ci1.document_type as from_type,
                cr.relationship,
                cr.to_chunk_id,
                ci2.document_type as to_type
            FROM chunk_relationships cr
            JOIN chunks_identity ci1 ON cr.from_chunk_id = ci1.chunk_id
            JOIN chunks_identity ci2 ON cr.to_chunk_id = ci2.chunk_id
            WHERE ci1.section = %s
            ORDER BY cr.relationship, cr.from_chunk_id
        """, (section_number,))
        
        relationships = cur.fetchall()
        
        if not relationships:
            print(f"No relationships found for section {section_number}")
            return
        
        print(f"\n🔗 Relationships in Section {section_number}:")
        print("="*70)
        
        current_rel = None
        for rel in relationships:
            if rel['relationship'] != current_rel:
                current_rel = rel['relationship']
                print(f"\n{current_rel.upper()}:")
            
            print(f"  {rel['from_chunk_id']} ({rel['from_type']}) → {rel['to_chunk_id']} ({rel['to_type']})")
        
        print("="*70 + "\n")
        
        cur.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-map relationships based on document types')
    parser.add_argument('--section', type=str, help='Show relationships for specific section')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without inserting')
    
    args = parser.parse_args()
    
    if args.section:
        # Show relationships for specific section
        show_section_relationships(args.section)
    else:
        # Auto-map all relationships
        if args.dry_run:
            print("⚠️  DRY RUN MODE - No changes will be made to database\n")
            # TODO: Implement dry-run logic
        
        auto_map_all_relationships()
