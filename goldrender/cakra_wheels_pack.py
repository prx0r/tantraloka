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
SEED = 13131

NIGHT = (18, 20, 26)
DEEP_INDIGO = (40, 48, 86)
INDIGO = (68, 76, 132)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
TEAL = (90, 146, 148)
DEEP_TEAL = (64, 112, 114)
VIOLET = (100, 84, 144)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
UMBER = (78, 64, 50)
GREEN = (106, 152, 114)
SAFFRON = (224, 152, 56)
SILVER = (216, 222, 232)

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


def cakra_ground(seed):
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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(16,18,24,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    glow(im,(cx,cy),110,TEAL,50,28)
    for i in range(4):
        r=50+i*45; n=8+i*4
        for j in range(n):
            a=-math.pi/2+j*2*math.pi/n+t*.03*(1 if i%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
            col=mix(GOLD,TEAL,i/3)
            d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,180))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'cakra — wheels of energy turning in the field of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for r,n,col in [(190,12,GOLD),(140,8,CRIMSON),(90,6,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.05
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,180))
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    d.text((640,505),'each wheel has its own number of spokes — its own rhythm',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    glow(im,(cx,cy),95,VIOLET,45,24)
    for i in range(5):
        r=40+i*36
        for j in range(6+i*2):
            a=-math.pi/2+j*2*math.pi/(6+i*2)+t*.04*(1 if j%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
            col=mix(GOLD,VIOLET,i/4)
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,160))
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'wheels within wheels — each level of consciousness has its own cakra',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    for i in range(6):
        r=30+i*30
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(CRIMSON,GOLD,i/5),140-15*i),width=2-i//5)
        for j in range(14-i*2):
            a=-math.pi/2+j*2*math.pi/(14-i*2)+t*.06*(1 if i%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(CRIMSON,GOLD,i/5),160))
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    d.text((640,505),'the wheels spin at different speeds — the cosmos is a harmony of rhythms',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),65,GOLD_LIGHT,140,20)
    for r,col,n in [(210,GOLD,16),(165,TEAL,12),(118,CRIMSON,8)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.03
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            lineglow(im,[(cx,cy),(x,y)],col,1,55,4)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_MED,fill=GOLD,anchor='mm')
    d.text((640,505),'the spokes of the wheel are the energies that radiate from the center',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    glow(im,(cx,cy),100,CRIMSON,40,26)
    for i in range(3):
        r=50+i*55
        for j in range(6+i*3):
            a=-math.pi/2+j*2*math.pi/(6+i*3)+t*.05*(1 if i%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
            col=mix(VIOLET,GOLD,i/2)
            d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,190))
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the wheels interlock — the energies of consciousness are one system',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    pairs=[(200,GOLD,18),(150,CRIMSON,14),(100,TEAL,10)]
    for r,col,n in pairs:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,115),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.04
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,170))
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the turning of the cakras is the pulse of consciousness itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24)
    for r,col in [(220,SLATE),(175,GOLD),(130,CRIMSON),(85,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
        for i in range(20-r//11):
            a=-math.pi/2+i*2*math.pi/(20-r//11)+t*.03
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,160))
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'चक्र',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the cakra seal: all wheels turn around one unmoving center',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('ca01','Wheels of Energy','Cakras as rotating fields of consciousness.','Cakra','The wheels of energy that structure awareness.','overview',['cakra','wheels','energy'],'overview','four-ring rotating node field',sc01),
Scene('ca02','Spokes and Rhythm','Each wheel has its own count.','Arāḥ','The spokes of each cakra are its unique energies.','spokes',['spokes','wheels','rhythm'],'structure','three wheels with different counts',sc02),
Scene('ca03','Wheels Within Wheels','Nested cakras.','Cakra-valaya','Cakras contain cakras at every level.','nested_wheels',['nested','wheels','levels'],'structure','five concentric rotating bands',sc03),
Scene('ca04','Harmony of Rhythms','The cosmos as interlocking cycles.','Cakra-tāla','Different cakras spin at different rates in harmony.','rhythm_harmony',['rhythm','harmony','cycles'],'dynamics','six dissappearing rings',sc04),
Scene('ca05','Spokes of Energy','Radiating from the center.','Arka-prabhā','The spokes are the energies that flow from the center.','energy_spokes',['spokes','energy','radiation'],'structure','three rings with radial spokes',sc05),
Scene('ca06','Interlocking Cakras','One system of energies.','Cakra-sāmarasya','The cakras interlock as one system.','interlocking',['interlocking','system','unity'],'synthesis','three interlocking bands',sc06),
Scene('ca07','The Pulse of Consciousness','The turning is awareness itself.','Cakra-spanda','The rotation of the cakras is the pulse of consciousness.','consciousness_pulse',['pulse','consciousness','turning'],'dynamics','three rings with node counts',sc07),
Scene('ca08','The Cakra Seal','All wheels around one center.','Cakra-cakra','Closing seal: all energies turning around the unmoving center.','closing_seal',['seal','wheels','center'],'seal','quadruple ring seal with rotating nodes',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=cakra_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Cakra: Wheels of Energy','source_basis':'Tantrāloka and Trika: cakras as rotating fields of consciousness, each with unique spokes, rhythms, interlocking as one system around the center.','style':{'family':'rotational-wheel cosmography','background':'deep night field','ink':'silver and slate','accent':'gold, crimson, teal, violet','materials':['rotating node rings','spoked wheels','concentric bands','interlocking circles','radial spokes']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['ca01'],'wheels_and_rhythm':['ca02','ca03','ca04'],'structure_and_synthesis':['ca05','ca06','ca07'],'seal':['ca08']},'reusability_notes':{'ca01':'Use for cakra overview.','ca02':'Use for spokes or wheel counts.','ca03':'Use for nested wheels.','ca04':'Use for rhythm or harmony.','ca05':'Use for spokes radiating.','ca06':'Use for interlocking energies.','ca07':'Use for pulse of consciousness.','ca08':'Use as closing cakra seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Cakra

## Aim
Visualize cakras: the rotating wheels of energy that structure consciousness, each with its own spokes, rhythm, and place in the interlocking whole.

## Structure
1. Cakras are wheels of energy
2. Each wheel has its own number of spokes
3. Wheels within wheels — nested structures
4. Harmony of different rhythms
5. Spokes radiate from the center
6. Cakras interlock as one system
7. The turning is the pulse of awareness
8. All wheels turn around one unmoving center

## Visual rules
- Rotating node fields as wheel representations.
- Each wheel has different spoke counts.
- Gold/teal/violet color progression from center outward.
- The center remains still while wheels turn.
- No anatomical chakra locations — abstract rotating fields.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Cakra Pack\n\n## Differentiation\nThis pack uses rotating wheel and node imagery — fields of orbiting points, concentric rings with spokes — distinct from the explosive arcs of Bhairava or the triangles of Trikona.\n\n## New symbols\n1. four-ring rotating node field\n2. three wheels with different counts\n3. five concentric rotating bands\n4. six disappearing rings\n5. three rings with radial spokes\n6. three interlocking bands\n7. three rings with node counts\n8. quadruple ring seal with rotating nodes\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Cakra Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'cakra_wheels_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'cakra_wheels_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['cakra_wheels_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','cakra_wheels_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'cakra_wheels_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
