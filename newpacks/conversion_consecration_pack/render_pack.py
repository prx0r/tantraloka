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
SEED = 51405

BRONZE = (185, 120, 70)
BRONZE_DARK = (140, 85, 45)
BRONZE_LIGHT = (220, 170, 120)
EMBER = (200, 90, 50)
EMBER_LIGHT = (235, 170, 100)
EMBER_DARK = (150, 60, 30)
EMBER_LIGHT = (235, 170, 100)
INK = (35, 30, 35)
INK_LIGHT = (85, 75, 80)
PARCHMENT = (245, 240, 230)
PARCHMENT_DARK = (220, 212, 200)
TRANSMISSION = (180, 155, 110)
WHITE = (252, 251, 248)
BLACK = (18, 20, 25)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_BIG=ImageFont.truetype(FONT_DEVA,48)
DEVA_MED=ImageFont.truetype(FONT_DEVA,28)
DEVA_SMALL=ImageFont.truetype(FONT_DEVA,19)
DEVA_BIG = ImageFont.truetype(FONT_DEVA, 48)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 19)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): return 0.5 - 0.5*math.cos(math.pi*clamp(t))
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)

def rgba(c,a=255): return (*c[:3], int(a))


def base_image(seed: int):
    rng=np.random.default_rng(seed)
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(PARCHMENT,dtype=np.float32)
    noise=rng.normal(0,1,(H,W)).astype(np.float32)
    arr += noise[...,None]*0.9
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    arr -= np.clip((dx*dx+dy*dy)*7,0,14)[...,None]*0.6
    halo=np.exp(-(((xx-W/2)/(W*.29))**2 + ((yy-H*.34)/(H*.20))**2)*2.8)
    for i in range(3): arr[...,i] += halo*(8 if i<2 else 18)
    return Image.fromarray(np.uint8(np.clip(arr,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def glow(im,xy,r,color,alpha=145,blur=16):
    ov=layer(); d=ImageDraw.Draw(ov); x,y=xy
    d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(color,alpha))
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))

def line_glow(im,pts,color,width=3,alpha=145,blur=8):
    ov=layer(); d=ImageDraw.Draw(ov)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def bezier(p0,p1,p2,p3,n=100):
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
        p,b=points[i],points[i+1]; out.append((lerp(p[0],b[0],q),lerp(p[1],b[1],q)))
    return out

def arrow(draw,p0,p1,col,s=1.0):
    a=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); z=11*s
    draw.polygon([p1,(p1[0]-math.cos(a-.5)*z,p1[1]-math.sin(a-.5)*z),(p1[0]-math.cos(a+.5)*z,p1[1]-math.sin(a+.5)*z)],fill=rgba(col,230))


def rosette(draw,cx,cy,r):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(TRANSMISSION,140),outline=rgba(BRONZE,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(BRONZE_LIGHT,110),outline=rgba(INK,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(EMBER,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(INK,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(BRONZE,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(243,238,228,220),outline=rgba(INK,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=INK_LIGHT)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=BRONZE_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),70,BRONZE_LIGHT,110,16)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(BRONZE,150),width=3)
    d.ellipse((cx-195,cy-135,cx+195,cy+135),outline=rgba(EMBER,90),width=1)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(TRANSMISSION,120),width=2)
    d.text((cx,cy),'संक्रान्ति',font=DEVA_SMALL,fill=INK,anchor='mm')
    d.text((640,505),'Crossing traditions: conversion brings the aspirant into the Śaiva fold',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,BRONZE_LIGHT,105,14)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        r=lerp(20,200,smooth(.05+.1*i,.84,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(EMBER,BRONZE,i/7),160),outline=rgba(BRONZE_DARK,130),width=1)
    d.text((cx,cy-5),'मन्त्र',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'Seven common mantras are given to the convert as the foundation of new practice',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(EMBER,160),width=2)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.8,t)>i*0.08:
            d.line(((cx,cy),(x,y)),fill=rgba(BRONZE,140),width=3)
    glow(im,(cx,cy-10),35,EMBER_LIGHT,100,12)
    d.text((cx,cy),'अग्नि',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'Fire and purification: the element of transformation in conversion rites',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,BRONZE_LIGHT,115,16)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*190; y=cy+math.sin(a)*190*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*50,cy+math.sin(a)*50-20),(x-20,y+20),(x,y),40),smooth(.04,.82,t))
        if len(pts)>1: line_glow(im,pts,mix(BRONZE,EMBER,i/10),2,85,6)
    d.text((cx,cy-10),'आचार्य',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'Who can teach: the qualifications and lineage necessary for true transmission',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-210,cy-150,cx+210,cy+150),outline=rgba(BRONZE,170),width=3)
    for i in range(12):
        a=i*2*math.pi/12
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*140
        d.line(((cx,cy),(x,y)),fill=rgba(TRANSMISSION,100),width=1)
    d.text((cx,cy),'लक्षण',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'Marks of a true teacher: realization, lineage, compassion, and scriptural mastery',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),50,EMBER_LIGHT,110,14)
    d.ellipse((cx-160,cy-115,cx+160,cy+115),outline=rgba(EMBER,150),width=2)
    d.ellipse((cx-155,cy-110,cx+155,cy+110),outline=rgba(INK,80),width=1)
    d.line((cx-180,cy-80,cx+180,cy+80),fill=rgba(BRONZE_DARK,130),width=3)
    d.line((cx-180,cy+80,cx+180,cy-80),fill=rgba(BRONZE_DARK,130),width=3)
    d.text((cx,cy+110),'कुगुरु',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'The false teacher: the warning against those who transmit without realization',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(BRONZE,160),width=2)
    for i in range(8):
        a=i*2*math.pi/8
        r=lerp(30,175,smooth(.05+.06*i,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(BRONZE,EMBER,i/8),170),outline=rgba(TRANSMISSION,120),width=1)
    glow(im,(cx,cy-5),40,BRONZE_LIGHT,100,12)
    d.text((cx,cy),'अभिषेक',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'The ritual of consecration establishes the teacher in the seat of transmission',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),60,BRONZE_LIGHT,110,15)
    d.ellipse((cx-140,cy-100,cx+140,cy+100),outline=rgba(TRANSMISSION,140),width=2)
    d.text((cx,cy),'ज्ञान',font=DEVA_BIG,fill=INK,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14
        x=cx+math.cos(a)*130; y=cy+math.sin(a)*92
        if smooth(.05,.78,t)>i*0.05: d.line(((cx,cy),(x,y)),fill=rgba(BRONZE,110),width=2)
    d.text((640,505),'Knowledge is the sole sign of authentic transmission — not birth or office',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(EMBER,150),width=3)
    d.ellipse((cx-175,cy-120,cx+175,cy+120),outline=rgba(BRONZE,100),width=1)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(TRANSMISSION,130),width=2)
    glow(im,(cx,cy-10),35,EMBER_LIGHT,95,12)
    d.text((cx,cy),'व्रत',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'The teacher\'s vow: to transmit without distortion and without possessiveness',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),45,BRONZE_LIGHT,100,13)
    d.ellipse((cx-170,cy-120,cx+170,cy+120),outline=rgba(INK,140),width=2)
    for i in range(9):
        a=i*2*math.pi/9
        x=cx+math.cos(a)*155; y=cy+math.sin(a)*110
        if smooth(.05,.75,t)>i*0.06: d.line(((cx,cy),(x,y)),fill=rgba(EMBER,110),width=2)
    d.text((cx,cy),'पतन',font=DEVA_MED,fill=INK,anchor='mm')
    d.text((640,505),'When the disciple falls: compassion and re-initiation for those who stumble',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),80,BRONZE_LIGHT,130,18)
    for i in range(18):
        a=i*2*math.pi/18
        r=lerp(25,215,smooth(.02,.9,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(INK,BRONZE,i/18),180),outline=rgba(EMBER,120),width=1)
    d.text((cx,cy),'सिद्ध',font=DEVA_BIG,fill=INK,anchor='mm')
    d.text((cx,190),'ādeya stage',font=TERM_FONT,fill=BRONZE,anchor='mm')
    d.text((640,505),'The adept stage: one who has realized and now transmits the teaching',font=SUB_FONT,fill=INK_LIGHT,anchor='mm')


SCENES=[
Scene('cc01','Crossing Traditions','Bringing the aspirant into the Śaiva fold.','Saṅkrānti','Conversion rites welcome aspirants from other traditions.','conversion',['conversion','crossing','traditions'],'overview','seven-ray crossing seal',sc01),
Scene('cc02','Seven Common Mantras','The foundation of new practice.','Mantra','Seven root mantras are given to the convert.','mantra',['mantra','seven','foundation'],'foundation','seven-point mantra ring',sc02),
Scene('cc03','Fire and Purification','The element of transformation.','Agni','Fire is the transformative element in conversion rites.','fire',['fire','purification','transformation'],'foundation','sixfold fire diagram',sc03),
Scene('cc04','Who Can Teach','Qualifications for authentic transmission.','Ācārya','The teacher must embody realization, lineage, and compassion.','qualification',['teacher','qualification','transmission'],'foundation','ten-ray qualification field',sc04),
Scene('cc05','Marks of a True Teacher','Realization, lineage, compassion, mastery.','Lakṣaṇa','The distinguishing marks of an authentic guru.','marks',['teacher','marks','authenticity'],'teacher','twelve-mark seal',sc05),
Scene('cc06','The False Teacher','Warning against unrealized transmission.','Kuguru','The dangers of following a teacher without realization.','warning',['false teacher','warning','danger'],'warning','crossed-out false seal',sc06),
Scene('cc07','Ritual of Consecration','Establishing the teacher in the seat of transmission.','Abhiṣeka','The consecration ritual empowers the teacher.','consecration',['consecration','ritual','empowerment'],'ritual','eight-point consecration ring',sc07),
Scene('cc08','Knowledge as Sole Sign','Knowledge is the only true credential.','Jñāna','Realization, not birth or office, qualifies a teacher.','knowledge',['knowledge','sign','authenticity'],'teaching','knowledge radiance circle',sc08),
Scene('cc09','Teacher\'s Vow','To transmit without distortion.','Vrata','The teacher vows to transmit the teaching faithfully.','vow',['vow','transmission','integrity'],'vow','five-vow pentagon',sc09),
Scene('cc10','When the Disciple Falls','Compassion for those who stumble.','Patana','Re-initiation is available for those who fall.','compassion',['disciple','fall','compassion'],'compassion','nine-point fall circle',sc10),
Scene('cc11','The Adept Stage','Realization and transmission.','Siddha','The adept who has realized and now transmits the teaching.','seal',['adept','realization','transmission'],'seal','adept radiance seal',sc11),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000: continue
        t=i/max(1,NFRAMES-1); im=base_image(SEED+hash(sc.id)%10000+i); border(im); dust(im,SEED+i,20); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=94)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def contact_sheet():
    sheet=Image.new('RGB',(4*320,3*180),PARCHMENT)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Conversion & Teacher Consecration','source_basis':'Tantrāloka Chapters 22-23: Conversion (saṅkrānti) & Teacher Consecration (ācāryābhiṣeka).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'transmission and consecration','background':'warm parchment with bronze tint','materials':['bronze','ember fire','dark ink','transmission rod','parchment ground']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['cc01'],'foundation':['cc02','cc03','cc04'],'teacher':['cc05','cc08'],'warning':['cc06'],'ritual':['cc07'],'vow':['cc09'],'compassion':['cc10'],'seal':['cc11']},'reusability_notes':{'cc01':'Use for conversion or crossing traditions.','cc02':'Use for seven mantras.','cc03':'Use for fire purification.','cc04':'Use for teacher qualifications.','cc05':'Use for marks of a true teacher.','cc06':'Use for false teacher warning.','cc07':'Use for consecration ritual.','cc08':'Use for knowledge as sign.','cc09':'Use for teacher\'s vow.','cc10':'Use for disciple falling.','cc11':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Conversion & Teacher Consecration (Chapters 22-23)

## Aim
This pack visualizes Tantrāloka Chapters 22-23 on conversion (saṅkrānti) and teacher consecration (ācāryābhiṣeka).

## Core structure
- Conversion brings an aspirant from another tradition into the Śaiva fold.
- Seven common mantras form the foundation of new practice.
- Fire is the transformative and purifying element.
- The teacher must possess realization, lineage, compassion, and mastery.
- Marks of a true teacher distinguish authentic from false.
- The false teacher transmits without realization.
- Consecration establishes the teacher in the seat of transmission.
- Knowledge (jñāna) is the sole sign of authentic transmission.
- The teacher vows to transmit without distortion.
- Compassion extends to the fallen disciple.
- The adept stage marks one who has realized and transmits.

## Visual rules
- Bronze and ember convey the forge-like nature of conversion.
- Use rod-like shapes suggesting transmission implements.
- The false teacher should be marked by crossed lines or negation.
- Consecration scenes should feel formal and numinous.

## Style family
Warm parchment, bronze metal, ember fire, dark ink, transmission rod.

## Guardrails
- Conversion is not superiority — it is joining a specific lineage.
- The false teacher is warned against, not condemned absolutely.
- Consecration is empowerment of an already-existing qualification.
- Knowledge as sole sign: realization trumps birth, office, or reputation.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Conversion & Consecration Pack

## Differentiation
This pack introduces bronze/ember transmission-rod visual language distinct from threshold or ceremonial palettes.

## New symbols
1. seven-ray crossing seal
2. seven-point mantra ring
3. sixfold fire diagram
4. ten-ray qualification field
5. twelve-mark seal
6. crossed-out false seal
7. eight-point consecration ring
8. knowledge radiance circle
9. five-vow pentagon
10. nine-point fall circle
11. adept radiance seal

## New relationships
- conversion → crossing into Śaiva fold
- fire → transformation
- teacher → qualification marks
- false teacher → crossed negation
- consecration → empowerment
- knowledge → sole credential

## Material vocabulary
Bronze, ember fire, dark ink, transmission rod, parchment ground.

## Closing seal
An 18-point bronze/ink radiance ring with the title 'siddha' — the adept stage as the completion of the teacher's path.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Conversion & Teacher Consecration Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'conversion_consecration_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'conversion_consecration_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['conversion_consecration_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            q.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): q.write(p,arcname=f'scenes/{p.name}')

def main():
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "--metadata":
        metadata()
        return
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES:
        print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'conversion_consecration_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
