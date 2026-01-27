import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class CompaniesActScraper:
    BASE_URL = "https://ca2013.com"
    SECTIONS_URL = f"{BASE_URL}/sections/"
    TABS = {
        "1": {"name": "act", "type": "html"},
        "2": {"name": "rules", "type": "pdf"},
        "3": {"name": "orders", "type": "pdf"},
        "4": {"name": "notifications", "type": "pdf"},
        "5": {"name": "circulars", "type": "pdf"},
        "6": {"name": "register", "type": "pdf"},
        "7": {"name": "return", "type": "pdf"},
        "8": {"name": "schedule", "type": "mixed"}
    }
    
    def __init__(self, output_dir: str = "raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_section_listing(self, chapter_num: int) -> List[Dict[str, str]]:
        chapter_url = f"{self.SECTIONS_URL}{chapter_num}/"
        
        try:
            logger.info(f"Fetching chapter {chapter_num} listing from {chapter_url}")
            response = self.session.get(chapter_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            sections = []
            ol = soup.find('ol')
            if ol:
                items = ol.find_all('li')
                logger.info(f"Found {len(items)} sections in chapter {chapter_num}")
                
                for li in items:
                    link = li.find('a')
                    if link:
                        href = link.get('href')
                        title = link.get_text(strip=True)
                        detail_url = urljoin(self.BASE_URL, href)
                        sections.append({
                            'title': title,
                            'url': detail_url
                        })
            
            return sections
            
        except Exception as e:
            logger.error(f"Error getting chapter {chapter_num} listing: {e}")
            return []
    
    def extract_html_content(self, soup: BeautifulSoup) -> str:
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)
        return text
    
    def download_pdf(self, pdf_url: str, save_path: Path) -> bool:
        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            response = self.session.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            save_path.parent.mkdir(exist_ok=True, parents=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f" Saved: {save_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading {pdf_url}: {e}")
            return False
    
    def scrape_tab(self, detail_url: str, tab_num: str, section_dir: Path) -> Dict[str, Any]:
        tab_info = self.TABS[tab_num]
        tab_name = tab_info['name']
        tab_type = tab_info['type']
        
        tab_dir = section_dir / tab_name
        tab_dir.mkdir(exist_ok=True, parents=True)
        
        result = {
            'tab': tab_num,
            'name': tab_name,
            'type': tab_type,
            'items': []
        }
        
        try:
            logger.info(f"  Scraping tab {tab_num} ({tab_name})...")
            response = self.session.get(detail_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            tab_content = soup.find('div', id=f'tab-{tab_num}')
            
            if not tab_content:
                logger.warning(f"  Tab {tab_num} ({tab_name}) not found")
                return result
            
            if tab_type == 'html':
                section_num = section_dir.name.split('_')[1]
                
                html_path = tab_dir / f"section_{section_num}_act.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(str(tab_content))
                
                text_content = self.extract_html_content(tab_content)
                txt_path = tab_dir / f"section_{section_num}_act.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                result['items'].append({
                    'type': 'html',
                    'files': [html_path.name, txt_path.name]
                })
                logger.info(f" Saved HTML and text")
                
            elif tab_type == 'pdf' or tab_type == 'mixed':

                pdf_links = tab_content.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                iframes = tab_content.find_all('iframe', class_='pdfjs-viewer')
                
                pdf_sources = []
                
                for link in pdf_links:
                    pdf_url = urljoin(self.BASE_URL, link.get('href'))
                    title = link.get_text(strip=True)
                    pdf_sources.append({'url': pdf_url, 'title': title})
                
                for iframe in iframes:
                    src = iframe.get('src', '')
                    if 'file=' in src:
                        pdf_url = src.split('file=')[-1]
                        title = ''
                        prev_h2 = iframe.find_previous('h2')
                        if prev_h2:
                            title = prev_h2.get_text(strip=True)
                        pdf_sources.append({'url': pdf_url, 'title': title})
                
                if not pdf_sources:
                    logger.info(f"  No PDFs found in {tab_name}")
                    
                    if tab_type == 'mixed':
                        text_content = self.extract_html_content(tab_content)
                        if text_content.strip():
                            section_num = section_dir.name.split('_')[1]
                            txt_path = tab_dir / f"section_{section_num}_{tab_name}.txt"
                            with open(txt_path, 'w', encoding='utf-8') as f:
                                f.write(text_content)
                            result['items'].append({
                                'type': 'html',
                                'files': [txt_path.name]
                            })
                            logger.info(f"  Saved text content")
                else:
                    logger.info(f"  Found {len(pdf_sources)} PDFs")
                
                for idx, pdf_info in enumerate(pdf_sources, 1):
                    pdf_url = pdf_info['url']
                    pdf_title = pdf_info['title'] or f"document_{idx}"
                    
                    safe_filename = re.sub(r'[^\w\s-]', '', pdf_title)
                    safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
                    safe_filename = safe_filename[:100]  
                    
                    if not safe_filename:
                        safe_filename = f"document_{idx}"
                    
                    pdf_path = tab_dir / f"{safe_filename}.pdf"
                    
                    counter = 1
                    while pdf_path.exists():
                        pdf_path = tab_dir / f"{safe_filename}_{counter}.pdf"
                        counter += 1
                    
                    if self.download_pdf(pdf_url, pdf_path):
                        result['items'].append({
                            'type': 'pdf',
                            'title': pdf_title,
                            'url': pdf_url,
                            'file': pdf_path.name
                        })
                    
                    time.sleep(0.5) 
            
            logger.info(f"  Tab {tab_num} ({tab_name}): {len(result['items'])} items")
            
        except Exception as e:
            logger.error(f"  Error scraping tab {tab_num} ({tab_name}): {e}")
        
        return result
    
    def scrape_section(self, section_num: int, section_title: str, detail_url: str) -> Dict[str, Any]:
        logger.info(f"\n{'='*80}")
        logger.info(f"SCRAPING SECTION {section_num}: {section_title}")
        logger.info(f"{'='*80}")
        logger.info(f"URL: {detail_url}")
        
        section_dir = self.output_dir / f"section_{section_num:03d}"
        section_dir.mkdir(exist_ok=True, parents=True)
        
        section_metadata = {
            'section_number': section_num,
            'title': section_title,
            'url': detail_url,
            'tabs': {}
        }
        
        for tab_num in self.TABS.keys():
            tab_result = self.scrape_tab(detail_url, tab_num, section_dir)
            section_metadata['tabs'][tab_num] = tab_result
            time.sleep(1) 
        
        metadata_path = section_dir / 'section_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(section_metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Section {section_num} complete\n")
        
        return section_metadata
    
    def scrape_chapter_4(self, start_section: int = 43, end_section: int = 72):

        logger.info(f"\n{'#'*80}")
        logger.info("SHARE CAPITAL AND DEBENTURES")
        logger.info(f"Scraping Sections {start_section}-{end_section}")
        logger.info(f"{'#'*80}\n")
        
        mapping_path = self.output_dir / 'chapter_mapping.json'
        if not mapping_path.exists():
            logger.error(f"chapter_mapping.json not found at {mapping_path}")
            logger.error("Please ensure the chapter mapping file exists")
            return
        
        with open(mapping_path, 'r', encoding='utf-8') as f:
            chapter_mapping = json.load(f)
        
        chapter_4 = chapter_mapping.get('4')
        if not chapter_4:
            logger.error("Chapter 4 not found in chapter_mapping.json")
            return
        
        sections_list = chapter_4.get('sections', [])
        logger.info(f"Loaded {len(sections_list)} sections from chapter_mapping.json\n")
        
        scraped_sections = []
        for section_info in sections_list:
            section_num = section_info['number']
            section_title = section_info['name']
            section_url = section_info['url']
            
            if section_num < start_section or section_num > end_section:
                continue
            
            section_metadata = self.scrape_section(
                section_num,
                section_title,
                section_url
            )
            
            if section_metadata:
                scraped_sections.append(section_metadata)
            time.sleep(2) 
        
        logger.info(f"\n{'#'*80}")
        logger.info("SCRAPING COMPLETE")
        logger.info(f"Total sections scraped: {len(scraped_sections)}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        logger.info(f"Sections scraped: {start_section}-{end_section}")
        logger.info(f"{'#'*80}\n")


def main():
    scraper = CompaniesActScraper(output_dir="raw")
    scraper.scrape_chapter_4(start_section=43, end_section=72)


if __name__ == "__main__":
    main()
