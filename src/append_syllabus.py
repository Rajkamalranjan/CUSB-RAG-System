"""Append syllabus content to markdown with proper UTF-8 encoding."""
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent

# Read original markdown
md_path = base_dir / "data" / "CUSB_markdown.md"
syllabus_path = base_dir / "data" / "CUSB_syllabus_content.md"

# Read both files
md_content = md_path.read_text(encoding="utf-8", errors="ignore")
syllabus_content = syllabus_path.read_text(encoding="utf-8", errors="ignore")

# Find position to insert (before any trailing markers)
insert_pos = len(md_content)
if "# CUSB Website Scraped Data" in md_content:
    insert_pos = md_content.index("# CUSB Website Scraped Data")

# Combine - add syllabus before scraped section
new_content = md_content[:insert_pos] + "\n\n" + syllabus_content + "\n\n" + md_content[insert_pos:]

# Write back with UTF-8
md_path.write_text(new_content, encoding="utf-8")

print(f"Syllabus content appended: {len(syllabus_content)} characters")
print(f"Total KB size: {len(new_content)} characters")
