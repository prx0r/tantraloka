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
SEED = 121212

# Embodied cosmography palette
PARCHMENT = (239, 233, 220)
PARCHMENT_LIGHT = (249, 245, 236)
INK = (35, 35, 42)
UMBER = (84, 66, 52)
INDIGO = (67, 78, 128)
DEEP_INDIGO = (45, 54, 94)
GOLD = (202, 158, 75)
GOLD_LIGHT = (241, 210, 132)
COPPER = (185, 104, 65)
CRIMSON = (150, 49, 65)
ROSE = (187, 111, 136)
TEAL = (92, 142, 143)
SEA = (93, 128, 150)
GREEN = (102, 146, 105)
SLATE = (109, 118, 135)
MIST = (181, 184, 191)
PEARL = (245, 242, 232)
WHITE = (252, 250, 246)
NIGHT = (25, 27, 35)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 21)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PARCHMENT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(17))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.8 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*5,0,14)[...,None]*0.65
    bodyhalo=np.exp(-(((xx-W/2)/(W*.20))**2+((yy-H*.42)/(H*.35))**2)*2.4)
    base[...,0]+=bodyhalo*8; base[...,1]+=bodyhalo*7; base[...,2]+=bodyhalo*16
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def glow(im,xy,r,color,alpha=145,blur=16):
    ov=layer(); d=ImageDraw.Draw(ov); x,y=xy
    d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(color,alpha))
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))

def lineglow(im,pts,color,width=3,alpha=145,blur=7):
    ov=layer(); d=ImageDraw.Draw(ov)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def bezier(p0,p1,p2,p3,n=90):
    out=[]
    for i in range(n):
        t=i/(n-1);u=1-t
        out.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return out

def partial(points,a):
    a=clamp(a)
    if a<=0:return []
    if a>=1:return points
    f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points):
        A,B=points[i],points[i+1];out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out

def arrow(draw,p0,p1,col,s=1):
    a=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); z=11*s
    draw.polygon([p1,(p1[0]-math.cos(a-.5)*z,p1[1]-math.sin(a-.5)*z),(p1[0]-math.cos(a+.5)*z,p1[1]-math.sin(a+.5)*z)],fill=rgba(col,225))


def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8;x=cx+math.cos(a)*r*.62;y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)

def border(im):
    d=ImageDraw.Draw(im);d.rectangle((28,28,W-28,H-28),outline=rgba(UMBER,115),width=2);d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,85),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:rosette(d,x,y,22,ROSE,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im);y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(247,243,234,218),outline=rgba(UMBER,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK);d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2];d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=DEEP_INDIGO)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed);ov=layer();d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(110,W-110));y=float(rng.uniform(110,H-170));r=float(rng.uniform(1,2.2));c=mix(MIST,GOLD_LIGHT,rng.uniform())
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(20,70))))
    im.alpha_composite(ov)


def body_outline(d,cx=640,top=115,scale=1.0,col=INDIGO,fill=None):
    # stylized front-facing body
    head_r=28*scale
    d.ellipse((cx-head_r,top,cx+head_r,top+2*head_r),outline=rgba(col,205),fill=fill,width=max(1,int(2*scale)))
    neck_y=top+2*head_r
    pts=[(cx-18*scale,neck_y),(cx-70*scale,neck_y+48*scale),(cx-88*scale,neck_y+160*scale),(cx-48*scale,neck_y+245*scale),(cx-38*scale,neck_y+370*scale),(cx-15*scale,neck_y+370*scale),(cx-6*scale,neck_y+245*scale),(cx,neck_y+180*scale),(cx+6*scale,neck_y+245*scale),(cx+15*scale,neck_y+370*scale),(cx+38*scale,neck_y+370*scale),(cx+48*scale,neck_y+245*scale),(cx+88*scale,neck_y+160*scale),(cx+70*scale,neck_y+48*scale),(cx+18*scale,neck_y)]
    d.polygon(pts,outline=rgba(col,205),fill=fill)
    d.line((cx-70*scale,neck_y+55*scale,cx-135*scale,neck_y+210*scale),fill=rgba(col,180),width=max(1,int(2*scale)))
    d.line((cx+70*scale,neck_y+55*scale,cx+135*scale,neck_y+210*scale),fill=rgba(col,180),width=max(1,int(2*scale)))
    return neck_y

def node(d,x,y,r,col,label=None):
    d.ellipse((x-r,y-r,x+r,y+r),outline=rgba(col,220),fill=rgba(PARCHMENT_LIGHT,100),width=2)
    d.ellipse((x-r*.35,y-r*.35,x+r*.35,y+r*.35),fill=rgba(col,170))
    if label:d.text((x+r+8,y-8),label,font=TINY_FONT,fill=col)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im);cx=640;ny=body_outline(d,cx,102,1.0,INDIGO,rgba((220,225,236),28))
    # six paths as body channels
    cols=[GOLD,ROSE,TEAL,GREEN,EARTH if 'EARTH' in globals() else UMBER,INDIGO]
    xs=[-56,-34,-12,12,34,56]
    for i,(dx,col) in enumerate(zip(xs,cols)):
        pts=partial(bezier((cx+dx*.2,150),(cx+dx,235),(cx+dx*.7,385),(cx+dx*.45,520),90),smooth(.03+i*.04,.82+i*.02,t))
        if len(pts)>1:lineglow(im,pts,col,2,90,5)
    # time wheel and direction cross
    d.ellipse((cx-44,248,cx+44,336),outline=rgba(COPPER,150),width=2)
    for i in range(12):
        a=i*2*math.pi/12;d.line((cx+math.cos(a)*34,292+math.sin(a)*34,cx+math.cos(a)*43,292+math.sin(a)*43),fill=rgba(COPPER,120),width=1)
    d.line((cx-185,360,cx+185,360),fill=rgba(SLATE,95),width=1);d.line((cx,210,cx,510),fill=rgba(SLATE,95),width=1)
    # deity lamps
    for x,y,col in [(570,218,GOLD),(710,218,ROSE),(555,360,TEAL),(725,360,GREEN),(600,470,COPPER),(680,470,INDIGO)]:
        glow(im,(x,y),14,col,80,6);d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(WHITE,245),outline=rgba(col,180))
    d.text((640,522),'paths · time · space · deities · rite',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,105,.98,SLATE,rgba((230,230,235),22))
    names=['Varṇa','Mantra','Pada','Kalā','Tattva','Bhuvana'];cols=[INDIGO,ROSE,TEAL,GREEN,UMBER,GOLD]
    starts=[(520,190),(500,255),(510,330),(770,190),(790,275),(775,365)]
    ends=[(610,240),(610,315),(610,400),(670,240),(670,315),(670,400)]
    for i,(n,col,s,e) in enumerate(zip(names,cols,starts,ends)):
        p=partial(bezier(s,((s[0]+e[0])/2,s[1]-25),((s[0]+e[0])/2,e[1]+25),e,70),smooth(.05+i*.05,.82,t))
        if len(p)>1:lineglow(im,p,col,3,100,6);arrow(d,p[-2],p[-1],col,.7)
        d.text(s,n,font=SMALL_FONT,fill=col,anchor='mm')
    d.text((640,500),'the six paths are installed within the body',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,105,.98,SLATE,rgba((230,230,235),22))
    # pulse along vertical axis
    pts=[]
    for i in range(150):
        u=i/149;x=cx+math.sin(u*math.pi*8+t*.3)*26*math.sin(math.pi*u);y=160+u*350;pts.append((x,y))
    lineglow(im,pts,COPPER,4,115,7)
    for i in range(8):
        y=175+i*42;r=13+6*math.sin(t*2*math.pi+i)
        d.ellipse((cx-r,y-r*.35,cx+r,y+r*.35),outline=rgba(mix(COPPER,GOLD,i/8),145),width=2)
    d.text((820,225),'kāla',font=TERM_FONT,fill=COPPER);d.text((820,260),'pulse of time',font=SUB_FONT,fill=UMBER)
    d.text((640,510),'time is contemplated as a pulse living within embodiment',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,112,.92,INDIGO,rgba((220,225,240),20))
    # spatial compass around body
    dirs=[('E',0,GOLD),('S',math.pi/2,CRIMSON),('W',math.pi,TEAL),('N',-math.pi/2,INDIGO)]
    for lab,a,col in dirs:
        x=cx+math.cos(a)*260;y=310+math.sin(a)*185
        p=partial(bezier((cx,310),(cx+math.cos(a)*90,310+math.sin(a)*45),(cx+math.cos(a)*180,310+math.sin(a)*130),(x,y),80),smooth(.05,.85,t))
        if len(p)>1:lineglow(im,p,col,3,90,6);arrow(d,p[-2],p[-1],col,.8)
        node(d,x,y,20,col,lab)
    for r in [90,145,205]:d.ellipse((cx-r,310-r*.72,cx+r,310+r*.72),outline=rgba(SLATE,70),width=1)
    d.text((640,510),'the directions and spatial field radiate from the body-center',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,105,.98,SLATE,rgba((230,230,235),20))
    senses=[('hearing',(570,200),INDIGO),('touch',(535,300),TEAL),('sight',(640,210),GOLD),('taste',(705,300),ROSE),('smell',(670,420),GREEN)]
    for i,(lab,(x,y),col) in enumerate(senses):
        glow(im,(x,y),22,col,90,9);node(d,x,y,13,col)
        d.text((x,y+34),lab,font=TINY_FONT,fill=col,anchor='mm')
        p=partial(bezier((x,y),(x+(cx-x)*.25,y+35),(cx+(x-cx)*.15,360),(cx,390),75),smooth(.05+i*.07,.86,t))
        if len(p)>1:lineglow(im,p,col,2,78,5)
    glow(im,(cx,390),45,GOLD_LIGHT,100,14);d.ellipse((cx-18,372,cx+18,408),fill=rgba(WHITE,250),outline=rgba(GOLD,210),width=2)
    d.text((840,245),'karaṇa-devatāḥ',font=DEVA_SMALL,fill=INDIGO)
    d.text((640,510),'the sensory powers are contemplated as deities within the body',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,105,.98,SLATE,rgba((230,230,235),18))
    # ritual architecture within body
    # altar at pelvis, vessel at belly, mantra at throat, flame at heart, canopy at crown
    d.polygon([(590,470),(690,470),(670,430),(610,430)],outline=rgba(COPPER,210),fill=rgba(COPPER,40))
    d.ellipse((605,330,675,390),outline=rgba(TEAL,190),fill=rgba(TEAL,25),width=2)
    d.text((640,300),'मन्त्र',font=DEVA_SMALL,fill=INDIGO,anchor='mm')
    glow(im,(640,265),28,CRIMSON,105,10);d.polygon([(640,225),(622,270),(638,255),(650,287),(660,250)],outline=rgba(CRIMSON,210),fill=rgba(CRIMSON,45))
    d.arc((575,145,705,225),180,360,fill=rgba(GOLD,190),width=3)
    labels=[('altar',710,455,COPPER),('vessel',710,356,TEAL),('mantra',710,300,INDIGO),('inner fire',710,248,CRIMSON),('canopy',710,177,GOLD)]
    for lab,x,y,col in labels:d.text((x,y),lab,font=TINY_FONT,fill=col)
    d.text((640,510),'every component of rite is rediscovered as a bodily power',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,105,.98,SLATE,rgba((230,230,235),18))
    # offerings from world into heart fire
    inputs=[(250,190,GOLD,'form'),(210,300,TEAL,'touch'),(280,430,ROSE,'taste'),(1030,190,INDIGO,'sound'),(1070,300,GREEN,'scent'),(1000,430,COPPER,'action')]
    for i,(x,y,col,lab) in enumerate(inputs):
        d.text((x,y-25),lab,font=TINY_FONT,fill=col,anchor='mm');node(d,x,y,11,col)
        p=partial(bezier((x,y),(lerp(x,cx,.35),y),(lerp(x,cx,.75),350),(cx,330),80),smooth(.03+i*.04,.84,t))
        if len(p)>1:lineglow(im,p,col,2,82,5);arrow(d,p[-2],p[-1],col,.65)
    glow(im,(cx,330),52,CRIMSON,120,16)
    d.polygon([(640,275),(618,330),(634,315),(646,360),(666,312)],outline=rgba(CRIMSON,220),fill=rgba(CRIMSON,55))
    d.text((640,510),'experience itself becomes libation into the inner fire of awareness',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im);left,right=400,880;cy=300
    body_outline(d,left,120,.72,INDIGO,rgba((220,225,240),20))
    # cosmos on right
    for r,col in [(190,GOLD),(145,TEAL),(100,ROSE),(55,INDIGO)]:d.ellipse((right-r,cy-r*.72,right+r,cy+r*.72),outline=rgba(col,125),width=2)
    for i in range(12):
        a=i*2*math.pi/12;x=right+math.cos(a)*180;y=cy+math.sin(a)*130;d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,INDIGO,i/12),180))
    # mirrored fusion
    p1=partial(bezier((500,300),(610,230),(670,230),(780,300),90),smooth(.05,.86,t))
    p2=partial(bezier((500,340),(610,410),(670,410),(780,340),90),smooth(.05,.86,t))
    if len(p1)>1:lineglow(im,p1,GOLD,3,100,6)
    if len(p2)>1:lineglow(im,p2,INDIGO,3,100,6)
    glow(im,(640,320),40,WHITE,95,12);d.text((640,320),'=',font=TERM_FONT,fill=UMBER,anchor='mm')
    d.text((640,510),'abhedabhāvanā: body and cosmos are contemplated without division',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im);cx,cy=640,300
    # multiple forms around equality grid
    forms=[('human',GOLD),('animal',TEAL),('stone',UMBER),('deity',ROSE),('thought',INDIGO),('ritual',COPPER),('world',GREEN),('void',SLATE)]
    for i,(lab,col) in enumerate(forms):
        a=-math.pi/2+i*2*math.pi/8;x=cx+math.cos(a)*250;y=cy+math.sin(a)*160
        d.rounded_rectangle((x-42,y-24,x+42,y+24),radius=12,outline=rgba(col,180),fill=rgba(PARCHMENT_LIGHT,70),width=2)
        d.text((x,y),lab,font=TINY_FONT,fill=col,anchor='mm')
        p=partial(bezier((x,y),(lerp(x,cx,.4),y),(lerp(x,cx,.7),cy),(cx,cy),70),smooth(.04+i*.035,.84,t))
        if len(p)>1:lineglow(im,p,col,2,70,5)
    glow(im,(cx,cy),55,GOLD_LIGHT,115,15);d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(WHITE,250),outline=rgba(GOLD,210),width=2)
    # equality grid
    for x in np.linspace(300,980,7):d.line((x,145,x,455),fill=rgba(SLATE,35),width=1)
    for y in np.linspace(150,450,5):d.line((300,y,980,y),fill=rgba(SLATE,35),width=1)
    d.text((640,510),'the pure vow: every appearance is met as an equal form of consciousness',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im);cx=640;body_outline(d,cx,112,.88,INDIGO,rgba((230,230,240),18))
    # outer mandala
    for r,col in [(230,GOLD),(195,TEAL),(160,ROSE),(126,INDIGO)]:d.ellipse((cx-r,310-r*.72,cx+r,310+r*.72),outline=rgba(col,130),width=2)
    # six path petals
    for i,(lab,col) in enumerate([('Varṇa',INDIGO),('Mantra',ROSE),('Pada',TEAL),('Kalā',GREEN),('Tattva',UMBER),('Bhuvana',GOLD)]):
        a=-math.pi/2+i*2*math.pi/6;x=cx+math.cos(a)*190;y=310+math.sin(a)*136
        d.ellipse((x-29,y-20,x+29,y+20),outline=rgba(col,185),fill=rgba(PARCHMENT_LIGHT,85),width=2);d.text((x,y),lab,font=TINY_FONT,fill=col,anchor='mm')
    # time wheel, directions and deity lights
    d.ellipse((cx-56,254,cx+56,366),outline=rgba(COPPER,160),width=2)
    for i in range(12):
        a=i*2*math.pi/12;d.line((cx+math.cos(a)*46,310+math.sin(a)*46,cx+math.cos(a)*55,310+math.sin(a)*55),fill=rgba(COPPER,110),width=1)
    for x,y,col in [(600,245,GOLD),(680,245,ROSE),(590,375,TEAL),(690,375,GREEN)]:glow(im,(x,y),12,col,80,5);d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,250))
    glow(im,(cx,310),40,GOLD_LIGHT,105,13);d.ellipse((cx-16,294,cx+16,326),fill=rgba(WHITE,250),outline=rgba(GOLD,210),width=2)
    d.text((640,510),'the body-mandala closes around one undivided field of consciousness',font=SUB_FONT,fill=UMBER,anchor='mm')

SCENES=[
Scene('cb01','The Cosmic Body','Paths, time, space, deities, and ritual inhabit one embodied field.','Viśva-deha','Overview of the body as a complete cosmological field.','overview',['body','cosmos','overview'],'overview','body map with paths and deities',sc01),
Scene('cb02','The Paths Within the Body','The six paths are installed through embodied coordinates.','Adhva-deha','Speech and world paths are mapped into bodily structure.','paths_body',['six paths','body'],'structure','six channels in body',sc02),
Scene('cb03','The Pulse of Time','Kāla is contemplated as an embodied pulse.','Kāla-spanda','Time lives as rhythmic dynamism within the body.','time_pulse',['time','pulse','body'],'structure','spinal time waveform',sc03),
Scene('cb04','Space and the Directions','The body-center radiates the spatial field.','Deśa-dik','Directions and spatial extension unfold from embodiment.','directions_body',['space','directions'],'structure','compass body field',sc04),
Scene('cb05','The Deities of the Senses','Each sensory power is contemplated as a deity.','Karaṇa-devatā','The faculties of perception become divine gateways.','sense_deities',['senses','deities'],'deities','sense lamps feeding heart',sc05),
Scene('cb06','The Rite Within the Body','Every ritual implement is rediscovered as an embodied power.','Antaryāga','Altar, vessel, mantra, fire, and canopy are internalized.','inner_rite',['rite','body','inner worship'],'ritual','ritual architecture in body',sc06),
Scene('cb07','Experience as Offering','The sensory world becomes libation into awareness.','Āhuti','All experience is offered into the inner fire.','inner_offering',['offering','inner fire'],'ritual','six offerings into heart fire',sc07),
Scene('cb08','Contemplation of Nonduality','Body and cosmos are contemplated without division.','Abhedabhāvanā','The embodied and cosmic fields mirror one another as one.','nondual_mirror',['nonduality','body','cosmos'],'contemplation','body-cosmos mirror fusion',sc08),
Scene('cb09','The Pure Vow of Equality','Every appearance is met as an equal form of consciousness.','Sāmya-vrata','Difference remains visible without becoming ontological division.','equality_vow',['equality','vow','nonduality'],'contemplation','forms converging through equality grid',sc09),
Scene('cb10','The Cosmic Body Seal','The complete embodied cosmology gathers into one body-mandala.','Deha-maṇḍala','The body becomes the closing seal of paths, time, space, deities, and rite.','closing_seal',['seal','body mandala'],'seal','cosmic body mandala',sc10),
]


def render_scene(sc):
    sdir=FRAMES_ROOT/sc.id;sdir.mkdir(parents=True,exist_ok=True)
    frames=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1);im=ground(SEED+(hash(sc.id)%10000)+i);border(im);dust(im,SEED+i,45);sc.draw_fn(im,t);footer(im,sc.title,sc.subtitle,sc.term);im.convert('RGB').save(p,quality=94)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg';thumbs.append(Image.open(p).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,540),PARCHMENT)
    for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — The Cosmic Body','source_basis':'Tantrāloka Chapter 12 overview: the body contains the Paths, the pulse of Time and Space, all deities, and every component of rite; inner offering and the pure vow of equality.','style':{'family':'embodied cosmographic cartography','background':'warm parchment with translucent skin-field','accent':'gold nerve filaments, indigo spatial glass, copper time pulse, pearl deity lamps, crimson inner fire','materials':['translucent skin parchment','gold filaments','spatial glass','deity lamps','inner-fire lacquer']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['cb01'],'embodied_structure':['cb02','cb03','cb04'],'deities_and_rite':['cb05','cb06','cb07'],'nondual_contemplation':['cb08','cb09'],'seal':['cb10']},'reusability_notes':{'cb01':'Use for the whole cosmic-body doctrine.','cb02':'Use for mapping the six paths into embodiment.','cb03':'Use for embodied time or pulse.','cb04':'Use for directions and spatial extension.','cb05':'Use for sense-deities or divine faculties.','cb06':'Use for internalized ritual architecture.','cb07':'Use for inner offering and sensory libation.','cb08':'Use for body-cosmos nonduality.','cb09':'Use for equality contemplation.','cb10':'Use as the closing body-mandala seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The Cosmic Body

## Aim
This pack visualizes the Chapter 12 teaching that the body is a complete cosmological and ritual field.

## Source-derived structure
- The Paths are present within the parts of the body and within the components of ritual.
- Nonduality is cultivated through **abhedabhāvanā**.
- The body contains the Paths, the pulse of Time and Space, and all the deities.
- The body and every component of the rite are full of all things and deities.
- Offering to these internal powers constitutes inner worship, meditation, and libation.
- The sequence culminates in the pure vow of equality.

## Visual rules
- Do not treat the body as a merely anatomical container.
- Do not depict the cosmos as externally inserted into a passive body.
- Body, path, deity, time, space, and rite should be mutually homologous.
- Inner worship should look like re-reading experience as offering, not rejecting the senses.
- Equality should preserve visible difference while removing ontological hierarchy.

## New motifs
- six-path body channels
- spinal time pulse
- directional body-compass
- sensory deity lamps
- internal ritual architecture
- experiential offerings into heart-fire
- body-cosmos mirror bridge
- equality lattice
- cosmic-body closing mandala

## Reuse strategy
- cb01–cb04: body as path/time/space architecture
- cb05–cb07: deity and rite within embodiment
- cb08–cb09: nondual contemplation and equality
- cb10: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Cosmic Body Pack

## Differentiation
This pack moves beyond abstract diagrams into embodied cartography. The body is translucent cosmographic parchment rather than medical anatomy.

## New symbols
1. six colored path channels in the body
2. spinal wheel-pulse of time
3. compass field radiating from the torso
4. sensory deity lamps
5. altar/vessel/mantra/fire/canopy inside the body
6. offerings converging into heart-fire
7. body-cosmos mirror bridge
8. equality lattice
9. body-maṇḍala seal

## New relationships
- Paths ↔ body parts
- Time ↔ pulse
- Space ↔ directions
- Senses ↔ deities
- Ritual implements ↔ embodied powers
- Experience ↔ offering
- Body ↔ cosmos
- Equality ↔ nondual perception

## New material vocabulary
- translucent skin parchment
- gold nerve filaments
- indigo spatial glass
- copper pulse rings
- pearl deity lamps
- crimson inner-fire lacquer

## Closing seal
The closing seal is a full **deha-maṇḍala**: the body surrounded by the six Paths, time-wheel, direction field, and deity lamps.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — The Cosmic Body Pack

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
    p=ROOT/'cosmic_body_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'cosmic_body_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['cosmic_body_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')):zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True);SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES:print('Rendering',s.id,s.title,flush=True);render_scene(s)
    lst=ROOT/'concat_list.txt';lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'cosmic_body_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet();metadata();validate();make_zip()

if __name__=='__main__':main()
