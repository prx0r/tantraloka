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

# airy threshold palette
PAPER = (247, 246, 242)
PAPER_LIGHT = (251, 250, 247)
INK = (35, 41, 50)
SLATE = (102, 115, 134)
MIST = (173, 184, 197)
PALE_BLUE = (216, 227, 240)
SKY = (123, 158, 196)
DEEP_SKY = (75, 110, 149)
TEAL = (88, 148, 150)
SEA = (87, 129, 155)
GOLD = (204, 166, 91)
GOLD_LIGHT = (244, 215, 142)
CORAL = (203, 101, 90)
ROSE = (188, 122, 138)
VIOLET = (122, 110, 166)
WHITE = (252, 251, 248)
ASH = (223, 227, 233)
SMOKE = (202, 208, 215)
BLACK = (18, 20, 24)

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


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def rgba(c, a=255):
    return (*c[:3], int(a))


def ground(seed: int):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(PAPER, dtype=np.float32)
    coarse = rng.normal(0, 1, (38, 70)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse - coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32) - 128) / 128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.0 + fine[...,None]*0.9
    yy, xx = np.mgrid[0:H,0:W]
    dx = (xx-W/2)/(W/2)
    dy = (yy-H/2)/(H/2)
    vign = np.clip((dx*dx + dy*dy) * 4.3, 0, 11)
    base -= vign[...,None]*0.55
    halo = np.exp(-(((xx-W/2)/(W*0.32))**2 + ((yy-H*0.30)/(H*0.18))**2)*2.4)
    for i in range(3):
        base[...,i] += halo * (8 if i < 2 else 18)
    low = np.exp(-(((xx-W/2)/(W*0.28))**2 + ((yy-H*0.64)/(H*0.22))**2)*2.8)
    for i in range(3):
        base[...,i] += low * (10 if i == 2 else 5)
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W,H), (0,0,0,0))


def draw_glow(im, xy, radius, color, alpha=145, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
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
        draw.ellipse((x-r*0.42, y-r*0.42, x+r*0.42, y+r*0.42), fill=rgba(outer,140), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42, cy-r*0.42, cx+r*0.42, cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(SLATE,110), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,85), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d, x, y, 22, PALE_BLUE, GOLD)


def footer(im, title, subtitle, term=None):
    d = ImageDraw.Draw(im)
    y0 = H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(248,247,243,220), outline=rgba(SLATE,66), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=INK)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=SLATE)
    if term:
        tw = d.textbbox((0,0), term, font=TERM_FONT)[2]
        d.text((W-118-tw, y0+24), term, font=TERM_FONT, fill=DEEP_SKY)


def bezier(p0, p1, p2, p3, n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
        y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
        pts.append((x,y))
    return pts


def partial_polyline(points, amount):
    amount=clamp(amount)
    if amount <= 0: return []
    if amount >= 1: return points
    f=amount*(len(points)-1)
    idx=int(f); frac=f-idx
    out=list(points[:idx+1])
    if idx+1 < len(points):
        a,b=points[idx], points[idx+1]
        out.append((lerp(a[0],b[0],frac), lerp(a[1],b[1],frac)))
    return out


def draw_arrowhead(draw, p0, p1, color, scale=1.0):
    ang=math.atan2(p1[1]-p0[1], p1[0]-p0[0])
    s=12*scale
    pts=[p1,
         (p1[0]-math.cos(ang-0.5)*s, p1[1]-math.sin(ang-0.5)*s),
         (p1[0]-math.cos(ang+0.5)*s, p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts, fill=rgba(color,230))


def dust(im, seed, n=56):
    rng=np.random.default_rng(seed)
    ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(MIST, GOLD_LIGHT, rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c, int(rng.uniform(20,72))))
    im.alpha_composite(ov)


def draw_breath_capsule(draw, bbox, outline, fill=None, width=2):
    draw.rounded_rectangle(bbox, radius=(bbox[3]-bbox[1])//2, outline=rgba(outline,210), fill=fill, width=width)


def draw_hollow_node(draw, x, y, r, col, width=2):
    draw.ellipse((x-r,y-r,x+r,y+r), outline=rgba(col,220), width=width)
    draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), outline=rgba(col,180), width=1)


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


# scenes

def sc01(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 278
    # left lobe / recaka
    draw_breath_capsule(d, (170, 216, 500, 340), SKY, rgba(mix(PAPER_LIGHT,SKY,.08), 90), 2)
    draw_breath_capsule(d, (780, 216, 1110, 340), TEAL, rgba(mix(PAPER_LIGHT,TEAL,.08), 90), 2)
    d.text((335, 278), 'Recaka', font=TERM_FONT, fill=DEEP_SKY, anchor='mm')
    d.text((945, 278), 'Pūraka', font=TERM_FONT, fill=TEAL, anchor='mm')
    # central vertical stack
    for y,lab,col in [(182,'Śūnyāntara',VIOLET),(278,'Kumbhaka',GOLD),(374,'Śūnyāntara',VIOLET)]:
        draw_hollow_node(d, cx, y, 26, col, 2)
        d.text((cx+90, y-3), lab, font=SMALL_FONT, fill=col)
    # arrows
    pts = partial_polyline(bezier((500,278),(555,260),(585,248),(614,226),80), smoothstep(0.03,0.75,t))
    if len(pts)>1:
        draw_line_glow(im, pts, SKY, 3, 105, 6); draw_arrowhead(d, pts[-2], pts[-1], SKY, .9)
    pts2 = partial_polyline(bezier((780,278),(726,296),(695,308),(666,330),80), smoothstep(0.03,0.75,t))
    if len(pts2)>1:
        draw_line_glow(im, pts2, TEAL, 3, 105, 6); draw_arrowhead(d, pts2[-2], pts2[-1], TEAL, .9)
    d.line((640,208,640,352), fill=rgba(MIST,120), width=2)
    d.text((640, 504), 'linear time appears as a byproduct of the respiratory swing', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc02(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = 300, 280
    draw_glow(im, (cx,cy), 38, CORAL, 120, 12)
    d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=rgba(WHITE,255), outline=rgba(CORAL,220), width=2)
    # projective beam outward
    x1 = lerp(cx+40, 1040, ease_out_cubic(t))
    draw_line_glow(im, [(cx+20,cy), (x1,cy)], CORAL, 5, 140, 8)
    draw_arrowhead(d, (x1-36,cy), (x1,cy), CORAL, 1.2)
    for i in range(6):
        x = 600 + i*76
        y = cy + math.sin(i*0.8)*24
        r = 10 + (i%3)*3
        d.ellipse((x-r, y-r, x+r, y+r), fill=rgba(mix(CORAL, GOLD_LIGHT, i/6), 175), outline=rgba(CORAL,120))
    d.text((240, 192), 'subjective core', font=SMALL_FONT, fill=SLATE, anchor='mm')
    d.text((885, 190), 'object-field', font=SMALL_FONT, fill=SLATE, anchor='mm')
    d.text((640, 505), 'exhalation is the outward projective vector of consciousness', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc03(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # external reversal gap
    x = 980
    draw_line_glow(im, [(260,cy),(x-46,cy)], SKY, 4, 105, 7)
    draw_arrowhead(d, (x-82,cy), (x-46,cy), SKY, 1.1)
    draw_glow(im,(x,cy),56,VIOLET,95,16)
    d.ellipse((x-26,cy-26,x+26,cy+26), outline=rgba(VIOLET,220), width=2)
    d.ellipse((x-10,cy-10,x+10,cy+10), fill=rgba(WHITE,255), outline=rgba(VIOLET,180), width=2)
    d.text((x, 205), 'stambhata', font=TERM_FONT, fill=VIOLET, anchor='mm')
    d.text((x, 234), 'time stops', font=SMALL_FONT, fill=SLATE, anchor='mm')
    # returning hint
    pts = partial_polyline(bezier((x,cy+26),(x-18,cy+64),(770,cy+54),(690,cy+20),80), smoothstep(0.2,0.95,t))
    if len(pts)>1:
        draw_line_glow(im, pts, mix(VIOLET,TEAL,.5), 2, 85, 6)
    d.text((640, 505), 'at the dead-end of motion breath pauses and nondual awareness flashes', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc04(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = 980, 280
    draw_glow(im,(cx,cy),36,TEAL,120,12)
    d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=rgba(WHITE,255), outline=rgba(TEAL,220), width=2)
    x1 = lerp(cx-40, 240, ease_out_cubic(t))
    draw_line_glow(im, [(cx-20,cy), (x1,cy)], TEAL, 5, 140, 8)
    draw_arrowhead(d, (x1+36,cy), (x1,cy), TEAL, 1.2)
    for i in range(6):
        x = 340 + i*76
        y = cy + math.sin(i*0.9+1.1)*22
        r = 10 + (i%3)*3
        d.ellipse((x-r, y-r, x+r, y+r), outline=rgba(mix(TEAL,ASH,i/6),180), fill=rgba(mix(PAPER_LIGHT,TEAL,.08), 80), width=2)
    d.text((1035, 192), 'subjective core', font=SMALL_FONT, fill=SLATE, anchor='mm')
    d.text((375, 190), 'reabsorbed field', font=SMALL_FONT, fill=SLATE, anchor='mm')
    d.text((640, 505), 'inhalation strips objects of autonomy and draws them back inward', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc05(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = 300, 280
    draw_line_glow(im, [(1020,cy),(cx+46,cy)], TEAL, 4, 105, 7)
    draw_arrowhead(d, (cx+82,cy), (cx+46,cy), TEAL, 1.1)
    draw_glow(im,(cx,cy),56,VIOLET,95,16)
    d.ellipse((cx-26,cy-26,cx+26,cy+26), outline=rgba(VIOLET,220), width=2)
    d.ellipse((cx-10,cy-10,cx+10,cy+10), fill=rgba(WHITE,255), outline=rgba(VIOLET,180), width=2)
    d.text((cx, 205), 'stambhata', font=TERM_FONT, fill=VIOLET, anchor='mm')
    d.text((cx, 234), 'inner gap', font=SMALL_FONT, fill=SLATE, anchor='mm')
    pts = partial_polyline(bezier((cx,cy-26),(cx+18,cy-64),(510,cy-54),(590,cy-20),80), smoothstep(0.2,0.95,t))
    if len(pts)>1:
        draw_line_glow(im, pts, mix(VIOLET,CORAL,.55), 2, 85, 6)
    d.text((640, 505), 'the inner reversal node is another micro-stop beyond linear duration', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc06(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # opposing vectors balanced
    ptsl = partial_polyline(bezier((230,cy),(350,cy-40),(520,cy-26),(cx-24,cy),80), smoothstep(0.04,0.82,t))
    ptsr = partial_polyline(bezier((1050,cy),(930,cy+40),(760,cy+26),(cx+24,cy),80), smoothstep(0.04,0.82,t))
    if len(ptsl)>1: draw_line_glow(im, ptsl, CORAL, 4, 115, 8)
    if len(ptsr)>1: draw_line_glow(im, ptsr, TEAL, 4, 115, 8)
    draw_glow(im,(cx,cy),86,GOLD_LIGHT,125,24)
    d.ellipse((cx-30,cy-30,cx+30,cy+30), fill=rgba(WHITE,255), outline=rgba(GOLD,230), width=2)
    d.ellipse((cx-72,cy-72,cx+72,cy+72), outline=rgba(GOLD_LIGHT,145), width=2)
    d.text((cx, 196), 'zero-point equilibrium', font=TERM_FONT, fill=GOLD, anchor='mm')
    d.text((cx, 225), 'pressurized balance', font=SMALL_FONT, fill=SLATE, anchor='mm')
    d.text((640, 505), 'retention is the pressured equilibrium where inward and outward cancel', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc07(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 278
    # periodic breath creates time-axis
    d.line((180, 390, 1100, 390), fill=rgba(SLATE,120), width=2)
    for i in range(7):
        x = 210 + i*145
        d.line((x,380,x,400), fill=rgba(SLATE,140), width=2)
    d.text((1120, 390), 'kāla', font=TERM_FONT, fill=SLATE, anchor='lm')
    pts=[]
    for i in range(220):
        u=i/219
        x=lerp(190,1090,u)
        y=300 + math.sin(u*2*math.pi*2 + t*0.18)*74
        pts.append((x,y))
    draw_line_glow(im, pts, mix(SKY,TEAL,.45), 4, 115, 7)
    # mark kinks as shunyantara
    for u in [0.125,0.375,0.625,0.875]:
        x=lerp(190,1090,u)
        y=300 + math.sin(u*2*math.pi*2 + t*0.18)*74
        draw_hollow_node(d, x, y, 11, VIOLET, 2)
    d.text((640, 505), 'objective time is drawn as the periodic trace of respiration', font=SUB_FONT, fill=SLATE, anchor='mm')


def sc08(im, t):
    d = ImageDraw.Draw(im)
    cx, cy = W/2, 280
    # final seal: horizontal breath axis with central retention and two void nodes
    draw_breath_capsule(d, (250, 246, 1030, 314), mix(SKY,TEAL,.4), rgba(mix(PAPER_LIGHT,PALE_BLUE,.35), 100), 2)
    draw_line_glow(im, [(300,280),(585,280)], CORAL, 4, 120, 8)
    draw_line_glow(im, [(980,280),(695,280)], TEAL, 4, 120, 8)
    for x,col,lab in [(300,CORAL,'Recaka'),(640,GOLD,'Kumbhaka'),(980,TEAL,'Pūraka')]:
        draw_glow(im,(x,280),30,col,110,10)
        d.ellipse((x-16,264,x+16,296), fill=rgba(WHITE,255), outline=rgba(col,220), width=2)
        d.text((x, 336), lab, font=SMALL_FONT, fill=col, anchor='mm')
    for x in [505,775]:
        draw_hollow_node(d, x, 280, 14, VIOLET, 2)
        d.text((x, 336), 'Śūnyāntara', font=TINY_FONT, fill=VIOLET, anchor='mm')
    # vertical hint of awareness at center
    d.line((640,170,640,214), fill=rgba(GOLD_LIGHT,160), width=2)
    d.line((640,346,640,390), fill=rgba(GOLD_LIGHT,160), width=2)
    d.text((640, 505), 'the breath-axis as a contemplative engine of time, reversal, and pure awareness', font=SUB_FONT, fill=SLATE, anchor='mm')


SCENES = [
    Scene('pv01', 'The Breath Axis', 'An overview of exhalation, reversal nodes, inhalation, and retention.', 'Prāṇavicāra', 'The respiratory cycle is mapped as an axis generating apparent time.', 'overview_axis', ['overview','breath','axis'], 'overview', 'bilateral breath axis', sc01),
    Scene('pv02', 'Recaka', 'Exhalation as the outward projective vector.', 'Recaka', 'Consciousness projects potency outward as sensory objectivity.', 'exhalation_projection', ['recaka','projection','outward'], 'phase', 'projective beam', sc02),
    Scene('pv03', 'The External Śūnyāntara', 'The outer dead-end where motion pauses.', 'Śūnyāntara', 'At the reversal node movement ceases and the nondual substratum flashes.', 'outer_gap', ['gap','reversal','pause'], 'gap', 'outer gap pause', sc03),
    Scene('pv04', 'Pūraka', 'Inhalation as the inward reabsorptive vector.', 'Pūraka', 'The outward field is pulled back into the subjective core.', 'inhalation_reabsorption', ['puraka','inward','reabsorption'], 'phase', 'reabsorptive beam', sc04),
    Scene('pv05', 'The Internal Śūnyāntara', 'The inner dead-end where breath reverses again.', 'Śūnyāntara', 'A second reversal node exposes the same motionless awareness.', 'inner_gap', ['gap','inner','pause'], 'gap', 'inner gap pause', sc05),
    Scene('pv06', 'Kumbhaka', 'Retention as pressurized equilibrium.', 'Kumbhaka', 'Opposing vectors cancel in a zero-point of potent balance.', 'retention_equilibrium', ['kumbhaka','retention','equilibrium'], 'phase', 'opposing vector balance', sc06),
    Scene('pv07', 'Time as Breath Trace', 'Linear time emerges as the waveform of respiration.', 'Kāla', 'Objective duration is shown as the periodic trace of the respiratory swing.', 'time_trace', ['time','wave','cycle'], 'process', 'waveform time axis', sc07),
    Scene('pv08', 'The Breath Seal', 'A closing contemplative map of the full respiratory engine.', 'Prāṇa-cakra', 'The whole axis resolves into a closing contemplative seal.', 'closing_seal', ['seal','summary','breath'], 'seal', 'breath-axis seal', sc08),
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
            im = ground(SEED + hash(scene.id)%10000 + i)
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
    cols, rows = 4, 2
    sheet = Image.new('RGB', (cols*320, rows*180), color=PAPER)
    for idx,im in enumerate(thumbs):
        x=(idx%cols)*320; y=(idx//cols)*180
        sheet.paste(im,(x,y))
    sheet.save(ROOT/'contact_sheet.jpg', quality=95)


def write_metadata():
    manifest = {
        'project':'Tantrāloka — The Structure of the Breath Axis (Prāṇavicāra)',
        'source_basis':'Conceptual mapping supplied by the user from Tantrāloka Chapter 6: recaka, pūraka, kumbhaka, and śūnyāntara.',
        'style': {
            'family':'air-axis diagram / contemplative respiratory mechanics',
            'background':'clean airy field with blue threshold halos',
            'ink':'slate and deep sky',
            'accent':'coral, teal, gold, violet',
            'materials':['breath axis','gap nodes','projective beams','equilibrium core','time waveform']
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
            'overview':['pv01'],
            'phases':['pv02','pv04','pv06'],
            'gaps':['pv03','pv05'],
            'process_summary':['pv07','pv08']
        },
        'reusability_notes':{
            'pv01':'Use to introduce the whole respiratory axis or the relation between breath and time.',
            'pv02':'Use for exhalation, projection, objectification, or outward vector scenes.',
            'pv03':'Use for the outer reversal gap or motionless threshold.',
            'pv04':'Use for inhalation, reabsorption, interiorization, or return-to-source scenes.',
            'pv05':'Use for the inner reversal gap or pause inside the return movement.',
            'pv06':'Use for retention, equilibrium, suspended tension, or zero-point balance.',
            'pv07':'Use for cyclic respiration producing time or periodic waveform motifs.',
            'pv08':'Use as a closing seal for breath contemplations and prāṇavicāra doctrine.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    dossier = '''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The Structure of the Breath Axis

## Aim
This pack visualizes **Prāṇavicāra**, the doctrine that apparent objective time is generated through the oscillation of the respiratory cycle.

## Textual orientation
The pack is based on the user-supplied structural account from **Tantrāloka, Chapter 6**: recaka, pūraka, kumbhaka, and the reversal gaps called śūnyāntara.

## Core doctrinal structure represented
1. **Recaka** — exhalation / outward projective vector
2. **Śūnyāntara** — reversal gap / motionless threshold
3. **Pūraka** — inhalation / inward reabsorptive vector
4. **Śūnyāntara** — inner reversal gap
5. **Kumbhaka** — retention / zero-point equilibrium
6. **Kāla** — linear time as a byproduct or trace of the respiratory swing

## Visual rules
- Keep this pack cleaner and more axial than previous cosmographic packs.
- Exhalation should feel centrifugal and projective.
- Inhalation should feel centripetal and recollecting.
- Kumbhaka must not look inert only; it is pressurized stillness.
- The śūnyāntara nodes should appear as genuine motionless thresholds.
- The time scene should show periodicity as generated by breath, not as an independent timeline.

## Style family
- pale breathable field
- sky / teal directional flows
- coral for exhalation
- teal for inhalation
- gold for equilibrium
- violet for reversal thresholds

## New motifs introduced
- bilateral breath-axis overview
- projective exhalation beam
- outer reversal gap
- reabsorptive inhalation beam
- inner reversal gap
- pressurized equilibrium core
- waveform time trace
- breath-axis closing seal

## Guardrails
- Do not reduce the pack to mere pranayama instruction.
- The interest here is ontological and phenomenological: breath as generator of apparent time.
- The gap nodes should be theologically / contemplatively significant, not decorative pauses only.
- The final seal should summarize the axis rather than simply repeat one beam scene.

## Reuse strategy
- pv01: full architecture
- pv02 / pv04 / pv06: the three major respiratory phases
- pv03 / pv05: reversal thresholds
- pv07: relation of respiration and time
- pv08: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier, encoding='utf-8')

    style = '''# STYLE EVOLUTION — Prāṇavicāra Pack

## Inheritance
This pack inherits the contemplative diagram language of the series but becomes distinctly lighter, cleaner, and more axial.

## Prāṇavicāra differentiation
This pack emphasizes:
- respiratory oscillation
- directional vectors rather than taxonomic stacks
- pressure, reversal, and pause
- time emerging from cyclic motion
- clean airy spatial organization

## New motifs added
1. breath-axis overview
2. exhalation beam
3. outer śūnyāntara node
4. inhalation beam
5. inner śūnyāntara node
6. kumbhaka equilibrium core
7. breath waveform generating time
8. breath-axis seal

## New relationships added
- subject core → object-field projection
- object-field → subjective reabsorption
- motion → pause → reversal
- opposing respiratory vectors → equilibrium
- respiration → apparent time

## New material vocabulary
- pale breathable paper field
- sky-blue and teal axes
- coral outward pressure
- violet gap nodes
- gold center of equilibrium

## Deprecated clichés
- generic yoga-lungs iconography
- overly anatomical or medical diagram looks
- reducing kumbhaka to empty stoppage without pressure

## Distinct closing seal
The closing seal is a **horizontal breath-axis seal** showing recaka, kumbhaka, pūraka, and the two śūnyāntara nodes in one contemplative engine.

## Recommendation for next pack
Strong next candidate:
- The 12-Stage Movement of the Breath (Dvādaśānta Axis)
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style, encoding='utf-8')

    readme = f'''# Tantrāloka — The Structure of the Breath Axis (Prāṇavicāra) Pack

Included files:
- pranavicara_breath_axis_animation.mp4
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
    combined = ROOT / 'pranavicara_breath_axis_animation.mp4'
    probe = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info = json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info, indent=2))


def make_zip():
    zpath = ROOT / 'pranavicara_breath_axis_pack.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ['pranavicara_breath_axis_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    combined = ROOT / 'pranavicara_breath_axis_animation.mp4'
    if not combined.exists() or combined.stat().st_size < 100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)], check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__ == '__main__':
    render_all()
