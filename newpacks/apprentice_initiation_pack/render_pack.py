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
SEED = 51403

THREAD = (185, 150, 90)
THREAD_DARK = (140, 110, 60)
THREAD_LIGHT = (225, 195, 145)
THREAD_GOLD = (205, 165, 80)
GOLD_LIGHT = (240, 205, 130)
GOLD_DARK = (155, 120, 50)
INDIGO = (55, 65, 120)
INDIGO_DARK = (35, 42, 85)
INDIGO_LIGHT = (110, 120, 175)
SACRED = (80, 55, 65)
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
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array((248, 246, 240),dtype=np.float32)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(INDIGO_LIGHT,140),outline=rgba(THREAD,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(INDIGO,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(THREAD,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(INDIGO,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(THREAD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(246,244,238,220),outline=rgba(INDIGO,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INDIGO_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SACRED)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=THREAD_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),75,THREAD_LIGHT,120,16)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        r=lerp(30,200,smooth(.05+.1*i,.86,t))
        pts=[]
        for j in range(20):
            u=j/19; pts.append((cx+math.cos(a+u*0.5)*r,cy+math.sin(a+u*0.5)*r*0.68))
        if len(pts)>1: line_glow(im,pts,mix(INDIGO,THREAD,i/2),2,80,6)
    d.text((cx,cy),'त्रिशूल',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The triple trident maṇḍala is the geometric foundation of apprentice initiation',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy-20),50,GOLD_LIGHT,110,14)
    for i in range(7):
        a=i*2*math.pi/7
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*180*0.65
        pts=partial(bezier((cx,cy),(x-30,y-20),(x+30,y-20),(x,y),30),smooth(.05,.82,t))
        if len(pts)>1: line_glow(im,pts,mix(THREAD,INDIGO,i/7),3,90,6)
    d.text((cx,cy-5),'पशु',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Esoteric animal sacrifice: the bound soul is offered to reveal its true nature',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x1=cx+math.cos(a)*70; y1=cy+math.sin(a)*50
        x2=cx+math.cos(a)*210; y2=cy+math.sin(a)*210*0.68
        pts=partial(bezier((x1,y1),(lerp(x1,cx,.3),y1-30),(lerp(x2,cx,.3),y2+30),(x2,y2),50),smooth(.05,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(INDIGO,THREAD_GOLD,i/6),2,75,5)
    d.text((cx,cy),'षडध्वन्',font=DEVA_SMALL,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The six paths are deposited in the body, mapping the cosmos onto the initiate',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),65,THREAD_LIGHT,115,15)
    for i in range(36):
        a=-math.pi/2+i*2*math.pi/36
        r=lerp(20,225,smooth(.02,.9,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(INDIGO,THREAD,(i%6)/6),160),outline=rgba(THREAD_GOLD,100),width=1)
    d.text((cx,cy),'तत्त्व',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((cx,190),'36 tattvas',font=TERM_FONT,fill=THREAD,anchor='mm')
    d.text((640,505),'The 36 principles are inscribed on the body as the complete map of reality',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(THREAD,160),width=3)
    d.ellipse((cx-185,cy-130,cx+185,cy+130),outline=rgba(INDIGO,100),width=1)
    for i in range(8):
        a=i*2*math.pi/8
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*120
        d.line(((cx,cy),(x,y)),fill=rgba(THREAD_GOLD,120),width=2)
    d.text((cx,cy-5),'प्रकार',font=DEVA_SMALL,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Initiation has several types, each suited to the capacity of the aspirant',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,GOLD_LIGHT,120,14)
    for i in range(24):
        a=i*2*math.pi/24
        r=160+20*math.sin(i*0.5+t*0.5)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.65
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(INDIGO,THREAD,(i%4)/4),170),outline=rgba(THREAD_GOLD,130),width=1)
    d.text((cx,cy),'मन्त्र',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Mantra is reflective awareness (parāmarśa) — it is not a sound but a mode of consciousness',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-200,cy-145,cx+200,cy+145),outline=rgba(INDIGO,150),width=3)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*135
        d.line(((cx,cy),(x,y)),fill=rgba(THREAD_GOLD,130),width=2)
    glow(im,(cx,cy-15),40,THREAD_LIGHT,100,12)
    d.text((cx,cy),'शक्ति',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The teacher\'s power to purify comes from the lineage, not personal attainment',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(3):
        r=lerp(20,180,smooth(.05+.1*i,.85,t))
        d.ellipse((cx-r,cy-r*0.7,cx+r,cy+r*0.7),outline=rgba(mix(INDIGO,THREAD_GOLD,i/3),120),width=2)
    pts=[(cx-50,cy-20),(cx,cy-80),(cx+50,cy-20)]
    d.polygon(pts,outline=rgba(THREAD,160),fill=rgba((240,235,225),50))
    d.text((cx,cy+10),'ग्रन्थि',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The three knots (granthis) bind the soul and must be cut by initiation',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),70,GOLD_LIGHT,125,16)
    for i in range(36):
        a=-math.pi/2+i*2*math.pi/36
        r=lerp(15,205,smooth(.02,.88,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(THREAD_GOLD,INDIGO,(i%9)/9),165))
    d.text((cx,cy-10),'शुद्धि',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Each tattva is purified in sequence, ascending from earth to śiva-tattva',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),50,THREAD_LIGHT,110,14)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*195*0.65
        flame=partial(bezier((cx,cy),(cx+math.cos(a)*40,cy-40),(x,cy+20),(x,y),40),smooth(.05,.83,t))
        if len(flame)>1: line_glow(im,flame,mix(THREAD_GOLD,INDIGO,i/2),4,105,7)
    d.text((cx,cy),'पाश',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The three fetters (āṇava, māyīya, kārma) are burned by the fire of initiation',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    d.ellipse((cx-140,cy-100,cx+140,cy+100),outline=rgba(THREAD_GOLD,170),width=3)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*120; y=cy+math.sin(a)*85
        if smooth(.05,.8,t)>i*0.08: d.line(((cx,cy),(x,y)),fill=rgba(THREAD,150),width=3)
    d.text((cx,cy),'आहुति',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Three full oblations complete the offering — body, speech, and mind',font=SUB_FONT,fill=SACRED,anchor='mm')

def sc12(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,GOLD_LIGHT,140,20)
    for i in range(20):
        a=i*2*math.pi/20
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(INDIGO,THREAD,i/20),180),outline=rgba(THREAD_GOLD,120),width=1)
    d.text((cx,cy),'दीक्षा',font=DEVA_BIG,fill=INDIGO_DARK,anchor='mm')
    d.text((cx,190),'for benefit vs liberation',font=TERM_FONT,fill=THREAD,anchor='mm')
    d.text((640,505),'Initiation may aim at worldly benefit or complete liberation — both are forms of grace',font=SUB_FONT,fill=SACRED,anchor='mm')


SCENES=[
Scene('ai01','Triple Trident Maṇḍala','The geometric foundation of apprentice initiation.','Triśūla Maṇḍala','The triple trident forms the maṇḍala for apprentice initiation.','mandala',['trident','mandala','apprentice'],'overview','triple trident rays',sc01),
Scene('ai02','Esoteric Animal Sacrifice','The bound soul is offered to reveal true nature.','Paśu','Animal sacrifice as metaphor for offering the bound self.','sacrifice',['animal','sacrifice','paśu'],'foundation','sevenfold offering path',sc02),
Scene('ai03','Six Paths Deposition','The cosmos is mapped onto the initiate\'s body.','Ṣaḍadhvan','The six paths (adhvans) are ritually deposited in the body.','deposition',['six paths','deposition','body'],'foundation','six-path deposition rays',sc03),
Scene('ai04','36 Principles on the Body','The complete map of reality inscribed on the body.','Tattva','The 36 tattvas are placed on the body as a living maṇḍala.','tattva',['tattva','36','principles'],'foundation','36-point body ring',sc04),
Scene('ai05','Initiation Types','Each type suits the capacity of the aspirant.','Prakāra','Multiple initiation types exist for different capacities.','types',['types','initiation','varieties'],'practice','eight-type radial diagram',sc05),
Scene('ai06','Mantra as Reflective Awareness','Mantra is a mode of consciousness, not a mere sound.','Parāmarśa','Mantra is the reflective power of consciousness itself.','mantra',['mantra','reflection','awareness'],'practice','24-node mantra field',sc06),
Scene('ai07','Teacher\'s Power to Purify','The lineage transmits through the teacher.','Śakti','The teacher purifies through the power of the lineage.','transmission',['teacher','power','purification'],'transmission','five-radiance teacher seal',sc07),
Scene('ai08','Three Knots','The three granthis binding the soul.','Granthi','The three knots (āṇava, māyīya, kārma) are cut by initiation.','knots',['knots','granthi','binding'],'process','three-knot triangle',sc08),
Scene('ai09','Tattva Purification','Each principle purified in ascending order.','Śuddhi','The 36 tattvas are purified sequentially from earth to śiva.','purification',['tattva','purification','ascension'],'process','36-point purification ring',sc09),
Scene('ai10','Burning the Fetters','The three bonds are consumed by initiation fire.','Pāśa','Three fetters are burned by the fire of liberating knowledge.','burning',['fetters','burning','liberation'],'process','triple flame binding',sc10),
Scene('ai11','Three Full Oblations','Body, speech, and mind offered completely.','Āhuti','Three oblations complete the inner sacrifice.','oblation',['oblations','offering','completion'],'practice','triple oblation circle',sc11),
Scene('ai12','Initiation for Benefit vs Liberation','Grace takes different forms for different aims.','Dīkṣā','Initiation may seek worldly benefit or ultimate liberation.','seal',['benefit','liberation','duality'],'seal','duality synthesis seal',sc12),
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
    sheet=Image.new('RGB',(4*320,3*180),(248,246,240))
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Apprentice Initiation','source_basis':'Tantrāloka Chapters 16-17: Apprentice Initiation (śaiṣya dīkṣā).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'maṇḍala geometry and apprentice initiation','background':'warm cream field','materials':['gold thread','indigo maṇḍala ink','sacred geometry','thread binding','gemstone light']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['ai01'],'foundation':['ai02','ai03','ai04'],'practice':['ai05','ai06','ai11'],'transmission':['ai07'],'process':['ai08','ai09','ai10'],'seal':['ai12']},'reusability_notes':{'ai01':'Use for trident maṇḍala.','ai02':'Use for animal sacrifice metaphor.','ai03':'Use for six paths deposition.','ai04':'Use for 36 tattvas body map.','ai05':'Use for initiation types.','ai06':'Use for mantra as parāmarśa.','ai07':'Use for teacher\'s purification power.','ai08':'Use for three knots.','ai09':'Use for tattva purification sequence.','ai10':'Use for burning fetters.','ai11':'Use for three oblations.','ai12':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Apprentice Initiation (Chapters 16-17)

## Aim
This pack visualizes Tantrāloka Chapters 16-17 on śaiṣya dīkṣā, the initiation of the apprentice (disciple).

## Core structure
- The triple trident maṇḍala is the geometric foundation of the initiation.
- Esoteric animal sacrifice: the bound soul (paśu) is offered up to reveal its true nature.
- The six paths (adhvans) are deposited in the initiate's body.
- The 36 tattvas are inscribed on the body as a complete reality map.
- Various initiation types address different aspirant capacities.
- Mantra is parāmarśa (reflective awareness), not a mere phonetic vibration.
- The teacher's power to purify flows through lineage transmission.
- Three knots (granthis) bind the soul until cut by initiation.
- Each tattva is purified sequentially from earth to śiva-tattva.
- Three fetters (pāśas) are consumed by the fire of liberating knowledge.
- Three full oblations complete the offering: body, speech, mind.
- Initiation may aim at worldly benefit or ultimate liberation.

## Visual rules
- Maṇḍala geometry is primary — use concentric circular and radial forms.
- Gold thread and indigo ink are the defining material pair.
- The body map must be schematic, not anatomical.
- Knots should appear as binding energy, not rope.
- The trident is a geometric figure, not a weapon.

## Style family
Warm cream field, gold thread, indigo maṇḍala ink, sacred geometry lines, gemstone accent points.

## Guardrails
- Animal sacrifice is entirely esoteric/metaphorical, never literal.
- The 36 tattvas are not a numbered list but a living hierarchy of principles.
- Mantra is not phonetic magic; it is the structure of consciousness.
- Benefit-oriented initiation is not inferior, merely different in aim.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Apprentice Initiation Pack

## Differentiation
This pack introduces maṇḍala geometry as the primary visual language, distinct from threshold or ceremonial palettes.

## New symbols
1. triple trident ray field
2. sevenfold offering path
3. six-path deposition rays
4. 36-point body ring
5. eight-type radial diagram
6. 24-node mantra field
7. five-radiance teacher seal
8. three-knot triangle
9. 36-point purification ring
10. triple flame binding
11. triple oblation circle
12. duality synthesis seal

## New relationships
- trident maṇḍala → initiation foundation
- body → tattva map
- mantra → reflective awareness
- teacher → lineage power
- knots → binding → cutting
- fetters → fire → liberation

## Material vocabulary
Gold thread, indigo maṇḍala ink, sacred geometry, thread binding, gemstone light.

## Closing seal
A 20-point synthesis ring of indigo and gold with the central title 'dīkṣā' — initiation for both worlds.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Apprentice Initiation Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'apprentice_initiation_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'apprentice_initiation_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['apprentice_initiation_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'apprentice_initiation_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
