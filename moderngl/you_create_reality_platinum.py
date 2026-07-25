#!/usr/bin/env python3
"""
YOU CREATE YOUR OWN REALITY — The Foundational Claim
Seth, Silver, and the creative power of consciousness.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
You create your own reality — every moment, without exception.
There is no exception to this rule. What you believe, expect, and feel
shapes what appears as experience. The world you see is not independent
of the one who sees. Consciousness is not a passive receiver of reality.
It is the active producer of every experience.

For Seth, this is not a metaphor. It is the literal structure of reality.

FILM THESIS
-----------
The modern picture often runs:

reality exists independently
→ we perceive it
→ we react to it
→ we are victims of circumstance

The Seth/Silver picture can be staged as:

consciousness is the primary reality
→ beliefs form expectations
→ expectations shape perception
→ perception becomes experience
→ experience confirms the belief
→ the loop continues

To change your experience, change your belief. This is radical responsibility.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a golden thread of intent weaving through every scene.
• Final reveal: the thread was always your own attention — and you are the weaver.

OUTPUT
------
output_you_create_reality/
  frames/
  scenes/
  you_create_reality.mp4
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
OUTPUT = ROOT / "output_you_create_reality"
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

def draw_intent_thread(im,cx,cy,length,progress,color=GOLD):
    pts=[]
    for i in range(100):
        q=i/99
        a=q*math.tau*2
        x=cx-length/2+q*length
        y=cy+math.sin(a+math.pi*progress)*(15+25*math.sin(q*math.pi))
        pts.append((x,y))
    glow_line(im,partial(pts,progress),color,width=3,alpha=200,blur=10)

def draw_belief_field(im,cx,cy,radius,progress,color):
    d=ImageDraw.Draw(im)
    for i in range(6):
        a=i*math.tau/6+progress*.5
        q=clamp(progress*6-i*.08)
        if q<=0: continue
        x=cx+math.cos(a)*radius*q
        y=cy+math.sin(a)*radius*q*.5
        d.line((cx,cy,x,y),fill=(*color,int(180*q)),width=3)
        glow_circle(im,x,y,6+4*q,color,int(160*q),8)

def draw_probable_branches(im,cx,cy,progress,count=7):
    d=ImageDraw.Draw(im)
    for i in range(count):
        a=i*math.tau/count+progress*.3
        q=clamp(progress*3-i*.06)
        if q<=0: continue
        x=cx+math.cos(a)*(60+100*q)
        y=cy+math.sin(a)*(60+100*q)*.35
        col=mix(CYAN,GOLD,i/count)
        d.line((cx,cy,x,y),fill=(*col,int(170*q)),width=2)
        glow_circle(im,x,y,7,col,int(150*q),7)


# =============================================================================
# VISUALS
# =============================================================================

def vis_claim(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,300,q,GOLD)
    glow_circle(im,cx,cy,18,GOLD,int(180*q),12)
    seal(im,"THE FOUNDATIONAL CLAIM",
         "you create your own reality — every moment, without exception")

def vis_belief(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,250,q,GOLD)
    draw_belief_field(im,cx,cy,120,q,CYAN)
    seal(im,"BELIEFS FORM EXPERIENCE",
         "what you believe shapes what you perceive — belief precedes evidence")

def vis_expectation(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,200,q,GOLD)
    d=ImageDraw.Draw(im)
    for i in range(3):
        qc=clamp(q*3-i*.15)
        if qc<=0: continue
        x=cx+(i-1)*w*.18
        glow_circle(im,x,cy,10+8*qc,GREEN,int(180*qc),9)
        d.line((cx,cy,x,cy),fill=(*GREEN,int(150*qc)),width=3)
    seal(im,"EXPECTATION DIRECTS EVENTS",
         "reality conforms to what you anticipate — the mind is a magnet")

def vis_emotion(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,150,q,GOLD)
    for i in range(8):
        a=i*math.tau/8+t*.1
        qc=clamp(q*4-i*.05)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+80*qc)
        y=cy+math.sin(a)*(30+80*qc)*.4
        col=mix(CRIMSON,GOLD,.5+.5*math.sin(t+i))
        d.ellipse((x-10*qc,y-10*qc,x+10*qc,y+10*qc),fill=(*col,int(180*qc)))
    seal(im,"EMOTION IS THE ENGINE",
         "intensity determines speed of manifestation — feeling creates")

def vis_probable(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,220,q,GOLD)
    draw_probable_branches(im,cx,cy,q,8)
    seal(im,"PROBABLE REALITIES",
         "you choose among infinite realities each moment — all exist now")

def vis_responsibility(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,280,q,GOLD)
    rings=4
    for i in range(rings):
        qc=clamp(q*rings-i)
        if qc<=0: continue
        rad=30+i*35
        glow_circle(im,cx,cy,rad,mix(GOLD,CYAN,i/rings),int(120*qc),6+i*3)
        d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad),
                  outline=(*mix(GOLD,CYAN,i/rings),int(180*qc)),width=2)
    seal(im,"RADICAL RESPONSIBILITY",
         "if you create it, you can change it — freedom is the other side of creation")

def vis_freedom(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,320,q,GOLD)
    d=ImageDraw.Draw(im)
    for i in range(12):
        a=i*math.tau/12+t*.06
        qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+110*qc)
        y=cy+math.sin(a)*(20+110*qc)*.35
        glow_circle(im,x,y,5+3*qc,PALE_GOLD,int(140*qc),5)
    seal(im,"YOU ARE NOT AT THE MERCY",
         "you ARE the reality that mercy comes from — creator, not victim")

def vis_past_present(im,u,t,p):
    w,h=im.size; cx,cy=w*.30,h*.40; cx2,cy2=w*.70,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,120,q,CRIMSON)
    draw_intent_thread(im,cx2,cy2,120,q,GOLD)
    if q>.3:
        pts=[]
        for i in range(60):
            f=i/59
            x=lerp(cx+60,cx2-60,f)
            y=lerp(cy,cy2,f)+math.sin(f*math.tau*3+t*2)*20
            pts.append((x,y))
        glow_line(im,partial(pts,(q-.3)*1.4),PALE_GOLD,width=2,alpha=160,blur=8)
    seal(im,"PAST AND PRESENT ARE ONE",
         "the present recreates the past — your current belief changes history")

def vis_intention(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_intent_thread(im,cx,cy,200,q,GOLD)
    for i in range(5):
        a=i*math.tau/5
        qc=clamp(q*3-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*90*qc
        y=cy+math.sin(a)*90*qc*.4
        d.line((cx,cy,x,y),fill=(*CYAN,int(160*qc)),width=2)
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),CYAN,2,8)
    seal(im,"INTENTION IS THE ARROW",
         "focused intent directs the field — aim before action")

def vis_dreaming_self(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_intent_thread(im,cx,cy,180,q,VIOLET)
    for i in range(6):
        a=i*math.tau/6+t*.08
        rad=40+20*math.sin(t+i)
        x=cx+math.cos(a)*rad*(.6+.4*q)
        y=cy+math.sin(a)*rad*.4
        glow_circle(im,x,y,8+4*q,PALE_VIOLET,int(150*q),8)
    seal(im,"THE DREAMING SELF CREATES",
         "in sleep, you choose the probable realities you will wake into")

def vis_daily_creation(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_intent_thread(im,cx,cy,260,q,GOLD)
    hours=12
    for i in range(hours):
        a=i*math.tau/hours-math.pi/2+t*.05
        qc=clamp(q*3-i*.04)
        if qc<=0: continue
        rad=20+100*qc
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        d.line((cx,cy,x,y),fill=(*GOLD,int(120*qc)),width=1)
        glow_circle(im,x,y,3,PALE_GOLD,int(100*qc),4)
    seal(im,"YOU CREATE EVERY DAY",
         "reality is not a one-time event — you recreate it each morning")

def vis_belief_change(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_intent_thread(im,cx,cy,150,q,GOLD)
    before=(cx-60,cy); after=(cx+60,cy)
    qc=smoothstep(.2,.8,q)
    glow_circle(im,*before,12,CRIMSON,int(200*(1-qc)),9)
    glow_circle(im,*after,12,GREEN,int(200*qc),9)
    if qc>.1:
        pts=[(before[0],before[1]),(cx,cy-50*qc),(after[0],after[1])]
        glow_line(im,partial(pts,qc),GOLD,width=3,alpha=180,blur=9)
    seal(im,"CHANGE THE BELIEF",
         "the fastest way to change experience — choose a new assumption")

def vis_collective(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    points=[]
    for i in range(16):
        a=i*math.tau/16
        rad=50+80*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        glow_circle(im,x,y,6+3*q,CYAN if i%2==0 else GOLD,int(150*q),7)
        points.append((x,y))
    if len(points)>1:
        glow_line(im,partial(points,q),PALE_GOLD,width=2,alpha=120,blur=6)
    seal(im,"COLLECTIVE BELIEF",
         "shared beliefs create consensus reality — culture is a mass assumption")

def vis_you_are_free(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_intent_thread(im,cx,cy,350,q,GOLD)
    d=ImageDraw.Draw(im)
    for i in range(14):
        a=i*math.tau/14+t*.04
        qc=clamp(q*5-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+120*qc)
        y=cy+math.sin(a)*(40+120*qc)*.35
        d.line((cx,cy,x,y),fill=(*mix(GOLD,VIOLET,i/14),int(160*qc)),width=2)
        glow_circle(im,x,y,5,PALE_GOLD,int(130*qc),5)
    seal(im,"THE PRISON IS A BELIEF",
         "the only cage is the assumption that you are caged — freedom is your nature")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs):
        glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"PLACEBO EFFECT",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"CONSCIOUS CREATION",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE CONFIRMS: BELIEF ALTERS OUTCOME",
         "the placebo effect is the empirical evidence for the creative power of belief")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("YOU CREATE YOUR OWN REALITY","SUPPORTED BY NDE DATA",GREEN),
        ("YOU CREATE OTHER PEOPLE'S REALITY","NOT SUPPORTED",CRIMSON),
        ("YOU CAN MANIFEST ANYTHING INSTANTLY","NOT SUPPORTED BY EXPERIENCE",CRIMSON),
        ("YOU CREATE YOUR PERCEPTUAL REALITY","SUPPORTED BY COGNITIVE SCIENCE",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"THIS IS NOT MAGICAL THINKING",
         "you create your reality through belief, expectation, and feeling — not by bypassing causation")


VISUALS: dict[str,Callable] = {
    "claim":vis_claim,
    "belief":vis_belief,
    "expectation":vis_expectation,
    "emotion":vis_emotion,
    "probable":vis_probable,
    "responsibility":vis_responsibility,
    "freedom":vis_freedom,
    "past_present":vis_past_present,
    "intention":vis_intention,
    "dreaming_self":vis_dreaming_self,
    "daily_creation":vis_daily_creation,
    "belief_change":vis_belief_change,
    "collective":vis_collective,
    "you_are_free":vis_you_are_free,
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
    Scene("The Foundational Claim",
          "You create your own reality — every moment, without exception.",
          9.0,"claim",{}),
    Scene("No Exceptions",
          "The rule has no exceptions. Even the experience of being a victim is created.",
          8.5,"claim",{}),
    Scene("Consciousness is Primary",
          "Consciousness is not a product of reality. Reality is a product of consciousness.",
          8.5,"claim",{}),

    Scene("Beliefs Form Experience",
          "What you believe shapes what you perceive. Belief precedes evidence.",
          8.5,"belief",{}),
    Scene("The Invisible Lens",
          "Belief is a lens. You do not see the lens. You see through it.",
          8.0,"belief",{}),
    Scene("The Self-Fulfilling Prophecy",
          "Every belief carries its own confirmation. The world arranges itself to prove you right.",
          9.0,"belief",{}),
    Scene("Core Beliefs",
          "Deepest assumptions create the architecture of your reality. Change them, change everything.",
          9.0,"belief",{}),

    Scene("Expectation Directs Events",
          "Reality conforms to what you anticipate. The mind is a magnet.",
          8.5,"expectation",{}),
    Scene("The Preceding Assumption",
          "What you expect to happen prepares the field for its arrival.",
          8.5,"expectation",{}),
    Scene("Anticipation Shapes Outcome",
          "Expectation is not passive waiting. It is active molding of what comes.",
          8.5,"expectation",{}),

    Scene("Emotion is the Engine",
          "Intensity determines the speed of manifestation. Feeling creates.",
          8.5,"emotion",{}),
    Scene("Feeling is the Language",
          "The inner self speaks in feeling, not words. Attention plus feeling equals creation.",
          8.5,"emotion",{}),
    Scene("The Emotional Tone",
          "The emotional quality of a belief determines the quality of the experience it produces.",
          8.5,"emotion",{}),

    Scene("Probable Realities",
          "You choose among infinite realities each moment. All exist, now.",
          9.0,"probable",{}),
    Scene("The Threshold of Choice",
          "At every moment, a fork. You select which probability to actualize.",
          8.5,"probable",{}),
    Scene("The Unchosen Paths",
          "The paths you did not take are still real. They are being lived by other versions of you.",
          9.0,"probable",{}),

    Scene("Radical Responsibility",
          "If you create it, you can change it. Freedom is the other side of creation.",
          9.0,"responsibility",{}),
    Scene("Ownership",
          "Taking responsibility for your reality is not blame. It is empowerment.",
          8.5,"responsibility",{}),
    Scene("The Liberating Truth",
          "If you are the creator, you are not the victim. And you can create differently.",
          8.5,"responsibility",{}),

    Scene("Past and Present are One",
          "The present recreates the past. Your current belief changes history.",
          8.5,"past_present",{}),
    Scene("Retroactive Creation",
          "The past is not fixed. Your present understanding rewrites what happened.",
          8.5,"past_present",{}),
    Scene("Now is the Point of Power",
          "The present is the only point where power exists. All change begins here.",
          8.5,"past_present",{}),

    Scene("Intention is the Arrow",
          "Focused intent directs the field. Aim before action.",
          8.0,"intention",{}),
    Scene("The Directed Thread",
          "Intention is the golden thread that weaves potential into actuality.",
          8.5,"intention",{}),
    Scene("Clarity",
          "Unclear intention produces unclear results. Precision of aim is precision of creation.",
          8.5,"intention",{}),

    Scene("The Dreaming Self Creates",
          "In sleep, you choose the probable realities you will wake into.",
          8.5,"dreaming_self",{}),
    Scene("Nightly Creation",
          "Each night, the dreaming self selects from the field of probabilities.",
          8.5,"dreaming_self",{}),
    Scene("The Dreamer Wakes",
          "You carry the choices of the dreaming self into the day — whether you remember or not.",
          8.5,"dreaming_self",{}),

    Scene("You Create Every Day",
          "Reality is not a one-time event. You recreate it each morning.",
          8.0,"daily_creation",{}),
    Scene("Continuous Creation",
          "Creation is not a past event. It is happening now and always.",
          8.0,"daily_creation",{}),
    Scene("The Daily Reset",
          "Each morning, you choose again. Each moment, the world is born anew.",
          8.5,"daily_creation",{}),

    Scene("Change the Belief",
          "The fastest way to change experience: choose a new assumption.",
          8.5,"belief_change",{}),
    Scene("The Pivot",
          "A single shifted assumption can reorganize an entire reality.",
          8.5,"belief_change",{}),
    Scene("The New Lens",
          "When the lens changes, the world seen through it changes.",
          8.0,"belief_change",{}),

    Scene("Collective Belief",
          "Shared beliefs create consensus reality. Culture is a mass assumption.",
          9.0,"collective",{}),
    Scene("Consensus Trance",
          "Most people live inside a reality they did not individually choose — they absorbed it.",
          9.0,"collective",{}),
    Scene("Cultural Creation",
          "The collective dream is the most powerful creative force on the planet.",
          8.5,"collective",{}),

    Scene("The Prison is a Belief",
          "The only cage is the assumption that you are caged. Freedom is your nature.",
          9.0,"you_are_free",{}),
    Scene("The Open Door",
          "The cage has always been open. You were the one who believed it was locked.",
          9.0,"you_are_free",{}),
    Scene("You ARE the Creator",
          "The creator and the creation are one. You are the reality you seek.",
          9.5,"you_are_free",{}),

    Scene("Science Bridge",
          "The placebo effect is the empirical evidence for the creative power of belief.",
          9.0,"bridge",{}),
    Scene("Expectation Physiology",
          "What you expect physiologically changes your body. Belief becomes biology.",
          9.0,"bridge",{}),
    Scene("The Open Question",
          "If belief can heal the body, what else can it create? The horizon is not yet mapped.",
          9.5,"bridge",{}),

    Scene("Caution",
          "You create your reality — not the reality of others. Co-creation is a collaboration.",
          8.5,"caution",{}),
    Scene("The Discipline of Creation",
          "Creation is not wishful thinking. It is the alignment of belief, expectation, and feeling.",
          8.5,"caution",{}),
    Scene("The Practice",
          "You create your reality every moment. The practice is to create consciously.",
          8.5,"caution",{}),

    Scene("Return to the Thread",
          "The golden thread of intent weaves through every scene.",
          8.0,"claim",{}),
    Scene("The Weaver",
          "The thread is your attention. You are the weaver.",
          8.5,"you_are_free",{}),
    Scene("Closing",
          "You create your own reality — every moment, without exception. There is no exception to this rule. What you believe, expect, and feel shapes what appears as experience. To change your experience, change your belief. This is not philosophy. It is the structure of reality.",
          10.0,"you_are_free",{}),
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
    output=OUTPUT/"you_create_reality.mp4"
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
        "title":"you create your own reality",
        "subtitle":"Seth, Silver, and the creative power of consciousness",
        "scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"golden thread of intent weaving through every scene",
        "visual_arc":[
            "claim","belief","expectation","emotion","probable realities",
            "responsibility","intention","freedom"
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
