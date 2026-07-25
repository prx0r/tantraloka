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
SEED = 44444

# Khecarī palette — void, ascent, piercing
VOID = (10, 12, 18)
DEEP_VIOLET = (44, 36, 66)
VIOLET = (102, 84, 144)
LAVENDER = (166, 148, 196)
PALE_VIOLET = (196, 182, 216)
SILVER = (216, 222, 232)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
PALE_GOLD = (252, 236, 196)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
TEAL = (86, 144, 148)
DEEP_TEAL = (62, 110, 114)
MIST = (176, 186, 204)
SLATE = (104, 114, 132)
DEEP_SLATE = (72, 80, 96)
UMBER = (78, 64, 50)

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


def void_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(VOID,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.5 + fine[...,None]*1.2
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*22,0,30)[...,None]
    aura=np.exp(-(((xx-W/2)/(W*.18))**2+((yy-H*.30)/(H*.22))**2)*2.2)
    base[...,0]+=aura*8; base[...,1]+=aura*10; base[...,2]+=aura*24
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
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(8,10,16,210),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=60):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(.8,2.0))
        c=mix(VIOLET,SILVER,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,58))))
    im.alpha_composite(ov)

def tongue_pierce(d,cx,cy,scale=1.0,col=SILVER):
    pts=[(cx-8*scale,cy),(cx-4*scale,cy-60*scale-20*scale),(cx,cy-90*scale-30*scale),(cx+4*scale,cy-60*scale-20*scale),(cx+8*scale,cy)]
    d.polygon(pts,outline=rgba(col,210),fill=rgba(col,35))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,VIOLET,130,20)
    for r,col in [(210,SILVER),(160,VIOLET),(108,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    for i in range(14):
        a=i*2*math.pi/14; x=cx+math.cos(a)*195; y=cy+math.sin(a)*132
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(VIOLET,SILVER,i/13),160))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,190))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'खेचरी',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,cy+40),'मुद्रा',font=DEVA_MED,fill=SILVER,anchor='mm')
    d.text((640,505),'khecarīmudrā — the seal that moves through the void of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,320
    glow(im,(cx,180),30,GOLD_LIGHT,100,12)
    d.ellipse((cx-14,166,cx+14,194),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,140),'ऊर्ध्व',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(12):
        a=-math.pi/2+i*math.pi/11; r=lerp(20,150,ease(t))
        x=cx+math.cos(a)*r*.7; y=180+math.sin(a)*r*.9
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SILVER,VIOLET,i/11),170))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,180))
    tongue_pierce(d,cx,cy,.7,SILVER)
    d.text((640,505),'the tongue pierces upward toward the space beyond the palate',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy-100),36,VIOLET,100,14)
    d.ellipse((cx-12,cy-112,cx+12,cy-88),fill=rgba(WHITE,255),outline=rgba(VIOLET,220),width=2)
    d.text((cx,cy-130),'कोश',font=DEVA_SMALL,fill=LAVENDER,anchor='mm')
    for i in range(8):
        y=lerp(cy-80,cy+130,i/7); r=lerp(16,115,i/7)*ease(t)
        d.ellipse((cx-r,y-9,cx+r,y+9),outline=rgba(mix(VIOLET,PALE_VIOLET,i/7),140-12*i),width=2)
    tongue_pierce(d,cx,cy+40,.6,SILVER)
    for i in range(6):
        a=i*2*math.pi/6; x=cx+math.cos(a)*70; y=cy+50+math.sin(a)*40
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(GOLD_LIGHT,120))
    d.text((640,505),'the seal pierces through successive layers of bodily containment',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(10):
        r=20+i*24; alpha=int(140*(1-i/10)*(.5+.5*math.sin(t*1.5)))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(DEEP_VIOLET,PALE_VIOLET,i/10),alpha),width=2)
    glow(im,(cx,cy),60,VIOLET,120,20)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(VIOLET,220),width=2)
    d.text((cx,cy),'शून्य',font=DEVA_MED,fill=LAVENDER,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.05; x=cx+math.cos(a)*170; y=cy+math.sin(a)*118
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(VIOLET,WHITE,i/13),140))
    d.text((640,505),'consciousness enters the void beyond all bodily support',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,120),30,GOLD_LIGHT,110,12)
    d.ellipse((cx-12,106,cx+12,134),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,95),'ब्रह्मरन्ध्र',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    pts=[]
    for i in range(70):
        u=i/69; x=cx+math.sin(u*math.pi*6)*35*ease(t); y=lerp(150,440,u)
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,SILVER,3,95,7)
    for i in range(5):
        y=lerp(170,410,i/4); d.ellipse((cx-2,y-2,cx+2,y+2),fill=rgba(WHITE,180))
    d.text((640,505),'the energy rolls upward through the brahmarandhra into the sky of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for r,col in [(220,GOLD),(170,VIOLET),(120,SILVER)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    glow(im,(cx,cy),55,GOLD_LIGHT,130,16)
    d.text((cx,cy-40),'सर्व',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,cy+40),'मुद्रा',font=DEVA_MED,fill=SILVER,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16; x=cx+math.cos(a)*188; y=cy+math.sin(a)*132
        seg=partial([(cx,cy),(x,y)],ease(t))
        if len(seg)>1:lineglow(im,seg,mix(VIOLET,SILVER,i/15),2,65,5)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(VIOLET,SILVER,i/15),160))
    tongue_pierce(d,cx,cy-20,.5,SILVER)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'khecarī is the supreme mudrā — it contains all others within its movement',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(8):
        r=30+i*32; alpha=int(130*(1-i/8)*ease(t))
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(DEEP_VIOLET,LAVENDER,i/8),alpha),width=2)
    glow(im,(cx,cy),80,VIOLET,140,24)
    d.text((cx,cy),'चिदाकाश',font=DEVA_MED,fill=LAVENDER,anchor='mm')
    tongue_pierce(d,cx,cy-50,.35,WHITE)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255))
    for i in range(24):
        a=i*2*math.pi/24; r=130+50*math.sin(t*2+i)*ease(t)
        d.ellipse((cx+math.cos(a)*r-3,cy+math.sin(a)*r-3,cx+math.cos(a)*r+3,cy+math.sin(a)*r+3),fill=rgba(mix(VIOLET,WHITE,i/23),130))
    d.text((640,505),'the space-faring seal dissolves into the pure space of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),80,GOLD_LIGHT,140,24)
    for r,col in [(220,SILVER),(170,VIOLET),(120,GOLD),(70,WHITE)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120-15*(r//50)),width=2)
    tongue_pierce(d,cx+50,cy-60,.5,GOLD_LIGHT)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'खेचरी',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(18):
        a=i*2*math.pi/18; x=cx+math.cos(a)*193; y=cy+math.sin(a)*134
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(SILVER,PALE_VIOLET,i/17),170))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,200))
    d.text((640,505),'the khecarī seal: moving through the void, one becomes the void',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('kh01','The Space-Faring Seal','Moving through the void of consciousness.','Khecarīmudrā','Overview: khecarīmudrā as the supreme gesture of traversing consciousness.','overview',['khecari','void','mudra'],'overview','void field with concentric rings',sc01),
Scene('kh02','Piercing Upward','The tongue ascends toward the brahmarandhra.','Ūrdhva-gati','The piercing upward movement begins the traversal.','upward_pierce',['piercing','upward','tongue'],'ascent','tongue piercing into upper void',sc02),
Scene('kh03','Piercing the Sheaths','Successive layers of containment are crossed.','Kośa-bheda','The seal pierces through the five bodily sheaths.','sheath_piercing',['sheaths','layers','piercing'],'ascent','horizontal rings with central pierce',sc03),
Scene('kh04','Entering the Void','The space beyond all support.','Śūnya-praveśa','Consciousness enters the void that supports no form.','void_entry',['void','entry','boundless'],'void','dissolving concentric rings',sc04),
Scene('kh05','Rolling Upward','The energy rolls through the brahmarandhra.','Ūrdhva-kuṇḍalī','The coiled energy ascends through the cranial aperture.','upward_roll',['roll','energy','ascent'],'ascent','sinuous upward line',sc05),
Scene('kh06','The Supreme Mudrā','All seals are contained in this one movement.','Sarva-mudrā','Khecarī is the mudrā that contains every other mudrā.','supreme_seal',['supreme','mudra','containment'],'synthesis','radial convergence with pierce',sc06),
Scene('kh07','Space of Consciousness','The seal dissolves into pure space.','Cid-ākāśa','The practitioner becomes the space through which the seal moves.','consciousness_space',['space','consciousness','dissolution'],'dissolution','expanding luminous void',sc07),
Scene('kh08','The Khecarī Seal','The void-farer becomes the void.','Khecarī-cakra','Closing seal: the supreme gesture resolved into pure space.','closing_seal',['seal','khecari','void'],'seal','concentric void ring seal',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=void_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,50); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=94)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(p).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),VOID)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Khecarīmudrā: The Space-Faring Seal','source_basis':'Tantrāloka and Trika yoga: khecarīmudrā as the seal that moves through the void, pierces the sheaths, and dissolves into pure consciousness.','style':{'family':'void-piercing cosmography','background':'deep void field with violet aura','ink':'silver and mist','accent':'violet, gold, white, silver','materials':['void rings','piercing tongues','sheath layers','sinuous ascent lines','luminous void fields']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['kh01'],'ascent':['kh02','kh03','kh05'],'void_and_synthesis':['kh04','kh06','kh07'],'seal':['kh08']},'reusability_notes':{'kh01':'Use for khecarī overview or supreme mudrā.','kh02':'Use for piercing or upward ascent.','kh03':'Use for piercing the sheaths.','kh04':'Use for entering the void.','kh05':'Use for upward rolling energy.','kh06':'Use for all mudrās contained in one.','kh07':'Use for consciousness as space.','kh08':'Use as closing void seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Khecarīmudrā

## Aim
Visualize khecarīmudrā: the seal that moves through the void, pierces the upper palate, and dissolves into the space of consciousness.

## Structure
1. Khecarīmudrā is the supreme seal
2. The tongue pierces upward through the palate
3. It pierces the five bodily sheaths
4. It enters the void beyond all support
5. Energy rolls through the brahmarandhra
6. This mudrā contains all other mudrās
7. The practitioner becomes the space itself
8. The seal: the void-farer becomes the void

## Visual rules
- Void backgrounds with violet and silver.
- The piercing tongue motif as a central vertical element.
- Concentric rings represent sheaths being crossed.
- The closing is pure luminous expansion.

## New motifs
- void field with concentric rings
- tongue-pierce upward
- horizontal sheath rings
- dissolving void circles
- sinuous upward roll
- radial convergence with central pierce
- expanding luminous void
- concentric void ring seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Khecarīmudrā Pack

## Differentiation
This pack uses void, piercing, and spatial expansion motifs distinct from the body-placement imagery of Nyāsa or the hand-gestures of Mudrā. The void field is the primary visual ground.

## New symbols
1. void field with concentric rings
2. tongue-piercing upward
3. horizontal sheath-piercing rings
4. dissolving void circles
5. sinuous upward energy roll
6. radial convergence with central pierce
7. expanding luminous void
8. concentric void ring seal

## Material vocabulary
- deep void background
- violet aura light
- silver piercing
- gold supreme-light
- white dissolution

## Closing seal
Four concentric rings — silver, violet, gold, white — with a tongue-pierce ascending at the side and sixteen silver nodes around the circumference.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Khecarīmudrā Pack

- {W}x{H}, {FPS}fps, {len(SCENES)} scenes, {DURATION}s each, {len(SCENES)*DURATION:.1f}s total

Run: `python render_pack.py` (resume-safe)
'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'khecari_mudra_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'khecari_mudra_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['khecari_mudra_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','khecari_mudra_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'khecari_mudra_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
