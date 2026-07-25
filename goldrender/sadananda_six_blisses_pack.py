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
SEED = 60666

# Ṣaḍānanda palette — six qualities of bliss, one consciousness
DEEP_VOID = (16, 14, 16)
WARM_VOID = (24, 22, 20)
NIGHT_SILVER = (26, 24, 28)
DARK_GOLD = (36, 30, 22)
BONE = (239, 235, 226)
IVORY = (248, 245, 238)
PEARL = (252, 250, 246)
WHITE = (254, 252, 249)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
SILVER = (204, 212, 226)
MOON = (200, 210, 228)
LAVENDER = (202, 194, 216)
TEAL = (96, 146, 148)
TEAL_LIGHT = (162, 198, 200)
CRIMSON = (154, 44, 58)
CARDINAL = (188, 56, 70)
ROSE = (196, 106, 130)
CORAL = (210, 130, 120)
VIOLET = (120, 100, 164)
LAVENDER_DEEP = (140, 128, 180)
UMBER = (82, 66, 50)
SLATE = (100, 110, 130)
MIST = (170, 178, 194)

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
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t * t * (3 - 2 * t)


def rgba(c, a=255):
    return (*c[:3], int(a))


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


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(WHITE, 55), width=1)
    d.rectangle((36, 36, W-36, H-36), outline=rgba(WHITE, 30), width=1)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H - 100
    d.rounded_rectangle((120, y0, W-120, H-38), radius=12, fill=(20, 18, 20, 160), outline=rgba(WHITE, 30), width=1)
    d.text((W/2, y0+18), title, font=TITLE_FONT, fill=rgba(WHITE, 230), anchor='mm')
    d.text((W/2, y0+50), subtitle, font=SUB_FONT, fill=rgba(MIST, 180), anchor='mm')
    if term:
        tw = d.textbbox((0, 0), term, font=TERM_FONT)[2]
        d.text((W-130-tw, y0+22), term, font=TERM_FONT, fill=rgba(GOLD_LIGHT, 200))


def bliss_ground(seed, bg, glow_col, glow_intensity=1.0):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(bg, dtype=np.float32)
    coarse = rng.normal(0, 1, (42, 76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*2.8*glow_intensity + fine[..., None]*0.8*glow_intensity
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx-W/2)/(W/2)
    dy = (yy-H/2)/(H/2)
    vign = np.clip((dx*dx+dy*dy)*14, 0, 22)
    base -= vign[..., None]
    g = np.exp(-(((xx-W*0.45)/(W*0.28))**2 + ((yy-H*0.40)/(H*0.24))**2)*2.4)
    for i in range(3):
        base[..., i] += g * glow_col[i] * glow_intensity * 0.04
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def fluid_overlay(primary, secondary, accent, t, blur=55):
    field = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(field)
    dx = 30 * math.sin(t * math.pi * 0.6)
    dy = 20 * math.cos(t * math.pi * 0.5)
    br = 1.0 + 0.025 * math.sin(t * math.pi * 2)
    cx1 = W*0.45 + dx
    cy1 = H*0.40 + dy*0.5
    r1x = W*0.38*br
    r1y = H*0.34*br
    d.ellipse((cx1-r1x, cy1-r1y, cx1+r1x, cy1+r1y), fill=rgba(primary, 80))
    cx2 = W*0.55 - dx*0.6
    cy2 = H*0.55 - dy*0.4
    r2x = W*0.34*br
    r2y = H*0.28*br
    d.ellipse((cx2-r2x, cy2-r2y, cx2+r2x, cy2+r2y), fill=rgba(secondary, 70))
    cx3 = W*0.50 + dx*0.2
    cy3 = H*0.46 + dy*0.7
    r3 = min(W, H)*0.14*br
    d.ellipse((cx3-r3, cy3-r3, cx3+r3, cy3+r3), fill=rgba(accent, 55))
    return field.filter(ImageFilter.GaussianBlur(blur))


def particles(im, seed, t, n=25, col=WHITE):
    rng = np.random.default_rng(seed)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        x = float(rng.uniform(80, W-80))
        y = float(rng.uniform(80, H-80))
        dx = 25 * math.sin(t*0.5 + i*1.7)
        dy = 15 * math.cos(t*0.7 + i*2.3)
        r = float(rng.uniform(1.0, 2.5))
        a = int(rng.uniform(25, 70))
        d.ellipse((x+dx-r, y+dy-r, x+dx+r, y+dy+r), fill=rgba(col, a))
    im.alpha_composite(ov)


def draw_breath_ripple(im, cx, cy, t, col, max_r=200):
    ripples = 4
    for i in range(ripples):
        phase = i / ripples
        r = max_r * clamp((t * 1.2) - phase)
        if r <= 5: continue
        alpha = int(60 * (1 - r/max_r) * (0.5 + 0.5*math.sin(t*math.pi*2)))
        d = ImageDraw.Draw(im)
        d.ellipse((cx-r, cy-r*0.62, cx+r, cy+r*0.62), outline=rgba(col, alpha), width=1)


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
    g = bliss_ground(fs, DEEP_VOID, GOLD, 0.5)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((40, 36, 34), (55, 48, 44), GOLD, t, 60)
    im.alpha_composite(ov)
    draw_glow(im, (W//2, int(H*0.38)), 60, GOLD, 60, 50)
    draw_glow(im, (W//2, int(H*0.45)), 20, GOLD_LIGHT, 50, 30)


def sc02(im, t):
    fs = SEED + int(t*9973+500) % 100000
    g = bliss_ground(fs, NIGHT_SILVER, SILVER, 0.6)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((90, 88, 100), (70, 68, 82), SILVER, t, 55)
    im.alpha_composite(ov)
    settle = ease_in_out(t)
    draw_glow(im, (W//2, int(H*0.35 + 80*(1-settle))), 50, SILVER, int(70*settle), 45)
    particles(im, fs+100, t, 20, SILVER)


def sc03(im, t):
    fs = SEED + int(t*9973+1000) % 100000
    g = bliss_ground(fs, (22, 24, 32), MOON, 0.7)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((60, 70, 100), (50, 55, 80), MOON, t, 55)
    im.alpha_composite(ov)
    arise = smoothstep(0, 0.8, t)
    if arise > 0:
        draw_glow(im, (W//2, int(H*0.55)), int(10+40*arise), MOON, int(80*arise), 35)
    particles(im, fs+200, t*0.7, 18, MOON)


def sc04(im, t):
    fs = SEED + int(t*9973+1500) % 100000
    g = bliss_ground(fs, (28, 30, 26), GOLD, 0.5)
    im.paste(g, (0, 0), g)
    gm = mix(GOLD, TEAL_LIGHT, .6)
    ov = fluid_overlay((80, 100, 96), gm, GOLD, t, 50)
    im.alpha_composite(ov)
    for i in range(4):
        phase = i*0.15
        p = clamp((t-phase)*2)
        if p <= 0: continue
        draw_glow(im, (W//2, H//2), 40+i*36, GOLD, int(40*p*(1-i/5)), 30)
    particles(im, fs+300, t*0.5, 30, GOLD_LIGHT)


def sc05(im, t):
    fs = SEED + int(t*9973+2000) % 100000
    g = bliss_ground(fs, (30, 20, 18), CORAL, 0.7)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((90, 40, 48), (70, 50, 30), GOLD, t, 50)
    im.alpha_composite(ov)
    rise = ease_in_out(t)
    for i in range(6):
        a = -math.pi/2 + i*0.3
        r = 60 + 90*rise
        x = W//2 + math.cos(a)*r*0.3
        y = H//2 + math.sin(a)*r*0.5 - 40*(1-rise)
        draw_glow(im, (int(x), int(y)), 18, CORAL, int(70*rise*(1-i/7)), 20)
    particles(im, fs+400, t*1.3, 22, CORAL)


def sc06(im, t):
    fs = SEED + int(t*9973+2500) % 100000
    g = bliss_ground(fs, (28, 22, 36), VIOLET, 0.6)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((80, 64, 110), (60, 50, 90), LAVENDER, t, 55)
    im.alpha_composite(ov)
    expand = ease_in_out(t)
    for i in range(3):
        r = int(20 + 80*expand + i*30)
        draw_glow(im, (W//2, H//2), r, VIOLET, int(45*(1-i*0.2)*expand), 35)
    particles(im, fs+500, t*0.4, 35, LAVENDER)


def sc07(im, t):
    fs = SEED + int(t*9973+3000) % 100000
    g = bliss_ground(fs, (30, 28, 24), GOLD_LIGHT, 0.8)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((120, 108, 80), GOLD, WHITE, t, 50)
    im.alpha_composite(ov)
    rad = ease_in_out(t)
    for r, col, delay in [(180, GOLD, 0), (120, GOLD_LIGHT, 0.15), (60, WHITE, 0.3)]:
        p = smoothstep(delay, delay+0.5, t)
        if p <= 0: continue
        draw_glow(im, (W//2, H//2), r, col, int(100*p), 40)
    particles(im, fs+600, t*0.3, 40, WHITE)


def sc08(im, t):
    fs = SEED + int(t*9973+3500) % 100000
    g = bliss_ground(fs, DEEP_VOID, GOLD, 0.5)
    im.paste(g, (0, 0), g)
    ov = fluid_overlay((70, 60, 50), GOLD, WHITE, t, 50)
    im.alpha_composite(ov)
    bliss_cols = [GOLD, SILVER, MOON, TEAL_LIGHT, CORAL, LAVENDER, WHITE]
    for i, col in enumerate(bliss_cols):
        a = -math.pi/2 + i*2*math.pi/len(bliss_cols) + t*0.03
        r = 110 + 30*math.sin(t*math.pi + i)
        x = W//2 + math.cos(a)*r
        y = H//2 + math.sin(a)*r*0.62
        rr = 14 + 8*math.sin(t*2 + i*0.7)
        draw_glow(im, (int(x), int(y)), int(rr), col, int(60+30*math.sin(t*0.5+i)), 25)
    draw_glow(im, (W//2, H//2), 80, GOLD_LIGHT, 100, 45)
    draw_glow(im, (W//2, H//2), 25, WHITE, 120, 20)
    d = ImageDraw.Draw(im)
    d.ellipse((W//2-10, H//2-10, W//2+10, H//2+10), fill=rgba(WHITE, 255))
    particles(im, fs+700, t*0.5, 50, WHITE)


SCENES = [
    Scene('sa01', 'Nijānanda', 'Innate bliss — pure subjectivity, deep luminous emptiness.', 'Nijānanda', 'The base state: the heart as pure emptiness, lucid deep sleep.', 'innate_bliss', ['bliss','innate','emptiness'], 'base', 'deep luminous dark with golden heart-glow', sc01),
    Scene('sa02', 'Nirānanda', 'Bliss of stillness — the exhaled breath settling.', 'Nirānanda', 'Stillness arises with prāṇa: the subject settles into itself.', 'stillness_bliss', ['bliss','stillness','prana'], 'breath', 'silver-white settling field', sc02),
    Scene('sa03', 'Parānanda', 'Bliss of the other — the object arises like the moon.', 'Parānanda', 'Inhalation brings the object: the world is received.', 'other_bliss', ['bliss','object','apana'], 'breath', 'cool moon-blue arising field', sc03),
    Scene('sa04', 'Brahmānanda', 'Bliss of Brahman — all objects fused into one.', 'Brahmānanda', 'Retention integrates: subject and object become one field.', 'brahman_bliss', ['bliss','integration','samana'], 'breath', 'gold-teal integrated field', sc04),
    Scene('sa05', 'Mahānanda', 'Great bliss — the fire of udāna devours duality.', 'Mahānanda', 'The rising breath consumes all distinction in its flame.', 'great_bliss', ['bliss','fire','udana'], 'breath', 'crimson-gold rising fire field', sc05),
    Scene('sa06', 'Cidānanda', 'Bliss of consciousness — the great pervasion.', 'Cidānanda', 'Vyāna pervades all: consciousness as unlimited field.', 'consciousness_bliss', ['bliss','pervasion','vyana'], 'breath', 'violet-white pervasive field', sc06),
    Scene('sa07', 'Jagadānanda', 'Cosmic bliss — the universe as one\'s own consciousness.', 'Jagadānanda', 'Beyond all limitation: the world shines as self-radiant awareness.', 'cosmic_bliss', ['bliss','cosmic','anupaya'], 'synthesis', 'pure white-gold radiant field', sc07),
    Scene('sa08', 'The Seal of the Six', 'All blisses gathered as one luminous field.', 'Ṣaḍānanda-cakra', 'The six qualities of bliss resolve into one consciousness.', 'closing_seal', ['seal','blisses','consciousness'], 'seal', 'all bliss-colors in one field', sc08),
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
    sheet = Image.new('RGB', (4*320, 2*180), color=DEEP_VOID)
    for idx, im in enumerate(thumbs):
        x = (idx%4)*320; y = (idx//4)*180
        sheet.paste(im, (x, y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — Ṣaḍānanda: The Six Blisses of Consciousness',
        'source_basis': 'Tantrāloka Āhnika 5 (lines 3440–4003): the six blisses associated with the five vital breaths and their cosmic synthesis. Unique to Abhinavagupta.',
        'style': {
            'family': 'fluid color-field meditation / painterly abstraction',
            'background': 'deep warm voids and luminous color fields',
            'ink': 'color itself — no linework, no geometry',
            'accent': 'gold, silver, moon-blue, teal-gold, crimson, violet, white',
            'materials': ['blurred color fields','atmospheric glow','luminous particles','breathing expansion']
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
            'base_stillness': ['sa01', 'sa02'],
            'emergence_integration': ['sa03', 'sa04'],
            'fire_pervasion': ['sa05', 'sa06'],
            'cosmic_seal': ['sa07', 'sa08']
        },
        'reusability_notes': {
            'sa01': 'Use for deep subjectivity, the heart as emptiness, or the base of all bliss.',
            'sa02': 'Use for stillness, exhalation, settling, or the bliss of the subject alone.',
            'sa03': 'Use for the arising of the object, inhalation, lunar quality, or the bliss of the other.',
            'sa04': 'Use for integration, retention, nonduality, or the bliss of Brahman.',
            'sa05': 'Use for rising fire, devouring duality, udāna, or Mahānanda.',
            'sa06': 'Use for pervasion, vyāna, unlimited consciousness, or Cidānanda.',
            'sa07': 'Use for cosmic consciousness, Anupāya, or Jagadānanda as the universe in one\'s own self.',
            'sa08': 'Use as a closing seal for the six blisses or experiential ascent through breath.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Ṣaḍānanda: The Six Blisses

## Aim
This pack visualizes the six blisses (ṣaḍānanda) of Tantrāloka Āhnika 5 — a unique systematization by Abhinavagupta in which each phase of the vital breath corresponds to a specific quality of bliss.

## Doctrine
The six blisses map the progressive expansion of consciousness through the five vital breaths plus their cosmic synthesis:

1. **Nijānanda** (Innate Bliss) — the base state: pure emptiness of deep sleep, the heart as pure subjectivity
2. **Nirānanda** (Bliss of Stillness) — arises with prāṇa (exhalation); the subject settles into stillness
3. **Parānanda** (Bliss of the Other) — arises with apāna (inhalation); the object arises like the moon
4. **Brahmānanda** (Bliss of Brahman) — arises with samāna (retention); objects fuse into unitary consciousness
5. **Mahānanda** (Great Bliss) — arises with udāna (rising breath); fire devours duality
6. **Cidānanda** (Bliss of Consciousness) — arises with vyāna (pervasive breath); unlimited field
7. **Jagadānanda** (Cosmic Bliss) — beyond limitation; the universe shining as one's own consciousness

## Visual rules
- No geometry. No diagrams. No text on the field.
- Each scene is a single, evolving color field — a meditation on one quality of bliss.
- Color IS the content. The shift from one scene to the next IS the philosophy.
- The visual language is abstract painterly — Rothko, not textbook.
- Tiny luminous particles drift like motes in sunlight, imperceptibly alive.
- A slow breathing pulse animates the entire field.

## Style
- Pure fluid color fields with heavy Gaussian blur
- No linework except the minimal border and footer
- No geometric shapes — all forms are organically blurred
- Particles as subtle life in the field
- Each scene a different quality of light

## New motifs
- fluid color-field abstraction as philosophical statement
- breaths as evolving color relationships
- particles as luminous awareness
- the seal: all colors as one field
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Ṣaḍānanda Pack

## Radical Differentiation
This pack breaks from every convention of the project. It contains:
- NO geometric shapes (circles, arcs, polygons, regular forms)
- NO diagrams or taxonomies
- NO labels on the visual field
- NO linework except the border
- NO body silhouettes, no schematics

Instead: pure color fields, atmospheric glow, and drifting particles. The pack is a sequence of painterly meditations — each 4.8 seconds of evolving color that corresponds to a quality of conscious bliss.

## What this enables
- Emotional / felt understanding rather than intellectual grasp
- The blisses are not explained — they are experienced chromatically
- The transitions between scenes enact the progression of consciousness
- The closing seal gathers all colors without collapsing their distinctness

## Material vocabulary
- deep warm void → silver stillness → moon-blue emergence
- gold-teal integration → crimson-gold fire → violet-white pervasion
- pure white-gold radiance → all colors as one field

## Deprecated
- All geometry
- All diagrams
- All labels
- All body references

## Distinct closing seal
All seven bliss-colors arranged as a corona around a pure white center — the many qualities of bliss as one consciousness.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — Ṣaḍānanda: The Six Blisses of Consciousness Pack

This pack is radically different from every other pack in the project. It contains no geometry, no diagrams, no labels. Each scene is a pure fluid color field — a painterly meditation on one quality of bliss.

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
    combined = ROOT / 'sadananda_six_blisses_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'sadananda_six_blisses_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['sadananda_six_blisses_animation.mp4','contact_sheet.jpg',
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
    combined = ROOT / 'sadananda_six_blisses_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
