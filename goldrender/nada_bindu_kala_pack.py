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
SEED = 55555

# Nāda-Bindu-Kalā palette — sound, point, emanation
NIGHT = (16, 18, 26)
DEEP_VIOLET = (48, 42, 72)
VIOLET = (104, 88, 146)
LAVENDER = (168, 152, 198)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
TEAL = (88, 146, 148)
MIST = (176, 186, 204)
SLATE = (104, 114, 132)
SILVER = (216, 222, 232)
PARCHMENT = (244, 240, 230)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
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


def sound_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.28))**2+((yy-H*.35)/(H*.22))**2)*2.4)
    base[...,0]+=halo*8; base[...,1]+=halo*12; base[...,2]+=halo*22
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,95),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,75),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,VIOLET,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(14,16,24,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=48):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,62))))
    im.alpha_composite(ov)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),70,GOLD_LIGHT,130,20)
    for r,col in [(210,VIOLET),(160,SILVER),(110,GOLD)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*190; y=cy+math.sin(a)*130
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(VIOLET,GOLD,i/12),150))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'nāda-bindu-kalā — sound, point, and creative emanation',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # nāda — unmanifest vibration
    for i in range(10):
        a=i*2*math.pi/10; r=lerp(20,180,ease(t))
        x=cx+math.cos(a+t)*r*.8; y=cy+math.sin(a+t)*r*.5
        col=mix(DEEP_VIOLET,LAVENDER,i/9)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,160))
    glow(im,(cx,cy),50,VIOLET,110,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(VIOLET,220),width=2)
    d.text((cx,cy-40),'नाद',font=DEVA_MED,fill=LAVENDER,anchor='mm')
    d.text((640,505),'nāda — the first stirring of sound before any form',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # bindu condensing from nāda
    glow(im,(cx,cy),70,VIOLET,120,20)
    for i in range(8):
        r=lerp(100,16,ease(t))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(LAVENDER,GOLD,i/8),140-15*i),width=2)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-60),'बिन्दु',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'bindu — the vibration condenses into a single radiant point',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # kalā — the point emanates creative rays
    glow(im,(cx,cy),50,GOLD_LIGHT,130,16)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16
        seg=partial([(cx+math.cos(a)*18,cy+math.sin(a)*18),(cx+math.cos(a)*210,cy+math.sin(a)*140)],smooth(.03+i*.03,.84,t))
        col=mix(GOLD_LIGHT,TEAL,i/15)
        if len(seg)>1:lineglow(im,seg,col,3,90,6)
    d.text((cx,cy-60),'कला',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'kalā — the point radiates into differentiated creative power',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # descending sequence: nāda → bindu → kalā
    cols=[VIOLET,GOLD,GOLD_LIGHT]
    labels=[('nāda','नाद'),('bindu','बिन्दु'),('kalā','कला')]
    ys=[140,240,340]
    for i,(col,(eng,sans)) in enumerate(zip(cols,labels)):
        y=ys[i]
        d.rounded_rectangle((cx-120,y-22,cx+120,y+22),radius=14,outline=rgba(col,170),fill=rgba(col,18),width=2)
        d.text((cx-70,y),sans,font=DEVA_MED,fill=col,anchor='mm')
        d.text((cx+60,y),eng,font=SMALL_FONT,fill=col,anchor='mm')
        if i<2:
            seg=partial([(cx,y+22),(cx,ys[i+1]-22)],smooth(.05+i*.08,.8,t))
            if len(seg)>1:lineglow(im,seg,mix(col,cols[i+1],.5),2,70,5)
    glow(im,(cx,cy-200),30,GOLD_LIGHT,100,12)
    d.text((640,505),'the three stages of manifestation: vibration condenses into point, point radiates as power',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # kalā as the matrix of the tattvas
    for r,col,n in [(220,GOLD,16),(170,VIOLET,12),(118,GOLD_LIGHT,8)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.03; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(col,WHITE,i/n),160))
    glow(im,(cx,cy),40,GOLD_LIGHT,110,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'from kalā, the entire tattvic order unfolds as differentiated manifestation',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # return: kalā dissolves back into bindu, bindu into nāda
    for i in range(5):
        r=lerp(200,20,1-ease(t))*ease(t)
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(GOLD,VIOLET,i/5),140-25*i),width=2)
    glow(im,(cx,cy),50,VIOLET,110,18)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(VIOLET,220),width=2)
    d.text((640,505),'the emanation reverses: kalā returns to bindu, bindu dissolves into nāda',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),80,GOLD_LIGHT,140,24)
    for r,col in [(220,SILVER),(170,VIOLET),(120,GOLD),(70,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120-15*(r//50)),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'नादबिन्दुकला',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=i*2*math.pi/16; x=cx+math.cos(a)*190; y=cy+math.sin(a)*130
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(SILVER,WHITE,i/16),160))
    d.text((640,505),'the seal of sound, point, and emanation: one consciousness unfolding and returning',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('nb01','Sound, Point, Emanation','The three stages of manifestation.','Nāda-Bindu-Kalā','Overview: nāda, bindu, and kalā as the threefold unfolding of consciousness.','overview',['nada','bindu','kala'],'overview','triple concentric field',sc01),
Scene('nb02','Nāda — Unmanifest Vibration','The first stirring before form.','Nāda','Sound as the initial impulse of consciousness.','unmanifest_sound',['sound','vibration','nada'],'stage','orbiting vibration particles',sc02),
Scene('nb03','Bindu — The Radiant Point','Vibration condenses into a single point.','Bindu','The point of concentrated potency.','radiant_point',['point','bindu','concentration'],'stage','contracting concentric rings',sc03),
Scene('nb04','Kalā — Creative Emanation','The point radiates creative power.','Kalā','Differentiated power streams forth from the point.','creative_rays',['emanation','rays','power'],'stage','radial emission lines',sc04),
Scene('nb05','The Threefold Descent','From vibration through point to emanation.','Avataraṇa','The descent of consciousness through three stages.','triple_descent',['descent','three','stages'],'process','three-tier cascade diagram',sc05),
Scene('nb06','Kalā as Matrix of the Tattvas','All thirty-six levels unfold from kalā.','Kalā-tattva','The emanation becomes the matrix of all categories.','tattva_matrix',['matrix','tattvas','unfolding'],'process','nested ring matrices',sc06),
Scene('nb07','The Return','Emanation dissolves back into the source.','Nivṛtti','Kalā returns to bindu, bindu dissolves into nāda.','reverse_absorption',['return','absorption','source'],'return','contracting dissolution rings',sc07),
Scene('nb08','The Nāda-Bindu-Kalā Seal','Consciousness unfolding and returning.','Nāda-bindu-kalā-cakra','Closing seal: the one consciousness that vibrates, concentrates, and emanates.','closing_seal',['seal','sound','point','emanation'],'seal','concentric ring seal with Sanskrit',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=sound_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,42); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
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
    manifest={'project':'Tantrāloka — Nāda-Bindu-Kalā: Sound, Point, Emanation','source_basis':'Tantrāloka and Trika phonemic cosmology: nāda as unmanifest vibration, bindu as concentrated point, kalā as creative emanation.','style':{'family':'phonemic condensation cosmography','background':'deep night with violet-silver aura','ink':'slate and mist','accent':'violet, gold, silver, teal, white','materials':['vibration particles','condensing rings','emission rays','tiered cascade','nested matrices','dissolution rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['nb01'],'individual_stages':['nb02','nb03','nb04'],'process_and_return':['nb05','nb06','nb07'],'seal':['nb08']},'reusability_notes':{'nb01':'Use for nāda-bindu-kalā overview.','nb02':'Use for unmanifest sound or vibration.','nb03':'Use for bindu condensation or concentration.','nb04':'Use for creative emanation or rays.','nb05':'Use for threefold descent.','nb06':'Use for kalā as matrix of tattvas.','nb07':'Use for reversal or absorption.','nb08':'Use as closing sound-point-emanation seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Nāda-Bindu-Kalā

## Aim
Visualize the three stages of manifestation: nāda (unmanifest sound), bindu (the radiant point), and kalā (creative emanation).

## Structure
1. Nāda, bindu, and kalā are three phases of one consciousness
2. Nāda — vibration before form
3. Bindu — vibration condenses to a point
4. Kalā — the point radiates creative power
5. The threefold descent from subtle to gross
6. Kalā is the matrix of the tattvas
7. The return: emanation dissolves back
8. The seal: the one consciousness

## Visual rules
- Violet for nāda (unmanifest vibration), gold for bindu (concentrated point), gold-light for kalā (emanation).
- Use orbiting particles for vibration, contracting rings for condensation, rays for emanation.
- The three stages are a continuum, not three separate things.

## New motifs
- triple concentric field
- orbiting vibration particles
- contracting condensation rings
- radial emission lines
- three-tier cascade
- nested ring matrices
- contracting dissolution rings
- concentric ring seal with Sanskrit
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Nāda-Bindu-Kalā Pack

## Differentiation
This pack uses phonemic condensation imagery — vibration particles, contracting points, and radial emanations — distinct from the void-piercing motifs of Khecarī.

## New symbols
1. triple concentric field
2. orbiting vibration particles
3. contracting condensation rings
4. radial emission lines
5. three-tier cascade
6. nested ring matrices
7. contracting dissolution rings
8. concentric ring seal with Sanskrit

## Material vocabulary
- deep night ground
- violet vibration-light
- gold concentrated-light
- gold-light emanations
- silver mediating sheen

## Closing seal
Four concentric rings — silver, violet, gold, gold-light — with Sanskrit नादबिन्दुकला and sixteen luminous nodes.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Nāda-Bindu-Kalā Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'nada_bindu_kala_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'nada_bindu_kala_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['nada_bindu_kala_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','nada_bindu_kala_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'nada_bindu_kala_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
