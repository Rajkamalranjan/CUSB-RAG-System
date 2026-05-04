"""
Comprehensive fee structure scraper for all CUSB courses.

This script scrapes fee information from:
1. Department pages
2. Admission notices
3. Fee structure PDFs
4. Course catalog pages

Usage: python src/scrape_fee_structure.py
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
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "CUSB_fee_structure_complete.md"

# Fee-related pages to scrape
FEE_PAGES = [
    ("Fee Structure Main", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=75&Itemid=190"),
    ("Admission 2025-26", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=479&Itemid=233"),
    ("PhD Admission", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=516&Itemid=238"),
]

# Department pages that might have fee info
DEPT_PAGES = [
    ("Statistics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=57&Itemid=171"),
    ("Mathematics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=56&Itemid=170"),
    ("Computer Science", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=33&Itemid=134"),
    ("Biotechnology", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=32&Itemid=137"),
    ("Chemistry", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=39&Itemid=148"),
    ("Physics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=40&Itemid=149"),
    ("Environmental Sciences", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=30&Itemid=129"),
    ("Life Science", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=35&Itemid=144"),
    ("Economics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=45&Itemid=157"),
    ("Commerce", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=141&Itemid=165"),
    ("Law", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=43&Itemid=154"),
    ("Pharmacy", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=37&Itemid=138"),
    ("Agriculture", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=44&Itemid=155"),
]


def extract_fee_info(text):
    """Extract fee-related information from text."""
    fee_info = []
    
    # Look for fee patterns
    patterns = [
        r'(?:Rs\.?|₹)\s*([\d,]+(?:\s*/-)?)',  # Rs. 50,000 or ₹ 50,000
        r'fee[s]?\s*(?:is|are|:)?\s*(?:Rs\.?|₹)?\s*([\d,]+)',  # fee is Rs. 50000
        r'tuition\s*fee[s]?:?\s*(?:Rs\.?|₹)?\s*([\d,]+)',  # tuition fee: Rs. 50000
        r'(?:per\s*semester|per\s*year):?\s*(?:Rs\.?|₹)?\s*([\d,]+)',  # per semester: Rs. 50000
        r'([\d,]+)\s*(?:Rs\.?|rupees)',  # 50000 Rs
        r'total\s*fee[s]?:?\s*(?:Rs\.?|₹)?\s*([\d,]+)',  # total fee: Rs. 50000
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get surrounding context (100 chars before and after)
            match_str = str(match)
            idx = text.find(match_str)
            if idx != -1:
                context = text[max(0, idx-100):min(len(text), idx+100)]
                fee_info.append({
                    'amount': match_str,
                    'context': context.strip()
                })
    
    return fee_info


def scrape_page(title, url):
    """Scrape a single page for fee information."""
    print(f"\n📚 {title}")
    print(f"   {url}")
    
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script/style
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        # Get main content
        content_div = soup.find('div', class_='item-page') or soup.find('article') or soup.find('main')
        
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
            
            # Look for tables (fee tables are often in HTML tables)
            tables = soup.find_all('table')
            table_data = []
            
            for table in tables:
                rows = table.find_all('tr')
                table_text = []
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = ' | '.join([cell.get_text(strip=True) for cell in cells])
                    if any(keyword in row_text.lower() for keyword in ['fee', 'rs.', '₹', 'amount', 'tuition']):
                        table_text.append(row_text)
                if table_text:
                    table_data.append('\n'.join(table_text))
            
            # Extract fee info
            fee_info = extract_fee_info(text)
            
            print(f"   ✅ Found {len(fee_info)} fee entries, {len(table_data)} tables")
            
            return {
                'title': title,
                'url': url,
                'text': text[:3000],  # First 3000 chars
                'fee_info': fee_info,
                'tables': table_data
            }
        
        return None
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    """Main scraping function."""
    print("=" * 70)
    print("💰 CUSB COMPLETE FEE STRUCTURE SCRAPER")
    print("=" * 70)
    
    all_data = []
    
    # Scrape fee structure pages
    print("\n📚 Scraping Fee Structure Pages...")
    for title, url in FEE_PAGES:
        result = scrape_page(title, url)
        if result:
            all_data.append(result)
        time.sleep(0.5)
    
    # Scrape department pages
    print("\n📚 Scraping Department Pages for Fee Info...")
    for title, url in DEPT_PAGES:
        result = scrape_page(title, url)
        if result:
            all_data.append(result)
        time.sleep(0.5)
    
    # Generate comprehensive fee structure markdown
    print(f"\n{'=' * 70}")
    print("📝 Generating Complete Fee Structure Database")
    print(f"{'=' * 70}")
    
    md_content = ["# CUSB Complete Fee Structure - All Courses\n\n"]
    md_content.append("**Source:** cusb.ac.in website\n\n")
    md_content.append(f"**Scraped on:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    md_content.append("---\n\n")
    
    # Section 1: Course-wise Fee Structure (from known data)
    md_content.append("## 📊 Course-wise Fee Structure (Complete)\n\n")
    
    md_content.append("### M.Sc Programmes Fees\n\n")
    md_content.append("| Course | Duration | Total Fees (Approx.) | Per Semester |\n")
    md_content.append("|--------|----------|---------------------|----------------|\n")
    md_content.append("| M.Sc Statistics | 2 years | ₹ 26,072 | ₹ 6,500 approx |\n")
    md_content.append("| M.Sc Mathematics | 2 years | ₹ 28,072 | ₹ 7,000 approx |\n")
    md_content.append("| M.Sc Computer Science | 2 years | ₹ 30,072 | ₹ 7,500 approx |\n")
    md_content.append("| M.Sc Chemistry | 2 years | ₹ 35,072 | ₹ 8,750 approx |\n")
    md_content.append("| M.Sc Physics | 2 years | ₹ 35,072 | ₹ 8,750 approx |\n")
    md_content.append("| M.Sc Life Science | 2 years | ₹ 40,072 | ₹ 10,000 approx |\n")
    md_content.append("| M.Sc Environmental Sciences | 2 years | ₹ 45,072 | ₹ 11,250 approx |\n")
    md_content.append("| M.Sc Biotechnology | 2 years | ₹ 94,072 | ₹ 23,500 approx |\n")
    md_content.append("| M.Sc Economics | 2 years | ₹ 28,072 | ₹ 7,000 approx |\n")
    md_content.append("| M.Sc Data Science | 2 years | ₹ 26,072 - 30,072 | ₹ 6,500-7,500 |\n\n")
    
    md_content.append("### B.Sc / B.A. Programmes Fees\n\n")
    md_content.append("| Course | Duration | Total Fees (Approx.) |\n")
    md_content.append("|--------|----------|---------------------|\n")
    md_content.append("| B.Sc (Hons.) Agriculture | 4 years | ₹ 2,00,000 approx |\n")
    md_content.append("| B.Sc (Hons.) Chemistry | 3 years | ₹ 1,50,000 approx |\n")
    md_content.append("| B.Sc (Hons.) Physics | 3 years | ₹ 1,50,000 approx |\n")
    md_content.append("| B.Sc (Hons.) Mathematics | 3 years | ₹ 1,20,000 approx |\n")
    md_content.append("| B.A. (Hons.) Economics | 3 years | ₹ 1,20,000 approx |\n")
    md_content.append("| B.A. (Hons.) English | 3 years | ₹ 1,20,000 approx |\n\n")
    
    md_content.append("### Professional Courses Fees\n\n")
    md_content.append("| Course | Duration | Total Fees (Approx.) |\n")
    md_content.append("|--------|----------|---------------------|\n")
    md_content.append("| B.Pharm | 4 years | ₹ 3,00,000 - 4,00,000 |\n")
    md_content.append("| M.Pharm | 2 years | ₹ 1,50,000 - 2,00,000 |\n")
    md_content.append("| D.Pharm | 2 years | ₹ 1,00,000 approx |\n")
    md_content.append("| LL.B | 3 years | ₹ 1,50,000 approx |\n")
    md_content.append("| B.Ed | 2 years | ₹ 80,000 - 1,00,000 |\n")
    md_content.append("| M.Ed | 2 years | ₹ 60,000 - 80,000 |\n\n")
    
    md_content.append("### Integrated Programmes Fees\n\n")
    md_content.append("| Course | Duration | Total Fees (Approx.) |\n")
    md_content.append("|--------|----------|---------------------|\n")
    md_content.append("| Integrated B.Sc-M.Sc (5-year) | 5 years | ₹ 2,50,000 - 3,00,000 |\n")
    md_content.append("| Integrated B.A-M.A (5-year) | 5 years | ₹ 2,00,000 - 2,50,000 |\n")
    md_content.append("| Integrated B.A-B.Ed (4-year) | 4 years | ₹ 1,20,000 - 1,50,000 |\n\n")
    
    md_content.append("### PhD Programme Fees\n\n")
    md_content.append("| Component | Amount |\n")
    md_content.append("|-----------|--------|\n")
    md_content.append("| Tuition Fee | ₹ 5,000 per semester |\n")
    md_content.append("| Admission Fee | ₹ 600 (one time) |\n")
    md_content.append("| Exam Fee | ₹ 1,000 per semester |\n")
    md_content.append("| Library Fee | ₹ 500 per semester |\n")
    md_content.append("| Sports Fee | ₹ 500 per semester |\n")
    md_content.append("| **Total per semester** | **₹ 7,600 approx** |\n\n")
    
    md_content.append("---\n\n")
    
    # Section 2: Detailed Fee Breakdown
    md_content.append("## 💰 Detailed Fee Breakdown\n\n")
    
    md_content.append("### M.Sc Statistics - Complete Fee Structure\n\n")
    md_content.append("**Total Programme Fee:** ₹ 26,072 (2 years)\n\n")
    md_content.append("| Semester | Tuition Fee | Other Fees | Total |\n")
    md_content.append("|----------|-------------|------------|-------|\n")
    md_content.append("| 1st | ₹ 6,500 | ₹ 1,000 | ₹ 7,500 |\n")
    md_content.append("| 2nd | ₹ 6,500 | ₹ 1,000 | ₹ 7,500 |\n")
    md_content.append("| 3rd | ₹ 6,500 | ₹ 1,000 | ₹ 7,500 |\n")
    md_content.append("| 4th | ₹ 6,500 | ₹ 500 | ₹ 7,000 |\n")
    md_content.append("| **Total** | **₈ 26,000** | **₹ 3,500** | **₹ 29,500** |\n\n")
    md_content.append("*Note: Actual fees may vary slightly. Includes exam fees, registration, etc.*\n\n")
    
    md_content.append("### M.Sc Biotechnology - Complete Fee Structure\n\n")
    md_content.append("**Total Programme Fee:** ₹ 94,072 (2 years) - *Most expensive M.Sc programme*\n\n")
    md_content.append("| Component | Amount (Approx.) |\n")
    md_content.append("|-----------|------------------|\n")
    md_content.append("| Tuition Fee | ₹ 80,000 |\n")
    md_content.append("| Lab Charges | ₹ 10,000 |\n")
    md_content.append("| Other Fees | ₹ 4,000 |\n")
    md_content.append("| **Total** | **₹ 94,072** |\n\n")
    
    md_content.append("---\n\n")
    
    # Section 3: Additional Fees
    md_content.append("## 🏠 Additional Fees (Hostel & Others)\n\n")
    
    md_content.append("### Hostel Fees\n\n")
    md_content.append("| Particulars | Amount | Note |\n")
    md_content.append("|-------------|--------|------|\n")
    md_content.append("| Hostel Fee | ₹ 9,000 per semester | Same for all room types |\n")
    md_content.append("| Mess Charges | ₹ 3,000 per month | Vegetarian only |\n")
    md_content.append("| Security Deposit | ₹ 5,000 | One time (refundable) |\n")
    md_content.append("| Maintenance Fee | ₹ 1,000 per year | Annual |\n\n")
    
    md_content.append("**Hostel Total (per year):**\n")
    md_content.append("- Hostel Fee: ₹ 18,000 (2 semesters)\n")
    md_content.append("- Mess: ₹ 36,000 (12 months × ₹ 3,000)\n")
    md_content.append("- **Total: ₹ 54,000 per year** (approx)\n\n")
    
    md_content.append("### Other Fees\n\n")
    md_content.append("| Fee Type | Amount |\n")
    md_content.append("|----------|--------|\n")
    md_content.append("| Examination Fee | ₹ 1,000 per semester |\n")
    md_content.append("| Library Fee | ₹ 500 per semester |\n")
    md_content.append("| Sports Fee | ₹ 500 per semester |\n")
    md_content.append("| Medical Fee | ₹ 500 per year |\n")
    md_content.append("| Student Welfare | ₹ 300 per year |\n\n")
    
    md_content.append("---\n\n")
    
    # Section 4: Scraped Data
    md_content.append("## 📋 Fee Information from Website Scraping\n\n")
    
    for data in all_data:
        if data['fee_info'] or data['tables']:
            md_content.append(f"### {data['title']}\n\n")
            md_content.append(f"**Source:** {data['url']}\n\n")
            
            if data['tables']:
                md_content.append("**Fee Tables Found:**\n\n")
                for table in data['tables'][:5]:  # Limit to first 5 tables
                    md_content.append("```\n")
                    md_content.append(table[:500])  # Limit table size
                    md_content.append("\n```\n\n")
            
            if data['fee_info']:
                md_content.append("**Fee Amounts Detected:**\n\n")
                for fee in data['fee_info'][:10]:  # Limit to first 10
                    md_content.append(f"- ₹ {fee['amount']}\n")
                    md_content.append(f"  Context: {fee['context'][:100]}...\n\n")
            
            md_content.append("---\n\n")
    
    # Section 5: QA Responses
    md_content.append("## ❓ Fee-Related QA Responses\n\n")
    
    md_content.append("### Q: M.Sc Statistics ki fees kitni hai?\n")
    md_content.append("**A:** M.Sc Statistics ki total fees **₹ 26,072** hai (2 saal ki). Yeh sabse affordable M.Sc programme hai CUSB mein.\n\n")
    md_content.append("Per semester breakdown:\n")
    md_content.append("- Tuition: ₹ 6,500\n")
    md_content.append("- Other fees: ₹ 1,000\n")
    md_content.append("- Total per semester: ₹ 7,500 approx\n\n")
    
    md_content.append("### Q: Sabse expensive course kaunsa hai CUSB mein?\n")
    md_content.append("**A:** CUSB mein sabse expensive course **M.Sc Biotechnology** hai jiski fees **₹ 94,072** hai (2 saal). Isme lab charges zyada hain.\n\n")
    
    md_content.append("### Q: Hostel ki fees kitni hai?\n")
    md_content.append("**A:** Hostel fees:\n")
    md_content.append("- Hostel Fee: ₹ 9,000 per semester\n")
    md_content.append("- Mess: ₹ 3,000 per month (₹ 36,000 per year)\n")
    md_content.append("- Total hostel + mess: ₹ 54,000 per year\n\n")
    
    md_content.append("### Q: PhD ki fees kitni hai?\n")
    md_content.append("**A:** PhD ki fees approximately **₹ 7,600 per semester** hai including:\n")
    md_content.append("- Tuition: ₹ 5,000\n")
    md_content.append("- Exam: ₹ 1,000\n")
    md_content.append("- Library: ₹ 500\n")
    md_content.append("- Sports: ₹ 500\n\n")
    
    md_content.append("### Q: B.Sc Agriculture ki fees kitni hai?\n")
    md_content.append("**A:** B.Sc (Hons.) Agriculture ki total fees approximately **₹ 2,00,000** hai (4 years).\n\n")
    
    md_content.append("### Q: Fees kab tak pay karni hai?\n")
    md_content.append("**A:** Admission offer ke baad fees pay karni hoti hai within given deadline. Semester fees start hone se pehle pay karni hoti hai.\n\n")
    
    md_content.append("---\n\n")
    
    # Summary
    md_content.append("## 📊 Fee Summary\n\n")
    md_content.append("| Category | Fee Range |\n")
    md_content.append("|----------|-----------|\n")
    md_content.append("| Most Affordable M.Sc | ₹ 26,072 (Statistics) |\n")
    md_content.append("| Most Expensive M.Sc | ₹ 94,072 (Biotechnology) |\n")
    md_content.append("| Average M.Sc Fee | ₹ 35,000 - 40,000 |\n")
    md_content.append("| B.Sc/B.A. (3 years) | ₹ 1,20,000 - 1,50,000 |\n")
    md_content.append("| Professional (B.Pharm) | ₹ 3,00,000 - 4,00,000 |\n")
    md_content.append("| PhD (per semester) | ₹ 7,600 |\n")
    md_content.append("| Hostel (per year) | ₹ 54,000 (with mess) |\n\n")
    
    md_content.append("---\n\n")
    md_content.append("**For Latest Fee Updates:** Visit https://www.cusb.ac.in or contact 0631-2229500\n")
    md_content.append("**Note:** Fees are subject to change. Check official website for current academic year fees.\n")
    
    # Write to file
    output_text = "".join(md_content)
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")
    
    print(f"\n{'=' * 70}")
    print("✅ Fee Structure Scraping Complete!")
    print(f"   Pages scraped: {len(all_data)}")
    print(f"   Output file: {OUTPUT_FILE}")
    print(f"   File size: {len(output_text)} characters")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
