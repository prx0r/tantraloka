#!/usr/bin/env python3
"""ESSAYS 45-51 COLLECTION — serpent / stones / being of light / bodies / gods / stars / beauty
White field, semantic colors.
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
import random as rnd
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_45_51"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94)
GD=(191,154,73); CY=(67,157,180); GN=(72,135,101); CR=(158,57,66); VR=(140,125,180); SL=(180,186,192)
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

def v_serpent(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    pts=[]
    for i in range(60):
        q=i/59; x=le(cx-100,cx+100,q); y=cy+50*math.sin(q*4+pr*6)+30*math.sin(q*1.3+pr*2)
        pts.append((x,y))
    gl(im,pts,GD,5,13,225)
    if pr>.6:
        gc(im,cx,cy-40,12,GD,200,10)
    se(im,"THE SERPENT IN YOUR SPINE","kundalini — the power that reorganizes consciousness",GD)

def v_stones(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    for i in range(15):
        x=float(rnd.Random(i).uniform(w*.1,w*.9))
        y=float(rnd.Random(100+i).uniform(h*.15,h*.65))
        alpha=int(100+155*pr*(0.3+0.7*rnd.Random(200+i).random()))
        d.ellipse((x-8,y-8,x+8,y+8),fill=(*mi(SL,VR,i/15),alpha))
    se(im,"THE STONES ARE WATCHING YOU","consciousness appears at every level of complexity",VR)

def v_being_light(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,40,GD,200,22)
    for i in range(30):
        a=i*2*math.pi/30; r=le(10,200,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,WH,i/30),int(100*pr)),width=1)
    d.text((cx,cy+65),"the being of light",font=lf(F2B,int(h*.018)),fill=GD,anchor="mm")
    d.text((cx,cy+85),"that knows your name",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE PERFECT NATURE","your eternal companion",GD)

def v_bodies(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3; r=le(20,130,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.ellipse((x-30,y-50,x+30,y+50),outline=(*mi(GD,CY,i/3),int(160*pr)),width=2)
    se(im,"THE BODIES YOU ARE ALREADY WEARING","gross, subtle, causal — one being, three densities",CY)

def v_gods_need(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.arc((cx-90,cy-70,cx+90,cy+70),0,360*pr,fill=(*GD,int(200*pr)),width=4)
    gc(im,cx,cy,20,GD,200,12)
    if pr>.6:
        d.text((cx,cy+55),"the gods need you",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
        d.text((cx,cy+75),"as much as you need them",font=lf(F2,int(h*.014)),fill=ST,anchor="mm")
    se(im,"GOD IS INCOMPLETE WITHOUT YOU","the beloved requires the lover",GD)

def v_stars(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(60):
        x=float(rnd.Random(i).uniform(50,w-50))
        y=float(rnd.Random(100+i).uniform(h*.12,h*.68))
        r=float(rnd.Random(200+i).uniform(1,3))
        alpha=int(60+195*pr*(0.2+0.8*rnd.Random(300+i).random()))
        d.ellipse((x-r,y-r,x+r,y+r),fill=(*mi(GD,SL,alpha/255),alpha))
    se(im,"THE STARS ARE IN YOUR BLOOD","the cosmos is your body",GD)

def v_beauty(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(30):
        a=i*2*math.pi/30; r=le(10,160,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        col=mi(GD,VR,i/30)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*col,int(100+100*pr)))
    gc(im,cx,cy,25,GD,200,14)
    if pr>.7:
        d.text((cx,cy+55),"the beauty that won't leave",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
        d.text((cx,cy+75),"it has been here all along",font=lf(F2,int(h*.014)),fill=ST,anchor="mm")
    se(im,"BEAUTY IS NOT AN ADDITION","it is what consciousness feels like when it recognizes itself",GD)

VS={"serpent":v_serpent,"stones":v_stones,"light":v_being_light,"bodies":v_bodies,
    "gods":v_gods_need,"stars":v_stars,"beauty":v_beauty}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("The serpent in your spine",6.0,"serpent"),Sc("Kundalini awakens",5.5,"serpent"),
    Sc("The stones are watching",6.0,"stones"),Sc("Consciousness at every level",5.5,"stones"),
    Sc("The being of light",6.0,"light"),Sc("That knows your name",5.5,"light"),
    Sc("The bodies you wear",6.0,"bodies"),Sc("Gross, subtle, causal",5.5,"bodies"),
    Sc("The gods need you",6.0,"gods"),Sc("The beloved requires the lover",5.5,"gods"),
    Sc("The stars in your blood",6.0,"stars"),Sc("The cosmos is your body",5.5,"stars"),
    Sc("The beauty that won't leave",6.0,"beauty"),Sc("It has been here all along",5.5,"beauty"),
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
    subprocess.run([e,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(op)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return op
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
    op=O/"essays_45_51.mp4"
    subprocess.run([e,"-y","-f","concat","-safe","0","-i",str(cf),"-c","copy","-movflags","+faststart",str(op)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return op
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
