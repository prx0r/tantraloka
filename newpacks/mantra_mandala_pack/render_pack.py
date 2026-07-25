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
SEED = 51409

INDIGO = (55, 65, 120)
INDIGO_DARK = (35, 42, 85)
INDIGO_LIGHT = (110, 120, 175)
ELECTRIC = (100, 180, 220)
ELECTRIC_DARK = (60, 130, 170)
PEARL = (240, 238, 232)
PEARL_LIGHT = (250, 248, 244)
PEARL_DARK = (218, 212, 205)
RESONANCE_GOLD = (205, 165, 80)
GOLD_LIGHT = (240, 205, 130)
SYLLABLE = (180, 120, 170)
SYLLABLE_LIGHT = (215, 170, 210)
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
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(PEARL,dtype=np.float32)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(SYLLABLE_LIGHT,140),outline=rgba(ELECTRIC,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(INDIGO,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(ELECTRIC,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(INDIGO,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(RESONANCE_GOLD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(248,244,238,220),outline=rgba(INDIGO,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INDIGO_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=PEARL_DARK)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=ELECTRIC_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),75,ELECTRIC,105,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(INDIGO,160),width=3)
    for i in range(16):
        a=i*2*math.pi/16
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(ELECTRIC,100),width=1)
    d.text((cx,cy),'मन्त्र',font=DEVA_BIG,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Mantra is living consciousness — it is not a sound but the structure of awareness',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,INDIGO_LIGHT,110,16)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        r=lerp(30,205,smooth(.05+.1*i,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-7,y-7,x+7,y+7),fill=rgba(mix(ELECTRIC,RESONANCE_GOLD,i/5),170),outline=rgba(INDIGO,130),width=2)
    d.text((cx,cy-5),'त्रिक',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The great mantras of Trika: the heart of the threefold goddess tradition',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(RESONANCE_GOLD,150),width=2)
    d.ellipse((cx-185,cy-130,cx+185,cy+130),outline=rgba(SYLLABLE,90),width=1)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(ELECTRIC,130),width=3)
    glow(im,(cx,cy-10),35,GOLD_LIGHT,95,12)
    d.text((cx,cy),'विद्या',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'The three Vidyās: Parā, Parāparā, Aparā — the three levels of sacred knowledge',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,ELECTRIC,100,14)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*195*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*50,cy+math.sin(a)*50-25),(x-20,y+20),(x,y),40),smooth(.04,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(INDIGO,ELECTRIC,i/6),2,85,6)
    d.text((cx,cy-10),'अङ्ग',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Six limbs of mantra: the integrated structure of mantra practice',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(SYLLABLE,160),width=3)
    for i in range(14):
        a=i*2*math.pi/14
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        d.line(((cx,cy),(x,y)),fill=rgba(RESONANCE_GOLD,100),width=1)
    glow(im,(cx,cy-10),30,GOLD_LIGHT,90,10)
    d.text((cx,cy),'ब्रह्म',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Brahmavidyā: the supreme knowledge of mantra as consciousness itself',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),60,ELECTRIC,105,15)
    for i in range(10):
        a=i*2*math.pi/10
        r=lerp(25,200,smooth(.03,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(ELECTRIC,SYLLABLE,i/10),170))
    d.text((cx,cy-10),'वीर्य',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Vitality of mantras: mantras have innate power that awakens with practice',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    d.ellipse((cx-210,cy-150,cx+210,cy+150),outline=rgba(INDIGO,170),width=2)
    for i in range(8):
        a=i*2*math.pi/8
        x=cx+math.cos(a)*195; y=cy+math.sin(a)*140
        d.line(((cx,cy),(x,y)),fill=rgba(RESONANCE_GOLD,110),width=2)
    d.ellipse((cx-70,cy-50,cx+70,cy+50),outline=rgba(ELECTRIC,140),width=2)
    glow(im,(cx,cy-5),30,GOLD_LIGHT,90,10)
    d.text((cx,cy),'मण्डल',font=DEVA_MED,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Sacred geometry of the maṇḍala: the structural map of divine presence',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,INDIGO_LIGHT,110,16)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        r=lerp(25,210,smooth(.03+.08*i,.88,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(RESONANCE_GOLD,ELECTRIC,i/5),170),outline=rgba(INDIGO,120),width=1)
    d.text((cx,cy-10),'परम्परा',font=DEVA_SMALL,fill=INDIGO_DARK,anchor='mm')
    d.text((640,505),'Five traditions, one maṇḍala: diverse lineages share a single sacred structure',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,GOLD_LIGHT,140,20)
    for i in range(24):
        a=i*2*math.pi/24
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(INDIGO,ELECTRIC,i/24),180),outline=rgba(SYLLABLE,120),width=1)
    d.text((cx,cy),'ख',font=DEVA_BIG,fill=INDIGO_DARK,anchor='mm')
    d.text((cx,190),'Lord of the Sky, Khecarī',font=TERM_FONT,fill=RESONANCE_GOLD,anchor='mm')
    d.text((640,505),'Khecarī: the sky-going power of mantra that moves in the void of awareness',font=SUB_FONT,fill=PEARL_DARK,anchor='mm')


SCENES=[
Scene('mm01','Mantra as Living Consciousness','Mantra is the structure of awareness itself.','Mantra','Mantra is not sound but consciousness.','essence',['mantra','consciousness','essence'],'overview','16-ray mantra field',sc01),
Scene('mm02','Great Mantras of Trika','The heart of the threefold goddess.','Trika','The primary mantras of the Trika system.','trika',['trika','mantra','goddess'],'foundation','five-point trika star',sc02),
Scene('mm03','Three Vidyās','Three levels of sacred knowledge.','Vidyā','Parā, Parāparā, and Aparā: the three vidyās.','vidya',['vidyā','three','knowledge'],'foundation','threefold vidyā triangle',sc03),
Scene('mm04','Six Limbs of Mantra','The integrated structure of practice.','Aṅga','Mantra has six limbs that form a complete practice.','limbs',['limbs','six','structure'],'practice','sixfold limb field',sc04),
Scene('mm05','Brahmavidyā','The supreme knowledge of mantra.','Brahmavidyā','Ultimate knowledge is mantra as consciousness.','brahmavidya',['brahmavidyā','knowledge','supreme'],'teaching','14-ray brahmavidyā wheel',sc05),
Scene('mm06','Vitality of Mantras','Mantras awaken with practice.','Vīrya','Mantras have innate power that practice activates.','vitality',['vitality','power','awakening'],'practice','ten-point vitality ring',sc06),
Scene('mm07','Sacred Geometry of Maṇḍala','The structural map of divine presence.','Maṇḍala','Maṇḍala is the geometric architecture of reality.','mandala',['maṇḍala','geometry','sacred'],'practice','eight-ray maṇḍala grid',sc07),
Scene('mm08','Five Traditions One Maṇḍala','Diverse lineages share one structure.','Paramparā','Five streams of tradition share one sacred architecture.','traditions',['traditions','unity','maṇḍala'],'synthesis','five-point unity circle',sc08),
Scene('mm09','Lord of the Sky','The sky-going power of mantra.','Khecarī','Khecarī moves in the void of pure awareness.','seal',['khecarī','sky','void'],'seal','24-point khecarī seal',sc09),
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
    sheet=Image.new('RGB',(4*320,3*180),PEARL)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Mantras & Maṇḍalas','source_basis':'Tantrāloka Chapters 30-31: Mantras (mantra) and Maṇḍalas (maṇḍala).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'resonance indigo and syllable-wheels','background':'pearl with indigo resonance','materials':['resonance indigo','electric syllable-blue','pearl ground','gold mantra-light','syllable violet']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['mm01'],'foundation':['mm02','mm03'],'practice':['mm04','mm06','mm07'],'teaching':['mm05'],'synthesis':['mm08'],'seal':['mm09']},'reusability_notes':{'mm01':'Use for mantra as consciousness.','mm02':'Use for Trika mantras.','mm03':'Use for three Vidyās.','mm04':'Use for six limbs of mantra.','mm05':'Use for Brahmavidyā.','mm06':'Use for mantra vitality.','mm07':'Use for maṇḍala geometry.','mm08':'Use for five traditions one maṇḍala.','mm09':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Mantras & Maṇḍalas (Chapters 30-31)

## Aim
This pack visualizes Tantrāloka Chapters 30-31 on mantras and maṇḍalas, the living structures of sound and geometry.

## Core structure
- Mantra is living consciousness, not a mere phonetic sound.
- The great mantras of Trika embody the three goddesses.
- The three Vidyās (Parā, Parāparā, Aparā) structure sacred knowledge.
- Mantra has six limbs forming a complete practice.
- Brahmavidyā is the supreme knowledge of mantra.
- Mantras have innate vitality that practice awakens.
- The maṇḍala is the sacred geometry of divine presence.
- Five traditions share one underlying maṇḍala structure.
- Khecarī is the sky-going power moving in the void of awareness.

## Visual rules
- Indigo resonance is the dominant color; electric blue provides energy.
- Syllable shapes should suggest sound-forms, not letters.
- The maṇḍala must be geometric, not decorative.
- Khecarī should evoke sky and void, not a flying figure.
- Wheel and circle motifs dominate.

## Style family
Pearl field, resonance indigo, electric syllable-blue, gold mantra-light, syllable violet.

## Guardrails
- Mantra is not magic — it is the structure of consciousness.
- Maṇḍala is not a diagram but a living architecture.
- Khecarī is a state of awareness, not a spatial movement.
- The five traditions are not competing — they share one maṇḍala.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Mantra & Maṇḍala Pack

## Differentiation
This pack introduces syllable-wheel and resonance-indigo visual language distinct from ceremonial or daily-cycle palettes.

## New symbols
1. 16-ray mantra field
2. five-point trika star
3. threefold vidyā triangle
4. sixfold limb field
5. 14-ray brahmavidyā wheel
6. ten-point vitality ring
7. eight-ray maṇḍala grid
8. five-point unity circle
9. 24-point khecarī seal

## New relationships
- mantra → consciousness structure
- Trika → three goddesses
- Vidyās → three knowledge levels
- mantra limbs → complete practice
- maṇḍala → sacred geometry
- traditions → one structure
- khecarī → void awareness

## Material vocabulary
Resonance indigo, electric syllable-blue, pearl ground, gold mantra-light, syllable violet.

## Closing seal
A 24-point indigo/electric ring with the title 'khecarī' — the sky-going power of mantra moving in the void of awareness.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Mantra & Maṇḍala Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'mantra_mandala_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'mantra_mandala_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['mantra_mandala_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'mantra_mandala_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
