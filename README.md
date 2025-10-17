# 2i2c Incident Reports

The 2i2c infrastructure is constantly evolving. As people use our hubs,
different issues often arise that result in new needs for development and
updates to the deployment. 2i2c follows a process of transparent and blameless
post-mortems to address these issues now, and prevent them from happening in the
future. This repository contains those reports.

## To Add a New Report

1. Generate a report within PagerDuty (File → Export as PDF)
2. Upload the PDF to the `reports/` directory
3. Commit and push - that's it! The site will auto-rebuild.

**Note**: You can also add manually-written markdown reports directly to `reports/`.

## Our Report Website

We distribute these reports as a [MyST website](https://mystmd.org) for easier reading and discoverability.

### Building Locally

```bash
# Build and serve with live reload
nox -s docs-live

# Build once (output in doc/_build/)
nox -s docs

# Just convert PDFs without building the site
nox -s convert
```

## How It Works

### Repository Structure

```
incident-reports/
├── reports/              # Source PDFs and markdown files
│   ├── 2025-10-16-incident-name.pdf
│   └── 2025-10-15-another-incident.md
├── scripts/              # Conversion scripts
│   ├── convert_pdfs.py   # Main conversion orchestrator
│   ├── config.py         # Configuration and patterns
│   └── report-template.md # Template for generated markdown
├── doc/                  # MyST site source
│   ├── index.md          # Landing page
│   ├── myst.yml          # MyST configuration
│   └── report/           # Generated reports (git-ignored)
│       ├── 2025-10-16-incident-name.md
│       └── report-table.txt  # Auto-generated table
├── noxfile.py            # Build automation
└── requirements.txt      # Python dependencies
```

### Conversion Process

The conversion script (`scripts/convert_pdfs.py`) automates the following:

1. **PDF Text Extraction**: Uses PyMuPDF to extract raw text from PDFs
2. **Structured Data Parsing**: Extracts:
   - Title (may span multiple lines)
   - Metadata (status, owner, impact time, duration)
   - Sections (overview, what happened, resolution, etc.)
   - Timeline entries (timestamped events)
   - Action items
3. **Template Population**: Fills in `scripts/report-template.md` with extracted data
4. **Markdown Generation**: Outputs clean MyST-formatted files to `doc/report/`
5. **Table Generation**: Creates summary table for index page

### PagerDuty PDF Format

The script expects PDFs exported from PagerDuty with this structure:

```
OWNER OF REVIEW PROCESS
<Name>

IMPACT TIME
<Date and time>

DURATION
<Duration>

*All times listed in <Timezone>.

<Multi-line Title>

Status: Draft/Reviewed

Overview
<Content>

What Happened
<Content>

Resolution
<Content>

Timeline
<Time> <Event>
<Time> <Event>
...
```

### Configuration

All parsing patterns and configuration live in `scripts/config.py`:
- Section names and regex patterns
- Metadata field patterns
- Template placeholders
- File paths

This makes it easy to customize the conversion process without touching the main logic.

## Troubleshooting

**Problem**: PDF not converting correctly
- Check if the PDF matches the expected PagerDuty format
- Look for parsing errors in the script output
- Manually inspect the PDF text to see if sections are labeled correctly

**Problem**: Empty sections in output
- The script removes empty trailing sections automatically
- If a section appears empty, check if the content exists in the PDF

**Problem**: Title extraction issues
- Titles are extracted from between the timezone line and "Status:"
- Multi-line titles are supported and joined with spaces
- Timezone descriptions are automatically filtered out

