#!/usr/bin/env python3
"""THE SOUL NEEDS A SECOND BODY — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_soul_second_body"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); VIOLET=(130,104,160); PV=(206,196,216)
TEAL=(67,157,180); CRIMSON=(158,57,66); DARK=(24,27,32); GRAPHITE=(90,85,82); LAVENDER=(196,186,216)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold"); FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
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
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*INK,40),width=1)
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

def v_second_body(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-90,cy-30,cx+90,cy+50),outline=(*GRAPHITE,int(160*pr)),width=3)
    d.ellipse((cx-70,cy-15,cx+70,cy+35),outline=(*VIOLET,int(140*pr)),width=2)
    gc(im,cx,cy+10,25,LAVENDER,int(80*pr),14); d.ellipse((cx-8,cy+2,cx+8,cy+18),fill=(*WHITE,int(180*pr)))
    seal(im,"THE SOUL NEEDS A SECOND BODY","the ochēma-pneuma — a luminous vehicle between intellect and flesh")
def v_nested(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,r in enumerate([140,100,65,35]):
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        d.ellipse((cx-r,cy-60-r*.6,cx+r,cy-60+r*.6),outline=(*mix(LAVENDER,GOLD,i/3),int(150*q)),width=3-i)
        if i==3: gc(im,cx,cy-60,15,GL,int(120*q),12); d.ellipse((cx-6,cy-66,cx+6,cy-54),fill=(*WHITE,int(220*q)))
    seal(im,"NESTED BODIES","a soul wearing a luminous garment — the vehicle is the interface through which the soul acts on matter")
def v_colored_glass(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,c in enumerate([CRIMSON,TEAL,VIOLET,GOLD]):
        q=clamp(pr*1.5-i*.1)
        if q<=0: continue
        x=200+i*240; d.rectangle((x-30,cy-40,x+30,cy+20),outline=(*c,int(190*q)),fill=(*c,int(12*q)),width=2)
        if i>0: gl(im,[(x-30,cy-10),(x-240+30,cy-10)],mix(c,CRIMSON if i>1 else TEAL,.5),2,int(50*q),4)
    seal(im,"LIGHT PASSING THROUGH COLORED GLASS","the vehicle takes on character — shaped by life, by practice, by love")
def v_dream_space(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(8): a=i*2*math.pi/8+t*.05; r=lerp(20,150,pr); x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6; col=mix(GRAPHITE,LAVENDER,i/7); d.ellipse((x-4,y-4,x+4,y+4),fill=(*col,int(100*pr)))
    gc(im,cx,cy,30,LAVENDER,int(90*pr),16)
    seal(im,"DREAM-SPACE CARRIED BETWEEN WORLDS","the soul carries its vehicle across the threshold of death")
def v_character(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-100,cy-50,cx+100,cy+50),outline=(*VIOLET,int(160*pr)),width=2)
    for i in range(3): y=cy-20+i*30; gl(im,[(cx-80,y),(cx+80,y)],mix(VIOLET,GOLD,i/2),2,int(70*pr),5)
    gc(im,cx,cy,20,GL,int(80*pr),12)
    seal(im,"THE VEHICLE AS CHARACTER","shaped by every act — it becomes what you have made of yourself")
def v_survives(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gc(im,cx,cy-30,30,GL,int(100*pr),18); d.ellipse((cx-12,cy-42,cx+12,cy-18),fill=(*WHITE,int(200*pr)))
    d.ellipse((cx-50,cy-60,cx+50,cy-10),outline=(*GOLD,int(160*pr)),width=2)
    for i in range(6): a=i*2*math.pi/6; r=lerp(15,80,pr); x=cx+math.cos(a)*r; y=cy-30+math.sin(a)*r*.6; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,LAVENDER,i/5),int(130*pr)))
    seal(im,"WHAT SURVIVES","the form of a life is not lost — it is translated into the substance of the vehicle")
def v_interface(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(2): a=i*math.pi; x=cx+math.cos(a)*130; col=[GOLD,GRAPHITE][i]; d.ellipse((x-35,cy-50,x+35,cy+30),outline=(*col,int(170*pr)),width=2); ct(d,(x,cy+40),["INTELLIGIBLE","SENSIBLE"][i],lf(FSNB,int(h*.016)),col)
    gl(im,[(cx-95,cy-10),(cx+95,cy-10)],VIOLET,3,int(100*pr),7)
    seal(im,"INTERFACE BETWEEN INTELLECT AND BODY","the vehicle mediates — it is how the eternal touches the temporal")
def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(210,GRAPHITE),(160,VIOLET),(110,LAVENDER),(60,GL)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(130*pr),18); d.ellipse((cx-12,cy-72,cx+12,cy-48),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(LAVENDER,WHITE,i/15),int(120*pr)))
    seal(im,"THE LUMINOUS VEHICLE","you have been preparing your second body with every act — it is the shape of your becoming")

VISUALS={"second_body":v_second_body,"nested":v_nested,"colored_glass":v_colored_glass,"dream_space":v_dream_space,"character":v_character,"survives":v_survives,"interface":v_interface,"closing":v_closing}
SCENES=[
    Scene("Ochēma-Pneuma","The soul needs a second body — the ochēma-pneuma, a luminous vehicle between intellect and flesh.",5.5,"second_body",{}),
    Scene("The Vehicle","Not a ghost — not a second self — but the interface through which the soul acts on matter.",5.5,"second_body",{}),
    Scene("Nested Bodies","A soul wearing a luminous garment — nested bodies, each subtler than the last.",5.5,"nested",{}),
    Scene("The Garment","The Stoics called it pneuma — the Neoplatonists called it the ochēma — the vehicle that carries character.",5.5,"nested",{}),
    Scene("Light Through Glass","Light passing through colored glass — the vehicle takes on character.",5.5,"colored_glass",{}),
    Scene("Shaped by Life","Shaped by what you have loved — by what you have repeated — by what has wounded you.",5.5,"colored_glass",{}),
    Scene("The Vehicle Becomes Character","It is not a second self — it is the shape the self has grown into.",5.5,"character",{}),
    Scene("The Mark of Use","A tool bears the marks of how it was used — the vehicle bears the marks of how you have lived.",5.5,"character",{}),
    Scene("Dream-Space","The vehicle is the continuity between waking and sleeping — between living and dying.",5.5,"dream_space",{}),
    Scene("Threshold","The soul carries its vehicle across the threshold of death — the dream-space is practice for the crossing.",5.5,"dream_space",{}),
    Scene("What Survives","Not every detail — but the form, the character, the direction the life was taking.",5.5,"survives",{}),
    Scene("The Shape of a Life","The form of a life is not lost — it is translated into the substance of the vehicle.",5.5,"survives",{}),
    Scene("Interface","The vehicle is how the eternal touches the temporal — it partakes of both realms.",5.5,"interface",{}),
    Scene("Bridge","Neither pure intellect nor pure matter — the vehicle is the bridge.",5.0,"interface",{}),
    Scene("Closing","You have been preparing your second body with every act — it is the shape of your becoming.",6.0,"closing",{}),
    Scene("Final","The soul needs a second body — and the body the soul needs is the one it has been growing all along.",6.5,"closing",{}),
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
    for fi in range(nf):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists(): rf(scene,fi,nf,w,h,idx*1000+fi).save(p,quality=95,subsampling=0)
    return enc(idx,fps)
def concat(paths):
    ff=req_ff(); c=O/"concat.txt"; c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    o=O/"soul_needs_second_body.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"the soul needs a second body","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
