# 2i2c Incident Reports

**Public incident reports for 2i2c managed cloud infrastructure.**

We believe in transparency. This site documents incidents, their resolutions, and what we learned.

🔗 **View the site:** https://2i2c-org.github.io/incident-reports/

## Why This Exists

- **Transparency**: Share what goes wrong and how we fix it
- **Learning**: Document lessons learned from each incident
- **Accountability**: Public record of our service reliability
- **Knowledge sharing**: Help others learn from our experiences

## Add a Report


1. Export PDF from PagerDuty
2. Add to reports/ folder
3. Commit and push

GitHub Actions automatically converts the PDF and deploys the updated site.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt
cd doc && myst build --html

# OR, do it with one command
nox -s docs-live
```

## How It Works

1. **PDFs go in** `reports/` folder
2. **Script converts** PDFs → Markdown (extracts sections, timelines, metadata)
3. **MyST builds** Markdown → HTML website
4. **GitHub Pages** hosts the site

## Who is responsible for this repository

- The Product and Services team is responsible for the content in the incident reports, and for adding new ones to this repository.
- The Marketing team is responsible for the code and infrastructure that generates a MyST site from these PDFs.

---

Built with [MyST](https://mystmd.org) • Maintained by [2i2c](https://2i2c.org)
