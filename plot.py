# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///

"""
One year of air over Hong Kong, drawn twice: as relative humidity and as dew point.

    uv run plot.py

Writes out/humidity-grids.png and opens a window.

Both panels are the same 8,760 hours laid out the same way: 365 rows, one per day,
24 columns, one per hour. The only thing that changes between them is which
number colours the square. And that change moves the pattern: in relative
humidity the stripes run down the page — the same hour looks the same on every
day of the year. In dew point they run across — the day almost disappears and
the year takes over.

Relative humidity is a fraction: how full the air is, compared with how full it
could be at its temperature. Dew point is an amount: the temperature at which
that air would be saturated. The first forgets how warm the air is; the second
does not. That difference is the whole picture.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "out"
FILE = DATA / "open-meteo-hong-kong-hourly-2025.json"

PAPER = "#faf8f4"
INK = "#1d1d1b"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FIGSIZE = (13.5, 7.2)


def load():
    """The raw file, and the three lists of numbers in it."""
    reply = json.loads(FILE.read_text(encoding="utf-8"))
    hours = reply["hourly"]
    return hours["time"], hours["relative_humidity_2m"], hours["dewpoint_2m"], reply["hourly_units"]


def as_days(values, per_day=24):
    """One flat list of 8,760 numbers as 365 rows of 24. A loop, one day at a time."""
    rows = []
    for start in range(0, len(values), per_day):
        rows.append(values[start:start + per_day])
    return rows


def average(numbers):
    """The mean of a list, written out. One loop over the numbers."""
    total = 0
    for value in numbers:
        total += value
    return total / len(numbers)


def month_marks(times):
    """Where each month starts, and the middle of each month, counted in days.

    A loop over the time strings: the day number changes whenever the month does.
    The first version of this function counted hours instead of days, which put
    the December tick at 4,546 and stretched the year axis twelvefold — the
    whole picture ended up as one thin stripe at the top of the panel.
    """
    starts = []
    last_month = None
    for i, stamp in enumerate(times):
        month = int(stamp[5:7])
        if month != last_month:
            starts.append(i // 24)              # hours to days: 24 hours to a row
            last_month = month
    ends = starts[1:] + [len(times) // 24]      # each month runs to the start of the next
    middles = [(a + b) / 2 for a, b in zip(starts, ends)]
    return starts, middles


def two_rhythms(times, humidity, dewpoint):
    """The numbers the whole picture rests on, printed so the README can quote them."""
    per_hour = [[] for _ in range(24)]
    for stamp, value in zip(times, humidity):
        per_hour[int(stamp[11:13])].append(value)
    hour_means = [average(v) for v in per_hour]

    narrow = [(d, h) for h, d in zip(humidity, dewpoint) if 78 <= h <= 82]
    dps = [d for d, _ in narrow]

    print("relative humidity, hour by hour across the year")
    print(f"  most humid hour of the day: {hour_means.index(max(hour_means)):02d}:00 "
          f"at {max(hour_means):.0f} %")
    print(f"  driest  hour of the day:    {hour_means.index(min(hour_means)):02d}:00 "
          f"at {min(hour_means):.0f} %")
    print(f"  the daily swing is {max(hour_means) - min(hour_means):.0f} points, "
          f"every single day")
    print(f"\nhours reading 78-82 %: {len(narrow)}")
    print(f"  their dew points run {min(dps):.1f} to {max(dps):.1f} C — "
          f"the same number, two different airs")


def draw(axes, grid, cmap, title, unit, vmin, vmax, month_starts, month_middles):
    """One panel. The layout is identical for both; only the numbers differ."""
    picture = axes.imshow(grid, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto",
                          interpolation="nearest", origin="upper",
                          extent=(0, 24, len(grid), 0))
    for edge in month_starts[1:]:
        axes.axhline(edge, color=PAPER, linewidth=0.6, alpha=0.7)
    axes.set_title(title, color=INK, fontsize=12, pad=8)
    axes.set_xlabel("hour of the day", color=INK)
    axes.set_xticks([h + 0.5 for h in range(0, 24, 3)])
    axes.set_xticklabels([f"{h:02d}" for h in range(0, 24, 3)])
    axes.set_yticks([m + 15 for m in month_middles])
    axes.set_yticklabels(MONTHS)
    axes.tick_params(colors=INK, length=0)
    bar = plt.colorbar(picture, ax=axes, fraction=0.035, pad=0.02)
    bar.set_label(unit, color=INK)
    bar.ax.tick_params(colors=INK)
    bar.outline.set_visible(False)


def main():
    times, humidity, dewpoint, units = load()
    rh_days = as_days(humidity)
    dp_days = as_days(dewpoint)
    month_starts, month_middles = month_marks(times)

    two_rhythms(times, humidity, dewpoint)

    figure, (left, right) = plt.subplots(1, 2, figsize=FIGSIZE, facecolor=PAPER)
    figure.suptitle("Hong Kong, 2025 — the same 8,760 hours, two numbers",
                    color=INK, fontsize=14)

    draw(left, rh_days, "YlGnBu",
         "relative humidity — the stripes run down", units["relative_humidity_2m"],
         20, 100, month_starts, month_middles)
    draw(right, dp_days, "YlOrRd",
         "dew point — the stripes run across", f"dew point ({units['dewpoint_2m']})",
         0, 28, month_starts, month_middles)

    OUT.mkdir(exist_ok=True)
    target = OUT / "humidity-grids.png"
    figure.tight_layout()
    figure.savefig(target, dpi=150, facecolor=PAPER)
    print(f"\nwrote {target.relative_to(HERE)}")
    plt.show()


if __name__ == "__main__":
    main()
