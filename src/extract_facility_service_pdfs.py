"""Extract CUSB Student Corner, facilities, services, committees and PDFs.

Outputs:
    data/CUSB_facility_service_pdfs.md
    data/cusb_facility_service_pdfs.jsonl
    data/cusb_facility_service_pdfs_meta.json
"""

from __future__ import annotations

from pathlib import Path

import extract_about_university_pdfs as extractor


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

extractor.CACHE_DIR = DATA_DIR / "facility_service_pdf_cache"
extractor.OUTPUT_MD = DATA_DIR / "CUSB_facility_service_pdfs.md"
extractor.OUTPUT_JSONL = DATA_DIR / "cusb_facility_service_pdfs.jsonl"
extractor.OUTPUT_META = DATA_DIR / "cusb_facility_service_pdfs_meta.json"
extractor.DISCOVERY_CACHE = DATA_DIR / "facility_service_discovered_preview.json"
extractor.USER_AGENT = "CUSB-RAG-FacilityServicePDFExtractor/2.0"
extractor.EXTRACTOR_NAME = "CUSB STUDENT CORNER/FACILITY/SERVICE PDF EXTRACTOR"
extractor.CORPUS_TITLE = "CUSB Student Corner, Facility, Services, Committee, Cell PDF Extracts"
extractor.ID_PREFIX = "facility_pdf_"

extractor.SEED_PAGES = [
    # Student Corner
    ("Department & Programmes", "https://cusb.ac.in/index.php?option=com_content&view=article&id=535&Itemid=190"),
    ("Academics/Examination Notices", "https://cusb.ac.in/index.php?option=com_content&view=article&id=76&Itemid=191"),
    ("Semester Exam Schedule", "https://cusb.ac.in/index.php?option=com_content&view=article&id=77&Itemid=192"),
    ("Ordinance/ Manual/ Regulation", "https://cusb.ac.in/index.php?option=com_content&view=article&id=78&Itemid=193"),
    ("Semester Result", "https://cusb.ac.in/index.php?option=com_content&view=article&id=904&Itemid=194"),
    ("Prospectus", "https://cusb.ac.in/index.php?option=com_content&view=article&id=82&Itemid=197"),
    ("Convocation", "https://cusb.ac.in/index.php?option=com_content&view=article&id=625&Itemid=209"),
    ("Download (Format/Performa)", "https://cusb.ac.in/index.php?option=com_content&view=article&id=455&Itemid=619"),
    ("Course Structure and Syllabus", "https://cusb.ac.in/index.php?option=com_content&view=article&id=119&Itemid=195"),
    ("Scholarship and Fellowship", "https://cusb.ac.in/index.php?option=com_content&view=article&id=81&Itemid=196"),
    ("Hostel", "https://cusb.ac.in/index.php?option=com_content&view=article&id=451&Itemid=198"),
    ("Anti-Ragging", "https://cusb.ac.in/index.php?option=com_content&view=article&id=84&Itemid=199"),
    ("Alumni", "https://cusb.ac.in/index.php?option=com_content&view=article&id=85&Itemid=200"),
    ("DACE", "https://cusb.ac.in/index.php?option=com_content&view=article&id=86&Itemid=201"),
    (
        "Capacity Development and Skill Enhancement Programme",
        "https://cusb.ac.in/index.php?option=com_content&view=article&id=525&Itemid=202",
    ),
    ("Placement Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=88&Itemid=203"),
    (
        "Students Counselling and Well- being Centre",
        "https://cusb.ac.in/index.php?option=com_content&view=article&id=89&Itemid=204",
    ),
    ("NSS", "https://cusb.ac.in/index.php?option=com_content&view=article&id=495&Itemid=205"),
    ("NCC", "https://cusb.ac.in/index.php?option=com_content&view=article&id=92&Itemid=206"),
    ("Extracurricular Activities", "https://cusb.ac.in/index.php?option=com_content&view=article&id=93&Itemid=207"),
    ("Code of Ethics", "https://cusb.ac.in/index.php?option=com_content&view=article&id=96&Itemid=210"),
    (
        "Grievance Redressal Committee for Students",
        "https://cusb.ac.in/index.php?option=com_content&view=article&id=97&Itemid=211",
    ),
    # Facilities and services
    ("University Guest House", "https://cusb.ac.in/index.php?option=com_content&view=article&id=98&Itemid=213"),
    ("Hostel Facility", "https://cusb.ac.in/index.php?option=com_content&view=article&id=99&Itemid=214"),
    ("Health Care", "https://cusb.ac.in/index.php?option=com_content&view=article&id=100&Itemid=215"),
    ("Sports Complex", "https://cusb.ac.in/index.php?option=com_content&view=article&id=101&Itemid=216"),
    ("Biodiversity Park", "https://cusb.ac.in/index.php?option=com_content&view=article&id=102&Itemid=217"),
    ("Media Studio", "https://cusb.ac.in/index.php?option=com_content&view=article&id=103&Itemid=218"),
    ("University Computer Lab", "https://cusb.ac.in/index.php?option=com_content&view=article&id=104&Itemid=219"),
    ("University Computer Centre", "https://cusb.ac.in/index.php?option=com_content&view=article&id=61&Itemid=220"),
    ("University Wi-Fi Facility", "https://cusb.ac.in/index.php?option=com_content&view=article&id=106&Itemid=221"),
    ("Smart Class Room", "https://cusb.ac.in/index.php?option=com_content&view=article&id=107&Itemid=222"),
    ("Integrated Security System", "https://cusb.ac.in/index.php?option=com_content&view=article&id=108&Itemid=223"),
    ("Biometric Attendance", "https://cusb.ac.in/index.php?option=com_content&view=article&id=109&Itemid=224"),
    ("Engineering Wing", "https://cusb.ac.in/index.php?option=com_content&view=article&id=110&Itemid=225"),
    ("Lightning Location Network", "https://cusb.ac.in/index.php?option=com_content&view=article&id=111&Itemid=226"),
    ("Day Care Centre", "https://cusb.ac.in/index.php?option=com_content&view=article&id=112&Itemid=227"),
    ("Bank", "https://cusb.ac.in/index.php?option=com_content&view=article&id=113&Itemid=228"),
    # Research/support facilities already covered by the old facility-service extractor.
    ("Central Instrumental Facility", "https://cusb.ac.in/index.php?option=com_content&view=article&id=60&Itemid=174"),
    ("45th INCA International Congress", "https://cusb.ac.in/index.php?option=com_content&view=article&id=850&Itemid=650"),
    ("IIC-Innovation Council", "https://cusb.ac.in/index.php?option=com_content&view=article&id=63&Itemid=177"),
    ("IPR Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=64&Itemid=178"),
    ("R&D Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=65&Itemid=179"),
    ("FPAC/IAEC/RDC Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=66&Itemid=180"),
    ("Legal Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=221&Itemid=181"),
    ("IECBHR/IBSC Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=71&Itemid=185"),
    ("Highlights and Publications", "https://cusb.ac.in/index.php?option=com_content&view=article&id=58&Itemid=141"),
    ("Partnership", "https://cusb.ac.in/index.php?option=com_content&view=article&id=59&Itemid=173"),
    ("Grants for Faculties", "https://cusb.ac.in/index.php?option=com_content&view=article&id=73&Itemid=187"),
    ("Committee/Cell", "https://cusb.ac.in/index.php?option=com_content&view=article&id=28:committee&catid=2&Itemid=132"),
]


if __name__ == "__main__":
    extractor.main()
