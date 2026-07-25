#!/usr/bin/env python3
"""
THE WAVE — HYPERDIMENSIONAL REALITY IS HERE
Platinum procedural visual essay — Cassiopaean cosmology.

Adapted from:
The Cassiopaean Transcripts (1994-1997)

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
INK     3rd density / physical reality / the program
CYAN    4th density bleedthrough / the Wave
GOLD    STO / service to others / knowledge
CRIMSON STS / service to self / control
VIOLET  6th density / the future self
GREEN   the merge / healing / balance
PAPER   the hyperdimensional substrate / the program code

CONTINUITY OBJECT
-----------------
A wave-crest — a luminous sinusoidal pulse — travels through every
scene. Sometimes it is a quantum collapse, sometimes a density
transition, sometimes the future self merging with the present.

OUTPUT
------
output_wave/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  the_wave.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python the_wave_cassiopaean_platinum.py
python the_wave_cassiopaean_platinum.py --preview
python the_wave_cassiopaean_platinum.py --scene 12
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
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_wave")
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


def arrow(draw, a, b, color=INK, width=3, head=10):
    draw.line((*a, *b), fill=color, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        p = (b[0] - math.cos(ang + s * .53) * head, b[1] - math.sin(ang + s * .53) * head)
        draw.line((*b, *p), fill=color, width=width)


def wave_curve(cx, cy, length, amplitude, phase=0.0, samples=80):
    pts = []
    for i in range(samples):
        q = i / (samples - 1)
        x = cx - length / 2 + q * length
        y = cy + math.sin(q * math.tau + phase) * amplitude
        pts.append((x, y))
    return pts


def density_ring(cx, cy, radius, color, alpha=150, width=3):
    d = ImageDraw.Draw(layer((1000, 1000)))  # dummy for type
    pass


# =============================================================================
# VISUAL FUNCTIONS
# =============================================================================

def vis_contact(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    pts = wave_curve(cx, cy - 30, w * 0.40, h * 0.04, t * 0.3)
    glow_line(im, partial(pts, reveal), VIOLET, 4, int(120 + 100 * reveal), 10)

    if reveal > 0.4:
        q = (reveal - 0.4) * 1.7
        d.rounded_rectangle((cx - w * 0.20, cy + 15, cx + w * 0.20, cy + 55), radius=12,
                            fill=(*mix(WHITE, VIOLET, 0.08), int(180 * q)),
                            outline=(*VIOLET, int(160 * q)), width=2)
        centered(d, (cx, cy + 35),
                 "WE ARE YOU IN THE FUTURE",
                 font(FONT_SANS_BOLD, int(h * 0.022)),
                 (*VIOLET, int(220 * q)))

    seal(im, "THE CASSIOPAEAN CONTACT",
         "a sixth-density source — 1994 - 1997", VIOLET)


def vis_program_illusion(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    n_grid = int(12 * reveal)
    for i in range(n_grid):
        x = lerp(w * 0.10, w * 0.90, i / max(1, n_grid - 1))
        d.line((x, h * 0.10, x, h * 0.72), fill=(*INK, int(40 + 60 * pulse(t * 0.2 + i))), width=1)

    for j in range(int(8 * reveal)):
        y = lerp(h * 0.10, h * 0.72, j / 7)
        d.line((w * 0.10, y, w * 0.90, y), fill=(*INK, int(40 + 60 * pulse(t * 0.2 + j * 0.3))), width=1)

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        d.rounded_rectangle((cx - w * 0.30, cy - 20, cx + w * 0.30, cy + 20), radius=10,
                            fill=(*mix(WHITE, CRIMSON, 0.06), int(180 * q)),
                            outline=(*CRIMSON, int(150 * q)), width=2)
        centered(d, (cx, cy),
                 "THAT PERCEPTION IS PART OF THE ILLUSION",
                 font(FONT_SANS_BOLD, int(h * 0.020)), (*CRIMSON, int(220 * q)))

    seal(im, "REALITY IS A PROGRAM",
         "what you perceive as solid is a readout of a hyperdimensional code", CRIMSON)


def vis_wave_intro(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    pts = wave_curve(cx, cy, w * 0.55, h * 0.06, t * 0.5)
    glow_line(im, pts, CYAN, 5, int(100 + 120 * reveal), 14)

    if reveal > 0.4:
        q = (reveal - 0.4) * 1.7
        d.rounded_rectangle((cx - w * 0.32, cy - 25, cx + w * 0.32, cy + 25), radius=12,
                            fill=(*mix(WHITE, CYAN, 0.08), int(180 * q)),
                            outline=(*CYAN, int(160 * q)), width=2)
        centered(d, (cx, cy),
                 "MACRO-COSMIC QUANTUM WAVE COLLAPSE",
                 font(FONT_SANS_BOLD, int(h * 0.022)),
                 (*CYAN, int(220 * q)))

    seal(im, "THE WAVE",
         "a hyperdimensional transition — predicted, measurable, underway", CYAN)


def vis_third_density(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    d.ellipse((cx - 50, cy - 55, cx + 50, cy + 55),
              fill=(*PALE_SILVER, 150), outline=(*INK, 160), width=3)
    centered(d, (cx, cy - 5), "3RD DENSITY", font(FONT_SANS_BOLD, int(h * 0.025)), INK)
    centered(d, (cx, cy + 22), "self-consciousness\nchoice\npolarity",
             font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    if reveal > 0.4:
        q = (reveal - 0.4) * 1.7
        d.ellipse((cx - 60 - 15 * q, cy - 65 - 15 * q, cx + 60 + 15 * q, cy + 65 + 15 * q),
                  outline=(*CYAN, int(120 * q)), width=2)
        arrow(d, (cx + 55, cy), (cx + 70, cy), CYAN, 2, 6)
        centered(d, (cx + 85, cy), "4D",
                 font(FONT_SANS_BOLD, int(h * 0.022)), (*CYAN, int(200 * q)))

    seal(im, "CURRENT DENSITY: THIRD",
         "the density of forgetting — and of first conscious choice", INK)


def vis_fourth_density(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(5):
        rr = 25 + i * 25
        a = int(180 * (1 - i / 5) * reveal)
        d.ellipse((cx - rr, cy - rr * 0.5, cx + rr, cy + rr * 0.5),
                  outline=(*CYAN, a), width=2)

    if reveal > 0.4:
        q = smoothstep(0.4, 0.8, u)
        centered(d, (cx, h * 0.76),
                 "4TH DENSITY — VARIABLE PHYSICALITY",
                 font(FONT_SANS_BOLD, int(h * 0.020)), CYAN)
        centered(d, (cx, h * 0.81),
                 "thought becomes malleable — reality responds to consciousness",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "FOURTH DENSITY",
         "the first density where physicality is not fixed", CYAN)


def vis_dna_superconductor(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    steps = 40
    pts_l = []
    pts_r = []
    for i in range(steps):
        q = i / (steps - 1)
        x = cx - w * 0.25 + q * w * 0.50
        offset = math.sin(q * math.tau * 4 + t * 0.5) * h * 0.04
        pts_l.append((x, cy + offset - h * 0.015))
        pts_r.append((x, cy + offset + h * 0.015))

    visible = int(steps * reveal)
    if visible > 1:
        d.line(pts_l[:visible], fill=(*CYAN, 200), width=3)
        d.line(pts_r[:visible], fill=(*CYAN, 200), width=3)
        for i in range(0, visible, 3):
            d.line((pts_l[i][0], pts_l[i][1], pts_r[i][0], pts_r[i][1]),
                   fill=(*GOLD, 120), width=2)

    if reveal > 0.5:
        q = smoothstep(0.5, 0.9, u)
        sig_x = cx + math.sin(t * 0.8) * w * 0.10
        sig_y = cy + math.sin(t * 0.3) * h * 0.06
        glow_circle(im, sig_x, sig_y, 8, GOLD, int(160 * q), 8)
        d.line((cx, cy, sig_x, sig_y), fill=(*GOLD, int(100 * q)), width=2)

    seal(im, "DNA AS SUPERCONDUCTOR",
         "neurotransceiver for thought pattern programs — the hardware of the illusion", CYAN)


def vis_sto_sts(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    sto_x = cx - w * 0.22
    sts_x = cx + w * 0.22

    # STO
    for i in range(3):
        a = i * math.tau / 3 + t * 0.2
        rr = 30 + 15 * pulse(t + i, 0.5)
        x = sto_x + math.cos(a) * rr
        y = cy + math.sin(a) * rr
        d.line((sto_x, cy, x, y), fill=(*GOLD, 120), width=2)
    d.ellipse((sto_x - 20, cy - 20, sto_x + 20, cy + 20),
              fill=(*PALE_GOLD, 180), outline=(*GOLD, 180), width=3)
    centered(d, (sto_x, cy), "STO",
             font(FONT_SANS_BOLD, int(h * 0.030)), GOLD)

    # STS
    d.ellipse((sts_x - 20, cy - 20, sts_x + 20, cy + 20),
              fill=(*PALE_CRIMSON, 180), outline=(*CRIMSON, 180), width=3)
    centered(d, (sts_x, cy), "STS",
             font(FONT_SANS_BOLD, int(h * 0.030)), CRIMSON)

    if reveal > 0.5:
        q = smoothstep(0.5, 0.9, u)
        arrow(d, (sto_x, cy), (cx - 5, cy), GOLD, 3, 8)
        arrow(d, (sts_x, cy), (cx + 5, cy), CRIMSON, 3, 8)
        centered(d, (cx, cy - 35),
                 "STO FLOWS OUTWARD\nSTS FLOWS INWARD",
                 font(FONT_SANS_BOLD, int(h * 0.018)),
                 (*SOFT_INK, int(200 * q)))

    seal(im, "THE POLARITY CHOICE",
         "STO touches all — STS touches only the origin point", GOLD)


def vis_bleedthrough(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    bleed = smoothstep(0.15, 0.7, u)

    # solid reality
    d.rectangle((w * 0.10, h * 0.08, w * 0.42, h * 0.72),
                fill=(*PALE_SILVER, 180), outline=(*INK, 160), width=3)

    # bleedthrough
    d.rectangle((w * 0.58, h * 0.08, w * 0.90, h * 0.72),
                fill=(*mix(PALE_SILVER, CYAN, 0.3 * bleed), 180),
                outline=(*mix(INK, CYAN, bleed), 160), width=3)

    if bleed > 0.3:
        q = clamp((bleed - 0.3) / 0.7)
        pts = wave_curve(cx + w * 0.24, cy, w * 0.18, h * 0.05 * q, t * 0.5)
        glow_line(im, pts, CYAN, 4, int(150 * q), 10)

    state = "BLEEDTHROUGH ACTIVE" if bleed > 0.5 else "REALM SEPARATE"
    col = CYAN if bleed > 0.5 else INK
    seal(im, state,
         "4th density oozes into 3rd — faint reflections of a new reality", col)


def vis_knowledge_protects(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(6):
        a = i * math.tau / 6 + t * 0.1
        rr = 20 + 15 * i * reveal * 0.15
        x = cx + math.cos(a) * rr
        y = cy + math.sin(a) * rr * 0.5
        d.line((cx, cy, x, y), fill=(*GOLD, int(100 * reveal)), width=2)
        d.ellipse((x - 5, y - 5, x + 5, y + 5),
                  fill=(*PALE_GOLD, int(180 * reveal)),
                  outline=(*GOLD, int(150 * reveal)), width=2)

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        d.rounded_rectangle((cx - w * 0.30, cy - 20, cx + w * 0.30, cy + 20), radius=10,
                            fill=(*mix(WHITE, GOLD, 0.08), int(160 * q)),
                            outline=(*GOLD, int(150 * q)), width=2)
        centered(d, (cx, cy),
                 "KNOWLEDGE PROTECTS",
                 font(FONT_SANS_BOLD, int(h * 0.025)),
                 (*GOLD, int(220 * q)))

    seal(im, "THE ONLY DEFENSE",
         "not symbols, not names — understanding itself raises your vibration", GOLD)


def vis_realm_border(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)
    crossing = smoothstep(0.2, 0.8, u)

    # two realms
    d.rectangle((w * 0.06, cy - 80, w * 0.46, cy + 80),
                fill=(*PALE_SILVER, 150), outline=(*INK, 120), width=3)
    centered(d, (w * 0.26, cy), "3D",
             font(FONT_SANS_BOLD, int(h * 0.040)), INK)

    d.rectangle((w * 0.54, cy - 80, w * 0.94, cy + 80),
                fill=(*PALE_CYAN, 120), outline=(*CYAN, 120), width=3)
    centered(d, (w * 0.74, cy), "4D",
             font(FONT_SANS_BOLD, int(h * 0.040)), CYAN)

    if crossing > 0:
        q = clamp(crossing * 2)
        border_pts = wave_curve(cx, cy, w * 0.06, h * 0.02, t * 0.5)
        glow_line(im, border_pts, GOLD, 5, int(200 * q), 12)
        if crossing > 0.5:
            centered(d, (cx, h * 0.76),
                     "REALM BORDER CROSSING",
                     font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)

    seal(im, "THE BORDER IS THINNING",
         "the realm crossing will be like a thermonuclear blast — or a birth", CYAN)


def vis_time_illusion(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    pts = wave_curve(cx, cy, w * 0.50, h * 0.05, t * 0.3)
    glow_line(im, partial(pts, reveal), VIOLET, 4, 180, 10)

    if reveal > 0.4:
        q = smoothstep(0.4, 0.85, u)
        # ring representing simultaneity
        d.ellipse((cx - 40 * q, cy - 25 * q, cx + 40 * q, cy + 25 * q),
                  outline=(*GOLD, int(150 * q)), width=3)
        if q > 0.5:
            centered(d, (cx, cy),
                     "THE PAST AND FUTURE\nARE ALL IN THE PRESENT",
                     font(FONT_SANS_BOLD, int(h * 0.022)),
                     (*GOLD, int(200 * q)))

    seal(im, "TIME IS A PERCEPTION ILLUSION",
         "linear time is a program readout — all moments coexist", VIOLET)


def vis_thought_matter(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # thought
    glow_circle(im, cx - 60, cy, 12, VIOLET, 150, 10)

    # bilaterality
    if reveal > 0.3:
        q = smoothstep(0.3, 0.7, u)
        arrow(d, (cx - 45, cy), (cx - 10, cy), VIOLET, 3, 8)
        arrow(d, (cx + 10, cy), (cx + 45, cy), GOLD, 3, 8)
        glow_circle(im, cx + 60, cy, 12, GOLD, int(150 * q), 10)

    if reveal > 0.5:
        q2 = (reveal - 0.5) * 2
        centered(d, (cx, h * 0.76),
                 "THOUGHT BECOMES MATTER — BILATERALLY",
                 font(FONT_SANS_BOLD, int(h * 0.020)), GOLD)
        centered(d, (cx, h * 0.81),
                 "the beginning emerges from the end, and vice versa",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "THE EMERGENCE OF REALITY",
         "thought and matter are the same substance at different stages of expression", VIOLET)


def vis_merge(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    # two waves approach and merge
    left_wave = wave_curve(cx - 60, cy, 80, h * 0.03, t * 0.4)
    right_wave = wave_curve(cx + 60, cy, 80, h * 0.03, t * 0.6 + 1)

    merge_factor = smoothstep(0.2, 0.7, u)

    if merge_factor < 0.8:
        glow_line(im, left_wave, VIOLET, 4, 160, 10)
        glow_line(im, right_wave, CYAN, 4, 160, 10)

    if merge_factor > 0.3:
        q = clamp((merge_factor - 0.3) / 0.7)
        merged = wave_curve(cx, cy, w * 0.35, h * 0.06 * q, t * 0.5)
        glow_line(im, merged, GOLD, 6, int(200 * q), 14)
        if q > 0.5:
            glow_circle(im, cx, cy, 20, GOLD, int(150 * q), 16)

    seal(im, "THE MERGE",
         "when the wave reaches earth — the future self merges with the present", GOLD)


def vis_wave_crowded(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(int(15 * reveal)):
        a = random.uniform(0, 1) * math.tau
        r = random.uniform(20, w * 0.35)
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r * 0.5
        col = [GOLD, CYAN, VIOLET, GREEN][i % 4]
        d.ellipse((x - 4, y - 4, x + 4, y + 4),
                  fill=(*col, int(120 + 80 * pulse(t + i))))

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        centered(d, (cx, h * 0.76),
                 "THE WAVE IS CROWDED",
                 font(FONT_SANS_BOLD, int(h * 0.022)), GOLD)
        centered(d, (cx, h * 0.81),
                 "everyone in the galaxy who wants a piece of Earth's transition is riding it",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "THE TRANSITION IS HERE",
         "the realm border crossing is not future — it is now", CYAN)


def vis_seventh_density(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(20):
        a = i * math.tau / 20 + t * 0.05
        rr = 15 + i * 6 * reveal
        col = mix(VIOLET, GOLD, i / 20)
        d.ellipse((cx - rr, cy - rr * 0.5, cx + rr, cy + rr * 0.5),
                  outline=(*col, int(200 * (1 - i / 20) * reveal)), width=2)

    if reveal > 0.6:
        q = (reveal - 0.6) * 2.5
        centered(d, (cx, cy),
                 "7TH DENSITY: UNION WITH THE ONE",
                 font(FONT_SANS_BOLD, int(h * 0.024)),
                 (*GOLD, int(220 * q)))
        centered(d, (cx, cy + 25),
                 "timeless — essence radiates through all realms",
                 font(FONT_SANS, int(h * 0.016)), (*SOFT_INK, int(180 * q)))

    seal(im, "THE RETURN TO SOURCE",
         "7th density is union with the One — the ground of all being", GOLD)


def vis_knowledge_center(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(7):
        rr = 15 + i * 18 * reveal
        col = mix(INK, GOLD, i / 6) if reveal < 0.5 else mix(GOLD, VIOLET, (reveal - 0.5) * 2)
        a = int(180 * (1 - i / 7) * reveal)
        d.ellipse((cx - rr, cy - rr * 0.6, cx + rr, cy + rr * 0.6),
                  outline=(*col, a), width=3)

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        centered(d, (cx, h * 0.76),
                 "REMOVAL OF KNOWLEDGE CENTERS",
                 font(FONT_SANS_BOLD, int(h * 0.020)), CRIMSON)
        centered(d, (cx, h * 0.81),
                 "the cutting up of Osiris' body = the breaking up of DNA",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "KNOWLEDGE CENTERS IN DNA",
         "the fall was a reduction in the number of accessible frequencies", CRIMSON)


def vis_sts_nature(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    for i in range(10):
        a = i * math.tau / 10 + t * 0.15
        rr = 30 + 20 * math.sin(t * 0.3 + i)
        x = cx + math.cos(a) * rr
        y = cy + math.sin(a) * rr
        d.line((cx, cy, x, y), fill=(*CRIMSON, int(100 * reveal)), width=2)

    glow_circle(im, cx, cy, 15, CRIMSON, int(150 * reveal), 10)
    centered(d, (cx, cy),
             "STS",
             font(FONT_SANS_BOLD, int(h * 0.035)),
             (*CRIMSON, int(200 * reveal)))

    if reveal > 0.5:
        q = (reveal - 0.5) * 2
        centered(d, (cx, h * 0.76),
                 "STS = ULTIMATE IMBALANCE",
                 font(FONT_SANS_BOLD, int(h * 0.020)), CRIMSON)
        centered(d, (cx, h * 0.81),
                 "flows inward — touches only the origin point",
                 font(FONT_SANS, int(h * 0.016)), SOFT_INK)

    seal(im, "SERVICE TO SELF",
         "the path of separation — powerful but self-disintegrating", CRIMSON)


def vis_final(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.50, h * 0.42
    reveal = ease(u)

    wave = wave_curve(cx, cy, w * 0.55, h * 0.06, t * 0.3)
    glow_line(im, partial(wave, reveal), CYAN, 5, 180, 14)

    if reveal > 0.3:
        q = smoothstep(0.3, 0.9, u)
        glow_circle(im, cx, cy, 25 * q, GOLD, int(120 * q), 18)
        if q > 0.5:
            centered(d, (cx, cy),
                     "WAKE UP",
                     font(FONT_SERIF_BOLD, int(h * 0.055)),
                     (*GOLD, int(200 * (q - 0.5) * 2)))

    seal(im, "YOU ARE THE WAVE",
         "the future self is not coming — it is remembering itself through you", GOLD)


VISUALS = {
    "contact": vis_contact,
    "program": vis_program_illusion,
    "wave_intro": vis_wave_intro,
    "third": vis_third_density,
    "fourth": vis_fourth_density,
    "dna": vis_dna_superconductor,
    "polarity": vis_sto_sts,
    "bleed": vis_bleedthrough,
    "knowledge": vis_knowledge_protects,
    "border": vis_realm_border,
    "time": vis_time_illusion,
    "thought_matter": vis_thought_matter,
    "merge": vis_merge,
    "crowded": vis_wave_crowded,
    "seventh": vis_seventh_density,
    "knowledge_center": vis_knowledge_center,
    "sts": vis_sts_nature,
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
    Scene("The contact",
          "In 1994, a group of researchers in Florida began receiving communications from a source identifying as 'you in the future.'",
          7.0, "contact", {}),
    Scene("Sixth density",
          "The Cassiopaeans claimed to be a sixth-density collective — humanity's own future self, communicating backward through time.",
          7.5, "contact", {}),

    Scene("The program",
          "Reality, they said, is a program — a hyperdimensional simulation maintained by electromagnetic fields interacting with DNA.",
          7.5, "program", {}),
    Scene("Perception is part of the illusion",
          "'That perception is part of the illusion. What you perceive as solid is a readout of a hyperdimensional code.'",
          7.5, "program", {}),

    Scene("The Wave",
          "The Wave is a Macro-cosmic Quantum Wave Collapse — a hyperdimensional transition that reshapes the very structure of reality.",
          8.0, "wave_intro", {}),
    Scene("The crest",
          "It is not a metaphor. It is a physical and metaphysical event — a shift in the vibrational frequency of the planet itself.",
          7.5, "wave_intro", {}),

    Scene("Third density",
          "We are currently in third density — the density of self-consciousness, of forgetting, and of first conscious choice.",
          7.0, "third", {}),
    Scene("The forgetting",
          "The veil of forgetting is what makes third density unique. We do not remember where we came from — which makes our choices real.",
          7.5, "third", {}),

    Scene("Fourth density",
          "Fourth density is the first density with variable physicality. Thought becomes malleable. Reality begins to respond directly to consciousness.",
          8.0, "fourth", {}),
    Scene("The next octave",
          "Earth is transitioning from third to fourth density. The clock has been ticking for 75,000 years — and the hour is striking.",
          7.5, "fourth", {}),

    Scene("DNA as superconductor",
          "DNA is not just a protein-coding blueprint. It is a conductor of electricity — a neurotransceiver for consciousness itself.",
          8.0, "dna", {}),
    Scene("The antenna",
          "'DNA acts as a superconductor — the method used for creation and maintenance of program illusions, such as the perception of linear time.'",
          8.0, "dna", {}),

    Scene("STO and STS",
          "The fundamental polarity: Service to Others and Service to Self. Both are paths to the Creator — they just take different routes.",
          7.5, "polarity", {}),
    Scene("Flow outward, flow inward",
          "STO flows outward and touches all, including the point of origin. STS flows inward and touches only the origin point.",
          7.5, "polarity", {}),

    Scene("Bleedthrough",
          "Fourth density is already bleeding into third. Unexplained phenomena, synchronicities, 'paranormal' events — these are the ooze of a new reality.",
          8.0, "bleedthrough", {}),
    Scene("The heat",
          "'Heat means 4th density bleedthrough — oozing of faint reflections of new reality.' The transition is not theoretical. It is thermal.",
          8.0, "bleedthrough", {}),

    Scene("Knowledge protects",
          "The Cassiopaeans' most repeated teaching: knowledge protects. Not faith, not ritual, not symbols — understanding itself raises your vibration.",
          7.5, "knowledge", {}),
    Scene("The vibration",
          "Knowledge is not information. It is the alignment of your being with the truth of your own nature. And that alignment IS protection.",
          8.0, "knowledge", {}),

    Scene("Realm border crossing",
          "The realm border crossing will be like a thermonuclear blast. The lower cannot enter the higher — only the vibrationally compatible can pass.",
          8.0, "border", {}),
    Scene("The sorting",
          "There is no judgment. There is only resonance. You are sorted by your own vibration — which is the sum of what you have chosen to become.",
          8.0, "border", {}),

    Scene("Time is a perception illusion",
          "Linear time is not fundamental. It is a readout of the program — a way of organizing a simultaneous reality into a sequential experience.",
          8.0, "time", {}),
    Scene("All time is now",
          "'The past and the future are all in the present.' Time does not flow. You move through a static block of all moments.",
          7.5, "time", {}),

    Scene("Thought becomes matter",
          "The Cassiopaeans described a principle called 'bilaterality' — thought becomes matter, and matter becomes thought, in a continuous loop.",
          8.0, "thought_matter", {}),
    Scene("Dual emergence",
          "'The beginning emerges from the end, and vice versa. Union with the One is both origin and destination.'",
          8.0, "thought_matter", {}),

    Scene("The merge",
          "When the Wave reaches Earth, the Cassiopaeans merge with us. Not as invaders — as our own future self, recognizing itself.",
          8.0, "merge", {}),
    Scene("The crowded wave",
          "The Wave is crowded. Every civilization in the galaxy that has an interest in Earth's transition is riding it. Both sides respect free will. Only one respects yours.",
          8.5, "crowded", {}),

    Scene("The Black Sun",
          "The ultimate destiny of the STS path is the Black Sun — a black hole. Not as metaphor, but as literal gravitational collapse of a consciousness that has turned entirely inward.",
          8.0, "sts", {}),
    Scene("The centre that cannot hold",
          "STS disintegrates because separation is not sustainable. A self that serves only itself eventually consumes itself.",
          7.5, "sts", {}),

    Scene("Seventh density",
          "Seventh density is union with the One — timeless, radiant, the ground from which all realities emerge and to which all return.",
          7.5, "seventh", {}),
    Scene("The great cycle",
          "Eighth density is the beginning of the next octave. The universe breathes — expansion and contraction, creation and return, in an eternal rhythm.",
          8.0, "seventh", {}),

    Scene("Knowledge centers in DNA",
          "The Osirian cycle is not myth. It is the history of consciousness encoded in biology — the removal of knowledge centers from DNA.",
          8.0, "knowledge_center", {}),

    Scene("Closing",
          "The Wave is not a belief. It is a fact of hyperdimensional physics. The only question is whether your vibration is aligned with its frequency.",
          8.0, "final", {}),
    Scene("Final frame",
          "Knowledge protects. Wake up. The future self is not coming — it is remembering itself through you.",
          7.0, "final", {}),
]


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
                frame_dir / f"preview_{oi:02d}.jpg", quality=95)
        return frame_dir
    for fi in range(count):
        path = frame_dir / f"{fi:05d}.jpg"
        if path.exists():
            continue
        render_frame(scene, fi, count, width, height, index * 10000 + fi).save(
            path, quality=95, subsampling=0)
    return encode_scene(index, fps)


def concatenate(paths):
    concat_path = OUTPUT / "concat.txt"
    concat_path.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    final = OUTPUT / "the_wave.mp4"
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
        "title": "the wave — hyperdimensional reality is here",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "luminous wave-crest travelling through every scene",
        "palette_roles": {
            "ink": "3rd density / physical reality",
            "cyan": "4th density / the Wave bleedthrough",
            "gold": "STO / knowledge / protection",
            "crimson": "STS / control / separation",
            "violet": "6th density / the future self",
            "green": "the merge / healing / balance",
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
