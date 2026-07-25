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
SEED = 51411

CRYSTAL = (248, 246, 242)
CRYSTAL_LIGHT = (252, 251, 248)
CRYSTAL_DARK = (228, 224, 218)
CRYSTAL_GOLD = (205, 165, 80)
GOLD_LIGHT = (240, 205, 130)
GOLD_DARK = (155, 120, 50)
VIOLET = (130, 100, 180)
VIOLET_LIGHT = (175, 150, 215)
VIOLET_DARK = (85, 60, 130)
MIRROR = (200, 210, 225)
MIRROR_DARK = (140, 152, 175)
CERTAINTY = (180, 200, 230)
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
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(CRYSTAL,dtype=np.float32)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(VIOLET_LIGHT,140),outline=rgba(MIRROR,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(VIOLET,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(CRYSTAL_GOLD,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(VIOLET,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(CRYSTAL_GOLD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(246,244,240,220),outline=rgba(VIOLET,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=VIOLET_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=VIOLET)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),75,VIOLET_LIGHT,105,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(VIOLET,150),width=3)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(CRYSTAL_GOLD,120),width=2)
    d.text((cx,cy),'उपाय',font=DEVA_MED,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'The three upāyas: divine, empowered, and individual — three doors to the same reality',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,MIRROR,105,16)
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(CRYSTAL_GOLD,150),width=2)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        r=lerp(25,200,smooth(.05+.08*i,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(CRYSTAL_GOLD,VIOLET,i/7),170),outline=rgba(MIRROR_DARK,120),width=1)
    d.text((cx,cy-5),'गहन',font=DEVA_MED,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'Penetrating deeper: each upāya opens into greater subtlety of awareness',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(VIOLET,160),width=3)
    d.ellipse((cx-175,cy-120,cx+175,cy+120),outline=rgba(CRYSTAL_GOLD,80),width=1)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(MIRROR,120),width=2)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,85,10)
    d.text((cx,cy),'लadder',font=DEVA_MED,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'Abandoning the ladder: the means are left behind once the goal is reached',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,GOLD_LIGHT,110,16)
    d.ellipse((cx-140,cy-100,cx+140,cy+100),outline=rgba(MIRROR,140),width=2)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*130; y=cy+math.sin(a)*92
        d.line(((cx,cy),(x,y)),fill=rgba(VIOLET_LIGHT,100),width=1)
    d.text((cx,cy),'भैरव',font=DEVA_BIG,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'Bhairava state: the terrifying freedom beyond all conceptual frameworks',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(CRYSTAL_GOLD,160),width=2)
    for i in range(12):
        a=i*2*math.pi/12
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        d.line(((cx,cy),(x,y)),fill=rgba(CERTAINTY,100),width=1)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,90,10)
    d.text((cx,cy),'प्रसिद्धि',font=DEVA_SMALL,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'What makes knowledge certain (prasiddhi): the self-evident nature of awareness',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),55,VIOLET_LIGHT,100,14)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        r=lerp(30,195,smooth(.05+.1*i,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(mix(CRYSTAL_GOLD,VIOLET,i/3),170),outline=rgba(MIRROR,130),width=2)
    d.text((cx,cy-10),'परम्परा',font=DEVA_SMALL,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'Tradition as foundation: knowledge is transmitted through unbroken lineage',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(VIOLET,160),width=3)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(CRYSTAL_GOLD,110),width=2)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,85,10)
    d.text((cx,cy),'सदाशिव',font=DEVA_SMALL,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'Five faces of Sadāśiva: Īśāna, Tatpuruṣa, Aghora, Vāmadeva, Sadyojāta',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,GOLD_LIGHT,110,16)
    for i in range(8):
        a=i*2*math.pi/8
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*195*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*60,cy+math.sin(a)*60-25),(x-20,y+20),(x,y),40),smooth(.04,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(VIOLET,CRYSTAL_GOLD,i/8),2,80,6)
    d.text((cx,cy-10),'एक',font=DEVA_MED,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'One tradition, many paths: diversity of approaches within a single transmission',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),60,MIRROR,105,15)
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(VIOLET,150),width=2)
    for i in range(9):
        a=i*2*math.pi/9
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.78,t)>i*0.06: d.line(((cx,cy),(x,y)),fill=rgba(CRYSTAL_GOLD,110),width=2)
    d.text((cx,cy),'कुल',font=DEVA_MED,fill=VIOLET_DARK,anchor='mm')
    d.text((640,505),'Trika as Kula: the triad is the family of powers that constitutes all reality',font=SUB_FONT,fill=VIOLET,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,GOLD_LIGHT,140,20)
    for i in range(20):
        a=i*2*math.pi/20
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(VIOLET,CRYSTAL_GOLD,i/20),180),outline=rgba(MIRROR,120),width=1)
    d.text((cx,cy),'शैव',font=DEVA_BIG,fill=VIOLET_DARK,anchor='mm')
    d.text((cx,190),'complete',font=TERM_FONT,fill=CRYSTAL_GOLD,anchor='mm')
    d.text((640,505),'Why Śaiva is complete: the non-dual Śaiva tradition encompasses all paths',font=SUB_FONT,fill=VIOLET,anchor='mm')


SCENES=[
Scene('ps01','Three Upāyas','Three doors to the same reality.','Upāya','The divine (śāmbhava), empowered (śākta), and individual (āṇava) upāyas.','upaya',['upāya','three','means'],'overview','threefold upāya triangle',sc01),
Scene('ps02','Penetrating Deeper','Each upāya opens into greater subtlety.','Gahana','The means are progressively more subtle.','deepening',['deepening','upāya','subtlety'],'foundation','seven-point penetration ring',sc02),
Scene('ps03','Abandoning the Ladder','Means left behind at the goal.','Sopāna','Once the goal is reached, the means are transcended.','transcendence',['ladder','abandon','transcendence'],'foundation','fivefold ladder abandonment',sc03),
Scene('ps04','Bhairava State','The terrifying freedom beyond frameworks.','Bhairava','Bhairava consciousness is the state beyond all concepts.','bhairava',['bhairava','freedom','non-conceptual'],'state','ten-ray bhairava circle',sc04),
Scene('ps05','What Makes Knowledge Certain','Prasiddhi: self-evident awareness.','Prasiddhi','Certainty comes from direct, self-validating awareness.','certainty',['certainty','knowledge','prasiddhi'],'teaching','twelve-ray certainty wheel',sc05),
Scene('ps06','Tradition as Foundation','Unbroken lineage of transmission.','Paramparā','Knowledge requires an unbroken chain of realized teachers.','tradition',['tradition','lineage','foundation'],'foundation','triple lineage seal',sc06),
Scene('ps07','Five Faces of Sadāśiva','The five aspects of the eternal.','Sadāśiva','Sadāśiva\'s five faces represent cosmic functions.','sadasiva',['sadāśiva','five','faces'],'cosmic','five-faced pentagon',sc07),
Scene('ps08','One Tradition Many Paths','Diversity within a single transmission.','Eka Paramparā','The one tradition accommodates many approaches.','diversity',['tradition','paths','diversity'],'synthesis','eight-fold path ring',sc08),
Scene('ps09','Trika as Kula','The triad as the family of powers.','Kula','Trika is kula — the family of Śiva, Śakti, and the bound soul.','trika',['trika','kula','family'],'synthesis','nine-point kula wheel',sc09),
Scene('ps10','Why Śaiva is Complete','Non-dual tradition encompasses all paths.','Śaiva','The Śaiva tradition is complete because it includes all approaches.','seal',['śaiva','complete','encompassing'],'seal','Śaiva completeness seal',sc10),
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
    sheet=Image.new('RGB',(4*320,3*180),CRYSTAL)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Philosophical Synthesis','source_basis':'Tantrāloka Chapters 34-35: Entry into Scripture (śāstra prakāśa) & Encounter of Scriptures (śāstra samāgama).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'crystalline certainty and mirror-of-truth','background':'crystal white with violet clarity','materials':['crystal white','gold certainty','violet transcendence','mirror glass','prasiddhi light']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['ps01'],'foundation':['ps02','ps03','ps06'],'state':['ps04'],'teaching':['ps05'],'cosmic':['ps07'],'synthesis':['ps08','ps09'],'seal':['ps10']},'reusability_notes':{'ps01':'Use for three upāyas.','ps02':'Use for penetration/deepening.','ps03':'Use for abandoning the ladder.','ps04':'Use for Bhairava state.','ps05':'Use for prasiddhi.','ps06':'Use for tradition as foundation.','ps07':'Use for five faces.','ps08':'Use for one tradition many paths.','ps09':'Use for Trika as Kula.','ps10':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Philosophical Synthesis (Chapters 34-35)

## Aim
This pack visualizes Tantrāloka Chapters 34-35 on the entry into scripture and the encounter of traditions.

## Core structure
- Three upāyas: śāmbhava (divine), śākta (empowered), āṇava (individual).
- Each upāya opens into greater subtlety of awareness.
- The means (upāya) are abandoned once the goal is reached.
- Bhairava is the state beyond all conceptual frameworks.
- Certainty (prasiddhi) comes from self-validating awareness.
- Tradition provides the foundation through unbroken lineage.
- Five faces of Sadāśiva represent cosmic functions.
- One tradition accommodates many paths.
- Trika is kula: the family of Śiva, Śakti, and the bound soul.
- The Śaiva tradition is complete, encompassing all approaches.

## Visual rules
- Crystal white and violet convey clarity and transcendence.
- Mirror imagery suggests the self-reflective nature of certainty.
- Gold provides the thread of tradition and realization.
- Bhairava should suggest vastness, not terror.
- The ladder is a geometric structure, not a literal object.

## Style family
Crystal white, gold certainty, violet transcendence, mirror glass, prasiddhi light.

## Guardrails
- Upāyas are not stages — they are simultaneous doors.
- Bhairava is not a wrathful deity but a state of awareness.
- Tradition is foundation, not restriction.
- Completeness of Śaiva is about inclusivity, not superiority.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Philosophical Synthesis Pack

## Differentiation
This pack introduces a crystalline mirror-of-certainty visual language distinct from gesture or mantra palettes.

## New symbols
1. threefold upāya triangle
2. seven-point penetration ring
3. fivefold ladder abandonment
4. ten-ray bhairava circle
5. twelve-ray certainty wheel
6. triple lineage seal
7. five-faced pentagon
8. eight-fold path ring
9. nine-point kula wheel
10. Śaiva completeness seal

## New relationships
- upāyas → three doors
- penetration → greater subtlety
- means → abandonment at goal
- Bhairava → non-conceptual freedom
- prasiddhi → self-certainty
- tradition → lineage foundation
- Śaiva → completeness

## Material vocabulary
Crystal white, gold certainty, violet transcendence, mirror glass, prasiddhi light.

## Closing seal
A 20-point violet/gold ring with the title 'śaiva' — the non-dual Śaiva tradition as the complete synthesis of all paths.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Philosophical Synthesis Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'philosophical_synthesis_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'philosophical_synthesis_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['philosophical_synthesis_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'philosophical_synthesis_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
