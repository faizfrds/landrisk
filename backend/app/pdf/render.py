"""Renders the report_md into a PDF.

WeasyPrint chosen over reportlab: report_md -> HTML -> a single Jinja2
template fits WeasyPrint's CSS-driven model far better than hand-drawing
with reportlab's canvas API. Requires native libs (Pango/Cairo/
GDK-Pixbuf) -- on macOS: `brew install pango` then `pip install
weasyprint`. This is a local setup prerequisite distinct from `pip
install -e .`, documented in the README.
"""

from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def render_pdf(report_md: str, report_id: str, parcel_id: str, data_version: str) -> bytes:
    # Imported lazily: WeasyPrint needs native Pango/Cairo/GDK-Pixbuf libs
    # (see README setup steps) that aren't required just to import the
    # rest of the app -- keeps business-logic tests independent of this
    # native dependency.
    from weasyprint import HTML

    body_html = markdown.markdown(report_md, extensions=["extra"])
    template = _env.get_template("report.html.jinja2")
    html = template.render(
        body_html=body_html, report_id=report_id, parcel_id=parcel_id, data_version=data_version
    )
    return HTML(string=html).write_pdf()
