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
SEED = 12345

# Initiation palette — threshold, transmission, consecration
NIGHT = (16, 14, 18)
OBSIDIAN = (24, 22, 28)
SLATE = (96, 100, 112)
MIST = (172, 178, 190)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
SAFFRON = (220, 146, 52)
CRIMSON = (154, 44, 58)
CARDINAL = (186, 52, 68)
ROSE = (192, 104, 128)
TEAL = (92, 144, 146)
INDIGO = (66, 76, 132)
DEEP_INDIGO = (44, 54, 98)
IVORY = (247, 244, 236)
WHITE = (252, 250, 246)
UMBER = (80, 64, 50)
GREEN = (104, 150, 110)

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


def threshold_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.2 + fine[...,None]*1.15
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    glow=np.exp(-(((xx-W/2)/(W*.26))**2+((yy-H*.38)/(H*.28))**2)*2.4)
    base[...,0]+=glow*12; base[...,1]+=glow*14; base[...,2]+=glow*16
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
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(14,12,16,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=IVORY)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,65))))
    im.alpha_composite(ov)

def arch(d,x0,y0,x1,y1,col,width=3):
    d.arc((x0,y0,x1,y1),0,180,fill=rgba(col,210),width=width)

def flame(d,cx,cy,scale=1.0,col=SAFFRON):
    pts=[(cx,cy-60*scale),(cx-22*scale,cy-8*scale),(cx-6*scale,cy+32*scale),(cx+4*scale,cy+6*scale),(cx+18*scale,cy+42*scale),(cx+36*scale,cy-4*scale)]
    d.polygon(pts,outline=rgba(col,220),fill=rgba(mix(col,GOLD_LIGHT,.35),55))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),70,GOLD_LIGHT,130,20)
    glow(im,(cx,cy),120,CARDINAL,60,30)
    arch(d,cx-220,cy-130,cx+220,cy+130,GOLD,4)
    d.rounded_rectangle((cx-100,cy-50,cx+100,cy+50),radius=22,outline=rgba(CARDINAL,180),fill=rgba(CARDINAL,20),width=2)
    d.text((cx,cy),'दीक्षा',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx-80,cy-80),'गुरु',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    d.text((cx+80,cy+80),'शिष्य',font=DEVA_SMALL,fill=TEAL,anchor='mm')
    for i in range(10):
        a=i*2*math.pi/10; x=cx+math.cos(a)*185; y=cy+math.sin(a)*124
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(GOLD,TEAL,i/9),180))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,200))
    d.text((640,505),'initiation is the transmission of consciousness from guru to disciple',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy-60),40,GOLD_LIGHT,120,14)
    d.ellipse((cx-16,cy-76,cx+16,cy-44),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    # descent of grace
    pts=[]
    for i in range(80):
        u=i/79; a=-math.pi/2+u*math.pi; x=cx+math.cos(a)*180; y=lerp(cy-40,cy+130,u)
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,GOLD_LIGHT,3,100,7)
    d.rounded_rectangle((cx-80,cy+80,cx+80,cy+140),radius=18,outline=rgba(CARDINAL,170),fill=rgba(CARDINAL,20),width=2)
    d.text((cx,126),'guru',font=TERM_FONT,fill=GOLD,anchor='mm')
    d.text((cx-90,174),'śiṣya',font=SMALL_FONT,fill=CARDINAL,anchor='mm')
    d.text((640,505),'grace descends through the channel of the guru\'s transmission',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(7):
        r=36+i*32
        alpha=int(155*(1-i/7)*ease(t))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(SLATE,CRIMSON,i/7),alpha),width=2)
        if i%2==0:
            for j in range(6):
                a=j*2*math.pi/6+i*.25; x=cx+math.cos(a)*r*.85; y=cy+math.sin(a)*r*.6
                d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(SLATE,GOLD_LIGHT,i/7),100))
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    glow(im,(cx,cy),80,CRIMSON,50,24)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'मल',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12+t*.06; x=cx+math.cos(a)*180; y=cy+math.sin(a)*118
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(SLATE,GOLD_LIGHT,i/11),150))
    d.text((640,505),'the disciple is purified through the removal of the three malas',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    # four stages of initiation
    stages=[('anavopāya',SLATE),('śāktopāya',INDIGO),('śāmbhavopāya',GOLD),('anupāya',WHITE)]
    for i,(lab,col) in enumerate(stages):
        y=120+i*80
        d.rounded_rectangle((cx-140,y-18,cx+140,y+18),radius=12,outline=rgba(col,170),fill=rgba(col,20),width=2)
        d.text((cx,y),lab,font=SMALL_FONT,fill=col,anchor='mm')
        if i<3:
            seg=partial([(cx,y+18),(cx,stages[i+1][1] if False else y-18)],smooth(.05+i*.08,.8,t))
            if len(seg)>1:lineglow(im,seg,mix(col,stages[i+1][1],.5),2,70,5)
    glow(im,(cx,cy-120),30,GOLD_LIGHT,100,12)
    d.text((640,505),'initiation unfolds through four progressive modes of transmission',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    draw=ImageDraw.Draw(im)
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    draw.arc((cx-72,cy-34,cx+72,cy+34),180,360,fill=rgba(GOLD,190),width=3)
    draw.arc((cx-72,cy-34,cx+72,cy+34),0,180,fill=rgba(GOLD,190),width=3)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255))
    d.text((cx,cy-60),'हृदय',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(10):
        a=i*2*math.pi/10; x=cx+math.cos(a)*120; y=cy+math.sin(a)*80
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,TEAL,i/9),130))
    seeds=[('बीज',-100),('मन्त्र',0),('विद्या',100)]
    for i,(lab,off) in enumerate(seeds):
        x=cx+off; y=cy+70
        d.ellipse((x-11,y-11,x+11,y+11),outline=rgba(mix(GOLD,TEAL,i/2),190),fill=rgba(mix(GOLD,TEAL,i/2),25),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/2),210))
        d.text((x,y+30),lab,font=DEVA_SMALL,fill=mix(GOLD,TEAL,i/2),anchor='mm')
    d.text((640,505),'the guru plants the seeds of liberation in the disciple\'s heart',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    # threshold crossing
    for r,col,w in [(220,SLATE,2),(180,GOLD,3),(130,CRIMSON,2)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,140),width=w)
    d.ellipse((cx-70,cy-150,cx+70,cy-40),outline=rgba(GOLD,180),width=3)
    d.arc((cx-70,cy-150,cx+70,cy-40),180,360,fill=rgba(GOLD_LIGHT,200),width=3)
    flame(d,cx,cy-75,.6,SAFFRON)
    glow(im,(cx,cy),40,GOLD_LIGHT,110,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'the disciple crosses the threshold from bondage to liberation',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # transmission as mirroring
    draw=ImageDraw.Draw(im)
    draw.arc((cx-72,cy-34,cx+72,cy+34),180,360,fill=rgba(GOLD,180),width=2)
    draw.arc((cx-72,cy-34,cx+72,cy+34),0,180,fill=rgba(GOLD,180),width=2)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255))
    for side,col,lab in [(-1,GOLD,'guru'),(1,TEAL,'disciple')]:
        x=cx+side*130; y=cy
        d.ellipse((x-28,y-28,x+28,y+28),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.text((x,y+52),lab,font=SMALL_FONT,fill=col,anchor='mm')
        seg=partial(bezier((x-side*28,y),(cx-10,y-40),(cx+10,y+40),(cx,y),70),smooth(.05,.85,t))
        if len(seg)>1:lineglow(im,seg,mix(col,GOLD_LIGHT,.5),3,100,6)
    d.text((640,505),'true initiation is the recognition of identity between guru and disciple',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # closing seal
    for r,col in [(220,SLATE),(175,CARDINAL),(128,GOLD)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130),width=2)
    arch(d,cx-230,cy-170,cx+230,cy+170,GOLD_LIGHT,4)
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*130
        flame(d,x,y,.2,SAFFRON)
    d.text((640,505),'the seal of initiation: transmission without interval',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('dk01','The Gate of Initiation','Transmission of consciousness from guru to disciple.','Dīkṣā','Overview: initiation as the threshold of liberation.','overview',['initiation','transmission','threshold'],'overview','arch gate with flames',sc01),
Scene('dk02','Descent of Grace','Śaktipāta descends through the guru.','Śaktipāta','Grace flows through the living channel of transmission.','grace_descent',['grace','descent','guru'],'transmission','descent arc to receiver',sc02),
Scene('dk03','Purification','The three malas are removed before entry.','Mala-śuddhi','The disciple is prepared through purification.','purification',['purification','malas','preparation'],'preparation','concentric purification rings',sc03),
Scene('dk04','Four Stages of Initiation','Transmission unfolds through four upāyas.','Upāya-catuṣṭaya','From embodied practice to direct recognition.','four_stages',['upaya','stages','transmission'],'stages','four-tier ladder',sc04),
Scene('dk05','Seeds Planted in the Heart','Bīja, mantra, and vidyā are placed.','Bīja-nyāsa','The guru implants the seeds of realization.','seed_placement',['seeds','heart','placement'],'transmission','eye with three seed-nodes',sc05),
Scene('dk06','Crossing the Threshold','Transition from bondage to liberation.','Saṃkrānti','The disciple crosses the boundary of contracted awareness.','threshold_cross',['threshold','crossing','liberation'],'transition','gate and flame aperture',sc06),
Scene('dk07','Mirror of Recognition','The guru-disciple identity is revealed.','Pratyabhijñā','In true initiation, no separation remains between transmitter and received.','recognition_mirror',['recognition','identity','mirror'],'recognition','dual eye mirroring',sc07),
Scene('dk08','The Dīkṣā Seal','Transmission without interval.','Dīkṣā-cakra','The closing seal: initiation as timeless recognition.','closing_seal',['seal','initiation','transmission'],'seal','arched gate with flames',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=threshold_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,45); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
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
    manifest={'project':'Tantrāloka — Dīkṣā: Initiation and Transmission','source_basis':'Tantrāloka doctrine of dīkṣā: initiation as transmission of consciousness, purification, upāya-stages, and guru-disciple identity.','style':{'family':'threshold cosmography','background':'deep night with crimson-gold gate','ink':'slate and mist','accent':'cardinal, gold, saffron, teal, white','materials':['ornamental arches','descent arcs','purification rings','flame lamps','mirroring eyes']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['dk01'],'transmission':['dk02','dk05','dk07'],'preparation_and_stages':['dk03','dk04'],'transition_and_seal':['dk06','dk08']},'reusability_notes':{'dk01':'Use for initiation overview or gate imagery.','dk02':'Use for grace descent or guru transmission.','dk03':'Use for purification or mala removal.','dk04':'Use for upāya stages of initiation.','dk05':'Use for seed placement or heart implantation.','dk06':'Use for threshold crossing or liberation entry.','dk07':'Use for guru-disciple identity mirror.','dk08':'Use as closing initiation seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Dīkṣā: Initiation

## Aim
Visualize the Tantrāloka doctrine of initiation: transmission of consciousness, purification, and recognition of identity.

## Structure
1. Initiation is the threshold of liberation
2. Grace descends through the guru's transmission
3. The disciple is purified of the three malas
4. Initiation unfolds through four upāya stages
5. Seeds are planted in the heart of the disciple
6. The disciple crosses the threshold
7. Guru and disciple are recognized as identical
8. The seal: transmission without interval

## Visual rules
- Use arch, gate, and threshold motifs.
- Gold for transmission; cardinal for transformative fire.
- Flames represent the transformative power of initiation.
- The closing depicts identity, not hierarchy.

## New motifs
- ornamental arch gate
- grace descent arc
- purification rings
- four-stage initiation ladder
- three seed nodes in eye
- threshold crossing with flame
- guru-disciple mirroring
- arched seal with flame crown
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Dīkṣā Pack

## Differentiation
This pack uses threshold and transmission imagery distinct from the heart-lotus or freedom-field packs. Arches, descents, and flames replace concentric rings.

## New symbols
1. ornamental arch gate
2. grace descent arc
3. purification rings
4. four-stage ladder
5. seed-placement eye
6. flame threshold
7. dual-eye mirror
8. arched flame seal

## Material vocabulary
- deep night ground
- cardinal flame-lacquer
- gold transmission-light
- saffron transformative fire
- teal receiving field

## Closing seal
Ornamental arch with encircling flame-crowns and central gold bindu.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Dīkṣā: Initiation Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'diksa_initiation_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'diksa_initiation_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['diksa_initiation_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','diksa_initiation_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'diksa_initiation_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
