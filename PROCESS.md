# PROCESS.md

**Tools.** I worked with an AI assistant (Claude, in WorkBuddy) for most of the
making: it tested five candidate data sources against the "no key, one file"
rule before I chose, wrote `fetch.py`, `print_humidity.py` and `plot.py`, and
rendered both pictures. The decisions were mine: the phenomenon (humidity,
over the wind, rain, daylight and solar-radiation options it offered), the
informative path over the artistic one, and whether each picture actually says
something.

**What I kept.** The two-panel layout — relative humidity and dew point on the
same 365 × 24 grid. It was proposed after the numbers showed that 894 hours
read "78–82 %" while their dew points spanned 7 to 27 °C, and it earns its
place because the point is visible without reading a word: the stripes run
down in one panel and across in the other.

**What I rejected.** The first picture, `out/humidity-year.png` — one line of
daily means. It answered "which month is humid" but averaged the day away, and
the daily 22-point swing turned out to be the strongest pattern in the file.
It stays in the repo as the first attempt, not the answer.

**One correction worth writing down.** The first version of the month-label
code looped over the time strings and counted every one as a day. December's
tick landed at 4,546 on a 365-row axis, the year stretched twelvefold, and the
whole picture collapsed into a single stripe at the top of the panel. The fix
was one line — hours to days, `i // 24` — but the lesson is the one week 2
kept making: the picture breaking loudly was the only reason we looked.

**The interface.** Week 4's exercise was to adapt one interaction idea from
the tide examples. I chose the most direct one — the tide app's promise
"when I choose a day, the chart shows that day's 24 hourly heights" — and
applied it to my own numbers. The AI helped me write `app.py` in one pass; my
contribution was the scoping: a 2D line chart, not anything
three-dimensional; the month's average day drawn underneath the chosen day,
because that comparison is the one thing the static grids cannot give; and
testing that February offers 28 days before trusting the selector. Running
the app changed how I read my own picture: the grids say the daily rhythm
repeats 365 times, but picking a wet Saturday and watching it hug the
month's average line is what made the claim feel true.

**The bloom.** The grids answer "what does a year of humidity look like", but
I kept wondering whether the same numbers could be *grown* instead of plotted.
The AI helped me write two pygame sketches. In `bloom_day.py` one flower is
one day — 24 petals, one per hour, scrubbed with the arrow keys. It was pretty
but I could not shake the feeling that a flower that lasts one keystroke is
not a flower you watch live. The second version, `bloom.py`, is the one I
kept: one flower is one month, one petal is one day, and the petal's radius
is the hour — 00:00 at the heart, 24:00 at the tip. That last mapping is the
whole point: it is the humidity grid bent into a wheel, the stripes that ran
down the panel now running outward through every petal, and the dew-point
panel reduced to a gesture (each petal curls by that day's mean dew point).
Pressing → opens one more day, so the flower assembles the way a month does.
The decisions were mine: keeping the old version in the repo instead of
deleting it, keeping the 365-tick year ring so growth always has a context,
and accepting that a month-flower takes a minute to open — the slowness is
the data.
