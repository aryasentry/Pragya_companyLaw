import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import logging
from langchain_ollama import OllamaLLM
import fitz  

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COMPLIANCE_AREAS = [
    "Company Incorporation", "Corporate Governance", "Share Capital & Debentures",
    "Prospectus & Capital Raising", "Board Meetings & Resolutions", "Accounts & Audit",
    "Deposits", "Directors & KMP", "Related Party Transactions",
    "Corporate Social Responsibility", "Mergers & Amalgamations", "Winding Up & Dissolution",
    "NCLT Proceedings", "Inspection & Investigation", "Producer Companies", "Nidhis",
    "Compromises & Arrangements", "Foreign Companies", "Government Companies",
    "Tribunal & Appellate", "Penalties & Prosecution", "General Provisions"
]

AUTHORITY_LEVELS = {
    "act": "Statutory", "rules": "Sub-statutory", "notifications": "Sub-statutory",
    "orders": "Sub-statutory", "circulars": "Guidance", "register": "Procedural",
    "return": "Procedural", "schedule": "Statutory"
}


class GovernanceChunkingEngine:
    
    def __init__(self, raw_dir: str = "raw", chunks_file: str = "chunks/chunks_final.json"):
        self.raw_dir = Path(raw_dir)
        self.chunks_file = Path(chunks_file)
        self.chunks_file.parent.mkdir(exist_ok=True, parents=True)
        
        self.existing_chunks = []
        self.existing_chunk_ids = set()
        
        if self.chunks_file.exists():
            logger.info(f"Loading existing chunks from {self.chunks_file}")
            with open(self.chunks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.existing_chunks = data.get('chunks', [])
                self.existing_chunk_ids = {c['chunk_id'] for c in self.existing_chunks}
            logger.info(f"  {len(self.existing_chunks)} existing chunks (WILL NOT MODIFY)")
        
        self.new_chunks = []
        
        logger.info("Initializing LLM (qwen2.5:1.5b)...")
        self.llm = OllamaLLM(model="qwen2.5:1.5b", base_url="http://localhost:11434", temperature=0.3)
        self.sections_processed = set()
        
    def extract_pdf_text(self, pdf_path: Path) -> str:
        try:
            text_parts = []
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            return '\n\n'.join(text_parts).strip()
        except Exception as e:
            logger.error(f"Error extracting {pdf_path}: {e}")
            return ""
    
    def generate_summary(self, text: str, title: str) -> str:
        """LLM: 2-sentence summary"""
        if not text.strip():
            return ""
        
        text_preview = text[:3000] if len(text) > 3000 else text
        prompt = f"""Generate a concise 2-sentence summary.

Title: {title}
Text: {text_preview}

Summary:"""
        
        try:
            summary = self.llm.invoke(prompt).strip()
            sentences = summary.split('.')[:2]
            return '. '.join(s.strip() for s in sentences if s.strip()) + '.'
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return ""
    
    def extract_keywords(self, text: str, title: str) -> List[str]:
        if not text.strip():
            return []
        
        text_preview = text[:2000] if len(text) > 2000 else text
        prompt = f"""Extract 5-7 specific legal keywords (NOT generic terms).

Title: {title}
Text: {text_preview}

Keywords (comma-separated):"""
        
        try:
            keywords_str = self.llm.invoke(prompt).strip()
            keywords = [k.strip() for k in keywords_str.split(',')]
            return [k for k in keywords if k and len(k) > 3][:7]
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    def determine_compliance_area(self, title: str, text: str, section_num: int) -> str:
        
        if 1 <= section_num <= 2:
            return "General Provisions"
        elif 3 <= section_num <= 22:
            return "Company Incorporation"
        elif 23 <= section_num <= 42:
            return "Prospectus & Capital Raising"
        elif 43 <= section_num <= 72:
            return "Share Capital & Debentures"
        
        text_preview = text[:1500] if len(text) > 1500 else text
        prompt = f"""Choose ONE compliance area from the list.

Title: {title}
Text: {text_preview}

Areas: {', '.join(COMPLIANCE_AREAS)}

If uncertain, return "General Provisions".
Compliance Area:"""
        
        try:
            area = self.llm.invoke(prompt).strip()
            for valid_area in COMPLIANCE_AREAS:
                if valid_area.lower() in area.lower():
                    return valid_area
            return "General Provisions"
        except Exception as e:
            logger.error(f"Compliance area determination failed: {e}")
            return "General Provisions"
    
    def create_chunk_id(self, doc_type: str, section_num: int, title: str = "", pdf_path: Path = None) -> str:

        if doc_type == "act":
            return f"ca2013_act_s{section_num:03d}"
        else:
            if pdf_path:
                path_hash = hashlib.sha1(str(pdf_path).encode()).hexdigest()[:10]
                chunk_id = f"ca2013_{doc_type}_{path_hash}"
            else:
                chunk_id = f"ca2013_{doc_type}_s{section_num:03d}"
            
            original = chunk_id
            counter = 1
            while chunk_id in self.existing_chunk_ids:
                chunk_id = f"{original}_dup{counter}"
                counter += 1
            
            return chunk_id
    
    def process_act_section(self, section_num: int, section_dir: Path) -> List[Dict[str, Any]]:
        act_dir = section_dir / "act"
        if not act_dir.exists():
            return []
        
        txt_files = list(act_dir.glob("section_*_act.txt"))
        if not txt_files:
            return []
        
        txt_file = txt_files[0]
        
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
        except Exception as e:
            logger.error(f"Read error {txt_file}: {e}")
            return []
        
        if len(text) < 200:
            logger.warning(f"Section {section_num}: text too short ({len(text)} chars)")
            return []
        
        lines = text.split('\n')
        title = lines[0] if lines else f"Section {section_num}"
        title = re.sub(r'^Section \d+[:\.\-\s]*', '', title).strip() or f"Section {section_num}"
        
        chunk_id = self.create_chunk_id("act", section_num)
        if chunk_id in self.existing_chunk_ids:
            logger.info(f"Section {section_num} exists, skipping")
            return []
        
        logger.info(f"NEW Act Section {section_num}: {title}")
        summary = self.generate_summary(text, title)
        keywords = self.extract_keywords(text, title)
        compliance_area = self.determine_compliance_area(title, text, section_num)
        
        assert compliance_area in COMPLIANCE_AREAS, f"Invalid compliance_area: {compliance_area}"
        
        section_url = self.get_section_url(section_num)
        
        chunk = {
            "chunk_id": chunk_id,
            "document_type": "act",
            "authority_level": "Statutory",
            "section": section_num,
            "sub_section": None,
            "title": title,
            "compliance_area": compliance_area,
            "text": text,  
            "summary": summary,
            "keywords": keywords,
            "relationships": {
                "implements": [], "implemented_by": [], "amended_by": [],
                "clarified_by": [], "proceduralised_by": [], "has_schedule": [],
                "applies_to": []
            },
            "citation": f"Companies Act, 2013 — Section {section_num}",
            "source": {
                "path": str(txt_file.relative_to(self.raw_dir.parent)),
                "url": section_url
            }
        }
        
        return [chunk]
    
    def process_other_documents(self, section_num: int, section_dir: Path, doc_type: str) -> List[Dict[str, Any]]:
        doc_dir = section_dir / doc_type
        if not doc_dir.exists():
            return []
        
        pdf_files = list(doc_dir.glob("*.pdf"))
        if not pdf_files:
            return []
        
        chunks = []
        for idx, pdf_file in enumerate(pdf_files, 1):
            title = pdf_file.stem.replace('_', ' ').strip()
            text = self.extract_pdf_text(pdf_file)
            
            if len(text) < 200:
                logger.warning(f"Skipping {doc_type}: {title} ({len(text)} chars)")
                continue
            
            chunk_id = self.create_chunk_id(doc_type, section_num, title, pdf_file)
            
            if chunk_id in self.existing_chunk_ids:
                logger.info(f"  {doc_type} exists: {title}")
                continue
            
            logger.info(f"  NEW {doc_type}: {title}")
            
            chunk = {
                "chunk_id": chunk_id,
                "document_type": doc_type,
                "authority_level": AUTHORITY_LEVELS.get(doc_type, "Sub-statutory"),
                "section": section_num,
                "sub_section": None,
                "title": title,
                "compliance_area": "", 
                "text": text,  
                "summary": "", 
                "keywords": [], 
                "relationships": {  
                    "implements": [], "implemented_by": [], "amended_by": [],
                    "clarified_by": [], "proceduralised_by": [], "has_schedule": [],
                    "applies_to": []
                },
                "citation": f"Companies Act, 2013 — Section {section_num} — {doc_type.title()}",
                "source": {
                    "path": str(pdf_file.relative_to(self.raw_dir.parent)),
                    "url": self.get_section_url(section_num)
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def get_section_url(self, section_num: int) -> str:
        mapping_file = self.raw_dir / "chapter_mapping.json"
        if not mapping_file.exists():
            return f"https://ca2013.com/sections/{section_num}/"
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            for chapter_data in mapping.values():
                for section in chapter_data.get('sections', []):
                    if section.get('number') == section_num:
                        return section.get('url', f"https://ca2013.com/sections/{section_num}/")
            
            return f"https://ca2013.com/sections/{section_num}/"
        except:
            return f"https://ca2013.com/sections/{section_num}/"
    
    def process_section(self, section_num: int) -> List[Dict[str, Any]]:
        section_dir = self.raw_dir / f"section_{section_num:03d}"
        if not section_dir.exists():
            logger.warning(f"Section {section_num} dir not found")
            return []
        
        logger.info(f"\n{'='*80}\nPROCESSING SECTION {section_num}\n{'='*80}")
        all_new = []
        all_new.extend(self.process_act_section(section_num, section_dir))
        
        for doc_type in ["rules", "orders", "notifications", "circulars", "register", "return", "schedule"]:
            all_new.extend(self.process_other_documents(section_num, section_dir, doc_type))
        
        if all_new:
            logger.info(f"Section {section_num}: {len(all_new)} NEW chunks")
            self.sections_processed.add(section_num)
        else:
            logger.info(f"○ Section {section_num}: No new chunks")
        
        return all_new
    
    def process_sections(self, start_section: int = 43, end_section: int = 72):
        logger.info(f"\n{'#'*80}\nCHUNKING ENGINE\nSections {start_section}-{end_section} (NEW ONLY)\n{'#'*80}\n")
        
        for section_num in range(start_section, end_section + 1):
            self.new_chunks.extend(self.process_section(section_num))
        
        logger.info(f"\n{'#'*80}\n COMPLETE\nNew chunks: {len(self.new_chunks)}\nSections: {len(self.sections_processed)}\n{'#'*80}\n")
    
    def validate_chunks(self) -> bool:
        logger.info("Running validation...")
        
        all_ids = [c['chunk_id'] for c in self.existing_chunks + self.new_chunks]
        if len(set(all_ids)) != len(all_ids):
            logger.error("Duplicate chunk_ids!")
            return False
        logger.info("  No duplicates")
        
        short = [c for c in self.new_chunks if len(c['text']) < 200]
        if short:
            logger.error(f" {len(short)} chunks have text < 200 chars")
            return False
        logger.info("  All text >= 200 chars")
        
        bad_rel = [c for c in self.new_chunks if c['document_type'] != 'act' and any(c['relationships'].values())]
        if bad_rel:
            logger.error(f"{len(bad_rel)} non-Act chunks have relationships")
            return False
        logger.info("   Relationships empty for non-Act")
        
        logger.info(" Validation passed")
        return True
    
    def save_chunks(self):
        if not self.validate_chunks():
            logger.error("Validation failed. ABORTING.")
            return False
        
        all_chunks = self.existing_chunks + self.new_chunks
        
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "total_chunks": len(all_chunks),
            "statute": "Companies Act, 2013",
            "sections_processed": len(self.sections_processed) + len(set(c['section'] for c in self.existing_chunks if c.get('section')))
        }
        
        output = {"metadata": metadata, "chunks": all_chunks}
        
        logger.info(f"\nSaving to {self.chunks_file}...")
        logger.info(f"  Existing: {len(self.existing_chunks)}")
        logger.info(f"  New: {len(self.new_chunks)}")
        logger.info(f"  Total: {len(all_chunks)}")
        
        with open(self.chunks_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        size_mb = self.chunks_file.stat().st_size / 1024 / 1024
        logger.info(f" Saved: {self.chunks_file} ({size_mb:.2f} MB)")
        return True


def main():
    engine = GovernanceChunkingEngine(raw_dir="raw", chunks_file="chunks/chunks_final.json")
    engine.process_sections(start_section=43, end_section=72)
    engine.save_chunks()


if __name__ == "__main__":
    main()
