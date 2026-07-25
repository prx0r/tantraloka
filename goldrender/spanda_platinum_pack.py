#!/usr/bin/env python3
"""SPANDA — THE HIDDEN PULSE — Platinum Edition
Essay 1: the engine of consciousness

DESIGN CONTRACT
• 5-10 second shots, white scientific field
• Gold = spanda / the pulse itself
• Cyan = the wheel / structure
• Crimson = heartbeat / fish-belly throb
• Violet = the six names
• Green = recognition / krīḍā
• Continuity: the gold pulse-ring
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_spanda_platinum"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94); GD=(191,154,73); PG=(232,216,174)
CY=(67,157,180); PC=(196,226,231); GN=(72,135,101); CR=(158,57,66); VR=(140,125,180); SL=(180,186,192); SV=(210,185,195)
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

def v_hidden_pulse(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Heartbeat (crimson) vs spanda (gold) — two rhythms contrasted
    pts_heart=[]
    for i in range(120):
        q=i/119
        x=le(w*.12,w*.45,q)
        y=cy-15*math.sin(q*math.tau*2)*math.exp(-5*((q-.5)**2))
        pts_heart.append((x,y))
    gl(im,pp(pts_heart,pr),CR,3,10,200)
    # Spanda — slow gold pulse ring
    r=le(20,120,pr)
    gc(im,w*.72,cy,int(r),GD,int(150*pr),16)
    d.text((w*.72,cy+r+20),"spanda",font=lf(F2B,int(h*.018)),fill=GD,anchor="mm")
    d.text((w*.28,cy-r-15),"heartbeat",font=lf(F2B,int(h*.015)),fill=CR,anchor="mm")
    se(im,"THERE IS A PULSE NOT YOUR HEARTBEAT","the hidden pulse — most never notice it",GD)

def v_wheel_powers(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Hub
    gc(im,cx,cy,20,GD,200,12)
    # Spokes appear
    for i in range(12):
        a=i*2*math.pi/12; q=cl(pr*1.5-i*.05)
        if q<=0: continue
        r=le(20,140,q)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.55
        col=CY if i%4==0 else VR if i%4==1 else SV if i%4==2 else GD
        d.line(((cx,cy),(int(x),int(y))),fill=(*col,int(180*q)),width=2)
        d.ellipse((int(x)-4,int(y)-4,int(x)+4,int(y)+4),fill=(*col,int(200*q)))
    d.text((cx,cy+65),"hub = awareness",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
    d.text((cx,cy+85),"spokes = will, cognition, action",font=lf(F2,int(h*.014)),fill=ST,anchor="mm")
    se(im,"THE WHEEL OF POWERS","expansion is arising — contraction is dissolution",GD)

def v_six_names(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    names=[("prāṇanā","vitality"),("spanda","vibration"),("sphurattā","effulgence"),
           ("viśrānti","repose"),("jīva","living being"),("hṛdaya","heart")]
    cols=[GD,CY,VR,GN,SV,CR]
    rads=[25,48,72,98,125,155]
    for i in range(6):
        q=cl(pr*1.5-i*.07)
        if q<=0: continue
        r=rads[i]
        d.ellipse((cx-r,cy-r*.55,cx+r,cy+r*.55),outline=(*cols[i],int(180*q)),width=2)
        d.text((cx+r+18,cy-6),names[i][0],font=lf(F2B,int(h*.013)),fill=cols[i],anchor="lm")
    gc(im,cx,cy,12,GD,180,10)
    se(im,"SIX NAMES FOR ONE PULSE","Abhinavagupta's anatomy of the hidden thrum",GD)

def v_breath_mantra(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Breath wave carrying mantra
    pts=[]
    for i in range(160):
        q=i/159; x=le(w*.10,w*.90,q)
        y=cy+math.sin(q*math.tau*3+pr*4)*35*(1-.3*abs(q-.5))
        pts.append((x,y))
    gl(im,pp(pts,pr),GD,4,13,220)
    # Seed syllables at wave crests
    for i,ch in enumerate(["हं","सौः","ॐ"]):
        q2=(i+1)/4; idx=int(q2*159)
        if len(pts)>idx:
            d.text((pts[idx][0], pts[idx][1]-30),ch,font=lf(F1B,int(h*.020)),fill=GD,anchor="mm")
    se(im,"MANTRA IS THE PULSE SHAPED INTO SOUND","say a word — feel the breath move",GD)

def v_unmesha_nimesha(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    senses=["hearing","touch","sight","taste","smell"]
    cols=[VR,CY,GD,CR,SV]
    for i in range(5):
        a=-math.pi/2+i*2*math.pi/5; r=140
        x=w*.50+math.cos(a)*r; y=h*.38+math.sin(a)*r*.5
        of=0.3+0.7*(0.5+0.5*math.sin(t*2.5+i*1.3))*pr
        gc(im,int(x),int(y),int(18*of),cols[i],int(140*of),10)
        if pr>.5:
            d.text((int(x),int(y+r*.35)),senses[i],font=lf(F2B,int(h*.013)),fill=cols[i],anchor="mm")
    gc(im,w*.50,h*.38,15,GD,180,10)
    se(im,"UNMEṢA-NIMEṢA","every perception — opening and closing",GD)

def v_resonance(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Two tuning forks
    fork(im,w*.25,h*.42,pr,t,GD,"spanda")
    fork(im,w*.75,h*.42,pr*ss(.3,.9,pr),t,VR,"mantra")
    # Resonance wave
    if pr>.3:
        wv_pts=[]
        for i in range(60):
            q=i/59; x=le(w*.30,w*.70,q)
            y=h*.42+math.sin(q*math.tau*3+pr*6)*10*pr
            wv_pts.append((x,y))
        gl(im,wv_pts,GD,2,8,180)
    se(im,"TUNING FORK RESONANCE","mantra meets spanda the same way",GD)

def fork(im,x,y,pr,t,col,lab):
    d=ImageDraw.Draw(im)
    vib=0.5+0.5*math.sin(t*4*math.pi)*pr
    th=40+25*vib
    d.line((x-6,y-15,x-6,y-15-th),fill=(*col,200),width=3)
    d.line((x+6,y-15,x+6,y-15-th),fill=(*col,200),width=3)
    d.ellipse((x-14,y-5,x+14,y+12),fill=(*mi(col,WH,.3),150),outline=(*col,180),width=2)
    d.text((x,y-25-th),lab,font=lf(F2B,int(12)),fill=col,anchor="mm")

def v_fish_belly(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    br=0.5+0.5*math.sin(t*math.pi*2)
    for i in range(5):
        r=le(20,20+i*34,pr)*(.82+.18*br)
        col=mi(CR,GD,i/5)
        d.ellipse((cx-r,cy-r*.55,cx+r,cy+r*.55),outline=(*col,int(180*pr)),width=2)
    gc(im,cx,cy,18,GD,200,12)
    se(im,"THE FISH-BELLY THROB","the whole body one single pulse",CR)


def v_cascading(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    layers=["kāla","prāṇa","spanda","śūnya","citi"]
    cols=[ST,CY,GD,SL,WH]
    widths=[260,210,160,110,60]
    for i in range(5):
        q=cl(pr*1.5-i*.08)
        if q<=0: continue
        ww=widths[i]
        d.arc((w*.50-ww,h*.38-ww*.45,w*.50+ww,h*.38+ww*.45),200,340,fill=(*cols[i],int(170*q)),width=2)
        d.text((w*.50+ww+15,h*.38-6),layers[i],font=lf(F2B,int(h*.015)),fill=cols[i],anchor="lm")
    se(im,"TIME → BREATH → PULSE → VOID → CONSCIOUSNESS","the pulse: middle link between breath and stillness",GD)

def v_krida(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    n=20
    for i in range(n):
        a=pr*.3+i*2*math.pi/n
        r=le(15,160,pr*(.5+.5*math.sin(t+i*.3)))
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.55
        col=mi(GD,VR,i/7) if i%2==0 else mi(CY,GD,i/7)
        d.line(((cx,cy),(int(x),int(y))),fill=(*col,int(70*pr)),width=1)
        d.ellipse((int(x)-3,int(y)-3,int(x)+3,int(y)+3),fill=(*col,int(170*pr)))
    gc(im,cx,cy,22,GD,200,12)
    d.text((cx,cy+55),"krīḍā",font=lf(F1B,int(h*.022)),fill=GD,anchor="mm")
    d.text((cx,cy+75),"the engine is a dancer",font=lf(F2,int(h*.016)),fill=ST,anchor="mm")
    se(im,"PLAY — VIBRATION SEEKING JOY","a king who pretends to be a foot soldier",GD)

def v_seal(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(36):
        a=i*2*math.pi/36+pr*.2; r=le(10,200,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.55
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,CY,i/36),int(80*pr)),width=1)
    d.ellipse((cx-80*pr,cy-50*pr,cx+80*pr,cy+50*pr),outline=(*GD,int(150*pr)),width=3)
    d.ellipse((cx-40*pr,cy-25*pr,cx+40*pr,cy+25*pr),outline=(*GD,int(150*pr)),width=2)
    gc(im,cx,cy,22,GD,200,12)
    d.text((cx,cy),"pūrṇavikāsa",font=lf(F1B,int(h*.016)),fill=GD,anchor="mm")
    se(im,"WHEN YOU KNOW YOURSELF AS THE PULSE","desire becomes creative power",GD)

VS={"hidden":v_hidden_pulse,"wheel":v_wheel_powers,"names":v_six_names,"breath":v_breath_mantra,
    "unmesha":v_unmesha_nimesha,"resonance":v_resonance,"belly":v_fish_belly,"cascade":v_cascading,
    "krida":v_krida,"seal":v_seal}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("The hidden pulse",6.0,"hidden"),Sc("Not your heartbeat — not your breath",5.5,"hidden"),
    Sc("The wheel of powers",7.0,"wheel"),Sc("Hub = awareness, spokes = will, cognition, action",6.5,"wheel"),
    Sc("Six names",7.0,"names"),Sc("Pranana, spanda, sphuratta, visranti, jiva, hrdaya",6.5,"names"),
    Sc("Mantra as shaped pulse",7.0,"breath"),Sc("Say a word — feel the breath move",6.5,"breath"),
    Sc("Unmesha-nimesha",7.0,"unmesha"),Sc("Every perception is an opening and closing",6.5,"unmesha"),
    Sc("Tuning fork",7.0,"resonance"),Sc("Mantra meets spanda by resonance",6.5,"resonance"),
    Sc("The fish-belly throb",7.0,"belly"),Sc("The whole body one single pulse",6.5,"belly"),
    Sc("Cascading layers",7.0,"cascade"),Sc("Time → breath → pulse → void → consciousness",6.5,"cascade"),
    Sc("Krida — divine play",7.0,"krida"),Sc("The engine is a dancer",6.5,"krida"),
    Sc("Desire becomes power",7.0,"seal"),Sc("When you know the pulse — complete expansion",6.5,"seal"),
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
    op=O/"spanda_platinum.mp4"
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
