#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=14140

DEEP_GOLD=(18,16,20); WARM_DARK=(22,20,22); DEEP=(14,14,22)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); ROSE_GOLD=(210,170,145)
ROSE_GOLD_LIGHT=(225,200,180); MIRROR=(215,222,235); SILVER=(196,204,222)
PEARL=(246,243,236); WHITE=(252,250,246); TEAL=(92,146,148)
LAVENDER=(170,156,200); SLATE=(90,100,120); MIST=(160,172,192)
CRIMSON=(154,44,58); CORAL=(206,108,100)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA='/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30)
SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21)
SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)
DEVA_MED=ImageFont.truetype(FONT_DEVA,26)

def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[
    :3,
    :3,
],int(a))

def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def draw_glow(im,xy,radius,color,alpha=145,blur=16):
    gl=layer(); d=ImageDraw.Draw(gl); x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))

def draw_line_glow(im,pts,color,width=3,alpha=145,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def partial_polyline(points,amount):
    amount=clamp(amount)
    if amount<=0: return []
    if amount>=1: return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx; out=list(points[:idx+1])
    if idx+1<len(points): a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def arc_points(cx,cy,rx,ry,a0,a1,n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx,cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]

def draw_rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        d.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    d.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(ROSE_GOLD,GOLD,.5),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(ROSE_GOLD,GOLD,.3),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(14,12,18,200),outline=rgba(mix(ROSE_GOLD,GOLD,.3),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(mix(ROSE_GOLD,GOLD,.5),SILVER,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def ibn_ground(seed,bg,glow_col,intensity=0.5):
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
        g=np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.38)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.035
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,ROSE_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,105),'what if god needs you',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,135),'as much as you need god?',font=TERM_FONT,fill=ROSE_GOLD,anchor='mm')
    prog=ease_in_out(t)
    r=140
    d.arc((cx-r,cy-r,cx+r,cy+r),180,360,fill=rgba(ROSE_GOLD,120),width=3)
    d.arc((cx-r,cy-r,cx+r,cy+r),0,180,fill=rgba(GOLD,120),width=3)
    gap=lerp(0.5,0.02,prog)
    d.arc((cx-r,cy-r,cx+r,cy+r),180,180+180*(1-gap),fill=rgba(ROSE_GOLD,int(200*prog)),width=3)
    d.arc((cx-r,cy-r,cx+r,cy+r),0,180*(1-gap),fill=rgba(GOLD,int(200*prog)),width=3)
    draw_glow(im,(cx,cy),18,GOLD_LIGHT,int(100*prog),14)
    d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=rgba(WHITE,int(220*prog)))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(ibn_ground(fs,DEEP,TEAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,95),'there is only one act of being',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'one ocean — many waves',font=TERM_FONT,fill=TEAL,anchor='mm')
    d.text((cx,155),'different forms, same water',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.line((180,380,1100,380),fill=rgba(TEAL,100),width=1)
    for i in range(8):
        x=220+i*100; a=t*0.5+i*0.8
        amp=20+15*math.sin(i*1.3)
        y=380+amp*math.sin(a)*prog
        pts=[]
        for j in range(30):
            u=j/29; xx=x-40+u*80; yy=y+6*math.sin(u*3+a)*prog
            pts.append((xx,yy))
        draw_line_glow(im,pts,mix(TEAL,GOLD_LIGHT,i/8),1,70,4)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'i created perception in thee',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'only that i might become',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,150),'the object of my perception',font=TERM_FONT,fill=ROSE_GOLD,anchor='mm')
    prog=ease_in_out(t)
    d.arc((cx-50,cy+10,cx+50,cy+70),180,360,fill=rgba(SILVER,150),width=3)
    d.arc((cx-50,cy+10,cx+50,cy+70),0,180,fill=rgba(SILVER,150),width=3)
    d.ellipse((cx-5,cy+38,cx+5,cy+42),fill=rgba(WHITE,220))
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        pts=bezier((cx,cy+10),(cx-40,cy-20),(cx+60,cy-10),(cx,cy-50),60)
        reveal=partial_polyline(pts,p)
        if len(reveal)>1: draw_line_glow(im,reveal,GOLD_LIGHT,2,90,6)
        d.ellipse((cx-4,cy-54,cx+4,cy-46),fill=rgba(GOLD_LIGHT,int(200*p)))

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,MIRROR,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'you are the mirror',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'in which the divine can see itself',font=TERM_FONT,fill=MIRROR,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((400,200,880,380),radius=16,outline=rgba(MIRROR,150),width=2)
    draw_glow(im,(700,260),40,GOLD_LIGHT,int(80*prog),20)
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        d.ellipse((640-10,290-10,640+10,290+10),fill=rgba(ROSE_GOLD,int(180*p)))
        d.text((640,330),'reflection',font=SMALL_FONT,fill=rgba(ROSE_GOLD,int(200*p)),anchor='mm')

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(ibn_ground(fs,WARM_DARK,CORAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the formless takes form',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'in the heart that contemplates it',font=TERM_FONT,fill=CORAL,anchor='mm')
    d.text((cx,150),'in the most beautiful of forms',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-35,cy+10,cx+35,cy+60),outline=rgba(CORAL,120),width=2)
    draw_glow(im,(cx,cy+35),int(5+30*prog),GOLD_LIGHT,int(130*prog),14)
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        d.ellipse((cx-20,cy+18,cx+20,cy+52),fill=rgba(ROSE_GOLD_LIGHT,int(60*p)))
        d.ellipse((cx-4,cy+31,cx+4,cy+39),fill=rgba(WHITE,int(200*p)))

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(ibn_ground(fs,DEEP,SILVER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'to know god is to know',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'that you do not know',font=TERM_FONT,fill=SILVER,anchor='mm')
    d.text((cx,155),'and that the one who does not know',font=SMALL_FONT,fill=MIST,anchor='mm')
    d.text((cx,175),'is not separate from what is known',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    if prog<0.5:
        p=prog*2
        d.rounded_rectangle((500,200,780,280),radius=10,outline=rgba(SILVER,int(180*p)),width=2)
        d.text((640,240),'concept of god',font=SMALL_FONT,fill=rgba(SILVER,int(200*p)),anchor='mm')
    else:
        p=(prog-0.5)*2
        draw_glow(im,(cx,cy+20),int(15+25*p),GOLD_LIGHT,int(120*p),16)
        d.ellipse((cx-15,cy+5,cx+15,cy+35),outline=rgba(GOLD_LIGHT,int(200*p)),width=2)
        d.text((640,300),'unknowing',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'the perfect man',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'divine self-disclosure reaches completion',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,152),'the cosmos groans toward the birth of this individual',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-25,cy+10,cx+25,cy+55),outline=rgba(SLATE,120),width=2)
    d.line((cx,cy+55,cx,cy+110),fill=rgba(SLATE,100),width=2)
    d.line((cx,cy+30,cx-50,cy+70),fill=rgba(SLATE,80),width=2)
    d.line((cx,cy+30,cx+50,cy+70),fill=rgba(SLATE,80),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        draw_glow(im,(cx,cy+35),int(10+35*p),GOLD_LIGHT,int(120*p),16)
        d.ellipse((cx-int(12+20*p),cy+23-int(12+20*p),cx+int(12+20*p),cy+47+int(12+20*p)),fill=rgba(WHITE,int(200*p)))

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(ibn_ground(fs,DEEP,LAVENDER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'an individual who is his own species',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'a category of one — like the angel',font=TERM_FONT,fill=LAVENDER,anchor='mm')
    d.text((cx,155),'the goal: to become a new possibility for being itself',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+20),int(15+35*prog),LAVENDER,int(120*prog),16)
    d.ellipse((cx-int(12+25*prog),cy-int(8+15*prog),cx+int(12+25*prog),cy+40+int(8+15*prog)),fill=rgba(WHITE,int(200*prog)),outline=rgba(LAVENDER,int(200*prog)),width=2)

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(ibn_ground(fs,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'every scripture',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'is a letter addressed to you personally',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,150),'the whole cosmos is a book — you are the reader',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((400,200,880,360),radius=8,outline=rgba(GOLD,150),width=2)
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        d.line((420,260,860,260),fill=rgba(GOLD_LIGHT,int(100*p)),width=1)
        d.line((420,290,800,290),fill=rgba(GOLD_LIGHT,int(80*p)),width=1)
        d.line((420,320,750,320),fill=rgba(GOLD_LIGHT,int(60*p)),width=1)
        d.text((640,240),'dear you,',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,ROSE_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'love requires a beloved',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the mirror in which love sees itself',font=TERM_FONT,fill=ROSE_GOLD,anchor='mm')
    d.text((cx,145),'two mirrors facing each other — infinite reflections',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx-100,cy+25),25,ROSE_GOLD,int(100*prog),14)
    d.rounded_rectangle((cx-130,cy-10,cx-70,cy+60),radius=6,outline=rgba(ROSE_GOLD,int(180*prog)),width=2)
    draw_glow(im,(cx+100,cy+25),25,GOLD_LIGHT,int(100*prog),14)
    d.rounded_rectangle((cx+70,cy-10,cx+130,cy+60),radius=6,outline=rgba(GOLD_LIGHT,int(180*prog)),width=2)
    draw_line_glow(im,[(cx-68,cy+25),(cx+68,cy+25)],ROSE_GOLD,int(100*prog),2,70,6)
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        d.ellipse((cx-4,cy+21,cx+4,cy+29),fill=rgba(WHITE,int(200*p)))

def sc11(im,t):
    fs=SEED+int(t*9973+5000)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'you are an organ of the divine body',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'necessary for self-completion',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'the world is incomplete until you arrive',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-80,cy-40,cx+80,cy+60),outline=rgba(SLATE,100),width=2)
    missing=lerp(0.5,0.05,prog)
    d.arc((cx-80,cy-40,cx+80,cy+60),0,360*(1-missing),fill=rgba(GOLD,int(150*prog)),width=3)
    d.arc((cx-80,cy-40,cx+80,cy+60),360*(1-missing),360,fill=rgba(GOLD_LIGHT,int(200*prog)),width=3)
    draw_glow(im,(cx,cy+10),15,GOLD_LIGHT,int(100*prog),12)

def sc12(im,t):
    fs=SEED+int(t*9973+5500)%100000; im.paste(ibn_ground(fs,DEEP_GOLD,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,85),'the only question',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'is whether you will know it',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'and in knowing it, complete the circle',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    r=150
    d.arc((cx-r,cy-r,cx+r,cy+r),0,360*prog,fill=rgba(GOLD,int(200*prog)),width=3)
    draw_glow(im,(cx,cy),int(10+25*prog),GOLD_LIGHT,int(130*prog),14)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=rgba(WHITE,int(255*prog)))
    for i in range(12):
        a=i*2*math.pi/12+t*0.06; r2=170+20*prog
        x=cx+math.cos(a)*r2; y=cy+math.sin(a)*r2*0.62
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(GOLD_LIGHT,int(120*prog)))
    d.text((640,485),'you are that being. you have always been that being.',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[,Scene('iw01','God Needs You','What if god needs you as much as you need god?','Wahdat al-wujud','','opening',['god','need','completion'],'intro','two arcs forming a circle',6.0,sc01)
Scene('iw02','One Ocean','One act of being — one ocean, many waves.','Wahdat al-wujud','','unity',['ocean','waves','unity'],'unity','many waves on one ocean surface',8.0,sc02)
Scene('iw03','I Created Perception','That i might become the object of my perception.','Tajallī','','perception',['perception','self-seeing','eye'],'perception','eye whose gaze curves back to itself',8.0,sc03)
Scene('iw04','The Mirror','You are the mirror in which the divine sees itself.','Mir\'āt','','mirror',['mirror','reflection','witness'],'mirror','mirror reflecting luminous source',8.0,sc04)
Scene('iw05','The Formless Takes Form','In the heart that contemplates — the most beautiful form.','Tashakkul','','theophany',['heart','form','theophany'],'theophany','light taking shape within a heart-space',8.0,sc05)
Scene('iw06','Unknowing','To know god is to know you do not know.','Jahl','','unknowing',['unknowing','concept','dissolution'],'unknowing','concept of god dissolving into open hands',8.0,sc06)
Scene('iw07','The Perfect Man','Divine self-disclosure reaching completion.','Al-insān al-kāmil','','perfection',['perfect man','completion','luminous'],'perfection','human figure becoming translucent with light',8.0,sc07)
Scene('iw08','A Category of One','An individual who is his own species.','Fard','','angel',['angel','unique','species'],'angel','single luminous figure — complete alone',6.0,sc08)
Scene('iw09','A Letter to You','Every scripture addressed to you personally.','Kitāb','','scripture',['scripture','letter','reader'],'scripture','open book showing "dear you"',8.0,sc09)
Scene('iw10','Two Mirrors','Love requires a beloved — infinite reflections.','Mahabbah','','love',['love','mirror','reflection'],'love','two mirrors facing each other with light',8.0,sc10)
Scene('iw11','The Divine Body','You are an organ — necessary for completion.','Jism ilāhī','','body',['body','completion','arrival'],'body','cosmic body with one part missing — you',6.0,sc11)
Scene('iw12','Complete the Circle','The only question is whether you will know it.','Kamāl','','seal',['circle','completion','recognition'],'seal','circle closing with radiant center',8.0,sc12)
Scene('iw01','God Needs You','What if god needs you as much as you need god?','Wahdat al-wujud','','opening',['god','need','completion'],'intro','two arcs forming a circle',6.0,sc01)
Scene('iw02','One Ocean','One act of being — one ocean, many waves.','Wahdat al-wujud','','unity',['ocean','waves','unity'],'unity','many waves on one ocean surface',8.0,sc02)
Scene('iw03','I Created Perception','That i might become the object of my perception.','Tajallī','','perception',['perception','self-seeing','eye'],'perception','eye whose gaze curves back to itself',8.0,sc03)
Scene('iw04','The Mirror','You are the mirror in which the divine sees itself.','Mir\'āt','','mirror',['mirror','reflection','witness'],'mirror','mirror reflecting luminous source',8.0,sc04)
Scene('iw05','The Formless Takes Form','In the heart that contemplates — the most beautiful form.','Tashakkul','','theophany',['heart','form','theophany'],'theophany','light taking shape within a heart-space',8.0,sc05)
Scene('iw06','Unknowing','To know god is to know you do not know.','Jahl','','unknowing',['unknowing','concept','dissolution'],'unknowing','concept of god dissolving into open hands',8.0,sc06)
Scene('iw07','The Perfect Man','Divine self-disclosure reaching completion.','Al-insān al-kāmil','','perfection',['perfect man','completion','luminous'],'perfection','human figure becoming translucent with light',8.0,sc07)
Scene('iw08','A Category of One','An individual who is his own species.','Fard','','angel',['angel','unique','species'],'angel','single luminous figure — complete alone',6.0,sc08)
Scene('iw09','A Letter to You','Every scripture addressed to you personally.','Kitāb','','scripture',['scripture','letter','reader'],'scripture','open book showing "dear you"',8.0,sc09)
Scene('iw10','Two Mirrors','Love requires a beloved — infinite reflections.','Mahabbah','','love',['love','mirror','reflection'],'love','two mirrors facing each other with light',8.0,sc10)
Scene('iw11','The Divine Body','You are an organ — necessary for completion.','Jism ilāhī','','body',['body','completion','arrival'],'body','cosmic body with one part missing — you',6.0,sc11)
Scene('iw12','Complete the Circle','The only question is whether you will know it.','Kamāl','','seal',['circle','completion','recognition'],'seal','circle closing with radiant center',8.0,sc12)
Scene('iw01','God Needs You','What if god needs you as much as you need god?','Wahdat al-wujud','','opening',['god','need','completion'],'intro','two arcs forming a circle',6.0,sc01)
Scene('iw02','One Ocean','One act of being — one ocean, many waves.','Wahdat al-wujud','','unity',['ocean','waves','unity'],'unity','many waves on one ocean surface',8.0,sc02)
Scene('iw03','I Created Perception','That i might become the object of my perception.','Tajallī','','perception',['perception','self-seeing','eye'],'perception','eye whose gaze curves back to itself',8.0,sc03)
Scene('iw04','The Mirror','You are the mirror in which the divine sees itself.','Mir\'āt','','mirror',['mirror','reflection','witness'],'mirror','mirror reflecting luminous source',8.0,sc04)
Scene('iw05','The Formless Takes Form','In the heart that contemplates — the most beautiful form.','Tashakkul','','theophany',['heart','form','theophany'],'theophany','light taking shape within a heart-space',8.0,sc05)
Scene('iw06','Unknowing','To know god is to know you do not know.','Jahl','','unknowing',['unknowing','concept','dissolution'],'unknowing','concept of god dissolving into open hands',8.0,sc06)
Scene('iw07','The Perfect Man','Divine self-disclosure reaching completion.','Al-insān al-kāmil','','perfection',['perfect man','completion','luminous'],'perfection','human figure becoming translucent with light',8.0,sc07)
Scene('iw08','A Category of One','An individual who is his own species.','Fard','','angel',['angel','unique','species'],'angel','single luminous figure — complete alone',6.0,sc08)
Scene('iw09','A Letter to You','Every scripture addressed to you personally.','Kitāb','','scripture',['scripture','letter','reader'],'scripture','open book showing "dear you"',8.0,sc09)
Scene('iw10','Two Mirrors','Love requires a beloved — infinite reflections.','Mahabbah','','love',['love','mirror','reflection'],'love','two mirrors facing each other with light',8.0,sc10)
Scene('iw11','The Divine Body','You are an organ — necessary for completion.','Jism ilāhī','','body',['body','completion','arrival'],'body','cosmic body with one part missing — you',6.0,sc11)
Scene('iw12','Complete the Circle','The only question is whether you will know it.','Kamāl','','seal',['circle','completion','recognition'],'seal','circle closing with radiant center',8.0,sc12)
    Scene('iw01','God Needs You','What if god needs you as much as you need god?','Wahdat al-wujud','','opening',['god','need','completion'],'intro','two arcs forming a circle',6.0,sc01),
    Scene('iw02','One Ocean','One act of being — one ocean, many waves.','Wahdat al-wujud','','unity',['ocean','waves','unity'],'unity','many waves on one ocean surface',8.0,sc02),
    Scene('iw03','I Created Perception','That i might become the object of my perception.','Tajallī','','perception',['perception','self-seeing','eye'],'perception','eye whose gaze curves back to itself',8.0,sc03),
    Scene('iw04','The Mirror','You are the mirror in which the divine sees itself.','Mir\'āt','','mirror',['mirror','reflection','witness'],'mirror','mirror reflecting luminous source',8.0,sc04),
    Scene('iw05','The Formless Takes Form','In the heart that contemplates — the most beautiful form.','Tashakkul','','theophany',['heart','form','theophany'],'theophany','light taking shape within a heart-space',8.0,sc05),
    Scene('iw06','Unknowing','To know god is to know you do not know.','Jahl','','unknowing',['unknowing','concept','dissolution'],'unknowing','concept of god dissolving into open hands',8.0,sc06),
    Scene('iw07','The Perfect Man','Divine self-disclosure reaching completion.','Al-insān al-kāmil','','perfection',['perfect man','completion','luminous'],'perfection','human figure becoming translucent with light',8.0,sc07),
    Scene('iw08','A Category of One','An individual who is his own species.','Fard','','angel',['angel','unique','species'],'angel','single luminous figure — complete alone',6.0,sc08),
    Scene('iw09','A Letter to You','Every scripture addressed to you personally.','Kitāb','','scripture',['scripture','letter','reader'],'scripture','open book showing "dear you"',8.0,sc09),
    Scene('iw10','Two Mirrors','Love requires a beloved — infinite reflections.','Mahabbah','','love',['love','mirror','reflection'],'love','two mirrors facing each other with light',8.0,sc10),
    Scene('iw11','The Divine Body','You are an organ — necessary for completion.','Jism ilāhī','','body',['body','completion','arrival'],'body','cosmic body with one part missing — you',6.0,sc11),
    Scene('iw12','Complete the Circle','The only question is whether you will know it.','Kamāl','','seal',['circle','completion','recognition'],'seal','circle closing with radiant center',8.0,sc12),
]

def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    nframes=int(FPS*scene.duration)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    for i,path in enumerate(expected):
        if path.exists() and path.stat().st_size>1000: continue
        t=i/max(1,nframes-1)
        im=Image.new('RGBA',(W,H),(0,0,0,0))
        scene.draw_fn(im,t)
        dust(im,SEED+hash(scene.id)%10000+i,55)
        border(im); footer(im,scene.title,scene.subtitle,scene.term)
        im.convert('RGB').save(path,quality=95)
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DEEP_GOLD)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Wahdat al-Wujud — God Is Incomplete Without You',
        'source_basis':'Expansion Essay 14: "god is incomplete without you" (Ibn \'Arabi) — 12 scenes.',
        'style':{'family':'wahdat / mirror visualization','background':'deep gold','ink':'rose-gold, gold-light, mirror-silver'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Wahdat al-Wujud — 12 scenes, rose-gold/mirror palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Wahdat Pack — rose-gold/mirror/self-disclosure palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Wahdat al-Wujud — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'ibn_arabi_wahdat_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'ibn_arabi_wahdat_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['ibn_arabi_wahdat_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'ibn_arabi_wahdat_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
