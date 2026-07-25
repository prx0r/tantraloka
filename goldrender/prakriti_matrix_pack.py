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
SEED = 14141

PARCHMENT = (244, 240, 232)
PARCHMENT_LIGHT = (250, 247, 240)
INK = (34, 38, 44)
UMBER = (78, 64, 50)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60)
ROSE = (194, 108, 132)
TEAL = (90, 146, 148)
INDIGO = (66, 78, 136)
SLATE = (106, 118, 138)
MIST = (176, 186, 200)
WHITE = (252, 250, 246)
SILVER = (216, 222, 232)
GREEN = (106, 152, 114)
SAFFRON = (224, 152, 56)
VIOLET = (100, 84, 144)
DEEP_VIOLET = (52, 44, 78)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
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


def prakriti_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PARCHMENT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.0 + fine[...,None]*0.85
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*4.5,0,13)[...,None]*0.55
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(UMBER,110),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,80),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=CRIMSON)

def dust(im,seed,n=42):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def guna_line(d,x0,x1,y,amp,phase,col,width=3):
    pts=[]
    for i in range(80):
        u=i/79; x=lerp(x0,x1,u); y=y+math.sin(u*math.pi*3+phase)*amp
        pts.append((x,y))
    d.line(pts,fill=rgba(col,190),width=width)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'प्रकृति',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*170; y=cy+math.sin(a)*110
        col=mix(VIOLET,GOLD,i/2)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,180),fill=rgba(col,20),width=2)
        lineglow(im,[(cx,cy),(x,y)],col,2,70,5)
    d.text((640,505),'prakṛti — the primordial matrix of all manifestation',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'सत्त्व',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(6):
        y=lerp(160,400,i/5); amp=lerp(5,25,ease(t))
        guna_line(d,250,1050,y,amp*(1-i*.1),t*2+i*.5,GOLD,3)
    d.text((640,505),'sattva — the guṇa of purity, luminosity, and harmony',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,CRIMSON,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(CRIMSON,220),width=2)
    d.text((cx,cy-50),'रजस्',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(6):
        y=lerp(160,400,i/5); r=lerp(5,45,ease(t))
        x=400+i*100; d.ellipse((x-r,y-r,x+r,y+r),outline=rgba(mix(CRIMSON,SAFFRON,i/5),160),width=2)
    d.text((640,505),'rajas — the guṇa of activity, passion, and dynamic energy',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,DEEP_VIOLET,110,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(DEEP_VIOLET,220),width=2)
    d.text((cx,cy-50),'तमस्',font=DEVA_MED,fill=VIOLET,anchor='mm')
    for i in range(6):
        y=lerp(160,400,i/5); w=lerp(300,100,ease(t))
        alpha=int(140*(1-i/6)*ease(t))
        d.arc((cx-w,y-8,cx+w,y+8),200,340,fill=rgba(mix(DEEP_VIOLET,SLATE,i/5),alpha),width=3)
    d.text((640,505),'tamas — the guṇa of inertia, darkness, and potentiality',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'गुण',font=DEVA_MED,fill=GOLD,anchor='mm')
    cols=[GOLD,CRIMSON,DEEP_VIOLET]
    for i,col in enumerate(cols):
        y=160+i*100
        for j in range(5):
            x=250+j*190; r=lerp(5,30,ease(t))
            d.ellipse((x-r,y-r,x+r,y+r),outline=rgba(col,160),width=2)
    d.text((640,505),'the three guṇas are the threads from which the fabric of reality is woven',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'प्रकृति',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    cols=[GOLD,CRIMSON,DEEP_VIOLET]
    for i,col in enumerate(cols):
        y=170+i*80
        seg=partial([(250,y),(1050,y)],smooth(.03+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,3,85,6)
    d.text((640,505),'the three threads braid together — no guṇa acts alone',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'गुण',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3+t*.06
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*110
        col=mix(GOLD,CRIMSON,i/2)
        lineglow(im,[(cx,cy),(x,y)],col,3,90,6)
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,190),fill=rgba(col,22),width=2)
    d.text((640,505),'the guṇas are in constant interplay — equilibrium is rare and dynamic',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),75,GOLD_LIGHT,150,24)
    for r,col in [(220,UMBER),(175,GOLD),(130,CRIMSON),(85,DEEP_VIOLET)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'प्रकृति',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,CRIMSON,i/15),170))
    d.text((640,505),'the prakṛti seal: the three guṇas as one matrix of becoming',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('pr01','The Primordial Matrix','The three guṇas as the fabric of reality.','Prakṛti','Prakṛti as the three-threaded matrix of all manifestation.','overview',['prakriti','gunas','matrix'],'overview','three-branch radial diagram',sc01),
Scene('pr02','Sattva','The guṇa of luminosity.','Sattva','Purity, harmony, lightness, and lucidity.','sattva',['sattva','purity','harmony'],'guna','sine wave field',sc02),
Scene('pr03','Rajas','The guṇa of activity.','Rajas','Energy, passion, movement, and dynamism.','rajas',['rajas','activity','energy'],'guna','expanding circle field',sc03),
Scene('pr04','Tamas','The guṇa of inertia.','Tamas','Darkness, density, potentiality, and rest.','tamas',['tamas','inertia','darkness'],'guna','contracting arc field',sc04),
Scene('pr05','Three Threads','The braided fabric of reality.','Tri-guṇa','The three guṇas weave together as one fabric.','three_threads',['threads','weaving','fabric'],'synthesis','three rows of pulsing circles',sc05),
Scene('pr06','No Guṇa Acts Alone','Their constant interplay.','Guṇa-tantra','The guṇas never operate independently.','interplay',['interplay','together','dynamics'],'dynamics','three parallel glowing lines',sc06),
Scene('pr07','Dynamic Equilibrium','Balance in motion.','Guṇa-sāmya','Equilibrium of the guṇas is rare, dynamic, and powerful.','equilibrium',['equilibrium','balance','dynamic'],'dynamics','three-branch rotating interplay',sc07),
Scene('pr08','The Prakṛti Seal','The matrix of all becoming.','Prakṛti-cakra','Closing seal: the three guṇas as one primordial matrix.','closing_seal',['seal','prakriti','gunas'],'seal','quadruple ring seal',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=prakriti_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,38); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),PARCHMENT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Prakṛti: The Primordial Matrix','source_basis':'Tantrāloka and Trika/Sāṃkhya: prakṛti as the three-guṇa matrix of all manifestation — sattva, rajas, and tamas.','style':{'family':'guna-weaving cosmography','background':'warm parchment','ink':'umber and slate','accent':'gold for sattva, crimson for rajas, deep violet for tamas','materials':['sine wave fields','expanding circles','contracting arcs','pulsing circle rows','parallel glow lines','braided interplay']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['pr01'],'individual_gunas':['pr02','pr03','pr04'],'braiding_and_play':['pr05','pr06','pr07'],'seal':['pr08']},'reusability_notes':{'pr01':'Use for prakṛti or guṇa overview.','pr02':'Use for sattva.','pr03':'Use for rajas.','pr04':'Use for tamas.','pr05':'Use for three threads.','pr06':'Use for interplay.','pr07':'Use for equilibrium.','pr08':'Use as closing prakṛti seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Prakṛti

## Aim
Visualize prakṛti: the primordial matrix of three guṇas — sattva, rajas, tamas — that weave together as the fabric of all manifestation.

## Structure
1. Prakṛti is the matrix of three guṇas
2. Sattva — purity, luminosity, harmony
3. Rajas — activity, passion, energy
4. Tamas — inertia, density, potential
5. Three threads woven as one fabric
6. No guṇa acts alone
7. Dynamic equilibrium
8. The seal: one matrix of becoming

## Visual rules
- Gold for sattva (luminosity), crimson for rajas (activity), deep violet for tamas (darkness).
- Wave lines for sattva, expanding circles for rajas, contracting arcs for tamas.
- Parallel lines for braiding.
- Warm parchment ground.
- The three are always shown together.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Prakṛti Pack\n\n## Differentiation\nThis pack uses three-color systemic imagery — wave, circle, arc for the three guṇas — distinct from the rotating wheels of Cakra or the terrifying night of Bhairava.\n\n## New symbols\n1. three-branch radial diagram\n2. sine wave field (sattva)\n3. expanding circle field (rajas)\n4. contracting arc field (tamas)\n5. three rows of pulsing circles\n6. three parallel glowing lines\n7. three-branch rotating interplay\n8. quadruple ring seal\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Prakṛti Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'prakriti_matrix_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'prakriti_matrix_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['prakriti_matrix_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','prakriti_matrix_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'prakriti_matrix_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
