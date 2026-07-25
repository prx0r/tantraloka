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

# Directional temple palette
PARCHMENT = (242, 236, 224)
PARCHMENT_LIGHT = (249, 246, 238)
INK = (39, 36, 35)
UMBER = (86, 68, 54)
GOLD = (203, 159, 77)
GOLD_LIGHT = (243, 211, 132)
EAST = (211, 126, 62)      # creation / sunrise
SOUTH = (155, 58, 67)      # mantra / defense
WEST = (86, 130, 126)      # reabsorption / body
NORTH = (72, 76, 124)      # transcendence / Krama
CENTER = (231, 218, 185)
SLATE = (112, 116, 127)
MIST = (184, 181, 174)
WHITE = (252, 250, 245)
BLACK = (22, 22, 24)
ROSE = (188, 119, 136)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 12)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def rgba(c, a=255):
    return (*c[:3], int(a))


def ground(seed: int):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(PARCHMENT, dtype=np.float32)
    coarse = rng.normal(0, 1, (42, 76)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg = cimg.resize((W,H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx = np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*6,0,16)
    base -= vign[...,None]*0.7
    # directional halos
    east = np.exp(-(((xx-W*0.72)/(W*0.18))**2 + ((yy-H*0.42)/(H*0.24))**2)*2.8)
    west = np.exp(-(((xx-W*0.28)/(W*0.18))**2 + ((yy-H*0.42)/(H*0.24))**2)*2.8)
    north = np.exp(-(((xx-W*0.50)/(W*0.22))**2 + ((yy-H*0.20)/(H*0.16))**2)*2.8)
    south = np.exp(-(((xx-W*0.50)/(W*0.22))**2 + ((yy-H*0.66)/(H*0.18))**2)*2.8)
    for i in range(3):
        base[...,i] += east * (15 if i<2 else 5)
        base[...,i] += west * (8 if i!=1 else 13)
        base[...,i] += north * (8 if i<2 else 15)
        base[...,i] += south * (14 if i==0 else 6)
    return Image.fromarray(np.uint8(np.clip(base,0,255)), 'RGB').convert('RGBA')


def layer():
    return Image.new('RGBA',(W,H),(0,0,0,0))


def draw_glow(im,xy,radius,color,alpha=145,blur=16):
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
        x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        draw.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42), fill=rgba(outer,145), outline=rgba(inner,180), width=1)
    draw.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42), fill=rgba(inner,120), outline=rgba(outer,220), width=2)


def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28), outline=rgba(UMBER,120), width=2)
    d.rectangle((42,42,W-42,H-42), outline=rgba(GOLD,88), width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]:
        draw_rosette(d,x,y,22,ROSE,GOLD)


def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34), radius=14, fill=(248,244,235,218), outline=rgba(UMBER,70), width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=UMBER)
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=NORTH)


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
    pts=[p1,(p1[0]-math.cos(ang-0.5)*s,p1[1]-math.sin(ang-0.5)*s),(p1[0]-math.cos(ang+0.5)*s,p1[1]-math.sin(ang+0.5)*s)]
    draw.polygon(pts,fill=rgba(color,230))


def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(20,78))))
    im.alpha_composite(ov)


def draw_temple_gate(draw,cx,cy,w,h,col):
    draw.rectangle((cx-w/2,cy-h/2,cx+w/2,cy+h/2), outline=rgba(col,190), width=3)
    draw.arc((cx-w/2,cy-h/2,cx+w/2,cy+h/2),180,360,fill=rgba(col,190),width=3)
    draw.line((cx-w/2+22,cy+h/2,cx-w/2+22,cy-h/2+24),fill=rgba(col,140),width=2)
    draw.line((cx+w/2-22,cy+h/2,cx+w/2-22,cy-h/2+24),fill=rgba(col,140),width=2)


def draw_vowel_ring(draw,cx,cy,r,col):
    letters=['अ','आ','इ','ई','उ','ऊ','ऋ','ए','ऐ','ओ','औ','अः']
    for i,ch in enumerate(letters):
        a=-math.pi/2+i*2*math.pi/len(letters)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.74
        draw.text((x,y),ch,font=DEVA_MED,fill=col,anchor='mm')


def draw_mantra_grid(draw,x0,y0,rows,cols,col):
    seeds=['ॐ','ह्रीं','श्रीं','क्लीं','हं','सौः']
    idx=0
    for r in range(rows):
        for c in range(cols):
            x=x0+c*100; y=y0+r*72
            draw.rounded_rectangle((x-34,y-26,x+34,y+26),radius=12,outline=rgba(col,170),fill=rgba(mix(PARCHMENT_LIGHT,col,.05),65),width=2)
            draw.text((x,y),seeds[idx%len(seeds)],font=DEVA_MED,fill=col,anchor='mm')
            idx+=1


def draw_vessel(draw,cx,cy,w,h,col):
    draw.arc((cx-w/2,cy-h/2,cx+w/2,cy+h/2),0,180,fill=rgba(col,210),width=3)
    draw.line((cx-w/2,cy,cx-w/2+20,cy+h/2),fill=rgba(col,210),width=3)
    draw.line((cx+w/2,cy,cx+w/2-20,cy+h/2),fill=rgba(col,210),width=3)
    draw.arc((cx-w/2+20,cy+h/2-20,cx+w/2-20,cy+h/2+20),0,180,fill=rgba(col,210),width=3)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    draw_glow(im,(cx,cy),46,GOLD_LIGHT,120,14)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    dirs=[('EAST',EAST,(1010,280)),('SOUTH',SOUTH,(640,455)),('WEST',WEST,(270,280)),('NORTH',NORTH,(640,105))]
    for lab,col,(x,y) in dirs:
        pts=partial_polyline(bezier((cx,cy),(lerp(cx,x,.35),lerp(cy,y,.25)),(lerp(cx,x,.72),lerp(cy,y,.78)),(x,y),80),smoothstep(.05,.82,t))
        if len(pts)>1:
            draw_line_glow(im,pts,col,4,115,7); draw_arrowhead(d,pts[-2],pts[-1],col,1.0)
        d.rounded_rectangle((x-86,y-30,x+86,y+30),radius=14,outline=rgba(col,190),fill=rgba(mix(PARCHMENT_LIGHT,col,.05),70),width=2)
        d.text((x,y),lab,font=TERM_FONT,fill=col,anchor='mm')
    d.text((cx,cy+58),'CENTRAL AXIS',font=SMALL_FONT,fill=UMBER,anchor='mm')
    d.text((640,515),'four transmissions step down around one unmoving pivot',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    draw_glow(im,(cx-180,cy),40,GOLD_LIGHT,110,12)
    d.ellipse((cx-196,cy-16,cx-164,cy+16),fill=rgba(WHITE,255),outline=rgba(EAST,220),width=2)
    draw_vowel_ring(d,cx+90,cy,160,EAST)
    for i in range(9):
        a=-math.pi/2+i*2*math.pi/9
        pts=partial_polyline(bezier((cx-150,cy),(cx-60,cy-40),(cx+10+math.cos(a)*80,cy+math.sin(a)*50),(cx+90+math.cos(a)*150,cy+math.sin(a)*110),80),smoothstep(.04+i*.03,.78+i*.02,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(EAST,GOLD_LIGHT,i/9),2,85,5)
    d.text((640,515),'the eastern stream projects creation through the vowel-field',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im)
    draw_temple_gate(d,640,250,420,250,SOUTH)
    draw_mantra_grid(d,490,220,2,4,SOUTH)
    # protective perimeter
    for i in range(4):
        off=28+i*18
        d.rounded_rectangle((370-off,135-off,910+off,390+off),radius=24,outline=rgba(mix(SOUTH,GOLD,i/4),95),width=2)
    draw_glow(im,(640,250),36,SOUTH,85,12)
    d.text((640,450),'mantra architecture stabilizes and protects lineage',font=TERM_FONT,fill=SOUTH,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    draw_vessel(d,cx,cy,260,220,WEST)
    # inputs enter, transform, rise
    inputs=[(270,210,EAST),(270,285,GOLD),(270,360,ROSE)]
    for i,(x,y,col) in enumerate(inputs):
        d.ellipse((x-10,y-10,x+10,y+10),fill=rgba(col,190))
        pts=partial_polyline(bezier((x,y),(390,y),(450,cy+(i-1)*35),(510,cy+(i-1)*20),80),smoothstep(.04+i*.09,.82+i*.04,t))
        if len(pts)>1: draw_line_glow(im,pts,col,3,95,6)
    # transformed upward output
    pts=partial_polyline(bezier((cx,cy+70),(cx,cy+20),(cx,175),(cx,120),90),smoothstep(.16,.94,t))
    if len(pts)>1:
        draw_line_glow(im,pts,WEST,4,120,7); draw_arrowhead(d,pts[-2],pts[-1],WEST,1.0)
    draw_glow(im,(cx,cy),44,WEST,90,14)
    d.text((640,480),'the body becomes a Kaula vessel of reabsorption and transformation',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,295
    # twelve kalis rising north
    for i in range(12):
        y=470-i*28
        x=cx+math.sin(i*.8+t*.1)*35
        r=9 if i<11 else 14
        col=mix(NORTH,GOLD_LIGHT,i/11)
        draw_glow(im,(x,y),r*1.8,col,75,8)
        d.ellipse((x-r,y-r,x+r,y+r),outline=rgba(col,210),fill=rgba(mix(PARCHMENT_LIGHT,col,.08),70),width=2)
        if i<11:
            pts=partial_polyline(bezier((x,y-r),(x+10,y-10),(cx+math.sin((i+1)*.8+t*.1)*35,y-18),(cx+math.sin((i+1)*.8+t*.1)*35,y-28+r),40),smoothstep(.04+i*.05,.72+i*.04,t))
            if len(pts)>1: draw_line_glow(im,pts,col,2,70,4)
    draw_glow(im,(cx,125),48,GOLD_LIGHT,105,14)
    d.ellipse((cx-18,107,cx+18,143),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'the northern Krama stream devours and transcends the other directions',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # compass seal
    d.ellipse((cx-210,cy-210,cx+210,cy+210),outline=rgba(GOLD,145),width=2)
    d.ellipse((cx-138,cy-138,cx+138,cy+138),outline=rgba(SLATE,105),width=2)
    dirs=[('Pūrva',EAST,(cx+210,cy)),('Dakṣiṇa',SOUTH,(cx,cy+210)),('Paścima',WEST,(cx-210,cy)),('Uttara',NORTH,(cx,cy-210))]
    for lab,col,(x,y) in dirs:
        draw_glow(im,(x,y),28,col,95,10)
        d.ellipse((x-14,y-14,x+14,y+14),fill=rgba(WHITE,255),outline=rgba(col,220),width=2)
        d.text((x,y+36 if y<=cy else y-36),lab,font=SMALL_FONT,fill=col,anchor='mm')
        draw_line_glow(im,[(cx,cy),(x,y)],col,3,100,6)
    draw_glow(im,(cx,cy),50,CENTER,130,14)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(WHITE,255),outline=rgba(GOLD,230),width=2)
    d.text((cx,cy+1),'बिन्दु',font=DEVA_MED,fill=UMBER,anchor='mm')
    d.text((640,525),'one central pivot coordinates creation, maintenance, reabsorption, and transcendence',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
    Scene('am01','The Four Āmnāyas','A directional map of four transmission streams around a central pivot.','Āmnāya-cakra','Revelation descends through four directional modes coordinated by one center.','overview_compass',['overview','directions','transmission'],'overview','four-way compass tree',sc01),
    Scene('am02','Pūrvāmnāya','The eastern stream of creation and vowel projection.','Pūrvāmnāya','Objective forms emerge from the source through the vowel-field.','east_vowels',['east','creation','vowels'],'stream','vowel emission ring',sc02),
    Scene('am03','Dakṣiṇāmnāya','The southern stream of mantra, stability, and protection.','Dakṣiṇāmnāya','Mantric architecture stabilizes lineages and ritual order.','south_mantra_gate',['south','mantra','protection'],'stream','mantra temple grid',sc03),
    Scene('am04','Paścimāmnāya','The western stream of embodied Kaula reabsorption.','Paścimāmnāya','The body transforms physical inputs into integrated spiritual force.','west_vessel',['west','Kaula','reabsorption'],'stream','alchemical body-vessel',sc04),
    Scene('am05','Uttarāmnāya','The northern stream of Krama transcendence.','Uttarāmnāya','The apex stream devours and transcends the other directions through the Kālī sequence.','north_ascent',['north','Krama','transcendence'],'stream','twelve-node ascent',sc05),
    Scene('am06','The Āmnāya Seal','The four streams resolve into a single directional transmission seal.','Āmnāya-maṇḍala','Creation, maintenance, reabsorption, and transcendence revolve around one bindu.','closing_seal',['seal','compass','summary'],'seal','compass mandala',sc06),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1)
            im=ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,44); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(3*320,2*180),color=PARCHMENT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%3)*320,(idx//3)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def write_metadata():
    manifest={
        'project':'Tantrāloka — The Four Directional Transmission Streams (Āmnāyas)',
        'source_basis':'Conceptual mapping supplied by the user from Tantrāloka Chapter 29.',
        'style':{'family':'directional temple-compass cosmography','background':'warm parchment with four directional halos','ink':'umber and slate','accent':'east orange, south crimson, west teal, north indigo, central gold','materials':['compass axes','vowel ring','mantra gate','Kaula vessel','Krama ascent','directional seal']},
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={
        'ids':[s.id for s in SCENES],
        'titles':{s.id:s.title for s in SCENES},
        'modes':{s.id:s.mode for s in SCENES},
        'theme_clusters':{'overview':['am01'],'directional_streams':['am02','am03','am04','am05'],'closing_seal':['am06']},
        'reusability_notes':{
            'am01':'Use for overview of the four āmnāyas or directional transmission systems.',
            'am02':'Use for eastern creation, vowels, emission, or first projection.',
            'am03':'Use for southern mantra systems, protection, stabilization, or ritual lineage.',
            'am04':'Use for western Kaula practice, embodiment, transformation, or reabsorption.',
            'am05':'Use for northern Krama, transcendence, Kālī sequence, or terminal absorption.',
            'am06':'Use as a closing seal for directional lineage maps or fourfold transmission systems.'
        }
    }
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / The Four Āmnāyas

## Aim
This pack visualizes the **four directional transmission streams (Āmnāyas)** as a functional map of revelation stepping down around a central pivot.

## Textual orientation
The pack follows the user-supplied conceptual summary from **Tantrāloka, Chapter 29**.

## Core structure
1. **Pūrvāmnāya — East**: creation, vowel projection, emergence of objective forms
2. **Dakṣiṇāmnāya — South**: maintenance, mantra structure, protection of lineages
3. **Paścimāmnāya — West**: Kaula embodiment, chemical / bodily integration, reabsorption
4. **Uttarāmnāya — North**: Krama transcendence, the twelve Kālīs, terminal absorption
5. **Central axis**: the coordinating pivot around which all four streams function

## Visual rules
- Preserve the directional logic clearly.
- Each stream needs a distinct symbolic language.
- East should feel emissive and phonemic.
- South should feel architectural, mantric, and protective.
- West should feel embodied, vessel-like, and transformative.
- North should feel vertical, austere, and terminally absorptive.
- The center should remain stable while all four streams move around it.

## Style family
- warm parchment compass field
- east orange / gold
- south crimson
- west teal
- north indigo
- central ivory-gold bindu

## New motifs introduced
- four-direction transmission compass
- vowel projection ring
- mantra-protection temple gate
- Kaula transformation vessel
- twelve-node Krama ascent
- directional bindu seal

## Guardrails
- Do not collapse the āmnāyas into mere geography.
- Their directions indicate functional transmission streams, not just compass locations.
- Avoid making the western Kaula stream purely sensual or the northern Krama stream purely destructive.
- The final seal should show differentiation around a single source.

## Reuse strategy
- am01: overview
- am02–am05: four individual streams
- am06: closing seal
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Āmnāyas Pack

## Inheritance
This pack inherits the manuscript cosmography of the series while introducing directional temple architecture.

## Āmnāya differentiation
It emphasizes:
- compass orientation
- four color-coded transmission logics
- direction as function
- a stable central pivot
- lineage and revelation rather than ontological hierarchy

## New motifs added
1. central four-way compass
2. eastern vowel-projection ring
3. southern mantra gate
4. western Kaula vessel
5. northern twelve-node ascent
6. directional bindu seal

## New relationships added
- center → four directional transmissions
- vowel emergence → creation
- mantra architecture → maintenance and protection
- embodiment → transformation and reabsorption
- Kālī sequence → transcendence

## New material vocabulary
- sunrise orange
- protective crimson architecture
- teal vessel geometry
- indigo vertical ascent
- ivory-gold central bindu

## Deprecated clichés
- generic compass rose with no doctrinal function
- identical symbols repeated in four quadrants
- reducing āmnāyas to simple cardinal directions

## Distinct closing seal
The closing seal is an **Āmnāya-maṇḍala** with four directional nodes revolving around a central bindu.

## Recommendation for next pack
- The Seven Types of Knowing Subjects (Pramātṛ Taxonomy)
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — The Four Directional Transmission Streams (Āmnāyas) Pack

Included files:
- amnayas_four_streams_animation.mp4
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
    combined=ROOT/'amnayas_four_streams_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))


def make_zip():
    zpath=ROOT/'amnayas_four_streams_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['amnayas_four_streams_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')):
            zf.write(mp4,arcname=f'scenes/{mp4.name}')


def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat_file=ROOT/'concat_list.txt'
    concat_file.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'amnayas_four_streams_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat_file),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
