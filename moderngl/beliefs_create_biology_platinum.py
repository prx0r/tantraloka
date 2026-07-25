#!/usr/bin/env python3
"""
YOUR BELIEFS CREATE YOUR BIOLOGY
Platinum procedural visual essay — psychoneuroimmunology and consciousness.

Adapted from:
Seth Material (Jane Roberts, 1963-1982)
The Nature of the Psyche (1979)
Dreams, "Evolution", and Value Fulfillment (1986)

HOUSE CONTRACT
--------------
• 5–10 seconds per shot.
• Every shot performs the spoken claim as a visible transformation.
• Clean ivory scientific field; no lined manuscript background.
• Genuinely animated processes, not static labelled slides.
• Sparse typography used only as conceptual seals.
• Distinct visual vocabulary from all previous films.

PALETTE ROLES
-------------
INK     conventional biology / materialism / the "given" world
CYAN    cellular consciousness / molecular cooperation
GOLD    belief / intent / the shaping principle
CRIMSON illness / blockage / the signal of dimming
GREEN   healing / value fulfillment / cellular faith
VIOLET  the psyche / the dreaming self / inner reality
PAPER   the body as field / the subtle form

CONTINUITY OBJECT
-----------------
A gold particle of intent (a "belief seed") drifts through every scene —
as a thought, a cellular signal, a genetic expression, a healing pulse.
It always moves from consciousness toward matter, never the reverse.

OUTPUT
------
output_beliefs_create_biology/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  beliefs_create_biology.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python beliefs_create_biology_platinum.py
python beliefs_create_biology_platinum.py --preview
python beliefs_create_biology_platinum.py --scene 12
python beliefs_create_biology_platinum.py --fps 12 --width 1920 --height 1080
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


# =============================================================================
# CONFIG
# =============================================================================

ROOT = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_beliefs_create_biology")
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


# =============================================================================
# HELPERS
# =============================================================================

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t)


def mix(a, b, t):
    t = clamp(t)
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a))
    return q * q * (3 - 2 * q)


def ease(t: float) -> float:
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def pulse(t: float, speed: float = 1.0, phase: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin(math.tau * (speed * t + phase))


def font(path: str, size: int):
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def scientific_field(w: int, h: int, seed: int) -> Image.Image:
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
    d.rounded_rectangle(
        (26, 26, w - 26, h - 26),
        radius=18,
        outline=(*INK, 48),
        width=2,
    )
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
    gd.ellipse((x - r, y - r, x + r, y + r), fill=(*color, alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    core = layer(im.size)
    ImageDraw.Draw(core).ellipse(
        (x - r * .38, y - r * .38, x + r * .38, y + r * .38),
        fill=(*mix(color, WHITE, .35), min(255, alpha + 55)),
    )
    im.alpha_composite(core)


def glow_line(im, points, color, width=4, alpha=210, blur=12):
    if len(points) < 2:
        return
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.line(points, fill=(*color, alpha), width=width * 3, joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).line(
        points,
        fill=(*mix(color, WHITE, .08), min(255, alpha + 25)),
        width=width,
        joint="curve",
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


def arrow(draw, a, b, color=INK, width=3, head=10):
    draw.line((*a, *b), fill=color, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        p = (
            b[0] - math.cos(ang + s * .53) * head,
            b[1] - math.sin(ang + s * .53) * head,
        )
        draw.line((*b, *p), fill=color, width=width)


def spiral(cx, cy, radius, turns, phase=0.0, samples=120):
    pts = []
    for i in range(samples):
        q = i / (samples - 1)
        a = q * turns * math.tau + phase
        r = radius * q * 0.8
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


# =============================================================================
# DOMAIN DRAWING FUNCTIONS
# =============================================================================

def draw_pill(im, cx, cy, size, alpha=255):
    d = ImageDraw.Draw(im)
    w = size * 0.6
    h = size * 0.25
    d.rounded_rectangle((cx - w, cy - h, cx + w, cy + h), radius=6,
                        fill=(*PALE_GOLD, alpha), outline=(*GOLD, min(255, alpha)), width=2)
    d.line((cx - w * 0.6, cy - h, cx - w * 0.6, cy + h),
           fill=(*GOLD, min(200, alpha)), width=3)


def draw_brain_fmri(im, cx, cy, size, active_regions=None, phase=0.0):
    d = ImageDraw.Draw(im)
    r = size * 0.5
    d.ellipse((cx - r, cy - r * 1.1, cx + r, cy + r * 1.1),
              fill=(*PALE_SILVER, 180), outline=(*INK, 160), width=3)
    d.ellipse((cx - r * 0.6, cy - r * 0.55, cx + r * 0.6, cy + r * 0.55),
              fill=(*PALE_SILVER, 100), outline=(*INK, 80), width=2)
    if active_regions:
        colors = [GOLD, CYAN, GREEN, VIOLET]
        for i, (x, y) in enumerate(active_regions):
            act = pulse(phase + i * 0.3)
            glow_circle(im, cx + x * r, cy + y * r * 1.1,
                        int(8 + 6 * act), colors[i % 4], int(120 + 80 * act), 8)


def draw_cell(im, x, y, r, nucleus=True, active=False, phase=0.0):
    d = ImageDraw.Draw(im)
    d.ellipse((x - r, y - r, x + r, y + r),
              fill=(*PALE_GREEN, 200), outline=(*GREEN, 160), width=2)
    if nucleus:
        nr = r * 0.4
        d.ellipse((x - nr, y - nr, x + nr, y + nr),
                  fill=(*(PALE_GOLD if active else PALE_CYAN), 220),
                  outline=(*(GOLD if active else DEEP_CYAN), 180), width=2)
        if active:
            for a in (0, math.tau / 3, math.tau * 2 / 3):
                dx = math.cos(a + phase) * nr * 0.8
                dy = math.sin(a + phase) * nr * 0.8
                d.line((x, y, x + dx, y + dy), fill=(*GOLD, 120), width=1)


def draw_cell_network(im, nodes, edges, reveal=1.0, phase=0.0, active_idx=None):
    d = ImageDraw.Draw(im)
    for ei, (a, b) in enumerate(edges):
        q = clamp(reveal * len(edges) - ei)
        if q <= 0:
            continue
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        d.line((x1, y1, x2, y2), fill=(*CYAN, int(80 + 60 * q)), width=2)
    for i, (x, y) in enumerate(nodes):
        q = clamp(reveal * len(nodes) - i)
        if q <= 0:
            continue
        active = active_idx is not None and i in active_idx
        col = GOLD if active else PALE_CYAN
        out = GOLD if active else DEEP_CYAN
        r = 10 + 2 * pulse(phase + i * 0.2)
        d.ellipse((x - r, y - r, x + r, y + r),
                  fill=(*col, int(220 * q)),
                  outline=(*out, int(170 * q)), width=2)
        if active:
            for a in range(4):
                dx = math.cos(a * math.tau / 4 + phase) * r * 1.8
                dy = math.sin(a * math.tau / 4 + phase) * r * 1.8
                d.line((x, y, x + dx, y + dy), fill=(*GOLD, 150), width=2)


def draw_dna(im, cx, cy, length, width, phase=0.0, reveal=1.0):
    d = ImageDraw.Draw(im)
    steps = 40
    left_strand = []
    right_strand = []
    for i in range(steps):
        q = i / (steps - 1)
        x = cx - length / 2 + q * length
        offset = math.sin(q * math.tau * 4 + phase) * width * 0.5
        left_strand.append((x, cy + offset - width * 0.15))
        right_strand.append((x, cy + offset + width * 0.15))

    visible = int(steps * reveal)
    if visible > 1:
        d.line(left_strand[:visible], fill=(*CYAN, 200), width=3)
        d.line(right_strand[:visible], fill=(*CYAN, 200), width=3)
        # rungs
        for i in range(0, visible, 3):
            a = left_strand[i]
            b = right_strand[i]
            d.line((a[0], a[1], b[0], b[1]), fill=(*GOLD, 120), width=2)
        # signal
        if reveal > 0.8:
            sig_y = cy + math.sin(phase * 2) * width * 0.6
            glow_circle(im, cx + length * 0.3, sig_y, 8, GOLD, 160, 8)


def draw_field_wave(im, cx, cy, radius, phase=0.0, color=VIOLET):
    d = ImageDraw.Draw(im)
    for r in range(10, int(radius), 12):
        alpha = int(120 * (1 - r / radius) * (0.6 + 0.4 * pulse(phase + r * 0.01)))
        d.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 0.6),
                  outline=(*color, alpha), width=2)


def draw_belief_particle(im, x, y, phase, alpha=255):
    r = 5 + 3 * pulse(phase, 1.3)
    glow_circle(im, x, y, r, GOLD, min(200, alpha), 8)
    core = layer(im.size)
    d = ImageDraw.Draw(core)
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(*WHITE, min(200, alpha)))
    im.alpha_composite(core)


# =============================================================================
# VISUAL FUNCTIONS
# =============================================================================

def vis_conventional_view(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    d.ellipse((cx - 50, cy - 55, cx + 50, cy + 55),
              fill=(*PALE_SILVER, 180), outline=(*INK, 160), width=3)
    centered(d, (cx, cy - 15), "BRAIN",
             font(FONT_SANS_BOLD, int(h * 0.030)), INK)
    centered(d, (cx, cy + 20), "generates consciousness",
             font(FONT_SANS, int(h * 0.019)), SOFT_INK)

    arrow(d, (cx, cy + 70), (cx, cy + 110), INK, 2, 6)
    d.rectangle((cx - 35, cy + 115, cx + 35, cy + 175),
                fill=(*PALE_SILVER, 150), outline=(*INK, 120), width=3)
    centered(d, (cx, cy + 145), "MIND",
             font(FONT_SANS_BOLD, int(h * 0.025)), SOFT_INK)

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        d.rectangle((w * 0.12, h * 0.08, w * 0.88, h * 0.22),
                    fill=(*mix(WHITE, CRIMSON, 0.06), int(180 * q)),
                    outline=(*CRIMSON, int(150 * q)), width=2)
        centered(d, (w * 0.50, h * 0.15),
                 "MATTER → MIND: THE CONVENTIONAL STORY",
                 font(FONT_SANS_BOLD, int(h * 0.022)), CRIMSON)

    seal(im, "THE MATERIALIST FRAMEWORK",
         "biology produces consciousness — or so we assume", INK)


def vis_placebo_phenomenon(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.38
    reveal = ease(u)

    draw_pill(im, cx, cy - 30, 40, int(200 * reveal))
    if reveal > 0.2:
        descent = smoothstep(0.2, 0.6, u)
        pill_y = lerp(cy - 30, cy + 30, descent)
        draw_pill(im, cx, pill_y, 40, int(200 * reveal))

    if reveal > 0.4:
        brain_regions = [(0.2, -0.3), (-0.1, 0.4), (0.3, 0.2), (-0.3, -0.1)]
        draw_brain_fmri(im, cx, cy + 70, 70, brain_regions, t)

    if reveal > 0.7:
        centered(d, (cx, h * 0.78),
                 "A SUGAR PILL STOPS PAIN",
                 font(FONT_SANS_BOLD, int(h * 0.022)), GOLD)
        centered(d, (cx, h * 0.84),
                 "the belief — not the chemistry — is the active ingredient",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "THE PLACEBO EFFECT",
         "expectation changes physiology — measurably, repeatably", GOLD)


def vis_placebo_growing(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    d.line((w * 0.12, cy + 100, w * 0.88, cy + 100),
           fill=(*INK, 160), width=2)
    d.line((w * 0.12, cy - 60, w * 0.12, cy + 100),
           fill=(*INK, 160), width=2)

    years = [1990, 2000, 2010, 2020]
    for i, yr in enumerate(years):
        x = lerp(w * 0.15, w * 0.85, i / 3)
        d.text((x - 10, cy + 105), str(yr), font=font(FONT_SANS, int(h * 0.016)), fill=SOFT_INK)

    line_pts = []
    for i in range(40):
        q = i / 39
        x = lerp(w * 0.15, w * 0.85, q)
        baseline = 0.15 + 0.65 * q ** 0.7
        y = cy + 100 - baseline * 160
        line_pts.append((x, y))

    visible = int(reveal * len(line_pts))
    if visible > 1:
        d.line(line_pts[:visible], fill=(*GOLD, 200), width=4)

    if reveal > 0.6:
        arrow(d, (w * 0.75, cy - 40), (w * 0.75, cy + 10), CRIMSON, 2, 6)
        centered(d, (w * 0.75, cy - 50),
                 "PLACEBO EFFECT\n65% STRONGER IN 2023",
                 font(FONT_SANS_BOLD, int(h * 0.018)), CRIMSON)

    seal(im, "THE PLACEBO IS ACCELERATING",
         "we are learning to heal ourselves — and the effect compounds", GOLD)


def vis_seth_claim(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # abstract channeling scene
    n_lines = int(8 * reveal)
    for i in range(n_lines):
        q = i / max(1, n_lines - 1)
        x = lerp(w * 0.15, w * 0.85, q)
        y = cy + math.sin(q * math.tau * 3 + t * 0.5) * h * 0.05
        d.line((x - 40, y, x + 40, y),
               fill=(*VIOLET, int(120 + 80 * pulse(t * 0.4 + i * 0.5))), width=3)

    if reveal > 0.3:
        words = [
            "DESIRE", "LOVE", "INTENT", "BELIEF", "PURPOSE"
        ]
        for i, word in enumerate(words):
            q = clamp((reveal - 0.3) * len(words) - i)
            if q <= 0:
                continue
            x = lerp(w * 0.15, w * 0.85, i / (len(words) - 1))
            y = cy - h * 0.02 + math.sin(t * 0.3 + i) * 8
            glow_circle(im, x, y, 6, GOLD, int(150 * q), 6)
            centered(d, (x, y + 22), word,
                     font(FONT_SANS_BOLD, int(h * 0.020)),
                     (*GOLD, int(220 * q)))

    if reveal > 0.65:
        centered(d, (cx, cy + h * 0.08),
                 "these form the experience of",
                 font(FONT_SANS, int(h * 0.019)), SOFT_INK)
        glow_circle(im, cx, cy + h * 0.14, 18, GOLD, 140, 12)
        centered(d, (cx, cy + h * 0.14),
                 "YOUR BODY",
                 font(FONT_SERIF_BOLD, int(h * 0.032)), GOLD)

    seal(im, "SETH (1975)",
         "desire, love, intent, belief and purpose — these form the experience of your body", VIOLET)


def vis_belief_shapes_cell(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    belief_arrives = smoothstep(0.1, 0.4, u)
    belief_enters = smoothstep(0.35, 0.65, u)
    cell_changes = smoothstep(0.60, 0.95, u)

    draw_cell(im, cx, cy, 40, True, cell_changes > 0.3, t)

    if belief_arrives > 0:
        pt_x = cx - 80 + belief_arrives * 60
        pt_y = cy - 30
        draw_belief_particle(im, pt_x, pt_y, t * 1.5, int(200 * belief_arrives))

    if belief_enters > 0:
        path = [(cx - 20, cy - 30), (cx - 10, cy - 15), (cx, cy)]
        visible = int(belief_enters * len(path))
        if visible > 1:
            d.line(path[:visible], fill=(*GOLD, 200), width=3)
        if belief_enters > 0.8:
            glow_circle(im, cx, cy, 8, GOLD, 200, 6)

    if cell_changes > 0.3:
        nr = 16 * (0.5 + 0.5 * cell_changes)
        d.ellipse((cx - nr, cy - nr, cx + nr, cy + nr),
                  fill=(*PALE_GOLD, int(150 * cell_changes)),
                  outline=(*GOLD, int(200 * cell_changes)), width=3)

    seal(im, "BELIEF ENTERS THE CELL",
         "a thought is not separate from biology — it becomes cellular structure", GOLD)


def vis_cells_have_beliefs(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    rng = random.Random(42)
    nodes = []
    for i in range(9):
        x = lerp(w * 0.18, w * 0.82, i % 3 / 2)
        y = lerp(h * 0.22, h * 0.62, i // 3 / 2)
        nodes.append((x + rng.uniform(-8, 8), y + rng.uniform(-8, 8)))

    edges = [(i, i + 1) for i in range(0, 8, 1) if (i + 1) % 3 != 0]
    edges += [(i, i + 3) for i in range(6)]

    active = [int(t * 2 + i) % 9 for i in range(3)] if reveal > 0.3 else None
    draw_cell_network(im, nodes, edges, reveal, t, active)

    if reveal > 0.6:
        quote = "EACH CELL BELIEVES IN A BETTER TOMORROW"
        centered(d, (cx, h * 0.76),
                 quote,
                 font(FONT_SANS_BOLD, int(h * 0.020)), GREEN)

    seal(im, "CELLULAR FAITH",
         "each cell contains a built-in belief in its own fulfillment", GREEN)


def val_fulfillment(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(30):
        q = i / 29
        x = lerp(w * 0.10, w * 0.90, q)
        y = cy + math.sin(q * math.tau * 3 + t * 0.3) * h * 0.08
        alpha = int(150 * reveal * (0.3 + 0.7 * pulse(t * 0.2 + q * 2)))
        d.ellipse((x - 4, y - 4, x + 4, y + 4),
                  fill=(*mix(CYAN, GOLD, q), alpha))

    if reveal > 0.4:
        for i in range(5):
            q = clamp((reveal - 0.4) * 10 - i)
            if q <= 0:
                continue
            labels = ["JOY", "GROWTH", "COOPERATION", "CREATIVITY", "HEALING"]
            x = lerp(w * 0.20, w * 0.80, i / 4)
            y = cy + h * 0.06 + i * 3
            d.text((x - len(labels[i]) * 4, y), labels[i],
                   font=font(FONT_SANS_BOLD, int(h * 0.018)),
                   fill=(*GREEN, int(200 * q)))

    seal(im, "VALUE FULFILLMENT",
         "life seeks not just to continue — to enhance the quality of life itself", GREEN)


def vis_molecular_cooperation(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    n_particles = 80
    rng = random.Random(73)
    centers = []
    for i in range(n_particles):
        a = rng.uniform(0, math.tau)
        r = (rng.random() ** 0.6) * min(w, h) * 0.22
        centers.append((
            cx + math.cos(a) * r * 1.6,
            cy + math.sin(a) * r,
            rng.uniform(2, 5),
        ))

    visible = int(reveal * n_particles)
    for i in range(visible):
        x, y, s = centers[i]
        col = CYAN if i % 3 != 0 else GOLD
        d.ellipse((x - s, y - s, x + s, y + s),
                  fill=(*mix(WHITE, col, 0.2), 200),
                  outline=(*col, 140), width=1)

    if reveal > 0.6:
        connections = [(0, 1), (1, 2), (3, 4), (5, 6), (7, 8)]
        for a, b in connections:
            x1, y1, _ = centers[a]
            x2, y2, _ = centers[b]
            d.line((x1, y1, x2, y2), fill=(*GOLD, 80), width=2)

    seal(im, "MOLECULAR AND CELLULAR COOPERATION",
         "the body exists as a unit because of inner relationships of a cooperative nature", CYAN)


def vis_dna_antenna(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    draw_dna(im, cx, cy, w * 0.50, h * 0.08, t * 0.5, reveal)

    if reveal > 0.5:
        signal = smoothstep(0.5, 0.85, u)
        for i in range(5):
            a = i * math.tau / 5 + t * 0.3
            r = signal * w * 0.20
            x = cx + math.cos(a) * w * 0.25
            y = cy + math.sin(a) * h * 0.06
            d.line((cx, cy, x, y), fill=(*GOLD, int(100 * signal)), width=2)
            if signal > 0.7:
                glow_circle(im, x, y, 4, GOLD, int(120 * signal), 4)

    if reveal > 0.7:
        centered(d, (cx, h * 0.76),
                 "DNA: CONDUCTOR OR ANTENNA?",
                 font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)

    seal(im, "THE LIVING INSTRUMENT",
         "DNA conducts electricity — could it also receive information?", CYAN)


def vis_consciousness_field(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    draw_field_wave(im, cx, cy, w * 0.48, t * 0.3, VIOLET)

    if reveal > 0.3:
        for i in range(6):
            a = i * math.tau / 6 + t * 0.1
            r = w * 0.25 + 15 * math.sin(t * 0.5 + i)
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * 0.5
            draw_belief_particle(im, int(x), int(y), t + i, int(150 * reveal))

    if reveal > 0.5:
        d.ellipse((cx - 30, cy - 40, cx + 30, cy + 40),
                  fill=(*PALE_GOLD, int(100 * (reveal - 0.5) * 2)),
                  outline=(*GOLD, int(150 * (reveal - 0.5) * 2)), width=3)
        centered(d, (cx, cy),
                 "SELF",
                 font(FONT_SERIF_BOLD, int(h * 0.040)),
                 (*GOLD, int(200 * (reveal - 0.5) * 2)))

    if reveal > 0.7:
        centered(d, (cx, h * 0.76),
                 "CONSCIOUSNESS IS NOT IN THE BODY",
                 font(FONT_SANS_BOLD, int(h * 0.020)), VIOLET)
        centered(d, (cx, h * 0.81),
                 "THE BODY IS IN CONSCIOUSNESS",
                 font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)

    seal(im, "THE FIELD OF AWARENESS",
         "consciousness contains the body — not the other way around", VIOLET)


def vis_illness_as_communication(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    distress = smoothstep(0.1, 0.45, u)
    resolution = smoothstep(0.55, 0.90, u)

    draw_cell(im, cx, cy, 35, True, False, t)

    if distress > 0.1 and resolution < 0.6:
        # fracturing
        glow = layer(im.size)
        gd = ImageDraw.Draw(glow)
        r = 30 + 10 * distress
        gd.ellipse((cx - r, cy - r, cx + r, cy + r),
                    fill=(*CRIMSON, int(70 * distress * (1 - resolution))))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)))
        for a in range(4):
            x = cx + math.cos(a * math.tau / 4 + t * 0.3) * 30
            y = cy + math.sin(a * math.tau / 4 + t * 0.3) * 30
            d.line((cx, cy, x, y), fill=(*CRIMSON, int(150 * distress)), width=3)

    if resolution > 0.2:
        for i in range(5):
            a = i * math.tau / 5 + t * 0.2
            x = cx + math.cos(a) * (35 + 15 * resolution)
            y = cy + math.sin(a) * (35 + 15 * resolution)
            d.line((cx, cy, x, y), fill=(*GREEN, int(120 * resolution)), width=2)
            draw_belief_particle(im, int(x), int(y), t + i, int(100 * resolution))

    state = "ILLNESS AS SIGNAL" if distress > 0.3 and resolution < 0.5 else "RESTORED COHERENCE"
    col = CRIMSON if distress > 0.3 and resolution < 0.5 else GREEN
    seal(im, state,
         "the body has no language but health and its disturbance", col)


def vis_dreams_source(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # dream space
    rng = random.Random(55)
    for i in range(50):
        q = clamp(reveal * 50 - i)
        if q <= 0:
            continue
        x = rng.uniform(w * 0.08, w * 0.92)
        y = rng.uniform(h * 0.08, h * 0.72)
        a = int(180 * q * (0.5 + 0.5 * pulse(t * 0.3 + i)))
        d.ellipse((x - 3, y - 3, x + 3, y + 3),
                  fill=(*VIOLET, a))

    if reveal > 0.4:
        # event formation
        event_x = cx + math.sin(t * 0.4) * w * 0.10
        event_y = cy + math.cos(t * 0.3) * h * 0.05
        glow_circle(im, event_x, event_y, 12, GOLD, 160, 10)
        arrow(d, (event_x, event_y), (event_x + 40, event_y - 20), GOLD, 2, 6)

    if reveal > 0.6:
        centered(d, (cx, h * 0.76),
                 "DREAMS ARE THE SOURCE OF PHYSICAL EVENTS",
                 font(FONT_SANS_BOLD, int(h * 0.019)), VIOLET)

    seal(im, "THE DREAMING GROUND",
         "all physical events begin as nonphysical patterns in the dreaming self", VIOLET)


def vis_psyche_gestalt(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    vertices = [
        (cx, cy - h * 0.12),
        (cx - w * 0.12, cy + h * 0.08),
        (cx + w * 0.12, cy + h * 0.08),
    ]

    for i, (x, y) in enumerate(vertices):
        col = [GOLD, CYAN, VIOLET][i]
        d.ellipse((x - 12, y - 12, x + 12, y + 12),
                  fill=(*mix(WHITE, col, 0.15), int(200 * reveal)),
                  outline=(*col, int(180 * reveal)), width=3)

    for i in range(3):
        a, b = vertices[i], vertices[(i + 1) % 3]
        d.line((a[0], a[1], b[0], b[1]),
               fill=(*GOLD, int(100 * reveal)), width=3)

    if reveal > 0.5:
        cx2, cy2 = cx, cy
        d.ellipse((cx2 - 8, cy2 - 8, cx2 + 8, cy2 + 8),
                  fill=(*PALE_GOLD, int(200 * (reveal - 0.5) * 2)),
                  outline=(*GOLD, int(180 * (reveal - 0.5) * 2)), width=3)
        glow_circle(im, cx2, cy2, 20, GOLD, int(60 * (reveal - 0.5) * 2), 14)

    seal(im, "THE PSYCHE IS A GESTALT",
         "an ever-forming state of being — you create it and it creates you", VIOLET)


def vis_free_will_primitive(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # sphere of possibilities
    glow_circle(im, cx, cy, 60, GOLD, 60, 30)
    d.ellipse((cx - 60, cy - 60, cx + 60, cy + 60),
              outline=(*GOLD, 120), width=2)

    if reveal > 0.2:
        n_rays = int(16 * reveal)
        for i in range(n_rays):
            a = i * math.tau / max(1, n_rays) + t * 0.1
            inner_r = 65 + 10 * pulse(t * 0.5 + i)
            outer_r = 90 + 20 * math.sin(a * 3 + t)
            x1 = cx + math.cos(a) * inner_r
            y1 = cy + math.sin(a) * inner_r * 0.7
            x2 = cx + math.cos(a) * outer_r
            y2 = cy + math.sin(a) * outer_r * 0.7
            d.line((x1, y1, x2, y2), fill=(*GOLD, int(100 + 80 * pulse(t * 0.4 + i))), width=2)

    if reveal > 0.5:
        centered(d, (cx, h * 0.76),
                 "THE FIRST DISTORTION: FREE WILL",
                 font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)
        centered(d, (cx, h * 0.81),
                 "infinity became aware — and chose to explore many-ness",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "FREEDOM BEFORE CAUSALITY",
         "the universe begins with choice, not law — free will is the primitive", GOLD)


def vis_vikalpa_samskara(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # consciousness as clear field
    for i in range(20):
        a = i * math.tau / 20
        r = w * 0.30
        x = cx + math.cos(a) * r + 8 * math.sin(t + i)
        y = cy + math.sin(a) * r * 0.5 + 8 * math.cos(t * 0.7 + i)
        alpha = int(80 * (0.5 + 0.5 * pulse(t * 0.2 + i)))
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(*VIOLET, alpha))

    if reveal > 0.2:
        impression = smoothstep(0.2, 0.6, u)
        for i in range(5):
            q = clamp(impression * 8 - i)
            if q <= 0:
                continue
            x = lerp(cx - w * 0.15, cx + w * 0.15, i / 4)
            y = cy + math.sin(i * 1.5 + t * 0.3) * h * 0.03
            d.rounded_rectangle((x - 20, y - 12, x + 20, y + 12),
                                radius=5,
                                fill=(*mix(WHITE, GOLD, 0.1), int(150 * q)),
                                outline=(*GOLD, int(120 * q)), width=2)

    if reveal > 0.7:
        centered(d, (cx, h * 0.76),
                 "VIKALPA-SAMSKARA",
                 font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)
        centered(d, (cx, h * 0.81),
                 "conceptual constructions leave impressions that shape form",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "IMPRESSIONS ON CONSCIOUSNESS",
         "every thought is a seed planted in the field of the body", GOLD)


def vis_healing_parity(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    body_cycle = smoothstep(0.1, 0.5, u)
    dream_cycle = smoothstep(0.5, 0.9, u)

    if body_cycle > 0:
        d.ellipse((cx - 50, cy - 60, cx + 50, cy + 60),
                  fill=(*PALE_GREEN, int(100 * body_cycle)),
                  outline=(*GREEN, int(150 * body_cycle)), width=3)

    if body_cycle > 0.3:
        for i in range(6):
            a = i * math.tau / 6 + t * 0.2
            r = 60 + 10 * math.sin(t + i)
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * 0.7
            draw_belief_particle(im, int(x), int(y), t + i, int(120 * body_cycle))

    if dream_cycle > 0:
        d.ellipse((cx - 60, cy - 55, cx + 60, cy + 55),
                  outline=(*VIOLET, int(150 * dream_cycle)), width=3)
        centered(d, (cx, cy),
                 "HEALING",
                 font(FONT_SERIF_BOLD, int(h * 0.035)),
                 (*GREEN, int(200 * dream_cycle)))

    if dream_cycle > 0.5:
        centered(d, (cx, h * 0.76),
                 "THE BODY HEALS ITSELF IN SLEEP — IN DREAMS",
                 font(FONT_SANS_BOLD, int(h * 0.019)), GREEN)

    seal(im, "THE NOCTURNAL PHARMACY",
         "at certain levels in the dream state, each portion of consciousness contributes to the health of all", GREEN)


def vis_consciousness_before_matter(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # field
    for r in range(10, int(w * 0.35), 15):
        a = int(100 * (1 - r / (w * 0.35)) * reveal)
        d.ellipse((cx - r, cy - r * 0.5, cx + r, cy + r * 0.5),
                  outline=(*VIOLET, a), width=2)

    if reveal > 0.3:
        form = smoothstep(0.3, 0.75, u)
        pts = []
        for i in range(30):
            q = i / 29
            angle = q * math.tau + t * 0.15
            r = w * 0.15 * q * form
            pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r * 0.5))
        if len(pts) > 2:
            d.line(pts, fill=(*GOLD, int(150 * form)), width=3)

    if reveal > 0.6:
        centered(d, (cx, h * 0.76),
                 "THERE WAS CONSCIOUSNESS BEFORE THERE WAS MATTER",
                 font(FONT_SANS_BOLD, int(h * 0.019)), VIOLET)
        centered(d, (cx, h * 0.81),
                 "it is an error to separate matter from consciousness",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "PRIMACY OF CONSCIOUSNESS",
         "consciousness materializes itself as matter — not the reverse", VIOLET)


def vis_final_synthesis(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    gather = smoothstep(0.1, 0.5, u)
    resolve = smoothstep(0.5, 0.95, u)

    # particles gather
    n_particles = 30
    for i in range(n_particles):
        phase = (t * 0.3 + i / n_particles) % 1
        a = phase * math.tau + i * 0.5
        r = w * 0.20 * gather
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r * 0.4
        col = GOLD if i % 3 < 2 else CYAN
        draw_belief_particle(im, int(x), int(y), t * 0.5 + i, int(180 * gather))

    if gather > 0.5:
        glow_circle(im, cx, cy, 25, GOLD, 80, 20)

    if resolve > 0.2:
        for j in range(8):
            a = j * math.tau / 8 + t * 0.1
            r = 35 + 20 * math.sin(t * 0.4 + j)
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r
            d.line((cx, cy, x, y), fill=(*GOLD, int(70 * resolve)), width=2)

    if resolve > 0.4:
        centered(d, (cx, cy),
                 "YOU ARE",
                 font(FONT_SERIF_BOLD, int(h * 0.055)),
                 (*GOLD, int(180 * resolve)))

    seal(im, "YOUR BELIEFS CREATE YOUR BIOLOGY",
         "consciousness is not a property of the body — the body is a property of consciousness", GOLD)


# =============================================================================
# REGISTRY
# =============================================================================

VISUALS: dict[str, Callable] = {
    "conventional": vis_conventional_view,
    "placebo": vis_placebo_phenomenon,
    "placebo_growing": vis_placebo_growing,
    "seth_claim": vis_seth_claim,
    "belief_cell": vis_belief_shapes_cell,
    "cellular_faith": vis_cells_have_beliefs,
    "value_fulfillment": val_fulfillment,
    "cooperation": vis_molecular_cooperation,
    "dna_antenna": vis_dna_antenna,
    "field": vis_consciousness_field,
    "illness": vis_illness_as_communication,
    "dreams": vis_dreams_source,
    "psyche": vis_psyche_gestalt,
    "free_will": vis_free_will_primitive,
    "vikalpa": vis_vikalpa_samskara,
    "healing": vis_healing_parity,
    "primacy": vis_consciousness_before_matter,
    "final": vis_final_synthesis,
}


# =============================================================================
# SCENES
# =============================================================================

@dataclass
class Scene:
    title: str
    narration: str
    duration: float
    visual: str
    params: dict


SCENES = [
    Scene("The materialist assumption",
          "For centuries, Western science has assumed that matter generates mind — that consciousness is a byproduct of brain activity.",
          7.0, "conventional", {}),
    Scene("The boundary",
          "The brain is the hardware. Consciousness is the software. Or so the story goes.",
          6.0, "conventional", {}),
    Scene("The placebo",
          "A patient receives a sugar pill and is told it is a powerful painkiller. Their pain vanishes.",
          7.0, "placebo", {}),
    Scene("Not imagined",
          "fMRI scans show the brain's pain centers deactivating. The saline did nothing. The belief did everything.",
          7.5, "placebo", {}),
    Scene("Growing stronger",
          "In 2023, a meta-analysis found the placebo effect in pain trials is 65% stronger than it was in the 1990s.",
          7.5, "placebo_growing", {}),
    Scene("Learning to heal",
          "We are not imagining relief more effectively — we are learning to translate belief into biology more efficiently.",
          8.0, "placebo_growing", {}),
    Scene("The forgotten variable",
          "The placebo effect was once dismissed as a statistical nuisance. It is now understood as the mechanism of healing itself.",
          8.0, "placebo_growing", {}),

    Scene("A different starting point",
          "In 1963, a woman named Jane Roberts began channeling a personality named Seth.",
          7.0, "seth_claim", {}),
    Scene("Seth's claim",
          "Seth said: 'Desire, love, intent, belief and purpose — these form the experience of your body and all the events it perceives.'",
          8.0, "seth_claim", {}),
    Scene("Not metaphor",
          "He meant this literally — not metaphorically. Belief is not a commentary on biology. Belief IS the substance of biology.",
          8.0, "seth_claim", {}),

    Scene("Belief enters the cell",
          "How does a thought become a biological change? The same way an instruction becomes a cellular response.",
          7.5, "belief_cell", {}),
    Scene("Gene expression",
          "Beliefs regulate gene expression through epigenetic mechanisms. A thought can silence a gene or activate it.",
          8.0, "belief_cell", {}),
    Scene("The body listens",
          "Every cell of your body is listening to your thoughts. Not metaphorically — biochemically.",
          8.0, "belief_cell", {}),

    Scene("Cellular faith",
          "Seth: 'Each cell contains within itself a belief and an understanding of its own inevitability.'",
          7.5, "cellular_faith", {}),
    Scene("Built-in optimism",
          "Each cell believes in a better tomorrow. This is not poetry — it is the biological impetus of all growth.",
          8.0, "cellular_faith", {}),
    Scene("The network",
          "Cells communicate through gap junctions, ion channels, electromagnetic fields. They weigh probabilities. They make decisions.",
          8.0, "cellular_faith", {}),

    Scene("Value fulfillment",
          "Life seeks not just to continue, but to enhance the quality of life itself. Seth called this value fulfillment.",
          7.5, "value_fulfillment", {}),
    Scene("Cooperative venture",
          "The very existence of one human body speaks of molecular and cellular cooperation that chance alone cannot explain.",
          8.0, "value_fulfillment", {}),

    Scene("Molecular cooperation",
          "Minerals, plants, animals, cells — all participate in a cooperative venture that unites every level of life.",
          7.5, "cooperation", {}),
    Scene("The given gift",
          "Cooperation is not learned — it is given. The gift of life brings along with it the actualization of that cooperation.",
          8.0, "cooperation", {}),

    Scene("DNA as antenna",
          "Cassiopaean: 'DNA acts as a superconductor — a neurotransceiver for thought pattern programs.'",
          7.5, "dna_antenna", {}),
    Scene("Electrical conductor",
          "Research confirms that DNA conducts electricity. Its structure is optimized for charge transport.",
          8.0, "dna_antenna", {}),
    Scene("Signal or noise?",
          "What if DNA is not a blueprint but a receiver — shaped by consciousness to receive consciousness?",
          8.0, "dna_antenna", {}),

    Scene("The field of awareness",
          "Consciousness is not located inside the body. The body is located inside consciousness.",
          7.5, "field", {}),
    Scene("Brain or field?",
          "The brain is not the source of consciousness — it is a reducing valve that filters consciousness into the bandwidth of a single body.",
          8.0, "field", {}),

    Scene("Illness as communication",
          "Seth: 'Illness is often another mode of expression, a means to a desired end.'",
          7.0, "illness", {}),
    Scene("The body's language",
          "The body has no language but health and its disturbance. Illness is the body's way of speaking what the mind cannot.",
          8.0, "illness", {}),

    Scene("The dreaming source",
          "Seth: 'The dream state is the source of all physical events. Physical events are the end products of nonphysical properties.'",
          8.0, "dreams", {}),
    Scene("Events from significances",
          "Events are not built from cause and effect. They are built from significances — from meaning, belief, and intent.",
          8.0, "dreams", {}),

    Scene("The psyche as gestalt",
          "The psyche is not a thing. It is an ever-forming state of being — a gestalt of aware energy.",
          7.5, "psyche", {}),
    Scene("You create it",
          "You create the psyche and it creates you. This is not paradox — it is the structure of subjective life.",
          8.0, "psyche", {}),

    Scene("The first distortion",
          "The Law of One: 'Intelligent infinity invested itself in an exploration of many-ness. The first distortion is free will.'",
          8.0, "free_will", {}),
    Scene("Freedom is primitive",
          "Freedom does not emerge from causality. Causality emerges from freedom. This is the ground of all existence.",
          8.0, "free_will", {}),

    Scene("Impressions on consciousness",
          "Tantraloka: vikalpa-samskara — conceptual constructions leave impressions on consciousness that shape subsequent form.",
          8.0, "vikalpa", {}),
    Scene("Seeds of belief",
          "Every thought is a seed planted in the field of the body. The harvest is health or illness, vitality or decay.",
          8.0, "vikalpa", {}),

    Scene("Healing parity",
          "The body learned to heal itself in sleep — in dreams. At certain levels, every cell contributes to the health of all.",
          7.5, "healing", {}),
    Scene("The nocturnal pharmacy",
          "In the dream state, each portion of consciousness contributes to the health and stability of all other portions.",
          8.0, "healing", {}),

    Scene("Consciousness before matter",
          "Seth: 'There was consciousness before there was matter. It is an error to separate matter from consciousness.'",
          8.0, "primacy", {}),
    Scene("Matter as manifestation",
          "Consciousness materializes itself as matter in physical life. The body does not generate consciousness — it is generated BY consciousness.",
          8.5, "primacy", {}),

    Scene("Closing",
          "Your beliefs create your biology. This is not a slogan. It is the most verified and most ignored finding in medical science.",
          8.0, "final", {}),
    Scene("Final frame",
          "You are not a body having a spiritual experience. You are consciousness having a biological experience.",
          7.0, "final", {}),
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
    final = OUTPUT / "beliefs_create_biology.mp4"
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
        "title": "your beliefs create your biology",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "gold belief-particle moving from consciousness toward matter",
        "palette_roles": {
            "ink": "conventional biology / materialism",
            "cyan": "cellular consciousness / molecular cooperation",
            "gold": "belief / intent / the shaping principle",
            "crimson": "illness / blockage / dimming signal",
            "green": "healing / value fulfillment / cellular faith",
            "violet": "the psyche / the dreaming self / inner reality",
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
