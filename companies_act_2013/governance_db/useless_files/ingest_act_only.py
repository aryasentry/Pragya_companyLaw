"""
Ingest ONLY Companies Act text files (section_XXX_act.txt)
No PDFs, circulars, notifications, or other supporting documents.

This script temporarily moves non-act files and runs unified ingestion.
"""

import os
import shutil
from pathlib import Path
from unified_ingest_full import unified_batch_ingest

def setup_act_only_environment():
    """
    Move non-act files to temporary location so unified_ingest_full.py
    will only scan and process act text files
    """
    base_path = Path(__file__).parent.parent / "raw" / "companies_act"
    temp_storage = Path(__file__).parent.parent / "temp_non_act_files"
    
    # Create temp storage
    temp_storage.mkdir(exist_ok=True)
    
    moved_count = 0
    
    # For each section, move non-act subdirectories
    for section_dir in sorted(base_path.glob("section_*")):
        section_num = section_dir.name.split("_")[1]
        
        # Subdirectories to move (everything except 'act')
        subdirs_to_move = ['circulars', 'notifications', 'orders', 'register', 
                          'return', 'rules', 'schedule']
        
        for subdir_name in subdirs_to_move:
            subdir = section_dir / subdir_name
            if subdir.exists() and subdir.is_dir():
                dest = temp_storage / f"section_{section_num}" / subdir_name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(subdir), str(dest))
                moved_count += 1
        
        # Also move HTML files from act directory
        act_dir = section_dir / "act"
        if act_dir.exists():
            for html_file in act_dir.glob("*.html"):
                dest = temp_storage / f"section_{section_num}" / "act" / html_file.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(html_file), str(dest))
                moved_count += 1
    
    print(f"✅ Moved {moved_count} non-act files/directories to temp storage")
    return temp_storage

def restore_non_act_files(temp_storage):
    """Restore non-act files back to their original locations"""
    base_path = Path(__file__).parent.parent / "raw" / "companies_act"
    restored_count = 0
    
    if temp_storage.exists():
        for section_dir in temp_storage.glob("section_*"):
            section_num = section_dir.name.split("_")[1]
            dest_section = base_path / f"section_{section_num}"
            
            # Move subdirectories back
            for subdir in section_dir.glob("*"):
                dest = dest_section / subdir.name
                shutil.move(str(subdir), str(dest))
                restored_count += 1
        
        # Clean up temp directory
        shutil.rmtree(temp_storage)
        print(f"✅ Restored {restored_count} non-act files/directories")

def main():
    """Process only act text files"""
    print("=" * 70)
    print("INGESTING COMPANIES ACT TEXT FILES ONLY")
    print("=" * 70)
    print()
    
    temp_storage = None
    
    try:
        # Move non-act files temporarily
        print("📦 Preparing environment...")
        temp_storage = setup_act_only_environment()
        print()
        
        # Run unified ingestion (will only find act files now)
        sections = [f"{i:03d}" for i in range(1, 44)]  # 001 to 043
        unified_batch_ingest(
            sections=sections,
            max_workers=4,
            verification_interval=5,
            skip_html=True,
            generate_summaries=True
        )
        
    finally:
        # Always restore files
        if temp_storage:
            print("\n📦 Restoring original directory structure...")
            restore_non_act_files(temp_storage)

if __name__ == "__main__":
    main()
