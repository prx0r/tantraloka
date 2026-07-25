#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=25252

# Ibn Arabi / mirror palette
NIGHT=(12,12,20); DEEP_GOLD=(80,60,30); GOLD=(206,166,88); GOLD_LIGHT=(244,214,138)
PALE_GOLD=(252,244,226); WHITE=(252,250,246); PEARL=(246,242,236)
CRIMSON=(154,46,60); ROSE=(192,108,130); TEAL=(92,146,148)
SLATE=(106,118,138); MIST=(176,186,200); SILVER=(216,222,232)
PARCHMENT=(244,240,232); UMBER=(78,64,50); VIOLET=(120,104,168)
SKY_BLUE=(140,170,200); INK=(34,38,44)

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

def ground(seed,bg=NIGHT,glow_col=None):
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
    d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,80),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,60),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,SILVER,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(10,10,18,200),outline=rgba(SLATE,45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,55))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def s01_unseen_face(im,t):
    im.paste(ground(SEED+1,NIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,80),'you have never seen your own face directly',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'this is a metaphysical clue',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Mirror outline (oval)
    d.ellipse((cx-120,cy-60,cx+120,cy+100),outline=rgba(SILVER,int(180*prog)),width=3)
    # Reflection surface — lighter center
    d.arc((cx-100,cy-40,cx+100,cy+80),200,340,fill=rgba(SILVER,int(80*prog)),width=2)
    # Gaze lines — converging toward viewer
    for i in range(7):
        a=-0.3+i*0.1; x=cx+math.sin(a)*80; y=cy+20
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        pts=partial([(x,y),(cx-40,cy-90)],p)
        if len(pts)>1: lineglow(im,pts,PEARL,1,int(40*p),3)
    glow(im,(cx,cy+20),20,GOLD_LIGHT,int(60*prog),12)
    d.text((640,505),'the face by which the world knows you is the one face you can never encounter without mediation',font=SUB_FONT,fill=MIST,anchor='mm')

def s02_hidden_treasure(im,t):
    im.paste(ground(SEED+2,NIGHT,(VIOLET[0],VIOLET[1],VIOLET[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'I was a hidden treasure who desired to be known',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'— Ibn Arabi',font=SMALL_FONT,fill=GOLD_LIGHT,anchor='mm')
    prog=ease(t)
    # Hidden treasure as dark center, becoming light
    for i in range(4):
        r=30+i*35*prog
        alpha=int(120*(1-i/4)*prog)
        if alpha<5: continue
        d.ellipse((cx-r,cy-60-r*0.5,cx+r,cy-60+r*0.5),outline=rgba(mix(SLATE,GOLD,i/3),alpha),width=2)
    glow(im,(cx,cy-60),20*(1-prog)+40*prog,GOLD_LIGHT,int(80+80*prog),16)
    d.ellipse((cx-8,cy-68,cx+8,cy-52),fill=rgba(WHITE,int(200*prog)))
    # Rays emanating
    for i in range(10):
        a=i*2*math.pi/10+t*0.05; r=lerp(30,160,prog)
        x=cx+math.cos(a)*r; y=cy-60+math.sin(a)*r*0.6
        col=mix(GOLD_LIGHT,VIOLET,i/9)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,int(120*prog)))
        if prog>0.5:
            pts=partial([(cx,cy-60),(x,y)],clamp((prog-0.5)*2))
            if len(pts)>1: lineglow(im,pts,col,1,int(40*prog),3)
    d.text((640,505),'creation gives the hidden names faces, histories, colors, voices',font=SUB_FONT,fill=MIST,anchor='mm')

def s03_mirror_of_creation(im,t):
    im.paste(ground(SEED+3,PARCHMENT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'the world is a mirror',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'every creature discloses a divine name',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    # Central mirror circle
    d.ellipse((cx-100,cy-60,cx+100,cy+80),outline=rgba(GOLD,int(180*prog)),width=3)
    # Names radiating outward
    names=['The Lion — Power','The Mother — Mercy','The Judge — Justice','The Night — Hiddenness','The Dawn — Unveiling']
    cols=[CRIMSON,ROSE,TEAL,VIOLET,GOLD]
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5
        x=cx+math.cos(a)*200; y=cy-60+math.sin(a)*140
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(cols[i],int(180*p)),width=1)
        d.text((x,y),names[i],font=TINY_FONT,fill=rgba(cols[i],int(200*p)),anchor='mm')
        pts=partial([(cx,cy-5),(cx+math.cos(a)*40,cy-60+math.sin(a)*60),(x-math.cos(a)*30,y-math.sin(a)*20),(x,y)],p)
        if len(pts)>1: lineglow(im,pts,cols[i],1,int(60*p),4)
    d.text((640,505),'no single being can display the whole — infinity appears as difference',font=SUB_FONT,fill=UMBER,anchor='mm')

def s04_the_lens(im,t):
    im.paste(ground(SEED+4,NIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'the finite person is a lens',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,105),'the light is older',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    prog=ease(t)
    # Lens shape
    d.ellipse((cx-60,cy-40,cx+60,cy+40),outline=rgba(SILVER,int(180*prog)),width=2)
    d.arc((cx-60,cy-40,cx+60,cy+40),200,340,fill=rgba(SILVER,int(60*prog)),width=2)
    # Light behind lens
    glow(im,(cx,cy-140),40,GOLD_LIGHT,int(100*prog),20)
    # Beam through lens
    if prog>0.2:
        p=clamp((prog-0.2)*1.5)
        lineglow(im,[(cx,cy-100),(cx,cy-45)],GOLD_LIGHT,5,int(120*p),10)
    # Rays exiting lens
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        for i in range(5):
            a=-0.5+i*0.25; x=cx+math.sin(a)*120; y=cy+40+math.cos(a)*40
            lineglow(im,[(cx+math.sin(a)*40,cy+30),(x,y)],mix(GOLD_LIGHT,TEAL,i/4),2,int(80*p),5)
    d.text((cx,80),'you do not own the qualities passing through you',font=TINY_FONT,fill=MIST,anchor='mm')
    d.text((640,505),'the qualities appearing through you belong to a depth greater than the personality',font=SUB_FONT,fill=MIST,anchor='mm')

def s05_polished_mirror(im,t):
    im.paste(ground(SEED+5,PARCHMENT,(SILVER[0],SILVER[1],SILVER[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'the complete human is a polished mirror',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'transparency does not remove individuality',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    # Mirror surface
    d.rounded_rectangle((cx-110,cy-70,cx+110,cy+80),radius=18,outline=rgba(SILVER,int(190*prog)),width=3)
    # Polishing motion — circular arcs
    for i in range(4):
        r=60+i*15; a=lerp(0,2*math.pi,prog)*i
        d.arc((cx-r,cy-r*0.5,cx+r,cy+r*0.5),int(i*20),int(i*20+180*prog),fill=rgba(mix(SILVER,GOLD_LIGHT,i/4),int(100*prog)),width=2)
    # Light reflection
    glow(im,(cx+30,cy),15,GOLD_LIGHT,int(80*prog),10)
    d.arc((cx+10,cy-20,cx+60,cy+20),180,360,fill=rgba(GOLD_LIGHT,int(120*prog)),width=2)
    # Dust particles falling away
    for i in range(15):
        a=i*2*math.pi/15; r=lerp(80,120,1-prog)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(SLATE,int(80*(1-prog))))
    d.text((640,505),'polishing does not remove individuality — it removes opacity',font=SUB_FONT,fill=UMBER,anchor='mm')

def s06_other_as_mirror(im,t):
    im.paste(ground(SEED+6,NIGHT,(ROSE[0],ROSE[1],ROSE[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,75),'other people reveal the face you cannot see',font=TERM_FONT,fill=PEARL,anchor='mm')
    prog=ease(t)
    # Two faces / mirrors facing each other
    for side in [-1,1]:
        x=cx+side*120
        d.ellipse((x-40,cy-30,x+40,cy+50),outline=rgba(mix(ROSE,TEAL,(side+1)/2),int(180*prog)),width=2)
        # Eye in each
        d.arc((x-18,cy-12,x+6,cy+12),200,340,fill=rgba(PEARL,int(160*prog)),width=2)
        d.arc((x-18,cy-12,x+6,cy+12),20,160,fill=rgba(PEARL,int(100*prog)),width=1)
        d.ellipse((x-6,cy-2,x+2,cy+6),fill=rgba(PEARL,int(200*prog)))
    # Gaze lines between them
    for i in range(5):
        y=lerp(cy-10,cy+30,i/4)
        p=clamp(prog*1.5-i*0.08)
        if p<=0: continue
        lineglow(im,[(cx-80,y),(cx-50,y)],mix(ROSE,TEAL,.3),2,int(80*p),5)
        lineglow(im,[(cx+80,y),(cx+50,y)],mix(TEAL,ROSE,.3),2,int(80*p),5)
    # Central glow — recognition
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        glow(im,(cx,cy+10),25,GOLD_LIGHT,int(100*p),14)
        d.text((cx,cy+60),'a mirror cannot see dust on its own surface',font=TINY_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')
    d.text((640,505),'the beloved reveals a capacity for experience whose depth you did not know',font=SUB_FONT,fill=MIST,anchor='mm')

def s07_remembrance(im,t):
    im.paste(ground(SEED+7,NIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'remembrance',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,105),'the mirror turns toward the light',font=SMALL_FONT,fill=GOLD_LIGHT,anchor='mm')
    prog=ease(t)
    # Mirror tilting
    angle=lerp(0,math.pi/4,prog)
    # Mirror rectangle
    pts=[(cx-60,cy-40),(cx+60,cy-40),(cx+60,cy+40),(cx-60,cy+40)]
    rotated=[(cx+(x-cx)*math.cos(angle)-(y-cy)*math.sin(angle),cy+(x-cx)*math.sin(angle)+(y-cy)*math.cos(angle)) for x,y in pts]
    d.polygon(rotated,outline=rgba(SILVER,int(180*prog)),width=2)
    # Light from above-right reaching mirror
    if prog>0.2:
        p=clamp((prog-0.2)*1.5)
        sx,sy=cx+200,cy-180; mx,my=cx+40*math.cos(angle),cy-40*math.cos(angle)
        lineglow(im,[(sx,sy),(int(mx),int(my))],GOLD_LIGHT,4,int(100*p),10)
        # Reflection beam
        rx,ry=cx-60*math.cos(angle),cy+60*math.cos(angle)
        lineglow(im,[(int(mx),int(my)),(int(rx),int(ry+200))],PEARL,2,int(60*p),8)
    # Name repetition — fading text
    if prog>0.4:
        p=clamp((prog-0.4)*2)
        for i in range(5):
            y=cy+80+i*25; a=lerp(250,50,p)
            if a<20: continue
            d.text((cx-100,y),'huwa — huwa — huwa',font=TINY_FONT,fill=rgba(GOLD_LIGHT,int(a)),anchor='lm')
    d.text((640,505),'remembrance introduces another center — the name repeated until it no longer feels like an object',font=SUB_FONT,fill=MIST,anchor='mm')

def s08_the_gaze(im,t):
    im.paste(ground(SEED+8,NIGHT,(GOLD[0],GOLD[1],GOLD[2])),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,70),'god looks through your face',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,100),'the light does not cease because the reflection is imperfect',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Face outlined as two mirrored curves becoming a single mandala
    for side in [-1,1]:
        # Face outline
        pts=[]
        for i in range(20):
            u=i/19; y=cy-80+u*160
            x=cx+side*(20+60*u*(1-u))
            pts.append((x,y))
        reveal=partial(pts,prog)
        if len(reveal)>1: lineglow(im,reveal,mix(GOLD_LIGHT,PEARL,.3),2,int(120*prog),6)
    # Eye in the center (third eye)
    glow(im,(cx,cy),30,GOLD_LIGHT,int(150*prog),18)
    d.arc((cx-25,cy-12,cx+5,cy+12),200,340,fill=rgba(PEARL,int(200*prog)),width=2)
    d.arc((cx-25,cy-12,cx+5,cy+12),20,160,fill=rgba(PEARL,int(120*prog)),width=1)
    d.ellipse((cx-8,cy-3,cx+2,cy+5),fill=rgba(PEARL,int(220*prog)))
    # Light entering and leaving
    if prog>0.3:
        p=clamp((prog-0.3)*1.5)
        lineglow(im,[(cx,cy-140),(cx,cy-30)],GOLD_LIGHT,5,int(120*p),12)
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        for i in range(8):
            a=i*2*math.pi/8; r=80+40*p
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,PEARL,i/8),int(150*p)))
    d.text((640,505),'what might become visible if, for one moment, you stopped standing in front of the mirror?',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
    Scene('gf01','The Unseen Face','You have never seen your own face directly.','Wajh','','opening',['face','mirror','metaphysics'],'opening','oval mirror with gaze lines',6.0,s01_unseen_face),
    Scene('gf02','Hidden Treasure','I was a hidden treasure who desired to be known.','Kanz','','treasure',['hidden','treasure','manifestation'],'treasure','dark center radiating light',6.0,s02_hidden_treasure),
    Scene('gf03','Mirror of Creation','Every creature discloses a divine name.','Tajallī','','creation',['mirror','creation','names'],'creation','central mirror with radiating name-nodes',6.0,s03_mirror_of_creation),
    Scene('gf04','The Lens','The finite person is a lens.','Qābil','','lens',['lens','light','transmission'],'lens','lens shape with beam and dispersion',6.0,s04_the_lens),
    Scene('gf05','The Polished Mirror','Transparency without removal of individuality.','Ṣaqal','','polishing',['polish','mirror','transparency'],'polishing','rounded mirror with polishing arcs',6.0,s05_polished_mirror),
    Scene('gf06','The Other as Mirror','Other people reveal the face you cannot see.','Akhar','','relation',['other','mirror','love'],'relation','two facing faces with gaze between',6.0,s06_other_as_mirror),
    Scene('gf07','Remembrance','The mirror turns toward the light.','Dhikr','','practice',['remembrance','turning','light'],'practice','tilted mirror receiving light beam',6.0,s07_remembrance),
    Scene('gf08','The Gaze','God looks through your face.','Baṣar','','seal',['gaze','face','divine'],'seal','luminous face-mandala with central eye',6.0,s08_the_gaze),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'God Looks Through Your Face',
        'source_basis':'Expansion Essay — god looks through your face, Tier 1 #1.',
        'style':{'family':'mirror-theophany cosmography','background':'deep night with gold radiance','ink':'silver and mist','accent':'gold, silver, rose, teal, violet'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — God Looks Through Your Face

## Aim
Visualize Ibn Arabi's doctrine of the mirror: the hidden treasure desiring to be known, creation as disclosure, the human as polished mirror.

## Structure
1. You've never seen your own face — metaphysical clue
2. Hidden treasure desiring to be known
3. The world as mirror for divine names
4. The finite person as lens, not source
5. The polished mirror — transparency without removal
6. The other as mirror for self-knowledge
7. Remembrance — turning toward the light
8. God looks through your face

## Visual rules
- Night fields with gold radiance for the divine source.
- Mirror and lens shapes as primary motifs.
- Silver for mirrors, gold for light, rose/teal for the relational poles.
- No anthropomorphic faces — abstract oval face-icons only.
- The closing seal reveals the face as a luminous mandala.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — God Looks Through Your Face

## Differentiation
This pack uses mirror, lens, and gaze imagery — reflective surfaces, light beams, facing ovals — distinct from the reed-bundle motifs of the Self and World pack.

## New symbols
1. oval mirror with gaze lines
2. dark center radiating light (hidden treasure)
3. central mirror with radiating name-nodes
4. lens shape with beam and dispersion
5. rounded mirror with polishing arcs
6. two facing faces with gaze between
7. tilted mirror receiving light beam
8. luminous face-mandala with central eye
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# God Looks Through Your Face — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'god_looks_through_your_face_animation.mp4'
    if combined.exists():
        probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
        (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'god_looks_through_your_face_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['god_looks_through_your_face_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'god_looks_through_your_face_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
