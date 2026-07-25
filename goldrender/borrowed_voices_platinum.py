#!/usr/bin/env python3
"""THE UNIVERSE SPEAKS IN BORROWED VOICES — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_borrowed_voices"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66); TEAL=(67,157,180)
VIOLET=(130,104,160); LAPIS=(56,76,124); DARK=(24,27,32)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold"); FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0; q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def lf(p,s):
    for c in (p,FS,FSN):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rl(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,s,bg=IVORY):
    rng=np.random.default_rng(s); a=np.empty((h,w,3),dtype=np.float32); a[:]=bg
    a+=rng.normal(0,1.15,(h,w,1)); a=np.clip(a,0,255).astype(np.uint8)
    im=Image.fromarray(a,"RGB").convert("RGBA"); e=rl(im.size); d=ImageDraw.Draw(e)
    for i in range(14): al=int(i*.7); ins=20+i*3; d.rounded_rectangle((ins,ins,w-ins,h-ins),radius=16,outline=(*INK,al),width=2)
    im.alpha_composite(e); return im
def ct(d,xy,t,font,fill=INK): d.text(xy,t,font=font,fill=fill,anchor="mm")
def seal(im,t,sub="",c=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    ct(d,(w/2,h*.875),t,lf(FSB,max(20,int(h*.038))),c)
    if sub: ct(d,(w/2,h*.925),sub,lf(FSN,max(11,int(h*.018))),SOFT_INK)
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im); d.rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*INK,40),width=1)
def gc(im,cx,cy,r,col,al=180,bl=18):
    l=rl(im.size); ImageDraw.Draw(l).ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*col,al))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(bl)))
def gl(im,pts,col,w=4,g=14,al=225):
    if len(pts)<2: return
    l=rl(im.size); ImageDraw.Draw(l).line(pts,fill=(*col,al),width=w,joint="curve")
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(g))); im.alpha_composite(l)
def pp(points,progress):
    progress=clamp(progress)
    if len(points)<2: return points
    ls=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]; t=sum(ls); tr=t*progress
    o=[points[0]]; w=0.0
    for i,l in enumerate(ls):
        if w+l<=tr: o.append(points[i+1]); w+=l
        else: q=0.0 if l==0 else (tr-w)/l; ax,ay=points[i]; bx,by=points[i+1]; o.append((lerp(ax,bx,q),lerp(ay,by,q))); break
    return o
def wave_arc(d,cx,cy,amp,freq,phase,length,points=60):
    pts=[]
    for i in range(points):
        u=i/(points-1); x=cx-length/2+u*length; y=cy+math.sin(u*freq+phase)*amp
        pts.append((x,y))
    return pts

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_voices(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gc(im,cx,cy,22,GL,int(100*pr),14)
    for i in range(5):
        x=200+i*220; q=clamp(pr*1.5-i*.06)
        if q<=0: continue
        r=40+20*math.sin(t+i); d.ellipse((x-r,cy-50,x+r,cy+50),outline=(*mix(GOLD,TEAL,i/4),int(150*q)),width=2)
        d.text((x,cy+30),["ANCIENT","GUEST","DEITY","WORLD","SILENCE"][i],font=lf(FSN,int(h*.016)),fill=(*mix(GOLD,TEAL,i/4),int(180*q)),anchor="mm")
    seal(im,"THE UNIVERSE SPEAKS IN BORROWED VOICES","no voice is original — each is a transmission, a guest, a conduit")

def v_microphone(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    pts=[(cx-30,cy+40),(cx-30,cy-30),(cx+30,cy-30),(cx+30,cy+40)]
    d.polygon(pts,outline=(*GRAPHITE,int(170*pr)),width=3)
    d.ellipse((cx-15,cy-50,cx+15,cy-20),fill=(*SILVER,int(140*pr)),outline=(*GRAPHITE,180),width=2)
    for i in range(5):
        x=cx+(i-2)*35; q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        y=cy+50+15*math.sin(i+t*2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*TEAL,int(130*q)))
    seal(im,"A MICROPHONE WITH CHANGING SPEAKERS","the instrument is constant — who speaks through it changes")

def v_channel(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gl(im,wave_arc(d,cx,cy,40,6*math.pi,t*2,500,100),TEAL,3,12,190)
    gl(im,wave_arc(d,cx,cy,20,3*math.pi,-t,500,100),GOLD,2,10,150)
    gc(im,cx,cy-10,18,GL,int(80*pr),14)
    seal(im,"SIGNAL AND NOISE","the channel carries voices across time — the signal persists through changing media")

def v_borrowed(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    ct(d,(cx,cy-20),"ALL SPEECH IS BORROWED",lf(FSB,int(h*.028)),INK)
    for i,w in enumerate(["FROM LANGUAGE","FROM CULTURE","FROM THE AIR","FROM THE DEAD","FROM THE SOURCE"]):
        q=clamp(pr*1.5-i*.06)
        if q<=0: continue; y=cy+30+i*32
        d.ellipse((cx-120,y-10,cx-96,y+10),fill=(*mix(GOLD,TEAL,i/4),int(160*q)))
        ct(d,(cx+20,y),w,lf(FSN,int(h*.018)),mix(GOLD,TEAL,i/4))
    seal(im,"YOU DID NOT INVENT THE WORDS YOU ARE SPEAKING","they arrived from elsewhere — you are a temporary home for an ancient transmission")

def v_speakers(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(lab,col) in enumerate([("SELF",INK),("ANCESTORS",TEAL),("DEITIES",GOLD),("WORLD",VIOLET)]):
        q=clamp(pr*1.5-i*.06)
        if q<=0: continue
        x=200+i*240; y=cy+40*math.sin(i*1.5+t)
        d.ellipse((x-35,y-35,x+35,y+35),outline=(*col,int(170*q)),fill=(*mix(IVORY,col,.08),int(120*q)),width=2)
        ct(d,(x,y),lab,lf(FSNB,int(h*.016)),col)
        lineglow=d.line((cx,cy,int(x),int(y)),fill=(*col,int(60*q)),width=2)
    gc(im,cx,cy,18,GL,int(100*pr),14)
    seal(im,"THE SELF IS ONE SPEAKER AMONG MANY","the voice you call your own is a guest — the universe speaks through you")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,TEAL),(150,GOLD),(100,VIOLET),(50,CRIMSON)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,TEAL,i/15),int(120*pr)))
    seal(im,"THE UNIVERSE SPEAKS IN BORROWED VOICES","listen carefully — you are not only the one who speaks, but the one through whom speech passes")

VISUALS={"voices":v_voices,"microphone":v_microphone,"channel":v_channel,"borrowed":v_borrowed,"speakers":v_speakers,"closing":v_closing}
SCENES=[
    Scene("Borrowed Voices","The universe speaks in borrowed voices — no voice is original.",5.5,"voices",{}),
    Scene("Transmission","Each voice is a transmission — a guest passing through.",5.0,"borrowed",{}),
    Scene("Mic","A microphone with changing speakers — the instrument is constant.",5.5,"microphone",{}),
    Scene("Channel","Signal and noise — the channel carries voices across time.",5.5,"channel",{}),
    Scene("All Speech","All speech is borrowed — from language, culture, the air, the dead.",5.5,"borrowed",{}),
    Scene("You Did Not Invent","You did not invent the words you are speaking — they arrived from elsewhere.",5.5,"borrowed",{}),
    Scene("Temporary Home","You are a temporary home for an ancient transmission.",5.0,"borrowed",{}),
    Scene("Speakers","The self is one speaker among many — ancestors, deities, world.",5.5,"speakers",{}),
    Scene("Self","The voice you call your own is a guest.",5.0,"speakers",{}),
    Scene("Ancestors","The ancestors speak through your habits, your fears, your loves.",5.5,"speakers",{}),
    Scene("Deities","The deities speak through moments of unexpected clarity.",5.5,"speakers",{}),
    Scene("World","The world speaks through coincidence, beauty, disaster.",5.5,"speakers",{}),
    Scene("Closing","Listen carefully — you are not only the one who speaks.",6.0,"closing",{}),
    Scene("Final","You are the one through whom speech passes — the universe speaks in borrowed voices.",6.5,"closing",{}),
]

def rf(scene,fi,fc,w,h,s):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=bg(w,h,s,mix(IVORY,PAPER,.5))
    VISUALS[scene.visual](im,u,t,scene.params); border(im); return im.convert("RGB")
def req_ff():
    if not (e:=shutil.which("ffmpeg")): raise RuntimeError("ffmpeg required"); return e
def enc(idx,fps):
    ff=req_ff(); fd=FRAMES/f"scene_{idx:03d}"; o=SCENES_DIR/f"scene_{idx:03d}.mp4"
    subprocess.run([ff,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def rs(idx,scene,fps,w,h,preview):
    fd=FRAMES/f"scene_{idx:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    nf=max(2,round(scene.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(nf*.35),int(nf*.72),nf-1]): rf(scene,fi,nf,w,h,idx*1000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(nf): p=fd/f"{fi:05d}.jpg"
    if not p.exists(): rf(scene,fi,nf,w,h,idx*1000+fi).save(p,quality=95,subsampling=0)
    return enc(idx,fps)
def concat(paths):
    ff=req_ff(); c=O/"concat.txt"; c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    o=O/"universe_borrowed_voices.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"the universe speaks in borrowed voices","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
def cs(w,h):
    th=[]; tw,th2=320,int(320*h/w)
    for idx,s in enumerate(SCENES,1):
        nf=max(2,round(s.duration*FPS)); im=rf(s,int(nf*.72),nf,w,h,idx*1000+72); im.thumbnail((tw,th2)); th.append((idx,s.title,im.copy()))
    cols=4; rows=math.ceil(len(th)/cols); ch=th2+48
    sheet=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(sheet); font=lf(FSNB,14)
    for idx,tt,im in th: s=idx-1; x=(s%cols)*tw; y=(s//cols)*ch; sheet.paste(im,(x,y)); d.text((x+8,y+th2+10),f"{idx:02d}  {tt}",font=font,fill=INK)
    p=O/"contact_sheet.jpg"; sheet.save(p,quality=94); return p
def pa():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=FPS); p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true")
    return p.parse_args()
def main():
    args=pa()
    for d in (O,FRAMES,SCENES_DIR): d.mkdir(parents=True,exist_ok=True)
    tl=export_tl(); print(f"Timeline: {tl} | {len(SCENES)} scenes | {sum(s.duration for s in SCENES)/60:.2f}m")
    if args.scene:
        if not 1<=args.scene<=len(SCENES): raise ValueError
        print(rs(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview)); return
    rd=[]
    for idx,s in enumerate(SCENES,1):
        print(f"[{idx:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)"); r=rs(idx,s,args.fps,args.width,args.height,args.preview)
        if not args.preview: rd.append(r)
    print(f"Contact: {cs(args.width,args.height)}")
    if not args.preview: print(f"Final: {concat(rd)}")
if __name__=="__main__":
    main()
