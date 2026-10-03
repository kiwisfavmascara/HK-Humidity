# /// script
# requires-python = ">=3.10"
# dependencies = ["pygame-ce"]
# ///

"""
A flower of dust that opens and closes with the air: 8,760 hours as one shape.

    uv run --with pygame-ce bloom.py

Keys: LEFT/RIGHT move one day, UP/DOWN move one week, SPACE plays or pauses a
full year, the mouse wheel also scrubs, S saves a frame, Q or ESC quits.
Headless: uv run bloom.py --save out.png [--day 213]

The promise: when I choose a day, the flower shows that day's 24 hours — one
petal of particles per hour, 00:00 at the top. Each petal is a membrane of
curved dotted streams. A stream's reach blends how humid that hour was against
its own day and against the year, so even a soaked day still opens and closes
hour by hour, and a dry day blooms small. The colour is the hour's relative
humidity — dry edges glow blue, soaked ones magenta — and each petal shimmers
between neighbouring hues across its width. The curl of a petal is the hour's
dew point: warm humid air bends the streams one way, cool air the other, so
the flower's gesture records which kind of wet the day was. Loose dust drifts
past the petal tips; its colour is the day's mean humidity. The faint outer
ring is the whole year: one tick per day, coloured by that day's mean
humidity, with a needle on the chosen day. Every number comes from
data/*.json — nothing here is decorative.
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
R_MAX = 262.0                 # stream length at 100 % humidity
R_IN = R_MAX * 0.15           # streams start here, leaving a visible heart
RING_R = R_MAX * 1.14         # the year ring's inner radius
PAPER = (5, 6, 10)            # night air; the dust carries the colour
INK = (232, 230, 224)

# Humidity 30-100 %, dry air to soaked air: royal blue -> teal -> jade ->
# violet -> magenta -> rose, the ramp of the reference bloom.
HUM_STOPS = [(30, 60, 135), (0, 130, 160), (40, 170, 160),
             (140, 110, 215), (205, 95, 200), (250, 105, 150)]

# Dew point 4-28 C, only used for the bend of a petal.
DEW_STOPS = [(26, 42, 96), (32, 118, 181), (94, 197, 187),
             (222, 217, 121), (233, 150, 68), (214, 69, 65)]


def load_days():
    """The committed snapshot, as one record per day: 24 humidities, 24 dew points."""
    reply = json.loads(FILE.read_text(encoding="utf-8"))
    hours = reply["hourly"]
    times, rh, dp = hours["time"], hours["relative_humidity_2m"], hours["dewpoint_2m"]
    days = []
    for stamp, a, b in zip(times, rh, dp):
        month, day = int(stamp[5:7]), int(stamp[8:10])
        if not days or days[-1]["day"] != day or days[-1]["month"] != month:
            days.append({"month": month, "day": day, "rh": [], "dp": []})
        days[-1]["rh"].append(a)
        days[-1]["dp"].append(b)
    return days


def average(numbers):
    total = 0
    for value in numbers:
        total += value
    return total / len(numbers)


def _ramp(stops, value, low, high):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    pos = t * (len(stops) - 1)
    i = min(int(pos), len(stops) - 2)
    f = pos - i
    return tuple(int(a + (b - a) * f) for a, b in zip(stops[i], stops[i + 1]))


def hum_colour(rh):
    """One stop along the humidity ramp, 30-100 %."""
    return _ramp(HUM_STOPS, rh, 30.0, 100.0)


def petal(surface, angle, frac, rh, bend, rng):
    """One petal: a membrane of curved dotted streams.
    frac (0-1) sets the reach, rh colours it, bend curls the tip."""
    length = R_IN + 30 + frac * (R_MAX - R_IN - 30)
    if frac < 0.06:
        return
    spread = length * (0.075 + 0.095 * frac)        # narrow enough that 24 petals stay distinct
    streams = 18 + int(frac * 14)                   # wet hours weave more silk
    swirl = bend * 0.55                             # the tip curls with the dew point
    ox = CENTRE[0] + math.cos(angle) * R_IN
    oy = CENTRE[1] + math.sin(angle) * R_IN
    base = hum_colour(rh)
    boost = 1.45                                    # saturated dust, not grey
    dots = 32
    for s in range(streams):
        u = (s / (streams - 1)) * 2 - 1 if streams > 1 else 0.0
        # Iridescence: the dry edge of a petal cools, the wet edge warms,
        # so each membrane shimmers between neighbouring hues.
        sheen = hum_colour(max(30.0, min(100.0, rh + u * 12)))
        mix = abs(u) * 0.65
        base = tuple(int(a + (b - a) * mix) for a, b in zip(hum_colour(rh), sheen))
        edge = math.sqrt(max(0.0, 1.0 - u * u * 0.85))   # side streams shorter
        for i in range(dots):
            t = (i + 1) / dots
            # The spine curls: the whole fan turns as it leaves the heart.
            a = angle + swirl * t * t
            dx, dy = math.cos(a), math.sin(a)
            px, py = -dy, dx
            reach = (R_IN + (length - R_IN) * t) * (0.72 + 0.28 * edge)
            off = u * spread * math.sin(math.pi * min(1.0, t * 1.02)) ** 0.8
            x = CENTRE[0] + dx * reach + px * off
            y = CENTRE[1] + dy * reach + py * off
            # Bright heart, glowing tip, dim mid-relaxation like silk in light.
            fade = (0.18 + 0.82 * t) * (0.45 + 0.55 * math.sin(math.pi * t) ** 0.35)
            fade *= edge * (0.30 + 0.60 * frac)
            bright = int(255 * min(1.0, fade))
            r = min(255, int(base[0] * boost))
            g = min(255, int(base[1] * boost))
            b = min(255, int(base[2] * boost))
            if rng.random() < 0.035:                # a bright mote with a halo
                r, g, b = min(255, r + 90), min(255, g + 90), min(255, b + 90)
                pygame.draw.circle(surface, (r // 5, g // 5, b // 5),
                                   (int(x), int(y)), 3)
                radius = 2
            else:
                radius = 2 if i % 8 == 0 else 1
            pygame.draw.circle(surface, (r * bright // 255, g * bright // 255,
                                         b * bright // 255),
                               (int(x), int(y)), radius)


def draw_dust(surface, days, current):
    """Loose motes drifting off the petal tips, coloured by the day's mean humidity."""
    rng = random.Random(current * 97 + 13)
    colour = hum_colour(average(days[current]["rh"]))
    for _ in range(70):
        angle = rng.random() * math.tau
        dist = R_MAX * (0.72 + rng.random() ** 1.5 * 0.42)   # mostly past the tips
        x = CENTRE[0] + math.cos(angle) * dist
        y = CENTRE[1] + math.sin(angle) * dist
        bright = int(150 * (0.3 + rng.random() * 0.7))
        pygame.draw.circle(surface, (colour[0] * bright // 255,
                                     colour[1] * bright // 255,
                                     colour[2] * bright // 255),
                           (int(x), int(y)), 1)


def draw_heart(surface, days, current):
    """A small knot of bright dust at the centre of the day."""
    rng = random.Random(current * 31 + 7)
    colour = hum_colour(average(days[current]["rh"]))
    for _ in range(120):
        angle = rng.random() * math.tau
        dist = rng.random() ** 1.6 * (R_IN - 6)
        x = CENTRE[0] + math.cos(angle) * dist
        y = CENTRE[1] + math.sin(angle) * dist
        bright = int(170 * (0.4 + rng.random() * 0.6))
        pygame.draw.circle(surface, (colour[0] * bright // 255,
                                     colour[1] * bright // 255,
                                     colour[2] * bright // 255),
                           (int(x), int(y)), 1)


def draw_ring(surface, days, current):
    """365 ticks, one per day, coloured by that day's mean humidity."""
    for i, record in enumerate(days):
        angle = i / len(days) * math.tau - math.pi / 2
        mean = average(record["rh"])
        length = 8 + (mean - 40) / 60 * 10          # 40-100 % -> 8-18 px
        colour = hum_colour(mean)
        colour = (colour[0] // 3 + 40, colour[1] // 3 + 40, colour[2] // 3 + 40)
        x1 = CENTRE[0] + math.cos(angle) * RING_R
        y1 = CENTRE[1] + math.sin(angle) * RING_R
        x2 = CENTRE[0] + math.cos(angle) * (RING_R + length)
        y2 = CENTRE[1] + math.sin(angle) * (RING_R + length)
        pygame.draw.line(surface, colour, (x1, y1), (x2, y2), 2)
    needle = current / len(days) * math.tau - math.pi / 2
    pygame.draw.line(surface, INK,
                     (CENTRE[0] + math.cos(needle) * (RING_R - 8),
                      CENTRE[1] + math.sin(needle) * (RING_R - 8)),
                     (CENTRE[0] + math.cos(needle) * (RING_R + 24),
                      CENTRE[1] + math.sin(needle) * (RING_R + 24)), 3)


def draw(surface, days, current, fonts, cache):
    """One frame: the year ring, the dust flower of the chosen day, the captions."""
    surface.fill(PAPER)
    draw_ring(surface, days, current)
    record = days[current]

    # The flower is slow to grow, so each day is rendered once and kept.
    if current not in cache:
        if len(cache) > 42:
            cache.pop(next(iter(cache)))
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        rng = random.Random(current * 1009 + 3)     # stable composition per day
        mean_dp = average(record["dp"])
        lo, hi = min(record["rh"]), max(record["rh"])
        for hour in range(24):
            angle = hour / 24 * math.tau - math.pi / 2   # 00:00 at the top
            rh = record["rh"][hour]
            # Reach blends the hour against its own day and against the year,
            # so even a soaked day still opens and closes hour by hour.
            rel = (rh - lo) / (hi - lo) if hi > lo else 0.5
            frac = 0.75 * rel + 0.25 * max(0.0, min(1.0, (rh - 40.0) / 60.0))
            bend = max(-1.0, min(1.0, (record["dp"][hour] - mean_dp) / 9.0))
            petal(layer, angle, frac, rh, bend, rng)
        draw_dust(layer, days, current)
        draw_heart(layer, days, current)
        cache[current] = layer
    surface.blit(cache[current], (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    date = f"2025-{record['month']:02d}-{record['day']:02d}"
    line1 = fonts[0].render(date, True, INK)
    line2 = fonts[1].render(
        f"humidity {average(record['rh']):.0f} %   dew point {average(record['dp']):.1f} C   "
        f"← → day   ↑ ↓ week   space play", True, (140, 142, 150))
    surface.blit(line1, (24, 20))
    surface.blit(line2, (24, HEIGHT - 40))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", metavar="PNG")
    parser.add_argument("--day", type=int, default=0, metavar="N")
    args = parser.parse_args()

    pygame.init()
    fonts = (pygame.font.SysFont("menlo,monaco,arial", 34),
             pygame.font.SysFont("menlo,monaco,arial", 17))
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Hong Kong humidity, in bloom")
    clock = pygame.time.Clock()

    days = load_days()
    current = args.day % len(days)
    playing = False
    cache = {}

    if args.save:
        draw(surface, days, current, fonts, cache)
        pygame.image.save(surface, args.save)
        print(f"saved {args.save} (day {current + 1} of {len(days)})")
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
                    current = (current + 1) % len(days)
                elif event.key == pygame.K_LEFT:
                    current = (current - 1) % len(days)
                elif event.key == pygame.K_UP:
                    current = (current + 7) % len(days)
                elif event.key == pygame.K_DOWN:
                    current = (current - 7) % len(days)
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_s:
                    name = HERE / "out" / f"bloom-{current + 1:03d}.png"
                    (HERE / "out").mkdir(parents=True, exist_ok=True)
                    pygame.image.save(surface, name)
                    print(f"saved {name.name}")
            elif event.type == pygame.MOUSEWHEEL:
                current = (current + event.y) % len(days)
        if playing and frame % 3 == 0:
            current = (current + 1) % len(days)
        draw(surface, days, current, fonts, cache)
        pygame.display.flip()
        clock.tick(FPS)
        frame += 1
    pygame.quit()


if __name__ == "__main__":
    main()
