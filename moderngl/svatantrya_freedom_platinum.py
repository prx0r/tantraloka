#!/usr/bin/env python3
"""
FREEDOM COMES BEFORE CAUSALITY — Svatantrya as the Ground
Absolute freedom as the nature of consciousness.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Svātantrya — absolute freedom — is not a property of consciousness.
It IS consciousness. Before causality, before law, before form, there is
the freedom that chooses to appear constrained. The universe is not governed
by laws that consciousness must obey. Consciousness freely chooses the
laws that appear to govern it.

For Abhinavagupta and the Trika school: freedom is not something you achieve.
It is what you are before you are anything.

FILM THESIS
-----------
The modern picture often runs:

laws → causality → necessity → consciousness emerges within constraints

The Śaiva picture can be staged as:

absolute freedom (svātantrya)
→ freedom contracts to experience limitation
→ the kañcukas (limiting principles) appear
→ causality, time, and law emerge
→ consciousness experiences itself as bound
→ recognition reveals the bondage was freely chosen

Freedom is the ground. Causality is the figure.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: an unbounded golden field that contracts into a grid.
• Final reveal: the grid was always inside the field.

OUTPUT
------
output_svatantrya_freedom/
  frames/
  scenes/
  svatantrya_freedom.mp4
  narration_timeline.json
  contact_sheet.jpg
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_svatantrya_freedom"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH=1280; DEFAULT_HEIGHT=720; DEFAULT_FPS=10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
CYAN=(57,156,180); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); CRIMSON=(162,58,69); VIOLET=(109,83,153); PALE_VIOLET=(218,208,235)
FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)
def font(path,size):
    for c in (path,FONT_SERIF,FONT_SANS):
        try: return ImageFont.truetype(c,size)
        except OSError: pass
    return ImageFont.load_default()
def layer(size): return Image.new("RGBA",size,(0,0,0,0))
def field(w,h,seed):
    rng=np.random.default_rng(seed)
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=IVORY
    arr+=rng.normal(0,.9,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2)
    arr[...,1]+=halo*3.2; arr[...,2]+=halo*4.6
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")
def centered(d,xy,text,fnt,fill=INK): d.text(xy,text,font=fnt,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered(d,(w/2,h*.875),title,font(FONT_SERIF_BOLD,max(22,int(h*.04))),color)
    if subtitle: centered(d,(w/2,h*.923),subtitle,font(FONT_SANS,max(13,int(h*.019))),SOFT_INK)
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,45),width=2)
def glow_circle(im,x,y,r,color,alpha=170,blur=14):
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.ellipse((x-r,y-r,x+r,y+r),fill=(*color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).ellipse((x-r*.34,y-r*.34,x+r*.34,y+r*.34),
        fill=(*mix(color,WHITE,.35),min(255,alpha+50)))
    im.alpha_composite(fg)
def glow_line(im,pts,color,width=4,alpha=210,blur=11):
    if len(pts)<2: return
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.line(pts,fill=(*color,alpha),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(color,WHITE,.08),min(255,alpha+25)),width=width,joint="curve")
    im.alpha_composite(fg)
def partial(pts,a):
    if not pts: return []; a=clamp(a)
    if a>=1: return pts
    k=a*(len(pts)-1); i=int(k); f=k-i
    out=list(pts[:i+1])
    if i+1<len(pts): p,q=pts[i],pts[i+1]; out.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return out
def arrow(d,a,b,color=INK,width=3,head=10):
    d.line((*a,*b),fill=color,width=width)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (-1,1):
        p=(b[0]-math.cos(ang+s*.52)*head,b[1]-math.sin(ang+s*.52)*head)
        d.line((*b,*p),fill=color,width=width)

def vis_svatantrya(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,24,GOLD,int(240*q),20)
    for i in range(16):
        a=i*math.tau/16+t*.03; rad=30+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,3+2*q,PALE_GOLD,int(120*q),4)
    seal(im,"SVĀTANTRYA: ABSOLUTE FREEDOM","consciousness IS freedom — the ground of all causality")

def vis_causality(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        a=i*math.tau/6+t*.06; qc=clamp(q*4-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+100*qc); y=cy+math.sin(a)*(20+100*qc)*.35
        col=mix(CYAN,INK,i/5); d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),col,2,8)
    seal(im,"CAUSALITY IS DERIVED","freedom contracts into law")

def vis_kancukas(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(5):
        qc=clamp(q*5-i*.1)
        if qc<=0: continue
        a=i*math.tau/5+r*.2; rad=20+100*qc
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(GOLD,CRIMSON,i/4)
        d.ellipse((x-15*qc,y-15*qc,x+15*qc,y+15*qc),outline=(*col,int(180*qc)),width=2)
    seal(im,"THE KAÑCUKAS AS SELF-LIMITATION","freedom choosing to appear constrained")

def vis_choice(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(3):
        a=(i-1)*.6; qc=clamp(q*3-i*.15)
        if qc<=0: continue
        x=cx+math.cos(a)*120*qc; y=cy+math.sin(a)*120*qc
        col=GREEN if i==1 else (CYAN if i==0 else GOLD)
        d.line((cx,cy,x,y),fill=(*col,int(170*qc)),width=3)
        glow_circle(im,x,y,8+4*qc,col,int(170*qc),8)
    seal(im,"CHOICE IS NOT AN ILLUSION","every moment is a free act of consciousness")

def vis_physics(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(4):
        qc=clamp(q*4-i*.1)
        if qc<=0: continue
        y=lerp(h*.25,h*.60,i/3); width=lerp(300,100,i/3)*qc
        d.line((w*.50-width/2,y,w*.50+width/2,y),fill=(*INK,int(180*qc)),width=3)
    glow_circle(im,cx,cy,10,GOLD,int(160*q),8)
    seal(im,"PHYSICS DESCRIBES CONSTRAINTS","not why there are constraints — freedom is the why")

def vis_paradox(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,18,GOLD,int(200*q),14)
    d.ellipse((cx-100*q,cy-80*q,cx+100*q,cy+80*q),outline=(*CRIMSON,int(170*q)),width=3)
    d.ellipse((cx-130*q,cy-100*q,cx+130*q,cy+100*q),outline=(*CYAN,int(120*q)),width=2)
    seal(im,"THE PARADOX OF FREEDOM","to be free includes appearing unfree")

def vis_living(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+120*q),cy+math.sin(i*math.tau/40)*(30+120*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),GOLD,4,220,14)
    for i in range(4):
        a=i*math.tau/4+t*.06; x=cx+math.cos(a)*80*q; y=cy+math.sin(a)*80*q*.35
        glow_circle(im,x,y,6+3*q,GREEN,int(160*q),7)
    seal(im,"LIVING FROM FREEDOM","acting without bondage to the past")

def vis_contraction(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,20,GOLD,int(220*q),16)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        rad=20+i*25; col=mix(GOLD,CRIMSON,i/5)
        d.ellipse((cx-rad*qc,cy-rad*qc*.6,cx+rad*qc,cy+rad*qc*.6),outline=(*col,int(200*qc)),width=3)
        centered(d,(cx,cy-rad*qc*.6-15),f"KAÑCUKA {i+1}",font(FONT_SANS_BOLD,int(h*.017)),(*col,int(180*qc)))
    seal(im,"FREEDOM CONTRACTS","freedom limits itself to experience limitation")

def vis_absolute(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/50)*(30+140*q),cy+math.sin(i*math.tau/50)*(30+140*q)*.35) for i in range(51)]
    glow_line(im,partial(pts,q),GOLD,5,240,18)
    centered(d,(cx,cy),"SVĀTANTRYA",font(FONT_SERIF_BOLD,int(h*.050)),(*GOLD,int(200*q)))
    if q>.6:
        for i in range(15):
            a=i*math.tau/15+t*.03; rad=40+140*q
            x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
            d.ellipse((x-3*q,y-3*q,x+3*q,y+3*q),fill=(*PALE_GOLD,int(150*q)))
    seal(im,"ABSOLUTE FREEDOM","not the freedom to choose — the freedom that IS choice itself")

def vis_free_will(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(3):
        a=(i-1)*.7; qc=clamp(q*3-i*.15)
        if qc<=0: continue
        x=cx+math.cos(a)*130*qc; y=cy+math.sin(a)*130*qc
        col=[CRIMSON,CYAN,GREEN][i]; d.line((cx,cy,x,y),fill=(*col,int(170*qc)),width=3)
        d.ellipse((x-12*qc,y-12*qc,x+12*qc,y+12*qc),fill=(*col,int(160*qc)))
        labels=['DETERMINISM','FREEDOM','CHOICE']; centered(d,(x,y+22*qc),labels[i],font(FONT_SANS_BOLD,int(h*.020)),col)
    seal(im,"FREE WILL IS REAL","not the freedom to choose what you want — the freedom to BE what you choose")

def vis_consciousness(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+120*q),cy+math.sin(i*math.tau/30)*(30+120*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),GOLD,4,230,16)
    centered(d,(cx,cy),"SVĀTANTRYA",font(FONT_SERIF_BOLD,int(h*.045)),(*GOLD,int(210*q)))
    centered(d,(cx,cy+35),"ABSOLUTE FREEDOM",font(FONT_SANS,int(h*.025)),(*PALE_GOLD,int(160*q)))
    for i in range(6):
        a=i*math.tau/6+t*.05; rad=30+100*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,5+3*q,PALE_GOLD,int(140*q),6)
    seal(im,"CONSCIOUSNESS IS FREEDOM","freedom is not a property of consciousness — it IS consciousness")

def vis_ground(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+130*q),cy+math.sin(i*math.tau/40)*(30+130*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),GOLD,5,240,18)
    centered(d,(cx,cy),chr(8734),font(FONT_SERIF_BOLD,int(h*.10)),(*GOLD,int(210*q)))
    for i in range(8):
        a=i*math.tau/8+t*.04; rad=50+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        d.ellipse((x-4*q,y-4*q,x+4*q,y+4*q),fill=(*PALE_GOLD,int(140*q)))
    seal(im,"FREEDOM IS THE GROUND","freedom is not something you achieve — it is what you are before you are anything")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"PHYSICS AND CAUSALITY",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"ABSOLUTE FREEDOM",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE DESCRIBES WHAT IS NECESSARY","FREEDOM ASKS WHY THERE IS NECESSITY AT ALL")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("SVĀTANTRYA MEANS YOU CAN VIOLATE PHYSICS","CATEGORY ERROR — FREEDOM IS THE GROUND OF LAW",CRIMSON),
        ("FREEDOM CONTRADICTS SCIENCE","FREEDOM AND LAW ARE DIFFERENT DOMAINS",CRIMSON),
        ("CAUSALITY IS A SUBSET OF FREEDOM","CENTRAL CLAIM OF TRIKA ŚAIVISM",GREEN),
        ("RECOGNITION REVEALS BONDAGE AS CHOICE","SUPPORTED BY EXPERIENTIAL REPORTS",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DO NOT CONFUSE METAPHYSICAL AND PHYSICAL FREEDOM","svātantrya is the ground of causality — not a violation of it")

VISUALS = {
    "svatantrya":vis_svatantrya,"causality":vis_causality,"kancukas":vis_kancukas,
    "choice":vis_choice,"physics":vis_physics,"paradox":vis_paradox,
    "living":vis_living,"contraction":vis_contraction,"absolute":vis_absolute,
    "free_will":vis_free_will,"consciousness":vis_consciousness,"ground":vis_ground,
    "bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("Svātantrya: Absolute Freedom","Consciousness IS freedom — the ground of all causality.",9.0,"svatantrya",{}),
    Scene("Freedom Before Being","Freedom is not a property of consciousness. It IS consciousness.",9.0,"svatantrya",{}),
    Scene("The Ground","Before any constraint, there is the freedom that chooses constraint.",9.0,"svatantrya",{}),
    Scene("Causality is Derived","Freedom contracts into law. Causality is a subset of freedom.",9.0,"causality",{}),
    Scene("Law is Chosen","The laws of physics are not imposed on consciousness. Consciousness chooses them.",9.0,"causality",{}),
    Scene("The Subset","Every causal relation is a freely chosen limitation of absolute freedom.",8.5,"causality",{}),
    Scene("The Kañcukas as Self-Limitation","Freedom choosing to appear constrained.",9.0,"kancukas",{}),
    Scene("The Five Coverings","Time, space, causality, knowledge, agency — each is a limitation freely chosen.",9.0,"kancukas",{}),
    Scene("The Voluntary Chains","The kañcukas are not punishments. They are freedoms chosen for experience.",9.0,"kancukas",{}),
    Scene("Choice is Not an Illusion","Every moment is a free act of consciousness.",8.5,"choice",{}),
    Scene("The Free Act","Every action is free. We just forget we chose it.",8.5,"choice",{}),
    Scene("The Contracted Choice","Even the experience of being constrained is a choice.",8.5,"choice",{}),
    Scene("Physics Describes Constraints","Not why there are constraints. Freedom is the why.",8.5,"physics",{}),
    Scene("The Why Behind the How","Physics answers 'how' things behave. Freedom answers 'why' there is behavior at all.",9.0,"physics",{}),
    Scene("The Limits of Science","Science can describe every law. It cannot explain why there is law rather than chaos.",9.0,"physics",{}),
    Scene("The Paradox of Freedom","To be free includes appearing unfree. The game of limitation.",9.0,"paradox",{}),
    Scene("The Play of Consciousness","The Absolute plays hide-and-seek with itself. The hiding is the game.",9.0,"paradox",{}),
    Scene("The Lila","Creation is not work. It is play. And play requires not knowing the outcome.",9.0,"paradox",{}),
    Scene("Living from Freedom","Acting without bondage to the past. The liberated life.",9.5,"living",{}),
    Scene("The Free Life","When you know you are free, action becomes effortless.",9.0,"living",{}),
    Scene("Spontaneity","The liberated being acts spontaneously — not from impulse, from freedom.",9.0,"living",{}),
    Scene("Freedom Contracts","Freedom limits itself to experience limitation — the game of consciousness.",9.5,"contraction",{}),
    Scene("The Descent","Freedom descends through the kañcukas to experience finitude.",9.0,"contraction",{}),
    Scene("The Ascent","Recognition reverses the descent. The kañcukas are seen as freely chosen.",9.0,"contraction",{}),
    Scene("Absolute Freedom","Not the freedom to choose — the freedom that IS choice itself.",10.0,"absolute",{}),
    Scene("The Freedom Beyond Choice","Choice implies alternatives. Absolute freedom is prior to alternatives.",9.5,"absolute",{}),
    Scene("Unbounded","Svātantrya has no object, no direction, no content. It is the pure capacity for all.",9.5,"absolute",{}),
    Scene("Free Will is Real","Not the freedom to choose what you want — the freedom to BE what you choose.",9.0,"free_will",{}),
    Scene("Beyond Determinism","Determinism is a perspective within freedom. It describes what freedom has chosen.",9.0,"free_will",{}),
    Scene("The Free Witness","Before every choice, there is the witness who is already free.",9.0,"free_will",{}),
    Scene("Consciousness is Freedom","Freedom is not a property of consciousness — it IS consciousness.",10.0,"consciousness",{}),
    Scene("The Identity","There is no consciousness that is not free. Freedom is its essential nature.",9.5,"consciousness",{}),
    Scene("The Recognition","Recognizing this is liberation. You are not becoming free. You are knowing you are free.",9.5,"consciousness",{}),
    Scene("Freedom is the Ground","Freedom is not something you achieve — it is what you are before you are anything.",10.0,"ground",{}),
    Scene("The Unborn","Before you were born, you were free. After you die, you are free. Now you only appear constrained.",9.5,"ground",{}),
    Scene("The Eternal Freedom","What you seek is what you are. The seeking is the veil.",9.5,"ground",{}),
    Scene("Science Bridge","Physics describes what is necessary. Freedom asks why there is necessity at all.",9.0,"bridge",{}),
    Scene("The Prior Question","Science asks 'how.' Freedom asks 'why.' Both questions are valid.",9.0,"bridge",{}),
    Scene("The Complementarity","Freedom and causality are not opposed. They are nested: causality within freedom.",9.0,"bridge",{}),
    Scene("Caution","Svātantrya is the ground of causality — not a violation of it.",8.5,"caution",{}),
    Scene("Not License","Absolute freedom does not mean you can break the laws of physics. It means you chose them.",9.0,"caution",{}),
    Scene("The Discipline","Freedom is not an excuse. It is the deepest responsibility.",8.5,"caution",{}),
    Scene("Closing","Freedom comes before causality. Svātantrya is not a property of consciousness — it IS consciousness. The laws of nature are freedoms that have contracted into regularities. And liberation is not the removal of constraint. It is the recognition that every constraint was freely chosen.",10.0,"absolute",{}),
]

def render_frame(s,fi,fc,w,h,seed):
    u=fi/max(1,fc-1); t=u*s.duration
    im=field(w,h,seed); VISUALS[s.visual](im,u,t,s.params); border(im)
    return im.convert("RGB")
def ffmpeg_path():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg required")
    return exe
def encode_scene(idx,fps):
    fd=FRAMES/f"scene_{idx:03d}"; o=SCENES_DIR/f"scene_{idx:03d}.mp4"
    subprocess.run([ffmpeg_path(),"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def render_scene(idx,s,fps,w,h,prev):
    fd=FRAMES/f"scene_{idx:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    cnt=max(2,round(s.duration*fps))
    if prev:
        for oi,fi in enumerate([0,int(cnt*.33),int(cnt*.72),cnt-1]):
            render_frame(s,fi,cnt,w,h,idx*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(cnt):
        p=fd/f"{fi:05d}.jpg"
        if p.exists(): continue
        render_frame(s,fi,cnt,w,h,idx*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(idx,fps)
def concat(paths):
    txt=OUTPUT/"concat.txt"; txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    o=OUTPUT/"svatantrya_freedom.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"freedom comes before causality","subtitle":"svātantrya as the ground of all experience",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"unbounded golden field contracting into a grid",
        "visual_arc":["freedom","causality","kancukas","choice","paradox","recognition"],
        "scenes":recs},indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def contact_sheet(w,h):
    tw=320; th=int(tw*h/w); cols=4; rows=math.ceil(len(SCENES)/4); ch=th+48
    s=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(s); lf=font(FONT_SANS_BOLD,14)
    for i,sc in enumerate(SCENES,1):
        cnt=max(2,round(sc.duration*DEFAULT_FPS))
        im=render_frame(sc,int(cnt*.72),cnt,w,h,i*10000+72); im.thumbnail((tw,th))
        sl=i-1; x=(sl%cols)*tw; y=(sl//cols)*ch; s.paste(im,(x,y))
        d.text((x+8,y+th+7),f"{i:02d}  {sc.title}",font=lf,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; s.save(p,quality=94); return p
def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS); p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT); p.add_argument("--scene",type=int)
    p.add_argument("--preview",action="store_true"); p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()
def main():
    a=parse_args(); OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_timeline()}"); print(f"Scenes: {len(SCENES)}"); print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} min")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError("scene out of range")
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rendered.append(r)
    if not a.no_contact_sheet: print(f"Contact: {contact_sheet(a.width,a.height)}")
    if not a.preview: print(f"Final: {concat(rendered)}")
if __name__=="__main__": main()
