#!/usr/bin/env python3
"""
CONSCIOUSNESS IS NOT LOCATED
The 36 Tattvas — How One Becomes Many Without Leaving Itself

CENTRAL CLAIM
-------------
Neuroscience looks for consciousness inside the brain.
Abhinavagupta says: you cannot find consciousness inside experience
because consciousness is the space in which all experience appears.

The 36 tattvas are not a list of things.
They are a map of how the one infinite consciousness contracts step by step
until it appears as a finite subject encountering a world of objects.

Each tattva is not a new entity produced by the previous one.
It is the same consciousness, appearing at a different density of self-limitation.

FILM THESIS
-----------
Modern picture:
brain → consciousness → world

Abhinavagupta's picture:
pure consciousness (Siva)
→ the power to appear as all this (Sakti)
→ the first limitation (limited agency, kala)
→ the second limitation (limited knowledge, vidya)
→ the third limitation (attachment, raga)
→ the fourth limitation (time, kala)
→ the fifth limitation (causality, niyati)
→ the subtle world of mind and senses
→ the gross world of elements
→ the body
→ the world appears as external

The chain is not causal. It is a series of appearances.
Each stage is consciousness appearing more densely.

OUTPUT
------
output_consciousness_container/
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_consciousness_container")
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
W, H, FPS = 1280, 720, 10

IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
SILVER=(180,187,194); CYAN=(57,156,180); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); CRIMSON=(162,58,69); VIOLET=(109,83,153); PALE_VIOLET=(218,208,235)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold")
FNS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FNSB=FNS.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)
def font(p,s):
    for c in (p,FS,FNS):
        try: return ImageFont.truetype(c,s)
        except: pass
    return ImageFont.load_default()
def layer(s): return Image.new("RGBA",s,(0,0,0,0))

def field(w,h,seed):
    r=np.random.default_rng(seed)
    a=np.empty((h,w,3),dtype=np.float32); a[:]=IVORY
    a+=r.normal(0,.9,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
    h2=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2)
    a[...,1]+=h2*3.2; a[...,2]+=h2*4.6
    return Image.fromarray(np.clip(a,0,255).astype(np.uint8),"RGB").convert("RGBA")

def centered(d,xy,t,f,fill=INK): d.text(xy,t,font=f,fill=fill,anchor="mm")
def seal(im,t,s="",c=INK):
    w2,h2=im.size; d=ImageDraw.Draw(im)
    tf=font(FSB,max(22,int(h2*.04))); sf=font(FNS,max(13,int(h2*.019)))
    centered(d,(w2/2,h2*.875),t,tf,c)
    if s: centered(d,(w2/2,h2*.923),s,sf,SOFT_INK)
def border(im):
    w2,h2=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w2-26,h2-26),radius=18,outline=(*INK,45),width=2)
def glow_circle(im,x,y,r,c,a=170,b=14):
    gl=layer(im.size); ImageDraw.Draw(gl).ellipse((x-r,y-r,x+r,y+r),fill=(*c,int(a)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(b)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).ellipse((x-r*.34,y-r*.34,x+r*.34,y+r*.34),fill=(*mix(c,WHITE,.35),min(255,int(a)+50)))
    im.alpha_composite(fg)
def glow_line(im,pts,c,w=4,a=210,b2=11):
    if len(pts)<2: return
    gl=layer(im.size); ImageDraw.Draw(gl).line(pts,fill=(*c,int(a)),width=w*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(b2)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(c,WHITE,.08),min(255,int(a)+25)),width=w,joint="curve")
    im.alpha_composite(fg)
def partial(pts,a):
    if not pts: return []
    a=clamp(a)
    if a>=1: return pts
    k=a*(len(pts)-1); i=int(k); f=k-i
    out=list(pts[:i+1])
    if i+1<len(pts):
        p,q=pts[i],pts[i+1]
        out.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return out
def arrow(d,a,b,c=INK,w=3,h2=10):
    d.line((*a,*b),fill=c,width=w)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s2 in(-1,1):
        p=(b[0]-math.cos(ang+s2*.52)*h2,b[1]-math.sin(ang+s2*.52)*h2)
        d.line((*b,*p),fill=c,width=w)

def draw_tattva_ring(im,cx,cy,r,label,color,alpha=200,width=3):
    d=ImageDraw.Draw(im)
    d.ellipse((cx-r,cy-r*.62,cx+r,cy+r*.62),outline=(*color,alpha),width=width)
    centered(d,(cx,cy),label,font(FSB,18),color)

# =============================================================================
# VISUALS
# =============================================================================

def vis_siva(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    for rr in range(15,240,20):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*GOLD,int(55*(1-rr/260))),width=2)
    glow_circle(im,cx,cy,18,GOLD,190,15)
    centered(d,(cx,cy),"ŚIVA",font(FSB,32),GOLD)
    seal(im,"PURE CONSCIOUSNESS","not a god — the unconditioned field of all appearing")

def vis_sakti(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    for rr in range(15,210,20):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*VIOLET,int(50*(1-rr/230))),width=2)
    pts=[]
    for i in range(120):
        x=w*.12+i*w*.76/119
        y=h*.40+math.sin(i*.15+t)*35
        pts.append((x,y))
    glow_line(im,partial(pts,q),VIOLET,5,190,12)
    glow_circle(im,cx,cy,15,VIOLET,180,13)
    seal(im,"ŚAKTI — THE POWER TO APPEAR","consciousness is not static — it is the power to be all this")

def vis_sadasiva(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,120,"I-AM-THIS",mix(GOLD,VIOLET,.5),200,3)
    left_x=cx-70; right_x=cx+70
    for i,x in enumerate([left_x,right_x]):
        glow_circle(im,x,cy,10,[CYAN,VIOLET][i],150,8)
        centered(d,(x,cy+55),["I","THIS"][i],font(FNSB,16),[CYAN,VIOLET][i])
    glow_line(im,partial([(left_x+20,cy),(right_x-20,cy)],q),GOLD,3,160,8)
    seal(im,"SADĀŚIVA — THE FIRST EMERGENCE OF SUBJECT AND OBJECT","not two — a single pulse of I and this together")

def vis_isvara(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,130,"THIS-NESS",CYAN,190,3)
    for rr in range(30,130,25):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*CYAN,int(65*(1-rr/140))),width=2)
    seal(im,"ĪŚVARA — THE OBJECT POLE BECOMES PROMINENT","the world begins to appear as other")

def vis_sadvidya(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,140,"I-NESS",GREEN,190,3)
    for rr in range(30,140,25):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*GREEN,int(65*(1-rr/150))),width=2)
    seal(im,"SADVIDYĀ — THE SUBJECT POLE BECOMES PROMINENT","the sense of self emerges from the unity")

def vis_maya(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,150,"MĀYĀ",CRIMSON,190,3)
    for rr in range(45,155,25):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*CRIMSON,int(55*(1-rr/170))),width=2)
    if q>.35:
        centered(d,(cx,cy+65),"the power of limitation",font(FNS,16),SOFT_INK)
    seal(im,"MĀYĀ IS NOT ILLUSION","it is consciousness freely contracting into finitude")

def vis_kala(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    cols=[CRIMSON,VIOLET,GREEN,CYAN,GOLD]
    labels=["KĀLA","VIDYĀ","RĀGA","KĀLA","NIYATI"]
    for i in range(5):
        r=100-i*14
        draw_tattva_ring(im,cx,cy,r,labels[i],cols[i],int(180-20*i),3)
    seal(im,"THE FIVE KAÑCUKAS","consciousness binds itself into finitude — agency, knowledge, attachment, time, causality")

def vis_purusha(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,90,"PURUṢA",GOLD,190,3)
    draw_tattva_ring(im,cx,cy,110,"PRAKṚTI",SILVER,160,3)
    centered(d,(cx,cy+55),"the experiencer and its apparatus",font(FNS,14),SOFT_INK)
    seal(im,"THE INDIVIDUAL SOUL ENTERS","a finite knower with the equipment of knowing")

def vis_buddhi(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,80,"BUDDHI",CYAN,190,3)
    pts=[]
    for i in range(60):
        x=w*.20+i*w*.60/59
        y=h*.40+math.sin(i*.2+t)*25
        pts.append((x,y))
    glow_line(im,partial(pts,q),CYAN,4,170,10)
    seal(im,"BUDDHI — THE INTELLECT","decision, discernment, the capacity to know this as this")

def vis_ahankara(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,90,"AHAṄKĀRA",CRIMSON,190,3)
    for i,x in enumerate([cx-40,cx+40]):
        glow_circle(im,x,cy,8,CRIMSON,140,6)
    seal(im,"AHAṄKĀRA — THE I-MAKER","the sense that this experience belongs to me")

def vis_manas(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,80,"MANAS",VIOLET,190,3)
    for i in range(6):
        a=i*math.tau/6+t*0.2
        x=cx+math.cos(a)*55; y=cy+math.sin(a)*55*.7
        d.line((cx,cy,x,y),fill=(*VIOLET,140),width=2)
    seal(im,"MANAS — THE MIND","attention, deliberation, the oscillation between possibilities")

def vis_indriyas(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,100,"INDRIYAS",GREEN,190,3)
    labels=["HEAR","TOUCH","SEE","TASTE","SMELL"]
    for i,lab in enumerate(labels):
        a=i*math.tau/5+t*0.15
        x=cx+math.cos(a)*70; y=cy+math.sin(a)*70*.6
        centered(d,(x,y),lab,font(FNS,12),GREEN)
        d.line((cx,cy,x,y),fill=(*GREEN,120),width=2)
    seal(im,"THE FIVE SENSE CAPACITIES","consciousness learns to perceive through gates")

def vis_tanmatras(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,90,"TANMĀTRAS",CYAN,190,3)
    for i in range(30):
        a=i*math.tau/30+t*0.1
        r=50+20*math.sin(i+t)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*CYAN,150))
    seal(im,"THE FIVE SUBTLE ELEMENTS","sound, touch, form, taste, smell — the raw data of perception")

def vis_mahabhutas(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    draw_tattva_ring(im,cx,cy,85,"MAHĀBHŪTAS",INK,190,3)
    labels=["ETHER","AIR","FIRE","WATER","EARTH"]
    cols=[VIOLET,CYAN,GOLD,GREEN,INK]
    for i,lab in enumerate(labels):
        a=i*math.tau/5+t*0.1
        x=cx+math.cos(a)*55; y=cy+math.sin(a)*55*.6
        centered(d,(x,y),lab,font(FNS,13),cols[i])
    seal(im,"THE FIVE GROSS ELEMENTS","consciousness becomes physical — appears as a world")

def vis_body(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    d.ellipse((cx-27,cy-145,cx+27,cy-91),outline=(*INK,170),width=4)
    d.line((cx,cy-91,cx,cy+55),fill=(*INK,170),width=6)
    d.line((cx-68,cy-54,cx+68,cy-54),fill=(*INK,170),width=5)
    d.line((cx,cy+55,cx-52,cy+160),fill=(*INK,170),width=5)
    d.line((cx,cy+55,cx+52,cy+160),fill=(*INK,170),width=5)
    for rr in range(45,200,25):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*GOLD,int(45*(1-rr/220))),width=2)
    seal(im,"THE BODY IS THE LAST TATTVA","earth — the most contracted form of consciousness")

def vis_brain_search(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    d.ellipse((cx-55,cy-45,cx+55,cy+45),fill=(*PALE_GOLD,80),outline=(*INK,170),width=4)
    centered(d,(cx,cy),"BRAIN",font(FSB,22),INK)
    if q>.35:
        rr=lerp(20,180,(q-.35)/.65)
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*GOLD,int(65*(1-rr/200))),width=3)
        centered(d,(cx,cy+60),"consciousness not found",font(FNS,14),SOFT_INK)
    seal(im,"NEUROSCIENCE LOOKS HERE","but the search space is not inside the brain — it is what contains the brain")

def vis_return(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    labels=["ŚIVA","ŚAKTI","SADĀŚIVA","ĪŚVARA","SADVIDYĀ","MĀYĀ","PURUṢA","PRAKṚTI","BUDDHI","AHAṄKĀRA","MANAS","INDRIYAS","TANMĀTRAS","MAHĀBHŪTAS","EARTH"]
    cols=[GOLD,VIOLET,mix(GOLD,VIOLET,.5),CYAN,GREEN,CRIMSON,GOLD,SILVER,CYAN,CRIMSON,VIOLET,GREEN,CYAN,INK,INK]
    for i,(lab,col) in enumerate(zip(labels,cols)):
        local=clamp(q*len(labels)-i)
        if local<=0: continue
        y=h*(.12+i*.042)
        d.rounded_rectangle((w*.20,y-10,w*.80,y+10),radius=5,
                            fill=(*mix(WHITE,col,.08),int(180*local)),
                            outline=(*col,int(140*local)),width=1)
        centered(d,(w*.50,y),lab,font(FNS,12),col)
    seal(im,"THE 36 TATTVAS","not a list of things — a map of consciousness limiting itself",GOLD)

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[("THE 36 TATTVAS DESCRIBE APPEARANCE, NOT PRODUCTION","SUPPORTED",GREEN),
          ("EACH TATTVA IS CONSCIOUSNESS APPEARING MORE DENSELY","SUPPORTED",CYAN),
          ("THE TATTVAS ARE PHYSICAL LAYERS OF THE BRAIN","CATEGORY ERROR",CRIMSON),
          ("NEUROSCIENCE CAN VERIFY THE TATTVA HIERARCHY","NOT ESTABLISHED",CRIMSON)]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FNSB,13),INK)
        centered(d,(w*.74,y),status,font(FNSB,13),col)
    seal(im,"THE TATTVAS ARE ONTOLOGICAL, NOT PHYSICAL","they describe modes of appearing, not physical layers of the universe")

def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.40; q=ease(u)
    for rr in range(15,280,25):
        d.ellipse((cx-rr,cy-rr*.62,cx+rr,cy+rr*.62),outline=(*GOLD,int(55*(1-rr/300))),width=2)
    glow_circle(im,cx,cy,16,GOLD,180,13)
    if q>.6:
        q2=(q-.6)/.4
        centered(d,(cx,cy),"ŚIVA",font(FSB,36),(*GOLD,int(200*q2)))
        centered(d,(cx,cy+50),"never left",font(FNSB,20),(*SOFT_INK,int(180*q2)))
    seal(im,"CONSCIOUSNESS IS NOT LOCATED","the container cannot be found inside the contained",GOLD)


@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

VISUALS={}
for k,v in list(locals().items()):
    if k.startswith('vis_') and callable(v):
        VISUALS[k[4:]]=v

SCENES = [
    Scene("Siva","Pure consciousness, the unconditioned ground.",8.0,"siva",{}),
    Scene("Not a god","Siva is not a deity — it is the field of all possible appearing.",8.0,"siva",{}),
    Scene("Sakti","The power to appear as all this — consciousness is not static.",8.0,"sakti",{}),
    Scene("Dynamic","Siva-Sakti are not two things — they are the same reality as ground and as power.",8.5,"sakti",{}),
    Scene("Sadasiva","I-am-this — the first pulse of subject and object together.",8.0,"sadasiva",{}),
    Scene("First distinction","Not two — one pulse that contains both poles.",7.5,"sadasiva",{}),
    Scene("Isvara","This-ness becomes prominent — the world begins to appear as other.",8.0,"isvara",{}),
    Scene("The object pole","Objectivity emerges from the unity.",7.5,"isvara",{}),
    Scene("Sadvidya","I-ness becomes prominent — the sense of self emerges.",8.0,"sadvidya",{}),
    Scene("The subject pole","Subjectivity emerges from the unity.",7.5,"sadvidya",{}),
    Scene("Maya","Consciousness contracts into finitude — the power of limitation.",8.5,"maya",{}),
    Scene("Not illusion","Maya is not false appearance — it is consciousness freely choosing to appear limited.",9.0,"maya",{}),
    Scene("Kala","Limited agency — I can only do this much.",7.5,"kala",{}),
    Scene("Vidya","Limited knowledge — I can only know this much.",7.5,"kala",{}),
    Scene("Raga","Attachment — I want this and not that.",7.0,"kala",{}),
    Scene("Kala","Time — I experience sequence, not simultaneity.",7.5,"kala",{}),
    Scene("Niyati","Causality — events appear determined.",7.5,"kala",{}),
    Scene("Purusha","The individual experiencer enters.",7.5,"purusha",{}),
    Scene("Prakrti","The apparatus of experience — nature as the field of limitation.",8.0,"purusha",{}),
    Scene("Buddhi","The intellect — discernment, decision, the capacity to know this as this.",8.0,"buddhi",{}),
    Scene("Ahankara","The I-maker — the sense that this experience belongs to me.",8.0,"ahankara",{}),
    Scene("Manas","The mind — attention, deliberation, oscillation.",8.0,"manas",{}),
    Scene("The five senses","Hearing, touching, seeing, tasting, smelling — gates through which consciousness perceives.",8.5,"indriyas",{}),
    Scene("The five subtle elements","Sound, touch, form, taste, smell — the raw data of perception.",8.0,"tanmatras",{}),
    Scene("The five gross elements","Ether, air, fire, water, earth — consciousness becomes physical.",8.5,"mahabhutas",{}),
    Scene("Ether","Space — the first condition of physical appearance.",7.0,"mahabhutas",{}),
    Scene("Earth","The most contracted form of consciousness.",7.0,"mahabhutas",{}),
    Scene("The body","Earth tattva — the final density of appearing.",8.0,"body",{}),
    Scene("Matter as consciousness","The body is not unconscious — it is consciousness appearing at maximum contraction.",8.5,"body",{}),
    Scene("Neuroscience","Modern science looks for consciousness inside the brain.",8.0,"brain_search",{}),
    Scene("Not found","After decades of searching, the neural correlate is not the thing itself.",8.5,"brain_search",{}),
    Scene("Wrong question","Abhinavagupta: you cannot find consciousness inside experience because consciousness is the space of experience.",9.5,"brain_search",{}),
    Scene("The descent","36 tattvas: one consciousness appearing as all this.",7.5,"return",{}),
    Scene("The ascent","The return path: from earth back to Siva — consciousness recognizing itself.",8.0,"return",{}),
    Scene("Discipline","The tattvas are ontological, not physical.",7.0,"caution",{}),
    Scene("No reduction","They describe modes of appearing, not physical layers.",8.0,"caution",{}),
    Scene("Closing","Siva never leaves. The 36 tattvas are the same one, appearing at different densities of self-limitation.",9.0,"final",{}),
    Scene("Final frame","Consciousness is not located. It is where location appears.",7.0,"final",{}),
]

def rf(sc,fi,fc,w2,h2,se):
    u=fi/max(1,fc-1); t=u*sc.duration
    im=field(w2,h2,se)
    VISUALS[sc.visual](im,u,t,sc.params); border(im)
    return im.convert("RGB")
def _ff():
    f2=shutil.which("ffmpeg")
    if not f2: raise RuntimeError("ffmpeg required")
    return f2
def es(idx,f2):
    o=SCENES_DIR/f"scene_{idx:03d}.mp4"; d=FRAMES/f"scene_{idx:03d}"
    subprocess.run([_ff(),"-y","-framerate",str(f2),"-i",str(d/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def rs(idx,s,f2,w2,h2,prev):
    d=FRAMES/f"scene_{idx:03d}"; d.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    cnt=max(2,round(s.duration*f2))
    if prev:
        for oi,fi2 in enumerate([0,int(cnt*.33),int(cnt*.72),cnt-1]):
            rf(s,fi2,cnt,w2,h2,idx*10000+fi2).save(d/f"preview_{oi:02d}.jpg",quality=95)
        return d
    for fi2 in range(cnt):
        p=d/f"{fi2:05d}.jpg"
        if p.exists(): continue
        rf(s,fi2,cnt,w2,h2,idx*10000+fi2).save(p,quality=95,subsampling=0)
    return es(idx,f2)
def concat(paths):
    cp=OUTPUT/"concat.txt"
    cp.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    final=OUTPUT/"consciousness_is_not_located.mp4"
    subprocess.run([_ff(),"-y","-f","concat","-safe","0","-i",str(cp),
        "-c","copy","-movflags","+faststart",str(final)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return final
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        item=asdict(s); item["scene_id"]=f"scene_{i:03d}"
        item["start_seconds"]=round(cursor,3); cursor+=s.duration
        item["end_seconds"]=round(cursor,3); recs.append(item)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"consciousness is not located",
        "subtitle":"the 36 tattvas — how one becomes many without leaving itself",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],
        "continuity_object":"gold ring of Siva surviving every contraction",
        "visual_arc":["siva","descent through tattvas","body","recognition"],
        "scenes":recs},indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def contact_sheet(w2,h2):
    tw,th=320,int(320*h2/w2); cols,rows=4,math.ceil(len(SCENES)/4); ch=th+48
    s=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(s)
    lf=font(FNSB,14)
    for i,sc in enumerate(SCENES,1):
        cnt=max(2,round(sc.duration*FPS))
        im=rf(sc,int(cnt*.72),cnt,w2,h2,i*10000+72)
        im.thumbnail((tw,th)); sl=i-1
        x,y=(sl%cols)*tw,(sl//cols)*ch
        s.paste(im,(x,y)); d.text((x+9,y+th+7),f"{i:02d}  {sc.title}",font=lf,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; s.save(p,quality=94); return p
def parse_args():
    p2=argparse.ArgumentParser()
    p2.add_argument("--fps",type=int,default=FPS)
    p2.add_argument("--width",type=int,default=W); p2.add_argument("--height",type=int,default=H)
    p2.add_argument("--scene",type=int); p2.add_argument("--preview",action="store_true")
    p2.add_argument("--no-contact-sheet",action="store_true")
    return p2.parse_args()
def main():
    a2=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    tl=export_timeline(); total=sum(s.duration for s in SCENES)
    print(f"Timeline: {tl}\nScenes: {len(SCENES)}\nRuntime: {total/60:.2f} min")
    if a2.scene:
        if not 1<=a2.scene<=len(SCENES): raise ValueError("scene range")
        print(rs(a2.scene,SCENES[a2.scene-1],a2.fps,a2.width,a2.height,a2.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        rendered.append(rs(i,s,a2.fps,a2.width,a2.height,a2.preview))
    final=concat(rendered); print(f"Final: {final}")
    if not a2.no_contact_sheet: print(f"Contact: {contact_sheet(a2.width,a2.height)}")
    print("Done.")
if __name__=="__main__": main()
