"""Build a clean table from data/admission_fee/pg_course_fee.pdf."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOURCE_FILE = DATA_DIR / "admission_fee" / "pg_course_fee.pdf"

OUTPUT_MD = DATA_DIR / "CUSB_pg_course_fee_clean.md"
OUTPUT_JSONL = DATA_DIR / "cusb_pg_course_fee_clean.jsonl"
OUTPUT_META = DATA_DIR / "cusb_pg_course_fee_clean_meta.json"
ADMISSION_MD = DATA_DIR / "CUSB_admission_fee_pdfs.md"

PROGRAMMES = [
    "M.Sc. Mathematics / M.Sc. Statistics / M.A. Political Science and International Relations / M.A. Sociology / M.A. English / M.A. Hindi / M.A. Psychology / M.A. History / M.Com.",
    "M.A. Economics",
    "M.Sc. Environmental Science / M.A./M.Sc. Geography",
    "M.Sc. Biotechnology",
    "M.Sc. Bioinformatics",
    "M.Sc. Life Science",
    "M.A. Journalism and Mass Communication",
    "M.Sc. Computer Science",
    "M.Ed.",
    "LL.M.",
    "M.Sc. Physics / M.Sc. Chemistry",
    "Master in Social Work",
    "M.Sc. Geology",
    "M.Pharm. Pharmaceutics / M.Pharm. Pharmacology",
    "M.Sc. Artificial Intelligence",
    "M.Sc. Data Science and Applied Statistics",
    "M.P.Ed.",
]

ROWS = [
    ("Admission", [500] * 17),
    ("Enrolment No.", [1000] * 17),
    ("Identity Card", [100] * 17),
    ("Development Fee", [1000] * 17),
    ("Security Deposit (Refundable)", [1000] * 17),
    ("Sports Kit", [0] * 16 + [9500]),
    ("Psychological Lab / Research Centre / Pedagogy Labs / Educational Adventure / Leadership Tour", [0] * 8 + [2000] + [0] * 7 + [5000]),
    ("Tuition Fee", [2500, 2500, 3500, 3500, 3500, 3500, 3500, 3500, 3500, 5000, 3000, 5000, 3500, 6000, 3500, 15000, 3500]),
    ("Laboratory Fee", [0, 0, 3000, 3000, 0, 3000, 3000, 0, 0, 0, 1000, 0, 3000, 10000, 0, 0, 500]),
    ("Computer Lab", [500, 500, 500, 500, 3000, 500, 500, 3000, 500, 500, 500, 500, 3000, 500, 5000, 5000, 500]),
    ("Evaluation Fee", [500] * 17),
    ("Academic / Extension Activity Fee", [0, 0, 0, 0, 0, 0, 0, 0, 500, 2000, 0, 1000, 0, 0, 0, 0, 500]),
    ("Addt. Professional Enrichment Fee", [0, 0, 0, 0, 0, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 700]),
    ("Field Visit", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5000, 0, 0, 0, 0, 0]),
    ("Library / Magazine / News Letter", [500] * 17),
    ("Cultural Activities", [500] * 17),
    ("Games / Athletics", [500] * 17),
    ("Econometric Lab Fee", [0, 500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ("Total Fee", [8600, 9100, 12600, 12600, 12100, 12600, 12600, 12100, 12800, 13100, 10100, 17100, 15100, 22100, 14100, 25600, 25800]),
    ("Vidyarthi Mediclaim Premium (Optional)", [618] * 17),
    ("Total Fee (with VMC)", [9218, 9718, 13218, 13218, 12718, 13218, 13218, 12718, 13418, 13718, 10718, 17718, 15718, 22718, 14718, 26218, 26418]),
]

NOTES = [
    "Rs. 2000 towards production fee shall be charged in 4th semester from the students of M.A. Journalism and Mass Communication Programme.",
    "Rs. 5000 towards field visit shall be charged in 3rd semester from the students of M.Sc. Geology programme.",
    "Security Deposit amounting Rs. 500 only shall be refunded after deduction of Alumni Fee at Rs. 500 only.",
    "Rs. 5000 for Educational/Adventure/Leadership Tour and Rs. 9500 for Sports from students of M.P.Ed. Programme should be deposited through Demand Draft in favour of The Head, Department of Physical Education, CUSB, Gaya.",
]


def money(value: int) -> str:
    return f"Rs. {value:,}"


def build_records() -> list[dict]:
    records = []
    by_fee_head = {name: values for name, values in ROWS}
    for index, programme in enumerate(PROGRAMMES):
        fee_components = {name: values[index] for name, values in ROWS}
        records.append(
            {
                "id": f"pg_course_fee_{index + 1:03d}",
                "record_type": "pg_course_fee",
                "source_file": str(SOURCE_FILE.relative_to(BASE_DIR)),
                "programme": programme,
                "fee_components": fee_components,
                "total_fee": by_fee_head["Total Fee"][index],
                "vidyarthi_mediclaim_premium_optional": by_fee_head["Vidyarthi Mediclaim Premium (Optional)"][index],
                "total_fee_with_vmc": by_fee_head["Total Fee (with VMC)"][index],
            }
        )
    return records


def table_markdown() -> str:
    md = [
        "# CUSB PG Course Fee Clean Extract\n\n",
        f"Source PDF: `{SOURCE_FILE.relative_to(BASE_DIR)}`\n\n",
        "Source title: Fee Structure of PG Programme for Academic Year 2025-26\n\n",
        "This clean table is transcribed from `pg_course_fee.pdf`; the raw OCR block remains later in the admission fee corpus.\n\n",
        "| Fee Head | " + " | ".join(PROGRAMMES) + " |\n",
        "| --- | " + " | ".join(["---:"] * len(PROGRAMMES)) + " |\n",
    ]
    for name, values in ROWS:
        md.append("| " + name + " | " + " | ".join(money(value) for value in values) + " |\n")
    md.append("\n## Notes\n\n")
    for note in NOTES:
        md.append(f"- {note}\n")
    md.append("\n")
    return "".join(md)


def write_outputs() -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    records = build_records()
    md = table_markdown()
    md = md.replace("# CUSB PG Course Fee Clean Extract\n\n", f"# CUSB PG Course Fee Clean Extract\n\nCreated at UTC: {created_at}\n\n", 1)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    OUTPUT_META.write_text(
        json.dumps(
            {
                "created_at_utc": created_at,
                "source_file": str(SOURCE_FILE.relative_to(BASE_DIR)),
                "record_count": len(records),
                "failed_records": 0,
                "outputs": {
                    "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
                    "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
                    "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
                    "admission_markdown_with_pg_course_fee": str(ADMISSION_MD.relative_to(BASE_DIR)),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if ADMISSION_MD.exists():
        admission_text = ADMISSION_MD.read_text(encoding="utf-8", errors="ignore")
        marker = "# CUSB PG Course Fee Clean Extract"
        next_marker = "# CUSB UG/PG Fee Structure Department-Wise Clean Extract"
        if marker in admission_text and next_marker in admission_text:
            admission_text = admission_text[admission_text.index(next_marker) :]
        ADMISSION_MD.write_text(md + "\n\n---\n\n" + admission_text, encoding="utf-8")


def main() -> None:
    write_outputs()
    print(f"Wrote {len(PROGRAMMES)} clean PG course fee records")
    print(f"Markdown: {OUTPUT_MD}")
    print(f"JSONL: {OUTPUT_JSONL}")
    print(f"Metadata: {OUTPUT_META}")


if __name__ == "__main__":
    main()
