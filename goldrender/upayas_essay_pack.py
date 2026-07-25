#!/usr/bin/env python3
"""THE PATH CHOSE YOU — Essay 4: The Four Upāyas
Gold=Śāmbhava (will), Cyan=Śākta (knowledge), Crimson=Āṇava (action), White=Anupāya
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_upayas"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94); GD=(191,154,73); CY=(67,157,180)
GN=(72,135,101); CR=(158,57,66); VR=(140,125,180); SV=(180,186,192); SL=(180,186,192)
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
    if len(pts)<2: return; lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.line(pts,fill=(*col,al),width=wd,joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glw))); im.alpha_composite(lay)

def v_path_chose(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    d.text((w*.50,h*.38),"the path chose you",font=lf(F1B,int(h*.032)),fill=GD,anchor="mm")
    if pr>.4: d.text((w*.50,h*.55),"something deeper than preference",font=lf(F2B,int(h*.018)),fill=ST,anchor="mm")
    se(im,"YOUR SPIRITUAL PATH PICKED YOU","before you ever chose it",GD)

def v_three_windows(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    cols=[GD,CY,CR]; labels=["sambhava","sakta","anava"]
    for i in range(3):
        q=cl(pr*1.5-i*.1)
        if q<=0: continue
        x=250+i*380
        d.rounded_rectangle((x-70,cy-50,x+70,cy+50),radius=14,outline=(*cols[i],int(180*q)),width=3)
        d.text((x,cy-10),labels[i],font=lf(F2B,int(h*.016)),fill=cols[i],anchor="mm")
    se(im,"THREE WINDOWS INTO THE SAME ROOM","the entry hinges on the doorway awareness has carved",CY)

def v_anupaya(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.rounded_rectangle((cx-100,cy-10,cx+100,cy+10),radius=8,outline=(*GD,int(180*pr)),width=3)
    if pr>.3:
        p2=cl((pr-.3)/.7)
        d.rounded_rectangle((cx-80,cy-60,cx+80,cy+60),radius=14,outline=(*SV,int(150*p2)),width=2)
        d.text((cx,cy),"anupāya",font=lf(F1B,int(h*.024)),fill=GD,anchor="mm")
    se(im,"NO MEANS","the fundamental state — the light of Śiva consciousness",GD)

def v_sambhava(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    gc(im,cx,cy,30,GD,200,16)
    for i in range(12):
        a=i*2*math.pi/12; r=le(10,160,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,WH,i/12),int(80*pr)),width=1)
    d.text((cx,cy+55),"a flash — instantaneous — no method",font=lf(F2B,int(h*.014)),fill=GD,anchor="mm")
    se(im,"ŚĀMBHAVOPĀYA","the divine means — pure will, free of thought constructs",GD)

def v_sakta(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(8):
        q=cl(pr*1.5-i*.08)
        if q<=0: continue
        a=-math.pi/2+i*2*math.pi/8; r=140
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.ellipse((x-12,y-12,x+12,y+12),outline=(*mi(CY,GD,i/8),int(160*q)),width=2)
        d.line((x,y,cx,cy),fill=(*CY,int(80*q)),width=1)
    gc(im,cx,cy,18,CY,180,10)
    d.text((cx,cy+55),"thought purified until it becomes transparent",font=lf(F2B,int(h*.014)),fill=CY,anchor="mm")
    se(im,"ŚĀKTOPĀYA","the empowered means — knowledge through purification of thought",CY)

def v_anava(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.line((cx,cy-60,cx,cy+60),fill=(*mi(CR,GD,.4),int(180*pr)),width=4)
    d.line((cx-40,cy+20,cx+40,cy+20),fill=(*CR,120),width=2)
    d.line((cx-30,cy+40,cx+30,cy+40),fill=(*CR,120),width=2)
    gc(im,cx,cy,15,CR,180,10)
    d.text((cx,cy+75),"body — breath — mantra — visualization",font=lf(F2B,int(h*.014)),fill=CR,anchor="mm")
    se(im,"ĀṆAVOPĀYA","the individual means — action, embodiment, structured practice",CR)

def v_three_resistances(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.line((w*.30,cy,w*.70,cy),fill=(*ST,150),width=2)
    for i in range(3):
        x=280+i*350
        d.ellipse((x-15,cy-15,x+15,cy+15),outline=(*[GD,CY,CR][i],int(180*pr)),width=3)
        d.text((x,cy+30),["will","knowledge","action"][i],font=lf(F2B,int(h*.015)),fill=[GD,CY,CR][i],anchor="mm")
    se(im,"THE ONE THAT MEETS RESISTANCE","that one is yours — the resistance itself is information",GD)

def v_one_reality(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.ellipse((cx-100,cy-60,cx+100,cy+60),outline=(*GD,int(180*pr)),width=3)
    d.ellipse((cx-70,cy-40,cx+70,cy+40),outline=(*SV,int(130*pr)),width=2)
    d.ellipse((cx-40,cy-20,cx+40,cy+20),outline=(*GD,int(180*pr)),width=2)
    gc(im,cx,cy,18,GD,200,12)
    d.text((cx,cy),"(siva, sakti, nara)",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"EACH IS THE FULL REALITY","experienced from one perspective — Śiva, Śakti, or individual soul",GD)

VS={"chose":v_path_chose,"windows":v_three_windows,"anupaya":v_anupaya,"sambhava":v_sambhava,
    "sakta":v_sakta,"anava":v_anava,"resistance":v_three_resistances,"reality":v_one_reality}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("The path chose you",6.0,"chose"),Sc("Something deeper than preference",5.5,"chose"),
    Sc("Three windows",7.0,"windows"),Sc("Sambhava, Sakta, Anava",6.5,"windows"),
    Sc("Anupaya — no means",7.0,"anupaya"),Sc("The fundamental state of awareness",6.5,"anupaya"),
    Sc("Sambhavopaya — the divine means",7.0,"sambhava"),Sc("A flash — instantaneous — pure will",6.5,"sambhava"),
    Sc("Saktopaya — the empowered means",7.0,"sakta"),Sc("Knowledge through purified thought",6.5,"sakta"),
    Sc("Anavopaya — the individual means",7.0,"anava"),Sc("Body, breath, mantra, visualization",6.5,"anava"),
    Sc("The one that meets resistance",7.0,"resistance"),Sc("That one is yours",6.5,"resistance"),
    Sc("One reality — three perspectives",7.0,"reality"),Sc("Siva, Sakti, Nara — all the same whole",6.5,"reality"),
    Sc("Siva, Sakti, and the individual soul",6.5,"windows"),
    Sc("Sambhava = will, Sakta = knowledge, Anava = action",7.0,"windows"),
    Sc("Each means corresponds to a triadic state",6.5,"reality"),
    Sc("The one reality experienced from one perspective",7.0,"reality"),
    Sc("Sambhavopaya = the means pertaining to Sambhu",6.5,"sambhava"),
    Sc("Siva's own state",6.0,"sambhava"),
    Sc("Saktopaya = the means pertaining to Sakti",6.5,"sakta"),
    Sc("Anavopaya = the means pertaining to the individual soul",7.0,"anava"),
    Sc("Each is the full and complete triadic reality",7.0,"reality"),
    Sc("From one of these three perspectives",6.5,"reality"),
    Sc("Leading to the same ultimate reality — Anuttara",7.0,"reality"),
    Sc("Also understood to be Bhairava",6.5,"reality"),
    Sc("No Means — Anupaya — the fundamental state",7.0,"anupaya"),
    Sc("The light of Siva consciousness itself",6.5,"anupaya"),
    Sc("Sambhavopaya — a flash — instantaneous",6.5,"sambhava"),
    Sc("Extremely intense awakened insight developing in an instant",8.0,"sambhava"),
    Sc("Free of thought constructs",6.0,"sambhava"),
    Sc("One who does not think of anything",6.5,"sambhava"),
    Sc("Thought constructs are of no use here",6.5,"sambhava"),
    Sc("They do not arise — attainment is instantaneous",7.0,"sambhava"),
    Sc("Pure subjectivity free of the contamination of objectivity",8.0,"sambhava"),
    Sc("The means of unity — abheda",6.5,"sambhava"),
    Sc("Saktopaya — unity-in-diversity",6.5,"sakta"),
    Sc("Knowledge through purification of thought",7.0,"sakta"),
    Sc("Vikalpa-samskara — consecrating thought",7.0,"sakta"),
    Sc("Thought is not merely suppressed",6.5,"sakta"),
    Sc("It is purified until it becomes transparent",7.0,"sakta"),
    Sc("Transparent to the light of consciousness",7.0,"sakta"),
    Sc("Anavopaya — the means based on difference",6.5,"anava"),
    Sc("Embodied, structured practice",6.5,"anava"),
    Sc("Body, breath, mantra, visualization",7.0,"anava"),
    Sc("The path of outer supports",6.5,"anava"),
    Sc("The resistance itself is information",6.5,"resistance"),
    Sc("The one that meets resistance is yours",7.0,"resistance"),
    Sc("The resistance is not failure — it is the path showing itself",8.0,"resistance"),
    Sc("Your spiritual path picked you before you chose it",7.0,"chose"),
    Sc("Three paths — the one that is yours",6.5,"chose"),
    Sc("Is the one you meet with resistance",6.5,"chose"),
    Sc("The three means correspond to the triadic state",7.0,"windows"),
    Sc("Siva, Sakti, and the individual soul",6.5,"windows"),
    Sc("The means of Siva is unity — abheda",6.5,"sambhava"),
    Sc("The empowered means is unity-in-diversity",7.0,"sakta"),
    Sc("The individual means is based on difference",6.5,"anava"),
    Sc("One who does not think of anything",6.0,"sambhava"),
    Sc("Attainment is instantaneous",6.0,"sambhava"),
    Sc("Pure subjectivity — free of objectivity",7.0,"sambhava"),
    Sc("Knowledge purified until it becomes direct perception",7.5,"sakta"),
    Sc("The individual means operates through embodied practice",7.0,"anava"),
    Sc("The body becomes the instrument of transformation",7.0,"anava"),
    Sc("Each means leads to the same ultimate reality",7.0,"reality"),
    Sc("Anuttara — the unsurpassable",6.5,"reality"),
    Sc("Bhairava consciousness itself",6.5,"reality"),
    Sc("The path chose you — before you ever chose it",7.0,"chose"),
    Sc("The resistance itself is information",6.5,"resistance"),
    Sc("Not failure — the path showing itself",6.5,"resistance"),
    Sc("Three windows into the same room",6.5,"windows"),
    Sc("The room stays as it was",6.0,"windows"),
    Sc("The entry hinges on the doorway carved in you",7.0,"chose"),
    Sc("Sambhavopaya — a flash of recognition",6.5,"sambhava"),
    Sc("No steps — no ladder",6.0,"sambhava"),
    Sc("The ground appears beneath your feet as you step",7.0,"sambhava"),
    Sc("There was never any gap",6.5,"sambhava"),
    Sc("Between you and where you needed to be",6.5,"sambhava"),
    Sc("Saktopaya — thought purified into transparency",7.0,"sakta"),
    Sc("Reflecting the light of consciousness without distortion",7.5,"sakta"),
    Sc("Anavopaya — the path of outer supports",6.5,"anava"),
    Sc("Intellectual meditation, vital breath, mantra",7.0,"anava"),
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
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in pths),encoding="utf-8"); op=O/"upayas.mp4"
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
