#!/usr/bin/env python3
"""ŚAKTI DRAWS THE LINE THAT TURNS PHYSICS INTO INFORMATION — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_sakti_line"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66); TEAL=(67,157,180)
VIOLET=(130,104,160); PV=(206,196,216); DARK=(24,27,32); LAPIS=(56,76,124); PTE=(196,226,231)
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
def bit_state(d,cx,cy,state,col=INK,size=16):
    r=size
    if state==0: d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(*col,180),width=2)
    else: d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*col,180),outline=(*col,180),width=2)
def line_between(d,x1,y1,x2,y2,col=CRIMSON,width=3):
    d.line((x1,y1,x2,y2),fill=(*col,200),width=width)

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_bit_from_it(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(2):
        x=cx+(i-.5)*120; y=cy
        q=clamp(pr*1.5-i*.15)
        if q<=0: continue
        bit_state(d,cx+(i-.5)*120,cy,i,LAPIS,int(16*q))
        ct(d,(x,y+40),["0","1"][i],lf(FSNB,int(h*.030)),LAPIS)
    line_between(d,cx-40,cy,cx+40,cy,CRIMSON,3)
    gc(im,cx,cy,30,GL,int(80*pr),18)
    ct(d,(cx,cy-50),"IT FROM BIT",lf(FSB,int(h*.022)),GOLD)
    seal(im,"BEFORE A BIT CAN BE ZERO OR ONE","something must distinguish the alternatives — Śakti draws the line")

def v_line(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.line((cx-200,cy,cx+200,cy),fill=(*INK,int(180*pr)),width=2)
    for i in range(2):
        x=cx+(i-.5)*200; col=[GOLD,TEAL][i]
        d.ellipse((x-25,cy-25,x+25,cy+25),outline=(*col,int(180*pr)),fill=(*mix(IVORY,col,.1),int(60*pr)),width=2)
        ct(d,(x,cy-50),["PHYSICS","INFORMATION"][i],lf(FSNB,int(h*.020)),col)
    gc(im,cx,cy,22,GL,int(100*pr),16)
    ct(d,(cx,cy),"ŚAKTI",lf(FSB,int(h*.035)),CRIMSON)
    seal(im,"THE BIT APPEARS ONLY AFTER MANIFESTATION HAS ACQUIRED THE POWER TO DRAW A LINE","śakti draws the line that turns physics into information")

def v_measurement(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-80,cy-60,cx+80,cy+60),outline=(*GRAPHITE,int(160*pr)),width=3)
    ct(d,(cx,cy),"SYSTEM",lf(FSNB,int(h*.022)),INK)
    measurement_probe = ss(.25,.65,u)
    if measurement_probe>0:
        x1,y1=cx+80,cy-20; x2,y2=cx+160,cy-40
        d.line((x1,y1,x2,y2),fill=(*TEAL,int(180*measurement_probe)),width=3)
        d.ellipse((x2-6,y2-6,x2+6,y2+6),fill=(*TEAL,int(200*measurement_probe)))
        ct(d,(x2+35,y2),"MEASUREMENT",lf(FSN,int(h*.016)),TEAL)
    seal(im,"MEASUREMENT YIELDS ALTERNATIVES","questions help define which properties become determinate")

def v_semantic(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    # Three boxes representing system, environment, meaning
    gc(im,cx,cy,20,GL,int(80*pr),14)
    d.rounded_rectangle((cx-110,cy-60,cx-20,cy+60),radius=12,outline=(*TEAL,int(170*pr)),width=3)
    ct(d,(cx-65,cy),"SYSTEM",lf(FSNB,int(h*.018)),TEAL)
    d.rounded_rectangle((cx+20,cy-60,cx+110,cy+60),radius=12,outline=(*VIOLET,int(170*pr)),width=3)
    ct(d,(cx+65,cy),"ENV",lf(FSNB,int(h*.018)),VIOLET)
    arrow=d.line((cx-20,cy,cx+20,cy),fill=(*GOLD,int(140*pr)),width=3)
    seal(im,"MEANING REQUIRES CONTEXT — A DECODER","information is matter organized so that difference can be preserved and used across transformations")

def v_living_bit(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    # A living cell with a bit that matters
    d.ellipse((cx-80,cy-70,cx+80,cy+70),outline=(*TEAL,int(170*pr)),width=3)
    d.ellipse((cx-50,cy-45,cx+50,cy+45),fill=(*PTE,int(60*pr)),outline=(*TEAL,int(90*pr)),width=1)
    bit_state(d,cx+30,cy-10,1,CRIMSON,10)
    bit_state(d,cx-20,cy+15,0,CRIMSON,10)
    ct(d,(cx,cy-45),"A LIVING BIT",lf(FSNB,int(h*.020)),TEAL)
    seal(im,"A LIVING BIT IS A PHYSICAL DISTINCTION ATTACHED TO VIABILITY","meaning enters through counterfactual consequence — the system's future depends upon the distinction")

def v_prakasha_vimarsha(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-130,cy-80,cx+130,cy+80),outline=(*GOLD,int(160*pr)),width=3)
    gc(im,cx-40,cy,25,GOLD,int(100*pr),14); gc(im,cx+40,cy,25,SILVER,int(80*pr),14)
    ct(d,(cx-40,cy-55),"PRAKĀŚA",lf(FSNB,int(h*.019)),GL)
    ct(d,(cx+40,cy+45),"VIMARŚA",lf(FSNB,int(h*.019)),SILVER)
    ct(d,(cx,cy),"CONSCIOUSNESS",lf(FSB,int(h*.022)),INK)
    seal(im,"BEFORE THE BIT — THE POWER OF DISTINCTION ITSELF","prakāśa illuminates — vimarśa reflects — consciousness is the ground of information")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,LAPIS),(150,GOLD),(100,TEAL),(50,VIOLET)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,LAPIS,i/15),int(120*pr)))
    seal(im,"ŚAKTI DRAWS THE LINE THAT TURNS PHYSICS INTO INFORMATION","the bit is never encountered without an architecture of distinction — consciousness is that architecture")

VISUALS={"bit":v_bit_from_it,"line":v_line,"measurement":v_measurement,"semantic":v_semantic,"living_bit":v_living_bit,"prakasha_vimarsha":v_prakasha_vimarsha,"closing":v_closing}
SCENES=[
    Scene("It from Bit","Before a bit can be zero or one, something must distinguish the alternatives.",5.5,"bit",{}),
    Scene("Distinction","Before the distinction can carry information, some system must preserve it.",5.5,"bit",{}),
    Scene("Consequence","Before information can matter, different values must lead to different consequences.",5.5,"bit",{}),
    Scene("Physics of Difference","Physics supplies differences everywhere — information appears when a difference enters an organized perspective.",5.5,"line",{}),
    Scene("Wheeler","John Wheeler: it from bit — physical reality rooted in acts of yes-or-no distinction.",5.5,"bit",{}),
    Scene("Earlier","Kashmir Śaivism begins earlier — the bit appears only after manifestation can draw a line.",5.5,"line",{}),
    Scene("Śakti Draws the Line","Śakti draws the line that turns physics into information.",5.5,"line",{}),
    Scene("Not Automatic","A bit in information theory is not automatically meaningful — meaning requires context.",5.5,"semantic",{}),
    Scene("Encoder","Which physical state encodes zero? Which encodes one? What system reads the difference?",5.5,"semantic",{}),
    Scene("Material Varies","A magnetic orientation can encode a bit — so can a voltage, a hole in a card, a nucleotide.",5.5,"bit",{}),
    Scene("Logical Distinction","The material varies — the logical distinction remains.",5.0,"bit",{}),
    Scene("Portability","This portability makes information appear more fundamental than matter.",5.0,"semantic",{}),
    Scene("Decoder Required","A voltage counts as one only inside a convention that treats it differently from zero — without a decoder, no symbol system.",5.5,"semantic",{}),
    Scene("Organized Matter","Information is not the absence of matter — it is matter organized so difference can be preserved across transformations.",5.5,"line",{}),
    Scene("Semantic Information","Kolchinsky and Wolpert: a correlation carries semantic information when scrambling it reduces the system's ability to maintain itself.",6.0,"semantic",{}),
    Scene("Counterfactual Consequence","Meaning enters through counterfactual consequence — the bit matters because the system's future depends upon the distinction.",5.5,"semantic",{}),
    Scene("Value Before Semantics","This places value before semantics — a difference matters because some organization can fare differently.",5.5,"living_bit",{}),
    Scene("Living Bit","A living bit is a physical distinction attached to viability.",5.0,"living_bit",{}),
    Scene("Viability","But viability already presupposes manifestation in a weaker sense — the organized perspective that can fare differently.",5.5,"living_bit",{}),
    Scene("Prakāśa-Vimarśa","Beneath it from bit lies a more fundamental structure: prakāśa-vimarśa — illumination and reflection.",5.5,"prakasha_vimarsha",{}),
    Scene("Ground of Information","Consciousness is not an emergent property of information — information is a mode of consciousness.",5.5,"prakasha_vimarsha",{}),
    Scene("Closing","Śakti draws the line that turns physics into information — the bit is never encountered without an architecture of distinction.",6.0,"closing",{}),
    Scene("Final","Consciousness is that architecture — the line is drawn not by a system within the world, but by the power through which the world appears.",6.5,"closing",{}),
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
    o=O/"sakti_draws_line.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"sakti draws the line that turns physics into information","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
