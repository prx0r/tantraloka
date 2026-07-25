#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=22222

DEEP_VOID=(10,12,18); WARM_DARK=(18,16,18); DEEP=(12,14,22)
PRIMORDIAL=(235,240,245); GOLD=(206,166,88); GOLD_LIGHT=(246,218,144)
SILVER=(196,204,222); PEARL=(246,243,236); WHITE=(252,250,246)
TEAL=(88,140,142); DARK_SERPENT=(30,50,45); SLATE=(90,100,120)
MIST=(160,172,192); CRIMSON=(154,44,58); LAVENDER=(170,156,200)
STAR=GOLD_LIGHT

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30)
SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21)
SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)
DEVA_MED=ImageFont.truetype(FONT_DEVA:= '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf',26)

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
    d.rectangle((28,28,W-28,H-28),outline=rgba(GOLD,70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,TEAL,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(10,12,18,200),outline=rgba(GOLD,40),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(SILVER,STAR,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def hermetic_ground(seed,bg,glow_col,intensity=0.5):
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
    fs=SEED+int(t*9973)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,105),'what if the universe is a mind?',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,135),'every star, every stone, every thought',font=SMALL_FONT,fill=MIST,anchor='mm')
    d.text((cx,160),'is a thought within that mind',font=SMALL_FONT,fill=MIST,anchor='mm')
    rng=np.random.default_rng(222)
    for i in range(50):
        x=float(rng.uniform(60,W-60)); y=float(rng.uniform(170,450))
        r=float(rng.uniform(1,3)); a=int(40+160*ease_in_out(t)*(0.2+0.8*rng.random()))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(STAR,a))
    draw_glow(im,(cx,cy),18,GOLD,80,12)
    d.ellipse((cx-6,cy-6,cx+6,cy+6),fill=rgba(WHITE,220))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'i am poimandres',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'mind of sovereignty',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,150),'i am with you everywhere',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    dr=lerp(10,160,prog)
    draw_glow(im,(cx,cy+20),int(dr),GOLD_LIGHT,int(150*prog),30)
    d.ellipse((cx-int(dr*0.6),cy+20-int(dr*0.4),cx+int(dr*0.6),cy+20+int(dr*0.4)),fill=rgba(WHITE,int(180*prog)))
    d.ellipse((cx-12,cy-40,cx+12,cy-16),outline=rgba(SILVER,int(150*prog)),width=2)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'everything became light',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'clear and joyful',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'then darkness arose — coiling sinuously like a snake',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    r_light=lerp(200,80,clamp(prog*2))
    draw_glow(im,(cx,cy),int(r_light),GOLD_LIGHT,int(200*(1-clamp(prog*2))),30)
    d.ellipse((cx-int(r_light*0.5),cy-int(r_light*0.4),cx+int(r_light*0.5),cy+int(r_light*0.4)),fill=rgba(WHITE,int(200*(1-clamp(prog*2)))))
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        snake_pts=[]
        for i in range(80):
            u=i/79; x=cx-200+u*400; y=cy+120+60*math.sin(u*3+t*2)*p*0.5
            snake_pts.append((x,y))
        draw_line_glow(im,snake_pts,DARK_SERPENT,5,150,9)
        d.ellipse((cx-20,cy+100,cx+20,cy+140),outline=rgba(TEAL,int(100*p)),width=1)

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(hermetic_ground(fs,DEEP,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the light-giving word',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'who comes from mind',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,155),'is the son of god',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy-60),30,GOLD_LIGHT,100,16)
    d.ellipse((cx-10,cy-70,cx+10,cy-50),fill=rgba(WHITE,220))
    ray=bezier((cx,cy-50),(cx-20,cy-10),(cx+30,cy+30),(cx,cy+60),60)
    reveal=partial_polyline(ray,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,GOLD,3,110,7)
    if prog>0.7:
        p=clamp((prog-0.7)*3.3)
        draw_glow(im,(cx,cy+70),15,GOLD_LIGHT,int(100*p),12)
        d.ellipse((cx-6,cy+64,cx+6,cy+76),fill=rgba(WHITE,int(200*p)))

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'the mixing bowl',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'immerse yourself if your heart has the strength',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    prog=ease_in_out(t)
    bowl_y=lerp(100,300,prog)
    d.ellipse((cx-80,int(bowl_y-30),cx+80,int(bowl_y+20)),outline=rgba(GOLD,180),width=2)
    d.ellipse((cx-60,int(bowl_y-15),cx+60,int(bowl_y+5)),fill=rgba(GOLD_LIGHT,int(60*prog)))
    draw_glow(im,(cx,int(bowl_y+10)),30,GOLD_LIGHT,int(120*prog),18)
    d.text((cx,int(bowl_y-50)),'step in. drown. rise.',font=SMALL_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,470),'most hear it and keep walking. some step in and remember.',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(hermetic_ground(fs,WARM_DARK,TEAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the reflection',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'a boy sees his image in the water and dives in',font=TERM_FONT,fill=TEAL,anchor='mm')
    d.text((cx,155),'he forgets he was ever dry',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-80,cy+40,cx+80,cy+80),outline=rgba(TEAL,120),width=2)
    if prog<0.7:
        p=clamp(prog/0.7)
        draw_glow(im,(cx,cy+20-int(40*p)),15,SILVER,int(100*p),10)
        d.ellipse((cx-10,cy+10-int(40*p),cx+10,cy+30-int(40*p)),outline=rgba(SILVER,int(150*p)),width=2)
        d.ellipse((cx-45,cy+35-int(20*p),cx+45,cy+55-int(20*p)),outline=rgba(SILVER,int(100*p)),width=1)
    if prog>0.7:
        p=clamp((prog-0.7)/0.3)
        for i in range(10):
            x=cx-40+i*8; y=cy+50+10*math.sin(i+t*2)
            d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(TEAL,int(80*p)))

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'a thousand mirrors',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the god with all names and no name',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'every face is the same face',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for i in range(6):
        x=cx-140+56*i; y=cy+20
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        d.rounded_rectangle((x-22,y-30,x+22,y+30),radius=6,outline=rgba(SILVER,int(150*p)),width=2)
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(mix(GOLD,SILVER,i/6),int(150*p)))
    draw_glow(im,(cx,cy+20),15,GOLD,70,12)

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,80),'the ascent through the spheres',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'a garment left on each step',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    prog=ease_in_out(t)
    s_cols=[SLATE,TEAL,LAVENDER,GOLD,SILVER,CRIMSON,WHITE]
    s_names=['moon','mercury','venus','sun','mars','jupiter','saturn']
    for i in range(7):
        y=170+i*28
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        d.line((cx-100,y,cx+100,y),fill=rgba(s_cols[i],int(180*p)),width=2)
        d.text((cx-110,y-4),s_names[i],font=TINY_FONT,fill=rgba(s_cols[i],int(200*p)),anchor='rm')
    figure_y=lerp(380,180,prog)
    draw_glow(im,(cx,int(figure_y)),10,GOLD_LIGHT,int(150*prog),8)
    d.ellipse((cx-4,int(figure_y)-4,cx+4,int(figure_y)+4),fill=rgba(WHITE,255))

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(hermetic_ground(fs,DEEP,GOLD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,90),'stretch your arms',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'one hand touches the first morning',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,150),'the other touches the last evening',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    prog=ease_in_out(t)
    r=lerp(20,200,prog)
    d.ellipse((cx-r,cy-r*0.62,cx+r,cy+r*0.62),outline=rgba(GOLD,int(150*prog)),width=2)
    draw_glow(im,(cx,cy),int(r*0.3),GOLD_LIGHT,int(100*prog),14)
    d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=rgba(WHITE,255))
    d.text((cx,470),'you are the size of your willingness to stop measuring',font=SUB_FONT,fill=MIST,anchor='mm')

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(hermetic_ground(fs,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'sunlight on a window',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'it can see the light because it is made of the same light',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,152),'if it realized what it was made of, it would stop calling itself glass',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((300,200,980,380),radius=10,outline=rgba(GOLD,120),width=2)
    draw_glow(im,(300,290),40,GOLD_LIGHT,int(80*prog),25)
    d.line((300,200,980,380),fill=rgba(GOLD_LIGHT,int(80*prog)),width=1)
    d.line((300,380,980,200),fill=rgba(GOLD_LIGHT,int(80*prog)),width=1)
    draw_glow(im,(640,290),15,GOLD,int(100*prog),12)

def sc11(im,t):
    fs=SEED+int(t*9973+5000)%100000; im.paste(hermetic_ground(fs,DEEP_VOID,GOLD_LIGHT,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,85),'you are a thought',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'in the mind of the universe',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'that has learned to think itself',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,175),'the stars are in you — not above you',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    for i in range(36):
        a=i*2*math.pi/36+t*0.04; r=lerp(10,190,prog)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        draw_line_glow(im,[(cx,cy),(int(x),int(y))],mix(GOLD_LIGHT,SILVER,i/36),1,50,4)
    draw_glow(im,(cx,cy),30,GOLD_LIGHT,int(130*prog),16)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(GOLD,200),width=2)
    d.text((cx,cy),'νοῦς',font=TERM_FONT,fill=GOLD,anchor='mm')
    d.text((640,485),'the mixing bowl is the space between your next two breaths',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[,Scene('pm01','The Universe Is a Mind','Stars are thoughts. You are the part that is aware.','Nous','','opening',['mind','universe','stars'],'intro','star-field that is also neural',6.0,sc01)
Scene('pm02','Poimandres','Mind of sovereignty — I am with you everywhere.','Poimandres','','vision',['poimandres','vision','light'],'vision','vast luminous figure appearing',8.0,sc02)
Scene('pm03','Light and Serpent','Light arose — then darkness coiling like a snake.','Phōs kai skotos','','creation',['light','darkness','serpent'],'duality','primordial light yielding to coiling serpent',8.0,sc03)
Scene('pm04','The Light-Giving Word','The logos from mind — the son of god.','Logos','','emanation',['word','light','logos'],'emanation','ray of light descending from source',8.0,sc04)
Scene('pm05','The Mixing Bowl','Immerse yourself if your heart has the strength.','Krater','','invitation',['bowl','immersion','choice'],'invitation','great bowl of light descending',8.0,sc05)
Scene('pm06','The Reflection','A boy sees his image and dives in — forgets he was dry.','Katabasis','','descent',['reflection','descent','forgetting'],'descent','figure diving into water reflection',6.0,sc06)
Scene('pm07','A Thousand Mirrors','All names and no name — every face the same face.','Panonymos','','mirrors',['mirrors','names','one'],'manifestation','six mirrors reflecting one presence',8.0,sc07)
Scene('pm08','The Ascent','Leaving a garment on each sphere — at the top, nothing remains.','Anodos','','ascent',['spheres','ascent','shedding'],'ascent','seven spheres with figure ascending',8.0,sc08)
Scene('pm09','Stretch Your Arms','One hand touches the first morning. The other, the last evening.','Apeiros','','expansion',['measureless','expansion','cosmic'],'expansion','figure expanding to cosmic scale',6.0,sc09)
Scene('pm10','Sunlight on a Window','Made of the same light — if only it knew.','Homoiosis','','identity',['light','window','identity'],'identity','window with streaming light, realizing itself',8.0,sc10)
Scene('pm11','The Thought That Thinks Itself','The stars are in you. Step in. Drown. Rise.','Gnōsis','','seal',['thought','self-knowing','gnosis'],'seal','radial cosmic mandala with nous center',8.0,sc11)
Scene('pm01','The Universe Is a Mind','Stars are thoughts. You are the part that is aware.','Nous','','opening',['mind','universe','stars'],'intro','star-field that is also neural',6.0,sc01)
Scene('pm02','Poimandres','Mind of sovereignty — I am with you everywhere.','Poimandres','','vision',['poimandres','vision','light'],'vision','vast luminous figure appearing',8.0,sc02)
Scene('pm03','Light and Serpent','Light arose — then darkness coiling like a snake.','Phōs kai skotos','','creation',['light','darkness','serpent'],'duality','primordial light yielding to coiling serpent',8.0,sc03)
Scene('pm04','The Light-Giving Word','The logos from mind — the son of god.','Logos','','emanation',['word','light','logos'],'emanation','ray of light descending from source',8.0,sc04)
Scene('pm05','The Mixing Bowl','Immerse yourself if your heart has the strength.','Krater','','invitation',['bowl','immersion','choice'],'invitation','great bowl of light descending',8.0,sc05)
Scene('pm06','The Reflection','A boy sees his image and dives in — forgets he was dry.','Katabasis','','descent',['reflection','descent','forgetting'],'descent','figure diving into water reflection',6.0,sc06)
Scene('pm07','A Thousand Mirrors','All names and no name — every face the same face.','Panonymos','','mirrors',['mirrors','names','one'],'manifestation','six mirrors reflecting one presence',8.0,sc07)
Scene('pm08','The Ascent','Leaving a garment on each sphere — at the top, nothing remains.','Anodos','','ascent',['spheres','ascent','shedding'],'ascent','seven spheres with figure ascending',8.0,sc08)
Scene('pm09','Stretch Your Arms','One hand touches the first morning. The other, the last evening.','Apeiros','','expansion',['measureless','expansion','cosmic'],'expansion','figure expanding to cosmic scale',6.0,sc09)
Scene('pm10','Sunlight on a Window','Made of the same light — if only it knew.','Homoiosis','','identity',['light','window','identity'],'identity','window with streaming light, realizing itself',8.0,sc10)
Scene('pm11','The Thought That Thinks Itself','The stars are in you. Step in. Drown. Rise.','Gnōsis','','seal',['thought','self-knowing','gnosis'],'seal','radial cosmic mandala with nous center',8.0,sc11)
Scene('pm01','The Universe Is a Mind','Stars are thoughts. You are the part that is aware.','Nous','','opening',['mind','universe','stars'],'intro','star-field that is also neural',6.0,sc01)
Scene('pm02','Poimandres','Mind of sovereignty — I am with you everywhere.','Poimandres','','vision',['poimandres','vision','light'],'vision','vast luminous figure appearing',8.0,sc02)
Scene('pm03','Light and Serpent','Light arose — then darkness coiling like a snake.','Phōs kai skotos','','creation',['light','darkness','serpent'],'duality','primordial light yielding to coiling serpent',8.0,sc03)
Scene('pm04','The Light-Giving Word','The logos from mind — the son of god.','Logos','','emanation',['word','light','logos'],'emanation','ray of light descending from source',8.0,sc04)
Scene('pm05','The Mixing Bowl','Immerse yourself if your heart has the strength.','Krater','','invitation',['bowl','immersion','choice'],'invitation','great bowl of light descending',8.0,sc05)
Scene('pm06','The Reflection','A boy sees his image and dives in — forgets he was dry.','Katabasis','','descent',['reflection','descent','forgetting'],'descent','figure diving into water reflection',6.0,sc06)
Scene('pm07','A Thousand Mirrors','All names and no name — every face the same face.','Panonymos','','mirrors',['mirrors','names','one'],'manifestation','six mirrors reflecting one presence',8.0,sc07)
Scene('pm08','The Ascent','Leaving a garment on each sphere — at the top, nothing remains.','Anodos','','ascent',['spheres','ascent','shedding'],'ascent','seven spheres with figure ascending',8.0,sc08)
Scene('pm09','Stretch Your Arms','One hand touches the first morning. The other, the last evening.','Apeiros','','expansion',['measureless','expansion','cosmic'],'expansion','figure expanding to cosmic scale',6.0,sc09)
Scene('pm10','Sunlight on a Window','Made of the same light — if only it knew.','Homoiosis','','identity',['light','window','identity'],'identity','window with streaming light, realizing itself',8.0,sc10)
Scene('pm11','The Thought That Thinks Itself','The stars are in you. Step in. Drown. Rise.','Gnōsis','','seal',['thought','self-knowing','gnosis'],'seal','radial cosmic mandala with nous center',8.0,sc11)
    Scene('pm01','The Universe Is a Mind','Stars are thoughts. You are the part that is aware.','Nous','','opening',['mind','universe','stars'],'intro','star-field that is also neural',6.0,sc01),
    Scene('pm02','Poimandres','Mind of sovereignty — I am with you everywhere.','Poimandres','','vision',['poimandres','vision','light'],'vision','vast luminous figure appearing',8.0,sc02),
    Scene('pm03','Light and Serpent','Light arose — then darkness coiling like a snake.','Phōs kai skotos','','creation',['light','darkness','serpent'],'duality','primordial light yielding to coiling serpent',8.0,sc03),
    Scene('pm04','The Light-Giving Word','The logos from mind — the son of god.','Logos','','emanation',['word','light','logos'],'emanation','ray of light descending from source',8.0,sc04),
    Scene('pm05','The Mixing Bowl','Immerse yourself if your heart has the strength.','Krater','','invitation',['bowl','immersion','choice'],'invitation','great bowl of light descending',8.0,sc05),
    Scene('pm06','The Reflection','A boy sees his image and dives in — forgets he was dry.','Katabasis','','descent',['reflection','descent','forgetting'],'descent','figure diving into water reflection',6.0,sc06),
    Scene('pm07','A Thousand Mirrors','All names and no name — every face the same face.','Panonymos','','mirrors',['mirrors','names','one'],'manifestation','six mirrors reflecting one presence',8.0,sc07),
    Scene('pm08','The Ascent','Leaving a garment on each sphere — at the top, nothing remains.','Anodos','','ascent',['spheres','ascent','shedding'],'ascent','seven spheres with figure ascending',8.0,sc08),
    Scene('pm09','Stretch Your Arms','One hand touches the first morning. The other, the last evening.','Apeiros','','expansion',['measureless','expansion','cosmic'],'expansion','figure expanding to cosmic scale',6.0,sc09),
    Scene('pm10','Sunlight on a Window','Made of the same light — if only it knew.','Homoiosis','','identity',['light','window','identity'],'identity','window with streaming light, realizing itself',8.0,sc10),
    Scene('pm11','The Thought That Thinks Itself','The stars are in you. Step in. Drown. Rise.','Gnōsis','','seal',['thought','self-knowing','gnosis'],'seal','radial cosmic mandala with nous center',8.0,sc11),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DEEP_VOID)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Poimandres — The Mind That Thinks Through You',
        'source_basis':'Expansion Essay 22: "the mind that\'s thinking through you" (Hermetica) — 11 scenes.',
        'style':{'family':'hermetic/primordial light visualization','background':'deep void','ink':'gold-light, silver, teal, dark serpent'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Poimandres — 11 scenes, primordial light/serpent/bowl palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Poimandres Pack — primordial gold/teal/serpent-dark palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Poimandres — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'poimandres_hermetic_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'poimandres_hermetic_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['poimandres_hermetic_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'poimandres_hermetic_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
