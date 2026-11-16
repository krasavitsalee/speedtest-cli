# Internet Speed Test (CLI)

A small console script that measures download speed by fetching a given URL
( for example a heavy image ) 10 times in a row and timing each request.

## Requirements

- Python 3.8+ (only the standard library is used, no `pip install` needed)

## Run

```bash
python3 speedtest.py <URL>
```

Example:

```bash
python3 speedtest.py https://example.com/heavy-image.jpg
```

The script makes 10 sequential requests, waits for the full response body on
each one, then prints the average request time, total downloaded volume and
the download speed.

## Units

- Request time: seconds (s)
- Downloaded volume: bytes (and megabytes, 1 MB = 1 000 000 bytes)
- Download speed: **megabytes per second (MB/s)**, where 1 MB = 1 000 000 bytes.
  The equivalent in megabits per second (Mbps) is also printed (1 byte = 8 bits).

Speed is computed as total downloaded bytes divided by total elapsed time
across all 10 requests.
