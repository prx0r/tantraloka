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
SEED = 26262

# Bhūtaśuddhi palette — elemental purification
PARCHMENT = (244, 240, 232)
PARCHMENT_LIGHT = (250, 247, 240)
INK = (34, 38, 44)
UMBER = (80, 64, 50)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
TEAL = (90, 146, 148)
DEEP_TEAL = (64, 112, 114)
SKY_BLUE = (132, 166, 200)
DEEP_SKY = (86, 122, 162)
EARTH = (158, 126, 84)
DEEP_EARTH = (120, 92, 56)
FIRE = (224, 140, 56)
FLAME = (240, 180, 80)
AIR = (196, 208, 218)
ETHEREAL = (210, 218, 230)
WHITE = (252, 250, 246)
SLATE = (106, 118, 138)
MIST = (176, 186, 200)
SILVER = (216, 222, 232)
GREEN = (106, 152, 114)
DEEP_GREEN = (74, 116, 78)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_BIG = ImageFont.truetype(FONT_DEVA, 42)
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


def elemental_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PARCHMENT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.2 + fine[...,None]*0.9
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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,EARTH,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=CARDINAL)

def dust(im,seed,n=45):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)


def element_cube(d,cx,cy,s,col):
    d.polygon([(cx,cy-s*.6),(cx+s*.7,cy),(cx,cy+s*.6),(cx-s*.7,cy)],outline=rgba(col,200),fill=rgba(col,25),width=2)

def element_wave(d,cx,cy,amp,phase,col):
    pts=[(cx-60,cy+math.sin(x*.15+phase)*amp) for x in range(-60,61,3)]
    d.line(pts,fill=rgba(col,200),width=3)

def element_flame(d,cx,cy,scale,col):
    pts=[(cx,cy-50*scale),(cx-18*scale,cy-5*scale),(cx-6*scale,cy+28*scale),(cx+4*scale,cy+4*scale),(cx+16*scale,cy+34*scale),(cx+30*scale,cy-4*scale)]
    d.polygon(pts,outline=rgba(col,210),fill=rgba(col,35))

def element_spiral(d,cx,cy,r,col,phase):
    pts=[]
    for i in range(80):
        u=i/79; a=u*4*math.pi+phase; rr=r*u
        pts.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr*.6))
    d.line(pts,fill=rgba(col,200),width=2)

def element_dots(d,cx,cy,r,col,phase,n=30):
    for i in range(n):
        a=i*2*math.pi/n+phase; rr=r*(.3+.7*math.sin(i*.5+phase))
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,180))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'भूतशुद्धि',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    elems=[('पृथिवी',EARTH,-120,50),('आपः',TEAL,-60,-50),('तेजस्',FIRE,0,50),('वायु',AIR,60,-50),('आकाश',ETHEREAL,120,50)]
    for lab,col,x,y_off in elems:
        y=cy+y_off; d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,190),fill=rgba(col,25),width=2)
        d.text((x,y-26),lab,font=DEVA_SMALL,fill=col,anchor='mm')
        lineglow(im,[(cx,cy),(x,y)],col,2,70,5)
    d.text((640,505),'bhūtaśuddhi — the purification of the five elements',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),80,EARTH,120,20)
    glow(im,(cx,cy),120,DEEP_EARTH,60,30)
    d.text((cx,cy-60),'पृथिवी',font=DEVA_MED,fill=EARTH,anchor='mm')
    s=lerp(10,90,ease(t))
    element_cube(d,cx,cy,s,EARTH)
    for i in range(10):
        a=i*2*math.pi/10; x=cx+math.cos(a)*s*1.3; y=cy+math.sin(a)*s*1.3
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(DEEP_EARTH,GOLD_LIGHT,i/9),160))
    for i in range(6):
        a=i*2*math.pi/6+t*.05; r=s*.5
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r
        d.ellipse((x-5,y-5,x+5,y+5),outline=rgba(DEEP_EARTH,140),width=1)
    d.text((640,505),'earth dissolves into water — the solid returns to the fluid',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),80,TEAL,120,20)
    glow(im,(cx,cy),120,DEEP_TEAL,50,28)
    d.text((cx,cy-60),'आपः',font=DEVA_MED,fill=TEAL,anchor='mm')
    amp=lerp(5,45,ease(t))
    for i in range(5):
        phase=t*2+i*1.2; y_off=(i-2)*28
        element_wave(d,cx,cy+y_off,amp,phase,TEAL)
    for i in range(8):
        a=i*2*math.pi/8+t*.06; x=cx+math.cos(a)*100; y=cy+math.sin(a)*65
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(TEAL,WHITE,i/7),170))
        d.ellipse((x-1,y-1,x+1,y+1),fill=rgba(WHITE,200))
    d.text((640,505),'water dissolves into fire — the fluid returns to energy',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),80,FIRE,130,22)
    glow(im,(cx,cy),120,FLAME,50,26)
    d.text((cx,cy-60),'तेजस्',font=DEVA_MED,fill=FIRE,anchor='mm')
    for i in range(6):
        scale=lerp(.2,.95,ease(t))*(1-i*.1); x_off=(i-2.5)*44
        element_flame(d,cx+x_off,cy+20,scale,FIRE if i%2==0 else FLAME)
    for i in range(10):
        a=i*2*math.pi/10; r=lerp(10,105,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(FIRE,GOLD_LIGHT,i/9),180))
        d.ellipse((x-1,y-1,x+1,y+1),fill=rgba(WHITE,200))
    d.text((640,505),'fire dissolves into air — energy returns to motion',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,AIR,110,18)
    glow(im,(cx,cy),110,SKY_BLUE,40,24)
    d.text((cx,cy-60),'वायु',font=DEVA_MED,fill=DEEP_SKY,anchor='mm')
    r=lerp(10,120,ease(t))
    for i in range(4):
        phase=t*3+i*1.8
        element_spiral(d,cx,cy,r*(1-i*.12),mix(AIR,SKY_BLUE,i/3),phase)
    for i in range(12):
        a=i*2*math.pi/12+t*.08; x=cx+math.cos(a)*r*.85; y=cy+math.sin(a)*r*.52
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(AIR,WHITE,i/11),170))
        d.ellipse((x-1,y-1,x+1,y+1),fill=rgba(WHITE,200))
    d.text((640,505),'air dissolves into ether — motion returns to space',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),60,ETHEREAL,100,16)
    glow(im,(cx,cy),100,WHITE,35,22)
    d.text((cx,cy-60),'आकाश',font=DEVA_MED,fill=ETHEREAL,anchor='mm')
    r=lerp(10,130,ease(t))
    element_dots(d,cx,cy,r,ETHEREAL,t*1.5,40)
    for i in range(5):
        rr=r*(.15+.85*ease(t))
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(mix(ETHEREAL,WHITE,i/4),100-18*i),width=2)
    for i in range(16):
        a=i*2*math.pi/16+t*.04; x=cx+math.cos(a)*r*.6; y=cy+math.sin(a)*r*.4
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,120))
    d.text((640,505),'ether dissolves into pure consciousness — space reveals awareness',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,130,20)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'शुद्धि',font=DEVA_MED,fill=GOLD,anchor='mm')
    elems=[(EARTH,-130),('पृथिवी'),(TEAL,-65),('आपः'),(FIRE,0),('तेजस्'),(AIR,65),('वायु'),(ETHEREAL,130),('आकाश')]
    # this is getting complex, simplify
    cols=[EARTH,TEAL,FIRE,AIR,ETHEREAL]; names=['पृ','आ','ते','वा','आ']
    for i,(col,lab) in enumerate(zip(cols,names)):
        a=-math.pi/2+i*2*math.pi/5; x=cx+math.cos(a)*140; y=cy+math.sin(a)*88
        seg=partial([(cx,cy),(x,y)],smooth(.03+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,3,85,6)
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,190),fill=rgba(col,25),width=2)
        d.text((x,y+32),lab,font=DEVA_SMALL,fill=col,anchor='mm')
    d.text((640,505),'the five elements purified — each reveals the next, all reveal consciousness',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for r,col in [(220,GOLD),(170,FIRE),(120,TEAL),(70,ETHEREAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'भूत',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(15):
        a=i*2*math.pi/15+t*.04; x=cx+math.cos(a)*190; y=cy+math.sin(a)*132
        col=mix(EARTH,ETHEREAL,i/14)
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,180))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,200))
    d.text((640,505),'the bhūtaśuddhi seal: elements purified into the light of awareness',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('bs01','The Five Elements','Purification of the elemental field.','Bhūtaśuddhi','Overview: the five great elements and their sequential purification.','overview',['elements','purification','bhuta'],'overview','five-element radial diagram',sc01),
Scene('bs02','Pṛthivī — Earth','The solid element dissolves.','Pṛthivī','Earth dissolves into water — density returns to flow.','earth_dissolution',['earth','solid','dissolution'],'element','earth cube dissolving into waves',sc02),
Scene('bs03','Āpas — Water','The fluid element dissolves.','Āpas','Water dissolves into fire — fluid returns to energy.','water_dissolution',['water','fluid','dissolution'],'element','water waves becoming flames',sc03),
Scene('bs04','Tejas — Fire','The fiery element dissolves.','Tejas','Fire dissolves into air — energy returns to motion.','fire_dissolution',['fire','energy','dissolution'],'element','flames becoming air spirals',sc04),
Scene('bs05','Vāyu — Air','The aerial element dissolves.','Vāyu','Air dissolves into ether — motion returns to space.','air_dissolution',['air','motion','dissolution'],'element','spirals becoming ether dots',sc05),
Scene('bs06','Ākāśa — Ether','Space dissolves into consciousness.','Ākāśa','Ether dissolves into pure awareness — the ground of all.','ether_dissolution',['ether','space','consciousness'],'element','ether dots becoming luminous space',sc06),
Scene('bs07','The Fivefold Purification','Each element reveals the next.','Pañca-śuddhi','Sequential purification of earth, water, fire, air, ether.','fivefold_purification',['purification','sequence','revelation'],'synthesis','five-ray purification wheel',sc07),
Scene('bs08','The Bhūtaśuddhi Seal','Elements purified into awareness.','Bhūtaśuddhi-cakra','Closing seal: the great elements as expressions of consciousness.','closing_seal',['seal','elements','consciousness'],'seal','quadruple elemental ring seal',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=elemental_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,40); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
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
    manifest={'project':'Tantrāloka — Bhūtaśuddhi: Elemental Purification','source_basis':'Tantrāloka and Trika bhūtaśuddhi: the sequential purification of earth, water, fire, air, and ether into pure consciousness.','style':{'family':'elemental dissolution cosmography','background':'warm parchment ground','ink':'umber and slate','accent':'earth brown, water teal, fire orange, air sky, ether white','materials':['geometric cubes','wave lines','flame polygons','spiral traces','luminous dots','dissolution rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['bs01'],'individual_elements':['bs02','bs03','bs04','bs05','bs06'],'synthesis_and_seal':['bs07','bs08']},'reusability_notes':{'bs01':'Use for bhūtaśuddhi or elemental overview.','bs02':'Use for earth purification or dissolution.','bs03':'Use for water purification.','bs04':'Use for fire purification.','bs05':'Use for air purification.','bs06':'Use for ether purification.','bs07':'Use for fivefold purification summary.','bs08':'Use as closing elemental seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Bhūtaśuddhi

## Aim
Visualize bhūtaśuddhi: the sequential purification of the five great elements — earth, water, fire, air, ether — each dissolving into the next.

## Structure
1. The five elements are purified sequentially
2. Earth dissolves into water
3. Water dissolves into fire
4. Fire dissolves into air
5. Air dissolves into ether
6. Ether dissolves into consciousness
7. The fivefold purification is one continuum
8. The seal: elements as consciousness

## Visual rules
- Each element has a distinct geometric signature: cube (earth), wave (water), flame (fire), spiral (air), dots (ether).
- Colors transition: earth-brown → water-teal → fire-orange → air-sky → ether-white.
- Each scene shows the current element dissolving toward the next.
- Parchment ground throughout for manuscript feel.

## New motifs
- five-element radial diagram
- earth cube with dissolving halo
- water wave field
- flame polygon array
- air spiral traces
- ether dot field
- five-ray purification wheel
- quadruple elemental ring seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Bhūtaśuddhi Pack

## Differentiation
This pack uses elemental dissolution imagery — each scene is dominated by a specific element transforming into the next. The visual grammar shifts per element.

## New symbols
1. five-element radial diagram
2. earth cube with dissolving halo
3. water wave field
4. flame polygon array
5. air spiral traces
6. ether dot field
7. five-ray purification wheel
8. quadruple elemental ring seal

## Material vocabulary
- warm parchment ground
- earth-umber cube geometry
- water-teal wave lines
- fire-orange flame polygons
- air-sky spiral traces
- ether-white luminous dots

## Closing seal
Quadruple ring seal with elemental colors transitioning from earth-brown to ether-white around a central Sanskrit भूत.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Bhūtaśuddhi: Elemental Purification Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'bhuta_shuddhi_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'bhuta_shuddhi_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['bhuta_shuddhi_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','bhuta_shuddhi_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'bhuta_shuddhi_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
