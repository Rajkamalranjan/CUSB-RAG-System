"""Build a clean department-wise table from data/admission_fee/ug_pg_fee_structure.pdf.

The source PDF is image-only. Raw OCR is kept separately in
data/CUSB_admission_fee_pdfs.md; this script writes a clean, manually verified
department/programme-wise table from the total-fee rows in the PDF.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOURCE_FILE = DATA_DIR / "admission_fee" / "ug_pg_fee_structure.pdf"

OUTPUT_MD = DATA_DIR / "CUSB_ug_pg_fee_structure_department_wise.md"
OUTPUT_JSONL = DATA_DIR / "cusb_ug_pg_fee_structure_department_wise.jsonl"
OUTPUT_META = DATA_DIR / "cusb_ug_pg_fee_structure_department_wise_meta.json"
ADMISSION_MD = DATA_DIR / "CUSB_admission_fee_pdfs.md"

SOURCE_TITLE = "Fee Structure UG and UG-PG, Central University of South Bihar"


RECORDS = [
    {
        "page": 1,
        "school": "School of Mathematics and Statistics",
        "department_or_programme": "Department of Mathematics and Statistics",
        "programme": "5-Year Integrated UG-PG",
        "period_type": "Semester",
        "totals": [8800, 5000, 5000, 5000, 5000, 5000, 6000, 6000, 6000, 6000],
    },
    {
        "page": 2,
        "school": "School of Management and Commerce",
        "department_or_programme": "Department of Commerce",
        "programme": "5-Year Integrated UG-PG",
        "period_type": "Semester",
        "totals": [8800, 5000, 5000, 5000, 5000, 5000, 6000, 6000, 6000, 6000],
    },
    {
        "page": 3,
        "school": "School of Agriculture and Development",
        "department_or_programme": "Department of Agriculture",
        "programme": "4-Year B.Sc. (Hons.) in Agriculture",
        "period_type": "Semester",
        "totals": [32800, 29000, 29000, 29000, 29000, 29000, 29000, 29000],
    },
    {
        "page": 4,
        "school": "Department of Teacher Education",
        "department_or_programme": "Department of Teacher Education",
        "programme": "4-Year Integrated B.A. B.Ed.",
        "period_type": "Semester",
        "totals": [11300, 5500, 5500, 5500, 5500, 5500, 5500, 5500],
    },
    {
        "page": 5,
        "school": "Department of Teacher Education",
        "department_or_programme": "Department of Teacher Education",
        "programme": "4-Year B.Sc. B.Ed.",
        "period_type": "Semester",
        "totals": [12300, 6500, 6500, 6500, 6500, 6500, 6500, 6500],
    },
    {
        "page": 6,
        "school": "School of Human Sciences",
        "department_or_programme": "Department of Psychology",
        "programme": "5-Year Integrated UG-PG",
        "period_type": "Semester",
        "totals": [9000, 5200, 5200, 5200, 5200, 5200, 6200, 6200, 6200, 6200],
    },
    {
        "page": 7,
        "school": "School of Physical and Chemical Sciences",
        "department_or_programme": "Department of Physics and Chemistry",
        "programme": "5-Year Integrated UG-PG",
        "period_type": "Semester",
        "totals": [10550, 6750, 6750, 6750, 6750, 6750, 7750, 7750, 8250, 8250],
    },
    {
        "page": 8,
        "school": "School of Humanities",
        "department_or_programme": "Department of Indian Languages and Foreign Languages",
        "programme": "5-Year Integrated UG-PG",
        "period_type": "Semester",
        "totals": [8800, 5000, 5000, 5000, 5000, 5000, 6000, 6000, 6000, 6000],
    },
    {
        "page": 9,
        "school": "School of Social Sciences and Policy",
        "department_or_programme": "Departments of History, Sociology, Economics, Geography, and Political Science and International Relations",
        "programme": "5-Year Integrated UG-PG",
        "period_type": "Semester",
        "totals": [8800, 5000, 5000, 5000, 5000, 5000, 6000, 6000, 6000, 6000],
    },
    {
        "page": 10,
        "school": "School of Law and Governance",
        "department_or_programme": "B.B.A. LL.B. (Self-Finance)",
        "programme": "B.B.A. LL.B. (Self-Finance)",
        "period_type": "Semester",
        "totals": [29300, 25500, 25500, 25500, 25500, 25500, 25500, 25500, 25500, 25500],
    },
    {
        "page": 11,
        "school": "School of Law and Governance",
        "department_or_programme": "B.A. LL.B. (Hons.)",
        "programme": "B.A. LL.B. (Hons.)",
        "period_type": "Semester",
        "totals": [12300, 8000, 8000, 8000, 8000, 8000, 8000, 8000, 8000, 8000],
    },
    {
        "page": 12,
        "school": "Department of Computer Science",
        "department_or_programme": "Department of Computer Science",
        "programme": "5-Year Integrated UG-PG in Computer Science with an option of specialization in Artificial Intelligence",
        "period_type": "Semester",
        "totals": [10800, 8000, 8000, 8000, 8000, 8000, 11000, 11000, 11000, 11000],
        "vmc": [618] * 10,
    },
    {
        "page": 13,
        "school": "Department of Life Science",
        "department_or_programme": "Department of Life Science",
        "programme": "5-Year Integrated UG-PG in Life Science with specialization in Zoology/Botany",
        "period_type": "Semester",
        "totals": [13050, 9250, 9250, 9250, 9250, 9250, 12750, 12750, 12750, 12750],
        "vmc": [618] * 10,
    },
    {
        "page": 14,
        "school": "Department of Geology",
        "department_or_programme": "Department of Geology",
        "programme": "UG-PG 5-Year Integrated Program in Geology",
        "period_type": "Semester",
        "totals": [10550],
        "vmc": [618],
    },
    {
        "page": 15,
        "school": "Department of Mass Communication and Media",
        "department_or_programme": "Department of Mass Communication and Media",
        "programme": "5-Year UG-PG",
        "period_type": "Semester",
        "totals": [11550, 7750, 7750, 7750, 7750, 9750, 7750, 7750, 7750, 7750],
        "note": "Semester VI includes production fee.",
    },
    {
        "page": 16,
        "school": "Diploma in Pharmacy",
        "department_or_programme": "Diploma in Pharmacy (D.Pharm.)",
        "programme": "Diploma in Pharmacy (D.Pharm.)",
        "period_type": "Year",
        "period_labels": ["First Year", "Second Year"],
        "totals": [51600, 48000],
        "vmc": [1236, 1236],
        "note": "Field visit expenditure is to be borne by the students.",
    },
]


def first_only(value: int, length: int) -> list[int | None]:
    return [value] + [None] * (length - 1)


def repeat(value: int, length: int) -> list[int]:
    return [value] * length


def common_one_time(length: int, security: bool = True) -> list[dict]:
    rows = [
        {"fee_head": "Admission", "amounts": first_only(500, length)},
        {"fee_head": "Enrolment No.", "amounts": first_only(1000, length)},
        {"fee_head": "Identity Card", "amounts": first_only(100, length)},
        {"fee_head": "Development Fee", "amounts": first_only(1000, length)},
    ]
    if security:
        rows.append({"fee_head": "Security Deposit (Refundable)", "amounts": first_only(1000, length)})
    rows.extend(
        [
            {"fee_head": "Student Aid / Welfare Fund", "amounts": first_only(100, length)},
            {"fee_head": "NSS/NCC/Community Engagement", "amounts": first_only(100, length)},
        ]
    )
    return rows


def set_components(page: int, one_time: list[dict], semester: list[dict]) -> None:
    for record in RECORDS:
        if record["page"] == page:
            record["fee_components"] = one_time + semester + [{"fee_head": "Total", "amounts": record["totals"]}]
            return
    raise ValueError(f"Unknown page: {page}")


def add_fee_components() -> None:
    common_semester_5yr = [
        {"fee_head": "Tuition Fee", "amounts": [2500] * 6 + [3500] * 4},
        {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
        {"fee_head": "Econometric Fee", "amounts": repeat(0, 10)},
        {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
        {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
        {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
        {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
        {"fee_head": "Professional Enrichment Fee", "amounts": repeat(0, 10)},
    ]
    for page in (1, 2, 8, 9):
        set_components(page, common_one_time(10), common_semester_5yr)

    set_components(
        3,
        common_one_time(8),
        [
            {"fee_head": "Tuition Fee", "amounts": repeat(15000, 8)},
            {"fee_head": "Laboratory Fee", "amounts": repeat(5000, 8)},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(2000, 8)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 8)},
            {"fee_head": "Field Visit", "amounts": repeat(5000, 8)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 8)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 8)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 8)},
        ],
    )
    teacher_one_time = common_one_time(8) + [
        {"fee_head": "Pedagogy Labs / Educational Adventure / Leadership Tour", "amounts": first_only(2000, 8)}
    ]
    set_components(
        4,
        teacher_one_time,
        [
            {"fee_head": "Tuition Fee", "amounts": repeat(3000, 8)},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 8)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 8)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 8)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 8)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 8)},
        ],
    )
    set_components(
        5,
        teacher_one_time,
        [
            {"fee_head": "Tuition Fee", "amounts": repeat(3000, 8)},
            {"fee_head": "Laboratory Fee", "amounts": repeat(1000, 8)},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 8)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 8)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 8)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 8)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 8)},
        ],
    )
    set_components(
        6,
        common_one_time(10),
        [
            {"fee_head": "Tuition Fee", "amounts": [2500] * 6 + [3500] * 4},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Psychological Lab Fee", "amounts": repeat(200, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
        ],
    )
    set_components(
        7,
        common_one_time(10),
        [
            {"fee_head": "Tuition Fee", "amounts": [2500] * 6 + [3500] * 4},
            {"fee_head": "Laboratory Fee", "amounts": [1500] * 6 + [2500, 2500, 3000, 3000]},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
            {"fee_head": "Professional Enrichment Fee", "amounts": repeat(250, 10)},
        ],
    )
    set_components(
        10,
        common_one_time(10),
        [
            {"fee_head": "Tuition Fee", "amounts": repeat(21000, 10)},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Academic Activity Fee", "amounts": repeat(1000, 10)},
            {"fee_head": "Professional Enrichment Fee", "amounts": repeat(1000, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
        ],
    )
    set_components(
        11,
        common_one_time(10),
        [
            {"fee_head": "Tuition Fee", "amounts": repeat(3500, 10)},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Academic Activity Fee", "amounts": repeat(1000, 10)},
            {"fee_head": "Professional Enrichment Fee", "amounts": repeat(1000, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
        ],
    )
    set_components(
        12,
        common_one_time(10, security=False),
        [
            {"fee_head": "Tuition Fee", "amounts": [3500] * 6 + [5000] * 4},
            {"fee_head": "Computer Lab Fee", "amounts": [2500] * 6 + [4000] * 4},
            {"fee_head": "Econometric Fee", "amounts": repeat(0, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
            {"fee_head": "Professional Enrichment Fee", "amounts": repeat(0, 10)},
        ],
    )
    set_components(
        13,
        common_one_time(10, security=False),
        [
            {"fee_head": "Tuition Fee", "amounts": [3500] * 6 + [5000] * 4},
            {"fee_head": "Laboratory Fee", "amounts": [3000] * 6 + [5000] * 4},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
            {"fee_head": "Professional Enrichment Fee", "amounts": repeat(250, 10)},
        ],
    )
    set_components(
        14,
        common_one_time(1),
        [
            {"fee_head": "Tuition Fee", "amounts": [3000]},
            {"fee_head": "Laboratory Fee", "amounts": [1000]},
            {"fee_head": "Computer Lab", "amounts": [500]},
            {"fee_head": "Examination Fee", "amounts": [500]},
            {"fee_head": "Library / Magazine / News Letter", "amounts": [500]},
            {"fee_head": "Cultural Activities", "amounts": [500]},
            {"fee_head": "Games / Athletics", "amounts": [500]},
            {"fee_head": "Professional Enrichment Fee", "amounts": [250]},
        ],
    )
    set_components(
        15,
        common_one_time(10) + [{"fee_head": "Production Fee", "amounts": [None, None, None, None, None, 2000, None, None, None, None]}],
        [
            {"fee_head": "Tuition Fee", "amounts": repeat(2500, 10)},
            {"fee_head": "Laboratory Fee", "amounts": repeat(2500, 10)},
            {"fee_head": "Computer Lab Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Examination Fee", "amounts": repeat(500, 10)},
            {"fee_head": "Library / Magazine / News Letter", "amounts": repeat(500, 10)},
            {"fee_head": "Cultural Activities", "amounts": repeat(500, 10)},
            {"fee_head": "Games / Athletics", "amounts": repeat(500, 10)},
            {"fee_head": "Professional Enrichment Fee", "amounts": repeat(250, 10)},
        ],
    )
    set_components(
        16,
        [
            {"fee_head": "Admission", "amounts": [500, 0]},
            {"fee_head": "Enrolment No.", "amounts": [1000, 0]},
            {"fee_head": "Identity Card", "amounts": [100, 0]},
            {"fee_head": "Development Fees", "amounts": [1000, 0]},
            {"fee_head": "Security Deposit (Refundable)", "amounts": [1000, 0]},
        ],
        [
            {"fee_head": "Tuition Fee", "amounts": [31000, 31000]},
            {"fee_head": "Laboratory Fee", "amounts": [12000, 12000]},
            {"fee_head": "Computer", "amounts": [1000, 1000]},
            {"fee_head": "Evaluation Fee", "amounts": [1000, 1000]},
            {"fee_head": "Academic / Extension Activity Fee", "amounts": [0, 0]},
            {"fee_head": "Addt. Professional Enrichment Fee", "amounts": [0, 0]},
            {"fee_head": "Field Visit", "amounts": [None, None]},
            {"fee_head": "Library / Magazine / News Letter", "amounts": [1000, 1000]},
            {"fee_head": "Cultural Activities", "amounts": [1000, 1000]},
            {"fee_head": "Games / Athletics", "amounts": [1000, 1000]},
            {"fee_head": "Economic Lab Fee", "amounts": [0, 0]},
        ],
    )


add_fee_components()


def money(value: int | None) -> str:
    return "" if value is None else f"Rs. {value:,}"


def labels(record: dict) -> list[str]:
    if "period_labels" in record:
        return record["period_labels"]
    return [f"Semester {index}" for index in range(1, len(record["totals"]) + 1)]


def with_vmc(record: dict) -> list[int | None]:
    vmc = record.get("vmc")
    if not vmc:
        return [None] * len(record["totals"])
    return [fee + premium for fee, premium in zip(record["totals"], vmc)]


def markdown_for_record(record: dict) -> str:
    rows = [
        f"## {record['department_or_programme']}\n\n",
        f"**Source Page:** {record['page']}\n\n",
        f"**School/Unit:** {record['school']}\n\n",
        f"**Programme:** {record['programme']}\n\n",
    ]
    if record.get("note"):
        rows.append(f"**Note:** {record['note']}\n\n")
    period_labels = labels(record)
    rows.append("### Detailed Fee Components\n\n")
    rows.append("| Fee Head | " + " | ".join(period_labels) + " |\n")
    rows.append("| --- | " + " | ".join(["---:"] * len(period_labels)) + " |\n")
    for component in record.get("fee_components", []):
        amounts = component["amounts"] + [None] * (len(period_labels) - len(component["amounts"]))
        rows.append(
            "| "
            + component["fee_head"]
            + " | "
            + " | ".join(money(value) for value in amounts[: len(period_labels)])
            + " |\n"
        )
    if record.get("vmc"):
        rows.append("| Vidyarthi Mediclaim Premium (Optional) | " + " | ".join(money(value) for value in record["vmc"]) + " |\n")
        rows.append("| Total Fee With Optional VMC | " + " | ".join(money(value) for value in with_vmc(record)) + " |\n")
    rows.append("\n### Total Fee Summary\n\n")
    rows.append("| Period | Total Fee | Optional VMC | Total Fee With Optional VMC |\n")
    rows.append("| --- | ---: | ---: | ---: |\n")
    for label, total, vmc_value, total_vmc in zip(period_labels, record["totals"], record.get("vmc", [None] * len(record["totals"])), with_vmc(record)):
        rows.append(f"| {label} | {money(total)} | {money(vmc_value)} | {money(total_vmc)} |\n")
    rows.append("\n")
    return "".join(rows)


def record_to_json(row_id: int, record: dict) -> dict:
    period_totals = {
        label: total for label, total in zip(labels(record), record["totals"])
    }
    vmc = record.get("vmc")
    return {
        "id": f"ug_pg_fee_department_{row_id:03d}",
        "record_type": "ug_pg_department_wise_fee",
        "source_file": str(SOURCE_FILE.relative_to(BASE_DIR)),
        "source_page": record["page"],
        "school": record["school"],
        "department_or_programme": record["department_or_programme"],
        "programme": record["programme"],
        "period_type": record["period_type"],
        "period_totals": period_totals,
        "optional_vmc": {label: amount for label, amount in zip(labels(record), vmc)} if vmc else {},
        "period_totals_with_optional_vmc": {
            label: amount for label, amount in zip(labels(record), with_vmc(record)) if amount is not None
        },
        "fee_components": {
            component["fee_head"]: {
                label: amount
                for label, amount in zip(labels(record), component["amounts"])
                if amount is not None
            }
            for component in record.get("fee_components", [])
        },
        "note": record.get("note", ""),
    }


def write_outputs() -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    md = [
        "# CUSB UG/PG Fee Structure Department-Wise Clean Extract\n\n",
        f"Created at UTC: {created_at}\n\n",
        f"Source PDF: `{SOURCE_FILE.relative_to(BASE_DIR)}`\n\n",
        f"Source title: {SOURCE_TITLE}\n\n",
        "Scope: clean department/programme-wise total-fee rows from `ug_pg_fee_structure.pdf`. The source PDF is image-only, so the raw OCR text remains available separately, while this file keeps verified period totals in clean tables.\n\n",
        "---\n\n",
    ]
    for record in RECORDS:
        md.append(markdown_for_record(record))
        md.append("---\n\n")
    OUTPUT_MD.write_text("".join(md), encoding="utf-8")

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for index, record in enumerate(RECORDS, start=1):
            f.write(json.dumps(record_to_json(index, record), ensure_ascii=False) + "\n")

    OUTPUT_META.write_text(
        json.dumps(
            {
                "created_at_utc": created_at,
                "source_file": str(SOURCE_FILE.relative_to(BASE_DIR)),
                "record_count": len(RECORDS),
                "failed_records": 0,
                "outputs": {
                    "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
                    "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
                    "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if ADMISSION_MD.exists():
        admission_text = ADMISSION_MD.read_text(encoding="utf-8", errors="ignore")
        marker = "# CUSB UG/PG Fee Structure Department-Wise Clean Extract"
        next_marker = "# CUSB Admission Fee Department-Wise Clean Table"
        if marker in admission_text and next_marker in admission_text:
            admission_text = admission_text[admission_text.index(next_marker) :]
        ADMISSION_MD.write_text("".join(md) + "\n\n---\n\n" + admission_text, encoding="utf-8")


def main() -> None:
    write_outputs()
    print(f"Wrote {len(RECORDS)} UG/PG department-wise fee records")
    print(f"Markdown: {OUTPUT_MD}")
    print(f"JSONL: {OUTPUT_JSONL}")
    print(f"Metadata: {OUTPUT_META}")


if __name__ == "__main__":
    main()
