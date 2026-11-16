# Internet Speed Test (CLI)

A small console script that measures download speed by fetching a given URL
(e.g. a heavy image) 10 times in a row and timing each request.

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

Options:

```bash
python3 speedtest.py <URL> -n 5 --timeout 30 --progress --output json --output-file result.json
```

The script makes N sequential requests (default 10), fully reads each response
body, then prints the average request time, total downloaded volume and the
download speed.

## Units

- Request time: seconds (s)
- Downloaded volume: bytes (and megabytes, 1 MB = 1 000 000 bytes)
- Download speed: **megabytes per second (MB/s)**, where 1 MB = 1 000 000 bytes.
  The equivalent in megabits per second (Mbps) is also printed (1 byte = 8 bits).

Speed is computed as total downloaded bytes divided by total elapsed time
across all requests.

## What is downloaded

The script does not save files to disk: data is downloaded into memory
(in chunks), bytes and time are counted, then the data is discarded.

What gets downloaded depends on the URL. For testing you can use a service
like `https://httpbin.org/bytes/1000000` or a real heavy image URL.

Project files:

- `speedtest.py` — the script.
- `README.md` — instructions and units (Russian).
- `README.en.md` — this file (English).
- `.gitignore` — excludes IDE/cache files.
- `tests/` — unit tests.
