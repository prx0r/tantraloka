#!/usr/bin/env python3
"""BHAGAVAD GĪTĀ — Platinum Edition — Essay 19: the battle you are fighting
White field, semantic: Gold=Krishna/self, Crimson=battle/action, Cyan=wisdom, Green=devotion
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_gita_platinum"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94)
GD=(191,154,73); PG=(232,216,174); CY=(67,157,180); PC=(196,226,231)
GN=(72,135,101); CR=(158,57,66); VR=(140,125,180); SV=(210,185,195); SL=(180,186,192)
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

def v_battlefield(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.line((w*.30,h*.60,w*.70,h*.60),fill=(*ST,150),width=2)
    for side, col in [(-1,CR),(1,CY)]:
        for i in range(8):
            x=cx+side*(w*.02+i*w*.03); y=h*.55+20*(i%2)
            d.ellipse((x-3,y-3,x+3,y+3),fill=(*col,int(180*pr)))
    gc(im,cx,h*.38,15,GD,200,10)
    d.text((cx,h*.55),"the two armies",font=lf(F2B,int(h*.015)),fill=ST,anchor="mm")
    se(im,"HE SEES HIS TEACHERS, HIS FAMILY","and drops his bow: I will not fight",CR)

def v_eternal_self(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.ellipse((cx-22,cy+10,cx+22,cy+55),outline=(*ST,150),width=3)
    if pr>.3:
        p2=cl((pr-.3)/.7)
        gc(im,cx,cy+32,int(15+30*p2),GD,int(160*p2),14)
        d.line((cx-22,cy+32,cx-50,cy+22),fill=(*GD,int(150*p2)),width=2)
        d.line((cx+22,cy+32,cx+50,cy+22),fill=(*GD,int(150*p2)),width=2)
    d.text((cx,cy+70),"death is changing worn-out robes",font=lf(F2B,int(h*.014)),fill=GD,anchor="mm")
    se(im,"THE SPIRIT WAS NEVER BORN","death hath not touched it at all",GD)

def v_action(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    pts=[(cx,cy+20),(cx-25,cy+50),(cx+15,cy+45),(cx+35,cy+20),(cx+25,cy-5),(cx,cy+20)]
    d.polygon(pts,outline=(*CY,int(180*pr)),width=3)
    if pr>.4:
        p2=cl((pr-.4)/.6)
        gc(im,cx,cy+20,int(5+20*p2),GD,int(120*p2),10)
    d.text((cx,cy+65),"act without attachment",font=lf(F2B,int(h*.014)),fill=CY,anchor="mm")
    se(im,"COMPLETE ENGAGEMENT — ZERO CLINGING","the act is its own reward",CY)

def v_gunas(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cols=[mi(GD,WH,.5),mi(CR,GD,.4),mi(ST,SL,.5)]
    labels=["sattva","rajas","tamas"]
    for i in range(3):
        q=cl(pr*1.5-i*.1)
        if q<=0: continue
        x=280+i*350; y=h*.38
        d.ellipse((x-20,y-20,x+20,y+20),outline=(*cols[i],int(180*q)),width=3)
        d.text((x,y),labels[i],font=lf(F2B,int(h*.016)),fill=cols[i],anchor="mm")
        if i<2:
            d.line((x+20,y,x+330,y),fill=(*ST,int(80*q)),width=1)
    se(im,"THREE GUNAS — THE ROPE OF NATURE","you escape by seeing them, not by choosing",GD)

def v_knower_field(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Field below, knower above
    d.rectangle((w*.30,cy:=h*.45,w*.70,h*.68),outline=(*ST,int(180*pr)),width=2)
    if pr>.3:
        gc(im,w*.50,h*.28,18,GD,int(160*pr),12)
        d.ellipse((w*.50-5,h*.24,w*.50+5,h*.32),fill=(*WH,int(220*pr)))
        d.line((w*.50,h*.32,w*.50,h*.45),fill=(*GD,int(150*pr)),width=2)
    se(im,"THE FIELD AND THE KNOWER","pleasure and pain are crops — the knower watches unmoved",GD)

def v_cosmic_vision(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(30):
        a=i*2*math.pi/30; r=le(5,190,pr)
        x=cx+math.cos(a+pr)*r; y=cy+math.sin(a+pr)*r*.55
        col=mi(mi(CR,GD,.3),mi(GD,WH,.5),i/30)
        d.line(((cx,cy),(int(x),int(y))),fill=(*col,int(50*pr)),width=1)
    gc(im,cx,cy,25,GD,200,14)
    d.text((cx,cy+55),"a mouth eating every star",font=lf(F2B,int(h*.015)),fill=GD,anchor="mm")
    se(im,"THE COSMIC VISION","teeth of light — the taste of ash and honey",CR)

def v_devotion(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.42
    gc(im,cx,cy,25,GD,200,14)
    for i in range(16):
        a=i*2*math.pi/16; r=le(10,150,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,GN,i/16),int(80*pr)),width=1)
    d.text((cx,cy+50),"bhakti",font=lf(F1B,int(h*.024)),fill=GN,anchor="mm")
    d.text((cx,cy+72),"the heart that has found its home rests",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE EASIEST PATH","one thing only: the willingness to love beyond yourself",GN)

def v_seal(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Battlefield unchanged
    d.line((w*.30,h*.60,w*.70,h*.60),fill=(*ST,120),width=2)
    for side,col in [(-1,CR),(1,CY)]:
        for i in range(8):
            x=cx+side*(w*.02+i*w*.03); y=h*.55+20*(i%2)
            d.ellipse((x-2,y-2,x+2,y+2),fill=(*col,120))
    # But the witness has changed
    gc(im,cx,h*.25,20,GD,200,12)
    d.ellipse((cx-8,h*.21,cx+8,h*.29),fill=(*WH,255))
    d.text((640,480),"the one who watches has never been born",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
    se(im,"THE BATTLE IS STILL THERE","but ARJUNA IS NO LONGER THE SAME",GD)

VS={"field":v_battlefield,"eternal":v_eternal_self,"action":v_action,"gunas":v_gunas,
    "knower":v_knower_field,"vision":v_cosmic_vision,"devotion":v_devotion,"seal":v_seal}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("The battlefield",6.0,"field"),Sc("He drops his bow",5.5,"field"),
    Sc("The eternal self",7.0,"eternal"),Sc("Death is changing clothes",6.5,"eternal"),
    Sc("Act without attachment",7.0,"action"),Sc("The potter's hands — wholly absorbed",6.5,"action"),
    Sc("Three gunas",7.0,"gunas"),Sc("Sattva, rajas, tamas",6.5,"gunas"),
    Sc("Field and knower",7.0,"knower"),Sc("The farmer watches the field",6.5,"knower"),
    Sc("The cosmic vision",8.0,"vision"),Sc("A mouth eating every star",7.5,"vision"),
    Sc("Devotion — bhakti",7.0,"devotion"),Sc("The heart that has found its home",6.5,"devotion"),
    Sc("You are the journey",7.0,"seal"),Sc("The battle continues — arjuna is changed",6.5,"seal"),
]
def rf(sc,fi,fc,w,h,sd):
    u=fi/max(1,fc-1); t=u*sc.dur; im=bg(w,h,sd); VS[sc.vis](im,u,t,{}); bo(im); return im.convert("RGB")
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
        for oi,fi in enumerate([0,int(fc*.35),int(fc*.72),fc-1]): rf(sc,fi,fc,w,h,si*1000+fi).save(fd/f"pv_{oi:02d}.jpg",quality=95); return fd
    for fi in range(fc): p=fd/f"{fi:05d}.jpg"
    if not p.exists(): rf(sc,fi,fc,w,h,si*1000+fi).save(p,quality=95)
    return en(si,fps)
def ct(pths):
    e=ff(); cf=O/"concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in pths),encoding="utf-8"); op=O/"gita_platinum.mp4"
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
