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
SEED = 141414

# Black lacquer / crystal / copper palette
NIGHT = (18, 21, 29)
GRAPHITE = (31, 37, 50)
SLATE = (91, 104, 126)
MIST = (171, 181, 199)
SILVER = (220, 225, 235)
PEARL = (245, 243, 239)
WHITE = (252, 250, 246)
GOLD = (205, 164, 83)
GOLD_LIGHT = (245, 215, 137)
ELECTRIC = (236, 188, 74)
VIOLET = (126, 104, 170)
LAVENDER = (174, 154, 205)
INDIGO = (67, 79, 137)
TEAL = (89, 148, 151)
COPPER = (188, 107, 69)
CORAL = (205, 100, 91)
ROSE = (190, 112, 141)
GREEN = (105, 153, 115)
BLACK = (12, 13, 16)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 27)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t):
    t=clamp(t); return .5-.5*math.cos(math.pi*t)
def ease_out_cubic(t):
    t=clamp(t); return 1-(1-t)**3
def smoothstep(a,b,x):
    if a==b:return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3],int(a))


def ground(seed:int):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(17))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.1 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*20,0,27)[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.34))**2+((yy-H*.40)/(H*.27))**2)*2.6)
    for i in range(3): base[...,i]+=halo*(14 if i==2 else 6)
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))
def draw_glow(im,xy,radius,color,alpha=150,blur=16):
    gl=layer(); d=ImageDraw.Draw(gl); x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
def draw_line_glow(im,pts,color,width=3,alpha=150,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,140),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(MIST,110),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,88),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,VIOLET,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((88,y0,W-88,H-34),radius=14,fill=(17,20,28,204),outline=rgba(MIST,66),width=1)
    d.text((120,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((122,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-116-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def partial_polyline(points,amount):
    amount=clamp(amount)
    if amount<=0:return []
    if amount>=1:return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx; out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    draw.polygon([p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)],fill=rgba(color,230))
def dust(im,seed,n=64):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(100,W-100)); y=float(rng.uniform(90,H-170)); r=float(rng.uniform(.8,2.3)); c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(22,76))))
    im.alpha_composite(ov)

def draw_eye(draw,cx,cy,scale=1.0,col=GOLD_LIGHT):
    draw.arc((cx-66*scale,cy-30*scale,cx+66*scale,cy+30*scale),180,360,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.arc((cx-66*scale,cy-30*scale,cx+66*scale,cy+30*scale),0,180,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.ellipse((cx-14*scale,cy-14*scale,cx+14*scale,cy+14*scale),fill=rgba(WHITE,235))

def draw_crystal(draw,box,col,alpha=65):
    x0,y0,x1,y1=box
    pts=[(x0+18,y0),(x1-18,y0),(x1,y0+18),(x1-18,y1),(x0+18,y1),(x0,y1-18)]
    draw.polygon(pts,outline=rgba(col,190),fill=rgba(mix(GRAPHITE,col,.20),alpha))
    draw.line((x0+18,y0,x1-18,y1),fill=rgba(mix(col,WHITE,.5),70),width=1)

def draw_breath_wave(im,x0,x1,y,amp,phase,col,progress=1.0):
    pts=[]
    for i in range(100):
        u=i/99; x=lerp(x0,x1,u); yy=y+math.sin(u*math.pi*4+phase)*amp
        pts.append((x,yy))
    pts=partial_polyline(pts,progress)
    if len(pts)>1:draw_line_glow(im,pts,col,3,100,6)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    draw_glow(im,(cx,cy),58,GOLD_LIGHT,120,16); draw_eye(d,cx,cy,.72,GOLD_LIGHT)
    gates=[('Anupāya',WHITE,-math.pi/2),('Śāmbhava',ELECTRIC,0),('Śākta',VIOLET,math.pi/2),('Āṇava',COPPER,math.pi)]
    for i,(lab,col,a) in enumerate(gates):
        x=cx+math.cos(a)*240; y=cy+math.sin(a)*150
        if i==0:
            d.arc((x-52,y-40,x+52,y+40),195,345,fill=rgba(col,220),width=3)
        elif i==1:
            d.polygon([(x-16,y-55),(x+12,y-12),(x-4,y-8),(x+20,y+48),(x-18,y+4),(x-2,y)],fill=rgba(col,210))
        elif i==2:
            draw_crystal(d,(x-52,y-40,x+52,y+40),col,55)
        else:
            d.rounded_rectangle((x-48,y-40,x+48,y+40),radius=14,outline=rgba(col,210),width=2)
            for k in range(3): d.line((x-30+k*30,y-25,x-30+k*30,y+25),fill=rgba(col,100),width=2)
        d.text((x,y+68),lab,font=SMALL_FONT,fill=col,anchor='mm')
        pts=partial_polyline(bezier((x,y),(lerp(x,cx,.35),lerp(y,cy,.35)),(lerp(x,cx,.7),lerp(y,cy,.7)),(cx,cy),80),smoothstep(.03+i*.05,.82,t))
        if len(pts)>1:draw_line_glow(im,pts,col,3,105,6)
    d.text((640,505),'four degrees of support converging on one recognition',font=SUB_FONT,fill=MIST,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    for r in [190,145,100,58]:
        a=int(125*(1-ease_in_out(t)))
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(SILVER,a),width=2)
    draw_glow(im,(cx,cy),86,WHITE,145,24)
    d.ellipse((cx-26,cy-26,cx+26,cy+26),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    d.text((640,188),'no apparatus · no interval',font=TERM_FONT,fill=WHITE,anchor='mm')
    d.text((640,505),'in the no-means, recognition is not produced by a path',font=SUB_FONT,fill=MIST,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    start=(270,390); end=(cx,cy)
    bolt=[start,(380,330),(420,350),(500,250),(548,292),end]
    pts=partial_polyline(bolt,ease_out_cubic(t))
    if len(pts)>1:draw_line_glow(im,pts,ELECTRIC,5,150,9)
    draw_glow(im,(cx,cy),52,GOLD_LIGHT,125,15); draw_eye(d,cx,cy,.55,GOLD_LIGHT)
    d.text((315,220),'icchā',font=TERM_FONT,fill=ELECTRIC,anchor='mm')
    d.text((315,248),'a single act of will',font=SMALL_FONT,fill=MIST,anchor='mm')
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5; x=cx+math.cos(a)*150; y=cy+math.sin(a)*90
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(ELECTRIC,170))
    d.text((640,505),'the supreme means enters through a nonconceptual impulse of will',font=SUB_FONT,fill=MIST,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im)
    boxes=[(150,230,310,328),(380,214,550,344),(620,198,800,360),(875,180,1070,378)]
    words=['coarse vikalpa','refined thought','transparent mantra','self-recognition']
    cols=[SLATE,VIOLET,LAVENDER,GOLD_LIGHT]
    for i,(box,word,col) in enumerate(zip(boxes,words,cols)):
        draw_crystal(d,box,col,70-i*8)
        d.text(((box[0]+box[2])/2,box[3]+30),word,font=SMALL_FONT,fill=col,anchor='mm')
        if i<3:
            p0=(box[2],(box[1]+box[3])/2); p1=(boxes[i+1][0],(boxes[i+1][1]+boxes[i+1][3])/2)
            pts=partial_polyline(bezier(p0,(p0[0]+35,p0[1]-20),(p1[0]-35,p1[1]+20),p1,70),smoothstep(.05+i*.14,.78+i*.07,t))
            if len(pts)>1:draw_line_glow(im,pts,mix(col,cols[i+1],.5),3,105,6)
    d.text((640,505),'the empowered means purifies thought until thought discloses its source',font=SUB_FONT,fill=MIST,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx=640
    # body-breath-mantra instrument
    d.ellipse((cx-32,125,cx+32,189),outline=rgba(COPPER,200),width=2)
    d.line((cx,190,cx,430),fill=rgba(COPPER,180),width=4)
    for y,col,lab in [(220,COPPER,'body'),(290,TEAL,'breath'),(360,VIOLET,'mantra'),(430,GOLD,'attention')]:
        d.ellipse((cx-38,y-18,cx+38,y+18),outline=rgba(col,200),fill=rgba(mix(GRAPHITE,col,.18),60),width=2)
        d.text((cx+105,y),lab,font=SMALL_FONT,fill=col,anchor='lm')
    draw_breath_wave(im,320,960,290,26,t*math.pi*2,TEAL,ease_out_cubic(t))
    for i,ch in enumerate(['हं','सः','ॐ']):
        d.text((520+i*120,360),ch,font=DEVA_MED,fill=VIOLET,anchor='mm')
    draw_glow(im,(cx,430),34,GOLD_LIGHT,105,12)
    d.text((640,505),'the individual means coordinates body, breath, sound, and deliberate attention',font=SUB_FONT,fill=MIST,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im)
    labels=['asphuṭa','sphuṭatā-bhāvin','prasphuṭa','sphuṭitātmaka']
    cols=[SLATE,VIOLET,LAVENDER,GOLD_LIGHT]
    for i,(lab,col) in enumerate(zip(labels,cols)):
        x=230+i*275; r=62-i*6
        alpha=65+i*35
        d.ellipse((x-r,280-r,x+r,280+r),outline=rgba(col,200),fill=rgba(mix(GRAPHITE,col,.16),alpha),width=2)
        for k in range(max(1,4-i)):
            off=(k-(3-i)/2)*12
            d.line((x-r*.6,280+off,x+r*.6,280-off),fill=rgba(col,60+i*30),width=2)
        d.text((x,375),lab,font=SMALL_FONT,fill=col,anchor='mm')
        if i<3:
            p0=(x+r,280); p1=(230+(i+1)*275-(r-6),280)
            pts=partial_polyline(bezier(p0,(p0[0]+38,245),(p1[0]-38,315),p1,70),smoothstep(.05+i*.12,.8+i*.06,t))
            if len(pts)>1:draw_line_glow(im,pts,mix(col,cols[i+1],.5),3,95,5)
    d.text((640,505),'repeated refinement makes thought progressively lucid and nondual',font=SUB_FONT,fill=MIST,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im)
    bays=[('no support',WHITE,150,400,1),('will',ELECTRIC,400,350,2),('thought',VIOLET,650,300,3),('body · breath',COPPER,900,250,4)]
    for lab,col,x,y,n in bays:
        h=430-y
        if n==1:
            d.arc((x-70,y-55,x+70,y+55),195,345,fill=rgba(col,220),width=3)
        else:
            d.rounded_rectangle((x-70,y,x+70,430),radius=16,outline=rgba(col,185),fill=rgba(mix(GRAPHITE,col,.10),48),width=2)
            for k in range(n-1):
                yy=lerp(y+25,410,(k+1)/n); d.line((x-50,yy,x+50,yy),fill=rgba(col,100),width=2)
        d.text((x,465),lab,font=SMALL_FONT,fill=col,anchor='mm')
    draw_line_glow(im,[(150,190),(900,190)],GOLD_LIGHT,2,70,5)
    d.text((640,155),'increasing density of support',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the distinction concerns mediation, not four different goals',font=SUB_FONT,fill=MIST,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,275
    # shared lotus/object
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8; x=cx+math.cos(a)*55; y=cy+math.sin(a)*35
        d.ellipse((x-22,y-12,x+22,y+12),outline=rgba(ROSE,170),fill=rgba(ROSE,35),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(GOLD_LIGHT,210))
    routes=[('identity',WHITE,(230,150)),('will',ELECTRIC,(1050,150)),('thought',VIOLET,(1050,420)),('breath/body',COPPER,(230,420))]
    for i,(lab,col,start) in enumerate(routes):
        p=partial_polyline(bezier(start,(lerp(start[0],cx,.35),start[1]),(lerp(start[0],cx,.7),cy),(cx,cy),85),smoothstep(.04+i*.04,.85,t))
        if len(p)>1:draw_line_glow(im,p,col,3,100,6)
        d.text(start,lab,font=SMALL_FONT,fill=col,anchor='mm')
    d.text((640,505),'one perception can be entered at four different resolutions of support',font=SUB_FONT,fill=MIST,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im)
    # one grace beam, four receiver architectures
    draw_glow(im,(640,105),34,GOLD_LIGHT,125,12)
    d.ellipse((626,91,654,119),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    xs=[210,500,780,1070]; labs=['Anupāya','Śāmbhava','Śākta','Āṇava']; cols=[WHITE,ELECTRIC,VIOLET,COPPER]
    for i,(x,lab,col) in enumerate(zip(xs,labs,cols)):
        pts=partial_polyline(bezier((640,120),(640+(x-640)*.2,190),(x,220),(x,265),80),smoothstep(.03+i*.05,.82,t))
        if len(pts)>1:draw_line_glow(im,pts,col,3,100,6)
        if i==0:d.arc((x-50,255,x+50,325),195,345,fill=rgba(col,220),width=3)
        elif i==1:d.polygon([(x,245),(x+18,282),(x+4,282),(x+18,322),(x-18,284),(x-4,284)],fill=rgba(col,210))
        elif i==2:draw_crystal(d,(x-50,250,x+50,330),col,60)
        else:
            d.rounded_rectangle((x-50,250,x+50,330),radius=14,outline=rgba(col,210),width=2)
            d.line((x,258,x,322),fill=rgba(col,100),width=2)
        d.text((x,365),lab,font=SMALL_FONT,fill=col,anchor='mm')
    d.text((640,505),'one grace is received through different capacities for directness and support',font=SUB_FONT,fill=MIST,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,278
    # diamond gate seal
    pts=[(cx,105),(825,cy),(cx,451),(455,cy)]
    d.polygon(pts,outline=rgba(SILVER,150),fill=rgba(GRAPHITE,50))
    gate_data=[((cx,105),WHITE,'Anupāya'),((825,cy),ELECTRIC,'Śāmbhava'),((cx,451),VIOLET,'Śākta'),((455,cy),COPPER,'Āṇava')]
    for i,(p,col,lab) in enumerate(gate_data):
        x,y=p; draw_glow(im,(x,y),22,col,90,9)
        d.ellipse((x-11,y-11,x+11,y+11),fill=rgba(WHITE,240),outline=rgba(col,220),width=2)
        tx=x+(0 if i in [0,2] else (74 if i==1 else -74)); ty=y+(-32 if i==0 else 32 if i==2 else 0)
        d.text((tx,ty),lab,font=TINY_FONT,fill=col,anchor='mm')
        path=partial_polyline(bezier((x,y),(lerp(x,cx,.35),lerp(y,cy,.35)),(lerp(x,cx,.7),lerp(y,cy,.7)),(cx,cy),70),smoothstep(.05+i*.05,.8,t))
        if len(path)>1:draw_line_glow(im,path,col,3,105,6)
    draw_glow(im,(cx,cy),66,GOLD_LIGHT,135,18); draw_eye(d,cx,cy,.62,GOLD_LIGHT)
    d.text((640,505),'four gates, one Bhairava field',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
    Scene('up01','The Four Upāyas','Four degrees of mediation converging on one recognition.','Upāya-catuṣṭaya','The four modes differ by their density of support, not by their final ground.','overview_gates',['overview','upaya','four modes'],'overview','four distinct gates around one eye',sc01),
    Scene('up02','Anupāya','Direct realization without a produced method.','Anupāya','No apparatus intervenes between awareness and its own recognition.','no_means_field',['anupaya','direct','no means'],'mode','dissolving rings and open field',sc02),
    Scene('up03','Śāmbhavopāya','The supreme means: entry through a nonconceptual act of will.','Śāmbhavopāya','A minimal impulse of icchā enters directly into the supreme state.','will_lightning',['shambhava','will','iccha'],'mode','lightning will-vector',sc03),
    Scene('up04','Śāktopāya','The empowered means: thought refined until it becomes transparent.','Śāktopāya','Vikalpa is not merely suppressed; it is purified into recognition.','thought_prisms',['shakta','vikalpa','thought'],'mode','four thought-prisms',sc04),
    Scene('up05','Āṇavopāya','The individual means: body, breath, sound, and attention.','Āṇavopāya','Embodied supports are coordinated as an instrument of entry.','somatic_instrument',['anava','body','breath','mantra'],'mode','body-breath-mantra instrument',sc05),
    Scene('up06','Vikalpa-saṃskāra','Conceptuality becomes progressively clearer and more self-aware.','Vikalpa-saṃskāra','Repeated refinement moves thought from indistinct to fully lucid.','concept_refinement',['vikalpa','refinement','chapter 4'],'process','four clarity stages',sc06),
    Scene('up07','The Density of Support','From no apparatus to embodied and respiratory supports.','Ālambana','The four modes differ in how much structure mediates recognition.','support_density',['support','mediation','comparison'],'comparison','four architectural support bays',sc07),
    Scene('up08','One Perception, Four Entrances','The same appearing object can be entered at four resolutions.','Praveśa','Identity, will, thought, and embodiment converge on one field.','four_entrances',['perception','comparison','entry'],'comparison','lotus with four approach routes',sc08),
    Scene('up09','Grace and Capacity','One descent of grace meets different capacities for directness.','Śaktipāta–Upāya','The modes correspond to varying requirements for mediation and support.','grace_receivers',['grace','capacity','upaya'],'relation','one beam and four receiver architectures',sc09),
    Scene('up10','The Four-Gate Seal','The four modes resolve into one Bhairava center.','Upāya-cakra','The complete system closes as four gates around one awareness-field.','closing_seal',['seal','bhairava','summary'],'seal','diamond four-gate cosmogram',sc10),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000:continue
            t=i/max(1,NFRAMES-1); im=ground(SEED+hash(scene.id)%10000+i); border(im); dust(im,SEED+i,58); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'; thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(4*320,3*180),color=NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={
        'project':'Tantrāloka — The Four Upāyas (Modes of Realization)',
        'source_basis':'Tantrāloka Chapters 2–5: anupāya, śāmbhavopāya, śāktopāya, and āṇavopāya.',
        'style':{'family':'black lacquer, crystal mediation, copper somatics','background':'graphite-black contemplative field','ink':'silver / pearl','accent':'white, electric gold, violet glass, copper-teal','materials':['open field','lightning will','thought prisms','somatic instrument','diamond gate seal']},
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['up01'],'four_modes':['up02','up03','up04','up05'],'comparative_processes':['up06','up07','up08','up09'],'seal':['up10']},'reusability_notes':{
        'up01':'Use for the overall four-upāya system.','up02':'Use for direct recognition, no-method, immediacy, or apparatus-free awareness.','up03':'Use for will, nonconceptual impulse, lightning recognition, or Śāmbhava entry.','up04':'Use for vikalpa refinement, mantra-cognition, or thought becoming transparent.','up05':'Use for body, breath, mantra, visualization, and deliberate practice.','up06':'Use for progressive clarification of conceptual thought.','up07':'Use to compare support density across methods.','up08':'Use to show one phenomenon approached through four modes.','up09':'Use for the relation between grace, capacity, and mediation.','up10':'Use as the closing seal for the full upāya system.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The Four Upāyas

## Aim
This pack visualizes the four modes of realization associated with Tantrāloka Chapters 2–5.

## Textual orientation
- Chapter 2: **Anupāya**, direct realization with no operative method.
- Chapter 3: **Śāmbhavopāya**, the supreme means, involving extremely subtle or nonconceptual entry.
- Chapter 4: **Śāktopāya**, the empowered means, including purification and empowerment of thought (vikalpa-saṃskāra) and sound reasoning.
- Chapter 5: **Āṇavopāya**, the individual means, including intellectual meditation, vital breath, utterance, voids, locations, and phonemic practice.

## Visual rules
- Do not depict the four modes as four unrelated religions or goals.
- Anupāya is technically “no means”; the open field must look apparatus-free.
- Śāmbhavopāya should use one minimal impulse rather than elaborate machinery.
- Śāktopāya should transform thought instead of simply erasing it.
- Āṇavopāya should look embodied and structured, but not spiritually inferior in moral worth.
- The comparison scenes should emphasize different degrees of mediation and support.

## Style family
- black lacquer field
- pearl-white immediacy for Anupāya
- electric gold for Śāmbhava will
- violet crystal for Śākta cognition
- copper / teal somatic architecture for Āṇava

## New motifs introduced
- apparatus-free open field
- will-lightning
- thought-prism refinement
- body-breath-mantra instrument
- four-stage vikalpa clarity sequence
- support-density architecture
- one perception / four entrances
- one grace / four receivers
- diamond four-gate seal

## Guardrails
- Avoid the simplistic equation “higher = good, lower = bad.”
- Do not claim that a practitioner arbitrarily chooses a mode as a consumer preference; capacity and grace condition the needed supports.
- Do not reduce Āṇavopāya to posture or breathing alone.
- Do not reduce Śāktopāya to ordinary intellectual analysis.

## Reuse strategy
- up01: overview
- up02–up05: the four modes
- up06–up09: conceptual and comparative scenes
- up10: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Four Upāyas Pack

## Differentiation
This pack shifts from grace-rain and cosmological shells into a language of **mediation architecture**.

## New symbols
1. open no-gate field
2. lightning of will
3. violet thought-prisms
4. copper somatic instrument
5. progressive clarity lenses
6. four support bays
7. four-entry lotus
8. four receiver architectures
9. diamond Bhairava seal

## New relationships
- no interval → direct identity
- will → immediate entry
- thought → self-purification
- body/breath/mantra → structured entry
- grace → receiver capacity
- increasing support → same final awareness

## Material vocabulary
- black lacquer
- pearl void-light
- electric gold
- violet crystal glass
- copper somatic mechanisms
- teal breath-wave

## Distinct closing seal
A diamond with four materially distinct gates converging on one central Bhairava eye.

## Next pack
AHAṂ and the Fifty Powers of Reflection.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — The Four Upāyas Pack

Included files:
- four_upayas_animation.mp4
- contact_sheet.jpg
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- STYLE_EVOLUTION.md
- render_pack.py
- README.md
- validation.json
- scenes/*.mp4

Specs:
- Resolution: {W}x{H}
- FPS: {FPS}
- Scene count: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total runtime: {len(SCENES)*DURATION/60:.2f} min

Render:
```bash
python render_pack.py
```
The script is resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'four_upayas_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'four_upayas_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['four_upayas_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat_file=ROOT/'concat_list.txt'; concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    combined=ROOT/'four_upayas_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':render_all()
