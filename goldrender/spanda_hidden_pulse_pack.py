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
SEED = 11112

DEEP_VOID = (14, 16, 24)
WARM_DARK = (22, 20, 22)
NIGHT = (18, 20, 30)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
SILVER = (196, 204, 222)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
CRIMSON = (154, 44, 58)
CORAL = (206, 108, 100)
TEAL = (92, 146, 148)
TEAL_LIGHT = (148, 186, 190)
INDIGO = (68, 78, 136)
VIOLET = (120, 104, 168)
LAVENDER = (166, 156, 196)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)
ROSE = (196, 104, 130)

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
    return (*c[:3], int(a))


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


def spanda_ground(seed, bg, glow_col, intensity=0.7):
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
    im.paste(spanda_ground(fs, WARM_DARK, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 300
    d.text((cx, 140), 'there is a pulse happening in you right now', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 168), 'that is not your heartbeat', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    p_cycle = (t * 0.6) % 1.0
    r = lerp(8, 170, ease_in_out(p_cycle))
    draw_glow(im, (cx, cy), int(r*0.5), GOLD_LIGHT, int(80*(1-r/170)), 14)
    d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(GOLD_LIGHT, int(180*(1-r/170))), width=2)
    r2 = lerp(200, 30, ease_in_out(p_cycle))
    d.ellipse((cx-r2, cy-r2*0.62, cx+r2, cy+r2*0.62), outline=rgba(GOLD, int(40*(1-r2/200))), width=1)
    d.text((100, 70), 'स्पन्द', font=DEVA_MED, fill=rgba(GOLD, 30))


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(spanda_ground(fs, WARM_DARK, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    d.text((cx, 150), 'most people never notice it', font=TERM_FONT, fill=PEARL, anchor='mm')
    p_cycle = (t * 0.5) % 1.0
    r = lerp(10, 140, ease_in_out(p_cycle))
    draw_glow(im, (cx, cy), int(r*0.4), GOLD, int(70*(1-r/140)), 12)
    d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(GOLD, int(160*(1-r/170))), width=2)
    d.text((cx-110, cy+48), 'स्पन्द', font=DEVA_MED, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx+130, cy+52), 'spanda', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, cy+100), 'the hidden pulse', font=SMALL_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(spanda_ground(fs, NIGHT, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 95), 'yasyonmeṣa-nimeṣābhyāṃ jagataḥ pralayodayau', font=DEVA_SMALL, fill=GOLD, anchor='mm')
    d.text((cx, 130), 'expansion = arising  ·  contraction = dissolution', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = 0.5 + 0.5*math.sin(t*math.pi)
    r1 = lerp(20, 190, prog)
    r2 = lerp(190, 20, prog)
    d.ellipse((cx-r1, cy-r1*0.62, cx+r1, cy+r1*0.62), outline=rgba(GOLD, 180), width=2)
    d.ellipse((cx-r2, cy-r2*0.62, cx+r2, cy+r2*0.62), outline=rgba(SILVER, 120), width=1)
    for i in range(12):
        a = i*2*math.pi/12
        x1 = cx + math.cos(a)*18
        y1 = cy + math.sin(a)*18*0.62
        x2 = cx + math.cos(a)*r1
        y2 = cy + math.sin(a)*r1*0.62
        draw_line_glow(im, [(x1, y1), (x2, y2)], mix(GOLD, SILVER, i/12), 1, 60, 3)
    draw_glow(im, (cx, cy), 16, GOLD_LIGHT, 90, 10)
    d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=rgba(WHITE, 220))


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(spanda_ground(fs, NIGHT, GOLD_LIGHT, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    d.text((cx, 120), 'a wheel', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 150), 'hub — awareness itself', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 172), 'spokes — will, cognition, action', font=SMALL_FONT, fill=MIST, anchor='mm')
    for r, col in [(50, GOLD), (100, SILVER), (150, GOLD), (180, SILVER)]:
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(col, 100), width=1)
    n = 12
    for i in range(n):
        a = t*0.1 + i*2*math.pi/n
        r = 170
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        col = CORAL if i%4==0 else TEAL if i%4==1 else INDIGO if i%4==2 else GOLD
        w = 3 if i%4==0 else 1
        draw_line_glow(im, [(cx, cy), (x, y)], col, w, 70, 4)
        d.ellipse((x-3, y-3, x+3, y+3), fill=rgba(col, 180))
    draw_glow(im, (cx, cy), 22, GOLD_LIGHT, 110, 12)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((cx, cy), 'cit', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')
    for i, (lab, col, dx) in enumerate([('icchā', CORAL, 0), ('jñāna', TEAL, 1), ('kriyā', INDIGO, 2)]):
        a = t*0.1 + dx*2*math.pi/3
        x = cx + math.cos(a)*200
        y = cy + math.sin(a)*200*0.62
        d.text((x, y-10), lab, font=SMALL_FONT, fill=col, anchor='mm')


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(spanda_ground(fs, DEEP_VOID, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    d.text((cx, 115), 'the cause of the creation and dissolution', font=SMALL_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 140), 'of the world of your experience', font=SMALL_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 170), 'is none other than your own true nature', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    for i in range(20):
        a = i*2*math.pi/20
        r = 160
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        draw_line_glow(im, [(cx, cy), (x, y)], mix(GOLD, SILVER, i/20), 1, 50, 3)
    for r, col in [(70, GOLD), (120, GOLD_LIGHT), (160, SILVER)]:
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(col, 140), width=2)
    draw_glow(im, (cx, cy), 24, GOLD_LIGHT, 120, 12)
    d.ellipse((cx-12, cy-12, cx+12, cy+12), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((cx, cy), 'you', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(spanda_ground(fs, DEEP_VOID, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 100), 'six names for one thing', font=TERM_FONT, fill=PEARL, anchor='mm')
    names = [('prāṇanā', 'vitality', CORAL), ('spanda', 'vibration', GOLD),
             ('sphurattā', 'effulgence', TEAL), ('viśrānti', 'repose', INDIGO),
             ('jīva', 'living being', ROSE), ('hṛdaya', 'heart', GOLD_LIGHT)]
    rads = [28, 52, 78, 106, 136, 168]
    for i in range(6):
        r = rads[i]
        phase = t*(0.15+i*0.04)
        rr = r + 6*math.sin(phase*math.pi*2)
        d.ellipse((cx-rr, cy-rr*0.6, cx+rr, cy+rr*0.6), outline=rgba(names[i][2], 180), width=2 if i%2 else 1)
        d.text((cx+rr+28, cy-6), names[i][0], font=TINY_FONT, fill=rgba(names[i][2], 200))
        d.text((cx+rr+28, cy+12), names[i][1], font=TINY_FONT, fill=rgba(names[i][2], 130))
    draw_glow(im, (cx, cy), 14, GOLD_LIGHT, 90, 10)
    d.ellipse((cx-5, cy-5, cx+5, cy+5), fill=rgba(WHITE, 220))


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(spanda_ground(fs, WARM_DARK, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 130), 'when you are about to speak', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 158), 'and the word is already there', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 186), 'before your mouth moves — that pulse', font=SMALL_FONT, fill=MIST, anchor='mm')
    for i in range(3):
        r = 80 + i*40
        d.ellipse((cx-r, cy+20-r*0.62, cx+r, cy+20+r*0.62), outline=rgba(GOLD, int(50-i*12)), width=1)
    shimmer = 0.5 + 0.5*math.sin(t*2*math.pi*1.5)
    draw_glow(im, (cx, 330), 22, GOLD_LIGHT, int(90*shimmer), 14)
    d.ellipse((cx-44, 300, cx+44, 360), outline=rgba(GOLD_LIGHT, int(180*shimmer)), width=2)
    d.ellipse((cx-34, 310, cx+34, 350), outline=rgba(WHITE, int(60*shimmer)), width=1)
    d.text((cx, 340), 'वाक्', font=DEVA_MED, fill=rgba(GOLD_LIGHT, int(200+55*shimmer)), anchor='mm')
    d.text((50, 80), 'स्पन्द', font=DEVA_SMALL, fill=rgba(GOLD, 25))
    if t > 0.6:
        d.ellipse((cx-50, 380, cx+50, 430), outline=rgba(CORAL, int(120*(t-0.6)*2.5)), width=2)


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(spanda_ground(fs, WARM_DARK, GOLD_LIGHT, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 105), 'say a word out loud. any word.', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'feel how the breath has to move,', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 155), 'how the throat shapes the air', font=SMALL_FONT, fill=MIST, anchor='mm')
    wave = []
    for i in range(80):
        u = i/79
        x = lerp(180, 1100, u)
        amp = 35 + 20*math.sin(u*math.pi)
        y = cy + 90 + math.sin(u*2*math.pi*3 + t*math.pi*2)*amp
        wave.append((x, y))
    draw_line_glow(im, wave, GOLD, 3, 120, 7)
    for i, ch in enumerate(['हं', 'सौः', 'ॐ']):
        u = (i+1)/4
        x = lerp(180, 1100, u)
        y = cy + 90 + math.sin(u*2*math.pi*3 + t*math.pi*2)*(35+20*math.sin(u*math.pi))
        d.text((int(x), int(y)-35), ch, font=DEVA_MED, fill=rgba(GOLD_LIGHT, 220), anchor='mm')
    d.text((cx, 470), 'mantra is the pulse itself taking shape as sound', font=SUB_FONT, fill=MIST, anchor='mm')


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(spanda_ground(fs, NIGHT, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    d.text((cx, 120), 'the mantra works because', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 148), 'it IS the pulse you started with', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 176), '— shaped into sound, riding the breath —', font=SMALL_FONT, fill=MIST, anchor='mm')
    r = 120 + 30*math.sin(t*math.pi*2)
    r2 = 160 + 20*math.sin(t*math.pi*2+0.7)
    d.ellipse((cx-r2, cy-r2*0.62, cx+r2, cy+r2*0.62), outline=rgba(SILVER, 60), width=1)
    d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(GOLD, 160), width=2)
    wave = []
    for i in range(60):
        u = i/59
        x = lerp(cx-r, cx+r, u)
        y = cy + math.sin(u*2*math.pi*2 + t*math.pi*2)*25
        wave.append((x, y))
    draw_line_glow(im, wave, GOLD_LIGHT, 2, 90, 5)
    for i in range(6):
        a = i*2*math.pi/6
        x = cx + math.cos(a)*r2
        y = cy + math.sin(a)*r2*0.62
        d.ellipse((x-2,y-2,x+2,y+2), fill=rgba(GOLD, 100))
    d.text((cx, cy+10), 'spandanātmatā', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')
    draw_glow(im, (cx, cy), 18, GOLD_LIGHT, 100, 10)
    d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=rgba(WHITE, 220))


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(spanda_ground(fs, NIGHT, TEAL, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 100), 'the rhythm of sensory activity', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 128), 'is essentially the pulse of consciousness', font=TERM_FONT, fill=TEAL, anchor='mm')
    senses = ['hearing', 'touch', 'sight', 'taste', 'smell']
    s_cols = [CORAL, GOLD, TEAL, INDIGO, VIOLET]
    for i in range(5):
        a = -math.pi/2 + i*2*math.pi/5
        x = cx + math.cos(a)*170
        y = cy + math.sin(a)*105
        of = 0.3 + 0.7*(0.5+0.5*math.sin(t*2.5 + i*1.3))
        rx = 28 * of
        draw_glow(im, (int(x), int(y)), 14, s_cols[i], 60, 10)
        d.ellipse((x-rx, y-26, x+rx, y+26), outline=rgba(s_cols[i], 190), width=2)
        if of > 0.4:
            d.ellipse((x-4, y-4, x+4, y+4), fill=rgba(WHITE, int(200*of)))
        d.text((x, y+40), senses[i], font=TINY_FONT, fill=s_cols[i], anchor='mm')
        draw_line_glow(im, [(cx, cy), (int(x), int(y))], mix(s_cols[i], GOLD, .3), 1, 50, 3)
    draw_glow(im, (cx, cy), 18, GOLD_LIGHT, 80, 10)
    d.ellipse((cx-7, cy-7, cx+7, cy+7), fill=rgba(WHITE, 220))
    d.text((cx, 470), 'unmeṣa — opening  ·  nimeṣa — closing', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 494), 'the wheel turns, and you call it experience', font=TINY_FONT, fill=SLATE, anchor='mm')


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(spanda_ground(fs, DEEP_VOID, GOLD, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 110), 'a tuning fork across a room', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 138), 'begins to ring when its note is struck', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    fx1, fx2 = 360, 920
    vib = 0.5 + 0.5*math.sin(t*4*math.pi)
    for i, fx in enumerate([fx1, fx2]):
        th = 50 + 25*vib*(1 if i==0 else 0.5+0.5*math.sin(t*2.5))
        col = GOLD if i==0 else mix(GOLD, GOLD_LIGHT, 0.5+0.5*math.sin(t*2))
        d.line((fx-6, cy-20, fx-6, cy-20-th), fill=rgba(col, 200), width=3)
        d.line((fx+6, cy-20, fx+6, cy-20-th), fill=rgba(col, 200), width=3)
        d.ellipse((fx-16, cy-5, fx+16, cy+15), fill=rgba(col, 80), outline=rgba(col, 180), width=2)
    d.text((fx1, cy-90), 'spanda', font=SMALL_FONT, fill=GOLD, anchor='mm')
    d.text((fx2, cy-90), 'mantra', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    r_pts = partial_polyline(bezier(
        (fx1+50, cy+30), (fx1+200, cy-20), (fx2-200, cy+60), (fx2-50, cy+30)
    ), smoothstep(0.1, 0.9, t))
    if len(r_pts) > 1:
        draw_line_glow(im, r_pts, GOLD_LIGHT, 2, 100, 6)
    d.text((cx, 475), 'mantra meets spanda by resonance', font=SUB_FONT, fill=MIST, anchor='mm')


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(spanda_ground(fs, WARM_DARK, CRIMSON, 0.6), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    d.text((cx, 100), 'the belly of the fish', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 128), 'pulled out of the water', font=TERM_FONT, fill=CORAL, anchor='mm')
    breath = 0.5 + 0.5*math.sin(t*math.pi*2)
    for i in range(5):
        r = 24 + i*34
        p = clamp(t*1.3 - i*0.1)
        if p <= 0: continue
        rr = r * (0.82 + 0.18*breath)
        col = mix(CRIMSON, GOLD_LIGHT, i/5)
        draw_glow(im, (cx, cy), int(rr*0.5), col, int(70*p*(1-i/6)), 14)
        d.ellipse((cx-rr, cy-rr*0.62, cx+rr, cy+rr*0.62), outline=rgba(col, int(190*p)), width=2)
    for i in range(5):
        a = i*2*math.pi/5 + t*0.3
        dr = 15*math.sin(t*3 + i*1.5)
        d.ellipse((cx-8+dr-2, cy+60+a*3, cx+8+dr+2, cy+80+a*3), fill=rgba(TEAL, 100), width=1)
    draw_glow(im, (cx, cy), 20, GOLD_LIGHT, 120, 10)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=rgba(WHITE, 255))
    d.text((cx, 475), 'every part of it alive in the same rhythm', font=SUB_FONT, fill=MIST, anchor='mm')


def sc13(im, t):
    fs = SEED + int(t*9973+6000) % 100000
    im.paste(spanda_ground(fs, DEEP_VOID, SILVER, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    d.text((cx, 95), 'this is the power of time,', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), 'established in the vital breath', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    layers = ['kāla', 'prāṇa', 'spanda', 'śūnya', 'citi']
    cols = [SLATE, TEAL, GOLD, SILVER, WHITE]
    widths = [260, 210, 160, 110, 60]
    pulse_pos = clamp(t * 1.2)
    for i in range(5):
        w = widths[i]
        a_start = math.pi * 0.08
        pts = arc_points(cx, cy, w, w*0.55, math.pi+a_start, 2*math.pi-a_start, 50)
        if len(pts) > 1:
            d.line(pts, fill=rgba(cols[i], 180), width=2)
        d.text((cx+w+30, cy-8), layers[i], font=SMALL_FONT, fill=rgba(cols[i], 200))
        pp = clamp((pulse_pos - i*0.12)*5)
        if pp > 0:
            cx2 = cx - w + 2*w*pp
            cy2 = cy + w*0.55 - 2*w*0.55*pp
            draw_glow(im, (int(cx2), int(cy2)), 8, GOLD_LIGHT, int(120*pp), 6)
    draw_glow(im, (cx, cy), 12, WHITE, 80, 10)
    d.ellipse((cx-4, cy-4, cx+4, cy+4), fill=rgba(WHITE, 220))
    d.text((cx, 475), 'time → breath → pulse → void → consciousness', font=SUB_FONT, fill=MIST, anchor='mm')


def sc14(im, t):
    fs = SEED + int(t*9973+6500) % 100000
    im.paste(spanda_ground(fs, NIGHT, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 120), 'the heartbeat in your wrist', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 148), 'the thought forming behind your eyes', font=TERM_FONT, fill=MIST, anchor='mm')
    d.text((cx, 176), 'the light shaping itself into this page', font=TERM_FONT, fill=MIST, anchor='mm')
    rng = np.random.default_rng(140)
    for i in range(14):
        x = float(rng.uniform(120, W-120))
        y = float(rng.uniform(180, H-180))
        col = mix(GOLD, CORAL, i/14)
        pr = 0.5 + 0.5*math.sin(t*3.5 + i*2.1)
        rr = 4 + 10*pr
        draw_glow(im, (int(x), int(y)), int(rr), col, int(60+60*pr), 8)
        d.ellipse((x-3, y-3, x+3, y+3), fill=rgba(WHITE, 200))
    draw_glow(im, (cx, cy), 20, GOLD_LIGHT, 90, 12)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=rgba(WHITE, 255))
    d.text((cx, 480), 'each is a real pulse of consciousness', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((cx, 503), 'a drum that has never stopped', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')


def sc15(im, t):
    fs = SEED + int(t*9973+7000) % 100000
    im.paste(spanda_ground(fs, DEEP_VOID, SILVER, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    d.text((cx, 105), 'all these pulses are waves', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 133), 'of one ocean that never moves', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    for i in range(5):
        pts = []
        for j in range(80):
            u = j/79
            x = lerp(150, 1130, u)
            y = cy + 60 + math.sin(u*2*math.pi*2 + t*i*0.3)*20 + (i-2)*30
            pts.append((x, y))
        draw_line_glow(im, pts, mix(SILVER, GOLD_LIGHT, i/5), 1, 80, 5)
    d.line((150, cy+110, 1130, cy+110), fill=rgba(GOLD_LIGHT, 100), width=1)
    d.line((150, cy+60, 1130, cy+60), fill=rgba(GOLD_LIGHT, 100), width=1)
    d.text((cx, 475), 'wave upon wave arises and merges back', font=SUB_FONT, fill=MIST, anchor='mm')


def sc16(im, t):
    fs = SEED + int(t*9973+7500) % 100000
    im.paste(spanda_ground(fs, WARM_DARK, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 100), 'play — krīḍā —', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 128), 'is vibration seeking out joy', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    n = 20
    for i in range(n):
        a = t*0.08 + i*2*math.pi/n
        r = lerp(15, 170 + 30*math.sin(t*math.pi*1.5 + i*0.3), ease_in_out(t))
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        col = mix(GOLD, CORAL, (i%7)/7) if i%2==0 else mix(SILVER, TEAL, (i%7)/7)
        draw_line_glow(im, [(cx, cy), (x, y)], col, 1 if i%3 else 2, 60, 4)
        d.ellipse((x-3, y-3, x+3, y+3), fill=rgba(col, 180))
    for r, col in [(140, GOLD), (95, GOLD_LIGHT), (45, WHITE)]:
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(col, 140), width=2)
    draw_glow(im, (cx, cy), 26, GOLD_LIGHT, 120, 12)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((cx, cy), 'krīḍā', font=DEVA_SMALL, fill=GOLD, anchor='mm')
    d.text((cx, 478), 'a king who pretends to be a foot soldier', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((cx, 500), 'simply to experience the joy of play', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')


def sc17(im, t):
    fs = SEED + int(t*9973+8000) % 100000
    im.paste(spanda_ground(fs, WARM_DARK, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    d.text((cx, 100), 'when you know yourself as the pulse', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 128), 'desire becomes creative power', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    for i in range(36):
        a = i*2*math.pi/36 + t*0.05
        r = lerp(20, 210, smoothstep(0.1, 0.9, t))
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        draw_line_glow(im, [(cx, cy), (x, y)], mix(GOLD_LIGHT, WHITE, i/36), 1, 50, 4)
    a1 = t*0.15
    x1 = cx + math.cos(a1)*180*(0.5+0.5*math.sin(t*2))
    y1 = cy + math.sin(a1)*180*0.62*(0.5+0.5*math.sin(t*2))
    draw_glow(im, (int(x1), int(y1)), 20, GOLD, 100, 12)
    d.ellipse((int(x1)-8, int(y1)-8, int(x1)+8, int(y1)+8), fill=rgba(WHITE, 220))
    a2 = t*0.15 + math.pi
    x2 = cx + math.cos(a2)*180*(0.5+0.5*math.cos(t*2))
    y2 = cy + math.sin(a2)*180*0.62*(0.5+0.5*math.cos(t*2))
    draw_glow(im, (int(x2), int(y2)), 18, SILVER, 90, 11)
    d.ellipse((int(x2)-6, int(y2)-6, int(x2)+6, int(y2)+6), fill=rgba(WHITE, 200))
    draw_glow(im, (cx, cy), 30, GOLD_LIGHT, 130, 14)
    d.ellipse((cx-12, cy-12, cx+12, cy+12), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((cx, 480), 'the sixth bliss: complete expansion — pūrṇavikāsa', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('sp01', 'The Hidden Pulse', 'Not your heartbeat.', 'Spanda', '', 'hidden', ['pulse'], 'intro', 'pulse ring vs heartbeat', 6.0, sc01),
    Scene('sp02', 'Most People Never Notice', 'They called it Spanda.', 'Spanda', '', 'named', ['spanda'], 'intro', 'pulse with label', 5.0, sc02),
    Scene('sp03', 'Opening and Closing', 'Expansion is arising, contraction dissolution.', 'Unmeṣa-nimeṣa', '', 'wheel', ['unmesha','nimesha'], 'doctrine', 'expanding/contracting wheel', 8.0, sc03),
    Scene('sp04', 'The Wheel of Powers', 'Hub = awareness. Spokes = will, cognition, action.', 'Śakti-cakra', '', 'wheel', ['iccha','jnana','kriya'], 'doctrine', 'wheel with labeled spokes', 6.0, sc04),
    Scene('sp05', 'Your Own True Nature', 'You are the cause of creation and dissolution.', 'Svātantrya', '', 'sovereignty', ['self','sovereignty'], 'doctrine', 'first-person at wheel hub', 8.0, sc05),
    Scene('sp06', 'Six Names, One Pulse', 'Prāṇanā, spanda, sphurattā, viśrānti, jīva, hṛdaya.', 'Ṣaḍ-nāma', '', 'names', ['six names'], 'anatomy', 'six labeled concentric rings', 10.0, sc06),
    Scene('sp07', 'The Word Before Speech', 'When a word arrives before your mouth moves — that pulse.', 'Anāgatā vāk', '', 'word', ['speech','intention'], 'experience', 'syllable shimmering before speech', 6.0, sc07),
    Scene('sp08', 'Say a Word Out Loud', 'Mantra is the pulse shaped into sound.', 'Mantra-spanda', '', 'mantra', ['breath','sound','word'], 'practice', 'breath wave with seed syllables', 8.0, sc08),
    Scene('sp09', 'It IS the Pulse', 'Riding the breath. One woven thrum.', 'Spandanātmatā', '', 'identity', ['identity','pulse','breath'], 'practice', 'pulse ring with internal wave', 8.0, sc09),
    Scene('sp10', 'Unmeṣa-Nimeṣa', 'Every perception — opening, closing.', 'Unmeṣa-nimeṣa', '', 'perception', ['senses','open','close'], 'perception', 'five sense-gates opening/closing', 8.0, sc10),
    Scene('sp11', 'Tuning Fork', 'Mantra meets spanda by resonance.', 'Anuranana', '', 'resonance', ['resonance','mantra','tuning'], 'resonance', 'two tuning forks vibrating', 8.0, sc11),
    Scene('sp12', 'The Fish-Belly Throb', 'The whole body one single pulse.', 'Matsyodara', '', 'fish', ['fish','belly','universal'], 'culmination', 'full-field pulsation with water drips', 10.0, sc12),
    Scene('sp13', 'The Cascading Layers', 'Time → breath → pulse → void → consciousness.', 'Krama', '', 'cascade', ['time','breath','consciousness'], 'integration', 'five dome layers with traveling pulse', 8.0, sc13),
    Scene('sp14', 'The Universe Is a Drum', 'Every pulse is real. The drum never stops.', 'Bherī', '', 'drum', ['pulse','real','drum'], 'manifestation', 'multiple independent pulsing points', 6.0, sc14),
    Scene('sp15', 'One Ocean', 'Waves arise and merge. The ocean never moves.', 'Sāmānyaspanda', '', 'ocean', ['waves','ocean','stillness'], 'unity', 'waves rising from still horizontal surface', 8.0, sc15),
    Scene('sp16', 'Krīḍā — Divine Play', 'The engine is a dancer.', 'Krīḍā', '', 'play', ['play','joy','dancer'], 'play', 'dancing asymmetrical wheel', 10.0, sc16),
    Scene('sp17', 'Desire Becomes Power', 'The sixth bliss — complete expansion.', 'Pūrṇavikāsa', '', 'seal', ['bliss','expansion','power'], 'seal', 'radiant center with sun and moon rising', 10.0, sc17),
]


def render_scene(scene: Scene):
    sdir = FRAMES_ROOT / scene.id
    sdir.mkdir(parents=True, exist_ok=True)
    nframes = int(FPS * scene.duration)
    expected = [sdir / f'frame_{i:04d}.jpg' for i in range(nframes)]
    if not all(p.exists() and p.stat().st_size > 1000 for p in expected):
        for i, path in enumerate(expected):
            if path.exists() and path.stat().st_size > 1000:
                continue
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
            frame = FRAMES_ROOT / sc.id / f'frame_0000.jpg'
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
        'project': 'Tantrāloka — Spanda: The Hidden Pulse of Consciousness',
        'source_basis': 'Expansion Essay 1: "the engine of consciousness" — 17 scenes, each mapping to a specific beat of the essay.',
        'style': {'family': 'pulse-centric essay visualization', 'background': 'deep void', 'ink': 'gold, silver, coral, teal', 'accent': 'crimson, violet, white'},
        'fps': FPS, 'resolution': [W, H],
        'total_scenes': len(SCENES), 'total_duration_seconds': round(sum(s.duration for s in SCENES), 1),
        'scenes': [{'id': s.id, 'title': s.title, 'duration': s.duration} for s in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    d = '''# Expansion Essay 1 — Spanda: 17-Scene Breakdown

Each scene maps to a specific beat in the essay and directly illustrates what is being said.

1. sp01 (6s) — There is a pulse that is not your heartbeat
2. sp02 (5s) — Most people never notice. Called Spanda.
3. sp03 (8s) — yasyonmeṣa-nimeṣābhyām: expansion/contraction
4. sp04 (6s) — Wheel: hub + spokes (will, cognition, action)
5. sp05 (8s) — Kallata: your own true nature is the cause
6. sp06 (10s) — Six names for one pulse
7. sp07 (6s) — Word arrives before speech
8. sp08 (8s) — Say a word — mantra shaped into sound
9. sp09 (8s) — It IS the pulse — spandanātmatā
10. sp10 (8s) — Unmeṣa-nimeṣa: perception as pulse
11. sp11 (8s) — Tuning fork resonance
12. sp12 (10s) — Fish-belly throb — universal spanda
13. sp13 (8s) — Cascading layers: time→breath→spanda→void→consciousness
14. sp14 (6s) — Every pulse real — universe is a drum
15. sp15 (8s) — One ocean never moves
16. sp16 (10s) — Krīḍā: play seeking joy
17. sp17 (10s) — Desire becomes creative power — pūrṇavikāsa

Total: 17 scenes, ~129s
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d, encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Spanda Pack — 17-scene direct essay visualization', encoding='utf-8')
    readme = f'# Spanda: The Hidden Pulse — 17 scenes ({sum(s.duration for s in SCENES):.0f}s total)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'spanda_hidden_pulse_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))


def make_zip():
    zpath = ROOT / 'spanda_hidden_pulse_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['spanda_hidden_pulse_animation.mp4','contact_sheet.jpg',
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
    combined = ROOT / 'spanda_hidden_pulse_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
