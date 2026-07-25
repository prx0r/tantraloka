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
SEED = 51408

DEEP_BLUE = (20, 30, 70)
DEEP_BLUE_LIGHT = (60, 75, 130)
ASTRAL_GOLD = (205, 165, 80)
GOLD_LIGHT = (240, 205, 130)
GOLD_DARK = (155, 120, 50)
SILVER = (185, 195, 210)
SILVER_DARK = (130, 140, 160)
ASTRAL = (100, 130, 180)
ASTRAL_LIGHT = (155, 180, 220)
IVORY = (248, 244, 235)
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
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(IVORY,dtype=np.float32)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(ASTRAL_LIGHT,140),outline=rgba(SILVER,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(DEEP_BLUE,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(ASTRAL_GOLD,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(DEEP_BLUE,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(ASTRAL_GOLD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(246,242,233,220),outline=rgba(DEEP_BLUE,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=DEEP_BLUE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SILVER_DARK)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),70,GOLD_LIGHT,110,16)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(ASTRAL_GOLD,150),width=3)
    d.ellipse((cx-195,cy-135,cx+195,cy+135),outline=rgba(SILVER,90),width=1)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(ASTRAL,120),width=2)
    d.text((cx,cy),'नैमित्तिक',font=DEVA_SMALL,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Occasional rites respond to special junctures in the cosmic calendar',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55, GOLD_LIGHT,105,14)
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12
        r=lerp(25,195,smooth(.04+.05*i,.84,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(ASTRAL_GOLD,ASTRAL,i/12),170),outline=rgba(DEEP_BLUE,120),width=1)
    d.text((cx,cy-5),'काल',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'The sacred calendar: certain times carry heightened spiritual power',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(SILVER,160),width=2)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        if smooth(.05,.8,t)>i*0.06: d.line(((cx,cy),(x,y)),fill=rgba(ASTRAL,110),width=2)
    glow(im,(cx,cy-10),30,SILVER,90,12)
    d.text((cx,cy),'समूह',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Collective consciousness: rites performed together amplify spiritual power',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),60,ASTRAL_LIGHT,105,15)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        x=cx+math.cos(a)*190; y=cy+math.sin(a)*190*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*50,cy+math.sin(a)*50-20),(x-20,y+20),(x,y),40),smooth(.04,.82,t))
        if len(pts)>1: line_glow(im,pts,mix(SILVER,ASTRAL_GOLD,i/7),2,80,6)
    d.text((cx,cy-10),'सूत्र',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'The sacred thread: a symbol of connection across the community of practitioners',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(DEEP_BLUE,150),width=3)
    d.ellipse((cx-175,cy-120,cx+175,cy+120),outline=rgba(ASTRAL_GOLD,90),width=1)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        d.line(((cx,cy),(x,y)),fill=rgba(SILVER,100),width=1)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,85,10)
    d.text((cx,cy),'मृत्यु',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Death and the initiate: for one who knows, death is a transition, not an end',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,GOLD_LIGHT,110,16)
    for i in range(14):
        a=i*2*math.pi/14
        r=lerp(30,210,smooth(.02,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(ASTRAL,ASTRAL_GOLD,i/14),170))
    d.text((cx,cy-10),'परकाय',font=DEVA_SMALL,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Entering another body: the advanced yogi can transfer consciousness at will',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(ASTRAL_GOLD,160),width=2)
    for i in range(12):
        a=i*2*math.pi/12
        r=lerp(20,185,smooth(.05+.06*i,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SILVER,DEEP_BLUE,i/12),160),outline=rgba(GOLD_DARK,110),width=1)
    glow(im,(cx,cy-5),35,GOLD_LIGHT,95,12)
    d.text((cx,cy),'जीवन्मुक्त',font=DEVA_SMALL,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Living liberation: the jīvanmukta experiences freedom while still embodied',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),50,GOLD_LIGHT,100,14)
    for i in range(16):
        a=i*2*math.pi/16
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*195*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*60,cy+math.sin(a)*60-25),(x-20,y+20),(x,y),40),smooth(.04,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(ASTRAL_GOLD,ASTRAL,i/16),2,75,5)
    d.text((cx,cy-5),'भावना',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Bhāvanā power: creative imagination is a force that shapes reality',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),70,ASTRAL_LIGHT,110,18)
    for i in range(13):
        a=-math.pi/2+i*2*math.pi/13
        r=lerp(30,200,smooth(.03,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SILVER,ASTRAL,i/13),170),outline=rgba(ASTRAL_GOLD,110),width=1)
    d.text((cx,cy-10),'योगिनी',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Gathering with Yoginīs: the circle of awakened feminine powers',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(ASTRAL_GOLD,160),width=3)
    d.ellipse((cx-185,cy-130,cx+185,cy+130),outline=rgba(DEEP_BLUE,90),width=1)
    for i in range(9):
        a=i*2*math.pi/9
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        d.line(((cx,cy),(x,y)),fill=rgba(SILVER,110),width=2)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,90,10)
    d.text((cx,cy),'शास्त्र',font=DEVA_MED,fill=DEEP_BLUE,anchor='mm')
    d.text((640,505),'Teaching scriptures: the transmission of textual knowledge within the living tradition',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,GOLD_LIGHT,140,20)
    for i in range(20):
        a=i*2*math.pi/20
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(DEEP_BLUE,ASTRAL_GOLD,i/20),180),outline=rgba(SILVER,120),width=1)
    d.text((cx,cy),'गुरु',font=DEVA_BIG,fill=DEEP_BLUE,anchor='mm')
    d.text((cx,190),'pūjā',font=TERM_FONT,fill=ASTRAL_GOLD,anchor='mm')
    d.text((640,505),'Guru Pūjā: honoring the teacher in whom the entire tradition is embodied',font=SUB_FONT,fill=SILVER_DARK,anchor='mm')


SCENES=[
Scene('or01','Occasional vs Regular Rites','Responding to special cosmic junctures.','Naimittika','Occasional rites differ from regular daily practice.','distinction',['occasional','regular','distinction'],'overview','six-ray occasional seal',sc01),
Scene('or02','Sacred Calendar','Times of heightened spiritual power.','Kāla','Certain moments in the calendar carry special potency.','calendar',['calendar','sacred','time'],'foundation','twelve-month wheel',sc02),
Scene('or03','Collective Consciousness','Amplified power through group practice.','Samūha','Community rites amplify spiritual effect.','community',['community','collective','amplification'],'foundation','ten-point community wheel',sc03),
Scene('or04','Sacred Thread','A symbol of community connection.','Sūtra','The sacred thread represents connection across practitioners.','thread',['thread','connection','symbol'],'symbol','seven-thread rays',sc04),
Scene('or05','Death and the Initiate','Death is a transition, not an end.','Mṛtyu','The initiate faces death as a passage, not a termination.','death',['death','initiate','transition'],'threshold','eight-ray death passage',sc05),
Scene('or06','Entering Another Body','Consciousness transfer at will.','Parakāya','Advanced yogis can enter another body.','parakaya',['body','entry','consciousness'],'advanced','14-point parakāya ring',sc06),
Scene('or07','Living Liberation','Freedom while embodied.','Jīvanmukti','The jīvanmukta experiences liberation in this life.','jivanmukti',['jīvanmukti','liberation','life'],'seal','twelve-point liberation ring',sc07),
Scene('or08','Bhāvanā Power','Creative imagination shapes reality.','Bhāvanā','Intensive creative contemplation has transformative power.','bhavana',['bhāvanā','imagination','power'],'practice','16-ray bhāvanā field',sc08),
Scene('or09','Gathering with Yoginīs','The circle of awakened feminine powers.','Yoginī','The yoginī circle embodies the collective awakened feminine.','yogini',['yoginī','circle','feminine'],'practice','thirteen-point yoginī ring',sc09),
Scene('or10','Teaching Scriptures','Transmission of textual knowledge.','Śāstra','Scriptural teaching within the living tradition.','teaching',['scripture','teaching','transmission'],'transmission','nine-ray scripture wheel',sc10),
Scene('or11','Guru Pūjā','Honoring the embodied tradition.','Guru Pūjā','Worship of the teacher in whom the tradition lives.','seal',['guru','pūjā','honor'],'seal','guru pūjā seal',sc11),
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
    sheet=Image.new('RGB',(4*320,3*180),IVORY)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Occasional Rites','source_basis':'Tantrāloka Chapter 28: Occasional Rites (naimittika vidhi), Death, and Liberation.','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'astronomical deep-blue and wheel-of-time','background':'warm ivory with deep blue undertone','materials':['deep blue cosmos','gold zodiac','silver astral light','astral blue','ivory ground']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['or01'],'foundation':['or02','or03'],'symbol':['or04'],'threshold':['or05'],'advanced':['or06'],'seal':['or07','or11'],'practice':['or08','or09'],'transmission':['or10']},'reusability_notes':{'or01':'Use for occasional vs regular distinction.','or02':'Use for sacred calendar.','or03':'Use for collective consciousness.','or04':'Use for sacred thread.','or05':'Use for death passage.','or06':'Use for parakāya.','or07':'Use for jīvanmukti.','or08':'Use for bhāvanā power.','or09':'Use for yoginī circle.','or10':'Use for scripture teaching.','or11':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Occasional Rites (Chapter 28)

## Aim
This pack visualizes Tantrāloka Chapter 28 on occasional rites (naimittika vidhi), propitious times, death, and liberation.

## Core structure
- Occasional rites differ from regular daily practice in timing and purpose.
- The sacred calendar identifies times of heightened spiritual power.
- Collective rites amplify effect through group consciousness.
- The sacred thread symbolizes community connection.
- The initiate faces death as transition, not termination.
- Advanced yogis can transfer consciousness into another body (parakāya).
- Living liberation (jīvanmukti) is attainable in this life.
- Bhāvanā is creative imagination that shapes reality.
- The yoginī circle embodies collective awakened feminine power.
- Scriptural teaching transmits textual knowledge within the tradition.
- Guru Pūjā honors the teacher as the embodied tradition.

## Visual rules
- Deep blue cosmos and gold stars create an astronomical feel.
- Silver astral light provides secondary illumination.
- Use circular forms suggesting cycles, wheels, and orbits.
- Parakāya should suggest transfer, not magic.
- The yoginī circle is dignified and collective, not exoticized.

## Style family
Ivory field, deep blue cosmos, gold zodiac, silver astral light, astral blue.

## Guardrails
- Sacred calendar is about resonance, not superstition.
- Parakāya is an advanced capacity, not a party trick.
- Jīvanmukti is not self-congratulatory.
- Yoginīs are awakened powers, not decorative figures.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Occasional Rites Pack

## Differentiation
This pack introduces an astronomical wheel-of-time visual language distinct from daily-cycle or initiatory palettes.

## New symbols
1. six-ray occasional seal
2. twelve-month wheel
3. ten-point community wheel
4. seven-thread rays
5. eight-ray death passage
6. 14-point parakāya ring
7. twelve-point liberation ring
8. 16-ray bhāvanā field
9. thirteen-point yoginī ring
10. nine-ray scripture wheel
11. guru pūjā seal

## New relationships
- occasional rites → cosmic calendar
- collective → amplified power
- death → transition
- parakāya → consciousness transfer
- jīvanmukti → freedom in life
- bhāvanā → reality shaping
- guru pūjā → embodied tradition

## Material vocabulary
Deep blue cosmos, gold zodiac, silver astral light, astral blue, ivory ground.

## Closing seal
A 20-point deep-blue/gold ring with the central title 'guru pūjā' — honoring the teacher as the living embodiment of the complete tradition.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Occasional Rites Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'occasional_rites_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'occasional_rites_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['occasional_rites_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'occasional_rites_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
