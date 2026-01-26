"""
Chunking Engine for Companies Act 2013
Processes scraped data and PDF extracts into structured chunks
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any


class ChunkingEngine:
    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size
        self.chunks = []
        
    def chunk_act_sections(self, act_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk the Companies Act sections.
        Expected format: [{"section": "1", "title": "...", "text": "...", "sub_sections": [...]}]
        """
        chunks = []
        
        for section_data in act_data:
            section_num = section_data.get("section", "Unknown")
            section_title = section_data.get("title", "")
            section_text = section_data.get("text", "")
            
            # Main section chunk
            if section_text:
                chunks.append({
                    "section": section_num,
                    "sub_section": None,
                    "title": section_title,
                    "text": section_text.strip(),
                    "citation": f"Companies Act, 2013 — Section {section_num}",
                    "document_type": "act",
                    "chapter": section_data.get("chapter"),
                    "part": section_data.get("part")
                })
            
            # Sub-sections
            for sub_section in section_data.get("sub_sections", []):
                sub_num = sub_section.get("number")
                sub_text = sub_section.get("text", "")
                
                if sub_text:
                    chunks.append({
                        "section": section_num,
                        "sub_section": sub_num,
                        "title": section_title,
                        "text": sub_text.strip(),
                        "citation": f"Companies Act, 2013 — Section {section_num}({sub_num})",
                        "document_type": "act",
                        "chapter": section_data.get("chapter"),
                        "part": section_data.get("part")
                    })
        
        return chunks
    
    def chunk_pdf_extracts(self, pdf_dir: Path) -> List[Dict[str, Any]]:
        """
        Process extracted PDF text files (forms, notifications, rules, circulars)
        """
        chunks = []
        
        if not pdf_dir.exists():
            print(f"PDF directory {pdf_dir} does not exist")
            return chunks
        
        # Process all JSON files in the PDF extracts directory
        for json_file in pdf_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    pdf_data = json.load(f)
                
                doc_type = self._classify_document(json_file.stem)
                
                # Extract text and metadata
                text = pdf_data.get("text", "")
                filename = pdf_data.get("filename", json_file.stem)
                
                # Determine section if mentioned
                section = self._extract_section_reference(text)
                
                # Chunk large documents
                if len(text) > self.max_chunk_size:
                    text_chunks = self._split_text(text, self.max_chunk_size)
                    for i, chunk_text in enumerate(text_chunks):
                        chunks.append({
                            "section": section,
                            "sub_section": None,
                            "title": filename,
                            "text": chunk_text.strip(),
                            "citation": f"{doc_type.capitalize()} {filename}",
                            "document_type": doc_type,
                            "chunk_index": i,
                            "source_file": str(json_file)
                        })
                else:
                    chunks.append({
                        "section": section,
                        "sub_section": None,
                        "title": filename,
                        "text": text.strip(),
                        "citation": f"{doc_type.capitalize()} {filename}",
                        "document_type": doc_type,
                        "source_file": str(json_file)
                    })
                    
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        
        return chunks
    
    def _classify_document(self, filename: str) -> str:
        """Classify document type based on filename"""
        filename_lower = filename.lower()
        
        if 'form' in filename_lower or 'inc-' in filename_lower:
            return 'form'
        elif 'notification' in filename_lower or 'gsr' in filename_lower:
            return 'notification'
        elif 'rule' in filename_lower:
            return 'rule'
        elif 'circular' in filename_lower:
            return 'circular'
        else:
            return 'pdf_document'
    
    def _extract_section_reference(self, text: str) -> str:
        """Extract section reference from text"""
        # Look for patterns like "Section 2", "Section 10", etc.
        match = re.search(r'Section\s+(\d+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _split_text(self, text: str, max_size: int) -> List[str]:
        """Split text into chunks at sentence boundaries"""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def save_chunks(self, chunks: List[Dict[str, Any]], output_file: Path):
        """Save chunks to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(chunks)} chunks to {output_file}")


def main():
    """Main execution"""
    engine = ChunkingEngine(max_chunk_size=1000)
    
    # Process Companies Act sections
    act_file = Path("companies_act_sections.json")
    if act_file.exists():
        print("Processing Companies Act sections...")
        with open(act_file, 'r', encoding='utf-8') as f:
            act_data = json.load(f)
        act_chunks = engine.chunk_act_sections(act_data)
        print(f"Created {len(act_chunks)} chunks from Act sections")
    else:
        print(f"Act data file {act_file} not found")
        act_chunks = []
    
    # Process PDF extracts
    pdf_dir = Path("pdf_extracts")
    if pdf_dir.exists():
        print("Processing PDF extracts...")
        pdf_chunks = engine.chunk_pdf_extracts(pdf_dir)
        print(f"Created {len(pdf_chunks)} chunks from PDF documents")
    else:
        print(f"PDF directory {pdf_dir} not found")
        pdf_chunks = []
    
    # Combine all chunks
    all_chunks = act_chunks + pdf_chunks
    
    # Save to output
    output_file = Path("chunks_final.json")
    engine.save_chunks(all_chunks, output_file)
    
    # Print statistics
    print("\n=== Chunking Statistics ===")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Act chunks: {len(act_chunks)}")
    print(f"PDF chunks: {len(pdf_chunks)}")
    
    doc_types = {}
    for chunk in all_chunks:
        dtype = chunk.get("document_type", "unknown")
        doc_types[dtype] = doc_types.get(dtype, 0) + 1
    
    print("\nBy document type:")
    for dtype, count in sorted(doc_types.items()):
        print(f"  {dtype}: {count}")


if __name__ == "__main__":
    main()
