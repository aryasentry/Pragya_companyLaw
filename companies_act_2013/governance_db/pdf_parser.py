"""PDF parsing with pypdf and OCR fallback"""
import os
from pathlib import Path
from typing import Optional, Dict
import pypdf
from ocr_utils import ocr_pdf

def extract_text_from_pdf(pdf_path: str, min_text_length: int = 100) -> Optional[str]:
    """
    Extract text from PDF using pypdf.
    
    Args:
        pdf_path: Path to PDF file
        min_text_length: Minimum text length to consider PDF parsable
        
    Returns:
        Extracted text or None if failed
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text_parts = []
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            full_text = "\n\n".join(text_parts).strip()
            
            # Check if extracted text is meaningful
            if len(full_text) >= min_text_length:
                return full_text
            else:
                return None
                
    except Exception as e:
        print(f"✗ Error parsing PDF {pdf_path}: {e}")
        return None

def parse_pdf_with_ocr_fallback(
    pdf_path: str, 
    ocr_output_dir: str = "ocr_temp",
    force_ocr: bool = False
) -> Optional[str]:
    """
    Parse PDF with pypdf, fall back to OCR if needed.
    
    Args:
        pdf_path: Path to PDF file
        ocr_output_dir: Directory for OCRed PDFs
        force_ocr: Force OCR even if text extraction works
        
    Returns:
        Extracted text or None if both methods failed
    """
    pdf_name = Path(pdf_path).name
    
    # Try pypdf first unless forced to OCR
    if not force_ocr:
        text = extract_text_from_pdf(pdf_path)
        if text:
            print(f"✓ Parsed (pypdf): {pdf_name}")
            return text
        else:
            print(f"⚠ Low/no text in {pdf_name}, trying OCR...")
    
    # Fall back to OCR
    ocred_path = ocr_pdf(pdf_path, ocr_output_dir)
    
    if ocred_path and os.path.exists(ocred_path):
        # Extract text from OCRed PDF
        text = extract_text_from_pdf(ocred_path)
        if text:
            print(f"✓ Parsed (OCR): {pdf_name}")
            return text
        else:
            print(f"✗ OCR failed to extract text from {pdf_name}")
            return None
    else:
        print(f"✗ OCR process failed for {pdf_name}")
        return None

def parse_text_file(file_path: str) -> Optional[str]:
    """
    Parse plain text file.
    
    Args:
        file_path: Path to text file
        
    Returns:
        File content or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            if text:
                print(f"✓ Parsed (text): {Path(file_path).name}")
                return text
            return None
    except Exception as e:
        print(f"✗ Error reading text file {file_path}: {e}")
        return None

def parse_html_file(file_path: str) -> Optional[str]:
    """
    Parse HTML file - basic text extraction.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        Extracted text or None if failed
    """
    try:
        from bs4 import BeautifulSoup
        
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            if text:
                print(f"✓ Parsed (html): {Path(file_path).name}")
                return text
            return None
            
    except ImportError:
        print("⚠ BeautifulSoup not installed, treating HTML as text")
        return parse_text_file(file_path)
    except Exception as e:
        print(f"✗ Error parsing HTML file {file_path}: {e}")
        return None

def parse_document(file_path: str, ocr_output_dir: str = "ocr_temp") -> Dict[str, Optional[str]]:
    """
    Parse any document (PDF, TXT, HTML).
    
    Args:
        file_path: Path to document
        ocr_output_dir: Directory for OCRed PDFs
        
    Returns:
        Dict with 'text' and 'parse_method' keys
    """
    ext = Path(file_path).suffix.lower()
    
    if ext == '.pdf':
        text = parse_pdf_with_ocr_fallback(file_path, ocr_output_dir)
        method = 'pdf_with_ocr'
    elif ext == '.txt':
        text = parse_text_file(file_path)
        method = 'text'
    elif ext in ['.html', '.htm']:
        text = parse_html_file(file_path)
        method = 'html'
    else:
        print(f"⚠ Unsupported file type: {ext}")
        return {'text': None, 'parse_method': None}
    
    return {'text': text, 'parse_method': method if text else None}

if __name__ == "__main__":
    # Test PDF parsing
    test_pdf = r"c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\raw\companies_act\section_001\circulars\General-Circular-No.-16-20131.pdf"
    
    if os.path.exists(test_pdf):
        result = parse_document(test_pdf)
        if result['text']:
            print(f"\nExtracted {len(result['text'])} characters using {result['parse_method']}")
            print(f"Preview: {result['text'][:200]}...")
        else:
            print("✗ Failed to extract text")
    else:
        print(f"Test file not found: {test_pdf}")
