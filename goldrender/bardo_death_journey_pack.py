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
SEED = 10101

DEEP_VOID = (10, 12, 18)
NIGHT = (14, 16, 24)
WARM_DARK = (20, 18, 20)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
SILVER = (196, 204, 222)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
CRIMSON = (154, 44, 58)
CORAL = (206, 108, 100)
BLOOD = (120, 30, 30)
TEAL = (92, 146, 148)
INDIGO = (68, 78, 136)
VIOLET = (120, 104, 168)
LAVENDER = (166, 156, 196)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)
UMBER = (82, 66, 52)
SKY_BLUE = (80, 130, 180)
GREEN = (96, 148, 108)
AMBER = (220, 160, 60)

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
def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1-t)**3
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
    d.rectangle((28,28,W-28,H-28), outline=rgba(GOLD,90), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,60), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,CRIMSON,GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im); y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(10,12,18,200), outline=rgba(GOLD,45), width=1)
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


def bardo_ground(seed, bg, glow_col, intensity=0.7):
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
    base -= np.clip((dx*dx+dy*dy)*20,0,28)[...,None]
    if glow_col:
        g = np.exp(-(((xx-W*0.48)/(W*0.32))**2+((yy-H*0.38)/(H*0.26))**2)*2.4)
        for i in range(3): base[...,i] += g * glow_col[i] * 0.035
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


@dataclass
class Scene:
    id: str; title: str; subtitle: str; term: str; summary: str
    mode: str; tags: list[str]; group: str; technique: str
    duration: float; draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, SILVER, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 110), 'no one remembers dying', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 140), 'you have died before', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 175), 'many times', font=SMALL_FONT, fill=MIST, anchor='mm')
    for i in range(5):
        x = cx - 150 + i*75
        alpha = int(40 + 60*(0.5+0.5*math.sin(t*0.5+i*1.3)))
        d.ellipse((x-15,cy+30,x+15,cy+60), outline=rgba(SILVER, alpha), width=1)
    draw_glow(im, (cx,cy+45), 12, GOLD, 60, 10)
    d.ellipse((cx-4,cy+41,cx+4,cy+49), fill=rgba(WHITE,200))


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(bardo_ground(fs, NIGHT, GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 95), 'four independent witnesses', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'describe the same river', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    syms = [('T', SILVER), ('E', GOLD), ('K', CRIMSON), ('S', TEAL)]
    labs = ['Tibetan', 'Egyptian', 'Tantric', 'Steiner']
    for i, ((sym, col), lab) in enumerate(zip(syms, labs)):
        x = 220 + i*230
        d.rounded_rectangle((x-50,200,x+50,320), radius=14, outline=rgba(col,170), width=2)
        d.text((x,250), sym, font=DEVA_MED, fill=col, anchor='mm')
        d.text((x,345), lab, font=TINY_FONT, fill=col, anchor='mm')
    pts = bezier((150,380),(300,350),(980,350),(1130,380),60)
    draw_line_glow(im, pts, GOLD_LIGHT, 2, 80, 5)
    d.text((cx, 485), 'the same river. independent witnesses. the river is real.', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(bardo_ground(fs, WARM_DARK, None, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 95), 'the elements dissolve', font=TERM_FONT, fill=PEARL, anchor='mm')
    prog = smoothstep(0.05, 0.92, t)
    phases = [('earth', UMBER, 0), ('water', TEAL, 0.2), ('fire', CORAL, 0.4), ('wind', SILVER, 0.6)]
    for i, (name, col, offset) in enumerate(phases):
        p = clamp((prog - offset)*4)
        if p <= 0: continue
        x = 220 + i*230
        y = cy + 40
        if i==0:
            d.rounded_rectangle((x-35,y-35+30*(1-p),x+35,y+35-20*(1-p)), radius=8, outline=rgba(col,int(180*p)), width=2)
        elif i==1:
            d.ellipse((x-30,y-15-15*(1-p),x+30,y+15-15*(1-p)), outline=rgba(col,int(180*p)), width=2)
        elif i==2:
            pts = [(x,y-25*p),(x-20,y+15*p-2),(x-6,y),(x+12,y+15*p-8),(x+22,y-6)]
            d.polygon(pts, outline=rgba(col,int(180*p)), fill=rgba(col,int(30*p)))
        else:
            for j in range(6):
                a = j*2*math.pi/6 + t*0.3
                r = 25*p*(0.6+0.4*math.sin(t*2+j))
                px = x+math.cos(a)*r; py = y+math.sin(a)*r*0.6
                d.ellipse((px-3,py-3,px+3,py+3), fill=rgba(col,int(150*p)))
        d.text((x,y+55), name, font=TINY_FONT, fill=rgba(col,int(200*p)), anchor='mm')


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 100), 'redness. whiteness. blackness.', font=TERM_FONT, fill=PEARL, anchor='mm')
    prog = clamp(t*1.2)
    colors = [CRIMSON, SILVER, DEEP_VOID]
    labels = ['red', 'white', 'black']
    for i in range(3):
        phase = i*0.33
        p = clamp((prog-phase)*3)
        if p <= 0: continue
        r = 200*p
        d.ellipse((cx-r,cy-r,cx+r,cy+r), fill=rgba(colors[i], int(220*p)))
        d.text((cx,cy+80+100*(1-p)), labels[i], font=SMALL_FONT, fill=rgba(PEARL,int(180*p)), anchor='mm')
    if prog > 0.95:
        draw_glow(im, (cx,cy-10), 40, GOLD_LIGHT, int(150*(prog-0.95)*20), 20)
        d.ellipse((cx-8,cy-18,cx+8,cy-2), fill=rgba(WHITE,int(200*(prog-0.95)*20)))


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 265
    prog = ease_in_out(t)
    d.text((cx, 95), 'the inner radiance dawns', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'the clear light of your own true nature', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    r = lerp(10, 350, prog)
    draw_glow(im, (cx,cy), int(r), GOLD_LIGHT, int(200*prog), 40)
    d.ellipse((cx-int(r*0.6),cy-int(r*0.4), cx+int(r*0.6), cy+int(r*0.4)), fill=rgba(WHITE, int(180*prog)))
    if prog > 0.7:
        d.text((cx, cy+80), 'prabhāsvara', font=DEVA_SMALL, fill=rgba(GOLD, 180), anchor='mm')
        d.text((cx, cy+108), '— recognize it —', font=SMALL_FONT, fill=rgba(WHITE, 180), anchor='mm')


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(bardo_ground(fs, NIGHT, GOLD_LIGHT, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 95), 'the entire life unfolds', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'not as memory — as presence', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(14):
        x = cx - 350 + i*52
        y = cy + 20 + 30*math.sin(i*0.7+t*2)
        p = clamp(prog*2 - i*0.06)
        if p <= 0: continue
        col = mix(GOLD_LIGHT, TEAL if i%3==0 else CORAL if i%3==1 else SILVER, i/14)
        d.ellipse((x-6,y-6,x+6,y+6), fill=rgba(col, int(180*p)))
        if i > 0:
            d.line((x-46-6, cy+20+30*math.sin((i-1)*0.7+t*2), x-6, y), fill=rgba(col, int(80*p)), width=1)
    draw_glow(im, (cx,cy-60), 15, GOLD_LIGHT, 70, 10)


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, SKY_BLUE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 85), 'forty-two peaceful deities', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 113), 'five directions — five colors', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    dirs = [(cx,cy-70,SKY_BLUE,'center'),(cx+120,cy+20,WHITE,'east'),(cx+70,cy+80,AMBER,'south'),(cx-70,cy+80,CRIMSON,'west'),(cx-120,cy+20,GREEN,'north')]
    for i,(x,y,col,lab) in enumerate(dirs):
        p = clamp(prog*1.2 - i*0.08)
        if p <= 0: continue
        draw_glow(im, (int(x),int(y)), 30, col, int(130*p), 18)
        d.ellipse((int(x)-16,int(y)-16,int(x)+16,int(y)+16), outline=rgba(col,int(200*p)), width=2)
        d.ellipse((int(x)-6,int(y)-6,int(x)+6,int(y)+6), fill=rgba(WHITE,int(150*p)))
        d.text((int(x),int(y)+30), lab, font=TINY_FONT, fill=rgba(col,int(200*p)), anchor='mm')
    d.text((640, 490), 'each one radiant. each one your own awareness.', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(bardo_ground(fs, WARM_DARK, CRIMSON, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 85), 'fifty-eight wrathful deities', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 113), 'crowned with skulls, drinking blood from skull-cups', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    dirs = [(cx,cy-60,BLOOD),(cx+110,cy+20,CRIMSON),(cx+60,cy+70,CORAL),(cx-60,cy+70,CORAL),(cx-110,cy+20,CRIMSON)]
    for i,(x,y,col) in enumerate(dirs):
        p = clamp(prog*1.2 - i*0.08)
        if p <= 0: continue
        draw_glow(im, (int(x),int(y)), 28, col, int(140*p), 16)
        d.ellipse((int(x)-18,int(y)-18,int(x)+18,int(y)+18), outline=rgba(col,int(200*p)), width=3)
        for j in range(6):
            a = j*2*math.pi/6 + t*0.1
            fx = int(x)+math.cos(a)*26
            fy = int(y)+math.sin(a)*18
            d.ellipse((fx-3,fy-3,fx+3,fy+3), fill=rgba(AMBER,int(100*p)))
    d.text((640, 490), 'the peaceful ones, unrecognized, now appear as wrathful', font=SUB_FONT, fill=MIST, anchor='mm')


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'every being you encounter', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'is a part of yourself', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 158), 'not yet recognized', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(12):
        a = i*2*math.pi/12 + t*0.05*(1-prog)
        r = lerp(160, 10, prog)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        col = mix(GOLD_LIGHT, WHITE, i/12)
        draw_line_glow(im, [(cx,cy),(int(x),int(y))], col, 1, int(80*(1-prog+0.2)), 4)
        d.ellipse((int(x)-4,int(y)-4,int(x)+4,int(y)+4), fill=rgba(col, int(180*(1-prog))))
    draw_glow(im, (cx,cy), 25, GOLD_LIGHT, 120, 12)
    d.ellipse((cx-10,cy-10,cx+10,cy+10), fill=rgba(WHITE,255))


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(bardo_ground(fs, WARM_DARK, GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 90), 'the hall of the two truths', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), 'the heart weighed against the feather', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.line((470,200,470,400), fill=rgba(GOLD,150), width=2)
    d.line((810,200,810,400), fill=rgba(GOLD,150), width=2)
    beam = lerp(640, 470, (0.5+0.5*math.sin(t*0.8))*0.7+0.3)
    d.line((470,int(beam),810,int(beam)), fill=rgba(GOLD,180), width=3)
    draw_glow(im, (470,int(beam)), 14, CORAL, 100, 10)
    d.ellipse((462,int(beam)-8,478,int(beam)+8), fill=rgba(CORAL,200))
    draw_glow(im, (810,int(beam)), 10, WHITE, 80, 8)
    d.line((806,int(beam)-14,814,int(beam)-14), fill=rgba(WHITE,200), width=1)
    d.line((806,int(beam)-2,814,int(beam)-2), fill=rgba(WHITE,200), width=1)
    d.text((470,int(beam)-30), 'heart', font=TINY_FONT, fill=CORAL, anchor='mm')
    d.text((810,int(beam)-30), 'ma\'at', font=TINY_FONT, fill=WHITE, anchor='mm')


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, SILVER, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'yama holds up a mirror', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'you judge yourself', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.rounded_rectangle((400,200,880,380), radius=20, outline=rgba(SILVER,200), width=2)
    if prog > 0.3:
        p = clamp((prog-0.3)/0.7)
        draw_glow(im, (640,290), 40, GOLD_LIGHT, int(80*p), 18)
        d.ellipse((620,270,660,310), fill=rgba(WHITE,int(200*p)))
        d.line((620,290,580,260), fill=rgba(GOLD,int(120*p)), width=1)
        d.line((660,290,700,320), fill=rgba(GOLD,int(120*p)), width=1)
        d.line((620,290,580,320), fill=rgba(GOLD,int(120*p)), width=1)
        d.line((660,290,700,260), fill=rgba(GOLD,int(120*p)), width=1)
    d.text((640, 490), 'the verdict is simply your own recognition', font=SUB_FONT, fill=MIST, anchor='mm')


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 90), 'the twelve kalis', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), 'consume objectivity, knowing, subjectivity', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    waves = [('objects', CORAL, 0), ('thoughts', TEAL, 0.3), ('self', GOLD, 0.6)]
    for i, (lab, col, offset) in enumerate(waves):
        p = clamp((prog-offset)*3)
        if p <= 0: continue
        r = 200*p
        d.ellipse((cx-r,cy-r*0.62,cx+r,cy+r*0.62), outline=rgba(col,int(180*p)), width=3-i)
        d.text((cx,cy+int(r*0.7)+15), lab, font=SMALL_FONT, fill=rgba(col,int(200*p)), anchor='mm')
    if prog > 0.95:
        draw_glow(im, (cx,cy), 18, WHITE, 100, 12)
        d.ellipse((cx-6,cy-6,cx+6,cy+6), fill=rgba(WHITE,255))
    d.text((640, 488), 'what remains is what was there before any of it began', font=SUB_FONT, fill=MIST, anchor='mm')


def sc13(im, t):
    fs = SEED + int(t*9973+6000) % 100000
    im.paste(bardo_ground(fs, WARM_DARK, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 90), 'six lights — six realms', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 118), 'the soul gravitates toward its tendency', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    realms = [('god', SILVER, 0), ('envy', CRIMSON, 1), ('desire', SKY_BLUE, 2),
              ('delusion', GREEN, 3), ('greed', AMBER, 4), ('anger', SLATE, 5)]
    for i, (lab, col, idx) in enumerate(realms):
        a = -math.pi/2 + idx*2*math.pi/6
        r = 170
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        p = clamp(prog*1.2 - i*0.06)
        if p <= 0: continue
        draw_glow(im, (int(x),int(y)), 20, col, int(80*p), 14)
        d.ellipse((int(x)-16,int(y)-16,int(x)+16,int(y)+16), outline=rgba(col,int(180*p)), width=2)
        d.text((int(x),int(y)+28), lab, font=TINY_FONT, fill=rgba(col,int(200*p)), anchor='mm')
    a_pt = t*2*math.pi*0.2
    px = cx + math.cos(a_pt)*170
    py = cy + math.sin(a_pt)*170*0.6
    draw_glow(im, (int(px),int(py)), 8, GOLD_LIGHT, 100, 6)
    d.ellipse((int(px)-3,int(py)-3,int(px)+3,int(py)+3), fill=rgba(WHITE,220))
    d.text((640, 485), 'consciousness seeking its own level', font=SUB_FONT, fill=MIST, anchor='mm')


def sc14(im, t):
    fs = SEED + int(t*9973+6500) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'the soul boards a boat', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'crosses the water', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 155), 'emerges at sunrise', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.line((50,400,1230,400), fill=rgba(SLATE,100), width=2)
    for i in range(20):
        x = 70 + i*60
        y = 400 + 8*math.sin(i*2.3)
        d.line((x,y,x+50,y+5*math.sin(i*2.3+0.5)), fill=rgba(SLATE,40), width=1)
    boat_x = lerp(100, 1100, prog)
    d.ellipse((int(boat_x)-20,380,int(boat_x)+20,400), fill=rgba(UMBER,180), outline=rgba(GOLD,120), width=1)
    d.line((int(boat_x)-5,380,int(boat_x)+5,365), fill=rgba(GOLD,150), width=2)
    d.text((int(boat_x),370), '\u2191', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    if prog > 0.7:
        sunrise = clamp((prog-0.7)*3.3)
        draw_glow(im, (1120,380), int(20+40*sunrise), GOLD_LIGHT, int(120*sunrise), 20)
        d.arc((1080,340,1160,420), 0, 180, fill=rgba(GOLD,int(200*sunrise)), width=2)


def sc15(im, t):
    fs = SEED + int(t*9973+7000) % 100000
    im.paste(bardo_ground(fs, DEEP_VOID, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 90), 'the radiance of your own true nature', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 145), 'recognize it', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    r = lerp(10, 350, prog)
    draw_glow(im, (cx,cy), int(r), GOLD_LIGHT, int(200*prog), 40)
    d.ellipse((cx-int(r*0.6),cy-int(r*0.4), cx+int(r*0.6), cy+int(r*0.4)), fill=rgba(WHITE, int(200*prog)))
    if prog > 0.6:
        p = clamp((prog-0.6)*2.5)
        d.ellipse((cx-10,cy-10,cx+10,cy+10), fill=rgba(WHITE,255))
        d.text((cx, cy+120), 'o nobly-born, do not be afraid', font=SMALL_FONT, fill=rgba(WHITE, int(200*p)), anchor='mm')
        d.text((cx, cy+145), 'this is the radiance of your own true nature', font=SMALL_FONT, fill=rgba(GOLD_LIGHT, int(200*p)), anchor='mm')
        d.text((cx, cy+170), 'recognize it, and liberation is immediate', font=SMALL_FONT, fill=rgba(GOLD, int(200*p)), anchor='mm')


SCENES =,Scene('bd01','No One Remembers Dying','You have died before. Many times.','Punarmṛtyu','','hook',['death','memory','many lives'],'intro','faint figures with after-images',6.0,sc01)
Scene('bd02','Four Witnesses','Tibetan, Egyptian, Tantric, Steiner — the same river.','Catur-āgama','','witnesses',['traditions','river','agreement'],'traditions','four symbols with river below',8.0,sc02)
Scene('bd03','Elements Dissolve','Earth — water — fire — wind. Each in sequence.','Bhūta-kṣaya','','dissolution',['elements','dissolution','body'],'process','four elements dissolving sequentially',10.0,sc03)
Scene('bd04','Three Visions','Redness. Whiteness. Blackness. Then radiance.','Raktādi','','visions',['red','white','black','radiance'],'threshold','three full-field colors then light',6.0,sc04)
Scene('bd05','The Clear Light','The radiance of your own true nature.','Prabhāsvara','','clear light',['clear light','radiance','nature'],'recognition','full-field radiance expanding',10.0,sc05)
Scene('bd06','Life in an Instant','Every face. Every word. Every wound. As presence.','Jīvita-smṛti','','life review',['life','instant','presence'],'review','rushing panorama of moments',6.0,sc06)
Scene('bd07','Peaceful Deities','Forty-two — center and four directions, five colors.','Śānta-devatā','','peaceful',['deities','peaceful','directions'],'visions','five-point luminous mandala',10.0,sc07)
Scene('bd08','Wrathful Deities','Fifty-eight — crowned with skulls, wielding weapons.','Krodha-devatā','','wrathful',['deities','wrathful','intense'],'visions','flaming fierce forms in five directions',8.0,sc08)
Scene('bd09','All Is Yourself','Every being is a part of you not yet recognized.','Svātmāvabhāsa','','recognition',['self','recognition','unity'],'recognition','deities converging into center',8.0,sc09)
Scene('bd10','The Hall of Two Truths','The heart weighed against the feather of Ma\'at.','Psychostasia','','judgment',['heart','feather','balance'],'judgment','scale with heart and feather',8.0,sc10)
Scene('bd11','Yama\'s Mirror','You judge yourself. The mirror shows all.','Ādarśa','','mirror',['mirror','self-judgment','reflection'],'judgment','mirror showing actions of a life',8.0,sc11)
Scene('bd12','The Twelve Kālīs','They consume objectivity, then knowing, then self.','Kalī-saṃhāra','','kalis',['kalis','dissolution','awareness'],'tantric','three concentric dissolving waves',8.0,sc12)
Scene('bd13','Six Lights — Six Realms','The soul gravitates toward its tendency.','Gati','','rebirth',['realms','lights','tendency'],'rebirth','six colored orbs with drifting point',8.0,sc13)
Scene('bd14','The Crossing','A boat on dark water. Emerges at sunrise.','Tarī','','crossing',['boat','water','sunrise'],'crossing','small boat crossing toward dawn',6.0,sc14)
Scene('bd15','Recognize It','This is the radiance of your own true nature.','Pratyabhijñā','','seal',['recognition','radiance','freedom'],'seal','clear light with figure recognizing it',8.0,sc15)
Scene('bd01','No One Remembers Dying','You have died before. Many times.','Punarmṛtyu','','hook',['death','memory','many lives'],'intro','faint figures with after-images',6.0,sc01)
Scene('bd02','Four Witnesses','Tibetan, Egyptian, Tantric, Steiner — the same river.','Catur-āgama','','witnesses',['traditions','river','agreement'],'traditions','four symbols with river below',8.0,sc02)
Scene('bd03','Elements Dissolve','Earth — water — fire — wind. Each in sequence.','Bhūta-kṣaya','','dissolution',['elements','dissolution','body'],'process','four elements dissolving sequentially',10.0,sc03)
Scene('bd04','Three Visions','Redness. Whiteness. Blackness. Then radiance.','Raktādi','','visions',['red','white','black','radiance'],'threshold','three full-field colors then light',6.0,sc04)
Scene('bd05','The Clear Light','The radiance of your own true nature.','Prabhāsvara','','clear light',['clear light','radiance','nature'],'recognition','full-field radiance expanding',10.0,sc05)
Scene('bd06','Life in an Instant','Every face. Every word. Every wound. As presence.','Jīvita-smṛti','','life review',['life','instant','presence'],'review','rushing panorama of moments',6.0,sc06)
Scene('bd07','Peaceful Deities','Forty-two — center and four directions, five colors.','Śānta-devatā','','peaceful',['deities','peaceful','directions'],'visions','five-point luminous mandala',10.0,sc07)
Scene('bd08','Wrathful Deities','Fifty-eight — crowned with skulls, wielding weapons.','Krodha-devatā','','wrathful',['deities','wrathful','intense'],'visions','flaming fierce forms in five directions',8.0,sc08)
Scene('bd09','All Is Yourself','Every being is a part of you not yet recognized.','Svātmāvabhāsa','','recognition',['self','recognition','unity'],'recognition','deities converging into center',8.0,sc09)
Scene('bd10','The Hall of Two Truths','The heart weighed against the feather of Ma\'at.','Psychostasia','','judgment',['heart','feather','balance'],'judgment','scale with heart and feather',8.0,sc10)
Scene('bd11','Yama\'s Mirror','You judge yourself. The mirror shows all.','Ādarśa','','mirror',['mirror','self-judgment','reflection'],'judgment','mirror showing actions of a life',8.0,sc11)
Scene('bd12','The Twelve Kālīs','They consume objectivity, then knowing, then self.','Kalī-saṃhāra','','kalis',['kalis','dissolution','awareness'],'tantric','three concentric dissolving waves',8.0,sc12)
Scene('bd13','Six Lights — Six Realms','The soul gravitates toward its tendency.','Gati','','rebirth',['realms','lights','tendency'],'rebirth','six colored orbs with drifting point',8.0,sc13)
Scene('bd14','The Crossing','A boat on dark water. Emerges at sunrise.','Tarī','','crossing',['boat','water','sunrise'],'crossing','small boat crossing toward dawn',6.0,sc14)
Scene('bd15','Recognize It','This is the radiance of your own true nature.','Pratyabhijñā','','seal',['recognition','radiance','freedom'],'seal','clear light with figure recognizing it',8.0,sc15)
Scene('bd01','No One Remembers Dying','You have died before. Many times.','Punarmṛtyu','','hook',['death','memory','many lives'],'intro','faint figures with after-images',6.0,sc01)
Scene('bd02','Four Witnesses','Tibetan, Egyptian, Tantric, Steiner — the same river.','Catur-āgama','','witnesses',['traditions','river','agreement'],'traditions','four symbols with river below',8.0,sc02)
Scene('bd03','Elements Dissolve','Earth — water — fire — wind. Each in sequence.','Bhūta-kṣaya','','dissolution',['elements','dissolution','body'],'process','four elements dissolving sequentially',10.0,sc03)
Scene('bd04','Three Visions','Redness. Whiteness. Blackness. Then radiance.','Raktādi','','visions',['red','white','black','radiance'],'threshold','three full-field colors then light',6.0,sc04)
Scene('bd05','The Clear Light','The radiance of your own true nature.','Prabhāsvara','','clear light',['clear light','radiance','nature'],'recognition','full-field radiance expanding',10.0,sc05)
Scene('bd06','Life in an Instant','Every face. Every word. Every wound. As presence.','Jīvita-smṛti','','life review',['life','instant','presence'],'review','rushing panorama of moments',6.0,sc06)
Scene('bd07','Peaceful Deities','Forty-two — center and four directions, five colors.','Śānta-devatā','','peaceful',['deities','peaceful','directions'],'visions','five-point luminous mandala',10.0,sc07)
Scene('bd08','Wrathful Deities','Fifty-eight — crowned with skulls, wielding weapons.','Krodha-devatā','','wrathful',['deities','wrathful','intense'],'visions','flaming fierce forms in five directions',8.0,sc08)
Scene('bd09','All Is Yourself','Every being is a part of you not yet recognized.','Svātmāvabhāsa','','recognition',['self','recognition','unity'],'recognition','deities converging into center',8.0,sc09)
Scene('bd10','The Hall of Two Truths','The heart weighed against the feather of Ma\'at.','Psychostasia','','judgment',['heart','feather','balance'],'judgment','scale with heart and feather',8.0,sc10)
Scene('bd11','Yama\'s Mirror','You judge yourself. The mirror shows all.','Ādarśa','','mirror',['mirror','self-judgment','reflection'],'judgment','mirror showing actions of a life',8.0,sc11)
Scene('bd12','The Twelve Kālīs','They consume objectivity, then knowing, then self.','Kalī-saṃhāra','','kalis',['kalis','dissolution','awareness'],'tantric','three concentric dissolving waves',8.0,sc12)
Scene('bd13','Six Lights — Six Realms','The soul gravitates toward its tendency.','Gati','','rebirth',['realms','lights','tendency'],'rebirth','six colored orbs with drifting point',8.0,sc13)
Scene('bd14','The Crossing','A boat on dark water. Emerges at sunrise.','Tarī','','crossing',['boat','water','sunrise'],'crossing','small boat crossing toward dawn',6.0,sc14)
Scene('bd15','Recognize It','This is the radiance of your own true nature.','Pratyabhijñā','','seal',['recognition','radiance','freedom'],'seal','clear light with figure recognizing it',8.0,sc15) [
    Scene('bd01','No One Remembers Dying','You have died before. Many times.','Punarmṛtyu','','hook',['death','memory','many lives'],'intro','faint figures with after-images',6.0,sc01),
    Scene('bd02','Four Witnesses','Tibetan, Egyptian, Tantric, Steiner — the same river.','Catur-āgama','','witnesses',['traditions','river','agreement'],'traditions','four symbols with river below',8.0,sc02),
    Scene('bd03','Elements Dissolve','Earth — water — fire — wind. Each in sequence.','Bhūta-kṣaya','','dissolution',['elements','dissolution','body'],'process','four elements dissolving sequentially',10.0,sc03),
    Scene('bd04','Three Visions','Redness. Whiteness. Blackness. Then radiance.','Raktādi','','visions',['red','white','black','radiance'],'threshold','three full-field colors then light',6.0,sc04),
    Scene('bd05','The Clear Light','The radiance of your own true nature.','Prabhāsvara','','clear light',['clear light','radiance','nature'],'recognition','full-field radiance expanding',10.0,sc05),
    Scene('bd06','Life in an Instant','Every face. Every word. Every wound. As presence.','Jīvita-smṛti','','life review',['life','instant','presence'],'review','rushing panorama of moments',6.0,sc06),
    Scene('bd07','Peaceful Deities','Forty-two — center and four directions, five colors.','Śānta-devatā','','peaceful',['deities','peaceful','directions'],'visions','five-point luminous mandala',10.0,sc07),
    Scene('bd08','Wrathful Deities','Fifty-eight — crowned with skulls, wielding weapons.','Krodha-devatā','','wrathful',['deities','wrathful','intense'],'visions','flaming fierce forms in five directions',8.0,sc08),
    Scene('bd09','All Is Yourself','Every being is a part of you not yet recognized.','Svātmāvabhāsa','','recognition',['self','recognition','unity'],'recognition','deities converging into center',8.0,sc09),
    Scene('bd10','The Hall of Two Truths','The heart weighed against the feather of Ma\'at.','Psychostasia','','judgment',['heart','feather','balance'],'judgment','scale with heart and feather',8.0,sc10),
    Scene('bd11','Yama\'s Mirror','You judge yourself. The mirror shows all.','Ādarśa','','mirror',['mirror','self-judgment','reflection'],'judgment','mirror showing actions of a life',8.0,sc11),
    Scene('bd12','The Twelve Kālīs','They consume objectivity, then knowing, then self.','Kalī-saṃhāra','','kalis',['kalis','dissolution','awareness'],'tantric','three concentric dissolving waves',8.0,sc12),
    Scene('bd13','Six Lights — Six Realms','The soul gravitates toward its tendency.','Gati','','rebirth',['realms','lights','tendency'],'rebirth','six colored orbs with drifting point',8.0,sc13),
    Scene('bd14','The Crossing','A boat on dark water. Emerges at sunrise.','Tarī','','crossing',['boat','water','sunrise'],'crossing','small boat crossing toward dawn',6.0,sc14),
    Scene('bd15','Recognize It','This is the radiance of your own true nature.','Pratyabhijñā','','seal',['recognition','radiance','freedom'],'seal','clear light with figure recognizing it',8.0,sc15),
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
    manifest = {'project':'Bardo: The Death Journey Across Traditions',
        'source_basis':'Expansion Essay 10: "you died already" — 15 scenes.',
        'style':{'family':'cinematic death-journey visualization','background':'deep void','ink':'gold, silver, blood, sky-blue, green, amber'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    d = 'bardo — 15 scenes, the death journey as described by four independent traditions.\n'
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d, encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Bardo Pack — cinematic multi-traditional death journey\n', encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Bardo: The Death Journey — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n', encoding='utf-8')

def validate_outputs():
    combined = ROOT/'bardo_death_journey_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))

def make_zip():
    zpath = ROOT/'bardo_death_journey_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['bardo_death_journey_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4, arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat = ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT/'bardo_death_journey_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
