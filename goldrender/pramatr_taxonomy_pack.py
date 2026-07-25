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

# observer / filtration palette
NIGHT = (19, 21, 29)
OBSIDIAN = (28, 30, 38)
CHARCOAL = (47, 49, 58)
ASH = (132, 137, 149)
SILVER = (206, 213, 225)
IVORY = (244, 242, 236)
WHITE = (252, 250, 246)
CRIMSON = (153, 49, 64)
VIOLET = (121, 103, 166)
INDIGO = (65, 80, 140)
TEAL = (86, 143, 146)
GREEN = (101, 149, 111)
GOLD = (205, 164, 87)
GOLD_LIGHT = (245, 215, 142)
ROSE = (188, 111, 140)
BLUE_GREY = (115, 130, 158)
MIST = (174, 184, 201)
SLATE = (103, 112, 130)
SMOKE = (78, 81, 93)
BLACK = (15, 15, 18)
DEEP_INDIGO = (45, 55, 100)

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

def lerp(a,b,t):
    return a + (b-a)*clamp(t)

def mix(c1,c2,t):
    t=clamp(t)
    return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))

def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)

def ease_in_out(t):
    t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)

def ease_out_cubic(t):
    t=clamp(t); return 1-(1-t)**3

def rgba(c,a=255):
    return (*c[:3], int(a))


def observer_ground(seed:int):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32)
    base[:] = np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.2 + fine[...,None]*1.15
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    vign=np.clip((dx*dx+dy*dy)*19,0,27)
    base -= vign[...,None]
    top=np.exp(-(((xx-W/2)/(W*0.28))**2+((yy-H*0.18)/(H*0.13))**2)*2.8)
    mid=np.exp(-(((xx-W/2)/(W*0.34))**2+((yy-H*0.47)/(H*0.25))**2)*2.4)
    for i in range(3):
        base[...,i]+=top*(28 if i<2 else 24)
        base[...,i]+=mid*(8 if i!=2 else 18)
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
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def draw_rosette(draw,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.42,y-r*.42,x+r*.42,y+r*.42),fill=rgba(outer,140),outline=rgba(inner,180),width=1)
    draw.ellipse((cx-r*.42,cy-r*.42,cx+r*.42,cy+r*.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(ASH,110),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,85),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,VIOLET,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(18,20,28,202),outline=rgba(MIST,65),width=1)
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
    f=amount*(len(points)-1); idx=int(f); frac=f-idx; out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def draw_arrowhead(draw,p0,p1,color,scale=1.0):
    ang=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); s=12*scale
    pts=[p1,(p1[0]-math.cos(ang-.5)*s,p1[1]-math.sin(ang-.5)*s),(p1[0]-math.cos(ang+.5)*s,p1[1]-math.sin(ang+.5)*s)]
    draw.polygon(pts,fill=rgba(color,230))
def dust(im,seed,n=72):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.2))
        c=mix(MIST,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(22,78))))
    im.alpha_composite(ov)
def draw_silhouette(draw,cx,cy,scale=1.0,col=ASH):
    draw.ellipse((cx-15*scale,cy-64*scale,cx+15*scale,cy-34*scale),fill=rgba(col,190))
    draw.polygon([(cx-38*scale,cy+22*scale),(cx-27*scale,cy-18*scale),(cx-14*scale,cy-35*scale),(cx+14*scale,cy-35*scale),(cx+27*scale,cy-18*scale),(cx+38*scale,cy+22*scale)],fill=rgba(col,160))
def draw_eye(draw,cx,cy,scale=1.0,col=GOLD_LIGHT):
    box=(cx-68*scale,cy-32*scale,cx+68*scale,cy+32*scale)
    draw.arc(box,180,360,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.arc(box,0,180,fill=rgba(col,220),width=max(1,int(3*scale)))
    draw.ellipse((cx-14*scale,cy-14*scale,cx+14*scale,cy+14*scale),fill=rgba(col,210))

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable[[Image.Image,float],None]

# scenes

def sc01(im,t):
    d=ImageDraw.Draw(im); cx=W/2
    levels=[('Śiva',WHITE),('Mantramaheśvara',GOLD_LIGHT),('Mantreśvara',GOLD),('Mantra',TEAL),('Vijñānākala',INDIGO),('Pralayākala',VIOLET),('Sakala',CRIMSON)]
    ys=[110,170,230,300,370,440,500]
    for i,((lab,col),y) in enumerate(zip(levels,ys)):
        r=22+int((6-i)*2)
        d.ellipse((cx-r,y-r,cx+r,y+r),outline=rgba(col,220),fill=rgba(mix(NIGHT,col,.12),80),width=2)
        d.text((cx+110,y-5),lab,font=SMALL_FONT,fill=col)
        if i<len(levels)-1:
            pts=partial_polyline(bezier((cx,y+r),(cx-30,y+38),(cx+30,ys[i+1]-38),(cx,ys[i+1]-r),70),smoothstep(.03+i*.07,.7+i*.05,t))
            if len(pts)>1:
                draw_line_glow(im,pts,mix(col,levels[i+1][1],.5),3,100,6); draw_arrowhead(d,pts[-2],pts[-1],mix(col,levels[i+1][1],.5),.8)
    # filter count bars
    for i,y in enumerate(ys[::-1]):
        count=max(0,3-i//2)
        for j in range(count):
            x=390+j*26
            d.rounded_rectangle((x,y-10,x+12,y+10),radius=5,fill=rgba([CRIMSON,VIOLET,SLATE][j],160))
    d.text((420,520),'filters diminish upward',font=SMALL_FONT,fill=ASH,anchor='mm')
    d.text((640, 548), 'seven grades of subjectivity defined by the veils still operating', font=SUB_FONT, fill=MIST, anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,292
    # cage and three veils
    for i,col in enumerate([CRIMSON,VIOLET,SLATE]):
        inset=40+i*34
        d.rounded_rectangle((cx-220+inset,cy-145+inset*.3,cx+220-inset,cy+145-inset*.3),radius=20,outline=rgba(col,170),width=3)
    draw_silhouette(d,cx,cy+36,1.2,ASH)
    for i in range(10):
        x=390+i*56
        d.line((x,160,x+20,430),fill=rgba(ASH,55),width=1)
    d.text((300,184),'āṇava',font=TERM_FONT,fill=CRIMSON)
    d.text((300,222),'māyīya',font=TERM_FONT,fill=VIOLET)
    d.text((300,260),'kārma',font=TERM_FONT,fill=SLATE)
    d.text((640, 505), 'the bound subject perceives fragmented objects through all three veils', font=SUB_FONT, fill=MIST, anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    # objectless void subject
    for i in range(8):
        r=54+i*26
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(mix(VIOLET,SMOKE,i/8),95),width=2)
    draw_glow(im,(cx,cy),72,VIOLET,85,22)
    d.ellipse((cx-28,cy-28,cx+28,cy+28),fill=rgba(BLACK,255),outline=rgba(VIOLET,200),width=2)
    draw_silhouette(d,cx,cy+70,.8,CHARCOAL)
    d.text((640, 505), 'only primordial limitation remains within uniform cosmic darkness', font=SUB_FONT, fill=MIST, anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    # isolated luminous orb, no object field
    draw_glow(im,(cx,cy),78,INDIGO,110,20)
    d.ellipse((cx-86,cy-86,cx+86,cy+86),outline=rgba(INDIGO,180),width=2)
    d.ellipse((cx-28,cy-28,cx+28,cy+28),fill=rgba(WHITE,250),outline=rgba(INDIGO,220),width=2)
    d.text((cx,cy),'I',font=TERM_FONT,fill=DEEP_INDIGO if 'DEEP_INDIGO' in globals() else INDIGO,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12; x=cx+math.cos(a)*175; y=cy+math.sin(a)*110
        d.ellipse((x-5,y-5,x+5,y+5),outline=rgba(ASH,70),width=1)
    d.text((640, 505), 'pure subjectivity remains, but without a manifested objective world', font=SUB_FONT, fill=MIST, anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    # mantra form subject: faint I/This symmetry
    draw_glow(im,(cx,cy),54,TEAL,105,16)
    d.ellipse((cx-20,cy-20,cx+20,cy+20),fill=rgba(WHITE,255),outline=rgba(TEAL,220),width=2)
    words=['ॐ','ह्रीं','श्रीं','हं','सौः','क्लीं']
    for i,w in enumerate(words):
        a=-math.pi/2+i*2*math.pi/6+t*.05
        x=cx+math.cos(a)*155; y=cy+math.sin(a)*102
        d.ellipse((x-30,y-30,x+30,y+30),outline=rgba(TEAL,170),fill=rgba(mix(NIGHT,TEAL,.1),70),width=2)
        d.text((x,y),w,font=DEVA_SMALL,fill=TEAL,anchor='mm')
        draw_line_glow(im,[(cx,cy),(x,y)],TEAL,2,70,5)
    d.text((370,184),'I',font=TERM_FONT,fill=IVORY)
    d.text((880,184),'This',font=TERM_FONT,fill=TEAL)
    d.text((640, 505), 'the universe is self-expression, though a faint conceptual boundary remains', font=SUB_FONT, fill=MIST, anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    # objective ideas commanded as internal lattice
    d.rounded_rectangle((300,150,980,420),radius=24,outline=rgba(GOLD,160),width=2)
    pts=[]
    for r in range(3):
        for c in range(6):
            x=360+c*112; y=205+r*82; pts.append((x,y))
            d.ellipse((x-10,y-10,x+10,y+10),fill=rgba(mix(GOLD,ROSE,(r*6+c)/18),180),outline=rgba(GOLD,120))
    for p in pts:
        draw_line_glow(im,[(cx,cy),p],GOLD,1,55,4)
    draw_eye(d,cx,cy,.7,GOLD_LIGHT)
    d.text((640, 505), 'pure objectivity appears as an internally commanded field of cosmic ideas', font=SUB_FONT, fill=MIST, anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,286
    # universe absorbed into I
    d.text((cx,cy),'I',font=ImageFont.truetype(FONT_SERIF_BOLD,96),fill=GOLD_LIGHT,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14+t*.03; r=190-i*3
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
        d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(mix(GOLD_LIGHT,ROSE,i/14),190))
        pts=partial_polyline(bezier((x,y),(x*.7+cx*.3,y),(cx+math.cos(a)*50,cy+math.sin(a)*34),(cx,cy),70),smoothstep(.06,.86,t))
        if len(pts)>1: draw_line_glow(im,pts,mix(GOLD_LIGHT,ROSE,i/14),2,75,5)
    draw_glow(im,(cx,cy),90,GOLD_LIGHT,100,22)
    d.text((640, 505), 'objectivity is fully absorbed into the declaration: I am this universe', font=SUB_FONT, fill=MIST, anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,282
    # absolute subject
    draw_glow(im,(cx,cy),110,WHITE,140,28)
    for r,col in [(42,WHITE),(88,GOLD_LIGHT),(150,SILVER),(218,ASH)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(col,135),width=2)
    d.ellipse((cx-26,cy-26,cx+26,cy+26),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    for i in range(20):
        a=i*2*math.pi/20
        d.line((cx+math.cos(a)*165,cy+math.sin(a)*165,cx+math.cos(a)*230,cy+math.sin(a)*230),fill=rgba(SILVER,80),width=1)
    d.text((640, 505), 'no category, boundary, or filtering remains in the absolute subject', font=SUB_FONT, fill=MIST, anchor='mm')

def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    # closing seal: seven membranes transparent toward center
    cols=[CRIMSON,VIOLET,INDIGO,TEAL,GOLD, GOLD_LIGHT, WHITE]
    radii=[230,195,160,128,98,68,34]
    for i,(r,col) in enumerate(zip(radii,cols)):
        d.ellipse((cx-r,cy-r*.76,cx+r,cy+r*.76),outline=rgba(col,155),width=2)
        d.text((cx+r+16,cy-r*.3),str(7-i),font=TINY_FONT,fill=col)
    draw_glow(im,(cx,cy),72,WHITE,130,22)
    d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=rgba(WHITE,255),outline=rgba(GOLD_LIGHT,220),width=2)
    # one eye across the full field
    draw_eye(d,cx,cy,1.6,GOLD_LIGHT)
    d.text((640, 505), 'the seven observers resolve into one field of progressively unfiltered awareness', font=SUB_FONT, fill=MIST, anchor='mm')

SCENES=[
    Scene('pr01','The Seven Knowing Subjects','An overview of subjectivity from total bondage to absolute freedom.','Pramātṛ-saptaka','Seven grades of observer are ordered by the filters that remain active.','overview_filtration',['overview','subjects','filters'],'overview','vertical membrane taxonomy',sc01),
    Scene('pr02','Sakala','The fully bound subject beneath Māyā.','Sakala','All three malas restrict awareness into fragmented object-perception.','bound_cage',['bound','three malas','objects'],'subject','triple veil cage',sc02),
    Scene('pr03','Pralayākala','The voided subject in cosmic dissolution.','Pralayākala','Only primordial limitation remains within objectless darkness.','void_subject',['void','sleep','anava'],'subject','dark concentric void',sc03),
    Scene('pr04','Vijñānākala','The isolated subject at the threshold of Māyā.','Vijñānākala','Pure subjectivity remains without a projected world.','isolated_subject',['isolation','pure subject'],'subject','isolated luminous orb',sc04),
    Scene('pr05','Mantra','The form-subject of Śuddhavidyā.','Mantra','The universe is experienced as self-expression with a faint conceptual distinction.','mantra_subject',['mantra','form','suddhavidya'],'subject','mantra orbit field',sc05),
    Scene('pr06','Mantreśvara','The lord of formulas at Īśvara.','Mantreśvara','Pure objectivity is held as an internally commanded field of ideas.','lord_of_formulas',['lord','isvara','ideas'],'subject','command lattice',sc06),
    Scene('pr07','Mantramaheśvara','The great lord anchored in Sadāśiva.','Mantramaheśvara','The whole universe is absorbed into the dominant I-consciousness.','great_lord',['sadasiva','I am universe'],'subject','universe absorbed into I',sc07),
    Scene('pr08','Śiva','The absolute subject without filters.','Śiva','No boundaries, categories, or constrictions remain.','absolute_subject',['absolute','freedom','shiva'],'subject','radiant unfiltered field',sc08),
    Scene('pr09','The Pramātṛ Seal','Seven observer-fields resolving into one awareness.','Pramātṛ-cakra','The taxonomy closes as a contemplative map of progressive transparency.','closing_seal',['seal','summary','observer'],'seal','seven transparent membranes',sc09),
]


def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    if not all(p.exists() and p.stat().st_size>1000 for p in expected):
        for i,path in enumerate(expected):
            if path.exists() and path.stat().st_size>1000: continue
            t=i/max(1,NFRAMES-1); im=observer_ground(SEED+hash(scene.id)%10000+i)
            border(im); dust(im,SEED+i,66); scene.draw_fn(im,t); footer(im,scene.title,scene.subtitle,scene.term)
            im.convert('RGB').save(path,quality=95)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    sheet=Image.new('RGB',(4*320,3*180),color=NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={
        'project':'Tantrāloka — The Seven Types of Knowing Subjects (Pramātṛ Taxonomy)',
        'source_basis':'Conceptual taxonomy supplied by the user from Tantrāloka Chapters 1 and 9.',
        'style':{'family':'observer-field filtration cosmography','background':'dark stratified field','ink':'silver and mist','accent':'crimson, violet, indigo, teal, gold, white','materials':['veils','glass membranes','observer cages','command lattices','radiant apertures']},
        'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':round(len(SCENES)*DURATION,2),
        'scenes':[{'id':sc.id,'title':sc.title,'subtitle':sc.subtitle,'mode':sc.mode,'summary':sc.summary,'group':sc.group,'technique_notes':sc.technique,'tags':sc.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{sc.id}.mp4'} for sc in SCENES]
    }
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[sc.id for sc in SCENES],'titles':{sc.id:sc.title for sc in SCENES},'modes':{sc.id:sc.mode for sc in SCENES},'theme_clusters':{'overview':['pr01'],'mayic_subjects':['pr02','pr03','pr04'],'pure_subjects':['pr05','pr06','pr07','pr08'],'seal':['pr09']},'reusability_notes':{
        'pr01':'Use to introduce the whole pramātṛ taxonomy or progressive filtering.',
        'pr02':'Use for bondage, fragmentation, three malas, or heavily filtered cognition.',
        'pr03':'Use for cosmic dissolution, deep sleep subjectivity, or objectless void.',
        'pr04':'Use for isolated subjectivity without world-manifestation.',
        'pr05':'Use for Śuddhavidyā, mantra-subjectivity, or faint I/This distinction.',
        'pr06':'Use for Īśvara-level sovereignty or command over cosmic ideas.',
        'pr07':'Use for Sadāśiva, I-am-the-universe, or absorption of objectivity.',
        'pr08':'Use for unfiltered absolute subjectivity or Śiva.',
        'pr09':'Use as a closing seal for graded observer-fields or liberation through transparency.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Tantrāloka / Pramātṛ Taxonomy

## Aim
This pack visualizes the **seven types of knowing subjects** as progressive degrees of filtering.

## Source orientation
The pack follows the user-supplied conceptual taxonomy from *Tantrāloka*, Chapters 1 and 9. It preserves that structure rather than attempting a full textual-critical reconstruction.

## Seven observers
1. **Sakala** — bound by āṇava, māyīya, and kārma malas
2. **Pralayākala** — objectless void-subject retaining primordial limitation
3. **Vijñānākala** — isolated pure subject without an objective world
4. **Mantra** — Śuddhavidyā-level subject with faint I/This distinction
5. **Mantreśvara** — Īśvara-level lord of cosmic formulas and ideas
6. **Mantramaheśvara** — Sadāśiva-level great lord: “I am this universe”
7. **Śiva** — absolute, unfiltered subject

## Visual rules
- Show filters becoming progressively transparent upward.
- Avoid a plain seven-rung ladder as the only composition.
- Sakala should feel caged by multiple overlapping membranes.
- Pralayākala should feel voided, not liberated.
- Vijñānākala should feel pure yet isolated.
- Mantra-level scenes should introduce active mantra-form and sovereignty.
- Śiva should be radiant and boundaryless without becoming visually empty.

## New motifs
- triple-veil observer cage
- objectless dissolution field
- isolated luminous subject orb
- mantra-subject constellation
- commanded idea lattice
- universe absorbed into I
- absolute observer radiance
- seven-membrane closing seal

## Guardrails
- Do not confuse reduced filtering with simple moral ranking.
- Pralayākala and Vijñānākala are not equivalent to final liberation.
- Keep the classification tied to modes of cognition and remaining veils.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Pramātṛ Taxonomy Pack

## Differentiation
This pack shifts from directional and breath-based mechanics into **observer-field filtration**.

## New symbols
1. triple membrane cage
2. dissolution void
3. isolated subject orb
4. mantra orbit constellation
5. sovereign idea lattice
6. universe collapsing into I
7. absolute radiant observer
8. seven transparent closing membranes

## New relationships
- all three malas → fragmented perception
- objectless void → retained primordial limitation
- isolated subject → absence of world projection
- faint I/This distinction → mantra subject
- objective idea-field → lordly command
- world → absorption into I
- filters → complete transparency

## Material vocabulary
- obsidian field
- stained-glass membranes
- silver observer apertures
- mantra-light
- gold sovereign lattices
- white absolute radiance

## Closing seal
A **seven-membrane observer seal** in which colored filters become transparent toward a white central eye.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'''# Tantrāloka — The Seven Types of Knowing Subjects Pack

Included files:
- pramatr_taxonomy_animation.mp4
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

Render with:
```bash
python render_pack.py
```
The renderer is resume-safe.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')

def validate_outputs():
    combined=ROOT/'pramatr_taxonomy_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'pramatr_taxonomy_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['pramatr_taxonomy_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'pramatr_taxonomy_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__': render_all()
