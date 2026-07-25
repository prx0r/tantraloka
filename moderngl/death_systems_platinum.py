#!/usr/bin/env python3
"""
EVERY DEATH SYSTEM SAYS THE SAME THING
Six traditions, one structure: the afterlife is a recognition event.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Every major death tradition — Tibetan Bardo, Egyptian Book of the Dead,
Steiner's Kamaloca, Tantraloka's utkrānti, the Greek daimon at death,
and the modern near-death experience — describes the same sequence:

dissolution → encounter → judgment → recognition → integration → return

This convergence is not coincidence. The dying brain does not hallucinate
random content. It navigates a structural transition that consciousness
undergoes when it separates from the body.

FILM THESIS
-----------
The modern picture often runs:

death → nothing → annihilation

The comparative tradition shows:

dissolution of elements
→ panoramic memory review
→ encounter with a being of light
→ self-judgment
→ peaceful and wrathful visions
→ recognition as liberation
→ integration
→ return or rebirth

The structure is cross-cultural because the structure is metaphysical.
These are not cultural costumes on a neurological event.
They are reports from the same territory.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a dissolving body outline that reforms as light.
• Final reveal: the encounter is with your own deeper nature.

OUTPUT
------
output_death_systems/
  frames/
  scenes/
  death_systems.mp4
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
OUTPUT = ROOT / "output_death_systems"
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

def dissolve_field(w,h,count=30,seed=0):
    rng=random.Random(seed)
    return [(rng.uniform(w*.12,w*.88),rng.uniform(h*.18,h*.65)) for _ in range(count)]


# =============================================================================
# VISUALS
# =============================================================================

def vis_dissolution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.72,INK,int(200*(1-q)))
    pts=dissolve_field(w,h,35,5)
    for i,(x,y) in enumerate(pts):
        col=[PALE_GOLD,PALE_CYAN,PALE_VIOLET][i%3]
        glow_circle(im,x,y,6+4*q,col,int(80+100*q),7)
    for rr in range(30,200,25):
        d.ellipse((w*.50-rr,cy-rr*.60,w*.50+rr,cy+rr*.60),
                  outline=(*GOLD,int(55*q*(1-rr/240))),width=3)
    seal(im,"THE DISSOLUTION OF ELEMENTS",
         "earth, water, fire, air, ether — each releases its hold")

def vis_tibetan_bardo(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=[]
    for i in range(120):
        a=i*math.tau/120+t*.04
        rad=20+140*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        pts.append((x,y))
    glow_line(im,partial(pts,q),GOLD,4,195,12)
    glow_circle(im,cx,cy,16,GOLD,int(190*q),12)
    seal(im,"THE TIBETAN BOOK OF THE DEAD",
         "the bardo is not a place — it is a gap between identities")

def vis_egyptian_peret(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.65,INK,int(190*(1-q)))
    scale_pts=[(cx-80*q,cy-60),(cx+80*q,cy-60),(cx,cy+100*q)]
    glow_line(im,partial(scale_pts,q),GOLD,3,180,10)
    if q>.45:
        glow_circle(im,cx,cy-60,10,GOLD,int(180*(q-.45)/.55),8)
    seal(im,"THE EGYPTIAN BOOK OF THE DEAD",
         "the heart is weighed against a feather — the soul judges itself")

def vis_kamaloca(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    points=[(cx,cy)]
    for i in range(8):
        a=i*math.tau/8+t*.06
        rad=30+90*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,6+3*q,PALE_VIOLET,int(140*q),7)
        points.append((x,y))
    glow_line(im,partial(points,q),VIOLET,3,180,11)
    seal(im,"KAMALOCA (STEINER)",
         "the soul region where desire burns away — nothing punishes but your own attachments")

def vis_tantraloka_utkranti(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    for i in range(12):
        a=i*math.tau/12+t*.05
        rad=30+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=[CRIMSON,GOLD,VIOLET][i%3]
        d.line((cx,cy,x,y),fill=(*col,int(150*q)),width=2)
        glow_circle(im,x,y,5+3*q,col,int(140*q),7)
    glow_circle(im,cx,cy,14,GOLD,int(190*q),10)
    seal(im,"UTRKRĀNTI (TANTRALOKA)",
         "the ascent through the cakras — consciousness exits through the crown")

def vis_daimon_at_death(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx1,cy1=w*.32,h*.40; cx2,cy2=w*.68,h*.40; q=ease(u)
    draw_body(d,cx1,cy1,.55,INK,int(190*(1-q)))
    glow_circle(im,cx2,cy2,18,VIOLET,int(190*q),14)
    glow_circle(im,cx2,cy2,10,GOLD,int(170*q),8)
    if q>.35:
        pts=[]
        for i in range(60):
            f=i/59
            x=lerp(cx1+40,cx2-40,f)
            y=lerp(cy1,cy2,f)+math.sin(f*math.tau*3+t*2)*20
            pts.append((x,y))
        glow_line(im,partial(pts,(q-.35)/.65),GOLD,3,170,10)
    seal(im,"THE DAIMON AT DEATH",
         "the being you meet at the threshold is your own deeper nature")

def vis_panoramic_memory(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    pts=[]
    for i in range(60):
        x=lerp(w*.10,w*.90,i/59)
        yy=y+math.sin(i*.12+t*.8)*35*q
        pts.append((x,yy))
    glow_line(im,partial(pts,q),CYAN,3,190,11)
    for i in range(15):
        x=w*.10+i*w*.80/14
        glow_circle(im,x,y+math.sin(i*.9+t*.6)*35*q,6,GOLD,int(100*q),5)
    seal(im,"PANORAMIC MEMORY REVIEW",
         "your entire life appears in a single timeless moment")

def vis_self_judgment(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.65,INK,int(190*q))
    glow_circle(im,cx-60,cy-30,12,CRIMSON,int(170*q),9)
    glow_circle(im,cx+60,cy-30,12,GREEN,int(170*q),9)
    if q>.5:
        d.line((cx-60,cy-30,cx,cy-70,cx+60,cy-30),
               fill=(*GOLD,int(180*(q-.5)/.5)),width=3)
    seal(im,"SELF-JUDGMENT IS NOT PUNISHMENT",
         "you see what you did and who you became — and you are the only judge")

def vis_peaceful_wrathful(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    for i in range(14):
        a=i*math.tau/14+t*.06
        rad=30+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(PALE_GOLD,CRIMSON,abs(math.sin(i*1.3)))
        glow_circle(im,x,y,7+4*q,col,int(150*q),8)
        d.line((cx,cy,x,y),fill=(*col,int(120*q)),width=2)
    glow_circle(im,cx,cy,14,GOLD,int(190*q),10)
    seal(im,"PEACEFUL AND WRATHFUL DEITIES",
         "the beautiful and terrifying are projections of your own mind's contents")

def vis_recognition_liberation(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    line=[(w*.18,cy),(w*.82,cy)]
    glow_line(im,partial(line,q),CYAN,4,190,11)
    for rr in range(45,280,30):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(70*q*(1-rr/310))),width=3)
    glow_circle(im,cx,cy,16,GOLD,int(200*q),12)
    if q>.65:
        centered(d,(cx,cy),"I AM THIS",
                 font(FONT_SERIF_BOLD,int(h*.06)),(*GOLD,int(200*(q-.65)/.35)))
    seal(im,"RECOGNITION IS LIBERATION",
         "the moment you recognize what you see — you are free")

def vis_integration(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=[]
    for i in range(200):
        a=i*math.tau/200
        rad=20+150*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        pts.append((x,y))
    glow_line(im,partial(pts,q),GOLD,5,220,16)
    for i in range(8):
        a=i*math.tau/8+t*.04
        rad=30+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,4+2*q,PALE_GOLD,int(130*q),5)
    seal(im,"INTEGRATION",
         "what was fragmented becomes whole — the soul recomposes itself")

def vis_return(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.55,INK,int(190*q))
    glow_circle(im,cx,cy-30,12,GOLD,int(170*q),9)
    if q>.5:
        for i in range(10):
            a=i*math.tau/10+t*.08
            rad=40+100*(q-.5)/.5
            x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
            d.line((cx,cy-30,x,y),fill=(*PALE_GOLD,int(120*(q-.5)/.5)),width=1)
    seal(im,"RETURN AND REBIRTH",
         "having seen the other side — you choose to come back")

def vis_convergence(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    traditions=["TIBETAN","EGYPTIAN","STEINER","TANTRALOKA","GREEK","NDE"]
    for i,lab in enumerate(traditions):
        a=i*math.tau/len(traditions)-math.pi/2
        rad=40+140*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=[GOLD,CYAN,VIOLET,CRIMSON,GREEN,PALE_GOLD][i]
        glow_circle(im,x,y,8+4*q,col,int(170*q),8)
        d.line((cx,cy,x,y),fill=(*col,int(130*q)),width=2)
        if q>.55:
            centered(d,(x,y-20*q),lab,font(FONT_SANS_BOLD,11),col)
    glow_circle(im,cx,cy,16,GOLD,int(200*q),14)
    seal(im,"SIX TRADITIONS, ONE STRUCTURE",
         "the convergence is the strongest argument — they describe the same territory")

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
    glow_circle(im,cx,cy,16,GOLD,int(185*q),12)
    if q>.72:
        centered(d,(cx,cy),"THE ENCOUNTER IS WITH YOURSELF",
                 font(FONT_SERIF_BOLD,int(h*.035)),GOLD)
    seal(im,"EVERY DEATH SYSTEM SAYS THE SAME THING",
         "dissolution, encounter, recognition, return — the structure is real",GOLD)

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
        if i<len(xs)-1:
            arrow(d,(x+14,left[1]),(xs[i+1]-14,left[1]),
                  (*SILVER,140),2,7)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"NEAR-DEATH STUDIES",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"COMPARATIVE MYSTICISM",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE AND TRADITION AGREE ON THE PHENOMENA",
         "they disagree on interpretation — the structure itself is not in dispute")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("NDE REPORTS PROVE AN AFTERLIFE","NOT ESTABLISHED",CRIMSON),
        ("ALL TRADITIONS DESCRIBE THE SAME STRUCTURE","SUPPORTED",GREEN),
        ("CONSCIOUSNESS REQUIRES A BRAIN","PHYSICALIST ASSUMPTION",CRIMSON),
        ("THE STRUCTURE IS CROSS-CULTURAL","ESTABLISHED",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"KEEP THE CLAIMS DISCIPLINED",
         "the convergence is real — the interpretation remains open")


VISUALS: dict[str,Callable] = {
    "dissolution":vis_dissolution,
    "tibetan":vis_tibetan_bardo,
    "egyptian":vis_egyptian_peret,
    "kamaloca":vis_kamaloca,
    "tantraloka":vis_tantraloka_utkranti,
    "daimon":vis_daimon_at_death,
    "memory":vis_panoramic_memory,
    "judgment":vis_self_judgment,
    "deities":vis_peaceful_wrathful,
    "recognition":vis_recognition_liberation,
    "integration":vis_integration,
    "return":vis_return,
    "convergence":vis_convergence,
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
    Scene("The Dissolution of Elements",
          "Earth, water, fire, air, ether — each releases its hold on consciousness.",
          9.0,"dissolution",{}),
    Scene("The Gap",
          "Between identities there is a gap. The traditions call it bardo, kamaloca, or the threshold.",
          8.0,"dissolution",{}),
    Scene("Release",
          "What you called yourself begins to unbind. The elements return to their source.",
          8.5,"dissolution",{}),

    Scene("The Tibetan Book of the Dead",
          "The bardos are not places. They are gaps between one identity and the next.",
          9.0,"tibetan",{}),
    Scene("Chikhai Bardo",
          "The first bardo: the moment of death. Clear light appears — if you recognize it, you are free.",
          9.5,"tibetan",{}),
    Scene("Chonyid Bardo",
          "The second bardo: visions of peaceful and wrathful deities. They are your own mind's contents.",
          10.0,"tibetan",{}),
    Scene("Sidpa Bardo",
          "The third bardo: the search for rebirth. Desire pulls consciousness back into form.",
          9.0,"tibetan",{}),

    Scene("The Egyptian Book of the Dead",
          "The soul navigates the Duat — a landscape of judgment, transformation, and renewal.",
          9.0,"egyptian",{}),
    Scene("The Weighing of the Heart",
          "Your heart is weighed against the feather of Ma'at. You are the one who knows the verdict.",
          9.5,"egyptian",{}),
    Scene("The Negative Confession",
          "You declare what you have not done. The declaration reshapes your soul.",
          8.5,"egyptian",{}),
    Scene("The Field of Reeds",
          "Those who pass through judgment enter a world made of their own fulfilled nature.",
          9.0,"egyptian",{}),

    Scene("Kamaloca (Steiner)",
          "The soul region where desire burns away. Nothing punishes but your own attachments.",
          9.0,"kamaloca",{}),
    Scene("The Purification of Desire",
          "What you wanted but could not have — you experience fully in the soul world.",
          9.5,"kamaloca",{}),
    Scene("The Panorama of Life",
          "Your entire life appears as a single moment. Every action, every thought, every omission.",
          9.5,"kamaloca",{}),
    Scene("The Threshold of Spirit",
          "When desire is spent, the soul stands ready for its next embodiment or its freedom.",
          9.0,"kamaloca",{}),

    Scene("Utkrānti (Tantraloka)",
          "The ascent of consciousness through the cakras at the moment of death.",
          9.0,"tantraloka",{}),
    Scene("The Snake Uncoils",
          "Kundalini does not rise — it withdraws. Consciousness contracts upward through the spine.",
          9.5,"tantraloka",{}),
    Scene("The Crown Opening",
          "At the crown, the subtle body releases. The knower becomes what it always knew.",
          9.0,"tantraloka",{}),
    Scene("Recognition at the Threshold",
          "If you recognize the light as your own nature, you do not return. If you turn back, you choose rebirth.",
          10.0,"tantraloka",{}),

    Scene("The Daimon at Death",
          "Socrates: the daimon that guided you in life meets you at death.",
          8.5,"daimon",{}),
    Scene("The Guide",
          "The being you encounter is not a stranger. It is your own deeper self wearing a face you can bear.",
          9.5,"daimon",{}),
    Scene("The Question",
          "The daimon asks: what have you become? The answer determines your next world.",
          9.0,"daimon",{}),

    Scene("Panoramic Memory Review",
          "Near-death experiencers report the same phenomenon: your entire life appears at once.",
          9.0,"memory",{}),
    Scene("No Judgment, Only Seeing",
          "You do not feel judged. You see what you did and what you omitted — and you feel the effects on others.",
          10.0,"memory",{}),
    Scene("The Instant of Recognition",
          "A lifetime compressed into a single act of understanding. Time collapses into meaning.",
          9.5,"memory",{}),

    Scene("Self-Judgment",
          "You are the judge. The standard is not divine law — it is the law of your own becoming.",
          9.0,"judgment",{}),
    Scene("The Mirror",
          "The afterlife does not punish. It reveals. And revelation is its own consequence.",
          8.5,"judgment",{}),
    Scene("Mercy",
          "The judgment is always merciful because the judge is finally you — and you understand.",
          9.0,"judgment",{}),

    Scene("Peaceful and Wrathful Deities",
          "The bardo deities are projections of your own mind — beautiful and terrifying by turn.",
          9.5,"deities",{}),
    Scene("Projection",
          "What appears as external is internal. The wrathful deity is your own unexamined fear.",
          9.0,"deities",{}),
    Scene("Recognition Frees",
          "The moment you recognize the deity as your own nature — it dissolves into light.",
          9.0,"deities",{}),

    Scene("Recognition is Liberation",
          "The central insight of every tradition: seeing what is really happening frees you.",
          9.5,"recognition",{}),
    Scene("I Am This",
          "Not 'I see the light' but 'I AM the light.' Recognition is identity.",
          9.5,"recognition",{}),
    Scene("The Door",
          "The threshold is not a place you arrive at. It is a realization you become.",
          9.0,"recognition",{}),

    Scene("Integration",
          "What was fragmented becomes whole. The soul recomposes itself.",
          9.0,"integration",{}),
    Scene("The Soul Re-membered",
          "All the parts of yourself that were scattered by life gather again.",
          9.0,"integration",{}),
    Scene("Wholeness",
          "Integration is not the end. It is the condition for what comes next.",
          8.5,"integration",{}),

    Scene("Return and Rebirth",
          "Having seen the other side, some choose to return. The soul elects its next experience.",
          9.0,"return",{}),
    Scene("The Choice",
          "Rebirth is not punishment. It is the soul's desire to continue learning through form.",
          9.0,"return",{}),
    Scene("The Return",
          "Those who return from NDE bring back the same message: there is nothing to fear.",
          8.5,"return",{}),

    Scene("The Convergence",
          "Six traditions, one structure. The convergence is the strongest argument.",
          9.5,"convergence",{}),
    Scene("Not Cultural Costume",
          "These are not cultural costumes on a neurological event. They are reports from the same territory.",
          10.0,"convergence",{}),
    Scene("The Shared Map",
          "Dissolution, encounter, judgment, recognition, integration, return — the map is consistent.",
          9.5,"convergence",{}),

    Scene("Science Bridge",
          "Near-death studies confirm the structure: life review, light, encounter, decision.",
          9.0,"bridge",{}),
    Scene("Research",
          "Greyson, Moody, van Lommel, Parnia — their data matches the traditional accounts.",
          9.5,"bridge",{}),
    Scene("The Open Question",
          "Science describes the phenomena. The traditions offer the metaphysics. Both are needed.",
          10.0,"bridge",{}),

    Scene("Caution",
          "The convergence is real — but interpretation remains open.",
          8.5,"caution",{}),
    Scene("Not Proof",
          "The structure being cross-cultural does not prove an afterlife. It proves the structure is real.",
          9.0,"caution",{}),
    Scene("Discipline",
          "Keep the claim disciplined: six traditions describe the same sequence. That is the fact.",
          8.5,"caution",{}),

    Scene("Return to the Body",
          "The dissolved form re-assembles. The journey ends where it began.",
          8.0,"final",{}),
    Scene("The Continuity",
          "The body was always a temporary residence. Consciousness is the inhabitant.",
          8.5,"final",{}),
    Scene("The Structure Remains",
          "Death systems around the world tell the same story because the story is true.",
          9.0,"final",{}),
    Scene("Closing",
          "Every death system says the same thing: dissolution, encounter, recognition, return. The structure is real because the territory is real. What you meet at death is your own deeper nature.",
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
    output=OUTPUT/"death_systems.mp4"
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
        "title":"every death system says the same thing",
        "subtitle":"Six traditions, one structure: the afterlife is a recognition event",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"dissolving body outline that reforms as light",
        "visual_arc":[
            "dissolution","bardo","judgment","recognition",
            "integration","return","convergence"
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
