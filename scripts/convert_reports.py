"""
Convert incident reports from PDFs and markdown to MyST format.

This script:
1. Reads PDFs from reports/ directory
2. Extracts incident details (title, timeline, action items, etc.)
3. Converts to markdown with MyST frontmatter
4. Generates a summary table of all reports

Uses docling (IBM Research) for ML-based PDF layout analysis, which handles
PagerDuty's two-column layout natively. Light regex post-processing extracts
metadata and sections from docling's markdown output.

Usage:
    python scripts/convert_reports.py
"""

import re
from pathlib import Path

import yaml
from docling.document_converter import DocumentConverter


def clean_pdf_text(text: str) -> str:
    """Clean docling markdown output for section parsing.

    - Fixes URL word-breaks (docling sometimes inserts spaces in long URLs)
    - Strips markdown heading markers so section names match as plain text
    - Removes timezone footer from PagerDuty exports
    - Removes right-column metadata sections (values extracted beforehand)
    - Converts PDF bullet glyphs ("\") to "- " list items
    - Normalizes "- Timeline" list items to "Timeline" section headers
    - Inserts "Timeline" header when docling omits it
    """
    # Pass 1: space immediately after "://" → "https:// github.com/"
    text = re.sub(r"(https?://)\s+", r"\1", text)
    # Pass 2: space within a URL path (repeat for chained breaks).
    # Only joins when the continuation contains "/" so we don't merge prose words.
    for _ in range(3):
        text = re.sub(
            r"(https?://\S+?/)\s+([a-z0-9][a-z0-9\-_./]*)",
            lambda m: m.group(1) + m.group(2) if "/" in m.group(2) else m.group(0),
            text,
        )

    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*All times listed[^\n]*", "", text)

    # PDF bullet glyphs (•) render as "\" in docling output. Convert "\ \n content"
    # into "- content", and drop any remaining lone "\" lines.
    text = re.sub(r"^\\\n(.+)", r"- \1", text, flags=re.MULTILINE)
    text = re.sub(r"^\\$", "", text, flags=re.MULTILINE)

    # Remove right-column metadata sections (values already extracted before cleaning)
    # Handles "OWNER OF REVIEW PROCESS" and concatenated "OWNEROFREVIEWPROCESS"
    text = re.sub(
        r"OWNER\s*OF?\s*REVIEW\s*PROCESS\s*\n.*?\n", "", text, flags=re.IGNORECASE
    )
    # Handles "IMPACT TIME" and truncated "IMPACT TIM" (some PDFs cut the column)
    text = re.sub(r"IMPACT\s*TIM\w*\s*\n.*?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"DURATION\s*\n.*?\n", "", text, flags=re.IGNORECASE)

    text = re.sub(r"^-\s+Timeline\s*$", "Timeline", text, flags=re.MULTILINE)

    # If no "Timeline" header exists but time entries follow Action Items,
    # insert one so extract_section("Action Items") stops at the right place.
    # Detects markdown tables (|), plain entries (10:02 AM), and list items
    # (- 10:02 AM) since docling uses all three formats.
    if "Timeline" not in text:
        text = re.sub(
            r"(Action Items\s*\n.*?)(\n\||\n\d{1,2}:\d{2}\s*[AP]M|\n-\s+\d{1,2}:\d{2}\s*[AP]M)",
            r"\1\nTimeline\2",
            text,
            count=1,
            flags=re.DOTALL,
        )

    return text


def clean_title(title: str) -> str:
    """Strip 'Incident report [date] -' or 'Postmortem Report -' prefix from title."""
    cleaned = re.sub(
        r"^(Incident\s+report\s+\w+\s+\d{1,2}\s+\d{4}\s*-\s*|Postmortem\s+Report\s*-\s*)",
        "",
        title,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def extract_title(text: str) -> str:
    """Extract incident title from PDF text.

    Returns text before "Status:" field, handling multi-line titles
    and PagerDuty export headers. Falls back to first non-URL line
    if no "Status:" field is found.

    Expects clean text (heading markers already stripped by clean_pdf_text).
    """
    match = re.search(r"^(.*?)\s*Status:", text, re.DOTALL)
    if match:
        before_status = match.group(1).strip()
        lines = [line.strip() for line in before_status.split("\n") if line.strip()]

        if not lines:
            return "Untitled Incident"

        # Skip PagerDuty export header line if present
        if len(lines) > 1 and ("PagerDuty" in lines[0] or "http" in lines[0]):
            title_lines = lines[1:]
        else:
            title_lines = lines

        title = " ".join(title_lines)
        title = " ".join(title.split())
        return clean_title(title)

    # Fallback: first non-empty, non-URL line
    for line in text.split("\n"):
        line = line.strip()
        if line and not line.startswith("http"):
            return clean_title(line)

    return "Untitled Incident"


def extract_impact_time(text: str) -> str:
    """Extract impact time range from raw docling text (before clean_pdf_text).

    Docling extracts right-column metadata as sections:
        IMPACT TIME
        Feb 11 at 08:46 to Feb 11 at 22:44
    """
    # Handles "IMPACT TIME" and truncated "IMPACT TIM" (some PDFs cut the column)
    match = re.search(r"IMPACT\s*TIM\w*\s*\n\s*(.+?)$", text, re.MULTILINE | re.IGNORECASE)
    if match:
        value = match.group(1).strip()
        if " at " in value and " to " in value:
            return value

    # Fallback: inline time range anywhere in text
    pattern = (
        r"([A-Z][a-z]{2}\s+\d{1,2}\s+at\s+\d{1,2}:\d{2}\s+"
        r"to\s+[A-Z][a-z]{2}\s+\d{1,2}\s+at\s+\d{1,2}:\d{2})"
    )
    match = re.search(pattern, text)
    return match.group(1) if match else "Unknown"


def extract_duration(text: str) -> str:
    """Extract incident duration from raw docling text (before clean_pdf_text).

    Docling extracts right-column metadata as sections:
        DURATION
        13h 58m
    """
    match = re.search(r"DURATION\s*\n\s*(.+?)$", text, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: match duration patterns like "13h 58m", "4d 1h 30m", "17m 6s"
    match = re.search(r"(\d+[dhm]\s+\d+[hms](?:\s+\d+[ms])?)", text)
    return match.group(1) if match else "Unknown"


def extract_section(text: str, section_name: str, next_sections: list) -> str:
    """Extract a section from PDF text.

    Returns content between section_name and the next section in next_sections.
    """
    next_pattern = "|".join(re.escape(s) for s in next_sections)
    pattern = rf"{re.escape(section_name)}\s*\n" rf"(.*?)(?=\n(?:{next_pattern})|\Z)"

    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""

    content = match.group(1).strip()
    content = content.replace("No comments added", "").strip()
    return content


def extract_timeline(text: str) -> str:
    """Extract and format timeline from PDF text as markdown tables.

    Handles three formats produced by docling:
    - Markdown tables: | 10:28AM | event |
    - Plain time entries: 10:28 AM Some event
    - List items: - 10:28 AM Some event

    Groups entries under date sub-headings when present.
    """
    match = re.search(r"Timeline\s*\n(.*)", text, re.DOTALL)
    if not match:
        return ""

    lines = match.group(1).strip().split("\n")

    current_date = None
    sections = []  # list of (date_or_None, [row_strings])
    rows = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("INCIDENT #"):
            continue

        # Date sub-heading (e.g. "October 16, 2025")
        if re.match(r"^[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4}$", line):
            if rows:
                sections.append((current_date, rows[:]))
                rows = []
            current_date = line
            continue

        # Markdown table separator — skip
        if re.match(r"^\|[-\s|]+\|$", line):
            continue

        # Markdown table row: | 10:28AM | event |
        m = re.match(r"\|\s*(\d{1,2}:\d{2}\s*[AP]M)\s*\|\s*(.*?)\s*\|$", line)
        if m:
            rows.append(f"| {m.group(1)} | {m.group(2).strip()} |")
            continue

        # Plain time entry: 10:28 AM Some event
        m = re.match(r"^(\d{1,2}:\d{2}\s*[AP]M)\s+(.*)", line)
        if m:
            rows.append(f"| {m.group(1)} | {m.group(2)} |")
            continue

        # List item: - 10:28 AM Some event
        m = re.match(r"^-\s+(\d{1,2}:\d{2}\s*[AP]M)\s+(.*)", line)
        if m:
            rows.append(f"| {m.group(1)} | {m.group(2)} |")
            continue

        # Continuation of previous entry (skip PagerDuty system lines)
        skip_starts = ("Triggered", "Resolved", "INCIDENT")
        if rows and not any(line.startswith(w) for w in skip_starts):
            rows[-1] = rows[-1].rstrip(" |") + " " + line + " |"

    if rows:
        sections.append((current_date, rows))

    if not sections:
        return ""

    output = []
    for date, date_rows in sections:
        if date:
            output.append(f"\n### {date}\n")
        output.append("| Time | Event |")
        output.append("| --- | --- |")
        output.extend(date_rows)

    return "\n".join(output)


def parse_pdf_incident(pdf_path: Path) -> dict:
    """Parse a PagerDuty incident PDF and extract all sections."""
    converter = DocumentConverter()
    text_raw = converter.convert(str(pdf_path)).document.export_to_markdown()

    # Extract metadata from raw text BEFORE cleaning (clean_pdf_text removes these sections)
    impact_time = extract_impact_time(text_raw)
    duration = extract_duration(text_raw)

    text = clean_pdf_text(text_raw)
    title = extract_title(text)

    return {
        "title": title,
        "impact_time": impact_time,
        "duration": duration,
        "overview": extract_section(
            text, "Overview", ["What Happened", "Resolution", "Where we got lucky"]
        ),
        "what_happened": extract_section(
            text,
            "What Happened",
            ["Resolution", "Where we got lucky", "What Went Well"],
        ),
        "resolution": extract_section(
            text,
            "Resolution",
            ["Where we got lucky", "What Went Well", "What Didn't Go"],
        ),
        "where_we_got_lucky": extract_section(
            text, "Where we got lucky", ["What Went Well", "What Didn't Go So Well"]
        ),
        "what_went_well": extract_section(
            text, "What Went Well?", ["What Didn't Go So Well", "Action Items"]
        ),
        "what_didnt_go_well": extract_section(
            text, "What Didn't Go So Well?", ["Action Items", "Timeline"]
        ),
        "action_items": extract_section(text, "Action Items", ["Timeline"]),
        "timeline": extract_timeline(text),
    }


def to_markdown(data: dict, date: str) -> str:
    """Convert parsed incident data to MyST markdown format."""
    lines = [
        "---",
        f'title: "{data["title"]}"',
        f"date: {date}",
        "---",
        "",
        f"# {data['title']}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| **Impact Time** | {data['impact_time']} |",
        f"| **Duration** | {data['duration']} |",
        "",
    ]

    sections = [
        ("Overview", data.get("overview")),
        ("What Happened", data.get("what_happened")),
        ("Resolution", data.get("resolution")),
        ("Where We Got Lucky", data.get("where_we_got_lucky")),
        ("What Went Well", data.get("what_went_well")),
        ("What Didn't Go So Well", data.get("what_didnt_go_well")),
        ("Action Items", data.get("action_items")),
        ("Timeline", data.get("timeline")),
    ]

    for section_title, content in sections:
        if content:
            if section_title == "Action Items":
                content = re.sub(r"- \[[ x]\] ", "- ", content)
            lines.append(f"## {section_title}")
            lines.append("")
            lines.append(content)
            lines.append("")

    return "\n".join(lines)


def ensure_frontmatter(content: str, filename: str) -> str:
    """Add MyST frontmatter to markdown file if missing."""
    content = re.sub(r"- \[[ x]\] ", "- ", content)

    if content.strip().startswith("---"):
        return content

    date = "Unknown"
    if re.match(r"\d{4}-\d{2}-\d{2}", filename):
        date = filename[:10]

    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = clean_title(title_match.group(1).strip())
    else:
        title = filename.replace("-", " ").title()

    frontmatter = ["---", f'title: "{title}"', f"date: {date}", "---", ""]
    return "\n".join(frontmatter) + content


def generate_report_table(report_dir: Path) -> str:
    """Generate summary table of all reports for the index page."""
    rows = ["| Date | Report | Duration |", "| --- | --- | --- |"]

    for md_file in sorted(report_dir.glob("*.md"), reverse=True):
        content = md_file.read_text()

        title = md_file.stem
        date = md_file.stem[:10]

        if content.strip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    title = frontmatter.get("title", title)
                    date = frontmatter.get("date", date)
                except Exception:
                    pass

        duration_match = re.search(r"\|\s*\*\*Duration\*\*\s*\|\s*(.+?)\s*\|", content)
        duration = duration_match.group(1).strip() if duration_match else "Unknown"

        link = f"[{title}](./report/{md_file.stem})"
        rows.append(f"| {date} | {link} | {duration} |")

    return "\n".join(rows) + "\n"


def process_pdf(pdf_path: Path, output_dir: Path, cache_dir: Path) -> None:
    """Process a single PDF file.

    Converted markdown is cached in cache_dir so docling only runs when the
    cached file is absent. Delete cache_dir to force a full re-conversion.
    """
    cache_path = cache_dir / f"{pdf_path.stem}.md"
    output_path = output_dir / f"{pdf_path.stem}.md"

    if cache_path.exists():
        print(f"Processing: {pdf_path.name} (cached)")
        output_path.write_text(cache_path.read_text())
        return

    print(f"Processing: {pdf_path.name}")
    date = pdf_path.stem[:10] if re.match(r"\d{4}-\d{2}-\d{2}", pdf_path.stem) else "Unknown"
    markdown = to_markdown(parse_pdf_incident(pdf_path), date)
    cache_path.write_text(markdown)
    output_path.write_text(markdown)


def process_markdown(md_path: Path, output_dir: Path) -> None:
    """Process a single markdown file, adding frontmatter if missing."""
    print(f"Processing: {md_path.name}")
    content = ensure_frontmatter(md_path.read_text(), md_path.stem)
    (output_dir / md_path.name).write_text(content)


def main():
    """Main entry point - process all reports and generate site."""
    reports_dir = Path("reports")
    output_dir = Path("docs/report")
    cache_dir = Path("docs/_build/docling")
    reports_dir.mkdir(exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(reports_dir.glob("*.pdf"))
    md_files = list(reports_dir.glob("*.md"))

    print(f"Found {len(pdf_files)} PDFs and {len(md_files)} markdown files\n")

    if not pdf_files and not md_files:
        print("No files found. Add PDFs or markdown to reports/ directory.")
        return

    for pdf_path in pdf_files:
        process_pdf(pdf_path, output_dir, cache_dir)

    for md_path in md_files:
        process_markdown(md_path, output_dir)

    print("Generating report table...")
    table = generate_report_table(output_dir)
    (output_dir / "report-table.txt").write_text(table)


if __name__ == "__main__":
    main()
