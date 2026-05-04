"""
Comprehensive syllabus scraper for all CUSB departments.

This script:
1. Discovers all department pages
2. Finds syllabus/course structure PDF links
3. Downloads PDFs and extracts text content
4. Creates structured markdown with both content and links

Usage: python src/scrape_syllabus.py
"""

import re
import sys
import time
import io
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Try to import PyPDF2 for PDF extraction
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF content extraction disabled.")
    print("Install with: pip install PyPDF2")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.cusb.ac.in"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_syllabus.md"

# All CUSB departments with their possible URL patterns
DEPARTMENTS = [
    # School of Earth, Biological & Environmental Sciences
    {"name": "Bioinformatics", "keywords": ["bioinformatics", "bioinfo"], "syllabus_patterns": ["syllabus", "course_structure", "bos", "botechonology"]},
    {"name": "Geology", "keywords": ["geology"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Geography", "keywords": ["geography"], "syllabus_patterns": ["syllabus", "structure", "bos", "geography"]},
    {"name": "Life Science", "keywords": ["life_science", "lifesc", "life-science"], "syllabus_patterns": ["syllabus", "structure", "bos", "life"]},
    {"name": "Biotechnology", "keywords": ["biotechnology", "biotechonology", "biotech", "btn"], "syllabus_patterns": ["syllabus", "structure", "bos", "biotech"]},
    {"name": "Environmental Science", "keywords": ["environmental", "env_science"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    
    # School of Social Sciences & Policies
    {"name": "Historical Studies", "keywords": ["history", "historical"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Economic Studies", "keywords": ["economics", "eco_studies"], "syllabus_patterns": ["syllabus", "structure", "bos", "eco"]},
    {"name": "Development Studies", "keywords": ["development"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Political Studies", "keywords": ["political", "pol_science"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Sociological Studies", "keywords": ["sociology", "sociological"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Library & Information Science", "keywords": ["library", "lib"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    
    # School of Mathematics, Statistics & Computer Science
    {"name": "Mathematics", "keywords": ["mathematics", "math"], "syllabus_patterns": ["syllabus", "structure", "bos", "maths"]},
    {"name": "Statistics", "keywords": ["statistics", "stat"], "syllabus_patterns": ["syllabus", "structure", "bos", "data_science"]},
    {"name": "Computer Science", "keywords": ["computer_science", "cs"], "syllabus_patterns": ["syllabus", "structure", "bos", "cs"]},
    
    # School of Education
    {"name": "Teacher Education", "keywords": ["teacher_education", "bed", "b_ed"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Physical Education", "keywords": ["physical_education", "ped"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    
    # School of Physical & Chemical Sciences
    {"name": "Chemistry", "keywords": ["chemistry", "chem"], "syllabus_patterns": ["syllabus", "structure", "bos", "chem"]},
    {"name": "Physics", "keywords": ["physics", "phy"], "syllabus_patterns": ["syllabus", "structure", "bos", "phy"]},
    
    # School of Languages & Literature
    {"name": "English", "keywords": ["english"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Indian Languages", "keywords": ["hindi", "indian_languages", "sanskrit"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    
    # Other Schools
    {"name": "Mass Communication", "keywords": ["mass_comm", "media", "journalism"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Commerce & Business Studies", "keywords": ["commerce", "business", "mcom", "bcom"], "syllabus_patterns": ["syllabus", "structure", "bos", "commerce"]},
    {"name": "Psychological Sciences", "keywords": ["psychology", "psy"], "syllabus_patterns": ["syllabus", "structure", "bos", "psy"]},
    {"name": "Law & Governance", "keywords": ["law", "llb", "llm"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Pharmacy", "keywords": ["pharmacy", "pharma"], "syllabus_patterns": ["syllabus", "structure", "bos"]},
    {"name": "Agriculture", "keywords": ["agriculture", "agri"], "syllabus_patterns": ["syllabus", "structure", "bos", "agri"]},
]


def extract_pdf_text(pdf_url: str) -> str:
    """Download PDF and extract text content."""
    if not PDF_SUPPORT:
        return "[PDF content extraction not available - install PyPDF2]"
    
    try:
        # Build full URL if needed
        if pdf_url.startswith('/'):
            pdf_url = BASE_URL + pdf_url
        
        print(f"  Downloading PDF: {pdf_url[:80]}...")
        response = requests.get(pdf_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Extract text using PyPDF2
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_content = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
            except Exception as e:
                print(f"    Warning: Could not extract page {page_num + 1}: {e}")
                continue
        
        full_text = "\n\n".join(text_content)
        
        # Clean up the text
        full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)  # Remove excessive newlines
        full_text = re.sub(r' {2,}', ' ', full_text)  # Remove multiple spaces
        
        # Limit text length to avoid huge chunks
        if len(full_text) > 10000:
            full_text = full_text[:10000] + "\n\n[Content truncated due to length...]"
        
        return full_text.strip()
        
    except Exception as e:
        print(f"  Error extracting PDF {pdf_url}: {e}")
        return f"[PDF extraction failed: {str(e)}]"


def find_department_pages():
    """Find all department pages from the CUSB website."""
    print("\n🔍 Discovering department pages...")
    
    try:
        response = requests.get(f"{BASE_URL}/index.php", timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links
        department_links = {}
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True).lower()
            
            # Build full URL
            if href.startswith('/'):
                full_url = BASE_URL + href
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = f"{BASE_URL}/{href}"
            
            # Check if this matches any department
            for dept in DEPARTMENTS:
                dept_name = dept["name"].lower()
                keywords = dept["keywords"]
                
                # Match by keyword in URL or text
                matches = any(kw.lower() in href.lower() or kw.lower() in text for kw in keywords)
                matches = matches or dept_name in text
                
                if matches:
                    if dept["name"] not in department_links:
                        department_links[dept["name"]] = {
                            "url": full_url,
                            "keywords": dept["keywords"],
                            "syllabus_patterns": dept["syllabus_patterns"]
                        }
                        print(f"  Found: {dept['name']} -> {full_url}")
                    break
        
        print(f"✅ Found {len(department_links)} department pages")
        return department_links
        
    except Exception as e:
        print(f"Error finding department pages: {e}")
        return {}


def find_syllabus_pdfs(dept_info: dict) -> list[dict]:
    """Find syllabus PDF links on a department page."""
    dept_url = dept_info["url"]
    patterns = dept_info.get("syllabus_patterns", ["syllabus", "structure", "bos"])
    
    print(f"\n📄 Scanning {dept_info.get('name', 'Unknown')}...")
    
    try:
        response = requests.get(dept_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        syllabus_links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True)
            
            # Only process PDF links
            if not href.lower().endswith('.pdf'):
                continue
            
            # Check if this matches syllabus patterns
            href_lower = href.lower()
            text_lower = text.lower()
            
            is_syllabus = any(p in href_lower or p in text_lower for p in patterns)
            is_syllabus = is_syllabus or any(word in text_lower for word in 
                ["syllabus", "course structure", "bos", "board of studies", "curriculum", "course", "structure"])
            
            if is_syllabus:
                # Build full URL
                if href.startswith('/'):
                    full_url = BASE_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(dept_url, href)
                
                # Determine course type from text
                course_type = "Unknown"
                if any(x in text_lower for x in ["integrated", "ug-pg", "5 year", "5-year"]):
                    course_type = "Integrated UG-PG"
                elif any(x in text_lower for x in ["m.sc", "msc", "m.a", "ma ", "pg", "postgraduate"]):
                    course_type = "Masters (PG)"
                elif any(x in text_lower for x in ["phd", "ph.d", "doctorate", "doctoral"]):
                    course_type = "PhD"
                elif any(x in text_lower for x in ["b.sc", "bsc", "b.a", "ba ", "ug", "undergraduate"]):
                    course_type = "Bachelors (UG)"
                elif any(x in text_lower for x in ["bos", "board of studies"]):
                    course_type = "Board of Studies"
                
                syllabus_links.append({
                    "title": text,
                    "url": full_url,
                    "type": course_type
                })
                print(f"    ✅ {text[:50]} -> {course_type}")
        
        return syllabus_links
        
    except Exception as e:
        print(f"  Error scanning {dept_url}: {e}")
        return []


def scrape_all_syllabus():
    """Main function to scrape all syllabus data."""
    print("=" * 70)
    print("📚 CUSB ALL DEPARTMENTS SYLLABUS SCRAPER")
    print("=" * 70)
    
    # Find department pages
    departments = find_department_pages()
    
    if not departments:
        print("❌ No department pages found")
        return
    
    # Find syllabus PDFs for each department
    all_syllabus_data = []
    
    for dept_name, dept_info in departments.items():
        syllabus_links = find_syllabus_pdfs({"name": dept_name, **dept_info})
        
        if syllabus_links:
            all_syllabus_data.append({
                "department": dept_name,
                "url": dept_info["url"],
                "syllabus_files": syllabus_links
            })
        
        time.sleep(0.5)  # Be polite to server
    
    # Generate markdown output
    print("\n📝 Generating markdown output...")
    
    md_content = ["# CUSB All Departments Syllabus and Course Structure\n"]
    md_content.append(f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append("-" * 50 + "\n\n")
    
    # Summary table
    md_content.append("## 📊 Summary - All Departments\n")
    md_content.append("| Department | Syllabus Files |\n")
    md_content.append("|------------|----------------|\n")
    for dept_data in all_syllabus_data:
        md_content.append(f"| {dept_data['department']} | {len(dept_data['syllabus_files'])} |\n")
    md_content.append("\n---\n\n")
    
    # Detailed content for each department
    for dept_data in all_syllabus_data:
        dept_name = dept_data["department"]
        dept_url = dept_data["url"]
        
        md_content.append(f"## 🎓 {dept_name}\n")
        md_content.append(f"**Department URL:** {dept_url}\n\n")
        
        # Group by course type
        by_type = {}
        for syl in dept_data["syllabus_files"]:
            t = syl["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(syl)
        
        for course_type, files in by_type.items():
            md_content.append(f"### {course_type} Programs\n\n")
            
            for syl in files:
                title = syl["title"]
                url = syl["url"]
                
                md_content.append(f"#### {title}\n")
                md_content.append(f"**Download Link:** {url}\n\n")
                
                # Extract and add PDF content
                if PDF_SUPPORT:
                    print(f"\n  📖 Extracting content from: {title[:40]}...")
                    pdf_content = extract_pdf_text(url)
                    
                    if pdf_content and not pdf_content.startswith("["):
                        md_content.append("**Syllabus Content (Extracted):**\n")
                        md_content.append("```\n")
                        md_content.append(pdf_content)
                        md_content.append("\n```\n\n")
                    else:
                        md_content.append("*[PDF content extraction pending or failed]*\n\n")
                else:
                    md_content.append("*[PDF content: Install PyPDF2 to extract content]*\n\n")
            
            md_content.append("\n---\n\n")
        
        md_content.append("\n---\n\n")
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n✅ Scraped syllabus data saved to: {OUTPUT_FILE}")
    print(f"   Departments: {len(all_syllabus_data)}")
    total_files = sum(len(d['syllabus_files']) for d in all_syllabus_data)
    print(f"   Total Syllabus Files: {total_files}")
    print(f"   File size: {len(output_text)} characters")


if __name__ == "__main__":
    scrape_all_syllabus()
