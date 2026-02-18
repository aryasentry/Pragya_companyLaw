import os
import subprocess
import glob
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional

def ocr_pdf(input_path: str, output_dir: str, image_tag: str = "jbarlow83/ocrmypdf-alpine") -> Optional[str]:
    """
    OCR a PDF using Docker and ocrmypdf
    
    Args:
        input_path: Path to input PDF
        output_dir: Directory for OCR output
        image_tag: Docker image to use
    
    Returns:
        Path to OCRed PDF or None if failed
    """
    input_file = Path(input_path)
    output_path = Path(output_dir) / input_file.with_suffix('.ocr.pdf').name
    
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{input_file.parent.absolute()}:/data",
        image_tag,
        "/data/" + input_file.name,
        "/data/" + output_path.name,
        "--skip-text",  # Skip existing text, only OCR images
        "-j", "2"  # Use 2 parallel jobs
    ]
    
    try:
        print(f"🔍 OCRing: {input_file.name}...")
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        print(f"✓ OCRed: {input_file.name}")
        return str(output_path)
    except subprocess.TimeoutExpired:
        print(f"✗ OCR timeout for {input_path} (exceeded 5 minutes)")
        return None
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        print(f"✗ Error OCRing {input_path}:")
        print(f"  {error_msg}")
        return None
    except FileNotFoundError:
        print(f"✗ Docker not found. Please install Docker Desktop.")
        print(f"  Download from: https://www.docker.com/products/docker-desktop")
        return None
    except Exception as e:
        print(f"✗ Unexpected error OCRing {input_path}: {e}")
        return None

def batch_ocr_pdfs(pdf_dir: str, output_dir: str = "ocred_pdfs", max_workers: int = 4) -> List[str]:
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
    print(f"\n Successfully OCRed {len(success_paths)}/{len(pdf_paths)} PDFs")
    return success_paths

def check_docker_available() -> bool:
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
    try:
        print(f"Checking for Docker image: {image_tag}")
        subprocess.run(
            ["docker", "pull", image_tag],
            check=True,
            capture_output=True
        )
        print(f" Image {image_tag} ready")
        return True
    except subprocess.CalledProcessError as e:
        print(f" Failed to pull image: {e}")
        return False

if __name__ == "__main__":

    if not check_docker_available():
        print(" Docker is not available. Please install Docker Desktop.")
        exit(1)
    
    print(" Docker is available")
    
    if not pull_ocr_image():
        print(" Failed to pull OCR image")
        exit(1)
    
    print("\n OCR utilities ready")
