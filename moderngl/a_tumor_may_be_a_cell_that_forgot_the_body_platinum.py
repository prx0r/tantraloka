#!/usr/bin/env python3
"""
A TUMOR MAY BE A CELL THAT FORGOT THE BODY
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/02_a_tumor_may_be_a_cell_that_forgot_the_body.md

DESIGN CONTRACT
---------------
• Every shot lasts 5–10 seconds.
• Every shot visibly performs the narrated operation.
• Clean white biomedical field; deep field only for attractor landscapes.
• No static slide layouts and no decorative loops.
• Cyan = tissue-scale bioelectric body-map / collective anatomical memory
• Green = healthy coupling / differentiation / normalization
• Crimson = local runaway goal / depolarized state / malignant attractor
• Gold = causal intervention / experimentally testable perturbation
• Violet = gene regulation / latent cellular possibility
• Graphite = tissue architecture / physical boundary
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: one cyan tissue-scale voltage map persists across chapters.
• Tumor imagery must remain scientific and non-moralizing.
• The final visual should restore conversation, not imply magical cure.

OUTPUT
------
output_tumor_forgot_body/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  a_tumor_may_be_a_cell_that_forgot_the_body.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.

USAGE
-----
python a_tumor_may_be_a_cell_that_forgot_the_body_platinum.py
python a_tumor_may_be_a_cell_that_forgot_the_body_platinum.py --preview
python a_tumor_may_be_a_cell_that_forgot_the_body_platinum.py --scene 8
python a_tumor_may_be_a_cell_that_forgot_the_body_platinum.py --fps 12 --width 1920 --height 1080
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"output_tumor_forgot_body"
FRAMES=OUTPUT/"frames"
SCENES_DIR=OUTPUT/"scenes"

DEFAULT_WIDTH=1280
DEFAULT_HEIGHT=720
DEFAULT_FPS=10

WHITE=(248,247,243); PAPER=(242,239,232); INK=(29,31,35); SOFT_INK=(84,88,94)
SILVER=(177,184,190); PALE_SILVER=(224,227,229)
CYAN=(54,153,181); PALE_CYAN=(192,226,233)
GREEN=(69,139,97); PALE_GREEN=(194,225,206)
CRIMSON=(158,52,66); PALE_CRIMSON=(230,192,198)
GOLD=(194,153,68); PALE_GOLD=(235,218,175)
VIOLET=(104,79,146); PALE_VIOLET=(216,205,232)
LAPIS=(48,72,124); VOID=(22,25,31)

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
    lengths=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]
    total=sum(lengths); target=total*progress; out=[points[0]]; walked=0
    for i,L in enumerate(lengths):
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
def organic_blob(d,cx,cy,rx,ry,color,phase=0,points=100,outline=None):
    pts=[]
    for i in range(points):
        a=math.tau*i/points
        wob=1+.06*math.sin(a*3+phase)+.035*math.sin(a*7-phase*.5)
        pts.append((cx+math.cos(a)*rx*wob,cy+math.sin(a)*ry*wob))
    d.polygon(pts,fill=color,outline=outline); return pts
def cell(d,x,y,r,color,alpha=220,nucleus=True):
    d.ellipse((x-r,y-r,x+r,y+r),fill=(*mix(WHITE,color,.16),alpha),outline=(*color,min(255,alpha+10)),width=3)
    if nucleus:d.ellipse((x-r*.28,y-r*.28,x+r*.28,y+r*.28),fill=(*mix(color,VIOLET,.35),170))
def tissue_grid(w,h,cols=12,rows=7):
    pts=[]
    for j in range(rows):
        for i in range(cols):
            x=w*(.14+i*(.72/(cols-1))); y=h*(.20+j*(.46/(rows-1)))
            pts.append((x,y,i,j))
    return pts
def body_map_lines(im,phase=0,alpha=100):
    w,h=im.size
    for j in range(9):
        pts=[]
        for i in range(160):
            q=i/159
            x=lerp(w*.10,w*.90,q)
            y=h*(.20+j*.055)+math.sin(q*math.tau*2+phase+j*.4)*12
            pts.append((x,y))
        glow_line(im,pts,CYAN,2,7,alpha)

@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict

def visual_local_competence(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    body_map_lines(im,t*.1,65)
    cx,cy=w*.5,h*.42
    # one competent cell branches into local lineage
    q=ease(u)
    positions=[(cx,cy)]
    for ring in range(1,4):
        for k in range(6*ring):
            a=k*math.tau/(6*ring)
            rr=ring*42*q
            positions.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
    for idx,(x,y) in enumerate(positions):
        col=CRIMSON if idx>0 else GOLD
        cell(d,x,y,15+4*(idx==0),col,210)
    # local loop
    d.arc((cx-140*q,cy-140*q,cx+140*q,cy+140*q),0,320,fill=(*CRIMSON,170),width=5)
    seal(im,"THE CELL HAS NOT FORGOTTEN HOW TO LIVE","its competence has narrowed to a smaller future")

def visual_voltage_surface(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    body_map_lines(im,t*.12,90)
    pts=tissue_grid(w,h)
    for x,y,i,j in pts:
        v=.5+.5*math.sin(i*.55+j*.7+t*.25)
        col=mix(CYAN,VIOLET,v)
        cell(d,x,y,13,col,205)
    # gap junctions
    for x,y,i,j in pts:
        if i<11:d.line((x+13,y,x+w*.72/11-13,y),fill=(*CYAN,90),width=2)
        if j<6:d.line((x,y+13,x,y+h*.46/6-13),fill=(*CYAN,90),width=2)
    # one depolarized patch
    q=smoothstep(.35,.9,u)
    for x,y,i,j in pts:
        if (i-7)**2+(j-3)**2<5:
            d.ellipse((x-15,y-15,x+15,y+15),outline=(*CRIMSON,int(180*q)),width=4)
    seal(im,"THE MEMBRANE IS AN ELECTRICAL DECISION SURFACE","cells form tissue-scale voltage networks")

def visual_pre_tumor_state(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=tissue_grid(w,h)
    q=ease(u)
    for x,y,i,j in pts:
        dist=((i-7)**2+(j-3)**2)**.5
        dep=smoothstep(4.5,0,dist)*q
        col=mix(CYAN,CRIMSON,dep)
        cell(d,x,y,14,col,215)
    # oncogene remains gold within one cell
    ox,oy,_,_=pts[3*12+7]
    glow_circle(im,ox,oy,10,GOLD,170,9)
    # invisible state before visible shape
    ring=25+85*smoothstep(.45,.95,u)
    d.ellipse((ox-ring,oy-ring,ox+ring,oy+ring),outline=(*CRIMSON,int(150*q)),width=3)
    seal(im,"VOLTAGE CAN CHANGE BEFORE VISIBLE FORM","genetic signal and physiological context interact")

def visual_distant_signal(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=tissue_grid(w,h)
    for x,y,i,j in pts: cell(d,x,y,12,CYAN,190)
    source=(w*.20,h*.32); target=(w*.76,h*.52)
    glow_circle(im,*source,16,GOLD,180,10)
    path=[]
    for i in range(160):
        q=i/159
        x=lerp(source[0],target[0],q)
        y=lerp(source[1],target[1],q)+math.sin(q*math.tau*3+t*.4)*20
        path.append((x,y))
    glow_line(im,partial_polyline(path,ease(u)),GOLD,4,12,210)
    if u>.65:
        glow_circle(im,*target,24,CRIMSON,170,12)
    seal(im,"DISTANT CELLS CAN ALTER LOCAL BEHAVIOR","the physiological network changes what a cell can become")

def visual_context_switch(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.42); right=(w*.70,h*.42)
    # same genome glyph
    for cx,col,label in [(left,CRIMSON,"DISORDERED CONTEXT"),(right,GREEN,"EMBRYONIC CONTEXT")]:
        cell(d,*cx,95,col,220)
        for i in range(6):
            a=i*math.tau/6
            d.line((cx[0],cx[1],cx[0]+math.cos(a)*62,cx[1]+math.sin(a)*62),fill=(*VIOLET,130),width=3)
        centered_text(d,(cx[0],h*.66),label,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    # context arrows reshape right cell
    q=ease(u)
    for i in range(8):
        a=i*math.tau/8
        sx=right[0]+math.cos(a)*150; sy=right[1]+math.sin(a)*120
        arrow(d,(sx,sy),(right[0]+math.cos(a)*92,right[1]+math.sin(a)*92),GREEN,3,9)
    seal(im,"THE SAME GENOME CAN PARTICIPATE IN DIFFERENT BEHAVIORS","the neighborhood changes what the resident believes is possible")

def visual_tissue_expectations(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cmds=[("DIVIDE HERE",GREEN),("STOP HERE",CRIMSON),("MIGRATE THERE",CYAN),("BECOME THIS",VIOLET),("REPAIR BOUNDARY",GOLD)]
    cx,cy=w*.5,h*.42
    for i,(txt,col) in enumerate(cmds):
        a=-math.pi/2+i*math.tau/5
        x=cx+math.cos(a)*w*.27; y=cy+math.sin(a)*h*.25
        q=smoothstep(i*.10,.62+i*.06,u)
        d.rounded_rectangle((x-105*q,y-24*q,x+105*q,y+24*q),radius=14,
                            fill=(*mix(WHITE,col,.14),int(220*q)),outline=(*col,int(175*q)),width=2)
        if q>.64:centered_text(d,(x,y),txt,load_font(FONT_SANS_BOLD,int(h*.013)),col)
        d.line((cx,cy,x,y),fill=(*col,int(120*q)),width=2)
    cell(d,cx,cy,34,CYAN,220)
    seal(im,"A TISSUE CARRIES EXPECTATIONS IN ITS STRUCTURE","when constraints weaken, local goals can escape")

def visual_traffic_network(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    # road network
    roads=[((w*.12,h*.28),(w*.88,h*.28)),((w*.12,h*.50),(w*.88,h*.50)),((w*.30,h*.18),(w*.30,h*.67)),((w*.62,h*.18),(w*.62,h*.67))]
    for a,b in roads:d.line((*a,*b),fill=(*INK,120),width=7)
    # cars function, network jams
    rng=random.Random(22)
    for i in range(38):
        road=i%4
        q=(i*0.137+u*.2)%1
        if road<2:
            y=roads[road][0][1]; x=lerp(w*.12,w*.88,q)
        else:
            x=roads[road][0][0]; y=lerp(h*.18,h*.67,q)
        jam=abs(x-w*.5)<w*.15 and abs(y-h*.39)<h*.15
        col=CRIMSON if jam else CYAN
        d.rounded_rectangle((x-10,y-6,x+10,y+6),radius=4,fill=(*col,210))
    seal(im,"COMPONENTS CAN WORK WHILE ORGANIZATION FAILS","the disease may exist partly in relations")

def visual_attractor_landscape(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    # dark potential field
    pts=[]
    for i in range(260):
        q=i/259; x=lerp(w*.10,w*.90,q)
        y=h*.68-h*.26*(math.exp(-((q-.28)/.13)**2)+.95*math.exp(-((q-.72)/.12)**2))
        pts.append((x,y))
    d.line(pts,fill=(*PALE_SILVER,190),width=4)
    centered_text(d,(w*.28,h*.30),"HEALTHY ATTRACTOR",load_font(FONT_SANS_BOLD,int(h*.015)),GREEN)
    centered_text(d,(w*.72,h*.30),"TUMOR-SUPPORTING ATTRACTOR",load_font(FONT_SANS_BOLD,int(h*.015)),CRIMSON)
    q=ease(u); idx=min(259,int(q*259)); x,y=pts[idx]
    glow_circle(im,x,y-12,14,GOLD,190,10)
    # intervention shifts basin
    if u>.55:
        arrow(d,(w*.72,h*.53),(w*.38,h*.48),GREEN,5,13)
    seal(im,"NETWORK STATE CAN HAVE MORE THAN ONE STABLE BASIN","normalization means shifting the collective landscape",WHITE,True)

def visual_normalization(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=tissue_grid(w,h)
    q=ease(u)
    for x,y,i,j in pts:
        dist=((i-7)**2+(j-3)**2)**.5
        initial=smoothstep(4.2,0,dist)
        recovered=initial*(1-q)
        col=mix(CYAN,CRIMSON,recovered)
        cell(d,x,y,13,col,210)
    # restore gap junctions
    for x,y,i,j in pts:
        alpha=int(30+150*q)
        if i<11:d.line((x+13,y,x+w*.72/11-13,y),fill=(*GREEN,alpha),width=2)
        if j<6:d.line((x,y+13,x,y+h*.46/6-13),fill=(*GREEN,alpha),width=2)
    seal(im,"RESTORE INSTRUCTIVE CONTEXT","change state, coupling, signaling, and architecture—not only survival")

def visual_overstatement_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.28,h*.42); right=(w*.72,h*.42)
    d.rounded_rectangle((left[0]-150,left[1]-100,left[0]+150,left[1]+100),radius=20,
                        fill=(*PALE_CYAN,220),outline=(*CYAN,180),width=3)
    centered_text(d,(left[0],left[1]-25),"GENES · IMMUNE · METABOLISM",load_font(FONT_SANS_BOLD,int(h*.016)),CYAN)
    centered_text(d,(left[0],left[1]+25),"MICROENVIRONMENT · VOLTAGE",load_font(FONT_SANS_BOLD,int(h*.016)),CYAN)
    claims=["CANCER IS ELECTRICAL","ONE MECHANISM","EASY CURE"]
    fade=smoothstep(.3,.9,u)
    for i,txt in enumerate(claims):
        y=right[1]-65+i*65
        centered_text(d,(right[0],y),txt,load_font(FONT_SERIF_BOLD,int(h*.018)),(*CRIMSON,int(180*(1-.7*fade))))
        d.line((right[0]-130,y,right[0]+130,y),fill=(*CRIMSON,int(220*fade)),width=4)
    seal(im,"THE RESPONSIBLE CLAIM IS NARROWER","bioelectric state is one important control layer among many")

def visual_relational_identity(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    center=(w*.5,h*.42)
    signals=[("GENOME",VIOLET,-210,-95),("NEIGHBORS",CYAN,210,-95),("MATRIX",GOLD,-210,105),("IMMUNE",GREEN,210,105)]
    cell(d,*center,50,CYAN,220)
    for i,(name,col,ox,oy) in enumerate(signals):
        x=center[0]+ox; y=center[1]+oy; q=smoothstep(i*.1,.62+i*.06,u)
        d.rounded_rectangle((x-80*q,y-24*q,x+80*q,y+24*q),radius=14,
                            fill=(*mix(WHITE,col,.14),int(220*q)),outline=(*col,int(175*q)),width=2)
        if q>.65:centered_text(d,(x,y),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
        d.line((x,y,*center),fill=(*col,int(130*q)),width=3)
    seal(im,"WHAT IS THIS CELL?","identity depends on signals, boundaries, and the future behavior preserves")

def visual_scale_sacrifice(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    # organism outline
    d.ellipse((cx-w*.28,cy-h*.25,cx+w*.28,cy+h*.25),outline=(*CYAN,150),width=4)
    rng=random.Random(12)
    for i in range(70):
        a=rng.random()*math.tau; rr=math.sqrt(rng.random())
        x=cx+math.cos(a)*w*.25*rr; y=cy+math.sin(a)*h*.21*rr
        col=GREEN if i%7 else GOLD
        cell(d,x,y,8,col,170,False)
    # one local lineage expands
    q=ease(u); tx,ty=cx+w*.12,cy+h*.02
    for ring in range(3):
        for k in range(6+ring*4):
            a=k*math.tau/(6+ring*4); rr=ring*22*q
            cell(d,tx+math.cos(a)*rr,ty+math.sin(a)*rr,8,CRIMSON,200,False)
    seal(im,"LOCAL SUCCESS CAN BECOME ORGANISM FAILURE","a smaller goal captures the machinery of life")

def visual_non_moralizing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.42); right=(w*.70,h*.42)
    # biology
    for i in range(18):
        a=i*math.tau/18
        x=left[0]+math.cos(a)*80; y=left[1]+math.sin(a)*65
        cell(d,x,y,10,CRIMSON if i%4==0 else CYAN,180,False)
    centered_text(d,(left[0],h*.66),"BIOLOGICAL SYSTEM",load_font(FONT_SANS_BOLD,int(h*.016)),INK)
    # crossed-out blame terms
    terms=["SELFISHNESS","SPIRITUAL FAILURE","DISCONNECTION"]
    q=smoothstep(.25,.9,u)
    for i,txt in enumerate(terms):
        y=right[1]-65+i*65
        centered_text(d,(right[0],y),txt,load_font(FONT_SERIF_BOLD,int(h*.018)),(*CRIMSON,170))
        d.line((right[0]-120,y,right[0]+120,y),fill=(*CRIMSON,int(220*q)),width=4)
    seal(im,"DO NOT TURN SYSTEMS BIOLOGY INTO BLAME","tumors are not moral messages")

def visual_distributed_governance(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    # no throne, only network
    pts=[]
    for i in range(22):
        a=i*math.tau/22; rr=80+(i%3)*55
        pts.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr*.68))
    for i,p1 in enumerate(pts):
        for j in (1,4,7):
            p2=pts[(i+j)%len(pts)]
            d.line((*p1,*p2),fill=(*CYAN,55),width=2)
    for i,(x,y) in enumerate(pts):
        cell(d,x,y,11,mix(GREEN,CYAN,i/len(pts)),190,False)
    glow_circle(im,cx,cy,18,GOLD,120,12)
    seal(im,"NO CENTRAL CELL COMMANDS THE BODY","order is renewed through distributed communication and layered constraints")

def visual_mechanism_list(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    items=[("MEMBRANE POTENTIAL",CYAN),("GAP JUNCTIONS",GREEN),("EXTRACELLULAR SIGNALS",GOLD),
           ("TISSUE ARCHITECTURE",INK),("IMMUNE RECOGNITION",VIOLET),("GENE EXPRESSION",CRIMSON)]
    cx,cy=w*.5,h*.42
    for i,(txt,col) in enumerate(items):
        a=-math.pi/2+i*math.tau/6
        x=cx+math.cos(a)*w*.29; y=cy+math.sin(a)*h*.26
        q=smoothstep(i*.08,.58+i*.06,u)
        d.rounded_rectangle((x-100*q,y-23*q,x+100*q,y+23*q),radius=14,
                            fill=(*mix(WHITE,col,.13),int(220*q)),outline=(*col,int(175*q)),width=2)
        if q>.65:centered_text(d,(x,y),txt,load_font(FONT_SANS_BOLD,int(h*.012)),col)
        d.line((cx,cy,x,y),fill=(*col,int(115*q)),width=2)
    glow_circle(im,cx,cy,22,GOLD,150,12)
    seal(im,"REMEMBER THE BODY MUST LEAD BACK TO MECHANISM","otherwise poetry pretends to be treatment")

def visual_empirical_questions(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    qs=[("PRE-TUMOR SIGNATURES?",CYAN),("DISTANT INFLUENCE?",GOLD),("NORMAL PARTICIPATION?",GREEN),("HEALTHY ATTRACTOR?",VIOLET)]
    for i,(txt,col) in enumerate(qs):
        x=w*(.20+i*.20); q=smoothstep(i*.12,.60+i*.07,u)
        d.rounded_rectangle((x-105*q,h*.38-35*q,x+105*q,h*.38+35*q),radius=18,
                            fill=(*mix(WHITE,col,.14),int(220*q)),outline=(*col,int(180*q)),width=3)
        if q>.65:centered_text(d,(x,h*.38),txt,load_font(FONT_SANS_BOLD,int(h*.012)),col)
    d.line((w*.15,h*.62,w*.85,h*.62),fill=(*INK,120),width=3)
    centered_text(d,(w*.5,h*.67),"EMPIRICAL QUESTIONS",load_font(FONT_SANS_BOLD,int(h*.018)),INK)
    seal(im,"GOOD METAPHORS OPEN EXPERIMENTS","their answers may support, modify, or reject the theory")

def visual_final_conversation(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    body_map_lines(im,t*.10,90)
    pts=tissue_grid(w,h)
    q=ease(u)
    for x,y,i,j in pts:
        dist=((i-7)**2+(j-3)**2)**.5
        local=smoothstep(4.2,0,dist)
        col=mix(CRIMSON,CYAN,q) if local>.3 else GREEN
        cell(d,x,y,12,col,200,False)
    # connections restore progressively
    for x,y,i,j in pts:
        alpha=int(30+150*q)
        if i<11:d.line((x+12,y,x+w*.72/11-12,y),fill=(*CYAN,alpha),width=2)
        if j<6:d.line((x,y+12,x,y+h*.46/6-12),fill=(*CYAN,alpha),width=2)
    # organism-scale contour
    d.ellipse((w*.10,h*.12,w*.90,h*.73),outline=(*GOLD,int(90+100*q)),width=4)
    seal(im,"NOT ONLY THE DAMAGED COMPONENT · THE BROKEN CONVERSATION","how did the body once convince the cell to belong?",GREEN)

VISUALS:dict[str,Callable]={
    "local":visual_local_competence,
    "voltage":visual_voltage_surface,
    "pretumor":visual_pre_tumor_state,
    "distant":visual_distant_signal,
    "context":visual_context_switch,
    "expectations":visual_tissue_expectations,
    "traffic":visual_traffic_network,
    "attractor":visual_attractor_landscape,
    "normalize":visual_normalization,
    "caution":visual_overstatement_caution,
    "identity":visual_relational_identity,
    "scale":visual_scale_sacrifice,
    "blame":visual_non_moralizing,
    "governance":visual_distributed_governance,
    "mechanisms":visual_mechanism_list,
    "questions":visual_empirical_questions,
    "final":visual_final_conversation,
}

SCENES:list[Scene]=[
    Scene("Alive enough","A cancer cell is not dead matter.",5.5,"local",{}),
    Scene("Divide","It is alive enough to divide.",5.5,"local",{}),
    Scene("Move","Alive enough to move.",5.5,"local",{}),
    Scene("Recruit and evade","Alive enough to alter surroundings, recruit vessels, evade control, and preserve its lineage.",9.0,"local",{}),
    Scene("Narrowed competence","The problem is not absence of competence. The competence has narrowed.",7.5,"local",{}),
    Scene("Local future","The cell begins acting as though its local future were the only future that matters.",8.5,"scale",{}),
    Scene("Forgot scale","It may have forgotten the scale at which it belongs.",7.0,"final",{}),

    Scene("Mainstream foundations","Cancer biology studies mutation, regulation, metabolism, immunity, microenvironment, and selection.",9.5,"caution",{}),
    Scene("Bioelectric layer","Developmental bioelectricity adds another layer.",6.5,"voltage",{}),
    Scene("Membrane voltage","Non-neural cells maintain voltages through ion channels and pumps.",8.0,"voltage",{}),
    Scene("Gap junction network","Gap junctions connect cells into tissue-scale electrical networks.",8.0,"voltage",{}),
    Scene("Influence behavior","Voltage patterns influence proliferation, migration, differentiation, and gene expression.",9.0,"voltage",{}),
    Scene("Decision surface","The membrane is not only a fence. It is an electrical decision surface.",8.0,"voltage",{}),

    Scene("Vmem research","Resting membrane potential changes during development, regeneration, and tumor-like growth.",9.0,"pretumor",{}),
    Scene("Before visible tumor","Depolarized states can appear before visible tumor-like structures.",8.0,"pretumor",{}),
    Scene("Channel intervention","Ion-channel manipulation has sometimes reduced tumor formation despite oncogenic signal.",9.0,"pretumor",{}),
    Scene("Distant metastasis signal","Altered bioelectric signaling in distant cells can induce metastasis-like behavior in models.",9.0,"distant",{}),
    Scene("Striking limited","These findings are striking and limited.",6.5,"caution",{}),
    Scene("Amphibian models","Much foundational evidence comes from amphibian models, not human treatment.",8.0,"caution",{}),
    Scene("No cure claim","This is not an established electrical cure for cancer.",7.0,"caution",{}),

    Scene("Causal question","The importance lies in the causal question.",6.0,"pretumor",{}),
    Scene("Genes not alone","If voltage changes alter tumor formation, genetic information does not act alone.",8.5,"pretumor",{}),
    Scene("Context matters","Context matters.",5.5,"context",{}),
    Scene("Voltage to transcription","Cellular voltage changes transcription, signaling molecules, and tissue interactions.",8.5,"voltage",{}),
    Scene("Same genome","The same genome can support different behaviors in different physiological networks.",9.0,"context",{}),
    Scene("Weapon and trigger","Mutation may load the weapon. Tissue state helps determine how it fires.",8.0,"pretumor",{}),

    Scene("Older observations","Older cancer biology shows malignant cells can behave differently in embryonic or regenerative contexts.",9.0,"context",{}),
    Scene("Architecture suppresses","Tissue architecture, matrix, immunity, neighbors, and developmental cues can redirect behavior.",9.5,"context",{}),
    Scene("Not evil program","Cancer is not always one evil cell carrying a complete independent program.",8.0,"context",{}),
    Scene("Failure of organization","It can also be studied as a failure of organization.",7.0,"traffic",{}),
    Scene("Misread body","The cell receives, ignores, or misinterprets information about the larger body.",8.0,"expectations",{}),
    Scene("Neighborhood possibility","The neighborhood changes what the resident believes is possible.",7.5,"context",{}),

    Scene("Forgetting metaphor","Calling this forgetting is a metaphor.",6.0,"expectations",{}),
    Scene("No conscious memory","Cells do not remember the organism through conscious images.",7.0,"expectations",{}),
    Scene("Maintained states","They participate in maintained electrical, chemical, mechanical, and genetic states.",9.0,"expectations",{}),
    Scene("Tissue expectations","A tissue carries expectations in its structure.",7.0,"expectations",{}),
    Scene("Divide stop migrate","Divide here. Stop here. Migrate there. Become this type. Repair this boundary.",9.0,"expectations",{}),
    Scene("Constraints weaken","When constraints weaken, local cellular goals can escape.",7.5,"expectations",{}),
    Scene("Not rebellion","The cell is not morally rebellious. Its regulatory world has changed.",8.0,"blame",{}),

    Scene("Traffic analogy","A traffic jam cannot be explained only by inspecting engines.",8.0,"traffic",{}),
    Scene("Cars work roads fail","Every car may function while the road network fails collectively.",8.0,"traffic",{}),
    Scene("Not merely jam","Cancer is not merely a traffic jam, but organization deserves study.",8.0,"traffic",{}),
    Scene("Society of cells","A multicellular body is a society of cells.",7.0,"governance",{}),
    Scene("Signals coordinate","Health depends on machinery and signals coordinating the whole.",8.0,"governance",{}),
    Scene("Disease in relations","The disease may exist partly in relations.",6.5,"traffic",{}),

    Scene("Distributed state","Bioelectric networks can store distributed state.",7.0,"voltage",{}),
    Scene("Cells influence cells","Connected cells influence one another and stabilize group patterns.",8.0,"voltage",{}),
    Scene("Collective attractors","Tissue behaves like a network with preferred attractors.",8.0,"attractor",{}),
    Scene("Healthy basin","Healthy anatomy may correspond to one attractor.",6.5,"attractor",{}),
    Scene("Tumor basin","A tumor-supporting state may correspond to another.",6.5,"attractor",{}),
    Scene("Shift basin","Therapy in this speculative view may shift the network, not only destroy cells.",9.0,"attractor",{}),

    Scene("Normalization","This is the idea of normalization.",6.0,"normalize",{}),
    Scene("Not irreversible","Some pathological behaviors may be reprogrammed by restoring instructive context.",8.5,"normalize",{}),
    Scene("Broader strategies","Differentiation therapy, immune modulation, and microenvironmental approaches also change state.",9.0,"normalize",{}),
    Scene("Bioelectric tools","Bioelectric work studies voltage, channels, gap junctions, serotonin, butyrate, and coordination.",9.5,"mechanisms",{}),
    Scene("Form active","It treats form as an active regulatory achievement.",7.0,"normalize",{}),

    Scene("Overstatement danger","The danger is overstatement.",5.5,"caution",{}),
    Scene("Not only electrical","Cancer is electrical is no more sufficient than cancer is genetic.",8.0,"caution",{}),
    Scene("Many cancers","Human tumors vary by tissue, mutation, immunity, metabolism, development, and history.",9.0,"caution",{}),
    Scene("Voltage roles differ","Voltage change may be cause, consequence, marker, or feedback.",8.0,"caution",{}),
    Scene("Models not clinic","Animal-model normalization does not guarantee safe human therapy.",8.0,"caution",{}),
    Scene("Narrow claim","Bioelectric state is one biologically important control layer interacting with oncogenesis.",9.0,"caution",{}),

    Scene("Identity beyond genome","A cell's identity is not located entirely in its genome.",7.0,"identity",{}),
    Scene("Shared DNA different life","Neuron and liver cell can share DNA while living radically different lives.",8.5,"identity",{}),
    Scene("Cancer intensifies","Cancer intensifies this principle.",6.0,"identity",{}),
    Scene("What signals","What signals does the cell receive?",5.5,"identity",{}),
    Scene("Which boundaries","Which collective boundaries does it respect?",5.5,"identity",{}),
    Scene("Which future","What future is its behavior organized to preserve?",6.5,"identity",{}),
    Scene("Relational identity","Identity is relational.",6.0,"identity",{}),

    Scene("Healthy sacrifice","Healthy cells sacrifice local possibilities for the larger whole.",8.0,"scale",{}),
    Scene("Stop and differentiate","They stop dividing, differentiate, die when required, and perform specialized work.",9.0,"scale",{}),
    Scene("Constraint cooperation","The body exists because cellular freedom is constrained into cooperation.",8.0,"scale",{}),
    Scene("Larger identity collapse","Cancer can involve collapse of this larger identity.",7.5,"scale",{}),
    Scene("Local self","The local lineage becomes the operative self.",6.5,"scale",{}),
    Scene("Success failure","Its success becomes the organism's failure.",6.5,"scale",{}),
    Scene("Smaller goal","A smaller goal captures the machinery of life.",7.0,"scale",{}),

    Scene("No moral psychology","This language must not become moral psychology.",7.0,"blame",{}),
    Scene("No patient blame","People with cancer are not ill because they were selfish or spiritually disconnected.",9.0,"blame",{}),
    Scene("No cosmic metaphor","Tumors are not messages sent by the universe.",7.0,"blame",{}),
    Scene("Systems value","The comparison is valuable only for systems reasoning.",7.0,"blame",{}),
    Scene("Competent parts","Competent parts can produce destructive outcomes when cross-scale coordination fails.",9.0,"traffic",{}),

    Scene("No throne","A body is not governed by one throne.",6.0,"governance",{}),
    Scene("No central cell","No central cell commands every other cell.",6.5,"governance",{}),
    Scene("Distributed order","Order is maintained through distributed communication and layered constraints.",8.5,"governance",{}),
    Scene("Collective achievement","The organism is a collective achievement renewed continuously.",8.0,"governance",{}),
    Scene("Negotiation","Health is successful negotiation among billions of agents with local information.",9.0,"governance",{}),
    Scene("Scale agreement","The body survives because its parts repeatedly agree about the scale of the problem.",9.0,"governance",{}),

    Scene("Remind cell","What would it mean to remind a cell of the body?",7.0,"mechanisms",{}),
    Scene("Molecular answer","In experimental biology the answer must be molecular and testable.",7.5,"mechanisms",{}),
    Scene("Alter voltage","Alter membrane potential.",5.5,"mechanisms",{}),
    Scene("Restore junctions","Restore gap-junction communication.",5.5,"mechanisms",{}),
    Scene("Change signals","Change extracellular signals.",5.5,"mechanisms",{}),
    Scene("Rebuild architecture","Reconstruct tissue architecture.",5.5,"mechanisms",{}),
    Scene("Recruit immunity","Recruit immune recognition.",5.5,"mechanisms",{}),
    Scene("Shift expression","Shift gene expression.",5.5,"mechanisms",{}),
    Scene("Mechanism or poetry","Remember the body is useful only if it leads back to mechanisms.",8.0,"mechanisms",{}),

    Scene("Metaphors open experiments","Good scientific metaphors can open new experiments.",7.0,"questions",{}),
    Scene("Geometry information","If cancer is partly geometry and information, new questions become visible.",8.0,"questions",{}),
    Scene("Pre-tumor signatures","Can electrical signatures reveal pre-tumor states?",6.5,"questions",{}),
    Scene("Distant tissue","Can distant tissues influence metastatic behavior?",6.5,"questions",{}),
    Scene("Normal participation","Can oncogene-bearing cells return toward normal participation?",7.0,"questions",{}),
    Scene("Healthy network","Which physiological network states stabilize healthy anatomy?",7.0,"questions",{}),
    Scene("Empirical answers","Answers may support, modify, or reject the larger theory.",8.0,"questions",{}),

    Scene("Return metaphor","A tumor may be a cell that forgot the body.",7.0,"final",{}),
    Scene("Not lost image","Not because the cell contemplated the whole and lost a memory.",7.5,"final",{}),
    Scene("Altered mechanisms","Because mechanisms connecting local action to organism-level goals were altered.",9.0,"final",{}),
    Scene("Power remains","The cell remains powerful.",5.5,"local",{}),
    Scene("Horizon shrinks","The horizon of power has shrunk.",6.5,"scale",{}),
    Scene("World too small","It adapts inside a world that no longer includes enough of the organism's future.",9.0,"scale",{}),
    Scene("Different object","The deepest promise is not an easy cure but a different object of study.",9.0,"final",{}),
    Scene("Broken conversation","Not only the damaged component. The broken conversation.",8.0,"final",{}),
    Scene("Belonging","Not only how to kill the cell. How the body once convinced it to belong.",9.0,"final",{}),
]

def render_frame(scene,frame_index,frame_count,width,height,seed):
    u=frame_index/max(1,frame_count-1); t=u*scene.duration
    dark=scene.visual=="attractor"
    im=background(width,height,seed,dark)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im,dark)
    return im.convert("RGB")

def require_ffmpeg():
    exe=shutil.which("ffmpeg")
    if not exe:raise RuntimeError("ffmpeg is required but was not found on PATH")
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
        samples=[0,int(fc*.35),int(fc*.72),fc-1]
        for oi,fi in enumerate(samples):
            render_frame(scene,fi,fc,width,height,scene_index*1000+fi).save(frame_dir/f"preview_{oi:02d}.jpg",quality=95)
        return frame_dir
    for fi in range(fc):
        p=frame_dir/f"{fi:05d}.jpg"
        if p.exists():continue
        render_frame(scene,fi,fc,width,height,scene_index*1000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(scene_index,fps)

def concatenate(paths):
    ffmpeg=require_ffmpeg(); c=OUTPUT/"concat.txt"
    c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    out=OUTPUT/"a_tumor_may_be_a_cell_that_forgot_the_body.mp4"
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
        "title":"a tumor may be a cell that forgot the body",
        "runtime_seconds":round(cursor,3),
        "scene_count":len(SCENES),
        "style":{
            "continuity_object":"cyan tissue-scale bioelectric body-map",
            "shot_duration_range_seconds":[5,10],
            "palette_roles":{
                "cyan":"collective anatomical memory",
                "green":"healthy coupling and normalization",
                "crimson":"local runaway goal and depolarization",
                "gold":"testable intervention",
                "violet":"gene regulation and latent possibility",
                "graphite":"tissue architecture",
            }
        },
        "scenes":payload
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return p

def make_contact_sheet(width,height):
    tw=320; th=int(tw*height/width); thumbs=[]
    for i,s in enumerate(SCENES,1):
        fc=max(2,round(s.duration*DEFAULT_FPS)); im=render_frame(s,int(fc*.72),fc,width,height,i*1000+72)
        im.thumbnail((tw,th)); thumbs.append((i,s.title,im.copy()))
    cols=4; rows=math.ceil(len(thumbs)/cols); cell_h=th+52
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),WHITE); d=ImageDraw.Draw(sheet); font=load_font(FONT_SANS_BOLD,15)
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
        if not 1<=args.scene<=len(SCENES):raise ValueError(f"--scene must be between 1 and {len(SCENES)}")
        print(render_scene(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview));return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:03d}/{len(SCENES):03d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,args.fps,args.width,args.height,args.preview)
        if not args.preview:rendered.append(r)
    if not args.no_contact_sheet:print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview:print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
