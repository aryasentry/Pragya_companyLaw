"""OCR utilities using Docker and jbarlow83/ocrmypdf-alpine"""
import os
import subprocess
import glob
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional

def ocr_pdf(input_path: str, output_dir: str, image_tag: str = "jbarlow83/ocrmypdf-alpine") -> Optional[str]:
    """
    OCR a single PDF via Docker.
    
    Args:
        input_path: Path to input PDF file
        output_dir: Directory to save OCRed PDF
        image_tag: Docker image to use for OCR
        
    Returns:
        Path to OCRed PDF or None if failed
    """
    input_file = Path(input_path)
    output_path = Path(output_dir) / input_file.with_suffix('.ocr.pdf').name
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{input_file.parent.absolute()}:/data",
        image_tag,
        "/data/" + input_file.name,
        "/data/" + output_path.name,
        "--skip-text",  # Skip if text exists
        "-j", "2"  # Threads per PDF; tune to CPU cores
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ OCRed: {input_file.name}")
        return str(output_path)
    except subprocess.CalledProcessError as e:
        print(f"✗ Error OCRing {input_path}: {e.stderr}")
        return None

def batch_ocr_pdfs(pdf_dir: str, output_dir: str = "ocred_pdfs", max_workers: int = 4) -> List[str]:
    """
    Batch OCR all PDFs in directory.
    
    Args:
        pdf_dir: Directory containing PDFs to OCR
        output_dir: Directory to save OCRed PDFs
        max_workers: Number of parallel OCR processes
        
    Returns:
        List of successfully OCRed PDF paths
    """
    pdf_paths = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    
    if not pdf_paths:
        print(f"No PDFs found in {pdf_dir}")
        return []
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing {len(pdf_paths)} PDFs with {max_workers} workers...")
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(
            lambda p: ocr_pdf(p, output_dir),
            pdf_paths
        ))
    
    success_paths = [p for p in results if p]
    print(f"\n✓ Successfully OCRed {len(success_paths)}/{len(pdf_paths)} PDFs")
    return success_paths

def check_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        subprocess.run(
            ["docker", "--version"], 
            check=True, 
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def pull_ocr_image(image_tag: str = "jbarlow83/ocrmypdf-alpine") -> bool:
    """Pull OCR Docker image if not present."""
    try:
        print(f"Checking for Docker image: {image_tag}")
        subprocess.run(
            ["docker", "pull", image_tag],
            check=True,
            capture_output=True
        )
        print(f"✓ Image {image_tag} ready")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to pull image: {e}")
        return False

if __name__ == "__main__":
    # Test OCR setup
    if not check_docker_available():
        print("✗ Docker is not available. Please install Docker Desktop.")
        exit(1)
    
    print("✓ Docker is available")
    
    # Pull OCR image
    if not pull_ocr_image():
        print("✗ Failed to pull OCR image")
        exit(1)
    
    print("\n✓ OCR utilities ready")
