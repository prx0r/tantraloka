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
SEED = 51401

PARCHMENT = (243, 237, 226)
PARCHMENT_LIGHT = (250, 246, 238)
OBSIDIAN = (30, 27, 25)
AMBER = (195, 150, 80)
AMBER_DARK = (155, 115, 55)
AMBER_LIGHT = (235, 200, 130)
RUST = (160, 80, 50)
RUST_DARK = (120, 55, 30)
THRESHOLD = (85, 70, 60)
THRESHOLD_LIGHT = (130, 115, 100)
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
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(PARCHMENT,dtype=np.float32)
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
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(THRESHOLD_LIGHT,140),outline=rgba(AMBER,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(AMBER_LIGHT,110),outline=rgba(OBSIDIAN,180),width=2)

def dust(im,seed,count=40):
    rng=np.random.default_rng(seed); d=ImageDraw.Draw(im)
    for _ in range(count):
        x=int(rng.uniform(0,W)); y=int(rng.uniform(0,H)); s=rng.uniform(0.5,2.0); a=int(rng.uniform(20,70))
        d.ellipse((x-s,y-s,x+s,y+s),fill=rgba(AMBER,a))

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(THRESHOLD,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(AMBER,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(245,240,232,220),outline=rgba(THRESHOLD,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=OBSIDIAN)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=THRESHOLD)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=RUST_DARK)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    d.ellipse((cx-230,cy-160,cx+230,cy+160),outline=rgba(AMBER,175),width=3)
    d.ellipse((cx-225,cy-155,cx+225,cy+155),outline=rgba(OBSIDIAN,90),width=1)
    for i,side in enumerate([-1,1]):
        a=-math.pi/3+i*2*math.pi/3
        pts=[]
        for j in range(30):
            u=j/29; r=lerp(30,220,u)
            pts.append((cx+side*math.cos(a+u*0.8)*r,cy+math.sin(a+u*0.8)*r*0.75))
        trail=partial(pts,smooth(.05,.9,t))
        if len(trail)>1: line_glow(im,trail,mix(AMBER,RUST,side/2+.5),2,85,6)
    glow(im,(cx,cy),45,AMBER_LIGHT,130,14)
    d.text((cx,cy),'द्वे',font=DEVA_BIG,fill=OBSIDIAN,anchor='mm')
    d.text((640,505),'The Lord has two modes: obscuration and grace — both are freedom',font=SUB_FONT,fill=THRESHOLD,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(3):
        r=lerp(30,200,smooth(.05+.1*i,.8,t))
        d.ellipse((cx-r,cy-r*0.7,cx+r,cy+r*0.7),outline=rgba(mix(THRESHOLD,AMBER,i/3),120),width=2)
    d.line((cx-180,cy,cx+180,cy),fill=rgba(AMBER,140),width=2)
    d.line((cx,cy-120,cx,cy+120),fill=rgba(AMBER,140),width=2)
    glow(im,(cx,cy-20),40,AMBER_LIGHT,110,12)
    d.text((cx,cy),'कर्म',font=DEVA_MED,fill=OBSIDIAN,anchor='mm')
    d.text((640,505),'Initiation cuts beyond karma — the Lord\'s grace is not governed by past action',font=SUB_FONT,fill=THRESHOLD,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),80,AMBER_LIGHT,100,18)
    for i in range(16):
        a=i*2*math.pi/16+t*0.03
        r1=lerp(50,210,smooth(.1,.85,t))
        x1=cx+math.cos(a)*r1; y1=cy+math.sin(a)*r1*0.65
        x2=cx+math.cos(a+math.pi/16)*r1*0.85; y2=cy+math.sin(a+math.pi/16)*r1*0.55
        d.line(((x1,y1),(x2,y2)),fill=rgba(mix(RUST,AMBER,(i%4)/4),130),width=2)
    d.text((cx,cy-10),'आच्छादन',font=DEVA_MED,fill=RUST_DARK,anchor='mm')
    d.text((640,505),'The Lord conceals and reveals enlightenment through his own freedom',font=SUB_FONT,fill=THRESHOLD,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        pts=[]
        for j in range(25):
            u=j/24; r=lerp(40,210,u)
            pts.append((cx+math.cos(a+u*0.6)*r,cy+math.sin(a+u*0.6)*r*0.7))
        trail=partial(pts,smooth(.05+.1*i,.85,t))
        if len(trail)>1: line_glow(im,trail,mix(AMBER,RUST,i/4),3,90,7)
    glow(im,(cx,cy-20),55,AMBER,120,15)
    d.text((cx,cy),'पञ्च',font=DEVA_MED,fill=OBSIDIAN,anchor='mm')
    d.text((cx,195),'pañca kṛtya',font=TERM_FONT,fill=AMBER,anchor='mm')
    d.text((640,505),'The five tasks of Śiva: creation, maintenance, dissolution, concealment, grace',font=SUB_FONT,fill=THRESHOLD,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    glow(im,(cx,cy-30),70,RUST,120,16)
    for i in range(12):
        a=i*2*math.pi/12
        pts=partial(bezier((cx,cy),(cx+math.cos(a)*80,cy+math.sin(a)*80-60),(cx+math.cos(a)*180,cy+math.sin(a)*180-20),(cx+math.cos(a)*220,cy+math.sin(a)*220*0.7),60),smooth(.05,.88,t))
        if len(pts)>1: line_glow(im,pts,mix(OBSIDIAN,RUST,(i%3)/3),2,65,5)
    d.text((cx,cy-15),'माया',font=DEVA_MED,fill=RUST_DARK,anchor='mm')
    d.text((640,505),'Yogic powers delude when mistaken for the ultimate — they are signs, not the goal',font=SUB_FONT,fill=THRESHOLD,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    d.rectangle((cx-150,cy-80,cx+150,cy+80),outline=rgba(AMBER,160),width=3,fill=rgba(PARCHMENT_LIGHT,60))
    for i in range(8):
        a=i*2*math.pi/8; xs=[-1,1]; ys=[-1,1]
        for sx in xs:
            for sy in ys:
                x=cx+sx*120*math.cos(a)*0.6; y=cy+sy*60*math.sin(a)*0.6
                if smooth(.05,.8,t)>i*0.1:
                    d.line(((cx,cy),(x,y)),fill=rgba(RUST,110),width=2)
    glow(im,(cx,cy-5),30,AMBER_LIGHT,90,10)
    d.text((cx,cy),'मोक्ष',font=DEVA_MED,fill=OBSIDIAN,anchor='mm')
    d.text((640,505),'Forced exit from the body brings no freedom — liberation is already the case',font=SUB_FONT,fill=THRESHOLD,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),90,AMBER_LIGHT,150,22)
    for i in range(24):
        a=i*2*math.pi/24
        r=lerp(20,230,smooth(.02,.92,t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(AMBER,RUST,i/24),175),outline=rgba(AMBER_DARK,120),width=1)
    d.text((cx,cy),'जीवन्मुक्ति',font=DEVA_MED,fill=OBSIDIAN,anchor='mm')
    d.text((cx,190),'jīvanmukti',font=TERM_FONT,fill=AMBER,anchor='mm')
    d.text((640,505),'Freedom is attainable in this life — not after death, but here and now',font=SUB_FONT,fill=THRESHOLD,anchor='mm')


SCENES=[
Scene('ip01','The Lord\'s Two Modes','Obscuration and grace — both are expressions of the Lord\'s freedom.','Dve','The Lord has two fundamental modes: obscuration and grace.','overview',['śiva','modes','obscuration','grace'],'overview','two-mode ellipse field',sc01),
Scene('ip02','Beyond Karma','Grace is not governed by past action.','Karma','Initiation cuts through the chain of karma entirely.','threshold',['karma','grace','initiation'],'foundation','crossed-karma axis',sc02),
Scene('ip03','Concealing and Revealing','The Lord veils and unveils enlightenment through his own freedom.','Ācchādana','Enlightenment is concealed or revealed by the Lord\'s free will.','concealment',['concealment','revelation','enlightenment'],'foundation','veil aperture ring',sc03),
Scene('ip04','Five Tasks of Śiva','The fivefold activity of the supreme Lord.','Pañca Kṛtya','Creation, maintenance, dissolution, concealment, and grace.','cosmic',['pañca kṛtya','śiva','tasks'],'cosmic','five-stream rays',sc04),
Scene('ip05','Delusion of Yogic Powers','Powers are signs, not the goal.','Māyā','Mistaking yogic powers for the ultimate leads to delusion.','warning',['yogic powers','delusion','māyā'],'warning','power entanglement web',sc05),
Scene('ip06','Futility of Forced Exit','Liberation is not achieved by forcing the soul out.','Mokṣa','No forced departure from the body can bring freedom.','teaching',['forced exit','liberation','body'],'teaching','blocked gate rectangle',sc06),
Scene('ip07','Freedom in This Life','Liberation is attainable here and now.','Jīvanmukti','Full enlightenment can be realized in this very lifetime.','seal',['jīvanmukti','freedom','embodiment'],'seal','radiant field seal',sc07),
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
    sheet=Image.new('RGB',(4*320,3*180),PARCHMENT)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — Initiation Philosophy','source_basis':'Tantrāloka Chapter 14: Preamble to Initiation (dīkṣopakramaṇam).','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'threshold-crossing and initiation preamble','background':'parchment with amber tint','materials':['parchment','obsidian ink','amber light','rust threshold','threshold stone']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'foundation':['ip01','ip02'],'cosmic':['ip03','ip04'],'warning':['ip05','ip06'],'seal':['ip07']},'reusability_notes':{'ip01':'Use for the two modes of Śiva or grace/obscuration.','ip02':'Use for karma-transcendence or initiation power.','ip03':'Use for concealment/revelation of enlightenment.','ip04':'Use for the five cosmic tasks.','ip05':'Use for yogic power delusion warning.','ip06':'Use for futility of forced liberation.','ip07':'Use for jīvanmukti closing seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Initiation Philosophy (Chapter 14)

## Aim
This pack visualizes Tantrāloka Chapter 14, the preamble to initiation (dīkṣopakramaṇam), establishing the philosophical ground of dīkṣā.

## Core structure
- The Lord has two modes: obscuration (tirodhāna) and grace (anugraha).
- Initiation cuts beyond karma — grace is not a reward for past action.
- Enlightenment is concealed or revealed by the Lord's freedom.
- The five tasks of Śiva encompass all cosmic and spiritual activity.
- Yogic powers can delude when mistaken for the ultimate.
- Forced departure from the body cannot achieve liberation.
- Freedom is attainable in this life (jīvanmukti).

## Visual rules
- Parchment tones must suggest age and authority.
- Use threshold imagery — doorways, apertures, crossing points.
- Amber represents grace; rust represents obscuration.
- Do not depict the Lord anthropomorphically.
- Keep the feeling preparatory: these scenes open into initiation.

## Style family
Parchment field, obsidian ink, amber threshold-light, rust obscuration, and threshold stone boundaries.

## Guardrails
- Avoid representing Śiva as a person; use geometric modes.
- Grace must not appear as sentimental; it is a structural reality.
- Jīvanmukti is not self-congratulatory — it is the recognition of already-existing freedom.
- Do not imply that karma is merely erased; it is cut through.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Initiation Philosophy Pack

## Differentiation
This pack establishes a threshold-crossing visual language distinct from the reflective/phonemic palette of earlier packs.

## New symbols
1. two-mode double ellipse
2. crossed-karma axis lines
3. veiling aperture ring
4. five-stream task rays
5. power entanglement web
6. blocked gate rectangle
7. radiance field seal

## New relationships
- Lord → two modes of obscuration and grace
- initiation → cutting beyond karma
- enlightenment → concealment/revelation
- five tasks → cosmic activity
- yogic powers → delusion risk
- freedom → this-life attainment

## Material vocabulary
Parchment, obsidian ink, amber threshold-light, rust obscuration, threshold stone.

## Closing seal
A radiant circular field of 24 amber-rust points surrounding the Sanskrit term jīvanmukti, affirming freedom in this life.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Initiation Philosophy Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'initiation_philosophy_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'initiation_philosophy_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['initiation_philosophy_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    out=ROOT/'initiation_philosophy_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
