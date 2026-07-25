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
SEED = 99900

NIGHT = (14, 16, 22)
DEEP_INDIGO = (38, 44, 84)
INDIGO = (66, 74, 132)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
PALE_GOLD = (252, 242, 218)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
ROSE = (194, 108, 132)
TEAL = (90, 146, 148)
GREEN = (106, 152, 114)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
UMBER = (78, 64, 50)
SILVER = (216, 222, 232)
VIOLET = (100, 84, 144)
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


def trikona_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.8 + fine[...,None]*1.0
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
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(12,14,20,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=48):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def regular_tri(cx,cy,r,rot=0):
    return [(cx+math.cos(rot+2*math.pi*i/3)*r,cy+math.sin(rot+2*math.pi*i/3)*r) for i in range(3)]

def draw_tri(d,pts,col,fill=None,width=3):
    d.polygon(pts,outline=rgba(col,210),fill=fill or rgba(col,12),width=width)
    for i in range(3):
        a=pts[i]; b=pts[(i+1)%3]
        d.line((a,b),fill=rgba(col,210),width=width)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    tri=regular_tri(cx,cy,190-ease(t)*20,-math.pi/2)
    draw_tri(d,tri,GOLD,rgba(GOLD,18),3)
    tri2=regular_tri(cx,cy,120+ease(t)*10,math.pi/2)
    draw_tri(d,tri2,GOLD_LIGHT,rgba(GOLD_LIGHT,14),2)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-55),'त्रिकोण',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*200; y=cy+math.sin(a)*136
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,TEAL,i/7),160))
    d.text((640,505),'trikona — the sacred triangle, the geometric root of all yantra',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    inner=regular_tri(cx,cy,lerp(10,100,ease(t)),-math.pi/2+t*.05)
    draw_tri(d,inner,CRIMSON,rgba(CRIMSON,16),3)
    outer=regular_tri(cx,cy,lerp(30,180,ease(t)),math.pi/2+t*.05)
    draw_tri(d,outer,GOLD,rgba(GOLD,10),2)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'त्रिकोण',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    for i in range(3):
        px,py=outer[i]
        d.ellipse((px-8,py-8,px+8,py+8),outline=rgba(GOLD,190),fill=rgba(GOLD,20),width=2)
    d.text((640,505),'the triangle arises from the bindu — geometry born of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    for i in range(4):
        r=lerp(30,200,1-ease(t))-i*30
        if r<10: continue
        tri=regular_tri(cx,cy,r,-math.pi/2+i*.2+t*.03)
        draw_tri(d,tri,mix(SLATE,GOLD,i/3),width=2)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'यन्त्र',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'overlapping triangles generate the structure of the yantra',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for s in [1,-1]:
        tri=regular_tri(cx,cy,160,math.pi/2*s)
        draw_tri(d,tri,mix(GOLD,CRIMSON,(s+1)/2),rgba(mix(GOLD,CRIMSON,(s+1)/2),10),3)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'षट्कोण',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; x=cx+math.cos(a)*170; y=cy+math.sin(a)*116
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/5),170))
    d.text((640,505),'the six-pointed star — the union of upward and downward triangles',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    tri=regular_tri(cx,cy,180,-math.pi/2)
    draw_tri(d,tri,GOLD,rgba(GOLD,12),3)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*100; y=cy+math.sin(a)*100
        col=mix(CRIMSON,TEAL,i/2)
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.text((x,y+30),['icchā','jñāna','kriyā'][i],font=TINY_FONT,fill=col,anchor='mm')
    d.text((640,505),'the three vertices are will, knowledge, and action — powers of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    for i in range(5):
        r=80+i*30
        tri=regular_tri(cx,cy,r,-math.pi/2+i*.3+t*.02)
        draw_tri(d,tri,mix(GOLD,VIOLET,i/4),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'त्रिकोण',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    d.text((640,505),'nested triangles — each containing the next, all containing the center',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),65,GOLD_LIGHT,140,20)
    tri=regular_tri(cx,cy,180,-math.pi/2)
    draw_tri(d,tri,GOLD,rgba(GOLD,10),3)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3
        x1=cx+math.cos(a)*180; y1=cy+math.sin(a)*180
        # rays from vertices
        for j in range(6):
            ang=a-math.pi/2+j*math.pi/3
            seg=partial([(x1,y1),(x1+math.cos(ang)*60,y1+math.sin(ang)*60)],ease(t))
            if len(seg)>1:lineglow(im,seg,mix(GOLD,TEAL,j/5),2,65,5)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'from the triangle, all geometry radiates — the yantra unfolds',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),80,GOLD_LIGHT,150,24)
    for r,col in [(220,SLATE),(175,GOLD),(130,CRIMSON),(85,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    tri=regular_tri(cx,cy,160,-math.pi/2)
    draw_tri(d,tri,GOLD,rgba(GOLD,14),3)
    tri2=regular_tri(cx,cy,100,math.pi/2)
    draw_tri(d,tri2,GOLD_LIGHT,rgba(GOLD_LIGHT,10),2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-55),'त्रिकोण',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/15),170))
    d.text((640,505),'the trikona seal: all geometry returns to the triangle of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('tk01','The Sacred Triangle','The geometric root of all yantra.','Trikona','The triangle as the fundamental form of sacred geometry.','overview',['triangle','geometry','yantra'],'overview','interlocking triangles with bindu',sc01),
Scene('tk02','Triangle from Bindu','Geometry born of consciousness.','Bindu-trikona','The triangle arises from the point, form from the formless.','triangle_from_point',['bindu','triangle','emergence'],'emergence','expanding nested triangles',sc02),
Scene('tk03','Overlapping Triangles','The yantra emerges.','Yantra-trikona','Overlapping triangles generate the structure of the yantra.','yantra_emergence',['yantra','overlap','geometry'],'structure','converging triangle rings',sc03),
Scene('tk04','Six-Pointed Star','Upward and downward triangles.','Ṣaṭkoṇa','The upward and downward triangles interlock as the six-pointed star.','six_pointed_star',['star','union','polarity'],'union','superimposed triangles',sc04),
Scene('tk05','Will, Knowledge, Action','The three powers at the vertices.','Icchā-jñāna-kriyā','The three vertices are the three powers of consciousness.','three_powers',['will','knowledge','action'],'powers','triangle with three nodal vertices',sc05),
Scene('tk06','Nested Triangles','Each contains the next.','Trikona-valaya','Nested triangles showing the self-similar structure of reality.','nested_triangles',['nested','self-similar','geometry'],'structure','five nested rotating triangles',sc06),
Scene('tk07','Radiant Geometry','From the triangle, all form unfolds.','Trikona-prabhā','The triangle radiates into all geometric form.','radiant_geometry',['radiation','geometry','unfolding'],'radiation','vertex rays from triangle',sc07),
Scene('tk08','The Trikona Seal','All geometry returns to the triangle.','Trikona-cakra','Closing seal: the triangle as the root of all form.','closing_seal',['seal','triangle','geometry'],'seal','quadruple ring with dual triangles',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=trikona_ground(SEED+(hash(sc.id)%10000)+i)
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
    manifest={'project':'Tantrāloka — Trikona: The Sacred Triangle','source_basis':'Tantrāloka and Trika yantra-śāstra: the triangle as the fundamental geometric form, its emergence from bindu, and its radiation into all form.','style':{'family':'sacred-geometry cosmography','background':'deep night field','ink':'silver and slate','accent':'gold, crimson, teal, violet','materials':['interlocking triangles','nested triangular rings','six-pointed stars','vertex rays','triangle chains']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['tk01'],'emergence_and_structure':['tk02','tk03','tk06'],'union_and_powers':['tk04','tk05'],'radiation_and_seal':['tk07','tk08']},'reusability_notes':{'tk01':'Use for trikona or sacred geometry overview.','tk02':'Use for triangle emerging from bindu.','tk03':'Use for overlapping triangles or yantra.','tk04':'Use for six-pointed star or union.','tk05':'Use for will, knowledge, action.','tk06':'Use for nested or self-similar triangles.','tk07':'Use for radiant geometry.','tk08':'Use as closing triangle seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Trikona

## Aim
Visualize trikona: the sacred triangle as the fundamental geometric form from which all yantra and manifestation unfolds.

## Structure
1. The triangle is the root of sacred geometry
2. The triangle arises from the bindu
3. Overlapping triangles generate the yantra
4. Upward and downward triangles form the six-pointed star
5. Vertices = will, knowledge, action
6. Nested triangles show self-similarity
7. From the triangle, all geometry radiates
8. The seal: the triangle of consciousness

## Visual rules
- Pure geometric abstraction — no representational elements.
- Gold triangles for the primary form.
- Crimson and teal for vertices and powers.
- Nested and overlapping structures.
- Rotating triangles suggest living geometry.
- Night field to emphasize luminous lines.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Trikona Pack\n\n## Differentiation\nThis pack uses pure geometric abstraction — triangles, stars, nested polygons — distinct from the broken-ring imagery of Avadhūta or the seed-burst of Vīrya.\n\n## New symbols\n1. interlocking triangles with bindu\n2. expanding nested triangles\n3. converging triangle rings\n4. superimposed triangles (star)\n5. triangle with three nodal vertices\n6. five nested rotating triangles\n7. vertex rays from triangle\n8. quadruple ring with dual triangles\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Trikona Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'trikona_triangle_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'trikona_triangle_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['trikona_triangle_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','trikona_triangle_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'trikona_triangle_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
