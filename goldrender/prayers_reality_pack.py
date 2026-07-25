#!/usr/bin/env python3
"""YOUR PRAYERS ARE CHANGING REALITY — Proclus hymns as theurgic technology
White field, semantic colors: Gold=theurgy, Cyan=hymns, Green=ascent"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_prayers"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94); GD=(191,154,73); CY=(67,157,180); GN=(72,135,101)
F1="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; F1B="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F2="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; F2B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def cl(x,l=0.0,h=1.0): return max(l,min(h,x))
def le(a,b,t): return a+(b-a)*cl(t)
def mi(a,b,t): t=cl(t); return tuple(int(le(x,y,t)) for x,y in zip(a,b))
def es(t): t=cl(t); return 0.5-0.5*math.cos(math.pi*t)
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=cl((x-a)/(b-a)); return q*q*(3-2*q)
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

def v_hymn(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,30,GD,200,14)
    for i in range(12):
        a=i*2*math.pi/12; r=le(10,160,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,WH,i/12),int(120*pr)),width=2)
    d.text((cx,cy-50),"hymns as technology",font=lf(F1B,int(h*.024)),fill=GD,anchor="mm")
    d.text((cx,cy+65),"precision instruments for the soul",font=lf(F2B,int(h*.017)),fill=ST,anchor="mm")
    se(im,"THE LAST PHILOSOPHER WROTE HYMNS","not poetry — technology",GD)

def v_spheres(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    for i in range(7):
        r=le(20,180,pr)*(1-i*.1)
        d.ellipse((w*.50-r,h*.38-r*.5,w*.50+r,h*.38+r*.5),outline=(*mi(CY,GD,i/7),int(150-15*i)),width=2)
        if pr>.5:
            d.text((w*.50+r+15,le(h*.38,h*.38-r*.5,i/7)),str(i+1),font=lf(F2B,int(h*.016)),fill=mi(CY,GD,i/7),anchor="lm")
    gc(im,w*.50,h*.38,18,GD,200,12)
    se(im,"THROUGH THE PLANETARY SPHERES","each hymn draws the soul upward",CY)

def v_instrument(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.rounded_rectangle((cx-120,cy-80,cx+120,cy+80),radius=16,outline=(*GD,int(180*pr)),width=3)
    d.rounded_rectangle((cx-100,cy-60,cx+100,cy+60),radius=10,outline=(*mi(GD,WH,.5),int(120*pr)),width=2)
    d.text((cx,cy-30),"the name",font=lf(F1B,int(h*.026)),fill=GD,anchor="mm")
    d.text((cx,cy),"the epithets",font=lf(F1B,int(h*.024)),fill=mi(GD,WH,.5),anchor="mm")
    d.text((cx,cy+30),"the petition",font=lf(F1B,int(h*.024)),fill=mi(GD,WH,.3),anchor="mm")
    se(im,"THE THREE-PART STRUCTURE","name, epithets, petition — each precise",GD)

def v_ascent(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    path=[(w*.15,h*.72),(w*.30,h*.58),(w*.45,h*.42),(w*.55,h*.28),(w*.65,h*.16),(w*.78,h*.08)]
    gl(im,pp(path,pr),GD,4,13,220)
    for i,(x,y) in enumerate(path):
        q=cl(pr*2-i*.1)
        if q<=0: continue
        gc(im,int(x),int(y),8,mi(GD,GN,i/5),int(190*q),6)
    se(im,"DRAW THE SOUL UPWARD","planetary ascent through hymnody",GN)

VS={"hymn":v_hymn,"spheres":v_spheres,"instrument":v_instrument,"ascent":v_ascent}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("Hymns as technology",6.0,"hymn"),Sc("Precision instruments for the soul",5.5,"hymn"),
    Sc("Through the spheres",7.0,"spheres"),Sc("Planetary ascent",6.5,"spheres"),
    Sc("The three-part structure",7.0,"instrument"),Sc("Name, epithets, petition",6.5,"instrument"),
    Sc("Drawing the soul upward",7.0,"ascent"),Sc("To that which cannot be named",6.0,"ascent"),
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
    op=O/"prayers.mp4"
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
