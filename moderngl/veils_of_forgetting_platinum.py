#!/usr/bin/env python3
"""
THE VEIL OF FORGETTING — Why We Forget Who We Are
The mechanism of amnesia between lives.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
The veil of forgetting is not a punishment. It is a tool for extending free will.
If you remembered who you really are — an infinite creator spirit — every choice
would be predetermined by that knowledge. You would not experience genuine choice.
The veil creates the conditions for love, faith, and growth by hiding your own nature.

For the Law of One, for Seth, for Silver: the veil is the gift of not knowing.

FILM THESIS
-----------
The modern picture often runs:

birth → life → death → annihilation

The veiled picture can be staged as:

infinite awareness
→ the choice to forget
→ descent into limitation
→ the veil
→ struggle and growth
→ piercing the veil
→ remembering
→ return to infinite awareness

The veil is not an obstacle. It is the entire point.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a descending curtain that lifts and falls — the veil.
• Final reveal: the curtain was never opaque — you agreed not to see through it.

OUTPUT
------
output_veils_of_forgetting/
  frames/
  scenes/
  veils_of_forgetting.mp4
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
OUTPUT = ROOT / "output_veils_of_forgetting"
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

def draw_veil(im,progress,color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=lerp(h*1.2,h*(-.2),progress)
    for i in range(14):
        a=lerp(.4,.12,i/13)
        alpha=int(120*(1-abs(i/13-.5)*1.6)*progress)
        d.line((w*.08,y+i*h*.07,w*.92,y+i*h*.07),
               fill=(*color,alpha),width=4)

def draw_curtain_edge(im,progress,color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.42
    rad=60+140*progress
    d.arc((cx-rad,cy-rad*.6,cx+rad,cy+rad*.6),
          180,360,fill=(*color,int(180*progress)),width=3)


# =============================================================================
# VISUALS
# =============================================================================

def vis_veil_intro(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q,INK)
    cx,cy=w*.50,h*.40
    glow_circle(im,cx,cy,14,GOLD,int(150*(1-q)),10)
    seal(im,"THE VEIL OF FORGETTING",
         "the tool for extending free will — the gift of not knowing")

def vis_purpose(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q*.6,INK)
    cx,cy=w*.50,h*.40
    sp=[(cx+math.cos(i*math.tau/40)*(80+40*q),
         cy+math.sin(i*math.tau/40)*(80+40*q)*.4) for i in range(41)]
    glow_line(im,partial(sp,q),GOLD,3,190,10)
    seal(im,"WHY WE FORGET",
         "without forgetting, no real choice — the veil enables love")

def vis_before_veil(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    for i in range(9):
        a=i*math.tau/9+t*.06
        rad=30+80*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        col=mix(VIOLET,GOLD,i/8)
        d.line((cx,cy,x,y),fill=(*col,int(160*q)),width=2)
        glow_circle(im,x,y,5+3*q,col,int(150*q),6)
    seal(im,"BEFORE THE VEIL",
         "no separation between conscious and unconscious — direct knowing")

def vis_after_veil(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q*.8,INK)
    cx,cy=w*.50,h*.40
    glow_circle(im,cx,cy,8,GOLD,int(100*(1-q)),6)
    d=ImageDraw.Draw(im)
    d.ellipse((cx-50,cy-50,cx+50,cy+50),outline=(*INK,int(180*q)),width=2)
    seal(im,"AFTER THE VEIL",
         "third density — the density of choice, faith, and love")

def vis_thinning(im,u,t,p):
    w,h=im.size; q=ease(u)
    fade=smoothstep(0,.7,q)
    draw_veil(im,(1-fade)*.6,INK)
    cx,cy=w*.50,h*.40
    d=ImageDraw.Draw(im)
    for i in range(6):
        a=i*math.tau/6+t*.08
        rad=30+60*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        glow_circle(im,x,y,6+4*q,CYAN,int(180*q),8)
        d.line((cx,cy,x,y),fill=(*CYAN,int(140*q)),width=2)
    seal(im,"THE VEIL IS THINNING",
         "as the planet moves to 4D, memory returns — the curtain lifts")

def vis_what_you_are(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    sp=[(cx+math.cos(i*math.tau/50)*(40+100*q),
         cy+math.sin(i*math.tau/50)*(40+100*q)*.35) for i in range(51)]
    glow_line(im,partial(sp,q),GOLD,4,220,14)
    if q>.6:
        centered(d,(cx,cy),"∞",font(FONT_SERIF_BOLD,int(h*.10)),
                 (*GOLD,int(200*(q-.6)/.4)))
    seal(im,"WHAT YOU REALLY ARE",
         "the infinite creator experiencing itself — veiled and unveiling")

def vis_piercing(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q*.5,INK)
    cx,cy=w*.50,h*.40
    glow_circle(im,cx,cy,16+8*q,GOLD,int(200*q),12)
    if q>.4:
        pts=[]
        for i in range(100):
            f=i/99
            x=cx+math.cos(f*math.tau*3+t)*80*f
            y=cy+math.sin(f*math.tau*3+t)*80*f*.4
            pts.append((x,y))
        glow_line(im,partial(pts,(q-.4)*1.6),GOLD,3,200,10)
    seal(im,"PIERCING THE VEIL",
         "meditation, dreams, art, love — the curtain tears")

def vis_darkness(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q,INK)
    cx,cy=w*.50,h*.40
    d=ImageDraw.Draw(im)
    for i in range(10):
        a=i*math.tau/10+t*.05
        rad=20+40*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        d.ellipse((x-8*q,y-8*q,x+8*q,y+8*q),fill=(*INK,int(120*q)))
    seal(im,"THE DARKNESS BEFORE BIRTH",
         "the soul chooses to forget — the descent into matter")

def vis_choice_enables(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    for i in range(3):
        a=(i-1)*.8
        qc=clamp(q*3-i*.2)
        if qc<=0: continue
        x=cx+math.cos(a)*120*qc
        y=cy+math.sin(a)*120*qc
        col=GREEN if i==1 else (CRIMSON if i==0 else CYAN)
        d.line((cx,cy,x,y),fill=(*col,int(180*qc)),width=3)
        glow_circle(im,x,y,8,col,int(170*qc),8)
    seal(im,"THE VEIL ENABLES CHOICE",
         "if you knew everything, no act would be truly free")

def vis_faith(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q*.3,INK)
    cx,cy=w*.50,h*.40
    d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,10,GOLD,int(160*q),8)
    for i in range(4):
        a=i*math.tau/4+t*.06
        rad=50+60*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        d.line((cx,cy,x,y),fill=(*PALE_GOLD,int(140*q)),width=2)
        glow_circle(im,x+20,y+20,5,PALE_GOLD,int(100*q),5)
    seal(im,"FAITH IS THE BRIDGE",
         "trust is the only way across the veil — love requires not knowing")

def vis_gradual(im,u,t,p):
    w,h=im.size; q=ease(u)
    stages=5; cx,cy=w*.50,h*.40
    for i in range(stages):
        qc=clamp(q*stages-i)
        if qc<=0: continue
        x=lerp(w*.15,w*.85,i/(stages-1))
        glow_circle(im,x,cy,6+4*qc,mix(CRIMSON,GOLD,i/(stages-1)),
                    int(180*qc),7)
    seal(im,"GRADUAL AWAKENING",
         "the veil does not lift all at once — it thins in layers")

def vis_service(im,u,t,p):
    w,h=im.size; q=ease(u)
    cx,cy=w*.50,h*.40
    d=ImageDraw.Draw(im)
    draw_veil(im,q*.2,INK)
    for i in range(8):
        a=i*math.tau/8+t*.04
        qc=clamp(q*3-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+80*qc)
        y=cy+math.sin(a)*(40+80*qc)*.35
        col=mix(CYAN,GOLD,i/7)
        d.line((cx,cy,x,y),fill=(*col,int(140*qc)),width=2)
        d.ellipse((x-12*qc,y-12*qc,x+12*qc,y+12*qc),
                  outline=(*col,int(160*qc)),width=2)
    seal(im,"SERVICE TO OTHERS",
         "the veil makes compassion possible — you cannot see the other's wounds")

def vis_remembering(im,u,t,p):
    w,h=im.size; q=ease(u)
    cx,cy=w*.50,h*.40
    draw_veil(im,1-q,INK)
    d=ImageDraw.Draw(im)
    sp=[(cx+math.cos(i*math.tau/60)*(30+100*q),
         cy+math.sin(i*math.tau/60)*(30+100*q)*.35) for i in range(61)]
    glow_line(im,partial(sp,q),GOLD,4,230,14)
    seal(im,"REMEMBERING IS RISING",
         "each moment of recognition lifts the veil another millimeter")

def vis_gift(im,u,t,p):
    w,h=im.size; q=ease(u)
    draw_veil(im,q*.4,INK)
    cx,cy=w*.50,h*.40
    glow_circle(im,cx,cy,12,GOLD,int(180*(1-q*.5)),10)
    d=ImageDraw.Draw(im)
    for i in range(8):
        a=i*math.tau/8+r*.5
        x=cx+math.cos(a)*80*q; y=cy+math.sin(a)*80*q*.4
        d.line((cx,cy,x,y),fill=(*PALE_GOLD,int(120*q)),width=2)
    seal(im,"THE GIFT OF FORGETTING",
         "to begin again, fresh — this is the soul's mercy to itself")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"DISSOCIATIVE AMNESIA",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"METAPHYSICAL VEIL",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"TRAUMATIC FORGETTING IS THE EARTHLY ANALOGUE",
         "the mind can forget its own history — the soul can forget its own nature")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("THE VEIL IS NOT DIVINE PUNISHMENT","IT IS A VOLUNTARY CHOICE",CRIMSON),
        ("FORGETTING IS NOT FAILURE","IT IS THE TERMS OF THE GAME",GREEN),
        ("ALL SOULS CHOSE THE VEIL","CENTRAL CLAIM OF LAW OF ONE",CYAN),
        ("THE VEIL IS LIFTING NOW","SUPPORTED BY AWAKENING REPORTS",GREEN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"THE VEIL IS NOT AN ENEMY",
         "it is a gift you gave yourself — and you can begin to lift it anytime")


VISUALS: dict[str,Callable] = {
    "veil_intro":vis_veil_intro,
    "purpose":vis_purpose,
    "before":vis_before_veil,
    "after":vis_after_veil,
    "thinning":vis_thinning,
    "what_you_are":vis_what_you_are,
    "piercing":vis_piercing,
    "darkness":vis_darkness,
    "choice":vis_choice_enables,
    "faith":vis_faith,
    "gradual":vis_gradual,
    "service":vis_service,
    "remembering":vis_remembering,
    "gift":vis_gift,
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
    Scene("The Veil of Forgetting",
          "The tool for extending free will — the gift of not knowing.",
          8.5,"veil_intro",{}),
    Scene("The Curtain",
          "Between who you are and who you experience yourself to be, there is a veil.",
          8.0,"veil_intro",{}),
    Scene("The Agreement",
          "You chose the veil before you entered this life. It was not imposed.",
          8.5,"veil_intro",{}),

    Scene("Why We Forget",
          "Without forgetting, no real choice. The veil enables love.",
          8.5,"purpose",{}),
    Scene("The Purpose",
          "If you remembered your infinite nature, every action would be a foregone conclusion.",
          9.0,"purpose",{}),
    Scene("The Gift of Not Knowing",
          "Not knowing who you are makes the discovery meaningful.",
          8.5,"purpose",{}),

    Scene("Before the Veil",
          "No separation between conscious and unconscious — direct knowing.",
          8.5,"before",{}),
    Scene("The Unitary State",
          "Before the veil, there is no subject and object. There is only knowing.",
          8.5,"before",{}),
    Scene("The Choice to Descend",
          "The soul chose to enter limitation. The veil was the door.",
          8.5,"before",{}),

    Scene("After the Veil",
          "Third density — the density of choice, faith, and love.",
          8.0,"after",{}),
    Scene("The Density of Choice",
          "In this density, you cannot see the spiritual world. You must choose without proof.",
          9.0,"after",{}),
    Scene("Faith is the Currency",
          "Without direct knowledge, faith becomes the medium of growth.",
          8.5,"after",{}),

    Scene("The Veil is Thinning",
          "As the planet moves to 4D, memory returns. The curtain lifts.",
          9.0,"thinning",{}),
    Scene("The Harvest",
          "The veiled density is ending. The choice now is which density you will inhabit.",
          9.0,"thinning",{}),
    Scene("Memory Returning",
          "More people remember their dreams, their past lives, their true nature.",
          8.5,"thinning",{}),

    Scene("What You Really Are",
          "The infinite creator experiencing itself — veiled and unveiling.",
          9.0,"what_you_are",{}),
    Scene("The Creator Forgets",
          "The infinite created the veil so it could experience finitude.",
          9.0,"what_you_are",{}),
    Scene("The Game of Consciousness",
          "You are God playing at being human. The veil makes the game compelling.",
          9.0,"what_you_are",{}),

    Scene("Piercing the Veil",
          "Meditation, dreams, art, love — the curtain tears.",
          8.5,"piercing",{}),
    Scene("The Tears",
          "In moments of intense love or beauty, the veil thins to transparency.",
          8.5,"piercing",{}),
    Scene("Glimpses",
          "These are not anomalies. They are previews of what is always the case.",
          8.5,"piercing",{}),

    Scene("The Darkness Before Birth",
          "The soul chooses to forget. The descent into matter.",
          8.5,"darkness",{}),
    Scene("The Descent",
          "To enter a body is to enter forgetting. The light dims gradually.",
          8.5,"darkness",{}),
    Scene("Birth Trauma",
          "The moment of birth is the moment the veil snaps into place.",
          8.0,"darkness",{}),

    Scene("The Veil Enables Choice",
          "If you knew everything, no act would be truly free.",
          8.5,"choice",{}),
    Scene("Genuine Freedom",
          "Freedom requires uncertainty. The veil creates the condition for real choice.",
          8.5,"choice",{}),
    Scene("The Fork",
          "Without the veil, every fork would show its destination. The choice would vanish.",
          8.5,"choice",{}),

    Scene("Faith is the Bridge",
          "Trust is the only way across. Love requires not knowing.",
          8.5,"faith",{}),
    Scene("The Leap",
          "Faith is not belief without evidence. It is the courage to act in uncertainty.",
          8.5,"faith",{}),
    Scene("The Bridge of Trust",
          "You cannot see the other side. But you step forward anyway. That is faith.",
          8.5,"faith",{}),

    Scene("Gradual Awakening",
          "The veil does not lift all at once. It thins in layers.",
          8.5,"gradual",{}),
    Scene("Incremental Revelation",
          "You are not given more than you can integrate. The veil lifts in stages.",
          8.5,"gradual",{}),
    Scene("Patience",
          "Awakening is a process, not an event. Each layer reveals the next.",
          8.5,"gradual",{}),

    Scene("Service to Others",
          "The veil makes compassion possible — you cannot see the other's wounds.",
          8.5,"service",{}),
    Scene("Blind Compassion",
          "If you could see another's soul, helping them would be calculation, not love.",
          9.0,"service",{}),
    Scene("The Hidden Wound",
          "You serve because you choose to, not because you know the score.",
          8.0,"service",{}),

    Scene("Remembering is Rising",
          "Each moment of recognition lifts the veil another millimeter.",
          8.5,"remembering",{}),
    Scene("The Accumulation of Glimpses",
          "Glimpse by glimpse, the veil becomes gauze. Then memory returns.",
          8.5,"remembering",{}),
    Scene("The Inevitable Dawn",
          "Eventually, the veil dissolves entirely. You remember who you are.",
          9.0,"remembering",{}),

    Scene("The Gift of Forgetting",
          "To begin again, fresh — this is the soul's mercy to itself.",
          8.5,"gift",{}),
    Scene("Fresh Start",
          "Forgetting is not loss. It is the condition for genuine novelty.",
          8.5,"gift",{}),
    Scene("The Soul's Mercy",
          "You did not come here to remember. You came here to experience.",
          8.5,"gift",{}),

    Scene("Science Bridge",
          "Dissociative amnesia shows that consciousness can forget its own biography.",
          8.5,"bridge",{}),
    Scene("The Mechanism",
          "The mind can compartmentalize experience. The soul may do the same.",
          8.5,"bridge",{}),
    Scene("The Analogy",
          "If the mind can forget trauma, the soul can forget its origin.",
          8.5,"bridge",{}),

    Scene("Caution",
          "The veil is not an enemy to be destroyed. It is a gift to be understood.",
          8.5,"caution",{}),
    Scene("Gratitude",
          "Be grateful for the veil. It made possible everything you have experienced.",
          8.5,"caution",{}),
    Scene("The Return",
          "The veil is not removed. You simply see that it was never opaque.",
          9.0,"caution",{}),

    Scene("The Curtain Rises",
          "What was hidden is now revealed. You are the one who hid it.",
          8.5,"veil_intro",{}),
    Scene("Recognition",
          "The veil was always your own choice. You are free to lift it.",
          8.5,"remembering",{}),
    Scene("Closing",
          "The veil of forgetting is not a punishment. It is a tool for extending free will. You chose to forget so you could choose freely. And now, the remembering begins — not because the veil is torn away, but because you are ready to see through it.",
          10.0,"remembering",{}),
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
    subprocess.run([ffmpeg_path(),"-y","-framerate",str(fps),
        "-i",str(frame_dir/"%05d.jpg"),"-c:v","libx264","-preset","medium",
        "-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(output)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output

def render_scene(index,scene,fps,width,height,preview):
    frame_dir=FRAMES/f"scene_{index:03d}"
    frame_dir.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
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
    output=OUTPUT/"veils_of_forgetting.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0",
        "-i",str(txt),"-c","copy","-movflags","+faststart",str(output)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return output

def export_timeline():
    cursor=0.0; records=[]
    for index,scene in enumerate(SCENES,1):
        rec=asdict(scene); rec["scene_id"]=f"scene_{index:03d}"
        rec["start_seconds"]=round(cursor,3); cursor+=scene.duration
        rec["end_seconds"]=round(cursor,3); records.append(rec)
    path=OUTPUT/"narration_timeline.json"
    path.write_text(json.dumps({"title":"the veil of forgetting",
        "subtitle":"why we forget who we are — the mechanism of amnesia between lives",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],"continuity_object":"descending curtain — the veil",
        "visual_arc":["veil","purpose","before","after","thinning","piercing","remembering"],
        "scenes":records},indent=2,ensure_ascii=False),encoding="utf-8")
    return path

def make_contact_sheet(width,height):
    tw=320; th=int(tw*height/width); cols=4
    rows=math.ceil(len(SCENES)/cols); cell_h=th+48
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),IVORY)
    d=ImageDraw.Draw(sheet); lf=font(FONT_SANS_BOLD,14)
    for index,scene in enumerate(SCENES,1):
        count=max(2,round(scene.duration*DEFAULT_FPS))
        image=render_frame(scene,int(count*.72),count,width,height,index*10000+72)
        image.thumbnail((tw,th)); slot=index-1
        x=(slot%cols)*tw; y=(slot//cols)*cell_h
        sheet.paste(image,(x,y))
        d.text((x+8,y+th+7),f"{index:02d}  {scene.title}",font=lf,fill=INK)
    path=OUTPUT/"contact_sheet.jpg"; sheet.save(path,quality=94); return path

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS)
    p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()

def main():
    args=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if args.scene:
        if not 1<=args.scene<=len(SCENES): raise ValueError("scene out of range")
        print(render_scene(args.scene,SCENES[args.scene-1],
              args.fps,args.width,args.height,args.preview)); return
    rendered=[]
    for index,scene in enumerate(SCENES,1):
        print(f"[{index:02d}/{len(SCENES):02d}] {scene.title} ({scene.duration:.1f}s)")
        result=render_scene(index,scene,args.fps,args.width,args.height,args.preview)
        if not args.preview: rendered.append(result)
    if not args.no_contact_sheet:
        print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview: print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__": main()
