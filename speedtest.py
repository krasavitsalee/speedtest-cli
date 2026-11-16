#!/usr/bin/env python3
"""Measure download speed by fetching a given URL N times sequentially."""

import argparse
import csv
import io
import json
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
RETRY_DELAY = 1.0      # seconds (base; exponential backoff applied)


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


def _validate_url(url):
    if not url:
        raise ValueError("URL is empty")
    url = url.strip()
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme!r} (use http or https)")
    if not parsed.netloc:
        raise ValueError("URL has no host")
    return url


def _build_opener(proxy=None):
    https_handler = urllib.request.HTTPSHandler(context=SSL_CONTEXT)
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}),
            https_handler,
        )
    return urllib.request.build_opener(https_handler)


def _make_request(url, headers):
    req_headers = {
        "User-Agent": "speedtest-cli/1.0",
        "Accept": "*/*",
        "Accept-Encoding": "identity",  # keep byte count == network bytes
    }
    req_headers.update(headers or {})
    return urllib.request.Request(url, headers=req_headers)


def fetch(url, opener, headers, timeout, chunk_size, retries, retry_delay,
          progress=False):
    """Download url fully (in chunks) and return (bytes_count, elapsed_seconds)."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            start = time.perf_counter()
            total = 0
            request = _make_request(url, headers)
            with opener.open(request, timeout=timeout) as response:
                content_length = response.headers.get("Content-Length")
                total_len = int(content_length) if content_length and content_length.isdigit() else None
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    total += len(chunk)
                    if progress:
                        if total_len:
                            pct = min(100.0, total / total_len * 100)
                            sys.stdout.write(
                                f"\r  downloaded {total} / {total_len} bytes ({pct:5.1f}%)"
                            )
                        else:
                            sys.stdout.write(f"\r  downloaded {total} bytes")
                        sys.stdout.flush()
            if progress:
                sys.stdout.write("\n")
                sys.stdout.flush()
            elapsed = time.perf_counter() - start
            return total, elapsed
        except urllib.error.HTTPError as exc:
            last_error = exc
            if (exc.code >= 500 or exc.code == 429) and attempt < retries:
                time.sleep(retry_delay * (2 ** (attempt - 1)))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_delay * (2 ** (attempt - 1)))
                continue
            raise
    raise last_error  # type: ignore[misc]


def run(args):
    url = _validate_url(args.url)
    opener = _build_opener(args.proxy)
    headers = {}
    for h in (args.header or []):
        if ":" not in h:
            raise ValueError(f"Bad header (expected 'Key: Value'): {h!r}")
        key, val = h.split(":", 1)
        headers[key.strip()] = val.strip()

    print(f"Target: {url}")
    print(f"Requests: {args.count} (retries per request: {args.retries})\n")

    total_bytes = 0
    times = []
    failures = 0
    rows = []

    for i in range(1, args.count + 1):
        try:
            size, elapsed = fetch(
                url, opener, headers, args.timeout, args.chunk_size,
                args.retries, args.retry_delay, progress=args.progress,
            )
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"Request {i:2d}/{args.count}: FAILED - {exc}")
            rows.append({"request": i, "bytes": 0, "seconds": 0.0, "mbps": 0.0, "ok": False})
            continue
        total_bytes += size
        times.append(elapsed)
        speed = (size * 8) / (elapsed * 1_000_000) if elapsed > 0 else float("inf")
        print(f"Request {i:2d}/{args.count}: {size:>10} bytes in {elapsed:7.3f} s  ({speed:7.2f} Mbps)")
        rows.append({"request": i, "bytes": size, "seconds": round(elapsed, 6),
                     "mbps": round(speed, 6) if speed != float("inf") else None, "ok": True})

    if not times:
        print("\nAll requests failed.")
        return 1, rows, total_bytes, times

    avg_time = sum(times) / len(times)
    total_time = sum(times)
    speed_mbps = (total_bytes * 8) / (total_time * 1_000_000) if total_time > 0 else float("inf")
    speed_MBs = total_bytes / (total_time * 1_000_000) if total_time > 0 else float("inf")

    print("\n--- Results ---")
    print(f"Successful requests : {len(times)}/{args.count}")
    if failures:
        print(f"Failed requests     : {failures}")
    print(f"Average request time : {avg_time:.3f} s")
    print(f"Total downloaded     : {total_bytes} bytes ({total_bytes / 1_000_000:.2f} MB)")
    print(f"Total time           : {total_time:.3f} s")
    print(f"Download speed       : {speed_MBs:.2f} MB/s ({speed_mbps:.2f} Mbps)")

    return 0, rows, total_bytes, times, avg_time, total_time, speed_MBs, speed_mbps


def write_output(args, payload):
    if args.output == "text":
        return
    if args.output == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:  # csv
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["request", "bytes", "seconds", "mbps", "ok"])
        writer.writeheader()
        for r in payload["requests"]:
            writer.writerow(r)
        text = buf.getvalue()
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nSaved {args.output} to {args.output_file}")
    else:
        print("\n" + text)


def main():
    parser = argparse.ArgumentParser(
        description="Measure download speed by fetching a URL N times sequentially."
    )
    parser.add_argument("url", help="URL to download (e.g. a heavy image)")
    parser.add_argument("-n", "--count", type=int, default=REQUESTS,
                        help="number of requests (default: 10)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT,
                        help="per-request timeout in seconds (default: 60)")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE,
                        help="download chunk size in bytes (default: 65536)")
    parser.add_argument("--retries", type=int, default=RETRIES,
                        help="retries per request (default: 3)")
    parser.add_argument("--retry-delay", type=float, default=RETRY_DELAY,
                        help="base retry delay in seconds (default: 1.0, exponential backoff)")
    parser.add_argument("--proxy", default=None,
                        help="HTTP/HTTPS proxy URL")
    parser.add_argument("--header", action="append", default=[],
                        help="extra header 'Key: Value' (repeatable)")
    parser.add_argument("--progress", action="store_true",
                        help="show per-request download progress")
    parser.add_argument("--output", choices=["text", "json", "csv"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--output-file", default=None,
                        help="write json/csv output to file instead of stdout")
    args = parser.parse_args()

    if args.count < 1:
        print("count must be >= 1")
        sys.exit(1)

    try:
        result = run(args)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)

    if isinstance(result, tuple) and len(result) >= 4:
        _rc, rows, total_bytes, times = result[0], result[1], result[2], result[3]
        payload = {
            "url": args.url,
            "count": args.count,
            "successful": len(times),
            "failed": args.count - len(times),
            "total_bytes": total_bytes,
            "requests": rows,
        }
        if len(result) >= 8:
            payload.update({
                "avg_request_time_s": round(result[4], 6),
                "total_time_s": round(result[5], 6),
                "speed_MBps": round(result[6], 6),
                "speed_Mbps": round(result[7], 6),
            })
        write_output(args, payload)
        sys.exit(_rc)
    sys.exit(0)


if __name__ == "__main__":
    main()
