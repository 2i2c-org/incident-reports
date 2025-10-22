# 2i2c Incident Reports

Incident reports for 2i2c managed services, published as a [MyST website](https://mystmd.org).

The site is automatically built and deployed to GitHub Pages when changes are pushed to `main`.

## Quick Start

```bash
# Build and view the site locally
nox -s docs-live
```

## Adding New Reports

1. Export incident postmortem from PagerDuty as PDF
2. Add PDF to `reports/` folder
3. Commit and push to `main`

GitHub Actions will automatically convert the PDF and deploy the updated site!

## How It Works

- `reports/` - Store PDF exports or markdown files here
- `scripts/convert_reports.py` - Converts PDFs -> Markdown
- `doc/report/` - Generated MyST markdown files (not checked into git)
- `noxfile.py` - Builds the MyST website

The conversion script:
- Parses PDF text and extracts sections
- Generates clean markdown with MyST frontmatter
- Handles both PDFs and markdown files
- Creates a summary table of all reports

## Setup GitHub Pages

First-time setup (do once):

1. Go to repository Settings → Pages
2. Set Source to "GitHub Actions"
3. Push a change to `main` branch
4. Site will be live at `https://2i2c-org.github.io/incident-reports/`

## Manual Usage

```bash
# Convert reports to markdown
python scripts/convert_reports.py

# Build the site
cd doc && myst build --html
```