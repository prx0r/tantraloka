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
SEED = 17171

# Prakāśa-Vimarśa palette — light and reflection
NIGHT = (12, 14, 20)
DEEP_INDIGO = (40, 48, 88)
INDIGO = (66, 76, 132)
GOLD = (206, 168, 92)
GOLD_LIGHT = (244, 216, 144)
PALE_GOLD = (252, 242, 218)
WHITE = (254, 253, 250)
SILVER = (218, 224, 234)
MERCURY = (200, 208, 220)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
ROSE = (194, 108, 132)
TEAL = (90, 146, 148)
MIST = (176, 186, 204)
SLATE = (106, 118, 138)
UMBER = (78, 64, 50)
LAVENDER = (168, 152, 196)
PALE_VIOLET = (200, 190, 218)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_BIG = ImageFont.truetype(FONT_DEVA, 48)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def light_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.2 + fine[...,None]*1.15
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*20,0,28)[...,None]
    g1=np.exp(-(((xx-W/2)/(W*.22))**2+((yy-H*.35)/(H*.25))**2)*2.2)
    g2=np.exp(-(((xx-W*.60)/(W*.15))**2+((yy-H*.42)/(H*.18))**2)*2.6)
    base[...,0]+=g1*18+g2*6; base[...,1]+=g1*22+g2*8; base[...,2]+=g1*28+g2*18
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def glow(im,xy,r,color,alpha=145,blur=16):
    ov=layer(); d=ImageDraw.Draw(ov); x,y=xy
    d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(color,alpha))
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))

def lineglow(im,pts,color,width=3,alpha=145,blur=8):
    ov=layer(); d=ImageDraw.Draw(ov)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def bezier(p0,p1,p2,p3,n=90):
    out=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        out.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return out

def partial(points,a):
    a=clamp(a)
    if a<=0:return[]
    if a>=1:return points
    f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points):
        A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out

def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)

def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,100),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,80),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,GOLD,WHITE)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(10,12,18,210),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(.8,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,60))))
    im.alpha_composite(ov)

def mirror_arc(d,cx,cy,rx,ry,col,width=2):
    d.arc((cx-rx,cy-ry,cx+rx,cy+ry),200,340,fill=rgba(col,190),width=width)
    d.arc((cx-rx,cy-ry,cx+rx,cy+ry),20,160,fill=rgba(mix(col,WHITE,.45),120),width=width-1)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),90,WHITE,160,28)
    for r,col in [(220,GOLD),(170,WHITE),(120,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130),width=2)
    for i in range(16):
        a=i*2*math.pi/16; x=cx+math.cos(a)*200; y=cy+math.sin(a)*138
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD_LIGHT,WHITE,i/15),180))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,220))
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'प्रकाश',font=DEVA_BIG,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,cy+44),'विमर्श',font=DEVA_BIG,fill=SILVER,anchor='mm')
    d.text((640,505),'prakāśa-vimarśa — light and reflection, one consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),100,WHITE,180,32)
    for r,col in [(230,WHITE),(180,GOLD_LIGHT),(130,GOLD)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,140-20*(r//50)),width=2)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'प्रकाश',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(20):
        a=i*2*math.pi/20+t*.03; x=cx+math.cos(a)*205; y=cy+math.sin(a)*140
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(WHITE,GOLD_LIGHT,i/19),200))
    d.text((640,505),'prakāśa — self-luminous radiance, the ground of all appearance',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,SILVER,130,22)
    for r,col in [(210,SILVER),(160,MERCURY),(108,GOLD_LIGHT)]:
        mirror_arc(d,cx,cy,r,r*.72,col,2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'विमर्श',font=DEVA_MED,fill=SILVER,anchor='mm')
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12+t*.04; x=cx+math.cos(a)*190; y=cy+math.sin(a)*130
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(SILVER,WHITE,i/11),170))
    d.text((640,505),'vimarśa — reflective self-awareness, consciousness turning back on itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    # light + mirror: inseparability
    d.ellipse((cx-190,cy-130,cx+190,cy+130),outline=rgba(GOLD,130),width=2)
    d.ellipse((cx-130,cy-88,cx+130,cy+88),outline=rgba(SILVER,150),width=2)
    d.ellipse((cx-70,cy-48,cx+70,cy+48),outline=rgba(WHITE,180),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'प्रकाश',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+5,cy+44),'विमर्श',font=DEVA_SMALL,fill=SILVER,anchor='mm')
    for i in range(2):
        a=i*math.pi; x=cx+math.cos(a)*120
        d.ellipse((x-8,cy-8,x+8,cy+8),fill=rgba(mix(GOLD,SILVER,i),190))
    d.text((640,505),'light and reflection are not two things — they are one awareness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # the mirror surface where light knows itself
    glow(im,(cx,cy),90,GOLD_LIGHT,140,24)
    for i in range(6):
        r=26+i*38; alpha=int(150*(1-i/6)*ease(t))
        mirror_arc(d,cx,cy,r,r*.72,mix(GOLD,SILVER,i/5),3)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'ज्ञान',font=DEVA_BIG,fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*128
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD_LIGHT,WHITE,i/13),180))
    d.text((640,505),'the mirror of self-awareness: light recognizing itself as light',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # the world as the play of light and reflection
    glow(im,(cx,cy),70,WHITE,140,22)
    for r,col in [(220,GOLD),(175,SILVER),(130,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    for i in range(18):
        a=i*2*math.pi/18+t*.03
        x=cx+math.cos(a)*(100+80*ease(t)); y=cy+math.sin(a)*(70+55*ease(t))
        col=mix(GOLD,SILVER,i/17)
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,180))
        lineglow(im,[(cx,cy),(x,y)],col,2,65,5)
    d.text((640,505),'the universe appears as the interplay of light and its self-reflection',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # recognition: no difference between light and reflection
    glow(im,(cx,cy),100,GOLD_LIGHT,160,30)
    for r,col,n in [(220,WHITE,18),(170,GOLD,14),(118,GOLD_LIGHT,10)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.03; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(col,WHITE,i/n),180))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'अद्वय',font=DEVA_MED,fill=WHITE,anchor='mm')
    d.text((640,505),'recognition: light and reflection were never two',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),110,GOLD_LIGHT,170,32)
    for r,col in [(230,SILVER),(180,GOLD),(130,GOLD_LIGHT),(80,WHITE)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130-15*(r//50)),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-55),'प्रकाश',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+5,cy+50),'विमर्श',font=DEVA_MED,fill=SILVER,anchor='mm')
    for i in range(20):
        a=i*2*math.pi/20; x=cx+math.cos(a)*210; y=cy+math.sin(a)*145
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(SILVER,WHITE,i/19),170))
        d.ellipse((x-1,y-1,x+1,y+1),fill=rgba(WHITE,220))
    d.text((640,505),'the seal of prakāśa-vimarśa: light that knows itself as light',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('pv01','Light and Reflection','The two poles of one consciousness.','Prakāśa-Vimarśa','Overview: prakāśa and vimarśa as inseparable aspects of awareness.','overview',['prakasha','vimarsha','consciousness'],'overview','dual Devanagari field with rings',sc01),
Scene('pv02','Prakāśa — Self-Luminous Radiance','Light that shines by itself.','Prakāśa','The ground of all appearance is pure luminosity.','self_luminous',['light','radiance','ground'],'pole','expanding radiant rings',sc02),
Scene('pv03','Vimarśa — Reflective Awareness','Consciousness turning back on itself.','Vimarśa','The dynamic self-awareness that constitutes knowing.','reflective_awareness',['reflection','self-awareness','mirror'],'pole','mirror arc field',sc03),
Scene('pv04','Inseparability','Light and reflection are one act.','Prakāśa-Vimarśa-aikya','The two are not two — they are the same reality.','nondual_poles',['nonduality','poles','unity'],'synthesis','nested chambers with dual labels',sc04),
Scene('pv05','The Mirror of Self-Awareness','Light recognizing itself as light.','Jñāna','The mirror surface where awareness knows itself.','self_knowledge',['mirror','knowledge','self'],'recognition','concentric mirror arcs',sc05),
Scene('pv06','The Play of the World','The universe as interplay of light and reflection.','Viśva','All manifestation is the dance of prakāśa and vimarśa.','world_play',['world','play','manifestation'],'manifestation','radial emission of dual nodes',sc06),
Scene('pv07','Nondual Recognition','They were never two.','Advaya','The final recognition: no separation between light and its self-awareness.','nondual_recognition',['recognition','nondual','advaya'],'recognition','triple concentric node rings',sc07),
Scene('pv08','The Prakāśa-Vimarśa Seal','Light that knows itself as light.','Prakāśa-Vimarśa-cakra','Closing seal: the eternal self-illumination of consciousness.','closing_seal',['seal','light','reflection'],'seal','quadruple ring seal with dual Devanagari',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=light_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,48); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(p).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),NIGHT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Prakāśa-Vimarśa: Light and Reflection','source_basis':'Tantrāloka and Trika foundation: prakāśa as self-luminous radiance, vimarśa as reflective self-awareness, their inseparability as the nature of consciousness.','style':{'family':'luminous-reflection cosmography','background':'deep night with white-gold radiance and silver mirror surfaces','ink':'slate and mist','accent':'gold, gold-light, white, silver, mercury','materials':['radiant glow fields','mirror arcs','nested chambers','dual Devanagari','concentric node rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['pv01'],'poles':['pv02','pv03'],'synthesis':['pv04','pv05','pv06'],'recognition_and_seal':['pv07','pv08']},'reusability_notes':{'pv01':'Use for prakāśa-vimarśa overview.','pv02':'Use for pure luminosity or self-radiance.','pv03':'Use for self-awareness or reflection.','pv04':'Use for inseparability of light and reflection.','pv05':'Use for self-knowing mirror.','pv06':'Use for world as play of light.','pv07':'Use for nondual recognition.','pv08':'Use as closing light-reflection seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Prakāśa-Vimarśa

## Aim
Visualize the two inseparable poles of consciousness: prakāśa (self-luminous radiance) and vimarśa (reflective self-awareness).

## Core structure
1. Consciousness is both light and its self-awareness
2. Prakāśa — pure luminosity, the ground of appearance
3. Vimarśa — dynamic reflection, the power of self-knowing
4. They are not two — one reality with two aspects
5. The mirror of self-awareness
6. The world is their interplay
7. Recognition: they were never separate
8. The seal: light knowing itself

## Visual rules
- Gold/white for prakāśa (radiance), silver/mercury for vimarśa (reflection).
- Mirror arcs and reflective surfaces for vimarśa.
- Expansive glow fields for prakāśa.
- Both are always present in every scene.
- Devanagari text as primary compositional element.

## New motifs
- dual Devanagari field
- expanding radiant rings
- mirror arc field
- nested chambers with dual labels
- concentric mirror arcs
- dual-node radial emission
- triple concentric node rings
- quadruple ring seal with dual Devanagari
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Prakāśa-Vimarśa Pack

## Differentiation
This pack uses luminous-reflection imagery distinct from all others. No geometric tattvas, no body diagrams, no breath flows — only light and its self-awareness.

## New symbols
1. dual Devanagari field with rings
2. expanding radiant rings
3. mirror arc field
4. nested chambers with dual labels
5. concentric mirror arcs
6. dual-node radial emission
7. triple concentric node rings
8. quadruple ring seal with dual Devanagari

## Material vocabulary
- deep night field
- white-gold radiance
- silver mirror surfaces
- mercury reflection arcs
- gold-light illumination

## Closing seal
Quadruple ring seal with प्रकाश and विमर्श in Devanagari flanking a central white bindu.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Prakāśa-Vimarśa: Light and Reflection Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'prakasha_vimarsha_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'prakasha_vimarsha_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['prakasha_vimarsha_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','prakasha_vimarsha_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'prakasha_vimarsha_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
