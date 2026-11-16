#!/usr/bin/env python3
"""Measure download speed by fetching a given URL 10 times sequentially."""

import sys
import time
import ssl
import urllib.request
import urllib.error
import urllib.parse

REQUESTS = 10
TIMEOUT = 60          # seconds per request
CHUNK_SIZE = 64 * 1024  # 64 KiB
RETRIES = 3
RETRY_DELAY = 1.0      # seconds between retries


def make_ssl_context():
    """Build an SSL context, preferring system CA bundles."""
    candidates = [
        "/private/etc/ssl/cert.pem",
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
    ]
    for path in candidates:
        try:
            ctx = ssl.create_default_context(cafile=path)
            return ctx
        except (OSError, ssl.SSLError):
            continue
    try:
        return ssl.create_default_context()
    except Exception:  # noqa: BLE001
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


SSL_CONTEXT = make_ssl_context()


def _open(url, timeout):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "speedtest-cli/1.0",
            "Accept": "*/*",
            "Accept-Encoding": "identity",  # avoid gzip so byte count == network bytes
        },
    )
    return urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT)


def fetch(url):
    """Download url fully (in chunks) and return (bytes_count, elapsed_seconds)."""
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            start = time.perf_counter()
            total = 0
            with _open(url, TIMEOUT) as response:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
            elapsed = time.perf_counter() - start
            return total, elapsed
        except urllib.error.HTTPError as exc:
            last_error = exc
            # Retry only on server-side / rate-limit errors.
            if exc.code >= 500 or exc.code == 429:
                if attempt < RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                raise
    # Should not reach here, but keep for safety.
    raise last_error  # type: ignore[misc]


def _validate_url(url):
    if not url:
        raise ValueError("URL is empty")
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme!r} (use http or https)")
    if not parsed.netloc:
        raise ValueError("URL has no host")
    return url


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 speedtest.py <URL>")
        print("Example: python3 speedtest.py https://example.com/big-image.jpg")
        sys.exit(1)

    try:
        url = _validate_url(sys.argv[1].strip())
    except ValueError as exc:
        print(f"Invalid URL: {exc}")
        sys.exit(1)

    print(f"Target: {url}")
    print(f"Requests: {REQUESTS} (retries per request: {RETRIES})\n")

    total_bytes = 0
    times = []
    failures = 0

    for i in range(1, REQUESTS + 1):
        try:
            size, elapsed = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"Request {i:2d}/{REQUESTS}: FAILED - {exc}")
            continue
        total_bytes += size
        times.append(elapsed)
        speed = (size * 8) / (elapsed * 1_000_000) if elapsed > 0 else float("inf")
        print(f"Request {i:2d}/{REQUESTS}: {size:>10} bytes in {elapsed:7.3f} s  ({speed:7.2f} Mbps)")

    print("\n--- Results ---")
    if not times:
        print("All requests failed.")
        sys.exit(1)

    avg_time = sum(times) / len(times)
    total_time = sum(times)
    speed_mbps = (total_bytes * 8) / (total_time * 1_000_000) if total_time > 0 else float("inf")
    speed_MBs = total_bytes / (total_time * 1_000_000) if total_time > 0 else float("inf")

    print(f"Successful requests : {len(times)}/{REQUESTS}")
    if failures:
        print(f"Failed requests     : {failures}")
    print(f"Average request time : {avg_time:.3f} s")
    print(f"Total downloaded     : {total_bytes} bytes ({total_bytes / 1_000_000:.2f} MB)")
    print(f"Total time           : {total_time:.3f} s")
    print(f"Download speed       : {speed_MBs:.2f} MB/s ({speed_mbps:.2f} Mbps)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
