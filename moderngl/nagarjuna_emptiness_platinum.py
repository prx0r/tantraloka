#!/usr/bin/env python3
"""
EVERYTHING IS EMPTY OF INHERENT EXISTENCE
Nāgārjuna's Mūlamadhyamakakārikā on dependent arising and the middle way.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
All phenomena are empty (śūnya) of inherent existence (svabhāva) because
they arise dependently (pratītyasamutpāda). Nothing exists independently.
Nothing exists from its own side. This is not nihilism — it is the middle
way between eternalism and annihilationism.

Emptiness itself is empty. The very concept of emptiness must be relinquished.

FILM THESIS
-----------
The modern picture often runs:

things exist independently
→ they are real
→ they are permanent or they are nothing

The Mādhyamaka picture can be staged as:

things arise dependently
→ they are empty
→ emptiness is not nothing — it is the absence of inherent existence
→ emptiness itself is empty
→ freedom from all views
→ the middle way

The goal is not to believe in emptiness. It is to see through the illusion
of inherent existence.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a net of interdependent threads — no thread stands alone.
• Final reveal: the net has no center, no edge, and no weaver.

OUTPUT
------
output_nagarjuna_emptiness/
  frames/
  scenes/
  nagarjuna_emptiness.mp4
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
OUTPUT = ROOT / "output_nagarjuna_emptiness"
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

def dependency_net(w,h,n=30,seed=0):
    rng=random.Random(seed)
    return [(rng.uniform(w*.14,w*.86),rng.uniform(h*.16,h*.66)) for _ in range(n)]


# =============================================================================
# VISUALS
# =============================================================================

def vis_sunyata(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=dependency_net(w,h,36,1)
    for i,(x,y) in enumerate(pts):
        col=[GOLD,CYAN,VIOLET][i%3]
        glow_circle(im,x,y,8+3*q,col,int(110+70*q),7)
    for rr in range(45,260,30):
        d.ellipse((w*.50-rr,cy-rr*.60,w*.50+rr,cy+rr*.60),
                  outline=(*GOLD,int(60*q*(1-rr/290))),width=3)
    seal(im,"ŚŪNYATĀ — EMPTINESS",
         "not nothing — empty of inherent existence, full of dependent arising")

def vis_dependent_arising(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=dependency_net(w,h,25,3)
    for i,(x,y) in enumerate(pts):
        col=[CYAN,GOLD,GREEN][i%3]
        glow_circle(im,x,y,7+3*q,col,int(130+50*q),7)
    for i in range(len(pts)):
        for j in range(i+1,len(pts)):
            if random.Random(i*100+j).random()<.25*q:
                d.line((*pts[i],*pts[j]),fill=(*CYAN,int(40*q)),width=1)
    seal(im,"PRATĪTYASAMUTPĀDA",
         "dependent arising — when this is, that is; when this is not, that is not")

def vis_middle_way(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.12,cy),(w*.88,cy)]
    glow_line(im,partial(line,q),GOLD,5,200,12)
    centered(d,(w*.20,cy-30),"ETERNALISM",font(FONT_SANS_BOLD,14),CRIMSON)
    centered(d,(w*.80,cy-30),"NIHILISM",font(FONT_SANS_BOLD,14),CRIMSON)
    centered(d,(cx,cy+30),"MIDDLE WAY",font(FONT_SERIF_BOLD,22),GOLD)
    glow_circle(im,cx,cy,12,GOLD,int(200*q),10)
    seal(im,"THE MIDDLE WAY",
         "not existence, not non-existence — free from both extremes")

def vis_four_cornered(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    corners=[
        ("EXISTS",cx-80,cy-50),
        ("NOT EXISTS",cx+80,cy-50),
        ("BOTH",cx-80,cy+50),
        ("NEITHER",cx+80,cy+50),
    ]
    for i,(lab,x,y) in enumerate(corners):
        qc=clamp(q*4-i*.10)
        if qc<=0: continue
        d.rounded_rectangle((x-55,y-18,x+55,y+18),radius=10,
                            fill=(*mix(WHITE,CRIMSON,.08),int(200*qc)),
                            outline=(*CRIMSON,int(160*qc)),width=2)
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,14),CRIMSON)
    arrow(d,(cx,cy-20),(cx,cy+20),GOLD,2,8)
    seal(im,"THE FOUR-CORNERED NEGATION",
         "it is not the case that X exists, does not exist, both, or neither")

def vis_eight_negations(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    negations=[
        ("NOT ONE",-1),("NOT MANY",-0.7),("NOT COMING",-0.3),("NOT GOING",0),
        ("NOT THE SAME",0.3),("NOT DIFFERENT",0.7),("NOT PERMANENT",-0.5),("NOT ANNIHILATED",0.5),
    ]
    glow_circle(im,cx,cy,14,GOLD,int(190*q),10)
    for i,(lab,_) in enumerate(negations):
        a=i*math.tau/len(negations)-math.pi/2+t*.04
        rad=40+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        qc=clamp(q*len(negations)-i*.08)
        if qc<=0: continue
        d.line((cx,cy,x,y),fill=(*PALE_GOLD,int(120*qc)),width=1)
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,11),PALE_GOLD)
    seal(im,"THE EIGHT NEGATIONS",
         "Nāgārjuna's famous opening: no arising, no ceasing, no permanence, no annihilation...")

def vis_two_truths(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    left=(w*.30,cy); right=(w*.70,cy)
    for rr in range(30,160,25):
        d.ellipse((left[0]-rr,left[1]-rr*.62,left[0]+rr,left[1]+rr*.62),
                  outline=(*SILVER,int(55*q*(1-rr/180))),width=3)
    for rr in range(30,180,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(65*q*(1-rr/200))),width=3)
    glow_circle(im,*left,12,SILVER,int(170*q),8)
    glow_circle(im,*right,12,GOLD,int(190*q),10)
    centered(d,(left[0],h*.68),"CONVENTIONAL TRUTH",font(FONT_SANS_BOLD,14),SILVER)
    centered(d,(right[0],h*.68),"ULTIMATE TRUTH",font(FONT_SANS_BOLD,14),GOLD)
    arrow(d,(left[0]+50,cy-15),(right[0]-50,cy-15),VIOLET,2,8)
    seal(im,"THE TWO TRUTHS",
         "conventional and ultimate — both are necessary, neither is final")

def vis_emptiness_empty(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,4,190,11)
    for rr in range(45,280,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(70*q*(1-rr/310))),width=3)
    glow_circle(im,cx,cy,14,GOLD,int(200*q),10)
    if q>.5:
        centered(d,(cx,cy),"EMPTINESS IS EMPTY",
                 font(FONT_SERIF_BOLD,int(h*.04)),(*GOLD,int(190*(q-.5)/.5)))
    seal(im,"EMPTINESS IS EMPTY",
         "even emptiness does not exist inherently — the medicine must be released")

def vis_samsara_nirvana(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    left=(w*.30,cy); right=(w*.70,cy)
    glow_circle(im,*left,15,CRIMSON,int(190*q),10)
    glow_circle(im,*right,15,GOLD,int(190*q),10)
    centered(d,(left[0],h*.68),"SAṀSĀRA",font(FONT_SERIF_BOLD,18),CRIMSON)
    centered(d,(right[0],h*.68),"NIRVĀṆA",font(FONT_SERIF_BOLD,18),GOLD)
    if q>.4:
        arrow(d,(left[0]+40,cy),(right[0]-40,cy),
              (*VIOLET,int(180*(q-.4)/.6)),3,10)
        centered(d,(cx,cy+35),"=",font(FONT_SERIF_BOLD,int(h*.05)),
                 (*VIOLET,int(180*(q-.4)/.6)))
    seal(im,"SAṀSĀRA IS NIRVĀṆA",
         "there is no difference between the conditioned and the unconditioned")

def vis_causality(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    nodes=[]
    for i in range(6):
        x=lerp(w*.15,w*.85,i/5)
        y=cy+math.sin(i*1.2)*30
        nodes.append((x,y))
        glow_circle(im,x,y,8+4*q,PALE_GOLD,int(160*q),7)
    for i in range(len(nodes)-1):
        glow_line(im,partial([nodes[i],nodes[i+1]],q),CYAN,3,160,9)
        arrow(d,((nodes[i][0]+nodes[i+1][0])/2,
                 (nodes[i][1]+nodes[i+1][1])/2-16),
              ((nodes[i][0]+nodes[i+1][0])/2,
               (nodes[i][1]+nodes[i+1][1])/2+10),CYAN,2,7)
    seal(im,"CAUSALITY IS DEPENDENT ARISING",
         "cause and effect are not separate — they co-arise in dependence")

def vis_no_motion(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=[(w*.20,cy),(w*.35,cy),(w*.50,cy),(w*.65,cy),(w*.80,cy)]
    for i,x in enumerate([p[0] for p in pts]):
        glow_circle(im,x,cy,10+3*q,[GOLD,CYAN,VIOLET,GREEN,CRIMSON][i],
                    int(170*q),8)
    glow_line(im,partial(pts,q),CYAN,3,160,9)
    seal(im,"MOTION IS ILLUSORY",
         "if motion is in the present, what moves? If it is in the past, where has it gone?")

def vis_self_no_self(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=dependency_net(w,h,20,7)
    for i,(x,y) in enumerate(pts):
        col=[GOLD,CYAN,VIOLET][i%3]
        glow_circle(im,x,y,6+3*q,col,int(130+50*q),7)
    glow_circle(im,cx,cy,14,GOLD,int(200*q),12)
    for x,y in pts:
        if random.Random(int(x*100+y)).random()<.3*q:
            d.line((cx,cy,x,y),fill=(*PALE_GOLD,int(60*q)),width=1)
    seal(im,"THE SELF IS EMPTY",
         "the 'I' is a dependently arisen designation — empty of inherent existence")

def vis_freedom(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=[]
    for i in range(220):
        a=i*math.tau/220
        rad=20+160*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        pts.append((x,y))
    glow_line(im,partial(pts,q),GOLD,5,220,16)
    for i in range(8):
        a=i*math.tau/8+t*.04
        rad=30+140*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,4+2*q,PALE_GOLD,int(130*q),5)
    seal(im,"FREEDOM FROM VIEWS",
         "the ultimate freedom is not holding any view — not even the view of emptiness")

def vis_nagarjuna_icon(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_seated(d,cx,cy,.60,INK,int(200*q))
    glow_circle(im,cx,cy-20,16,GOLD,int(210*q),14)
    for i in range(8):
        a=i*math.tau/8+t*.05
        rad=40+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        d.line((cx,cy-20,x,y),fill=(*GOLD,int(130*q)),width=1)
        if i%2==0:
            glow_circle(im,x,y,5+2*q,PALE_GOLD,int(120*q),6)
    seal(im,"NĀGĀRJUNA",
         "the great dialectician — who used reason to show the limits of reason")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"PHILOSOPHY",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"MĀDHYAMAKA",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"WESTERN PHILOSOPHY MEETS THE MIDDLE WAY",
         "Wittgenstein's ladder, Derrida's différance — similar insights, different vocabularies")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("EMPTINESS IS NOT NIHILISM","IT IS DEPENDENT ARISING",CRIMSON),
        ("EMPTINESS IS NOT NOTHINGNESS","IT IS THE ABSENCE OF INHERENT EXISTENCE",CRIMSON),
        ("EMPTINESS IS COMPATIBLE WITH SCIENCE","SUPPORTED — NATURALISM IS NOT ETERNALISM",GREEN),
        ("THE MIDDLE WAY IS NOT COMPROMISE","IT IS TRANSCENDENCE OF EXTREMES",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DO NOT TURN EMPTINESS INTO A BELIEF",
         "emptiness is not something to believe — it is something to see")

def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,5,195,12)
    for i,x in enumerate([w*.25,w*.40,w*.55,w*.70]):
        glow_circle(im,x,cy,10,[VIOLET,GREEN,CRIMSON,GOLD][i],140,7)
    for rr in range(45,310,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(72*q*(1-rr/340))),width=3)
    glow_circle(im,cx,cy,16,GOLD,int(220*q),16)
    if q>.72:
        centered(d,(cx,cy-15),"THE NET HAS NO CENTER",
                 font(FONT_SERIF_BOLD,int(h*.035)),GOLD)
    seal(im,"Everything is empty of inherent existence. Dependent arising is the middle way. Emptiness itself is empty. There is nothing to grasp — and that is the ultimate freedom.",
         "",GOLD)


def draw_seated(d,cx,cy,scale=1.0,color=INK,alpha=205):
    d.ellipse((cx-27*scale,cy-130*scale,cx+27*scale,cy-78*scale),
              outline=(*color,alpha),width=max(2,int(4*scale)))
    d.line((cx,cy-78*scale,cx,cy+35*scale),
           fill=(*color,alpha),width=max(3,int(6*scale)))
    d.line((cx-68*scale,cy-35*scale,cx+68*scale,cy-35*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((cx-50*scale,cy+35*scale,cx-25*scale,cy+80*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((cx+50*scale,cy+35*scale,cx+25*scale,cy+80*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((cx,cy-35*scale,cx-30*scale,cy-12*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((cx,cy-35*scale,cx+30*scale,cy-12*scale),
           fill=(*color,alpha),width=max(3,int(5*scale)))


VISUALS: dict[str,Callable] = {
    "sunyata":vis_sunyata,
    "dependent":vis_dependent_arising,
    "middle":vis_middle_way,
    "four":vis_four_cornered,
    "eight":vis_eight_negations,
    "truths":vis_two_truths,
    "empty":vis_emptiness_empty,
    "samsara":vis_samsara_nirvana,
    "causality":vis_causality,
    "motion":vis_no_motion,
    "self":vis_self_no_self,
    "freedom":vis_freedom,
    "nagarjuna":vis_nagarjuna_icon,
    "bridge":vis_bridge,
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
    Scene("Śūnyatā — Emptiness",
          "Not nothing — empty of inherent existence, full of dependent arising.",
          9.0,"sunyata",{}),
    Scene("Opening",
          "Nāgārjuna begins: no arising, no ceasing, no permanence, no annihilation.",
          8.5,"eight",{}),
    Scene("The Field",
          "All things appear in relation. Nothing stands alone.",
          8.0,"sunyata",{}),

    Scene("Pratītyasamutpāda",
          "Dependent arising: when this is, that is. When this is not, that is not.",
          9.0,"dependent",{}),
    Scene("The Net of Relations",
          "Every phenomenon is a knot in a net of causes and conditions. No knot stands alone.",
          9.0,"dependent",{}),
    Scene("No First Cause",
          "There is no first cause because every cause is itself an effect.",
          8.5,"dependent",{}),
    Scene("The Web",
          "The net has no center and no edge. Every thread supports every other.",
          9.0,"dependent",{}),

    Scene("The Middle Way",
          "Not existence. Not non-existence. Free from both extremes.",
          8.5,"middle",{}),
    Scene("Eternalism and Nihilism",
          "Eternalism: things exist inherently. Nihilism: nothing exists at all. Both miss the point.",
          9.0,"middle",{}),
    Scene("Beyond Both",
          "The middle way is not a compromise. It is a transcendence of the framework itself.",
          9.0,"middle",{}),

    Scene("The Four-Cornered Negation",
          "It is not the case that X exists, does not exist, both, or neither.",
          9.0,"four",{}),
    Scene("Catuṣkoṭi",
          "The four-cornered logic of Nāgārjuna — a dialectic that exhausts all positions.",
          9.0,"four",{}),
    Scene("Each Corner Collapses",
          "Existence, non-existence, both, neither — each position refutes itself when examined.",
          9.5,"four",{}),

    Scene("The Eight Negations",
          "No arising, no ceasing, no coming, no going, no sameness, no difference, no permanence, no annihilation.",
          9.5,"eight",{}),
    Scene("Opening Stanza",
          "The famous first verse of the Mūlamadhyamakakārikā — the gateway to the entire system.",
          9.0,"eight",{}),

    Scene("The Two Truths",
          "Conventional truth describes the world as it appears. Ultimate truth sees through inherent existence.",
          9.5,"truths",{}),
    Scene("Both Are Necessary",
          "Without conventional truth, the ultimate cannot be taught. Without the ultimate, freedom is not attained.",
          9.5,"truths",{}),
    Scene("Neither Is Final",
          "Even the ultimate truth is not final. It too is a dependently arisen designation.",
          9.0,"truths",{}),

    Scene("Emptiness is Empty",
          "The most subtle point: emptiness itself does not exist inherently.",
          9.5,"empty",{}),
    Scene("The Medicine",
          "Emptiness is medicine. Once the disease of inherent existence is cured, the medicine is released.",
          9.0,"empty",{}),
    Scene("No View",
          "Even the view of emptiness must be relinquished. The ultimate freedom is freedom from all views.",
          9.5,"empty",{}),

    Scene("Saṁsāra is Nirvāṇa",
          "There is no difference between the conditioned and the unconditioned.",
          9.0,"samsara",{}),
    Scene("Not Two",
          "Saṁsāra and nirvāṇa are not two different places. They are two ways of seeing the same.",
          9.0,"samsara",{}),
    Scene("Seeing Changes Everything",
          "Nothing changes but the way you see. And that changes everything.",
          8.5,"samsara",{}),

    Scene("Causality is Dependent Arising",
          "Cause and effect are not separate entities. They co-arise in dependence on each other.",
          9.0,"causality",{}),
    Scene("No Self-Cause",
          "Nothing causes itself. Nothing is uncaused. Everything arises in dependence on everything else.",
          9.0,"causality",{}),
    Scene("The Middle Way of Causality",
          "Not determinism, not randomness — dependent arising is the middle way of causation.",
          9.0,"causality",{}),

    Scene("Motion is Illusory",
          "If motion is in the present, what moves? If it is in the past, where has it gone?",
          8.5,"motion",{}),
    Scene("The Arrow",
          "The flying arrow is stationary at every instant. Motion is a conceptual construction.",
          8.5,"motion",{}),
    Scene("Zeno Meets Nāgārjuna",
          "The Greek and Indian traditions both saw that motion cannot be found when examined.",
          8.5,"motion",{}),

    Scene("The Self is Empty",
          "The 'I' is a dependently arisen designation. Empty of inherent existence.",
          9.0,"self",{}),
    Scene("No Owner",
          "If the self existed inherently, where would it be found? In the body? In the mind? Between them?",
          9.0,"self",{}),
    Scene("The Designation",
          "The self is a convenient designation for a collection of processes. Nothing more, nothing less.",
          8.5,"self",{}),

    Scene("Freedom from Views",
          "The ultimate freedom is not holding any view — not even the view of emptiness.",
          9.5,"freedom",{}),
    Scene("The Ladder",
          "Wittgenstein: the ladder must be thrown away after climbing. Nāgārjuna: the view must be released.",
          9.0,"freedom",{}),
    Scene("No Ground",
          "There is no ultimate ground. And that is not a problem. It is liberation.",
          9.5,"freedom",{}),

    Scene("Nāgārjuna",
          "The great dialectician who used reason to show the limits of reason.",
          9.0,"nagarjuna",{}),
    Scene("The Dialectician",
          "He did not offer a positive doctrine. He showed that every position refutes itself.",
          9.0,"nagarjuna",{}),
    Scene("The Gift",
          "The gift of Mādhyamaka: freedom from the need to have a final view.",
          8.5,"nagarjuna",{}),

    Scene("Science Bridge",
          "Modern physics describes a world of relations, not substances. The parallels are striking.",
          9.0,"bridge",{}),
    Scene("Relativity",
          "Mass, space, time — all are relative, dependent, empty of independent existence.",
          9.0,"bridge",{}),
    Scene("Quantum Relations",
          "Quantum phenomena are defined by their relations, not by intrinsic properties.",
          9.0,"bridge",{}),

    Scene("Caution",
          "Emptiness is not a hypothesis. It is an invitation to look more closely.",
          8.5,"caution",{}),
    Scene("Not a Theory",
          "Mādhyamaka is not a theory to believe. It is a method of seeing through theories.",
          9.0,"caution",{}),
    Scene("The Practice",
          "Emptiness is not the conclusion. It is the beginning of genuine inquiry.",
          8.5,"caution",{}),

    Scene("The Net",
          "The net of dependent arising has no center, no edge, and no weaver.",
          9.0,"final",{}),
    Scene("Release",
          "When you see through inherent existence, the world does not disappear. It appears for the first time.",
          9.0,"final",{}),
    Scene("Closing",
          "Everything is empty of inherent existence. Dependent arising is the middle way. Emptiness itself is empty. There is nothing to grasp — and that is the ultimate freedom. The net remains, but you no longer ask who wove it.",
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
    output=OUTPUT/"nagarjuna_emptiness.mp4"
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
        "title":"everything is empty of inherent existence",
        "subtitle":"Nāgārjuna's Mūlamadhyamakakārikā on dependent arising and the middle way",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"net of interdependent threads — no thread stands alone",
        "visual_arc":[
            "emptiness","dependent arising","middle way","negations",
            "two truths","emptiness of emptiness","freedom"
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
