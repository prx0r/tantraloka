#!/usr/bin/env python3
"""
YOUR BODY IS THE DIAGRAM YOUR MIND KEEPS REDRAWING
A complete Platinum-house procedural visual essay.

Source:
expansion-essays/01_your_body_is_the_diagram_your_mind_keeps_redrawing.md

VISUAL THESIS
-------------
The lived body is not a passive anatomical readout. It is a dynamic geometry
assembled from interoception, proprioception, exteroception, memory, prediction,
and action. Ritual can deliberately redraw that geometry.

HOUSE RULES
-----------
• Every scene lasts 5–10 seconds.
• Every scene performs a visible transformation.
• Clean ivory scientific/gallery field.
• No slideshow layouts.
• Sparse labels only.
• Mature frame around u=0.72.
• Continuity object: a cyan body-perimeter that expands, contracts, and becomes mandala.

PALETTE ROLES
-------------
IVORY    open experiential field
CYAN     body schema / inferred perimeter
GOLD     sacred correspondence / Śrīcakra
GREEN    coordinated action / viable embodiment
VIOLET   interoceptive depth / latent body
CRIMSON  threat weighting / distorted precision
INK      fixed anatomical category

OUTPUT
------
output_body_diagram/
  frames/
  scenes/
  body_diagram.mp4
  narration_timeline.json
  contact_sheet.jpg
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"output_body_diagram"
FRAMES=OUTPUT/"frames"
SCENES_DIR=OUTPUT/"scenes"
DEFAULT_WIDTH=1280
DEFAULT_HEIGHT=720
DEFAULT_FPS=10

IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
SILVER=(180,187,194); PALE_SILVER=(226,229,232)
CYAN=(57,156,180); PALE_CYAN=(196,227,233)
GOLD=(194,156,72); PALE_GOLD=(236,219,175)
VIOLET=(109,83,153); PALE_VIOLET=(220,211,237)
CRIMSON=(162,58,69); PALE_CRIMSON=(231,198,202)
GREEN=(70,139,99); PALE_GREEN=(198,225,208)

FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0,hi=1): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b:return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)

def font(path,size):
    for c in (path,FONT_SERIF,FONT_SANS):
        try:return ImageFont.truetype(c,size)
        except OSError:pass
    return ImageFont.load_default()

def layer(size): return Image.new("RGBA",size,(0,0,0,0))

def field(w,h,seed):
    rng=np.random.default_rng(seed)
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=IVORY
    arr+=rng.normal(0,.9,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.39)/(h*.31))**2)*2)
    arr[...,1]+=halo*3.4; arr[...,2]+=halo*5.2
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")

def centered(d,xy,text,f,fill=INK): d.text(xy,text,font=f,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered(d,(w/2,h*.875),title,font(FONT_SERIF_BOLD,max(22,int(h*.04))),color)
    if subtitle:centered(d,(w/2,h*.923),subtitle,font(FONT_SANS,max(13,int(h*.019))),SOFT_INK)
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,45),width=2)

def glow_circle(im,x,y,r,color,alpha=170,blur=14):
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.ellipse((x-r,y-r,x+r,y+r),fill=(*color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).ellipse((x-r*.34,y-r*.34,x+r*.34,y+r*.34),
                               fill=(*mix(color,WHITE,.35),min(255,alpha+50)))
    im.alpha_composite(fg)

def glow_line(im,pts,color,width=4,alpha=210,blur=11):
    if len(pts)<2:return
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.line(pts,fill=(*color,alpha),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(color,WHITE,.08),min(255,alpha+25)),
                            width=width,joint="curve")
    im.alpha_composite(fg)

def partial(pts,a):
    if not pts:return []
    a=clamp(a)
    if a>=1:return pts
    k=a*(len(pts)-1); i=int(k); f=k-i
    out=list(pts[:i+1])
    if i+1<len(pts):
        p,q=pts[i],pts[i+1]
        out.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return out

def body_points(cx,cy,scale=1.0):
    return {
        "head":(cx,cy-145*scale,34*scale),
        "neck":(cx,cy-105*scale),
        "shoulder_l":(cx-72*scale,cy-75*scale),
        "shoulder_r":(cx+72*scale,cy-75*scale),
        "hand_l":(cx-155*scale,cy+20*scale),
        "hand_r":(cx+155*scale,cy+20*scale),
        "hip":(cx,cy+55*scale),
        "foot_l":(cx-55*scale,cy+170*scale),
        "foot_r":(cx+55*scale,cy+170*scale),
    }

def draw_body(d,cx,cy,scale,color,alpha=220,tool=0.0):
    p=body_points(cx,cy,scale)
    hx,hy,hr=p["head"]
    d.ellipse((hx-hr,hy-hr,hx+hr,hy+hr),outline=(*color,alpha),width=max(2,int(4*scale)))
    d.line((*p["neck"],*p["hip"]),fill=(*color,alpha),width=max(3,int(6*scale)))
    d.line((*p["shoulder_l"],*p["shoulder_r"]),fill=(*color,alpha),width=max(3,int(6*scale)))
    d.line((*p["shoulder_l"],*p["hand_l"]),fill=(*color,alpha),width=max(3,int(5*scale)))
    end_r=(lerp(p["hand_r"][0],p["hand_r"][0]+120*scale,tool),p["hand_r"][1])
    d.line((*p["shoulder_r"],*end_r),fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((*p["hip"],*p["foot_l"]),fill=(*color,alpha),width=max(3,int(5*scale)))
    d.line((*p["hip"],*p["foot_r"]),fill=(*color,alpha),width=max(3,int(5*scale)))
    return p,end_r

def sri_chakra_lines(cx,cy,r):
    tris=[]
    for direction,scale,offset in [(1,1.0,0),(-1,.92,0),(1,.72,0),(-1,.65,0),
                                   (1,.50,0),(-1,.43,0),(1,.30,0),(-1,.24,0),(1,.15,0)]:
        rr=r*scale
        if direction==1:
            tris.append([(cx,cy-rr),(cx-rr*.88,cy+rr*.55),(cx+rr*.88,cy+rr*.55),(cx,cy-rr)])
        else:
            tris.append([(cx,cy+rr),(cx-rr*.88,cy-rr*.55),(cx+rr*.88,cy-rr*.55),(cx,cy+rr)])
    return tris

def vis_lived_body(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.39; q=ease(u)
    draw_body(d,cx,cy,1.0,INK,190)
    # center/front/back/reach/perimeter
    glow_circle(im,cx,cy,12,CYAN,170,11)
    d.arc((cx-210*q,cy-190*q,cx+210*q,cy+210*q),200,340,fill=(*CYAN,int(180*q)),width=4)
    d.line((cx,cy-120,cx,cy+120),fill=(*GOLD,int(160*q)),width=3)
    centered(d,(cx,h*.68),"FIELD OF REACH",font(FONT_SANS_BOLD,16),CYAN)
    seal(im,"YOU EXPERIENCE A GEOMETRY, NOT A LIST OF ORGANS",
         "centre, front, back, reach, inside, and possible action")

def vis_body_to_mandala(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.95,INK,int(220*(1-q*.55)))
    for tri in sri_chakra_lines(cx,cy,190*q):
        d.line(tri,fill=(*GOLD,int(190*q)),width=3)
    if q>.6: glow_circle(im,cx,cy,12,GOLD,180,11)
    seal(im,"THE BODY IS THE ŚRĪCAKRA",
         "not a diagram added to flesh, but lived embodiment reread as mandala",GOLD)

def vis_correspondence(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.92,INK,180)
    mappings=[
        ("SENSES · HORSES",CYAN,-235,-90),("OBJECTS · ELEPHANTS",GOLD,235,-90),
        ("MIND · BOW",VIOLET,-235,100),("DESIRE · NOOSE",CRIMSON,235,100),
        ("KNOWER · OFFERING",GREEN,0,180)
    ]
    for i,(lab,col,ox,oy) in enumerate(mappings):
        local=clamp(q*len(mappings)-i)
        x,y=cx+ox,cy+oy
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,15),(*col,int(210*local)))
        d.line((x,y,cx,cy),fill=(*col,int(95*local)),width=2)
    seal(im,"THE ARCHITECTURE OF EXPERIENCE BECOMES RITUAL SPACE",
         "sensation, emotion, function, and knowledge are reclassified")

def vis_same_flesh_new_world(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.95,INK,180)
    left=["ORGAN","SYMPTOM","SHAMEFUL","MINE"]
    right=["DEITY","POWER","MANDALA","GATE"]
    for i,lab in enumerate(left):
        y=h*(.24+i*.10)
        centered(d,(w*.20,y),lab,font(FONT_SANS_BOLD,16),(*CRIMSON,int(210*(1-q*.65))))
    for i,lab in enumerate(right):
        y=h*(.24+i*.10)
        centered(d,(w*.80,y),lab,font(FONT_SANS_BOLD,16),(*GOLD,int(210*q)))
    glow_line(im,[(w*.32,h*.40),(cx,cy),(w*.68,h*.40)],mix(CRIMSON,GOLD,q),5,190,13)
    seal(im,"THE MATERIAL BODY STAYS · THE PHENOMENOLOGICAL WORLD CHANGES",
         "the same events enter another model")

def vis_streams(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    streams=[
        ("INTEROCEPTION",VIOLET,w*.17,h*.24),
        ("PROPRIOCEPTION",CYAN,w*.17,h*.40),
        ("EXTEROCEPTION",GOLD,w*.17,h*.56),
    ]
    for i,(lab,col,x,y) in enumerate(streams):
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,15),col)
        pts=[(x+100,y),(w*.38,y),(cx,cy)]
        glow_line(im,partial(pts,clamp(q*3-i)),col,4,180,10)
    draw_body(d,cx+160,cy,.7,INK,int(220*q))
    seal(im,"THE LIVED BODY EMERGES FROM NEGOTIATION",
         "noisy streams are weighted, compared, and integrated")

def vis_precision_scales(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    # balance beams
    d.line((cx-220,cy,cx+220,cy),fill=(*INK,180),width=5)
    pivot=(cx,cy+40)
    d.polygon([(cx-18,cy+40),(cx+18,cy+40),(cx,cy)],fill=(*INK,150))
    left_drop=lerp(0,90,q if p.get("mode","internal")=="internal" else 1-q)
    right_drop=90-left_drop
    d.line((cx-180,cy,cx-180,cy+left_drop),fill=(*VIOLET,190),width=4)
    d.line((cx+180,cy,cx+180,cy+right_drop),fill=(*GOLD,190),width=4)
    centered(d,(cx-180,cy+130),"INTERNAL",font(FONT_SANS_BOLD,16),VIOLET)
    centered(d,(cx+180,cy+130),"EXTERNAL",font(FONT_SANS_BOLD,16),GOLD)
    seal(im,"PRECISION MEANS ESTIMATED RELIABILITY",
         "the body is continuously adjudicated")

def vis_relational_map(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.78,INK,170)
    labels=[("TOUCH",CYAN,-210,-100),("REACH",GREEN,220,-95),
            ("THREAT",CRIMSON,-220,105),("SELF-CAUSED",GOLD,220,105),
            ("INSIDE",VIOLET,0,185)]
    for i,(lab,col,ox,oy) in enumerate(labels):
        local=clamp(q*len(labels)-i)
        x,y=cx+ox,cy+oy
        d.ellipse((x-9,y-9,x+9,y+9),fill=(*col,int(220*local)))
        centered(d,(x,y+28),lab,font(FONT_SANS_BOLD,14),col)
        d.line((x,y,cx,cy),fill=(*col,int(100*local)),width=2)
    seal(im,"THE BODY-MODEL IS A DYNAMIC GEOMETRY OF RELEVANCE",
         "where, how far, dangerous, mine, and internal")

def vis_bodywide_loop(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.9,INK,180)
    nodes=[("HEART",CRIMSON,cx,cy-20),("BREATH",CYAN,cx,cy+35),
           ("POSTURE",GREEN,cx,cy+95),("VISION",GOLD,cx,cy-125)]
    for i,(lab,col,x,y) in enumerate(nodes):
        glow_circle(im,x,y,10,col,160,9)
        if q>.4:centered(d,(x+70,y),lab,font(FONT_SANS_BOLD,14),col)
    loop=[(cx,cy-125),(cx+150,cy-30),(cx,cy+110),(cx-150,cy-30),(cx,cy-125)]
    glow_line(im,partial(loop,q),CYAN,5,190,12)
    seal(im,"MIND IS ONE PHASE OF A BODY-WIDE CONTROL LOOP",
         "regulation contributes to perception, emotion, decision, and selfhood")

def vis_bow_arrows(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.36,h*.42; q=ease(u)
    # bow
    d.arc((cx-70,cy-150,cx+70,cy+150),-70,70,fill=(*VIOLET,210),width=6)
    d.line((cx+25,cy-140,cx+25,cy+140),fill=(*VIOLET,160),width=3)
    targets=[("EXIT",CRIMSON,w*.72,h*.25),("FACE",CYAN,w*.78,h*.42),("OPPORTUNITY",GOLD,w*.72,h*.60)]
    chosen=p.get("chosen",0)
    for i,(lab,col,x,y) in enumerate(targets):
        d.ellipse((x-35,y-35,x+35,y+35),outline=(*col,170),width=3)
        centered(d,(x,y+55),lab,font(FONT_SANS_BOLD,14),col)
        if i==chosen:
            glow_line(im,partial([(cx+20,cy),(x,y)],q),col,5,210,13)
    seal(im,"ATTENTION AIMS THE FLOWER-ARROWS",
         "precision weighting decides which difference becomes the world")

def vis_nyasa_learning(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    pts=[(cx,cy-120),(cx-80,cy-55),(cx+80,cy-55),(cx-110,cy+45),(cx+110,cy+45),(cx,cy+115)]
    draw_body(d,cx,cy,.85,INK,170)
    for i,(x,y) in enumerate(pts):
        local=clamp(q*len(pts)-i)
        glow_circle(im,x,y,12,[GOLD,CYAN,VIOLET,GREEN,CRIMSON,GOLD][i],int(150+60*local),10)
        if local>.5:
            centered(d,(x,y+30),["HEAD","SHOULDER","SHOULDER","HAND","HAND","HEART"][i],
                     font(FONT_SANS_BOLD,12),SOFT_INK)
    seal(im,"TOUCH · NAME · VISUALIZE · REPEAT",
         "ritual binds sensation, word, image, emotion, and cosmology")

def vis_skill_maps(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    roles=[("MUSICIAN",CYAN),("DANCER",GOLD),("SURGEON",GREEN)]
    q=ease(u)
    for i,(lab,col) in enumerate(roles):
        x=w*(.24+i*.26); y=h*.40
        draw_body(d,x,y,.48,INK,150)
        if i==0:
            for k in range(5): d.line((x-50,y-80+k*25,x+50,y-80+k*25),fill=(*col,int(180*q)),width=2)
        elif i==1:
            d.arc((x-75,y-100,x+75,y+100),190,350,fill=(*col,int(190*q)),width=4)
        else:
            d.line((x,y-20,x+80,y+20),fill=(*col,int(190*q)),width=5)
        centered(d,(x,h*.68),lab,font(FONT_SANS_BOLD,15),col)
    seal(im,"PRACTICE CHANGES THE REFERENCE FRAME",
         "flesh becomes actionable through learned geometry")

def vis_body_cosmos(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.92,INK,int(210*(1-q*.35)))
    for rr,col in [(70,GOLD),(115,CYAN),(160,VIOLET),(205,GREEN)]:
        d.ellipse((cx-rr*q,cy-rr*q*.60,cx+rr*q,cy+rr*q*.60),
                  outline=(*col,int(160*q)),width=3)
    for tri in sri_chakra_lines(cx,cy,160*q):
        d.line(tri,fill=(*GOLD,int(150*q)),width=2)
    seal(im,"THE BODY BECOMES A LOCAL PRESENTATION OF TOTAL ORDER",
         "skin remains; its metaphysical meaning changes",GOLD)

def vis_virtual_limb(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.45,h*.40; q=ease(u)
    _,end=draw_body(d,cx,cy,.85,INK,180,tool=q)
    # tactile markers spread as perceived arm length changes
    start=(cx+60,cy-20)
    for i in range(6):
        x=lerp(start[0],end[0],i/5)
        d.ellipse((x-6,cy-5,x+6,cy+7),fill=(*CYAN,180))
    d.line((start[0],cy+45,end[0],cy+45),fill=(*GOLD,180),width=4)
    centered(d,((start[0]+end[0])/2,cy+70),"PERCEIVED DISTANCE",font(FONT_SANS_BOLD,14),GOLD)
    seal(im,"CHANGE THE BODY-MODEL · CHANGE THE MEASUREMENT",
         "the ruler is made of the thing being measured")

def vis_significance_space(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.42,h*.40; q=ease(u)
    draw_body(d,cx,cy,.75,INK,170)
    labels=[("NEAR",CYAN,w*.63,h*.28),("FAR",VIOLET,w*.82,h*.22),
            ("REACHABLE",GREEN,w*.66,h*.48),("THREATENING",CRIMSON,w*.80,h*.56),
            ("SACRED",GOLD,w*.68,h*.66)]
    for i,(lab,col,x,y) in enumerate(labels):
        local=clamp(q*len(labels)-i)
        d.ellipse((x-8,y-8,x+8,y+8),fill=(*col,int(220*local)))
        centered(d,(x,y+25),lab,font(FONT_SANS_BOLD,13),col)
        d.line((cx+55,cy,x,y),fill=(*col,int(95*local)),width=2)
    seal(im,"THE BODY HELPS GENERATE THE SPACE OF SIGNIFICANCE",
         "change the body-model and the experienced world changes")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    statements=[("BODY OWNERSHIP ILLUSION","SUPPORTED",GREEN),
                ("DEITIES LITERALLY IN LIMBS","NOT ESTABLISHED",CRIMSON),
                ("BODY MODEL IS REVISABLE","SUPPORTED",CYAN),
                ("ŚRĪCAKRA = NERVOUS SYSTEM","NOT ESTABLISHED",CRIMSON)]
    q=ease(u)
    for i,(a,b,col) in enumerate(statements):
        local=clamp(q*len(statements)-i)
        y=h*(.23+i*.13)
        d.rounded_rectangle((w*.18,y-27,w*.82,y+27),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.38,y),a,font(FONT_SANS_BOLD,15),INK)
        centered(d,(w*.69,y),b,font(FONT_SANS_BOLD,14),col)
    seal(im,"THE PARALLEL IS STRUCTURAL, NOT PROOF",
         "science explains plastic embodiment; ritual asserts sacred identity")

def vis_minimal_practice(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.9,INK,170)
    phases=[("PERIMETER",CYAN,180),("INTERIOR",VIOLET,115),("WORLD",GOLD,245)]
    for i,(lab,col,rr) in enumerate(phases):
        local=clamp(q*len(phases)-i)
        d.ellipse((cx-rr*local,cy-rr*.60*local,cx+rr*local,cy+rr*.60*local),
                  outline=(*col,int(170*local)),width=3)
        if local>.55:centered(d,(cx,cy-rr*.60*local-18),lab,font(FONT_SANS_BOLD,14),col)
    seal(im,"NOTICE HOW THE BODY IS INFERRED",
         "pressure, temperature, vision, memory, expectation, and possible movement")

def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_body(d,cx,cy,.92,INK,int(210*(1-q*.35)))
    for tri in sri_chakra_lines(cx,cy,190*q):
        d.line(tri,fill=(*GOLD,int(190*q)),width=3)
    d.ellipse((cx-220*q,cy-150*q,cx+220*q,cy+150*q),outline=(*CYAN,int(150*q)),width=4)
    if q>.7:centered(d,(cx,h*.70),"ŚRĪCAKRA",font(FONT_SERIF_BOLD,30),GOLD)
    seal(im,"YOUR BODY IS THE DIAGRAM YOUR MIND KEEPS REDRAWING",
         "what universe does the map teach you to inhabit?",GOLD)

VISUALS:dict[str,Callable]={
    "lived":vis_lived_body,
    "mandala":vis_body_to_mandala,
    "correspondence":vis_correspondence,
    "reclassify":vis_same_flesh_new_world,
    "streams":vis_streams,
    "precision":vis_precision_scales,
    "relations":vis_relational_map,
    "loop":vis_bodywide_loop,
    "bow":vis_bow_arrows,
    "nyasa":vis_nyasa_learning,
    "skills":vis_skill_maps,
    "cosmos":vis_body_cosmos,
    "virtual":vis_virtual_limb,
    "space":vis_significance_space,
    "caution":vis_caution,
    "practice":vis_minimal_practice,
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
Scene("Not organs","You do not experience the body as a collection of organs.",6.5,"lived",{}),
Scene("Centre and reach","You experience a centre, a front, a back, a field of reach, and a region called inside.",9.0,"lived",{}),
Scene("World around action","The world is arranged around what this body can sense, survive, and do.",8.0,"lived",{}),
Scene("Body as Śrīcakra","The Bhāvanopaniṣad makes an audacious claim: the body is the Śrīcakra.",8.0,"mandala",{}),
Scene("Not decoration","Not a sacred diagram added to flesh. The lived body itself is interpreted as the ninefold mandala.",9.5,"mandala",{}),

Scene("Correspondence","The central operation of the text is correspondence.",6.0,"correspondence",{}),
Scene("Senses and objects","The senses become horses. Their objects become elephants.",7.5,"correspondence",{}),
Scene("Mind and desire","Mind becomes the sugarcane bow. Desire and repulsion become noose and goad.",8.5,"correspondence",{}),
Scene("Internal sacrifice","Knower, knowing, and known become participants in an internal sacrifice.",8.5,"correspondence",{}),

Scene("Not primitive anatomy","The text is not claiming that blood is literally a ruby or that a shoulder contains an ocean.",8.0,"reclassify",{}),
Scene("Controlled reclassification","It reorganizes how bodily processes are grouped, valued, and experienced.",8.5,"reclassify",{}),
Scene("Same flesh new world","The same physical events enter another model. Materially identical flesh becomes phenomenologically another world.",10.0,"reclassify",{}),

Scene("Predictive body","Predictive processing also denies that bodily experience is a passive readout.",8.0,"streams",{}),
Scene("Noisy streams","The nervous system receives partial signals from muscles, joints, viscera, skin, balance, and the external senses.",10.0,"streams",{}),
Scene("Three channels","Interoception concerns internal states. Proprioception concerns position and movement. Exteroception concerns the environment.",10.0,"streams",{}),
Scene("Negotiation","These streams are weighted, compared, and integrated. The lived body emerges from negotiation.",9.5,"streams",{}),

Scene("Precision","Precision means estimated reliability.",6.0,"precision",{"mode":"internal"}),
Scene("Internal dominance","If internal signals receive excessive weight, ambiguous sensations can dominate perception.",8.5,"precision",{"mode":"internal"}),
Scene("External dominance","If external cues overwhelm the internal stream, a person can become detached from bodily information.",9.0,"precision",{"mode":"external"}),
Scene("Adjudicated body","There is no single body-signal informing a neutral observer. The body is continuously adjudicated.",9.5,"precision",{"mode":"internal"}),

Scene("Yantra relations","A yantra is not a realistic picture. It is an organized field of relations.",8.0,"relations",{}),
Scene("Relational maps","The nervous system does not need a tiny anatomical painting. It needs maps of touch, reach, threat, self-caused movement, and inside.",10.0,"relations",{}),
Scene("Dynamic geometry","The body is experienced through a dynamic geometry of relevance.",7.5,"relations",{}),

Scene("No brain headquarters","The Bhāvanopaniṣad places the Śrīcakra across the whole body rather than behind the eyes.",9.0,"loop",{}),
Scene("Body-wide control","Heartbeat, breathing, visceral signals, posture, and action capacity all contribute to perception and selfhood.",10.0,"loop",{}),
Scene("Mind as phase","Mind is not a spectator receiving messages from below. It is one phase of a body-wide control loop.",9.5,"loop",{}),

Scene("Mind as bow","The text's image of mind as bow and sense-impressions as arrows is technically suggestive.",8.5,"bow",{"chosen":0}),
Scene("Fear aims","Fear aims toward exits and uncertain faces.",7.0,"bow",{"chosen":0}),
Scene("Desire aims","Desire aims toward opportunity.",6.5,"bow",{"chosen":2}),
Scene("Training changes aim","Training changes the aim before it changes the world.",7.5,"bow",{"chosen":1}),
Scene("World struck","The sensory difference amplified by attention becomes the world the organism inhabits.",9.0,"bow",{"chosen":1}),

Scene("Beyond science","Cognitive science asks how an organism constructs a body-model. The Bhāvanopaniṣad asks the practitioner to recognize it as the body of the goddess.",10.0,"mandala",{}),
Scene("Structural parallel","The parallel lies in structure, not proof.",6.5,"caution",{}),

Scene("Nyāsa","Ritual becomes controlled reclassification: touch the body, name a power, visualize a location, repeat.",10.0,"nyasa",{}),
Scene("Semantic depth","A shoulder is no longer only shoulder. It can become direction, deity, element, or enclosure.",8.5,"nyasa",{}),
Scene("Skilled maps","A musician feels intervals as hand-shapes. A dancer feels space through possible movement. A surgeon feels anticipated resistance.",10.0,"skills",{}),
Scene("Reference frame","Practice changes the reference frame through which flesh becomes actionable.",8.0,"skills",{}),

Scene("Body and cosmos","Tantric bhāvanā does not merely make the body efficient. It makes body and cosmos less absolute as separate categories.",10.0,"cosmos",{}),
Scene("Sacred geography","Oceans surround the organism. Deities inhabit functions. Time enters through breath.",9.0,"cosmos",{}),
Scene("Local total order","The body becomes the local presentation of a total order.",7.5,"cosmos",{}),
Scene("Skin remains","The skin remains. Its metaphysical meaning changes.",6.5,"cosmos",{}),

Scene("Virtual limb","Virtual-reality research makes body-schema malleability visible.",7.5,"virtual",{}),
Scene("Elongated forearm","When a virtual forearm appears longer, perceived tactile distance on the real forearm can change.",9.5,"virtual",{}),
Scene("Ruler and measured","The internal reference frame has changed. The ruler is made of the thing being measured.",9.0,"virtual",{}),

Scene("Space of significance","The body is not merely an object in pre-given space. It helps generate the space of significance.",9.5,"space",{}),
Scene("Near and sacred","Near, far, reachable, internal, threatening, and sacred arise through a body capable of action and interpretation.",10.0,"space",{}),
Scene("Religious technology","Nyāsa and bhāvanā turn body-schema plasticity into a religious technology.",8.5,"space",{}),

Scene("Do not overclaim","A body-ownership illusion does not prove that deities literally inhabit limbs.",8.0,"caution",{}),
Scene("No neural Śrīcakra proof","Predictive processing does not prove that the Śrīcakra is the hidden geometry of the nervous system.",9.0,"caution",{}),
Scene("What science removes","Science removes one obstacle: the ordinary body is already constructed and revisable.",8.5,"caution",{}),

Scene("Feel perimeter","Feel the body's perimeter. Notice that it is not given as one continuous signal.",8.0,"practice",{}),
Scene("Sparse interior","Most organs are not continuously felt. The inside is built from sparse information.",8.5,"practice",{}),
Scene("World by movement","The world around the body is organized by possible movement.",7.5,"practice",{}),
Scene("Reference frame","The body is not one object among objects. It is the reference frame through which objects become available.",9.5,"practice",{}),

Scene("Radicalized body","The Bhāvanopaniṣad radicalizes this ordinary construction.",7.5,"final",{}),
Scene("Island and deity","The body is the island. The senses are its animals. Mind is its weapon. Breath is its time. Awareness is its deity.",10.0,"final",{}),
Scene("Embodiment as gate","The practitioner does not flee embodiment. Every function becomes a gate into the whole.",9.0,"final",{}),
Scene("Closing","Your body is the diagram your mind keeps redrawing. The question is what kind of universe the map teaches you to inhabit.",10.0,"final",{}),
]

def render_frame(scene,fi,count,w,h,seed):
    u=fi/max(1,count-1); t=u*scene.duration
    im=field(w,h,seed); VISUALS[scene.visual](im,u,t,scene.params); border(im)
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

def render_scene(i,s,fps,w,h,preview):
    fd=FRAMES/f"scene_{i:03d}"; fd.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    count=max(2,round(s.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(count*.33),int(count*.72),count-1]):
            render_frame(s,fi,count,w,h,i*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(count):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(s,fi,count,w,h,i*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(i,fps)

def concatenate(paths):
    txt=OUTPUT/"concat.txt"
    txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    out=OUTPUT/"body_diagram.mp4"
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
    p.write_text(json.dumps({"title":"your body is the diagram your mind keeps redrawing",
                             "scene_count":len(SCENES),"runtime_seconds":round(cur,3),
                             "shot_duration_range":[5,10],
                             "continuity_object":"cyan inferred body perimeter",
                             "scenes":rec},indent=2,ensure_ascii=False),encoding="utf-8")
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
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rendered.append(r)
    if not a.no_contact_sheet: print(f"Contact sheet: {contact_sheet(a.width,a.height)}")
    if not a.preview: print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
