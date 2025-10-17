"""
Configuration for PDF to Markdown conversion.

This module contains all the patterns, section names, and configuration
used to parse PagerDuty incident reports and convert them to MyST markdown.
"""

from pathlib import Path

# Paths
TEMPLATE_PATH = Path(__file__).parent / "report-template.md"
REPORTS_DIR = Path("reports")
OUTPUT_DIR = Path("doc/report")
REPORT_TABLE_PATH = OUTPUT_DIR / "report-table.txt"

# PagerDuty PDF Structure Patterns
# PagerDuty PDFs have this structure:
# 1. Metadata fields (OWNER, IMPACT TIME, DURATION)
# 2. Timezone declaration (*All times listed in...)
# 3. Title (may span multiple lines)
# 4. Status: Draft/Reviewed
# 5. Sections (Overview, What Happened, etc.)

# Regex patterns for extracting metadata from PDF text
METADATA_PATTERNS = {
    "status": r"Status:\s*(\w+)",  # Captures first word after "Status:"
    "review_owner": r"OWNER OF REVIEW PROCESS\n([^\n]+)",  # First line after label
    "impact_time": r"IMPACT TIME\n([^\n]+)",  # First line after label
    "duration": r"DURATION\n([^\n]+)",  # First line after label
}

# Section patterns - these extract content between section headers
SECTION_PATTERNS = {
    "overview": r"Overview\n(.*?)(?=What Happened)",
    "what_happened": r"What Happened\n(.*?)(?=Resolution)",
    "resolution": r"Resolution\n(.*?)(?=Where we got lucky)",
    "where_we_got_lucky": r"Where we got lucky\n(.*?)(?=What Went Well\?)",
    "what_went_well": r"What Went Well\?\n(.*?)(?=What Didn\'t Go So Well\?)",
    "what_didnt_go_so_well": r"What Didn\'t Go So Well\?\n(.*?)(?=Action Items)",
    "action_items": r"Action Items\n(.*?)(?=Timeline)",
}

# Section headers - used for empty section removal
SECTION_HEADERS = [
    "Overview",
    "Action Items",
    "What Happened",
    "Resolution",
    "Timeline",
    "Where we got lucky",
    "What Went Well\\?",
    "What Didn't Go So Well\\?",
]

# Metadata fields that appear in both the table and frontmatter
METADATA_FIELDS = ["status", "review_owner", "impact_time", "duration"]

# Timeline pattern - looks for timestamp at start of line
TIMELINE_TIMESTAMP_PATTERN = r"\d{1,2}:\d{2} [AP]M"

# Title extraction patterns
TIMEZONE_PREFIX = "*All times"
# Lines containing these keywords followed by "." are considered timezone declarations
TIMEZONE_INDICATORS = ["Time", "London", "Edinburgh"]

# Metadata keywords to exclude when extracting title
METADATA_KEYWORDS = ["OWNER", "IMPACT", "DURATION"]

# Template placeholder strings
TEMPLATE_PLACEHOLDERS = {
    "title": "YYYY-MM-DD - Incident Title",
    "date": "date: 2025-01-01",
    "output_path": "output: reports/YYYY-MM-DD-incident-title.md",
    "source_file": "SOURCE-FILE-PLACEHOLDER",
    "action_items": "- [ ] Action item 1\n- [ ] Action item 2\n",
    "timeline_placeholder": r"\| Time \| Event \|\n\| --- \| --- \|\n\| \| \|",
}
