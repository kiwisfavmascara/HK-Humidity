# /// script
# requires-python = ">=3.10"
# dependencies = ["pygame-ce"]
# ///

"""
A flower that grows with the year: one flower is one month, one petal is one day.

    uv run --with pygame-ce bloom.py

Keys: RIGHT opens one more petal (one more day), LEFT closes one; when a month
is full, the next petal starts the following month. UP/DOWN jump between
months, SPACE plays the year growing from January the 1st, the mouse wheel
also opens and closes, S saves a frame, Q or ESC quits.
Headless: uv run bloom.py --save out.png [--month 6 --open 16]

The promise: the two grids (out/humidity-grids.png) show 365 days x 24 hours;
this flower is the same numbers with the grid bent into a wheel. One petal is
one day, and the radius of a petal is the hour: the centre of the flower is
00:00, the petal tips are 24:00, so the daily stripes that ran down the grid
now run outward through every petal. The colour of the dust at each radius is
that hour's relative humidity — dry air glows blue, soaked air magenta — and
the petal swells where its hours were humid, so a petal's silhouette is that
day's humidity rhythm. The curl of a petal is that day's mean dew point —
warm air curls, cool air straightens — the "stripes run across" grid drawn
as a gesture. A month begins as a single petal; each RIGHT adds a day, so the
flower you end up with is the month, petal by petal. The faint outer ring is
still the whole year: one tick per day with a needle on the newest petal.
Every number comes from data/*.json — nothing here is decorative.
"""

import argparse
import json
import math
import random
from pathlib import Path

import pygame

HERE = Path(__file__).parent
FILE = HERE / "data" / "open-meteo-hong-kong-hourly-2025.json"

WIDTH, HEIGHT, FPS = 840, 880, 60
CENTRE = (WIDTH // 2, HEIGHT // 2 + 12)
R_MAX = 292.0                 # petal tip at the most humid hour of the wettest day
R_IN = R_MAX * 0.13           # the flower keeps a visible heart
RING_R = R_MAX * 1.16         # the year ring's inner radius
PAPER = (5, 6, 10)            # night air; the dust carries the colour
INK = (232, 230, 224)

# Humidity 30-100 %, dry air to soaked air: royal blue -> teal -> jade ->
# violet -> magenta -> rose, the ramp of the reference bloom.
HUM_STOPS = [(30, 60, 135), (0, 130, 160), (40, 170, 160),
             (140, 110, 215), (205, 95, 200), (250, 105, 150)]


def load_days():
    """The committed snapshot, as one record per day: 24 humidities, 24 dew points."""
    reply = json.loads(FILE.read_text(encoding="utf-8"))
    hours = reply["hourly"]
    times, rh, dp = hours["time"], hours["relative_humidity_2m"], hours["dewpoint_2m"]
    days = []
    for stamp, a, b in zip(times, rh, dp):
        month, day = int(stamp[5:7]), int(stamp[8:10])
        if not days or days[-1]["month"] != month:
            days.append({"month": month, "first": len(days), "days": []})
        if not days[-1]["days"] or days[-1]["days"][-1]["day"] != day:
            days[-1]["days"].append({"day": day, "rh": [], "dp": []})
        days[-1]["days"][-1]["rh"].append(a)
        days[-1]["days"][-1]["dp"].append(b)
    first = 0                                   # day-of-year of each month's start
    for month in days:
        month["first"] = first
        first += len(month["days"])
    return days


def average(numbers):
    total = 0
    for value in numbers:
        total += value
    return total / len(numbers)


def clamp(x, low=0.0, high=1.0):
    return max(low, min(high, x))


def _ramp(stops, value, low, high):
    t = clamp((value - low) / (high - low))
    pos = t * (len(stops) - 1)
    i = min(int(pos), len(stops) - 2)
    f = pos - i
    return tuple(int(a + (b - a) * f) for a, b in zip(stops[i], stops[i + 1]))


def hum_colour(rh):
    """One stop along the humidity ramp, 30-100 %."""
    return _ramp(HUM_STOPS, rh, 30.0, 100.0)


def petal(surface, angle, record, frac, swirl, rng):
    """One petal = one day. The radius is the hour: 00:00 at the heart,
    24:00 at the tip. Colour is the hour's humidity, swell is the hour's
    humidity, curl is the day's dew point."""
    length = R_IN + 40 + frac * (R_MAX - R_IN - 40)
    spread = length * 0.30                        # a broad membrane, like the study
    streams = 20                                  # warp threads of dust
    dots = 46                                     # weft: finer than the hours
    rh = record["rh"]
    for s in range(streams):
        u = (s / (streams - 1)) * 2 - 1 if streams > 1 else 0.0
        edge = math.sqrt(max(0.0, 1.0 - u * u * 0.85))   # side threads shorter
        for i in range(dots):
            t = (i + 1) / dots
            hour = min(23, int(t * 24))
            rh_hour = rh[hour]
            # The spine curls as it leaves the heart: dew point as gesture.
            a = angle + swirl * t * t
            dx, dy = math.cos(a), math.sin(a)
            px, py = -dy, dx
            reach = R_IN + (length - R_IN) * t * (0.74 + 0.26 * edge)
            # Humid hours swell the petal; the silhouette is the day's rhythm.
            swell = 0.45 + 0.55 * rh_hour / 100
            off = u * spread * edge * swell * math.sin(math.pi * min(1.0, t * 1.02)) ** 0.75
            x = CENTRE[0] + dx * reach + px * off
            y = CENTRE[1] + dy * reach + py * off
            # Iridescence: the dry edge cools, the wet edge warms.
            sheen = hum_colour(clamp(rh_hour + u * 10, 30.0, 100.0))
            base = hum_colour(rh_hour)
            mix = abs(u) * 0.65
            r = int((base[0] + (sheen[0] - base[0]) * mix) * 1.45)
            g = int((base[1] + (sheen[1] - base[1]) * mix) * 1.45)
            b = int((base[2] + (sheen[2] - base[2]) * mix) * 1.45)
            fade = (0.20 + 0.80 * t) * edge * (0.40 + 0.60 * math.sin(math.pi * t) ** 0.3)
            bright = int(255 * min(1.0, fade))
            if rng.random() < 0.03:               # a bright mote with a halo
                r, g, b = min(255, r + 90), min(255, g + 90), min(255, b + 90)
                pygame.draw.circle(surface, (r // 5, g // 5, b // 5),
                                   (int(x), int(y)), 3)
                radius = 2
            else:
                radius = 2 if i % 9 == 0 else 1
            pygame.draw.circle(surface, (min(255, r) * bright // 255,
                                         min(255, g) * bright // 255,
                                         min(255, b) * bright // 255),
                               (int(x), int(y)), radius)


def draw_dust(surface, colour):
    """Loose motes drifting past the petal tips, coloured by the month."""
    rng = random.Random(4242)
    for _ in range(70):
        angle = rng.random() * math.tau
        dist = R_MAX * (0.78 + rng.random() ** 1.5 * 0.40)
        x = CENTRE[0] + math.cos(angle) * dist
        y = CENTRE[1] + math.sin(angle) * dist
        bright = int(150 * (0.3 + rng.random() * 0.7))
        pygame.draw.circle(surface, (colour[0] * bright // 255,
                                     colour[1] * bright // 255,
                                     colour[2] * bright // 255),
                           (int(x), int(y)), 1)


def draw_heart(surface, colour):
    """A knot of bright dust at the centre: 00:00, the hour the day turns."""
    rng = random.Random(77)
    for _ in range(130):
        angle = rng.random() * math.tau
        dist = rng.random() ** 1.6 * (R_IN - 4)
        x = CENTRE[0] + math.cos(angle) * dist
        y = CENTRE[1] + math.sin(angle) * dist
        bright = int(170 * (0.4 + rng.random() * 0.6))
        pygame.draw.circle(surface, (colour[0] * bright // 255,
                                     colour[1] * bright // 255,
                                     colour[2] * bright // 255),
                           (int(x), int(y)), 1)


def draw_ring(surface, days, needle_day):
    """365 ticks, one per day, coloured by that day's mean humidity."""
    for i, month in enumerate(days):
        for j, record in enumerate(month["days"]):
            k = month["first"] + j
            angle = k / 365 * math.tau - math.pi / 2
            mean = average(record["rh"])
            length = 8 + (mean - 40) / 60 * 10
            colour = hum_colour(mean)
            colour = (colour[0] // 3 + 40, colour[1] // 3 + 40, colour[2] // 3 + 40)
            x1 = CENTRE[0] + math.cos(angle) * RING_R
            y1 = CENTRE[1] + math.sin(angle) * RING_R
            x2 = CENTRE[0] + math.cos(angle) * (RING_R + length)
            y2 = CENTRE[1] + math.sin(angle) * (RING_R + length)
            pygame.draw.line(surface, colour, (x1, y1), (x2, y2), 2)
    needle = needle_day / 365 * math.tau - math.pi / 2
    pygame.draw.line(surface, INK,
                     (CENTRE[0] + math.cos(needle) * (RING_R - 8),
                      CENTRE[1] + math.sin(needle) * (RING_R - 8)),
                     (CENTRE[0] + math.cos(needle) * (RING_R + 24),
                      CENTRE[1] + math.sin(needle) * (RING_R + 24)), 3)


def month_rh_spread(month):
    lo, hi = 100.0, 0.0
    for record in month["days"]:
        lo = min(lo, min(record["rh"]))
        hi = max(hi, max(record["rh"]))
    return lo, hi


def draw(surface, year, month_i, open_count, fonts, cache):
    """One frame: the year ring, the month-flower with `open_count` petals, captions."""
    surface.fill(PAPER)
    month = year[month_i]
    records = month["days"][:open_count]
    newest = month["first"] + open_count - 1
    draw_ring(surface, year, newest)

    key = (month_i, open_count)
    if key not in cache:
        if len(cache) > 26:
            cache.pop(next(iter(cache)))
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        rng = random.Random(month_i * 101 + open_count)
        lo, hi = month_rh_spread(month)
        mean_dp = average([average(r["dp"]) for r in month["days"]])
        n = len(month["days"])
        all_rh = [average(r["rh"]) for r in month["days"]]
        m_lo, m_hi = min(all_rh), max(all_rh)
        for j, record in enumerate(records):
            # Petals rebalance as the month grows: the flower always fills
            # the wheel, day 1 clockwise from the top.
            angle = j / open_count * math.tau - math.pi / 2
            mean_rh = average(record["rh"])
            # Reach: how humid the day was, against its month and against the ramp.
            rel = (mean_rh - m_lo) / (m_hi - m_lo) if m_hi > m_lo else 0.5
            frac = 0.5 * rel + 0.5 * clamp((mean_rh - 40.0) / 60.0)
            swirl = clamp((average(record["dp"]) - mean_dp) / 8.0, -1.0, 1.0) * 0.45
            petal(layer, angle, record, frac, swirl, rng)
        mean_rh_month = average([average(r["rh"]) for r in month["days"]])
        draw_dust(layer, hum_colour(mean_rh_month))
        draw_heart(layer, hum_colour(mean_rh_month))
        cache[key] = layer
    surface.blit(cache[key], (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    last = records[-1]
    date = f"2025-{month['month']:02d}-{last['day']:02d}"
    line1 = fonts[0].render(date, True, INK)
    line2 = fonts[1].render(
        f"{open_count} of {len(month['days'])} petals   "
        f"humidity {average([average(r['rh']) for r in records]):.0f} %   "
        f"← → grow   ↑ ↓ month   space play", True, (140, 142, 150))
    surface.blit(line1, (24, 20))
    surface.blit(line2, (24, HEIGHT - 40))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", metavar="PNG")
    parser.add_argument("--month", type=int, default=0, metavar="1-12")
    parser.add_argument("--open", type=int, default=0, metavar="N",
                        help="petals open; 0 = the whole month")
    args = parser.parse_args()

    pygame.init()
    fonts = (pygame.font.SysFont("menlo,monaco,arial", 34),
             pygame.font.SysFont("menlo,monaco,arial", 17))
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hong Kong humidity, in bloom")
    clock = pygame.time.Clock()

    year = load_days()
    month_i = (args.month - 1) % 12
    full = len(year[month_i]["days"])
    open_count = full if args.open == 0 else max(1, min(full, args.open))
    playing = False
    cache = {}

    if args.save:
        draw(surface, year, month_i, open_count, fonts, cache)
        pygame.image.save(surface, args.save)
        print(f"saved {args.save} (month {month_i + 1}, {open_count} petals)")
        pygame.quit()
        return

    running = True
    frame = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN
                                             and event.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    open_count += 1
                    if open_count > len(year[month_i]["days"]):
                        month_i = (month_i + 1) % 12
                        open_count = 1
                elif event.key == pygame.K_LEFT:
                    open_count -= 1
                    if open_count < 1:
                        month_i = (month_i - 1) % 12
                        open_count = len(year[month_i]["days"])
                elif event.key == pygame.K_UP:
                    month_i = (month_i + 1) % 12
                    open_count = len(year[month_i]["days"])
                elif event.key == pygame.K_DOWN:
                    month_i = (month_i - 1) % 12
                    open_count = len(year[month_i]["days"])
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_s:
                    name = HERE / "out" / f"bloom-{month_i + 1:02d}-{open_count:02d}.png"
                    (HERE / "out").mkdir(parents=True, exist_ok=True)
                    pygame.image.save(surface, name)
                    print(f"saved {name.name}")
            elif event.type == pygame.MOUSEWHEEL:
                open_count = max(1, min(len(year[month_i]["days"]),
                                        open_count + event.y))
        if playing and frame % 4 == 0:
            open_count += 1
            if open_count > len(year[month_i]["days"]):
                month_i = (month_i + 1) % 12
                open_count = 1
        draw(surface, year, month_i, open_count, fonts, cache)
        pygame.display.flip()
        clock.tick(FPS)
        frame += 1
    pygame.quit()


if __name__ == "__main__":
    main()
