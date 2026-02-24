# 2i2c Incident Reports

**Public incident reports for 2i2c managed cloud infrastructure.**

This site documents 2i2c's engineering team incidents, their resolutions, and what we learned.

🔗 **View the site:** https://2i2c-org.github.io/incident-reports/

## Why This Exists

- **Transparency**: Share what goes wrong and how we fix it
- **Learning**: Document lessons learned from each incident
- **Accountability**: Public record of our service reliability
- **Knowledge sharing**: Help others learn from our experiences

## Add a Report

1. Export PDF from PagerDuty
2. Add to `reports/` folder
3. Commit and push

GitHub Actions automatically converts the PDF and deploys the updated site using [docling](https://github.com/docling-project/docling)

## Local Development

```bash
nox -s docs-live
```

## How It Works

This repository roughly follows a 3-step process:

- Parse PDFs in `reports/`
- Convert them to markdown using [docling](https://github.com/docling-project/docling)
- Parse the markdown for metadata with hacky regexes (e.g. "duration")
- Output MyST markdown to be parsed by the MyST site in `docs/`

GitHub Actions automates all of the above any time we change the repository.

_**Note**: There is some hacky logic that parses the PDFs and extracts standardized metadata from it. I did my best to figure out the proper regexes, but this is likely brittle and will break if we change the format of our incident reports...it'll probably miss some stuff too_.

## Who is responsible for this repository

- The Product and Services team is responsible for the content in `reports/`, and for adding new ones to this repository.
- The Marketing team is responsible for the code and infrastructure that generates a MyST site from these PDFs.
