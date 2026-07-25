#!/usr/bin/env python3
"""
KNOWLEDGE BINDS BY MAKING THE WORLD SMALL ENOUGH TO USE
A complete Platinum-house procedural visual essay.

Source:
expansion-essays/01_knowledge_binds_by_making_the_world_small_enough_to_use.md

VISUAL THESIS
-------------
Finite cognition survives by compression. A large field passes through a narrow
bottleneck and becomes food, threat, face, path, mine. Bondage begins when the
selected map forgets the field it excluded.

HOUSE RULES
-----------
• 5–10 seconds per scene.
• Every shot visibly transforms one state into another.
• Clean ivory scientific field.
• No slideshow layouts.
• Sparse labels only.
• Mature frame around u=0.72.
• Continuity object: a cyan aperture that first narrows, later becomes transparent.

PALETTE ROLES
-------------
IVORY    uncompressed field
CYAN     bottleneck / selective attention
GOLD     useful invariant / awakened recognition
INK      fixed category / determination
VIOLET   excluded variation / latent detail
CRIMSON  defensive compression / rigid prior
GREEN    transparent concept / flexible use

OUTPUT
------
output_knowledge_binds/
  frames/
  scenes/
  knowledge_binds.mp4
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
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_knowledge_binds"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 10

IVORY=(249,247,241)
WHITE=(255,254,250)
INK=(29,33,39)
SOFT_INK=(86,91,98)
SILVER=(180,187,194)
PALE_SILVER=(226,229,232)
CYAN=(57,156,180)
PALE_CYAN=(196,227,233)
GOLD=(194,156,72)
PALE_GOLD=(236,219,175)
VIOLET=(109,83,153)
PALE_VIOLET=(220,211,237)
CRIMSON=(162,58,69)
PALE_CRIMSON=(231,198,202)
GREEN=(70,139,99)
PALE_GREEN=(198,225,208)

FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3
def pulse(t,s=1.0,p=0.0): return .5+.5*math.sin(math.tau*(s*t+p))

def font(path,size):
    for c in (path,FONT_SERIF,FONT_SANS):
        try: return ImageFont.truetype(c,size)
        except OSError: pass
    return ImageFont.load_default()

def layer(size): return Image.new("RGBA",size,(0,0,0,0))

def field(w,h,seed):
    rng=np.random.default_rng(seed)
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=IVORY
    arr+=rng.normal(0,.9,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2.0)
    arr[...,1]+=halo*3.5; arr[...,2]+=halo*5.0
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")

def centered(d,xy,text,f,fill=INK): d.text(xy,text,font=f,fill=fill,anchor="mm")

def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered(d,(w/2,h*.875),title,font(FONT_SERIF_BOLD,max(22,int(h*.04))),color)
    if subtitle:
        centered(d,(w/2,h*.923),subtitle,font(FONT_SANS,max(13,int(h*.019))),SOFT_INK)

def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,45),width=2)

def glow_circle(im,x,y,r,color,alpha=170,blur=14):
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.ellipse((x-r,y-r,x+r,y+r),fill=(*color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).ellipse((x-r*.35,y-r*.35,x+r*.35,y+r*.35),
                               fill=(*mix(color,WHITE,.35),min(255,alpha+50)))
    im.alpha_composite(fg)

def glow_line(im,pts,color,width=4,alpha=210,blur=11):
    if len(pts)<2: return
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.line(pts,fill=(*color,alpha),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(color,WHITE,.08),min(255,alpha+20)),
                            width=width,joint="curve")
    im.alpha_composite(fg)

def partial(pts,a):
    if not pts: return []
    a=clamp(a)
    if a>=1: return pts
    k=a*(len(pts)-1); i=int(k); f=k-i
    out=list(pts[:i+1])
    if i+1<len(pts):
        p,q=pts[i],pts[i+1]
        out.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return out

def arrow(d,a,b,color=INK,width=3,head=10):
    d.line((*a,*b),fill=color,width=width)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (-1,1):
        p=(b[0]-math.cos(ang+s*.52)*head,b[1]-math.sin(ang+s*.52)*head)
        d.line((*b,*p),fill=color,width=width)

def aperture_polygon(cx,cy,left_w,right_w,height):
    return [(cx-left_w,cy-height/2),(cx+right_w,cy-height*.18),
            (cx+right_w,cy+height*.18),(cx-left_w,cy+height/2)]

def draw_aperture(d,cx,cy,width,height,alpha=220,color=CYAN):
    d.rounded_rectangle((cx-width/2,cy-height/2,cx+width/2,cy+height/2),
                        radius=max(8,int(width*.12)),outline=(*color,alpha),width=4)

def noisy_points(w,h,count,seed):
    rng=random.Random(seed)
    return [(rng.uniform(w*.08,w*.92),rng.uniform(h*.16,h*.70),
             [CYAN,VIOLET,GOLD,SOFT_INK,CRIMSON][i%5]) for i in range(count)]

def draw_word_box(d,x,y,text,color,alpha=220,w=145,h=42):
    d.rounded_rectangle((x-w/2,y-h/2,x+w/2,y+h/2),radius=14,
                        fill=(*mix(WHITE,color,.12),alpha),
                        outline=(*color,alpha),width=2)
    centered(d,(x,y),text,font(FONT_SANS_BOLD,16),(*color,alpha))


# =============================================================================
# VISUALS
# =============================================================================

def vis_world_compress(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=noisy_points(w,h,180,44)
    q=ease(u)
    aperture_x=w*.55
    width=lerp(w*.34,w*.07,q)
    draw_aperture(d,aperture_x,h*.40,width,h*.40,220,CYAN)
    for i,(x,y,col) in enumerate(pts):
        if x<aperture_x:
            xx=x; yy=y
        else:
            xx=lerp(x,w*.78,q)
            yy=lerp(y,h*.40,q)
        r=2+i%3
        d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(*col,int(80+110*q)))
    if q>.55:
        labels=["FOOD","THREAT","FACE","PATH","MINE"]
        for i,lab in enumerate(labels):
            yy=h*(.24+i*.08)
            draw_word_box(d,w*.82,yy,lab,[GREEN,CRIMSON,CYAN,GOLD,VIOLET][i],int(220*q),130,34)
    seal(im,"A WORLD TOO LARGE BECOMES USABLE",
         "survival depends on selective discard")


def vis_triad(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    spread=smoothstep(.10,.62,u)
    labels=[("KNOWER",CYAN,-190,0),("KNOWN",GOLD,190,0),("RULE",VIOLET,0,155)]
    for lab,col,ox,oy in labels:
        x=lerp(cx,cx+ox,spread); y=lerp(cy,cy+oy,spread)
        glow_circle(im,x,y,14,col,170,11)
        if spread>.4: centered(d,(x,y-34),lab,font(FONT_SANS_BOLD,17),col)
    if spread>.35:
        for i in range(3):
            x1,y1=cx+labels[i][2]*spread,cy+labels[i][3]*spread
            x2,y2=cx+labels[(i+1)%3][2]*spread,cy+labels[(i+1)%3][3]*spread
            d.line((x1,y1,x2,y2),fill=(*INK,int(150*spread)),width=3)
    seal(im,"CONTRACTED KNOWLEDGE",
         "knower, known, and rule harden into separate terms")


def vis_chair_exclusion(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.39
    details=[
        ("MOLECULES",VIOLET,-210,-100),("SCRATCHES",CRIMSON,210,-100),
        ("HISTORY",GOLD,-220,100),("LIGHT",CYAN,220,100),("AIR",GREEN,0,170)
    ]
    fade=ease(u)
    for lab,col,ox,oy in details:
        x,y=cx+ox,cy+oy
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,15),(*col,int(210*(1-fade*.85))))
        d.line((x,y,cx,cy),fill=(*col,int(110*(1-fade*.8))),width=2)
    # chair appears as details vanish
    alpha=int(230*fade)
    d.line((cx-55,cy-55,cx-55,cy+80),fill=(*INK,alpha),width=6)
    d.line((cx+55,cy-55,cx+55,cy+80),fill=(*INK,alpha),width=6)
    d.line((cx-55,cy-15,cx+55,cy-15),fill=(*INK,alpha),width=8)
    d.line((cx-55,cy-55,cx+55,cy-55),fill=(*INK,alpha),width=8)
    centered(d,(cx,cy+130),"CHAIR",font(FONT_SERIF_BOLD,30),(*INK,alpha))
    seal(im,"A CONCEPT WORKS BY EXCLUSION",
         "the object becomes manageable because most of it disappears")


def vis_information_bottleneck(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    left_pts=noisy_points(w,h,120,88)
    for i,(x,y,col) in enumerate(left_pts):
        xx=lerp(x,w*.39,q*.25); yy=lerp(y,cy,q*.45)
        if x<w*.44:
            d.ellipse((xx-3,yy-3,xx+3,yy+3),fill=(*col,130))
    width=lerp(w*.20,w*.055,q)
    draw_aperture(d,cx,cy,width,h*.30,230,CYAN)
    # output features
    feats=[("EDGE",CYAN),("SHAPE",GOLD),("CATEGORY",GREEN)]
    for i,(lab,col) in enumerate(feats):
        x=w*.72+i*w*.08
        y=cy+(i-1)*55
        draw_word_box(d,x,y,lab,col,int(120+100*q),120,34)
    glow_line(im,partial([(w*.35,cy),(cx,cy),(w*.72,cy)],q),CYAN,5,210,13)
    seal(im,"THE INFORMATION BOTTLENECK",
         "retain what predicts the target; discard what the task ignores")


def vis_task_compressions(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    tasks=[("CLASSIFY",CYAN,-220,-95),("RECONSTRUCT",GOLD,220,-95),
           ("NAVIGATE",GREEN,-220,105),("REMEMBER",VIOLET,220,105)]
    q=ease(u)
    for i,(lab,col,ox,oy) in enumerate(tasks):
        x,y=cx+ox,cy+oy
        draw_word_box(d,x,y,lab,col,220,160,40)
        # distinct retained dimensions
        count=2+i
        for k in range(count):
            a=k*math.tau/max(1,count)
            px=x+math.cos(a)*42*q; py=y+math.sin(a)*22*q
            d.ellipse((px-5,py-5,px+5,py+5),fill=(*col,180))
        arrow(d,(cx,cy),(x,y),(*col,170),2,7)
    glow_circle(im,cx,cy,15,INK,150,10)
    seal(im,"THERE IS NO PURPOSE-FREE COMPRESSED TRUTH",
         "the goal decides which differences survive")


def vis_different_worlds(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    roles=[("BOTANIST",GREEN),("CARPENTER",GOLD),("AFRAID",CRIMSON),("CHILD",CYAN)]
    q=ease(u)
    for i,(lab,col) in enumerate(roles):
        x=w*(.18+i*.21); y=h*.40
        d.ellipse((x-70,y-120,x+70,y+120),outline=(*col,180),width=4)
        # same central tree, different highlighted features
        d.line((x,y-30,x,y+65),fill=(*INK,160),width=5)
        d.ellipse((x-38,y-80,x+38,y-5),outline=(*GREEN,120),width=3)
        if i==0: d.ellipse((x-45,y-87,x+45,y+2),outline=(*GREEN,int(220*q)),width=5)
        elif i==1: d.line((x-18,y-30,x+18,y+50),fill=(*GOLD,int(220*q)),width=6)
        elif i==2: arrow(d,(x,y),(x+45,y+70),(*CRIMSON,int(220*q)),4,9)
        else: d.arc((x-55,y-25,x+55,y+95),200,340,fill=(*CYAN,int(220*q)),width=5)
        centered(d,(x,h*.69),lab,font(FONT_SANS_BOLD,16),col)
    seal(im,"THE FIELD OVERLAPS · THE BOTTLENECK DIFFERS",
         "training, memory, state, and purpose shape the appearing world")


def vis_model_prison(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    phrase=p.get("phrase","I FAILED")
    q=ease(u)
    # events merge into one category
    events=[(-190,-100),(-140,80),(0,-140),(145,-70),(190,95),(-20,140)]
    for ox,oy in events:
        x=lerp(cx+ox,cx,q); y=lerp(cy+oy,cy,q)
        d.ellipse((x-8,y-8,x+8,y+8),fill=(*VIOLET,int(150*(1-q*.5))))
    centered(d,(cx,cy),phrase,font(FONT_SERIF_BOLD,int(h*.055)),(*CRIMSON,int(230*q)))
    if q>.55:
        for i in range(-3,4):
            x=cx+i*42
            d.line((x,cy-130,x,cy+130),fill=(*INK,int(160*(q-.55)/.45)),width=4)
    seal(im,"A SUMMARY BECOMES A PRISON",
         "the model controls which future evidence can still appear",CRIMSON)


def vis_memorize_compress(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    cycle=(u*2)%1
    detail_phase=u<.5
    rng=random.Random(33)
    if detail_phase:
        for i in range(90):
            x=rng.uniform(w*.15,w*.85); y=rng.uniform(h*.20,h*.65)
            d.ellipse((x-3,y-3,x+3,y+3),fill=(*[CYAN,VIOLET,GOLD][i%3],140))
        seal(im,"CONTACT WITH DETAIL","learning begins by absorbing variation")
    else:
        q=smoothstep(.5,1,u)
        groups=[(w*.32,h*.35,CYAN),(w*.50,h*.48,GOLD),(w*.68,h*.32,GREEN)]
        for gx,gy,col in groups:
            glow_circle(im,gx,gy,18,col,170,11)
        for i in range(90):
            x=rng.uniform(w*.15,w*.85); y=rng.uniform(h*.20,h*.65)
            nearest=min(groups,key=lambda g:(x-g[0])**2+(y-g[1])**2)
            xx=lerp(x,nearest[0],q); yy=lerp(y,nearest[1],q)
            d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=(*nearest[2],100))
        seal(im,"SELECTIVE FORGETTING","generalization requires compression after contact")


def vis_local_os(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # operating system window closes around subject
    d.rounded_rectangle((cx-260*q,cy-150*q,cx+260*q,cy+150*q),radius=22,
                        fill=(*PALE_SILVER,int(180*q)),outline=(*INK,int(210*q)),width=4)
    if q>.35:
        labels=["KNOWN","USEFUL","ALLOWED","REAL"]
        for i,lab in enumerate(labels):
            draw_word_box(d,cx-150+i*100,cy-80,lab,[CYAN,GOLD,GREEN,CRIMSON][i],200,90,34)
        centered(d,(cx,cy+25),"I AM THE ONE REPRESENTED HERE",
                 font(FONT_SERIF_BOLD,24),INK)
    if q>.72:
        d.line((cx-220,cy+95,cx+220,cy+95),fill=(*CRIMSON,180),width=4)
    seal(im,"A LOCAL OPERATING SYSTEM",
         "knowledge forgets that it runs inside a larger field")


def vis_cage_key(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    letters=list("A I U M Ś H R Ī M".split())
    # cage first
    for i,lab in enumerate(letters):
        x=cx-180+i*(360/max(1,len(letters)-1))
        y=cy
        centered(d,(x,y),lab,font(FONT_SERIF_BOLD,28),(*INK,int(220*(1-q*.35))))
        d.line((x,cy-95,x,cy+95),fill=(*INK,int(160*(1-q*.5))),width=3)
    # then letters arc into key
    if q>.35:
        pts=[]
        for i in range(100):
            a=lerp(math.pi*.1,math.pi*1.9,i/99)
            pts.append((cx+math.cos(a)*110,cy+math.sin(a)*70))
        glow_line(im,partial(pts,(q-.35)/.65),GOLD,5,210,13)
        d.line((cx+110,cy,cx+235,cy),fill=(*GOLD,int(220*q)),width=7)
        d.ellipse((cx+215,cy-18,cx+250,cy+18),outline=(*GOLD,int(220*q)),width=5)
    seal(im,"THE CAGE AND KEY USE THE SAME LETTERS",
         "a word binds when it hides articulation; mantra reveals the power")


def vis_prior_field(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    prior=smoothstep(.10,.65,u)
    evidence=smoothstep(.45,.95,u)
    # ambiguous incoming dots
    rng=random.Random(77)
    pts=[]
    for i in range(80):
        x=rng.uniform(w*.12,w*.40); y=rng.uniform(h*.20,h*.65)
        pts.append((x,y))
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*SILVER,120))
    # strong prior bends them
    for x,y in pts:
        bx=lerp(x,cx,prior*.65)
        by=lerp(y,cy-50,prior*.65)
        d.line((x,y,bx,by),fill=(*CRIMSON,int(90*prior)),width=2)
    centered(d,(cx+170,cy-50),"DANGER",font(FONT_SERIF_BOLD,30),(*CRIMSON,int(220*prior)))
    if evidence>.5:
        # conflicting green evidence remains outside
        for i in range(8):
            x=w*.72+i*14; y=cy+80+math.sin(i)*15
            d.ellipse((x-5,y-5,x+5,y+5),fill=(*GREEN,int(220*evidence)))
    seal(im,"A STRONG PRIOR CHANGES WHAT COUNTS AS EVIDENCE",
         "compression becomes defensive when correction is explained away",CRIMSON)


def vis_social_compression(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    labels=[("STUDENT","SCORE",CYAN),("BORROWER","CREDIT",GOLD),
            ("TRAVELLER","BORDER",CRIMSON)]
    q=ease(u)
    for i,(person,metric,col) in enumerate(labels):
        x=w*(.22+i*.28); y=h*.40
        # person as rich cloud
        for k in range(18):
            a=k*math.tau/18
            rr=45+12*math.sin(k*2)
            px=x+math.cos(a)*rr*(1-q*.6)
            py=y+math.sin(a)*rr*(1-q*.6)
            d.ellipse((px-5,py-5,px+5,py+5),fill=(*[CYAN,VIOLET,GREEN,GOLD][k%4],120))
        centered(d,(x,y),metric,font(FONT_SERIF_BOLD,26),(*col,int(230*q)))
        centered(d,(x,h*.68),person,font(FONT_SANS_BOLD,15),SOFT_INK)
    seal(im,"LARGE SYSTEMS GOVERN BY REDUCTION",
         "efficiency is purchased by dimensions the model cannot represent")


def vis_map_landscape(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    # landscape
    pts=[]
    for i in range(180):
        x=w*.10+i*w*.80/179
        y=h*.55-60*math.sin(i/179*math.pi*2)-25*math.sin(i/179*math.pi*5)
        pts.append((x,y))
    d.line(pts,fill=(*GREEN,int(220*q)),width=5)
    # map grid overlays and then becomes translucent
    opacity=int(210*(1-q*.65))
    for i in range(9):
        x=w*.18+i*w*.64/8
        d.line((x,h*.20,x,h*.67),fill=(*INK,opacity),width=2)
    for j in range(6):
        y=h*.22+j*h*.42/5
        d.line((w*.18,y,w*.82,y),fill=(*INK,opacity),width=2)
    centered(d,(w*.50,h*.33),"MAP",font(FONT_SERIF_BOLD,32),(*INK,opacity))
    if q>.6:
        centered(d,(w*.50,h*.70),"LANDSCAPE REMAINS",font(FONT_SANS_BOLD,17),GREEN)
    seal(im,"A MAP NEED NOT BE FALSE TO BECOME A PRISON",
         "it binds when it becomes the only thing one is willing to see")


def vis_transparent_concept(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # concept box fades transparent while field remains
    alpha=int(220*(1-q*.75))
    d.rounded_rectangle((cx-240,cy-125,cx+240,cy+125),radius=22,
                        fill=(*PALE_CYAN,alpha//2),outline=(*CYAN,alpha),width=4)
    centered(d,(cx,cy),"CONCEPT",font(FONT_SERIF_BOLD,34),(*CYAN,alpha))
    # larger field appears through it
    for rr in range(40,260,34):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(85*q*(1-rr/290))),width=3)
    if q>.65:
        glow_circle(im,cx,cy,14,GOLD,180,12)
    seal(im,"A CONCEPT BECOMES TRANSPARENT",
         "it performs its task without claiming to measure everything",GREEN)


def vis_inquiry_sentence(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    sentence=p.get("sentence","I AM INCAPABLE")
    q=ease(u)
    centered(d,(cx,cy-120),sentence,font(FONT_SERIF_BOLD,30),CRIMSON)
    questions=[
        "WHICH EVENTS WERE MERGED?",
        "WHICH DIFFERENCES WERE DISCARDED?",
        "WHAT PREDICTION BECAME CHEAP?",
        "WHAT EVIDENCE BECAME EXPENSIVE?"
    ]
    for i,text in enumerate(questions):
        local=clamp(q*len(questions)-i)
        y=cy-20+i*48
        d.line((cx-260,y,cx-260+420*local,y),fill=(*CYAN,int(180*local)),width=3)
        centered(d,(cx,y-12),text,font(FONT_SANS_BOLD,15),(*SOFT_INK,int(210*local)))
    seal(im,"EXAMINE THE COMPRESSION",
         "bondage lies in claiming that nothing relevant remains outside")


def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # field
    pts=noisy_points(w,h,160,101)
    for x,y,col in pts:
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*col,int(70+60*q)))
    # aperture remains but becomes transparent
    width=lerp(w*.08,w*.18,q)
    alpha=int(220*(1-q*.55))
    draw_aperture(d,cx,cy,width,h*.34,alpha,CYAN)
    # gold field passes through without being reduced to aperture
    for rr in range(30,270,32):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(85*q*(1-rr/300))),width=3)
    if q>.7:
        centered(d,(cx,h*.70),"JÑĀNAṂ BANDHAḤ",font(FONT_SERIF_BOLD,30),GOLD)
    seal(im,"KNOWLEDGE BINDS BY MAKING THE WORLD SMALL ENOUGH TO USE",
         "wisdom remembers that the field was never contained by the model",GOLD)


VISUALS: dict[str,Callable] = {
    "compress":vis_world_compress,
    "triad":vis_triad,
    "chair":vis_chair_exclusion,
    "bottleneck":vis_information_bottleneck,
    "tasks":vis_task_compressions,
    "worlds":vis_different_worlds,
    "prison":vis_model_prison,
    "cycle":vis_memorize_compress,
    "os":vis_local_os,
    "cage":vis_cage_key,
    "prior":vis_prior_field,
    "social":vis_social_compression,
    "map":vis_map_landscape,
    "transparent":vis_transparent_concept,
    "inquiry":vis_inquiry_sentence,
    "final":vis_final,
}


@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict


SCENES=[
    Scene("Too much world","A living organism cannot perceive everything, remember every detail, or test every interpretation before acting.",9.0,"compress",{}),
    Scene("Discard","To survive, it must discard.",5.5,"compress",{}),
    Scene("Usable distinctions","The nervous system compresses a world too large to inhabit into distinctions small enough to use: food, threat, face, path, mine.",10.0,"compress",{}),
    Scene("Jñānaṃ bandhaḥ","Jñānaṃ bandhaḥ. Knowledge is bondage.",6.5,"final",{}),
    Scene("Not anti-truth","The claim is not that truth enslaves and ignorance liberates.",7.0,"transparent",{}),
    Scene("Closure","Every usable knowledge closes a larger field into one determinate world.",8.5,"compress",{}),

    Scene("Consciousness and bondage","If consciousness is primary, why should knowing bind it?",7.5,"triad",{}),
    Scene("Contracted knowledge","The text attacks contracted knowledge: cognition divided into knower, known object, and rule.",9.0,"triad",{}),
    Scene("This not that","The world becomes this and not that. Each determination is useful. Each hides the freedom that produced it.",9.5,"triad",{}),

    Scene("Chair","To recognize a chair, the system ignores almost everything about it.",7.0,"chair",{}),
    Scene("Discarded details","Molecular composition, scratches, history, changing light, and moving air disappear from the usable concept.",9.5,"chair",{}),
    Scene("Bottleneck","A representation containing every physical detail would be as difficult to use as the world itself. Knowledge requires a bottleneck.",10.0,"bottleneck",{}),

    Scene("Information bottleneck","The Information Bottleneck principle retains information useful for predicting a target while discarding variation irrelevant to that task.",10.0,"bottleneck",{}),
    Scene("Too little","Compression without prediction produces ignorance.",6.0,"bottleneck",{}),
    Scene("Too much","Prediction without compression produces an unusable copy.",6.0,"bottleneck",{}),
    Scene("Selective invariance","Knowing becomes selective invariance: stable across noise while preserving task-relevant differences.",9.0,"tasks",{}),

    Scene("Task dependence","Different tasks require different compressions.",6.5,"tasks",{}),
    Scene("No single truth","A representation optimized for classification may discard what reconstruction needs. There is no single compressed truth independent of purpose.",10.0,"tasks",{}),
    Scene("Goal selects","Every useful model preserves one family of differences by sacrificing others. The goal decides what becomes real enough to retain.",10.0,"tasks",{}),

    Scene("Different worlds","Two people can occupy different worlds without hallucinating the entire environment.",8.0,"worlds",{}),
    Scene("Botanist and carpenter","A botanist sees species. A carpenter sees grain, stress, and joinery.",8.0,"worlds",{}),
    Scene("Fear and play","A frightened person sees exits. A child sees climbable surfaces.",8.0,"worlds",{}),
    Scene("Task-shaped reduction","The sensory field overlaps. The bottleneck differs. The world appears through task-shaped reduction.",9.0,"worlds",{}),

    Scene("Reduction forgotten","The Śiva Sūtras calls this bondage because the reduction is forgotten.",8.0,"prison",{"phrase":"I FAILED"}),
    Scene("Model as prison","A model mistaken for the final structure of reality becomes a prison.",8.0,"prison",{"phrase":"I FAILED"}),
    Scene("Future controlled","The concept does not merely summarize the past. It controls what future can be learned.",9.0,"prison",{"phrase":"I FAILED"}),

    Scene("Memorize","Learning requires contact with detail.",6.5,"cycle",{}),
    Scene("Compress","Generalization requires selective forgetting.",6.5,"cycle",{}),
    Scene("Timing","A system compressing too early repeats prior categories and misses novelty. Intelligence depends on when the bottleneck tightens.",10.0,"cycle",{}),

    Scene("Not anti-conceptual","Tantra is not anti-conceptual. Language, mantra, discrimination, ritual, and philosophy are all used.",9.0,"cage",{}),
    Scene("Identification","Bondage occurs when consciousness appears only as the limited subject enclosed by its representation.",9.5,"os",{}),
    Scene("Local operating system","Knowledge becomes a local operating system that has forgotten it is running inside a larger field.",9.0,"os",{}),

    Scene("Alphabet binds","The same alphabet can bind through fixed concepts.",7.0,"cage",{}),
    Scene("Alphabet liberates","It can liberate when articulation becomes visible as consciousness's own power.",8.5,"cage",{}),
    Scene("Cage and key","The cage and key are made from the same letters.",6.5,"cage",{}),

    Scene("Strong priors","Predictive processing uses prior expectations to interpret ambiguous signals.",8.0,"prior",{}),
    Scene("Stability","Strong priors stabilize perception. Without them, the world would be noisy and difficult to act within.",9.0,"prior",{}),
    Scene("Defensive compression","Excessive precision explains away conflicting evidence. Compression becomes defensive.",8.5,"prior",{}),

    Scene("Ethical bottleneck","The information bottleneck is also an ethical problem.",7.0,"social",{}),
    Scene("Scores","A school score reduces a student. A credit score reduces a borrower. A border reduces a traveller.",9.5,"social",{}),
    Scene("Cost outside model","Compression makes systems governable, but the cost is paid by what they cannot represent.",9.0,"social",{}),

    Scene("Accurate prison","A perfectly accurate local model can bind if it claims universality.",8.0,"map",{}),
    Scene("Map and landscape","A map does not need to be false to hide the landscape. It only needs to become the only thing one is willing to see.",10.0,"map",{}),

    Scene("Recognition","Recognition does not require throwing the map away. It reveals the map as an activity within awareness.",9.0,"transparent",{}),
    Scene("Known objects","Thought appears. Category appears. Prediction appears. Certainty appears. Each is known.",9.0,"transparent",{}),
    Scene("Turn toward knower","Pratyabhijñā asks not what final description contains me, but what is present before, during, and after every description.",10.0,"transparent",{}),

    Scene("Definitive sentence","Take one sentence that feels definitive: I am incapable.",7.0,"inquiry",{"sentence":"I AM INCAPABLE"}),
    Scene("Inspect compression","Which events were merged? Which differences discarded? What prediction became cheap? What evidence became expensive?",10.0,"inquiry",{"sentence":"I AM INCAPABLE"}),
    Scene("Truth without totality","The sentence may contain truth. Its bondage lies in claiming that nothing relevant remains outside it.",9.5,"inquiry",{"sentence":"I AM INCAPABLE"}),

    Scene("No final escape","Finite cognition cannot escape compression completely. Even 'all is consciousness' is a summary that omits detail.",9.5,"transparent",{}),
    Scene("Transparent concept","A concept becomes transparent when it performs its task without claiming that its task measures everything.",9.5,"transparent",{}),

    Scene("Return","A living organism cannot perceive everything. It survives by compressing.",7.5,"compress",{}),
    Scene("Necessary bottlenecks","The Śiva Sūtras does not ask the finite mind to become omniscient.",7.5,"final",{}),
    Scene("Closing","It asks consciousness to stop mistaking its necessary bottlenecks for the boundary of reality.",9.5,"final",{}),
    Scene("Wisdom","Knowledge binds by making the world small enough to use. Wisdom begins when the user remembers that the field was never contained by the model.",10.0,"final",{}),
]


def render_frame(scene,fi,count,w,h,seed):
    u=fi/max(1,count-1); t=u*scene.duration
    im=field(w,h,seed)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im)
    return im.convert("RGB")

def ffmpeg():
    x=shutil.which("ffmpeg")
    if not x: raise RuntimeError("ffmpeg required")
    return x

def encode_scene(i,fps):
    out=SCENES_DIR/f"scene_{i:03d}.mp4"
    subprocess.run([ffmpeg(),"-y","-framerate",str(fps),"-i",
                    str(FRAMES/f"scene_{i:03d}"/"%05d.jpg"),
                    "-c:v","libx264","-preset","medium","-crf","18",
                    "-pix_fmt","yuv420p","-movflags","+faststart",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def render_scene(i,scene,fps,w,h,preview):
    fd=FRAMES/f"scene_{i:03d}"; fd.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    count=max(2,round(scene.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(count*.33),int(count*.72),count-1]):
            render_frame(scene,fi,count,w,h,i*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(count):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(scene,fi,count,w,h,i*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(i,fps)

def concatenate(paths):
    txt=OUTPUT/"concat.txt"
    txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    out=OUTPUT/"knowledge_binds.mp4"
    subprocess.run([ffmpeg(),"-y","-f","concat","-safe","0","-i",str(txt),
                    "-c","copy","-movflags","+faststart",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def export_timeline():
    cur=0.0; rec=[]
    for i,s in enumerate(SCENES,1):
        x=asdict(s); x["scene_id"]=f"scene_{i:03d}"; x["start_seconds"]=round(cur,3)
        cur+=s.duration; x["end_seconds"]=round(cur,3); rec.append(x)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({
        "title":"knowledge binds by making the world small enough to use",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cur,3),
        "shot_duration_range":[5,10],
        "continuity_object":"cyan aperture",
        "scenes":rec
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return p

def contact_sheet(w,h):
    tw=320; th=int(tw*h/w); cols=4; rows=math.ceil(len(SCENES)/cols)
    sheet=Image.new("RGB",(cols*tw,rows*(th+48)),IVORY)
    d=ImageDraw.Draw(sheet); f=font(FONT_SANS_BOLD,14)
    for i,s in enumerate(SCENES,1):
        c=max(2,round(s.duration*DEFAULT_FPS))
        im=render_frame(s,int(c*.72),c,w,h,i*10000+72); im.thumbnail((tw,th))
        x=((i-1)%cols)*tw; y=((i-1)//cols)*(th+48)
        sheet.paste(im,(x,y)); d.text((x+8,y+th+7),f"{i:02d}  {s.title}",font=f,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; sheet.save(p,quality=94); return p

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS)
    p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    p.add_argument("--scene",type=int)
    p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()

def main():
    a=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError("scene out of range")
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview))
        return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rendered.append(r)
    if not a.no_contact_sheet: print(f"Contact sheet: {contact_sheet(a.width,a.height)}")
    if not a.preview: print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
