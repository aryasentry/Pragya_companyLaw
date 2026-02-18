"""
Retrieve and display chunk relationships in final_chunks.json format
Shows bidirectional relationships with proper document linking
"""
import json
from typing import Dict, List, Optional
from db_config import get_db_connection

# Allowed relationship types (validation whitelist)
ALLOWED_RELATIONSHIPS = {
    "clarifies", "proceduralises", "implements",
    "amends", "supersedes", "part_of", "precedes"
}

def get_chunk_with_relationships(chunk_id: str) -> Optional[Dict]:
    """Get a chunk with all its relationships in final_chunks.json format"""
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Get chunk identity and content
        cur.execute("""
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
                cc.title,
                cc.compliance_area,
                cc.text,
                cc.summary,
                cc.citation
            FROM chunks_identity ci
            LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
            WHERE ci.chunk_id = %s
        """, (chunk_id,))
        
        chunk = cur.fetchone()
        if not chunk:
            return None
        
        # Get keywords
        cur.execute("""
            SELECT keyword
            FROM chunk_keywords
            WHERE chunk_id = %s
            ORDER BY keyword
        """, (chunk_id,))
        keywords = [row['keyword'] for row in cur.fetchall()]
        
        # Initialize relationships structure like final_chunks.json
        relationships = {
            # Forward relationships (writable)
            "clarifies": [],
            "proceduralises": [],
            "implements": [],
            "amends": [],
            "supersedes": [],
            
            # Reverse relationships (derived)
            "clarified_by": [],
            "proceduralised_by": [],
            "implemented_by": [],
            "amended_by": [],
            "superseded_by": [],
            
            # Hierarchical relationships
            "part_of": [],
            "has_parts": [],
            "precedes": [],
            "preceded_by": [],
            
            # Generic
            "applies_to": []
        }
        
        # Get forward relationships (FROM this chunk)
        cur.execute("""
            SELECT to_chunk_id, relationship
            FROM chunk_relationships
            WHERE from_chunk_id = %s
            ORDER BY relationship, to_chunk_id
        """, (chunk_id,))
        
        for row in cur.fetchall():
            rel_type = row['relationship']
            target = row['to_chunk_id']
            
            # Validate relationship type against whitelist
            if rel_type not in ALLOWED_RELATIONSHIPS:
                print(f"⚠️  Warning: Unknown relationship type '{rel_type}' for {chunk_id}")
                continue
            
            if rel_type == 'clarifies':
                relationships['clarifies'].append(target)
            elif rel_type == 'proceduralises':
                relationships['proceduralises'].append(target)
            elif rel_type == 'implements':
                relationships['implements'].append(target)
            elif rel_type == 'amends':
                relationships['amends'].append(target)
            elif rel_type == 'supersedes':
                relationships['supersedes'].append(target)
            elif rel_type == 'part_of':
                relationships['part_of'].append(target)
            elif rel_type == 'precedes':
                relationships['precedes'].append(target)
        
        # Get reverse relationships (TO this chunk)
        cur.execute("""
            SELECT from_chunk_id, relationship
            FROM chunk_relationships
            WHERE to_chunk_id = %s
            ORDER BY relationship, from_chunk_id
        """, (chunk_id,))
        
        for row in cur.fetchall():
            rel_type = row['relationship']
            source = row['from_chunk_id']
            
            # Validate relationship type against whitelist
            if rel_type not in ALLOWED_RELATIONSHIPS:
                print(f"⚠️  Warning: Unknown relationship type '{rel_type}' pointing to {chunk_id}")
                continue
            
            # Map forward relationships to their reverse counterparts
            if rel_type == 'clarifies':
                relationships['clarified_by'].append(source)
            elif rel_type == 'proceduralises':
                relationships['proceduralised_by'].append(source)
            elif rel_type == 'implements':
                relationships['implemented_by'].append(source)
            elif rel_type == 'amends':
                relationships['amended_by'].append(source)
            elif rel_type == 'supersedes':
                relationships['superseded_by'].append(source)
            elif rel_type == 'part_of':
                relationships['has_parts'].append(source)
            elif rel_type == 'precedes':
                relationships['preceded_by'].append(source)
        
        # Build response in final_chunks.json format
        result = {
            "chunk_id": chunk['chunk_id'],
            "document_type": chunk['document_type'],
            "authority_level": chunk['authority_level'],
            "act": chunk['act'],  # Legal anchor (MANDATORY for non-Acts)
            "section": chunk['section'],  # Never infer from chunk_id - use DB only
            "sub_section": chunk['sub_section'],
            "title": chunk['title'],
            "compliance_area": chunk['compliance_area'],
            "text": chunk['text'],
            "summary": chunk['summary'],
            "keywords": keywords,
            "relationships": relationships,
            "citation": chunk['citation']
        }
        
        cur.close()
        return result

def get_related_chunks_for_retrieval(chunk_id: str) -> Dict:
    """
    Get all related chunks that should be considered during retrieval
    This is what the LLM needs to check for citations
    """
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Get the main chunk
        main_chunk = get_chunk_with_relationships(chunk_id)
        if not main_chunk:
            return {"error": "Chunk not found"}
        
        # Collect all related chunk IDs
        related_ids = set()
        rels = main_chunk['relationships']
        
        # Add all forward relationships
        for rel_list in [rels['clarifies'], rels['proceduralises'], rels['implements'], 
                        rels['amends'], rels['supersedes'], rels['part_of']]:
            related_ids.update(rel_list)
        
        # Add all reverse relationships
        for rel_list in [rels['clarified_by'], rels['proceduralised_by'], rels['implemented_by'],
                        rels['amended_by'], rels['superseded_by'], rels['has_parts']]:
            related_ids.update(rel_list)
        
        # Fetch all related chunks
        related_chunks = []
        for rel_id in related_ids:
            chunk = get_chunk_with_relationships(rel_id)
            if chunk:
                related_chunks.append(chunk)
        
        return {
            "main_chunk": main_chunk,
            "related_chunks": related_chunks,
            "total_related": len(related_chunks),
            "relationship_summary": {
                "clarifies": len(rels['clarifies']),
                "clarified_by": len(rels['clarified_by']),
                "implements": len(rels['implements']),
                "implemented_by": len(rels['implemented_by']),
                "amends": len(rels['amends']),
                "amended_by": len(rels['amended_by']),
                "supersedes": len(rels['supersedes']),
                "superseded_by": len(rels['superseded_by']),
                "proceduralises": len(rels['proceduralises']),
                "proceduralised_by": len(rels['proceduralised_by'])
            }
        }

def search_chunks_with_relationships(query: str = None, limit: int = 5) -> List[Dict]:
    """Search for chunks and return them with relationships"""
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        if query:
            # Search by text content or chunk_id pattern
            cur.execute("""
                SELECT ci.chunk_id
                FROM chunks_identity ci
                LEFT JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                WHERE ci.chunk_role = 'parent'
                AND (ci.chunk_id LIKE %s OR cc.text ILIKE %s)
                ORDER BY ci.chunk_id
                LIMIT %s
            """, (f'%{query}%', f'%{query}%', limit))
        else:
            # Get sample parent chunks
            cur.execute("""
                SELECT chunk_id
                FROM chunks_identity
                WHERE chunk_role = 'parent'
                ORDER BY chunk_id
                LIMIT %s
            """, (limit,))
        
        chunk_ids = [row['chunk_id'] for row in cur.fetchall()]
        cur.close()
        
        results = []
        for chunk_id in chunk_ids:
            chunk = get_chunk_with_relationships(chunk_id)
            if chunk:
                results.append(chunk)
        
        return results

def validate_relationship_rules(chunk: Dict) -> List[str]:
    """Validate chunk against relationship rules"""
    errors = []
    
    # Rule 1: Child chunks MUST have empty relationships
    if chunk.get('chunk_id', '').endswith(('_c1', '_c2', '_c3', '_c4', '_c5', '_c6', '_c7', '_c8', '_c9')):
        rels = chunk.get('relationships', {})
        for key, val in rels.items():
            if val and key not in ['part_of', 'precedes', 'preceded_by']:  # Allow hierarchical only
                errors.append(f"Child chunk has non-empty {key} relationship")
    
    # Rule 2: Document-type enforcement
    doc_type = chunk.get('document_type')
    rels = chunk.get('relationships', {})
    
    if doc_type == 'act':
        # Acts should only have reverse relationships
        if rels['clarifies'] or rels['proceduralises'] or rels['implements']:
            errors.append("Act chunks should not have forward clarifies/proceduralises/implements")
    
    elif doc_type == 'rule':
        # Rules can implement and proceduralise
        if rels['clarifies'] or rels['amends']:
            errors.append("Rule chunks should not clarify or amend")
    
    elif doc_type == 'circular':
        # Circulars can clarify and supersede
        if rels['implements'] or rels['proceduralises']:
            errors.append("Circular chunks should not implement or proceduralise")
        if chunk.get('binding'):
            errors.append("Circular must have binding=false")
    
    elif doc_type == 'notification':
        # Notifications can implement and supersede
        if rels['clarifies'] or rels['proceduralises']:
            errors.append("Notification chunks should not clarify or proceduralise")
    
    elif doc_type in ['sop', 'form']:
        # SOPs/Forms can only proceduralise
        if rels['clarifies'] or rels['implements'] or rels['amends']:
            errors.append(f"{doc_type} chunks should only proceduralise")
    
    elif doc_type == 'commentary':
        # Commentary should have no relationships
        if any(rels.values()):
            errors.append("Commentary chunks should have no relationships")
    
    # Rule 3: Act anchor (MANDATORY for non-Act documents)
    if doc_type != 'act':
        act = chunk.get('act')
        section = chunk.get('section')
        if not act or not section:
            errors.append(f"Non-Act document missing act anchor: act={act}, section={section}")
    
    return errors

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Retrieve chunk relationships")
    parser.add_argument('--chunk', type=str, help='Specific chunk ID to retrieve')
    parser.add_argument('--search', type=str, help='Search query')
    parser.add_argument('--limit', type=int, default=5, help='Number of results')
    parser.add_argument('--with-related', action='store_true', help='Include all related chunks')
    parser.add_argument('--validate', action='store_true', help='Validate relationship rules')
    parser.add_argument('--output', type=str, help='Save to JSON file')
    
    args = parser.parse_args()
    
    if args.chunk:
        # Get specific chunk
        if args.with_related:
            result = get_related_chunks_for_retrieval(args.chunk)
        else:
            result = get_chunk_with_relationships(args.chunk)
        
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if args.validate:
                if args.with_related:
                    errors = validate_relationship_rules(result['main_chunk'])
                else:
                    errors = validate_relationship_rules(result)
                
                if errors:
                    print("\n⚠️ VALIDATION ERRORS:")
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print("\n✅ All relationship rules validated")
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"\n✅ Saved to {args.output}")
        else:
            print(f"❌ Chunk not found: {args.chunk}")
    
    else:
        # Search or list chunks
        results = search_chunks_with_relationships(args.search, args.limit)
        
        print(f"\n{'='*70}")
        print(f"FOUND {len(results)} CHUNKS")
        print(f"{'='*70}\n")
        
        for chunk in results:
            print(f"📄 {chunk['chunk_id']}")
            print(f"   Type: {chunk['document_type']} | Section: {chunk['section']}")
            
            rels = chunk['relationships']
            rel_count = sum([
                len(rels['clarifies']), len(rels['clarified_by']),
                len(rels['implements']), len(rels['implemented_by']),
                len(rels['amends']), len(rels['amended_by']),
                len(rels['supersedes']), len(rels['superseded_by']),
                len(rels['proceduralises']), len(rels['proceduralised_by'])
            ])
            
            if rel_count > 0:
                print(f"   Relationships: {rel_count}")
                if rels['clarifies']:
                    print(f"     - Clarifies: {rels['clarifies']}")
                if rels['clarified_by']:
                    print(f"     - Clarified by: {rels['clarified_by']}")
                if rels['implements']:
                    print(f"     - Implements: {rels['implements']}")
                if rels['implemented_by']:
                    print(f"     - Implemented by: {rels['implemented_by']}")
            else:
                print(f"   Relationships: None")
            
            if args.validate:
                errors = validate_relationship_rules(chunk)
                if errors:
                    print(f"   ⚠️ Validation errors: {len(errors)}")
            
            print()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(results)} chunks to {args.output}")
