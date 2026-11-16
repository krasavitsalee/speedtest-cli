#!/usr/bin/env python3
"""Measure download speed by fetching a given URL 10 times sequentially."""

import sys
import time
import ssl
import urllib.request

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
    # Fall back to default (may work on some platforms) or unverified as last resort.
    try:
        return ssl.create_default_context()
    except Exception:  # noqa: BLE001
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


SSL_CONTEXT = make_ssl_context()

REQUESTS = 10
TIMEOUT = 60  # seconds per request


def fetch(url):
    """Download url fully and return (bytes_count, elapsed_seconds)."""
    request = urllib.request.Request(url, headers={"User-Agent": "speedtest-cli/1.0"})
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=TIMEOUT, context=SSL_CONTEXT) as response:
        data = response.read()
    elapsed = time.perf_counter() - start
    return len(data), elapsed


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 speedtest.py <URL>")
        print("Example: python3 speedtest.py https://example.com/big-image.jpg")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Target: {url}")
    print(f"Requests: {REQUESTS}\n")

    total_bytes = 0
    times = []

    for i in range(1, REQUESTS + 1):
        try:
            size, elapsed = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report and stop
            print(f"Request {i}/{REQUESTS}: FAILED - {exc}")
            sys.exit(1)
        total_bytes += size
        times.append(elapsed)
        speed = (size * 8) / (elapsed * 1_000_000) if elapsed > 0 else float("inf")
        print(f"Request {i:2d}/{REQUESTS}: {size:>10} bytes in {elapsed:7.3f} s  ({speed:7.2f} Mbps)")

    avg_time = sum(times) / len(times)
    total_time = sum(times)
    speed_mbps = (total_bytes * 8) / (total_time * 1_000_000) if total_time > 0 else float("inf")
    speed_MBs = total_bytes / (total_time * 1_000_000) if total_time > 0 else float("inf")

    print("\n--- Results ---")
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
