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
DURATION = 4.8
NFRAMES = int(FPS * DURATION)
SEED = 101010

# gallery / observer-field palette
NIGHT = (19, 22, 31)
OBSIDIAN = (27, 30, 41)
INK = (34, 38, 49)
IVORY = (246, 243, 236)
WHITE = (252, 250, 246)
MIST = (177, 185, 201)
SLATE = (109, 121, 144)
SILVER = (211, 217, 229)
GOLD = (205, 166, 88)
GOLD_LIGHT = (245, 214, 143)
CRIMSON = (154, 51, 68)
ROSE = (191, 113, 145)
VIOLET = (124, 110, 176)
INDIGO = (70, 82, 144)
DEEP_INDIGO = (45, 55, 101)
TEAL = (88, 145, 150)
GREEN = (106, 151, 113)
COPPER = (177, 113, 73)
BLUE = (104, 137, 184)
BLACK = (12, 13, 17)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)

PERCEIVERS = [
    ('Sakala', CRIMSON),
    ('Pralayākala', SLATE),
    ('Vijñānākala', VIOLET),
    ('Mantra', TEAL),
    ('Mantreśvara', BLUE),
    ('Mantramaheśvara', GOLD),
    ('Śiva', WHITE),
]


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a,b,t):
    return a + (b-a)*clamp(t)


def mix(c1,c2,t):
    t=clamp(t)
    return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))


def smoothstep(a,b,x):
    if a==b:
        return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a))
    return t*t*(3-2*t)


def ease_in_out(t):
    t=clamp(t)
    return .5-.5*math.cos(math.pi*t)


def ease_out_cubic(t):
    t=clamp(t)
    return 1-(1-t)**3


def rgba(c,a=255):
    return (*c[:3], int(a))


def ground(seed:int):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(OBSIDIAN, dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.2 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*18,0,27)
    base -= vign[...,None]
    halo=np.exp(-(((xx-W/2)/(W*.28))**2 + ((yy-H*.40)/(H*.26))**2)*2.5)
    for i in range(3):
        base[...,i]+=halo*(20 if i==2 else 7)
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA',(W,H),(0,0,0,0))


def draw_glow(im,xy,radius,color,alpha=150,blur=16):
    gl=layer(); d=ImageDraw.Draw(gl)
    x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius), fill=rgba(color,alpha))
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im,pts,color,width=3,alpha=150,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color,alpha), width=max(1,width*3), joint='curve')
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color,min(255,alpha+70)), width=width, joint='curve')


def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8
        x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42), fill=rgba(outer,140), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(MIST,110), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,82), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,DEEP_INDIGO,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im)
    y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(18,21,30,198), outline=rgba(MIST,65), width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=IVORY)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)


def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
        y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
        pts.append((x,y))
    return pts


def partial_polyline(points,amount):
    amount=clamp(amount)
    if amount<=0:return []
    if amount>=1:return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx
    out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]
        out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out


def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    pts=[p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)]
    draw.polygon(pts,fill=rgba(color,230))


def dust(im,seed,n=64):
    rng=np.random.default_rng(seed)
    ov=layer();d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(22,75))))
    im.alpha_composite(ov)


def draw_lotus(draw,cx,cy,scale=1.0,col=GOLD_LIGHT,fill=None,petals=8):
    fill=fill or rgba(col,26)
    for i in range(petals):
        a=-math.pi/2+i*2*math.pi/petals
        px=cx+math.cos(a)*34*scale; py=cy+math.sin(a)*24*scale
        bbox=(px-20*scale,py-34*scale,px+20*scale,py+34*scale)
        draw.ellipse(bbox, outline=rgba(col,190), fill=fill, width=max(1,int(2*scale)))
    draw.ellipse((cx-20*scale,cy-20*scale,cx+20*scale,cy+20*scale), fill=rgba(WHITE,235), outline=rgba(col,220), width=2)


def draw_lens(draw,x,y,w,h,col,alpha=110):
    draw.rounded_rectangle((x-w/2,y-h/2,x+w/2,y+h/2), radius=int(min(w,h)*.22), outline=rgba(col,190), fill=rgba(mix(OBSIDIAN,col,.16),alpha), width=2)


def draw_eye(draw,cx,cy,scale=1.0,col=GOLD_LIGHT):
    draw.arc((cx-60*scale,cy-26*scale,cx+60*scale,cy+26*scale),180,360,fill=rgba(col,210),width=max(1,int(3*scale)))
    draw.arc((cx-60*scale,cy-26*scale,cx+60*scale,cy+26*scale),0,180,fill=rgba(col,210),width=max(1,int(3*scale)))
    draw.ellipse((cx-12*scale,cy-12*scale,cx+12*scale,cy+12*scale),fill=rgba(col,220))


def draw_object(draw,cx,cy,scale=1.0,col=GOLD_LIGHT,mode='lotus'):
    if mode=='lotus':
        draw_lotus(draw,cx,cy,scale,col,rgba(col,20),8)
    elif mode=='disc':
        draw.ellipse((cx-48*scale,cy-48*scale,cx+48*scale,cy+48*scale),outline=rgba(col,220),fill=rgba(col,25),width=2)
        for i in range(8):
            a=i*2*math.pi/8
            draw.line((cx,cy,cx+math.cos(a)*42*scale,cy+math.sin(a)*42*scale),fill=rgba(col,100),width=1)


def draw_fragmented_lotus(draw,cx,cy,scale=1.0,col=CRIMSON):
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        px=cx+math.cos(a)*48*scale; py=cy+math.sin(a)*34*scale
        ox=math.cos(a)*16*scale; oy=math.sin(a)*16*scale
        draw.ellipse((px-18*scale+ox,py-28*scale+oy,px+18*scale+ox,py+28*scale+oy),outline=rgba(col,190),fill=rgba(col,20),width=2)
    draw.ellipse((cx-14*scale,cy-14*scale,cx+14*scale,cy+14*scale),outline=rgba(col,190),width=2)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; textual_anchor:str; source_status:str; philological_confidence:str; creative_visual_inference:str; draw_fn:Callable[[Image.Image,float],None]


# ---------- scene functions ----------

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    draw_glow(im,(cx,cy),70,GOLD_LIGHT,115,18); draw_object(d,cx,cy,1.0,GOLD_LIGHT)
    for i,(name,col) in enumerate(PERCEIVERS):
        a=-math.pi/2+i*2*math.pi/7
        x=cx+math.cos(a)*310; y=cy+math.sin(a)*175
        draw_lens(d,x,y,128,70,col,90)
        d.text((x,y),name,font=SMALL_FONT,fill=col,anchor='mm')
        pts=partial_polyline(bezier((cx,cy),(cx+math.cos(a)*90,cy+math.sin(a)*50),(x-math.cos(a)*65,y-math.sin(a)*36),(x,y),80), smoothstep(.02+i*.04,.76+i*.03,t))
        if len(pts)>1: draw_line_glow(im,pts,col,2,75,5)
    d.text((640,510),'one object, seven observer architectures, differentiated manifestation',font=SUB_FONT,fill=MIST,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    draw_object(d,cx,cy,1.25,GOLD_LIGHT)
    for r,col in [(90,GOLD_LIGHT),(145,SILVER),(205,INDIGO)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    for i in range(12):
        a=i*2*math.pi/12+t*.06
        x=cx+math.cos(a)*205; y=cy+math.sin(a)*148
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD_LIGHT,INDIGO,i/12),190))
    d.text((640,485),'perceptibility belongs to the manifest nature of the entity',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,252
    draw_object(d,cx,cy,1.05,GOLD_LIGHT)
    for i,(name,col) in enumerate(PERCEIVERS):
        x=175+i*155; y=420
        draw_lens(d,x,y,116,64,col,85)
        d.text((x,y),str(i+1),font=TERM_FONT,fill=col,anchor='mm')
        pts=partial_polyline(bezier((cx,cy+45),(cx+(x-cx)*.25,cy+90),(x,y-80),(x,y-34),80),smoothstep(.03+i*.04,.78+i*.02,t))
        if len(pts)>1: draw_line_glow(im,pts,col,2,80,5)
    d.text((640,505),'common perceptibility does not require identical appearance',font=SUB_FONT,fill=MIST,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    for i,col in enumerate([CRIMSON,SLATE,COPPER]):
        inset=40+i*34
        d.rounded_rectangle((180+inset,120+inset,1100-inset,450-inset),radius=20,outline=rgba(col,150),width=2,fill=rgba(mix(OBSIDIAN,col,.12),30))
    draw_fragmented_lotus(d,cx,cy,1.15,CRIMSON)
    for i in range(16):
        a=i*2*math.pi/16
        x=cx+math.cos(a)*250; y=cy+math.sin(a)*135
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(CRIMSON,COPPER,i/16),170))
    d.text((640,505),'all three impurities fragment the field into separate objects',font=SUB_FONT,fill=MIST,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    draw_glow(im,(cx,cy),100,SLATE,70,26)
    for r in [50,95,145,205]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(SLATE,95),width=2)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=rgba(BLACK,255),outline=rgba(SLATE,200),width=2)
    d.text((640,505),'the object-field is withdrawn into uniform objectless darkness',font=SUB_FONT,fill=MIST,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    draw_glow(im,(cx,cy),80,VIOLET,90,22)
    d.ellipse((cx-44,cy-44,cx+44,cy+44),fill=rgba(mix(OBSIDIAN,VIOLET,.18),130),outline=rgba(VIOLET,220),width=3)
    draw_eye(d,cx,cy,.55,VIOLET)
    # absent object as broken outer ring
    for i in range(10):
        a0=i*2*math.pi/10+.12; a1=a0+.35
        pts=[(cx+math.cos(lerp(a0,a1,j/18))*210,cy+math.sin(lerp(a0,a1,j/18))*145) for j in range(19)]
        d.line(pts,fill=rgba(SLATE,70),width=2)
    d.text((640,505),'pure subjectivity remains, but without an objective world',font=SUB_FONT,fill=MIST,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    draw_glow(im,(cx-75,cy),45,TEAL,100,15); draw_glow(im,(cx+75,cy),45,GOLD_LIGHT,85,15)
    draw_eye(d,cx-75,cy,.6,TEAL); draw_object(d,cx+75,cy,.6,GOLD_LIGHT)
    draw_line_glow(im,[(cx-15,cy),(cx+15,cy)],mix(TEAL,GOLD_LIGHT,.5),3,115,6)
    d.text((cx-75,200),'I',font=TERM_FONT,fill=TEAL,anchor='mm'); d.text((cx+75,200),'This',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the universe is self-expression, though a faint distinction remains',font=SUB_FONT,fill=MIST,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    draw_eye(d,cx,cy,.8,BLUE)
    for i in range(9):
        a=-math.pi/2+i*2*math.pi/9+t*.04
        x=cx+math.cos(a)*210; y=cy+math.sin(a)*135
        d.rounded_rectangle((x-30,y-22,x+30,y+22),radius=8,outline=rgba(BLUE,160),fill=rgba(mix(OBSIDIAN,BLUE,.15),65),width=2)
        d.text((x,y),str(i+1),font=SMALL_FONT,fill=BLUE,anchor='mm')
        draw_line_glow(im,[(cx,cy),(x,y)],BLUE,2,65,5)
    d.text((640,505),'objects appear as internally commanded ideas within awareness',font=SUB_FONT,fill=MIST,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    d.text((cx,cy),'I',font=ImageFont.truetype(FONT_SERIF_BOLD,120),fill=rgba(GOLD_LIGHT,210),anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.03
        x=cx+math.cos(a)*235; y=cy+math.sin(a)*148
        draw_object(d,x,y,.22,mix(GOLD,WHITE,i/14),'disc')
        draw_line_glow(im,[(x,y),(cx,cy)],GOLD,2,55,5)
    d.text((640,505),'objectivity is absorbed into the dominant awareness: “I am this universe”',font=SUB_FONT,fill=MIST,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    draw_glow(im,(cx,cy),150,WHITE,140,32)
    for r,col in [(28,WHITE),(80,GOLD_LIGHT),(145,SILVER),(220,WHITE)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(col,120),width=2)
    d.ellipse((cx-24,cy-24,cx+24,cy+24),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    d.text((640,505),'no independent object remains outside absolute subjectivity',font=SUB_FONT,fill=MIST,anchor='mm')


def sc11(im,t):
    d=ImageDraw.Draw(im)
    # stage/performance analogy
    d.rounded_rectangle((420,130,860,340),radius=18,outline=rgba(GOLD,170),fill=rgba(mix(OBSIDIAN,GOLD,.08),60),width=2)
    draw_object(d,640,235,.85,GOLD_LIGHT)
    for i,(name,col) in enumerate(PERCEIVERS):
        x=170+i*155; y=420
        draw_lens(d,x,y,105,54,col,75); d.text((x,y),str(i+1),font=SMALL_FONT,fill=col,anchor='mm')
        pts=partial_polyline(bezier((x,y-28),(x,360),(580+(i-3)*18,330),(640,300),70),smoothstep(.05+i*.04,.82+i*.02,t))
        if len(pts)>1: draw_line_glow(im,pts,col,2,70,5)
    d.text((640,505),'one performance delights a plural audience without becoming seven objects',font=SUB_FONT,fill=MIST,anchor='mm')


def sc12(im,t):
    d=ImageDraw.Draw(im)
    # state/perceiver matrix
    x0,y0=150,145; cw,ch=122,66
    cols=[GOLD_LIGHT,ROSE,SEA if 'SEA' in globals() else BLUE,TEAL,WHITE]
    states=['Waking','Dream','Sleep','Turīya','Beyond']
    for j,s in enumerate(states):
        d.text((x0+170+j*cw,y0-28),s,font=SMALL_FONT,fill=cols[j],anchor='mm')
    for i,(name,col) in enumerate(PERCEIVERS):
        yy=y0+i*52
        d.text((x0-20,yy+18),name,font=TINY_FONT,fill=col,anchor='rm')
        for j,s in enumerate(states):
            xx=x0+110+j*cw
            alpha=int(55+180*((i+j)%7)/6)
            d.rounded_rectangle((xx,yy,xx+90,yy+36),radius=8,outline=rgba(mix(col,cols[j],.5),120),fill=rgba(mix(OBSIDIAN,mix(col,cols[j],.5),.18),alpha//3),width=1)
            if j==3:
                d.ellipse((xx+39,yy+9,xx+51,yy+21),fill=rgba(cols[j],170))
    d.text((640,505),'the same observer-principles articulate waking, dream, sleep and the fourth',font=SUB_FONT,fill=MIST,anchor='mm')


def sc13(im,t):
    d=ImageDraw.Draw(im); cx=640
    ys=np.linspace(440,120,7)
    for i,((name,col),y) in enumerate(zip(PERCEIVERS,ys)):
        opacity=1-i/7
        lensw=260-i*26
        draw_lens(d,cx,y,lensw,44,col,int(45+opacity*60))
        d.text((cx,y),name,font=SMALL_FONT,fill=col,anchor='mm')
        if i<6:
            draw_line_glow(im,[(cx,y-22),(cx,ys[i+1]+22)],mix(col,PERCEIVERS[i+1][1],.5),3,80,5)
    draw_glow(im,(cx,90),45,WHITE,120,14)
    d.text((640,505),'as ignorance thins, the object is re-read as manifestation of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')


def sc14(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    draw_object(d,cx,cy,.9,GOLD_LIGHT)
    for i,(name,col) in enumerate(PERCEIVERS):
        a=-math.pi/2+i*2*math.pi/7+t*.03
        r=195
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.74
        draw_lens(d,x,y,88,50,col,72)
        d.text((x,y),str(i+1),font=SMALL_FONT,fill=col,anchor='mm')
        draw_line_glow(im,[(x,y),(cx+math.cos(a)*65,cy+math.sin(a)*45)],col,2,65,5)
    for r,col in [(110,SILVER),(155,INDIGO),(230,GOLD)]:
        d.ellipse((cx-r,cy-r*.74,cx+r,cy+r*.74),outline=rgba(col,70),width=1)
    d.text((640,505),'common perceptibility and sevenfold manifestation in one closing matrix',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('pm01','One Object, Seven Perceivers','The full perceptibility matrix.','Pramātṛ–Vedya','One manifest entity is common to seven observer-architectures.','overview',['overview','seven perceivers','object'],'overview','central lotus with seven lenses','TA 10.3–18; 19–78ab','derived','high','A central lotus and seven gallery lenses synthesize the chapter structure.',sc01),
Scene('pm02','Perceptibility as Vastudharma','The object shines as intrinsically perceptible.','Vastudharma','Perceptibility belongs to the manifest nature of the entity.','intrinsic_perceptibility',['vastudharma','perceptibility'],'theory','lotus with intrinsic halos','TA 10.19–78ab','direct','high','Concentric halos visualize perceptibility as an intrinsic manifest quality.',sc02),
Scene('pm03','Common but Not Identical','Several perceivers encounter one entity differently.','Sādhāraṇa-vedyatā','Common perceptibility does not imply identical appearance.','common_object',['plural perception','common object'],'theory','one object branching to seven lenses','TA 10.19–78ab','direct','high','The branching gallery layout is a schematic inference.',sc03),
Scene('pm04','Sakala','The object appears fragmented and externally independent.','Sakala','Three impurities fracture the field into separate objects.','sakala_view',['sakala','fragmentation'],'observer','fragmented lotus behind three membranes','TA 10 perceiver taxonomy; ch. 1/9 background','derived','high','The three visible membranes symbolize the three malas.',sc04),
Scene('pm05','Pralayākala','The object-field withdraws into uniform darkness.','Pralayākala','No differentiated object is perceived in dissolution-like darkness.','pralayakala_view',['pralayakala','objectless darkness'],'observer','uniform dark field','TA 10.152ff state analysis','derived','medium','Concentric darkness is a phenomenological visualization.',sc05),
Scene('pm06','Vijñānākala','Pure but isolated subjectivity remains.','Vijñānākala','The subject persists without an objective world.','vijnanakala_view',['vijnanakala','isolated subject'],'observer','isolated eye and broken outer ring','TA 10 perceiver taxonomy','derived','high','The broken object-ring visualizes absent objective projection.',sc06),
Scene('pm07','Mantra','The universe is self-expression with a faint I/This distinction.','Mantra-pramātṛ','Objectivity is recognized as one’s own extension, though polarity remains.','mantra_view',['mantra','I and This'],'observer','paired eye and lotus','TA 10 seven perceivers','derived','high','Paired symbols clarify faint residual distinction.',sc07),
Scene('pm08','Mantreśvara','The object is an internally commanded idea.','Mantreśvara','Cosmic ideas appear within sovereign awareness.','mantresvara_view',['mantresvara','cosmic ideas'],'observer','central eye controlling idea-cells','TA 10 seven perceivers','derived','high','Idea-cells are a modern visual inference.',sc08),
Scene('pm09','Mantramaheśvara','The object is absorbed into dominant I-consciousness.','Mantramaheśvara','Awareness takes the universe as its own I-ness.','mantramahesvara_view',['mantramahesvara','I am universe'],'observer','large I with absorbed worlds','TA 10 seven perceivers','derived','high','The typographic I is a synthetic emblem.',sc09),
Scene('pm10','Śiva','Absolute subjectivity without independent objectification.','Śiva','No boundary remains between perceiver and perceived.','shiva_view',['shiva','absolute subject'],'observer','white-gold field','TA 10 culmination of perceiver ascent','derived','high','The field avoids personifying Śiva as a figure.',sc10),
Scene('pm11','One Performance, Many Viewers','A common display is enjoyed by a plural audience.','Nṛtya-dṛṣṭānta','One manifestation can be common to many without multiplying into separate objects.','audience_analogy',['performance','audience','common object'],'analogy','stage and seven viewers','TA 10 discussion of common perceptibility; performance analogy in chapter overview tradition','derived','medium','Stage composition literalizes the analogy.',sc11),
Scene('pm12','States Across the Perceivers','Observer-levels articulate waking, dream, sleep, Turīya and beyond.','Avasthā-pramātṛ','The seven perceiver structures interweave with states of consciousness.','state_matrix',['states','perceivers','matrix'],'synthesis','seven-by-five matrix','TA 10 later state analysis','derived','medium','The matrix is schematic and does not claim an exact traditional table.',sc12),
Scene('pm13','Ascent and the Elimination of Ignorance','Filtration thins across the seven perceiver levels.','Avidyā-kṣaya','The object is progressively recognized as manifestation of consciousness.','ascent',['ascent','ignorance','recognition'],'process','transparent ascending lenses','TA 10.12cd–18','direct','high','Lens transparency visualizes decreasing filtering.',sc13),
Scene('pm14','The Perceptibility Seal','Common object and differentiated manifestation resolve together.','Vedyatā-cakra','One entity and seven observer-fields form a single closing matrix.','seal',['seal','perceptibility','seven lenses'],'seal','lotus within sevenfold lens wheel','TA 10 synthesis','synthetic','high','The closing cosmogram is explicitly synthetic.',sc14),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1)
            im=ground(SEED+hash(scene.id)%10000+i); border(im); dust(im,SEED+i,54)
            scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    cols,rows=4,4
    sheet=Image.new('RGB',(cols*320,rows*180),color=OBSIDIAN)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%cols)*320,(idx//cols)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={'project':'Tantrāloka — One Object, Seven Perceivers: The Perceptibility Matrix','source_basis':'Chapter 10 account of the seven perceivers, common perceptibility, observer-relative manifestation, and the states of consciousness.','style':{'family':'observer-field gallery / perceptual glass','background':'obsidian contemplative field','accent':'seven perceiver colors around a gold object','materials':['gallery lenses','silver perceptibility halos','fragmented lotus','idea-cells','state matrix','perceptibility seal']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),'scenes':[]}
    for sc in SCENES:
        manifest['scenes'].append({'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4','textual_anchor':sc.textual_anchor,'source_status':sc.source_status,'philological_confidence':sc.philological_confidence,'creative_visual_inference':sc.creative_visual_inference})
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview_and_theory':['pm01','pm02','pm03'],'seven_observers':['pm04','pm05','pm06','pm07','pm08','pm09','pm10'],'analogies_and_states':['pm11','pm12'],'ascent_and_seal':['pm13','pm14']},'reusability_notes':{s.id:s.summary for s in SCENES}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))

    dossier='''# AGENT KNOWLEDGE DOSSIER — One Object, Seven Perceivers\n\n## Aim\nVisualize Chapter 10’s account of common perceptibility and differentiated manifestation across the seven perceiver-architectures.\n\n## Central thesis\nThe chapter does not simply classify seven subjects. It asks how one entity can be perceptible to several perceivers and still appear differently through each perceiver’s innate condition. Perceptibility is treated as belonging to the manifest nature of the entity, while manifestation varies through observer-structure.\n\n## Seven perceivers\nSakala, Pralayākala, Vijñānākala, Mantra, Mantreśvara, Mantramaheśvara, Śiva.\n\n## Visual rules\n- Keep one common lotus-object through many scenes.\n- Change the observer-field, not the underlying entity alone.\n- Do not imply seven private hallucinations with no common manifestation.\n- Do not imply that every perceiver sees an identical object.\n- Show perceptibility and observer-conditioned disclosure together.\n\n## Source-critical policy\nThe exact conceptual architecture is direct or derived from Chapter 10. Gallery lenses, lotus-object, state matrix, and final seal are synthetic visual devices and are labeled accordingly.\n'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')

    source='''# SOURCE NOTES\n\n## Main anchors\n- Tantrāloka Chapter 10 overview: seven perceivers as possessors of power; ascent through the seven perceivers; perceptibility common to several perceivers as an intrinsic quality of an entity’s manifested nature.\n- Tantrāloka 10a translation: perceptibility is distinguished from ordinary qualities such as blue and treated as an essential quality comparable to existence.\n- Tantrāloka 10b translation: later analysis of waking, dreaming, deep sleep, and continuity of the perceiver.\n\n## Cautions\n- The seven-by-five state matrix is schematic.\n- The exact stage/gallery imagery is not traditional iconography.\n- The closing seven-lens wheel is a synthetic explanatory seal.\n'''
    (ROOT/'SOURCE_NOTES.md').write_text(source,encoding='utf-8')

    style='''# STYLE EVOLUTION — Perceptibility Matrix Pack\n\n## New visual thesis\nOne common object is refracted through seven observer-fields. The pack uses gallery lenses, perceptual glass, and observer-specific fields rather than another vertical hierarchy.\n\n## New motifs\n1. common lotus-object\n2. seven gallery lenses\n3. intrinsic perceptibility halos\n4. fragmented Sakala lotus\n5. objectless Pralayākala field\n6. isolated Vijñānākala eye\n7. paired I/This field\n8. sovereign idea-cells\n9. universe absorbed into I\n10. stage-and-audience analogy\n11. states/perceivers matrix\n12. transparent ascent lenses\n13. sevenfold perceptibility seal\n\n## Distinct material vocabulary\n- obsidian gallery field\n- silver perceptibility glass\n- seven colored observer lenses\n- gold common-object light\n- transparent ascent membranes\n\n## Closing seal\nA single lotus surrounded by seven lenses, preserving both common perceptibility and differentiated manifestation.\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')

    readme=f'''# One Object, Seven Perceivers — The Perceptibility Matrix\n\n- Resolution: {W}x{H}\n- FPS: {FPS}\n- Scenes: {len(SCENES)}\n- Duration per scene: {DURATION}s\n- Total runtime: {len(SCENES)*DURATION:.1f}s\n\nRun:\n```bash\npython render_pack.py\n```\nThe renderer is resume-safe.\n'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')


def validate_outputs():
    combined=ROOT/'perceptibility_matrix_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))


def make_zip():
    zpath=ROOT/'perceptibility_matrix_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['perceptibility_matrix_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','SOURCE_NOTES.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'perceptibility_matrix_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__': render_all()
