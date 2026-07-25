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
SEED = 50505

# Palette: cleaner, more architectural than Kalis; loop-oriented cosmography
NIGHT = (22, 27, 38)
DEEP_BLUE = (33, 52, 88)
SLATE = (83, 98, 122)
MIST = (171, 184, 201)
BONE = (240, 234, 223)
IVORY = (248, 244, 236)
GOLD = (202, 161, 78)
GOLD_LIGHT = (245, 212, 129)
CRIMSON = (154, 47, 62)
EMBER = (225, 122, 58)
TEAL = (86, 142, 144)
GREEN = (104, 150, 112)
UMBER = (79, 63, 49)
BLACK = (18, 18, 18)
WHITE = (250, 248, 244)

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


def cosmic_ground(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0, 1, (44, 78)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse - coarse.min()) / (np.ptp(coarse) + 1e-6) * 255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr = (np.asarray(cimg).astype(np.float32) - 128) / 128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None] * 4.2 + fine[..., None] * 1.1
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W/2)/(W/2)
    dy = (yy - H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy)*22, 0, 24)
    base -= vign[..., None]
    # softer central luminosity
    glow = np.exp(-(((xx-W/2)/(W*0.34))**2 + ((yy-H*0.43)/(H*0.28))**2)*2.6)
    for i,c in enumerate((DEEP_BLUE[0], DEEP_BLUE[1], DEEP_BLUE[2])):
        base[..., i] += glow * (26 if i==2 else 12)
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W, H), (0,0,0,0))


def draw_glow(im: Image.Image, xy, radius, color, alpha=160, blur=18):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im: Image.Image, pts, color, width=3, alpha=160, blur=8):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1, width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+80)), width=width, joint='curve')


def footer(im: Image.Image, title: str, subtitle: str, term: str | None = None):
    d = ImageDraw.Draw(im)
    y0 = H - 112
    d.rounded_rectangle((90, y0, W-90, H-34), radius=14, fill=(18,21,30,198), outline=rgba(MIST, 70), width=1)
    d.text((122, y0+18), title, font=TITLE_FONT, fill=IVORY)
    d.text((124, y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def border(im: Image.Image):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(MIST, 115), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD, 95), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, CRIMSON, GOLD)


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,150), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
        y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
        pts.append((x,y))
    return pts


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


def arc_points(cx, cy, rx, ry, a0, a1, n=90):
    return [(cx + math.cos(lerp(a0, a1, i/(n-1)))*rx, cy + math.sin(lerp(a0, a1, i/(n-1)))*ry) for i in range(n)]


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang = math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s = 12*scale
    pts = [p1,
           (p1[0]-math.cos(ang-0.5)*s, p1[1]-math.sin(ang-0.5)*s),
           (p1[0]-math.cos(ang+0.5)*s, p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts, fill=rgba(color, 230))


def draw_starburst(im, cx, cy, rays, r0, r1, color):
    d = ImageDraw.Draw(im)
    for i in range(rays):
        a = -math.pi/2 + i*2*math.pi/rays
        p0 = (cx + math.cos(a)*r0, cy + math.sin(a)*r0)
        p1 = (cx + math.cos(a)*r1, cy + math.sin(a)*r1)
        draw_line_glow(im, [p0,p1], color, 2, 90, 5)
    draw_glow(im, (cx,cy), int(r0*0.7), color, 120, 14)
    d.ellipse((cx-16,cy-16,cx+16,cy+16), fill=rgba(WHITE,255), outline=rgba(color,220), width=2)


def draw_orbit(im, cx, cy, rx, ry, progress, color, width=3, rotation=0.0):
    pts = []
    for i in range(120):
        a = rotation + i*(2*math.pi/119)
        pts.append((cx + math.cos(a)*rx, cy + math.sin(a)*ry))
    pts = partial_polyline(pts, progress)
    if len(pts) > 1:
        draw_line_glow(im, pts, color, width, 120, 6)
        d = ImageDraw.Draw(im)
        draw_arrowhead(d, pts[-2], pts[-1], color, 1.0)


def draw_node(draw, x, y, r, outline, fill=None, label=None):
    draw.ellipse((x-r,y-r,x+r,y+r), outline=rgba(outline,220), fill=fill or rgba((255,255,255),30), width=2)
    if label:
        draw.text((x,y), label, font=SMALL_FONT, fill=IVORY, anchor='mm')


def draw_micro_nodes(draw, cx, cy, phase=0.0):
    for i in range(5):
        a = phase + i*2*math.pi/5
        x = cx + math.cos(a)*52
        y = cy + math.sin(a)*34
        draw.ellipse((x-4,y-4,x+4,y+4), fill=rgba(mix(GOLD, MIST, i/5), 220))


def dust(im, seed, n=90):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 2.6))
        c = mix(MIST, GOLD_LIGHT, rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c, int(rng.uniform(35,95))))
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


# Scene functions

def sc01(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # fivefold overview loop
    labels = [('sṛṣṭi', GOLD_LIGHT), ('sthiti', TEAL), ('saṃhāra', CRIMSON), ('tirodhāna', SLATE), ('anugraha', GREEN)]
    radius = 185
    for i,(lab,col) in enumerate(labels):
        a = -math.pi/2 + i*2*math.pi/5
        x = cx + math.cos(a)*radius
        y = cy + math.sin(a)*radius*0.76
        draw_node(d, x, y, 36, col, rgba(mix(NIGHT,col,.18), 80), None)
        d.text((x,y+1), str(i+1), font=TERM_FONT, fill=IVORY, anchor='mm')
        d.text((x, y+58), lab, font=SMALL_FONT, fill=col, anchor='mm')
    for i,(lab,col) in enumerate(labels):
        a0 = -math.pi/2 + i*2*math.pi/5
        a1 = -math.pi/2 + ((i+1)%5)*2*math.pi/5
        pts = arc_points(cx, cy, radius, radius*0.76, a0+0.18, a1-0.18, 60)
        pts = partial_polyline(pts, smoothstep(0.05,0.8,t))
        if len(pts)>1:
            draw_line_glow(im, pts, col, 3, 110, 6)
            draw_arrowhead(d, pts[-2], pts[-1], col, 0.9)
    draw_glow(im,(cx,cy),46,GOLD_LIGHT,120,12)
    d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 275
    draw_starburst(im, cx, cy, 12, 32, 230*ease_out_cubic(t), GOLD_LIGHT)
    for i in range(12):
        a = -math.pi/2 + i*2*math.pi/12
        x = cx + math.cos(a)*(245*ease_out_cubic(t))
        y = cy + math.sin(a)*(145*ease_out_cubic(t))
        d.ellipse((x-10,y-10,x+10,y+10), fill=rgba(mix(GOLD_LIGHT,TEAL,i/12),180), outline=rgba(GOLD,140))
    d.text((640, 496), 'form flashes outward from a single center', font=SUB_FONT, fill=MIST, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 290
    for i in range(5):
        rx = 78 + i*64
        ry = 28 + i*21
        d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry), outline=rgba(mix(TEAL, MIST, i/5), 140), width=2)
    block_w = lerp(36, 220, ease_in_out(t))
    d.rounded_rectangle((cx-block_w, cy-36, cx+block_w, cy+36), radius=20, outline=rgba(TEAL, 220), fill=rgba((45,84,92),110), width=3)
    draw_glow(im, (cx,cy), 44, TEAL, 100, 12)
    d.text((640, 500), 'manifestation is held in a tense equilibrium', font=SUB_FONT, fill=MIST, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 286
    for i in range(9):
        a = -math.pi/2 + i*2*math.pi/9 + t*0.04
        start = (cx + math.cos(a)*240, cy + math.sin(a)*135)
        pts = partial_polyline(bezier(start, (start[0]*0.65+cx*0.35, start[1]), (cx+math.cos(a)*70, cy+math.sin(a)*45), (cx,cy), 90), smoothstep(0.02,0.84,t))
        if len(pts)>1:
            draw_line_glow(im, pts, mix(CRIMSON, GOLD, i/9), 3, 110, 6)
    draw_glow(im,(cx,cy),56,CRIMSON,100,14)
    d.ellipse((cx-24,cy-24,cx+24,cy+24), fill=rgba(NIGHT,250), outline=rgba(CRIMSON,220), width=2)
    d.text((640, 500), 'what has emerged is drawn back to the center', font=SUB_FONT, fill=MIST, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 278
    # veil between source and object
    draw_glow(im,(cx-175,cy),34,GOLD_LIGHT,120,10)
    d.ellipse((cx-185, cy-10, cx-165, cy+10), fill=rgba(WHITE,255))
    d.rounded_rectangle((cx-55, 150, cx+55, 408), radius=14, outline=rgba(SLATE,180), fill=rgba((80,90,115),80), width=2)
    for i in range(9):
        x = cx-44 + i*11
        draw_line_glow(im, [(x,162),(x+15*math.sin(t*2*math.pi+i*0.4),398)], mix(SLATE, MIST, .5), 1, 65, 5)
    orb_x = lerp(cx-172, cx+220, smoothstep(0.1,0.9,t))
    d.ellipse((orb_x-16, cy-16, orb_x+16, cy+16), fill=rgba(CRIMSON,190), outline=rgba(MIST,160), width=2)
    d.text((cx-176, 126), 'source', font=SMALL_FONT, fill=GOLD_LIGHT, anchor='mm')
    d.text((cx+220, 126), 'object', font=SMALL_FONT, fill=CRIMSON, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 278
    # split field, veil opening, grace flash
    d.ellipse((cx-220, cy-110, cx-20, cy+110), outline=rgba(SLATE,130), width=2)
    d.ellipse((cx+20, cy-110, cx+220, cy+110), outline=rgba(GREEN,130), width=2)
    opening = 8 + 110*ease_in_out(t)
    d.rounded_rectangle((cx-opening, 140, cx+opening, 416), radius=18, outline=rgba(GOLD_LIGHT, 190), fill=rgba((250,225,160), 35), width=2)
    draw_glow(im, (cx,cy), int(26 + 55*ease_in_out(t)), GOLD_LIGHT, 150, 18)
    pts1 = partial_polyline(bezier((cx-130,cy), (cx-70,cy-60), (cx-30,cy-18), (cx,cy), 80), smoothstep(0.1,0.82,t))
    pts2 = partial_polyline(bezier((cx+130,cy), (cx+70,cy+60), (cx+30,cy+18), (cx,cy), 80), smoothstep(0.1,0.82,t))
    if len(pts1)>1: draw_line_glow(im, pts1, GREEN, 3, 120, 7)
    if len(pts2)>1: draw_line_glow(im, pts2, GOLD_LIGHT, 3, 120, 7)
    d.text((640, 505), 'grace reveals identity with the source', font=SUB_FONT, fill=MIST, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    # macrocosm and microcosm performing same loop
    leftx, rightx, cy = 355, 925, 280
    # macro loop
    for cx, scale, colmix in [(leftx, 1.0, 0.0), (rightx, 0.55, 0.45)]:
        labels = [('1', GOLD_LIGHT), ('2', TEAL), ('3', CRIMSON), ('4', SLATE), ('5', GREEN)]
        r = 170*scale
        for i,(lab,col) in enumerate(labels):
            a = -math.pi/2 + i*2*math.pi/5
            x = cx + math.cos(a)*r
            y = cy + math.sin(a)*(r*0.76)
            rr = 24*scale
            d.ellipse((x-rr,y-rr,x+rr,y+rr), outline=rgba(mix(col, MIST, colmix), 220), fill=rgba(mix(NIGHT,col,.1),75), width=2)
            d.text((x,y), lab, font=SMALL_FONT if scale<0.8 else TERM_FONT, fill=IVORY, anchor='mm')
        for i,(lab,col) in enumerate(labels):
            a0 = -math.pi/2 + i*2*math.pi/5
            a1 = -math.pi/2 + ((i+1)%5)*2*math.pi/5
            pts = arc_points(cx, cy, r, r*0.76, a0+0.18, a1-0.18, 60)
            pts = partial_polyline(pts, smoothstep(0.05,0.9,t))
            if len(pts)>1:
                draw_line_glow(im, pts, mix(col, MIST, colmix), 2 if scale<0.8 else 3, 110, 5)
        if cx == leftx:
            draw_micro_nodes(d, cx, cy, phase=t*0.2)
        else:
            draw_glow(im, (cx,cy), 18, GOLD_LIGHT, 120, 7)
    # connecting relation
    draw_line_glow(im, [(leftx+180, cy), (rightx-95, cy)], GOLD, 3, 100, 6)
    d.text((640, 498), 'the five acts operate at every scale', font=SUB_FONT, fill=MIST, anchor='mm')


SCENES = [
    Scene('pk01', 'The Fivefold Wheel', 'An overview of the simultaneous cosmic acts.', 'Pañcakṛtya', 'Śiva performs five functions continuously as one living cycle.', 'fivefold_overview', ['overview','loop','five acts'], 'overview', 'five-node loop wheel', sc01),
    Scene('pk02', 'Sṛṣṭi', 'Emission: form flashes forth from the source.', 'Sṛṣṭi', 'Manifestation is projected outward from a single center.', 'emission_starburst', ['creation','emission'], 'act', 'starburst emergence', sc02),
    Scene('pk03', 'Sthiti', 'Maintenance: form is held in stable tension.', 'Sthiti', 'The produced form is sustained and stabilized.', 'maintenance_block', ['maintenance','stability'], 'act', 'rings plus held block', sc03),
    Scene('pk04', 'Saṃhāra', 'Reabsorption: the outward field is drawn back in.', 'Saṃhāra', 'Manifest forms are recollected into the subjective center.', 'reabsorption_inward', ['reabsorption','withdrawal'], 'act', 'inward trajectories', sc04),
    Scene('pk05', 'Tirodhāna', 'Concealment: the source is veiled and objectified.', 'Tirodhāna', 'The real source is obscured, making the object seem independent.', 'veiling_screen', ['concealment','veil','objectification'], 'act', 'veil screen and displaced object', sc05),
    Scene('pk06', 'Anugraha', 'Grace: the veil opens in a flash of recognition.', 'Anugraha', 'Revelation discloses the identity of source and appearance.', 'grace_opening', ['grace','revelation','recognition'], 'act', 'opening veil and converging arcs', sc06),
    Scene('pk07', 'The Act at Every Scale', 'Macrocosm and microcosm repeat the same divine loop.', 'Kriyācakra', 'The five acts operate in worlds, bodies, and even single moments of thought.', 'micro_macro_loop', ['microcosm','macrocosm','summary'], 'seal', 'dual loop comparison', sc07),
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
            im = cosmic_ground(SEED + hash(scene.id)%10000 + i)
            border(im)
            dust(im, SEED+i, 72)
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
    sheet = Image.new('RGB', (4*320, 2*180), color=NIGHT)
    for idx, im in enumerate(thumbs):
        x = (idx % 4)*320; y = (idx // 4)*180
        sheet.paste(im, (x,y))
    sheet.save(ROOT / 'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project': 'Tantrāloka — The Fivefold Cosmic Act (Pañcakṛtya)',
        'source_basis': 'Conceptual mapping of the fivefold act supplied by the user from Tantrāloka / Kashmir Shaiva doctrine.',
        'style': {
            'family': 'loop cosmography / divine process architecture',
            'background': 'midnight blue cosmographic field',
            'ink': 'mist and bone',
            'accent': 'gold, teal, crimson, slate, green',
            'materials': ['luminous loop arcs','veils','starburst emission','held block tension','grace aperture']
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
            }
            for sc in SCENES
        ]
    }
    (ROOT / 'scene_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    catalog = {
        'ids': [sc.id for sc in SCENES],
        'titles': {sc.id: sc.title for sc in SCENES},
        'modes': {sc.id: sc.mode for sc in SCENES},
        'theme_clusters': {
            'overview': ['pk01'],
            'individual_acts': ['pk02','pk03','pk04','pk05','pk06'],
            'cross_scale_summary': ['pk07']
        },
        'reusability_notes': {
            'pk01': 'Use for any summary of pañcakṛtya, cyclic process, or divine functions as a loop.',
            'pk02': 'Use for creation, emanation, arising, manifestation, or first emergence.',
            'pk03': 'Use for maintenance, stability, holding, structuring, or sustaining tension.',
            'pk04': 'Use for reabsorption, withdrawal, return, recollection, or interiorization.',
            'pk05': 'Use for concealment, veiling, ignorance, objectification, or separation.',
            'pk06': 'Use for grace, revelation, awakening, recognition, or opening of the veil.',
            'pk07': 'Use to show the same process operating in macrocosm and microcosm.'
        }
    }
    (ROOT / 'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Pañcakṛtya

## Aim
This pack visualizes the **fivefold cosmic act (pañcakṛtya)** as a continuous loop of divine functioning.

## Textual orientation
The pack is based on the user-supplied structural account: manifestation, stabilization, reabsorption, concealment, and revelation. It is a conceptual / visual pack, not a ritual manual.

## Core doctrinal idea
Śiva performs five functions simultaneously and continuously at every level of reality:
1. **Sṛṣṭi** — emission / manifestation
2. **Sthiti** — maintenance / support
3. **Saṃhāra** — reabsorption / withdrawal
4. **Tirodhāna** (or vilaya / concealment in the user’s wording) — obscuration of the source
5. **Anugraha** — grace / revelation / recognition

## Visual rules
- The acts should not look like isolated checklist boxes only.
- Always imply circularity and simultaneity, even in the single-act scenes.
- Creation should feel like flashing emergence.
- Maintenance should feel like held tension, not dead stasis.
- Reabsorption should feel centripetal.
- Concealment should show separation by a veil, not merely darkness.
- Grace should feel like an opening or flash, not just a generic glow.

## Style family
- midnight cosmographic ground
- mist / bone linework
- gold for emission and revelation
- teal for stability
- crimson for reabsorption and turning points
- slate for concealment
- green for beneficent disclosure

## New motifs introduced
- five-node loop wheel
- starburst emission field
- sustained central block in tension-rings
- inward reabsorption trajectories
- veil-screen and displaced object
- grace aperture / opening veil
- macrocosm–microcosm paired loops

## Guardrails
- Do not treat concealment as pure evil; it is a divine act.
- Do not treat grace as external intervention only; it is recognition of identity.
- Do not reduce the five acts to a simple temporal sequence only; they are also simultaneous.
- The same loop should be intelligible at both cosmic and psychological scales.

## Reuse strategy
- pk01: overall fivefold wheel
- pk02–pk06: individual acts
- pk07: cross-scale summary / closing seal
'''
    (ROOT / 'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Pañcakṛtya Pack

## Inheritance
This pack inherits the project’s cosmographic framing, but it shifts away from the destructive furnace tone of the Kālī pack into a cleaner, more architectural process-language.

## Pañcakṛtya differentiation
This pack emphasizes:
- circularity and recurrence
- simultaneity of divine acts
- held tension rather than collapse
- veils and apertures rather than total incineration
- macrocosm / microcosm repetition

## New motifs added
1. five-node loop wheel
2. emission starburst
3. maintenance tension-rings and held block
4. inward recollection trajectories
5. concealment veil-screen
6. grace aperture
7. cross-scale twin-loop seal

## New relationships added
- source → manifestation
- manifestation → support
- support → withdrawal
- withdrawal → concealment
- concealment → revelation
- cosmic cycle ↔ mental cycle
- macrocosm ↔ microcosm parallelism

## New material vocabulary
- midnight blue field
- mist linework
- bone-white nodes
- gold luminous apertures
- teal stability fields
- slate veils

## Deprecated clichés
- flat five-box infographic only
- generic wheel with no process-specific scene language
- making concealment simply darkness with no structural mediation

## Distinct closing seal
The closing seal is a **dual loop comparison** showing the same five acts in both macrocosm and microcosm.

## Recommendation for next packs
Strong next candidates:
- Mātṛkā / Parāparā-vāk
- Ṣaḍadhvan
- Avasthās and the five voids
- Three structural bindus / Kāmākalā
'''
    (ROOT / 'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The Fivefold Cosmic Act (Pañcakṛtya) Pack

Included files:
- pancakrtya_fivefold_act_animation.mp4
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
    (ROOT / 'README.md').write_text(readme, encoding='utf-8')


def validate_outputs():
    combined = ROOT / 'pancakrtya_fivefold_act_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT / 'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'pancakrtya_fivefold_act_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['pancakrtya_fivefold_act_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT / name, arcname=name)
        for mp4 in sorted((SCENES_ROOT).glob('*.mp4')):
            zf.write(mp4, arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering', sc.id, sc.title, flush=True)
        render_scene(sc)
    concat_file = ROOT / 'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT / (sc.id + '.mp4')).as_posix()}'" for sc in SCENES]))
    combined = ROOT / 'pancakrtya_fivefold_act_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
