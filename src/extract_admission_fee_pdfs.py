"""Extract PDFs from data/admission_fee into a standalone corpus.

Outputs:
    data/CUSB_admission_fee_pdfs.md
    data/cusb_admission_fee_pdfs.jsonl
    data/cusb_admission_fee_pdfs_meta.json
"""

from __future__ import annotations

from pathlib import Path

import extract_manual_syllabus_pdfs as extractor


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

extractor.INPUT_DIR = DATA_DIR / "admission_fee"
extractor.OUTPUT_MD = DATA_DIR / "CUSB_admission_fee_pdfs.md"
extractor.OUTPUT_JSONL = DATA_DIR / "cusb_admission_fee_pdfs.jsonl"
extractor.OUTPUT_META = DATA_DIR / "cusb_admission_fee_pdfs_meta.json"
extractor.EXTRACTOR_NAME = "CUSB ADMISSION/FEE HYBRID PDF EXTRACTOR"
extractor.CORPUS_TITLE = "CUSB Admission and Fee PDF Extracts"
extractor.ID_PREFIX = "admission_fee_pdf_"


if __name__ == "__main__":
    extractor.main()
