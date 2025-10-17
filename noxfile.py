import nox

@nox.session
def convert(session):
    """Convert PDFs to markdown files."""
    session.install("uv")
    session.run("uv", "pip", "install", "-r", "requirements.txt")
    session.run("python", "scripts/convert_pdfs.py")

@nox.session
def docs(session):
    """Build the MyST site."""
    convert(session)
    with session.cd('doc'):
        session.run("myst", "build", "--html")

@nox.session(name="docs-live")
def docs_live(session):
    """Build and serve the MyST site with a live server."""
    convert(session)
    with session.cd('doc'):
        session.run("myst", "start")
