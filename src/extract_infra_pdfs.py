"""Extract CUSB INFRA pages and PDFs into a standalone corpus.

Outputs:
    data/CUSB_infra_pdfs.md
    data/cusb_infra_pdfs.jsonl
    data/cusb_infra_pdfs_meta.json
"""

from __future__ import annotations

from pathlib import Path


import extract_about_university_pdfs as extractor


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

extractor.CACHE_DIR = DATA_DIR / "infra_pdf_cache"
extractor.OUTPUT_MD = DATA_DIR / "CUSB_infra_pdfs.md"
extractor.OUTPUT_JSONL = DATA_DIR / "cusb_infra_pdfs.jsonl"
extractor.OUTPUT_META = DATA_DIR / "cusb_infra_pdfs_meta.json"
extractor.DISCOVERY_CACHE = DATA_DIR / "infra_discovered_preview.json"
extractor.USER_AGENT = "CUSB-RAG-InfraExtractor/2.0"
extractor.EXTRACTOR_NAME = "CUSB INFRA WEBSITE/PDF EXTRACTOR"
extractor.CORPUS_TITLE = "CUSB Infrastructure Website and PDF Extracts"
extractor.ID_PREFIX = "infra_pdf_"
extractor.PAGE_ID_PREFIX = "infra_page_"

extractor.SEED_PAGES = [
    ("Guest House", "https://www.cusb.ac.in/index.php?Itemid=213&id=98&option=com_content&view=article"),
    ("Library Services", "https://library.cusb.ac.in/"),
    ("Hostel Facility", "https://www.cusb.ac.in/index.php?Itemid=214&id=99&option=com_content&view=article"),
    ("Health Care", "https://www.cusb.ac.in/index.php?Itemid=215&id=100&option=com_content&view=article"),
    ("Sports", "https://www.cusb.ac.in/index.php?Itemid=216&id=101&option=com_content&view=article"),
    ("Biodiversity park", "https://www.cusb.ac.in/index.php?Itemid=217&id=102&option=com_content&view=article"),
    ("Media Studio", "https://www.cusb.ac.in/index.php?Itemid=218&id=103&option=com_content&view=article"),
    ("University Computer Lab", "https://www.cusb.ac.in/index.php?Itemid=219&id=104&option=com_content&view=article"),
    ("University Computer Centre", "https://www.cusb.ac.in/index.php?Itemid=220&id=61&option=com_content&view=article"),
    ("Wi-Fi Campus", "https://www.cusb.ac.in/index.php?Itemid=221&id=106&option=com_content&view=article"),
    ("Smart Class Room", "https://www.cusb.ac.in/index.php?Itemid=222&id=107&option=com_content&view=article"),
    ("Integrated Security System", "https://www.cusb.ac.in/index.php?Itemid=223&id=108&option=com_content&view=article"),
    ("Biometric Attendance", "https://www.cusb.ac.in/index.php?Itemid=224&id=109&option=com_content&view=article"),
    ("Engineering Wing", "https://www.cusb.ac.in/index.php?Itemid=225&id=110&option=com_content&view=article"),
    ("Lightning Location Network", "https://www.cusb.ac.in/index.php?Itemid=226&id=111&option=com_content&view=article"),
    ("Day Care Centre", "https://www.cusb.ac.in/index.php?Itemid=227&id=112&option=com_content&view=article"),
    ("Bank/ATM", "https://www.cusb.ac.in/index.php?Itemid=228&id=113&option=com_content&view=article"),
    ("Dhanvantari Arogya Vatika", "https://www.cusb.ac.in/index.php?Itemid=649&id=833&option=com_content&view=article"),
    ("Auditorium", "https://www.cusb.ac.in/index.php?Itemid=269&id=149&option=com_content&view=article"),
    ("Conference Hall", "https://www.cusb.ac.in/index.php?Itemid=270&id=150&option=com_content&view=article"),
]


if __name__ == "__main__":
    extractor.main()
