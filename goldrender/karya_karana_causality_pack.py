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
SEED = 90909

# Causal-field palette
NIGHT = (14, 18, 29)
OBSIDIAN = (24, 29, 43)
DEEP_BLUE = (38, 51, 88)
INDIGO = (72, 84, 143)
VIOLET = (128, 104, 168)
TEAL = (80, 139, 144)
SEA = (88, 126, 151)
COPPER = (184, 104, 62)
EMBER = (224, 112, 52)
GOLD = (205, 162, 79)
GOLD_LIGHT = (242, 211, 132)
ROSE = (185, 96, 127)
CRIMSON = (150, 44, 61)
GREEN = (91, 139, 104)
ASH = (162, 171, 188)
MIST = (205, 211, 222)
IVORY = (241, 238, 227)
WHITE = (252, 249, 240)
SLATE = (94, 106, 128)
BLACK = (7, 9, 14)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 27)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b-a) * clamp(t)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi*t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1-t)**3


def smoothstep(a,b,x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t*t*(3-2*t)


def rgba(c,a=255):
    return (*c[:3], int(a))


def causal_ground(seed: int):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0,1,(45,80)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.0
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*18,0,27)
    base -= vign[...,None]
    # central causal aurora
    band = np.exp(-((yy-H*0.40)/(H*0.20))**2) * np.exp(-((xx-W/2)/(W*0.44))**2)
    base[...,0] += band*8; base[...,1] += band*11; base[...,2] += band*24
    lower = np.exp(-(((xx-W*0.68)/(W*0.23))**2 + ((yy-H*0.62)/(H*0.18))**2)*2.8)
    base[...,0] += lower*12; base[...,1] += lower*5; base[...,2] += lower*2
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA',(W,H),(0,0,0,0))


def draw_glow(im,xy,radius,color,alpha=150,blur=18):
    gl=layer(); d=ImageDraw.Draw(gl)
    x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius), fill=rgba(color,alpha))
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im,pts,color,width=3,alpha=150,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+75)),width=width,joint='curve')


def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8
        x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(ASH,115),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,95),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,INDIGO,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(15,19,31,208),outline=rgba(ASH,70),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=IVORY)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=ASH)
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


def dust(im,seed,n=82):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(115,W-115)); y=float(rng.uniform(100,H-180)); r=float(rng.uniform(.8,2.1))
        c=mix(ASH,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,75))))
    im.alpha_composite(ov)


def draw_eye(draw,cx,cy,scale=1.0,col=GOLD_LIGHT):
    draw.arc((cx-72*scale,cy-34*scale,cx+72*scale,cy+34*scale),180,360,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.arc((cx-72*scale,cy-34*scale,cx+72*scale,cy+34*scale),0,180,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.ellipse((cx-15*scale,cy-15*scale,cx+15*scale,cy+15*scale),fill=rgba(col,210))


def draw_pot(draw,cx,cy,scale=1.0,col=COPPER,alpha=190):
    w=58*scale; h=72*scale
    draw.arc((cx-w,cy-h,cx+w,cy+h),20,160,fill=rgba(col,alpha),width=max(1,int(3*scale)))
    draw.arc((cx-w,cy-h,cx+w,cy+h),200,340,fill=rgba(col,alpha),width=max(1,int(3*scale)))
    draw.line((cx-w*.58,cy-h*.62,cx+w*.58,cy-h*.62),fill=rgba(col,alpha),width=max(1,int(3*scale)))
    draw.ellipse((cx-w*.58,cy-h*.74,cx+w*.58,cy-h*.48),outline=rgba(col,alpha),width=max(1,int(2*scale)))


def draw_node(draw,x,y,r,col,label=None,fill_alpha=48,font=None,text_col=None):
    draw.ellipse((x-r,y-r,x+r,y+r),outline=rgba(col,215),fill=rgba(mix(OBSIDIAN,col,.12),fill_alpha),width=2)
    if label:
        draw.text((x,y),label,font=font or TINY_FONT,fill=text_col or IVORY,anchor='mm')


def draw_slice(draw,x,y,w,h,col,alpha=42,offset=0):
    pts=[(x-w,y-h),(x+w,y-h+offset),(x+w,y+h+offset),(x-w,y+h)]
    draw.polygon(pts,outline=rgba(col,150),fill=rgba(col,alpha))


@dataclass
class Scene:
    id:str
    title:str
    subtitle:str
    term:str
    summary:str
    mode:str
    tags:list[str]
    group:str
    technique:str
    source_status:str
    textual_anchor:str
    draw_fn:Callable[[Image.Image,float],None]


# ---------- scenes ----------

def sc01(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,278
    # simultaneous field above, sequential trace below
    for i in range(8):
        a=i*2*math.pi/8+t*.05
        x=cx+math.cos(a)*195; y=cy-52+math.sin(a)*92
        draw_node(d,x,y,13,mix(INDIGO,GOLD_LIGHT,i/8),str(i+1),42,TINY_FONT)
        draw_line_glow(im,[(cx,cy-52),(x,y)],mix(INDIGO,GOLD,i/8),2,60,4)
    draw_glow(im,(cx,cy-52),48,GOLD_LIGHT,110,14)
    d.ellipse((cx-18,cy-70,cx+18,cy-34),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    # sequential trace
    y2=425
    xs=np.linspace(260,1020,8)
    for i,x in enumerate(xs):
        draw_node(d,float(x),y2,10,mix(COPPER,GOLD,i/8),str(i+1),40,TINY_FONT)
        if i<len(xs)-1:
            pts=partial_polyline(bezier((x+10,y2),(x+35,y2-22),(xs[i+1]-35,y2+22),(xs[i+1]-10,y2),60),smoothstep(.05+i*.06,.72+i*.03,t))
            if len(pts)>1:
                draw_line_glow(im,pts,mix(COPPER,GOLD,i/8),2,80,5)
                draw_arrowhead(d,pts[-2],pts[-1],mix(COPPER,GOLD,i/8),.7)
    d.text((640,500),'one complete field appears as a chain from the contracted viewpoint',font=SUB_FONT,fill=ASH,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    # all events visible at once on one plate
    d.rounded_rectangle((230,130,1050,425),radius=24,outline=rgba(INDIGO,150),fill=rgba(DEEP_BLUE,35),width=2)
    events=[]
    for r in range(3):
        for c in range(6):
            x=310+c*132; y=195+r*82
            events.append((x,y))
    for i,(x,y) in enumerate(events):
        col=mix(INDIGO,GOLD_LIGHT,i/max(1,len(events)-1))
        draw_node(d,x,y,12,col,None,34)
        for j in [1,6]:
            if i+j<len(events):
                d.line((x,y,events[i+j][0],events[i+j][1]),fill=rgba(SLATE,35),width=1)
    draw_glow(im,(cx,cy),58,GOLD_LIGHT,85,18)
    draw_eye(d,cx,cy,.75,GOLD_LIGHT)
    d.text((640,496),'non-successive awareness contains the complete causal pattern simultaneously',font=SUB_FONT,fill=ASH,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im)
    # transparent time slices revealed by moving aperture
    for i in range(7):
        x=260+i*118
        col=mix(INDIGO,COPPER,i/6)
        draw_slice(d,x,280,62,130,col,36,offset=i*4)
        d.text((x,434),f't{i+1}',font=TINY_FONT,fill=col,anchor='mm')
    sweep=lerp(215,1060,ease_in_out(t))
    draw_line_glow(im,[(sweep,135),(sweep,420)],GOLD_LIGHT,4,120,10)
    d.polygon([(sweep,130),(sweep-10,150),(sweep+10,150)],fill=rgba(GOLD_LIGHT,230))
    d.text((640,496),'prior and posterior arise when one luminous field is scanned in slices',font=SUB_FONT,fill=ASH,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,278
    draw_glow(im,(cx,cy),72,GOLD_LIGHT,125,20)
    draw_eye(d,cx,cy,.95,GOLD_LIGHT)
    # agency rays generating effects
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12
        x=cx+math.cos(a)*245; y=cy+math.sin(a)*150
        pts=partial_polyline(bezier((cx,cy),(cx+math.cos(a)*70,cy+math.sin(a)*45),(x-math.cos(a)*40,y-math.sin(a)*25),(x,y),75),smoothstep(.04+i*.025,.82,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(GOLD,INDIGO,i/12),2,85,5)
        draw_node(d,x,y,10,mix(GOLD,INDIGO,i/12),None,35)
    d.text((640,496),'Śiva is the universal agent through whose freedom every causal order appears',font=SUB_FONT,fill=ASH,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im)
    # cause and effect nested, not detached
    left,right=350,930; cy=278
    draw_glow(im,(left,cy),45,COPPER,90,14)
    draw_node(d,left,cy,70,COPPER,'cause',40,SMALL_FONT)
    draw_pot(d,right,cy,1.0,GOLD_LIGHT,220)
    d.text((right,390),'effect',font=SMALL_FONT,fill=GOLD_LIGHT,anchor='mm')
    # seed pattern inside both
    for cx,col in [(left,COPPER),(right,GOLD_LIGHT)]:
        for i in range(6):
            a=i*2*math.pi/6+t*.05
            x=cx+math.cos(a)*34; y=cy+math.sin(a)*24
            d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,200))
    pts=partial_polyline(bezier((left+70,cy),(520,190),(760,365),(right-75,cy),100),smoothstep(.05,.86,t))
    if len(pts)>1:
        draw_line_glow(im,pts,mix(COPPER,GOLD_LIGHT,.5),4,115,8)
        draw_arrowhead(d,pts[-2],pts[-1],GOLD_LIGHT,.9)
    d.text((640,496),'the effect articulates a power already held within the causal field',font=SUB_FONT,fill=ASH,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx=640
    # Māyā prism differentiating one beam into many tattvas
    draw_glow(im,(250,278),40,GOLD_LIGHT,110,12)
    d.ellipse((235,263,265,293),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    draw_line_glow(im,[(265,278),(505,278)],GOLD_LIGHT,5,120,8)
    prism=[(505,190),(625,278),(505,366)]
    d.polygon(prism,outline=rgba(VIOLET,210),fill=rgba(VIOLET,45))
    colors=[INDIGO,VIOLET,ROSE,COPPER,GOLD,TEAL,GREEN]
    for i,col in enumerate(colors):
        y=175+i*36
        pts=partial_polyline(bezier((625,278),(710,278),(825,y),(1030,y),80),smoothstep(.08+i*.04,.78+i*.03,t))
        if len(pts)>1: draw_line_glow(im,pts,col,3,100,6)
        draw_node(d,1050,y,9,col,str(i+1),35,TINY_FONT)
    d.text((565,398),'Māyā',font=TERM_FONT,fill=VIOLET,anchor='mm')
    d.text((640,496),'differentiation makes Śiva’s powers appear as separate causal levels',font=SUB_FONT,fill=ASH,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im)
    # causal loom of tattva sequence
    x0,x1=220,1060; y0,y1=150,420
    for i in range(10):
        y=lerp(y0,y1,i/9)
        col=mix(INDIGO,COPPER,i/9)
        d.line((x0,y,x1,y),fill=rgba(col,65),width=1)
    for j in range(8):
        x=lerp(x0,x1,j/7)
        d.line((x,y0,x,y1),fill=rgba(SLATE,50),width=1)
    # golden shuttle weaving sequence
    shuttle_x=lerp(x0+20,x1-20,ease_in_out(t))
    points=[]
    for i in range(10):
        y=lerp(y0,y1,i/9)
        x=shuttle_x+math.sin(i*.9+t*3)*22
        points.append((x,y))
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,ROSE,i/10),210))
    draw_line_glow(im,points,GOLD_LIGHT,3,105,7)
    d.text((640,496),'the tattva sequence is a woven order of relative prior and posterior',font=SUB_FONT,fill=ASH,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im)
    # same matrix branches differently for three observers
    source=(640,145)
    draw_glow(im,source,36,GOLD_LIGHT,100,12)
    d.ellipse((626,131,654,159),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    observers=[(300,390,ROSE,'pleasure'),(640,390,TEAL,'neutral'),(980,390,COPPER,'pain')]
    for i,(x,y,col,lab) in enumerate(observers):
        pts=partial_polyline(bezier(source,(640,220),(x,245),(x,y-42),90),smoothstep(.04+i*.08,.82,t))
        if len(pts)>1: draw_line_glow(im,pts,col,3,100,6)
        draw_node(d,x,y,42,col,None,50)
        draw_eye(d,x,y,.38,col)
        d.text((x,y+65),lab,font=SMALL_FONT,fill=col,anchor='mm')
        for k in range(5):
            a=-math.pi/2+k*2*math.pi/5
            xx=x+math.cos(a)*78; yy=y+math.sin(a)*45
            draw_node(d,xx,yy,7,col,None,32)
    d.text((640,496),'the causal stream is individuated as distinct fields of pleasure and pain',font=SUB_FONT,fill=ASH,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    # karma loop: action -> trace -> fruition -> action
    labels=[('act',COPPER),('trace',VIOLET),('fruit',GOLD),('desire',ROSE)]
    pts=[]
    for i,(lab,col) in enumerate(labels):
        a=-math.pi/2+i*2*math.pi/4
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*115
        pts.append((x,y,col,lab))
        draw_node(d,x,y,38,col,lab,50,SMALL_FONT)
    for i,(x,y,col,lab) in enumerate(pts):
        nx,ny,ncol,_=pts[(i+1)%4]
        curve=partial_polyline(bezier((x,y),(x+(nx-x)*.3+40, y+(ny-y)*.3),(x+(nx-x)*.7-40,y+(ny-y)*.7),(nx,ny),75),smoothstep(.05+i*.08,.84,t))
        if len(curve)>1:
            draw_line_glow(im,curve,mix(col,ncol,.5),3,95,6)
            draw_arrowhead(d,curve[-2],curve[-1],mix(col,ncol,.5),.8)
    draw_glow(im,(cx,cy),44,CRIMSON,80,12)
    d.text((cx,cy),'karman',font=TERM_FONT,fill=CRIMSON,anchor='mm')
    d.text((640,496),'action becomes a recursive causal loop within contracted agency',font=SUB_FONT,fill=ASH,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im)
    # higher possesses, lower appears as its power
    xs=np.linspace(250,1030,6); y=280
    cols=[GOLD_LIGHT,GOLD,TEAL,INDIGO,VIOLET,COPPER]
    for i,x in enumerate(xs):
        r=52-i*5
        draw_node(d,float(x),y,r,cols[i],str(i+1),42,TERM_FONT)
        if i<len(xs)-1:
            pts=partial_polyline(bezier((x+r,y),(x+80,y-40),(xs[i+1]-80,y+40),(xs[i+1]-(r-5),y),70),smoothstep(.05+i*.08,.82,t))
            if len(pts)>1:
                draw_line_glow(im,pts,mix(cols[i],cols[i+1],.5),3,95,6)
                draw_arrowhead(d,pts[-2],pts[-1],mix(cols[i],cols[i+1],.5),.8)
        d.text((x,370),'possessor' if i==0 else 'power',font=TINY_FONT,fill=cols[i],anchor='mm')
    d.text((640,496),'each lower tattva appears as the power of the higher principle',font=SUB_FONT,fill=ASH,anchor='mm')


def sc11(im,t):
    d=ImageDraw.Draw(im)
    # forward emanation and reverse absorption on same vertical spine
    cx=640; ys=np.linspace(135,430,10)
    for i,y in enumerate(ys):
        col=mix(GOLD_LIGHT,COPPER,i/9)
        draw_node(d,cx,float(y),13,col,str(i+1),34,TINY_FONT)
    # downward path
    down=partial_polyline([(cx-65,float(y)) for y in ys],smoothstep(.03,.82,t))
    if len(down)>1:
        draw_line_glow(im,down,COPPER,4,115,8); draw_arrowhead(d,down[-2],down[-1],COPPER,1.0)
    # upward path
    up=partial_polyline([(cx+65,float(y)) for y in ys[::-1]],smoothstep(.15,.94,t))
    if len(up)>1:
        draw_line_glow(im,up,TEAL,4,115,8); draw_arrowhead(d,up[-2],up[-1],TEAL,1.0)
    d.text((500,278),'sṛṣṭi',font=TERM_FONT,fill=COPPER,anchor='mm')
    d.text((780,278),'saṃhāra',font=TERM_FONT,fill=TEAL,anchor='mm')
    d.text((640,496),'emanation and reabsorption traverse one structure in opposite readings',font=SUB_FONT,fill=ASH,anchor='mm')


def sc12(im,t):
    d=ImageDraw.Draw(im)
    # pot in thought and external world
    left,right=380,900; cy=280
    d.rounded_rectangle((210,145,550,420),radius=22,outline=rgba(INDIGO,140),fill=rgba(DEEP_BLUE,30),width=2)
    d.rounded_rectangle((730,145,1070,420),radius=22,outline=rgba(COPPER,140),fill=rgba(COPPER,18),width=2)
    draw_pot(d,left,cy,.85,INDIGO,190)
    draw_pot(d,right,cy,.85,COPPER,210)
    d.text((left,390),'saṅkalpa',font=SMALL_FONT,fill=INDIGO,anchor='mm')
    d.text((right,390),'bahis',font=SMALL_FONT,fill=COPPER,anchor='mm')
    # common pattern membrane
    for i in range(8):
        a=i*2*math.pi/8+t*.06
        lx=left+math.cos(a)*38; ly=cy+math.sin(a)*26
        rx=right+math.cos(a)*38; ry=cy+math.sin(a)*26
        d.ellipse((lx-3,ly-3,lx+3,ly+3),fill=rgba(GOLD_LIGHT,190))
        d.ellipse((rx-3,ry-3,rx+3,ry+3),fill=rgba(GOLD_LIGHT,190))
    draw_line_glow(im,[(left+95,cy),(right-95,cy)],GOLD_LIGHT,3,100,7)
    d.text((640,496),'thought-form and external form share one avabhāsa-pattern in consciousness',font=SUB_FONT,fill=ASH,anchor='mm')


def sc13(im,t):
    d=ImageDraw.Draw(im)
    # split screen: global simultaneous vs local sequential
    d.line((640,125,640,430),fill=rgba(ASH,90),width=2)
    # global side
    d.text((335,125),'global view',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    for i in range(9):
        a=i*2*math.pi/9
        x=335+math.cos(a)*145; y=285+math.sin(a)*95
        draw_node(d,x,y,10,mix(INDIGO,GOLD_LIGHT,i/9),str(i+1),32,TINY_FONT)
        draw_line_glow(im,[(335,285),(x,y)],mix(INDIGO,GOLD_LIGHT,i/9),1,45,3)
    draw_eye(d,335,285,.5,GOLD_LIGHT)
    # local side
    d.text((945,125),'local view',font=TERM_FONT,fill=COPPER,anchor='mm')
    xs=np.linspace(760,1130,9)
    for i,x in enumerate(xs):
        draw_node(d,float(x),285,9,mix(COPPER,GOLD,i/9),str(i+1),30,TINY_FONT)
        if i<len(xs)-1:
            d.line((x+9,285,xs[i+1]-9,285),fill=rgba(COPPER,100),width=2)
    moving=lerp(760,1130,ease_in_out(t))
    draw_glow(im,(moving,285),22,GOLD_LIGHT,80,8)
    d.text((640,496),'simultaneity belongs to the whole; succession belongs to contracted access',font=SUB_FONT,fill=ASH,anchor='mm')


def sc14(im,t):
    d=ImageDraw.Draw(im); cx,cy=640,280
    # final causal seal: outer chain folds into inner eye
    for r,col,n in [(225,INDIGO,18),(170,VIOLET,14),(116,COPPER,10)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,130),width=2)
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.04*(1 if n%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            draw_node(d,x,y,5,mix(col,GOLD_LIGHT,i/n),None,28)
    # cause-effect arrows fold inward
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        p0=(cx+math.cos(a)*205,cy+math.sin(a)*145)
        p1=(cx+math.cos(a)*62,cy+math.sin(a)*42)
        pts=partial_polyline(bezier(p0,(cx+math.cos(a+.2)*155,cy+math.sin(a+.2)*105),(cx+math.cos(a-.2)*95,cy+math.sin(a-.2)*65),p1,65),smoothstep(.05+i*.04,.84,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(INDIGO,GOLD_LIGHT,i/8),2,70,5)
    draw_glow(im,(cx,cy),66,GOLD_LIGHT,120,18)
    draw_eye(d,cx,cy,.72,GOLD_LIGHT)
    d.text((640,496),'every causal relation folds into one non-successive act of awareness',font=SUB_FONT,fill=ASH,anchor='mm')


SCENES=[
    Scene('kk01','The Causal Problem','One complete field appears as sequential cause and effect.','Kārya–Kāraṇa','Overview of simultaneity and apparent succession.','overview_field',['overview','causality','succession'],'overview','simultaneous orbit plus sequential trace','derived','Tantrāloka 9.1–48; chapter overview',sc01),
    Scene('kk02','Non-Successive Consciousness','The total causal pattern is present in a single luminous field.','Akramasaṃvit','Consciousness is not internally divided by sequence.','simultaneous_plate',['consciousness','simultaneity'],'theory','event plate with eye-field','synthetic','Conceptual synthesis from Tantrāloka 9.1–48',sc02),
    Scene('kk03','Prior and Posterior','Succession emerges through the scanning of transparent time-slices.','Paurvāparya','Prior and posterior are modes of manifestation.','time_slices',['succession','prior','posterior'],'theory','moving aperture through slices','derived','Tantrāloka 9.25–48; varied manifestation of succession',sc03),
    Scene('kk04','The Universal Agent','Śiva’s freedom manifests every causal order.','Sarvakartṛtva','Universal agency grounds the appearance of causes and effects.','universal_agent',['agency','shiva','freedom'],'theory','central eye with agency rays','derived','Tantrāloka Chapter 9 causality discussion; Dyczkowski overview',sc04),
    Scene('kk05','Cause Within Effect','The effect articulates a power already held in the causal field.','Kāraṇa–Kārya','Cause and effect are internally related manifestations.','nested_effect',['cause','effect','power'],'theory','cause chamber to pot effect','synthetic','Interpretive visualization of Tantrāloka 9.1–48',sc05),
    Scene('kk06','Māyā Differentiates','One power refracts into apparently separate causal levels.','Māyā','Differentiation makes tattvas appear as distinct effects.','maya_prism',['maya','differentiation','tattvas'],'process','prism splitting one beam','direct','Tantrāloka 9.142–166; 9.154–158',sc06),
    Scene('kk07','The Causal Loom','The tattvas are woven as an ordered stream of relative succession.','Tattvakrama','The principles possess a varied order of prior and posterior.','causal_loom',['tattvas','sequence','loom'],'process','woven grid and shuttle','derived','Tantrāloka 9.49–60 and 9.25–48',sc07),
    Scene('kk08','Individual Causal Streams','One matrix appears differently for each finite subject.','Pratyātma-bheda','Pleasure and pain reveal individualized causal fields.','individual_streams',['individual','pleasure','pain'],'process','three observer branches','direct','Tantrāloka 9.160–170; distinction per individual soul',sc08),
    Scene('kk09','The Karmic Recursion','Action becomes trace, fruition, desire, and renewed action.','Karman','Contracted agency generates a recursive causal loop.','karma_loop',['karma','action','recursion'],'process','four-node causal wheel','direct','Tantrāloka 9.88–141',sc09),
    Scene('kk10','Power and Possessor','Each lower principle appears as the power of the higher.','Śakti–Śaktimat','Adjacent tattvas relate as power and possessor.','power_possessor',['power','tattvas','hierarchy'],'theory','descending linked chambers','direct','Tantrāloka 9.312',sc10),
    Scene('kk11','Emanation and Reabsorption','One order can be read forward as creation and backward as return.','Sṛṣṭi–Saṃhāra','The same tattvic architecture supports opposite sequences.','double_reading',['emanation','reabsorption','sequence'],'process','dual-direction spine','derived','Tantrāloka 9 tattva sequence; tradition of sṛṣṭi and saṃhāra orders',sc11),
    Scene('kk12','The Pot in Thought and World','Mental and external form share one manifestation-pattern.','Avabhāsa','Thought-form and outer form arise within consciousness.','pot_mirror',['thought','world','pot'],'epistemic','paired pot chambers','direct','Tantrāloka 9.159',sc12),
    Scene('kk13','Global and Local Time','The whole is simultaneous; contracted access is sequential.','Krama–Akrama','Sequence depends on the scale and mode of access.','global_local',['global','local','time'],'synthesis','split simultaneous/sequential view','synthetic','Conceptual synthesis from Tantrāloka 9 causality and succession',sc13),
    Scene('kk14','The Causal Seal','All causal relations fold into one act of awareness.','Kāryakāraṇa-cakra','The complete causal field resolves into non-successive consciousness.','closing_seal',['seal','causality','awareness'],'seal','nested causal rings and eye','synthetic','Closing synthesis based on Tantrāloka Chapter 9',sc14),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1)
            im=causal_ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,72); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
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
    sheet=Image.new('RGB',(cols*320,rows*180),color=NIGHT)
    for idx,im in enumerate(thumbs):
        sheet.paste(im,((idx%cols)*320,(idx//cols)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
        'project':'Tantrāloka — Kārya–Kāraṇa: Causality and Apparent Succession',
        'source_basis':'Tantrāloka Chapter 9, especially verses 1–60, 142–170, 312, and chapter-level overviews of kāryakāraṇabhāva and tattvakrama.',
        'source_critical_note':'Direct textual claims are separated from derived philosophical diagrams and synthetic visual inferences.',
        'style':{
            'family':'causal-field architecture / transparent time mechanics',
            'background':'obsidian indigo field',
            'ink':'ash and gold',
            'accent':'copper, violet, teal, rose',
            'materials':['transparent time slices','causal loom','prism differentiation','observer branches','nested causal rings']
        },
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[
            {'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'source_status':sc.source_status,'textual_anchor':sc.textual_anchor,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'}
            for sc in SCENES
        ]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id:sc.title for sc in SCENES},
        'modes':{sc.id:sc.mode for sc in SCENES},
        'theme_clusters':{
            'causal_problem':['kk01','kk02','kk03','kk04','kk05'],
            'differentiation_and_sequence':['kk06','kk07','kk08','kk10','kk11'],
            'karma_and_epistemology':['kk09','kk12','kk13'],
            'seal':['kk14']
        },
        'reusability_notes':{
            'kk01':'Use for causality, simultaneity versus sequence, or chapter introductions.',
            'kk02':'Use for non-successive consciousness or all-at-once fields.',
            'kk03':'Use for temporal ordering, prior and posterior, or scanning effects.',
            'kk04':'Use for universal agency or svātantrya.',
            'kk06':'Use for Māyā as differentiation rather than simple illusion.',
            'kk07':'Use for ordered tattva manifestation or causal weaving.',
            'kk08':'Use for individualized experience and differing causal worlds.',
            'kk09':'Use for karmic recursion and action-fruit loops.',
            'kk12':'Use for avabhāsa, internal/external form, or mirror epistemology.',
            'kk13':'Use for global versus local views of time.',
            'kk14':'Use as a closing causality seal.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))

    dossier='''# AGENT KNOWLEDGE DOSSIER — Kārya–Kāraṇa

## Aim
This pack visualizes Chapter 9's account of **cause, effect, tattva sequence, Māyā, karma, and apparent succession**.

## Core problem
The nondual system must explain why a universe that is one act of consciousness appears as a chain of prior and posterior events. The pack distinguishes:

- the **global, non-successive field** of consciousness;
- the **local, contracted sequence** experienced by finite subjects;
- the role of **Māyā** in differentiating powers into separate levels;
- **karma** as recursive causation under contracted agency;
- the tattvas as ordered relations of **power and possessor**.

## Textual anchors
- Tantrāloka 9.1–48: cause and effect
- 9.49–60: sequence of the principles
- 9.88–141: karma
- 9.142–170: Māyā and differentiated tattvas
- 9.159: form in thought and external form
- 9.312: lower principle as power of the higher

## Visual rules
- Do not represent consciousness as one more event inside time.
- Sequence must appear as a mode of access, scanning, or differentiation.
- Māyā should be a differentiating matrix, not a cartoon lie.
- Karma should be recursive and agent-relative.
- The closing seal must fold the causal chain into a simultaneous awareness-field.

## Direct / derived / synthetic distinction
Each manifest scene is marked:
- **direct** — closely tied to a cited textual claim;
- **derived** — a visual interpretation of a supported argument;
- **synthetic** — a conceptual model added for explanatory clarity.

## Reuse strategy
- kk01–kk05: causal theory
- kk06–kk11: differentiated tattva sequence and agency
- kk12–kk13: epistemic and viewpoint consequences
- kk14: final synthesis
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')

    notes='''# SOURCE NOTES — Kārya–Kāraṇa Pack

## Primary textual frame
Tantrāloka Chapter 9 is titled Tattvādhvā and opens with the relation between cause and effect, followed by the sequence of the principles.

## Important source distinctions
1. The claim that there is a varied manifestation of prior and posterior among the tattvas is textual.
2. The split-screen distinction between global simultaneity and local succession is a synthetic explanatory visualization.
3. Māyā as differentiating power and material cause for lower levels is textual.
4. The individual differentiation of the causal stream, evidenced through pleasure and pain, is textual.
5. The pot-in-thought and external-pot scene is anchored in verse 159.
6. The final causal seal is a synthetic summary and not a traditional maṇḍala.

## Research sources used
- Anuttara Trika Kula, Chapter 9 overview
- Sanskrit & Trika Shaivism, Tantrāloka Chapter 9 Sanskrit and English rendering
'''
    (ROOT/'SOURCE_NOTES.md').write_text(notes,encoding='utf-8')

    style='''# STYLE EVOLUTION — Kārya–Kāraṇa Pack

## Differentiation
This pack shifts away from world-atlas imagery into **causal mechanics**:

- transparent time slices
- simultaneous event plates
- causal looms
- differentiation prisms
- recursive karma wheels
- global/local split views
- cause-effect mirror chambers

## New relationships
1. simultaneous field → sequential scan
2. universal agency → differentiated effects
3. Māyā → separate causal levels
4. one matrix → different individual streams
5. action → trace → fruition → renewed action
6. higher principle → lower principle as power
7. emanation ↔ reabsorption

## New materials
- black causal glass
- gold filament
- copper event traces
- violet differentiation prism
- translucent time membranes

## Closing seal
Nested causal chains fold into a central eye, signifying that causal order is a mode of the one awareness-field.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')

    readme=f'''# Tantrāloka — Kārya–Kāraṇa Pack

Included:
- karya_karana_causality_animation.mp4
- contact_sheet.jpg
- scenes/*.mp4
- render_pack.py
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- SOURCE_NOTES.md
- STYLE_EVOLUTION.md
- validation.json

Specs:
- {W}x{H}
- {FPS} fps
- {len(SCENES)} scenes
- {DURATION}s per scene
- {len(SCENES)*DURATION:.1f}s total

Render:
```bash
python render_pack.py
```
Resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')


def validate_outputs():
    combined=ROOT/'karya_karana_causality_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))


def make_zip():
    zpath=ROOT/'karya_karana_causality_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['karya_karana_causality_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','SOURCE_NOTES.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):
            zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True)
        render_scene(sc)
    concat_file=ROOT/'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'karya_karana_causality_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
