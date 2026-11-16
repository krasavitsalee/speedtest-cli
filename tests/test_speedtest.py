import sys
import os
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import speedtest


class TestValidateUrl(unittest.TestCase):
    def test_empty(self):
        with self.assertRaises(ValueError):
            speedtest._validate_url("")

    def test_no_host(self):
        with self.assertRaises(ValueError):
            speedtest._validate_url("https://")

    def test_bad_scheme(self):
        with self.assertRaises(ValueError):
            speedtest._validate_url("ftp://example.com/x")

    def test_adds_https(self):
        self.assertEqual(speedtest._validate_url("example.com/x"), "https://example.com/x")

    def test_ok(self):
        self.assertEqual(speedtest._validate_url("http://example.com/x"), "http://example.com/x")


class TestFetchMocked(unittest.TestCase):
    @patch("speedtest._build_opener")
    def test_fetch_counts_bytes(self, mock_build):
        fake_resp = MagicMock()
        fake_resp.read.side_effect = [b"abc", b"de", b""]
        fake_resp.headers.get.return_value = "5"
        cm = MagicMock()
        cm.__enter__.return_value = fake_resp
        cm.__exit__.return_value = False
        mock_build.return_value.open.return_value = cm

        size, elapsed = speedtest.fetch(
            "https://example.com/x", mock_build.return_value, {}, 10, 1024, 1, 0.0, progress=False
        )
        self.assertEqual(size, 5)
        self.assertGreaterEqual(elapsed, 0.0)


if __name__ == "__main__":
    unittest.main()


class TestFetchErrors(unittest.TestCase):
    @patch("speedtest._build_opener")
    def test_http_error_404_raises(self, mock_build):
        err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
        cm = MagicMock()
        cm.__enter__.side_effect = err
        cm.__exit__.return_value = False
        mock_build.return_value.open.return_value = cm
        with self.assertRaises(urllib.error.HTTPError):
            speedtest.fetch("https://example.com/x", mock_build.return_value, {}, 10, 1024, 1, 0.0, progress=False)


class TestRun(unittest.TestCase):
    @patch("speedtest.fetch")
    def test_run_all_success(self, mock_fetch):
        mock_fetch.return_value = (1000, 1.0)
        import argparse
        args = argparse.Namespace(
            url="https://example.com/x", count=2, timeout=10, chunk_size=1024,
            retries=1, retry_delay=0.0, proxy=None, header=[], progress=False,
            output="text", output_file=None, save_dir=None,
        )
        rc, rows, total_bytes, times, *_ = speedtest.run(args)
        self.assertEqual(rc, 0)
        self.assertEqual(len(times), 2)
        self.assertEqual(total_bytes, 2000)
        self.assertTrue(all(r["ok"] for r in rows))

    @patch("speedtest.fetch")
    def test_run_partial_failure(self, mock_fetch):
        mock_fetch.side_effect = [ (1000, 1.0), Exception("boom") ]
        import argparse
        args = argparse.Namespace(
            url="https://example.com/x", count=2, timeout=10, chunk_size=1024,
            retries=1, retry_delay=0.0, proxy=None, header=[], progress=False,
            output="text", output_file=None, save_dir=None,
        )
        rc, rows, total_bytes, times, *_ = speedtest.run(args)
        self.assertEqual(len(times), 1)
        self.assertEqual(total_bytes, 1000)
        self.assertFalse(rows[1]["ok"])

    @patch("speedtest.fetch")
    def test_run_all_fail(self, mock_fetch):
        mock_fetch.side_effect = Exception("boom")
        import argparse
        args = argparse.Namespace(
            url="https://example.com/x", count=2, timeout=10, chunk_size=1024,
            retries=1, retry_delay=0.0, proxy=None, header=[], progress=False,
            output="text", output_file=None, save_dir=None,
        )
        rc, *_ = speedtest.run(args)
        self.assertEqual(rc, 1)


class TestCLI(unittest.TestCase):
    def test_no_args_exits_nonzero(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, "speedtest.py"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("required", r.stderr.lower())

    def test_bad_url_exits_1(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, "speedtest.py", "ftp://example.com/x"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
