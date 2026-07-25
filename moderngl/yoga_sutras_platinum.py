#!/usr/bin/env python3
"""
THE SEER ABIDES IN ITS OWN NATURE
Patañjali's Yoga Sūtras on the cessation of mental modification.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Yoga is the cessation of mental modification (yogaś citta-vṛtti-nirodhaḥ).
When the mind stops churning, the seer abides in its own nature.
The sūtras are not a philosophy — they are a practical technology
for the systematic purification of attention.

FILM THESIS
-----------
The modern picture often runs:

mind → thoughts → identity → suffering

The Yoga Sūtra picture can be staged as:

unrestricted awareness
→ vṛtti (mental whirl)
→ duḥkha (suffering)
→ abhyāsa (practice)
→ vairāgya (detachment)
→ the eight limbs
→ samādhi
→ kaivalya (liberation)

The sūtras describe a gradient of stability, not a doctrine to believe.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a citta-vṛtti whirl that resolves into a still point.
• Final reveal: the seer was never disturbed — only obscured.

OUTPUT
------
output_yoga_sutras/
  frames/
  scenes/
  yoga_sutras.mp4
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
OUTPUT = ROOT / "output_yoga_sutras"
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

def vritti_field(w,h,n=20,seed=0):
    rng=random.Random(seed)
    return [(rng.uniform(w*.14,w*.86),rng.uniform(h*.18,h*.64)) for _ in range(n)]


# =============================================================================
# VISUALS
# =============================================================================

def vis_yoga_cessation(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=vritti_field(w,h,25,1)
    for i,(x,y) in enumerate(pts):
        col=[GOLD,CYAN,VIOLET][i%3]
        glow_circle(im,x,y,8+4*(1-q),col,int(100+80*q),7)
    for rr in range(45,250,30):
        d.ellipse((w*.50-rr,cy-rr*.60,w*.50+rr,cy+rr*.60),
                  outline=(*GOLD,int(60*q*(1-rr/280))),width=3)
    seal(im,"YOGA IS CESSATION",
         "yogaś citta-vṛtti-nirodhaḥ — the stilling of mental modification")

def vis_seer_abides(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_seated(d,cx,cy,.65,INK,int(200*q))
    glow_circle(im,cx,cy-10,16,GOLD,int(200*q),14)
    for rr in range(40,220,28):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(65*q*(1-rr/250))),width=3)
    seal(im,"THE SEER ABIDES IN ITS OWN NATURE",
         "when the mind is still, the seer is revealed")

def vis_vrittis(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=vritti_field(w,h,30,3)
    for i,(x,y) in enumerate(pts):
        col=[CYAN,CRIMSON,GREEN,VIOLET][i%4]
        glow_circle(im,x,y,8+5*q,col,int(130+50*q),7)
    center_field=[(x,y) for x,y in pts if math.dist((x,y),(cx,cy))<100]
    if center_field and q>.4:
        pts2=sorted(center_field,key=lambda p:math.dist(p,(cx,cy)))
        glow_line(im,partial(pts2,(q-.4)/.6),VIOLET,3,160,10)
    seal(im,"THE FIVE VRITTIS",
         "pramāṇa, viparyaya, vikalpa, nidrā, smṛti — the five whirls of mind")

def vis_practice_detachment(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx1,cy1=w*.35,h*.40; cx2,cy2=w*.65,h*.40; q=ease(u)
    glow_circle(im,cx1,cy1,14,CYAN,int(190*q),10)
    glow_circle(im,cx2,cy2,14,VIOLET,int(190*q),10)
    if q>.3:
        pts=[]
        for i in range(50):
            f=i/49
            x=lerp(cx1+30,cx2-30,f)
            y=lerp(cy1,cy2,f)+math.sin(f*math.tau*2+t)*20*q
            pts.append((x,y))
        glow_line(im,partial(pts,(q-.3)/.7),GOLD,3,180,10)
    centered(d,(cx1,cy1+35),"ABHYĀSA",font(FONT_SERIF_BOLD,18),CYAN)
    centered(d,(cx2,cy2+35),"VAIRĀGYA",font(FONT_SERIF_BOLD,18),VIOLET)
    seal(im,"PRACTICE AND DETACHMENT",
         "the two pillars: persistent effort and freedom from grasping")

def vis_isvara(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    glow_circle(im,cx,cy,22,GOLD,int(220*q),18)
    for i in range(12):
        a=i*math.tau/12+t*.05
        rad=40+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(130*q)),width=1)
        glow_circle(im,x,y,4+2*q,PALE_GOLD,int(120*q),5)
    seal(im,"ĪŚVARA",
         "the special puruṣa untouched by affliction — a seed of still awareness")

def vis_eight_limbs(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    limbs=["YAMA","NIYAMA","ĀSANA","PRĀṆĀYĀMA","PRATYĀHĀRA","DHĀRAṆĀ","DHYĀNA","SAMĀDHI"]
    for i,lab in enumerate(limbs):
        a=i*math.tau/len(limbs)-math.pi/2+t*.04
        rad=30+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(CYAN,GOLD,i/7)
        d.line((cx,cy,x,y),fill=(*col,int(150*q)),width=2)
        glow_circle(im,x,y,6+3*q,col,int(160*q),7)
        if q>.5:
            centered(d,(x,y-16*q),lab,font(FONT_SANS_BOLD,10),col)
    seal(im,"THE EIGHT LIMBS",
         "a graduated path from outer conduct to inner absorption")

def vis_yama(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    yamas=["AHIṀSĀ","SATYA","ASTEYA","BRAHMACARYA","APARIGRAHA"]
    for i,lab in enumerate(yamas):
        a=i*math.tau/len(yamas)+t*.05
        rad=30+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(GREEN,CRIMSON,i/4)
        d.line((cx,cy,x,y),fill=(*col,int(150*q)),width=2)
        glow_circle(im,x,y,6+3*q,col,int(160*q),7)
        if q>.5:
            centered(d,(x,y+18*q),lab,font(FONT_SANS_BOLD,10),col)
    seal(im,"YAMA — THE GREAT VOWS",
         "non-violence, truth, non-stealing, celibacy, non-possessiveness")

def vis_niyama(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    niyamas=["ŚAUCA","SANTOSA","TAPAS","SVĀDHYĀYA","ĪŚVARAPRAṆIDHĀNA"]
    for i,lab in enumerate(niyamas):
        a=i*math.tau/len(niyamas)+t*.05
        rad=30+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(CYAN,VIOLET,i/4)
        d.line((cx,cy,x,y),fill=(*col,int(150*q)),width=2)
        glow_circle(im,x,y,6+3*q,col,int(160*q),7)
        if q>.5:
            centered(d,(x,y+18*q),lab,font(FONT_SANS_BOLD,10),col)
    seal(im,"NIYAMA — PERSONAL OBSERVANCES",
         "purity, contentment, austerity, self-study, surrender to the Lord")

def vis_asana(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_seated(d,cx,cy,.70,INK,int(190*q))
    glow_circle(im,cx,cy-22,12,GOLD,int(170*q),9)
    for rr in range(40,180,24):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(60*q*(1-rr/200))),width=3)
    seal(im,"ĀSANA — STEADY POSTURE",
         "sthira-sukham-āsanam — steady and comfortable, the body becomes stable")

def vis_pranayama(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_seated(d,cx,cy,.65,INK,int(190*q))
    for rr in range(30,170,20):
        r_cur=rr*q
        d.ellipse((cx-r_cur,cy-r_cur*.62,cx+r_cur,cy+r_cur*.62),
                  outline=(*CYAN,int(60*(1-rr/200))),width=2)
    for i in range(4):
        a=math.pi/2+i*math.pi/2
        x=cx+math.cos(a)*50*q; y=cy+math.sin(a)*50*q
        glow_circle(im,x,y,5+3*q,CYAN,int(150*q),6)
    seal(im,"PRĀṆĀYĀMA — REGULATION OF BREATH",
         "the breath lengthens — the mind follows the breath into stillness")

def vis_pratyahara(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    for i in range(8):
        a=i*math.tau/8+t*.06
        rad=20+130*(1-q)
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(SILVER,WHITE,i/7)
        glow_circle(im,x,y,8+4*(1-q),col,int(160*(1-q)),8)
    draw_seated(d,cx,cy,.60,INK,int(200*q))
    glow_circle(im,cx,cy,12,GOLD,int(180*q),9)
    seal(im,"PRATYĀHĀRA — WITHDRAWAL OF THE SENSES",
         "the senses cease to follow their objects — awareness turns inward")

def vis_dharana(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_seated(d,cx,cy,.60,INK,int(190*q))
    target=(cx,cy-35)
    glow_circle(im,*target,14,GOLD,int(220*q),12)
    for i in range(6):
        a=i*math.tau/6+t*.06
        rad=30+100*q
        x=target[0]+math.cos(a)*rad; y=target[1]+math.sin(a)*rad*.35
        d.line((*target,x,y),fill=(*GOLD,int(130*q)),width=2)
    seal(im,"DHĀRAṆĀ — FOCUSED CONCENTRATION",
         "binding the mind to a single place — the first stage of inner discipline")

def vis_dhyana(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_seated(d,cx,cy,.60,INK,int(190*q))
    glow_circle(im,cx,cy-35,14,GOLD,int(200*q),12)
    for rr in range(45,240,28):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(70*q*(1-rr/270))),width=3)
    seal(im,"DHYĀNA — MEDITATIVE FLOW",
         "the stream of thought becomes one continuous act of awareness")

def vis_samadhi(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,4,190,11)
    for rr in range(40,280,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(72*q*(1-rr/310))),width=3)
    glow_circle(im,cx,cy,16,GOLD,int(210*q),14)
    if q>.6:
        centered(d,(cx,cy),"SAMĀDHI",
                 font(FONT_SERIF_BOLD,int(h*.05)),(*GOLD,int(200*(q-.6)/.4)))
    seal(im,"SAMĀDHI — ABSORPTION",
         "the meditator, the act, and the object become one")

def vis_samprajnata(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    stages=["VITARKA","VICĀRA","ĀNANDA","ASMITĀ"]
    for i,lab in enumerate(stages):
        y=lerp(h*.22,h*.58,i/3)
        width=lerp(60,240,i/3)*q
        col=mix(CYAN,GOLD,i/3)
        d.line((w*.50-width/2,y,w*.50+width/2,y),
               fill=(*col,int(190*q)),width=4)
        if q>.4:
            centered(d,(w*.50,y-14),lab,font(FONT_SANS_BOLD,14),col)
    seal(im,"SAMPRAJÑĀTA SAMĀDHI",
         "absorption with support — reasoning, reflection, bliss, and I-am-ness")

def vis_asamprajnata(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,3,170,10)
    for rr in range(45,280,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(65*q*(1-rr/310))),width=3)
    if q>.55:
        for i,x in enumerate([w*.25,w*.40,w*.55,w*.70]):
            glow_circle(im,x,cy,8,[VIOLET,GREEN,CRIMSON,GOLD][i],120,6)
    seal(im,"ASAMPRAJÑĀTA SAMĀDHI",
         "absorption without support — the seedless state, freedom from mental content")

def vis_kaivalya(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,5,195,12)
    for rr in range(45,310,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(72*q*(1-rr/340))),width=3)
    glow_circle(im,cx,cy,18,GOLD,int(220*q),16)
    if q>.65:
        centered(d,(cx,cy-10),"KAIVALYA",
                 font(FONT_SERIF_BOLD,int(h*.05)),(*GOLD,int(210*(q-.65)/.35)))
    seal(im,"KAIVALYA — LIBERATION",
         "the seer abides in its own nature — the end of suffering, the beginning of freedom")

def vis_kleshas(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    kleshas=["AVIDYĀ","ASMITĀ","RĀGA","DVEṢA","ABHINIVEŚA"]
    for i,lab in enumerate(kleshas):
        a=i*math.tau/len(kleshas)+t*.06
        rad=30+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(CRIMSON,INK,i/4)
        d.line((cx,cy,x,y),fill=(*col,int(150*q)),width=2)
        glow_circle(im,x,y,7+4*q,col,int(160*q),8)
        if q>.5:
            centered(d,(x,y+18*q),lab,font(FONT_SANS_BOLD,10),col)
    seal(im,"THE FIVE KLESHAS",
         "ignorance, egoity, attraction, aversion, and the fear of death")

def vis_gunas(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    gunas=[("SATTVA",PALE_GOLD),("RAJAS",CRIMSON),("TAMAS",INK)]
    for i,(lab,col) in enumerate(gunas):
        x=w*.25+i*w*.25
        y=h*.40
        rad=20+60*q
        d.ellipse((x-rad,cy-rad,x+rad,cy+rad),
                  fill=(*mix(col,WHITE,.15),int(180*q)),
                  outline=(*col,int(200*q)),width=3)
        centered(d,(x,cy),lab,font(FONT_SANS_BOLD,16),col)
    seal(im,"THE THREE GUṆAS",
         "sattva, rajas, tamas — the qualities of prakṛti that the seer witnesses")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"COGNITIVE SCIENCE",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"PĀTAÑJALA YOGA",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE STUDIES ATTENTION — YOGA TRANSFORMS IT",
         "both agree: the mind can be trained; they differ on the ultimate goal")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("YOGA IS NOT A WORKOUT","IT IS A DISCIPLINE OF CONSCIOUSNESS",CRIMSON),
        ("SIDDHIS (POWERS) ARE OBSTACLES","THEY ARE DISTRACTIONS ON THE PATH",CRIMSON),
        ("KLESHAS CAN BE REDUCED","SUPPORTED — THROUGH PRACTICE",GREEN),
        ("KAIVALYA IS NOT MAGICAL","IT IS THE NATURAL STATE OF THE SEER",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DO NOT MYSTIFY THE SŪTRAS",
         "the sūtras are a practical technology — not a supernatural claim")

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
    glow_circle(im,cx,cy,18,GOLD,int(220*q),16)
    if q>.72:
        centered(d,(cx,cy-10),"THE SEER ABIDES",
                 font(FONT_SERIF_BOLD,int(h*.045)),GOLD)
    seal(im,"Yoga is cessation — the seer abides in its own nature. Practice and detachment clear the way. The mind stills, the seer is revealed, and the suffering ends.",
         "",GOLD)


VISUALS: dict[str,Callable] = {
    "cessation":vis_yoga_cessation,
    "seer":vis_seer_abides,
    "vrittis":vis_vrittis,
    "practice":vis_practice_detachment,
    "isvara":vis_isvara,
    "limbs":vis_eight_limbs,
    "yama":vis_yama,
    "niyama":vis_niyama,
    "asana":vis_asana,
    "pranayama":vis_pranayama,
    "pratyahara":vis_pratyahara,
    "dharana":vis_dharana,
    "dhyana":vis_dhyana,
    "samadhi":vis_samadhi,
    "samprajnata":vis_samprajnata,
    "asamprajnata":vis_asamprajnata,
    "kaivalya":vis_kaivalya,
    "kleshas":vis_kleshas,
    "gunas":vis_gunas,
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
    Scene("Yoga is Cessation",
          "Yogaś citta-vṛtti-nirodhaḥ — yoga is the cessation of mental modification.",
          9.0,"cessation",{}),
    Scene("The Seer Abides",
          "When the mind is still, the seer abides in its own nature.",
          8.5,"seer",{}),
    Scene("Vṛtti",
          "The mind is a whirl. Thoughts, memories, fantasies — all modifications of the same substance.",
          8.0,"vrittis",{}),

    Scene("Pramāṇa",
          "Right knowledge: perception, inference, and testimony. Even valid knowledge binds.",
          8.5,"vrittis",{}),
    Scene("Viparyaya",
          "Wrong knowledge: mistaking the rope for a snake. Most suffering begins here.",
          8.0,"vrittis",{}),
    Scene("Vikalpa",
          "Imagination: verbal constructs with no corresponding reality. Language creates worlds.",
          8.5,"vrittis",{}),
    Scene("Nidrā",
          "Sleep: the modification of absence. Even in deep sleep, the mind is active.",
          8.0,"vrittis",{}),
    Scene("Smṛti",
          "Memory: not the past itself, but the past as modified by the present.",
          8.5,"vrittis",{}),

    Scene("Abhyāsa",
          "Practice: sustained effort toward stability. Not occasional — continuous.",
          8.5,"practice",{}),
    Scene("Vairāgya",
          "Detachment: freedom from thirst for seen and unseen objects. The letting-go of grasping.",
          9.0,"practice",{}),
    Scene("The Two Wings",
          "Practice and detachment are the two wings of yoga. Neither alone can fly.",
          8.5,"practice",{}),

    Scene("Īśvara",
          "The special puruṣa, untouched by affliction. A seed of still awareness within.",
          9.0,"isvara",{}),
    Scene("Praṇidhāna",
          "Surrender to the Lord: not worship, but the recognition that the personal will is finite.",
          8.5,"isvara",{}),
    Scene("The Seed",
          "Īśvara is the seed of all knowledge. The OM carries the vibration of that seed.",
          8.5,"isvara",{}),

    Scene("The Eight Limbs",
          "From outer conduct to inner absorption — the graduated path of yoga.",
          8.5,"limbs",{}),
    Scene("Ladder",
          "Each limb prepares the ground for the next. No limb can be skipped.",
          8.0,"limbs",{}),
    Scene("Integration",
          "The limbs are not steps in a sequence. They are aspects of a single practice.",
          8.5,"limbs",{}),

    Scene("Yama — The Great Vows",
          "Non-violence, truth, non-stealing, celibacy, non-possessiveness.",
          9.0,"yama",{}),
    Scene("Ahimsā",
          "Non-violence: the foundation. When firmly established, hostility ceases in your presence.",
          8.5,"yama",{}),
    Scene("Satya",
          "Truth: speech and mind must align. Truth spoken without violence is the highest power.",
          8.5,"yama",{}),

    Scene("Niyama — Personal Observances",
          "Purity, contentment, austerity, self-study, surrender to the Lord.",
          9.0,"niyama",{}),
    Scene("Śauca",
          "Purity: not just cleanliness, but the discernment that removes what obscures the seer.",
          8.5,"niyama",{}),
    Scene("Santoṣa",
          "Contentment: the happiness that depends on nothing external.",
          8.5,"niyama",{}),

    Scene("Āsana — Steady Posture",
          "Sthira-sukham-āsanam: steady and comfortable. The body becomes a stable seat for awareness.",
          8.5,"asana",{}),
    Scene("Stillness",
          "When the body is still, the mind can follow. Posture is the outer form of inner stability.",
          8.0,"asana",{}),

    Scene("Prāṇāyāma — Breath Regulation",
          "The breath lengthens. The mind follows the breath into stillness.",
          8.5,"pranayama",{}),
    Scene("The Fourth",
          "When the breath ceases to be felt, the veil between body and mind thins.",
          8.5,"pranayama",{}),

    Scene("Pratyāhāra — Withdrawal",
          "The senses cease to follow their objects. Awareness turns inward.",
          9.0,"pratyahara",{}),
    Scene("The Turn",
          "What was reaching outward now rests. The energy of the senses returns to its source.",
          8.5,"pratyahara",{}),

    Scene("Dhāraṇā — Concentration",
          "Binding the mind to a single place. The first stage of inner discipline.",
          8.5,"dharana",{}),
    Scene("The Point",
          "One point, one focus. The scattered mind gathers itself.",
          8.0,"dharana",{}),

    Scene("Dhyāna — Meditation",
          "The stream of awareness becomes one continuous act. No gaps, no distractions.",
          9.0,"dhyana",{}),
    Scene("Flow",
          "The boundary between meditator and object begins to dissolve.",
          8.5,"dhyana",{}),

    Scene("Samādhi — Absorption",
          "The meditator, the act, and the object become one. No separation remains.",
          9.5,"samadhi",{}),
    Scene("The Three Become One",
          "Knower, knowing, known — they collapse into a single luminous act.",
          9.0,"samadhi",{}),

    Scene("Samprajñāta Samādhi",
          "Absorption with support: reasoning, reflection, bliss, and I-am-ness.",
          9.0,"samprajnata",{}),
    Scene("With Seed",
          "The seed of knowledge remains. The mind is still but not yet free.",
          8.5,"samprajnata",{}),

    Scene("Asamprajñāta Samādhi",
          "Absorption without support. The seedless state. Freedom from mental content.",
          9.5,"asamprajnata",{}),
    Scene("Without Seed",
          "No object, no thought, no 'I'. Only what remains when everything has been released.",
          9.5,"asamprajnata",{}),

    Scene("The Kleśas",
          "Ignorance, egoity, attraction, aversion, the fear of death — the five afflictions.",
          9.0,"kleshas",{}),
    Scene("Avidyā",
          "Ignorance: mistaking the impermanent for permanent, the impure for pure.",
          8.5,"kleshas",{}),
    Scene("Asmitā",
          "Egoity: the identification of the seer with the instruments of seeing.",
          8.5,"kleshas",{}),
    Scene("Rāga and Dveṣa",
          "Attraction and aversion: the mind moves toward pleasure and away from pain.",
          8.5,"kleshas",{}),
    Scene("Abhiniveśa",
          "The fear of death: the deepest kleśa, present even in the wise.",
          9.0,"kleshas",{}),

    Scene("The Three Guṇas",
          "Sattva, rajas, tamas — the qualities of nature that the seer witnesses.",
          8.5,"gunas",{}),
    Scene("Prakṛti and Puruṣa",
          "Nature and the seer. They are not the same. Liberation is their discernment.",
          9.0,"gunas",{}),

    Scene("Kaivalya — Liberation",
          "The seer abides in its own nature. Freedom from the guṇas. The end of suffering.",
          10.0,"kaivalya",{}),
    Scene("Alone in the Self",
          "Not isolation from the world — freedom within the world.",
          8.5,"kaivalya",{}),
    Scene("The Natural State",
          "Kaivalya is not a attainment. It is the nature of the seer when the veil of vṛtti lifts.",
          9.5,"kaivalya",{}),

    Scene("Science Bridge",
          "Cognitive science studies attention, neuroplasticity, and the trainability of mind.",
          8.5,"bridge",{}),
    Scene("Parallels",
          "Mindfulness research confirms what the sūtras describe: the mind can be reshaped by practice.",
          9.0,"bridge",{}),
    Scene("Different Goals",
          "Science aims at function. Yoga aims at freedom. Both recognize the path.",
          9.0,"bridge",{}),

    Scene("Caution",
          "The sūtras are a practical technology, not a supernatural claim.",
          8.0,"caution",{}),
    Scene("Not Supernatural",
          "The powers (siddhis) are described as obstacles. The goal is clarity, not magic.",
          8.5,"caution",{}),
    Scene("Discipline",
          "Keep the practice grounded: the sūtras describe what happens when attention is purified.",
          8.5,"caution",{}),

    Scene("The Seer Remains",
          "Through all the modifications, the seer was never disturbed — only obscured.",
          8.5,"final",{}),
    Scene("Stillness",
          "The whirl settles. What was always there becomes visible.",
          8.0,"final",{}),
    Scene("Closing",
          "Yoga is cessation. The seer abides in its own nature. Practice and detachment clear the way. The mind stills, the seer is revealed, and the suffering ends — not because suffering was unreal, but because the one who suffered was never what it seemed.",
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
    output=OUTPUT/"yoga_sutras.mp4"
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
        "title":"the seer abides in its own nature",
        "subtitle":"Patañjali's Yoga Sūtras on the cessation of mental modification",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"citta-vṛtti whirl resolving into a still point",
        "visual_arc":[
            "cessation","vṛtti","practice","limbs",
            "samādhi","kaivalya"
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
