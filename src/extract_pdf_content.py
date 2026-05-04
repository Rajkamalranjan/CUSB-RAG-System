"""
Extract content from syllabus PDFs and add to knowledge base.

This downloads PDF files and extracts text content for RAG.
"""

import re
import sys
import io
from pathlib import Path

import requests
import PyPDF2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.cusb.ac.in"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_syllabus_content.md"

# Priority PDFs to extract (most requested)
PRIORITY_PDFS = [
    # Data Science & Statistics
    ("M.Sc Data Science - Complete Syllabus", 
     "https://www.cusb.ac.in/images/dept/statistics/syllabus/msc_data_science_syllabus.pdf",
     "Data Science and Statistics Department"),
    ("M.Sc Data Science - Course Structure",
     "https://www.cusb.ac.in/images/dept/statistics/syllabus/msc_data_science_course_structure.pdf",
     "Data Science and Statistics Department"),
    ("M.Sc Statistics - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/statistics/syllabus/msc_statistics_syllabus.pdf",
     "Data Science and Statistics Department"),
    
    # Computer Science
    ("M.Sc Computer Science - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/computer_science/syllabus/syllabus_msc_cs.pdf",
     "Computer Science Department"),
    ("M.Sc Computer Science - Course Structure",
     "https://www.cusb.ac.in/images/dept/computer_science/syllabus/course_structure_msc.pdf",
     "Computer Science Department"),
    
    # Mathematics
    ("M.Sc Mathematics - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/mathematics/syllabus/syllabus_msc_maths.pdf",
     "Mathematics Department"),
    
    # Biotechnology
    ("M.Sc Biotechnology - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/biotechonology/syllabus/2020_NEP_Msc_Biotechnology_Syllabus.pdf",
     "Biotechnology Department"),
    
    # Life Science
    ("M.Sc Life Science - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/life_science/syllabus/NEP_Msc_lifesc_compressed.pdf",
     "Life Science Department"),
    
    # Chemistry
    ("M.Sc Chemistry - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/chemistry/syllabus/syllabus_msc_chem.pdf",
     "Chemistry Department"),
    
    # Physics
    ("M.Sc Physics - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/physics/Syllabus/Syllabus_msc_physics.pdf",
     "Physics Department"),
    
    # Geography
    ("M.A/M.Sc Geography - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/geography/syllabus/MA_MSc_Geography_Syllabus.pdf",
     "Geography Department"),
    ("Integrated Geography - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/geography/syllabus/5_year_Integrated_UG_PG_Geography_Syllabus.pdf",
     "Geography Department"),
    
    # Psychology
    ("M.A/M.Sc Psychology - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/psychological_sciences/syllabus/pg_nep_syllabus_psy.pdf",
     "Psychological Sciences Department"),
    
    # Economics
    ("M.A Economics - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/eco_studies/Syllabus/MA_Economics_Syllabus_DESP_CUSB_Final.pdf",
     "Economic Studies Department"),
    
    # Commerce
    ("M.Com - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/commerce_bstudies/syllabus/syllabus%20PhD_compressed.pdf",
     "Commerce and Business Studies Department"),
    
    # Bioinformatics
    ("M.Sc Bioinformatics - Complete Syllabus",
     "https://www.cusb.ac.in/images/dept/bioinfo/syllabus/msc_syllabus_new.pdf",
     "Bioinformatics Department"),
]


def extract_pdf_content(pdf_url: str, title: str) -> str:
    """Download PDF and extract text content."""
    try:
        print(f"  Downloading: {title}")
        response = requests.get(pdf_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text_content = []
        total_pages = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_content.append(f"--- Page {page_num + 1} ---\n{page_text.strip()}")
            except Exception as e:
                print(f"    Warning: Page {page_num + 1} extraction failed: {e}")
                continue
        
        full_text = "\n\n".join(text_content)
        
        # Clean up the text
        full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)  # Remove excessive newlines
        full_text = re.sub(r' {2,}', ' ', full_text)  # Remove multiple spaces
        full_text = re.sub(r'\t+', ' ', full_text)  # Replace tabs with spaces
        
        print(f"    ✅ Extracted {total_pages} pages, {len(full_text)} characters")
        
        return full_text.strip()
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return ""


def main():
    """Extract content from all priority PDFs."""
    print("=" * 70)
    print("📚 EXTRACTING PDF CONTENT FOR RAG KNOWLEDGE BASE")
    print("=" * 70)
    
    md_content = ["# CUSB Syllabus - Complete Content (Extracted from PDFs)\n\n"]
    md_content.append(f"Total Syllabi: {len(PRIORITY_PDFS)}\n")
    md_content.append("=" * 50 + "\n\n")
    
    successful = 0
    failed = 0
    
    for title, pdf_url, department in PRIORITY_PDFS:
        print(f"\n📖 {title}")
        print(f"   URL: {pdf_url}")
        
        # Extract content
        content = extract_pdf_content(pdf_url, title)
        
        if content and len(content) > 100:
            md_content.append(f"## 🎓 {title}\n\n")
            md_content.append(f"**Department:** {department}\n\n")
            md_content.append(f"**PDF Download Link:** {pdf_url}\n\n")
            md_content.append("**Complete Syllabus Content:**\n\n")
            md_content.append("```\n")
            md_content.append(content)
            md_content.append("\n```\n\n")
            md_content.append("---\n\n")
            successful += 1
        else:
            # Add entry with just link if extraction failed
            md_content.append(f"## 🎓 {title}\n\n")
            md_content.append(f"**Department:** {department}\n\n")
            md_content.append(f"**PDF Download Link:** {pdf_url}\n\n")
            md_content.append("*[PDF content extraction failed - please download using link above]*\n\n")
            md_content.append("---\n\n")
            failed += 1
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ PDF Content Extraction Complete!")
    print(f"   Successfully extracted: {successful}/{len(PRIORITY_PDFS)}")
    print(f"   Failed: {failed}/{len(PRIORITY_PDFS)}")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   File size: {len(output_text)} characters")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
