"""
Web scraper for cusb.ac.in to extract and add data to knowledge base.

Usage: python src/scrape_cusb.py
"""

import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.cusb.ac.in"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_scraped.md"


def clean_text(text: str, url: str = "") -> str:
    """Clean and normalize text, removing navigation noise."""
    # Remove common navigation/footer patterns
    noise_patterns = [
        r'Central University of South Bihar, Gaya, Bihar.*?Webmail',
        r'Quick Links.*?Copyright reserved',
        r'☎\s*\d+.*?✉\s*\w+@\w+\.\w+',
        r'Reception\s*:\s*\+91.*?FOLLOW US.*?IMPORTANT LINKS.*?Copyright reserved @ Central University of South Bihar, Gaya',
        r'\[\s*RTI\s*\].*?\[\s*Public Self Disclosure\s*\]',
        r'1st Vice-Chancellor.*?Cup.*?Box Cricket League.*?\[.*?\]',
        r'CUSB Admission Bulletin.*?CUET-PG.*?\d{4}',
        r'Ministry of Human Resource Development.*?National Academic Depository.*?Public Self Disclosure',
        r'Download Academic Notices / Exam Notices.*?Committee & Cells.*?Upcoming Events.*?Tenders.*?Recruitment',
        r'Contact Us:.*?LOCATE US.*?FOLLOW US.*?IMPORTANT LINKS',
        r'×\s*☎.*?✉.*?\[.*?\]',
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, ' ', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    # Remove repeated university name at start
    text = re.sub(r'^Central University of South Bihar.*?Bihar\s*', '', text, flags=re.IGNORECASE)
    
    return text


def scrape_page(url: str) -> str:
    """Scrape a single page and return cleaned markdown content with links."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove noise elements
        for elem in soup(["script", "style", "nav", "footer", "header", "aside", 
                         ".menu", ".navigation", ".sidebar", ".widget"]):
            elem.decompose()
        
        # Try to find main content area
        main_content = None
        for selector in ['article', 'main', '.content', '#content', '.article', 
                        '.post-content', '.entry-content', '[role="main"]']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body but remove header/footer areas
        if not main_content:
            body = soup.find('body')
            if body:
                for elem in body.find_all(['div', 'header', 'footer'], class_=lambda x: x and any(
                    word in str(x).lower() for word in ['header', 'footer', 'top', 'bottom', 'nav', 'menu'])):
                    elem.decompose()
                main_content = body
            else:
                main_content = soup
        
        # Extract text content
        content = main_content.get_text(separator='\n')
        content = clean_text(content, url)
        
        # Extract important links (PDF downloads, forms, etc.)
        important_links = []
        for a in main_content.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            
            # Only capture meaningful links with text
            if text and len(text) > 3:
                # Build full URL
                if href.startswith('/'):
                    full_url = BASE_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = url.rsplit('/', 1)[0] + '/' + href
                
                # Capture download/form links
                if any(keyword in text.lower() or keyword in href.lower() 
                       for keyword in ['pdf', 'download', 'form', 'application', 'format', 
                                     'performa', 'link', 'click', 'here', 'apply',
                                     'scholarship', 'regulation', 'notice']):
                    important_links.append(f"[{text}]: {full_url}")
        
        # Add links section if any found
        if important_links:
            content += "\n\n---\nImportant Links:\n" + '\n'.join(important_links)
        
        # Remove very short lines
        lines = [line.strip() for line in content.split('\n') if len(line.strip()) > 10]
        content = '\n'.join(lines)
        
        return content
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""


def scrape_cusb():
    """Scrape key pages from CUSB website."""
    # Admission and administrative keywords
    admission_keywords = [
        'admission 2026', 'admission 2025', 'admission 2026-27', 'admission 2025-26',
        'international student', 'programmes', 'courses', 'help desk',
        'ranking', 'naac', 'feedback', 'audit', 'aqar', 'meetings', 
        'iqac', 'iqac report', 'cycle-ii', 'cycle ii', 'accreditation',
        'admission bulletin', 'cuet', 'admission process', 'eligibility',
        'apply', 'application', 'prospectus', 'international', 'nri',
        'helpdesk', 'student support', 'academic calendar'
    ]
    try:
        response = requests.get(BASE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/') or href.startswith(BASE_URL):
                full_url = href if href.startswith('http') else BASE_URL + href
                links.append((a.get_text(strip=True), full_url))
        
        print(f"Found {len(links)} links")
        
        # Filter for admission and administrative pages
        key_pages = []
        seen_urls = set()
        
        for title, url in links:
            if url in seen_urls:
                continue
            # Look for admission and administrative pages
            if any(keyword in url.lower() or keyword in title.lower() for keyword in admission_keywords):
                if len(key_pages) < 30:  # Limit for admission pages
                    key_pages.append((title or url, url))
                    seen_urls.add(url)
        
        # Also look for official/accreditation pages
        admin_patterns = ['naac', 'iqac', 'audit', 'report', 'meeting', 'committee', 'board']
        for title, url in links:
            if url in seen_urls:
                continue
            if any(pattern in title.lower() for pattern in admin_patterns):
                if len(key_pages) < 30:
                    key_pages.append((title or url, url))
                    seen_urls.add(url)
        
        print(f"Found {len(key_pages)} admission/administrative pages")
        
        if not key_pages:
            for title, url in links[:15]:
                if url not in seen_urls:
                    key_pages.append((title or url, url))
                    seen_urls.add(url)
                    
    except Exception as e:
        print(f"Error discovering pages: {e}")
        key_pages = [("Homepage", BASE_URL)]
    
    markdown_content = "# CUSB Website Scraped Data\n\n"
    markdown_content += f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    markdown_content += "---\n\n"
    
    for title, url in key_pages:
        print(f"Scraping: {title}...")
        content = scrape_page(url)
        
        if content:
            markdown_content += f"## {title}\n\n"
            markdown_content += f"Source: {url}\n\n"
            markdown_content += content + "\n\n"
            markdown_content += "---\n\n"
        else:
            print(f"  Warning: Failed to scrape {title}")
        
        time.sleep(1)  # Be respectful to the server
    
    # Save to file
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n✅ Scraped data saved to: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    scrape_cusb()
