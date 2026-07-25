#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent; FRAMES_ROOT = ROOT / 'frames'; SCENES_ROOT = ROOT / 'scenes'
W, H = 1280, 720; FPS = 10; DURATION = 4.8; NFRAMES = int(FPS * DURATION); SEED = 19191

NIGHT = (16, 14, 20); DEEP_GOLD = (120, 90, 50); GOLD = (208, 168, 92)
GOLD_LIGHT = (246, 216, 142); PALE_GOLD = (252, 242, 222); WHITE = (254, 253, 250)
CRIMSON = (154, 46, 60); ROSE = (196, 108, 132); TEAL = (90, 146, 148)
SLATE = (106, 118, 138); MIST = (176, 186, 204); SILVER = (216, 222, 232)
SAFFRON = (224, 152, 56); PALE_SAFFRON = (248, 218, 168)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31); SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22); DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))

def ananda_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.8 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    g=np.exp(-(((xx-W/2)/(W*.26))**2+((yy-H*.40)/(H*.28))**2)*2.2)
    base[...,0]+=g*26; base[...,1]+=g*20; base[...,2]+=g*8
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
def partial(points,a):
    a=clamp(a); f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points): A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out
def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,90),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,70),width=1)
def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(14,12,18,206),outline=rgba(SLATE,50),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE); d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(GOLD_LIGHT,PALE_GOLD,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(20,65))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24); glow(im,(cx,cy),120,PALE_GOLD,60,32)
    for r,col in [(200,GOLD),(150,GOLD_LIGHT),(100,PALE_GOLD)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आनन्द',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*190; y=cy+math.sin(a)*130
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,PALE_GOLD,i/11),180))
    d.text((640,505),'ānanda — the bliss that is the very substance of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18); glow(im,(cx,cy),100,SAFFRON,50,26)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आनन्द',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; x=cx+math.cos(a)*170; y=cy+math.sin(a)*116
        col=mix(GOLD,SAFFRON,i/5)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,180),fill=rgba(col,20),width=2)
        lineglow(im,[(cx,cy),(x,y)],col,3,85,6)
    d.text((640,505),'bliss is not a feeling — it is the taste of consciousness itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18); glow(im,(cx,cy),95,ROSE,45,24)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आनन्द',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(8):
        a=i*2*math.pi/8+t*.05; r=lerp(10,175,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GOLD,ROSE,i/7)
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,180))
    d.text((640,505),'ānanda expands from the center — the joy of being radiates outward',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),65,GOLD_LIGHT,140,22); glow(im,(cx,cy),105,PALE_GOLD,55,28)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आनन्द',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*170; y=cy+math.sin(a)*110
        col=mix(GOLD,TEAL,i/2)
        lineglow(im,[(cx,cy),(x,y)],col,3,90,6)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,200))
    d.text((640,505),'sat-cit-ānanda — being, consciousness, and bliss are one reality',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),75,GOLD_LIGHT,150,24)
    for r,col in [(210,GOLD),(160,GOLD_LIGHT),(110,PALE_GOLD),(60,WHITE)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,120-15*(r//50)),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आनन्द',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,PALE_GOLD,i/15),170))
    d.text((640,505),'the ānanda seal: the bliss of consciousness radiating without end',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
Scene('an01','Bliss','The substance of consciousness.','Ānanda','The bliss that is the very nature of awareness.','overview',['ananda','bliss','consciousness'],'overview','golden concentric rings',sc01),
Scene('an02','The Taste of Consciousness','Not a feeling but the substance.','Ānanda-rasa','Bliss is the taste of consciousness itself.','taste_of_consciousness',['bliss','taste','consciousness'],'bliss','six-branch golden emission',sc02),
Scene('an03','Expanding Joy','Radiating from the center.','Ānanda-prabhā','Bliss radiates outward from the center of awareness.','expanding_joy',['joy','expansion','radiation'],'bliss','eight-point expanding radii',sc03),
Scene('an04','Sat-Cit-Ānanda','Being, consciousness, bliss.','Sat-cit-ānanda','The three aspects of the one reality.','three_aspects',['being','consciousness','bliss'],'synthesis','three-branch golden seal',sc04),
Scene('an05','The Ānanda Seal','Bliss radiating without end.','Ānanda-cakra','Closing seal: bliss as the substance of consciousness.','closing_seal',['seal','bliss','ananda'],'seal','quadruple golden ring seal',sc05),
]

def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=ananda_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,45); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
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
    manifest={'project':'Tantrāloka — Ānanda: Bliss','source_basis':'Tantrāloka: ānanda as the bliss that is the very substance of consciousness.','style':{'family':'golden-bliss cosmography','background':'deep night with gold radiance','ink':'slate and mist','accent':'gold, saffron, rose, pale gold','materials':['golden rings','emission rays','expanding radii','quadruple seal']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['an01'],'bliss_and_synthesis':['an02','an03','an04'],'seal':['an05']},'reusability_notes':{'an01':'Use for ānanda overview.','an02':'Use for taste of consciousness.','an03':'Use for expanding joy.','an04':'Use for sat-cit-ānanda.','an05':'Use as closing bliss seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Ānanda\n\nVisualize ānanda: the bliss that is the very substance of consciousness.\n\n## Structure\n1. Ānanda is the nature of awareness\n2. Not a feeling but the taste of consciousness\n3. Radiating joy from the center\n4. Sat-cit-ānanda — one reality\n5. The seal: bliss without end\n\n## Visual rules\n- Golden palette — gold, saffron, pale gold.\n- Radiant expanding forms.\n- Warm, luminous, overflowing.\n- Abstract radiance — no figures.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Ānanda Pack\n\n## Differentiation\nThis pack uses golden radiance imagery — warm, luminous, expanding — distinct from the cool peace of Śānti.\n\n## New symbols\n1. golden concentric rings\n2. six-branch golden emission\n3. eight-point expanding radii\n4. three-branch golden seal\n5. quadruple golden ring seal\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Ānanda Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)
def validate():
    p=ROOT/'ananda_bliss_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))
def make_zip():
    z=ROOT/'ananda_bliss_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['ananda_bliss_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','ananda_bliss_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')
def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'ananda_bliss_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()
if __name__=='__main__': main()
