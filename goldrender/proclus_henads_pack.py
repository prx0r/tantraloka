#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=11111

DEEP_VOID=(12,14,22); WARM_DARK=(18,16,20); DEEP=(14,14,20)
CRYSTAL=(200,215,230); SILVER=(196,204,222); WHITE=(252,250,246)
PEARL=(246,243,236); GOLD=(206,166,88); GOLD_LIGHT=(246,218,144)
LAVENDER=(170,156,200); TEAL=(92,146,148); SLATE=(90,100,120)
MIST=(160,172,192); INDIGO=(68,78,136); CORAL=(206,108,100)

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
        d.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42),fill=rgba(outer,145),outline=rgba(mix(inner,PEARL,.3),180),width=1)
    d.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(CRYSTAL,SILVER,.5),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(CRYSTAL,SILVER,.3),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,INDIGO,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,14,22,200),outline=rgba(mix(CRYSTAL,SILVER,.3),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(mix(CRYSTAL,SILVER,.5),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)

def proclus_ground(seed,bg,glow_col,intensity=0.5):
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

def draw_facet(d,cx,cy,r,rot,prog,col):
    n=6
    ang=rot
    for i in range(n):
        a=ang+i*2*math.pi/n
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        x2=cx+math.cos(a)*r*0.5; y2=cy+math.sin(a)*r*0.3
        d.line([(cx,cy),(int(x),int(y))],fill=rgba(col,int(180*prog)),width=1)
        d.line([(int(x2),int(y2)),(int(x),int(y))],fill=rgba(col,int(100*prog)),width=1)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(proclus_ground(fs,DEEP_VOID,CRYSTAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'what if the entire universe',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'is a reflection of a single reality',font=TERM_FONT,fill=CRYSTAL,anchor='mm')
    d.text((cx,155),'that cannot be seen directly?',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((380,200,900,380),radius=16,outline=rgba(CRYSTAL,int(150*prog)),width=2)
    draw_glow(im,(700,260),40,GOLD_LIGHT,int(80*prog),20)
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        d.ellipse((640-8,290-8,640+8,290+8),fill=rgba(WHITE,int(200*p)))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(proclus_ground(fs,DEEP_VOID,SILVER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the one is the mirror itself',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'not the image in it',font=TERM_FONT,fill=SILVER,anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((450,180,830,390),radius=20,outline=rgba(SILVER,int(180*prog)),width=2)
    draw_glow(im,(640,285),20,GOLD_LIGHT,int(80*prog),14)
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        d.ellipse((640-30*p,275-20*p,640+30*p,295+20*p),fill=rgba(CRYSTAL,int(60*p)))
    d.text((640,470),'images pass across it. the mirror is untouched.',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(proclus_ground(fs,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'a diamond has many facets',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'each one shows the entire diamond',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,150),'from a different angle',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    rot=t*0.3
    draw_facet(d,cx,cy+30,140,rot,prog,GOLD)
    draw_facet(d,cx,cy+30,70,rot+0.5,prog,CRYSTAL)
    draw_glow(im,(cx,cy+30),ease_in_out(t)*15,GOLD_LIGHT,int(100*prog),12)
    d.ellipse((cx-6,cy+24,cx+6,cy+36),fill=rgba(WHITE,int(220*prog)))

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(proclus_ground(fs,DEEP_VOID,CRYSTAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'every god is a self-complete henad',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the whole from a specific perspective',font=TERM_FONT,fill=CRYSTAL,anchor='mm')
    prog=ease_in_out(t)
    for i in range(8):
        a=i*2*math.pi/8+t*0.05; r=lerp(10,150,prog)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        p=clamp(prog*1.2-i*0.06)
        if p<=0: continue
        draw_line_glow(im,[(cx,cy),(int(x),int(y))],mix(CRYSTAL,GOLD,i/8),1,60,4)
        d.ellipse((int(x)-6,int(y)-6,int(x)+6,int(y)+6),outline=rgba(CRYSTAL,int(160*p)),width=2)
        d.ellipse((int(x)-3,int(y)-3,int(x)+3,int(y)+3),fill=rgba(GOLD_LIGHT,int(140*p)))
    draw_glow(im,(cx,cy),15,GOLD_LIGHT,100,10)

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(proclus_ground(fs,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'remaining — proceeding — returning',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the movement outward is the movement inward',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'seen from the other side',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=rgba(WHITE,220))
    pts=bezier((cx,cy),(cx+120,cy-60),(cx+150,cy+40),(cx,cy+80),80)
    reveal=partial_polyline(pts,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,GOLD,3,110,7)
    pts2=bezier((cx,cy),(cx-120,cy-60),(cx-150,cy+40),(cx,cy+80),80)
    reveal2=partial_polyline(pts2,prog)
    if len(reveal2)>1: draw_line_glow(im,reveal2,SILVER,2,80,6)
    d.text((cx+60,cy-30),'proceeding',font=TINY_FONT,fill=GOLD,anchor='mm')
    d.text((cx-60,cy-30),'returning',font=TINY_FONT,fill=SILVER,anchor='mm')
    d.text((cx,cy+85),'remaining',font=TINY_FONT,fill=GOLD_LIGHT,anchor='mm')

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(proclus_ground(fs,DEEP,TEAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'intellect is being and knowing simultaneously',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'thinking and being are the same act',font=TERM_FONT,fill=TEAL,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+20),40,GOLD_LIGHT,int(100*prog),20)
    d.arc((cx-25,cy-5,cx+25,cy+45),180,360,fill=rgba(CRYSTAL,int(180*prog)),width=3)
    d.arc((cx-25,cy-5,cx+25,cy+45),0,180,fill=rgba(CRYSTAL,int(180*prog)),width=3)
    d.ellipse((cx-4,cy+18,cx+4,cy+22),fill=rgba(WHITE,int(220*prog)))
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        pts=bezier((cx,cy+20),(cx-60,cy-20),(cx+80,cy-10),(cx,cy-60),60)
        reveal=partial_polyline(pts,p)
        if len(reveal)>1: draw_line_glow(im,reveal,GOLD_LIGHT,2,90,6)

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(proclus_ground(fs,WARM_DARK,INDIGO,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'soul has forgotten it is also intellect',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'it descends into time and space',font=TERM_FONT,fill=INDIGO,anchor='mm')
    d.text((cx,145),'learning what it already knows',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy-80),12,GOLD_LIGHT,int(100*prog),8)
    d.ellipse((cx-5,cy-85,cx+5,cy-75),fill=rgba(WHITE,int(200*prog)))
    pt=bezier((cx,cy-80),(cx-40,cy-40),(cx+30,cy+20),(cx,cy+60),60)
    reveal=partial_polyline(pt,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,INDIGO,2,90,6)
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        d.ellipse((cx-5,cy+55,cx+5,cy+65),fill=rgba(WHITE,int(120*p)))
    for i in range(4):
        y=cy-50+i*25
        d.line((cx-30,y,cx+30,y),fill=rgba(SLATE,int(60*prog)),width=1)

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(proclus_ground(fs,DEEP_VOID,CRYSTAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,80),'the hierarchy',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'gods — daimons — souls — matter',font=TERM_FONT,fill=CRYSTAL,anchor='mm')
    d.text((cx,140),'each level contains every level above it in compressed form',font=SMALL_FONT,fill=MIST,anchor='mm')
    levels=['gods','daimons','souls','matter']
    l_cols=[GOLD,LAVENDER,TEAL,SLATE]
    prog=smoothstep(0.05,0.9,t)
    for i in range(4):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        y=190+i*55
        d.rounded_rectangle((cx-120,y,cx+120,y+35),radius=8,outline=rgba(l_cols[i],int(180*p)),width=2)
        d.text((cx-80,y+17),levels[i],font=SMALL_FONT,fill=rgba(l_cols[i],int(200*p)),anchor='mm')
        n_small=4-i
        for j in range(n_small):
            d.ellipse((cx+40+j*12,y+10+j*2,cx+40+j*12+6,y+16+j*2),fill=rgba(l_cols[i],int(120*p)))
        if i<3:
            pts=partial_polyline([(cx,y+35),(cx,y+190+(i+1)*55)],p)
            if len(pts)>1: draw_line_glow(im,pts,l_cols[i],1,50,3)

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(proclus_ground(fs,WARM_DARK,LAVENDER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the daimons translate',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the will of the gods',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,145),'into the experience of souls',font=TERM_FONT,fill=LAVENDER,anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy-70),20,GOLD,int(80*prog),14)
    d.ellipse((cx-8,cy-78,cx+8,cy-62),fill=rgba(WHITE,int(200*prog)))
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        draw_glow(im,(cx,cy+20),15,LAVENDER,int(100*p),12)
        d.ellipse((cx-6,cy+14,cx+6,cy+26),fill=rgba(WHITE,int(200*p)))
        pts1=partial_polyline(bezier((cx,cy-62),(cx-30,cy-20),(cx+20,cy),(cx,cy+14),60),p)
        pts2=partial_polyline(bezier((cx,cy-62),(cx+30,cy-20),(cx-20,cy),(cx,cy+14),60),p)
        if len(pts1)>1: draw_line_glow(im,pts1,GOLD,2,80,5)
        if len(pts2)>1: draw_line_glow(im,pts2,LAVENDER,2,80,5)
    d.text((640,475),'the hands of the divine, reaching down and up',font=SUB_FONT,fill=MIST,anchor='mm')

def sc10(im,t):
    fs=SEED+int(t*9973+4500)%100000; im.paste(proclus_ground(fs,WARM_DARK,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'you are one facet',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'polish it — the whole shines more brightly',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx,152),'your angle on the infinite is irreplaceable',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease_in_out(t)
    draw_facet(d,cx,cy+20,120,t*0.2,prog,GOLD)
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        draw_facet(d,cx,cy+20,120+20*p,t*0.2+0.3,prog,CRYSTAL)
        draw_glow(im,(cx,cy+20),25,GOLD_LIGHT,int(140*p),16)
    d.ellipse((cx-10,cy+10,cx+10,cy+30),fill=rgba(WHITE,int(255*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    d.text((640,485),'every act of attention polishes the mirror of the universe',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[,Scene('pl01','A Single Reflection','The entire universe is a reflection of one reality.','Hen','','opening',['reflection','one','mirror'],'intro','mirror reflecting luminous source',6.0,sc01)
Scene('pl02','The Mirror Itself','The one is the mirror — not the images in it.','To Hen','','one',['one','mirror','source'],'one','mirror surface with passing images',8.0,sc02)
Scene('pl03','The Diamond Facets','Many facets — each shows the entire diamond.','Henade','','facets',['diamond','facets','whole'], 'henads', 'rotating diamond with many facets',8.0,sc03)
Scene('pl04','Self-Complete Henads','The whole from a specific perspective.','Henas','','henads',['henads','perspective','whole'],'henads','radiating facets from one center',8.0,sc04)
Scene('pl05','Remaining, Proceeding, Returning','The outward movement is the inward movement, seen from the other side.','Monē, proodos, epistrophē','','triad',['remaining','proceeding','returning'],'triad','three-part path from and back to center',8.0,sc05)
Scene('pl06','Intellect','Being and knowing simultaneously.','Nous','','intellect',['intellect','knowing','being'],'intellect','eye that is also the light it sees by',8.0,sc06)
Scene('pl07','Soul\'s Descent','Soul forgets it is intellect — descends into time and space.','Psychē','','soul',['soul','descent','forgetting'],'soul','point descending through layers forgetting',8.0,sc07)
Scene('pl08','The Hierarchy','Gods, daimons, souls, matter — same thing at different compression.','Diakosmos','','hierarchy',['gods','daimons','souls','matter'],'hierarchy','four levels with preceding compression',6.0,sc08)
Scene('pl09','The Daimons','Translating the will of the gods into the experience of souls.','Daimones','','mediation',['daimons','translation','mediation'],'mediation','middle figure receiving and transmitting light',8.0,sc09)
Scene('pl10','Polish Your Facet','Your angle on the infinite is irreplaceable.','Epistrophē','','seal',['facet','polishing','whole'],'seal','facet becoming transparent, whole brightening',8.0,sc10)
Scene('pl01','A Single Reflection','The entire universe is a reflection of one reality.','Hen','','opening',['reflection','one','mirror'],'intro','mirror reflecting luminous source',6.0,sc01)
Scene('pl02','The Mirror Itself','The one is the mirror — not the images in it.','To Hen','','one',['one','mirror','source'],'one','mirror surface with passing images',8.0,sc02)
Scene('pl03','The Diamond Facets','Many facets — each shows the entire diamond.','Henade','','facets',['diamond','facets','whole'], 'henads', 'rotating diamond with many facets',8.0,sc03)
Scene('pl04','Self-Complete Henads','The whole from a specific perspective.','Henas','','henads',['henads','perspective','whole'],'henads','radiating facets from one center',8.0,sc04)
Scene('pl05','Remaining, Proceeding, Returning','The outward movement is the inward movement, seen from the other side.','Monē, proodos, epistrophē','','triad',['remaining','proceeding','returning'],'triad','three-part path from and back to center',8.0,sc05)
Scene('pl06','Intellect','Being and knowing simultaneously.','Nous','','intellect',['intellect','knowing','being'],'intellect','eye that is also the light it sees by',8.0,sc06)
Scene('pl07','Soul\'s Descent','Soul forgets it is intellect — descends into time and space.','Psychē','','soul',['soul','descent','forgetting'],'soul','point descending through layers forgetting',8.0,sc07)
Scene('pl08','The Hierarchy','Gods, daimons, souls, matter — same thing at different compression.','Diakosmos','','hierarchy',['gods','daimons','souls','matter'],'hierarchy','four levels with preceding compression',6.0,sc08)
Scene('pl09','The Daimons','Translating the will of the gods into the experience of souls.','Daimones','','mediation',['daimons','translation','mediation'],'mediation','middle figure receiving and transmitting light',8.0,sc09)
Scene('pl10','Polish Your Facet','Your angle on the infinite is irreplaceable.','Epistrophē','','seal',['facet','polishing','whole'],'seal','facet becoming transparent, whole brightening',8.0,sc10)
Scene('pl01','A Single Reflection','The entire universe is a reflection of one reality.','Hen','','opening',['reflection','one','mirror'],'intro','mirror reflecting luminous source',6.0,sc01)
Scene('pl02','The Mirror Itself','The one is the mirror — not the images in it.','To Hen','','one',['one','mirror','source'],'one','mirror surface with passing images',8.0,sc02)
Scene('pl03','The Diamond Facets','Many facets — each shows the entire diamond.','Henade','','facets',['diamond','facets','whole'], 'henads', 'rotating diamond with many facets',8.0,sc03)
Scene('pl04','Self-Complete Henads','The whole from a specific perspective.','Henas','','henads',['henads','perspective','whole'],'henads','radiating facets from one center',8.0,sc04)
Scene('pl05','Remaining, Proceeding, Returning','The outward movement is the inward movement, seen from the other side.','Monē, proodos, epistrophē','','triad',['remaining','proceeding','returning'],'triad','three-part path from and back to center',8.0,sc05)
Scene('pl06','Intellect','Being and knowing simultaneously.','Nous','','intellect',['intellect','knowing','being'],'intellect','eye that is also the light it sees by',8.0,sc06)
Scene('pl07','Soul\'s Descent','Soul forgets it is intellect — descends into time and space.','Psychē','','soul',['soul','descent','forgetting'],'soul','point descending through layers forgetting',8.0,sc07)
Scene('pl08','The Hierarchy','Gods, daimons, souls, matter — same thing at different compression.','Diakosmos','','hierarchy',['gods','daimons','souls','matter'],'hierarchy','four levels with preceding compression',6.0,sc08)
Scene('pl09','The Daimons','Translating the will of the gods into the experience of souls.','Daimones','','mediation',['daimons','translation','mediation'],'mediation','middle figure receiving and transmitting light',8.0,sc09)
Scene('pl10','Polish Your Facet','Your angle on the infinite is irreplaceable.','Epistrophē','','seal',['facet','polishing','whole'],'seal','facet becoming transparent, whole brightening',8.0,sc10)
    Scene('pl01','A Single Reflection','The entire universe is a reflection of one reality.','Hen','','opening',['reflection','one','mirror'],'intro','mirror reflecting luminous source',6.0,sc01),
    Scene('pl02','The Mirror Itself','The one is the mirror — not the images in it.','To Hen','','one',['one','mirror','source'],'one','mirror surface with passing images',8.0,sc02),
    Scene('pl03','The Diamond Facets','Many facets — each shows the entire diamond.','Henade','','facets',['diamond','facets','whole'], 'henads', 'rotating diamond with many facets',8.0,sc03),
    Scene('pl04','Self-Complete Henads','The whole from a specific perspective.','Henas','','henads',['henads','perspective','whole'],'henads','radiating facets from one center',8.0,sc04),
    Scene('pl05','Remaining, Proceeding, Returning','The outward movement is the inward movement, seen from the other side.','Monē, proodos, epistrophē','','triad',['remaining','proceeding','returning'],'triad','three-part path from and back to center',8.0,sc05),
    Scene('pl06','Intellect','Being and knowing simultaneously.','Nous','','intellect',['intellect','knowing','being'],'intellect','eye that is also the light it sees by',8.0,sc06),
    Scene('pl07','Soul\'s Descent','Soul forgets it is intellect — descends into time and space.','Psychē','','soul',['soul','descent','forgetting'],'soul','point descending through layers forgetting',8.0,sc07),
    Scene('pl08','The Hierarchy','Gods, daimons, souls, matter — same thing at different compression.','Diakosmos','','hierarchy',['gods','daimons','souls','matter'],'hierarchy','four levels with preceding compression',6.0,sc08),
    Scene('pl09','The Daimons','Translating the will of the gods into the experience of souls.','Daimones','','mediation',['daimons','translation','mediation'],'mediation','middle figure receiving and transmitting light',8.0,sc09),
    Scene('pl10','Polish Your Facet','Your angle on the infinite is irreplaceable.','Epistrophē','','seal',['facet','polishing','whole'],'seal','facet becoming transparent, whole brightening',8.0,sc10),
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
    manifest={'project':'Proclus — One Thing Looking at Itself',
        'source_basis':'Expansion Essay 11: "one thing looking at itself" (Proclus, Elements of Theology) — 10 scenes.',
        'style':{'family':'henadic / diamond-facet visualization','background':'deep void','ink':'crystal, silver, gold, lavender'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Proclus — 10 scenes, crystal/silver/gold henadic palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Proclus Pack — crystal/silver/gold diamond-facet palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Proclus — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'proclus_henads_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'proclus_henads_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['proclus_henads_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'proclus_henads_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
