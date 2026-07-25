#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES_ROOT = ROOT / 'frames'
SCENES_ROOT = ROOT / 'scenes'
W, H = 1280, 720
FPS = 10
DURATION = 4.8
NFRAMES = int(FPS * DURATION)
SEED = 90909

NIGHT = (18, 22, 34)
DEEP_INDIGO = (46, 56, 105)
INDIGO = (80, 92, 155)
SILVER = (192, 200, 218)
MIRROR = (215, 222, 235)
PEARL = (242, 240, 234)
WHITE = (252, 250, 246)
GOLD = (204, 162, 82)
GOLD_LIGHT = (244, 213, 136)
ROSE = (188, 110, 136)
TEAL = (95, 147, 150)
VIOLET = (124, 106, 172)
UMBER = (84, 68, 55)
SLATE = (98, 110, 132)
MIST = (170, 182, 200)
BLACK = (14, 16, 22)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b-a) * clamp(t)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1-t) ** 3


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t * t * (3 - 2 * t)


def rgba(c, a=255):
    return (*c[:3], int(a))


def recognition_ground(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0, 1, (44, 78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*4.0 + fine[..., None]*1.1
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2)/(W/2)
    dy = (yy - H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy)*18, 0, 26)
    base -= vign[..., None]
    g1 = np.exp(-(((xx-W*0.38)/(W*0.22))**2 + ((yy-H*0.36)/(H*0.28))**2)*2.6)
    g2 = np.exp(-(((xx-W*0.62)/(W*0.22))**2 + ((yy-H*0.54)/(H*0.28))**2)*2.6)
    for i in range(3):
        base[..., i] += g1*(14 if i==2 else 7) + g2*(11 if i==2 else 5)
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def draw_glow(im, xy, radius, color, alpha=145, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))


def draw_line_glow(im, pts, color, width=3, alpha=145, blur=8):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1, width*3), joint='curve')
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+70)), width=width, joint='curve')


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42, y-r*0.42, x+r*0.42, y+r*0.42), fill=rgba(outer, 145), outline=rgba(inner, 180), width=1)
    draw.ellipse((cx-r*0.42, cy-r*0.42, cx+r*0.42, cy+r*0.42), fill=rgba(inner, 120), outline=rgba(outer, 220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(SILVER, 110), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 85), width=1)
    for x, y in [(70, 70), (W-70, 70), (70, H-70), (W-70, H-70)]:
        draw_rosette(d, x, y, 22, INDIGO, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(16, 20, 31, 202), outline=rgba(SILVER, 65), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def bezier(p0, p1, p2, p3, n=100):
    pts = []
    for i in range(n):
        t = i/(n-1); u = 1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts


def partial_polyline(points, amount):
    amount = clamp(amount)
    if amount <= 0: return []
    if amount >= 1: return points
    f = amount*(len(points)-1); idx = int(f); frac = f-idx
    out = list(points[:idx+1])
    if idx+1 < len(points):
        a, b = points[idx], points[idx+1]
        out.append((lerp(a[0], b[0], frac), lerp(a[1], b[1], frac)))
    return out


def arc_points(cx, cy, rx, ry, a0, a1, n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx, cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang = math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s = 12*scale
    draw.polygon([p1,
                  (p1[0]-math.cos(ang-0.5)*s, p1[1]-math.sin(ang-0.5)*s),
                  (p1[0]-math.cos(ang+0.5)*s, p1[1]-math.sin(ang+0.5)*s)], fill=rgba(color, 230))


def dust(im, seed, n=70):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 2.3))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0, 1))
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(c, int(rng.uniform(25, 78))))
    im.alpha_composite(ov)


def draw_moire(draw, cx, cy, t, n=20, spacing=14, col=SILVER):
    for i in range(n):
        r = spacing + i * spacing
        offset = 5 * math.sin(t * 2 * math.pi + i * 0.25)
        alpha = 35 + i * 6
        draw.ellipse((cx - r + offset, cy - r*0.68 + offset*0.5,
                      cx + r + offset, cy + r*0.68 + offset*0.5),
                     outline=rgba(col, min(180, alpha)), width=1)
        draw.ellipse((cx - r - offset, cy - r*0.68 - offset*0.5,
                      cx + r - offset, cy + r*0.68 - offset*0.5),
                     outline=rgba(col, min(180, alpha)), width=1)


def mobius_path(cx, cy, rx, ry, t_phase=0.0, n=120):
    pts = []
    for i in range(n):
        u = i / (n-1)
        a = u * 2 * math.pi + t_phase
        twist = u * math.pi
        r_offset = 18 * math.cos(twist)
        x = cx + (rx + r_offset) * math.cos(a)
        y = cy + (ry + r_offset * 0.6) * math.sin(a)
        pts.append((x, y))
    return pts


def draw_mirror_arcs(d, cx, cy, r, col, progress, mirror_col=None):
    mirror_col = mirror_col or col
    a_start = -math.pi * 0.85
    a_end = math.pi * 0.85
    pts1 = arc_points(cx - 6, cy, r, r*0.66, a_start, a_end, 60)
    pts2 = arc_points(cx + 6, cy, r, r*0.66, a_start, a_end, 60)
    p1 = partial_polyline(pts1, progress)
    p2 = partial_polyline(pts2, progress)
    if len(p1) > 1:
        ImageDraw.Draw(im := Image.new('RGBA', (1,1))).polygon([])
        draw_line_glow(d.im if hasattr(d,'im') else globals().get('_last_im'), p1, col, 3, 110, 7)
        draw_line_glow(d.im if hasattr(d,'im') else globals().get('_last_im'), p2, mirror_col, 3, 90, 6)


@dataclass
class Scene:
    id: str
    title: str
    subtitle: str
    term: str
    summary: str
    mode: str
    tags: list[str]
    group: str
    technique: str
    draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 275
    draw_moire(d, cx, cy, t, 18, 13, MIRROR)
    mob = mobius_path(cx, cy, 200, 120, t*0.06, 130)
    reveal = partial_polyline(mob, smoothstep(0.04, 0.82, t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, GOLD_LIGHT, 4, 140, 8)
    for i, a in enumerate(np.linspace(0, 2*math.pi, 6, endpoint=False)):
        x = cx + math.cos(a)*196
        y = cy + math.sin(a)*118
        alpha = int(120 + 80 * math.sin(t*2*math.pi + i))
        d.ellipse((x-4, y-4, x+4, y+4), fill=rgba(GOLD, alpha))
    draw_glow(im, (cx, cy), 50, GOLD_LIGHT, 130, 16)
    d.ellipse((cx-16, cy-16, cx+16, cy+16), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'recognition: the torsion of consciousness returning to itself', font=SUB_FONT, fill=MIST, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_glow(im, (cx, cy), 70, SLATE, 80, 22)
    d.ellipse((cx-140, cy-96, cx+140, cy+96), outline=rgba(SLATE, 120), width=2)
    gap = lerp(140, 8, ease_in_out(t))
    d.arc((cx-gap-30, cy-100, cx+30, cy+100), 270, 450, fill=rgba(SLATE, 160), width=3)
    d.arc((cx-30, cy-100, cx+gap+30, cy+100), 90, 270, fill=rgba(mix(SLATE, MIST, .3), 130), width=3)
    d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=rgba(BLACK, 200), outline=rgba(SILVER, 180), width=1)
    for i in range(12):
        a = i*2*math.pi/12
        x = cx + math.cos(a)*160
        y = cy + math.sin(a)*108
        d.ellipse((x-3, y-3, x+3, y+3), fill=rgba(mix(SLATE, BLACK, .5), 100))
    d.text((640, 510), 'self-forgetting: consciousness appears absent from itself', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    r = 160
    gap = lerp(60, 2, ease_in_out(t))
    left_col, right_col = SILVER, GOLD_LIGHT
    d.arc((cx-r-gap, cy-r*0.7, cx-r+gap, cy+r*0.7), 280, 440, fill=rgba(left_col, 190), width=4)
    d.arc((cx+r-gap, cy-r*0.7, cx+r+gap, cy+r*0.7), 100, 260, fill=rgba(right_col, 190), width=4)
    shimmer = 4 * math.sin(t * 4 * math.pi)
    for i in range(5):
        yy = cy - 60 + i*30
        d.line((cx-12+shimmer, yy, cx+12+shimmer, yy), fill=rgba(VIOLET, 80+30*i), width=1)
    draw_glow(im, (cx, cy), 36, VIOLET, 100, 14)
    d.ellipse((cx-12, cy-12, cx+12, cy+12), fill=rgba(WHITE, 255), outline=rgba(VIOLET, 220), width=2)
    d.text((380, 160), 'subject', font=SMALL_FONT, fill=SILVER, anchor='mm')
    d.text((900, 160), 'object', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((640, 510), 'the mirror relation: subject and object face each other across a gap', font=SUB_FONT, fill=MIST, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    mob = mobius_path(cx, cy, 210, 130, t*0.08, 140)
    reveal = partial_polyline(mob, smoothstep(0.05, 0.88, t))
    if len(reveal) > 1:
        twist_idx = len(reveal) // 2
        pts1 = reveal[:twist_idx]
        pts2 = reveal[twist_idx:]
        if len(pts1) > 1:
            draw_line_glow(im, pts1, SILVER, 4, 130, 7)
        if len(pts2) > 1:
            draw_line_glow(im, pts2, GOLD_LIGHT, 4, 130, 7)
    for i in range(14):
        a = i*2*math.pi/14 + t*0.06
        r = 40 + 10*math.sin(i*1.5 + t*math.pi)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        draw_glow(im, (x, y), 8, mix(SILVER, GOLD_LIGHT, (i%7)/7), 100, 5)
    draw_glow(im, (cx, cy), 44, GOLD, 120, 14)
    d.ellipse((cx-14, cy-14, cx+14, cy+14), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'the Möbius twist: the seeker discovers it is the sought', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    spiral = []
    rev_point = int(0.5 * smoothstep(0.1, 0.9, t) * 120)
    for i in range(120):
        u = i/119
        r = 30 + 200 * u
        a = -math.pi/2 + u * (4 * math.pi + math.pi * smoothstep(0.1, 0.9, t))
        if i > rev_point and rev_point > 10:
            reflected_i = rev_point - (i - rev_point)
            if reflected_i < 0: continue
            u2 = reflected_i/119
            a = -math.pi/2 + u2 * (4 * math.pi + math.pi * smoothstep(0.1, 0.9, t))
            r = 30 + 200 * u2
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.55
        if 0 <= x < W and 0 <= y < H:
            spiral.append((x, y))
    reveal = partial_polyline(spiral, ease_in_out(t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, mix(SILVER, GOLD_LIGHT, smoothstep(0.1, 0.9, t)), 3, 120, 7)
    draw_glow(im, (cx, cy), 48, GOLD_LIGHT, 130, 16)
    d.ellipse((cx-16, cy-16, cx+16, cy+16), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'the outward arc folds back: emission becomes return', font=SUB_FONT, fill=MIST, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 275
    d.rounded_rectangle((250, 130, 1030, 420), radius=18, outline=rgba(SILVER, 120), fill=rgba((20,24,40),60), width=2)
    d.line((640, 150, 640, 400), fill=rgba(SILVER, 80), width=2)
    left_items = [('Śiva', GOLD), ('prakāśa', GOLD_LIGHT), ('subject', SILVER)]
    right_items = [('Śiva', GOLD), ('prakāśa', GOLD_LIGHT), ('subject', SILVER)]
    for i, (lab, col) in enumerate(left_items):
        y = 190 + i*70
        d.rounded_rectangle((290, y-18, 590, y+18), radius=10, outline=rgba(col, 140), fill=rgba((30,34,55),50), width=1)
        d.text((440, y), lab, font=SMALL_FONT, fill=col, anchor='mm')
    for i, (lab, col) in enumerate(right_items):
        y = 190 + i*70
        d.rounded_rectangle((690, y-18, 990, y+18), radius=10, outline=rgba(col, 140), fill=rgba((30,34,55),50), width=1)
        d.text((840, y), lab, font=SMALL_FONT, fill=col, anchor='mm')
    pairs = [(0.15, GOLD), (0.35, GOLD_LIGHT), (0.55, SILVER)]
    for delay, col in pairs:
        p = smoothstep(delay, delay+0.45, t)
        if p > 0:
            d.line((595, 190 + pairs.index((delay, col))*70, 685, 190 + pairs.index((delay, col))*70),
                   fill=rgba(col, int(180*p)), width=3)
    draw_glow(im, (cx, 140), 28, GOLD_LIGHT, 100, 10)
    d.ellipse((cx-10, 128, cx+10, 152), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((640, 510), 'recognition reveals nothing new: only what was always the case', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    paths = [
        (bezier((250, 160), (400, 120), (500, 200), (cx, cy), 80), SILVER),
        (bezier((250, 400), (400, 440), (500, 360), (cx, cy), 80), GOLD_LIGHT),
        (bezier((1030, 280), (880, 200), (750, 300), (cx, cy), 80), ROSE),
    ]
    for i, (pts, col) in enumerate(paths):
        rev = partial_polyline(pts, smoothstep(0.05+i*0.08, 0.78+i*0.06, t))
        if len(rev) > 1:
            draw_line_glow(im, rev, col, 4, 120, 7)
            draw_arrowhead(d, rev[-2], rev[-1], col, 0.9)
    draw_glow(im, (cx, cy), 56, GOLD_LIGHT, 135, 18)
    d.ellipse((cx-18, cy-18, cx+18, cy+18), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((330, 150), 'pramātṛ', font=SMALL_FONT, fill=SILVER, anchor='mm')
    d.text((330, 380), 'prameya', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((980, 150), 'pramāṇa', font=SMALL_FONT, fill=ROSE, anchor='mm')
    d.text((640, 510), 'the three factors of knowing converge into one act of recognition', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    for i in range(8):
        a = i*2*math.pi/8 + t*0.03
        rx = 60 + i*24
        ry = 36 + i*14
        col = mix(INDIGO, GOLD_LIGHT, i/8)
        draw_moire(d, cx, cy, t+i*0.1, 6, rx/3, col)
    mob = mobius_path(cx, cy, 230, 145, -t*0.05, 140)
    reveal = partial_polyline(mob, smoothstep(0.05, 0.9, t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, GOLD, 4, 135, 8)
    for i in range(24):
        a = -math.pi/2 + i*2*math.pi/24 + t*0.06
        r = 160 + 30 * math.sin(i*1.3 + t*math.pi)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        d.ellipse((x-3, y-3, x+3, y+3), fill=rgba(mix(GOLD, SILVER, (i%8)/8), 180))
    draw_glow(im, (cx, cy), 60, GOLD_LIGHT, 145, 20)
    d.ellipse((cx-20, cy-20, cx+20, cy+20), fill=rgba(WHITE, 255), outline=rgba(GOLD, 225), width=2)
    d.text((cx, cy), 'प्रत्यभिज्ञा', font=DEVA_MED, fill=GOLD, anchor='mm')
    d.text((640, 510), 'the seal of recognition: self-luminous consciousness returning to itself', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('pr01', 'The Recognition Field', 'Consciousness folding back upon itself.', 'Pratyabhijñā-kṣetra', 'Recognition is the torsion of consciousness returning to its own source.', 'overview_mobius', ['recognition','overview','self'], 'overview', 'moiré field with Möbius ribbon', sc01),
    Scene('pr02', 'Self-Forgetting', 'The state before recognition, where the self seems absent.', 'Vismṛti', 'Consciousness appears to be separated from itself.', 'self_forgetting', ['forgetting','absence','gap'], 'absence', 'broken ring with shrinking gap', sc02),
    Scene('pr03', 'The Mirror', 'Subject and object face each other across a shimmering boundary.', 'Darpaṇa', 'The mirror relation: a shared boundary that belongs to both sides.', 'mirror_relation', ['mirror','subject','object'], 'relation', 'two facing arcs with shimmer', sc03),
    Scene('pr04', 'The Twist', 'The torsion where seeker becomes the sought.', 'Möbius', 'The topological twist of recognition: the inside becomes the outside.', 'mobius_twist', ['twist','reversal','topology'], 'reversal', 'Möbius strip with color shift at twist point', sc04),
    Scene('pr05', 'The Return', 'The outward arc of manifestation folds back.', 'Āvṛtti', 'Recognition is not a new act but the reversal of the outgoing movement.', 'fold_return', ['return','fold','arc'], 'return', 'outward spiral folding back', sc05),
    Scene('pr06', 'Nothing New', 'Recognition uncovers what was always the case.', 'Pūrṇatā', 'No new content is acquired; only the quality of awareness changes.', 'no_change', ['fullness','recognition','identity'], 'identity', 'side-by-side comparison of identical fields', sc06),
    Scene('pr07', 'Three in One', 'Knower, known, and knowing converge in a single act.', 'Pramātṛ-pramāṇa-prameya', 'The three factors of cognition resolve into one recognition.', 'triple_convergence', ['trika','convergence','three factors'], 'convergence', 'three converging bezier arcs', sc07),
    Scene('pr08', 'The Pratyabhijñā Seal', 'Self-luminous consciousness returning to itself.', 'Pratyabhijñā-cakra', 'The closing seal: recognition as the sole act of consciousness.', 'closing_seal', ['seal','recognition','self-luminosity'], 'seal', 'moiré rings with central Möbius seal', sc08),
]


def render_scene(scene: Scene):
    sdir = FRAMES_ROOT / scene.id
    sdir.mkdir(parents=True, exist_ok=True)
    expected = [sdir / f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size > 1000 for p in expected):
        for i, path in enumerate(expected):
            if path.exists() and path.stat().st_size > 1000:
                continue
            t = i / max(1, NFRAMES-1)
            im = recognition_ground(SEED + hash(scene.id)%10000 + i)
            border(im)
            dust(im, SEED+i, 60)
            scene.draw_fn(im, t)
            footer(im, scene.title, scene.subtitle, scene.term)
            im.convert('RGB').save(path, quality=95)
    out = SCENES_ROOT / f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size < 30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)], check=True)


def make_contact_sheet():
    thumbs = []
    for sc in SCENES:
        frame = FRAMES_ROOT / sc.id / f'frame_{int(NFRAMES*0.72):04d}.jpg'
        im = Image.open(frame).convert('RGB').resize((320,180), Image.Resampling.LANCZOS)
        thumbs.append(im)
    sheet = Image.new('RGB', (4*320, 2*180), color=NIGHT)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Pratyabhijñā: The Act of Recognition',
        'source_basis': 'Tantrāloka / Trika epistemology of recognition (pratyabhijñā) as the self-return of consciousness.',
        'style': {
            'family': 'mirror-topological contemplative field',
            'background': 'deep indigo night with double glow',
            'ink': 'silver and mist',
            'accent': 'gold, violet, rose, gold-light',
            'materials': ['moiré interference','Möbius ribbons','mirror arcs','self-similar rings','convergence paths']
        },
        'fps': FPS, 'resolution': [W, H], 'scene_duration_seconds': DURATION,
        'total_scenes': len(SCENES), 'total_duration_seconds': round(len(SCENES)*DURATION, 2),
        'scenes': [
            {'id': sc.id, 'title': sc.title, 'subtitle': sc.subtitle, 'mode': sc.mode,
             'summary': sc.summary, 'group': sc.group, 'technique_notes': sc.technique,
             'tags': sc.tags, 'duration_seconds': DURATION, 'output_filename': f'scenes/{sc.id}.mp4'}
            for sc in SCENES
        ]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    catalog = {
        'ids': [sc.id for sc in SCENES],
        'titles': {sc.id: sc.title for sc in SCENES},
        'modes': {sc.id: sc.mode for sc in SCENES},
        'theme_clusters': {
            'overview_and_absence': ['pr01', 'pr02'],
            'relation_and_reversal': ['pr03', 'pr04'],
            'return_and_identity': ['pr05', 'pr06'],
            'convergence_and_seal': ['pr07', 'pr08']
        },
        'reusability_notes': {
            'pr01': 'Use for recognition as self-return or the torsion structure of awareness.',
            'pr02': 'Use for self-forgetting, spiritual ignorance, or the sense of absence.',
            'pr03': 'Use for subject-object structure, the mirror relation, or epistemic duality.',
            'pr04': 'Use for the reversal of direction, topological transformation, or gnostic twist.',
            'pr05': 'Use for the return movement, the fold, or manifestation turning back to source.',
            'pr06': 'Use for the non-accretive nature of recognition, or pūrṇatā (fullness).',
            'pr07': 'Use for the three factors of knowing resolving into one act.',
            'pr08': 'Use as a closing seal for recognition-based or self-luminosity packs.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Pratyabhijñā: The Act of Recognition

## Aim
This pack visualizes the Trika epistemology of recognition (pratyabhijñā): the act by which consciousness returns to itself, not as a new cognition but as the self-luminosity of awareness.

## Core doctrine
1. **Self-forgetting (vismṛti)** — consciousness appears absent from itself; subject and object seem separate.
2. **The mirror relation** — what appears as a gap between subject and object is actually a shared boundary.
3. **The Möbius twist** — the torsion where inside becomes outside, seeker becomes sought.
4. **The return (āvṛtti)** — the outgoing movement of manifestation folds back.
5. **No new content** — recognition acquires nothing; only the quality of awareness changes.
6. **Triple convergence** — knower, known, and knowing are one act.

## Visual rules
- The Möbius strip is the master topological metaphor: one surface, one edge, yet appearing as two.
- Moiré interference represents the shimmer of recognition — two patterns whose interaction creates a third.
- Mirror arcs that almost touch: the gap is the condition of appearance; its closing is recognition.
- The pack should feel like a topological transformation, not a linear narrative.

## New motifs
- moiré interference fields
- parametric Möbius ribbons
- broken-ring forgetting diagram
- mirror arcs with shimmer boundary
- outward-to-return folding spiral
- side-by-side identity comparison
- triple convergence paths
- moiré-Möbius closing seal

## Material vocabulary
- deep indigo double-glow field
- silver mirror surfaces
- gold recognition-light
- violet shimmer boundary
- rose witness factor
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Pratyabhijñā Pack

## Differentiation
This pack introduces topological and interference-based visual language that breaks from the purely geometric-diagrammatic tradition of earlier packs.

## New symbols
1. moiré interference field — two patterns whose interaction reveals a third
2. parametric Möbius ribbon — one surface with one edge, twisted
3. broken ring with shrinking gap — self-forgetting as annular absence
4. mirror arcs with shimmer — subject and object sharing a boundary
5. outward-to-return folding spiral — the emission that reverses direction
6. side-by-side identity panels — the same content, different quality
7. three converging bezier paths — the three factors becoming one
8. moiré-Möbius closing seal — self-luminosity as interference pattern

## New relationships
- forgetting → gap
- mirror relation → shared boundary
- subject × object → Möbius twist
- outward arc → fold → return
- three factors → one act
- interference pattern → recognition field

## Material vocabulary
- deep indigo with double luminous source
- silver mirror quality
- gold recognition-light
- violet shimmer boundaries

## Distinct closing seal
A moiré interference field centered on a Möbius ribbon with radiating recognition-light.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — Pratyabhijñā: The Act of Recognition Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total runtime: {len(SCENES)*DURATION/60:.2f} min

Run:
```bash
python render_pack.py
```
Resume-safe.
'''
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'pratyabhijna_recognition_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'pratyabhijna_recognition_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['pratyabhijna_recognition_animation.mp4','contact_sheet.jpg',
                     'scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md',
                     'STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):
            zf.write(mp4, arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, flush=True)
        render_scene(sc)
    concat_file = ROOT / 'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT / 'pratyabhijna_recognition_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
