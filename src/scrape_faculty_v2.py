"""
Faculty scraper v2 - targets specific faculty/staff pages on CUSB website.

Many universities have dedicated faculty pages under /faculty, /staff, /people, etc.
This scraper tries multiple patterns to find actual faculty information.

Usage: python src/scrape_faculty_v2.py
"""

import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.cusb.ac.in"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_faculty_v2.md"

# Department faculty page patterns to try
FACULTY_PAGE_PATTERNS = [
    # Pattern: dept/article params that might have faculty tabs/sections
    ("Bioinformatics", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31&Itemid=136",
    ]),
    ("Geology", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=29&Itemid=128",
    ]),
    ("Geography", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=46&Itemid=158",
    ]),
    ("Life Science", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=35&Itemid=144",
    ]),
    ("Biotechnology", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=32&Itemid=137",
    ]),
    ("Environmental Sciences", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=30&Itemid=129",
    ]),
    ("Mathematics", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=56&Itemid=170",
    ]),
    ("Statistics", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=57&Itemid=171",
    ]),
    ("Computer Science", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=33&Itemid=134",
    ]),
    ("Chemistry", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=39&Itemid=148",
    ]),
    ("Physics", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=40&Itemid=149",
    ]),
    ("English", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=143&Itemid=167",
    ]),
    ("Economics", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=45&Itemid=157",
    ]),
    ("Psychology", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=38&Itemid=146",
    ]),
    ("Commerce", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=141&Itemid=165",
    ]),
    ("Law", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=43&Itemid=154",
    ]),
    ("Pharmacy", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=37&Itemid=138",
    ]),
    ("Agriculture", [
        "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=44&Itemid=155",
    ]),
]

# Administration pages that have faculty names
ADMIN_PAGES = [
    ("Administration", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=9&Itemid=115"),
    ("Visitor", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=10&Itemid=116"),
    ("Chancellor", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=11&Itemid=117"),
    ("Vice-Chancellor", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=12&Itemid=118"),
    ("Dean of Students", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=18&Itemid=124"),
    ("Proctorial Board", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=21&Itemid=125"),
    ("Registrar", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=16&Itemid=122"),
    ("Finance Officer", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=17&Itemid=123"),
    ("Controller of Examination", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=19&Itemid=126"),
    ("Librarian", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=20&Itemid=127"),
]


def scrape_page(url):
    """Scrape a single page and return content."""
    try:
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script/style
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        # Get main content
        content_div = soup.find('div', class_='item-page') or soup.find('article') or soup.find('main') or soup.find('div', class_='content')
        
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
            # Clean up
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            return text[:5000]  # Limit content
        return ""
        
    except Exception as e:
        print(f"    Error: {e}")
        return ""


def extract_faculty_from_text(text):
    """Extract faculty names and designations from text."""
    faculty_list = []
    
    # Patterns for faculty names
    patterns = [
        r'(Prof\.\s+[A-Z][a-zA-Z\s\.]+)',  # Prof. Name
        r'(Dr\.\s+[A-Z][a-zA-Z\s\.]+)',     # Dr. Name
        r'(Professor\s+[A-Z][a-zA-Z\s\.]+)', # Professor Name
        r'(Associate Professor\s+[A-Z][a-zA-Z\s\.]+)', # Associate Professor Name
        r'(Assistant Professor\s+[A-Z][a-zA-Z\s\.]+)', # Assistant Professor Name
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) > 10 and len(match) < 100:  # Reasonable length
                faculty_list.append(match.strip())
    
    return list(set(faculty_list))  # Remove duplicates


def main():
    """Main scraping function."""
    print("=" * 70)
    print("👨‍🏫 CUSB FACULTY SCRAPER V2 - Administration Pages")
    print("=" * 70)
    
    all_data = []
    
    # Scrape administration pages (these have actual names)
    print("\n📚 Scraping Administration Pages...")
    for title, url in ADMIN_PAGES:
        print(f"  {title}...")
        content = scrape_page(url)
        if content:
            faculty = extract_faculty_from_text(content)
            all_data.append({
                'title': title,
                'url': url,
                'content': content,
                'faculty': faculty
            })
            print(f"    ✅ Found {len(faculty)} names")
        time.sleep(0.5)
    
    # Generate markdown
    print("\n📝 Generating faculty database...")
    
    md_content = ["# CUSB Faculty and Administration Directory\n\n"]
    md_content.append(f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    for item in all_data:
        md_content.append(f"## {item['title']}\n\n")
        md_content.append(f"**Page:** {item['url']}\n\n")
        
        if item['faculty']:
            md_content.append("### Key Persons\n\n")
            for name in item['faculty'][:10]:  # Limit to 10 per page
                md_content.append(f"- {name}\n")
            md_content.append("\n")
        
        # Add raw content (limited)
        md_content.append("### Page Content\n\n")
        md_content.append("```\n")
        md_content.append(item['content'][:2000])  # First 2000 chars
        md_content.append("\n```\n\n---\n\n")
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ Faculty scraping complete!")
    print(f"   Pages scraped: {len(all_data)}")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
