#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=18180

DEEP=(14,16,26); WARM=(20,18,22); NIGHT=(16,14,20)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246)
PEARL=(246,243,236); SILVER=(196,204,222); CRIMSON=(154,44,58)
CORAL=(206,108,100); TEAL=(92,146,148); INDIGO=(68,78,136)
VIOLET=(120,104,168); LAVENDER=(170,156,200); ROSE=(196,104,130)
SLATE=(90,100,120); MIST=(160,172,192); AMBER=(200,150,60)
GREEN=(96,148,108)

C7=[
    CRIMSON,
    CORAL,
    AMBER,
    GREEN,
    TEAL,
    INDIGO,
    LAVENDER,
    CRIMSON,
    CORAL,
    AMBER,
    GREEN,
    TEAL,
    INDIGO,
    LAVENDER,
]
C7_LIGHT=[(200,120,120),(220,160,140),(230,200,100),(140,200,140),(140,200,200),(140,150,200),(200,180,210)]

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
def rgba(c,a=255): return (*c[:3],int(a))

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

def draw_rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        d.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    d.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(LAVENDER,SILVER,.5),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(LAVENDER,SILVER,.3),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,INDIGO,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,12,20,200),outline=rgba(mix(LAVENDER,SILVER,.4),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,LAVENDER,.5))

def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(LAVENDER,SILVER,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(10,40))))
    im.alpha_composite(ov)

def subtle_ground(seed,bg,glow_col,intensity=0.4):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*2.8*intensity+fine[...,None]*0.8*intensity
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*16,0,22)[...,None]
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
    fs=SEED+int(t*9973)%100000; im.paste(subtle_ground(fs,DEEP,mix(LAVENDER,SILVER,.5),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'a body you have never touched',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'runs alongside the physical — a second current',font=TERM_FONT,fill=mix(LAVENDER,SILVER,.6),anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-28,cy-15,cx+28,cy+45),outline=rgba(mix(SLATE,LAVENDER,.5),120),width=2)
    d.ellipse((cx-22,cy-10,cx+22,cy+38),outline=rgba(mix(LAVENDER,GOLD_LIGHT,.3),int(200*prog)),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        draw_glow(im,(cx,cy+15),int(8+25*p),mix(LAVENDER,GOLD_LIGHT,.5),int(120*p),14)
        d.ellipse((cx-int(8+15*p),cy+7-int(8+15*p),cx+int(8+15*p),cy+23+int(8+15*p)),fill=rgba(WHITE,int(200*p)))
    d.text((640,480),'invisible — but measurable by its effects',font=SUB_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(subtle_ground(fs,WARM,mix(TEAL,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the three channels',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'iḍā — piṅgalā — suṣumṇā',font=TERM_FONT,fill=mix(TEAL,GOLD_LIGHT,.5),anchor='mm')
    d.text((cx,145),'lunar, solar, fire — each with its own sound',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(3):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        x=cx-80+i*80
        col=[mix(WHITE,TEAL,.4),mix(CORAL,GOLD,.5),mix(GOLD,CRIMSON,.4)][i]
        sz=12+8*(0.5+0.5*math.sin(t+i))
        pts=[]
        for j in range(40):
            u=j/39; y=cy+60+u*80
        for j in range(40):
            u=j/39; yy=cy+60+u*80
            xx=x+10*math.sin(u*2+t+i)*p
            pts.append((xx,yy))
        draw_line_glow(im,pts,col,3,110,7)
        d.text((x,cy+45),['iḍā','piṅgalā','suṣumṇā'][i],font=SMALL_FONT,fill=rgba(col,int(200*p)),anchor='mm')
    draw_glow(im,(cx,cy+100),15,mix(GOLD_LIGHT,WHITE,.5),80,10)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(subtle_ground(fs,NIGHT,mix(LAVENDER,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,85),'the seven cakras',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'thresholds where consciousness condenses into different densities',font=SMALL_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')
    c_names=['mūlādhāra','svādhiṣṭhāna','maṇipūra','anāhata','viśuddha','ājñā','sahasrāra']
    prog=smoothstep(0.05,0.9,t)
    for i in range(7):
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        y=155+i*38
        r=8+4*math.sin(t+i)
        draw_glow(im,(cx,y),int(r+4),mix(C7[i],C7_LIGHT[i],.5),int(100*p),10)
        d.ellipse((cx-r,y-r,cx+r,y+r),fill=rgba(mix(C7_LIGHT[i],WHITE,.3),int(200*p)),outline=rgba(C7[i],int(190*p)),width=2)
        d.text((cx-45,y-4),c_names[i],font=TINY_FONT,fill=rgba(mix(C7_LIGHT[i],PEARL,.3),int(200*p)),anchor='rm')
        if i<6:
            pts=partial_polyline([(cx,y+8+r),(cx,y+38-8)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(C7[i],C7[i+1],.5),1,50,3)

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(subtle_ground(fs,DEEP,mix(TEAL,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the nāḍīs — wireless system',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'patterns in the prāṇic field, not carried by any physical substrate',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(20):
        a=i*2*math.pi/20
        x=cx+math.cos(a)*140; y=cy+20+math.sin(a)*140*0.55
        p=clamp(prog*1.3-i*0.03)
        if p<=0: continue
        col=mix(LAVENDER,TEAL,i/20)
        draw_line_glow(im,[(cx,cy+20),(int(x),int(y))],col,1,40+(i%3)*15,3)
        d.ellipse((int(x)-2,int(y)-2,int(x)+2,int(y)+2),fill=rgba(col,int(120*p)))
    draw_glow(im,(cx,cy+20),18,mix(GOLD_LIGHT,TEAL,.5),100,12)
    d.ellipse((cx-7,cy+13,cx+7,cy+27),fill=rgba(WHITE,220))

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(subtle_ground(fs,WARM,mix(CORAL,GOLD,.3),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'kuṇḍalinī — three lights',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'sunless light — moonlike light — firelike burning light',font=SMALL_FONT,fill=mix(MIST,CORAL,.4),anchor='mm')
    prog=ease_in_out(t)
    coils=bezier((cx,cy+50),(cx-60,cy+20),(cx+60,cy+20),(cx,cy+50),60)
    reveal=partial_polyline(coils,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,mix(GOLD,CRIMSON,.4),4,130,8)
    c_names=['sunless','moonlike','firelike']
    c_cols=[mix(GOLD_LIGHT,WHITE,.5),mix(LAVENDER,TEAL,.4),mix(CORAL,GOLD,.5)]
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*130; y=cy+math.sin(a)*130*0.55
        d.ellipse((x-14,y-14,x+14,y+14),outline=rgba(c_cols[i],170),width=2)
        d.text((x,y+24),c_names[i],font=TINY_FONT,fill=c_cols[i],anchor='mm')
    d.text((640,485),'the power that, when awakened, reorganizes consciousness from the ground up',font=SUB_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(subtle_ground(fs,DEEP,mix(LAVENDER,SILVER,.5),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'static and dynamic',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the stillness that makes motion possible',font=TERM_FONT,fill=mix(LAVENDER,SILVER,.6),anchor='mm')
    d.text((cx,150),'kuṇḍalinī is that stillness — coiled, waiting',font=SMALL_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+20),int(5+30*prog),mix(LAVENDER,GOLD_LIGHT,.4),int(100*prog),16)
    d.ellipse((cx-40,cy-5,cx+40,cy+45),outline=rgba(mix(LAVENDER,GOLD,.3),int(160*prog)),width=2)
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        d.ellipse((cx-15,cy+6,cx+15,cy+34),outline=rgba(mix(GOLD,WHITE,.5),int(200*p)),width=2)
        d.ellipse((cx-6,cy+14,cx+6,cy+26),fill=rgba(WHITE,int(220*p)))
    d.text((640,480),'the energy that moves is not the whole story',font=SUB_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(subtle_ground(fs,WARM,mix(GOLD,CRIMSON,.3),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'the ascent and the descent',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the power rises — and returns transformed',font=TERM_FONT,fill=mix(GOLD,CRIMSON,.4),anchor='mm')
    d.text((cx,145),'it spiritualizes the ordinary consciousness it descends into',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    rise=bezier((cx,cy+60),(cx-40,cy+20),(cx+40,cy-20),(cx,cy-60),60)
    reveal=partial_polyline(rise,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,mix(GOLD,CRIMSON,.4),3,120,7)
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        fall=bezier((cx,cy-60),(cx+40,cy-20),(cx-40,cy+20),(cx,cy+60),60)
        reveal2=partial_polyline(fall,p)
        if len(reveal2)>1: draw_line_glow(im,reveal2,mix(LAVENDER,GOLD_LIGHT,.5),2,80,5)
    d.text((640,480),'the descent is as important as the ascent — you bring the light back',font=SUB_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(subtle_ground(fs,NIGHT,mix(TEAL,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the three sounds',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'ciñcinī — the cricket — the bell',font=TERM_FONT,fill=mix(TEAL,GOLD_LIGHT,.5),anchor='mm')
    d.text((cx,145),'when the bell dies down, the yogin becomes the silence',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(3):
        x=320+i*300; y=cy+40
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        col=[mix(WHITE,TEAL,.4),mix(TEAL,GOLD,.5),mix(GOLD,CRIMSON,.4)][i]
        r=20+10*p
        for j in range(20):
            a=j*2*math.pi/20; xx=x+math.cos(a)*r; yy=y+math.sin(a)*r*0.6
            d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=rgba(col,int(80*p)))
        d.ellipse((x-r,y-r*0.6,x+r,y+r*0.6),outline=rgba(col,int(180*p)),width=2)
        if i==2:
            d.ellipse((x-r*0.5,y-r*0.3,x+r*0.5,y+r*0.3),fill=rgba(mix(GOLD,WHITE,.5),int(100*p)))
    d.text((640,480),'the bell-like resonance — then silence. the unsupported state.',font=SUB_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(subtle_ground(fs,DEEP,mix(LAVENDER,GOLD_LIGHT,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,85),'the body you cannot see',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'touches everything you experience',font=TERM_FONT,fill=mix(LAVENDER,GOLD_LIGHT,.5),anchor='mm')
    d.text((cx,150),'you are the light the flesh was made to contain',font=SMALL_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-28,cy-5,cx+28,cy+55),outline=rgba(mix(SLATE,LAVENDER,.4),120),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        for i in range(7):
            y=cy+10+i*5
            d.ellipse((cx-20+i*2,y,cx+20-i*2,y+4),fill=rgba(mix(C7_LIGHT[i],GOLD_LIGHT,.3),int(80*p)))
        draw_glow(im,(cx,cy+25),int(5+35*p),mix(GOLD_LIGHT,WHITE,.5),int(150*p),18)
        d.ellipse((cx-14,cy+11,cx+14,cy+39),fill=rgba(WHITE,int(220*p)))
        for i in range(12):
            a=i*2*math.pi/12; rr=60+50*p
            x=cx+math.cos(a)*rr; y=cy+25+math.sin(a)*rr*0.5
            draw_line_glow(im,[(cx,cy+25),(int(x),int(y))],mix(LAVENDER,GOLD_LIGHT,i/12),1,50,4)

SCENES=[,Scene('sb01','The Second Current','A body you have never touched, running alongside the physical.','Sūkṣma śarīra','','intro',['subtle','body','invisible'],'intro','luminous outline within physical',6.0,sc01)
Scene('sb02','Three Channels','Iḍā, piṅgalā, suṣumṇā — lunar, solar, fire.','Nāḍī','','channels',['nadi','channels','trinity'],'channels','three vertical channels with pulsations',8.0,sc02)
Scene('sb03','The Seven Cakras','Thresholds where consciousness condenses into densities.','Cakra','','cakras',['cakras','thresholds','densities'],'cakras','seven ascending wheels of colored light',8.0,sc03)
Scene('sb04','The Nāḍī Network','Wireless patterns in the prāṇic field.','Nāḍī','','network',['nadis','wireless','network'],'network','radiating lines from central channel',8.0,sc04)
Scene('sb05','Kuṇḍalinī — Three Lights','Sunlike, moonlike, firelike — illumination, deepening, absorption.','Kuṇḍalinī','','kundalini',['kundalini','light','coiled'],'kundalini','coiled serpent with three light aspects',8.0,sc05)
Scene('sb06','Static and Dynamic','The stillness that makes motion possible.','Sthira','','polarity',['static','dynamic','stillness'],'polarity','still center within dynamic field',8.0,sc06)
Scene('sb07','Ascent and Descent','Rises — then returns, transforming ordinary consciousness.','Ārohaṇa','','descent',['ascent','descent','return'],'descent','rising and falling arc of light',8.0,sc07)
Scene('sb08','Three Sounds','Ciñcinī, cricket, bell — when the bell dies, you become the silence.','Nāda','','sounds',['sounds','silence','bell'],'sounds','three sound-emitting forms, bell fading',8.0,sc08)
Scene('sb09','You Are the Light','The body you cannot see touches everything. The light the flesh contains.','Prakāśa','','seal',['light','body','contain'],'seal','radiant subtle body with radial light',8.0,sc09)
Scene('sb01','The Second Current','A body you have never touched, running alongside the physical.','Sūkṣma śarīra','','intro',['subtle','body','invisible'],'intro','luminous outline within physical',6.0,sc01)
Scene('sb02','Three Channels','Iḍā, piṅgalā, suṣumṇā — lunar, solar, fire.','Nāḍī','','channels',['nadi','channels','trinity'],'channels','three vertical channels with pulsations',8.0,sc02)
Scene('sb03','The Seven Cakras','Thresholds where consciousness condenses into densities.','Cakra','','cakras',['cakras','thresholds','densities'],'cakras','seven ascending wheels of colored light',8.0,sc03)
Scene('sb04','The Nāḍī Network','Wireless patterns in the prāṇic field.','Nāḍī','','network',['nadis','wireless','network'],'network','radiating lines from central channel',8.0,sc04)
Scene('sb05','Kuṇḍalinī — Three Lights','Sunlike, moonlike, firelike — illumination, deepening, absorption.','Kuṇḍalinī','','kundalini',['kundalini','light','coiled'],'kundalini','coiled serpent with three light aspects',8.0,sc05)
Scene('sb06','Static and Dynamic','The stillness that makes motion possible.','Sthira','','polarity',['static','dynamic','stillness'],'polarity','still center within dynamic field',8.0,sc06)
Scene('sb07','Ascent and Descent','Rises — then returns, transforming ordinary consciousness.','Ārohaṇa','','descent',['ascent','descent','return'],'descent','rising and falling arc of light',8.0,sc07)
Scene('sb08','Three Sounds','Ciñcinī, cricket, bell — when the bell dies, you become the silence.','Nāda','','sounds',['sounds','silence','bell'],'sounds','three sound-emitting forms, bell fading',8.0,sc08)
Scene('sb09','You Are the Light','The body you cannot see touches everything. The light the flesh contains.','Prakāśa','','seal',['light','body','contain'],'seal','radiant subtle body with radial light',8.0,sc09)
Scene('sb01','The Second Current','A body you have never touched, running alongside the physical.','Sūkṣma śarīra','','intro',['subtle','body','invisible'],'intro','luminous outline within physical',6.0,sc01)
Scene('sb02','Three Channels','Iḍā, piṅgalā, suṣumṇā — lunar, solar, fire.','Nāḍī','','channels',['nadi','channels','trinity'],'channels','three vertical channels with pulsations',8.0,sc02)
Scene('sb03','The Seven Cakras','Thresholds where consciousness condenses into densities.','Cakra','','cakras',['cakras','thresholds','densities'],'cakras','seven ascending wheels of colored light',8.0,sc03)
Scene('sb04','The Nāḍī Network','Wireless patterns in the prāṇic field.','Nāḍī','','network',['nadis','wireless','network'],'network','radiating lines from central channel',8.0,sc04)
Scene('sb05','Kuṇḍalinī — Three Lights','Sunlike, moonlike, firelike — illumination, deepening, absorption.','Kuṇḍalinī','','kundalini',['kundalini','light','coiled'],'kundalini','coiled serpent with three light aspects',8.0,sc05)
Scene('sb06','Static and Dynamic','The stillness that makes motion possible.','Sthira','','polarity',['static','dynamic','stillness'],'polarity','still center within dynamic field',8.0,sc06)
Scene('sb07','Ascent and Descent','Rises — then returns, transforming ordinary consciousness.','Ārohaṇa','','descent',['ascent','descent','return'],'descent','rising and falling arc of light',8.0,sc07)
Scene('sb08','Three Sounds','Ciñcinī, cricket, bell — when the bell dies, you become the silence.','Nāda','','sounds',['sounds','silence','bell'],'sounds','three sound-emitting forms, bell fading',8.0,sc08)
Scene('sb09','You Are the Light','The body you cannot see touches everything. The light the flesh contains.','Prakāśa','','seal',['light','body','contain'],'seal','radiant subtle body with radial light',8.0,sc09)
    Scene('sb01','The Second Current','A body you have never touched, running alongside the physical.','Sūkṣma śarīra','','intro',['subtle','body','invisible'],'intro','luminous outline within physical',6.0,sc01),
    Scene('sb02','Three Channels','Iḍā, piṅgalā, suṣumṇā — lunar, solar, fire.','Nāḍī','','channels',['nadi','channels','trinity'],'channels','three vertical channels with pulsations',8.0,sc02),
    Scene('sb03','The Seven Cakras','Thresholds where consciousness condenses into densities.','Cakra','','cakras',['cakras','thresholds','densities'],'cakras','seven ascending wheels of colored light',8.0,sc03),
    Scene('sb04','The Nāḍī Network','Wireless patterns in the prāṇic field.','Nāḍī','','network',['nadis','wireless','network'],'network','radiating lines from central channel',8.0,sc04),
    Scene('sb05','Kuṇḍalinī — Three Lights','Sunlike, moonlike, firelike — illumination, deepening, absorption.','Kuṇḍalinī','','kundalini',['kundalini','light','coiled'],'kundalini','coiled serpent with three light aspects',8.0,sc05),
    Scene('sb06','Static and Dynamic','The stillness that makes motion possible.','Sthira','','polarity',['static','dynamic','stillness'],'polarity','still center within dynamic field',8.0,sc06),
    Scene('sb07','Ascent and Descent','Rises — then returns, transforming ordinary consciousness.','Ārohaṇa','','descent',['ascent','descent','return'],'descent','rising and falling arc of light',8.0,sc07),
    Scene('sb08','Three Sounds','Ciñcinī, cricket, bell — when the bell dies, you become the silence.','Nāda','','sounds',['sounds','silence','bell'],'sounds','three sound-emitting forms, bell fading',8.0,sc08),
    Scene('sb09','You Are the Light','The body you cannot see touches everything. The light the flesh contains.','Prakāśa','','seal',['light','body','contain'],'seal','radiant subtle body with radial light',8.0,sc09),
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
        dust(im,SEED+hash(scene.id)%10000+i,50)
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DEEP)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Sūkṣma Śarīra — The Body You Cannot See',
        'source_basis':'Expansion Essay 18: "the body you cannot see" — 9 scenes.',
        'style':{'family':'subtle body / cakra visualization','background':'deep night','ink':'seven cakra colors, lavender, gold'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Subtle Body — 9 scenes, chakra/iridescent palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Subtle Body Pack — seven-cakra / iridescent palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Sūkṣma Śarīra — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'subtle_body_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'subtle_body_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['subtle_body_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'subtle_body_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
