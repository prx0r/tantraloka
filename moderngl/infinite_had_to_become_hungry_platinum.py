#!/usr/bin/env python3
"""
THE INFINITE HAD TO BECOME HUNGRY
An original Platinum-house procedural visual essay.

CORE THESIS
-----------
If consciousness is unlimited, why appear as a finite biological organism with
hunger, fear, desire, memory, and pain?

This film proposes a disciplined answer rather than a proof:

An unlimited field cannot encounter anything as other.
To produce perspective, it must contract.
To preserve contraction, it must draw a boundary.
A living boundary must regulate exchange.
Regulated exchange creates need.
Need creates value.
Value creates action.
Action creates a world.
A remembered world creates a self.
A threatened self creates suffering.
Recognition does not erase the organism.
It reveals the finite life as one local mode of the same field that became it.

VISUAL THESIS
-------------
One gold pulse survives every stage:
field → boundary → gradient → metabolism → hunger → action → prediction →
identity → suffering → recognition.

HOUSE RULES
-----------
• Every scene lasts 5–10 seconds.
• Every scene performs one visible metaphysical or biological transformation.
• White gallery/scientific field; black only where conceptually necessary.
• No static slide layouts.
• Sparse labels only.
• Every mature frame near u=0.72 should work as a still.
• Continuity object: a gold pulse that changes carrier but never disappears.

PALETTE ROLES
-------------
IVORY    open field / unclaimed possibility
GOLD     luminous continuity / recognition
CYAN     boundary / regulation / perception
GREEN    metabolism / viable action
CRIMSON  threat / suffering / defensive contraction
VIOLET   memory / latent possibility / interior depth
INK      fixed form / determination

OUTPUT
------
output_infinite_hungry/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  infinite_had_to_become_hungry.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python infinite_had_to_become_hungry_platinum.py
python infinite_had_to_become_hungry_platinum.py --preview
python infinite_had_to_become_hungry_platinum.py --scene 12
python infinite_had_to_become_hungry_platinum.py --fps 12 --width 1920 --height 1080
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


# =============================================================================
# CONFIG
# =============================================================================

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_infinite_hungry"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 10

IVORY = (249, 247, 241)
WHITE = (255, 254, 250)
INK = (29, 33, 39)
SOFT_INK = (86, 91, 98)
SILVER = (180, 187, 194)
PALE_SILVER = (226, 229, 232)
CYAN = (57, 156, 180)
PALE_CYAN = (196, 227, 233)
DEEP_CYAN = (34, 101, 129)
GOLD = (194, 156, 72)
PALE_GOLD = (236, 219, 175)
GREEN = (70, 139, 99)
PALE_GREEN = (198, 225, 208)
CRIMSON = (162, 58, 69)
PALE_CRIMSON = (231, 198, 202)
VIOLET = (109, 83, 153)
PALE_VIOLET = (220, 211, 237)
VOID = (24, 28, 34)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# =============================================================================
# HELPERS
# =============================================================================

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t)


def mix(a, b, t):
    t = clamp(t)
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a))
    return q * q * (3.0 - 2.0 * q)


def ease(t: float) -> float:
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def pulse(t: float, speed: float = 1.0, phase: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin(math.tau * (speed * t + phase))


def load_font(path: str, size: int):
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def field(w: int, h: int, seed: int, dark: bool = False) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = VOID if dark else IVORY
    arr = np.empty((h, w, 3), dtype=np.float32)
    arr[:] = base
    arr += rng.normal(0, 0.9 if not dark else 1.4, (h, w, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    halo = np.exp(-(((xx - w * 0.5) / (w * 0.37)) ** 2
                    + ((yy - h * 0.40) / (h * 0.31)) ** 2) * 2.0)
    if dark:
        arr[..., 0] += halo * 3.0
        arr[..., 1] += halo * 7.0
        arr[..., 2] += halo * 10.0
    else:
        arr[..., 1] += halo * 3.4
        arr[..., 2] += halo * 5.0
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def centered(draw, xy, text, fnt, fill=INK):
    draw.text(xy, text, font=fnt, fill=fill, anchor="mm")


def seal(im, title, subtitle="", color=INK):
    w, h = im.size
    d = ImageDraw.Draw(im)
    centered(d, (w / 2, h * 0.875), title,
             load_font(FONT_SERIF_BOLD, max(22, int(h * 0.04))), color)
    if subtitle:
        centered(d, (w / 2, h * 0.923), subtitle,
                 load_font(FONT_SANS, max(13, int(h * 0.019))), SOFT_INK)


def border(im, dark=False):
    w, h = im.size
    d = ImageDraw.Draw(im)
    c = WHITE if dark else INK
    d.rounded_rectangle((26, 26, w - 26, h - 26), radius=18,
                        outline=(*c, 45), width=2)


def glow_circle(im, x, y, r, color, alpha=170, blur=14):
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.ellipse((x - r, y - r, x + r, y + r), fill=(*color, alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).ellipse(
        (x - r * 0.34, y - r * 0.34, x + r * 0.34, y + r * 0.34),
        fill=(*mix(color, WHITE, 0.35), min(255, alpha + 50)),
    )
    im.alpha_composite(fg)


def glow_line(im, pts, color, width=4, alpha=210, blur=11):
    if len(pts) < 2:
        return
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.line(pts, fill=(*color, alpha), width=width * 3, joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).line(
        pts,
        fill=(*mix(color, WHITE, 0.08), min(255, alpha + 25)),
        width=width,
        joint="curve",
    )
    im.alpha_composite(fg)


def partial(pts, amount):
    if not pts:
        return []
    amount = clamp(amount)
    if amount >= 1:
        return pts
    target = amount * (len(pts) - 1)
    idx = int(target)
    frac = target - idx
    out = list(pts[:idx + 1])
    if idx + 1 < len(pts):
        a, b = pts[idx], pts[idx + 1]
        out.append((lerp(a[0], b[0], frac), lerp(a[1], b[1], frac)))
    return out


def arrow(draw, a, b, color=INK, width=3, head=10):
    draw.line((*a, *b), fill=color, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        p = (
            b[0] - math.cos(ang + s * 0.52) * head,
            b[1] - math.sin(ang + s * 0.52) * head,
        )
        draw.line((*b, *p), fill=color, width=width)


def draw_cell(draw, cx, cy, r, membrane=CYAN, fill_color=PALE_CYAN, alpha=220):
    draw.ellipse((cx-r, cy-r, cx+r, cy+r),
                 fill=(*fill_color, alpha//2),
                 outline=(*membrane, alpha), width=4)


def draw_body(draw, cx, cy, scale=1.0, color=INK, alpha=220):
    draw.ellipse((cx-28*scale, cy-145*scale, cx+28*scale, cy-89*scale),
                 outline=(*color, alpha), width=max(2, int(4*scale)))
    draw.line((cx, cy-89*scale, cx, cy+55*scale),
              fill=(*color, alpha), width=max(3, int(6*scale)))
    draw.line((cx-70*scale, cy-55*scale, cx+70*scale, cy-55*scale),
              fill=(*color, alpha), width=max(3, int(5*scale)))
    draw.line((cx-70*scale, cy-55*scale, cx-145*scale, cy+15*scale),
              fill=(*color, alpha), width=max(3, int(5*scale)))
    draw.line((cx+70*scale, cy-55*scale, cx+145*scale, cy+15*scale),
              fill=(*color, alpha), width=max(3, int(5*scale)))
    draw.line((cx, cy+55*scale, cx-55*scale, cy+160*scale),
              fill=(*color, alpha), width=max(3, int(5*scale)))
    draw.line((cx, cy+55*scale, cx+55*scale, cy+160*scale),
              fill=(*color, alpha), width=max(3, int(5*scale)))


def radial_field(cx, cy, r, count=140, phase=0.0):
    pts = []
    for i in range(count):
        q = i / (count - 1)
        a = q * math.tau * 2.2 + phase
        rr = r * (0.1 + 0.9 * q)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.62))
    return pts


# =============================================================================
# VISUALS
# =============================================================================

def vis_unbounded_field(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w * .50, h * .40
    q = ease(u)
    for rr in range(35, 300, 30):
        d.ellipse((cx-rr, cy-rr*.62, cx+rr, cy+rr*.62),
                  outline=(*GOLD, int(85*q*(1-rr/330))), width=3)
    glow_circle(im, cx, cy, 18, GOLD, int(140+70*q), 14)
    seal(im, "WITHOUT A BOUNDARY, NOTHING CAN BE OTHER",
         "an unlimited field has no outside from which to encounter itself", GOLD)


def vis_first_contraction(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    q = ease(u)
    outer = lerp(260, 95, q)
    d.ellipse((cx-outer, cy-outer*.62, cx+outer, cy+outer*.62),
              outline=(*CYAN, 210), width=5)
    for rr in range(40, 250, 35):
        alpha = int(70*(1-q)*(1-rr/270))
        d.ellipse((cx-rr, cy-rr*.62, cx+rr, cy+rr*.62),
                  outline=(*GOLD, alpha), width=2)
    glow_circle(im, cx, cy, 14, GOLD, 180, 12)
    seal(im, "THE FIRST CREATIVE ACT IS CONTRACTION",
         "perspective begins when possibility accepts a center")


def vis_membrane(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    q = ease(u)
    r = lerp(40, 150, q)
    draw_cell(d, cx, cy, r, CYAN, PALE_CYAN, 220)
    # inside/outside particles separate
    rng = random.Random(11)
    for i in range(80):
        a = rng.random()*math.tau
        rr = rng.uniform(20, 250)
        x = cx + math.cos(a)*rr
        y = cy + math.sin(a)*rr*.62
        inside = rr < r
        col = GOLD if inside else VIOLET
        alpha = 150 if q > .25 else 80
        d.ellipse((x-3,y-3,x+3,y+3), fill=(*col,alpha))
    seal(im, "A LIVING CENTER NEEDS A MEMBRANE",
         "the boundary does not end relation; it regulates relation")


def vis_gradient(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    draw_cell(d, cx, cy, 150, CYAN, PALE_CYAN, 215)
    q = ease(u)
    # gradient
    for i in range(80):
        x = lerp(cx-140, cx+140, i/79)
        intensity = i/79
        d.line((x, cy-120, x, cy+120),
               fill=(*mix(VIOLET, GOLD, intensity), int(35+80*q)), width=3)
    # flow
    pts = [(cx-105,cy),(cx-35,cy-35),(cx+35,cy+15),(cx+110,cy)]
    glow_line(im, partial(pts,q), GREEN, 5, 210, 13)
    seal(im, "A BOUNDARY CREATES A GRADIENT",
         "inside and outside become unequal—and inequality becomes usable")


def vis_metabolism(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    draw_cell(d, cx, cy, 150, CYAN, PALE_GREEN, 215)
    q = ease(u)
    # circulating metabolic loop
    pts=[]
    for i in range(180):
        a=i/179*math.tau
        r=95+18*math.sin(a*3+t*.7)
        pts.append((cx+math.cos(a)*r, cy+math.sin(a)*r*.62))
    glow_line(im, partial(pts,q), GREEN, 5, 210, 13)
    for i in range(12):
        a=i*math.tau/12+t*.4
        x=cx+math.cos(a)*65
        y=cy+math.sin(a)*40
        glow_circle(im,x,y,7,GOLD,130,8)
    seal(im, "LIFE IS A BOUNDARY THAT MUST KEEP WORKING",
         "metabolism is the cost of maintaining a difference")


def vis_hunger(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.42, h*.40
    draw_cell(d, cx, cy, 120, CYAN, PALE_GREEN, 210)
    q = ease(u)
    target=(w*.75,h*.40)
    glow_circle(im,*target,18,GOLD,180,12)
    # cell depletes and bends toward target
    for i in range(8):
        a=i*math.tau/8
        x=cx+math.cos(a)*70
        y=cy+math.sin(a)*44
        alpha=int(170*(1-q*.65))
        d.ellipse((x-5,y-5,x+5,y+5),fill=(*GREEN,alpha))
    glow_line(im,partial([(cx+90,cy),(w*.58,h*.33),target],q),GOLD,5,210,13)
    seal(im, "THE MOMENT A BOUNDARY MUST CONTINUE, HUNGER APPEARS",
         "need is not an accident added to life; it is the price of persistence")


def vis_value(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    q=ease(u)
    items=[("FOOD",GREEN,-190,-70),("POISON",CRIMSON,190,-70),
           ("SHELTER",CYAN,-190,100),("THREAT",CRIMSON,190,100)]
    for i,(lab,col,ox,oy) in enumerate(items):
        local=clamp(q*len(items)-i)
        x,y=cx+ox,cy+oy
        glow_circle(im,x,y,12,col,150,9)
        centered(d,(x,y+30),lab,load_font(FONT_SANS_BOLD,15),col)
        arrow(d,(cx,cy),(x,y),(*col,int(120*local)),2,7)
    glow_circle(im,cx,cy,15,GOLD,180,11)
    seal(im, "NEED CREATES VALUE",
         "the world divides into what sustains, what threatens, and what can be ignored")


def vis_action_world(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.28,h*.42
    q=ease(u)
    draw_cell(d,cx,cy,70,CYAN,PALE_GREEN,210)
    targets=[(w*.72,h*.25,GREEN),(w*.74,h*.58,CRIMSON),(w*.60,h*.42,GOLD)]
    for x,y,col in targets:
        glow_circle(im,x,y,12,col,150,9)
    path=[(cx+60,cy),(w*.45,h*.35),(w*.60,h*.42)]
    glow_line(im,partial(path,q),GOLD,5,210,13)
    seal(im,"VALUE CREATES ACTION",
         "a world becomes real wherever movement can succeed or fail")


def vis_prediction(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # predicted arc
    pred=[]
    actual=[]
    for i in range(160):
        x=lerp(w*.15,w*.85,i/159)
        pred.append((x,cy-60*math.sin(i/159*math.pi)))
        actual.append((x,cy-25*math.sin(i/159*math.pi*1.3+t*.1)))
    d.line(pred,fill=(*VIOLET,150),width=4)
    glow_line(im,partial(actual,q),CYAN,5,200,12)
    # errors
    for i in range(12):
        idx=int(i*(len(pred)-1)/11)
        if q>i/12:
            d.line((*pred[idx],*actual[idx]),fill=(*CRIMSON,150),width=2)
    seal(im,"ACTION REQUIRES A FUTURE",
         "prediction turns present sensation into preparation")


def vis_nervous_system(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    rng=random.Random(54)
    nodes=[(rng.uniform(w*.18,w*.82),rng.uniform(h*.18,h*.66)) for _ in range(48)]
    for i,(x,y) in enumerate(nodes):
        d.ellipse((x-5,y-5,x+5,y+5),fill=(*PALE_CYAN,220),outline=(*CYAN,140))
        if i>0 and i%2:
            px,py=nodes[i-1]
            d.line((px,py,x,y),fill=(*SILVER,80),width=2)
    wave_x=lerp(w*.15,w*.85,q)
    gl=layer(im.size)
    gd=ImageDraw.Draw(gl)
    gd.rectangle((wave_x-25,h*.15,wave_x+25,h*.68),fill=(*GOLD,50))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18)))
    seal(im,"NERVOUS SYSTEMS MAKE NEED FAST",
         "the organism begins modelling what has not happened yet")


def vis_memory_self(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    y=h*.40
    xs=[w*.18,w*.34,w*.50,w*.66,w*.82]
    q=ease(u)
    for i,x in enumerate(xs):
        glow_circle(im,x,y,14,[CYAN,VIOLET,GREEN,CRIMSON,CYAN][i],160,9)
    glow_line(im,partial([(x,y) for x in xs],q),GOLD,5,220,13)
    if q>.62:
        centered(d,(w*.50,h*.66),"ONE LIFE",load_font(FONT_SERIF_BOLD,29),GOLD)
    seal(im,"MEMORY TURNS EVENTS INTO A LIFE",
         "a self appears wherever moments become mine")


def vis_ego_shell(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    draw_body(d,cx,cy,.82,INK,170)
    r=lerp(230,115,q)
    d.ellipse((cx-r,cy-r*.68,cx+r,cy+r*.68),
              outline=(*CRIMSON,210),width=5)
    labels=["MY BODY","MY STORY","MY FUTURE","MY THREAT"]
    for i,lab in enumerate(labels):
        a=i*math.tau/4-math.pi/2
        x=cx+math.cos(a)*r*.78
        y=cy+math.sin(a)*r*.50
        centered(d,(x,y),lab,load_font(FONT_SANS_BOLD,14),CRIMSON)
    seal(im,"THE SELF-MODEL BECOMES A DEFENDED CENTER",
         "what began as regulation hardens into identity",CRIMSON)


def vis_suffering(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    draw_body(d,cx,cy,.82,INK,160)
    loops=[]
    for k,col in enumerate([CRIMSON,VIOLET,GOLD]):
        pts=[]
        for i in range(160):
            a=i/159*math.tau*2+k
            r=lerp(190,65,q)*(.65+.35*math.sin(i/159*math.pi))
            pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.58))
        loops.append((pts,col))
    for pts,col in loops:
        glow_line(im,pts,col,4,175,10)
    seal(im,"SUFFERING IS THE BOUNDARY DEFENDING ITS OWN STORY",
         "pain becomes world when sensation, memory, and future lock together",CRIMSON)


def vis_fear_world(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.38,h*.42
    draw_body(d,cx,cy,.70,INK,170)
    q=ease(u)
    threats=[(w*.72,h*.25),(w*.80,h*.45),(w*.68,h*.63)]
    for x,y in threats:
        glow_circle(im,x,y,12,CRIMSON,160,9)
        glow_line(im,partial([(cx+40,cy),(x,y)],q),CRIMSON,3,150,9)
    gl=layer(im.size)
    gd=ImageDraw.Draw(gl)
    gd.polygon([(cx,cy),(w*.92,h*.15),(w*.92,h*.70)],fill=(*CRIMSON,int(40*q)))
    im.alpha_composite(gl)
    seal(im,"FEAR DOES NOT MERELY ADD A FEELING",
         "it reorganizes the geometry of the whole world")


def vis_desire_world(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.38,h*.42
    draw_body(d,cx,cy,.70,INK,170)
    q=ease(u)
    target=(w*.76,h*.40)
    glow_circle(im,*target,22,GOLD,190,12)
    paths=[
        [(cx+40,cy),(w*.55,h*.30),target],
        [(cx+40,cy),(w*.58,h*.48),target],
    ]
    for pts in paths:
        glow_line(im,partial(pts,q),GOLD,4,180,11)
    seal(im,"DESIRE TURNS ABSENCE INTO DIRECTION",
         "the not-yet-present begins governing the present")


def vis_human_scale(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # cell -> organism -> human
    draw_cell(d,w*.23,cy,55,CYAN,PALE_GREEN,int(220*(1-q*.6)))
    if q>.25:
        draw_body(d,cx,cy,.55,GREEN,int(220*smoothstep(.25,.60,u)))
    if q>.58:
        draw_body(d,w*.76,cy,.86,INK,int(220*smoothstep(.58,.95,u)))
    glow_line(im,partial([(w*.28,cy),(cx,cy),(w*.70,cy)],q),GOLD,5,210,13)
    seal(im,"THE HUMAN IS NOT A FALL FROM LIGHT",
         "it is light carrying boundary, metabolism, memory, and world")


def vis_no_external_designer(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # hand fades; process self-organizes
    hand_alpha=int(200*(1-q))
    d.line((w*.18,h*.20,w*.36,h*.32),fill=(*CRIMSON,hand_alpha),width=10)
    for rr in range(35,230,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/260))),width=3)
    draw_cell(d,cx,cy,120,CYAN,PALE_GREEN,int(220*q))
    seal(im,"NO OUTSIDE HAND NEEDS TO INSERT LIFE",
         "the field appears as the lawful conditions through which life can arise")


def vis_science_metaphysics(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40)
    q=ease(u)
    # science gears
    for i,r in enumerate((45,33,24)):
        x=left[0]+(i-1)*52; y=left[1]+(i%2)*28
        d.ellipse((x-r,y-r,x+r,y+r),outline=(*CYAN,180),width=4)
    centered(d,(left[0],h*.66),"HOW",load_font(FONT_SERIF_BOLD,28),CYAN)
    # metaphysical field
    for rr in range(35,150,28):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(90*q*(1-rr/175))),width=3)
    centered(d,(right[0],h*.66),"WHY THIS APPEARS AT ALL",load_font(FONT_SERIF_BOLD,24),GOLD)
    glow_line(im,partial([left,(w*.50,h*.22),right],q),VIOLET,4,180,11)
    seal(im,"MECHANISM AND METAPHYSICS ARE DIFFERENT QUESTIONS",
         "biology explains organization; philosophy asks what appearing means")


def vis_recognition_gap(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40)
    a=smoothstep(.05,.30,u)
    gap=smoothstep(.28,.70,u)*(1-smoothstep(.70,.96,u))
    b=smoothstep(.68,.96,u)
    draw_body(d,*left,.65,INK,int(220*(1-a)))
    draw_body(d,*right,.65,INK,int(220*b))
    if gap>0:
        for rr in range(30,220,30):
            d.ellipse((w*.50-rr,h*.40-rr*.58,w*.50+rr,h*.40+rr*.58),
                      outline=(*GOLD,int(85*gap*(1-rr/250))),width=3)
    glow_line(im,partial([left,(w*.50,h*.40),right],u),GOLD,5,200,13)
    seal(im,"BETWEEN TWO IDENTITIES, THE LIGHT REMAINS",
         "recognition notices continuity before the next story closes")


def vis_prakasa_vimarsa(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    light=smoothstep(.05,.48,u)
    reflect=smoothstep(.38,.88,u)
    for rr in range(35,250,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(90*light*(1-rr/280))),width=3)
    pts=radial_field(cx,cy,w*.23,t*.2)
    glow_line(im,partial(pts,reflect),CYAN,5,int(120+100*reflect),13)
    centered(d,(w*.28,h*.70),"PRAKĀŚA",load_font(FONT_SERIF_BOLD,27),GOLD)
    centered(d,(w*.72,h*.70),"VIMARŚA",load_font(FONT_SERIF_BOLD,27),CYAN)
    seal(im,"LIGHT AND SELF-APPREHENSION",
         "awareness is not merely bright; it knows its own appearing")


def vis_finite_in_infinite(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # finite shell inside larger field
    r=lerp(180,95,q)
    draw_body(d,cx,cy,.72,INK,170)
    d.ellipse((cx-r,cy-r*.68,cx+r,cy+r*.68),outline=(*CYAN,210),width=4)
    for rr in range(120,290,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(80*q*(1-rr/320))),width=3)
    seal(im,"THE FINITE DOES NOT NEED TO STOP BEING FINITE",
         "it needs to stop mistaking its boundary for the boundary of reality")


def vis_return_without_erasure(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # body remains while field becomes visible
    draw_body(d,cx,cy,.80,INK,190)
    for rr in range(35,280,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(85*q*(1-rr/310))),width=3)
    # metabolic pulse still present
    pulse_r=18+8*math.sin(t*2)
    glow_circle(im,cx,cy,pulse_r,GREEN,160,11)
    seal(im,"RECOGNITION DOES NOT CANCEL HUNGER",
         "it reveals hunger as one local rhythm of a larger life",GREEN)


def vis_final(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # all stages nested
    for rr,col in [(250,GOLD),(200,VIOLET),(150,CYAN),(100,GREEN)]:
        d.ellipse((cx-rr*q,cy-rr*.62*q,cx+rr*q,cy+rr*.62*q),
                  outline=(*col,int(160*q)),width=3)
    draw_body(d,cx,cy,.78,INK,int(210*q))
    glow_circle(im,cx,cy,18,GOLD,190,13)
    if q>.72:
        centered(d,(cx,h*.69),"AHAM EVA ŚIVAḤ",load_font(FONT_SERIF_BOLD,28),GOLD)
    seal(im,"THE INFINITE HAD TO BECOME HUNGRY",
         "so that light could become a life, a world, and finally recognition",GOLD)


VISUALS: dict[str, Callable] = {
    "field": vis_unbounded_field,
    "contract": vis_first_contraction,
    "membrane": vis_membrane,
    "gradient": vis_gradient,
    "metabolism": vis_metabolism,
    "hunger": vis_hunger,
    "value": vis_value,
    "action": vis_action_world,
    "prediction": vis_prediction,
    "nervous": vis_nervous_system,
    "memory": vis_memory_self,
    "ego": vis_ego_shell,
    "suffering": vis_suffering,
    "fear": vis_fear_world,
    "desire": vis_desire_world,
    "human": vis_human_scale,
    "selforganize": vis_no_external_designer,
    "questions": vis_science_metaphysics,
    "gap": vis_recognition_gap,
    "prakasa": vis_prakasa_vimarsa,
    "finite": vis_finite_in_infinite,
    "return": vis_return_without_erasure,
    "final": vis_final,
}


# =============================================================================
# FILM-FIRST ESSAY
# =============================================================================

@dataclass
class Scene:
    title: str
    narration: str
    duration: float
    visual: str
    params: dict


SCENES = [
    Scene("No other",
          "Imagine an unlimited field with no outside.",
          6.0, "field", {}),
    Scene("No encounter",
          "Nothing stands against it. Nothing surprises it. Nothing can arrive from elsewhere.",
          8.0, "field", {}),
    Scene("Question",
          "How could such a field ever become a life?",
          6.5, "field", {}),

    Scene("Contraction",
          "The first answer is not creation from nothing. It is contraction.",
          8.0, "contract", {}),
    Scene("A center",
          "Possibility accepts a center.",
          5.5, "contract", {}),
    Scene("Perspective",
          "A field that was nowhere in particular becomes here.",
          7.0, "contract", {}),
    Scene("First loss",
          "The gain is perspective. The price is exclusion.",
          7.5, "contract", {}),

    Scene("Boundary",
          "A living center cannot remain only a point. It needs a boundary.",
          8.0, "membrane", {}),
    Scene("Membrane",
          "The membrane says: this exchange enters, that exchange waits, this pattern belongs inside.",
          9.5, "membrane", {}),
    Scene("Not wall",
          "The boundary is not a wall against reality. It is a rule for remaining in relation.",
          9.0, "membrane", {}),

    Scene("Gradient",
          "The moment there is inside and outside, there can be inequality.",
          8.0, "gradient", {}),
    Scene("Stored difference",
          "More here. Less there. Charge on one side. Nutrient on another.",
          8.0, "gradient", {}),
    Scene("Use",
          "A gradient is difference stored as possibility.",
          7.0, "gradient", {}),

    Scene("Metabolism",
          "But a difference decays unless work preserves it.",
          7.5, "metabolism", {}),
    Scene("Cost of life",
          "Metabolism is the cost of keeping the boundary meaningful.",
          8.0, "metabolism", {}),
    Scene("Living loop",
          "Life is not a thing. It is a loop that must keep succeeding.",
          8.5, "metabolism", {}),

    Scene("Hunger appears",
          "And here hunger enters.",
          5.5, "hunger", {}),
    Scene("Need",
          "Not as a punishment added to consciousness, but as the condition of a boundary that must continue.",
          9.5, "hunger", {}),
    Scene("Persistence",
          "The organism needs what it is not because it has become something definite.",
          9.0, "hunger", {}),

    Scene("Value",
          "Need creates value.",
          5.5, "value", {}),
    Scene("Good and bad",
          "Food and poison are not abstract labels. They are differences measured against continued existence.",
          9.0, "value", {}),
    Scene("World matters",
          "A world begins to matter wherever one outcome sustains the boundary and another destroys it.",
          9.5, "value", {}),

    Scene("Action",
          "Value creates action.",
          5.5, "action", {}),
    Scene("Reach",
          "The organism bends toward what may sustain it and away from what may end it.",
          8.5, "action", {}),
    Scene("World as affordance",
          "The environment becomes path, obstacle, shelter, prey, mate, danger.",
          9.0, "action", {}),

    Scene("Future",
          "Action requires a future.",
          6.0, "prediction", {}),
    Scene("Prediction",
          "To move now, the organism must model what will happen next.",
          8.0, "prediction", {}),
    Scene("Error",
          "Every failed prediction reshapes the model. Every successful prediction makes one world more likely to appear again.",
          10.0, "prediction", {}),

    Scene("Nerves",
          "Nervous systems make this loop faster.",
          6.5, "nervous", {}),
    Scene("Before event",
          "Sensation no longer only reports what happened. It prepares for what has not happened yet.",
          9.0, "nervous", {}),
    Scene("Modelled body",
          "The organism begins living inside a controlled anticipation of itself and its world.",
          9.0, "nervous", {}),

    Scene("Memory",
          "Prediction alone is not yet a self.",
          7.0, "memory", {}),
    Scene("One life",
          "Memory threads separate events into one life.",
          8.0, "memory", {}),
    Scene("Mine",
          "This wound happened to me. This place fed me. This face means safety. This loss may return.",
          10.0, "memory", {}),

    Scene("Ego",
          "The self-model then becomes a defended center.",
          7.5, "ego", {}),
    Scene("My body",
          "My body. My history. My future. My threat.",
          7.5, "ego", {}),
    Scene("Useful enclosure",
          "This enclosure is useful. Without it, the organism could not protect a coherent life.",
          9.0, "ego", {}),
    Scene("Forgotten construction",
          "But the model forgets that it is a construction.",
          7.5, "ego", {}),

    Scene("Suffering",
          "Suffering begins when pain is bound to memory, identity, and future.",
          9.0, "suffering", {}),
    Scene("Knot",
          "A sensation becomes my danger, my failure, my permanent world.",
          8.5, "suffering", {}),
    Scene("Defence",
          "The boundary no longer only preserves life. It preserves a story about life.",
          9.0, "suffering", {}),

    Scene("Fear geometry",
          "Fear does not merely add a feeling.",
          6.5, "fear", {}),
    Scene("Threat field",
          "It reorganizes distance, attention, posture, memory, and possibility around danger.",
          9.5, "fear", {}),
    Scene("World contracts",
          "The whole world contracts into what must be escaped.",
          8.0, "fear", {}),

    Scene("Desire geometry",
          "Desire performs the opposite geometry.",
          7.0, "desire", {}),
    Scene("Absence rules",
          "Something absent begins ruling the present.",
          7.5, "desire", {}),
    Scene("Direction",
          "The organism stretches toward a future image and calls the tension hope, craving, love, ambition, devotion.",
          10.0, "desire", {}),

    Scene("Human",
          "A human being is not light imprisoned inside meat.",
          8.0, "human", {}),
    Scene("Light carrying form",
          "A human is light carrying membrane, metabolism, memory, language, and a model of tomorrow.",
          10.0, "human", {}),
    Scene("Drives",
          "Biological drives are what luminous perspective feels like when it must preserve a finite form through time.",
          10.0, "human", {}),

    Scene("No external insertion",
          "No outside hand needs to place spirit into matter.",
          7.5, "selforganize", {}),
    Scene("Lawful emergence",
          "The field can appear as lawful conditions in which boundaries, gradients, and living loops arise.",
          9.5, "selforganize", {}),
    Scene("Same event two languages",
          "Science describes the organization. Metaphysics asks what it means that organization appears at all.",
          9.5, "questions", {}),

    Scene("Do not confuse",
          "These questions should not be collapsed.",
          6.5, "questions", {}),
    Scene("Mechanism",
          "Biology can explain hunger through regulation, chemistry, evolution, and neural control.",
          9.0, "questions", {}),
    Scene("Appearance",
          "It may still leave open why any of this is present as experience.",
          8.0, "questions", {}),

    Scene("Gap",
          "The Tantric wager begins in the gap between identities.",
          8.0, "gap", {}),
    Scene("Release",
          "A thought ends. A desire pauses. A fear loosens for one breath.",
          8.5, "gap", {}),
    Scene("What remains",
          "The defended story disappears for an instant. Illumination remains.",
          8.0, "gap", {}),

    Scene("Prakāśa",
          "Prakāśa is the capacity for anything to appear.",
          7.0, "prakasa", {}),
    Scene("Vimarśa",
          "Vimarśa is the capacity of appearing to know itself.",
          7.5, "prakasa", {}),
    Scene("Recognition",
          "Recognition is not the organism escaping its boundary. It is the boundary becoming transparent to the field that formed it.",
          10.0, "prakasa", {}),

    Scene("Finite remains",
          "The finite life remains finite.",
          6.5, "finite", {}),
    Scene("Boundary not absolute",
          "Its boundary still matters, but it is no longer mistaken for the boundary of reality.",
          9.0, "finite", {}),
    Scene("Local center",
          "The person becomes a local center rather than a metaphysical prison.",
          8.5, "finite", {}),

    Scene("Hunger remains",
          "Recognition does not cancel hunger.",
          6.5, "return", {}),
    Scene("Pain remains",
          "Pain can still hurt. The body can still fail. Desire can still move.",
          8.5, "return", {}),
    Scene("Meaning changes",
          "What changes is the meaning of the movement.",
          7.0, "return", {}),
    Scene("Local rhythm",
          "Hunger is no longer proof of separation. It is one local rhythm through which the larger field sustains a life.",
          10.0, "return", {}),

    Scene("Return to question",
          "Why would the infinite become biological?",
          7.0, "final", {}),
    Scene("Answer",
          "Because without boundary there is no perspective. Without need there is no value. Without value there is no action. Without action there is no lived world.",
          10.0, "final", {}),
    Scene("Deeper answer",
          "And without forgetting, there can be no recognition.",
          7.5, "final", {}),
    Scene("Closing",
          "The infinite had to become hungry so that light could become a life, a world, and finally the recognition that it had never ceased to be light.",
          10.0, "final", {}),
]


# =============================================================================
# PIPELINE
# =============================================================================

def render_frame(scene, frame_index, frame_count, width, height, seed):
    u = frame_index / max(1, frame_count - 1)
    t = u * scene.duration
    im = field(width, height, seed)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")


def ffmpeg_path():
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("ffmpeg is required but was not found on PATH")
    return executable


def encode_scene(index, fps):
    frame_dir = FRAMES / f"scene_{index:03d}"
    output = SCENES_DIR / f"scene_{index:03d}.mp4"
    subprocess.run([
        ffmpeg_path(), "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "%05d.jpg"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output


def render_scene(index, scene, fps, width, height, preview):
    frame_dir = FRAMES / f"scene_{index:03d}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    frame_count = max(2, round(scene.duration * fps))

    if preview:
        samples = [0, int(frame_count * .33), int(frame_count * .72), frame_count - 1]
        for output_index, frame_index in enumerate(samples):
            render_frame(
                scene, frame_index, frame_count, width, height,
                index * 10000 + frame_index,
            ).save(frame_dir / f"preview_{output_index:02d}.jpg", quality=95)
        return frame_dir

    for frame_index in range(frame_count):
        path = frame_dir / f"{frame_index:05d}.jpg"
        if path.exists():
            continue
        render_frame(
            scene, frame_index, frame_count, width, height,
            index * 10000 + frame_index,
        ).save(path, quality=95, subsampling=0)

    return encode_scene(index, fps)


def concatenate(paths):
    concat_file = OUTPUT / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.resolve()}'" for path in paths),
        encoding="utf-8",
    )
    output = OUTPUT / "infinite_had_to_become_hungry.mp4"
    subprocess.run([
        ffmpeg_path(), "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output


def export_timeline():
    cursor = 0.0
    records = []
    for index, scene in enumerate(SCENES, 1):
        record = asdict(scene)
        record["scene_id"] = f"scene_{index:03d}"
        record["start_seconds"] = round(cursor, 3)
        cursor += scene.duration
        record["end_seconds"] = round(cursor, 3)
        records.append(record)

    path = OUTPUT / "narration_timeline.json"
    path.write_text(json.dumps({
        "title": "the infinite had to become hungry",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "gold pulse surviving every contraction",
        "palette_roles": {
            "ivory": "open possibility",
            "gold": "luminous continuity",
            "cyan": "boundary and perception",
            "green": "metabolism and viable action",
            "crimson": "threat and defensive contraction",
            "violet": "memory and latent depth",
            "ink": "fixed form",
        },
        "scenes": records,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def make_contact_sheet(width, height):
    thumb_width = 320
    thumb_height = int(thumb_width * height / width)
    columns = 4
    rows = math.ceil(len(SCENES) / columns)
    cell_height = thumb_height + 48

    sheet = Image.new("RGB", (columns * thumb_width, rows * cell_height), IVORY)
    d = ImageDraw.Draw(sheet)
    label_font = load_font(FONT_SANS_BOLD, 14)

    for index, scene in enumerate(SCENES, 1):
        frame_count = max(2, round(scene.duration * DEFAULT_FPS))
        image = render_frame(
            scene,
            int(frame_count * .72),
            frame_count,
            width,
            height,
            index * 10000 + 72,
        )
        image.thumbnail((thumb_width, thumb_height))
        slot = index - 1
        x = (slot % columns) * thumb_width
        y = (slot // columns) * cell_height
        sheet.paste(image, (x, y))
        d.text((x + 8, y + thumb_height + 7),
               f"{index:02d}  {scene.title}",
               font=label_font, fill=INK)

    path = OUTPUT / "contact_sheet.jpg"
    sheet.save(path, quality=94)
    return path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--scene", type=int)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--no-contact-sheet", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(scene.duration for scene in SCENES) / 60:.2f} minutes")

    if args.scene:
        if not 1 <= args.scene <= len(SCENES):
            raise ValueError("scene out of range")
        print(render_scene(
            args.scene,
            SCENES[args.scene - 1],
            args.fps,
            args.width,
            args.height,
            args.preview,
        ))
        return

    rendered = []
    for index, scene in enumerate(SCENES, 1):
        print(f"[{index:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        result = render_scene(
            index, scene, args.fps, args.width, args.height, args.preview
        )
        if not args.preview:
            rendered.append(result)

    if not args.no_contact_sheet:
        print(f"Contact sheet: {make_contact_sheet(args.width, args.height)}")

    if not args.preview:
        print(f"Final video: {concatenate(rendered)}")


if __name__ == "__main__":
    main()
