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
SEED = 22221

DEEP_VOID = (14, 16, 24)
WARM_DARK = (24, 22, 20)
NIGHT = (18, 20, 30)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
SILVER = (196, 204, 222)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
CRIMSON = (154, 44, 58)
CORAL = (206, 108, 100)
TEAL = (92, 146, 148)
INDIGO = (68, 78, 136)
VIOLET = (120, 104, 168)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)
UMBER = (82, 66, 52)
EARTH = (136, 106, 74)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 18)


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
def smoothstep(a, b, x):
    if a == b: return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t * t * (3 - 2 * t)
def rgba(c, a=255):
    return (*c[
    :3,
    :3,
], int(a))


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


def bezier(p0, p1, p2, p3, n=100):
    pts = []
    for i in range(n):
        t = i/(n-1); u = 1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts


def arc_points(cx, cy, rx, ry, a0, a1, n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx, cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer, 145), outline=rgba(inner, 180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner, 120), outline=rgba(outer, 220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(GOLD, 100), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 70), width=1)
    for x, y in [(70, 70), (W-70, 70), (70, H-70), (W-70, H-70)]:
        draw_rosette(d, x, y, 22, CRIMSON, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(13, 15, 22, 200), outline=rgba(GOLD, 55), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def dust(im, seed, n=40):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40, W-40)); y = float(rng.uniform(40, H-40))
        r = float(rng.uniform(0.8, 2.0))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0, 1))
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(c, int(rng.uniform(20, 60))))
    im.alpha_composite(ov)


def kancuka_ground(seed, bg, glow_col, intensity=0.7):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(bg, dtype=np.float32)
    coarse = rng.normal(0, 1, (44, 78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*3.2*intensity + fine[..., None]*0.9*intensity
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx-W/2)/(W/2); dy = (yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18, 0, 26)[..., None]
    if glow_col:
        g = np.exp(-(((xx-W*0.48)/(W*0.30))**2 + ((yy-H*0.40)/(H*0.24))**2)*2.4)
        for i in range(3):
            base[..., i] += g * glow_col[i] * 0.04
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


KANCHUKA_COLS = [CRIMSON, INDIGO, CORAL, SLATE, EARTH]
KANCHUKA_NAMES = ['kalā', 'vidyā', 'rāga', 'kāla', 'niyati']


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
    duration: float
    draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 290
    d.text((cx, 140), 'you can only do so much', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 168), 'you can only know so much', font=TERM_FONT, fill=MIST, anchor='mm')
    d.text((cx, 196), 'time moves whether you want it or not', font=TERM_FONT, fill=MIST, anchor='mm')
    prog = smoothstep(0.1, 0.9, t)
    for i in range(5):
        p = clamp(prog*1.2 - i*0.08)
        if p <= 0: continue
        r = 26 + i*30
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(KANCHUKA_COLS[i], int(200*p)), width=3-i//2)
    draw_glow(im, (cx, cy), 16, GOLD_LIGHT, int(100*(1-prog*0.6)), 10)
    d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=rgba(WHITE, int(255*(1-prog*0.5))))


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(kancuka_ground(fs, NIGHT, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    d.text((cx, 115), 'five pieces of armor', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 143), 'between you and freedom', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    for i in range(5):
        r = 28 + i*30
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(KANCHUKA_COLS[i], 200), width=3-i//2)
        d.text((cx+r+24, cy-6), KANCHUKA_NAMES[i], font=TINY_FONT, fill=rgba(KANCHUKA_COLS[i], 200))
    draw_glow(im, (cx, cy), 14, GOLD_LIGHT, 80, 10)
    d.ellipse((cx-5, cy-5, cx+5, cy+5), fill=rgba(WHITE, 200))
    d.text((cx, cy), 'cit', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 483), 'kalā, vidyā, rāga, kāla, niyati', font=TERM_FONT, fill=MIST, anchor='mm')
    d.text((cx, 506), 'the five obscuring coverings', font=SMALL_FONT, fill=SLATE, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, CORAL, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 115), 'a knot pulls tighter', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 143), 'the more you wrestle it', font=TERM_FONT, fill=CORAL, anchor='mm')
    prog = ease_in_out(t)
    pts = bezier((400, 350), (500, 250), (600, 400), (cx, cy), 40)
    pts2 = bezier((cx, cy), (700, 150), (800, 350), (880, 350), 40)
    strand = pts + pts2[1:]
    reveal = partial_polyline(strand, prog)
    if len(reveal) > 1:
        draw_line_glow(im, reveal, GOLD, 3, 120, 7)
    tension = 10 + 20*(0.5+0.5*math.sin(t*2))
    knot_x = cx
    knot_y = cy
    d.ellipse((knot_x-8-tension, knot_y-8, knot_x+8+tension, knot_y+8), outline=rgba(CORAL, 180), width=2)
    d.text((cx, 478), 'relaxed attention finds the thread', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((cx, 500), 'and quietly undoes it, one loop at a time', font=TINY_FONT, fill=SLATE, anchor='mm')


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(kancuka_ground(fs, DEEP_VOID, GOLD_LIGHT, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 105), 'kalā — limited agency', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'you can only lift so much', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 163), 'beneath it: the power to lift anything', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    ceiling = lerp(320, 200, prog)
    d.line((200, int(ceiling), 1080, int(ceiling)), fill=rgba(CRIMSON, int(180*(1-prog))), width=2)
    pts = bezier((640, 460), (580, ceiling+40), (700, ceiling+40), (640, ceiling), 50)
    draw = partial_polyline(pts, smoothstep(0.1, 0.9, t))
    if len(draw) > 1:
        draw_line_glow(im, draw, GOLD_LIGHT, 3, 100, 6)
    if prog > 0.8:
        pts2 = bezier((640, 460), (580, 150), (700, 150), (640, 130), 40)
        draw2 = partial_polyline(pts2, clamp((prog-0.8)*5))
        if len(draw2) > 1:
            draw_line_glow(im, draw2, GOLD, 4, 130, 7)


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(kancuka_ground(fs, DEEP_VOID, TEAL, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 105), 'vidyā — limited knowledge', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'you only see a sliver', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 163), 'beneath it: the capacity to see through', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    slit = lerp(200, 10, prog)
    d.rectangle((cx-slit, 220, cx+slit, 420), fill=rgba(INDIGO, 180))
    draw_glow(im, (cx, 320), 30, GOLD_LIGHT, int(80*prog), 14)
    d.ellipse((cx-slit+10, 260, cx+slit-10, 380), fill=rgba(WHITE, int(60*prog)))
    d.text((cx, 470), 'an eye cannot see itself without a mirror', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((cx, 492), 'vidyā is that mirror', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, CORAL, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 105), 'rāga — craving', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'you reach for what you lack', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 163), 'beneath it: the fullness that reaches for nothing', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    arm_len = lerp(80, 220, prog)
    d.line((cx-60, 340, cx-60, 260), fill=rgba(CORAL, 180), width=4)
    d.line((cx-60, 260, cx-60-arm_len, 230), fill=rgba(CORAL, 180), width=4)
    d.ellipse((cx-60-arm_len-10, 220, cx-60-arm_len+10, 240), fill=rgba(GOLD_LIGHT, 180))
    obj_x = cx + 100
    d.ellipse((obj_x-12, 228, obj_x+12, 252), outline=rgba(GOLD, 200), width=2)
    reach = lerp(arm_len, 300, 0.5+0.5*math.sin(t*2.5))
    if reach < 300:
        d.line((cx-60, 340, cx-60, 260), fill=rgba(CORAL, 180), width=4)


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(kancuka_ground(fs, NIGHT, GOLD_LIGHT, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 105), 'kāla — time', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'you move from A to B', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 163), 'beneath it: the present that never moves', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.line((180, 320, 1100, 320), fill=rgba(SLATE, 150), width=2)
    for x in [180, 410, 640, 870, 1100]:
        d.line((x, 310, x, 330), fill=rgba(SLATE, 120), width=1)
        d.text((x, 340), chr(65+(x-180)//230), font=SMALL_FONT, fill=SLATE, anchor='mm')
    pos = lerp(180, 1100, prog)
    draw_glow(im, (int(pos), 320), 12, GOLD_LIGHT, 120, 8)
    d.ellipse((int(pos)-6, 314, int(pos)+6, 326), fill=rgba(WHITE, 255))
    d.line((640, 280, 640, 360), fill=rgba(GOLD, 150), width=1)
    d.text((640, 270), 'now', font=SMALL_FONT, fill=GOLD, anchor='mm')


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(kancuka_ground(fs, DEEP_VOID, EARTH, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 105), 'niyati — necessity', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'you reap what you sow', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 163), 'beneath it: the freedom that sows regardless', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(6):
        x = cx - 150 + i*60
        y = cy + 40
        r = 18
        d.ellipse((x-r, y-r, x+r, y+r), outline=rgba(EARTH, 180), width=2)
        if i < 5:
            d.line((x+r, y, x+60-r, y), fill=rgba(EARTH, 120), width=2)
    if prog > 0.3:
        hand_x = cx - 150 + int(clamp((prog-0.3)*3)*300)
        draw_glow(im, (hand_x, cy+40), 14, GOLD_LIGHT, 100, 8)
        d.ellipse((hand_x-6, cy+34, hand_x+6, cy+46), fill=rgba(WHITE, 220))


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(kancuka_ground(fs, NIGHT, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 115), 'an eye cannot see itself', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 143), 'without a mirror', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 175), 'vidyā is that mirror', font=SMALL_FONT, fill=MIST, anchor='mm')
    left_x, right_x = 440, 840
    r = 36
    for x, col in [(left_x, GOLD), (right_x, TEAL)]:
        draw_glow(im, (x, cy+30), 20, col, 70, 12)
        d.arc((x-r, cy+30-r, x+r, cy+30+r), 20, 160, fill=rgba(col, 200), width=3)
        d.arc((x-r, cy+30-r, x+r, cy+30+r), 200, 340, fill=rgba(col, 200), width=3)
        d.ellipse((x-5, cy+25, x+5, cy+35), fill=rgba(WHITE, 200))
    d.rectangle((left_x+50, cy+10, right_x-50, cy+50), outline=rgba(GOLD_LIGHT, 100), width=1)


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(kancuka_ground(fs, NIGHT, CRIMSON, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 105), 'the words "just now" are a cage', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'the cage is made of time', font=TERM_FONT, fill=CRIMSON, anchor='mm')
    d.text((cx, 170), 'just now', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(8):
        x = cx - 100 + i*28
        alpha = int(100 + 100*(0.5+0.5*math.sin(t*2+i)))
        d.line((x, 280, x, 440), fill=rgba(SLATE, alpha), width=2)
    bars = int(3 + 5*prog)
    for i in range(bars):
        x = cx - 60 + i*40
        d.line((x, 280, x, 440), fill=rgba(CRIMSON, 180), width=3)


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, CORAL, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    d.text((cx, 105), 'the fist that closes', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 133), 'also brings blood to the palm', font=TERM_FONT, fill=CORAL, anchor='mm')
    d.text((cx, 165), 'contraction itself generates the heat of life', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    fingers = [
        (cx-40, cy-40, cx-20, cy-60, cx+10, cy-55),
        (cx+10, cy-55, cx+30, cy-65, cx+50, cy-45),
        (cx+50, cy-45, cx+60, cy-20, cx+55, cy+10),
    ]
    for p0, p1, p2 in fingers:
        close = lerp(1.0, 0.3, prog)
        pts = bezier(p0, p1, p2, (cx, cy+20), 30)
        reveal = partial_polyline(pts, close)
        if len(reveal) > 1:
            draw_line_glow(im, reveal, CORAL, 3, 100, 6)
    palm_r = lerp(40, 20, prog)
    d.ellipse((cx-palm_r, cy-palm_r, cx+palm_r, cy+palm_r), outline=rgba(CORAL, 180), width=2)
    glow_r = int(5 + 20*prog)
    draw_glow(im, (cx, cy), glow_r, GOLD_LIGHT, int(60*prog), 12)


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(kancuka_ground(fs, DEEP_VOID, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 95), 'the seven perceivers', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 122), 'waking, dreaming, deep sleep,', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 142), 'the fourth, beyond the fourth', font=SMALL_FONT, fill=MIST, anchor='mm')
    states = ['jāgrat', 'svapna', 'suṣupti', 'turīya', 'turīyātīta']
    s_cols = [SLATE, INDIGO, VIOLET, GOLD_LIGHT, WHITE]
    for i in range(5):
        y = 190 + i*48
        w = 180 - i*18
        d.rounded_rectangle((cx-w, y-14, cx+w, y+14), radius=8, outline=rgba(s_cols[i], 160), fill=rgba((14,16,24),40), width=2)
        d.text((cx, y), states[i], font=TINY_FONT, fill=s_cols[i], anchor='mm')
        for j in range(5):
            dx = (j-2)*20
            active = int(180*((i+j)%3/3+0.3))
            d.ellipse((cx+dx-3, y-24+j+3, cx+dx+3, y-18+j+3), fill=rgba(KANCHUKA_COLS[j], active))


def sc13(im, t):
    fs = SEED + int(t*9973+6000) % 100000
    im.paste(kancuka_ground(fs, DEEP_VOID, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 110), 'māyā is the night', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 140), "of the lord's consciousness", font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 175), 'the same turning that makes stars visible', font=SMALL_FONT, fill=MIST, anchor='mm')
    rng = np.random.default_rng(130)
    prog = ease_in_out(t)
    for i in range(70):
        x = float(rng.uniform(60, W-60))
        y = float(rng.uniform(170, 470))
        r = float(rng.uniform(1, 3.5))
        a = int(15 + 200*prog*(0.2+0.8*rng.random()))
        col = mix(GOLD_LIGHT, SILVER, rng.random())
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(col, a))
    draw_glow(im, (cx-100,cy+30), 14, SILVER, int(50*prog), 10)
    d.arc((cx-110,cy+18,cx-90,cy+42), 0, 180, fill=rgba(SILVER, int(150*prog)), width=2)
    d.text((50, 80), 'रात्री', font=DEVA_SMALL, fill=rgba(GOLD, 30))


def sc14(im, t):
    fs = SEED + int(t*9973+6500) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 240
    d.text((cx, 95), 'no two souls wear the same armor', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 123), 'your limits are your signature', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    offsets = [(-200, 30), (200, 10), (-140, 100), (140, 80), (0, 50), (-60, -60)]
    rng = np.random.default_rng(321)
    for ox, oy in offsets:
        for i in range(5):
            r = 10 + i*8 + float(rng.uniform(-2, 2))
            d.ellipse((cx+ox-r, cy+oy-r*0.6, cx+ox+r, cy+oy+r*0.6), outline=rgba(KANCHUKA_COLS[i], 120), width=1)
            if i > 0:
                d.ellipse((cx+ox-r*0.3, cy+oy-r*0.18, cx+ox+r*0.3, cy+oy+r*0.18), outline=rgba(KANCHUKA_COLS[i], 60), width=1)


def sc15(im, t):
    fs = SEED + int(t*9973+7000) % 100000
    im.paste(kancuka_ground(fs, NIGHT, GOLD_LIGHT, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 95), 'time is a gesture consciousness makes', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'a slicing of the eternal into manageable pieces', font=SMALL_FONT, fill=MIST, anchor='mm')
    for i in range(3):
        draw_glow(im, (cx-100+i*100, cy+20), 60, GOLD_LIGHT, 30, 30)
    d.line((180, cy+50, 1100, cy+50), fill=rgba(GOLD, 120), width=2)
    prog = ease_in_out(t)
    cut = int(4*prog)
    for i in range(cut):
        x = cx - 150 + i*100
        d.line((x, cy-20, x, cy+80), fill=rgba(CRIMSON, 180), width=2)


def sc16(im, t):
    fs = SEED + int(t*9973+7500) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 105), 'the body:', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 133), 'a garment woven from the same thread as the armor', font=TERM_FONT, fill=MIST, anchor='mm')
    d.text((cx, 165), 'karma spun into form, limitation worn as skin', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.ellipse((cx-24, 200, cx+24, 250), outline=rgba(GOLD, 120), width=2)
    body = [(cx-50, 360), (cx-36, 260), (cx-24, 250), (cx+24, 250), (cx+36, 260), (cx+50, 360)]
    d.polygon(body, outline=rgba(GOLD, 120), width=2)
    d.line((cx, 360, cx, 450), fill=rgba(GOLD, 100), width=2)
    d.line((cx, 300, cx-70, 380), fill=rgba(GOLD, 80), width=2)
    d.line((cx, 300, cx+70, 380), fill=rgba(GOLD, 80), width=2)
    for i in range(5):
        y = 230 + i*20
        d.line((cx-24, y, cx+24, y), fill=rgba(KANCHUKA_COLS[i], 150), width=2)


def sc17(im, t):
    fs = SEED + int(t*9973+8000) % 100000
    im.paste(kancuka_ground(fs, WARM_DARK, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    d.text((cx, 100), 'they hide the infinite', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 128), 'they also reveal the finite as beautiful', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 160), 'you only feel the weight of armor', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 182), 'because you have touched what lies beneath', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(5):
        r = 28 + i*28
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(KANCHUKA_COLS[i], int(180-150*prog)), width=3-i//2)
    int_r = lerp(5, 50, prog)
    draw_glow(im, (cx, cy), int(int_r), GOLD_LIGHT, int(120*prog), 16)
    d.ellipse((cx-int_r, cy-int_r*0.62, cx+int_r, cy+int_r*0.62), outline=rgba(GOLD, int(220*prog)), width=2)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=rgba(WHITE, int(255*prog)))
    d.text((cx, 478), 'unarmored. unbound. uninjured. always have been.', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES =,Scene('ka01', 'You Can Only Do So Much', 'Time moves whether you want it to or not.', 'Pariccheda', '', 'limits', ['limitation'], 'intro', 'five rings wrapping a center', 6.0, sc01)
Scene('ka02', 'Five Pieces of Armor', 'Between you and freedom.', 'Kañcuka', '', 'armor', ['kancuka','covering'], 'intro', 'five named rings', 8.0, sc02)
Scene('ka03', 'The Knot of Māyā', 'Pull tighter the more you wrestle it.', 'Māyāgranthi', '', 'knot', ['maya','knot','tighten'], 'doctrine', 'knot that tightens/loosens', 6.0, sc03)
Scene('ka04', 'Kalā — Limited Agency', 'You can only lift so much.', 'Kalā', '', 'agency', ['kala','agency'], 'kancuka', 'lifting arm with ceiling breaking', 8.0, sc04)
Scene('ka05', 'Vidyā — Limited Knowledge', 'You only see a sliver.', 'Vidyā', '', 'knowledge', ['vidya','sliver'], 'kancuka', 'narrow beam expanding to full field', 8.0, sc05)
Scene('ka06', 'Rāga — Craving', 'You reach for what you lack.', 'Rāga', '', 'craving', ['raga','desire'], 'kancuka', 'reaching arm toward an object', 8.0, sc06)
Scene('ka07', 'Kāla — Time', 'You move from A to B.', 'Kāla', '', 'time', ['kala','time'], 'kancuka', 'timeline with moving point + still now', 8.0, sc07)
Scene('ka08', 'Niyati — Necessity', 'You reap what you sow.', 'Niyati', '', 'necessity', ['niyati','karma'], 'kancuka', 'chain of links with free hand', 8.0, sc08)
Scene('ka09', 'The Mirror of Vidyā', 'An eye cannot see itself without a mirror.', 'Vimarśa', '', 'mirror', ['vidya','mirror','self-knowledge'], 'reflection', 'two eyes facing each other with mirror', 6.0, sc09)
Scene('ka10', 'The Cage of Time', 'The words "just now" are a cage.', 'Kāla-pañjara', '', 'cage', ['time','cage','now'], 'reflection', '"just now" dissolving into cage bars', 6.0, sc10)
Scene('ka11', 'The Fist That Closes', 'Contraction generates the heat of life.', 'Saṃkoca', '', 'fist', ['contraction','heat','life'], 'paradox', 'hand closing into fist with glow at center', 8.0, sc11)
Scene('ka12', 'The Seven Perceivers', 'Each state configures the five differently.', 'Saptapramātṛ', '', 'perceivers', ['states','perceivers','configurations'], 'states', 'five states with different ring configs', 8.0, sc12)
Scene('ka13', 'Māyā Is the Night', 'The turning that makes stars visible.', 'Rātrī', '', 'night', ['maya','night','stars'], 'maya', 'dark field with stars appearing', 6.0, sc13)
Scene('ka14', 'Your Limits Are Your Signature', 'No two souls wear the same armor.', 'Svakīya', '', 'signature', ['unique','limits','signature'], 'individuality', 'multiple different ring configurations', 6.0, sc14)
Scene('ka15', 'Time Is a Gesture', 'A slicing of the eternal.', 'Kṣaṇa', '', 'gesture', ['time','gesture','slicing'], 'time', 'slicing gesture through luminous field', 8.0, sc15)
Scene('ka16', 'The Body as Garment', 'Karma spun into form.', 'Puryaṣṭaka', '', 'body', ['body','garment','karma'], 'embodiment', 'body silhouette with five woven colors', 8.0, sc16)
Scene('ka17', 'Both Faces of Armor', 'They reveal the finite as beautiful.', 'Saundarya', '', 'both', ['both','beauty','freedom'], 'seal', 'rings dissolving — translucent jewel-like', 8.0, sc17)
Scene('ka01', 'You Can Only Do So Much', 'Time moves whether you want it to or not.', 'Pariccheda', '', 'limits', ['limitation'], 'intro', 'five rings wrapping a center', 6.0, sc01)
Scene('ka02', 'Five Pieces of Armor', 'Between you and freedom.', 'Kañcuka', '', 'armor', ['kancuka','covering'], 'intro', 'five named rings', 8.0, sc02)
Scene('ka03', 'The Knot of Māyā', 'Pull tighter the more you wrestle it.', 'Māyāgranthi', '', 'knot', ['maya','knot','tighten'], 'doctrine', 'knot that tightens/loosens', 6.0, sc03)
Scene('ka04', 'Kalā — Limited Agency', 'You can only lift so much.', 'Kalā', '', 'agency', ['kala','agency'], 'kancuka', 'lifting arm with ceiling breaking', 8.0, sc04)
Scene('ka05', 'Vidyā — Limited Knowledge', 'You only see a sliver.', 'Vidyā', '', 'knowledge', ['vidya','sliver'], 'kancuka', 'narrow beam expanding to full field', 8.0, sc05)
Scene('ka06', 'Rāga — Craving', 'You reach for what you lack.', 'Rāga', '', 'craving', ['raga','desire'], 'kancuka', 'reaching arm toward an object', 8.0, sc06)
Scene('ka07', 'Kāla — Time', 'You move from A to B.', 'Kāla', '', 'time', ['kala','time'], 'kancuka', 'timeline with moving point + still now', 8.0, sc07)
Scene('ka08', 'Niyati — Necessity', 'You reap what you sow.', 'Niyati', '', 'necessity', ['niyati','karma'], 'kancuka', 'chain of links with free hand', 8.0, sc08)
Scene('ka09', 'The Mirror of Vidyā', 'An eye cannot see itself without a mirror.', 'Vimarśa', '', 'mirror', ['vidya','mirror','self-knowledge'], 'reflection', 'two eyes facing each other with mirror', 6.0, sc09)
Scene('ka10', 'The Cage of Time', 'The words "just now" are a cage.', 'Kāla-pañjara', '', 'cage', ['time','cage','now'], 'reflection', '"just now" dissolving into cage bars', 6.0, sc10)
Scene('ka11', 'The Fist That Closes', 'Contraction generates the heat of life.', 'Saṃkoca', '', 'fist', ['contraction','heat','life'], 'paradox', 'hand closing into fist with glow at center', 8.0, sc11)
Scene('ka12', 'The Seven Perceivers', 'Each state configures the five differently.', 'Saptapramātṛ', '', 'perceivers', ['states','perceivers','configurations'], 'states', 'five states with different ring configs', 8.0, sc12)
Scene('ka13', 'Māyā Is the Night', 'The turning that makes stars visible.', 'Rātrī', '', 'night', ['maya','night','stars'], 'maya', 'dark field with stars appearing', 6.0, sc13)
Scene('ka14', 'Your Limits Are Your Signature', 'No two souls wear the same armor.', 'Svakīya', '', 'signature', ['unique','limits','signature'], 'individuality', 'multiple different ring configurations', 6.0, sc14)
Scene('ka15', 'Time Is a Gesture', 'A slicing of the eternal.', 'Kṣaṇa', '', 'gesture', ['time','gesture','slicing'], 'time', 'slicing gesture through luminous field', 8.0, sc15)
Scene('ka16', 'The Body as Garment', 'Karma spun into form.', 'Puryaṣṭaka', '', 'body', ['body','garment','karma'], 'embodiment', 'body silhouette with five woven colors', 8.0, sc16)
Scene('ka17', 'Both Faces of Armor', 'They reveal the finite as beautiful.', 'Saundarya', '', 'both', ['both','beauty','freedom'], 'seal', 'rings dissolving — translucent jewel-like', 8.0, sc17)
Scene('ka01', 'You Can Only Do So Much', 'Time moves whether you want it to or not.', 'Pariccheda', '', 'limits', ['limitation'], 'intro', 'five rings wrapping a center', 6.0, sc01)
Scene('ka02', 'Five Pieces of Armor', 'Between you and freedom.', 'Kañcuka', '', 'armor', ['kancuka','covering'], 'intro', 'five named rings', 8.0, sc02)
Scene('ka03', 'The Knot of Māyā', 'Pull tighter the more you wrestle it.', 'Māyāgranthi', '', 'knot', ['maya','knot','tighten'], 'doctrine', 'knot that tightens/loosens', 6.0, sc03)
Scene('ka04', 'Kalā — Limited Agency', 'You can only lift so much.', 'Kalā', '', 'agency', ['kala','agency'], 'kancuka', 'lifting arm with ceiling breaking', 8.0, sc04)
Scene('ka05', 'Vidyā — Limited Knowledge', 'You only see a sliver.', 'Vidyā', '', 'knowledge', ['vidya','sliver'], 'kancuka', 'narrow beam expanding to full field', 8.0, sc05)
Scene('ka06', 'Rāga — Craving', 'You reach for what you lack.', 'Rāga', '', 'craving', ['raga','desire'], 'kancuka', 'reaching arm toward an object', 8.0, sc06)
Scene('ka07', 'Kāla — Time', 'You move from A to B.', 'Kāla', '', 'time', ['kala','time'], 'kancuka', 'timeline with moving point + still now', 8.0, sc07)
Scene('ka08', 'Niyati — Necessity', 'You reap what you sow.', 'Niyati', '', 'necessity', ['niyati','karma'], 'kancuka', 'chain of links with free hand', 8.0, sc08)
Scene('ka09', 'The Mirror of Vidyā', 'An eye cannot see itself without a mirror.', 'Vimarśa', '', 'mirror', ['vidya','mirror','self-knowledge'], 'reflection', 'two eyes facing each other with mirror', 6.0, sc09)
Scene('ka10', 'The Cage of Time', 'The words "just now" are a cage.', 'Kāla-pañjara', '', 'cage', ['time','cage','now'], 'reflection', '"just now" dissolving into cage bars', 6.0, sc10)
Scene('ka11', 'The Fist That Closes', 'Contraction generates the heat of life.', 'Saṃkoca', '', 'fist', ['contraction','heat','life'], 'paradox', 'hand closing into fist with glow at center', 8.0, sc11)
Scene('ka12', 'The Seven Perceivers', 'Each state configures the five differently.', 'Saptapramātṛ', '', 'perceivers', ['states','perceivers','configurations'], 'states', 'five states with different ring configs', 8.0, sc12)
Scene('ka13', 'Māyā Is the Night', 'The turning that makes stars visible.', 'Rātrī', '', 'night', ['maya','night','stars'], 'maya', 'dark field with stars appearing', 6.0, sc13)
Scene('ka14', 'Your Limits Are Your Signature', 'No two souls wear the same armor.', 'Svakīya', '', 'signature', ['unique','limits','signature'], 'individuality', 'multiple different ring configurations', 6.0, sc14)
Scene('ka15', 'Time Is a Gesture', 'A slicing of the eternal.', 'Kṣaṇa', '', 'gesture', ['time','gesture','slicing'], 'time', 'slicing gesture through luminous field', 8.0, sc15)
Scene('ka16', 'The Body as Garment', 'Karma spun into form.', 'Puryaṣṭaka', '', 'body', ['body','garment','karma'], 'embodiment', 'body silhouette with five woven colors', 8.0, sc16)
Scene('ka17', 'Both Faces of Armor', 'They reveal the finite as beautiful.', 'Saundarya', '', 'both', ['both','beauty','freedom'], 'seal', 'rings dissolving — translucent jewel-like', 8.0, sc17) [
    Scene('ka01', 'You Can Only Do So Much', 'Time moves whether you want it to or not.', 'Pariccheda', '', 'limits', ['limitation'], 'intro', 'five rings wrapping a center', 6.0, sc01),
    Scene('ka02', 'Five Pieces of Armor', 'Between you and freedom.', 'Kañcuka', '', 'armor', ['kancuka','covering'], 'intro', 'five named rings', 8.0, sc02),
    Scene('ka03', 'The Knot of Māyā', 'Pull tighter the more you wrestle it.', 'Māyāgranthi', '', 'knot', ['maya','knot','tighten'], 'doctrine', 'knot that tightens/loosens', 6.0, sc03),
    Scene('ka04', 'Kalā — Limited Agency', 'You can only lift so much.', 'Kalā', '', 'agency', ['kala','agency'], 'kancuka', 'lifting arm with ceiling breaking', 8.0, sc04),
    Scene('ka05', 'Vidyā — Limited Knowledge', 'You only see a sliver.', 'Vidyā', '', 'knowledge', ['vidya','sliver'], 'kancuka', 'narrow beam expanding to full field', 8.0, sc05),
    Scene('ka06', 'Rāga — Craving', 'You reach for what you lack.', 'Rāga', '', 'craving', ['raga','desire'], 'kancuka', 'reaching arm toward an object', 8.0, sc06),
    Scene('ka07', 'Kāla — Time', 'You move from A to B.', 'Kāla', '', 'time', ['kala','time'], 'kancuka', 'timeline with moving point + still now', 8.0, sc07),
    Scene('ka08', 'Niyati — Necessity', 'You reap what you sow.', 'Niyati', '', 'necessity', ['niyati','karma'], 'kancuka', 'chain of links with free hand', 8.0, sc08),
    Scene('ka09', 'The Mirror of Vidyā', 'An eye cannot see itself without a mirror.', 'Vimarśa', '', 'mirror', ['vidya','mirror','self-knowledge'], 'reflection', 'two eyes facing each other with mirror', 6.0, sc09),
    Scene('ka10', 'The Cage of Time', 'The words "just now" are a cage.', 'Kāla-pañjara', '', 'cage', ['time','cage','now'], 'reflection', '"just now" dissolving into cage bars', 6.0, sc10),
    Scene('ka11', 'The Fist That Closes', 'Contraction generates the heat of life.', 'Saṃkoca', '', 'fist', ['contraction','heat','life'], 'paradox', 'hand closing into fist with glow at center', 8.0, sc11),
    Scene('ka12', 'The Seven Perceivers', 'Each state configures the five differently.', 'Saptapramātṛ', '', 'perceivers', ['states','perceivers','configurations'], 'states', 'five states with different ring configs', 8.0, sc12),
    Scene('ka13', 'Māyā Is the Night', 'The turning that makes stars visible.', 'Rātrī', '', 'night', ['maya','night','stars'], 'maya', 'dark field with stars appearing', 6.0, sc13),
    Scene('ka14', 'Your Limits Are Your Signature', 'No two souls wear the same armor.', 'Svakīya', '', 'signature', ['unique','limits','signature'], 'individuality', 'multiple different ring configurations', 6.0, sc14),
    Scene('ka15', 'Time Is a Gesture', 'A slicing of the eternal.', 'Kṣaṇa', '', 'gesture', ['time','gesture','slicing'], 'time', 'slicing gesture through luminous field', 8.0, sc15),
    Scene('ka16', 'The Body as Garment', 'Karma spun into form.', 'Puryaṣṭaka', '', 'body', ['body','garment','karma'], 'embodiment', 'body silhouette with five woven colors', 8.0, sc16),
    Scene('ka17', 'Both Faces of Armor', 'They reveal the finite as beautiful.', 'Saundarya', '', 'both', ['both','beauty','freedom'], 'seal', 'rings dissolving — translucent jewel-like', 8.0, sc17),
]


def render_scene(scene: Scene):
    sdir = FRAMES_ROOT / scene.id
    sdir.mkdir(parents=True, exist_ok=True)
    nframes = int(FPS * scene.duration)
    expected = [sdir / f'frame_{i:04d}.jpg' for i in range(nframes)]
    if not all(p.exists() and p.stat().st_size > 1000 for p in expected):
        for i, path in enumerate(expected):
            if path.exists() and path.stat().st_size > 1000: continue
            t = i / max(1, nframes-1)
            im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            scene.draw_fn(im, t)
            dust(im, SEED + hash(scene.id)%10000 + i, 55)
            border(im)
            footer(im, scene.title, scene.subtitle, scene.term)
            im.convert('RGB').save(path, quality=95)
    out = SCENES_ROOT / f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size < 30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)], check=True)


def make_contact_sheet():
    thumbs = []
    for sc in SCENES:
        frame = FRAMES_ROOT / sc.id / f'frame_{int(10*sc.duration*0.72):04d}.jpg'
        if not frame.exists():
            frame = FRAMES_ROOT / sc.id / 'frame_0000.jpg'
            if not frame.exists(): continue
        im = Image.open(frame).convert('RGB').resize((320,180), Image.Resampling.LANCZOS)
        thumbs.append(im)
    rows = (len(thumbs)+3)//4
    sheet = Image.new('RGB', (4*320, rows*180), color=DEEP_VOID)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Kañcuka: The Armor of Limitation',
        'source_basis': 'Expansion Essay 2: "you\'re wearing armor" — 17 scenes mapping to specific beats of the essay.',
        'style': {'family': 'kancuka didactic visualization', 'background': 'warm dark and deep void', 'ink': 'gold, crimson, indigo, coral, slate, earth'},
        'fps': FPS, 'resolution': [W, H],
        'total_scenes': len(SCENES), 'total_duration_seconds': round(sum(s.duration for s in SCENES), 1),
        'scenes': [{'id': s.id, 'title': s.title, 'duration': s.duration} for s in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    d = '''# Expansion Essay 2 — Kañcuka: 17-Scene Breakdown

1. ka01 (6s) — You can only do so much. Five rings appear.
2. ka02 (8s) — Five pieces of armor. Named: kala, vidya, raga, kala, niyati.
3. ka03 (6s) — The knot of maya. Tightens when wrestled.
4. ka04 (8s) — Kala: limited agency. Ceiling breaks.
5. ka05 (8s) — Vidya: limited knowledge. Sliver opens to full field.
6. ka06 (8s) — Raga: craving. Reaching for what is lacking.
7. ka07 (8s) — Kala: time. A to B with still now at center.
8. ka08 (8s) — Niyati: necessity. Chain of karma with free hand.
9. ka09 (6s) — Eye cannot see itself. Vidya as mirror.
10. ka10 (6s) — Cage of time. "Just now" becomes bars.
11. ka11 (8s) — Fist that closes. Contraction generates heat.
12. ka12 (8s) — Seven perceivers. Each configures the five differently.
13. ka13 (6s) — Maya is night. Stars appear in darkness.
14. ka14 (6s) — Your limits your signature. Multiple unique configs.
15. ka15 (8s) — Time is a gesture. Slicing the eternal.
16. ka16 (8s) — Body as garment. Five colors woven into form.
17. ka17 (8s) — Both faces. Rings translucent. Unarmored always.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d, encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Kañcuka Pack — 17-scene direct essay visualization\n', encoding='utf-8')
    readme = f'# Kañcuka: The Armor of Limitation — 17 scenes ({sum(s.duration for s in SCENES):.0f}s total)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'kancuka_armor_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))


def make_zip():
    zpath = ROOT / 'kancuka_armor_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['kancuka_armor_animation.mp4','contact_sheet.jpg',
                     'scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md',
                     'STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):
            zf.write(mp4, arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat_file = ROOT / 'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT / 'kancuka_armor_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
