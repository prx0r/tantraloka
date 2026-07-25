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
SEED = 51407

PEARL = (242, 238, 230)
PEARL_LIGHT = (250, 247, 240)
PEARL_DARK = (215, 210, 200)
SAFFRON = (215, 155, 70)
SAFFRON_LIGHT = (240, 195, 120)
SAFFRON_DARK = (170, 120, 50)
PARCHMENT = (243, 237, 226)
PARCHMENT_DARK = (220, 212, 200)
DAY = (140, 165, 175)
DAY_LIGHT = (185, 205, 215)
NIGHT = (80, 70, 90)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(DAY_LIGHT,140),outline=rgba(SAFFRON,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(SAFFRON_LIGHT,110),outline=rgba(NIGHT,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(SAFFRON,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(NIGHT,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(SAFFRON,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(248,244,235,220),outline=rgba(NIGHT,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=NIGHT)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=PARCHMENT_DARK)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=SAFFRON_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    glow(im,(cx,cy),75,SAFFRON_LIGHT,110,18)
    d.ellipse((cx-200,cy-140,cx+200,cy+140),outline=rgba(SAFFRON,150),width=3)
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8+t*0.02
        r=lerp(40,190,smooth(.05,.85,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SAFFRON,DAY,i/8),170),outline=rgba(SAFFRON_DARK,120),width=1)
    d.text((cx,cy),'नित्य',font=DEVA_MED,fill=NIGHT,anchor='mm')
    d.text((640,505),'Daily practice after initiation: the steady rhythm of niṭya pūjā',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(DAY,140),width=2)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        pts=partial(bezier((cx,cy),(x-20,y-15),(x+20,y-15),(x,y),30),smooth(.05,.8,t))
        if len(pts)>1: line_glow(im,pts,mix(SAFFRON,DAY,i/6),2,85,6)
    glow(im,(cx,cy-10),35,SAFFRON_LIGHT,95,12)
    d.text((cx,cy),'मुख',font=DEVA_MED,fill=NIGHT,anchor='mm')
    d.text((640,505),'The living word: oral mantra transmission carries the power of living presence',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),65,SAFFRON_LIGHT,105,16)
    for i in range(12):
        a=i*2*math.pi/12
        r=lerp(20,200,smooth(.02,.86,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(DAY,SAFFRON,i/12),170))
    d.text((cx,cy-10),'सन्ध्या',font=DEVA_MED,fill=NIGHT,anchor='mm')
    d.text((640,505),'Worship at the junctures: sandhyā rites mark the sacred transitions of the day',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(SAFFRON,160),width=2)
    d.ellipse((cx-65,cy-45,cx+65,cy+45),outline=rgba(DAY,130),width=2)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*120
        d.line(((cx,cy),(x,y)),fill=rgba(SAFFRON_LIGHT,120),width=2)
    glow(im,(cx,cy-5),30,SAFFRON_LIGHT,90,10)
    d.text((cx,cy),'आवाहन',font=DEVA_SMALL,fill=NIGHT,anchor='mm')
    d.text((640,505),'Invocation and libation: calling the presence and making the offering',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),55,SAFFRON_LIGHT,100,14)
    for i in range(10):
        a=i*2*math.pi/10
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*185*0.65
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*50,cy+math.sin(a)*50-25),(x-20,y+20),(x,y),40),smooth(.04,.84,t))
        if len(pts)>1: line_glow(im,pts,mix(SAFFRON,DAY,i/10),2,80,6)
    d.text((cx,cy-10),'अन्तर्',font=DEVA_MED,fill=NIGHT,anchor='mm')
    d.text((640,505),'Inner worship: mental pūjā is superior to external ritual',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-180,cy-125,cx+180,cy+125),outline=rgba(NIGHT,150),width=3)
    d.ellipse((cx-175,cy-120,cx+175,cy+120),outline=rgba(SAFFRON,90),width=1)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*115
        if smooth(.05,.8,t)>i*0.1: d.line(((cx,cy),(x,y)),fill=rgba(DAY,130),width=2)
    glow(im,(cx,cy-10),30,SAFFRON_LIGHT,90,10)
    d.text((cx,cy),'भुक्ति',font=DEVA_SMALL,fill=NIGHT,anchor='mm')
    d.text((640,505),'Rites for worldly benefit vs. rites for liberation: both have their place',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),70,SAFFRON_LIGHT,115,16)
    for i in range(9):
        a=-math.pi/2+i*2*math.pi/9
        r=lerp(30,210,smooth(.03,.88,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SAFFRON,PEARL,i/9),170),outline=rgba(DAY,110),width=1)
    d.text((cx,cy),'लिङ्ग',font=DEVA_BIG,fill=NIGHT,anchor='mm')
    d.text((640,505),'Many forms of liṅga: the supreme is worshipped in countless manifestations',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.ellipse((cx-190,cy-135,cx+190,cy+135),outline=rgba(SAFFRON,160),width=3)
    for i in range(12):
        a=i*2*math.pi/12
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*125
        d.line(((cx,cy),(x,y)),fill=rgba(SAFFRON_LIGHT,100),width=1)
    d.text((cx,cy-5),'स्थापन',font=DEVA_SMALL,fill=NIGHT,anchor='mm')
    d.text((640,505),'Installing the divine: bringing the presence into the image through mantra',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),50,SAFFRON_LIGHT,100,14)
    for i in range(24):
        a=i*2*math.pi/24
        r=160+16*math.sin(i*0.7+t*0.4)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.65
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(DAY,SAFFRON,(i%4)/4),165))
    d.ellipse((cx-25,cy-18,cx+25,cy+18),outline=rgba(SAFFRON,180),width=2)
    d.text((cx,cy+5),'जप',font=DEVA_MED,fill=NIGHT,anchor='mm')
    d.text((640,505),'Rosary and jar: the japamālā and kalaśa are tools of concentrated practice',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy),85,SAFFRON_LIGHT,140,20)
    for i in range(20):
        a=i*2*math.pi/20
        r=lerp(25,220,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(NIGHT,SAFFRON,i/20),180),outline=rgba(DAY,120),width=1)
    d.text((cx,cy),'पूजा',font=DEVA_BIG,fill=NIGHT,anchor='mm')
    d.text((cx,190),'inner and outer',font=TERM_FONT,fill=SAFFRON,anchor='mm')
    d.text((640,505),'Inner and outer worship unite in the final recognition that all is offering',font=SUB_FONT,fill=PARCHMENT_DARK,anchor='mm')


SCENES=[
Scene('do01','Daily Practice After Initiation','The steady rhythm of niṭya pūjā.','Nitya','Regular daily practice sustains the initiatory transformation.','daily',['daily','practice','nitya'],'overview','eight-point daily rhythm',sc01),
Scene('do02','Living Word','Oral mantra transmission.','Mukha','Mantra transmitted orally carries living presence.','oral',['mantra','oral','transmission'],'foundation','sixfold oral emission',sc02),
Scene('do03','Worship at Junctures','Sandhyā rites mark sacred transitions.','Sandhyā','Worship at dawn, noon, and dusk aligns with cosmic rhythms.','junctures',['sandhyā','junctures','transitions'],'foundation','twelve-point sandhyā ring',sc03),
Scene('do04','Invocation and Libation','Calling the presence and making the offering.','Āvāhana','Invoking the deity and offering libation.','invocation',['invocation','libation','offering'],'practice','five-ray invocation seal',sc04),
Scene('do05','Inner Worship','Mental pūjā surpasses external ritual.','Antar','Inner worship is superior to external ritual alone.','inner',['inner','worship','mental'],'practice','ten-ray antar field',sc05),
Scene('do06','Rites for Benefit vs Liberation','Both worldly and ultimate aims served.','Bhukti Mukti','Rites can aim at worldly benefit or ultimate liberation.','aims',['benefit','liberation','aims'],'teaching','dual-aim hexagram',sc06),
Scene('do07','Many Forms of Liṅga','Countless manifestations of the supreme.','Liṅga','Liṅga worship recognizes form as a support for the formless.','linga',['liṅga','worship','form'],'practice','nine-point liṅga ring',sc07),
Scene('do08','Installing the Divine','Bringing presence into the image.','Sthāpana','Prāṇa pratiṣṭhā installs divine presence into the image.','installation',['installation','image','presence'],'practice','twelve-ray installation',sc08),
Scene('do09','Rosary and Jar','Tools of concentrated practice.','Japa','The japamālā and kalaśa support meditative practice.','tools',['rosary','jar','tools'],'practice','24-bead rosary circle',sc09),
Scene('do10','Inner and Outer Worship','All is offering.','Pūjā','The final synthesis: inner and outer worship as one act.','seal',['inner','outer','synthesis'],'seal','inner-outer synthesis seal',sc10),
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
    manifest={'project':'Tantrāloka — Daily Observance & Liṅga Worship','source_basis':'Tantrāloka Chapters 26-27: Daily Practice (niṭya vidhi) & Liṅga Worship (liṅgapūjā).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'daily-cycle observance and liṅga worship','background':'dawn pearl with saffron warmth','materials':['pearl dawn','saffron robe','parchment','day sky','night ink']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['do01'],'foundation':['do02','do03'],'practice':['do04','do05','do07','do08','do09'],'teaching':['do06'],'seal':['do10']},'reusability_notes':{'do01':'Use for daily practice or nitya vidhi.','do02':'Use for oral mantra transmission.','do03':'Use for sandhyā worship.','do04':'Use for invocation and libation.','do05':'Use for inner worship.','do06':'Use for bhukti/mukti rites.','do07':'Use for liṅga forms.','do08':'Use for installation ceremony.','do09':'Use for rosary or jar.','do10':'Use as pack closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Daily Observance & Liṅga Worship (Chapters 26-27)

## Aim
This pack visualizes Tantrāloka Chapters 26-27 on daily practice (niṭya vidhi) and Liṅga worship (liṅgapūjā).

## Core structure
- Daily practice after initiation maintains and deepens the transformation.
- Oral mantra transmission carries the living word (mukha).
- Worship at the three junctures (sandhyā) aligns with cosmic rhythms.
- Invocation (āvāhana) calls the presence; libation makes the offering.
- Inner (mental) worship is superior to external ritual alone.
- Rites may aim at worldly benefit or ultimate liberation.
- The liṅga appears in countless forms as a support for meditation.
- Installing the divine (prāṇa pratiṣṭhā) brings presence into the image.
- The rosary (japamālā) and jar (kalaśa) are tools of practice.
- Inner and outer worship unite in the final synthesis.

## Visual rules
- Dawn pearl and saffron evoke the daily cycle's beginning.
- The liṅga should be stylized, not literal-phallic.
- Use circular and cyclic motifs suggesting the rotation of days.
- Sandhyā scenes should feel transitional between light and dark.

## Style family
Dawn pearl, saffron robe, parchment, day sky, night ink.

## Guardrails
- The liṅga is a cosmic symbol, not a physical object.
- Outer worship is not inferior — it supports inner realization.
- Rites for benefit are valid, not merely worldly.
- The daily cycle is not routine; it is a sacred structure.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Daily Observance Pack

## Differentiation
This pack introduces a dawn-to-dusk cyclic visual language distinct from threshold or maṇḍala palettes.

## New symbols
1. eight-point daily rhythm
2. sixfold oral emission
3. twelve-point sandhyā ring
4. five-ray invocation seal
5. ten-ray antar field
6. dual-aim hexagram
7. nine-point liṅga ring
8. twelve-ray installation
9. 24-bead rosary circle
10. inner-outer synthesis seal

## New relationships
- daily practice → initiatory deepening
- oral mantra → living presence
- sandhyā → cosmic rhythm alignment
- invocation → presence calling
- inner worship → mental offering
- liṅga → form supporting formless

## Material vocabulary
Pearl dawn, saffron robe, parchment, day sky, night ink.

## Closing seal
A 20-point dawn/saffron ring with the central title 'pūjā' — inner and outer worship united as one complete offering.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Daily Observance & Liṅga Worship Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'daily_observance_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'daily_observance_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['daily_observance_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'daily_observance_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
