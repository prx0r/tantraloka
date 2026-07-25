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
SEED = 51412

HERITAGE_GOLD = (195, 155, 75)
HERITAGE_GOLD_LIGHT = (230, 195, 130)
HERITAGE_GOLD_DARK = (145, 110, 50)
EARTH = (140, 100, 70)
EARTH_LIGHT = (185, 150, 120)
EARTH_DARK = (95, 65, 40)
INDIGO = (55, 65, 120)
INDIGO_LIGHT = (110, 120, 175)
INDIGO_DARK = (35, 42, 85)
PARCHMENT = (245, 240, 230)
PARCHMENT_LIGHT = (250, 247, 240)
LINEAGE = (170, 145, 105)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(HERITAGE_GOLD_LIGHT,140),outline=rgba(EARTH,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(HERITAGE_GOLD_LIGHT,110),outline=rgba(INDIGO,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(HERITAGE_GOLD,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(INDIGO,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(HERITAGE_GOLD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(243,238,228,220),outline=rgba(EARTH,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INDIGO_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=EARTH)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=HERITAGE_GOLD_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),75,HERITAGE_GOLD_LIGHT,110,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(HERITAGE_GOLD,160),width=3)
    d.ellipse((cx-195,cy-135,cx+195,cy+135),outline=rgba(INDIGO,90),width=1)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(EARTH_LIGHT,100),width=2)
    d.text((cx,cy),'देव',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Divine transmission: the teaching descends from Śiva through unbroken succession',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,HERITAGE_GOLD_LIGHT,105,16)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        r=lerp(30,200,smooth(.04+.07*i,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(HERITAGE_GOLD,EARTH,i/7),170),outline=rgba(INDIGO,120),width=1)
    d.text((cx,cy-5),'भारत',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The journey of scripture across India: from Kashmir to Kerala and beyond',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(INDIGO,150),width=2)
    for i in range(12):
        a=i*2*math.pi/12
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        d.line(((cx,cy),(x,y)),fill=rgba(HERITAGE_GOLD_LIGHT,100),width=1)
    glow(im,(cx,cy-10),30,HERITAGE_GOLD_LIGHT,90,10)
    d.text((cx,cy),'तन्त्रालोक',font=DEVA_SMALL,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Tantrāloka as essence: Abhinavagupta\'s magnum opus distills the entire tradition',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),60,HERITAGE_GOLD_LIGHT,105,15)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        r=lerp(25,205,smooth(.05+.1*i,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-7,y-7,x+7,y+7),fill=rgba(mix(INDIGO,HERITAGE_GOLD,i/6),170),outline=rgba(EARTH,130),width=2)
    d.text((cx,cy-10),'शास्त्र',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Hierarchy of scriptures: each text belongs in a complete ecology of knowledge',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(EARTH,160),width=3)
    for i in range(4):
        a=-math.pi/2+i*2*math.pi/4
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(HERITAGE_GOLD,130),width=2)
    glow(im,(cx,cy-10),30,HERITAGE_GOLD_LIGHT,85,10)
    d.text((cx,cy),'पीठ',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Four Pīthas: the sacred seats of transmission in the four directions',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),70,HERITAGE_GOLD_LIGHT,110,16)
    for i in range(14):
        a=i*2*math.pi/14
        r=lerp(30,210,smooth(.02,.88,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(HERITAGE_GOLD,INDIGO,i/14),170))
    d.text((cx,cy-10),'कौल',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Trika Kaulism as the crown: the non-dual Kaula is the highest teaching',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(HERITAGE_GOLD,160),width=2)
    for i in range(16):
        a=i*2*math.pi/16
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(INDIGO_LIGHT,90),width=1)
    glow(im,(cx,cy-10),30,HERITAGE_GOLD_LIGHT,90,10)
    d.text((cx,cy),'सद्यः',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Immediate realization: the teaching aims at direct, instantaneous enlightenment',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,EARTH_LIGHT,105,16)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        r=lerp(30,195,smooth(.05+.08*i,.84,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(HERITAGE_GOLD,INDIGO,i/5),170),outline=rgba(EARTH,120),width=1)
    d.text((cx,cy-10),'अभिनव',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Abhinavagupta\'s life: the great master who synthesized and transmitted the tradition',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(INDIGO,150),width=3)
    d.ellipse((cx-175,cy-120,cx+175,cy+120),outline=rgba(HERITAGE_GOLD,90),width=1)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.78,t)>i*0.07: d.line(((cx,cy),(x,y)),fill=rgba(EARTH_LIGHT,120),width=2)
    d.text((cx,cy),'अम्बा',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Ambā the Yoginī: the inspired collaborator who catalyzed Abhinavagupta\'s work',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),55,HERITAGE_GOLD_LIGHT,100,14)
    for i in range(18):
        a=i*2*math.pi/18
        r=lerp(25,200,smooth(.02,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(INDIGO,HERITAGE_GOLD,i/18),165))
    d.text((cx,cy-10),'रचना',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Composition of Tantrāloka: the circumstances, structure, and scope of the work',font=SUB_FONT,fill=EARTH,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,HERITAGE_GOLD_LIGHT,140,20)
    for i in range(24):
        a=i*2*math.pi/24
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(INDIGO,HERITAGE_GOLD,i/24),180),outline=rgba(EARTH,120),width=1)
    d.text((cx,cy),'शिव',font=DEVA_BIG,fill=INDIGO_DARK,anchor='mm')
    d.text((cx,190),'iti śivam',font=TERM_FONT,fill=HERITAGE_GOLD,anchor='mm')
    d.text((640,505),'Final blessing: Tantrāloka concludes with the seal of auspiciousness — iti śivam',font=SUB_FONT,fill=EARTH,anchor='mm')


SCENES=[
Scene('tc01','Divine Transmission','The teaching descends from Śiva.','Deva','The unbroken succession of transmission from Śiva.','transmission',['divine','transmission','succession'],'overview','ten-ray divine transmission',sc01),
Scene('tc02','Journey of Scripture Across India','From Kashmir to Kerala and beyond.','Bhārata','The geographical spread of Tantric teachings.','geography',['india','journey','scripture'],'foundation','seven-point geography ring',sc02),
Scene('tc03','Tantrāloka as Essence','Abhinavagupta\'s magnum opus.','Tantrāloka','Tantrāloka distills the entire Śaiva tradition.','essence',['tantrāloka','essence','abhinavagupta'],'foundation','twelve-ray essence wheel',sc03),
Scene('tc04','Hierarchy of Scriptures','An ecology of knowledge.','Śāstra','Scriptures form a hierarchy within a complete system.','hierarchy',['scriptures','hierarchy','order'],'cosmic','six-level hierarchy ring',sc04),
Scene('tc05','Four Pīthas','The sacred seats of transmission.','Pīṭha','The four pīthas in the four cardinal directions.','pithas',['pīṭha','seats','directions'],'cosmic','four-pītha cross',sc05),
Scene('tc06','Trika Kaulism as Crown','The highest teaching.','Kaula','Non-dual Kaula is the crown of the Trika system.','kaula',['kaula','crown','trika'],'synthesis','14-point kaula crown',sc06),
Scene('tc07','Immediate Realization','Direct, instantaneous enlightenment.','Sadyas','The teaching aims at immediacy of realization.','immediate',['immediate','realization','direct'],'teaching','16-ray immediate field',sc07),
Scene('tc08','Abhinavagupta\'s Life','The master who synthesized the tradition.','Abhinavagupta','The remarkable life and work of the great master.','master',['abhinavagupta','life','master'],'biography','five-point life ring',sc08),
Scene('tc09','Ambā the Yoginī','The inspired collaborator.','Ambā','Ambā catalyzed Abhinavagupta\'s creative output.','yogini',['ambā','yoginī','collaborator'],'biography','eight-point ambā wheel',sc09),
Scene('tc10','Composition of Tantrāloka','Structure and scope of the work.','Racanā','The circumstances and scope of the masterwork.','composition',['composition','structure','scope'],'process','18-point composition ring',sc10),
Scene('tc11','Final Blessing','The seal of auspiciousness.','Iti Śivam','Tantrāloka concludes with the auspicious seal.','seal',['final','blessing','śivam'],'seal','iti śivam final seal',sc11),
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
    manifest={'project':'Tantrāloka — Transmission & Conclusion','source_basis':'Tantrāloka Chapters 36-37: Lineage (guru-paramparā) & Conclusion (saṃgraha/upasaṃhāra).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'heritage gold and lineage-tree','background':'warm parchment with heritage gold','materials':['heritage gold','earth brown','indigo lineage','parchment','lineage thread']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['tc01'],'foundation':['tc02','tc03'],'cosmic':['tc04','tc05'],'synthesis':['tc06'],'teaching':['tc07'],'biography':['tc08','tc09'],'process':['tc10'],'seal':['tc11']},'reusability_notes':{'tc01':'Use for divine transmission.','tc02':'Use for journey across India.','tc03':'Use for Tantrāloka essence.','tc04':'Use for scripture hierarchy.','tc05':'Use for four pīthas.','tc06':'Use for Kaula as crown.','tc07':'Use for immediate realization.','tc08':'Use for Abhinavagupta\'s life.','tc09':'Use for Ambā the Yoginī.','tc10':'Use for composition of Tantrāloka.','tc11':'Use as pack final seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Transmission & Conclusion (Chapters 36-37)

## Aim
This pack visualizes Tantrāloka Chapters 36-37 on lineage (guru-paramparā) and conclusion (upasaṃhāra).

## Core structure
- Divine transmission descends from Śiva through an unbroken succession.
- The journey of scripture across India from Kashmir to Kerala.
- Tantrāloka is the essence of the entire Śaiva tradition.
- Scriptures form a hierarchy within a complete ecology of knowledge.
- Four Pīthas are the sacred seats of transmission.
- Trika Kaulism is the crown of the system.
- Immediate realization (sadyas) is the teaching's aim.
- Abhinavagupta's life embodied the tradition.
- Ambā the Yoginī catalyzed the master's work.
- Tantrāloka's composition has a specific structure and scope.
- The work closes with the seal of auspiciousness: iti śivam.

## Visual rules
- Heritage gold and earth brown convey tradition and groundedness.
- Indigo represents the lineage thread through time.
- Tree-like and branching structures suggest lineage.
- The map of India should be suggested, not detailed.
- Ambā is dignified as an equal collaborator.

## Style family
Warm parchment, heritage gold, earth brown, indigo lineage, lineage thread.

## Guardrails
- Lineage is not mere chronology — it is living transmission.
- The four pīthas are not just geographical — they are spiritual seats.
- Kaula as crown is about inclusivity, not hierarchy.
- Iti śivam is not just a colophon — it is the seal of the tradition.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Transmission & Conclusion Pack

## Differentiation
This pack introduces a heritage-gold lineage-tree visual language distinct from crystalline or gesture palettes.

## New symbols
1. ten-ray divine transmission
2. seven-point geography ring
3. twelve-ray essence wheel
4. six-level hierarchy ring
5. four-pītha cross
6. 14-point kaula crown
7. 16-ray immediate field
8. five-point life ring
9. eight-point ambā wheel
10. 18-point composition ring
11. iti śivam final seal

## New relationships
- transmission → śiva → lineage
- scripture → journey across India
- Tantrāloka → tradition essence
- pīthas → sacred seats
- Kaula → crown of system
- Abhinavagupta → embodiment
- Ambā → inspired collaboration
- iti śivam → auspicious seal

## Material vocabulary
Heritage gold, earth brown, indigo lineage, parchment, lineage thread.

## Closing seal
A 24-point heritage-gold/indigo ring with the central title 'iti śivam' — the final blessing sealing the entire Tantrāloka tradition.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Transmission & Conclusion Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'transmission_conclusion_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'transmission_conclusion_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['transmission_conclusion_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'transmission_conclusion_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
