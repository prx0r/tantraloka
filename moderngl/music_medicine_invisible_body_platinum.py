#!/usr/bin/env python3
"""MUSIC IS MEDICINE FOR THE INVISIBLE BODY — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_music_medicine"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
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
def lyre(d,cx,cy,scale,col=GOLD,progress=1.0):
    d.arc((cx-30*scale,cy-50*scale,cx+30*scale,cy+50*scale),200,340,fill=(*col,int(180*progress)),width=3)
    d.line((cx-30*scale,cy,cx-30*scale,cy+60*scale),fill=(*col,int(170*progress)),width=2)
    d.line((cx+30*scale,cy,cx+30*scale,cy+60*scale),fill=(*col,int(170*progress)),width=2)
    for i in range(4):
        x=lerp(cx-25*scale,cx+25*scale,i/3); y=cy+15*scale+10*math.sin(i*1.5)
        d.line((x,cy-20*scale,x,y),fill=(*col,int(130*progress)),width=1)

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_lyre(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    lyre(d,cx,cy,1.2,GOLD,pr)
    gc(im,cx,cy-20,25,GL,int(100*pr),16)
    for i in range(5):
        a=-.5+i*.25; r=lerp(20,120,pr); x=cx+math.cos(a)*r; y=cy-40+math.sin(a)*r*.7
        col=mix(TEAL,VIOLET,i/4); d.ellipse((x-5,y-5,x+5,y+5),fill=(*col,int(140*pr)))
    seal(im,"MUSIC IS MEDICINE FOR THE INVISIBLE BODY","Ficino: the lyre and the pulse — spiritus, melancholy, and the harmony of the soul")

def v_vapour(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gl(im,pp([(cx-80,cy+20),(cx,cy-30+20*math.sin(t)*pr),(cx+80,cy+20)],pr),TEAL,3,12,180)
    gl(im,pp([(cx-80,cy+35),(cx,cy-15+20*math.sin(t+1)*pr),(cx+80,cy+35)],pr),GOLD,2,10,140)
    gc(im,cx,cy-20,20,GL,int(80*pr),14)
    seal(im,"THE VAPOROUS INTERMEDIARY BODY","spiritus — the subtle medium through which music reaches the soul")

def v_harmony(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-90,cy-70,cx+90,cy+70),outline=(*GOLD,int(170*pr)),width=3)
    for i in range(3):
        a=-math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*130; y=cy+math.sin(a)*90
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        col=[GOLD,TEAL,VIOLET][i]; d.ellipse((x-12,y-12,x+12,y+12),fill=(*col,int(160*q)))
        ct(d,(x,y+30),["SATURN","JUPITER","SOUL"][i],lf(FSNB,int(h*.015)),col)
    seal(im,"SATURN AND JUPITER IN BALANCE","melancholy transformed — the room retuned by one chord")

def v_resonance(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(2):
        x=cx+(i-.5)*140; q=clamp(pr*1.3-i*.1)
        if q<=0: continue
        col=[TEAL,CRIMSON][i]; d.ellipse((x-25,cy-25,x+25,cy+25),outline=(*col,int(170*q)),width=2)
        ct(d,(x,cy),["BODY","SOUL"][i],lf(FSNB,int(h*.017)),col)
    if pr>.5:
        p2=clamp((pr-.5)*2)
        for i in range(8):
            a=i*2*math.pi/8; r=lerp(30,110,pr)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
            d.ellipse((x-4,y-4,x+4,y+4),fill=(*GOLD,int(120*p2)))
    seal(im,"THE HARMONY BETWEEN THE VISIBLE AND THE INVISIBLE","music is the bridge — it prepares the soul to receive what the intellect cannot force")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,GOLD),(150,TEAL),(100,VIOLET),(50,CRIMSON)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,TEAL,i/15),int(120*pr)))
    seal(im,"MUSIC IS MEDICINE FOR THE INVISIBLE BODY","the lyre and the pulse — one chord can retune the room")

VISUALS={"lyre":v_lyre,"vapour":v_vapour,"harmony":v_harmony,"resonance":v_resonance,"closing":v_closing}
SCENES=[
    Scene("Lyre and Pulse","Music is medicine for the invisible body — Ficino's lyre and the pulse.",5.5,"lyre",{}),
    Scene("Spiritus","Spiritus — the vaporous intermediary between soul and body.",5.5,"vapour",{}),
    Scene("Melancholy","The scholar's melancholy — black bile, genius, and the risk of despair.",5.5,"harmony",{}),
    Scene("Saturn","Saturn太重, Jupiter解放 — astrology as inner geometry.",5.5,"harmony",{}),
    Scene("One Chord","One chord can retune the room — resonance before understanding.",5.5,"lyre",{}),
    Scene("Bridge","Music prepares the soul to receive what the intellect cannot force.",5.5,"resonance",{}),
    Scene("Medicine","Not for the body — for what the body contains but cannot touch.",5.5,"vapour",{}),
    Scene("Closing","Music is medicine for the invisible body — the lyre and the pulse.",6.0,"closing",{}),
    Scene("Final","One chord can retune the room — you have been listening to the wrong silence.",6.5,"closing",{}),
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
    o=O/"music_medicine_invisible_body.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"music is medicine for the invisible body","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
