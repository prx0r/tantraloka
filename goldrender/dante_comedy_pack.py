#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=23230

DARK=(10,8,12); WARM=(20,14,12); NIGHT=(14,12,18); PURPLE=(18,12,22)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246); PEARL=(246,243,236)
SILVER=(196,204,222); CRIMSON=(154,44,58); CORAL=(206,108,100); TEAL=(92,146,148)
INDIGO=(68,78,136); VIOLET=(120,104,168); SLATE=(90,100,120); MIST=(160,172,192)
LAVENDER=(170,156,200); FLAME=(220,120,40); ROSE=(196,104,130)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'; FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA='/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
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
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(GOLD,LAVENDER,.4),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(GOLD,LAVENDER,.2),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,CRIMSON,mix(GOLD,LAVENDER,.5))

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(10,8,14,200),outline=rgba(mix(GOLD,LAVENDER,.3),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,LAVENDER,.5))

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.5)); c=mix(mix(SILVER,LAVENDER,.5),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def dante_ground(seed,bg,glow_col,intensity=0.4):
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
    fs=SEED+int(t*9973)%100000; im.paste(dante_ground(fs,DARK,mix(CRIMSON,GOLD,.2),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'halfway through life',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'dante finds himself in a dark wood',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.4),anchor='mm')
    d.text((cx,150),'he has no idea where he is going',font=SMALL_FONT,fill=mix(MIST,CRIMSON,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(12):
        a=i*2*math.pi/12; r=140+20*math.sin(t*2+i)
        x=cx+math.cos(a)*r; y=cy+30+math.sin(a)*r*0.55
        d.line((x,y,x+10*math.cos(a),y+10*math.sin(a)),fill=rgba(mix(CRIMSON,SLATE,.3),int(80*prog)),width=2)
    draw_glow(im,(cx,cy+30),12,mix(GOLD,WHITE,.3),int(80*prog),10)
    d.ellipse((cx-5,cy+25,cx+5,cy+35),fill=rgba(WHITE,int(180*prog)))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(dante_ground(fs,DARK,mix(CRIMSON,FLAME,.4),0.5),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'inferno — nine circles',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'each step downward is a layer of skin peeled back',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.4),anchor='mm')
    d.text((cx,140),'from the lustful blown by winds to the treacherous locked in ice',font=SMALL_FONT,fill=mix(MIST,CRIMSON,.4),anchor='mm')
    circles=['limbo','lust','gluttony','greed','wrath','heresy','violence','fraud','treachery']
    c_cols=[SLATE,CRIMSON,CORAL,FLAME,INDIGO,VIOLET,TEAL,SLATE,DARK]
    prog=smoothstep(0.05,0.92,t)
    for i in range(9):
        p=clamp(prog*1.3-i*0.05)
        if p<=0: continue
        y=int(lerp(400,180,i/8*prog))
        sz=14-abs(i-4)
        d.ellipse((cx-sz,y-sz,cx+sz,y+sz),outline=rgba(mix(c_cols[i],GOLD,.2),int(170*p)),width=2)
        d.text((cx+sz+18,y-4),circles[i],font=TINY_FONT,fill=rgba(mix(c_cols[i],GOLD,.3),int(180*p)),anchor='lm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(dante_ground(fs,WARM,mix(GOLD,SILVER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'virgil — the guide',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'a lantern that can illuminate what is already there',font=TERM_FONT,fill=mix(GOLD,SILVER,.5),anchor='mm')
    d.text((cx,150),'he can name every sin — but cannot show what has no shape',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx-80,cy+40),15,mix(GOLD,SILVER,.5),int(100*prog),10)
    d.ellipse((cx-80-12,cy+28,cx-80+12,cy+52),outline=rgba(mix(GOLD,SILVER,.5),int(170*prog)),width=2)
    draw_glow(im,(cx+80,cy+40),18,mix(GOLD,WHITE,.4),int(120*prog),12)
    d.ellipse((cx+80-14,cy+26,cx+80+14,cy+54),outline=rgba(mix(GOLD,WHITE,.4),int(190*prog)),width=2)
    d.line((cx-66,cy+40,cx+64,cy+40),fill=rgba(mix(GOLD,SILVER,.4),int(120*prog)),width=2)
    d.text((640,485),'reason takes you to the edge of the knowable',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(dante_ground(fs,WARM,mix(TEAL,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'purgatory — seven terraces',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'a mountain ringed by fire — each terrace dissolves a sheath',font=TERM_FONT,fill=mix(TEAL,GOLD,.5),anchor='mm')
    d.text((cx,140),'pride, envy, wrath, sloth, avarice, gluttony, lust',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    sins=['pride','envy','wrath','sloth','avarice','gluttony','lust']
    s_cols=[GOLD,TEAL,CRIMSON,SLATE,INDIGO,CORAL,ROSE]
    prog=smoothstep(0.05,0.88,t)
    for i in range(7):
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        y=180+i*35
        d.line((cx-80,y,cx+80,y),fill=rgba(s_cols[i],int(180*p)),width=2)
        d.text((cx-90,y-4),sins[i],font=TINY_FONT,fill=rgba(s_cols[i],int(200*p)),anchor='rm')

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(dante_ground(fs,PURPLE,mix(ROSE,GOLD,.5),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'beatrice — the beloved who reveals',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'she leads by being seen',font=TERM_FONT,fill=mix(ROSE,GOLD,.6),anchor='mm')
    d.text((cx,150),'to be seen by her is to see yourself for the first time',font=SMALL_FONT,fill=mix(MIST,ROSE,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+40),25,mix(ROSE,GOLD,.5),int(130*prog),16)
    d.ellipse((cx-12,cy+25,cx+12,cy+55),outline=rgba(mix(ROSE,GOLD,.5),int(190*prog)),width=2)
    d.ellipse((cx-5,cy+36,cx+5,cy+44),fill=rgba(WHITE,int(220*prog)))
    for i in range(8):
        a=i*2*math.pi/8; r=60+50*prog
        x=cx+math.cos(a+prog)*r; y=cy+40+math.sin(a+prog)*r*0.5
        draw_line_glow(im,[(cx,cy+40),(int(x),int(y))],mix(ROSE,GOLD,.3),1,50,4)

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(dante_ground(fs,DARK,mix(GOLD,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'paradise — nine spheres of light',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'each sphere strips another layer of separation',font=TERM_FONT,fill=mix(GOLD,LAVENDER,.5),anchor='mm')
    d.text((cx,140),'beatrice grows brighter — dante grows lighter',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    spheres=['moon','mercury','venus','sun','mars','jupiter','saturn','fixed stars','primum mobile']
    s_cols=[SILVER,TEAL,ROSE,GOLD,CORAL,LAVENDER,INDIGO,WHITE,mix(GOLD,WHITE,.6)]
    prog=smoothstep(0.05,0.92,t)
    for i in range(9):
        p=clamp(prog*1.3-i*0.04)
        if p<=0: continue
        r=30+i*18
        d.ellipse((cx-r,cy+20-r*0.6,cx+r,cy+20+r*0.6),outline=rgba(s_cols[i],int(150*p)),width=2)
        d.text((cx+r+16,cy+18-4),spheres[i],font=TINY_FONT,fill=rgba(s_cols[i],int(180*p)),anchor='lm')
    draw_glow(im,(cx,cy+20),10,mix(GOLD,WHITE,.5),80,8)

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(dante_ground(fs,PURPLE,mix(ROSE,GOLD,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the celestial rose',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a vast rose of living petals — each petal a face, each face a star',font=TERM_FONT,fill=mix(ROSE,GOLD,.5),anchor='mm')
    d.text((cx,145),'consciousness recognizing itself as all that is',font=SMALL_FONT,fill=mix(MIST,ROSE,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(24):
        a=i*2*math.pi/24; r=lerp(5,150,prog)
        x=cx+math.cos(a)*r; y=cy+25+math.sin(a)*r*0.55
        col=mix(ROSE,GOLD,i/24)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,int(100+80*prog)))
    for r in [50,90,130]:
        d.ellipse((cx-r,cy+25-r*0.55,cx+r,cy+25+r*0.55),outline=rgba(mix(ROSE,GOLD,.3),int(80*prog)),width=1)
    draw_glow(im,(cx,cy+25),20,mix(GOLD,WHITE,.5),int(130*prog),14)
    d.ellipse((cx-8,cy+17,cx+8,cy+33),fill=rgba(WHITE,int(255*prog)))

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(dante_ground(fs,DARK,mix(GOLD,WHITE,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the final flash',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a love that moves the sun and other stars',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,145),'no method left — no guide, no ladder, no steps',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    r=lerp(3,250,prog)
    draw_glow(im,(cx,cy),int(r),mix(GOLD,WHITE,.5),int(200*prog),35)
    d.ellipse((cx-int(r*0.4),cy-int(r*0.3),cx+int(r*0.4),cy+int(r*0.3)),fill=rgba(WHITE,int(200*prog)))
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        d.text((cx,cy+60),'the love that has been seeking you',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')
        d.text((cx,cy+84),'since before time began',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(dante_ground(fs,WARM,mix(GOLD,TEAL,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'three movements of one music',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'first: you try — second: you are helped — third: you disappear',font=TERM_FONT,fill=mix(GOLD,TEAL,.5),anchor='mm')
    d.text((cx,145),'inferno = individual effort, purgatory = grace, paradise = direct recognition',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    movements=['inferno','purgatory','paradise']
    m_cols=[CRIMSON,TEAL,mix(GOLD,WHITE,.6)]
    prog=smoothstep(0.05,0.85,t)
    for i in range(3):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        x=300+i*310; y=cy+35
        sz=20+10*p
        d.ellipse((x-sz,y-sz,x+sz,y+sz),outline=rgba(m_cols[i],int(180*p)),width=2)
        d.text((x,y),movements[i],font=SMALL_FONT,fill=rgba(m_cols[i],int(200*p)),anchor='mm')
        if i<2:
            pts=partial_polyline([(x+sz+5,y),(x+310-sz-5,y)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(m_cols[i],m_cols[i+1],.5),2,70,5)
    d.text((640,480),'the dark wood and the morning star are the same place, seen from opposite ends',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(dante_ground(fs,PURPLE,mix(GOLD,WHITE,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,85),'you are the journey',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the guide through the fire is you',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,145),'the beloved at the summit is you',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,175),'the love that turns the will — is what you are when every mask falls away',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(18):
        a=i*2*math.pi/18; r=lerp(10,180,prog)
        x=cx+math.cos(a)*r; y=cy+10+math.sin(a)*r*0.6
        draw_line_glow(im,[(cx,cy+10),(int(x),int(y))],mix(GOLD,LAVENDER,i/18),1,50,4)
    draw_glow(im,(cx,cy+10),25,mix(GOLD,WHITE,.5),int(130*prog),14)
    d.ellipse((cx-10,cy,cx+10,cy+20),fill=rgba(WHITE,int(255*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    d.text((cx,cy+10),'io',font=TERM_FONT,fill=GOLD,anchor='mm')

SCENES=[,Scene('dc01','The Dark Wood','Halfway through life — lost, with no idea where he is going.','Selva oscura','','opening',['dark','wood','lost'],'intro','dark forest with distant light',6.0,sc01)
Scene('dc02','Inferno — Nine Circles','Each step downward — a layer of skin peeled back.','Inferno','','hell',['hell','circles','descent'],'hell','nine descending rings of fire and ice',8.0,sc02)
Scene('dc03','Virgil — The Lantern','Reason — a lantern illuminating what is already there.','Virgilio','','guide',['guide','reason','limits'],'guide','two figures, lantern between them',8.0,sc03)
Scene('dc04','Purgatory — Seven Terraces','A mountain ringed by fire — each terrace dissolves a sheath.','Purgatorio','','purification',['purgatory','terraces','purification'],'purification','seven ascending terraces of fire',8.0,sc04)
Scene('dc05','Beatrice — The Beloved','She leads by being seen — to see her is to see yourself.','Beatrice','','love',['beatrice','beloved','revelation'],'revelation','radiant feminine figure with rays',8.0,sc05)
Scene('dc06','Paradise — Nine Spheres','Each sphere strips another layer of separation.','Paradiso','','heaven',['paradise','spheres','ascent'],'ascent','nine expanding concentric rings',8.0,sc06)
Scene('dc07','The Celestial Rose','A vast rose of living petals — all as one.','Rosa celeste','','vision',['rose','unity','recognition'],'unity','rose mandala of faces and stars',8.0,sc07)
Scene('dc08','The Final Flash','A love that moves the sun — no method left.','Fulgore','','direct',['flash','love','recognition'],'recognition','expanding radiance overwhelming all',10.0,sc08)
Scene('dc09','Three Movements','Try — be helped — disappear.','Triforme','','structure',['hell','purgatory','paradise'],'structure','three linked circles with path',8.0,sc09)
Scene('dc10','You Are the Journey','The guide, the beloved, the love — all you.','Unus','','seal',['self','journey','recognition'],'seal','radial self-recognition mandala',8.0,sc10)
Scene('dc01','The Dark Wood','Halfway through life — lost, with no idea where he is going.','Selva oscura','','opening',['dark','wood','lost'],'intro','dark forest with distant light',6.0,sc01)
Scene('dc02','Inferno — Nine Circles','Each step downward — a layer of skin peeled back.','Inferno','','hell',['hell','circles','descent'],'hell','nine descending rings of fire and ice',8.0,sc02)
Scene('dc03','Virgil — The Lantern','Reason — a lantern illuminating what is already there.','Virgilio','','guide',['guide','reason','limits'],'guide','two figures, lantern between them',8.0,sc03)
Scene('dc04','Purgatory — Seven Terraces','A mountain ringed by fire — each terrace dissolves a sheath.','Purgatorio','','purification',['purgatory','terraces','purification'],'purification','seven ascending terraces of fire',8.0,sc04)
Scene('dc05','Beatrice — The Beloved','She leads by being seen — to see her is to see yourself.','Beatrice','','love',['beatrice','beloved','revelation'],'revelation','radiant feminine figure with rays',8.0,sc05)
Scene('dc06','Paradise — Nine Spheres','Each sphere strips another layer of separation.','Paradiso','','heaven',['paradise','spheres','ascent'],'ascent','nine expanding concentric rings',8.0,sc06)
Scene('dc07','The Celestial Rose','A vast rose of living petals — all as one.','Rosa celeste','','vision',['rose','unity','recognition'],'unity','rose mandala of faces and stars',8.0,sc07)
Scene('dc08','The Final Flash','A love that moves the sun — no method left.','Fulgore','','direct',['flash','love','recognition'],'recognition','expanding radiance overwhelming all',10.0,sc08)
Scene('dc09','Three Movements','Try — be helped — disappear.','Triforme','','structure',['hell','purgatory','paradise'],'structure','three linked circles with path',8.0,sc09)
Scene('dc10','You Are the Journey','The guide, the beloved, the love — all you.','Unus','','seal',['self','journey','recognition'],'seal','radial self-recognition mandala',8.0,sc10)
Scene('dc01','The Dark Wood','Halfway through life — lost, with no idea where he is going.','Selva oscura','','opening',['dark','wood','lost'],'intro','dark forest with distant light',6.0,sc01)
Scene('dc02','Inferno — Nine Circles','Each step downward — a layer of skin peeled back.','Inferno','','hell',['hell','circles','descent'],'hell','nine descending rings of fire and ice',8.0,sc02)
Scene('dc03','Virgil — The Lantern','Reason — a lantern illuminating what is already there.','Virgilio','','guide',['guide','reason','limits'],'guide','two figures, lantern between them',8.0,sc03)
Scene('dc04','Purgatory — Seven Terraces','A mountain ringed by fire — each terrace dissolves a sheath.','Purgatorio','','purification',['purgatory','terraces','purification'],'purification','seven ascending terraces of fire',8.0,sc04)
Scene('dc05','Beatrice — The Beloved','She leads by being seen — to see her is to see yourself.','Beatrice','','love',['beatrice','beloved','revelation'],'revelation','radiant feminine figure with rays',8.0,sc05)
Scene('dc06','Paradise — Nine Spheres','Each sphere strips another layer of separation.','Paradiso','','heaven',['paradise','spheres','ascent'],'ascent','nine expanding concentric rings',8.0,sc06)
Scene('dc07','The Celestial Rose','A vast rose of living petals — all as one.','Rosa celeste','','vision',['rose','unity','recognition'],'unity','rose mandala of faces and stars',8.0,sc07)
Scene('dc08','The Final Flash','A love that moves the sun — no method left.','Fulgore','','direct',['flash','love','recognition'],'recognition','expanding radiance overwhelming all',10.0,sc08)
Scene('dc09','Three Movements','Try — be helped — disappear.','Triforme','','structure',['hell','purgatory','paradise'],'structure','three linked circles with path',8.0,sc09)
Scene('dc10','You Are the Journey','The guide, the beloved, the love — all you.','Unus','','seal',['self','journey','recognition'],'seal','radial self-recognition mandala',8.0,sc10)
    Scene('dc01','The Dark Wood','Halfway through life — lost, with no idea where he is going.','Selva oscura','','opening',['dark','wood','lost'],'intro','dark forest with distant light',6.0,sc01),
    Scene('dc02','Inferno — Nine Circles','Each step downward — a layer of skin peeled back.','Inferno','','hell',['hell','circles','descent'],'hell','nine descending rings of fire and ice',8.0,sc02),
    Scene('dc03','Virgil — The Lantern','Reason — a lantern illuminating what is already there.','Virgilio','','guide',['guide','reason','limits'],'guide','two figures, lantern between them',8.0,sc03),
    Scene('dc04','Purgatory — Seven Terraces','A mountain ringed by fire — each terrace dissolves a sheath.','Purgatorio','','purification',['purgatory','terraces','purification'],'purification','seven ascending terraces of fire',8.0,sc04),
    Scene('dc05','Beatrice — The Beloved','She leads by being seen — to see her is to see yourself.','Beatrice','','love',['beatrice','beloved','revelation'],'revelation','radiant feminine figure with rays',8.0,sc05),
    Scene('dc06','Paradise — Nine Spheres','Each sphere strips another layer of separation.','Paradiso','','heaven',['paradise','spheres','ascent'],'ascent','nine expanding concentric rings',8.0,sc06),
    Scene('dc07','The Celestial Rose','A vast rose of living petals — all as one.','Rosa celeste','','vision',['rose','unity','recognition'],'unity','rose mandala of faces and stars',8.0,sc07),
    Scene('dc08','The Final Flash','A love that moves the sun — no method left.','Fulgore','','direct',['flash','love','recognition'],'recognition','expanding radiance overwhelming all',10.0,sc08),
    Scene('dc09','Three Movements','Try — be helped — disappear.','Triforme','','structure',['hell','purgatory','paradise'],'structure','three linked circles with path',8.0,sc09),
    Scene('dc10','You Are the Journey','The guide, the beloved, the love — all you.','Unus','','seal',['self','journey','recognition'],'seal','radial self-recognition mandala',8.0,sc10),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DARK)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Divina Commedia — The Journey You Didn\'t Know You Were On',
        'source_basis':'Expansion Essay 23: "the journey you didn\'t know you were on" (Dante) — 10 scenes.',
        'style':{'family':'dante / three-worlds visualization','background':'dark to light','ink':'gold, crimson, teal, lavender, white'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Dante — 10 scenes, hell/purgatory/paradise palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Dante Pack — inferno/purgatorio/paradiso palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Divina Commedia — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'dante_comedy_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'dante_comedy_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['dante_comedy_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'dante_comedy_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
