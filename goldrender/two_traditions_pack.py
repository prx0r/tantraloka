#!/usr/bin/env python3
"""TWO TRUTHS THAT ARE ACTUALLY ONE
Comparative mysticism: Kashmir Shaivism meets Rudolf Steiner

DESIGN CONTRACT
• 5-10 second shots
• White scientific field
• Gold = Kashmir Shaivism / Tantraloka
• Silver = Steiner / Anthroposophy
• Cyan = the common architecture
• Crimson = limitation / separation
• Green = recognition / union
• Terms as seals, never paragraphs
• Continuity: the mountain silhouette
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict; from pathlib import Path; from typing import Callable
import numpy as np; from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent; OUTPUT=ROOT/"output_two_traditions"; FRAMES=OUTPUT/"frames"; SD=OUTPUT/"scenes"
W,H,FP=1280,720,10
WHITE=(248,247,243); INK=(30,32,36); SOFT=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); SILVER=(180,186,192); PS=(224,227,229)
CYAN=(67,157,180); PC=(196,226,231); CRIMSON=(158,57,66); GREEN=(72,135,101)
F1="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; F1B="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F2="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; F2B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def cl(x,l=0.0,h=1.0): return max(l,min(h,x))
def le(a,b,t): return a+(b-a)*cl(t)
def mi(a,b,t): t=cl(t); return tuple(int(le(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=cl((x-a)/(b-a)); return q*q*(3-2*q)
def es(t): t=cl(t); return 0.5-0.5*math.cos(math.pi*t)
def lf(p,s):
    for c in (p,F1,F2):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rg(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,sd):
    r=np.random.default_rng(sd); a=np.empty((h,w,3),dtype=np.float32); a[:]=WHITE
    a+=r.normal(0,0.8,(h,w,1))
    return Image.fromarray(np.clip(a,0,255).astype(np.uint8),"RGB").convert("RGBA")
def se(im,t,s="",c=INK):
    d=ImageDraw.Draw(im); tw,th=im.size
    d.text((tw/2,th*0.875),t,font=lf(F1B,max(22,int(th*0.042))),fill=c,anchor="mm")
    if s: d.text((tw/2,th*0.925),s,font=lf(F2,max(13,int(th*0.020))),fill=SOFT,anchor="mm")
def bo(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*INK,50),width=2)
def gc(im,cx,cy,r,col,al=180,bl=18):
    lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*col,al))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(bl)))
    c2=rg(im.size)
    ImageDraw.Draw(c2).ellipse((cx-r*.45,cy-r*.45,cx+r*.45,cy+r*.45),fill=(*mi(col,WHITE,.3),min(255,al+40)))
    im.alpha_composite(c2)
def gl(im,pts,col,wd=4,glw=14,al=225):
    if len(pts)<2: return
    lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.line(pts,fill=(*col,al),width=wd,joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glw))); im.alpha_composite(lay)

def v_mountain(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Two paths up same mountain
    pts_mtn=[(w*.20,h*.70),(w*.35,h*.28),(w*.50,h*.15),(w*.65,h*.28),(w*.80,h*.70)]
    d.line(pts_mtn,fill=(*SOFT,200),width=3)
    d.text((w*.30,h*.73),"Kashmir Shaiva",font=lf(F2B,int(h*.019)),fill=GOLD,anchor="mm")
    d.text((w*.70,h*.73),"Steiner",font=lf(F2B,int(h*.019)),fill=SILVER,anchor="mm")
    # Ascending dots on each path
    for side, col in [(-1,GOLD),(1,SILVER)]:
        y=le(h*.15,h*.70,pr)
        x=w*.50+side*(w*.15)*pr
        gc(im,int(x),int(y),8,col,190,8)
    se(im,"TWO TRADITIONS","the same mountain, seen from opposite sides",CYAN)

def v_sevenfold(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    tantra=["physical","pranic","cognitive","ego","grace","wisdom","pure self"]
    steiner=["physical","ether","astral","ego","spirit self","life spirit","spirit man"]
    cols=[mi(SOFT,WHITE,.5),CYAN,GOLD,SILVER,mi(GOLD,WHITE,.5),mi(CYAN,GOLD,.5),GREEN]
    for i in range(7):
        q=cl(pr*2-i*.08)
        if q<=0: continue
        y=130+i*55
        d.line((w*.15,y,w*.42,y),fill=(*GOLD,int(180*q)),width=3)
        d.line((w*.58,y,w*.85,y),fill=(*SILVER,int(180*q)),width=3)
        d.text((w*.10,y),tantra[i],font=lf(F2B,int(h*.015)),fill=mi(GOLD,SOFT,q),anchor="rm")
        d.text((w*.90,y),steiner[i],font=lf(F2B,int(h*.015)),fill=mi(SILVER,SOFT,q),anchor="lm")
    se(im,"SEVENFOLD HUMAN","layer for layer — identical architecture",CYAN)

def v_descent(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Two ladders side by side
    for side, col, lab in [(-1,GOLD,"tattva descent"),(1,SILVER,"cosmic evolution")]:
        x=w*.50+side*w*.20
        d.line((x,h*.20,x,h*.70),fill=(*col,150),width=3)
        for i in range(5):
            y=le(h*.70,h*.20,i/4)
            d.ellipse((x-6,y-6,x+6,y+6),fill=(*col,int(200*pr)))
        d.text((x,h*.78),lab,font=lf(F2,int(h*.015)),fill=col,anchor="mm")
    se(im,"SAME DESCENT","unity → multiplicity, spirit → matter",CYAN)

def v_upayas(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    stages=[("anavopaya","imagination"),("saktopaya","inspiration"),("sambhavopaya","intuition")]
    cols=[mi(CYAN,SOFT,.4),mi(GOLD,WHITE,.3),GREEN]
    for i in range(3):
        q=cl(pr*1.5-i*.1)
        if q<=0: continue
        x=250+i*350; y=h*.38
        d.rounded_rectangle((x-80,y-30,x+80,y+30),radius=12,outline=(*cols[i],int(190*q)),width=3)
        d.text((x,y-8),stages[i][0],font=lf(F2B,int(h*.018)),fill=cols[i],anchor="mm")
        d.text((x,y+14),stages[i][1],font=lf(F2,int(h*.015)),fill=SOFT,anchor="mm")
        if i<2:
            d.line((x+80,y,x+270,y),fill=(*cols[i],int(100*q)),width=2)
    se(im,"THREE STAGES OF INITIATION","symbol → inspiration → union",GREEN)

def v_five_states(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    states=[("jagrat","waking"),("svapna","dreaming"),("susupti","deep sleep"),("turiya","imagination"),("turiyatita","intuition")]
    cols=[SOFT,SILVER,mi(SOFT,WHITE,.5),GOLD,GREEN]
    for i in range(5):
        q=cl(pr*2-i*.07)
        if q<=0: continue
        x=180+i*220; y=h*.40
        r=28+8*math.sin(i+t)
        d.ellipse((x-r,y-r,x+r,y+r),outline=(*cols[i],int(190*q)),width=3)
        d.text((x,y+r+15),states[i][0],font=lf(F2B,int(h*.016)),fill=cols[i],anchor="mm")
        d.text((x,y+r+32),states[i][1],font=lf(F2,int(h*.013)),fill=SOFT,anchor="mm")
    se(im,"FIVE STATES OF CONSCIOUSNESS","the fourth is the threshold",GOLD)

def v_guardian(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Figure with veils falling
    cx,cy=w*.50,h*.38
    d.ellipse((cx-15,cy-45,cx+15,cy-15),outline=(*SOFT,200),width=3)
    d.line((cx,cy-15,cx,cy+30),fill=(*SOFT,200),width=3)
    for i in range(5):
        q=cl(pr*2-i*.1)
        if q<=0: continue
        a=-0.3+i*0.15
        d.line((cx-40-i*10,cy+20+i*20-i*20*q,
                cx+40+i*10,cy+20+i*20-i*20*q),
               fill=(*CRIMSON,int(160-140*q)),width=3)
    se(im,"FIVE KANCUKAS = THE GUARDIAN","the sum of everything you have not yet transformed",CRIMSON)

def v_flash(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Flash of recognition
    cx,cy=w*.50,h*.38
    for i in range(20):
        a=i*2*math.pi/20; r=le(10,200,pr**1.5)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GOLD,CYAN,i/20),int(150*pr)),width=2)
    gc(im,cx,cy,25,mi(GOLD,WHITE,.5),200,16)
    d.text((cx,cy+60),"pratibha",font=lf(F2B,int(h*.022)),fill=GOLD,anchor="mm")
    d.text((cx,cy+80),"the daimonic flash",font=lf(F2,int(h*.017)),fill=SOFT,anchor="mm")
    se(im,"RECOGNITION","two mountains — same dawn",GREEN)

def v_unity(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Two arcs forming a circle
    cx,cy=w*.50,h*.40; r=140
    d.arc((cx-r,cy-r*0.6,cx+r,cy+r*0.6),0,180,fill=(*GOLD,int(200*pr)),width=4)
    d.arc((cx-r,cy-r*0.6,cx+r,cy+r*0.6),180,360,fill=(*SILVER,int(200*pr)),width=4)
    gc(im,cx,cy,25,mi(GOLD,WHITE,.5),200,14)
    d.text((cx,cy+80),"the mountain exists",font=lf(F2B,int(h*.022)),fill=CYAN,anchor="mm")
    d.text((cx,cy+105),"the dawn is every moment",font=lf(F2,int(h*.017)),fill=SOFT,anchor="mm")
    se(im,"ONE ARCHITECTURE","they were looking at the same mountain",CYAN)

VS={"mountain":v_mountain,"sevenfold":v_sevenfold,"descent":v_descent,"upayas":v_upayas,
    "states":v_five_states,"guardian":v_guardian,"flash":v_flash,"unity":v_unity}

@dataclass
class Sc: title:str; dur:float; vis:str; par:dict
SCENES=[
    Sc("Two traditions",
    6.0,
    "mountain",
    {})
Sc("Same mountain",
    5.5,
    "mountain",
    {})
Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {})
Sc("Layer for layer",
    7.0,
    "sevenfold",
    {})
Sc("Same descent",
    7.0,
    "descent",
    {})
Sc("Unity into multiplicity",
    6.5,
    "descent",
    {})
Sc("Three stages",
    8.0,
    "upayas",
    {})
Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {})
Sc("Five states",
    8.0,
    "states",
    {})
Sc("The fourth is the threshold",
    7.0,
    "states",
    {})
Sc("The guardian",
    8.0,
    "guardian",
    {})
Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {})
Sc("Pratibha",
    7.0,
    "flash",
    {})
Sc("The daimonic flash",
    6.5,
    "flash",
    {})
Sc("One architecture",
    7.0,
    "unity",
    {})
Sc("The mountain exists",
    7.0,
    "unity",
    {})
Sc("Two traditions",
    6.0,
    "mountain",
    {})
Sc("Same mountain",
    5.5,
    "mountain",
    {})
Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {})
Sc("Layer for layer",
    7.0,
    "sevenfold",
    {})
Sc("Same descent",
    7.0,
    "descent",
    {})
Sc("Unity into multiplicity",
    6.5,
    "descent",
    {})
Sc("Three stages",
    8.0,
    "upayas",
    {})
Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {})
Sc("Five states",
    8.0,
    "states",
    {})
Sc("The fourth is the threshold",
    7.0,
    "states",
    {})
Sc("The guardian",
    8.0,
    "guardian",
    {})
Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {})
Sc("Pratibha",
    7.0,
    "flash",
    {})
Sc("The daimonic flash",
    6.5,
    "flash",
    {})
Sc("One architecture",
    7.0,
    "unity",
    {})
Sc("The mountain exists",
    7.0,
    "unity",
    {})
Sc("Two traditions",
    6.0,
    "mountain",
    {})
Sc("Same mountain",
    5.5,
    "mountain",
    {})
Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {})
Sc("Layer for layer",
    7.0,
    "sevenfold",
    {})
Sc("Same descent",
    7.0,
    "descent",
    {})
Sc("Unity into multiplicity",
    6.5,
    "descent",
    {})
Sc("Three stages",
    8.0,
    "upayas",
    {})
Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {})
Sc("Five states",
    8.0,
    "states",
    {})
Sc("The fourth is the threshold",
    7.0,
    "states",
    {})
Sc("The guardian",
    8.0,
    "guardian",
    {})
Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {})
Sc("Pratibha",
    7.0,
    "flash",
    {})
Sc("The daimonic flash",
    6.5,
    "flash",
    {})
Sc("One architecture",
    7.0,
    "unity",
    {})
Sc("The mountain exists",
    7.0,
    "unity",
    {})
    Sc("Two traditions",
    6.0,
    "mountain",
    {}),
    Sc("Same mountain",
    5.5,
    "mountain",
    {}),
    Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {}),
    Sc("Layer for layer",
    7.0,
    "sevenfold",
    {}),
    Sc("Same descent",
    7.0,
    "descent",
    {}),
    Sc("Unity into multiplicity",
    6.5,
    "descent",
    {}),
    Sc("Three stages",
    8.0,
    "upayas",
    {}),
    Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {}),
    Sc("Five states",
    8.0,
    "states",
    {}),
    Sc("The fourth is the threshold",
    7.0,
    "states",
    {}),
    Sc("The guardian",
    8.0,
    "guardian",
    {}),
    Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {}),
    Sc("Pratibha",
    7.0,
    "flash",
    {}),
    Sc("The daimonic flash",
    6.5,
    "flash",
    {}),
    Sc("One architecture",
    7.0,
    "unity",
    {}),
    Sc("The mountain exists",
    7.0,
    "unity",
    {}),
    Sc("Two traditions",
    6.0,
    "mountain",
    {})
Sc("Same mountain",
    5.5,
    "mountain",
    {})
Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {})
Sc("Layer for layer",
    7.0,
    "sevenfold",
    {})
Sc("Same descent",
    7.0,
    "descent",
    {})
Sc("Unity into multiplicity",
    6.5,
    "descent",
    {})
Sc("Three stages",
    8.0,
    "upayas",
    {})
Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {})
Sc("Five states",
    8.0,
    "states",
    {})
Sc("The fourth is the threshold",
    7.0,
    "states",
    {})
Sc("The guardian",
    8.0,
    "guardian",
    {})
Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {})
Sc("Pratibha",
    7.0,
    "flash",
    {})
Sc("The daimonic flash",
    6.5,
    "flash",
    {})
Sc("One architecture",
    7.0,
    "unity",
    {})
Sc("The mountain exists",
    7.0,
    "unity",
    {})
Sc("Two traditions",
    6.0,
    "mountain",
    {})
Sc("Same mountain",
    5.5,
    "mountain",
    {})
Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {})
Sc("Layer for layer",
    7.0,
    "sevenfold",
    {})
Sc("Same descent",
    7.0,
    "descent",
    {})
Sc("Unity into multiplicity",
    6.5,
    "descent",
    {})
Sc("Three stages",
    8.0,
    "upayas",
    {})
Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {})
Sc("Five states",
    8.0,
    "states",
    {})
Sc("The fourth is the threshold",
    7.0,
    "states",
    {})
Sc("The guardian",
    8.0,
    "guardian",
    {})
Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {})
Sc("Pratibha",
    7.0,
    "flash",
    {})
Sc("The daimonic flash",
    6.5,
    "flash",
    {})
Sc("One architecture",
    7.0,
    "unity",
    {})
Sc("The mountain exists",
    7.0,
    "unity",
    {})
Sc("Two traditions",
    6.0,
    "mountain",
    {})
Sc("Same mountain",
    5.5,
    "mountain",
    {})
Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {})
Sc("Layer for layer",
    7.0,
    "sevenfold",
    {})
Sc("Same descent",
    7.0,
    "descent",
    {})
Sc("Unity into multiplicity",
    6.5,
    "descent",
    {})
Sc("Three stages",
    8.0,
    "upayas",
    {})
Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {})
Sc("Five states",
    8.0,
    "states",
    {})
Sc("The fourth is the threshold",
    7.0,
    "states",
    {})
Sc("The guardian",
    8.0,
    "guardian",
    {})
Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {})
Sc("Pratibha",
    7.0,
    "flash",
    {})
Sc("The daimonic flash",
    6.5,
    "flash",
    {})
Sc("One architecture",
    7.0,
    "unity",
    {})
Sc("The mountain exists",
    7.0,
    "unity",
    {})
    Sc("Two traditions",
    6.0,
    "mountain",
    {}),
    Sc("Same mountain",
    5.5,
    "mountain",
    {}),
    Sc("Sevenfold human",
    8.0,
    "sevenfold",
    {}),
    Sc("Layer for layer",
    7.0,
    "sevenfold",
    {}),
    Sc("Same descent",
    7.0,
    "descent",
    {}),
    Sc("Unity into multiplicity",
    6.5,
    "descent",
    {}),
    Sc("Three stages",
    8.0,
    "upayas",
    {}),
    Sc("Symbol → inspiration → union",
    7.0,
    "upayas",
    {}),
    Sc("Five states",
    8.0,
    "states",
    {}),
    Sc("The fourth is the threshold",
    7.0,
    "states",
    {}),
    Sc("The guardian",
    8.0,
    "guardian",
    {}),
    Sc("Face it or live behind veils",
    7.0,
    "guardian",
    {}),
    Sc("Pratibha",
    7.0,
    "flash",
    {}),
    Sc("The daimonic flash",
    6.5,
    "flash",
    {}),
    Sc("One architecture",
    7.0,
    "unity",
    {}),
    Sc("The mountain exists",
    7.0,
    "unity",
    {}),
]

def rf(sc,fi,fc,w,h,sd):
    u=fi/max(1,fc-1); t=u*sc.dur
    im=bg(w,h,sd); VS[sc.vis](im,u,t,sc.par); bo(im)
    return im.convert("RGB")
def ff():
    e=shutil.which("ffmpeg")
    if not e: raise RuntimeError("ffmpeg required"); return e
def en(si,fps):
    e=ff(); fd=FRAMES/f"sc_{si:03d}"; op=SD/f"sc_{si:03d}.mp4"
    subprocess.run([e,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),
                    "-c:v","libx264","-preset","medium","-crf","18",
                    "-pix_fmt","yuv420p","-movflags","+faststart",str(op)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return op
def rs(si,sc,fps,w,h,pv):
    fd=FRAMES/f"sc_{si:03d}"; fd.mkdir(parents=True,exist_ok=True); SD.mkdir(parents=True,exist_ok=True)
    fc=max(2,round(sc.dur*fps))
    if pv:
        for oi,fi in enumerate([0,int(fc*.35),int(fc*.72),fc-1]):
            rf(sc,fi,fc,w,h,si*1000+fi).save(fd/f"pv_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(fc):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists(): rf(sc,fi,fc,w,h,si*1000+fi).save(p,quality=95)
    return en(si,fps)
def ct(paths):
    e=ff(); cf=OUTPUT/"concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    op=OUTPUT/"two_traditions.mp4"
    subprocess.run([e,"-y","-f","concat","-safe","0","-i",str(cf),"-c","copy","-movflags","+faststart",str(op)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return op
def tl():
    c=0.0; pl=[]
    for i,sc in enumerate(SCENES,1):
        pl.append({"id":f"sc_{i:03d}","title":sc.title,"dur":sc.dur,"start":round(c,3),"end":round(c+sc.dur,3)})
        c+=sc.dur
    (OUTPUT/"timeline.json").write_text(json.dumps({"runtime":round(c,3),"scenes":pl},indent=2),encoding="utf-8")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=FP); p.add_argument("--width",type=int,default=W)
    p.add_argument("--height",type=int,default=H); p.add_argument("--scene",type=int)
    p.add_argument("--preview",action="store_true"); a=p.parse_args()
    for d in (OUTPUT,FRAMES,SD): d.mkdir(parents=True,exist_ok=True)
    tl()
    if a.scene: s=SCENES[a.scene-1]; print(rs(a.scene,s,a.fps,a.width,a.height,a.preview)); return
    r=[]
    for i,sc in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {sc.title} ({sc.dur:.1f}s)")
        o=rs(i,sc,a.fps,a.width,a.height,a.preview)
        if not a.preview: r.append(o)
    if not a.preview: print(f"Final: {ct(r)}")
if __name__=="__main__": main()
