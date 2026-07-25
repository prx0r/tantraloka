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
SEED = 22222

# Nyāsa palette — ritual placement, touch, installation
PARCHMENT = (243, 238, 228)
PARCHMENT_LIGHT = (249, 246, 238)
INK = (34, 36, 42)
UMBER = (82, 68, 54)
GOLD = (204, 164, 88)
GOLD_LIGHT = (243, 213, 138)
CRIMSON = (154, 48, 62)
CARDINAL = (186, 54, 70)
ROSE = (190, 110, 134)
INDIGO = (66, 78, 136)
DEEP_INDIGO = (44, 54, 98)
TEAL = (92, 146, 148)
DEEP_TEAL = (66, 118, 120)
SLATE = (106, 118, 138)
MIST = (180, 186, 198)
WHITE = (252, 250, 246)
NIGHT = (22, 24, 30)
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


def nyasa_ground(seed):
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
    base -= np.clip((dx*dx+dy*dy)*4,0,12)[...,None]*0.55
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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,ROSE,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,60),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=DEEP_INDIGO)

def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def axial_col(d,cx,y0,y1,col,width=2):
    d.line((cx,y0,cx,y1),fill=rgba(col,160),width=width)
    for y in np.linspace(y0,y1,6):
        d.line((cx-12,y,cx+12,y),fill=rgba(col,100),width=1)

def seed_bindu(d,cx,cy,label,col):
    glow(d.im if hasattr(d,'im') else None,cx,cy,20,col,90,10) if False else None
    d.ellipse((cx-7,cy-7,cx+7,cy+7),fill=rgba(col,210),outline=rgba(WHITE,140))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    # axial column with power-stations
    axial_col(d,cx,140,430,SLATE,3)
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'न्यास',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    pts=[(cx,150),(cx-90,210),(cx+90,210),(cx-80,310),(cx+80,310),(cx,400)]
    cols=[GOLD,CRIMSON,TEAL,CRIMSON,TEAL,GOLD]
    for i,(x,y) in enumerate(pts):
        d.ellipse((x-9,y-9,x+9,y+9),outline=rgba(cols[i],190),fill=rgba(cols[i],30),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,200))
        lineglow(im,[(cx,lerp(140,430,i/len(pts))) if i>0 else (cx,140),(x,y)],mix(cols[i],GOLD_LIGHT,.3),2,65,5)
    d.text((640,505),'nyāsa — installing mantra-power along the axis of awareness',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_col(d,cx,140,430,SLATE,2)
    glow(im,(cx,cy-80),36,GOLD_LIGHT,120,14)
    d.ellipse((cx-12,cy-94,cx+12,cy-66),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-80),'स्पर्श',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        x=cx+math.cos(a)*(80+50*ease(t)); y=cy-80+math.sin(a)*(50+30*ease(t))
        col=mix(CRIMSON,GOLD,i/7)
        d.ellipse((x-6,y-6,x+6,y+6),outline=rgba(col,180),fill=rgba(col,25),width=2)
        lineglow(im,[(cx,cy-80),(x,y)],col,2,70,5)
    d.text((640,505),'the guru\'s touch places power at precise stations along the axis',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_col(d,cx,140,430,SLATE,2)
    positions=[(cx,cy-100),(cx+110,cy-30),(cx+70,cy+80),(cx-70,cy+80),(cx-110,cy-30),(cx,cy-100)]
    for i,(x,y) in enumerate(positions):
        seg=partial([(cx,cy),(x,y)],smooth(.04+i*.06,.8,t))
        col=mix(CARDINAL,GOLD,i/5)
        if len(seg)>1:lineglow(im,seg,col,2,80,5)
        d.ellipse((x-11,y-11,x+11,y+11),outline=rgba(col,190),fill=rgba(col,28),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,180))
    glow(im,(cx,cy),40,GOLD_LIGHT,110,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'अङ्ग',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    d.text((640,505),'the six limbs are consecrated through touch and mantra',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_col(d,cx,140,430,SLATE,2)
    glow(im,(cx,cy),40,GOLD_LIGHT,130,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'ह्रीं',font=DEVA_SMALL,fill=CARDINAL,anchor='mm')
    for i in range(10):
        a=i*2*math.pi/10
        seg=partial([(cx+math.cos(a)*20,cy+math.sin(a)*20),(cx+math.cos(a)*150,cy+math.sin(a)*100)],smooth(.03+i*.04,.84,t))
        col=mix(GOLD_LIGHT,TEAL,i/9)
        if len(seg)>1:lineglow(im,seg,col,3,85,6)
        x=cx+math.cos(a)*160; y=cy+math.sin(a)*108
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,170))
    d.text((640,505),'the seed-mantra in the heart radiates through all stations',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    axial_col(d,cx,140,440,SLATE,3)
    stations=[(cx,150),(cx-70,200),(cx+70,200),(cx-90,280),(cx+90,280),(cx-80,350),(cx+80,350),(cx,420)]
    cols=[GOLD,CRIMSON,TEAL,CARDINAL,INDIGO,CRIMSON,TEAL,GOLD]
    for i,(x,y) in enumerate(stations):
        seg=partial([(cx,lerp(140,440,i/7)),(x,y)],smooth(.03+i*.04,.82,t))
        if len(seg)>1:lineglow(im,seg,cols[i],2,75,5)
        d.ellipse((x-9,y-9,x+9,y+9),outline=rgba(cols[i],190),fill=rgba(cols[i],25),width=2)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(WHITE,200))
        d.text((x,y+24),str(i+1),font=TINY_FONT,fill=cols[i],anchor='mm')
    d.text((640,505),'eight stations along the axis become seats of power',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_col(d,cx,140,430,SLATE,2)
    # five rays representing fingers
    angles=[-1.2,-0.5,0,0.5,1.2]
    cols=[CARDINAL,GOLD,TEAL,INDIGO,GREEN]
    for i,(a,col) in enumerate(zip(angles,cols)):
        r=lerp(30,160,ease(t))
        x=cx+math.sin(a)*r; y=cy-40-math.cos(a)*r
        seg=partial([(cx,cy-40),(x,y)],smooth(.04+i*.06,.8,t))
        if len(seg)>1:lineglow(im,seg,col,3,90,6)
        d.ellipse((x-7,y-7,x+7,y+7),outline=rgba(col,200),fill=rgba(col,30),width=2)
    d.ellipse((cx-14,cy-54,cx+14,cy-26),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'कर',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'kara-nyāsa — mantra power placed at five points of emission',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    axial_col(d,cx,140,430,SLATE,2)
    for r,col in [(220,GOLD),(170,CARDINAL),(120,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,110),width=2)
    for i in range(14):
        a=i*2*math.pi/14; x=cx+math.cos(a)*195; y=cy+math.sin(a)*130
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/13),150))
        lineglow(im,[(cx,cy),(x,y)],mix(GOLD,TEAL,i/13),1,55,4)
    glow(im,(cx,cy),45,GOLD_LIGHT,120,16)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'मण्डल',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    d.text((640,505),'the maṇḍala: power stations arranged around the central axis',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    axial_col(d,cx,140,430,SLATE,2)
    for r,col in [(210,GOLD),(158,CARDINAL),(106,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130),width=2)
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'न्यास',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12+t*.04; x=cx+math.cos(a)*175; y=cy+math.sin(a)*120
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,TEAL,i/11),180))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,220))
    d.text((640,505),'the nyāsa seal: power installed along the axis of awareness',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('ny01','The Art of Nyāsa','Installing mantra-power in the body.','Nyāsa','Overview: nyāsa as ritual placement of divine power.','overview',['nyasa','placement','body'],'overview','body with power points',sc01),
Scene('ny02','The Guru\'s Touch','Power descends through physical contact.','Guru-sparśa','The guru\'s hand transmits power to specific body-stations.','guru_touch',['touch','guru','transmission'],'transmission','hand and descending nodes',sc02),
Scene('ny03','Aṅga-nyāsa','The six limbs of the body are consecrated.','Aṅga-nyāsa','Six body-parts receive mantra and divine presence.','limb_consecration',['limbs','consecration','six'],'placement','six-directional emission',sc03),
Scene('ny04','Hṛdaya-nyāsa','The seed-mantra is placed in the heart.','Hṛdaya-nyāsa','The heart-station receives the bīja.','heart_placement',['heart','seed','placement'],'placement','hand placing seed at heart',sc04),
Scene('ny05','Installation in the Body','Eight stations become seats of divinities.','Aṣṭa-nyāsa','The practitioner becomes the dwelling of the deities.','body_installation',['body','stations','deities'],'installation','body with eight stations',sc05),
Scene('ny06','Kara-nyāsa','Mantra power placed at the fingertips.','Kara-nyāsa','The hand becomes an instrument of power.','finger_placement',['hand','fingers','mantra'],'placement','hand with five finger-nodes',sc06),
Scene('ny07','Body as Maṇḍala','The consecrated body becomes the cosmos.','Deha-maṇḍala','Nyāsa transforms the body into a living maṇḍala.','body_mandala',['body','mandala','consecration'],'synthesis','body within cosmic rings',sc07),
Scene('ny08','The Nyāsa Seal','The body as the temple of awareness.','Nyāsa-cakra','Closing seal: consecrated embodiment.','closing_seal',['seal','nyasa','body'],'seal','body within concentric rings',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=nyasa_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Nyāsa: Ritual Placement and Consecration','source_basis':'Tantrāloka and Trika ritual doctrine: nyāsa as the installation of mantra-power in the body through touch and intention.','style':{'family':'embodied consecration cosmography','background':'warm parchment','ink':'umber and slate','accent':'gold, crimson, teal, indigo','materials':['body silhouettes','consecrating hands','power-point stations','seed mantras','finger nodes','mandala rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['ny01'],'touch_and_transmission':['ny02','ny04','ny06'],'body_installation':['ny03','ny05','ny07'],'seal':['ny08']},'reusability_notes':{'ny01':'Use for nyāsa overview.','ny02':'Use for guru touch or transmission.','ny03':'Use for limb consecration.','ny04':'Use for heart placement.','ny05':'Use for deity installation in body.','ny06':'Use for finger or hand nyāsa.','ny07':'Use for body as mandala.','ny08':'Use as closing consecration seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Nyāsa: Ritual Placement

## Aim
Visualize nyāsa: the ritual placement of mantra-power in the body through touch, intention, and consecration.

## Structure
1. Nyāsa installs divine power in the body
2. The guru's touch transmits power to body-stations
3. The six limbs are consecrated
4. The seed-mantra is placed in the heart
5. Eight stations become seats of deities
6. The hand becomes an instrument (kara-nyāsa)
7. The body becomes a living maṇḍala
8. The seal: body as temple

## Visual rules
- Use body silhouettes, hand motifs, and power-point nodes.
- Warm parchment ground with gold and crimson accents.
- Show placement and installation rather than abstract flow.
- The body is shown as sacred architecture.

## New motifs
- body with power-point stations
- guru hand with descending nodes
- six-limb emission diagram
- hand placing seed at heart
- eight-station body diagram
- five-finger hand with mantra nodes
- body within mandala rings
- consecration seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Nyāsa Pack

## Differentiation
This pack uses embodied consecration imagery — body silhouettes, hands, and touch-points — distinct from the threshold and flame motifs of Dīkṣā.

## New symbols
1. body power-point diagram
2. guru hand with descending nodes
3. six-limb angular emission
4. hand placing seed at heart
5. eight-station body
6. five-finger mantra nodes
7. body in mandala rings
8. consecration seal

## Material vocabulary
- warm parchment ground
- gold consecration-light
- crimson power-points
- teal receiving stations
- umber body silhouette

## Closing seal
Body silhouette enclosed in concentric rings with twelve golden power-stations.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Nyāsa: Ritual Placement Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'nyasa_placement_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'nyasa_placement_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['nyasa_placement_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','nyasa_placement_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'nyasa_placement_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
