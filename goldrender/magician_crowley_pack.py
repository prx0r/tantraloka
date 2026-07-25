#!/usr/bin/env python3
"""YOU ARE ALREADY A MAGICIAN — A DIAGRAMMATIC ESSAY
Crowley's Liber Resh / Liber E / Liber Astarte

DESIGN CONTRACT
• 5-10 second shots, white scientific field
• Gold = solar / the will
• Crimson = the work / effort
• Cyan = technique / structure
• Green = attainment / HGA
• Terms as seals, continuity: the solar disc
"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np; from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_magician"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10
WH=(248,247,243); IK=(30,32,36); ST=(86,89,94)
GD=(191,154,73); PG=(232,216,174); CR=(158,57,66); PC=(229,193,197)
CY=(67,157,180); GN=(72,135,101); SL=(180,186,192)
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
def pp(p,pr):
    pr=cl(pr)
    if len(p)<2: return p
    ls=[math.dist(a,b) for a,b in zip(p[:-1],p[1:])]; ttl=sum(ls); tg=ttl*pr; o=[p[0]]; wk=0.0
    for i,l in enumerate(ls):
        if wk+l<=tg: o.append(p[i+1]); wk+=l
        else:
            q=0.0 if l==0 else (tg-wk)/l
            o.append((le(p[i][0],p[i+1][0],q),le(p[i][1],p[i+1][1],q))); break
    return o

def v_solar(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,50,GD,200,20)
    for i in range(12):
        a=i*2*math.pi/12; r=le(70,200,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*GD,int(130*pr)),width=2)
    # Four stations
    for i,(lab,dx,dy) in enumerate([("dawn",0,-1),("noon",1,0),("sunset",0,1),("midnight",-1,0)]):
        q=cl(pr*2-i*.1)
        if q<=0: continue
        x=cx+dx*w*.30*q; y=cy+dy*h*.22*q
        d.text((x,y),lab,font=lf(F2B,int(h*.017)),fill=mi(GD,ST,q),anchor="mm")
    se(im,"FOUR SOLAR STATIONS","mnemonic — relational — theurgic",GD)

def v_define(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.text((cx,cy),"magic = causing change",font=lf(F1B,int(h*.030)),fill=IK,anchor="mm")
    d.text((cx,cy+35),"in conformity with will",font=lf(F1B,int(h*.030)),fill=GD,anchor="mm")
    if pr>.5:
        q=cl((pr-.5)*2)
        d.text((cx,cy+80),"you already do this every time you move your hand",
               font=lf(F2,int(h*.017)),fill=ST,anchor="mm")
    se(im,"THE DEFINITION","no demons required",CY)

def v_four_limbs(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    limbs=[("asana","posture",GD),("pranayama","breath",CY),("dharana","concentration",CR),("dhyana","meditation",GN)]
    for i,(lab,sub,col) in enumerate(limbs):
        q=cl(pr*2-i*.08)
        if q<=0: continue
        x=200+i*290; y=h*.38
        d.rounded_rectangle((x-60,y-30,x+60,y+30),radius=14,outline=(*col,int(190*q)),width=3)
        d.text((x,y-8),lab,font=lf(F2B,int(h*.018)),fill=col,anchor="mm")
        d.text((x,y+16),sub,font=lf(F2,int(h*.014)),fill=mi(col,ST,.5),anchor="mm")
        if i<3:
            d.line((x+60,y,x+230,y),fill=(*col,int(80*q)),width=2)
    se(im,"THE FOUNDATION","before magic, sit still for four hours",CR)

def v_solar_wheel(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,35,GD,190,14)
    texts=[("RA","dawn"),("AHATHOOR","noon"),("TUM","sunset"),("KHEPHA","midnight")]
    for i,(god,tm) in enumerate(texts):
        a=-math.pi/2+i*math.pi/2; x=cx+math.cos(a)*140*pr; y=cy+math.sin(a)*140*pr
        q=cl(pr*2-i*.1)
        if q<=0: continue
        d.text((x,y),god,font=lf(F2B,int(h*.020)),fill=mi(GD,ST,q),anchor="mm")
        d.text((x,y+22),tm,font=lf(F2,int(h*.014)),fill=ST,anchor="mm")
    se(im,"Tahuti at the prow — Ra-Hoor at the helm","wisdom guides, the crowned child commands",GD)

def v_breath(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # 1:4:2 ratio as a waveform
    pts=[]
    for i in range(180):
        q=i/179; x=le(w*.10,w*.90,q)
        cycle=(q*3+pr)%1.0
        amp=30 if cycle<1/7 else 70 if cycle<5/7 else 30
        y=cy+amp*math.sin(q*math.tau*2+t*2)
        pts.append((x,y))
    gl(im,pp(pts,pr),CY,4,13,210)
    d.text((w*.15,cy+50),"1",font=lf(F2B,int(h*.018)),fill=CY,anchor="mm")
    d.text((w*.50,cy+65),"4",font=lf(F2B,int(h*.020)),fill=GD,anchor="mm")
    d.text((w*.85,cy+50),"2",font=lf(F2B,int(h*.018)),fill=CY,anchor="mm")
    se(im,"1 : 4 : 2","the breath ratio — foundation of all higher work",CY)

def v_devotion(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Heart-centering devotion
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,25,GN,200,14)
    for i in range(16):
        a=i*2*math.pi/16; r=le(40,160,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        gl(im,[(cx,cy),(int(x),int(y))],mi(GN,WH,.3),2,8,80)
    d.text((cx,cy+70),"bhakti-yoga",font=lf(F2B,int(h*.018)),fill=GN,anchor="mm")
    d.text((cx,cy+90),"constant mindfulness of the Beloved",font=lf(F2,int(h*0.015)),fill=ST,anchor="mm")
    se(im,"ENFLAME YOURSELF IN PRAYING","love as a magical force",GN)

def v_great_work(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,30,GD,200,14)
    for i in range(30):
        a=i*2*math.pi/30; r=le(10,200,pr**1.3)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,CY,i/30),int(120*pr)),width=1)
    d.text((cx,cy-60),"the Great Work",font=lf(F1B,int(h*.024)),fill=GD,anchor="mm")
    d.text((cx,cy+70),"Knowledge and Conversation",font=lf(F2B,int(h*.018)),fill=GN,anchor="mm")
    d.text((cx,cy+92),"of the Holy Guardian Angel",font=lf(F2B,int(h*.017)),fill=mi(GN,WH,.5),anchor="mm")
    se(im,"THE PURPOSE","for which every human being exists",GD)

VS={"solar":v_solar,"define":v_define,"limbs":v_four_limbs,"wheel":v_solar_wheel,"breath":v_breath,"devotion":v_devotion,"work":v_great_work}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("Magic defined",
    6.0,
    "define")
Sc("Causing change in conformity with will",
    5.5,
    "define")
Sc("Four solar stations",
    7.0,
    "solar")
Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar")
Sc("Four limbs of training",
    8.0,
    "limbs")
Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs")
Sc("The solar wheel",
    7.0,
    "wheel")
Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel")
Sc("The breath ratio",
    7.0,
    "breath")
Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath")
Sc("Devotional yoga",
    7.0,
    "devotion")
Sc("Enflame yourself in praying",
    6.5,
    "devotion")
Sc("The Great Work",
    8.0,
    "work")
Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work")
Sc("Magic defined",
    6.0,
    "define")
Sc("Causing change in conformity with will",
    5.5,
    "define")
Sc("Four solar stations",
    7.0,
    "solar")
Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar")
Sc("Four limbs of training",
    8.0,
    "limbs")
Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs")
Sc("The solar wheel",
    7.0,
    "wheel")
Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel")
Sc("The breath ratio",
    7.0,
    "breath")
Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath")
Sc("Devotional yoga",
    7.0,
    "devotion")
Sc("Enflame yourself in praying",
    6.5,
    "devotion")
Sc("The Great Work",
    8.0,
    "work")
Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work")
Sc("Magic defined",
    6.0,
    "define")
Sc("Causing change in conformity with will",
    5.5,
    "define")
Sc("Four solar stations",
    7.0,
    "solar")
Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar")
Sc("Four limbs of training",
    8.0,
    "limbs")
Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs")
Sc("The solar wheel",
    7.0,
    "wheel")
Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel")
Sc("The breath ratio",
    7.0,
    "breath")
Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath")
Sc("Devotional yoga",
    7.0,
    "devotion")
Sc("Enflame yourself in praying",
    6.5,
    "devotion")
Sc("The Great Work",
    8.0,
    "work")
Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work")
    Sc("Magic defined",
    6.0,
    "define"),
    Sc("Causing change in conformity with will",
    5.5,
    "define"),
    Sc("Four solar stations",
    7.0,
    "solar"),
    Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar"),
    Sc("Four limbs of training",
    8.0,
    "limbs"),
    Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs"),
    Sc("The solar wheel",
    7.0,
    "wheel"),
    Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel"),
    Sc("The breath ratio",
    7.0,
    "breath"),
    Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath"),
    Sc("Devotional yoga",
    7.0,
    "devotion"),
    Sc("Enflame yourself in praying",
    6.5,
    "devotion"),
    Sc("The Great Work",
    8.0,
    "work"),
    Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work"),
    Sc("Magic defined",
    6.0,
    "define")
Sc("Causing change in conformity with will",
    5.5,
    "define")
Sc("Four solar stations",
    7.0,
    "solar")
Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar")
Sc("Four limbs of training",
    8.0,
    "limbs")
Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs")
Sc("The solar wheel",
    7.0,
    "wheel")
Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel")
Sc("The breath ratio",
    7.0,
    "breath")
Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath")
Sc("Devotional yoga",
    7.0,
    "devotion")
Sc("Enflame yourself in praying",
    6.5,
    "devotion")
Sc("The Great Work",
    8.0,
    "work")
Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work")
Sc("Magic defined",
    6.0,
    "define")
Sc("Causing change in conformity with will",
    5.5,
    "define")
Sc("Four solar stations",
    7.0,
    "solar")
Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar")
Sc("Four limbs of training",
    8.0,
    "limbs")
Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs")
Sc("The solar wheel",
    7.0,
    "wheel")
Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel")
Sc("The breath ratio",
    7.0,
    "breath")
Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath")
Sc("Devotional yoga",
    7.0,
    "devotion")
Sc("Enflame yourself in praying",
    6.5,
    "devotion")
Sc("The Great Work",
    8.0,
    "work")
Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work")
Sc("Magic defined",
    6.0,
    "define")
Sc("Causing change in conformity with will",
    5.5,
    "define")
Sc("Four solar stations",
    7.0,
    "solar")
Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar")
Sc("Four limbs of training",
    8.0,
    "limbs")
Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs")
Sc("The solar wheel",
    7.0,
    "wheel")
Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel")
Sc("The breath ratio",
    7.0,
    "breath")
Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath")
Sc("Devotional yoga",
    7.0,
    "devotion")
Sc("Enflame yourself in praying",
    6.5,
    "devotion")
Sc("The Great Work",
    8.0,
    "work")
Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work")
    Sc("Magic defined",
    6.0,
    "define"),
    Sc("Causing change in conformity with will",
    5.5,
    "define"),
    Sc("Four solar stations",
    7.0,
    "solar"),
    Sc("Dawn,
    noon,
    sunset,
    midnight",
    6.5,
    "solar"),
    Sc("Four limbs of training",
    8.0,
    "limbs"),
    Sc("Asana,
    pranayama,
    dharana,
    dhyana",
    7.0,
    "limbs"),
    Sc("The solar wheel",
    7.0,
    "wheel"),
    Sc("Ra,
    Ahathoor,
    Tum,
    Khephra",
    6.5,
    "wheel"),
    Sc("The breath ratio",
    7.0,
    "breath"),
    Sc("1:4:2 — in,
    hold,
    out",
    6.0,
    "breath"),
    Sc("Devotional yoga",
    7.0,
    "devotion"),
    Sc("Enflame yourself in praying",
    6.5,
    "devotion"),
    Sc("The Great Work",
    8.0,
    "work"),
    Sc("Knowledge and Conversation of the HGA",
    7.0,
    "work"),
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
    subprocess.run([e,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),
                    "-c:v","libx264","-preset","medium","-crf","18",
                    "-pix_fmt","yuv420p","-movflags","+faststart",str(op)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
    op=O/"magician.mp4"
    subprocess.run([e,"-y","-f","concat","-safe","0","-i",str(cf),"-c","copy","-movflags","+faststart",str(op)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return op
def tl():
    c=0.0; pl=[]
    for i,sc in enumerate(SCENES,1):
        pl.append({"id":f"sc_{i:03d}","title":sc.title,"dur":sc.dur,"start":round(c,3),"end":round(c+sc.dur,3)})
        c+=sc.dur
    (O/"timeline.json").write_text(json.dumps({"runtime":round(c,3),"scenes":pl},indent=2),encoding="utf-8")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=FP); p.add_argument("--width",type=int,default=W)
    p.add_argument("--height",type=int,default=H); p.add_argument("--scene",type=int)
    p.add_argument("--preview",action="store_true"); a=p.parse_args()
    for d in (O,FR,SD): d.mkdir(parents=True,exist_ok=True); tl()
    if a.scene: s=SCENES[a.scene-1]; print(rs(a.scene,s,a.fps,a.width,a.height,a.preview)); return
    r=[]
    for i,sc in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {sc.title} ({sc.dur:.1f}s)")
        o=rs(i,sc,a.fps,a.width,a.height,a.preview)
        if not a.preview: r.append(o)
    if not a.preview: print(f"Final: {ct(r)}")
if __name__=="__main__": main()
