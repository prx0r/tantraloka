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
SEED = 88888

# Svātantrya palette — unbounded freedom
NIGHT = (14, 16, 24)
DEEP_INDIGO = (40, 48, 92)
INDIGO = (68, 76, 135)
GOLD = (207, 168, 92)
GOLD_LIGHT = (245, 216, 145)
WHITE = (252, 250, 246)
IVORY = (245, 242, 235)
UMBER = (78, 65, 52)
SLATE = (106, 118, 140)
MIST = (176, 186, 204)
TEAL = (96, 150, 152)
CRIMSON = (152, 46, 60)
ROSE = (190, 110, 136)
VIOLET = (128, 108, 170)
GREEN = (106, 151, 114)
BLACK = (10, 11, 16)
SILVER = (222, 228, 236)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
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


def freedom_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.30))**2+((yy-H*.40)/(H*.26))**2)*2.4)
    base[...,0]+=halo*10; base[...,1]+=halo*18; base[...,2]+=halo*28
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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,INDIGO,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(13,15,22,210),outline=rgba(SLATE,60),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=IVORY)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(20,68))))
    im.alpha_composite(ov)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),80,GOLD_LIGHT,140,24)
    glow(im,(cx,cy),130,INDIGO,60,32)
    for r,col in [(210,GOLD),(160,INDIGO),(108,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130),width=2)
    for i in range(16):
        a=i*2*math.pi/16; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD_LIGHT,INDIGO,i/15),180))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,200))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'स्वातन्त्र्य',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'svātantrya — the absolute freedom of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(12):
        r=22+i*20
        alpha=int(160*(1-i/12)*(.5+.5*math.sin(t*2)))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(GOLD,INDIGO,i/12),alpha),width=2)
    glow(im,(cx,cy),70,GOLD_LIGHT,150,22)
    glow(im,(cx,cy),110,INDIGO,50,28)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'स्वभाव',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.04; x=cx+math.cos(a)*180; y=cy+math.sin(a)*124
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,INDIGO,i/13),140))
    d.text((640,505),'freedom is the very nature of consciousness, not a property it possesses',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,GOLD_LIGHT,140,20)
    for i in range(10):
        a=-math.pi/2+i*2*math.pi/10+t*.04
        x=cx+math.cos(a)*205; y=cy+math.sin(a)*134
        col=mix(GOLD,TEAL,i/9)
        d.ellipse((x-18,y-18,x+18,y+18),outline=rgba(col,180),fill=rgba(col,22),width=2)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,210))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,220))
        lineglow(im,[(cx,cy),(x,y)],col,2,75,6)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'शक्ति',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'all powers of consciousness arise from its absolute freedom',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # the freedom to create without constraint
    glow(im,(cx,cy-80),40,GOLD_LIGHT,120,14)
    d.ellipse((cx-14,cy-94,cx+14,cy-66),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*120; y=cy-80+math.sin(a)*76
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(mix(GOLD_LIGHT,TEAL,i/6),180))
        seg=partial(bezier((cx,cy-80),(cx+math.cos(a)*50,cy-80+math.sin(a)*30),(x-math.cos(a)*20,y-math.sin(a)*10),(x,y),80),smooth(.05+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,mix(GOLD_LIGHT,TEAL,i/6),2,80,5)
    d.text((640,505),'the freedom to create is the same as the freedom to withhold — both are one power',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # absolute freedom is not license — it is the nature of the real
    for r,col in [(220,INDIGO),(170,GOLD),(118,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    # freedom marks
    for i in range(16):
        a=i*2*math.pi/16; x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        r=5+4*math.sin(t*3+i)
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(mix(GOLD,SILVER,i/16),150))
    d.text((640,505),'svātantrya is not license but the self-determination of the real',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    # freedom as the source of both bondage and liberation
    d.rounded_rectangle((250,150,1030,410),radius=24,outline=rgba(GOLD,140),fill=rgba(GOLD,15),width=2)
    glow(im,(cx,cy),55,GOLD_LIGHT,120,16)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i,lab in enumerate(['bondage','seeking','grace','liberation']):
        a=-math.pi/2+i*2*math.pi/4
        x=cx+math.cos(a)*150; y=cy+math.sin(a)*95
        col=mix(CRIMSON,TEAL,i/3)
        d.ellipse((x-18,y-18,x+18,y+18),outline=rgba(col,170),fill=rgba(col,30),width=2)
        d.text((x,y),lab,font=SMALL_FONT,fill=col,anchor='mm')
        lineglow(im,[(cx,cy),(x,y)],col,2,65,5)
    d.text((640,505),'freedom itself appears as bondage and liberation — both are its play',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # recognition of one's own freedom
    glow(im,(cx,cy),80,GOLD_LIGHT,140,22)
    for i in range(18):
        a=i*2*math.pi/18; r=160+30*ease(t)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.62
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD_LIGHT,WHITE,i/18),200))
        lineglow(im,[(cx,cy),(x,y)],mix(GOLD_LIGHT,WHITE,i/18),1,50,3)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'to recognize svātantrya is to know oneself as the free ground of all experience',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # closing seal — the freedom field
    for r,col in [(230,INDIGO),(185,GOLD),(140,GOLD_LIGHT),(95,WHITE)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130-20*(r//50)),width=2)
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(WHITE,255),outline=rgba(GOLD,225),width=2)
    for i in range(16):
        a=i*2*math.pi/16
        p0=(cx+math.cos(a)*55,cy+math.sin(a)*55); p1=(cx+math.cos(a)*185,cy+math.sin(a)*130)
        seg=partial([p0,p1],ease(t))
        if len(seg)>1:lineglow(im,seg,GOLD_LIGHT,2,60,4)
    d.text((640,505),'the seal of freedom: consciousness is its own ground and its own determination',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('sv01','Svātantrya','The absolute freedom of consciousness.','Svātantrya','Freedom is the very nature of consciousness.','overview',['freedom','consciousness','nature'],'overview','radiant freedom field',sc01),
Scene('sv02','The Nature of Freedom','Consciousness does not possess freedom — it is freedom.','Svābhāvya','Freedom is not a quality but the substance of awareness.','free_nature',['nature','substance','awareness'],'foundation','unbounded pulse rings',sc02),
Scene('sv03','Source of All Powers','All capacities arise from freedom.','Sarva-śakti','Every power of consciousness is an expression of svātantrya.','source_of_powers',['powers','expression','freedom'],'foundation','eight-nodal power wheel',sc03),
Scene('sv04','Creation and Withholding','To create and to withhold are one freedom.','Sṛṣṭi-saṃhāra','The freedom to manifest and to dissolve is one and the same.','create_withhold',['creation','withholding','unity'],'expression','six rays from source',sc04),
Scene('sv05','Freedom as Self-Determination','The real determines itself.','Svayam-ādhāra','Freedom is not arbitrary but is the self-grounding of the real.','self_determination',['self-determination','real','ground'],'foundation','concentric self-grounding rings',sc05),
Scene('sv06','The Play of Bondage and Liberation','Bondage and liberation are both expressions of freedom.','Bandha-mokṣa','Even limitation is an expression of the unlimited.','bondage_liberation',['bondage','liberation','play'],'expression','four stages in a field',sc06),
Scene('sv07','Recognition of Freedom','To know oneself as the free ground.','Svātantrya-pratyabhijñā','Recognition reveals one\'s own nature as absolute freedom.','recognition',['recognition','self-knowledge','freedom'],'recognition','radial recognition burst',sc07),
Scene('sv08','The Svātantrya Seal','Consciousness as its own determination.','Svātantrya-cakra','The closing seal: freedom as the one ground.','closing_seal',['seal','freedom','consciousness'],'seal','concentric freedom seal',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=freedom_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,45); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=94)
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
    manifest={'project':'Tantrāloka — Svātantrya: The Absolute Freedom of Consciousness','source_basis':'Tantrāloka and Trika doctrine of svātantrya: consciousness as absolute freedom, self-determination, and the ground of all powers.','style':{'family':'freedom-field cosmography','background':'deep indigo night','ink':'slate and mist','accent':'gold, indigo, teal, white, silver','materials':['radiant freedom rings','nodal power wheels','self-grounding ellipses','recognition bursts']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['sv01'],'foundation':['sv02','sv03','sv05'],'expression':['sv04','sv06'],'recognition_and_seal':['sv07','sv08']},'reusability_notes':{'sv01':'Use for svātantrya overview.','sv02':'Use for freedom as nature of consciousness.','sv03':'Use for powers arising from freedom.','sv04':'Use for creation and withholding as one.','sv05':'Use for self-determination of the real.','sv06':'Use for bondage and liberation as play.','sv07':'Use for recognition of one\'s own freedom.','sv08':'Use as closing freedom seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Svātantrya: Absolute Freedom

## Aim
Visualize the doctrine of svātantrya: consciousness is absolute freedom, not as a property but as its very nature.

## Core structure
1. Svātantrya is the nature of consciousness
2. Freedom is not a quality but the substance of awareness
3. All powers arise from freedom
4. The freedom to create and to withhold are one
5. Freedom is self-determination, not arbitrariness
6. Bondage and liberation are both expressions of freedom
7. Recognition reveals one's own nature as freedom
8. The seal: consciousness as its own ground

## Visual rules
- Freedom is shown as radiance and expansion, not as breaking chains.
- Gold and indigo for the field; white for recognition.
- Avoid depicting freedom as rebellion or transgression.
- Rings expanding from a center are the primary motif.

## New motifs
- radiant freedom field
- unbounded pulse rings
- eight-nodal power wheel
- creation-withholding rays
- self-grounding concentric rings
- four-stage play wheel
- radial recognition burst
- concentric freedom seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Svātantrya Pack

## Differentiation
Where other packs emphasize structure, descent, or path, this pack emphasizes radiance and self-determination. The freedom field is the primary visual language.

## New symbols
1. radiant freedom field
2. unbounded pulse rings
3. eight-nodal power wheel
4. creation-withholding rays
5. self-grounding rings
6. bondage-liberation wheel
7. recognition burst
8. concentric freedom seal

## Relationships
- consciousness → freedom (not: consciousness + freedom)
- freedom → all powers
- creation ↔ withholding (same freedom)
- bondage + liberation → expressions of freedom
- recognition → self-knowledge as freedom

## Material vocabulary
- deep indigo night
- gold center-light
- teal secondary powers
- white recognition radiance
- silver freedom marks

## Closing seal
Concentric rings of indigo, gold, gold-light, and white around a central bindu — freedom as the only ground.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Svātantrya: Absolute Freedom Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run:
```bash
python render_pack.py
```
Resume-safe.
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'svatantrya_freedom_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'svatantrya_freedom_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['svatantrya_freedom_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','svatantrya_freedom_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'svatantrya_freedom_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
