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
SEED = 22408

# Cosmic atlas palette
NIGHT = (13, 18, 31)
OBSIDIAN = (22, 27, 43)
DEEP_LAPIS = (34, 48, 91)
LAPIS = (61, 83, 145)
INDIGO = (79, 89, 145)
VIOLET = (132, 102, 164)
TEAL = (78, 139, 145)
SEA = (83, 124, 150)
COPPER = (186, 105, 61)
EMBER = (230, 105, 49)
GOLD = (202, 158, 76)
GOLD_LIGHT = (242, 208, 126)
NACRE = (221, 226, 231)
IVORY = (242, 238, 226)
WHITE = (251, 248, 239)
ASH = (160, 168, 184)
SLATE = (91, 102, 125)
EARTH = (120, 91, 63)
GREEN = (89, 137, 104)
CRIMSON = (147, 43, 58)
ROSE = (186, 98, 129)
BLACK = (8, 9, 13)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 30)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 17)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 21)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 14)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)
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


def cosmic_ground(seed: int):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(NIGHT, dtype=np.float32)
    coarse = rng.normal(0,1,(45,80)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.2 + fine[...,None]*1.05
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*18,0,27)
    base -= vign[...,None]
    # vertical aurora axis
    axis = np.exp(-((xx-W/2)/(W*0.18))**2) * np.exp(-((yy-H*0.38)/(H*0.42))**2)
    for i in range(3):
        base[...,i] += axis * (9 if i<2 else 22)
    lower = np.exp(-(((xx-W/2)/(W*0.28))**2 + ((yy-H*0.66)/(H*0.18))**2)*2.6)
    base[...,0] += lower*16; base[...,1] += lower*7; base[...,2] += lower*2
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W,H), (0,0,0,0))


def draw_glow(im, xy, radius, color, alpha=150, blur=18):
    gl=layer(); d=ImageDraw.Draw(gl)
    x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius), fill=rgba(color,alpha))
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im, pts, color, width=3, alpha=150, blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color,alpha), width=max(1,width*3), joint='curve')
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color,min(255,alpha+75)), width=width, joint='curve')


def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8
        x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42), fill=rgba(outer,145), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(ASH,115), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,95), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,LAPIS,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(15,19,31,208), outline=rgba(ASH,70), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=IVORY)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=ASH)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24), term, font=TERM_FONT, fill=GOLD_LIGHT)


def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
        y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
        pts.append((x,y))
    return pts


def partial_polyline(points, amount):
    amount=clamp(amount)
    if amount<=0: return []
    if amount>=1: return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx
    out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]
        out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out


def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    pts=[p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)]
    draw.polygon(pts, fill=rgba(color,230))


def dust(im,seed,n=95):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(115,W-115)); y=float(rng.uniform(100,H-180)); r=float(rng.uniform(.8,2.2))
        c=mix(ASH,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r), fill=rgba(c,int(rng.uniform(20,82))))
    im.alpha_composite(ov)


def ring_nodes(draw,cx,cy,rx,ry,n,col,phase=0.0,r=5,labels=None,font=None):
    pts=[]
    for i in range(n):
        a=-math.pi/2+phase+i*2*math.pi/n
        x=cx+math.cos(a)*rx; y=cy+math.sin(a)*ry
        pts.append((x,y))
        draw.ellipse((x-r,y-r,x+r,y+r), fill=rgba(col,205), outline=rgba(WHITE,90))
        if labels and i<len(labels):
            draw.text((x,y+18), labels[i], font=font or TINY_FONT, fill=ASH, anchor='mm')
    return pts


def draw_shell(draw,cx,cy,rx,ry,col,width=2,fill_alpha=18):
    draw.ellipse((cx-rx,cy-ry,cx+rx,cy+ry), outline=rgba(col,175), fill=rgba(col,fill_alpha), width=width)


def draw_flame(draw,cx,cy,scale=1.0,col=EMBER):
    pts=[(cx,cy-70*scale),(cx-26*scale,cy-8*scale),(cx-8*scale,cy+38*scale),(cx+4*scale,cy+8*scale),(cx+22*scale,cy+50*scale),(cx+42*scale,cy-6*scale)]
    draw.polygon(pts, outline=rgba(col,220), fill=rgba(mix(col,GOLD_LIGHT,.35),65))


def draw_lord_icon(draw,cx,cy,col,kind=0,scale=1.0):
    r=18*scale
    draw.ellipse((cx-r,cy-r,cx+r,cy+r), outline=rgba(col,210), fill=rgba(mix(OBSIDIAN,col,.12),100), width=max(1,int(2*scale)))
    if kind%3==0:
        draw.line((cx,cy-r*.65,cx,cy+r*.65), fill=rgba(col,220), width=max(1,int(2*scale)))
        draw.line((cx-r*.5,cy,cx+r*.5,cy), fill=rgba(col,220), width=max(1,int(2*scale)))
    elif kind%3==1:
        draw.arc((cx-r*.6,cy-r*.6,cx+r*.6,cy+r*.6), 20, 320, fill=rgba(col,220), width=max(1,int(2*scale)))
    else:
        draw.polygon([(cx,cy-r*.7),(cx-r*.6,cy+r*.45),(cx+r*.6,cy+r*.45)], outline=rgba(col,220))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; source_status:str; textual_anchor:str; draw_fn:Callable[[Image.Image,float],None]

# ---------- scene functions ----------

def sc01(im,t):
    d=ImageDraw.Draw(im); cx=W/2
    draw_glow(im,(cx,100),42,GOLD_LIGHT,120,14)
    d.ellipse((cx-13,87,cx+13,113), fill=rgba(WHITE,255), outline=rgba(GOLD,220), width=2)
    d.text((cx,62),'ŚIVA',font=TERM_FONT,fill=GOLD_LIGHT,anchor='mm')
    # 36-level ladder, 224 schematic lights
    ys=np.linspace(135,480,36)
    rng=np.random.default_rng(224)
    for i,y in enumerate(ys):
        width=lerp(90,420,i/35)
        x0=cx-width/2; x1=cx+width/2
        d.line((x0,y,x1,y), fill=rgba(mix(GOLD,LAPIS,i/35),80), width=1)
        count=2+(i%7)
        for j in range(count):
            x=lerp(x0+8,x1-8,(j+1)/(count+1))
            d.ellipse((x-3,y-3,x+3,y+3), fill=rgba(mix(GOLD_LIGHT,COPPER,i/35),175))
    draw_flame(d,cx,505,.45,EMBER)
    d.text((cx,546),'KĀLĀGNI',font=TERM_FONT,fill=EMBER,anchor='mm')
    d.text((1040,164),'224 worlds',font=TERM_FONT,fill=IVORY)
    d.text((1040,196),'across 36 tattvas',font=SMALL_FONT,fill=ASH)


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,300
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12
        x=cx+math.cos(a)*190; y=cy+math.sin(a)*120
        draw_flame(d,x,y,.27,mix(EMBER,GOLD_LIGHT,i/12))
        draw_line_glow(im,[(x,y),(cx,cy)],EMBER,2,70,5)
    draw_glow(im,(cx,cy),80,EMBER,145,24)
    d.ellipse((cx-30,cy-30,cx+30,cy+30), fill=rgba(BLACK,255), outline=rgba(EMBER,225), width=3)
    d.text((cx,cy),'काल',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,510),'the lowest limit of the mapped cosmos burns as the Fire of Time',font=SUB_FONT,fill=ASH,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im); cx=W/2
    strata=[(165,CRIMSON,'Naraka'),(230,COPPER,'Tāmisra'),(300,EMBER,'Raurava'),(375,SLATE,'Lower strata'),(445,BLACK,'Limit')]
    for i,(y,col,lab) in enumerate(strata):
        w=lerp(600,280,i/4)
        d.rounded_rectangle((cx-w/2,y-24,cx+w/2,y+24),radius=18,outline=rgba(col,185),fill=rgba(mix(OBSIDIAN,col,.08),85),width=2)
        d.text((cx,y),lab,font=SMALL_FONT,fill=col if col!=BLACK else ASH,anchor='mm')
        if i<len(strata)-1:
            draw_line_glow(im,[(cx,y+25),(cx,strata[i+1][0]-25)],mix(col,strata[i+1][1],.5),2,75,5)
    d.text((640,510),'hells are visualized as descending experiential strata within the earth-sphere',font=SUB_FONT,fill=ASH,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,292
    for i in range(7):
        r=48+i*28
        a0=-math.pi/2+i*.35+t*.05
        pts=[]
        for j in range(120):
            u=j/119; a=a0+u*math.pi*1.65
            x=cx+math.cos(a)*r*1.2; y=cy+math.sin(a)*r*.72
            pts.append((x,y))
        draw_line_glow(im,pts,mix(TEAL,LAPIS,i/7),3,90,6)
    draw_glow(im,(cx,cy),45,COPPER,100,12)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(EARTH,220),outline=rgba(GOLD,180),width=2)
    d.text((cx,cy),'हाटक',font=DEVA_SMALL,fill=IVORY,anchor='mm')
    d.text((640,510),'the netherworlds coil around Hāṭaka and the hidden foundations of earth',font=SUB_FONT,fill=ASH,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,292
    draw_shell(d,cx,cy,250,165,COPPER,3,28)
    draw_shell(d,cx,cy,188,120,GOLD,2,22)
    d.arc((cx-250,cy-165,cx+250,cy+165),180,360,fill=rgba(COPPER,220),width=5)
    draw_flame(d,cx,cy+140,.5,EMBER)
    for i,lab in enumerate(['Earth','Sky','Brahmā']):
        y=cy+70-i*68
        d.rounded_rectangle((cx-110,y-19,cx+110,y+19),radius=14,outline=rgba(mix(EARTH,GOLD,i/2),180),fill=rgba(OBSIDIAN,80),width=2)
        d.text((cx,y),lab,font=SMALL_FONT,fill=IVORY,anchor='mm')
    d.text((640,510),'the terrestrial cauldron holds earth, heaven, and the ascent toward Brahmā',font=SUB_FONT,fill=ASH,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    draw_shell(d,cx,cy,310,205,NACRE,3,20)
    layers=[('Kālāgni',cy+160,EMBER),('Naraka',cy+105,CRIMSON),('Pātāla',cy+50,TEAL),('Earth',cy-5,EARTH),('Heaven',cy-60,LAPIS),('Brahmā',cy-120,GOLD)]
    for lab,y,col in layers:
        d.rounded_rectangle((cx-140,y-16,cx+140,y+16),radius=12,outline=rgba(col,180),fill=rgba(mix(OBSIDIAN,col,.08),76),width=2)
        d.text((cx,y),lab,font=SMALL_FONT,fill=col,anchor='mm')
    d.text((1000,160),'Brahmāṇḍa',font=TERM_FONT,fill=NACRE)
    d.text((1000,192),'earth principle',font=SMALL_FONT,fill=ASH)
    d.text((640,510),'the Egg of Brahmā is a complete vertical world-system inside Pṛthivī',font=SUB_FONT,fill=ASH,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im)
    # 10x10 guardian grid around central egg
    x0,y0=170,118; cell=34
    for r in range(10):
        for c in range(10):
            x=x0+c*cell; y=y0+r*cell
            col=mix(COPPER,GOLD_LIGHT,(r+c)/18)
            draw_lord_icon(d,x,y,col,(r+c)%3,.42)
    cx,cy=890,285
    draw_shell(d,cx,cy,160,112,NACRE,2,18)
    d.text((cx,cy),'Brahmāṇḍa',font=TERM_FONT,fill=NACRE,anchor='mm')
    d.text((640,510),'ten guardians in ten directions form the Hundred Rudras beyond Brahmā’s egg',font=SUB_FONT,fill=ASH,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,292
    labels=['Kālāgni','Kuṣmāṇḍa','Hāṭaka','Earth-cauldron','Brahmā','Muni','Lokeśa','Rudras','Kapālin','Agni','Yama','Nirṛti','Bala','Īśvara','Śambhu','Vīrabhadra']
    for i,lab in enumerate(labels):
        a=-math.pi/2+i*2*math.pi/16+t*.03
        r=210 if i%2==0 else 165
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
        col=mix(EMBER,GOLD_LIGHT,i/15)
        d.ellipse((x-10,y-10,x+10,y+10),fill=rgba(col,190),outline=rgba(WHITE,80))
        if i%2==0:
            d.text((x,y+21),lab,font=TINY_FONT,fill=ASH,anchor='mm')
    draw_shell(d,cx,cy,235,162,COPPER,2,12)
    d.text((640,510),'Nivṛtti gathers sixteen worlds from Kālāgni to Vīrabhadra',font=SUB_FONT,fill=ASH,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im); centers=[]
    groups=['Water','Fire','Air','Ether','Ahaṃkāra','Buddhi','Prakṛti']
    cols=[TEAL,EMBER,SEA,LAPIS,VIOLET,GOLD,GREEN]
    for i,(lab,col) in enumerate(zip(groups,cols)):
        x=180+i*150; y=286+math.sin(i*.9)*42
        centers.append((x,y))
        d.ellipse((x-48,y-48,x+48,y+48),outline=rgba(col,190),fill=rgba(mix(OBSIDIAN,col,.08),78),width=2)
        ring_nodes(d,x,y,32,23,8,col,phase=t*.08+i*.15,r=3)
        d.text((x,y+66),lab,font=SMALL_FONT,fill=col,anchor='mm')
        if i<len(groups)-1:
            draw_line_glow(im,[(x+48,y),(x+102,centers[-1][1] if centers else y)],mix(col,cols[i+1],.5),2,60,4)
    d.text((640,510),'Pratiṣṭhā contains seven octads—fifty-six worlds from water through Prakṛti',font=SUB_FONT,fill=ASH,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,288
    names=['Lakulīśa','Bhārabhūti','Diṇḍi','Āṣāḍhi','Puṣkara','Nimeṣa','Prabhāsa','Sureśa']
    pts=ring_nodes(d,cx,cy,225,142,8,TEAL,phase=t*.08,r=8,labels=names,font=TINY_FONT)
    for i,p in enumerate(pts): draw_lord_icon(d,p[0],p[1],TEAL,i,.65)
    draw_glow(im,(cx,cy),45,TEAL,90,12)
    d.text((cx,cy),'jala',font=TERM_FONT,fill=WHITE,anchor='mm')
    d.text((640,510),'the water principle is governed by the octad beginning with Lakulīśa',font=SUB_FONT,fill=ASH,anchor='mm')


def sc11(im,t):
    d=ImageDraw.Draw(im); xs=[300,640,980]; labels=['Guhyāṣṭaka','Atiguhyāṣṭaka','Pavitrāṣṭaka']; subs=['Fire','Air','Ether']; cols=[EMBER,SEA,LAPIS]
    for k,(x,lab,sub,col) in enumerate(zip(xs,labels,subs,cols)):
        ring_nodes(d,x,288,88,62,8,col,phase=(1 if k%2==0 else -1)*t*.09,r=5)
        d.ellipse((x-36,252,x+36,324),outline=rgba(col,180),width=2)
        d.text((x,282),sub,font=TERM_FONT,fill=col,anchor='mm')
        d.text((x,350),lab,font=SMALL_FONT,fill=ASH,anchor='mm')
    d.text((640,510),'secret octads govern fire, air, and ether as progressively subtler world-fields',font=SUB_FONT,fill=ASH,anchor='mm')


def sc12(im,t):
    d=ImageDraw.Draw(im); xs=[300,640,980]; labels=['Ahaṃkāra','Buddhi','Prakṛti']; cols=[VIOLET,GOLD,GREEN]
    for k,(x,lab,col) in enumerate(zip(xs,labels,cols)):
        d.rounded_rectangle((x-100,190,x+100,390),radius=26,outline=rgba(col,180),fill=rgba(mix(OBSIDIAN,col,.08),72),width=2)
        ring_nodes(d,x,285,70,52,8,col,phase=t*.06*(1 if k!=1 else -1),r=5)
        d.text((x,414),lab,font=TERM_FONT,fill=col,anchor='mm')
    d.text((640,510),'the cognitive principles each host their own octad of worlds and beings',font=SUB_FONT,fill=ASH,anchor='mm')


def sc13(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    for i,(rx,ry,col) in enumerate([(260,170,GREEN),(190,122,GOLD),(120,76,VIOLET)]):
        draw_shell(d,cx,cy,rx,ry,col,2,14)
    names=['Akṛta','Kṛta','Vaibhava','Brahmā','Vaiṣṇava','Kaumāra','Auma','Śrīkaṇṭha']
    ring_nodes(d,cx,cy,215,138,8,GREEN,phase=t*.07,r=7,labels=names,font=TINY_FONT)
    d.text((cx,cy),'Prakṛtyaṇḍa',font=TERM_FONT,fill=GREEN,anchor='mm')
    d.text((640,510),'the Prakṛti egg expands beyond intellect and contains its own yogic world-octad',font=SUB_FONT,fill=ASH,anchor='mm')


def sc14(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,288
    names=['Vāma','Bhīma','Ugra','Bhava','Īśa','Ekavīra','Pracaṇḍa','Gaurī','Aja','Ananta','Ekaśiva']
    pts=ring_nodes(d,cx,cy,230,148,11,CRIMSON,phase=t*.055,r=7,labels=names,font=TINY_FONT)
    for i,p in enumerate(pts):
        draw_line_glow(im,[p,(cx,cy)],mix(CRIMSON,GOLD_LIGHT,i/10),1,55,4)
    draw_glow(im,(cx,cy),44,CRIMSON,95,12)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(CRIMSON,220),width=2)
    d.text((640,510),'Puruṣa hosts the eleven Rudra-worlds of increasingly sovereign subjectivity',font=SUB_FONT,fill=ASH,anchor='mm')


def sc15(im,t):
    d=ImageDraw.Draw(im)
    stages=[('Aśuddhavidyā',2,INDIGO),('Kāla',2,SEA),('Niyati',2,SLATE),('Kalā',3,COPPER),('Māyā',8,VIOLET)]
    x=180
    for idx,(lab,n,col) in enumerate(stages):
        y=282
        d.rounded_rectangle((x-62,205,x+62,360),radius=18,outline=rgba(col,180),fill=rgba(mix(OBSIDIAN,col,.08),76),width=2)
        ring_nodes(d,x,y,38,28,n,col,phase=t*.06+idx*.2,r=5)
        d.text((x,390),lab,font=SMALL_FONT,fill=col,anchor='mm')
        d.text((x,417),str(n),font=TERM_FONT,fill=IVORY,anchor='mm')
        x += 220
    d.text((640,510),'the constricted corridor from Puruṣa through Māyā contains twenty-eight worlds',font=SUB_FONT,fill=ASH,anchor='mm')


def sc16(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    names=['Hālāhala-rudra','Krodha','Ambikā','Aghora','Yama']
    pts=ring_nodes(d,cx,cy,220,142,5,GOLD,phase=t*.055,r=10,labels=names,font=SMALL_FONT)
    for i,p in enumerate(pts): draw_lord_icon(d,p[0],p[1],GOLD,i,.7)
    draw_glow(im,(cx,cy),50,GOLD_LIGHT,115,14)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,510),'Śuddhavidyā contains five luminous worlds at the threshold of pure manifestation',font=SUB_FONT,fill=ASH,anchor='mm')


def sc17(im,t):
    d=ImageDraw.Draw(im); left,right=390,890; cy=286
    ring_nodes(d,left,cy,150,96,8,LAPIS,phase=t*.06,r=7)
    d.text((left,cy),'Īśvara',font=TERM_FONT,fill=LAPIS,anchor='mm')
    d.text((left,430),'8 vidyā-lord worlds',font=SMALL_FONT,fill=ASH,anchor='mm')
    ring_nodes(d,right,cy,150,96,5,ROSE,phase=-t*.06,r=9)
    d.text((right,cy),'Sadāśiva',font=TERM_FONT,fill=ROSE,anchor='mm')
    d.text((right,430),'5 worlds',font=SMALL_FONT,fill=ASH,anchor='mm')
    draw_line_glow(im,[(left+150,cy),(right-150,cy)],mix(LAPIS,ROSE,.5),3,85,6)
    d.text((640,510),'pure objectivity and dominant I-consciousness retain distinct world-orders',font=SUB_FONT,fill=ASH,anchor='mm')


def sc18(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,300
    ring_nodes(d,cx,cy,215,140,18,NACRE,phase=t*.04,r=5)
    draw_shell(d,cx,cy,240,160,NACRE,2,10)
    # opening above
    draw_glow(im,(cx,110),54,WHITE,125,18)
    d.ellipse((cx-18,92,cx+18,128),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    draw_line_glow(im,[(cx,140),(cx,220)],GOLD_LIGHT,3,100,7)
    d.text((cx,75),'Śāntātītā — no worlds',font=SMALL_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,510),'Śāntā contains eighteen worlds; beyond it, world-structure gives way to Śiva',font=SUB_FONT,fill=ASH,anchor='mm')


def sc19(im,t):
    d=ImageDraw.Draw(im); cx=640
    # body silhouette
    d.ellipse((cx-26,122,cx+26,174),outline=rgba(NACRE,180),width=2)
    d.line((cx,174,cx,430),fill=rgba(NACRE,160),width=3)
    d.line((cx,220,cx-120,320),fill=rgba(NACRE,120),width=2)
    d.line((cx,220,cx+120,320),fill=rgba(NACRE,120),width=2)
    d.line((cx,430,cx-80,500),fill=rgba(NACRE,120),width=2)
    d.line((cx,430,cx+80,500),fill=rgba(NACRE,120),width=2)
    ys=np.linspace(160,455,18)
    cols=[EMBER,COPPER,TEAL,LAPIS,VIOLET,GOLD,NACRE]
    for i,y in enumerate(ys):
        col=cols[min(len(cols)-1,int(i/18*len(cols)))]
        d.ellipse((cx-6,y-6,cx+6,y+6),fill=rgba(col,205))
        if i%3==0:
            d.line((cx-6,y,cx-70-8*i,y),fill=rgba(col,65),width=1)
            d.text((cx-80-8*i,y),str(i+1),font=TINY_FONT,fill=ASH,anchor='rm')
    draw_glow(im,(cx,130),38,GOLD_LIGHT,100,12)
    d.text((900,170),'body',font=TERM_FONT,fill=NACRE)
    d.text((900,204),'vital energy',font=TERM_FONT,fill=TEAL)
    d.text((900,238),'intellect',font=TERM_FONT,fill=VIOLET)
    d.text((900,272),'great void',font=TERM_FONT,fill=GOLD_LIGHT)
    d.text((640,535),'the complete world-path may be projected into body, breath, intellect, or pure awareness',font=SUB_FONT,fill=ASH,anchor='mm')


def sc20(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    # 36 level rings and exactly 224 schematic lights
    rings=12
    for i in range(rings):
        rx=52+i*18; ry=34+i*12
        col=mix(EMBER,NACRE,i/(rings-1))
        d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=rgba(col,110),width=1)
    # distribute exactly 224 points in 14 elliptical bands
    counts=[16,18,18,18,18,18,18,18,16,16,16,14,10,10]  # sums 224
    assert sum(counts)==224
    for band,n in enumerate(counts):
        rx=58+band*16; ry=38+band*10
        col=mix(EMBER,GOLD_LIGHT,band/(len(counts)-1))
        for j in range(n):
            a=-math.pi/2+j*2*math.pi/n+t*.018*(1 if band%2==0 else -1)
            x=cx+math.cos(a)*rx; y=cy+math.sin(a)*ry
            r=2.2 if band<8 else 1.8
            d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(col,190))
    draw_glow(im,(cx,cy),42,WHITE,120,14)
    d.ellipse((cx-15,cy-15,cx+15,cy+15),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    d.text((1000,180),'224 lights',font=TERM_FONT,fill=IVORY)
    d.text((1000,210),'schematic distribution',font=SMALL_FONT,fill=ASH)
    d.text((640,535),'the many worlds remain translucent expressions within the one light of consciousness',font=SUB_FONT,fill=ASH,anchor='mm')

SCENES=[
Scene('bh01','The Path of Worlds','A complete ascent from Kālāgni through thirty-six tattvas to Śiva.','Bhuvanādhvan','Overview of the 224-world cosmographic path.','overview_ladder',['overview','224 worlds','36 tattvas'],'overview','vertical ladder with schematic lights','direct','Tantrāloka Chapter 8 overview; detailed count summarized by Dyczkowski',sc01),
Scene('bh02','Kālāgni','The all-consuming Fire of Time at the lower limit.','Kālāgni','The mapped cosmos begins at the fire of time.','fire_of_time',['kalagni','lower limit','fire'],'earth','twelve-flame wheel','direct','Tantrasāra Chapter 7/Path of Space summary',sc02),
Scene('bh03','The Hell Strata','Descending experiential worlds beneath the human plane.','Naraka','Lower worlds appear as layered experiential regions.','hell_strata',['hells','lower worlds'],'earth','descending terraces','derived','Tantrasāra summary: Kālāgni followed by hells',sc03),
Scene('bh04','The Netherworld Coils','Pātāla and Hāṭaka as hidden foundations beneath earth.','Pātāla / Hāṭaka','Netherworlds coil around the concealed foundations of the earth-sphere.','nether_coils',['patala','hataka'],'earth','spiral coils around hidden node','derived','Tantrasāra Path of Space summary',sc04),
Scene('bh05','The Earth Cauldron','Earth, heaven, and Brahmā held within one gross enclosure.','Pṛthivī','The gross terrestrial field functions as a complete cosmic vessel.','earth_cauldron',['earth','brahma egg'],'earth','copper cauldron layers','derived','Tantrasāra description of Brahmāṇḍa in Pṛthivī',sc05),
Scene('bh06','The Egg of Brahmā','A cutaway of Kālāgni, hell, netherworlds, earth, heaven, and Brahmā.','Brahmāṇḍa','The Egg of Brahmā contains a vertical world order within the earth principle.','brahma_egg',['brahmanda','world egg'],'earth','nacre cutaway egg','direct','Tantrasāra Path of Space summary',sc06),
Scene('bh07','The Hundred Rudras','Ten directional groups of ten guardians outside Brahmā’s egg.','Śatarudras','A hundred Rudras guard the quarters beyond the Brahmāṇḍa.','hundred_rudras',['rudras','guardians'],'earth','10x10 guardian grid','direct','Tantrasāra note 105',sc07),
Scene('bh08','The Sixteen Worlds of Nivṛtti','Earth’s enclosure from Kālāgni to Vīrabhadra.','Nivṛtti-kalā','Sixteen worlds are gathered in the lowest kalā-zone.','nivritti_16',['nivritti','16 worlds'],'kalas','sixteen-node world orbit','direct','Tantrasāra notes 114 and Path of Space list',sc08),
Scene('bh09','The Seven Octads of Pratiṣṭhā','Fifty-six worlds distributed from water through Prakṛti.','Pratiṣṭhā-kalā','Seven groups of eight worlds occupy the foundation zone.','seven_octads',['pratistha','56 worlds'],'kalas','seven octad medallions','direct','Tantrasāra Path of Space and note 109',sc09),
Scene('bh10','The Lords of Water','The octad beginning with Lakulīśa.','Jala-bhuvanas','Eight lords govern the water principle.','water_octad',['water','lakulisa'],'octads','eight-lord ring','direct','Tantrasāra Path of Space list',sc10),
Scene('bh11','The Secret Octads','Fire, air, and ether each host an eightfold divine assembly.','Guhyāṣṭakas','Three subtler elements carry three distinct octads.','secret_octads',['fire','air','ether'],'octads','three octad triptych','direct','Tantrasāra Path of Space list and note 109',sc11),
Scene('bh12','The Cognitive Octads','Ahaṃkāra, Buddhi, and Prakṛti each support a world-octad.','Antaḥkaraṇa-bhuvanas','Cosmic cognition contains inhabited world-orders.','cognitive_octads',['ahamkara','buddhi','prakriti'],'octads','three cognitive chambers','direct','Tantrasāra Path of Space and notes 107–109',sc12),
Scene('bh13','The Prakṛti Egg','A vast enclosure containing eight yogic world-types.','Prakṛtyaṇḍa','Prakṛti expands into an immense egg with its own yogic worlds.','prakriti_egg',['prakriti egg','yogastaka'],'eggs','nested green-gold shells','direct','Tantrasāra Path of Space; note 108',sc13),
Scene('bh14','The Eleven Rudra Worlds','Puruṣa opens into eleven Rudra domains.','Puruṣa-bhuvanas','Eleven Rudra worlds mark the finite subject’s cosmic field.','eleven_rudras',['purusha','eleven rudras'],'maya','eleven-node crimson wheel','direct','Tantrasāra note 110',sc14),
Scene('bh15','The Māyic Corridor','Twenty-eight worlds distributed from Puruṣa through Māyā.','Vidyā–Māyā','The constricted levels form a corridor of differentiated world-orders.','maya_corridor',['maya','kanchukas','28 worlds'],'maya','five-chamber count map','direct','Tantrasāra Path of Space summary',sc15),
Scene('bh16','The Five Worlds of Śuddhavidyā','A luminous pentad at the threshold of pure manifestation.','Śuddhavidyā','Five worlds occupy the balanced field of pure knowledge.','suddhavidya_five',['suddhavidya','five worlds'],'pure','five-lord star','direct','Tantrasāra note 113',sc16),
Scene('bh17','Īśvara and Sadāśiva','Eight worlds of vidyā-lords and five worlds of dominant I-consciousness.','Īśvara / Sadāśiva','The pure levels still carry distinct world-orders.','isvara_sadasiva',['isvara','sadasiva'],'pure','dual pure-world medallions','direct','Tantrasāra Path of Space summary',sc17),
Scene('bh18','Śāntā and Worldlessness','Eighteen worlds resolve into Śāntātītā, where no worlds remain.','Śāntā / Śāntātītā','The final world-zone opens into the worldless reach beyond enclosure.','worldlessness',['santa','santatita'],'pure','eighteen-node shell opening upward','direct','Tantrasāra note 114',sc18),
Scene('bh19','The World-Path in the Body','Bhuvanādhvan projected into body, breath, intellect, and void.','Deha-bhuvanādhvan','The cosmography can be internalized as an embodied contemplative map.','body_projection',['body','projection','initiation'],'embodied','body-axis installation','direct','Tantrasāra Path of Space conclusion',sc19),
Scene('bh20','The Bhuvanādhvan Seal','Two hundred twenty-four lights within one consciousness-field.','Bhuvana-cakra','A schematic closing cosmogram of the world-path.','closing_seal',['seal','224 lights'],'seal','224-light elliptical seal','synthetic','Schematic synthesis based on Chapter 8 total count',sc20),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1)
            im=cosmic_ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,80)
            scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=94)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(4*320,5*180),color=NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
      'project':'Tantrāloka — Bhuvanādhvan: The 224 Worlds',
      'source_basis':'Tantrāloka Chapter 8 overview, Tantrasāra Path of Space summary, and associated notes on world groups.',
      'source_critical_note':'Chapter 8 is summarized as a detailed 224-world account. The Tantrasāra also preserves a condensed 118-world enumeration by kalā (16 + 56 + 28 + 18; none in Śāntātītā). This pack preserves both layers rather than treating them as identical.',
      'style':{'family':'deep spatial atlas / inhabited cosmography','background':'obsidian-lapis field','ink':'ivory and ash','accent':'copper, gold, teal, violet, nacre','materials':['nacre world-eggs','copper cauldrons','lapis octads','guardian grids','aurora ladders','body projection']},
      'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
      'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'source_status':s.source_status,'textual_anchor':s.textual_anchor,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{
      'overview_and_lower_worlds':['bh01','bh02','bh03','bh04','bh05','bh06'],
      'earth_and_octad_worlds':['bh07','bh08','bh09','bh10','bh11','bh12','bh13'],
      'maya_and_pure_worlds':['bh14','bh15','bh16','bh17','bh18'],
      'embodiment_and_seal':['bh19','bh20']},
      'reusability_notes':{
        'bh01':'Use for Chapter 8 overview, world-ladders, or ascent through layered cosmos.',
        'bh06':'Use for Brahmāṇḍa cutaways or nested-world cosmology.',
        'bh07':'Use for directional guardians, hundredfold assemblies, or world-lord grids.',
        'bh09':'Use for the seven octads / fifty-six worlds of Pratiṣṭhā.',
        'bh15':'Use for Māyic world distribution and the constricted corridor.',
        'bh18':'Use for worldlessness beyond the final world-zone.',
        'bh19':'Use for projecting cosmology into body, breath, intellect, or void.',
        'bh20':'Use as the Bhuvanādhvan closing seal; the 224-light distribution is explicitly schematic.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))

    dossier='''# AGENT KNOWLEDGE DOSSIER — Bhuvanādhvan / The 224 Worlds

## Aim
This pack visualizes the **Path of Worlds** taught in Tantrāloka Chapter 8: a layered Śaiva cosmos extending from Kālāgni through the Egg of Brahmā, the tattvas, pure worlds, and finally beyond world-structure to Śiva.

## Source-critical structure
- Mark Dyczkowski’s Chapter 8 overview describes **224 worlds and their inhabitants distributed across the thirty-six tattvas**.
- The Tantrasāra Path of Space summary gives a compressed kalā-based enumeration: **16 in Nivṛtti, 56 in Pratiṣṭhā, 28 in Vidyā, 18 in Śāntā, and none in Śāntātītā**, for 118 worlds.
- These are not silently conflated. Scene 20 uses 224 lights as a **schematic total**, while the kalā-count scenes follow the compressed Tantrasāra enumeration.

## Core cosmographic movement
1. Kālāgni
2. hells and netherworlds
3. earth and heaven
4. Brahmāṇḍa
5. the Hundred Rudras outside it
6. elemental and cognitive octads
7. Prakṛti egg
8. Puruṣa and the Māyic corridor
9. pure worlds
10. worldlessness beyond Śāntā
11. projection of the complete path into body, breath, intellect, or void

## Visual rules
- Worlds are inhabited domains, not empty concentric circles.
- Each group should imply rulers, inhabitants, and experiential conditions.
- Keep the lower worlds dense, copper, ember, and earth-toned.
- Let the pure worlds become nacreous, spacious, and increasingly transparent.
- Worldlessness is not another shell; it is the opening beyond shell-structure.
- The closing 224-light seal is a schematic visualization, not a claim about exact per-tattva allocation.

## New motifs
- Fire-of-Time wheel
- hell terraces
- netherworld coils
- earth cauldron
- Brahmāṇḍa cutaway
- Hundred Rudra guardian grid
- sixteen-world Nivṛtti orbit
- seven octad medallions
- elemental secret-octad triptych
- cognitive octad chambers
- Prakṛti egg
- eleven-Rudra wheel
- Māyic world corridor
- pure-world medallions
- worldlessness aperture
- body-projected world ladder
- 224-light closing seal

## Guardrails
- Do not treat Bhuvanādhvan as fantasy geography detached from initiation and consciousness.
- Do not imply that all enumerations in all Śaiva sources are identical.
- Do not reduce the worlds to moral reward/punishment only; they are differentiated experiential and ontological domains.
- The path rises through progressively wider space and consciousness, culminating in identity with Śiva and Śakti.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')

    style='''# STYLE EVOLUTION — Bhuvanādhvan Pack

## Differentiation
This pack adds an inhabited spatial atlas to the existing Tantrāloka corpus. It is darker and more jewel-like than the white breath packs, but avoids generic fantasy-space imagery.

## New symbols
1. Fire-of-Time wheel
2. descending hell terraces
3. netherworld coils
4. copper earth-cauldron
5. nacre Brahmāṇḍa cutaway
6. ten-by-ten Rudra guardian grid
7. octad-world medallions
8. Prakṛti egg
9. Māyic corridor
10. worldlessness aperture
11. body-installed world ladder
12. 224-light seal

## New relationships
- world → ruler → inhabitants
- shell → wider shell → pervasive principle
- lower density → wider space → purer consciousness
- external cosmography ↔ body projection
- world enumeration → worldlessness

## New material vocabulary
- obsidian atmosphere
- lapis spatial glass
- copper world-vessels
- nacre cosmic eggs
- aurora ascent axes
- gold world-lord lights

## Distinct closing seal
Exactly 224 schematic lights are distributed through nested elliptical bands around one luminous center. The manifest explicitly marks this as schematic rather than an exact textual allocation.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')

    source_notes='''# SOURCE NOTES — Bhuvanādhvan Pack

## Directly grounded
- Tantrāloka Chapter 8 concerns the Path of Worlds and describes 224 worlds distributed across the thirty-six tattvas.
- The ascent begins with Kālāgni and passes through Brahmāṇḍa and successively higher principles toward Śiva.
- Tantrasāra describes the Brahmā egg, Hundred Rudras, elemental and cognitive octads, eleven Rudra worlds in Puruṣa, twenty-eight worlds from Puruṣa through Māyā, five in Śuddhavidyā, eight in Īśvara, five in Sadāśiva, and eighteen in Śāntā.
- Tantrasāra also gives the kalā-based total of 118 worlds.

## Derived visual interpretation
- Hell terraces, netherworld coils, cauldrons, shells, and corridors are visual metaphors for layered domains and pervasion.
- The body scene condenses the instruction that the paths may be conceived in body, vital energy, intellect, or the great void.

## Synthetic
- The exact spatial arrangement of 224 lights in scene bh20 is a renderer-created schematic. It does not claim exact traditional per-tattva allocation.
'''
    (ROOT/'SOURCE_NOTES.md').write_text(source_notes,encoding='utf-8')

    readme=f'''# Tantrāloka — Bhuvanādhvan: The 224 Worlds

Included files:
- bhuvanadhvan_224_worlds_animation.mp4
- contact_sheet.jpg
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- STYLE_EVOLUTION.md
- SOURCE_NOTES.md
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

Render:
```bash
python render_pack.py
```
The script is resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')


def validate_outputs():
    combined=ROOT/'bhuvanadhvan_224_worlds_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))


def make_zip():
    zpath=ROOT/'bhuvanadhvan_224_worlds_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['bhuvanadhvan_224_worlds_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','SOURCE_NOTES.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):
            zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'
    concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    combined=ROOT/'bhuvanadhvan_224_worlds_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__': render_all()
