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
SEED = 51406

BONE = (235, 225, 215)
BONE_DARK = (200, 188, 175)
SMOKE = (130, 125, 120)
SMOKE_LIGHT = (175, 170, 165)
SMOKE_DARK = (80, 75, 70)
IVORY = (250, 245, 235)
IVORY_DARK = (225, 218, 205)
THREAD = (185, 155, 115)
THREAD_DARK = (140, 115, 80)
THREAD_LIGHT = (220, 195, 160)
EMBER = (200, 100, 55)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(THREAD_LIGHT,140),outline=rgba(SMOKE,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(BONE,110),outline=rgba(THREAD,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(THREAD,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(SMOKE,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(THREAD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(248,243,235,220),outline=rgba(SMOKE,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=SMOKE_DARK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SMOKE)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=THREAD_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),75,THREAD_LIGHT,105,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(SMOKE,160),width=3)
    d.ellipse((cx-195,cy-135,cx+195,cy+135),outline=rgba(THREAD,90),width=1)
    for i in range(8):
        a=i*2*math.pi/8
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        d.line(((cx,cy),(x,y)),fill=rgba(BONE_DARK,110),width=2)
    d.text((cx,cy),'अन्त्य',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((640,505),'The final passage: rites for the departed ensure a smooth transition beyond death',font=SUB_FONT,fill=SMOKE,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(THREAD,150),width=2)
    for i in range(9):
        a=i*2*math.pi/9
        r=lerp(20,170,smooth(.05+.08*i,.84,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SMOKE,THREAD,i/9),160),outline=rgba(BONE_DARK,120),width=1)
    glow(im,(cx,cy-10),35,THREAD_LIGHT,95,12)
    d.text((cx,cy),'पात्र',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((640,505),'The qualified recipient: rites are effective only for those who receive them',font=SUB_FONT,fill=SMOKE,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),65,THREAD_LIGHT,110,16)
    for i in range(12):
        a=i*2*math.pi/12
        r=lerp(20,205,smooth(.02,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(THREAD,BONE,i/12),170),outline=rgba(SMOKE,110),width=1)
    d.text((cx,cy-10),'मृत',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((640,505),'Liberating the dead: śrāddha rites can elevate the consciousness of the departed',font=SUB_FONT,fill=SMOKE,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(SMOKE,160),width=3)
    d.ellipse((cx-185,cy-130,cx+185,cy+130),outline=rgba(THREAD,100),width=1)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(THREAD_LIGHT,130),width=2)
    d.text((cx,cy-5),'पिण्ड',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((640,505),'Feeding the ancestors: piṇḍadāna nourishes and frees the lineage of the departed',font=SUB_FONT,fill=SMOKE,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),50,THREAD_LIGHT,100,14)
    d.line((cx-200,cy,cx+200,cy),fill=rgba(SMOKE,140),width=3)
    d.line((cx,cy-100,cx,cy+100),fill=rgba(SMOKE,140),width=3)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*60; y=cy+math.sin(a)*42
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(THREAD,150),outline=rgba(THREAD_DARK,180),width=2)
    d.text((cx,cy+115),'नित्य',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((640,505),'Identifying the fettered with the eternal: the root mistake that binds the soul',font=SUB_FONT,fill=SMOKE,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),55,THREAD_LIGHT,105,15)
    for i in range(10):
        a=-math.pi/2+i*2*math.pi/10
        r=lerp(30,200,smooth(.03,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(BONE,THREAD,i/10),165),outline=rgba(SMOKE,100),width=1)
    for i in range(7):
        a=-math.pi/2+i*2*math.pi/7
        x=cx+math.cos(a)*150; y=cy+math.sin(a)*150*0.68
        d.line(((cx,cy),(x,y)),fill=rgba(THREAD_LIGHT,100),width=1)
    d.text((cx,cy-10),'नाडी',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((640,505),'Breath channels (nāḍīs): the subtle pathways through which consciousness travels',font=SUB_FONT,fill=SMOKE,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),80,THREAD_LIGHT,130,20)
    for i in range(16):
        a=i*2*math.pi/16
        r=lerp(25,220,smooth(.02,.9,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SMOKE,THREAD,i/16),180),outline=rgba(BONE_DARK,120),width=1)
    d.text((cx,cy),'भुक्ति',font=DEVA_MED,fill=SMOKE_DARK,anchor='mm')
    d.text((cx,190),'mukti',font=TERM_FONT,fill=THREAD,anchor='mm')
    d.text((640,505),'Bestowing enjoyment (bhukti) and liberation (mukti) through ancestral rites',font=SUB_FONT,fill=SMOKE,anchor='mm')


SCENES=[
Scene('dr01','Final Passage','Rites for a smooth transition beyond death.','Antya','Funerary rites guide the departed soul to its next station.','funerary',['death','passage','rites'],'overview','eight-ray passage seal',sc01),
Scene('dr02','Qualified Recipient','Rites are effective only for the receptive.','Pātra','The effectiveness of rites depends on the recipient\'s capacity.','recipient',['qualified','recipient','receptivity'],'foundation','nine-point recipient ring',sc02),
Scene('dr03','Liberating the Dead','Śrāddha elevates the departed.','Mṛta','Funerary rites can liberate the consciousness of the dead.','liberation',['death','liberation','śrāddha'],'process','12-point liberation ring',sc03),
Scene('dr04','Feeding the Ancestors','Piṇḍadāna nourishes the lineage.','Piṇḍa','Offering food (piṇḍa) to ancestors sustains and frees them.','ancestors',['ancestors','offering','piṇḍa'],'practice','sixfold offering diagram',sc04),
Scene('dr05','Identifying Fettered with Eternal','The root mistake binding the soul.','Nitya','Confusing the finite self with the eternal is the primal error.','error',['error','identification','eternal'],'teaching','crossed identification grid',sc05),
Scene('dr06','Breath Channels','Subtle pathways of consciousness.','Nāḍī','The nāḍīs are the channels through which prāṇa and consciousness flow.','nadis',['nāḍī','channels','breath'],'subtle','ten-channel nāḍī field',sc06),
Scene('dr07','Bestowing Enjoyment and Liberation','Both worldly and ultimate gifts.','Bhukti Mukti','Ancestral rites bestow both enjoyment and liberation.','seal',['enjoyment','liberation','seal'],'seal','duality bestowal seal',sc07),
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
    manifest={'project':'Tantrāloka — Departed Rites','source_basis':'Tantrāloka Chapters 24-25: Funerary Rites (antyakriyā) & Ancestral Rites (śrāddha).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'funerary and ancestral rites','background':'warm ivory with bone undertone','materials':['bone','smoke veil','ivory vessels','lineage thread','ember offering']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['dr01'],'foundation':['dr02'],'process':['dr03'],'practice':['dr04'],'teaching':['dr05'],'subtle':['dr06'],'seal':['dr07']},'reusability_notes':{'dr01':'Use for funerary rites or final passage.','dr02':'Use for qualified recipient.','dr03':'Use for liberating the dead.','dr04':'Use for feeding ancestors or piṇḍa.','dr05':'Use for identifying finite with eternal.','dr06':'Use for nāḍī channels.','dr07':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Departed Rites (Chapters 24-25)

## Aim
This pack visualizes Tantrāloka Chapters 24-25 on funerary rites (antyakriyā) and ancestral rites (śrāddha).

## Core structure
- Funerary rites guide the departed through the transition after death.
- The recipient must be qualified for rites to be effective.
- Śrāddha can liberate the consciousness of the dead.
- Feeding the ancestors (piṇḍadāna) sustains and frees the lineage.
- The root error is identifying the fettered self with the eternal.
- Breath channels (nāḍīs) are the pathways of subtle consciousness.
- Ancestral rites bestow both worldly enjoyment (bhukti) and liberation (mukti).

## Visual rules
- Bone and smoke tones evoke the liminal space between worlds.
- Thread imagery suggests the continuities of lineage.
- Ivory provides a pure, funerary-appropriate ground.
- Departed souls should be suggested geometrically, not as ghosts.
- Ancestral rites feel continuous, not mournful.

## Style family
Ivory field, bone structures, smoke veil, lineage thread, ember offering.

## Guardrails
- Funerary rites are about guidance, not manipulation of the dead.
- Ancestral rites are offerings, not payments.
- The nāḍī system is subtle anatomy, not physical nerves.
- Bhukti and mukti are not opposed — rites bestow both.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Departed Rites Pack

## Differentiation
This pack introduces a bone/smoke/lineage-thread visual language distinct from ceremonial or threshold palettes.

## New symbols
1. eight-ray passage seal
2. nine-point recipient ring
3. 12-point liberation ring
4. sixfold offering diagram
5. crossed identification grid
6. ten-channel nāḍī field
7. duality bestowal seal

## New relationships
- death → transition passage
- recipient → qualification
- śrāddha → liberation of dead
- piṇḍa → feeding ancestors
- identification error → bondage
- nāḍīs → consciousness pathways
- bhukti ↔ mukti → both bestowed

## Material vocabulary
Bone, smoke veil, ivory vessels, lineage thread, ember offering.

## Closing seal
A 16-point smoke/thread ring with the paired terms 'bhukti' and 'mukti' — bestowing enjoyment and liberation through ancestral rites.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Departed Rites Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'departed_rites_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'departed_rites_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['departed_rites_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'departed_rites_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
