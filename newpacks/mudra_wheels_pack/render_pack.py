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
SEED = 51410

OCHRE = (195, 150, 95)
OCHRE_DARK = (150, 110, 65)
OCHRE_LIGHT = (230, 195, 145)
DEEP_INDIGO = (44, 53, 96)
DEEP_INDIGO_LIGHT = (90, 100, 155)
BONE = (235, 225, 215)
BONE_DARK = (200, 188, 175)
GESTURE = (170, 130, 100)
GESTURE_LIGHT = (210, 180, 155)
GESTURE_GOLD = (205, 165, 80)
GOLD_LIGHT = (240, 205, 130)
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
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(BONE,dtype=np.float32)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(GESTURE_LIGHT,140),outline=rgba(OCHRE,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(DEEP_INDIGO,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(OCHRE,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(DEEP_INDIGO,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(OCHRE,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(243,238,230,220),outline=rgba(DEEP_INDIGO,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=DEEP_INDIGO)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=GESTURE)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=OCHRE_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),70,OCHRE_LIGHT,105,16)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(OCHRE,150),width=3)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(DEEP_INDIGO_LIGHT,100),width=2)
    d.text((cx,cy),'मुद्रा',font=DEVA_BIG,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Mudrā seals and communicates — it is the gesture of awakening',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,GOLD_LIGHT,110,16)
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        r=lerp(30,200,smooth(.05+.08*i,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(GESTURE_GOLD,OCHRE,i/8),170),outline=rgba(DEEP_INDIGO,130),width=1)
    d.text((cx,cy-5),'खेचरी',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Khecarīmudrā: the supreme seal that moves in the void of consciousness',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(DEEP_INDIGO,160),width=2)
    for i in range(2):
        a=-math.pi/2+i*math.pi
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*130
        pts=partial(bezier((cx,cy),(x-30,cy-40),(x+30,cy+40),(x,y),40),smooth(.05,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(OCHRE,GESTURE_GOLD,i/2),3,100,7)
    d.text((cx,cy),'त्रिशूल',font=DEVA_SMALL,fill=DEEP_INDIGO,anchor='mm')
    d.text((cx,cy+30),'अस्थि',font=DEVA_SMALL,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Trident seal and skeleton seal: gestures that evoke the core structures of reality',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,OCHRE_LIGHT,100,14)
    for i in range(12):
        a=i*2*math.pi/12
        r=lerp(25,195,smooth(.03,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(OCHRE,GESTURE,i/12),165))
    d.text((cx,cy-10),'वीर्य',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Vitality of mudrā: these gestures channel and direct spiritual energy',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),60,OCHRE_LIGHT,105,15)
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(GESTURE_GOLD,150),width=2)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(DEEP_INDIGO_LIGHT,120),width=2)
    d.text((cx,cy),'देवी',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Wheels of Goddesses: the cakras of feminine power that govern manifestation',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),70,OCHRE_LIGHT,110,18)
    for i in range(34):
        a=-math.pi/2+i*2*math.pi/34
        r=lerp(20,210,smooth(.02,.88,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(OCHRE,GESTURE_GOLD,i/34),175))
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*155; y=cy+math.sin(a)*155*0.68
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(DEEP_INDIGO,160),outline=rgba(GESTURE_GOLD,200),width=2)
    d.text((cx,cy),'अर',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Six to thirty-four spokes: the wheels range from simple to complete articulation',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(OCHRE,160),width=3)
    for i in range(14):
        a=i*2*math.pi/14
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(GESTURE,100),width=1)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,90,10)
    d.text((cx,cy),'आधार',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Powerholders (ādhāras) of the wheels: the deities that preside over each cakra',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,OCHRE_LIGHT,110,16)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        r=lerp(50,190,smooth(.05+.1*i,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(mix(GESTURE_GOLD,DEEP_INDIGO,i/3),170),outline=rgba(OCHRE,140),width=2)
        d.text((x,y+25),['मालिनी','मातृका','शब्दराशि'][i],font=SMALL_FONT,fill=DEEP_INDIGO,anchor='mm')
    d.text((cx,cy-10),'तीन',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'Mālinī, Mātṛkā, Śabdarāśi: the three arrangements of the powers of speech',font=SUB_FONT,fill=GESTURE,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,OCHRE_LIGHT,140,20)
    for i in range(24):
        a=i*2*math.pi/24
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(DEEP_INDIGO,OCHRE,i/24),180),outline=rgba(GESTURE,120),width=1)
    d.text((cx,cy),'एकम्',font=DEVA_BIG,fill=DEEP_INDIGO,anchor='mm')
    d.text((cx,190),'sarvam advaitam',font=TERM_FONT,fill=OCHRE,anchor='mm')
    d.text((640,505),'All is One: mudrā, mantra, maṇḍala, and deity all resolve in non-dual awareness',font=SUB_FONT,fill=GESTURE,anchor='mm')


SCENES=[
Scene('mw01','What is Mudrā','The gesture that seals and communicates awakening.','Mudrā','Mudrā is a ritual seal that channels and expresses spiritual energy.','essence',['mudrā','gesture','seal'],'overview','ten-ray mudrā field',sc01),
Scene('mw02','Khecarīmudrā','The supreme seal moving in the void.','Khecarīmudrā','Khecarīmudrā seals consciousness in the void of supreme awareness.','khechari',['khecarī','mudrā','void'],'advanced','eight-point khecarī ring',sc02),
Scene('mw03','Trident Seal and Skeleton Seal','Gestures evoking core reality structures.','Triśūla Aṣṭhi','The trident seal and skeleton seal are powerful ritual gestures.','seals',['trident','skeleton','seal'],'practice','triple gesture emblem',sc03),
Scene('mw04','Vitality of Mudrā','Gestures channel spiritual energy.','Vīrya','Mudrās direct and concentrate spiritual energy.','vitality',['vitality','energy','gesture'],'practice','twelve-point vitality ring',sc04),
Scene('mw05','Wheels of Goddesses','The cakras of feminine power.','Devī','The goddess wheels govern different levels of manifestation.','wheels',['goddesses','wheels','cakras'],'cosmic','sixfold goddess wheel',sc05),
Scene('mw06','Six to Thirty-Four Spokes','Ranges of wheel articulation.','Ara','Wheels range from simple 6-spoke to complete 34-spoke forms.','spokes',['spokes','wheels','articulation'],'cosmic','34-spoke wheel with 6 hubs',sc06),
Scene('mw07','Powerholders of Wheels','Deities presiding over each cakra.','Ādhāra','Each wheel has a presiding deity that holds its power.','powerholders',['powerholders','deities','wheels'],'cosmic','14-ray ādhāra wheel',sc07),
Scene('mw08','Mālinī, Mātṛkā, Śabdarāśi','Three arrangements of speech powers.','Mālinī Mātṛkā Śabdarāśi','Three different organizations of the powers of speech.','arrangements',['arrangements','speech','powers'],'teaching','threefold arrangement triangle',sc08),
Scene('mw09','All is One','Everything resolves in non-dual awareness.','Ekam','Mudrā, mantra, maṇḍala, and deity all non-dual.','seal',['oneness','non-dual','seal'],'seal','24-point unity seal',sc09),
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
    sheet=Image.new('RGB',(4*320,3*180),BONE)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Mudrās & Wheels of Deities','source_basis':'Tantrāloka Chapters 32-33: Mudrās (mudrā) and Wheels of Deities (devīcakra).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'gesture ochre and hand-seal geometry','background':'bone with ochre warmth','materials':['gesture ochre','deep indigo','bone ground','mudrā gold','seal gesture-brown']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['mw01'],'advanced':['mw02'],'practice':['mw03','mw04'],'cosmic':['mw05','mw06','mw07'],'teaching':['mw08'],'seal':['mw09']},'reusability_notes':{'mw01':'Use for mudrā definition.','mw02':'Use for khecarīmudrā.','mw03':'Use for trident/skeleton seals.','mw04':'Use for mudrā vitality.','mw05':'Use for goddess wheels.','mw06':'Use for 6-34 spokes.','mw07':'Use for powerholders.','mw08':'Use for Mālinī/Mātṛkā/Śabdarāśi.','mw09':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Mudrās & Wheels of Deities (Chapters 32-33)

## Aim
This pack visualizes Tantrāloka Chapters 32-33 on mudrās (seals/gestures) and wheels of deities (devīcakra).

## Core structure
- Mudrā is a ritual seal that expresses and channels spiritual awareness.
- Khecarīmudrā seals consciousness in the void of supreme awareness.
- The trident seal (triśūla mudrā) and skeleton seal evoke core structures.
- Mudrās channel spiritual energy with specific vitality.
- Goddess wheels (devīcakras) govern manifestation levels.
- Spokes range from 6 to 34, representing increasing articulation.
- Each wheel has presiding powerholders (ādhāras).
- Mālinī, Mātṛkā, and Śabdarāśi organize the powers of speech.
- All distinctions resolve in non-dual awareness.

## Visual rules
- Ochre and deep indigo dominate as earthy and contemplative.
- Hand-seal shapes should be suggested through line, not anatomy.
- Wheels must feel rotational and alive.
- The skeleton seal is not morbid — it evokes the bare structure.
- Khecarīmudrā should suggest interiority, not the sky.

## Style family
Bone field, gesture ochre, deep indigo, mudrā gold, seal gesture-brown.

## Guardrails
- Mudrās are not decorative hand positions — they are energetic seals.
- Khecarīmudrā is a subtle practice, not a physical tongue posture.
- The skeleton seal is about structure, not death.
- Goddess wheels are powers, not mythological figures.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Mudrā & Wheels Pack

## Differentiation
This pack introduces hand-seal and wheel-of-deities visual language distinct from mantra or daily-cycle palettes.

## New symbols
1. ten-ray mudrā field
2. eight-point khecarī ring
3. triple gesture emblem
4. twelve-point vitality ring
5. sixfold goddess wheel
6. 34-spoke wheel with 6 hubs
7. 14-ray ādhāra wheel
8. threefold arrangement triangle
9. 24-point unity seal

## New relationships
- mudrā → energetic seal
- khecarīmudrā → void consciousness
- trident seal → core structure
- wheel spokes → articulation levels
- powerholders → presiding deities
- Mālinī/Mātṛkā/Śabdarāśi → speech arrangements
- all distinctions → non-dual

## Material vocabulary
Gesture ochre, deep indigo, bone ground, mudrā gold, seal gesture-brown.

## Closing seal
A 24-point deep-indigo/ochre ring with the title 'ekam sarvam advaitam' — all is one, the non-dual conclusion of mudrā and wheels.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Mudrā & Wheels Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'mudra_wheels_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'mudra_wheels_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['mudra_wheels_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'mudra_wheels_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
