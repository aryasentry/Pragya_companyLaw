"""
Companies Act 2013 PDF Parser
Extracts sections from PDF using chapter_mapping.json
Stores in rawNew/ folder structure with metadata
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import fitz  # PyMuPDF
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompaniesActPDFParser:
    """Parse Companies Act PDF and extract sections"""
    
    def __init__(self, pdf_path: str, mapping_file: str, output_dir: str = "rawNew"):
        """Initialize parser"""
        self.pdf_path = Path(pdf_path)
        self.mapping_file = Path(mapping_file)
        self.output_dir = Path(output_dir)
        
        # Create output structure
        self.companies_act_dir = self.output_dir / "companies_act_2013"
        self.non_binding_dir = self.output_dir / "non_binding"
        
        self._create_directory_structure()
        
        # Load chapter mapping
        logger.info(f"Loading chapter mapping from {self.mapping_file}")
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            self.chapter_mapping = json.load(f)
        
        # Open PDF
        logger.info(f"Opening PDF: {self.pdf_path}")
        self.doc = fitz.open(self.pdf_path)
        logger.info(f"PDF loaded: {len(self.doc)} pages")
        
        # Section metadata
        self.sections_metadata = []
        
    def _create_directory_structure(self):
        """Create rawNew folder structure"""
        logger.info("Creating directory structure...")
        
        # Companies Act sections
        self.companies_act_dir.mkdir(parents=True, exist_ok=True)
        
        # Non-binding materials
        (self.non_binding_dir / "textbooks").mkdir(parents=True, exist_ok=True)
        (self.non_binding_dir / "qa_guides").mkdir(parents=True, exist_ok=True)
        (self.non_binding_dir / "commentaries").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"  Created: {self.output_dir}")
    
    def extract_text_from_page(self, page_num: int) -> str:
        """Extract text from a specific page"""
        try:
            page = self.doc[page_num]
            return page.get_text()
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {e}")
            return ""
    
    def find_section_in_pdf(self, section_num: int, section_title: str) -> Optional[Tuple[int, int, str]]:
        """
        Find section text in PDF by searching for section number and title
        Returns: (start_page, end_page, text) or None
        
        Section format: "3. Formation of company.—(1)"
        """
        # Normalize title for matching (first few words)
        title_words = section_title.lower().split()[:4]  # First 4 words
        
        logger.info(f"Searching for Section {section_num}: {section_title}")
        
        # Search for section start (skip first 15 pages - index 0-14)
        start_page = None
        for page_num in range(15, len(self.doc)):
            page_text = self.extract_text_from_page(page_num)
            
            # Look for section pattern: "123. Title text.—"
            # The section number should appear at the start of a line or after newline
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                # Check if line starts with section number followed by period
                if line_stripped.startswith(f"{section_num}. "):
                    # Extract first part after number to check against title
                    # Format: "123. Some title text.—"
                    text_after_num = line_stripped[len(f"{section_num}. "):].lower()
                    
                    # Check if any of the first title words appear in this line
                    if any(word in text_after_num for word in title_words if len(word) > 3):
                        start_page = page_num
                        logger.info(f"  Found Section {section_num} starting at page {page_num + 1}")
                        break
            
            if start_page is not None:
                break
        
        if start_page is None:
            logger.warning(f"  Section {section_num} not found in PDF")
            return None
        
        # Find end page by looking for the next section in chapter_mapping
        next_section_info = self.get_next_section(section_num)
        end_page = len(self.doc) - 1  # Default to end of document
        
        if next_section_info:
            next_num = next_section_info['number']
            next_title_words = next_section_info['name'].lower().split()[:4]
            
            for page_num in range(start_page + 1, len(self.doc)):
                page_text = self.extract_text_from_page(page_num)
                lines = page_text.split('\n')
                
                for line in lines:
                    line_stripped = line.strip()
                    # Look for next section number at start of line
                    if line_stripped.startswith(f"{next_num}. "):
                        text_after_num = line_stripped[len(f"{next_num}. "):].lower()
                        # Verify it's the right section by checking title words
                        if any(word in text_after_num for word in next_title_words if len(word) > 3):
                            end_page = page_num - 1
                            logger.info(f"  Section {section_num} ends at page {end_page + 1} (next: Section {next_num})")
                            break
                
                if end_page != len(self.doc) - 1:
                    break
        
        if end_page == len(self.doc) - 1:
            logger.info(f"  Section {section_num} ends at page {end_page + 1} (end of document)")
        
        # Extract text from all pages
        section_text_parts = []
        for page_num in range(start_page, end_page + 1):
            page_text = self.extract_text_from_page(page_num)
            
            # Special handling for page 16 (index 15) - remove footnotes
            if page_num == 15:
                page_text = self.clean_page_16_footnotes(page_text)
            
            section_text_parts.append(page_text)
        
        section_text = '\n\n'.join(section_text_parts).strip()
        
        # Clean up the text
        section_text = self.clean_section_text(section_text, section_num, section_title)
        
        return start_page, end_page, section_text
    
    def clean_page_16_footnotes(self, text: str) -> str:
        """Clean footnotes specifically from page 16"""
        lines = text.split('\n')
        cleaned_lines = []
        in_footnote = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect footnote sections (start with *1., *2., etc. or dates like "12th September, 2013")
            if re.match(r'^\*\d+\.\s+\d{1,2}(st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)', line_stripped):
                in_footnote = True
                continue
            
            # Skip lines in footnote sections
            if in_footnote:
                # Check if still in footnote (contains notification references, dates, etc.)
                if any(marker in line_stripped for marker in ['notification No.', 'S.O.', 'Gazette of India', 'vide', 'dated', 'sec. 3', 'see Gazette']):
                    continue
                # Check if it's a continuation line (starts with date)
                if re.match(r'^\d{1,2}(st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)', line_stripped):
                    continue
                # Check if line starts with "ss." or "s." (section references in footnotes)
                if re.match(r'^s{1,2}\.\s+\d+', line_stripped):
                    continue
                # End of footnote section - look for actual content
                if len(line_stripped) > 50 and not any(marker in line_stripped for marker in ['notification', 'S.O.', 'Gazette']):
                    in_footnote = False
            
            if not in_footnote:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_section_text(self, text: str, section_num: int, section_title: str) -> str:
        """Clean extracted section text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove page headers/footers (common patterns)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Skip common header/footer patterns
            if re.match(r'^\d+$', line_stripped):  # Just page numbers
                continue
            if re.match(r'^Page \d+', line_stripped, re.I):
                continue
            if re.match(r'THE COMPANIES ACT', line_stripped, re.I) and len(line_stripped) < 50:
                continue
            if 'ACT NO. 18 OF 2013' in line_stripped:
                continue
            
            # Skip date headers like [29th August, 2013.]
            if re.match(r'^\[.*?(January|February|March|April|May|June|July|August|September|October|November|December).*?\]\.?$', line_stripped):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def save_section(self, section_num: int, section_title: str, text: str, start_page: int, end_page: int):
        """Save section text to appropriate folder"""
        # Create section directory
        section_dir = self.companies_act_dir / f"section_{section_num:03d}"
        act_dir = section_dir / "act"
        act_dir.mkdir(parents=True, exist_ok=True)
        
        # Also create other subdirs matching the desired structure
        for subdir in ["rules", "notifications", "circulars", "forms"]:
            (section_dir / subdir).mkdir(exist_ok=True)
        
        # Save text file
        txt_file = act_dir / f"section_{section_num:03d}_act.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.info(f"  Saved: {txt_file}")
        
        # Store metadata (no redundant paths)
        self.sections_metadata.append({
            "section_number": section_num,
            "section_title": section_title,
            "start_page": start_page + 1,  # Convert to 1-based
            "end_page": end_page + 1,      # Convert to 1-based
            "page_count": end_page - start_page + 1,
            "text_length": len(text)
        })
    
    def get_all_sections(self) -> List[Dict]:
        """Get all sections from chapter mapping"""
        all_sections = []
        
        for chapter_num, chapter_data in self.chapter_mapping.items():
            sections = chapter_data.get('sections', [])
            for section in sections:
                all_sections.append({
                    'chapter': chapter_num,
                    'chapter_name': chapter_data.get('name'),
                    'number': section.get('number'),
                    'name': section.get('name')
                })
        
        return all_sections
    
    def get_next_section(self, current_section_num: int) -> Optional[Dict]:
        """Get the next section info from chapter mapping"""
        all_sections = self.get_all_sections()
        
        for i, section in enumerate(all_sections):
            if section['number'] == current_section_num:
                if i + 1 < len(all_sections):
                    return all_sections[i + 1]
                break
        
        return None
    
    def parse_all_sections(self):
        """Parse all sections from PDF"""
        logger.info(f"\n{'#'*80}")
        logger.info("COMPANIES ACT 2013 PDF PARSER")
        logger.info(f"{'#'*80}\n")
        
        all_sections = self.get_all_sections()
        logger.info(f"Found {len(all_sections)} sections in chapter mapping")
        
        processed = 0
        failed = 0
        
        for section_info in all_sections:
            section_num = section_info['number']
            section_title = section_info['name']
            
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing Section {section_num}: {section_title}")
            logger.info(f"{'='*80}")
            
            # Find and extract section
            result = self.find_section_in_pdf(section_num, section_title)
            
            if result:
                start_page, end_page, text = result
                
                if len(text) > 100:  # Ensure we got meaningful text
                    self.save_section(section_num, section_title, text, start_page, end_page)
                    processed += 1
                else:
                    logger.warning(f"  Section {section_num}: Extracted text too short ({len(text)} chars)")
                    failed += 1
            else:
                logger.error(f"  Section {section_num}: Not found in PDF")
                failed += 1
        
        logger.info(f"\n{'#'*80}")
        logger.info("PARSING COMPLETE")
        logger.info(f"Processed: {processed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"{'#'*80}\n")
    
    def save_metadata(self):
        """Save sections metadata to JSON"""
        metadata_file = self.output_dir / "sections_metadata.json"
        
        metadata = {
            "pdf_source": str(self.pdf_path),
            "total_sections": len(self.sections_metadata),
            "total_pages": len(self.doc),
            "sections": self.sections_metadata
        }
        
        logger.info(f"\nSaving metadata to {metadata_file}")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Metadata saved: {metadata_file}")
        
        # Print summary
        logger.info(f"\nSummary:")
        logger.info(f"  Total sections: {len(self.sections_metadata)}")
        logger.info(f"  Total pages in PDF: {len(self.doc)}")
        
        if self.sections_metadata:
            total_text = sum(s['text_length'] for s in self.sections_metadata)
            logger.info(f"  Total text extracted: {total_text:,} characters")
    
    def close(self):
        """Close PDF document"""
        if hasattr(self, 'doc'):
            self.doc.close()


def main():
    """Main entry point"""
    # Configuration
    pdf_path = "c:/Users/kalid/OneDrive/Documents/RAG/companiesactpdf.pdf"
    mapping_file = "raw/chapter_mapping.json"
    output_dir = "rawNew"
    
    # Create parser
    parser = CompaniesActPDFParser(pdf_path, mapping_file, output_dir)
    
    try:
        # Parse all sections
        parser.parse_all_sections()
        
        # Save metadata
        parser.save_metadata()
        
    finally:
        # Close PDF
        parser.close()


if __name__ == "__main__":
    main()
