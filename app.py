# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "streamlit"]
# ///

"""
The same year of air as an interface: pick a day, see its 24 hours.

    uv run --with streamlit --with pandas streamlit run app.py

When I choose a month, the day list shows only that month's days. When I choose
a day, the chart shows that day's 24 hourly readings — relative humidity on the
left, dew point on the right — with the month's average day drawn underneath for
comparison.

The promise: a widget change reruns the script with the new value, so the two
selectors and the two charts always describe one and the same day. The static
grids in out/ show the whole year at once; this page is the close-up. The
month's average day is the reference the grid cannot give: does this particular
day follow its month's rhythm, or break it?

Reads the committed snapshot beside the script; the internet is only needed the
first time fetch.py runs.
"""

import calendar
import json
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).parent
FILE = HERE / "data" / "open-meteo-hong-kong-hourly-2025.json"


def load():
    """The raw file, and the three lists of numbers in it."""
    reply = json.loads(FILE.read_text(encoding="utf-8"))
    hours = reply["hourly"]
    return (hours["time"], hours["relative_humidity_2m"],
            hours["dewpoint_2m"], reply["hourly_units"])


def as_days(times, humidity, dewpoint):
    """8,760 hours as one record per day. A loop, one stamp at a time."""
    days = []
    for stamp, rh, dp in zip(times, humidity, dewpoint):
        month, day = int(stamp[5:7]), int(stamp[8:10])
        if not days or days[-1]["day"] != day or days[-1]["month"] != month:
            days.append({"month": month, "day": day, "rh": [], "dp": []})
        days[-1]["rh"].append(rh)
        days[-1]["dp"].append(dp)
    return days


def average(numbers):
    """The mean of a list, written out. One loop over the numbers."""
    total = 0
    for value in numbers:
        total += value
    return total / len(numbers)


def average_day(records, key):
    """The month's typical day: each hour averaged across all its days."""
    per_hour = [[] for _ in range(24)]
    for record in records:
        for hour, value in enumerate(record[key]):
            per_hour[hour].append(value)
    return [average(values) for values in per_hour]


st.set_page_config(page_title="Hong Kong air, one day at a time", page_icon="💧")
st.title("Hong Kong air, one day at a time")
st.caption("Open-Meteo archive · Hong Kong · 2025, one day at a time")

times, humidity, dewpoint, units = load()
days = as_days(times, humidity, dewpoint)

month = st.selectbox("Month", range(1, 13),
                     format_func=lambda n: calendar.month_name[n],
                     index=6)                      # July: the most humid stretch
month_days = [d for d in days if d["month"] == month]
if not month_days:
    st.info("There are no records for that month.")
    st.stop()

day = st.selectbox("Day", [d["day"] for d in month_days])
record = next(d for d in month_days if d["day"] == day)

hours = range(1, 25)
left, right = st.columns(2)

with left:
    st.subheader(f"Relative humidity ({units['relative_humidity_2m']})")
    chart = pd.DataFrame({"that day": record["rh"],
                          "the month's average day": average_day(month_days, "rh")},
                         index=hours)
    chart.index.name = "Hour"
    st.line_chart(chart)

with right:
    st.subheader(f"Dew point ({units['dewpoint_2m']})")
    chart = pd.DataFrame({"that day": record["dp"],
                          "the month's average day": average_day(month_days, "dp")},
                         index=hours)
    chart.index.name = "Hour"
    st.line_chart(chart)

st.caption(f"2025-{month:02}-{day:02} · 24 hourly readings · "
           "the dotted question: does this day follow its month's rhythm?")
