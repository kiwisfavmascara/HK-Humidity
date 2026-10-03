# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///

"""
Fetch the numbers once, save the raw reply to data/, and never fetch again.

    uv run fetch.py

Open-Meteo's historical archive answers with JSON, no key, no account. This asks
for one year of hourly air at one point over Hong Kong: the relative humidity,
the dew point and the temperature, 8,760 hours of each.

The reply is written to data/ byte for byte, unchanged, and committed. Every
other script in this repo reads that file and never touches the network, so the
whole thing runs with the wifi off.
"""

from pathlib import Path

import requests

# CHANGE ME was here: this is the phenomenon, and where it comes from.
URL = ("https://archive-api.open-meteo.com/v1/archive"
       "?latitude=22.302&longitude=114.174"
       "&start_date=2025-01-01&end_date=2025-12-31"
       "&hourly=relative_humidity_2m,dewpoint_2m,temperature_2m"
       "&timezone=Asia%2FHong_Kong")

FILE = "open-meteo-hong-kong-hourly-2025.json"

HERE = Path(__file__).parent
DATA = HERE / "data"


def fetch(url, path):
    """Ask for the file once. If it is already in data/, do nothing."""
    if path.exists():
        print(f"data/{path.name} is already here ({path.stat().st_size // 1024} KB). "
              "Delete it to fetch again.")
        return path
    DATA.mkdir(parents=True, exist_ok=True)
    print(f"asking {url}")
    reply = requests.get(url, timeout=60, headers={"User-Agent": "SD5913 PolyU student"})
    reply.raise_for_status()
    path.write_bytes(reply.content)     # byte for byte: what arrived is what gets committed
    print(f"saved data/{path.name} ({path.stat().st_size // 1024} KB). Now: git add data")
    return path


def main():
    path = fetch(URL, DATA / FILE)
    print(f"\n{path.relative_to(HERE)} is the raw reply. Next: uv run print_humidity.py")


if __name__ == "__main__":
    main()
