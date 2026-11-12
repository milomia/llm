"""The optional ClamAV scan of uploads, tested against a fake clamd that speaks the real INSTREAM protocol
over a local TCP or unix socket. No ClamAV, network or real malware is involved: the fake flags any file
containing a marker string of our own.
"""
import hashlib
import os
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from analysis.models import Transcription
from analysis.test_pdf_upload import CALL, make_pdf
from ingestion.models import IngestionError
from ingestion.scanner import MalwareDetected, ScanUnavailable, scan_upload, scanner_configured

MARKER = b"FAKE-VIRUS-MARKER"
SCANNER_VARS = ("INGEST_CLAMD_HOST", "INGEST_CLAMD_PORT", "INGEST_CLAMD_SOCKET", "INGEST_CLAMD_TIMEOUT")


def recv_exact(sock, count):
    data = b""
    while len(data) < count:
        piece = sock.recv(count - len(data))
        if not piece:
            raise ConnectionError("client went away")
        data += piece
    return data


class FakeClamd:
    """A clamd stand-in. `mode`: normal | error | hang | hangup | weird."""

    def __init__(self, mode="normal"):
        self.mode, self.commands, self.received = mode, [], []
        fake = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                sock = self.request
                try:
                    fake.commands.append(recv_exact(sock, len(b"zINSTREAM\0")))
                    if fake.mode == "hangup":
                        return
                    if fake.mode == "hang":
                        time.sleep(3)
                        return
                    data = b""
                    while True:
                        size = struct.unpack("!I", recv_exact(sock, 4))[0]
                        if size == 0:
                            break
                        data += recv_exact(sock, size)
                    fake.received.append(data)
                    replies = {"error": b"INSTREAM size limit exceeded. ERROR\0",
                               "weird": b"stream: Bad<script>alert(1)</script>.Sig FOUND\0"}
                    if fake.mode in replies:
                        sock.sendall(replies[fake.mode])
                    elif MARKER in data:
                        sock.sendall(b"stream: Fake.Test.Signature FOUND\0")
                    else:
                        sock.sendall(b"stream: OK\0")
                except (ConnectionError, OSError):
                    pass

        self.handler = Handler


@contextmanager
def running(fake, unix=False):
    """Serve `fake` and point the scanner settings at it; yields the fake."""
    if unix:
        folder = tempfile.mkdtemp(prefix="clamd-")
        path = str(Path(folder) / "clamd.sock")
        server = socketserver.ThreadingUnixStreamServer(path, fake.handler)
        env = {"INGEST_CLAMD_SOCKET": path}
    else:
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), fake.handler)
        env = {"INGEST_CLAMD_HOST": "127.0.0.1", "INGEST_CLAMD_PORT": str(server.server_address[1])}
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with patch.dict(os.environ, {**env, "INGEST_CLAMD_TIMEOUT": "1"}):
            yield fake
    finally:
        server.shutdown()
        server.server_close()


def without_scanner():
    cleaned = {k: v for k, v in os.environ.items() if k not in SCANNER_VARS}
    return patch.dict(os.environ, cleaned, clear=True)


def closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ScannerTests(SimpleTestCase):
    def test_it_is_off_unless_configured_and_then_touches_no_network(self):
        with without_scanner(), patch("socket.create_connection") as connect, patch("socket.socket") as sock:
            self.assertFalse(scanner_configured())
            self.assertFalse(scan_upload(b"anything"))
        connect.assert_not_called()
        sock.assert_not_called()

    def test_a_clean_file_is_streamed_whole_in_chunks_and_passes(self):
        data = os.urandom(200 * 1024 + 17)  # several chunks, not a multiple of the chunk size
        with running(FakeClamd()) as fake:
            self.assertTrue(scan_upload(data))
        self.assertEqual(fake.commands, [b"zINSTREAM\0"])
        self.assertEqual(hashlib.sha256(fake.received[0]).digest(), hashlib.sha256(data).digest())

    def test_an_empty_file_is_scanned_too(self):
        with running(FakeClamd()):
            self.assertTrue(scan_upload(b""))

    def test_a_detection_is_rejected_with_the_signature_name(self):
        with running(FakeClamd()), self.assertRaisesRegex(MalwareDetected, r"virus scanner \(Fake\.Test\.Signature\)"):
            scan_upload(b"harmless text " + MARKER)

    def test_a_signature_name_is_sanitised_before_it_reaches_a_response(self):
        with running(FakeClamd("weird")), self.assertRaises(MalwareDetected) as caught:
            scan_upload(b"x")
        self.assertNotIn("<", str(caught.exception))
        self.assertNotIn("(1)", str(caught.exception))

    def test_it_works_over_a_unix_socket(self):
        with running(FakeClamd(), unix=True):
            self.assertTrue(scan_upload(b"clean"))
            with self.assertRaises(MalwareDetected):
                scan_upload(MARKER)

    def test_every_failure_to_scan_fails_closed(self):
        # An unreachable scanner, a scanner that never answers, an error reply, and a scanner that hangs up
        # while the file is still being sent (as clamd does over its size limit) must all refuse the file.
        with patch.dict(os.environ, {"INGEST_CLAMD_HOST": "127.0.0.1", "INGEST_CLAMD_PORT": str(closed_port()),
                                     "INGEST_CLAMD_TIMEOUT": "1"}):
            with self.assertRaises(ScanUnavailable):
                scan_upload(b"x")
        started = time.monotonic()
        with running(FakeClamd("hang")), patch.dict(os.environ, {"INGEST_CLAMD_TIMEOUT": "0.3"}):
            with self.assertRaises(ScanUnavailable):
                scan_upload(b"x")
        self.assertLess(time.monotonic() - started, 2.5)
        with running(FakeClamd("error")), self.assertRaisesRegex(ScanUnavailable, "returned an error"):
            scan_upload(b"x")
        with running(FakeClamd("hangup")), self.assertRaisesRegex(ScanUnavailable, "too large for it"):
            scan_upload(os.urandom(4 * 1024 * 1024))

    def test_the_exceptions_carry_the_right_http_status(self):
        self.assertTrue(issubclass(MalwareDetected, IngestionError) and issubclass(ScanUnavailable, IngestionError))
        self.assertEqual((MalwareDetected.status_code, ScanUnavailable.status_code), (422, 503))


class UploadScanTests(APITestCase):
    def upload(self, name, data):
        return self.client.post(reverse("transcript"), {"file": SimpleUploadedFile(name, data)}, format="multipart")

    def test_without_a_scanner_uploads_work_as_before(self):
        with without_scanner():
            self.assertEqual(self.upload("call.txt", b"MSL Hello there.").status_code, 201)

    def test_an_infected_text_file_is_rejected_and_nothing_is_saved(self):
        with running(FakeClamd()):
            response = self.upload("call.txt", b"MSL Hello " + MARKER)
        self.assertEqual(response.status_code, 422)
        self.assertIn("virus scanner (Fake.Test.Signature)", response.json()["file"][0])
        self.assertEqual(Transcription.objects.count(), 0)

    def test_an_infected_pdf_is_stopped_before_the_pdf_reader_starts(self):
        infected = make_pdf() + MARKER  # a valid PDF with bytes after %%EOF, which readers tolerate
        with running(FakeClamd()) as fake, patch("ingestion.secure.subprocess.run", wraps=subprocess.run) as spawned:
            response = self.upload("call.pdf", infected)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(fake.received), 1)
        spawned.assert_not_called()

    def test_a_clean_upload_is_scanned_byte_for_byte_and_then_accepted(self):
        pdf = make_pdf()
        with running(FakeClamd()) as fake:
            response = self.upload("call.pdf", pdf)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(fake.received, [pdf])
        self.assertIn("Hello Dr Lewis", Transcription.objects.get().text)

    def test_a_scanner_that_is_down_refuses_the_upload_with_503(self):
        with patch.dict(os.environ, {"INGEST_CLAMD_HOST": "127.0.0.1", "INGEST_CLAMD_PORT": str(closed_port())}):
            response = self.upload("call.txt", b"MSL Hello there.")
        self.assertEqual(response.status_code, 503)
        self.assertIn("could not check the file", response.json()["file"][0])
        self.assertEqual(Transcription.objects.count(), 0)

    def test_the_scan_comes_before_parsing_so_a_down_scanner_wins_over_a_parse_error(self):
        with patch.dict(os.environ, {"INGEST_CLAMD_HOST": "127.0.0.1", "INGEST_CLAMD_PORT": str(closed_port())}):
            response = self.upload("fake.pdf", b"MZ not a pdf at all")
        self.assertEqual(response.status_code, 503)

    def test_posted_text_is_not_sent_to_the_scanner(self):
        with running(FakeClamd()) as fake:
            response = self.client.post(reverse("transcript"), {"text": CALL}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(fake.commands, [])
