#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=17171

DARK_SANCTUM=(14,12,16); WARM_DARK=(20,18,20); DEEP=(12,12,18)
SMOKE=(80,78,82); ASH=(160,150,145); TEMPLE_GOLD=(190,155,80)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); FIRE_AMBER=(210,140,50)
PEARL=(246,243,236); WHITE=(252,250,246); SILVER=(196,204,222)
SLATE=(90,100,120); MIST=(160,172,192); CRIMSON=(154,44,58)
LAVENDER=(170,156,200)

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
    d.rectangle((28,28,W-28,H-28),outline=rgba(TEMPLE_GOLD,80),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(TEMPLE_GOLD,50),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,CRIMSON,TEMPLE_GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,10,14,200),outline=rgba(TEMPLE_GOLD,45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=FIRE_AMBER)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(ASH,FIRE_AMBER,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def theurgy_ground(seed,bg,glow_col,intensity=0.5):
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
    fs=SEED+int(t*9973)%100000; im.paste(theurgy_ground(fs,DARK_SANCTUM,TEMPLE_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,105),'what if ritual is not symbolic?',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,135),'what if it changes the structure of reality?',font=TERM_FONT,fill=TEMPLE_GOLD,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy),int(10+40*prog),TEMPLE_GOLD,int(80*prog),14)
    d.rounded_rectangle((cx-50,cy-30,cx+50,cy+30),radius=8,outline=rgba(TEMPLE_GOLD,int(180*prog)),width=2)
    d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=rgba(WHITE,int(200*prog)))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(theurgy_ground(fs,DARK_SANCTUM,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,95),'theurgy means god-work',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'the theurgist is a technician of the divine',font=TERM_FONT,fill=TEMPLE_GOLD,anchor='mm')
    d.text((cx,155),'sounds, gestures, substances, intentions — precise combinations',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for i in range(4):
        x=280+i*240; y=cy+40
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        syms=['\u266b','\u263d','\u2737','\u25c7']
        d.ellipse((x-24,y-24,x+24,y+24),outline=rgba(TEMPLE_GOLD,int(180*p)),width=2)
        d.text((x,y),syms[i],font=TERM_FONT,fill=rgba(TEMPLE_GOLD,int(200*p)),anchor='mm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(theurgy_ground(fs,WARM_DARK,SILVER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'iamblichus broke with porphyry',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'contemplation is not enough',font=TERM_FONT,fill=SILVER,anchor='mm')
    d.text((cx,150),'beyond thought — you need acts, materials, the body',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((200,200,520,360),radius=12,outline=rgba(SLATE,150),width=2)
    d.text((360,280),'thought',font=SMALL_FONT,fill=SLATE,anchor='mm')
    d.rounded_rectangle((760,200,1080,360),radius=12,outline=rgba(TEMPLE_GOLD,180),fill=rgba(TEMPLE_GOLD,15),width=2)
    d.text((920,280),'ritual',font=SMALL_FONT,fill=TEMPLE_GOLD,anchor='mm')
    draw_line_glow(im,bezier((520,280),(640,240),(680,320),(760,280),60),FIRE_AMBER,3,120,7)

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(theurgy_ground(fs,DARK_SANCTUM,ASH,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the incense is divinity',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'in the form of smoke',font=TERM_FONT,fill=ASH,anchor='mm')
    d.text((cx,150),'the hymn is the god in the form of sound',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for i in range(20):
        x=float(np.random.default_rng(171+i).uniform(300,980))
        y=lerp(cy+60,cy-60,prog)+float(np.random.default_rng(200+i).uniform(-15,15))
        r=float(np.random.default_rng(300+i).uniform(4,10))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(ASH,int(80*(1-abs(y-(cy-60))/120))))
    draw_glow(im,(cx,cy+60),15,TEMPLE_GOLD,80,12)
    d.rounded_rectangle((cx-20,cy+50,cx+20,cy+70),radius=4,outline=rgba(TEMPLE_GOLD,150),width=2)

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(theurgy_ground(fs,WARM_DARK,FIRE_AMBER,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'containing ecstasy',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the formless accessed through perfect form',font=TERM_FONT,fill=FIRE_AMBER,anchor='mm')
    d.text((cx,150),'form is the vessel that can hold the formless',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    flame_h=lerp(10,120,prog)
    pts=[(cx,cy+30-flame_h),(cx-25,cy+10),(cx-10,cy+25),(cx+15,cy+20),(cx+30,cy+10)]
    d.polygon(pts,fill=rgba(FIRE_AMBER,int(60*prog)),outline=rgba(FIRE_AMBER,int(200*prog)))
    draw_glow(im,(cx,cy),int(flame_h*0.3),FIRE_AMBER,int(100*prog),14)
    d.rounded_rectangle((cx-60,cy-60,cx+60,cy+40),radius=10,outline=rgba(TEMPLE_GOLD,int(120*prog)),width=2)

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(theurgy_ground(fs,DARK_SANCTUM,TEMPLE_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the gods descend',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'because they are invited',font=TERM_FONT,fill=TEMPLE_GOLD,anchor='mm')
    d.text((cx,150),'by the correct sequence of gestures, sounds, and substances',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    pts=bezier((cx,180),(cx-30,240),(cx+40,310),(cx,380),60)
    reveal=partial_polyline(pts,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,GOLD,3,110,7)
    a=prog*2*math.pi; x=cx+math.cos(a)*80*prog; y=cy+math.sin(a)*50*prog
    for i in range(3):
        ai=t*0.2+i*2*math.pi/3; xi=cx+math.cos(ai)*40*prog; yi=180+40*prog+math.sin(ai)*20*prog
        draw_glow(im,(int(xi),int(yi)),6,TEMPLE_GOLD,int(80*prog),6)

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(theurgy_ground(fs,WARM_DARK,GOLD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the luminous body',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'a body of light parallel to the physical',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'theurgy works on this body — purifies, strengthens, activates',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-25,cy+10,cx+25,cy+60),outline=rgba(SLATE,120),width=2)
    d.line((cx,cy+60,cx,cy+120),fill=rgba(SLATE,100),width=2)
    d.line((cx,cy+30,cx-50,cy+70),fill=rgba(SLATE,80),width=2)
    d.line((cx,cy+30,cx+50,cy+70),fill=rgba(SLATE,80),width=2)
    draw_glow(im,(cx,cy+35),int(5+20*prog),GOLD_LIGHT,int(120*prog),14)
    d.ellipse((cx-int(8+15*prog),cy+27-int(8+15*prog),cx+int(8+15*prog),cy+43+int(8+15*prog)),fill=rgba(WHITE,int(200*prog)))

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(theurgy_ground(fs,DARK_SANCTUM,TEMPLE_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'taking the shape of the gods',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'tuning an instrument to a divine frequency',font=TERM_FONT,fill=TEMPLE_GOLD,anchor='mm')
    d.text((cx,150),'the human becomes a channel — not possessed, but resonant',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-30,cy-15,cx+30,cy+45),outline=rgba(SLATE,120),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        d.ellipse((cx-40-30*p,cy-25-30*p,cx+40+30*p,cy+55+30*p),outline=rgba(TEMPLE_GOLD,int(180*p)),width=2)
        draw_glow(im,(cx,cy+15),int(15+20*p),GOLD,int(100*p),12)
    for i in range(5):
        a=i*2*math.pi/5+t*0.15; r=80+40*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.5
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(TEMPLE_GOLD,int(80*prog)))

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(theurgy_ground(fs,WARM_DARK,ASH,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'the anonymous priest',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the flute — the music belongs to the breath',font=TERM_FONT,fill=TEMPLE_GOLD,anchor='mm')
    d.text((cx,150),'his name does not matter. only the precision of the performance.',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.line((cx-15,cy+30,cx-15,cy+60),fill=rgba(TEMPLE_GOLD,150),width=3)
    d.line((cx+15,cy+30,cx+15,cy+60),fill=rgba(TEMPLE_GOLD,150),width=3)
    d.ellipse((cx-12,cy+20,cx+12,cy+34),outline=rgba(TEMPLE_GOLD,180),width=2)
    pts=[]
    for i in range(60):
        u=i/59; x=lerp(300,980,u); y=cy+70+math.sin(u*2*math.pi*2+t*math.pi)*15*prog
        pts.append((x,y))
    draw_line_glow(im,pts,TEMPLE_GOLD,2,80,5)

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(theurgy_ground(fs,WARM_DARK,FIRE_AMBER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'body as furnace',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'ritual as heat — god as gold',font=TERM_FONT,fill=FIRE_AMBER,anchor='mm')
    d.text((cx,145),'the technology is different; the logic is identical',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-25,cy+10,cx+25,cy+60),outline=rgba(SLATE,120),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        draw_glow(im,(cx,cy+35),int(15+30*p),FIRE_AMBER,int(100*p),16)
        d.ellipse((cx-5,cy+30,cx+5,cy+40),fill=rgba(GOLD_LIGHT,int(200*p)))
    d.text((640,478),'theurgy and tantra — the same fire, different vessels',font=SUB_FONT,fill=MIST,anchor='mm')

def sc11(im,t):
    fs=SEED+int(t*9973+5000)%100000; im.paste(theurgy_ground(fs,DARK_SANCTUM,TEMPLE_GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,85),'your actions have ontological weight',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'you become devout by praying',font=TERM_FONT,fill=TEMPLE_GOLD,anchor='mm')
    d.text((cx,145),'you become worthy by performing the acts that invite the descent',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for i in range(16):
        a=i*2*math.pi/16+t*0.04; r=lerp(10,180,prog)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.62
        draw_line_glow(im,[(cx,cy),(int(x),int(y))],mix(TEMPLE_GOLD,ASH,i/16),1,50,4)
    d.rounded_rectangle((cx-60,cy-30,cx+60,cy+30),radius=10,outline=rgba(TEMPLE_GOLD,int(180*prog)),fill=rgba(TEMPLE_GOLD,int(20*prog)),width=2)
    draw_glow(im,(cx,cy),20,GOLD,100,12)
    d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=rgba(WHITE,255))
    d.text((640,480),'the question: are you willing to become the place where they can appear?',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[,Scene('th01','Ritual Is Not Symbolic','It changes the structure of reality.','Theourgia','','opening',['ritual','ontology','reality'],'intro','ritual vessel with inner glow',6.0,sc01)
Scene('th02','God-Work','The theurgist: technician of the divine.','Theourgia','','definition',['theurgy','god-work','technician'],'definition','four symbols in a ring',8.0,sc02)
Scene('th03','The Break','Iamblichus vs Porphyry — contemplation is not enough.','Aporrheton','','debate',['iamblichus','porphyry','contemplation'],'debate','two panels: thought vs ritual',8.0,sc03)
Scene('th04','Divinity in Smoke','The incense is god in the form of smoke.','Thymiama','','material',['incense','smoke','divine'],'material','rising smoke from censer',8.0,sc04)
Scene('th05','Containing Ecstasy','The formless accessed through perfect form.','Perioche','','containment',['ecstasy','vessel','form'],'vessel','flame in a vessel',8.0,sc05)
Scene('th06','The Descent','The gods descend because they are invited.','Katabasis','','invitation',['descent','invitation','sequence'],'descent','descending divine light',8.0,sc06)
Scene('th07','The Luminous Body','A body of light parallel to the physical.','Augeides sōma','','body',['luminous','body','vehicle'],'vehicle','light body within physical outline',8.0,sc07)
Scene('th08','Taking the Shape','Tuning an instrument to a divine frequency.','Morphē theōn','','channel',['shape','gods','channel'],'channel','figure expanding into resonance',8.0,sc08)
Scene('th09','The Anonymous Priest','The flute — the music belongs to the breath.','Anonymia','','anonymity',['anonymous','priest','transparency'],'transparency','flute with breath-music',8.0,sc09)
Scene('th10','Body as Furnace','Ritual as heat. God as gold.','Chrysopoeia','','transformation',['body','furnace','gold'],'transformation','body outline with gold at heart',6.0,sc10)
Scene('th11','Ontological Weight','You become by doing.','Dromenon','','seal',['action','becoming','descent'],'seal','radial ritual mandala',8.0,sc11)
Scene('th01','Ritual Is Not Symbolic','It changes the structure of reality.','Theourgia','','opening',['ritual','ontology','reality'],'intro','ritual vessel with inner glow',6.0,sc01)
Scene('th02','God-Work','The theurgist: technician of the divine.','Theourgia','','definition',['theurgy','god-work','technician'],'definition','four symbols in a ring',8.0,sc02)
Scene('th03','The Break','Iamblichus vs Porphyry — contemplation is not enough.','Aporrheton','','debate',['iamblichus','porphyry','contemplation'],'debate','two panels: thought vs ritual',8.0,sc03)
Scene('th04','Divinity in Smoke','The incense is god in the form of smoke.','Thymiama','','material',['incense','smoke','divine'],'material','rising smoke from censer',8.0,sc04)
Scene('th05','Containing Ecstasy','The formless accessed through perfect form.','Perioche','','containment',['ecstasy','vessel','form'],'vessel','flame in a vessel',8.0,sc05)
Scene('th06','The Descent','The gods descend because they are invited.','Katabasis','','invitation',['descent','invitation','sequence'],'descent','descending divine light',8.0,sc06)
Scene('th07','The Luminous Body','A body of light parallel to the physical.','Augeides sōma','','body',['luminous','body','vehicle'],'vehicle','light body within physical outline',8.0,sc07)
Scene('th08','Taking the Shape','Tuning an instrument to a divine frequency.','Morphē theōn','','channel',['shape','gods','channel'],'channel','figure expanding into resonance',8.0,sc08)
Scene('th09','The Anonymous Priest','The flute — the music belongs to the breath.','Anonymia','','anonymity',['anonymous','priest','transparency'],'transparency','flute with breath-music',8.0,sc09)
Scene('th10','Body as Furnace','Ritual as heat. God as gold.','Chrysopoeia','','transformation',['body','furnace','gold'],'transformation','body outline with gold at heart',6.0,sc10)
Scene('th11','Ontological Weight','You become by doing.','Dromenon','','seal',['action','becoming','descent'],'seal','radial ritual mandala',8.0,sc11)
Scene('th01','Ritual Is Not Symbolic','It changes the structure of reality.','Theourgia','','opening',['ritual','ontology','reality'],'intro','ritual vessel with inner glow',6.0,sc01)
Scene('th02','God-Work','The theurgist: technician of the divine.','Theourgia','','definition',['theurgy','god-work','technician'],'definition','four symbols in a ring',8.0,sc02)
Scene('th03','The Break','Iamblichus vs Porphyry — contemplation is not enough.','Aporrheton','','debate',['iamblichus','porphyry','contemplation'],'debate','two panels: thought vs ritual',8.0,sc03)
Scene('th04','Divinity in Smoke','The incense is god in the form of smoke.','Thymiama','','material',['incense','smoke','divine'],'material','rising smoke from censer',8.0,sc04)
Scene('th05','Containing Ecstasy','The formless accessed through perfect form.','Perioche','','containment',['ecstasy','vessel','form'],'vessel','flame in a vessel',8.0,sc05)
Scene('th06','The Descent','The gods descend because they are invited.','Katabasis','','invitation',['descent','invitation','sequence'],'descent','descending divine light',8.0,sc06)
Scene('th07','The Luminous Body','A body of light parallel to the physical.','Augeides sōma','','body',['luminous','body','vehicle'],'vehicle','light body within physical outline',8.0,sc07)
Scene('th08','Taking the Shape','Tuning an instrument to a divine frequency.','Morphē theōn','','channel',['shape','gods','channel'],'channel','figure expanding into resonance',8.0,sc08)
Scene('th09','The Anonymous Priest','The flute — the music belongs to the breath.','Anonymia','','anonymity',['anonymous','priest','transparency'],'transparency','flute with breath-music',8.0,sc09)
Scene('th10','Body as Furnace','Ritual as heat. God as gold.','Chrysopoeia','','transformation',['body','furnace','gold'],'transformation','body outline with gold at heart',6.0,sc10)
Scene('th11','Ontological Weight','You become by doing.','Dromenon','','seal',['action','becoming','descent'],'seal','radial ritual mandala',8.0,sc11)
    Scene('th01','Ritual Is Not Symbolic','It changes the structure of reality.','Theourgia','','opening',['ritual','ontology','reality'],'intro','ritual vessel with inner glow',6.0,sc01),
    Scene('th02','God-Work','The theurgist: technician of the divine.','Theourgia','','definition',['theurgy','god-work','technician'],'definition','four symbols in a ring',8.0,sc02),
    Scene('th03','The Break','Iamblichus vs Porphyry — contemplation is not enough.','Aporrheton','','debate',['iamblichus','porphyry','contemplation'],'debate','two panels: thought vs ritual',8.0,sc03),
    Scene('th04','Divinity in Smoke','The incense is god in the form of smoke.','Thymiama','','material',['incense','smoke','divine'],'material','rising smoke from censer',8.0,sc04),
    Scene('th05','Containing Ecstasy','The formless accessed through perfect form.','Perioche','','containment',['ecstasy','vessel','form'],'vessel','flame in a vessel',8.0,sc05),
    Scene('th06','The Descent','The gods descend because they are invited.','Katabasis','','invitation',['descent','invitation','sequence'],'descent','descending divine light',8.0,sc06),
    Scene('th07','The Luminous Body','A body of light parallel to the physical.','Augeides sōma','','body',['luminous','body','vehicle'],'vehicle','light body within physical outline',8.0,sc07),
    Scene('th08','Taking the Shape','Tuning an instrument to a divine frequency.','Morphē theōn','','channel',['shape','gods','channel'],'channel','figure expanding into resonance',8.0,sc08),
    Scene('th09','The Anonymous Priest','The flute — the music belongs to the breath.','Anonymia','','anonymity',['anonymous','priest','transparency'],'transparency','flute with breath-music',8.0,sc09),
    Scene('th10','Body as Furnace','Ritual as heat. God as gold.','Chrysopoeia','','transformation',['body','furnace','gold'],'transformation','body outline with gold at heart',6.0,sc10),
    Scene('th11','Ontological Weight','You become by doing.','Dromenon','','seal',['action','becoming','descent'],'seal','radial ritual mandala',8.0,sc11),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DARK_SANCTUM)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Theurgy — When the Gods Speak',
        'source_basis':'Expansion Essay 17: "when the gods speak" (Iamblichus/Shaw) — 11 scenes.',
        'style':{'family':'theurgic / temple visualization','background':'dark sanctum','ink':'temple gold, smoke, fire-amber'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Theurgy — 11 scenes, temple gold/smoke/amber palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Theurgy Pack — temple gold/smoke/amber ritual palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Theurgy — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'theurgy_iamblichus_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'theurgy_iamblichus_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['theurgy_iamblichus_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'theurgy_iamblichus_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
