"""
Direct syllabus scraper - uses known syllabus URLs from CUSB website.

This script scrapes syllabus content from department pages that have 
known PDF links for course structures and syllabi.

Usage: python src/scrape_syllabus_direct.py
"""

import re
import sys
import time
import io
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.cusb.ac.in"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_syllabus_complete.md"

# Known department syllabus page URLs (from CUSB website structure)
DEPARTMENT_SYLLABUS_URLS = {
    "Statistics & Data Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Computer Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Mathematics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Chemistry": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Physics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Biotechnology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Life Science": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Economics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Psychology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Commerce": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Geography": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Geology": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
    "Bioinformatics": "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31:department-of-bioinformatics&Itemid=136&catid=15",
}

# Department-specific syllabus path patterns (based on CUSB URL structure)
SYLLABUS_PATTERNS = {
    "Data Science & Statistics": {
        "base_path": "images/dept/statistics/syllabus",
        "files": [
            ("M.Sc Data Science Course Structure", "msc_data_science_course_structure.pdf"),
            ("M.Sc Data Science Syllabus", "msc_data_science_syllabus.pdf"),
            ("M.Sc Statistics Course Structure", "msc_statistics_course_structure.pdf"),
            ("M.Sc Statistics Syllabus", "msc_statistics_syllabus.pdf"),
            ("Integrated Statistics Syllabus", "integrated_statistics_syllabus.pdf"),
        ]
    },
    "Computer Science": {
        "base_path": "images/dept/computer_science/syllabus",
        "files": [
            ("M.Sc CS Course Structure", "course_structure_msc.pdf"),
            ("M.Sc CS Syllabus", "syllabus_msc_cs.pdf"),
            ("Integrated CS Course Structure", "integrated_cs_structure.pdf"),
            ("Integrated CS Syllabus", "integrated_cs_syllabus.pdf"),
        ]
    },
    "Mathematics": {
        "base_path": "images/dept/mathematics/syllabus",
        "files": [
            ("M.Sc Mathematics Course Structure", "course_structure_msc_maths.pdf"),
            ("M.Sc Mathematics Syllabus", "syllabus_msc_maths.pdf"),
            ("Integrated Mathematics Syllabus", "integrated_maths_syllabus.pdf"),
        ]
    },
    "Chemistry": {
        "base_path": "images/dept/chemistry/syllabus",
        "files": [
            ("M.Sc Chemistry Course Structure", "msc_chem_struct.pdf"),
            ("M.Sc Chemistry Syllabus", "syllabus_msc_chem.pdf"),
            ("Integrated Chemistry Syllabus", "integrated_syllabus.pdf"),
        ]
    },
    "Physics": {
        "base_path": "images/dept/physics/Syllabus",
        "files": [
            ("M.Sc Physics Course Structure", "course_structure_msc_physics.pdf"),
            ("M.Sc Physics Syllabus", "Syllabus_msc_physics.pdf"),
            ("Integrated Physics Syllabus", "Integrated_UG_PG_Syllabus_Physics.pdf"),
        ]
    },
    "Biotechnology": {
        "base_path": "images/dept/biotechonology/syllabus",
        "files": [
            ("M.Sc Biotechnology Course Structure", "structure_btn.pdf"),
            ("M.Sc Biotechnology Syllabus", "2020_NEP_Msc_Biotechnology_Syllabus.pdf"),
            ("PhD Biotechnology Syllabus", "syllabus_2023_PhD_Biotechnology.pdf"),
        ]
    },
    "Life Science": {
        "base_path": "images/dept/life_science/syllabus",
        "files": [
            ("M.Sc Life Science Course Structure", "NEP_Msc_lifesc_compressed.pdf"),
            ("M.Sc Life Science Syllabus", "NEP_Msc_lifesc_compressed.pdf"),
            ("Integrated Life Science Syllabus", "UGPGlsc_final_compressed.pdf"),
        ]
    },
    "Economics": {
        "base_path": "images/dept/eco_studies",
        "files": [
            ("M.A Economics Course Structure", "MA_Eco.pdf"),
            ("M.A Economics Syllabus", "Syllabus/MA_Economics_Syllabus_DESP_CUSB_Final.pdf"),
            ("Integrated Economics Syllabus", "Syllabus_Integ_eco-1-12.pdf"),
        ]
    },
    "Psychology": {
        "base_path": "images/dept/psychological_sciences/syllabus",
        "files": [
            ("M.A/M.Sc Psychology Course Structure", "pg_nep_structure_psy.pdf"),
            ("M.A/M.Sc Psychology Syllabus", "pg_nep_syllabus_psy.pdf"),
            ("Integrated Psychology Syllabus", "syllabus_5_years_ug_pg_psy.pdf"),
        ]
    },
    "Geography": {
        "base_path": "images/dept/geography/syllabus",
        "files": [
            ("M.A/M.Sc Geography Course Structure", "Structure_ma_geography.pdf"),
            ("M.A/M.Sc Geography Syllabus", "MA_MSc_Geography_Syllabus.pdf"),
            ("Integrated Geography Syllabus", "5_year_Integrated_UG_PG_Geography_Syllabus.pdf"),
        ]
    },
    "Geology": {
        "base_path": "images/dept/geology",
        "files": [
            ("M.Sc Geology Syllabus", "syllabus_msc_geology.pdf"),
        ]
    },
    "Commerce": {
        "base_path": "images/dept/commerce_bstudies/syllabus",
        "files": [
            ("M.Com Course Structure", "m_com_course_structure.pdf"),
            ("Integrated Commerce Course Structure", "integrated_course_str_mcom.pdf"),
            ("PhD Commerce Syllabus", "syllabus PhD_compressed.pdf"),
        ]
    },
    "Bioinformatics": {
        "base_path": "images/dept/bioinfo/syllabus",
        "files": [
            ("M.Sc Bioinformatics Course Structure", "msc_struct_new.pdf"),
            ("M.Sc Bioinformatics Syllabus", "msc_syllabus_new.pdf"),
        ]
    },
}


def extract_pdf_text(pdf_url: str) -> str:
    """Download PDF and extract text content."""
    if not PDF_SUPPORT:
        return ""
    
    try:
        print(f"    Downloading: {pdf_url[:70]}...")
        response = requests.get(pdf_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_content = []
        for page_num, page in enumerate(pdf_reader.pages[:5]):  # Limit to first 5 pages
            try:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            except Exception as e:
                continue
        
        full_text = "\n".join(text_content)
        
        # Clean up
        full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)
        full_text = re.sub(r' {2,}', ' ', full_text)
        
        # Truncate if too long
        if len(full_text) > 8000:
            full_text = full_text[:8000] + "\n\n[Content truncated...]"
        
        return full_text.strip()
        
    except Exception as e:
        print(f"    Error: {e}")
        return ""


def scrape_all_syllabus():
    """Scrape syllabus from all departments using known URL patterns."""
    print("=" * 70)
    print("📚 CUSB COMPLETE SYLLABUS SCRAPER")
    print("=" * 70)
    
    md_content = ["# CUSB All Departments - Complete Syllabus & Course Structure\n"]
    md_content.append(f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append("Source: Central University of South Bihar (cusb.ac.in)\n")
    md_content.append("=" * 50 + "\n\n")
    
    total_pdfs = 0
    successful_extractions = 0
    
    for dept_name, dept_info in SYLLABUS_PATTERNS.items():
        print(f"\n📖 Processing: {dept_name}")
        
        md_content.append(f"## 🎓 {dept_name} Department\n\n")
        
        base_path = dept_info["base_path"]
        files = dept_info["files"]
        
        dept_pdfs = 0
        
        for file_title, file_path in files:
            pdf_url = f"{BASE_URL}/{base_path}/{file_path}"
            
            md_content.append(f"### {file_title}\n")
            md_content.append(f"**PDF Download Link:** {pdf_url}\n\n")
            
            # Extract PDF content
            if PDF_SUPPORT:
                pdf_content = extract_pdf_text(pdf_url)
                
                if pdf_content:
                    md_content.append("**Syllabus Content:**\n")
                    md_content.append("```\n")
                    md_content.append(pdf_content)
                    md_content.append("\n```\n\n")
                    successful_extractions += 1
                    print(f"    ✅ Extracted: {file_title}")
                else:
                    md_content.append("*[PDF content not available - download link provided above]*\n\n")
                    print(f"    ⚠️ No content: {file_title}")
            else:
                md_content.append("*[Install PyPDF2 to extract PDF content]*\n\n")
            
            dept_pdfs += 1
            total_pdfs += 1
            time.sleep(0.3)  # Be polite to server
        
        md_content.append("---\n\n")
        print(f"  ✅ Processed {dept_pdfs} PDFs for {dept_name}")
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ Syllabus scraping complete!")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   Total PDFs: {total_pdfs}")
    print(f"   Successfully extracted: {successful_extractions}")
    print(f"   File size: {len(output_text)} characters")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    scrape_all_syllabus()
