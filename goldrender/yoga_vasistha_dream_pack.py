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
SEED = 16160

DARK_DREAM = (18, 16, 22)
WARM_DARK = (22, 20, 22)
DEEP = (14, 14, 24)
LAVENDER = (170, 156, 200)
LAVENDER_LIGHT = (210, 200, 230)
ROSE_GOLD = (210, 170, 145)
ROSE_GOLD_LIGHT = (225, 200, 180)
DREAM_BLUE = (140, 170, 210)
DREAM_BLUE_LIGHT = (190, 210, 235)
SILVER = (196, 204, 222)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
TEAL = (92, 146, 148)
CRIMSON = (154, 44, 58)
SLATE = (90, 100, 120)
MIST = (160, 172, 192)

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
    d.rectangle((28,28,W-28,H-28), outline=rgba(LAVENDER,70), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(LAVENDER_LIGHT,45), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,DREAM_BLUE,ROSE_GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im); y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(14,12,20,200), outline=rgba(LAVENDER,45), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24), term, font=TERM_FONT, fill=ROSE_GOLD)


def dust(im, seed, n=55):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40,W-40)); y = float(rng.uniform(40,H-40))
        r = float(rng.uniform(0.8,2.0))
        c = mix(LAVENDER_LIGHT,DREAM_BLUE_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)


def dream_ground(seed, bg, glow_col, intensity=0.5):
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
    base -= np.clip((dx*dx+dy*dy)*16,0,24)[...,None]
    if glow_col:
        g = np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.38)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i] += g * glow_col[i] * 0.035
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def dream_ripple(d, cx, cy, t, col, max_r=200):
    for i in range(3):
        phase = i/3
        r = max_r * clamp((t*0.8) - phase)
        if r <= 5: continue
        alpha = int(60 * (1-r/max_r))
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(col, alpha), width=1)


@dataclass
class Scene:
    id: str; title: str; subtitle: str; term: str; summary: str
    mode: str; tags: list[str]; group: str; technique: str
    duration: float; draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, LAVENDER, 0.4), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 110), 'what if you are dreaming right now?', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 145), 'what if this room, this body, these thoughts', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((cx, 170), 'are no more solid than a dream?', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    dream_ripple(d, cx, cy, t, LAVENDER, 180)
    for i in range(3):
        x = cx - 80 + i*80
        y = cy + 40 + 15*math.sin(t*1.5 + i*2)
        offset = 8*math.sin(t*2 + i*1.3)
        d.ellipse((x-40+offset, y-25, x+40+offset, y+25), outline=rgba(DREAM_BLUE, int(80+60*prog)), width=1)
    draw_glow(im, (cx,cy), 15, LAVENDER_LIGHT, 60, 12)


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, DREAM_BLUE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 100), 'what is this world?', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 130), 'who am i? what is bondage?', font=TERM_FONT, fill=ROSE_GOLD, anchor='mm')
    d.text((cx, 160), 'how can i be free?', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    dissolve = 0.5 + 0.5*math.sin(t*1.5)
    d.ellipse((cx-35,cy+40-10*dissolve,cx+35,cy+90+10*dissolve), outline=rgba(SILVER, int(120+80*dissolve)), width=2)
    d.ellipse((cx-22,cy+50,cx+22,cy+80), outline=rgba(LAVENDER, int(80*prog)), width=1)
    for i in range(8):
        a = i*2*math.pi/8 + t*0.2
        r = 30 + 20*dissolve
        x = cx + math.cos(a)*r
        y = cy + 65 + math.sin(a)*r*0.5
        d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(DREAM_BLUE_LIGHT, int(60*dissolve)))


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, ROSE_GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 85), 'stories within stories', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'nested like russian dolls', font=TERM_FONT, fill=ROSE_GOLD, anchor='mm')
    d.text((cx, 145), 'each frame is a level of the dream', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    frames_cols = [ROSE_GOLD, LAVENDER, DREAM_BLUE, GOLD, SILVER]
    for i in range(5):
        p = clamp(prog*1.3 - i*0.08)
        if p <= 0: continue
        s = 1 - i*0.15
        x0 = cx - 180*s
        y0 = cy + 20 - 120*s
        x1 = cx + 180*s
        y1 = cy + 20 + 120*s
        d.rounded_rectangle((int(x0),int(y0),int(x1),int(y1)), radius=12, outline=rgba(frames_cols[i], int(160*p)), width=2)
        if i == 0:
            d.ellipse((int(cx-15),int(cy-5),int(cx+15),int(cy+25)), outline=rgba(PEARL, int(200*p)), width=2)


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, DREAM_BLUE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'a queen visited another universe', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'through the power of her mind', font=TERM_FONT, fill=DREAM_BLUE_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    crack_x = lerp(cx, cx-100, prog)
    d.rounded_rectangle((80,160,cx,500), radius=14, outline=rgba(SILVER, 120), width=2)
    d.rounded_rectangle((cx,160,1200,500), radius=14, outline=rgba(DREAM_BLUE, 120), width=2)
    d.ellipse((int(crack_x)-18, 320-18, int(crack_x)+18, 320+18), outline=rgba(ROSE_GOLD, 180), width=2)
    draw_glow(im, (int(crack_x), 320), 20, ROSE_GOLD, 80, 12)
    pts = bezier((int(crack_x), 320), (int(crack_x)-40, 280), (int(crack_x)+60, 240), (int(crack_x)+20, 200), 50)
    reveal = partial_polyline(pts, clamp((prog-0.3)*1.5))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, ROSE_GOLD_LIGHT, 2, 80, 5)


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(dream_ground(fs, WARM_DARK, LAVENDER, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'a king dreamed he was a beggar', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'a beggar dreamed he was a king', font=TERM_FONT, fill=ROSE_GOLD, anchor='mm')
    d.text((cx, 155), 'neither is real. both are the dreamer.', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in [0, 1]:
        x = cx + (1 if i==0 else -1) * lerp(100, 50, prog)
        y = cy + 40
        col = GOLD if i==0 else SILVER
        d.ellipse((x-25,y-30,x+25,y+30), outline=rgba(col, 160), width=2)
    draw_line_glow(im, [(cx-100+50*prog, cy+40), (cx+100-50*prog, cy+40)], ROSE_GOLD, 2, 80, 5)
    draw_glow(im, (cx, cy+40), 12, GOLD_LIGHT, 80, 10)


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, DREAM_BLUE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 95), 'the world is a long dream', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'there is no world apart from the mind', font=TERM_FONT, fill=DREAM_BLUE_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(10):
        x = cx - 200 + i*44
        y = cy + 40 + 30*math.sin(i*0.9 + t*2)
        alpha = int(180 * (1-prog) * (0.5+0.5*math.sin(i+t)))
        d.ellipse((x-2,y-2,x+2,y+2), fill=rgba(LAVENDER, alpha))
    for r in [60, 100, 140]:
        d.ellipse((cx-r, cy+20-r*0.62, cx+r, cy+20+r*0.62), outline=rgba(DREAM_BLUE, int(80*(1-prog))), width=1)
    draw_glow(im, (cx, cy+20), 15, GOLD_LIGHT, int(80*prog), 12)
    d.ellipse((cx-6,cy+14,cx+6,cy+26), fill=rgba(WHITE, int(200*prog)))


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(dream_ground(fs, DEEP, ROSE_GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 240
    d.text((cx, 85), 'seven stages of wisdom', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'from desire to absorption', font=SMALL_FONT, fill=MIST, anchor='mm')
    stages = ['īpsā', 'vicāraṇa', 'tanumānasa', 'sattvāpatti', 'asaṅga', 'padārtha-bhāvanā', 'turyagā']
    s_cols = [SLATE, DREAM_BLUE, LAVENDER, GOLD, ROSE_GOLD, DREAM_BLUE_LIGHT, WHITE]
    prog = smoothstep(0.05, 0.9, t)
    for i in range(7):
        p = clamp(prog*1.2 - i*0.06)
        if p <= 0: continue
        y = 170 + i*38
        x0 = cx - 160 + i*12
        x1 = cx + 160 - i*12
        d.line((int(x0), y, int(x1), y), fill=rgba(s_cols[i], int(180*p)), width=3)
        d.text((cx-175+i*12, y-6), stages[i], font=TINY_FONT, fill=rgba(s_cols[i], int(200*p)), anchor='rm')
        if i == 3:
            draw_glow(im, (cx, y), 18, GOLD, int(100*p), 12)
            d.ellipse((cx-6,y-6,cx+6,y+6), fill=rgba(WHITE, int(200*p)))


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(dream_ground(fs, DEEP, LAVENDER, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 95), 'the mind alone is the universe', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'when the mind is still, the world ceases', font=TERM_FONT, fill=LAVENDER_LIGHT, anchor='mm')
    prog = ease_in_out(t)
    for i in range(5):
        r = 30 + i*30
        alpha = int(160 * (1-prog) * (1-i/6))
        d.ellipse((cx-r, cy+20-r*0.62, cx+r, cy+20+r*0.62), outline=rgba(LAVENDER, alpha), width=2)
    if prog > 0.5:
        p = clamp((prog-0.5)*2)
        draw_glow(im, (cx, cy+20), int(10+30*p), GOLD_LIGHT, int(120*p), 16)
        d.ellipse((cx-8, cy+12, cx+8, cy+28), fill=rgba(WHITE, int(255*p)))
    d.text((640, 480), 'stop your mind for one moment', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((640, 500), 'and see what happens to the world', font=TINY_FONT, fill=SLATE, anchor='mm')


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 95), 'the jivanmukta', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'a lamp that flickers after the oil is gone', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, 158), 'acting without doership, thinking without thinker', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    d.ellipse((cx-12,230,cx+12,260), outline=rgba(GOLD, 120), width=2)
    pts = [(cx,200),(cx-12,230),(cx+12,230)]
    d.polygon(pts, outline=rgba(GOLD, 150), fill=rgba(GOLD, 30))
    draw_glow(im, (cx, 195), int(15+20*prog), GOLD_LIGHT, int(100*prog), 14)
    d.ellipse((cx-6,189,cx+6,201), fill=rgba(WHITE, int(220*prog)))


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(dream_ground(fs, DEEP, TEAL, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 95), 'the breath is the handle of the mind', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'two branches of the same tree', font=TERM_FONT, fill=TEAL, anchor='mm')
    prog = ease_in_out(t)
    trunk = bezier((cx, 480), (cx-20, 400), (cx+15, 320), (cx, 250), 60)
    reveal = partial_polyline(trunk, prog)
    if len(reveal) > 1:
        draw_line_glow(im, reveal, GOLD, 3, 100, 7)
    b1 = bezier((cx, 320), (cx+40, 280), (cx+100, 260), (cx+140, 240), 40)
    b2 = bezier((cx, 340), (cx-50, 300), (cx-100, 280), (cx-140, 260), 40)
    b1r = partial_polyline(b1, clamp((prog-0.3)*1.5))
    b2r = partial_polyline(b2, clamp((prog-0.3)*1.5))
    if len(b1r) > 1: draw_line_glow(im, b1r, TEAL, 2, 80, 5)
    if len(b2r) > 1: draw_line_glow(im, b2r, LAVENDER, 2, 80, 5)
    d.text((cx+150, 238), 'prāṇa', font=TINY_FONT, fill=TEAL, anchor='lm')
    d.text((cx-150, 258), 'citta', font=TINY_FONT, fill=LAVENDER, anchor='rm')


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(dream_ground(fs, DEEP, SILVER, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'ajāti-vāda', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'no creation, no destruction', font=TERM_FONT, fill=SILVER, anchor='mm')
    d.text((cx, 155), 'neither the dream nor the waking — just this', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for r in [40, 80, 120]:
        alpha = int(100 * (1-prog))
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(SILVER, alpha), width=1)
    draw_glow(im, (cx,cy), int(10+30*prog), GOLD_LIGHT, int(120*prog), 16)
    d.ellipse((cx-10,cy-10,cx+10,cy+10), fill=rgba(WHITE, int(255*prog)))
    d.text((cx, cy+50), 'sat', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, int(200*prog)), anchor='mm')


def sc12(im, t):
    fs = SEED + int(t*9973+5500) % 100000
    im.paste(dream_ground(fs, DARK_DREAM, ROSE_GOLD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'you are the dreamer', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'you have always been the dreamer', font=TERM_FONT, fill=ROSE_GOLD, anchor='mm')
    d.text((cx, 150), 'the dream becomes transparent. it was never a prison.', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    for i in range(8):
        a = i*2*math.pi/8 + t*0.04
        r = lerp(10, 190, prog)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        draw_line_glow(im, [(cx,cy),(int(x),int(y))], mix(LAVENDER, ROSE_GOLD, i/8), 1, 50, 4)
        d.ellipse((int(x)-3,int(y)-3,int(x)+3,int(y)+3), fill=rgba(mix(LAVENDER, ROSE_GOLD, i/8), 160))
    d.ellipse((cx-180*prog, cy-110*prog, cx+180*prog, cy+110*prog), outline=rgba(ROSE_GOLD, int(120*prog)), width=2)
    draw_glow(im, (cx,cy), 28, GOLD_LIGHT, 120, 14)
    d.ellipse((cx-12,cy-12,cx+12,cy+12), fill=rgba(WHITE,255), outline=rgba(ROSE_GOLD,200), width=2)
    d.text((cx, cy), 'द्रष्टा', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')
    d.text((640, 485), 'the lucid one — dreaming freely', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES =,Scene('yv01','What If You Are Dreaming?','This room, this body — no more solid than a dream.','Svapna','','opening',['dream','question','reality'],'intro','rippling room with soft edges',6.0,sc01)
Scene('yv02','What Is This World?','Rāma\'s existential question — who am I?','Vairāgya','','question',['existential','question','self'],'question','questioning figure with dissolving edges',8.0,sc02)
Scene('yv03','Stories Within Stories','Nested like Russian dolls — each frame is a level of the dream.','Upāya','','narrative',['stories','nested','frames'],'method','five nested frames with diminishing size',10.0,sc03)
Scene('yv04','Another Universe','A queen visited another world through the power of her mind.','Dṛṣṭi-sṛṣṭi','','threshold',['threshold','other world','mind'],'threshold','figure stepping through cracked reality',8.0,sc04)
Scene('yv05','King and Beggar','Each dreaming the other — neither is real.','Bhrānti','','reversal',['king','beggar','dream'],'reversal','two silhouettes exchanging places',8.0,sc05)
Scene('yv06','The Long Dream','No world apart from the mind — perception is creation.','Dṛṣṭi-sṛṣṭi','','dissolution',['dream','world','dissolving'],'dissolution','landscape dissolving into stillness',8.0,sc06)
Scene('yv07','Seven Stages of Wisdom','From desire to absorption — the ascent through the tattvas.','Sapta bhūmika','','ascent',['stages','wisdom','ascent'],'ascent','seven-step ladder with glowing fourth step',8.0,sc07)
Scene('yv08','Still Mind, Still World','When the mind is still, the world ceases to exist.','Citta','','stillness',['mind','stillness','cessation'],'stillness','concentric rings dissolving to still center',8.0,sc08)
Scene('yv09','The Jīvanmukta','A lamp that flickers after the oil is gone.','Jīvanmukta','','liberation',['liberated','lamp','oil'],'liberation','flame burning without fuel',8.0,sc09)
Scene('yv10','Two Branches, One Tree','The breath is the handle of the mind.','Prāṇa-samrodha','','practice',['breath','mind','tree'],'practice','tree branching into prāṇa and citta',8.0,sc10)
Scene('yv11','No Creation, No Destruction','Neither dream nor waking — ajāti-vāda.','Ajāti','','non-origination',['non-origination','stillness','presence'],'culmination','bare presence with dissolving rings',8.0,sc11)
Scene('yv12','You Are the Dreamer','The dream becomes transparent. It was never a prison.','Jīvanmukti','','seal',['dreamer','recognition','freedom'],'seal','radial dream-mandala with recognizing self',6.0,sc12)
Scene('yv01','What If You Are Dreaming?','This room, this body — no more solid than a dream.','Svapna','','opening',['dream','question','reality'],'intro','rippling room with soft edges',6.0,sc01)
Scene('yv02','What Is This World?','Rāma\'s existential question — who am I?','Vairāgya','','question',['existential','question','self'],'question','questioning figure with dissolving edges',8.0,sc02)
Scene('yv03','Stories Within Stories','Nested like Russian dolls — each frame is a level of the dream.','Upāya','','narrative',['stories','nested','frames'],'method','five nested frames with diminishing size',10.0,sc03)
Scene('yv04','Another Universe','A queen visited another world through the power of her mind.','Dṛṣṭi-sṛṣṭi','','threshold',['threshold','other world','mind'],'threshold','figure stepping through cracked reality',8.0,sc04)
Scene('yv05','King and Beggar','Each dreaming the other — neither is real.','Bhrānti','','reversal',['king','beggar','dream'],'reversal','two silhouettes exchanging places',8.0,sc05)
Scene('yv06','The Long Dream','No world apart from the mind — perception is creation.','Dṛṣṭi-sṛṣṭi','','dissolution',['dream','world','dissolving'],'dissolution','landscape dissolving into stillness',8.0,sc06)
Scene('yv07','Seven Stages of Wisdom','From desire to absorption — the ascent through the tattvas.','Sapta bhūmika','','ascent',['stages','wisdom','ascent'],'ascent','seven-step ladder with glowing fourth step',8.0,sc07)
Scene('yv08','Still Mind, Still World','When the mind is still, the world ceases to exist.','Citta','','stillness',['mind','stillness','cessation'],'stillness','concentric rings dissolving to still center',8.0,sc08)
Scene('yv09','The Jīvanmukta','A lamp that flickers after the oil is gone.','Jīvanmukta','','liberation',['liberated','lamp','oil'],'liberation','flame burning without fuel',8.0,sc09)
Scene('yv10','Two Branches, One Tree','The breath is the handle of the mind.','Prāṇa-samrodha','','practice',['breath','mind','tree'],'practice','tree branching into prāṇa and citta',8.0,sc10)
Scene('yv11','No Creation, No Destruction','Neither dream nor waking — ajāti-vāda.','Ajāti','','non-origination',['non-origination','stillness','presence'],'culmination','bare presence with dissolving rings',8.0,sc11)
Scene('yv12','You Are the Dreamer','The dream becomes transparent. It was never a prison.','Jīvanmukti','','seal',['dreamer','recognition','freedom'],'seal','radial dream-mandala with recognizing self',6.0,sc12)
Scene('yv01','What If You Are Dreaming?','This room, this body — no more solid than a dream.','Svapna','','opening',['dream','question','reality'],'intro','rippling room with soft edges',6.0,sc01)
Scene('yv02','What Is This World?','Rāma\'s existential question — who am I?','Vairāgya','','question',['existential','question','self'],'question','questioning figure with dissolving edges',8.0,sc02)
Scene('yv03','Stories Within Stories','Nested like Russian dolls — each frame is a level of the dream.','Upāya','','narrative',['stories','nested','frames'],'method','five nested frames with diminishing size',10.0,sc03)
Scene('yv04','Another Universe','A queen visited another world through the power of her mind.','Dṛṣṭi-sṛṣṭi','','threshold',['threshold','other world','mind'],'threshold','figure stepping through cracked reality',8.0,sc04)
Scene('yv05','King and Beggar','Each dreaming the other — neither is real.','Bhrānti','','reversal',['king','beggar','dream'],'reversal','two silhouettes exchanging places',8.0,sc05)
Scene('yv06','The Long Dream','No world apart from the mind — perception is creation.','Dṛṣṭi-sṛṣṭi','','dissolution',['dream','world','dissolving'],'dissolution','landscape dissolving into stillness',8.0,sc06)
Scene('yv07','Seven Stages of Wisdom','From desire to absorption — the ascent through the tattvas.','Sapta bhūmika','','ascent',['stages','wisdom','ascent'],'ascent','seven-step ladder with glowing fourth step',8.0,sc07)
Scene('yv08','Still Mind, Still World','When the mind is still, the world ceases to exist.','Citta','','stillness',['mind','stillness','cessation'],'stillness','concentric rings dissolving to still center',8.0,sc08)
Scene('yv09','The Jīvanmukta','A lamp that flickers after the oil is gone.','Jīvanmukta','','liberation',['liberated','lamp','oil'],'liberation','flame burning without fuel',8.0,sc09)
Scene('yv10','Two Branches, One Tree','The breath is the handle of the mind.','Prāṇa-samrodha','','practice',['breath','mind','tree'],'practice','tree branching into prāṇa and citta',8.0,sc10)
Scene('yv11','No Creation, No Destruction','Neither dream nor waking — ajāti-vāda.','Ajāti','','non-origination',['non-origination','stillness','presence'],'culmination','bare presence with dissolving rings',8.0,sc11)
Scene('yv12','You Are the Dreamer','The dream becomes transparent. It was never a prison.','Jīvanmukti','','seal',['dreamer','recognition','freedom'],'seal','radial dream-mandala with recognizing self',6.0,sc12) [
    Scene('yv01','What If You Are Dreaming?','This room, this body — no more solid than a dream.','Svapna','','opening',['dream','question','reality'],'intro','rippling room with soft edges',6.0,sc01),
    Scene('yv02','What Is This World?','Rāma\'s existential question — who am I?','Vairāgya','','question',['existential','question','self'],'question','questioning figure with dissolving edges',8.0,sc02),
    Scene('yv03','Stories Within Stories','Nested like Russian dolls — each frame is a level of the dream.','Upāya','','narrative',['stories','nested','frames'],'method','five nested frames with diminishing size',10.0,sc03),
    Scene('yv04','Another Universe','A queen visited another world through the power of her mind.','Dṛṣṭi-sṛṣṭi','','threshold',['threshold','other world','mind'],'threshold','figure stepping through cracked reality',8.0,sc04),
    Scene('yv05','King and Beggar','Each dreaming the other — neither is real.','Bhrānti','','reversal',['king','beggar','dream'],'reversal','two silhouettes exchanging places',8.0,sc05),
    Scene('yv06','The Long Dream','No world apart from the mind — perception is creation.','Dṛṣṭi-sṛṣṭi','','dissolution',['dream','world','dissolving'],'dissolution','landscape dissolving into stillness',8.0,sc06),
    Scene('yv07','Seven Stages of Wisdom','From desire to absorption — the ascent through the tattvas.','Sapta bhūmika','','ascent',['stages','wisdom','ascent'],'ascent','seven-step ladder with glowing fourth step',8.0,sc07),
    Scene('yv08','Still Mind, Still World','When the mind is still, the world ceases to exist.','Citta','','stillness',['mind','stillness','cessation'],'stillness','concentric rings dissolving to still center',8.0,sc08),
    Scene('yv09','The Jīvanmukta','A lamp that flickers after the oil is gone.','Jīvanmukta','','liberation',['liberated','lamp','oil'],'liberation','flame burning without fuel',8.0,sc09),
    Scene('yv10','Two Branches, One Tree','The breath is the handle of the mind.','Prāṇa-samrodha','','practice',['breath','mind','tree'],'practice','tree branching into prāṇa and citta',8.0,sc10),
    Scene('yv11','No Creation, No Destruction','Neither dream nor waking — ajāti-vāda.','Ajāti','','non-origination',['non-origination','stillness','presence'],'culmination','bare presence with dissolving rings',8.0,sc11),
    Scene('yv12','You Are the Dreamer','The dream becomes transparent. It was never a prison.','Jīvanmukti','','seal',['dreamer','recognition','freedom'],'seal','radial dream-mandala with recognizing self',6.0,sc12),
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
    sheet = Image.new('RGB', (4*320, rows*180), color=DARK_DREAM)
    for idx,im in enumerate(thumbs): sheet.paste(im, ((idx%4)*320, (idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)

def write_metadata():
    manifest = {'project':'Yoga Vāsiṣṭha — The Dream That You Are',
        'source_basis':'Expansion Essay 16: "the dream that you are" — 12 scenes.',
        'style':{'family':'dream / surreal visualization','background':'dark dream tones','ink':'lavender, rose-gold, dream-blue, silver'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    d = 'Yoga Vasistha — 12 scenes, dream/surreal palette.\n'
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d, encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Yoga Vasistha Pack — dream/surreal lavender/rose-gold palette\n', encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Yoga Vāsiṣṭha — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n', encoding='utf-8')

def validate_outputs():
    combined = ROOT/'yoga_vasistha_dream_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))

def make_zip():
    zpath = ROOT/'yoga_vasistha_dream_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['yoga_vasistha_dream_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4, arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat = ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT/'yoga_vasistha_dream_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
