"""
Web Scraper for Companies Act 2013
Scrapes the full text of the Companies Act from official sources
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup


class CompaniesActScraper:
    def __init__(self):
        self.base_url = "https://www.mca.gov.in"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def scrape_act(self) -> List[Dict[str, Any]]:
        """
        Scrape the Companies Act 2013
        Returns list of sections with metadata
        """
        print("Scraping Companies Act 2013...")
        
        # Note: This is a template - actual URL may vary
        # The MCA website structure may change, so this would need updating
        act_url = "https://www.mca.gov.in/content/mca/global/en/acts-rules/ebooks/acts.html"
        
        try:
            response = self.session.get(act_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            sections = self._parse_act_sections(soup)
            print(f"Scraped {len(sections)} sections")
            
            return sections
            
        except Exception as e:
            print(f"Error scraping: {e}")
            print("\nAlternative: Manual data entry or PDF parsing")
            return self._create_sample_sections()
    
    def _parse_act_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse sections from the Act HTML"""
        sections = []
        
        # Find all section elements (adjust selectors based on actual HTML)
        section_elements = soup.find_all(['div', 'section'], class_=re.compile(r'section|chapter'))
        
        for element in section_elements:
            section_data = self._extract_section_data(element)
            if section_data:
                sections.append(section_data)
        
        return sections
    
    def _extract_section_data(self, element) -> Dict[str, Any]:
        """Extract data from a section element"""
        # This is a template - actual implementation depends on HTML structure
        
        # Look for section number
        section_num_match = re.search(r'Section\s+(\d+)', element.get_text())
        if not section_num_match:
            return None
        
        section_num = section_num_match.group(1)
        
        # Extract title and text
        title = ""
        text = ""
        
        # Find heading
        heading = element.find(['h1', 'h2', 'h3', 'h4'])
        if heading:
            title = heading.get_text().strip()
        
        # Get section text
        paragraphs = element.find_all('p')
        text = '\n'.join([p.get_text().strip() for p in paragraphs])
        
        # Extract sub-sections
        sub_sections = self._extract_sub_sections(element)
        
        return {
            "section": section_num,
            "title": title,
            "text": text,
            "sub_sections": sub_sections,
            "chapter": None,  # Would extract from structure
            "part": None      # Would extract from structure
        }
    
    def _extract_sub_sections(self, element) -> List[Dict[str, Any]]:
        """Extract sub-sections from a section"""
        sub_sections = []
        
        # Look for numbered sub-sections (1), (2), (3), etc.
        text = element.get_text()
        sub_pattern = r'\((\d+)\)\s*([^\(]+?)(?=\(\d+\)|$)'
        
        for match in re.finditer(sub_pattern, text):
            sub_num = match.group(1)
            sub_text = match.group(2).strip()
            
            if sub_text:
                sub_sections.append({
                    "number": sub_num,
                    "text": sub_text
                })
        
        return sub_sections
    
    def _create_sample_sections(self) -> List[Dict[str, Any]]:
        """
        Create sample sections for testing
        In practice, you would manually input or parse from PDF
        """
        print("Creating sample sections...")
        
        sample_sections = [
            {
                "section": "1",
                "title": "Short title, extent and commencement",
                "text": "This Act may be called the Companies Act, 2013. It extends to the whole of India. It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint.",
                "sub_sections": [
                    {"number": "1", "text": "This Act may be called the Companies Act, 2013."},
                    {"number": "2", "text": "It extends to the whole of India."},
                    {"number": "3", "text": "It shall come into force on such date as the Central Government may notify."}
                ],
                "chapter": "I",
                "part": "I"
            },
            {
                "section": "2",
                "title": "Definitions",
                "text": "In this Act, unless the context otherwise requires, various terms are defined including 'company', 'director', 'financial year', and others.",
                "sub_sections": [
                    {"number": "20", "text": "Company means a company incorporated under this Act or under any previous company law."},
                    {"number": "34", "text": "Director means a director appointed to the Board of a company."}
                ],
                "chapter": "I",
                "part": "I"
            }
        ]
        
        return sample_sections
    
    def scrape_mca_notifications(self) -> List[Dict[str, Any]]:
        """Scrape MCA notifications and circulars"""
        print("Scraping MCA notifications...")
        
        notifications = []
        
        # MCA circulars page
        circulars_url = "https://www.mca.gov.in/content/mca/global/en/mca/master-data/circulars.html"
        
        try:
            response = self.session.get(circulars_url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find notification links
            links = soup.find_all('a', href=re.compile(r'\.pdf$'))
            
            for link in links[:10]:  # Limit to first 10 for testing
                pdf_url = link.get('href')
                if not pdf_url.startswith('http'):
                    pdf_url = self.base_url + pdf_url
                
                notifications.append({
                    "title": link.get_text().strip(),
                    "url": pdf_url,
                    "type": "notification"
                })
                
                time.sleep(1)  # Be respectful
            
        except Exception as e:
            print(f"Error scraping notifications: {e}")
        
        return notifications
    
    def save_to_json(self, data: List[Dict], filename: str):
        """Save scraped data to JSON"""
        output_file = Path(filename)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved data to {output_file}")


def main():
    """Main execution"""
    scraper = CompaniesActScraper()
    
    # Scrape the Act
    sections = scraper.scrape_act()
    scraper.save_to_json(sections, "companies_act_sections.json")
    
    # Scrape notifications
    notifications = scraper.scrape_mca_notifications()
    scraper.save_to_json(notifications, "mca_notifications.json")
    
    print("\n=== Scraping Complete ===")
    print(f"Sections: {len(sections)}")
    print(f"Notifications: {len(notifications)}")
    print("\nNote: For production use, consider:")
    print("1. Manual PDF parsing of official Act PDF")
    print("2. Respecting robots.txt and rate limits")
    print("3. Caching responses to avoid repeated requests")


if __name__ == "__main__":
    main()
