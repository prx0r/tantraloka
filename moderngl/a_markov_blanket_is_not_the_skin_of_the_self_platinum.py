#!/usr/bin/env python3
"""
A MARKOV BLANKET IS NOT THE SKIN OF THE SELF
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/02_a_markov_blanket_is_not_the_skin_of_the_self.md

DESIGN CONTRACT
---------------
• Every shot lasts 5–10 seconds.
• Every shot visibly performs the narrated operation.
• Clean white scientific field; deep field only for conditional-independence scenes.
• No static slide layouts and no decorative loops.
• Graphite = physical anatomy / literal membrane
• Cyan = sensory channels / incoming influence
• Green = active channels / outgoing influence
• Gold = statistical dependency boundary / inferred blanket
• Crimson = invalid inference / metaphysical inflation / failed partition
• Violet = hidden internal states / formal belief states
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: a mobile gold dependency contour overlays but never equals anatomy.
• Biological membranes must look material; blanket boundaries must look relational.
• Nested scales should morph continuously: cell → tissue → organ → organism.
• The final frame must preserve coupling across the boundary.

OUTPUT
------
output_markov_blanket/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  a_markov_blanket_is_not_the_skin_of_the_self.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.

USAGE
-----
python a_markov_blanket_is_not_the_skin_of_the_self_platinum.py
python a_markov_blanket_is_not_the_skin_of_the_self_platinum.py --preview
python a_markov_blanket_is_not_the_skin_of_the_self_platinum.py --scene 8
python a_markov_blanket_is_not_the_skin_of_the_self_platinum.py --fps 12 --width 1920 --height 1080
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_markov_blanket"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH=1280
DEFAULT_HEIGHT=720
DEFAULT_FPS=10

WHITE=(248,247,243); PAPER=(242,239,232); INK=(29,31,35); SOFT_INK=(84,88,94)
SILVER=(177,184,190); PALE_SILVER=(224,227,229)
CYAN=(55,153,181); PALE_CYAN=(192,226,233)
GREEN=(70,139,98); PALE_GREEN=(194,225,206)
GOLD=(194,153,68); PALE_GOLD=(235,218,175)
CRIMSON=(158,52,66); PALE_CRIMSON=(230,192,198)
VIOLET=(104,79,146); PALE_VIOLET=(216,205,232)
LAPIS=(48,72,124); VOID=(22,25,31)

FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0,hi=1): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*t
def mix(a,b,t):
    t=clamp(t)
    return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b:return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): return .5-.5*math.cos(math.pi*clamp(t))
def ease_out(t): t=clamp(t); return 1-(1-t)**3
def pulse(t,hz=1,phase=0): return .5+.5*math.sin(math.tau*(hz*t+phase))

def load_font(path,size):
    for p in (path,FONT_SERIF,FONT_SANS):
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()

def rgba_layer(size): return Image.new("RGBA",size,(0,0,0,0))
def background(w,h,seed,dark=False):
    rng=np.random.default_rng(seed); base=VOID if dark else WHITE
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=base
    arr+=rng.normal(0,1.1 if not dark else 1.7,(h,w,1))
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")
def centered_text(d,xy,text,font,fill=INK): d.text(xy,text,font=font,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered_text(d,(w/2,h*.875),title,load_font(FONT_SERIF_BOLD,max(22,int(h*.042))),color)
    if subtitle:centered_text(d,(w/2,h*.925),subtitle,load_font(FONT_SANS,max(13,int(h*.020))),SOFT_INK)
def border(im):
    w,h=im.size
    ImageDraw.Draw(im).rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*INK,46),width=2)
def glow_line(im,pts,color,width=4,glow=14,alpha=225):
    if len(pts)<2:return
    layer=rgba_layer(im.size); d=ImageDraw.Draw(layer)
    d.line(pts,fill=(*color,alpha),width=width,joint="curve")
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(glow))); im.alpha_composite(layer)
def glow_circle(im,cx,cy,r,color,alpha=180,blur=18):
    layer=rgba_layer(im.size); d=ImageDraw.Draw(layer)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*color,alpha))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    core=rgba_layer(im.size)
    ImageDraw.Draw(core).ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),
        fill=(*mix(color,WHITE,.28),min(255,alpha+40)))
    im.alpha_composite(core)
def partial_polyline(points,progress):
    progress=clamp(progress)
    if len(points)<2:return points
    lens=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]
    total=sum(lens); target=total*progress; out=[points[0]]; walked=0
    for i,L in enumerate(lens):
        if walked+L<=target:
            out.append(points[i+1]); walked+=L
        else:
            q=0 if L==0 else (target-walked)/L
            ax,ay=points[i]; bx,by=points[i+1]
            out.append((lerp(ax,bx,q),lerp(ay,by,q))); break
    return out
def arrow(d,start,end,color=INK,width=3,head=12):
    d.line((*start,*end),fill=color,width=width)
    a=math.atan2(end[1]-start[1],end[0]-start[0])
    for delta in (2.55,-2.55):
        p=(end[0]+math.cos(a+delta)*head,end[1]+math.sin(a+delta)*head)
        d.line((*end,*p),fill=color,width=width)
def organic_blob(d,cx,cy,rx,ry,color,phase=0,points=100,outline=None):
    pts=[]
    for i in range(points):
        a=math.tau*i/points
        wob=1+.06*math.sin(a*3+phase)+.035*math.sin(a*7-phase*.5)
        pts.append((cx+math.cos(a)*rx*wob,cy+math.sin(a)*ry*wob))
    d.polygon(pts,fill=color,outline=outline)
    return pts
def membrane_ring(d,cx,cy,rx,ry,phase=0,alpha=220):
    pts=[]
    for i in range(160):
        a=math.tau*i/160
        wob=1+.025*math.sin(a*8+phase)
        pts.append((cx+math.cos(a)*rx*wob,cy+math.sin(a)*ry*wob))
    d.line(pts+[pts[0]],fill=(*INK,alpha),width=5)
    for i in range(0,160,8):
        x,y=pts[i]
        d.ellipse((x-5,y-5,x+5,y+5),fill=(*PALE_CYAN,230),outline=(*CYAN,150))
def blanket_contour(d,cx,cy,rx,ry,phase=0,alpha=180,width=4):
    pts=[]
    for i in range(150):
        a=math.tau*i/150
        wob=1+.10*math.sin(a*3+phase)+.04*math.sin(a*11-phase)
        pts.append((cx+math.cos(a)*rx*wob,cy+math.sin(a)*ry*wob))
    d.line(pts+[pts[0]],fill=(*GOLD,alpha),width=width)
    return pts

@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict

def visual_visible_vs_invisible(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.42); right=(w*.70,h*.42)
    membrane_ring(d,*left,w*.15,h*.22,t*.3)
    blanket_contour(d,*right,w*.15,h*.22,t*.3,180,4)
    # material molecules inside left
    for i in range(24):
        a=i*math.tau/24
        x=left[0]+math.cos(a)*w*.10; y=left[1]+math.sin(a)*h*.13
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*CYAN,150))
    # relation lines inside right
    for i in range(9):
        a=i*math.tau/9
        x=right[0]+math.cos(a)*w*.10; y=right[1]+math.sin(a)*h*.13
        d.line((right[0],right[1],x,y),fill=(*GOLD,130),width=2)
    centered_text(d,(left[0],h*.70),"MEMBRANE",load_font(FONT_SANS_BOLD,int(h*.018)),INK)
    centered_text(d,(right[0],h*.70),"MARKOV BLANKET",load_font(FONT_SANS_BOLD,int(h*.018)),GOLD)
    seal(im,"ONE IS MATERIAL · ONE IS CONDITIONAL","a Markov blanket is not the skin of the self")

def visual_bayesian_node(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    center=(w*.5,h*.42)
    parents=[(w*.25,h*.24),(w*.42,h*.18)]
    child=(w*.56,h*.62); coparents=[(w*.74,h*.22),(w*.79,h*.55)]
    nodes=[("X",center,VIOLET)]+[("P",pt,CYAN) for pt in parents]+[("C",child,GREEN)]+[("O",pt,GOLD) for pt in coparents]
    for label,(x,y),col in nodes:
        d.ellipse((x-28,y-28,x+28,y+28),fill=(*mix(WHITE,col,.18),230),outline=(*col,190),width=3)
        centered_text(d,(x,y),label,load_font(FONT_SANS_BOLD,int(h*.020)),col)
    for pt in parents: arrow(d,pt,center,CYAN,3,9)
    arrow(d,center,child,GREEN,3,9)
    for pt in coparents: arrow(d,pt,child,GOLD,3,9)
    q=smoothstep(.25,.90,u)
    blanket_contour(d,w*.52,h*.41,w*.34*q,h*.31*q,t*.2,190,4)
    seal(im,"PARENTS · CHILDREN · CO-PARENTS","the minimal set that screens a node from the rest")

def visual_four_states(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    xs=[w*.18,w*.40,w*.62,w*.84]
    labels=[("EXTERNAL",CRIMSON),("SENSORY",CYAN),("ACTIVE",GREEN),("INTERNAL",VIOLET)]
    for i,(x,(label,col)) in enumerate(zip(xs,labels)):
        q=smoothstep(i*.10,.58+i*.07,u)
        d.rounded_rectangle((x-72*q,h*.35-45*q,x+72*q,h*.35+45*q),radius=18,
                            fill=(*mix(WHITE,col,.15),int(225*q)),outline=(*col,int(180*q)),width=3)
        if q>.6:centered_text(d,(x,h*.35),label,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    arrow(d,(xs[0]+72,h*.35),(xs[1]-72,h*.35),CYAN,4,10)
    arrow(d,(xs[1]+72,h*.35),(xs[3]-72,h*.35),CYAN,4,10)
    arrow(d,(xs[3]-72,h*.47),(xs[2]+72,h*.47),GREEN,4,10)
    arrow(d,(xs[2]-72,h*.47),(xs[0]+72,h*.47),GREEN,4,10)
    # blanket is middle pair
    d.rounded_rectangle((xs[1]-95,h*.22,xs[2]+95,h*.58),radius=30,outline=(*GOLD,190),width=5)
    seal(im,"THE BLANKET IS SENSORY + ACTIVE STATES","it specifies the route of relation, not isolation")

def visual_membrane_approximation(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    membrane_ring(d,cx,cy,w*.22,h*.28,t*.3)
    # receptors and pumps
    for i in range(16):
        a=i*math.tau/16
        x=cx+math.cos(a)*w*.22; y=cy+math.sin(a)*h*.28
        col=CYAN if i%2==0 else GREEN
        d.rounded_rectangle((x-8,y-14,x+8,y+14),radius=5,fill=(*mix(WHITE,col,.2),230),outline=(*col,170))
    # gold contour drifts across anatomy
    shift=math.sin(t*.7)*w*.035
    blanket_contour(d,cx+shift,cy,w*.25,h*.25,t*.4,170,4)
    # molecule outside participating
    ox=cx+w*.30; oy=cy-h*.06
    glow_circle(im,ox,oy,14,GOLD,160,10)
    glow_line(im,[(ox,oy),(cx+w*.15,cy)],GOLD,3,10,170)
    seal(im,"THE MEMBRANE MAY REALIZE SOME DEPENDENCIES","but anatomy and blanket are not automatically identical")

def visual_model_world_gap(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.28,h*.42); right=(w*.72,h*.42)
    # model graph
    for i in range(7):
        a=i*math.tau/7
        x=left[0]+math.cos(a)*80; y=left[1]+math.sin(a)*65
        d.ellipse((x-10,y-10,x+10,y+10),fill=(*PALE_GOLD,230),outline=(*GOLD,170))
        d.line((left[0],left[1],x,y),fill=(*GOLD,120),width=2)
    d.ellipse((left[0]-22,left[1]-22,left[0]+22,left[1]+22),fill=(*VIOLET,190))
    # living cell
    membrane_ring(d,*right,w*.14,h*.20,t*.25)
    organic_blob(d,*right,w*.08,h*.11,(*PALE_CYAN,210),t*.2,outline=(*CYAN,150))
    # bridge question
    q=smoothstep(.28,.88,u)
    d.line((left[0]+90,left[1],right[0]-90,right[1]),fill=(*CRIMSON,int(180*q)),width=4)
    centered_text(d,(w*.5,h*.34),"? MODEL → WORLD ?",load_font(FONT_SANS_BOLD,int(h*.018)),CRIMSON)
    seal(im,"A PARTITION IN A MODEL IS NOT YET NATURE'S TRUE EDGE","the bridge requires argument and evidence")

def visual_dynamic_partition(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    rng=random.Random(61)
    pts=[(rng.uniform(w*.18,w*.82),rng.uniform(h*.18,h*.68)) for _ in range(95)]
    q=ease(u)
    # dynamic contour moves through particle field
    contour=[]
    for i in range(160):
        a=i*math.tau/160
        r=w*(.16+.035*math.sin(t*.55+a*3))
        contour.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.72))
    d.line(contour+[contour[0]],fill=(*GOLD,180),width=4)
    for x,y in pts:
        inside=((x-cx)/(w*.18))**2+((y-cy)/(h*.18))**2<1
        col=GREEN if inside else SILVER
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*col,150))
    # show violation channels crossing
    for i in range(5):
        y=h*(.24+i*.09)
        glow_line(im,[(w*.14,y),(w*.86,h*.68-y+h*.24)],CRIMSON,2,8,int(120+60*q))
    seal(im,"BLANKETS MAY BE DYNAMIC · GRADED · TEMPORARY","the idea becomes scientific when it can fail")

def visual_self_evidencing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    membrane_ring(d,cx,cy,w*.14,h*.20,t*.25)
    blanket_contour(d,cx,cy,w*.18,h*.24,t*.35,170,4)
    cycle=[("SENSE",CYAN,-150,-70),("INFER",VIOLET,0,-145),("ACT",GREEN,155,-60),("EVIDENCE",GOLD,0,145)]
    points=[]
    for name,col,ox,oy in cycle:
        x=cx+ox; y=cy+oy; points.append((x,y))
        d.ellipse((x-28,y-28,x+28,y+28),fill=(*mix(WHITE,col,.18),225),outline=(*col,180),width=3)
        centered_text(d,(x,y),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    for a,b,col in zip(points,points[1:]+points[:1],[CYAN,VIOLET,GREEN,GOLD]):
        glow_line(im,partial_polyline([a,b],ease(u)),col,4,11,180)
    seal(im,"THE LIVING FORM IS A HYPOTHESIS","action helps make the hypothesis true")

def visual_empirical_questions(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    questions=["INTERNAL STATES?","SENSORY CHANNELS?","ACTION POLICIES?","FREE-ENERGY FUNCTIONAL?","PERTURBATION?"]
    cx,cy=w*.5,h*.42
    for i,qtext in enumerate(questions):
        a=-math.pi/2+i*math.tau/5
        x=cx+math.cos(a)*w*.27; y=cy+math.sin(a)*h*.25
        q=smoothstep(i*.10,.62+i*.06,u)
        d.rounded_rectangle((x-110*q,y-23*q,x+110*q,y+23*q),radius=14,
                            fill=(*PALE_SILVER,int(220*q)),outline=(*INK,int(150*q)),width=2)
        if q>.65:centered_text(d,(x,y),qtext,load_font(FONT_SANS_BOLD,int(h*.014)),INK)
        d.line((cx,cy,x,y),fill=(*CRIMSON,int(120*q)),width=2)
    glow_circle(im,cx,cy,20,GOLD,150,12)
    seal(im,"FORMAL ELEGANCE DOES NOT REPLACE IDENTIFICATION","the blanket is a tool, not a finished theory of life")

def visual_nested_blankets(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    levels=[("CELL",55,CYAN),("TISSUE",95,GREEN),("ORGAN",145,GOLD),("ORGANISM",205,VIOLET)]
    for i,(name,r,col) in enumerate(levels):
        q=smoothstep(i*.12,.62+i*.07,u)
        d.ellipse((cx-r*q,cy-r*.62*q,cx+r*q,cy+r*.62*q),
                  outline=(*col,int(185*q)),width=4)
        if q>.65:centered_text(d,(cx,cy-r*.62*q-18),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    # emergent heartbeat
    beat=pulse(t,1.2)
    glow_circle(im,cx,cy,12+18*beat,CRIMSON,150,10)
    seal(im,"BLANKETS OF BLANKETS","higher-level variables need not belong to any single part")

def visual_density_gradient(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    # density field
    for r in range(220,20,-12):
        frac=1-r/220
        alpha=int(12+95*frac)
        col=mix(PALE_GOLD,GOLD,frac)
        d.ellipse((cx-r,cy-r*.62,cx+r,cy+r*.62),outline=(*col,alpha),width=5)
    # moving object pattern
    shift=math.sin(t*.55)*w*.08
    organic_blob(d,cx+shift,cy,w*.11,h*.14,(*PALE_CYAN,210),t*.3,outline=(*CYAN,170))
    seal(im,"BOUNDARY AS DENSITY, NOT BINARY EDGE","living objects exchange matter, migrate, and replace components")

def visual_pattern_not_line(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    examples=[("FLAME",CRIMSON,w*.20),("CELL",CYAN,w*.40),("PERSON + TOOL",GREEN,w*.63),("LANGUAGE",VIOLET,w*.84)]
    for i,(name,col,x) in enumerate(examples):
        q=smoothstep(i*.10,.60+i*.07,u)
        if i==0:
            pts=[(x,h*.58),(x-35*q,h*.42),(x,h*.24),(x+35*q,h*.42)]
            d.polygon(pts,fill=(*PALE_CRIMSON,int(220*q)),outline=(*col,int(180*q)))
        elif i==1:
            membrane_ring(d,x,h*.43,45*q,62*q,t*.2,int(210*q))
        elif i==2:
            d.ellipse((x-18*q,h*.28-18*q,x+18*q,h*.28+18*q),outline=(*INK,int(190*q)),width=3)
            d.line((x,h*.30,x,h*.52),fill=(*INK,int(190*q)),width=4)
            d.line((x,h*.38,x+70*q,h*.30),fill=(*GREEN,int(190*q)),width=4)
        else:
            for j in range(6):
                yy=h*(.28+j*.06)
                d.line((x-45*q,yy,x+45*q,yy),fill=(*VIOLET,int(150*q)),width=3)
        if q>.7:centered_text(d,(x,h*.68),name,load_font(FONT_SANS_BOLD,int(h*.013)),col)
    seal(im,"OBJECTHOOD MAY REQUIRE TRACKING A DYNAMIC PATTERN","not drawing one permanent line")

def visual_metaphysical_inflation(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    claims=[("BLANKET",GOLD),("SELF",CYAN),("MIND",VIOLET),("CONSCIOUSNESS",CRIMSON)]
    xs=[w*.16,w*.38,w*.62,w*.84]
    for i,((name,col),x) in enumerate(zip(claims,xs)):
        q=smoothstep(i*.12,.58+i*.08,u)
        d.ellipse((x-58*q,h*.40-58*q,x+58*q,h*.40+58*q),
                  fill=(*mix(WHITE,col,.15),int(220*q)),outline=(*col,int(180*q)),width=3)
        if q>.65:centered_text(d,(x,h*.40),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
        if i>0:
            d.line((xs[i-1]+58,h*.40,x-58,h*.40),fill=(*CRIMSON,int(160*q)),width=4)
    q=smoothstep(.55,.92,u)
    d.line((w*.12,h*.26,w*.88,h*.56),fill=(*CRIMSON,int(220*q)),width=7)
    seal(im,"CONDITIONAL INDEPENDENCE IS NOT SUBJECTIVITY","renaming the structure does not solve the hard problem")

def visual_distributed_self(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.42
    body=(cx,cy)
    membrane_ring(d,*body,w*.11,h*.20,t*.2)
    extensions=[("TOOL",GREEN,w*.18,h*.27),("LANGUAGE",VIOLET,w*.80,h*.23),
                ("OTHER PERSON",CYAN,w*.82,h*.60),("MICROBES",GOLD,w*.18,h*.61)]
    for name,col,x,y in extensions:
        glow_line(im,[(cx,cy),(x,y)],col,4,11,180)
        d.ellipse((x-28,y-28,x+28,y+28),fill=(*mix(WHITE,col,.18),225),outline=(*col,180),width=3)
        centered_text(d,(x,y),name,load_font(FONT_SANS_BOLD,int(h*.012)),col)
    # multiple question-specific contours
    for idx,(rx,ry,col) in enumerate([(170,120,GREEN),(230,155,VIOLET),(285,190,GOLD)]):
        q=smoothstep(.18+idx*.12,.75+idx*.05,u)
        d.ellipse((cx-rx*q,cy-ry*q,cx+rx*q,cy+ry*q),outline=(*col,int(100*q)),width=3)
    seal(im,"THE TRUE BOUNDARY DEPENDS UPON THE QUESTION","metabolic · legal · experiential · immunological selves cut differently")

def visual_testable_dependency(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    # dependency matrix
    n=9; x0=w*.25; y0=h*.20; cell=34
    rng=random.Random(21)
    for i in range(n):
        for j in range(n):
            val=rng.random()
            col=GOLD if val>.72 else (CYAN if val>.48 else PALE_SILVER)
            alpha=200 if val>.48 else 100
            d.rectangle((x0+j*cell,y0+i*cell,x0+(j+1)*cell-3,y0+(i+1)*cell-3),
                        fill=(*col,alpha))
    # intervention arrow
    arrow(d,(w*.62,h*.34),(w*.80,h*.34),CRIMSON,4,12)
    d.rounded_rectangle((w*.78,h*.25,w*.92,h*.44),radius=18,outline=(*CRIMSON,180),width=3)
    centered_text(d,(w*.85,h*.345),"TEST",load_font(FONT_SANS_BOLD,int(h*.020)),CRIMSON)
    seal(im,"PRECISION BEFORE METAPHOR","useful blankets expose dependencies, interventions, and screening-off")

def visual_final_grammar(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    membrane_ring(d,cx,cy,w*.15,h*.22,t*.25)
    blanket_contour(d,cx,cy,w*.23,h*.27,t*.35,190,5)
    # channels cross but only through organized gates
    gates=[(-.75,CYAN),(-.25,GREEN),(.25,CYAN),(.75,GREEN)]
    for off,col in gates:
        y=cy+off*h*.16
        if col==CYAN:
            arrow(d,(w*.12,y),(cx-w*.16,y),CYAN,4,10)
        else:
            arrow(d,(cx+w*.16,y),(w*.88,y),GREEN,4,10)
    # internal-external particles remain coupled
    for i in range(14):
        a=i*math.tau/14+t*.12
        r=w*(.07 if i%2==0 else .31)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.62
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(VIOLET,GOLD,i/13),160))
    seal(im,"A PROVISIONAL INSIDE WITHOUT INDEPENDENCE","the blanket is the grammar of controlled dependence",GREEN)

VISUALS:dict[str,Callable]={
    "visible":visual_visible_vs_invisible,
    "bayes":visual_bayesian_node,
    "four":visual_four_states,
    "membrane":visual_membrane_approximation,
    "gap":visual_model_world_gap,
    "dynamic":visual_dynamic_partition,
    "self_evidencing":visual_self_evidencing,
    "questions":visual_empirical_questions,
    "nested":visual_nested_blankets,
    "density":visual_density_gradient,
    "pattern":visual_pattern_not_line,
    "inflation":visual_metaphysical_inflation,
    "distributed":visual_distributed_self,
    "testable":visual_testable_dependency,
    "final":visual_final_grammar,
}

SCENES:list[Scene]=[
    Scene("Visible membrane","A cell membrane is visible.",5.5,"visible",{}),
    Scene("Invisible blanket","A Markov blanket is not.",5.5,"visible",{}),
    Scene("Material membrane","The membrane is made of lipids and proteins.",6.5,"visible",{}),
    Scene("Conditional blanket","The blanket is made of conditional independencies.",7.0,"visible",{}),
    Scene("Does not stop matter","It does not stop matter.",5.5,"visible",{}),
    Scene("Mathematics first","The phrase sounds biological, but it is mathematics first.",7.5,"visible",{}),
    Scene("Not skin","A Markov blanket is not the skin of the self.",6.5,"final",{}),

    Scene("Graphical models","The concept comes from probabilistic graphical models.",6.5,"bayes",{}),
    Scene("Choose variable","Choose a variable or set of variables.",5.5,"bayes",{}),
    Scene("Minimal collection","Its blanket is the minimal collection that makes it conditionally independent from the rest.",9.0,"bayes",{}),
    Scene("Known blanket","Once blanket states are known, information beyond them adds nothing further in the model.",9.0,"bayes",{}),
    Scene("Parents children","For a Bayesian node, the blanket includes parents, children, and co-parents.",8.0,"bayes",{}),
    Scene("No fabric","The definition concerns statistical dependence. No literal fabric is required.",8.0,"bayes",{}),
    Scene("Relative boundary","The boundary exists relative to variables and probability structure chosen for analysis.",9.0,"bayes",{}),

    Scene("Biological partition","Active inference gives the partition a biological interpretation.",7.0,"four",{}),
    Scene("Four groups","States divide into internal, external, sensory, and active.",8.0,"four",{}),
    Scene("Sensory route","External states influence sensory states, which affect internal states.",8.0,"four",{}),
    Scene("Active route","Internal states influence active states, which affect external states.",8.0,"four",{}),
    Scene("Blanket middle","The blanket consists of sensory and active states.",7.0,"four",{}),
    Scene("Statistical interface","The organism meets the world through a statistical interface.",7.5,"four",{}),
    Scene("Not isolation","The blanket does not isolate the two sides. It specifies their route of relation.",9.0,"four",{}),

    Scene("Cell intuition","A cell offers an intuitive example, but only approximately.",7.0,"membrane",{}),
    Scene("Receptors channels","The membrane carries receptors, channels, pumps, and cytoskeletal machinery.",8.5,"membrane",{}),
    Scene("External chemistry","External chemistry affects receptor and membrane states.",7.5,"membrane",{}),
    Scene("Internal action","Internal processes alter movement, secretion, and exchange.",7.5,"membrane",{}),
    Scene("Some dependencies","The physical boundary may realize some dependencies represented by a blanket.",8.5,"membrane",{}),
    Scene("Not identical","Membrane and blanket are not automatically identical.",7.0,"membrane",{}),
    Scene("Model dependence","The partition depends on timescale, coarse-graining, and variables selected.",8.5,"dynamic",{}),
    Scene("Across anatomy","A statistical boundary can cut across anatomical ones.",7.0,"dynamic",{}),
    Scene("Must demonstrate","The mathematics must be demonstrated, not inferred from visual resemblance.",8.0,"gap",{}),

    Scene("First caution","This is the first major caution.",5.5,"gap",{}),
    Scene("No unique metaphysical edge","Bayesian success does not prove one unique metaphysical boundary for every living thing.",9.5,"gap",{}),
    Scene("Pearl blanket","A Pearl blanket is an epistemic structure in a probabilistic model.",8.0,"bayes",{}),
    Scene("Friston blanket","A Friston-style blanket is asked to identify a persisting physical system.",8.0,"membrane",{}),
    Scene("More assumptions","The second use requires more assumptions.",6.0,"gap",{}),
    Scene("Model to world","One cannot move from a model partition to nature's true edge without argument.",9.0,"gap",{}),
    Scene("Discovered or imposed","The blanket may be discovered or imposed by description.",8.0,"gap",{}),

    Scene("Sharper question","The criticism does not make the framework useless. It makes the question sharper.",8.0,"dynamic",{}),
    Scene("Real partition","When do real non-equilibrium dynamics support a stable partition?",8.0,"dynamic",{}),
    Scene("Sparse not enough","Sparse connectivity alone is not enough.",6.5,"dynamic",{}),
    Scene("Scale violation","A living system may approximate a blanket at one scale and violate it at another.",9.0,"dynamic",{}),
    Scene("Dynamic graded temporary","Blankets may be dynamic, graded, or temporary.",7.5,"dynamic",{}),
    Scene("Can fail","The idea becomes scientifically interesting when it can fail.",7.0,"dynamic",{}),
    Scene("Definition cannot explain","A boundary that exists only by definition cannot explain autonomy.",8.5,"dynamic",{}),

    Scene("Free-energy layer","The free-energy principle adds another layer.",6.5,"self_evidencing",{}),
    Scene("Limited states","A living system persists in a limited range rather than diffusing everywhere.",8.0,"self_evidencing",{}),
    Scene("Formal expectations","Internal dynamics can be described as encoding expectations through sensory states.",8.5,"self_evidencing",{}),
    Scene("Actions maintain","Actions alter the environment and sensory stream to maintain viable organization.",9.0,"self_evidencing",{}),
    Scene("No calculation","This does not mean the cell consciously calculates probabilities.",7.5,"self_evidencing",{}),
    Scene("Formal belief","Belief here is formal and may exist without experienced conviction.",8.0,"self_evidencing",{}),

    Scene("Self-evidencing","Self-evidencing names the loop.",6.0,"self_evidencing",{}),
    Scene("Bring about evidence","A living system brings about sensory states consistent with continued existence.",8.5,"self_evidencing",{}),
    Scene("Fish water","A fish seeks water.",5.5,"self_evidencing",{}),
    Scene("Bacterium gradient","A bacterium moves through chemical gradients.",6.5,"self_evidencing",{}),
    Scene("Temperature regulation","A body regulates temperature.",6.5,"self_evidencing",{}),
    Scene("Living hypothesis","The organism creates evidence for the model embodied in its organization.",8.5,"self_evidencing",{}),
    Scene("Action makes true","The living form is a hypothesis continually tested; action helps make it true.",9.0,"self_evidencing",{}),

    Scene("Circular language","But this language can become circular.",6.0,"questions",{}),
    Scene("Persists because surprise","The organism persists because it minimizes surprise.",6.5,"questions",{}),
    Scene("Minimizes because persists","We know it minimizes surprise because it persists.",6.5,"questions",{}),
    Scene("Need mechanisms","Explanatory power requires mechanisms, variables, and novel predictions.",8.5,"questions",{}),
    Scene("Which states","Which internal states?",5.0,"questions",{}),
    Scene("Which channels","Which sensory channels?",5.0,"questions",{}),
    Scene("Which policies","Which action policies?",5.0,"questions",{}),
    Scene("Which functional","Which free-energy functional?",5.5,"questions",{}),
    Scene("Which perturbation","Which perturbation should disrupt the inferred blanket?",6.5,"questions",{}),
    Scene("Tool not theory","The blanket is a tool, not a finished theory of life.",7.5,"questions",{}),

    Scene("Nested blankets","Nested blankets make the picture more complex.",6.5,"nested",{}),
    Scene("Cells tissues","Cells form tissues.",5.5,"nested",{}),
    Scene("Tissues organs","Tissues form organs.",5.5,"nested",{}),
    Scene("Organs organisms","Organs form organisms.",5.5,"nested",{}),
    Scene("Not sum","The organism is not merely the sum of cell blankets.",7.0,"nested",{}),
    Scene("Emergent variables","Higher-level variables emerge through collective dynamics.",7.5,"nested",{}),
    Scene("Heart state","A heart has states no single cardiomyocyte possesses.",7.0,"nested",{}),
    Scene("Community pattern","A community has communication patterns no individual carries alone.",8.0,"nested",{}),
    Scene("Blankets of blankets","Markov blankets can in principle be blankets of blankets.",7.5,"nested",{}),
    Scene("Not equal agency","This does not prove that every scale is equally agentic.",7.5,"nested",{}),

    Scene("Density proposal","Recent work treats blanket density as graded across space.",7.5,"density",{}),
    Scene("Dynamic detection","Dynamic detection can identify macroscopic objects from changing microscopic roles.",9.0,"density",{}),
    Scene("Early proposals","These proposals are early.",5.5,"density",{}),
    Scene("Exchange and replacement","Real organisms exchange matter, change shape, migrate, and replace components.",8.5,"density",{}),
    Scene("Fixed edge too rigid","A fixed binary edge may be too rigid.",6.5,"density",{}),
    Scene("Maintained by activity","The living boundary is maintained through activity.",7.0,"density",{}),
    Scene("Flame no membrane","A flame has no membrane.",5.5,"pattern",{}),
    Scene("Cell replaces molecules","A cell replaces molecules.",6.0,"pattern",{}),
    Scene("Person tool","A person extends action through tools.",6.5,"pattern",{}),
    Scene("Pattern not line","Objecthood may require tracking a dynamic pattern rather than a permanent line.",8.5,"pattern",{}),

    Scene("Inflation temptation","This is where metaphysical inflation becomes tempting.",6.5,"inflation",{}),
    Scene("Every blanket self","If blankets define things, perhaps every blanket is a self.",7.5,"inflation",{}),
    Scene("Earth mind","If blankets nest through the biosphere, perhaps Earth is one mind.",8.0,"inflation",{}),
    Scene("All conscious","If internal states infer, perhaps all bounded systems are conscious.",8.0,"inflation",{}),
    Scene("Does not follow","None of these conclusions follows automatically.",7.0,"inflation",{}),
    Scene("Independence not subjectivity","Conditional independence is not subjectivity.",6.5,"inflation",{}),
    Scene("Autonomies differ","Statistical autonomy is not biological autonomy, and biological autonomy is not consciousness.",9.0,"inflation",{}),
    Scene("Pendulum","A pendulum may admit a blanket-like partition without feeling motion.",7.5,"inflation",{}),
    Scene("Hard problem remains","The framework does not settle the hard problem by changing vocabulary.",8.0,"inflation",{}),

    Scene("Skin important","The skin remains important.",5.5,"distributed",{}),
    Scene("Physical achievement","It regulates exchange, prevents mixing, hosts sensation, and marks vulnerability.",8.5,"distributed",{}),
    Scene("Lived self extends","But the lived self is not coextensive with skin.",7.0,"distributed",{}),
    Scene("Tools action","Tools can become parts of action.",6.5,"distributed",{}),
    Scene("Language memory","Language extends memory into culture.",6.5,"distributed",{}),
    Scene("Other people regulate","Other people regulate emotion and physiology.",7.5,"distributed",{}),
    Scene("Microbes metabolism","Microbes participate in metabolism.",6.5,"distributed",{}),
    Scene("Different selves","Metabolic, legal, experiential, and immunological selves cut the world differently.",9.0,"distributed",{}),

    Scene("Precision over romance","The precision of the boundary matters more than the romance of the metaphor.",8.0,"testable",{}),
    Scene("Useful blanket","A blanket is useful when it exposes a testable dependency structure.",8.0,"testable",{}),
    Scene("Clarifies intervention","It should clarify intervention and predict which variables screen one another off.",9.0,"testable",{}),
    Scene("Decorative blanket","It becomes decorative when every interesting object is declared blanketed after the fact.",8.5,"testable",{}),

    Scene("Return membrane","A cell membrane is visible.",5.5,"final",{}),
    Scene("Return blanket","A Markov blanket is not.",5.5,"final",{}),
    Scene("Mutual modeling","The membrane can help realize a blanket; the blanket can model the membrane's role.",9.0,"final",{}),
    Scene("Confusion loses precision","Confusing them makes both less precise.",7.0,"final",{}),
    Scene("No mystical aura","The living boundary is not a mystical aura.",6.5,"final",{}),
    Scene("Controlled dependence","It is a pattern of controlled dependence.",7.0,"final",{}),
    Scene("Coupled channels","Inside and outside continue affecting one another through organized channels.",8.5,"final",{}),
    Scene("Grammar","A Markov blanket is the grammar describing how a provisional inside can exist without independence.",10.0,"final",{}),
]

def render_frame(scene,frame_index,frame_count,width,height,seed):
    u=frame_index/max(1,frame_count-1); t=u*scene.duration
    im=background(width,height,seed,False)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im)
    return im.convert("RGB")

def require_ffmpeg():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg is required but was not found on PATH")
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
    frame_dir.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
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
    output_path=OUTPUT/"a_markov_blanket_is_not_the_skin_of_the_self.mp4"
    cmd=[ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat_file),
         "-c","copy","-movflags","+faststart",str(output_path)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output_path

def export_timeline():
    cursor=0; payload=[]
    for index,scene in enumerate(SCENES,start=1):
        rec=asdict(scene); rec["scene_id"]=f"scene_{index:03d}"
        rec["start_seconds"]=round(cursor,3); rec["end_seconds"]=round(cursor+scene.duration,3)
        payload.append(rec); cursor+=scene.duration
    path=OUTPUT/"narration_timeline.json"
    path.write_text(json.dumps({
        "title":"a markov blanket is not the skin of the self",
        "runtime_seconds":round(cursor,3),
        "scene_count":len(SCENES),
        "style":{
            "background":"clean white scientific field",
            "continuity_object":"mobile gold dependency contour over graphite-cyan anatomy",
            "shot_duration_range_seconds":[5,10],
            "palette_roles":{
                "graphite":"physical anatomy",
                "cyan":"sensory influence",
                "green":"active influence",
                "gold":"statistical blanket",
                "crimson":"failed inference or metaphysical inflation",
                "violet":"hidden internal states",
            }
        },
        "scenes":payload
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return path

def make_contact_sheet(width,height):
    thumbs=[]; tw=320; th=int(tw*height/width)
    for index,scene in enumerate(SCENES,start=1):
        fc=max(2,round(scene.duration*DEFAULT_FPS))
        im=render_frame(scene,int(fc*.72),fc,width,height,index*1000+72)
        im.thumbnail((tw,th)); thumbs.append((index,scene.title,im.copy()))
    cols=4; rows=math.ceil(len(thumbs)/cols); cell_h=th+52
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),WHITE); d=ImageDraw.Draw(sheet)
    font=load_font(FONT_SANS_BOLD,15)
    for idx,title,im in thumbs:
        slot=idx-1; x=(slot%cols)*tw; y=(slot//cols)*cell_h
        sheet.paste(im,(x,y)); d.text((x+10,y+th+8),f"{idx:03d}  {title}",font=font,fill=INK)
    path=OUTPUT/"contact_sheet.jpg"; sheet.save(path,quality=94); return path

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
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    timeline=export_timeline()
    print(f"Timeline: {timeline}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if args.scene is not None:
        if not 1<=args.scene<=len(SCENES):raise ValueError(f"--scene must be between 1 and {len(SCENES)}")
        print(render_scene(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview)); return
    rendered=[]
    for index,scene in enumerate(SCENES,start=1):
        print(f"[{index:03d}/{len(SCENES):03d}] {scene.title} ({scene.duration:.1f}s)")
        result=render_scene(index,scene,args.fps,args.width,args.height,args.preview)
        if not args.preview:rendered.append(result)
    if not args.no_contact_sheet:print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview:print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
