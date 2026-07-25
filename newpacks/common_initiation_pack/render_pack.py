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
SEED = 51402

CRIMSON = (170, 45, 55)
CRIMSON_DARK = (120, 25, 35)
CRIMSON_LIGHT = (210, 100, 110)
RITUAL_GOLD = (205, 165, 80)
GOLD_LIGHT = (240, 205, 130)
GOLD_DARK = (155, 120, 50)
IVORY = (250, 245, 235)
IVORY_DARK = (225, 218, 205)
SACRED = (80, 55, 65)
SACRED_LIGHT = (130, 100, 115)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(GOLD_LIGHT,140),outline=rgba(CRIMSON,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(SACRED,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(RITUAL_GOLD,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(SACRED,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(RITUAL_GOLD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(248,243,235,220),outline=rgba(SACRED,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=CRIMSON_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SACRED)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),80,GOLD_LIGHT,120,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(RITUAL_GOLD,160),width=3)
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*180; y=cy+math.sin(a)*125
        if smooth(.05,.8,t)>i*0.06: d.line(((cx,cy),(x,y)),fill=rgba(CRIMSON,100),width=2)
    d.text((cx,cy),'दीक्षा',font=DEVA_BIG,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'Initiation is the act of grace that opens the door to liberating knowledge',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        x=cx+math.cos(a)*190; y=cy+math.sin(a)*190*0.65
        r=20; amt=smooth(.05+.1*i,.85,t)
        if amt>0:
            d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(mix(RITUAL_GOLD,CRIMSON,i/8),int(80+amt*90)),outline=rgba(GOLD_DARK,150),width=2)
    d.text((cx,cy-10),'अष्ट',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'The eight ablutions purify the initiate through the elements of the cosmos',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,GOLD_LIGHT,110,16)
    d.ellipse((cx-140,cy-100,cx+140,cy+100),outline=rgba(CRIMSON,150),width=2)
    d.ellipse((cx-130,cy-92,cx+130,cy+92),outline=rgba(RITUAL_GOLD,130),width=2)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5; x=cx+math.cos(a)*100; y=cy+math.sin(a)*72
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(RITUAL_GOLD,140),width=3)
    d.text((cx,cy),'सुरा',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'Wine as sacrament in Kaula — the material world itself becomes the vehicle of grace',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        r=lerp(30,200,smooth(.05+.05*i,.82,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(CRIMSON,RITUAL_GOLD,i/7),170),outline=rgba(SACRED,130),width=1)
    d.ellipse((cx-120,cy-85,cx+120,cy+85),outline=rgba(RITUAL_GOLD,140),width=2)
    d.text((cx,cy),'देह',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'The body is a sacred geography — every part is a seat of divine power',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy-20),50,GOLD_LIGHT,115,14)
    for i in range(16):
        a=i*2*math.pi/16
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*90,cy+math.sin(a)*90-30),(cx+math.cos(a)*170,cy+math.sin(a)*170-10),(cx+math.cos(a)*210,cy+math.sin(a)*210*0.7),50),smooth(.04,.86,t))
        if len(pts)>1: line_glow(im,pts,mix(RITUAL_GOLD,CRIMSON,i/16),2,80,6)
    d.text((cx,cy-5),'मन्त्र',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'Mantra deposited in the body awakens the dormant power of consciousness',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    trishul_pts=[(cx,cy-110),(cx-90,cy+60),(cx+90,cy+60)]
    d.polygon(trishul_pts,outline=rgba(RITUAL_GOLD,180),fill=rgba(IVORY_DARK,40))
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*140; y=cy+math.sin(a)*140*0.6
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*60,cy+math.sin(a)*60-20),(x,y),(x+math.cos(a)*20,y+20),40),smooth(.05,.84,t))
        if len(pts)>1: line_glow(im,pts,RITUAL_GOLD,3,100,7)
    d.text((cx,cy-5),'त्रिशूल',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'The trident throne is built within the initiate as the seat of wisdom',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,CRIMSON_LIGHT,110,16)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*180*0.65
        d.polygon([(cx,cy),(x-20,y),(x+20,y)],fill=rgba(mix(RITUAL_GOLD,CRIMSON,i/6),120),outline=rgba(GOLD_DARK,140))
    d.text((cx,cy-10),'होम',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'The inner fire sacrifice consumes impurity and reveals the innate purity of awareness',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,GOLD_LIGHT,125,14)
    for f in range(1,6):
        r=lerp(10,195,smooth(.05+f*.02,.88,t))
        d.ellipse((cx-r,cy-r*0.7,cx+r,cy+r*0.7),outline=rgba(mix(RITUAL_GOLD,CRIMSON,f/6),100),width=2)
    d.text((cx,cy),'गुरु',font=DEVA_BIG,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'The teacher\'s hand transmits the current of grace directly into the disciple',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*200; y=cy+math.sin(a)*200*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*80,cy+math.sin(a)*80-40),(x-20,y),(x,y),60),smooth(.05,.85,t))
        if len(pts)>1: line_glow(im,pts,mix(CRIMSON,RITUAL_GOLD,i/3),3,95,7)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*80; y=cy+math.sin(a)*55
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(GOLD_LIGHT,180))
    d.text((cx,cy-10),'स्वप्न',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'Dream yoga reveals the dreamlike nature of waking experience',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),90,GOLD_LIGHT,130,20)
    for i in range(48):
        a=-math.pi/2+i*2*math.pi/48
        x=cx+math.cos(a)*210; y=cy+math.sin(a)*210*0.68
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(RITUAL_GOLD,CRIMSON,(i%7)/7),170),outline=rgba(GOLD_DARK,90),width=1)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        x=cx+math.cos(a)*160; y=cy+math.sin(a)*160*0.68
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(CRIMSON,150),outline=rgba(RITUAL_GOLD,200),width=2)
    d.text((cx,cy),'48+7',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'Forty-eight rites and seven purifications prepare the initiate for complete grace',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(RITUAL_GOLD,160),width=3)
    for i in range(10):
        a=i*2*math.pi/10; x=cx+math.cos(a)*170; y=cy+math.sin(a)*120
        d.line(((cx,cy),(x,y)),fill=rgba(CRIMSON,100),width=1)
    d.text((cx,cy),'व्रत',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((640,505),'Sacred vows structure the spiritual life and protect the transmission',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc12(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,GOLD_LIGHT,140,20)
    for i in range(18):
        a=i*2*math.pi/18
        r=lerp(25,215,smooth(.02,.9,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(CRIMSON,RITUAL_GOLD,i/18),180),outline=rgba(GOLD_DARK,120),width=1)
    d.text((cx,cy),'संयोग',font=DEVA_MED,fill=CRIMSON_DARK,anchor='mm')
    d.text((cx,190),'samāyī dīkṣā',font=TERM_FONT,fill=RITUAL_GOLD,anchor='mm')
    d.text((640,505),'The common initiation synthesizes all elements into a complete transmission',font=SUB_FONT,fill=SACRED,anchor='mm')


SCENES=[
Scene('ci01','What Initiation Is','The act of grace that opens the door to liberating knowledge.','Dīkṣā','Definition and nature of initiation as the foundation of the spiritual path.','definition',['initiation','dīkṣā','grace'],'overview','radiant initiatory seal',sc01),
Scene('ci02','The Eight Ablutions','Purification through the elements of the cosmos.','Aṣṭa','Eight ritual ablutions purify the initiate element by element.','purification',['ablutions','eight','purification'],'foundation','eight-orb ablution circle',sc02),
Scene('ci03','Wine as Sacrament','Kaula uses the material world as a vehicle of grace.','Surā','Wine consecrates the sacrament in the Kaula tradition.','kaula',['wine','sacrament','kaula'],'foundation','concentric kaula cup',sc03),
Scene('ci04','Sacred Geography of the Body','Every part of the body is a seat of divine power.','Deha','The body is a maṇḍala of sacred sites.','body_geography',['body','geography','sacred'],'foundation','seven-seat body circle',sc04),
Scene('ci05','Power of Mantra Deposition','Mantra awakens dormant consciousness.','Mantra','Mantra deposited in the body activates spiritual power.','mantra',['mantra','deposition','awakening'],'practice','mantra-ray deposition',sc05),
Scene('ci06','Building the Trident Throne','The trident throne is the seat of wisdom.','Triśūla','The trident (triśūla) is built within as wisdom\'s seat.','throne',['trident','throne','wisdom'],'practice','trident throne triangle',sc06),
Scene('ci07','Inner Fire Sacrifice','Impurity is consumed by inner fire.','Homa','Inner fire sacrifice reveals innate purity.','sacrifice',['fire','sacrifice','purity'],'practice','sixfold flame offering',sc07),
Scene('ci08','Teacher\'s Hand','The teacher transmits grace through touch.','Guru','The guru\'s hand channels the current of grace.','transmission',['teacher','hand','transmission'],'transmission','hand concentric rings',sc08),
Scene('ci09','Dream Yoga','The dreamlike nature of waking experience.','Svapna','Dream yoga reveals the constructed nature of reality.','dream',['dream','yoga','awareness'],'practice','triple dream stream',sc09),
Scene('ci10','48+7 Purifying Rites','Forty-eight rites and seven purifications.','Aṣṭācatvāriṃśat','The complete purificatory sequence.','purification',['purification','rites','number'],'process','48+7 double field',sc10),
Scene('ci11','Sacred Vows','Vows structure the spiritual life.','Vrata','Sacred vows protect and guide the transmission.','vows',['vows','vrata','commitment'],'foundation','vow wheel ten-point',sc11),
Scene('ci12','Complete Synthesis','All elements united in one transmission.','Samāyī Dīkṣā','The common initiation as a complete synthesis.','seal',['synthesis','initiation','seal'],'seal','synthesis radiance seal',sc12),
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
    manifest={'project':'Tantrāloka — Common Initiation','source_basis':'Tantrāloka Chapter 15: The Common Initiation (sāmayī dīkṣā).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'ceremonial initiation and ritual implements','background':'ivory with gold undertone','materials':['crimson ritual cloth','gold ceremonial vessels','ivory altars','sacred thread','gemstone offerings']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['ci01'],'foundation':['ci02','ci03','ci04','ci11'],'practice':['ci05','ci06','ci07','ci09','ci10'],'transmission':['ci08'],'seal':['ci12']},'reusability_notes':{'ci01':'Use for definition of initiation.','ci02':'Use for elemental ablutions.','ci03':'Use for Kaula sacramental wine.','ci04':'Use for sacred body geography.','ci05':'Use for mantra deposition.','ci06':'Use for trident throne.','ci07':'Use for inner fire sacrifice.','ci08':'Use for guru\'s hand transmission.','ci09':'Use for dream yoga.','ci10':'Use for the 48+7 sequence.','ci11':'Use for sacred vows.','ci12':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Common Initiation (Chapter 15)

## Aim
This pack visualizes Tantrāloka Chapter 15 on sāmayī dīkṣā, the common initiation available to all qualified aspirants.

## Core structure
- Initiation is the act of grace opening the door to liberating knowledge.
- Eight ablutions purify the initiate through the elements.
- Wine as sacrament in Kaula: the material world as vehicle of grace.
- The body is a sacred geography with divine power centers.
- Mantra deposited in the body awakens consciousness.
- The trident throne is built as the seat of wisdom.
- Inner fire sacrifice consumes impurity.
- The teacher's hand transmits grace through touch.
- Dream yoga reveals the constructed nature of experience.
- Forty-eight rites and seven purifications complete the initiation.
- Sacred vows protect the transmission.
- All elements unite in a complete synthesis.

## Visual rules
- Crimson and gold dominate as ceremonial colors.
- Use ritual-object shapes: cups, flames, tridents, hands.
- The initiatory feel must be sacred but accessible.
- Icons should suggest ritual implements, not abstract philosophy.
- The teacher's hand should be stylized, not realistic.

## Style family
Ivory field, crimson ritual cloth, gold vessels, sacred purple trim, gemstone accents.

## Guardrails
- Initiation is not a transaction; it is the opening of what is already there.
- Wine as sacrament is specific to Kaula; do not generalize to all Tantric traditions.
- The teacher is a conduit, not the source of grace.
- Do not reduce the 48+7 rites to a numbered checklist.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Common Initiation Pack

## Differentiation
This pack creates a ceremonial ritual-implement visual language distinct from threshold or reflective palettes.

## New symbols
1. initiatory radiance seal
2. eight-orb ablution circle
3. consecrated wine cup
4. seven-seat body geography
5. mantra ray deposition
6. trident throne triangle
7. sixfold flame offering
8. teacher's hand concentric rings
9. triple dream stream
10. 48+7 double field
11. ten-point vow wheel
12. synthesis radiance seal

## New relationships
- initiation → grace opening
- elements → ablution
- material → sacrament
- body → sacred geography
- mantra → awakening
- teacher → transmission

## Material vocabulary
Crimson ritual cloth, gold ceremonial vessels, ivory altars, sacred thread, gemstone offerings.

## Closing seal
A radiant 18-point synthesis ring of crimson-gold points with the title 'samāyī dīkṣā' — the common initiation as a complete transmission.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Common Initiation Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'common_initiation_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'common_initiation_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['common_initiation_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'common_initiation_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
