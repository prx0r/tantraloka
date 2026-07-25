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
SEED = 78787

NIGHT = (18, 16, 22)
DEEP_INDIGO = (42, 44, 84)
INDIGO = (70, 76, 132)
GOLD = (208, 168, 92)
GOLD_LIGHT = (246, 216, 142)
PALE_GOLD = (252, 242, 218)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (188, 56, 72)
ROSE = (194, 108, 132)
TEAL = (92, 148, 150)
GREEN = (108, 152, 114)
DEEP_GREEN = (74, 116, 78)
UMBER = (78, 64, 50)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
SILVER = (216, 222, 232)
SAFFRON = (224, 152, 56)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 22)
DEVA_TINY = ImageFont.truetype(FONT_DEVA, 16)


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


def virya_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.22))**2+((yy-H*.38)/(H*.28))**2)*2.4)
    base[...,0]+=halo*16; base[...,1]+=halo*12; base[...,2]+=halo*8
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
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(16,14,20,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def burst_ray(d,cx,cy,a,len_start,len_end,col,width=2):
    d.line((cx+math.cos(a)*len_start,cy+math.sin(a)*len_start,cx+math.cos(a)*len_end,cy+math.sin(a)*len_end),fill=rgba(col,190),width=width)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),80,GOLD_LIGHT,140,24)
    glow(im,(cx,cy),120,CARDINAL,60,32)
    for r,col in [(200,GOLD),(150,CARDINAL),(100,GOLD_LIGHT)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'वीर्य',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14; r=170+30*ease(t)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,CARDINAL,i/13),180))
        burst_ray(d,cx,cy,a,50,r,mix(GOLD,CARDINAL,i/13),2)
    d.text((640,505),'vīrya — the potent seed of mantra, charged with the energy of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'बीज',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(16):
        a=i*2*math.pi/16
        seg=partial([(cx+math.cos(a)*18,cy+math.sin(a)*18),(cx+math.cos(a)*190,cy+math.sin(a)*130)],smooth(.03+i*.03,.84,t))
        col=mix(GOLD_LIGHT,TEAL,i/15)
        if len(seg)>1:lineglow(im,seg,col,3,85,6)
        x=cx+math.cos(a)*200; y=cy+math.sin(a)*136
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,180))
    d.text((640,505),'the seed contains the entire tree — the mantra contains the entire cosmos',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,20)
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5; r=lerp(20,170,ease(t))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GOLD,SAFFRON,i/4)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,190),fill=rgba(col,22),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(WHITE,200))
        lineglow(im,[(cx,cy),(x,y)],col,3,90,6)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'वीर्य',font=DEVA_MED,fill=SAFFRON,anchor='mm')
    d.text((640,505),'the potency of the mantra is not in its meaning but in its energy',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,80),36,GOLD_LIGHT,120,14)
    d.ellipse((cx-12,66,cx+12,94),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,55),'मन्त्र',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; r=lerp(10,150,ease(t))
        x=cx+math.cos(a)*r; y=80+math.sin(a)*r*.7
        col=mix(GOLD,TEAL,i/5)
        d.ellipse((x-7,y-7,x+7,y+7),fill=rgba(col,180))
        lineglow(im,[(cx,80),(x,y)],col,2,70,5)
    d.text((640,505),'mantra is vīrya — power that vibrates, not information that signifies',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for r,col in [(200,GOLD),(155,CARDINAL),(110,GREEN)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'स्पन्द',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=i*2*math.pi/16+t*.04; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,GREEN,i/15),170))
    d.text((640,505),'spanda — the vibration that is the potency of consciousness itself',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'वीर्य',font=DEVA_MED,fill=CARDINAL,anchor='mm')
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*116
        col=mix(CARDINAL,GOLD,i/7)
        seg=partial(bezier((cx,cy),(cx+math.cos(a-.1)*80,cy+math.sin(a-.1)*50),(x+math.cos(a)*20,y+math.sin(a)*10),(x,y),80),smooth(.04+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,3,95,7)
        d.ellipse((x-9,y-9,x+9,y+9),outline=rgba(col,190),fill=rgba(col,22),width=2)
    d.text((640,505),'vīrya is the power that erupts as the universe — the same power that returns',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'वीर्य',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    seeds=['ॐ','ह्रीं','श्रीं','क्लीं','हं','सौः']
    for i,ch in enumerate(seeds):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*150; y=cy+math.sin(a)*100
        col=mix(GOLD,TEAL,i/5)
        d.ellipse((x-16,y-16,x+16,y+16),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.text((x,y),ch,font=DEVA_SMALL,fill=col,anchor='mm')
        seg=partial([(cx,cy),(x,y)],smooth(.04+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,2,75,5)
    d.text((640,505),'bīja-mantras are vīrya made audible — power condensed into sound',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24)
    for r,col in [(220,SLATE),(175,GOLD),(130,CARDINAL),(85,GREEN)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'वीर्य',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04
        for ri in [175,120]:
            x=cx+math.cos(a)*ri; y=cy+math.sin(a)*ri*.68
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,CARDINAL,i/15),160))
    d.text((640,505),'the vīrya seal: the potent seed of all that is and all that can be',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('vi01','Mantra Potency','The power of the seed.','Vīrya','The potent energy of mantra that contains the cosmos.','overview',['virya','potency','seed'],'overview','radial burst with rings',sc01),
Scene('vi02','The Seed Contains the Tree','The whole cosmos in one syllable.','Bīja-viśva','Every mantra is a seed that contains the universe.','seed_contains',['seed','cosmos','containment'],'potency','emission rays from bindu',sc02),
Scene('vi03','Vīrya as Energy','Power vibrating, not signifying.','Vīrya-spanda','Mantra potency is vibrational, not semantic.','energy_not_meaning',['energy','vibration','potency'],'potency','five-branch radial burst',sc03),
Scene('vi04','Mantra is Power','Not information but vibration.','Mantra-vīrya','Mantra is effective because of its vīrya, not its meaning.','mantra_power',['mantra','power','vibration'],'mantra','six-ray emission from source',sc04),
Scene('vi05','Spanda as Potency','The pulse that carries all power.','Spanda-vīrya','Spanda is the vibration that is the potency of consciousness.','spanda_potency',['spanda','pulse','potency'],'vibration','triple ring with nodes',sc05),
Scene('vi06','Eruption and Return','Power goes out and comes back.','Vīrya-saṃcāra','The same power erupts as universe and returns to its source.','eruption_return',['eruption','return','power'],'process','eight-curve bezier emission',sc06),
Scene('vi07','Bīja-mantras as Vīrya','Seed-sound as condensed power.','Bīja-vīrya','The seed mantras are vīrya made audible.','seed_sound',['bija','sound','power'],'mantras','six bīja in radial orbit',sc07),
Scene('vi08','The Vīrya Seal','The seed of all that is.','Vīrya-cakra','Closing seal: potent consciousness as the source of all.','closing_seal',['seal','virya','potency'],'seal','quadruple ring with double node ring',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=virya_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Vīrya: Mantra Potency','source_basis':'Tantrāloka doctrine of mantra-vīrya: the potent seed-energy of mantra as vibrational power, not semantic meaning.','style':{'family':'seed-potency cosmography','background':'deep night with cardinal-gold burst','ink':'silver and slate','accent':'gold, cardinal, teal, green, saffron','materials':['radial burst rings','emission rays','branching potency lines','bīja medallions','double node rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['vi01'],'potency':['vi02','vi03','vi05'],'mantra_and_return':['vi04','vi06','vi07'],'seal':['vi08']},'reusability_notes':{'vi01':'Use for vīrya overview or mantra potency.','vi02':'Use for seed containing cosmos.','vi03':'Use for potency as energy.','vi04':'Use for mantra as vibration.','vi05':'Use for spanda as potency.','vi06':'Use for eruption and return.','vi07':'Use for bīja as condensed power.','vi08':'Use as closing potency seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Vīrya

## Aim
Visualize vīrya: the potent seed-energy of mantra, the power of consciousness that vibrates, erupts, and returns.

## Structure
1. Vīrya is mantra potency
2. The seed contains the entire tree
3. Vīrya is energy, not meaning
4. Mantra is power vibrating
5. Spanda is the pulse of potency
6. Power erupts and returns
7. Bīja-mantras are vīrya audible
8. The seal: potent consciousness

## Visual rules
- Cardinal/gold burst imagery for potency.
- Rays, seeds, and emission lines.
- Mantra bījas as central glyphs.
- Triple rings for containment of power.
- Contrast between concentrated seed and radiating burst.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Vīrya Pack\n\n## Differentiation\nThis pack uses burst and seed imagery — rays, emissions, germinating lines — distinct from the phoneme matrix of Śabdarāśi or the lineage trees of Kula-Akula.\n\n## New symbols\n1. radial burst with rings\n2. emission rays from bindu\n3. five-branch radial burst\n4. six-ray emission from source\n5. triple ring with nodes\n6. eight-curve bezier emission\n7. six bīja in radial orbit\n8. quadruple ring with double node ring\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Vīrya Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'virya_potency_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'virya_potency_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['virya_potency_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','virya_potency_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'virya_potency_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
