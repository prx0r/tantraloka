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
SEED = 10101

NIGHT = (20, 22, 30)
GRAPHITE = (32, 35, 46)
DEEP_VIOLET = (52, 46, 80)
VIOLET = (100, 88, 140)
LAVENDER = (170, 158, 195)
SILVER = (192, 196, 210)
MIST = (164, 172, 192)
PEARL = (243, 241, 235)
WHITE = (252, 250, 246)
GOLD = (205, 163, 82)
GOLD_LIGHT = (245, 214, 138)
CORAL = (198, 94, 90)
TEAL = (92, 144, 148)
UMBER = (82, 66, 52)
BLACK = (14, 12, 16)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
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


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1-t) ** 3


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t * t * (3 - 2 * t)


def rgba(c, a=255):
    return (*c[:3], int(a))


def veil_ground(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0, 1, (42, 76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*4.2 + fine[..., None]*1.15
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2)/(W/2)
    dy = (yy - H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy)*20, 0, 28)
    base -= vign[..., None]
    glow = np.exp(-(((xx-W/2)/(W*0.28))**2 + ((yy-H*0.40)/(H*0.26))**2)*2.8)
    for i, v in enumerate((DEEP_VIOLET[0], DEEP_VIOLET[1], DEEP_VIOLET[2])):
        base[..., i] += glow * (v/255*18)
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


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


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42, y-r*0.42, x+r*0.42, y+r*0.42), fill=rgba(outer, 145), outline=rgba(inner, 180), width=1)
    draw.ellipse((cx-r*0.42, cy-r*0.42, cx+r*0.42, cy+r*0.42), fill=rgba(inner, 120), outline=rgba(outer, 220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(VIOLET, 105), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 80), width=1)
    for x, y in [(70, 70), (W-70, 70), (70, H-70), (W-70, H-70)]:
        draw_rosette(d, x, y, 22, LAVENDER, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(18, 20, 28, 200), outline=rgba(VIOLET, 60), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def bezier(p0, p1, p2, p3, n=100):
    pts = []
    for i in range(n):
        t = i/(n-1); u = 1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts


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


def arc_points(cx, cy, rx, ry, a0, a1, n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx, cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang = math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s = 12*scale
    draw.polygon([p1,
                  (p1[0]-math.cos(ang-0.5)*s, p1[1]-math.sin(ang-0.5)*s),
                  (p1[0]-math.cos(ang+0.5)*s, p1[1]-math.sin(ang+0.5)*s)], fill=rgba(color, 230))


def dust(im, seed, n=65):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 2.1))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0, 1))
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(c, int(rng.uniform(22, 72))))
    im.alpha_composite(ov)


def draw_moire_grid(d, cx, cy, angle, spacing, n_lines, col, alpha=80, t=0.0):
    for i in range(-n_lines, n_lines+1):
        a = angle + t * 0.015
        dist = i * spacing
        dx = math.cos(a + math.pi/2) * dist
        dy = math.sin(a + math.pi/2) * dist
        x0 = cx + dx - math.cos(a)*500
        y0 = cy + dy - math.sin(a)*500
        x1 = cx + dx + math.cos(a)*500
        y1 = cy + dy + math.sin(a)*500
        d.line((x0, y0, x1, y1), fill=rgba(col, alpha), width=1)


def draw_veil_ribbon(im, cx, cy, width, height, progress, col=SILVER):
    pts = []
    for i in range(80):
        u = i/79
        x = cx - width/2 + u * width
        y = cy - height/2 + u * height
        undulation = 30 * math.sin(u * math.pi * 3) * math.sin(math.pi * u)
        x += undulation * 0.3
        y += undulation * 0.5
        pts.append((x, y))
    reveal = partial_polyline(pts, progress)
    if len(reveal) > 1:
        draw_line_glow(im, reveal, col, 4, 120, 8)
        return reveal[-1]
    return None


def draw_figure_ground(d, cx, cy, r, t):
    for i in range(12):
        a = i*2*math.pi/12 + t*0.08
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.68
        rm = 18
        d.arc((x-rm, y-18, x+rm, y+18), 0, 360, fill=rgba(SILVER, 160), width=2)
        d.ellipse((x-6, y-6, x+6, y+6), fill=rgba(WHITE, 200))


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
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_moire_grid(d, cx, cy, -math.pi/6, 22, 18, SILVER, 70, t)
    draw_moire_grid(d, cx, cy, math.pi/6, 22, 18, GOLD_LIGHT, 70, t)
    draw_glow(im, (cx, cy), 60, GOLD_LIGHT, 110, 18)
    d.ellipse((cx-18, cy-18, cx+18, cy+18), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((cx, cy+48), 'one power', font=TERM_FONT, fill=GOLD, anchor='mm')
    d.text((cx, cy+80), 'two directions', font=SMALL_FONT, fill=MIST, anchor='mm')
    d.text((640, 510), 'tirodhāna-anugraha: what conceals and what reveals are one act', font=SUB_FONT, fill=MIST, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_glow(im, (cx, cy), 80, VIOLET, 90, 20)
    d.ellipse((cx-160, cy-110, cx+160, cy+110), outline=rgba(VIOLET, 140), width=2)
    d.ellipse((cx-100, cy-70, cx+100, cy+70), outline=rgba(LAVENDER, 110), width=2)
    veil_progress = ease_in_out(t)
    for i in range(12):
        a = i*2*math.pi/12
        x = cx + math.cos(a)*150
        y = cy + math.sin(a)*100
        length = 80 * veil_progress
        d.line((x, y, x + math.cos(a)*length, y + math.sin(a)*length),
               fill=rgba(mix(VIOLET, LAVENDER, i/12), 80+60*veil_progress), width=2)
    draw_glow(im, (cx, cy), 30, GOLD_LIGHT, 80, 10)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(BLACK, 200), outline=rgba(GOLD, 160), width=1)
    d.text((640, 510), 'the veil descends: concealment makes the world-appearance possible', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    aperture = lerp(4, 160, ease_in_out(t))
    d.rounded_rectangle((cx-200, cy-130, cx+200, cy+130), radius=30, outline=rgba(VIOLET, 170), fill=rgba((35,32,55),80), width=3)
    d.rounded_rectangle((cx-aperture, cy-int(aperture*0.68),
                         cx+aperture, cy+int(aperture*0.68)),
                        radius=18, outline=rgba(GOLD_LIGHT, 220), fill=rgba((255,230,170), 40), width=3)
    for i in range(16):
        a = -math.pi/2 + i*2*math.pi/16
        x = cx + math.cos(a)*(aperture+20)
        y = cy + math.sin(a)*(aperture*0.68+14)
        d.line((cx + math.cos(a)*aperture, cy + math.sin(a)*aperture*0.68,
                x, y), fill=rgba(GOLD, 130), width=2)
    draw_glow(im, (cx, cy), 40, GOLD_LIGHT, 120, 12)
    d.ellipse((cx-14, cy-14, cx+14, cy+14), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'the aperture: the same substance that blocks also frames and opens', font=SUB_FONT, fill=MIST, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 290
    r = 170
    phase = ease_in_out(t)
    d.ellipse((cx-r, cy-r*0.7, cx+r, cy+r*0.7), outline=rgba(SILVER, 150), width=2)
    for i, a in enumerate(np.linspace(0, 2*math.pi, 10, endpoint=False)):
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.7
        if phase < 0.5:
            d.ellipse((x-12, y-12, x+12, y+12), fill=rgba(VIOLET, 190), outline=rgba(LAVENDER, 140), width=1)
            d.ellipse((x-6, y-6, x+6, y+6), fill=rgba(BLACK, 200))
        else:
            d.ellipse((x-12, y-12, x+12, y+12), fill=rgba(GOLD_LIGHT, 190), outline=rgba(GOLD, 140), width=1)
            d.ellipse((x-5, y-5, x+5, y+5), fill=rgba(WHITE, 220))
        d.line((cx, cy, x, y), fill=rgba(mix(VIOLET, GOLD_LIGHT, phase), 80), width=1)
    draw_glow(im, (cx, cy), 40, mix(VIOLET, GOLD_LIGHT, phase), 110, 14)
    d.ellipse((cx-14, cy-14, cx+14, cy+14), fill=rgba(mix(BLACK, WHITE, phase), 255), outline=rgba(GOLD, 200), width=2)
    d.text((640, 510), 'the same form seen as obstacle or as opening — a shift in perception', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 275
    draw_moire_grid(d, cx, cy, -math.pi/7, 20, 15, VIOLET, 60, t)
    draw_moire_grid(d, cx, cy, math.pi/7, 20, 15, GOLD_LIGHT, 60, t)
    rent = smoothstep(0.1, 0.9, t)
    rent_w = lerp(8, 280, rent)
    draw_glow(im, (cx, cy), 70, GOLD_LIGHT, 130, 22)
    d.rounded_rectangle((cx-rent_w/2, cy-100, cx+rent_w/2, cy+100),
                        radius=rent_w/6, outline=rgba(GOLD, 220), fill=rgba((255,235,180), 55), width=3)
    for i in range(14):
        a = -math.pi/2 + i*2*math.pi/14
        x = cx + math.cos(a)*180
        y = cy + math.sin(a)*115
        if abs(math.cos(a)) < 0.3 and rent > 0.3:
            continue
        d.line((x, y, cx + math.cos(a)*(rent_w/2+10), cy + math.sin(a)*90),
               fill=rgba(mix(VIOLET, SILVER, i/14), 130), width=1)
    d.ellipse((cx-18, cy-18, cx+18, cy+18), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'the glimpse: grace as a rent in the fabric of concealment', font=SUB_FONT, fill=MIST, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    breath = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
    r_max = 200
    r = 30 + r_max * breath
    d.ellipse((cx-r, cy-r*0.7, cx+r, cy+r*0.7), outline=rgba(mix(VIOLET, GOLD_LIGHT, breath), 160), width=3)
    r2 = 30 + r_max * (1 - breath)
    d.ellipse((cx-r2, cy-r2*0.7, cx+r2, cy+r2*0.7), outline=rgba(mix(GOLD_LIGHT, VIOLET, breath), 130), width=2)
    for i in range(8):
        a = i*2*math.pi/8 + t*0.2
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.7
        d.ellipse((x-5, y-5, x+5, y+5), fill=rgba(mix(GOLD, VIOLET, breath), 180))
    draw_glow(im, (cx, cy), 30, GOLD_LIGHT, 100, 10)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((640, 510), 'the rhythm of veiling and unveiling: one power breathing', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    for i in range(6):
        r = 40 + i*32
        col = mix(VIOLET, GOLD_LIGHT, i/6)
        d.ellipse((cx-r, cy-r*0.66, cx+r, cy+r*0.66), outline=rgba(col, 120-10*i), width=2)
    dissolve = ease_in_out(t)
    for i in range(18):
        a = i*2*math.pi/18
        r = 170
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.66
        seg_len = lerp(80, 0, dissolve)
        off = int(30 * (1-dissolve))
        d.line((x, y, x+math.cos(a)*seg_len, y+math.sin(a)*seg_len),
               fill=rgba(mix(VIOLET, GOLD_LIGHT, i/18), int(180*(1-dissolve+0.2))), width=2)
    draw_glow(im, (cx, cy), 50, GOLD_LIGHT, 130, 16)
    d.ellipse((cx-18, cy-18, cx+18, cy+18), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'the veil dissolves: what was hidden was never elsewhere', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    draw_moire_grid(d, cx, cy, -math.pi/8, 24, 16, VIOLET, 55, t)
    draw_moire_grid(d, cx, cy, math.pi/8, 24, 16, GOLD_LIGHT, 55, t)
    for r, col in [(220, VIOLET), (170, LAVENDER), (120, GOLD), (70, GOLD_LIGHT)]:
        d.ellipse((cx-r, cy-r*0.7, cx+r, cy+r*0.7), outline=rgba(col, 120), width=2)
    for i in range(20):
        a = -math.pi/2 + i*2*math.pi/20 + t*0.05
        x = cx + math.cos(a)*195
        y = cy + math.sin(a)*130
        d.ellipse((x-4, y-4, x+4, y+4), fill=rgba(mix(VIOLET, GOLD, (i%10)/10), 170))
    draw_glow(im, (cx, cy), 65, GOLD_LIGHT, 140, 20)
    d.ellipse((cx-22, cy-22, cx+22, cy+22), fill=rgba(WHITE, 255), outline=rgba(GOLD, 225), width=2)
    d.text((cx, cy), 'तिरोधान-अनुग्रह', font=DEVA_SMALL, fill=GOLD, anchor='mm')
    d.text((640, 510), 'the seal: one power, two faces — the veil is the face of the beloved', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('tg01', 'One Power, Two Faces', 'The same act conceals and reveals.', 'Tirodhāna–Anugraha', 'Concealment and grace are not opposites but directions of one power.', 'overview_moire', ['overview','concealment','grace'], 'overview', 'double moiré grid with central bindu', sc01),
    Scene('tg02', 'The Veil Descends', 'Concealment as the condition for world-appearance.', 'Tirodhāna', 'The first movement: the source is hidden so manifestation can appear.', 'veil_descent', ['concealment','veil','descent'], 'concealment', 'concentric veiling rays', sc02),
    Scene('tg03', 'The Aperture', 'What blocks also frames — the veil creates the opening.', 'Chiḍra', 'The same structure that obscures also creates the possibility of vision.', 'aperture_frame', ['aperture','frame','opening'], 'concealment', 'rounded frame with expanding aperture', sc03),
    Scene('tg04', 'Figure and Ground', 'The same form seen as obstacle or opening.', 'Rūpa–ādhāra', 'A shift in perception transforms a barrier into a gateway.', 'figure_ground', ['figure','ground','oscillation'], 'threshold', 'radial figure-ground flip', sc04),
    Scene('tg05', 'The Glimpse', 'Grace as a rent in the fabric of concealment.', 'Anugraha-darśana', 'A sudden opening reveals what was always present but hidden.', 'grace_rent', ['grace','glimpse','rent'], 'grace', 'moire grid with golden rent', sc05),
    Scene('tg06', 'The Rhythm', 'The pulse of veiling and unveiling.', 'Chanda', 'Concealment and revelation alternate as the rhythm of consciousness.', 'veil_rhythm', ['rhythm','pulse','alternation'], 'rhythm', 'breathing concentric rings', sc06),
    Scene('tg07', 'No Departure', 'What was behind the veil was never elsewhere.', 'Akhaṇḍa', 'When the veil dissolves, no separate hidden content is found.', 'veil_dissolve', ['dissolve','identity','presence'], 'identity', 'dissolving veil arcs', sc07),
    Scene('tg08', 'The Tirodhāna-Anugraha Seal', 'The veil recognized as the face of the beloved.', 'Tirodhāna-anugraha-cakra', 'The closing seal: one power, two faces, one consciousness.', 'closing_seal', ['seal','veil','face'], 'seal', 'moire cosmogram with dual-grid seal', sc08),
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
            im = veil_ground(SEED + hash(scene.id)%10000 + i)
            border(im)
            dust(im, SEED+i, 55)
            scene.draw_fn(im, t)
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
    sheet = Image.new('RGB', (4*320, 2*180), color=NIGHT)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Tirodhāna-Anugraha: Concealment and Grace',
        'source_basis': 'Tantrāloka pañcakṛtya: tirodhāna (concealment) and anugraha (grace) as two directions of one divine power.',
        'style': {
            'family': 'veil-aperture contemplative field / figure-ground oscillation',
            'background': 'deep violet night',
            'ink': 'silver and lavender',
            'accent': 'violet, gold-light, coral, teal',
            'materials': ['moire grids','veil ribbons','aperture frames','figure-ground rings','glimpse rents']
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
            'overview_and_concealment': ['tg01', 'tg02'],
            'aperture_and_figure_ground': ['tg03', 'tg04'],
            'grace_and_rhythm': ['tg05', 'tg06'],
            'dissolution_and_seal': ['tg07', 'tg08']
        },
        'reusability_notes': {
            'tg01': 'Use for the dual-aspect power of concealment and grace, or moiré visual language.',
            'tg02': 'Use for the descent of the veil, the necessity of concealment for manifestation.',
            'tg03': 'Use for aperture, threshold, or the frame created by limitation.',
            'tg04': 'Use for figure-ground reversal, perceptual flip, or ambiguous form.',
            'tg05': 'Use for the sudden glimpse, grace breaking through, or epistemic opening.',
            'tg06': 'Use for the rhythmic alternation of presence and absence.',
            'tg07': 'Use for the dissolution of the veil or the recognition of non-separation.',
            'tg08': 'Use as a closing seal for concealment/grace or veil cosmology.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tirodhāna-Anugraha

## Aim
This pack visualizes concealment (tirodhāna) and grace (anugraha) as two movements of the same power — the fourth and fifth acts of the pañcakṛtya.

## Core doctrine
1. **One power, two directions** — the act that conceals is the same act that reveals.
2. **The veil** — concealment is not a mistake; it is the condition for world-appearance.
3. **The aperture** — the same substance that blocks also creates the opening.
4. **Figure-ground** — a shift in perception transforms barrier into gateway.
5. **The glimpse** — grace as a rent in the fabric of concealment.
6. **No departure** — what was hidden was never elsewhere.

## Visual rules
- Use moiré interference as the master pattern: two grids whose interaction creates a shimmer.
- The veil must be a dynamic, living structure, not a static curtain.
- The aperture is created by the same material that blocks — show this.
- Figure-ground oscillation: the same form must be readable two ways.
- The closing seal should integrate both faces (violet concealment + gold grace) into one pattern.

## New motifs
- double-grid moiré interference
- radiating veiling rays
- aperture frame with expanding opening
- figure-ground radial flip
- golden rent in grid-field
- breathing concentric pulse
- dissolving veil arcs
- dual-grid cosmogram seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Tirodhāna-Anugraha Pack

## Differentiation
This pack introduces moiré grid interference and figure-ground oscillation — visual techniques not used in any earlier pack.

## New symbols
1. double-grid moiré field — two superimposed line sets
2. radiating veiling rays — concealment as outward projection
3. aperture frame — the containing boundary that also opens
4. figure-ground radial flip — the same points read as obstacle or opening
5. golden rent in grid — grace breaking through the moiré field
6. breathing concentric pulse — the rhythm of veiling and unveiling
7. dissolving veil arcs — the veil thins and disappears
8. dual-grid cosmogram — both grids resolved around one center

## Material vocabulary
- deep violet night field
- lavender and silver grid lines
- gold rent-light
- violet concealment tones
- white aperture radiance
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — Tirodhāna-Anugraha: Concealment and Grace Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total runtime: {len(SCENES)*DURATION/60:.2f} min

Run:
```bash
python render_pack.py
```
Resume-safe.
'''
    (ROOT/'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'tirodhana_anugraha_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'tirodhana_anugraha_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['tirodhana_anugraha_animation.mp4','contact_sheet.jpg',
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
    combined = ROOT / 'tirodhana_anugraha_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
