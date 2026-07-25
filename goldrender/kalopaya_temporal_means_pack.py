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
SEED = 33333

COSMIC_DARK = (8, 10, 16)
DEEP_SPACE = (12, 14, 22)
SPACE_BLUE = (18, 22, 36)
SILVER = (198, 206, 222)
GOLD = (206, 166, 88)
GOLD_LIGHT = (245, 216, 142)
TEAL = (92, 146, 148)
TEAL_LIGHT = (148, 186, 190)
VIOLET = (120, 104, 168)
LAVENDER = (172, 162, 208)
WHITE = (252, 250, 246)
CORAL = (200, 106, 98)
UMBER = (82, 66, 50)
SLATE = (100, 110, 132)
MIST = (164, 172, 192)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)


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


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(SILVER, 45), width=1)
    d.rectangle((36, 36, W-36, H-36), outline=rgba(SILVER, 22), width=1)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 100
    d.rounded_rectangle((120, y0, W-120, H-38), radius=12, fill=(8, 10, 16, 170), outline=rgba(SILVER, 25), width=1)
    d.text((W/2, y0+18), title, font=TITLE_FONT, fill=rgba(SILVER, 220), anchor='mm')
    d.text((W/2, y0+50), subtitle, font=SUB_FONT, fill=rgba(MIST, 160), anchor='mm')
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-130-tw, y0+22), term, font=TERM_FONT, fill=rgba(GOLD_LIGHT, 180))


def orbit_point(cx, cy, r, angle, squeeze=0.6):
    return (cx + r * math.cos(angle), cy + r * math.sin(angle) * squeeze)


def trail(im, cx, cy, r, speed, n, col, t, squeeze=0.6, width=2, alpha=100, blur=4):
    pts = []
    for i in range(n):
        a = i/(n-1) * 2 * math.pi + t * speed
        p = orbit_point(cx, cy, r, a, squeeze)
        pts.append(p)
    reveal = partial_polyline(pts, smoothstep(0.02, 0.92, t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, col, width, alpha, blur)


def epicycle(im, cx, cy, R, r, speed_ratio, t, col, n=180, squeeze=0.6, width=2):
    pts = []
    for i in range(n):
        u = i/(n-1)
        theta = u * 2 * math.pi
        x = cx + R * math.cos(theta) + r * math.cos(theta * speed_ratio + t * 0.15)
        y = (cy + R * math.sin(theta) + r * math.sin(theta * speed_ratio + t * 0.15)) * squeeze
        pts.append((x, y))
    reveal = partial_polyline(pts, smoothstep(0.03, 0.9, t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, col, width, 100, 5)


def precessing_ring(im, cx, cy, R, precess_rate, t, col, n=100, squeeze=0.6, width=2):
    pts = []
    pa = t * precess_rate
    for i in range(n):
        theta = i/(n-1) * 2 * math.pi
        x = cx + R * math.cos(theta) * math.cos(pa) - R * 0.2 * math.sin(theta) * math.sin(pa)
        y = cy + R * math.sin(theta) * squeeze
        x += 20 * math.sin(pa) * math.sin(theta)
        pts.append((x, y))
    reveal = partial_polyline(pts, smoothstep(0.04, 0.88, t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, col, width, 90, 6)


def star_dust(im, seed, t, n=120):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for i in range(n):
        x = float(rng.uniform(30, W-30))
        y = float(rng.uniform(30, H-30))
        dx = 8 * math.sin(t*0.3 + i*2.1)
        dy = 5 * math.cos(t*0.4 + i*1.7)
        r = float(rng.uniform(0.5, 1.8))
        a = int(rng.uniform(20, 60))
        d.ellipse((x+dx-r, y+dy-r, x+dx+r, y+dy+r), fill=rgba(WHITE, a))
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


def cosmic_ground(seed, nebula_col=None, intensity=1.0):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(COSMIC_DARK, dtype=np.float32)
    coarse = rng.normal(0, 1, (44, 78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*3.5*intensity + fine[..., None]*1.0*intensity
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx-W/2)/(W/2); dy = (yy-H/2)/(H/2)
    vign = np.clip((dx*dx+dy*dy)*20, 0, 28)
    base -= vign[..., None]
    if nebula_col:
        nebula = np.exp(-(((xx-W*0.45)/(W*0.32))**2 + ((yy-H*0.35)/(H*0.28))**2)*2.4)
        for i in range(3):
            base[..., i] += nebula * nebula_col[i] * 0.035
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def sc01(im, t):
    fs = SEED + int(t*9973) % 100000
    im.paste(cosmic_ground(fs, GOLD, 0.5), (0, 0))
    cx, cy = W/2, 320
    trail(im, cx, cy, 180, 0.4, 80, GOLD, t, 0.6, 3, 100, 5)
    trail(im, cx, cy, 120, -0.6, 60, SILVER, t, 0.6, 2, 80, 4)
    trail(im, cx, cy, 60, 0.9, 40, TEAL, t, 0.6, 2, 70, 4)
    a = t * 0.4
    for r, col in [(180, GOLD), (120, SILVER), (60, TEAL)]:
        p = orbit_point(cx, cy, r, a * (1 if col==GOLD else (-1.5 if col==SILVER else 2.3)), 0.6)
        draw_glow(im, (int(p[0]), int(p[1])), 8, col, 130, 10)
        d = ImageDraw.Draw(im)
        d.ellipse((int(p[0])-3, int(p[1])-3, int(p[0])+3, int(p[1])+3), fill=rgba(WHITE, 220))
    star_dust(im, SEED, t, 100)


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    im.paste(cosmic_ground(fs, TEAL, 0.4), (0, 0))
    cx, cy = W/2, 320
    trail(im, cx, cy, 200, 0.25, 100, GOLD_LIGHT, t, 0.6, 2, 90, 5)
    epicycle(im, cx, cy, 120, 50, 4, t, TEAL, 200, 0.6, 2)
    epicycle(im, cx, cy, 120, 30, -2.5, t, VIOLET, 180, 0.6, 2)
    a = t * 0.25
    p = orbit_point(cx, cy, 200, a, 0.6)
    draw_glow(im, (int(p[0]), int(p[1])), 10, GOLD_LIGHT, 120, 8)
    d = ImageDraw.Draw(im)
    d.ellipse((int(p[0])-4, int(p[1])-4, int(p[0])+4, int(p[1])+4), fill=rgba(WHITE, 200))
    star_dust(im, SEED+100, t, 80)


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    im.paste(cosmic_ground(fs, SILVER, 0.4), (0, 0))
    cx, cy = W/2, 330
    precessing_ring(im, cx, cy, 200, 0.3, t, SILVER, 120, 0.6, 2)
    precessing_ring(im, cx, cy, 150, 0.45, t*1.2, GOLD, 100, 0.6, 2)
    precessing_ring(im, cx, cy, 100, 0.6, t*0.8, TEAL, 80, 0.6, 2)
    pa = t * 0.3
    dx = 30 * math.sin(pa) * math.cos(t*0.5)
    draw_glow(im, (cx+int(dx), cy-60), 30, SILVER, 70, 20)
    star_dust(im, SEED+200, t, 90)


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    im.paste(cosmic_ground(fs, GOLD_LIGHT, 0.5), (0, 0))
    cx, cy = W/2, 320
    speeds = [1.0, 2.0, 3.0, 4.0, 5.0]
    cols = [GOLD, SILVER, TEAL, VIOLET, CORAL]
    for i, (s, col) in enumerate(zip(speeds, cols)):
        r = 40 + i*36
        trail(im, cx, cy, r, s*0.15, int(40+i*12), col, t, 0.6, 2, 80, 4)
    a = t * 0.15
    for i, (s, col) in enumerate(zip(speeds, cols)):
        r = 40 + i*36
        p = orbit_point(cx, cy, r, a * s, 0.6)
        draw_glow(im, (int(p[0]), int(p[1])), 6, col, 100, 8)
    draw_glow(im, (cx, cy), 25, GOLD, 80, 15)
    star_dust(im, SEED+300, t, 70)


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    im.paste(cosmic_ground(fs, GOLD, 0.6), (0, 0))
    cx, cy = W/2, 320
    R, r = 160, 60
    ratio = 0.97
    pts = []
    n = 250
    for i in range(n):
        u = i/(n-1)
        theta = u * 2 * math.pi * 4 + t * 0.12
        x = cx + R * math.cos(theta) + r * math.cos(theta * ratio)
        y = (cy + R * math.sin(theta) + r * math.sin(theta * ratio)) * 0.6
        pts.append((x, y))
    reveal = partial_polyline(pts, smoothstep(0.04, 0.92, t))
    if len(reveal) > 1:
        draw_line_glow(im, reveal, GOLD_LIGHT, 2, 110, 5)
    for i in range(7):
        u = i/7
        theta = u * 2 * math.pi * 4 + t * 0.12
        x = cx + R * math.cos(theta) + r * math.cos(theta * ratio)
        y = (cy + R * math.sin(theta) + r * math.sin(theta * ratio)) * 0.6
        draw_glow(im, (int(x), int(y)), 6, GOLD, 120, 7)
    draw_glow(im, (cx, cy), 18, GOLD_LIGHT, 70, 12)
    star_dust(im, SEED+400, t, 60)


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    im.paste(cosmic_ground(fs, None, 0.8), (0, 0))
    cx, cy = W/2, 320
    breath = 0.5 + 0.5 * math.sin(t * math.pi * 2)
    trail(im, cx, cy, 80 + 60*breath, 0.5, 80, GOLD, t, 0.6, 3, 110, 6)
    trail(im, cx, cy, 80 + 60*(1-breath), -0.5, 80, SILVER, t, 0.6, 2, 90, 5)
    a = t * 0.5
    p1 = orbit_point(cx, cy, 80 + 60*breath, a, 0.6)
    p2 = orbit_point(cx, cy, 80 + 60*(1-breath), -a, 0.6)
    draw_glow(im, (int(p1[0]), int(p1[1])), 10, GOLD, 150, 10)
    draw_glow(im, (int(p2[0]), int(p2[1])), 8, SILVER, 120, 9)
    d = ImageDraw.Draw(im)
    d.ellipse((int(p1[0])-3, int(p1[1])-3, int(p1[0])+3, int(p1[1])+3), fill=rgba(WHITE, 220))
    star_dust(im, SEED+500, t, 85)


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    im.paste(cosmic_ground(fs, GOLD_LIGHT, 0.4), (0, 0))
    cx, cy = W/2, 320
    epicycle(im, cx, cy, 60, 180, -1.5, t, GOLD, 200, 0.6, 2)
    epicycle(im, cx, cy, 60, 120, 2, t*1.1, SILVER, 180, 0.6, 2)
    epicycle(im, cx, cy, 60, 80, -3, t*0.9, TEAL, 160, 0.6, 2)
    epicycle(im, cx, cy, 60, 40, 4.5, t*0.8, VIOLET, 140, 0.6, 2)
    a = t * 0.2
    p0 = orbit_point(cx, cy, 20, a, 1.0)
    draw_glow(im, (int(p0[0]), int(p0[1])), 35, GOLD_LIGHT, 130, 18)
    d = ImageDraw.Draw(im)
    d.ellipse((int(p0[0])-8, int(p0[1])-8, int(p0[0])+8, int(p0[1])+8), fill=rgba(WHITE, 255))
    star_dust(im, SEED+600, t, 100)


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    im.paste(cosmic_ground(fs, VIOLET, 0.4), (0, 0))
    cx, cy = W/2, 320
    for i in range(9):
        r = 30 + i*22
        speed = (1 if i%2==0 else -1) * (0.2 + i*0.04)
        col = mix(GOLD, VIOLET, i/9)
        trail(im, cx, cy, r, speed, int(30+i*8), col, t, 0.6, 1, 60, 3)
    draw_glow(im, (cx, cy), 50, GOLD_LIGHT, 100, 22)
    draw_glow(im, (cx, cy), 20, WHITE, 140, 12)
    d = ImageDraw.Draw(im)
    d.ellipse((cx-10, cy-10, cx+10, cy+10), fill=rgba(WHITE, 255))
    star_dust(im, SEED+700, t, 130)


SCENES = [
    Scene('kl01', 'The Wheel of Time', 'Three nested cycles turning at different rates.', 'Kāla-cakra', 'The most basic structure of time: concentric cycles of different durations.', 'nested_orbits', ['time','cycles','wheel'], 'cycle', 'three concentric luminous orbits', sc01),
    Scene('kl02', 'The Epicycle', 'A cycle upon a cycle — the path of compounded motion.', 'Epicyclus', 'Each prāṇa is a cycle that rides upon a larger cycle.', 'epicyclic_path', ['epicycle','compounding','orbit'], 'cycle', 'epicyclic traced path with orbiting nodes', sc02),
    Scene('kl03', 'The Precession', 'The slow drift of the axis — the 26,000-year turn.', 'Ayana', 'Vyāna governs the precession: the vastest cycle within consciousness.', 'axial_precession', ['precession','axis','drift'], 'cycle', 'precessing rings with axial wobble', sc03),
    Scene('kl04', 'The Five Speeds', 'Five prāṇas as five distinct temporal frequencies.', 'Pañca-chanda', 'Prāṇa, apāna, samāna, udāna, vyāna as harmonic time-scales.', 'five_frequencies', ['pranas','frequencies','harmonics'], 'multiplicity', 'five concentric orbits at different speeds', sc04),
    Scene('kl05', 'The Near Return', 'An orbit that almost closes — the subtle drift.', 'Asaṃpūrṇa', 'No cycle perfectly returns; the near-miss IS time\'s creativity.', 'near_return', ['return','drift','near-miss'], 'drift', 'dense epicyclic trace with near-closure', sc05),
    Scene('kl06', 'The Breath of Time', 'Expansion and contraction — time breathing.', 'Prāṇa-kāla', 'Prāṇa and apāna as the systole and diastole of cosmic time.', 'breath_cycle', ['breath','expansion','contraction'], 'breath', 'two interacting breath-orbits', sc06),
    Scene('kl07', 'The Still Point', 'All cycles from the unmoving center.', 'Niścala', 'The witness: cycles turn but the center does not move.', 'still_center', ['center','witness','stillness'], 'witness', 'nested epicycles around a fixed still center', sc07),
    Scene('kl08', 'The Kālopāya Seal', 'All cycles as one timeless pattern.', 'Kālopāya-cakra', 'Time and timelessness are one: the pattern of all cycles as a single eternal form.', 'closing_seal', ['seal','timeless','cycles'], 'seal', 'nine concentric orbits of harmonically related speeds', sc08),
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
    sheet = Image.new('RGB', (4*320, 2*180), color=COSMIC_DARK)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Kālopāya: The Temporal Means',
        'source_basis': 'Tantrāloka Āhnika 6: Kālopāya — the unique Tantrāloka teaching that time itself is the path. The five prāṇas govern cosmic time cycles (solar, lunar, equinoxes, nakṣatras, precession). No equivalent in Layayoga or Buddhist tantras.',
        'style': {
            'family': 'abstract orbital mechanics / celestial time-art',
            'background': 'deep cosmic dark',
            'ink': 'luminous orbital trails of silver, gold, teal, violet',
            'accent': 'orbiting nodes, epicyclic traces, precessing rings',
            'materials': ['luminous trails','epicyclic paths','precessing rings','orbital nodes','star dust']
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
            'basic_time': ['kl01', 'kl02'],
            'vast_cycles': ['kl03', 'kl04'],
            'subtle_time': ['kl05', 'kl06'],
            'stillness_and_seal': ['kl07', 'kl08']
        },
        'reusability_notes': {
            'kl01': 'Use for the wheel of time, nested cycles, or basic temporal structure.',
            'kl02': 'Use for compounded cycles, epicyclic motion, or prāṇas riding on prāṇas.',
            'kl03': 'Use for precession, vast time, axial drift, or vyāna as cosmic time.',
            'kl04': 'Use for the five prāṇas as temporal frequencies.',
            'kl05': 'Use for near-return, the almost-closed cycle, or time as creative non-repetition.',
            'kl06': 'Use for breath-rhythm of time, expansion/contraction, or prāṇa-apāna as systole-diastole.',
            'kl07': 'Use for the still center, the witness amidst change, or the unmoving point.',
            'kl08': 'Use as a closing seal for time-as-path or Kālopāya cosmology.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Kālopāya: The Temporal Means

## Aim
This pack visualizes Kālopāya — the unique Tantrāloka teaching that TIME itself is the spiritual path. No equivalent exists in Layayoga or Buddhist tantras.

## Doctrine
- The five prāṇas govern specific cosmic time cycles
- Prāṇa = solar year, Apāna = lunar month, Samāna = equinoxes
- Udāna = nakṣatras (27 lunar mansions), Vyāna = precession of equinoxes (26,000 years)
- Time is not an obstacle to liberation — it IS the path
- The cycles of breath, day, year, and precession are all gates

## Visual rules
- No diagrams or labels — pure orbital motion as meditation
- Each scene is a different temporal structure rendered as luminous trails
- The viewer experiences time through the motion, not through explanation
- Slow, majestic pacing — these cycles take lifetimes
- The closing seal shows all cycles as one timeless pattern

## Style
- Deep cosmic dark background
- Luminous orbital trails (not solid rings — traced paths)
- Epicyclic motion: circles on circles
- Precession: the axis itself turns
- Star dust as distant temporal markers

## New motifs
- nested luminous orbits at different speeds
- epicyclic traced paths
- precessing rings with axial wobble
- near-return / almost-closed trajectory
- breath-orbits expanding and contracting
- still center within all motion
- nine-speed harmony seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Kālopāya Pack

## Differentiation
This pack uses abstract celestial mechanics as its visual language — orbiting points, epicyclic traces, precessing rings — completely different from the fluid color fields of Ṣaḍānanda, the moiré interference of Pratyabhijñā, or the dream forms of Ābhāsa.

## What makes it unique
- NO filled shapes — entirely line-based
- NO static forms — everything is traced in motion
- NO symmetry for symmetry's sake — the patterns emerge from orbital mechanics
- The content IS the motion: the philosophy is enacted through orbital dynamics
- Star dust as the only texture — pure space

## New motifs
1. nested luminous trails
2. epicyclic path traces
3. precessing axial rings
4. five-speed harmonic orbits
5. near-return dense epicycle
6. breathing orbit pairs
7. still center with surrounding epicycles
8. nine-speed harmony seal

## Material vocabulary
- cosmic dark field
- silver orbital trails
- gold primary cycles
- teal harmonic frequencies
- violet precessional drift
- white nodal points
- star dust markers

## Distinct closing seal
Nine concentric orbits at harmonically related speeds, each rendered as a luminous trail, converging on a pure white still center.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — Kālopāya: The Temporal Means Pack

This pack visualizes time itself as the spiritual path — a teaching unique to the Tantrāloka. The visual language is abstract celestial mechanics: orbiting points, epicyclic traces, precessing rings. No diagrams, no labels — pure motion as meditation.

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
    combined = ROOT / 'kalopaya_temporal_means_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'kalopaya_temporal_means_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['kalopaya_temporal_means_animation.mp4','contact_sheet.jpg',
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
    combined = ROOT / 'kalopaya_temporal_means_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
