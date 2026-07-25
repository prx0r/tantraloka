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
SEED = 99999

# Five Prāṇas palette — vital currents
PARCHMENT = (244, 240, 232)
PARCHMENT_LIGHT = (250, 247, 240)
INK = (34, 38, 44)
UMBER = (82, 68, 54)
SLATE = (106, 118, 138)
DEEP_SLATE = (78, 88, 104)
MIST = (176, 186, 200)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60)
CARDINAL = (188, 56, 72)
ROSE = (194, 106, 130)
TEAL = (90, 146, 148)
DEEP_TEAL = (64, 112, 114)
GREEN = (106, 152, 114)
DEEP_GREEN = (78, 120, 82)
INDIGO = (68, 78, 136)
DEEP_INDIGO = (46, 56, 104)
WHITE = (252, 250, 246)
NIGHT = (18, 20, 26)
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


def prana_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PARCHMENT,dtype=np.float32)
    coarse=rng.normal(0,1,(38,68)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.0 + fine[...,None]*0.85
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*4,0,12)[...,None]*0.5
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
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def axial_current(d,cx,y0,y1,col,width=2):
    d.line((cx,y0,cx,y1),fill=rgba(col,150),width=width)
    for y in np.linspace(y0,y1,8):
        d.line((cx-14,y,cx+14,y),fill=rgba(col,90),width=1)

def flow_arrow(d,x0,y0,x1,y1,col):
    d.line((x0,y0,x1,y1),fill=rgba(col,190),width=3)
    ang=math.atan2(y1-y0,x1-x0); s=10
    d.polygon([(x1,y1),(x1-math.cos(ang-.4)*s,y1-math.sin(ang-.4)*s),(x1-math.cos(ang+.4)*s,y1-math.sin(ang+.4)*s)],fill=rgba(col,220))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    axial_current(d,cx,140,440,SLATE,3)
    glow(im,(cx,cy),45,GOLD_LIGHT,120,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'प्राण',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    pranas=[(cx-90,170,CARDINAL,'प्राण'),(cx+90,250,TEAL,'अपान'),(cx,310,GOLD,'समान'),(cx-80,390,INDIGO,'उदान'),(cx+80,430,GREEN,'व्यान')]
    for x,y,col,lab in pranas:
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,190),fill=rgba(col,28),width=2)
        d.text((x,y-26),lab,font=DEVA_SMALL,fill=col,anchor='mm')
        lineglow(im,[(cx,lerp(140,440,pranas.index((x,y,col,lab))/4)),(x,y)],col,2,70,5)
    d.text((640,505),'the five vital breaths — one current, five functions',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_current(d,cx,140,440,SLATE,2)
    glow(im,(cx,cy-60),30,CARDINAL,110,12)
    d.ellipse((cx-12,cy-74,cx+12,cy-46),fill=rgba(WHITE,255),outline=rgba(CARDINAL,220),width=2)
    d.text((cx,cy-60),'प्राण',font=DEVA_SMALL,fill=CARDINAL,anchor='mm')
    pts=[]
    for i in range(50):
        u=i/49; x=cx+math.sin(u*math.pi*3)*30*ease(t); y=lerp(cy-30,cy+130,u)
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,CARDINAL,4,115,8)
    for i in range(6):
        y=lerp(cy-20,cy+120,i/5); d.ellipse((cx-5,y-5,cx+5,y+5),fill=rgba(CARDINAL,160))
    d.text((640,505),'prāṇa — the forward current from the heart upward',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_current(d,cx,140,440,SLATE,2)
    glow(im,(cx,cy+80),30,TEAL,110,12)
    d.ellipse((cx-12,cy+66,cx+12,cy+94),fill=rgba(WHITE,255),outline=rgba(TEAL,220),width=2)
    d.text((cx,cy+80),'अपान',font=DEVA_SMALL,fill=TEAL,anchor='mm')
    pts=[]
    for i in range(50):
        u=i/49; x=cx+math.sin(u*math.pi*3)*25*ease(t); y=lerp(cy+30,cy-130,u)
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,TEAL,4,115,8)
    for i in range(5):
        y=lerp(cy+20,cy-100,i/4); d.ellipse((cx-4,y-4,cx+4,y+4),fill=rgba(TEAL,160))
    d.text((640,505),'apāna — the descending current from the navel downward',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_current(d,cx,140,440,SLATE,2)
    glow(im,(cx,cy),35,GOLD,120,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'समान',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(10):
        a=i*2*math.pi/10; r=lerp(15,95,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GOLD,GOLD_LIGHT,i/9)
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,180))
        lineglow(im,[(cx,cy),(x,y)],col,2,70,5)
    d.text((640,505),'samāna — the radial current of balance and integration',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_current(d,cx,140,440,SLATE,2)
    glow(im,(cx,cy-100),30,INDIGO,110,12)
    d.ellipse((cx-12,cy-114,cx+12,cy-86),fill=rgba(WHITE,255),outline=rgba(INDIGO,220),width=2)
    d.text((cx,cy-100),'उदान',font=DEVA_SMALL,fill=INDIGO,anchor='mm')
    pts=[]
    for i in range(60):
        u=i/59; x=cx+math.sin(u*math.pi*2)*18*ease(t); y=lerp(cy-90,cy+130,u)
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,INDIGO,4,115,8)
    for i in range(7):
        y=lerp(cy-80,cy+120,i/6); d.ellipse((cx-3,y-3,cx+3,y+3),fill=rgba(INDIGO,160))
    d.text((640,505),'udāna — the ascending current from the throat to the crown',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_current(d,cx,140,440,SLATE,2)
    glow(im,(cx,cy),45,GREEN,120,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GREEN,220),width=2)
    d.text((cx,cy),'व्यान',font=DEVA_SMALL,fill=GREEN,anchor='mm')
    for i in range(16):
        a=i*2*math.pi/16+t*.04; r=lerp(20,140,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GREEN,GOLD_LIGHT,i/15)
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,175))
        lineglow(im,[(cx,cy),(x,y)],col,2,65,5)
    d.text((640,505),'vyāna — the pervasive current through the entire field',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    axial_current(d,cx,140,440,SLATE,3)
    glow(im,(cx,cy),40,GOLD_LIGHT,110,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'प्राणाः',font=DEVA_MED,fill=GOLD,anchor='mm')
    cols=[CARDINAL,TEAL,GOLD,INDIGO,GREEN]
    for i,col in enumerate(cols):
        a=-math.pi/2+i*2*math.pi/5; x=cx+math.cos(a)*150; y=cy+math.sin(a)*95
        seg=partial([(cx,cy),(x,y)],smooth(.03+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,3,90,6)
        d.ellipse((x-11,y-11,x+11,y+11),outline=rgba(col,190),fill=rgba(col,28),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,180))
    d.text((640,505),'the five prāṇas are one life-force expressed through five functions',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_current(d,cx,140,440,SLATE,2)
    for r,col,n in [(210,GOLD,5),(158,CARDINAL,5),(106,TEAL,5)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.04; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(col,WHITE,i/n),175))
    glow(im,(cx,cy),50,GOLD_LIGHT,130,18)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'प्राण',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    d.text((640,505),'the prāṇa seal: one life-current flowing through five gates',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('pr01','The Five Prāṇas','The five vital breaths of the body.','Pañca-prāṇa','Overview: prāṇa, apāna, samāna, udāna, and vyāna.','overview',['prana','breath','five'],'overview','body with five prāṇa nodes',sc01),
Scene('pr02','Prāṇa','The forward-moving breath.','Prāṇa','The breath that governs the upper body, inhalation, and reception.','forward_breath',['prana','forward','upper'],'individual','central column with descending pulse',sc02),
Scene('pr03','Apāna','The downward-moving breath.','Apāna','The breath that governs elimination and grounding.','downward_breath',['apana','downward','elimination'],'individual','central column with ascending pulse',sc03),
Scene('pr04','Samāna','The balancing breath.','Samāna','The breath that regulates digestion and integration at the navel.','balancing_breath',['samana','balance','digestion'],'individual','navel radial expansion',sc04),
Scene('pr05','Udāna','The upward-moving breath.','Udāna','The breath that governs speech, ascent, and the transition at death.','upward_breath',['udana','upward','speech'],'individual','thin ascending thread',sc05),
Scene('pr06','Vyāna','The pervasive breath.','Vyāna','The breath that moves through the entire body network.','pervasive_breath',['vyana','pervasion','network'],'individual','radial pervasive emission',sc06),
Scene('pr07','The Fivefold Unity','One life expressed through five functions.','Pañcaikya','The five breaths are one prāṇa differentiated by function.','fivefold_unity',['unity','five','prana'],'synthesis','five rays from center in body',sc07),
Scene('pr08','The Prāṇa Seal','One life-current flowing through five gates.','Prāṇa-cakra','Closing seal: the five breaths as a single vital field.','closing_seal',['seal','prana','breath'],'seal','three concentric rings with five nodes each',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=prana_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,35); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=94)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(p).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),PARCHMENT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Pañca-prāṇa: The Five Vital Breaths','source_basis':'Tantrāloka and Trika prāṇa-vidyā: prāṇa, apāna, samāna, udāna, vyāna as the five currents of life-energy.','style':{'family':'vital-current cosmography','background':'warm parchment body-field','ink':'umber and slate','accent':'cardinal, teal, gold, indigo, green','materials':['body silhouettes','breath current lines','radial expansions','five-force emission','concentric node rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['pr01'],'individual_breaths':['pr02','pr03','pr04','pr05','pr06'],'synthesis_and_seal':['pr07','pr08']},'reusability_notes':{'pr01':'Use for pañca-prāṇa overview.','pr02':'Use for prāṇa, forward breath, or upper body.','pr03':'Use for apāna, downward breath, or grounding.','pr04':'Use for samāna, balance, or digestion.','pr05':'Use for udāna, speech, or ascent.','pr06':'Use for vyāna, pervasion, or circulation.','pr07':'Use for unity of the five breaths.','pr08':'Use as closing prāṇa seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Pañca-prāṇa

## Aim
Visualize the five vital breaths of Tantrāloka: prāṇa, apāna, samāna, udāna, and vyāna.

## Structure
1. The five prāṇas are one life-force with five functions
2. Prāṇa — forward-moving, upper body, inhalation
3. Apāna — downward-moving, elimination, grounding
4. Samāna — balancing, navel, digestion
5. Udāna — upward-moving, speech, ascent
6. Vyāna — pervasive, whole-body circulation
7. The five are one
8. The seal: five currents, one life

## Visual rules
- Use body silhouette as base for all scenes.
- Each breath has a distinct color and flow direction.
- Prāṇa = cardinal (upward/forward), Apāna = teal (downward), Samāna = gold (central), Udāna = indigo (upward ascent), Vyāna = green (radial).
- Lines and pulses show current direction.

## New motifs
- body with five prāṇa nodes
- central column with breath pulse
- descending/ascending current lines
- navel radial expansion
- thin ascending thread
- radial pervasive emission
- five rays from center in body
- three concentric rings with five nodes
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Pañca-prāṇa Pack

## Differentiation
This pack uses embodied vital-current motifs — body silhouettes with directional breath flows — distinct from the condensation imagery of Nāda-Bindu-Kalā or the void-piercing of Khecarī.

## New symbols
1. body with five prāṇa nodes
2. central column pulse
3. descending/ascending current
4. navel radial expansion
5. thin ascending thread
6. radial pervasive emission
7. five rays from center in body
8. three concentric rings with five nodes each

## Material vocabulary
- warm parchment body-field
- cardinal prāṇa flow
- teal apāna grounding
- gold samāna center
- indigo udāna ascent
- green vyāna pervasion

## Closing seal
Three concentric rings — gold, crimson, teal — each with five nodes representing the five prāṇas in their differentiated and unified state.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Pañca-prāṇa: The Five Vital Breaths Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'prana_panchaka_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'prana_panchaka_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['prana_panchaka_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','prana_panchaka_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'prana_panchaka_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
