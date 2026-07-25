#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=21210

DEEP=(14,16,24); WARM=(20,18,20); NIGHT=(16,14,22)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246); PEARL=(246,243,236)
SILVER=(196,204,222); TEAL=(92,146,148); INDIGO=(68,78,136); VIOLET=(120,104,168)
SLATE=(90,100,120); MIST=(160,172,192); CRIMSON=(154,44,58); CORAL=(206,108,100)
LAVENDER=(170,156,200); EARTH=(110,80,50)

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
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(GOLD,SILVER,.5),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(GOLD,SILVER,.3),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,INDIGO,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,14,20,200),outline=rgba(mix(GOLD,SILVER,.4),45),width=1)
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

def ys_ground(seed,bg,glow_col,intensity=0.4):
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
    fs=SEED+int(t*9973)%100000; im.paste(ys_ground(fs,DEEP,mix(GOLD,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'yoga is about stopping',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'the wrong kind of activity',font=TERM_FONT,fill=mix(GOLD,LAVENDER,.5),anchor='mm')
    d.text((cx,155),'the churning that keeps you from seeing what you already are',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(3):
        r=30+i*30
        d.ellipse((cx-r,cy+20-r*0.6,cx+r,cy+20+r*0.6),outline=rgba(mix(SLATE,LAVENDER,.3),int(100*(1-clamp(prog*1.2-i*0.2)))),width=1)
    draw_glow(im,(cx,cy+20),int(5+20*prog),mix(GOLD,WHITE,.5),int(120*prog),14)
    d.ellipse((cx-8,cy+12,cx+8,cy+28),fill=rgba(WHITE,int(220*prog)))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(ys_ground(fs,WARM,mix(TEAL,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'five vrittis — five streams into one pool',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'correct knowledge, error, imagination, sleep, memory',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    d.text((cx,145),'the mind is the pool — not any one stream',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    v_names=['pramāṇa','viparyaya','vikalpa','nidrā','smṛti']
    v_cols=[mix(GOLD,WHITE,.5),mix(CRIMSON,GOLD,.4),mix(VIOLET,LAVENDER,.5),mix(TEAL,SILVER,.5),mix(EARTH,GOLD,.3)]
    prog=smoothstep(0.05,0.9,t)
    for i in range(5):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        x=180+i*220
        d.ellipse((x-40,cy+20-25,x+40,cy+20+25),outline=rgba(v_cols[i],int(170*p)),width=2)
        d.text((x,cy+20),v_names[i],font=TINY_FONT,fill=rgba(v_cols[i],int(200*p)),anchor='mm')
        if i<4:
            pts=partial_polyline([(x+40,cy+20),(x+180,cy+20)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(v_cols[i],v_cols[i+1],.5),1,50,3)
    d.text((640,480),'even correct knowledge is a vritti — the goal is to witness all five',font=SUB_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(ys_ground(fs,NIGHT,mix(CRIMSON,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'five kleshas — the seer mistaking the seen',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'a man mistakes his reflection for another person',font=TERM_FONT,fill=mix(CRIMSON,GOLD,.5),anchor='mm')
    d.text((cx,150),'he waves. it waves back. he falls in love — with himself.',font=SMALL_FONT,fill=mix(MIST,CRIMSON,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx-60,cy+40),20,mix(CRIMSON,GOLD,.4),int(80*prog),12)
    d.ellipse((cx-60-18,cy+15,cx-60+18,cy+65),outline=rgba(mix(CRIMSON,GOLD,.4),int(170*prog)),width=2)
    draw_glow(im,(cx+60,cy+40),20,mix(GOLD,LAVENDER,.5),int(80*prog),12)
    d.ellipse((cx+60-18,cy+15,cx+60+18,cy+65),outline=rgba(mix(GOLD,LAVENDER,.5),int(170*prog)),width=2)
    d.text((640,485),'avidya: the deep mistake of identifying with what you are not',font=SUB_FONT,fill=mix(MIST,CRIMSON,.4),anchor='mm')

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(ys_ground(fs,WARM,mix(GOLD,CORAL,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'kriya yoga — three acts, one fire',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'tapas — svadhyaya — ishvara pranidhana',font=TERM_FONT,fill=mix(GOLD,CORAL,.5),anchor='mm')
    d.text((cx,145),'the heat of practice, the study that reads you, the release',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    cols=[mix(CORAL,GOLD,.5),mix(TEAL,GOLD,.5),mix(GOLD,WHITE,.6)]
    labels=['tapas','svādhyāya','īśvara praṇidhāna']
    for i in range(3):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        x=280+i*350; y=cy+30
        sz=20+12*math.sin(t+i)
        d.ellipse((x-sz,y-sz,x+sz,y+sz),outline=rgba(cols[i],int(180*p)),width=2)
        d.ellipse((x-int(sz*0.5),y-int(sz*0.5),x+int(sz*0.5),y+int(sz*0.5)),fill=rgba(cols[i],int(100*p)))
        d.text((x,y+sz+15),labels[i],font=TINY_FONT,fill=rgba(cols[i],int(200*p)),anchor='mm')

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(ys_ground(fs,DEEP,mix(GOLD,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'the eight limbs',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'a ladder that does not lean against anything',font=TERM_FONT,fill=mix(GOLD,LAVENDER,.5),anchor='mm')
    limbs=['yama','niyama','āsana','prāṇāyāma','pratyāhāra','dhāraṇā','dhyāna','samādhi']
    l_cols=[SLATE,TEAL,GOLD,CORAL,INDIGO,LAVENDER,SILVER,WHITE]
    prog=smoothstep(0.05,0.9,t)
    for i in range(8):
        p=clamp(prog*1.3-i*0.05)
        if p<=0: continue
        y=155+i*38
        d.line((cx-120,y,cx+120,y),fill=rgba(l_cols[i],int(180*p)),width=3)
        d.text((cx-130,y-4),limbs[i],font=TINY_FONT,fill=rgba(l_cols[i],int(200*p)),anchor='rm')

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(ys_ground(fs,WARM,mix(EARTH,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the foundation — yama and niyama',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'how you treat the person next to you on the bus',font=TERM_FONT,fill=mix(EARTH,GOLD,.4),anchor='mm')
    d.text((cx,150),'meditation cannot untangle a life built on lies',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    yamas=['ahiṃsā','satya','asteya','brahmacarya','aparigraha']
    niyamas=['śauca','santoṣa','tapas','svādhyāya','īśvara praṇidhāna']
    prog=smoothstep(0.05,0.85,t)
    for i in range(5):
        for side,names in enumerate([yamas,niyamas]):
            p=clamp(prog*1.3-(i+side*0.1)*0.06)
            if p<=0: continue
            x=230+side*620; y=190+i*32
            d.line((x-60,y,x+60,y),fill=rgba(mix(EARTH,GOLD,side/2),int(150*p)),width=2)
            d.text((x,y-4),names[i],font=TINY_FONT,fill=rgba(mix(EARTH,GOLD,side/2),int(200*p)),anchor='mm')

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(ys_ground(fs,NIGHT,mix(GOLD,WHITE,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'dharana — dhyana — samadhi',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'steady the hand — hold it still — become the leaf',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,145),'a magnifying glass over a dry leaf',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(3):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        x=300+i*310
        sz=12+8*p
        draw_glow(im,(x,cy+40),int(sz+5),mix(GOLD,WHITE,i/3),int(100*p),10)
        d.ellipse((x-sz,cy+40-sz,x+sz,cy+40+sz),outline=rgba(mix(GOLD,WHITE,i/3),int(180*p)),width=2)
        d.text((x,cy+65),['dhāraṇā','dhyāna','samādhi'][i],font=SMALL_FONT,fill=rgba(mix(GOLD,WHITE,i/3),int(200*p)),anchor='mm')
        if i<2:
            pts=partial_polyline([(x+sz+5,cy+40),(x+310-sz-5,cy+40)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(GOLD,WHITE,.3),1,50,3)

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(ys_ground(fs,DEEP,mix(GOLD,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the projector and the screen',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'no one turns around to look at the projector',font=TERM_FONT,fill=mix(GOLD,LAVENDER,.5),anchor='mm')
    d.text((cx,150),'liberation is a slow turning — not of the screen, but of the head',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((500,200,1080,380),radius=14,outline=rgba(mix(SLATE,LAVENDER,.3),150),width=2)
    draw_glow(im,(320,290),30,mix(GOLD,WHITE,.5),int(100*prog),20)
    d.ellipse((310,280,330,300),fill=rgba(WHITE,int(200*prog)))
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        turn_x=int(lerp(640,340,p))
        d.ellipse((turn_x-8,240,turn_x+8,280),outline=rgba(mix(GOLD,LAVENDER,.5),int(160*p)),width=2)

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(ys_ground(fs,WARM,mix(GOLD,WHITE,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,85),'kaivalya — standing in your own nature',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a man walks out of a cinema into broad daylight',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,145),'the film is still running inside — he is no longer in the dark',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((350,180,930,320),radius=12,outline=rgba(mix(SLATE,LAVENDER,.3),150),width=2)
    d.text((640,250),'cinema',font=SMALL_FONT,fill=mix(SLATE,LAVENDER,.3),anchor='mm')
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        draw_glow(im,(cx,cy+40),int(10+30*p),mix(GOLD,WHITE,.6),int(150*p),18)
        d.ellipse((cx-14,cy+26,cx+14,cy+54),fill=rgba(WHITE,int(255*p)))
        d.text((cx,cy+70),'kaivalya',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')
    d.text((640,485),'you have been this light all along — you just forgot to look away from the screen',font=SUB_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')

SCENES=[,Scene('ys01','Stilling the Mind','Yoga is about stopping the churning — the seer is revealed.','Yogaḥ','','opening',['still','mind','seer'],'intro','stilling pool with luminous center',6.0,sc01)
Scene('ys02','Five Vrittis','Five streams — correct knowledge, error, imagination, sleep, memory.','Vṛtti','','activities',['vrittis','streams','mind'],'activities','five streams converging into one pool',8.0,sc02)
Scene('ys03','Five Kleshas','The seer mistaking the seen — avidya, the root error.','Kleśa','','hindrances',['kleshas','hindrances','error'],'hindrances','two facing forms — reflection mistaken for other',8.0,sc03)
Scene('ys04','Kriya Yoga','Tapas, svadhyaya, ishvara pranidhana — three acts, one fire.','Kriyā yoga','','practice',['tapas','study','surrender'],'practice','three interconnected fiery circles',8.0,sc04)
Scene('ys05','Eight Limbs','A ladder that does not lean against anything.','Aṣṭāṅga','','limbs',['eight','limbs','ladder'],'limbs','eight ascending rungs',8.0,sc05)
Scene('ys06','Yama and Niyama','The foundation — how you treat others comes before posture.','Yama-niyama','','ethics',['ethics','foundation','conduct'],'ethics','ten ethical precepts as two columns',8.0,sc06)
Scene('ys07','The Inner Limbs','Dharana, dhyana, samadhi — steady, hold, become.','Sanyama','','inner',['concentration','meditation','absorption'],'inner','three stages of focusing light',8.0,sc07)
Scene('ys08','The Projector','No one turns to look at the source of the light.','Puruṣa','','seer',['projector','light','source'],'seer','screen with projector light — a head turning',8.0,sc08)
Scene('ys09','Kaivalya','Standing in your own nature — walking out of the cinema into daylight.','Kaivalya','','seal',['freedom','nature','light'],'seal','cinema door opening to brilliant light',10.0,sc09)
Scene('ys01','Stilling the Mind','Yoga is about stopping the churning — the seer is revealed.','Yogaḥ','','opening',['still','mind','seer'],'intro','stilling pool with luminous center',6.0,sc01)
Scene('ys02','Five Vrittis','Five streams — correct knowledge, error, imagination, sleep, memory.','Vṛtti','','activities',['vrittis','streams','mind'],'activities','five streams converging into one pool',8.0,sc02)
Scene('ys03','Five Kleshas','The seer mistaking the seen — avidya, the root error.','Kleśa','','hindrances',['kleshas','hindrances','error'],'hindrances','two facing forms — reflection mistaken for other',8.0,sc03)
Scene('ys04','Kriya Yoga','Tapas, svadhyaya, ishvara pranidhana — three acts, one fire.','Kriyā yoga','','practice',['tapas','study','surrender'],'practice','three interconnected fiery circles',8.0,sc04)
Scene('ys05','Eight Limbs','A ladder that does not lean against anything.','Aṣṭāṅga','','limbs',['eight','limbs','ladder'],'limbs','eight ascending rungs',8.0,sc05)
Scene('ys06','Yama and Niyama','The foundation — how you treat others comes before posture.','Yama-niyama','','ethics',['ethics','foundation','conduct'],'ethics','ten ethical precepts as two columns',8.0,sc06)
Scene('ys07','The Inner Limbs','Dharana, dhyana, samadhi — steady, hold, become.','Sanyama','','inner',['concentration','meditation','absorption'],'inner','three stages of focusing light',8.0,sc07)
Scene('ys08','The Projector','No one turns to look at the source of the light.','Puruṣa','','seer',['projector','light','source'],'seer','screen with projector light — a head turning',8.0,sc08)
Scene('ys09','Kaivalya','Standing in your own nature — walking out of the cinema into daylight.','Kaivalya','','seal',['freedom','nature','light'],'seal','cinema door opening to brilliant light',10.0,sc09)
Scene('ys01','Stilling the Mind','Yoga is about stopping the churning — the seer is revealed.','Yogaḥ','','opening',['still','mind','seer'],'intro','stilling pool with luminous center',6.0,sc01)
Scene('ys02','Five Vrittis','Five streams — correct knowledge, error, imagination, sleep, memory.','Vṛtti','','activities',['vrittis','streams','mind'],'activities','five streams converging into one pool',8.0,sc02)
Scene('ys03','Five Kleshas','The seer mistaking the seen — avidya, the root error.','Kleśa','','hindrances',['kleshas','hindrances','error'],'hindrances','two facing forms — reflection mistaken for other',8.0,sc03)
Scene('ys04','Kriya Yoga','Tapas, svadhyaya, ishvara pranidhana — three acts, one fire.','Kriyā yoga','','practice',['tapas','study','surrender'],'practice','three interconnected fiery circles',8.0,sc04)
Scene('ys05','Eight Limbs','A ladder that does not lean against anything.','Aṣṭāṅga','','limbs',['eight','limbs','ladder'],'limbs','eight ascending rungs',8.0,sc05)
Scene('ys06','Yama and Niyama','The foundation — how you treat others comes before posture.','Yama-niyama','','ethics',['ethics','foundation','conduct'],'ethics','ten ethical precepts as two columns',8.0,sc06)
Scene('ys07','The Inner Limbs','Dharana, dhyana, samadhi — steady, hold, become.','Sanyama','','inner',['concentration','meditation','absorption'],'inner','three stages of focusing light',8.0,sc07)
Scene('ys08','The Projector','No one turns to look at the source of the light.','Puruṣa','','seer',['projector','light','source'],'seer','screen with projector light — a head turning',8.0,sc08)
Scene('ys09','Kaivalya','Standing in your own nature — walking out of the cinema into daylight.','Kaivalya','','seal',['freedom','nature','light'],'seal','cinema door opening to brilliant light',10.0,sc09)
    Scene('ys01','Stilling the Mind','Yoga is about stopping the churning — the seer is revealed.','Yogaḥ','','opening',['still','mind','seer'],'intro','stilling pool with luminous center',6.0,sc01),
    Scene('ys02','Five Vrittis','Five streams — correct knowledge, error, imagination, sleep, memory.','Vṛtti','','activities',['vrittis','streams','mind'],'activities','five streams converging into one pool',8.0,sc02),
    Scene('ys03','Five Kleshas','The seer mistaking the seen — avidya, the root error.','Kleśa','','hindrances',['kleshas','hindrances','error'],'hindrances','two facing forms — reflection mistaken for other',8.0,sc03),
    Scene('ys04','Kriya Yoga','Tapas, svadhyaya, ishvara pranidhana — three acts, one fire.','Kriyā yoga','','practice',['tapas','study','surrender'],'practice','three interconnected fiery circles',8.0,sc04),
    Scene('ys05','Eight Limbs','A ladder that does not lean against anything.','Aṣṭāṅga','','limbs',['eight','limbs','ladder'],'limbs','eight ascending rungs',8.0,sc05),
    Scene('ys06','Yama and Niyama','The foundation — how you treat others comes before posture.','Yama-niyama','','ethics',['ethics','foundation','conduct'],'ethics','ten ethical precepts as two columns',8.0,sc06),
    Scene('ys07','The Inner Limbs','Dharana, dhyana, samadhi — steady, hold, become.','Sanyama','','inner',['concentration','meditation','absorption'],'inner','three stages of focusing light',8.0,sc07),
    Scene('ys08','The Projector','No one turns to look at the source of the light.','Puruṣa','','seer',['projector','light','source'],'seer','screen with projector light — a head turning',8.0,sc08),
    Scene('ys09','Kaivalya','Standing in your own nature — walking out of the cinema into daylight.','Kaivalya','','seal',['freedom','nature','light'],'seal','cinema door opening to brilliant light',10.0,sc09),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DEEP)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Yoga Sūtras — The Eight Steps You\'re Already Taking',
        'source_basis':'Expansion Essay 21: "the 8 steps you\'re already taking" — 9 scenes.',
        'style':{'family':'yoga / interior visualization','background':'deep calm','ink':'gold, lavender, silver, teal'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Yoga Sutras — 9 scenes, gold/lavender/calm palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Yoga Sutras Pack — gold/lavender/interior palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Yoga Sūtras — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'yoga_sutras_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'yoga_sutras_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['yoga_sutras_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'yoga_sutras_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
