# /// script
# requires-python = ">=3.10"
# dependencies = ["pygame-ce"]
# ///

"""
A flower that grows with the year: one flower is one month, one petal is one day.

    uv run --with pygame-ce bloom.py

Keys: RIGHT opens one more petal (one more day), LEFT closes one; when a month
is full, the next petal starts the following month. UP/DOWN jump between
months, SPACE plays the year growing from January the 1st, the mouse wheel and
mouse clicks also open and close, holding an arrow key keeps growing, S saves
a frame, Q or ESC quits. Click the window once first: key presses follow the
focused window, and the terminal you launched it from would otherwise keep
them.
Headless: uv run bloom.py --save out.png [--month 6 --open 16]
          uv run bloom.py --sheet out/bloom-year.png   (all twelve months)

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
flower you end up with is the month, petal by petal. The petals keep their
places — day 1 at the top, day 2 clockwise of it, and so on — so a petal, once
grown, never moves again, and the month fills the wheel in order. Move the
mouse over a petal and that day lights up, with its own humidity and dew point
written at the foot of the window. The faint outer ring is still the whole
year: one tick per day with a needle on the newest petal.
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


# How a day's humidity becomes a petal's reach.
#   REL_WEIGHT   how much of the reach is "wetter than the rest of this month"
#                (the rest is the absolute, year-wide reading)
#   REACH_POWER  a gentle compression, so a two-point gap is not a chasm
#   REACH_FLOOR  no petal disappears: the driest day is a short petal, not a gap
REL_WEIGHT = 0.35
REACH_POWER = 0.85
REACH_FLOOR = 0.12


def _ramp(stops, value, low, high):
    t = clamp((value - low) / (high - low))
    pos = t * (len(stops) - 1)
    i = min(int(pos), len(stops) - 2)
    f = pos - i
    return tuple(int(a + (b - a) * f) for a, b in zip(stops[i], stops[i + 1]))


def hum_colour(rh):
    """One stop along the humidity ramp, 30-100 %."""
    return _ramp(HUM_STOPS, rh, 30.0, 100.0)


def petal(surface, angle, record, frac, swirl, rng, glow=1.0):
    """One petal = one day. The radius is the hour: 00:00 at the heart,
    24:00 at the tip. Colour is the hour's humidity, swell is the hour's
    humidity, curl is the day's dew point. `glow` lifts a hovered petal."""
    length = R_IN + 40 + frac * (R_MAX - R_IN - 40)
    spread = length * 0.30                        # a broad membrane, like the study
    streams = 20                                  # warp threads of dust
    dots = 46                                     # weft: finer than the hours
    boost = 1.45 * glow
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
            r = int((base[0] + (sheen[0] - base[0]) * mix) * boost)
            g = int((base[1] + (sheen[1] - base[1]) * mix) * boost)
            b = int((base[2] + (sheen[2] - base[2]) * mix) * boost)
            fade = (0.20 + 0.80 * t) * edge * (0.40 + 0.60 * math.sin(math.pi * t) ** 0.3)
            bright = int(255 * min(1.0, fade * (1.0 + 0.55 * (glow - 1.0))))
            if rng.random() < 0.03 * glow:        # a bright mote with a halo
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


def petal_frac(month, record):
    """How far this day's petal reaches: its own month and the whole ramp, mixed,
    then compressed so the flower stays readable, with a floor so no day vanishes."""
    means = [average(r["rh"]) for r in month["days"]]
    lo, hi = min(means), max(means)
    mean_rh = average(record["rh"])
    rel = (mean_rh - lo) / (hi - lo) if hi > lo else 0.5
    abso = clamp((mean_rh - 40.0) / 60.0)
    mixed = REL_WEIGHT * rel + (1.0 - REL_WEIGHT) * abso
    return max(REACH_FLOOR, mixed ** REACH_POWER)


def petal_at(pos, year, month_i, open_count):
    """Which petal is under the cursor? Fixed slots, so this is just arithmetic."""
    month = year[month_i]
    dx, dy = pos[0] - CENTRE[0], pos[1] - CENTRE[1]
    dist = math.hypot(dx, dy)
    if dist < R_IN * 0.85 or dist > R_MAX * 1.06:
        return None
    # 0 at the top, growing clockwise — the same order the petals are drawn in.
    angle = (math.atan2(dy, dx) + math.pi / 2) % math.tau
    n = len(month["days"])
    j = int(angle / (math.tau / n)) % n
    if j >= open_count:
        return None
    record = month["days"][j]
    tip = R_IN + 40 + petal_frac(month, record) * (R_MAX - R_IN - 40)
    return j if dist <= tip * 1.06 else None


def draw(surface, year, month_i, open_count, fonts, cache, captions=True,
         hover=None, glow_cache=None):
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
        mean_dp = average([average(r["dp"]) for r in month["days"]])
        n = len(month["days"])
        for j, record in enumerate(records):
            # Fixed slots: day 1 at the top, day 2 clockwise of it, and so on.
            # A petal that has opened never moves again.
            angle = j / n * math.tau - math.pi / 2
            frac = petal_frac(month, record)
            swirl = clamp((average(record["dp"]) - mean_dp) / 8.0, -1.0, 1.0) * 0.45
            petal(layer, angle, record, frac, swirl, rng)
        mean_rh_month = average([average(r["rh"]) for r in month["days"]])
        draw_dust(layer, hum_colour(mean_rh_month))
        draw_heart(layer, hum_colour(mean_rh_month))
        cache[key] = layer
    surface.blit(cache[key], (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # The petal under the cursor is drawn a second time, brighter.
    if hover is not None and glow_cache is not None and hover < len(records):
        gkey = (month_i, open_count, hover)
        if gkey not in glow_cache:
            if len(glow_cache) > 14:
                glow_cache.pop(next(iter(glow_cache)))
            layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            rng = random.Random(month_i * 101 + open_count)   # same dust, same places
            record = records[hover]
            mean_dp = average([average(r["dp"]) for r in month["days"]])
            angle = hover / len(month["days"]) * math.tau - math.pi / 2
            frac = petal_frac(month, record)
            swirl = clamp((average(record["dp"]) - mean_dp) / 8.0, -1.0, 1.0) * 0.45
            petal(layer, angle, record, frac, swirl, rng, glow=2.1)
            glow_cache[gkey] = layer
        surface.blit(glow_cache[gkey], (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    last = records[-1]
    if not captions:
        return
    date = f"2025-{month['month']:02d}-{last['day']:02d}"
    line1 = fonts[0].render(date, True, INK)
    if hover is not None and hover < len(records):
        record = records[hover]
        line2_text = (f"day {record['day']:02d} under the cursor   "
                      f"humidity {average(record['rh']):.0f} %   "
                      f"dew point {average(record['dp']):.1f} C")
    else:
        line2_text = (f"{open_count} of {len(month['days'])} petals   "
                      f"humidity {average([average(r['rh']) for r in records]):.0f} %   "
                      f"← → grow (hold, click, or wheel)   ↑ ↓ month   space play")
    line2 = fonts[1].render(line2_text, True, (140, 142, 150))
    surface.blit(line1, (24, 20))
    surface.blit(line2, (24, HEIGHT - 40))


def render_sheet(days, fonts, scale=0.52):
    """The whole year on one page: twelve months, each a flower fully open."""
    cell_w, cell_h = int(WIDTH * scale), int(HEIGHT * scale)
    cols, rows = 4, 3
    pad = 18
    sheet = pygame.Surface((cols * cell_w + (cols + 1) * pad,
                            rows * cell_h + (rows + 1) * pad + 44))
    sheet.fill((10, 11, 15))
    title_font = pygame.font.SysFont("menlo,monaco,arial", 24)
    label_font = pygame.font.SysFont("menlo,monaco,arial", 18)
    names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
             "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    title = title_font.render(
        "Hong Kong 2025, in bloom — one flower per month, one petal per day, "
        "the radius is the hour", True, (226, 224, 218))
    sheet.blit(title, (pad + 6, 12))
    frame = pygame.Surface((WIDTH, HEIGHT))
    for month_i in range(12):
        count = len(days[month_i]["days"])
        draw(frame, days, month_i, count, fonts, {}, captions=False)
        small = pygame.transform.smoothscale(frame, (cell_w, cell_h))
        col, row = month_i % cols, month_i // cols
        x = pad + col * (cell_w + pad)
        y = 44 + pad + row * (cell_h + pad)
        sheet.blit(small, (x, y))
        mean = average([average(r["rh"]) for r in days[month_i]["days"]])
        label = label_font.render(
            f"{names[month_i]}  ·  {count} days  ·  mean {mean:.0f} %",
            True, (200, 202, 210))
        sheet.blit(label, (x + 10, y + 8))
    return sheet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", metavar="PNG")
    parser.add_argument("--sheet", metavar="PNG",
                        help="render all twelve months on one page")
    parser.add_argument("--play", action="store_true",
                        help="start with the year already growing")
    parser.add_argument("--month", type=int, default=0, metavar="1-12")
    parser.add_argument("--open", type=int, default=0, metavar="N",
                        help="petals open; 0 = the whole month")
    parser.add_argument("--hover", type=int, default=0, metavar="N",
                        help="draw petal N as if the cursor were on it")
    args = parser.parse_args()

    pygame.init()
    fonts = (pygame.font.SysFont("menlo,monaco,arial", 34),
             pygame.font.SysFont("menlo,monaco,arial", 17))
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hong Kong humidity, in bloom — click this window, then ← →")
    clock = pygame.time.Clock()
    pygame.key.set_repeat(280, 45)      # holding an arrow key keeps growing

    year = load_days()
    month_i = (args.month - 1) % 12
    full = len(year[month_i]["days"])
    open_count = full if args.open == 0 else max(1, min(full, args.open))
    playing = args.play
    hover = (args.hover - 1) if args.hover else None
    cache = {}
    glow_cache = {}

    if args.sheet:
        pygame.image.save(render_sheet(year, fonts), args.sheet)
        print(f"saved {args.sheet} (twelve months)")
        pygame.quit()
        return

    if args.save:
        draw(surface, year, month_i, open_count, fonts, cache,
             hover=hover, glow_cache=glow_cache)
        pygame.image.save(surface, args.save)
        print(f"saved {args.save} (month {month_i + 1}, {open_count} petals)")
        pygame.quit()
        return

    def report():
        """Mirror the state in the terminal, so it is visible even unfocused."""
        month = year[month_i]
        record = month["days"][open_count - 1]
        note = f"petal {hover + 1} lit" if hover is not None else ""
        print(f"\r2025-{month['month']:02d}-{record['day']:02d}   "
              f"{open_count} of {len(month['days'])} petals   "
              f"{'growing...' if playing else 'paused   '}  {note}     ",
              end="", flush=True)

    def track(pos=None):
        """Which petal is under the cursor right now?"""
        nonlocal hover
        found = petal_at(pos if pos is not None else pygame.mouse.get_pos(),
                         year, month_i, open_count)
        if found != hover:
            hover = found
            try:      # a hand over a petal; fails on some drivers, which is fine
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if found is not None
                                        else pygame.SYSTEM_CURSOR_ARROW)
            except pygame.error:
                pass
            report()

    def grow():
        nonlocal month_i, open_count
        open_count += 1
        if open_count > len(year[month_i]["days"]):
            month_i = (month_i + 1) % 12
            open_count = 1
        report()
        track()

    def shrink():
        nonlocal month_i, open_count
        open_count -= 1
        if open_count < 1:
            month_i = (month_i - 1) % 12
            open_count = len(year[month_i]["days"])
        report()
        track()

    print("click the window, then use ← → to open and close petals")
    report()

    running = True
    frame = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN
                                             and event.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    grow()
                elif event.key == pygame.K_LEFT:
                    shrink()
                elif event.key == pygame.K_UP:
                    month_i = (month_i + 1) % 12
                    open_count = len(year[month_i]["days"])
                    report()
                    track()
                elif event.key == pygame.K_DOWN:
                    month_i = (month_i - 1) % 12
                    open_count = len(year[month_i]["days"])
                    report()
                    track()
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                    report()
                elif event.key == pygame.K_s:
                    name = HERE / "out" / f"bloom-{month_i + 1:02d}-{open_count:02d}.png"
                    (HERE / "out").mkdir(parents=True, exist_ok=True)
                    pygame.image.save(surface, name)
                    print(f"\nsaved {name.name}")
                    report()
            elif event.type == pygame.MOUSEMOTION:
                track(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                for _ in range(abs(event.y)):
                    grow() if event.y > 0 else shrink()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:            # left click opens a petal
                    grow()
                elif event.button == 3:          # right click closes one
                    shrink()
        if playing and frame % 4 == 0:
            grow()
        draw(surface, year, month_i, open_count, fonts, cache,
             hover=hover, glow_cache=glow_cache)
        pygame.display.flip()
        clock.tick(FPS)
        frame += 1
    print()
    pygame.quit()


if __name__ == "__main__":
    main()
