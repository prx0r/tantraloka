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
SEED = 12121

DEEP = (12, 14, 26)
TWILIGHT = (20, 18, 34)
NIGHT = (16, 18, 28)
EMERALD = (65, 135, 100)
EMERALD_LIGHT = (130, 200, 155)
PEARL = (246, 243, 236)
STAR_WHITE = (238, 244, 250)
WHITE = (252, 250, 246)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
FLAME = (220, 140, 50)
ROSE_GOLD = (210, 170, 140)
DAWN = (200, 180, 200)
SILVER = (196, 204, 222)
LAVENDER = (170, 160, 200)
SLATE = (90, 100, 120)
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
    d.rectangle((28,28,W-28,H-28), outline=rgba(EMERALD,90), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(LAVENDER,60), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,EMERALD,ROSE_GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im); y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(14,14,26,200), outline=rgba(EMERALD,50), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24), term, font=TERM_FONT, fill=ROSE_GOLD)


def dust(im, seed, n=40):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40,W-40)); y = float(rng.uniform(40,H-40))
        r = float(rng.uniform(0.8,2.0))
        c = mix(DAWN,EMERALD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(15,50))))
    im.alpha_composite(ov)


def imaginal_ground(seed, bg, glow_col, intensity=0.6):
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
        g = np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.40)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i] += g * glow_col[i] * 0.035
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def luminous_figure(d, im, cx, cy, r, col, t, prog, inner_col=None):
    inner_col = inner_col or col
    draw_glow(im, (cx,cy), int(r*1.5), col, int(100*prog), 25)
    d.ellipse((cx-int(r*0.5),cy-int(r*0.7), cx+int(r*0.5), cy+int(r*0.7)), fill=rgba(inner_col,int(150*prog)), outline=rgba(col,int(200*prog)), width=2)
    d.ellipse((cx-int(r*0.3),cy-int(r*0.1), cx+int(r*0.3), cy+int(r*0.1)), fill=rgba(inner_col,int(200*prog)))
    for i in range(6):
        a = i*2*math.pi/6 + t*0.06
        x = cx + math.cos(a)*r*0.6
        y = cy + math.sin(a)*r*0.4
        d.ellipse((x-4,y-4,x+4,y+4), fill=rgba(col,int(120*prog)))


@dataclass
class Scene:
    id: str; title: str; subtitle: str; term: str; summary: str
    mode: str; tags: list[str]; group: str; technique: str
    duration: float; draw_fn: Callable[[Image.Image, float], None]


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 100), 'what if there is a world', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 130), 'neither physical nor spiritual', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 160), '— but somewhere in between?', font=TERM_FONT, fill=DAWN, anchor='mm')
    prog = ease_in_out(t)
    crack_h = lerp(2, 300, prog)
    d.rounded_rectangle((cx-120,cy-crack_h/2,cx+120,cy+crack_h/2), radius=8, outline=rgba(EMERALD,int(150*prog)), width=2)
    draw_glow(im, (cx,cy), int(10+20*prog), EMERALD_LIGHT, int(100*prog), 12)
    d.text((640, 480), 'the mundus imaginalis — more real than either', font=SUB_FONT, fill=MIST, anchor='mm')


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, EMERALD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 95), 'active imagination', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'an organ of perception', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 155), 'tuned to a real world', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    open_frac = lerp(0.05, 0.95, prog)
    d.arc((cx-60,cy+10,cx+60,cy+110), 0, 360, fill=rgba(SILVER,150), width=3)
    d.ellipse((cx-55,cy+15,cx+55,cy+105), fill=rgba(TWILIGHT,200))
    d.ellipse((cx-int(50*open_frac),cy+20,cx+int(50*open_frac),cy+100), fill=rgba(EMERALD_LIGHT,int(60*prog)))
    d.ellipse((cx-3,cy+58,cx+3,cy+62), fill=rgba(STAR_WHITE,int(200*prog)))
    d.text((640, 485), 'like the eye or the ear — but turned inward', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 95), 'the suprasensory orient', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 125), 'the cosmic north', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 155), 'where your soul came from before it entered this body', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    angle = lerp(0, 2*math.pi, smoothstep(0.1, 0.6, t)) if t < 0.6 else 2*math.pi
    d.ellipse((cx-80,cy+10,cx+80,cy+90), outline=rgba(EMERALD,120), width=2)
    dx = 60*math.cos(angle)
    dy = 40*math.sin(angle)
    draw_glow(im, (int(cx+dx),int(cy+50+dy)), 6, STAR_WHITE, 120, 6)
    d.line((cx,cy+50,int(cx+dx),int(cy+50+dy)), fill=rgba(STAR_WHITE,180), width=2)
    if t > 0.6:
        p = clamp((t-0.6)*2.5)
        d.text((cx,cy+120), '\u2191 north', font=SMALL_FONT, fill=rgba(ROSE_GOLD,int(200*p)), anchor='mm')
    d.text((640, 485), 'to turn toward the imaginal world is to turn toward home', font=SUB_FONT, fill=MIST, anchor='mm')


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, STAR_WHITE, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'the perfect nature', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'the person of light', font=TERM_FONT, fill=STAR_WHITE, anchor='mm')
    d.text((cx, 145), 'the being that has been with you since before your birth', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    luminous_figure(d, im, cx, cy+20, 50, STAR_WHITE, t, prog, PEARL)
    d.text((640, 490), 'neither a symbol nor a psychological projection — real', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 90), 'the thread of the spider', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 120), 'cut — and re-joined', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 150), '1 x 1', font=TERM_FONT, fill=STAR_WHITE, anchor='mm')
    prog = ease_in_out(t)
    pts = bezier((300,270),(500,220),(780,320),(980,270),80)
    draw_line_glow(im, pts, SILVER, 2, 100, 5)
    if prog > 0.3 and prog < 0.7:
        cut = clamp((prog-0.3)*2.5)
        cx1 = int(lerp(300,640,0.5-cut*0.05))
        cx2 = int(lerp(640,980,0.5+cut*0.05))
        d.line((300,270,cx1, int(lerp(270,400,0.5))), fill=rgba(SILVER,100), width=2)
        d.line((cx2,int(lerp(400,270,0.5)),980,270), fill=rgba(SILVER,100), width=2)
    if prog > 0.7:
        p = clamp((prog-0.7)*3.3)
        draw_line_glow(im, pts, EMERALD_LIGHT, 3, int(150*p), 6)
        d.text((cx,cy+100), 'not 1=1, not n+1 — 1\u00d71', font=SMALL_FONT, fill=rgba(ROSE_GOLD,int(200*p)), anchor='mm')


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, STAR_WHITE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 85), 'your face becomes pure', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'it radiates light', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 145), 'then another face appears — made of light', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    draw_glow(im, (cx-100,cy+10), int(20+30*prog), STAR_WHITE, int(100*prog), 20)
    d.ellipse((cx-100-20,cy+10-25,cx-100+20,cy+10+25), outline=rgba(STAR_WHITE,int(200*prog)), width=2)
    if prog > 0.4:
        p = clamp((prog-0.4)*1.7)
        draw_glow(im, (cx+100,cy-10), int(20+30*p), GOLD_LIGHT, int(100*p), 20)
        d.ellipse((cx+100-20,cy-10-25,cx+100+20,cy-10+25), outline=rgba(GOLD_LIGHT,int(200*p)), width=2)
        d.line((cx-78,cy+5,cx+78,cy-5), fill=rgba(ROSE_GOLD,int(150*p)), width=2)
    d.text((640, 480), 'the face you had before you were born', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(imaginal_ground(fs, DEEP, FLAME, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 255
    d.text((cx, 85), 'the dhikr', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'fire that burns away', font=TERM_FONT, fill=FLAME, anchor='mm')
    d.text((cx, 145), 'everything between you and the person of light', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    flame_h = lerp(10, 180, prog)
    d.polygon([(cx,cy+60-flame_h),(cx-30,cy+50),(cx-12,cy+60),(cx+18,cy+55),(cx+35,cy+50)],
              fill=rgba(FLAME,int(60*prog)), outline=rgba(FLAME,int(200*prog)))
    draw_glow(im, (cx,cy+20), int(flame_h*0.3), FLAME, int(100*prog), 14)
    for i in range(8):
        a = i*2*math.pi/8 + t*0.1
        r = 40 + 80*prog
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.6
        d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(FLAME,int(80*prog)))
    d.text((640, 485), 'the repetition itself is the ascent', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(imaginal_ground(fs, DEEP, STAR_WHITE, 0.2), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'light upon light', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'when your light meets its light', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 145), 'they do not merge — they combine', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    x1 = lerp(200, 540, prog)
    x2 = lerp(1080, 740, prog)
    draw_glow(im, (int(x1),cy+20), 18, STAR_WHITE, 120, 12)
    d.ellipse((int(x1)-8,cy+12,int(x1)+8,cy+28), fill=rgba(WHITE,220))
    draw_glow(im, (int(x2),cy+20), 18, GOLD_LIGHT, 120, 12)
    d.ellipse((int(x2)-8,cy+12,int(x2)+8,cy+28), fill=rgba(GOLD_LIGHT,220))
    if abs(x1-x2) < 100:
        mid = (x1+x2)/2
        draw_glow(im, (int(mid),cy+20), 25, EMERALD_LIGHT, 140, 16)
        d.ellipse((int(mid)-10,cy+10,int(mid)+10,cy+30), fill=rgba(WHITE,255))
    d.text((640, 485), 'nurun \'ala nur — light upon light', font=SUB_FONT, fill=MIST, anchor='mm')


def sc09(im, t):
    fs = SEED + int(t*9973+4000) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, None, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 250
    d.text((cx, 80), 'the chinvat bridge', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 110), '"who art thou?"', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 140), '"i am your own celestial counterpart"', font=TERM_FONT, fill=ROSE_GOLD, anchor='mm')
    prog = ease_in_out(t)
    bridge = bezier((200,370),(400,330),(880,330),(1080,370),60)
    draw_line_glow(im, bridge, SILVER, 2, 90, 6)
    luminous_figure(d, im, int(lerp(300,550,prog)), 310, 25, STAR_WHITE, t, prog, PEARL)
    luminous_figure(d, im, int(lerp(980,730,prog)), 310, 22, ROSE_GOLD, t, prog, PEARL)
    d.text((640, 488), 'i was loved — you made me more loved. i was beautiful — you made me more beautiful.', font=SUB_FONT, fill=MIST, anchor='mm')


def sc10(im, t):
    fs = SEED + int(t*9973+4500) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, STAR_WHITE, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'the guide is both parent and child', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'you create each other', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 150), 'the relationship is mutual, recursive, and eternal', font=SMALL_FONT, fill=MIST, anchor='mm')
    luminous_figure(d, im, cx-100, cy+20, 30, STAR_WHITE, t, 1.0, PEARL)
    luminous_figure(d, im, cx+100, cy+20, 30, ROSE_GOLD, t, 1.0, PEARL)
    draw_line_glow(im, [(cx-70,cy+20),(cx+70,cy+20)], GOLD_LIGHT, 2, 100, 6)
    for i in range(6):
        a = i*2*math.pi/6 + t*0.08
        x = cx + math.cos(a)*20
        y = cy + 20 + math.sin(a)*14
        d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(EMERALD_LIGHT,180))


def sc11(im, t):
    fs = SEED + int(t*9973+5000) % 100000
    im.paste(imaginal_ground(fs, TWILIGHT, EMERALD, 0.3), (0,0))
    d = ImageDraw.Draw(im); cx, cy = W/2, 260
    d.text((cx, 85), 'the door is always open', font=TERM_FONT, fill=PEARL, anchor='mm')
    d.text((cx, 115), 'the guide is always waiting', font=TERM_FONT, fill=EMERALD_LIGHT, anchor='mm')
    d.text((cx, 150), 'the only question is whether you will open your other eyes', font=SMALL_FONT, fill=MIST, anchor='mm')
    prog = ease_in_out(t)
    d.rounded_rectangle((cx-80,cy-40,cx+80,cy+80), radius=40, outline=rgba(EMERALD,int(150*prog)), width=2)
    d.rounded_rectangle((cx-55,cy-20,cx+55,cy+60), radius=28, fill=rgba(EMERALD_LIGHT,int(40*prog)))
    if prog > 0.3:
        p = clamp((prog-0.3)/0.7)
        luminous_figure(d, im, cx+100, cy+10, 20, STAR_WHITE, t, p, PEARL)
    d.text((640, 485), 'the mundus imaginalis is more real than the physical. it does not pass away.', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES =,Scene('mi01','The World Between Worlds','Neither physical nor spiritual — somewhere in between.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'intro','crack of light in twilight',6.0,sc01)
Scene('mi02','Active Imagination','An organ of perception tuned to a real world.','Imaginatio vera','','perception',['imagination','perception','organ'],'faculty','inner eye opening to another world',8.0,sc02)
Scene('mi03','The Cosmic North','The suprasensory orient — where you came from.','Al-mashriq','','orientation',['north','orient','origin'],'orientation','compass needle settling on new direction',8.0,sc03)
Scene('mi04','The Person of Light','The perfect nature — with you since before birth.','Shakhs nurani','','guide',['guide','light','nature'],'guide','luminous figure of pure light approaching',10.0,sc04)
Scene('mi05','1x1','The spider\'s thread — cut and re-joined.','Unus-ambo','','formula',['thread','unity','difference'],'formula','glowing thread cut and restored with 1x1',8.0,sc05)
Scene('mi06','Two Faces','Your face becomes light — then another appears.','Shakhs nurani','','encounter',['face','light','recognition'],'encounter','two luminous faces recognizing each other',8.0,sc06)
Scene('mi07','The Dhikr','Fire that burns away what separates you.','Dhikr','','practice',['fire','dhikr','burning'],'practice','rising flame consuming obstacles',8.0,sc07)
Scene('mi08','Light Upon Light','Your light meets its light — they combine.','Nurun \'ala nur','','union',['light','union','combine'],'union','two lights approaching and combining',8.0,sc08)
Scene('mi09','The Chinvat Bridge','"Who art thou?" "I am your own celestial counterpart."','Daena','','bridge',['bridge','meeting','daena'],'bridge','two figures meeting on a bridge of light',8.0,sc09)
Scene('mi10','Mutual Creation','The guide is both parent and child — you give birth to each other.','Syzygy','','relationship',['mutual','creation','recursive'],'relationship','two figures connected by heart-thread',6.0,sc10)
Scene('mi11','The Open Door','The door is always open. The guide is always waiting.','Janua','','seal',['door','waiting','open'],'seal','door of light standing open, guide at threshold',8.0,sc11)
Scene('mi01','The World Between Worlds','Neither physical nor spiritual — somewhere in between.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'intro','crack of light in twilight',6.0,sc01)
Scene('mi02','Active Imagination','An organ of perception tuned to a real world.','Imaginatio vera','','perception',['imagination','perception','organ'],'faculty','inner eye opening to another world',8.0,sc02)
Scene('mi03','The Cosmic North','The suprasensory orient — where you came from.','Al-mashriq','','orientation',['north','orient','origin'],'orientation','compass needle settling on new direction',8.0,sc03)
Scene('mi04','The Person of Light','The perfect nature — with you since before birth.','Shakhs nurani','','guide',['guide','light','nature'],'guide','luminous figure of pure light approaching',10.0,sc04)
Scene('mi05','1x1','The spider\'s thread — cut and re-joined.','Unus-ambo','','formula',['thread','unity','difference'],'formula','glowing thread cut and restored with 1x1',8.0,sc05)
Scene('mi06','Two Faces','Your face becomes light — then another appears.','Shakhs nurani','','encounter',['face','light','recognition'],'encounter','two luminous faces recognizing each other',8.0,sc06)
Scene('mi07','The Dhikr','Fire that burns away what separates you.','Dhikr','','practice',['fire','dhikr','burning'],'practice','rising flame consuming obstacles',8.0,sc07)
Scene('mi08','Light Upon Light','Your light meets its light — they combine.','Nurun \'ala nur','','union',['light','union','combine'],'union','two lights approaching and combining',8.0,sc08)
Scene('mi09','The Chinvat Bridge','"Who art thou?" "I am your own celestial counterpart."','Daena','','bridge',['bridge','meeting','daena'],'bridge','two figures meeting on a bridge of light',8.0,sc09)
Scene('mi10','Mutual Creation','The guide is both parent and child — you give birth to each other.','Syzygy','','relationship',['mutual','creation','recursive'],'relationship','two figures connected by heart-thread',6.0,sc10)
Scene('mi11','The Open Door','The door is always open. The guide is always waiting.','Janua','','seal',['door','waiting','open'],'seal','door of light standing open, guide at threshold',8.0,sc11)
Scene('mi01','The World Between Worlds','Neither physical nor spiritual — somewhere in between.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'intro','crack of light in twilight',6.0,sc01)
Scene('mi02','Active Imagination','An organ of perception tuned to a real world.','Imaginatio vera','','perception',['imagination','perception','organ'],'faculty','inner eye opening to another world',8.0,sc02)
Scene('mi03','The Cosmic North','The suprasensory orient — where you came from.','Al-mashriq','','orientation',['north','orient','origin'],'orientation','compass needle settling on new direction',8.0,sc03)
Scene('mi04','The Person of Light','The perfect nature — with you since before birth.','Shakhs nurani','','guide',['guide','light','nature'],'guide','luminous figure of pure light approaching',10.0,sc04)
Scene('mi05','1x1','The spider\'s thread — cut and re-joined.','Unus-ambo','','formula',['thread','unity','difference'],'formula','glowing thread cut and restored with 1x1',8.0,sc05)
Scene('mi06','Two Faces','Your face becomes light — then another appears.','Shakhs nurani','','encounter',['face','light','recognition'],'encounter','two luminous faces recognizing each other',8.0,sc06)
Scene('mi07','The Dhikr','Fire that burns away what separates you.','Dhikr','','practice',['fire','dhikr','burning'],'practice','rising flame consuming obstacles',8.0,sc07)
Scene('mi08','Light Upon Light','Your light meets its light — they combine.','Nurun \'ala nur','','union',['light','union','combine'],'union','two lights approaching and combining',8.0,sc08)
Scene('mi09','The Chinvat Bridge','"Who art thou?" "I am your own celestial counterpart."','Daena','','bridge',['bridge','meeting','daena'],'bridge','two figures meeting on a bridge of light',8.0,sc09)
Scene('mi10','Mutual Creation','The guide is both parent and child — you give birth to each other.','Syzygy','','relationship',['mutual','creation','recursive'],'relationship','two figures connected by heart-thread',6.0,sc10)
Scene('mi11','The Open Door','The door is always open. The guide is always waiting.','Janua','','seal',['door','waiting','open'],'seal','door of light standing open, guide at threshold',8.0,sc11) [
    Scene('mi01','The World Between Worlds','Neither physical nor spiritual — somewhere in between.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'intro','crack of light in twilight',6.0,sc01),
    Scene('mi02','Active Imagination','An organ of perception tuned to a real world.','Imaginatio vera','','perception',['imagination','perception','organ'],'faculty','inner eye opening to another world',8.0,sc02),
    Scene('mi03','The Cosmic North','The suprasensory orient — where you came from.','Al-mashriq','','orientation',['north','orient','origin'],'orientation','compass needle settling on new direction',8.0,sc03),
    Scene('mi04','The Person of Light','The perfect nature — with you since before birth.','Shakhs nurani','','guide',['guide','light','nature'],'guide','luminous figure of pure light approaching',10.0,sc04),
    Scene('mi05','1x1','The spider\'s thread — cut and re-joined.','Unus-ambo','','formula',['thread','unity','difference'],'formula','glowing thread cut and restored with 1x1',8.0,sc05),
    Scene('mi06','Two Faces','Your face becomes light — then another appears.','Shakhs nurani','','encounter',['face','light','recognition'],'encounter','two luminous faces recognizing each other',8.0,sc06),
    Scene('mi07','The Dhikr','Fire that burns away what separates you.','Dhikr','','practice',['fire','dhikr','burning'],'practice','rising flame consuming obstacles',8.0,sc07),
    Scene('mi08','Light Upon Light','Your light meets its light — they combine.','Nurun \'ala nur','','union',['light','union','combine'],'union','two lights approaching and combining',8.0,sc08),
    Scene('mi09','The Chinvat Bridge','"Who art thou?" "I am your own celestial counterpart."','Daena','','bridge',['bridge','meeting','daena'],'bridge','two figures meeting on a bridge of light',8.0,sc09),
    Scene('mi10','Mutual Creation','The guide is both parent and child — you give birth to each other.','Syzygy','','relationship',['mutual','creation','recursive'],'relationship','two figures connected by heart-thread',6.0,sc10),
    Scene('mi11','The Open Door','The door is always open. The guide is always waiting.','Janua','','seal',['door','waiting','open'],'seal','door of light standing open, guide at threshold',8.0,sc11),
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
    sheet = Image.new('RGB', (4*320, rows*180), color=TWILIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im, ((idx%4)*320, (idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)

def write_metadata():
    manifest = {'project':'Mundus Imaginalis — The World Between Worlds',
        'source_basis':'Expansion Essay 12: "the world between worlds" (Corbin) — 11 scenes.',
        'style':{'family':'threshold imaginal visualization','background':'twilight indigo','ink':'emerald, star-white, rose-gold, dawn'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Mundus Imaginalis — 11 scenes, threshold/emerald/person-of-light palette.\n', encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Mundus Imaginalis Pack — twilight/emerald/rose-gold palette\n', encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Mundus Imaginalis — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n', encoding='utf-8')

def validate_outputs():
    combined = ROOT/'mundus_imaginalis_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe), indent=2))

def make_zip():
    zpath = ROOT/'mundus_imaginalis_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['mundus_imaginalis_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4, arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, f'({sc.duration}s)', flush=True)
        render_scene(sc)
    concat = ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT/'mundus_imaginalis_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
