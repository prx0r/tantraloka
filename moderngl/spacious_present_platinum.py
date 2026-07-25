#!/usr/bin/env python3
"""
ALL TIME IS NOW — The Spacious Present Where Past, Present, and Future Coexist
Silver and Seth on the simultaneity of experience.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Ordinary consciousness experiences time as a line: past behind, future ahead,
present as a knife-edge. But the spacious present is not a point. It is a field.
All moments coexist. The past is not annihilated. The future is not unreal.
The present is a moving window of attention on a landscape that contains everything.

For Seth and for Silver, reincarnation is not a chain. It is a landscape.
You live all your lives at once. What appears as succession is a limitation
of focused awareness.

FILM THESIS
-----------
The modern picture often runs:

time → events → sequence → memory → identity

The spacious-present picture can be staged as:

eternal field
→ multiple moments coexisting
→ attention selects a sequence
→ the present reorganizes the past
→ probable futures
→ simultaneous selves
→ all time is now

Time is not a container. It is a function of attention.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a spiral threading all moments.
• Final reveal: the spiral has no end — every moment contains every other.

OUTPUT
------
output_spacious_present/
  frames/
  scenes/
  spacious_present.mp4
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
OUTPUT = ROOT / "output_spacious_present"
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
PALE_VIOLET=(218,208,235)

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

def spiral_points(cx,cy,max_r,turns,samples=120):
    pts=[]
    for i in range(samples):
        q=i/(samples-1)
        r=max_r*q
        a=q*math.tau*turns
        x=cx+math.cos(a)*r
        y=cy+math.sin(a)*r*.45
        pts.append((x,y))
    return pts

def event_field(w,h,count=36,seed=0):
    rng=random.Random(seed)
    return [(rng.uniform(w*.16,w*.84),rng.uniform(h*.20,h*.62)) for _ in range(count)]


# =============================================================================
# VISUALS
# =============================================================================

def vis_field_all(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,160,4,160)
    glow_line(im,partial(sp,q),GOLD,4,220,14)
    pts=event_field(w,h,35,1)
    for i,(x,y) in enumerate(pts):
        col=[GOLD,CYAN,VIOLET,GREEN][i%4]
        glow_circle(im,x,y,7+3*q,col,int(100+70*q),6)
    seal(im,"IMAGINE A FIELD WITH NO BEFORE OR AFTER",
         "all moments coexist — time is a landscape, not a line")

def vis_clock_convention(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,180,3+2*q,140)
    glow_line(im,partial(sp,q),GOLD,3,200,10)
    for i in range(12):
        a=i*math.tau/12-math.pi/2+t*.08
        x=cx+math.cos(a)*(60+40*q)
        y=cy+math.sin(a)*(60+40*q)*.45
        d.line((cx,cy,x,y),fill=(*CRIMSON,int(150*q)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*q),12)
    seal(im,"CLOCK TIME IS A CONVENTION",
         "the brain parses sequence from an atemporal field")

def vis_psychological(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.42,h*.40; cx2,cy2=w*.68,h*.40; q=ease(u)
    sp1=spiral_points(cx,cy,60+40*q,2+q,80)
    sp2=spiral_points(cx2,cy2,60+40*q,2+q,80)
    glow_line(im,partial(sp1,q),VIOLET,3,190,9)
    glow_line(im,partial(sp2,q),CYAN,3,190,9)
    glow_circle(im,cx,cy,12,VIOLET,int(160*q),10)
    glow_circle(im,cx2,cy2,12,CYAN,int(160*q),10)
    if q>.5:
        pts=[]
        for i in range(60):
            f=i/59
            x=lerp(cx+50,cx2-50,f)
            y=lerp(cy,cy2,f)+math.sin(f*math.tau*3-t*2)*20
            pts.append((x,y))
        glow_line(im,partial(pts,(q-.5)*2),GOLD,3,180,8)
    seal(im,"PSYCHOLOGICAL TIME",
         "felt duration — the second inner sense, measured by meaning, not clocks")

def vis_dreams(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,160,4,160)
    glow_line(im,partial(sp,q),GOLD,3,190,12)
    for i in range(20):
        a=i*math.tau/20+t*.12
        rad=40+30*math.sin(a*2+t)
        x=cx+math.cos(a)*rad*(.6+.4*q)
        y=cy+math.sin(a)*rad*.4
        glow_circle(im,x,y,6+4*q,PALE_GOLD,int(120*q),6)
    seal(im,"IN DREAMS YOU KNOW",
         "beginning and end at once — the spacious present revealed in sleep")

def vis_coexist(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    layers=5
    for i in range(layers):
        qc=clamp(q*layers-i)
        if qc<=0: continue
        rad=40+i*30
        col=mix(GOLD,VIOLET,i/(layers-1))
        sp=spiral_points(cx,cy,rad,1.5+i*.5,80)
        glow_line(im,partial(sp,qc),col,width=2+i,alpha=int(180*qc),blur=8+i*2)
    seal(im,"ALL MOMENTS COEXIST",
         "past, present, future are regions of the same landscape")

def vis_simultaneous(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,140,3.5,150)
    glow_line(im,partial(sp,q),GOLD,4,220,14)
    branches=8
    for i in range(branches):
        a=i*math.tau/branches+t*.05
        qc=clamp(q*2-i*.15)
        if qc<=0: continue
        x=cx+math.cos(a)*(50+80*qc)
        y=cy+math.sin(a)*(50+80*qc)*.4
        d.line((cx,cy,x,y),fill=(*GOLD,int(180*qc)),width=2)
        glow_circle(im,x,y,6,PALE_GOLD,int(140*qc),6)
    seal(im,"ALL LIVES ARE SIMULTANEOUS",
         "reincarnation is a landscape — you live all lives at once")

def vis_present_brings_past(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.30,h*.40; cx2,cy2=w*.70,h*.40; q=ease(u)
    sp1=spiral_points(cx,cy,50+40*q,2.5,80)
    sp2=spiral_points(cx2,cy2,50+40*q,2.5,80)
    glow_line(im,partial(sp1,q),CRIMSON,3,180,9)
    glow_line(im,partial(sp2,q),GOLD,3,180,9)
    if q>.3:
        for j in range(3):
            pts=[]
            off=j*30
            for i in range(60):
                f=i/59
                x=lerp(cx+60,cx2-60,f)
                y=lerp(cy,cy2,f)+math.sin(f*math.tau*2+t+off*.1)*30
                pts.append((x,y))
            glow_line(im,partial(pts,(q-.3)*1.4),
                      mix(CRIMSON,GOLD,.5+.5*math.sin(t+j)),
                      width=2,alpha=int(160*(q-.3)*1.4),blur=7)
    seal(im,"EACH PRESENT BRINGS ITS PAST",
         "the past changes with the present — memory is alive and creative")

def vis_probable_futures(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,120,3,120)
    glow_line(im,partial(sp,q),GOLD,3,200,12)
    futures=7
    for i in range(futures):
        a=i*math.tau/futures+t*.06
        qc=clamp(q*2.5-i*.12)
        if qc<=0: continue
        x=cx+math.cos(a)*(70+100*qc)
        y=cy+math.sin(a)*(70+100*qc)*.4
        col=mix(CYAN,VIOLET,i/futures)
        d.line((cx,cy,x,y),fill=(*col,int(170*qc)),width=2)
        glow_circle(im,x,y,7,col,int(150*qc),8)
    seal(im,"PROBABLE FUTURES",
         "all possible futures exist now — attention selects one into experience")

def vis_eternal_now(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,200,5,200)
    glow_line(im,partial(sp,q),GOLD,5,230,16)
    pulse_r=30+20*math.sin(t*1.5)
    glow_circle(im,cx,cy,pulse_r,VIOLET,int(180*q),14)
    glow_circle(im,cx,cy,12,GOLD,int(200*q),8)
    if q>.5:
        rng=random.Random(42)
        for _ in range(40):
            a=rng.uniform(0,math.tau)
            rad=rng.uniform(60,180)*clamp((q-.5)*2)
            x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
            sz=rng.uniform(2,5)
            d.ellipse((x-sz,y-sz,x+sz,y+sz),fill=(*PALE_GOLD,int(200*(q-.5)*2)))
    seal(im,"THE ETERNAL NOW",
         "when you remember everything, time ceases — all that ever was is present")

def vis_self_remember(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,150,4,150)
    glow_line(im,partial(sp,q),GOLD,3,200,12)
    for i in range(3):
        off=i*math.tau/3
        a=off+t*.08
        rad=50+30*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        col=[CYAN,GREEN,VIOLET][i]
        glow_circle(im,x,y,12,col,int(180*q),10)
        d.line((cx,cy,x,y),fill=(*mix(GOLD,col,.5),int(160*q)),width=2)
    seal(im,"REMEMBERING YOURSELF",
         "the observer who watches all moments is the spacious present itself")

def vis_attention_creates(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,100,2.5,100)
    glow_line(im,partial(sp,q),GOLD,3,200,10)
    foci=[(cx-70,cy-40),(cx+60,cy+30),(cx-30,cy+50),(cx+50,cy-50)]
    for i,(fx,fy) in enumerate(foci):
        qc=clamp(q*4-i*.18)
        if qc<=0: continue
        glow_circle(im,fx,fy,8+6*qc,CYAN,int(180*qc),9)
        d.line((cx,cy,fx,fy),fill=(*CYAN,int(150*qc)),width=2)
    seal(im,"ATTENTION CREATES TIME",
         "where you place attention, a moment unfolds")

def vis_duration(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left,right=w*.12,w*.88; y=h*.40; q=ease(u)
    sp=spiral_points(w*.50,y,60,1.5,60)
    glow_line(im,partial(sp,q),GOLD,3,180,8)
    for i in range(10):
        qc=clamp(q*10-i)
        if qc<=0: continue
        x=lerp(left,right,i/9)
        ht=80+60*math.sin(i*1.3)
        d.line((x,y-ht*qc,x,y+ht*qc),fill=(*GOLD,int(180*qc)),width=3)
        glow_circle(im,x,y-ht*qc,5,PALE_GOLD,int(100*qc),5)
        glow_circle(im,x,y+ht*qc,5,PALE_GOLD,int(100*qc),5)
    seal(im,"DURATION IS NOT TIME",
         "the felt length of a moment — attention's signature on experience")

def vis_narrative(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,130,3,130)
    glow_line(im,partial(sp,q),GOLD,3,200,10)
    for i in range(8):
        a=i*math.tau/8+t*.05
        qc=clamp(q*3-i*.12)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+60*qc)
        y=cy+math.sin(a)*(30+60*qc)*.35
        d.line((cx,cy,x,y),fill=(*CRIMSON,int(160*qc)),width=2)
        d.ellipse((x-12*qc,y-12*qc,x+12*qc,y+12*qc),
                  outline=(*CRIMSON,int(180*qc)),width=2)
    seal(im,"NARRATIVE IS LINEAR",
         "the brain strings moments into story — forgetting the spiral beneath")

def vis_simultaneous_self(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,170,4.5,180)
    glow_line(im,partial(sp,q),GOLD,4,220,14)
    for i in range(5):
        qc=clamp(q*5-i)
        if qc<=0: continue
        off_x=(i-2)*w*.12
        off_y=(i%3-1)*80*qc
        x=cx+off_x; y=cy+off_y
        col=mix(VIOLET,CYAN,i/4)
        glow_circle(im,x,y,14,col,int(180*qc),10)
        d.ellipse((x-30*qc,y-30*qc,x+30*qc,y+30*qc),
                  outline=(*col,int(120*qc)),width=2)
    seal(im,"THE SIMULTANEOUS SELF",
         "you are not one self — a field of selves in ongoing dialogue")

def vis_threshold(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,160,3.5,150)
    glow_line(im,partial(sp,q),GOLD,3,210,12)
    reveal=smoothstep(.2,.8,q)
    if reveal>0:
        for i in range(3):
            a=i*math.tau/3+t*.1
            x=cx+math.cos(a)*(80+60*reveal)
            y=cy+math.sin(a)*(80+60*reveal)*.4
            glow_circle(im,x,y,10+8*reveal,CRIMSON,int(170*reveal),9)
            d.line((cx,cy,x,y),fill=(*CRIMSON,int(150*reveal)),width=2)
    seal(im,"THE THRESHOLD MOMENT",
         "when linear time pauses — the spacious present opens")

def vis_recall(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cy=h*.40; q=ease(u)
    sp=spiral_points(w*.50,cy,100,2,100)
    glow_line(im,partial(sp,q),GOLD,3,190,10)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        x=lerp(w*.15,w*.85,i/5)
        y=cy+math.sin(i*1.2+t)*40*qc
        col=mix(PALE_GOLD,GOLD,.5+.5*math.sin(i))
        glow_circle(im,x,y,8,col,int(170*qc),7)
        d.ellipse((x-18*qc,y-18*qc,x+18*qc,y+18*qc),
                  outline=(*col,int(100*qc)),width=1)
    seal(im,"RECALL IS ACTIVE",
         "memory is not storage — it is creation in the present")

def vis_spacious_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    sp=spiral_points(cx,cy,220,6,240)
    glow_line(im,partial(sp,q),GOLD,6,240,18)
    for i in range(20):
        a=i*math.tau/20+t*.04
        rad=40+100*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.38
        sz=4+3*math.sin(a*3+t)
        glow_circle(im,x,y,sz,mix(PALE_GOLD,GOLD,.5),int(150*q),6)
    if q>.7:
        qc=(q-.7)/.3
        centered(d,(cx,cy),"∞",font(FONT_SERIF_BOLD,int(h*.12)),(*GOLD,int(200*qc)))
    seal(im,"ALL TIME IS NOW",
         "the spiral contains every moment — you are the spacious present")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"SIMULTANEITY RESEARCH",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"SPACIOUS PRESENT",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"PHYSICS CONFIRMS — ALL MOMENTS EXIST",
         "the block universe is the physics of the spacious present")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("THE BLOCK UNIVERSE IS NOT SPIRITUAL","IT IS A MATHEMATICAL MODEL",CRIMSON),
        ("ALL MOMENTS COEXISTING IS CONSISTENT WITH RELATIVITY","SUPPORTED",GREEN),
        ("TIME TRAVEL IS IMPLIED","NOT SUPPORTED",CRIMSON),
        ("ATTENTION CREATES SEQUENCE","SUPPORTED BY COGNITIVE SCIENCE",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DO NOT CONFLATE PHYSICS AND METAPHYSICS",
         "the block universe describes spacetime — the spacious present describes experience")


VISUALS: dict[str,Callable] = {
    "field":vis_field_all,
    "clock":vis_clock_convention,
    "psychological":vis_psychological,
    "dreams":vis_dreams,
    "coexist":vis_coexist,
    "simultaneous":vis_simultaneous,
    "present_brings_past":vis_present_brings_past,
    "probable_futures":vis_probable_futures,
    "eternal_now":vis_eternal_now,
    "self_remember":vis_self_remember,
    "attention":vis_attention_creates,
    "duration":vis_duration,
    "narrative":vis_narrative,
    "simultaneous_self":vis_simultaneous_self,
    "threshold":vis_threshold,
    "recall":vis_recall,
    "spacious_final":vis_spacious_final,
    "bridge":vis_bridge,
    "caution":vis_caution,
}


@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict


SCENES = [
    Scene("Without Sequence",
          "Imagine a field in which all moments coexist — nothing waits for something else to disappear.",
          9.0,"field",{}),
    Scene("The Spacious Present",
          "The present is not a knife-edge. It is a field of simultaneous experience.",
          8.5,"field",{}),
    Scene("No Waiting",
          "Nothing must wait for something else to disappear before it can be known.",
          8.0,"field",{}),

    Scene("Clock Time is a Convention",
          "The brain parses sequence from an atemporal field. Clocks measure convention, not reality.",
          8.5,"clock",{}),
    Scene("The Mechanical Tick",
          "The clock divides what is undivided. Its ticking is not a property of time.",
          8.0,"clock",{}),
    Scene("Convenient Fiction",
          "Clock time is useful. It is also not fundamental.",
          7.5,"clock",{}),

    Scene("Psychological Time",
          "Felt duration — the second inner sense. Not measured but lived.",
          8.5,"psychological",{}),
    Scene("Two Times",
          "Clock time and psychological time are not the same. One is measured, the other felt.",
          8.5,"psychological",{}),
    Scene("The Texture of Duration",
          "A moment of pain is long. A moment of joy is short. The content shapes the experience.",
          8.5,"psychological",{}),

    Scene("In Dreams You Know",
          "In sleep, the spacious present reveals itself. Beginning and end at once.",
          8.5,"dreams",{}),
    Scene("Dream Time",
          "Dreams compress years into seconds. This is not distortion — it is direct experience.",
          8.5,"dreams",{}),
    Scene("The Nightly Reminder",
          "Every night, you enter a state where sequence dissolves. You just forget by morning.",
          8.0,"dreams",{}),

    Scene("All Moments Coexist",
          "Past, present, and future are regions of the same landscape.",
          9.0,"coexist",{}),
    Scene("The Landscape of Time",
          "The past is not behind you. It is spread beside you like a terrain.",
          8.5,"coexist",{}),
    Scene("Every When is Now",
          "From the perspective of the field, every moment is equally present.",
          8.5,"coexist",{}),

    Scene("All Lives are Simultaneous",
          "Reincarnation is not a chain. You live all lives at once.",
          9.0,"simultaneous",{}),
    Scene("The Life Landscape",
          "Each life is a region of the same field. You are living them all right now.",
          9.0,"simultaneous",{}),
    Scene("No Past Lives",
          "There are no past lives. There are only other lives — equally present.",
          8.5,"simultaneous",{}),

    Scene("Each Present Brings Its Past",
          "The past is not fixed. Each present reorganizes memory.",
          8.5,"present_brings_past",{}),
    Scene("The Past is Plastic",
          "Memory is a creative act in the now. The past changes with the present.",
          8.5,"present_brings_past",{}),
    Scene("Retroactive Creation",
          "What happened is not settled. The present rewrites the past.",
          8.5,"present_brings_past",{}),

    Scene("Probable Futures",
          "All possible futures exist now. Attention selects one into experience.",
          8.5,"probable_futures",{}),
    Scene("The Forking Field",
          "Every moment is a node of infinite branches. You walk one, but all are real.",
          9.0,"probable_futures",{}),
    Scene("Choice is Selection",
          "Choice is not creation ex nihilo. It is selection from what already exists.",
          8.5,"probable_futures",{}),

    Scene("The Eternal Now",
          "When you remember everything, time ceases. All that ever was is present.",
          9.5,"eternal_now",{}),
    Scene("Timeless Awareness",
          "The witness of time is not in time. It is the field in which time appears.",
          9.0,"eternal_now",{}),
    Scene("The Still Point",
          "At the center of the spiral, there is no movement. There is only the watching.",
          9.0,"eternal_now",{}),

    Scene("Remembering Yourself",
          "The observer who watches all moments is the spacious present itself.",
          8.5,"self_remember",{}),
    Scene("The Witness",
          "Who watches the passage of time is not in time. Who remembers is the timeless.",
          9.0,"self_remember",{}),
    Scene("The Observer",
          "The observer of all moments cannot be found among the moments.",
          8.5,"self_remember",{}),

    Scene("Attention Creates Time",
          "Where you place attention, a moment unfolds. Time is a function of awareness.",
          8.5,"attention",{}),
    Scene("The Spotlight",
          "Attention is a spotlight on the field. The rest does not disappear — it becomes unavailable.",
          8.5,"attention",{}),
    Scene("Narrowing the Field",
          "The spacious present narrows to a single thread when you focus.",
          8.0,"attention",{}),

    Scene("Duration is Not Time",
          "The felt length of a moment has nothing to do with the clock — it is attention's signature.",
          8.5,"duration",{}),
    Scene("The Elastic Moment",
          "A moment can stretch or compress depending on what it contains.",
          8.0,"duration",{}),
    Scene("Content Shapes Time",
          "Boredom stretches. Flow compresses. The content of experience shapes the experience of time.",
          8.5,"duration",{}),

    Scene("Narrative is Linear",
          "The brain strings moments into a story. It forgets the spiral beneath.",
          8.5,"narrative",{}),
    Scene("The Storyteller",
          "Narrative is the brain's way of making the field navigable. But the story is not the field.",
          8.5,"narrative",{}),
    Scene("Beyond the Story",
          "When you see through the story, the spiral reveals itself.",
          8.5,"narrative",{}),

    Scene("The Simultaneous Self",
          "You are not one self — a field of selves in ongoing dialogue.",
          9.0,"simultaneous_self",{}),
    Scene("The Self Field",
          "Each 'you' is a probability that became actual. The others are still there.",
          9.0,"simultaneous_self",{}),
    Scene("Inner Multiplicity",
          "The voices in your head are not pathology. They are the field manifesting.",
          8.5,"simultaneous_self",{}),

    Scene("The Threshold Moment",
          "When linear time pauses — in crisis, awe, or love — the spacious present opens.",
          8.5,"threshold",{}),
    Scene("The Crack Between Worlds",
          "These moments are not anomalies. They are glimpses of what is always the case.",
          8.5,"threshold",{}),
    Scene("Aperture",
          "The threshold is not a place. It is the dissolution of the attention that creates sequence.",
          8.5,"threshold",{}),

    Scene("Recall is Active",
          "Memory is not storage. It is a creative act performed in the present.",
          8.5,"recall",{}),
    Scene("The Creative Past",
          "Every act of recall changes what is recalled. The past is reborn each time.",
          8.5,"recall",{}),
    Scene("Memory is Now",
          "You do not remember the past. You construct it in the present.",
          8.0,"recall",{}),

    Scene("Science Bridge",
          "The block universe of special relativity describes a world where all moments coexist.",
          9.0,"bridge",{}),
    Scene("Einstein's Insight",
          "The distinction between past, present, and future is a stubbornly persistent illusion.",
          9.0,"bridge",{}),
    Scene("Prior Question",
          "If all moments coexist, why do we experience succession? The answer concerns attention.",
          9.5,"bridge",{}),

    Scene("Caution",
          "The block universe is a mathematical model. The spacious present is an experiential reality.",
          8.5,"caution",{}),
    Scene("Not Time Travel",
          "All moments coexisting does not imply time travel. It implies that location is relative.",
          8.5,"caution",{}),
    Scene("Different Claim",
          "The claim concerns modes of apprehension, not a literal model of physics.",
          8.5,"caution",{}),

    Scene("Return",
          "Return to the spiral. All moments are here.",
          8.0,"spacious_final",{}),
    Scene("Reveal",
          "The spiral has no end. Every moment contains every other.",
          8.5,"spacious_final",{}),
    Scene("Field",
          "The timeline of your life is inside a field that contains all timelines.",
          9.0,"spacious_final",{}),
    Scene("Closing",
          "All time is now. The spacious present is not a concept — it is what remains when attention stops contracting. Sequence appears when awareness narrows, and the whole field is what is always present when it does not.",
          10.0,"spacious_final",{}),
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
                frame_dir/f"preview_{oi:02d}.jpg",quality=95)
        return frame_dir
    for fi in range(count):
        p=frame_dir/f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(scene,fi,count,width,height,index*10000+fi).save(
                p,quality=95,subsampling=0)
    return encode_scene(index,fps)

def concatenate(paths):
    txt=OUTPUT/"concat.txt"
    txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    output=OUTPUT/"spacious_present.mp4"
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
        "title":"all time is now",
        "subtitle":"the spacious present where past, present, and future coexist",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"spiral threading all moments",
        "visual_arc":[
            "field","clock","psychological","dreams","coexistence",
            "probable futures","eternal now","simultaneous self","recognition"
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
        print(render_scene(args.scene,SCENES[args.scene-1],
              args.fps,args.width,args.height,args.preview))
        return
    rendered=[]
    for index,scene in enumerate(SCENES,1):
        print(f"[{index:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        result=render_scene(index,scene,args.fps,args.width,args.height,args.preview)
        if not args.preview:
            rendered.append(result)
    if not args.no_contact_sheet:
        print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview:
        print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
