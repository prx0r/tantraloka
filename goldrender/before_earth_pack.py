#!/usr/bin/env python3
"""YOU EXISTED BEFORE THE EARTH — Seth / consciousness-before-matter

DESIGN CONTRACT: White field, diagrammatic, semantic colors.
Gold = consciousness / the dream, Cyan = evolution / unfolding, Green = physical emergence
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_before_earth"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10
WH=(248,247,243); IK=(30,32,36); ST=(86,89,94); GD=(191,154,73); PG=(232,216,174)
CY=(67,157,180); PC=(196,226,231); GN=(72,135,101); PGn=(196,222,206); SL=(180,186,192); CR=(158,57,66)
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

def v_dream(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38; gc(im,cx,cy,35,GD,200,18)
    for i in range(20):
        a=i*2*math.pi/20; r=le(10,180,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(GD,ST,i/20),int(100*pr)),width=2)
    d.text((cx,cy+60),"in the beginning was the dream",font=lf(F2B,int(h*.019)),fill=GD,anchor="mm")
    d.text((cx,cy+80),"and the dream became flesh",font=lf(F2,int(h*0.016)),fill=ST,anchor="mm")
    se(im,"CONSCIOUSNESS DREAMED THE WORLD","from the inside out",GD)

def v_evolution(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # Evolution as unfolding, not adaptation
    cx,cy=w*.50,h*.38; r=le(20,170,pr)
    d.ellipse((cx-r,cy-r*.5,cx+r,cy+r*.5),outline=(*CY,int(180*pr)),width=3)
    if pr>.3:
        p2=cl((pr-.3)/.7)
        for i in range(3):
            a=math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*r*1.2*p2; y=cy+math.sin(a)*r*.5*1.2*p2
            d.ellipse((x-8,y-8,x+8,y+8),fill=(*mi(GD,GN,i/3),int(180*p2)))
    se(im,"EVOLUTION = UNFOLDING","not adaptation — bodies result from consciousness",CY)

def v_gestalt(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Divine psychological gestalt
    gc(im,cx,cy,40,GD,200,20)
    for i in range(40):
        a=i*2*math.pi/40; r=le(50,190,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*mi(GD,WH,i/40),int(120*pr)))
    d.text((cx,cy+65),"a spacious present",font=lf(F2B,int(h*.018)),fill=GD,anchor="mm")
    d.text((cx,cy+85),"past, present, future held in one focus",font=lf(F2,int(h*0.015)),fill=ST,anchor="mm")
    se(im,"DIVINE PSYCHOLOGICAL GESTALT","the source from which all being emerges",GD)

def v_ee(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # CU → EE unit → matter cascade
    ys=[h*.25,h*.38,h*.51]
    labels=[("consciousness unit","CU",GD),("EE unit","field/wave/particle",CY),("physical matter","atoms, cells, bodies",GN)]
    for i,(desc,lab,col) in enumerate(labels):
        q=cl(pr*1.5-i*.1)
        if q<=0: continue
        y=ys[i]
        d.rounded_rectangle((w*.25,y-22,w*.75,y+22),radius=12,outline=(*col,int(190*q)),width=3)
        d.text((w*.50,y-6),desc,font=lf(F2B,int(h*.016)),fill=col,anchor="mm")
        d.text((w*.50,y+14),lab,font=lf(F2,int(h*.013)),fill=ST,anchor="mm")
        if i<2:
            d.line((w*.50,y+22,w*.50,ys[i+1]-22),fill=(*col,int(100*q)),width=2)
    se(im,"CONSCIOUSNESS INTENSIFIES INTO MATTER","CU → EE → physical",GD)

def v_flower(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    # Seed → flower — the whole plant already in the seed
    for i in range(8):
        a=-math.pi/2+i*2*math.pi/8
        r=le(10,120,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*mi(GD,GN,i/8),int(180*pr)))
    gc(im,cx,cy,20,GD,200,12)
    d.text((cx,cy+75),"like a flower opening",font=lf(F2B,int(h*.018)),fill=GN,anchor="mm")
    d.text((cx,cy+95),"from a seed that already contains the whole",font=lf(F2,int(h*0.015)),fill=ST,anchor="mm")
    se(im,"EVOLUTION AS UNFOLDING","the whole was present from the beginning",GN)

def v_present(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # The spacious present — all time held now
    cx,cy=w*.50,h*.38
    for i in range(3):
        q=cl(pr*2-i*.15)
        if q<=0: continue
        x=[w*.25,w*.50,w*.75][i]; y=cy
        gc(im,int(x),int(y),20,[GD,CY,GN][i],int(190*q),12)
        d.text((int(x),int(y)+35),["past","present","future"][i],font=lf(F2B,int(h*.017)),fill=[GD,CY,GN][i],anchor="mm")
    draw_line_glow = gl
    gl(im,[(w*.32,cy),(w*.68,cy)],GD,3,10,150)
    se(im,"THE SPACIOUS PRESENT","everything held in a single moment of attention",GD)

VS={"dream":v_dream,"evolution":v_evolution,"gestalt":v_gestalt,"ee":v_ee,"flower":v_flower,"present":v_present}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("In the beginning was the dream",6.0,"dream"),Sc("The dream became flesh",5.5,"dream"),
    Sc("Evolution as unfolding",7.0,"evolution"),Sc("Consciousness expands by its own nature",6.5,"evolution"),
    Sc("Divine psychological gestalt",7.0,"gestalt"),Sc("A spacious present",6.5,"gestalt"),
    Sc("CU → EE → matter",7.0,"ee"),Sc("The cascade from consciousness to atoms",6.5,"ee"),
    Sc("Like a flower from a seed",7.0,"flower"),Sc("The whole was present from the beginning",6.0,"flower"),
    Sc("The spacious present",6.0,"present"),Sc("Everything held in one focus",5.5,"present"),
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
    op=O/"before_earth.mp4"
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
