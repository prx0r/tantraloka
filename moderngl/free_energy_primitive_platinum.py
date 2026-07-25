#!/usr/bin/env python3
"""
EVERY LIVING SYSTEM MINIMIZES SURPRISE — The Free Energy Principle
Friston's unified theory of self-organization.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Every self-organizing system — from a bacterium to a brain to a society —
acts to minimize its free energy, where free energy is an upper bound on
surprise. Surprise is information the system cannot predict. By minimizing
surprise through perception and action, the system maintains its boundaries
(Markov blankets) and preserves its integrity.

For Friston, this is not a metaphor. It is a mathematical principle that
applies to anything that persists.

FILM THESIS
-----------
The modern picture often runs:

organism → senses world → builds model → acts → learns

The free-energy picture can be staged as:

organism has a generative model
→ predicts sensory input
→ prediction error = free energy
→ perception updates the model
→ action changes the world to match predictions
→ precision weights which errors matter
→ the self is the model

Everything that exists does so because it minimizes surprise.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a descending cascade of prediction error that resolves into order.
• Final reveal: the system that minimizes surprise is the self.

OUTPUT
------
output_free_energy_primitive/
  frames/
  scenes/
  free_energy_primitive.mp4
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
OUTPUT = ROOT / "output_free_energy_primitive"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH=1280; DEFAULT_HEIGHT=720; DEFAULT_FPS=10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
CYAN=(57,156,180); PALE_CYAN=(196,227,233); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); CRIMSON=(162,58,69); VIOLET=(109,83,153)
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

def vis_principle(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,16,CYAN,int(190*q),12)
    for i in range(8):
        a=i*math.tau/8+t*.06; qc=clamp(q*3-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+90*qc); y=cy+math.sin(a)*(20+90*qc)*.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(160*qc)),width=2)
        glow_circle(im,x,y,5+3*qc,PALE_CYAN,int(140*qc),6)
    seal(im,"THE FREE ENERGY PRINCIPLE","self-organizing systems minimize surprise")

def vis_prediction(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(12):
        a=i*math.tau/12+t*.05; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+100*qc); y=cy+math.sin(a)*(20+100*qc)*.35
        col=mix(PALE_CYAN,CYAN,.5+.5*math.sin(t+i))
        d.line((cx,cy,x,y),fill=(*col,int(150*qc)),width=2)
        d.ellipse((x-6*qc,y-6*qc,x+6*qc,y+6*qc),fill=(*col,int(150*qc)))
    seal(im,"PREDICTIVE PROCESSING","the brain predicts and updates — perception is controlled hallucination")

def vis_active(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        a=i*math.tau/6+r*.4; qc=clamp(q*3-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+80*qc); y=cy+math.sin(a)*(40+80*qc)*.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(170*qc)),width=3)
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),GOLD,2,8)
    glow_circle(im,cx,cy,12,GOLD,int(180*q),10)
    seal(im,"ACTIVE INFERENCE","action makes the world match the prediction")

def vis_markov(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    d.ellipse((cx-100*q,cy-80*q,cx+100*q,cy+80*q),outline=(*INK,int(170*q)),width=3)
    d.ellipse((cx-50*q,cy-40*q,cx+50*q,cy+40*q),outline=(*GOLD,int(150*q)),width=2)
    glow_circle(im,cx,cy,10,CYAN,int(160*q),8)
    centered(d,(cx,cy-30*q),"SELF",font(FONT_SANS_BOLD,int(h*.025)),GOLD)
    centered(d,(cx,cy+50*q),"WORLD",font(FONT_SANS_BOLD,int(h*.025)),INK)
    seal(im,"MARKOV BLANKETS","boundary between self and world — actively maintained")

def vis_surprise(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(10):
        a=i*math.tau/10+t*.08; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        col=GREEN if qc>.6 else CRIMSON
        d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        glow_circle(im,x,y,5+3*qc,col,int(150*qc),6)
    seal(im,"SURPRISE IS INFORMATION","error is the engine of learning")

def vis_hierarchy(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(5):
        qc=clamp(q*5-i)
        if qc<=0: continue
        y=lerp(h*.20,h*.67,i/4); rad=lerp(60,15,i/4); col=mix(CYAN,GOLD,i/4)
        d.ellipse((w*.50-rad*qc,y-rad*qc,w*.50+rad*qc,y+rad*qc),outline=(*col,int(180*qc)),width=2)
    seal(im,"HIERARCHICAL INFERENCE","deep models at multiple scales")

def vis_self(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(180*q),10)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+90*qc); y=cy+math.sin(a)*(40+90*qc)*.35
        d.line((cx,cy,x,y),fill=(*mix(CYAN,GOLD,i/7),int(160*qc)),width=2)
        d.ellipse((x-8*qc,y-8*qc,x+8*qc,y+8*qc),outline=(*PALE_GOLD,int(140*qc)),width=2)
    seal(im,"THE SELF IS A PREDICTION","you are your brain's best guess")

def vis_precision(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        y=lerp(h*.20,h*.67,i/5); width=lerp(200,40,i/5)*qc
        d.line((w*.50-width/2,y,w*.50+width/2,y),fill=(*CYAN,int(200*qc)),width=4)
    seal(im,"PRECISION WEIGHTING","attention modulates gain on prediction error")

def vis_free_energy(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+110*q),cy+math.sin(i*math.tau/30)*(30+110*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),GOLD,4,220,14)
    for i in range(5):
        a=i*math.tau/5+r*.5; x=cx+math.cos(a)*80*q; y=cy+math.sin(a)*80*q*.35
        d.line((cx,cy,x,y),fill=(*GREEN,int(160*q)),width=2)
    seal(im,"FREE ENERGY IS LIFE","the principle that every living system enacts")

def vis_niche(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,CYAN,int(180*q),10)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        col=mix(CYAN,GREEN,i/7); d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        d.ellipse((x-8*qc,y-8*qc,x+8*qc,y+8*qc),fill=(*col,int(150*qc)))
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),col,2,8)
    seal(im,"NICHE CONSTRUCTION","organisms do not adapt to the world — they build the world they adapt to")

def vis_curiosity(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(180*q),10)
    for i in range(10):
        a=i*math.tau/10+t*.07; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+110*qc); y=cy+math.sin(a)*(30+110*qc)*.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(150*qc)),width=2)
        d.ellipse((x-8*qc,y-8*qc,x+8*qc,y+8*qc),fill=(*PALE_CYAN,int(130*qc)))
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),CYAN,2,7)
    seal(im,"CURIOSITY IS EPISTEMIC VALUE","we seek information that resolves uncertainty")

def vis_cultural(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(7):
        qc=clamp(q*7-i)
        if qc<=0: continue
        y=lerp(h*.20,h*.65,i/6); col=mix(CYAN,GOLD,i/6)
        width=lerp(30,260,i/6)*qc
        d.line((w*.50-width/2,y,w*.50+width/2,y),fill=(*col,int(190*qc)),width=4)
        centered(d,(w*.50,y-14),f"SCALE {i+1}",font(FONT_SANS_BOLD,int(h*.017)),(*col,int(180*qc)))
    seal(im,"CULTURAL EVOLUTION","free energy minimization scales from cells to societies")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"BAYESIAN BRAIN",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"SELF-ORGANIZATION",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"THE FREE ENERGY PRINCIPLE BRIDGES PHYSICS AND BIOLOGY","from thermodynamics to consciousness — the same principle")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("FEP IS NOT A THEORY OF EVERYTHING","IT IS A MATHEMATICAL FRAMEWORK",CRIMSON),
        ("ALL SYSTEMS MINIMIZE FREE ENERGY","SUPPORTED — EVERYTHING THAT PERSISTS",GREEN),
        ("FEP EXPLAINS CONSCIOUSNESS","NOT ESTABLISHED — IT EXPLAINS ADAPTIVE BEHAVIOR",CRIMSON),
        ("PREDICTION ERROR DRIVES LEARNING","SUPPORTED BY NEUROSCIENCE",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"THE FEP IS A FRAMEWORK — NOT A DOCTRINE","it unifies but does not replace domain-specific theories")

VISUALS = {
    "principle":vis_principle,"prediction":vis_prediction,"active":vis_active,
    "markov":vis_markov,"surprise":vis_surprise,"hierarchy":vis_hierarchy,
    "self":vis_self,"precision":vis_precision,"free_energy":vis_free_energy,
    "niche":vis_niche,"curiosity":vis_curiosity,"cultural":vis_cultural,
    "bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("The Free Energy Principle","Self-organizing systems minimize surprise — the first law of life.",9.0,"principle",{}),
    Scene("Surprise Bound","Free energy is an upper bound on surprise. Minimize the bound and you minimize surprise.",9.0,"principle",{}),
    Scene("The Universal Principle","From bacteria to societies — the same principle at every scale.",9.0,"principle",{}),
    Scene("Predictive Processing","The brain predicts and updates — perception is controlled hallucination.",9.0,"prediction",{}),
    Scene("The Generative Model","Every organism has a model of its world. Perception is model updating.",8.5,"prediction",{}),
    Scene("Top-Down and Bottom-Up","Predictions flow down. Prediction errors flow up. The brain is a hypothesis tester.",8.5,"prediction",{}),
    Scene("Active Inference","Action makes the world match the prediction — moving to minimize surprise.",9.0,"active",{}),
    Scene("Perception and Action","Perception updates the model. Action changes the world. Both minimize free energy.",8.5,"active",{}),
    Scene("The Action-Perception Loop","The loop is closed: predict, perceive, act, re-predict.",8.5,"active",{}),
    Scene("Markov Blankets","Boundary between self and world — actively maintained by every living system.",9.0,"markov",{}),
    Scene("The Statistical Boundary","A Markov blanket separates internal states from external states. The blanket IS the self.",9.0,"markov",{}),
    Scene("Active Maintenance","The blanket is not passive. It is continuously maintained by action.",9.0,"markov",{}),
    Scene("Surprise is Information","Error is the engine of learning — prediction error drives adaptation.",8.5,"surprise",{}),
    Scene("The Error Signal","Without error, no learning. Surprise is the fuel of all intelligence.",8.5,"surprise",{}),
    Scene("Expected Surprise","Not all surprise is equal. Expected surprise is epistemic value.",8.5,"surprise",{}),
    Scene("Hierarchical Inference","Deep models at multiple scales — the brain is a deep prediction engine.",8.5,"hierarchy",{}),
    Scene("Levels of Abstraction","Lower levels predict sensory details. Higher levels predict abstract patterns.",8.5,"hierarchy",{}),
    Scene("Scale and Time","Higher levels integrate over longer timescales. The hierarchy IS time.",8.5,"hierarchy",{}),
    Scene("The Self is a Prediction","You are your brain's best guess — the self is a generative model.",9.0,"self",{}),
    Scene("The Bayesian Self","The self is not a thing. It is the most persistent prediction your brain makes.",9.0,"self",{}),
    Scene("Self-Evidence","To exist is to model. The model that persists minimizes surprise.",9.0,"self",{}),
    Scene("Precision Weighting","Attention modulates the gain on prediction error — the anatomy of focus.",8.5,"precision",{}),
    Scene("The Gain Control","Not all prediction errors are equal. Precision weights determine what matters.",8.5,"precision",{}),
    Scene("Attention as Precision","Attention is the process of optimizing precision weights.",8.5,"precision",{}),
    Scene("Free Energy is Life","The principle that every living system enacts — necessity becomes freedom.",9.5,"free_energy",{}),
    Scene("Life as Inference","To live is to infer. Every living system is an inference machine.",9.5,"free_energy",{}),
    Scene("The Variational Imperative","Free energy is a variational bound on surprise. All life optimizes this bound.",9.0,"free_energy",{}),
    Scene("Niche Construction","Organisms do not adapt to the world — they build the world they adapt to.",9.0,"niche",{}),
    Scene("The Extended Organism","The niche is part of the organism's model. Building the niche is model updating.",9.0,"niche",{}),
    Scene("Ecosystem Inference","Ecosystems minimize free energy collectively. Cooperation is variational.",9.0,"niche",{}),
    Scene("Curiosity is Epistemic Value","We seek information that resolves uncertainty. Knowledge reduces free energy.",9.0,"curiosity",{}),
    Scene("The Drive to Know","Curiosity is not a luxury. It is a biological imperative to reduce uncertainty.",8.5,"curiosity",{}),
    Scene("Epistemic Foraging","We explore to resolve uncertainty. Information is the most valuable resource.",8.5,"curiosity",{}),
    Scene("Cultural Evolution","Free energy minimization scales from cells to societies — the same principle.",9.5,"cultural",{}),
    Scene("The Social Blanket","Societies maintain boundaries. Cultures are collective generative models.",9.0,"cultural",{}),
    Scene("Global Inference","Humanity is a planetary inference system. We are minimizing free energy together.",9.5,"cultural",{}),
    Scene("Science Bridge","The Bayesian brain hypothesis confirms predictive processing in neural systems.",9.0,"bridge",{}),
    Scene("Neuroimaging","Prediction error signals are observed in the cortex. The brain is Bayesian.",8.5,"bridge",{}),
    Scene("The Mathematical Foundation","Free energy is a mathematical principle. It bridges physics, biology, and cognitive science.",9.0,"bridge",{}),
    Scene("Caution","The FEP is a framework — it does not replace domain-specific theories.",8.5,"caution",{}),
    Scene("Not Pansychism","The FEP does not claim everything is conscious. It claims everything that persists minimizes free energy.",9.0,"caution",{}),
    Scene("The Proper Scope","The FEP applies to systems with Markov blankets. Not to rocks, not to atoms.",9.0,"caution",{}),
    Scene("Closing","Every living system minimizes surprise. Free energy is the imperative of existence. From bacteria to brains to civilizations — the same principle holds. The self is a prediction. The world is a model. And life is the ongoing act of making the model match what comes.",10.0,"free_energy",{}),
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
    o=OUTPUT/"free_energy_primitive.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"every living system minimizes surprise","subtitle":"Friston's free energy principle",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"descending cascade of prediction error resolving into order",
        "visual_arc":["principle","prediction","active inference","markov blankets","hierarchy","free energy"],
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
