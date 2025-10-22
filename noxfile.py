import nox

@nox.session
def docs(session):
    """Build the MyST site."""
    session.install("-r", "requirements.txt")
    session.run("python", "scripts/convert_reports.py")
    with session.cd("doc"):
        session.run("myst", "build", "--html")

@nox.session(name="docs-live")
def docs_live(session):
    """Build and serve the MyST site with a live server."""
    session.install("-r", "requirements.txt")
    session.run("python", "scripts/convert_reports.py")
    with session.cd("doc"):
        session.run("myst", "start")
