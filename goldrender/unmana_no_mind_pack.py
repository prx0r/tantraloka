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
SEED = 45454

VOID = (8, 8, 12)
DEEP_GREY = (16, 18, 24)
SLATE = (88, 96, 112)
MIST = (156, 166, 182)
PALE_MIST = (206, 212, 222)
SILVER = (210, 216, 228)
WHITE = (248, 246, 242)
GOLD = (196, 160, 86)
GOLD_LIGHT = (236, 208, 134)
PALE_GOLD = (248, 238, 216)
TEAL = (80, 138, 142)
LAVENDER = (158, 144, 186)
VIOLET = (96, 80, 140)
UMBER = (70, 58, 46)
PALE_VIOLET = (194, 184, 210)
CRIMSON = (146, 44, 58)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
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
    coarse=rng.normal(0,1,(36,64)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(24))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.5 + fine[...,None]*0.9
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*22,0,30)[...,None]
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

def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,70),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,60),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(SLATE,60),width=1)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(6,6,10,190),outline=rgba(SLATE,45),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=PALE_MIST)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=SLATE)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=35):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(.6,1.6))
        c=mix(SLATE,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,50))))
    im.alpha_composite(ov)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,PALE_MIST,100,26)
    for r,col in [(190,SLATE),(130,PALE_MIST),(70,WHITE)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,80-15*(r//50)),width=1)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,180))
    d.text((cx,cy-40),'उन्मना',font=DEVA_MED,fill=PALE_MIST,anchor='mm')
    d.text((640,505),'unmanā — the state beyond mind, where even the witness dissolves',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(5):
        r=lerp(10,180,ease(1-t))
        alpha=int(100*(1-i/5)*(1-t*.7))
        if alpha<5: continue
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(SLATE,WHITE,i/4),alpha),width=1)
    d.text((cx,cy),'मनस्',font=DEVA_MED,fill=rgba(PALE_MIST,int(180*(1-ease(t)))),anchor='mm')
    d.text((640,505),'mind unweaves itself — thought dissolves into its own ground',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(6):
        y=lerp(120,440,i/5); w=lerp(400,40,ease(t))*(1-i*.1)
        alpha=int(90*(1-i/5)*ease(t))
        if w<2 or alpha<5: continue
        d.arc((cx-w,y-10,cx+w,y+10),200,340,fill=rgba(mix(SLATE,PALE_MIST,i/5),alpha),width=1)
    d.text((cx,cy),'वासना',font=DEVA_SMALL,fill=rgba(PALE_MIST,int(120*ease(t))),anchor='mm')
    d.text((640,505),'the traces of past experience dissolve — no seed remains',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    p=1-ease(t)
    for r in range(4):
        rr=30+r*40*p; alpha=int(80*(1-r/4)*p)
        if alpha<5: continue
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(SILVER,alpha),width=1)
    d.text((cx,cy),'अहंकार',font=DEVA_SMALL,fill=rgba(PALE_MIST,int(150*p)),anchor='mm')
    d.text((640,505),'the I-sense dissolves — no one remains to witness',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,300
    # fading breath line
    pts=[]
    for i in range(60):
        u=i/59; x=lerp(200,1080,u); y=cy+math.sin(u*math.pi*4)*lerp(60,5,ease(t))
        pts.append((x,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1:lineglow(im,reveal,SLATE,2,80,6)
    d.text((640,505),'the breath thins — the boundary between inner and outer dissolves',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for i in range(8):
        a=i*2*math.pi/8; rr=lerp(140,10,ease(t))
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.6
        alpha=int(120*(1-i/8)*(1-ease(t)))
        if alpha<5: continue
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(PALE_MIST,alpha))
    d.text((cx,cy),'शून्य',font=DEVA_MED,fill=rgba(PALE_MIST,int(150*(1-ease(t)))),anchor='mm')
    d.text((640,505),'all form evaporates — only the void remains, and the void is peace',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # the threshold
    for i in range(3):
        r=lerp(160,20,1-ease(t))
        alpha=int(100*(1-i/3)*(1-ease(t)))
        if alpha<5: continue
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(GOLD,WHITE,i/2),alpha),width=2)
    d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=rgba(WHITE,int(200*(1-ease(t)))))
    d.text((cx,cy-50),'उन्मना',font=DEVA_MED,fill=rgba(PALE_GOLD,int(200*(1-ease(t)))),anchor='mm')
    d.text((640,505),'the threshold of unmanā — even the void is crossed',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    for r,col in [(200,SLATE),(150,PALE_MIST),(100,WHITE)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,70-10*(r//50)),width=1)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=rgba(WHITE,int(180*ease(t))),outline=rgba(PALE_GOLD,int(100*ease(t))),width=1)
    d.text((cx,cy),'उन्मना',font=DEVA_MED,fill=rgba(PALE_MIST,int(200*ease(t))),anchor='mm')
    d.text((640,505),'the seal of unmanā: no mind, no form, no witness — only this',font=SUB_FONT,fill=SLATE,anchor='mm')


SCENES=[
Scene('um01','Beyond Mind','The state of no-mind.','Unmanā','Overview: unmanā as the state beyond all mental activity.','overview',['unmana','no-mind','beyond'],'overview','faint concentric void rings',sc01),
Scene('um02','Mind Unweaving','Thought dissolves into its source.','Manas-laya','The mind unravels back into the ground of awareness.','mind_dissolution',['mind','dissolution','unweaving'],'dissolution','dissolving concentric thought-rings',sc02),
Scene('um03','Traces Dissolved','No seed of past experience remains.','Vāsanā-kṣaya','The subliminal traces that generate experience dissolve.','trace_dissolution',['traces','vasana','dissolution'],'dissolution','fading horizontal arcs',sc03),
Scene('um04','The I-Sense Dissolves','No witness remains.','Ahaṃkāra-laya','The egoic center dissolves into the void.','ego_dissolution',['ego','I-sense','dissolution'],'dissolution','contracting ego-rings',sc04),
Scene('um05','Breath Thins','The boundary between inner and outer dissolves.','Prāṇa-laya','Breath fades, the inner-outer distinction collapses.','breath_thinning',['breath','thinning','boundary'],'dissolution','flattening sine wave',sc05),
Scene('um06','Form Evaporates','All appearance returns to the void.','Rūpa-laya','Every form dissolves into empty space.','form_evaporation',['form','evaporation','void'],'dissolution','radial dissolving nodes',sc06),
Scene('um07','The Threshold','The void itself is crossed.','Unmanā-dvāra','Crossing the threshold where even the void is left behind.','threshold',['threshold','crossing','void'],'threshold','vanishing threshold rings',sc07),
Scene('um08','The Unmanā Seal','No mind — no witness — only this.','Unmanā-cakra','Closing seal: the state beyond all states.','closing_seal',['seal','unmana','beyond'],'seal','minimal dissolving ring seal',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=void_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,30); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),VOID)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Unmanā: The Mindless State','source_basis':'Tantrāloka: unmanā as the state beyond mind, beyond the dvādaśānta, where all mental activity, traces, and self-sense dissolve.','style':{'family':'dissolution-void cosmography','background':'deep near-black void','ink':'faint slate and silver','accent':'pale mist, silver, gold-light','materials':['faint concentric rings','dissolving arcs','thinning waveforms','vanishing thresholds','minimal seal']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['um01'],'dissolution_sequence':['um02','um03','um04','um05','um06'],'threshold_and_seal':['um07','um08']},'reusability_notes':{'um01':'Use for unmanā overview or beyond-mind states.','um02':'Use for mind dissolution or thought dissolving.','um03':'Use for vāsanā dissolution or trace dissolution.','um04':'Use for ego dissolution or I-sense collapse.','um05':'Use for breath thinning or inner-outer boundary.','um06':'Use for form dissolving into void.','um07':'Use for threshold crossing or beyond all states.','um08':'Use as closing dissolution seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Unmanā

## Aim
Visualize unmanā: the mindless state beyond all mental activity, where thought, trace, I-sense, and form dissolve into the void.

## Structure
1. Unmanā is beyond mind
2. Mind unweaves itself
3. Subliminal traces dissolve
4. The I-sense dissolves
5. Breath thins to nothing
6. All form evaporates
7. The void itself is crossed
8. The seal: no mind, no witness

## Visual rules
- Minimalist, dissolving, fading visuals.
- Elements appear and then dissolve — never fully present.
- Use negative space as primary compositional element.
- SLATE/PALE_MIST/WHITE gradation from form to void.
- Devanagari text fades in and out.
- The pack gets sparser as it progresses.

## New motifs
- faint concentric void rings
- dissolving thought-rings
- fading horizontal arcs
- contracting ego-rings
- flattening sine wave
- radial dissolving nodes
- vanishing threshold rings
- minimal dissolving ring seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Unmanā Pack

## Differentiation
This pack uses dissolution and negative space — elements appear only to fade. No bright golds, no dense node networks. The visual language gets sparser with each scene.

## New symbols
1. faint concentric void rings
2. dissolving thought-rings
3. fading horizontal arcs
4. contracting ego-rings
5. flattening sine wave
6. radial dissolving nodes
7. vanishing threshold rings
8. minimal dissolving ring seal'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Unmanā: The Mindless State Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'unmana_no_mind_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'unmana_no_mind_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['unmana_no_mind_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','unmana_no_mind_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'unmana_no_mind_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
