"""
Web Scraper for Companies Act 2013 from ca2013.com
Scrapes first 3 chapters (sections 1-42) with all 8 tabs per section
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import os


class CompaniesActScraper:
    def __init__(self, output_dir="raw"):
        self.base_url = "https://ca2013.com"
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Tab mapping
        self.tabs = {
            1: "act",
            2: "rules", 
            3: "orders",
            4: "notifications",
            5: "circulars",
            6: "register",
            7: "return",
            8: "schedule"
        }
        
    def get_chapters(self):
        """Get chapter information from sections page"""
        print("Fetching chapter structure...")
        url = f"{self.base_url}/sections/"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            chapters = {}
            
            # Find chapter headings
            chapter_headings = soup.find_all('h2', string=re.compile(r'Chapter \d+'))
            
            for heading in chapter_headings[:3]:  # Only first 3 chapters
                chapter_text = heading.get_text(strip=True)
                chapter_match = re.search(r'Chapter (\d+)', chapter_text)
                
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))
                    
                    # Get sections range from heading text
                    range_match = re.search(r'\(Section (\d+) to (\d+)\)', chapter_text)
                    if range_match:
                        start_sec = int(range_match.group(1))
                        end_sec = int(range_match.group(2))
                        
                        chapters[chapter_num] = {
                            "title": chapter_text,
                            "sections": list(range(start_sec, end_sec + 1))
                        }
            
            print(f"Found {len(chapters)} chapters")
            for ch, info in chapters.items():
                print(f"  Chapter {ch}: {len(info['sections'])} sections")
            
            return chapters
            
        except Exception as e:
            print(f"Error fetching chapters: {e}")
            return {}
    
    def get_section_url_from_list(self, section_num):
        """Get the section detail URL from the sections list page"""
        chapter_url = f"{self.base_url}/sections/{section_num}/"
        
        try:
            response = self.session.get(chapter_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the first link in the ordered list (the actual section page)
            ol = soup.find('ol')
            if ol:
                first_li = ol.find('li')
                if first_li:
                    link = first_li.find('a')
                    if link and link.get('href'):
                        section_url = urljoin(self.base_url, link['href'])
                        return section_url
            
            return None
            
        except Exception as e:
            print(f"    Error getting section URL: {e}")
            return None
    
    def scrape_section(self, section_num):
        """Scrape a single section with all 8 tabs"""
        print(f"\n{'='*70}")
        print(f"Scraping Section {section_num}")
        print(f"{'='*70}")
        
        # Create section directory
        section_dir = self.output_dir / f"section_{section_num:03d}"
        section_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the actual section page URL
        section_url = self.get_section_url_from_list(section_num)
        if not section_url:
            print(f"  ✗ Could not find section {section_num} URL")
            return False
        
        print(f"  Section URL: {section_url}")
        
        # Scrape each tab
        for tab_num, tab_name in self.tabs.items():
            tab_url = f"{section_url}#tab-{tab_num}"
            print(f"\n  [{tab_num}/8] Scraping {tab_name.upper()} tab...")
            
            if tab_num == 1 or tab_num == 8:
                # Act and Schedule are HTML text
                self.scrape_html_tab(section_url, tab_num, section_num, section_dir, tab_name)
            else:
                # Other tabs have PDFs
                self.scrape_pdf_tab(section_url, tab_num, section_num, section_dir, tab_name)
        
        print(f"\n  ✓ Section {section_num} complete")
        return True
    
    def scrape_html_tab(self, section_url, tab_num, section_num, section_dir, tab_name):
        """Scrape HTML content from Act or Schedule tab"""
        try:
            response = self.session.get(section_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the tab content
            tab_content = soup.find('div', id=f'tab-{tab_num}')
            
            if not tab_content:
                print(f"    ⚠ No content found for tab {tab_num}")
                return
            
            # Create subdirectory
            tab_dir = section_dir / tab_name
            tab_dir.mkdir(exist_ok=True)
            
            # Extract text content
            text_content = tab_content.get_text(separator='\n', strip=True)
            
            # Save as .txt
            txt_file = tab_dir / f"section_{section_num:03d}_{tab_name}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # Save as .html
            html_file = tab_dir / f"section_{section_num:03d}_{tab_name}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(str(tab_content))
            
            print(f"    ✓ Saved {tab_name} text ({len(text_content)} chars)")
            
        except Exception as e:
            print(f"    ✗ Error scraping {tab_name}: {e}")
    
    def scrape_pdf_tab(self, section_url, tab_num, section_num, section_dir, tab_name):
        """Scrape PDF links from a tab and download them"""
        try:
            response = self.session.get(section_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the tab content
            tab_content = soup.find('div', id=f'tab-{tab_num}')
            
            if not tab_content:
                print(f"    ⚠ No content for {tab_name} tab")
                return
            
            # Find all PDF links
            pdf_links = []
            for link in tab_content.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf') or '/pdf/' in href.lower():
                    pdf_url = urljoin(self.base_url, href)
                    pdf_links.append({
                        'url': pdf_url,
                        'text': link.get_text(strip=True)
                    })
            
            if not pdf_links:
                print(f"    ⚠ No PDFs found in {tab_name} tab")
                return
            
            # Create subdirectory
            tab_dir = section_dir / tab_name
            tab_dir.mkdir(exist_ok=True)
            
            # Download PDFs
            print(f"    Found {len(pdf_links)} PDF(s)")
            for i, pdf_info in enumerate(pdf_links, 1):
                self.download_pdf(pdf_info['url'], tab_dir, pdf_info['text'], i, len(pdf_links))
                time.sleep(0.5)  # Be polite
            
        except Exception as e:
            print(f"    ✗ Error scraping {tab_name} PDFs: {e}")
    
    def download_pdf(self, url, save_dir, link_text, current, total):
        """Download a single PDF file"""
        try:
            # Generate filename from URL or link text
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            
            if not filename or not filename.endswith('.pdf'):
                # Generate from link text
                safe_name = re.sub(r'[^\w\s-]', '', link_text)
                safe_name = re.sub(r'[-\s]+', '-', safe_name).strip('-')
                filename = f"{safe_name[:100]}.pdf" if safe_name else f"document_{current}.pdf"
            
            filepath = save_dir / filename
            
            # Check if already exists
            if filepath.exists():
                print(f"      [{current}/{total}] ⊙ {filename} (already exists)")
                return True
            
            # Download
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = filepath.stat().st_size / 1024  # KB
            print(f"      [{current}/{total}] ✓ {filename} ({file_size:.1f} KB)")
            return True
            
        except Exception as e:
            print(f"      [{current}/{total}] ✗ Error downloading {filename}: {e}")
            return False
    
    def save_chapter_mapping(self, chapters):
        """Save chapter to sections mapping"""
        mapping_file = self.output_dir / "chapter_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(chapters, f, indent=2, ensure_ascii=False)
        print(f"\nSaved chapter mapping to {mapping_file}")
    
    def run(self):
        """Main scraping execution"""
        print("\n" + "="*70)
        print("COMPANIES ACT 2013 WEB SCRAPER")
        print("Scraping first 3 chapters from ca2013.com")
        print("="*70 + "\n")
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Get chapter structure
        chapters = self.get_chapters()
        if not chapters:
            print("Failed to get chapter structure!")
            return
        
        # Save chapter mapping
        self.save_chapter_mapping(chapters)
        
        # Collect all sections to scrape
        all_sections = []
        for chapter_num, chapter_info in sorted(chapters.items()):
            all_sections.extend(chapter_info['sections'])
        
        print(f"\nTotal sections to scrape: {len(all_sections)}")
        print(f"Sections: {min(all_sections)} to {max(all_sections)}")
        
        # Scrape each section
        successful = 0
        failed = 0
        
        for i, section_num in enumerate(all_sections, 1):
            print(f"\n[{i}/{len(all_sections)}] Section {section_num}")
            
            if self.scrape_section(section_num):
                successful += 1
            else:
                failed += 1
            
            # Be polite - wait between sections
            if i < len(all_sections):
                time.sleep(2)
        
        # Summary
        print("\n" + "="*70)
        print("SCRAPING COMPLETE")
        print("="*70)
        print(f"Successfully scraped: {successful} sections")
        print(f"Failed: {failed} sections")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("="*70 + "\n")


def main():
    scraper = CompaniesActScraper(output_dir="raw")
    scraper.run()


if __name__ == "__main__":
    main()
