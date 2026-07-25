#!/usr/bin/env python3
"""THE DEAD WERE BURIED WITH INSTRUCTIONS — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_dead_buried"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66)
TEAL=(67,157,180); PTE=(196,226,231); VIOLET=(130,104,160); PV=(206,196,216); DARK=(24,27,32); LAPIS=(56,76,124)
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
def gold_tablet(d,cx,cy,w,h,col=GOLD,progress=1.0):
    q=ease(progress)
    pts=[(cx-w,cy),(cx-w+q*w*0.3,cy-h),(cx+w-q*w*0.3,cy-h),(cx+w,cy)]
    d.polygon(pts,outline=(*col,int(210*q)),fill=(*PG,int(50*q)),width=max(1,int(3*q)))
    return (cx,cy-h/2)
def underworld_springs(d,cx,cy,r,col,progress=1.0):
    for i in range(2):
        x=cx+(i-0.5)*r*1.2; y=cy
        d.ellipse((x-r,cy-r,x+r,cy+r),outline=(*col,int(180*progress)),width=2)
        d.text((x,y),["MNEMOSYNE","LETHE"][i],font=lf(FSN,int(14)),fill=(*col,int(180*progress)),anchor="mm")
def road_of_souls(d,cx,cy,length,points,col=GOLD,progress=1.0):
    for i in range(points):
        q=clamp(progress*points-i)
        if q<=0: continue
        x=cx+(i/(points-1)-.5)*length; y=cy+math.sin(i*0.7)*12
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*col,int(200*q)))

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_gold_tablet(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gold_tablet(d,cx,cy,180,80,GOLD,pr)
    gc(im,cx,cy-40,30,GL,int(100*pr),16)
    lines=["I am a child of Earth and starry Heaven","My race is heavenly","Give me to drink from the spring of Memory"]
    for i,line in enumerate(lines):
        q=clamp(pr*1.5-i*.1)
        if q<=0: continue; y=cy+30+i*22
        ct(d,(cx,y),line,lf(FSN,int(h*.016)),mix(GOLD,INK,.3))
    seal(im,"THE DEAD WERE BURIED WITH INSTRUCTIONS","gold tablets in tombs — passwords for the afterworld")

def v_two_springs(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    underworld_springs(d,cx,cy,60,TEAL,pr)
    d.line((cx-80,cy+60,cx+80,cy+60),fill=(*INK,int(140*pr)),width=2)
    ct(d,(cx-60,cy+80),"FORGET",lf(FSNB,int(h*.016)),CRIMSON)
    ct(d,(cx+60,cy+80),"REMEMBER",lf(FSNB,int(h*.016)),TEAL)
    seal(im,"TWO SPRINGS IN THE UNDERWORLD","one makes the soul forget — one grants memory of the divine origin")

def v_password(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gc(im,cx,cy,25,GL,int(100*pr),14)
    road_of_souls(d,cx,cy+30,400,20,GOLD,pr)
    passwords=["I am parched with thirst — give me to drink","Of the spring of Memory","I am a child of Earth and starry Heaven"]
    for i,pwd in enumerate(passwords):
        q=clamp(pr*1.5-i*.1)
        if q<=0: continue
        x=cx+(i-1)*160; y=cy-50
        d.rounded_rectangle((x-80,y-14,x+80,y+14),radius=8,outline=(*GOLD,int(170*q)),fill=(*PG,int(15*q)),width=2)
        ct(d,(x,y),pwd[:30],lf(FSN,int(h*.015)),GOLD)
    seal(im,"A PASSWORD BECOMES A ROAD","the soul speaks — the guardians step aside")

def v_identity_death(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-80,cy-90,cx+80,cy+90),outline=(*GRAPHITE,int(160*pr)),width=3)
    gc(im,cx,cy-60,20,GOLD,int(80*pr),14)
    d.text((cx,cy-30),"WHO WERE YOU?",font=lf(FSB,int(h*.026)),fill=(*INK,int(200*pr)),anchor="mm")
    for i,ans in enumerate(["THE NAMES YOU ANSWERED TO","THE STORIES YOU TOLD","WHAT YOU LOVED"]):
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        ct(d,(cx,cy+25+i*30),ans,lf(FSN,int(h*.018)),mix(GOLD,TEAL,i/2))
    seal(im,"THE BODY MUST BE REMEMBERED","identity performed beyond death — the gold tablet as a map")

def v_guardians(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for side in [-1,1]:
        x=cx+side*180
        q=clamp(pr*1.3-(side+1)*.15)
        if q<=0: continue
        d.arc((x-50,cy-80,x+50,cy+20),200,340,fill=(*LAPIS,int(180*q)),width=4)
        d.line((x,cy-40,x,cy+40),fill=(*LAPIS,int(160*q)),width=3)
    gc(im,cx,cy,25,GL,int(120*pr),16)
    ct(d,(cx,cy),"YOU MUST PASS BY THEM",lf(FSB,int(h*.022)),GOLD)
    seal(im,"THE GUARDIANS OF THE THRESHOLD","they do not block the worthy — they test the prepared")

def v_material_ritual(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gold_tablet(d,cx,cy-20,140,60,GOLD,pr)
    for i,item in enumerate(["GOLD LEAF","INK","BURIAL WITH THE BODY","ORAL INSTRUCTION"]):
        q=clamp(pr*1.4-i*.07)
        if q<=0: continue
        y=cy+45+i*28
        d.ellipse((cx-120,y-12,cx-96,y+12),fill=(*mix(GOLD,INK,i/3),int(160*q)))
        ct(d,(cx+20,y),item,lf(FSN,int(h*.017)),mix(GOLD,INK,i/3))
    seal(im,"THE MATERIALITY OF INSTRUCTION","gold, ink, burial, speech — the medium belongs to the message")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,LAPIS),(150,GOLD),(100,TEAL),(50,GL)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,LAPIS,i/15),int(120*pr)))
    seal(im,"THE DEAD WERE BURIED WITH INSTRUCTIONS","folded gold leaf — two springs — a password becoming a road")

VISUALS={"gold_tablet":v_gold_tablet,"two_springs":v_two_springs,"password":v_password,"identity":v_identity_death,"guardians":v_guardians,"material":v_material_ritual,"closing":v_closing}
SCENES=[
    Scene("Gold Tablets","The dead were buried with instructions — thin gold leaf inscribed with memory.",5.5,"gold_tablet",{}),
    Scene("Orphic","The Orphic gold tablets — found in tombs across Greece and southern Italy.",5.5,"gold_tablet",{}),
    Scene("Instructions for the Soul","Instructions for the soul — what to say, which springs to avoid, which to drink from.",5.5,"gold_tablet",{}),
    Scene("Two Springs","Two springs in the underworld — Lethe and Mnemosyne.",5.5,"two_springs",{}),
    Scene("Forgetting","Lethe makes the soul forget its origin — the soul becomes trapped in the cycle of birth.",5.5,"two_springs",{}),
    Scene("Remembering","Mnemosyne restores memory of the divine origin — the soul is released.",5.5,"two_springs",{}),
    Scene("The Choice","The soul arrives thirsty — it must choose which spring to drink from.",5.5,"two_springs",{}),
    Scene("Password","The soul speaks a password to the guardians.",5.5,"password",{}),
    Scene("I Am a Child","I am a child of Earth and starry Heaven — my race is heavenly.",5.0,"password",{}),
    Scene("Give Me to Drink","Give me to drink from the spring of Memory — the password becomes a road.",5.5,"password",{}),
    Scene("Identity","The gold tablet asserts identity — not by name but by origin.",5.5,"identity",{}),
    Scene("Divine Descent","The soul has descended from heaven — the task is to remember and return.",5.5,"identity",{}),
    Scene("What Survives","The body must be remembered — not in its accidents, but in its divine belonging.",5.5,"identity",{}),
    Scene("Guardians","Guardians stand at the threshold — they do not block the worthy, they test the prepared.",5.5,"guardians",{}),
    Scene("Worthiness","Worthiness is memory — the soul that remembers its origin passes freely.",5.5,"guardians",{}),
    Scene("The Test","The test is not moral — it is ontological: do you know what you are?",5.5,"guardians",{}),
    Scene("Materiality","The instructions were material — gold leaf, ink, burial, oral tradition.",5.5,"material",{}),
    Scene("Medium and Message","The medium belongs to the message — gold that does not decay for a truth that death cannot corrupt.",5.5,"material",{}),
    Scene("Closing","The dead were buried with instructions — folded gold leaf, two springs, a password becoming a road.",6.0,"closing",{}),
    Scene("Final","What you are is not exhausted by what you have become — memory is the thread through the labyrinth.",6.5,"closing",{}),
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
    o=O/"dead_buried_with_instructions.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"the dead were buried with instructions","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
