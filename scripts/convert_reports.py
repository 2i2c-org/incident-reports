"""
Convert incident reports from PDFs and markdown to MyST format.

This script:
1. Reads PDFs from reports/ directory
2. Extracts incident details (title, timeline, action items, etc.)
3. Converts to markdown with MyST frontmatter
4. Generates a summary table of all reports

There is a bunch of regex in here! That's because we're parsing PDF.
Ideally we can use the PagerDuty API to get the text from incidents directly,
but there seems to be missing information that we only have via the PDF exports.

Usage:
    python scripts/convert_reports.py
"""

import re
from pathlib import Path

import pdfplumber
import yaml


# ============================================================================
# PDF EXTRACTION
# ============================================================================


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def clean_pdf_text(text: str) -> str:
    """Remove PDF layout artifacts from extracted text."""
    # Remove two-column layout keywords
    text = re.sub(r"OWNER OF REVIEW PROCESS\s*", "\n", text)
    text = re.sub(r"IMPACT TIME\s*", "\n", text)
    text = re.sub(r"DURATION\s*", "\n", text)
    # Remove timezone footer
    pattern = r"\*All times listed.*?Pacific Time.*?\)"
    text = re.sub(pattern, "", text, flags=re.DOTALL)
    return text


# ============================================================================
# METADATA EXTRACTION
# ============================================================================


def extract_title(text: str) -> str:
    """Extract incident title from PDF text."""
    match = re.search(r"^(.*?)\s*Status:", text, re.DOTALL)
    if match:
        # Clean up whitespace and join multi-line titles
        return " ".join(match.group(1).split())
    return "Untitled Incident"


def extract_impact_time(text: str) -> str:
    """Extract impact time range from PDF text."""
    pattern = (
        r"([A-Z][a-z]{2}\s+\d{1,2}\s+at\s+\d{1,2}:\d{2}\s+"
        r"to\s+[A-Z][a-z]{2}\s+\d{1,2}\s+at\s+\d{1,2}:\d{2})"
    )
    match = re.search(pattern, text)
    return match.group(1) if match else "Unknown"


def extract_duration(text: str) -> str:
    """Extract incident duration from PDF text."""
    match = re.search(r"(\d+[mh]\s+\d+[ms])", text)
    return match.group(1) if match else "Unknown"


# ============================================================================
# SECTION EXTRACTION
# ============================================================================


def extract_section(text: str, section_name: str, next_sections: list) -> str:
    """
    Extract a section from PDF text.

    Args:
        text: The full PDF text
        section_name: Name of section to extract (e.g., "Overview")
        next_sections: List of section names that might follow this one

    Returns:
        Section content as string, or empty string if not found
    """
    # Build regex pattern to match section until next section
    next_pattern = "|".join(re.escape(s) for s in next_sections)
    pattern = rf"{re.escape(section_name)}\s*\n" rf"(.*?)(?=\n(?:{next_pattern})|\Z)"

    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""

    content = match.group(1).strip()
    # Remove PagerDuty placeholder text
    content = content.replace("No comments added", "").strip()
    return content


# ============================================================================
# TIMELINE EXTRACTION
# ============================================================================


def extract_timeline(text: str) -> str:
    """
    Extract and format timeline from PDF text.

    Returns timeline as markdown with tables for each date.
    """
    match = re.search(r"Timeline\s*\n(.*)", text, re.DOTALL)
    if not match:
        return ""

    lines = match.group(1).strip().split("\n")
    timeline = ""
    current_date = None
    entries = []

    for line in lines:
        line = line.strip()

        # Skip empty lines and incident numbers
        if not line or line.startswith("INCIDENT #"):
            continue

        # Check if this is a date header (e.g., "October 16, 2025")
        is_date = re.match(r"^[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4}$", line)
        if is_date:
            # Write out previous date's table if it exists
            if current_date and entries:
                timeline += (
                    f"\n### {current_date}\n\n" f"| Time | Event |\n| --- | --- |\n"
                )
                timeline += "\n".join(entries) + "\n"
                entries = []
            current_date = line
            continue

        # Check if this is a time entry (e.g., "3:00 PM Some event")
        time_match = re.match(r"^(\d{1,2}:\d{2}\s*[AP]M)\s+(.*)", line)
        if time_match:
            time = time_match.group(1)
            event = time_match.group(2)
            entries.append(f"| {time} | {event} |")
            continue

        # Otherwise, it's a continuation of the previous entry
        skip_words = ("Triggered", "Resolved")
        if entries and not line.startswith(skip_words):
            # Append to last entry
            entries[-1] = entries[-1].rstrip(" |") + " " + line + " |"

    # Write final date's table
    if current_date and entries:
        timeline += f"\n### {current_date}\n\n" f"| Time | Event |\n| --- | --- |\n"
        timeline += "\n".join(entries)

    return timeline


# ============================================================================
# PDF PARSING
# ============================================================================


def parse_pdf_incident(pdf_path: Path) -> dict:
    """
    Parse a PagerDuty incident PDF and extract all sections.

    Returns dict with keys: title, impact_time, duration, overview,
    what_happened, resolution, etc.
    """
    # Step 1: Extract and clean text
    text = extract_text_from_pdf(pdf_path)
    text = clean_pdf_text(text)

    # Step 2: Extract metadata
    title = extract_title(text)
    impact_time = extract_impact_time(text)
    duration = extract_duration(text)

    # Step 3: Extract content sections
    sections = {
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

    return sections


# ============================================================================
# MARKDOWN GENERATION
# ============================================================================


def to_markdown(data: dict, date: str) -> str:
    """Convert parsed incident data to MyST markdown format."""
    # Start with frontmatter and title
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

    # Add each section if it has content
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
            # Remove checkboxes from action items
            if section_title == "Action Items":
                content = re.sub(r"- \[[ x]\] ", "- ", content)

            lines.append(f"## {section_title}")
            lines.append("")
            lines.append(content)
            lines.append("")

    return "\n".join(lines)


def ensure_frontmatter(content: str, filename: str) -> str:
    """Add MyST frontmatter to markdown file if missing."""
    # Remove checkboxes (convert to regular bullets)
    content = re.sub(r"- \[[ x]\] ", "- ", content)

    # If already has frontmatter, we're done
    if content.strip().startswith("---"):
        return content

    # Extract date from filename (format: YYYY-MM-DD-title.md)
    date = "Unknown"
    if re.match(r"\d{4}-\d{2}-\d{2}", filename):
        date = filename[:10]

    # Try to extract title from first heading
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        # Generate title from filename
        title = filename.replace("-", " ").title()

    # Add frontmatter
    frontmatter = [
        "---",
        f'title: "{title}"',
        f"date: {date}",
        "---",
        "",
    ]

    return "\n".join(frontmatter) + content


# ============================================================================
# REPORT TABLE GENERATION
# ============================================================================


def generate_report_table(report_dir: Path) -> str:
    """Generate summary table of all reports for the index page."""
    rows = ["| Date | Report | Duration |", "| --- | --- | --- |"]

    # Process each markdown file, newest first
    for md_file in sorted(report_dir.glob("*.md"), reverse=True):
        content = md_file.read_text()

        # Extract frontmatter using YAML
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

        # Extract duration from content
        duration_match = re.search(r"\|\s*\*\*Duration\*\*\s*\|\s*(.+?)\s*\|", content)
        duration = "Unknown"
        if duration_match:
            duration = duration_match.group(1).strip()

        # Add row to table
        link = f"[{title}](./report/{md_file.stem})"
        rows.append(f"| {date} | {link} | {duration} |")

    return "\n".join(rows) + "\n"


# ============================================================================
# MAIN PROCESSING
# ============================================================================


def process_pdf(pdf_path: Path, output_dir: Path) -> bool:
    """Process a single PDF file. Returns True on success."""
    print(f"Processing: {pdf_path.name}")
    try:
        # Parse PDF
        data = parse_pdf_incident(pdf_path)

        # Extract date from filename
        date = "Unknown"
        if re.match(r"\d{4}-\d{2}-\d{2}", pdf_path.stem):
            date = pdf_path.stem[:10]

        # Convert to markdown
        markdown = to_markdown(data, date)

        # Write output
        output_path = output_dir / f"{pdf_path.stem}.md"
        output_path.write_text(markdown)

        print("  ✓ Converted to markdown\n")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return False


def process_markdown(md_path: Path, output_dir: Path) -> bool:
    """Process a single markdown file. Returns True on success."""
    print(f"Processing: {md_path.name}")
    try:
        # Read and add frontmatter if needed
        content = md_path.read_text()
        content = ensure_frontmatter(content, md_path.stem)

        # Write output
        output_path = output_dir / md_path.name
        output_path.write_text(content)

        print("  ✓ Added frontmatter\n")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return False


def main():
    """Main entry point - process all reports and generate site."""
    # Setup directories
    reports_dir = Path("reports")
    output_dir = Path("doc/report")
    reports_dir.mkdir(exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find input files
    pdf_files = list(reports_dir.glob("*.pdf"))
    md_files = list(reports_dir.glob("*.md"))
    total = len(pdf_files) + len(md_files)

    print(f"Found {len(pdf_files)} PDFs and {len(md_files)} markdown files\n")

    if total == 0:
        print("No files found. Add PDFs or markdown to reports/ directory.")
        return

    # Process all files
    success = 0
    for pdf_path in pdf_files:
        if process_pdf(pdf_path, output_dir):
            success += 1

    for md_path in md_files:
        if process_markdown(md_path, output_dir):
            success += 1

    # Generate report table
    print("Generating report table...")
    try:
        table = generate_report_table(output_dir)
        (output_dir / "report-table.txt").write_text(table)
        print("  ✓ Report table created\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

    # Print summary
    print("=" * 60)
    print(f"Successfully processed {success}/{total} files")
    print("=" * 60)


if __name__ == "__main__":
    main()
