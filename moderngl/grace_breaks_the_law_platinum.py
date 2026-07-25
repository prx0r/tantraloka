#!/usr/bin/env python3
"""GRACE BREAKS THE LAW THAT BROUGHT YOU HERE — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_grace_breaks_law"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66); PC=(229,193,197)
TEAL=(67,157,180); PTE=(196,226,231); VIOLET=(130,104,160); PV=(206,196,216); DARK=(24,27,32); GRAPHITE=(90,85,82)
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
def chain_links(d,cx,cy,count,spacing,color=GRAPHITE,alpha=200,progress=1.0):
    for i in range(count):
        q=clamp(progress*count-i)
        if q<=0: continue
        x=cx+i*spacing-count*spacing/2
        d.rounded_rectangle((x-12,cy-8,x+12,cy+8),radius=6,outline=(*color,int(alpha*q)),width=2)
        if i>0: d.line((x-12,cy,x-spacing+12,cy),fill=(*color,int(alpha*q*.5)),width=2)
def staircase(d,cx,cy,steps,width,height,color=INK,progress=1.0):
    for i in range(steps):
        q=clamp(progress*steps-i)
        if q<=0: continue
        y=cy-i*height
        w=width-i*(width*.08)
        d.line((cx-w,y,cx+w,y),fill=(*color,int(200*q)),width=max(2,int(4*(1-i/steps))))
        d.line((cx-w,y,cx-w,y+height),fill=(*color,int(120*q)),width=max(1,int(2*(1-i/steps))))
        d.line((cx+w,y,cx+w,y+height),fill=(*color,int(120*q)),width=max(1,int(2*(1-i/steps))))

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_chain(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    chain_links(d,cx,cy,8,60,GRAPHITE,200,pr)
    if pr>.55:
        p2=clamp((pr-.55)*2.5)
        break_idx=p.get("break_idx",3)
        bx=cx+(break_idx-4)*60
        d.line((bx-12,cy-3,bx+25,cy-25),fill=(*CRIMSON,int(180*p2)),width=3)
        gc(im,bx+30,cy-30,20,GL,int(100*p2),14)
    seal(im,"GRACE BREAKS THE LAW THAT BROUGHT YOU HERE","it enters where causality cannot reach")

def v_sail(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    pts=[(cx-55,cy+15),(cx-15,cy-45),(cx+15,cy-30),(cx+55,cy+15)]
    d.polygon(pts,outline=(*INK,int(180*pr)),fill=(*IVORY,int(20*pr)),width=3)
    for i in range(8):
        a=-.5+i*.14; r=35+85*pr; x=cx+math.cos(a)*r; y=cy+15+math.sin(a)*r*.6; col=mix(TEAL,GL,i/7)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*col,int(80*pr)))
    gc(im,cx,cy+15,20,GL,int(80*pr),14)
    seal(im,"THE SAIL DOES NOT PRODUCE THE WIND","it receives it — the wind is not earned")

def v_lightning(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    if pr>.15:
        p2=clamp((pr-.15)*1.5)
        bolt=[(cx,cy-130),(cx-35,cy-60),(cx+15,cy-30),(cx-25,cy+30),(cx+5,cy+70)]
        rv=pp(bolt,p2)
        if len(rv)>1: gl(im,rv,GL,6,int(200*p2),14)
        gc(im,cx,cy-130,18,GL,int(140*p2),16)
    seal(im,"LIGHTNING ENTERING A HOUSE","sudden, unearned, transformative — it does not ask permission, it arrives")

def v_staircase(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    staircase(d,cx,cy+80,10,220,35,INK,pr)
    gc(im,cx,cy-60,40,GL,int(80*pr),22)
    seal(im,"THE STAIRCASE DISSOLVING INTO SKY","the lower steps are solid — the higher steps become light")

def v_freedom(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(3): r=50+i*40*pr; al=int(120*(1-i/3)*pr); d.ellipse((cx-r,cy-60-r*.5,cx+r,cy-60+r*.5),outline=(*GOLD,al),width=2)
    gc(im,cx,cy-60,20,GL,int(100*pr),16); d.ellipse((cx-8,cy-68,cx+8,cy-52),fill=(*WHITE,int(200*pr)))
    seal(im,"THE FREEDOM OF GRACE","not the freedom to choose — the freedom to be chosen — the gift is the nature of the source")

def v_fulfillment(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(6):
        r=30+i*30*(1-.5*pr); al=int(100*(1-i/6)*(1-pr*.5))
        if al<5: continue
        d.ellipse((cx-r,cy-60-r*.5,cx+r,cy-60+r*.5),outline=(*mix(GRAPHITE,GOLD,i/5),al),width=2)
    if pr>.5:
        p2=clamp((pr-.5)*2)
        gc(im,cx,cy-60,30,GL,int(140*p2),20); d.ellipse((cx-12,cy-72,cx+12,cy-48),fill=(*WHITE,int(220*p2)),outline=(*GOLD,int(200*p2)),width=2)
    seal(im,"FULFILLMENT IS SUDDEN SILENCE","the search ends not by reaching an object but by the need dissolving")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(210,GRAPHITE),(160,TEAL),(110,GOLD),(60,GL)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,TEAL,i/15),int(120*pr)))
    seal(im,"THE LAW DESCRIBED THE CONTAINER — GRACE FILLS IT","not by destroying the law — by revealing what the law was pointing toward")

VISUALS={"chain":v_chain,"sail":v_sail,"lightning":v_lightning,"staircase":v_staircase,"freedom":v_freedom,"fulfillment":v_fulfillment,"closing":v_closing}
SCENES=[
    Scene("Broken Chain","Grace breaks the law that brought you here — it enters where causality cannot reach.",5.5,"chain",{}),
    Scene("The Law","The law describes the structure — karma, causality, the regular order of things.",5.5,"chain",{}),
    Scene("What the Law Cannot Do","What the law cannot do is initiate — it can only continue what has already begun.",5.5,"chain",{}),
    Scene("Grace Enters","Grace is not a violation of law — it is a different order acting within the same territory.",5.5,"chain",{}),
    Scene("Sail and Wind","The sail does not produce the wind — it receives it.",5.5,"sail",{}),
    Scene("Not Earned","The wind is not earned — the only question is whether the sail is open.",5.5,"sail",{}),
    Scene("Preparation","You cannot deserve grace — you can only become available to it.",5.5,"sail",{}),
    Scene("Lightning","Lightning entering a house — sudden, unearned, transformative.",5.5,"lightning",{}),
    Scene("It Arrives","The lightning does not ask permission — it arrives.",5.0,"lightning",{}),
    Scene("After Lightning","After the lightning, the house is different — not because it earned the strike, but because the energy passed through.",5.5,"lightning",{}),
    Scene("Staircase","The staircase dissolving into sky — the lower steps are solid, the higher become light.",5.5,"staircase",{}),
    Scene("Steps Become Light","Grace does not cancel the law — it fulfills it by going beyond it.",5.5,"staircase",{}),
    Scene("The Ascent","The climb is real — but the top of the staircase opens onto something the steps themselves could not generate.",5.5,"staircase",{}),
    Scene("Freedom","The freedom of grace — not the freedom to choose, but the freedom to be chosen.",5.5,"freedom",{}),
    Scene("Not a Wage","The gift is not payment — it is not a wage — it is the nature of the source.",5.5,"freedom",{}),
    Scene("Receptivity","The only preparation is the willingness to receive.",5.0,"freedom",{}),
    Scene("Grace Is Always Present","Grace is always present — the variable is the openness of the receiver.",5.5,"freedom",{}),
    Scene("Fulfillment","Fulfillment is sudden silence — the search ends by the need dissolving.",5.5,"fulfillment",{}),
    Scene("Not Reaching","The point was not reaching an object — the point was the awakening of capacity.",5.5,"fulfillment",{}),
    Scene("The Object Falls Away","When grace arrives, the object falls away — what remains is the capacity that was seeking it.",5.5,"fulfillment",{}),
    Scene("Closing","The law described the container — grace fills it.",6.0,"closing",{}),
    Scene("Final","Grace breaks the law that brought you here — not by destroying it, but by completing it.",6.5,"closing",{}),
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
    o=O/"grace_breaks_the_law.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"grace breaks the law that brought you here","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
