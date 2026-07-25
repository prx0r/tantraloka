#!/usr/bin/env python3
"""ESSAYS 37-44 COLLECTION — dream / no-self / road / voices / body / operation
White field, semantic colors: Gold=insight, Violet=dream, Cyan=self, Crimson=shadow
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_37_44"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94)
GD=(191,154,73); CY=(67,157,180); GN=(72,135,101); CR=(158,57,66); VR=(140,125,180); SL=(180,186,192)
F1="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; F1B="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F2="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; F2B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def cl(x,l=0.0,h=1.0): return max(l,min(h,x))
def le(a,b,t): return a+(b-a)*cl(t)
def mi(a,b,t): t=cl(t); return tuple(int(le(x,y,t)) for x,y in zip(a,b))
def es(t): t=cl(t); return 0.5-0.5*math.cos(math.pi*t); import random as rnd
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

# Visual modes for each essay
def v_dream_dreaming(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.ellipse((cx-40,cy-60,cx+40,cy+30),outline=(*VR,int(180*pr)),width=3)
    d.ellipse((cx-60,cy-80,cx+60,cy+40),outline=(*VR,int(100*pr)),width=2)
    if pr>.4:
        p2=cl((pr-.4)/.6)
        gc(im,cx-20,cy-120,12,GD,int(190*p2),8)
        d.text((cx-20,cy-145),"daimon",font=lf(F2B,int(h*.015)),fill=GD,anchor="mm")
    se(im,"DREAMS ARE DAIMON COMMUNICATION","learning to read them is the skill you never developed",VR)

def v_not_real(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Figure that dissolves on inspection
    pt=[(cx,cy-45),(cx-25,cy+15),(cx+25,cy+15)]
    d.polygon(pt,outline=(*ST,200),fill=(*WH,int(200*(1-pr))),width=3)
    if pr>.5:
        p2=cl((pr-.5)/.5)
        for i in range(20):
            x=float(rnd.Random(i).uniform(w*.1,w*.9))
            y=float(rnd.Random(100+i).uniform(h*.15,h*.65))
            d.ellipse((x-2,y-2,x+2,y+2),fill=(*mi(CR,ST,p2),int(80*p2)))
    se(im,"THERE IS NO SELF THAT SUFFERs","the basic assumption is where every error begins",CR)

def v_road(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Forking path
    d.line((w*.15,cy,w*.50,cy),fill=(*ST,180),width=3)
    if pr>.2:
        d.line((w*.50,cy,w*.80,cy-40),fill=(*GD,int(150*pr)),width=3)
        d.line((w*.50,cy,w*.80,cy+40),fill=(*CY,int(150*pr)),width=3)
    gc(im,w*.50,cy,10,GD,200,8)
    if pr>.5:
        d.text((w*.80,cy-55),"known",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
        d.text((w*.80,cy+55),"unknown",font=lf(F2B,int(h*.016)),fill=CY,anchor="mm")
    se(im,"THE ROAD YOU DIDN'T KNOW","you were walking it the whole time",GD)

def v_voice_inside(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.ellipse((cx-20,cy-35,cx+20,cy+30),outline=(*ST,150),width=3)
    if pr>.3:
        p2=cl((pr-.3)/.7)
        for i in range(3):
            x=cx+120*math.sin(i*2+pr*4); y=cy-50+i*40
            gc(im,int(x),int(y),10,mi(GD,VR,i/3),int(150*p2),8)
    se(im,"THE VOICES THAT SPEAK","they are not strangers — they are parts of you",VR)

def v_friend_enemy(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    render=gc
    render(im,cx-60,cy-10,22,GD,170,10)
    render(im,cx+60,cy-10,22,CR,170,10)
    gl(im,[(cx-38,cy-10),(cx+38,cy-10)],mi(GD,CR,.5),3,10,180)
    d.text((cx-60,cy+35),"friend",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
    d.text((cx+60,cy+35),"enemy",font=lf(F2B,int(h*.016)),fill=CR,anchor="mm")
    se(im,"THE FRIEND WHO IS ALSO AN ENEMY","the shadow that protects",CR)

def v_voice_no(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.ellipse((cx-18,cy-30,cx+18,cy+30),outline=(*CR,int(180*pr)),width=3)
    d.text((cx,cy-55),"NO",font=lf(F1B,int(h*.035)),fill=CR,anchor="mm")
    for i in range(8):
        a=i*2*math.pi/8; r=80+20*pr
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line((cx,cy,int(x),int(y)),fill=(*CR,int(80*pr)),width=1)
    se(im,"THE VOICE THAT ONLY SAYS NO","the guardian at the threshold",CR)

def v_body_travels(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.ellipse((cx-25,cy+10,cx+25,cy+55),outline=(*ST,150),width=3)
    if pr>.3:
        p2=cl((pr-.3)/.7)
        gc(im,cx+80*p2,cy-30,15,GD,int(180*p2),10)
        d.line((cx+15,cy-10,cx+80*p2-15,cy-30),fill=(*GD,int(150*p2)),width=2)
    se(im,"THE BODY THAT TRAVELS","between worlds — the subtle vehicle",GD)

def v_operation(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.rounded_rectangle((cx-80,cy-60,cx+80,cy+60),radius=14,outline=(*CY,int(180*pr)),width=3)
    if pr>.4:
        p2=cl((pr-.4)/.6)
        d.rounded_rectangle((cx-65,cy-45+45*(1-p2),cx+65,cy+45),radius=10,
                            fill=(*WH,int(200*p2)),outline=(*GD,int(180*p2)),width=2)
    se(im,"THE OPERATION YOU ONLY DO ONCE","the threshold that, once crossed, changes everything",CY)

VS={"dream":v_dream_dreaming,"notreal":v_not_real,"road":v_road,"voice":v_voice_inside,
    "friend":v_friend_enemy,"no":v_voice_no,"travels":v_body_travels,"operation":v_operation}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("The dream is dreaming you",6.0,"dream"),Sc("Dreams as daimon communication",5.5,"dream"),
    Sc("Not real",6.0,"notreal"),Sc("The self that suffers is the error",5.5,"notreal"),
    Sc("The road you didn't know",6.0,"road"),Sc("You were walking it the whole time",5.5,"road"),
    Sc("The voice inside",6.0,"voice"),Sc("Parts of you speaking",5.5,"voice"),
    Sc("Friend and enemy",6.0,"friend"),Sc("The shadow that protects",5.5,"friend"),
    Sc("The voice that says no",6.0,"no"),Sc("The guardian at the threshold",5.5,"no"),
    Sc("The body that travels",6.0,"travels"),Sc("Between worlds",5.5,"travels"),
    Sc("The one operation",6.0,"operation"),Sc("The threshold that changes everything",5.5,"operation"),
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
    for fi in range(fc): p=fd/f"{fi:05d}.jpg"
    if not p.exists(): rf(sc,fi,fc,w,h,si*1000+fi).save(p,quality=95)
    return en(si,fps)
def ct(pths):
    e=ff(); cf=O/"concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in pths),encoding="utf-8")
    op=O/"essays_37_44.mp4"
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
