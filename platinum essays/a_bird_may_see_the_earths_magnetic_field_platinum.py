#!/usr/bin/env python3
"""
A BIRD MAY SEE THE EARTH'S MAGNETIC FIELD
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/02_a_bird_may_see_the_earths_magnetic_field.md

DESIGN CONTRACT
---------------
• Every shot lasts 5–10 seconds.
• Every shot visibly performs the narrated operation.
• White scientific field; night scenes use deep indigo only where necessary.
• No static slide layouts and no decorative loops.
• Blue-green = geomagnetic field / directional inclination
• Gold = photon excitation / radical-pair correlation
• Cyan = cryptochrome / retinal architecture
• Crimson = decoherence, disruption, or unsupported metaphysical leap
• Violet = spin-state evolution / molecular coupling
• Green = amplified biological direction / successful orientation
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: the same magnetic field lattice persists from molecule to migration.
• Visual grammar moves continuously across scales:
  planet → retina → protein → radical pair → neural signal → wing trajectory.
• Quantum imagery must remain precise and non-magical.

OUTPUT
------
output_bird_magnetic_field/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  a_bird_may_see_the_earths_magnetic_field.mp4
  narration_timeline.json
  contact_sheet.jpg

REQUIREMENTS
------------
pip install pillow numpy
ffmpeg must be on PATH.

USAGE
-----
python a_bird_may_see_the_earths_magnetic_field_platinum.py
python a_bird_may_see_the_earths_magnetic_field_platinum.py --preview
python a_bird_may_see_the_earths_magnetic_field_platinum.py --scene 8
python a_bird_may_see_the_earths_magnetic_field_platinum.py --fps 12 --width 1920 --height 1080
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"output_bird_magnetic_field"
FRAMES=OUTPUT/"frames"
SCENES_DIR=OUTPUT/"scenes"

DEFAULT_WIDTH=1280
DEFAULT_HEIGHT=720
DEFAULT_FPS=10

WHITE=(248,247,243); PAPER=(242,239,232); INK=(28,31,35); SOFT_INK=(84,88,94)
SILVER=(177,184,190); PALE_SILVER=(224,227,229)
FIELD=(48,132,145); PALE_FIELD=(184,220,221)
CYAN=(55,153,181); PALE_CYAN=(192,226,233)
GOLD=(195,154,68); PALE_GOLD=(235,218,175)
VIOLET=(104,79,146); PALE_VIOLET=(216,205,232)
CRIMSON=(158,52,66); PALE_CRIMSON=(230,192,198)
GREEN=(70,139,98); PALE_GREEN=(194,225,206)
LAPIS=(48,72,124); NIGHT=(17,23,39); VOID=(22,25,31)

FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0,hi=1): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*t
def mix(a,b,t):
    t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b:return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): return .5-.5*math.cos(math.pi*clamp(t))
def pulse(t,hz=1,phase=0): return .5+.5*math.sin(math.tau*(hz*t+phase))
def load_font(path,size):
    for p in (path,FONT_SERIF,FONT_SANS):
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()
def rgba_layer(size): return Image.new("RGBA",size,(0,0,0,0))
def background(w,h,seed,dark=False):
    rng=np.random.default_rng(seed); base=NIGHT if dark else WHITE
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=base
    arr+=rng.normal(0,1.0 if not dark else 1.7,(h,w,1))
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")
def centered_text(d,xy,text,font,fill=INK): d.text(xy,text,font=font,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK,dark=False):
    w,h=im.size; d=ImageDraw.Draw(im)
    base=WHITE if dark else color
    centered_text(d,(w/2,h*.875),title,load_font(FONT_SERIF_BOLD,max(22,int(h*.042))),base)
    if subtitle:centered_text(d,(w/2,h*.925),subtitle,load_font(FONT_SANS,max(13,int(h*.020))),PALE_SILVER if dark else SOFT_INK)
def border(im,dark=False):
    w,h=im.size
    ImageDraw.Draw(im).rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*(WHITE if dark else INK),42),width=2)
def glow_line(im,pts,color,width=4,glow=14,alpha=225):
    if len(pts)<2:return
    layer=rgba_layer(im.size); d=ImageDraw.Draw(layer)
    d.line(pts,fill=(*color,alpha),width=width,joint="curve")
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(glow))); im.alpha_composite(layer)
def glow_circle(im,cx,cy,r,color,alpha=180,blur=18):
    layer=rgba_layer(im.size); d=ImageDraw.Draw(layer)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*color,alpha))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    core=rgba_layer(im.size)
    ImageDraw.Draw(core).ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=(*mix(color,WHITE,.28),min(255,alpha+40)))
    im.alpha_composite(core)
def partial_polyline(points,progress):
    progress=clamp(progress)
    if len(points)<2:return points
    lengths=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]
    total=sum(lengths); target=total*progress; out=[points[0]]; walked=0
    for i,L in enumerate(lengths):
        if walked+L<=target: out.append(points[i+1]); walked+=L
        else:
            q=0 if L==0 else (target-walked)/L
            ax,ay=points[i]; bx,by=points[i+1]
            out.append((lerp(ax,bx,q),lerp(ay,by,q))); break
    return out
def arrow(d,start,end,color=INK,width=3,head=12):
    d.line((*start,*end),fill=color,width=width)
    a=math.atan2(end[1]-start[1],end[0]-start[0])
    for delta in (2.55,-2.55):
        p=(end[0]+math.cos(a+delta)*head,end[1]+math.sin(a+delta)*head)
        d.line((*end,*p),fill=color,width=width)
def organic_blob(d,cx,cy,rx,ry,color,phase=0,points=100,outline=None):
    pts=[]
    for i in range(points):
        a=math.tau*i/points
        wob=1+.06*math.sin(a*3+phase)+.035*math.sin(a*7-phase*.5)
        pts.append((cx+math.cos(a)*rx*wob,cy+math.sin(a)*ry*wob))
    d.polygon(pts,fill=color,outline=outline); return pts
def field_lines(w,h,phase=0,tilt=.18,count=13):
    lines=[]
    for j in range(count):
        y0=h*(.14+j*.055)
        pts=[]
        for i in range(180):
            q=i/179; x=lerp(w*.05,w*.95,q)
            y=y0+math.sin(q*math.pi)*h*.10 + (q-.5)*h*tilt + math.sin(q*math.tau*2+phase+j*.2)*4
            pts.append((x,y))
        lines.append(pts)
    return lines
def draw_field(im,phase=0,tilt=.18,alpha=70,dark=False):
    col=PALE_FIELD if dark else FIELD
    for pts in field_lines(*im.size,phase,tilt):
        glow_line(im,pts,col,2,6,alpha)
def bird_shape(d,cx,cy,scale,color=INK,alpha=220,wing=.7):
    body=[(cx-55*scale,cy),(cx+25*scale,cy-5*scale),(cx+52*scale,cy+4*scale),(cx+20*scale,cy+12*scale)]
    d.polygon(body,fill=(*color,alpha))
    d.polygon([(cx-5*scale,cy),(cx-70*scale,cy-70*scale*wing),(cx-28*scale,cy+5*scale)],fill=(*color,alpha))
    d.polygon([(cx-2*scale,cy+3*scale),(cx-65*scale,cy+60*scale*wing),(cx-25*scale,cy+8*scale)],fill=(*color,alpha))
    d.polygon([(cx+50*scale,cy+4*scale),(cx+68*scale,cy),(cx+50*scale,cy-4*scale)],fill=(*GOLD,alpha))
def radical_pair(d,cx,cy,separation=110,angle=0,alpha=220):
    dx=math.cos(angle)*separation/2; dy=math.sin(angle)*separation/2
    a=(cx-dx,cy-dy); b=(cx+dx,cy+dy)
    d.ellipse((a[0]-18,a[1]-18,a[0]+18,a[1]+18),fill=(*PALE_GOLD,230),outline=(*GOLD,alpha),width=3)
    d.ellipse((b[0]-18,b[1]-18,b[0]+18,b[1]+18),fill=(*PALE_VIOLET,230),outline=(*VIOLET,alpha),width=3)
    d.line((*a,*b),fill=(*FIELD,150),width=3)
    arrow(d,(a[0],a[1]-4),(a[0],a[1]-26),GOLD,2,7)
    arrow(d,(b[0],b[1]+4),(b[0],b[1]+26),VIOLET,2,7)

@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict

def visual_night_migration(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    draw_field(im,t*.18,.24,65,True)
    # stars obscured by cloud
    for i in range(30):
        x=(i*83)%w; y=50+(i*47)%180
        d.ellipse((x-1,y-1,x+1,y+1),fill=(*WHITE,80))
    cloud=smoothstep(.15,.65,u)
    for i in range(7):
        x=w*(.18+i*.11); y=h*.22+math.sin(i)*20
        d.ellipse((x-90,y-35,x+90,y+35),fill=(*PALE_SILVER,int(60+90*cloud)))
    q=ease(u); x=lerp(w*.12,w*.86,q); y=h*.48-math.sin(q*math.pi)*80
    bird_shape(d,x,y,.8,WHITE,230,.7+.18*math.sin(t*2))
    glow_line(im,partial_polyline([(w*.12,h*.48),(w*.45,h*.36),(w*.86,h*.48)],q),GREEN,4,12,180)
    seal(im,"NO ROAD · NO MAP · CLOUDS HIDE THE STARS","yet the bird corrects its direction",WHITE,True)

def visual_weak_field_noise(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    draw_field(im,t*.15,.10,55,False)
    cx,cy=w*.5,h*.42
    # noisy molecular interior
    rng=random.Random(11)
    for i in range(120):
        a=rng.random()*math.tau; rr=rng.random()*w*.31
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.58
        jitter=8*math.sin(t*3+i)
        d.ellipse((x+jitter-3,y-3,x+jitter+3,y+3),fill=(*mix(CYAN,CRIMSON,i/120),110))
    # weak central field arrow
    arrow(d,(cx,cy+90),(cx,cy-90),FIELD,5,13)
    seal(im,"WEAK FIELD · WARM · NOISY · WET","can a quantum effect survive long enough to alter function?")

def visual_cryptochrome(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    organic_blob(d,cx,cy,w*.22,h*.22,(*PALE_CYAN,220),t*.2,outline=(*CYAN,180))
    # flavin core and amino acid chain
    glow_circle(im,cx-w*.06,cy,22,GOLD,180,12)
    chain=[]
    for i in range(6):
        x=cx-w*.02+i*w*.045; y=cy+math.sin(i*.8)*32
        chain.append((x,y))
        d.ellipse((x-10,y-10,x+10,y+10),fill=(*PALE_VIOLET,230),outline=(*VIOLET,170),width=2)
    q=ease(u)
    glow_line(im,partial_polyline([(cx-w*.06,cy)]+chain,q),GOLD,4,12,220)
    if q>.72: radical_pair(d,cx+w*.18,cy,90,t*.2)
    seal(im,"CRYPTOCHROME","light excites flavin; electron transfer creates a radical pair")

def visual_spin_evolution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    draw_field(im,t*.12,p.get("tilt",.18),60,False)
    cx,cy=w*.5,h*.42
    angle=lerp(-.6,.8,ease(u))
    radical_pair(d,cx,cy,150,angle)
    # singlet-triplet phase rings
    for r,col in [(70,GOLD),(105,VIOLET)]:
        d.arc((cx-r,cy-r,cx+r,cy+r),0,int(360*ease(u)),fill=(*col,170),width=4)
    centered_text(d,(cx-w*.16,cy-110),"SINGLET",load_font(FONT_SANS_BOLD,int(h*.015)),GOLD)
    centered_text(d,(cx+w*.16,cy-110),"TRIPLET",load_font(FONT_SANS_BOLD,int(h*.015)),VIOLET)
    seal(im,"SPIN CHEMISTRY","Earth's field slightly changes how correlated states evolve")

def visual_orientation_yield(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    draw_field(im,t*.1,p.get("tilt",.28),55,False)
    # rotate cryptochrome axis
    angle=lerp(-math.pi*.45,math.pi*.45,ease(u))
    x1=cx-math.cos(angle)*120; y1=cy-math.sin(angle)*120
    x2=cx+math.cos(angle)*120; y2=cy+math.sin(angle)*120
    glow_line(im,[(x1,y1),(x2,y2)],CYAN,6,12,210)
    radical_pair(d,cx,cy,100,angle)
    # yield bars
    yield_a=.5+.45*math.cos(angle)
    yield_b=1-yield_a
    d.rectangle((w*.15,h*.65,w*.15+180*yield_a,h*.69),fill=(*GOLD,210))
    d.rectangle((w*.62,h*.65,w*.62+180*yield_b,h*.69),fill=(*VIOLET,210))
    seal(im,"ORIENTATION CHANGES REACTION YIELD","a minute chemical difference can be amplified")

def visual_retinal_pattern(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    # eye field
    cx,cy=w*.5,h*.42
    d.ellipse((cx-w*.32,cy-h*.23,cx+w*.32,cy+h*.23),outline=(*INK,190),width=4)
    d.ellipse((cx-55,cy-55,cx+55,cy+55),fill=(*LAPIS,190),outline=(*INK,160),width=3)
    # magnetic overlay
    tilt=math.sin(t*.35)*.5
    for j in range(16):
        x=w*(.24+j*.035)
        y=cy+math.sin(j*.55+tilt*3)*55
        alpha=int(40+140*smoothstep(.2,.88,u))
        d.line((x,cy-h*.18,x+tilt*80,cy+h*.18),fill=(*FIELD,alpha),width=4)
    seal(im,"A SHADOW WITHOUT AN OBJECT","perhaps a shifting magnetic pattern superimposed on vision")

def visual_evidence_open(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    items=[("LIGHT-DEPENDENT COMPASS",CYAN),("RF DISRUPTION",CRIMSON),("CRY4 IN VITRO",GOLD)]
    for i,(name,col) in enumerate(items):
        x=w*(.22+i*.28); q=smoothstep(i*.12,.62+i*.07,u)
        d.rounded_rectangle((x-120*q,h*.34-38*q,x+120*q,h*.34+38*q),radius=20,
                            fill=(*mix(WHITE,col,.15),int(225*q)),outline=(*col,int(180*q)),width=3)
        if q>.65:centered_text(d,(x,h*.34),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    # open mechanism
    d.arc((w*.32,h*.50,w*.68,h*.72),180,360,fill=(*GOLD,180),width=5)
    centered_text(d,(w*.5,h*.61),"PLAUSIBLE · NOT COMPLETE",load_font(FONT_SANS_BOLD,int(h*.018)),INK)
    seal(im,"REAL EVIDENCE · OPEN MACHINERY","sensor, radical pair, alignment, signaling remain under debate")

def visual_zeno_chemistry(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.5,h*.42
    radical_pair(d,cx,cy,150,0)
    # repeated reaction channels constrain evolution
    for i in range(8):
        y=h*(.18+i*.065)
        alpha=int(60+120*smoothstep(i*.06,.75,u))
        d.line((w*.22,y,w*.78,y),fill=(*CRIMSON,alpha),width=3)
    # one asymmetric exit
    glow_line(im,partial_polyline([(cx,cy),(w*.80,h*.30)],ease(u)),GREEN,5,13,210)
    seal(im,"CHEMISTRY PERFORMS THE WATCHING","quantum Zeno does not require a conscious observer")

def visual_quantum_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.27,h*.42); right=(w*.73,h*.42)
    # precise mechanism
    d.rounded_rectangle((left[0]-150,left[1]-110,left[0]+150,left[1]+110),radius=20,
                        fill=(*PALE_CYAN,225),outline=(*CYAN,180),width=3)
    centered_text(d,(left[0],left[1]-28),"STATE · TIMESCALE",load_font(FONT_SANS_BOLD,int(h*.018)),CYAN)
    centered_text(d,(left[0],left[1]+24),"MOLECULE · FIELD · YIELD",load_font(FONT_SANS_BOLD,int(h*.018)),CYAN)
    claims=["MIND COLLAPSES REALITY","QUANTUM HEALING","COSMIC ENTANGLEMENT"]
    fade=smoothstep(.3,.9,u)
    for i,txt in enumerate(claims):
        y=right[1]-70+i*70
        centered_text(d,(right[0],y),txt,load_font(FONT_SERIF_BOLD,int(h*.018)),(*CRIMSON,int(180*(1-.7*fade))))
        d.line((right[0]-150,y,right[0]+150,y),fill=(*CRIMSON,int(220*fade)),width=4)
    seal(im,"THE WONDER GROWS AS THE CLAIMS BECOME NARROWER","precision is the opposite of metaphysical permission")

def visual_noise_engineering(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rng=random.Random(44)
    cx,cy=w*.5,h*.42
    # noisy environment
    for i in range(150):
        x=rng.uniform(w*.12,w*.88); y=rng.uniform(h*.18,h*.67)
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*mix(CYAN,VIOLET,rng.random()),90))
    # structured path emerges using noise
    pts=[]
    for i in range(180):
        q=i/179
        x=lerp(w*.12,w*.88,q)
        y=cy+math.sin(q*math.tau*3+t*.4)*28+math.sin(q*math.tau*11)*6
        pts.append((x,y))
    glow_line(im,partial_polyline(pts,ease(u)),GOLD,5,13,210)
    seal(im,"LIFE MAY ENGINEER WITH DISSIPATION","noise can become part of the channel")

def visual_scale_ladder(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    stages=[("SPIN",GOLD),("CHEMISTRY",VIOLET),("PROTEIN",CYAN),("RETINA",FIELD),("NEURAL",GREEN),("FLIGHT",INK)]
    xs=[w*(.10+i*.16) for i in range(6)]
    for i,((name,col),x) in enumerate(zip(stages,xs)):
        q=smoothstep(i*.09,.58+i*.06,u)
        r=24+7*i
        d.ellipse((x-r*q,h*.42-r*q,x+r*q,h*.42+r*q),fill=(*mix(WHITE,col,.15),int(220*q)),outline=(*col,int(180*q)),width=3)
        if q>.68:centered_text(d,(x,h*.58),name,load_font(FONT_SANS_BOLD,int(h*.013)),col)
        if i>0: arrow(d,(xs[i-1]+r,h*.42),(x-r,h*.42),mix(stages[i-1][1],col,.5),3,9)
    # feedback arcs
    q=smoothstep(.55,.94,u)
    d.arc((w*.12,h*.18,w*.88,h*.72),200,340,fill=(*GREEN,int(160*q)),width=4)
    seal(im,"NO LEVEL ALONE CONTAINS MIGRATION","the journey is distributed across scales")

def visual_legibility(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    draw_field(im,t*.12,.12,55,False)
    left=(w*.25,h*.42); right=(w*.75,h*.42)
    # stone
    organic_blob(d,*left,80,58,(*PALE_SILVER,230),t*.2,outline=(*SILVER,170))
    # retinal architecture
    d.ellipse((right[0]-100,right[1]-70,right[0]+100,right[1]+70),outline=(*CYAN,180),width=4)
    for i in range(12):
        x=right[0]-80+i*14
        d.line((x,right[1]-55,x,right[1]+55),fill=(*FIELD,120),width=3)
    # same field through both, only one converts
    arrow(d,(left[0],left[1]+90),(left[0],left[1]-90),FIELD,4,10)
    arrow(d,(right[0],right[1]+90),(right[0],right[1]-90),FIELD,4,10)
    glow_line(im,[(right[0],right[1]),(w*.90,h*.28)],GREEN,5,12,190)
    seal(im,"INFORMATION MUST BE MADE LEGIBLE","the smallest event matters because architecture gives it a role")

def visual_sense_treaty(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    worlds=[("UV",VIOLET),("INFRARED",CRIMSON),("ELECTRIC",CYAN),("MAGNETIC",FIELD)]
    for i,(name,col) in enumerate(worlds):
        x=w*(.17+i*.22); q=smoothstep(i*.1,.62+i*.07,u)
        d.ellipse((x-60*q,h*.42-60*q,x+60*q,h*.42+60*q),fill=(*mix(WHITE,col,.18),int(225*q)),outline=(*col,int(180*q)),width=3)
        if i==0:
            for j in range(8):
                a=j*math.tau/8
                d.ellipse((x+math.cos(a)*34*q-4,h*.42+math.sin(a)*34*q-4,x+math.cos(a)*34*q+4,h*.42+math.sin(a)*34*q+4),fill=(*col,160))
        elif i==1:
            d.arc((x-38*q,h*.42-38*q,x+38*q,h*.42+38*q),0,300,fill=(*col,180),width=4)
        elif i==2:
            for j in range(5): d.line((x-40*q+j*20*q,h*.38,x-40*q+j*20*q,h*.48),fill=(*col,160),width=3)
        else:
            for j in range(5): d.arc((x-45*q-j*5,h*.36-j*3,x+45*q+j*5,h*.48+j*3),190,350,fill=(*col,160),width=3)
        if q>.68:centered_text(d,(x,h*.61),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
    seal(im,"A SENSE ORGAN IS A TREATY BETWEEN ORGANISM AND COSMOS","your world is the subset your body can translate")

def visual_world_leans(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    # visual horizon tilts while bird remains stable
    tilt=math.sin(t*.5)*.22
    cx,cy=w*.5,h*.42
    for j in range(14):
        y=h*(.18+j*.035)
        d.line((w*.12,y,w*.88,y+tilt*w*.18),fill=(*FIELD,70+j*4),width=3)
    bird_shape(d,cx,cy,.8,INK,220,.75)
    d.arc((cx-120,cy-90,cx+120,cy+90),210,330,fill=(*GOLD,150),width=4)
    seal(im,"WHAT COLOR IS NORTH?","the bird may simply experience a world that leans")

def visual_measurement_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    stages=[("MOLECULE",GOLD),("REACTION",VIOLET),("RETINA",CYAN),("BEHAVIOR",GREEN)]
    xs=[w*(.16+i*.23) for i in range(4)]
    for i,((name,col),x) in enumerate(zip(stages,xs)):
        q=smoothstep(i*.12,.60+i*.07,u)
        d.rounded_rectangle((x-75*q,h*.35-35*q,x+75*q,h*.35+35*q),radius=17,
                            fill=(*mix(WHITE,col,.15),int(220*q)),outline=(*col,int(180*q)),width=3)
        if q>.64:centered_text(d,(x,h*.35),name,load_font(FONT_SANS_BOLD,int(h*.014)),col)
        if i>0: arrow(d,(xs[i-1]+75,h*.35),(x-75,h*.35),mix(stages[i-1][1],col,.5),3,9)
    d.line((w*.14,h*.62,w*.86,h*.62),fill=(*CRIMSON,150),width=4)
    centered_text(d,(w*.5,h*.66),"THE BRIDGE IS THE WORK",load_font(FONT_SANS_BOLD,int(h*.018)),CRIMSON)
    seal(im,"NOT JUST QUANTUM BEHAVIOR IN A BIOMOLECULE","quantum behavior that makes a biological difference")

def visual_final_earth_seen(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    draw_field(im,t*.12,.20,65,True)
    # earth arc
    d.arc((w*.10,h*.40,w*.90,h*1.18),180,360,fill=(*PALE_FIELD,160),width=5)
    q=ease(u)
    x=lerp(w*.12,w*.86,q); y=h*.34-math.sin(q*math.pi)*75
    bird_shape(d,x,y,.85,WHITE,230,.7+.12*math.sin(t*2))
    # retina-to-direction continuity
    glow_line(im,partial_polyline([(w*.18,h*.52),(w*.48,h*.30),(w*.82,h*.47)],q),GREEN,5,14,210)
    seal(im,"A BIRD MAY BE SEEING THE EARTH","the field enters as chemistry and exits as direction",WHITE,True)

VISUALS:dict[str,Callable]={
    "night":visual_night_migration,
    "noise":visual_weak_field_noise,
    "crypto":visual_cryptochrome,
    "spin":visual_spin_evolution,
    "yield":visual_orientation_yield,
    "retina":visual_retinal_pattern,
    "evidence":visual_evidence_open,
    "zeno":visual_zeno_chemistry,
    "caution":visual_quantum_caution,
    "noise_engineering":visual_noise_engineering,
    "ladder":visual_scale_ladder,
    "legibility":visual_legibility,
    "treaty":visual_sense_treaty,
    "leans":visual_world_leans,
    "bridge":visual_measurement_bridge,
    "final":visual_final_earth_seen,
}

SCENES:list[Scene]=[
    Scene("Night departure","A bird leaves northern Europe at night.",6.0,"night",{}),
    Scene("No road","No road. No map.",5.5,"night",{}),
    Scene("Clouds","Clouds hide the stars and the landscape becomes unfamiliar darkness.",8.0,"night",{}),
    Scene("Direction correction","Yet the animal corrects its direction and continues.",7.0,"night",{}),
    Scene("Chemical compass","The bird may perceive Earth's magnetic field through chemical reactions in its eyes.",9.0,"retina",{}),
    Scene("Quantum mechanically","Not metaphorically. Quantum mechanically.",6.0,"spin",{}),

    Scene("Weak field","Earth's magnetic field is weak.",5.5,"noise",{}),
    Scene("Warm noisy wet","The biological interior is warm, noisy, and wet.",7.0,"noise",{}),
    Scene("Quantum question","Can life organize a quantum effect long enough to alter biological function?",9.0,"noise",{}),
    Scene("Narrow claim","The question is not whether life is mystical because everything is quantum.",8.0,"caution",{}),
    Scene("Organism scale","Does a recognizably quantum process explain an ability at organism scale?",8.0,"bridge",{}),
    Scene("Magnetoreception","Magnetoreception is one of the strongest places to look.",6.5,"final",{}),

    Scene("Cryptochrome","The candidate mechanism begins with cryptochrome.",6.0,"crypto",{}),
    Scene("Retinal protein","Certain cryptochromes occur in the bird retina.",6.5,"crypto",{}),
    Scene("Photon excitation","Light excites flavin inside the protein.",6.0,"crypto",{}),
    Scene("Electron transfer","An electron transfers along a chain of amino acids.",7.0,"crypto",{}),
    Scene("Radical pair","Two molecules with unpaired electrons form a radical pair.",7.0,"crypto",{}),
    Scene("Correlated spin","The electrons begin in a correlated spin state.",6.5,"spin",{}),
    Scene("Field alters evolution","A magnetic field alters interconversion between spin configurations.",8.5,"spin",{}),
    Scene("Direction sensitivity","The chemical reaction becomes weakly sensitive to direction.",7.5,"yield",{}),
    Scene("Planet molecule","The planet enters the molecule.",6.0,"yield",{}),

    Scene("Spin not rotation","Electron spin is not a tiny ball literally rotating.",7.0,"spin",{}),
    Scene("Singlet triplet","Radical pairs occupy correlated singlet and triplet configurations.",8.0,"spin",{}),
    Scene("Nuclear interactions","Atomic nuclei create local magnetic interactions.",7.0,"spin",{}),
    Scene("Earth adds influence","Earth's field adds another influence.",6.5,"spin",{}),
    Scene("Subtle balance","The balance is extraordinarily subtle.",6.0,"yield",{}),
    Scene("Rotate protein","Change protein orientation and reaction yield may change minutely.",8.5,"yield",{}),
    Scene("Amplify difference","A minute chemical difference may be amplified through signaling.",8.0,"retina",{}),
    Scene("Coherent arrangement","Enough oriented cryptochromes could provide directional information.",8.5,"retina",{}),
    Scene("Not north text","Not north written across the sky.",5.5,"retina",{}),
    Scene("Visual modulation","Perhaps a shifting pattern superimposed upon vision.",7.0,"retina",{}),
    Scene("Planet brightness","A brightness whose source is the planet.",6.5,"retina",{}),

    Scene("Behavior evidence","Behavioral experiments support a light-dependent magnetic compass.",8.0,"evidence",{}),
    Scene("RF disruption","Weak radiofrequency fields can disrupt orientation.",7.5,"evidence",{}),
    Scene("Cry4 evidence","European robin cryptochrome 4 shows magnetic sensitivity in vitro.",8.5,"evidence",{}),
    Scene("Real evidence","This is real evidence.",5.5,"evidence",{}),
    Scene("Not complete","It is not a completed explanation.",5.5,"evidence",{}),
    Scene("Open questions","Sensor identity, radical pair, alignment, signaling, and natural sensitivity remain open.",9.5,"evidence",{}),
    Scene("Plausible compass","The compass is plausible. Its exact machinery remains open.",7.0,"evidence",{}),

    Scene("Zeno mechanism","A 2024 proposal explored asymmetric recombination and a quantum Zeno-related effect.",9.0,"zeno",{}),
    Scene("No conscious watching","The bird is not consciously observing quantum states.",7.0,"zeno",{}),
    Scene("Reaction constraints","Asymmetric reaction pathways can constrain state evolution.",8.0,"zeno",{}),
    Scene("Chemistry watches","Chemistry performs the watching.",6.0,"zeno",{}),
    Scene("No philosopher bird","No philosopher-bird is required.",5.5,"zeno",{}),

    Scene("Projection danger","Quantum biology attracts metaphysical projection.",6.5,"caution",{}),
    Scene("Permission slip","The word quantum becomes a permission slip.",6.5,"caution",{}),
    Scene("Mind claims","Consciousness collapses reality. Thought heals cells. Entanglement proves unity.",8.5,"caution",{}),
    Scene("Refuse vagueness","Serious quantum biology succeeds by refusing vagueness.",7.5,"caution",{}),
    Scene("Which state","Which state? Which timescale? Which molecule?",7.5,"caution",{}),
    Scene("Which field","Which field strength and measurable change in yield?",7.0,"caution",{}),
    Scene("Which alternative","Which classical alternative has been excluded?",6.5,"caution",{}),
    Scene("Narrow wonder","The wonder grows as the claims become narrower.",7.0,"caution",{}),

    Scene("Photosynthesis caution","Photosynthesis offers another caution.",6.0,"noise_engineering",{}),
    Scene("Coherence proposal","Quantum coherence was proposed to guide energy through molecular networks.",8.5,"noise_engineering",{}),
    Scene("Complicated picture","Later analysis complicated the picture.",6.0,"noise_engineering",{}),
    Scene("Vibrations","Some oscillations were molecular vibrations rather than functional electronic coherence.",8.5,"noise_engineering",{}),
    Scene("No pristine computer","Life may not preserve a pristine quantum computation against noise.",8.0,"noise_engineering",{}),
    Scene("Engineer dissipation","It may exploit structured interaction with the environment.",7.5,"noise_engineering",{}),
    Scene("Noise channel","Life may use noise as part of the channel.",6.5,"noise_engineering",{}),

    Scene("Enzyme case","Enzymes provide another case.",5.5,"bridge",{}),
    Scene("Tunneling","Electrons and protons can tunnel through barriers in catalysts.",7.5,"bridge",{}),
    Scene("No grand revolution","Quantum mechanics in biology is not automatically a philosophical revolution.",8.0,"caution",{}),
    Scene("Functional importance","The task is to establish when tunneling matters functionally.",7.5,"bridge",{}),
    Scene("Precisely strange","The molecule becomes more precisely strange, not magical.",7.0,"caution",{}),

    Scene("Continent bridge","The avian compass joins the smallest scale to a journey across a continent.",9.0,"ladder",{}),
    Scene("Spin to chemistry","A correlated electron state biases chemistry.",6.5,"ladder",{}),
    Scene("Chemistry to protein","Chemistry alters a protein.",5.5,"ladder",{}),
    Scene("Protein to retina","Proteins affect retinal signaling.",6.0,"ladder",{}),
    Scene("Retina to neural","Neural systems integrate direction with stars, odors, landmarks, and learning.",9.5,"ladder",{}),
    Scene("Neural to wings","Muscles move wings. The bird crosses a sea.",7.0,"ladder",{}),
    Scene("Distributed journey","No level alone contains migration.",6.5,"ladder",{}),

    Scene("Simple causation fails","This is a problem for simple pictures of causation.",7.0,"ladder",{}),
    Scene("No one real level","Navigation is not located in one privileged layer.",7.5,"ladder",{}),
    Scene("Quantum constrains","Quantum events constrain chemical possibilities.",6.5,"ladder",{}),
    Scene("Architecture stabilizes","Protein architecture stabilizes those events.",6.5,"ladder",{}),
    Scene("Cells amplify","Cellular organization amplifies them.",6.5,"ladder",{}),
    Scene("Brains interpret","Neural systems interpret the signal.",6.5,"ladder",{}),
    Scene("Behavior matters","Behavior places the bird where the signal matters.",7.0,"ladder",{}),
    Scene("Evolution preserves","Evolution preserves arrangements that connect the scales.",8.0,"ladder",{}),
    Scene("Feedback ladder","Causation forms a ladder with feedback in both directions.",8.0,"ladder",{}),

    Scene("Function relational","A physical effect becomes meaningful only inside an architecture that can use it.",9.0,"legibility",{}),
    Scene("Stone field","Earth's field passes through stones. The stone does not navigate.",7.0,"legibility",{}),
    Scene("Protein field","The field passes through many proteins.",6.5,"legibility",{}),
    Scene("Organized conversion","Only certain organized systems convert influence into direction.",8.0,"legibility",{}),
    Scene("Legibility","Information is not merely present. It must be made legible.",7.0,"legibility",{}),

    Scene("Perception generally","This resembles perception more generally.",6.0,"treaty",{}),
    Scene("Eye world","Light strikes everywhere, but an eye turns light into a world.",7.5,"treaty",{}),
    Scene("Ear voice","Air vibrates everywhere, but an ear turns pressure into voice.",7.5,"treaty",{}),
    Scene("Retina field","A retina may turn magnetic regularity into actionable experience.",8.5,"treaty",{}),
    Scene("Treaty","A sense organ is a treaty between organism and cosmos.",7.5,"treaty",{}),
    Scene("Bees","Bees see ultraviolet patterns.",5.5,"treaty",{}),
    Scene("Pit vipers","Pit vipers detect infrared.",5.5,"treaty",{}),
    Scene("Fish","Some fish sense electric fields.",5.5,"treaty",{}),
    Scene("Bird world","A migratory bird may inhabit a world threaded with magnetic inclination.",8.5,"treaty",{}),
    Scene("Subset","Your world is the subset your body knows how to translate.",7.5,"treaty",{}),

    Scene("What does field look like","What would a magnetic field look like?",6.0,"leans",{}),
    Scene("Not known","Researchers do not know whether magnetoreception is literally visual.",7.5,"leans",{}),
    Scene("Head movement","Models imagine patterns changing as the head moves.",7.0,"leans",{}),
    Scene("Human limitation","You translate a foreign sense into one of your own.",7.5,"leans",{}),
    Scene("Color north","What color is north? What shape is inclination?",7.0,"leans",{}),
    Scene("World leans","The bird may simply experience a world that leans.",7.0,"leans",{}),

    Scene("No hidden human senses","The evidence does not prove hidden human senses or planetary consciousness.",8.5,"caution",{}),
    Scene("Disciplined astonishment","The responsible response is astonishment disciplined by scale.",8.0,"caution",{}),
    Scene("Weak field chemistry","A weak field may alter spin chemistry.",6.5,"yield",{}),
    Scene("Protein amplification","A protein may preserve and amplify the difference.",7.0,"crypto",{}),
    Scene("Orientation","An organism may turn that difference into orientation.",7.0,"final",{}),
    Scene("Enough","That is enough. The actual claim is already extraordinary.",7.0,"final",{}),

    Scene("Frontier","Quantum biology remains a frontier because the criteria are difficult.",8.0,"bridge",{}),
    Scene("Complex systems","Many variables can produce similar outcomes.",6.5,"bridge",{}),
    Scene("Short signatures","Quantum signatures can be brief, indirect, and hard to isolate.",7.5,"bridge",{}),
    Scene("Plausibility not proof","A model can show plausibility without proving evolution uses it in vivo.",8.5,"bridge",{}),
    Scene("Connect scales","The field needs measurements connecting microscopic dynamics to organism function.",9.0,"bridge",{}),
    Scene("Bridge work","That bridge is the work.",5.5,"bridge",{}),

    Scene("Night return","A bird leaves at night.",5.5,"final",{}),
    Scene("Photon trigger","Inside its retina, photons may trigger electron transfer.",7.0,"crypto",{}),
    Scene("Pairs vanish","Radical pairs form and vanish in fractions of a second.",7.0,"spin",{}),
    Scene("Planetary iron","Their spin dynamics may be nudged by a field generated deep within Earth.",8.5,"spin",{}),
    Scene("No equations needed","The bird does not know the equations. It does not need to.",7.0,"final",{}),
    Scene("Body equation","Its body may be an equation evolution learned to solve.",8.0,"ladder",{}),
    Scene("Chemistry direction","The field enters as chemistry and exits as direction.",7.5,"final",{}),
    Scene("Wings south","Then wings carry the result south.",6.5,"final",{}),

    Scene("Same field","You walk beneath the same field without feeling it.",7.0,"final",{}),
    Scene("Translation difference","That does not make the field absent. Your body translates differently.",8.0,"treaty",{}),
    Scene("Reality exceeds senses","Reality exceeds every sensory world.",7.0,"treaty",{}),
    Scene("Untranslated structures","Around you are structures too weak, fast, slow, or unfamiliar to become experience.",9.0,"treaty",{}),
    Scene("Nature strange to itself","Nature contains forms of perception by which it becomes strange to itself.",8.5,"treaty",{}),
    Scene("No color","A magnetic field has no color.",5.5,"final",{}),
    Scene("Seeing Earth","Yet somewhere above you, an animal may be seeing the Earth.",8.5,"final",{}),
]

def render_frame(scene,frame_index,frame_count,width,height,seed):
    u=frame_index/max(1,frame_count-1); t=u*scene.duration
    dark=scene.visual in {"night","final"} and scene.title in {"Night departure","No road","Clouds","Direction correction","Night return","No equations needed","Chemistry direction","Wings south","Same field","No color","Seeing Earth"}
    im=background(width,height,seed,dark)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im,dark)
    return im.convert("RGB")

def require_ffmpeg():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg is required but was not found on PATH")
    return exe
def encode_scene(scene_index,fps):
    ffmpeg=require_ffmpeg(); frame_dir=FRAMES/f"scene_{scene_index:03d}"
    out=SCENES_DIR/f"scene_{scene_index:03d}.mp4"
    cmd=[ffmpeg,"-y","-framerate",str(fps),"-i",str(frame_dir/"%05d.jpg"),
         "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(out)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out
def render_scene(scene_index,scene,fps,width,height,preview):
    frame_dir=FRAMES/f"scene_{scene_index:03d}"
    frame_dir.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    fc=max(2,round(scene.duration*fps))
    if preview:
        samples=[0,int(fc*.35),int(fc*.72),fc-1]
        for oi,fi in enumerate(samples):
            render_frame(scene,fi,fc,width,height,scene_index*1000+fi).save(frame_dir/f"preview_{oi:02d}.jpg",quality=95)
        return frame_dir
    for fi in range(fc):
        p=frame_dir/f"{fi:05d}.jpg"
        if p.exists():continue
        render_frame(scene,fi,fc,width,height,scene_index*1000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(scene_index,fps)
def concatenate(paths):
    ffmpeg=require_ffmpeg(); c=OUTPUT/"concat.txt"
    c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    out=OUTPUT/"a_bird_may_see_the_earths_magnetic_field.mp4"
    subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out
def export_timeline():
    cursor=0; payload=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3); r["end_seconds"]=round(cursor+s.duration,3)
        payload.append(r); cursor+=s.duration
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({
        "title":"a bird may see the earth's magnetic field",
        "runtime_seconds":round(cursor,3),
        "scene_count":len(SCENES),
        "style":{
            "continuity_object":"blue-green geomagnetic field lattice",
            "shot_duration_range_seconds":[5,10],
            "palette_roles":{
                "field":"geomagnetic inclination",
                "gold":"photon excitation and correlated radical pair",
                "cyan":"cryptochrome and retinal architecture",
                "violet":"spin-state evolution",
                "crimson":"disruption and metaphysical overreach",
                "green":"amplified biological direction",
            }
        },
        "scenes":payload
    },indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def make_contact_sheet(width,height):
    tw=320; th=int(tw*height/width); thumbs=[]
    for i,s in enumerate(SCENES,1):
        fc=max(2,round(s.duration*DEFAULT_FPS)); im=render_frame(s,int(fc*.72),fc,width,height,i*1000+72)
        im.thumbnail((tw,th)); thumbs.append((i,s.title,im.copy()))
    cols=4; rows=math.ceil(len(thumbs)/cols); cell_h=th+52
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),WHITE); d=ImageDraw.Draw(sheet); font=load_font(FONT_SANS_BOLD,15)
    for idx,title,im in thumbs:
        slot=idx-1; x=(slot%cols)*tw; y=(slot//cols)*cell_h
        sheet.paste(im,(x,y)); d.text((x+10,y+th+8),f"{idx:03d}  {title}",font=font,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; sheet.save(p,quality=94); return p
def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS)
    p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    p.add_argument("--scene",type=int,default=None)
    p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()
def main():
    args=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if args.scene is not None:
        if not 1<=args.scene<=len(SCENES): raise ValueError(f"--scene must be between 1 and {len(SCENES)}")
        print(render_scene(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:03d}/{len(SCENES):03d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,args.fps,args.width,args.height,args.preview)
        if not args.preview: rendered.append(r)
    if not args.no_contact_sheet: print(f"Contact sheet: {make_contact_sheet(args.width,args.height)}")
    if not args.preview: print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
