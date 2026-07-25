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
SEED = 12121

BLACK = (6, 6, 10)
NIGHT = (14, 12, 18)
BLOOD = (108, 22, 32)
CRIMSON = (152, 40, 56)
CARDINAL = (188, 52, 68)
EMBER = (220, 110, 44)
GOLD = (200, 160, 84)
GOLD_LIGHT = (240, 210, 134)
WHITE = (248, 244, 238)
SLATE = (96, 104, 120)
MIST = (166, 174, 192)
SILVER = (212, 218, 228)
TEAL = (84, 138, 142)
DEEP_VIOLET = (52, 40, 72)
VIOLET = (104, 84, 146)
UMBER = (72, 58, 46)
SILVER_DARK = (144, 152, 168)

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


def bhairava_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.5 + fine[...,None]*1.2
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*22,0,30)[...,None]
    glow=np.exp(-(((xx-W/2)/(W*.24))**2+((yy-H*.44)/(H*.22))**2)*2.0)
    base[...,0]+=glow*22; base[...,1]+=glow*6; base[...,2]+=glow*4
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

def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,85),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,65),width=1)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(12,10,16,200),outline=rgba(SLATE,50),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=MIST)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SLATE)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(SLATE,EMBER,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,55))))
    im.alpha_composite(ov)

def trident(d,cx,cy,scale=1.0,col=GOLD):
    w=6*scale; d.line((cx,cy-60*scale,cx,cy+46*scale),fill=rgba(col,200),width=max(1,int(w)))
    d.arc((cx-42*scale,cy-76*scale,cx,cy-18*scale),250,80,fill=rgba(col,200),width=max(1,int(w)))
    d.arc((cx,cy-76*scale,cx+42*scale,cy-18*scale),100,290,fill=rgba(col,200),width=max(1,int(w)))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),80,CRIMSON,130,24)
    glow(im,(cx,cy),120,BLOOD,60,32)
    for r,col in [(200,GOLD),(150,CRIMSON),(100,EMBER)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,110),width=2)
    trident(d,cx,cy-20,.85,GOLD)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-60),'भैरव',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(10):
        a=i*2*math.pi/10+t*.05; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(CRIMSON,GOLD,i/9),160))
    d.text((640,505),'bhairava — the terrifying ground that is the source of all',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    for i in range(8):
        r=30+i*26; alpha=int(150*(1-i/8)*ease(t))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(BLOOD,GOLD,i/8),alpha),width=2)
    glow(im,(cx,cy),50,GOLD_LIGHT,120,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'भैरव',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the terrifying — not as horror but as the overwhelming intensity of the real',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,20)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*116
        col=mix(CRIMSON,EMBER,i/5)
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,180),fill=rgba(col,18),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,190))
        lineglow(im,[(cx,cy),(x,y)],col,3,85,6)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    trident(d,cx,cy-30,.55,GOLD)
    d.text((640,505),'bhairava is the power that devours all categories — leaving only the real',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'भैरव',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(8):
        a=i*2*math.pi/8
        seg=partial(bezier((cx,cy),(cx+math.cos(a-.2)*80,cy+math.sin(a-.2)*50),(cx+math.cos(a+.2)*140,cy+math.sin(a+.2)*90),(cx+math.cos(a)*195,cy+math.sin(a)*134),90),smooth(.03+i*.04,.84,t))
        col=mix(CRIMSON,GOLD,i/7)
        if len(seg)>1:lineglow(im,seg,col,4,100,7)
    d.text((640,505),'the energy of bhairava erupts — it is the explosive self-revelation of the real',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'अघोर',font=DEVA_SMALL,fill=EMBER,anchor='mm')
    for i in range(4):
        a=-math.pi/2+i*2*math.pi/4
        x=cx+math.cos(a)*165; y=cy+math.sin(a)*112
        col=mix(EMBER,GOLD,i/3)
        seg=partial([(cx,cy),(x,y)],smooth(.04+i*.08,.82,t))
        if len(seg)>1:lineglow(im,seg,col,5,120,9)
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(col,190))
    d.text((640,505),'aghora — the non-terrifying aspect of the terrifying ground',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for r,col in [(200,GOLD),(155,CRIMSON),(110,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,115),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'भैरव',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/13),160))
    d.text((640,505),'bhairava is simultaneously the most terrifying and the most peaceful',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    trident(d,cx,cy,.9,GOLD)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-45),'भैरव',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*180; y=cy+math.sin(a)*122
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(CRIMSON,GOLD,i/11),170))
        lineglow(im,[(cx,cy),(x,y)],mix(CRIMSON,GOLD,i/11),1,55,4)
    d.text((640,505),'the trident of bhairava — cutting through all illusion to the bone of reality',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24)
    for r,col in [(220,SLATE),(175,GOLD),(130,CRIMSON),(85,EMBER)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    trident(d,cx,cy-20,.65,GOLD)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-55),'भैरव',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,CRIMSON,i/15),170))
    d.text((640,505),'the bhairava seal: the terrifying ground that is the source and the end',font=SUB_FONT,fill=SLATE,anchor='mm')


SCENES=[
Scene('bh01','The Terrifying Ground','Bhairava as the ultimate reality.','Bhairava','The terrifying intensity of the real as the ground of all.','overview',['bhairava','terrifying','ground'],'overview','trident with rings',sc01),
Scene('bh02','The Intensity of the Real','Not horror but overwhelming presence.','Bhairava-tattva','The terrifying is the sheer force of reality.','intensity',['intensity','reality','presence'],'nature','pulsing concentric rings',sc02),
Scene('bh03','Devouring Categories','All concepts consumed.','Bhairava-prakāśa','Bhairava devours every category leaving only the real.','devouring',['devouring','categories','real'],'action','six-ray consumption wheel',sc03),
Scene('bh04','Eruptive Revelation','The explosive self-showing of the real.','Bhairava-sphuraṇā','The real reveals itself with explosive force.','eruption',['eruption','revelation','force'],'action','eight-curve explosive bezier',sc04),
Scene('bh05','Aghora — The Non-Terrifying','The gentle face of the terrible.','Aghora','The non-terrifying aspect of the terrifying ground.','non_terrifying',['aghora','gentle','aspect'],'aspect','four-fold directional cross',sc05),
Scene('bh06','Terrifying and Peaceful','The coincidence of opposites.','Bhairava-śānti','Bhairava is simultaneously the most intense and the most still.','peace_in_terror',['peace','terror','coincidence'],'synthesis','triple equality rings',sc06),
Scene('bh07','The Trident','Cutting through illusion.','Triśūla','The trident of bhairava cuts through all false appearance.','trident',['trident','cutting','illusion'],'symbol','trident with radial emission',sc07),
Scene('bh08','The Bhairava Seal','The terrifying ground as source and end.','Bhairava-cakra','Closing seal: bhairava as the alpha and omega of all.','closing_seal',['seal','bhairava','ground'],'seal','quadruple ring with trident',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=bhairava_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,48); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),NIGHT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Bhairava: The Terrifying Ground','source_basis':'Tantrāloka: Bhairava as the ultimate terrifying-yet-peaceful ground of reality, destroyer of categories, source of all.','style':{'family':'terrifying-sublime cosmography','background':'deep night with blood-crimson glow','ink':'slate and silver','accent':'crimson, gold, ember, teal','materials':['blood glow','trident geometry','explosive bezier arcs','consumption wheels','concentric pulse rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['bh01'],'nature_and_action':['bh02','bh03','bh04'],'aspect_and_synthesis':['bh05','bh06','bh07'],'seal':['bh08']},'reusability_notes':{'bh01':'Use for bhairava overview.','bh02':'Use for intensity of the real.','bh03':'Use for devouring categories.','bh04':'Use for eruptive revelation.','bh05':'Use for aghora.','bh06':'Use for terror and peace coincidence.','bh07':'Use for trident symbol.','bh08':'Use as closing bhairava seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Bhairava

## Aim
Visualize bhairava: the terrifying ground of reality that devours all categories and reveals itself with explosive intensity.

## Structure
1. Bhairava is the terrifying ground
2. Intensity of the real
3. Devouring all categories
4. Eruptive self-revelation
5. Aghora — the non-terrifying aspect
6. Terror and peace coincide
7. The trident of bhairava
8. The seal: alpha and omega

## Visual rules
- Deep night with blood-crimson glow.
- Trident as primary symbol.
- Explosive bezier arcs for eruption.
- Concentric pulse rings for intensity.
- Gold for the radiant core within the terror.
- The terrifying is never depicted as a monster.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Bhairava Pack\n\n## Differentiation\nThis pack uses blood-crimson night, trident geometry, and explosive arcs — distinct from the abstract triangles of Trikona or the broken rings of Avadhūta.\n\n## New symbols\n1. trident with rings\n2. pulsing concentric rings\n3. six-ray consumption wheel\n4. eight-curve explosive bezier\n5. four-fold directional cross\n6. triple equality rings\n7. trident with radial emission\n8. quadruple ring with trident\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Bhairava Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'bhairava_ground_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'bhairava_ground_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['bhairava_ground_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','bhairava_ground_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'bhairava_ground_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
