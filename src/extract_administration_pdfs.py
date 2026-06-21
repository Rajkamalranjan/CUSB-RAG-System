"""Extract PDFs from CUSB Administration pages into a standalone corpus.

Outputs:
    data/CUSB_administration_pdfs.md
    data/cusb_administration_pdfs.jsonl
    data/cusb_administration_pdfs_meta.json
"""

from __future__ import annotations

from pathlib import Path

import extract_about_university_pdfs as extractor


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

extractor.CACHE_DIR = DATA_DIR / "administration_pdf_cache"
extractor.OUTPUT_MD = DATA_DIR / "CUSB_administration_pdfs.md"
extractor.OUTPUT_JSONL = DATA_DIR / "cusb_administration_pdfs.jsonl"
extractor.OUTPUT_META = DATA_DIR / "cusb_administration_pdfs_meta.json"
extractor.DISCOVERY_CACHE = DATA_DIR / "administration_discovered_preview.json"
extractor.USER_AGENT = "CUSB-RAG-AdministrationPDFExtractor/1.0"
extractor.EXTRACTOR_NAME = "CUSB ADMINISTRATION PDF EXTRACTOR"
extractor.CORPUS_TITLE = "CUSB Administration PDF Extracts"
extractor.ID_PREFIX = "admin_pdf_"

extractor.SEED_PAGES = [
    ("Visitor", "https://cusb.ac.in/index.php?option=com_content&view=article&id=16:visitor&catid=2&Itemid=120"),
    ("Chancellor", "https://cusb.ac.in/index.php?option=com_content&view=article&id=17:chancellor&catid=2&Itemid=121"),
    ("Vice-Chancellor", "https://cusb.ac.in/index.php?option=com_content&view=article&id=18:vice-chancellor&Itemid=122&catid=2"),
    ("Pro-Vice Chancellor", "https://cusb.ac.in/index.php?option=com_content&view=article&id=19:pro-vice-chancellor&catid=2&Itemid=123"),
    ("Dean of Student welfare", "https://cusb.ac.in/index.php?option=com_content&view=article&id=20:dean-of-student-welfare&catid=2&Itemid=124"),
    ("Proctorial Board", "https://cusb.ac.in/index.php?option=com_content&view=article&id=21:proctorial-board&catid=2&Itemid=125"),
    ("Dean/Head", "https://cusb.ac.in/index.php?option=com_content&view=article&id=22:dean-head&catid=2&Itemid=126"),
    ("Registrar", "https://cusb.ac.in/index.php?option=com_content&view=article&id=23:registrar&catid=2&Itemid=127"),
    ("Finance Officer", "https://cusb.ac.in/index.php?option=com_content&view=article&id=24:finance-officer&catid=2&Itemid=128"),
    ("Controller of Examination", "https://cusb.ac.in/index.php?option=com_content&view=article&id=25:controller-of-examination&catid=2&Itemid=129"),
    ("Librarian", "https://cusb.ac.in/index.php?option=com_content&view=article&id=26:librarian&catid=2&Itemid=130"),
    ("Section & Staff", "https://cusb.ac.in/index.php?option=com_content&view=article&id=27:section-staff&catid=2&Itemid=131"),
    ("Committee/Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=28:committee&catid=2&Itemid=132"),
    ("Organogram", "https://cusb.ac.in/index.php?option=com_content&view=article&id=29:organogram&catid=2&Itemid=133"),
]


if __name__ == "__main__":
    extractor.main()
