#!/usr/bin/env python3
"""
THE VOICE INSIDE YOUR CHEST
Platinum procedural visual essay — the enteric nervous system.

Adapted from:
expansion-essays/40_the_voice_inside_your_chest.md

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
INK     architecture / scaffold / connective form
CYAN    neural signalling / enteric communication
GOLD    gut-derived signals / serotonin / microbiome messaging
CRIMSON perturbation / stress / inflammation / vagal withdrawal
GREEN   coordinated repair / trophic maintenance / resilience
VIOLET  higher vagal integration / brainstem relay
PAPER   epithelial lining / gut wall

CONTINUITY OBJECT
-----------------
A gold signal-particle (serotonin molecule analogue) travels from
enteric neurons upward through the vagus nerve. It appears in every
scene — as a local gut signal, a vagal impulse, or a brainstem arrival.

OUTPUT
------
output_voice_inside_chest/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  voice_inside_chest.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python voice_inside_chest_platinum.py
python voice_inside_chest_platinum.py --preview
python voice_inside_chest_platinum.py --scene 12
python voice_inside_chest_platinum.py --fps 12 --width 1920 --height 1080
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
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_voice_inside_chest")
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
VOID = (24, 28, 34)
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


def glow_polygon(im, poly, color, alpha=170, blur=16):
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.polygon(poly, fill=(*color, alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))


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


def wavy_tube(cx, cy, length, amp, phase=0.0, samples=80):
    pts = []
    for i in range(samples):
        q = i / (samples - 1)
        x = cx - length / 2 + q * length
        envelope = math.sin(math.pi * q) ** .48
        y = cy + math.sin(q * math.tau * 2.5 + phase) * amp * envelope
        pts.append((x, y))
    return pts


def tube_wall(cx, cy, length, amp, width, phase=0.0, samples=80):
    top = []
    bot = []
    for i in range(samples):
        q = i / (samples - 1)
        x = cx - length / 2 + q * length
        envelope = math.sin(math.pi * q) ** .48
        y = cy + math.sin(q * math.tau * 2.5 + phase) * amp * envelope
        local_w = width * (.55 + .45 * math.sin(math.pi * q) ** .7)
        top.append((x, y - local_w / 2))
        bot.append((x, y + local_w / 2))
    return top, bot


def draw_gut_tube(im, cx, cy, length, amp, width, phase=0.0,
                  fill=PALE_SILVER, outline=INK, alpha=230):
    d = ImageDraw.Draw(im)
    top, bot = tube_wall(cx, cy, length, amp, width, phase)
    poly = top + list(reversed(bot))
    d.polygon(poly, fill=(*fill, alpha), outline=(*outline, min(255, alpha)), width=3)
    return top, bot


def draw_enteric_neuron(im, x, y, size, active=False, phase=0.0):
    d = ImageDraw.Draw(im)
    r = size * .5
    n_neurites = 6
    for i in range(n_neurites):
        a = i * math.tau / n_neurites + phase * .3
        nr = size * (.8 + .6 * math.sin(phase + i))
        d.line((x, y, x + math.cos(a) * nr, y + math.sin(a) * nr),
               fill=(*CYAN, 160), width=2)
    col = PALE_GOLD if active else PALE_CYAN
    outline = GOLD if active else DEEP_CYAN
    d.ellipse((x - r, y - r, x + r, y + r),
              fill=(*col, 230), outline=(*outline, 200), width=3)
    if active:
        glow_circle(im, x, y, r + 4, GOLD, 90, 8)


def draw_neural_crest_cells(im, cx, points, reveal=1.0):
    d = ImageDraw.Draw(im)
    for i, (x, y) in enumerate(points):
        q = clamp(reveal * len(points) - i)
        if q <= 0:
            continue
        r = lerp(10, 5, i / max(1, len(points) - 1))
        d.ellipse((x - r, y - r, x + r, y + r),
                  fill=(*PALE_VIOLET, int(220 * q)),
                  outline=(*VIOLET, int(170 * q)), width=2)
        for a in (0, math.tau / 3, math.tau * 2 / 3):
            dx = math.cos(a + i) * r * 1.6
            dy = math.sin(a + i) * r * 1.6
            d.line((x, y, x + dx, y + dy), fill=(*PALE_VIOLET, int(100 * q)), width=1)


def draw_vagus(im, x1, y1, x2, y2, branches=0, active=False, phase=0.0):
    d = ImageDraw.Draw(im)
    cable_y = []
    for i in range(16):
        q = i / 15
        cx = lerp(x1, x2, q) + math.sin(q * math.tau * 4 + phase) * 6
        cy = lerp(y1, y2, q)
        cable_y.append((cx, cy))
    col = GOLD if active else SILVER
    d.line(cable_y, fill=(*col, 180), width=5, joint="curve")
    for b in range(branches):
        bx = lerp(x1, x2, (b + 1) / (branches + 1))
        by = lerp(y1, y2, (b + 1) / (branches + 1))
        spread = 30 + 20 * math.sin(phase + b)
        d.line((bx, by, bx + spread, by + spread * .3),
               fill=(*col, 120), width=3)
        d.line((bx, by, bx - spread, by + spread * .3),
               fill=(*col, 120), width=3)


def draw_microbiome(im, cx, cy, count, reveal=1.0, phase=0.0):
    d = ImageDraw.Draw(im)
    rng = random.Random(48)
    for i in range(count):
        q = clamp(reveal * count - i)
        if q <= 0:
            continue
        a = rng.uniform(0, math.tau)
        r = rng.uniform(6, 18) * (1 + .08 * math.sin(phase + i))
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        col = (rng.randint(50, 200), rng.randint(100, 220), rng.randint(80, 200))
        d.ellipse((x - 4, y - 3, x + 4, y + 3),
                  fill=(*col, int(200 * q)),
                  outline=(*SOFT_INK, int(100 * q)), width=1)


def draw_serotonin_molecule(im, x, y, size, alpha=255):
    d = ImageDraw.Draw(im)
    points = []
    a = -math.pi / 2
    for _ in range(6):
        points.append((x + math.cos(a) * size, y + math.sin(a) * size))
        a += math.tau / 6
    d.polygon(points, fill=(*PALE_GOLD, alpha), outline=(*GOLD, min(255, alpha)), width=2)
    d.ellipse((x - size * .2, y - size * .2, x + size * .2, y + size * .2),
              fill=(*WHITE, alpha))
    glow_circle(im, x, y, size * 1.5, GOLD, int(60 * alpha / 255), 6)
    return (x, y)


def draw_signal_particle(im, x, y, phase, color=GOLD):
    r = 6 + 4 * pulse(phase, 1.5)
    glow_circle(im, x, y, r, color, 190, 9)
    core = layer(im.size)
    ImageDraw.Draw(core).ellipse(
        (x - 4, y - 4, x + 4, y + 4),
        fill=(*mix(color, WHITE, .4), 220),
    )
    im.alpha_composite(core)


def peristaltic_wave(top, bot, point, phase=0.0):
    """Return the point along a tube where a peristaltic contraction sits."""
    idx = int(point * (len(top) - 1))
    idx = max(0, min(len(top) - 1, idx))
    return (
        lerp(top[idx][0], bot[idx][0], .5),
        lerp(top[idx][1], bot[idx][1], .5),
    )


# =============================================================================
# VISUAL FUNCTIONS
# =============================================================================

def vis_gut_architecture(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    top, bot = draw_gut_tube(im, cx, cy, w * .56, h * .04, h * .14,
                             phase=t * .15, alpha=int(200 + 55 * reveal))
    label = "ENTERIC NERVOUS SYSTEM"
    sub = "500 million neurons — the second brain"
    if reveal > .6:
        for i in range(7):
            q = i / 6
            x = lerp(cx - w * .26, cx + w * .26, q)
            y = lerp(top[int(q * 79)][1], bot[int(q * 79)][1], .5)
            active = pulse(t * .4 + i) > .5
            draw_enteric_neuron(im, x, y, 14, active, t + i)
    seal(im, label, sub, CYAN)


def vis_neural_crest_migration(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    top, bot = tube_wall(cx, cy, w * .40, h * .03, h * .10, phase=t * .08)
    d.polygon(top + list(reversed(bot)),
              fill=(*PALE_SILVER, 180), outline=(*INK, 150), width=2)
    crest_start_y = h * .18
    crest_end_y = cy
    n_cells = 12
    reveal = ease(u)
    cells = []
    for i in range(n_cells):
        q = i / (n_cells - 1)
        x = cx + w * .28 * (reveal * 1.2) * math.sin(q * math.pi * 1.3)
        y = lerp(crest_start_y, crest_end_y, q * reveal)
        cells.append((x, y))
    draw_neural_crest_cells(im, cx + w * .10, cells, reveal)
    d.line((cx + w * .10, crest_start_y - 20, cx + w * .10, crest_end_y + 20),
           fill=(*VIOLET, 100), width=2)
    arrow(d, (cx + w * .10, crest_start_y - 10),
          (cx + w * .10, crest_start_y + 20), VIOLET, 2, 6)
    seal(im, "NEURAL CREST MIGRATION",
         "enteric neurons originate in the embryonic spinal cord", VIOLET)


def vis_independent_reflex(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .12, alpha=int(180 + 75 * reveal))
    contraction = smoothstep(.15, .45, u)
    release = smoothstep(.40, .72, u)
    if contraction > 0:
        wave_pt = peristaltic_wave(top, bot, .3 + .4 * contraction - .3 * release)
        glow_circle(im, wave_pt[0], wave_pt[1], 22, CRIMSON if contraction < release else CYAN,
                    140, 12)
        d.line((wave_pt[0] - 15, wave_pt[1] - 15, wave_pt[0] + 15, wave_pt[1] + 15),
               fill=(*CRIMSON, 180), width=4)
        d.line((wave_pt[0] + 15, wave_pt[1] - 15, wave_pt[0] - 15, wave_pt[1] + 15),
               fill=(*CRIMSON, 180), width=4)
    label = "ISOLATED PERISTALTIC REFLEX"
    sub = "the enteric network coordinates movement without brain input"
    if release > .5:
        cx2 = wave_pt[0] + 10
        cy2 = wave_pt[1] - 30
        draw_signal_particle(im, cx2, cy2, t * .8, GOLD)
    seal(im, label, sub, CYAN)


def vis_serotonin_factory(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .12, alpha=int(180 + 75 * reveal))
    n_molecules = 8
    for i in range(n_molecules):
        q = i / max(1, n_molecules - 1)
        mx = lerp(cx - w * .18, cx + w * .18, q)
        my = lerp(cy - h * .04, cy + h * .04,
                  math.sin(q * math.tau + t * .5) * .5 + .5)
        alpha = int(200 * reveal * (.6 + .4 * pulse(t * .3 + i)))
        draw_serotonin_molecule(im, mx, my, 8, alpha)
    if reveal > .55:
        d.rounded_rectangle((cx - w * .28, cy - h * .16, cx + w * .28, cy + h * .16),
                            radius=14, outline=(*GOLD, 140), width=3)
    seal(im, "95% OF YOUR SEROTONIN",
         "the gut produces almost all of the body's mood-regulating molecule", GOLD)


def vis_vagus_highway(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    brain_y = h * .18
    gut_y = h * .62
    cx = w * .50
    reveal = ease(u)
    draw_vagus(im, cx, brain_y, cx, gut_y, branches=4, active=True, phase=t * .3)

    d.ellipse((cx - 30, brain_y - 28, cx + 30, brain_y + 28),
              fill=(*PALE_VIOLET, 180), outline=(*VIOLET, 200), width=3)
    centered(d, (cx, brain_y), "BRAINSTEM",
             font(FONT_SANS_BOLD, int(h * .022)), VIOLET)

    top, bot = draw_gut_tube(im, cx, gut_y, w * .36, h * .025, h * .10,
                             phase=t * .08 + .5, alpha=int(200 * reveal))

    if reveal > .32:
        sig_y = lerp(gut_y, brain_y, ease((reveal - .32) / .68))
        draw_signal_particle(im, cx, sig_y, t * 1.2, GOLD)
    seal(im, "THE VAGUS HIGHWAY",
         "80-90% of vagal fibers carry signals from body to brain", GOLD)


def vis_microbiome_dialogue(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    top, bot = draw_gut_tube(im, cx, cy, w * .44, h * .03, h * .10,
                             phase=t * .1, alpha=200)
    draw_microbiome(im, cx, cy - h * .02, 30, reveal, t)

    if reveal > .35:
        n_signal = 5
        for i in range(n_signal):
            q = (t * .4 + i / n_signal) % 1
            x = lerp(cx - w * .12, cx + w * .12, q)
            y = cy - h * .06 + math.sin(q * math.tau * 3) * h * .04
            col = GOLD if i % 2 == 0 else CYAN
            draw_signal_particle(im, x, y, t + i, col)

    seal(im, "MICROBIOME DIALOGUE",
         "gut bacteria produce neurotransmitters that influence the brain", GOLD)


def vis_gut_feeling(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)

    top, bot = draw_gut_tube(im, cx, cy, w * .40, h * .025, h * .10,
                             phase=t * .08, alpha=180)

    if reveal > .15:
        sensation = smoothstep(.15, .75, u)
        rising = sensation * (1 - smoothstep(.60, .90, u))
        if rising > 0:
            origin = (cx, cy)
            for j in range(6):
                a = j * math.tau / 6 + t * .3
                r = rising * h * .12
                x = origin[0] + math.cos(a) * r
                y = origin[1] + math.sin(a) * r
                col = mix(GOLD, CRIMSON, j / 5)
                d.ellipse((x - 5, y - 5, x + 5, y + 5),
                          fill=(*col, int(180 * rising)),
                          outline=(*GOLD, int(100 * rising)), width=2)

    if reveal > .55:
        brain_region = smoothstep(.55, .90, u)
        insula_x = cx
        insula_y = h * .14
        d.ellipse((insula_x - 30, insula_y - 20, insula_x + 30, insula_y + 20),
                  fill=(*PALE_VIOLET, int(180 * brain_region)),
                  outline=(*VIOLET, int(200 * brain_region)), width=3)
        if brain_region > .5:
            centered(d, (insula_x, insula_y), "INSULA",
                     font(FONT_SANS_BOLD, int(h * .020)), VIOLET)
            draw_vagus(im, cx, insula_y + 30, cx, cy - h * .08, branches=0,
                       active=True, phase=t * .2)

    seal(im, "GUT FEELINGS ARE REAL",
         "interoceptive signals from the gut reach conscious awareness", GOLD)


def vis_enteric_glia(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .12, alpha=int(180 + 75 * reveal))

    n_glia = 10
    for i in range(n_glia):
        q = i / max(1, n_glia - 1)
        gx = lerp(cx - w * .20, cx + w * .20, q)
        gy = lerp(cy - h * .06, cy + h * .06,
                  math.sin(q * math.tau * 2 + t * .2) * .5 + .5)
        active = pulse(t * .3 + i * .7) > .5
        r = 8
        col = GREEN if active else PALE_GREEN
        d.ellipse((gx - r, gy - r, gx + r, gy + r),
                  fill=(*col, int(200 * reveal)),
                  outline=(*GREEN, int(150 * reveal)), width=2)
        for a in (0, math.tau / 3, math.tau * 2 / 3):
            dx = math.cos(a + i * 1.3) * r * 2.2
            dy = math.sin(a + i * 1.3) * r * 2.2
            d.line((gx, gy, gx + dx, gy + dy),
                   fill=(*GREEN, int(80 * reveal)), width=1)

    seal(im, "ENTERIC GLIA",
         "support cells maintain neuronal health and gut barrier function", GREEN)


def vis_stress_response(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    stress_on = smoothstep(.10, .40, u)
    recovery = smoothstep(.55, .90, u)

    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .08, alpha=int(200 - 60 * stress_on + 40 * recovery))

    if stress_on > .05:
        glow = layer(im.size)
        gd = ImageDraw.Draw(glow)
        gd.rectangle((cx - w * .28, cy - h * .14, cx + w * .28, cy + h * .14),
                     fill=(*CRIMSON, int(80 * stress_on * (1 - recovery))))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(25)))

    if stress_on > .25:
        for i in range(5):
            a = i * math.tau / 5 + t * .6
            r = stress_on * h * .06 * (1 - recovery * .7)
            x = cx + math.cos(a) * w * .12
            y = cy + math.sin(a) * r
            d.line((cx, cy, x, y), fill=(*CRIMSON, int(120 * stress_on * (1 - recovery))),
                   width=3)

    if recovery > .3:
        draw_vagus(im, cx, cy - h * .12, cx, cy + h * .08,
                   branches=0, active=True, phase=t * .2)

    state = "VAGAL WITHDRAWAL" if stress_on > .3 and recovery < .5 else "VAGAL TONE RESTORED"
    col = CRIMSON if stress_on > .3 and recovery < .5 else GREEN
    seal(im, "STRESS RESHAPES THE GUT",
         state, col)


def vis_neurogenesis(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .1, alpha=int(150 + 100 * reveal))

    n_new = 5
    for i in range(n_new):
        q = t * .3 + i / n_new
        emerge = clamp(reveal * 2 - i * .3)
        if emerge <= 0:
            continue
        x = cx + math.cos(q * math.tau + i * 1.1) * w * .18
        y = cy + math.sin(q * math.tau + i * 1.1) * h * .05
        size = emerge * 12
        draw_enteric_neuron(im, x, y, size, True, t + i)
        d.ellipse((x - size * .4, y - size * .4, x + size * .4, y + size * .4),
                  fill=(*PALE_GOLD, int(180 * emerge)),
                  outline=(*GOLD, int(150 * emerge)), width=2)

    seal(im, "LIFELONG NEUROGENESIS",
         "the enteric nervous system continues to generate new neurons", GOLD)


def vis_heart_center(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .38
    reveal = ease(u)

    d.ellipse((cx - 40, cy - 35, cx + 40, cy + 35),
              fill=(*PALE_CRIMSON, 120), outline=(*CRIMSON, 180), width=3)
    d.line((cx - 20, cy, cx + 20, cy), fill=(*CRIMSON, 200), width=4)
    d.arc((cx - 15, cy - 18, cx + 15, cy + 5), 0, 180, fill=(*CRIMSON, 200), width=3)

    vagal_y = cy + 50
    draw_vagus(im, cx, vagal_y, cx, h * .72, branches=0, active=True, phase=t * .25)

    gut_y = h * .78
    top, bot = draw_gut_tube(im, cx, gut_y, w * .28, h * .02, h * .08,
                             phase=t * .1 + .3, alpha=180)

    if reveal > .25:
        sig_phase = (reveal - .25) / .75
        sig_y = lerp(gut_y, vagal_y, ease(sig_phase))
        draw_signal_particle(im, cx, sig_y, t * 1.5, GOLD)

    if reveal > .6:
        sig2_phase = (reveal - .6) / .4
        sig2_y = lerp(vagal_y, cy + 35, ease(sig2_phase))
        draw_signal_particle(im, cx, sig2_y, t * 1.8, CRIMSON)

    seal(im, "THE VOICE INSIDE YOUR CHEST",
         "heart, gut, and brain form a continuous intelligence", VIOLET)


def vis_dual_brain(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    reveal = ease(u)

    brain_x = w * .30
    brain_y = h * .30
    enteric_x = w * .70
    enteric_y = h * .30

    d.ellipse((brain_x - 50, brain_y - 35, brain_x + 50, brain_y + 35),
              fill=(*PALE_VIOLET, int(180 * reveal)),
              outline=(*VIOLET, int(200 * reveal)), width=3)
    centered(d, (brain_x, brain_y), "CEPHALIC BRAIN",
             font(FONT_SANS_BOLD, int(h * .019)), VIOLET)

    d.ellipse((enteric_x - 50, enteric_y - 35, enteric_x + 50, enteric_y + 35),
              fill=(*PALE_CYAN, int(180 * reveal)),
              outline=(*CYAN, int(200 * reveal)), width=3)
    centered(d, (enteric_x, enteric_y), "ENTERIC BRAIN",
             font(FONT_SANS_BOLD, int(h * .019)), CYAN)

    draw_vagus(im, brain_x + 50, brain_y, enteric_x - 50, enteric_y,
               branches=2, active=True, phase=t * .25)

    if reveal > .4:
        freq = smoothstep(.4, .85, u)
        n_lines = int(10 * freq)
        for i in range(n_lines):
            a = i * math.tau / max(1, n_lines) + t * .2
            r1 = 55 + 20 * math.sin(t + i)
            x1 = brain_x + math.cos(a) * r1
            y1 = brain_y + math.sin(a) * r1 * .7
            r2 = 55 + 20 * math.cos(t * .7 + i)
            x2 = enteric_x + math.cos(a + math.pi * .5) * r2
            y2 = enteric_y + math.sin(a + math.pi * .5) * r2 * .7
            d.line((x1, y1, x2, y2), fill=(*GOLD, int(60 * freq)), width=2)

    seal(im, "TWO BRAINS, ONE BODY",
         "the enteric nervous system is a second, independent mind", CYAN)


def vis_synthesis(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)

    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .1, alpha=int(180 + 75 * reveal))

    for i in range(8):
        q = i / 7
        x = lerp(cx - w * .22, cx + w * .22, q)
        y = lerp(cy - h * .04, cy + h * .04,
                 math.sin(q * math.tau * 2 + t * .3) * .5 + .5)
        draw_enteric_neuron(im, x, y, 12, pulse(t * .5 + i * .8) > .5, t + i)

    if reveal > .25:
        ascent = smoothstep(.25, .85, u)
        sig_y = lerp(cy, cy - h * .14, ease(ascent))
        draw_signal_particle(im, cx, sig_y, t * 1.3, GOLD)

    if reveal > .6:
        d.ellipse((cx - 30, cy - h * .16 - 25, cx + 30, cy - h * .16 + 25),
                  fill=(*PALE_GOLD, int(150 * (reveal - .6) / .4)),
                  outline=(*GOLD, int(180 * (reveal - .6) / .4)), width=3)
        centered(d, (cx, cy - h * .16),
                 "AWARENESS", font(FONT_SANS_BOLD, int(h * .020)), GOLD)

    seal(im, "THE BODY HAS ITS OWN INTELLIGENCE",
         "listen to the voice inside your chest", GOLD)


def vis_bodily_intelligence(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)

    top, bot = draw_gut_tube(im, cx, cy, w * .44, h * .03, h * .10,
                             phase=t * .08, alpha=200)

    n_neurons = 6
    for i in range(n_neurons):
        a = i * math.tau / n_neurons + t * .15
        r = w * .16
        nx = cx + math.cos(a) * r
        ny = cy + math.sin(a) * r * .6
        draw_enteric_neuron(im, nx, ny, 14, pulse(t * .6 + i) > .5, t + i)

    if reveal > .3:
        hub_phase = smoothstep(.3, .7, u)
        for a in range(n_neurons):
            ax = cx + math.cos(a * math.tau / n_neurons + t * .15) * w * .16
            ay = cy + math.sin(a * math.tau / n_neurons + t * .15) * h * .06
            d.line((ax, ay, cx, cy), fill=(*GOLD, int(100 * hub_phase)), width=2)

    seal(im, "INTELLIGENCE IS DISTRIBUTED",
         "the body thinks in ways the brain cannot", CYAN)


def vis_resilience(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    repair = smoothstep(.15, .85, u)

    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .1, alpha=int(200 - 80 * (1 - repair)))

    if repair < .6:
        damage = 1 - repair / .6
        for i in range(4):
            a = i * math.tau / 4 + t * .3
            x = cx + math.cos(a) * w * .12
            y = cy + math.sin(a) * h * .04
            d.line((x - 10, y - 10, x + 10, y + 10),
                   fill=(*CRIMSON, int(200 * damage)), width=4)
            d.line((x + 10, y - 10, x - 10, y + 10),
                   fill=(*CRIMSON, int(200 * damage)), width=4)

    if repair > .3:
        for i in range(5):
            q = clamp(repair * 5 - i - 1)
            x = cx + math.cos(t * .3 + i * 1.3) * w * .15
            y = cy + math.sin(t * .3 + i * 1.3) * h * .04
            draw_enteric_neuron(im, x, y, lerp(12, 16, q), True, t + i)

    seal(im, "THE SYSTEM REPAIRS ITSELF",
         "enteric neuroplasticity supports lifelong adaptation", GREEN)


def vis_human_implication(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)

    statements = [
        ("YOU HAVE A SECOND BRAIN", CYAN, True),
        ("IT ACTS WITHOUT PERMISSION", GOLD, True),
        ("IT PRODUCES YOUR MOOD", CRIMSON, True),
        ("IT LEARNS AND REMEMBERS", VIOLET, True),
        ("YOU CAN TRAIN IT", GREEN, False),
    ]
    for i, (text, col, supported) in enumerate(statements):
        q = clamp(reveal * len(statements) - i)
        y = h * (.18 + i * .12)
        d.rounded_rectangle((w * .18, y - 24, w * .82, y + 24), radius=14,
                            fill=(*mix(WHITE, col, .08), int(220 * q)),
                            outline=(*col, int(160 * q)), width=2)
        centered(d, (w * .42, y), text,
                 font(FONT_SANS_BOLD, int(h * .018)), (*INK, int(220 * q)))
        sym = "SUPPORTED" if supported else "EMERGING"
        centered(d, (w * .70, y), sym,
                 font(FONT_SANS_BOLD, int(h * .016)), (*col, int(200 * q)))

    seal(im, "WHAT THE SCIENCE SUPPORTS",
         "the gut is a fully functional neural network", CYAN)


def vis_final(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .42
    reveal = ease(u)
    gather = smoothstep(.10, .55, u)
    resolve = smoothstep(.55, .95, u)

    top, bot = draw_gut_tube(im, cx, cy, w * .50, h * .035, h * .12,
                             phase=t * .1, alpha=int(180 + 75 * reveal))

    n_signals = 12
    for i in range(n_signals):
        phase = (t * .3 + i / n_signals) % 1
        x = cx + math.cos(phase * math.tau + i * .5) * w * .18 * gather
        y = cy + math.sin(phase * math.tau + i * .5) * h * .05 * gather
        draw_signal_particle(im, x, y, t + i, GOLD if i % 3 < 2 else CYAN)

    if gather > .5:
        glow_circle(im, cx, cy, 30, GOLD, 100, 20)

    if resolve > .2:
        for j in range(8):
            a = j * math.tau / 8 + t * .1
            r = 50 + 30 * math.sin(t * .5 + j)
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r
            d.line((cx, cy, x, y), fill=(*GOLD, int(80 * resolve)), width=2)

    label = "YOU ARE NOT ONE VOICE"
    sub = "the body speaks in a language older than language"
    if resolve > .35:
        centered(d, (cx, cy),
                 "LISTEN", font(FONT_SERIF_BOLD, int(h * .060)),
                 (*GOLD, int(150 * resolve)))
    seal(im, label, sub, CYAN)


# =============================================================================
# REGISTRY
# =============================================================================

VISUALS: dict[str, Callable] = {
    "architecture": vis_gut_architecture,
    "neural_crest": vis_neural_crest_migration,
    "reflex": vis_independent_reflex,
    "serotonin": vis_serotonin_factory,
    "vagus": vis_vagus_highway,
    "microbiome": vis_microbiome_dialogue,
    "gut_feeling": vis_gut_feeling,
    "glia": vis_enteric_glia,
    "stress": vis_stress_response,
    "neurogenesis": vis_neurogenesis,
    "heart": vis_heart_center,
    "dual_brain": vis_dual_brain,
    "synthesis": vis_synthesis,
    "intelligence": vis_bodily_intelligence,
    "resilience": vis_resilience,
    "evidence": vis_human_implication,
    "final": vis_final,
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
    Scene("Architecture of the second brain",
          "Your gut contains a complete nervous system — 500 million neurons, more than the spinal cord.",
          8.0, "architecture", {}),

    Scene("Enteric network",
          "It wraps the entire digestive tract in a dense mesh of sensory neurons, interneurons, and motor neurons.",
          8.0, "architecture", {}),

    Scene("Independent origin",
          "These neurons did not grow from your brain. They migrated from the neural crest during early embryonic development.",
          8.5, "neural_crest", {}),

    Scene("Long migration",
          "Neural crest cells travel from the closing neural tube down into the developing gut, building a second brain from a different source.",
          9.0, "neural_crest", {}),

    Scene("Independence",
          "The enteric nervous system can function without any input from the brain or spinal cord.",
          7.5, "reflex", {}),

    Scene("Peristaltic reflex",
          "An isolated segment of gut can coordinate peristalsis entirely on its own. Cut it free and it still moves food.",
          9.0, "reflex", {}),

    Scene("Local decision",
          "Sensory neurons detect stretch. Interneurons process the signal. Motor neurons contract the muscle downstream. All in the gut.",
          9.0, "reflex", {}),

    Scene("Serotonin factory",
          "The gut produces 95 percent of the body's serotonin — the molecule most associated with mood, well-being, and emotion.",
          8.5, "serotonin", {}),

    Scene("Mood molecule",
          "Most of the serotonin in your blood was made by enteric neurons, not by your brain.",
          7.5, "serotonin", {}),

    Scene("Gut-brain chemistry",
          "The gut synthesizes serotonin from dietary tryptophan and releases it into the bloodstream and the brain.",
          8.0, "serotonin", {}),

    Scene("The vagus highway",
          "The vagus nerve connects the gut and the brain, carrying signals in both directions.",
          7.5, "vagus", {}),

    Scene("Eighty percent ascending",
          "Eighty to ninety percent of vagal fibers carry information from the body upward to the brainstem.",
          8.0, "vagus", {}),

    Scene("Bottom-up perception",
          "Your brain does not merely command the body. It listens to the body, and most of what it hears comes from the gut.",
          9.0, "vagus", {}),

    Scene("Microbiome dialogue",
          "The gut microbiome produces neurotransmitters that enteric neurons detect and relay.",
          8.0, "microbiome", {}),

    Scene("Bacterial signaling",
          "Gut bacteria synthesize dopamine, serotonin, GABA, and other molecules that influence mood and behavior.",
          8.5, "microbiome", {}),

    Scene("Ecosystem inside",
          "Your gut hosts an ecosystem of trillions of microorganisms. They talk to your second brain, and your second brain talks to your first.",
          9.0, "microbiome", {}),

    Scene("Gut feelings are real",
          "Interoception — the perception of internal body states — carries enteric signals into conscious awareness.",
          8.5, "gut_feeling", {}),

    Scene("Insula integration",
          "The insular cortex maps the body's internal state. It is where the gut feeling becomes a felt sensation.",
          8.5, "gut_feeling", {}),

    Scene("Intuition has anatomy",
          "What we call intuition may be the enteric nervous system contributing its computation to decisions before the brain has finished processing.",
          9.0, "gut_feeling", {}),

    Scene("Enteric glia",
          "More than half of the cells in the enteric nervous system are glia — support cells that maintain neuronal health.",
          7.5, "glia", {}),

    Scene("Gut barrier",
          "Enteric glia help maintain the gut barrier and regulate inflammation. They are the immune system's interface with the enteric brain.",
          8.5, "glia", {}),

    Scene("Trophic support",
          "Glial cells release neurotrophic factors that keep enteric neurons alive and functional throughout life.",
          8.0, "glia", {}),

    Scene("Stress reshapes the gut",
          "Chronic stress alters enteric neural activity, barrier function, and gut motility.",
          8.0, "stress", {}),

    Scene("Vagal withdrawal",
          "Stress suppresses vagal tone, disconnecting the two brains and leaving the gut to operate without higher modulation.",
          8.5, "stress", {}),

    Scene("Healing the connection",
          "Restoring vagal tone through breath, movement, or social connection improves enteric function and emotional regulation.",
          9.0, "stress", {}),

    Scene("Lifelong neurogenesis",
          "Unlike most of the central nervous system, the enteric nervous system continues to generate new neurons throughout life.",
          8.5, "neurogenesis", {}),

    Scene("Continuous renewal",
          "The enteric brain is not a fixed structure. It rewires, replaces, and adapts in response to diet, experience, and injury.",
          8.5, "neurogenesis", {}),

    Scene("Two brains, one body",
          "The cephalic brain and the enteric brain are separate organs with different embryological origins, different transmitters, different functions.",
          9.0, "dual_brain", {}),

    Scene("Parallel processing",
          "They process information in parallel, communicate bidirectionally, and influence each other's development.",
          8.0, "dual_brain", {}),

    Scene("Second mind",
          "The enteric nervous system has its own sensory processing, its own reflexes, its own memory, its own capacity to learn.",
          9.0, "dual_brain", {}),

    Scene("Intelligence is distributed",
          "Intelligence is not a single organ. It is distributed throughout the body, and the body has ways of knowing the brain does not.",
          9.0, "intelligence", {}),

    Scene("Embodied cognition",
          "Cognition is not computation on abstract symbols. It is the activity of a body that senses, moves, digests, and feels.",
          8.5, "intelligence", {}),

    Scene("Listen",
          "The voice inside your chest is not a metaphor. It is a neural network with half a billion neurons speaking in the language of serotonin and peristalsis.",
          9.5, "synthesis", {}),

    Scene("Resilience",
          "The enteric nervous system repairs itself, adapts to injury, and maintains function across decades of use.",
          8.0, "resilience", {}),

    Scene("Neuroplasticity",
          "Enteric neuroplasticity is the reason dietary changes, probiotics, and behavioral interventions can reshape gut function.",
          8.5, "resilience", {}),

    Scene("Supported claims",
          "That the gut has an independent nervous system. That it produces most of the body's serotonin. That it communicates with the brain.",
          9.0, "evidence", {}),

    Scene("Emerging frontier",
          "That gut feelings are interoceptive signals reaching awareness. That the microbiome modulates mood. These are active research frontiers.",
          9.0, "evidence", {}),

    Scene("Not metaphor",
          "What traditions called the second brain or the voice in the chest is now visible as a biological organ with specific anatomy and physiology.",
          9.0, "evidence", {}),

    Scene("Closing",
          "You are not one voice. You are a chorus. The body speaks in a language older than language. It has been speaking since before there was a brain to hear it.",
          10.0, "final", {}),

    Scene("Final frame",
          "Listen to the voice inside your chest. It has been trying to tell you something.",
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
    final = OUTPUT / "voice_inside_chest.mp4"
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
        "title": "the voice inside your chest",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "gold serotonin signal-particle ascending the vagus nerve",
        "palette_roles": {
            "ink": "architectural scaffold",
            "cyan": "enteric neural signalling",
            "gold": "serotonin / gut-derived signal / microbiome message",
            "crimson": "stress / vagal withdrawal / perturbation",
            "green": "repair / trophic support / resilience",
            "violet": "higher vagal integration / brainstem relay",
            "paper": "epithelial lining / gut wall",
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
