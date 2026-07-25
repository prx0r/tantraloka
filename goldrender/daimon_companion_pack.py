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
SEED = 88881

DEEP_VOID = (12, 14, 22)
NIGHT = (16, 18, 28)
WARM_DARK = (22, 20, 22)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
SILVER = (196, 204, 222)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
TEAL = (92, 146, 148)
INDIGO = (68, 78, 136)
VIOLET = (120, 104, 168)
LAVENDER = (166, 156, 196)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)
CORAL = (206, 108, 100)
CRIMSON = (154, 44, 58)
UMBER = (82, 66, 52)

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
        a = 2*math.pi*i/8; x = cx+math.cos(a)*r*0.62; y = cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,145), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(GOLD,100), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,70), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,INDIGO,GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im); y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(13,15,22,200), outline=rgba(GOLD,55), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def dust(im, seed, n=40):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40,W-40)); y = float(rng.uniform(40,H-40))
        r = float(rng.uniform(0.8,2.0))
        c = mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(20,60))))
    im.alpha_composite(ov)


def daimon_ground(seed, bg, glow_col, intensity=0.7):
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
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    if glow_col:
        g = np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.40)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i] += g * glow_col[i] * 0.04
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def luminous_form(d, im, cx, cy, r, col, t, prog=1.0):
    draw_glow(im, (cx,cy), int(r*1.5), col, int(80*prog), 20)
    for i in range(12):
        a = i*2*math.pi/12 + t*0.04
        x = cx + math.cos(a)*r*0.8
        y = cy + math.sin(a)*r*0.6
        d.ellipse((x-6,y-6,x+6,y+6), fill=rgba(col, int(120*prog)))
    d.ellipse((cx-int(r*0.6),cy-int(r*0.4), cx+int(r*0.6), cy+int(r*0.4)), fill=rgba(WHITE,int(220*prog)), outline=rgba(col,200), width=2)


@dataclass
class Scene:
    id: str; title: str; subtitle: str; term: str; summary: str
    mode: str; tags: list[str]; group: str; technique: str
    duration: float; draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(daimon_ground(fs, DEEP_VOID, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 280
    d.text((cx, 115), 'there is something with you', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 145), 'that has always been with you', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    luminous_form(d, im, cx+100, cy-20, 30, GOLD_LIGHT, t, prog)
    luminous_form(d, im, cx-80, cy+10, 20, TEAL, t, prog)
    draw_glow(im, (cx,cy), 15, GOLD, 70, 12)
    d.ellipse((cx-5,cy-5,cx+5,cy+5), fill=rgba(WHITE,200))


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(daimon_ground(fs, NIGHT, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 105), 'assigned at birth', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 135), 'your life is a shared project', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.line((cx-60, 180, cx-60, 430), fill=rgba(SLATE, 120), width=1)
    d.line((cx+60, 180, cx+60, 430), fill=rgba(SLATE, 120), width=1)
    for i in range(8):
        y = 200 + i*28
        d.line((cx-55, y, cx+55, y), fill=rgba(SLATE, 40+i*8), width=1)
    p1 = (cx-60, int(lerp(430, 280, prog)))
    p2 = (cx+60, int(lerp(180, 320, prog)))
    draw_glow(im, p1, 12, TEAL, 100, 8)
    d.ellipse((p1[0]-5,p1[1]-5,p1[0]+5,p1[1]+5), fill=rgba(WHITE,220))
    draw_glow(im, p2, 12, GOLD_LIGHT, 100, 8)
    d.ellipse((p2[0]-5,p2[1]-5,p2[0]+5,p2[1]+5), fill=rgba(WHITE,220))
    draw_line_glow(im, [p1,p2], GOLD, 2, 60, 5)
    d.text((cx, 478), 'before the first breath — already accompanied', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(daimon_ground(fs, DEEP_VOID, GOLD_LIGHT, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'the daimon is a function', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'the bridge between divine and human', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.rounded_rectangle((200, 120, 1080, 180), radius=12, outline=rgba(GOLD,120), width=1)
    d.text((640, 150), 'divine', font=SMALL_FONT, fill=GOLD, anchor='mm')
    d.rounded_rectangle((200, 420, 1080, 480), radius=12, outline=rgba(SLATE,120), width=1)
    d.text((640, 450), 'human', font=SMALL_FONT, fill=SLATE, anchor='mm')
    pts = bezier((640, 180), (720, 250), (560, 320), (640, 420), 80)
    reveal = partial_polyline(pts, prog)
    if len(reveal) > 1:
        draw_line_glow(im, reveal, GOLD_LIGHT, 4, 130, 8)
    draw_glow(im, (640, 300), 18, GOLD_LIGHT, 70, 14)
    d.text((640, 300), 'daimōn', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(daimon_ground(fs, NIGHT, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'plotinus: the undescended part', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'of your own soul', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    glow_y = lerp(240, 120, prog)
    luminous_form(d, im, cx, int(glow_y), 40, GOLD_LIGHT, t, 0.8+0.2*(1-prog))
    body_y = lerp(300, 400, prog)
    d.ellipse((cx-25,int(body_y),cx+25,int(body_y+50)), outline=rgba(SLATE,150), width=2)
    d.line((cx,int(body_y+50),cx,int(body_y+130)), fill=rgba(SLATE,120), width=2)
    d.line((cx, int(body_y+30), cx-50, int(body_y+80)), fill=rgba(SLATE,100), width=2)
    d.line((cx, int(body_y+30), cx+50, int(body_y+80)), fill=rgba(SLATE,100), width=2)
    draw_line_glow(im, [(cx, int(glow_y+40)), (cx, int(body_y))], GOLD, 2, 80, 5)
    d.text((cx, 480), 'the part that never descended — always connected', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(daimon_ground(fs, WARM_DARK, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'iamblichus: a superior being', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'requiring ritual', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    luminous_form(d, im, cx, 160, 35, GOLD_LIGHT, t, prog)
    d.ellipse((cx-25, 340, cx+25, 420), outline=rgba(SLATE,150), width=2)
    steps = 5
    for i in range(steps):
        p = clamp(prog*1.5 - i*0.12)
        if p <= 0: continue
        x = cx - 80 + i*40
        d.line((x, 340, x, 420), fill=rgba(GOLD, int(120*p)), width=2)
        d.ellipse((x-6, 370-6, x+6, 370+6), outline=rgba(GOLD, int(180*p)), width=2)
    d.text((cx, 478), 'ritual builds the bridge when the gap is too wide', font=SUB_FONT, fill=MIST, anchor='mm')


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(daimon_ground(fs, DEEP_VOID, GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'proclus: both are right', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), '— at different levels —', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    levels = [('the one', GOLD, 120), ('gods', GOLD_LIGHT, 170), ('daimons', TEAL, 230), ('souls', INDIGO, 300), ('bodies', SLATE, 380)]
    for i, (lab, col, y) in enumerate(levels):
        p = clamp(prog*1.3 - i*0.08)
        if p <= 0: continue
        d.line((cx-80, y, cx+80, y), fill=rgba(col, int(180*p)), width=2)
        d.text((cx+100, y-6), lab, font=TINY_FONT, fill=rgba(col, int(200*p)))
    d.text((cx, 480), 'the daimon: the middle term in the chain of being', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(daimon_ground(fs, DEEP_VOID, GOLD_LIGHT, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 95), 'corbin: the man of light', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'a being of pure luminosity', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 160), 'the celestial witness', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    br = lerp(10, 90, prog)
    draw_glow(im, (cx,cy), int(br), GOLD_LIGHT, int(150*prog), 25)
    d.ellipse((cx-int(br*0.7), cy-int(br*0.9), cx+int(br*0.7), cy+int(br*0.9)), fill=rgba(WHITE, int(180*prog)))
    d.ellipse((cx-int(br*0.4), cy-int(br*0.2), cx+int(br*0.4), cy+int(br*0.2)), fill=rgba(WHITE, int(220*prog)))
    d.text((cx, cy+br+30), 'shahid', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, 200), anchor='mm')
    d.text((cx, 488), 'the unus-ambo: two that are one, still two in that oneness', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(daimon_ground(fs, NIGHT, GOLD_LIGHT, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'ficino\'s music', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'planetary songs attuned the soul', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 160), 'the right melody drew the daimon closer', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(6):
        a = i*2*math.pi/6 + t*0.08
        r = 170
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        d.ellipse((x-12,y-12,x+12,y+12), outline=rgba(mix(INDIGO,GOLD,i/6), 150), width=2)
        d.ellipse((x-6,y-6,x+6,y+6), fill=rgba(mix(INDIGO,GOLD,i/6), 200))
    pts = []
    for i in range(80):
        u = i/79
        x = lerp(150, 1130, u)
        y = cy + 80 + math.sin(u*2*math.pi*2 + t*math.pi)*20*prog
        pts.append((x, y))
    draw_line_glow(im, pts, GOLD_LIGHT, 2, 80, 5)
    draw_glow(im, (cx,cy), 15, GOLD_LIGHT, 80, 10)


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(daimon_ground(fs, WARM_DARK, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 90), 'the pgm systasis', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 118), 'five stages of preparation', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    stages = ['skinning', 'purifying', 'charging', 'inflaming', 'communion']
    s_cols = [SLATE, TEAL, GOLD, CORAL, WHITE]
    prog = smoothstep(0.05, 0.92, t)
    for i in range(5):
        x = 200 + i*185
        y = cy + 20
        p = clamp(prog*1.5 - i*0.1)
        if p <= 0: continue
        d.rounded_rectangle((x-55, y-55, x+55, y+55), radius=10, outline=rgba(s_cols[i], int(190*p)), width=2)
        d.text((x, y-5), stages[i], font=TINY_FONT, fill=rgba(s_cols[i], int(200*p)), anchor='mm')
        if i < 4:
            ax = x+55; ay = y
            bx = x+130; by = y
            pts = partial_polyline([(ax,ay),(bx,by)], clamp(prog*2 - i*0.15))
            if len(pts) > 1: draw_line_glow(im, pts, GOLD, 1, 60, 3)
    d.text((640, 510), 'each stage: a precise operation on the soul-body', font=TINY_FONT, fill=MIST, anchor='mm')


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(daimon_ground(fs, NIGHT, GOLD_LIGHT, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'acher\'s four-stage cycle', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'trust — joy — darkness — encounter', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 160), 'then the cycle begins again at a deeper level', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    labels = ['trust', 'joy', 'darkness', 'encounter']
    cols = [TEAL, GOLD, INDIGO, WHITE]
    for i, (lab, col) in enumerate(zip(labels, cols)):
        a = -math.pi/2 + i*2*math.pi/4
        r = 150
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        d.ellipse((x-24,y-24,x+24,y+24), outline=rgba(col, 170), width=2)
        d.text((x, y), lab, font=TINY_FONT, fill=col, anchor='mm')
    a_pos = t*2*math.pi*0.3
    px = cx + math.cos(a_pos)*150
    py = cy + math.sin(a_pos)*150*0.6
    draw_glow(im, (int(px), int(py)), 12, GOLD_LIGHT, 100, 8)
    d.ellipse((int(px)-4, int(py)-4, int(px)+4, int(py)+4), fill=rgba(WHITE,255))


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(daimon_ground(fs, DEEP_VOID, GOLD, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'the daimon also wants the meeting', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 130), 'you are not pursuing a reluctant being', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 158), 'it has been waiting for you to turn around', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    luminous_form(d, im, int(cx-120+80*prog), cy+20, 25, GOLD_LIGHT, t, prog)
    luminous_form(d, im, int(cx+120-80*prog), cy-10, 20, TEAL, t, prog)
    if prog > 0.3:
        cx_mid = cx
        cy_mid = cy+5
        draw_glow(im, (cx_mid, cy_mid), int(10+20*(prog-0.3)/0.7), GOLD, int(80*(prog-0.3)/0.7), 12)
    d.text((cx, 480), 'the companion has never left. both reach.', font=SUB_FONT, fill=MIST, anchor='mm')


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(daimon_ground(fs, DEEP_VOID, GOLD_LIGHT, 0.5), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 90), 'the voice that said "look up"', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), '— that was it', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 155), 'every intuition, every synchronicity,', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 175), 'every moment of inexplicable knowing', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(36):
        a = i*2*math.pi/36 + t*0.05
        r = lerp(10, 200, prog)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        draw_line_glow(im, [(cx,cy),(x,y)], mix(GOLD_LIGHT,SILVER,i/36), 1, 50, 4)
    draw_glow(im, (cx,cy), 35, GOLD_LIGHT, 140, 16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((cx, 480), 'the meeting can happen now', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((cx, 502), 'epistrophē — turning toward', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')


SCENES =,Scene('da01','Always With You','Before birth. After death. Always.','Daimōn','','presence',['companion','always'],'intro','two luminous forms near center',6.0,sc01)
Scene('da02','Assigned at Birth','Your life is a shared project.','Synaphē','','birth',['birth','assignment','companion'],'assignment','two points moving down parallel lines',8.0,sc02)
Scene('da03','The Bridge','Between divine and human.','Mesitēs','','bridge',['bridge','mediation'],'function','luminous bridge between two realms',8.0,sc03)
Scene('da04','The Undescended Soul','Plotinus: the part that never descended.','Ameres psychē','','plotinus',['undescended','soul','connection'],'internal','luminous above, body below, thread between',8.0,sc04)
Scene('da05','The Superior Being','Iamblichus: requiring ritual.','Theourgia','','iamblichus',['ritual','preparation','gap'],'external','luminous being above, steps below',8.0,sc05)
Scene('da06','Both Are Right','Proclus: different levels of the chain.','Taxis','','proclus',['hierarchy','levels'],'synthesis','five horizontal levels with labels',6.0,sc06)
Scene('da07','The Man of Light','Corbin: a being of pure luminosity.','Shahid','','corbin',['light','witness','luminosity'],'witness','radiant luminous figure expanding',8.0,sc07)
Scene('da08','Planetary Music','Ficino: the right song draws it closer.','Harmonia','','ficino',['music','planets','resonance'],'music','orbiting planets with sound wave below',6.0,sc08)
Scene('da09','The Five Stages','PGM systasis: skinning, purifying, charging, inflaming, communion.','Systasis','','pgm',['ritual','stages','preparation'],'ritual','five sequential chambers',8.0,sc09)
Scene('da10','The Fourfold Cycle','Acher: trust, joy, darkness, encounter.','Kyklos','','acher',['cycle','stages','repetition'],'cycle','four stations in a circle with moving point',6.0,sc10)
Scene('da11','The Mutual Reaching','Both want the meeting.','Synantēsis','','meeting',['mutual','reaching','meeting'],'meeting','two forms moving toward each other',8.0,sc11)
Scene('da12','Turn Around','The meeting can happen now.','Epistrophē','','seal',['turning','recognition','now'],'seal','radial burst + central radiance',10.0,sc12)
Scene('da01','Always With You','Before birth. After death. Always.','Daimōn','','presence',['companion','always'],'intro','two luminous forms near center',6.0,sc01)
Scene('da02','Assigned at Birth','Your life is a shared project.','Synaphē','','birth',['birth','assignment','companion'],'assignment','two points moving down parallel lines',8.0,sc02)
Scene('da03','The Bridge','Between divine and human.','Mesitēs','','bridge',['bridge','mediation'],'function','luminous bridge between two realms',8.0,sc03)
Scene('da04','The Undescended Soul','Plotinus: the part that never descended.','Ameres psychē','','plotinus',['undescended','soul','connection'],'internal','luminous above, body below, thread between',8.0,sc04)
Scene('da05','The Superior Being','Iamblichus: requiring ritual.','Theourgia','','iamblichus',['ritual','preparation','gap'],'external','luminous being above, steps below',8.0,sc05)
Scene('da06','Both Are Right','Proclus: different levels of the chain.','Taxis','','proclus',['hierarchy','levels'],'synthesis','five horizontal levels with labels',6.0,sc06)
Scene('da07','The Man of Light','Corbin: a being of pure luminosity.','Shahid','','corbin',['light','witness','luminosity'],'witness','radiant luminous figure expanding',8.0,sc07)
Scene('da08','Planetary Music','Ficino: the right song draws it closer.','Harmonia','','ficino',['music','planets','resonance'],'music','orbiting planets with sound wave below',6.0,sc08)
Scene('da09','The Five Stages','PGM systasis: skinning, purifying, charging, inflaming, communion.','Systasis','','pgm',['ritual','stages','preparation'],'ritual','five sequential chambers',8.0,sc09)
Scene('da10','The Fourfold Cycle','Acher: trust, joy, darkness, encounter.','Kyklos','','acher',['cycle','stages','repetition'],'cycle','four stations in a circle with moving point',6.0,sc10)
Scene('da11','The Mutual Reaching','Both want the meeting.','Synantēsis','','meeting',['mutual','reaching','meeting'],'meeting','two forms moving toward each other',8.0,sc11)
Scene('da12','Turn Around','The meeting can happen now.','Epistrophē','','seal',['turning','recognition','now'],'seal','radial burst + central radiance',10.0,sc12)
Scene('da01','Always With You','Before birth. After death. Always.','Daimōn','','presence',['companion','always'],'intro','two luminous forms near center',6.0,sc01)
Scene('da02','Assigned at Birth','Your life is a shared project.','Synaphē','','birth',['birth','assignment','companion'],'assignment','two points moving down parallel lines',8.0,sc02)
Scene('da03','The Bridge','Between divine and human.','Mesitēs','','bridge',['bridge','mediation'],'function','luminous bridge between two realms',8.0,sc03)
Scene('da04','The Undescended Soul','Plotinus: the part that never descended.','Ameres psychē','','plotinus',['undescended','soul','connection'],'internal','luminous above, body below, thread between',8.0,sc04)
Scene('da05','The Superior Being','Iamblichus: requiring ritual.','Theourgia','','iamblichus',['ritual','preparation','gap'],'external','luminous being above, steps below',8.0,sc05)
Scene('da06','Both Are Right','Proclus: different levels of the chain.','Taxis','','proclus',['hierarchy','levels'],'synthesis','five horizontal levels with labels',6.0,sc06)
Scene('da07','The Man of Light','Corbin: a being of pure luminosity.','Shahid','','corbin',['light','witness','luminosity'],'witness','radiant luminous figure expanding',8.0,sc07)
Scene('da08','Planetary Music','Ficino: the right song draws it closer.','Harmonia','','ficino',['music','planets','resonance'],'music','orbiting planets with sound wave below',6.0,sc08)
Scene('da09','The Five Stages','PGM systasis: skinning, purifying, charging, inflaming, communion.','Systasis','','pgm',['ritual','stages','preparation'],'ritual','five sequential chambers',8.0,sc09)
Scene('da10','The Fourfold Cycle','Acher: trust, joy, darkness, encounter.','Kyklos','','acher',['cycle','stages','repetition'],'cycle','four stations in a circle with moving point',6.0,sc10)
Scene('da11','The Mutual Reaching','Both want the meeting.','Synantēsis','','meeting',['mutual','reaching','meeting'],'meeting','two forms moving toward each other',8.0,sc11)
Scene('da12','Turn Around','The meeting can happen now.','Epistrophē','','seal',['turning','recognition','now'],'seal','radial burst + central radiance',10.0,sc12) [
    Scene('da01','Always With You','Before birth. After death. Always.','Daimōn','','presence',['companion','always'],'intro','two luminous forms near center',6.0,sc01),
    Scene('da02','Assigned at Birth','Your life is a shared project.','Synaphē','','birth',['birth','assignment','companion'],'assignment','two points moving down parallel lines',8.0,sc02),
    Scene('da03','The Bridge','Between divine and human.','Mesitēs','','bridge',['bridge','mediation'],'function','luminous bridge between two realms',8.0,sc03),
    Scene('da04','The Undescended Soul','Plotinus: the part that never descended.','Ameres psychē','','plotinus',['undescended','soul','connection'],'internal','luminous above, body below, thread between',8.0,sc04),
    Scene('da05','The Superior Being','Iamblichus: requiring ritual.','Theourgia','','iamblichus',['ritual','preparation','gap'],'external','luminous being above, steps below',8.0,sc05),
    Scene('da06','Both Are Right','Proclus: different levels of the chain.','Taxis','','proclus',['hierarchy','levels'],'synthesis','five horizontal levels with labels',6.0,sc06),
    Scene('da07','The Man of Light','Corbin: a being of pure luminosity.','Shahid','','corbin',['light','witness','luminosity'],'witness','radiant luminous figure expanding',8.0,sc07),
    Scene('da08','Planetary Music','Ficino: the right song draws it closer.','Harmonia','','ficino',['music','planets','resonance'],'music','orbiting planets with sound wave below',6.0,sc08),
    Scene('da09','The Five Stages','PGM systasis: skinning, purifying, charging, inflaming, communion.','Systasis','','pgm',['ritual','stages','preparation'],'ritual','five sequential chambers',8.0,sc09),
    Scene('da10','The Fourfold Cycle','Acher: trust, joy, darkness, encounter.','Kyklos','','acher',['cycle','stages','repetition'],'cycle','four stations in a circle with moving point',6.0,sc10),
    Scene('da11','The Mutual Reaching','Both want the meeting.','Synantēsis','','meeting',['mutual','reaching','meeting'],'meeting','two forms moving toward each other',8.0,sc11),
    Scene('da12','Turn Around','The meeting can happen now.','Epistrophē','','seal',['turning','recognition','now'],'seal','radial burst + central radiance',10.0,sc12),
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
    manifest = {'project':'Daimon: The Companion You Have Had Since Birth',
        'source_basis':'Expansion Essay 9: "the angel you\'ve been ignoring" — 12 scenes.',
        'style':{'family':'luminous daimonic visualization','background':'deep void','ink':'gold, silver, teal, indigo'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    d = 'daimon — 12 scenes, the companion you have had since birth.\n'
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d, encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Daimon Pack — luminous companion visualization\n', encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Daimon: The Companion — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n', encoding='utf-8')

def validate_outputs():
    combined = ROOT/'daimon_companion_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))

def make_zip():
    zpath = ROOT/'daimon_companion_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['daimon_companion_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4, arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat = ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT/'daimon_companion_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
