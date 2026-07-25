#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=19190

DARK=(14,12,14); WARM=(20,16,14); NIGHT=(16,14,20); DUSTY=(36,32,28)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246); PEARL=(246,243,236)
SILVER=(196,204,222); CRIMSON=(154,44,58); CORAL=(206,108,100); TEAL=(92,146,148)
INDIGO=(68,78,136); VIOLET=(120,104,168); SLATE=(90,100,120); MIST=(160,172,192)
SUN=(220,180,80); BLOOD=(120,30,30); EARTH=(110,80,50); MUD=(80,65,50)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA='/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11); DEVA_MED=ImageFont.truetype(FONT_DEVA,26)

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
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(GOLD,SUN,.4),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(GOLD,SUN,.2),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,CRIMSON,mix(GOLD,SUN,.5))
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,10,12,200),outline=rgba(mix(GOLD,SUN,.3),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,SUN,.5))

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.5)); c=mix(mix(EARTH,GOLD,.3),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,50))))
    im.alpha_composite(ov)

def gita_ground(seed,bg,glow_col,intensity=0.5):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*3.0*intensity+fine[...,None]*0.9*intensity
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*16,0,24)[...,None]
    if glow_col:
        g=np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.38)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.04
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(gita_ground(fs,WARM,mix(EARTH,GOLD,.2),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'a battlefield. arjuna sees his own teachers,',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'his own family, his own ancestors.',font=TERM_FONT,fill=mix(EARTH,GOLD,.4),anchor='mm')
    d.text((cx,150),'he drops his bow. "i will not fight."',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.3),anchor='mm')
    prog=ease_in_out(t)
    d.line((180,360,1100,360),fill=rgba(mix(EARTH,SLATE,.5),120),width=2)
    d.line((180,400,1100,400),fill=rgba(mix(EARTH,SLATE,.5),120),width=2)
    for i in range(10):
        x=200+i*100; y=330+40*(i%2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(CRIMSON,EARTH,i/10),int(150*prog)))
        d.ellipse((x-4,y+60-4,x+4,y+60+4),fill=rgba(mix(INDIGO,SLATE,i/10),int(150*prog)))
    d.text((640,485),'between two armies, a god explains why he must fight',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(gita_ground(fs,NIGHT,mix(GOLD,WHITE,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'never the spirit was born',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'death is like changing worn-out robes for new ones',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,145),'the one who breathes was never born — cannot be killed',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-22,cy+15,cx+22,cy+55),outline=rgba(mix(EARTH,SLATE,.4),120),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        draw_glow(im,(cx,cy+35),int(15+30*p),mix(GOLD,WHITE,.5),int(150*p),16)
        d.ellipse((cx-12,cy+23,cx+12,cy+47),fill=rgba(WHITE,int(220*p)))
        d.line((cx-12,cy+35,cx-40,cy+25),fill=rgba(mix(GOLD,WHITE,.3),int(150*p)),width=1)
        d.line((cx+12,cy+35,cx+40,cy+25),fill=rgba(mix(GOLD,WHITE,.3),int(150*p)),width=1)
    d.text((640,480),'krishna dismantles the battlefield by changing what "you" means',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(gita_ground(fs,DUSTY,mix(SUN,GOLD,.4),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'act without attachment to outcome',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the potter\'s hands — wholly absorbed, utterly unattached',font=TERM_FONT,fill=mix(SUN,GOLD,.6),anchor='mm')
    d.text((cx,145),'complete engagement, zero clinging — the act is its own reward',font=SMALL_FONT,fill=mix(MIST,SUN,.4),anchor='mm')
    prog=ease_in_out(t)
    pts=[(cx,cy+35),(cx-30,cy+60),(cx+20,cy+55),(cx+40,cy+35),(cx+30,cy+10),(cx,cy+35)]
    d.polygon(pts,outline=rgba(mix(EARTH,SUN,.4),int(180*prog)),width=2)
    draw_glow(im,(cx,cy+35),int(5+20*prog),mix(SUN,GOLD_LIGHT,.5),int(100*prog),12)
    d.ellipse((cx-8,cy+27,cx+8,cy+43),fill=rgba(WHITE,int(200*prog)))

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(gita_ground(fs,WARM,mix(CRIMSON,TEAL,.3),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'the three gunas',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'sattva — rajas — tamas',font=TERM_FONT,fill=mix(SUN,GOLD,.6),anchor='mm')
    d.text((cx,145),'the spirit is what the rope holds, not the rope itself',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    cols=[mix(SUN,WHITE,.5),mix(CRIMSON,GOLD,.4),mix(MUD,SLATE,.5)]
    labels=['sattva','rajas','tamas']
    for i in range(3):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        x=cx-100+i*100; y=cy+40
        d.ellipse((x-18,y-18,x+18,y+18),outline=rgba(cols[i],int(180*p)),width=2)
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(cols[i],int(120*p)))
        d.text((x,y+30),labels[i],font=SMALL_FONT,fill=rgba(mix(cols[i],PEARL,.3),int(200*p)),anchor='mm')
        if i<2:
            pts=partial_polyline([(x+18,y),(x+82,y)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(cols[i],cols[i+1],.5),2,70,5)

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(gita_ground(fs,DUSTY,mix(EARTH,GOLD,.3),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the field and the knower of the field',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'pleasure and pain are crops — they grow and rot',font=TERM_FONT,fill=mix(EARTH,GOLD,.4),anchor='mm')
    d.text((cx,150),'the knower watches from a stillness that does not move',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    d.rectangle((250,200,1030,380),outline=rgba(mix(EARTH,SLATE,.5),150),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        for i in range(20):
            x=float(np.random.default_rng(i).uniform(280,980))
            y=float(np.random.default_rng(100+i).uniform(220,360))
            col=mix(EARTH,TEAL,float(np.random.default_rng(200+i).random()))
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,int(100*p)))
    draw_glow(im,(cx,120),15,mix(GOLD,WHITE,.5),int(100*prog),12)
    d.ellipse((cx-6,114,cx+6,126),fill=rgba(WHITE,int(220*prog)))

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(gita_ground(fs,NIGHT,mix(GOLD,WHITE,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'higher and lower nature',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a string of pearls — each pearl a galaxy',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,145),'the thread invisible, the hand that holds it nowhere seen',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(9):
        p=clamp(prog*1.3-i*0.04)
        if p<=0: continue
        x=cx-200+i*50
        rr=12+5*math.sin(t+i)
        col=mix(GOLD,TEAL,i/9)
        draw_glow(im,(x,cy+40),int(rr),col,int(70*p),8)
        d.ellipse((x-rr,cy+40-rr,x+rr,cy+40+rr),fill=rgba(col,int(150*p)),outline=rgba(mix(col,WHITE,.3),int(180*p)),width=2)
        if i>0:
            draw_line_glow(im,[(x-50-rr,cy+40),(x-rr,cy+40)],mix(GOLD,WHITE,.3),1,50,3)

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(gita_ground(fs,DARK,mix(CRIMSON,GOLD,.4),0.5),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'the cosmic vision',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'a mouth eating every star — teeth of light',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.5),anchor='mm')
    d.text((cx,140),'the taste of ash and honey at the same instant',font=SMALL_FONT,fill=mix(MIST,CRIMSON,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(30):
        a=i*2*math.pi/30; r=lerp(5,180,prog)
        x=cx+math.cos(a+prog)*r; y=cy+30+math.sin(a+prog)*r*0.55
        col=mix(mix(GOLD,CRIMSON,.3),mix(WHITE,GOLD,.5),i/30)
        draw_line_glow(im,[(cx,cy+30),(int(x),int(y))],col,1,50,4)
    draw_glow(im,(cx,cy+30),30,mix(GOLD,WHITE,.5),int(150*prog),18)
    d.ellipse((cx-14,cy+16,cx+14,cy+44),fill=rgba(WHITE,int(255*prog)))

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(gita_ground(fs,WARM,mix(SUN,CRIMSON,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'devotion — the easiest path',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'a woman kneeling in a dark temple',font=TERM_FONT,fill=mix(SUN,GOLD,.6),anchor='mm')
    d.text((cx,150),'the heart that has found its home rests',font=SMALL_FONT,fill=mix(MIST,SUN,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+40),30,mix(SUN,GOLD,.4),int(100*prog),16)
    d.ellipse((cx-20,cy+20,cx+20,cy+60),outline=rgba(mix(EARTH,SLATE,.4),150),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        d.ellipse((cx-6,cy+34,cx+6,cy+46),fill=rgba(WHITE,int(200*p)))
        draw_flame_pts=[(cx,cy+10-30*p),(cx-15,cy+15-5*p),(cx-6,cy+25),(cx+8,cy+22),(cx+18,cy+18)]
        d.polygon(draw_flame_pts,fill=rgba(mix(SUN,GOLD,.5),int(50*p)),outline=rgba(mix(SUN,GOLD,.5),int(150*p)))
    d.text((640,480),'it requires only one thing: the willingness to love beyond yourself',font=SUB_FONT,fill=mix(MIST,SUN,.4),anchor='mm')

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(gita_ground(fs,DUSTY,mix(SUN,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'the posture — dust motes in afternoon light',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the spine is a mountain. the breath is a thread.',font=TERM_FONT,fill=mix(SUN,GOLD,.5),anchor='mm')
    d.text((cx,145),'from this simple geometry, liberation grows',font=SMALL_FONT,fill=mix(MIST,SUN,.4),anchor='mm')
    prog=ease_in_out(t)
    pts=[(cx,cy+60),(cx-30,cy+90),(cx+30,cy+90)]
    d.polygon(pts,outline=rgba(mix(EARTH,SLATE,.4),150),width=2)
    d.line((cx,cy+60,cx,cy-10),fill=rgba(mix(EARTH,SLATE,.4),150),width=3)
    d.ellipse((cx-12,cy-25,cx+12,cy+5),outline=rgba(mix(EARTH,SLATE,.4),150),width=2)
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        draw_glow(im,(cx,cy-10),int(8+25*p),mix(GOLD,WHITE,.5),int(140*p),14)
        d.ellipse((cx-8,cy-18,cx+8,cy-2),fill=rgba(WHITE,int(220*p)))
        for i in range(15):
            x=float(np.random.default_rng(i).uniform(100,1180))
            y=float(np.random.default_rng(100+i).uniform(150,250))
            d.ellipse((x-1,y-1,x+1,y+1),fill=rgba(mix(SUN,WHITE,.3),int(80*p)))
    d.text((640,480),'the one who sits does nothing — the one who sits does everything',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(gita_ground(fs,WARM,mix(GOLD,CRIMSON,.2),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the battlefield is still there',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the armies have not moved',font=TERM_FONT,fill=mix(GOLD,CRIMSON,.4),anchor='mm')
    d.text((cx,145),'but arjuna is no longer the same man who dropped his bow',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,175),'the chariot moves. the conch sounds. the war goes on.',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    d.line((180,360,1100,360),fill=rgba(mix(EARTH,SLATE,.5),120),width=2)
    d.line((180,400,1100,400),fill=rgba(mix(EARTH,SLATE,.5),120),width=2)
    for i in range(10):
        x=200+i*100; y=330+40*(i%2)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(CRIMSON,EARTH,i/10),120))
        d.ellipse((x-3,y+57-3,x+3,y+57+3),fill=rgba(mix(INDIGO,SLATE,i/10),120))
    draw_glow(im,(cx,140),25,mix(GOLD,WHITE,.5),int(150*prog),16)
    d.ellipse((cx-12,128,cx+12,152),fill=rgba(WHITE,int(255*prog)))
    d.text((cx,140),'dṛṣṭa',font=DEVA_MED,fill=GOLD,anchor='mm')
    d.text((640,485),'the one who watches has never been born and will never die',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

SCENES=[,Scene('bg01','The Battlefield','Arjuna sees his teachers, his family — drops his bow.','Kuruksetra','','opening',['battle','arjuna','krishna'],'intro','two armies with a gap between',6.0,sc01)
Scene('bg02','Never Born, Never Dead','Death is changing worn-out robes for new ones.','Nitya','','spirit',['spirit','death','eternal'],'spirit','body-shedding luminous self',8.0,sc02)
Scene('bg03','Act Without Attachment','The potter\'s hands — wholly absorbed, zero clinging.','Nishkāma karma','','action',['action','detachment','presence'],'action','potter\'s wheel with glowing hands',8.0,sc03)
Scene('bg04','Three Gunas','Sattva, rajas, tamas — three strands of one rope.','Guṇa','','gunas',['gunas','strands','rope'],'gunas','three interlocking colored circles',8.0,sc04)
Scene('bg05','Field and Knower','The field bears crops; the knower watches unmoved.','Kṣetra-kṣetrajña','','knowledge',['field','knower','witness'],'witness','field with farmer standing apart',8.0,sc05)
Scene('bg06','Pearls on a String','The thread invisible, each pearl a galaxy.','Parā-prakṛti','','nature',['higher','lower','string'],'nature','string of pearl-galaxies on invisible thread',8.0,sc06)
Scene('bg07','The Cosmic Vision','A mouth eating every star — teeth of light.','Viśvarūpa','','vision',['cosmic','vision','arvind'],'vision','radial all-consuming form',10.0,sc07)
Scene('bg08','The Path of Devotion','A woman kneeling — the heart that has found its home.','Bhakti','','devotion',['devotion','love','surrender'],'devotion','kneeling figure before lamp flame',8.0,sc08)
Scene('bg09','The Posture','Spine a mountain, breath a thread — liberation from simple geometry.','Dhyāna','','practice',['posture','meditation','seat'],'practice','seated figure with dust motes in light',8.0,sc09)
Scene('bg10','The Battle Continues','The armies have not moved — but arjuna is no longer the same.','Sthitaprajña','','seal',['battle','witness','freedom'],'seal','battlefield with luminous witness above',10.0,sc10)
Scene('bg01','The Battlefield','Arjuna sees his teachers, his family — drops his bow.','Kuruksetra','','opening',['battle','arjuna','krishna'],'intro','two armies with a gap between',6.0,sc01)
Scene('bg02','Never Born, Never Dead','Death is changing worn-out robes for new ones.','Nitya','','spirit',['spirit','death','eternal'],'spirit','body-shedding luminous self',8.0,sc02)
Scene('bg03','Act Without Attachment','The potter\'s hands — wholly absorbed, zero clinging.','Nishkāma karma','','action',['action','detachment','presence'],'action','potter\'s wheel with glowing hands',8.0,sc03)
Scene('bg04','Three Gunas','Sattva, rajas, tamas — three strands of one rope.','Guṇa','','gunas',['gunas','strands','rope'],'gunas','three interlocking colored circles',8.0,sc04)
Scene('bg05','Field and Knower','The field bears crops; the knower watches unmoved.','Kṣetra-kṣetrajña','','knowledge',['field','knower','witness'],'witness','field with farmer standing apart',8.0,sc05)
Scene('bg06','Pearls on a String','The thread invisible, each pearl a galaxy.','Parā-prakṛti','','nature',['higher','lower','string'],'nature','string of pearl-galaxies on invisible thread',8.0,sc06)
Scene('bg07','The Cosmic Vision','A mouth eating every star — teeth of light.','Viśvarūpa','','vision',['cosmic','vision','arvind'],'vision','radial all-consuming form',10.0,sc07)
Scene('bg08','The Path of Devotion','A woman kneeling — the heart that has found its home.','Bhakti','','devotion',['devotion','love','surrender'],'devotion','kneeling figure before lamp flame',8.0,sc08)
Scene('bg09','The Posture','Spine a mountain, breath a thread — liberation from simple geometry.','Dhyāna','','practice',['posture','meditation','seat'],'practice','seated figure with dust motes in light',8.0,sc09)
Scene('bg10','The Battle Continues','The armies have not moved — but arjuna is no longer the same.','Sthitaprajña','','seal',['battle','witness','freedom'],'seal','battlefield with luminous witness above',10.0,sc10)
Scene('bg01','The Battlefield','Arjuna sees his teachers, his family — drops his bow.','Kuruksetra','','opening',['battle','arjuna','krishna'],'intro','two armies with a gap between',6.0,sc01)
Scene('bg02','Never Born, Never Dead','Death is changing worn-out robes for new ones.','Nitya','','spirit',['spirit','death','eternal'],'spirit','body-shedding luminous self',8.0,sc02)
Scene('bg03','Act Without Attachment','The potter\'s hands — wholly absorbed, zero clinging.','Nishkāma karma','','action',['action','detachment','presence'],'action','potter\'s wheel with glowing hands',8.0,sc03)
Scene('bg04','Three Gunas','Sattva, rajas, tamas — three strands of one rope.','Guṇa','','gunas',['gunas','strands','rope'],'gunas','three interlocking colored circles',8.0,sc04)
Scene('bg05','Field and Knower','The field bears crops; the knower watches unmoved.','Kṣetra-kṣetrajña','','knowledge',['field','knower','witness'],'witness','field with farmer standing apart',8.0,sc05)
Scene('bg06','Pearls on a String','The thread invisible, each pearl a galaxy.','Parā-prakṛti','','nature',['higher','lower','string'],'nature','string of pearl-galaxies on invisible thread',8.0,sc06)
Scene('bg07','The Cosmic Vision','A mouth eating every star — teeth of light.','Viśvarūpa','','vision',['cosmic','vision','arvind'],'vision','radial all-consuming form',10.0,sc07)
Scene('bg08','The Path of Devotion','A woman kneeling — the heart that has found its home.','Bhakti','','devotion',['devotion','love','surrender'],'devotion','kneeling figure before lamp flame',8.0,sc08)
Scene('bg09','The Posture','Spine a mountain, breath a thread — liberation from simple geometry.','Dhyāna','','practice',['posture','meditation','seat'],'practice','seated figure with dust motes in light',8.0,sc09)
Scene('bg10','The Battle Continues','The armies have not moved — but arjuna is no longer the same.','Sthitaprajña','','seal',['battle','witness','freedom'],'seal','battlefield with luminous witness above',10.0,sc10)
    Scene('bg01','The Battlefield','Arjuna sees his teachers, his family — drops his bow.','Kuruksetra','','opening',['battle','arjuna','krishna'],'intro','two armies with a gap between',6.0,sc01),
    Scene('bg02','Never Born, Never Dead','Death is changing worn-out robes for new ones.','Nitya','','spirit',['spirit','death','eternal'],'spirit','body-shedding luminous self',8.0,sc02),
    Scene('bg03','Act Without Attachment','The potter\'s hands — wholly absorbed, zero clinging.','Nishkāma karma','','action',['action','detachment','presence'],'action','potter\'s wheel with glowing hands',8.0,sc03),
    Scene('bg04','Three Gunas','Sattva, rajas, tamas — three strands of one rope.','Guṇa','','gunas',['gunas','strands','rope'],'gunas','three interlocking colored circles',8.0,sc04),
    Scene('bg05','Field and Knower','The field bears crops; the knower watches unmoved.','Kṣetra-kṣetrajña','','knowledge',['field','knower','witness'],'witness','field with farmer standing apart',8.0,sc05),
    Scene('bg06','Pearls on a String','The thread invisible, each pearl a galaxy.','Parā-prakṛti','','nature',['higher','lower','string'],'nature','string of pearl-galaxies on invisible thread',8.0,sc06),
    Scene('bg07','The Cosmic Vision','A mouth eating every star — teeth of light.','Viśvarūpa','','vision',['cosmic','vision','arvind'],'vision','radial all-consuming form',10.0,sc07),
    Scene('bg08','The Path of Devotion','A woman kneeling — the heart that has found its home.','Bhakti','','devotion',['devotion','love','surrender'],'devotion','kneeling figure before lamp flame',8.0,sc08),
    Scene('bg09','The Posture','Spine a mountain, breath a thread — liberation from simple geometry.','Dhyāna','','practice',['posture','meditation','seat'],'practice','seated figure with dust motes in light',8.0,sc09),
    Scene('bg10','The Battle Continues','The armies have not moved — but arjuna is no longer the same.','Sthitaprajña','','seal',['battle','witness','freedom'],'seal','battlefield with luminous witness above',10.0,sc10),
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
    manifest={'project':'Bhagavad Gītā — The Battle You Are Fighting',
        'source_basis':'Expansion Essay 19: "the battle you are fighting" — 10 scenes.',
        'style':{'family':'gita / battlefield visualization','background':'warm dust','ink':'gold, crimson, earth, sun'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    d='Gita — 10 scenes, battlefield/earth/gold palette.\n'
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(d,encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Gita Pack — battlefield/earth/gold/crimson palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Bhagavad Gītā — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'gita_battlefield_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'gita_battlefield_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['gita_battlefield_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'gita_battlefield_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
