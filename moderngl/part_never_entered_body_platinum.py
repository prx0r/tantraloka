#!/usr/bin/env python3
"""PART OF YOU NEVER ENTERED THE BODY — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,random,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_part_never_entered"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
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
    if not pts: return []
    a=clamp(a); k=a*(len(pts)-1); i=int(k); f=k-i; o=list(pts[:i+1])
    if i+1<len(pts): p,q=pts[i],pts[i+1]; o.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return o

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def vroot(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-80,cy+30,cx+80,cy+90),fill=(*mix(WHITE,CYAN,.08),150),outline=(*CYAN,180),width=3)
    for i in range(12):
        a=i*2*math.pi/12; r=30+i*10*q; x=cx+math.cos(a)*r; y=cy-20+math.sin(a)*r*.6
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*GOLD,int(140*q)))
    gl(im,[(cx,cy-10),(cx,cy+30)],GOLD,4,180,12)
    ct(d,(cx,cy-60),"ROOT ABOVE THE VISIBLE TREE",lf(FSNB,17),GOLD)
    seal(im,"PART OF YOU NEVER ENTERED THE BODY","the undescended soul — root above the tree — sunlight behind a turned figure")

def vinstr(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-50,cy-50,cx+50,cy+50),outline=(*INK,int(170*q)),width=3)
    d.ellipse((cx-25,cy-25,cx+25,cy+25),fill=(*GOLD,int(30*q)))
    ct(d,(cx,cy+65),"INSTRUMENT",lf(FSNB,17),INK)
    ct(d,(cx,cy-70),"MUSICIAN",lf(FSNB,17),GOLD)
    gl(im,[(cx,cy-55),(cx,cy-25)],GOLD,3,150,8)
    seal(im,"THE SOUL IS NOT THE INSTRUMENT — IT IS THE MUSICIAN","the body is played — the player never fully enters the instrument")

def vvertical(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    gl(im,[(cx,cy-120),(cx,cy+100)],CYAN,3,150,10)
    for i in range(5):
        y=cy-90+i*45; x=cx+math.sin(i*1.3)*50*q
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*mix(GOLD,CYAN,i/4),int(160*q)))
    ct(d,(cx-90,cy-80),"ABOVE",lf(FSNB,16),GOLD)
    ct(d,(cx-90,cy+50),"BELOW",lf(FSNB,16),CYAN)
    seal(im,"VERTICAL ORIENTATION — THE SOUL DESCENDS AND ASCENDS","the soul remains rooted in the intelligible while living in the sensible")

def vrecall(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    d.ellipse((cx-100,cy-80,cx+100,cy+80),outline=(*GOLD,int(170*q)),width=3)
    for i in range(8):
        a=i*2*math.pi/8; r=lerp(20,130,q); x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GOLD,VIOLET,i/7); d.ellipse((x-4,y-4,x+4,y+4),fill=(*col,int(130*q)))
    ct(d,(cx,cy),"— RECOLLECTION —",lf(FSB,22),GOLD)
    seal(im,"KNOWLEDGE IS RECOLLECTION — THE SOUL REMEMBERS WHAT IT ALWAYS KNEW","the path of return is the path of recognition")

def vclosing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for i,(r,c) in enumerate([(200,GOLD),(150,VIOLET),(100,CYAN),(50,CRIMSON)]):
        rr=r*q; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GOLD,int(140*q),20)
    d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*q)),outline=(*GOLD,int(200*q)),width=2)
    for i in range(16): a=i*2*math.pi/16; x=cx+math.cos(a)*185*q; y=cy-60+math.sin(a)*125*q; d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(GOLD,WHITE,i/15),int(120*q)))
    seal(im,"PART OF YOU NEVER ENTERED THE BODY","the undescended soul — always rooted in the light — the body is a visitation, not a prison")

VISUALS={"root":vroot,"instr":vinstr,"vertical":vvertical,"recall":vrecall,"closing":vclosing}
SCENES=[
    Scene("Root","Part of you never entered the body — root above the visible tree, sunlight behind a turned figure.",7.0,"root",{}),
    Scene("Undescended","Plotinus: the undescended soul remains in Intellect while also present in embodiment.",7.5,"root",{}),
    Scene("Music","The soul is not the instrument — it is the musician.",6.0,"instr",{}),
    Scene("Played","The body is played — the player never fully enters the instrument.",6.5,"instr",{}),
    Scene("Vertical","The soul descends and ascends — rooted in the intelligible while living in the sensible.",7.0,"vertical",{}),
    Scene("Recollection","Knowledge is recollection — the soul remembers what it always knew.",7.0,"recall",{}),
    Scene("Return","The path of return is the path of recognition — what was never lost can be found.",7.0,"recall",{}),
    Scene("Closing","Part of you never entered the body — always rooted in the light.",7.5,"closing",{}),
    Scene("Final","The body is a visitation, not a prison — you have never been fully contained.",8.0,"closing",{}),
]

def rf(scene,fi,fc,w,h,s):
    u=fi/max(1,fc-1); t=u*scene.duration; im=bg(w,h,s); VISUALS[scene.visual](im,u,t,scene.params); return im.convert("RGB")
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
    o=O/"part_never_entered_body.mp4"
    subprocess.run([ff(),"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for i,s in enumerate(SCENES,1): r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cur,3); cur+=s.duration; r["end_seconds"]=round(cur,3); pl.append(r)
    (p:=O/"narration_timeline.json").write_text(json.dumps({"title":"part of you never entered the body","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
