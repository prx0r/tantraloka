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
SEED = 55551

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
ROSE = (196, 104, 130)
TEAL = (92, 146, 148)
INDIGO = (68, 78, 136)
VIOLET = (120, 104, 168)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)
MURK = (80, 75, 55)
BLOOD = (120, 30, 30)
RASA_COLS = [
    SLATE,
    BLOOD,
    MURK,
    CRIMSON,
    GOLD,
    CORAL,
    TEAL,
    ROSE,
    WHITE,
    SLATE,
    BLOOD,
    MURK,
    CRIMSON,
    GOLD,
    CORAL,
    TEAL,
    ROSE,
    WHITE,
]
RASA_NAMES = ['śoka', 'bhaya', 'jugupsā', 'raudra', 'adbhuta', 'hāsya', 'vīra', 'śṛṅgāra', 'śānta']

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
        a = 2*math.pi*i/8; x = cx+math.cos(a)*r*0.62; y = cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,145), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(GOLD, 100), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 70), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, CRIMSON, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im); y0 = H-112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(13,15,22,200), outline=rgba(GOLD,55), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def dust(im, seed, n=40):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40, W-40)); y = float(rng.uniform(40, H-40))
        r = float(rng.uniform(0.8, 2.0))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c, int(rng.uniform(20,60))))
    im.alpha_composite(ov)


def rasa_ground(seed, bg, glow_col, intensity=0.7):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(bg, dtype=np.float32)
    coarse = rng.normal(0,1,(44,78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.2*intensity + fine[...,None]*0.9*intensity
    yy,xx = np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18, 0, 26)[...,None]
    if glow_col:
        g = np.exp(-(((xx-W*0.48)/(W*0.30))**2 + ((yy-H*0.40)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i] += g * glow_col[i] * 0.04
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


@dataclass
class Scene:
    id: str; title: str; subtitle: str; term: str; summary: str
    mode: str; tags: list[str]; group: str; technique: str
    duration: float; draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(rasa_ground(fs, WARM_DARK, GOLD, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 120), 'a song you should turn off', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 148), 'but can\'t', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 178), 'a movie you know will wreck you', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 200), 'but you watch anyway', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(3):
        a = -math.pi/2 + i*2*math.pi/3 + t*0.2
        x = cx + math.cos(a)*100*prog
        y = cy + math.sin(a)*65*prog
        d.ellipse((x-12,y-12,x+12,y+12), outline=rgba(mix(GOLD,CORAL,i/3), int(180*prog)), width=2)
    draw_glow(im, (cx,cy), 18, GOLD_LIGHT, 100, 12)


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(rasa_ground(fs, DEEP_VOID, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 95), 'a philosopher called it rasa', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'the juice. the flavor.', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 155), 'nine of them', font=TERM_FONT, fill=GOLD, anchor='mm')
    eng = ['grief','terror','disgust','wrath','wonder','laughter','courage','tenderness','peace']
    for i in range(9):
        a = -math.pi/2 + i*2*math.pi/9
        r = 170
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        rr = 14
        d.ellipse((x-rr,y-rr,x+rr,y+rr), outline=rgba(RASA_COLS[i], 180), fill=rgba(RASA_COLS[i], 30), width=2)
        d.text((x, y+24), eng[i], font=TINY_FONT, fill=rgba(RASA_COLS[i], 180), anchor='mm')
        d.text((cx, cy), 'rasa', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(rasa_ground(fs, NIGHT, GOLD_LIGHT, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 110), 'the same thing that makes you cry', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 138), 'makes flowers grow', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(3):
        x = cx - 80 + i*80
        y = cy + 60
        p = clamp(prog*1.5 - i*0.2)
        if p <= 0: continue
        rr = 8 + 16*p
        col = mix(GOLD_LIGHT, ROSE, i/3)
        for j in range(6):
            a = j*2*math.pi/6
            px = x + math.cos(a)*rr
            py = y + math.sin(a)*rr*0.6
            d.ellipse((px-3, py-3, px+3, py+3), fill=rgba(col, int(150*p)))
        d.ellipse((x-4, y-4, x+4, y+4), fill=rgba(col, int(200*p)))
    draw_glow(im, (cx, cy-20), 22, GOLD_LIGHT, 80, 12)
    d.text((cx, 205), 'तेनैव रसः', font=TINY_FONT, fill=rgba(GOLD_LIGHT, 120), anchor='mm')


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(rasa_ground(fs, WARM_DARK, SLATE, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 280
    d.text((cx, 120), 'grief — let it sit in your chest', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 150), 'like a stone', font=TERM_FONT, fill=SLATE, anchor='mm')
    prog = ease_in_out(t)
    stone_r = lerp(10, 40, prog)
    draw_glow(im, (cx, cy+20), int(stone_r+10), SLATE, int(80*prog), 14)
    d.ellipse((cx-stone_r, cy+20-stone_r*0.8, cx+stone_r, cy+20+stone_r*0.8), fill=rgba(SLATE, int(180*prog)))
    if prog > 0.5:
        p2 = clamp((prog-0.5)*2)
        d.line((cx-40, cy-30, cx-20, cy-10), fill=rgba(GOLD_LIGHT, int(150*p2)), width=3)
        d.line((cx+20, cy-10, cx+40, cy-30), fill=rgba(GOLD_LIGHT, int(150*p2)), width=3)
        d.text((cx, cy+80), 'from clenched to open', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
        d.text((cx, cy+102), 'from fist to cup', font=SMALL_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(rasa_ground(fs, DEEP_VOID, GOLD, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'the goddess who is the Absolute', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'is aesthetic rapture — camatkara', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(24):
        a = i*2*math.pi/24 + t*0.04
        r = lerp(20, 190, prog)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        draw_line_glow(im, [(cx,cy),(x,y)], mix(GOLD,GOLD_LIGHT,i/24), 1, 60, 4)
        d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(GOLD_LIGHT, 180))
    draw_glow(im, (cx,cy), 30, GOLD_LIGHT, 130, 14)
    d.ellipse((cx-12,cy-12,cx+12,cy+12), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(rasa_ground(fs, WARM_DARK, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 105), 'tasting versus consuming', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'the emotion is wine', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 155), 'the witness is tasting', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    cup_w = lerp(10, 50, prog)
    d.ellipse((cx-cup_w, cy+10, cx+cup_w, cy+30), fill=rgba(CRIMSON, int(80+80*prog)), outline=rgba(GOLD,180), width=2)
    d.line((cx-cup_w, cy+10, cx-cup_w-10, cy-20), fill=rgba(GOLD,150), width=2)
    d.line((cx+cup_w, cy+10, cx+cup_w+10, cy-20), fill=rgba(GOLD,150), width=2)
    for i in range(5):
        a = i*2*math.pi/5 + t*0.2
        r = 60+40*prog
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.5
        d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(CRIMSON, int(100*prog*(1-i/5))))
    d.text((50, 80), 'रस', font=DEVA_SMALL, fill=rgba(GOLD, 25))
    if prog > 0.5:
        p2 = clamp((prog-0.5)*2)
        draw_glow(im, (cx, cy-30), int(10+20*p2), GOLD_LIGHT, int(80*p2), 10)
        d.text((cx, cy-60), 'āsvādana', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, 180), anchor='mm')


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(rasa_ground(fs, NIGHT, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 105), 'the savouring of one\'s own self', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), '— beyond objects, beyond poetry —', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    n = 16
    for i in range(n):
        a = i*2*math.pi/n + t*0.06
        r = lerp(10, 160, prog)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        draw_line_glow(im, [(cx,cy),(x,y)], mix(ROSE,GOLD,i/n), 1, 50, 3)
    d.ellipse((cx-100*prog, cy-62*prog, cx+100*prog, cy+62*prog), outline=rgba(ROSE,150), width=2)
    d.ellipse((cx-50*prog, cy-30*prog, cx+50*prog, cy+30*prog), outline=rgba(GOLD_LIGHT,180), width=2)
    draw_glow(im, (cx,cy), 20, ROSE, 100, 12)
    d.ellipse((cx-8,cy-8,cx+8,cy+8), fill=rgba(WHITE, 255))
    d.text((cx, 475), 'ātmananda — the self tasting itself', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(rasa_ground(fs, WARM_DARK, TEAL, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 105), 'rest in the feeling', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'not fighting. not holding. not analyzing.', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(10):
        a = i*2*math.pi/10 + t*0.08
        r = 60 + 30*math.sin(t*1.5 + i*0.7)
        x = cx + math.cos(a)*r*prog
        y = cy + math.sin(a)*r*0.45*prog
        col = mix(TEAL, GOLD_LIGHT, i/10)
        draw_glow(im, (int(x),int(y)), 12, col, int(50*prog), 10)
        d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(col, 160))
    r_ring = 40 + 15*math.sin(t*2)
    d.ellipse((cx-r_ring,cy-r_ring*0.62,cx+r_ring,cy+r_ring*0.62), outline=rgba(TEAL, int(100*prog)), width=1)
    draw_glow(im, (cx,cy), 25, GOLD_LIGHT, 100, 14)
    d.ellipse((cx-10,cy-10,cx+10,cy+10), fill=rgba(WHITE, 255))
    d.text((cx, 478), 'like resting in warm water', font=SUB_FONT, fill=MIST, anchor='mm')


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(rasa_ground(fs, WARM_DARK, GOLD, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 105), '"i am sad"', font=TERM_FONT, fill=SLATE, anchor='mm')
    d.text((cx, 135), '"there is sadness"', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 168), 'grief becomes rasa', font=SMALL_FONT, fill=GOLD, anchor='mm')
    prog = ease_in_out(t)
    if prog < 0.5:
        p = prog*2
        d.ellipse((cx-30,cy+20-15*p, cx+30,cy+50-15*p), fill=rgba(SLATE, int(180*(1-p))))
    else:
        p = (prog-0.5)*2
        d.ellipse((cx-30,cy-10, cx+30,cy+20), outline=rgba(GOLD_LIGHT, int(180*p)), width=2)
        draw_glow(im, (cx, cy+5), 20, GOLD_LIGHT, int(80*p), 12)
    d.text((cx, 475), 'when the "i" drops away — the pain becomes beauty', font=SUB_FONT, fill=MIST, anchor='mm')


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(rasa_ground(fs, DEEP_VOID, GOLD, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 105), 'the one who rests in the power of bliss', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'becomes the bliss itself', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(20):
        a = i*2*math.pi/20 + t*0.05
        r = 20 + 150*prog
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        col = mix(GOLD, GOLD_LIGHT, i/20)
        d.ellipse((x-2,y-2,x+2,y+2), fill=rgba(col, int(180*prog*(1-i/20))))
    draw_glow(im, (cx,cy), 35, GOLD_LIGHT, 140, 16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((cx, 478), 'tadātmya — the witness becomes the witnessed', font=SUB_FONT, fill=MIST, anchor='mm')


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(rasa_ground(fs, WARM_DARK, CORAL, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 105), 'grief still hurts', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'the witness is made of something', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 155), 'grief cannot touch', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(5):
        a = i*2*math.pi/5 + t*0.15
        r = 30 + 110*prog
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        d.ellipse((x-18,y-18,x+18,y+18), outline=rgba(mix(CORAL,CRIMSON,i/5), int(160*prog)), width=2)
        d.ellipse((x-6,y-6,x+6,y+6), fill=rgba(mix(CORAL,CRIMSON,i/5), int(120*prog)))
    draw_glow(im, (cx,cy), 22, GOLD_LIGHT, 120, 12)
    d.ellipse((cx-8,cy-8,cx+8,cy+8), fill=rgba(WHITE,255))
    d.text((cx, 478), 'the witness: fire cannot burn it', font=SUB_FONT, fill=MIST, anchor='mm')


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(rasa_ground(fs, NIGHT, GOLD_LIGHT, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 95), 'ride it. let it crest. let it crash.', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'let it dissolve', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 160), 'another wave is already forming', font=SMALL_FONT, fill=MIST, anchor='mm')
    wave_cols = [SLATE, CRIMSON, CORAL, GOLD, TEAL, ROSE]
    for wi in range(6):
        pts = []
        for i in range(80):
            u = i/79
            x = lerp(150, 1130, u)
            phase = t*(0.5+wi*0.1) + wi*0.8
            y = cy + 60 + wi*12 + math.sin(u*2*math.pi*2 + phase)*20
            pts.append((x, y))
        draw_line_glow(im, pts, wave_cols[wi], 2, 80, 5)
    draw_glow(im, (cx, cy-80), 18, GOLD_LIGHT, 90, 12)
    d.ellipse((cx-6,cy-86,cx+6,cy-74), fill=rgba(WHITE,255))
    d.text((cx, 488), 'you are the ocean, not the wave', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES =,Scene('ra01','The Song You Can\'t Turn Off','Painful beauty draws you in.','Vedanā','','hook',['beauty','pain'],'intro','three circling forms',6.0,sc01)
Scene('ra02','Nine Flavors','Grief, terror, disgust, wrath, wonder, laughter, courage, tenderness, peace.','Nava-rasa','','rasas',['nine','rasa'],'doctrine','nine colored drops in a ring',8.0,sc02)
Scene('ra03','The Same Vitality','Tears and flowers — one juice.','Saṃvit','','vitality',['vitality','tears','flowers'],'doctrine','tear becoming flower',8.0,sc03)
Scene('ra04','Grief Like a Stone','Let it sit. From fist to cup.','Śoka','','grief',['grief','stone','opening'],'emotion','stone in chest transforming',6.0,sc04)
Scene('ra05','Camatkāra','The goddess is aesthetic rapture.','Camatkāra','','wonder',['wonder','rapture','goddess'],'doctrine','radiant goddess form',8.0,sc05)
Scene('ra06','Tasting vs Consuming','The emotion is wine. The witness is tasting.','Āsvādana','','tasting',['taste','witness','wine'],'practice','wine cup with glow above',6.0,sc06)
Scene('ra07','The Self Tasting Itself','Beyond objects, beyond poetry.','Ātmananda','','self-taste',['self','taste','bliss'],'doctrine','self-enclosed luminous ring',8.0,sc07)
Scene('ra08','Rest in the Feeling','Not fighting. Not holding. Just resting.','Viśrānti','','rest',['rest','surrender','water'],'practice','floating in warm water glow',6.0,sc08)
Scene('ra09','I Am Sad → There Is Sadness','The shift that turns grief to rasa.','Sākṣin','','witness',['witness','shift','grief'],'transformation','phrase transform + grief to gold',8.0,sc09)
Scene('ra10','The Witness Becomes the Bliss','Resting in the power of bliss.','Tadātmya','','identity',['identity','bliss','witness'],'culmination','form dissolving into golden light',8.0,sc10)
Scene('ra11','Fire Cannot Burn It','Grief still hurts. The witness is untouched.','Avikriya','','untouched',['witness','fire','untouched'],'nature','flames around an untouched center',6.0,sc11)
Scene('ra12','The Wave','Crest. Crash. Dissolve. Another forms.','Ūrmi','','wave',['wave','ocean','cycle'],'seal','six colored waves + still center',8.0,sc12)
Scene('ra01','The Song You Can\'t Turn Off','Painful beauty draws you in.','Vedanā','','hook',['beauty','pain'],'intro','three circling forms',6.0,sc01)
Scene('ra02','Nine Flavors','Grief, terror, disgust, wrath, wonder, laughter, courage, tenderness, peace.','Nava-rasa','','rasas',['nine','rasa'],'doctrine','nine colored drops in a ring',8.0,sc02)
Scene('ra03','The Same Vitality','Tears and flowers — one juice.','Saṃvit','','vitality',['vitality','tears','flowers'],'doctrine','tear becoming flower',8.0,sc03)
Scene('ra04','Grief Like a Stone','Let it sit. From fist to cup.','Śoka','','grief',['grief','stone','opening'],'emotion','stone in chest transforming',6.0,sc04)
Scene('ra05','Camatkāra','The goddess is aesthetic rapture.','Camatkāra','','wonder',['wonder','rapture','goddess'],'doctrine','radiant goddess form',8.0,sc05)
Scene('ra06','Tasting vs Consuming','The emotion is wine. The witness is tasting.','Āsvādana','','tasting',['taste','witness','wine'],'practice','wine cup with glow above',6.0,sc06)
Scene('ra07','The Self Tasting Itself','Beyond objects, beyond poetry.','Ātmananda','','self-taste',['self','taste','bliss'],'doctrine','self-enclosed luminous ring',8.0,sc07)
Scene('ra08','Rest in the Feeling','Not fighting. Not holding. Just resting.','Viśrānti','','rest',['rest','surrender','water'],'practice','floating in warm water glow',6.0,sc08)
Scene('ra09','I Am Sad → There Is Sadness','The shift that turns grief to rasa.','Sākṣin','','witness',['witness','shift','grief'],'transformation','phrase transform + grief to gold',8.0,sc09)
Scene('ra10','The Witness Becomes the Bliss','Resting in the power of bliss.','Tadātmya','','identity',['identity','bliss','witness'],'culmination','form dissolving into golden light',8.0,sc10)
Scene('ra11','Fire Cannot Burn It','Grief still hurts. The witness is untouched.','Avikriya','','untouched',['witness','fire','untouched'],'nature','flames around an untouched center',6.0,sc11)
Scene('ra12','The Wave','Crest. Crash. Dissolve. Another forms.','Ūrmi','','wave',['wave','ocean','cycle'],'seal','six colored waves + still center',8.0,sc12) [
    Scene('ra01','The Song You Can\'t Turn Off','Painful beauty draws you in.','Vedanā','','hook',['beauty','pain'],'intro','three circling forms',6.0,sc01),
    Scene('ra02','Nine Flavors','Grief, terror, disgust, wrath, wonder, laughter, courage, tenderness, peace.','Nava-rasa','','rasas',['nine','rasa'],'doctrine','nine colored drops in a ring',8.0,sc02),
    Scene('ra03','The Same Vitality','Tears and flowers — one juice.','Saṃvit','','vitality',['vitality','tears','flowers'],'doctrine','tear becoming flower',8.0,sc03),
    Scene('ra04','Grief Like a Stone','Let it sit. From fist to cup.','Śoka','','grief',['grief','stone','opening'],'emotion','stone in chest transforming',6.0,sc04),
    Scene('ra05','Camatkāra','The goddess is aesthetic rapture.','Camatkāra','','wonder',['wonder','rapture','goddess'],'doctrine','radiant goddess form',8.0,sc05),
    Scene('ra06','Tasting vs Consuming','The emotion is wine. The witness is tasting.','Āsvādana','','tasting',['taste','witness','wine'],'practice','wine cup with glow above',6.0,sc06),
    Scene('ra07','The Self Tasting Itself','Beyond objects, beyond poetry.','Ātmananda','','self-taste',['self','taste','bliss'],'doctrine','self-enclosed luminous ring',8.0,sc07),
    Scene('ra08','Rest in the Feeling','Not fighting. Not holding. Just resting.','Viśrānti','','rest',['rest','surrender','water'],'practice','floating in warm water glow',6.0,sc08),
    Scene('ra09','I Am Sad → There Is Sadness','The shift that turns grief to rasa.','Sākṣin','','witness',['witness','shift','grief'],'transformation','phrase transform + grief to gold',8.0,sc09),
    Scene('ra10','The Witness Becomes the Bliss','Resting in the power of bliss.','Tadātmya','','identity',['identity','bliss','witness'],'culmination','form dissolving into golden light',8.0,sc10),
    Scene('ra11','Fire Cannot Burn It','Grief still hurts. The witness is untouched.','Avikriya','','untouched',['witness','fire','untouched'],'nature','flames around an untouched center',6.0,sc11),
    Scene('ra12','The Wave','Crest. Crash. Dissolve. Another forms.','Ūrmi','','wave',['wave','ocean','cycle'],'seal','six colored waves + still center',8.0,sc12),
]


def render_scene(scene:Scene):
    sdir = FRAMES_ROOT/scene.id; sdir.mkdir(parents=True, exist_ok=True)
    nframes = int(FPS * scene.duration)
    expected = [sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    if not all(p.exists() and p.stat().st_size > 1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size > 1000: continue
            t = i/max(1, nframes-1)
            im = Image.new('RGBA', (W,H), (0,0,0,0))
            scene.draw_fn(im, t)
            dust(im, SEED + hash(scene.id)%10000 + i, 55)
            border(im); footer(im, scene.title, scene.subtitle, scene.term)
            im.convert('RGB').save(path, quality=95)
    out = SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size < 30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)], check=True)

def make_contact_sheet():
    thumbs = []
    for sc in SCENES:
        frame = FRAMES_ROOT/sc.id/f'frame_{int(10*sc.duration*0.72):04d}.jpg'
        if not frame.exists(): frame = FRAMES_ROOT/sc.id/'frame_0000.jpg'
        if not frame.exists(): continue
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180), Image.Resampling.LANCZOS))
    rows = (len(thumbs)+3)//4
    sheet = Image.new('RGB', (4*320, rows*180), color=DEEP_VOID)
    for idx,im in enumerate(thumbs): sheet.paste(im, ((idx%4)*320, (idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)

def write_metadata():
    manifest = {'project':'Tantrāloka — Rasa: The Nine Flavors of Consciousness',
        'source_basis':'Expansion Essay 5: "pain is juice" — 12 scenes.',
        'style':{'family':'rasa/emotion visualization','background':'warm dark','ink':'gold, slate, crimson, coral, teal, rose'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    d = 'rasa — 12 scenes, 12 emotional flavors. each scene is one shift in the relationship to feeling.\n'
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d, encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Rasa Pack — emotion as aesthetic taste\n', encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Rasa: The Nine Flavors — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n', encoding='utf-8')

def validate_outputs():
    combined = ROOT/'rasa_nine_flavors_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))

def make_zip():
    zpath = ROOT/'rasa_nine_flavors_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['rasa_nine_flavors_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4, arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat = ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT/'rasa_nine_flavors_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
