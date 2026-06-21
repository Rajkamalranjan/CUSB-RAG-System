"""Scrape current CUSB department faculty details.

Outputs:
    data/CUSB_department_faculty_current.md
    data/cusb_department_faculty_current.jsonl
    data/cusb_department_faculty_current_meta.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_MD = DATA_DIR / "CUSB_department_faculty_current.md"
OUTPUT_JSONL = DATA_DIR / "cusb_department_faculty_current.jsonl"
OUTPUT_META = DATA_DIR / "cusb_department_faculty_current_meta.json"

BASE_URL = "https://www.cusb.ac.in/"
USER_AGENT = "CUSB-RAG-DepartmentFacultyScraper/1.0"

DEPARTMENTS = [
    ("Bioinformatics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=31&Itemid=136"),
    ("Geology", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=32&Itemid=142"),
    ("Geography", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=33&Itemid=143"),
    ("Life Science", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=36&Itemid=137"),
    ("Biotechnology", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=34&Itemid=144"),
    ("Environmental Sciences", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=131&Itemid=145"),
    ("Historical Studies and Archaeology", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=137&Itemid=157"),
    ("Economic Studies and Policy", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=46&Itemid=158"),
    ("Development Studies", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=47&Itemid=159"),
    ("Political Studies", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=48&Itemid=160"),
    ("Sociological Studies", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=49&Itemid=161"),
    ("Library and Information Science", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=761&Itemid=623"),
    ("Mathematics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=56&Itemid=170"),
    ("Statistics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=55&Itemid=171"),
    ("Computer Science", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=57&Itemid=172"),
    ("Teacher Education", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=41&Itemid=151"),
    ("Physical Education", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=42&Itemid=152"),
    ("Chemistry", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=39&Itemid=148"),
    ("Physics", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=40&Itemid=149"),
    ("English", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=143&Itemid=167"),
    ("Indian Languages", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=53&Itemid=168"),
    ("Mass Communication and Media", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=139&Itemid=163"),
    ("Commerce and Business Studies", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=141&Itemid=165"),
    ("Psychological Sciences", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=38&Itemid=146"),
    ("Law and Governance", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=43&Itemid=154"),
    ("Pharmacy", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=37&Itemid=138"),
    ("Agriculture", "https://www.cusb.ac.in/index.php?option=com_content&view=article&id=44&Itemid=155"),
]


@dataclass
class FacultyRecord:
    id: str
    department: str
    department_url: str
    faculty_page_url: str
    name: str
    designation: str
    email: str
    profile_url: str
    specialization: str
    qualification: str
    experience: str
    image_url: str
    source_text: str
    scraped_at_utc: str


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def record_id(department: str, name: str, faculty_page_url: str) -> str:
    raw = f"{department}|{name}|{faculty_page_url}"
    return "faculty_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]


def fetch_soup(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def get_main_content(soup: BeautifulSoup) -> Tag:
    return (
        soup.find("div", class_="item-page")
        or soup.find("main")
        or soup.find("article")
        or soup.body
        or soup
    )


def find_faculty_page(session: requests.Session, department_url: str) -> str | None:
    soup = fetch_soup(session, department_url)
    for link in soup.find_all("a", href=True):
        text = one_line(link.get_text(" ", strip=True)).lower()
        if text == "faculty":
            return urljoin(department_url, link["href"])
    for link in soup.find_all("a", href=True):
        text = one_line(link.get_text(" ", strip=True)).lower()
        href = link["href"].lower()
        if "faculty" in text or "faculty" in href:
            return urljoin(department_url, link["href"])
    return None


def parse_label_value(text: str, label: str) -> str:
    pattern = rf"^{re.escape(label)}\s*:?\s*(.*)$"
    match = re.match(pattern, text, flags=re.IGNORECASE)
    return one_line(match.group(1)) if match else ""


def collect_until_next_name(name_tag: Tag) -> list[Tag]:
    nodes: list[Tag] = []
    for sibling in name_tag.find_all_next():
        if sibling is name_tag:
            continue
        if sibling.name == "h3":
            break
        if sibling.name in {"h1", "h2"}:
            break
        if sibling.name in {"p", "h4", "a", "img"}:
            nodes.append(sibling)
    return nodes


def looks_like_faculty_name(text: str) -> bool:
    if not text or len(text) > 100:
        return False
    if not re.search(r"\b(Prof\.|Dr\.|Mr\.|Ms\.|Mrs\.)\s+", text):
        return False
    blocked = ["department of", "quick links", "about university"]
    return not any(item in text.lower() for item in blocked)


def parse_faculty_page(session: requests.Session, department: str, department_url: str, faculty_page_url: str) -> list[FacultyRecord]:
    soup = fetch_soup(session, faculty_page_url)
    main = get_main_content(soup)
    records: list[FacultyRecord] = []
    seen_names: set[str] = set()

    for name_tag in main.find_all("h3"):
        name = one_line(name_tag.get_text(" ", strip=True))
        if not looks_like_faculty_name(name) or name in seen_names:
            continue
        seen_names.add(name)

        nodes = collect_until_next_name(name_tag)
        designation = ""
        email = ""
        profile_url = ""
        specialization = ""
        qualification = ""
        experience = ""
        image_url = ""
        source_parts = [name]

        image = name_tag.find_previous("img")
        if image and image.get("src") and "social_icons" not in image.get("src", "") and "logo" not in image.get("src", ""):
            image_url = urljoin(faculty_page_url, image["src"])

        for node in nodes:
            text = one_line(node.get_text(" ", strip=True))
            if text:
                source_parts.append(text)

            if node.name == "p" and not designation:
                lower = text.lower()
                if any(word in lower for word in ["professor", "lecturer", "teacher", "head", "assistant", "associate"]):
                    designation = text

            if node.name == "a" and node.get("href"):
                href = node["href"]
                if href.startswith("mailto:") and not email:
                    email = one_line(href.replace("mailto:", ""))
                elif "profile" in text.lower() and not profile_url:
                    profile_url = urljoin(faculty_page_url, href)
                elif "people.samarth.edu.in" in href and not profile_url:
                    profile_url = href

            if "Specialization" in text:
                specialization = parse_label_value(text, "Specialization")
            elif "Qualification" in text:
                qualification = parse_label_value(text, "Qualification")
            elif "Experience" in text:
                experience = parse_label_value(text, "Experience")

        records.append(
            FacultyRecord(
                id=record_id(department, name, faculty_page_url),
                department=department,
                department_url=department_url,
                faculty_page_url=faculty_page_url,
                name=name,
                designation=designation,
                email=email,
                profile_url=profile_url,
                specialization=specialization,
                qualification=qualification,
                experience=experience,
                image_url=image_url,
                source_text=normalize_text("\n".join(source_parts)),
                scraped_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        )

    return records


def write_outputs(records: list[FacultyRecord], departments: list[dict], failed: list[dict]) -> None:
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for record in records:
        counts[record.department] = counts.get(record.department, 0) + 1

    md = [
        "# CUSB Department Faculty Details\n\n",
        f"Scraped at UTC: {datetime.now(timezone.utc).isoformat()}\n\n",
        f"Departments scanned: {len(departments)}\n\n",
        f"Faculty records extracted: {len(records)}\n\n",
        f"Departments failed or missing faculty page: {len(failed)}\n\n",
        "---\n\n",
        "## Summary\n\n",
        "| Department | Faculty Count | Faculty Page |\n",
        "|---|---:|---|\n",
    ]
    for item in departments:
        dept = item["department"]
        md.append(f"| {dept} | {counts.get(dept, 0)} | {item.get('faculty_page_url', '')} |\n")
    md.append("\n---\n\n")

    for department, _url in DEPARTMENTS:
        dept_records = [record for record in records if record.department == department]
        if not dept_records:
            continue
        md.append(f"## {department}\n\n")
        for index, record in enumerate(dept_records, start=1):
            md.append(f"### {index}. {record.name}\n\n")
            md.append(f"**Designation:** {record.designation}\n\n")
            if record.email:
                md.append(f"**Email:** {record.email}\n\n")
            if record.profile_url:
                md.append(f"**Profile:** {record.profile_url}\n\n")
            if record.specialization:
                md.append(f"**Specialization:** {record.specialization}\n\n")
            if record.qualification:
                md.append(f"**Qualification:** {record.qualification}\n\n")
            if record.experience:
                md.append(f"**Experience:** {record.experience}\n\n")
            if record.image_url:
                md.append(f"**Image:** {record.image_url}\n\n")
            md.append(f"**Faculty Page:** {record.faculty_page_url}\n\n")
            md.append("```text\n")
            md.append(record.source_text)
            md.append("\n```\n\n")
        md.append("---\n\n")

    if failed:
        md.append("## Failed / Missing Faculty Pages\n\n")
        for item in failed:
            md.append(f"- {item['department']} | {item['department_url']} | {item['error']}\n")

    OUTPUT_MD.write_text("".join(md), encoding="utf-8")

    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "department_count": len(departments),
        "faculty_records": len(records),
        "failed_count": len(failed),
        "outputs": {
            "markdown": str(OUTPUT_MD.relative_to(BASE_DIR)),
            "jsonl": str(OUTPUT_JSONL.relative_to(BASE_DIR)),
            "metadata": str(OUTPUT_META.relative_to(BASE_DIR)),
        },
        "department_counts": counts,
        "departments": departments,
        "failed": failed,
    }
    OUTPUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("=" * 70, flush=True)
    print("CUSB CURRENT DEPARTMENT FACULTY SCRAPER", flush=True)
    print("=" * 70, flush=True)

    all_records: list[FacultyRecord] = []
    departments: list[dict] = []
    failed: list[dict] = []

    for index, (department, department_url) in enumerate(DEPARTMENTS, start=1):
        print(f"\n[{index}/{len(DEPARTMENTS)}] {department}", flush=True)
        try:
            faculty_page_url = find_faculty_page(session, department_url)
            if not faculty_page_url:
                raise ValueError("Faculty page link not found")
            print(f"  Faculty page: {faculty_page_url}", flush=True)
            records = parse_faculty_page(session, department, department_url, faculty_page_url)
            print(f"  Faculty records: {len(records)}", flush=True)
            departments.append(
                {
                    "department": department,
                    "department_url": department_url,
                    "faculty_page_url": faculty_page_url,
                    "faculty_count": len(records),
                }
            )
            all_records.extend(records)
        except Exception as exc:
            print(f"  Failed: {exc}", flush=True)
            failed.append({"department": department, "department_url": department_url, "error": str(exc)})
            departments.append(
                {
                    "department": department,
                    "department_url": department_url,
                    "faculty_page_url": "",
                    "faculty_count": 0,
                }
            )
        time.sleep(0.2)

    write_outputs(all_records, departments, failed)
    print("\nScraping complete", flush=True)
    print(f"  Departments: {len(departments)}", flush=True)
    print(f"  Faculty records: {len(all_records)}", flush=True)
    print(f"  Failed/missing: {len(failed)}", flush=True)
    print(f"  Markdown: {OUTPUT_MD}", flush=True)
    print(f"  JSONL: {OUTPUT_JSONL}", flush=True)
    print(f"  Metadata: {OUTPUT_META}", flush=True)


if __name__ == "__main__":
    main()
