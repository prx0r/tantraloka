#!/usr/bin/env python3
"""
OBJECTS ARE FROZEN ACTIONS — Kriyā-Śakti and the Verb Universe
Reality is verbs masquerading as nouns.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
What appears as a static object is actually a stabilized process —
action slowed to the point of appearing solid. A tree is the act of tree-ing.
A mountain is the act of mountain-ing. The self is the act of self-ing.
Consciousness does not act: it IS action.

For the Trika Śaiva tradition: kriyā-śakti is the power of consciousness
to take the form of its own actions. Objects are not products of action.
They are action, perceived at a temporal resolution that freezes motion
into form.

FILM THESIS
-----------
The modern picture often runs:

things exist → they have properties → they interact

The kriyā-śakti picture can be staged as:

pure action (kriyā-śakti)
→ action stabilizes into patterns
→ patterns appear as objects
→ perception freezes the flux
→ language names the frozen pattern
→ the noun obscures the verb

To see reality clearly is to see action everywhere — including in yourself.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a waveform that decelerates until it appears as a particle.
• Final reveal: the particle was always a wave — and so are you.

OUTPUT
------
output_objects_as_actions/
  frames/
  scenes/
  objects_as_actions.mp4
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
OUTPUT = ROOT / "output_objects_as_actions"
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
    arr+=rng.normal(0,.9,(h,w,1)); yy,xx=np.mgrid[0:h,0:w]
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

def vis_tree(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(40+100*q),cy+math.sin(i*math.tau/30)*(40+100*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),GOLD,3,200,12)
    glow_circle(im,cx,cy,12,GOLD,int(180*q),10)
    seal(im,"A TREE IS THE ACT OF TREE-ING","reality is verbs masquerading as nouns")

def vis_kriya(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(10):
        a=i*math.tau/10+t*.06; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+100*qc); y=cy+math.sin(a)*(20+100*qc)*.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(160*qc)),width=2)
        d.ellipse((x-5*qc,y-5*qc,x+5*qc,y+5*qc),fill=(*PALE_CYAN,int(150*qc)))
    seal(im,"KRIYĀ-ŚAKTI","consciousness does not act — it IS action")

def vis_stability(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+90*qc); y=cy+math.sin(a)*(30+90*qc)*.35
        d.line((cx,cy,x,y),fill=(*INK,int(150*qc)),width=2)
        d.ellipse((x-6*qc,y-6*qc,x+6*qc,y+6*qc),outline=(*INK,int(140*qc)),width=1)
    seal(im,"STABILITY IS RATE","an object is slowed activity — matter is frozen energy")

def vis_process(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        y=lerp(h*.20,h*.65,i/5); width=lerp(50,250,i/5)*qc
        col=mix(GOLD,CYAN,i/5); d.line((w*.50-width/2,y,w*.50+width/2,y),fill=(*col,int(180*qc)),width=4)
    seal(im,"EVERYTHING IS PROCESS","matter is energy slowed to the point of appearing solid")

def vis_perception(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(180*q),10)
    for i in range(8):
        a=i*math.tau/8+t*.06; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        col=mix(VIOLET,PALE_GOLD,i/7); d.line((cx,cy,x,y),fill=(*col,int(150*qc)),width=2)
    seal(im,"PERCEPTION FREEZES ACTION","seeing solidifies the flux — the observer crystallizes the observed")

def vis_identity(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/35)*(40+110*q),cy+math.sin(i*math.tau/35)*(40+110*q)*.35) for i in range(36)]
    glow_line(im,partial(pts,q),GOLD,4,220,14)
    centered(d,(cx,cy),'~',font(FONT_SERIF_BOLD,int(h*.080)),(*GOLD,int(200*q)))
    seal(im,"YOU ARE NOT A THING","you are a verb — activity recognizing itself as activity")

def vis_wave_particle(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[]
    for i in range(100):
        f=i/99; x=lerp(w*.10,w*.90,f)
        amp=(40-30*f)*q; y=cy+math.sin(f*math.tau*6+t*3)*amp
        pts.append((x,y))
    glow_line(im,partial(pts,q),CYAN,3,180,12)
    if q>.6:
        qc=(q-.6)/.4; cx2=w*.50
        for j in range(5):
            a=j*math.tau/5; rad=80*qc; x2=cx2+math.cos(a)*rad; y2=cy+math.sin(a)*rad*.35
            d.ellipse((x2-8*qc,y2-8*qc,x2+8*qc,y2+8*qc),fill=(*GOLD,int(200*qc)))
    seal(im,"WAVE AND PARTICLE","action is the wave — the object is the particle. Both are real")

def vis_field(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(8):
        a=i*math.tau/8+t*.06; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+110*qc); y=cy+math.sin(a)*(30+110*qc)*.35
        col=mix(GOLD,CYAN,i/7)
        d.line((cx,cy,x,y),fill=(*col,int(170*qc)),width=3)
        d.ellipse((x-8*qc,y-8*qc,x+8*qc,y+8*qc),fill=(*col,int(150*qc)))
        if qc>.6: centered(d,(x,y+20*qc),'ACT',font(FONT_SANS_BOLD,int(h*.018)),col)
    seal(im,"THE ACTION FIELD","every point in space is a potential action")

def vis_verb_world(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+120*q),cy+math.sin(i*math.tau/40)*(30+120*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),CYAN,4,210,14)
    labels=['FLOWING','BECOMING','DANCING','SINGING','LOVING','KNOWING']
    for i,l in enumerate(labels):
        a=i*math.tau/len(labels)+t*.05; qc=clamp(q*6-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+100*qc); y=cy+math.sin(a)*(40+100*qc)*.35
        centered(d,(x,y),l,font(FONT_SERIF,int(h*.020)),(*GOLD,int(180*qc)))
    seal(im,"THE VERB WORLD","reality is not made of things — it is made of actions we have learned to ignore")

def vis_noun_illusion(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+110*q),cy+math.sin(i*math.tau/30)*(30+110*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),CYAN,4,210,14)
    labels=['TABLE','CHAIR','MOUNTAIN','RIVER','SELF']
    for i,l in enumerate(labels):
        a=i*math.tau/len(labels)+t*.05; qc=clamp(q*5-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+100*qc); y=cy+math.sin(a)*(40+100*qc)*.35
        d.ellipse((x-10*qc,y-10*qc,x+10*qc,y+10*qc),outline=(*GOLD,int(150*qc)),width=2)
        centered(d,(x,y+16*qc),l,font(FONT_SERIF,int(h*.019)),GOLD)
    seal(im,"THE NOUN ILLUSION","nouns are frozen verbs — language tricks us into believing in static things")

def vis_flow(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for j in range(3):
        pts=[]
        for i in range(60):
            f=i/59; x=lerp(w*.10,w*.90,f)
            y=cy+math.sin(f*math.tau*(4+j*2)+t*2+q*math.tau)*(15+j*5)*q
            pts.append((x,y))
        col=mix(CYAN,GOLD,j/2)
        glow_line(im,partial(pts,q),col,width=3-j,alpha=int(180-40*j)*q,blur=8+j*2)
    glow_circle(im,cx,cy,10,GOLD,int(170*q),9)
    seal(im,"THE FLOW OF ACTION","reality is a continuous flowing action appearing as objects")

def vis_process_reality(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for j in range(4):
        pts=[]
        for i in range(60):
            f=i/59; x=lerp(w*.10,w*.90,f); freq=3+j*1.5
            y=cy+math.sin(f*math.tau*freq+t*1.5+q*math.tau)*(12+8*j)*q
            pts.append((x,y))
        col=mix(CYAN,GOLD,j/3)
        glow_line(im,partial(pts,q),col,width=2+j,alpha=int(170-30*j)*q,blur=8+j*2)
    seal(im,"PROCESS IS THE SUBSTANCE","the world is not made of matter — it is made of processes interacting")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"QUANTUM FIELD THEORY",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"KRIYĀ-ŚAKTI",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"PHYSICS CONFIRMS: PARTICLES ARE FIELD EXCITATIONS","quantum fields are actions — exactly as the Tantric tradition describes")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("OBJECTS DON'T EXIST","OBJECTS EXIST AS STABILIZED ACTIONS",CRIMSON),
        ("KRIYĀ-ŚAKTI IS A SCIENTIFIC THEORY","IT IS A METAPHYSICAL PRINCIPLE",CRIMSON),
        ("PERCEPTION FREEZES THE FLUX","SUPPORTED BY COGNITIVE SCIENCE",GREEN),
        ("THE SELF IS A VERB","SUPPORTED BY NEUROSCIENCE OF PLASTICITY",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"OBJECTS ARE NOT ILLUSIONS — THEY ARE STABILIZED ACTIONS","the table is real. It is also a dance.")

VISUALS = {
    "tree":vis_tree,"kriya":vis_kriya,"stability":vis_stability,"process":vis_process,
    "perception":vis_perception,"identity":vis_identity,"wave_particle":vis_wave_particle,
    "field":vis_field,"verb_world":vis_verb_world,"noun_illusion":vis_noun_illusion,
    "flow":vis_flow,"process_reality":vis_process_reality,"bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("A Tree IS the Act of Tree-ing","Reality is verbs masquerading as nouns.",9.0,"tree",{}),
    Scene("The Verb Nature of Everything","What you call a table is a temporary stabilization of activity.",8.5,"tree",{}),
    Scene("The Mountain is Moving","The mountain is not static. It is the act of mountain-ing.",8.5,"tree",{}),
    Scene("Kriyā-Śakti","Consciousness does not act — it IS action.",9.0,"kriya",{}),
    Scene("The Power of Action","Kriyā-śakti is the power of consciousness to take the form of its own actions.",9.0,"kriya",{}),
    Scene("Consciousness as Verb","Consciousness is not a thing that acts. It is action that appears as a thing.",9.0,"kriya",{}),
    Scene("Stability is Rate","An object is slowed activity. Matter is frozen energy.",8.5,"stability",{}),
    Scene("The Speed of Being","What we call solid is action oscillating too fast to perceive.",8.5,"stability",{}),
    Scene("Frozen Light","Matter is congealed energy. The solid is a slow dance.",8.5,"stability",{}),
    Scene("Everything is Process","Matter is energy slowed to the point of appearing solid.",8.5,"process",{}),
    Scene("The Process Universe","The universe is not a collection of things. It is a collection of events.",9.0,"process",{}),
    Scene("From Physics to Metaphysics","Quantum field theory agrees: fields are primary, particles are excitations.",9.0,"process",{}),
    Scene("Perception Freezes Action","Seeing solidifies the flux. The observer crystallizes the observed.",9.0,"perception",{}),
    Scene("The Crystallizing Gaze","Attention freezes movement into shape. Without perception, everything is flux.",9.0,"perception",{}),
    Scene("The Role of the Observer","Perception is not passive. It participates in the stabilization of reality.",8.5,"perception",{}),
    Scene("You Are Not a Thing","You are a verb — activity recognizing itself as activity.",9.5,"identity",{}),
    Scene("The Self as Process","The self is not a noun. It is the continuous act of self-ing.",9.5,"identity",{}),
    Scene("The Recognizing Verb","When activity recognizes itself as activity — that is consciousness.",9.5,"identity",{}),
    Scene("Wave and Particle","Action is the wave — the object is the particle. Both are real.",9.0,"wave_particle",{}),
    Scene("The Complementarity","Wave and particle are not opposites. They are the same action at different resolutions.",9.0,"wave_particle",{}),
    Scene("Quantum Analogy","The quantum wave-particle duality is physics expressing the same truth: action precedes form.",9.0,"wave_particle",{}),
    Scene("The Action Field","Every point in space is a potential action. Reality is the actualized.",9.0,"field",{}),
    Scene("Potential and Actual","The field is all possible actions. Perception selects and stabilizes.",9.0,"field",{}),
    Scene("The Unified Field","There is only one action appearing as many. The field is undivided.",9.0,"field",{}),
    Scene("The Verb World","Reality is not made of things — it is made of actions we have learned to ignore.",9.5,"verb_world",{}),
    Scene("The Dance of Verbs","Flowing, becoming, dancing, singing, loving, knowing — these are the true elements.",9.0,"verb_world",{}),
    Scene("The Frozen Verb","Every noun is a verb we no longer see moving.",9.0,"verb_world",{}),
    Scene("The Noun Illusion","Nouns are frozen verbs — language tricks us into believing in static things.",9.0,"noun_illusion",{}),
    Scene("Language Creates Reality","The subject-predicate structure of language imposes a thing-action split.",8.5,"noun_illusion",{}),
    Scene("Beyond Grammar","To see reality directly is to see through the subject-predicate structure.",9.0,"noun_illusion",{}),
    Scene("The Flow of Action","Reality is a continuous flowing action appearing as objects.",9.5,"flow",{}),
    Scene("The River of Being","Heraclitus was right: you cannot step into the same river twice.",9.0,"flow",{}),
    Scene("The Constant Dance","What appears still is only moving at a rate our perception cannot resolve.",9.0,"flow",{}),
    Scene("Process is the Substance","The world is not made of matter — it is made of processes interacting.",9.5,"process_reality",{}),
    Scene("Interacting Processes","Every object is a process nested within other processes. The universe is a process.",9.5,"process_reality",{}),
    Scene("No Final Substance","There is no ultimate stuff. There is only action all the way down.",9.5,"process_reality",{}),
    Scene("Science Bridge","Quantum field theory: fields are primary, particles are excitations of fields.",9.0,"bridge",{}),
    Scene("The Physics of Verbs","Modern physics describes a world of verbs — interactions, fields, processes.",9.0,"bridge",{}),
    Scene("The Convergence","Physics and metaphysics converge: reality is action, not substance.",9.0,"bridge",{}),
    Scene("Caution","Objects are not illusions — they are stabilized actions.",8.5,"caution",{}),
    Scene("The Table is Real","The table is real. It is also a dance. Both are true.",8.5,"caution",{}),
    Scene("The Middle Way","Neither solid matter nor empty illusion — stabilized action is the middle way.",8.5,"caution",{}),
    Scene("Closing","Objects are frozen actions. A tree is the act of tree-ing. A mountain is the act of mountain-ing. You are not a thing — you are the act of self-ing. Reality is verbs masquerading as nouns. Kriyā-śakti is the power of consciousness to take the form of its own actions. And what you call 'I' is the action recognizing itself.",10.0,"identity",{}),
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
    o=OUTPUT/"objects_as_actions.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"objects are frozen actions","subtitle":"kriyā-śakti and the verb universe",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"waveform decelerating to particle appearance",
        "visual_arc":["action","stability","perception","identity","verb world","recognition"],
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
