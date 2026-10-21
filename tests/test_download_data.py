"""Offline coverage of transfer failures, resume safety, and archive inspection."""

import hashlib
import http.client
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import download_data as tool


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "Dataset.zip"
        self.body = b"published bytes"
        self.checksum = "md5:" + hashlib.md5(self.body).hexdigest()

    def transfer(self):
        return tool.download(
            "https://example.test/archive", self.target, len(self.body), self.checksum, attempts=1
        )

    def test_download_verified_then_cache_needs_no_network(self):
        with patch.object(
            tool.urllib.request, "urlopen", return_value=Response(self.body)
        ) as request:
            result = self.transfer()
            self.assertEqual(result["hashes"]["sha256"], hashlib.sha256(self.body).hexdigest())
            self.assertTrue(self.transfer()["cached"])
            self.assertEqual(request.call_count, 1)

    def test_resume_uses_valid_content_range(self):
        self.target.with_suffix(".zip.part").write_bytes(self.body[:4])
        response = Response(
            self.body[4:], 206, {"Content-Range": f"bytes 4-{len(self.body) - 1}/{len(self.body)}"}
        )
        with patch.object(tool.urllib.request, "urlopen", return_value=response) as request:
            self.transfer()
            self.assertEqual(request.call_args.args[0].get_header("Range"), "bytes=4-")
        self.assertEqual(self.target.read_bytes(), self.body)

    def test_ignored_range_restarts_instead_of_appending(self):
        self.target.with_suffix(".zip.part").write_bytes(self.body[:4])
        with patch.object(tool.urllib.request, "urlopen", return_value=Response(self.body)):
            self.transfer()
        self.assertEqual(self.target.read_bytes(), self.body)

    def test_bad_content_range_never_appends(self):
        part = self.target.with_suffix(".zip.part")
        part.write_bytes(self.body[:4])
        with patch.object(
            tool.urllib.request,
            "urlopen",
            return_value=Response(self.body[4:], 206, {"Content-Range": "bytes 0-2/3"}),
        ):
            with self.assertRaises(RuntimeError):
                self.transfer()
        self.assertEqual(part.read_bytes(), self.body[:4])

    def test_short_response_keeps_partial_for_later_resume(self):
        with patch.object(tool.urllib.request, "urlopen", return_value=Response(self.body[:4])):
            with self.assertRaises(RuntimeError):
                self.transfer()
        self.assertFalse(self.target.exists())
        self.assertEqual(self.target.with_suffix(".zip.part").read_bytes(), self.body[:4])

    def test_hash_mismatch_does_not_publish_final_file(self):
        with patch.object(
            tool.urllib.request, "urlopen", return_value=Response(b"x" * len(self.body))
        ):
            with self.assertRaises(RuntimeError):
                self.transfer()
        self.assertFalse(self.target.exists())

    def test_network_failure_is_bounded(self):
        with patch.object(
            tool.urllib.request, "urlopen", side_effect=TimeoutError("fixture timeout")
        ) as request:
            with self.assertRaises(RuntimeError):
                self.transfer()
            self.assertEqual(request.call_count, 1)

    def test_corrupt_complete_part_is_replaced_on_retry(self):
        self.target.with_suffix(".zip.part").write_bytes(b"x" * len(self.body))
        with (
            patch.object(tool.time, "sleep"),
            patch.object(
                tool.urllib.request, "urlopen", return_value=Response(self.body)
            ) as request,
        ):
            result = tool.download(
                "https://example.test/archive",
                self.target,
                len(self.body),
                self.checksum,
                attempts=2,
            )
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.target.read_bytes(), self.body)

    def test_content_range_end_must_be_inside_published_size(self):
        self.target.with_suffix(".zip.part").write_bytes(self.body[:4])
        response = Response(self.body[4:], 206, {"Content-Range": f"bytes 4-999/{len(self.body)}"})
        with patch.object(tool.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(RuntimeError):
                self.transfer()

    def test_incomplete_read_is_a_reported_download_failure(self):
        response = Response(b"")
        with (
            patch.object(response, "read1", side_effect=http.client.IncompleteRead(b"", 10)),
            patch.object(tool.urllib.request, "urlopen", return_value=response),
        ):
            with self.assertRaisesRegex(RuntimeError, "IncompleteRead"):
                self.transfer()

    def test_inventory_lists_and_reads_docs_without_extracting(self):
        with zipfile.ZipFile(self.target, "w") as bundle:
            bundle.writestr("Dataset/train/movie.tif", b"not decoded")
            bundle.writestr("Dataset/README.txt", "source documentation")
        result = tool.inventory(self.target)
        self.assertEqual(result["file_types"][".tif"], 1)
        self.assertEqual(result["documentation"][0]["text"], "source documentation")
        self.assertFalse((self.target.parent / "Dataset").exists())

    def test_inventory_rejects_traversal(self):
        with zipfile.ZipFile(self.target, "w") as bundle:
            bundle.writestr("../escape", b"bad")
        with self.assertRaises(ValueError):
            tool.inventory(self.target)

    def test_cli_failure_is_nonzero_and_status_is_saved(self):
        with patch("sys.argv", ["download_data.py", "--artifacts", str(self.target.parent)]):
            with patch.object(tool.urllib.request, "urlopen", side_effect=TimeoutError("offline")):
                self.assertEqual(tool.main(), 1)
        status = json.loads(
            (self.target.parent / "raw/zenodo_7660424/download-status.json").read_text()
        )
        self.assertEqual(status["status"], "failed")
        self.assertIn("elapsed_seconds", status)


if __name__ == "__main__":
    unittest.main()
