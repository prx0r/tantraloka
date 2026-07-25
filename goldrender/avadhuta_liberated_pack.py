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
SEED = 89898

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
DEEP_INDIGO = (44, 54, 98)
SLATE = (106, 118, 138)
MIST = (176, 186, 200)
WHITE = (252, 250, 246)
SILVER = (216, 222, 232)
SAFFRON = (224, 152, 56)
GREEN = (106, 152, 114)
VIOLET = (100, 84, 144)

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


def avadhuta_ground(seed):
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

def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def broken_ring(d,cx,cy,r,col,width=2):
    d.arc((cx-r,cy-r*.72,cx+r,cy+r*.72),200,340,fill=rgba(col,150),width=width)
    d.arc((cx-r,cy-r*.72,cx+r,cy+r*.72),20,160,fill=rgba(mix(col,WHITE,.5),90),width=width-1)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    for r,col in [(200,GOLD),(150,CRIMSON),(100,TEAL)]:
        broken_ring(d,cx,cy,r,col,2)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'अवधूत',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/11),160))
    d.text((640,505),'avadhūta — the one who has transcended all bounds and conventions',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for i in range(5):
        r=lerp(150,30,ease(t))+i*20
        broken_ring(d,cx,cy,r,mix(SLATE,GOLD,i/4),3)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'अवधूत',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'all bonds are shed — the avadhūta stands free of every constraint',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'अवधूत',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(7):
        y=lerp(150,400,i/6); w=lerp(300,60,ease(t))
        alpha=int(140*(1-i/6)*ease(t))
        if alpha<5: continue
        d.arc((cx-w,y-8,cx+w,y+8),200,340,fill=rgba(mix(SLATE,GOLD,i/6),alpha),width=2)
    d.text((640,505),'no dharma, no āśrama — the avadhūta moves beyond all categories',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'अवधूत',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(8):
        a=i*2*math.pi/8; r=lerp(20,170,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(CRIMSON,GOLD,i/7)
        d.ellipse((x-8,y-8,x+8,y+8),outline=rgba(col,180),fill=rgba(col,20),width=2)
        lineglow(im,[(cx,cy),(x,y)],col,2,70,5)
    d.text((640,505),'free from inside and outside — the avadhūta abides in the heart of all',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'अवधूत',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(6):
        y=lerp(150,410,i/5)
        pts=partial([(200,y),(1080,y)],smooth(.04+i*.06,.82,t))
        if len(pts)>1:lineglow(im,pts,mix(SLATE,GOLD,i/5),2,75,5)
    d.text((640,505),'no mark distinguishes the avadhūta — they are the same as all beings',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    for r,col in [(210,SLATE),(160,GOLD),(110,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'अवधूत',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/13),170))
    d.text((640,505),'the avadhūta is not defined by what they have left behind',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'अवधूत',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(4):
        a=-math.pi/2+i*2*math.pi/4
        r=130+50*math.sin(t*2+i)*ease(t)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GOLD,VIOLET,i/3)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,180))
    d.text((640,505),'the avadhūta lives in the world but is not of it — like water on a lotus',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24)
    for r,col in [(220,UMBER),(175,GOLD),(130,CRIMSON),(85,TEAL)]:
        broken_ring(d,cx,cy,r,col,2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'अवधूत',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/15),170))
    d.text((640,505),'the avadhūta seal: freedom beyond all categories, abiding in the heart',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('av01','The Liberated One','Beyond all bounds and conventions.','Avadhūta','The avadhūta is the one who has transcended every category.','overview',['avadhuta','liberated','beyond'],'overview','broken rings with Devanagari',sc01),
Scene('av02','All Bonds Shed','Every constraint is released.','Bandha-mukti','The avadhūta stands free of every bond.','bonds_shed',['bonds','freedom','release'],'liberation','contracting broken rings',sc02),
Scene('av03','Beyond Categories','No dharma, no āśrama.','Nirdharma','The avadhūta moves beyond all social and religious categories.','beyond_categories',['beyond','categories','freedom'],'transcendence','fading horizontal arcs',sc03),
Scene('av04','Free Within All','Inside and outside are the same.','Sarvatraga','The avadhūta abides in the heart of all things.','free_within',['freedom','heart','omnipresence'],'freedom','eight-ray emission from center',sc04),
Scene('av05','No Mark Distinguishes','The same as all beings.','Sama-darśana','The avadhūta appears ordinary while being extraordinary.','no_mark',['ordinary','extraordinary','same'],'equality','parallel horizon lines',sc05),
Scene('av06','Not What Is Left Behind','Defined by presence, not absence.','Asaṅga','The avadhūta is not defined by renunciation.','not_defined_by',['presence','freedom','being'],'presence','triple equality rings',sc06),
Scene('av07','Water on a Lotus','In the world but not of it.','Padma-jalavat','The avadhūta touches nothing though moving through all.','world_not_of_it',['world','freedom','non-attachment'],'freedom','four-node pivot cross',sc07),
Scene('av08','The Avadhūta Seal','Freedom beyond all categories.','Avadhūta-cakra','Closing seal: the liberated one abiding in the heart.','closing_seal',['seal','avadhuta','freedom'],'seal','quadruple broken ring seal',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=avadhuta_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Avadhūta: The Liberated One','source_basis':'Tantrāloka and Trika: the avadhūta as the one beyond all bounds, free of conventions, abiding in the heart of all.','style':{'family':'liberation cosmography','background':'warm parchment','ink':'umber and slate','accent':'gold, crimson, teal, violet','materials':['broken rings','fading arcs','emission rays','parallel horizons','cross pivots']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['av01'],'liberation':['av02','av03','av05'],'freedom':['av04','av06','av07'],'seal':['av08']},'reusability_notes':{'av01':'Use for avadhūta overview.','av02':'Use for shedding bonds.','av03':'Use for beyond categories.','av04':'Use for freedom within all.','av05':'Use for ordinary appearance.','av06':'Use for presence not absence.','av07':'Use for in the world but not of it.','av08':'Use as closing avadhūta seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Avadhūta

## Aim
Visualize the avadhūta: the one who has transcended all categories, all bounds, and all conventions, abiding in the heart of all beings.

## Structure
1. The avadhūta is beyond all bounds
2. All bonds are shed
3. Beyond all categories and conventions
4. Free within all things
5. No mark distinguishes them
6. Defined by presence, not renunciation
7. In the world but not of it
8. The seal: freedom beyond all categories

## Visual rules
- Broken rings represent transcended bounds.
- Warm parchment ground for the ordinary-as-extraordinary.
- Fading elements represent the release of fixed forms.
- Gold for the freedom, crimson for the heart-abiding.
- The avadhūta is never depicted as a figure.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Avadhūta Pack\n\n## Differentiation\nThis pack uses broken-ring and fading imagery — bounds breaking, categories dissolving — distinct from the seed-burst of Vīrya or the triangles of Trikona.\n\n## New symbols\n1. broken rings with Devanagari\n2. contracting broken rings\n3. fading horizontal arcs\n4. eight-ray emission from center\n5. parallel horizon lines\n6. triple equality rings\n7. four-node pivot cross\n8. quadruple broken ring seal\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Avadhūta Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'avadhuta_liberated_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'avadhuta_liberated_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['avadhuta_liberated_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','avadhuta_liberated_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'avadhuta_liberated_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
