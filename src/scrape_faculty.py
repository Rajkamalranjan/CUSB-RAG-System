"""
Comprehensive faculty scraper for all CUSB departments.

This script scrapes faculty information from all department pages including:
- Faculty names, designations, qualifications
- Contact information (email, phone)
- Research areas and specializations
- Profile links

Usage: python src/scrape_faculty.py
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
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_faculty.md"

# All CUSB Departments with their URLs
DEPARTMENTS = {
    # School of Earth, Biological & Environmental Sciences
    "Bioinformatics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31&Itemid=136",
    "Geology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=29&Itemid=128",
    "Geography": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=46&Itemid=158",
    "Life Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=35&Itemid=144",
    "Biotechnology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=32&Itemid=137",
    "Environmental Sciences": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=30&Itemid=129",
    
    # Social Sciences and Policies
    "Historical Studies and Archaeology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=50&Itemid=162",
    "Economic Studies and Policy": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=45&Itemid=157",
    "Development Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=47&Itemid=159",
    "Political Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=48&Itemid=160",
    "Sociological Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=49&Itemid=161",
    "Library and Information Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=55&Itemid=169",
    
    # Mathematics, Statistics and Computer Science
    "Mathematics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=56&Itemid=170",
    "Statistics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=57&Itemid=171",
    "Computer Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31&Itemid=136",
    
    # School of Education
    "Teacher Education": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=41&Itemid=151",
    "Physical Education": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=42&Itemid=152",
    
    # Physical & Chemical Sciences
    "Chemistry": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=39&Itemid=148",
    "Physics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=40&Itemid=149",
    
    # Languages & Literature
    "English": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=143&Itemid=167",
    "Indian Languages": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=53&Itemid=168",
    
    # Media, Arts & Aesthetics
    "Mass Communication": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=139&Itemid=163",
    
    # School of Management
    "Commerce and Business Studies": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=141&Itemid=165",
    
    # Human Sciences
    "Psychological Sciences": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=38&Itemid=146",
    
    # Law and Governance
    "Law and Governance": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=43&Itemid=154",
    
    # Health Science
    "Pharmacy": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=37&Itemid=138",
    
    # Agriculture & Development
    "Agriculture": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=44&Itemid=155",
}


def extract_faculty_info(soup, dept_name):
    """Extract faculty information from department page."""
    faculty_list = []
    
    # Look for faculty tables, lists, or sections
    # Common patterns in academic websites
    
    # Try to find faculty in tables
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                text = ' '.join([cell.get_text(strip=True) for cell in cells])
                # Look for professor/assistant professor/associate professor
                if any(title in text.lower() for title in ['professor', 'lecturer', 'reader', 'head', 'coordinator']):
                    faculty_list.append({
                        'info': text,
                        'type': 'table'
                    })
    
    # Look for faculty in lists
    lists = soup.find_all(['ul', 'ol'])
    for lst in lists:
        items = lst.find_all('li')
        for item in items:
            text = item.get_text(strip=True)
            if any(title in text.lower() for title in ['professor', 'lecturer', 'reader', 'head', 'coordinator']):
                if len(text) > 20:  # Filter out short items
                    faculty_list.append({
                        'info': text,
                        'type': 'list'
                    })
    
    # Look for specific faculty sections
    faculty_sections = soup.find_all(['div', 'section', 'article'], class_=lambda x: x and any(
        keyword in str(x).lower() for keyword in ['faculty', 'staff', 'teacher', 'professor', 'people']))
    
    for section in faculty_sections:
        text = section.get_text(separator='\n', strip=True)
        if text and len(text) > 50:
            faculty_list.append({
                'info': text,
                'type': 'section'
            })
    
    # Look for headings with faculty names
    headings = soup.find_all(['h2', 'h3', 'h4', 'h5'])
    for heading in headings:
        text = heading.get_text(strip=True)
        if any(title in text.lower() for title in ['professor', 'lecturer', 'head', 'coordinator']):
            # Get following content
            next_elem = heading.find_next_sibling()
            content = text
            if next_elem:
                content += '\n' + next_elem.get_text(strip=True)
            faculty_list.append({
                'info': content,
                'type': 'heading'
            })
    
    return faculty_list


def clean_faculty_text(text):
    """Clean and format faculty information."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove JavaScript email protection
    text = re.sub(r'This email address is being protected from spambots.*?view it\.', '[Email Protected]', text)
    # Clean up phone numbers
    text = re.sub(r'(\d{5,})\s*(\d+)', r'\1 \2', text)
    return text.strip()


def scrape_department_faculty(dept_name, dept_url):
    """Scrape faculty from a single department."""
    print(f"\n📚 Scraping: {dept_name}")
    print(f"   URL: {dept_url}")
    
    try:
        response = requests.get(dept_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract faculty info
        faculty_list = extract_faculty_info(soup, dept_name)
        
        if not faculty_list:
            # Try to get any content if no faculty found
            main_content = soup.find('div', class_='item-page') or soup.find('article') or soup.find('main')
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
                # Look for faculty-related content
                if any(keyword in text.lower() for keyword in ['professor', 'faculty', 'head', 'department']):
                    faculty_list.append({
                        'info': text[:3000],  # Limit content
                        'type': 'general'
                    })
        
        print(f"   ✅ Found {len(faculty_list)} faculty entries")
        return faculty_list
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []


def scrape_all_faculty():
    """Scrape faculty from all departments."""
    print("=" * 70)
    print("👨‍🏫 CUSB ALL DEPARTMENTS FACULTY SCRAPER")
    print("=" * 70)
    
    all_faculty_data = []
    total_faculty = 0
    
    for dept_name, dept_url in DEPARTMENTS.items():
        faculty_list = scrape_department_faculty(dept_name, dept_url)
        
        if faculty_list:
            all_faculty_data.append({
                'department': dept_name,
                'url': dept_url,
                'faculty': faculty_list
            })
            total_faculty += len(faculty_list)
        
        time.sleep(0.5)  # Be polite to server
    
    # Generate markdown
    print("\n📝 Generating faculty database...")
    
    md_content = ["# CUSB Faculty Directory - All Departments\n\n"]
    md_content.append(f"Total Departments: {len(all_faculty_data)}\n")
    md_content.append(f"Total Faculty Entries: {total_faculty}\n")
    md_content.append(f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append("=" * 50 + "\n\n")
    
    # Summary table
    md_content.append("## 📊 Faculty Summary by Department\n\n")
    md_content.append("| Department | Faculty Count |\n")
    md_content.append("|------------|---------------|\n")
    for dept_data in all_faculty_data:
        md_content.append(f"| {dept_data['department']} | {len(dept_data['faculty'])} |\n")
    md_content.append("\n---\n\n")
    
    # Detailed faculty by department
    for dept_data in all_faculty_data:
        dept_name = dept_data['department']
        dept_url = dept_data['url']
        
        md_content.append(f"## 🎓 {dept_name}\n\n")
        md_content.append(f"**Department Page:** {dept_url}\n\n")
        
        if dept_data['faculty']:
            md_content.append("### Faculty Members\n\n")
            
            for idx, faculty in enumerate(dept_data['faculty'], 1):
                info = clean_faculty_text(faculty['info'])
                if info and len(info) > 10:
                    md_content.append(f"**{idx}.** {info}\n\n")
        else:
            md_content.append("*Faculty information not available on public page*\n\n")
        
        md_content.append("---\n\n")
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ Faculty scraping complete!")
    print(f"   Departments: {len(all_faculty_data)}")
    print(f"   Total Faculty Entries: {total_faculty}")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   File size: {len(output_text)} characters")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    scrape_all_faculty()
