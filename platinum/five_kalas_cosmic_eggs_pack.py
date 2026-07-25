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
SEED = 11115

# Cosmic membrane palette
PARCHMENT = (242, 237, 227)
PARCHMENT_LIGHT = (249, 246, 239)
INK = (35, 38, 46)
UMBER = (84, 69, 56)
BASALT = (76, 77, 82)
EARTH = (143, 112, 76)
AQUA = (98, 150, 155)
TEAL = (76, 132, 139)
LAPIS = (70, 82, 144)
INDIGO = (50, 61, 109)
ROSE = (188, 111, 138)
VIOLET = (130, 105, 165)
GOLD = (202, 159, 81)
GOLD_LIGHT = (242, 211, 134)
OPAL = (224, 230, 239)
PEARL = (245, 243, 238)
WHITE = (252, 250, 246)
BLACK = (18, 19, 23)
SMOKE = (174, 178, 187)
SILVER = (206, 214, 226)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 22)
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


def parchment(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(PARCHMENT, dtype=np.float32)
    coarse = rng.normal(0,1,(42,76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(17))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.5 + fine[...,None]*1.0
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*5,0,13)
    base -= vign[...,None]*0.65
    halo=np.exp(-(((xx-W/2)/(W*0.30))**2 + ((yy-H*0.33)/(H*0.22))**2)*2.4)
    for i in range(3):
        base[...,i] += halo * (8 if i < 2 else 16)
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA',(W,H),(0,0,0,0))


def draw_glow(im,xy,radius,color,alpha=145,blur=17):
    gl=layer(); d=ImageDraw.Draw(gl)
    x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,alpha))
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im,pts,color,width=3,alpha=145,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    gl=gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')


def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8
        x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,140),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(UMBER,116),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,88),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,ROSE,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im)
    y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(248,244,236,218),outline=rgba(UMBER,70),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=UMBER)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=INDIGO)


def dust(im,seed,n=54):
    rng=np.random.default_rng(seed)
    ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(SMOKE,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(22,72))))
    im.alpha_composite(ov)


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
    draw.polygon([p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)],fill=rgba(color,230))


def egg_bbox(cx,cy,rx,ry):
    return (cx-rx,cy-ry,cx+rx,cy+ry)


def draw_egg(draw,cx,cy,rx,ry,col,alpha=160,width=2,fill=None):
    draw.ellipse(egg_bbox(cx,cy,rx,ry),outline=rgba(col,alpha),fill=fill,width=width)


def draw_cracks(draw,cx,cy,rx,ry,col,n=7,phase=0.0):
    for i in range(n):
        a=-math.pi/2+i*2*math.pi/n+phase
        x=cx+math.cos(a)*rx; y=cy+math.sin(a)*ry
        x2=cx+math.cos(a)*rx*.73; y2=cy+math.sin(a)*ry*.73
        mid=(lerp(x,x2,.45)+math.sin(i)*8,lerp(y,y2,.45)+math.cos(i)*8)
        draw.line((x,y,mid[0],mid[1],x2,y2),fill=rgba(col,120),width=2)


def draw_tattva_beads(draw,cx,cy,count,rx,ry,col,phase=0.0,max_show=None):
    total=max_show or count
    for i in range(total):
        a=-math.pi/2+i*2*math.pi/total+phase
        x=cx+math.cos(a)*rx; y=cy+math.sin(a)*ry
        r=4 if total>12 else 6
        draw.ellipse((x-r,y-r,x+r,y+r),fill=rgba(col,190),outline=rgba(WHITE,100))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]


# scenes

def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,282
    shells=[(238,170,BASALT,'Nivṛtti'),(194,138,AQUA,'Pratiṣṭhā'),(148,104,LAPIS,'Vidyā'),(102,72,ROSE,'Śāntā')]
    for i,(rx,ry,col,lab) in enumerate(shells):
        p=smoothstep(.03+i*.08,.75+i*.06,t)
        if p<=0:continue
        draw_egg(d,cx,cy,rx*p,ry*p,col,int(175*p),2,rgba(mix(PARCHMENT_LIGHT,col,.04),28))
        d.text((cx+rx+48,cy-ry+18),lab,font=SMALL_FONT,fill=col)
    draw_glow(im,(cx,cy),50,GOLD_LIGHT,125,15)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    # fifth field beyond shells
    d.arc((cx-284,cy-214,cx+284,cy+214),205,335,fill=rgba(OPAL,150),width=3)
    d.text((cx,92),'Śāntyatītā — beyond the four eggs',font=TERM_FONT,fill=INDIGO,anchor='mm')
    d.text((640,510),'five powers organize four cosmic enclosures and the field beyond them',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,288
    # outermost earth egg / basalt shell
    draw_glow(im,(cx,cy),95,EARTH,78,20)
    draw_egg(d,cx,cy,230,154,BASALT,210,5,rgba((102,93,82),55))
    draw_egg(d,cx,cy,192,126,EARTH,160,2,rgba((176,145,102),45))
    draw_cracks(d,cx,cy,230,154,GOLD,8,t*.08)
    # earth cube at center
    s=54
    d.rectangle((cx-s,cy-s,cx+s,cy+s),outline=rgba(EARTH,220),fill=rgba((174,139,96),90),width=3)
    d.text((cx,cy),'Pṛthivī',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((640,510),'the outermost power encloses the earth principle and marks withdrawal',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,288
    # foundation terraces with 23 beads
    for i in range(5):
        rx=250-i*36; ry=160-i*23
        col=mix(AQUA,GOLD,i/5)
        draw_egg(d,cx,cy,rx,ry,col,135,2,rgba(mix(PARCHMENT_LIGHT,col,.04),22))
    # 23 tattva beads on terrace-like arcs
    positions=[]
    for row,n in enumerate([7,6,5,3,2]):
        y=188+row*48
        span=390-row*55
        xs=np.linspace(cx-span/2,cx+span/2,n)
        for x in xs:positions.append((x,y))
    for i,(x,y) in enumerate(positions[:23]):
        a=smoothstep(.05+i*.018,.85,t)
        r=6
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(mix(AQUA,GOLD,i/23),int(190*a)),outline=rgba(WHITE,100))
    d.line((cx-230,430,cx+230,430),fill=rgba(AQUA,140),width=3)
    d.text((640,468),'water through Prakṛti — a stable foundation of twenty-three levels',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,282
    # vidya prism egg / 7 levels
    draw_egg(d,cx,cy,225,150,LAPIS,150,2,rgba((100,112,175),32))
    prism=[(cx,145),(cx-115,370),(cx+115,370)]
    d.polygon(prism,outline=rgba(LAPIS,220),fill=rgba((160,170,225),38))
    # beam and seven refracted bands
    draw_line_glow(im,[(210,282),(cx-108,282)],GOLD_LIGHT,4,110,7)
    for i in range(7):
        y=210+i*24
        pts=partial_polyline(bezier((cx-20,282),(cx+35,250),(780,y),(1030,y)),smoothstep(.05+i*.04,.72+i*.03,t))
        if len(pts)>1:
            col=mix(LAPIS,ROSE,i/7)
            draw_line_glow(im,pts,col,2,90,5)
            d.text((1050,y-5),str(i+1),font=TINY_FONT,fill=col)
    d.text((640,470),'Puruṣa through Māyā — differentiated knowledge within a lucid shell',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # quiet opaline basin with four pure levels
    draw_egg(d,cx,cy,230,155,ROSE,130,2,rgba((230,195,210),34))
    for i,(lab,col) in enumerate([('Śuddhavidyā',AQUA),('Īśvara',LAPIS),('Sadāśiva',ROSE),('Śakti',GOLD)]):
        y=180+i*70
        rx=160-i*25
        d.arc((cx-rx,y-18,cx+rx,y+18),185,355,fill=rgba(col,175),width=3)
        d.text((cx+210,y-5),lab,font=SMALL_FONT,fill=col)
    draw_glow(im,(cx,412),42,GOLD_LIGHT,100,12)
    d.text((640,505),'four pure levels become progressively quieter until only power remains',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # beyond-peace field, no enclosing egg
    for i in range(7):
        r=34+i*34
        alpha=int(140*(1-i/8))
        d.arc((cx-r,cy-r,cx+r,cy+r),200,340,fill=rgba(mix(GOLD_LIGHT,OPAL,i/7),alpha),width=2)
    draw_glow(im,(cx,cy),82,WHITE,145,23)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    d.text((cx,cy+1),'36',font=SMALL_FONT,fill=INDIGO,anchor='mm')
    # one broken shell far below
    d.arc((cx-250,cy-160,cx+250,cy+160),195,285,fill=rgba(SMOKE,90),width=2)
    d.arc((cx-250,cy-160,cx+250,cy+160),300,345,fill=rgba(SMOKE,90),width=2)
    d.text((640,505),'Śāntyatītā exceeds the four enclosures and reaches the Śiva principle',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,282
    # four eggs displayed as cutaway cross-section
    shells=[(250,166,BASALT,'Nivṛtti'),(205,136,AQUA,'Pratiṣṭhā'),(158,104,LAPIS,'Vidyā'),(108,72,ROSE,'Śāntā')]
    for i,(rx,ry,col,lab) in enumerate(shells):
        draw_egg(d,cx,cy,rx,ry,col,165,3,rgba(mix(PARCHMENT_LIGHT,col,.04),25))
        # cutaway wedge on right
        d.line((cx,cy,cx+rx,cy-ry*.25),fill=rgba(col,105),width=2)
        d.text((cx-rx-80,cy-ry+18),lab,font=SMALL_FONT,fill=col)
    d.text((cx,cy),'one cosmos\nfour eggs',font=TERM_FONT,fill=INK,anchor='mm',align='center')
    d.text((640,505),'the first four powers define nested cosmological containers',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    # elements pervade and cross shells
    elems=[('earth',EARTH),('water',AQUA),('fire',GOLD),('air',TEAL),('space',INDIGO)]
    for i,(lab,col) in enumerate(elems):
        x=220+i*210
        d.ellipse((x-38,cy-38,x+38,cy+38),outline=rgba(col,190),fill=rgba(mix(PARCHMENT_LIGHT,col,.05),55),width=2)
        if i==0:
            d.rectangle((x-16,cy-16,x+16,cy+16),outline=rgba(col,220),width=2)
        elif i==1:
            d.arc((x-22,cy-15,x+22,cy+24),195,345,fill=rgba(col,220),width=3)
        elif i==2:
            d.polygon([(x,cy-28),(x-17,cy+18),(x,cy+8),(x+14,cy+26),(x+22,cy-5)],outline=rgba(col,220),fill=rgba(col,45))
        elif i==3:
            d.arc((x-25,cy-15,x+25,cy+15),205,335,fill=rgba(col,220),width=3)
            d.arc((x-18,cy-2,x+35,cy+24),205,335,fill=rgba(col,160),width=2)
        else:
            for r in [8,16,25]:d.ellipse((x-r,cy-r,x+r,cy+r),outline=rgba(col,140),width=1)
        d.text((x,cy+62),lab,font=SMALL_FONT,fill=col,anchor='mm')
        if i<4:
            pts=partial_polyline(bezier((x+40,cy),(x+90,cy-40),(x+130,cy+40),(x+170,cy)),smoothstep(.05+i*.1,.8+i*.05,t))
            if len(pts)>1:
                draw_line_glow(im,pts,mix(col,elems[i+1][1],.5),2,85,5)
    d.text((640,505),'the elemental powers pervade the cosmic enclosures and extend beyond them',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,282
    # 36 to 38 trident transition
    ys=[400,280,160]
    labels=[('36 — Śiva',GOLD),('37 — Supreme Śiva',OPAL),('38 — the indefinable',VIOLET)]
    for i,(y,(lab,col)) in enumerate(zip(ys,labels)):
        draw_glow(im,(cx,y),44+16*i,col,110,16)
        d.ellipse((cx-18,y-18,cx+18,y+18),fill=rgba(WHITE,245),outline=rgba(col,220),width=2)
        d.text((cx+150,y-6),lab,font=TERM_FONT if i<2 else SMALL_FONT,fill=col)
        if i<2:
            pts=partial_polyline(bezier((cx,y-20),(cx-30,y-65),(cx+30,ys[i+1]+65),(cx,ys[i+1]+20),80),smoothstep(.08+i*.12,.78+i*.08,t))
            if len(pts)>1:
                draw_line_glow(im,pts,mix(col,labels[i+1][1],.5),4,115,7)
                draw_arrowhead(d,pts[-2],pts[-1],mix(col,labels[i+1][1],.5),.9)
    # subtle trident arms at 38
    d.arc((cx-75,90,cx,190),240,70,fill=rgba(VIOLET,180),width=3)
    d.arc((cx,90,cx+75,190),110,300,fill=rgba(VIOLET,180),width=3)
    d.text((640,505),'the sequence passes from the thirty-sixth principle into two transconceptual thresholds',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,282
    # final shell seal with five kalas as translucent petals/shells
    shells=[(250,172,BASALT),(205,140,AQUA),(158,108,LAPIS),(112,76,ROSE)]
    for i,(rx,ry,col) in enumerate(shells):
        a=int(165*smoothstep(.03+i*.06,.72+i*.05,t))
        draw_egg(d,cx,cy,rx,ry,col,a,3,rgba(mix(PARCHMENT_LIGHT,col,.04),24))
    # fifth open crown
    d.arc((cx-286,cy-212,cx+286,cy+212),202,338,fill=rgba(OPAL,190),width=4)
    draw_glow(im,(cx,cy),62,GOLD_LIGHT,130,18)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=rgba(WHITE,255),outline=rgba(GOLD,225),width=2)
    # labels around shell
    names=[('Nivṛtti',BASALT,-160,58),('Pratiṣṭhā',AQUA,-125,20),('Vidyā',LAPIS,110,-10),('Śāntā',ROSE,110,48),('Śāntyatītā',INDIGO,0,-220)]
    for name,col,dx,dy in names:
        d.text((cx+dx,cy+dy),name,font=SMALL_FONT,fill=col,anchor='mm')
    d.text((640,505),'the cosmic eggs resolve into transparent membranes held within one consciousness-field',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
    Scene('fk01','The Five Kalās','Five cosmic powers organize four eggs and a field beyond them.','Kalādhvan','The kalās group the tattvas into nested cosmological domains.','five_kalas_overview',['overview','kalas','eggs'],'overview','nested egg overview',sc01),
    Scene('fk02','Nivṛtti-kalā','The outermost withdrawal boundary containing the earth principle.','Nivṛtti','The first force defines the densest external enclosure.','nivritti_earth_shell',['nivritti','earth','outer shell'],'kalā','basalt egg and earth cube',sc02),
    Scene('fk03','Pratiṣṭhā-kalā','The foundation sphere spanning water through Prakṛti.','Pratiṣṭhā','Twenty-three levels form a stable cosmological foundation.','pratistha_foundation',['pratistha','foundation','23 tattvas'],'kalā','terraced foundation egg',sc03),
    Scene('fk04','Vidyā-kalā','The lucid sphere spanning Puruṣa through Māyā.','Vidyā','Seven differentiated levels are refracted within a knowledge-shell.','vidya_prism',['vidya','knowledge','7 tattvas'],'kalā','prism egg and seven beams',sc04),
    Scene('fk05','Śāntā-kalā','The tranquil pure sphere extending through Śakti.','Śāntā','Four pure levels become progressively quieter and more subtle.','shanta_basin',['shanta','pure levels','peace'],'kalā','opaline basin and four arcs',sc05),
    Scene('fk06','Śāntyatītā-kalā','Beyond peace and beyond the four egg-enclosures.','Śāntyatītā','The fifth power reaches the Śiva principle outside the enclosed cosmos.','shantyatita_beyond',['shantyatita','beyond','shiva'],'kalā','open crown field',sc06),
    Scene('fk07','The Four Cosmic Eggs','A cutaway map of the nested cosmological containers.','Catur-aṇḍa','The first four kalās define four nested eggs.','four_eggs_cutaway',['eggs','cutaway','cosmos'],'process','nested cutaway eggs',sc07),
    Scene('fk08','The Elements Across the Eggs','Elemental powers pervade the enclosures and extend beyond them.','Mahābhūta-vyāpti','The five elements form a continuous pervasion across the structure.','element_pervasion',['elements','pervasion','cosmos'],'process','five elemental medallions',sc08),
    Scene('fk09','From the 36th to the 38th','Śiva, Supreme Śiva, and the indefinable threshold beyond.','Ṣaṭtriṃśat–aṣṭatriṃśat','The chapter crosses from the standard tattva-system into two higher principles.','principles_36_38',['36','37','38','beyond'],'hero','vertical trident threshold',sc09),
    Scene('fk10','The Kalā–Egg Seal','Five powers and four translucent eggs resolve into one field.','Kalā-aṇḍa-cakra','The full structure closes as a transparent cosmological seal.','closing_seal',['seal','kalas','eggs'],'seal','open-crown egg seal',sc10),
]


def render_scene(scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000:continue
            t=i/max(1,NFRAMES-1)
            im=parchment(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,48); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(4*320,3*180),color=PARCHMENT)
    for idx,im in enumerate(thumbs):sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
      'project':'Tantrāloka — The Five Kalās and the Cosmic Eggs',
      'source_basis':'Tantrāloka Chapter 11, especially the five kalās, four cosmic eggs, elemental pervasion, and transition from the 36th to 38th principle.',
      'doctrinal_note':'The first four kalās correspond to four nested cosmic eggs; Śāntyatītā reaches beyond the egg structure to the Śiva principle.',
      'style':{'family':'translucent membrane cosmography','background':'warm parchment','ink':'umber / indigo','accent':'basalt, aqua, lapis, rose, gold, opal','materials':['nacre membranes','basalt crust','aquamarine terraces','lapis prism','opaline crown']},
      'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
      'scenes':[{'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'} for sc in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={
      'ids':[sc.id for sc in SCENES],
      'titles':{sc.id:sc.title for sc in SCENES},
      'modes':{sc.id:sc.mode for sc in SCENES},
      'theme_clusters':{'overview':['fk01'],'five_kalas':['fk02','fk03','fk04','fk05','fk06'],'cosmic_structure':['fk07','fk08'],'beyond_tattvas':['fk09'],'seal':['fk10']},
      'reusability_notes':{
        'fk01':'Use for an overview of kalādhvan or nested cosmic enclosures.',
        'fk02':'Use for dense outer boundary, earth principle, or withdrawal.',
        'fk03':'Use for foundations, layered support, or the water-to-Prakṛti range.',
        'fk04':'Use for knowledge, Māyā, sevenfold differentiation, or prism imagery.',
        'fk05':'Use for pure tattvas, tranquility, or progressive subtlety.',
        'fk06':'Use for Śiva beyond enclosure or open-field transcendence.',
        'fk07':'Use for four eggs, nested universes, or cutaway cosmology.',
        'fk08':'Use for elemental pervasion across domains.',
        'fk09':'Use for the 36th–38th principle transition.',
        'fk10':'Use as the pack’s closing kalā–egg seal.'}
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))

    dossier='''# AGENT KNOWLEDGE DOSSIER — The Five Kalās and the Cosmic Eggs

## Aim
This pack visualizes the opening structure of **Tantrāloka Chapter 11**: five kalās or cosmic powers, four nested eggs, elemental pervasion, and the transition beyond the standard thirty-six tattvas.

## Source-supported structure
The five kalās are:
1. **Nivṛtti** — associated with the earth principle.
2. **Pratiṣṭhā** — extending from water through Prakṛti.
3. **Vidyā** — extending from Puruṣa through Māyā.
4. **Śāntā** — extending through the pure levels to Śakti.
5. **Śāntyatītā** — beyond the four eggs, reaching the Śiva principle.

The first four define four cosmic eggs. The chapter then discusses elemental pervasion, Supreme Śiva as a thirty-seventh principle, and an indefinable thirty-eighth principle.

## Visual rules
- The kalās are organizing powers, not merely decorative colored shells.
- The first four should look like distinct kinds of containment.
- Śāntyatītā should remain open and unenclosed.
- Nivṛtti must feel dense and boundary-like.
- Pratiṣṭhā should feel foundational and load-bearing.
- Vidyā should feel lucid, refractive, and differentiating.
- Śāntā should feel increasingly quiet and pure.
- The 36th–38th scene must be visually distinct from the egg scenes.

## New symbols
- basalt earth egg
- aquamarine foundation terraces
- seven-beam knowledge prism
- opaline pure-level basin
- open crown beyond the eggs
- cutaway four-egg cosmology
- elemental pervasion chain
- 36–38 trident threshold

## Material vocabulary
- nacre membranes
- basalt crust
- aquamarine terraces
- lapis prism-glass
- rose opaline veil
- pearl-white open field

## Guardrails
- Do not state that there are five eggs: Chapter 11 distinguishes five kalās but four eggs.
- Do not collapse Śāntyatītā into another closed shell.
- Do not turn the kalās into the five gross elements; the elements are related but are not identical to the five kalās.
- Treat the thirty-eighth principle as indefinable rather than over-describing it.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')

    style='''# STYLE EVOLUTION — Five Kalās and Cosmic Eggs

## Differentiation
This pack introduces a translucent cosmological-material language rather than another ladder or mantra wheel.

## New motifs
1. nested cosmic eggs
2. basalt withdrawal crust
3. twenty-three-level foundation terraces
4. sevenfold knowledge prism
5. opaline tranquility basin
6. open crown beyond enclosure
7. elemental pervasion chain
8. 36th–38th trident transition
9. kalā–egg closing seal

## New relationships
- organizing power → enclosed tattva-range
- density → foundation → knowledge → tranquility → beyond
- element → pervasion across shells
- thirty-six tattvas → transconceptual principles
- enclosure → transparency within consciousness

## New materials
- nacre membrane
- basalt crust
- aquamarine stone-water
- lapis prism glass
- opal and pearl light

## Composition discipline
No basic composition is reused more than twice. The scenes alternate among nested shells, terraced cross-section, prism refraction, tranquil basin, open field, cutaway diagram, elemental chain, and vertical threshold.

## Closing seal
A four-shell egg structure crowned by the unenclosed fifth kalā, all made transparent around a gold bindu.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')

    readme=f'''# Tantrāloka — The Five Kalās and the Cosmic Eggs Pack

Included:
- five_kalas_cosmic_eggs_animation.mp4
- contact_sheet.jpg
- render_pack.py
- scene_manifest.json
- scene_catalog.json
- AGENT_KNOWLEDGE_DOSSIER.md
- STYLE_EVOLUTION.md
- validation.json
- scenes/*.mp4

Specs:
- {W}×{H}
- {FPS} fps
- {len(SCENES)} scenes
- {DURATION}s per scene
- {len(SCENES)*DURATION:.1f}s total

Run:
```bash
python render_pack.py
```
The renderer is resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')


def validate_outputs():
    combined=ROOT/'five_kalas_cosmic_eggs_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))


def make_zip():
    zpath=ROOT/'five_kalas_cosmic_eggs_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['five_kalas_cosmic_eggs_animation.mp4','contact_sheet.jpg','render_pack.py','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat_file=ROOT/'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'five_kalas_cosmic_eggs_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':render_all()
