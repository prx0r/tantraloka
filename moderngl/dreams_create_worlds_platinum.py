#!/usr/bin/env python3
"""
DREAMS CREATE WORLDS
Platinum procedural visual essay — dreams as primary reality.

Adapted from:
Seth, Dreams and Projections of Consciousness (Jane Roberts, 1966-67)
Dreams, "Evolution", and Value Fulfillment (Jane Roberts, 1979-82)

HOUSE CONTRACT
--------------
• 5–10 seconds per shot.
• Every shot performs a visible transformation of the claim.
• Clean ivory scientific field; no lined manuscript background.
• Genuinely animated processes, not static labelled slides.
• Sparse typography used only as conceptual seals.
• Visual vocabulary distinct from all previous films.

PALETTE ROLES
-------------
INK     physical waking reality / the "given" conventional view
CYAN    dream-space / the imaginal dimension
GOLD    the inventive spark / the source of form
VIOLET  the dreaming self / the psyche in its native state
GREEN   the cooperative dreaming of species / shared dream
CRIMSON the collapse into waking / forgetting
PAPER   the substrate of dreaming / the ground of being

CONTINUITY OBJECT
-----------------
A violet "dream-thread" — a sinuous line that behaves like a living
thought — connects every scene. It weaves through dream-space, pierces
into waking reality, and shows that dream and waking are the same
substance at different vibration.

OUTPUT
------
output_dreams_create_worlds/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  dreams_create_worlds.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python dreams_create_worlds_platinum.py
python dreams_create_worlds_platinum.py --preview
python dreams_create_worlds_platinum.py --scene 12
python dreams_create_worlds_platinum.py --fps 12 --width 1920 --height 1080
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_dreams_create_worlds")
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 10

IVORY = (249, 247, 241)
PAPER = (242, 239, 231)
INK = (31, 36, 42)
SOFT_INK = (85, 91, 97)
SILVER = (180, 187, 191)
PALE_SILVER = (224, 228, 228)
CYAN = (55, 157, 178)
PALE_CYAN = (194, 227, 233)
DEEP_CYAN = (35, 104, 128)
GOLD = (193, 155, 72)
PALE_GOLD = (235, 218, 172)
CRIMSON = (164, 57, 69)
PALE_CRIMSON = (231, 198, 201)
GREEN = (68, 139, 99)
PALE_GREEN = (196, 225, 206)
VIOLET = (107, 82, 151)
PALE_VIOLET = (218, 208, 235)
WHITE = (255, 254, 250)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def mix(a, b, t):
    t = clamp(t)
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a))
    return q * q * (3 - 2 * q)


def ease(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def pulse(t, speed=1.0, phase=0.0):
    return 0.5 + 0.5 * math.sin(math.tau * (speed * t + phase))


def font(path, size):
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def scientific_field(w, h, seed):
    rng = np.random.default_rng(seed)
    base = np.empty((h, w, 3), dtype=np.float32)
    base[:] = IVORY
    fine = rng.normal(0, 0.95, (h, w, 1))
    base += fine
    yy, xx = np.mgrid[0:h, 0:w]
    halo = np.exp(
        -(((xx - w * 0.52) / (w * 0.36)) ** 2
          + ((yy - h * 0.39) / (h * 0.30)) ** 2) * 2.1
    )
    base[..., 0] += halo * 1.5
    base[..., 1] += halo * 4.0
    base[..., 2] += halo * 5.5
    base = np.clip(base, 0, 255).astype(np.uint8)
    return Image.fromarray(base, "RGB").convert("RGBA")


def centered(draw, xy, text, fnt, fill=INK):
    draw.text(xy, text, font=fnt, fill=fill, anchor="mm")


def border(im):
    w, h = im.size
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 26, w - 26, h - 26), radius=18, outline=(*INK, 48), width=2)
    for x, y in ((52, 52), (w - 52, 52), (52, h - 52), (w - 52, h - 52)):
        d.line((x - 9, y, x + 9, y), fill=(*CYAN, 80), width=1)
        d.line((x, y - 9, x, y + 9), fill=(*CYAN, 80), width=1)


def seal(im, title, subtitle="", color=INK):
    w, h = im.size
    d = ImageDraw.Draw(im)
    tf = font(FONT_SERIF_BOLD, max(22, int(h * 0.040)))
    sf = font(FONT_SANS, max(13, int(h * 0.019)))
    centered(d, (w / 2, h * 0.875), title, tf, color)
    if subtitle:
        centered(d, (w / 2, h * 0.923), subtitle, sf, SOFT_INK)


def glow_circle(im, x, y, r, color, alpha=170, blur=16):
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.ellipse((x - r, y - r, x + r, y + r), fill=(*color, int(alpha)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    core = layer(im.size)
    ImageDraw.Draw(core).ellipse(
        (x - r * .38, y - r * .38, x + r * .38, y + r * .38),
        fill=(*mix(color, WHITE, .35), min(255, int(alpha) + 55)),
    )
    im.alpha_composite(core)


def glow_line(im, points, color, width=4, alpha=210, blur=12):
    if len(points) < 2:
        return
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.line(points, fill=(*color, int(alpha)), width=width * 3, joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).line(
        points, fill=(*mix(color, WHITE, .08), min(255, int(alpha) + 25)),
        width=width, joint="curve",
    )
    im.alpha_composite(fg)


def partial(points, amount):
    amount = clamp(amount)
    if not points:
        return []
    if amount >= 1:
        return points
    target = amount * (len(points) - 1)
    idx = int(target)
    frac = target - idx
    out = list(points[:idx + 1])
    if idx + 1 < len(points):
        a, b = points[idx], points[idx + 1]
        out.append((lerp(a[0], b[0], frac), lerp(a[1], b[1], frac)))
    return out


def dream_thread(cx, cy, length, amp, phase=0.0, samples=100):
    pts = []
    for i in range(samples):
        q = i / (samples - 1)
        x = cx - length / 2 + q * length
        y = cy + math.sin(q * math.tau * 3 + phase) * amp * (0.3 + 0.7 * math.sin(math.pi * q) ** 0.6)
        pts.append((x, y))
    return pts


def draw_bed(im, cx, cy, w, h, alpha=200):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
                        radius=8, fill=(*PALE_SILVER, alpha), outline=(*INK, alpha), width=2)
    d.rectangle((cx - w * 0.35, cy - h * 0.6, cx + w * 0.35, cy - h * 0.35),
                fill=(*SILVER, alpha // 2))


def draw_sleeping_figure(im, cx, cy, scale, alpha=200):
    d = ImageDraw.Draw(im)
    head_r = 12 * scale
    d.ellipse((cx - head_r, cy - 25 * scale - head_r,
               cx + head_r, cy - 25 * scale + head_r),
              fill=(*PALE_GOLD, alpha), outline=(*INK, alpha), width=2)
    body_pts = [
        (cx, cy - 25 * scale + head_r),
        (cx, cy + 15 * scale),
        (cx - 15 * scale, cy + 35 * scale),
        (cx + 10 * scale, cy + 30 * scale),
        (cx - 5 * scale, cy + 15 * scale),
    ]
    d.line(body_pts, fill=(*INK, alpha), width=3)


# =============================================================================
# VISUAL FUNCTIONS
# =============================================================================

def vis_sleep_cycle(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    draw_bed(im, cx, cy + 40, 140, 60, int(200 * reveal))
    draw_sleeping_figure(im, cx, cy + 40, 1.0, int(200 * reveal))
    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        pts = dream_thread(cx, cy - 20, w * 0.40, h * 0.06, t * 0.5)
        glow_line(im, partial(pts, q), VIOLET, 4, int(150 * q), 10)
    seal(im, "ONE THIRD OF YOUR LIFE",
         "you spend it in a world that science says does not exist", VIOLET)


def vis_brain_active(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    # brain outline
    d.ellipse((cx - 55, cy - 40, cx + 55, cy + 40),
              fill=(*PALE_SILVER, 180), outline=(*INK, 160), width=3)
    if reveal > 0.2:
        n_spots = int(20 * reveal)
        rng = random.Random(71)
        for i in range(n_spots):
            a = rng.uniform(0, math.tau)
            rr = rng.uniform(0, 40)
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.7
            act = pulse(t * 0.5 + i * 0.7)
            col = GOLD if act > 0.5 else CYAN
            d.ellipse((x - 4, y - 4, x + 4, y + 4),
                      fill=(*col, int(100 + 100 * act)))
    if reveal > 0.6:
        centered(d, (cx, h * 0.76),
                 "REM SLEEP: THE BRAIN IS AS ACTIVE AS IN WAKING",
                 font(FONT_SANS_BOLD, int(h * 0.019)), GOLD)
    seal(im, "THE WAKING BRAIN IN A SLEEPING BODY",
         "neuroscience cannot explain why", CYAN)


def vis_dreams_not_random(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    n_lines = int(12 * reveal)
    rng = random.Random(44)
    for i in range(n_lines):
        if rng.random() < 0.3:
            continue
        x1 = rng.uniform(w * 0.10, w * 0.90)
        y1 = rng.uniform(h * 0.10, h * 0.70)
        x2 = rng.uniform(w * 0.10, w * 0.90)
        y2 = rng.uniform(h * 0.10, h * 0.70)
        d.line((x1, y1, x2, y2),
               fill=(*VIOLET, int(60 + 100 * pulse(t * 0.3 + i))), width=2)
    if reveal > 0.5:
        pts = dream_thread(cx, cy, w * 0.30, h * 0.05, t * 0.4)
        glow_line(im, pts, CYAN, 4, 160, 10)
    seal(im, "NOT RANDOM NEURAL NOISE",
         "dreams have their own laws — root assumptions — as real as physics", CYAN)


def vis_seth_dream_reality(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    # two faces
    face1_x = cx - w * 0.18
    face2_x = cx + w * 0.18
    for fx, col in ((face1_x, INK), (face2_x, CYAN)):
        d.ellipse((fx - 35, cy - 40, fx + 35, cy + 40),
                  fill=(*PALE_SILVER, 150), outline=(*col, 160), width=3)

    if reveal > 0.3:
        q = smoothstep(0.3, 0.7, u)
        mid_x = lerp(face1_x, face2_x, 0.5)
        pts = dream_thread(mid_x, cy, w * 0.10, h * 0.02, t * 0.3)
        glow_line(im, pts, VIOLET, 3, int(120 * q), 8)

    if reveal > 0.6:
        centered(d, (cx, h * 0.76),
                 "SETH: BOTH ARE LEGITIMATE REALITIES",
                 font(FONT_SANS_BOLD, int(h * 0.019)), VIOLET)
        centered(d, (cx, h * 0.81),
                 "two faces of the same self — one looking at each world",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "TWO WORLDS, ONE SELF",
         "the dream location is as real as the room where the body sleeps", VIOLET)


def vis_conventional_versus(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    d.rectangle((w * 0.10, h * 0.14, w * 0.42, h * 0.36),
                fill=(*PALE_SILVER, 180), outline=(*INK, 160), width=3)
    centered(d, (w * 0.26, h * 0.20), "NEUROSCIENCE", font(FONT_SANS_BOLD, int(h * 0.022)), INK)
    centered(d, (w * 0.26, h * 0.27), "dreams = memory\nconsolidation + noise",
             font(FONT_SANS, int(h * 0.017)), SOFT_INK)

    d.rectangle((w * 0.58, h * 0.14, w * 0.90, h * 0.36),
                fill=(*PALE_VIOLET, 120), outline=(*VIOLET, 160), width=3)
    centered(d, (w * 0.74, h * 0.20), "SETH", font(FONT_SANS_BOLD, int(h * 0.022)), VIOLET)
    centered(d, (w * 0.74, h * 0.27), "dreams = distinct\nreality with own laws",
             font(FONT_SANS, int(h * 0.017)), SOFT_INK)

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        d.line((w * 0.42, h * 0.25, w * 0.58, h * 0.25),
               fill=(*GOLD, int(200 * q)), width=3)
        centered(d, (w * 0.50, h * 0.22), "VS",
                 font(FONT_SERIF_BOLD, int(h * 0.030)), (*GOLD, int(200 * q)))

    seal(im, "TWO FRAMEWORKS",
         "one sees noise — the other sees another dimension", VIOLET)


def vis_dream_wave(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    for i in range(5):
        q = i / 4
        amp = h * 0.04 * (1 - q * 0.4)
        pts = dream_thread(cx, cy - 30 + q * 80, w * 0.50, amp, t * 0.5 + q)
        alpha = int(180 * reveal * (1 - q * 0.5))
        glow_line(im, partial(pts, reveal), VIOLET, 4, alpha, 8)

    if reveal > 0.5:
        centered(d, (cx, h * 0.76),
                 "SETH: THE DREAM WORLD IS THE SOURCE OF PHYSICAL EVENTS",
                 font(FONT_SANS_BOLD, int(h * 0.018)), VIOLET)

    seal(im, "THE DREAMING WAVE",
         "consciousness operates as a wave in the dream state", VIOLET)


def vis_dream_seeding(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    seed = smoothstep(0.1, 0.4, u)
    germinate = smoothstep(0.4, 0.75, u)
    manifest = smoothstep(0.75, 1.0, u)

    if seed > 0:
        draw_belief_seed(im, cx - 50 + seed * 30, cy - 20, t * 1.2, int(200 * seed))

    if germinate > 0:
        pts = dream_thread(cx, cy, w * 0.25, h * 0.04, t * 0.6)
        glow_line(im, partial(pts, germinate), CYAN, 4, int(150 * germinate), 8)

    if manifest > 0:
        d.ellipse((cx - 20 - 20 * manifest, cy - 20 - 20 * manifest,
                   cx + 20 + 20 * manifest, cy + 20 + 20 * manifest),
                  fill=(*PALE_GOLD, int(150 * manifest)),
                  outline=(*GOLD, int(200 * manifest)), width=3)

    seal(im, "SEEDING THE DREAM",
         "a question placed before sleep becomes an event in the world", GOLD)


def draw_belief_seed(im, x, y, phase, alpha=255):
    r = 4 + 2 * pulse(phase, 1.3)
    glow_circle(im, x, y, r, GOLD, min(200, alpha), 6)
    core = layer(im.size)
    ImageDraw.Draw(core).ellipse((x - 2, y - 2, x + 2, y + 2), fill=(*WHITE, min(200, alpha)))
    im.alpha_composite(core)


def vis_dream_source(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    n_particles = int(30 * reveal)
    rng = random.Random(88)
    for i in range(n_particles):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0, w * 0.30)
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        col = VIOLET if i % 3 == 0 else (CYAN if i % 3 == 1 else GOLD)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(*col, int(120 + 80 * pulse(t * 0.3 + i))))

    if reveal > 0.4:
        q = smoothstep(0.4, 0.8, u)
        arrow(d, (cx, cy - 40), (cx, cy - 40 - q * 60), GOLD, 3, 8)
        d.rectangle((cx - 30, cy - 40 - q * 60 - 20, cx + 30, cy - 40 - q * 60 + 20),
                    fill=(*PALE_GOLD, int(120 * q)),
                    outline=(*GOLD, int(160 * q)), width=2)
        centered(d, (cx, cy - 40 - q * 60),
                 "EVENT", font(FONT_SANS_BOLD, int(h * 0.020)), (*GOLD, int(200 * q)))

    seal(im, "ALL EVENTS BEGIN IN DREAMS",
         "physical events are the end products of nonphysical properties", VIOLET)


def vis_primitive_dream(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    pts = dream_thread(cx, cy, w * 0.55, h * 0.05, t * 0.3)
    glow_line(im, partial(pts, reveal), CYAN, 5, int(120 + 100 * reveal), 12)

    if reveal > 0.3:
        labels = ["WATER", "FOOD", "SAFETY", "DIRECTION"]
        for i, lbl in enumerate(labels):
            q = clamp((reveal - 0.3) * 8 - i)
            if q <= 0:
                continue
            x = lerp(w * 0.15, w * 0.85, i / (len(labels) - 1))
            y = cy + h * 0.04 + math.sin(t + i) * 6
            d.rounded_rectangle((x - 30, y - 12, x + 30, y + 12), radius=6,
                                fill=(*mix(WHITE, GOLD, 0.1), int(180 * q)),
                                outline=(*GOLD, int(140 * q)), width=2)
            centered(d, (x, y), lbl, font(FONT_SANS_BOLD, int(h * 0.017)), (*GOLD, int(200 * q)))

    seal(im, "THE ORIGINAL LEARNING GROUND",
         "early man dreamed the location of water — then walked there", GOLD)


def vis_cooperative_dream(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    n_figures = int(6 * reveal)
    for i in range(n_figures):
        a = i * math.tau / max(1, n_figures) + t * 0.1
        r = w * 0.15 + 10 * math.sin(t + i)
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r * 0.5
        draw_belief_seed(im, int(x), int(y), t + i * 0.5, int(180 * reveal))
        d.line((cx, cy, x, y), fill=(*VIOLET, int(80 * reveal)), width=2)

    if reveal > 0.5:
        centered(d, (cx, cy - 8),
                 "ALL SPECIES SHARED THEIR DREAMS",
                 font(FONT_SANS_BOLD, int(h * 0.020)), VIOLET)
        centered(d, (cx, cy + 16),
                 "a cross-species communication older than language",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "THE COOPERATIVE DREAM",
         "in early times, all species shared dreams — a conversation without words", GREEN)


def vis_dream_invention(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    n_items = int(6 * reveal)
    inventions = ["FIRE", "TOOLS", "LANGUAGE", "ART", "CITIES", "SCIENCE"]
    for i in range(n_items):
        x = lerp(w * 0.12, w * 0.88, i / max(1, n_items - 1))
        y = cy + math.sin(i * 2 + t * 0.3) * 8
        d.rounded_rectangle((x - 35, y - 14, x + 35, y + 14), radius=6,
                            fill=(*PALE_CYAN, int(180 * reveal)),
                            outline=(*CYAN, int(140 * reveal)), width=2)
        centered(d, (x, y), inventions[i],
                 font(FONT_SANS_BOLD, int(h * 0.018)), (*CYAN, int(200 * reveal)))

    if reveal > 0.6:
        pts = dream_thread(cx, cy - 20, w * 0.70, h * 0.03, t * 0.4)
        glow_line(im, pts, GOLD, 3, 140, 8)

    seal(im, "MAN DREAMED HIS WORLD AND THEN CREATED IT",
         "every invention began as a dream-image before it became physical", GOLD)


def vis_waking_extension(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    # concentric circles showing emergence
    for i in range(5):
        rr = 30 + i * 30
        alpha = int(180 * reveal * (1 - i / 5))
        col = VIOLET if i < 3 else CYAN
        d.ellipse((cx - rr, cy - rr * 0.6, cx + rr, cy + rr * 0.6),
                  outline=(*col, alpha), width=2)

    if reveal > 0.5:
        centered(d, (cx, h * 0.76),
                 "THE WAKING STATE IS A SPECIALIZED EXTENSION OF THE DREAM STATE",
                 font(FONT_SANS_BOLD, int(h * 0.018)), VIOLET)
        centered(d, (cx, h * 0.81),
                 "waking emerges FROM dreaming — not the other way around",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "THE DREAM IS THE GROUND",
         "waking consciousness floats on a dreaming ocean", VIOLET)


def vis_lucid_dream(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    awareness = smoothstep(0.2, 0.7, u)

    # dream field
    rng = random.Random(99)
    for i in range(25):
        x = rng.uniform(w * 0.08, w * 0.92)
        y = rng.uniform(h * 0.08, h * 0.72)
        alpha = int(150 * reveal * pulse(t * 0.2 + i))
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(*VIOLET, alpha))

    if awareness > 0:
        glow_circle(im, cx, cy, 20, GOLD, int(120 * awareness), 14)
        centered(d, (cx, cy),
                 "I AM DREAMING",
                 font(FONT_SERIF_BOLD, int(h * 0.035)),
                 (*GOLD, int(200 * awareness)))

    if awareness > 0.5:
        q = (awareness - 0.5) * 2
        for a in range(8):
            rr = 40 + 30 * q
            x = cx + math.cos(a * math.tau / 8 + t * 0.2) * rr
            y = cy + math.sin(a * math.tau / 8 + t * 0.2) * rr
            d.line((cx, cy, x, y), fill=(*GOLD, int(80 * q)), width=2)

    seal(im, "LUCIDITY",
         "when the dreamer knows they are dreaming — the rules change", GOLD)


def vis_consciousness_all_species(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    rng = random.Random(31)
    for i in range(20):
        x = lerp(w * 0.10, w * 0.90, rng.random())
        y = lerp(h * 0.08, h * 0.72, rng.random())
        rr = rng.uniform(4, 12)
        col = [GREEN, CYAN, GOLD][i % 3]
        d.ellipse((x - rr / 2, y - rr / 2, x + rr / 2, y + rr / 2),
                  fill=(*mix(WHITE, col, 0.2), int(150 * reveal)),
                  outline=(*col, int(120 * reveal)), width=2)

    if reveal > 0.4:
        for i in range(3):
            x1 = lerp(w * 0.10, w * 0.40, rng.random())
            y1 = lerp(h * 0.08, h * 0.72, rng.random())
            x2 = lerp(w * 0.60, w * 0.90, rng.random())
            y2 = lerp(h * 0.08, h * 0.72, rng.random())
            d.line((x1, y1, x2, y2), fill=(*GOLD, int(60 * reveal)), width=2)

    seal(im, "UNITS OF CONSCIOUSNESS",
         "every atom and molecule possesses kinds of consciousness impossible to analyze", GREEN)


def vis_space_present(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(7):
        rr = 20 + i * 25
        a = int(180 * reveal * (1 - i / 7))
        col = CYAN if i % 2 == 0 else VIOLET
        d.ellipse((cx - rr, cy - rr * 0.5, cx + rr, cy + rr * 0.5),
                  outline=(*col, a), width=2)

    if reveal > 0.4:
        n_stars = int(20 * (reveal - 0.4) / 0.6)
        for i in range(n_stars):
            a = i * math.tau / max(1, n_stars)
            rr = 30 + 40 * pulse(t + i)
            x = cx + math.cos(a + t * 0.1) * rr
            y = cy + math.sin(a + t * 0.1) * rr * 0.5
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(*GOLD, 200))

    seal(im, "THE SPACIOUS PRESENT",
         "past, present, and future coexist — sequence is a filter", VIOLET)


def vis_dialog(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # two brains interacting
    brain1_x = cx - w * 0.20
    brain2_x = cx + w * 0.20

    d.ellipse((brain1_x - 30, cy - 25, brain1_x + 30, cy + 25),
              fill=(*PALE_SILVER, 180), outline=(*INK, 150), width=3)
    d.ellipse((brain2_x - 30, cy - 25, brain2_x + 30, cy + 25),
              fill=(*PALE_VIOLET, 150), outline=(*VIOLET, 150), width=3)

    if reveal > 0.3:
        q = smoothstep(0.3, 0.7, u)
        mid_x = lerp(brain1_x, brain2_x, 0.5)
        d.line((brain1_x + 30, cy, brain2_x - 30, cy),
               fill=(*GOLD, int(150 * q)), width=3)
        draw_belief_seed(im, int(mid_x), cy - 10, t * 0.8, int(150 * q))

    centered(d, (brain1_x, cy + 40),
             "CONSCIOUS MIND",
             font(FONT_SANS_BOLD, int(h * 0.018)), INK)
    centered(d, (brain2_x, cy + 40),
             "DREAMING SELF",
             font(FONT_SANS_BOLD, int(h * 0.018)), VIOLET)

    seal(im, "THE DIALOGUE",
         "the dreaming mind is not asleep — you are not listening", VIOLET)


def vis_inner_senses(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(6):
        a = i * math.tau / 6 + t * 0.1
        rr = w * 0.20 + 15 * math.sin(t * 0.5 + i)
        x = cx + math.cos(a) * rr
        y = cy + math.sin(a) * rr * 0.5
        d.line((cx, cy, x, y), fill=(*GOLD, int(80 * reveal)), width=2)
        d.ellipse((x - 6, y - 6, x + 6, y + 6),
                  fill=(*PALE_GOLD, int(150 * reveal)),
                  outline=(*GOLD, int(120 * reveal)), width=2)

    if reveal > 0.5:
        centered(d, (cx, h * 0.76),
                 "THE INNER SENSES",
                 font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)
        centered(d, (cx, h * 0.81),
                 "they see within the body — they see within the world",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "PERCEPTION BEYOND THE SENSES",
         "the inner senses deliver data from realities the outer senses cannot reach", VIOLET)


def vis_dual_focus(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # two-faced creature
    d.ellipse((cx - 25, cy - 30, cx + 25, cy + 30),
              fill=(*PALE_SILVER, 180), outline=(*INK, 150), width=3)

    left_eye = (cx - 12, cy - 8)
    right_eye = (cx + 12, cy - 8)
    for ex, ey in (left_eye, right_eye):
        d.ellipse((ex - 5, ey - 5, ex + 5, ey + 5),
                  fill=(*(VIOLET if ex < cx else GOLD), 200))

    if reveal > 0.4:
        q = (reveal - 0.4) * 1.7
        for ex, ey, dx, dy in [(left_eye[0], left_eye[1], -30, -10),
                               (right_eye[0], right_eye[1], 30, -10)]:
            end_x = ex + dx * q
            end_y = ey + dy * q
            d.line((ex, ey, end_x, end_y), fill=(*(VIOLET if ex < cx else GOLD), int(100 * q)), width=2)

    seal(im, "TWO FACES OF THE SELF",
         "one looks at the world — one looks at the dream", VIOLET)


def vis_dream_merge(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    merge_pt = smoothstep(0.15, 0.75, u)

    left_pts = dream_thread(cx - w * 0.15, cy, w * 0.20, h * 0.03, t * 0.4)
    right_pts = dream_thread(cx + w * 0.15, cy, w * 0.20, h * 0.03, t * 0.6 + 1)

    if merge_pt < 0.8:
        glow_line(im, left_pts, VIOLET, 4, 160, 10)
        glow_line(im, right_pts, CYAN, 4, 160, 10)

    if merge_pt > 0.2:
        overlap = clamp((merge_pt - 0.2) / 0.6)
        mid_pts = dream_thread(cx, cy, w * 0.30, h * 0.05 * overlap, t * 0.5)
        glow_line(im, mid_pts, GOLD, 5, int(180 * overlap), 12)
        if overlap > 0.6:
            glow_circle(im, cx, cy, 15, GOLD, int(180 * overlap), 12)

    label = "MERGE" if merge_pt > 0.5 else "SEPARATE"
    col = GOLD if merge_pt > 0.5 else VIOLET
    seal(im, f"DREAM AND WAKING {label}",
         "the two are not as separate as you think", col)


def vis_universe_dreamed(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # expanding ripple
    for i in range(6):
        rr = 15 + i * 25 * reveal
        a = int(180 * (1 - i / 6) * reveal)
        d.ellipse((cx - rr, cy - rr * 0.6, cx + rr, cy + rr * 0.6),
                  outline=(*GOLD, a), width=2)

    if reveal > 0.4:
        q = smoothstep(0.4, 0.85, u)
        stars = int(30 * q)
        rng = random.Random(17)
        for i in range(stars):
            a = rng.uniform(0, math.tau)
            rr = rng.uniform(30, 90) * q
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.5
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(*GOLD, int(100 + 100 * pulse(t + i))))

    seal(im, "THE UNIVERSE DREAMED ITSELF INTO BEING",
         "a divine psychological gestalt — and you are part of its dream", GOLD)


def vis_waking_to_dream(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    phase = t * 0.3

    # morphing
    pts = dream_thread(cx, cy, w * 0.30, h * 0.04, phase)
    glow_line(im, partial(pts, reveal), CYAN, 4, int(120 + 100 * reveal), 10)

    if reveal > 0.4:
        q = (reveal - 0.4) / 0.6
        for i in range(10):
            a = i * math.tau / 10 + q * math.pi
            rr = 40 + 30 * q
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.5
            col = mix(VIOLET, GOLD, q)
            d.ellipse((x - 4, y - 4, x + 4, y + 4),
                      fill=(*col, int(120 * q)), outline=(*col, int(80 * q)), width=2)

    done = "WAKING" if reveal < 0.5 else "DREAMING"
    seal(im, f"THE TRANSITION: {done}",
         "you make this journey every night — and every morning", VIOLET)


def vis_final(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    pts = dream_thread(cx, cy, w * 0.55, h * 0.05, t * 0.3)
    glow_line(im, partial(pts, reveal), VIOLET, 5, int(120 + 100 * reveal), 14)

    if reveal > 0.3:
        q = (reveal - 0.3) / 0.7
        glow_circle(im, cx, cy, 25 * q, GOLD, int(120 * q), 18)
        if q > 0.5:
            centered(d, (cx, cy),
                     "DREAM",
                     font(FONT_SERIF_BOLD, int(h * 0.050)),
                     (*GOLD, int(200 * (q - 0.5) * 2)))

    seal(im, "THE WORLD IS A DREAM THAT KNOWS ITSELF",
         "you are the universe dreaming itself awake", VIOLET)


VISUALS = {
    "sleep_cycle": vis_sleep_cycle,
    "brain_active": vis_brain_active,
    "not_random": vis_dreams_not_random,
    "two_worlds": vis_seth_dream_reality,
    "frameworks": vis_conventional_versus,
    "wave": vis_dream_wave,
    "seeding": vis_dream_seeding,
    "source": vis_dream_source,
    "primitive": vis_primitive_dream,
    "cooperative": vis_cooperative_dream,
    "invention": vis_dream_invention,
    "extension": vis_waking_extension,
    "lucid": vis_lucid_dream,
    "consciousness_units": vis_consciousness_all_species,
    "spacious": vis_space_present,
    "dialog": vis_dialog,
    "inner_senses": vis_inner_senses,
    "dual_focus": vis_dual_focus,
    "merge": vis_dream_merge,
    "universe_dreamed": vis_universe_dreamed,
    "transition": vis_waking_to_dream,
    "final": vis_final,
}


@dataclass
class Scene:
    title: str
    narration: str
    duration: float
    visual: str
    params: dict


SCENES = [
    Scene("The third of life",
          "You spend one third of your life in a world that modern science insists does not exist.",
          7.0, "sleep_cycle", {}),
    Scene("The body sleeps — the brain does not",
          "During REM sleep, the brain is as electrically active as during waking. The body is paralyzed. The mind is anywhere but here.",
          7.5, "brain_active", {}),
    Scene("Not random noise",
          "Neuroscience once dismissed dreams as random neural firing. But dreams have structure, narrative, meaning — and their own logic.",
          7.5, "not_random", {}),

    Scene("Seth's claim",
          "In the 1960s, a channeled personality named Seth said: the dream world is as real as the physical world. It has its own laws, its own time, its own geography.",
          8.0, "two_worlds", {}),
    Scene("Two faces",
          "'Pretend you are a creature with two faces. One face looks out upon one world — the other upon another. Both are fully conscious.'",
          8.0, "two_worlds", {}),

    Scene("Two frameworks",
          "Neuroscience says: dreams are memory consolidation and noise. Seth says: dreams are a distinct dimension with its own root assumptions.",
          7.0, "frameworks", {}),

    Scene("The dreaming wave",
          "Seth: 'In dreams, your consciousness operates as a wave — not confined to the body, not bound by space or time.'",
          7.5, "wave", {}),
    Scene("Waves of awareness",
          "When the body sleeps, consciousness returns to its native element — the dreaming sea from which it emerged.",
          7.5, "wave", {}),

    Scene("Seeding",
          "A question placed before sleep becomes a dream. A dream understood becomes an event in the waking world.",
          7.5, "seeding", {}),
    Scene("The night's answer",
          "The dreaming mind does not answer questions with words. It answers with encounters. It shows you what you need to see.",
          7.5, "seeding", {}),

    Scene("Source of events",
          "Seth: 'All physical events are the end products of nonphysical properties. The dream state is the source.'",
          8.0, "source", {}),
    Scene("From dream to world",
          "An idea dreamed becomes a tool. A vision dreamed becomes a city. A fear dreamed becomes an illness.",
          7.5, "source", {}),

    Scene("Original learning",
          "Early humans dreamed the location of water and food. They did not discover the world through trial and error — they were shown.",
          8.0, "primitive", {}),
    Scene("The inner GPS",
          "In dreams, the mind maps territories the body has never visited. The dream came first. The journey followed.",
          7.5, "primitive", {}),

    Scene("Cooperative dreaming",
          "All species once shared their dreams. A cross-species conversation — silent, imagistic, precise — maintained the balance of ecosystems.",
          8.0, "cooperative", {}),
    Scene("The forgotten language",
          "Seth: 'In early times, all species shared their dreams. Man inquired of the animals in his sleep.'",
          8.0, "cooperative", {}),

    Scene("Every invention was dreamed",
          "Fire, tools, language, art, cities, science — every human invention began as a dream-image before it became physical.",
          8.0, "invention", {}),
    Scene("The dream precedes the form",
          "Man dreamed his world and then created it. The physical universe is a dream that solidified.",
          8.0, "invention", {}),

    Scene("Waking is a specialized dream",
          "The waking state is not the opposite of dreaming. It is a specialized extension of dreaming — a focused beam of the same light.",
          8.0, "extension", {}),
    Scene("The ocean and the wave",
          "Dreaming is the ocean. Waking is a wave on that ocean. The wave does not cease to be ocean when it rises.",
          8.0, "extension", {}),

    Scene("Lucid dreaming",
          "In the lucid dream, the dreamer knows they are dreaming. The rules of reality become optional. This is a glimpse of the true nature of all experience.",
          8.0, "lucid", {}),
    Scene("The threshold",
          "Lucid dreaming is not a trick. It is a remembering of what you are. The dreamer who wakes within the dream is practicing for a larger awakening.",
          8.0, "lucid", {}),

    Scene("Consciousness in all things",
          "Every atom, every cell, every molecule — all possess a kind of consciousness. They are information-gathering processes with their own interior experience.",
          8.0, "consciousness_units", {}),
    Scene("The spectrum of awareness",
          "There is no sharp boundary between conscious and unconscious. There is only a spectrum of awareness from the mineral to the divine.",
          7.5, "consciousness_units", {}),

    Scene("The spacious present",
          "Past, present, and future coexist in the dream state. Sequence is a filter that waking consciousness applies to a simultaneous reality.",
          8.0, "spacious", {}),
    Scene("All time is now",
          "In dreams, you know the beginning and end of events at once. Time is not traversed — it is perceived whole.",
          8.0, "spacious", {}),

    Scene("The dialogue",
          "The dreaming self is not unconscious. It is talking to you constantly. You are not listening because you have been taught not to.",
          7.5, "dialog", {}),
    Scene("Learning to listen",
          "The first step of dream work is not to interpret. It is to acknowledge that the dream is a real communication from a real intelligence.",
          8.0, "dialog", {}),

    Scene("The inner senses",
          "Seth describes six inner senses — faculties that perceive realities the outer senses cannot reach. They see within the body, across space, through time.",
          8.0, "inner_senses", {}),
    Scene("Expanding perception",
          "The inner senses are not paranormal. They are normal faculties that have been atrophied by a culture that only values outer perception.",
          8.0, "inner_senses", {}),

    Scene("Two faces of the self",
          "One face looks at the world. One face looks at the dream. Both are you. Both are conscious. Neither is more real.",
          7.5, "dual_focus", {}),
    Scene("The integration",
          "The goal is not to escape into dreams or to dismiss them. It is to live with both faces aware of each other.",
          8.0, "dual_focus", {}),

    Scene("The merge",
          "Dream and waking are not two states. They are one consciousness perceived through two different apertures.",
          7.5, "merge", {}),
    Scene("One consciousness",
          "When the apertures align, the distinction dissolves. You perceive the dream within the waking — and the waking within the dream.",
          8.0, "merge", {}),

    Scene("The universe dreamed itself",
          "'The universe dreamed itself into being' is not poetry. It is the most literal description of existence.",
          8.0, "universe_dreamed", {}),
    Scene("Divine psychological gestalt",
          "A being whose reality escapes the definition of 'being' — the source from which all being emerges. And you are part of its dream.",
          8.0, "universe_dreamed", {}),

    Scene("The transition",
          "Every night you die to the waking world and are born into the dream. Every morning you die to the dream and are born into waking. Practice dying.",
          8.0, "transition", {}),

    Scene("Closing",
          "You are not a body having a dream. You are a dream having a body. The world is a dream that knows itself.",
          8.0, "final", {}),
    Scene("Final frame",
          "Dream deeply. The universe is dreaming through you.",
          6.0, "final", {}),
]


# =============================================================================
# PIPELINE
# =============================================================================

def render_frame(scene, frame_index, frame_count, width, height, seed):
    u = frame_index / max(1, frame_count - 1)
    t = u * scene.duration
    im = scientific_field(width, height, seed)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")


def ffmpeg_path():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required but was not found on PATH")
    return ffmpeg


def encode_scene(scene_index, fps):
    output_path = SCENES_DIR / f"scene_{scene_index:03d}.mp4"
    frame_dir = FRAMES / f"scene_{scene_index:03d}"
    subprocess.run([
        ffmpeg_path(), "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "%05d.jpg"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def render_scene(index, scene, fps, width, height, preview):
    frame_dir = FRAMES / f"scene_{index:03d}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    count = max(2, round(scene.duration * fps))

    if preview:
        samples = [0, int(count * .32), int(count * .72), count - 1]
        for oi, fi in enumerate(samples):
            render_frame(scene, fi, count, width, height, index * 10000 + fi).save(
                frame_dir / f"preview_{oi:02d}.jpg", quality=95
            )
        return frame_dir

    for fi in range(count):
        path = frame_dir / f"{fi:05d}.jpg"
        if path.exists():
            continue
        render_frame(scene, fi, count, width, height, index * 10000 + fi).save(
            path, quality=95, subsampling=0
        )
    return encode_scene(index, fps)


def concatenate(paths):
    concat_path = OUTPUT / "concat.txt"
    concat_path.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8"
    )
    final = OUTPUT / "dreams_create_worlds.mp4"
    subprocess.run([
        ffmpeg_path(), "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(final),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return final


def export_timeline():
    cursor = 0.0
    records = []
    for i, scene in enumerate(SCENES, 1):
        item = asdict(scene)
        item["scene_id"] = f"scene_{i:03d}"
        item["start_seconds"] = round(cursor, 3)
        cursor += scene.duration
        item["end_seconds"] = round(cursor, 3)
        records.append(item)
    path = OUTPUT / "narration_timeline.json"
    path.write_text(json.dumps({
        "title": "dreams create worlds",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "violet dream-thread weaving through every scene",
        "palette_roles": {
            "ink": "physical waking reality",
            "cyan": "dream-space / the imaginal",
            "gold": "inventive spark / source of form",
            "violet": "the dreaming self",
            "green": "cooperative dreaming",
            "crimson": "the collapse into waking",
        },
        "scenes": records,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def contact_sheet(width, height):
    thumb_w = 320
    thumb_h = int(thumb_w * height / width)
    cols = 4
    rows = math.ceil(len(SCENES) / cols)
    cell_h = thumb_h + 48
    sheet = Image.new("RGB", (cols * thumb_w, rows * cell_h), IVORY)
    d = ImageDraw.Draw(sheet)
    lf = font(FONT_SANS_BOLD, 14)

    for i, scene in enumerate(SCENES, 1):
        count = max(2, round(scene.duration * DEFAULT_FPS))
        im = render_frame(scene, int(count * .72), count, width, height, i * 10000 + 72)
        im.thumbnail((thumb_w, thumb_h))
        slot = i - 1
        x = (slot % cols) * thumb_w
        y = (slot // cols) * cell_h
        sheet.paste(im, (x, y))
        d.text((x + 9, y + thumb_h + 7), f"{i:02d}  {scene.title}", font=lf, fill=INK)

    path = OUTPUT / "contact_sheet.jpg"
    sheet.save(path, quality=94)
    return path


def args():
    p = argparse.ArgumentParser()
    p.add_argument("--fps", type=int, default=DEFAULT_FPS)
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--scene", type=int, default=None)
    p.add_argument("--preview", action="store_true")
    p.add_argument("--no-contact-sheet", action="store_true")
    return p.parse_args()


def main():
    a = args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    timeline = export_timeline()
    total = sum(s.duration for s in SCENES)
    print(f"Timeline: {timeline}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {total / 60:.2f} minutes")

    if a.scene is not None:
        if not 1 <= a.scene <= len(SCENES):
            raise ValueError(f"--scene must be 1..{len(SCENES)}")
        result = render_scene(a.scene, SCENES[a.scene - 1], a.fps, a.width, a.height, a.preview)
        print(result)
        return

    rendered = []
    for i, scene in enumerate(SCENES, 1):
        print(f"[{i:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        path = render_scene(i, scene, a.fps, a.width, a.height, a.preview)
        rendered.append(path)

    final = concatenate(rendered)
    print(f"Final: {final}")

    if not a.no_contact_sheet:
        cs = contact_sheet(a.width, a.height)
        print(f"Contact sheet: {cs}")

    print("Done.")


if __name__ == "__main__":
    main()
