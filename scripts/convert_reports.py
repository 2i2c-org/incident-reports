"""
Convert incident reports from PDFs and markdown to MyST format.

Usage:
    python scripts/convert_reports.py
"""

import re
from pathlib import Path
import pdfplumber
import yaml


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def parse_pdf_incident(pdf_path: Path) -> dict:
    """Parse a PagerDuty incident PDF and extract all sections."""
    text = extract_text_from_pdf(pdf_path)

    # Clean up two-column layout artifacts
    text = re.sub(r'OWNER OF REVIEW PROCESS\s*', '\n', text)
    text = re.sub(r'IMPACT TIME\s*', '\n', text)
    text = re.sub(r'DURATION\s*', '\n', text)
    text = re.sub(r'\*All times listed.*?Pacific Time.*?\)', '', text, flags=re.DOTALL)

    # Extract title
    title_match = re.search(r'^(.*?)\s*Status:', text, re.DOTALL)
    title = ' '.join(title_match.group(1).split()) if title_match else "Untitled Incident"

    # Extract metadata
    owner_match = re.search(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', text, re.MULTILINE)
    owner = owner_match.group(0) if owner_match else "Unknown"

    impact_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2}\s+at\s+\d{1,2}:\d{2}\s+to\s+[A-Z][a-z]{2}\s+\d{1,2}\s+at\s+\d{1,2}:\d{2})', text)
    impact_time = impact_match.group(1) if impact_match else "Unknown"

    duration_match = re.search(r'(\d+[mh]\s+\d+[ms])', text)
    duration = duration_match.group(1) if duration_match else "Unknown"

    status_match = re.search(r'Status:\s*(\w+)', text)
    status = status_match.group(1) if status_match else "Unknown"

    # Extract sections using simple pattern
    def get_section(start, end_markers):
        pattern = rf'{re.escape(start)}\s*\n(.*?)(?=\n(?:{"|".join(re.escape(m) for m in end_markers)})|\Z)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            if 'No comments added' in content:
                content = content.replace('No comments added', '').strip()
            return content if content else ""
        return ""

    # Parse timeline
    timeline_match = re.search(r'Timeline\s*\n(.*)', text, re.DOTALL)
    timeline = ""
    if timeline_match:
        lines = timeline_match.group(1).strip().split('\n')
        current_date = None
        entries = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('INCIDENT #'):
                continue

            # Date header
            if re.match(r'^[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4}$', line):
                if current_date and entries:
                    timeline += f"\n### {current_date}\n\n| Time | Event |\n| --- | --- |\n"
                    timeline += "\n".join(entries) + "\n"
                    entries = []
                current_date = line
            # Time entry
            elif match := re.match(r'^(\d{1,2}:\d{2}\s*[AP]M)\s+(.*)', line):
                entries.append(f"| {match.group(1)} | {match.group(2)} |")
            # Continuation
            elif entries and not line.startswith(('Triggered', 'Resolved')):
                entries[-1] = entries[-1].rstrip(' |') + " " + line + " |"

        # Add last date
        if current_date and entries:
            timeline += f"\n### {current_date}\n\n| Time | Event |\n| --- | --- |\n"
            timeline += "\n".join(entries)

    return {
        'title': title,
        'status': status,
        'owner': owner,
        'impact_time': impact_time,
        'duration': duration,
        'overview': get_section('Overview', ['What Happened', 'Resolution', 'Where we got lucky', 'What Went Well']),
        'what_happened': get_section('What Happened', ['Resolution', 'Where we got lucky', 'What Went Well']),
        'resolution': get_section('Resolution', ['Where we got lucky', 'What Went Well', "What Didn't Go So Well"]),
        'where_we_got_lucky': get_section('Where we got lucky', ['What Went Well', "What Didn't Go So Well"]),
        'what_went_well': get_section('What Went Well?', ["What Didn't Go So Well", 'Action Items']),
        'what_didnt_go_well': get_section("What Didn't Go So Well?", ['Action Items', 'Timeline']),
        'action_items': get_section('Action Items', ['Timeline']),
        'timeline': timeline,
    }


def to_markdown(data: dict, date: str) -> str:
    """Convert parsed data to MyST markdown."""
    md = f"""---
title: "{data['title']}"
date: {date}
---

# {data['title']}

| Field | Value |
| --- | --- |
| **Impact Time** | {data['impact_time']} |
| **Duration** | {data['duration']} |

"""

    # Add sections if they exist
    sections = [
        ('Overview', data.get('overview')),
        ('What Happened', data.get('what_happened')),
        ('Resolution', data.get('resolution')),
        ('Where We Got Lucky', data.get('where_we_got_lucky')),
        ('What Went Well', data.get('what_went_well')),
        ("What Didn't Go So Well", data.get('what_didnt_go_well')),
        ('Action Items', data.get('action_items')),
        ('Timeline', data.get('timeline')),
    ]

    for title, content in sections:
        if content:
            md += f"## {title}\n\n{content}\n\n"

    return md


def ensure_frontmatter(content: str, filename: str) -> str:
    """Add MyST frontmatter to markdown if missing."""
    if content.strip().startswith('---'):
        return content

    # Extract date and title
    date = filename[:10] if re.match(r'\d{4}-\d{2}-\d{2}', filename) else "Unknown"
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else filename.replace('-', ' ').title()

    return f"""---
title: "{title}"
date: {date}
---

{content}"""


def generate_report_table(report_dir: Path) -> str:
    """Generate summary table of all reports."""
    table = "| Date | Report | Status | Duration |\n| --- | --- | --- | --- |\n"

    for md_file in sorted(report_dir.glob("*.md"), reverse=True):
        content = md_file.read_text()

        # Parse frontmatter
        frontmatter = {}
        if content.strip().startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                except:
                    pass

        title = frontmatter.get('title', md_file.stem)
        date = frontmatter.get('date', md_file.stem[:10])

        # Extract status and duration from content
        status = re.search(r'\|\s*\*\*Status\*\*\s*\|\s*(.+?)\s*\|', content)
        status = status.group(1).strip() if status else "Unknown"

        duration = re.search(r'\|\s*\*\*Duration\*\*\s*\|\s*(.+?)\s*\|', content)
        duration = duration.group(1).strip() if duration else "Unknown"

        table += f"| {date} | [{title}](./report/{md_file.stem}) | {status} | {duration} |\n"

    return table


def main():
    """Process all reports in reports/ directory."""
    reports_dir = Path("reports")
    output_dir = Path("doc/report")

    # Create directories
    reports_dir.mkdir(exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find files
    pdf_files = list(reports_dir.glob("*.pdf"))
    md_files = list(reports_dir.glob("*.md"))

    print(f"Found {len(pdf_files)} PDFs and {len(md_files)} markdown files\n")

    if not pdf_files and not md_files:
        print("No files found. Add PDFs or markdown to reports/ directory.")
        return

    success = 0

    # Process PDFs
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        try:
            data = parse_pdf_incident(pdf_path)
            date = pdf_path.stem[:10] if re.match(r'\d{4}-\d{2}-\d{2}', pdf_path.stem) else "Unknown"
            markdown = to_markdown(data, date)
            (output_dir / f"{pdf_path.stem}.md").write_text(markdown)
            print(f"  ✓ Converted to markdown\n")
            success += 1
        except Exception as e:
            print(f"  ✗ Error: {e}\n")

    # Process markdown files
    for md_path in md_files:
        print(f"Processing: {md_path.name}")
        try:
            content = md_path.read_text()
            content = ensure_frontmatter(content, md_path.stem)
            (output_dir / md_path.name).write_text(content)
            print(f"  ✓ Added frontmatter\n")
            success += 1
        except Exception as e:
            print(f"  ✗ Error: {e}\n")

    # Generate report table
    print("Generating report table...")
    try:
        table = generate_report_table(output_dir)
        (output_dir / "report-table.txt").write_text(table)
        print("  ✓ Report table created\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

    print(f"{'='*60}")
    print(f"Successfully processed {success}/{len(pdf_files) + len(md_files)} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
