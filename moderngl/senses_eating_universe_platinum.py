#!/usr/bin/env python3
"""YOUR SENSES ARE ALREADY EATING THE UNIVERSE — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,random,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_senses_eating"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT=(86,91,98)
GOLD=(194,156,72); GL=(236,219,175); CYAN=(57,156,180); CRIMSON=(162,58,69); VIOLET=(109,83,153); GREEN=(70,139,99); ROSE=(183,113,129)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold"); FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0; q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): return .5-.5*math.cos(math.pi*clamp(t))
def lf(p,s):
    for c in (p,FS,FSN):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rl(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,s):
    rng=np.random.default_rng(s); a=np.empty((h,w,3),dtype=np.float32); a[:]=IVORY
    a+=rng.normal(0,.9,(h,w,1)); yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2.0)
    a[...,1]+=halo*3.5; a[...,2]+=halo*5.0
    im=Image.fromarray(np.clip(a,0,255).astype(np.uint8),"RGB").convert("RGBA")
    for i in range(14): draw=ImageDraw.Draw(rl(im.size)); draw.rounded_rectangle((20+i*3,20+i*3,w-20-i*3,h-20-i*3),radius=18,outline=(*INK,int(i*.7)),width=2)
    return im
def ct(d,xy,t,f,fill=INK): d.text(xy,t,font=f,fill=fill,anchor="mm")
def seal(im,t,s="",c=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    ct(d,(w/2,h*.875),t,lf(FSB,max(22,int(h*.04))),c)
    if s: ct(d,(w/2,h*.923),s,lf(FSN,max(13,int(h*.019))),SOFT)
def gc(im,x,y,r,col,al=170,bl=14):
    l=rl(im.size); ImageDraw.Draw(l).ellipse((x-r,y-r,x+r,y+r),fill=(*col,al))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(bl)))
    f=rl(im.size); ImageDraw.Draw(f).ellipse((x-r*.35,y-r*.35,x+r*.35,y+r*.35),fill=(*mix(col,WHITE,.35),min(255,al+50)))
    im.alpha_composite(f)
def gl(im,pts,col,w=4,al=210,bl=11):
    if len(pts)<2: return
    l=rl(im.size); ImageDraw.Draw(l).line(pts,fill=(*col,al),width=w*3,joint="curve")
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(bl)))
    f=rl(im.size); ImageDraw.Draw(f).line(pts,fill=(*mix(col,WHITE,.08),min(255,al+20)),width=w,joint="curve")
    im.alpha_composite(f)
def pp(pts,a):
    if not pts: return []
    a=clamp(a); k=a*(len(pts)-1); i=int(k); f=k-i; o=list(pts[:i+1])
    if i+1<len(pts): p,q=pts[i],pts[i+1]; o.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return o
def npts(w,h,c,s):
    r=random.Random(s); return [(r.uniform(w*.08,w*.92),r.uniform(h*.16,h*.70),[CYAN,VIOLET,GOLD,SOFT,CRIMSON][i%5]) for i in range(c)]

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def vsenses(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    senses=[("EVE",CYAN,-160,-60),("EAR",VIOLET,160,-60),("TONGUE",GOLD,-160,40),("NOSE",GREEN,160,40),("MIND",ROSE,0,100)]
    for l,c,ox,oy in senses:
        x,y=cx+ox*q,cy+oy*q; d.ellipse((x-30,y-30,x+30,y+30),outline=(*c,int(190*q)),fill=(*mix(WHITE,c,.1),int(100*q)),width=3)
        ct(d,(x,y),l,lf(FSNB,16),c)
    seal(im,"EVERY PERCEPTION CONSUMES SOMETHING","the eye takes colour — the ear takes vibration — the tongue takes chemistry — consciousness is the fire")
def vsense_det(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for l,c,ox,oy in [("SAY\nMINE",CRIMSON,-120,-50),("SAY\nPLEASANT",GOLD,120,-50),("SAY\nMORE",VIOLET,0,50)]:
        x,y=cx+ox*q,cy+oy*q; d.ellipse((x-25,y-25,x+25,y+25),outline=(*c,int(170*q)),fill=(*mix(WHITE,c,.08),int(100*q)),width=2)
        ct(d,(x,y),l,lf(FSNB,14),c)
    seal(im,"THE MIND TAKES THE RESULT AND SAYS MINE, PLEASANT, DANGEROUS, MORE")
def vfire(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for i in range(3):
        r=30+i*40*q; al=int(120*(1-i/3)*q); d.ellipse((cx-r,cy-r*.6,cx+r,cy+r*.6),outline=(*mix(GOLD,CRIMSON,i/2),al),width=2)
    gc(im,cx,cy,25,CYAN,int(80*q),16)
    ct(d,(cx,cy-60),"THE SENSES ARE DEITIES — THE WORLD IS AN OFFERING",lf(FSNB,16),SOFT)
    seal(im,"CONSCIOUSNESS IS THE FIRE INTO WHICH DIFFERENCE IS THROWN")

VISUALS={"senses":vsenses,"sense_det":vsense_det,"fire":vfire}
SCENES=[
    Scene("Senses","Every perception consumes something — the eye takes colour, the ear takes vibration.",7.0,"senses",{}),
    Scene("Mine","The mind takes the result and says mine, pleasant, dangerous, more.",6.5,"sense_det",{}),
    Scene("Fire","The senses are deities — the world is an offering — consciousness is the fire.",7.0,"fire",{}),
    Scene("Closing","Your senses are already eating the universe — you have always been feeding on the real.",8.0,"fire",{}),
]

def rf(scene,fi,fc,w,h,s):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=bg(w,h,s); VISUALS[scene.visual](im,u,t,scene.params); return im.convert("RGB")
def ff():
    if not (x:=shutil.which("ffmpeg")): raise RuntimeError("ffmpeg required"); return x
def enc(i,fps):
    subprocess.run([ff(),"-y","-framerate",str(fps),"-i",str(FRAMES/f"scene_{i:03d}"/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(SCENES_DIR/f"scene_{i:03d}.mp4")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return SCENES_DIR/f"scene_{i:03d}.mp4"
def rs(i,s,fps,w,h,pv):
    fd=FRAMES/f"scene_{i:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    nf=max(2,round(s.duration*fps))
    if pv:
        for oi,fi in enumerate([0,int(nf*.33),int(nf*.72),nf-1]): rf(s,fi,nf,w,h,i*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(nf):
        if not (p:=fd/f"{fi:05d}.jpg").exists(): rf(s,fi,nf,w,h,i*10000+fi).save(p,quality=95,subsampling=0)
    return enc(i,fps)
def concat(paths):
    (c:=O/"concat.txt").write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    o=O/"senses_eating_universe.mp4"
    subprocess.run([ff(),"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for i,s in enumerate(SCENES,1): r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cur,3); cur+=s.duration; r["end_seconds"]=round(cur,3); pl.append(r)
    (p:=O/"narration_timeline.json").write_text(json.dumps({"title":"your senses are already eating the universe","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
def cs(w,h):
    th=[]; tw,th2=320,int(320*h/w)
    for i,s in enumerate(SCENES,1): nf=max(2,round(s.duration*FPS)); im=rf(s,int(nf*.72),nf,w,h,i*10000+72); im.thumbnail((tw,th2)); th.append((i,s.title,im.copy()))
    sht=Image.new("RGB",(4*tw,math.ceil(len(th)/4)*(th2+48)),IVORY); d=ImageDraw.Draw(sht)
    for i,t,im in th: s=i-1; x=(s%4)*tw; y=(s//4)*(th2+48); sht.paste(im,(x,y)); d.text((x+8,y+th2+7),f"{i:02d}  {t}",lf(FSNB,14),INK)
    (p:=O/"contact_sheet.jpg").save(sht,quality=94); return p
def pa():
    p=argparse.ArgumentParser(); p.add_argument("--fps",type=int,default=FPS); p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true")
    return p.parse_args()
def main():
    a=pa()
    for d in (O,FRAMES,SCENES_DIR): d.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_tl()} | Scenes: {len(SCENES)} | Runtime: {sum(s.duration for s in SCENES)/60:.2f}m")
    if a.scene: print(rs(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rd=[]
    for i,s in enumerate(SCENES,1): print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)"); r=rs(i,s,a.fps,a.width,a.height,a.preview)
    if not a.preview: rd.append(r)
    print(f"Contact: {cs(a.width,a.height)}")
    if not a.preview: print(f"Final: {concat(rd)}")
if __name__=="__main__":
    main()
