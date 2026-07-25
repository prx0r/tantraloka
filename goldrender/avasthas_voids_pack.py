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
SEED = 70707

# twilight / threshold palette
NIGHT = (21, 24, 34)
DEEP_INDIGO = (44, 55, 96)
INDIGO = (77, 94, 152)
VIOLET = (128, 110, 170)
SLATE = (110, 122, 147)
MIST = (176, 184, 201)
ASH = (205, 210, 220)
IVORY = (245, 242, 236)
WHITE = (251, 249, 246)
GOLD = (209, 167, 89)
GOLD_LIGHT = (245, 214, 142)
CORAL = (198, 102, 104)
ROSE = (190, 129, 154)
TEAL = (104, 149, 151)
SEA = (85, 126, 148)
SMOKE = (78, 81, 93)
BLACK = (15, 15, 18)
SILVER = (218, 222, 231)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def rgba(c, a=255):
    return (*c[:3], int(a))


def threshold_ground(seed: int):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0, 1, (44, 78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse - coarse.min()) / (np.ptp(coarse) + 1e-6) * 255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32) - 128) / 128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None] * 4.0 + fine[..., None] * 1.15
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2)/(W/2)
    dy = (yy - H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy) * 18, 0, 26)
    base -= vign[..., None]
    glow1 = np.exp(-(((xx-W/2)/(W*0.28))**2 + ((yy-H*0.28)/(H*0.16))**2) * 2.7)
    glow2 = np.exp(-(((xx-W/2)/(W*0.24))**2 + ((yy-H*0.62)/(H*0.22))**2) * 2.8)
    for i in range(3):
        base[..., i] += glow1 * (22 if i == 2 else 8)
        base[..., i] += glow2 * (10 if i != 2 else 18)
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def draw_glow(im, xy, radius, color, alpha=150, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im, pts, color, width=3, alpha=150, blur=8):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1, width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+70)), width=width, joint='curve')


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42, y-r*0.42, x+r*0.42, y+r*0.42), fill=rgba(outer, 150), outline=rgba(inner, 180), width=1)
    draw.ellipse((cx-r*0.42, cy-r*0.42, cx+r*0.42, cy+r*0.42), fill=rgba(inner, 120), outline=rgba(outer, 220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(MIST, 115), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 90), width=1)
    for x, y in [(70, 70), (W-70, 70), (70, H-70), (W-70, H-70)]:
        draw_rosette(d, x, y, 22, ROSE, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(19, 22, 31, 198), outline=rgba(MIST, 70), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=IVORY)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def bezier(p0, p1, p2, p3, n=100):
    pts = []
    for i in range(n):
        t = i/(n-1); u = 1-t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        pts.append((x,y))
    return pts


def partial_polyline(points, amount):
    amount = clamp(amount)
    if amount <= 0: return []
    if amount >= 1: return points
    f = amount*(len(points)-1)
    idx = int(f); frac = f-idx
    out = list(points[:idx+1])
    if idx+1 < len(points):
        a,b = points[idx], points[idx+1]
        out.append((lerp(a[0],b[0],frac), lerp(a[1],b[1],frac)))
    return out


def arc_points(cx, cy, rx, ry, a0, a1, n=90):
    return [(cx + math.cos(lerp(a0, a1, i/(n-1))) * rx, cy + math.sin(lerp(a0, a1, i/(n-1))) * ry) for i in range(n)]


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang = math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s = 12*scale
    pts = [p1,
           (p1[0]-math.cos(ang-0.5)*s, p1[1]-math.sin(ang-0.5)*s),
           (p1[0]-math.cos(ang+0.5)*s, p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts, fill=rgba(color, 230))


def dust(im, seed, n=76):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 2.3))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0,1))
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(c, int(rng.uniform(26,85))))
    im.alpha_composite(ov)


def draw_node(draw, x, y, r, outline, fill=None, label=None, font=None):
    draw.ellipse((x-r, y-r, x+r, y+r), outline=rgba(outline, 220), fill=fill or rgba((255,255,255), 28), width=2)
    if label:
        draw.text((x,y), label, font=font or SMALL_FONT, fill=IVORY, anchor='mm')


def draw_eye(draw, cx, cy, scale=1.0, col=GOLD_LIGHT):
    draw.arc((cx-72*scale, cy-34*scale, cx+72*scale, cy+34*scale), 180, 360, fill=rgba(col, 220), width=max(1,int(3*scale)))
    draw.arc((cx-72*scale, cy-34*scale, cx+72*scale, cy+34*scale), 0, 180, fill=rgba(col, 220), width=max(1,int(3*scale)))
    draw.ellipse((cx-16*scale, cy-16*scale, cx+16*scale, cy+16*scale), fill=rgba(col, 210))


def draw_crescent(draw, cx, cy, r, col):
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=rgba(col, 200), width=2)
    draw.ellipse((cx-r*0.52, cy-r, cx+r*1.48, cy+r), fill=rgba(NIGHT, 255), outline=None)


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


# -------- scenes --------

def sc01(im, t):
    d = ImageDraw.Draw(im)
    xs = [150, 300, 430, 560, 700, 840, 975, 1115]
    labels = [
        ('Jāgrat', GOLD_LIGHT),
        ('Śūnya I', SLATE),
        ('Svapna', ROSE),
        ('Śūnya II', VIOLET),
        ('Suṣupti', SEA),
        ('Madhya-śūnya', INDIGO),
        ('Turīya', TEAL),
        ('Turīyātīta', WHITE),
    ]
    y = 300
    for i,(x,(lab,col)) in enumerate(zip(xs, labels)):
        rr = 28 if i not in [1,3,5] else 22
        fill = rgba(mix(NIGHT,col,.15), 90) if i not in [7] else rgba((248,248,244),180)
        d.ellipse((x-rr,y-rr,x+rr,y+rr), outline=rgba(col,220), fill=fill, width=2)
        if 'Śūnya' in lab or 'Madhya' in lab:
            d.ellipse((x-10,y-10,x+10,y+10), outline=rgba(col,190), width=2)
        else:
            d.text((x,y), str(i//2 + 1) if i < 6 and i % 2 == 0 else ('4' if lab=='Turīya' else ''), font=SMALL_FONT, fill=IVORY if col != WHITE else NIGHT, anchor='mm')
        d.text((x, y+56), lab, font=SMALL_FONT, fill=col, anchor='mm')
        if i < len(xs)-1:
            pts = partial_polyline(bezier((x+rr,y),(x+60,y-40),(xs[i+1]-60,y+40),(xs[i+1]-rr,y),80), smoothstep(0.04+i*0.08,0.74+i*0.06,t))
            if len(pts)>1:
                draw_line_glow(im, pts, mix(col, labels[i+1][1], .5), 3, 110, 6)
                draw_arrowhead(d, pts[-2], pts[-1], mix(col, labels[i+1][1], .5), 0.8)
    d.text((640, 510), 'the states of consciousness are crossed through friction-points of void', font=SUB_FONT, fill=MIST, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 282
    # outward sensory star
    for i in range(8):
        a = -math.pi/2 + i*2*math.pi/8
        x = cx + math.cos(a)*210
        y = cy + math.sin(a)*135
        draw_line_glow(im, [(cx,cy),(x,y)], mix(GOLD_LIGHT, GOLD, i/8), 2, 85, 5)
        d.ellipse((x-9,y-9,x+9,y+9), fill=rgba(GOLD_LIGHT,180))
    draw_eye(d, cx, cy, 1.0, GOLD_LIGHT)
    d.text((640, 505), 'waking consciousness projects outward toward an object-field', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # external data collapsing into first void
    for i in range(10):
        a = -math.pi/2 + i*2*math.pi/10
        sx = cx + math.cos(a)*240
        sy = cy + math.sin(a)*150
        pts = partial_polyline(bezier((sx,sy), (sx*0.75+cx*0.25, sy), (cx+math.cos(a)*60, cy+math.sin(a)*34), (cx,cy), 90), smoothstep(0.05,0.88,t))
        if len(pts)>1: draw_line_glow(im, pts, mix(GOLD_LIGHT, SLATE, i/10), 2, 90, 5)
    draw_glow(im,(cx,cy),62,SLATE,100,18)
    d.ellipse((cx-34,cy-34,cx+34,cy+34), outline=rgba(SILVER,190), width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14), fill=rgba(NIGHT,255), outline=rgba(SLATE,220), width=2)
    d.text((640, 505), 'the first void appears as the collapse of external data', font=SUB_FONT, fill=MIST, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # dream-icons around central sleeper
    dream_cols = [ROSE, VIOLET, GOLD_LIGHT, TEAL, SEA]
    icons = ['◐','✦','☾','✧','◌']
    for i,(col,ic) in enumerate(zip(dream_cols, icons)):
        a = -math.pi/2 + i*2*math.pi/5 + t*0.05
        x = cx + math.cos(a)*175
        y = cy + math.sin(a)*110
        d.ellipse((x-26,y-26,x+26,y+26), outline=rgba(col, 180), fill=rgba(mix(NIGHT,col,.12),70), width=2)
        d.text((x,y), ic, font=TERM_FONT, fill=col, anchor='mm')
        pts = partial_polyline(bezier((cx,cy+18),(cx+math.cos(a)*40,cy+20),(x,y-20),(x,y),70), smoothstep(0.06,0.84,t))
        if len(pts)>1: draw_line_glow(im, pts, col, 2, 80, 5)
    d.ellipse((cx-36, cy-16, cx+36, cy+20), outline=rgba(ROSE, 210), width=2)
    d.arc((cx-46, cy-2, cx+46, cy+34), 0, 180, fill=rgba(ROSE,200), width=2)
    d.text((640, 505), 'dreaming projects a subtler internal world of forms', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 282
    # dream imagery thinning into subtle void
    for i in range(7):
        a = -math.pi/2 + i*2*math.pi/7
        r = 175 - i*16*ease_in_out(t)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.68
        d.ellipse((x-18,y-18,x+18,y+18), outline=rgba(mix(ROSE, VIOLET, i/7), int(170*(1-i/10))), width=2)
    draw_glow(im,(cx,cy),58,VIOLET,105,18)
    d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=rgba(NIGHT,255), outline=rgba(VIOLET,220), width=2)
    d.ellipse((cx-36,cy-36,cx+36,cy+36), outline=rgba(SILVER,100), width=1)
    d.text((640, 505), 'the second void appears as internal imagery dissolves', font=SUB_FONT, fill=MIST, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # uniform dark sleep field
    for i in range(8):
        r = 60 + i*28
        d.ellipse((cx-r, cy-r*0.72, cx+r, cy+r*0.72), outline=rgba(mix(SEA, SLATE, i/8), 110), width=2)
    draw_glow(im,(cx,cy),86,SEA,85,24)
    d.ellipse((cx-24,cy-24,cx+24,cy+24), fill=rgba(BLACK,255), outline=rgba(SEA,190), width=2)
    d.text((640, 505), 'deep sleep is uniform, dark, and objectless', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # central void between identity and emptiness
    for i in range(12):
        a = i*2*math.pi/12
        r1 = 110
        r2 = lerp(170, 112, ease_in_out(t))
        p0 = (cx + math.cos(a)*r2, cy + math.sin(a)*r2*0.72)
        p1 = (cx + math.cos(a)*r1, cy + math.sin(a)*r1*0.72)
        draw_line_glow(im, [p0,p1], mix(INDIGO, SILVER, i/12), 2, 80, 5)
    d.ellipse((cx-112, cy-82, cx+112, cy+82), outline=rgba(INDIGO, 120), width=2)
    d.ellipse((cx-62, cy-46, cx+62, cy+46), outline=rgba(SILVER, 150), width=2)
    draw_glow(im,(cx,cy),52,INDIGO,110,18)
    d.ellipse((cx-20,cy-20,cx+20,cy+20), fill=rgba(BLACK,255), outline=rgba(GOLD_LIGHT,180), width=2)
    d.text((640, 505), 'the central void is the gap between identity and emptiness', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # turiya: still witness around all states
    state_cols = [GOLD_LIGHT, ROSE, SEA]
    for i,col in enumerate(state_cols):
        r = [76, 118, 164][i]
        d.ellipse((cx-r, cy-r*0.72, cx+r, cy+r*0.72), outline=rgba(col, 110), width=2)
    for i,a in enumerate(np.linspace(0,2*math.pi,12, endpoint=False)):
        x = cx + math.cos(a)*210
        y = cy + math.sin(a)*145
        d.line((x, y, cx + math.cos(a)*176, cy + math.sin(a)*122), fill=rgba(SILVER,80), width=1)
    draw_glow(im,(cx,cy),60,TEAL,120,18)
    d.ellipse((cx-22,cy-22,cx+22,cy+22), fill=rgba(WHITE,255), outline=rgba(TEAL,220), width=2)
    d.text((640, 505), 'the fourth is pure background awareness witnessing all states', font=SUB_FONT, fill=MIST, anchor='mm')


def sc09(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # fourth void / witness gulf opening into integration
    pts1 = partial_polyline(bezier((250,cy),(390,cy-120),(560,cy-70),(cx,cy),100), smoothstep(0.05,0.84,t))
    pts2 = partial_polyline(bezier((1030,cy),(890,cy+120),(720,cy+70),(cx,cy),100), smoothstep(0.05,0.84,t))
    if len(pts1)>1: draw_line_glow(im, pts1, mix(TEAL, SILVER, .5), 3, 110, 7)
    if len(pts2)>1: draw_line_glow(im, pts2, mix(TEAL, GOLD_LIGHT, .4), 3, 110, 7)
    draw_glow(im,(cx,cy),74,SILVER,90,20)
    d.ellipse((cx-26,cy-26,cx+26,cy+26), fill=rgba(WHITE,255), outline=rgba(SILVER,210), width=2)
    d.ellipse((cx-164,cy-96,cx+164,cy+96), outline=rgba(TEAL, 85), width=2)
    d.text((640, 505), 'the witness-field itself becomes a subtler threshold', font=SUB_FONT, fill=MIST, anchor='mm')


def sc10(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # all-integrating beyond: no inside/outside
    for i in range(5):
        r = 44 + i*44
        d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=rgba(mix(WHITE, GOLD_LIGHT, i/5), 120), width=2)
    for i in range(18):
        a = i*2*math.pi/18
        p0 = (cx + math.cos(a)*128, cy + math.sin(a)*128)
        p1 = (cx + math.cos(a)*188, cy + math.sin(a)*188)
        draw_line_glow(im, [p0,p1], mix(SILVER, GOLD_LIGHT, (i%6)/6), 2, 75, 5)
    draw_glow(im,(cx,cy),84,WHITE,130,22)
    d.ellipse((cx-28,cy-28,cx+28,cy+28), fill=rgba(WHITE,255), outline=rgba(GOLD_LIGHT,220), width=2)
    d.text((cx, cy), 'ॐ', font=DEVA_MED, fill=rgba(GOLD,230), anchor='mm')
    d.text((640, 505), 'beyond the fourth: no inside, no outside, only integrated awareness', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('av01', 'The States and the Voids', 'An overview of the four states crossed through void-transitions.', 'Avasthā–Śūnya', 'The architecture of consciousness is traversed through state-changes and void thresholds.', 'overview_path', ['overview','states','voids'], 'overview', 'state-path overview line', sc01),
    Scene('av02', 'Jāgrat', 'Waking consciousness projects outward toward objects.', 'Jāgrat', 'The waking state is outward, sensory, and object-engaged.', 'waking_projection', ['waking','projection','objects'], 'state', 'sensory star', sc02),
    Scene('av03', 'The First Void', 'External data collapses into the first friction-point.', 'Prathama-śūnya', 'The first void marks the collapse of outwardly projected data.', 'first_void', ['void','transition','collapse'], 'void', 'centripetal collapse', sc03),
    Scene('av04', 'Svapna', 'Dreaming projects a subtler inner field of forms.', 'Svapna', 'The dream state internalizes projection into imaginal space.', 'dream_projection', ['dream','inner image'], 'state', 'dream icon orbit', sc04),
    Scene('av05', 'The Second Void', 'Internal imagery thins and dissolves into a subtler gap.', 'Dvitīya-śūnya', 'The second void marks the collapse of dream-forms.', 'second_void', ['void','dream collapse'], 'void', 'dream thinning rings', sc05),
    Scene('av06', 'Suṣupti', 'Deep sleep is uniform, dark, and objectless.', 'Suṣupti', 'The sleep state is undifferentiated and non-projective.', 'deep_sleep', ['sleep','darkness','objectless'], 'state', 'uniform oval field', sc06),
    Scene('av07', 'The Central Void', 'A gap appears between identity and emptiness.', 'Madhya-śūnya', 'The central void is the hinge between self-sense and pure blankness.', 'central_void', ['central void','gap'], 'void', 'converging gap field', sc07),
    Scene('av08', 'Turīya', 'Pure background awareness witnesses all states.', 'Turīya', 'The fourth is stable witnessing consciousness.', 'fourth_state', ['witness','awareness','turiya'], 'state', 'witness rings', sc08),
    Scene('av09', 'The Witness-Threshold', 'Even the witness-field becomes a subtler opening.', 'Caturtha-śūnya', 'A further void appears at the threshold of integrated awareness.', 'witness_threshold', ['void','witness','threshold'], 'void', 'converging witness arcs', sc09),
    Scene('av10', 'Turīyātīta', 'Beyond the fourth, all inner and outer divisions dissolve.', 'Turīyātīta', 'Total integration: no inside or outside remains.', 'beyond_fourth', ['integration','beyond','seal'], 'seal', 'integrated radiant seal', sc10),
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
            im = threshold_ground(SEED + hash(scene.id)%10000 + i)
            border(im)
            dust(im, SEED+i, 70)
            scene.draw_fn(im, t)
            footer(im, scene.title, scene.subtitle, scene.term)
            im.convert('RGB').save(path, quality=95)
    out = SCENES_ROOT / f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size < 30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)], check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame = FRAMES_ROOT / sc.id / f'frame_{int(NFRAMES*0.72):04d}.jpg'
        im = Image.open(frame).convert('RGB').resize((320,180), Image.Resampling.LANCZOS)
        thumbs.append(im)
    cols = 4; rows = 3
    sheet = Image.new('RGB', (cols*320, rows*180), color=NIGHT)
    for idx,im in enumerate(thumbs):
        x=(idx%cols)*320; y=(idx//cols)*180
        sheet.paste(im,(x,y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project':'Tantrāloka — The Four States of Consciousness (Avasthās) & The Five Voids',
        'source_basis':'Conceptual mapping supplied by the user from Tantrāloka: Jāgrat, Svapna, Suṣupti, Turīya, Turīyātīta, with void-transitions.',
        'style': {
            'family':'threshold cosmography / twilight contemplative states',
            'background':'midnight indigo threshold field',
            'ink':'mist and silver',
            'accent':'gold, rose, violet, teal, sea blue, white',
            'materials':['sensory star','dream orbits','uniform sleep field','void gaps','witness rings','radiant integration seal']
        },
        'fps': FPS,
        'resolution': [W,H],
        'scene_duration_seconds': DURATION,
        'total_scenes': len(SCENES),
        'total_duration_seconds': round(len(SCENES)*DURATION,2),
        'scenes': [
            {
                'id': sc.id,
                'title': sc.title,
                'subtitle': sc.subtitle,
                'mode': sc.mode,
                'summary': sc.summary,
                'group': sc.group,
                'technique_notes': sc.technique,
                'tags': sc.tags,
                'duration_seconds': DURATION,
                'output_filename': f'scenes/{sc.id}.mp4'
            } for sc in SCENES
        ]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    catalog = {
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id: sc.title for sc in SCENES},
        'modes':{sc.id: sc.mode for sc in SCENES},
        'theme_clusters':{
            'overview':['av01'],
            'state_scenes':['av02','av04','av06','av08','av10'],
            'void_scenes':['av03','av05','av07','av09'],
        },
        'reusability_notes':{
            'av01':'Use to introduce the whole sequence of states and voids.',
            'av02':'Use for waking, projection, sensory outwardness, or object-engagement.',
            'av03':'Use for the first void or collapse of outer cognition.',
            'av04':'Use for dream, imaginal projection, or subtle interiority.',
            'av05':'Use for the second void or dissolution of imaginal content.',
            'av06':'Use for deep sleep, undifferentiated darkness, or objectless rest.',
            'av07':'Use for central void, identity-gap, or hinge of consciousness.',
            'av08':'Use for witnessing awareness, pure background presence, or the fourth state.',
            'av09':'Use for a subtle witness-threshold or higher void transition.',
            'av10':'Use as a closing seal for integration, nonduality, or beyond-the-fourth.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Avasthās & the Voids

## Aim
This pack visualizes the **states of consciousness** and the **void-thresholds** through which awareness passes.

## Textual orientation
The pack is based on the user-supplied structural account: waking, dreaming, deep sleep, the fourth, and beyond the fourth, with voids functioning as transition friction-points.

## Core doctrinal structure represented
### States
1. **Jāgrat** — waking / outward projection
2. **Svapna** — dreaming / inward imaginal projection
3. **Suṣupti** — deep sleep / objectless darkness
4. **Turīya** — pure witnessing awareness
5. **Turīyātīta** — total integration beyond the fourth

### Voids used in the pack
1. **Prathama-śūnya** — collapse of external data
2. **Dvitīya-śūnya** — collapse of internal imagery
3. **Madhya-śūnya** — central gap between identity and emptiness
4. **Caturtha-śūnya** — witness-threshold / subtle opening beyond witnessing
5. **All-integrating culmination** implicit in Turīyātīta

## Visual rules
- Each state must feel phenomenologically distinct.
- Waking = outward, radiant, object-facing.
- Dream = inner, symbolic, imaginal.
- Deep sleep = smooth, uniform, dark, non-projective.
- Turīya = stillness with encompassing awareness.
- Turīyātīta = integration without dual border.
- The voids should feel like thresholds, not merely black circles.

## Style family
- midnight threshold field
- indigo / violet / silver atmospherics
- gold waking light
- rose dream forms
- sea-blue sleep field
- teal witness light
- white integrated seal

## New motifs introduced
- state-path overview
- sensory star
- centripetal collapse void
- dream icon orbit
- dream thinning ring-void
- uniform sleep ellipses
- central gap field
- witness rings
- witness-threshold convergence
- radiant nondual seal

## Guardrails
- Do not flatten the states into a single psychology diagram only.
- Do not make deep sleep simply unconscious blankness without structural significance.
- Do not treat Turīya as just another altered state; it is the witnessing ground.
- The pack should track movement through thresholds, not isolated snapshots only.

## Reuse strategy
- av01: whole architecture
- av02 / av04 / av06 / av08 / av10: the major states
- av03 / av05 / av07 / av09: the transition voids
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Avasthās & Voids Pack

## Inheritance
This pack preserves the project’s contemplative diagrammatic language while shifting from cosmographic taxonomy into phenomenological thresholds.

## Avasthā differentiation
This pack emphasizes:
- transitions of consciousness rather than cosmic topology
- sensory outwardness vs imaginal inwardness
- dark objectless continuity
- threshold voids between modes of awareness
- radiant, nondual integration at the end

## New motifs added
1. path-overview with state and void markers
2. waking sensory star
3. first void collapse aperture
4. dream orbit icons
5. second void thinning rings
6. deep sleep uniform field
7. central void gap
8. witness rings
9. witness-threshold convergence
10. radiant integration seal

## New relationships added
- waking → first void
- dreaming → second void
- deep sleep → central void
- central void → witnessing
- witnessing → subtle threshold
- threshold → integrated nonduality

## New material vocabulary
- midnight indigo field
- silver threshold geometry
- gold projection rays
- rose imaginal motifs
- sea-blue sleep halos
- white integration light

## Deprecated clichés
- generic chakra sleep infographic look
- cluttered neuroscience-brain aesthetics
- making voids into mere empty holes without process

## Distinct closing seal
The closing seal is a **radiant integration seal** representing Turīyātīta as the dissolution of inner and outer division.

## Recommendation for next packs
Strong next candidate:
- Three Structural Bindus / Kāmākalā
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The Four States of Consciousness (Avasthās) & The Five Voids Pack

Included files:
- avasthas_voids_animation.mp4
- contact_sheet.jpg
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- STYLE_EVOLUTION.md
- render_pack.py
- README.md
- validation.json
- scenes/*.mp4

Specs:
- Resolution: {W}x{H}
- FPS: {FPS}
- Scene count: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total runtime: {len(SCENES)*DURATION/60:.2f} min

Render instructions:
```bash
python render_pack.py
```
The script is resume-safe.
'''
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'avasthas_voids_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'avasthas_voids_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['avasthas_voids_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name, arcname=name)
        for mp4 in sorted((SCENES_ROOT).glob('*.mp4')):
            zf.write(mp4, arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, flush=True)
        render_scene(sc)
    concat_file = ROOT / 'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT / 'avasthas_voids_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
