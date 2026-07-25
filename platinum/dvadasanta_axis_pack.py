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
SEED = 121212

# Vertical somatic/transcendental palette
PAPER = (247, 245, 239)
PAPER_LIGHT = (252, 250, 245)
INK = (38, 42, 49)
UMBER = (91, 76, 61)
SLATE = (104, 116, 133)
MIST = (177, 187, 199)
SILVER = (215, 222, 231)
PALE_BLUE = (223, 232, 241)
BLUE = (105, 143, 183)
DEEP_BLUE = (67, 102, 145)
TEAL = (89, 148, 149)
GREEN = (105, 151, 112)
GOLD = (205, 164, 88)
GOLD_LIGHT = (244, 214, 141)
CORAL = (201, 102, 91)
ROSE = (190, 126, 143)
VIOLET = (128, 111, 168)
INDIGO = (77, 83, 139)
WHITE = (252, 251, 248)
BLACK = (20, 22, 26)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)

STATIONS = [
    ('Hṛdaya', CORAL), ('Kaṇṭha', TEAL), ('Tālu', GOLD), ('Bhrūmadhya', INDIGO),
    ('Lalāṭa', VIOLET), ('Brahmarandhra', GOLD_LIGHT), ('Śikha', CORAL),
    ('Paścima', BLUE), ('Śakti', ROSE), ('Vyāpinī', TEAL), ('Samanā', SILVER),
    ('Unmanā / Dvādaśānta', WHITE)
]


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t): t=clamp(t); return 0.5 - 0.5*math.cos(math.pi*t)
def ease_out_cubic(t): t=clamp(t); return 1-(1-t)**3
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def ground(seed:int):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PAPER,dtype=np.float32)
    coarse=rng.normal(0,1,(38,68)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.1 + fine[...,None]*0.9
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*4.2,0,11)[...,None]*0.55
    # vertical central breath column
    col=np.exp(-(((xx-W/2)/(W*0.11))**2 + ((yy-H*0.44)/(H*0.54))**2)*1.7)
    for i in range(3): base[...,i] += col*(10 if i<2 else 22)
    # upper transcendental glow
    top=np.exp(-(((xx-W/2)/(W*0.25))**2 + ((yy-H*0.13)/(H*0.15))**2)*2.4)
    for i in range(3): base[...,i] += top*(10 if i<2 else 21)
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


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

def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,140),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,85),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,PALE_BLUE,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(248,247,243,220),outline=rgba(SLATE,65),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=SLATE)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=DEEP_BLUE)

def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def partial_polyline(points,amount):
    amount=clamp(amount)
    if amount<=0:return []
    if amount>=1:return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx; out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    draw.polygon([p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)],fill=rgba(color,230))

def dust(im,seed,n=44):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(105,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,65))))
    im.alpha_composite(ov)

def draw_human_axis(draw,cx=640,top=105,bottom=490,alpha=150):
    # simplified body silhouette and vertical axis
    draw.ellipse((cx-22,top+46,cx+22,top+90),outline=rgba(SLATE,alpha),width=2)
    draw.arc((cx-110,top+96,cx+110,bottom),200,340,fill=rgba(SLATE,alpha-20),width=2)
    draw.line((cx,top+90,cx,bottom-42),fill=rgba(SLATE,alpha),width=2)
    draw.arc((cx-88,bottom-115,cx+88,bottom-30),20,160,fill=rgba(SLATE,alpha-25),width=2)

def node(draw,x,y,r,col,label=None,num=None):
    draw.ellipse((x-r,y-r,x+r,y+r),outline=rgba(col,220),fill=rgba(mix(PAPER_LIGHT,col,.05),75),width=2)
    if num is not None: draw.text((x,y),str(num),font=SMALL_FONT,fill=INK,anchor='mm')
    if label: draw.text((x+52,y),label,font=SMALL_FONT,fill=col,anchor='lm')

def petals(draw,cx,cy,r,col,n=6):
    for i in range(n):
        a=2*math.pi*i/n
        x=cx+math.cos(a)*r*.6; y=cy+math.sin(a)*r*.6
        draw.ellipse((x-r*.36,y-r*.20,x+r*.36,y+r*.20),outline=rgba(col,180),fill=rgba(mix(PAPER_LIGHT,col,.05),45),width=1)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]


def sc01(im,t):
    d=ImageDraw.Draw(im); cx=640
    draw_human_axis(d,cx,92,485,135)
    ys=[440,392,348,302,260,220,184,154,128,106,86,64]
    # compress transcendental top visually
    for i,((lab,col),y) in enumerate(zip(STATIONS,ys),1):
        s=clamp(t*1.18-(i-1)*.045)
        if s<=0: continue
        r=13 if i<7 else 10
        node(d,cx,y,r,col,None,i)
        if i<12:
            y2=ys[i]
            pts=partial_polyline([(cx,y-r),(cx,y2+r)],s)
            if len(pts)>1: draw_line_glow(im,pts,mix(col,STATIONS[i][1],.5),2,80,5)
    d.text((805,430),'somatic segment',font=TERM_FONT,fill=CORAL)
    d.text((805,265),'cephalic segment',font=TERM_FONT,fill=INDIGO)
    d.text((805,135),'transcendental vector',font=TERM_FONT,fill=TEAL)
    d.text((640,515),'twelve coordinate stations carry prāṇa from the heart into empty space',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,320
    draw_human_axis(d,cx,112,500,120)
    draw_glow(im,(cx,cy),48,CORAL,110,14); petals(d,cx,cy,70,CORAL,8)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(CORAL,220),width=2)
    for i in range(7):
        a=-math.pi/2+i*math.pi/6
        pts=partial_polyline(bezier((cx,cy),(cx+math.cos(a)*40,cy-40),(cx+math.cos(a)*70,cy-90),(cx+math.cos(a)*85,cy-145),80),smoothstep(.04,.85,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(CORAL,GOLD_LIGHT,i/7),2,80,5)
    d.text((640,515),'the upward pulse begins at the primary subjective heart-node',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,285
    # tuning fork throat
    d.line((cx-58,cy-72,cx-58,cy+32),fill=rgba(TEAL,210),width=5)
    d.line((cx+58,cy-72,cx+58,cy+32),fill=rgba(TEAL,210),width=5)
    d.arc((cx-58,cy-6,cx+58,cy+92),0,180,fill=rgba(TEAL,210),width=5)
    for i in range(6):
        r=36+i*24
        d.arc((cx-r,cy-r*.42,cx+r,cy+r*.42),190,350,fill=rgba(mix(TEAL,MIST,i/6),130),width=2)
    d.text((640,425),'speech and intent begin to take formal shape',font=TERM_FONT,fill=TEAL,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    # palate gate
    d.rounded_rectangle((450,190,830,370),radius=52,outline=rgba(GOLD,190),fill=rgba(mix(PAPER_LIGHT,GOLD,.035),65),width=3)
    d.arc((520,215,760,350),180,360,fill=rgba(GOLD,210),width=4)
    d.line((640,220,640,356),fill=rgba(GOLD_LIGHT,170),width=2)
    opening=18+90*ease_in_out(t)
    d.rounded_rectangle((640-opening,232,640+opening,352),radius=28,outline=rgba(GOLD_LIGHT,200),fill=rgba((255,245,210),55),width=2)
    draw_glow(im,(640,292),44,GOLD_LIGHT,110,14)
    d.text((640,445),'the physical gateway where bodily stability begins to loosen',font=TERM_FONT,fill=GOLD,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,270
    # dual sensory streams into one lens
    p1=partial_polyline(bezier((270,220),(420,200),(520,245),(cx,cy),90),smoothstep(.04,.84,t))
    p2=partial_polyline(bezier((1010,320),(860,340),(760,295),(cx,cy),90),smoothstep(.04,.84,t))
    if len(p1)>1: draw_line_glow(im,p1,INDIGO,3,110,6)
    if len(p2)>1: draw_line_glow(im,p2,ROSE,3,110,6)
    draw_glow(im,(cx,cy),52,INDIGO,100,15)
    d.ellipse((cx-34,cy-34,cx+34,cy+34),outline=rgba(INDIGO,220),width=3)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=rgba(WHITE,255),outline=rgba(GOLD,190),width=2)
    d.text((640,445),'dual sensory inputs bind into a single stream of awareness',font=TERM_FONT,fill=INDIGO,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,278
    # forehead basin settling ripples
    d.arc((420,220,860,430),0,180,fill=rgba(VIOLET,180),width=3)
    for i in range(7):
        rx=170-i*20; ry=56-i*6
        alpha=int(150*(1-i/8)*(1-.35*ease_in_out(t)))
        d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=rgba(mix(VIOLET,MIST,i/7),alpha),width=2)
    draw_glow(im,(cx,cy),38,VIOLET,90,12)
    d.text((640,450),'mental modifications settle into a still forehead-field',font=TERM_FONT,fill=VIOLET,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,300
    # cranial aperture / crown exit
    d.arc((500,185,780,410),180,360,fill=rgba(SLATE,170),width=3)
    d.line((520,298,520,390),fill=rgba(SLATE,130),width=2); d.line((760,298,760,390),fill=rgba(SLATE,130),width=2)
    opening=20+74*ease_in_out(t)
    d.arc((cx-opening,170,cx+opening,250),180,360,fill=rgba(GOLD_LIGHT,220),width=4)
    pts=partial_polyline(bezier((cx,305),(cx,250),(cx,190),(cx,120),90),smoothstep(.04,.9,t))
    if len(pts)>1: draw_line_glow(im,pts,GOLD_LIGHT,4,120,8)
    draw_arrowhead(d,pts[-2],pts[-1],GOLD_LIGHT,1.0) if len(pts)>1 else None
    d.text((640,455),'vital energy crosses the physical crown aperture',font=TERM_FONT,fill=GOLD,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,260
    # localized flame just above scalp
    d.arc((510,255,770,430),180,360,fill=rgba(SLATE,135),width=2)
    draw_glow(im,(cx,180),44,CORAL,105,14)
    flame=[(cx,115),(cx-28,174),(cx-10,220),(cx+4,190),(cx+20,235),(cx+38,166)]
    d.polygon(flame,outline=rgba(CORAL,220),fill=rgba((255,185,160),55))
    d.line((cx,230,cx,280),fill=rgba(CORAL,180),width=3)
    d.text((640,455),'a localized station appears just above the scalp line',font=TERM_FONT,fill=CORAL,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,265
    # rear apex stabilization: arc behind crown
    d.arc((500,215,780,420),180,360,fill=rgba(SLATE,125),width=2)
    rearx=760
    draw_glow(im,(rearx,180),38,BLUE,100,13)
    d.ellipse((rearx-18,162,rearx+18,198),fill=rgba(WHITE,255),outline=rgba(BLUE,220),width=2)
    pts=partial_polyline(bezier((640,210),(690,190),(725,182),(rearx,180),80),smoothstep(.04,.88,t))
    if len(pts)>1: draw_line_glow(im,pts,BLUE,3,110,6)
    for r in [46,80,116]: d.arc((rearx-r,180-r*.55,rearx+r,180+r*.55),180,360,fill=rgba(BLUE,95),width=2)
    d.text((640,455),'energy stabilizes at a spatial apex behind the upper crown',font=TERM_FONT,fill=BLUE,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,270
    # cosmic frequency node, individual wave syncing with large field
    small=[]; large=[]
    for i in range(120):
        u=i/119; x=lerp(250,1030,u)
        small.append((x,cy+math.sin(u*2*math.pi*4+t*.12)*24))
        large.append((x,cy+math.sin(u*2*math.pi*2+t*.08)*78))
    draw_line_glow(im,large,ROSE,3,90,7)
    draw_line_glow(im,small,GOLD_LIGHT,3,110,6)
    draw_glow(im,(cx,cy),42,ROSE,100,13)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(ROSE,220),width=2)
    d.text((640,455),'the individual pulse begins vibrating at a cosmic frequency',font=TERM_FONT,fill=ROSE,anchor='mm')


def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    # spatial expansion field
    for i in range(8):
        r=26+i*34*ease_out_cubic(t)
        d.ellipse((cx-r,cy-r*.66,cx+r,cy+r*.66),outline=rgba(mix(TEAL,SILVER,i/8),140),width=2)
    draw_glow(im,(cx,cy),52,TEAL,110,16)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,255),outline=rgba(TEAL,220),width=2)
    d.text((640,455),'localized identity dissolves into infinite spatial expansion',font=TERM_FONT,fill=TEAL,anchor='mm')


def sc12(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,275
    # weightless thought feathers
    rng=np.random.default_rng(50)
    for i in range(18):
        x=float(rng.uniform(320,960)); y=float(rng.uniform(150,390))
        lift=40*ease_in_out(t)*(0.5+0.5*math.sin(i))
        yy=y-lift
        d.arc((x-12,yy-5,x+12,yy+7),180,360,fill=rgba(SILVER,170),width=2)
        d.line((x,yy+2,x+math.sin(i)*10,yy+18),fill=rgba(SILVER,135),width=1)
    draw_glow(im,(cx,cy),34,SILVER,85,12)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),outline=rgba(GOLD_LIGHT,190),fill=rgba(WHITE,245),width=2)
    d.text((640,455),'thoughts become weightless while a final seed of identity remains',font=TERM_FONT,fill=SLATE,anchor='mm')


def sc13(im,t):
    d=ImageDraw.Draw(im); cx=640
    # external 12th above head, ruler/fingerbreadths
    d.arc((520,330,760,500),180,360,fill=rgba(SLATE,115),width=2)
    y0=340; y1=110
    d.line((cx,y0,cx,y1),fill=rgba(SLATE,120),width=2)
    for i in range(12):
        y=lerp(y0,y1,(i+1)/12)
        d.line((cx-16,y,cx+16,y),fill=rgba(SLATE,110),width=1)
    draw_glow(im,(cx,y1),62,WHITE,130,20)
    d.ellipse((cx-24,y1-24,cx+24,y1+24),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    d.text((cx+90, y1), '12 finger-breadths', font=SMALL_FONT, fill=SLATE, anchor='lm')
    d.text((640,455),'the final external station rests above the head in empty space',font=TERM_FONT,fill=GOLD,anchor='mm')


def sc14(im,t):
    d=ImageDraw.Draw(im); cx=640
    # full vertical seal with three segments
    d.line((cx,450,cx,85),fill=rgba(SLATE,120),width=2)
    ys=[432,398,364,330,296,262,226,196,168,142,116,88]
    for i,((lab,col),y) in enumerate(zip(STATIONS,ys),1):
        draw_glow(im,(cx,y),12,col,80,5)
        d.ellipse((cx-7,y-7,cx+7,y+7),fill=rgba(WHITE,255),outline=rgba(col,210),width=2)
        if i in [1,6,12]:
            d.text((cx+56,y),lab,font=SMALL_FONT,fill=col,anchor='lm')
    # three enclosing segment arcs
    d.rounded_rectangle((525,345,755,468),radius=54,outline=rgba(CORAL,120),width=2)
    d.rounded_rectangle((545,210,735,340),radius=52,outline=rgba(INDIGO,120),width=2)
    d.rounded_rectangle((565,70,715,205),radius=50,outline=rgba(TEAL,120),width=2)
    draw_glow(im,(cx,88),42,GOLD_LIGHT,120,14)
    d.text((640,515),'the twelve-station axis resolves into a single ascent from body to boundless space',font=SUB_FONT,fill=SLATE,anchor='mm')


SCENES=[
    Scene('dv01','The Dvādaśānta Axis','An overview of twelve stations from heart to external space.','Dvādaśānta','The full ascent is mapped as a vertical migration through bodily, cranial, and transcendent coordinates.','overview_axis',['overview','12 stages','axis'],'overview','vertical body-space axis',sc01),
    Scene('dv02','Hṛdaya','The heart center where the upward pulse begins.','Hṛdaya','The subjective origin of udāna and the first somatic station.','heart_origin',['heart','origin','udana'],'somatic','heart lotus and rising rays',sc02),
    Scene('dv03','Kaṇṭha','The throat junction where speech and intent configure.','Kaṇṭha','The first processing node of articulated potency.','throat_node',['throat','speech','intent'],'somatic','tuning fork throat',sc03),
    Scene('dv04','Tālu','The palate threshold where bodily stability starts to loosen.','Tālu','A physical gateway opens toward subtler ascent.','palate_gate',['palate','threshold','gateway'],'somatic','palate aperture',sc04),
    Scene('dv05','Bhrūmadhya','The eyebrow center binds dual sensory input into one stream.','Bhrūmadhya','Dispersed perception is focused into a single current.','eyebrow_focus',['eyebrow','focus','sensory binding'],'cephalic','dual streams into lens',sc05),
    Scene('dv06','Lalāṭa','The forehead field where mental modifications settle.','Lalāṭa','Vṛttis quiet into a still frontal basin.','forehead_stillness',['forehead','stillness','vrittis'],'cephalic','settling ripple basin',sc06),
    Scene('dv07','Brahmarandhra','The crown aperture where energy leaves bodily containment.','Brahmarandhra','The vertical current crosses the physical cranial boundary.','cranial_exit',['crown','exit','aperture'],'cephalic','crown opening and exit beam',sc07),
    Scene('dv08','Śikha','A localized coordinate just above the scalp.','Śikha','The first post-bodily station remains concentrated and near the body.','topknot_node',['topknot','above head','localized'],'transcendent','localized flame node',sc08),
    Scene('dv09','Paścima','The rear apex stabilizes the ascending current.','Paścima','Energy rests at a spatial point behind the upper crown.','rear_apex',['rear apex','stabilization'],'transcendent','rear halo arc',sc09),
    Scene('dv10','Śakti','The individual life-force begins vibrating cosmically.','Śakti','The localized pulse synchronizes with a larger frequency-field.','cosmic_frequency',['shakti','frequency','cosmic'],'transcendent','dual-frequency waves',sc10),
    Scene('dv11','Vyāpinī','Energy expands beyond localization.','Vyāpinī','The current becomes spatially pervasive and loses bounded identity.','infinite_expansion',['expansion','pervasion','nonlocal'],'transcendent','expanding ellipses',sc11),
    Scene('dv12','Samanā','Thought becomes weightless, though a seed remains.','Samanā','The field is almost free of identity but not yet fully dissolved.','weightless_thought',['thought','weightless','subtle seed'],'transcendent','floating thought feathers',sc12),
    Scene('dv13','Unmanā / Dvādaśānta','The external twelfth station in empty space.','Unmanā','Vital energy dissolves at the point twelve finger-breadths above the head.','external_twelfth',['unmana','external point','dissolution'],'transcendent','measured external halo',sc13),
    Scene('dv14','The Dvādaśānta Seal','The complete ascent resolved into one vertical cosmogram.','Dvādaśānta-cakra','The body-to-space axis closes as a single contemplative seal.','closing_seal',['seal','summary','vertical axis'],'seal','three-segment ascent seal',sc14),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1); im=ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,42); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    cols,rows=4,4; sheet=Image.new('RGB',(cols*320,rows*180),color=PAPER)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%cols)*320,(idx//cols)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
        'project':'Tantrāloka — The 12-Stage Movement of the Breath (Dvādaśānta Axis)',
        'source_basis':'Conceptual mapping supplied by the user from Tantrāloka Chapter 6: twelve stations from Hṛdaya to Unmanā / Dvādaśānta.',
        'style':{'family':'vertical somatic-transcendental architecture','background':'clean ivory field with central blue column','ink':'slate and deep blue','accent':'coral, teal, gold, indigo, violet, silver','materials':['body-axis','tuning fork','palate gate','sensory lens','crown aperture','frequency field','expansion rings','external halo']},
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[{'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'} for sc in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id:sc.title for sc in SCENES},
        'modes':{sc.id:sc.mode for sc in SCENES},
        'theme_clusters':{'overview':['dv01'],'somatic':['dv02','dv03','dv04'],'cephalic':['dv05','dv06','dv07'],'transcendental':['dv08','dv09','dv10','dv11','dv12','dv13'],'seal':['dv14']},
        'reusability_notes':{
            'dv01':'Use to introduce the whole twelve-station axis.','dv02':'Use for the heart, udāna, or subjective origin.','dv03':'Use for throat, speech formation, or vibratory processing.','dv04':'Use for palate threshold or first bodily destabilization.','dv05':'Use for eyebrow focus, sensory unification, or one-pointed awareness.','dv06':'Use for forehead stillness or quieting of vṛttis.','dv07':'Use for crown exit, cranial aperture, or bodily transcendence.','dv08':'Use for the first post-bodily station or topknot imagery.','dv09':'Use for stabilization behind the crown.','dv10':'Use for individual-to-cosmic frequency synchronization.','dv11':'Use for pervasion, spatial expansion, or loss of localization.','dv12':'Use for weightless cognition and the final subtle seed.','dv13':'Use for the external dvādaśānta point above the head.','dv14':'Use as the closing seal for body-to-space ascent.'}
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))

    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Dvādaśānta Axis

## Aim
This pack visualizes the **12-stage movement of breath-energy** from the heart through bodily and cranial stations into an external point above the head.

## Textual orientation
The pack follows the user-supplied Chapter 6 map. It is a structural and contemplative visualization, not a practical breath-retention manual.

## The twelve stations represented
1. Hṛdaya — heart origin
2. Kaṇṭha — throat node
3. Tālu — palate threshold
4. Bhrūmadhya — eyebrow center
5. Lalāṭa — forehead station
6. Brahmarandhra — cranial aperture
7. Śikha — topknot coordinate
8. Paścima — rear apex
9. Śakti — cosmic-frequency node
10. Vyāpinī — infinite spatial expansion
11. Samanā — weightless thought with subtle seed
12. Unmanā / Dvādaśānta — external twelfth point above the head

## Visual rules
- Preserve the three-part architecture: somatic, cephalic, transcendental.
- Each node must have a distinct visual metaphor rather than repeating a generic chakra circle.
- The ascent should gradually lose anatomical density and gain spatial openness.
- Dvādaśānta should be visibly outside the body in empty space.
- Samanā and Unmanā must be distinguished: the former retains a subtle seed; the latter dissolves it.

## Style family
- clean ivory ground
- central pale-blue vertical column
- coral heart and topknot accents
- teal and indigo cognitive / spatial nodes
- gold palate and crown apertures
- silver weightlessness near the upper stations

## New motifs introduced
- heart lotus with upward rays
- throat tuning fork
- palate aperture
- eyebrow convergence lens
- forehead settling basin
- crown exit portal
- topknot flame
- rear apex halo
- frequency synchronization waves
- spatial expansion rings
- floating thought feathers
- measured external halo
- three-segment vertical seal

## Guardrails
- Avoid generic rainbow chakra iconography.
- Do not turn the pack into physiological anatomy only.
- The upper stations are spatial / ontological coordinates, not merely body parts.
- Keep the final point visibly external to bodily containment.

## Reuse strategy
- dv01: full overview
- dv02–dv04: somatic segment
- dv05–dv07: cephalic segment
- dv08–dv13: transcendental vector
- dv14: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')

    style='''# STYLE EVOLUTION — Dvādaśānta Axis Pack

## Inheritance
This pack inherits the clean breath-oriented clarity of Prāṇavicāra but turns the horizontal respiratory swing into a vertical body-to-space migration.

## Dvādaśānta differentiation
This pack emphasizes:
- somatic architecture
- cranial thresholds
- progressive de-localization
- vertical ascent into external space
- coordinate stations rather than respiratory phases

## New motifs added
1. heart lotus and udāna rays
2. throat tuning fork
3. palate gate
4. eyebrow convergence lens
5. forehead stillness basin
6. crown aperture
7. topknot flame
8. rear apex halo
9. cosmic frequency synchronization
10. infinite expansion rings
11. weightless thought feathers
12. measured external halo
13. three-segment closing seal

## New relationships added
- heart → speech junction
- speech → palate threshold
- dual sensory input → one stream
- mental movement → stillness
- bodily containment → crown exit
- localized vitality → cosmic frequency
- cosmic frequency → infinite pervasion
- subtle identity seed → complete dissolution

## New material vocabulary
- ivory somatic field
- pale-blue vertical column
- gold apertures
- indigo focus lens
- silver weightlessness
- white external halo

## Deprecated clichés
- standard chakra rainbow stack
- anatomical diagram repetition
- identical glowing nodes at every station

## Distinct closing seal
The closing seal is a **three-segment vertical ascent cosmogram** linking somatic, cephalic, and transcendental stations.

## Recommendation for next pack
- The Four Āmnāyas
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')

    readme=f'''# Tantrāloka — The 12-Stage Movement of the Breath (Dvādaśānta Axis) Pack

Included files:
- dvadasanta_axis_animation.mp4
- contact_sheet.jpg
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- STYLE_EVOLUTION.md
- render_pack.py
- README.md
- validation.json
- scenes/*.mp4

Specs:
- Resolution: {W}x{H}
- FPS: {FPS}
- Scene count: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total runtime: {len(SCENES)*DURATION/60:.2f} min

Render instructions:
```bash
python render_pack.py
```
The script is resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')


def validate_outputs():
    combined=ROOT/'dvadasanta_axis_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'dvadasanta_axis_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['dvadasanta_axis_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat_file=ROOT/'concat_list.txt'; concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'dvadasanta_axis_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__': render_all()
