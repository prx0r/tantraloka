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
SEED = 11111

# Purification / mirror-thread palette
NIGHT = (15, 20, 30)
OBSIDIAN = (25, 31, 43)
MERCURY = (205, 214, 224)
SILVER = (231, 236, 241)
LAPIS = (58, 79, 139)
DEEP_LAPIS = (39, 55, 101)
INDIGO = (82, 92, 151)
TEAL = (75, 137, 141)
SAFFRON = (224, 154, 54)
GOLD = (204, 163, 82)
GOLD_LIGHT = (243, 212, 136)
CRIMSON = (150, 47, 63)
ROSE = (183, 105, 133)
COPPER = (181, 103, 67)
GREEN = (93, 139, 105)
ASH = (164, 174, 191)
MIST = (208, 214, 224)
IVORY = (242, 239, 229)
WHITE = (252, 249, 241)
SLATE = (97, 108, 129)
BLACK = (7, 9, 13)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 27)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t):
    t=clamp(t); return .5-.5*math.cos(math.pi*t)
def ease_out_cubic(t):
    t=clamp(t); return 1-(1-t)**3
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3],int(a))


def purifier_ground(seed:int):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(46,82)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.8 + fine[...,None]*1.0
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*18,0,27); base -= vign[...,None]
    band=np.exp(-(((xx-W/2)/(W*.40))**2 + ((yy-H*.36)/(H*.22))**2)*2.3)
    base[...,0]+=band*8; base[...,1]+=band*13; base[...,2]+=band*26
    lower=np.exp(-(((xx-W*.50)/(W*.22))**2 + ((yy-H*.68)/(H*.18))**2)*2.8)
    base[...,0]+=lower*12; base[...,1]+=lower*8; base[...,2]+=lower*2
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def draw_glow(im,xy,radius,color,alpha=150,blur=18):
    gl=layer(); d=ImageDraw.Draw(gl); x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,alpha))
    gl=gl.filter(ImageFilter.GaussianBlur(blur)); im.alpha_composite(gl)

def draw_line_glow(im,pts,color,width=3,alpha=150,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    gl=gl.filter(ImageFilter.GaussianBlur(blur)); im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+75)),width=width,joint='curve')

def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(ASH,115),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,95),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,LAPIS,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(15,19,29,208),outline=rgba(ASH,70),width=1)
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
        a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    pts=[p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)]
    draw.polygon(pts,fill=rgba(color,230))
def dust(im,seed,n=78):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(115,W-115)); y=float(rng.uniform(100,H-180)); r=float(rng.uniform(.8,2.1))
        c=mix(ASH,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,72))))
    im.alpha_composite(ov)
def draw_eye(draw,cx,cy,scale=1.0,col=GOLD_LIGHT):
    draw.arc((cx-72*scale,cy-34*scale,cx+72*scale,cy+34*scale),180,360,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.arc((cx-72*scale,cy-34*scale,cx+72*scale,cy+34*scale),0,180,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.ellipse((cx-15*scale,cy-15*scale,cx+15*scale,cy+15*scale),fill=rgba(col,210))
def draw_node(draw,x,y,r,col,label=None,fill_alpha=48,font=None,text_col=None):
    draw.ellipse((x-r,y-r,x+r,y+r),outline=rgba(col,215),fill=rgba(mix(OBSIDIAN,col,.12),fill_alpha),width=2)
    if label: draw.text((x,y),label,font=font or TINY_FONT,fill=text_col or IVORY,anchor='mm')
def draw_mirror(draw,cx,cy,w,h,col=MERCURY,alpha=160):
    draw.rounded_rectangle((cx-w,cy-h,cx+w,cy+h),radius=22,outline=rgba(col,alpha),fill=rgba(mix(OBSIDIAN,col,.12),34),width=2)
    draw.arc((cx-w*.72,cy-h*.56,cx+w*.72,cy+h*.56),210,325,fill=rgba(SILVER,105),width=2)
def draw_thread_bundle(im,p0,p1,cols,spread=20,amount=1.0,width=2):
    for i,col in enumerate(cols):
        off=(i-(len(cols)-1)/2)*spread
        pts=partial_polyline(bezier((p0[0],p0[1]+off),(lerp(p0[0],p1[0],.35),p0[1]-35+off*.3),(lerp(p0[0],p1[0],.65),p1[1]+35-off*.3),(p1[0],p1[1]-off),85),amount)
        if len(pts)>1: draw_line_glow(im,pts,col,width,85,5)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; source_status:str; textual_anchor:str; draw_fn:Callable[[Image.Image,float],None]

# ---------- scenes ----------

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    left=[('Varṇa',LAPIS),('Mantra',ROSE),('Pada',TEAL)]
    right=[('Kalā',GREEN),('Tattva',COPPER),('Bhuvana',GOLD)]
    ys=[185,282,379]
    d.text((305,120),'ŚODHAKA / VĀCAKA',font=TERM_FONT,fill=MERCURY,anchor='mm')
    d.text((975,120),'ŚODHYA / VĀCYA',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    for (lab,col),y in zip(left,ys): draw_node(d,305,y,38,col,lab,58,SMALL_FONT)
    for (lab,col),y in zip(right,ys): draw_node(d,975,y,38,col,lab,58,SMALL_FONT)
    for i,y in enumerate(ys):
        pts=partial_polyline(bezier((345,y),(470,y-45+i*15),(810,y+45-i*15),(935,y),100),smoothstep(.04+i*.1,.84,t))
        col=mix(left[i][1],right[i][1],.5)
        if len(pts)>1:
            draw_line_glow(im,pts,col,4,120,8); draw_arrowhead(d,pts[-2],pts[-1],col,.9)
    draw_glow(im,(cx,cy),54,SILVER,110,18); draw_eye(d,cx,cy,.58,GOLD_LIGHT)
    d.text((640,496),'the expressive paths purify the manifested paths within one awareness-field',font=SUB_FONT,fill=ASH,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im)
    draw_mirror(d,355,278,180,150,MERCURY,170); draw_mirror(d,925,278,180,150,GOLD,160)
    d.text((355,118),'DENOTATOR',font=TERM_FONT,fill=MERCURY,anchor='mm'); d.text((925,118),'DENOTED',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    for i,ch in enumerate(['अ','हं','शि','व']):
        x=285+i*48; d.text((x,278),ch,font=DEVA_MED,fill=mix(LAPIS,ROSE,i/4),anchor='mm')
    # world symbols
    for i,(x,y,col) in enumerate([(860,240,GREEN),(940,220,GOLD),(1000,300,COPPER),(875,330,TEAL)]):
        draw_node(d,x,y,14,col,None,42)
    amount=smoothstep(.05,.86,t); draw_thread_bundle(im,(535,278),(745,278),[LAPIS,ROSE,TEAL,GOLD],14,amount,3)
    d.text((640,496),'word and world are not two substances but two functions of manifestation',font=SUB_FONT,fill=ASH,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    left=[('Varṇa',LAPIS),('Mantra',ROSE),('Pada',TEAL)]; right=[('Kalā',GREEN),('Tattva',COPPER),('Bhuvana',GOLD)]
    for i,(lab,col) in enumerate(left):
        a=-math.pi/2+i*2*math.pi/3; x=cx-170+math.cos(a)*92; y=cy+math.sin(a)*82
        draw_node(d,x,y,34,col,lab,52,SMALL_FONT)
    for i,(lab,col) in enumerate(right):
        a=-math.pi/2+i*2*math.pi/3; x=cx+170+math.cos(a)*92; y=cy+math.sin(a)*82
        draw_node(d,x,y,34,col,lab,52,SMALL_FONT)
    draw_glow(im,(cx,cy),56,GOLD_LIGHT,110,16); draw_eye(d,cx,cy,.55,GOLD_LIGHT)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6+t*.04; x=cx+math.cos(a)*236; y=cy+math.sin(a)*142
        draw_line_glow(im,[(cx,cy),(x,y)],mix(INDIGO,GOLD_LIGHT,i/6),2,60,4)
    d.text((640,496),'all six paths are threaded through cognition, subject, object, and knowing',font=SUB_FONT,fill=ASH,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    draw_mirror(d,cx,cy,255,160,MERCURY,180)
    # dream image / world image
    for i in range(11):
        a=i*2*math.pi/11+t*.05; r=78+20*math.sin(i*.7)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.62
        draw_node(d,x,y,7,mix(LAPIS,GOLD_LIGHT,i/11),None,34)
    draw_glow(im,(cx,cy),42,SILVER,100,12); draw_eye(d,cx,cy,.38,SILVER)
    d.text((330,145),'dream',font=TERM_FONT,fill=ROSE,anchor='mm'); d.text((950,145),'world',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    pts=partial_polyline(bezier((360,185),(450,220),(520,250),(585,270),85),smoothstep(.06,.84,t))
    pts2=partial_polyline(bezier((920,185),(830,220),(760,250),(695,270),85),smoothstep(.06,.84,t))
    if len(pts)>1: draw_line_glow(im,pts,ROSE,3,90,6)
    if len(pts2)>1: draw_line_glow(im,pts2,GOLD,3,90,6)
    d.text((640,496),'dream and world both arise as images within reflective awareness',font=SUB_FONT,fill=ASH,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im)
    # word and world interpenetration
    xs=[250,520,760,1030]; labs=['VARṆA','MANTRA','PADA','WORLD']; cols=[LAPIS,ROSE,TEAL,GOLD]
    for x,lab,col in zip(xs,labs,cols):
        draw_node(d,x,278,38,col,lab,58,SMALL_FONT)
    for i in range(3):
        pts=partial_polyline(bezier((xs[i]+38,278),(xs[i]+95,220),(xs[i+1]-95,336),(xs[i+1]-38,278),90),smoothstep(.05+i*.12,.75+i*.08,t))
        if len(pts)>1:
            col=mix(cols[i],cols[i+1],.5); draw_line_glow(im,pts,col,4,115,7); draw_arrowhead(d,pts[-2],pts[-1],col,.85)
    d.text((640,496),'language progressively reveals itself as the structure of manifestation',font=SUB_FONT,fill=ASH,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # noetic consciousness lens
    for r,col in [(190,SLATE),(140,INDIGO),(92,LAPIS)]: d.ellipse((cx-r,cy-r*.68,cx+r,cy+r*.68),outline=rgba(col,120),width=2)
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*205; y=cy+math.sin(a)*135
        pts=partial_polyline(bezier((x,y),(cx+math.cos(a)*150,cy+math.sin(a)*95),(cx+math.cos(a)*90,cy+math.sin(a)*55),(cx,cy),75),smoothstep(.03+i*.03,.82,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(LAPIS,SILVER,i/12),2,75,5)
    draw_glow(im,(cx,cy),58,SILVER,120,18); draw_eye(d,cx,cy,.62,SILVER)
    d.text((640,496),'noetic consciousness is purified as its phonemic ground becomes transparent',font=SUB_FONT,fill=ASH,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # subject membranes become transparent
    for i,(r,col) in enumerate([(190,CRIMSON),(145,VIOLET if 'VIOLET' in globals() else INDIGO),(100,LAPIS)]):
        alpha=int(165*(1-ease_in_out(t)*(.18+.18*i))); d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(col,alpha),width=3)
    draw_glow(im,(cx,cy),62,GOLD_LIGHT,115,18); draw_eye(d,cx,cy,.58,GOLD_LIGHT)
    d.text((640,496),'the subject is purified when its contracted membranes cease to appear absolute',font=SUB_FONT,fill=ASH,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # object field in layers stripped of independence
    for i in range(9):
        a=i*2*math.pi/9+t*.03; r=170
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.65
        draw_node(d,x,y,12,mix(GREEN,GOLD,i/9),str(i+1),42,TINY_FONT)
        pts=partial_polyline(bezier((x,y),(cx+math.cos(a)*118,cy+math.sin(a)*77),(cx+math.cos(a)*66,cy+math.sin(a)*40),(cx,cy),70),smoothstep(.05+i*.04,.84,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(GREEN,GOLD,i/9),2,72,5)
    draw_glow(im,(cx,cy),55,GOLD_LIGHT,105,16); d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,496),'the object is purified when its appearance is recollected into consciousness',font=SUB_FONT,fill=ASH,anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im)
    # means of knowledge as bridge instrument
    draw_eye(d,270,280,.55,LAPIS); draw_mirror(d,640,280,105,90,MERCURY,160); draw_node(d,1010,280,42,GOLD,'object',55,SMALL_FONT)
    pts=partial_polyline(bezier((330,280),(430,220),(505,240),(535,280),80),smoothstep(.04,.74,t))
    pts2=partial_polyline(bezier((745,280),(830,320),(910,300),(968,280),80),smoothstep(.18,.9,t))
    if len(pts)>1: draw_line_glow(im,pts,LAPIS,4,115,7)
    if len(pts2)>1: draw_line_glow(im,pts2,GOLD,4,115,7)
    draw_glow(im,(640,280),42,SILVER,100,12)
    d.text((270,145),'knower',font=SMALL_FONT,fill=LAPIS,anchor='mm'); d.text((640,145),'means',font=SMALL_FONT,fill=MERCURY,anchor='mm'); d.text((1010,145),'known',font=SMALL_FONT,fill=GOLD,anchor='mm')
    d.text((640,496),'the means of knowledge becomes transparent rather than standing between subject and object',font=SUB_FONT,fill=ASH,anchor='mm')

def sc10(im,t):
    d=ImageDraw.Draw(im)
    # six modes of purification
    labs=['enjoy','master','release','know as Śiva','merge','remove']; cols=[COPPER,GOLD,TEAL,LAPIS,ROSE,SILVER]
    xs=np.linspace(190,1090,6); y=278
    for i,(x,lab,col) in enumerate(zip(xs,labs,cols)):
        draw_node(d,float(x),y,30,col,str(i+1),50,SMALL_FONT)
        d.text((x,y+54),lab,font=TINY_FONT,fill=col,anchor='mm')
        if i<5:
            pts=partial_polyline(bezier((x+30,y),(x+65,y-26),(xs[i+1]-65,y+26),(xs[i+1]-30,y),70),smoothstep(.04+i*.1,.72+i*.06,t))
            if len(pts)>1: draw_line_glow(im,pts,mix(col,cols[i+1],.5),2,85,5)
    d.text((640,496),'purification can proceed through enjoyment, mastery, release, recognition, merger, or removal',font=SUB_FONT,fill=ASH,anchor='mm')

def sc11(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    # sequence vs no-sequence
    y1=205; xs=np.linspace(260,1020,6)
    for i,x in enumerate(xs):
        draw_node(d,float(x),y1,10,mix(COPPER,GOLD,i/6),str(i+1),36,TINY_FONT)
        if i<5: d.line((x+10,y1,xs[i+1]-10,y1),fill=rgba(mix(COPPER,GOLD,i/6),100),width=2)
    d.text((190,y1),'krama',font=SMALL_FONT,fill=COPPER,anchor='rm')
    # simultaneous flower
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; x=cx+math.cos(a)*145; y=385+math.sin(a)*78
        draw_node(d,x,y,14,mix(LAPIS,SILVER,i/6),str(i+1),40,TINY_FONT); draw_line_glow(im,[(cx,385),(x,y)],mix(LAPIS,SILVER,i/6),2,55,4)
    draw_glow(im,(cx,385),40,SILVER,100,12); draw_eye(d,cx,385,.35,SILVER)
    d.text((190,385),'akrama',font=SMALL_FONT,fill=LAPIS,anchor='rm')
    d.text((640,496),'the six modes may unfold sequentially or be grasped in one act',font=SUB_FONT,fill=ASH,anchor='mm')

def sc12(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    # guru unites six paths, non-instructional schematic
    draw_eye(d,260,278,.62,GOLD_LIGHT); draw_node(d,1020,278,44,LAPIS,'disciple',58,SMALL_FONT)
    cols=[LAPIS,ROSE,TEAL,GREEN,COPPER,GOLD]
    draw_thread_bundle(im,(330,278),(970,278),cols,14,smoothstep(.04,.9,t),3)
    for i,col in enumerate(cols):
        x=640+math.cos(-math.pi/2+i*2*math.pi/6)*92; y=278+math.sin(-math.pi/2+i*2*math.pi/6)*64
        draw_node(d,x,y,8,col,None,35)
    d.text((260,145),'guru',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm'); d.text((1020,145),'integrated six-path field',font=SMALL_FONT,fill=LAPIS,anchor='mm')
    d.text((640,496),'the guru’s function is shown as unifying the six paths within the disciple',font=SUB_FONT,fill=ASH,anchor='mm')

def sc13(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # purifier gradually dissolves into purified
    draw_mirror(d,390,cy,135,110,MERCURY,170); draw_mirror(d,890,cy,135,110,GOLD,160)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6+t*.04; x=cx+math.cos(a)*105; y=cy+math.sin(a)*72
        draw_node(d,x,y,9,mix(LAPIS,GOLD,i/6),None,36)
    amount=ease_in_out(t)
    draw_thread_bundle(im,(525,cy),(755,cy),[LAPIS,ROSE,TEAL,GOLD],12,amount,3)
    draw_glow(im,(cx,cy),48,mix(SILVER,GOLD_LIGHT,amount),105,14); draw_eye(d,cx,cy,.4,GOLD_LIGHT)
    d.text((390,145),'purifier',font=TERM_FONT,fill=MERCURY,anchor='mm'); d.text((890,145),'purified',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,496),'at completion, purifier and purified are recognized as functions of one awareness',font=SUB_FONT,fill=ASH,anchor='mm')

def sc14(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    cols=[LAPIS,ROSE,TEAL,GREEN,COPPER,GOLD]
    for idx,(r,col) in enumerate(zip([215,180,145,110,78,48],cols)):
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,150),width=2)
        n=6+idx
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.03*(1 if idx%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
            draw_node(d,x,y,4,mix(col,SILVER,i/n),None,28)
    for i in range(6):
        a=-math.pi/2+i*2*math.pi/6; p0=(cx+math.cos(a)*205,cy+math.sin(a)*147); p1=(cx+math.cos(a)*52,cy+math.sin(a)*36)
        pts=partial_polyline(bezier(p0,(cx+math.cos(a+.22)*155,cy+math.sin(a+.22)*110),(cx+math.cos(a-.22)*95,cy+math.sin(a-.22)*65),p1,70),smoothstep(.05+i*.04,.84,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(LAPIS,GOLD_LIGHT,i/6),2,70,5)
    draw_glow(im,(cx,cy),66,GOLD_LIGHT,120,18); draw_eye(d,cx,cy,.72,GOLD_LIGHT)
    d.text((640,496),'the six paths, purifier, purified, knowing, knower, and known resolve into one field',font=SUB_FONT,fill=ASH,anchor='mm')

SCENES=[
    Scene('ss01','The Purification Engine','The expressive paths purify the manifested paths.','Śodhya–Śodhaka','Overview of purifier and purified across the six paths.','overview_engine',['overview','six paths','purification'],'overview','bilateral triads with central eye','derived','Tantrāloka 11.1–6 and 11.83–85',sc01),
    Scene('ss02','Denotator and Denoted','Speech and world are paired functions of manifestation.','Vācaka–Vācya','The denotator side operates as purifier of the denoted side.','denotator_denoted',['speech','world','denotation'],'theory','paired mercury and gold mirrors','derived','Tantrāloka 11; chapter overview and six-path doctrine',sc02),
    Scene('ss03','The Six Paths in One Field','All six paths are threaded through the structure of knowing.','Ṣaḍadhvan','Varṇa, mantra, pada, kalā, tattva, and bhuvana form one architecture.','six_path_field',['six paths','knowing','architecture'],'theory','two triads around central eye','direct','Tantrāloka 11.83–85',sc03),
    Scene('ss04','Mirror and Dream','World and dream both arise as reflective images.','Pratibimba','Manifestation is compared with reflection and dream.','mirror_dream',['mirror','dream','world'],'epistemic','mercury mirror with two approach paths','derived','Tantrāloka 11 reflection/dream discussion; chapter summaries',sc04),
    Scene('ss05','Word Becomes World','Phoneme, mantra, word, and manifestation form one chain.','Śabda–Artha','Language reveals itself as an ontological structure.','word_world_chain',['language','world','manifestation'],'process','four-node semantic chain','derived','Tantrāloka 11.71–82',sc05),
    Scene('ss06','Purifying Noetic Consciousness','Cognition reveals its phonemic and conscious ground.','Pramā-śuddhi','Noetic consciousness is purified through the six paths.','noetic_purification',['cognition','noetic consciousness','purification'],'process','centripetal cognition lens','direct','Tantrāloka 11.83–85',sc06),
    Scene('ss07','Purifying the Subject','Contracted observer-membranes become transparent.','Pramātṛ-śuddhi','The knowing subject is purified through recognition.','subject_purification',['subject','observer','purification'],'process','transparent observer membranes','direct','Tantrāloka 11.83–85',sc07),
    Scene('ss08','Purifying the Object','The object-field is recollected into awareness.','Prameya-śuddhi','The known ceases to appear independently self-sufficient.','object_purification',['object','recollection','purification'],'process','world nodes recollected inward','direct','Tantrāloka 11.83–85',sc08),
    Scene('ss09','Purifying the Means of Knowledge','The instrument of cognition becomes transparent.','Pramāṇa-śuddhi','Means of knowledge no longer stands as a hard barrier.','means_purification',['means of knowledge','bridge','purification'],'process','knower-mirror-known bridge','direct','Tantrāloka 11.83–85',sc09),
    Scene('ss10','Six Modes of Purification','Enjoyment, mastery, release, recognition, merger, and removal.','Ṣaḍvidha-śodhana','Purification is described in six operational modes.','six_modes',['enjoyment','mastery','merger'],'process','six-stage linear sequence','direct','Tantrāloka 11; Sanskrit-Trikashaivism rendering of six modes',sc10),
    Scene('ss11','Sequence and Non-Sequence','The six modes may unfold successively or at once.','Krama–Akrama','Purification may occur in sequence or non-sequentially.','sequence_nonsequence',['sequence','nonsequence','purification'],'theory','linear chain versus simultaneous flower','direct','Tantrāloka 11 purification discussion',sc11),
    Scene('ss12','The Guru Unites the Paths','The six paths are integrated within the disciple.','Adhva-saṃyojana','The guru is described as inspecting and uniting the six paths.','guru_unification',['guru','disciple','six paths'],'initiation','six luminous threads joining fields','direct','Tantrāloka 11 opening verses and Chapter 17 initiation summaries',sc12),
    Scene('ss13','Purifier Becomes Transparent','Purifier and purified are seen as functions of one awareness.','Śodhaka–Śodhya-aikya','The distinction is retained operationally but dissolved ultimately.','identity_resolution',['purifier','purified','identity'],'synthesis','paired mirrors merging through threads','synthetic','Conceptual synthesis from Tantrāloka 11 nondual purification',sc13),
    Scene('ss14','The Purification Seal','All six paths fold into one awareness-field.','Śodhana-cakra','The complete purification engine resolves into one consciousness.','closing_seal',['seal','six paths','awareness'],'seal','six concentric path-rings and central eye','synthetic','Closing synthesis based on Tantrāloka 11',sc14),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1)
            im=purifier_ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,70); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(4*320,4*180),color=NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
        'project':'Tantrāloka — Śodhya–Śodhaka: The Six-Path Purification Engine',
        'source_basis':'Tantrāloka Chapter 11, especially the distinction between denoted/purified and denotator/purifier paths and verses 83–85 on purification of cognition, subject, object, and means of knowledge.',
        'source_critical_note':'Direct claims, derived explanatory diagrams, and synthetic visual inferences are marked separately.',
        'style':{'family':'mercury-mirror purification architecture','background':'obsidian-lapis field','ink':'silver and gold','accent':'lapis, rose, teal, saffron, copper','materials':['mercury mirrors','script-thread','transparent membranes','semantic chains','six-path rings']},
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[{'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'source_status':sc.source_status,'textual_anchor':sc.textual_anchor,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'} for sc in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'architecture':['ss01','ss02','ss03','ss04','ss05'],'fourfold_purification':['ss06','ss07','ss08','ss09'],'modes_and_transmission':['ss10','ss11','ss12'],'resolution':['ss13','ss14']},'reusability_notes':{'ss01':'Use for six-path purification overviews.','ss02':'Use for denotator/denoted or speech/world relationships.','ss04':'Use for mirror, dream, and reflective manifestation.','ss06':'Use for purification of cognition.','ss07':'Use for subject purification and transparent filters.','ss08':'Use for object recollection into awareness.','ss09':'Use for means-of-knowledge diagrams.','ss10':'Use for the six operational modes of purification.','ss12':'Use for guru transmission and integration of paths.','ss14':'Use as the closing purification seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Śodhya–Śodhaka

## Aim
Visualize Chapter 11's six-path purification system without reducing it to a generic cleansing metaphor.

## Core structure
- **Vācaka / śodhaka**: expressive, denotator, purifier side — varṇa, mantra, pada.
- **Vācya / śodhya**: expressed, denoted, purified side — kalā, tattva, bhuvana.
- The six paths traverse and purify **pramā**, **pramātṛ**, **prameya**, and **pramāṇa**.
- Purification is ultimately recognition that purifier and purified are functions of one consciousness.

## Six modes
A Chapter 11 rendering enumerates enjoyment, mastery, abandonment, knowing oneself as Śiva, merger, and removal. These may occur successively or non-successively.

## Visual rules
- Use mirror, dream, word/world, and threading relations.
- Do not depict purification as moral washing.
- Do not collapse operational distinctions too early.
- Final nonduality should preserve why purifier/purified distinctions were useful.

## Source-status system
- direct: closely tied to textual statement
- derived: supported interpretive visualization
- synthetic: explanatory synthesis
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    notes='''# SOURCE NOTES — Śodhya–Śodhaka Pack

## Core source frame
Tantrāloka Chapter 11 treats the paths of kalā and related structures, language, phonemic consciousness, and the purification of the six paths through cognition, subject, object, and means of knowledge.

## Important distinctions
1. The vācaka/vācya and śodhaka/śodhya polarity is doctrinally grounded.
2. The mirror and dream scenes are derived explanatory visualizations.
3. The fourfold purification scenes are anchored in Chapter 11.83–85.
4. The six-mode sequence is based on the Chapter 11 rendering available at Sanskrit-Trikashaivism.
5. The guru-thread scene is non-instructional and conceptual; it does not reconstruct initiation procedure.
6. The final identity seal is synthetic.

## Research sources
- Anuttara Trika Kula, Chapter 11 overview
- Sanskrit & Trika Shaivism, Tantrāloka Chapter 11
- Tantrasāra translation for later initiation context
'''
    (ROOT/'SOURCE_NOTES.md').write_text(notes,encoding='utf-8')
    style='''# STYLE EVOLUTION — Śodhya–Śodhaka Pack

## New visual grammar
- mercury-silver consciousness mirrors
- lapis script-thread
- gold world-membranes
- semantic transformation chains
- transparent observer filters
- six-path integration bundles

## New relationships
1. denotator → denoted
2. word ↔ world
3. mirror image ↔ awareness
4. six paths → cognition, subject, object, means
5. guru → integrated six-path field
6. purifier ↔ purified identity

## Closing seal
Six concentric path-rings fold into a central eye, showing all purification as recognition within one awareness-field.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — Śodhya–Śodhaka Pack

Included:
- shodhya_shodhaka_purification_animation.mp4
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
- {DURATION}s each
- {len(SCENES)*DURATION:.1f}s total

Render:
```bash
python render_pack.py
```
Resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'shodhya_shodhaka_purification_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'shodhya_shodhaka_purification_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['shodhya_shodhaka_purification_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','SOURCE_NOTES.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat_file=ROOT/'concat_list.txt'; concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'shodhya_shodhaka_purification_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__': render_all()
