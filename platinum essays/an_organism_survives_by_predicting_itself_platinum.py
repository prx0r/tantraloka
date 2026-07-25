#!/usr/bin/env python3
"""
AN ORGANISM SURVIVES BY PREDICTING ITSELF
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/02_an_organism_survives_by_predicting_itself.md

DESIGN CONTRACT
---------------
• Every shot lasts 5–10 seconds.
• Every shot visibly performs the narrated operation.
• Clean white biological systems field; deep field only where concept requires it.
• No static slide layouts and no decorative loops.
• Cyan = predictive silhouette / expected future state
• Gold = prediction error / evidence / useful surprise
• Green = viable regulation / successful correction
• Crimson = rigid prior / threat weighting / avoidance policy
• Violet = memory / learned expectation / psychological model
• Graphite = physical constraint / practical boundary
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: a cyan future-outline remains slightly ahead of the living body.
• Visual world: anticipatory shadows, homeostatic bands, reach trajectories,
  morphogenetic target fields, error vectors, precision weights, curiosity probes.
• No generic mandalas. Geometry must emerge from control, regulation, or anatomy.

OUTPUT
------
output_predicting_itself/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  an_organism_survives_by_predicting_itself.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.

USAGE
-----
python an_organism_survives_by_predicting_itself_platinum.py
python an_organism_survives_by_predicting_itself_platinum.py --preview
python an_organism_survives_by_predicting_itself_platinum.py --scene 8
python an_organism_survives_by_predicting_itself_platinum.py --fps 12 --width 1920 --height 1080
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
OUTPUT = ROOT / "output_predicting_itself"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 10

WHITE = (248, 247, 243)
PAPER = (242, 239, 232)
INK = (28, 31, 35)
SOFT_INK = (84, 88, 94)
SILVER = (177, 184, 190)
PALE_SILVER = (224, 227, 229)
CYAN = (56, 153, 181)
PALE_CYAN = (192, 226, 233)
GOLD = (194, 153, 69)
PALE_GOLD = (235, 218, 175)
GREEN = (70, 139, 98)
PALE_GREEN = (194, 225, 206)
CRIMSON = (158, 52, 66)
PALE_CRIMSON = (230, 192, 198)
VIOLET = (104, 79, 146)
PALE_VIOLET = (216, 205, 232)
LAPIS = (48, 72, 124)
VOID = (22, 25, 31)

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
    return a + (b - a) * t


def mix(a, b, t):
    t = clamp(t)
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))


def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a))
    return q * q * (3 - 2*q)


def ease(t: float) -> float:
    t = clamp(t)
    return .5 - .5 * math.cos(math.pi*t)


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1 - (1-t)**3


def pulse(t: float, hz: float = 1.0, phase: float = 0.0) -> float:
    return .5 + .5*math.sin(math.tau*(hz*t+phase))


def load_font(path: str, size: int):
    for candidate in (path, FONT_SERIF, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def rgba_layer(size):
    return Image.new("RGBA", size, (0,0,0,0))


def background(width, height, seed, dark=False):
    rng=np.random.default_rng(seed)
    base=VOID if dark else WHITE
    arr=np.empty((height,width,3),dtype=np.float32)
    arr[:]=base
    arr += rng.normal(0,1.1 if not dark else 1.7,(height,width,1))
    arr=np.clip(arr,0,255).astype(np.uint8)
    return Image.fromarray(arr,"RGB").convert("RGBA")


def centered_text(draw, xy, text, font, fill=INK):
    draw.text(xy,text,font=font,fill=fill,anchor="mm")


def seal(im,title,subtitle="",color=INK):
    w,h=im.size
    d=ImageDraw.Draw(im)
    title_font=load_font(FONT_SERIF_BOLD,max(22,int(h*.042)))
    sub_font=load_font(FONT_SANS,max(13,int(h*.020)))
    centered_text(d,(w/2,h*.875),title,title_font,color)
    if subtitle:
        centered_text(d,(w/2,h*.925),subtitle,sub_font,SOFT_INK)


def border(im):
    w,h=im.size
    ImageDraw.Draw(im).rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*INK,46),width=2)


def glow_line(im,points,color,width=4,glow=14,alpha=225):
    if len(points)<2:return
    layer=rgba_layer(im.size)
    d=ImageDraw.Draw(layer)
    d.line(points,fill=(*color,alpha),width=width,joint="curve")
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(glow)))
    im.alpha_composite(layer)


def glow_circle(im,cx,cy,radius,color,alpha=180,blur=18):
    layer=rgba_layer(im.size)
    d=ImageDraw.Draw(layer)
    d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=(*color,alpha))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    core=rgba_layer(im.size)
    ImageDraw.Draw(core).ellipse(
        (cx-radius*.42,cy-radius*.42,cx+radius*.42,cy+radius*.42),
        fill=(*mix(color,WHITE,.28),min(255,alpha+40))
    )
    im.alpha_composite(core)


def partial_polyline(points,progress):
    progress=clamp(progress)
    if len(points)<2:return points
    lengths=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]
    total=sum(lengths)
    target=total*progress
    output=[points[0]]
    walked=0.0
    for i,length in enumerate(lengths):
        if walked+length<=target:
            output.append(points[i+1]); walked+=length
        else:
            q=0 if length==0 else (target-walked)/length
            ax,ay=points[i]; bx,by=points[i+1]
            output.append((lerp(ax,bx,q),lerp(ay,by,q)))
            break
    return output


def arrow(draw,start,end,color=INK,width=3,head=12):
    draw.line((*start,*end),fill=color,width=width)
    a=math.atan2(end[1]-start[1],end[0]-start[0])
    for delta in (2.55,-2.55):
        p=(end[0]+math.cos(a+delta)*head,end[1]+math.sin(a+delta)*head)
        draw.line((*end,*p),fill=color,width=width)


def organic_blob(draw,cx,cy,rx,ry,color,phase=0,points=100,outline=None):
    pts=[]
    for i in range(points):
        a=math.tau*i/points
        wob=1+.06*math.sin(a*3+phase)+.035*math.sin(a*7-phase*.5)
        pts.append((cx+math.cos(a)*rx*wob,cy+math.sin(a)*ry*wob))
    draw.polygon(pts,fill=color,outline=outline)
    return pts


def body_silhouette(draw,cx,cy,scale,color,alpha=220,width=4,dash=False):
    head=28*scale
    draw.ellipse((cx-head,cy-120*scale-head,cx+head,cy-120*scale+head),
                 outline=(*color,alpha),width=width)
    segments=[
        ((cx,cy-92*scale),(cx,cy+20*scale)),
        ((cx,cy-55*scale),(cx-58*scale,cy-5*scale)),
        ((cx,cy-55*scale),(cx+58*scale,cy-5*scale)),
        ((cx,cy+20*scale),(cx-42*scale,cy+105*scale)),
        ((cx,cy+20*scale),(cx+42*scale,cy+105*scale)),
    ]
    for s,e in segments:
        if dash:
            for i in range(0,12,2):
                q0=i/12;q1=min(1,(i+1)/12)
                draw.line((lerp(s[0],e[0],q0),lerp(s[1],e[1],q0),
                           lerp(s[0],e[0],q1),lerp(s[1],e[1],q1)),
                          fill=(*color,alpha),width=width)
        else:
            draw.line((*s,*e),fill=(*color,alpha),width=width)


def prediction_shadow(draw,cx,cy,scale=1.0,offset=70,alpha=180):
    body_silhouette(draw,cx+offset,cy,scale,CYAN,alpha,3,True)


# =============================================================================
# SCENES
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

def visual_mismatch_field(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.35,h*.46
    prediction_shadow(d,cx,cy,1.0,95,170)
    body_silhouette(d,cx,cy,1.0,INK,220,5)
    shifts=[("temperature",CYAN,-110,-110),("chemistry",VIOLET,160,-90),
            ("footfall",GOLD,-95,120),("expression",CRIMSON,165,105)]
    for i,(label,col,ox,oy) in enumerate(shifts):
        q=smoothstep(i*.10,.68+i*.05,u)
        x=cx+ox; y=cy+oy
        glow_circle(im,x,y,12+13*q,col,int(80+100*q),10)
        arrow(d,(x,y),(cx+40,cy),(*col,int(170*q)),2,8)
        if q>.72:centered_text(d,(x,y-30),label,load_font(FONT_SANS_BOLD,int(h*.015)),col)
    seal(im,"LIFE CONTINUES BY CORRECTING SURPRISE","the organism adjusts before the person notices")


def visual_model_compare(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=w*.20; right=w*.80; cy=h*.42
    prediction_shadow(d,left,cy,.85,85,160)
    body_silhouette(d,left,cy,.85,INK,220,4)
    # world signals
    for i in range(10):
        y=h*(.20+i*.05)
        x=lerp(right,left+95,ease(u))
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*GOLD,180))
    # comparison chamber
    chamber=(w*.50,cy)
    d.rounded_rectangle((chamber[0]-90,cy-80,chamber[0]+90,cy+80),
                        radius=20,fill=(*PALE_CYAN,220),outline=(*CYAN,180),width=3)
    centered_text(d,chamber,"COMPARE",load_font(FONT_SANS_BOLD,int(h*.020)),CYAN)
    err=smoothstep(.42,.88,u)
    glow_circle(im,chamber[0],chamber[1],18+25*err,GOLD,int(100+110*err),14)
    seal(im,"PERCEPTION CHANGES THE GUESS · ACTION CHANGES THE EVIDENCE","model and world correct one another")


def visual_reaching_glass(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    shoulder=(w*.18,h*.50); glass=(w*.78,h*.43)
    # arm forecast
    pred=[]
    actual=[]
    for i in range(120):
        q=i/119
        px=lerp(shoulder[0],glass[0],q)
        py=shoulder[1]-math.sin(q*math.pi)*110
        pred.append((px,py))
        ay=py+math.sin(q*math.tau*2+t*.8)*10*(1-q)
        actual.append((px,ay))
    d.line(partial_polyline(pred,ease(u)),fill=(*CYAN,150),width=5)
    glow_line(im,partial_polyline(actual,ease(u)),GOLD,5,12,220)
    # correction vectors
    for i in range(20,110,18):
        q=smoothstep(i/130,(i+25)/130,u)
        if q:
            arrow(d,pred[i],actual[i],(*CRIMSON,int(130*q)),2,7)
    d.rounded_rectangle((glass[0]-34,glass[1]-65,glass[0]+34,glass[1]+65),
                        radius=10,outline=(*INK,190),width=4)
    fill=smoothstep(.72,.96,u)
    d.rectangle((glass[0]-28,glass[1]+10,glass[0]+28,glass[1]+58),
                fill=(*PALE_CYAN,int(190*fill)))
    seal(im,"AGENCY IS SMOOTH ERROR MANAGEMENT","clumsiness is when correction becomes visible")


def visual_free_energy_landscape(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=[]
    for i in range(240):
        q=i/239
        x=lerp(w*.10,w*.90,q)
        y=h*.66 - h*.25*(math.exp(-((q-.28)/.13)**2)+.75*math.exp(-((q-.72)/.16)**2))
        pts.append((x,y))
    d.line(pts,fill=(*INK,190),width=4)
    q=ease(u)
    idx=min(len(pts)-1,int(q*(len(pts)-1)))
    x,y=pts[idx]
    glow_circle(im,x,y-12,14,GOLD,190,10)
    # information-seeking branch
    branch=smoothstep(.42,.92,u)
    probe=[(x,y-12),(w*.52,h*.28),(w*.70,h*.36)]
    glow_line(im,partial_polyline(probe,branch),CYAN,4,12,190)
    seal(im,"NOT BLAND PREDICTABILITY","viable engagement may include seeking uncertainty")


def visual_homeostatic_band(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    variables=[("temperature",CYAN,.25),("oxygen",GREEN,.38),("hydration",LAPIS,.51),
               ("glucose",GOLD,.64)]
    for i,(name,col,yf) in enumerate(variables):
        y=h*yf
        d.rounded_rectangle((w*.18,y-17,w*.82,y+17),radius=16,
                            fill=(*PALE_SILVER,190),outline=(*SILVER,130),width=2)
        d.rounded_rectangle((w*.40,y-13,w*.60,y+13),radius=12,
                            fill=(*mix(WHITE,col,.18),210),outline=(*col,160),width=2)
        q=(u+i*.18)%1
        x=w*.18+q*w*.64
        correction=0
        if x<w*.40: correction=1
        elif x>w*.60: correction=-1
        d.ellipse((x-8,y-8,x+8,y+8),fill=(*col,210))
        if correction:
            arrow(d,(x,y),(x+correction*55,y),(*GOLD,190),3,9)
        centered_text(d,(w*.12,y),name.upper(),load_font(FONT_SANS_BOLD,int(h*.014)),col)
    seal(im,"THE BODY PREDICTS ITSELF","organization rebuilds evidence that it is still itself")


def visual_implicit_model(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    modes=[("ROOT",GREEN),("BACTERIUM",CYAN),("IMMUNE",VIOLET)]
    for i,(label,col) in enumerate(modes):
        x=w*(.22+i*.28); q=smoothstep(i*.12,.62+i*.06,u)
        if i==0:
            d.line((x,h*.28,x,h*.55),fill=(*col,int(210*q)),width=7)
            for j in range(7):
                a=math.pi*.15+j*.42
                d.line((x,h*.48,x+math.cos(a)*70*q,h*.48+math.sin(a)*90*q),
                       fill=(*col,int(170*q)),width=3)
            glow_circle(im,x+45,h*.60,12,GOLD,int(120*q),9)
        elif i==1:
            organic_blob(d,x,h*.43,55*q,35*q,(*PALE_CYAN,int(220*q)),phase=t*.4,outline=(*col,int(180*q)))
            d.line((x-55*q,h*.43,x-95*q,h*.43+math.sin(t)*18),fill=(*col,int(180*q)),width=3)
        else:
            for j in range(9):
                a=j*math.tau/9+t*.15
                xx=x+math.cos(a)*48*q; yy=h*.43+math.sin(a)*48*q
                d.ellipse((xx-8,yy-8,xx+8,yy+8),fill=(*mix(WHITE,col,.22),int(210*q)),outline=(*col,int(160*q)))
        if q>.7:centered_text(d,(x,h*.66),label,load_font(FONT_SANS_BOLD,int(h*.016)),col)
    seal(im,"A MODEL CAN BE IMPLICIT IN STRUCTURE","inference need not contain a little scientist")


def visual_morphogenesis_target(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.43
    # target morphology cyan
    target=[]
    for i in range(120):
        a=i*math.tau/120
        r=120*(1+.20*math.sin(3*a))
        target.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.72))
    d.line(target+[target[0]],fill=(*CYAN,150),width=4)
    rng=random.Random(81)
    cells=[]
    repair=smoothstep(.18,.92,u)
    for i in range(90):
        a=rng.random()*math.tau; rr=rng.random()*160
        sx=cx+math.cos(a)*rr; sy=cy+math.sin(a)*rr*.72
        ta=i*math.tau/90
        tr=120*(1+.20*math.sin(3*ta))
        tx=cx+math.cos(ta)*tr; ty=cy+math.sin(ta)*tr*.72
        x=lerp(sx,tx,repair); y=lerp(sy,ty,repair)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(CRIMSON,GREEN,repair),170))
    if repair>.65:
        glow_line(im,target+[target[0]],GREEN,4,11,170)
    seal(im,"ANATOMICAL ERROR BECOMES ACTION","growth and remodeling move tissue toward a target form")


def visual_model_limits(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.42
    # one formula net trying to cover diverse phenomena
    nodes=[("BRAIN",CYAN,(-220,-100)),("CELL",GREEN,(210,-90)),
           ("EMBRYO",GOLD,(-205,120)),("SOCIETY",VIOLET,(220,115))]
    for i,(name,col,(ox,oy)) in enumerate(nodes):
        q=smoothstep(i*.10,.62+i*.06,u)
        x=cx+ox; y=cy+oy
        d.rounded_rectangle((x-72*q,y-28*q,x+72*q,y+28*q),radius=16,
                            fill=(*mix(WHITE,col,.13),int(220*q)),
                            outline=(*col,int(180*q)),width=2)
        if q>.6:centered_text(d,(x,y),name,load_font(FONT_SANS_BOLD,int(h*.015)),col)
        d.line((cx,cy,x,y),fill=(*SILVER,int(120*q)),width=2)
    d.ellipse((cx-75,cy-45,cx+75,cy+45),fill=(*PALE_SILVER,220),outline=(*INK,170),width=3)
    centered_text(d,(cx,cy),"MODEL",load_font(FONT_SANS_BOLD,int(h*.021)),INK)
    # red caution boundary appears
    q=smoothstep(.55,.92,u)
    d.arc((cx-110,cy-78,cx+110,cy+78),205,335,fill=(*CRIMSON,int(190*q)),width=5)
    seal(im,"BREADTH IS POWER · BREADTH IS DANGER","a theory of everything must show unique predictions")


def visual_precision_weights(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    center=(w*.50,h*.42)
    signals=[("faint threat",CRIMSON,w*.18,h*.26),("background hum",SILVER,w*.18,h*.58),
             ("prior belief",VIOLET,w*.82,h*.28),("new evidence",GOLD,w*.82,h*.57)]
    for i,(label,col,x,y) in enumerate(signals):
        weight=.15+.85*abs(math.sin(t*.35+i))
        width=max(2,int(2+10*weight))
        d.line((x,y,*center),fill=(*col,int(80+150*weight)),width=width)
        d.ellipse((x-12,y-12,x+12,y+12),fill=(*mix(WHITE,col,.22),220),outline=(*col,180),width=2)
        centered_text(d,(x,y-30),label,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    glow_circle(im,*center,22,GREEN,150,13)
    seal(im,"PRECISION IS CALIBRATED TRUST","which error deserves to change the organism?")


def visual_model_habitat(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.43
    # expectation builds habitat walls
    q=ease(u)
    for i in range(7):
        inset=55+i*28
        col=mix(PALE_VIOLET,CRIMSON,i/7)
        alpha=int(70+100*q)
        d.rounded_rectangle((cx-inset,cy-inset*.62,cx+inset,cy+inset*.62),
                            radius=22,outline=(*col,alpha),width=3)
    body_silhouette(d,cx,cy,.8,INK,220,4)
    prediction_shadow(d,cx,cy,.8,0,110)
    words=[("EXPECTATION",VIOLET,-170,-95),("ATTENTION",GOLD,170,-95),
           ("ACTION",CRIMSON,-170,105),("EVIDENCE",GREEN,170,105)]
    for name,col,ox,oy in words:
        d.line((cx,cy,cx+ox,cy+oy),fill=(*col,140),width=3)
        centered_text(d,(cx+ox,cy+oy),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    seal(im,"A MODEL BECOMES A HABITAT","the world increasingly confirms the prediction")


def visual_avoidance_prison(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.35,h*.44
    body_silhouette(d,cx,cy,.9,INK,220,4)
    prediction_shadow(d,cx,cy,.9,85,160)
    # feared zone
    zone=(w*.75,h*.43)
    d.ellipse((zone[0]-80,zone[1]-80,zone[0]+80,zone[1]+80),
              fill=(*PALE_CRIMSON,190),outline=(*CRIMSON,190),width=3)
    # avoidance wall grows
    wall=smoothstep(.25,.85,u)
    x=lerp(w*.58,w*.53,wall)
    d.rounded_rectangle((x-14,h*.18,x+14,h*.69),radius=8,
                        fill=(*INK,int(220*wall)))
    # short-term relief loop
    arrow(d,(cx+50,cy-55),(cx+5,cy-100),GREEN,3,10)
    arrow(d,(cx+5,cy-100),(cx-40,cy-55),GREEN,3,10)
    # future corridor narrows
    for i in range(7):
        yy=h*(.22+i*.07)
        d.line((x+20,yy,w*.92,lerp(h*.32,h*.54,i/6)),fill=(*CRIMSON,int(130*wall)),width=2)
    seal(im,"THE MODEL REMAINS SAFE BECAUSE IT REMAINS UNTESTED","short-term predictability buys a smaller future")


def visual_curiosity_probe(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    child=(w*.25,h*.48); object_c=(w*.72,h*.43)
    body_silhouette(d,*child,.72,INK,210,4)
    organic_blob(d,*object_c,68,68,(*PALE_CYAN,220),phase=t*.3,outline=(*CYAN,180))
    # multiple exploratory policies
    routes=[
        [(child[0]+40,child[1]-20),(w*.48,h*.26),object_c],
        [(child[0]+40,child[1]),(w*.50,h*.43),object_c],
        [(child[0]+40,child[1]+25),(w*.49,h*.62),object_c],
    ]
    cols=[GOLD,CYAN,VIOLET]
    for i,path in enumerate(routes):
        glow_line(im,partial_polyline(path,smoothstep(i*.12,.75+i*.05,u)),cols[i],4,11,180)
    # information pulses return
    ret=smoothstep(.55,.95,u)
    for i in range(8):
        q=(ret+i/8)%1
        x=lerp(object_c[0],child[0]+35,q); y=lerp(object_c[1],child[1]-40,q)+math.sin(q*math.pi)*30
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*GOLD,180))
    seal(im,"THE WORLD BECOMES A QUESTION THE BODY ASKS PHYSICALLY","knowledge is produced through controlled disturbance")


def visual_agency_scale(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    items=[("THERMOSTAT",SILVER,.14),("CELL",CYAN,.34),("ANIMAL",GREEN,.56),("HUMAN",VIOLET,.78)]
    for i,(name,col,xf) in enumerate(items):
        q=smoothstep(i*.12,.60+i*.07,u)
        x=w*xf
        r=28+18*i
        d.ellipse((x-r*q,h*.43-r*q,x+r*q,h*.43+r*q),
                  fill=(*mix(WHITE,col,.16),int(220*q)),outline=(*col,int(180*q)),width=3)
        branches=1+i*2
        for j in range(branches):
            a=-math.pi/2+j*math.pi/max(1,branches-1)
            d.line((x,h*.43,x+math.cos(a)*r*1.5*q,h*.43+math.sin(a)*r*1.5*q),
                   fill=(*col,int(150*q)),width=2)
        if q>.7:centered_text(d,(x,h*.66),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    seal(im,"AGENCY MAY BE GRADED","difference lies in the size and flexibility of the problem space")


def visual_metaphysical_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.28,h*.43); right=(w*.72,h*.43)
    d.rounded_rectangle((left[0]-150,left[1]-105,left[0]+150,left[1]+105),
                        radius=20,fill=(*PALE_CYAN,220),outline=(*CYAN,180),width=3)
    centered_text(d,(left[0],left[1]-28),"FUNCTIONAL",load_font(FONT_SANS_BOLD,int(h*.022)),CYAN)
    centered_text(d,(left[0],left[1]+24),"PREDICTION",load_font(FONT_SANS_BOLD,int(h*.022)),CYAN)
    d.rounded_rectangle((right[0]-150,right[1]-105,right[0]+150,right[1]+105),
                        radius=20,fill=(*PALE_VIOLET,180),outline=(*VIOLET,180),width=3)
    centered_text(d,(right[0],right[1]-28),"INNER",load_font(FONT_SANS_BOLD,int(h*.022)),VIOLET)
    centered_text(d,(right[0],right[1]+24),"EXPERIENCE",load_font(FONT_SANS_BOLD,int(h*.022)),VIOLET)
    q=smoothstep(.30,.88,u)
    d.line((w*.49,h*.32,w*.51,h*.54),fill=(*CRIMSON,int(210*q)),width=7)
    d.line((w*.49,h*.54,w*.51,h*.32),fill=(*CRIMSON,int(210*q)),width=7)
    seal(im,"MATHEMATICAL SIMILARITY DOES NOT PROVE IDENTICAL EXPERIENCE","competence, consciousness, life, and selfhood remain distinct")


def visual_future_bets(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.30,h*.46
    body_silhouette(d,cx,cy,.9,INK,220,4)
    prediction_shadow(d,cx,cy,.9,100,160)
    bets=[("gravity",CYAN,w*.68,h*.24),("air",GREEN,w*.80,h*.38),
          ("safety",GOLD,w*.68,h*.56),("recovery",VIOLET,w*.82,h*.66)]
    for i,(name,col,x,y) in enumerate(bets):
        q=smoothstep(i*.10,.65+i*.06,u)
        arrow(d,(cx+35,cy),(x,y),(*col,int(180*q)),3,10)
        d.ellipse((x-10,y-10,x+10,y+10),fill=(*col,int(190*q)))
        if q>.72:centered_text(d,(x,y-28),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    seal(im,"THE BODY IS ALREADY BETTING ON A FUTURE","some predictions are ancient; others can be revised")


def visual_tolerable_mismatch(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.43
    # concentric tolerance bands
    bands=[(175,PALE_CRIMSON,"CHAOS"),(115,PALE_GOLD,"LEARNING"),(55,PALE_GREEN,"NO CHANGE")]
    for r,col,label in bands:
        d.ellipse((cx-r,cy-r*.62,cx+r,cy+r*.62),fill=(*col,90),outline=(*mix(col,INK,.25),130),width=2)
    prediction_shadow(d,cx-90,cy,.75,90,150)
    body_silhouette(d,cx-90,cy,.75,INK,220,4)
    q=ease(u)
    errx=lerp(cx-20,cx+145,q)
    erry=cy+math.sin(q*math.pi)*45
    glow_circle(im,errx,erry,13,GOLD,190,10)
    if q>.15: arrow(d,(cx-20,cy),(errx,erry),GOLD,3,9)
    centered_text(d,(cx,cy-92),"USEFUL SURPRISE",load_font(FONT_SANS_BOLD,int(h*.016)),GOLD)
    seal(im,"REALITY MUST VIOLATE EXPECTATION IN A FORM THE ORGANISM CAN METABOLIZE","too little changes nothing; too much becomes chaos")


def visual_final_balance(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.45,h*.45
    # body and prediction converge but never fully overlap
    q=ease(u)
    offset=lerp(115,38,q)
    prediction_shadow(d,cx,cy,.95,offset,180)
    body_silhouette(d,cx,cy,.95,INK,230,5)
    # gold errors entering
    for i in range(18):
        a=i*math.tau/18+t*.08
        rr=lerp(220,70,q)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.65
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*GOLD,170))
    # green path forward
    path=[(cx+45,cy+40),(w*.62,h*.43),(w*.78,h*.34),(w*.90,h*.42)]
    glow_line(im,partial_polyline(path,smoothstep(.35,.95,u)),GREEN,6,14,220)
    seal(im,"AN ORGANISM SURVIVES BY PREDICTING ITSELF","confident enough to move · uncertain enough to change",GREEN)


VISUALS: dict[str, Callable] = {
    "mismatch": visual_mismatch_field,
    "compare": visual_model_compare,
    "reach": visual_reaching_glass,
    "landscape": visual_free_energy_landscape,
    "homeostasis": visual_homeostatic_band,
    "implicit": visual_implicit_model,
    "morphogenesis": visual_morphogenesis_target,
    "limits": visual_model_limits,
    "precision": visual_precision_weights,
    "habitat": visual_model_habitat,
    "avoidance": visual_avoidance_prison,
    "curiosity": visual_curiosity_probe,
    "agency": visual_agency_scale,
    "caution": visual_metaphysical_caution,
    "bets": visual_future_bets,
    "mismatch_learning": visual_tolerable_mismatch,
    "final": visual_final_balance,
}


# =============================================================================
# FULL ADAPTED ESSAY / TIMED SHOT LIST
# =============================================================================

SCENES: list[Scene] = [
    Scene("Constant mismatch","Your body is constantly failing to encounter the world exactly as expected.",7.0,"mismatch",{}),
    Scene("Temperature","Temperature shifts.",5.0,"mismatch",{}),
    Scene("Chemistry","Blood chemistry changes.",5.0,"mismatch",{}),
    Scene("Footfall","A foot lands slightly differently than predicted.",6.0,"mismatch",{}),
    Scene("Expression","A face produces an expression you did not anticipate.",6.0,"mismatch",{}),
    Scene("Before consciousness","Most mismatches never become conscious. The organism adjusts before the person notices.",8.5,"mismatch",{}),
    Scene("Correcting surprise","Life continues by correcting surprise.",6.0,"final",{}),

    Scene("Not passive reception","Perception is not passive reception.",6.0,"compare",{}),
    Scene("Generative model","The organism carries expectations about hidden causes, bodily states, sensory inputs, and consequences of action.",9.5,"compare",{}),
    Scene("Prediction error","Incoming signals are compared with predictions. Mismatch produces prediction error.",8.0,"compare",{}),
    Scene("Update model","The system can update its model to fit the world.",6.5,"compare",{}),
    Scene("Act on world","Or it can act so that sensations fit the prediction.",7.0,"compare",{}),
    Scene("Guess and evidence","Perception changes the guess. Action changes the evidence.",7.5,"compare",{}),

    Scene("Reach for glass","Imagine reaching for a glass.",5.5,"reach",{}),
    Scene("Predicted consequences","The nervous system predicts joint angles, muscle tension, visual position, and contact.",9.0,"reach",{}),
    Scene("Signals return","Signals return. Differences are corrected.",6.5,"reach",{}),
    Scene("Precision","The hand arrives with remarkable precision despite delay, noise, and variation.",8.0,"reach",{}),
    Scene("Fluency","Successful movement feels immediate because prediction and correction disappear into fluency.",8.5,"reach",{}),
    Scene("Agency","Agency is smooth error management. Clumsiness makes the management visible.",8.0,"reach",{}),

    Scene("Formal language","Active inference uses the formal language of variational free energy.",7.5,"landscape",{}),
    Scene("Not everyday energy","This is not free energy in the everyday sense.",6.0,"landscape",{}),
    Scene("Not emotional surprise","Surprise is a technical quantity, not merely astonishment.",6.5,"landscape",{}),
    Scene("Not hating novelty","An agent may seek novelty when uncertainty reduction is useful.",7.5,"landscape",{}),
    Scene("Viable uncertainty","The point is viable engagement with an uncertain world.",7.0,"landscape",{}),

    Scene("Narrow states","A living organism occupies a narrow range of viable states.",7.0,"homeostasis",{}),
    Scene("Variables","Temperature, oxygen, hydration, glucose, and integrity cannot wander indefinitely.",9.0,"homeostasis",{}),
    Scene("Circularity","The organism survives because it visits unsurprising states, and those states are unsurprising because surviving organisms revisit them.",10.0,"homeostasis",{}),
    Scene("Embodied constraints","A lasting system embodies constraints reflecting the kind of system it is.",8.0,"homeostasis",{}),
    Scene("Predicts itself","The body predicts itself by rebuilding evidence that it is still itself.",8.5,"homeostasis",{}),

    Scene("No little scientist","A cell does not contain a little internal scientist.",6.5,"implicit",{}),
    Scene("Implicit model","A model can be implicit in structure and dynamics.",7.0,"implicit",{}),
    Scene("Root","A plant root grows toward water without representing water in language.",7.5,"implicit",{}),
    Scene("Bacterium","A bacterium changes movement in response to chemical gradients.",7.0,"implicit",{}),
    Scene("Immune system","An immune system distinguishes self and threat through distributed molecular interactions.",8.5,"implicit",{}),
    Scene("Functional relation","Inference names a functional relation between hidden conditions, partial signals, and action.",9.0,"implicit",{}),

    Scene("Beyond brains","The framework becomes controversial when extended beyond nervous systems.",7.5,"morphogenesis",{}),
    Scene("Cellular collective","Cells receive chemical, mechanical, and bioelectric signals.",7.5,"morphogenesis",{}),
    Scene("Target morphology","They migrate, differentiate, divide, communicate, and reach a target morphology.",9.0,"morphogenesis",{}),
    Scene("Persistent error","An anatomical defect becomes persistent prediction error.",7.0,"morphogenesis",{}),
    Scene("Growth as action","Growth and remodeling become action.",6.5,"morphogenesis",{}),

    Scene("Not final proof","This is not yet a universally accepted description of development.",7.5,"limits",{}),
    Scene("Implementation question","A formal model does not prove that cells implement every quantity exactly as brains might.",9.0,"limits",{}),
    Scene("What counts as model","Researchers debate what counts as a generative model and where variables are physically realized.",9.0,"limits",{}),
    Scene("Breadth","The framework is powerful because it connects many domains.",7.0,"limits",{}),
    Scene("Danger","That breadth is also its danger.",6.0,"limits",{}),
    Scene("Unique prediction","A theory describing almost everything must show what it uniquely predicts.",8.0,"limits",{}),

    Scene("Experimental contact","Experimental contact matters.",6.0,"morphogenesis",{}),
    Scene("Embryonic tests","Models of embryonic development have generated simulations and testable perturbations.",8.5,"morphogenesis",{}),
    Scene("Research border","The border between cognition and development becomes a research question.",8.0,"morphogenesis",{}),

    Scene("Precision","Not every prediction error receives equal weight.",7.0,"precision",{}),
    Scene("Reliability","The system estimates which signals are reliable.",7.0,"precision",{}),
    Scene("Threat weighting","A faint sound in darkness may gain authority if danger is expected.",8.0,"precision",{}),
    Scene("Ignore hum","A familiar background hum may be ignored.",6.5,"precision",{}),
    Scene("Rigid prior","Too much confidence in prior expectation can ignore correction.",7.5,"precision",{}),
    Scene("Noisy evidence","Too much confidence in noisy signals can destabilize the model.",7.5,"precision",{}),
    Scene("Calibrated trust","Healthy inference depends on calibrated trust.",7.0,"precision",{}),
    Scene("Which error","The organism must decide which error deserves to change it.",8.0,"precision",{}),

    Scene("Psychological force","This gives the framework psychological force.",6.5,"habitat",{}),
    Scene("Threat expectations","Anxiety may interpret ambiguity through strong expectations of threat.",8.0,"habitat",{}),
    Scene("Failure predictions","Depression may carry rigid predictions of failure and reduced control.",8.5,"habitat",{}),
    Scene("No total explanation","No equation should erase biography, society, trauma, or meaning.",8.0,"limits",{}),
    Scene("Prediction loop","Expectation shapes attention. Attention selects evidence. Action changes the environment.",9.0,"habitat",{}),
    Scene("Expected result","The environment returns the expected result.",6.5,"habitat",{}),
    Scene("Model habitat","A model becomes a habitat.",6.0,"habitat",{}),

    Scene("Not destiny","Prediction is not destiny.",6.0,"avoidance",{}),
    Scene("Learning","Models can update when error becomes strong, repeated, and trusted.",8.5,"mismatch_learning",{}),
    Scene("New action","New action samples evidence unavailable inside the old routine.",8.0,"curiosity",{}),
    Scene("Avoidance relief","Avoidance reduces immediate distress by preventing feared contact.",8.0,"avoidance",{}),
    Scene("No disconfirmation","It also prevents disconfirmation.",6.5,"avoidance",{}),
    Scene("Safe because untested","The model remains safe because it remains untested.",7.0,"avoidance",{}),
    Scene("Smaller future","Short-term predictability can purchase a smaller future.",7.5,"avoidance",{}),
    Scene("Policy prison","The prison is maintained by policy, not belief alone.",7.5,"avoidance",{}),

    Scene("Curiosity","Curiosity is a strategy for improving prediction.",7.0,"curiosity",{}),
    Scene("Seek information","The agent seeks information because unresolved uncertainty matters.",7.5,"curiosity",{}),
    Scene("Child experiment","A child shakes, drops, opens, and watches.",7.5,"curiosity",{}),
    Scene("Question body asks","The world becomes a question the body asks physically.",8.0,"curiosity",{}),
    Scene("Controlled disturbance","Knowledge is produced through controlled disturbance.",7.5,"curiosity",{}),

    Scene("Not just reaction","Living systems are not simply reacting to external forces.",7.5,"agency",{}),
    Scene("Sample and test","They sample conditions, test expectations, and modify themselves.",8.0,"agency",{}),
    Scene("Graded agency","Agency becomes graded.",6.0,"agency",{}),
    Scene("Thermostat","A thermostat regulates one variable through a simple loop.",7.0,"agency",{}),
    Scene("Cell","A cell integrates many signals and changes state.",6.5,"agency",{}),
    Scene("Animal","An animal pursues absent goals across time.",6.5,"agency",{}),
    Scene("Human","A human can revise the values defining preferable futures.",7.5,"agency",{}),
    Scene("Problem space","Difference may lie in the size and flexibility of the problem space.",8.0,"agency",{}),

    Scene("Dangerous leap","A dangerous metaphysical leap often follows.",6.5,"caution",{}),
    Scene("Universe predicts","Mathematical similarity across scales does not establish a conscious predicting universe.",9.0,"caution",{}),
    Scene("No feeling guaranteed","A system can minimize a quantity without feeling surprise.",7.5,"caution",{}),
    Scene("Functional preferences","It can have functional preferences without human desire.",7.0,"caution",{}),
    Scene("Separate questions","Competence, consciousness, life, and selfhood remain separate questions.",8.5,"caution",{}),

    Scene("Prepared world","You are not confronting a raw world with no preparation.",7.0,"bets",{}),
    Scene("Expectation in perception","Every perception arrives through expectation.",6.5,"bets",{}),
    Scene("Assumptions in action","Every action expresses assumptions about what can happen and what is worth preserving.",9.0,"bets",{}),
    Scene("Future bet","The body is already betting on a future.",7.0,"bets",{}),
    Scene("Ancient bets","Gravity will continue. Air will enter. This body should remain within bounds.",8.5,"bets",{}),
    Scene("Learned bets","Other predictions are learned and revisable.",6.5,"bets",{}),
    Scene("Protection","The nervous system may protect old predictions because predictability once mattered more than freedom.",9.0,"bets",{}),

    Scene("More than sentence","Change requires more than replacing a sentence.",6.5,"mismatch_learning",{}),
    Scene("New evidence","The system needs new evidence.",6.0,"mismatch_learning",{}),
    Scene("Different action","A different action.",5.0,"mismatch_learning",{}),
    Scene("Tolerable mismatch","A tolerable mismatch.",5.5,"mismatch_learning",{}),
    Scene("Enough safety","Enough safety to update without being overwhelmed.",7.5,"mismatch_learning",{}),
    Scene("Metabolizable violation","Learning occurs when reality violates expectation in a form the organism can metabolize.",9.5,"mismatch_learning",{}),
    Scene("Too little","Too little error changes nothing.",6.0,"mismatch_learning",{}),
    Scene("Too much","Too much becomes chaos.",6.0,"mismatch_learning",{}),
    Scene("Useful surprise","Useful surprise enters at the edge of what the model can survive.",8.5,"mismatch_learning",{}),

    Scene("Failure is opening","Failure to meet expectation is not a flaw.",6.5,"final",{}),
    Scene("Learning enters","It is the opening through which learning enters.",6.5,"final",{}),
    Scene("Prediction coordinates","Prediction allows coordinated action.",6.5,"final",{}),
    Scene("Error prevents hallucination","Error prevents prediction from becoming hallucination.",7.5,"final",{}),
    Scene("Between two","Life persists between the two.",6.0,"final",{}),
    Scene("Confident uncertain","Confident enough to move. Uncertain enough to change.",7.0,"final",{}),
    Scene("Predicting itself","An organism survives by predicting itself.",7.0,"final",{}),
    Scene("Beyond current model","It becomes more than its current model by discovering where prediction was wrong.",9.0,"final",{}),
    Scene("Expect again","The future becomes possible when the body learns to expect again.",9.0,"final",{}),
]


# =============================================================================
# RENDER PIPELINE
# =============================================================================

def render_frame(scene, frame_index, frame_count, width, height, seed):
    u=frame_index/max(1,frame_count-1)
    t=u*scene.duration
    im=background(width,height,seed,False)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im)
    return im.convert("RGB")


def require_ffmpeg():
    exe=shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg is required but was not found on PATH")
    return exe


def encode_scene(scene_index,fps):
    ffmpeg=require_ffmpeg()
    frame_dir=FRAMES/f"scene_{scene_index:03d}"
    output_path=SCENES_DIR/f"scene_{scene_index:03d}.mp4"
    cmd=[ffmpeg,"-y","-framerate",str(fps),"-i",str(frame_dir/"%05d.jpg"),
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(output_path)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output_path


def render_scene(scene_index,scene,fps,width,height,preview):
    frame_dir=FRAMES/f"scene_{scene_index:03d}"
    frame_dir.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    frame_count=max(2,round(scene.duration*fps))
    if preview:
        samples=[0,int(frame_count*.35),int(frame_count*.72),frame_count-1]
        for out_idx,frame_idx in enumerate(samples):
            im=render_frame(scene,frame_idx,frame_count,width,height,scene_index*1000+frame_idx)
            im.save(frame_dir/f"preview_{out_idx:02d}.jpg",quality=95)
        return frame_dir
    for frame_idx in range(frame_count):
        path=frame_dir/f"{frame_idx:05d}.jpg"
        if path.exists():continue
        im=render_frame(scene,frame_idx,frame_count,width,height,scene_index*1000+frame_idx)
        im.save(path,quality=95,subsampling=0)
    return encode_scene(scene_index,fps)


def concatenate(scene_paths):
    ffmpeg=require_ffmpeg()
    concat_file=OUTPUT/"concat.txt"
    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_paths),encoding="utf-8")
    output_path=OUTPUT/"an_organism_survives_by_predicting_itself.mp4"
    cmd=[ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat_file),
         "-c","copy","-movflags","+faststart",str(output_path)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output_path


def export_timeline():
    cursor=0.0
    payload=[]
    for index,scene in enumerate(SCENES,start=1):
        rec=asdict(scene)
        rec["scene_id"]=f"scene_{index:03d}"
        rec["start_seconds"]=round(cursor,3)
        rec["end_seconds"]=round(cursor+scene.duration,3)
        payload.append(rec)
        cursor+=scene.duration
    path=OUTPUT/"narration_timeline.json"
    path.write_text(json.dumps({
        "title":"an organism survives by predicting itself",
        "runtime_seconds":round(cursor,3),
        "scene_count":len(SCENES),
        "style":{
            "background":"clean white biological systems field",
            "continuity_object":"cyan predictive silhouette",
            "shot_duration_range_seconds":[5,10],
            "palette_roles":{
                "cyan":"predicted future state",
                "gold":"prediction error and useful surprise",
                "green":"viable correction",
                "crimson":"rigid prior and avoidance",
                "violet":"memory and learned expectation",
                "graphite":"physical constraint",
            }
        },
        "scenes":payload,
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return path


def make_contact_sheet(width,height):
    thumbs=[]
    tw=320
    th=int(tw*height/width)
    for index,scene in enumerate(SCENES,start=1):
        fc=max(2,round(scene.duration*DEFAULT_FPS))
        im=render_frame(scene,int(fc*.72),fc,width,height,index*1000+72)
        im.thumbnail((tw,th))
        thumbs.append((index,scene.title,im.copy()))
    cols=4
    rows=math.ceil(len(thumbs)/cols)
    cell_h=th+52
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),WHITE)
    d=ImageDraw.Draw(sheet)
    font=load_font(FONT_SANS_BOLD,15)
    for idx,title,im in thumbs:
        slot=idx-1;x=(slot%cols)*tw;y=(slot//cols)*cell_h
        sheet.paste(im,(x,y))
        d.text((x+10,y+th+8),f"{idx:02d}  {title}",font=font,fill=INK)
    path=OUTPUT/"contact_sheet.jpg"
    sheet.save(path,quality=94)
    return path


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS)
    p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    p.add_argument("--scene",type=int,default=None)
    p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()


def main():
    args=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    FRAMES.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    timeline=export_timeline()
    print(f"Timeline: {timeline}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")

    if args.scene is not None:
        if not 1<=args.scene<=len(SCENES):
            raise ValueError(f"--scene must be between 1 and {len(SCENES)}")
        result=render_scene(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview)
        print(result);return

    rendered=[]
    for index,scene in enumerate(SCENES,start=1):
        print(f"[{index:03d}/{len(SCENES):03d}] {scene.title} ({scene.duration:.1f}s)")
        result=render_scene(index,scene,args.fps,args.width,args.height,args.preview)
        if not args.preview:rendered.append(result)

    if not args.no_contact_sheet:
        print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview:
        print(f"Final video: {concatenate(rendered)}")


if __name__=="__main__":
    main()
