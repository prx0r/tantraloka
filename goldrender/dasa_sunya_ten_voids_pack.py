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
SEED = 11111

DEEP_VOID = (16, 18, 24)
WARM_DARK = (24, 22, 20)
DARK_UMBER = (32, 28, 24)
DARK_INDIGO = (22, 24, 36)
UMBER = (82, 66, 52)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
SILVER = (198, 206, 224)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
CRIMSON = (154, 44, 58)
ROSE = (196, 104, 130)
TEAL = (92, 146, 148)
TEAL_LIGHT = (148, 186, 190)
INDIGO = (68, 78, 136)
VIOLET = (120, 104, 168)
LAVENDER = (168, 158, 200)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)
CORAL = (204, 108, 100)
EARTH = (136, 106, 74)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)


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
    if a == b:
        return 1.0 if x >= b else 0.0
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
    d.rectangle((28, 28, W-28, H-28), outline=rgba(GOLD, 110), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 75), width=1)
    for x, y in [(70, 70), (W-70, 70), (70, H-70), (W-70, H-70)]:
        draw_rosette(d, x, y, 22, CRIMSON, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(15, 17, 22, 200), outline=rgba(GOLD, 60), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def dust(im, seed, n=55):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(40, W-40)); y = float(rng.uniform(40, H-40))
        r = float(rng.uniform(0.8, 2.0))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0, 1))
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(c, int(rng.uniform(20, 60))))
    im.alpha_composite(ov)


def void_ground(seed, bg, glow_col, intensity=0.8):
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
    base -= np.clip((dx*dx+dy*dy)*16, 0, 24)[..., None]
    if glow_col:
        g = np.exp(-(((xx-W*0.48)/(W*0.26))**2 + ((yy-H*0.38)/(H*0.22))**2)*2.6)
        for i in range(3):
            base[..., i] += g * glow_col[i] * 0.035
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def draw_voided_ring(d, cx, cy, r, col, void_frac=0.0, width=2):
    a_start = math.pi * void_frac * 0.5
    a_end = 2*math.pi - math.pi * void_frac * 0.5
    pts = arc_points(cx, cy, r, r*0.62, a_start, a_end, 60)
    if len(pts) > 1:
        d.line(pts, fill=rgba(col, 200), width=width)


def draw_voided_mandala(d, cx, cy, n_layers, t, base_r, cols, void_prog):
    for i in range(n_layers):
        r = base_r - i * (base_r // n_layers)
        vf = clamp(void_prog * 1.5 - i * 0.12)
        draw_voided_ring(d, cx, cy, r, cols[i % len(cols)], vf, 2 if i < n_layers//2 else 1)


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


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(void_ground(fs, DEEP_VOID, GOLD, 0.6), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    n = 10
    cols = [GOLD, SILVER, TEAL, INDIGO, VIOLET, ROSE, CORAL, GOLD_LIGHT, LAVENDER, WHITE]
    labels = ['1','2','3','4','5','6','7','8','9','10']
    prog = smoothstep(0.05, 0.85, t)
    for i in range(n):
        p = clamp(prog * 1.3 - i * 0.06)
        if p <= 0: continue
        r = 40 + i * 18
        draw_voided_ring(d, cx, cy, r, cols[i], 1-p*0.6, 2 if i%2==0 else 1)
        d.ellipse((cx-r*0.15, cy-r*0.15, cx+r*0.15, cy+r*0.15), outline=rgba(cols[i], 100), width=1)
        if i % 3 == 0:
            d.text((cx+r+22, cy-6), f'śūnya {i+1}', font=TINY_FONT, fill=cols[i])
    draw_glow(im, (cx, cy), 18, GOLD_LIGHT, 100, 14)
    d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=rgba(WHITE, 220), outline=rgba(GOLD, 200), width=1)
    d.text((640, 480), 'ten voids — progressive emptying of objectivity', font=SUB_FONT, fill=MIST, anchor='mm')
    d.text((640, 498), 'each ring = one level of dissolution', font=TINY_FONT, fill=SLATE, anchor='mm')


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(void_ground(fs, DARK_INDIGO, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    prog = ease_in_out(t)
    r = 140
    draw_voided_ring(d, cx, cy, r, GOLD, 1-prog, 3)
    d.ellipse((cx-r*0.85, cy-r*0.52, cx+r*0.85, cy+r*0.52), outline=rgba(GOLD_LIGHT, 80), width=1)
    d.ellipse((cx-r*0.5, cy-r*0.3, cx+r*0.5, cy+r*0.3), outline=rgba(GOLD, 120), width=1)
    draw_glow(im, (cx, cy), 40, GOLD_LIGHT, int(80*prog), 25)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(WHITE, int(200*prog)))
    d.text((cx, cy+60), 'nonbeing = consciousness', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx, cy+86), 'yat nāśūnyaṁ tat śūnyam', font=DEVA_SMALL, fill=GOLD, anchor='mm')
    d.text((640, 500), 'the void is not absence — it is the plenitude of awareness', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(void_ground(fs, WARM_DARK, (EARTH[0], EARTH[1], EARTH[2]), 0.6), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    prog = ease_in_out(t)
    side = 180
    for i in range(4):
        x0 = cx - side/2 + (1 if i%2==0 else 0)*2
        y0 = cy - side/2 + (1 if i>1 else 0)*2
        x1 = cx + side/2 - (1 if i%2==0 else 0)*2
        y1 = cy + side/2 - (1 if i>1 else 0)*2
        d.rectangle((x0, y0, x1, y1), outline=rgba(mix(EARTH, GOLD, i/4), 180), width=2)
    for i in range(8):
        a = i*2*math.pi/8
        x = cx + math.cos(a)*side*0.65
        y = cy + math.sin(a)*side*0.65
        d.ellipse((x-14, y-14, x+14, y+14), outline=rgba(mix(EARTH, GOLD_LIGHT, i/8), 160), width=2)
    void_r = lerp(10, 70, prog)
    draw_glow(im, (cx, cy), int(void_r+10), GOLD_LIGHT, int(100*prog), 20)
    d.ellipse((cx-void_r, cy-void_r, cx+void_r, cy+void_r), fill=rgba((16, 18, 24), 200))
    d.ellipse((cx-void_r-4, cy-void_r-4, cx+void_r+4, cy+void_r+4), outline=rgba(GOLD, int(200*prog)), width=2)
    d.text((cx, cy), 'viṣaya', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, 200), anchor='mm')
    d.text((620, 470), 'gross objectivity dissolves into the void', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((620, 490), 'the outer world empties into inner light', font=TINY_FONT, fill=SLATE, anchor='mm')


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(void_ground(fs, WARM_DARK, CORAL, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    prog = smoothstep(0.05, 0.9, t)
    sense_cols = [CORAL, ROSE, GOLD, TEAL, INDIGO]
    sense_names = ['hearing', 'touch', 'sight', 'taste', 'smell']
    for i in range(5):
        p = clamp(prog * 1.3 - i * 0.12)
        if p <= 0: continue
        a = -math.pi/2 + i*2*math.pi/5
        x = cx + math.cos(a)*110
        y = cy + math.sin(a)*110*0.62
        r = 28 + 6*math.sin(t*math.pi + i)
        draw_glow(im, (int(x), int(y)), int(r*0.5), sense_cols[i], int(60*p), 12)
        d.ellipse((x-r, y-r, x+r, y+r), outline=rgba(sense_cols[i], int(190*p)), width=2)
        d.ellipse((x-r*0.4, y-r*0.4, x+r*0.4, y+r*0.4), fill=rgba(DEEP_VOID, int(150*p)))
        d.text((x, y+40), sense_names[i], font=TINY_FONT, fill=rgba(sense_cols[i], int(200*p)), anchor='mm')
    draw_glow(im, (cx, cy), 30, GOLD_LIGHT, int(60*prog), 16)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(DEEP_VOID, 200), outline=rgba(WHITE, 150), width=1)
    d.text((640, 490), 'the senses empty — experience loses its channels', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(void_ground(fs, DEEP_VOID, TEAL, 0.6), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    prog = ease_in_out(t)
    n_branches = 8
    for i in range(n_branches):
        p = clamp(prog * 1.2 - i * 0.08)
        if p <= 0: continue
        a = i*2*math.pi/n_branches
        pts = bezier(
            (cx, cy),
            (cx+math.cos(a)*40, cy+math.sin(a)*25),
            (cx+math.cos(a)*100, cy+math.sin(a)*60),
            (cx+math.cos(a)*160, cy+math.sin(a)*100),
            70
        )
        reveal = partial_polyline(pts, p)
        if len(reveal) > 1:
            draw_line_glow(im, reveal, mix(TEAL, SILVER, i/n_branches), 2, 80, 5)
        x = cx + math.cos(a)*160
        y = cy + math.sin(a)*100
        d.ellipse((x-4, y-4, x+4, y+4), fill=rgba(mix(TEAL, SILVER, i/n_branches), 180))
    void_r = lerp(10, 50, prog)
    draw_glow(im, (cx, cy), int(void_r+8), GOLD_LIGHT, int(80*prog), 15)
    d.ellipse((cx-void_r, cy-void_r, cx+void_r, cy+void_r), fill=rgba(DEEP_VOID, 220))
    d.ellipse((cx-void_r-3, cy-void_r-3, cx+void_r+3, cy+void_r+3), outline=rgba(GOLD, int(200*prog)), width=2)
    d.text((cx, cy), 'manas', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, 200), anchor='mm')
    d.text((640, 490), "the mind's branches emanate from an empty center", font=SUB_FONT, fill=MIST, anchor='mm')


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(void_ground(fs, DEEP_VOID, CRIMSON, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 260
    prog = ease_in_out(t)
    r = 130
    thick = lerp(8, 2, prog)
    d.ellipse((cx-r-8, cy-int(r*0.62)-8, cx+r+8, cy+int(r*0.62)+8), outline=rgba(CRIMSON, 80), width=1)
    d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(CRIMSON, int(220-100*prog)), width=int(thick))
    for i in range(6):
        a = i*2*math.pi/6 + t*0.05
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        d.line((cx, cy, x, y), fill=rgba(CRIMSON, int(100-80*prog)), width=1)
    inner_r = lerp(80, 120, prog)
    draw_glow(im, (cx, cy), 35, GOLD_LIGHT, int(100*prog), 18)
    d.ellipse((cx-inner_r, cy-inner_r*0.62, cx+inner_r, cy+inner_r*0.62), outline=rgba(GOLD, int(180*prog)), width=2)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=rgba(DEEP_VOID, 200), outline=rgba(GOLD_LIGHT, int(200*prog)), width=1)
    d.text((cx, cy), 'ahaṅkāra', font=DEVA_SMALL, fill=rgba(GOLD_LIGHT, 200), anchor='mm')
    d.text((740, 220), 'the ego-ring thins until', font=SMALL_FONT, fill=CRIMSON, anchor='lm')
    d.text((740, 244), 'it is transparent —', font=SMALL_FONT, fill=CRIMSON, anchor='lm')
    d.text((740, 268), 'the boundary was a gate', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='lm')
    d.text((640, 498), 'ego-void: the boundary of self dissolves into the center', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(void_ground(fs, DEEP_INDIGO, SILVER, 0.4), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 270
    prog = ease_in_out(t)
    for i in range(8):
        p = clamp(prog * 1.2 - i * 0.08)
        if p <= 0: continue
        r = 30 + i*22
        col = mix(INDIGO, SILVER, i/8)
        a_start = math.pi * (1-p*0.4) * 0.3
        a_end = 2*math.pi - math.pi*(1-p*0.4)*0.3
        pts = arc_points(cx, cy, r, r*0.62, a_start, a_end, 50)
        if len(pts) > 1:
            d.line(pts, fill=rgba(col, int(200*p)), width=1)
    innermost = lerp(60, 10, prog)
    draw_glow(im, (cx, cy), 50, WHITE, int(120*prog), 25)
    d.ellipse((cx-innermost, cy-innermost*0.62, cx+innermost, cy+innermost*0.62),
              outline=rgba(WHITE, int(200*prog)), width=2)
    d.text((cx, cy), 'śūnyātiśūnya', font=DEVA_SMALL, fill=rgba(WHITE, 220), anchor='mm')
    d.text((cx, cy+40), 'void beyond voids', font=SMALL_FONT, fill=SILVER, anchor='mm')
    d.text((cx, cy+60), '= the Heart', font=TERM_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((640, 500), 'the supreme void: all voids merge into consciousness itself', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(void_ground(fs, DEEP_VOID, GOLD, 0.5), (0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    cols = [EARTH, CORAL, ROSE, TEAL, INDIGO, VIOLET, LAVENDER, GOLD, SILVER, WHITE]
    labels = ['bhūta','indriya','manas','ahaṅkāra','buddhi','prakṛti','puruṣa','mahā','para','sarva']
    prog = smoothstep(0.05, 0.9, t)
    for i in range(10):
        p = clamp(prog * 1.3 - i * 0.06)
        if p <= 0: continue
        r = 24 + i*20
        draw_voided_ring(d, cx, cy, r, cols[i], 1-p*0.3, 2)
        draw_glow(im, (cx, cy), int(r*0.3), cols[i], int(40*p*(1-i/10)), 12)
        if i % 2 == 0:
            d.text((cx+r+24, cy-6), labels[i], font=TINY_FONT, fill=rgba(cols[i], int(180*p)))
    draw_glow(im, (cx, cy), 28, WHITE, 140, 14)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((cx, cy), 'pūrṇa', font=DEVA_SMALL, fill=GOLD_LIGHT, anchor='mm')
    d.text((640, 498), 'ten voids — one fullness — consciousness emptying into itself', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('ds01', 'The Ten Voids', 'An overview of progressive emptiness.', 'Daśa-śūnya', 'Ten levels of emptying as consciousness withdraws from objectivity.', 'overview_rings', ['overview','voids','emptiness'], 'overview', 'ten nested voided rings', sc01),
    Scene('ds02', 'The Paradox', 'That which is not void is called the Void.', 'Śūnya-pāradoxa', 'The void is not absence — it is consciousness, the plenitude.', 'paradox_ring', ['paradox','consciousness','fullness'], 'paradox', 'luminous ring with empty center becoming full', sc02),
    Scene('ds03', 'Void of the Object', 'Gross objectivity dissolves into inner light.', 'Viṣaya-śūnya', 'The outer world of objects empties first.', 'object_void', ['object','gross','dissolution'], 'dissolution', 'square mandala with voided center', sc03),
    Scene('ds04', 'Void of the Senses', 'The five channels of experience lose their content.', 'Indriya-śūnya', 'Hearing, touch, sight, taste, smell — each sense-channel empties.', 'sense_void', ['senses','emptying','channels'], 'dissolution', 'five-petal lotus with voided petals', sc04),
    Scene('ds05', 'Void of the Mind', 'Thought branches from an empty center.', 'Manas-śūnya', "The mind's proliferations arise from and return to void.", 'mind_void', ['mind','branches','center'], 'dissolution', 'branching tree from void center', sc05),
    Scene('ds06', 'Void of the Ego', 'The boundary of self becomes transparent.', 'Ahaṅkāra-śūnya', 'The ring of I-making thins until it is seen as a gate.', 'ego_void', ['ego','boundary','transparent'], 'dissolution', 'thinning ego-ring with luminous center', sc06),
    Scene('ds07', 'The Void Beyond Voids', 'All voids merge into consciousness itself.', 'Śūnyātiśūnya', 'The supreme void is the Heart — full of all things.', 'supreme_void', ['supreme','void','heart'], 'culmination', 'dissolving nested rings with radiant center', sc07),
    Scene('ds08', 'The Daśa-śūnya Seal', 'Ten voids as one fullness.', 'Daśa-śūnya-cakra', 'All levels of emptying resolve into the single plenitude of awareness.', 'closing_seal', ['seal','fullness','emptiness'], 'seal', 'ten concentric rings around a pūrṇa center', sc08),
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
            im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            scene.draw_fn(im, t)
            dust(im, SEED + hash(scene.id)%10000 + i, 40)
            border(im)
            footer(im, scene.title, scene.subtitle, scene.term)
            im.convert('RGB').save(path, quality=95)
    out = SCENES_ROOT / f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size < 30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)], check=True)


def make_contact_sheet():
    thumbs = []
    for sc in SCENES:
        frame = FRAMES_ROOT / sc.id / f'frame_{int(NFRAMES*0.72):04d}.jpg'
        im = Image.open(frame).convert('RGB').resize((320,180), Image.Resampling.LANCZOS)
        thumbs.append(im)
    sheet = Image.new('RGB', (4*320, 2*180), color=DEEP_VOID)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Daśa-śūnya: The Ten Voids',
        'source_basis': 'Tantrāloka Āhnika 5.90–93ab (lines 3592–3625): the ten levels of emptiness experienced along the dvādaśānta axis, preparing the six blisses.',
        'style': {
            'family': 'voided yantra cosmography / mandala dissolution',
            'background': 'deep indigo-void field with warm glow',
            'ink': 'gold, silver, teal, violet',
            'accent': 'umber, crimson, rose, lavender',
            'materials': ['voided rings','partial mandalas','branching voids','thinning ego-rings','dissolving lotus petals']
        },
        'fps': FPS, 'resolution': [W, H], 'scene_duration_seconds': DURATION,
        'total_scenes': len(SCENES), 'total_duration_seconds': round(len(SCENES)*DURATION, 2),
        'scenes': [
            {'id': sc.id, 'title': sc.title, 'subtitle': sc.subtitle, 'mode': sc.mode,
             'summary': sc.summary, 'group': sc.group, 'technique_notes': sc.technique,
             'tags': sc.tags, 'duration_seconds': DURATION, 'output_filename': f'scenes/{sc.id}.mp4'}
            for sc in SCENES
        ]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    catalog = {
        'ids': [sc.id for sc in SCENES],
        'titles': {sc.id: sc.title for sc in SCENES},
        'modes': {sc.id: sc.mode for sc in SCENES},
        'theme_clusters': {
            'overview_and_paradox': ['ds01', 'ds02'],
            'dissolution': ['ds03', 'ds04', 'ds05', 'ds06'],
            'culmination_and_seal': ['ds07', 'ds08']
        },
        'reusability_notes': {
            'ds01': 'Use for the overview of the ten voids or progressive emptiness.',
            'ds02': 'Use for the paradox of void-as-fullness or the non-nihilistic void.',
            'ds03': 'Use for dissolution of objectivity, the gross level emptying.',
            'ds04': 'Use for sense-withdrawal, indriya-void, or the emptying of perception.',
            'ds05': 'Use for mind-void, thought dissolving, or the branching mind returning to center.',
            'ds06': 'Use for ego-dissolution, self-boundary thinning, or identity as gate.',
            'ds07': 'Use for the supreme void, void-beyond-voids, or the Heart as fullness.',
            'ds08': 'Use as a closing seal for the ten voids or emptiness-as-fullness cosmology.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Daśa-śūnya: The Ten Voids

## Aim
This pack visualizes the ten voids (daśaśūnya) of Tantrāloka Āhnika 5 — the progressive emptying of objectivity that prepares the six blisses.

## Doctrine
The ten voids are NOT nihilistic absences. They are the progressive self-emptying of objectivity, revealing the luminous plenitude of consciousness itself. Key verse: "That which is not void is called the Void" — the void is consciousness.

1. The void is the plenitude of consciousness, not nothingness
2. Each void marks the dissolution of a level of objectivity
3. The voids correspond to stations along the dvādaśānta axis
4. They prepare the six blisses — each bliss transcends a level of void
5. Śūnyātiśūnya (void beyond voids) = the Heart itself
6. The supreme void is "full of all things"

## Visual rules
- Use voided mandala forms: geometric structures with empty/luminous centers
- The void is shown as an absence OF form that IS luminous — not black but golden
- Labels (Sanskrit terms, numbers) explain what is being voided
- Each scene shows a different level of emptying
- The border and footer follow the standard pack format exactly
- Dust particles create atmospheric depth

## New motifs
- ten nested voided rings overview
- luminous paradox ring (nonbeing = consciousness)
- square mandala with void center (object-void)
- five-petal lotus with voided petals (sense-void)
- branching tree from void center (mind-void)
- thinning ego-ring with luminous gate (ego-void)
- dissolving nested rings culmination
- ten-colored convergence seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Daśa-śūnya Pack

## Differentiation
This pack introduces voided yantra/mandala forms — geometric structures that are systematically emptied at their center. No other pack uses partial/voided geometry as its primary motif.

## New symbols
1. ten nested voided rings (overview ladder)
2. paradox ring — luminous boundary with empty fullness
3. square mandala with voided center (earth/object)
4. five-petal lotus with dissolving petals (senses)
5. branching tree emanating from void (mind)
6. thinning ring with luminous center (ego as gate)
7. dissolving nested rings (void beyond voids)
8. ten-colored convergence seal with pūrṇa center

## Material vocabulary
- deep indigo-void field
- gold paradox-light
- umber/earth object-void
- coral/rose sense-void
- teal/silver mind-void
- crimson ego-boundary
- white supreme-void radiance
- ten colors in closing seal

## Distinct closing seal
Ten concentric rings in progressive colors (earth → sense → mind → ego → intellect → nature → person → great → supreme → all) converging on a central "pūrṇa" (fullness) bindu.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — Daśa-śūnya: The Ten Voids Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total runtime: {len(SCENES)*DURATION/60:.2f} min

The ten voids are progressive levels of emptying that reveal the plenitude of consciousness. "That which is not void is called the Void."

Run:
```bash
python render_pack.py
```
Resume-safe.
'''
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'dasa_sunya_ten_voids_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'dasa_sunya_ten_voids_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['dasa_sunya_ten_voids_animation.mp4','contact_sheet.jpg',
                     'scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md',
                     'STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name, arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):
            zf.write(mp4, arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, flush=True)
        render_scene(sc)
    concat_file = ROOT / 'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT / 'dasa_sunya_ten_voids_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
