#!/usr/bin/env python3
from __future__ import annotations

import json, math, os, random, shutil, subprocess, textwrap, zipfile
from dataclasses import dataclass, asdict
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
SEED = 36036

# Kashmir Shaiva palette
PARCHMENT = (240, 230, 208)
PARCHMENT_LIGHT = (248, 242, 226)
INK = (38, 31, 29)
UMBER = (76, 58, 45)
CRIMSON = (142, 43, 55)
SAFFRON = (204, 148, 57)
GOLD = (183, 142, 68)
GOLD_LIGHT = (235, 206, 128)
INDIGO = (52, 66, 107)
BLUE_GREY = (103, 120, 154)
TEAL = (85, 132, 132)
SLATE = (92, 97, 104)
WHITE = (250, 246, 237)
NIGHT = (24, 28, 40)
LOTUS_PINK = (191, 110, 132)
EARTH = (117, 96, 66)
GREEN = (97, 132, 95)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
DEVA_FONT = ImageFont.truetype(FONT_DEVA, 34)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1, c2, t: float):
    return tuple(int(lerp(a, b, clamp(t))) for a, b in zip(c1, c2))


def rgba(c, a=255):
    return (*c[:3], int(a))


def parchment(seed: int, dark: bool = False) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    col = np.array(NIGHT if dark else PARCHMENT, dtype=np.float32)
    base[:] = col
    coarse = rng.normal(0, 1, (40, 70)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse - coarse.min()) / (np.ptp(coarse) + 1e-6) * 255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32) - 128) / 128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None] * (4.5 if not dark else 3.2)
    base += fine[..., None] * (1.6 if not dark else 1.2)
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2) / (W/2)
    dy = (yy - H/2) / (H/2)
    vign = np.clip((dx*dx + dy*dy) * 5.0, 0, 16)
    if not dark:
        base -= vign[..., None]
    else:
        base -= vign[..., None] * 0.4
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def draw_glow(im: Image.Image, xy, radius, color, alpha=160, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im: Image.Image, pts, color, width=3, alpha=160, blur=10):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1, width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+70)), width=width, joint='curve')


def footer(im: Image.Image, title: str, subtitle: str, term: str | None = None, deva: str | None = None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(247,239,219,218), outline=rgba(UMBER, 80), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=INK)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=UMBER)
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-120-tw, y0+25), term, font=TERM_FONT, fill=CRIMSON)
    if deva:
        d.text((W-240, y0+55), deva, font=DEVA_SMALL, fill=INDIGO)


def border(im: Image.Image):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(UMBER, 140), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 120), width=1)
    for x, y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, CRIMSON, GOLD_LIGHT)


def partial_polyline(points, amount: float):
    amount = clamp(amount)
    if amount <= 0:
        return []
    if amount >= 1:
        return points
    f = amount * (len(points)-1)
    idx = int(f)
    frac = f - idx
    out = list(points[:idx+1])
    if idx + 1 < len(points):
        a = points[idx]; b = points[idx+1]
        out.append((lerp(a[0], b[0], frac), lerp(a[1], b[1], frac)))
    return out


def bezier(p0, p1, p2, p3, n=100):
    pts = []
    for i in range(n):
        t = i/(n-1)
        u = 1-t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        pts.append((x,y))
    return pts


def regular_polygon(cx, cy, r, n, rot=-math.pi/2):
    return [(cx + math.cos(rot+2*math.pi*i/n)*r, cy + math.sin(rot+2*math.pi*i/n)*r) for i in range(n)]


def star_points(cx, cy, r1, r2, n=8, rot=-math.pi/2):
    pts = []
    for i in range(n*2):
        r = r1 if i % 2 == 0 else r2
        a = rot + math.pi*i/n
        pts.append((cx + math.cos(a)*r, cy + math.sin(a)*r))
    return pts


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42, y-r*0.42, x+r*0.42, y+r*0.42), fill=rgba(outer, 150), outline=rgba(inner, 200), width=1)
    draw.ellipse((cx-r*0.42, cy-r*0.42, cx+r*0.42, cy+r*0.42), fill=rgba(inner, 150), outline=rgba(outer, 220), width=2)


def draw_lotus(draw, cx, cy, scale=1.0, color=CRIMSON, fill=(0,0,0,0), petals=8):
    for i in range(petals):
        ang = -math.pi/2 + (i-(petals-1)/2)*0.28
        rx = 20*scale; ry = 50*scale
        pts = []
        for t in np.linspace(0, math.pi, 20):
            x = math.sin(t)*rx
            y = -math.cos(t)*ry*0.65
            xr = x*math.cos(ang)-y*math.sin(ang)
            yr = x*math.sin(ang)+y*math.cos(ang)
            pts.append((cx+xr, cy+yr))
        for t in np.linspace(math.pi, 0, 20):
            x = math.sin(t)*rx*0.5
            y = math.cos(t)*ry*0.2
            xr = x*math.cos(ang)-y*math.sin(ang)
            yr = x*math.sin(ang)+y*math.cos(ang)
            pts.append((cx+xr, cy+yr))
        draw.polygon(pts, outline=rgba(color, 200), fill=fill)
    draw.line((cx-48*scale, cy+28*scale, cx+48*scale, cy+28*scale), fill=rgba(color, 180), width=max(1,int(2*scale)))


def draw_eye(draw, cx, cy, scale=1.0, color=INDIGO):
    bbox = (cx-58*scale, cy-28*scale, cx+58*scale, cy+28*scale)
    draw.arc(bbox, 15, 165, fill=rgba(color, 220), width=max(1, int(3*scale)))
    draw.arc(bbox, 195, 345, fill=rgba(color, 220), width=max(1, int(3*scale)))
    draw.ellipse((cx-12*scale, cy-12*scale, cx+12*scale, cy+12*scale), fill=rgba(color, 210))
    draw.ellipse((cx-4*scale, cy-4*scale, cx+4*scale, cy+4*scale), fill=rgba(WHITE, 255))


def draw_trident(draw, cx, cy, scale=1.0, color=CRIMSON):
    w = 6*scale
    draw.line((cx, cy-60*scale, cx, cy+46*scale), fill=rgba(color, 210), width=max(1,int(w)))
    draw.arc((cx-42*scale, cy-76*scale, cx, cy-18*scale), 250, 80, fill=rgba(color,210), width=max(1,int(w)))
    draw.arc((cx, cy-76*scale, cx+42*scale, cy-18*scale), 100, 290, fill=rgba(color,210), width=max(1,int(w)))
    draw.arc((cx-18*scale, cy-72*scale, cx+18*scale, cy-20*scale), 180, 360, fill=rgba(color,210), width=max(1,int(w)))


def draw_silhouette(draw, cx, cy, scale=1.0, color=UMBER):
    draw.ellipse((cx-16*scale, cy-72*scale, cx+16*scale, cy-40*scale), fill=rgba(color, 190))
    body = [(cx-40*scale, cy+20*scale), (cx-30*scale, cy-22*scale), (cx-16*scale, cy-42*scale),
            (cx+16*scale, cy-42*scale), (cx+30*scale, cy-22*scale), (cx+40*scale, cy+20*scale)]
    draw.polygon(body, fill=rgba(color, 170))
    draw.arc((cx-52*scale, cy-8*scale, cx+52*scale, cy+62*scale), 200, 340, fill=rgba(color, 180), width=max(1, int(3*scale)))


def draw_wave_field(im, bbox, lines=11, amp=22, color=INDIGO, phase=0.0, alpha=110):
    x0,y0,x1,y1 = bbox
    ov = layer(); d = ImageDraw.Draw(ov)
    for i in range(lines):
        yy = lerp(y0, y1, i/(lines-1 if lines>1 else 1))
        pts = []
        for j in range(70):
            t = j/69
            x = lerp(x0, x1, t)
            y = yy + math.sin(t*2*math.pi*2 + phase + i*0.45) * amp * math.sin(math.pi*i/max(1,lines-1))
            pts.append((x, y))
        d.line(pts, fill=rgba(color, alpha), width=2)
    ov = ov.filter(ImageFilter.GaussianBlur(1.5))
    im.alpha_composite(ov)


def draw_ring_ladder(draw, cx, y_top, y_bottom, count, progress, color=SLATE, width=3):
    for i in range(count):
        s = clamp(progress*1.18 - i*0.055)
        if s <= 0:
            continue
        y = lerp(y_top, y_bottom, i/(count-1 if count>1 else 1))
        rx = lerp(25, 105, i/(count-1 if count>1 else 1))
        ry = lerp(9, 26, i/(count-1 if count>1 else 1))
        draw.arc((cx-rx, y-ry, cx+rx, y+ry), 190, 350, fill=rgba(color, int(160*s)), width=width)
        draw.arc((cx-rx, y-ry, cx+rx, y+ry), 10, 170, fill=rgba(mix(color, WHITE, .55), int(125*s)), width=max(1, width-1))


def draw_grid(draw, x0, y0, x1, y1, rows, cols, color=UMBER):
    draw.rounded_rectangle((x0, y0, x1, y1), radius=16, outline=rgba(color, 150), width=2)
    for r in range(1, rows):
        y = lerp(y0, y1, r/rows)
        draw.line((x0, y, x1, y), fill=rgba(color, 110), width=1)
    for c in range(1, cols):
        x = lerp(x0, x1, c/cols)
        draw.line((x, y0, x, y1), fill=rgba(color, 90), width=1)


def list_text(draw, items, x, y, leading=28, color=INK, font=None):
    font = font or SUB_FONT
    for i, txt in enumerate(items):
        draw.text((x, y + i*leading), txt, font=font, fill=color)


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


# ---------- Scene functions ----------

def scene01(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    a = ease_in_out(t)
    for r in [50, 95, 145, 205]:
        d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=rgba(mix(GOLD, WHITE, .55), 65), width=1)
    draw_glow(im, (cx, cy), 90, GOLD_LIGHT, 160, 30)
    rr = 14 + 10*a
    d.ellipse((cx-rr, cy-rr, cx+rr, cy+rr), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    for i in range(16):
        ang = 2*math.pi*i/16 + t*0.06
        x2 = cx + math.cos(ang)*220
        y2 = cy + math.sin(ang)*120
        draw_line_glow(im, [(cx, cy), (x2, y2)], mix(GOLD, WHITE, .25), 2, 90, 7)
    draw_lotus(d, cx, 440, 1.4, color=CRIMSON, fill=rgba(LOTUS_PINK, 45))
    d.text((150, 128), 'चितिः', font=DEVA_FONT, fill=rgba(CRIMSON, 220))
    d.text((935, 126), 'अनुत्तरम्', font=DEVA_FONT, fill=rgba(INDIGO, 220))


def scene02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 290
    pulse = 0.55 + 0.45*math.sin(2*math.pi*t)
    for i in range(8):
        r = 32 + i*42 + pulse*10
        alpha = int(160 * (1 - i/8) * (0.55 + 0.45*pulse))
        d.ellipse((cx-r, cy-r*0.72, cx+r, cy+r*0.72), outline=rgba(mix(INDIGO, GOLD_LIGHT, i/8), alpha), width=2)
    draw_glow(im, (cx, cy), 55, WHITE, 150, 16)
    path = bezier((300, 415), (480, 350+math.sin(t*2*math.pi)*18), (790, 480-math.sin(t*2*math.pi)*18), (980, 415), 100)
    draw_line_glow(im, path, CRIMSON, 4, 130, 8)
    draw_wave_field(im, (280, 180, 1000, 420), 10, 18, color=BLUE_GREY, phase=t*2*math.pi, alpha=90)


def scene03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    draw_glow(im, (cx, cy), 80, GOLD_LIGHT, 140, 22)
    d.ellipse((cx-18, cy-18, cx+18, cy+18), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    tri = regular_polygon(cx, cy+62, 70, 3, rot=math.pi/2)
    d.polygon(tri, outline=rgba(SAFFRON, 210), fill=rgba((250,242,220), 90))
    for i in range(3):
        ang0 = t*2*math.pi + i*2*math.pi/3
        pts = []
        for j in range(80):
            u = j/79
            r = 22 + 210*u
            a = ang0 + 3.2*u
            x = cx + math.cos(a)*r*0.9
            y = cy + 60 + math.sin(a)*r*0.52
            pts.append((x,y))
        draw_line_glow(im, pts, CRIMSON if i==0 else mix(CRIMSON, GOLD_LIGHT, i/2), 3, 125, 7)
    d.text((520, 508), 'Śiva', font=TERM_FONT, fill=INK, anchor='mm')
    d.text((760, 508), 'Śakti', font=TERM_FONT, fill=INK, anchor='mm')


def scene04(im, t):
    d = ImageDraw.Draw(im)
    cx, top = W/2, 170
    draw_glow(im, (cx, top), 85, GOLD_LIGHT, 150, 25)
    d.ellipse((cx-20, top-20, cx+20, top+20), fill=rgba(WHITE,255))
    for i in range(11):
        s = clamp(t*1.2 - i*0.06)
        if s <= 0: continue
        y = 220 + i*26
        w = 26 + i*48
        d.arc((cx-w, y-16, cx+w, y+16), 200, 340, fill=rgba(mix(GOLD, WHITE, .35), int(170*s)), width=2)
    d.text((cx, 485), 'aham', font=ImageFont.truetype(FONT_SERIF_BOLD, 44), fill=rgba(CRIMSON, 210), anchor='mm')
    d.text((cx+160, 502), 'idam', font=ImageFont.truetype(FONT_SERIF, 26), fill=rgba(INDIGO, 140), anchor='mm')


def scene05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    draw_glow(im, (cx, cy), 62, WHITE, 130, 18)
    d.text((cx-118, 200), 'idam', font=ImageFont.truetype(FONT_SERIF_BOLD, 40), fill=rgba(INDIGO, 210), anchor='mm')
    d.text((cx+110, 214), 'aham', font=ImageFont.truetype(FONT_SERIF, 24), fill=rgba(CRIMSON, 160), anchor='mm')
    for i in range(8):
        ang = math.pi/6 + i*math.pi/7 + t*0.1
        r = 145 + 18*math.sin(t*2*math.pi + i)
        x = cx + math.cos(ang)*r
        y = cy + 45 + math.sin(ang)*r*0.55
        d.ellipse((x-16, y-16, x+16, y+16), fill=rgba(mix(INDIGO, GOLD_LIGHT, i/8), 130), outline=rgba(UMBER, 100), width=1)
        draw_line_glow(im, [(cx, cy), (x, y)], GOLD, 2, 90, 6)
    star = star_points(cx, cy, 46, 20, 6)
    d.polygon(star, outline=rgba(SAFFRON, 220), fill=rgba((250,240,220), 70))


def scene06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    tri1 = regular_polygon(cx-90*(1-t*0.2), cy, 70, 3, rot=-math.pi/2)
    tri2 = regular_polygon(cx+90*(1-t*0.2), cy, 70, 3, rot=math.pi/2)
    d.polygon(tri1, outline=rgba(CRIMSON, 200), fill=rgba((255,230,230), 55))
    d.polygon(tri2, outline=rgba(INDIGO, 200), fill=rgba((225,230,255), 55))
    inter = star_points(cx, cy, 74, 40, 3, rot=-math.pi/2+t*0.15)
    d.polygon(inter, outline=rgba(GOLD, 220), fill=rgba((250,242,220), 40))
    draw_lotus(d, cx, 430, 1.05, color=GOLD, fill=rgba((250,240,220), 30), petals=6)
    d.text((cx, 515), 'balance of “I” and “This”', font=SUB_FONT, fill=UMBER, anchor='mm')


def scene07(im, t):
    d = ImageDraw.Draw(im)
    x0,y0,x1,y1 = 270, 130, 1010, 470
    # clear upper field
    draw_glow(im, (640, 170), 45, GOLD_LIGHT, 120, 12)
    prog = smoothstep(.1, .8, t)
    for i in range(9):
        a = clamp(prog*1.2 - i*0.07)
        y = lerp(y0+30, y1-30, i/8)
        pts = bezier((x0, y), (420, y-25), (860, y+25), (x1, y), 90)
        pts = partial_polyline(pts, a)
        if len(pts) > 1:
            draw_line_glow(im, pts, mix(SLATE, INDIGO, i/10), 2, 95, 6)
    for j in range(6):
        a = clamp(prog*1.1 - j*0.09)
        x = lerp(x0+40, x1-40, j/5)
        pts = bezier((x, y0), (x-40, 220), (x+40, 390), (x, y1), 80)
        pts = partial_polyline(pts, a)
        if len(pts) > 1:
            draw_line_glow(im, pts, mix(UMBER, GOLD, .3), 2, 75, 5)
    d.rounded_rectangle((565, 205, 715, 360), radius=18, outline=rgba(CRIMSON, 190), width=3)
    d.text((640, 282), 'Māyā', font=ImageFont.truetype(FONT_SERIF_BOLD, 33), fill=CRIMSON, anchor='mm')


def scene08(im, t):
    d = ImageDraw.Draw(im)
    cx = W/2
    labels = ['kalā', 'vidyā', 'rāga', 'kāla', 'niyati']
    cols = [SAFFRON, INDIGO, LOTUS_PINK, BLUE_GREY, SLATE]
    for i, lab in enumerate(labels):
        a = clamp(t*1.25 - i*0.1)
        y = 150 + i*68
        rx = 66 + i*40
        ry = 22 + i*7
        d.arc((cx-rx, y-ry, cx+rx, y+ry), 180, 360, fill=rgba(cols[i], int(180*a)), width=3)
        d.arc((cx-rx, y-ry, cx+rx, y+ry), 0, 180, fill=rgba(mix(cols[i], WHITE, .4), int(90*a)), width=2)
        d.text((cx+195, y-8), lab, font=TERM_FONT, fill=rgba(cols[i], int(210*a)))
    draw_silhouette(d, cx, 470, 1.2, color=UMBER)
    draw_glow(im, (cx, 430), 35, WHITE, 90, 9)


def scene09(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    draw_glow(im, (cx, cy), 40, WHITE, 120, 10)
    d.ellipse((cx-85, cy-85, cx+85, cy+85), outline=rgba(GOLD, 160), width=2)
    d.ellipse((cx-145, cy-145, cx+145, cy+145), outline=rgba(INDIGO, 110), width=1)
    draw_silhouette(d, cx, cy+40, 1.15, color=UMBER)
    for i in range(12):
        ang = i*2*math.pi/12 + t*0.08
        r = 160 + 12*math.sin(t*2*math.pi+i)
        x = cx + math.cos(ang)*r
        y = cy + math.sin(ang)*r*0.65
        d.ellipse((x-6,y-6,x+6,y+6), fill=rgba(mix(GOLD, INDIGO, i/12), 180))
        d.line((cx,cy,x,y), fill=rgba(mix(SLATE, GOLD, .4), 60), width=1)


def scene10(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    colors = [TEAL, SAFFRON, CRIMSON]
    labels = ['sattva', 'rajas', 'tamas']
    for i in range(3):
        ang0 = -math.pi/2 + i*2*math.pi/3 + t*0.1*(1 if i!=2 else -1)
        pts=[]
        for j in range(110):
            u = j/109
            r = 40 + 210*u
            a = ang0 + (1.9+0.2*i)*u
            x = cx + math.cos(a)*r*0.96
            y = cy + math.sin(a)*r*0.56
            pts.append((x,y))
        draw_line_glow(im, pts, colors[i], 4, 120, 6)
        d.text((170+i*180, 505), labels[i], font=TERM_FONT, fill=colors[i])
    d.ellipse((cx-28, cy-28, cx+28, cy+28), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)


def scene11(im, t):
    d = ImageDraw.Draw(im)
    xs = [330, 640, 950]
    labels = ['Buddhi', 'Ahaṃkāra', 'Manas']
    motifs = ['mirror', 'knot', 'net']
    cols = [INDIGO, CRIMSON, SLATE]
    for i, x in enumerate(xs):
        a = clamp(t*1.25 - i*0.08)
        d.rounded_rectangle((x-110, 150, x+110, 420), radius=18, outline=rgba(cols[i], int(190*a)), width=3, fill=rgba(mix(PARCHMENT_LIGHT, cols[i], .06), 60))
        if motifs[i] == 'mirror':
            d.ellipse((x-55, 200, x+55, 310), outline=rgba(cols[i], 220), width=3)
            d.line((x, 310, x, 350), fill=rgba(cols[i], 220), width=4)
            d.arc((x-30, 340, x+30, 380), 0, 180, fill=rgba(cols[i],220), width=4)
        elif motifs[i] == 'knot':
            d.arc((x-58, 208, x+8, 286), 35, 320, fill=rgba(cols[i],220), width=6)
            d.arc((x-8, 224, x+58, 302), 215, 140, fill=rgba(cols[i],220), width=6)
        else:
            for p in [(x-44,230),(x,210),(x+44,240),(x-30,294),(x+28,300),(x,342)]:
                d.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5), fill=rgba(cols[i],220))
            lines=[((x-44,230),(x,210)),((x,210),(x+44,240)),((x-44,230),(x-30,294)),((x,210),(x-30,294)),((x+44,240),(x+28,300)),((x-30,294),(x,342)),((x+28,300),(x,342))]
            for a1,b1 in lines:
                d.line((a1,b1), fill=rgba(cols[i],180), width=3)
        d.text((x, 382), labels[i], font=TERM_FONT, fill=cols[i], anchor='mm')
    d.text((640, 480), 'the inner instrument', font=ImageFont.truetype(FONT_SERIF, 26), fill=UMBER, anchor='mm')


def scene12(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 292
    draw_lotus(d, cx, cy+55, 1.0, color=INDIGO, fill=rgba((220,225,240), 30), petals=5)
    positions = [(cx-180, cy-10), (cx-85, cy-115), (cx+85, cy-115), (cx+180, cy-8), (cx, cy+120)]
    names = ['hearing', 'touch', 'sight', 'taste', 'smell']
    for i, (x,y) in enumerate(positions):
        a = clamp(t*1.3 - i*0.08)
        d.ellipse((x-42,y-42,x+42,y+42), fill=rgba((245,242,230),100), outline=rgba(INDIGO, int(180*a)), width=2)
        if i == 0:
            d.arc((x-18,y-18,x+6,y+6), 250, 40, fill=rgba(INDIGO,220), width=3)
            d.arc((x-30,y-26,x+18,y+18), 250, 40, fill=rgba(INDIGO,160), width=2)
        elif i == 1:
            d.rectangle((x-10,y-18,x+10,y+16), outline=rgba(INDIGO,220), width=2)
            for dx in [-18,-8,0,8,18]: d.line((x+dx,y+16,x+dx,y+30), fill=rgba(INDIGO,200), width=2)
        elif i == 2:
            draw_eye(d, x, y, 0.52, INDIGO)
        elif i == 3:
            d.arc((x-20,y-20,x+20,y+20), 30, 150, fill=rgba(INDIGO,220), width=3)
            d.line((x,y+20,x,y+8), fill=rgba(INDIGO,220), width=3)
        else:
            d.arc((x-18,y-18,x+18,y+25), 210, 330, fill=rgba(INDIGO,220), width=3)
            d.line((x,y-18,x,y+18), fill=rgba(INDIGO,220), width=3)
        d.text((x, y+56), names[i], font=SMALL_FONT, fill=UMBER, anchor='mm')
    d.text((cx, 490), 'five avenues of knowing', font=SUB_FONT, fill=UMBER, anchor='mm')


def scene13(im, t):
    d = ImageDraw.Draw(im)
    centers = [(250,240),(460,190),(640,325),(830,190),(1030,240)]
    names = ['speech','grasping','locomotion','release','generation']
    cols = [CRIMSON, SAFFRON, INDIGO, SLATE, LOTUS_PINK]
    for i,(x,y) in enumerate(centers):
        a = clamp(t*1.25 - i*0.08)
        d.ellipse((x-48,y-48,x+48,y+48), outline=rgba(cols[i], int(190*a)), width=3, fill=rgba(mix(PARCHMENT_LIGHT, cols[i], .05), 55))
        if i == 0:
            for k in range(3):
                pts = [(x-14, y-10+k*10), (x+30, y-20+k*6), (x+48, y-8+k*10)]
                d.arc((x+18+k*8,y-24+k*5,x+56+k*8,y+10+k*5), 220, 320, fill=rgba(cols[i],200), width=2)
        elif i == 1:
            d.rectangle((x-10,y-18,x+10,y+18), outline=rgba(cols[i],220), width=2)
            for dx in [-18,-8,0,8,18]: d.line((x+dx,y+18,x+dx,y+32), fill=rgba(cols[i],220), width=2)
        elif i == 2:
            d.line((x-8,y-12,x-22,y+24), fill=rgba(cols[i],220), width=4)
            d.line((x+8,y-12,x+22,y+24), fill=rgba(cols[i],220), width=4)
            d.line((x-20,y+8,x+20,y+8), fill=rgba(cols[i],220), width=4)
        elif i == 3:
            d.arc((x-20,y-10,x+20,y+28), 200, 340, fill=rgba(cols[i],220), width=3)
            d.line((x-18,y+9,x+18,y+9), fill=rgba(cols[i],220), width=3)
        else:
            draw_lotus(d, x, y+6, 0.42, color=cols[i], fill=rgba(cols[i], 30), petals=4)
        d.text((x, y+62), names[i], font=SMALL_FONT, fill=UMBER, anchor='mm')
    for i in range(4):
        draw_line_glow(im, [(centers[i][0]+50, centers[i][1]), (centers[i+1][0]-50, centers[i+1][1])], mix(cols[i], cols[i+1], .5), 2, 70, 4)


def scene14(im, t):
    d = ImageDraw.Draw(im)
    names = ['śabda','sparśa','rūpa','rasa','gandha']
    for i, name in enumerate(names):
        x = 180 + i*220
        a = clamp(t*1.2 - i*0.08)
        d.ellipse((x-60,260-60,x+60,260+60), outline=rgba(INDIGO, int(180*a)), width=2, fill=rgba((245,242,232),60))
        if i == 0:
            for k in range(4):
                d.arc((x-35-k*10,240-k*6,x+35+k*10,280+k*6), 220, 320, fill=rgba(INDIGO,220-k*25), width=2)
        elif i == 1:
            draw_wave_field(im, (x-48, 220, x+48, 300), 5, 10, color=TEAL, phase=t*2*math.pi+i, alpha=120)
        elif i == 2:
            draw_glow(im, (x,260), 22, GOLD_LIGHT, 140, 10)
            draw_eye(d, x, 260, 0.45, INDIGO)
        elif i == 3:
            d.polygon([(x,210),(x-18,270),(x,320),(x+18,270)], outline=rgba(BLUE_GREY,220), fill=rgba((220,235,255),70))
        else:
            for r in [12,24,36]: d.arc((x-r,260-r,x+r,260+r), 0, 300, fill=rgba(SLATE,180), width=2)
        d.text((x, 342), name, font=TERM_FONT, fill=CRIMSON if i%2==0 else INDIGO, anchor='mm')


def scene15(im, t):
    d = ImageDraw.Draw(im)
    names = ['ākāśa','vāyu','tejas','ap','pṛthivī']
    cols = [NIGHT, TEAL, SAFFRON, BLUE_GREY, EARTH]
    xs = [170, 390, 610, 830, 1050]
    for i, x in enumerate(xs):
        a = clamp(t*1.15 - i*0.08)
        d.ellipse((x-70,225,x+70,365), outline=rgba(cols[i], int(190*a)), width=3, fill=rgba(mix(PARCHMENT_LIGHT, cols[i], .08),65))
        if i == 0:
            for ang in np.linspace(0, 2*math.pi, 14, endpoint=False):
                sx = x + math.cos(ang)*38; sy = 295 + math.sin(ang)*38
                d.ellipse((sx-2,sy-2,sx+2,sy+2), fill=rgba(GOLD_LIGHT,220))
        elif i == 1:
            for k in range(4):
                pts = [(x-48, 275+k*12), (x-12, 260+k*6), (x+22, 290+k*8), (x+46, 275+k*12)]
                d.line(pts, fill=rgba(TEAL,200), width=3)
        elif i == 2:
            flame=[(x,220),(x-24,286),(x-8,335),(x+4,308),(x+18,348),(x+28,296)]
            d.polygon(flame, outline=rgba(SAFFRON,220), fill=rgba((250,180,80),90))
        elif i == 3:
            d.arc((x-48, 255, x+48, 333), 200, 340, fill=rgba(BLUE_GREY,220), width=4)
            d.arc((x-30, 240, x+30, 320), 180, 320, fill=rgba(BLUE_GREY,160), width=3)
            d.ellipse((x-10,240,x+10,260), fill=rgba((220,235,255),120))
        else:
            d.polygon([(x-44,332),(x-10,258),(x+12,302),(x+40,246),(x+56,332)], outline=rgba(EARTH,220), fill=rgba((170,145,105),80))
        d.text((x, 392), names[i], font=TERM_FONT, fill=cols[i], anchor='mm')


def scene16(im, t):
    d = ImageDraw.Draw(im)
    cx = W/2
    draw_glow(im, (cx, 120), 55, GOLD_LIGHT, 130, 18)
    d.ellipse((cx-14,106,cx+14,134), fill=rgba(WHITE,255))
    levels = [120, 160, 210, 265, 325, 390, 460]
    counts = [1, 2, 2, 6, 3, 5, 5]
    idx = 1
    for li,(y,c) in enumerate(zip(levels,counts)):
        for j in range(c):
            s = clamp(t*1.2 - idx*0.025)
            x = cx if c==1 else lerp(cx-140, cx+140, j/(c-1))
            r = 16 if li < 3 else 12
            d.ellipse((x-r,y-r,x+r,y+r), fill=rgba((250,246,235), int(180*s)), outline=rgba(mix(CRIMSON,INDIGO, li/6), int(200*s)), width=2)
            d.text((x, y+1), str(idx), font=SMALL_FONT, fill=INK, anchor='mm')
            if li>0:
                py = levels[li-1]
                if counts[li-1] == 1:
                    pxs=[cx]
                else:
                    pxs=[lerp(cx-140, cx+140, k/(counts[li-1]-1)) for k in range(counts[li-1])]
                for px in pxs:
                    d.line((px, py+14, x, y-14), fill=rgba(UMBER, 40), width=1)
            idx += 1
    d.text((1020, 210), 'descent through all 36', font=TERM_FONT, fill=CRIMSON)
    draw_trident(d, 140, 420, 0.8, CRIMSON)


def scene17(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 310
    # ascent arrow
    draw_line_glow(im, [(220, 520), (220, 150)], INDIGO, 4, 110, 8)
    d.polygon([(220,136),(208,168),(232,168)], fill=rgba(INDIGO,220))
    draw_silhouette(d, cx, 390, 1.0, color=UMBER)
    for i in range(11):
        a = clamp(t*1.25 - i*0.06)
        pts = bezier((cx, 438-i*6), (cx-40, 396-i*18), (cx-160, 310-i*20), (cx-220, 160-i*6), 90)
        pts = partial_polyline(pts, a)
        if len(pts)>1:
            draw_line_glow(im, pts, mix(GOLD, INDIGO, i/10), 2, 90, 5)
    draw_glow(im, (cx, 188), 62, GOLD_LIGHT, 150, 18)
    d.text((930, 210), 'pratyabhijñā', font=ImageFont.truetype(FONT_SERIF_BOLD, 32), fill=CRIMSON)
    d.text((930, 248), 'recognition returns to the source', font=SUB_FONT, fill=UMBER)


def scene18(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    draw_silhouette(d, cx, cy+90, 1.1, color=UMBER)
    draw_lotus(d, cx, cy+45, 0.72, color=CRIMSON, fill=rgba(LOTUS_PINK, 28), petals=6)
    # 36 small lights distributed through body field
    coords = []
    for row, y in enumerate([150,185,225,270,315,360,410]):
        count = [1,2,2,6,3,10,12][row]
        span = 18 if count==1 else 160 if count<7 else 220
        for j in range(count):
            x = cx if count == 1 else lerp(cx-span, cx+span, j/(count-1))
            coords.append((x,y))
    for i,(x,y) in enumerate(coords[:36]):
        s = clamp(t*1.15 - i*0.02)
        draw_glow(im, (x,y), 8, mix(GOLD_LIGHT, INDIGO, i/36), int(120*s), 5)
        d.ellipse((x-4,y-4,x+4,y+4), fill=rgba(WHITE, int(220*s)))
    d.text((640, 520), 'the body contains the tattvic cosmos', font=SUB_FONT, fill=UMBER, anchor='mm')


def scene19(im, t):
    d = ImageDraw.Draw(im)
    # macrocosm microcosm mirrors
    left, right = 350, 930
    d.ellipse((left-150,150,left+150,450), outline=rgba(INDIGO,170), width=2)
    d.ellipse((right-150,150,right+150,450), outline=rgba(CRIMSON,170), width=2)
    draw_silhouette(d, left, 315, 1.0, color=INDIGO)
    # world symbols
    draw_lotus(d, right, 330, 1.1, color=CRIMSON, fill=rgba((255,230,230),25), petals=8)
    for ang in np.linspace(0, 2*math.pi, 10, endpoint=False):
        x = right + math.cos(ang+t*0.2)*100
        y = 300 + math.sin(ang+t*0.2)*62
        d.ellipse((x-8,y-8,x+8,y+8), fill=rgba(mix(GOLD_LIGHT, INDIGO, abs(math.cos(ang))), 180))
    draw_line_glow(im, [(500,300),(780,300)], GOLD, 4, 130, 8)
    d.text((640, 500), 'yad idaṃ sarvaṃ śivamayam', font=DEVA_SMALL, fill=INDIGO, anchor='mm')


def scene20(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 292
    # concentric cosmogram
    for r, col, w in [(220, UMBER, 3), (188, GOLD, 2), (148, INDIGO, 2), (106, CRIMSON, 2)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(col,190), width=w)
    # 36 tattvas in ringed tree
    levels = [[1],[2],[3,4,5],[6],[7,8,9,10,11],[12],[13,14,15,16],[17,18,19,20,21],[22,23,24,25,26],[27,28,29,30,31],[32,33,34,35,36]]
    y_positions = np.linspace(cy-170, cy+170, len(levels))
    nodes=[]
    for level,y in zip(levels,y_positions):
        if len(level)==1:
            xs=[cx]
        else:
            span = min(300, 45*len(level))
            xs = np.linspace(cx-span/2, cx+span/2, len(level))
        for n,x in zip(level,xs):
            nodes.append((n,float(x),float(y)))
    node_map={n:(x,y) for n,x,y in nodes}
    # links sequential group flow
    edges=[]
    for a,b in [(1,2),(2,3),(2,4),(2,5),(5,6),(6,7),(6,8),(6,9),(6,10),(6,11),(11,12),(12,13),(13,14),(14,15),(15,16)]:
        edges.append((a,b))
    for k in range(17,22): edges.append((16,k))
    for k in range(22,27): edges.append((16,k))
    for k in range(27,32): edges.append((16,k))
    for k in range(32,37): edges.append((31,k))
    for i,(a,b) in enumerate(edges):
        s = clamp(t*1.15 - i*0.012)
        if s <= 0: continue
        p0=node_map[a]; p1=node_map[b]
        draw_line_glow(im, [p0,p1], mix(UMBER, GOLD, .3), 2, int(100*s), 5)
    for i,(n,x,y) in enumerate(nodes):
        s = clamp(t*1.15 - i*0.01)
        r = 11 if n < 7 else 9 if n < 17 else 8
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba((248,245,235), int(220*s)), outline=rgba(mix(CRIMSON,INDIGO, y/H), int(200*s)), width=2)
        d.text((x, y+1), str(n), font=ImageFont.truetype(FONT_SERIF, 10), fill=INK, anchor='mm')
    # mantra ring text simplified as repeated words
    ring_words = ['śiva', 'śakti', 'spanda', 'vimarśa', 'pratyabhijñā', 'tattva']
    for i,word in enumerate(ring_words*4):
        ang = -math.pi/2 + i*(2*math.pi/(len(ring_words)*4))
        r = 235
        x = cx + math.cos(ang)*r
        y = cy + math.sin(ang)*r
        rot_deg = math.degrees(ang + math.pi/2)
        # approximate by text without rotation for speed; place around circle
        d.text((x,y), word, font=SMALL_FONT, fill=rgba(UMBER,150), anchor='mm')
    draw_lotus(d, cx, cy+250, 0.5, color=GOLD, fill=rgba((250,240,220), 25), petals=6)


SCENES = [
    Scene('ta01', 'The Luminous Ground', 'Cit as self-radiant source before differentiation.', 'Cit / Anuttara', 'Pure consciousness shines as the unsurpassable ground.', 'luminous_bindu', ['pure','source','consciousness'], 'pure', 'radiant field + lotus', scene01),
    Scene('ta02', 'Spanda', 'The subtle pulse of consciousness.', 'Spanda', 'Reality trembles as living pulsation, not inert substance.', 'pulse_field', ['pure','spanda','rhythm'], 'pure', 'concentric pulse + wave ribbon', scene02),
    Scene('ta03', 'Śiva and Śakti', 'Static luminosity and reflexive power are inseparable.', 'Śiva–Śakti', 'The source and its dynamic power are one reality.', 'paired_spiral', ['pure','polarity','energy'], 'pure', 'bindu + triangle + spirals', scene03),
    Scene('ta04', 'Sadāśiva', 'The emergence of “I” with “This” still implicit.', 'Sadāśiva', 'Aham predominates while the world remains only nascent.', 'descending_canopy', ['pure','aham','emanation'], 'pure', 'descending arcs and aham text', scene04),
    Scene('ta05', 'Īśvara', 'The luminous disclosure of “This”.', 'Īśvara', 'Idam becomes manifest while remaining grounded in consciousness.', 'radiant_field', ['pure','idam','manifestation'], 'pure', 'star + distributed orbs', scene05),
    Scene('ta06', 'Śuddhavidyā', 'Balanced awareness of “I” and “This”.', 'Śuddhavidyā', 'Subject and object enter harmonious equilibrium.', 'balanced_triads', ['pure','balance','knowledge'], 'pure', 'interlocking triangles + lotus', scene06),
    Scene('ta07', 'Māyā', 'The power of delimitation and measurable difference.', 'Māyā', 'The undivided field becomes measured and sectioned.', 'veil_grid', ['pure-impure','māyā','limitation'], 'pure-impure', 'warp-grid veil', scene07),
    Scene('ta08', 'The Five Kañcukas', 'Limitation wraps consciousness in five constricting sheaths.', 'Kañcukas', 'Agency, knowledge, desire, time, and order become narrowed.', 'constriction_rings', ['pure-impure','kañcukas','contraction'], 'pure-impure', 'ring ladder + labels + silhouette', scene08),
    Scene('ta09', 'Puruṣa', 'The contracted experiencer appears.', 'Puruṣa', 'Consciousness now stands as the finite subject.', 'contracted_subject', ['pure-impure','puruṣa','subject'], 'pure-impure', 'haloed silhouette + orbiting points', scene09),
    Scene('ta10', 'Prakṛti', 'The matrix of differentiated manifestation.', 'Prakṛti', 'The guṇas churn the field of becoming.', 'guna_loom', ['pure-impure','prakṛti','guṇas'], 'pure-impure', 'three braided streams', scene10),
    Scene('ta11', 'The Inner Instrument', 'Buddhi, ahaṃkāra, and manas articulate cognition.', 'Antaḥkaraṇa', 'Discernment, individuation, and mental coordination arise.', 'triptych_psychology', ['inner instrument','buddhi','manas'], 'inner', 'triptych emblems', scene11),
    Scene('ta12', 'The Jñānendriyas', 'Five channels of knowing open onto the world.', 'Jñānendriyas', 'Hearing, touch, sight, taste, and smell become avenues of cognition.', 'sense_lotus', ['impure','senses','knowledge'], 'impure', 'lotus senses', scene12),
    Scene('ta13', 'The Karmendriyas', 'Action turns outward through five faculties.', 'Karmendriyas', 'Speech and bodily power project the individual into activity.', 'action_chain', ['impure','action','faculties'], 'impure', 'five act icons', scene13),
    Scene('ta14', 'The Tanmātras', 'Subtle potentials thicken toward sensible qualities.', 'Tanmātras', 'Sound, touch, form, taste, and smell hover as subtle seeds.', 'subtle_qualities', ['impure','tanmatras','subtle'], 'impure', 'five subtle discs', scene14),
    Scene('ta15', 'The Mahābhūtas', 'The gross elements condense the manifest world.', 'Mahābhūtas', 'Space, air, fire, water, and earth emerge as stable forms.', 'five_elements', ['impure','elements','world'], 'impure', 'elemental medallions', scene15),
    Scene('ta16', 'The Tattvic Cascade', 'All thirty-six levels can be read as one descending architecture.', 'Tattva-saṃghāta', 'The whole chain unfolds from subtle to gross manifestation.', 'full_descent', ['overview','descent','36 tattvas'], 'overview', 'numbered cascade', scene16),
    Scene('ta17', 'Recognition', 'Return follows the line of manifestation back to the source.', 'Pratyabhijñā', 'What descends can be recognised and re-ascended.', 'ascent_return', ['return','recognition','ascent'], 'return', 'ascent ribbon', scene17),
    Scene('ta18', 'The Body as Cosmos', 'The tattvas are present within embodied awareness itself.', 'Piṇḍa–Brahmāṇḍa', 'The microcosm recapitulates the cosmic order.', 'body_cosmogram', ['body','microcosm','tattvas'], 'return', 'body field lights', scene18),
    Scene('ta19', 'All This is Śiva', 'The world and the self mirror one consciousness.', 'Sarvaṃ Śivam', 'Manifest multiplicity remains the body of the one reality.', 'mirror_macro_micro', ['nonduality','world','śiva'], 'return', 'mirror worlds', scene19),
    Scene('ta20', 'The Seal of the Thirty-Six', 'The pack closes in one cosmogram of descent and return.', 'Tattva-cakra', 'The entire tattvic order resolves into one contemplative seal.', 'closing_seal', ['seal','cosmogram','summary'], 'seal', 'full mandala tree', scene20),
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
            im = parchment(SEED + hash(scene.id) % 10000 + i)
            border(im)
            scene.draw_fn(im, t)
            footer(im, scene.title, scene.subtitle, scene.term)
            im.convert('RGB').save(path, quality=95)
    out = SCENES_ROOT / f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size < 30000:
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS),
            '-i', str(sdir / 'frame_%04d.jpg'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-crf', '18', str(out)
        ]
        subprocess.run(cmd, check=True)


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, flush=True)
        render_scene(sc)
    concat_file = ROOT / 'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT / (sc.id + '.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT / 'tantraloka_36_tattvas_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', str(combined)], check=True)
    make_contact_sheet()
    write_metadata()
    validate_outputs()
    make_zip()


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame = FRAMES_ROOT / sc.id / f'frame_{int(NFRAMES*0.72):04d}.jpg'
        im = Image.open(frame).convert('RGB').resize((320,180), Image.Resampling.LANCZOS)
        thumbs.append(im)
    sheet = Image.new('RGB', (4*320, 5*180), color=PARCHMENT)
    for idx, im in enumerate(thumbs):
        x = (idx % 4)*320; y = (idx // 4)*180
        sheet.paste(im, (x,y))
    sheet.save(ROOT / 'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — The 36 Tattvas',
        'source_basis': 'Kashmir Śaiva 36-tattva schema as presented in the Trika tradition and associated with Abhinavagupta’s Tantrāloka.',
        'style': {
            'family': 'Kashmir Shaiva manuscript cosmography',
            'background': 'warm parchment',
            'ink': 'black / umber',
            'accent': 'crimson, indigo, gold',
            'materials': ['parchment', 'gold light', 'lotus lacquer', 'veil-silk', 'stone geometry']
        },
        'fps': FPS,
        'resolution': [W, H],
        'scene_duration_seconds': DURATION,
        'total_scenes': len(SCENES),
        'total_duration_seconds': round(len(SCENES) * DURATION, 2),
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
            }
            for sc in SCENES
        ]
    }
    (ROOT / 'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    catalog = {
        'ids': [sc.id for sc in SCENES],
        'titles': {sc.id: sc.title for sc in SCENES},
        'modes': {sc.id: sc.mode for sc in SCENES},
        'theme_clusters': {
            'pure': [sc.id for sc in SCENES if sc.group == 'pure'],
            'pure_impure': [sc.id for sc in SCENES if sc.group == 'pure-impure'],
            'inner_and_sensory': [sc.id for sc in SCENES if sc.group in ('inner','impure')],
            'return_and_synthesis': [sc.id for sc in SCENES if sc.group in ('overview','return','seal')],
        },
        'reusability_notes': {
            'ta02': 'Use for spanda, pulsation, subtle vibration, or alternation of manifestation and withdrawal.',
            'ta07': 'Use for māyā, delimitation, veiling, measurement, and contraction.',
            'ta08': 'Use for the five kañcukas or any theme of layered limitation.',
            'ta11': 'Use for cognition, the inner instrument, mind structures, or philosophical psychology.',
            'ta15': 'Use for five-elements discussions, ontological condensation, or cosmology.',
            'ta17': 'Use for ascent, return, pratyabhijñā, recognition, or contemplative reversal.',
            'ta20': 'Use as the pack’s closing seal or a summary of the full tattvic chain.'
        }
    }
    (ROOT / 'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = f'''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The 36 Tattvas

## Aim
This pack visualizes the Trika / Kashmir Śaiva map of the **36 tattvas** in a calm, contemplative, reusable motion-graphics form for documentary work.

## Textual orientation
The scenes are grounded in the standard Kashmir Śaiva tattva-system as it is deployed in Abhinavagupta’s intellectual world. The pack does **not** claim to illustrate every chapter of the *Tantrāloka* one-to-one. Instead, it turns the tattva-system and its associated logic of manifestation, limitation, embodiment, and recognition into a reusable scene library.

## Core doctrinal structure represented
1. **Cit / Anuttara** — luminous consciousness as unsurpassable source
2. **Spanda** — subtle pulsation
3. **Śiva–Śakti** — pure light and reflexive power
4. **The five pure tattvas** — Śiva, Śakti, Sadāśiva, Īśvara, Śuddhavidyā
5. **Māyā** — delimitation
6. **The five kañcukas** — kalā, vidyā, rāga, kāla, niyati
7. **Puruṣa** — the finite experiencer
8. **Prakṛti and antaḥkaraṇa** — the psychocosmic matrix and inner instrument
9. **Jñānendriyas / karmendriyas / tanmātras / mahābhūtas** — the differentiated sensory and material orders
10. **Pratyabhijñā** — return through recognition

## Visual rules
- Do not render the tattvas as a dead checklist only.
- Use motion to show **relations**: expansion, contraction, veiling, balancing, differentiation, embodiment, ascent.
- Keep the top levels luminous and subtle rather than mechanical.
- Māyā and the kañcukas should look like **self-limitation**, not evil forces.
- The material world should remain a real expression of consciousness, not a mistake.
- Recognition should reverse the descent without destroying the value of manifestation.

## Style family
- Warm parchment background
- Black / umber structure
- Crimson for power, disclosure, and decisive transition
- Indigo / blue-grey for reflective or sensory orders
- Gold for the luminous pure levels
- Lotus, bindu, triangles, veils, halos, and cosmograms as the primary vocabulary

## New motifs introduced in this pack
- radiant bindu fields
- pulse-rings for spanda
- paired Śiva–Śakti spirals
- descending arc-canopies for Sadāśiva
- distributed idam-orbs for Īśvara
- balanced interlocking triangles for Śuddhavidyā
- measuring veil-grids for Māyā
- ring-ladders for the kañcukas
- guṇa-stream looms for Prakṛti
- sense-lotuses and action medallions
- the body-cosmos field
- the final tattva-cakra seal

## Comparison guardrails
- Do not flatten the tattvas into a generic chakra poster.
- Do not equate the whole system with Advaita Vedānta’s māyā doctrine.
- Do not treat the pure-impure level as a fall into sin.
- Avoid collapsing the entire system into psychology only.
- When comparing with Sāṃkhya, note both borrowing and distinctively Śaiva reinterpretation.

## Reuse strategy
- ta01–ta06: source, pure consciousness, spanda, and the five pure tattvas
- ta07–ta10: māyā, kañcukas, puruṣa, prakṛti
- ta11–ta15: inner instrument, senses, action, subtle elements, gross elements
- ta16–ta20: full overview, ascent, body-cosmos, nonduality, closing seal
'''
    (ROOT / 'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Tantrāloka / 36 Tattvas Pack

## Shared project inheritance
This pack inherits the project’s love of parchment, cosmograms, diagrammatic clarity, and contemplative pacing.

## Kashmir Śaiva differentiation
Where Iamblichus emphasized temple, altar, hierarchy, and descent, and Plotinian development would emphasize fountain, mirror, and inwardness, this pack emphasizes:

- bindu and radiance
- pulsation and expansion / contraction
- lotuses and triangulated yantric forms
- veils, sheaths, and measuring grids
- the body as a tattvic field
- red-gold consciousness and blue-grey sensory articulation

## New motifs added
1. luminous bindu halo
2. pulse-rings for spanda
3. paired Śiva–Śakti spirals
4. descending canopies for Sadāśiva
5. distributed idam-orbs for Īśvara
6. interlocking balance-star for Śuddhavidyā
7. warp-grid veil for Māyā
8. constriction rings for the kañcukas
9. guṇa-loom streams
10. sense-lotus petals
11. action medallions
12. subtle-quality discs
13. five-element medallions
14. body-cosmos constellation
15. final tattva-cakra seal

## New relationships added
- self-radiance → pulsation
- source → disclosure of “I” / “This”
- undivided field → measured differentiation
- freedom → limitation by enclosure
- microcosm ↔ macrocosm mirroring
- descent → recognition-return

## New material vocabulary
- parchment and ivory field
- gold light
- lotus lacquer pink
- veil-silk grey-blue
- stone / earth browns for the gross elements

## Deprecated clichés
- generic chakra rainbow aesthetics
- flat list-only infographic approach
- treating tattvas as isolated labels with no causal or contemplative relation

## Distinct closing seal
The closing seal is a **tattva-cakra**: the full thirty-sixfold order organised into a contemplative cosmogram.

## Recommendation for next packs
A future Kashmir Śaiva pack should explore:
- phonemic matrices (mātṛkā)
- upāyas
- śaktipāta
- the heart (hṛdaya)
- body-temple diagrams
- more explicit mantra geometry
'''
    (ROOT / 'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The 36 Tattvas Pack

Included files:
- tantraloka_36_tattvas_animation.mp4
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
- Total runtime: {len(SCENES)*DURATION/60:.1f} min

Render instructions:
```bash
python render_pack.py
```
The script is resume-safe: it skips already-rendered frames and scene clips.
'''
    (ROOT / 'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'tantraloka_36_tattvas_animation.mp4'
    probe = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height,r_frame_rate:format=duration,size', '-of', 'json', str(combined)])
    info = json.loads(probe)
    (ROOT / 'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'tantraloka_36_tattvas_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['tantraloka_36_tattvas_animation.mp4', 'contact_sheet.jpg', 'scene_manifest.json', 'scene_catalog.json', 'AGENT_KNOWLEDGE_DOSSIER.md', 'STYLE_EVOLUTION.md', 'render_pack.py', 'README.md', 'validation.json']:
            zf.write(ROOT / name, arcname=name)
        for mp4 in sorted((SCENES_ROOT).glob('*.mp4')):
            zf.write(mp4, arcname=f'scenes/{mp4.name}')


if __name__ == '__main__':
    render_all()
