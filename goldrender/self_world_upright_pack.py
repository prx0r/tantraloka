#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=24242

PARCHMENT=(244,240,232); PARCHMENT_LIGHT=(250,247,240); INK=(34,38,44)
UMBER=(78,64,50); GOLD=(206,166,88); GOLD_LIGHT=(244,214,138)
CRIMSON=(154,46,60); ROSE=(192,108,130); TEAL=(92,146,148)
SLATE=(106,118,138); MIST=(176,186,200); WHITE=(252,250,246)
SILVER=(216,222,232); REED=(182,160,130); REED_DARK=(140,118,88)
VIOLET=(120,104,168); NIGHT=(14,14,22); SKY_BLUE=(140,170,200)
PALE_GOLD=(252,244,226); WARM_GLOW=(236,226,206)

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

def ground(seed,bg=PARCHMENT,glow_col=None):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*3.0+fine[...,None]*0.85
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*5,0,14)[...,None]*0.6
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
    d.rectangle((28,28,W-28,H-28),outline=rgba(UMBER,100),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,70),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,55),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=UMBER)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=CRIMSON)
def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def s01_reeds(im,t):
    im.paste(ground(SEED+1,PARCHMENT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,80),'place two bundles of reeds together',font=TERM_FONT,fill=INK,anchor='mm')
    # Left bundle leaning right
    lx0,ly0=300,440; lx1,ly1=cx,140
    pts=[]
    reeds_l=8
    for i in range(reeds_l):
        frac=i/(reeds_l-1)
        x=lerp(lx0,lx1,frac); y=lerp(ly0,ly1,frac)
        sway=30*math.sin(frac*math.pi)
        pts.append((x+sway,y))
    reveal=partial(pts,ease(t))
    if len(reveal)>1: lineglow(im,reveal,REED,3,120,6)
    # Individual reed lines
    for ri in range(12):
        off=(ri-5.5)*10
        pts2=[]
        for i in range(10):
            u=i/9
            x=lerp(lx0+off,lx1+off*0.3,u); y=lerp(ly0,ly1,u)
            pts2.append((x,y))
        re=partial(pts2,ease(t))
        if len(re)>1: d.line(re,fill=rgba(REED_DARK,100),width=1)
    # Right bundle leaning left
    rx0,ry0=980,440; rx1,ry1=cx,140
    for ri in range(12):
        off=(ri-5.5)*10
        pts3=[]
        for i in range(10):
            u=i/9
            x=lerp(rx0+off,rx1+off*0.3,u); y=lerp(ry0,ry1,u)
            pts3.append((x,y))
        re=partial(pts3,ease(t))
        if len(re)>1: d.line(re,fill=rgba(REED_DARK,100),width=1)
    glow(im,(cx,130),30,GOLD_LIGHT,60,14)
    d.text((640,505),'neither stands alone',font=SUB_FONT,fill=UMBER,anchor='mm')

def s02_braid(im,t):
    im.paste(ground(SEED+2,PARCHMENT,(TEAL[0],TEAL[1],TEAL[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'consciousness — name-and-form',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'each conditions the other',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    pts_self=[]; pts_world=[]
    for i in range(120):
        u=i/119; y=150+u*300
        x_self=cx-40+math.sin(u*math.pi*4)*30*(1+0.3*math.sin(u*math.pi))
        x_world=cx+40+math.sin(u*math.pi*4+math.pi)*30*(1+0.3*math.sin(u*math.pi))
        if u<=prog:
            pts_self.append((x_self,y))
            pts_world.append((x_world,y))
    if len(pts_self)>1: lineglow(im,pts_self,ROSE,4,130,7)
    if len(pts_world)>1: lineglow(im,pts_world,TEAL,4,130,7)
    # Labels
    d.text((cx-80,445),'consciousness',font=SMALL_FONT,fill=ROSE,anchor='mm')
    d.text((cx+80,445),'name-and-form',font=SMALL_FONT,fill=TEAL,anchor='mm')
    # Connecting arcs
    for i in range(4):
        y=180+i*75
        lineglow(im,[(cx-8,y),(cx+8,y)],mix(ROSE,TEAL,.5),1,50,3)
    d.text((640,505),'the two bundles lean — the relation produces the field',font=SUB_FONT,fill=UMBER,anchor='mm')

def s03_enaction(im,t):
    im.paste(ground(SEED+3,PARCHMENT_LIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    d.text((cx,80),'perception is not passive reception',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'it is skillful engagement',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.5),anchor='mm')
    prog=ease(t)
    # Circle
    r=130
    arc_pts=[]
    for i in range(90):
        a=i/89*math.pi; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r
        arc_pts.append((x,y))
    reveal=partial(arc_pts,prog)
    if len(reveal)>1: lineglow(im,reveal,GOLD,3,110,6)
    arc_pts2=[]
    for i in range(90):
        a=math.pi+i/89*math.pi; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r
        arc_pts2.append((x,y))
    reveal2=partial(arc_pts2,clamp(prog-0.3)*1.5)
    if len(reveal2)>1: lineglow(im,reveal2,TEAL,3,110,6)
    # Eye icon (left)
    d.arc((cx-r-40,cy-18,cx-r+20,cy+18),200,340,fill=rgba(UMBER,190),width=2)
    d.arc((cx-r-40,cy-18,cx-r+20,cy+18),20,160,fill=rgba(UMBER,150),width=2)
    d.ellipse((cx-r-18,cy-6,cx-r-2,cy+6),fill=rgba(UMBER,200))
    # Hand icon (right)
    d.ellipse((cx+r-20,cy-12,cx+r+20,cy+28),outline=rgba(UMBER,180),width=2)
    d.line((cx+r-10,cy-8,cx+r-10,cy-30),fill=rgba(UMBER,170),width=3)
    d.line((cx+r-2,cy-8,cx+r-2,cy-30),fill=rgba(UMBER,170),width=3)
    d.line((cx+r+6,cy-8,cx+r+6,cy-30),fill=rgba(UMBER,170),width=3)
    d.line((cx+r+14,cy-8,cx+r+14,cy-30),fill=rgba(UMBER,170),width=3)
    # Arrows
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        x0=cx+math.cos(0.2)*r; y0=cy+math.sin(0.2)*r
        x1=x0+50; y1=y0-30
        lineglow(im,[(x0,y0),(int(x1),int(y1))],CRIMSON,2,int(120*p),5)
        d.text((cx+r+40,cy-r+10),'action',font=TINY_FONT,fill=CRIMSON,anchor='mm')
    d.text((cx,420),'perception ⇄ action',font=TERM_FONT,fill=GOLD,anchor='mm')
    d.text((640,505),'the organism discovers a world through possible action',font=SUB_FONT,fill=UMBER,anchor='mm')

def s04_mirrors(im,t):
    im.paste(ground(SEED+4,PARCHMENT,(SILVER[0],SILVER[1],SILVER[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'self-model — world-model',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'each stabilizes the other',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    # Mirrors
    d.rounded_rectangle((250,160,370,400),radius=16,outline=rgba(ROSE,int(180*prog)),width=3)
    d.rounded_rectangle((910,160,1030,400),radius=16,outline=rgba(TEAL,int(180*prog)),width=3)
    d.text((310,420),'self-model',font=SMALL_FONT,fill=ROSE,anchor='mm')
    d.text((970,420),'world-model',font=SMALL_FONT,fill=TEAL,anchor='mm')
    # Infinite regress lines between mirrors
    for i in range(8):
        frac=i/7; y=lerp(190,370,frac)
        p=clamp(prog*1.5-frac*0.3)
        if p<=0: continue
        x1=lerp(370,400,frac); x2=lerp(910,880,frac)
        d.line((x1,y,x2,y),fill=rgba(SILVER,int(140*p)),width=1)
    # Shrinking recursive mirrors inside
    for i in range(3):
        p=clamp(prog*1.8-i*0.25)
        if p<=0: continue
        s=1-i*0.25
        cw=int(120*s); ch=int(240*s)
        d.rounded_rectangle((int(640-cw*s),int(260-ch*s),int(640+cw*s),int(260+ch*s)),radius=int(12*s),outline=rgba(mix(ROSE,TEAL,i/2),int(100*p)),width=1)
    glow(im,(310,280),20,ROSE,60,10)
    glow(im,(970,280),20,TEAL,60,10)
    d.text((640,505),'each pole confirms the other — the loop becomes stable',font=SUB_FONT,fill=UMBER,anchor='mm')

def s05_vortex(im,t):
    im.paste(ground(SEED+5,NIGHT,(CRIMSON[0],CRIMSON[1],CRIMSON[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'grasping hardens the loop',font=TERM_FONT,fill=PALE_GOLD,anchor='mm')
    d.text((cx,105),'the vortex tightens around itself',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Spiral tightening
    spirals=2+3*prog
    pts=[]
    for i in range(200):
        u=i/199; a=u*spirals*2*math.pi; r=10+u*160*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.65
        if u<=prog: pts.append((x,y))
    if len(pts)>1: lineglow(im,pts,mix(CRIMSON,GOLD,.3),3,130,8)
    # Particles spiraling
    for i in range(20):
        u=clamp(prog*i/20); a=u*spirals*2*math.pi+i; r=12+u*150*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.65
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(CRIMSON,GOLD_LIGHT,i/20),160))
    glow(im,(cx,cy),20+30*prog,CRIMSON,int(80+40*prog),14)
    d.text((640,505),'the prediction gains evidence because it creates its own conditions',font=SUB_FONT,fill=MIST,anchor='mm')

def s06_loosening(im,t):
    im.paste(ground(SEED+6,NIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'practice works at the loop',font=TERM_FONT,fill=PALE_GOLD,anchor='mm')
    d.text((cx,105),'not by attacking one pole',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Expanding unwinding spiral
    spirals=5-2*prog
    pts=[]
    for i in range(200):
        u=i/199; a=u*spirals*2*math.pi; r=10+u*120+40*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.65
        if u<=prog: pts.append((x,y))
    if len(pts)>1: lineglow(im,pts,mix(GOLD,TEAL,.4),3,120,7)
    # Light descending
    if prog>0.3:
        p=clamp((prog-0.3)*1.5)
        pts_beam=[(cx,cy-150),(cx,cy-30)]
        lineglow(im,pts_beam,GOLD_LIGHT,5,int(120*p),12)
        glow(im,(cx,cy),int(20+40*p),GOLD_LIGHT,int(100*p),16)
    # Particles expanding outward
    for i in range(15):
        a=i*2*math.pi/15; r=60+40*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.65
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD_LIGHT,TEAL,i/15),120))
    d.text((640,505),'no single intervention controls the whole vortex',font=SUB_FONT,fill=MIST,anchor='mm')

def s07_ground(im,t):
    im.paste(ground(SEED+7,PARCHMENT,(VIOLET[0],VIOLET[1],VIOLET[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'one field — two movements',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'both poles appear within the same awareness',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    # Two ripple points
    for side in [-1,1]:
        x_center=cx+side*120
        for i in range(4):
            r=20+i*40*prog
            alpha=int(100*(1-i/4)*prog)
            if alpha<5: continue
            d.ellipse((x_center-r,cy-60-r*0.5,x_center+r,cy-60+r*0.5),outline=rgba(mix(VIOLET,SILVER,i/3),alpha),width=1)
    # Ripples overlapping
    for r in [20,60,100,140]:
        d.ellipse((cx-r,cy-60-r*0.5,cx+r,cy-60+r*0.5),outline=rgba(GOLD,60-int(r/5)),width=1)
    glow(im,(cx,cy-60),40,GOLD_LIGHT,80,18)
    d.ellipse((cx-10,cy-70,cx+10,cy-50),fill=rgba(WHITE,200))
    d.text((640,505),'the dependence becomes visible — the claim of ownership loses precision',font=SUB_FONT,fill=UMBER,anchor='mm')

def s08_seal(im,t):
    im.paste(ground(SEED+8,PARCHMENT_LIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'self and world hold each other upright',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'in light',font=TERM_FONT,fill=GOLD,anchor='mm')
    prog=ease(t)
    # Two bundles becoming light — floating upright
    glow(im,(cx,220),60,GOLD_LIGHT,100,22)
    for side in [-1,1]:
        x_center=cx+side*80
        for i in range(10):
            y=160+i*20
            w=10+5*math.sin(i*0.8+prog)
            alpha=int(80+120*prog)
            d.line((x_center-w,y,x_center+w,y),fill=rgba(mix(GOLD_LIGHT,WHITE,0.3),int(alpha*prog)),width=2)
    # Rising particles
    for i in range(25):
        a=i*2*math.pi/5; r=40+i*8*prog
        x=cx+math.cos(a)*r; y=320-i*6*prog
        if y<cy-80: continue
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(mix(GOLD_LIGHT,WHITE,i/25),int(150*prog)))
    # Light source from below
    if prog>0.3:
        p=clamp((prog-0.3)*1.5)
        lineglow(im,[(cx,450),(cx,300)],GOLD_LIGHT,4,int(100*p),10)
    d.text((640,505),'when one bundle stops demanding the other prove it permanent — the structure becomes light',font=SUB_FONT,fill=UMBER,anchor='mm')

SCENES=[
    Scene('sw01','Two Bundles of Reeds','Neither stands alone.','Dvaya-āśraya','','opening',['reeds','support','nonduality'],'opening','two leaning reed bundles',6.0,s01_reeds),
    Scene('sw02','The Braid','Consciousness and name-and-form interweave.','Viññāṇa-nāmarūpa','','conditioning',['consciousness','name-form','conditioning'],'conditioning','interweaving sine strands',6.0,s02_braid),
    Scene('sw03','The Enacted World','Perception is skillful engagement.','Kriyā-jñāna','','enaction',['perception','action','engagement'],'enaction','action-perception cycle circle',6.0,s03_enaction),
    Scene('sw04','Infinite Mirrors','Self and world stabilize each other.','Atma-jagat-sthiti','','mirroring',['self','world','stabilization'],'mirroring','two facing mirrors with regress',6.0,s04_mirrors),
    Scene('sw05','The Vortex','Grasping hardens the loop.','Saṃsāra-cakra','','vortex',['vortex','grasping','hardening'],'vortex','tightening spiral',6.0,s05_vortex),
    Scene('sw06','Loosening','Practice works at the loop.','Abhyāsa','','practice',['practice','loosening','light'],'practice','unwinding spiral with light',6.0,s06_loosening),
    Scene('sw07','The Ground','Both poles appear in one awareness.','Eka-kṣetra','','ground',['field','awareness','ground'],'ground','two ripples on one pond',6.0,s07_ground),
    Scene('sw08','The Seal','Self and world hold each other upright in light.','Dvaya-jyoti','','seal',['light','seal','freedom'],'seal','luminous upright reeds',6.0,s08_seal),
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
        dust(im,SEED+hash(scene.id)%10000+i,35)
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
    sheet=Image.new('RGB',(4*320,rows*180),color=PARCHMENT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Self and World Hold Each Other Upright',
        'source_basis':'Expansion Essay — self and world hold each other upright, Tier 3.',
        'style':{'family':'reciprocal-arising cosmography','background':'warm parchment','ink':'umber and slate','accent':'reed, rose, teal, gold, crimson'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Self and World Hold Each Other Upright

## Aim
Visualize the co-arising of self and world through Ñāṇananda's image of two bundles of reeds.

## Core arc
1. Two reeds leaning — neither stands alone
2. Consciousness and name-and-form braid together
3. Perception is active engagement, not passive reception
4. Self-model and world-model mirror each other
5. Grasping tightens the loop into a vortex
6. Practice loosens it — light enters
7. Both poles appear within one awareness-field
8. The reeds become light — the structure is revealed as luminous

## Visual rules
- Parchment ground for opening and closing — dark night for the vortex.
- Rose (self) and teal (world) as the two pole colors.
- Gold for the ground of awareness.
- No figures — abstract geometric diagrams only.
- The reeds motif returns at the end transformed into light.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Self and World Pack

## Differentiation
This pack uses reed-bundle, braid, mirror, and vortex imagery distinct from all other packs. The central metaphor — two bundles of reeds — recurs in the opening and closing scenes, visually transformed.

## New symbols
1. two leaning reed bundles (line arrays)
2. interweaving sine wave braids
3. action-perception cycle circle
4. dual facing mirrors with infinite regress
5. tightening archimedean spiral vortex
6. unwinding spiral with descending light
7. two expanding ripples on one pond
8. luminous upright reeds as closing seal
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# Self and World Hold Each Other Upright — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'self_world_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'self_world_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['self_world_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'self_world_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
