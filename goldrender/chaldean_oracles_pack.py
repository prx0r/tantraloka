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
SEED = 25252

ABYSS = (8, 10, 24)
DEEP = (12, 18, 36)
NIGHT = (16, 20, 30)
EMERALD = (60, 140, 100)
EMERALD_LIGHT = (120, 200, 150)
STAR_WHITE = (235, 242, 250)
CRYSTAL = (200, 220, 240)
PEARL = (246, 243, 236)
SILVER = (196, 208, 224)
COSMIC_FIRE = (200, 100, 40)
EMBER = (180, 80, 30)
FLOWER_GOLD = (220, 180, 80)
GOLD_LIGHT = (240, 210, 140)
DAIMON_SPARK = (170, 220, 200)
DEPTH_BLUE = (20, 30, 60)
SPHERE_IRIS = (140, 100, 180)
WHITE = (252, 250, 246)
SLATE = (80, 90, 110)
MIST = (160, 172, 192)
UMBER = (70, 56, 42)

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
    d.rectangle((28,28,W-28,H-28), outline=rgba(EMERALD,80), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(EMERALD_LIGHT,50), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,EMERALD,STAR_WHITE)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im); y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(10,12,22,200), outline=rgba(EMERALD,45), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24), term, font=TERM_FONT, fill=EMERALD_LIGHT)


def dust(im, seed, n=40):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40,W-40)); y = float(rng.uniform(40,H-40))
        r = float(rng.uniform(0.8,2.0))
        c = mix(DAIMON_SPARK,STAR_WHITE,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(15,50))))
    im.alpha_composite(ov)


def oracle_ground(seed, bg, glow_col, intensity=0.6):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(bg, dtype=np.float32)
    coarse = rng.normal(0,1,(44,78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*2.8*intensity + fine[...,None]*0.8*intensity
    yy,xx = np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
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
    im.paste(oracle_ground(fs, DEEP, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 110), 'before plato, before pythagoras', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 140), 'there were the oracles', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 175), 'fragments survive', font=SMALL_FONT, fill=MIST, anchor='mm')
    for i in range(8):
        x = cx - 200 + i*55
        y = cy + 30 + 20*math.sin(i*1.3+t)
        r = 4 + 3*math.sin(t+i)
        alpha = int(40 + 80*(0.5+0.5*math.sin(t*0.7+i*0.9)))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(FLOWER_GOLD, alpha))
    d.text((150,320), '...kindle the fire within...', font=TINY_FONT, fill=rgba(FLOWER_GOLD,100), anchor='lm')
    d.text((800,350), '...the flower of the intellect...', font=TINY_FONT, fill=rgba(EMERALD_LIGHT,80), anchor='lm')


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(oracle_ground(fs, DEPTH_BLUE, None, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'the father is the depth', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'a hand reaching into water', font=TERM_FONT, fill=STAR_WHITE, anchor='mm')
    d.text((cx, 155), 'the water closes without a seam', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    pts = bezier((cx, 150), (cx-20, 220), (cx+30, 330), (cx, 380), 60)
    reveal = partial_polyline(pts, prog)
    if len(reveal) > 1:
        draw_line_glow(im, reveal, STAR_WHITE, 4, 120, 8)
    for i in range(4):
        a = t + i*0.5
        r = 10 + 30*(0.5+0.5*math.sin(a))
        draw_glow(im, (cx+int(r*0.5), 380), int(r), CRYSTAL, int(40*(1-r/40)), 10)
    d.text((640, 478), 'he snatches himself away by being too close to see', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(oracle_ground(fs, DEEP, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 95), 'the father has sown the symbols of wisdom in souls', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'giving them to learn the many-monitored doctrines', font=SMALL_FONT, fill=MIST, anchor='mm')
    seeds = ['wonder', 'love', 'create', 'truth']
    s_cols = [STAR_WHITE, EMERALD_LIGHT, FLOWER_GOLD, DAIMON_SPARK]
    prog = ease_in_out(t)
    for i, (lab, col) in enumerate(zip(seeds, s_cols)):
        x = cx - 150 + i*100
        y = cy + 40
        p = clamp(prog*1.5 - i*0.1)
        if p <= 0: continue
        draw_glow(im, (int(x),int(y-20)), 12, col, int(100*p), 10)
        d.ellipse((int(x)-5,int(y-20)-5,int(x)+5,int(y-20)+5), fill=rgba(col,int(200*p)))
        d.text((int(x),int(y+10)), lab, font=TINY_FONT, fill=rgba(col,int(200*p)), anchor='mm')
    draw_glow(im, (cx, cy-20), 12, STAR_WHITE, 60, 10)


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(oracle_ground(fs, DEEP, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'hekate stands at the hinge of the universe', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'above: fire so pure it has no color', font=SMALL_FONT, fill=STAR_WHITE, anchor='mm')
    d.text((cx, 140), 'below: fire so dense it has become stone', font=SMALL_FONT, fill=COSMIC_FIRE, anchor='mm')
    prog = ease_in_out(t)
    draw_glow(im, (cx, 150), int(50+20*prog), STAR_WHITE, int(100*prog), 25)
    draw_glow(im, (cx, 380), int(50+20*prog), COSMIC_FIRE, int(100*prog), 25)
    d.ellipse((cx-40,260,cx+40,340), outline=rgba(EMERALD,int(200*prog)), width=2)
    draw_glow(im, (cx,300), 25, EMERALD, int(80*prog), 15)
    for i in range(8):
        a = i*2*math.pi/8 + t*0.08
        x = cx + math.cos(a)*50
        y = 300 + math.sin(a)*40
        d.ellipse((x-6,y-6,x+6,y+6), outline=rgba(FLOWER_GOLD,int(120*prog)), width=1)
    d.text((640, 485), 'the space through which both fires move', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(oracle_ground(fs, ABYSS, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 85), 'around the hekate', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'a great band of daimons dances', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 148), 'sparks that fly off as the worlds above and below grind against each other', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.ellipse((cx-60,260,cx+60,340), outline=rgba(EMERALD,160), width=2)
    for i in range(24):
        a = i*2*math.pi/24 + t*0.1
        r = 120 + 20*math.sin(t*2 + i*0.5)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        col = mix(DAIMON_SPARK, FLOWER_GOLD, i/24)
        draw_glow(im, (int(x),int(y)), 6, col, 100, 6)
        d.ellipse((int(x)-3,int(y)-3,int(x)+3,int(y)+3), fill=rgba(col,200))
    draw_glow(im, (cx,cy), 20, EMERALD, 90, 14)


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(oracle_ground(fs, DEEP, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'the center from which all powers issue', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'the matrix of all things', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(16):
        a = i*2*math.pi/16 + t*0.06
        r = lerp(10, 190, prog)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        draw_line_glow(im, [(cx,cy),(int(x),int(y))], mix(EMERALD, STAR_WHITE, i/16), 1, 60, 4)
        d.ellipse((int(x)-4,int(y)-4,int(x)+4,int(y)+4), fill=rgba(EMERALD_LIGHT,180))
    draw_glow(im, (cx,cy), 25, EMERALD, 120, 14)
    d.ellipse((cx-10,cy-10,cx+10,cy+10), fill=rgba(STAR_WHITE,255), outline=rgba(EMERALD,200), width=2)


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(oracle_ground(fs, ABYSS, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 85), 'a pyramid of light', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'four levels — three triads — nine emanations', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 145), 'the numbers are the bones of reality', font=SMALL_FONT, fill=EMERALD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(4):
        p = clamp(prog*1.2 - i*0.1)
        if p <= 0: continue
        w = 50 + i*80
        y = cy + 20 + i*55
        d.rounded_rectangle((cx-w//2,y,cx+w//2,y+30), radius=6, outline=rgba(CRYSTAL,int(180*p)), fill=rgba(CRYSTAL,int(20*p)), width=2)
        d.text((cx,y+15), f'triad {i+1}', font=TINY_FONT, fill=rgba(CRYSTAL,int(200*p)), anchor='mm')
        if i < 3:
            bx = cx; by = y+30; tx = cx; ty = cy+20+(i+1)*55
            pts = partial_polyline([(bx,by),(tx,ty)], p)
            if len(pts) > 1: draw_line_glow(im, pts, STAR_WHITE, 1, 60, 3)
    draw_glow(im, (cx, cy-20), 8, STAR_WHITE, 100, 8)
    d.ellipse((cx-3,cy-23,cx+3,cy-17), fill=rgba(WHITE,255))


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(oracle_ground(fs, ABYSS, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 230
    d.text((cx, 80), 'the soul descends', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 110), 'through the planetary spheres', font=TERM_FONT, fill=STAR_WHITE, anchor='mm')
    d.text((cx, 140), 'at each sphere — a new garment', font=SMALL_FONT, fill=MIST, anchor='mm')
    spheres = [STAR_WHITE, FLOWER_GOLD, EMERALD_LIGHT, CRYSTAL, SPHERE_IRIS, DAIMON_SPARK, COSMIC_FIRE]
    prog = ease_in_out(t)
    soul_y = lerp(140, 420, prog)
    draw_glow(im, (cx, int(soul_y)), 10, STAR_WHITE, 130, 8)
    d.ellipse((cx-5,int(soul_y)-5,cx+5,int(soul_y)+5), fill=rgba(WHITE,255))
    for i, col in enumerate(spheres):
        y = 160 + i*35
        if abs(soul_y - y) < 20:
            d.ellipse((cx-70,y-12,cx+70,y+12), outline=rgba(col,180), width=2)
        else:
            d.line((cx-50,y,cx+50,y), fill=rgba(col,80), width=1)
        d.text((cx+80,y-4), ['moon','mercury','venus','sun','mars','jupiter','saturn'][i], font=TINY_FONT, fill=rgba(col,120), anchor='mm')


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(oracle_ground(fs, ABYSS, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 80), 'to ascend is not to climb', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 110), 'but to shed', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 145), 'the diver rises by letting each garment fall away', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    soul_y = lerp(420, 140, prog)
    draw_glow(im, (cx, int(soul_y)), 14, STAR_WHITE, 150, 8)
    d.ellipse((cx-5,int(soul_y)-5,cx+5,int(soul_y)+5), fill=rgba(WHITE,255))
    for i in range(7):
        y = 400 - i*35
        offset = (prog - i*0.1)
        if offset > 0 and offset < 1:
            fade = 1 - offset
            col = mix(COSMIC_FIRE, SPHERE_IRIS, i/7)
            d.ellipse((cx-60+30*offset,y-10,cx+60-30*offset,y+10), outline=rgba(col,int(180*fade)), width=2)


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(oracle_ground(fs, WARM_DARK := (22,20,24), COSMIC_FIRE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 85), 'philosophy vs theurgy', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'reading about honey', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 140), 'vs placing honey on your tongue', font=SMALL_FONT, fill=EMERALD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    d.rounded_rectangle((200,220,420,360), radius=12, outline=rgba(SLATE,150), width=2)
    d.text((310,290), 'book', font=SMALL_FONT, fill=SLATE, anchor='mm')
    draw_glow(im, (860,300), int(15+25*prog), COSMIC_FIRE, int(100*prog), 14)
    d.polygon([(860,260),(840,340),(880,340)], outline=rgba(COSMIC_FIRE,int(200*prog)), fill=rgba(COSMIC_FIRE,int(40*prog)))
    for i in range(6):
        x = 640 + (i-3)*80
        d.ellipse((x-8,380-8,x+8,380+8), outline=rgba(SLATE,80), width=1)
    d.text((640, 480), 'reason takes you to the door. fire takes you through it.', font=SUB_FONT, fill=MIST, anchor='mm')


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(oracle_ground(fs, DEEP, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 90), 'the flower of the intellect', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), 'a seed the father planted', font=TERM_FONT, fill=FLOWER_GOLD, anchor='mm')
    d.text((cx, 150), 'before you were born', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.ellipse((cx-25,230,cx+25,310), outline=rgba(SLATE,120), width=2)
    draw_glow(im, (cx,270), 12, FLOWER_GOLD, 120, 10)
    d.ellipse((cx-5,265,cx+5,275), fill=rgba(FLOWER_GOLD,255))
    d.text((640, 478), 'untouched by anything you have done or learned or become', font=SUB_FONT, fill=MIST, anchor='mm')


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(oracle_ground(fs, DEEP, FLOWER_GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'it grows toward the fire', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'because the fire is its native element', font=TERM_FONT, fill=FLOWER_GOLD, anchor='mm')
    d.text((cx, 150), 'the flower opens. it was always open.', font=SMALL_FONT, fill=EMERALD_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    stem = bezier((cx, 380), (cx-10, 340), (cx+15, 280), (cx, 220), 60)
    reveal = partial_polyline(stem, clamp((prog-0.1)*1.2))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, EMERALD, 3, 100, 6)
    if prog > 0.6:
        p = clamp((prog-0.6)*2.5)
        draw_glow(im, (cx, 200), int(15+20*p), FLOWER_GOLD, int(130*p), 14)
        for i in range(8):
            a = -math.pi/2 + i*2*math.pi/8
            x = cx + math.cos(a)*25*p
            y = 200 + math.sin(a)*18*p
            d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(FLOWER_GOLD,int(200*p)))
        d.ellipse((cx-6,194,cx+6,206), fill=rgba(STAR_WHITE,int(200*p)))


def sc13(im, t):
    fs = SEED + int(t*9973+6000) % 100000
    im.paste(oracle_ground(fs, ABYSS, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 85), 'the moon is a stopping place', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'the stars are beings who sang when you were born', font=TERM_FONT, fill=STAR_WHITE, anchor='mm')
    d.text((cx, 150), 'not balls of gas', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    rng = np.random.default_rng(252)
    for i in range(60):
        x = float(rng.uniform(60,W-60))
        y = float(rng.uniform(170,450))
        r = float(rng.uniform(1,3))
        a = int(30+170*prog*(0.2+0.8*rng.random()))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(DAIMON_SPARK, a))
    draw_glow(im, (cx, cy+60), 16, SILVER, int(80*prog), 12)
    d.ellipse((cx-12,cy+48,cx+12,cy+72), fill=rgba(SILVER,int(100*prog)), outline=rgba(DAIMON_SPARK,150), width=1)


def sc14(im, t):
    fs = SEED + int(t*9973+6500) % 100000
    im.paste(oracle_ground(fs, WARM_DARK := (22,20,24), EMERALD, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 95), 'the theurgist does not study the map', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'he walks the terrain', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 160), 'the terrain is his own soul', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    d.rounded_rectangle((250,210,500,360), radius=10, outline=rgba(EMERALD,int(120*(1-prog))), width=2)
    d.text((375,285), 'map', font=SMALL_FONT, fill=rgba(EMERALD,int(150*(1-prog))), anchor='mm')
    if prog > 0.3:
        p = clamp((prog-0.3)/0.7)
        d.ellipse((cx-p*150,220,cx+p*150,350), outline=rgba(FLOWER_GOLD,int(150*p)), width=2)
        d.ellipse((cx-10,cy+10-8,cx+10,cy+10+8), fill=rgba(FLOWER_GOLD,int(180*p)))
        d.text((cx, cy+60), 'the soul itself', font=SMALL_FONT, fill=rgba(FLOWER_GOLD,int(200*p)), anchor='mm')
    d.text((640, 485), 'which turns out to be identical with the soul of the universe', font=SUB_FONT, fill=MIST, anchor='mm')


def sc15(im, t):
    fs = SEED + int(t*9973+7000) % 100000
    im.paste(oracle_ground(fs, ABYSS, None, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 270
    d.text((cx, 85), 'theurgic silence', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), 'becoming the kind of silence', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 150), 'in which the universe can speak', font=TERM_FONT, fill=STAR_WHITE, anchor='mm')
    prog = ease_in_out(t)
    if prog > 0.5:
        p = clamp((prog-0.5)*2)
        draw_glow(im, (cx,cy), int(10+40*p), EMERALD, int(150*p), 20)
        d.ellipse((cx-8,cy-8,cx+8,cy+8), fill=rgba(EMERALD_LIGHT,int(200*p)))
        for i in range(3):
            r = 45 + i*30
            d.ellipse((cx-r,cy-r*0.62,cx+r,cy+r*0.62), outline=rgba(EMERALD,int(120*p*(1-i/3))), width=1)
        d.text((cx, cy+70), 'the oracles have been waiting', font=SMALL_FONT, fill=rgba(EMERALD_LIGHT,int(200*p)), anchor='mm')
        d.text((cx, cy+95), 'for someone to stop talking long enough to hear them', font=SMALL_FONT, fill=rgba(STAR_WHITE,int(200*p)), anchor='mm')


SCENES =,Scene('co01','Fragments','Before Plato, before Pythagoras — there were the Oracles.','Logia','','fragments',['oracles','fragments','lost'],'intro','floating fragments in darkness',6.0,sc01)
Scene('co02','The Depth','A hand reaching into water — the water closes without a seam.','Buthos','','father',['father','depth','abyss'],'father','hand descending into still water',8.0,sc02)
Scene('co03','Symbols of Wisdom','Seeds of wonder, love, creation, truth — sown in souls.','Synthemata','','seeds',['seeds','wisdom','symbols'],'sowing','seed-points descending into dark',8.0,sc03)
Scene('co04','The Hinge','Hekate stands between two fires — the space through which both move.','Hekate','','hekate',['hekate','hinge','fires'],'hekate','silhouette between star-white above and cosmic-fire below',10.0,sc04)
Scene('co05','The Dancing Daimons','A great band of daimons dances around her star-girdle.','Daimones','','daimons',['daimons','dance','sparks'],'hekate','sparks circling emerald center',8.0,sc05)
Scene('co06','The Matrix','The center from which all powers issue.','Mētragchys','','matrix',['matrix','powers','source'],'hekate','radiating emerald rays from center',8.0,sc06)
Scene('co07','The Pyramid of Light','Four levels — three triads — nine emanations.','Tetractys','','pyramid',['pyramid','triads','emanations'],'cosmos','crystalline pyramid descending',8.0,sc07)
Scene('co08','The Descent','The soul descends through seven spheres — each adds a garment.','Kathodos','','descent',['descent','spheres','garments'],'soul','white point descending through seven colored spheres',8.0,sc08)
Scene('co09','The Ascent','To ascend is not to climb but to shed.','Anodos','','ascent',['ascent','shedding','garments'],'soul','soul rising, garments falling away',8.0,sc09)
Scene('co10','Honey on the Tongue','Reason takes you to the door. Fire takes you through.','Theourgia','','theurgy',['philosophy','theurgy','fire'],'practice','book vs flame — theurgy and philosophy',6.0,sc10)
Scene('co11','The Flower of the Intellect','A seed the Father planted before you were born.','Nous anthos','','flower',['flower','intellect','seed'],'flower','seed glowing within body-silhouette',8.0,sc11)
Scene('co12','The Flower Opens','It grows toward the fire. It was always open.','Anthos','','opening',['flower','opening','fire'],'flower','stem reaching upward, flower blossoming',8.0,sc12)
Scene('co13','The Living Cosmos','The moon is a waystation. Stars are beings who sang at your birth.','Kosmos','','cosmos',['moon','stars','beings'],'cosmos','starfield with conscious star-beings',8.0,sc13)
Scene('co14','The Terrain','The map dissolves. The soul is the landscape.','Topos','','terrain',['map','terrain','soul'],'practice','map fading into living landscape of soul',6.0,sc14)
Scene('co15','The Silence','Becoming the kind of silence in which the universe can speak.','Sighē','','silence',['silence','universe','speaking'],'seal','stillness — then emerald ring expanding',8.0,sc15)
Scene('co01','Fragments','Before Plato, before Pythagoras — there were the Oracles.','Logia','','fragments',['oracles','fragments','lost'],'intro','floating fragments in darkness',6.0,sc01)
Scene('co02','The Depth','A hand reaching into water — the water closes without a seam.','Buthos','','father',['father','depth','abyss'],'father','hand descending into still water',8.0,sc02)
Scene('co03','Symbols of Wisdom','Seeds of wonder, love, creation, truth — sown in souls.','Synthemata','','seeds',['seeds','wisdom','symbols'],'sowing','seed-points descending into dark',8.0,sc03)
Scene('co04','The Hinge','Hekate stands between two fires — the space through which both move.','Hekate','','hekate',['hekate','hinge','fires'],'hekate','silhouette between star-white above and cosmic-fire below',10.0,sc04)
Scene('co05','The Dancing Daimons','A great band of daimons dances around her star-girdle.','Daimones','','daimons',['daimons','dance','sparks'],'hekate','sparks circling emerald center',8.0,sc05)
Scene('co06','The Matrix','The center from which all powers issue.','Mētragchys','','matrix',['matrix','powers','source'],'hekate','radiating emerald rays from center',8.0,sc06)
Scene('co07','The Pyramid of Light','Four levels — three triads — nine emanations.','Tetractys','','pyramid',['pyramid','triads','emanations'],'cosmos','crystalline pyramid descending',8.0,sc07)
Scene('co08','The Descent','The soul descends through seven spheres — each adds a garment.','Kathodos','','descent',['descent','spheres','garments'],'soul','white point descending through seven colored spheres',8.0,sc08)
Scene('co09','The Ascent','To ascend is not to climb but to shed.','Anodos','','ascent',['ascent','shedding','garments'],'soul','soul rising, garments falling away',8.0,sc09)
Scene('co10','Honey on the Tongue','Reason takes you to the door. Fire takes you through.','Theourgia','','theurgy',['philosophy','theurgy','fire'],'practice','book vs flame — theurgy and philosophy',6.0,sc10)
Scene('co11','The Flower of the Intellect','A seed the Father planted before you were born.','Nous anthos','','flower',['flower','intellect','seed'],'flower','seed glowing within body-silhouette',8.0,sc11)
Scene('co12','The Flower Opens','It grows toward the fire. It was always open.','Anthos','','opening',['flower','opening','fire'],'flower','stem reaching upward, flower blossoming',8.0,sc12)
Scene('co13','The Living Cosmos','The moon is a waystation. Stars are beings who sang at your birth.','Kosmos','','cosmos',['moon','stars','beings'],'cosmos','starfield with conscious star-beings',8.0,sc13)
Scene('co14','The Terrain','The map dissolves. The soul is the landscape.','Topos','','terrain',['map','terrain','soul'],'practice','map fading into living landscape of soul',6.0,sc14)
Scene('co15','The Silence','Becoming the kind of silence in which the universe can speak.','Sighē','','silence',['silence','universe','speaking'],'seal','stillness — then emerald ring expanding',8.0,sc15)
Scene('co01','Fragments','Before Plato, before Pythagoras — there were the Oracles.','Logia','','fragments',['oracles','fragments','lost'],'intro','floating fragments in darkness',6.0,sc01)
Scene('co02','The Depth','A hand reaching into water — the water closes without a seam.','Buthos','','father',['father','depth','abyss'],'father','hand descending into still water',8.0,sc02)
Scene('co03','Symbols of Wisdom','Seeds of wonder, love, creation, truth — sown in souls.','Synthemata','','seeds',['seeds','wisdom','symbols'],'sowing','seed-points descending into dark',8.0,sc03)
Scene('co04','The Hinge','Hekate stands between two fires — the space through which both move.','Hekate','','hekate',['hekate','hinge','fires'],'hekate','silhouette between star-white above and cosmic-fire below',10.0,sc04)
Scene('co05','The Dancing Daimons','A great band of daimons dances around her star-girdle.','Daimones','','daimons',['daimons','dance','sparks'],'hekate','sparks circling emerald center',8.0,sc05)
Scene('co06','The Matrix','The center from which all powers issue.','Mētragchys','','matrix',['matrix','powers','source'],'hekate','radiating emerald rays from center',8.0,sc06)
Scene('co07','The Pyramid of Light','Four levels — three triads — nine emanations.','Tetractys','','pyramid',['pyramid','triads','emanations'],'cosmos','crystalline pyramid descending',8.0,sc07)
Scene('co08','The Descent','The soul descends through seven spheres — each adds a garment.','Kathodos','','descent',['descent','spheres','garments'],'soul','white point descending through seven colored spheres',8.0,sc08)
Scene('co09','The Ascent','To ascend is not to climb but to shed.','Anodos','','ascent',['ascent','shedding','garments'],'soul','soul rising, garments falling away',8.0,sc09)
Scene('co10','Honey on the Tongue','Reason takes you to the door. Fire takes you through.','Theourgia','','theurgy',['philosophy','theurgy','fire'],'practice','book vs flame — theurgy and philosophy',6.0,sc10)
Scene('co11','The Flower of the Intellect','A seed the Father planted before you were born.','Nous anthos','','flower',['flower','intellect','seed'],'flower','seed glowing within body-silhouette',8.0,sc11)
Scene('co12','The Flower Opens','It grows toward the fire. It was always open.','Anthos','','opening',['flower','opening','fire'],'flower','stem reaching upward, flower blossoming',8.0,sc12)
Scene('co13','The Living Cosmos','The moon is a waystation. Stars are beings who sang at your birth.','Kosmos','','cosmos',['moon','stars','beings'],'cosmos','starfield with conscious star-beings',8.0,sc13)
Scene('co14','The Terrain','The map dissolves. The soul is the landscape.','Topos','','terrain',['map','terrain','soul'],'practice','map fading into living landscape of soul',6.0,sc14)
Scene('co15','The Silence','Becoming the kind of silence in which the universe can speak.','Sighē','','silence',['silence','universe','speaking'],'seal','stillness — then emerald ring expanding',8.0,sc15) [
    Scene('co01','Fragments','Before Plato, before Pythagoras — there were the Oracles.','Logia','','fragments',['oracles','fragments','lost'],'intro','floating fragments in darkness',6.0,sc01),
    Scene('co02','The Depth','A hand reaching into water — the water closes without a seam.','Buthos','','father',['father','depth','abyss'],'father','hand descending into still water',8.0,sc02),
    Scene('co03','Symbols of Wisdom','Seeds of wonder, love, creation, truth — sown in souls.','Synthemata','','seeds',['seeds','wisdom','symbols'],'sowing','seed-points descending into dark',8.0,sc03),
    Scene('co04','The Hinge','Hekate stands between two fires — the space through which both move.','Hekate','','hekate',['hekate','hinge','fires'],'hekate','silhouette between star-white above and cosmic-fire below',10.0,sc04),
    Scene('co05','The Dancing Daimons','A great band of daimons dances around her star-girdle.','Daimones','','daimons',['daimons','dance','sparks'],'hekate','sparks circling emerald center',8.0,sc05),
    Scene('co06','The Matrix','The center from which all powers issue.','Mētragchys','','matrix',['matrix','powers','source'],'hekate','radiating emerald rays from center',8.0,sc06),
    Scene('co07','The Pyramid of Light','Four levels — three triads — nine emanations.','Tetractys','','pyramid',['pyramid','triads','emanations'],'cosmos','crystalline pyramid descending',8.0,sc07),
    Scene('co08','The Descent','The soul descends through seven spheres — each adds a garment.','Kathodos','','descent',['descent','spheres','garments'],'soul','white point descending through seven colored spheres',8.0,sc08),
    Scene('co09','The Ascent','To ascend is not to climb but to shed.','Anodos','','ascent',['ascent','shedding','garments'],'soul','soul rising, garments falling away',8.0,sc09),
    Scene('co10','Honey on the Tongue','Reason takes you to the door. Fire takes you through.','Theourgia','','theurgy',['philosophy','theurgy','fire'],'practice','book vs flame — theurgy and philosophy',6.0,sc10),
    Scene('co11','The Flower of the Intellect','A seed the Father planted before you were born.','Nous anthos','','flower',['flower','intellect','seed'],'flower','seed glowing within body-silhouette',8.0,sc11),
    Scene('co12','The Flower Opens','It grows toward the fire. It was always open.','Anthos','','opening',['flower','opening','fire'],'flower','stem reaching upward, flower blossoming',8.0,sc12),
    Scene('co13','The Living Cosmos','The moon is a waystation. Stars are beings who sang at your birth.','Kosmos','','cosmos',['moon','stars','beings'],'cosmos','starfield with conscious star-beings',8.0,sc13),
    Scene('co14','The Terrain','The map dissolves. The soul is the landscape.','Topos','','terrain',['map','terrain','soul'],'practice','map fading into living landscape of soul',6.0,sc14),
    Scene('co15','The Silence','Becoming the kind of silence in which the universe can speak.','Sighē','','silence',['silence','universe','speaking'],'seal','stillness — then emerald ring expanding',8.0,sc15),
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
            dust(im, SEED + hash(scene.id)%10000 + i, 50)
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
    sheet = Image.new('RGB', (4*320, rows*180), color=ABYSS)
    for idx,im in enumerate(thumbs): sheet.paste(im, ((idx%4)*320, (idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)

def write_metadata():
    manifest = {'project':'Chaldean Oracles — The Fire That Was Never Burned',
        'source_basis':'Expansion Essay 25: "the oracles they tried to burn" — 15 scenes.',
        'style':{'family':'emerald-cosmic-fire oracle visualization','background':'abyssal blue','ink':'emerald, star-white, cosmic fire, crystal'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Chaldean Oracles — 15 scenes, emerald/crystal/fire palette.\n', encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Chaldean Oracles Pack — emerald/star-white/cosmic-fire palette\n', encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Chaldean Oracles — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n', encoding='utf-8')

def validate_outputs():
    combined = ROOT/'chaldean_oracles_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))

def make_zip():
    zpath = ROOT/'chaldean_oracles_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['chaldean_oracles_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4, arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat = ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT/'chaldean_oracles_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
