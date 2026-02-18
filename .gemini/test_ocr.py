"""
Test OCR functionality
"""
import sys
sys.path.insert(0, r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db')

from ocr_utils import check_docker_available, pull_ocr_image

print("=" * 70)
print("OCR SYSTEM CHECK")
print("=" * 70)

# Check Docker
print("\n1. Checking Docker...")
if check_docker_available():
    print("  ✓ Docker is installed and running")
else:
    print("  ✗ Docker is not available")
    print("  → Please install Docker Desktop from:")
    print("     https://www.docker.com/products/docker-desktop")
    sys.exit(1)

# Check OCR image
print("\n2. Checking OCR Docker image...")
if pull_ocr_image():
    print("  ✓ OCR image is ready (jbarlow83/ocrmypdf-alpine)")
else:
    print("  ✗ Failed to pull OCR image")
    print("  → Try manually: docker pull jbarlow83/ocrmypdf-alpine")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ OCR SYSTEM IS READY!")
print("=" * 70)
print("\nScanned PDFs will be automatically OCRed during ingestion.")
