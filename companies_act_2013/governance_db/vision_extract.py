
import os
import json
import re
import base64
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_PDF_PAGES = int(os.getenv("VISION_MAX_PDF_PAGES", "3"))

EXTRACTION_INSTRUCTIONS = """Extract metadata for a legal/governance knowledge base.
Return ONLY a valid JSON object with these keys (use null for unknown):
- documentType: one of act, rule, regulation, order, notification, circular, sop, form, guideline, practice_note, commentary, textbook, qa_book, schedule, register, return, qa, other
- isBinding: true if binding to Companies Act, false otherwise
- section: Companies Act section number as 3-digit string (e.g. "042") if binding, else null
- title: document title
- dateIssued: ISO date YYYY-MM-DD
- effectiveDateFrom: ISO date or null
- effectiveDateTo: ISO date or null
- complianceArea: one of Corporate Governance, Financial Reporting, Secretarial Compliance, Board Meetings, Annual Filings, Share Capital, Directors, Auditors, Accounts, Dividends, Mergers & Acquisitions, Winding Up, NCLT Matters, CSR, Related Party Transactions, Loans & Investments, Registers & Records, Other
- documentLanguage: e.g. English, Hindi
- notificationNumber: e.g. G.S.R. 123(E) or null
- issuedBy: e.g. Ministry of Corporate Affairs or null
- copyrightStatus: copyrighted or public_domain or null
- copyrightAttribution: text or null

Return only the JSON object, no markdown or explanation."""

EXTRACTION_PROMPT = "Analyze this document (PDF or image) and " + EXTRACTION_INSTRUCTIONS

MAX_TEXT_CHARS = int(os.getenv("VISION_MAX_TEXT_CHARS", "30000"))


def _read_text_file(path: str) -> Optional[str]:
    """Read text file; failsafe: only first MAX_TEXT_CHARS to get context (avoids huge files)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS] + "\n\n[... truncated: only first portion used for extraction ...]"
            logger.info(f"Text file truncated to first {MAX_TEXT_CHARS} chars (failsafe)")
        return text.strip() or None
    except Exception as e:
        logger.warning(f"Could not read text file {path}: {e}")
        return None


def _pdf_to_images(pdf_path: str, max_pages: int = MAX_PDF_PAGES) -> list[bytes]:
    """Render PDF to images. Failsafe: only first max_pages (metadata usually at start)."""
    try:
        import fitz  
    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed; vision for PDF may be limited")
        return []
    out: list[bytes] = []
    doc = fitz.open(pdf_path)
    try:
        total_pages = len(doc)
        pages_to_use = min(total_pages, max_pages)
        if total_pages > max_pages:
            logger.info(f"PDF has {total_pages} pages; using only first {pages_to_use} for extraction (failsafe)")
        for i in range(pages_to_use):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=150)
            out.append(pix.tobytes("png"))
    finally:
        doc.close()
    return out


def _image_file_to_bytes(path: str) -> Optional[bytes]:
    """Read image file as bytes."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return f.read()


def _extract_with_ollama(file_path: str, model: str = "qwen2-vl:7b") -> Optional[dict[str, Any]]:
    """Call Ollama API (vision for PDF/image, text-only for .txt)."""
    import requests
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        doc_text = _read_text_file(file_path)
        if not doc_text:
            return None
        content = f"Analyze the following document text and {EXTRACTION_INSTRUCTIONS}\n\n--- Document text ---\n{doc_text}"
        payload = {"model": model, "messages": [{"role": "user", "content": content}], "stream": False}
        try:
            r = requests.post(f"{ollama_base}/api/chat", json=payload, timeout=85)
            r.raise_for_status()
            text = (r.json().get("message") or {}).get("content") or ""
            return _parse_extraction_json(text.strip())
        except Exception as e:
            logger.error(f"Ollama text extraction error: {e}")
            return None

    images_b64: list[str] = []
    if suffix == ".pdf":
        imgs = _pdf_to_images(file_path)
        if not imgs:
            return None
        for img in imgs:
            images_b64.append(base64.b64encode(img).decode("utf-8"))
    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        raw = _image_file_to_bytes(file_path)
        if raw:
            images_b64.append(base64.b64encode(raw).decode("utf-8"))
    else:
        return None
    if not images_b64:
        return None
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": EXTRACTION_PROMPT, "images": images_b64}],
        "stream": False,
    }
    try:
        r = requests.post(f"{ollama_base}/api/chat", json=payload, timeout=85)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message") or {}
        text = (msg.get("content") or "").strip()
        return _parse_extraction_json(text)
    except Exception as e:
        logger.error(f"Ollama vision error: {e}")
        return None


def _extract_with_gemini(file_path: str) -> Optional[dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        return None
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.error("google-genai not installed; run: pip install google-genai")
        return None
    client = genai.Client(api_key=api_key)
    model_name = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        doc_text = _read_text_file(file_path)
        if not doc_text:
            return None
        content = f"Analyze the following document text and {EXTRACTION_INSTRUCTIONS}\n\n--- Document text ---\n{doc_text}"
        try:
            response = client.models.generate_content(model=model_name, contents=content)
            return _parse_extraction_json((response.text or "").strip())
        except Exception as e:
            logger.error(f"Gemini text extraction error: {e}")
            return None

    images_data: list[bytes] = []
    if suffix == ".pdf":
        imgs = _pdf_to_images(file_path)
        if not imgs:
            return None
        images_data = imgs
    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        raw = _image_file_to_bytes(file_path)
        if raw:
            images_data = [raw]
    else:
        return None
    if not images_data:
        return None
    contents: list = [EXTRACTION_PROMPT]
    for img_bytes in images_data:
        contents.append(genai_types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    try:
        response = client.models.generate_content(model=model_name, contents=contents)
        text = (response.text or "").strip()
        return _parse_extraction_json(text)
    except Exception as e:
        logger.error(f"Gemini vision error: {e}")
        return None


def _parse_extraction_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        text = m.group(1)
    else:
        m2 = re.search(r"\{[\s\S]*\}", text)
        if m2:
            text = m2.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Could not parse extraction as JSON: %s", text[:200])
        return None


def extract_metadata_with_vision(
    file_path: str,
    model_option: str,
) -> Optional[dict[str, Any]]:

    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return None
    if model_option == "ollama_qwen3_vl":
        model = os.getenv("OLLAMA_VISION_MODEL", "llava:latest")
        return _extract_with_ollama(file_path, model=model)
    if model_option == "gemini_flash":
        return _extract_with_gemini(file_path)
    logger.error(f"Unknown vision model option: {model_option}")
    return None



def _fallback_text_metadata(path: str) -> dict[str, Any]:

    p = Path(path)
    title = p.stem
    first_line = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    first_line = stripped[:120]
                    break
    except Exception:
        pass
    if first_line and len(first_line) > 3:
        title = first_line
    return {
        "documentType": "other",
        "isBinding": False,
        "section": None,
        "title": title,
        "dateIssued": None,
        "effectiveDateFrom": None,
        "effectiveDateTo": None,
        "complianceArea": "Other",
        "documentLanguage": None,
        "notificationNumber": None,
        "issuedBy": None,
        "copyrightStatus": None,
        "copyrightAttribution": None,
    }


def normalize_extracted_to_form_data(raw: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "documentType": "documentType",
        "document_type": "documentType",
        "isBinding": "isBinding",
        "is_binding": "isBinding",
        "section": "section",
        "title": "title",
        "dateIssued": "dateIssued",
        "date_issued": "dateIssued",
        "effectiveDateFrom": "effectiveDateFrom",
        "effective_date_from": "effectiveDateFrom",
        "effectiveDateTo": "effectiveDateTo",
        "effective_date_to": "effectiveDateTo",
        "complianceArea": "complianceArea",
        "compliance_area": "complianceArea",
        "documentLanguage": "documentLanguage",
        "document_language": "documentLanguage",
        "notificationNumber": "notificationNumber",
        "notification_number": "notificationNumber",
        "issuedBy": "issuedBy",
        "issued_by": "issuedBy",
        "copyrightStatus": "copyrightStatus",
        "copyright_status": "copyrightStatus",
        "copyrightAttribution": "copyrightAttribution",
        "copyright_attribution": "copyrightAttribution",
    }
    out: dict[str, Any] = {}
    for k, v in raw.items():
        camel = mapping.get(k) or (k if k in mapping.values() else None)
        if camel and v is not None:
            out[camel] = v
    return out
