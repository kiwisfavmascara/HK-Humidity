# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Print the numbers before plotting them.

    uv run print_humidity.py

Every week-3 script started by printing something, and it is worth copying: ten
seconds of printing saves ten minutes of a plot that came out empty because
everything was still text, or because the column was called something else.

It also settles a question this particular file raises. Two weeks ago the tide
file held `"2.19"` — a number wearing quotes, which somebody had to say
`float()` to. This file was written by a machine for machines, and it does not
do that.
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
FILE = DATA / "open-meteo-hong-kong-hourly-2025.json"


def load():
    """The raw reply, as Python sees it, with nothing converted yet."""
    return json.loads(FILE.read_text(encoding="utf-8"))


def smallest_and_largest(numbers):
    """One loop over the numbers. This is the loop the whole picture is built on."""
    low = high = numbers[0]
    for value in numbers:
        if value < low:
            low = value
        if value > high:
            high = value
    return low, high


def main():
    reply = load()

    print("what the file says about itself")
    for key in ("latitude", "longitude", "elevation", "timezone", "utc_offset_seconds"):
        print(f"  {key:22} {reply[key]}")
    print(f"  {'hourly_units':22} {reply['hourly_units']}")

    hours = reply["hourly"]
    print(f"\nthe keys inside 'hourly': {list(hours)}")
    for name, values in hours.items():
        print(f"  {name:22} {len(values):>6} values")

    print("\nthe first three hours, exactly as they arrived")
    for i in range(3):
        print(f"  {hours['time'][i]}   rh={hours['relative_humidity_2m'][i]!r} "
              f"dew={hours['dewpoint_2m'][i]!r} temp={hours['temperature_2m'][i]!r}")

    one = hours["relative_humidity_2m"][0]
    print(f"\nthe first humidity reading is {one!r} and its type is "
          f"{type(one).__name__} — already a number, no float() needed")

    for name in ("relative_humidity_2m", "dewpoint_2m", "temperature_2m"):
        values = hours[name]
        low, high = smallest_and_largest(values)
        total = 0
        for value in values:
            total += value
        print(f"  {name:22} {low:>7} … {high:>6}  "
              f"mean {total / len(values):6.1f} {reply['hourly_units'][name]}")

    print("\nnext: uv run plot.py")


if __name__ == "__main__":
    main()
