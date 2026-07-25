#!/usr/bin/env python3
"""
THE WORLD ARRIVES BEFORE YOU NAME IT
A complete Platinum-house procedural visual essay.

Source:
expansion-essays/01_the_world_arrives_before_you_name_it.md

VISUAL THESIS
-------------
Appearance precedes recognition. Color opens, contour separates, depth gathers,
and only then does the word close around the event. Liberation is not destroying
language but seeing the luminous act of manifestation before and through the name.

HOUSE RULES
-----------
• Every scene lasts 5–10 seconds.
• Every scene performs a visible transformation.
• Clean ivory scientific/gallery field.
• Sparse labels only.
• No slideshow layouts.
• Mature frame near u=0.72.
• Continuity object: a gold contour that appears before the label and survives beneath it.

PALETTE ROLES
-------------
IVORY    pre-categorical field
GOLD     manifestation / first arrival
CYAN     reflexive awareness / vimarśa
INK      stabilized object / name
VIOLET   latent possibility
CRIMSON  rigid naming / conceptual arrest
GREEN    recognition without confinement

OUTPUT
------
output_world_arrives/
  frames/
  scenes/
  world_arrives_before_name.mp4
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
OUTPUT=ROOT/"output_world_arrives"
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
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3

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
    halo=np.exp(-(((xx-w*.50)/(w*.37))**2+((yy-h*.39)/(h*.31))**2)*2.0)
    arr[...,1]+=halo*3.4; arr[...,2]+=halo*5.2
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")

def centered(d,xy,text,f,fill=INK): d.text(xy,text,font=f,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered(d,(w/2,h*.875),title,font(FONT_SERIF_BOLD,max(22,int(h*.04))),color)
    if subtitle: centered(d,(w/2,h*.923),subtitle,font(FONT_SANS,max(13,int(h*.019))),SOFT_INK)
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

def tree_points(cx,cy,scale=1.0):
    trunk=[(cx,cy+85*scale),(cx,cy-15*scale)]
    branches=[
        [(cx,cy+15*scale),(cx-60*scale,cy-35*scale)],
        [(cx,cy+5*scale),(cx+70*scale,cy-45*scale)],
        [(cx,cy-5*scale),(cx-20*scale,cy-85*scale)],
        [(cx-25*scale,cy-30*scale),(cx-80*scale,cy-75*scale)],
        [(cx+28*scale,cy-28*scale),(cx+90*scale,cy-78*scale)]
    ]
    return trunk,branches

def draw_tree(d,cx,cy,scale,color,alpha=220):
    trunk,branches=tree_points(cx,cy,scale)
    d.line((*trunk[0],*trunk[1]),fill=(*color,alpha),width=max(3,int(8*scale)))
    for a,b in branches:
        d.line((*a,*b),fill=(*color,alpha),width=max(2,int(5*scale)))
    for ox,oy,r in [(-70,-75,30),(0,-95,34),(75,-80,30),(-25,-45,35),(40,-50,34)]:
        d.ellipse((cx+(ox-r)*scale,cy+(oy-r)*scale,cx+(ox+r)*scale,cy+(oy+r)*scale),
                  outline=(*color,alpha),width=max(2,int(3*scale)))

def draw_cup(d,cx,cy,scale,color,alpha=220):
    d.rounded_rectangle((cx-36*scale,cy-42*scale,cx+28*scale,cy+42*scale),
                        radius=max(6,int(8*scale)),outline=(*color,alpha),width=max(2,int(4*scale)))
    d.arc((cx+10*scale,cy-25*scale,cx+52*scale,cy+25*scale),270,90,
          fill=(*color,alpha),width=max(2,int(4*scale)))

def noisy_cloud(w,h,n,seed):
    rng=random.Random(seed)
    return [(rng.uniform(w*.12,w*.88),rng.uniform(h*.18,h*.68),
             [GOLD,CYAN,VIOLET,SOFT_INK,GREEN][i%5]) for i in range(n)]

def vis_pre_name(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.41
    q=ease(u)
    pts=noisy_cloud(w,h,150,31)
    for x,y,col in pts:
        xx=lerp(x,cx,q*.42); yy=lerp(y,cy,q*.42)
        r=2
        d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(*col,int(70+90*q)))
    # contour forms before label
    if q>.25:
        alpha=int(220*(q-.25)/.75)
        draw_tree(d,cx,cy,1.25,GOLD,alpha)
    if q>.78:
        centered(d,(cx,h*.70),"TREE",font(FONT_SERIF_BOLD,32),(*INK,int(230*(q-.78)/.22)))
    seal(im,"THE WORLD ARRIVES BEFORE THE WORD",
         "color, contour, and distance gather before naming")

def vis_focus_plane(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    planes=[(w*.28,.65,VIOLET),(w*.50,1.0,GOLD),(w*.72,.65,CYAN)]
    for x,scale,col in planes:
        blur_alpha=int(90+140*(q if x==w*.50 else 1-q*.72))
        draw_tree(d,x,h*.42,scale,col,blur_alpha)
    # focus rails
    d.line((w*.15,h*.18,w*.85,h*.18),fill=(*SILVER,130),width=3)
    knob=lerp(w*.25,w*.50,q)
    glow_circle(im,knob,h*.18,11,CYAN,170,9)
    seal(im,"FOCUS GIVES THE IMAGE AN ARGUMENT",
         "look here; this matters; this is the world")

def vis_prakasa_vimarsa(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    light=smoothstep(.05,.48,u)
    reflect=smoothstep(.38,.88,u)
    for rr in range(35,250,32):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                  outline=(*GOLD,int(90*light*(1-rr/280))),width=3)
    pts=[]
    for i in range(160):
        q=i/159; a=q*math.tau*1.7+t*.3; r=w*.22*(.25+.75*q)
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.62))
    glow_line(im,partial(pts,reflect),CYAN,5,int(120+100*reflect),13)
    centered(d,(w*.28,h*.70),"PRAKĀŚA",font(FONT_SERIF_BOLD,28),GOLD)
    centered(d,(w*.72,h*.70),"VIMARŚA",font(FONT_SERIF_BOLD,28),CYAN)
    seal(im,"THE SHINING KNOWS ITSELF",
         "illumination and reflexive awareness form living consciousness")

def vis_stage_not_actor(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    # stage
    d.rounded_rectangle((w*.18,h*.20,w*.82,h*.64),radius=20,
                        fill=(*PALE_SILVER,120),outline=(*CYAN,170),width=4)
    actors=[(w*.30,GREEN),(w*.50,GOLD),(w*.70,VIOLET)]
    for i,(x,col) in enumerate(actors):
        local=clamp(q*3-i)
        d.ellipse((x-24,h*.36-24,x+24,h*.36+24),outline=(*col,int(210*local)),width=4)
        d.line((x,h*.36+24,x,h*.52),fill=(*col,int(210*local)),width=5)
    if q>.65:
        centered(d,(w*.50,h*.16),"THE STAGE IS NOT ANOTHER ACTOR",
                 font(FONT_SANS_BOLD,18),CYAN)
    seal(im,"CONSCIOUSNESS IS THE CONDITION OF APPEARANCE",
         "body, thought, object, distance, and identity all arise within it")

def vis_knower_known(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    left=(lerp(cx,cx-190,q),cy); right=(lerp(cx,cx+190,q),cy)
    glow_circle(im,*left,14,CYAN,170,10)
    glow_circle(im,*right,14,GOLD,170,10)
    d.line((*left,*right),fill=(*INK,int(180*q)),width=4)
    if q>.45:
        centered(d,(left[0],cy-40),"SEER",font(FONT_SANS_BOLD,17),CYAN)
        centered(d,(right[0],cy-40),"TREE",font(FONT_SANS_BOLD,17),GOLD)
    seal(im,"USEFUL DIVISION HARDENS INTO METAPHYSICS",
         "the tool becomes a cage when separation is mistaken for final reality")

def vis_abhasa_flower(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    layers=[("RED",CRIMSON,-180,-80),("SHAPE",GOLD,180,-80),
            ("FRAGRANCE",VIOLET,-180,95),("DISTANCE",CYAN,180,95)]
    q=ease(u)
    for i,(lab,col,ox,oy) in enumerate(layers):
        local=clamp(q*len(layers)-i)
        x=lerp(cx+ox,cx,local*.75); y=lerp(cy+oy,cy,local*.75)
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,16),(*col,int(210*local)))
        d.line((x,y,cx,cy),fill=(*col,int(100*local)),width=2)
    if q>.5:
        for a in range(0,360,60):
            px=cx+math.cos(math.radians(a))*35; py=cy+math.sin(math.radians(a))*35
            d.ellipse((px-18,py-18,px+18,py+18),outline=(*CRIMSON,int(220*q)),width=3)
        glow_circle(im,cx,cy,12,GOLD,170,10)
    seal(im,"ĀBHĀSA · AN ORGANIZED EVENT OF DISCLOSURE",
         "the flower is not dead matter later photographed by mind")

def vis_mirror_self_image(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    d.ellipse((cx-190,cy-220,cx+190,cy+220),fill=(*PALE_SILVER,100),
              outline=(*CYAN,180),width=5)
    draw_tree(d,cx,cy,1.15,GOLD,int(220*q))
    # no external original; reflection blooms from mirror itself
    if q>.3:
        for rr in range(40,210,30):
            d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),
                      outline=(*GOLD,int(80*q*(1-rr/240))),width=3)
    seal(im,"THE MIRROR DISPLAYS ITS OWN CAPACITY TO BECOME IMAGE",
         "world, seer, and knowing are one light in three positions")

def vis_thought_emergence(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # latent cloud
    for rr in range(40,220,30):
        d.ellipse((cx-rr,cy-rr*.55,cx+rr,cy+rr*.55),
                  outline=(*VIOLET,int(80*(1-q*.45)*(1-rr/250))),width=3)
    # thought crosses threshold
    line=[(w*.15,cy),(w*.42,cy-50),(cx,cy),(w*.72,cy+25)]
    glow_line(im,partial(line,q),GOLD,5,210,13)
    if q>.55:
        centered(d,(w*.72,cy+25),"I AM THINKING",font(FONT_SERIF_BOLD,26),
                 (*INK,int(220*(q-.55)/.45)))
    seal(im,"THE THOUGHT ARRIVES BEFORE THE OWNER CLAIMS IT",
         "the cloud announces that it created the sky")

def vis_threshold_gap(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40)
    a=smoothstep(.05,.30,u); gap=smoothstep(.28,.68,u)*(1-smoothstep(.68,.95,u)); b=smoothstep(.66,.96,u)
    draw_cup(d,*left,1.25,GOLD,int(230*(1-a)))
    draw_tree(d,*right,1.0,GREEN,int(230*b))
    if gap>0:
        for rr in range(30,220,30):
            d.ellipse((w*.50-rr,h*.40-rr*.55,w*.50+rr,h*.40+rr*.55),
                      outline=(*CYAN,int(80*gap*(1-rr/250))),width=3)
    glow_line(im,partial([left,(w*.50,h*.40),right],u),CYAN,4,180,11)
    seal(im,"THE OBJECT DISAPPEARS · ILLUMINATION REMAINS",
         "thresholds reveal the machinery of contraction")

def vis_sound_before_source(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    baseline=h*.40
    pts=[]
    for i in range(220):
        x=w*.10+i*w*.80/219
        y=baseline+math.sin(i*.22+t*4)*42*(.55+.45*math.sin(i*.07))
        pts.append((x,y))
    glow_line(im,partial(pts,q),CYAN,4,200,12)
    if q>.55:
        words=["CAR","ANNOYING","OUTSIDE"]
        for i,lab in enumerate(words):
            centered(d,(w*(.30+i*.20),h*.66),lab,font(FONT_SANS_BOLD,17),
                     (*INK,int(210*(q-.55)/.45)))
    seal(im,"SOUND ARRIVES BEFORE ITS ARCHITECTURE",
         "texture first; source, judgment, and location afterward")

def vis_cup_excess(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    details=[("COLOR",CRIMSON,-190,-90),("CURVATURE",GOLD,190,-90),
             ("WEIGHT",CYAN,-190,90),("MEMORY",VIOLET,190,90),("TOUCH",GREEN,0,160)]
    q=ease(u)
    for i,(lab,col,ox,oy) in enumerate(details):
        local=clamp(q*len(details)-i)
        x=lerp(cx+ox,cx,local*.80); y=lerp(cy+oy,cy,local*.80)
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,15),(*col,int(210*local)))
    if q>.5:
        draw_cup(d,cx,cy,1.45,INK,int(230*q))
        centered(d,(cx,h*.70),"CUP",font(FONT_SERIF_BOLD,32),(*CRIMSON,int(220*q)))
    seal(im,"THE WORD COMPRESSES AN EXCESS",
         "language lets the world be handled, then hides what exceeded the handle")

def vis_pratyabhijna(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # tree, seer, seeing emerge together
    positions=[(cx-180,cy,CYAN),(cx+180,cy,GOLD),(cx,cy+145,GREEN)]
    labels=["SEER","TREE","SEEING"]
    for i,(x,y,col) in enumerate(positions):
        local=clamp(q*3-i)
        glow_circle(im,x,y,14,col,170,11)
        if local>.45: centered(d,(x,y-34),labels[i],font(FONT_SANS_BOLD,16),col)
    if q>.55:
        for a,b in [(0,1),(1,2),(2,0)]:
            d.line((*positions[a][:2],*positions[b][:2]),fill=(*GOLD,int(150*q)),width=3)
    centered(d,(cx,h*.18),"PRATYABHIJÑĀ",font(FONT_SERIF_BOLD,28),GOLD)
    seal(im,"RECOGNIZE THE POWER PRESENT BEFORE EVERY CONCEPT",
         "the sacred is the world's act of becoming visible")

def vis_udyama(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    flash=smoothstep(.08,.34,u); form=smoothstep(.38,.90,u)
    for i in range(100):
        a=i*math.tau/100; r=lerp(5,250,flash)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.62
        d.line((cx,cy,x,y),fill=(*GOLD,int(110*flash)),width=2)
    if form>.2: draw_tree(d,cx,cy,1.05,GREEN,int(220*form))
    centered(d,(cx,h*.70),"UDYAMO BHAIRAVAḤ",font(FONT_SERIF_BOLD,28),GOLD)
    seal(im,"THE UPSURGE BEFORE FORM SETTLES",
         "consciousness caught in the act of exceeding its own limitation")

def vis_creation_cycle(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    labels=[("DISSOLVE",CRIMSON,-170,0),("FIELD",VIOLET,-80,-120),
            ("EMERGE",GOLD,90,-110),("CLAIM",CYAN,175,15),("FORM",GREEN,0,145)]
    q=ease(u)
    for i,(lab,col,ox,oy) in enumerate(labels):
        local=clamp(q*len(labels)-i)
        x,y=cx+ox,cy+oy
        d.ellipse((x-9,y-9,x+9,y+9),fill=(*col,int(220*local)))
        if local>.45: centered(d,(x,y+26),lab,font(FONT_SANS_BOLD,14),col)
        if i>0:
            px,py=cx+labels[i-1][2],cy+labels[i-1][3]
            d.line((px,py,x,y),fill=(*col,int(150*local)),width=2)
    seal(im,"THE RESTLESS MIND REPEATS CREATION AND DISSOLUTION",
         "the continuity of light was never broken")

def vis_wave_field(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    for j,col in enumerate([GOLD,CYAN,VIOLET]):
        pts=[]
        for i in range(220):
            x=w*.08+i*w*.84/219
            y=h*.40+math.sin(i*.10+t*(1+j*.3)+j)*45*(1-j*.18)
            pts.append((x,y))
        glow_line(im,partial(pts,q),col,4,170,10)
    if q>.65:
        centered(d,(w*.50,h*.67),"ONE FIELD · MANY WAVES",font(FONT_SERIF_BOLD,26),GOLD)
    seal(im,"LESS SOLID DOES NOT MEAN LESS REAL",
         "seer and seen are temporary waves in luminous recognition")

def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40
    q=ease(u)
    # manifestation first
    for rr in range(35,250,32):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(80*q*(1-rr/280))),width=3)
    draw_tree(d,cx,cy,1.2,GOLD,int(220*q))
    # name closes but remains translucent
    name=smoothstep(.58,.92,u)
    centered(d,(cx,h*.69),"TREE",font(FONT_SERIF_BOLD,34),(*INK,int(180*name)))
    if name>.65:
        centered(d,(cx,h*.18),"CAITANYAM ĀTMĀ",font(FONT_SERIF_BOLD,26),GOLD)
    seal(im,"THE WORLD DOES NOT WAIT BEHIND YOUR WORDS",
         "it arrives first—and what arrives as world is the same awareness arriving as you",GOLD)

VISUALS:dict[str,Callable]={
    "pre_name":vis_pre_name,
    "focus":vis_focus_plane,
    "prakasa":vis_prakasa_vimarsa,
    "stage":vis_stage_not_actor,
    "division":vis_knower_known,
    "abhasa":vis_abhasa_flower,
    "mirror":vis_mirror_self_image,
    "thought":vis_thought_emergence,
    "gap":vis_threshold_gap,
    "sound":vis_sound_before_source,
    "cup":vis_cup_excess,
    "recognition":vis_pratyabhijna,
    "udyama":vis_udyama,
    "cycle":vis_creation_cycle,
    "wave":vis_wave_field,
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
Scene("Before tree","Before you call it a tree, something has already happened.",7.0,"pre_name",{}),
Scene("Color and shape","Color has opened. Shape has separated from the sky. Distance has appeared.",8.0,"pre_name",{}),
Scene("Word arrives","Only afterward does the word arrive: tree.",6.0,"pre_name",{}),
Scene("World already world","By then the miracle is over. The world has already become a world.",7.5,"pre_name",{}),

Scene("Life after naming","Most of your life happens after naming.",6.0,"focus",{}),
Scene("Instant recognition","You enter a room and immediately know table, window, person, threat, opportunity, mine, not mine.",9.0,"focus",{}),
Scene("Earlier instant","Kashmir Śaivism asks you to become interested in the earlier instant: not the tree, but the coming-forth of the tree.",10.0,"pre_name",{}),

Scene("Prakāśa","Prakāśa is the luminous capacity through which anything becomes available to be known.",8.0,"prakasa",{}),
Scene("Vimarśa","Vimarśa is light folded back upon itself: the shining knowing that it shines.",8.5,"prakasa",{}),
Scene("Living awareness","Illumination and self-recognition form living consciousness.",7.0,"prakasa",{}),

Scene("Caitanyam ātmā","Caitanyam ātmā. Consciousness is the Self.",6.5,"stage",{}),
Scene("Grammar reversed","Consciousness does not belong to you. You belong to consciousness.",8.0,"stage",{}),
Scene("Stage","The Self is not one illuminated object among others. A stage is not one more actor, yet every actor depends upon it.",10.0,"stage",{}),

Scene("Jñānaṃ bandhaḥ","Jñānaṃ bandhaḥ. Limited knowing is bondage.",6.5,"division",{}),
Scene("Contraction","To know one object as this is to exclude everything it is not.",7.5,"division",{}),
Scene("Seer and seen","The tree becomes a thing over there. You become the one in here.",7.5,"division",{}),
Scene("Tool becomes cage","The division is useful, but usefulness hardens into metaphysics. The tool becomes a cage.",9.0,"division",{}),

Scene("Camera focus","Think of a camera focusing. One plane sharpens, foreground gains authority, and everything behind it recedes.",9.0,"focus",{}),
Scene("Image argument","Nothing outside the chosen plane has ceased to exist, but the image now has an argument: look here.",8.5,"focus",{}),
Scene("Result hides process","You experience there is a tree, not consciousness selecting tree. The completed result conceals the creative movement.",9.5,"focus",{}),

Scene("Ābhāsa","The world is a display of ābhāsas: appearances, manifestations, things shining forth.",8.0,"abhasa",{}),
Scene("Flower disclosure","Red, shape, fragrance, and distance are real as appearing within consciousness.",9.0,"abhasa",{}),
Scene("Organized disclosure","The flower is not dead matter later photographed by mind. It is an organized event of disclosure.",9.5,"abhasa",{}),

Scene("Mirror","A reflection depends on a mirror, but dependence does not equal nothingness.",8.0,"mirror",{}),
Scene("No external original","The mirror of consciousness does not require an original object outside itself. Its freedom produces the reflection.",10.0,"mirror",{}),
Scene("One light three positions","Tree, seer, and knowledge are one light appearing in three positions.",8.5,"mirror",{}),

Scene("Not ego invention","Your personal mind does not invent the tree.",7.0,"thought",{}),
Scene("Ego sentence","The ego is not the author. It is one of the sentences.",7.5,"thought",{}),
Scene("Thought arrives","Consider the next thought. Do not choose it. Wait. Something appears.",8.5,"thought",{}),
Scene("Ownership follows","Then vimarśa claims it: I am thinking. Ownership arrives after emergence.",9.0,"thought",{}),

Scene("Thresholds","The Śaiva masters became fascinated with the border between appearances.",8.0,"gap",{}),
Scene("Sound ends","A sound ends. The next has not yet been identified.",7.0,"gap",{}),
Scene("Breath turns","A breath turns. One object leaves attention. Another has not taken its place.",8.0,"gap",{}),
Scene("Illumination remains","The object disappears. Illumination remains.",6.5,"gap",{}),

Scene("Listen","Listen to the nearest continuous sound.",6.0,"sound",{}),
Scene("Texture first","Do not name the source. Let sound be texture before it becomes information.",8.5,"sound",{}),
Scene("Architecture closes","The mind reaches for causes and judgments: car, annoying, outside. Each statement builds architecture.",9.5,"sound",{}),
Scene("Only sound","Notice the instant before the architecture closes. Sound. Only sound.",7.0,"sound",{}),

Scene("Earlier is richer","The earlier instant is not blank. It contains more than the finished object, not less.",8.0,"cup",{}),
Scene("Cup excess","Before naming, a cup is color, curvature, weight, memory, touch, and reflected light.",9.5,"cup",{}),
Scene("Magnificent contraction","The word cup compresses this excess into a manageable tool. Language is a magnificent contraction.",9.0,"cup",{}),
Scene("Fresh perception","Freshness means cognition has not completely replaced manifestation with recognition.",8.0,"cup",{}),

Scene("Pratyabhijñā","Liberation is pratyabhijñā: recognition.",6.0,"recognition",{}),
Scene("Not new concept","Recognition does not add a new concept. It recognizes the power present before every concept.",9.0,"recognition",{}),
Scene("Tree seer seeing","Tree, seer, and seeing arise together through divine freedom.",8.0,"recognition",{}),
Scene("Sacred visibility","The sacred is not behind the world. It is the world's act of becoming visible.",8.5,"recognition",{}),

Scene("Udyamo bhairavaḥ","Udyamo bhairavaḥ. The upsurge is Bhairava.",6.5,"udyama",{}),
Scene("Before settling","Udyama is the surge before consciousness settles into a contracted form.",8.0,"udyama",{}),
Scene("Before word and movement","Before the word, pressure to speak. Before movement, the gathering of will.",9.0,"udyama",{}),
Scene("Bright opening","Before thought, the bright opening in which thought becomes possible.",8.0,"udyama",{}),

Scene("Distraction re-read","Attention jumps from object to object. Movement itself is not the enemy.",8.0,"cycle",{}),
Scene("Cosmic sequence","Each shift repeats the sequence: appearance dissolves, field remains, a new appearance emerges, self-recognition contracts.",10.0,"cycle",{}),
Scene("Restless creation","The restless mind performs creation and dissolution hundreds of times each minute.",8.5,"cycle",{}),
Scene("Same light","Meditation learns to see the same light through thought, gap, and next thought.",9.0,"cycle",{}),

Scene("Less solid","Then the world becomes less solid without becoming less real.",7.0,"wave",{}),
Scene("Edges soften","The body remains heavy, time continues, pain still hurts, yet the edges soften.",8.0,"wave",{}),
Scene("One field many waves","Knower and known are waves produced by one field of luminous recognition.",8.5,"wave",{}),

Scene("Return to tree","Before you call it a tree, the world is still visibly arriving.",7.5,"final",{}),
Scene("Name closes","Then the name closes around it: tree, useful, stable, known.",8.0,"final",{}),
Scene("First event remains","But beneath the word, color still opens, shape still gathers, and light still offers itself as form.",9.5,"final",{}),
Scene("Closing","The world does not wait behind your words. It arrives first. And what arrives as world is the same awareness now arriving as you.",10.0,"final",{}),
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
    out=OUTPUT/"world_arrives_before_name.mp4"
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
    p.write_text(json.dumps({"title":"the world arrives before you name it",
                             "scene_count":len(SCENES),"runtime_seconds":round(cur,3),
                             "shot_duration_range":[5,10],
                             "continuity_object":"gold pre-linguistic contour",
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
