#!/usr/bin/env python3
"""
THE BODY CAN REMEMBER A SHAPE IT IS NOT WEARING
Platinum procedural visual essay — bioelectric morphogenesis.

Adapted from:
expansion-essays/01_the_body_can_remember_a_shape_it_is_not_wearing.md

HOUSE CONTRACT
--------------
• 5–10 seconds per shot.
• Every shot performs the spoken claim as a visible transformation.
• Clean ivory scientific field; no lined manuscript background.
• Genuinely animated processes, not static labelled slides.
• Sparse typography used only as conceptual seals.
• Distinct visual vocabulary from the quantum-tunnelling film.

PALETTE ROLES
-------------
INK      anatomy / visible form
CYAN     bioelectric state / distributed communication
GOLD     target morphology / remembered future
CRIMSON  wound / perturbation / unstable polarity
GREEN    successful repair / coordinated viability
VIOLET   cryptic attractor / alternate stable state

CONTINUITY OBJECT
-----------------
A thin cyan current-line survives cuts, changes carriers, disappears beneath
normal anatomy, and returns when injury asks the tissue what body to rebuild.

OUTPUT
------
output_body_remembers/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  body_remembers_shape.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python body_remembers_shape_platinum.py
python body_remembers_shape_platinum.py --preview
python body_remembers_shape_platinum.py --scene 12
python body_remembers_shape_platinum.py --fps 12 --width 1920 --height 1080
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
OUTPUT = ROOT / "output_body_remembers"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 10

IVORY = (249, 247, 241)
PAPER = (242, 239, 231)
INK = (31, 36, 42)
SOFT_INK = (85, 91, 97)
SILVER = (180, 187, 191)
PALE_SILVER = (224, 228, 228)
CYAN = (55, 157, 178)
PALE_CYAN = (194, 227, 233)
DEEP_CYAN = (35, 104, 128)
GOLD = (193, 155, 72)
PALE_GOLD = (235, 218, 172)
CRIMSON = (164, 57, 69)
PALE_CRIMSON = (231, 198, 201)
GREEN = (68, 139, 99)
PALE_GREEN = (196, 225, 206)
VIOLET = (107, 82, 151)
PALE_VIOLET = (218, 208, 235)
VOID = (24, 28, 34)
WHITE = (255, 254, 250)

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
    return q * q * (3 - 2 * q)


def ease(t: float) -> float:
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def pulse(t: float, speed: float = 1.0, phase: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin(math.tau * (speed * t + phase))


def font(path: str, size: int):
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def scientific_field(w: int, h: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.empty((h, w, 3), dtype=np.float32)
    base[:] = IVORY
    fine = rng.normal(0, 0.95, (h, w, 1))
    base += fine

    yy, xx = np.mgrid[0:h, 0:w]
    halo = np.exp(
        -(((xx - w * 0.52) / (w * 0.36)) ** 2
          + ((yy - h * 0.39) / (h * 0.30)) ** 2) * 2.1
    )
    base[..., 0] += halo * 1.5
    base[..., 1] += halo * 4.0
    base[..., 2] += halo * 5.5
    base = np.clip(base, 0, 255).astype(np.uint8)
    return Image.fromarray(base, "RGB").convert("RGBA")


def centered(draw, xy, text, fnt, fill=INK):
    draw.text(xy, text, font=fnt, fill=fill, anchor="mm")


def border(im):
    w, h = im.size
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(
        (26, 26, w - 26, h - 26),
        radius=18,
        outline=(*INK, 48),
        width=2,
    )
    # restrained scientific registration marks
    for x, y in ((52, 52), (w - 52, 52), (52, h - 52), (w - 52, h - 52)):
        d.line((x - 9, y, x + 9, y), fill=(*CYAN, 80), width=1)
        d.line((x, y - 9, x, y + 9), fill=(*CYAN, 80), width=1)


def seal(im, title, subtitle="", color=INK):
    w, h = im.size
    d = ImageDraw.Draw(im)
    tf = font(FONT_SERIF_BOLD, max(22, int(h * 0.040)))
    sf = font(FONT_SANS, max(13, int(h * 0.019)))
    centered(d, (w / 2, h * 0.875), title, tf, color)
    if subtitle:
        centered(d, (w / 2, h * 0.923), subtitle, sf, SOFT_INK)


def glow_circle(im, x, y, r, color, alpha=170, blur=16):
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.ellipse((x-r, y-r, x+r, y+r), fill=(*color, alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    core = layer(im.size)
    ImageDraw.Draw(core).ellipse(
        (x-r*.38, y-r*.38, x+r*.38, y+r*.38),
        fill=(*mix(color, WHITE, .35), min(255, alpha+55)),
    )
    im.alpha_composite(core)


def glow_line(im, points, color, width=4, alpha=210, blur=12):
    if len(points) < 2:
        return
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.line(points, fill=(*color, alpha), width=width * 3, joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg = layer(im.size)
    ImageDraw.Draw(fg).line(
        points,
        fill=(*mix(color, WHITE, .08), min(255, alpha + 25)),
        width=width,
        joint="curve",
    )
    im.alpha_composite(fg)


def partial(points, amount):
    amount = clamp(amount)
    if not points:
        return []
    if amount >= 1:
        return points
    target = amount * (len(points) - 1)
    idx = int(target)
    frac = target - idx
    out = list(points[:idx+1])
    if idx + 1 < len(points):
        a, b = points[idx], points[idx+1]
        out.append((lerp(a[0], b[0], frac), lerp(a[1], b[1], frac)))
    return out


def arrow(draw, a, b, color=INK, width=3, head=10):
    draw.line((*a, *b), fill=color, width=width)
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    for s in (-1, 1):
        p = (
            b[0] - math.cos(ang + s * .53) * head,
            b[1] - math.sin(ang + s * .53) * head,
        )
        draw.line((*b, *p), fill=color, width=width)


def planarian_outline(cx, cy, length, width, heads=1, tail=True, phase=0.0):
    """Returns body polygon plus head centres."""
    pts_top = []
    pts_bottom = []
    samples = 100
    for i in range(samples):
        q = i / (samples - 1)
        x = cx - length/2 + q * length
        bulge = math.sin(math.pi * q) ** .62
        local_w = width * (.22 + .78 * bulge)
        local_w *= 1 + .035 * math.sin(q * math.tau * 3 + phase)
        pts_top.append((x, cy - local_w/2))
        pts_bottom.append((x, cy + local_w/2))

    poly = pts_top + list(reversed(pts_bottom))
    head_centres = []
    if heads >= 1:
        head_centres.append((cx - length/2 + width*.18, cy))
    if heads >= 2:
        head_centres.append((cx + length/2 - width*.18, cy))
    return poly, head_centres


def draw_planarian(im, cx, cy, length, width, heads=1, body_color=PALE_CYAN,
                   outline=DEEP_CYAN, alpha=245, phase=0.0):
    d = ImageDraw.Draw(im)
    poly, head_centres = planarian_outline(cx, cy, length, width, heads, True, phase)
    d.polygon(poly, fill=(*body_color, alpha), outline=(*outline, min(255, alpha)), width=3)

    # tapered tail when one-headed
    if heads == 1:
        d.polygon([
            (cx+length/2-width*.08, cy-width*.12),
            (cx+length/2+width*.25, cy),
            (cx+length/2-width*.08, cy+width*.12),
        ], fill=(*body_color, alpha), outline=(*outline, min(255, alpha)))

    for hx, hy in head_centres:
        direction = -1 if hx < cx else 1
        # triangular auricles
        d.polygon([
            (hx, hy-width*.20),
            (hx-direction*width*.18, hy-width*.43),
            (hx+direction*width*.05, hy-width*.29),
        ], fill=(*body_color, alpha), outline=(*outline, alpha))
        d.polygon([
            (hx, hy+width*.20),
            (hx-direction*width*.18, hy+width*.43),
            (hx+direction*width*.05, hy+width*.29),
        ], fill=(*body_color, alpha), outline=(*outline, alpha))
        # eyes
        ex = hx + direction * width*.035
        for oy in (-width*.11, width*.11):
            d.ellipse((ex-4, hy+oy-4, ex+4, hy+oy+4), fill=(*INK, alpha))


def current_path(cx, cy, length, amp, phase=0.0, samples=160):
    pts = []
    for i in range(samples):
        q = i / (samples - 1)
        x = cx - length/2 + q * length
        envelope = math.sin(math.pi * q) ** .55
        y = cy + math.sin(q * math.tau * 4 + phase) * amp * envelope
        pts.append((x, y))
    return pts


def draw_cell_network(im, nodes, edges, reveal=1.0, pulse_phase=0.0):
    d = ImageDraw.Draw(im)
    for ei, (a, b) in enumerate(edges):
        q = clamp(reveal * len(edges) - ei)
        if q <= 0:
            continue
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        end = (lerp(x1, x2, ease(q)), lerp(y1, y2, ease(q)))
        d.line((x1, y1, *end), fill=(*CYAN, int(125+75*q)), width=3)
    for i, (x, y) in enumerate(nodes):
        q = clamp(reveal * len(nodes) - i)
        if q <= 0:
            continue
        r = 12 + 3 * pulse(pulse_phase, 1.1, i*.13)
        d.ellipse((x-r, y-r, x+r, y+r), fill=(*PALE_CYAN, int(230*q)),
                  outline=(*DEEP_CYAN, int(190*q)), width=2)


# =============================================================================
# VISUALS
# =============================================================================

def vis_hidden_shape(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.42
    draw_planarian(im, cx, cy, w*.60, h*.16, heads=1, phase=t*.25)

    # Hidden alternate morphology appears only as a subsurface electrical topology.
    reveal = smoothstep(.22, .75, u)
    path = current_path(cx, cy, w*.48, h*.035, t*.55)
    glow_line(im, partial(path, reveal), VIOLET, 5, int(110+100*reveal), 14)
    if reveal > .62:
        for x in (cx-w*.20, cx+w*.20):
            glow_circle(im, x, cy, 11, GOLD, int(100+80*reveal), 10)
    seal(im, "ONE BODY · TWO POSSIBLE COMPLETIONS",
         "visible anatomy does not exhaust the state of the tissue", VIOLET)


def vis_cut_and_regenerate(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cy = h*.42
    stage1 = smoothstep(.00, .26, u)
    stage2 = smoothstep(.25, .45, u)
    stage3 = smoothstep(.44, .98, u)

    # intact worm contracts into fragments
    if stage2 < 1:
        draw_planarian(im, w*.50, cy, w*.63, h*.15, heads=1,
                       phase=t*.2, alpha=int(255*(1-stage2*.15)))
        for x in (w*.40, w*.60):
            cut_alpha = int(220*stage2)
            d.line((x, cy-h*.12, x, cy+h*.12), fill=(*CRIMSON, cut_alpha), width=5)

    # fragments separate and regrow
    if stage2 > .15:
        pieces = [
            (w*.24, 1, GREEN),
            (w*.50, p.get("middle_heads", 2), VIOLET),
            (w*.76, 1, GREEN),
        ]
        for idx, (cx, heads, col) in enumerate(pieces):
            sep = ease(stage2)
            local = clamp(stage3*3-idx)
            length = lerp(w*.10, w*.20, ease(local))
            width = lerp(h*.09, h*.13, ease(local))
            draw_planarian(im, cx, cy, length, width, heads=heads,
                           body_color=mix(PALE_CYAN, PALE_VIOLET if heads==2 else PALE_GREEN, .35),
                           outline=col, phase=t*.25)
            if local < .78:
                d.line((cx, cy-h*.09, cx, cy+h*.09), fill=(*CRIMSON, 170), width=3)

    seal(im, "THE WOUND ASKS A QUESTION",
         "what body should this fragment complete?")


def vis_voltage_membrane(im, u, t, p):
    w, h = im.size
    d = ImageDraw.Draw(im)
    cx, cy = w*.50, h*.40
    radius = min(w, h)*.20
    breathe = 1 + .025*math.sin(t*1.3)
    r = radius*breathe

    # membrane bilayer
    for ring, col in ((r, DEEP_CYAN), (r-18, CYAN)):
        d.ellipse((cx-ring, cy-ring, cx+ring, cy+ring), outline=(*col, 190), width=4)

    # ions move through channels
    channels = 10
    reveal = ease(u)
    for i in range(channels):
        a = i*math.tau/channels
        x1, y1 = cx+math.cos(a)*(r-30), cy+math.sin(a)*(r-30)
        x2, y2 = cx+math.cos(a)*(r+34), cy+math.sin(a)*(r+34)
        d.line((x1,y1,x2,y2), fill=(*INK, 115), width=5)
        ion_q = (t*.35+i/channels) % 1
        ion_q = ion_q if i%2==0 else 1-ion_q
        x, y = lerp(x1,x2,ion_q), lerp(y1,y2,ion_q)
        glow_circle(im, x, y, 7, GOLD if i%2==0 else CRIMSON, 150, 7)

    # voltage field
    for j in range(5):
        rr = r + 42 + j*24
        alpha = int(115*(1-j/5)*reveal)
        d.arc((cx-rr,cy-rr,cx+rr,cy+rr), 210, 330, fill=(*CYAN,alpha), width=3)
        d.arc((cx-rr,cy-rr,cx+rr,cy+rr), 30, 150, fill=(*CRIMSON,alpha), width=3)

    seal(im, "MEMBRANE POTENTIAL",
         "every living cell maintains an electrical difference")


def vis_gap_junction_network(im, u, t, p):
    w, h = im.size
    rng = random.Random(73)
    nodes = []
    cols, rows = 9, 5
    for j in range(rows):
        for i in range(cols):
            x = w*.18 + i*w*.64/(cols-1) + rng.uniform(-12,12)
            y = h*.22 + j*h*.40/(rows-1) + rng.uniform(-9,9)
            nodes.append((x,y))
    edges = []
    for j in range(rows):
        for i in range(cols):
            idx=j*cols+i
            if i<cols-1: edges.append((idx,idx+1))
            if j<rows-1: edges.append((idx,idx+cols))
            if i<cols-1 and j<rows-1 and (i+j)%2==0:
                edges.append((idx,idx+cols+1))
    draw_cell_network(im,nodes,edges,ease(u),t)

    # moving voltage wave
    wave_x = lerp(w*.15,w*.85,ease(u))
    gl = layer(im.size)
    gd = ImageDraw.Draw(gl)
    gd.rectangle((wave_x-34,h*.16,wave_x+34,h*.68),fill=(*CYAN,35))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22)))
    seal(im,"THE PATTERN BELONGS TO THE RELATION",
         "gap junctions turn neighboring cells into a tissue-scale network")


def vis_perturbation_memory(im, u, t, p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.41
    draw_planarian(im,cx,cy,w*.62,h*.15,heads=1,phase=t*.18)

    path=current_path(cx,cy,w*.50,h*.034,t*.45)
    glow_line(im,path,CYAN,4,190,11)

    # brief crimson pulse flips network into violet attractor
    pulse_in=smoothstep(.08,.28,u)*(1-smoothstep(.40,.54,u))
    if pulse_in>0:
        gl=layer(im.size)
        gd=ImageDraw.Draw(gl)
        gd.rectangle((w*.42,h*.22,w*.58,h*.61),fill=(*CRIMSON,int(140*pulse_in)))
        im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(25)))

    switch=smoothstep(.26,.62,u)
    alt=current_path(cx,cy,w*.50,h*.055,t*.7+1.2)
    glow_line(im,partial(alt,switch),VIOLET,5,int(100+120*switch),14)

    # perturbation vanishes but state remains
    if u>.60:
        centered(d,(w*.50,h*.20),"THE INPUT IS GONE",font(FONT_SANS_BOLD,int(h*.022)),SOFT_INK)

    seal(im,"A BRIEF INPUT · A PERSISTENT STATE",
         "the tissue keeps the decision after the intervention disappears",VIOLET)


def vis_normal_carrier(im,u,t,p):
    w,h=im.size
    cx,cy=w*.50,h*.42
    draw_planarian(im,cx,cy,w*.62,h*.15,heads=1,phase=t*.16)

    # hidden line fades beneath ordinary anatomy
    visible=1-smoothstep(.12,.60,u)
    hidden=current_path(cx,cy,w*.48,h*.052,t*.45+1)
    glow_line(im,hidden,VIOLET,5,int(35+155*visible),14)

    if u>.55:
        seal(im,"NORMAL ANATOMY · ALTERED FUTURE",
             "the present body does not reveal the whole state",VIOLET)
    else:
        seal(im,"THE HIDDEN ATTRACTOR REMAINS",
             "cryptic memory survives beneath ordinary form")


def vis_second_cut(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cy=h*.42
    cut=smoothstep(.12,.32,u)
    separate=smoothstep(.28,.48,u)
    regrow=smoothstep(.47,.98,u)

    if separate<1:
        draw_planarian(im,w*.50,cy,w*.62,h*.15,heads=1,phase=t*.16)
        hidden=current_path(w*.50,cy,w*.48,h*.052,t*.5)
        glow_line(im,hidden,VIOLET,5,185,14)
        for x in (w*.42,w*.58):
            d.line((x,cy-h*.12,x,cy+h*.12),fill=(*CRIMSON,int(220*cut)),width=5)

    if separate>.1:
        outcomes=[(w*.29,1,GREEN),(w*.51,2,VIOLET),(w*.73,2,VIOLET)]
        for i,(cx,heads,col) in enumerate(outcomes):
            q=clamp(regrow*3-i*.45)
            draw_planarian(im,cx,cy,lerp(w*.09,w*.20,ease(q)),
                           lerp(h*.08,h*.13,ease(q)),heads=heads,
                           body_color=PALE_VIOLET if heads==2 else PALE_GREEN,
                           outline=col,phase=t*.20)
    seal(im,"THE SECOND WOUND REVEALS THE FIRST CHANGE",
         "the knife does not create the hidden state; it interrogates it")


def vis_attractor_landscape(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left,right=w*.12,w*.88
    base=h*.63
    pts=[]
    for i in range(260):
        q=i/259
        # triple basin with one dominant and one cryptic alternative
        v=(q-.25)**2*(q-.53)**2*(q-.78)**2
        y=base-v*h*27
        pts.append((lerp(left,right,q),y))
    d.line(pts,fill=(*INK,200),width=4)

    # ball settles into chosen attractor
    start=.50
    target=p.get("target",.76)
    settle=ease(u)
    q=lerp(start,target,settle)
    x=lerp(left,right,q)
    # nearest curve y
    idx=int(q*259)
    y=pts[max(0,min(259,idx))][1]-16
    glow_circle(im,x,y,15,VIOLET if target>.6 else GREEN,180,10)

    for q0,label,col in ((.25,"HEAD–TAIL",GREEN),(.78,"HEAD–HEAD",VIOLET)):
        x0=lerp(left,right,q0)
        centered(d,(x0,h*.72),label,font(FONT_SANS_BOLD,int(h*.018)),col)

    seal(im,"MULTISTABLE ANATOMY",
         "one network can settle into more than one enduring completion")


def vis_switch(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    left=(w*.30,cy)
    right=(w*.70,cy)

    # bistable rail
    d.arc((w*.24,h*.24,w*.76,h*.59),200,340,fill=(*INK,160),width=5)
    q=ease(u)
    x=lerp(left[0],right[0],q)
    y=cy-math.sin(q*math.pi)*h*.15
    glow_circle(im,x,y,17,VIOLET if q>.5 else GREEN,180,11)
    d.line((left[0],cy+70,right[0],cy+70),fill=(*SILVER,150),width=3)

    centered(d,(left[0],h*.65),"WILD TYPE",font(FONT_SANS_BOLD,int(h*.020)),GREEN)
    centered(d,(right[0],h*.65),"ALTERED POLARITY",font(FONT_SANS_BOLD,int(h*.020)),VIOLET)

    seal(im,"THE HAND LEAVES · THE STATE REMAINS",
         "a biological switch preserves its chosen position")


def vis_memory_not_picture(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    split=w*.50

    # left: false miniature image
    alpha=int(210*(1-smoothstep(.32,.78,u)))
    d.rounded_rectangle((w*.10,h*.20,w*.42,h*.65),radius=24,
                        fill=(*PALE_SILVER,190),outline=(*SILVER,150),width=3)
    draw_planarian(im,w*.26,h*.42,w*.20,h*.08,heads=2,
                   body_color=PALE_VIOLET,outline=VIOLET,alpha=alpha)
    centered(d,(w*.26,h*.62),"PICTURE",font(FONT_SANS_BOLD,int(h*.020)),(*CRIMSON,alpha))
    if u>.38:
        d.line((w*.14,h*.24,w*.38,h*.60),fill=(*CRIMSON,210),width=5)
        d.line((w*.38,h*.24,w*.14,h*.60),fill=(*CRIMSON,210),width=5)

    # right: rule as vector field
    d.rounded_rectangle((w*.58,h*.20,w*.90,h*.65),radius=24,
                        fill=(*PALE_CYAN,100),outline=(*CYAN,160),width=3)
    reveal=ease(u)
    for j in range(5):
        for i in range(5):
            x=w*.62+i*w*.24/4
            y=h*.26+j*h*.30/4
            target=(w*.75,h*.42)
            dx=(target[0]-x)*.16
            dy=(target[1]-y)*.16
            arrow(d,(x,y),(x+dx*reveal,y+dy*reveal),CYAN,2,6)
    centered(d,(w*.74,h*.62),"RULE",font(FONT_SANS_BOLD,int(h*.020)),DEEP_CYAN)

    seal(im,"MEMORY NEED NOT BE A PICTURE",
         "it may be a stable rule for how to complete the body")


def vis_wound_exam(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.42
    draw_planarian(im,cx,cy,w*.58,h*.14,heads=1,phase=t*.2)

    # question mark made from cut and current
    cut=smoothstep(.12,.32,u)
    d.line((cx,cy-h*.12,cx,cy+h*.12),fill=(*CRIMSON,int(220*cut)),width=5)
    qpath=[]
    for i in range(100):
        q=i/99
        a=lerp(-math.pi*.2,math.pi*1.25,q)
        qpath.append((cx+math.cos(a)*75,cy-h*.19+math.sin(a)*52))
    qpath += [(cx,cy-h*.03),(cx,cy+h*.02)]
    glow_line(im,partial(qpath,smoothstep(.28,.82,u)),GOLD,5,200,13)
    if u>.75:
        glow_circle(im,cx,cy+h*.08,8,GOLD,180,8)
    seal(im,"THE WOUND ACTS LIKE AN EXAMINATION",
         "the hidden physiological state supplies the answer")


def vis_counterfactual_body(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.41

    # present body in center
    draw_planarian(im,cx,cy,w*.34,h*.12,heads=1,phase=t*.18)

    # possible futures branch outward
    branch=smoothstep(.15,.65,u)
    origins=[(cx-w*.13,cy),(cx+w*.13,cy)]
    targets=[
        (w*.20,h*.24,1,GREEN),
        (w*.20,h*.59,2,VIOLET),
        (w*.80,h*.24,1,GREEN),
        (w*.80,h*.59,2,VIOLET),
    ]
    for idx,(tx,ty,heads,col) in enumerate(targets):
        ox,oy=origins[idx%2]
        mid=(lerp(ox,tx,.45),lerp(oy,ty,.45)+(ty-cy)*.1)
        pts=[(ox,oy),mid,(tx,ty)]
        glow_line(im,partial(pts,branch),col,3,130,9)
        q=clamp(branch*2-idx*.12)
        if q>.35:
            draw_planarian(im,tx,ty,w*.16,h*.075,heads=heads,
                           body_color=PALE_GREEN if heads==1 else PALE_VIOLET,
                           outline=col,alpha=int(230*q),phase=t*.15)
    seal(im,"IDENTITY INCLUDES COUNTERFACTUALS",
         "what will this system defend, repair, reject, or accept?")


def vis_spatial_information(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.42
    # fragment
    draw_planarian(im,cx,cy,w*.34,h*.13,heads=0,phase=t*.2)
    d.line((cx-w*.17,cy-h*.09,cx-w*.17,cy+h*.09),fill=(*CRIMSON,180),width=3)
    d.line((cx+w*.17,cy-h*.09,cx+w*.17,cy+h*.09),fill=(*CRIMSON,180),width=3)

    # tissue polls remote state
    reveal=ease(u)
    nodes=[]
    for j in range(4):
        for i in range(7):
            nodes.append((cx-w*.13+i*w*.26/6,cy-h*.07+j*h*.14/3))
    for i,(x,y) in enumerate(nodes):
        q=clamp(reveal*len(nodes)-i)
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*PALE_CYAN,int(220*q)),
                  outline=(*CYAN,int(170*q)))
        if i%7<6:
            x2,y2=nodes[i+1]
            d.line((x,y,x2,y2),fill=(*CYAN,int(90*q)),width=2)

    # global polarity gradient
    gl=layer(im.size)
    gd=ImageDraw.Draw(gl)
    for i in range(100):
        q=i/99
        col=mix(GOLD,VIOLET,q)
        x=lerp(cx-w*.17,cx+w*.17,q)
        gd.line((x,cy-h*.11,x,cy+h*.11),fill=(*col,int(70*reveal)),width=3)
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(8)))
    seal(im,"SPATIAL INFORMATION",
         "local cells consult a state larger than any one cell can see")


def vis_local_to_global(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.41
    # many local cells
    rng=random.Random(28)
    cells=[]
    for i in range(70):
        a=rng.uniform(0,math.tau)
        r=(rng.random()**.55)*min(w,h)*.21
        cells.append((cx+math.cos(a)*r*1.8,cy+math.sin(a)*r))
    gather=smoothstep(.12,.82,u)
    for i,(x,y) in enumerate(cells):
        r=8
        d.ellipse((x-r,y-r,x+r,y+r),fill=(*PALE_CYAN,220),outline=(*CYAN,145))
        if gather>.25:
            tx=cx+math.cos(i/len(cells)*math.tau)*w*.19
            ty=cy+math.sin(i/len(cells)*math.tau)*h*.12
            d.line((x,y,lerp(x,tx,gather),lerp(y,ty,gather)),
                   fill=(*CYAN,int(100*gather)),width=2)

    if gather>.58:
        draw_planarian(im,cx,cy,w*.48,h*.15,heads=1,
                       body_color=(255,255,255),outline=GOLD,
                       alpha=int(220*(gather-.58)/.42),phase=t*.15)
    seal(im,"LOCAL COMPETENCE · LARGER GOAL",
         "cells contribute to a future body none can inhabit alone")


def vis_message_messengers(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cy=h*.42
    # Persistent cyan message
    message=current_path(w*.50,cy,w*.68,h*.04,t*.5)
    glow_line(im,message,CYAN,5,205,13)

    # Carrier cells dissolve and are replaced
    rng=random.Random(90)
    for i in range(46):
        q=i/45
        x=lerp(w*.16,w*.84,q)
        y=cy+math.sin(q*math.tau*4+t*.5)*h*.06
        generation=(u*2+q) % 1
        alpha=int(220*abs(math.cos(generation*math.pi)))
        col=PALE_GREEN if generation>.5 else PALE_VIOLET
        d.ellipse((x-11,y-11,x+11,y+11),fill=(*col,alpha),
                  outline=(*SOFT_INK,min(150,alpha)),width=2)
    seal(im,"THE MESSAGE PERSISTS WHILE MESSENGERS CHANGE",
         "memory must survive turnover, damage, and replacement")


def vis_city_repair(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    # abstract city grid continually replaced
    cols,rows=9,5
    reveal=ease(u)
    for j in range(rows):
        for i in range(cols):
            x=w*.16+i*w*.68/(cols-1)
            y=h*.20+j*h*.42/(rows-1)
            replace=(u*1.7+(i+j)*.11)%1
            col=CYAN if replace<.55 else GOLD
            alpha=int(100+120*abs(math.sin(replace*math.pi)))
            d.rounded_rectangle((x-18,y-13,x+18,y+13),radius=5,
                                fill=(*mix(WHITE,col,.18),alpha),
                                outline=(*col,alpha),width=2)
            if i<cols-1:
                d.line((x+18,y,x+w*.68/(cols-1)-18,y),
                       fill=(*SILVER,120),width=2)
            if j<rows-1:
                d.line((x,y+13,x,y+h*.42/(rows-1)-13),
                       fill=(*SILVER,120),width=2)

    # gold target plan survives over moving infrastructure
    if reveal>.32:
        d.ellipse((w*.38,h*.26,w*.62,h*.55),outline=(*GOLD,int(190*reveal)),width=5)
        d.line((w*.50,h*.26,w*.50,h*.55),fill=(*GOLD,int(110*reveal)),width=3)
    seal(im,"REPAIR THE CITY WHILE REPLACING ITS MAP",
         "robust control cannot depend on one exact arrangement of parts")


def vis_reset(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    left,right=w*.12,w*.88
    cy=h*.42

    # Attractor landscape morphs from violet basin back to green basin
    shift=ease(u)
    pts=[]
    for i in range(260):
        q=i/259
        left_depth=lerp(.5,1.35,shift)
        right_depth=lerp(1.35,.5,shift)
        y=h*.62 - h*.20*(
            left_depth*math.exp(-((q-.28)/.12)**2)
            + right_depth*math.exp(-((q-.74)/.12)**2)
        )
        pts.append((lerp(left,right,q),y))
    d.line(pts,fill=(*INK,190),width=4)

    q=lerp(.74,.28,shift)
    idx=int(q*259)
    x,y=pts[idx]
    glow_circle(im,x,y-14,15,mix(VIOLET,GREEN,shift),190,10)

    centered(d,(w*.30,h*.69),"WILD TYPE",font(FONT_SANS_BOLD,int(h*.018)),GREEN)
    centered(d,(w*.70,h*.69),"ALTERED",font(FONT_SANS_BOLD,int(h*.018)),VIOLET)
    seal(im,"PHYSIOLOGICAL MEMORY CAN BE EDITED",
         "persistent does not mean permanently fixed",GREEN)


def vis_morphoceutical(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.41

    # no micromanaging cells: adjust field, cells self-organize
    rng=random.Random(61)
    cells=[]
    for i in range(100):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.6)*min(w,h)*.22
        cells.append([cx+math.cos(a)*rr*1.6,cy+math.sin(a)*rr])

    field=smoothstep(.10,.58,u)
    for i,(x,y) in enumerate(cells):
        target_x=cx+(x-cx)*(.74+field*.10)
        target_y=cy+(y-cy)*(.74+field*.05)
        xx=lerp(x,target_x,field)
        yy=lerp(y,target_y,field)
        col=mix(PALE_CYAN,PALE_GREEN,field)
        d.ellipse((xx-7,yy-7,xx+7,yy+7),fill=(*col,220),outline=(*CYAN,120))

    # apply one field-level intervention
    if u>.24:
        for j in range(6):
            rr=lerp(w*.29,w*.12,j/5)
            alpha=int(65*field*(1-j/7))
            d.ellipse((cx-rr,cy-rr*.55,cx+rr,cy+rr*.55),
                      outline=(*GOLD,alpha),width=3)

    if field>.58:
        draw_planarian(im,cx,cy,w*.45,h*.14,heads=1,
                       body_color=(255,255,255),outline=GREEN,
                       alpha=int(220*(field-.58)/.42),phase=t*.15)
    seal(im,"TARGET THE CONTROL LAYER",
         "change the collective instruction rather than place every cell")


def vis_caution(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    statements=[
        ("PLANARIA",GREEN,True),
        ("PERSISTENT BIOELECTRIC STATE",CYAN,True),
        ("HUMAN ORGAN REGENERATION",CRIMSON,False),
        ("CLINICAL TREATMENT",CRIMSON,False),
    ]
    reveal=u*len(statements)
    for i,(text,col,valid) in enumerate(statements):
        q=clamp(reveal-i)
        y=h*(.23+i*.13)
        d.rounded_rectangle((w*.22,y-28,w*.78,y+28),radius=15,
                            fill=(*mix(WHITE,col,.10),int(230*q)),
                            outline=(*col,int(180*q)),width=2)
        centered(d,(w*.46,y),text,font(FONT_SANS_BOLD,int(h*.020)),(*INK,int(220*q)))
        symbol="SUPPORTED" if valid else "NOT ESTABLISHED"
        centered(d,(w*.69,y),symbol,font(FONT_SANS_BOLD,int(h*.016)),(*col,int(220*q)))
    seal(im,"KEEP THE CLAIM NARROW",
         "strange evidence does not need speculative inflation")


def vis_identity_layers(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    layers=[
        ("GENES",w*.34,h*.26,GOLD),
        ("PHYSIOLOGY",w*.66,h*.26,CYAN),
        ("ANATOMY",w*.34,h*.55,GREEN),
        ("RESPONSE",w*.66,h*.55,VIOLET),
    ]
    reveal=u*len(layers)
    for i,(name,x,y,col) in enumerate(layers):
        q=clamp(reveal-i)
        rr=lerp(0,74,ease_out(q))
        d.ellipse((x-rr,y-rr*.63,x+rr,y+rr*.63),
                  fill=(*mix(WHITE,col,.12),int(220*q)),
                  outline=(*col,int(190*q)),width=3)
        if q>.45:
            centered(d,(x,y),name,font(FONT_SANS_BOLD,int(h*.020)),col)
    if u>.55:
        for a in range(len(layers)):
            for b in range(a+1,len(layers)):
                x1,y1=layers[a][1:3]
                x2,y2=layers[b][1:3]
                d.line((x1,y1,x2,y2),fill=(*SILVER,75),width=2)
    glow_circle(im,cx,cy,14,GOLD,140,10)
    seal(im,"THE BODY'S IDENTITY IS DISTRIBUTED",
         "material, memory, present form, and future response")


def vis_human_analogy(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.42
    mode=p.get("mode","calm")

    # simplified human silhouette
    d.ellipse((cx-35,cy-150,cx+35,cy-80),outline=(*INK,210),width=4)
    d.line((cx,cy-80,cx,cy+80),fill=(*INK,210),width=5)
    d.line((cx,cy-25,cx-80,cy+20),fill=(*INK,210),width=4)
    d.line((cx,cy-25,cx+80,cy+20),fill=(*INK,210),width=4)
    d.line((cx,cy+80,cx-55,cy+155),fill=(*INK,210),width=4)
    d.line((cx,cy+80,cx+55,cy+155),fill=(*INK,210),width=4)

    if mode=="trigger":
        event=smoothstep(.18,.45,u)
        wave=[]
        for i in range(120):
            q=i/119
            x=lerp(w*.12,cx-50,q)
            y=cy-40+math.sin(q*math.tau*5-t*3)*18*(1-q)
            wave.append((x,y))
        glow_line(im,partial(wave,event),CRIMSON,4,190,12)
        react=smoothstep(.42,.85,u)
        for rr in range(40,170,26):
            d.arc((cx-rr,cy-rr,cx+rr,cy+rr),200,340,
                  fill=(*VIOLET,int(120*react*(1-rr/200))),width=3)
        seal(im,"A HIDDEN STATE CAN WAIT FOR ITS CONDITION",
             "present calm does not exhaust stored response",VIOLET)
    else:
        for rr in range(50,155,28):
            d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),
                      outline=(*CYAN,55),width=2)
        seal(im,"THE ANALOGY MUST REMAIN CAUTIOUS",
             "human memory and planarian pattern memory are not one mechanism")


def vis_final(im,u,t,p):
    w,h=im.size
    d=ImageDraw.Draw(im)
    cy=h*.42
    cut=smoothstep(.08,.24,u)
    reveal=smoothstep(.24,.56,u)
    regrow=smoothstep(.52,.98,u)

    # One-headed present body
    if regrow<.70:
        draw_planarian(im,w*.50,cy,w*.62,h*.15,heads=1,phase=t*.18,
                       alpha=int(255*(1-regrow*.45)))
        hidden=current_path(w*.50,cy,w*.48,h*.055,t*.55)
        glow_line(im,hidden,VIOLET,5,int(70+120*reveal),14)
        d.line((w*.50,cy-h*.12,w*.50,cy+h*.12),
               fill=(*CRIMSON,int(220*cut)),width=5)

    # Remembered future enters visible matter
    if regrow>.20:
        alpha=int(255*smoothstep(.20,.72,regrow))
        draw_planarian(im,w*.50,cy,w*.62,h*.16,heads=2,
                       body_color=PALE_VIOLET,outline=VIOLET,
                       alpha=alpha,phase=t*.18)
        path=current_path(w*.50,cy,w*.48,h*.052,t*.65)
        glow_line(im,path,GOLD,5,int(120+110*regrow),15)

    seal(im,"THE BODY REMEMBERS A SHAPE IT IS NOT WEARING",
         "memory may be an instruction about what should exist when form breaks",VIOLET)


VISUALS: dict[str, Callable] = {
    "hidden_shape": vis_hidden_shape,
    "cut_regenerate": vis_cut_and_regenerate,
    "membrane": vis_voltage_membrane,
    "network": vis_gap_junction_network,
    "perturb": vis_perturbation_memory,
    "normal_carrier": vis_normal_carrier,
    "second_cut": vis_second_cut,
    "attractor": vis_attractor_landscape,
    "switch": vis_switch,
    "rule": vis_memory_not_picture,
    "wound_exam": vis_wound_exam,
    "counterfactual": vis_counterfactual_body,
    "spatial": vis_spatial_information,
    "local_global": vis_local_to_global,
    "message": vis_message_messengers,
    "city": vis_city_repair,
    "reset": vis_reset,
    "morphoceutical": vis_morphoceutical,
    "caution": vis_caution,
    "identity": vis_identity_layers,
    "human": vis_human_analogy,
    "final": vis_final,
}


# =============================================================================
# TIMED ESSAY
# =============================================================================

@dataclass
class Scene:
    title: str
    narration: str
    duration: float
    visual: str
    params: dict


SCENES = [
    Scene("Ordinary carrier",
          "A flatworm can look completely ordinary while carrying the memory of another body.",
          8.0,"hidden_shape",{}),
    Scene("One head",
          "One head. One tail. Normal movement. Normal anatomy.",
          6.0,"hidden_shape",{}),
    Scene("The cut",
          "Then it is cut.",
          5.5,"cut_regenerate",{"middle_heads":2}),
    Scene("Different completions",
          "Some fragments rebuild the expected animal. Others produce two heads.",
          8.0,"cut_regenerate",{"middle_heads":2}),
    Scene("Hidden before the knife",
          "The hidden difference was present before the knife. The body was wearing one shape while remembering another.",
          9.0,"hidden_shape",{}),

    Scene("Regenerative problem",
          "A middle fragment must determine which wound faces forward, which faces backward, what is missing, how much to build, and when to stop.",
          9.5,"spatial",{}),
    Scene("Same genome",
          "Genes matter at every stage. But the same genome can support more than one regenerative outcome.",
          8.0,"counterfactual",{}),
    Scene("Which whole",
          "The question is not only what parts the cells can produce. It is which whole the collective is trying to restore.",
          9.0,"local_global",{}),

    Scene("Voltage",
          "Every living cell maintains a voltage across its membrane.",
          6.5,"membrane",{}),
    Scene("Ions and pumps",
          "Ion channels and pumps move charged particles, creating a difference between inside and outside.",
          8.0,"membrane",{}),
    Scene("Older than nerves",
          "Electrical communication is far older and more widespread than nervous systems.",
          7.5,"network",{}),
    Scene("Gap junctions",
          "Gap junctions allow ions and small signals to pass directly between neighboring cells.",
          8.0,"network",{}),
    Scene("Tissue network",
          "A tissue can therefore form an electrical network. The pattern belongs to no single cell. It exists across their relation.",
          9.5,"network",{}),

    Scene("Brief intervention",
          "In planaria, a brief perturbation of endogenous bioelectric communication can create a persistent change in regeneration.",
          9.0,"perturb",{}),
    Scene("DNA unchanged",
          "The treatment does not permanently rewrite the animals' DNA, and it need not remain present during every later injury.",
          9.0,"perturb",{}),
    Scene("Normal outside",
          "Some treated worms regenerate with normal one-head, one-tail anatomy while carrying a hidden alteration.",
          8.5,"normal_carrier",{}),
    Scene("Cut again",
          "Cut those apparently normal worms again in ordinary water, and some fragments produce the altered pattern.",
          9.0,"second_cut",{}),
    Scene("Future decision",
          "A temporary intervention has changed a future anatomical decision. The current body does not reveal the whole state.",
          9.0,"normal_carrier",{}),

    Scene("Multistability",
          "Researchers describe this as a multistable anatomical switch.",
          6.5,"switch",{}),
    Scene("Two attractors",
          "One attractor guides head-tail anatomy. Another guides head-head anatomy.",
          8.0,"attractor",{"target":.76}),
    Scene("Inside a prior state",
          "The tissue is not merely reacting to the wound. It interprets the wound from inside a previously stabilized physiological state.",
          9.5,"attractor",{"target":.76}),
    Scene("Switch holds",
          "Like a light switch, the input can be brief while the circuit preserves the state.",
          7.5,"switch",{}),

    Scene("Memory",
          "This is why the word memory becomes useful.",
          5.5,"rule",{}),
    Scene("Not recollection",
          "The worm does not need to recall a mental picture of having two heads.",
          7.0,"rule",{}),
    Scene("Stable trace",
          "Memory here means that a past event leaves a stable, reactivatable trace capable of changing later action.",
          9.0,"perturb",{}),
    Scene("Rule not image",
          "The memory may be less like a picture and more like a rule: when injury occurs, complete the body according to this relation.",
          9.5,"rule",{}),

    Scene("Cryptic until tested",
          "A biological attractor can remain cryptic until injury forces the network to answer a question.",
          8.0,"wound_exam",{}),
    Scene("Question",
          "What should this body become now?",
          5.5,"wound_exam",{}),
    Scene("Examination",
          "The wound acts like an examination. The hidden memory supplies the answer.",
          8.0,"wound_exam",{}),

    Scene("Anatomy is one layer",
          "We usually treat current shape as the final truth of a body. Regenerative biology reveals that anatomy is only one layer.",
          9.5,"identity",{}),
    Scene("Range of defended shapes",
          "The body is also the range of forms it will defend, repair, regenerate, or accept as the new normal.",
          9.0,"counterfactual",{}),
    Scene("Counterfactual identity",
          "Identity includes counterfactuals: what would this system do if cut here? What would it rebuild if one part vanished?",
          9.5,"counterfactual",{}),

    Scene("Spatial information",
          "Regeneration is a problem of spatial information.",
          6.0,"spatial",{}),
    Scene("Local polling",
          "Cells at a wound must determine where they are, what exists elsewhere, and what does not need to be rebuilt.",
          9.0,"spatial",{}),
    Scene("Whole available to parts",
          "The body coordinates by making the whole partially available to the parts.",
          8.0,"spatial",{}),

    Scene("Larger self",
          "That coordination creates a larger biological self.",
          6.5,"local_global",{}),
    Scene("Local lives",
          "Each cell regulates its own interior, yet regeneration requires action for an outcome far larger than any individual cell.",
          9.5,"local_global",{}),
    Scene("Captured competence",
          "Multicellularity is local competence captured by a larger goal.",
          7.5,"local_global",{}),

    Scene("Ancient electrical language",
          "Bioelectric networks can preserve global states even as individual cells change.",
          8.0,"message",{}),
    Scene("Before the brain",
          "The brain did not invent voltage. It inherited an ancient language and accelerated it.",
          8.0,"message",{}),
    Scene("Changing carriers",
          "A regenerative control system must preserve relevant information while the material carrying that information is changing.",
          9.5,"message",{}),
    Scene("City under repair",
          "Imagine repairing a city while roads, maps, workers, and communication lines are all being replaced.",
          9.0,"city",{}),
    Scene("Message survives",
          "The message persists while the messengers change.",
          6.5,"message",{}),

    Scene("Reset",
          "The altered bioelectric state can also be reset.",
          6.0,"reset",{}),
    Scene("Persistent not fixed",
          "The hidden pattern is persistent, but not absolutely fixed. Physiological memory can be edited.",
          8.5,"reset",{}),
    Scene("Landscape of goals",
          "Between genetic destiny and shapeless plasticity lies a landscape of remembered goals.",
          8.5,"attractor",{"target":.25}),

    Scene("Control layer",
          "If tissues store preferred states in distributed networks, medicine may eventually learn to alter the information guiding the collective.",
          9.5,"morphoceutical",{}),
    Scene("No micromanagement",
          "Instead of placing every cell, an intervention could change the control layer and let the tissue solve the construction problem.",
          9.5,"morphoceutical",{}),
    Scene("Research program",
          "This is a research program, not an established human treatment.",
          7.0,"caution",{}),
    Scene("Keep narrow",
          "Planarian results do not show that complex human organs can be regenerated by changing a few voltages.",
          8.5,"caution",{}),

    Scene("Where is true form",
          "Where is the body's true form? In the genome? Its current anatomy? The electrical network? Its developmental history?",
          9.5,"identity",{}),
    Scene("No single answer",
          "No single answer is sufficient.",
          5.5,"identity",{}),
    Scene("Distributed identity",
          "Genes define possibilities. Physiology stabilizes patterns. Anatomy expresses one outcome. Injury reveals the target the system attempts to recover.",
          10.0,"identity",{}),

    Scene("Specific evidence",
          "The evidence is specific: temporary alteration of planarian bioelectric networks can produce persistent, rewriteable changes in later regenerative anatomy.",
          10.0,"caution",{}),
    Scene("Strange enough",
          "That claim is narrow enough to be scientific, and strange enough without metaphysical decoration.",
          8.0,"caution",{}),

    Scene("Human comparison",
          "Your own body also preserves futures beneath its present appearance, though the comparison must remain cautious.",
          8.5,"human",{"mode":"calm"}),
    Scene("Hidden response",
          "A person may seem calm until a situation reactivates an old defensive state. A skill may remain invisible until conditions call it forth.",
          9.5,"human",{"mode":"trigger"}),
    Scene("Present not exhaustive",
          "Present form does not exhaust stored possibility. What a system is includes how it will answer disruption.",
          9.0,"counterfactual",{}),

    Scene("Return",
          "A flatworm can look completely ordinary while carrying the memory of another body.",
          8.0,"normal_carrier",{}),
    Scene("Question opens",
          "The hidden pattern waits without announcing itself. Then injury opens the question.",
          8.5,"wound_exam",{}),
    Scene("Future enters matter",
          "The network responds. The remembered future enters matter.",
          7.5,"final",{}),
    Scene("Knife reveals",
          "The knife did not create the second anatomy. It revealed which completion the tissue had been prepared to call home.",
          9.5,"final",{}),
    Scene("Closing",
          "The body can remember a shape it is not wearing. Biological memory may be not only a record of what happened, but an instruction about what should exist when the world breaks again.",
          10.0,"final",{}),
]


# =============================================================================
# PIPELINE
# =============================================================================

def render_frame(scene, frame_index, frame_count, width, height, seed):
    u = frame_index / max(1, frame_count - 1)
    t = u * scene.duration
    im = scientific_field(width, height, seed)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")


def ffmpeg_path():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required but was not found on PATH")
    return ffmpeg


def encode_scene(scene_index, fps):
    output_path = SCENES_DIR / f"scene_{scene_index:03d}.mp4"
    frame_dir = FRAMES / f"scene_{scene_index:03d}"
    subprocess.run([
        ffmpeg_path(), "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "%05d.jpg"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def render_scene(index, scene, fps, width, height, preview):
    frame_dir = FRAMES / f"scene_{index:03d}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    count = max(2, round(scene.duration * fps))

    if preview:
        samples = [0, int(count*.32), int(count*.72), count-1]
        for oi, fi in enumerate(samples):
            render_frame(scene, fi, count, width, height, index*10000+fi).save(
                frame_dir / f"preview_{oi:02d}.jpg", quality=95
            )
        return frame_dir

    for fi in range(count):
        path = frame_dir / f"{fi:05d}.jpg"
        if path.exists():
            continue
        render_frame(scene, fi, count, width, height, index*10000+fi).save(
            path, quality=95, subsampling=0
        )
    return encode_scene(index, fps)


def concatenate(paths):
    concat_path = OUTPUT / "concat.txt"
    concat_path.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8"
    )
    final = OUTPUT / "body_remembers_shape.mp4"
    subprocess.run([
        ffmpeg_path(), "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(final),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return final


def export_timeline():
    cursor = 0.0
    records = []
    for i, scene in enumerate(SCENES, 1):
        item = asdict(scene)
        item["scene_id"] = f"scene_{i:03d}"
        item["start_seconds"] = round(cursor, 3)
        cursor += scene.duration
        item["end_seconds"] = round(cursor, 3)
        records.append(item)
    path = OUTPUT / "narration_timeline.json"
    path.write_text(json.dumps({
        "title": "the body can remember a shape it is not wearing",
        "scene_count": len(SCENES),
        "runtime_seconds": round(cursor, 3),
        "shot_duration_range": [5, 10],
        "continuity_object": "cyan bioelectric current-line",
        "palette_roles": {
            "ink": "visible anatomy",
            "cyan": "bioelectric communication",
            "gold": "target morphology",
            "crimson": "wound and perturbation",
            "green": "coordinated repair",
            "violet": "alternate attractor",
        },
        "scenes": records,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def contact_sheet(width, height):
    thumb_w = 320
    thumb_h = int(thumb_w * height / width)
    cols = 4
    rows = math.ceil(len(SCENES)/cols)
    cell_h = thumb_h + 48
    sheet = Image.new("RGB", (cols*thumb_w, rows*cell_h), IVORY)
    d = ImageDraw.Draw(sheet)
    lf = font(FONT_SANS_BOLD, 14)

    for i, scene in enumerate(SCENES, 1):
        count=max(2,round(scene.duration*DEFAULT_FPS))
        im=render_frame(scene,int(count*.72),count,width,height,i*10000+72)
        im.thumbnail((thumb_w,thumb_h))
        slot=i-1
        x=(slot%cols)*thumb_w
        y=(slot//cols)*cell_h
        sheet.paste(im,(x,y))
        d.text((x+9,y+thumb_h+7),f"{i:02d}  {scene.title}",font=lf,fill=INK)

    path=OUTPUT/"contact_sheet.jpg"
    sheet.save(path,quality=94)
    return path


def args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS)
    p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    p.add_argument("--scene",type=int,default=None)
    p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()


def main():
    a=args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    FRAMES.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)

    timeline=export_timeline()
    total=sum(s.duration for s in SCENES)
    print(f"Timeline: {timeline}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {total/60:.2f} minutes")

    if a.scene is not None:
        if not 1 <= a.scene <= len(SCENES):
            raise ValueError(f"--scene must be 1..{len(SCENES)}")
        result=render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)
        print(result)
        return

    rendered=[]
    for i,scene in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        result=render_scene(i,scene,a.fps,a.width,a.height,a.preview)
        if not a.preview:
            rendered.append(result)

    if not a.no_contact_sheet:
        print(f"Contact sheet: {contact_sheet(a.width,a.height)}")

    if not a.preview:
        print(f"Final video: {concatenate(rendered)}")


if __name__ == "__main__":
    main()
