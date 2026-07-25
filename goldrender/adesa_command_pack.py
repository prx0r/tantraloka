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
SEED = 15151

NIGHT = (16, 14, 20)
DEEP_INDIGO = (42, 44, 82)
INDIGO = (68, 74, 130)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
TEAL = (90, 146, 148)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
SILVER = (216, 222, 232)
UMBER = (78, 64, 50)
GREEN = (106, 152, 114)
SAFFRON = (224, 152, 56)
VIOLET = (100, 84, 144)

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

def adesa_ground(seed):
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,100),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,80),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CARDINAL,GOLD)
def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)
def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(14,12,18,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE); d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=48):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22); glow(im,(cx,cy),110,CARDINAL,50,28)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आदेश',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,TEAL,i/7),180))
        lineglow(im,[(cx,cy),(x,y)],mix(GOLD,TEAL,i/7),2,70,5)
    d.text((640,505),'ādeśa — the command that carries authority across the lineage',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18); glow(im,(cx,cy),100,TEAL,45,24)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आदेश',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(7):
        y=lerp(150,410,i/6)
        seg=partial([(250,y),(1050,y)],smooth(.04+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,mix(GOLD,TEAL,i/6),3,85,6)
    d.text((640,505),'the command passes from guru to disciple — each receives the full authority',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18); glow(im,(cx,cy),95,INDIGO,45,24)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आज्ञा',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5; x=cx+math.cos(a)*165; y=cy+math.sin(a)*112
        col=mix(GOLD,TEAL,i/4)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,180),fill=rgba(col,20),width=2)
        lineglow(im,[(cx,cy),(x,y)],col,3,85,6)
    d.text((640,505),'the command is not a request — it carries the force of the source itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16); glow(im,(cx,cy),90,SAFFRON,40,22)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आदेश',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(5):
        r=lerp(20,170,ease(t)); a=i*2*math.pi/5
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(SAFFRON,GOLD,i/4)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,190))
    d.text((640,505),'the command radiates from the center — authorized by the source itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for r,col in [(200,GOLD),(155,CARDINAL),(110,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'आदेश',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/13),170))
    d.text((640,505),'the seal of ādeśa: authority transmitted through the living chain',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
Scene('ad01','The Command','Authority transmitted.','Ādeśa','The command that carries the full authority of the source.','overview',['adesa','command','authority'],'overview','eight-node radial with Devanagari',sc01),
Scene('ad02','Line of Transmission','Passed from guru to disciple.','Ādeśa-paramparā','The command passes unchanged through the lineage.','transmission_line',['transmission','lineage','guru'],'transmission','seven parallel transmission lines',sc02),
Scene('ad03','The Force of the Source','Not a request but an authority.','Ājñā','The command carries the force of the source itself.','source_force',['authority','force','source'],'authority','five-branch emission',sc03),
Scene('ad04','Radiant Command','Authority expanding from center.','Ādeśa-prabhā','The command radiates outward while remaining centered.','radiant_command',['radiation','command','center'],'transmission','five-point expanding radii',sc04),
Scene('ad05','The Ādeśa Seal','Authority in the living chain.','Ādeśa-cakra','Closing seal: the command as the living authority of the lineage.','closing_seal',['seal','adesa','authority'],'seal','triple ring with nodes',sc05),
]

def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=adesa_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,42); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
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
    manifest={'project':'Tantrāloka — Ādeśa: The Command','source_basis':'Tantrāloka: ādeśa as the command of the guru carrying the full authority of the lineage and source.','style':{'family':'command-transmission cosmography','background':'deep night field','ink':'slate and silver','accent':'gold, cardinal, teal, saffron','materials':['radial emission lines','parallel transmission lines','expanding radii','triple rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview_and_transmission':['ad01','ad02','ad04'],'authority_and_seal':['ad03','ad05']},'reusability_notes':{'ad01':'Use for ādeśa overview.','ad02':'Use for transmission line.','ad03':'Use for authority of source.','ad04':'Use for radiant command.','ad05':'Use as closing command seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Ādeśa\n\nVisualize ādeśa: the command transmitted from guru to disciple carrying the full authority of the source.\n\n## Structure\n1. The command carries the source's authority\n2. Passed unchanged through the lineage\n3. Not a request — authoritative force\n4. Radiates from the center\n5. The seal: authority in the living chain\n\n## Visual rules\n- Gold for authority, saffron for command-radiance, cardinal for the force.\n- Parallel lines for transmission.\n- Radial emission for command radiating.\n- No figures — abstract authority diagrams.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Ādeśa Pack\n\n## Differentiation\nThis pack uses transmission-line and radial-authority imagery — parallel lines, emission rays — distinct from the rotating wheels of Cakra or the guna-weaving of Prakṛti.\n\n## New symbols\n1. eight-node radial with Devanagari\n2. seven parallel transmission lines\n3. five-branch emission\n4. five-point expanding radii\n5. triple ring with nodes\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Ādeśa Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'adesa_command_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'adesa_command_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['adesa_command_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','adesa_command_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'adesa_command_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
