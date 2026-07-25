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
SEED = 66666

# Mudrā palette — gesture seals, hand-symbols
NIGHT = (20, 18, 24)
OBSIDIAN = (28, 26, 32)
DEEP_INDIGO = (44, 50, 90)
INDIGO = (70, 78, 136)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60)
CARDINAL = (188, 56, 72)
ROSE = (194, 106, 130)
TEAL = (92, 146, 148)
IVORY = (247, 244, 236)
WHITE = (252, 250, 246)
UMBER = (80, 64, 50)
SLATE = (106, 116, 134)
MIST = (176, 184, 198)
SAFFRON = (224, 152, 56)
GREEN = (106, 152, 114)

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


def gesture_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.8 + fine[...,None]*1.05
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.32))**2+((yy-H*.40)/(H*.26))**2)*2.6)
    base[...,0]+=halo*10; base[...,1]+=halo*14; base[...,2]+=halo*22
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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CARDINAL,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(18,16,22,206),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=IVORY)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=45):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,62))))
    im.alpha_composite(ov)

def finger(d,cx,cy,ang,length,col,width=5):
    x1=cx+math.cos(ang)*length; y1=cy+math.sin(ang)*length
    d.line((cx,cy,x1,y1),fill=rgba(col,190),width=width)
    d.ellipse((x1-6,y1-6,x1+6,y1+6),fill=rgba(col,200))
    return (x1,y1)

def hand_outline(d,cx,cy,scale=1.0,col=IVORY):
    d.ellipse((cx-28*scale,cy-22*scale,cx+28*scale,cy+30*scale),outline=rgba(col,180),fill=rgba(col,15),width=2)
    angles=[-1.0,-0.3,0.3,0.9,1.5]
    for i,a in enumerate(angles):
        l=lerp(55,85,abs(a)/1.5)*scale; finger(d,cx+math.cos(a)*10*scale,cy-20*scale,a-0.2,l,col,3)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),60,GOLD_LIGHT,130,20)
    hand_outline(d,cx,cy,1.3,IVORY)
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8; x=cx+math.cos(a)*170; y=cy+math.sin(a)*115
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,TEAL,i/8),170))
    d.text((640,505),'mudrā — the hand becomes a seal of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # abhaya-mudrā
    hand_outline(d,cx-40,cy,1.1,IVORY)
    # fearlessness rays
    for i in range(14):
        a=-math.pi/2+i*2*math.pi/14; x=cx+math.cos(a)*200; y=cy+math.sin(a)*130
        seg=partial([(cx+60,cy-40),(x,y)],smooth(.03+i*.04,.82,t))
        col=mix(GOLD_LIGHT,TEAL,i/13)
        if len(seg)>1:lineglow(im,seg,col,2,70,5)
    glow(im,(cx+60,cy-40),25,GOLD_LIGHT,110,10)
    d.ellipse((cx+46,cy-54,cx+74,cy-26),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'abhaya-mudrā — the gesture of fearlessness and protection',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # jñāna-mudrā
    hand_outline(d,cx-60,cy,1.0,IVORY)
    # index finger touching thumb circle
    d.ellipse((cx-38,cy-62,cx-6,cy-30),outline=rgba(GOLD_LIGHT,220),width=3)
    # radiance from the circle
    for i in range(10):
        a=i*2*math.pi/10+t*.06; r=100+40*ease(t)
        x=cx-22+math.cos(a)*r; y=cy-46+math.sin(a)*r*.6
        col=mix(GOLD_LIGHT,WHITE,i/10)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,180))
    glow(im,(cx-22,cy-46),30,GOLD_LIGHT,120,12)
    d.text((640,505),'jñāna-mudrā — the gesture of knowledge: finger and thumb meet',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # dhyāna-mudrā
    d.ellipse((cx-80,cy-50,cx+80,cy+50),outline=rgba(GOLD,150),fill=rgba(GOLD,18),width=2)
    d.ellipse((cx-60,cy-35,cx+60,cy+35),outline=rgba(GOLD_LIGHT,120),width=2)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*70; y=cy+math.sin(a)*35
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(CRIMSON,GOLD,i/8),160))
    glow(im,(cx,cy),40,GOLD_LIGHT,110,14)
    d.text((640,505),'dhyāna-mudrā — the gesture of meditation and receptivity',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # varada-mudrā
    hand_outline(d,cx,cy+40,1.0,IVORY)
    for i in range(6):
        a=math.pi/2+i*math.pi/5-math.pi/4
        x=cx+math.cos(a)*(120+30*ease(t)); y=cy+math.sin(a)*(120+30*ease(t))
        seg=partial([(cx-30,cy+80),(x,y)],smooth(.05+i*.06,.82,t))
        col=mix(GOLD,TEAL,i/5)
        if len(seg)>1:lineglow(im,seg,col,3,90,6)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,190))
    glow(im,(cx-30,cy+80),25,GOLD_LIGHT,100,12)
    d.text((640,505),'varada-mudrā — the gesture of boon-granting and compassion',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # karaṇa-mudrā
    hand_outline(d,cx,cy-20,1.2,IVORY)
    for i in range(5):
        a=math.pi+i*2*math.pi/5
        x=cx+math.cos(a)*(140+20*ease(t)); y=cy+math.sin(a)*(90+15*ease(t))
        seg=partial([(cx+10,cy-10),(x,y)],smooth(.04+i*.06,.8,t))
        col=mix(CRIMSON,SAFFRON,i/4)
        if len(seg)>1:lineglow(im,seg,col,3,95,6)
    glow(im,(cx+10,cy-10),20,CARDINAL,90,10)
    d.text((640,505),'karaṇa-mudrā — the gesture that dispels negativity',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # five mudrās
    names=['abhaya','jñāna','dhyāna','varada','karaṇa']
    cols=[TEAL,GOLD,GREEN,CRIMSON,SAFFRON]
    for i,(lab,col) in enumerate(zip(names,cols)):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*115
        hand_outline(d,x,y,.6,mix(IVORY,col,.2))
        d.text((x,y+50),lab,font=TINY_FONT,fill=col,anchor='mm')
        seg=partial([(cx,cy),(x,y)],smooth(.03+i*.06,.8,t))
        if len(seg)>1:lineglow(im,seg,col,2,70,5)
    glow(im,(cx,cy),45,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'five mudrās — each seal enacts a specific power of awareness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # closing seal — the cosmic hand
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    hand_outline(d,cx,cy,1.1,IVORY)
    for r,col in [(200,GOLD),(150,CARDINAL),(100,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    for i in range(14):
        a=-math.pi/2+i*2*math.pi/14+t*.04; x=cx+math.cos(a)*180; y=cy+math.sin(a)*120
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD_LIGHT,INDIGO,i/14),170))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'the seal of mudrā: every gesture is a signature of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('mu01','The Language of Mudrā','Hand-seals as gestures of consciousness.','Mudrā','Overview: mudrā as symbolic gestures that enact spiritual power.','overview',['mudra','gesture','seal'],'overview','hand with radiant nodes',sc01),
Scene('mu02','Abhaya-mudrā','The gesture of fearlessness.','Abhaya','Protection and fearlessness radiate from the open hand.','fearlessness',['fearlessness','protection','hand'],'gesture','open hand with radiating rays',sc02),
Scene('mu03','Jñāna-mudrā','The gesture of knowledge.','Jñāna','The finger and thumb circle generates knowing.','knowledge_gesture',['knowledge','finger','thumb'],'gesture','finger-thumb circle with radiance',sc03),
Scene('mu04','Dhyāna-mudrā','The gesture of meditation.','Dhyāna','The receptive hand-shape of contemplative stillness.','meditation_gesture',['meditation','stillness','receptivity'],'gesture','nested ellipses',sc04),
Scene('mu05','Varada-mudrā','The gesture of boon-granting.','Varada','Compassion flows downward from the open hand.','boon_granting',['boon','compassion','giving'],'gesture','descending boon rays',sc05),
Scene('mu06','Karaṇa-mudrā','The gesture that dispels.','Karaṇa','Negativity is expelled through the raised hand.','dispelling',['dispelling','protection','negativity'],'gesture','outward expelling arcs',sc06),
Scene('mu07','The Five Mudrās','Five gestures, five powers of awareness.','Pañca-mudrā','Each mudrā enacts a distinct function of consciousness.','five_gestures',['five','gestures','powers'],'synthesis','five hands in orbit',sc07),
Scene('mu08','The Mudrā Seal','Every gesture is a signature of consciousness.','Mudrā-cakra','Closing seal: the cosmic hand as the seal of all power.','closing_seal',['seal','hand','gesture'],'seal','cosmic hand with rings',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=gesture_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Mudrā: Gesture Seals of Consciousness','source_basis':'Tantrāloka and Trika doctrine of mudrā: hand-seals as enactments of spiritual power, knowledge, protection, and compassion.','style':{'family':'gesture-seal cosmography','background':'deep indigo night','ink':'slate and mist','accent':'gold, cardinal, teal, saffron, white','materials':['hand outlines','finger-thumb circles','radiating rays','descending boon arcs','expelling lines','cosmic hand']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['mu01'],'individual_gestures':['mu02','mu03','mu04','mu05','mu06'],'synthesis_and_seal':['mu07','mu08']},'reusability_notes':{'mu01':'Use for mudrā or gesture overview.','mu02':'Use for fearlessness or protection gesture.','mu03':'Use for knowledge gesture.','mu04':'Use for meditation mudrā.','mu05':'Use for compassion or boon-giving.','mu06':'Use for dispelling negativity.','mu07':'Use for five mudrās summary.','mu08':'Use as closing gesture seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Mudrā: Gesture Seals

## Aim
Visualize the Tantrāloka doctrine of mudrā: hand-seals as enactments of consciousness's powers.

## Structure
1. Mudrā is the language of gesture
2. Abhaya — fearlessness radiates from the open hand
3. Jñāna — knowledge through finger-thumb circle
4. Dhyāna — meditative receptivity
5. Varada — compassion flows as boon
6. Karaṇa — dispelling negativity
7. Five mudrās as five powers
8. The cosmic hand seal

## Visual rules
- Hand outlines are the primary motif, rendered in ivory.
- Each mudrā has a characteristic energy direction (outward, inward, downward).
- Gold for knowledge and protection; cardinal for dispelling.
- Avoid realistic hands — use stylized diagrammatic outlines.

## New motifs
- hand with radiant nodes
- open hand with radiating rays
- finger-thumb circle with knowledge radiance
- nested meditative ellipses
- descending boon rays
- outward expelling arcs
- five hands in orbital wheel
- cosmic hand with rings
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Mudrā Pack

## Differentiation
This pack uses hand-gesture motifs distinct from every other pack — the human hand as the primary symbolic vehicle.

## New symbols
1. hand outline with power nodes
2. abhaya radiant open hand
3. jñāna finger-thumb circle
4. dhyāna nested ellipses
5. varada descending rays
6. karaṇa outward arcs
7. five-hand orbital wheel
8. cosmic hand closing seal

## Material vocabulary
- deep indigo night
- ivory hand silhouettes
- gold knowledge-light
- cardinal dispelling-fire
- teal boon-receiving

## Closing seal
A cosmic hand enclosed in three concentric rings with fourteen golden gesture-nodes.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Mudrā: Gesture Seals Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'mudra_gesture_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'mudra_gesture_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['mudra_gesture_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','mudra_gesture_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'mudra_gesture_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
