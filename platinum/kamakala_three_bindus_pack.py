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
SEED = 30303

# Kāmākalā palette: clean white, red power, dark depth, mixed gold-violet
PARCHMENT = (246, 242, 233)
PARCHMENT_LIGHT = (252, 249, 243)
WHITE = (255, 253, 248)
SILVER = (211, 216, 224)
INK = (32, 31, 37)
UMBER = (83, 66, 57)
BLACK = (18, 17, 22)
INDIGO = (57, 64, 108)
VIOLET = (125, 92, 150)
CRIMSON = (158, 38, 57)
RED_LIGHT = (222, 111, 121)
ROSE = (192, 105, 135)
GOLD = (205, 160, 80)
GOLD_LIGHT = (245, 213, 137)
SAFFRON = (229, 151, 48)
TEAL = (98, 145, 145)
SMOKE = (168, 166, 176)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)


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
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.6 + fine[...,None]*1.05
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*5,0,13)
    base -= vign[...,None]*0.7
    # luminous white upper left, red lower right, violet central blend
    g1 = np.exp(-(((xx-W*0.34)/(W*0.20))**2 + ((yy-H*0.32)/(H*0.24))**2)*2.8)
    g2 = np.exp(-(((xx-W*0.66)/(W*0.20))**2 + ((yy-H*0.42)/(H*0.24))**2)*2.8)
    g3 = np.exp(-(((xx-W/2)/(W*0.18))**2 + ((yy-H*0.46)/(H*0.20))**2)*3.0)
    base[...,0] += g1*9 + g2*14 + g3*10
    base[...,1] += g1*9 + g2*3 + g3*4
    base[...,2] += g1*12 + g2*5 + g3*14
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA', (W,H), (0,0,0,0))


def draw_glow(im, xy, radius, color, alpha=150, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x,y = xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius), fill=rgba(color,alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)


def draw_line_glow(im, pts, color, width=3, alpha=150, blur=8):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color,alpha), width=max(1,width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color,min(255,alpha+70)), width=width, joint='curve')


def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8
        x=cx+math.cos(a)*r*0.62
        y=cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,150), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(UMBER,120), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,90), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,ROSE,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im)
    y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(248,244,237,216), outline=rgba(UMBER,75), width=1)
    d.text((122,y0+18), title, font=TITLE_FONT, fill=INK)
    d.text((124,y0+58), subtitle, font=SUB_FONT, fill=UMBER)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=INDIGO)


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


def arc_points(cx,cy,rx,ry,a0,a1,n=90):
    return [(cx+math.cos(lerp(a0,a1,i/(n-1)))*rx,cy+math.sin(lerp(a0,a1,i/(n-1)))*ry) for i in range(n)]


def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    pts=[p1,(p1[0]-math.cos(ang-0.5)*s,p1[1]-math.sin(ang-0.5)*s),(p1[0]-math.cos(ang+0.5)*s,p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts,fill=rgba(color,230))


def dust(im,seed,n=55):
    rng=np.random.default_rng(seed)
    ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(SMOKE,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(28,78))))
    im.alpha_composite(ov)


def draw_bindu(draw,im,x,y,r,col,core=WHITE,alpha=220):
    draw_glow(im,(x,y),int(r*1.8),col,120,16)
    draw.ellipse((x-r,y-r,x+r,y+r),fill=rgba(core,alpha),outline=rgba(col,230),width=2)


def draw_triangle(draw,pts,col,fill=None,width=3):
    draw.polygon(pts,outline=rgba(col,220),fill=fill or rgba((255,255,255),20))
    for i in range(3):
        a=pts[i]; b=pts[(i+1)%3]
        draw.line((a,b),fill=rgba(col,220),width=width)


def regular_triangle(cx,cy,r,rot=-math.pi/2):
    return [(cx+math.cos(rot+2*math.pi*i/3)*r,cy+math.sin(rot+2*math.pi*i/3)*r) for i in range(3)]


def draw_ripple(draw,cx,cy,r,col,alpha=110):
    draw.ellipse((cx-r,cy-r*0.68,cx+r,cy+r*0.68),outline=rgba(col,alpha),width=2)


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
    draw_fn:Callable[[Image.Image,float],None]


# scenes

def sc01(im,t):
    d=ImageDraw.Draw(im)
    pts=[(640,135),(380,420),(900,420)]
    cols=[WHITE,CRIMSON,VIOLET]
    names=['Prakāśa','Vimarśa','Miśra']
    for i,(p,col,name) in enumerate(zip(pts,cols,names)):
        draw_bindu(d,im,p[0],p[1],22,col,core=WHITE if i==0 else (CRIMSON if i==1 else GOLD_LIGHT))
        d.text((p[0],p[1]+54),name,font=TERM_FONT,fill=INDIGO if i==0 else col,anchor='mm')
    tri=regular_triangle(640,300,220,rot=-math.pi/2)
    progress=smoothstep(0.05,0.85,t)
    for i in range(3):
        a=tri[i]; b=tri[(i+1)%3]
        line=partial_polyline([a,b],progress)
        if len(line)>1: draw_line_glow(im,line,mix(cols[i],cols[(i+1)%3],.5),3,110,6)
    draw_glow(im,(640,300),40,GOLD_LIGHT,90,12)
    d.text((640,508),'light, reflection, and generative mixture',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=640,278
    draw_bindu(d,im,cx,cy,28,WHITE,core=WHITE)
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12
        p0=(cx+math.cos(a)*44,cy+math.sin(a)*44)
        p1=(cx+math.cos(a)*(230*ease_out_cubic(t)),cy+math.sin(a)*(145*ease_out_cubic(t)))
        draw_line_glow(im,[p0,p1],mix(WHITE,GOLD_LIGHT,i/12),2,85,5)
    for r in [68,118,176,228]:
        draw_ripple(d,cx,cy,r,SILVER,95)
    d.text((640,505),'self-luminous subjectivity before any reflected object',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=640,278
    draw_bindu(d,im,cx,cy,28,CRIMSON,core=CRIMSON)
    for i in range(10):
        a=-math.pi/2+i*2*math.pi/10+t*0.12
        x=cx+math.cos(a)*190
        y=cy+math.sin(a)*120
        pts=partial_polyline(bezier((cx,cy),(cx+math.cos(a)*70,cy+math.sin(a)*40),(x-20*math.cos(a),y-16*math.sin(a)),(x,y),80),smoothstep(0.05+i*0.04,0.8+i*0.02,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(CRIMSON,ROSE,i/10),3,100,6)
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(mix(CRIMSON,ROSE,i/10),190))
    d.text((640,505),'reflexive power turns light back upon itself',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im)
    lx,rx,cy=420,860,278
    draw_bindu(d,im,lx,cy,24,WHITE,core=WHITE)
    draw_bindu(d,im,rx,cy,24,CRIMSON,core=CRIMSON)
    # mirror field and crossing currents
    d.rounded_rectangle((560,150,720,406),radius=22,outline=rgba(SILVER,170),fill=rgba((235,238,246),55),width=2)
    for i in range(7):
        y=185+i*30
        pts1=partial_polyline(bezier((lx+28,cy),(510,y),(580,y),(640,y),70),smoothstep(0.05+i*0.04,0.75+i*0.03,t))
        pts2=partial_polyline(bezier((rx-28,cy),(770,y),(700,y),(640,y),70),smoothstep(0.05+i*0.04,0.75+i*0.03,t))
        if len(pts1)>1: draw_line_glow(im,pts1,mix(WHITE,VIOLET,i/7),2,75,5)
        if len(pts2)>1: draw_line_glow(im,pts2,mix(CRIMSON,VIOLET,i/7),2,75,5)
    draw_glow(im,(640,278),54,VIOLET,105,16)
    d.text((420,448),'subject',font=TERM_FONT,fill=INDIGO,anchor='mm')
    d.text((860,448),'object',font=TERM_FONT,fill=CRIMSON,anchor='mm')
    d.text((640,505),'the act of awareness arises between light and reflection',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im)
    lx,rx,cy=470,810,278
    mx=lerp(lx,640,ease_in_out(t)); rx2=lerp(rx,640,ease_in_out(t))
    draw_bindu(d,im,mx,cy,24,WHITE,core=WHITE)
    draw_bindu(d,im,rx2,cy,24,CRIMSON,core=CRIMSON)
    if abs(mx-rx2)<75:
        draw_glow(im,(640,cy),82,VIOLET,145,22)
        draw_bindu(d,im,640,cy,30,VIOLET,core=GOLD_LIGHT)
    # generative shock lines
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12
        length=30+140*smoothstep(.45,.95,t)
        p0=(640+math.cos(a)*26,cy+math.sin(a)*26)
        p1=(640+math.cos(a)*length,cy+math.sin(a)*length*0.68)
        draw_line_glow(im,[p0,p1],mix(VIOLET,GOLD_LIGHT,i/12),2,75,5)
    d.text((640,505),'the mixed bindu is the friction-point that generates the seed of cosmos',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im)
    pts=regular_triangle(640,300,220,rot=-math.pi/2)
    cols=[WHITE,CRIMSON,VIOLET]
    names=['Prakāśa','Vimarśa','Miśra']
    for p,col,name in zip(pts,cols,names):
        draw_bindu(d,im,p[0],p[1],22,col,core=WHITE if col==WHITE else (CRIMSON if col==CRIMSON else GOLD_LIGHT))
        d.text((p[0],p[1]+46),name,font=SMALL_FONT,fill=INDIGO if col==WHITE else col,anchor='mm')
    for i in range(3):
        a=pts[i]; b=pts[(i+1)%3]
        line=partial_polyline([a,b],smoothstep(0.05+i*0.10,0.82+i*0.06,t))
        if len(line)>1:
            draw_line_glow(im,line,mix(cols[i],cols[(i+1)%3],.5),4,125,7)
    # nested triangle appears
    inner=regular_triangle(640,300,110,rot=math.pi/2)
    for i in range(3):
        a=inner[i]; b=inner[(i+1)%3]
        line=partial_polyline([a,b],smoothstep(0.35+i*0.07,0.92,t))
        if len(line)>1: draw_line_glow(im,line,GOLD,2,85,5)
    draw_glow(im,(640,300),36,GOLD_LIGHT,105,12)
    d.text((640,505),'Kāmākalā: the triangular engine of polarity and manifestation',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=640,260
    draw_bindu(d,im,cx,cy,24,VIOLET,core=GOLD_LIGHT)
    # three streams: sound, form, world
    streams=[('phoneme',INDIGO,-170),('form',ROSE,0),('world',GOLD,170)]
    for i,(label,col,off) in enumerate(streams):
        end=(cx+off,430)
        pts=partial_polyline(bezier((cx,cy+24),(cx+off*0.2,310),(end[0],360),end,90),smoothstep(0.05+i*0.08,0.84+i*0.04,t))
        if len(pts)>1:
            draw_line_glow(im,pts,col,4,120,7)
            draw_arrowhead(d,pts[-2],pts[-1],col,0.9)
        if i==0:
            d.text((end[0],end[1]),'अ',font=DEVA_MED,fill=col,anchor='mm')
        elif i==1:
            tri=regular_triangle(end[0],end[1],32,rot=-math.pi/2)
            draw_triangle(d,tri,col,fill=rgba(ROSE,28),width=2)
        else:
            d.ellipse((end[0]-34,end[1]-24,end[0]+34,end[1]+24),outline=rgba(col,190),width=2)
            for a in np.linspace(0,2*math.pi,8,endpoint=False):
                x=end[0]+math.cos(a)*34; y=end[1]+math.sin(a)*24
                d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,190))
        d.text((end[0],485),label,font=SMALL_FONT,fill=col,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=640,295
    outer=regular_triangle(cx,cy,230,rot=-math.pi/2)
    inner=regular_triangle(cx,cy,120,rot=math.pi/2)
    cols=[WHITE,CRIMSON,VIOLET]
    # outer nodes and triangle
    for p,col in zip(outer,cols):
        draw_bindu(d,im,p[0],p[1],20,col,core=WHITE if col==WHITE else (CRIMSON if col==CRIMSON else GOLD_LIGHT))
    for i in range(3):
        a=outer[i]; b=outer[(i+1)%3]
        draw_line_glow(im,[a,b],mix(cols[i],cols[(i+1)%3],.5),4,120,7)
    for i in range(3):
        a=inner[i]; b=inner[(i+1)%3]
        draw_line_glow(im,[a,b],GOLD,2,90,5)
    # orbiting seed points
    for i in range(18):
        a=-math.pi/2+i*2*math.pi/18+t*0.08
        r=172+18*math.sin(i*1.7)
        x=cx+math.cos(a)*r
        y=cy+math.sin(a)*r*0.72
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(INDIGO,GOLD_LIGHT,i/18),185))
    draw_glow(im,(cx,cy),72,GOLD_LIGHT,130,18)
    draw_bindu(d,im,cx,cy,24,GOLD_LIGHT,core=WHITE)
    d.text((cx,cy),'ह्रीं',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    d.text((640,505),'the three bindus resolve into one generative seal',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
    Scene('kb01','The Three Bindus','An overview of light, reflection, and generative mixture.','Kāmākalā','The bindu-triad forms a structural triangle of subject, object, and their union.','three_bindu_overview',['overview','bindu','triangle'],'overview','three-node triangle',sc01),
    Scene('kb02','Prakāśa','White bindu: unmoving luminosity and subjective consciousness.','Prakāśa','Pure light shines as self-luminous subjectivity.','white_bindu',['prakasha','light','subject'],'bindu','white radiance field',sc02),
    Scene('kb03','Vimarśa','Red bindu: reflexive creative power and self-awareness.','Vimarśa','Consciousness reflects upon itself through dynamic power.','red_bindu',['vimarsha','reflection','shakti'],'bindu','red reflexive arcs',sc03),
    Scene('kb04','Subject, Object, and Knowing','The act of perception forms between light and reflection.','Pramātṛ–Prameya–Pramāṇa','Subject, object, and knowing are generated as a relational field.','relational_mirror',['subject','object','knowing'],'relation','mirror chamber',sc04),
    Scene('kb05','Miśra Bindu','White and red converge into a mixed generative seed.','Miśra Bindu','The collision of luminosity and reflection produces the mixed bindu.','mixed_collision',['misra','collision','seed'],'bindu','converging bindus',sc05),
    Scene('kb06','Kāmākalā','The three bindus stabilize as a generative triangle.','Kāmākalā','The bindu-triad becomes a structural engine of polarity and manifestation.','kamakala_triangle',['triangle','polarity','manifestation'],'structure','nested triangle engine',sc06),
    Scene('kb07','The Seed Becomes Cosmos','Sound, form, and world unfold from the mixed bindu.','Bīja–Viśva','The generative seed differentiates into phoneme, image, and world.', 'seed_to_cosmos',['sound','form','world'],'process','three-stream emergence',sc07),
    Scene('kb08','The Kāmākalā Seal','The three potentials resolve into a single generative cosmogram.','Kāmākalā-cakra','The pack closes in a triangular seal of light, reflection, and creation.','closing_seal',['seal','cosmogram','bindu'],'seal','triangular bindu seal',sc08),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id
    sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000:
                continue
            t=i/max(1,NFRAMES-1)
            im=parchment(SEED+hash(scene.id)%10000+i)
            border(im)
            dust(im,SEED+i,48)
            scene.draw_fn(im,t)
            footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*0.72):04d}.jpg'
        im=Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        thumbs.append(im)
    sheet=Image.new('RGB',(4*320,2*180),color=PARCHMENT)
    for idx,im in enumerate(thumbs):
        x=(idx%4)*320; y=(idx//4)*180
        sheet.paste(im,(x,y))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
        'project':'Tantrāloka — The Three Structural Bindus (Kāmākalā)',
        'source_basis':'Conceptual mapping supplied by the user: Prakāśa, Vimarśa, and Miśra as foundational bindus generating subject, object, and manifestation.',
        'style':{
            'family':'minimal bindu cosmography / triangular generative engine',
            'background':'clean warm parchment',
            'ink':'black / indigo',
            'accent':'white, crimson, violet, gold',
            'materials':['white radiance','red lacquer light','mirror membrane','mixed violet-gold bindu','triangular seal']
        },
        'fps':FPS,
        'resolution':[W,H],
        'scene_duration_seconds':DURATION,
        'total_scenes':len(SCENES),
        'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[
            {'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'}
            for sc in SCENES
        ]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id:sc.title for sc in SCENES},
        'modes':{sc.id:sc.mode for sc in SCENES},
        'theme_clusters':{
            'overview':['kb01'],
            'foundational_bindus':['kb02','kb03','kb05'],
            'relational_structure':['kb04','kb06'],
            'emanation_and_seal':['kb07','kb08']
        },
        'reusability_notes':{
            'kb01':'Use to introduce the three-bindus doctrine or Kāmākalā as a triadic structure.',
            'kb02':'Use for pure luminosity, subjectivity, prakāśa, or white bindu symbolism.',
            'kb03':'Use for reflexivity, vimarśa, Śakti, or red bindu symbolism.',
            'kb04':'Use for subject-object-knowing relations or perception as a relational field.',
            'kb05':'Use for the mixed bindu, union, friction, generative collision, or seed formation.',
            'kb06':'Use for Kāmākalā, triangular polarity, or foundational triadic generation.',
            'kb07':'Use for seed-to-cosmos, phoneme-form-world emergence, or creative differentiation.',
            'kb08':'Use as a closing seal for Kāmākalā, bindu cosmology, or triadic manifestation.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Kāmākalā and the Three Bindus

## Aim
This pack visualizes the **three structural bindus** as a triangular engine of subject, object, awareness, and manifestation.

## Textual orientation
The pack is based on the user-supplied conceptual structure:
- **Prakāśa** — white bindu, unmoving luminosity, Śiva, subjectivity
- **Vimarśa** — red bindu, dynamic reflection, Śakti, creative objectivity
- **Miśra** — mixed bindu, generative union / friction producing the seed of cosmos

## Core doctrinal idea
Consciousness is not a single inert light. It is luminous, reflexive, and generative. The white and red bindus form a polarity whose mixed point produces the structural seed of manifestation. The bindus also map the relation among subject, object, and knowing.

## Visual rules
- Keep the pack minimal, lucid, and potent.
- White should signify self-luminous Prakāśa, not emptiness alone.
- Red should signify dynamic reflexive power, not aggression.
- The mixed bindu should visibly combine rather than merely sit between the other two.
- Kāmākalā should stabilize as a triangle, not a generic three-dot diagram.
- The final seal should show the three potentials as one engine.

## Style family
- clean warm parchment
- white radiance
- crimson lacquer light
- violet-gold mixture
- silver mirror membrane
- nested triangles and bindu fields

## New motifs introduced
- three-bindu overview triangle
- white radiance field
- red reflexive arcs
- subject-object mirror chamber
- converging bindu collision
- nested Kāmākalā triangle
- seed-to-cosmos triple stream
- triangular bindu seal

## Guardrails
- Do not reduce Prakāśa to passive masculine substance and Vimarśa to a separate external feminine force.
- Do not treat Miśra as a compromise halfway-point only; it is generative.
- Avoid generic “sacred feminine / masculine” poster language.
- Preserve the structural relation: luminosity, reflexivity, and manifestation.

## Reuse strategy
- kb01: doctrinal overview
- kb02 / kb03 / kb05: the three bindus
- kb04: subject-object-knowing relation
- kb06: Kāmākalā triangle
- kb07: emergence from seed
- kb08: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Kāmākalā / Three Bindus Pack

## Inheritance
This pack inherits the project’s contemplative diagrammatic rigor but shifts into its most minimal visual language so far.

## Kāmākalā differentiation
This pack emphasizes:
- three concentrated points rather than large hierarchies
- white luminosity, red reflexivity, and violet-gold mixture
- relation and generative friction
- triangular stabilization
- clean white space with only necessary structure

## New motifs added
1. three-bindu overview triangle
2. white radiance field
3. red reflexive spiral-field
4. mirror membrane between subject and object
5. converging bindu collision
6. nested Kāmākalā triangle
7. triple stream: phoneme, form, world
8. triangular closing seal

## New relationships added
- light → reflection
- subject ↔ object
- subject + object → knowing
- white bindu + red bindu → mixed bindu
- mixed bindu → phoneme / form / world
- triadic polarity → stable generative engine

## New material vocabulary
- white luminous enamel
- crimson lacquer-light
- silver mirror membrane
- violet-gold mixed radiance
- fine triangular gold linework

## Deprecated clichés
- generic yin-yang treatment
- gendered New Age polarity posters
- three static colored dots with no relational motion

## Distinct closing seal
The closing seal is a **triangular Kāmākalā cosmogram** containing the three bindus, a nested inverse triangle, orbiting seed-points, and a central luminous bīja.

## Recommendation for future packs
The six requested structural packs are now complete. A next phase could deepen into:
- the upāyas
- śaktipāta
- mātṛkā-cakra variants
- hṛdaya / the heart
- āṇava, śākta, and śāmbhava contemplative operators
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — The Three Structural Bindus (Kāmākalā) Pack

Included files:
- kamakala_three_bindus_animation.mp4
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
    combined=ROOT/'kamakala_three_bindus_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    info=json.loads(probe)
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))


def make_zip():
    zpath=ROOT/'kamakala_three_bindus_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['kamakala_three_bindus_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
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
    combined=ROOT/'kamakala_three_bindus_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
