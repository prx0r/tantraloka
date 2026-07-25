#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent; FRAMES_ROOT = ROOT / 'frames'; SCENES_ROOT = ROOT / 'scenes'
W, H = 1280, 720; FPS = 10; DURATION = 4.8; NFRAMES = int(FPS * DURATION); SEED = 18181

SKY = (24, 30, 42); DEEP_SKY = (36, 44, 62); PALE_BLUE = (160, 180, 204)
SILVER = (218, 224, 234); WHITE = (252, 250, 246); GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138); SLATE = (106, 118, 138); MIST = (176, 186, 204)
TEAL = (90, 146, 148); UMBER = (78, 64, 50); CRIMSON = (154, 46, 60)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31); SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22); DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))

def shanti_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(SKY,dtype=np.float32)
    coarse=rng.normal(0,1,(36,64)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(22))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.0 + fine[...,None]*0.8
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*16,0,22)[...,None]
    g=np.exp(-(((xx-W/2)/(W*.30))**2+((yy-H*.40)/(H*.26))**2)*2.4)
    base[...,0]+=g*12; base[...,1]+=g*16; base[...,2]+=g*24
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,80),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,60),width=1)
def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(22,28,38,200),outline=rgba(SLATE,50),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=PALE_BLUE); d.text((124,y+58),subtitle,font=SUB_FONT,fill=SLATE)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=35):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(.8,1.8))
        c=mix(PALE_BLUE,SILVER,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,50))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),70,SILVER,120,24); glow(im,(cx,cy),110,PALE_BLUE,50,30)
    for i in range(4):
        r=80+i*40; d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(SLATE,SILVER,i/3),80),width=1)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,200))
    d.text((cx,cy-40),'शान्ति',font=DEVA_MED,fill=SILVER,anchor='mm')
    d.text((640,505),'śānti — the peace that is the nature of consciousness itself',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),60,SILVER,110,20)
    for i in range(6):
        y=lerp(160,410,i/5)
        seg=partial([(230,y),(1050,y)],smooth(.04+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,mix(SLATE,PALE_BLUE,i/5),2,70,5)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,180))
    d.text((cx,cy-40),'शान्ति',font=DEVA_SMALL,fill=PALE_BLUE,anchor='mm')
    d.text((640,505),'stillness is not the absence of movement — it is the ground of all movement',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),55,SILVER,110,18); glow(im,(cx,cy),95,PALE_BLUE,40,24)
    for i in range(4):
        a=-math.pi/2+i*2*math.pi/4; r=lerp(20,160,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(SILVER,PALE_BLUE,i/3)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,160))
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,180))
    d.text((cx,cy-50),'शान्ति',font=DEVA_MED,fill=SILVER,anchor='mm')
    d.text((640,505),'the peace of consciousness is not a state among states — it is the ground',font=SUB_FONT,fill=SLATE,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    glow(im,(cx,cy),65,GOLD_LIGHT,120,22)
    for r,col in [(200,GOLD),(150,GOLD_LIGHT),(100,WHITE)]:
        rr=r*ease(t)
        d.ellipse((cx-rr,cy-rr*.72,cx+rr,cy+rr*.72),outline=rgba(col,90),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,220))
    d.text((cx,cy-50),'शान्ति',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the śānti seal: the peace that is the source and end of all striving',font=SUB_FONT,fill=SLATE,anchor='mm')

SCENES=[
Scene('sa01','Peace','The ground of consciousness.','Śānti','The peace that is the very nature of awareness.','overview',['shanti','peace','ground'],'overview','faint concentric blue rings',sc01),
Scene('sa02','Stillness Within','The ground of all movement.','Śānti-sthiti','Stillness is not absence but the ground.','stillness',['stillness','ground','movement'],'stillness','horizontal peaceful lines',sc02),
Scene('sa03','Not a State','The ground of all states.','Śānti-prakṛti','Śānti is not a state among states.','not_a_state',['peace','ground','states'],'peace','four-fold peaceful expansion',sc03),
Scene('sa04','The Śānti Seal','Peace as source and end.','Śānti-cakra','Closing seal: peace as the ground of all.','closing_seal',['seal','peace','ground'],'seal','expanding gold rings',sc04),
]

def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=shanti_ground(SEED+(hash(sc.id)%10000)+i)
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
    sheet=Image.new('RGB',(1280,360),SKY)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)
def metadata():
    manifest={'project':'Tantrāloka — Śānti: Peace','source_basis':'Tantrāloka: śānti as the peace that is the very nature of consciousness, the ground of all states.','style':{'family':'peace-field cosmography','background':'deep blue-sky field','ink':'slate and silver','accent':'silver, pale blue, gold','materials':['faint rings','horizontal lines','peaceful expansions','gold ground']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['sa01'],'peace_and_seal':['sa02','sa03','sa04']},'reusability_notes':{'sa01':'Use for śānti overview.','sa02':'Use for stillness as ground.','sa03':'Use for peace beyond states.','sa04':'Use as closing peace seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Śānti\n\nVisualize śānti: the peace that is the nature of consciousness itself.\n\n## Structure\n1. Śānti is the ground of awareness\n2. Stillness is the ground of movement\n3. Not a state among states\n4. The seal: peace as source and end\n\n## Visual rules\n- Blue-sky field, silver and pale blue for peace.\n- Minimal, spacious, calm.\n- Horizontal lines for stillness.\n- Expanding gold rings at the seal for peace as ground.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Śānti Pack\n\n## Differentiation\nThis pack uses minimal, spacious blue-sky imagery — calm, horizontal, expansive — distinct from the crossing imagery of Tīrtha.\n\n## New symbols\n1. faint concentric blue rings\n2. horizontal peaceful lines\n3. four-fold peaceful expansion\n4. expanding gold rings\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Śānti Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)
def validate():
    p=ROOT/'shanti_peace_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))
def make_zip():
    z=ROOT/'shanti_peace_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['shanti_peace_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','shanti_peace_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')
def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'shanti_peace_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()
if __name__=='__main__': main()
