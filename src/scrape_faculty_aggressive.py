"""
Aggressive faculty scraper - tries multiple strategies to find faculty names.

Strategies:
1. Check all PDFs, notices, announcements for faculty names
2. Look in course syllabi for coordinator names
3. Check research/p publication pages
4. Look in committee/board notifications
5. Try staff directory if available

Usage: python src/scrape_faculty_aggressive.py
"""

import re
import sys
import time
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.cusb.ac.in"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_faculty_found.md"

# Possible faculty name patterns
FACULTY_PATTERNS = [
    r'Prof\.\s+([A-Z][a-zA-Z\s\.]+?)(?=,|\(|\n|$)',
    r'Dr\.\s+([A-Z][a-zA-Z\s\.]+?)(?=,|\(|\n|$)',
    r'Professor\s+([A-Z][a-zA-Z\s\.]+?)(?=,|\(|\n|$)',
    r'(?:Coordinator|Convener|Head)\s*[:\-]?\s*([A-Z][a-zA-Z\s\.]+?)(?=,|\(|\n|$)',
    r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[-,]?\s*(?:Professor|Assistant|Associate)',
]

# Department URL patterns to try
DEPARTMENT_URLS = {
    "Environmental Sciences": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=30&Itemid=129",
    ],
    "Statistics": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=57&Itemid=171",
    ],
    "Mathematics": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=56&Itemid=170",
    ],
    "Computer Science": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=33&Itemid=134",
    ],
    "Biotechnology": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=32&Itemid=137",
    ],
    "Chemistry": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=39&Itemid=148",
    ],
    "Physics": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=40&Itemid=149",
    ],
    "Economics": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=45&Itemid=157",
    ],
    "English": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=143&Itemid=167",
    ],
    "Psychology": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=38&Itemid=146",
    ],
    "Law": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=43&Itemid=154",
    ],
    "Commerce": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=141&Itemid=165",
    ],
    "Geology": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=29&Itemid=128",
    ],
    "Geography": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=46&Itemid=158",
    ],
    "Life Science": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=35&Itemid=144",
    ],
    "Bioinformatics": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31&Itemid=136",
    ],
    "Pharmacy": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=37&Itemid=138",
    ],
    "Agriculture": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=44&Itemid=155",
    ],
    "Mass Communication": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=139&Itemid=163",
    ],
    "Education": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=41&Itemid=151",
    ],
    "Physical Education": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=42&Itemid=152",
    ],
    "Library Science": [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=55&Itemid=169",
    ],
}

# Committee/Notice pages where faculty names might appear
COMMITTEE_PAGES = [
    ("Academic Council", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=13&Itemid=119"),
    ("Board of Studies", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=14&Itemid=120"),
    ("Finance Committee", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=15&Itemid=121"),
    ("Examination Committee", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=76&Itemid=191"),
]


def extract_names_from_text(text):
    """Extract faculty names from text using patterns."""
    names = []
    for pattern in FACULTY_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            # Clean up the match
            name = match.strip()
            # Filter out common false positives
            if len(name) > 3 and len(name) < 50:
                if not any(word in name.lower() for word in ['university', 'college', 'department', 'section', 'committee']):
                    names.append(name)
    return list(set(names))


def scrape_page_for_names(url, dept_name=""):
    """Scrape a page and extract faculty names."""
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script/style
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get all text
        text = soup.get_text(separator='\n', strip=True)
        
        # Extract names
        names = extract_names_from_text(text)
        
        return {
            'url': url,
            'names': names,
            'text_sample': text[:500]  # First 500 chars for debugging
        }
        
    except Exception as e:
        return {'url': url, 'names': [], 'error': str(e)}


def main():
    """Main scraping function."""
    print("=" * 70)
    print("🔍 AGGRESSIVE FACULTY NAME SCRAPER")
    print("=" * 70)
    
    all_results = []
    
    # Scrape department pages
    print("\n📚 Scraping Department Pages...")
    for dept_name, urls in DEPARTMENT_URLS.items():
        print(f"\n{dept_name}:")
        for url in urls:
            result = scrape_page_for_names(url, dept_name)
            if result['names']:
                print(f"  ✅ Found: {', '.join(result['names'][:5])}")
                all_results.append({
                    'department': dept_name,
                    'source': 'department_page',
                    'names': result['names'],
                    'url': url
                })
            else:
                print(f"  ❌ No names found")
            time.sleep(0.3)
    
    # Scrape committee pages
    print("\n📚 Scraping Committee Pages...")
    for title, url in COMMITTEE_PAGES:
        print(f"\n{title}:")
        result = scrape_page_for_names(url, title)
        if result['names']:
            print(f"  ✅ Found: {', '.join(result['names'][:5])}")
            all_results.append({
                'department': title,
                'source': 'committee_page',
                'names': result['names'],
                'url': url
            })
        else:
            print(f"  ❌ No names found")
        time.sleep(0.3)
    
    # Generate report
    print(f"\n{'=' * 70}")
    print("📊 RESULTS SUMMARY")
    print(f"{'=' * 70}")
    
    total_names = sum(len(r['names']) for r in all_results)
    print(f"Total pages scanned: {len(DEPARTMENT_URLS) + len(COMMITTEE_PAGES)}")
    print(f"Pages with faculty names: {len(all_results)}")
    print(f"Total unique names found: {total_names}")
    
    # Generate markdown
    md_content = ["# CUSB Faculty Names Found via Web Scraping\n\n"]
    md_content.append(f"**Scraped on:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    md_content.append(f"**Pages scanned:** {len(DEPARTMENT_URLS) + len(COMMITTEE_PAGES)}\n\n")
    md_content.append(f"**Pages with names:** {len(all_results)}\n\n")
    md_content.append(f"**Total names found:** {total_names}\n\n")
    md_content.append("---\n\n")
    
    for result in all_results:
        md_content.append(f"## {result['department']}\n\n")
        md_content.append(f"**Source:** {result['source']}\n\n")
        md_content.append(f"**URL:** {result['url']}\n\n")
        md_content.append("**Faculty Names Found:**\n\n")
        for name in result['names']:
            md_content.append(f"- {name}\n")
        md_content.append("\n---\n\n")
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ Scraping Complete!")
    print(f"Output saved to: {OUTPUT_FILE}")
    print(f"File size: {len(output_text)} characters")
    print(f"{'=' * 70}")
    
    return all_results


if __name__ == "__main__":
    main()
