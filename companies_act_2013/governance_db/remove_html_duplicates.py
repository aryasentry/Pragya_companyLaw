"""
Remove duplicate HTML chunks from database (keep TXT versions)
"""
from db_config import get_db_connection

def check_html_txt_duplicates():
    """Check for HTML/TXT duplicates"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print("="*70)
        print("CHECKING HTML/TXT DUPLICATES")
        print("="*70)
        
        # Find sections with both HTML and TXT files
        cur.execute("""
            SELECT 
                ci.section,
                COUNT(CASE WHEN ci.chunk_id LIKE '%_html%' THEN 1 END) as html_count,
                COUNT(CASE WHEN ci.chunk_id LIKE '%_txt%' THEN 1 END) as txt_count
            FROM chunks_identity ci
            WHERE ci.chunk_role = 'parent'
            GROUP BY ci.section
            HAVING COUNT(CASE WHEN ci.chunk_id LIKE '%_html%' THEN 1 END) > 0
               AND COUNT(CASE WHEN ci.chunk_id LIKE '%_txt%' THEN 1 END) > 0
            ORDER BY ci.section
        """)
        
        duplicates = cur.fetchall()
        
        if duplicates:
            print(f"\nFound {len(duplicates)} sections with both HTML and TXT files:")
            total_html = sum(d['html_count'] for d in duplicates)
            total_txt = sum(d['txt_count'] for d in duplicates)
            
            for dup in duplicates[:10]:  # Show first 10
                print(f"  Section {dup['section']}: {dup['html_count']} HTML, {dup['txt_count']} TXT")
            
            if len(duplicates) > 10:
                print(f"  ... and {len(duplicates) - 10} more sections")
            
            print(f"\nTotal HTML chunks to remove: {total_html}")
            print(f"Total TXT chunks to keep: {total_txt}")
        else:
            print("\nNo duplicate HTML/TXT files found")
        
        # Count total HTML chunks
        cur.execute("""
            SELECT COUNT(*) as count
            FROM chunks_identity
            WHERE chunk_id LIKE '%_html%'
        """)
        html_total = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count
            FROM chunks_identity
            WHERE chunk_id LIKE '%_html%' AND chunk_role = 'parent'
        """)
        html_parents = cur.fetchone()['count']
        
        print(f"\n{'='*70}")
        print(f"Total HTML chunks in database: {html_total}")
        print(f"  - Parents: {html_parents}")
        print(f"  - Children: {html_total - html_parents}")
        
        cur.close()
        
        return html_total > 0

def remove_html_chunks():
    """Remove all HTML chunks and their children from database"""
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print("\n" + "="*70)
        print("REMOVING HTML CHUNKS")
        print("="*70)
        
        # Get list of HTML parent chunk IDs
        cur.execute("""
            SELECT chunk_id
            FROM chunks_identity
            WHERE chunk_id LIKE '%_html%' AND chunk_role = 'parent'
            ORDER BY chunk_id
        """)
        html_parents = [row['chunk_id'] for row in cur.fetchall()]
        
        if not html_parents:
            print("No HTML parent chunks found to remove")
            cur.close()
            return
        
        print(f"\nFound {len(html_parents)} HTML parent chunks to remove")
        print("Sample IDs:")
        for chunk_id in html_parents[:5]:
            print(f"  - {chunk_id}")
        
        # Count child chunks
        cur.execute("""
            SELECT COUNT(*) as count
            FROM chunks_identity
            WHERE parent_chunk_id IN (
                SELECT chunk_id FROM chunks_identity WHERE chunk_id LIKE '%_html%' AND chunk_role = 'parent'
            )
        """)
        child_count = cur.fetchone()['count']
        print(f"\nAssociated child chunks: {child_count}")
        
        # Total to delete
        total_to_delete = len(html_parents) + child_count
        print(f"Total chunks to delete: {total_to_delete}")
        
        # Ask for confirmation
        print("\n" + "!"*70)
        confirm = input("Type 'DELETE' to confirm removal of all HTML chunks: ")
        
        if confirm != 'DELETE':
            print("Cancelled - no chunks were removed")
            cur.close()
            return
        
        print("\nDeleting HTML chunks...")
        
        # Delete all chunks with HTML in their ID
        # This will cascade to all related tables due to ON DELETE CASCADE
        cur.execute("""
            DELETE FROM chunks_identity
            WHERE chunk_id LIKE '%_html%'
        """)
        
        deleted_count = cur.rowcount
        
        print(f"✓ Deleted {deleted_count} chunks")
        
        # Verify deletion
        cur.execute("""
            SELECT COUNT(*) as count
            FROM chunks_identity
            WHERE chunk_id LIKE '%_html%'
        """)
        remaining = cur.fetchone()['count']
        
        if remaining == 0:
            print("✓ All HTML chunks successfully removed")
        else:
            print(f"⚠ Warning: {remaining} HTML chunks still remain")
        
        # Show final stats
        print("\n" + "="*70)
        print("FINAL DATABASE STATS")
        print("="*70)
        
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'parent'")
        parents = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM chunks_identity WHERE chunk_role = 'child'")
        children = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM chunk_relationships")
        relationships = cur.fetchone()['count']
        
        print(f"Parent chunks:  {parents}")
        print(f"Child chunks:   {children}")
        print(f"Total chunks:   {parents + children}")
        print(f"Relationships:  {relationships}")
        
        # Show remaining chunk types
        print("\nRemaining chunk ID patterns:")
        cur.execute("""
            SELECT 
                CASE 
                    WHEN chunk_id LIKE '%_txt%' THEN 'TXT'
                    WHEN chunk_id LIKE '%_pdf%' THEN 'PDF'
                    ELSE 'OTHER'
                END as type,
                COUNT(*) as count
            FROM chunks_identity
            WHERE chunk_role = 'parent'
            GROUP BY type
            ORDER BY count DESC
        """)
        
        for row in cur.fetchall():
            print(f"  {row['type']:10} {row['count']:4} chunks")
        
        cur.close()

if __name__ == "__main__":
    # First check what will be removed
    has_html = check_html_txt_duplicates()
    
    if has_html:
        # Then remove if confirmed
        remove_html_chunks()
    else:
        print("\nNo HTML chunks to remove!")
