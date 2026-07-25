#!/usr/bin/env python3
"""YOU ARE ALREADY AN ANGEL — Perfect Nature / Suhrawardi / Corbin
White field, semantic: Gold=Perfect Nature, Violet=imaginal, Cyan=the encounter
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_angel"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94); GD=(191,154,73); CY=(67,157,180)
GN=(72,135,101); SL=(180,186,192); VR=(140,125,180); PV=(218,208,235)
F1="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; F1B="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F2="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; F2B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def cl(x,l=0.0,h=1.0): return max(l,min(h,x))
def le(a,b,t): return a+(b-a)*cl(t)
def mi(a,b,t): t=cl(t); return tuple(int(le(x,y,t)) for x,y in zip(a,b))
def es(t): t=cl(t); return 0.5-0.5*math.cos(math.pi*t)
def lf(p,s):
    for c in (p,F1,F2):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rg(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,sd):
    r=np.random.default_rng(sd); a=np.empty((h,w,3),dtype=np.float32); a[:]=WH
    a+=r.normal(0,0.8,(h,w,1))
    return Image.fromarray(np.clip(a,0,255).astype(np.uint8),"RGB").convert("RGBA")
def se(im,t,s="",c=IK):
    d=ImageDraw.Draw(im); tw,th=im.size
    d.text((tw/2,th*0.875),t,font=lf(F1B,max(22,int(th*0.042))),fill=c,anchor="mm")
    if s: d.text((tw/2,th*0.925),s,font=lf(F2,max(13,int(th*0.020))),fill=ST,anchor="mm")
def bo(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*IK,50),width=2)
def gc(im,cx,cy,r,col,al=180,bl=18):
    lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*col,al))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(bl)))
    c2=rg(im.size)
    ImageDraw.Draw(c2).ellipse((cx-r*.45,cy-r*.45,cx+r*.45,cy+r*.45),fill=(*mi(col,WH,.3),min(255,al+40)))
    im.alpha_composite(c2)
def gl(im,pts,col,wd=4,glw=14,al=225):
    if len(pts)<2: return
    lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.line(pts,fill=(*col,al),width=wd,joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glw))); im.alpha_composite(lay)

def v_hermes(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Hermes in vault
    d.ellipse((cx-25,cy+15,cx+25,cy+65),outline=(*ST,150),width=3)
    # Perfect Nature appears
    if pr>.3:
        p2=cl((pr-.3)/.7)
        gc(im,cx+100*p2,cy-20,30,GD,int(190*p2),18)
        d.text((cx+100*p2,cy-70),"Perfect Nature",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
    d.text((cx,cy+85),"Hermes in the vault",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE ANGEL DOES NOT ARRIVE","it is recognized",GD)

def v_parent_child(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Two figures facing
    gc(im,cx-80,cy+10,25,GD,180,12)
    gc(im,cx+80,cy+10,25,VR,180,12)
    # Thread between them
    if pr>.3:
        p2=cl((pr-.3)/.7)
        gl(im,[(cx-55,cy+10),(cx+55,cy+10)],GD,3,10,200)
    d.text((cx-80,cy+50),"parent",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
    d.text((cx+80,cy+50),"child",font=lf(F2B,int(h*.016)),fill=VR,anchor="mm")
    se(im,"THOU GAVEST BIRTH TO ME","I give birth to thee — the same event",GD)

def v_unusambo(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.rounded_rectangle((cx-100,cy-60,cx+100,cy+60),radius=18,outline=(*GD,int(180*pr)),width=4)
    d.text((cx,cy-60),"1 × 1",font=lf(F1B,int(h*.050)),fill=GD,anchor="mm" if False else "mm")
    d.text((cx,cy),"= 1",font=lf(F1B,int(h*.040)),fill=VR,anchor="mm")
    if pr>.5:
        d.text((cx,cy+48),"not 1 = 1, not n + 1",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE FORMULA OF BI-UNITY","a oneness that preserves relationship",GD)

def v_encounter(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Mirror facing mirror
    cx,cy=w*.50,h*.38
    d.rounded_rectangle((cx-130,cy-60,cx-20,cy+60),radius=10,outline=(*GD,int(180*pr)),width=3)
    d.rounded_rectangle((cx+20,cy-60,cx+130,cy+60),radius=10,outline=(*VR,int(180*pr)),width=3)
    gl(im,[(cx-20,cy),(cx+20,cy)],GD,3,10,200)
    if pr>.5:
        d.text((cx-75,cy),"I",font=lf(F1B,int(h*.030)),fill=GD,anchor="mm")
        d.text((cx+75,cy),"I",font=lf(F1B,int(h*.030)),fill=VR,anchor="mm")
    se(im,"I LOOK AT IT WITH ITS OWN LOOK","the same being in two modes",GD)

def v_light(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,40,GD,200,20)
    for i in range(24):
        a=i*2*math.pi/24; r=le(10,180,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,VR,i/24),int(100*pr)),width=2)
    d.text((cx,cy+70),"a person of light",font=lf(F2B,int(h*.018)),fill=GD,anchor="mm")
    d.text((cx,cy+90),"who has never fallen into limitation",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE BEING OF LIGHT","your own nature in the imaginal world",GD)

VS={"hermes":v_hermes,"parent":v_parent_child,"unusambo":v_unusambo,"encounter":v_encounter,"light":v_light}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("Perfect Nature",
    6.0,
    "hermes")
Sc("The philosopher's Angel",
    5.5,
    "hermes")
Sc("Parent and child",
    7.0,
    "parent")
Sc("Thou gavest birth to me",
    6.5,
    "parent")
Sc("1 x 1",
    7.0,
    "unusambo")
Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo")
Sc("The encounter",
    7.0,
    "encounter")
Sc("I look at it with its own look",
    6.5,
    "encounter")
Sc("A person of light",
    6.0,
    "light")
Sc("Who has never fallen into limitation",
    5.5,
    "light")
Sc("Perfect Nature",
    6.0,
    "hermes")
Sc("The philosopher's Angel",
    5.5,
    "hermes")
Sc("Parent and child",
    7.0,
    "parent")
Sc("Thou gavest birth to me",
    6.5,
    "parent")
Sc("1 x 1",
    7.0,
    "unusambo")
Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo")
Sc("The encounter",
    7.0,
    "encounter")
Sc("I look at it with its own look",
    6.5,
    "encounter")
Sc("A person of light",
    6.0,
    "light")
Sc("Who has never fallen into limitation",
    5.5,
    "light")
Sc("Perfect Nature",
    6.0,
    "hermes")
Sc("The philosopher's Angel",
    5.5,
    "hermes")
Sc("Parent and child",
    7.0,
    "parent")
Sc("Thou gavest birth to me",
    6.5,
    "parent")
Sc("1 x 1",
    7.0,
    "unusambo")
Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo")
Sc("The encounter",
    7.0,
    "encounter")
Sc("I look at it with its own look",
    6.5,
    "encounter")
Sc("A person of light",
    6.0,
    "light")
Sc("Who has never fallen into limitation",
    5.5,
    "light")
    Sc("Perfect Nature",
    6.0,
    "hermes"),
    Sc("The philosopher's Angel",
    5.5,
    "hermes"),
    Sc("Parent and child",
    7.0,
    "parent"),
    Sc("Thou gavest birth to me",
    6.5,
    "parent"),
    Sc("1 x 1",
    7.0,
    "unusambo"),
    Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo"),
    Sc("The encounter",
    7.0,
    "encounter"),
    Sc("I look at it with its own look",
    6.5,
    "encounter"),
    Sc("A person of light",
    6.0,
    "light"),
    Sc("Who has never fallen into limitation",
    5.5,
    "light"),
    Sc("Perfect Nature",
    6.0,
    "hermes")
Sc("The philosopher's Angel",
    5.5,
    "hermes")
Sc("Parent and child",
    7.0,
    "parent")
Sc("Thou gavest birth to me",
    6.5,
    "parent")
Sc("1 x 1",
    7.0,
    "unusambo")
Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo")
Sc("The encounter",
    7.0,
    "encounter")
Sc("I look at it with its own look",
    6.5,
    "encounter")
Sc("A person of light",
    6.0,
    "light")
Sc("Who has never fallen into limitation",
    5.5,
    "light")
Sc("Perfect Nature",
    6.0,
    "hermes")
Sc("The philosopher's Angel",
    5.5,
    "hermes")
Sc("Parent and child",
    7.0,
    "parent")
Sc("Thou gavest birth to me",
    6.5,
    "parent")
Sc("1 x 1",
    7.0,
    "unusambo")
Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo")
Sc("The encounter",
    7.0,
    "encounter")
Sc("I look at it with its own look",
    6.5,
    "encounter")
Sc("A person of light",
    6.0,
    "light")
Sc("Who has never fallen into limitation",
    5.5,
    "light")
Sc("Perfect Nature",
    6.0,
    "hermes")
Sc("The philosopher's Angel",
    5.5,
    "hermes")
Sc("Parent and child",
    7.0,
    "parent")
Sc("Thou gavest birth to me",
    6.5,
    "parent")
Sc("1 x 1",
    7.0,
    "unusambo")
Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo")
Sc("The encounter",
    7.0,
    "encounter")
Sc("I look at it with its own look",
    6.5,
    "encounter")
Sc("A person of light",
    6.0,
    "light")
Sc("Who has never fallen into limitation",
    5.5,
    "light")
    Sc("Perfect Nature",
    6.0,
    "hermes"),
    Sc("The philosopher's Angel",
    5.5,
    "hermes"),
    Sc("Parent and child",
    7.0,
    "parent"),
    Sc("Thou gavest birth to me",
    6.5,
    "parent"),
    Sc("1 x 1",
    7.0,
    "unusambo"),
    Sc("Not 1=1,
    not n+1",
    6.5,
    "unusambo"),
    Sc("The encounter",
    7.0,
    "encounter"),
    Sc("I look at it with its own look",
    6.5,
    "encounter"),
    Sc("A person of light",
    6.0,
    "light"),
    Sc("Who has never fallen into limitation",
    5.5,
    "light"),
]
def rf(sc,fi,fc,w,h,sd):
    u=fi/max(1,fc-1); t=u*sc.dur
    im=bg(w,h,sd); VS[sc.vis](im,u,t,{}); bo(im)
    return im.convert("RGB")
def ff():
    e=shutil.which("ffmpeg")
    if not e: raise RuntimeError("ffmpeg required"); return e
def en(si,fps):
    e=ff(); fd=FR/f"sc_{si:03d}"; op=SD/f"sc_{si:03d}.mp4"
    subprocess.run([e,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(op)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return op
def rs(si,sc,fps,w,h,pv):
    fd=FR/f"sc_{si:03d}"; fd.mkdir(parents=True,exist_ok=True); SD.mkdir(parents=True,exist_ok=True)
    fc=max(2,round(sc.dur*fps))
    if pv:
        for oi,fi in enumerate([0,int(fc*.35),int(fc*.72),fc-1]):
            rf(sc,fi,fc,w,h,si*1000+fi).save(fd/f"pv_{oi:02d}.jpg",quality=95); return fd
    for fi in range(fc):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists(): rf(sc,fi,fc,w,h,si*1000+fi).save(p,quality=95)
    return en(si,fps)
def ct(pths):
    e=ff(); cf=O/"concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in pths),encoding="utf-8")
    op=O/"angel.mp4"
    subprocess.run([e,"-y","-f","concat","-safe","0","-i",str(cf),"-c","copy","-movflags","+faststart",str(op)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return op
def tl():
    c=0.0; pl=[]
    for i,sc in enumerate(SCENES,1):
        pl.append({"id":f"sc_{i:03d}","title":sc.title,"dur":sc.dur,"start":round(c,3),"end":round(c+sc.dur,3)}); c+=sc.dur
    (O/"timeline.json").write_text(json.dumps({"runtime":round(c,3),"scenes":pl},indent=2),encoding="utf-8")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=FP); p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true"); a=p.parse_args()
    for d in (O,FR,SD): d.mkdir(parents=True,exist_ok=True); tl()
    if a.scene: s=SCENES[a.scene-1]; print(rs(a.scene,s,a.fps,a.width,a.height,a.preview)); return
    r=[]
    for i,sc in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {sc.title} ({sc.dur:.1f}s)"); o=rs(i,sc,a.fps,a.width,a.height,a.preview)
        if not a.preview: r.append(o)
    if not a.preview: print(f"Final: {ct(r)}")
if __name__=="__main__": main()
