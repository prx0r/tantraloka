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
SEED = 71717

# Mantra-cycle palette: deep ink, pearl light, copper, electric indigo
NIGHT = (17, 21, 32)
INK_BLUE = (28, 39, 63)
DEEP_INDIGO = (48, 58, 110)
INDIGO = (78, 92, 168)
ELECTRIC = (112, 137, 210)
PEARL = (239, 238, 230)
WHITE = (252, 250, 244)
SILVER = (192, 200, 216)
COPPER = (194, 111, 72)
ROSE = (188, 98, 130)
GOLD = (205, 163, 78)
GOLD_LIGHT = (244, 213, 135)
TEAL = (86, 145, 150)
MIST = (137, 151, 176)
ASH = (90, 98, 118)
BLACK = (10, 12, 17)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)

SEEDS = ['ॐ', 'ह्रीं', 'क्लीं', 'सौः', 'हं']
PHRASE = ['ॐ', 'ह्रीं', 'श्रीं', 'क्लीं', 'भैरवाय', 'नमः']


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t):
    t=clamp(t); return 0.5 - 0.5*math.cos(math.pi*t)
def ease_out_cubic(t):
    t=clamp(t); return 1-(1-t)**3
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.1 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*20,0,27); base -= vign[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.32))**2+((yy-H*.38)/(H*.26))**2)*2.5)
    for i in range(3): base[...,i]+=halo*(26 if i==2 else 10)
    low=np.exp(-(((xx-W/2)/(W*.22))**2+((yy-H*.68)/(H*.18))**2)*2.7)
    for i in range(3): base[...,i]+=low*(10 if i<2 else 18)
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def draw_glow(im,xy,radius,color,alpha=150,blur=16):
    gl=layer(); d=ImageDraw.Draw(gl); x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))

def draw_line_glow(im,pts,color,width=3,alpha=150,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(SILVER,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(COPPER,90),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,DEEP_INDIGO,COPPER)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(15,19,29,202),outline=rgba(SILVER,60),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=SILVER)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1);u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def partial_polyline(points,amount):
    amount=clamp(amount)
    if amount<=0:return []
    if amount>=1:return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx; out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]);s=12*scale
    draw.polygon([p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)],fill=rgba(color,230))
def dust(im,seed,n=72):
    rng=np.random.default_rng(seed);ov=layer();d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120));y=float(rng.uniform(120,H-180));r=float(rng.uniform(1,2.3));c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(25,80))))
    im.alpha_composite(ov)
def orbit_points(cx,cy,rx,ry,phase=0,n=120):
    return [(cx+math.cos(phase+i*2*math.pi/(n-1))*rx,cy+math.sin(phase+i*2*math.pi/(n-1))*ry) for i in range(n)]
def draw_beads(draw,cx,cy,rx,ry,count,phase,col,labels=None,r=8):
    for i in range(count):
        a=phase+i*2*math.pi/count;x=cx+math.cos(a)*rx;y=cy+math.sin(a)*ry
        draw.ellipse((x-r,y-r,x+r,y+r),fill=rgba(col,190),outline=rgba(PEARL,110),width=1)
        if labels:
            draw.text((x,y),labels[i%len(labels)],font=DEVA_SMALL,fill=PEARL,anchor='mm')

def draw_breath_wave(im,x0,x1,cy,amp,cycles,phase,col,width=3):
    pts=[]
    for i in range(180):
        u=i/179;x=lerp(x0,x1,u);y=cy+math.sin(u*2*math.pi*cycles+phase)*amp
        pts.append((x,y))
    draw_line_glow(im,pts,col,width,110,6)
    return pts

@dataclass
class Scene:
    id:str;title:str;subtitle:str;term:str;summary:str;mode:str;tags:list[str];group:str;technique:str;draw_fn:Callable[[Image.Image,float],None]


def sc01(im,t):
    d=ImageDraw.Draw(im);cx,cy=W/2,282
    radii=[72,118,166,220];cols=[GOLD_LIGHT,COPPER,INDIGO,ELECTRIC]
    for i,(r,col) in enumerate(zip(radii,cols)):
        pts=partial_polyline(orbit_points(cx,cy,r,r*.66,phase=-math.pi/2+i*.25),smoothstep(.03+i*.08,.72+i*.06,t))
        if len(pts)>1:
            draw_line_glow(im,pts,col,3,105,6);draw_arrowhead(d,pts[-2],pts[-1],col,.8)
        draw_beads(d,cx,cy,r,r*.66,3+i*3,t*.18*(1 if i%2==0 else -1),col,r=5)
    draw_glow(im,(cx,cy),48,PEARL,120,14);d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,506),'mantra cycles arise in expanding proportion to the respiratory field',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im);cx,cy=W/2,282
    draw_breath_wave(im,180,1100,cy,78,1.0,t*.25,ELECTRIC,4)
    # mantra beads ride the breath
    for i,ch in enumerate(PHRASE):
        u=(i+.5)/len(PHRASE);x=lerp(210,1070,u);y=cy+math.sin(u*2*math.pi+t*.25)*78
        d.ellipse((x-20,y-20,x+20,y+20),outline=rgba(mix(COPPER,ELECTRIC,i/len(PHRASE)),180),fill=rgba(INK_BLUE,150),width=2)
        d.text((x,y),ch,font=DEVA_SMALL,fill=PEARL,anchor='mm')
    d.text((640,506),'the breath becomes a temporal carrier for articulated mantra',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im);cx,cy=W/2,282
    draw_glow(im,(cx,cy),78,GOLD_LIGHT,125,22)
    for r,col in [(40,GOLD_LIGHT),(78,COPPER),(122,INDIGO)]:d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(col,145),width=2)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=rgba(WHITE,255),outline=rgba(GOLD,230),width=2)
    d.text((cx,cy),'ॐ',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    # one short breath orbit
    pts=partial_polyline(orbit_points(cx,cy,174,102,-math.pi/2),ease_in_out(t))
    if len(pts)>1:draw_line_glow(im,pts,GOLD_LIGHT,4,130,8)
    d.text((640,506),'the shortest cycle holds a seed mantra within one compact breath-span',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im);cx,cy=W/2,282
    counts=[3,6,12];rs=[84,144,214];cols=[COPPER,INDIGO,ELECTRIC]
    for i,(count,r,col) in enumerate(zip(counts,rs,cols)):
        pts=partial_polyline(orbit_points(cx,cy,r,r*.64,-math.pi/2+i*.2),smoothstep(.02+i*.09,.8+i*.05,t))
        if len(pts)>1:draw_line_glow(im,pts,col,3,105,6)
        draw_beads(d,cx,cy,r,r*.64,count,t*.15*(1 if i%2==0 else -1),col,labels=PHRASE,r=11 if i==0 else 8)
    d.text((640,506),'as the formula lengthens, the containing respiratory orbit expands',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im)
    # phrase ladder mapped to increasing breath durations
    levels=[('bīja',3,COPPER),('mantra',6,ROSE),('vidyā',10,INDIGO),('extended vidyā',16,ELECTRIC)]
    for i,(lab,count,col) in enumerate(levels):
        y=160+i*90;x0=235;x1=1040
        draw_breath_wave(im,x0,x1,y,14+i*5,1+i*.35,t*.3,col,2)
        for j in range(count):
            u=(j+.5)/count;x=lerp(x0,x1,u);yy=y+math.sin(u*2*math.pi*(1+i*.35)+t*.3)*(14+i*5)
            d.ellipse((x-5,yy-5,x+5,yy+5),fill=rgba(col,200))
        d.text((155,y),lab,font=TERM_FONT,fill=col,anchor='mm')
        d.text((1112,y),f'{count} units',font=SMALL_FONT,fill=SILVER,anchor='mm')
    d.text((640,516),'longer formulas require proportionally enlarged cycles of attention and breath',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im);cx,cy=W/2,282
    # nested cycles with reversal nodes
    for i,(r,col) in enumerate([(85,COPPER),(145,ROSE),(210,INDIGO)]):
        pts=orbit_points(cx,cy,r,r*.65,-math.pi/2+i*.16)
        draw_line_glow(im,pts,col,3,90,6)
        for a in [0,math.pi]:
            x=cx+math.cos(a-i*.16)*r;y=cy+math.sin(a-i*.16)*r*.65
            d.ellipse((x-10,y-10,x+10,y+10),outline=rgba(GOLD_LIGHT,210),width=2)
    # pulses jump cycle at reversal nodes
    jump=ease_in_out(t)
    p0=(cx+85,cy);p1=(cx+145,cy);p2=(cx+210,cy)
    for a,b,col,delay in [(p0,p1,ROSE,0),(p1,p2,ELECTRIC,.18)]:
        pts=partial_polyline(bezier(a,(a[0]+20,a[1]-42),(b[0]-20,b[1]-42),b,70),smoothstep(delay,.82,t))
        if len(pts)>1:draw_line_glow(im,pts,col,3,115,7)
    draw_glow(im,(cx,cy),34,PEARL,100,10);d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255))
    d.text((640,506),'reversal points become gates through which one mantra cycle opens into another',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im)
    # breath/mantra proportional grid
    x0,y0,x1,y1=220,150,1060,450
    d.line((x0,y1,x1,y1),fill=rgba(SILVER,105),width=2)
    d.line((x0,y0,x0,y1),fill=rgba(SILVER,105),width=2)
    d.text((640,482),'breath-span',font=SMALL_FONT,fill=SILVER,anchor='mm')
    d.text((154,300),'mantra length',font=SMALL_FONT,fill=SILVER,anchor='mm')
    pts=[]
    for i in range(9):
        u=i/8;x=lerp(x0+40,x1-30,u);y=lerp(y1-30,y0+30,u)
        pts.append((x,y));r=8+i*2
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(mix(COPPER,ELECTRIC,u),190),outline=rgba(PEARL,100),width=1)
        d.text((x+34,y),str(2+i*2),font=TINY_FONT,fill=SILVER,anchor='lm')
    reveal=partial_polyline(pts,ease_in_out(t))
    if len(reveal)>1:draw_line_glow(im,reveal,GOLD_LIGHT,4,130,8)
    d.text((640,516),'mantra duration and respiratory duration scale together as one structured cycle',font=SUB_FONT,fill=SILVER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im);cx,cy=W/2,282
    # closing wheel: breath infinity plus mantra rings
    for i,(r,col,count) in enumerate([(76,GOLD_LIGHT,3),(128,COPPER,6),(184,INDIGO,10),(232,ELECTRIC,16)]):
        d.ellipse((cx-r,cy-r*.66,cx+r,cy+r*.66),outline=rgba(col,145),width=2)
        draw_beads(d,cx,cy,r,r*.66,count,t*.12*(1 if i%2==0 else -1),col,r=5)
    # central breath lemniscate
    pts=[]
    for i in range(180):
        a=i*2*math.pi/179
        x=cx+math.sin(a)*108;y=cy+math.sin(a)*math.cos(a)*78
        pts.append((x,y))
    draw_line_glow(im,pts,mix(COPPER,TEAL,.5),4,120,7)
    draw_glow(im,(cx,cy),42,PEARL,125,12);d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'हं',font=DEVA_SMALL,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,506),'the arising of cycles resolves into a single breath–mantra cosmogram',font=SUB_FONT,fill=SILVER,anchor='mm')

SCENES=[
Scene('co01','The Arising of the Cycles','An overview of mantra orbits expanding through breath.','Cakrodaya','Mantra cycles arise in nested proportion to respiratory duration.','overview_cycles',['overview','mantra','breath'],'overview','nested orbital cycles',sc01),
Scene('co02','Breath as Carrier','The respiratory waveform bears articulated mantra.','Prāṇa–mantra','Speech units move upon the rhythm of breath.','breath_carrier',['breath','carrier','syllables'],'process','wave with mantra beads',sc02),
Scene('co03','The Seed Cycle','A compact bīja occupies one short breath-span.','Bīja-cakra','The smallest formula is held within a minimal respiratory orbit.','seed_cycle',['seed','short cycle'],'cycle','seed orbit',sc03),
Scene('co04','Expanding Formula','Longer formulas require larger containing cycles.','Mantra-vṛddhi','Mantra length and breath capacity expand together.','expanding_orbits',['formula','expansion'],'cycle','multi-orbit expansion',sc04),
Scene('co05','From Bīja to Vidyā','Increasing formula-length produces increasing temporal architecture.','Mantra–Vidyā','Seed, mantra, and vidyā occupy progressively enlarged cycles.','length_ladder',['vidya','length','breath'],'process','wave ladder',sc05),
Scene('co06','Reversal Gates','Cycle-boundaries open through respiratory turning points.','Sandhi','Mantra cycles connect through breath reversal thresholds.','reversal_gates',['threshold','transition'],'process','nested gates',sc06),
Scene('co07','Proportional Law','Breath-span and mantra-length scale as one system.','Māna','The chapter’s architecture is rendered as proportional growth.','proportional_map',['proportion','duration'],'overview','rising relation graph',sc07),
Scene('co08','The Cakrodaya Seal','Breath and mantra gather into one generative wheel.','Cakrodaya-cakra','The full system resolves into a closing breath–mantra cosmogram.','closing_seal',['seal','summary'],'seal','orbital lemniscate seal',sc08),
]


def render_scene(scene):
    sdir=FRAMES_ROOT/scene.id;sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000:continue
            t=i/max(1,NFRAMES-1);im=ground(SEED+hash(scene.id)%10000+i);border(im);dust(im,SEED+i,62);scene.draw_fn(im,t);footer(im,scene.title,scene.subtitle,scene.term);im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg';thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),color=NIGHT)
    for idx,im in enumerate(thumbs):sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Tantrāloka — Cakrodaya: The Arising of Mantra Cycles','source_basis':'Tantrāloka Chapter 7: mantra and vidyā cycles linked proportionally to the rhythm and length of breath.','style':{'family':'orbital mantra cosmography','background':'deep ink-blue field','accent':'pearl, copper, electric indigo, gold','materials':['phonemic beads','respiratory waves','orbital cycles','reversal gates','lemniscate seal']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['co01','co07'],'breath_mantra':['co02','co03','co04','co05'],'transitions':['co06'],'seal':['co08']},'reusability_notes':{'co01':'Introduce cakrodaya or nested mantra cycles.','co02':'Use for mantra carried by breath.','co03':'Use for bīja, seed-formula, or compact cycles.','co04':'Use for expanding formula length and capacity.','co05':'Use for bīja-to-vidyā progression.','co06':'Use for reversal thresholds and cycle transitions.','co07':'Use for proportional relations between formula and breath.','co08':'Use as a closing breath-mantra seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Cakrodaya / The Arising of Mantra Cycles\n\n## Aim\nVisualize Tantrāloka Chapter 7 as a system in which mantra and vidyā cycles of progressively greater length are accommodated within proportionally enlarged respiratory cycles.\n\n## Core Structure\n- breath supplies temporal capacity;\n- bīja occupies a compact cycle;\n- longer mantra requires a larger orbit;\n- vidyā expands the architecture further;\n- respiratory reversal points connect cycles;\n- mantra-length and breath-span form a proportional system.\n\n## Visual Rules\n- Do not make this a generic mala-bead animation.\n- Breath and formula must visibly constrain one another.\n- Different cycle lengths should produce different spatial architectures.\n- Reversal nodes should function as gates.\n- The closing seal must integrate respiratory rhythm and mantra orbit.\n\n## Style\nDeep ink-blue field, pearl source-light, copper phonemic charge, electric indigo extended cycles, and gold threshold accents.\n'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Cakrodaya Pack\n\n## Differentiation\nThis pack moves from axial breath diagrams into orbital temporal architecture. Breath is no longer a single horizontal vector but a container whose capacity determines the size of mantra cycles.\n\n## New Motifs\n1. mantra beads on breath waves\n2. compact bīja orbit\n3. nested expanding formula-rings\n4. bīja-to-vidyā temporal ladder\n5. respiratory reversal gates\n6. proportional breath/mantra graph\n7. orbital lemniscate closing seal\n\n## New Relationships\n- breath-span ↔ formula length\n- seed mantra → extended mantra → vidyā\n- respiratory reversal → cycle transition\n- temporal capacity → phonemic accommodation\n\n## Material Vocabulary\nDeep ink, pearl light, oxidized copper, electric indigo, orbital beads, luminous respiratory traces.\n\n## Distinct Closing Seal\nA nested mantra wheel surrounding a central breath-lemniscate.\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — Cakrodaya Pack\n\nIncluded: combined MP4, eight scene clips, renderer, contact sheet, manifests, dossier, style evolution, validation.\n\n- Resolution: {W}x{H}\n- FPS: {FPS}\n- Scenes: {len(SCENES)}\n- Duration: {len(SCENES)*DURATION:.1f}s\n\nRun: `python render_pack.py`\n'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'cakrodaya_mantra_cycles_animation.mp4';probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)]);(ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))
def make_zip():
    zpath=ROOT/'cakrodaya_mantra_cycles_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['cakrodaya_mantra_cycles_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):zf.write(mp4,arcname=f'scenes/{mp4.name}')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True);SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:print('Rendering',sc.id,sc.title,flush=True);render_scene(sc)
    concat=ROOT/'concat_list.txt';concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'cakrodaya_mantra_cycles_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet();write_metadata();validate_outputs();make_zip()
if __name__=='__main__':render_all()
