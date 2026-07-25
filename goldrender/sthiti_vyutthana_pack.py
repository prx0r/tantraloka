#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent; FRAMES_ROOT = ROOT / 'frames'; SCENES_ROOT = ROOT / 'scenes'
W, H = 1280, 720; FPS = 10; DURATION = 4.8; NFRAMES = int(FPS * DURATION); SEED = 20202

PARCHMENT = (244, 240, 232); PARCHMENT_LIGHT = (250, 247, 240); INK = (34, 38, 44)
UMBER = (78, 64, 50); GOLD = (206, 166, 88); GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60); CARDINAL = (186, 54, 70); TEAL = (90, 146, 148)
SLATE = (106, 118, 138); MIST = (176, 186, 200); WHITE = (252, 250, 246)
SILVER = (216, 222, 232); INDIGO = (66, 78, 136); GREEN = (106, 152, 114)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31); SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22); SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11); DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))

def sthiti_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PARCHMENT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.0 + fine[...,None]*0.85
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
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
    a=clamp(a); f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points): A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out
def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(UMBER,110),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,80),width=1)
def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK); d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=CARDINAL)
def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18); glow(im,(cx,cy),100,TEAL,45,24)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'स्थिति',font=DEVA_MED,fill=TEAL,anchor='mm')
    d.text((cx+5,cy+44),'व्युत्थान',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    for i in range(2):
        a=i*math.pi; x=cx+math.cos(a)*180; y=cy+math.sin(a)*120
        col=[TEAL,CARDINAL][i]
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,180),fill=rgba(col,20),width=2)
        lineglow(im,[(cx,cy),(x,y)],col,3,85,6)
    d.text((640,505),'sthiti and vyutthāna — rest in the self and emergence into act',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,GOLD_LIGHT,120,16); glow(im,(cx,cy),95,TEAL,40,22)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(TEAL,220),width=2)
    d.text((cx,cy-40),'स्थिति',font=DEVA_MED,fill=TEAL,anchor='mm')
    for i in range(4):
        a=-math.pi/2+i*2*math.pi/4; r=lerp(10,160,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(TEAL,GREEN,i/3)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,170))
    d.text((640,505),'sthiti — rest in the self, the stable ground of all activity',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,GOLD_LIGHT,120,16); glow(im,(cx,cy),95,CARDINAL,40,22)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(CARDINAL,220),width=2)
    d.text((cx,cy-40),'व्युत्थान',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; x=cx+math.cos(a)*170; y=cy+math.sin(a)*116
        col=mix(CARDINAL,GOLD,i/5)
        d.ellipse((x-9,y-9,x+9,y+9),outline=rgba(col,180),fill=rgba(col,20),width=2)
        lineglow(im,[(cx,cy),(x,y)],col,3,85,6)
    d.text((640,505),'vyutthāna — emergence from the self into the world of form',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18); glow(im,(cx,cy),100,SLATE,40,24)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'स्थिति',font=DEVA_SMALL,fill=TEAL,anchor='mm')
    d.text((cx+5,cy+44),'व्युत्थान',font=DEVA_SMALL,fill=CARDINAL,anchor='mm')
    for i in range(2):
        a=-math.pi/2+i*math.pi; r=lerp(10,175,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(TEAL,CARDINAL,i)
        d.ellipse((x-8,y-8,x+8,y+8),outline=rgba(col,180),fill=rgba(col,20),width=2)
    d.text((640,505),'rest and emergence are not two states — they are one rhythm',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    for r,col in [(210,GOLD),(160,TEAL),(110,CARDINAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'स्थिति',font=DEVA_SMALL,fill=TEAL,anchor='mm')
    d.text((cx+5,cy+44),'व्युत्थान',font=DEVA_SMALL,fill=CARDINAL,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(TEAL,CARDINAL,i/11),170))
    d.text((640,505),'the sthiti-vyutthāna seal: one rhythm of rest and emergence',font=SUB_FONT,fill=UMBER,anchor='mm')

SCENES=[
Scene('sv01','Rest and Emergence','Two modes of the liberated.','Sthiti-Vyutthāna','Rest in the self and emergence into activity as one rhythm.','overview',['sthiti','vyutthana','rest','emergence'],'overview','dual Devanagari with two poles',sc01),
Scene('sv02','Sthiti — Rest in the Self','The stable ground.','Sthiti','Rest in the self as the ground of all.','rest_in_self',['rest','ground','stability'],'rest','four-fold stable expansion',sc02),
Scene('sv03','Vyutthāna — Emergence','Activity from the ground.','Vyutthāna','Emergence from the self into the world.','emergence',['emergence','activity','world'],'emergence','six-branch active emission',sc03),
Scene('sv04','One Rhythm','Rest and emergence together.','Sthiti-vyutthāna-tāla','The two are one rhythm of consciousness.','one_rhythm',['rhythm','rest','emergence'],'synthesis','dual expanding arcs',sc04),
Scene('sv05','The Sthiti-Vyutthāna Seal','One rhythm of consciousness.','Sthiti-vyutthāna-cakra','Closing seal: rest and emergence as one movement.','closing_seal',['seal','rest','emergence'],'seal','triple ring with dual Devanagari',sc05),
]

def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=sthiti_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,38); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)
def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),PARCHMENT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)
def metadata():
    manifest={'project':'Tantrāloka — Sthiti-Vyutthāna: Rest and Emergence','source_basis':'Tantrāloka: sthiti as rest in the self and vyutthāna as emergence into activity — two modes of the liberated.','style':{'family':'rest-activity cosmography','background':'warm parchment','ink':'umber and slate','accent':'teal for rest, cardinal for emergence, gold for unity','materials':['stable expansions','active emissions','dual arcs','triple rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['sv01'],'modes':['sv02','sv03'],'synthesis_and_seal':['sv04','sv05']},'reusability_notes':{'sv01':'Use for sthiti-vyutthāna overview.','sv02':'Use for rest in the self.','sv03':'Use for emergence into activity.','sv04':'Use for one rhythm.','sv05':'Use as closing rest-emergence seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Sthiti-Vyutthāna\n\nVisualize sthiti and vyutthāna: rest in the self and emergence into activity as the two modes of the liberated one.\n\n## Structure\n1. Two modes of one consciousness\n2. Sthiti — rest in the self\n3. Vyutthāna — emergence into act\n4. One rhythm\n5. The seal: rest and emergence as one\n\n## Visual rules\n- Teal for sthiti (cool, stable), cardinal for vyutthāna (warm, active).\n- Dual Devanagari as primary composition.\n- Stable forms for rest, radiating forms for emergence.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Sthiti-Vyutthāna Pack\n\n## Differentiation\nThis pack uses dual-mode imagery — teal rest and cardinal activity — distinct from the golden radiance of Ānanda.\n\n## New symbols\n1. dual Devanagari with two poles\n2. four-fold stable expansion\n3. six-branch active emission\n4. dual expanding arcs\n5. triple ring with dual Devanagari\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Sthiti-Vyutthāna Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)
def validate():
    p=ROOT/'sthiti_vyutthana_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))
def make_zip():
    z=ROOT/'sthiti_vyutthana_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['sthiti_vyutthana_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','sthiti_vyutthana_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')
def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'sthiti_vyutthana_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()
if __name__=='__main__': main()
