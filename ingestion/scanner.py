"""Optional virus scan of uploads with ClamAV, before anything parses the file.

Talks to a `clamd` daemon over its INSTREAM protocol with the standard library only (no new dependency).
Off by default: it runs only when INGEST_CLAMD_SOCKET (a unix socket path) or INGEST_CLAMD_HOST (with
INGEST_CLAMD_PORT, default 3310) is set. INGEST_CLAMD_TIMEOUT (seconds, default 30) bounds the whole check.

It fails closed: when a scanner is configured but unreachable, slow, or answers with anything other than
"OK" or a detection (for example a file over clamd's own size limit), the upload is refused rather than
passed unscanned. Only the verdict is logged, never file content.

What this is not: signature scanning finds known malware, not new exploits, so it complements the PDF
pre-scan and the sandbox rather than replacing them. Keep signatures current (freshclam; in an air-gapped
deployment, through an approved offline route), and run clamd in its own container with no route to the
internet. Never send confidential files to an online scanning service instead.

To test a real ClamAV end to end, use the standard EICAR test file (a harmless string every scanner flags
on purpose); it is deliberately not written into this repository, because many antivirus tools would
quarantine the source file.
"""
import logging
import os
import re
import socket
import struct

from .models import IngestionError

logger = logging.getLogger("ingestion.scanner")

CHUNK_BYTES = 64 * 1024
MAX_REPLY_BYTES = 4096


class MalwareDetected(IngestionError):
    """The scanner flagged the file."""
    status_code = 422


class ScanUnavailable(IngestionError):
    """A scan was required but could not be completed. The file is refused (fail closed)."""
    status_code = 503


def scanner_configured() -> bool:
    return bool(os.getenv("INGEST_CLAMD_SOCKET") or os.getenv("INGEST_CLAMD_HOST"))


def _connect(timeout: float):
    path = os.getenv("INGEST_CLAMD_SOCKET")
    if path:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(path)
        return sock
    return socket.create_connection((os.environ["INGEST_CLAMD_HOST"], int(os.getenv("INGEST_CLAMD_PORT", "3310"))),
                                    timeout=timeout)


def _read_reply(sock) -> str:
    reply = b""
    while len(reply) < MAX_REPLY_BYTES:
        data = sock.recv(1024)
        if not data:
            break
        reply += data
        if b"\0" in reply or b"\n" in reply:
            break
    return reply.decode("utf-8", "replace").strip("\0\n\r ")


def scan_upload(data: bytes) -> bool:
    """Scan `data` with clamd. Returns False when no scanner is configured (nothing was checked), True when
    the file was scanned and is clean. Raises MalwareDetected or ScanUnavailable."""
    if not scanner_configured():
        return False
    timeout = float(os.getenv("INGEST_CLAMD_TIMEOUT", "30"))
    try:
        with _connect(timeout) as sock:
            sock.sendall(b"zINSTREAM\0")
            for start in range(0, len(data), CHUNK_BYTES):
                chunk = data[start:start + CHUNK_BYTES]
                sock.sendall(struct.pack("!I", len(chunk)) + chunk)
            sock.sendall(struct.pack("!I", 0))
            reply = _read_reply(sock)
    except OSError as exc:  # refused, reset, timed out, or clamd hung up (e.g. over its size limit)
        logger.warning("Virus scan could not be completed: %s", type(exc).__name__)
        raise ScanUnavailable("The virus scanner could not check the file (it is unavailable, or the file is "
                              "too large for it), so the file was not accepted.") from exc

    if reply.endswith("OK"):
        return True
    if reply.endswith("FOUND"):
        signature = re.sub(r"[^\w.\-/ ]", "", reply.split(":", 1)[-1].rsplit("FOUND", 1)[0])[:100].strip()
        logger.warning("Virus scan flagged an upload: %s", signature)
        raise MalwareDetected(f"The file was rejected by the virus scanner ({signature or 'unnamed signature'}).")
    logger.warning("Virus scan gave an unusable reply: %.100s", reply)
    raise ScanUnavailable("The virus scanner returned an error, so the file was not accepted.")
