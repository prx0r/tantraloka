#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES_ROOT = ROOT / 'frames'
SCENES_ROOT = ROOT / 'scenes'
W, H = 1280, 720
FPS = 10
DURATION = 4.8
NFRAMES = int(FPS * DURATION)
SEED = 33033

# De Sole palette — light-as-medium optical world
WARM_VOID = (28, 24, 20)
DEEP_UMBER = (58, 46, 34)
IVORY_FIELD = (245, 240, 226)
PARCHMENT_LIGHT = (250, 247, 239)
GOLD_WARMTH = (212, 165, 116)
GOLD_LIGHT = (242, 214, 156)
PURE_WHITE = (255, 254, 247)
SKY_BLUE = (139, 164, 199)
SILVER_GREY = (168, 176, 184)
CINNABAR = (201, 60, 40)
CRIMSON = (160, 48, 48)
INK = (34, 32, 30)
TEAL = (100, 150, 155)
SLATE = (118, 126, 140)
VIOLET = (150, 130, 185)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def field(seed, bg=WARM_VOID):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(38,68)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.2 + fine[...,None]*0.9
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*6,0,16)[...,None]*0.6
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

def luminous_field(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32)
    base[:]=np.array(WARM_VOID,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.5 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    glow=np.exp(-(((xx-W/2)/(W*.34))**2+((yy-H*.42)/(H*.28))**2)*2.4)
    base[...,0]+=glow*14; base[...,1]+=glow*12; base[...,2]+=glow*8
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def glow(im,xy,r,color,alpha=145,blur=16):
    ov=layer(); d=ImageDraw.Draw(ov); x,y=xy
    d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(color,alpha))
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))

def lineglow(im,pts,color,width=3,alpha=145,blur=8):
    ov=layer(); d=ImageDraw.Draw(ov)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def bezier(p0,p1,p2,p3,n=90):
    out=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        out.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return out

def partial(points,a):
    a=clamp(a)
    if a<=0:return []
    if a>=1:return points
    f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points):
        A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out

def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)

def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,90),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD_WARMTH,70),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CINNABAR,GOLD_WARMTH)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(26,22,18,210),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=IVORY_FIELD)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SILVER_GREY)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_WARMTH)

def dust(im,seed,n=60):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(110,W-110)); y=float(rng.uniform(110,H-170)); r=float(rng.uniform(.8,2.0))
        c=mix(SILVER_GREY,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,65))))
    im.alpha_composite(ov)


def light_bloom(im,cx,cy,r,col,alpha=200):
    for i in range(6):
        rr=r*(1+i*.25)
        draw=ImageDraw.Draw(im)
        draw.ellipse((cx-rr,cy-rr*.7,cx+rr,cy+rr*.7),outline=rgba(col,alpha-30*i),width=2)

def spectrum_band(d,x0,y0,x1,y1,col,alpha=160):
    d.rectangle((x0,y0,x1,y1),fill=rgba(col,alpha))

def arc_pts(cx,cy,rx,ry,a0,a1,n=80):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx,cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,H/2
    r=6+40*ease(t)
    glow(im,(cx,cy),120,PURE_WHITE,190,42)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=rgba(PURE_WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    d.ellipse((cx-r*.35,cy-r*.35,cx+r*.35,cy+r*.35),fill=rgba((255,255,255),255))
    for i in range(8):
        a=i*2*math.pi/8; pts=partial([(cx,cy),(cx+math.cos(a)*r*3,cy+math.sin(a)*r*2)],ease(max(0,t-.2)))
        if len(pts)>1:lineglow(im,pts,PURE_WHITE,2,70,6)
    d.text((640,505),'a point of light appears — instant radiation of goodness',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,340
    # breath-fog on invisible surface
    pts=[]
    for i in range(80):
        a=i*2*math.pi/80; rr=80+20*math.sin(i*.7+t*2)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.5
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,SILVER_GREY,2,90,7)
    for i in range(40):
        a=i*2*math.pi/40; rr=60+15*math.sin(i*.9+t*2.5)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.45
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(SILVER_GREY,PURE_WHITE,.3),100))
    glow(im,(cx,cy-20),30,SILVER_GREY,80,10)
    d.text((640,505),'a witness breathes — the light has a subject',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # aperture iris opening
    max_r=200
    r=lerp(8,max_r,ease(t))
    glow(im,(cx,cy),80,GOLD_WARMTH,160,24)
    for i in range(12):
        a=i*2*math.pi/12
        x0=cx+math.cos(a)*r*.92; y0=cy+math.sin(a)*r*.68
        x1=cx+math.cos(a)*r*1.08; y1=cy+math.sin(a)*r*.78
        d.polygon([(cx,cy),(x0,y0),(x1,y1)],fill=rgba(WARM_VOID,200))
    d.ellipse((cx-r,cy-r*.74,cx+r,cy+r*.74),outline=rgba(GOLD_WARMTH,190),width=3)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.7; y=cy+math.sin(a)*r*.5
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(GOLD_LIGHT,150))
    d.text((640,505),'the visible sun is the gate to the invisible one',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # prism correspondence
    glow(im,(180,cy),30,PURE_WHITE,160,14)
    d.ellipse((165,cy-15,195,cy+15),fill=rgba(PURE_WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    ray=partial(bezier((200,cy),(320,cy-60),(480,cy-80),(cx,cy-90),90),smooth(.05,.85,t))
    if len(ray)>1:lineglow(im,ray,PURE_WHITE,4,130,8)
    cols=[CRIMSON,GOLD_WARMTH,GOLD_LIGHT,PURE_WHITE,SKY_BLUE,VIOLET]
    for i,col in enumerate(cols):
        y=lerp(160,400,i/(len(cols)-1))
        band=partial(bezier((cx,cy-90),(580,y+20),(820,y-20),(1070,y),90),smooth(.1+i*.08,.9,t))
        if len(band)>1:lineglow(im,band,col,3,100,6)
    d.text((640,505),'correspondence — not argument, but resonance',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # five behaviors of light separate
    glow(im,(cx,cy),80,GOLD_LIGHT,130,24)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(PURE_WHITE,255),outline=rgba(GOLD_WARMTH,220),width=2)
    behaviors=[('purity',PURE_WHITE),(('instant',GOLD_LIGHT)),('penetration',SKY_BLUE),('warmth',GOLD_WARMTH),('omnipresence',VIOLET)]
    for i,(lab,col) in enumerate(behaviors):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*210; y=cy+math.sin(a)*130
        rr=20+18*math.sin(t*3+i)
        glow(im,(x,y),30,col,90,10)
        d.ellipse((x-rr,y-rr*.6,x+rr,y+rr*.6),outline=rgba(col,200),fill=rgba(mix(WARM_VOID,col,.1),60),width=2)
        d.text((x,y+34),lab,font=TINY_FONT,fill=col,anchor='mm')
        seg=partial([(cx+math.cos(a)*28,cy+math.sin(a)*18),(x-math.cos(a)*40,y-math.sin(a)*20),(x,y)],smooth(.05+i*.08,.82,t))
        if len(seg)>1:lineglow(im,seg,col,2,80,5)
    d.text((640,505),'five properties — one light behaving differently',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # instant radiation
    glow(im,(cx,cy),140,PURE_WHITE,200,40)
    for r,col in [(45,GOLD_LIGHT),(90,PURE_WHITE),(140,GOLD_WARMTH),(200,PURE_WHITE)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,140-20*(r//45)),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(PURE_WHITE,255))
    d.text((640,505),'goodness extends by its own nature — radiated, not created',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    # participant orbit
    pts=[]
    for i in range(120):
        u=i/119; a=-math.pi/2+u*4.2*math.pi
        rr=30+u*200; x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.55
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,SILVER_GREY,3,110,7)
    for i in range(8):
        u=i/7; a=-math.pi/2+u*4.2*math.pi; rr=30+u*200
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.55
        glow(im,(x,y),12,mix(SILVER_GREY,GOLD_LIGHT,.4),80,7)
    d.text((640,505),'to be alive is to be in the sun\'s orbit — as a participant',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    # orbit becomes interior tube
    for i in range(10):
        rr=30+i*22; col=mix(SILVER_GREY,GOLD_WARMTH,i/10)
        d.ellipse((cx-rr,cy-rr*.68,cx+rr,cy+rr*.68),outline=rgba(col,120-i*10),width=2)
    pts=[]
    for i in range(90):
        u=i/89; a=u*2*math.pi*3
        r=60+120*ease_out(t); x=cx+math.cos(a+t)*r*.9; y=cy+math.sin(a+t)*r*.5
        x=lerp(cx,x,ease_out(t))
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,GOLD_WARMTH,4,120,8)
    glow(im,(cx,cy),50,GOLD_LIGHT,110,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(PURE_WHITE,255),outline=rgba(GOLD_WARMTH,220),width=2)
    d.text((640,505),'the orbit\'s trace — you are inside what you thought you observed',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # standing wave — the hymn
    for i in range(12):
        y=lerp(150,410,i/11)
        pts=[]
        for j in range(100):
            u=j/99; x=lerp(180,1100,u)
            yy=y+math.sin(u*2*math.pi*2.5+t*2+i*.35)*(18+8*math.sin(t*1.5+i*.5))
            pts.append((x,yy))
        lineglow(im,pts,mix(GOLD_WARMTH,CINNABAR,i/12),2,85,5)
    glow(im,(cx,cy),70,CINNABAR,100,22)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(PURE_WHITE,255),outline=rgba(CINNABAR,220),width=2)
    d.text((640,505),'the Muses never argue with Apollo — they sing',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # eye becomes light
    glow(im,(cx,cy),90,GOLD_LIGHT,130,22)
    draw=ImageDraw.Draw(im)
    draw.arc((cx-72,cy-34,cx+72,cy+34),180,360,fill=rgba(GOLD_WARMTH,210),width=3)
    draw.arc((cx-72,cy-34,cx+72,cy+34),0,180,fill=rgba(GOLD_WARMTH,210),width=3)
    inner_r=lerp(30,80,ease(t))
    draw.ellipse((cx-inner_r,cy-inner_r,cx+inner_r,cy+inner_r),fill=rgba(GOLD_LIGHT,200),outline=rgba(GOLD_WARMTH,180),width=2)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=rgba(PURE_WHITE,255))
    for i in range(14):
        a=-math.pi/2+i*2*math.pi/14+t*.06
        x=cx+math.cos(a)*inner_r; y=cy+math.sin(a)*inner_r
        segment=partial(bezier((x,y),(cx+math.cos(a)*(inner_r+40),cy+math.sin(a)*(inner_r+40)),(cx+math.cos(a)*260,cy+math.sin(a)*150),(cx+math.cos(a)*280,cy+math.sin(a)*170),80),smooth(.03+i*.03,.82,t))
        if len(segment)>1:lineglow(im,segment,mix(GOLD_LIGHT,PURE_WHITE,i/14),2,70,5)
    d.text((640,505),'the eye discovers it is made of the light it was looking at',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,H/2
    # recognition — the point is interior
    r=12+30*ease(t)
    glow(im,(cx,cy),60,GOLD_LIGHT,150,20)
    d.ellipse((cx-r,cy-r*.7,cx+r,cy+r*.7),fill=rgba(PURE_WHITE,255),outline=rgba(GOLD_WARMTH,220),width=2)
    for i in range(6):
        rr=r*(1.5+i*.3); alpha=100-15*i
        d.ellipse((cx-rr,cy-rr*.7,cx+rr,cy+rr*.7),outline=rgba(GOLD_WARMTH,alpha),width=1)
    pts=[]
    for i in range(40):
        a=i*2*math.pi/40; rr=30+15*math.sin(i*1.3+t*2)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.5
        pts.append((x,y))
    reveal=partial(pts,smooth(.5,.95,t))
    if len(reveal)>1:lineglow(im,reveal,SILVER_GREY,2,70,5)
    d.text((640,505),'the same point — now recognized as the light by which you see',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')

def sc12(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # closing seal — light that knows itself
    glow(im,(cx,cy),100,GOLD_WARMTH,140,28)
    for r,col in [(220,GOLD_WARMTH),(170,GOLD_LIGHT),(120,PURE_WHITE),(70,GOLD_WARMTH)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,130-20*(r//50)),width=2)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(PURE_WHITE,255),outline=rgba(GOLD_WARMTH,220),width=2)
    for i in range(16):
        a=i*2*math.pi/16
        p0=(cx+math.cos(a)*48,cy+math.sin(a)*48)
        p1=(cx+math.cos(a)*195,cy+math.sin(a)*130)
        pts=partial([p0,p1],ease(t))
        if len(pts)>1:lineglow(im,pts,GOLD_LIGHT,2,60,4)
    d.text((640,505),'the light that reads these words is the light that knows itself',font=SUB_FONT,fill=SILVER_GREY,anchor='mm')


SCENES=[
Scene('ds01','The Point','A single point of light radiates in the void.','Anuttara','The opening: instant radiation of goodness from a dimensionless point.','point_of_light',['light','point','origin'],'chapter_i','radiant point emergence',sc01),
Scene('ds02','The Witness','Breath-fog appears on an invisible surface.','Sākṣin','The viewer is present as the light\'s witness.','breath_witness',['breath','witness','presence'],'chapter_i','breath condensation pattern',sc02),
Scene('ds03','The Gate','The sun\'s disc becomes an aperture.','Aperture','The visible sun is the gate to the invisible one.','iris_gate',['gate','aperture','threshold'],'chapter_ii','iris aperture opening',sc03),
Scene('ds04','Correspondence','White light splits into spectrum and recombines.','Correspondentia','Correspondence as method — light through prism.','prism_spectrum',['prism','spectrum','correspondence'],'chapter_ii','prism refraction field',sc04),
Scene('ds05','Five Behaviors of Light','Five luminous qualities separate and become distinguishable.','Quinque','Purity, instant radiation, penetration, warmth, omnipresence.','five_behaviors',['five','light','behaviors'],'chapter_iii','five-node light orbit',sc05),
Scene('ds06','Instant Radiation','Goodness extends by its own nature.','Radiatio','The instant radiation of goodness — radiated, not created.','radiation_field',['radiation','goodness','extension'],'chapter_iii','radiating concentric rings',sc06),
Scene('ds07','The Orbit','A silver arc traces across the luminous field.','Orbis','The participant\'s orbit begins as a distant arc.','orbital_trace',['orbit','arc','participant'],'chapter_iv','silver orbital spiral',sc07),
Scene('ds08','The Interior','The orbit becomes a tube — the viewer is inside it.','Interior','What was observed externally is revealed as interior.','interior_orbit',['interior','orbit','tube'],'chapter_iv','converging orbital tunnel',sc08),
Scene('ds09','The Hymn','Standing waves structure the entire luminous field.','Hymnus','The Muses never argue with Apollo — they sing.','standing_wave',['hymn','wave','standing'],'chapter_v','Chladni wave field',sc09),
Scene('ds10','The Eye Becomes Light','The eye\'s interior is made of the same light.','Oculus','The distinction between seer and seen dissolves.','eye_light',['eye','light','dissolution'],'chapter_v','eye-to-light radial emission',sc10),
Scene('ds11','Recognition','The same point of light — now interior.','Recognitio','What was exterior is recognized as the viewer\'s own light.','recognition',['recognition','interior','return'],'chapter_vi','returning point of light',sc11),
Scene('ds12','The Seal','Light that knows itself.','Lux sui gnara','The closing seal: subject, object, and instrument are one light.','closing_seal',['seal','light','knowledge'],'seal','concentric light cosmogram',sc12),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000: continue
        t=i/max(1,NFRAMES-1)
        im=luminous_field(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,40); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=94)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(p).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,540),WARM_VOID)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — The Sun That Knows Itself (De Sole)','source_basis':'Marsilio Ficino, De Sole / The Book of the Sun (1494), as expanded in essay 33.','style':{'family':'light-as-medium optical cosmography','background':'warm void field with inner luminosity','ink':'silver-grey and deep umber','accent':'gold-warmth, sky-blue, cinnabar, pure white','materials':['pure light','apertures','prism spectra','standing waves','orbital traces','the eye-as-light']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'chapter_i':['ds01','ds02'],'chapter_ii':['ds03','ds04'],'chapter_iii':['ds05','ds06'],'chapter_iv':['ds07','ds08'],'chapter_v':['ds09','ds10'],'chapter_vi_and_seal':['ds11','ds12']},'reusability_notes':{'ds01':'Use for origin, instant radiation, or first point of light.','ds03':'Use for aperture, gate, threshold, or visible/invisible mediation.','ds04':'Use for prism, spectrum, correspondence, or resonance epistemology.','ds05':'Use for five properties or differentiated manifestation.','ds07':'Use for orbital paths, participation, or cosmic circulation.','ds09':'Use for hymn, praise, standing waves, or sung knowledge.','ds10':'Use for seer-seen dissolution, eye as light, or recognition.','ds12':'Use as a closing seal for light-based or recognition-centered packs.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — The Sun That Knows Itself

## Aim
This pack visualizes Ficino's De Sole: the sun as conscious being, light as the image of goodness, correspondence as the method of knowing.

## Core structure
1. A point of light radiates — instant radiation of goodness
2. A witness breathes — the light has a subject
3. The visible sun is the gate to the invisible one
4. Correspondence: light through prism shows relation without argument
5. Five properties of light: purity, instant radiation, harmless penetration, nourishing warmth, omnipresence
6. The participant's orbit: to be alive is to be in the sun's orbit
7. The hymn: the Muses never argue with Apollo, they sing
8. The eye becomes the light it was looking at
9. The same point — now recognized as interior

## Visual rules
- Light is never background — it is always the subject and substance of the frame.
- The opening point is the same entity as the closing point — it transforms, it does not disappear.
- No ball of fire in space. No rays from off-screen. No face on the sun.
- No generic sparkles — every visible particle is breath-fog, a prismatic speck, or a gold grain.
- The five properties of light must each have a distinct visual behavior.
- The hymn is the structural climax — the visual language shifts from description to enactment.

## Style
Warm void field, gold-warmth presence, pure white radiation, silver-grey orbital traces, cinnabar hymn intensity, sky-blue penetration.

## New motifs
- instant radiation point
- breath-fog witness pattern
- iris aperture gate
- prism spectrum correspondence
- five-behavior light orbit
- silver orbital trace
- standing wave Chladni field
- eye-to-light dissolution
- recognition point return
- concentric light cosmogram seal

## Guardrails
- The sun is not a character. No anthropomorphism.
- The essay is radically simple — do not add diagrams or complexity the essay lacks.
- The closing enacts the dissolution of the seer/seen — not as a conclusion but as recognition.
- Every visual element carries semantic weight. No decoration.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — The Sun That Knows Itself

## Inheritance
This pack introduces a light-as-medium visual language distinct from the earlier parchment, manuscript, and mineral vocabularies.

## Differentiation
Where the tattva packs emphasized structural manifestation and the breath packs emphasized axial mechanics, this pack emphasizes:
- light as active substance, not illumination
- correspondence as a visual operation (prism, spectrum, resonance)
- the dissolution of seer and seen
- optical depth rather than geometric space
- the participant's interiority

## New symbols
1. instant radiation point
2. breath-fog condensation
3. iris aperture gate
4. prism spectrum band
5. five-behavior light orbit
6. radiating goodness field
7. silver orbital trace
8. interior orbital tube
9. standing wave hymn field
10. eye-becoming-light
11. recognition point return
12. light cosmogram seal

## New relationships
- point → radiation → illumination
- visible light → gate → invisible light
- white light → prism → spectrum → recombination
- observer → breath → witness → participant
- external orbit → interior condition
- eye looking → eye emitting → eye as light
- the same point, first exterior, then interior

## Material vocabulary
- warm void background
- gold-warmth presence
- pure white radiation
- silver-grey traces
- sky-blue penetration
- cinnabar hymn intensity
- prismatic spectrum bands

## Closing seal
Concentric rings of gold-warmth and pure white around a central bindu, with sixteen rays radiating the recognition: the light that reads these words is the light that knows itself.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — The Sun That Knows Itself (De Sole) Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run:
```bash
python render_pack.py
```
The renderer is resume-safe.
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'sun_that_knows_itself_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'sun_that_knows_itself_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['sun_that_knows_itself_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','sun_that_knows_itself_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES:
        print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'sun_that_knows_itself_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()
    print('Done. Output:', out)

if __name__=='__main__': main()
