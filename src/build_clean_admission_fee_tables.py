"""Build clean department-wise CUSB admission/fee tables.

This file intentionally uses a curated transcription of the official total-fee
rows from data/admission_fee/ann_fee_1.pdf. The scanned fee PDFs in the folder
do not expose reliable table structure, so their OCR is kept in the raw corpus
and not used for the clean department-wise fee table.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_MD = DATA_DIR / "CUSB_admission_fee_department_wise.md"
OUTPUT_JSONL = DATA_DIR / "cusb_admission_fee_department_wise.jsonl"
OUTPUT_META = DATA_DIR / "cusb_admission_fee_department_wise_meta.json"
RAW_ADMISSION_MD = DATA_DIR / "CUSB_admission_fee_pdfs.md"

SOURCE_FILE = DATA_DIR / "admission_fee" / "ann_fee_1.pdf"
SOURCE_TITLE = (
    "Fee Structure of 3rd / 5th / 7th / 9th Semester of PG Students "
    "Admitted in AY 2024-25 and UG Students Admitted Before AY 2024-25"
)


COLUMNS = [
    {
        "programmes": [
            "M.Sc. Mathematics",
            "M.Sc. Statistics",
            "M.A. Political Science and International Relations",
            "M.A. Sociology",
            "M.A. English",
            "M.A. Hindi",
            "M.A. Psychology",
            "M.A. History",
            "M.Com.",
        ],
        "total_fee": 5000,
        "vmc": 618,
        "total_fee_with_vmc": 5618,
    },
    {"programmes": ["M.A. Economics"], "total_fee": 5500, "vmc": 618, "total_fee_with_vmc": 6118},
    {"programmes": ["M.Sc. Environmental Science"], "total_fee": 9000, "vmc": 618, "total_fee_with_vmc": 9618},
    {"programmes": ["M.A./M.Sc. Geography"], "total_fee": 9000, "vmc": 618, "total_fee_with_vmc": 9618},
    {"programmes": ["M.Sc. Biotechnology"], "total_fee": 8500, "vmc": 618, "total_fee_with_vmc": 9118},
    {"programmes": ["M.Sc. Bioinformatics"], "total_fee": 9000, "vmc": 618, "total_fee_with_vmc": 9618},
    {"programmes": ["M.Sc. Life Science"], "total_fee": 9000, "vmc": 618, "total_fee_with_vmc": 9618},
    {
        "programmes": ["M.A. Journalism and Mass Communication"],
        "total_fee": 8500,
        "vmc": 618,
        "total_fee_with_vmc": 9118,
        "note": "Rs. 2000 towards production fee shall be charged in 4th semester.",
    },
    {"programmes": ["M.Sc. Computer Science"], "total_fee": 12800, "vmc": 618, "total_fee_with_vmc": 13418},
    {"programmes": ["M.Ed."], "total_fee": 11100, "vmc": 618, "total_fee_with_vmc": 11718},
    {"programmes": ["B.A. B.Ed."], "total_fee": 12100, "vmc": 618, "total_fee_with_vmc": 12718},
    {"programmes": ["B.Sc. B.Ed."], "total_fee": 7000, "vmc": 618, "total_fee_with_vmc": 7618},
    {"programmes": ["B.A. LL.B."], "total_fee": 9500, "vmc": 618, "total_fee_with_vmc": 10118},
    {"programmes": ["LL.M."], "total_fee": 6500, "vmc": 618, "total_fee_with_vmc": 7118},
    {"programmes": ["M.Sc. Physics", "M.Sc. Chemistry"], "total_fee": 13500, "vmc": 618, "total_fee_with_vmc": 14118},
    {"programmes": ["M.A. Social Work"], "total_fee": 16500, "vmc": 618, "total_fee_with_vmc": 17118},
    {
        "programmes": ["M.Sc. Geology"],
        "total_fee": 18500,
        "vmc": 618,
        "total_fee_with_vmc": 19118,
        "note": "Rs. 5000 towards field visit shall be charged in 3rd semester.",
    },
    {
        "programmes": ["M.Pharm. Pharmaceutics", "M.Pharm. Pharmacology"],
        "total_fee": 6500,
        "vmc": 618,
        "total_fee_with_vmc": 7118,
    },
    {"programmes": ["One Year PG Diploma in Yoga"], "total_fee": 29000, "vmc": 618, "total_fee_with_vmc": 29618},
    {"programmes": ["B.Sc. Agriculture"], "total_fee": 10500, "vmc": 618, "total_fee_with_vmc": 11118},
    {"programmes": ["M.Sc. Artificial Intelligence"], "total_fee": 22000, "vmc": 618, "total_fee_with_vmc": 22618},
    {
        "programmes": ["M.Sc. Data Science and Applied Statistics"],
        "total_fee": 7600,
        "vmc": 618,
        "total_fee_with_vmc": 8318,
    },
]


def expanded_rows() -> list[dict]:
    rows = []
    for column in COLUMNS:
        for programme in column["programmes"]:
            rows.append(
                {
                    "programme": programme,
                    "total_fee": column["total_fee"],
                    "vidyarthi_mediclaim_premium_optional": column["vmc"],
                    "total_fee_with_vmc_optional": column["total_fee_with_vmc"],
                    "note": column.get("note", ""),
                    "source_file": str(SOURCE_FILE.relative_to(BASE_DIR)),
                    "source_title": SOURCE_TITLE,
                }
            )
    return rows


def money(value: int) -> str:
    return f"Rs. {value:,}"


def write_outputs(rows: list[dict]) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    md = [
        "# CUSB Admission Fee Department-Wise Clean Table\n\n",
        f"Created at UTC: {created_at}\n\n",
        f"Source PDF: `{SOURCE_FILE.relative_to(BASE_DIR)}`\n\n",
        f"Source title: {SOURCE_TITLE}\n\n",
        "Scope: official total-fee rows from `ann_fee_1.pdf` only. The scanned 2025-26 fee PDFs are kept in the raw OCR corpus and are not used here because their table OCR is not reliable enough for a clean department-wise table.\n\n",
        "Vidyarthi Mediclaim Premium (VMC) is optional and is Rs. 618 for every listed programme in this source table.\n\n",
        "| S.No. | Programme / Department | Total Fee | Optional VMC | Total Fee With Optional VMC | Note |\n",
        "| --- | --- | ---: | ---: | ---: | --- |\n",
    ]
    for index, row in enumerate(rows, start=1):
        md.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    row["programme"],
                    money(row["total_fee"]),
                    money(row["vidyarthi_mediclaim_premium_optional"]),
                    money(row["total_fee_with_vmc_optional"]),
                    row["note"],
                ]
            )
            + " |\n"
        )

    md.extend(
        [
            "\n## Source Notes\n\n",
            "- Rs. 2000 towards production fee shall be charged in 4th semester from the students of M.A. Journalism and Mass Communication Programme.\n",
            "- Rs. 5000 towards field visit shall be charged in 3rd semester from the students of M.Sc. Geology programme.\n",
            "- Security deposit amounting Rs. 500 only shall be refunded after deduction of Alumni Fee at Rs. 500 only.\n",
        ]
    )
    OUTPUT_MD.write_text("".join(md), encoding="utf-8")

    if RAW_ADMISSION_MD.exists():
        raw_text = RAW_ADMISSION_MD.read_text(encoding="utf-8", errors="ignore")
        marker = "# CUSB Admission Fee Department-Wise Clean Table"
        raw_marker = "# CUSB Admission and Fee PDF Extracts"
        if marker in raw_text and raw_marker in raw_text:
            raw_text = raw_text[raw_text.index(raw_marker) :]
        combined = "".join(md) + "\n\n---\n\n# Raw Admission and Fee PDF Extracts\n\n" + raw_text
        RAW_ADMISSION_MD.write_text(combined, encoding="utf-8")

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for index, row in enumerate(rows, start=1):
            f.write(
                json.dumps(
                    {
                        "id": f"admission_fee_department_{index:03d}",
                        "record_type": "department_wise_fee",
                        **row,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    OUTPUT_META.write_text(
        json.dumps(
            {
                "created_at_utc": created_at,
                "source_file": str(SOURCE_FILE.relative_to(BASE_DIR)),
                "record_count": len(rows),
                "failed_records": 0,
                "outputs": {
                    "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
                    "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
                    "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
                    "raw_markdown_with_clean_table": str(RAW_ADMISSION_MD.relative_to(BASE_DIR)),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    rows = expanded_rows()
    write_outputs(rows)
    print(f"Wrote {len(rows)} clean department-wise fee rows")
    print(f"Markdown: {OUTPUT_MD}")
    print(f"JSONL: {OUTPUT_JSONL}")
    print(f"Metadata: {OUTPUT_META}")


if __name__ == "__main__":
    main()
