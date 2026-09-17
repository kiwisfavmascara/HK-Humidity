# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///

"""
A first look at the year: one line.

    uv run plot.py

Writes out/humidity-year.png and opens a window.

This is the obvious first move — collapse each day to its average and join the
365 averages up. It is worth committing even though the next commit replaces it,
because of what it throws away: averaging the day away deletes the strongest
thing in this file.
"""

import datetime as dt
import json
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "out"
FILE = DATA / "open-meteo-hong-kong-hourly-2025.json"

PAPER = "#faf8f4"
INK = "#1d1d1b"
HUMID = "#2a6f7f"
MARK = "#d6591d"
FIGSIZE = (11, 4.5)


def load():
    """The three lists of numbers, and the hours they belong to."""
    reply = json.loads(FILE.read_text(encoding="utf-8"))
    hours = reply["hourly"]
    return hours["time"], hours["relative_humidity_2m"], reply["hourly_units"]


def days(values, per_day=24):
    """One flat list of 8,760 numbers as 365 days of 24. A loop, one day at a time."""
    whole = []
    for start in range(0, len(values), per_day):
        whole.append(values[start:start + per_day])
    return whole


def average(numbers):
    """The mean of a list, written out. One loop over the numbers."""
    total = 0
    for value in numbers:
        total += value
    return total / len(numbers)


def main():
    times, humidity, units = load()
    by_day = days(humidity)

    labels = []
    means = []
    for i, day in enumerate(by_day):
        labels.append(dt.date.fromisoformat(times[i * 24][:10]))
        means.append(average(day))

    figure, axes = plt.subplots(figsize=FIGSIZE, facecolor=PAPER)
    axes.set_facecolor(PAPER)

    axes.plot(labels, means, color=HUMID, linewidth=1.6)
    axes.fill_between(labels, means, min(means) - 2, color=HUMID, alpha=0.15)

    wettest = means.index(max(means))
    driest = means.index(min(means))
    for i, word in ((wettest, "wettest"), (driest, "driest")):
        axes.plot(labels[i], means[i], "o", color=MARK, markersize=7)
        axes.annotate(f"{word}: {means[i]:.0f} {units['relative_humidity_2m']}\n"
                      f"{labels[i]:%d %b}",
                      (labels[i], means[i]), textcoords="offset points",
                      xytext=(6, 10), color=MARK, fontsize=9)

    axes.set_title("Hong Kong, 2025 — the mean humidity of every day", color=INK, fontsize=13)
    axes.set_xlabel("day of the year", color=INK)
    axes.set_ylabel(f"daily mean relative humidity ({units['relative_humidity_2m']})", color=INK)
    axes.tick_params(colors=INK)
    axes.grid(color=INK, alpha=0.12)
    axes.set_ylim(min(means) - 6, max(means) + 10)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)

    OUT.mkdir(exist_ok=True)
    target = OUT / "humidity-year.png"
    figure.tight_layout()
    figure.savefig(target, dpi=150, facecolor=PAPER)
    print(f"wrote {target.relative_to(HERE)}")
    print(f"  wettest day {labels[wettest]} at {means[wettest]:.1f} {units['relative_humidity_2m']}")
    print(f"  driest  day {labels[driest]} at {means[driest]:.1f} {units['relative_humidity_2m']}")
    print(f"  the seasonal swing is {max(means) - min(means):.1f} points")
    plt.show()


if __name__ == "__main__":
    main()
