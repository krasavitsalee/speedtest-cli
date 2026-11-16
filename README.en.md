# Internet Speed Test (CLI)

[![Tests](https://github.com/krasavitsalee/speedtest-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/krasavitsalee/speedtest-cli/actions/workflows/tests.yml)

A small console script that measures download speed by fetching a given URL
(e.g. a heavy image) N times in a row and timing each request.

## Requirements

- Python 3.8+ (only the standard library is used, no `pip install` needed).

## Run

```bash
python3 speedtest.py <URL>
```

Example:

```bash
python3 speedtest.py https://example.com/heavy-image.jpg
```

By default 10 requests are made. Extra options:

```bash
python3 speedtest.py <URL> -n 5 --timeout 30 --progress --output json --output-file result.json
```

Main flags:

- `-n, --count` — number of requests (default 10)
- `--timeout` — per-request timeout in seconds (default 60)
- `--chunk-size` — read chunk size in bytes (default 65536)
- `--retries` — retries per request (default 3)
- `--retry-delay` — base retry delay in seconds (default 1.0, exponential backoff)
- `--proxy` — HTTP/HTTPS proxy URL
- `--header "Key: Value"` — extra header (repeatable)
- `--progress` — show download progress
- `--output {text,json,csv}` — output format (default text)
- `--output-file` — write json/csv to a file

The script makes N sequential requests, fully reads each response body, then
prints the average request time, total downloaded volume and the download
speed. If one request fails, the series continues and the final count of
successful requests is printed.

## Units

- Request time: seconds (s)
- Downloaded volume: bytes (and megabytes, 1 MB = 1 000 000 bytes)
- Download speed: **megabytes per second (MB/s)**, where 1 MB = 1 000 000 bytes.
  The equivalent in megabits per second (Mbps) is also printed (1 byte = 8 bits).

Speed is computed as total downloaded bytes divided by total elapsed time
across all requests.

## What is downloaded

The script does not save files to disk: data is downloaded into memory
(in chunks), bytes and time are counted, then the data is discarded. (Unless
`--output-file` is used for results.)

What gets downloaded depends on the URL. For testing you can use a service
like `https://httpbin.org/bytes/1000000` or a real heavy image URL.

## Tests

```bash
python -m unittest discover -s tests -v
```

12 unit tests + CI on GitHub Actions (Python 3.10–3.14).

## Project files

- `speedtest.py` — the script.
- `README.md` — instructions and units (Russian).
- `README.en.md` — this file (English).
- `.gitignore` — excludes IDE/cache files.
- `tests/` — unit tests.
- `.github/workflows/tests.yml` — CI.
