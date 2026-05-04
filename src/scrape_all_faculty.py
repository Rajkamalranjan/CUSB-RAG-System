"""
Comprehensive faculty scraper - extracts faculty from all department pages.

This scraper aggressively searches for faculty information on department pages
by looking at various HTML structures and patterns.

Usage: python src/scrape_all_faculty.py
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
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_all_faculty.md"

# All department pages to scrape for faculty
DEPARTMENTS = {
    "Bioinformatics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31&Itemid=136",
    "Geology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=29&Itemid=128",
    "Geography": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=46&Itemid=158",
    "Life Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=35&Itemid=144",
    "Biotechnology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=32&Itemid=137",
    "Environmental Sciences": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=30&Itemid=129",
    "Historical Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=50&Itemid=162",
    "Economic Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=45&Itemid=157",
    "Development Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=47&Itemid=159",
    "Political Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=48&Itemid=160",
    "Sociological Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=49&Itemid=161",
    "Library and Information Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=55&Itemid=169",
    "Mathematics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=56&Itemid=170",
    "Statistics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=57&Itemid=171",
    "Computer Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=33&Itemid=134",
    "Teacher Education": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=41&Itemid=151",
    "Physical Education": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=42&Itemid=152",
    "Chemistry": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=39&Itemid=148",
    "Physics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=40&Itemid=149",
    "English": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=143&Itemid=167",
    "Indian Languages": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=53&Itemid=168",
    "Mass Communication": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=139&Itemid=163",
    "Commerce and Business Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=141&Itemid=165",
    "Psychological Sciences": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=38&Itemid=146",
    "Law and Governance": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=43&Itemid=154",
    "Pharmacy": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=37&Itemid=138",
    "Agriculture": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=44&Itemid=155",
}


def extract_faculty_from_page(soup, dept_name):
    """Extract faculty information from a department page using multiple strategies."""
    faculty_list = []
    
    # Strategy 1: Look for tables with faculty information
    tables = soup.find_all('table')
    for table in tables:
        # Check if table might contain faculty data
        table_text = table.get_text().lower()
        if any(keyword in table_text for keyword in ['professor', 'faculty', 'head', 'coordinator', 'teacher']):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Extract text from cells
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    full_text = ' | '.join(cell_texts)
                    
                    # Check if this row contains a person
                    if any(title in full_text.lower() for title in ['professor', 'dr.', 'mr.', 'ms.', 'head', 'coordinator']):
                        if len(full_text) > 15 and len(full_text) < 200:
                            faculty_list.append({
                                'info': full_text,
                                'source': 'table'
                            })
    
    # Strategy 2: Look for lists (ul/ol) with faculty
    lists = soup.find_all(['ul', 'ol'])
    for lst in lists:
        items = lst.find_all('li')
        for item in items:
            text = item.get_text(strip=True)
            # Check for professor/head patterns
            if any(pattern in text.lower() for pattern in ['professor', 'associate professor', 'assistant professor', 'head', 'dr.']):
                if len(text) > 20 and len(text) < 300 and 'university' not in text.lower():
                    faculty_list.append({
                        'info': text,
                        'source': 'list'
                    })
    
    # Strategy 3: Look for specific divs/sections
    divs = soup.find_all(['div', 'section', 'article'])
    for div in divs:
        # Check class names
        class_attr = div.get('class', [])
        class_str = ' '.join(class_attr) if isinstance(class_attr, list) else str(class_attr)
        
        if any(keyword in class_str.lower() for keyword in ['faculty', 'staff', 'people', 'member']):
            text = div.get_text(strip=True)
            if any(pattern in text.lower() for pattern in ['professor', 'dr.', 'head']):
                if len(text) > 30 and len(text) < 500:
                    faculty_list.append({
                        'info': text[:300],
                        'source': 'div'
                    })
    
    # Strategy 4: Look for headings followed by content
    headings = soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])
    for heading in headings:
        heading_text = heading.get_text(strip=True).lower()
        
        # Check if heading indicates faculty section
        if any(keyword in heading_text for keyword in ['faculty', 'staff', 'people', 'professor', 'teacher']):
            # Get next siblings until next heading
            content_parts = []
            sibling = heading.find_next_sibling()
            
            while sibling and sibling.name not in ['h2', 'h3', 'h4', 'h5', 'h6']:
                if sibling.name in ['p', 'div', 'span', 'li']:
                    text = sibling.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                sibling = sibling.find_next_sibling()
            
            if content_parts:
                full_content = ' '.join(content_parts)
                if len(full_content) > 50:
                    faculty_list.append({
                        'info': full_content[:400],
                        'source': 'heading_section'
                    })
    
    # Strategy 5: Look for paragraphs with faculty patterns
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        # Look for patterns like "Dr. Name, Professor" or "Prof. Name (Head)"
        if re.search(r'(Dr\.|Prof\.|Professor|Associate|Assistant)\s+[A-Z]', text):
            if len(text) > 25 and len(text) < 300:
                faculty_list.append({
                    'info': text,
                    'source': 'paragraph'
                })
    
    # Strategy 6: Look for links that might be faculty profiles
    links = soup.find_all('a')
    for link in links:
        text = link.get_text(strip=True)
        href = link.get('href', '')
        
        # Check if link text looks like a faculty name
        if any(pattern in text for pattern in ['Prof.', 'Dr.', 'Professor']):
            if len(text) > 10 and len(text) < 100:
                faculty_list.append({
                    'info': f"{text} (Profile: {href})",
                    'source': 'link'
                })
    
    return faculty_list


def clean_faculty_entry(entry):
    """Clean up a faculty entry."""
    text = entry['info']
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove JavaScript email protection text
    text = re.sub(r'This email address is being protected from spambots.*?view it\.', '', text)
    
    # Clean up common noise
    text = re.sub(r'\[.*?\]', '', text)  # Remove things in brackets
    text = re.sub(r'\(.*?\)', '', text)  # Remove things in parentheses
    
    return text.strip()


def scrape_department(dept_name, url):
    """Scrape a single department page."""
    print(f"\n📚 {dept_name}")
    print(f"   {url}")
    
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract faculty
        faculty = extract_faculty_from_page(soup, dept_name)
        
        # Clean entries
        cleaned_faculty = []
        seen = set()
        
        for entry in faculty:
            cleaned = clean_faculty_entry(entry)
            # Remove duplicates and very short entries
            if cleaned and len(cleaned) > 15 and cleaned not in seen:
                # Filter out navigation noise
                if not any(noise in cleaned.lower() for noise in [
                    'chancellor', 'vice-chancellor', 'registrar', 'finance officer',
                    'controller of examination', 'visitor', 'webmail', 'feedback'
                ]):
                    cleaned_faculty.append({
                        'info': cleaned,
                        'source': entry['source']
                    })
                    seen.add(cleaned)
        
        print(f"   ✅ Found {len(cleaned_faculty)} faculty members")
        return cleaned_faculty
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []


def main():
    """Main function to scrape all departments."""
    print("=" * 70)
    print("👨‍🏫 COMPREHENSIVE FACULTY SCRAPER - ALL DEPARTMENTS")
    print("=" * 70)
    
    all_data = []
    total_faculty = 0
    departments_with_faculty = 0
    
    for dept_name, url in DEPARTMENTS.items():
        faculty = scrape_department(dept_name, url)
        
        if faculty:
            all_data.append({
                'department': dept_name,
                'url': url,
                'faculty': faculty
            })
            total_faculty += len(faculty)
            departments_with_faculty += 1
        
        time.sleep(0.5)  # Be polite to server
    
    # Generate markdown
    print(f"\n{'=' * 70}")
    print("📝 Generating Faculty Database...")
    print(f"{'=' * 70}")
    
    md_content = ["# CUSB Complete Faculty Directory - All Departments\n\n"]
    md_content.append(f"**Total Departments:** {len(DEPARTMENTS)}\n\n")
    md_content.append(f"**Departments with Faculty Data:** {departments_with_faculty}\n\n")
    md_content.append(f"**Total Faculty Members Found:** {total_faculty}\n\n")
    md_content.append(f"**Scraped on:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    md_content.append("=" * 50 + "\n\n")
    
    # Summary table
    md_content.append("## Summary by Department\n\n")
    md_content.append("| Department | Faculty Count |\n")
    md_content.append("|------------|---------------|\n")
    for dept_data in all_data:
        md_content.append(f"| {dept_data['department']} | {len(dept_data['faculty'])} |\n")
    md_content.append("\n---\n\n")
    
    # Detailed faculty by department
    for dept_data in all_data:
        dept_name = dept_data['department']
        md_content.append(f"## 🎓 {dept_name}\n\n")
        md_content.append(f"**Department URL:** {dept_data['url']}\n\n")
        md_content.append(f"**Total Faculty:** {len(dept_data['faculty'])}\n\n")
        
        md_content.append("### Faculty Members\n\n")
        for idx, faculty in enumerate(dept_data['faculty'], 1):
            md_content.append(f"**{idx}.** {faculty['info']}\n\n")
        
        md_content.append("---\n\n")
    
    # Write output
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ Faculty Scraping Complete!")
    print(f"   Departments scraped: {len(DEPARTMENTS)}")
    print(f"   Departments with faculty: {departments_with_faculty}")
    print(f"   Total faculty found: {total_faculty}")
    print(f"   Output file: {OUTPUT_FILE}")
    print(f"   File size: {len(output_text)} characters")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
