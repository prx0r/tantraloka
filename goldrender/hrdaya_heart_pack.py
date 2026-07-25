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
SEED = 77777

# Heart-lotus palette
NIGHT = (18, 16, 22)
CRIMSON = (152, 42, 58)
CARDINAL = (188, 50, 66)
ROSE = (196, 102, 124)
GOLD = (206, 165, 86)
GOLD_LIGHT = (244, 214, 138)
IVORY = (248, 244, 236)
PARCHMENT = (242, 238, 228)
UMBER = (82, 66, 52)
SLATE = (108, 118, 136)
MIST = (178, 186, 200)
TEAL = (92, 146, 148)
INDIGO = (68, 78, 132)
DEEP_INDIGO = (46, 55, 98)
GREEN = (104, 152, 112)
WHITE = (252, 250, 246)
BLACK = (14, 14, 18)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 22)


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


def heart_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.8 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*16,0,24)[...,None]
    glow=np.exp(-(((xx-W/2)/(W*.22))**2+((yy-H*.42)/(H*.32))**2)*2.2)
    base[...,0]+=glow*22; base[...,1]+=glow*8; base[...,2]+=glow*10
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,105),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,80),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(16,14,20,206),outline=rgba(SLATE,60),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=IVORY)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=48):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(20,70))))
    im.alpha_composite(ov)

def draw_lotus(d,cx,cy,scale=1.0,col=CRIMSON,fill=None,petals=8):
    for i in range(petals):
        a=-math.pi/2+(i-(petals-1)/2)*0.28; rx=20*scale; ry=50*scale
        pts=[]
        for t in np.linspace(0,math.pi,20):
            x=math.sin(t)*rx; y=-math.cos(t)*ry*.65
            xr=x*math.cos(a)-y*math.sin(a); yr=x*math.sin(a)+y*math.cos(a)
            pts.append((cx+xr,cy+yr))
        for t in np.linspace(math.pi,0,20):
            x=math.sin(t)*rx*.5; y=math.cos(t)*ry*.2
            xr=x*math.cos(a)-y*math.sin(a); yr=x*math.sin(a)+y*math.cos(a)
            pts.append((cx+xr,cy+yr))
        d.polygon(pts,outline=rgba(col,200),fill=fill or rgba((255,255,255),20))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,CARDINAL,130,22)
    for r,col in [(180,CRIMSON),(130,ROSE),(80,GOLD)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,140),width=2)
    draw_lotus(d,cx,cy,.9,CARDINAL,rgba(CRIMSON,25),8)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'the heart is the abode of the whole universe of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    draw_lotus(d,cx,cy,1.1,CARDINAL,rgba(CRIMSON,28),16)
    glow(im,(cx,cy),50,GOLD_LIGHT,120,15)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*140; y=cy+math.sin(a)*140
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(ROSE,GOLD_LIGHT,i/12),180))
    d.text((640,505),'the lotus of the heart unfolds as the ground of all manifestation',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # heart as center of all paths
    pts=[(cx,cy-140),(cx+130,cy+50),(cx-80,cy+110),(cx-130,cy-20)]
    d.polygon(pts,outline=rgba(GOLD,160),fill=rgba(GOLD,25))
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*155; y=cy+math.sin(a)*100
        d.ellipse((x-14,y-14,x+14,y+14),outline=rgba(mix(TEAL,ROSE,i/6),180),fill=rgba((255,255,255),30),width=2)
        lineglow(im,[(cx,cy),(x,y)],mix(TEAL,ROSE,i/6),2,75,5)
    glow(im,(cx,cy),42,GOLD_LIGHT,110,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'all paths of knowing return to the heart as their source',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # pulse of spanda in the heart
    for i in range(8):
        r=30+i*28
        alpha=int(150*(1-i/8)*(.5+.5*math.sin(t*2*math.pi)))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(CARDINAL,GOLD,i/8),alpha),width=2)
    glow(im,(cx,cy),50,CARDINAL,110,15)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(CARDINAL,220),width=2)
    d.text((640,505),'spanda — the heart pulses as the self-awareness of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # heart contains all tattvas
    levels=[1,2,2,6,3,5,5]
    ys=np.linspace(140,410,len(levels))
    idx=1
    for li,(c,y) in enumerate(zip(levels,ys)):
        span=min(260,40*c)
        xs=np.linspace(cx-span/2,cx+span/2,c)
        for x in xs:
            col=mix(CRIMSON,TEAL,li/(len(levels)-1))
            d.ellipse((x-6,y-6,x+6,y+6),outline=rgba(col,170),fill=rgba(col,45),width=2)
            d.text((x,y+1),str(idx),font=TINY_FONT,fill=col,anchor='mm')
            idx+=1
    glow(im,(cx,cy),36,GOLD_LIGHT,100,12)
    d.text((640,505),'the heart contains the entire tattvic order within itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # subject and object held in one heart
    d.ellipse((cx-200,cy-130,cx+200,cy+130),outline=rgba(GOLD,120),width=2)
    d.ellipse((cx-140,cy-90,cx+140,cy+90),outline=rgba(CRIMSON,140),width=2)
    d.ellipse((cx-80,cy-55,cx+80,cy+55),outline=rgba(CARDINAL,170),width=2)
    glow(im,(cx,cy),44,GOLD_LIGHT,120,14)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i in range(2):
        a=-math.pi/2+i*math.pi; x=cx+math.cos(a)*120
        d.ellipse((x-12,cy-12,x+12,cy+12),fill=rgba(mix(ROSE,TEAL,i),150))
    d.text((380,195),'I',font=TERM_FONT,fill=ROSE,anchor='mm')
    d.text((900,195),'this',font=TERM_FONT,fill=TEAL,anchor='mm')
    d.text((640,505),'subject and object are held together in the heart\'s single field',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # three currents converging in heart
    cols=[CRIMSON,TEAL,GOLD]
    for i,col in enumerate(cols):
        a=-math.pi/2-i*0.4+i*0.4
        p0=(cx+math.cos(a)*220,cy+math.sin(a)*130)
        seg=partial(bezier(p0,(cx+math.cos(a)*130,cy+math.sin(a)*80),(cx+math.cos(a+.1)*60,cy+math.sin(a+.1)*40),(cx,cy),80),smooth(.05+i*.08,.84,t))
        if len(seg)>1:lineglow(im,seg,col,3,100,6)
        d.ellipse((p0[0]-10,p0[1]-10,p0[0]+10,p0[1]+10),fill=rgba(col,190))
    glow(im,(cx,cy),55,GOLD_LIGHT,130,16)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'knowing, known, and knower converge in the heart of awareness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # closing seal — heart lotus with all powers
    draw_lotus(d,cx,cy,1.0,CARDINAL,rgba(CRIMSON,22),12)
    for r,col in [(200,CRIMSON),(155,ROSE),(108,GOLD)]:
        d.ellipse((cx-r,cy-r*.7,cx+r,cy+r*.7),outline=rgba(col,130),width=2)
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12+t*.04
        x=cx+math.cos(a)*175; y=cy+math.sin(a)*120
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(ROSE,GOLD_LIGHT,i/12),180))
    glow(im,(cx,cy),55,GOLD_LIGHT,130,16)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'हृदय',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    d.text((640,505),'the heart-seal: all manifestation rests in one awareness',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('hr01','The Heart of Consciousness','The heart is the abode of the universe.','Hṛdaya','Overview: the heart as the ground of all manifestation.','overview',['heart','consciousness','abode'],'overview','heart lotus with rings',sc01),
Scene('hr02','The Lotus of the Heart','The sixteen-petalled lotus unfolds.','Hṛdaya-padma','The heart\'s lotus contains all powers of consciousness.','lotus_unfold',['lotus','heart','unfolding'],'structure','sixteen-petal lotus',sc02),
Scene('hr03','Center of All Paths','All paths of knowing converge in the heart.','Adhva-hṛdaya','The six paths return to the heart as their common source.','path_convergence',['paths','center','return'],'structure','six nodes around heart',sc03),
Scene('hr04','The Pulse of Spanda','The heart pulsates as self-awareness.','Spanda-hṛdaya','The subtle vibration of consciousness is felt in the heart.','heart_pulse',['spanda','pulse','vibration'],'dynamics','expanding pulse rings',sc04),
Scene('hr05','The Heart Contains the Tattvas','All thirty-six levels are present within the heart.','Tattva-hṛdaya','The ontological order is not external to awareness.','tattvic_heart',['tattvas','containment','heart'],'structure','condensed ladder in heart',sc05),
Scene('hr06','Subject and Object in One Field','I and this are held together.','Aham-idam-hṛdaya','The duality of subject and object is enclosed within one heart.','dual_containment',['subject','object','nonduality'],'synthesis','nested chambers',sc06),
Scene('hr07','Three Currents Converge','Knowing, known, and knower meet in the heart.','Pramātṛ-pramāṇa-prameya','The three factors of cognition converge in one awareness.','triple_convergence',['knower','knowing','known'],'synthesis','three converging rays',sc07),
Scene('hr08','The Hṛdaya Seal','All powers of consciousness gathered in the heart.','Hṛdaya-cakra','The closing seal: heart as the center of all.','closing_seal',['seal','heart','awareness'],'seal','lotus cosmogram',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=heart_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,40); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
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
    manifest={'project':'Tantrāloka — Hṛdaya: The Heart of Consciousness','source_basis':'Tantrāloka and Trika heart-doctrine: the heart as the abode of the universe, spanda as self-awareness, and the convergence of all paths.','style':{'family':'cardiac-lotus cosmography','background':'deep night with crimson-gold heart glow','ink':'slate and mist','accent':'crimson, cardinal, rose, gold, teal','materials':['lotus petals','pulse rings','converging rays','nested chambers','tattvic ladder']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['hr01'],'heart_structure':['hr02','hr03','hr05'],'heart_dynamics':['hr04','hr06','hr07'],'seal':['hr08']},'reusability_notes':{'hr01':'Use for heart doctrine overview.','hr02':'Use for lotus symbolism or heart unfolding.','hr03':'Use as center of all paths or return of paths.','hr04':'Use for spanda or pulse of awareness.','hr05':'Use for heart containing the tattvas.','hr06':'Use for subject-object nonduality.','hr07':'Use for convergence of knower-known-knowing.','hr08':'Use as closing heart-lotus seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Hṛdaya: The Heart of Consciousness

## Aim
Visualize the heart (hṛdaya) as the central doctrine of Trika Shaivism: the abode of the entire universe of consciousness.

## Core structure
1. The heart is the ground of all manifestation
2. The lotus of the heart unfolds in sixteen petals
3. All six paths converge in the heart
4. Spanda is the heart's pulse of self-awareness
5. The heart contains the tattvic order
6. Subject and object are held together in one heart-field
7. Knower, knowing, and known converge
8. The heart-seal gathers all powers

## Visual rules
- The heart is not a physical organ — it is the center of consciousness.
- Use lotus, pulse, and convergence motifs.
- Crimson and gold for heart-presence; teal for objectivity.
- All forms return to the center.

## New motifs
- heart lotus with rings
- sixteen-petal lotus unfold
- six-nodal path convergence
- spanda pulse rings
- tattvic ladder in heart
- subject-object nested chambers
- three-ray convergence
- heart-lotus closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Hṛdaya Pack

## Differentiation
Where the Tattva pack emphasized structural descent and the Āmnāya pack emphasized directional transmission, this pack emphasizes interiority, convergence, and the heart as the living center.

## New symbols
1. heart lotus overview
2. sixteen-petal lotus unfold
3. six-nodal convergence wheel
4. spanda pulse rings
5. condensed tattva ladder
6. subject-object nested ellipses
7. three-ray convergence
8. heart-lotus closing seal

## Relationships
- heart → ground of all manifestation
- lotus → unfolding of powers
- paths → convergence in the center
- spanda → pulse of self-awareness
- subject + object → one heart-field
- knower + knowing + known → one awareness

## Material vocabulary
- deep night background
- crimson heart-glow
- cardinal lotus lacquer
- rose unfolding petals
- gold center-light
- teal objective field

## Closing seal
A twelve-petal lotus cosmogram with the Sanskrit हृदय at the radiant center.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Hṛdaya: The Heart of Consciousness Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run:
```bash
python render_pack.py
```
The renderer is resume-safe.
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'hrdaya_heart_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'hrdaya_heart_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['hrdaya_heart_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','hrdaya_heart_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'hrdaya_heart_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
