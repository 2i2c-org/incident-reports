"""
Convert PagerDuty incident report PDFs to MyST markdown files.

This script processes PDF incident reports from PagerDuty and converts them into
MyST-formatted markdown files suitable for building a documentation site.

The script:
1. Reads PDF files from the reports/ directory
2. Extracts structured data (title, metadata, sections, timeline, action items)
3. Applies a template to generate clean markdown files
4. Outputs files to doc/report/ directory
5. Generates a summary table for the index page

Usage:
    python scripts/convert_pdfs.py

Dependencies:
    - PyMuPDF (fitz): For PDF text extraction
    - rich: For progress bars
"""

import re
from pathlib import Path
import fitz  # PyMuPDF
from rich.progress import track
from config import (
    TEMPLATE_PATH,
    REPORTS_DIR,
    OUTPUT_DIR,
    REPORT_TABLE_PATH,
    METADATA_PATTERNS,
    SECTION_PATTERNS,
    SECTION_HEADERS,
    METADATA_FIELDS,
    TIMELINE_TIMESTAMP_PATTERN,
    TIMEZONE_PREFIX,
    TIMEZONE_INDICATORS,
    METADATA_KEYWORDS,
    TEMPLATE_PLACEHOLDERS,
)


def get_pdf_text(pdf_path):
    """
    Extract all text from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        str: Concatenated text from all pages
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def extract_title_from_pdf(ocr_text):
    """
    Extract the incident title from PagerDuty PDF text.

    PagerDuty PDFs have this structure:
    - Metadata fields (OWNER, IMPACT TIME, DURATION)
    - Timezone declaration line (*All times listed in...)
    - Title (may span multiple lines)
    - Status: Draft/Reviewed

    The title appears between the timezone line and "Status:".
    It may span multiple lines and should exclude timezone descriptions.

    Args:
        ocr_text: Raw text extracted from PDF

    Returns:
        str: Extracted title, or None if not found
    """
    # Find all text before "Status:"
    title_section = re.search(r"^(.*?)(?=\nStatus:)", ocr_text, re.DOTALL)
    if not title_section:
        return None

    # Split into lines and clean up
    lines = [
        line.strip()
        for line in title_section.group(1).strip().split("\n")
        if line.strip()
    ]

    # Find where the title starts (after timezone declaration)
    title_start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith(TIMEZONE_PREFIX):
            title_start_idx = i + 1
            break

    # Extract title lines (skip metadata and timezone lines)
    if title_start_idx > 0:
        title_lines = []
        for i in range(title_start_idx, len(lines)):
            line = lines[i]
            # Skip metadata keywords
            if any(keyword in line for keyword in METADATA_KEYWORDS):
                continue
            # Skip timezone description lines (e.g., "Pacific Time (US & Canada).")
            is_timezone = (
                any(indicator in line for indicator in TIMEZONE_INDICATORS)
                and line.endswith(".")
            )
            if is_timezone:
                continue
            title_lines.append(line)

        if title_lines:
            return " ".join(title_lines)

    # Fallback: take the last non-metadata line
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if (
            line
            and not line.startswith(TIMEZONE_PREFIX)
            and not any(keyword in line for keyword in METADATA_KEYWORDS)
        ):
            return line

    return None


def extract_metadata_from_pdf(ocr_text):
    """
    Extract metadata fields (status, owner, time, duration) from PDF text.

    Args:
        ocr_text: Raw text extracted from PDF

    Returns:
        dict: Metadata fields with keys from METADATA_PATTERNS
    """
    metadata = {}
    for key, pattern in METADATA_PATTERNS.items():
        match = re.search(pattern, ocr_text)
        if match:
            value = match.group(1).strip()
            # For status, only keep the first word (avoid "Draft Reviewed")
            if key == "status":
                value = value.split()[0] if value else value
            metadata[key] = value
    return metadata


def extract_sections_from_pdf(ocr_text):
    """
    Extract content sections (Overview, What Happened, etc.) from PDF text.

    Args:
        ocr_text: Raw text extracted from PDF

    Returns:
        dict: Section content with keys from SECTION_PATTERNS
    """
    sections = {}
    for key, pattern in SECTION_PATTERNS.items():
        match = re.search(pattern, ocr_text, re.DOTALL)
        if match:
            sections[key] = match.group(1).strip()
    return sections


def extract_timeline_from_pdf(ocr_text):
    """
    Extract and format timeline entries from PDF text.

    Timeline entries in PDFs have timestamps like "3:42 PM" followed by event text.
    Events may span multiple lines.

    Args:
        ocr_text: Raw text extracted from PDF

    Returns:
        str: Markdown table rows (without header), or None if no timeline found

    Example output:
        | 3:42 PM | Engineer notices issue\\n| 4:00 PM | Issue resolved
    """
    timeline_match = re.search(r"Timeline\n(.*)", ocr_text, re.DOTALL)
    if not timeline_match:
        return None

    timeline_text = timeline_match.group(1).strip()
    timeline_entries = []
    current_entry = None

    for line in timeline_text.split("\n"):
        # Check if line starts with a timestamp
        if re.match(TIMELINE_TIMESTAMP_PATTERN, line):
            # Save previous entry if exists
            if current_entry:
                timeline_entries.append(current_entry)
            # Start new entry with proper format: | time + event |
            current_entry = f"| {line.strip()} |"
        elif line.strip() and current_entry:
            # Append continuation to current entry
            current_entry += f" {line.strip()}"

    # Don't forget the last entry
    if current_entry:
        timeline_entries.append(current_entry)

    return "\n".join(timeline_entries) if timeline_entries else None


def parse_pdf_content(ocr_text):
    """
    Parse all structured data from PagerDuty PDF text.

    This is the main parsing function that extracts:
    - Title
    - Metadata (status, owner, impact time, duration)
    - Sections (overview, what happened, resolution, etc.)
    - Timeline entries

    Args:
        ocr_text: Raw text extracted from PDF

    Returns:
        dict: All extracted data with keys:
            - title: Incident title
            - status, review_owner, impact_time, duration: Metadata
            - overview, what_happened, resolution, etc.: Section content
            - timeline: Formatted timeline table rows
    """
    data = {}

    # Extract title
    title = extract_title_from_pdf(ocr_text)
    if title:
        data["title"] = title

    # Extract metadata
    metadata = extract_metadata_from_pdf(ocr_text)
    data.update(metadata)

    # Extract sections
    sections = extract_sections_from_pdf(ocr_text)
    data.update(sections)

    # Extract timeline
    timeline = extract_timeline_from_pdf(ocr_text)
    if timeline:
        data["timeline"] = timeline

    return data


def filename_to_title(filename_stem):
    """
    Convert a filename to a human-readable title.

    Example:
        '2025-10-16-oom-quota-enforcer' -> 'OOM Quota Enforcer'

    Args:
        filename_stem: Filename without extension

    Returns:
        str: Human-readable title
    """
    # Extract date and description parts (YYYY-MM-DD-description)
    parts = filename_stem.split("-", 3)
    if len(parts) >= 4:
        description = parts[3]
        # Convert: hyphens/underscores to spaces, apply title case
        description = description.replace("-", " ").replace("_", " ").title()
        return description
    else:
        # Fallback: use filename as-is
        return filename_stem


def populate_template(template_content, data, pdf_path):
    """
    Populate the markdown template with extracted data.

    This function:
    1. Replaces title and date
    2. Updates file paths in frontmatter
    3. Populates metadata table
    4. Fills in section content
    5. Formats timeline table
    6. Removes empty sections

    Args:
        template_content: Raw template markdown content
        data: Extracted data from parse_pdf_content()
        pdf_path: Path object for the source PDF

    Returns:
        str: Populated markdown content
    """
    content = template_content

    # Replace title - use extracted title or generate from filename
    human_title = data.get("title") or filename_to_title(pdf_path.stem)
    content = content.replace(TEMPLATE_PLACEHOLDERS["title"], human_title)

    # Replace date (YYYY-MM-DD from filename)
    date_str = pdf_path.stem[:10]
    content = content.replace(TEMPLATE_PLACEHOLDERS["date"], f"date: {date_str}")

    # Replace output path in frontmatter
    content = content.replace(
        TEMPLATE_PLACEHOLDERS["output_path"],
        f"output: reports/{pdf_path.stem}.md",
    )

    # Replace source file for downloads
    content = content.replace(
        TEMPLATE_PLACEHOLDERS["source_file"],
        pdf_path.name,
    )

    # Remove placeholder action items
    content = content.replace(TEMPLATE_PLACEHOLDERS["action_items"], "")

    # Process each data field
    for key, value in data.items():
        if not value:
            continue

        if key == "timeline":
            # Replace timeline table placeholder with actual entries
            content = re.sub(
                TEMPLATE_PLACEHOLDERS["timeline_placeholder"],
                f"| Time | Event |\n| --- | --- |\n{value}",
                content,
            )
        elif key == "title":
            # Already handled above
            continue
        elif key in METADATA_FIELDS:
            # Populate metadata table
            field_name = key.replace("_", " ").title()
            pattern = f"\\| \\*\\*{field_name}\\*\\* \\| \\|"
            replacement = f"| **{field_name}** | {value} |"
            content = re.sub(pattern, replacement, content)

            # Also update frontmatter exports section
            content = re.sub(
                f"(frontmatter:\\s*\\n.*?{key}:)(?=\\s*\\n)",
                f"\\1 {value}",
                content,
                flags=re.DOTALL,
            )
        else:
            # Add section content
            section_title = key.replace("_", " ").title()
            content = content.replace(
                f"{section_title}\n\n", f"{section_title}\n\n{value}\n\n"
            )

    # Remove empty sections at the end of the document
    content = remove_empty_trailing_sections(content)

    return content


def remove_empty_trailing_sections(content):
    """
    Remove empty sections from the end of the document.

    Empty sections are those that have a header but no content before
    the next section or end of file.

    Args:
        content: Markdown content

    Returns:
        str: Content with trailing empty sections removed
    """
    # First pass: remove sections followed immediately by another section
    for header in SECTION_HEADERS:
        for next_header in SECTION_HEADERS:
            pattern = f"## {header}\n\n## {next_header}"
            replacement = f"## {next_header}"
            content = re.sub(pattern, replacement, content)

    # Second pass: remove empty sections at the very end
    while True:
        old_content = content
        # Match: newline, section header, one or more newlines, optional whitespace, end
        content = re.sub(r"\n## [^\n]+\n+\s*$", "", content)
        if content == old_content:
            break

    return content


def convert_pdf_to_markdown(pdf_path_str, ocr_text):
    """
    Convert a PDF incident report to markdown format.

    Args:
        pdf_path_str: String path to PDF file
        ocr_text: Extracted text from PDF (from get_pdf_text)

    Returns:
        None: Writes markdown file to OUTPUT_DIR
    """
    pdf_path = Path(pdf_path_str)

    # Check template exists
    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}")
        return

    # Parse PDF content
    template_content = TEMPLATE_PATH.read_text()
    data = parse_pdf_content(ocr_text)

    # Populate template
    content = populate_template(template_content, data, pdf_path)

    # Write output file
    md_path = OUTPUT_DIR / f"{pdf_path.stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)

    with open(md_path, "w") as f:
        f.write(content)

    print(f"Converted {pdf_path} to {md_path}")


def handle_markdown_file(md_path):
    """
    Process a markdown incident report (non-PDF).

    For markdown files, we:
    1. Ensure they have proper frontmatter with title
    2. Add download link to the source markdown file
    3. Copy to the output directory

    Args:
        md_path: Path object for the markdown file

    Returns:
        str: Human-readable title extracted or generated from filename
    """
    # Ensure .md extension
    output_name = md_path.name if md_path.suffix == ".md" else f"{md_path.name}.md"
    new_md_path = OUTPUT_DIR / output_name

    content = md_path.read_text()

    # Add frontmatter if missing or incomplete
    if content.startswith("---"):
        frontmatter_section = content.split("---")[1]

        # Add title if missing
        if "title:" not in frontmatter_section:
            human_title = filename_to_title(md_path.stem)
            frontmatter_end = content.find("---", 3)
            if frontmatter_end > 0:
                content = (
                    content[:frontmatter_end]
                    + f"title: {human_title}\n"
                    + content[frontmatter_end:]
                )

        # Add download link if missing
        if "downloads:" not in frontmatter_section:
            frontmatter_end = content.find("---", 3)
            if frontmatter_end > 0:
                download_config = (
                    f"downloads:\n"
                    f"  - file: ../../reports/{md_path.name}\n"
                    f"    title: Download Source Report\n"
                )
                content = (
                    content[:frontmatter_end] + download_config + content[frontmatter_end:]
                )
    else:
        # No frontmatter - add one with title and download
        human_title = filename_to_title(md_path.stem)
        content = (
            f"---\n"
            f"title: {human_title}\n"
            f"downloads:\n"
            f"  - file: ../../reports/{md_path.name}\n"
            f"    title: Download Source Report\n"
            f"---\n\n{content}"
        )

    # Write to destination
    with open(new_md_path, "w") as f_out:
        f_out.write(content)

    print(f"Copied {md_path} to {new_md_path}")

    # Return title for table generation
    return human_title if "human_title" in locals() else filename_to_title(md_path.stem)


def generate_report_table(all_files):
    """
    Generate a markdown table summarizing all reports.

    The table includes date and title for each report, linking to the
    report pages. This table is included in the index page.

    Args:
        all_files: List of Path objects for all report files

    Returns:
        str: Markdown table content
    """
    report_table = "| Date | Report |\n| --- | --- |\n"

    for file_path in track(all_files, description="Processing reports..."):
        if file_path.suffix == ".pdf":
            ocr_text = get_pdf_text(file_path)
            data = parse_pdf_content(ocr_text)
            # Use extracted title or generate from filename
            human_title = data.get("title") or filename_to_title(file_path.stem)

            convert_pdf_to_markdown(file_path, ocr_text)
            # MyST links don't need .md extension
            # Use report/ prefix since table is included from doc/index.md
            report_table += (
                f"| {file_path.stem[:10]} | [{human_title}](./report/{file_path.stem}) |\n"
            )
        elif file_path.suffix == ".md":
            md_title = handle_markdown_file(file_path)
            # MyST links don't need .md extension
            # Use report/ prefix since table is included from doc/index.md
            report_table += (
                f"| {file_path.stem[:10]} | [{md_title}](./report/{file_path.stem}) |\n"
            )

    return report_table


def main():
    """Main entry point for the conversion script."""
    # Get all PDF and markdown files from reports directory
    all_files = sorted(
        list(REPORTS_DIR.glob("*.pdf")) + list(REPORTS_DIR.glob("*.md")),
        reverse=True,  # Newest first
    )

    # Generate report table and convert files
    report_table = generate_report_table(all_files)

    # Write the report table
    with open(REPORT_TABLE_PATH, "w") as f:
        f.write(report_table)


if __name__ == "__main__":
    main()
