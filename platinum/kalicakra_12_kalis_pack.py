#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile, sys
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
SEED = 12012

# Dark Kālīcakra palette
NIGHT = (18, 16, 20)
OBSIDIAN = (27, 24, 30)
SMOKE = (85, 80, 88)
ASH = (160, 150, 142)
IVORY = (236, 228, 214)
CRIMSON = (149, 38, 57)
BLOOD = (108, 22, 31)
EMBER = (218, 108, 38)
GOLD = (196, 152, 78)
GOLD_LIGHT = (243, 207, 132)
INDIGO = (64, 70, 112)
BONE = (215, 202, 184)
SLATE = (105, 109, 120)
BLUE_GREY = (116, 126, 150)
FLAME = (244, 153, 61)
WHITE = (248, 243, 232)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 24)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def ease_in_out(t: float) -> float:
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1, c2, t: float):
    t = clamp(t)
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def rgba(c, a=255):
    return (*c[:3], int(a))


def dark_parchment(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(OBSIDIAN, dtype=np.float32)
    coarse = rng.normal(0, 1, (42, 76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse - coarse.min()) / (np.ptp(coarse) + 1e-6) * 255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32) - 128) / 128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None] * 5.2 + fine[..., None] * 1.3
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2)/(W/2)
    dy = (yy - H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy)*22, 0, 28)
    base -= vign[..., None]
    # subtle furnace glow from center-bottom
    furnace = np.exp(-(((xx-W/2)/(W*0.32))**2 + ((yy-H*0.63)/(H*0.22))**2)*2.4)
    for i,c in enumerate((EMBER[0], EMBER[1], EMBER[2])):
        base[..., i] += furnace * (18 if i==0 else 8)
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W, H), (0,0,0,0))


def draw_glow(im: Image.Image, xy, radius, color, alpha=160, blur=18):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im: Image.Image, pts, color, width=3, alpha=160, blur=9):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1, width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+70)), width=width, joint='curve')


def footer(im: Image.Image, title: str, subtitle: str, term: str | None = None, deva: str | None = None):
    d = ImageDraw.Draw(im)
    y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(20,18,25,196), outline=rgba(ASH,80), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=IVORY)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=ASH)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-120-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)
    if deva:
        d.text((W-260, y0+56), deva, font=DEVA_SMALL, fill=mix(BLOOD, IVORY, .45))


def border(im: Image.Image):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(ASH,120), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,90), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, BLOOD, GOLD)


def partial_polyline(points, amount: float):
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


def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
        y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
        pts.append((x,y))
    return pts


def regular_polygon(cx,cy,r,n,rot=-math.pi/2):
    return [(cx+math.cos(rot+2*math.pi*i/n)*r, cy+math.sin(rot+2*math.pi*i/n)*r) for i in range(n)]


def star_points(cx,cy,r1,r2,n=8,rot=-math.pi/2):
    pts=[]
    for i in range(n*2):
        r=r1 if i%2==0 else r2
        a=rot+math.pi*i/n
        pts.append((cx+math.cos(a)*r, cy+math.sin(a)*r))
    return pts


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,150), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def draw_flame(draw, cx, cy, scale=1.0, color=FLAME, fill=None):
    fill = fill or rgba((255,182,96), 70)
    pts = [(cx, cy-72*scale), (cx-28*scale, cy-12*scale), (cx-10*scale, cy+36*scale),
           (cx+2*scale, cy+2*scale), (cx+20*scale, cy+52*scale), (cx+40*scale, cy-4*scale)]
    draw.polygon(pts, outline=rgba(color, 220), fill=fill)


def draw_kali_crown(draw, cx, cy, scale=1.0, color=GOLD_LIGHT):
    for i in range(5):
        ang = -math.pi/2 + (i-2)*0.26
        x = cx + math.cos(ang)*40*scale
        y = cy + math.sin(ang)*18*scale
        draw_flame(draw, x, y, 0.28*scale, color=color, fill=rgba(color,55))
    draw.arc((cx-48*scale, cy-10*scale, cx+48*scale, cy+38*scale), 180, 360, fill=rgba(color,220), width=max(1, int(3*scale)))


def draw_orbiting_dots(draw, cx, cy, r1, r2, n, color, phase=0):
    for i in range(n):
        a = phase + i*2*math.pi/n
        x = cx + math.cos(a)*r1
        y = cy + math.sin(a)*r2
        draw.ellipse((x-4,y-4,x+4,y+4), fill=rgba(color, 210))


def draw_spokes(draw, cx, cy, r, n, color, a0=0.0, width=1):
    for i in range(n):
        a = a0 + i*2*math.pi/n
        draw.line((cx,cy,cx+math.cos(a)*r,cy+math.sin(a)*r), fill=rgba(color,120), width=width)


def draw_smoke_ribbon(im, start, end, control_y, count, color=SMOKE, t=0.0):
    for i in range(count):
        off = (i-(count-1)/2)*10
        pts = bezier((start[0], start[1]+off), (start[0]+160, control_y-off), (end[0]-160, control_y+off), (end[0], end[1]-off), 90)
        draw_line_glow(im, pts, mix(color, ASH, i/max(1,count-1)), 2, 70, 7)


def draw_ash_field(im, n=120, seed=0):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 3))
        col = mix(ASH, SMOKE, rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(col, int(rng.uniform(40,110))))
    im.alpha_composite(ov)


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


# ------ Scene definitions ------

def s01(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_glow(im, (cx, cy), 55+20*t, GOLD_LIGHT, 160, 18)
    d.ellipse((cx-16,cy-16,cx+16,cy+16), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    for i in range(12):
        a = -math.pi/2 + i*2*math.pi/12 + t*0.05
        pts = bezier((cx,cy),(cx+math.cos(a)*80,cy+math.sin(a)*40),(cx+math.cos(a)*180,cy+math.sin(a)*90),(cx+math.cos(a)*260,cy+math.sin(a)*170),70)
        pts = partial_polyline(pts, smoothstep(0.05,0.85,t))
        if len(pts)>1: draw_line_glow(im, pts, mix(EMBER,GOLD_LIGHT,i/12), 3, 110, 7)
    draw_kali_crown(d, cx, 118, 1.0, GOLD_LIGHT)


def s02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 292
    for i in range(7):
        rr = 60 + i*34
        alpha = int(140*(1-i/7))
        d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr), outline=rgba(mix(BLOOD,GOLD,i/7), alpha), width=2)
    draw_orbiting_dots(d, cx, cy, 170, 90, 10, BLOOD, phase=t*2*math.pi*0.25)
    draw_glow(im,(cx,cy),40,CRIMSON,100,10)
    d.ellipse((cx-22,cy-22,cx+22,cy+22), fill=rgba(BLOOD,220), outline=rgba(GOLD_LIGHT,180), width=2)
    d.text((640, 505), 'the field is held and dyed with intensity', font=SUB_FONT, fill=ASH, anchor='mm')


def s03(im, t):
    d = ImageDraw.Draw(im)
    cx = W/2
    for i in range(11):
        y = 140 + i*28
        w = 60 + i*52
        a = clamp(t*1.15 - i*0.06)
        if a <= 0: continue
        d.arc((cx-w, y-16, cx+w, y+16), 190, 350, fill=rgba(mix(SMOKE,ASH,.45), int(155*a)), width=2)
    sever = 260 + (1-ease_in_out(t))*160
    d.line((250,sever,1030,sever), fill=rgba(BLOOD,150), width=3)
    d.text((640, 498), 'what was held begins to lose its standing', font=SUB_FONT, fill=ASH, anchor='mm')


def s04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    for i in range(9):
        r = 34 + i*36
        a = int(130*(1-i/9))
        d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(mix(INDIGO,SMOKE,i/9), a), width=2)
    # central dark seed
    draw_glow(im, (cx, cy), 70, INDIGO, 90, 18)
    d.ellipse((cx-48,cy-48,cx+48,cy+48), fill=rgba(NIGHT,240), outline=rgba(ASH,120), width=2)
    for i in range(6):
        a = i*2*math.pi/6 + t*0.08
        x = cx + math.cos(a)*132
        y = cy + math.sin(a)*74
        d.line((x,y,cx,cy), fill=rgba(SMOKE,75), width=1)


def s05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 300
    # contracting rings
    for i in range(6):
        f = 1 - ease_in_out(t)*0.7
        rx = (180 - i*22)*f + 20
        ry = (110 - i*14)*f + 10
        d.arc((cx-rx,cy-ry,cx+rx,cy+ry), 200, 340, fill=rgba(mix(CRIMSON,ASH,i/6), 160), width=3)
    # silhouette being pulled inward
    d.ellipse((cx-18,cy-60,cx+18,cy-24), fill=rgba(ASH,180))
    d.polygon([(cx-42,cy+32),(cx-24,cy-16),(cx+24,cy-16),(cx+42,cy+32)], fill=rgba(ASH,150))
    draw_glow(im, (cx, cy), 26, BLOOD, 100, 9)


def s06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    for i in range(12):
        a = -math.pi/2 + i*2*math.pi/12
        r = 190
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.66
        draw_flame(d, x, y, 0.35, FLAME, fill=rgba((255,170,80),40))
        draw_line_glow(im, [(x,y),(cx,cy)], mix(EMBER,GOLD,i/12), 2, 80, 6)
    draw_glow(im,(cx,cy),70,EMBER,140,20)
    d.ellipse((cx-26,cy-26,cx+26,cy+26), fill=rgba(NIGHT,255), outline=rgba(EMBER,220), width=3)
    d.arc((cx-70,cy-70,cx+70,cy+70), 0, 330, fill=rgba(GOLD_LIGHT,180), width=2)


def s07(im, t):
    d = ImageDraw.Draw(im)
    x0,y0,x1,y1 = 230, 170, 1050, 420
    cols = [GOLD_LIGHT, ASH, BLOOD]
    # vertical sorting slots
    for i in range(7):
        x = lerp(x0, x1, i/6)
        d.line((x, y0, x, y1), fill=rgba(mix(SMOKE,ASH,.25), 80), width=1)
    for i in range(22):
        a = i*2*math.pi/22 + t*0.06
        px = 640 + math.cos(a)*260
        py = 280 + math.sin(a)*120
        target = [330,640,950][i%3]
        qx = lerp(px, target, ease_in_out(t))
        qy = lerp(py, 300 + (i%5-2)*22, ease_in_out(t))
        d.ellipse((qx-6,qy-6,qx+6,qy+6), fill=rgba(cols[i%3], 210))
    d.text((330, 450), 'retain', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((640, 450), 'discard', font=TERM_FONT, fill=ASH, anchor='mm')
    d.text((950, 450), 'subtle', font=TERM_FONT, fill=CRIMSON, anchor='mm')


def s08(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    names = ['hearing','touch','sight','taste','smell']
    pos = [(cx-250,cy-90),(cx-125,cy-145),(cx,cy-165),(cx+125,cy-145),(cx+250,cy-90)]
    for i,(x,y) in enumerate(pos):
        s = clamp(t*1.15 - i*0.08)
        if s<=0: continue
        d.ellipse((x-28,y-28,x+28,y+28), outline=rgba(mix(GOLD_LIGHT,ASH,i/5), int(180*s)), width=2)
        d.text((x,y), str(i+1), font=TERM_FONT, fill=rgba(IVORY, int(200*s)), anchor='mm')
        pts = partial_polyline(bezier((x,y),(x,y+80),(cx + (x-cx)*0.3, cy+40),(cx,cy+90), 80), s)
        if len(pts)>1: draw_line_glow(im, pts, mix(ASH,SMOKE,.4), 2, 80, 5)
        d.text((x, y+50), names[i], font=SMALL_FONT, fill=ASH, anchor='mm')
    draw_glow(im,(cx,cy+116),36,INDIGO,90,10)
    d.ellipse((cx-22,cy+92,cx+22,cy+136), fill=rgba(NIGHT,240), outline=rgba(INDIGO,160), width=2)


def s09(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 290
    # multi-level lattice collapsing inward
    for i in range(7):
        w = 100 + i*78
        h = 42 + i*28
        s = 1 - ease_in_out(t)*0.65
        d.rectangle((cx-w*s, cy-h*s, cx+w*s, cy+h*s), outline=rgba(mix(INDIGO,ASH,i/7), 120), width=2)
    for i in range(9):
        ang = i*2*math.pi/9+t*0.03
        x = cx + math.cos(ang)*210*(1-t*0.65)
        y = cy + math.sin(ang)*120*(1-t*0.65)
        d.ellipse((x-5,y-5,x+5,y+5), fill=rgba(GOLD,190))
    d.text((640, 500), 'the organizing intellect loses its architecture', font=SUB_FONT, fill=ASH, anchor='mm')


def s10(im, t):
    d = ImageDraw.Draw(im)
    # burning canvas effect
    prog = smoothstep(0.08,0.92,t)
    rect = (180, 110, 1100, 470)
    d.rectangle(rect, outline=rgba(ASH,120), width=2, fill=rgba((30,28,36), 60))
    # burn line from left to right
    xburn = lerp(rect[0]+40, rect[2]-40, prog)
    for y in np.linspace(rect[1]+30, rect[3]-30, 16):
        draw_line_glow(im, [(rect[0]+40,y),(xburn,y)], mix(EMBER,GOLD_LIGHT, (y-rect[1])/(rect[3]-rect[1])), 2, 120, 8)
    # char edge
    d.line((xburn, rect[1]+14, xburn, rect[3]-14), fill=rgba(BLOOD, 180), width=4)
    for i in range(20):
        yy = lerp(rect[1]+18, rect[3]-18, i/19)
        draw_flame(d, xburn+12+8*math.sin(i), yy, 0.18, FLAME, fill=rgba((255,170,80),35))


def s11(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    # vast clock-like ring but abstract
    for i in range(6):
        rr = 58 + i*44
        d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr), outline=rgba(mix(SMOKE,ASH,i/6), 120), width=2)
    draw_spokes(d, cx, cy, 245, 24, SMOKE, a0=t*0.12, width=1)
    draw_glow(im,(cx,cy),80,EMBER,90,18)
    d.ellipse((cx-36,cy-36,cx+36,cy+36), fill=rgba(NIGHT,250), outline=rgba(EMBER,210), width=2)
    d.text((cx, cy), 'काल', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, 220), anchor='mm')


def s12(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 282
    # unmoving fire seal: outer flames, inner still void flame
    for i in range(12):
        a = -math.pi/2 + i*2*math.pi/12
        x = cx + math.cos(a)*190
        y = cy + math.sin(a)*120
        draw_flame(d, x, y, 0.28, mix(FLAME,GOLD_LIGHT,i/12), fill=rgba((255,170,90),30))
    for r,col in [(168,ASH),(128,GOLD),(88,CRIMSON)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(col, 140), width=2)
    draw_glow(im,(cx,cy),86,GOLD_LIGHT,120,22)
    d.ellipse((cx-26,cy-26,cx+26,cy+26), fill=rgba(WHITE,255), outline=rgba(GOLD_LIGHT,220), width=2)
    flame = [(cx,cy-78),(cx-30,cy-8),(cx-12,cy+42),(cx+4,cy+8),(cx+22,cy+54),(cx+40,cy-4)]
    d.polygon(flame, outline=rgba(FLAME,220), fill=rgba((255,190,110),55))
    # stillness rays
    for i in range(18):
        a = i*2*math.pi/18
        d.line((cx+math.cos(a)*110, cy+math.sin(a)*70, cx+math.cos(a)*138, cy+math.sin(a)*90), fill=rgba(ASH, 95), width=1)


SCENES = [
    Scene('kc01', 'Sṛṣṭikālī', 'Emission: form flashes outward from the consuming center.', 'Sṛṣṭikālī', 'The cycle begins in projection and creative emission.', 'emission_burst', ['creation','cycle','kalī'], 'cycle', 'radial furnace emission', s01),
    Scene('kc02', 'Raktakālī', 'Retention: the field is held, saturated, and intensified.', 'Raktakālī', 'The emitted field is retained and dyed with force.', 'retention_orbit', ['retention','intensity','kalī'], 'cycle', 'blood-ring retention', s02),
    Scene('kc03', 'Sthitināśakālī', 'The support of stable standing begins to fail.', 'Sthitināśakālī', 'What seemed fixed begins to lose its standing.', 'standing_dissolution', ['dissolution','standing','kalī'], 'cycle', 'layered canopy severance', s03),
    Scene('kc04', 'Yamayayokālī', 'Unmanifest potential gathers into a dark seed.', 'Yamayayokālī', 'The process turns toward latent, unexpressed possibility.', 'latent_seed', ['potential','void','kalī'], 'cycle', 'dark seed with concentric potential', s04),
    Scene('kc05', 'Saṃhārakālī', 'The egoic center is withdrawn into contraction.', 'Saṃhārakālī', 'The grasped self is pulled back toward the devouring heart.', 'ego_withdrawal', ['withdrawal','ego','kalī'], 'cycle', 'contracting arcs', s05),
    Scene('kc06', 'Mṛtyukālī', 'Death and time are themselves devoured.', 'Mṛtyukālī', 'Temporal mortality is consumed in a central fire.', 'death_devouring', ['death','time','fire'], 'cycle', 'flame wheel', s06),
    Scene('kc07', 'Bhadrakālī', 'The contents of experience are sorted and re-ordered.', 'Bhadrakālī', 'Spiritual discernment separates, filters, and judges the field.', 'sorting_channels', ['sorting','discernment','kalī'], 'cycle', 'sorting slots and particles', s07),
    Scene('kc08', 'Mārtaṇḍakālī', 'The senses fall inward and lose outward range.', 'Mārtaṇḍakālī', 'The sensory powers are recollected and dissolved.', 'sense_recollection', ['senses','recollection','kalī'], 'cycle', 'five sensory collapse paths', s08),
    Scene('kc09', 'Paramārkakālī', 'The cosmic intellect loses even its subtle architecture.', 'Paramārkakālī', 'The higher organizing framework itself dissolves.', 'intellect_collapse', ['intellect','collapse','kalī'], 'cycle', 'collapsing lattice', s09),
    Scene('kc10', 'Kālāgnirudrakālī', 'The cosmic canvas is burned away.', 'Kālāgnirudrakālī', 'The field of manifestation is incinerated by time-fire.', 'burning_canvas', ['fire','burning','cosmos'], 'cycle', 'canvas burn sweep', s10),
    Scene('kc11', 'Mahākālakālī', 'Great Time remains as total engulfing measurelessness.', 'Mahākālakālī', 'All partial cycles are swallowed into Great Time.', 'great_time', ['time','great time','void'], 'cycle', 'abstract time wheel', s11),
    Scene('kc12', 'Mahābhairavaghoracaṇḍakālī', 'The cycle resolves into absolute unmoving fire.', 'Mahābhairavaghoracaṇḍakālī', 'The final state is terrible, absolute, and still.', 'absolute_fire', ['absolute','bhairava','fire'], 'seal', 'still fire seal', s12),
]


def render_scene(scene: Scene):
    sdir = FRAMES_ROOT / scene.id
    sdir.mkdir(parents=True, exist_ok=True)
    expected = [sdir / f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size > 1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size > 1000:
                continue
            t = i / max(1, NFRAMES-1)
            im = dark_parchment(SEED + hash(scene.id)%10000 + i)
            border(im)
            draw_ash_field(im, 80, seed=SEED+i)
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
    sheet = Image.new('RGB', (4*320, 3*180), color=OBSIDIAN)
    for idx, im in enumerate(thumbs):
        x=(idx%4)*320; y=(idx//4)*180
        sheet.paste(im,(x,y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project':'Tantrāloka — The 12 Kālīs of the Kālīcakra',
        'source_basis':'Conceptual structural cycle of the 12 Kālīs as described by the user from Tantrāloka Chapter 4.',
        'style':{
            'family':'dark tantric furnace cosmography',
            'background':'charcoal vellum / dark parchment',
            'ink':'ash and bone',
            'accent':'blood crimson, ember orange, gold light, indigo smoke',
            'materials':['ash','embers','smoke ribbon','obsidian field','furnace light']
        },
        'fps':FPS,
        'resolution':[W,H],
        'scene_duration_seconds':DURATION,
        'total_scenes':len(SCENES),
        'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[
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
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    catalog = {
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id: sc.title for sc in SCENES},
        'modes':{sc.id: sc.mode for sc in SCENES},
        'theme_clusters':{
            'emission_and_retention':['kc01','kc02'],
            'dissolution_and_withdrawal':['kc03','kc04','kc05','kc06'],
            'sorting_and_cognitive_collapse':['kc07','kc08','kc09'],
            'incineration_and_absolute_fire':['kc10','kc11','kc12']
        },
        'reusability_notes':{
            'kc01':'Use for emission, projection, creation, or the first outward surge.',
            'kc05':'Use for ego withdrawal, contraction, recollection, or inward collapse.',
            'kc07':'Use for sorting, judgment, discrimination, purification, or spiritual filtering.',
            'kc10':'Use for cosmic burning, apocalyptic dissolution, incineration, or time-fire.',
            'kc12':'Use as a closing seal for terrible transcendence, unmoving fire, or Bhairava realization.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The 12 Kālīs of the Kālīcakra

## Aim
This pack visualizes the **12 Kālīs of the Kālīcakra** as a sequential cycle of cognitive and cosmic destruction.

## Textual orientation
The pack is based on the user-supplied conceptual mapping of the 12 Kālīs in Chapter 4 of the *Tantrāloka*. It should not be treated as a philological critical edition. It is a visual-structural pack: a cyclical engine rather than a ritual manual.

## Core doctrinal idea
The Kālī cycle shows consciousness as a process of emission, retention, erosion, withdrawal, devouring, sorting, sensory collapse, intellectual collapse, cosmic incineration, and final absolute still fire.

## The 12 Kālīs represented
1. Sṛṣṭikālī — emission / creation
2. Raktakālī — retention / saturation
3. Sthitināśakālī — undoing stable standing
4. Yamayayokālī — unmanifest potential
5. Saṃhārakālī — withdrawing the ego
6. Mṛtyukālī — devouring death / time
7. Bhadrakālī — spiritual sorting
8. Mārtaṇḍakālī — dissolving the senses
9. Paramārkakālī — dissolving the cosmic intellect
10. Kālāgnirudrakālī — burning the cosmic canvas
11. Mahākālakālī — Great Time
12. Mahābhairavaghoracaṇḍakālī — the Absolute as unmoving fire

## Visual rules
- This is not a generic goddess icon pack.
- Avoid anthropomorphic deity portraiture as the main explanatory strategy.
- Show process: projection, holding, collapse, sorting, burning, stilling.
- Keep the cycle dark, intense, and transformative.
- The last scene should feel motionless but not dead.

## Style family
- Dark parchment and furnace-light
- Blood crimson, ember orange, gold light, ash grey, indigo smoke
- Circles, wheels, flame-crowns, severing lines, burn fronts, sorting channels
- Less temple / geometry, more process / destruction / concentration

## New motifs introduced
- furnace emission spokes
- blood retention rings
- severed standing-canopies
- latent dark seed
- contracting ego arcs
- devouring flame wheel
- sorting channels
- sensory recollection paths
- collapsing intellect lattice
- burning canvas sweep
- abstract Great Time wheel
- unmoving fire seal

## Guardrails
- Do not present the cycle as mere annihilation; it is a structured transformation of consciousness.
- Do not equate the Kālīs with random chaos.
- Avoid reducing the cycle to external apocalypse; it is also cognitive and contemplative.
- The final absolute is terrifying and still, not simply explosive.

## Reuse strategy
- kc01–kc02: creation, emission, intensification
- kc03–kc06: collapse, withdrawal, death, devouring
- kc07–kc09: sorting, sensory dissolution, intellectual breakdown
- kc10–kc12: incineration, Great Time, final seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Kālīcakra / 12 Kālīs Pack

## Inheritance
This pack inherits the project’s diagrammatic clarity and contemplative pacing but turns the emotional temperature radically darker.

## Kālī differentiation
Where the 36 Tattvas pack emphasized parchment cosmography, bindu, lotuses, and structural manifestation, the Kālīcakra pack emphasizes:
- devouring cycles
- emission and re-absorption
- flame crowns and furnace light
- ash, smoke, and charred texture
- severing lines and burn fronts
- sorting channels and collapsing frameworks

## New motifs added
1. furnace emission spokes
2. blood-saturation rings
3. falling canopy layers
4. latent dark seed
5. contraction arcs
6. devouring fire wheel
7. sorting grid / channels
8. sensory return paths
9. collapsing lattice
10. burn-sweep canvas
11. Great Time wheel
12. unmoving fire seal

## New relationships added
- emission → saturation
- stability → collapse
- manifest field → latent seed
- egoic holding → inward withdrawal
- sensory dispersion → recollection
- cosmic canvas → incineration
- cyclical movement → motionless absolute fire

## New material vocabulary
- charcoal vellum
- ash grain
- ember / furnace glow
- blood crimson saturation
- smoke ribbons
- charred canvas edge

## Deprecated clichés
- generic goddess portrait montage
- flat wheel only
- random skull / gore aesthetics without structural meaning

## Distinct closing seal
The closing seal is an **unmoving fire seal**: a stationary central flame encircled by the residues of the full cycle.

## Recommendation for next packs
The next Tantrāloka structural packs could now branch into:
- Pañcakṛtya as a fivefold continuous loop
- Mātṛkā / Parāparā-vāk as a linguistic condensation engine
- Ṣaḍadhvan as the sixfold grand blueprint
- Avasthās and the five voids as state-transition architecture
- Kāmākalā / the three bindus as a seed-triangle generator
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The 12 Kālīs of the Kālīcakra Pack

Included files:
- kalicakra_12_kalis_animation.mp4
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
The script is resume-safe: it skips already-rendered frames and clips.
'''
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'kalicakra_12_kalis_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'kalicakra_12_kalis_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['kalicakra_12_kalis_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    combined = ROOT / 'kalicakra_12_kalis_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
