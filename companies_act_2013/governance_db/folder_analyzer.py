"""Analyze folder structure and extract metadata"""
import os
import re
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class DocumentMetadata:
    """Metadata extracted from folder structure"""
    file_path: str
    section_number: Optional[str]
    document_type: str
    is_binding: bool
    binding_note: Optional[str]
    file_type: str  # pdf, txt, html
    
    @property
    def title(self) -> Optional[str]:
        """Generate title from file path"""
        return Path(self.file_path).stem
    
    @property
    def compliance_area(self) -> str:
        """Determine compliance area from document type"""
        compliance_map = {
            'act': 'Company Incorporation',
            'circular': 'Administrative Guidance',
            'notification': 'Regulatory Compliance',
            'order': 'Judicial/Administrative Orders',
            'rule': 'Procedural Rules',
            'schedule': 'Annexures & Schedules',
            'register': 'Company Records',
            'return': 'Company Filings',
            'form': 'Statutory Forms'
        }
        return compliance_map.get(self.document_type, 'General Compliance')
    
    def to_dict(self) -> Dict:
        return {
            'file_path': self.file_path,
            'section_number': self.section_number,
            'document_type': self.document_type,
            'is_binding': self.is_binding,
            'binding_note': self.binding_note,
            'file_type': self.file_type,
            'title': self.title,
            'compliance_area': self.compliance_area
        }

# Mapping folder names to document_type enum values
FOLDER_TO_DOCTYPE = {
    'act': 'act',
    'circulars': 'circular',
    'notifications': 'notification',
    'orders': 'order',
    'rules': 'rule',
    'schedule': 'schedule',
    'register': 'register',
    'return': 'return',
    'forms': 'form',
    'qa': 'qa',
    'textbooks': 'textbook'
}

def extract_section_number(path: str) -> Optional[str]:
    """
    Extract section number from path.
    
    Example: .../section_001/... -> '001'
    
    Args:
        path: File path
        
    Returns:
        Section number string or None
    """
    match = re.search(r'section_(\d+)', path)
    return match.group(1) if match else None

def get_document_type_from_path(path: str) -> str:
    """
    Determine document type from folder structure.
    
    Args:
        path: File path
        
    Returns:
        Document type (enum value)
    """
    path_parts = Path(path).parts
    
    # Check each folder in path against mapping
    for part in reversed(path_parts):
        doc_type = FOLDER_TO_DOCTYPE.get(part.lower())
        if doc_type:
            return doc_type
    
    return 'other'

def is_binding_document(document_type: str) -> tuple[bool, Optional[str]]:
    """
    Determine if document type is binding.
    
    Args:
        document_type: Document type enum value
        
    Returns:
        (is_binding, binding_note) tuple
    """
    # Based on governance_rules.py BINDING_RULES
    binding_types = {
        'act': (True, None),
        'rule': (True, None),
        'regulation': (True, None),
        'order': (True, None),
        'notification': (True, 'Conditionally binding - verify administrative issuance'),
        'schedule': (True, 'Binding as part of parent Act'),
        'circular': (False, 'Advisory unless superseded by binding law'),
        'guideline': (False, 'Best practice recommendation'),
        'form': (False, 'Template for compliance'),
        'register': (False, 'Record-keeping format'),
        'return': (False, 'Reporting template'),
        'qa': (False, 'Educational content'),
        'textbook': (False, 'Reference material')
    }
    
    return binding_types.get(document_type, (False, 'Binding status unclear'))

def analyze_file(file_path: str) -> DocumentMetadata:
    """
    Extract all metadata from file path.
    
    Args:
        file_path: Path to document file
        
    Returns:
        DocumentMetadata object
    """
    section_num = extract_section_number(file_path)
    doc_type = get_document_type_from_path(file_path)
    is_binding, binding_note = is_binding_document(doc_type)
    file_type = Path(file_path).suffix.lower().lstrip('.')
    
    return DocumentMetadata(
        file_path=file_path,
        section_number=section_num,
        document_type=doc_type,
        is_binding=is_binding,
        binding_note=binding_note,
        file_type=file_type
    )

def scan_raw_directory(raw_dir: str, skip_html: bool = True) -> List[DocumentMetadata]:
    """
    Scan entire raw directory and extract metadata for all files.
    
    Args:
        raw_dir: Root directory to scan
        skip_html: If True, skip HTML files (default: True)
        
    Returns:
        List of DocumentMetadata objects
    """
    documents = []
    
    # Supported file extensions (skip HTML by default to avoid duplicates)
    if skip_html:
        extensions = ['.pdf', '.txt']
    else:
        extensions = ['.pdf', '.txt', '.html', '.htm']
    
    for root, dirs, files in os.walk(raw_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                metadata = analyze_file(file_path)
                documents.append(metadata)
    
    return documents

def get_statistics(documents: List[DocumentMetadata]) -> Dict:
    """
    Get statistics about discovered documents.
    
    Args:
        documents: List of DocumentMetadata objects
        
    Returns:
        Statistics dictionary
    """
    stats = {
        'total_files': len(documents),
        'by_type': {},
        'by_section': {},
        'by_file_format': {},
        'binding_count': sum(1 for d in documents if d.is_binding)
    }
    
    for doc in documents:
        # Count by document type
        stats['by_type'][doc.document_type] = stats['by_type'].get(doc.document_type, 0) + 1
        
        # Count by section
        section = doc.section_number or 'no_section'
        stats['by_section'][section] = stats['by_section'].get(section, 0) + 1
        
        # Count by file format
        stats['by_file_format'][doc.file_type] = stats['by_file_format'].get(doc.file_type, 0) + 1
    
    return stats

if __name__ == "__main__":
    # Test on raw directory
    raw_dir = r"c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\raw"
    
    print("Scanning raw directory...")
    documents = scan_raw_directory(raw_dir)
    
    print(f"\n✓ Found {len(documents)} documents\n")
    
    # Show statistics
    stats = get_statistics(documents)
    
    print("Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Binding documents: {stats['binding_count']}")
    
    print("\nBy document type:")
    for doc_type, count in sorted(stats['by_type'].items()):
        print(f"  {doc_type}: {count}")
    
    print("\nBy file format:")
    for fmt, count in sorted(stats['by_file_format'].items()):
        print(f"  {fmt}: {count}")
    
    print(f"\nSections: {len([k for k in stats['by_section'].keys() if k != 'no_section'])}")
    
    # Show sample documents
    print("\nSample documents:")
    for doc in documents[:5]:
        print(f"  Section {doc.section_number or 'N/A'} | {doc.document_type} | {doc.file_type} | Binding: {doc.is_binding}")
