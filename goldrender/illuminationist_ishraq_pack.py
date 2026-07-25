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
SEED = 15150

DEEP_NIGHT = (12, 14, 22)
WARM_NIGHT = (18, 16, 20)
DARK = (14, 14, 18)
EMERALD = (65, 140, 100)
EMERALD_LIGHT = (130, 205, 155)
DAWN_GOLD = (220, 190, 120)
GOLD = (206, 166, 88)
GOLD_LIGHT = (246, 218, 144)
PEARL = (246, 243, 236)
WHITE = (252, 250, 246)
SILVER = (196, 204, 222)
TEAL = (92, 146, 148)
SLATE = (90, 100, 120)
MIST = (160, 172, 192)
LAVENDER = (170, 156, 200)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 26)

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
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
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0], u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def arc_points(cx,cy,rx,ry,a0,a1,n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx, cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]

def draw_rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        d.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    d.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(EMERALD,80),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(EMERALD_LIGHT,50),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,EMERALD,DAWN_GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,14,22,200),outline=rgba(EMERALD,45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=DAWN_GOLD)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(EMERALD_LIGHT,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def ishraq_ground(seed,bg,glow_col,intensity=0.5):
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

def luminous_figure(d,im,cx,cy,r,col,t,prog,inner=None):
    inner=inner or col
    draw_glow(im,(cx,cy),int(r*1.5),col,int(100*prog),25)
    d.ellipse((cx-int(r*0.5),cy-int(r*0.7),cx+int(r*0.5),cy+int(r*0.7)),fill=rgba(inner,int(150*prog)),outline=rgba(col,int(200*prog)),width=2)
    d.ellipse((cx-int(r*0.3),cy-int(r*0.1),cx+int(r*0.3),cy+int(r*0.1)),fill=rgba(inner,int(200*prog)))
    for i in range(6):
        a=i*2*math.pi/6+t*0.06; x=cx+math.cos(a)*r*0.6; y=cy+math.sin(a)*r*0.4
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,int(120*prog)))

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,DAWN_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,105),'light is visible by itself',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,135),'it needs nothing else to see it',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy),int(10+60*prog),GOLD_LIGHT,int(150*prog),20)
    d.ellipse((cx-int(8+12*prog),cy-int(8+12*prog),cx+int(8+12*prog),cy+int(8+12*prog)),fill=rgba(WHITE,int(255*prog)))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,EMERALD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the world between worlds',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'— the mundus imaginalis —',font=TERM_FONT,fill=EMERALD_LIGHT,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((200,180,cx-20,400),radius=14,outline=rgba(SILVER,120),width=2)
    d.rounded_rectangle((cx+20,180,1080,400),radius=14,outline=rgba(EMERALD,120),width=2)
    shimmer=int(cx-20+(40+60*math.sin(t*1.5))*prog)
    d.rounded_rectangle((shimmer,190,shimmer+40,390),radius=8,outline=rgba(DAWN_GOLD,int(150*prog)),width=2)
    draw_glow(im,(shimmer+20,290),20,DAWN_GOLD,int(80*prog),12)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,EMERALD,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the emerald cities of hurqalya',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'on the cosmic mountain qaf',font=TERM_FONT,fill=EMERALD_LIGHT,anchor='mm')
    prog=ease_in_out(t)
    pts=[(cx,120),(cx-60,180),(cx-80,300),(cx-40,400),(cx+40,400),(cx+80,300),(cx+60,180)]
    d.polygon(pts,outline=rgba(EMERALD,int(150*prog)),fill=rgba(EMERALD,int(20*prog)))
    d.rounded_rectangle((cx-40,180,cx+40,280),radius=6,outline=rgba(DAWN_GOLD,int(180*prog)),fill=rgba(EMERALD_LIGHT,int(30*prog)),width=2)
    for i in range(5):
        x=cx-30+15*i; y=200+20*i
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(DAWN_GOLD,int(150*prog)))
    draw_glow(im,(cx,160),25,EMERALD_LIGHT,int(80*prog),14)

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,95),'na-koja-abad',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'the land that is nowhere',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    d.text((cx,155),'the cosmic north within you',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-80,cy+10,cx+80,cy+90),outline=rgba(EMERALD,120),width=2)
    d.ellipse((cx-40,cy+30,cx+40,cy+70),outline=rgba(DAWN_GOLD,100),width=1)
    draw_glow(im,(cx,cy+50),12,GOLD_LIGHT,int(100*prog),10)
    d.ellipse((cx-5,cy+45,cx+5,cy+55),fill=rgba(WHITE,int(200*prog)))
    for i in range(4):
        a=i*2*math.pi/4; x=cx+math.cos(a)*90*prog; y=cy+50+math.sin(a)*55*prog
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(EMERALD_LIGHT,int(120*prog)))

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(ishraq_ground(fs,WARM_NIGHT,GOLD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'perfect nature',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the guide of light',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    d.text((cx,150),'with you since before your birth',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    luminous_figure(d,im,cx,cy+20,45,GOLD_LIGHT,t,prog,WHITE)

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,DAWN_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,85),'thou art the spirit who gave birth to me',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'and the child to whom my spirit gives birth',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    d.text((cx,145),'— both parent and child —',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    luminous_figure(d,im,cx-90,cy+15,30,GOLD_LIGHT,t,prog,WHITE)
    luminous_figure(d,im,cx+90,cy+15,30,EMERALD_LIGHT,t,prog,WHITE)
    draw_line_glow(im,[(cx-60,cy+15),(cx+60,cy+15)],DAWN_GOLD,2,100,6)
    for i in range(6):
        a=i*2*math.pi/6+t*0.08; x=cx+math.cos(a)*20; y=cy+15+math.sin(a)*14
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(DAWN_GOLD,180))

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(ishraq_ground(fs,DARK,None,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,85),'the midnight sun',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'at the darkest point of the night',font=TERM_FONT,fill=SILVER,anchor='mm')
    d.text((cx,145),'the sun shines',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    prog=ease_in_out(t)
    r=lerp(3,200,prog)
    draw_glow(im,(cx,cy),int(r),GOLD_LIGHT,int(200*prog),40)
    d.ellipse((cx-int(r*0.5),cy-int(r*0.4),cx+int(r*0.5),cy+int(r*0.4)),fill=rgba(WHITE,int(200*prog)))
    if prog>0.7:
        p=clamp((prog-0.7)*3.3)
        d.ellipse((cx-int(r*0.7),cy-int(r*0.55),cx+int(r*0.7),cy+int(r*0.55)),outline=rgba(EMERALD,int(120*p)),width=1)

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,EMERALD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'every being has a fravarti',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a counterpart above',font=TERM_FONT,fill=EMERALD_LIGHT,anchor='mm')
    d.text((cx,145),'light upon light',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    prog=ease_in_out(t)
    for i in range(10):
        x=cx-180+40*i
        y_below=380; y_above=180
        p=clamp(prog*1.3-i*0.05)
        if p<=0: continue
        col=mix(EMERALD_LIGHT,DAWN_GOLD,i/10)
        d.ellipse((x-3,y_below-3,x+3,y_below+3),fill=rgba(col,int(180*p)))
        d.ellipse((x-3,y_above-3,x+3,y_above+3),fill=rgba(col,int(200*p)))
        draw_line_glow(im,[(x,y_below),(x,y_above)],col,1,60,4)

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(ishraq_ground(fs,WARM_NIGHT,DAWN_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'two kinds of knowing',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'evening knowledge — from outside',font=SMALL_FONT,fill=MIST,anchor='mm')
    d.text((cx,140),'morning knowledge — from within',font=SMALL_FONT,fill=DAWN_GOLD,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((180,200,500,380),radius=12,outline=rgba(SILVER,150),width=2)
    d.text((340,290),'observer',font=SMALL_FONT,fill=SILVER,anchor='mm')
    d.rounded_rectangle((780,200,1100,380),radius=12,outline=rgba(EMERALD,150),fill=rgba(EMERALD,15),width=2)
    d.text((940,290),'participant',font=SMALL_FONT,fill=EMERALD_LIGHT,anchor='mm')
    draw_line_glow(im,bezier((500,290),(640,250),(680,330),(780,290),60),DAWN_GOLD,3,120,7)

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,EMERALD,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the emerald rock',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'translucent, luminous',font=TERM_FONT,fill=EMERALD_LIGHT,anchor='mm')
    d.text((cx,145),'the goal of the journey',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    pts=[(cx,140),(cx-50,180),(cx-60,280),(cx-30,380),(cx+30,380),(cx+60,280),(cx+50,180)]
    d.polygon(pts,outline=rgba(EMERALD,int(180*prog)),fill=rgba(EMERALD,int(30*prog)))
    draw_glow(im,(cx,260),40,EMERALD_LIGHT,int(80*prog),18)
    draw_glow(im,(cx,260),15,WHITE,int(100*prog),10)
    d.ellipse((cx-6,254,cx+6,266),fill=rgba(WHITE,int(220*prog)))

def sc11(im,t):
    fs=SEED+int(t*9973+5000)%100000; im.paste(ishraq_ground(fs,DEEP_NIGHT,DAWN_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the chinvat bridge',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'you decide which self you will be',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    prog=ease_in_out(t)
    pts=bezier((200,370),(400,330),(880,330),(1080,370),80)
    draw_line_glow(im,pts,DAWN_GOLD,3,110,7)
    luminous_figure(d,im,int(lerp(400,640,prog)),320,25,GOLD_LIGHT,t,prog,WHITE)
    d.rounded_rectangle((120,130,280,200),radius=8,outline=rgba(SILVER,100),width=1)
    d.text((200,165),'exile',font=TINY_FONT,fill=SILVER,anchor='mm')
    d.rounded_rectangle((1000,130,1160,200),radius=8,outline=rgba(EMERALD,100),width=1)
    d.text((1080,165),'home',font=TINY_FONT,fill=EMERALD_LIGHT,anchor='mm')

def sc12(im,t):
    fs=SEED+int(t*9973+5500)%100000; im.paste(ishraq_ground(fs,WARM_NIGHT,GOLD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,85),'you are already light',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a candle that has forgotten it is fire',font=TERM_FONT,fill=DAWN_GOLD,anchor='mm')
    d.text((cx,150),'the seeker and the sought are the same luminosity',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-8,cy+10,cx+8,cy+35),outline=rgba(DAWN_GOLD,150),width=2)
    pts=[(cx,cy-10),(cx-8,cy+10),(cx+8,cy+10)]
    d.polygon(pts,outline=rgba(DAWN_GOLD,180),fill=rgba(DAWN_GOLD,30))
    draw_glow(im,(cx,cy-15),int(10+25*prog),GOLD_LIGHT,int(140*prog),16)
    d.ellipse((cx-10,cy-25,cx+10,cy-5),fill=rgba(WHITE,int(255*prog)))
    for i in range(12):
        a=i*2*math.pi/12+t*0.05; r=60+80*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.5
        draw_line_glow(im,[(cx,cy),(int(x),int(y))],mix(GOLD_LIGHT,EMERALD_LIGHT,i/12),1,50,4)

SCENES=[,Scene('ir01','Light Sees Itself','Visible by itself — needs nothing else.','Nūr','','opening',['light','self-luminous'],'intro','self-illuminating point',6.0,sc01)
Scene('ir02','The World Between','Mundus imaginalis — between pure light and sensory world.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'threshold','shimmering corridor between two realms',8.0,sc02)
Scene('ir03','Emerald Cities','Hurqalya on the cosmic mountain Qaf.','Hurqalya','','city',['emerald','city','mountain'],'geography','crystalline green city on mountain peak',8.0,sc03)
Scene('ir04','The Land That Is Nowhere','Na-koja-abad — the cosmic north within you.','Na-koja-abad','','center',['nowhere','center','north'],'geography','compass pointing inward to center',6.0,sc04)
Scene('ir05','Perfect Nature','The Guide of Light — with you since before birth.','Al-tiba\' al-tamm','','guide',['guide','light','nature'],'guide','luminous figure of pure light',8.0,sc05)
Scene('ir06','Parent and Child','Thou gavest birth to me — I give birth to thee.','Syzygy','','mutual',['mutual','birth','reciprocal'],'relationship','two figures connected by light-thread',8.0,sc06)
Scene('ir07','The Midnight Sun','At the darkest point of the night, the sun shines.','Nisf al-layl','','sun',['midnight','sun','darkness'],'illumination','radiance expanding from absolute dark',8.0,sc07)
Scene('ir08','Light Upon Light','Every being has a fravarti — a counterpart above.','Fravarti','','paired',['paired','counterpart','above'],'syzygy','pairs of lights in vertical column',8.0,sc08)
Scene('ir09','Two Knowings','Evening knowledge — morning knowledge.','Cognitio matutina','','knowledge',['knowledge','observer','participant'],'epistemology','observer vs participant side by side',8.0,sc09)
Scene('ir10','The Emerald Rock','Translucent, luminous — the goal of the journey.','Zarqā\'','','rock',['emerald','rock','goal'],'goal','crystalline rock glowing from within',6.0,sc10)
Scene('ir11','The Chinvat Bridge','You decide which self you will be.','Chinvat','','bridge',['bridge','threshold','decision'],'bridge','figure crossing bridge of light',8.0,sc11)
Scene('ir12','A Candle Forgetting It Is Fire','The seeker and the sought are the same luminosity.','Ishrāq','','seal',['light','recognition','self'],'seal','candle-flame with radial recognition rays',8.0,sc12)
Scene('ir01','Light Sees Itself','Visible by itself — needs nothing else.','Nūr','','opening',['light','self-luminous'],'intro','self-illuminating point',6.0,sc01)
Scene('ir02','The World Between','Mundus imaginalis — between pure light and sensory world.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'threshold','shimmering corridor between two realms',8.0,sc02)
Scene('ir03','Emerald Cities','Hurqalya on the cosmic mountain Qaf.','Hurqalya','','city',['emerald','city','mountain'],'geography','crystalline green city on mountain peak',8.0,sc03)
Scene('ir04','The Land That Is Nowhere','Na-koja-abad — the cosmic north within you.','Na-koja-abad','','center',['nowhere','center','north'],'geography','compass pointing inward to center',6.0,sc04)
Scene('ir05','Perfect Nature','The Guide of Light — with you since before birth.','Al-tiba\' al-tamm','','guide',['guide','light','nature'],'guide','luminous figure of pure light',8.0,sc05)
Scene('ir06','Parent and Child','Thou gavest birth to me — I give birth to thee.','Syzygy','','mutual',['mutual','birth','reciprocal'],'relationship','two figures connected by light-thread',8.0,sc06)
Scene('ir07','The Midnight Sun','At the darkest point of the night, the sun shines.','Nisf al-layl','','sun',['midnight','sun','darkness'],'illumination','radiance expanding from absolute dark',8.0,sc07)
Scene('ir08','Light Upon Light','Every being has a fravarti — a counterpart above.','Fravarti','','paired',['paired','counterpart','above'],'syzygy','pairs of lights in vertical column',8.0,sc08)
Scene('ir09','Two Knowings','Evening knowledge — morning knowledge.','Cognitio matutina','','knowledge',['knowledge','observer','participant'],'epistemology','observer vs participant side by side',8.0,sc09)
Scene('ir10','The Emerald Rock','Translucent, luminous — the goal of the journey.','Zarqā\'','','rock',['emerald','rock','goal'],'goal','crystalline rock glowing from within',6.0,sc10)
Scene('ir11','The Chinvat Bridge','You decide which self you will be.','Chinvat','','bridge',['bridge','threshold','decision'],'bridge','figure crossing bridge of light',8.0,sc11)
Scene('ir12','A Candle Forgetting It Is Fire','The seeker and the sought are the same luminosity.','Ishrāq','','seal',['light','recognition','self'],'seal','candle-flame with radial recognition rays',8.0,sc12)
Scene('ir01','Light Sees Itself','Visible by itself — needs nothing else.','Nūr','','opening',['light','self-luminous'],'intro','self-illuminating point',6.0,sc01)
Scene('ir02','The World Between','Mundus imaginalis — between pure light and sensory world.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'threshold','shimmering corridor between two realms',8.0,sc02)
Scene('ir03','Emerald Cities','Hurqalya on the cosmic mountain Qaf.','Hurqalya','','city',['emerald','city','mountain'],'geography','crystalline green city on mountain peak',8.0,sc03)
Scene('ir04','The Land That Is Nowhere','Na-koja-abad — the cosmic north within you.','Na-koja-abad','','center',['nowhere','center','north'],'geography','compass pointing inward to center',6.0,sc04)
Scene('ir05','Perfect Nature','The Guide of Light — with you since before birth.','Al-tiba\' al-tamm','','guide',['guide','light','nature'],'guide','luminous figure of pure light',8.0,sc05)
Scene('ir06','Parent and Child','Thou gavest birth to me — I give birth to thee.','Syzygy','','mutual',['mutual','birth','reciprocal'],'relationship','two figures connected by light-thread',8.0,sc06)
Scene('ir07','The Midnight Sun','At the darkest point of the night, the sun shines.','Nisf al-layl','','sun',['midnight','sun','darkness'],'illumination','radiance expanding from absolute dark',8.0,sc07)
Scene('ir08','Light Upon Light','Every being has a fravarti — a counterpart above.','Fravarti','','paired',['paired','counterpart','above'],'syzygy','pairs of lights in vertical column',8.0,sc08)
Scene('ir09','Two Knowings','Evening knowledge — morning knowledge.','Cognitio matutina','','knowledge',['knowledge','observer','participant'],'epistemology','observer vs participant side by side',8.0,sc09)
Scene('ir10','The Emerald Rock','Translucent, luminous — the goal of the journey.','Zarqā\'','','rock',['emerald','rock','goal'],'goal','crystalline rock glowing from within',6.0,sc10)
Scene('ir11','The Chinvat Bridge','You decide which self you will be.','Chinvat','','bridge',['bridge','threshold','decision'],'bridge','figure crossing bridge of light',8.0,sc11)
Scene('ir12','A Candle Forgetting It Is Fire','The seeker and the sought are the same luminosity.','Ishrāq','','seal',['light','recognition','self'],'seal','candle-flame with radial recognition rays',8.0,sc12)
    Scene('ir01','Light Sees Itself','Visible by itself — needs nothing else.','Nūr','','opening',['light','self-luminous'],'intro','self-illuminating point',6.0,sc01),
    Scene('ir02','The World Between','Mundus imaginalis — between pure light and sensory world.','Mundus imaginalis','','threshold',['threshold','imaginal','between'],'threshold','shimmering corridor between two realms',8.0,sc02),
    Scene('ir03','Emerald Cities','Hurqalya on the cosmic mountain Qaf.','Hurqalya','','city',['emerald','city','mountain'],'geography','crystalline green city on mountain peak',8.0,sc03),
    Scene('ir04','The Land That Is Nowhere','Na-koja-abad — the cosmic north within you.','Na-koja-abad','','center',['nowhere','center','north'],'geography','compass pointing inward to center',6.0,sc04),
    Scene('ir05','Perfect Nature','The Guide of Light — with you since before birth.','Al-tiba\' al-tamm','','guide',['guide','light','nature'],'guide','luminous figure of pure light',8.0,sc05),
    Scene('ir06','Parent and Child','Thou gavest birth to me — I give birth to thee.','Syzygy','','mutual',['mutual','birth','reciprocal'],'relationship','two figures connected by light-thread',8.0,sc06),
    Scene('ir07','The Midnight Sun','At the darkest point of the night, the sun shines.','Nisf al-layl','','sun',['midnight','sun','darkness'],'illumination','radiance expanding from absolute dark',8.0,sc07),
    Scene('ir08','Light Upon Light','Every being has a fravarti — a counterpart above.','Fravarti','','paired',['paired','counterpart','above'],'syzygy','pairs of lights in vertical column',8.0,sc08),
    Scene('ir09','Two Knowings','Evening knowledge — morning knowledge.','Cognitio matutina','','knowledge',['knowledge','observer','participant'],'epistemology','observer vs participant side by side',8.0,sc09),
    Scene('ir10','The Emerald Rock','Translucent, luminous — the goal of the journey.','Zarqā\'','','rock',['emerald','rock','goal'],'goal','crystalline rock glowing from within',6.0,sc10),
    Scene('ir11','The Chinvat Bridge','You decide which self you will be.','Chinvat','','bridge',['bridge','threshold','decision'],'bridge','figure crossing bridge of light',8.0,sc11),
    Scene('ir12','A Candle Forgetting It Is Fire','The seeker and the sought are the same luminosity.','Ishrāq','','seal',['light','recognition','self'],'seal','candle-flame with radial recognition rays',8.0,sc12),
]

def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    nframes=int(FPS*scene.duration)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DEEP_NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Ishrāq — The Light That Illuminates Itself',
        'source_basis':'Expansion Essay 15: "the light that illuminates itself" (Suhrawardi) — 12 scenes.',
        'style':{'family':'illuminationist / emerald-dawn visualization','background':'deep night','ink':'emerald, dawn-gold, luminous white'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Ishraq — 12 scenes, emerald/dawn/light palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Ishraq Pack — emerald/dawn-gold/white illumination palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Ishrāq — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'illuminationist_ishraq_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'illuminationist_ishraq_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['illuminationist_ishraq_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True)
        render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'illuminationist_ishraq_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
