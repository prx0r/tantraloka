#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=26262

DARK_LAB=(14,12,14); WARM_DARK=(20,18,18); CRUCIBLE=(22,18,16)
LEAD=(55,50,55); QUICKSILVER=(180,190,200); MOLTEN=(220,140,50)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); EMERALD=(60,140,100)
CRIMSON=(154,44,58); ROSE_GOLD=(210,170,145); SILVER=(196,204,222)
WHITE=(252,250,246); PEARL=(246,243,236); SLATE=(90,100,120)
MIST=(160,172,192); TEAL=(92,146,148); FLAME=(210,120,40)
AMBER=(200,150,60); VIOLET=(120,104,168); PALE_GOLD=(252,244,226)
INK=(34,38,44); UMBER=(78,64,50)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30)
SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21)
SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3],int(a))

def ground(seed,bg,glow_col=None,intensity=0.5):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*2.8*intensity+fine[...,None]*0.8*intensity
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*16,0,24)[...,None]
    if glow_col:
        g=np.exp(-(((xx-W/2)/(W*.28))**2+((yy-H*.38)/(H*.24))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.035
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
    if i+1<len(points): A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out
def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts
def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)
def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(AMBER,GOLD,.3),80),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(GOLD,FLAME,.4),50),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,mix(GOLD,AMBER,.5))
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,10,14,200),outline=rgba(mix(GOLD,FLAME,.4),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,AMBER,.5))
def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(mix(QUICKSILVER,AMBER,.3),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def s01_what_survives(im,t):
    im.paste(ground(SEED+1,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'some parts of you will survive almost anything',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'they have not yet met the right fire',font=TERM_FONT,fill=mix(MOLTEN,GOLD_LIGHT,.6),anchor='mm')
    prog=ease(t)
    # Kernel at center that resists
    glow(im,(cx,cy+20),15,LEAD,80,10)
    d.ellipse((cx-25,cy-5,cx+25,cy+45),fill=rgba(LEAD,120),outline=rgba(mix(LEAD,GOLD,.2),160),width=2)
    # Outer layers burning away
    for i in range(5):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        r=40+i*25
        d.ellipse((cx-r,cy+20-r*0.6,cx+r,cy+20+r*0.6),outline=rgba(mix(LEAD,MOLTEN,i/4),int(100*p)),width=1)
    # Flame licks at kernel
    if prog>0.4:
        p=clamp((prog-0.4)*1.5)
        pts=[(cx-15,cy-8),(cx-25,cy-30),(cx,cy-15),(cx+20,cy-35),(cx+15,cy-5)]
        d.polygon(pts,fill=rgba(mix(MOLTEN,FLAME,.5),int(40*p)),outline=rgba(mix(MOLTEN,AMBER,.5),int(120*p)))
    d.text((640,505),'the impure material had not yet met the right fire',font=SUB_FONT,fill=MIST,anchor='mm')

def s02_nigredo(im,t):
    im.paste(ground(SEED+2,DARK_LAB,CRIMSON,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'nigredo — the blackening',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the beautiful surface collapses into confusion and decay',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Structure breaking down
    for i in range(3):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        r=80-i*20
        d.ellipse((cx-r,cy+10-r*0.6,cx+r,cy+10+r*0.6),outline=rgba(mix(LEAD,CRIMSON,i/2),int(140*p)),width=2)
        d.ellipse((cx-r+5,cy+15-r*0.5,cx+r-5,cy+15+r*0.5),outline=rgba(mix(CRIMSON,SLATE,i/2),int(80*p)),width=1)
    # Cracks
    for i in range(6):
        a=i*2*math.pi/6; r=lerp(20,80,prog)
        x=cx+math.cos(a)*r; y=cy+10+math.sin(a)*r*0.6
        if prog>0.3+i*0.05:
            d.line((cx,cy+10,int(x),int(y)),fill=rgba(SLATE,int(100*prog)),width=1)
    glow(im,(cx,cy+10),10,SLATE,50,10)
    d.text((640,505),'what looked unified reveals incompatible substances hidden inside it',font=SUB_FONT,fill=MIST,anchor='mm')

def s03_small_deaths(im,t):
    im.paste(ground(SEED+3,WARM_DARK,SLATE,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'many small deaths before transformation',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the material dissolves and re-forms repeatedly',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Repeated dissolution-reformation cycles
    for i in range(6):
        y=140+i*40
        # Wave of dissolving
        phase=t*3+i*0.8
        amp=20*math.sin(phase)*prog
        col=mix(LEAD,QUICKSILVER,0.5+0.5*math.sin(phase))
        d.line((220,y+amp,1060,y+amp*0.3),fill=rgba(col,int(120*prog)),width=2)
        d.line((220,y-5+amp,1060,y-5+amp*0.3),fill=rgba(mix(col,MOLTEN,.3),int(60*prog)),width=1)
    # Dissolving particles
    for i in range(20):
        u=i/19; x=lerp(200,1080,u); y=cy+40+20*math.sin(u*6+t*2)*prog
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(mix(SLATE,QUICKSILVER,u),int(80*prog)))
    d.text((640,505),'the vessel was on the furnace — the alchemist was inside another vessel',font=SUB_FONT,fill=MIST,anchor='mm')

def s04_false_gold(im,t):
    im.paste(ground(SEED+4,WARM_DARK,GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'false gold',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the part that learns spiritual language while remaining exactly as it was',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Attractive surface
    d.ellipse((cx-90,cy+10-60,cx+90,cy+10+60),outline=rgba(mix(GOLD,AMBER,.4),int(180*prog)),width=3)
    d.ellipse((cx-80,cy+15-50,cx+80,cy+15+50),fill=rgba(mix(GOLD,AMBER,.2),int(30*prog)))
    # Cracks revealing darker interior
    for i in range(5):
        p=clamp(prog*1.5-i*0.1)
        if p<=0: continue
        a=-0.5+i*0.25; x=cx+math.sin(a)*80; y=cy+10+math.cos(abs(a))*50
        d.line((int(x),int(y),int(x+math.sin(a)*20),int(y+math.cos(abs(a))*15)),fill=rgba(LEAD,int(120*p)),width=2)
    glow(im,(cx,cy+10),15,LEAD,int(40*prog),8)
    d.text((cx,260),'the surface gleams — but the core has not changed',font=TINY_FONT,fill=MIST,anchor='mm')
    d.text((640,505),'they become more sophisticated while remaining exactly what they were',font=SUB_FONT,fill=MIST,anchor='mm')

def s05_tria_prima(im,t):
    im.paste(ground(SEED+5,DARK_LAB,QUICKSILVER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'mercury — sulfur — salt',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'body, soul, and spirit — one thing, equally present',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    cols=[QUICKSILVER,AMBER,LEAD]; labels=['mercury','sulphur','salt']; glows=[SILVER,FLAME,SLATE]
    for i in range(3):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*110; y=cy+math.sin(a)*110*0.65
        glow(im,(x,y),15,glows[i],int(50*p),10)
        d.ellipse((x-35,y-25,x+35,y+25),outline=rgba(cols[i],int(170*p)),fill=rgba(cols[i],int(15*p)),width=2)
        d.text((x,y+45),labels[i],font=SMALL_FONT,fill=rgba(cols[i],int(190*p)),anchor='mm')
    glow(im,(cx,cy),18,mix(GOLD_LIGHT,WHITE,.5),int(80*prog),12)
    d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=rgba(WHITE,int(200*prog)))
    d.text((640,505),'body, soul, and spirit — equally present, equally transformed',font=SUB_FONT,fill=MIST,anchor='mm')

def s06_right_fire(im,t):
    im.paste(ground(SEED+6,DARK_LAB,MOLTEN,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the right fire',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'it knows what to burn and what to leave',font=TERM_FONT,fill=mix(MOLTEN,GOLD,.7),anchor='mm')
    prog=ease(t)
    # Crucible vessel
    d.arc((cx-100,cy-40,cx+100,cy+60),200,340,fill=rgba(SLATE,int(160*prog)),width=3)
    d.arc((cx-100,cy-40,cx+100,cy+60),20,160,fill=rgba(SLATE,int(80*prog)),width=2)
    d.line((cx-100,cy+10,cx-80,cy+60),fill=rgba(SLATE,int(160*prog)),width=3)
    d.line((cx+100,cy+10,cx+80,cy+60),fill=rgba(SLATE,int(160*prog)),width=3)
    # Fire inside that discriminates
    if prog>0.2:
        p=clamp((prog-0.2)*1.5)
        flame_pts=[(cx,cy-20-30*p),(cx-20,cy-10-15*p),(cx-8,cy+5),(cx+12,cy+3),(cx+22,cy-10-10*p)]
        d.polygon(flame_pts,fill=rgba(mix(MOLTEN,FLAME,.5),int(50*p)),outline=rgba(mix(MOLTEN,AMBER,.7),int(160*p)))
        glow(im,(cx,cy-10),int(10+20*p),mix(MOLTEN,GOLD_LIGHT,.5),int(80*p),14)
    d.text((640,505),'the fire does not hate what it burns — it is completing a transformation',font=SUB_FONT,fill=MIST,anchor='mm')

def s07_fuel(im,t):
    im.paste(ground(SEED+7,WARM_DARK,AMBER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the dross is not your enemy',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'it is fuel — the fire is not destroying you',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Dross transforming into light
    d.ellipse((cx-80,cy-50,cx+80,cy+50),outline=rgba(mix(LEAD,GOLD,prog),int(160*prog)),width=3)
    for i in range(8):
        a=i*2*math.pi/8+t*0.05
        r_in=30; r_out=lerp(90,60,prog)
        x1=cx+math.cos(a)*r_in; y1=cy+math.sin(a)*r_in*0.6
        x2=cx+math.cos(a)*r_out; y2=cy+math.sin(a)*r_out*0.6
        lineglow(im,[(x1,y1),(x2,y2)],mix(LEAD,GOLD_LIGHT,prog),2,int(60+80*prog),5)
    glow(im,(cx,cy),int(15+25*prog),GOLD_LIGHT,int(80+80*prog),16)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=rgba(WHITE,int(200*prog)))
    d.text((640,505),'the goal is not to remove the dross but to see it as fuel',font=SUB_FONT,fill=MIST,anchor='mm')

def s08_seal(im,t):
    im.paste(ground(SEED+8,DARK_LAB,GOLD,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the fire is not destroying you',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'it is revealing what the fire cannot burn',font=TERM_FONT,fill=mix(GOLD_LIGHT,WHITE,.6),anchor='mm')
    prog=ease(t)
    # Crucible with golden light emerging
    d.arc((cx-110,cy-60,cx+110,cy+40),200,340,fill=rgba(mix(SLATE,GOLD,prog),int(150*prog)),width=3)
    d.arc((cx-110,cy-60,cx+110,cy+40),20,160,fill=rgba(mix(SLATE,GOLD,prog),int(70*prog)),width=2)
    d.line((cx-110,cy-10,cx-90,cy+40),fill=rgba(mix(SLATE,GOLD,prog),int(150*prog)),width=3)
    d.line((cx+110,cy-10,cx+90,cy+40),fill=rgba(mix(SLATE,GOLD,prog),int(150*prog)),width=3)
    # Light emerging from crucible
    glow(im,(cx,cy-30),int(20+50*prog),GOLD_LIGHT,int(120*prog),22)
    d.ellipse((cx-14,cy-44,cx+14,cy-16),fill=rgba(WHITE,int(220*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    # Rays upward
    if prog>0.3:
        p=clamp((prog-0.3)*1.5)
        for i in range(12):
            a=-math.pi/2+(i-6)*0.15
            x=cx+math.cos(a)*100; y=cy-60+math.sin(a)*80
            lineglow(im,[(cx,cy-40),(int(x),int(y))],mix(GOLD_LIGHT,WHITE,.3),2,int(60*p),6)
    d.text((640,505),'some parts of you will survive almost anything — they are what the fire cannot touch',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
    Scene('fi01','What Survives','The kernel that resists change.','Nigredo','','opening',['kernel','resistance','fire'],'opening','lead kernel with flame',6.0,s01_what_survives),
    Scene('fi02','Nigredo','Blackening — the collapse of the surface.','Nigredo','','blackening',['collapse','decay','breakdown'],'blackening','cracking black shell',6.0,s02_nigredo),
    Scene('fi03','Small Deaths','Repeated dissolution and reformation.','Solutio','','dissolution',['dissolution','cycles','death'],'dissolution','oscillating dissolution waves',6.0,s03_small_deaths),
    Scene('fi04','False Gold','The part that learns spiritual language without changing.','Aurum falsum','','false_gold',['false','gold','bypass'],'false_gold','gilded surface with dark core',6.0,s04_false_gold),
    Scene('fi05','Tria Prima','Mercury, sulfur, salt — body, soul, spirit.','Tria prima','','structure',['mercury','sulphur','salt'],'structure','three interlocking elements',6.0,s05_tria_prima),
    Scene('fi06','The Right Fire','Fire that knows what to burn.','Ignis','','fire',['fire','discrimination','transformation'],'fire','crucible with discriminating flame',6.0,s06_right_fire),
    Scene('fi07','Fuel','The dross is not the enemy — it is fuel.','Fomes','','fuel',['dross','fuel','integration'],'fuel','dark matter transforming to gold',6.0,s07_fuel),
    Scene('fi08','The Fire Seal','What the fire cannot burn.','Opus','','seal',['seal','fire','survival'],'seal','crucible with golden radiant emergence',6.0,s08_seal),
]

def render_scene(scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    nframes=int(FPS*scene.duration)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    for i,path in enumerate(expected):
        if path.exists() and path.stat().st_size>1000: continue
        t=i/max(1,nframes-1)
        im=Image.new('RGBA',(W,H),(0,0,0,0))
        scene.draw_fn(im,t)
        dust(im,SEED+hash(scene.id)%10000+i,45)
        border(im); footer(im,scene.title,scene.subtitle,scene.term)
        im.convert('RGB').save(path,quality=94)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(10*sc.duration*0.72):04d}.jpg'
        if not frame.exists(): frame=FRAMES_ROOT/sc.id/'frame_0000.jpg'
        if not frame.exists(): continue
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    rows=(len(thumbs)+3)//4
    sheet=Image.new('RGB',(4*320,rows*180),color=DARK_LAB)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'The Fire Is Not Destroying You',
        'source_basis':'Expansion Essay — the fire is not destroying you, Tier 1 #2.',
        'style':{'family':'alchemical-fire cosmography','background':'dark lab with flame glow','ink':'slate and mist','accent':'molten, quicksilver, amber, gold, lead'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — The Fire Is Not Destroying You

## Aim
Visualize alchemical transformation: the parts of you that survive anything, the nigredo, the false gold, and the fire that knows what to burn.

## Structure
1. The kernel that resists — not yet met the right fire
2. Nigredo — the surface collapses
3. Repeated dissolution and reformation
4. False gold — spiritual bypassing
5. Tria prima — mercury, sulfur, salt
6. The right fire — discrimination
7. The dross as fuel
8. What the fire cannot burn

## Visual rules
- Dark lab palette — lead, quicksilver, molten, amber, gold.
- Crucible and vessel shapes.
- Flame as discriminating force.
- The dross transforms into gold — not removed but integrated.
- No figures — crucibles, kernels, and flames only.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — The Fire Is Not Destroying You\n\n## Differentiation\nThis pack uses alchemical crucible and flame imagery — distinct from the mirror/gaze imagery of the God Looks Through Your Face pack.\n\n## New symbols\n1. lead kernel with flame\n2. cracking black shell\n3. oscillating dissolution waves\n4. gilded surface with dark core\n5. three interlocking elements\n6. crucible with discriminating flame\n7. dark matter transforming to gold\n8. crucible with golden radiant emergence\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# The Fire Is Not Destroying You — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'fire_not_destroying_animation.mp4'
    if combined.exists():
        probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
        (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'fire_not_destroying_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['fire_not_destroying_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'fire_not_destroying_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
