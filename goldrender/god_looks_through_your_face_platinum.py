#!/usr/bin/env python3
"""
GOD LOOKS THROUGH YOUR FACE
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/05_god_looks_through_your_face.md

DESIGN CONTRACT
---------------
• Every shot lasts 4-8 seconds.
• Every shot visibly performs the narrated operation.
• Clean parchment-white field; concept-led color only.
• No static slide layouts and no decorative loops.
• Ivory = ground of manifestation / the receptive field
• Gold = divine disclosure / theophanic light
• Silver = the mirror surface / reflection
• Rose = the human face / finite disclosure
• Crimson = distortion / egoic claim / the dust on the mirror
• Teal = the beloved / the other as mirror
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: the gold thread of divine light persists across chapters.

OUTPUT
------
output_god_looks/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  god_looks_through_your_face.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.

USAGE
-----
python god_looks_through_your_face_platinum.py
python god_looks_through_your_face_platinum.py --preview
python god_looks_through_your_face_platinum.py --scene 8
"""

from __future__ import annotations

import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_god_looks"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS = 1280, 720, 10

IVORY = (248, 245, 239); PAPER = (242, 239, 232); WHITE = (252, 251, 248)
INK = (30, 32, 36); SOFT_INK = (86, 89, 94); WARM_GREY = (164, 160, 154)
GOLD = (191, 154, 73); PALE_GOLD = (232, 216, 174); GOLD_LIGHT = (244, 224, 180)
SILVER = (180, 186, 192); PALE_SILVER = (224, 227, 229)
ROSE = (183, 113, 129); PALE_ROSE = (225, 198, 204)
CRIMSON = (158, 57, 66); PALE_CRIMSON = (229, 193, 197)
TEAL = (67, 157, 180); PALE_TEAL = (196, 226, 231)
LAPIS = (56, 76, 124); VIOLET = (130, 104, 160); PALE_VIOLET = (206, 196, 216)
DARK = (24, 27, 32)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float: return max(lo, min(hi, x))
def lerp(a: float, b: float, t: float) -> float: return a + (b - a) * clamp(t)
def mix(a: tuple[int,int,int], b: tuple[int,int,int], t: float) -> tuple[int,int,int]:
    t = clamp(t); return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))
def smoothstep(a: float, b: float, x: float) -> float:
    if a == b: return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a)); return q * q * (3.0 - 2.0 * q)
def ease(t: float) -> float: t = clamp(t); return 0.5 - 0.5 * math.cos(math.pi * t)
def ease_out(t: float) -> float: t = clamp(t); return 1.0 - (1.0 - t) ** 3
def pulse(t: float, hz: float = 1.0, phase: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin(math.tau * (hz * t + phase))

def load_font(path: str, size: int) -> ImageFont.ImageFont:
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try: return ImageFont.truetype(candidate, size)
        except OSError: continue
    return ImageFont.load_default()

def rgba_layer(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))

def background(width: int, height: int, seed: int, bg=IVORY) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.empty((height, width, 3), dtype=np.float32)
    arr[:] = bg
    arr += rng.normal(0, 1.15, (height, width, 1))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGB").convert("RGBA")
    edge = rgba_layer(im.size); d = ImageDraw.Draw(edge)
    for i in range(14):
        alpha = int(i * 0.7); inset = 20 + i * 3
        d.rounded_rectangle((inset, inset, width-inset, height-inset), radius=16,
                            outline=(*INK, alpha), width=2)
    im.alpha_composite(edge)
    return im

def centered_text(draw: ImageDraw.ImageDraw, xy: tuple[float,float], text: str,
                   font: ImageFont.ImageFont, fill=INK) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor="mm")

def seal(im: Image.Image, title: str, subtitle: str = "", color=INK) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    tf = load_font(FONT_SERIF_BOLD, max(20, int(h * 0.038)))
    sf = load_font(FONT_SANS, max(11, int(h * 0.018)))
    centered_text(d, (w/2, h*0.875), title, tf, color)
    if subtitle: centered_text(d, (w/2, h*0.925), subtitle, sf, SOFT_INK)

def border(im: Image.Image) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    d.rounded_rectangle((25, 25, w-25, h-25), radius=17, outline=(*INK, 40), width=1)

def glow_circle(im: Image.Image, cx: float, cy: float, radius: float,
                color: tuple[int,int,int], alpha: int = 180, blur: int = 18) -> None:
    layer = rgba_layer(im.size); d = ImageDraw.Draw(layer)
    d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(*color, alpha))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))

def glow_line(im: Image.Image, points: list[tuple[float,float]],
              color: tuple[int,int,int], width: int = 4, glow: int = 14,
              alpha: int = 225) -> None:
    if len(points) < 2: return
    layer = rgba_layer(im.size); d = ImageDraw.Draw(layer)
    d.line(points, fill=(*color, alpha), width=width, joint="curve")
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(glow)))
    im.alpha_composite(layer)

def arrow(draw: ImageDraw.ImageDraw, start: tuple[float,float], end: tuple[float,float],
          color=INK, width: int = 3, head: int = 12) -> None:
    draw.line((*start, *end), fill=color, width=width)
    angle = math.atan2(end[1]-start[1], end[0]-start[0])
    for delta in (2.55, -2.55):
        p = (end[0] + math.cos(angle + delta) * head, end[1] + math.sin(angle + delta) * head)
        draw.line((*end, *p), fill=color, width=width)

def partial_polyline(points: list[tuple[float,float]], progress: float) -> list[tuple[float,float]]:
    progress = clamp(progress)
    if len(points) < 2: return points
    lengths = [math.dist(a, b) for a, b in zip(points[:-1], points[1:])]
    total = sum(lengths); target = total * progress
    output = [points[0]]; walked = 0.0
    for i, length in enumerate(lengths):
        if walked + length <= target:
            output.append(points[i+1]); walked += length
        else:
            q = 0.0 if length == 0 else (target - walked) / length
            ax, ay = points[i]; bx, by = points[i+1]
            output.append((lerp(ax, bx, q), lerp(ay, by, q))); break
    return output

def mirror_face(im: Image.Image, cx: float, cy: float, scale: float = 1.0,
                outline_col=INK, glow_col=GOLD, show_eye=True, t=0.0) -> None:
    d = ImageDraw.Draw(im)
    s = scale
    # Face oval
    d.ellipse((cx-58*s, cy-72*s, cx+58*s, cy+68*s), outline=(*outline_col, 180), width=max(2,int(3*s)))
    # Eye
    if show_eye:
        ey = cy - 22*s
        d.arc((cx-18*s, ey-9*s, cx+6*s, ey+9*s), 200, 340, fill=(*outline_col, 190), width=max(1,int(2*s)))
        d.arc((cx-18*s, ey-9*s, cx+6*s, ey+9*s), 20, 160, fill=(*outline_col, 120), width=max(1,int(2*s)))
        d.ellipse((cx-7*s, ey-3*s, cx-1*s, ey+3*s), fill=(*outline_col, 220))
        glow_circle(im, cx, ey-1, 6, glow_col, 60, 8)
    # Smile line
    d.arc((cx-28*s, cy+12*s, cx+28*s, cy+42*s), 200, 340, fill=(*outline_col, 140), width=max(1,int(2*s)))


@dataclass
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

# =============================================================================
# VISUAL FUNCTIONS
# =============================================================================

def v_unseen_face(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.44
    # Mirror oval appearing
    progress = ease(u)
    rx = lerp(5, 115, progress); ry = lerp(5, 140, progress)
    d.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), outline=(*SILVER, int(180*progress)), width=3)
    d.arc((cx-rx*.78, cy-ry*.72, cx+rx*.78, cy+ry*.72), 200, 340, fill=(*SILVER, int(80*progress)), width=2)
    if progress > .3:
        p2 = clamp((progress-.3)/.7)
        # Face inside mirror
        mirror_face(im, cx, cy+10, .8, SILVER, GOLD, True, t)
        # Gaze lines toward viewer
        for i in range(5):
            a = -0.3 + i*0.15; x = cx + math.sin(a)*60; y = cy + 20
            line_alpha = int(60 * p2 * (1 - i/5))
            d.line((x, y, cx-20, cy-60), fill=(*PALE_GOLD, line_alpha), width=2)
    seal(im, "YOU HAVE NEVER SEEN YOUR OWN FACE", "this is a metaphysical clue")

def v_hidden_treasure(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    progress = ease(u)
    # Dark center radiating outward
    for i in range(5):
        r = 20 + i*45*progress
        alpha = int(130*(1-i/5)*progress)
        if alpha < 5: continue
        d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(*mix(SOFT_INK, GOLD, i/4), alpha), width=2)
    glow_circle(im, cx, cy, 20+40*progress, GOLD, int(60+140*progress), 20)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=(*WHITE, int(200*progress)))
    # Rays entering world
    if progress > .4:
        p2 = clamp((progress-.4)/.6)
        for i in range(10):
            a = i*2*math.pi/10 + t*.05
            x = cx + math.cos(a)*(150+30*p2)
            y = cy + math.sin(a)*(100+20*p2)
            col = mix(GOLD, PALE_GOLD, i/9)
            d.ellipse((x-4, y-4, x+4, y+4), fill=(*col, int(140*p2)))
            if i%2==0:
                d.line((cx+math.cos(a)*30, cy+math.sin(a)*30, x, y), fill=(*col, int(60*p2)), width=2)
    seal(im, "I WAS A HIDDEN TREASURE WHO DESIRED TO BE KNOWN", "— Ibn Arabi")

def v_creation_mirror(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Central mirror
    d.ellipse((cx-90, cy-70, cx+90, cy+80), outline=(*GOLD, int(180*progress)), width=3)
    mirror_face(im, cx, cy+5, .9, GOLD, GOLD, True, t)
    # Radiating divine names
    names = [("THE LION", "power", CRIMSON), ("THE MOTHER", "mercy", ROSE),
             ("THE JUDGE", "justice", LAPIS), ("THE NIGHT", "hiddenness", VIOLET),
             ("THE DAWN", "unveiling", TEAL)]
    for i, (title, subt, col) in enumerate(names):
        a = -math.pi/2 + i*2*math.pi/5
        x = cx + math.cos(a)*210; y = cy + math.sin(a)*155
        q = clamp(progress*1.4 - i*0.06)
        if q <= 0: continue
        d.rounded_rectangle((x-70, y-24, x+70, y+24), radius=12, outline=(*col, int(170*q)),
                            fill=(*mix(IVORY, col, .06), int(200*q)), width=2)
        centered_text(d, (x, y-5), title, load_font(FONT_SANS_BOLD, int(h*.017)), col)
        centered_text(d, (x, y+18), subt, load_font(FONT_SANS, int(h*.014)), SOFT_INK)
        d.line((cx, cy+5, x, y), fill=(*col, int(80*q)), width=2)
    seal(im, "THE WORLD IS A MIRROR", "every creature discloses a divine name")

def v_lens(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Lens shape
    d.ellipse((cx-55, cy-30, cx+55, cy+30), outline=(*SILVER, int(180*progress)), width=3)
    d.arc((cx-55, cy-30, cx+55, cy+30), 200, 340, fill=(*SILVER, int(60*progress)), width=2)
    # Light source above
    if progress > .15:
        p2 = clamp((progress-.15)/.85)
        glow_circle(im, cx, cy-130, 30, GOLD, int(180*p2), 24)
        lineglow = d.line([(cx, cy-95), (cx, cy-35)], fill=(*PALE_GOLD, int(160*p2)), width=6)
    # Dispersion below
    if progress > .55:
        p3 = clamp((progress-.55)/.45)
        for i in range(5):
            a = -0.4 + i*0.2
            x = cx + math.sin(a)*110; y = cy + 35 + math.cos(a)*40
            col = mix(GOLD, mix(ROSE, TEAL, i/4), .3)
            d.line([(cx+math.sin(a)*30, cy+28), (x, y)], fill=(*col, int(120*p3)), width=3)
            d.ellipse((x-5, y-5, x+5, y+5), fill=(*col, int(160*p3)))
    seal(im, "THE FINITE PERSON IS A LENS", "the light is older")

def v_polished_mirror(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Mirror surface
    d.rounded_rectangle((cx-105, cy-65, cx+105, cy+75), radius=18,
                        outline=(*SILVER, int(190*progress)), width=3)
    # Polishing arcs
    glow_circle(im, cx+35, cy-8, 12, PALE_GOLD, int(80*progress), 10)
    for i in range(4):
        r = 50 + i*18
        a_end = int(360 * progress * (i+1)/4)
        d.arc((cx-r, cy-r*.6, cx+r, cy+r*.6), i*20, a_end,
              fill=(*mix(SILVER, GOLD, i/3), int(100*progress)), width=3)
    # Dust falling away
    for i in range(12):
        a = i*2*math.pi/12; r = 70 + 40*(1-progress)
        x = cx + math.cos(a)*r; y = cy + math.sin(a)*r*.6
        alpha = int(80*(1-progress))
        d.ellipse((x-2, y-2, x+2, y+2), fill=(*WARM_GREY, alpha))
    if progress > .6:
        mirror_face(im, cx+5, cy+5, .7, mix(SILVER, GOLD, .3), GOLD, True, t)
    seal(im, "THE POLISHED MIRROR", "transparency does not remove individuality — it removes opacity")

def v_other_mirror(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Two faces facing each other
    for side in (-1, 1):
        x = cx + side*115
        col = ROSE if side < 0 else TEAL
        mirror_face(im, x, cy, .75, col, GOLD, True, t)
        centered_text(d, (x, cy+75), ["self", "other"][side>0],
                      load_font(FONT_SANS_BOLD, int(h*.018)), col)
    # Gaze between them
    if progress > .2:
        p2 = clamp((progress-.2)/.8)
        for i in range(5):
            y = cy - 25 + i*12
            d.line((cx-55, y, cx+55, y), fill=(*GOLD, int(60*p2*(1-i/5))), width=2)
    # Central glow — recognition
    if progress > .6:
        p3 = clamp((progress-.6)/.4)
        glow_circle(im, cx, cy, 30, GOLD, int(120*p3), 18)
        centered_text(d, (cx, cy-50), "recognition", load_font(FONT_SERIF, int(h*.022)), GOLD)
        centered_text(d, (cx, cy+95), "a mirror cannot see dust on its own surface",
                      load_font(FONT_SANS, int(h*.016)), SOFT_INK)
    seal(im, "THE OTHER REVEALS THE FACE YOU CANNOT SEE", "love is a dangerous spiritual practice")

def v_remembrance(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(t * 0.3) if False else ease(u)
    # Mirror tilting toward light
    angle = lerp(0, math.pi/6, progress)
    pts = [(cx-50,cy-35),(cx+50,cy-35),(cx+50,cy+35),(cx-50,cy+35)]
    rot = [(cx + (x-cx)*math.cos(angle) - (y-cy)*math.sin(angle),
            cy + (x-cx)*math.sin(angle) + (y-cy)*math.cos(angle)) for x,y in pts]
    d.polygon(rot, outline=(*SILVER, int(190*progress)), width=2)
    # Light beam from upper right
    if progress > .15:
        p2 = clamp((progress-.15)/.85)
        sx, sy = cx+140, cy-140
        mx = cx + 40*math.sin(angle)
        my = cy - 35*math.cos(angle)
        d.line([(sx, sy), (mx, my)], fill=(*PALE_GOLD, int(140*p2)), width=5)
        glow_circle(im, sx, sy, 20, GOLD, int(120*p2), 18)
    # Reflection beam downward
    if progress > .35:
        p3 = clamp((progress-.35)/.65)
        rx = cx - 50*math.sin(angle)
        ry = cy + 35*math.cos(angle)
        d.line([(mx, my), (rx, ry+160)], fill=(*PALE_GOLD, int(80*p3)), width=3)
    seal(im, "REMEMBRANCE", "the mirror turns toward the light — the name repeated until it no longer feels like an object")

def v_the_gaze(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Face-mandala emerging
    for side in (-1, 1):
        pts = []
        for i in range(20):
            q = i/19; y = cy - 80 + q*160
            x = cx + side*(20 + 55*q*(1-q))
            pts.append((x, y))
        reveal = partial_polyline(pts, progress)
        if len(reveal) > 1:
            glow_line(im, reveal, mix(GOLD, PALE_GOLD, .3), 3, 10, 180)
    # The eye that sees and is seen
    glow_circle(im, cx, cy, 25, GOLD, int(150*progress), 18)
    d.arc((cx-18, cy-8, cx+6, cy+10), 200, 340, fill=(*IVORY, int(200*progress)), width=3)
    d.arc((cx-18, cy-8, cx+6, cy+10), 20, 160, fill=(*IVORY, int(120*progress)), width=2)
    d.ellipse((cx-6, cy-2, cx+1, cy+4), fill=(*IVORY, int(220*progress)))
    # Light entering and leaving
    if progress > .25:
        p2 = clamp((progress-.25)/.75)
        d.line([(cx, cy-130), (cx, cy-30)], fill=(*PALE_GOLD, int(120*p2)), width=5)
        glow_circle(im, cx, cy-130, 22, GOLD, int(140*p2), 20)
    if progress > .55:
        p3 = clamp((progress-.55)/.45)
        for i in range(8):
            a = i*2*math.pi/8; r = 85 + 50*p3
            x = cx + math.cos(a)*r; y = cy + math.sin(a)*r*.6
            d.ellipse((x-4, y-4, x+4, y+4), fill=(*mix(GOLD, WHITE, i/7), int(150*p3)))
    seal(im, "GOD LOOKS THROUGH YOUR FACE", "the light does not cease because the reflection is imperfect")

def v_distortion(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Mirror with cracks and dust
    d.rounded_rectangle((cx-100, cy-70, cx+100, cy+70), radius=16,
                        outline=(*SILVER, int(180*progress)), width=3)
    # Cracks appearing
    if progress > .15:
        for i in range(4):
            q = clamp((progress-.15)*3 - i*.12)
            if q <= 0: continue
            angle = 0.3 + i*0.8; length = 30 + i*15
            x1 = cx + math.cos(angle)*60; y1 = cy + math.sin(angle)*40
            x2 = x1 + math.cos(angle+0.5)*length; y2 = y1 + math.sin(angle+0.5)*length
            d.line([(x1,y1), (x2,y2)], fill=(*CRIMSON, int(160*q)), width=2)
    # Dust spots
    for i in range(15):
        a = i*2*math.pi/15; r = 30 + i*4*progress
        x = cx + math.cos(a)*r; y = cy + math.sin(a)*r*.6
        d.ellipse((x-2, y-2, x+2, y+2), fill=(*WARM_GREY, int(80*progress)))
    if progress > .7:
        glow_circle(im, cx, cy, 15, GOLD, 100, 12)
    seal(im, "THE DUST ON THE MIRROR", "habitual self-reference — the need to own every virtue")

def v_signs(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Signs as icons radiating
    signs = [("storm", CRIMSON), ("child", ROSE), ("animal", TEAL), ("stranger", GOLD)]
    for i, (lab, col) in enumerate(signs):
        a = -math.pi/2 + i*2*math.pi/4
        x = cx + math.cos(a)*180; y = cy + math.sin(a)*130
        q = clamp(progress*1.5 - i*0.1)
        if q <= 0: continue
        d.rounded_rectangle((x-52, y-28, x+52, y+28), radius=14,
                            outline=(*col, int(170*q)), fill=(*mix(IVORY, col, .05), int(200*q)), width=2)
        centered_text(d, (x, y), lab, load_font(FONT_SERIF_BOLD, int(h*.020)), col)
        d.line([(cx, cy), (x, y)], fill=(*col, int(80*q)), width=2)
    glow_circle(im, cx, cy, 22, GOLD, 150, 16)
    centered_text(d, (cx, cy+80), "a sign is not the destination", load_font(FONT_SANS, int(h*.017)), SOFT_INK)
    seal(im, "THE WORLD IS COMPOSED OF SIGNS", "each points beyond itself while remaining fully present")

def v_polishing(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Circular polishing motion
    for i in range(3):
        r = 40 + i*25
        d.arc((cx-r, cy-r*.6, cx+r, cy+r*.6), int(i*30), int(i*30 + 360*progress),
              fill=(*mix(SILVER, GOLD, i/2), int(100*progress)), width=4)
    # Mirror brightening
    glow_circle(im, cx, cy, 20+30*progress, GOLD, int(60+100*progress), 16)
    d.rounded_rectangle((cx-90, cy-55, cx+90, cy+55), radius=14,
                        outline=(*mix(SILVER, GOLD, progress), int(180*progress)), width=3)
    if progress > .7:
        centered_text(d, (cx, cy), "the mirror is not the sun",
                      load_font(FONT_SERIF, int(h*.021)), GOLD)
    seal(im, "POLISHING IS MAINTENANCE, NOT SELF-HATRED", "you are a surface capable of receiving and reflecting light")

def v_terror_intimacy(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # The private self dissolving into transparency
    d.ellipse((cx-80, cy-70, cx+80, cy+70), outline=(*SOFT_INK, int(160*(1-progress))), width=3)
    # Transparent overlay emerging
    if progress > .3:
        p2 = clamp((progress-.3)/.7)
        d.ellipse((cx-90, cy-80, cx+90, cy+80), outline=(*GOLD, int(160*p2)), width=3)
        d.ellipse((cx-75, cy-65, cx+75, cy+65), fill=(*mix(IVORY, PALE_GOLD, .15), int(60*p2)))
    # Light becoming visible through the person
    if progress > .5:
        p3 = clamp((progress-.5)/.5)
        for i in range(6):
            a = -math.pi/2 + i*2*math.pi/6
            x = cx + math.cos(a)*(100+30*p3); y = cy + math.sin(a)*(80+25*p3)
            d.line([(cx, cy), (x, y)], fill=(*GOLD, int(100*p3)), width=3)
            d.ellipse((x-5, y-5, x+5, y+5), fill=(*PALE_GOLD, int(150*p3)))
    seal(im, "EVERY ACT BECOMES A PLACE OF DISCLOSURE",
         "how you use power — how you meet weakness — how you speak unobserved — reveals the condition of the mirror")

def v_love_as_worship(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # Two figures — one holding light, the other bowing
    left_x, right_x = cx-120, cx+120
    # Left: the lamp
    glow_circle(im, left_x, cy-20, 22, GOLD, 180, 18)
    d.ellipse((left_x-18, cy-50, left_x+18, cy-22), fill=(*PALE_GOLD, 220))
    d.line([(left_x, cy-20), (left_x, cy+10)], fill=(*INK, 160), width=3)
    d.line([(left_x-8, cy+10), (left_x+8, cy+10)], fill=(*INK, 160), width=2)
    # Right: the worshipper (abstract figure)
    if progress > .2:
        p2 = clamp((progress-.2)/.8)
        d.arc((right_x-50, cy-70, right_x+50, cy+10), 0, 180,
              fill=(*INK, int(140*p2)), width=3)
        d.line([(right_x, cy-30), (right_x, cy+40)], fill=(*INK, int(140*p2)), width=3)
        d.line([(right_x, cy+40), (right_x-30, cy+75)], fill=(*INK, int(120*p2)), width=2)
        d.line([(right_x, cy+40), (right_x+30, cy+75)], fill=(*INK, int(120*p2)), width=2)
    # Beam from lamp to worshipper
    if progress > .35:
        p3 = clamp((progress-.35)/.65)
        d.line([(left_x+18, cy-20), (right_x-30, cy-20)], fill=(*PALE_GOLD, int(100*p3)), width=3)
    seal(im, "YOU BOW TO THE LIGHT — YOU DO NOT SEIZE THE LAMP",
         "the beloved is not merely a symbol — what shines through them exceeds both of you")

def v_closing(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size; d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    progress = ease(u)
    # The gold thread of continuity — now fully manifest
    for i in range(4):
        r = 30 + i*52
        col = mix(GOLD, SILVER, i/3)
        d.ellipse((cx-r, cy-r*.6, cx+r, cy+r*.6), outline=(*col, int(140-25*i)), width=3-i)
    glow_circle(im, cx, cy, 30, GOLD, 200, 24)
    d.ellipse((cx-12, cy-12, cx+12, cy+12), fill=(*WHITE, 255), outline=(*GOLD, 220), width=2)
    # The face as threshold — light both enters and exits
    mirror_face(im, cx, cy, .8, mix(GOLD, WHITE, .3), GOLD, True, t)
    for i in range(14):
        a = i*2*math.pi/14 + t*.03; r = 170 + 20*pulse(t, .5, i)
        x = cx + math.cos(a)*r; y = cy + math.sin(a)*r*.6
        col = mix(GOLD, WHITE, i/13)
        d.ellipse((x-4, y-4, x+4, y+4), fill=(*col, int(150*progress)))
    if progress > .7:
        centered_text(d, (cx, cy-100), "you have spent years asking whether the divine can be found",
                      load_font(FONT_SERIF, int(h*.020)), SOFT_INK)
        centered_text(d, (cx, cy+115), "a more unsettling question remains: what has the divine been seeing through you?",
                      load_font(FONT_SERIF, int(h*.020)), GOLD)
    seal(im, "GOD LOOKS THROUGH YOUR FACE", "the hidden treasure desires to be known — you are the mirror")

VISUALS: dict[str, Callable] = {
    "unseen_face": v_unseen_face, "hidden_treasure": v_hidden_treasure,
    "creation_mirror": v_creation_mirror, "lens": v_lens,
    "polished_mirror": v_polished_mirror, "other_mirror": v_other_mirror,
    "remembrance": v_remembrance, "the_gaze": v_the_gaze,
    "distortion": v_distortion, "signs": v_signs,
    "polishing": v_polishing, "terror_intimacy": v_terror_intimacy,
    "love_as_worship": v_love_as_worship, "closing": v_closing,
}

SCENES: list[Scene] = [
    Scene("The Unseen Face","You have never seen your own face directly.",5.5,"unseen_face",{}),
    Scene("Metaphysical Clue","You have seen mirrors, reflections in dark windows, the reactions of other people.",5.0,"unseen_face",{}),
    Scene("The Face You Cannot Encounter","The face by which the world knows you is the one face you can never encounter without mediation.",5.5,"unseen_face",{}),
    Scene("A Metaphysical Clue","This is more than a biological inconvenience — it is a metaphysical clue.",5.0,"unseen_face",{}),
    Scene("Consciousness Requires Another Face","Perhaps consciousness requires another face in order to see itself.",5.0,"unseen_face",{}),
    Scene("Hidden Treasure","Ibn Arabi: I was a hidden treasure who desired to be known.",6.0,"hidden_treasure",{}),
    Scene("Creation as Disclosure","Creation gives those possibilities form — the world becomes a mirror.",5.5,"creation_mirror",{}),
    Scene("The Names Acquire Faces","The hidden names of God acquire faces, histories, conflicts, colors, voices.",5.5,"creation_mirror",{}),
    Scene("Knowledge Becoming Experience","Manifestation is knowledge becoming experience — the hidden treasure desires intimacy.",6.0,"hidden_treasure",{}),
    Scene("Every Creature Discloses a Name","The lion reveals power — the mother reveals mercy — the judge reveals justice.",5.5,"creation_mirror",{}),
    Scene("Infinity as Difference","To become manifest, infinity appears as difference — one being cannot display the whole.",5.5,"creation_mirror",{}),
    Scene("The Drama of Qualities","History is the drama of divine qualities learning their relations in form.",5.0,"creation_mirror",{}),
    Scene("You Are a Site of Disclosure","The qualities appearing through you belong to a depth greater than the personality.",5.5,"lens",{}),
    Scene("The Lens","The finite person is a lens — the light is older.",5.5,"lens",{}),
    Scene("The Dignity of Individuality","A lens does not produce light, but it gives light a particular path.",5.5,"lens",{}),
    Scene("The Mirror Can Distort","Mercy through one person becomes indulgence — power becomes protection or domination.",6.0,"distortion",{}),
    Scene("The Polished Mirror","Ibn Arabi called the complete human the polished mirror — transparent enough that the divine appears.",6.0,"polished_mirror",{}),
    Scene("Polishing Removes Opacity","Polishing does not remove individuality — it removes opacity.",5.5,"polished_mirror",{}),
    Scene("A Face That Does Not Block","Perfection is becoming a face that does not block the light it reveals.",5.5,"polished_mirror",{}),
    Scene("Why Self-Knowledge Is Difficult","The ego examines itself using the very distortions it is trying to detect.",5.5,"distortion",{}),
    Scene("The Mirror Needs Relation","A mirror cannot easily see the dust on its own surface — it needs relation.",5.5,"other_mirror",{}),
    Scene("Love Is Dangerous","The beloved becomes a mirror charged with enormous force.",5.5,"other_mirror",{}),
    Scene("Dormant Possibilities Awaken","Beauty arrives from outside — longing follows — but the capacity was already within you.",6.0,"other_mirror",{}),
    Scene("The Ego Confuses Mirror with Light","The ego confuses the mirror with the light — you try to own the glass.",5.5,"distortion",{}),
    Scene("Love More Truthfully","To love more truthfully is to recognize the source without reducing the person to an instrument.",6.0,"love_as_worship",{}),
    Scene("The Transparency of Sacred Art","An icon is not valuable because wood and pigment are secretly divine.",5.0,"polished_mirror",{}),
    Scene("The Worshipper Is Seen","The image looks back — the worshipper is seen through the very act of seeing.",5.5,"the_gaze",{}),
    Scene("The Shock of Being Truly Seen","For one moment, another's attention reaches beneath the performed identity.",5.5,"the_gaze",{}),
    Scene("The Infinite Gaze","One finite face becomes the place where the infinite gaze arrives.",5.5,"the_gaze",{}),
    Scene("Signs on the Horizons","The world is composed of signs — a storm displays majesty, a child's trust displays innocence.",6.0,"signs",{}),
    Scene("Reading the World Spiritually","To read spiritually is to perceive the depth operating through particularity.",5.5,"signs",{}),
    Scene("The Polished Heart Distinguishes","The polished heart distinguishes between real meaning and narcissistic interpretation.",5.5,"polishing",{}),
    Scene("Humility Is Accurate Scale","You are neither the whole sun nor a meaningless piece of dust.",5.0,"polishing",{}),
    Scene("Clean the Mirror, Do Not Worship It","Clean the mirror — do not worship it — do not smash it because it is not the sun.",5.5,"polishing",{}),
    Scene("What Is the Dust?","Habitual self-reference — the need to own every virtue — resentment that darkens.",5.5,"distortion",{}),
    Scene("Dust Gathers on Any Surface","Dust gathers on surfaces exposed to a world — polishing is maintenance, not self-hatred.",5.0,"polishing",{}),
    Scene("Remembrance Interrupts Monopoly","The repeated divine name interrupts the monopoly of the personal name.",6.0,"remembrance",{}),
    Scene("Another Center","Remembrance introduces another center — the name repeated until it no longer feels like an object.",6.0,"remembrance",{}),
    Scene("The Mirror Turns Toward Light","At first you remember God — later, it may seem that God remembers God through you.",6.5,"remembrance",{}),
    Scene("The Terror of Intimacy","If God sees through your face, your life is not private in the way the ego imagines.",6.0,"terror_intimacy",{}),
    Scene("Every Act Becomes Disclosure","How you use power reveals a name — how you meet weakness reveals a name.",5.5,"terror_intimacy",{}),
    Scene("Wisdom Is Proportion","No single divine quality can govern every situation — wisdom is the right name at the right intensity.",6.0,"creation_mirror",{}),
    Scene("The Purpose Is Availability","A mirror obsessed with its own cleanliness reflects nothing — the purpose is availability.",5.5,"polished_mirror",{}),
    Scene("Identity Is Relational","Perhaps identity is inherently relational — the face exists to be offered to another gaze.",5.5,"other_mirror",{}),
    Scene("The Light Seeks a Surface","The hidden seeks form — the light seeks a surface — the surface seeks the light it carries.",6.0,"closing",{}),
    Scene("A Singular Angle","Reality looks back through a configuration that will never exist again.",5.5,"the_gaze",{}),
    Scene("You Are Valuable","You are valuable because existence has accepted the risk of becoming visible through your limitations.",6.0,"closing",{}),
    Scene("The Light Does Not Cease","The light does not cease because the reflection is imperfect — it waits inside the act of seeing.",6.5,"closing",{}),
    Scene("What Has the Divine Been Seeing?","What has the divine been seeing through you — and what might become visible if you stopped standing in front of the mirror?",7.0,"closing",{}),
]

def render_frame(scene: Scene, frame_index: int, frame_count: int, w: int, h: int, seed: int) -> Image.Image:
    u = frame_index / max(1, frame_count - 1)
    t = u * scene.duration
    bg = mix(IVORY, PAPER, .5)
    im = background(w, h, seed, bg)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")

def require_ffmpeg() -> str:
    if not (e := shutil.which("ffmpeg")): raise RuntimeError("ffmpeg required")
    return e

def encode_scene(idx: int, fps: int) -> Path:
    ffmpeg = require_ffmpeg()
    frame_dir = FRAMES / f"scene_{idx:03d}"
    out = SCENES_DIR / f"scene_{idx:03d}.mp4"
    subprocess.run([ffmpeg,"-y","-framerate",str(fps),"-i",str(frame_dir/"%05d.jpg"),
                    "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
                    "-movflags","+faststart", str(out)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def render_scene(idx: int, scene: Scene, fps: int, w: int, h: int, preview: bool) -> Path:
    frame_dir = FRAMES / f"scene_{idx:03d}"; frame_dir.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    nframes = max(2, round(scene.duration * fps))
    if preview:
        for out_idx, fi in enumerate([0, int(nframes*.35), int(nframes*.72), nframes-1]):
            render_frame(scene, fi, nframes, w, h, idx*1000+fi).save(frame_dir/f"preview_{out_idx:02d}.jpg", quality=95)
        return frame_dir
    for fi in range(nframes):
        p = frame_dir / f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(scene, fi, nframes, w, h, idx*1000+fi).save(p, quality=95, subsampling=0)
    return encode_scene(idx, fps)

def concat(scene_paths: list[Path]) -> Path:
    ffmpeg = require_ffmpeg()
    c = OUTPUT/"concat.txt"
    c.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_paths), encoding="utf-8")
    out = OUTPUT/"god_looks_through_your_face.mp4"
    subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(out)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def export_timeline() -> Path:
    cursor = 0.0; payload = []
    for idx,s in enumerate(SCENES,1):
        r = asdict(s); r["scene_id"] = f"scene_{idx:03d}"
        r["start_seconds"] = round(cursor,3); r["end_seconds"] = round(cursor+s.duration,3)
        payload.append(r); cursor += s.duration
    p = OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"god looks through your face","runtime_seconds":round(cursor,3),
        "scene_count":len(SCENES),"scenes":payload}, indent=2, ensure_ascii=False), encoding="utf-8")
    return p

def make_contact_sheet(w:int, h:int) -> Path:
    thumbs = []; tw, th = 320, int(320*h/w)
    for idx,s in enumerate(SCENES,1):
        nf = max(2, round(s.duration*DEFAULT_FPS))
        im = render_frame(s, int(nf*.72), nf, w, h, idx*1000+72)
        im.thumbnail((tw, th)); thumbs.append((idx, s.title, im.copy()))
    cols = 4; rows = math.ceil(len(thumbs)/cols); cell_h = th + 48
    sheet = Image.new("RGB", (cols*tw, rows*cell_h), IVORY); d = ImageDraw.Draw(sheet)
    font = load_font(FONT_SANS_BOLD, 14)
    for idx,t,im in thumbs:
        s = idx-1; x=(s%cols)*tw; y=(s//cols)*cell_h
        sheet.paste(im,(x,y)); d.text((x+8,y+th+10),f"{idx:02d}  {t}",font=font,fill=INK)
    p = OUTPUT/"contact_sheet.jpg"; sheet.save(p, quality=94); return p

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps",type=int,default=DEFAULT_FPS)
    parser.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    parser.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    parser.add_argument("--scene",type=int,default=None)
    parser.add_argument("--preview",action="store_true")
    parser.add_argument("--no-contact-sheet",action="store_true")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    for d in (OUTPUT, FRAMES, SCENES_DIR): d.mkdir(parents=True, exist_ok=True)
    tl = export_timeline(); print(f"Timeline: {tl}  |  Scenes: {len(SCENES)}  |  Runtime: {sum(s.duration for s in SCENES)/60:.2f} min")
    if args.scene:
        if not 1 <= args.scene <= len(SCENES): raise ValueError
        print(render_scene(args.scene, SCENES[args.scene-1], args.fps, args.width, args.height, args.preview))
        return
    rendered = []
    for idx, s in enumerate(SCENES, 1):
        print(f"[{idx:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r = render_scene(idx, s, args.fps, args.width, args.height, args.preview)
        if not args.preview: rendered.append(r)
    if not args.no_contact_sheet: print(f"Contact sheet: {make_contact_sheet(args.width, args.height)}")
    if not args.preview: print(f"Final: {concat(rendered)}")

if __name__ == "__main__":
    main()
