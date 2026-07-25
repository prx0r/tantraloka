#!/usr/bin/env python3
"""FORM NEEDS A PLACE THAT HAS NO FORM — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_form_needs_no_form"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); VIOLET=(130,104,160)
TEAL=(67,157,180); CRIMSON=(158,57,66); DARK=(24,27,32); GRAPHITE=(90,85,82)
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

def v_chora(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(5): r=20+i*40; al=int(80*(1-i/5)*pr); d.ellipse((cx-r,cy-60-r*.5,cx+r,cy-60+r*.5),outline=(*GOLD,al),width=2)
    gc(im,cx,cy-60,20,GL,int(80*pr),16); d.ellipse((cx-8,cy-68,cx+8,cy-52),fill=(*WHITE,int(200*pr)))
    seal(im,"FORM NEEDS A PLACE THAT HAS NO FORM","chōra — the receptacle that receives every form by possessing none")
def v_three_kinds(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(lb,col) in enumerate([("INTELLIGIBLE FORMS",GOLD),("SENSIBLE THINGS",TEAL),("CHŌRA — RECEPTACLE",VIOLET)]):
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        x=220+i*400; d.rounded_rectangle((x-80,y-50,x+80,y+50),radius=12,outline=(*col,int(170*q)),fill=(*col,int(10*q)),width=2); ct(d,(x,cy+10),lb,lf(FSNB,int(h*.017)),col)
    seal(im,"PLATO'S THREE KINDS","forms — changing things — the receptacle without which nothing could appear")
def v_gold_shaped(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-80,cy-30,cx+80,cy+50),fill=(*PG,int(30*pr)),outline=(*GOLD,int(180*pr)),width=3)
    for i in range(4): a=i*math.pi/2; x=cx+math.cos(a)*100*pr; y=cy+math.sin(a)*60*pr; d.polygon([(x-30,y-20),(x+30,y-10),(x+20,y+20),(x-25,y+15)],outline=(*mix(GOLD,TEAL,i/3),int(120*pr)),width=2)
    gc(im,cx,cy+10,20,GL,int(80*pr),14)
    seal(im,"LIKE GOLD REPEATEDLY RESHAPED","the same substance — many forms — the gold does not become the forms")
def v_morphospace(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(20): u2=i/19; x=lerp(150,1130,u2); y=cy-40+60*math.sin(u2*4+t)*pr; d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(TEAL,GOLD,u2),int(120*pr)))
    for i in range(4):
        pts=[(lerp(200,1080,j/19),cy-40+100*math.sin(j/19*3+i*pr)*pr) for j in range(20)]; rv=pp(pts,ss(.05+i*.08,.82,pr))
        if len(rv)>1: gl(im,rv,mix(TEAL,VIOLET,i/3),2,int(70*pr),5)
    seal(im,"MORPHOSPACE","an abstract space of possible forms — dimensions along which bodies can vary")
def v_mother_without_face(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(6): r=20+i*30; al=int(80*(1-i/6)*pr); d.ellipse((cx-r,cy-r*.6,cx+r,cy+r*.6),outline=(*mix(GRAPHITE,VIOLET,i/5),al),width=1)
    gc(im,cx,cy,30,VIOLET,int(80*pr),18)
    seal(im,"A MOTHER WITHOUT A FACE","the receptacle receives by being nothing in particular — she is not empty, she is available")
def v_element_change(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(lb,col) in enumerate([("FIRE",CRIMSON),("AIR",TEAL),("WATER",VIOLET)]):
        q=clamp(pr*1.5-i*.12)
        if q<=0: continue; x=lerp(300,980,(i+1)/4)
        d.ellipse((x-30,y-20,x+30,y+20),outline=(*col,int(180*q)),fill=(*col,int(15*q)),width=2); ct(d,(x,cy+10),lb,lf(FSNB,int(h*.017)),col)
        if i<2: x2=lerp(300,980,(i+2)/4); gl(im,[(x+30,cy+10),(x2-30,cy+10)],GOLD,2,int(80*q),5)
    seal(im,"FIRE BECOMES AIR — AIR BECOMES WATER","the forms change — what receives the change cannot itself be a form")
def v_dreamlike(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i in range(12): a=i*2*math.pi/12+t*.05; r=80+40*math.sin(t+i)*pr; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GRAPHITE,GOLD,i/11),int(80*pr)))
    gc(im,cx,cy,30,VIOLET,int(90*pr),18)
    seal(im,"DIFFICULT, DREAMLIKE REASONING","the receptacle is known through a kind of difficult reasoning — not by clear intellectual grasp")
def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,GOLD),(150,VIOLET),(100,TEAL),(50,SILVER)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(130*pr),18); d.ellipse((cx-12,cy-72,cx+12,cy-48),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*180*pr; y=cy-60+math.sin(a)*120*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,SILVER,i/15),int(120*pr)))
    seal(im,"THE RECEPTACLE MAKES APPEARANCE POSSIBLE","by itself appearing as nothing — it is the condition in which sensible becoming can occur")

VISUALS={"chora":v_chora,"three_kinds":v_three_kinds,"gold_shaped":v_gold_shaped,"morphospace":v_morphospace,"mother_without_face":v_mother_without_face,"element_change":v_element_change,"dreamlike":v_dreamlike,"closing":v_closing}
SCENES=[
    Scene("Chōra","Form needs a place that has no form — before anything can change shape, there must be a somewhere.",5.5,"chora",{}),
    Scene("Fire Becomes Air","Fire becomes air — air becomes water — the forms change.",5.0,"element_change",{}),
    Scene("The Wound Becomes Scar","An embryo becomes folded tissue — a wound becomes a scar — the forms change.",5.5,"chora",{}),
    Scene("What Receives Change","What receives the change cannot already be only one of the forms.",5.0,"chora",{}),
    Scene("Plato's Name","Plato gives this impossible receiver a name: chōra — a place that is not exactly place.",5.5,"chora",{}),
    Scene("Three Kinds","Intelligible forms — sensible things — the receptacle without which nothing could appear.",5.5,"three_kinds",{}),
    Scene("The Third Kind","Plato struggles to describe it — it is compared to a mother receiving the impress of a father.",5.5,"three_kinds",{}),
    Scene("Gold Reshaped","Like gold repeatedly shaped into different objects — the same substance receiving many forms.",5.5,"gold_shaped",{}),
    Scene("Neutral Base","A neutral base capable of taking many fragrances — the analogies circle something that cannot be pictured.",6.0,"gold_shaped",{}),
    Scene("Chōra Must Remain Available","Every picture would give the receptacle one determinate form — chōra must remain available.",5.5,"chora",{}),
    Scene("Not Empty Space","This does not make it empty space in the modern physical sense — it is the condition of becoming.",5.5,"chora",{}),
    Scene("Invisible, Unshaped, All-Receiving","The receptacle is characterized through deprivation — invisible, unshaped, all-receiving.",5.0,"chora",{}),
    Scene("Difficult Reasoning","Known through a kind of difficult, dreamlike reasoning — not clear intellectual grasp.",5.5,"dreamlike",{}),
    Scene("Morphospace","Modern biology uses a term that sounds unexpectedly close: morphospace — abstract space of possible forms.",5.5,"morphospace",{}),
    Scene("Dimensions of Variation","Its dimensions represent features along which organisms and structures can vary.",5.0,"morphospace",{}),
    Scene("The Landscape of the Possible","Not every point in morphospace is reachable from every other — constraints shape the landscape.",5.5,"morphospace",{}),
    Scene("A Mother Without a Face","She receives without possessing — she is not exactly empty, she is available.",5.0,"mother_without_face",{}),
    Scene("Available to All Forms","If the receiver were already essentially fire, it could not neutrally receive water.",5.5,"mother_without_face",{}),
    Scene("The Deprivation of Character","The receptacle is defined by its lack of definition — it is whatever is needed.",5.0,"mother_without_face",{}),
    Scene("Elemental Cycle","Fire, air, water, earth transform into one another — the cycle of bodies.",5.5,"element_change",{}),
    Scene("The Unseen Ground","Every appearance rests on something that does not itself appear — the ground of manifestation.",5.5,"chora",{}),
    Scene("The Receptacle Is Everywhere","Present wherever form happens — without becoming one of the forms that happens.",5.0,"chora",{}),
    Scene("Closing","The receptacle makes appearance possible — by itself appearing as nothing.",6.0,"closing",{}),
    Scene("Final","Form needs a place that has no form — and that place is what you are, before you become anything.",6.5,"closing",{}),
]

def rf(scene,fi,fc,w,h,s):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=bg(w,h,s,mix(IVORY,PAPER,.5))
    VISUALS[scene.visual](im,u,t,scene.params); border(im); return im.convert("RGB")
def req_ff():
    if not (e:=shutil.which("ffmpeg")): raise RuntimeError("ffmpeg required"); return e
def enc(idx,fps):
    ff=req_ff(); fd=FRAMES/f"scene_{idx:03d}"; o=SCENES_DIR/f"scene_{idx:03d}.mp4"
    subprocess.run([ff,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
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
    o=O/"form_needs_no_form.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"
    p.write_text(json.dumps({"title":"form needs a place that has no form","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
