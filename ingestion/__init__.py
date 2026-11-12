"""Secure PDF reading for transcript uploads.

This is the PDF subset of the `ingestion` package from the AIMate project (models, textutil, pdf, secure,
worker are unchanged copies; see their docstrings for what is checked and what is not). Keep them in sync
with AIMate by hand, or move the package into a shared library when a third project needs it.

    text, warnings = pdf_to_text(data, "call.pdf")

A PDF is pre-scanned for JavaScript, launch actions, embedded files and similar, checked against size,
page and object limits, and parsed in a separate process with a scrubbed environment, a timeout and no
network. Hidden (white or tiny) text is removed and reported. Settings: INGEST_PDF_SANDBOX=0 parses in
process; INGEST_PDF_POLICY=warn accepts risky PDFs with a warning; INGEST_PDF_MAX_PAGES, _MAX_OBJECTS,
_TIMEOUT and INGEST_OCR_LANG tune the limits.
"""
import os

from .models import IngestionError, ParsedDocument
from .secure import parse_pdf_checked, parse_pdf_sandboxed

__all__ = ["IngestionError", "pdf_to_text", "read_pdf"]


def read_pdf(data: bytes, source: str, sandbox=None) -> ParsedDocument:
    """Read a PDF defensively. `sandbox=False`, or INGEST_PDF_SANDBOX=0, parses in this process."""
    use_sandbox = os.getenv("INGEST_PDF_SANDBOX", "1") != "0" if sandbox is None else sandbox
    return parse_pdf_sandboxed(data, source) if use_sandbox else parse_pdf_checked(data, source)


def pdf_to_text(data: bytes, source: str = "document.pdf", sandbox=None):
    """(text, warnings) for a PDF: the extracted blocks in reading order, one per line. Tables come out
    as markdown rows. The text is empty when the PDF has no readable text (a scan without OCR); the
    warnings then say why."""
    doc = read_pdf(data, source, sandbox)
    return "\n".join(block.text for block in doc.blocks), doc.warnings
