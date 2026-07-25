#!/usr/bin/env python3
"""
LIFE CROSSES BARRIERS IT CANNOT CLIMB
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/01_life_crosses_barriers_it_cannot_climb.md

DESIGN CONTRACT
---------------
• Every shot lasts 5–10 seconds.
• Every shot visibly performs the narrated operation.
• White scientific field; concept-led color only.
• No static slide layouts and no decorative loops.
• Graphite = classical constraint
• Gold = quantum amplitude / latent possibility
• Cyan = molecular architecture / fields
• Crimson = failed path / suppressed possibility
• Green = viable biological flux
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: the gold probability filament survives across chapters.

OUTPUT
------
output_life_crosses/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  life_crosses_barriers.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.

USAGE
-----
python life_crosses_barriers_platinum.py
python life_crosses_barriers_platinum.py --preview
python life_crosses_barriers_platinum.py --scene 8
python life_crosses_barriers_platinum.py --fps 12 --width 1920 --height 1080
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


# =============================================================================
# CONFIGURATION
# =============================================================================

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_life_crosses"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 10

WHITE = (248, 247, 243)
PAPER = (242, 239, 232)
INK = (30, 32, 36)
SOFT_INK = (86, 89, 94)
SILVER = (180, 186, 192)
PALE_SILVER = (224, 227, 229)
GOLD = (191, 154, 73)
PALE_GOLD = (232, 216, 174)
CYAN = (67, 157, 180)
PALE_CYAN = (196, 226, 231)
CRIMSON = (158, 57, 66)
PALE_CRIMSON = (229, 193, 197)
GREEN = (72, 135, 101)
PALE_GREEN = (196, 222, 206)
LAPIS = (56, 76, 124)
VOID = (24, 27, 32)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# =============================================================================
# MATHEMATICS / DRAWING HELPERS
# =============================================================================

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
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


def pulse(t: float, hz: float = 1.0, phase: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin(math.tau * (hz * t + phase))


def load_font(path: str, size: int) -> ImageFont.ImageFont:
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rgba_layer(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def background(width: int, height: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.empty((height, width, 3), dtype=np.float32)
    arr[:] = WHITE
    arr += rng.normal(0, 1.15, (height, width, 1))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGB").convert("RGBA")

    edge = rgba_layer(im.size)
    d = ImageDraw.Draw(edge)
    for i in range(18):
        alpha = int(i * 0.8)
        inset = 18 + i * 3
        d.rounded_rectangle(
            (inset, inset, width - inset, height - inset),
            radius=18,
            outline=(*INK, alpha),
            width=2,
        )
    im.alpha_composite(edge)
    return im


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill=INK,
) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor="mm")


def seal(im: Image.Image, title: str, subtitle: str = "", color=INK) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    title_font = load_font(FONT_SERIF_BOLD, max(22, int(h * 0.042)))
    sub_font = load_font(FONT_SANS, max(13, int(h * 0.020)))
    centered_text(d, (w / 2, h * 0.875), title, title_font, color)
    if subtitle:
        centered_text(d, (w / 2, h * 0.925), subtitle, sub_font, SOFT_INK)


def border(im: Image.Image) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((25, 25, w - 25, h - 25), radius=17, outline=(*INK, 50), width=2)


def glow_line(
    im: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    width: int = 4,
    glow: int = 14,
    alpha: int = 225,
) -> None:
    if len(points) < 2:
        return
    layer = rgba_layer(im.size)
    d = ImageDraw.Draw(layer)
    d.line(points, fill=(*color, alpha), width=width, joint="curve")
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(glow)))
    im.alpha_composite(layer)


def glow_circle(
    im: Image.Image,
    cx: float,
    cy: float,
    radius: float,
    color: tuple[int, int, int],
    alpha: int = 180,
    blur: int = 18,
) -> None:
    layer = rgba_layer(im.size)
    d = ImageDraw.Draw(layer)
    d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(*color, alpha))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    core = rgba_layer(im.size)
    ImageDraw.Draw(core).ellipse(
        (cx-radius*0.45, cy-radius*0.45, cx+radius*0.45, cy+radius*0.45),
        fill=(*mix(color, WHITE, 0.30), min(255, alpha + 40)),
    )
    im.alpha_composite(core)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    color=INK,
    width: int = 3,
    head: int = 12,
) -> None:
    draw.line((*start, *end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    for delta in (2.55, -2.55):
        p = (
            end[0] + math.cos(angle + delta) * head,
            end[1] + math.sin(angle + delta) * head,
        )
        draw.line((*end, *p), fill=color, width=width)


def partial_polyline(points: list[tuple[float, float]], progress: float) -> list[tuple[float, float]]:
    progress = clamp(progress)
    if len(points) < 2:
        return points
    lengths = [math.dist(a, b) for a, b in zip(points[:-1], points[1:])]
    total = sum(lengths)
    target = total * progress
    output = [points[0]]
    walked = 0.0
    for i, length in enumerate(lengths):
        if walked + length <= target:
            output.append(points[i + 1])
            walked += length
        else:
            q = 0.0 if length == 0 else (target - walked) / length
            ax, ay = points[i]
            bx, by = points[i + 1]
            output.append((lerp(ax, bx, q), lerp(ay, by, q)))
            break
    return output


def wavefunction_points(
    x0: float,
    x1: float,
    baseline: float,
    amplitude: float,
    cycles: float,
    count: int = 180,
    decay_start: float | None = None,
    decay_rate: float = 5.0,
) -> list[tuple[float, float]]:
    pts = []
    for i in range(count):
        q = i / (count - 1)
        x = lerp(x0, x1, q)
        amp = amplitude
        if decay_start is not None and q > decay_start:
            amp *= math.exp(-decay_rate * (q - decay_start))
        y = baseline + math.sin(q * math.tau * cycles) * amp
        pts.append((x, y))
    return pts


# =============================================================================
# SCENE DATA
# =============================================================================

@dataclass
class Scene:
    title: str
    narration: str
    duration: float
    visual: str
    params: dict


# =============================================================================
# VISUAL MODES
# =============================================================================

def visual_classical_wall(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    cy = h * 0.45
    wall_x = w * 0.56
    wall_w = w * 0.12
    wall_top = h * 0.18
    wall_bottom = h * 0.69

    d.rounded_rectangle(
        (wall_x-wall_w/2, wall_top, wall_x+wall_w/2, wall_bottom),
        radius=12,
        fill=(*PALE_SILVER, 255),
        outline=(*INK, 180),
        width=4,
    )

    mode = p.get("mode", "stop")
    proton_x = lerp(w * 0.12, wall_x - 30, ease(min(1.0, u * 1.3)))
    proton_y = cy

    if mode == "climb":
        q = smoothstep(0.25, 0.90, u)
        proton_x = lerp(w * 0.15, wall_x + wall_w, q)
        proton_y = cy - math.sin(q * math.pi) * h * 0.31
        glow_circle(im, proton_x, proton_y, 15, GOLD, 190, 9)
        trajectory = []
        for i in range(80):
            xq = i / 79
            x = lerp(w*.15, wall_x+wall_w, xq)
            y = cy - math.sin(xq*math.pi)*h*.31
            trajectory.append((x, y))
        d.line(partial_polyline(trajectory, q), fill=(*SOFT_INK, 130), width=3)
        seal(im, "CLIMB", "enough energy to cross the classical barrier")
    else:
        glow_circle(im, proton_x, proton_y, 15, GOLD, 190, 9)
        impact = smoothstep(.65, .82, u)
        if impact:
            for i in range(5):
                a = -0.8 + i * 0.4
                d.line(
                    (proton_x, proton_y,
                     proton_x - math.cos(a)*35*impact,
                     proton_y + math.sin(a)*35*impact),
                    fill=(*CRIMSON, int(180*impact)),
                    width=2,
                )
        seal(im, "STOP", "without enough energy, classical motion ends here")


def visual_tunnelling(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    cy = h * 0.44
    left = w * 0.10
    right = w * 0.90
    bx0 = w * p.get("barrier_start", 0.46)
    bx1 = w * p.get("barrier_end", 0.62)

    d.rounded_rectangle(
        (bx0, h*.20, bx1, h*.68),
        radius=10,
        fill=(*PALE_SILVER, 245),
        outline=(*INK, 150),
        width=3,
    )

    # Wave oscillates before the barrier and decays inside it.
    amp = h * 0.085
    pts = []
    count = 240
    for i in range(count):
        q = i / (count - 1)
        x = lerp(left, right, q)
        if x < bx0:
            local_amp = amp
        elif x <= bx1:
            local_amp = amp * math.exp(-5.8 * (x - bx0) / max(1, bx1-bx0))
        else:
            residual = math.exp(-5.8)
            local_amp = amp * residual * 3.3
        y = cy + math.sin(q * math.tau * 8 - t*3.0) * local_amp
        pts.append((x, y))

    reveal = ease(u)
    glow_line(im, partial_polyline(pts, reveal), GOLD, width=4, glow=13, alpha=220)

    # Detection event on far side occurs late.
    detect = smoothstep(.66, .90, u)
    if detect > 0:
        px = lerp(bx1+25, w*.80, detect)
        glow_circle(im, px, cy, 14, GOLD, int(100+110*detect), 10)

    seal(im, "THE WAVE DOES NOT END AT THE WALL", "amplitude decays through the forbidden region")


def visual_exponential_width(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    cy = h * .44
    width_phase = ease(u)
    barrier_width = lerp(w*.08, w*.30, width_phase)
    x0 = w*.50 - barrier_width/2
    x1 = w*.50 + barrier_width/2

    d.rounded_rectangle((x0,h*.19,x1,h*.69), radius=10,
                        fill=(*PALE_SILVER,245), outline=(*INK,150), width=3)

    # Probability glow collapses exponentially as width grows.
    prob = math.exp(-5.4 * barrier_width / (w*.30))
    left_pts = wavefunction_points(w*.10, x0, cy, h*.075, 4.5)
    glow_line(im, left_pts, GOLD, 4, 12, 220)

    inside = []
    for i in range(90):
        q = i/89
        x = lerp(x0,x1,q)
        amp = h*.075*math.exp(-5*q)
        inside.append((x,cy+math.sin(q*math.tau*2-t*2)*amp))
    glow_line(im, inside, GOLD, 4, 12, 210)

    glow_circle(im, w*.78, cy, 8+30*prob, GOLD, int(55+180*prob), 15)
    label = f"relative probability  {prob:0.3f}"
    centered_text(d,(w*.50,h*.75),label,load_font(FONT_SANS_BOLD,int(h*.025)),SOFT_INK)
    seal(im, "A FRACTION OF AN ÅNGSTRÖM", "geometry changes the rate exponentially")


def visual_mass_comparison(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    rows = [
        ("electron", 1.00, GOLD),
        ("proton", 0.56, CYAN),
        ("deuterium", 0.27, CRIMSON),
        ("heavy atom", 0.06, SOFT_INK),
    ]
    bx0, bx1 = w*.48, w*.60
    for idx, (label, transmission, color) in enumerate(rows):
        y = h*(.23 + idx*.15)
        d.rounded_rectangle((bx0,y-34,bx1,y+34),radius=8,
                            fill=(*PALE_SILVER,235),outline=(*INK,110),width=2)
        centered_text(d,(w*.18,y),label.upper(),load_font(FONT_SANS_BOLD,int(h*.021)),color)
        progress = smoothstep(idx*.11, min(1, idx*.11+.58), u)
        pre = [(w*.28+i*3,y+math.sin(i*.46-t*3)*15) for i in range(int(62*progress)+1)]
        if len(pre)>1:
            d.line(pre,fill=(*color,190),width=3)
        far_alpha = int(225*transmission*progress)
        d.line((bx1+20,y,bx1+20+(w*.22*transmission*progress),y),
               fill=(*color,far_alpha),width=max(2,int(7*transmission)))
    seal(im, "MASS CHANGES THE CROSSING", "lighter particles retain more amplitude beyond the barrier")


def visual_energy_landscape(im: Image.Image, u: float, t: float, p: dict) -> None:
    w, h = im.size
    d = ImageDraw.Draw(im)
    mode = p.get("mode","solution")
    base_y = h*.66
    left = w*.12
    right = w*.88
    points = []
    for i in range(220):
        q=i/219
        x=lerp(left,right,q)
        if mode=="solution":
            peak=h*.34
        elif mode=="enzyme":
            peak=h*.19
        else:
            peak=h*.25
        y=base_y-peak*math.exp(-((q-.5)/.13)**2)
        points.append((x,y))
    d.line(points,fill=(*INK,180),width=4)

    # Molecular state rolls toward the barrier.
    q = ease(u)
    idx=min(len(points)-1,int(q*(len(points)-1)))
    px,py=points[idx]
    glow_circle(im,px,py-13,14,CYAN,180,9)

    if mode=="enzyme":
        for off in (-.10,.10):
            gx=w*(.5+off)
            d.arc((gx-80,h*.21,gx+80,h*.62),200,340,fill=(*GOLD,130),width=4)
        seal(im,"THE ENZYME RESHAPES THE LANDSCAPE","orientation, electrostatics, exclusion, proximity")
    else:
        seal(im,"REACTION IN SOLUTION","the uncatalysed route carries a higher energetic cost")


def visual_enzyme_pocket(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.44
    breathe=.5+.5*math.sin(t*1.2)
    closing=smoothstep(.15,.72,u)
    gap=lerp(235,78,closing)+breathe*12

    # Protein lobes
    left=[(cx-gap/2-185,cy-135),(cx-gap/2-55,cy-165),(cx-gap/2,cy-70),
          (cx-gap/2-30,cy+50),(cx-gap/2-170,cy+145)]
    right=[(2*cx-x,y) for x,y in left]
    d.polygon(left,fill=(*PALE_CYAN,230),outline=(*CYAN,210))
    d.polygon(right,fill=(*PALE_CYAN,230),outline=(*CYAN,210))

    donor=(cx-gap/2,cy)
    acceptor=(cx+gap/2,cy)
    glow_circle(im,*donor,17,GOLD,190,9)
    glow_circle(im,*acceptor,17,GREEN,170,9)

    # Gold wave overlaps only once gap narrows.
    overlap=smoothstep(150,75,gap)
    if gap < 170:
        pts=[]
        for i in range(110):
            q=i/109
            x=lerp(donor[0],acceptor[0],q)
            amp=18*math.sin(math.pi*q)
            y=cy+math.sin(q*math.tau*4-t*4)*amp
            pts.append((x,y))
        glow_line(im,pts,GOLD,4,12,int(130+100*overlap))

    seal(im,"THE PROTEIN BREATHES THE BARRIER THIN","motion prepares; quantum probability completes")


def visual_isotope(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    bx0,bx1=w*.47,w*.59
    d.rounded_rectangle((bx0,h*.18,bx1,h*.69),radius=10,
                        fill=(*PALE_SILVER,245),outline=(*INK,140),width=3)
    rows=[("H",GOLD,.82,h*.34),("D",CRIMSON,.30,h*.55)]
    for label,color,trans,y in rows:
        centered_text(d,(w*.18,y),label,load_font(FONT_SERIF_BOLD,int(h*.065)),color)
        progress=ease(u)
        wave=wavefunction_points(w*.25,bx0,y,24,3.4,count=90)
        glow_line(im,partial_polyline(wave,progress),color,4,11,210)
        far_len=w*.23*trans*progress
        d.line((bx1+18,y,bx1+18+far_len,y),fill=(*color,210),width=6)
        centered_text(d,(w*.84,y),f"{trans:0.2f}",load_font(FONT_SANS_BOLD,int(h*.030)),color)
    seal(im,"KINETIC ISOTOPE EFFECT","heavier deuterium crosses less readily than hydrogen")


def visual_evidence_caution(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    center=(w*.50,h*.43)
    terms=[
        ("MASS",(-220,-95),GOLD),
        ("DISTANCE",(220,-95),CYAN),
        ("ELECTROSTATICS",(-230,105),LAPIS),
        ("PROTEIN MOTION",(230,105),GREEN),
        ("BARRIER SHAPE",(0,180),CRIMSON),
    ]
    reveal=u*len(terms)
    for i,(name,(ox,oy),color) in enumerate(terms):
        q=clamp(reveal-i)
        x=center[0]+ox*ease_out(q)
        y=center[1]+oy*ease_out(q)
        d.line((*center,x,y),fill=(*color,int(150*q)),width=3)
        d.rounded_rectangle((x-85,y-21,x+85,y+21),radius=14,
                            fill=(*mix(WHITE,color,.12),int(235*q)),
                            outline=(*color,int(190*q)),width=2)
        centered_text(d,(x,y),name,load_font(FONT_SANS_BOLD,int(h*.017)),color)
    glow_circle(im,*center,18,GOLD,170,12)
    seal(im,"AN ISOTOPE EFFECT OPENS A CASE","it does not close the mechanism automatically")


def visual_evolution(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    generations=7
    y=h*.45
    for i in range(generations):
        q=clamp(u*generations-i)
        x=lerp(w*.12,w*.88,i/(generations-1))
        improvement=i/(generations-1)
        gap=lerp(120,52,improvement)
        d.arc((x-38,y-85,x+38,y+5),190,350,fill=(*CYAN,int(200*q)),width=6)
        d.arc((x-38,y-5,x+38,y+85),10,170,fill=(*CYAN,int(200*q)),width=6)
        d.line((x-gap/2,y,x+gap/2,y),fill=(*GOLD,int(220*q)),width=max(2,int(2+4*improvement)))
        if i<generations-1:
            arrow(d,(x+48,y+120),(lerp(w*.12,w*.88,(i+1)/(generations-1))-48,y+120),
                  SOFT_INK,2,8)
    seal(im,"SELECTION OPERATES ON OUTCOMES","evolution need not understand the wavefunction")


def visual_triangle_doublewell(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    mode=p.get("mode","triangle")
    if mode=="triangle":
        q=ease(u)
        a=(w*.50,h*.20)
        b=(w*.25,h*.68)
        c=(w*.75,h*.68)
        edges=[(a,b),(b,c),(c,a)]
        for i,(s,e) in enumerate(edges):
            local=clamp(q*3-i)
            end=(lerp(s[0],e[0],local),lerp(s[1],e[1],local))
            d.line((*s,*end),fill=(*INK,220),width=5)
        if q>.72:
            for pt in (a,b,c):
                glow_circle(im,*pt,10,GOLD,170,8)
        seal(im,"BUILD A TRIANGLE","relations arrive with the arrangement")
    else:
        pts=[]
        for i in range(220):
            q=i/219
            x=lerp(w*.14,w*.86,q)
            v=((q-.25)*(q-.75))**2
            y=h*.60-v*h*4.8
            pts.append((x,y))
        d.line(pts,fill=(*INK,210),width=4)
        left=(w*.32,h*.49)
        right=(w*.68,h*.49)
        glow_circle(im,*left,15,CYAN,160,10)
        transfer=smoothstep(.42,.88,u)
        filament=[(left[0],left[1]),(w*.50,h*.31),(right[0],right[1])]
        glow_line(im,partial_polyline(filament,transfer),GOLD,4,13,220)
        if transfer>.85:
            glow_circle(im,*right,15,GREEN,180,10)
        seal(im,"BUILD A DOUBLE WELL","tunnelling enters the reaction landscape")


def visual_structure_rates(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    rows=8
    reveal=u*rows
    for i in range(rows):
        q=clamp(reveal-i)
        y=h*(.20+i*.075)
        width=lerp(w*.05,w*.43,math.exp(-i*.48))*q
        d.line((w*.30,y,w*.30+width,y),fill=(*mix(CRIMSON,GREEN,i/(rows-1)),210),width=7)
        centered_text(d,(w*.20,y),f"{0.1+i*0.1:0.1f} Å",load_font(FONT_SANS_BOLD,int(h*.019)),SOFT_INK)
    seal(im,"STRUCTURE SELECTS POSSIBILITY","small geometric changes separate reaction from silence")


def visual_proton_gate(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    mode=p.get("mode","water")
    y=h*.45
    left=w*.12
    right=w*.88

    # Membrane
    for row_y in (h*.24,h*.66):
        for i in range(22):
            x=lerp(left,right,i/21)
            d.ellipse((x-10,row_y-10,x+10,row_y+10),fill=(*PALE_CYAN,245),outline=(*CYAN,160))

    if mode=="water":
        nodes=[]
        for i in range(10):
            x=lerp(w*.22,w*.78,i/9)
            yy=y+math.sin(i*.9)*32
            nodes.append((x,yy))
            d.ellipse((x-13,yy-13,x+13,yy+13),fill=(*WHITE,255),outline=(*LAPIS,180),width=3)
        q=ease(u)
        for i in range(len(nodes)-1):
            if q>(i/(len(nodes)-1)):
                d.line((*nodes[i],*nodes[i+1]),fill=(*GOLD,160),width=3)
        idx=min(len(nodes)-1,int(q*(len(nodes)-1)))
        glow_circle(im,*nodes[idx],13,GOLD,190,9)
        seal(im,"PROTON RELAY","bonding patterns reorganize through a water chain")
    else:
        # Gate chooses one route from several.
        routes=[]
        for k,offset in enumerate((-115,-55,0,55,115)):
            routes.append([(w*.18,y),(w*.45,y+offset),(w*.82,y+offset*.45)])
        chosen=2
        reveal=ease(u)
        for k,path in enumerate(routes):
            color=GREEN if k==chosen else PALE_CRIMSON
            alpha=220 if k==chosen else int(115*(1-reveal*.65))
            d.line(partial_polyline(path,reveal),fill=(*color,alpha),width=5 if k==chosen else 3)
        seal(im,"THE GATE SUPPRESSES MOST POSSIBILITIES","constraint converts uncertainty into directed flow")


def visual_noise_control(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    rng=random.Random(44)
    count=120
    organize=smoothstep(.25,.85,u)
    for i in range(count):
        x=rng.uniform(w*.10,w*.90)
        y=rng.uniform(h*.18,h*.69)
        target_y=h*.44+math.sin((x/w)*math.tau*3)*34
        yy=lerp(y,target_y,organize)
        col=CYAN if i%5 else GOLD
        r=2+(i%3)
        d.ellipse((x-r,yy-r,x+r,yy+r),fill=(*col,140))
    if organize>.35:
        path=[(w*.12+i*w*.76/120,h*.44+math.sin(i/120*math.tau*3)*34) for i in range(121)]
        glow_line(im,partial_polyline(path,organize),GOLD,4,12,190)
    seal(im,"CONTROL WITHOUT PURITY","life builds noisy structures where specific quantum facts remain consequential")


def visual_architecture_truth(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    examples=[
        ("BIRD","spin chemistry",w*.20),
        ("CELL","voltage",w*.40),
        ("EMBRYO","geometry",w*.60),
        ("ENZYME","tunnelling",w*.80),
    ]
    reveal=u*len(examples)
    for i,(subject,law,x) in enumerate(examples):
        q=clamp(reveal-i)
        radius=52*ease_out(q)
        d.ellipse((x-radius,h*.42-radius,x+radius,h*.42+radius),
                  fill=(*mix(WHITE,CYAN,.14),int(235*q)),outline=(*CYAN,int(190*q)),width=3)
        if q>.45:
            centered_text(d,(x,h*.42),subject,load_font(FONT_SANS_BOLD,int(h*.020)),INK)
            centered_text(d,(x,h*.60),law,load_font(FONT_SERIF,int(h*.023)),GOLD)
    seal(im,"THE BODY ACTS THROUGH TRUTHS IT CANNOT STATE","competence can precede conceptual knowledge")


def visual_metaphor_warning(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    left=(w*.25,h*.44)
    right=(w*.75,h*.44)
    # Exact physical mechanism
    d.rounded_rectangle((left[0]-150,left[1]-110,left[0]+150,left[1]+110),radius=22,
                        fill=(*mix(WHITE,CYAN,.10),245),outline=(*CYAN,180),width=3)
    centered_text(d,(left[0],left[1]-35),"MASS · WIDTH · COUPLING",
                  load_font(FONT_SANS_BOLD,int(h*.021)),CYAN)
    centered_text(d,(left[0],left[1]+25),"MEASURABLE RATE EFFECT",
                  load_font(FONT_SANS_BOLD,int(h*.021)),GREEN)

    # Metaphorical overreach fragments.
    words=["THOUGHT TUNNELS","QUANTUM INTENTION","SPIRITUAL JUMP"]
    fade=smoothstep(.35,.85,u)
    for i,word in enumerate(words):
        yy=right[1]-70+i*70
        centered_text(d,(right[0],yy),word,load_font(FONT_SERIF_BOLD,int(h*.024)),
                      (*CRIMSON,int(190*(1-fade))))
        d.line((right[0]-135,yy,right[0]+135,yy),fill=(*CRIMSON,int(220*fade)),width=4)
    seal(im,"DO NOT TURN MECHANISM INTO MAGIC","let exact science discipline the metaphor")


def visual_psychological_geometry(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    mode=p.get("mode","force")
    cx,cy=w*.55,h*.45
    wall_x=w*.58
    d.rounded_rectangle((wall_x-55,h*.18,wall_x+55,h*.68),radius=12,
                        fill=(*PALE_SILVER,245),outline=(*INK,150),width=3)

    if mode=="force":
        progress=ease(u)
        person_x=lerp(w*.18,wall_x-85,progress)
        d.ellipse((person_x-18,cy-95,person_x+18,cy-59),outline=(*INK,220),width=4)
        d.line((person_x,cy-59,person_x,cy+25),fill=(*INK,220),width=4)
        d.line((person_x,cy-20,person_x+55,cy-10),fill=(*INK,220),width=4)
        d.line((person_x,cy+25,person_x-28,cy+82),fill=(*INK,220),width=4)
        d.line((person_x,cy+25,person_x+35,cy+82),fill=(*INK,220),width=4)
        for i in range(5):
            arrow(d,(person_x-55-i*24,cy),(person_x-25-i*24,cy),CRIMSON,3,8)
        seal(im,"MORE FORCE · SAME GEOMETRY","pressure repeats the classical route")
    else:
        # Supports reshape the route around the barrier.
        q=ease(u)
        path=[
            (w*.16,cy+80),
            (w*.36,cy+20),
            (wall_x-90,h*.20),
            (wall_x+95,h*.20),
            (w*.85,cy-10),
        ]
        glow_line(im,partial_polyline(path,q),CYAN,6,13,220)
        for x,y,label in [
            (w*.30,cy+35,"support"),
            (w*.48,h*.23,"regulation"),
            (w*.73,h*.23,"new evidence"),
        ]:
            if q>.35:
                d.ellipse((x-8,y-8,x+8,y+8),fill=(*GOLD,220))
                centered_text(d,(x,y-30),label,load_font(FONT_SANS_BOLD,int(h*.017)),SOFT_INK)
        seal(im,"CHANGE THE GEOMETRY","transformation looks sudden because preparation was hidden")


def visual_final_synthesis(im: Image.Image, u: float, t: float, p: dict) -> None:
    w,h=im.size
    d=ImageDraw.Draw(im)
    cy=h*.43
    bx0,bx1=w*.45,w*.58
    d.rounded_rectangle((bx0,h*.18,bx1,h*.68),radius=10,
                        fill=(*PALE_SILVER,240),outline=(*INK,140),width=3)

    # Enzyme chamber forms around the wall.
    chamber=smoothstep(.05,.55,u)
    d.arc((bx0-180,h*.12,bx1+180,h*.72),190,350,
          fill=(*CYAN,int(210*chamber)),width=7)
    d.arc((bx0-180,h*.12,bx1+180,h*.72),10,170,
          fill=(*CYAN,int(210*chamber)),width=7)

    # Persistent gold filament crosses once architecture is ready.
    cross=smoothstep(.40,.93,u)
    pts=[]
    for i in range(180):
        q=i/179
        x=lerp(w*.12,w*.88,q)
        if bx0<=x<=bx1:
            amp=24*math.exp(-5*(x-bx0)/(bx1-bx0))
        else:
            amp=24 if x<bx0 else 4
        y=cy+math.sin(q*math.tau*7-t*2.5)*amp
        pts.append((x,y))
    glow_line(im,partial_polyline(pts,cross),GOLD,5,15,230)
    if cross>.86:
        glow_circle(im,w*.82,cy,18,GREEN,190,12)

    seal(im,"LIFE CROSSES BARRIERS IT CANNOT CLIMB",
         "not through violation—through architecture aligned with possibility",GREEN)


VISUALS: dict[str, Callable[[Image.Image, float, float, dict], None]] = {
    "classical_wall": visual_classical_wall,
    "tunnelling": visual_tunnelling,
    "width": visual_exponential_width,
    "mass": visual_mass_comparison,
    "landscape": visual_energy_landscape,
    "enzyme": visual_enzyme_pocket,
    "isotope": visual_isotope,
    "evidence": visual_evidence_caution,
    "evolution": visual_evolution,
    "form": visual_triangle_doublewell,
    "rates": visual_structure_rates,
    "gate": visual_proton_gate,
    "noise": visual_noise_control,
    "architecture": visual_architecture_truth,
    "warning": visual_metaphor_warning,
    "psychology": visual_psychological_geometry,
    "final": visual_final_synthesis,
}


# =============================================================================
# FULL ADAPTED ESSAY / TIMED SHOT LIST
# =============================================================================

SCENES: list[Scene] = [
    Scene(
        "A proton reaches a wall",
        "A proton reaches a wall. Classical physics gives it two options.",
        6.0, "classical_wall", {"mode":"stop"},
    ),
    Scene(
        "Climb",
        "Bring enough energy to climb over.",
        5.5, "classical_wall", {"mode":"climb"},
    ),
    Scene(
        "Stop",
        "Or remain where it is.",
        5.5, "classical_wall", {"mode":"stop"},
    ),
    Scene(
        "Third option",
        "Inside enzymes, a third option matters. The proton can appear on the other side.",
        7.5, "tunnelling", {},
    ),
    Scene(
        "No crack",
        "Not because the wall opens. Not because the particle secretly found a crack.",
        6.5, "tunnelling", {"barrier_start":.45,"barrier_end":.61},
    ),
    Scene(
        "Wave penetrates",
        "Its quantum wave extends through the barrier, giving the transfer a probability even when the classical route is energetically forbidden.",
        9.0, "tunnelling", {},
    ),
    Scene(
        "No violation",
        "Life does not violate physics. It uses the version of physics in which a barrier is not always an absolute border.",
        8.0, "final", {},
    ),

    Scene(
        "Wavefunction",
        "A quantum particle is described by a wavefunction: a distribution of amplitudes over possible outcomes.",
        7.5, "tunnelling", {"barrier_start":.49,"barrier_end":.58},
    ),
    Scene(
        "Decay",
        "At a finite barrier, the wavefunction does not stop sharply. It decays through the forbidden region.",
        7.5, "tunnelling", {"barrier_start":.43,"barrier_end":.64},
    ),
    Scene(
        "Detection",
        "If enough amplitude reaches the far side, a measurement can find the particle there.",
        7.0, "tunnelling", {"barrier_start":.48,"barrier_end":.58},
    ),
    Scene(
        "Width",
        "The probability falls exponentially with barrier width.",
        7.0, "width", {},
    ),
    Scene(
        "Mass",
        "It also falls with particle mass. Electrons tunnel readily; protons can tunnel biologically; heavier atoms do so far less easily.",
        9.0, "mass", {},
    ),
    Scene(
        "Geometry becomes destiny",
        "At this scale, a difference of fractions of an ångström can transform the rate. Geometry becomes destiny.",
        8.0, "width", {},
    ),

    Scene(
        "Catalysis before enzyme",
        "Enzymes are molecular catalysts. A reaction in solution may face a steep and badly arranged energy landscape.",
        8.0, "landscape", {"mode":"solution"},
    ),
    Scene(
        "Catalysis inside enzyme",
        "An enzyme orients substrates, reorganizes electrostatics, positions water, and stabilizes favorable configurations.",
        9.0, "landscape", {"mode":"enzyme"},
    ),
    Scene(
        "No quantum magic",
        "Tunnelling is not a universal explanation for catalytic power. The enzyme does not replace chemistry with quantum magic.",
        8.0, "warning", {},
    ),
    Scene(
        "Prepared situation",
        "It prepares a molecular situation in which an unavoidable quantum process becomes useful.",
        7.5, "enzyme", {},
    ),

    Scene(
        "Hydrogen transfer",
        "Hydrogen-transfer enzymes offer the clearest cases because hydrogen is light and its quantum position is comparatively spread out.",
        8.5, "mass", {},
    ),
    Scene(
        "Replace H with D",
        "Replace ordinary hydrogen with deuterium. The heavier isotope tunnels less readily.",
        7.5, "isotope", {},
    ),
    Scene(
        "Open a case",
        "A large isotope effect can support tunnelling, but mass is not the only variable.",
        7.0, "evidence", {},
    ),
    Scene(
        "Mechanism remains plural",
        "Protein motion, barrier shape, electrostatics, and coupled coordinates also influence the result. The experiment opens a case. It does not close it automatically.",
        9.5, "evidence", {},
    ),

    Scene(
        "Donor and acceptor apart",
        "In soybean lipoxygenase, donor and acceptor begin too far apart for efficient hydrogen transfer.",
        7.0, "enzyme", {},
    ),
    Scene(
        "Protein samples geometry",
        "Protein motion samples configurations. For brief moments, the distance narrows.",
        7.0, "enzyme", {},
    ),
    Scene(
        "Breathing barrier",
        "The enzyme does not push the particle continuously across. It breathes the barrier into a form through which tunnelling becomes likely.",
        9.0, "enzyme", {},
    ),
    Scene(
        "Motion and probability",
        "Motion prepares. Quantum probability completes.",
        6.0, "enzyme", {},
    ),

    Scene(
        "Evolution selects geometry",
        "Evolution does not need to understand wavefunctions. It only needs to preserve molecular arrangements that produce better outcomes.",
        8.5, "evolution", {},
    ),
    Scene(
        "The molecule inherits mathematics",
        "Quantum effects can become biologically functional without being represented by the organism. Selection operates on outcomes. The molecule inherits the mathematics.",
        9.5, "evolution", {},
    ),

    Scene(
        "Triangle",
        "Build a triangle and geometric relations arrive with the arrangement.",
        6.5, "form", {"mode":"triangle"},
    ),
    Scene(
        "Double well",
        "Build a double-well molecular potential at the right scale and tunnelling enters the reaction landscape.",
        8.0, "form", {"mode":"doublewell"},
    ),
    Scene(
        "Reliable flux",
        "Build an enzyme that repeatedly narrows donor and acceptor distance, and a small probability becomes a reliable biological flux.",
        9.0, "enzyme", {},
    ),
    Scene(
        "Pointer into possibility",
        "The organism does not create the quantum law. It creates a pointer into the region where the law becomes useful.",
        8.0, "form", {"mode":"doublewell"},
    ),
    Scene(
        "Structure selects",
        "Structure does not merely decorate matter. Structure selects which physical possibilities become real often enough to matter.",
        9.0, "rates", {},
    ),

    Scene(
        "Water relay",
        "In respiratory enzymes, proton transfer may use hydrogen-bonded water chains. Bonding patterns reorganize in a relay.",
        8.5, "gate", {"mode":"water"},
    ),
    Scene(
        "Electric gate",
        "Electric fields, protonation states, and conformational switches lower one route while suppressing others.",
        8.5, "gate", {"mode":"routes"},
    ),
    Scene(
        "Constraint gives direction",
        "The proton reaches the correct destination not because every possibility remains open, but because architecture makes one event repeatable and most alternatives irrelevant.",
        9.5, "gate", {"mode":"routes"},
    ),
    Scene(
        "Life sculpts barriers",
        "Life does not defeat barriers. It sculpts them.",
        6.0, "gate", {"mode":"routes"},
    ),

    Scene(
        "Warm, wet, noisy",
        "Living systems do not preserve a laboratory-perfect quantum world inside the cell.",
        7.0, "noise", {},
    ),
    Scene(
        "Noise samples geometry",
        "Protein fluctuations can sample useful geometries. Dissipation can prevent a system from remaining trapped.",
        8.0, "noise", {},
    ),
    Scene(
        "Control without purity",
        "Life builds noisy structures in which specific quantum facts remain consequential. The miracle is control without purity.",
        9.0, "noise", {},
    ),

    Scene(
        "No concept required",
        "A proton does not know the destination. An enzyme does not know quantum mechanics. Evolution does not calculate tunnelling integrals.",
        9.0, "architecture", {},
    ),
    Scene(
        "Architecture knows",
        "Knowledge is not required at every level for a structure to exploit a law.",
        7.0, "architecture", {},
    ),
    Scene(
        "Truths the body cannot state",
        "A bird need not understand spin chemistry. A cell need not understand voltage. An embryo need not understand geometry. The body acts through truths it cannot state.",
        9.5, "architecture", {},
    ),

    Scene(
        "Do not overreach",
        "Tunnelling in enzymes does not prove that thought tunnels, intention controls particles, or spiritual realization is a quantum jump.",
        9.0, "warning", {},
    ),
    Scene(
        "Exact mechanism",
        "It is a specific physical mechanism defined by masses, barriers, coupling, geometry, and measurable rate effects.",
        8.0, "warning", {},
    ),
    Scene(
        "Disciplined metaphor",
        "The responsible philosophical movement goes in the other direction: let the exact mechanism transform the metaphor.",
        8.0, "warning", {},
    ),

    Scene(
        "Same wall, more force",
        "A person can spend years trying to climb a psychological wall through greater force: more pressure, more command, more repetition of the same approach.",
        9.5, "psychology", {"mode":"force"},
    ),
    Scene(
        "Change geometry",
        "Sometimes change happens only when the geometry changes.",
        6.5, "psychology", {"mode":"geometry"},
    ),
    Scene(
        "Preparation",
        "Support narrows the distance to safety. Regulation permits new evidence. Practice changes the shape of attention.",
        9.0, "psychology", {"mode":"geometry"},
    ),
    Scene(
        "Sudden from one level",
        "Transformation looks sudden because preparation happened in dimensions the conscious story did not track.",
        8.5, "psychology", {"mode":"geometry"},
    ),

    Scene(
        "Return to wall",
        "A proton reaches a wall. Classical intuition says it must climb or stop.",
        7.0, "classical_wall", {"mode":"stop"},
    ),
    Scene(
        "Quantum layer",
        "Quantum mechanics says the wall has thickness, the particle has a wavefunction, and probability penetrates where a point-object could not.",
        9.0, "tunnelling", {},
    ),
    Scene(
        "Biological layer",
        "Biology adds another layer: the enzyme evolves a chamber in which the forbidden crossing becomes ordinary enough to sustain life.",
        9.5, "final", {},
    ),
    Scene(
        "Closing",
        "Life crosses barriers it cannot climb. Not through will. Not through violation. Through architecture aligned with a deeper possibility already present in nature.",
        10.0, "final", {},
    ),
    Scene(
        "Thin wall",
        "The particle does not conquer the wall. The living system learns how thin the wall must become.",
        8.0, "final", {},
    ),
]


# =============================================================================
# RENDER PIPELINE
# =============================================================================

def render_frame(scene: Scene, frame_index: int, frame_count: int,
                 width: int, height: int, seed: int) -> Image.Image:
    u = frame_index / max(1, frame_count - 1)
    t = u * scene.duration
    im = background(width, height, seed)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")


def require_ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("ffmpeg is required but was not found on PATH")
    return executable


def encode_scene(scene_index: int, fps: int) -> Path:
    ffmpeg = require_ffmpeg()
    frame_dir = FRAMES / f"scene_{scene_index:03d}"
    output_path = SCENES_DIR / f"scene_{scene_index:03d}.mp4"
    command = [
        ffmpeg, "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "%05d.jpg"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def render_scene(scene_index: int, scene: Scene, fps: int,
                 width: int, height: int, preview: bool) -> Path:
    frame_dir = FRAMES / f"scene_{scene_index:03d}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    frame_count = max(2, round(scene.duration * fps))
    if preview:
        samples = [0, int(frame_count*.35), int(frame_count*.72), frame_count-1]
        for out_idx, frame_idx in enumerate(samples):
            image = render_frame(scene, frame_idx, frame_count, width, height, scene_index*1000+frame_idx)
            image.save(frame_dir / f"preview_{out_idx:02d}.jpg", quality=95)
        return frame_dir

    for frame_idx in range(frame_count):
        path = frame_dir / f"{frame_idx:05d}.jpg"
        if path.exists():
            continue
        image = render_frame(scene, frame_idx, frame_count, width, height, scene_index*1000+frame_idx)
        image.save(path, quality=95, subsampling=0)

    return encode_scene(scene_index, fps)


def concatenate(scene_paths: list[Path]) -> Path:
    ffmpeg = require_ffmpeg()
    concat_file = OUTPUT / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.resolve()}'" for path in scene_paths),
        encoding="utf-8",
    )
    output_path = OUTPUT / "life_crosses_barriers.mp4"
    command = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def export_timeline() -> Path:
    cursor = 0.0
    payload = []
    for index, scene in enumerate(SCENES, start=1):
        record = asdict(scene)
        record["scene_id"] = f"scene_{index:03d}"
        record["start_seconds"] = round(cursor, 3)
        record["end_seconds"] = round(cursor + scene.duration, 3)
        payload.append(record)
        cursor += scene.duration

    path = OUTPUT / "narration_timeline.json"
    path.write_text(json.dumps({
        "title": "life crosses barriers it cannot climb",
        "runtime_seconds": round(cursor, 3),
        "scene_count": len(SCENES),
        "style": {
            "background": "clean white scientific field",
            "continuity_object": "gold probability filament",
            "shot_duration_range_seconds": [5, 10],
            "palette_roles": {
                "graphite": "classical constraint",
                "gold": "quantum amplitude",
                "cyan": "molecular architecture",
                "crimson": "suppressed or failed path",
                "green": "viable biological flux",
            },
        },
        "scenes": payload,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def make_contact_sheet(width: int, height: int) -> Path:
    thumbs = []
    thumb_w = 320
    thumb_h = int(thumb_w * height / width)
    for index, scene in enumerate(SCENES, start=1):
        frame_count = max(2, round(scene.duration * DEFAULT_FPS))
        im = render_frame(scene, int(frame_count*.72), frame_count, width, height, index*1000+72)
        im.thumbnail((thumb_w, thumb_h))
        thumbs.append((index, scene.title, im.copy()))

    columns = 4
    rows = math.ceil(len(thumbs)/columns)
    cell_h = thumb_h + 52
    sheet = Image.new("RGB", (columns*thumb_w, rows*cell_h), WHITE)
    d = ImageDraw.Draw(sheet)
    label_font = load_font(FONT_SANS_BOLD, 15)

    for idx, title, im in thumbs:
        slot = idx-1
        x = (slot%columns)*thumb_w
        y = (slot//columns)*cell_h
        sheet.paste(im, (x,y))
        d.text((x+10,y+thumb_h+8), f"{idx:02d}  {title}", font=label_font, fill=INK)

    path = OUTPUT / "contact_sheet.jpg"
    sheet.save(path, quality=94)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--scene", type=int, default=None,
                        help="Render one 1-indexed scene only.")
    parser.add_argument("--preview", action="store_true",
                        help="Render four representative stills per scene, not MP4.")
    parser.add_argument("--no-contact-sheet", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    timeline = export_timeline()
    print(f"Timeline: {timeline}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")

    if args.scene is not None:
        if not 1 <= args.scene <= len(SCENES):
            raise ValueError(f"--scene must be between 1 and {len(SCENES)}")
        scene = SCENES[args.scene-1]
        result = render_scene(args.scene, scene, args.fps, args.width, args.height, args.preview)
        print(result)
        return

    rendered = []
    for index, scene in enumerate(SCENES, start=1):
        print(f"[{index:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        result = render_scene(index, scene, args.fps, args.width, args.height, args.preview)
        if not args.preview:
            rendered.append(result)

    if not args.no_contact_sheet:
        sheet = make_contact_sheet(args.width, args.height)
        print(f"Contact sheet: {sheet}")

    if not args.preview:
        final = concatenate(rendered)
        print(f"Final video: {final}")


if __name__ == "__main__":
    main()
