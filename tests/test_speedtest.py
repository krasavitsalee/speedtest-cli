import sys
import os
import unittest
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
