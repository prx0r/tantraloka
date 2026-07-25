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
SEED = 131313

# Moon-rain / resonance palette
NIGHT = (20, 22, 33)
DEEP_VIOLET = (54, 49, 91)
VIOLET = (104, 92, 155)
LAVENDER = (157, 146, 196)
INDIGO = (67, 79, 133)
SLATE = (108, 119, 145)
MIST = (176, 185, 205)
SILVER = (220, 225, 236)
PEARL = (244, 242, 238)
WHITE = (252, 250, 246)
GOLD = (207, 165, 86)
GOLD_LIGHT = (245, 214, 138)
ROSE = (192, 113, 145)
CRIMSON = (155, 55, 78)
TEAL = (91, 147, 151)
SEA = (88, 126, 153)
GREEN = (110, 153, 112)
AMBER = (224, 139, 62)
BLACK = (15, 16, 20)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)


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


def ground(seed: int):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0,1,(42,76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(17))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*20,0,27)
    base -= vign[...,None]
    top = np.exp(-(((xx-W/2)/(W*0.29))**2 + ((yy-H*0.10)/(H*0.12))**2)*2.3)
    low = np.exp(-(((xx-W/2)/(W*0.35))**2 + ((yy-H*0.58)/(H*0.26))**2)*2.8)
    for i in range(3):
        base[...,i] += top * (28 if i == 2 else 14)
        base[...,i] += low * (14 if i == 2 else 5)
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
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42), fill=rgba(outer,145), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(MIST,112), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,88), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,VIOLET,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((88,y0,W-88,H-34), radius=14, fill=(18,20,30,202), outline=rgba(MIST,66), width=1)
    d.text((120,y0+18), title, font=TITLE_FONT, fill=PEARL)
    d.text((122,y0+58), subtitle, font=SUB_FONT, fill=MIST)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-116-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)


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
    draw.polygon([p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)], fill=rgba(color,230))


def dust(im,seed,n=74):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(100,W-100)); y=float(rng.uniform(90,H-170)); r=float(rng.uniform(.8,2.4))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(24,82))))
    im.alpha_composite(ov)


def draw_receiver(draw,x,y,r,col,fill_alpha=70,open_fraction=1.0):
    # cup/aperture metaphor
    draw.arc((x-r,y-r*.75,x+r,y+r*.75), 5, 175, fill=rgba(col,215), width=3)
    draw.arc((x-r,y-r*.75,x+r,y+r*.75), 185, 355, fill=rgba(mix(col,NIGHT,.45),130), width=2)
    if open_fraction > 0:
        draw.ellipse((x-r*.28,y-r*.18,x+r*.28,y+r*.18), fill=rgba(col,int(150*open_fraction)))


def draw_rain(im,x0,x1,y0,y1,count,col,progress,seed=0):
    rng=np.random.default_rng(seed)
    for i in range(count):
        x=float(rng.uniform(x0,x1)); delay=float(rng.uniform(0,.35)); p=clamp((progress-delay)/(1-delay))
        yy=lerp(y0,y1,p); length=float(rng.uniform(18,46))
        draw_line_glow(im,[(x,yy-length),(x,yy)],col,1,65,5)


def draw_moon_eye(draw,cx,cy,scale=1.0,col=SILVER):
    draw.arc((cx-70*scale,cy-32*scale,cx+70*scale,cy+32*scale),180,360,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.arc((cx-70*scale,cy-32*scale,cx+70*scale,cy+32*scale),0,180,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.ellipse((cx-15*scale,cy-15*scale,cx+15*scale,cy+15*scale),fill=rgba(GOLD_LIGHT,220))


def draw_path_orbit(im,cx,cy,rx,ry,col,progress,phase=0):
    pts=[]
    for i in range(100):
        a=phase+i*2*math.pi/99
        pts.append((cx+math.cos(a)*rx,cy+math.sin(a)*ry))
    pts=partial_polyline(pts,progress)
    if len(pts)>1:draw_line_glow(im,pts,col,3,100,6)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]


def sc01(im,t):
    d=ImageDraw.Draw(im)
    cx=640
    draw_glow(im,(cx,102),54,SILVER,150,18)
    d.ellipse((cx-16,86,cx+16,118),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    draw_rain(im,150,1130,118,400,28,SILVER,ease_out_cubic(t),SEED+1)
    cols=[GOLD_LIGHT,GOLD,AMBER,ROSE,VIOLET,INDIGO,TEAL,SEA,SLATE]
    labels=['T-T','M-T','m-T','T-M','M-M','m-M','T-m','M-m','m-m']
    for idx in range(9):
        r=idx//3;c=idx%3
        x=350+c*290;y=220+r*105
        intensity=1-idx/10
        draw_receiver(d,x,y,36,cols[idx],70,intensity)
        d.text((x,y+48),labels[idx],font=SMALL_FONT,fill=cols[idx],anchor='mm')
    d.text((640,508),'one free descent, nine gradations of awakened response',font=SUB_FONT,fill=MIST,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im)
    # grace bypasses karma scale and mala clock
    draw_glow(im,(640,105),48,SILVER,145,16)
    d.ellipse((624,89,656,121),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    # obstructive mechanisms left/right
    d.line((250,285,450,285),fill=rgba(SLATE,150),width=3)
    d.line((350,230,350,340),fill=rgba(SLATE,150),width=3)
    d.ellipse((295,320,335,350),outline=rgba(CRIMSON,160),width=2)
    d.ellipse((365,320,405,350),outline=rgba(TEAL,160),width=2)
    d.text((350,370),'karma balance',font=SMALL_FONT,fill=SLATE,anchor='mm')
    for r in [42,72,102]:
        d.arc((930-r,285-r,930+r,285+r),0,330,fill=rgba(VIOLET,120),width=2)
    d.text((930,370),'mala ripening',font=SMALL_FONT,fill=SLATE,anchor='mm')
    # direct ray bypassing both
    pts=partial_polyline(bezier((640,130),(630,210),(650,300),(640,430),100),smoothstep(.02,.82,t))
    if len(pts)>1:
        draw_line_glow(im,pts,GOLD_LIGHT,5,145,9);draw_arrowhead(d,pts[-2],pts[-1],GOLD_LIGHT,1.1)
    draw_receiver(d,640,445,44,GOLD_LIGHT,80,1)
    d.text((640,508),'grace is not mechanically produced by karma, merit, or impurity',font=SUB_FONT,fill=MIST,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im);cx,cy=640,285
    # instant source-receiver identity
    draw_glow(im,(cx,100),46,SILVER,145,15)
    d.ellipse((624,84,656,116),fill=rgba(WHITE,255),outline=rgba(SILVER,220),width=2)
    pts=partial_polyline(bezier((cx,122),(cx-30,180),(cx+20,230),(cx,270),80),smoothstep(.02,.55,t))
    if len(pts)>1:draw_line_glow(im,pts,WHITE,7,175,12)
    draw_glow(im,(cx,cy),int(38+80*ease_out_cubic(t)),GOLD_LIGHT,170,24)
    d.ellipse((cx-25,cy-25,cx+25,cy+25),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,230),width=2)
    for i in range(16):
        a=i*2*math.pi/16
        draw_line_glow(im,[(cx+math.cos(a)*48,cy+math.sin(a)*48),(cx+math.cos(a)*185,cy+math.sin(a)*120)],GOLD_LIGHT,2,75,5)
    d.text((640,508),'the strongest descent discloses Śiva-nature without interval',font=SUB_FONT,fill=MIST,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im);cx,cy=640,280
    # intuition moon and corroborating scripture orbit
    draw_glow(im,(cx,cy),74,SILVER,115,20)
    draw_moon_eye(d,cx,cy,1.0,SILVER)
    d.text((cx,205),'pratibhā',font=TERM_FONT,fill=LAVENDER,anchor='mm')
    draw_path_orbit(im,cx,cy,205,120,VIOLET,smoothstep(.05,.85,t),phase=.2)
    for i,lab in enumerate(['śāstra','guru','svasaṃskāra']):
        a=-math.pi/2+i*2*math.pi/3+.2
        x=cx+math.cos(a)*205;y=cy+math.sin(a)*120
        d.rounded_rectangle((x-55,y-20,x+55,y+20),radius=10,outline=rgba(VIOLET,170),fill=rgba(DEEP_VIOLET,75),width=2)
        d.text((x,y),lab,font=SMALL_FONT,fill=PEARL,anchor='mm')
    d.text((640,508),'intuition may be self-luminous yet seek confirmation and refinement',font=SUB_FONT,fill=MIST,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im)
    # longing finds the true guru via compass
    cx,cy=430,285
    draw_receiver(d,cx,cy,44,ROSE,70,.72)
    d.text((cx,360),'longing for truth',font=SMALL_FONT,fill=ROSE,anchor='mm')
    # compass / path to teacher
    for r in [42,72]:d.ellipse((820-r,cy-r,820+r,cy+r),outline=rgba(GOLD,130),width=2)
    d.line((820,200,820,370),fill=rgba(GOLD,120),width=2);d.line((735,285,905,285),fill=rgba(GOLD,120),width=2)
    d.polygon([(820,218),(806,264),(834,264)],fill=rgba(GOLD_LIGHT,220))
    d.text((820,390),'sadguru',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    pts=partial_polyline(bezier((cx+48,cy),(560,220),(690,330),(748,285),100),smoothstep(.05,.88,t))
    if len(pts)>1:
        draw_line_glow(im,pts,mix(ROSE,GOLD,.55),4,120,7);draw_arrowhead(d,pts[-2],pts[-1],GOLD_LIGHT,1)
    d.text((640,508),'reduced intense grace awakens the desire to find a true teacher',font=SUB_FONT,fill=MIST,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im)
    # realization ripens across body threshold
    cx=640
    d.rounded_rectangle((330,190,590,375),radius=28,outline=rgba(INDIGO,170),fill=rgba(DEEP_VIOLET,55),width=2)
    d.rounded_rectangle((690,190,950,375),radius=28,outline=rgba(GOLD,170),fill=rgba(GOLD,32),width=2)
    d.text((460,225),'embodied',font=TERM_FONT,fill=INDIGO,anchor='mm')
    d.text((820,225),'ripened',font=TERM_FONT,fill=GOLD,anchor='mm')
    for i in range(7):
        a=i*2*math.pi/7
        x=460+math.cos(a)*70;y=300+math.sin(a)*44
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(INDIGO,170))
    draw_glow(im,(820,300),54,GOLD_LIGHT,115,16)
    d.ellipse((802,282,838,318),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    pts=partial_polyline(bezier((590,285),(630,240),(650,330),(690,285),80),smoothstep(.08,.9,t))
    if len(pts)>1:draw_line_glow(im,pts,mix(INDIGO,GOLD,.5),4,120,7)
    d.line((640,170,640,405),fill=rgba(SILVER,80),width=1)
    d.text((640,508),'intense-medium grace ripens realization through the body’s remaining span',font=SUB_FONT,fill=MIST,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im)
    # liberation current and enjoyment current braided
    pts1=[];pts2=[]
    for i in range(100):
        u=i/99;x=220+u*840
        pts1.append((x,270+math.sin(u*4*math.pi)*38))
        pts2.append((x,330-math.sin(u*4*math.pi)*38))
    p1=partial_polyline(pts1,smoothstep(.02,.85,t));p2=partial_polyline(pts2,smoothstep(.02,.85,t))
    if len(p1)>1:draw_line_glow(im,p1,GOLD,4,115,7)
    if len(p2)>1:draw_line_glow(im,p2,ROSE,4,105,7)
    d.text((230,220),'liberation',font=TERM_FONT,fill=GOLD)
    d.text((230,382),'enjoyment',font=TERM_FONT,fill=ROSE)
    draw_glow(im,(1060,300),42,GOLD_LIGHT,115,14)
    d.ellipse((1044,284,1076,316),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,508),'medium-medium grace permits enjoyment while the liberating current matures',font=SUB_FONT,fill=MIST,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im)
    # delayed maturation across two vessels / lives
    vessels=[(390,285,INDIGO,'first embodiment'),(890,285,GOLD,'later fruition')]
    for x,y,col,lab in vessels:
        d.arc((x-75,y-65,x+75,y+65),0,180,fill=rgba(col,190),width=3)
        d.line((x-75,y,x-50,y+85,x+50,y+85,x+75,y),fill=rgba(col,150),width=2)
        d.text((x,y+118),lab,font=SMALL_FONT,fill=col,anchor='mm')
    beads=[]
    for i in range(9):
        u=i/8;x=470+u*340;y=260+math.sin(u*math.pi)*-65
        beads.append((x,y))
    for i,(x,y) in enumerate(beads):
        s=smoothstep(.06+i*.06,.7+i*.035,t)
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(INDIGO,GOLD,i/8),int(210*s)))
    draw_line_glow(im,beads,mix(INDIGO,GOLD,.5),2,75,5)
    d.text((640,508),'reduced medium grace unfolds through delayed ripening and another embodiment',font=SUB_FONT,fill=MIST,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im)
    # upper gentle: powers/enjoyment dominate but ascent remains
    cx,cy=640,300
    for i in range(8):
        a=i*2*math.pi/8+t*.1
        x=cx+math.cos(a)*195;y=cy+math.sin(a)*110
        col=mix(AMBER,VIOLET,i/8)
        d.ellipse((x-12,y-12,x+12,y+12),outline=rgba(col,190),fill=rgba(col,55),width=2)
    pts=partial_polyline(bezier((cx,cy),(cx+20,240),(cx-10,180),(cx,118),80),smoothstep(.1,.95,t))
    if len(pts)>1:
        draw_line_glow(im,pts,GOLD_LIGHT,4,110,7);draw_arrowhead(d,pts[-2],pts[-1],GOLD_LIGHT,.9)
    d.text((640,508),'intense-gentle grace remains enjoyment-oriented yet preserves an upward vector',font=SUB_FONT,fill=MIST,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im)
    # middle gentle: spiral practice orbit
    cx,cy=640,295
    pts=[]
    for i in range(150):
        u=i/149;r=28+u*220;a=u*5.5*math.pi
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.58))
    pp=partial_polyline(pts,smoothstep(.02,.92,t))
    if len(pp)>1:draw_line_glow(im,pp,VIOLET,4,105,7)
    for idx,u in enumerate([.22,.42,.62,.82]):
        p=pts[int(u*(len(pts)-1))]
        d.ellipse((p[0]-9,p[1]-9,p[0]+9,p[1]+9),fill=rgba(mix(ROSE,GOLD,u),180))
    draw_glow(im,(cx,cy),28,GOLD_LIGHT,105,10)
    d.text((640,508),'medium-gentle grace advances through repeated practice, enjoyment, and refinement',font=SUB_FONT,fill=MIST,anchor='mm')


def sc11(im,t):
    d=ImageDraw.Draw(im)
    # gentle-gentle: long labyrinth with upward thread
    x0,y0=230,170;x1,y1=1050,420
    d.rounded_rectangle((x0,y0,x1,y1),radius=25,outline=rgba(SLATE,130),width=2)
    for i in range(7):
        off=i*30
        d.rounded_rectangle((x0+off,y0+off*.45,x1-off,y1-off*.45),radius=18,outline=rgba(mix(SLATE,VIOLET,i/7),95),width=2)
    pts=[(270,380),(330,210),(450,360),(570,230),(700,350),(835,220),(1000,315)]
    pp=partial_polyline(bezier(pts[0],pts[2],pts[4],pts[6],130),smoothstep(.04,.94,t))
    if len(pp)>1:
        draw_line_glow(im,pp,GOLD_LIGHT,3,95,7);draw_arrowhead(d,pp[-2],pp[-1],GOLD_LIGHT,.8)
    d.text((640,508),'gentle-gentle grace moves through the longest circuit, but still culminates in Śiva',font=SUB_FONT,fill=MIST,anchor='mm')


def sc12(im,t):
    d=ImageDraw.Draw(im)
    # pratibha and modes of transmission
    cx,cy=640,270
    draw_glow(im,(cx,cy),62,SILVER,115,18);draw_moon_eye(d,cx,cy,.85,SILVER)
    modes=[('glance',GOLD),('discourse',TEAL),('scripture',INDIGO),('conduct',GREEN),('offering',ROSE),('mantra/mudrā',VIOLET)]
    for i,(lab,col) in enumerate(modes):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*235;y=cy+math.sin(a)*145
        d.rounded_rectangle((x-62,y-20,x+62,y+20),radius=10,outline=rgba(col,170),fill=rgba(mix(NIGHT,col,.12),70),width=2)
        d.text((x,y),lab,font=SMALL_FONT,fill=PEARL,anchor='mm')
        pts=partial_polyline(bezier((cx,cy),(cx+math.cos(a)*70,cy+math.sin(a)*45),(x-20*math.cos(a),y-14*math.sin(a)),(x,y),70),smoothstep(.05+i*.04,.78+i*.025,t))
        if len(pts)>1:draw_line_glow(im,pts,col,2,78,5)
    d.text((640,508),'intuition and the true guru transmit insight through many forms, not ritual alone',font=SUB_FONT,fill=MIST,anchor='mm')


def sc13(im,t):
    d=ImageDraw.Draw(im);cx,cy=640,290
    # nine-cup seal around moon-eye
    for r,col in [(230,VIOLET),(175,SILVER),(112,GOLD)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(col,120),width=2)
    cols=[GOLD_LIGHT,GOLD,AMBER,ROSE,VIOLET,INDIGO,TEAL,SEA,SLATE]
    for i,col in enumerate(cols):
        a=-math.pi/2+i*2*math.pi/9+t*.04
        x=cx+math.cos(a)*190;y=cy+math.sin(a)*132
        draw_receiver(d,x,y,20,col,60,1-i*.07)
        draw_line_glow(im,[(cx,cy),(x,y)],col,1,52,4)
    draw_glow(im,(cx,cy),58,SILVER,130,18);draw_moon_eye(d,cx,cy,.72,SILVER)
    draw_rain(im,500,780,90,210,12,GOLD_LIGHT,ease_out_cubic(t),SEED+17)
    d.text((640,508),'the ninefold spectrum resolves into one free field of grace and recognition',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('sp01','The Ninefold Spectrum','One free descent awakens nine degrees of response.','Śaktipāta','The spectrum is intensity of awakened insight, not moral worth.','ninefold_overview',['overview','ninefold','grace'],'overview','rain field and receiver grid',sc01),
Scene('sp02','Grace Is Free','Śiva’s descent is not mechanically caused by karma or impurity.','Svātantrya','Grace expresses divine freedom rather than a karmic trigger.','freedom_bypass',['freedom','karma','mala'],'principle','direct ray bypassing mechanisms',sc02),
Scene('sp03','Tīvra–Tīvra','The strongest descent reveals identity without interval.','Tīvra-tīvra','Receiver and source become indistinguishable immediately.','instant_identity',['intense','immediate','liberation'],'grade','instant source merge',sc03),
Scene('sp04','Madhya–Tīvra','Spontaneous intuition shines, with possible corroboration and refinement.','Madhya-tīvra','Pratibhā is strong and inwardly authoritative.','intuition_orbit',['intuition','scripture','refinement'],'grade','moon eye and corroboration orbit',sc04),
Scene('sp05','Manda–Tīvra','The awakened longing for truth finds the true guru.','Manda-tīvra','Grace manifests as the irreversible desire for authentic guidance.','guru_compass',['guru','longing','guidance'],'grade','receiver-to-compass path',sc05),
Scene('sp06','Tīvra–Madhya','Realization ripens through the remaining embodied span.','Tīvra-madhya','Insight is real but reaches final firmness at the body’s end.','embodied_ripening',['medium','ripening','body'],'grade','two-chamber threshold',sc06),
Scene('sp07','Madhya–Madhya','Liberation and enjoyment move as braided currents.','Madhya-madhya','Desire for Śiva and desire for experience coexist during maturation.','braided_currents',['enjoyment','liberation','braid'],'grade','dual current braid',sc07),
Scene('sp08','Manda–Madhya','Grace ripens through delayed fruition and another embodiment.','Manda-madhya','Liberation follows after a longer arc of experience.','delayed_fruition',['delay','embodiment','fruition'],'grade','two vessels and bead bridge',sc08),
Scene('sp09','Tīvra–Manda','Enjoyment predominates, yet an upward vector remains.','Tīvra-manda','Gentle grace still carries the seed of liberation.','upper_gentle',['gentle','enjoyment','ascent'],'grade','orbit with vertical thread',sc09),
Scene('sp10','Madhya–Manda','Repeated practice gradually refines the receiver.','Madhya-manda','The route winds through enjoyment, practice, and maturation.','spiral_refinement',['practice','spiral','maturation'],'grade','spiral route',sc10),
Scene('sp11','Manda–Manda','The longest circuit nevertheless culminates in Śiva.','Manda-manda','Even the gentlest descent remains ultimately liberating in this system.','long_labyrinth',['long path','gentle','culmination'],'grade','labyrinth with gold thread',sc11),
Scene('sp12','Pratibhā and the True Guru','Insight may arrive through glance, word, scripture, conduct, offering, or mantra.','Pratibhā','Living wisdom, not status alone, marks the liberating teacher.','transmission_modes',['intuition','guru','transmission'],'transmission','moon eye and six rays',sc12),
Scene('sp13','The Śaktipāta Seal','Nine receivers gather around one moon-like eye of grace.','Śaktipāta-cakra','The spectrum resolves into one free descent of consciousness.','closing_seal',['seal','ninefold','grace'],'seal','nine cups around moon eye',sc13),
]


def render_scene(scene):
    sdir=FRAMES_ROOT/scene.id;sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000:continue
            t=i/max(1,NFRAMES-1);im=ground(SEED+hash(scene.id)%10000+i);border(im);dust(im,SEED+i,64);scene.draw_fn(im,t);footer(im,scene.title,scene.subtitle,scene.term);im.convert('RGB').save(path,quality=94)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg';thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    cols,rows=4,4;sheet=Image.new('RGB',(cols*320,rows*180),color=NIGHT)
    for idx,im in enumerate(thumbs):sheet.paste(im,((idx%cols)*320,(idx//cols)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={'project':'Tantrāloka — Śaktipāta: The Spectrum of Grace','source_basis':'Tantrāloka Chapter 13, especially the ninefold śaktipāta structure attributed to Śambhunātha, the independence of grace from karma and mala, pratibhā, and the true guru.','style':{'family':'moon-rain resonance cosmography','background':'obsidian violet field','ink':'silver and mist','accent':'pearl, gold, violet, rose, teal','materials':['moon-silver rain','pearl receiver cups','violet resonance glass','gold self-illumination','transmission rays']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),'scenes':[{'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'} for sc in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[sc.id for sc in SCENES],'titles':{sc.id:sc.title for sc in SCENES},'modes':{sc.id:sc.mode for sc in SCENES},'theme_clusters':{'overview_and_principle':['sp01','sp02'],'intense_grades':['sp03','sp04','sp05'],'medium_grades':['sp06','sp07','sp08'],'gentle_grades':['sp09','sp10','sp11'],'transmission_and_seal':['sp12','sp13']},'reusability_notes':{'sp01':'Use for ninefold grace, intensity spectra, or differential awakening.','sp02':'Use for divine freedom, grace independent of karma, or non-mechanical causation.','sp03':'Use for immediate realization or discontinuous awakening.','sp04':'Use for pratibhā, intuition, inner certainty, or corroboration.','sp05':'Use for longing for truth and finding an authentic teacher.','sp07':'Use where liberation and enjoyment coexist as braided motives.','sp12':'Use for guru transmission through multiple non-ritual modes.','sp13':'Use as the closing śaktipāta cosmogram.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Śaktipāta

## Aim
This pack visualizes Chapter 13's doctrine of the descent of Śiva's power of grace and its ninefold gradation.

## Source-supported structure
- Śiva's grace is free and is not mechanically caused by a balance of karma or a ripening of impurity.
- The chapter presents a **ninefold śaktipāta**, organized as intense, medium, and gentle, each with three internal gradations.
- The stronger forms awaken immediate realization or spontaneous intuition; reduced intense grace may awaken the desire to approach a true guru.
- Medium forms ripen through the remaining body, enjoyment, or a later embodiment.
- Gentle forms remain strongly oriented to enjoyment, but still ultimately culminate in liberation within this Śaiva framework.
- **Pratibhā**, intuitive insight, is central; a true teacher is distinguished by liberating knowledge put into practice.

## Nine gradations visualized
1. Tīvra–tīvra
2. Madhya–tīvra
3. Manda–tīvra
4. Tīvra–madhya
5. Madhya–madhya
6. Manda–madhya
7. Tīvra–manda
8. Madhya–manda
9. Manda–manda

## Creative visualization note
The receiver-cup and resonance metaphors are artistic devices. They do not imply that grace is earned by merit or that people possess fixed spiritual worth. They visualize variation in awakened insight and maturation.

## Visual rules
- Grace descends softly and freely, more like moon-rain than violent lightning.
- Never portray the ninefold sequence as moral superiority.
- Stronger grades should reduce mediation and delay.
- Medium grades should show ripening, coexistence of motives, or embodiment.
- Gentle grades should show longer temporal circuits without denying the final upward vector.
- Pratibhā and guru transmission need their own grammar distinct from the intensity grid.

## New motifs
- nine receiver cups
- moon-silver rain field
- karmic mechanism bypass
- instant source-receiver merge
- pratibhā moon-eye
- guru compass
- braided liberation/enjoyment streams
- two-vessel delayed fruition
- long labyrinth with a gold thread
- six modes of transmission
- nine-cup closing seal

## Guardrails
- Do not describe grace as a reward for good karma.
- Do not equate powerful experiences with spiritual authority.
- Do not reduce the guru to charisma; the chapter stresses effective liberating insight.
- Keep effects of each grade clearly marked as a simplified visual synthesis.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Śaktipāta Pack

## Differentiation
This pack leaves behind shell, ladder, and breath-axis imagery and develops a soft but potent language of free descent and differential resonance.

## New symbols
1. moon-silver rain
2. receiver cups / apertures
3. karma-scale bypass
4. source-receiver identity flare
5. pratibhā moon-eye
6. guru compass
7. braided liberation and enjoyment currents
8. embodiment vessels
9. spiral refinement route
10. gold-thread labyrinth
11. six transmission rays
12. nine-cup seal

## New relationships
- divine freedom → grace independent of karma
- intensity → degree of mediation and delay
- intuition → corroboration / self-refinement
- awakened longing → authentic guidance
- enjoyment + liberation → braided maturation
- teacher knowledge → multiple transmission modes

## Material vocabulary
- moon-silver rain
- pearl apertures
- violet resonance glass
- gold self-illumination
- rose longing-thread
- translucent transmission rays

## Distinct closing seal
Nine receiver cups orbit a moon-eye while one gold-silver rain field descends through the whole structure.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — Śaktipāta: The Spectrum of Grace

Included:
- shaktipata_grace_spectrum_animation.mp4
- contact_sheet.jpg
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- STYLE_EVOLUTION.md
- render_pack.py
- validation.json
- scenes/*.mp4

Specs: {W}x{H}, {FPS} fps, {len(SCENES)} scenes, {DURATION}s per scene, {len(SCENES)*DURATION:.1f}s total.

Run: `python render_pack.py`
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')


def validate_outputs():
    combined=ROOT/'shaktipata_grace_spectrum_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))


def make_zip():
    zpath=ROOT/'shaktipata_grace_spectrum_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['shaktipata_grace_spectrum_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True);SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True);render_scene(sc)
    concat=ROOT/'concat_list.txt';concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'shaktipata_grace_spectrum_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet();write_metadata();validate_outputs();make_zip()

if __name__=='__main__':render_all()
