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
SEED = 40440

# Palette: luminous manuscript / sound cosmography
PARCHMENT = (243, 238, 228)
PARCHMENT_LIGHT = (249, 246, 239)
IVORY = (252, 250, 245)
INK = (33, 36, 48)
UMBER = (88, 75, 61)
INDIGO = (69, 78, 136)
DEEP_INDIGO = (46, 54, 95)
SLATE = (112, 124, 147)
GOLD = (203, 164, 88)
GOLD_LIGHT = (242, 215, 142)
SAFFRON = (226, 154, 52)
CORAL = (198, 92, 85)
ROSE = (188, 109, 138)
TEAL = (96, 148, 150)
GREEN = (105, 151, 110)
SMOKE = (170, 173, 183)
WHITE = (252, 250, 246)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_BIG = ImageFont.truetype(FONT_DEVA, 38)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)

VOWELS = ['अ','आ','इ','ई','उ','ऊ','ऋ','ॠ','ऌ','ए','ऐ','ओ','औ','अं','अः']
CONSONANTS = ['क','ख','ग','घ','ङ','च','छ','ज','झ','ञ','ट','ठ','ड','ढ','ण','त','थ','द','ध','न','प','फ','ब','भ','म','य','र','ल','व','श','ष','स','ह']
WORDS = ['शिव','शक्ति','स्पन्द','वाक्','मन्त्र','तत्त्व','विश्व','भैरव']


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
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None] * 4.2 + fine[...,None] * 1.2
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*6,0,16)
    base -= vign[...,None]*0.8
    # soft indigo halo upper center
    halo = np.exp(-(((xx-W/2)/(W*0.26))**2 + ((yy-H*0.30)/(H*0.18))**2)*2.5)
    for i,v in enumerate((INDIGO[0], INDIGO[1], INDIGO[2])):
        base[...,i] += halo * (8 if i<2 else 18)
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
        a = 2*math.pi*i/8
        x = cx + math.cos(a)*r*0.62
        y = cy + math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,150), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,125), outline=rgba(outer,220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(UMBER, 125), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD, 90), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, ROSE, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(247,244,237,214), outline=rgba(UMBER,75), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=INK)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=UMBER)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=INDIGO)


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


def arc_points(cx, cy, rx, ry, a0, a1, n=90):
    return [(cx + math.cos(lerp(a0,a1,i/(n-1)))*rx, cy + math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


def dust(im, seed, n=55):
    rng = np.random.default_rng(seed)
    ov = layer(); d = ImageDraw.Draw(ov)
    for _ in range(n):
        x = float(rng.uniform(120, W-120)); y = float(rng.uniform(120, H-180))
        r = float(rng.uniform(1, 2.2))
        c = mix(SMOKE, GOLD_LIGHT, rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c, int(rng.uniform(30,85))))
    im.alpha_composite(ov)


def draw_wave_band(im, bbox, lines=8, amp=16, color=INDIGO, phase=0.0, alpha=100):
    x0,y0,x1,y1 = bbox
    ov = layer(); d = ImageDraw.Draw(ov)
    for i in range(lines):
        yy = lerp(y0,y1,i/(lines-1 if lines>1 else 1))
        pts=[]
        for j in range(90):
            u=j/89
            x = lerp(x0,x1,u)
            y = yy + math.sin(u*2*math.pi*2 + phase + i*0.35) * amp * math.sin(math.pi*i/max(1,lines-1))
            pts.append((x,y))
        d.line(pts, fill=rgba(color, alpha), width=2)
    ov = ov.filter(ImageFilter.GaussianBlur(1.5))
    im.alpha_composite(ov)


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang = math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s = 12*scale
    pts = [p1,
           (p1[0]-math.cos(ang-0.5)*s, p1[1]-math.sin(ang-0.5)*s),
           (p1[0]-math.cos(ang+0.5)*s, p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts, fill=rgba(color,230))


def draw_seed_symbol(draw, cx, cy, scale=1.0, color=GOLD_LIGHT):
    # stylized bindu in crescent
    draw.arc((cx-52*scale, cy-22*scale, cx+52*scale, cy+28*scale), 190, 350, fill=rgba(color,220), width=max(1,int(3*scale)))
    draw.ellipse((cx-9*scale, cy-36*scale, cx+9*scale, cy-18*scale), fill=rgba(color,230))


def draw_speech_ring(draw, cx, cy, r, letters, phase=0.0, color=INDIGO, font=None):
    font = font or DEVA_SMALL
    n = len(letters)
    for i,ch in enumerate(letters):
        a = -math.pi/2 + phase + i*2*math.pi/n
        x = cx + math.cos(a)*r
        y = cy + math.sin(a)*(r*0.78)
        draw.text((x,y), ch, font=font, fill=color, anchor='mm')


def draw_cell(draw, x, y, w, h, label, col):
    draw.rounded_rectangle((x,y,x+w,y+h), radius=14, outline=rgba(col,180), width=2, fill=rgba(mix(PARCHMENT_LIGHT,col,.05), 70))
    draw.text((x+w/2, y+h/2), label, font=DEVA_MED if len(label) < 3 else SMALL_FONT, fill=col, anchor='mm')


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


# ---- Scene functions ----

def sc01(im, t):
    d = ImageDraw.Draw(im)
    cx = W/2
    ys = [145, 235, 330, 432]
    labels = [('Parā', GOLD_LIGHT), ('Paśyantī', ROSE), ('Madhyamā', TEAL), ('Vaikharī', INDIGO)]
    for i,((lab,col),y) in enumerate(zip(labels, ys)):
        rx = 56 + i*88
        ry = 18 + i*20
        d.arc((cx-rx, y-ry, cx+rx, y+ry), 185, 355, fill=rgba(col, 180), width=2)
        d.text((cx+220, y-4), lab, font=TERM_FONT, fill=col)
        if i < 3:
            pts = partial_polyline(bezier((cx, y+ry+8), (cx-20, y+45), (cx+20, ys[i+1]-42), (cx, ys[i+1]-20), 80), smoothstep(0.05,0.85,t))
            if len(pts) > 1: draw_line_glow(im, pts, mix(col, labels[i+1][1], .5), 3, 110, 6)
    draw_seed_symbol(d, cx, 112, 0.7, GOLD_LIGHT)
    d.text((640, 515), 'the descent of speech from silence to sound', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 250
    draw_glow(im, (cx, cy), 82, GOLD_LIGHT, 120, 22)
    for r,col in [(42,GOLD_LIGHT),(86,GOLD),(132,mix(GOLD,SMOKE,.4))]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(col,140), width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    draw_seed_symbol(d, cx, 360, 1.1, GOLD)
    d.text((cx, 430), 'अ', font=DEVA_BIG, fill=rgba(DEEP_INDIGO, 220), anchor='mm')
    d.text((640, 500), 'undivided vibration before any inner distinction', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    star = []
    for i in range(12):
        a = -math.pi/2 + i*2*math.pi/12
        star.append((cx + math.cos(a)*90, cy + math.sin(a)*62))
    for p in star:
        draw_line_glow(im, [(cx,cy), p], ROSE, 2, 90, 5)
        d.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5), fill=rgba(ROSE, 200))
    draw_glow(im,(cx,cy),55,ROSE,100,16)
    d.ellipse((cx-15,cy-15,cx+15,cy+15), fill=rgba(WHITE,255), outline=rgba(ROSE,220), width=2)
    # inner flash of intent
    pts = arc_points(cx, cy, 200, 110, -math.pi*0.95, math.pi*0.1 + t*0.15, 100)
    draw_line_glow(im, pts, mix(ROSE, GOLD_LIGHT, .5), 3, 110, 6)
    draw_speech_ring(d, cx, cy, 205, ['बीज','भाव','इच्छा','दर्शन'], phase=t*0.1, color=ROSE, font=DEVA_SMALL)


def sc04(im, t):
    d = ImageDraw.Draw(im)
    x0,y0 = 260, 160
    cellw, cellh = 94, 74
    letters = VOWELS[:4] + CONSONANTS[:8]
    cols = [GOLD, ROSE, TEAL, INDIGO] * 3
    for idx, ch in enumerate(letters):
        r = idx // 4
        c = idx % 4
        x = x0 + c*170
        y = y0 + r*100
        draw_cell(d, x, y, cellw, cellh, ch, cols[idx])
    # connecting mental blueprint lines
    for r in range(3):
        y = y0 + r*100 + cellh/2
        pts = partial_polyline([(x0+cellw, y), (x0+3*170, y)], smoothstep(0.1,0.95,t))
        if len(pts)>1: draw_line_glow(im, pts, SLATE, 2, 75, 5)
    d.text((925, 225), 'letters separate', font=TERM_FONT, fill=TEAL)
    d.text((925, 260), 'patterns combine', font=TERM_FONT, fill=INDIGO)
    d.text((925, 295), 'mantras form', font=TERM_FONT, fill=ROSE)
    d.text((925, 330), 'blueprints stabilize', font=TERM_FONT, fill=GOLD)


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 255
    draw_wave_band(im, (200, 145, 1080, 365), 10, 18, color=INDIGO, phase=t*2*math.pi, alpha=95)
    # syllables to audible waves
    syllables = ['अ','क','श','ति','व','हं']
    for i,ch in enumerate(syllables):
        x = 250 + i*155
        d.ellipse((x-32, 410-32, x+32, 410+32), outline=rgba(mix(INDIGO, GOLD, i/6),180), fill=rgba((245,244,240),70), width=2)
        d.text((x,410), ch, font=DEVA_MED, fill=mix(DEEP_INDIGO, CORAL, i/6), anchor='mm')
        pts = partial_polyline(bezier((x,378), (x,345), (x,310), (x,250+math.sin(i)*5), 80), smoothstep(0.05,0.8,t))
        if len(pts)>1: draw_line_glow(im, pts, mix(INDIGO, GOLD, i/6), 2, 90, 5)
    d.text((640, 505), 'speech becomes vibratory and materially audible', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    boxes = [
        (145, 248, 140, 84, 'अ', GOLD_LIGHT),
        (385, 248, 150, 84, 'अग्नि', ROSE),
        (655, 248, 170, 84, 'मन्त्र', TEAL),
        (955, 232, 150, 116, '☀', SAFFRON),
    ]
    for x,y,w,h,label,col in boxes:
        d.rounded_rectangle((x,y,x+w,y+h), radius=16, outline=rgba(col, 190), fill=rgba(mix(PARCHMENT_LIGHT,col,.05), 70), width=2)
        d.text((x+w/2, y+h/2), label, font=DEVA_BIG if label=='अ' else (DEVA_MED if any(ord(c)>1000 for c in label) else TERM_FONT), fill=col, anchor='mm')
    captions = ['vibration','phoneme','word / image','material form']
    for i,(x,y,w,h,_,col) in enumerate(boxes):
        d.text((x+w/2, y+h+24), captions[i], font=SMALL_FONT, fill=UMBER, anchor='mm')
    for i in range(len(boxes)-1):
        p0 = (boxes[i][0]+boxes[i][2], boxes[i][1]+boxes[i][3]/2)
        p1 = (boxes[i+1][0], boxes[i+1][1]+boxes[i+1][3]/2)
        pts = partial_polyline(bezier(p0, (p0[0]+55,p0[1]), (p1[0]-55,p1[1]), p1, 80), smoothstep(0.05+i*0.12,0.7+i*0.12,t))
        if len(pts)>1:
            draw_line_glow(im, pts, mix(boxes[i][5], boxes[i+1][5], .5), 3, 115, 7)
            draw_arrowhead(d, pts[-2], pts[-1], mix(boxes[i][5], boxes[i+1][5], .5), 0.9)
    d.text((640, 520), 'unmanifest sound condenses into name and world', font=SUB_FONT, fill=UMBER, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 282
    for r,col in [(210,INDIGO),(170,TEAL),(128,ROSE),(88,GOLD)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(col,150), width=2)
    # outer ring vowels, inner ring consonants sample, center bindu
    draw_speech_ring(d, cx, cy, 212, VOWELS[:12], phase=t*0.12, color=INDIGO, font=DEVA_SMALL)
    draw_speech_ring(d, cx, cy, 170, CONSONANTS[:20], phase=-t*0.1, color=TEAL, font=DEVA_SMALL)
    # mantra petals
    for i,w in enumerate(['ॐ','ह्रीं','श्रीं','क्लीं','हं','सौः']):
        a = -math.pi/2 + i*2*math.pi/6
        x = cx + math.cos(a)*90
        y = cy + math.sin(a)*64
        d.ellipse((x-28,y-28,x+28,y+28), outline=rgba(ROSE,180), fill=rgba((255,240,245),55), width=2)
        d.text((x,y), w, font=DEVA_MED, fill=ROSE, anchor='mm')
    draw_glow(im, (cx,cy), 38, GOLD_LIGHT, 130, 12)
    d.ellipse((cx-14,cy-14,cx+14,cy+14), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((640, 515), 'the matrix of sound resolves into a contemplative seal', font=SUB_FONT, fill=UMBER, anchor='mm')


SCENES = [
    Scene('mt01', 'The Four Levels of Speech', 'An overview of the descent from silent source to audible language.', 'Vāk-catuṣṭaya', 'Speech descends through four ontological levels.', 'four_levels_overview', ['overview','speech','vāk'], 'overview', 'tiered descent overview', sc01),
    Scene('mt02', 'Parā Vāk', 'Undifferentiated, silent vibration at the source.', 'Parā Vāk', 'Supreme speech abides as undivided power before expression.', 'para_silence', ['source','silence','parā'], 'level', 'luminous bindu and seed', sc02),
    Scene('mt03', 'Paśyantī Vāk', 'The universe appears as a single visionary flash.', 'Paśyantī Vāk', 'Speech is seen inwardly as a unitary intuition or intent.', 'pasyanti_flash', ['visionary','intent','pasyanti'], 'level', 'inner flash and orbit ring', sc03),
    Scene('mt04', 'Madhyamā Vāk', 'Letters, formulas, and mental blueprints separate inwardly.', 'Madhyamā Vāk', 'The inner mental matrix divides into formal articulations.', 'madhyama_matrix', ['letters','matrix','madhyama'], 'level', 'cell-grid blueprint', sc04),
    Scene('mt05', 'Vaikharī Vāk', 'Speech emerges as audible wave and articulated syllable.', 'Vaikharī Vāk', 'Gross utterance appears as sound moving through matter.', 'vaikhari_wave', ['sound','gross speech','vaikhari'], 'level', 'wave-band and syllable channel', sc05),
    Scene('mt06', 'From Vibration to Matter', 'Phoneme, word, mantra, and world form one condensation chain.', 'Mātṛkā', 'The universe condenses out of sound and linguistic structure.', 'condensation_chain', ['sound matrix','condensation','world'], 'process', 'box-chain transformation', sc06),
    Scene('mt07', 'The Sound Matrix Seal', 'The alphabetic cosmos gathers into one contemplative ring.', 'Mātṛkā-cakra', 'The manifold of speech resolves into a closing sound cosmogram.', 'closing_seal', ['seal','alphabet','mantra'], 'seal', 'alphabetic cosmogram', sc07),
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
            dust(im, SEED+i, 48)
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
        'project':'Tantrāloka — The Sound Matrix (Mātṛkā / Parāparā-vāk)',
        'source_basis':'Conceptual mapping of the sound matrix and four levels of speech supplied by the user from Tantrāloka / Kashmir Shaiva doctrine.',
        'style': {
            'family':'luminous manuscript sound cosmography',
            'background':'pale parchment with indigo halo',
            'ink':'indigo / umber',
            'accent':'gold, rose, teal, saffron',
            'materials':['bindu glow','speech rings','letter cells','wave bands','alphabetic cosmogram']
        },
        'fps': FPS,
        'resolution': [W,H],
        'scene_duration_seconds': DURATION,
        'total_scenes': len(SCENES),
        'total_duration_seconds': round(len(SCENES)*DURATION, 2),
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
            'overview':['mt01'],
            'four_levels':['mt02','mt03','mt04','mt05'],
            'condensation_process':['mt06'],
            'closing_seal':['mt07']
        },
        'reusability_notes':{
            'mt01':'Use to introduce the four levels of speech or the full descent of sound.',
            'mt02':'Use for silence, source, undifferentiated vibration, or pure seed consciousness.',
            'mt03':'Use for inner flash, visionary intent, or unitary pre-discursive seeing.',
            'mt04':'Use for mental blueprint, letters, inner language, or mantra-forming cognition.',
            'mt05':'Use for gross speech, sound waves, utterance, or audible manifestation.',
            'mt06':'Use for phoneme-to-world sequences, linguistic ontology, or sound condensation.',
            'mt07':'Use as a closing seal for alphabet cosmology, mantra systems, or mātṛkā diagrams.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The Sound Matrix

## Aim
This pack visualizes the **Sound Matrix (Mātṛkā / Parāparā-vāk)** and the descent of speech from silent source to audible manifestation.

## Textual orientation
The pack is based on the user-supplied structural account: unmanifest vibration condensing into phonemic, mental, and vocalized structures, culminating in worldly manifestation. It is conceptual and visual rather than philological.

## Core doctrinal structure represented
1. **Parā Vāk** — supreme undivided speech / silent vibration
2. **Paśyantī Vāk** — unitary visionary flash of intent
3. **Madhyamā Vāk** — inner differentiation of letters, formulas, and structures
4. **Vaikharī Vāk** — gross audible speech
5. **Mātṛkā** — the alphabetic matrix as a cosmological generator

## Visual rules
- Keep the pack lighter and more luminous than the Kālī or Pañcakṛtya packs.
- Use letters and sound as living structure, not as flat textbook typography only.
- Parā should feel undivided and silent.
- Paśyantī should feel unitary but already intentional.
- Madhyamā should show differentiation and combinability.
- Vaikharī should show sound becoming physically wave-like and articulated.
- The final seal should present the alphabetic cosmos as a contemplative ring.

## Style family
- pale parchment background
- indigo manuscript linework
- gold luminous source
- rose visionary accents
- teal matrix order
- saffron for the transition toward materialization

## New motifs introduced
- four-level tiered descent
- bindu-seed glyph
- visionary flash wheel
- letter-cell blueprints
- syllable-to-wave channels
- condensation chain from phoneme to world
- alphabetic cosmogram seal

## Guardrails
- Do not reduce the doctrine to modern linguistics only.
- Do not treat letters as arbitrary marks; they are ontological operators in this framework.
- Avoid crowded scholastic tables; keep the diagrams contemplative and legible.
- The pack should remain about manifestation through speech, not merely about grammar.

## Reuse strategy
- mt01: full overview
- mt02–mt05: the four levels of speech
- mt06: sound-to-world condensation
- mt07: closing sound matrix seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Sound Matrix Pack

## Inheritance
This pack keeps the project’s contemplative diagrammatic clarity while shifting into a cleaner, lighter, more manuscript-and-phoneme aesthetic.

## Mātṛkā differentiation
This pack emphasizes:
- luminous speech descent
- alphabets as cosmological structure
- letter cells and wave-bands
- pale parchment and indigo precision
- bindu and mantra rings instead of destructive or cyclical energies

## New motifs added
1. four-level speech descent ladder
2. silent bindu-seed glyph
3. visionary flash ring
4. letter-cell matrix
5. audible wave-band
6. condensation chain
7. alphabetic cosmogram seal

## New relationships added
- silence → inner vision
- inner vision → mental differentiation
- mental differentiation → audible utterance
- phoneme → word / mantra → world
- source bindu ↔ alphabet ring

## New material vocabulary
- pale parchment
- indigo manuscript ink
- gold source-light
- rose visionary glow
- teal structural matrices
- saffron materialization accents

## Deprecated clichés
- flat alphabet charts with no ontological drama
- generic sound wave stock icon look
- over-cluttered Sanskrit pedagogy grids

## Distinct closing seal
The closing seal is an **alphabetic cosmogram**: vowels, consonants, and mantric seeds gathered around a luminous bindu.

## Recommendation for next packs
Strong next candidates:
- Ṣaḍadhvan
- Avasthās & the five voids
- Three structural bindus / Kāmākalā
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The Sound Matrix (Mātṛkā / Parāparā-vāk) Pack

Included files:
- matrika_sound_matrix_animation.mp4
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
    combined = ROOT / 'matrika_sound_matrix_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'matrika_sound_matrix_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['matrika_sound_matrix_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    combined = ROOT / 'matrika_sound_matrix_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()


if __name__ == '__main__':
    render_all()
