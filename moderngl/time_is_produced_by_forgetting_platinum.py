#!/usr/bin/env python3
"""
TIME IS PRODUCED BY FORGETTING
Abhinavagupta on Sequence, Contraction, and the Construction of Temporal Experience

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Ordinary consciousness experiences one event after another because it cannot
hold the whole field of manifestation in one act.

For Abhinavagupta, the Absolute is not trapped inside succession.
Temporal sequence appears when unlimited awareness contracts into a finite
center with limited attention, memory, anticipation, and action.

This does not mean clocks are imaginary or physics is false.
It means lived temporality—the felt passage from past to future—is inseparable
from the structure of a limited subject.

FILM THESIS
-----------
The modern picture often runs:

time → events → memory → identity

The Śaiva picture can be staged as:

unbounded manifestation
→ contraction
→ exclusion
→ sequence
→ memory
→ anticipation
→ personal time
→ recognition

The past is not simply annihilated.
It becomes unavailable to present attention except through trace and recall.

The future is not yet an experienced object.
It is an open field shaped by expectation, desire, and action.

HOUSE RULES
-----------
• Every shot lasts 5–10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a gold simultaneous field narrowing into a cyan timeline.
• Final reveal: the timeline remains inside the field it seemed to contain.

OUTPUT
------
output_time_forgetting/
  frames/
  scenes/
  time_is_produced_by_forgetting.mp4
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
OUTPUT = ROOT / "output_time_forgetting"
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
CYAN=(57,156,180)
PALE_CYAN=(196,227,233)
GOLD=(194,156,72)
PALE_GOLD=(236,219,175)
GREEN=(70,139,99)
CRIMSON=(162,58,69)
VIOLET=(109,83,153)

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
def ease(t):
    t=clamp(t); return .5-.5*math.cos(math.pi*t)

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
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2)
    arr[...,1]+=halo*3.2; arr[...,2]+=halo*4.6
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")

def centered(d,xy,text,fnt,fill=INK):
    d.text(xy,text,font=fnt,fill=fill,anchor="mm")

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
    ImageDraw.Draw(fg).ellipse(
        (x-r*.34,y-r*.34,x+r*.34,y+r*.34),
        fill=(*mix(color,WHITE,.35),min(255,alpha+50))
    )
    im.alpha_composite(fg)

def glow_line(im,pts,color,width=4,alpha=210,blur=11):
    if len(pts)<2: return
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.line(pts,fill=(*color,alpha),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(
        pts,fill=(*mix(color,WHITE,.08),min(255,alpha+25)),
        width=width,joint="curve"
    )
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

def draw_body(d,cx,cy,scale=1.0,color=INK,alpha=205):
    d.ellipse((cx-27*scale,cy-145*scale,cx+27*scale,cy-91*scale),
              outline=(*color,alpha),width=max(2,int(4*scale)))
    d.line((cx,cy-91*scale,cx,cy+55*scale),
           fill=(*color,alpha),width=max(3,int(6*scale)))
    d.line((cx-68*scale,cy-54*scale,cx+68*scale,cy-54*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((cx,cy+55*scale,cx-52*scale,cy+160*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((cx,cy+55*scale,cx+52*scale,cy+160*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))

def event_field(w,h,count=36,seed=0):
    rng=random.Random(seed)
    return [(rng.uniform(w*.16,w*.84),rng.uniform(h*.20,h*.62)) for _ in range(count)]


# =============================================================================
# VISUALS
# =============================================================================

def vis_all_at_once(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=event_field(w,h,40,1); q=ease(u)
    for i,(x,y) in enumerate(pts):
        col=[GOLD,CYAN,VIOLET,GREEN][i%4]
        glow_circle(im,x,y,8,col,int(110+70*q),7)
    for rr in range(45,285,32):
        d.ellipse((w*.50-rr,h*.40-rr*.60,w*.50+rr,h*.40+rr*.60),
                  outline=(*GOLD,int(65*q*(1-rr/315))),width=3)
    seal(im,"IMAGINE A FIELD WITH NO BEFORE OR AFTER",
         "difference is present without being forced into sequence")

def vis_exclusion(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=event_field(w,h,34,3); q=ease(u)
    target=pts[15]
    for i,(x,y) in enumerate(pts):
        dist=math.dist((x,y),target)
        alpha=190 if dist<70 else int(170*(1-q))
        glow_circle(im,x,y,8,[GOLD,CYAN,VIOLET,GREEN][i%4],alpha,7)
    r=lerp(220,55,q)
    d.ellipse((target[0]-r,target[1]-r,target[0]+r,target[1]+r),
              outline=(*CYAN,205),width=5)
    seal(im,"FINITE ATTENTION EXCLUDES",
         "to hold this clearly is to let the rest become unavailable")

def vis_sequence_birth(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=event_field(w,h,8,9)
    q=ease(u)
    sorted_pts=sorted(pts,key=lambda p:p[0])
    for i,(x,y) in enumerate(sorted_pts):
        glow_circle(im,x,y,10,[GOLD,CYAN,VIOLET,GREEN][i%4],150,8)
    glow_line(im,partial(sorted_pts,q),CYAN,5,195,12)
    for i,(x,y) in enumerate(sorted_pts):
        if q>.55:
            centered(d,(x,y+28),str(i+1),font(FONT_SANS_BOLD,13),INK)
    seal(im,"EXCLUSION TURNS DIFFERENCE INTO ORDER",
         "what cannot be held together appears one after another")

def vis_now_slice(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    xs=[w*.16+i*w*.68/8 for i in range(9)]
    for i,x in enumerate(xs):
        glow_circle(im,x,y,10,[VIOLET,CYAN,GREEN,GOLD][i%4],130,7)
    now_x=lerp(xs[0],xs[-1],q)
    gl=layer(im.size)
    ImageDraw.Draw(gl).rectangle((now_x-24,h*.18,now_x+24,h*.64),fill=(*GOLD,55))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(15)))
    centered(d,(now_x,h*.70),"NOW",font(FONT_SERIF_BOLD,22),GOLD)
    seal(im,"THE PRESENT IS A MOVING WINDOW",
         "one phase is vivid while others become trace or anticipation")

def vis_past_trace(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    xs=[w*.18,w*.34,w*.50,w*.66,w*.82]
    for i,x in enumerate(xs):
        alpha=int(210*(1-i*.12)*(1-q*.55 if i<3 else 1))
        glow_circle(im,x,y,12,[VIOLET,CYAN,GREEN,CRIMSON,GOLD][i],alpha,8)
    glow_line(im,partial([(x,y) for x in xs],q),VIOLET,5,190,12)
    centered(d,(w*.34,h*.68),"TRACE",font(FONT_SERIF_BOLD,24),VIOLET)
    seal(im,"THE PAST SURVIVES AS DIFFERENCE",
         "memory is presence altered by what is no longer present")

def vis_future_open(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    origin=(w*.24,h*.40); q=ease(u)
    glow_circle(im,*origin,14,CYAN,170,10)
    branches=[]
    for k in range(7):
        pts=[origin]
        for i in range(1,5):
            x=origin[0]+i*w*.14
            y=origin[1]+math.sin(k*1.7+i*.8)*45*(i/4)
            pts.append((x,y))
        branches.append(pts)
    for i,pts in enumerate(branches):
        glow_line(im,partial(pts,q),[GOLD,VIOLET,GREEN][i%3],3,125,8)
    seal(im,"THE FUTURE IS A FIELD OF UNRESOLVED POSSIBILITIES",
         "anticipation narrows it before action makes one path actual")

def vis_desire_clock(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    d.ellipse((cx-135,cy-135,cx+135,cy+135),outline=(*INK,160),width=4)
    for i in range(12):
        a=i*math.tau/12-math.pi/2
        x1=cx+math.cos(a)*110; y1=cy+math.sin(a)*110
        x2=cx+math.cos(a)*128; y2=cy+math.sin(a)*128
        d.line((x1,y1,x2,y2),fill=(*INK,120),width=2)
    angle=lerp(-math.pi/2,math.pi*1.5,q)
    arrow(d,(cx,cy),(cx+math.cos(angle)*92,cy+math.sin(angle)*92),
          (*CRIMSON,190),5,10)
    glow_circle(im,cx+180,cy,14,GOLD,170,10)
    seal(im,"DESIRE MAKES TIME PRESS FORWARD",
         "the absent good turns succession into urgency")

def vis_fear_future(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    origin=(w*.30,h*.42); q=ease(u)
    draw_body(d,*origin,.58,INK,170)
    future=[(w*.58,h*.25),(w*.72,h*.42),(w*.62,h*.59),(w*.82,h*.28)]
    for x,y in future:
        glow_circle(im,x,y,11,CRIMSON,145,8)
        glow_line(im,partial([(origin[0]+35,origin[1]),(x,y)],q),
                  CRIMSON,3,135,8)
    cone=layer(im.size)
    ImageDraw.Draw(cone).polygon([
        (origin[0]+30,origin[1]),
        (w*.90,h*.15),
        (w*.90,h*.68),
    ],fill=(*CRIMSON,int(35*q)))
    im.alpha_composite(cone)
    seal(im,"FEAR COLONIZES THE FUTURE",
         "events that have not happened reorganize the present body")

def vis_boredom(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    xs=[w*.16+i*w*.68/10 for i in range(11)]
    for i,x in enumerate(xs):
        amp=lerp(30,4,q)
        yy=y+math.sin(i*.8+t)*amp
        glow_circle(im,x,yy,8,SILVER,110,6)
    centered(d,(w*.50,h*.68),"NOTHING CHANGES ENOUGH",
             font(FONT_SERIF_BOLD,23),SILVER)
    seal(im,"BOREDOM STRETCHES TIME",
         "succession remains while meaningful difference collapses")

def vis_flow_time(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    pts=[]
    for i in range(220):
        x=w*.12+i*w*.76/219
        y=h*.40+math.sin(i*.12+t*.8)*35
        pts.append((x,y))
    glow_line(im,partial(pts,q),CYAN,5,200,12)
    for i in range(12):
        x=w*.14+i*w*.72/11
        glow_circle(im,x,h*.40+math.sin(i*.9+t*.8)*35,6,GOLD,100,5)
    seal(im,"FLOW COMPRESSES TIME",
         "action, attention, and feedback become one continuous gesture")

def vis_memory_identity(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    xs=[w*.17,w*.33,w*.49,w*.65,w*.81]
    for i,x in enumerate(xs):
        glow_circle(im,x,y,12,[CYAN,VIOLET,GREEN,CRIMSON,GOLD][i],150,8)
    glow_line(im,partial([(x,y) for x in xs],q),GOLD,5,200,12)
    if q>.58:
        d.ellipse((w*.12,h*.26,w*.86,h*.54),outline=(*CRIMSON,180),width=4)
    seal(im,"MEMORY TURNS SEQUENCE INTO A PERSON",
         "separate moments become the history of one center")

def vis_language_tense(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    items=[
        ("WAS",VIOLET,w*.25),
        ("IS",GOLD,w*.50),
        ("WILL BE",CYAN,w*.75),
    ]
    q=ease(u)
    for i,(lab,col,x) in enumerate(items):
        glow_circle(im,x,h*.40,15,col,160,9)
        centered(d,(x,h*.67),lab,font(FONT_SERIF_BOLD,25),col)
        if i<len(items)-1:
            arrow(d,(x+18,h*.40),(items[i+1][2]-18,h*.40),
                  (*SILVER,int(150*q)),3,8)
    seal(im,"LANGUAGE HARDENS TEMPORAL DIFFERENCE",
         "tense converts changing availability into grammar")

def vis_clock_vs_lived(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    d.ellipse((left[0]-100,left[1]-100,left[0]+100,left[1]+100),
              outline=(*INK,170),width=4)
    angle=t*.7
    arrow(d,left,(left[0]+math.cos(angle)*70,left[1]+math.sin(angle)*70),
          (*INK,170),4,9)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"MEASURED TIME",font(FONT_SERIF_BOLD,21),INK)
    centered(d,(right[0],h*.68),"LIVED TIME",font(FONT_SERIF_BOLD,21),GOLD)
    seal(im,"CLOCK TIME AND LIVED TIME ARE NOT IDENTICAL",
         "one measures intervals; the other structures significance")

def vis_kanchuka_kala(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    for rr in range(40,260,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(70*(1-q*.35)*(1-rr/290))),width=3)
    line=[(w*.20,cy),(w*.80,cy)]
    glow_line(im,partial(line,q),CYAN,5,205,13)
    for i,x in enumerate([w*.28,w*.42,w*.56,w*.70]):
        glow_circle(im,x,cy,9,[VIOLET,GREEN,CRIMSON,GOLD][i],140,7)
    seal(im,"KĀLA CONTRACTS SIMULTANEITY INTO SUCCESSION",
         "the unlimited field appears as before, now, and after")

def vis_krama(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    xs=[w*.16+i*w*.68/8 for i in range(9)]
    for i,x in enumerate(xs):
        local=clamp(q*9-i)
        glow_circle(im,x,y,10,[GOLD,CYAN,VIOLET,GREEN][i%4],
                    int(100+90*local),7)
        if local>.55:
            centered(d,(x,y+28),str(i+1),font(FONT_SANS_BOLD,12),INK)
    glow_line(im,partial([(x,y) for x in xs],q),CYAN,4,180,10)
    seal(im,"KRAMA IS ORDERED APPEARANCE",
         "a finite knower receives manifestation phase by phase")

def vis_akrama(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    pts=event_field(w,h,36,21); q=ease(u)
    for i,(x,y) in enumerate(pts):
        glow_circle(im,x,y,8,[GOLD,CYAN,VIOLET,GREEN][i%4],140,7)
    for rr in range(40,285,32):
        d.ellipse((w*.50-rr,h*.40-rr*.60,w*.50+rr,h*.40+rr*.60),
                  outline=(*GOLD,int(65*q*(1-rr/315))),width=3)
    seal(im,"AKRAMA IS NON-SEQUENTIAL APPREHENSION",
         "not endless duration, but freedom from having to receive reality piece by piece")

def vis_flash(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    if q<.55:
        glow_circle(im,cx,cy,lerp(15,220,q/.55),GOLD,int(130+100*q),18)
    else:
        for rr in range(45,280,30):
            d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                      outline=(*GOLD,int(75*(1-(q-.55)/.45)*(1-rr/310))),width=3)
    seal(im,"SOME INSIGHT ARRIVES AS A FLASH",
         "the whole relation appears before discursive thought unfolds it")

def vis_music(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    pts=[]
    for i in range(240):
        x=w*.12+i*w*.76/239
        y=h*.40+math.sin(i*.15+t)*42+math.sin(i*.045)*18
        pts.append((x,y))
    glow_line(im,partial(pts,q),VIOLET,5,190,12)
    now_idx=int(q*(len(pts)-1))
    glow_circle(im,*pts[now_idx],12,GOLD,170,9)
    seal(im,"MUSIC PROVES THAT SEQUENCE CAN FORM A SINGLE WHOLE",
         "the present note carries retention of the past and anticipation of the next")

def vis_death_boundary(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    line=[(w*.15,y),(w*.78,y)]
    glow_line(im,partial(line,q),CYAN,5,190,12)
    d.line((w*.78,h*.20,w*.78,h*.62),fill=(*CRIMSON,190),width=5)
    centered(d,(w*.78,h*.68),"UNKNOWN LIMIT",font(FONT_SERIF_BOLD,20),CRIMSON)
    seal(im,"DEATH GIVES PERSONAL TIME AN EDGE",
         "finitude turns sequence into urgency, meaning, and unfinished possibility")

def vis_meditation_gap(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.68,INK,170)
    left=[(w*.20,cy),(w*.44,cy)]
    right=[(w*.56,cy),(w*.80,cy)]
    glow_line(im,partial(left,q),VIOLET,4,170,10)
    glow_line(im,partial(right,q),CYAN,4,170,10)
    glow_circle(im,cx,cy,15,GOLD,180,11)
    seal(im,"MEDITATION REVEALS THE GAP AROUND SEQUENCE",
         "thoughts arise one by one inside an awareness not itself segmented")

def vis_recognition(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.20,cy),(w*.80,cy)]
    glow_line(im,partial(line,q),CYAN,5,190,12)
    for rr in range(45,290,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(72*q*(1-rr/320))),width=3)
    glow_circle(im,cx,cy,15,GOLD,180,11)
    seal(im,"RECOGNITION DOES NOT STOP THE CLOCK",
         "it sees succession as one mode within a wider field of awareness")

def vis_science_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-90,left[0],left[0]+90]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
        if i<len(xs)-1:
            arrow(d,(x+14,left[1]),(xs[i+1]-14,left[1]),
                  (*SILVER,140),2,7)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"TEMPORAL INTEGRATION",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"FIELD OF APPEARING",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE STUDIES HOW SEQUENCE IS INTEGRATED",
         "ABHINAVA ASKS WHY EXPERIENCE MUST APPEAR SEQUENTIALLY AT ALL")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("CLOCKS MEASURE REAL PHYSICAL REGULARITIES","SUPPORTED",GREEN),
        ("LIVED TIME DEPENDS ON COGNITIVE STRUCTURE","SUPPORTED",CYAN),
        ("THE ABSOLUTE IS A PHYSICAL TIMELESS OBJECT","CATEGORY ERROR",CRIMSON),
        ("NEUROSCIENCE PROVES AKRAMA","NOT ESTABLISHED",CRIMSON),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DO NOT TURN METAPHYSICAL TIMELESSNESS INTO BAD PHYSICS",
         "the claim concerns modes of apprehension, not denial of measured change")

def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,5,195,12)
    for i,x in enumerate([w*.25,w*.40,w*.55,w*.70]):
        glow_circle(im,x,cy,10,[VIOLET,GREEN,CRIMSON,GOLD][i],140,7)
    for rr in range(45,300,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(72*q*(1-rr/330))),width=3)
    glow_circle(im,cx,cy,16,GOLD,185,12)
    if q>.72:
        centered(d,(cx,h*.68),"KRAMA WITHIN AKRAMA",
                 font(FONT_SERIF_BOLD,25),GOLD)
    seal(im,"TIME IS PRODUCED BY FORGETTING",
         "sequence appears when the whole field can no longer be held at once",GOLD)


VISUALS: dict[str,Callable] = {
    "all":vis_all_at_once,
    "exclude":vis_exclusion,
    "sequence":vis_sequence_birth,
    "now":vis_now_slice,
    "past":vis_past_trace,
    "future":vis_future_open,
    "desire":vis_desire_clock,
    "fear":vis_fear_future,
    "boredom":vis_boredom,
    "flow":vis_flow_time,
    "identity":vis_memory_identity,
    "tense":vis_language_tense,
    "clock":vis_clock_vs_lived,
    "kala":vis_kanchuka_kala,
    "krama":vis_krama,
    "akrama":vis_akrama,
    "flash":vis_flash,
    "music":vis_music,
    "death":vis_death_boundary,
    "meditation":vis_meditation_gap,
    "recognition":vis_recognition,
    "bridge":vis_science_bridge,
    "caution":vis_caution,
    "final":vis_final,
}


@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict


SCENES = [
    Scene("Without sequence",
          "Imagine a field in which difference appears without being divided into before and after.",
          9.0,"all",{}),
    Scene("No waiting",
          "Nothing must wait for something else to disappear before it can be known.",
          8.5,"all",{}),
    Scene("Whole field",
          "The whole relation is present in one act.",
          7.0,"all",{}),

    Scene("Finite attention",
          "Now introduce a finite center.",
          7.0,"exclude",{}),
    Scene("This not that",
          "To hold this clearly, it must let that become unavailable.",
          8.0,"exclude",{}),
    Scene("Exclusion",
          "Finite attention creates knowledge through exclusion.",
          8.0,"exclude",{}),

    Scene("Birth of sequence",
          "What cannot be held together appears one after another.",
          8.5,"sequence",{}),
    Scene("Order",
          "Difference becomes order.",
          6.0,"sequence",{}),
    Scene("Krama",
          "The tradition calls this sequential manifestation krama.",
          8.0,"krama",{}),

    Scene("Now",
          "One phase becomes vivid as now.",
          7.0,"now",{}),
    Scene("Past",
          "What has passed survives only through trace, retention, and memory.",
          8.5,"past",{}),
    Scene("Future",
          "What has not arrived appears as possibility, expectation, or threat.",
          9.0,"future",{}),

    Scene("Moving window",
          "The present is not a point standing still.",
          7.5,"now",{}),
    Scene("Window",
          "It is a moving window of availability.",
          7.5,"now",{}),
    Scene("Passage",
          "Passage is the continual reorganization of what can be held directly.",
          9.0,"now",{}),

    Scene("Memory",
          "The past is not simply annihilated.",
          7.5,"past",{}),
    Scene("Trace",
          "It remains as a difference in the present system.",
          8.0,"past",{}),
    Scene("Reconstruction",
          "Memory reconstructs what is no longer directly available.",
          8.5,"past",{}),

    Scene("Open future",
          "The future is not yet one thing.",
          7.0,"future",{}),
    Scene("Branches",
          "It is a branching field of possible actions and consequences.",
          8.5,"future",{}),
    Scene("Narrowing",
          "Prediction, desire, and fear narrow the branches before action selects one.",
          9.5,"future",{}),

    Scene("Desire",
          "Desire makes time point forward.",
          7.5,"desire",{}),
    Scene("Absent good",
          "An absent good reorganizes the present around what has not yet arrived.",
          9.0,"desire",{}),
    Scene("Urgency",
          "Sequence becomes urgency.",
          6.5,"desire",{}),

    Scene("Fear",
          "Fear performs the same operation in reverse valence.",
          8.0,"fear",{}),
    Scene("Future threat",
          "A possible future event changes posture, attention, memory, and action now.",
          9.5,"fear",{}),
    Scene("Colonized present",
          "The future colonizes the present before it exists as experience.",
          8.5,"fear",{}),

    Scene("Boredom",
          "Boredom stretches time.",
          6.5,"boredom",{}),
    Scene("Low difference",
          "Succession continues, but meaningful difference collapses.",
          8.0,"boredom",{}),
    Scene("Heavy duration",
          "The empty interval becomes heavy.",
          7.0,"boredom",{}),

    Scene("Flow",
          "Flow compresses time.",
          6.5,"flow",{}),
    Scene("Continuous gesture",
          "Attention, action, and feedback become one continuous gesture.",
          8.5,"flow",{}),
    Scene("Vanishing clock",
          "Measured duration continues while lived duration recedes.",
          8.0,"flow",{}),

    Scene("Identity",
          "Memory turns sequence into a person.",
          8.0,"identity",{}),
    Scene("One owner",
          "Different moments are assigned to one body, one name, one history.",
          9.0,"identity",{}),
    Scene("Personal time",
          "Time becomes my past and my future.",
          7.5,"identity",{}),

    Scene("Language",
          "Language stabilizes temporal difference.",
          8.0,"tense",{}),
    Scene("Tense",
          "Was, is, and will be become grammatical worlds.",
          8.0,"tense",{}),
    Scene("Narrative",
          "Narrative binds them into a direction.",
          7.5,"tense",{}),

    Scene("Two times",
          "Clock time and lived time must be distinguished.",
          8.0,"clock",{}),
    Scene("Measurement",
          "Clocks measure repeatable physical intervals.",
          8.0,"clock",{}),
    Scene("Experience",
          "Lived time measures urgency, boredom, anticipation, grief, rhythm, and meaning.",
          9.5,"clock",{}),

    Scene("Kāla",
          "Abhinavagupta places temporal limitation among the coverings of finite subjectivity.",
          9.5,"kala",{}),
    Scene("Contraction",
          "Kāla contracts unlimited presence into before, now, and after.",
          8.5,"kala",{}),
    Scene("Not illusion",
          "This does not make sequence unreal. It makes sequence perspectival.",
          8.5,"kala",{}),

    Scene("Krama",
          "Krama is ordered manifestation.",
          7.0,"krama",{}),
    Scene("Phase by phase",
          "A finite knower receives the field phase by phase.",
          8.0,"krama",{}),
    Scene("Cognitive necessity",
          "Sequence is the price of limited apprehension.",
          8.0,"krama",{}),

    Scene("Akrama",
          "Akrama does not mean an infinitely long present.",
          8.0,"akrama",{}),
    Scene("Not endless duration",
          "Endless duration would still be time.",
          7.0,"akrama",{}),
    Scene("Non-sequential",
          "Akrama means freedom from having to receive reality piece by piece.",
          9.0,"akrama",{}),

    Scene("Flash",
          "Some insight gives us a small analogy.",
          7.5,"flash",{}),
    Scene("Whole relation",
          "A relation appears in a flash before thought unfolds its implications.",
          8.5,"flash",{}),
    Scene("Discursive unpacking",
          "Discursive reason then converts the whole into sequence.",
          8.0,"flash",{}),

    Scene("Music",
          "Music offers another analogy.",
          7.0,"music",{}),
    Scene("Retention",
          "The present note carries retention of what has passed.",
          8.0,"music",{}),
    Scene("Anticipation",
          "It also carries anticipation of what may follow.",
          8.0,"music",{}),
    Scene("Whole phrase",
          "A temporal sequence becomes one meaningful phrase.",
          8.0,"music",{}),

    Scene("Death",
          "Death gives personal time an edge.",
          7.5,"death",{}),
    Scene("Limit",
          "Because the sequence may end, projects become urgent and choices become irreversible.",
          9.5,"death",{}),
    Scene("Meaning",
          "Finitude converts duration into meaning.",
          7.5,"death",{}),

    Scene("Meditation",
          "Meditation can expose the gap around sequence.",
          8.0,"meditation",{}),
    Scene("Thoughts",
          "Thoughts arise one after another.",
          7.0,"meditation",{}),
    Scene("Awareness",
          "But the awareness in which they arise is not itself chopped into thought-sized pieces.",
          9.5,"meditation",{}),

    Scene("Recognition",
          "Recognition does not stop clocks or abolish succession.",
          8.5,"recognition",{}),
    Scene("Wider field",
          "It sees succession as one mode within a wider field of consciousness.",
          8.5,"recognition",{}),
    Scene("Krama in akrama",
          "Krama appears within akrama.",
          7.0,"recognition",{}),

    Scene("Science",
          "Modern science studies temporal integration.",
          8.0,"bridge",{}),
    Scene("Mechanisms",
          "Memory, prediction, neural oscillation, interoception, and action help construct lived succession.",
          9.5,"bridge",{}),
    Scene("Prior question",
          "Abhinavagupta asks the prior question: why must a finite subject receive manifestation sequentially at all?",
          10.0,"bridge",{}),

    Scene("Discipline",
          "The comparison must remain disciplined.",
          7.0,"caution",{}),
    Scene("No denial",
          "Physical change and clock measurement are not denied.",
          7.5,"caution",{}),
    Scene("Different claim",
          "The claim concerns the structure of apprehension, not a rejection of physics.",
          8.5,"caution",{}),

    Scene("Return",
          "Return to the timeline.",
          6.5,"final",{}),
    Scene("Reveal",
          "Past, present, and future remain visible.",
          7.0,"final",{}),
    Scene("Field",
          "But the timeline itself now appears inside a wider field.",
          8.5,"final",{}),
    Scene("Closing",
          "Time is produced by forgetting: sequence appears when the whole field can no longer be held at once, and liberation begins when succession is recognized as a mode of awareness rather than its final boundary.",
          10.0,"final",{}),
]


def render_frame(scene,frame_index,frame_count,width,height,seed):
    u=frame_index/max(1,frame_count-1)
    t=u*scene.duration
    im=field(width,height,seed)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im)
    return im.convert("RGB")

def ffmpeg_path():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg is required but was not found on PATH")
    return exe

def encode_scene(index,fps):
    frame_dir=FRAMES/f"scene_{index:03d}"
    output=SCENES_DIR/f"scene_{index:03d}.mp4"
    subprocess.run([
        ffmpeg_path(),"-y",
        "-framerate",str(fps),
        "-i",str(frame_dir/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(output),
    ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output

def render_scene(index,scene,fps,width,height,preview):
    frame_dir=FRAMES/f"scene_{index:03d}"
    frame_dir.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    count=max(2,round(scene.duration*fps))

    if preview:
        for oi,fi in enumerate([0,int(count*.33),int(count*.72),count-1]):
            render_frame(scene,fi,count,width,height,index*10000+fi).save(
                frame_dir/f"preview_{oi:02d}.jpg",quality=95
            )
        return frame_dir

    for fi in range(count):
        p=frame_dir/f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(scene,fi,count,width,height,index*10000+fi).save(
                p,quality=95,subsampling=0
            )
    return encode_scene(index,fps)

def concatenate(paths):
    txt=OUTPUT/"concat.txt"
    txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    output=OUTPUT/"time_is_produced_by_forgetting.mp4"
    subprocess.run([
        ffmpeg_path(),"-y","-f","concat","-safe","0",
        "-i",str(txt),"-c","copy","-movflags","+faststart",str(output),
    ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output

def export_timeline():
    cursor=0.0; records=[]
    for index,scene in enumerate(SCENES,1):
        rec=asdict(scene)
        rec["scene_id"]=f"scene_{index:03d}"
        rec["start_seconds"]=round(cursor,3)
        cursor+=scene.duration
        rec["end_seconds"]=round(cursor,3)
        records.append(rec)

    path=OUTPUT/"narration_timeline.json"
    path.write_text(json.dumps({
        "title":"time is produced by forgetting",
        "subtitle":"Abhinavagupta on sequence, contraction, and temporal experience",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"gold simultaneous field narrowing into cyan timeline",
        "visual_arc":[
            "simultaneity","exclusion","sequence","memory","anticipation",
            "personal time","krama","akrama","recognition"
        ],
        "scenes":records,
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return path

def make_contact_sheet(width,height):
    tw=320; th=int(tw*height/width); cols=4
    rows=math.ceil(len(SCENES)/cols); cell_h=th+48
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),IVORY)
    d=ImageDraw.Draw(sheet); lf=font(FONT_SANS_BOLD,14)
    for index,scene in enumerate(SCENES,1):
        count=max(2,round(scene.duration*DEFAULT_FPS))
        image=render_frame(scene,int(count*.72),count,width,height,index*10000+72)
        image.thumbnail((tw,th))
        slot=index-1; x=(slot%cols)*tw; y=(slot//cols)*cell_h
        sheet.paste(image,(x,y))
        d.text((x+8,y+th+7),f"{index:02d}  {scene.title}",font=lf,fill=INK)
    path=OUTPUT/"contact_sheet.jpg"
    sheet.save(path,quality=94)
    return path

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
    args=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    FRAMES.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)

    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")

    if args.scene:
        if not 1<=args.scene<=len(SCENES):
            raise ValueError("scene out of range")
        print(render_scene(
            args.scene,SCENES[args.scene-1],
            args.fps,args.width,args.height,args.preview
        ))
        return

    rendered=[]
    for index,scene in enumerate(SCENES,1):
        print(f"[{index:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        result=render_scene(
            index,scene,args.fps,args.width,args.height,args.preview
        )
        if not args.preview:
            rendered.append(result)

    if not args.no_contact_sheet:
        print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")

    if not args.preview:
        print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
