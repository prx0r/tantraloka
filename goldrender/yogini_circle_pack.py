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
SEED = 16161

NIGHT = (18, 14, 22)
DEEP_VIOLET = (50, 34, 64)
VIOLET = (102, 78, 138)
LAVENDER = (168, 148, 196)
ROSE = (196, 106, 130)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
TEAL = (90, 146, 148)
GREEN = (106, 152, 114)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
SILVER = (216, 222, 232)
SAFFRON = (224, 152, 56)
PALE_VIOLET = (200, 188, 218)
UMBER = (78, 64, 50)

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

def yogini_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,95),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,75),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)
def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)
def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(16,12,20,206),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE); d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(VIOLET,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22); glow(im,(cx,cy),110,VIOLET,55,28)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'योगिनी',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        col=mix(VIOLET,GOLD,i/7)
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,180),fill=rgba(col,18),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,210))
        lineglow(im,[(cx,cy),(x,y)],col,2,70,5)
    d.text((640,505),'yoginī — the circle of powers that surround the heart of awareness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18); glow(im,(cx,cy),100,LAVENDER,50,26)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'योगिनी',font=DEVA_SMALL,fill=LAVENDER,anchor='mm')
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12+t*.04; x=cx+math.cos(a)*175; y=cy+math.sin(a)*118
        col=mix(VIOLET,ROSE,i/11)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,180))
    d.text((640,505),'the yoginīs circle around the center — powers in eternal motion',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18); glow(im,(cx,cy),95,ROSE,45,24)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8+t*.05; r=160+30*ease(t)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(ROSE,GOLD,i/7)
        d.ellipse((x-8,y-8,x+8,y+8),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(WHITE,190))
    d.text((640,505),'sixty-four yoginīs — each a distinct power of the one consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18); glow(im,(cx,cy),100,TEAL,45,24)
    for r,col,n in [(200,GOLD,8),(150,ROSE,6),(100,TEAL,4)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.04; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,180))
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'योगिनी',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the yoginīs are the powers of the senses, mind, and consciousness itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),65,GOLD_LIGHT,140,20); glow(im,(cx,cy),105,VIOLET,50,26)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'योगिनी',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*160; y=cy+math.sin(a)*108
        col=mix(VIOLET,GOLD,i/2)
        lineglow(im,[(cx,cy),(x,y)],col,3,90,6)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,180),fill=rgba(col,20),width=2)
    d.text((640,505),'the yoginīs are the self-expression of the goddess — her powers made manifest',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
Scene('yo01','The Circle of Yoginīs','Powers surrounding the center.','Yoginī-cakra','The circle of yoginīs as the powers of consciousness in motion.','overview',['yogini','circle','powers'],'overview','eight-node radial ring',sc01),
Scene('yo02','The Turning Circle','Powers in eternal motion.','Yoginī-valaya','The yoginīs circle the center without cease.','turning_circle',['circle','motion','powers'],'circle','twelve-node rotating ring',sc02),
Scene('yo03','Sixty-Four Powers','Each a distinct energy.','Catuḥ-ṣaṣṭi-yoginī','Sixty-four distinct powers of consciousness.','sixty_four',['sixty-four','powers','consciousness'],'powers','eight-node expanding orbit',sc03),
Scene('yo04','Concentric Circles','Inner and outer powers.','Yoginī-maṇḍala','Inner and outer circles of yoginīs.','concentric_circles',['concentric','circles','inner-outer'],'structure','three concentric node rings',sc04),
Scene('yo05','The Yoginī Seal','Powers as self-expression of the goddess.','Yoginī-cakra','Closing seal: the yoginīs as the living powers of consciousness.','closing_seal',['seal','yogini','powers'],'seal','three-branch seal with Devanagari',sc05),
]

def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=yogini_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,45); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),NIGHT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)
def metadata():
    manifest={'project':'Tantrāloka — Yoginī: The Circle of Powers','source_basis':'Tantrāloka: the yoginīs as the circle of powers surrounding the center of consciousness.','style':{'family':'violet-power circle cosmography','background':'deep violet night','ink':'silver and slate','accent':'violet, gold, rose, teal','materials':['radial node rings','rotating circles','concentric rings','three-branch seal']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['yo01'],'circle_and_powers':['yo02','yo03','yo04'],'seal':['yo05']},'reusability_notes':{'yo01':'Use for yoginī overview.','yo02':'Use for turning circle.','yo03':'Use for sixty-four powers.','yo04':'Use for concentric circles.','yo05':'Use as closing yoginī seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Yoginī\n\nVisualize the circle of yoginīs: the powers of consciousness orbiting the center.\n\n## Structure\n1. The yoginīs circle the center\n2. Eternal motion of powers\n3. Sixty-four distinct energies\n4. Inner and outer circles\n5. The seal: powers as self-expression\n\n## Visual rules\n- Violet and rose palette for yoginī energy.\n- Gold for the center, violet for the circling powers.\n- Node rings and rotating circles.\n- No anthropomorphic yoginī figures — abstract power nodes.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Yoginī Pack\n\n## Differentiation\nThis pack uses violet-power node rings and rotating circles — distinct from the authority lines of Ādeśa.\n\n## New symbols\n1. eight-node radial ring\n2. twelve-node rotating ring\n3. eight-node expanding orbit\n4. three concentric node rings\n5. three-branch seal with Devanagari\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Yoginī Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)
def validate():
    p=ROOT/'yogini_circle_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))
def make_zip():
    z=ROOT/'yogini_circle_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['yogini_circle_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','yogini_circle_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')
def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'yogini_circle_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()
if __name__=='__main__': main()
