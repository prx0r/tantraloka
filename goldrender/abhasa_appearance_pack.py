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
SEED = 80808

WARM_VOID = (26, 24, 22)
DEEP_WARM = (42, 36, 30)
UMBER = (82, 66, 52)
EARTH = (142, 112, 76)
PARCHMENT = (244, 239, 228)
PARCHMENT_LIGHT = (250, 247, 239)
IVORY = (252, 250, 245)
GOLD = (206, 164, 84)
GOLD_LIGHT = (245, 216, 141)
ROSE = (192, 110, 134)
TEAL = (96, 146, 148)
MIST = (170, 180, 194)
SLATE = (100, 114, 136)
HAZE = (220, 218, 212)
WHITE = (254, 252, 248)
BLACK = (16, 14, 12)

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


def abhasa_ground(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(WARM_VOID, dtype=np.float32)
    coarse = rng.normal(0, 1, (44, 78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*3.5 + fine[..., None]*1.0
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2)/(W/2)
    dy = (yy - H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy)*16, 0, 24)
    base -= vign[..., None]
    g1 = np.exp(-(((xx-W*0.35)/(W*0.28))**2 + ((yy-H*0.34)/(H*0.22))**2)*2.2)
    g2 = np.exp(-(((xx-W*0.65)/(W*0.24))**2 + ((yy-H*0.52)/(H*0.20))**2)*2.4)
    for i in range(3):
        base[..., i] += g1*(8 if i<2 else 20) + g2*(6 if i<2 else 14)
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
    d.rectangle((28, 28, W-28, H-28), outline=rgba(SLATE, 100), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 75), width=1)
    for x, y in [(70, 70), (W-70, 70), (70, H-70), (W-70, H-70)]:
        draw_rosette(d, x, y, 22, ROSE, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(24, 22, 20, 210), outline=rgba(SLATE, 55), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=IVORY)
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


def dust(im, seed, n=80):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 2.0))
        c = mix(HAZE, GOLD_LIGHT, rng.uniform(0, 1))
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(c, int(rng.uniform(18, 60))))
    im.alpha_composite(ov)


def wash(draw, pts, col, alpha=60):
    """Draw a translucent filled polygon — a 'wash' like watercolor."""
    if len(pts) > 2:
        draw.polygon(pts, fill=rgba(col, alpha))


def dream_form(d, cx, cy, t, scale=1.0, col=GOLD_LIGHT):
    """A translucent, dream-like form that shimmers at the edges."""
    n = 20
    outer = []
    inner = []
    for i in range(n):
        a = i*2*math.pi/n
        r = 60 + 30*math.sin(i*1.7 + t*math.pi) + 20*math.sin(i*0.5 + t*0.7)
        outer.append((cx + math.cos(a)*r*scale, cy + math.sin(a)*r*0.6*scale))
        inner.append((cx + math.cos(a)*r*0.5*scale, cy + math.sin(a)*r*0.3*scale))
    wash(d, outer, col, 35)
    if len(outer) > 1:
        d.line(outer, fill=rgba(col, 140), width=2)
    if len(inner) > 1:
        d.line(inner, fill=rgba(mix(col, WHITE, .5), 90), width=1)
    return outer


def draw_reflection(d, im, cx, cy, t, progress, w=200, h=120, col=GOLD_LIGHT):
    """A city-in-a-mirror reflection effect."""
    pts = []
    for i in range(18):
        u = i/17
        x = cx - w/2 + u * w
        y = cy - h/2 + u * h + 20*math.sin(u*math.pi*3 + t*0.5)
        pts.append((x, y))
    reveal = partial_polyline(pts, progress)
    if len(reveal) > 1:
        draw_line_glow(im, reveal, col, 2, 80, 6)
    for i in range(7):
        yy = cy - h/2 + 16 + i*18
        seg = []
        for j in range(12):
            u = j/11
            x = cx - w/2 + u * w
            y = yy + 6*math.sin(u*math.pi*2 + t*0.7 + i*0.5)
            seg.append((x, y))
        s = partial_polyline(seg, progress)
        if len(s) > 1:
            draw_line_glow(im, s, mix(col, TEAL, i/7), 1, 50, 4)


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
    cx, cy = W/2, 275
    dream_form(d, cx, cy, t, 1.6, GOLD_LIGHT)
    dream_form(d, cx-80, cy+40, t*0.7, 0.8, ROSE)
    dream_form(d, cx+90, cy-30, t*0.5, 0.6, TEAL)
    draw_glow(im, (cx, cy), 50, GOLD_LIGHT, 120, 18)
    d.ellipse((cx-16, cy-16, cx+16, cy+16), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.text((640, 510), 'ābhāsa: the world appears within consciousness like forms in a mirror', font=SUB_FONT, fill=MIST, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_glow(im, (cx, cy), 80, GOLD_LIGHT, 100, 24)
    d.rounded_rectangle((cx-140, cy-90, cx+140, cy+90), radius=30, outline=rgba(GOLD, 120), fill=rgba((40,36,32),30), width=2)
    surf_progress = ease_in_out(t)
    for i in range(14):
        yy = cy - 70 + i*12
        w = 100 + 30*math.sin(i*0.7 + t*math.pi)
        alpha = int(60 * surf_progress * (1 - abs(i-7)/7))
        d.line((cx-w*0.5*surf_progress, yy, cx+w*0.5*surf_progress, yy),
               fill=rgba(mix(GOLD_LIGHT, HAZE, i/14), alpha), width=1)
    draw_glow(im, (cx, cy), 24, GOLD, 90, 8)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=rgba(WHITE, 255))
    d.text((640, 510), 'the mirror ground: a still surface capable of reflecting all forms', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_glow(im, (cx, cy), 60, TEAL, 70, 20)
    rings = 8
    for i in range(rings):
        r = 20 + i*24
        prog = smoothstep(i*0.05, 0.7+i*0.03, t)
        if prog <= 0: continue
        a = t * 2 * math.pi * 0.3 + i * 0.4
        rx = r + 12 * math.sin(a)
        ry = r * 0.6 + 8 * math.sin(a*0.7)
        d.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), outline=rgba(mix(TEAL, GOLD_LIGHT, i/rings), int(140*prog)), width=2)
    d.ellipse((cx-8, cy-8, cx+8, cy+8), fill=rgba(WHITE, 220), outline=rgba(TEAL, 180), width=1)
    d.text((640, 510), 'the first ripple: appearance stirs in the undifferentiated ground', font=SUB_FONT, fill=MIST, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    prog = ease_out_cubic(t)
    forms = [
        ((cx, cy), 1.0, GOLD_LIGHT),
        ((cx-160, cy+40), 0.6, ROSE),
        ((cx+170, cy-20), 0.55, TEAL),
        ((cx-100, cy-90), 0.4, HAZE),
        ((cx+130, cy+80), 0.45, mix(GOLD, EARTH, .5)),
    ]
    for (fx, fy), scale, col in forms:
        p = smoothstep(0.05, 0.8, prog * (1 + 0.3*(fx-cx)/200))
        if p <= 0: continue
        r = 50 * scale
        glow_r = 30
        draw_glow(im, (int(fx), int(fy)), int(glow_r), col, 80, 12)
        d.ellipse((fx-r, fy-r*0.66, fx+r, fy+r*0.66), outline=rgba(col, int(180*p)), width=2)
        d.ellipse((fx-r*0.5, fy-r*0.33, fx+r*0.5, fy+r*0.33), fill=rgba(col, int(30*p)))
    draw_glow(im, (cx, cy), 40, GOLD_LIGHT, 100, 14)
    d.ellipse((cx-12, cy-12, cx+12, cy+12), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((640, 510), 'forms arise from the formless: discrete appearances emerge in the field', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_glow(im, (cx, cy), 70, GOLD_LIGHT, 90, 22)
    dream_form(d, cx, cy, t, 1.3, GOLD_LIGHT)
    dream_form(d, cx-40, cy+20, t*0.8, 0.9, ROSE)
    dream_form(d, cx+50, cy-30, t*0.6, 0.7, TEAL)
    dissolve = ease_in_out(t)
    for i in range(16):
        a = i*2*math.pi/16 + t*0.04
        r = 140 + 20*math.sin(i*1.3 + t*0.5)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        alpha = int(180 * (1-0.5*dissolve) * (0.5+0.5*math.sin(i+t)))
        d.ellipse((x-4, y-4, x+4, y+4), fill=rgba(mix(GOLD_LIGHT, HAZE, dissolve), alpha))
    d.ellipse((cx-14, cy-14, cx+14, cy+14), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((640, 510), 'the dream-like quality: forms appear firmly yet shimmer at the edges', font=SUB_FONT, fill=MIST, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    draw_reflection(d, im, cx, cy, t, ease_in_out(t), 260, 140, GOLD_LIGHT)
    draw_glow(im, (cx, 280), 50, GOLD_LIGHT, 110, 16)
    d.ellipse((cx-16, cy-16, cx+16, cy+16), fill=rgba(WHITE, 255), outline=rgba(GOLD, 220), width=2)
    d.rounded_rectangle((cx-50, 372, cx+50, 410), radius=10, outline=rgba(HAZE, 100), fill=rgba((30,28,26),50), width=1)
    d.text((640, 394), 'yathā darpaṇa', font=DEVA_SMALL, fill=HAZE, anchor='mm')
    d.text((640, 510), 'the world shines in consciousness like a city reflected in a mirror', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    dream_form(d, cx, cy, t, 1.5, GOLD_LIGHT)
    transparentize = ease_in_out(t)
    inner_r = 40 + 60 * (1-transparentize)
    draw_glow(im, (cx, cy), int(20 + 40*transparentize), WHITE, 130, 18)
    for i in range(8):
        a = i*2*math.pi/8
        r = 120
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        seg = partial_polyline([(cx, cy), (x, y)], transparentize)
        if len(seg) > 1:
            draw_line_glow(im, seg, mix(GOLD, WHITE, transparentize), 2, 80, 5)
    d.ellipse((cx-inner_r, cy-inner_r*0.68, cx+inner_r, cy+inner_r*0.68),
              outline=rgba(WHITE, int(180*transparentize)), width=3)
    d.ellipse((cx-12, cy-12, cx+12, cy+12), fill=rgba(WHITE, 255), outline=rgba(GOLD, 200), width=2)
    d.text((640, 510), 'seeing through: the world-form is revealed as transparent to consciousness', font=SUB_FONT, fill=MIST, anchor='mm')


def sc08(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 285
    draw_glow(im, (cx, cy), 70, GOLD_LIGHT, 120, 22)
    dream_form(d, cx, cy, t, 1.8, GOLD_LIGHT)
    dream_form(d, cx-100, cy+30, t*0.6, 0.7, ROSE)
    dream_form(d, cx+110, cy-20, t*0.5, 0.6, TEAL)
    dream_form(d, cx-50, cy-70, t*0.4, 0.4, HAZE)
    dream_form(d, cx+60, cy+60, t*0.7, 0.5, mix(GOLD, EARTH, .5))
    for i in range(24):
        a = -math.pi/2 + i*2*math.pi/24 + t*0.04
        r = 200 + 20*math.sin(i*2.3 + t*math.pi)
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*r*0.62
        d.ellipse((x-3, y-3, x+3, y+3), fill=rgba(mix(GOLD, HAZE, (i%8)/8), 150))
    d.ellipse((cx-20, cy-20, cx+20, cy+20), fill=rgba(WHITE, 255), outline=rgba(GOLD, 225), width=2)
    d.text((cx, cy), 'आभास', font=DEVA_MED, fill=GOLD, anchor='mm')
    d.text((640, 510), 'the seal of appearance: all forms floating in self-luminous consciousness', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('ab01', 'The Field of Appearance', 'Forms emerge within consciousness like dawn from night.', 'Ābhāsa-kṣetra', 'The world appears as a shimmering within awareness, not as a separate substance.', 'overview_dream', ['overview','appearance','consciousness'], 'overview', 'layered dream forms', sc01),
    Scene('ab02', 'The Mirror Ground', 'The substrate of all appearance — clear, still, luminous.', 'Ādāra-darpaṇa', 'Consciousness as the mirror-surface in which all forms appear.', 'mirror_surface', ['mirror','ground','substrate'], 'ground', 'still reflective surface emerging', sc02),
    Scene('ab03', 'The First Ripple', 'Subtle vibration stirs the undifferentiated field.', 'Prathama-spanda', 'The first movement of appearance: a tremor in the mirror.', 'first_ripple', ['ripple','vibration','emergence'], 'emergence', 'expanding concentric wave rings', sc03),
    Scene('ab04', 'Forms Arise', 'Discrete shapes emerge from the formless field.', 'Rūpa-samutpāda', 'Differentiated appearances condense like islands rising from mist.', 'form_emergence', ['form','emergence','differentiation'], 'differentiation', 'multiple translucent forms emerging', sc04),
    Scene('ab05', 'The Dream', 'Appearances seem solid yet shimmer at their edges.', 'Svapna-upamā', 'The world has the quality of a dream: vivid but not substantial.', 'dream_quality', ['dream','shimmer','quality'], 'quality', 'dream forms with dissolving edges', sc05),
    Scene('ab06', 'The Shining', 'The world appears within consciousness like a reflection.', 'Pratibimba', 'The city-in-a-mirror: all forms are a shining within awareness.', 'reflection_world', ['reflection','shining','mirror'], 'reflection', 'city-in-mirror reflection lines', sc06),
    Scene('ab07', 'Transparency', 'Form is seen through — not destroyed but known as luminous.', 'Paiśārdhya', 'Seeing through the appearance reveals it as transparent to consciousness.', 'seeing_through', ['transparency','seeing through','luminosity'], 'transparency', 'dream form with transparent center', sc07),
    Scene('ab08', 'The Ābhāsa Seal', 'All forms floating as one self-luminous appearance.', 'Ābhāsa-cakra', 'The closing seal: manifestation as the single act of consciousness appearing to itself.', 'closing_seal', ['seal','appearance','self-luminosity'], 'seal', 'multi-dream cosmogram seal', sc08),
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
            im = abhasa_ground(SEED + hash(scene.id)%10000 + i)
            border(im)
            dust(im, SEED+i, 65)
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
    sheet = Image.new('RGB', (4*320, 2*180), color=WARM_VOID)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Ābhāsa: The Appearance of the World in Consciousness',
        'source_basis': 'Trikā ontology of ābhāsa: the world exists as a shining-forth within consciousness, not as independent substance.',
        'style': {
            'family': 'luminous emergence / dream cosmography',
            'background': 'warm void with double dawn-glow',
            'ink': 'umber and haze',
            'accent': 'gold-light, rose, teal, earth',
            'materials': ['dream forms','mirror surfaces','ripple rings','translucent washes','city-in-mirror reflections']
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
            'overview_and_ground': ['ab01', 'ab02'],
            'emergence_and_differentiation': ['ab03', 'ab04'],
            'dream_and_reflection': ['ab05', 'ab06'],
            'transparency_and_seal': ['ab07', 'ab08']
        },
        'reusability_notes': {
            'ab01': 'Use for the doctrine of appearance, or the shimmering quality of manifestation.',
            'ab02': 'Use for consciousness as mirror-ground, or the substrate of all appearance.',
            'ab03': 'Use for the first vibration, the stir of manifestation, the primordial ripple.',
            'ab04': 'Use for the emergence of differentiated forms from the undifferentiated field.',
            'ab05': 'Use for the dream-like quality of experience, or the subtle insubstantiality of forms.',
            'ab06': 'Use for the reflection metaphor, or the city-in-a-mirror analogy for the world.',
            'ab07': 'Use for transparency, seeing-through, or the form known as luminous appearance.',
            'ab08': 'Use as a closing seal for appearance-consciousness nonduality.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Ābhāsa: The Appearance of the World

## Aim
This pack visualizes the Trikā ontology of ābhāsa: the world is not a separate substance (dravya) but a shining-forth within consciousness.

## Core doctrine
1. **The mirror ground** — consciousness is the substrate of all appearance
2. **The first ripple** — a subtle vibration stirs the undifferentiated field
3. **Forms arise** — discrete appearances emerge like islands from mist
4. **The dream quality** — forms seem solid but shimmer at their edges
5. **The reflection** — the world is like a city reflected in a mirror
6. **Transparency** — seeing through the form reveals it as consciousness

## Visual rules
- The pack should feel like dawn emerging from night — luminous, warm, gradual.
- Forms should never be fully solid; they are translucent, shimmering, dissolving.
- Use soft washes rather than hard geometric boundaries.
- The mirror metaphor: a horizontal surface that is also a window.
- The dream quality: vividness without substantiality.

## New motifs
- layered dream forms (organic, shimmering shapes)
- mirror surface emergence
- concentric ripple rings
- translucent forms emerging from void
- city-in-mirror reflection lines
- transparent center revelation
- multi-dream cosmogram seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Ābhāsa Pack

## Differentiation
This pack introduces an organic, dream-like, watercolor aesthetic that breaks from the geometric and diagrammatic precision of all earlier packs.

## New symbols
1. layered dream forms — soft-edged, shimmering organic shapes
2. mirror surface emergence — a reflective plane appearing from dark
3. concentric ripple rings — vibration spreading in the substrate
4. translucent form clusters — multiple overlapping emergent shapes
5. shimmer-edge dream fields — forms with dissolving boundaries
6. city-in-mirror reflection — architectural metaphor as soft linework
7. transparent center — a form whose core becomes luminous
8. multi-dream cosmogram — overlapping translucent forms in one field

## Material vocabulary
- warm void background with double dawn-glow
- gold-light primary emergence
- rose secondary forms
- teal tertiary fields
- haze for dream edges
- earth for grounded forms

## Distinct closing seal
An overlapping arrangement of translucent dream forms around a central golden ābhāsa — the many appearances as one luminous field.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — Ābhāsa: The Appearance of the World in Consciousness Pack

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
    combined = ROOT / 'abhasa_appearance_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'abhasa_appearance_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['abhasa_appearance_animation.mp4','contact_sheet.jpg',
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
    combined = ROOT / 'abhasa_appearance_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
