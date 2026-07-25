#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=13130

DARK_LAB=(14,12,14); WARM_DARK=(20,18,18); DEEP=(12,12,18)
LEAD=(55,50,55); QUICKSILVER=(180,190,200); MOLTEN=(220,140,50)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); EMERALD=(60,140,100)
EMERALD_LIGHT=(130,205,155); CRIMSON=(154,44,58); ROSE_GOLD=(210,170,145)
SILVER=(196,204,222); WHITE=(252,250,246); PEARL=(246,243,236)
SLATE=(90,100,120); MIST=(160,172,192); TEAL=(92,146,148)
FLAME=(210,120,40); AMBER=(200,150,60); VIOLET=(120,104,168)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA='/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30)
SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21)
SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

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

def draw_rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        d.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    d.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(GOLD,EMERALD,.5),80),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(GOLD,EMERALD,.3),50),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,CRIMSON,mix(GOLD,AMBER,.5))

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,10,14,200),outline=rgba(mix(GOLD,EMERALD,.4),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,AMBER,.5))

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(mix(QUICKSILVER,AMBER,.3),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def alchemy_ground(seed,bg,glow_col,intensity=0.5):
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
    fs=SEED+int(t*9973)%100000; im.paste(alchemy_ground(fs,DARK_LAB,MOLTEN,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the alchemists were trying',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'to turn matter into light',font=TERM_FONT,fill=mix(MOLTEN,GOLD_LIGHT,.6),anchor='mm')
    prog=ease_in_out(t)
    for i in range(4):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        x=cx-100+i*67; y=cy+40
        sz=20+10*p
        col=mix(LEAD,GOLD,i/4)
        d.ellipse((x-sz,y-sz,x+sz,y+sz),fill=rgba(col,int(180*p)),outline=rgba(mix(col,GOLD_LIGHT,.3),int(200*p)),width=2)
        if i==3:
            draw_glow(im,(x,y),20,mix(GOLD_LIGHT,WHITE,.3),int(120*p),12)
            d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(WHITE,int(220*p)))
        d.text((x,y+sz+12),['lead','tin','copper','gold'][i],font=TINY_FONT,fill=rgba(mix(col,GOLD_LIGHT,.2),int(200*p)),anchor='mm')

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(alchemy_ground(fs,DEEP,EMERALD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the emerald tablet',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'that which is below is like that which is above',font=TERM_FONT,fill=EMERALD_LIGHT,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((350,170,930,390),radius=12,outline=rgba(EMERALD,int(180*prog)),width=2)
    lines=['that which is below','is like that which is above','and that which is above','is like that which is below','to accomplish the miracles','of one thing']
    for i,l in enumerate(lines):
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        d.text((640,200+i*28),l,font=TINY_FONT,fill=rgba(mix(EMERALD_LIGHT,PEARL,i/6),int(200*p)),anchor='mm')
    lines_above=[(cx-80,195),(cx+60,215),(cx-40,235)]
    lines_below=[(cx+80,325),(cx-60,345),(cx+40,365)]
    for (x1,y1),(x2,y2) in zip(lines_above,lines_below):
        draw_line_glow(im,[(x1,y1),(x2,y2)],EMERALD,1,50,3)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(alchemy_ground(fs,WARM_DARK,QUICKSILVER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'virgin mercury',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'yields to nothing but love',font=TERM_FONT,fill=mix(QUICKSILVER,GOLD_LIGHT,.5),anchor='mm')
    d.text((cx,145),'she is no animal, no vegetable, no mineral — she is the mother of them all',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for i in range(60):
        u=i/59; x=cx-200+u*400
        y=cy+50+40*math.sin(u*3+t*2)*prog
        col=mix(QUICKSILVER,mix(AMBER,PEARL,.3),0.3+0.7*(0.5+0.5*math.sin(u*2+t)))
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(col,int(100*prog)))
    draw_glow(im,(cx,cy+50),20,mix(QUICKSILVER,GOLD_LIGHT,.5),int(80*prog),14)
    d.ellipse((cx-40,cy+30,cx+40,cy+70),outline=rgba(mix(QUICKSILVER,GOLD_LIGHT,.3),int(160*prog)),width=2)

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(alchemy_ground(fs,DARK_LAB,AMBER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'body, soul, and spirit',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'one thing — equally present',font=TERM_FONT,fill=mix(AMBER,GOLD_LIGHT,.6),anchor='mm')
    prog=ease_in_out(t)
    cols=[mix(AMBER,CRIMSON,.3),mix(TEAL,GOLD,.5),mix(VIOLET,PEARL,.4)]
    labels=['body','soul','spirit']
    for i in range(3):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        a=-math.pi/2+i*2*math.pi/3
        x=cx+math.cos(a)*100; y=cy+math.sin(a)*100*0.6
        rr=40+8*math.sin(t+i)
        d.ellipse((x-rr,y-rr*0.7,x+rr,y+rr*0.7),outline=rgba(cols[i],int(190*p)),width=2)
        d.text((x,y),labels[i],font=SMALL_FONT,fill=rgba(cols[i],int(200*p)),anchor='mm')
    draw_glow(im,(cx,cy),18,mix(GOLD_LIGHT,WHITE,.5),int(100*prog),12)
    d.ellipse((cx-7,cy-7,cx+7,cy+7),fill=rgba(WHITE,int(220*prog)))

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(alchemy_ground(fs,DARK_LAB,MOLTEN,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'blake\'s printing house',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'six chambers of transformation',font=TERM_FONT,fill=mix(MOLTEN,GOLD,.7),anchor='mm')
    chambers=['dragon','viper','eagle','lions','forms','books']
    c_cols=[SLATE,TEAL,GOLD,MOLTEN,VIOLET,mix(GOLD,EMERALD,.5)]
    prog=smoothstep(0.05,0.9,t)
    for i in range(6):
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        x=180+i*160
        d.rounded_rectangle((x-55,180,x+55,340),radius=8,outline=rgba(c_cols[i],int(170*p)),width=2)
        d.text((x,210),chambers[i],font=SMALL_FONT,fill=rgba(mix(c_cols[i],PEARL,.3),int(200*p)),anchor='mm')
        if i<5:
            pts=partial_polyline([(x+55,260),(x+105,260)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(c_cols[i],c_cols[i+1],.5),1,60,3)
    d.text((640,480),'clearing away false certainties → fluid possibilities → transformed perception',font=TINY_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(alchemy_ground(fs,WARM_DARK,TEAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'make water of earth',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'and earth of water',font=TERM_FONT,fill=mix(TEAL,GOLD,.6),anchor='mm')
    d.text((cx,150),'dissolve the fixed — fix the volatile',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    rx=lerp(20,70,abs(0.5-t)*2)
    ry=20
    col1=mix(LEAD,TEAL,0.3+0.3*math.sin(t*2))
    col2=mix(TEAL,SLATE,0.3+0.3*math.cos(t*2))
    draw_glow(im,(cx-80,cy+40),15,mix(col1,GOLD_LIGHT,.3),int(80*(0.5+0.5*math.sin(t*2))),10)
    d.ellipse((cx-80-rx,cy+40-ry,cx-80+rx,cy+40+ry),fill=rgba(col1,int(200*prog)))
    rx2=lerp(70,20,abs(0.5-t)*2)
    draw_glow(im,(cx+80,cy+40),15,mix(col2,GOLD_LIGHT,.3),int(80*(0.5+0.5*math.cos(t*2))),10)
    d.ellipse((cx+80-rx2,cy+40-ry,cx+80+rx2,cy+40+ry),fill=rgba(col2,int(200*prog)))
    draw_line_glow(im,[(cx-70,cy+40),(cx+70,cy+40)],mix(TEAL,AMBER,.5),2,80,6)

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(alchemy_ground(fs,DARK_LAB,CRIMSON,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'without contraries',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'no progression',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.5),anchor='mm')
    d.text((cx,145),'the goal: hold them together until they generate a third',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    dx=lerp(60,20,prog)
    d.ellipse((cx-60-dx,cy+20-30,cx-60+dx,cy+20+30),outline=rgba(mix(CRIMSON,GOLD,.3),int(180*prog)),width=2)
    d.text((cx-60,cy+70),'reason',font=TINY_FONT,fill=rgba(mix(CRIMSON,PEARL,.3),int(180*prog)),anchor='mm')
    d.ellipse((cx+60-dx,cy+20-30,cx+60+dx,cy+20+30),outline=rgba(mix(TEAL,GOLD,.5),int(180*prog)),width=2)
    d.text((cx+60,cy+70),'energy',font=TINY_FONT,fill=rgba(mix(TEAL,PEARL,.3),int(180*prog)),anchor='mm')
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        draw_glow(im,(cx,cy+20),15,mix(GOLD_LIGHT,WHITE,.5),int(120*p),12)
        d.ellipse((cx-8,cy+12,cx+8,cy+28),fill=rgba(WHITE,int(220*p)))
        d.text((cx,cy+60),'the child of the philosophers',font=TINY_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(alchemy_ground(fs,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'the supercelestial marriage',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'soul and body reconciled',font=TERM_FONT,fill=mix(GOLD,ROSE_GOLD,.6),anchor='mm')
    d.text((cx,150),'the spirit and the flesh unified — not one destroyed for the other',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    x1=lerp(400,600,prog); x2=lerp(880,680,prog)
    draw_glow(im,(int(x1),cy+25),25,mix(GOLD,CRIMSON,.3),int(100*prog),14)
    d.ellipse((int(x1)-15,cy+10,int(x1)+15,cy+40),outline=rgba(mix(GOLD,CRIMSON,.3),int(180*prog)),width=2)
    draw_glow(im,(int(x2),cy+25),25,mix(ROSE_GOLD,GOLD_LIGHT,.5),int(100*prog),14)
    d.ellipse((int(x2)-15,cy+10,int(x2)+15,cy+40),outline=rgba(mix(ROSE_GOLD,GOLD_LIGHT,.5),int(180*prog)),width=2)
    if abs(x1-x2)<40:
        draw_glow(im,(cx,cy+25),30,mix(GOLD_LIGHT,WHITE,.5),int(140*prog),16)
        d.ellipse((cx-12,cy+13,cx+12,cy+37),fill=rgba(WHITE,int(220*prog)))

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(alchemy_ground(fs,DARK_LAB,GOLD,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'the philosophers\' stone',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'a state you can become',font=TERM_FONT,fill=mix(GOLD,EMERALD_LIGHT,.6),anchor='mm')
    d.text((cx,150),'not a thing you can hold',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for r in [30,50,70,90]:
        d.ellipse((cx-r,cy-r*0.62,cx+r,cy+r*0.62),outline=rgba(mix(LEAD,GOLD,0.2+0.8*prog),120),width=1)
    draw_glow(im,(cx,cy),int(10+35*prog),mix(GOLD_LIGHT,EMERALD_LIGHT,.5),int(150*prog),18)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,int(255*prog)),outline=rgba(mix(GOLD,EMERALD,.7),int(200*prog)),width=2)

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(alchemy_ground(fs,DARK_LAB,MOLTEN,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,85),'you are the furnace',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the fire is already lit',font=TERM_FONT,fill=mix(MOLTEN,GOLD_LIGHT,.6),anchor='mm')
    d.text((cx,145),'the work is underway — the only question is whether you will tend it',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-25,cy+10,cx+25,cy+55),outline=rgba(mix(SLATE,LEAD,.5),120),width=2)
    d.line((cx,cy+55,cx,cy+110),fill=rgba(mix(SLATE,LEAD,.3),100),width=2)
    d.line((cx,cy+30,cx-45,cy+70),fill=rgba(mix(SLATE,LEAD,.3),80),width=2)
    d.line((cx,cy+30,cx+45,cy+70),fill=rgba(mix(SLATE,LEAD,.3),80),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        draw_glow(im,(cx,cy+30),int(10+30*p),mix(MOLTEN,GOLD,.5),int(130*p),16)
        pts=[(cx,cy+20-30*p),(cx-20,cy+25-5*p),(cx-8,cy+30+5*p),(cx+12,cy+28),(cx+22,cy+22)]
        d.polygon(pts,fill=rgba(mix(MOLTEN,GOLD,.5),int(60*p)),outline=rgba(mix(MOLTEN,GOLD,.7),int(180*p)))

SCENES=[,Scene('al01','Turning Matter Into Light','Lead, tin, copper — gold is what matter becomes when purified.','Opus','','opening',['matter','light','gold'],'intro','four metals progressing from lead to gold',6.0,sc01)
Scene('al02','The Emerald Tablet','As above, so below — the founding axiom.','Tabula smaragdina','','axiom',['above','below','mirror'],'axiom','emerald text with mirrored lines',8.0,sc02)
Scene('al03','Virgin Mercury','Yields to nothing but love — the raw material of transformation.','Mercurius virginum','','potential',['mercury','potential','love'],'potential','fluid silver responding to warmth',8.0,sc03)
Scene('al04','Body, Soul, Spirit','One thing — equally present at the same time.','Tria prima','','triune',['body','soul','spirit'],'structure','three interlocking circles',8.0,sc04)
Scene('al05','The Printing House','Six chambers — from dragon to books.','Officina','','chambers',['chambers','transformation','blake'],'chambers','six chambers with sequential processing',8.0,sc05)
Scene('al06','Water of Earth','Dissolve the fixed — fix the volatile.','Solutio et coagulatio','','operations',['dissolve','fix','rhythm'],'operations','solid becoming fluid and back',8.0,sc06)
Scene('al07','Without Contraries','Hold opposites together until they generate a third.','Coincidentia oppositorum','','contraries',['opposites','third','marriage'],'opposites','two opposites converging to a third',8.0,sc07)
Scene('al08','Supercelestial Marriage','Soul and body reconciled — eternal marriage.','Coniunctio','','marriage',['marriage','union','reconciliation'],'marriage','two forms merging into one luminous being',8.0,sc08)
Scene('al09','The Philosophers\' Stone','A state you can become — not a thing you hold.','Lapis philosophorum','','stone',['stone','state','becoming'],'stone','dark matter becoming radiant gem',6.0,sc09)
Scene('al10','You Are the Furnace','The fire is already lit — will you tend it?','Opus continuus','','seal',['furnace','fire','work'],'seal','human silhouette containing furnace fire',8.0,sc10)
Scene('al01','Turning Matter Into Light','Lead, tin, copper — gold is what matter becomes when purified.','Opus','','opening',['matter','light','gold'],'intro','four metals progressing from lead to gold',6.0,sc01)
Scene('al02','The Emerald Tablet','As above, so below — the founding axiom.','Tabula smaragdina','','axiom',['above','below','mirror'],'axiom','emerald text with mirrored lines',8.0,sc02)
Scene('al03','Virgin Mercury','Yields to nothing but love — the raw material of transformation.','Mercurius virginum','','potential',['mercury','potential','love'],'potential','fluid silver responding to warmth',8.0,sc03)
Scene('al04','Body, Soul, Spirit','One thing — equally present at the same time.','Tria prima','','triune',['body','soul','spirit'],'structure','three interlocking circles',8.0,sc04)
Scene('al05','The Printing House','Six chambers — from dragon to books.','Officina','','chambers',['chambers','transformation','blake'],'chambers','six chambers with sequential processing',8.0,sc05)
Scene('al06','Water of Earth','Dissolve the fixed — fix the volatile.','Solutio et coagulatio','','operations',['dissolve','fix','rhythm'],'operations','solid becoming fluid and back',8.0,sc06)
Scene('al07','Without Contraries','Hold opposites together until they generate a third.','Coincidentia oppositorum','','contraries',['opposites','third','marriage'],'opposites','two opposites converging to a third',8.0,sc07)
Scene('al08','Supercelestial Marriage','Soul and body reconciled — eternal marriage.','Coniunctio','','marriage',['marriage','union','reconciliation'],'marriage','two forms merging into one luminous being',8.0,sc08)
Scene('al09','The Philosophers\' Stone','A state you can become — not a thing you hold.','Lapis philosophorum','','stone',['stone','state','becoming'],'stone','dark matter becoming radiant gem',6.0,sc09)
Scene('al10','You Are the Furnace','The fire is already lit — will you tend it?','Opus continuus','','seal',['furnace','fire','work'],'seal','human silhouette containing furnace fire',8.0,sc10)
Scene('al01','Turning Matter Into Light','Lead, tin, copper — gold is what matter becomes when purified.','Opus','','opening',['matter','light','gold'],'intro','four metals progressing from lead to gold',6.0,sc01)
Scene('al02','The Emerald Tablet','As above, so below — the founding axiom.','Tabula smaragdina','','axiom',['above','below','mirror'],'axiom','emerald text with mirrored lines',8.0,sc02)
Scene('al03','Virgin Mercury','Yields to nothing but love — the raw material of transformation.','Mercurius virginum','','potential',['mercury','potential','love'],'potential','fluid silver responding to warmth',8.0,sc03)
Scene('al04','Body, Soul, Spirit','One thing — equally present at the same time.','Tria prima','','triune',['body','soul','spirit'],'structure','three interlocking circles',8.0,sc04)
Scene('al05','The Printing House','Six chambers — from dragon to books.','Officina','','chambers',['chambers','transformation','blake'],'chambers','six chambers with sequential processing',8.0,sc05)
Scene('al06','Water of Earth','Dissolve the fixed — fix the volatile.','Solutio et coagulatio','','operations',['dissolve','fix','rhythm'],'operations','solid becoming fluid and back',8.0,sc06)
Scene('al07','Without Contraries','Hold opposites together until they generate a third.','Coincidentia oppositorum','','contraries',['opposites','third','marriage'],'opposites','two opposites converging to a third',8.0,sc07)
Scene('al08','Supercelestial Marriage','Soul and body reconciled — eternal marriage.','Coniunctio','','marriage',['marriage','union','reconciliation'],'marriage','two forms merging into one luminous being',8.0,sc08)
Scene('al09','The Philosophers\' Stone','A state you can become — not a thing you hold.','Lapis philosophorum','','stone',['stone','state','becoming'],'stone','dark matter becoming radiant gem',6.0,sc09)
Scene('al10','You Are the Furnace','The fire is already lit — will you tend it?','Opus continuus','','seal',['furnace','fire','work'],'seal','human silhouette containing furnace fire',8.0,sc10)
    Scene('al01','Turning Matter Into Light','Lead, tin, copper — gold is what matter becomes when purified.','Opus','','opening',['matter','light','gold'],'intro','four metals progressing from lead to gold',6.0,sc01),
    Scene('al02','The Emerald Tablet','As above, so below — the founding axiom.','Tabula smaragdina','','axiom',['above','below','mirror'],'axiom','emerald text with mirrored lines',8.0,sc02),
    Scene('al03','Virgin Mercury','Yields to nothing but love — the raw material of transformation.','Mercurius virginum','','potential',['mercury','potential','love'],'potential','fluid silver responding to warmth',8.0,sc03),
    Scene('al04','Body, Soul, Spirit','One thing — equally present at the same time.','Tria prima','','triune',['body','soul','spirit'],'structure','three interlocking circles',8.0,sc04),
    Scene('al05','The Printing House','Six chambers — from dragon to books.','Officina','','chambers',['chambers','transformation','blake'],'chambers','six chambers with sequential processing',8.0,sc05),
    Scene('al06','Water of Earth','Dissolve the fixed — fix the volatile.','Solutio et coagulatio','','operations',['dissolve','fix','rhythm'],'operations','solid becoming fluid and back',8.0,sc06),
    Scene('al07','Without Contraries','Hold opposites together until they generate a third.','Coincidentia oppositorum','','contraries',['opposites','third','marriage'],'opposites','two opposites converging to a third',8.0,sc07),
    Scene('al08','Supercelestial Marriage','Soul and body reconciled — eternal marriage.','Coniunctio','','marriage',['marriage','union','reconciliation'],'marriage','two forms merging into one luminous being',8.0,sc08),
    Scene('al09','The Philosophers\' Stone','A state you can become — not a thing you hold.','Lapis philosophorum','','stone',['stone','state','becoming'],'stone','dark matter becoming radiant gem',6.0,sc09),
    Scene('al10','You Are the Furnace','The fire is already lit — will you tend it?','Opus continuus','','seal',['furnace','fire','work'],'seal','human silhouette containing furnace fire',8.0,sc10),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DARK_LAB)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Alchemy — The Secret Life of Matter',
        'source_basis':'Expansion Essay 13: "the secret life of matter" — 10 scenes.',
        'style':{'family':'alchemical / laboratory visualization','background':'dark lab','ink':'molten gold, quicksilver, emerald, lead'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Alchemy — 10 scenes, laboratory/furnace palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Alchemy Pack — molten/quicksilver/emerald/lead palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Alchemy — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'alchemy_matter_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'alchemy_matter_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['alchemy_matter_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'alchemy_matter_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
