#!/usr/bin/env python3
"""
THE WORLD LEARNS TO FEEL THROUGH YOU
An original Platinum-house procedural visual essay.

CORE THESIS
-----------
A boundary creates an inside.
An inside can be altered.
Alteration becomes sensation.
Sensation measured against survival becomes valence.
Valence held across time becomes emotion.
Emotion interpreted through memory becomes a world.
When two living worlds begin regulating one another, feeling becomes relation.
Empathy is not access to another private interior.
It is one nervous system learning the shape of another's significance.
The world becomes vulnerable to itself through living beings.

VISUAL THESIS
-------------
One gold pulse becomes:
contact → sensation → valence → emotion → memory → expression → resonance →
co-regulation → empathy → grief → love → recognition.

HOUSE RULES
-----------
• Every shot lasts 5–10 seconds.
• Every shot performs a visible transformation.
• White gallery/scientific field.
• Sparse typography.
• No slideshow layouts.
• Mature frame near u=0.72.
• Continuity object: a gold pulse that changes from private signal to shared rhythm.

PALETTE ROLES
-------------
IVORY    open field
GOLD     felt presence / recognition
CYAN     sensing / transmission / regulation
GREEN    safety / viable relation
CRIMSON  pain / threat / rupture
VIOLET   memory / interiority / grief
INK      fixed form / interpretation

OUTPUT
------
output_world_feels/
  frames/
  scenes/
  world_learns_to_feel.mp4
  narration_timeline.json
  contact_sheet.jpg
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


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_world_feels"
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


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def mix(a, b, t):
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a))
    return q * q * (3 - 2 * q)


def ease(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def pulse(t, speed=1.0, phase=0.0):
    return 0.5 + 0.5 * math.sin(math.tau * (speed * t + phase))


def font(path, size):
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def field(w, h, seed):
    rng = np.random.default_rng(seed)
    arr = np.empty((h, w, 3), dtype=np.float32)
    arr[:] = IVORY
    arr += rng.normal(0, 0.9, (h, w, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    halo = np.exp(
        -(((xx - w * 0.50) / (w * 0.37)) ** 2
          + ((yy - h * 0.40) / (h * 0.31)) ** 2) * 2.0
    )
    arr[..., 1] += halo * 3.4
    arr[..., 2] += halo * 5.0
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def centered(d, xy, text, fnt, fill=INK):
    d.text(xy, text, font=fnt, fill=fill, anchor="mm")


def seal(im, title, subtitle="", color=INK):
    w, h = im.size
    d = ImageDraw.Draw(im)
    centered(
        d, (w / 2, h * 0.875), title,
        font(FONT_SERIF_BOLD, max(22, int(h * 0.04))),
        color,
    )
    if subtitle:
        centered(
            d, (w / 2, h * 0.923), subtitle,
            font(FONT_SANS, max(13, int(h * 0.019))),
            SOFT_INK,
        )


def border(im):
    w, h = im.size
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(
        (26, 26, w - 26, h - 26),
        radius=18,
        outline=(*INK, 45),
        width=2,
    )


def glow_circle(im, x, y, r, color, alpha=170, blur=14):
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.ellipse((x-r, y-r, x+r, y+r), fill=(*color, alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).ellipse(
        (x-r*.34, y-r*.34, x+r*.34, y+r*.34),
        fill=(*mix(color, WHITE, .35), min(255, alpha+50)),
    )
    im.alpha_composite(fg)


def glow_line(im, pts, color, width=4, alpha=210, blur=11):
    if len(pts) < 2:
        return
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.line(pts, fill=(*color, alpha), width=width*3, joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).line(
        pts,
        fill=(*mix(color, WHITE, .08), min(255, alpha+25)),
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
    target = amount * (len(pts)-1)
    idx = int(target)
    frac = target - idx
    out = list(pts[:idx+1])
    if idx+1 < len(pts):
        a, b = pts[idx], pts[idx+1]
        out.append((lerp(a[0], b[0], frac), lerp(a[1], b[1], frac)))
    return out


def arrow(d, a, b, color=INK, width=3, head=10):
    d.line((*a, *b), fill=color, width=width)
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    for s in (-1, 1):
        p = (
            b[0] - math.cos(ang+s*.52)*head,
            b[1] - math.sin(ang+s*.52)*head,
        )
        d.line((*b, *p), fill=color, width=width)


def draw_body(d, cx, cy, scale=1.0, color=INK, alpha=220):
    d.ellipse(
        (cx-28*scale, cy-145*scale, cx+28*scale, cy-89*scale),
        outline=(*color, alpha), width=max(2, int(4*scale))
    )
    d.line((cx, cy-89*scale, cx, cy+55*scale),
           fill=(*color, alpha), width=max(3, int(6*scale)))
    d.line((cx-70*scale, cy-55*scale, cx+70*scale, cy-55*scale),
           fill=(*color, alpha), width=max(3, int(5*scale)))
    d.line((cx-70*scale, cy-55*scale, cx-145*scale, cy+15*scale),
           fill=(*color, alpha), width=max(3, int(5*scale)))
    d.line((cx+70*scale, cy-55*scale, cx+145*scale, cy+15*scale),
           fill=(*color, alpha), width=max(3, int(5*scale)))
    d.line((cx, cy+55*scale, cx-55*scale, cy+160*scale),
           fill=(*color, alpha), width=max(3, int(5*scale)))
    d.line((cx, cy+55*scale, cx+55*scale, cy+160*scale),
           fill=(*color, alpha), width=max(3, int(5*scale)))


def draw_face(d, cx, cy, scale=1.0, color=INK, alpha=220, expression=0.0):
    d.ellipse((cx-60*scale, cy-78*scale, cx+60*scale, cy+78*scale),
              outline=(*color, alpha), width=max(2, int(4*scale)))
    for ex in (-20, 20):
        d.ellipse((cx+(ex-4)*scale, cy-18*scale,
                   cx+(ex+4)*scale, cy-10*scale),
                  fill=(*color, alpha))
    if expression >= 0:
        d.arc((cx-24*scale, cy+5*scale, cx+24*scale, cy+35*scale),
              10, 170, fill=(*color, alpha), width=max(2, int(3*scale)))
    else:
        d.arc((cx-24*scale, cy+12*scale, cx+24*scale, cy+42*scale),
              190, 350, fill=(*color, alpha), width=max(2, int(3*scale)))


def vis_contact(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    q = ease(u)
    d.ellipse((cx-145, cy-145, cx+145, cy+145),
              outline=(*CYAN, 180), width=4)
    point = (lerp(w*.15, cx-145, q), cy)
    glow_circle(im, *point, 14, GOLD, 180, 11)
    if q > .55:
        for rr in range(20, 140, 22):
            d.arc((cx-rr, cy-rr, cx+rr, cy+rr), 140, 220,
                  fill=(*GOLD, int(110*q*(1-rr/160))), width=3)
    seal(im, "CONTACT BECOMES SENSATION",
         "a boundary can be altered from beyond itself")


def vis_valence(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    q = ease(u)
    left = (w*.28, cy)
    right = (w*.72, cy)
    glow_circle(im, *left, 18, CRIMSON, 180, 12)
    glow_circle(im, *right, 18, GREEN, 180, 12)
    x = lerp(left[0], right[0], q)
    glow_circle(im, x, cy, 14, GOLD, 180, 10)
    centered(d, (left[0], h*.66), "AVOID", font(FONT_SERIF_BOLD, 25), CRIMSON)
    centered(d, (right[0], h*.66), "APPROACH", font(FONT_SERIF_BOLD, 25), GREEN)
    seal(im, "SENSATION MEASURED AGAINST LIFE BECOMES VALENCE",
         "not merely what happened, but whether it helps or harms")


def vis_emotion(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    q = ease(u)
    labels = [
        ("BODY", CYAN, -180, -80),
        ("MEMORY", VIOLET, 180, -80),
        ("PREDICTION", GOLD, -180, 95),
        ("ACTION", GREEN, 180, 95),
    ]
    for i, (lab, col, ox, oy) in enumerate(labels):
        local = clamp(q*len(labels)-i)
        x = lerp(cx+ox, cx, local*.78)
        y = lerp(cy+oy, cy, local*.78)
        glow_circle(im, x, y, 11, col, 150, 9)
        if local > .45:
            centered(d, (x, y+30), lab, font(FONT_SANS_BOLD, 14), col)
    if q > .55:
        glow_circle(im, cx, cy, 20, CRIMSON if p.get("tone")=="fear" else GOLD, 190, 13)
    seal(im, "EMOTION IS A WHOLE-BODY INTERPRETATION",
         "sensation, memory, prediction, and action bind into one state")


def vis_expression(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    left = (w*.32, h*.40)
    right = (w*.68, h*.40)
    q = ease(u)
    draw_face(d, *left, 1.0, INK, 180, expression=-1)
    wave = []
    for i in range(120):
        x = lerp(left[0]+65, right[0]-65, i/119)
        y = h*.40 + math.sin(i*.32-t*3)*20*(1-i/119)
        wave.append((x,y))
    glow_line(im, partial(wave, q), CYAN, 4, 190, 12)
    draw_face(d, *right, 1.0, mix(INK, CRIMSON, q*.45), 180, expression=-q)
    seal(im, "FEELING LEAVES THE BODY AS EXPRESSION",
         "voice, posture, face, and timing make interior states socially legible")


def vis_resonance(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    left = (w*.32, h*.40)
    right = (w*.68, h*.40)
    q = ease(u)
    draw_body(d, *left, .72, INK, 170)
    draw_body(d, *right, .72, INK, 170)
    for rr in range(30, 150, 24):
        a1 = int(90*q*(1-rr/170))
        d.arc((left[0]-rr,left[1]-rr,left[0]+rr,left[1]+rr),
              -55,55,fill=(*CRIMSON,a1),width=3)
        d.arc((right[0]-rr,right[1]-rr,right[0]+rr,right[1]+rr),
              125,235,fill=(*CYAN,a1),width=3)
    glow_line(im, partial([left,(w*.50,h*.25),right],q), GOLD, 5, 210, 13)
    seal(im, "ONE NERVOUS SYSTEM ENTERS THE WEATHER OF ANOTHER",
         "resonance begins before interpretation")


def vis_coregulation(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    left = (w*.34,h*.40)
    right = (w*.66,h*.40)
    q = ease(u)
    draw_body(d,*left,.70,INK,170)
    draw_body(d,*right,.70,INK,170)
    amp1 = lerp(70,32,q)
    amp2 = lerp(25,32,q)
    for center,amp,col,phase in [(left,amp1,CRIMSON,0),(right,amp2,CYAN,1.2)]:
        pts=[]
        for i in range(160):
            x=lerp(center[0]-120,center[0]+120,i/159)
            y=center[1]+math.sin(i*.23+t*2+phase)*amp
            pts.append((x,y))
        glow_line(im,pts,col,4,180,10)
    if q>.5:
        glow_line(im,[(left[0],left[1]),(right[0],right[1])],GOLD,5,180,11)
    seal(im,"CO-REGULATION IS SHARED PHYSIOLOGY",
         "breath, voice, distance, and timing alter what each body can bear")


def vis_empathy(im, u, t, p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.32,h*.40)
    right=(w*.68,h*.40)
    q=ease(u)
    draw_face(d,*left,.9,INK,170,-1)
    draw_face(d,*right,.9,INK,170,0)
    # no merger, only mapping
    for i in range(7):
        y=lerp(h*.25,h*.56,i/6)
        x1=left[0]+55
        x2=right[0]-55
        end=lerp(x1,x2,q)
        d.line((x1,y,end,y),fill=(*GOLD,int(120+80*q)),width=3)
    centered(d,(w*.50,h*.68),"NOT YOUR PAIN · A MODEL OF ITS SHAPE",
             font(FONT_SERIF_BOLD,21),GOLD)
    seal(im,"EMPATHY DOES NOT ERASE THE OTHER",
         "it builds a responsive map across an irreducible distance")


def vis_misattunement(im, u, t, p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.32,h*.40)
    right=(w*.68,h*.40)
    q=ease(u)
    draw_face(d,*left,.9,INK,170,-1)
    draw_face(d,*right,.9,INK,170,1)
    lines=[
        [(left[0]+55,left[1]-40),(w*.50,h*.25),(right[0]-55,right[1]+30)],
        [(left[0]+55,left[1]+25),(w*.50,h*.58),(right[0]-55,right[1]-45)]
    ]
    for pts in lines:
        glow_line(im,partial(pts,q),CRIMSON,4,180,10)
    seal(im,"A MODEL OF ANOTHER CAN FAIL",
         "projection begins where responsiveness ends",CRIMSON)


def vis_language(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    states=[("PRESSURE",CYAN,-190,-85),("FEAR",CRIMSON,190,-85),
            ("LOSS",VIOLET,-190,100),("LOVE",GOLD,190,100)]
    for i,(lab,col,ox,oy) in enumerate(states):
        local=clamp(q*len(states)-i)
        x=lerp(cx+ox,cx,local*.75)
        y=lerp(cy+oy,cy,local*.75)
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,16),(*col,int(210*local)))
    if q>.55:
        centered(d,(cx,cy),"I FEEL",font(FONT_SERIF_BOLD,32),GOLD)
    seal(im,"LANGUAGE GIVES FEELING A SECOND BODY",
         "what was diffuse becomes nameable, shareable, and sometimes imprisoning")


def vis_grief(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # absent figure
    draw_body(d,cx-150,cy,.66,VIOLET,int(180*(1-q)))
    # surviving relational field
    for rr in range(35,230,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*VIOLET,int(80*q*(1-rr/260))),width=3)
    glow_circle(im,cx+95,cy,15,GOLD,160,11)
    seal(im,"GRIEF IS A RELATION CONTINUING WITHOUT ITS OBJECT",
         "the body keeps preparing for someone who no longer arrives",VIOLET)


def vis_love(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.34,h*.40)
    right=(w*.66,h*.40)
    q=ease(u)
    draw_body(d,*left,.70,INK,170)
    draw_body(d,*right,.70,INK,170)
    # distinct boundaries remain
    for center,col in [(left,CYAN),(right,GREEN)]:
        d.ellipse((center[0]-115,center[1]-135,center[0]+115,center[1]+135),
                  outline=(*col,170),width=3)
    shared=[]
    for i in range(160):
        a=i/159*math.tau
        x=w*.50+math.cos(a)*180
        y=h*.40+math.sin(a)*85
        shared.append((x,y))
    glow_line(im,partial(shared,q),GOLD,5,190,12)
    seal(im,"LOVE IS NOT MERGER",
         "it is the willingness to let another life alter the shape of your own")


def vis_self_other(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    left=(lerp(cx,cx-180,q),cy)
    right=(lerp(cx,cx+180,q),cy)
    glow_circle(im,*left,14,CYAN,170,10)
    glow_circle(im,*right,14,GOLD,170,10)
    d.line((*left,*right),fill=(*INK,int(170*q)),width=4)
    if q>.45:
        centered(d,(left[0],cy-40),"SELF",font(FONT_SANS_BOLD,17),CYAN)
        centered(d,(right[0],cy-40),"OTHER",font(FONT_SANS_BOLD,17),GOLD)
    seal(im,"RELATION REQUIRES DIFFERENCE",
         "without two centers there is no encounter, response, or care")


def vis_shared_field(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    centers=[(w*.30,cy,CYAN),(w*.50,cy,GOLD),(w*.70,cy,GREEN)]
    for x,y,col in centers:
        glow_circle(im,x,y,14,col,170,10)
    for rr in range(45,255,35):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(75*q*(1-rr/285))),width=3)
    seal(im,"MANY INTERIORS CAN SHARE ONE FIELD",
         "unity need not abolish perspective")


def vis_pain_attention(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    points=[("HEAT",CRIMSON,-170,-70),("PRESSURE",CYAN,170,-70),
            ("MEMORY",VIOLET,-170,95),("FEAR",CRIMSON,170,95)]
    for lab,col,ox,oy in points:
        x=lerp(cx+ox,cx,q*.70)
        y=lerp(cy+oy,cy,q*.70)
        glow_circle(im,x,y,10,col,150,9)
        if q<.55:
            centered(d,(x,y+28),lab,font(FONT_SANS_BOLD,13),col)
    if q>.55:
        glow_circle(im,cx,cy,20,CRIMSON,190,13)
    seal(im,"ATTENTION CAN BIND MANY EVENTS INTO ONE PAIN",
         "or release the knot by revealing its threads")


def vis_compassion(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.32,h*.40)
    right=(w*.68,h*.40)
    q=ease(u)
    draw_body(d,*left,.72,INK,170)
    draw_body(d,*right,.72,INK,170)
    # right sends support without taking over
    path=[(right[0]-80,right[1]),(w*.50,h*.28),(left[0]+80,left[1])]
    glow_line(im,partial(path,q),GREEN,5,200,12)
    # left rhythm steadies
    for rr in range(25,120,22):
        d.arc((left[0]-rr,left[1]-rr,left[0]+rr,left[1]+rr),
              210,330,fill=(*GREEN,int(95*q*(1-rr/140))),width=3)
    seal(im,"COMPASSION IS FEELING TURNED INTO SKILLFUL RESPONSE",
         "not absorbing another's pain, but helping their world become livable")


def vis_sacred_vulnerability(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    draw_body(d,cx,cy,.80,INK,170)
    # boundary opens in one place without disappearing
    d.arc((cx-155,cy-180,cx+155,cy+180),40,320,fill=(*CYAN,200),width=5)
    opening=(cx+120,cy-110)
    glow_circle(im,*opening,15,GOLD,180,11)
    for rr in range(35,230,30):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(75*q*(1-rr/260))),width=3)
    seal(im,"TO FEEL IS TO BE ALTERABLE",
         "vulnerability is not the failure of life but its condition")


def vis_prakasa_vimarsa(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    light=smoothstep(.05,.48,u)
    reflect=smoothstep(.38,.88,u)
    for rr in range(35,250,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(90*light*(1-rr/280))),width=3)
    pts=[]
    for i in range(150):
        q=i/149
        a=q*math.tau*1.7+t*.3
        r=w*.22*(.25+.75*q)
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.60))
    glow_line(im,partial(pts,reflect),CYAN,5,int(120+100*reflect),13)
    centered(d,(w*.28,h*.70),"PRAKĀŚA",font(FONT_SERIF_BOLD,27),GOLD)
    centered(d,(w*.72,h*.70),"VIMARŚA",font(FONT_SERIF_BOLD,27),CYAN)
    seal(im,"THE FIELD DOES NOT MERELY SHINE",
         "it apprehends its own transformations")


def vis_final(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # many bodies, one field
    positions=[(w*.27,cy),(w*.50,cy),(w*.73,cy)]
    colors=[CYAN,GOLD,GREEN]
    for (x,y),col in zip(positions,colors):
        draw_body(d,x,y,.52,INK,int(210*q))
        glow_circle(im,x,y,12,col,160,9)
    for rr in range(45,290,35):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(80*q*(1-rr/320))),width=3)
    if q>.72:
        centered(d,(cx,h*.69),"SPANDA",font(FONT_SERIF_BOLD,30),GOLD)
    seal(im,"THE WORLD LEARNS TO FEEL THROUGH YOU",
         "each life is one place where reality becomes vulnerable to itself",GOLD)


VISUALS: dict[str, Callable] = {
    "contact": vis_contact,
    "valence": vis_valence,
    "emotion": vis_emotion,
    "expression": vis_expression,
    "resonance": vis_resonance,
    "coregulation": vis_coregulation,
    "empathy": vis_empathy,
    "misattunement": vis_misattunement,
    "language": vis_language,
    "grief": vis_grief,
    "love": vis_love,
    "self_other": vis_self_other,
    "shared": vis_shared_field,
    "pain": vis_pain_attention,
    "compassion": vis_compassion,
    "vulnerability": vis_sacred_vulnerability,
    "prakasa": vis_prakasa_vimarsa,
    "final": vis_final,
}


@dataclass
class Scene:
    title: str
    narration: str
    duration: float
    visual: str
    params: dict


SCENES = [
    Scene("Contact",
          "A living boundary can be altered by what lies beyond it.",
          7.0, "contact", {}),
    Scene("Sensation",
          "Pressure changes the membrane. Heat changes chemistry. Sound moves tissue. Light changes electrical state.",
          9.5, "contact", {}),
    Scene("First feeling",
          "Contact becomes sensation when the alteration is registered inside the life it affects.",
          9.0, "contact", {}),

    Scene("Valence",
          "But sensation is not yet feeling in the human sense.",
          7.0, "valence", {}),
    Scene("Better or worse",
          "The organism measures change against one silent question: does this help me continue?",
          9.0, "valence", {}),
    Scene("Approach and avoid",
          "That measurement creates valence: better, worse, approach, avoid.",
          8.0, "valence", {}),

    Scene("Emotion begins",
          "Emotion begins when valence recruits the whole organism.",
          8.0, "emotion", {}),
    Scene("Fear body",
          "Fear is not one signal. It is heartbeat, posture, memory, prediction, attention, and prepared action moving together.",
          10.0, "emotion", {"tone":"fear"}),
    Scene("World-state",
          "An emotion is not merely inside the body. It is a temporary world-state.",
          8.5, "emotion", {"tone":"fear"}),

    Scene("Expression",
          "Feeling does not remain private.",
          6.5, "expression", {}),
    Scene("Body speaks",
          "Face, voice, distance, timing, and movement carry the body's state into the space between bodies.",
          9.5, "expression", {}),
    Scene("Legibility",
          "The interior becomes partially legible without ever becoming fully exposed.",
          8.0, "expression", {}),

    Scene("Resonance",
          "Another nervous system receives the pattern.",
          7.0, "resonance", {}),
    Scene("Before thought",
          "Before interpretation, breath changes. Muscles prepare. Attention shifts.",
          8.5, "resonance", {}),
    Scene("Weather",
          "One nervous system enters the weather of another.",
          7.5, "resonance", {}),

    Scene("Co-regulation",
          "Sometimes the weather changes because another body stays.",
          7.5, "coregulation", {}),
    Scene("Shared physiology",
          "A slower voice, a reliable rhythm, a safe distance, and an unthreatening face can alter what the body predicts.",
          10.0, "coregulation", {}),
    Scene("Two bodies",
          "Co-regulation is not metaphor. Two bodies change the conditions under which each must regulate itself.",
          9.5, "coregulation", {}),

    Scene("Empathy",
          "Empathy begins here, but it is often misunderstood.",
          7.5, "empathy", {}),
    Scene("Not access",
          "You do not enter another person's private interior.",
          7.0, "empathy", {}),
    Scene("Responsive model",
          "You build a responsive model of what their expressions, history, and situation might mean.",
          9.0, "empathy", {}),
    Scene("Distance remains",
          "Good empathy preserves the distance it tries to cross.",
          7.5, "empathy", {}),

    Scene("Projection",
          "When the model stops updating, empathy becomes projection.",
          7.5, "misattunement", {}),
    Scene("Wrong map",
          "You answer the pain you expected, not the pain that was expressed.",
          8.5, "misattunement", {}),
    Scene("Responsiveness",
          "Care begins again when the map becomes corrigible.",
          7.5, "misattunement", {}),

    Scene("Language",
          "Language gives feeling a second body.",
          7.0, "language", {}),
    Scene("I feel",
          "A diffuse pressure becomes fear. A hollow absence becomes grief. Warmth becomes love.",
          9.0, "language", {}),
    Scene("Shared and fixed",
          "Naming makes feeling shareable. It can also make a changing state feel fixed.",
          8.5, "language", {}),

    Scene("Grief",
          "Grief reveals how deeply feeling is relational.",
          7.5, "grief", {}),
    Scene("Absent person",
          "The person is gone, but the body still prepares for their voice, their step, their return.",
          9.5, "grief", {}),
    Scene("Continuing relation",
          "Grief is a relation continuing without its object.",
          8.0, "grief", {}),

    Scene("Love",
          "Love reveals the opposite truth.",
          6.5, "love", {}),
    Scene("Not merger",
          "Love is not the erasure of two lives into one.",
          7.5, "love", {}),
    Scene("Alterability",
          "It is the willingness to let another life alter the shape of your own.",
          8.5, "love", {}),

    Scene("Difference",
          "Relation requires difference.",
          6.0, "self_other", {}),
    Scene("Two centers",
          "Without two centers, there is no encounter, response, surprise, or care.",
          8.5, "self_other", {}),
    Scene("Unity without collapse",
          "A deeper unity need not abolish perspective. It can sustain many interiors at once.",
          9.0, "shared", {}),

    Scene("Pain knot",
          "Attention can bind heat, pressure, memory, and fear into one solid pain.",
          9.0, "pain", {}),
    Scene("Threads",
          "The same attention can reveal that the solid object is a moving agreement among many events.",
          9.5, "pain", {}),
    Scene("No denial",
          "This does not make pain unreal. It makes its construction visible.",
          8.0, "pain", {}),

    Scene("Compassion",
          "Compassion is feeling turned into skillful response.",
          7.5, "compassion", {}),
    Scene("Not absorption",
          "It does not require absorbing another person's suffering into your own body.",
          8.0, "compassion", {}),
    Scene("Livable world",
          "It asks what action might help their world become more livable.",
          8.0, "compassion", {}),

    Scene("Vulnerability",
          "To feel is to be alterable.",
          6.5, "vulnerability", {}),
    Scene("No sealed life",
          "A perfectly sealed organism could not be wounded, but it could not be nourished, touched, surprised, or loved.",
          10.0, "vulnerability", {}),
    Scene("Condition of life",
          "Vulnerability is not the accidental weakness of life. It is the condition of exchange.",
          9.0, "vulnerability", {}),

    Scene("Prakāśa",
          "Kashmir Śaivism calls consciousness prakāśa: the power by which anything appears.",
          8.5, "prakasa", {}),
    Scene("Vimarśa",
          "It calls reflexive awareness vimarśa: the power by which appearing is felt and known.",
          8.5, "prakasa", {}),
    Scene("Feeling field",
          "Feeling is one local form of the field apprehending its own transformation.",
          9.0, "prakasa", {}),

    Scene("No cosmic sentimentality",
          "This does not prove that the universe has human emotions.",
          7.5, "shared", {}),
    Scene("Narrow claim",
          "It means that through living organization, reality can become present as better and worse, pain and relief, loss and love.",
          10.0, "shared", {}),
    Scene("Vulnerable reality",
          "A world that contains feeling is no longer only described. Somewhere within it, events matter.",
          9.0, "shared", {}),

    Scene("Return",
          "The world learns to feel through you.",
          7.0, "final", {}),
    Scene("Not chosen vessel",
          "Not because you were selected as a mystical container.",
          7.0, "final", {}),
    Scene("Living aperture",
          "Because a living body is an aperture through which contact becomes significance.",
          9.0, "final", {}),
    Scene("Closing",
          "Each life is one place where reality becomes vulnerable to itself—where light can be touched, changed, wounded, comforted, and recognized as feeling.",
          10.0, "final", {}),
]


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
        samples = [0, int(frame_count*.33), int(frame_count*.72), frame_count-1]
        for output_index, frame_index in enumerate(samples):
            render_frame(
                scene, frame_index, frame_count, width, height,
                index*10000 + frame_index
            ).save(frame_dir / f"preview_{output_index:02d}.jpg", quality=95)
        return frame_dir

    for frame_index in range(frame_count):
        p = frame_dir / f"{frame_index:05d}.jpg"
        if p.exists():
            continue
        render_frame(
            scene, frame_index, frame_count, width, height,
            index*10000 + frame_index
        ).save(p, quality=95, subsampling=0)

    return encode_scene(index, fps)


def concatenate(paths):
    concat_file = OUTPUT / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in paths),
        encoding="utf-8",
    )
    output = OUTPUT / "world_learns_to_feel.mp4"
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
        "title": "the world learns to feel through you",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "gold pulse becoming shared rhythm",
        "scenes": records,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def make_contact_sheet(width, height):
    tw = 320
    th = int(tw * height / width)
    cols = 4
    rows = math.ceil(len(SCENES) / cols)
    cell_h = th + 48
    sheet = Image.new("RGB", (cols*tw, rows*cell_h), IVORY)
    d = ImageDraw.Draw(sheet)
    lf = font(FONT_SANS_BOLD, 14)

    for index, scene in enumerate(SCENES, 1):
        frame_count = max(2, round(scene.duration * DEFAULT_FPS))
        image = render_frame(
            scene, int(frame_count*.72), frame_count,
            width, height, index*10000+72
        )
        image.thumbnail((tw, th))
        slot = index - 1
        x = (slot % cols) * tw
        y = (slot // cols) * cell_h
        sheet.paste(image, (x, y))
        d.text((x+8, y+th+7), f"{index:02d}  {scene.title}", font=lf, fill=INK)

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
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")

    if args.scene:
        if not 1 <= args.scene <= len(SCENES):
            raise ValueError("scene out of range")
        print(render_scene(
            args.scene,
            SCENES[args.scene-1],
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
