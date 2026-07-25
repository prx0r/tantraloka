#!/usr/bin/env python3
"""
YOUR CELLS MAY BE SOLVING A PROBLEM CALLED YOU
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/05_your_cells_may_be_solving_a_problem_called_you.md

DESIGN CONTRACT
---------------
• Every shot lasts 5–10 seconds.
• Every shot visibly performs the narrated operation.
• White developmental-biology field; dark field only for morphospace.
• No static slide layouts and no decorative loops.
• Gold = target morphology / preferred anatomical solution
• Cyan = bioelectric communication / local cellular sensing
• Green = successful regeneration / restored proportion
• Crimson = anatomical error / competing target / local defection
• Violet = gene expression / latent state / conceptual interpretation
• Graphite = physical anatomy / wound / tissue constraint
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: a gold target-form silhouette remains ahead of the tissue.
• The target must never appear as a tiny blueprint hidden inside a cell.
• Morphogenesis is rendered as navigation through a space of possible forms.
• Scientific and Śaiva interpretations remain visually distinct.

OUTPUT
------
output_cells_solving_you/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  your_cells_may_be_solving_a_problem_called_you.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"output_cells_solving_you"
FRAMES=OUTPUT/"frames"
SCENES_DIR=OUTPUT/"scenes"
DEFAULT_WIDTH=1280; DEFAULT_HEIGHT=720; DEFAULT_FPS=10

WHITE=(248,247,243); PAPER=(242,239,232); INK=(29,31,35); SOFT_INK=(84,88,94)
SILVER=(177,184,190); PALE_SILVER=(224,227,229)
CYAN=(55,153,181); PALE_CYAN=(192,226,233)
GOLD=(194,153,68); PALE_GOLD=(235,218,175)
GREEN=(70,139,98); PALE_GREEN=(194,225,206)
CRIMSON=(158,52,66); PALE_CRIMSON=(230,192,198)
VIOLET=(104,79,146); PALE_VIOLET=(216,205,232)
VOID=(22,25,31)

FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0,hi=1): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*t
def mix(a,b,t):
    t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b:return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): return .5-.5*math.cos(math.pi*clamp(t))
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
    arr+=rng.normal(0,1.05 if not dark else 1.7,(h,w,1))
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")
def centered_text(d,xy,text,font,fill=INK): d.text(xy,text,font=font,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK,dark=False):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered_text(d,(w/2,h*.875),title,load_font(FONT_SERIF_BOLD,max(22,int(h*.042))),WHITE if dark else color)
    if subtitle:centered_text(d,(w/2,h*.925),subtitle,load_font(FONT_SANS,max(13,int(h*.020))),PALE_SILVER if dark else SOFT_INK)
def border(im,dark=False):
    w,h=im.size
    ImageDraw.Draw(im).rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*(WHITE if dark else INK),42),width=2)
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
    ImageDraw.Draw(core).ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=(*mix(color,WHITE,.28),min(255,alpha+40)))
    im.alpha_composite(core)
def partial_polyline(points,progress):
    progress=clamp(progress)
    if len(points)<2:return points
    lens=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]
    total=sum(lens); target=total*progress; out=[points[0]]; walked=0
    for i,L in enumerate(lens):
        if walked+L<=target: out.append(points[i+1]); walked+=L
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
def cell(d,x,y,r,color,alpha=220,nucleus=True):
    d.ellipse((x-r,y-r,x+r,y+r),fill=(*mix(WHITE,color,.16),alpha),outline=(*color,min(255,alpha+10)),width=3)
    if nucleus:d.ellipse((x-r*.26,y-r*.26,x+r*.26,y+r*.26),fill=(*mix(color,VIOLET,.35),160))
def planarian_outline(d,cx,cy,length,height,color,alpha=180,width=4,heads=1):
    pts=[]
    for i in range(120):
        q=i/119; x=lerp(cx-length/2,cx+length/2,q)
        taper=math.sin(q*math.pi)**.65
        y=cy-height*taper*(.5+.08*math.sin(q*math.tau*2))
        pts.append((x,y))
    for i in range(119,-1,-1):
        q=i/119; x=lerp(cx-length/2,cx+length/2,q)
        taper=math.sin(q*math.pi)**.65
        y=cy+height*taper*(.5+.08*math.sin(q*math.tau*2))
        pts.append((x,y))
    d.line(pts+[pts[0]],fill=(*color,alpha),width=width)
    for side in range(heads):
        hx=cx+length/2-(side*length)
        d.ellipse((hx-10,cy-10,hx+10,cy+10),fill=(*color,alpha))
def tissue_points(w,h,cols=14,rows=8):
    out=[]
    for j in range(rows):
        for i in range(cols):
            out.append((w*(.12+i*(.76/(cols-1))),h*(.18+j*(.48/(rows-1))),i,j))
    return out
def body_map(im,phase=0,alpha=75):
    w,h=im.size
    for j in range(9):
        pts=[]
        for i in range(180):
            q=i/179
            x=lerp(w*.08,w*.92,q)
            y=h*(.16+j*.06)+math.sin(q*math.tau*2+phase+j*.45)*10
            pts.append((x,y))
        glow_line(im,pts,CYAN,2,7,alpha)

@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict

def visual_cut_regenerate(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    if q<.35:
        planarian_outline(d,w*.5,h*.42,w*.55,h*.18,INK,220,5)
        x=lerp(w*.33,w*.67,q/.35)
        d.line((x,h*.24,x,h*.60),fill=(*CRIMSON,220),width=5)
    else:
        pieces=[(w*.24,h*.42),(w*.50,h*.42),(w*.76,h*.42)]
        local=(q-.35)/.65
        for idx,(cx,cy) in enumerate(pieces):
            L=lerp(w*.12,w*.22,local); H=lerp(h*.08,h*.13,local)
            planarian_outline(d,cx,cy,L,H,mix(CRIMSON,GREEN,local),200,4)
    seal(im,"THE FRAGMENTS DO MORE THAN CLOSE THE WOUND","they rebuild missing structure, proportion, and stopping")

def visual_target_ahead(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    # gold target
    planarian_outline(d,cx,cy,w*.55,h*.18,GOLD,135,5,p.get("heads",1))
    rng=random.Random(45); q=ease(u)
    for i in range(85):
        sx=rng.uniform(w*.18,w*.82); sy=rng.uniform(h*.22,h*.63)
        tq=i/84
        tx=lerp(cx-w*.26,cx+w*.26,tq)
        taper=math.sin(tq*math.pi)**.65
        ty=cy+(1 if i%2 else -1)*h*.09*taper
        x=lerp(sx,tx,q); y=lerp(sy,ty,q)
        cell(d,x,y,5,mix(CRIMSON,GREEN,q),160,False)
    seal(im,"THE COLLECTIVE BEHAVES AS THOUGH IT KNOWS WHAT IS MISSING","the target is enacted, not stored as a tiny picture")

def visual_genome_gap(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.20,h*.42); right=(w*.80,h*.42)
    # DNA
    for i in range(100):
        q=i/99; y=lerp(h*.23,h*.61,q)
        x1=left[0]+math.sin(q*math.tau*3)*35; x2=left[0]-math.sin(q*math.tau*3)*35
        d.ellipse((x1-3,y-3,x1+3,y+3),fill=(*VIOLET,180)); d.ellipse((x2-3,y-3,x2+3,y+3),fill=(*CYAN,180))
        if i%10==0:d.line((x1,y,x2,y),fill=(*SILVER,120),width=2)
    planarian_outline(d,right[0],right[1],w*.24,h*.11,GOLD,170,4)
    # distributed bridge
    q=ease(u)
    for j in range(7):
        y=h*(.24+j*.06)
        glow_line(im,partial_polyline([(left[0]+45,y),(w*.5,h*.42),(right[0]-110,y)],q),mix(CYAN,GOLD,j/6),2,7,130)
    seal(im,"A LIST OF PARTS DOES NOT EXPLAIN WHEN THE WHOLE IS COMPLETE","between genome and body, a problem is being solved")

def visual_bioelectric_language(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    body_map(im,t*.12,95)
    pts=tissue_points(w,h)
    for x,y,i,j in pts:
        v=.5+.5*math.sin(i*.52+j*.65+t*.28)
        cell(d,x,y,10,mix(CYAN,VIOLET,v),190,False)
        if i<13:d.line((x+10,y,x+w*.76/13-10,y),fill=(*CYAN,70),width=2)
    seal(im,"ELECTRICITY BECOMES A LANGUAGE OF ANATOMY","ordinary cellular machinery negotiates the body it belongs to")

def visual_two_head_memory(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.42); right=(w*.70,h*.42)
    planarian_outline(d,*left,w*.30,h*.13,GREEN,190,4,1)
    planarian_outline(d,*right,w*.30,h*.13,CRIMSON,190,4,2)
    q=ease(u)
    # same genome bridge
    d.line((w*.40,h*.42,w*.60,h*.42),fill=(*VIOLET,150),width=4)
    centered_text(d,(w*.5,h*.35),"SAME GENOME",load_font(FONT_SANS_BOLD,int(h*.016)),VIOLET)
    glow_circle(im,right[0],right[1],25+30*q,CRIMSON,120,13)
    seal(im,"THE TISSUE CAN REMEMBER A DIFFERENT ANSWER","how many heads should this body have?")

def visual_goal_horizons(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    levels=[("BACTERIUM",45,CYAN),("TISSUE",85,GREEN),("ANIMAL",135,GOLD),("HUMAN",195,VIOLET)]
    cx,cy=w*.5,h*.42
    for i,(txt,r,col) in enumerate(levels):
        q=smoothstep(i*.12,.62+i*.07,u)
        d.ellipse((cx-r*q,cy-r*.62*q,cx+r*q,cy+r*.62*q),outline=(*col,int(185*q)),width=4)
        if q>.66:centered_text(d,(cx,cy-r*.62*q-17),txt,load_font(FONT_SANS_BOLD,int(h*.013)),col)
    seal(im,"THE BOUNDARIES OF AGENCY SCALE","competence is measured by the problem space a system can navigate")

def visual_shaiva_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.28,h*.42); right=(w*.72,h*.42)
    # science nesting
    for r,col in [(55,CYAN),(90,GREEN),(130,GOLD)]:
        d.ellipse((left[0]-r,left[1]-r*.62,left[0]+r,left[1]+r*.62),outline=(*col,160),width=4)
    centered_text(d,(left[0],h*.67),"BASAL COGNITION",load_font(FONT_SANS_BOLD,int(h*.015)),CYAN)
    # contraction aperture
    for r,col in [(130,GOLD),(90,VIOLET),(55,CRIMSON)]:
        d.ellipse((right[0]-r,right[1]-r*.62,right[0]+r,right[1]+r*.62),outline=(*col,150),width=4)
    centered_text(d,(right[0],h*.67),"ŚAIVA CONTRACTION",load_font(FONT_SANS_BOLD,int(h*.015)),VIOLET)
    q=smoothstep(.35,.9,u)
    d.line((w*.49,h*.25,w*.51,h*.57),fill=(*CRIMSON,int(210*q)),width=6)
    seal(im,"RESEMBLANCE IS NOT IDENTITY","experiments do not demonstrate Śiva; metaphysics does not predict ion channels")

def visual_distributed_controller(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    pts=tissue_points(w,h,10,6)
    for x,y,i,j in pts:cell(d,x,y,9,mix(CYAN,GREEN,i/9),180,False)
    # no center; distributed loops
    q=ease(u)
    for k in range(7):
        a=k*math.tau/7
        x=cx+math.cos(a)*w*.25; y=cy+math.sin(a)*h*.20
        glow_line(im,partial_polyline([(cx,cy),(x,y),(cx,cy)],q),GOLD,2,8,120)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),outline=(*CRIMSON,120),width=3)
    d.line((cx-28,cy-28,cx+28,cy+28),fill=(*CRIMSON,180),width=4)
    d.line((cx-28,cy+28,cx+28,cy-28),fill=(*CRIMSON,180),width=4)
    seal(im,"SOME SYSTEMS GOVERN THROUGH RELATIONSHIPS, NOT RULERS","the pattern controls by being enacted across the network")

def visual_political_cells(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rng=random.Random(17); nodes=[]
    for i in range(60):
        a=rng.random()*math.tau; rr=math.sqrt(rng.random())
        x=w*.5+math.cos(a)*w*.28*rr; y=h*.42+math.sin(a)*h*.23*rr
        nodes.append((x,y))
    for i,a in enumerate(nodes):
        for step in (3,9):
            b=nodes[(i+step)%len(nodes)]
            d.line((*a,*b),fill=(*CYAN,50),width=2)
    for i,(x,y) in enumerate(nodes):cell(d,x,y,7,mix(CYAN,GREEN,i/60),160,False)
    d.ellipse((w*.18,h*.14,w*.82,h*.70),outline=(*GOLD,140),width=5)
    seal(im,"ORGANISMIC UNITY IS AN ACHIEVEMENT","a political order of living agents with partial information")

def visual_contracted_self(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    # hand/fist aperture
    q=ease(u)
    for i in range(5):
        a=-1.1+i*.55
        length=150
        x1=cx+math.cos(a)*length; y1=cy+math.sin(a)*length*.75
        x2=lerp(x1,cx+math.cos(a)*65,q); y2=lerp(y1,cy+math.sin(a)*50,q)
        d.line((cx,cy,x2,y2),fill=(*VIOLET,180),width=16)
    glow_circle(im,cx,cy,18,GOLD,130,11)
    seal(im,"AGENCY REQUIRES LIMITATION","a goal excludes most possible futures in favor of a narrow region of success")

def visual_preference_asymmetry(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    options=[("HEAD HERE",GOLD,w*.22),("TAIL THERE",CYAN,w*.42),("INTEGRITY",GREEN,w*.62),("INDEFINITE GROWTH",CRIMSON,w*.82)]
    for i,(txt,col,x) in enumerate(options):
        q=smoothstep(i*.1,.62+i*.06,u)
        d.rounded_rectangle((x-85*q,h*.38-30*q,x+85*q,h*.38+30*q),radius=16,fill=(*mix(WHITE,col,.14),int(220*q)),outline=(*col,int(180*q)),width=3)
        if q>.65:centered_text(d,(x,h*.38),txt,load_font(FONT_SANS_BOLD,int(h*.012)),col)
    arrow(d,(w*.22,h*.58),(w*.62,h*.58),GREEN,5,13)
    d.line((w*.73,h*.56,w*.91,h*.60),fill=(*CRIMSON,180),width=5)
    seal(im,"INTELLIGENCE REQUIRES ASYMMETRY","this state, not that one")

def visual_morphospace(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    # axes
    d.line((w*.14,h*.66,w*.86,h*.66),fill=(*PALE_SILVER,150),width=3)
    d.line((w*.14,h*.66,w*.14,h*.16),fill=(*PALE_SILVER,150),width=3)
    labels=["POLARITY","PROPORTION","HEADS","ORGAN POSITION"]
    for i,txt in enumerate(labels):
        x=w*(.20+i*.18); centered_text(d,(x,h*.71),txt,load_font(FONT_SANS_BOLD,int(h*.011)),PALE_SILVER)
    # landscape
    for r,col in [(230,CRIMSON),(160,VIOLET),(95,GOLD),(35,GREEN)]:
        d.ellipse((w*.62-r,h*.39-r*.55,w*.62+r,h*.39+r*.55),outline=(*col,100),width=4)
    q=ease(u)
    path=[(w*.22,h*.55),(w*.35,h*.32),(w*.48,h*.50),(w*.62,h*.39)]
    glow_line(im,partial_polyline(path,q),GOLD,6,14,220)
    glow_circle(im,*path[-1],16,GREEN,180,10)
    seal(im,"MORPHOGENESIS IS NAVIGATION","the body occupies a position in a space of possible forms",WHITE,True)

def visual_map_types(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.28,h*.42); right=(w*.72,h*.42)
    # morphospace axes
    d.line((left[0]-110,left[1]+70,left[0]+110,left[1]+70),fill=(*CYAN,170),width=3)
    d.line((left[0]-110,left[1]+70,left[0]-110,left[1]-90),fill=(*CYAN,170),width=3)
    d.ellipse((left[0]-30,left[1]-15,left[0]+30,left[1]+15),outline=(*GOLD,180),width=4)
    centered_text(d,(left[0],h*.66),"MORPHOSPACE",load_font(FONT_SANS_BOLD,int(h*.015)),CYAN)
    # tattva cascade
    for i in range(6):
        r=120-i*18
        d.ellipse((right[0]-r,right[1]-r*.62,right[0]+r,right[1]+r*.62),outline=(*mix(GOLD,VIOLET,i/5),150),width=3)
    centered_text(d,(right[0],h*.66),"TATTVIC SPACE",load_font(FONT_SANS_BOLD,int(h*.015)),VIOLET)
    q=smoothstep(.35,.9,u)
    d.line((w*.49,h*.24,w*.51,h*.58),fill=(*CRIMSON,int(210*q)),width=6)
    seal(im,"DO NOT CONFUSE MAP TYPES","one models measurable forms; the other maps metaphysical manifestation")

def visual_target_sources(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    sources=[("EVOLUTION",GREEN),("GENETICS",VIOLET),("PHYSICS",INK),("BIOELECTRICITY",CYAN),("ENVIRONMENT",GOLD)]
    cx,cy=w*.5,h*.42
    for i,(txt,col) in enumerate(sources):
        a=-math.pi/2+i*math.tau/5
        x=cx+math.cos(a)*w*.28; y=cy+math.sin(a)*h*.25
        q=smoothstep(i*.1,.62+i*.06,u)
        d.rounded_rectangle((x-90*q,y-24*q,x+90*q,y+24*q),radius=14,fill=(*mix(WHITE,col,.14),int(220*q)),outline=(*col,int(180*q)),width=2)
        if q>.65:centered_text(d,(x,y),txt,load_font(FONT_SANS_BOLD,int(h*.012)),col)
        d.line((x,y,cx,cy),fill=(*col,int(120*q)),width=2)
    planarian_outline(d,cx,cy,w*.18,h*.07,GOLD,170,4)
    seal(im,"NO LITTLE SELF MUST IMAGINE THE FINISHED BODY","goal-directedness can emerge from organization")

def visual_bridge_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.26,h*.42); right=(w*.74,h*.42)
    d.rounded_rectangle((left[0]-150,left[1]-95,left[0]+150,left[1]+95),radius=20,fill=(*PALE_CYAN,220),outline=(*CYAN,180),width=3)
    centered_text(d,(left[0],left[1]),"BIOELECTRIC\nPATTERN MEMORY",load_font(FONT_SANS_BOLD,int(h*.018)),CYAN)
    d.rounded_rectangle((right[0]-150,right[1]-95,right[0]+150,right[1]+95),radius=20,fill=(*PALE_VIOLET,210),outline=(*VIOLET,180),width=3)
    centered_text(d,(right[0],right[1]),"RECOGNITION\nPHILOSOPHY",load_font(FONT_SANS_BOLD,int(h*.018)),VIOLET)
    d.arc((w*.40,h*.22,w*.60,h*.62),200,340,fill=(*GOLD,170),width=5)
    centered_text(d,(w*.5,h*.66),"GOOD BRIDGE · RIVER PRESERVED",load_font(FONT_SANS_BOLD,int(h*.014)),GOLD)
    seal(im,"DO NOT USE ONE AS PROOF OF THE OTHER","functional memory and phenomenal consciousness remain distinct")

def visual_quiet_maintenance(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    body_map(im,t*.12,70)
    acts=[("WOUND CLOSURE",GREEN,w*.22),("TURNOVER",CYAN,w*.42),("ORGAN FORM",GOLD,w*.62),("METABOLIC REPAIR",VIOLET,w*.82)]
    for i,(txt,col,x) in enumerate(acts):
        q=smoothstep(i*.1,.62+i*.06,u)
        d.ellipse((x-45*q,h*.40-45*q,x+45*q,h*.40+45*q),fill=(*mix(WHITE,col,.15),int(220*q)),outline=(*col,int(180*q)),width=3)
        if q>.65:centered_text(d,(x,h*.58),txt,load_font(FONT_SANS_BOLD,int(h*.012)),col)
    seal(im,"YOU ARE A NEGOTIATED PERSISTENCE ACROSS CHANGE","the agency sustaining your body is larger than the voice in your head")

def visual_final_question(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    # fragment
    planarian_outline(d,w*.24,h*.42,w*.22,h*.10,CRIMSON,170,4)
    # target body
    planarian_outline(d,w*.72,h*.42,w*.34,h*.14,GOLD,150,4)
    # distributed cells travel
    for i in range(26):
        a=i*math.tau/26
        sx=w*.24+math.cos(a)*70; sy=h*.42+math.sin(a)*45
        tq=i/25
        tx=lerp(w*.55,w*.88,tq); ty=h*.42+math.sin(tq*math.pi)*h*.07*(1 if i%2 else -1)
        x=lerp(sx,tx,q); y=lerp(sy,ty,q)
        cell(d,x,y,5,mix(CYAN,GREEN,q),160,False)
    glow_line(im,partial_polyline([(w*.34,h*.42),(w*.50,h*.30),(w*.62,h*.42)],q),GOLD,5,13,200)
    seal(im,"YOUR CELLS MAY BE SOLVING A PROBLEM CALLED YOU","the whole is present as a goal they learn to enact together",GREEN)

VISUALS:dict[str,Callable]={
    "cut":visual_cut_regenerate,
    "target":visual_target_ahead,
    "genome":visual_genome_gap,
    "bioelectric":visual_bioelectric_language,
    "twohead":visual_two_head_memory,
    "horizons":visual_goal_horizons,
    "shaiva":visual_shaiva_bridge,
    "distributed":visual_distributed_controller,
    "political":visual_political_cells,
    "contract":visual_contracted_self,
    "preference":visual_preference_asymmetry,
    "morphospace":visual_morphospace,
    "maps":visual_map_types,
    "sources":visual_target_sources,
    "bridge":visual_bridge_caution,
    "maintenance":visual_quiet_maintenance,
    "final":visual_final_question,
}

SCENES:list[Scene]=[
    Scene("Cut planarian","Cut a planarian flatworm into pieces.",6.0,"cut",{}),
    Scene("Not just closure","The fragments do not merely close their wounds.",6.0,"cut",{}),
    Scene("Restore structure","They rebuild missing structures, proportion, and stop when complete.",8.5,"target",{}),
    Scene("No original view","Cells at the wound did not see the original animal.",6.5,"target",{}),
    Scene("No tiny blueprint","They do not contain a tiny anatomical blueprint in each nucleus.",8.0,"genome",{}),
    Scene("Collective knows","Yet the collective behaves as though it knows what shape is missing.",8.0,"target",{}),
    Scene("Problem solved","Somewhere between genome and finished body, a problem is being solved.",8.0,"genome",{}),

    Scene("Genetic execution","Development is often narrated as genetic execution.",6.5,"genome",{}),
    Scene("DNA instructions","DNA contains instructions. Cells read them. A body is assembled.",8.0,"genome",{}),
    Scene("True and misleading","This is true at one level and misleading at another.",7.0,"genome",{}),
    Scene("Same genome outcomes","The same genome can participate in different anatomical outcomes.",8.0,"twohead",{}),
    Scene("Interpret and coordinate","Cells interpret signals, communicate, correct errors, and coordinate growth.",9.0,"bioelectric",{}),
    Scene("Parts not completion","A parts list does not explain how parts know when the whole is complete.",8.0,"genome",{}),
    Scene("Target morphology","What stores target morphology?",5.5,"target",{}),
    Scene("Detect deviation","How do cells detect deviation from it?",5.5,"target",{}),
    Scene("Reduce error","How do they act until the error is reduced?",5.5,"target",{}),

    Scene("Bioelectric medium","One important medium is bioelectricity.",6.0,"bioelectric",{}),
    Scene("Every cell voltage","Every cell maintains membrane voltage through channels and pumps.",8.0,"bioelectric",{}),
    Scene("Non-neural signaling","Non-neural cells exchange electrical information through gap junctions.",8.0,"bioelectric",{}),
    Scene("Voltage patterns","Across tissues, voltages form patterns.",6.5,"bioelectric",{}),
    Scene("Pattern interactions","Patterns interact with gene expression, proliferation, migration, and differentiation.",9.0,"bioelectric",{}),
    Scene("Not ghostly","Bioelectric states are physiological, not ghostly fields beyond chemistry.",8.0,"bioelectric",{}),
    Scene("Anatomical information","Their large-scale organization may carry anatomical information.",7.5,"bioelectric",{}),
    Scene("Language","Electricity becomes a language through which cells negotiate a body.",8.5,"bioelectric",{}),

    Scene("Planarian rewrite","Briefly altering electrical communication can produce two-headed regeneration.",9.0,"twohead",{}),
    Scene("Persistent anatomy","The altered anatomy can persist through later regeneration after treatment ends.",9.0,"twohead",{}),
    Scene("Genome unchanged","The genome remains ordinary while the regenerative outcome changes.",8.0,"twohead",{}),
    Scene("Pattern memory","Researchers describe rewriteable pattern memory in bioelectric networks.",8.0,"twohead",{}),
    Scene("How many heads","The tissue remembers a different answer: how many heads should this body have?",8.5,"twohead",{}),

    Scene("Functional memory","Memory here is not necessarily conscious recollection.",7.0,"horizons",{}),
    Scene("Stable target","A network can maintain a target state, compare conditions, and restore it.",8.5,"horizons",{}),
    Scene("Continuum cognition","The provocative move places memory, preference, error correction, and goals on a continuum.",9.5,"horizons",{}),
    Scene("Earlier than neurons","Perhaps nervous systems amplified an older capacity to navigate problem spaces.",9.0,"horizons",{}),

    Scene("Basal cognition","This framework is called basal cognition or diverse intelligence.",7.0,"horizons",{}),
    Scene("Not tiny humans","The claim is not that every cell thinks like a tiny human.",7.0,"horizons",{}),
    Scene("Competency definition","Intelligence can be defined by competencies rather than resemblance to us.",8.0,"horizons",{}),
    Scene("Goals and perturbation","Can a system pursue goals, integrate information, and adapt when perturbed?",9.0,"horizons",{}),
    Scene("Goal horizons","A bacterium, tissue, animal, and human occupy different goal horizons.",8.5,"horizons",{}),
    Scene("Agency scales","The boundaries of agency scale.",6.5,"horizons",{}),

    Scene("Science meets philosophy","This is where science begins to touch philosophy.",7.0,"shaiva",{}),
    Scene("Śaiva contraction","Kashmir Śaivism describes universal capacities contracting into finite centers.",8.5,"shaiva",{}),
    Scene("Kala vidya","Infinite agency becomes kalā; infinite knowledge becomes vidyā.",8.0,"shaiva",{}),
    Scene("Scale resemblance","Cells, tissues, organisms, and communities show a striking scale resemblance.",8.5,"shaiva",{}),
    Scene("Not identity","But resemblance is not identity.",6.0,"shaiva",{}),
    Scene("No Shiva proof","Levin's experiments do not demonstrate Śiva.",7.0,"shaiva",{}),
    Scene("No ion prediction","Tantric metaphysics does not predict ion-channel interventions.",7.5,"shaiva",{}),
    Scene("Preserve difference","The bridge must preserve empirical and ontological difference.",8.0,"bridge",{}),

    Scene("Agency beyond ego","Both frameworks resist the idea that agency belongs only to the human ego.",8.0,"shaiva",{}),
    Scene("Different foundations","One begins with consciousness; the other studies observable competencies.",8.5,"shaiva",{}),
    Scene("Where goals live","They meet at the question of where goals live.",7.0,"distributed",{}),

    Scene("No central architect","No single planarian cell contains the whole target like an architect's plan.",8.5,"distributed",{}),
    Scene("Distributed goal","The goal is distributed across interactions.",6.5,"distributed",{}),
    Scene("Signals stabilize","Cells exchange signals and local states stabilize larger patterns.",8.0,"distributed",{}),
    Scene("Collective repair","The collective detects anatomical error and coordinates repair.",8.0,"distributed",{}),
    Scene("Search controller","We search for the controller: brain, gene, command center.",8.0,"distributed",{}),
    Scene("Relational governance","Some systems govern through relationships rather than rulers.",8.0,"distributed",{}),
    Scene("Pattern enacted","The pattern controls by being enacted across the network.",7.5,"distributed",{}),

    Scene("Identity field","Pratyabhijñā treats identity as relationally manifested.",7.5,"political",{}),
    Scene("Subject object act","Consciousness appears as subject, object, and connecting act.",8.0,"political",{}),
    Scene("Trillions of agents","The body contains trillions of living agents with partial information.",8.0,"political",{}),
    Scene("What makes one","What makes them one organism?",6.0,"political",{}),
    Scene("Not genes alone","Not genetic sameness alone.",5.5,"political",{}),
    Scene("Not contact alone","Not spatial contact alone.",5.5,"political",{}),
    Scene("Unity achievement","Organismic unity is an achievement—a political order of cells.",8.0,"political",{}),

    Scene("Cancer revealing","Cancer becomes revealing in this vocabulary.",6.5,"political",{}),
    Scene("Local goals","Cancer cells pursue local goals while losing integration with the collective.",8.5,"political",{}),
    Scene("Self shrinks","The scale of the self shrinks.",6.0,"contract",{}),
    Scene("Lineage as whole","A cell behaves as though its local lineage were the whole organism.",8.0,"contract",{}),
    Scene("Systems claim","Pathology can emerge when competent subunits abandon larger goals.",8.5,"political",{}),
    Scene("No moral claim","This is not a moral claim about disease.",6.5,"bridge",{}),

    Scene("Bondage analogy","Śaivism describes bondage through contraction of identity.",7.0,"contract",{}),
    Scene("Only this body","I am only this body. My knowledge ends here. My good is separate.",8.5,"contract",{}),
    Scene("Structural analogy","The comparison is structural, not causal.",6.5,"bridge",{}),
    Scene("Not spiritual egoism","Cancer is not spiritual egoism; realization is not treatment.",8.0,"bridge",{}),
    Scene("Boundary changes behavior","What counts as me changes error, threat, repair, and success.",8.5,"contract",{}),

    Scene("Agent boundaries","How are the boundaries of an agent constructed?",7.0,"horizons",{}),
    Scene("Membrane boundary","A cell membrane creates one boundary.",6.0,"horizons",{}),
    Scene("Electrical networks","Electrical coupling joins cells into larger computational networks.",8.0,"bioelectric",{}),
    Scene("Nervous integration","Nervous systems bind organism-level control.",7.0,"horizons",{}),
    Scene("Culture extension","Language and culture extend goals across generations.",7.5,"horizons",{}),
    Scene("Self built","A self is not only found. It is built.",7.0,"contract",{}),
    Scene("Reorganized","What is built can be widened, narrowed, damaged, or reorganized.",8.0,"contract",{}),

    Scene("Samkoca","Saṃkoca means contraction.",5.5,"contract",{}),
    Scene("Power local","Universal power does not disappear; it becomes local.",7.0,"contract",{}),
    Scene("Fist image","A hand closes into a fist and compresses possible movement.",7.5,"contract",{}),
    Scene("Biological constraints","Membrane, body plan, nervous system, and goal create biological limitation.",9.0,"contract",{}),
    Scene("Agency limitation","Agency requires limitation.",6.5,"contract",{}),
    Scene("Every future none","A system pursuing every possible future would pursue nothing.",7.5,"preference",{}),

    Scene("Reversal","Limitation is not the opposite of intelligence.",6.5,"preference",{}),
    Scene("Condition","It is one of intelligence's conditions.",6.0,"preference",{}),
    Scene("Preferred states","A system must distinguish preferred from nonpreferred states.",8.0,"preference",{}),
    Scene("Functional preference","Planarian preference is shorthand for robust goal-directed behavior.",8.0,"preference",{}),
    Scene("Human felt value","Human preference includes felt value; the two should not collapse.",8.0,"preference",{}),
    Scene("Both asymmetric","Both require asymmetry: this state, not that one.",7.0,"preference",{}),
    Scene("Head tail integrity","A head here, a tail there, integrity rather than indefinite growth.",8.0,"preference",{}),

    Scene("Morphospace","Morphospace is an abstract space of possible anatomical configurations.",8.0,"morphospace",{}),
    Scene("Navigate form","Cells and tissues navigate it during development and regeneration.",8.0,"morphospace",{}),
    Scene("Injury displacement","Injury moves the body away from its target region.",7.0,"morphospace",{}),
    Scene("Repair distance","Repair processes reduce the distance.",6.5,"morphospace",{}),
    Scene("Shape axes","The axes are limbs, polarity, proportion, and organ placement.",8.5,"morphospace",{}),
    Scene("Form position","The body occupies a position in a space of possible forms.",7.5,"morphospace",{}),
    Scene("Navigation","Morphogenesis is navigation.",6.0,"morphospace",{}),

    Scene("Tattva analogy","Tantric cosmology also maps movement through structured possibility.",8.0,"maps",{}),
    Scene("Contraction sequence","Tattvas describe undivided capacity becoming increasingly specific form.",8.5,"maps",{}),
    Scene("Hidden dimensions","Both require a landscape beyond ordinary geography.",7.5,"maps",{}),
    Scene("Morphospace tattvic","Morphospace models form; tattvic space models modes of manifestation.",8.5,"maps",{}),
    Scene("Useful analogy","The analogy is useful because visible form is an endpoint of hidden organization.",8.5,"maps",{}),
    Scene("Map break","The analogy breaks because the map types differ.",7.0,"maps",{}),
    Scene("Do not confuse","Do not confuse map types.",6.0,"maps",{}),

    Scene("Target origin","Where does the target come from?",6.0,"sources",{}),
    Scene("Several answers","Evolution, genetics, physics, bioelectricity, and environment may all contribute.",9.0,"sources",{}),
    Scene("No little self","No little self inside the organism must imagine the completed body.",8.0,"sources",{}),
    Scene("Emergent goal","Goal-directedness can emerge from organization.",7.0,"sources",{}),
    Scene("Svatantrya","Śaivism answers metaphysically through svātantrya, freedom of manifestation.",8.0,"shaiva",{}),
    Scene("Different answers","Science operationalizes the question without settling ontology.",8.0,"bridge",{}),

    Scene("Proof temptation","Using Levin's work as proof of ancient idealism would weaken both.",8.0,"bridge",{}),
    Scene("Memory not consciousness","Pattern memory does not establish fundamental consciousness.",8.0,"bridge",{}),
    Scene("Goals not human awareness","Distributed correction does not show humanlike cellular awareness.",8.0,"bridge",{}),
    Scene("Shaivism not systems biology","Śaivism is not merely early systems biology.",7.5,"bridge",{}),
    Scene("Good bridge","A good bridge carries traffic while preserving the river beneath it.",8.0,"bridge",{}),

    Scene("Science pressure","The science gives philosophy pressure.",6.5,"horizons",{}),
    Scene("Human monopoly","It makes the human monopoly on intelligence harder to defend.",8.0,"horizons",{}),
    Scene("Non-neural memory","Memory-like dynamics occur in non-neural tissue.",7.0,"bioelectric",{}),
    Scene("Collective bodies","Bodies are collectives negotiating large-scale form.",7.5,"political",{}),
    Scene("Problem question","Ask what problems a system solves, across what scale and flexibility.",9.0,"horizons",{}),
    Scene("Competencies everywhere","The world becomes populated by competencies, not necessarily conscious minds.",9.0,"horizons",{}),

    Scene("Philosophy contribution","Philosophy offers a vocabulary of scale and contraction.",7.0,"shaiva",{}),
    Scene("Observer bias","It warns that our categories privilege one familiar center.",7.5,"shaiva",{}),
    Scene("Goal horizon subjectivity","It asks whether larger goal horizons alter subjectivity.",8.0,"shaiva",{}),
    Scene("Conceptual provocation","These are conceptual provocations, not experimental results.",8.0,"bridge",{}),

    Scene("Return fragment","Return to the planarian fragment.",6.0,"cut",{}),
    Scene("Injury signals","Cells encounter injury signals.",5.5,"bioelectric",{}),
    Scene("Electrical shift","Electrical patterns shift.",5.5,"bioelectric",{}),
    Scene("Genes change","Genes change expression.",5.5,"genome",{}),
    Scene("Stem cells","Stem cells proliferate.",5.5,"target",{}),
    Scene("Tissue reorganizes","Tissues reorganize.",6.0,"target",{}),
    Scene("Head needed","A head appears where a head is needed.",6.5,"target",{}),
    Scene("Stop proportion","Growth stops when proportion is restored.",6.5,"target",{}),
    Scene("Not printer","The process does not resemble a blueprint mechanically printed.",8.0,"genome",{}),
    Scene("Collective correction","It resembles a collective correcting position in a space of possible bodies.",9.0,"morphospace",{}),

    Scene("Quiet versions","Your body performs quieter versions continuously.",7.0,"maintenance",{}),
    Scene("Wounds close","Wounds close.",5.0,"maintenance",{}),
    Scene("Turnover","Cells die and are replaced.",5.5,"maintenance",{}),
    Scene("Organs persist","Organs preserve structure through molecular turnover.",7.0,"maintenance",{}),
    Scene("Metabolic repair","Metabolism repairs deviations.",6.0,"maintenance",{}),
    Scene("Negotiated persistence","The body is negotiated persistence across change.",7.5,"maintenance",{}),
    Scene("Larger agency","The you solving the body is larger than the voice in your head.",8.5,"maintenance",{}),

    Scene("Śaiva further","Śaivism pushes further.",5.5,"shaiva",{}),
    Scene("Consciousness larger","Consciousness is also larger than the voice in your head.",7.5,"shaiva",{}),
    Scene("Ego report","The ego is one local report issued by a deeper field.",7.0,"shaiva",{}),
    Scene("Recognition","Recognition finds that knowing and action did not originate inside the defended boundary.",9.0,"shaiva",{}),
    Scene("No reduction","Cells do not become human; humans do not become merely colonies.",8.0,"bridge",{}),
    Scene("Layered agency","Agency is layered. Identity is nested.",7.0,"horizons",{}),

    Scene("Animal question","Cut a planarian and the animal becomes a question distributed across wounds.",9.0,"final",{}),
    Scene("What shape","What shape belongs here? The cells answer together.",7.5,"final",{}),
    Scene("Human loss","A human life cut by loss or transition faces another uncertain target.",8.5,"final",{}),
    Scene("Wholeness","Philosophy asks what counts as wholeness.",6.5,"final",{}),
    Scene("Not previous shape","The answer may not be a return to the previous shape.",7.0,"final",{}),
    Scene("Identity changes","Living systems preserve identity partly by changing it.",7.5,"final",{}),
    Scene("Problem called you","Your cells may be solving a problem called you.",8.0,"final",{}),
    Scene("Not biography","Not your biography or ambitions, but the coherence making biography possible.",8.5,"final",{}),
    Scene("Larger field","The person called I may solve another problem inside a larger field.",8.0,"final",{}),
    Scene("Two memories","The worm remembers a body; recognition philosophy remembers a field.",8.5,"bridge",{}),
    Scene("Shared disturbance","The whole may be present in parts as a goal they learn to enact together.",9.0,"final",{}),
]

def render_frame(scene,frame_index,frame_count,width,height,seed):
    u=frame_index/max(1,frame_count-1); t=u*scene.duration
    dark=scene.visual=="morphospace"
    im=background(width,height,seed,dark)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im,dark)
    return im.convert("RGB")

def require_ffmpeg():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg is required but was not found on PATH")
    return exe
def encode_scene(scene_index,fps):
    ffmpeg=require_ffmpeg(); frame_dir=FRAMES/f"scene_{scene_index:03d}"
    out=SCENES_DIR/f"scene_{scene_index:03d}.mp4"
    cmd=[ffmpeg,"-y","-framerate",str(fps),"-i",str(frame_dir/"%05d.jpg"),
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(out)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out
def render_scene(scene_index,scene,fps,width,height,preview):
    frame_dir=FRAMES/f"scene_{scene_index:03d}"
    frame_dir.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    fc=max(2,round(scene.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(fc*.35),int(fc*.72),fc-1]):
            render_frame(scene,fi,fc,width,height,scene_index*1000+fi).save(frame_dir/f"preview_{oi:02d}.jpg",quality=95)
        return frame_dir
    for fi in range(fc):
        p=frame_dir/f"{fi:05d}.jpg"
        if p.exists(): continue
        render_frame(scene,fi,fc,width,height,scene_index*1000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(scene_index,fps)
def concatenate(paths):
    ffmpeg=require_ffmpeg(); c=OUTPUT/"concat.txt"
    c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    out=OUTPUT/"your_cells_may_be_solving_a_problem_called_you.mp4"
    subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out
def export_timeline():
    cursor=0; payload=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3); r["end_seconds"]=round(cursor+s.duration,3)
        payload.append(r); cursor+=s.duration
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({
        "title":"your cells may be solving a problem called you",
        "runtime_seconds":round(cursor,3),
        "scene_count":len(SCENES),
        "style":{
            "continuity_object":"gold target-form silhouette in morphospace",
            "shot_duration_range_seconds":[5,10],
            "palette_roles":{
                "gold":"target morphology",
                "cyan":"bioelectric communication",
                "green":"successful regeneration",
                "crimson":"anatomical error",
                "violet":"gene expression and conceptual interpretation",
                "graphite":"physical anatomy and wound"
            }
        },
        "scenes":payload
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def make_contact_sheet(width,height):
    tw=320; th=int(tw*height/width); thumbs=[]
    for i,s in enumerate(SCENES,1):
        fc=max(2,round(s.duration*DEFAULT_FPS))
        im=render_frame(s,int(fc*.72),fc,width,height,i*1000+72)
        im.thumbnail((tw,th)); thumbs.append((i,s.title,im.copy()))
    cols=4; rows=math.ceil(len(thumbs)/cols); cell_h=th+52
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),WHITE); d=ImageDraw.Draw(sheet)
    font=load_font(FONT_SANS_BOLD,15)
    for idx,title,im in thumbs:
        slot=idx-1; x=(slot%cols)*tw; y=(slot//cols)*cell_h
        sheet.paste(im,(x,y)); d.text((x+10,y+th+8),f"{idx:03d}  {title}",font=font,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; sheet.save(p,quality=94); return p
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
    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if args.scene is not None:
        if not 1<=args.scene<=len(SCENES): raise ValueError(f"--scene must be between 1 and {len(SCENES)}")
        print(render_scene(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:03d}/{len(SCENES):03d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,args.fps,args.width,args.height,args.preview)
        if not args.preview: rendered.append(r)
    if not args.no_contact_sheet: print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview: print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
