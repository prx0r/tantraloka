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
DURATION = 4.8
NFRAMES = int(FPS * DURATION)
SEED = 60606

# Split cosmography palette
PARCHMENT = (241, 236, 226)
PARCHMENT_LIGHT = (248, 245, 238)
IVORY = (252, 249, 244)
INK = (36, 38, 45)
UMBER = (87, 72, 58)
GOLD = (203, 162, 88)
GOLD_LIGHT = (242, 212, 140)
INDIGO = (68, 80, 138)
DEEP_INDIGO = (46, 57, 98)
ROSE = (187, 109, 136)
TEAL = (95, 145, 148)
GREEN = (103, 149, 111)
EARTH = (144, 116, 80)
SLATE = (110, 124, 146)
SMOKE = (176, 178, 186)
BLUE_GREY = (132, 145, 165)
WHITE = (251, 249, 244)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 22)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)

SUBJECTIVE = [('Varṇa', INDIGO), ('Mantra', ROSE), ('Pada', TEAL)]
OBJECTIVE = [('Kalā', GREEN), ('Tattva', EARTH), ('Bhuvana', GOLD)]


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b-a) * clamp(t)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi*t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1-t)**3


def smoothstep(a,b,x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t*t*(3-2*t)


def rgba(c,a=255):
    return (*c[:3], int(a))


def parchment(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(PARCHMENT, dtype=np.float32)
    coarse = rng.normal(0,1,(42,76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.15
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*5,0,14)
    base -= vign[...,None]*0.8
    # two side halos
    left = np.exp(-(((xx-W*0.28)/(W*0.18))**2 + ((yy-H*0.38)/(H*0.24))**2)*2.4)
    right = np.exp(-(((xx-W*0.72)/(W*0.18))**2 + ((yy-H*0.38)/(H*0.24))**2)*2.4)
    for i in range(3):
        base[...,i] += left * (18 if i==2 else 8)
        base[...,i] += right * (12 if i!=2 else 6)
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W,H), (0,0,0,0))


def draw_glow(im, xy, radius, color, alpha=150, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x,y = xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius), fill=rgba(color, alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im, pts, color, width=3, alpha=150, blur=8):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1,width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+70)), width=width, joint='curve')


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a=2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,150), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,125), outline=rgba(outer,220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(UMBER, 122), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD, 90), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, ROSE, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(247,243,235,214), outline=rgba(UMBER,75), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=INK)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=UMBER)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=DEEP_INDIGO)


def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
        y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
        pts.append((x,y))
    return pts


def partial_polyline(points, amount):
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


def arc_points(cx,cy,rx,ry,a0,a1,n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx, cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang = math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s = 12*scale
    pts=[p1,(p1[0]-math.cos(ang-0.5)*s,p1[1]-math.sin(ang-0.5)*s),(p1[0]-math.cos(ang+0.5)*s,p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts, fill=rgba(color,230))


def dust(im, seed, n=52):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c = mix(SMOKE, GOLD_LIGHT, rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c, int(rng.uniform(28,80))))
    im.alpha_composite(ov)


def draw_node(draw, x, y, r, outline, fill=None, label=None, font=None, textfill=None):
    draw.ellipse((x-r,y-r,x+r,y+r), outline=rgba(outline,220), fill=fill or rgba((255,255,255),30), width=2)
    if label:
        draw.text((x,y), label, font=font or SMALL_FONT, fill=textfill or IVORY, anchor='mm')


def draw_pillar(draw, x, y0, y1, col):
    draw.rounded_rectangle((x-16,y0,x+16,y1), radius=10, outline=rgba(col,170), fill=rgba(mix(PARCHMENT_LIGHT,col,.08),60), width=2)
    for yy in np.linspace(y0+24,y1-24,6):
        draw.line((x-11,yy,x+11,yy), fill=rgba(col,90), width=1)


def draw_world_orbit(draw, cx, cy, r, col, n=8):
    draw.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(col,150), width=2)
    for i in range(n):
        a = i*2*math.pi/n
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*(r*0.68)
        draw.ellipse((x-4,y-4,x+4,y+4), fill=rgba(col,190))


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


# --- Scene functions ---

def sc01(im, t):
    d = ImageDraw.Draw(im)
    cx = W/2
    # top source
    draw_glow(im, (cx, 110), 44, GOLD_LIGHT, 130, 14)
    d.ellipse((cx-14,96,cx+14,124), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((cx, 68), 'ANUTTARA', font=TERM_FONT, fill=GOLD, anchor='mm')
    # split branch
    ptsl = partial_polyline(bezier((cx,128),(cx-20,160),(380,155),(300,195),80), smoothstep(0.03,0.75,t))
    ptsr = partial_polyline(bezier((cx,128),(cx+20,160),(900,155),(980,195),80), smoothstep(0.03,0.75,t))
    if len(ptsl)>1:
        draw_line_glow(im, ptsl, INDIGO, 3, 110, 6)
        draw_arrowhead(d, ptsl[-2], ptsl[-1], INDIGO, 0.9)
    if len(ptsr)>1:
        draw_line_glow(im, ptsr, GREEN, 3, 110, 6)
        draw_arrowhead(d, ptsr[-2], ptsr[-1], GREEN, 0.9)
    d.text((292, 165), 'Vācaka', font=TERM_FONT, fill=INDIGO, anchor='mm')
    d.text((988, 165), 'Vācya', font=TERM_FONT, fill=GREEN, anchor='mm')
    ys = [240, 328, 418]
    for (lab,col),y in zip(SUBJECTIVE, ys):
        draw_node(d, 300, y, 34, col, rgba(mix(PARCHMENT_LIGHT,col,.08),70), None)
        d.text((300,y), lab, font=SMALL_FONT, fill=col, anchor='mm')
    for (lab,col),y in zip(OBJECTIVE, ys):
        draw_node(d, 980, y, 34, col, rgba(mix(PARCHMENT_LIGHT,col,.08),70), None)
        d.text((980,y), lab, font=SMALL_FONT, fill=col, anchor='mm')
    for i,y in enumerate(ys[:-1]):
        for x,col in [(300, SUBJECTIVE[i][1]), (980, OBJECTIVE[i][1])]:
            pts = partial_polyline(bezier((x, y+34), (x, y+56), (x, ys[i+1]-56), (x, ys[i+1]-34), 60), smoothstep(0.12+i*0.1,0.88+i*0.04,t))
            if len(pts)>1:
                draw_line_glow(im, pts, col, 3, 100, 5)
                draw_arrowhead(d, pts[-2], pts[-1], col, 0.8)
    d.line((640, 180, 640, 470), fill=rgba(SMOKE,100), width=2)
    d.text((640, 507), 'subjective paths of speech    |    objective paths of cosmos', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # phonemic wheel
    draw_glow(im,(cx,cy),42,INDIGO,110,12)
    d.ellipse((cx-16,cy-16,cx+16,cy+16), fill=rgba(WHITE,255), outline=rgba(INDIGO,220), width=2)
    letters = ['अ','आ','इ','उ','ऋ','ए','ओ','क','च','ट','त','प']
    n = len(letters)
    for i,ch in enumerate(letters):
        a = -math.pi/2 + i*2*math.pi/n + t*0.08
        x = cx + math.cos(a)*205
        y = cy + math.sin(a)*142
        d.text((x,y), ch, font=DEVA_MED, fill=INDIGO, anchor='mm')
        draw_line_glow(im, [(cx,cy),(x,y)], mix(INDIGO, GOLD_LIGHT, i/n), 2, 70, 5)
    for r in [82,142,205]:
        d.ellipse((cx-r,cy-r*0.7,cx+r,cy+r*0.7), outline=rgba(mix(INDIGO,SMOKE,r/205), 110), width=2)
    d.text((640, 505), 'the path of phonemic possibility', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    mantras = ['ॐ', 'ह्रीं', 'श्रीं', 'क्लीं', 'हं', 'सौः']
    cols = [ROSE, ROSE, GOLD, TEAL, INDIGO, GREEN]
    for i,m in enumerate(mantras):
        a = -math.pi/2 + i*2*math.pi/6
        x = cx + math.cos(a)*145
        y = cy + math.sin(a)*98
        d.ellipse((x-34,y-34,x+34,y+34), outline=rgba(cols[i], 180), fill=rgba(mix(PARCHMENT_LIGHT,cols[i],.06),70), width=2)
        d.text((x,y), m, font=DEVA_MED, fill=cols[i], anchor='mm')
        pts = partial_polyline(bezier((cx,cy),(cx+math.cos(a)*44,cy+math.sin(a)*28),(x-12*math.cos(a), y-10*math.sin(a)),(x,y),80), smoothstep(0.05+i*0.04,0.8+i*0.03,t))
        if len(pts)>1: draw_line_glow(im, pts, cols[i], 3, 100, 6)
    draw_glow(im,(cx,cy),48,ROSE,95,14)
    d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=rgba(WHITE,255), outline=rgba(ROSE,220), width=2)
    d.text((640, 505), 'phonemes gather as effective vibratory formulas', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    # words / syntax pathways
    boxes = [
        (150, 218, 180, 78, 'नाम', INDIGO),
        (390, 218, 200, 78, 'क्रिया', TEAL),
        (660, 218, 210, 78, 'वाक्य', ROSE),
        (955, 218, 170, 78, 'अर्थ', GOLD),
    ]
    for x,y,w,h,label,col in boxes:
        d.rounded_rectangle((x,y,x+w,y+h), radius=16, outline=rgba(col, 185), fill=rgba(mix(PARCHMENT_LIGHT,col,.05),70), width=2)
        d.text((x+w/2,y+h/2), label, font=DEVA_MED, fill=col, anchor='mm')
    for i in range(len(boxes)-1):
        p0 = (boxes[i][0]+boxes[i][2], boxes[i][1]+boxes[i][3]/2)
        p1 = (boxes[i+1][0], boxes[i+1][1]+boxes[i+1][3]/2)
        pts = partial_polyline(bezier(p0,(p0[0]+40,p0[1]-10),(p1[0]-40,p1[1]+10),p1,80), smoothstep(0.05+i*0.12,0.82+i*0.08,t))
        if len(pts)>1:
            draw_line_glow(im, pts, mix(boxes[i][5], boxes[i+1][5], .5), 3, 110, 6)
            draw_arrowhead(d, pts[-2], pts[-1], mix(boxes[i][5], boxes[i+1][5], .5), 0.9)
    d.text((640, 505), 'phonemic power becomes structured word and meaning', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    x0 = 270
    names = ['kalā', 'vidyā', 'rāga', 'kāla', 'niyati']
    cols = [GREEN, TEAL, ROSE, BLUE_GREY, EARTH]
    for i,(name,col) in enumerate(zip(names, cols)):
        y = 170 + i*58
        rx = 58 + i*34
        ry = 16 + i*6
        d.arc((x0-rx, y-ry, x0+rx, y+ry), 180, 360, fill=rgba(col, 185), width=3)
        d.arc((x0-rx, y-ry, x0+rx, y+ry), 0, 180, fill=rgba(mix(col,WHITE,.5), 95), width=2)
        d.text((460, y-6), name, font=TERM_FONT, fill=col)
    # enclosure frame on right
    d.rounded_rectangle((700, 170, 1040, 420), radius=20, outline=rgba(EARTH,170), fill=rgba(mix(PARCHMENT_LIGHT,EARTH,.04),70), width=2)
    for i in range(3):
        d.rounded_rectangle((740+i*44, 205+i*24, 1000-i*44, 385-i*24), radius=14, outline=rgba(mix(GREEN,EARTH,i/3), 120), width=2)
    d.text((870, 290), 'five enclosures', font=TERM_FONT, fill=EARTH, anchor='mm')
    d.text((640, 505), 'the objective side begins with bounded capacities', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, top = W/2, 120
    # condensed tattva ladder
    levels = [1,2,2,6,3,5,5]
    idx = 1
    y_positions = np.linspace(160, 450, len(levels))
    for li,(count,y) in enumerate(zip(levels, y_positions)):
        if count == 1:
            xs=[cx]
        else:
            span=min(360, 46*count)
            xs=np.linspace(cx-span/2, cx+span/2, count)
        for x in xs:
            col = mix(INDIGO, EARTH, li/(len(levels)-1))
            d.ellipse((x-12,y-12,x+12,y+12), outline=rgba(col, 200), fill=rgba((248,246,239),120), width=2)
            d.text((x,y+1), str(idx), font=TINY_FONT, fill=INK, anchor='mm')
            idx += 1
        if li>0:
            prev_count=levels[li-1]; py=y_positions[li-1]
            pxs=[cx] if prev_count==1 else np.linspace(cx-min(360,46*prev_count)/2, cx+min(360,46*prev_count)/2, prev_count)
            for px in pxs:
                for x in xs:
                    if abs(px-x) < 110 or prev_count==1:
                        d.line((px,py+12,x,y-12), fill=rgba(SMOKE,60), width=1)
    d.text((1048, 190), '36 levels', font=TERM_FONT, fill=EARTH)
    d.text((1048, 225), 'from pure to gross', font=SUB_FONT, fill=UMBER)
    d.text((640, 505), 'the path of ontological levels condensing into world', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # concentric world spheres / bhuvanas
    radii = [56, 96, 140, 188, 240]
    cols = [GOLD_LIGHT, GOLD, GREEN, TEAL, INDIGO]
    for r,col in zip(radii, cols):
        d.ellipse((cx-r, cy-r*0.72, cx+r, cy+r*0.72), outline=rgba(col, 155), width=2)
        for i in range(8):
            a = i*2*math.pi/8 + t*0.08*(1 if r%2==0 else -1)
            x = cx + math.cos(a)*r
            y = cy + math.sin(a)*(r*0.72)
            d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(col,190))
    draw_glow(im,(cx,cy),38,GOLD_LIGHT,120,12)
    d.ellipse((cx-14,cy-14,cx+14,cy+14), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((640, 505), 'the path of worlds as nested cosmic domains', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc08(im, t):
    d = ImageDraw.Draw(im)
    # mapping correspondences between left and right triads
    left_x, right_x = 320, 960
    ys = [180, 290, 400]
    for (lab,col),y in zip(SUBJECTIVE, ys):
        d.rounded_rectangle((left_x-88,y-34,left_x+88,y+34), radius=16, outline=rgba(col,185), fill=rgba(mix(PARCHMENT_LIGHT,col,.06),70), width=2)
        d.text((left_x,y), lab, font=TERM_FONT, fill=col, anchor='mm')
    for (lab,col),y in zip(OBJECTIVE, ys):
        d.rounded_rectangle((right_x-88,y-34,right_x+88,y+34), radius=16, outline=rgba(col,185), fill=rgba(mix(PARCHMENT_LIGHT,col,.06),70), width=2)
        d.text((right_x,y), lab, font=TERM_FONT, fill=col, anchor='mm')
    map_cols = [mix(INDIGO,GREEN,.5), mix(ROSE,EARTH,.5), mix(TEAL,GOLD,.5)]
    for i,y in enumerate(ys):
        pts = partial_polyline(bezier((left_x+90,y),(530,y-40+i*15),(750,y+40-i*15),(right_x-90,y),100), smoothstep(0.05+i*0.14,0.82+i*0.08,t))
        if len(pts)>1:
            draw_line_glow(im, pts, map_cols[i], 4, 130, 8)
            draw_arrowhead(d, pts[-2], pts[-1], map_cols[i], 0.9)
    draw_glow(im,(640, 115),30,GOLD_LIGHT,120,10)
    d.ellipse((626,101,654,129), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((640, 76), 'ANUTTARA', font=TERM_FONT, fill=GOLD, anchor='mm')
    d.text((640, 515), 'speech-paths and world-paths mirror one source', font=SUB_FONT, fill=UMBER, anchor='mm')


SCENES = [
    Scene('sd01', 'The Six Paths Overview', 'Anuttara unfolds into the two triads of expression and manifestation.', 'Ṣaḍadhvan', 'The six paths split into subjective and objective streams descending from the Absolute.', 'overview_split_tree', ['overview','split cosmos','six paths'], 'overview', 'split tree from Anuttara', sc01),
    Scene('sd02', 'Varṇa', 'The path of phonemes and atomic sound-units.', 'Varṇa', 'Letters and phonemic potentials form the first speech-path.', 'phoneme_wheel', ['speech','phonemes','varna'], 'speech', 'phonemic wheel', sc02),
    Scene('sd03', 'Mantra', 'The path of vibratory formulas and efficacious sound-bodies.', 'Mantra', 'Phonemic power gathers into mantric condensations.', 'mantra_orbits', ['speech','mantra','vibration'], 'speech', 'mantra constellation', sc03),
    Scene('sd04', 'Pada', 'The path of words, syntax, and articulated meaning.', 'Pada', 'Speech unfolds as ordered words and semantic structure.', 'word_chain', ['speech','words','meaning'], 'speech', 'word-box sequence', sc04),
    Scene('sd05', 'Kalā', 'The path of bounded capacities and enclosures.', 'Kalā', 'The objective stream begins in measured capacities and limitations.', 'enclosure_layers', ['objective','kala','enclosures'], 'object', 'five-enclosure frame', sc05),
    Scene('sd06', 'Tattva', 'The path of the thirty-six ontological levels.', 'Tattva', 'The cosmic hierarchy is ordered as a ladder of levels.', 'tattva_ladder', ['objective','tattvas','levels'], 'object', 'condensed 36-ladder', sc06),
    Scene('sd07', 'Bhuvana', 'The path of worlds and cosmic domains.', 'Bhuvana', 'Manifestation flowers into nested worlds or cosmic spheres.', 'world_spheres', ['objective','worlds','cosmos'], 'object', 'nested world orbits', sc07),
    Scene('sd08', 'The Correspondence Seal', 'Speech and cosmos mirror one another through a single source.', 'Vācaka–Vācya', 'The two triads correspond as expressive and expressed dimensions of one reality.', 'correspondence_map', ['seal','correspondence','mirror'], 'seal', 'triad-to-triad mapping', sc08),
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
            im = parchment(SEED + hash(scene.id)%10000 + i)
            border(im)
            dust(im, SEED+i, 46)
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
    sheet = Image.new('RGB', (4*320, 2*180), color=PARCHMENT)
    for idx,im in enumerate(thumbs):
        x=(idx%4)*320; y=(idx//4)*180
        sheet.paste(im,(x,y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project':'Tantrāloka — The Six Paths of Emanation (Ṣaḍadhvan)',
        'source_basis':'Conceptual mapping of the six paths supplied by the user from Tantrāloka Chapters 6–11.',
        'style': {
            'family':'bilateral cosmographic blueprint',
            'background':'pale parchment with dual halos',
            'ink':'indigo / umber',
            'accent':'indigo, rose, teal, green, earth, gold',
            'materials':['split-tree diagram','phonemic wheels','mantra orbits','word chain','tattva ladder','world orbits']
        },
        'fps': FPS,
        'resolution': [W,H],
        'scene_duration_seconds': DURATION,
        'total_scenes': len(SCENES),
        'total_duration_seconds': round(len(SCENES)*DURATION,2),
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
            } for sc in SCENES
        ]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    catalog = {
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id: sc.title for sc in SCENES},
        'modes':{sc.id: sc.mode for sc in SCENES},
        'theme_clusters':{
            'overview':['sd01'],
            'speech_paths':['sd02','sd03','sd04'],
            'objective_paths':['sd05','sd06','sd07'],
            'closing_correspondence':['sd08']
        },
        'reusability_notes':{
            'sd01':'Use to introduce the whole ṣaḍadhvan structure or the Vācaka/Vācya split.',
            'sd02':'Use for phonemic structure, alphabets, atomic speech-units, or sound architecture.',
            'sd03':'Use for mantra systems, vibratory formulas, or concentrated speech-power.',
            'sd04':'Use for words, syntax, semantic structures, or linguistic articulation.',
            'sd05':'Use for kalā, limitations, enclosures, or bounded capacity.',
            'sd06':'Use for the 36 tattvas, ontological hierarchy, or cosmological levels.',
            'sd07':'Use for worlds, cosmic domains, or nested spheres of manifestation.',
            'sd08':'Use as a closing seal for correspondence between speech and cosmos.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Ṣaḍadhvan

## Aim
This pack visualizes the **Six Paths of Emanation (Ṣaḍadhvan)** as a bilateral blueprint of reality.

## Textual orientation
The pack is based on the user-supplied structural summary: three subjective paths of speech (Vācakādhvan) and three objective paths of cosmic manifestation (Vācyādhvan), all descending from **Anuttara**.

## Core doctrinal structure represented
### Subjective / expressive side (Vācakādhvan)
1. **Varṇa** — phonemes / letters
2. **Mantra** — formulas / vibrations
3. **Pada** — words / syntactical forms

### Objective / expressed side (Vācyādhvan)
4. **Kalā** — bounded capacities / enclosures
5. **Tattva** — the thirty-six levels
6. **Bhuvana** — worlds / cosmic spheres

## Visual rules
- Always preserve the split structure: speech side vs world side.
- Keep **Anuttara** as the common source above both columns.
- The speech side should feel more linguistic, vibratory, and interior.
- The world side should feel more layered, architectural, and cosmological.
- The final seal should show correspondence rather than absolute separation.

## Style family
- pale bilateral blueprint on parchment
- indigo / rose / teal for the subjective side
- green / earth / gold for the objective side
- split trees, vertical ladders, and linking correspondence arcs

## New motifs introduced
- Anuttara split-tree overview
- phonemic wheel
- mantra constellation
- word / syntax chain
- five-enclosure frame
- condensed tattva ladder
- nested world spheres
- correspondence seal between triads

## Guardrails
- Do not collapse the six paths into a single flat list.
- Do not omit the expressive/objective distinction.
- Do not make the speech side purely grammatical or the world side purely physical; both remain cosmological.
- The pack should show structured parallels, not two unrelated halves.

## Reuse strategy
- sd01: full split overview
- sd02–sd04: speech-path triad
- sd05–sd07: objective-path triad
- sd08: correspondence seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Ṣaḍadhvan Pack

## Inheritance
This pack continues the contemplative manuscript-diagram language of the previous packs, but it becomes more bilateral, taxonomic, and architectonic.

## Ṣaḍadhvan differentiation
This pack emphasizes:
- two parallel columns or triads
- expressive vs expressed reality
- source branching into mirrored systems
- correspondence rather than simple sequence
- linguistic cosmology meeting world-cosmology

## New motifs added
1. split-tree overview from Anuttara
2. phonemic wheel
3. mantra constellation
4. syntactic word chain
5. five-enclosure frame
6. condensed tattva ladder
7. nested world spheres
8. triad-to-triad correspondence seal

## New relationships added
- Anuttara → subjective speech-paths
- Anuttara → objective world-paths
- phoneme → mantra → word
- kalā → tattva → bhuvana
- expressive side ↔ expressed side correspondence
- linguistic structure ↔ ontological structure

## New material vocabulary
- dual halo parchment field
- bilateral line architecture
- indigo / rose / teal speech-color logic
- green / earth / gold world-color logic
- linking mapping arcs

## Deprecated clichés
- flat six-item list with no structural polarity
- generic flowchart with no contemplative presence
- reducing the objective side to mere physical geography

## Distinct closing seal
The closing seal is a **Vācaka–Vācya correspondence map**, showing the two triads mirroring a single source.

## Recommendation for next packs
Strong next candidates:
- Avasthās & the five voids
- Three structural bindus / Kāmākalā
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The Six Paths of Emanation (Ṣaḍadhvan) Pack

Included files:
- sadadhvan_six_paths_animation.mp4
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
The script is resume-safe.
'''
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'sadadhvan_six_paths_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'sadadhvan_six_paths_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['sadadhvan_six_paths_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    combined = ROOT / 'sadadhvan_six_paths_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
