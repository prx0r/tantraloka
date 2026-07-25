#!/usr/bin/env python3
"""THE WHOLE CAN ACT BEFORE ANY PART UNDERSTANDS IT — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,random,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_whole_acts"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT=(86,91,98)
GOLD=(194,156,72); GL=(236,219,175); CYAN=(57,156,180); CRIMSON=(162,58,69); VIOLET=(109,83,153); GREEN=(70,139,99)
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
    for i in range(14): d=ImageDraw.Draw(rl(im.size)); d.rounded_rectangle((20+i*3,20+i*3,w-20-i*3,h-20-i*3),radius=18,outline=(*INK,int(i*.7)),width=2)
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
    if not pts: return []; a=clamp(a); k=a*(len(pts)-1); i=int(k); f=k-i; o=list(pts[:i+1])
    if i+1<len(pts): p,q=pts[i],pts[i+1]; o.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return o

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def vgradient(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    gl(im,[(cx,cy-80),(cx,cy+80)],CYAN,5,180,12)
    for i in range(7): y=cy-70+i*24; x=cx+math.sin(i*1.3)*60*q; d.ellipse((x-6,y-6,x+6,y+6),fill=(*mix(GOLD,CYAN,i/6),int(160*q)))
    ct(d,(cx,cy-95),"GLOBAL GRADIENT",lf(FSNB,16),GOLD)
    seal(im,"THE WHOLE CAN ACT BEFORE ANY PART UNDERSTANDS IT","tissue-level constraints alter local behaviour — the whole reorganises the parts")
def vriver(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for i in range(3):
        q2=clamp(q*2-i*.1)
        if q2<=0: continue
        pts=[(200+i*20,cy-60+i*10),(640,cy-20),(1080-i*20,cy-30+i*15)]; gl(im,pp(pts,q2),mix(CYAN,GOLD,i/2),3,150,9)
    ct(d,(cx,cy-70),"RIVERBANKS CONSTRAIN FLOW",lf(FSNB,16),SOFT)
    seal(im,"RIVERBANKS CONSTRAIN THE WATER — THE RIVER IS NOT INSTRUCTING EVERY DROPLET","global form emerges from boundary conditions, not micromanagement")
def vembryo(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-70,cy-60,cx+70,cy+60),outline=(*INK,int(160*q)),width=3)
    for i in range(8):
        a=i*2*math.pi/8; r=lerp(5,55,q); x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6; d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(GOLD,CYAN,i/7),int(150*q)))
    ct(d,(cx,cy+75),"EMBRYO",lf(FSNB,16),INK)
    seal(im,"ONE EMBRYO EMERGES FROM DISTRIBUTED DECISIONS","no single cell commands the body — the shape is the result of constraints acting together")
def vclosing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for i,(r,c) in enumerate([(200,GOLD),(150,CYAN),(100,VIOLET),(50,GREEN)]): rr=r*q; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GOLD,int(140*q),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*q)),outline=(*GOLD,int(200*q)),width=2)
    for i in range(16): a=i*2*math.pi/16; x=cx+math.cos(a)*185*q; y=cy-60+math.sin(a)*125*q; d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(GOLD,CYAN,i/15),int(120*q)))
    seal(im,"THE WHOLE CAN ACT BEFORE ANY PART UNDERSTANDS IT","downward causation — the whole constrains the parts without commanding every detail")

VISUALS={"gradient":vgradient,"river":vriver,"embryo":vembryo,"closing":vclosing}
SCENES=[
    Scene("Gradient","The whole can act before any part understands it — tissue-level constraints alter local behaviour.",7.0,"gradient",{}),
    Scene("Downward Causation","Downward causation: the whole constrains the parts without commanding every detail.",7.0,"gradient",{}),
    Scene("River","Riverbanks constrain the water — the river is not instructing every droplet.",7.0,"river",{}),
    Scene("Embryo","One embryo emerges from distributed decisions — no single cell commands the body.",7.0,"embryo",{}),
    Scene("Closing","The whole can act before any part understands it — global form from boundary conditions.",7.5,"closing",{}),
    Scene("Final","Not micromanagement — constraint. The whole does not need the parts to understand it.",8.0,"closing",{}),
]

def rf(s,fi,fc,w,h,se):
    u=fi/max(1,fc-1); t=u*s.duration; im=bg(w,h,se); VISUALS[s.visual](im,u,t,s.params); return im.convert("RGB")
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
    o=O/"whole_acts_before_parts.mp4"
    subprocess.run([ff(),"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def tl():
    cur=0.0; pl=[]
    for i,s in enumerate(SCENES,1): r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cur,3); cur+=s.duration; r["end_seconds"]=round(cur,3); pl.append(r)
    (p:=O/"narration_timeline.json").write_text(json.dumps({"title":"the whole can act before any part understands it","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
    print(f"Timeline: {tl()} | Scenes: {len(SCENES)} | Runtime: {sum(s.duration for s in SCENES)/60:.2f}m")
    if a.scene: print(rs(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rd=[]
    for i,s in enumerate(SCENES,1): print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)"); r=rs(i,s,a.fps,a.width,a.height,a.preview)
    if not a.preview: rd.append(r)
    print(f"Contact: {cs(a.width,a.height)}")
    if not a.preview: print(f"Final: {concat(rd)}")
if __name__=="__main__":
    main()
