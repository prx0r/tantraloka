#!/usr/bin/env python3
"""
SELF AND WORLD HOLD EACH OTHER UPRIGHT
Platinum procedural visual essay — dependent arising, enactive cognition, active inference.

Adapted from:
expansion-essays/04_self_and_world_hold_each_other_upright.md

HOUSE CONTRACT
--------------
• 5–10 seconds per shot.
• Every shot performs the spoken claim as a visible transformation.
• Clean ivory scientific field.
• Genuinely animated processes, not static labelled slides.
• Sparse typography used only as conceptual seals.

PALETTE ROLES
-------------
INK      structure / base
GOLD     awareness / the field of relation
PALE_GOLD  ground of consciousness
ROSE     the self-pole
TEAL     the world-pole
CRIMSON  grasping / the loop hardening
SILVER   the reciprocal relation / the between

CONTINUITY OBJECTS
------------------
A pair of reed-arcs that lean, separate, interweave, spiral, and finally
stand parallel as light — tracking the arc of the entire argument.

OUTPUT
------
output_nature_builds_bodies/
  frames/scene_001/*.jpg
  scenes/scene_001.mp4
  self_world_upright.mp4
  narration_timeline.json
  contact_sheet.jpg

USAGE
-----
python self_world_upright_platinum.py
python self_world_upright_platinum.py --preview
python self_world_upright_platinum.py --scene 8
"""
from __future__ import annotations
import argparse,json,math,random,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_nature_builds_bodies"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94); SILVER=(180,186,192)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); ROSE=(183,113,129); TEAL=(67,157,180); CRIMSON=(158,57,66); VIOLET=(130,104,160); DARK=(24,27,32)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold"); FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0; q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def lf(p,s):
    for c in (p,FS,FSN):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rl(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,s,bg=IVORY):
    rng=np.random.default_rng(s); a=np.empty((h,w,3),dtype=np.float32); a[:]=bg
    a+=rng.normal(0,.95,(h,w,1)); yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.52)/(w*.36))**2+((yy-h*.39)/(h*.30))**2)*2.1)
    a[...,0]+=halo*1.5; a[...,1]+=halo*4; a[...,2]+=halo*5.5
    a=np.clip(a,0,255).astype(np.uint8)
    im=Image.fromarray(a,"RGB").convert("RGBA"); e=rl(im.size); d=ImageDraw.Draw(e)
    for i in range(14): al=int(i*.7); ins=20+i*3; d.rounded_rectangle((ins,ins,w-ins,h-ins),radius=16,outline=(*INK,al),width=2)
    im.alpha_composite(e); return im
def ct(d,xy,t,font,fill=INK): d.text(xy,t,font=font,fill=fill,anchor="mm")
def seal(im,t,sub="",c=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    ct(d,(w/2,h*.875),t,lf(FSB,max(20,int(h*.038))),c)
    if sub: ct(d,(w/2,h*.925),sub,lf(FSN,max(11,int(h*.018))),SOFT_INK)
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,48),width=2)
    for x,y in ((52,52),(w-52,52),(52,h-52),(w-52,h-52)):
        d.line((x-9,y,x+9,y),fill=(*SILVER,80),width=1); d.line((x,y-9,x,y+9),fill=(*SILVER,80),width=1)
def gc(im,cx,cy,r,col,al=170,bl=16):
    l=rl(im.size); ImageDraw.Draw(l).ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*col,al))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(bl)))
    c=rl(im.size); ImageDraw.Draw(c).ellipse((cx-r*.38,cy-r*.38,cx+r*.38,cy+r*.38),fill=(*mix(col,WHITE,.35),min(255,al+55)))
    im.alpha_composite(c)
def gl(im,pts,col,w=4,g=14,al=225):
    if len(pts)<2: return
    l=rl(im.size); ImageDraw.Draw(l).line(pts,fill=(*col,al),width=max(1,w*3),joint="curve")
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(g)))
    f=rl(im.size); ImageDraw.Draw(f).line(pts,fill=(*mix(col,WHITE,.08),min(255,al+25)),width=w,joint="curve")
    im.alpha_composite(f)
def pp(points,progress):
    progress=clamp(progress)
    if len(points)<2: return points
    ls=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]; t=sum(ls); tr=t*progress
    o=[points[0]]; w=0.0
    for i,l in enumerate(ls):
        if w+l<=tr: o.append(points[i+1]); w+=l
        else: q=0.0 if l==0 else (tr-w)/l; ax,ay=points[i]; bx,by=points[i+1]; o.append((lerp(ax,bx,q),lerp(ay,by,q))); break
    return o

def reed_bundle(cx,cy,side,span,height,count=14,curve=.35):
    pts=[]; x0=cx+side*span/2; y0=cy+height/2; x1=cx; y1=cy-height/2
    for i in range(count):
        f=i/(count-1)-.5; rx=lerp(x0,x1*side,f*curve if side>0 else 0) 
        r=[]
        for j in range(20):
            u=j/19
            x=lerp(x0+f*25,x1+f*15,u); y=lerp(y0,y1,u)
            r.append((x,y))
        pts.append(r)
    return pts

def arrow(d,a,b,col=INK,w=3,head=10):
    d.line((*a,*b),fill=col,width=w)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (-1,1):
        p=(b[0]-math.cos(ang+s*.53)*head,b[1]-math.sin(ang+s*.53)*head)
        d.line((*b,*p),fill=col,width=w)

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_reeds(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    # Draw two reed bundles leaning toward each other
    for side,color in ((-1,ROSE),(1,TEAL)):
        x0=cx+side*200; y0=cy+80; x1=cx-side*10; y1=cy-70
        for ri in range(12):
            off=(ri-5.5)*8; q=clamp(pr*1.5-ri*.04)
            if q<=0: continue
            pts=[]
            for j in range(15):
                u2=j/14; x=lerp(x0+off*side*side,x1+off*.3*side,u2); y=lerp(y0,y1,u2)
                pts.append((x,y))
            reveal=pp(pts,q)
            if len(reveal)>1: 
                gl(im,reveal,color,2,8,150)
    # Label
    if pr>.6:
        ct(d,(cx,cy+110),"NEITHER STANDS ALONE",lf(FSNB,int(h*.022)),SOFT_INK)
    seal(im,"PLACE TWO BUNDLES OF REEDS TOGETHER","lean each against the other — self and world hold each other upright")

def v_braid(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    # Two strands interweaving
    pts_self=[]; pts_world=[]
    for i in range(120):
        u2=i/119; y=150+u2*280
        if u2<=pr:
            pts_self.append((cx-40+math.sin(u2*4)*30*pr, y))
            pts_world.append((cx+40+math.sin(u2*4+math.pi)*30*pr, y))
    if len(pts_self)>1: gl(im,pts_self,ROSE,4,13,200)
    if len(pts_world)>1: gl(im,pts_world,TEAL,4,13,200)
    ct(d,(cx-80,455),"CONSCIOUSNESS",lf(FSNB,int(h*.016)),ROSE)
    ct(d,(cx+80,455),"NAME-AND-FORM",lf(FSNB,int(h*.016)),TEAL)
    seal(im,"CONSCIOUSNESS AND NAME-AND-FORM ARE RECIPROCALLY CONDITIONED","each conditions the other — the two bundles lean")

def v_not_construction(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    d.rounded_rectangle((cx-130,cy-70,cx+130,cy+70),radius=20,outline=(*INK,int(160*pr)),width=3)
    ct(d,(cx,cy),"NOT\nCONSTRUCTION",lf(FSB,int(h*.028)),INK)
    for i,lab in enumerate(["RESISTANCE","LIGHT","CHEMISTRY","OTHERS"]):
        q=clamp(pr*1.5-i*.08)
        if q<=0: continue
        x=180+i*250; y=cy+100
        d.ellipse((x-30,y-14,x+30,y+14),outline=(*TEAL,int(160*q)),fill=(*mix(IVORY,TEAL,.06),int(150*q)),width=2)
        ct(d,(x,y),lab,lf(FSN,int(h*.016)),TEAL)
    seal(im,"THE MIND DOES NOT INVENT THE WORLD FROM NOTHING","a body encounters structures not chosen by personal thought")

def v_affordance(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    objects=[("STAIR",cx-180,"climbing"),("FACE",cx,"approach"),("NOISE",cx+180,"language")]
    for i,(lab,x,aff) in enumerate(objects):
        q=clamp(pr*1.5-i*.08)
        if q<=0: continue
        d.ellipse((x-38,cy-38,x+38,cy+38),outline=(*GOLD,int(170*q)),width=3)
        ct(d,(x,cy),lab,lf(FSNB,int(h*.020)),GOLD)
        ct(d,(x,cy+55),aff,lf(FSN,int(h*.016)),SOFT_INK)
    seal(im,"A STAIR AFFORDS CLIMBING — A FACE AFFORDS APPROACH","the world is organized through relevance for a body capable of action")

def v_enaction_cycle(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    r=100; pts=[]
    for i in range(180): a=i*2*math.pi/179; pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r))
    gl(im,pp(pts,pr),GOLD,4,13,200)
    if pr>.35:
        p2=clamp((pr-.35)*1.5)
        ct(d,(cx-r-45,cy-10),"EYE",lf(FSNB,int(h*.017)),TEAL)
        ct(d,(cx+r+45,cy-10),"HAND",lf(FSNB,int(h*.017)),ROSE)
        arrow(d,(cx-r-20,cy-15),(cx-r-50,cy-15),TEAL,3,10)
        arrow(d,(cx+r+20,cy+15),(cx+r+50,cy+15),ROSE,3,10)
    ct(d,(cx,cy+75),"PERCEPTION ⇄ ACTION",lf(FSB,int(h*.022)),GOLD)
    seal(im,"THE ORGANISM ENACTS ITS WORLD THROUGH POSSIBLE ACTION","vision changes with movement — touch requires contact — attention selects by goals")

def v_hidden_side(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    # Cup with hidden side as counterfactual
    d.arc((cx-35,cy-30,cx+35,cy+30),200,340,fill=(*INK,int(170*pr)),width=3)
    d.arc((cx-35,cy-30,cx+35,cy+30),20,160,fill=(*INK,int(100*pr)),width=2)
    # Hidden side as dotted arc
    if pr>.3:
        p2=clamp((pr-.3)*1.5)
        d.arc((cx-35,cy-30,cx+35,cy+30),20,160,fill=(*GOLD,int(120*p2)),width=2)
        ct(d,(cx+70,cy-25),"COUNTERFACTUAL",lf(FSN,int(h*.016)),GOLD)
        gl(im,[(cx+35,cy-15),(cx+65,cy-15)],GOLD,1,5,100)
    seal(im,"THE HIDDEN SIDE OF A CUP IS PRESENT AS A COUNTERFACTUAL","if I rotate it, another surface will appear — the world is enacted through transformations")

def v_ai_boundary(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i,(lab,col) in enumerate([("BIOLOGICAL\nAUTONOMY",TEAL),("EXTRINSIC\nREWARD",CRIMSON)]):
        x=cx+(i-.5)*200; q=clamp(pr*1.3-i*.1)
        if q<=0: continue
        d.rounded_rectangle((x-70,cy-50,x+70,cy+50),radius=14,outline=(*col,int(170*q)),width=3)
        ct(d,(x,cy),lab,lf(FSNB,int(h*.016)),col)
    if pr>.5:
        gl(im,[(cx-130,cy),(cx+130,cy)],GOLD,3,10,150)
        ct(d,(cx,cy-70),"A REWARD FROM OUTSIDE IS NOT\nA NEED FROM INSIDE",lf(FSN,int(h*.016)),SOFT_INK)
    seal(im,"REINFORCEMENT LEARNING CAPTURES STRUCTURE","but lacks the biological autonomy central to enactivism")

def v_mirrors(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    d.rounded_rectangle((230,160,370,390),radius=16,outline=(*ROSE,int(170*pr)),width=3)
    d.rounded_rectangle((910,160,1050,390),radius=16,outline=(*TEAL,int(170*pr)),width=3)
    ct(d,(300,405),"SELF-MODEL",lf(FSNB,int(h*.016)),ROSE)
    ct(d,(980,405),"WORLD-MODEL",lf(FSNB,int(h*.016)),TEAL)
    # Connecting lines
    for i in range(6): y=190+i*35; d.line((370,y,910,y),fill=(*SILVER,int(70*pr)),width=1)
    gl(im,[(370,250),(550,220),(730,360),(910,250)],GOLD,2,10,150)
    ct(d,(640,cy+45),"THE LOOP BECOMES STABLE ENOUGH\nTO FEEL DISCOVERED",lf(FSN,int(h*.016)),SOFT_INK)
    seal(im,"EACH POLE CONFIRMS THE OTHER","the self says 'this is happening to me' — the world says 'this is the kind of place where that self exists'")

def v_grasping(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    spirals=2+3*pr; pts=[]
    for i in range(250):
        u2=i/249; a=u2*spirals*2*math.pi; r=10+u2*170*pr
        if u2<=pr: pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.65))
    if len(pts)>1: gl(im,pts,mix(CRIMSON,GOLD,.3),4,14,200)
    for i in range(15):
        u2=clamp(pr*i/15); spirals=2+3*pr; a=u2*spirals*2*math.pi+i; r=12+u2*160*pr
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.65
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(CRIMSON,GL,i/15),160))
    seal(im,"GRASPING HARDENS THE LOOP","a painful self-model predicts rejection — attention finds signs — action becomes defensive")

def v_self_evidencing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    # Self-evidencing cycle
    d.ellipse((cx-100,cy-80,cx+100,cy+80),outline=(*INK,int(160*pr)),width=3)
    for i,(lab,col) in enumerate([("MINE",CRIMSON),("FOR ME",TEAL),("AGAINST ME",VIOLET),("WHAT I MUST\nBECOME",SOFT_INK)]):
        a=-math.pi/2+i*2*math.pi/4; x=cx+math.cos(a)*140; y=cy+math.sin(a)*100
        q=clamp(pr*1.3-i*.07)
        if q<=0: continue
        ct(d,(x,y),lab,lf(FSNB,int(h*.016)),col)
        d.line((cx,cy,int(x),int(y)),fill=(*col,int(60*q)),width=2)
    seal(im,"THE SELF IS REPEATEDLY REBUILT THROUGH MINE, FOR ME, AGAINST ME","the world becomes a field of objects capable of securing or threatening the owner")

def v_loosening(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    # Expanding spiral unwinding
    spirals=5-2*pr; pts=[]
    for i in range(200):
        u2=i/199; a=u2*spirals*2*math.pi; r=10+u2*120+40*pr
        if u2<=pr: pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.65))
    if len(pts)>1: gl(im,pts,mix(GOLD,TEAL,.4),4,13,180)
    if pr>.3:
        p2=clamp((pr-.3)*1.5)
        gl(im,[(cx,cy-140),(cx,cy-30)],GL,5,int(120*p2),12)
        gc(im,cx,cy,25,GL,int(100*p2),16)
    seal(im,"PRACTICE WORKS AT THE LOOP","change the environment — the self receives new evidence. Change action — the world reveals new possibilities")

def v_ground(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for side in (-1,1):
        x_center=cx+side*120
        for i in range(4): r=15+i*40*pr; al=int(100*(1-i/4)*pr)
        if al<5: continue; d.ellipse((x_center-r,cy-60-r*.5,x_center+r,cy-60+r*.5),outline=(*mix(VIOLET,SILVER,i/4),al),width=1)
    gc(im,cx,cy-60,30,GL,int(100*pr),16)
    d.ellipse((cx-10,cy-70,cx+10,cy-50),fill=(*WHITE,int(200*pr)))
    ct(d,(cx,cy-90),"ONE FIELD — TWO MOVEMENTS",lf(FSB,int(h*.024)),GOLD)
    seal(im,"KASHMIR ŚAIVISM AGREES THE EGO IS CONSTRUCTED","the collapse of false limitation reveals consciousness's universal reflexivity and freedom")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    # Reeds transcended into light
    for side,color in ((-1,ROSE),(1,TEAL)):
        x0=cx+side*120; y0=cy+80*pr; x1=cx; y1=cy-60
        for ri in range(10):
            off=(ri-4.5)*10; q=clamp(pr*1.5-ri*.05)
            if q<=0: continue
            pts=[]
            for j in range(15):
                u2=j/14; x=lerp(x0+off,x1+off*.3,u2); y=lerp(y0,y1,u2)
                pts.append((x,y))
            if len(pp(pts,q))>1: gl(im,pp(pts,q),mix(color,GL,.5),3,10,180)
    gc(im,cx,cy-30,35,GL,int(140*pr),20)
    d.ellipse((cx-14,cy-44,cx+14,cy-16),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-30+math.sin(a)*125*pr; d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(GOLD,WHITE,i/15),int(120*pr)))
    seal(im,"SELF AND WORLD HOLD EACH OTHER UPRIGHT","the error is not that the structures function — it is believing either possesses independent solidity")

VISUALS={}
# Build visual dict
for name,fn in [("reeds",v_reeds),("braid",v_braid),("not_construction",v_not_construction),("affordance",v_affordance),
                ("enaction_cycle",v_enaction_cycle),("hidden_side",v_hidden_side),("ai_boundary",v_ai_boundary),
                ("mirrors",v_mirrors),("grasping",v_grasping),("self_evidencing",v_self_evidencing),
                ("loosening",v_loosening),("ground",v_ground),("closing",v_closing)]:
    VISUALS[name]=fn


def v01(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-70,cy-50,cx+70,cy+50),outline=(*GOLD,int(160*q)),width=3)
    gc(im,cx,cy,20,GL,int(100*q),16)
    ct(d,(cx,cy),"Inward",lf(FSB,24),INK)
    seal(im,"Inward","Nature builds bodies by looking inward — form emerges from internal constraints.",GOLD)

def v02(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-70,cy-50,cx+70,cy+50),outline=(*GOLD,int(160*q)),width=3)
    gc(im,cx,cy,20,GL,int(100*q),16)
    ct(d,(cx,cy),"Folding",lf(FSB,24),INK)
    seal(im,"Folding","Folding generates structure — a sheet becomes a tube, a tube becomes an organ.",GOLD)

def v03(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-70,cy-50,cx+70,cy+50),outline=(*GOLD,int(160*q)),width=3)
    gc(im,cx,cy,20,GL,int(100*q),16)
    ct(d,(cx,cy),"Latent Shape",lf(FSB,24),INK)
    seal(im,"Latent Shape","Shape is not imposed from outside — it is the resolution of internal forces.",GOLD)

def v04(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-70,cy-50,cx+70,cy+50),outline=(*GOLD,int(160*q)),width=3)
    gc(im,cx,cy,20,GL,int(100*q),16)
    ct(d,(cx,cy),"Closing",lf(FSB,24),INK)
    seal(im,"Closing","Nature builds bodies by looking inward — the form was always latent in the material.",GOLD)

SCENES=[
    Scene("Inward","Nature builds bodies by looking inward — form emerges from internal constraints.",7.0,"v01",{}),
    Scene("Folding","Folding generates structure — a sheet becomes a tube, a tube becomes an organ.",7.0,"v02",{}),
    Scene("Latent Shape","Shape is not imposed from outside — it is the resolution of internal forces.",7.5,"v03",{}),
    Scene("Closing","Nature builds bodies by looking inward — the form was always latent in the material.",8.0,"v04",{}),
]
VISUALS={"v01":v01,"v02":v02,"v03":v03,"v04":v04,}

def rf(s,fi,fc,w,h,se): u=fi/max(1,fc-1); t=u*s.duration; im=bg(w,h,se); VISUALS[s.visual](im,u,t,s.params); return im.convert("RGB")
def ff():
    if not (x:=shutil.which("ffmpeg")): raise RuntimeError("ffmpeg required"); return x
def enc(i,fps):
    subprocess.run([ff(),"-y","-framerate",str(fps),"-i",str(FRAMES/f"scene_{i:03d}"/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(SCENES_DIR/f"scene_{i:03d}.mp4")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return SCENES_DIR/f"scene_{i:03d}.mp4"
def rs(i,s,fps,w,h,pv):
    fd=FRAMES/f"scene_{i:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    nf=max(2,round(s.duration*fps))
    if pv:
        for oi,fi in enumerate([0,int(nf*.33),int(nf*.72),nf-1]): rf(s,fi,nf,w,h,i*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95); return fd
    for fi in range(nf):
        if not (p:=fd/f"{fi:05d}.jpg").exists(): rf(s,fi,nf,w,h,i*10000+fi).save(p,quality=95,subsampling=0)
    return enc(i,fps)
def concat(paths):
    (c:=O/"concat.txt").write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    o=O/f"{slug}.mp4"; subprocess.run([ff(),"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def tl():
    cur=0.0; pl=[]
    for i,s in enumerate(SCENES,1): r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cur,3); cur+=s.duration; r["end_seconds"]=round(cur,3); pl.append(r)
    (p:=O/"narration_timeline.json").write_text(json.dumps({"title":f"{slug}","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
def cs(w,h):
    th=[]; tw,th2=320,int(320*h/w)
    for i,s in enumerate(SCENES,1): nf=max(2,round(s.duration*FPS)); im=rf(s,int(nf*.72),nf,w,h,i*10000+72); im.thumbnail((tw,th2)); th.append((i,s.title,im.copy()))
    sht=Image.new("RGB",(4*tw,math.ceil(len(th)/4)*(th2+48)),IVORY); d=ImageDraw.Draw(sht)
    for i,t,im in th: s=i-1; x=(s%4)*tw; y=(s//4)*(th2+48); sht.paste(im,(x,y)); d.text((x+8,y+th2+7),f"{i:02d}  {t}",lf(FSNB,14),INK)
    (p:=O/"contact_sheet.jpg").save(sht,quality=94); return p
def pa():
    p=argparse.ArgumentParser(); p.add_argument("--fps",type=int,default=FPS); p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true")
    return p.parse_args()
def main():
    a=pa()
    for d in (O,FRAMES,SCENES_DIR): d.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {tl()} | Scenes: {len(SCENES)} | {sum(s.duration for s in SCENES)/60:.2f}m")
    if a.scene: print(rs(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rd=[]
    for i,s in enumerate(SCENES,1): print(f"[{i:02d}] {s.title}"); r=rs(i,s,a.fps,a.width,a.height,a.preview)
    if not a.preview: rd.append(r)
    print(f"Final: {concat(rd)}")
if __name__=="__main__":
    main()
