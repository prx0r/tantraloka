#!/usr/bin/env python3
"""YOUR VOICE EXISTED BEFORE LANGUAGE — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_voice_before_language"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66); TEAL=(67,157,180)
VIOLET=(130,104,160); DARK=(24,27,32); LAPIS=(56,76,124)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold"); FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")
DEVA="/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf"

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0; q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def lf(p,s):
    for c in (p,FS,FSN,DEVA):
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

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_before_words(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gc(im,cx,cy,25,GL,int(100*pr),16)
    ct(d,(cx,cy-40),"BEFORE YOU SPEAK",lf(FSB,int(h*.026)),INK)
    for i,s in enumerate(["PRESSURE IN THE CHEST","GATHERING IN THE THROAT","DIRECTION WITHOUT GRAMMAR"]):
        q=clamp(pr*1.5-i*.08)
        if q<=0: continue; y=cy+15+i*32
        d.ellipse((cx-150,y-10,cx-126,y+10),fill=(*TEAL,int(150*q)))
        ct(d,(cx+20,y),s,lf(FSN,int(h*.017)),TEAL)
    seal(im,"YOUR VOICE BEGINS BEFORE LANGUAGE","the invisible acquires edges — breath rises, the mouth opens")

def v_mind_is_mantra(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    ct(d,(cx,cy-40),"चित्तं मन्त्रः",lf(DEVA,int(h*.040)),GOLD)
    ct(d,(cx,cy-15),"MIND IS MANTRA",lf(FSB,int(h*.026)),INK)
    for i,s in enumerate(["NOT EVERY THOUGHT","BUT THE POWER THAT FORMS","HOLDS AND DIRECTS","AND RETURNS TO SOURCE"]):
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue; y=cy+30+i*30
        d.ellipse((cx-8,y-3,cx+8,y+3),fill=(*GOLD,int(180*q)))
        ct(d,(cx+25,y),s,lf(FSN,int(h*.016)),GOLD)
    seal(im,"A MANTRA IS A CONFIGURATION THE MIND BECOMES","not only something the mind repeats — a form of attention returning to its source")

def v_breath_rises(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    pts=[]
    for i in range(100):
        u2=i/99; x=lerp(200,1080,u2); y=cy+math.sin(u2*4+t*2)*20*pr*(1+math.sin(u2)*.5)
        pts.append((x,y))
    gl(im,pts,TEAL,4,13,200)
    if pr>.3:
        p2=clamp((pr-.3)*1.5)
        for i in range(5):
            a=-.3+i*.15; x=cx+math.sin(a)*80; y=cy-30+math.cos(a)*60
            d.ellipse((x-5,y-5,x+5,y+5),fill=(*GOLD,int(140*p2)))
    seal(im,"BREATH RISES — THE INVISIBLE ACQUIRES EDGES","before words, there is vibration — the voice begins as pure potential")

def v_speech_emerges(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-100,cy-60,cx+100,cy+60),outline=(*GOLD,int(170*pr)),width=3)
    for i,g in enumerate(['अ','आ','इ','उ','ओ','क','ख','ग']):
        q=clamp(pr*1.5-i*.05)
        if q<=0: continue
        a=-math.pi/2+i*2*math.pi/8; x=cx+math.cos(a)*120; y=cy+math.sin(a)*80
        ct(d,(x,y),g,lf(DEVA,int(h*.024)),mix(GOLD,TEAL,i/7))
    seal(im,"FROM VIBRATION TO PHONEME","consciousness becomes audible — the alphabet is the shape awareness takes when it crosses into sound")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,GOLD),(150,TEAL),(100,VIOLET),(50,CRIMSON)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    ct(d,(cx,cy-110),"YOUR VOICE EXISTED BEFORE LANGUAGE",lf(FSB,int(h*.022)),GOLD)
    seal(im,"MANTRA IS CONSCIOUSNESS BECOMING AUDIBLE","the voice is not a tool language uses — language is a shape the voice takes")

VISUALS={"before_words":v_before_words,"mind_is_mantra":v_mind_is_mantra,"breath_rises":v_breath_rises,"speech_emerges":v_speech_emerges,"closing":v_closing}
SCENES=[
    Scene("Before Words","Before you speak, the sentence is already moving — not as words.",5.5,"before_words",{}),
    Scene("Pressure","Pressure in the chest — a gathering in the throat — direction without grammar.",5.5,"before_words",{}),
    Scene("Knows Before","You know that something wants to emerge before you know what it will say.",5.5,"before_words",{}),
    Scene("Breath Rises","Breath rises — the mouth opens — the invisible acquires edges.",5.5,"breath_rises",{}),
    Scene("Mantra","Kashmir Śaivism begins its philosophy of mantra inside this transition.",5.5,"mind_is_mantra",{}),
    Scene("Not a Word","Mantra is not fundamentally a sacred word added to an otherwise silent universe.",5.5,"mind_is_mantra",{}),
    Scene("Becoming Audible","It is consciousness becoming audible — the voice begins before language.",5.5,"mind_is_mantra",{}),
    Scene("Śiva Sūtras","cittaṃ mantraḥ — mind is mantra.",5.5,"mind_is_mantra",{}),
    Scene("Power","The power by which awareness forms, holds, and directs mental content.",5.5,"mind_is_mantra",{}),
    Scene("Configuration","A mantra is a configuration the mind becomes — not only something it repeats.",5.5,"mind_is_mantra",{}),
    Scene("From Silence","From silence to vibration — from vibration to phoneme — from phoneme to speech.",5.5,"speech_emerges",{}),
    Scene("Closing","Your voice existed before language — Mantra is consciousness becoming audible.",6.0,"closing",{}),
    Scene("Final","The voice is not a tool language uses — language is a shape the voice takes.",6.0,"closing",{}),
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
    o=O/"voice_existed_before_language.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"your voice existed before language","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
