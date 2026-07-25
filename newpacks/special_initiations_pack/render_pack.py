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
SEED = 51404

TWILIGHT = (55, 50, 75)
TWILIGHT_LIGHT = (100, 95, 125)
TWILIGHT_DARK = (30, 28, 45)
VOID = (20, 18, 30)
RAZOR = (175, 165, 155)
RAZOR_LIGHT = (210, 200, 190)
RAZOR_DARK = (130, 120, 110)
EMBER = (200, 100, 55)
EMBER_LIGHT = (230, 150, 100)
BONE = (235, 225, 215)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(TWILIGHT_LIGHT,140),outline=rgba(RAZOR,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(EMBER_LIGHT,110),outline=rgba(TWILIGHT,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(EMBER,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(TWILIGHT,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(RAZOR,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(233,223,215,220),outline=rgba(TWILIGHT,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=TWILIGHT_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=TWILIGHT)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=EMBER)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),75,EMBER_LIGHT,110,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(RAZOR,150),width=2)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(mix(TWILIGHT,EMBER,i/10),110),width=2)
    d.text((cx,cy),'दीक्षा',font=DEVA_BIG,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'The essence of initiation: the transmission of liberating awareness itself',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(TWILIGHT,160),width=3)
    for i in range(12):
        a=i*2*math.pi/12
        r=lerp(20,170,smooth(.05+.06*i,.82,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(RAZOR,EMBER,i/12),160))
    d.text((cx,cy-5),'लघु',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Sometimes less is more — brief initiations carry the full power of transmission',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy-15),50,RAZOR_LIGHT,105,14)
    d.polygon([(cx,cy-90),(cx-100,cy+60),(cx+100,cy+60)],outline=rgba(TWILIGHT,170),fill=rgba(BONE,50))
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*170*0.62
        d.line(((cx,cy),(x,y)),fill=rgba(EMBER,130),width=2)
    d.text((cx,cy-5),'आचार्य',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'The teacher\'s inner qualification, not outward show, determines initiation\'s power',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),80,TWILIGHT_LIGHT,100,20)
    d.ellipse((cx-140,cy-100,cx+140,cy+100),outline=rgba(RAZOR,140),width=2)
    d.ellipse((cx-130,cy-92,cx+130,cy+92),outline=rgba(EMBER,100),width=1)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*120; y=cy+math.sin(a)*85
        if smooth(.05,.78,t)>i*0.07: d.line(((cx,cy),(x,y)),fill=rgba(RAZOR,120),width=2)
    d.text((cx,cy-10),'अन्त्य',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Initiation at death\'s threshold: the final opportunity for liberating transmission',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.line((cx-210,cy,cx+210,cy),fill=rgba(RAZOR,160),width=2)
    d.line((cx,cy-100,cx,cy+100),fill=rgba(RAZOR,160),width=2)
    glow(im,(cx,cy),40,EMBER_LIGHT,115,12)
    d.text((cx,cy),'क्षुर',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'The razor that severs: initiation cuts the knot of ignorance in a single stroke',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    points=[]
    for i in range(20):
        a=-math.pi/2+i*2*math.pi/20
        r=lerp(30,205,smooth(.02,.88,t))
        points.append((cx+math.cos(a)*r,cy+math.sin(a)*r*0.68))
    if len(points)>1: line_glow(im,points,TWILIGHT_LIGHT,2,90,5)
    for i,(x,y) in enumerate(points):
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(EMBER,RAZOR,i/20),170))
    d.text((cx,cy),'प्राण',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Breath\'s final journey: the vital energy is guided upward at the moment of death',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),65,EMBER_LIGHT,120,16)
    for i in range(16):
        a=i*2*math.pi/16
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*195*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*60,cy+math.sin(a)*60-30),(x-20,y+20),(x,y),40),smooth(.04,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(RAZOR,EMBER,i/16),2,80,6)
    d.text((cx,cy-10),'ब्रह्मविद्या',font=DEVA_SMALL,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Brahmavidyā for the dying: supreme knowledge imparted at the ultimate moment',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(TWILIGHT,150),width=3)
    d.ellipse((cx-95,cy-67,cx+95,cy+67),outline=rgba(RAZOR,130),width=2)
    d.ellipse((cx-42,cy-30,cx+42,cy+30),outline=rgba(EMBER,120),width=2)
    d.text((cx,cy),'तुला',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Weighing the soul: the scale of merit and grace at the threshold of liberation',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),55,EMBER_LIGHT,110,14)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*195*0.65
        flame=partial(bezier((cx,cy),(cx+math.cos(a)*30,cy-50),(x,cy+30),(x,y),40),smooth(.05,.85,t))
        if len(flame)>1: line_glow(im,flame,mix(EMBER,TWILIGHT,i/2),3,105,7)
    d.text((cx,cy+5),'मल',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Three impurities (āṇava, māyīya, kārma) are burned away by initiatory fire',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy-20),45,RAZOR_LIGHT,100,12)
    for i in range(12):
        a=i*2*math.pi/12
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*185*0.68
        d.line(((cx,cy),(x,y)),fill=rgba(mix(RAZOR,EMBER,i/12),130),width=2)
    d.text((cx,cy),'दृश्य',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Visible proof: the signs of successful initiation appear in the disciple\'s life',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,TWILIGHT_LIGHT,110,18)
    for i in range(14):
        a=i*2*math.pi/14
        r=lerp(30,210,smooth(.02,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(EMBER,RAZOR,i/14),170),outline=rgba(TWILIGHT,120),width=1)
    d.text((cx,cy),'दूर',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((640,505),'Reaching across distance: initiation transcends physical presence through grace',font=SUB_FONT,fill=TWILIGHT,anchor='mm')

def sc12(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,EMBER_LIGHT,130,20)
    for i in range(22):
        a=i*2*math.pi/22
        r=lerp(25,220,smooth(.02,.9,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(TWILIGHT,EMBER,i/22),180),outline=rgba(RAZOR,120),width=1)
    d.text((cx,cy),'जाल',font=DEVA_MED,fill=TWILIGHT_DARK,anchor='mm')
    d.text((cx,190),'anugraha jāla',font=TERM_FONT,fill=EMBER,anchor='mm')
    d.text((640,505),'The net of grace: no one is beyond reach of the Lord\'s liberating compassion',font=SUB_FONT,fill=TWILIGHT,anchor='mm')


SCENES=[
Scene('si01','Essence of Initiation','The transmission of liberating awareness itself.','Dīkṣā','The essential nature of initiation as the heart of Tantric practice.','essence',['essence','initiation','heart'],'overview','essential radiance seal',sc01),
Scene('si02','When Less is More','Brief initiations carry the full power.','Laghu','Shorter initiatory forms are no less effective.','brevity',['brevity','initiation','power'],'foundation','twelve-point minimal ring',sc02),
Scene('si03','Teacher\'s Inner Qualification','The teacher\'s inner state determines initiation power.','Ācārya','Outer credentials matter less than inner qualification.','qualification',['teacher','qualification','inner'],'foundation','inner triangle authority',sc03),
Scene('si04','Initiation at Death\'s Threshold','The final opportunity for liberating transmission.','Antya','At the moment of death, initiation is still possible.','death',['death','threshold','final'],'threshold','concentric death aperture',sc04),
Scene('si05','The Razor that Severs','Initiation cuts the knot of ignorance in one stroke.','Kṣura','A single incisive transmission can bring liberation.','razor',['razor','cut','ignorance'],'process','razor cross lines',sc05),
Scene('si06','Breath\'s Final Journey','Guiding the vital energy at death.','Prāṇa','The breath is guided upward at the final moment.','breath',['breath','journey','death'],'process','breath spiral path',sc06),
Scene('si07','Brahmavidyā for the Dying','Supreme knowledge at the ultimate moment.','Brahmavidyā','Teaching supreme knowledge at the deathbed.','brahmavidya',['knowledge','death','teaching'],'practice','16-ray knowledge field',sc07),
Scene('si08','Weighing the Soul','The scale of merit and grace.','Tulā','The soul is weighed on the scale of grace.','weighing',['soul','scale','weighing'],'threshold','triple concentric scale',sc08),
Scene('si09','Burning Three Impurities','Three impurities consumed by initiatory fire.','Mala','The three malas are destroyed by initiation.','purification',['impurities','fire','purification'],'process','triple flame purification',sc09),
Scene('si10','Visible Proof','Signs of successful initiation appear.','Dṛśya','Outward signs confirm inward transformation.','signs',['visible','proof','signs'],'verification','12-ray proof diagram',sc10),
Scene('si11','Reaching Across Distance','Initiation transcends physical presence.','Dūra','Grace reaches across any distance.','distance',['distance','transcendence','grace'],'transmission','14-point distant ring',sc11),
Scene('si12','The Net of Grace','No one is beyond grace\'s reach.','Anugraha Jāla','The Lord\'s grace is a vast net encompassing all beings.','seal',['grace','net','universal'],'seal','net of grace seal',sc12),
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
    manifest={'project':'Tantrāloka — Special Initiations','source_basis':'Tantrāloka Chapters 18-21: Brief, Dying, Scales, and Absent Initiations.','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'threshold twilight and razor-edge initiation','background':'bone with twilight undertone','materials':['twilight void','razor steel','ember flame','bone parchment','threshold glass']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['si01'],'foundation':['si02','si03'],'threshold':['si04','si08'],'process':['si05','si06','si09'],'practice':['si07'],'verification':['si10'],'transmission':['si11'],'seal':['si12']},'reusability_notes':{'si01':'Use for essence of initiation.','si02':'Use for brief/minimal initiation.','si03':'Use for teacher qualification.','si04':'Use for deathbed initiation.','si05':'Use for razor-cut liberation.','si06':'Use for breath guidance at death.','si07':'Use for Brahmavidyā at death.','si08':'Use for soul-weighing scale.','si09':'Use for burning three impurities.','si10':'Use for signs of initiation.','si11':'Use for distant initiation.','si12':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Special Initiations (Chapters 18-21)

## Aim
This pack visualizes Tantrāloka Chapters 18-21 covering brief initiation (kṣura-dīkṣā), dying initiation, weighing of scales, and absent initiation.

## Core structure
- The essence of initiation is transmission of liberating awareness.
- Short initiations carry the same power as elaborate ones.
- The teacher's inner qualification matters more than outer credentials.
- Initiation is possible even at death's threshold.
- The razor severs ignorance in a single decisive stroke.
- The breath is guided upward at the final moment.
- Brahmavidyā can be imparted to the dying.
- The soul is weighed on the scale of grace and merit.
- Three impurities are consumed by initiatory fire.
- Visible signs confirm successful initiation.
- Initiation transcends physical distance.
- The net of grace encompasses all beings.

## Visual rules
- Twilight and void tones evoke the threshold between life and death.
- Razor imagery suggests incision and precision.
- Ember represents the fire that consumes impurity.
- Bone provides the neutral ground of mortality.
- Death scenes should be numinous, not morbid.

## Style family
Bone field, twilight void, razor steel lines, ember flame, threshold glass.

## Guardrails
- Deathbed initiation is not last-minute bargaining — it is genuine transmission.
- The razor metaphor is about precision, not violence.
- Absent initiation proves grace is not limited by physical presence.
- The net of grace is not sentiment; it is a structural claim about reality.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Special Initiations Pack

## Differentiation
This pack introduces a twilight/razor-edge visual language distinct from ceremonial or maṇḍala palettes.

## New symbols
1. essential radiance seal
2. twelve-point minimal ring
3. inner triangle authority
4. concentric death aperture
5. razor cross lines
6. breath spiral path
7. 16-ray knowledge field
8. triple concentric scale
9. triple flame purification
10. 12-ray proof diagram
11. 14-point distant ring
12. net of grace seal

## New relationships
- initiation → single stroke liberation
- death → threshold opportunity
- teacher → inner qualification
- breath → final journey
- fire → impurity consumption
- grace → universal net

## Material vocabulary
Twilight void, razor steel, ember flame, bone parchment, threshold glass.

## Closing seal
A 22-point twilight/ember ring forming the net of grace (anugraha jāla), demonstrating that no one is beyond reach.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Special Initiations Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'special_initiations_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'special_initiations_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['special_initiations_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'special_initiations_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
