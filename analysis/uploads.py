"""Turning an uploaded file into transcript text, defensively.

The file type is decided by its content, not its name: anything that starts like a PDF goes through the
secure PDF reader (see ingestion/), even if it is called transcript.txt, so renaming a file cannot route it
around the checks. Everything else must be UTF-8 text. Uploads are size-capped before they are read, and when
a ClamAV daemon is configured (INGEST_CLAMD_HOST or INGEST_CLAMD_SOCKET, see ingestion/scanner.py) every upload
is virus-scanned before anything parses it. A required scan that cannot complete refuses the upload.
"""
import os

from ingestion import IngestionError, pdf_to_text
from ingestion.scanner import scan_upload

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
PDF_SIGNATURE_WINDOW = 1024  # a PDF header must appear within the first KB


class UploadRejected(Exception):
    """An upload that cannot be used; carries the HTTP status and a message safe to show the client."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def transcript_from_upload(uploaded):
    """(text, warnings) from a Django UploadedFile. Raises UploadRejected."""
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise UploadRejected(f"File is larger than {MAX_UPLOAD_MB} MB.", 413)
    data = uploaded.read(MAX_UPLOAD_BYTES + 1)  # bounded read, whatever size the client claimed
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadRejected(f"File is larger than {MAX_UPLOAD_MB} MB.", 413)

    try:
        scan_upload(data)  # before any parser touches the bytes; a no-op unless a scanner is configured
    except IngestionError as exc:
        raise UploadRejected(str(exc), exc.status_code) from exc

    name = os.path.basename(uploaded.name or "") or "upload"
    if b"%PDF-" in data[:PDF_SIGNATURE_WINDOW] or name.lower().endswith(".pdf"):
        try:
            text, warnings = pdf_to_text(data, name)
        except IngestionError as exc:
            raise UploadRejected(str(exc), exc.status_code) from exc
        if not text.strip():
            raise UploadRejected(" ".join(["No text could be extracted from the PDF."] + warnings), 422)
        return text, warnings

    try:
        return data.decode("utf-8-sig"), []
    except UnicodeDecodeError:
        raise UploadRejected("File must be UTF-8 encoded text or a PDF.", 400)
