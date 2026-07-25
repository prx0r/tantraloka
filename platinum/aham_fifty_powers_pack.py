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
SEED = 50500

# Reflective phonemic palette
PAPER = (247, 245, 239)
PAPER_LIGHT = (252, 250, 245)
INK = (34, 38, 49)
UMBER = (84, 71, 59)
SILVER = (212, 221, 232)
SILVER_DARK = (133, 147, 166)
INDIGO = (67, 77, 137)
DEEP_INDIGO = (44, 53, 96)
VIOLET = (121, 104, 169)
ROSE = (188, 108, 140)
CORAL = (200, 96, 90)
TEAL = (91, 147, 149)
GOLD = (203, 163, 84)
GOLD_LIGHT = (244, 213, 137)
OPAL = (230, 224, 242)
WHITE = (252, 251, 248)
BLACK = (18, 20, 25)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_BIG = ImageFont.truetype(FONT_DEVA, 48)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 19)

# Representative phonemic inventory. The visual count is exactly fifty powers;
# not every petal is used as a claim about one standardized orthographic inventory.
GLYPHS = list('अआइईउऊऋॠऌॡएऐओऔअंअःकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहक्ष')


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): return 0.5 - 0.5*math.cos(math.pi*clamp(t))
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def base_image(seed: int):
    rng=np.random.default_rng(seed)
    arr=np.zeros((H,W,3),dtype=np.float32); arr[:]=np.array(PAPER,dtype=np.float32)
    noise=rng.normal(0,1,(H,W)).astype(np.float32)
    arr += noise[...,None]*0.9
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    arr -= np.clip((dx*dx+dy*dy)*7,0,14)[...,None]*0.6
    halo=np.exp(-(((xx-W/2)/(W*.29))**2 + ((yy-H*.34)/(H*.20))**2)*2.8)
    for i in range(3): arr[...,i] += halo*(8 if i<2 else 18)
    return Image.fromarray(np.uint8(np.clip(arr,0,255)),'RGB').convert('RGBA')


def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def glow(im,xy,r,color,alpha=145,blur=16):
    ov=layer(); d=ImageDraw.Draw(ov); x,y=xy
    d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(color,alpha))
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))

def line_glow(im,pts,color,width=3,alpha=145,blur=8):
    ov=layer(); d=ImageDraw.Draw(ov)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def bezier(p0,p1,p2,p3,n=100):
    out=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        out.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return out

def partial(points,a):
    a=clamp(a)
    if a<=0:return []
    if a>=1:return points
    f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points):
        p,b=points[i],points[i+1]; out.append((lerp(p[0],b[0],q),lerp(p[1],b[1],q)))
    return out

def arrow(draw,p0,p1,col,s=1.0):
    a=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); z=11*s
    draw.polygon([p1,(p1[0]-math.cos(a-.5)*z,p1[1]-math.sin(a-.5)*z),(p1[0]-math.cos(a+.5)*z,p1[1]-math.sin(a+.5)*z)],fill=rgba(col,230))


def rosette(draw,cx,cy,r):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        draw.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(OPAL,140),outline=rgba(GOLD,165),width=1)
    draw.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(GOLD_LIGHT,110),outline=rgba(INDIGO,180),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(SILVER_DARK,105),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,78),width=1)
    for p in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,*p,22)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(249,247,241,220),outline=rgba(SILVER_DARK,65),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
    d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=DEEP_INDIGO)

def mirror(draw,bbox,col=SILVER_DARK,fill=None,width=2):
    draw.ellipse(bbox,outline=rgba(col,205),fill=fill or rgba(SILVER,55),width=width)
    x0,y0,x1,y1=bbox
    draw.arc((x0+10,y0+10,x1-10,y1-10),205,320,fill=rgba(WHITE,170),width=2)

def petal(draw,cx,cy,ang,r0,r1,w,col,alpha=170):
    ux,uy=math.cos(ang),math.sin(ang); vx,vy=-uy,ux
    p0=(cx+ux*r0,cy+uy*r0); p1=(cx+ux*r1,cy+uy*r1)
    pts=[(p0[0]+vx*w,p0[1]+vy*w),(p1[0],p1[1]),(p0[0]-vx*w,p0[1]-vy*w)]
    draw.polygon(pts,fill=rgba(col,alpha),outline=rgba(mix(col,INK,.25),150))


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    mirror(d,(cx-240,cy-165,cx+240,cy+165),INDIGO,rgba(OPAL,65),3)
    # fifty reflected points
    for i in range(50):
        a=-math.pi/2+i*2*math.pi/50+t*.025
        r=190+18*math.sin(i*.7)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
        c=mix(INDIGO,GOLD_LIGHT,(i%10)/10)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(c,180))
    glow(im,(cx,cy),50,GOLD_LIGHT,125,15)
    d.text((cx,cy),'अहं',font=DEVA_BIG,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'the universe of words and meanings reflected within the great I',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    mirror(d,(cx-220,cy-150,cx+220,cy+150),SILVER_DARK,rgba(SILVER,48),3)
    # reflected city-like geometry without external prototype
    for i in range(10):
        x=cx-170+i*38; h=35+(i%4)*25
        a=smooth(.05+i*.035,.8,t)
        d.rounded_rectangle((x,cy+70-h*a,x+24,cy+70),radius=3,outline=rgba(mix(INDIGO,ROSE,i/10),160),fill=rgba(OPAL,45),width=2)
    glow(im,(cx,cy-30),38,GOLD_LIGHT,100,12)
    d.ellipse((cx-13,cy-43,cx+13,cy-17),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'no external prototype is required: consciousness generates its own reflections',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    glow(im,(cx,cy),95,GOLD_LIGHT,140,24)
    for r in [45,90,145,205]: d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=rgba(mix(GOLD,SILVER,r/205),125),width=2)
    d.text((cx,cy),'अ',font=ImageFont.truetype(FONT_DEVA,72),fill=DEEP_INDIGO,anchor='mm')
    for i in range(16):
        a=i*2*math.pi/16
        p1=(cx+math.cos(a)*lerp(40,225,ease(t)),cy+math.sin(a)*lerp(40,155,ease(t)))
        line_glow(im,[(cx,cy),p1],GOLD_LIGHT,2,70,5)
    d.text((640,505),'A: Anuttara, the open first power containing every later articulation',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    # A becoming long A through bliss expansion
    d.text((390,cy),'अ',font=ImageFont.truetype(FONT_DEVA,64),fill=DEEP_INDIGO,anchor='mm')
    d.text((890,cy),'आ',font=ImageFont.truetype(FONT_DEVA,64),fill=ROSE,anchor='mm')
    pts=partial(bezier((430,cy),(540,cy-125),(740,cy+125),(850,cy),100),smooth(.05,.86,t))
    if len(pts)>1:
        line_glow(im,pts,mix(GOLD_LIGHT,ROSE,.5),5,125,8); arrow(d,pts[-2],pts[-1],ROSE,1.1)
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8+t*.05
        x=640+math.cos(a)*115; y=cy+math.sin(a)*70
        d.ellipse((x-7,y-7,x+7,y+7),fill=rgba(mix(GOLD_LIGHT,ROSE,i/8),190))
    d.text((640,505),'Ā: bliss as the first expansion of the absolute into self-enjoyment',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,285
    # alphabetic unfolding spiral
    n=50
    pts=[]
    for i in range(n):
        u=i/(n-1); a=-math.pi/2+u*4.6*math.pi
        r=28+u*230
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.62))
    trail=partial(pts,smooth(.02,.95,t))
    if len(trail)>1: line_glow(im,trail,INDIGO,3,100,6)
    visible=max(1,int(50*smooth(.02,.95,t)))
    for i,(x,y) in enumerate(pts[:visible]):
        c=mix(GOLD_LIGHT,INDIGO,i/49)
        d.ellipse((x-8,y-8,x+8,y+8),fill=rgba(PAPER_LIGHT,190),outline=rgba(c,190),width=2)
        if i in [0,1,2,15,25,35,49]:
            glyph=GLYPHS[min(i,len(GLYPHS)-1)]
            d.text((x,y),glyph,font=DEVA_SMALL,fill=c,anchor='mm')
    d.text((640,505),'the fifty powers unfold progressively as the articulation of reflective awareness',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,278
    # terminal H as horizon / arch
    d.arc((250,115,1030,495),180,360,fill=rgba(INDIGO,190),width=5)
    for i in range(22):
        a=math.pi + i*math.pi/21
        x=cx+math.cos(a)*390; y=305+math.sin(a)*190
        d.text((x,y),GLYPHS[min(16+i,len(GLYPHS)-1)],font=DEVA_SMALL,fill=mix(ROSE,INDIGO,i/21),anchor='mm')
    glow(im,(cx,310),42,VIOLET,105,14)
    d.text((cx,310),'ह',font=ImageFont.truetype(FONT_DEVA,68),fill=DEEP_INDIGO,anchor='mm')
    d.line((360,370,920,370),fill=rgba(SILVER_DARK,120),width=2)
    d.text((640,505),'H: the terminal consonantal horizon completing the arc of articulation',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,275
    # all rays collected into bindu
    for i in range(32):
        a=i*2*math.pi/32
        p0=(cx+math.cos(a)*235,cy+math.sin(a)*150)
        p1=(cx+math.cos(a)*38,cy+math.sin(a)*25)
        amt=smooth(.05+i*.008,.88,t)
        pts=partial(bezier(p0,(lerp(p0[0],cx,.35),p0[1]),(lerp(p1[0],cx,.4),p1[1]),p1,70),amt)
        if len(pts)>1: line_glow(im,pts,mix(INDIGO,GOLD_LIGHT,(i%8)/8),2,75,5)
    glow(im,(cx,cy),68,GOLD_LIGHT,130,20)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,230),width=2)
    d.text((cx,205),'bindu',font=TERM_FONT,fill=GOLD,anchor='mm')
    d.text((640,505),'bindu gathers the articulated powers into a single reflective seed',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,290
    # A-H-bindu triangle
    pts=[(cx,135),(350,410),(930,410)]
    d.polygon(pts,outline=rgba(GOLD,190),fill=rgba(OPAL,34))
    for p,col,lab,font in [(pts[1],INDIGO,'अ',DEVA_BIG),(pts[2],ROSE,'ह',DEVA_BIG),(pts[0],GOLD_LIGHT,'•',TERM_FONT)]:
        glow(im,p,34,col,110,10); d.ellipse((p[0]-18,p[1]-18,p[0]+18,p[1]+18),fill=rgba(WHITE,240),outline=rgba(col,220),width=2)
        d.text(p,lab,font=font,fill=col,anchor='mm')
    for a,b,col in [(pts[1],pts[0],INDIGO),(pts[0],pts[2],GOLD),(pts[2],pts[1],ROSE)]:
        q=partial(bezier(a,((a[0]+b[0])/2, a[1]-35),((a[0]+b[0])/2,b[1]+35),b,80),smooth(.04,.85,t))
        if len(q)>1: line_glow(im,q,col,3,100,6)
    glow(im,(cx,300),52,GOLD_LIGHT,120,16)
    d.text((cx,300),'अहं',font=DEVA_BIG,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'A–H–bindu condense the full alphabet into supreme I-consciousness',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc09(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # fifty mirror petals
    for i in range(50):
        a=-math.pi/2+i*2*math.pi/50+t*.02
        col=mix(INDIGO,ROSE,(i%10)/10)
        petal(d,cx,cy,a,128,235,6,col,125)
        if i%5==0:
            x=cx+math.cos(a)*250; y=cy+math.sin(a)*250
            d.text((x,y),str(i+1),font=TINY_FONT,fill=UMBER,anchor='mm')
    mirror(d,(cx-88,cy-88,cx+88,cy+88),GOLD,rgba(SILVER,55),3)
    glow(im,(cx,cy),42,GOLD_LIGHT,125,14)
    d.text((cx,cy),'अहं',font=DEVA_MED,fill=DEEP_INDIGO,anchor='mm')
    d.text((640,505),'fifty reflective powers form the living circumference of the universal subject',font=SUB_FONT,fill=UMBER,anchor='mm')


def sc10(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,280
    # final full-I seal: mirror, 50 ring, word/meaning halves
    mirror(d,(cx-235,cy-175,cx+235,cy+175),INDIGO,rgba(OPAL,46),3)
    for i in range(50):
        a=-math.pi/2+i*2*math.pi/50
        r=205
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.72
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD_LIGHT,INDIGO,(i%12)/12),185))
    d.text((365,280),'शब्द',font=DEVA_MED,fill=INDIGO,anchor='mm')
    d.text((915,280),'अर्थ',font=DEVA_MED,fill=ROSE,anchor='mm')
    q1=partial(bezier((430,280),(510,210),(575,240),(620,275),80),smooth(.05,.8,t))
    q2=partial(bezier((850,280),(770,350),(705,320),(660,285),80),smooth(.05,.8,t))
    if len(q1)>1: line_glow(im,q1,INDIGO,3,100,6)
    if len(q2)>1: line_glow(im,q2,ROSE,3,100,6)
    glow(im,(cx,cy),66,GOLD_LIGHT,140,19)
    d.text((cx,cy),'अहं',font=ImageFont.truetype(FONT_DEVA,58),fill=DEEP_INDIGO,anchor='mm')
    d.text((cx,185),'PŪRṆĀHANTĀ',font=TERM_FONT,fill=GOLD,anchor='mm')
    d.text((640,505),'the seal of full I-ness: word, meaning, and world reflected in one awareness',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('ah01','AHAṂ — The Great I','The fifty powers appear within the mirror of complete subjectivity.','AHAṂ','Overview of universal I-consciousness and its fifty reflective powers.','overview',['aham','reflection','fifty powers'],'overview','mirror field with fifty points',sc01),
Scene('ah02','The Mirror of Consciousness','The world shines as a real reflection without an external prototype.','Pratibimba','Consciousness is the self-generating medium of all reflected appearance.','mirror_doctrine',['mirror','reflection','consciousness'],'foundation','mirror city',sc02),
Scene('ah03','A — Anuttara','The first phoneme opens as the unsurpassable source.','A / Anuttara','A contains all subsequent articulation in an unbounded first power.','letter_a',['anuttara','a','source'],'phoneme','radiant source letter',sc03),
Scene('ah04','Ā — Ānanda','The absolute lengthens into blissful self-expansion.','Ā / Ānanda','The second power is the expansion of the source into bliss.','letter_aa',['ananda','aa','bliss'],'phoneme','A-to-AA expansion curve',sc04),
Scene('ah05','The Fiftyfold Unfolding','The powers articulate progressively as the phonemic sequence.','Mātṛkā','Reflective awareness unfolds through fifty powers symbolized by the alphabet.','alphabet_spiral',['alphabet','fifty','unfolding'],'process','fifty-bead spiral',sc05),
Scene('ah06','H — The Terminal Horizon','The final consonantal horizon completes articulation.','H-kāra','H marks the terminal limit of the A-to-H cycle.','letter_h',['h','horizon','completion'],'phoneme','letter arch',sc06),
Scene('ah07','Bindu — The Gathering Seed','The dispersed powers recollect into one reflective point.','Bindu','The whole articulated field is gathered into a single seed.','bindu_gathering',['bindu','seed','recollection'],'process','centripetal ray gathering',sc07),
Scene('ah08','A–H–Bindu','The full phonemic field condenses into AHAṂ.','AHAṂ','First, last, and bindu form the great I of reflective awareness.','aham_triangle',['aham','triangle','subjectivity'],'synthesis','A-H-bindu triangle',sc08),
Scene('ah09','The Fifty Powers of Reflection','Fifty mirror-petals form the circumference of the universal subject.','Parāmarśa-śaktis','The powers are modes of reflective awareness, not inert letters.','fifty_petals',['fifty powers','reflection','petals'],'synthesis','exact fifty-petal mirror field',sc09),
Scene('ah10','The Seal of Full I-ness','Word, meaning, and world resolve in one mirror of awareness.','Pūrṇāhantā','The closing seal presents complete I-consciousness as the medium of all reality.','closing_seal',['seal','purnahanta','word meaning'],'seal','mirror seal with fifty ring',sc10),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000: continue
        t=i/max(1,NFRAMES-1); im=base_image(SEED+hash(sc.id)%10000+i); border(im); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=94)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)


def contact_sheet():
    sheet=Image.new('RGB',(4*320,3*180),PAPER)
    for i,sc in enumerate(SCENES):
        f=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        im=Image.open(f).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)


def metadata():
    manifest={'project':'Tantrāloka — AHAṂ and the Fifty Powers of Reflection','source_basis':'Tantrāloka Chapter 3: doctrine of reflection, the fifty forms of reflective awareness, and the A-to-H cycle of AHAṂ.','fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'style':{'family':'mirror-consciousness and phonemic radiance','background':'clean ivory paper','materials':['silver mirror','opal letter-glass','gold foil','indigo lacquer','rose reflective light']},'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'term':s.term,'summary':s.summary,'mode':s.mode,'tags':s.tags,'group':s.group,'technique_notes':s.technique,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'foundation':['ah01','ah02'],'phonemic_source':['ah03','ah04'],'unfolding_and_gathering':['ah05','ah06','ah07'],'aham_synthesis':['ah08','ah09','ah10']},'reusability_notes':{'ah02':'Use for pratibimbavāda, mirror-consciousness, or world-as-reflection scenes.','ah03':'Use for Anuttara, first phoneme, source, or open beginning.','ah05':'Use for alphabetic manifestation or progressive articulation.','ah07':'Use for bindu, recollection, seed, or centripetal gathering.','ah08':'Use for AHAṂ, great I, or phonemic subjectivity.','ah09':'Use for the fifty powers as a field of reflective awareness.','ah10':'Use as the pack closing seal or for pūrṇāhantā.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — AHAṂ and the Fifty Powers of Reflection

## Aim
This pack visualizes Chapter 3's doctrine of reflection and the fifty powers of reflective awareness symbolized by the Sanskrit alphabet.

## Core structure
- Consciousness is the mirror within which words, meanings, perceptions, and worlds appear.
- The reflections are real appearances dependent upon consciousness; they do not require an external prototype outside awareness.
- One universal power of freedom and reflective awareness unfolds in fifty forms symbolized by the alphabet.
- The sequence begins with A, associated with Anuttara, and unfolds toward H, the terminal consonantal horizon.
- A, H, and bindu are compressed visually into AHAṂ, the universal and transcendental I-consciousness.
- Pūrṇāhantā means full I-ness: the whole field appears within one complete subjectivity.

## Visual rules
- Do not make this a school alphabet chart.
- Letters are powers and reflective operators.
- Mirrors must suggest consciousness as active medium, not passive glass.
- A should feel radically open; H should feel like completed articulation.
- Bindu should gather the field rather than merely decorate it.
- The fifty-petal scene must contain exactly fifty petals.

## Style family
Clean ivory field, silver mirrors, opal letter-glass, indigo reflective depth, rose articulation, and gold source-light.

## Guardrails
- Avoid equating AHAṂ with ordinary egoism.
- The 'I' here is universal subjectivity, not the contracted personality.
- Do not claim one universal orthographic enumeration for the fifty Sanskrit letters; the pack visualizes fifty powers symbolized by the alphabet.
- Reflection is not treated as sheer unreality.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — AHAṂ and Fifty Powers Pack

## Differentiation
This pack adds a reflective and phonemic visual language rather than another hierarchy or breath-axis.

## New symbols
1. active consciousness mirror
2. source-letter A
3. bliss-expanding Ā
4. fifty-bead articulation spiral
5. terminal H arch
6. bindu recollection field
7. A–H–bindu triangle
8. exact fifty-petal mirror wheel
9. word / meaning mirror pair
10. full-I closing seal

## New relationships
- consciousness → reflection
- A → Ā → alphabetic unfolding
- articulation → terminal horizon
- dispersed powers → bindu recollection
- word ↔ meaning within one mirror
- fifty powers → full I-consciousness

## Material vocabulary
Silver mirror, opal phoneme glass, gold foil, indigo lacquer, rose reflective light.

## Closing seal
A silver consciousness mirror containing fifty points, word and meaning, and the central AHAṂ of pūrṇāhantā.
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# AHAṂ and the Fifty Powers of Reflection Pack

- Resolution: {W}x{H}
- FPS: {FPS}
- Scenes: {len(SCENES)}
- Duration per scene: {DURATION}s
- Total duration: {len(SCENES)*DURATION:.1f}s

Run: `python render_pack.py`
The renderer is resume-safe.
'''
    (ROOT/'README.md').write_text(readme)


def validate():
    f=ROOT/'aham_fifty_powers_animation.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(f)]))
    (ROOT/'validation.json').write_text(json.dumps(data,indent=2))

def zip_pack():
    z=ROOT/'aham_fifty_powers_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as q:
        for n in ['aham_fifty_powers_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            q.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): q.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES:
        print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'aham_fifty_powers_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); zip_pack()

if __name__=='__main__': main()
