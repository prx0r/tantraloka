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

# Optical-constriction palette
PAPER = (246, 243, 236)
PAPER_LIGHT = (251, 249, 244)
INK = (36, 39, 46)
UMBER = (84, 69, 55)
SLATE = (103, 111, 126)
MIST = (174, 181, 190)
WHITE = (253, 251, 246)
GOLD = (204, 164, 88)
GOLD_LIGHT = (244, 215, 143)
CRIMSON = (154, 51, 67)
CORAL = (205, 100, 93)
INDIGO = (72, 82, 133)
DEEP_INDIGO = (48, 58, 101)
VIOLET = (126, 111, 166)
ROSE = (188, 122, 138)
TEAL = (92, 145, 146)
GREEN = (104, 151, 112)
SMOKE = (202, 205, 213)
ASH = (223, 225, 230)
BLACK = (19, 20, 24)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 22)


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


def ground(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H,W,3), dtype=np.float32)
    base[:] = np.array(PAPER, dtype=np.float32)
    coarse = rng.normal(0,1,(40,74)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.6 + fine[...,None]*1.0
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*5,0,13)
    base -= vign[...,None]*0.7
    halo = np.exp(-(((xx-W/2)/(W*0.30))**2 + ((yy-H*0.30)/(H*0.20))**2)*2.6)
    for i in range(3):
        base[...,i] += halo * (12 if i<2 else 20)
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


def draw_rosette(draw, cx, cy, r, outer, inner):
    for i in range(8):
        a=2*math.pi*i/8
        x=cx+math.cos(a)*r*0.62
        y=cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,145), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(SLATE,112), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,86), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,VIOLET,GOLD)


def footer(im,title,subtitle,term=None):
    d = ImageDraw.Draw(im)
    y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(248,246,240,220), outline=rgba(SLATE,66), width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=SLATE)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=DEEP_INDIGO)


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
    if amount<=0:return []
    if amount>=1:return points
    f=amount*(len(points)-1)
    idx=int(f); frac=f-idx
    out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]
        out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out


def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    pts=[p1,(p1[0]-math.cos(ang-0.5)*s,p1[1]-math.sin(ang-0.5)*s),(p1[0]-math.cos(ang+0.5)*s,p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts,fill=rgba(color,230))


def dust(im, seed, n=50):
    rng=np.random.default_rng(seed)
    ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(20,68))))
    im.alpha_composite(ov)


def draw_aperture(draw,cx,cy,r_outer,r_inner,col,alpha=180):
    draw.ellipse((cx-r_outer,cy-r_outer,cx+r_outer,cy+r_outer),outline=rgba(col,alpha),width=2)
    for i in range(8):
        a=i*2*math.pi/8
        p1=(cx+math.cos(a)*r_inner,cy+math.sin(a)*r_inner)
        p2=(cx+math.cos(a)*r_outer,cy+math.sin(a)*r_outer)
        draw.line((p1,p2),fill=rgba(col,90),width=1)


def draw_chain_link(draw,cx,cy,w,h,col,rot=0.0):
    # approximate unrotated chain link
    draw.rounded_rectangle((cx-w/2,cy-h/2,cx+w/2,cy+h/2),radius=int(h/2),outline=rgba(col,200),width=3)
    draw.rounded_rectangle((cx-w*0.28,cy-h*0.18,cx+w*0.28,cy+h*0.18),radius=int(h*0.18),outline=rgba(col,120),width=2)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]


def sc01(im,t):
    d=ImageDraw.Draw(im)
    cx=220; cy=280
    draw_glow(im,(cx,cy),72,GOLD_LIGHT,130,20)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    labels=[('Āṇava',CRIMSON),('Māyīya',INDIGO),('Kārma',TEAL)]
    xs=[480,730,980]
    for i,(lab,col) in enumerate(labels):
        x=xs[i]
        d.rounded_rectangle((x-72,205,x+72,355),radius=18,outline=rgba(col,185),fill=rgba(mix(PAPER_LIGHT,col,.06),70),width=2)
        d.text((x,280),lab,font=TERM_FONT,fill=col,anchor='mm')
        p0=(cx+24 if i==0 else xs[i-1]+72,280)
        p1=(x-72,280)
        pts=partial_polyline(bezier(p0,(p0[0]+60,250),(p1[0]-60,310),p1,80),smoothstep(.04+i*.12,.78+i*.06,t))
        if len(pts)>1:
            draw_line_glow(im,pts,mix(labels[max(0,i-1)][1] if i>0 else GOLD,col,.5),3,105,6)
            draw_arrowhead(d,pts[-2],pts[-1],col,.8)
    draw_glow(im,(1110,280),28,SLATE,80,10)
    d.ellipse((1098,268,1122,292),fill=rgba(SLATE,190),outline=rgba(INK,100),width=1)
    d.text((640,505),'infinite capacity becomes finite through three successive filters',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    for i in range(18):
        a=i*2*math.pi/18
        r1=70; r2=230
        draw_line_glow(im,[(cx+math.cos(a)*r1,cy+math.sin(a)*r1),(cx+math.cos(a)*r2,cy+math.sin(a)*r2)],mix(GOLD_LIGHT,WHITE,i/18),2,75,5)
    draw_glow(im,(cx,cy),96,GOLD_LIGHT,145,24)
    d.ellipse((cx-28,cy-28,cx+28,cy+28),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,170),'pūrṇatva',font=TERM_FONT,fill=GOLD,anchor='mm')
    d.text((640,505),'pure consciousness begins as unbounded fullness and capacity',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    # shrinking aperture
    outer=220; inner=lerp(160,28,ease_in_out(t))
    draw_aperture(d,cx,cy,outer,inner,CRIMSON,180)
    draw_glow(im,(cx,cy),max(30,inner*.55),CORAL,95,14)
    d.ellipse((cx-inner*.30,cy-inner*.30,cx+inner*.30,cy+inner*.30),fill=rgba(CRIMSON,120),outline=rgba(CRIMSON,200),width=2)
    # broken circumference markers
    for i in range(9):
        a=i*2*math.pi/9
        x=cx+math.cos(a)*185; y=cy+math.sin(a)*120
        d.line((x-8,y,x+8,y),fill=rgba(UMBER,110),width=2)
    d.text((cx,150),'“I am small; I lack.”',font=TERM_FONT,fill=CRIMSON,anchor='mm')
    d.text((640,505),'āṇavamala contracts fullness into a felt fragment of insufficiency',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    draw_glow(im,(cx-230,cy),38,GOLD_LIGHT,110,12)
    d.ellipse((cx-244,cy-14,cx-216,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,210),width=2)
    # prism/mirror division
    prism=[(cx-18,190),(cx-18,370),(cx+76,280)]
    d.polygon(prism,outline=rgba(INDIGO,200),fill=rgba((225,230,246),70))
    pts=partial_polyline(bezier((cx-210,cy),(cx-120,cy),(cx-60,cy),(cx-20,cy),80),smoothstep(.05,.75,t))
    if len(pts)>1:draw_line_glow(im,pts,GOLD,4,110,7)
    # split beams
    p1=partial_polyline(bezier((cx+44,cy),(cx+130,220),(cx+250,190),(cx+380,200),90),smoothstep(.2,.92,t))
    p2=partial_polyline(bezier((cx+44,cy),(cx+130,340),(cx+250,370),(cx+380,360),90),smoothstep(.2,.92,t))
    if len(p1)>1:draw_line_glow(im,p1,INDIGO,4,120,7)
    if len(p2)>1:draw_line_glow(im,p2,ROSE,4,120,7)
    d.text((cx+410,195),'subject',font=TERM_FONT,fill=INDIGO)
    d.text((cx+410,355),'object',font=TERM_FONT,fill=ROSE)
    d.text((640,505),'māyīyamala refracts one field into “me” and “world”',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    # causal feedback wheel
    labels=[('lack',CRIMSON),('desire',ROSE),('action',TEAL),('result',INDIGO)]
    for i,(lab,col) in enumerate(labels):
        a=-math.pi/2+i*2*math.pi/4
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*115
        d.rounded_rectangle((x-58,y-28,x+58,y+28),radius=14,outline=rgba(col,185),fill=rgba(mix(PAPER_LIGHT,col,.06),70),width=2)
        d.text((x,y),lab,font=SMALL_FONT,fill=col,anchor='mm')
    for i,(lab,col) in enumerate(labels):
        a0=-math.pi/2+i*2*math.pi/4
        a1=-math.pi/2+((i+1)%4)*2*math.pi/4
        pts=[]
        for j in range(70):
            a=lerp(a0+.18,a1-.18,j/69)
            pts.append((cx+math.cos(a)*180,cy+math.sin(a)*115))
        pts=partial_polyline(pts,smoothstep(.05+i*.12,.78+i*.06,t))
        if len(pts)>1:
            draw_line_glow(im,pts,col,3,100,6)
            draw_arrowhead(d,pts[-2],pts[-1],col,.8)
    # chain at center
    draw_chain_link(d,cx-28,cy,96,38,TEAL)
    draw_chain_link(d,cx+28,cy,96,38,INDIGO)
    d.text((640,505),'kārmamala binds the localized subject into recursive cause and effect',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    # nested filters around bound observer
    filters=[(210,CRIMSON,'āṇava'),(150,INDIGO,'māyīya'),(95,TEAL,'kārma')]
    for r,col,lab in filters:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,155),width=3)
        d.text((cx+r+28,cy-r*.55),lab,font=SMALL_FONT,fill=col)
    draw_glow(im,(cx,cy),34,SLATE,85,10)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(SLATE,200),outline=rgba(INK,120),width=1)
    # surrounding objects
    for i in range(8):
        a=i*2*math.pi/8+t*.05
        x=cx+math.cos(a)*245; y=cy+math.sin(a)*155
        d.ellipse((x-7,y-7,x+7,y+7),fill=rgba(mix(UMBER,SLATE,i/8),150))
    d.text((640,505),'combined, the three veils produce the ordinary bound observer',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    # membranes becoming transparent/open
    vals=[(210,CRIMSON),(150,INDIGO),(95,TEAL)]
    for i,(r,col) in enumerate(vals):
        alpha=int(180*(1-ease_in_out(t)*.72))
        d.arc((cx-r,cy-r*.72,cx+r,cy+r*.72),200,340,fill=rgba(col,alpha),width=3)
        d.arc((cx-r,cy-r*.72,cx+r,cy+r*.72),20,160,fill=rgba(mix(col,WHITE,.65),alpha),width=2)
    draw_glow(im,(cx,cy),40+60*ease_in_out(t),GOLD_LIGHT,130,18)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    # outward recovered rays
    for i in range(10):
        a=i*2*math.pi/10
        p0=(cx+math.cos(a)*60,cy+math.sin(a)*44)
        p1=(cx+math.cos(a)*235,cy+math.sin(a)*155)
        draw_line_glow(im,[p0,p1],mix(GOLD_LIGHT,TEAL,i/10),2,65,5)
    d.text((640,505),'recognition does not destroy the field; it renders the filters transparent',font=SUB_FONT,fill=SLATE,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im)
    cx,cy=W/2,280
    # three translucent membranes opening around original bindu
    for r,col,phase in [(210,CRIMSON,0.0),(150,INDIGO,.12),(95,TEAL,-.12)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(col,105),width=2)
        for i in range(8):
            a=phase+i*2*math.pi/8
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r
            d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,135))
    draw_glow(im,(cx,cy),88,GOLD_LIGHT,145,24)
    d.ellipse((cx-28,cy-28,cx+28,cy+28),fill=rgba(WHITE,255),outline=rgba(GOLD,230),width=2)
    # eye/aperture motif
    d.arc((cx-66,cy-30,cx+66,cy+30),180,360,fill=rgba(GOLD,200),width=3)
    d.arc((cx-66,cy-30,cx+66,cy+30),0,180,fill=rgba(GOLD,200),width=3)
    d.text((640,505),'the three veils become translucent around the original fullness',font=SUB_FONT,fill=SLATE,anchor='mm')


SCENES=[
    Scene('ml01','The Three Veils','An overview of the three-stage constriction of infinite capacity.','Malatraya','Pure consciousness contracts through āṇava, māyīya, and kārma filters.','overview_filters',['overview','malas','constriction'],'overview','three-filter chain',sc01),
    Scene('ml02','Pūrṇatva','The original condition of unrestricted fullness.','Pūrṇatva','Pure consciousness begins as complete capacity without lack.','fullness_field',['fullness','source'],'source','radiant fullness field',sc02),
    Scene('ml03','Āṇavamala','The primordial contraction into smallness and lack.','Āṇavamala','Infinite capacity is constricted into a fragmentary sense of insufficiency.','aperture_contraction',['anava','lack','contraction'],'veil','shrinking aperture',sc03),
    Scene('ml04','Māyīyamala','The single field is divided into subject and object.','Māyīyamala','The sense of lack develops into a split between self and world.','prism_split',['mayiya','duality','subject-object'],'veil','prism division',sc04),
    Scene('ml05','Kārmamala','Action closes into a recursive causal circuit.','Kārmamala','The localized subject is bound into action, consequence, and repetition.','causal_wheel',['karma','action','causality'],'veil','causal feedback wheel',sc05),
    Scene('ml06','The Bound Observer','All three filters combine around the ordinary subject.','Sakala','The three malas generate the normal fragmented field of experience.','nested_filters',['bound observer','three malas'],'process','nested observer field',sc06),
    Scene('ml07','Making the Veils Transparent','Recognition loosens the filters without erasing manifestation.','Śuddhi','Liberation appears as transparency rather than world-destruction.','filter_transparency',['purification','recognition'],'return','opening membranes',sc07),
    Scene('ml08','The Malatraya Seal','The original bindu shines through three translucent membranes.','Mala-cakra','The pack closes with the three veils gathered around recovered fullness.','closing_seal',['seal','summary','malas'],'seal','translucent membrane seal',sc08),
]


def render_scene(scene):
    sdir=FRAMES_ROOT/scene.id
    sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1)
            im=ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,46); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(4*320,2*180),color=PAPER)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
        'project':'Tantrāloka — The Three Primary Veils (Malas)',
        'source_basis':'Conceptual mapping supplied by the user from Tantrāloka: āṇavamala, māyīyamala, and kārmamala as stages of constriction.',
        'style':{
            'family':'optical constriction / filtration cosmography',
            'background':'warm pale field',
            'ink':'slate / umber',
            'accent':'gold, crimson, indigo, teal',
            'materials':['apertures','prisms','translucent membranes','causal chains','observer fields']
        },
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[{
            'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,
            'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'
        } for sc in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={
        'ids':[sc.id for sc in SCENES],
        'titles':{sc.id:sc.title for sc in SCENES},
        'modes':{sc.id:sc.mode for sc in SCENES},
        'theme_clusters':{
            'overview_and_source':['ml01','ml02'],
            'three_veils':['ml03','ml04','ml05'],
            'bondage_and_return':['ml06','ml07','ml08']
        },
        'reusability_notes':{
            'ml01':'Use to introduce the full three-mala structure.',
            'ml02':'Use for fullness, infinite capacity, pure consciousness, or source-field.',
            'ml03':'Use for lack, smallness, contraction, or āṇava limitation.',
            'ml04':'Use for subject-object duality, separation, or māyīya filtering.',
            'ml05':'Use for karma, causal repetition, habit loops, or action-bondage.',
            'ml06':'Use for the compounded bound observer or Sakala condition.',
            'ml07':'Use for purification, transparency, recognition, or liberation.',
            'ml08':'Use as the closing seal for discussions of malas or constriction.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))

    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The Three Primary Veils

## Aim
This pack visualizes the **three malas** as operational filters that constrict infinite consciousness into finite, dualistic, causally bound experience.

## Textual orientation
The pack is based on the user-supplied structural account from the *Tantrāloka*: **āṇavamala**, **māyīyamala**, and **kārmamala**.

## Core doctrinal structure represented
1. **Pūrṇatva** — original fullness and unrestricted capacity
2. **Āṇavamala** — primordial contraction into lack, smallness, and incompleteness
3. **Māyīyamala** — division into subject and object
4. **Kārmamala** — bondage through action and causal consequence
5. **Sakala** — the compounded ordinary observer enclosed by all three
6. **Śuddhi / recognition** — the filters become transparent

## Visual rules
- The malas are filters, contractions, and distortions—not demonic substances.
- Āṇava should feel like narrowing and insufficiency.
- Māyīya should feel like refraction or splitting.
- Kārma should feel recursive and action-bound.
- Liberation should render the filters transparent rather than simply destroy the world.

## Style family
- warm pale field
- gold fullness-source
- crimson contraction
- indigo subject-object refraction
- teal causal structure
- translucent membranes and apertures

## New motifs introduced
- three-filter overview chain
- radiant fullness field
- shrinking aperture
- subject-object prism
- causal feedback wheel
- nested observer filters
- opening transparent membranes
- malatraya seal

## Guardrails
- Do not flatten all three malas into one vague “illusion.”
- Preserve the distinct functions of lack, division, and causal bondage.
- Do not treat manifestation itself as evil.
- Recognition is a change in transparency and identity, not mere deletion of appearances.

## Reuse strategy
- ml01: whole structure
- ml02: source / fullness
- ml03–ml05: the three individual veils
- ml06: compounded bondage
- ml07: purification / recognition
- ml08: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')

    style='''# STYLE EVOLUTION — Three Malas Pack

## Inheritance
This pack keeps the project’s philosophical clarity but shifts into an explicitly optical and mechanical vocabulary of filtering.

## Mala differentiation
This pack emphasizes:
- narrowing apertures
- refracting prisms
- causal loops and chain-links
- layered transparent membranes
- the observer as a field produced by filtering

## New motifs added
1. three-filter chain
2. fullness star-field
3. shrinking āṇava aperture
4. māyīya prism split
5. kārma feedback wheel
6. nested bound-observer membranes
7. membrane-transparency reversal
8. malatraya eye-seal

## New relationships added
- fullness → contraction
- contraction → subject-object division
- division → desire and action
- action → causal repetition
- filtering → bound observer
- recognition → transparency

## New material vocabulary
- white-gold source light
- crimson aperture blades
- indigo prism glass
- teal causal links
- translucent membrane rings

## Deprecated clichés
- generic “three dark veils” stacked as identical rectangles
- treating all malas as interchangeable darkness
- liberation shown only as explosive destruction

## Distinct closing seal
The closing seal is a **three-membrane eye aperture** around the recovered luminous bindu.

## Recommendation for next pack
A sixth item was not included in the supplied list. The next pack can proceed from the next framework you provide.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')

    readme=f'''# Tantrāloka — The Three Primary Veils (Malas) Pack

Included files:
- malas_three_veils_animation.mp4
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
    combined=ROOT/'malas_three_veils_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))


def make_zip():
    zpath=ROOT/'malas_three_veils_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['malas_three_veils_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True)
        render_scene(sc)
    concat_file=ROOT/'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'malas_three_veils_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
