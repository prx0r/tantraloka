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
SEED = 56565

NIGHT = (16, 14, 20)
DEEP_VIOLET = (48, 36, 66)
VIOLET = (100, 82, 142)
LAVENDER = (166, 148, 196)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
TEAL = (90, 146, 148)
DEEP_TEAL = (64, 112, 114)
GREEN = (106, 152, 114)
DEEP_GREEN = (74, 116, 78)
UMBER = (78, 64, 50)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
WHITE = (252, 250, 246)
SILVER = (216, 222, 232)
PALE_GOLD = (252, 240, 216)
ROSE = (194, 108, 132)

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


def kula_ground(seed):
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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(14,12,18,208),outline=rgba(SLATE,55),width=1)
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

def branch(d,x0,y0,x1,y1,col,width=3):
    d.line((x0,y0,x1,y1),fill=rgba(col,180),width=width)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'कुल',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+5,cy+44),'अकुल',font=DEVA_MED,fill=LAVENDER,anchor='mm')
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*120
        col=mix(GOLD,TEAL,i/2)
        branch(d,cx,cy,x,y,col,2)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,180),fill=rgba(col,20),width=2)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*200; y=cy+math.sin(a)*136
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,LAVENDER,i/7),160))
    d.text((640,505),'kula and akula — the family of transmission and the beyond',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    glow(im,(cx,160),36,GOLD_LIGHT,120,14)
    d.ellipse((cx-12,146,cx+12,174),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,130),'परम्परा',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    nodes=[(cx,200),(cx-80,260),(cx+80,260),(cx-120,350),(cx-40,350),(cx+40,350),(cx+120,350),(cx-60,430),(cx+60,430)]
    for i,(x,y) in enumerate(nodes):
        s=smooth(.03+i*.05,.8,t)
        if s<=0: continue
        col=mix(GOLD,TEAL,i/(len(nodes)-1))
        d.ellipse((x-8,y-8,x+8,y+8),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,200))
        if i>0:
            px=nodes[i-1][0]; py=nodes[i-1][1]
            seg=partial([(px,py),(x,y)],smooth(.06+i*.05,.82,t))
            if len(seg)>1:lineglow(im,seg,mix(col,mix(GOLD,TEAL,(i-1)/(len(nodes)-1)),.5),2,75,5)
    d.text((640,505),'the lineage transmits power from guru to disciple across generations',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'गुरु',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*170; y=cy+math.sin(a)*110
        col=mix(GOLD,GREEN,i/4)
        seg=partial(bezier((cx,cy),(cx+math.cos(a-.1)*80,cy+math.sin(a-.1)*50),(x-math.cos(a)*30,y-math.sin(a)*20),(x,y),80),smooth(.04+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,3,90,6)
        d.ellipse((x-11,y-11,x+11,y+11),outline=rgba(col,190),fill=rgba(col,22),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,210))
        d.text((x,y+30),str(i+1),font=TINY_FONT,fill=col,anchor='mm')
    d.text((640,505),'from the guru, the teaching branches into five streams',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    for r,col in [(210,VIOLET),(160,GOLD),(108,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'कुल',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(10):
        a=i*2*math.pi/10; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(VIOLET,TEAL,i/9),160))
        branch(d,cx,cy,x,y,mix(VIOLET,TEAL,i/9),1)
    d.text((640,505),'kula is the embodied tradition — the family of transmission through time',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,LAVENDER,120,24)
    for r,col in [(200,VIOLET),(150,LAVENDER),(100,WHITE)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,110),width=2)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(LAVENDER,200),width=2)
    d.text((cx,cy-40),'अकुल',font=DEVA_MED,fill=LAVENDER,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.04; x=cx+math.cos(a)*175; y=cy+math.sin(a)*120
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(VIOLET,WHITE,i/13),150))
    d.text((640,505),'akula is the transcendent beyond — the source beyond all lineage',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'कुल',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+5,cy+36),'अकुल',font=DEVA_SMALL,fill=LAVENDER,anchor='mm')
    pts=[(cx-140,cy-70,CRIMSON),(cx+130,cy-80,TEAL),(cx-160,cy+50,GOLD),(cx+150,cy+60,GREEN)]
    for x,y,col in pts:
        seg=partial(bezier((cx,cy),(cx+(x-cx)*.3,y-30),(cx+(x-cx)*.7,y+30),(x,y),80),smooth(.05+.03*pts.index((x,y,col)),.84,t))
        if len(seg)>1:lineglow(im,seg,col,3,100,6)
        d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(col,190),fill=rgba(col,22),width=2)
    d.text((640,505),'kula and akula are not two — the family is the body of the transcendent',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,180),36,GOLD_LIGHT,120,14)
    d.ellipse((cx-12,166,cx+12,194),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,155),'गुरु',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; r=lerp(20,160,ease(t))
        x=cx+math.cos(a)*r; y=180+math.sin(a)*r*.7
        col=mix(GOLD,TEAL,i/5)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(col,180))
        lineglow(im,[(cx,180),(x,y)],col,2,70,5)
    d.text((640,505),'from the center, transmission radiates in all directions at once',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24)
    for r,col in [(220,VIOLET),(175,GOLD),(130,GREEN),(85,LAVENDER)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-40),'कुल',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+5,cy+40),'अकुल',font=DEVA_MED,fill=LAVENDER,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,VIOLET,i/15),170))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(WHITE,200))
    d.text((640,505),'the kula-akula seal: the family of transmission opens onto the infinite',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('ka01','Kula and Akula','The family and the beyond.','Kula-Akula','The embodied lineage of transmission and its transcendent source.','overview',['kula','akula','lineage'],'overview','dual Devanagari with three branches',sc01),
Scene('ka02','The Lineage','Power transmitted across generations.','Guru-paramparā','The chain of gurus carrying the teaching through time.','lineage_chain',['lineage','transmission','generations'],'lineage','nine-node descending chain',sc02),
Scene('ka03','The Guru','The source of teaching branches outward.','Guru-tattva','From the guru, the teaching flows in multiple streams.','guru_streams',['guru','teaching','branches'],'transmission','five-branch radial from center',sc03),
Scene('ka04','Kula — The Embodied Tradition','The family of transmission through time.','Kula','The lineage as living body of practice and transmission.','embodied_tradition',['kula','tradition','embodiment'],'kula','radial wheel with Devanagari',sc04),
Scene('ka05','Akula — The Transcendent Beyond','The source beyond all lineage.','Akula','The formless ground from which all transmission arises.','transcendent_source',['akula','transcendent','source'],'akula','expanding lavender void rings',sc05),
Scene('ka06','The Two Are One','Kula and akula are not separate.','Kula-akula-aikya','The embodied tradition is the body of the transcendent.','nondual_lineage',['nonduality','kula','akula'],'synthesis','four converging beams to center',sc06),
Scene('ka07','Radiant Transmission','Teaching radiates from the center.','Kula-dīkṣā','From the one source, transmission proceeds in all directions.','radiant_transmission',['transmission','radiation','center'],'transmission','radial emission from guru',sc07),
Scene('ka08','The Kula-Akula Seal','Family opens onto the infinite.','Kula-akula-cakra','Closing seal: lineage and transcendence as one field.','closing_seal',['seal','lineage','transcendence'],'seal','quadruple ring with dual Devanagari',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=kula_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Kula-Akula: Family and Beyond','source_basis':'Tantrāloka and Trika: kula as the embodied lineage of transmission, akula as the transcendent source beyond all form.','style':{'family':'lineage-tree cosmography','background':'deep violet night','ink':'silver and slate','accent':'gold, violet, teal, green, lavender','materials':['lineage node chains','branching transmission lines','radial guru emissions','expanding void rings','convergence beams']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['ka01'],'lineage':['ka02','ka03','ka07'],'kula_and_akula':['ka04','ka05'],'synthesis_and_seal':['ka06','ka08']},'reusability_notes':{'ka01':'Use for kula-akula overview.','ka02':'Use for lineage or chain of transmission.','ka03':'Use for guru as source of teaching.','ka04':'Use for embodied tradition.','ka05':'Use for transcendent beyond.','ka06':'Use for nonduality of lineage and beyond.','ka07':'Use for radiant transmission.','ka08':'Use as closing lineage seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Kula-Akula

## Aim
Visualize kula and akula: the embodied lineage of transmission and the transcendent source beyond all form.

## Structure
1. Kula and akula are the family and the beyond
2. The lineage of gurus transmits power through time
3. The guru is the source of teaching streams
4. Kula is the embodied tradition
5. Akula is the source beyond
6. They are not two
7. Transmission radiates from the center
8. The seal: lineage opens onto the infinite

## Visual rules
- Violet for akula (transcendent), gold for kula (embodied lineage).
- Lineage chains and branching trees for transmission.
- Expanding void rings for the transcendent.
- Devanagari for both terms as compositional anchors.
- Contrast dense nodes (kula) with open space (akula).
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Kula-Akula Pack

## Differentiation
This pack uses lineage and tree imagery — node chains, branching lines, radial transmission — distinct from the elemental or light-reflection packs.

## New symbols
1. dual Devanagari with three branches
2. nine-node descending chain
3. five-branch radial from center
4. radial wheel with Devanagari
5. expanding lavender void rings
6. four converging beams to center
7. radial emission from guru
8. quadruple ring with dual Devanagari
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Kula-Akula Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'kula_akula_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'kula_akula_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['kula_akula_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','kula_akula_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'kula_akula_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
