#!/usr/bin/env python3
"""
KNOWLEDGE BINDS BY MAKING THE WORLD SMALL ENOUGH TO USE
A complete Platinum-house procedural visual essay.

Source:
expansion-essays/01_knowledge_binds_by_making_the_world_small_enough_to_use.md

HOUSE RULES
-----------
• 5–10 seconds per scene. Every shot transforms one state into another.
• Clean ivory scientific field. No slideshow layouts. Sparse labels only.
• Continuity object: a cyan aperture that first narrows, later becomes transparent.

PALETTE ROLES
-------------
IVORY = uncompressed field    CYAN = bottleneck / selective attention
GOLD = useful invariant       INK = fixed category
VIOLET = excluded variation   CRIMSON = defensive compression
GREEN = transparent concept
"""
from __future__ import annotations
import argparse,json,math,random,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_knowledge_binds"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
SILVER=(180,187,194); CYAN=(57,156,180); GOLD=(194,156,72); GL=(236,219,175)
VIOLET=(109,83,153); CRIMSON=(162,58,69); GREEN=(70,139,99)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold")
FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")

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
    e=rl(im.size); d=ImageDraw.Draw(e)
    for i in range(14): d.rounded_rectangle((20+i*3,20+i*3,w-20-i*3,h-20-i*3),radius=18,outline=(*INK,int(i*.7)),width=2)
    im.alpha_composite(e); return im
def ct(d,xy,t,f,fill=INK): d.text(xy,t,font=f,fill=fill,anchor="mm")
def seal(im,t,s="",c=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    ct(d,(w/2,h*.875),t,lf(FSB,max(22,int(h*.04))),c)
    if s: ct(d,(w/2,h*.923),s,lf(FSN,max(13,int(h*.019))),SOFT_INK)
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
def npts(w,h,c,s):
    r=random.Random(s); return [(r.uniform(w*.08,w*.92),r.uniform(h*.16,h*.70),[CYAN,VIOLET,GOLD,SOFT_INK,CRIMSON][i%5]) for i in range(c)]
def wbox(d,x,y,t,col,al=220,w=145,h=42):
    d.rounded_rectangle((x-w/2,y-h/2,x+w/2,y+h/2),radius=14,fill=(*mix(WHITE,col,.12),al),outline=(*col,al),width=2)
    ct(d,(x,y),t,lf(FSNB,16),(*col,al))

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def vc(im,u,t,p): # compress
    w,h=im.size; d=ImageDraw.Draw(im); r=npts(w,h,180,44); q=ease(u)
    aw=lerp(w*.34,w*.07,q); d.rounded_rectangle((w*.55-aw/2,h*.20,w*.55+aw/2,h*.60),radius=12,outline=(*CYAN,220),width=4)
    for x,y,col in r:
        xx=lerp(x,w*.78,q) if x>w*.55 else x; yy=lerp(y,h*.40,q) if x>w*.55 else y
        d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=(*col,int(80+110*q)))
    if q>.55:
        for i,l in enumerate(["FOOD","THREAT","FACE","PATH","MINE"]): wbox(d,w*.82,h*(.24+i*.08),l,[GREEN,CRIMSON,CYAN,GOLD,VIOLET][i],220,130,34)
    seal(im,"A WORLD TOO LARGE BECOMES USABLE — SURVIVAL DEPENDS ON SELECTIVE DISCARD")
def vt(im,u,t,p): # triad
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ss(.1,.62,u)
    for l,c,ox,oy in [("KNOWER",CYAN,-190,0),("KNOWN",GOLD,190,0),("RULE",VIOLET,0,155)]:
        x,y=cx+ox*q,cy+oy*q; gc(im,x,y,14,c,170,11)
        if q>.4: ct(d,(x,y-34),l,lf(FSNB,17),c)
    if q>.35:
        for i in range(3): x1,y1=cx+[(-190,0),(190,0),(0,155)][i][0]*q,cy+[(-190,0),(190,0),(0,155)][i][1]*q; x2,y2=cx+[(-190,0),(190,0),(0,155)][(i+1)%3][0]*q,cy+[(-190,0),(190,0),(0,155)][(i+1)%3][1]*q; d.line((x1,y1,x2,y2),fill=(*INK,int(150*q)),width=3)
    seal(im,"CONTRACTED KNOWLEDGE — KNOWER, KNOWN, AND RULE HARDEN INTO SEPARATE TERMS")
def vch(im,u,t,p): # chair
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.39; q=ease(u)
    for l,c,ox,oy in [("MOLECULES",VIOLET,-210,-100),("SCRATCHES",CRIMSON,210,-100),("HISTORY",GOLD,-220,100),("LIGHT",CYAN,220,100),("AIR",GREEN,0,170)]:
        ct(d,(cx+ox,cy+oy),l,lf(FSNB,15),(*c,int(210*(1-q*.85)))); d.line((cx+ox,cy+oy,cx,cy),fill=(*c,int(110*(1-q*.8))),width=2)
    d.line((cx-55,cy-55,cx-55,cy+80),fill=(*INK,230),width=6); d.line((cx+55,cy-55,cx+55,cy+80),fill=(*INK,230),width=6)
    d.line((cx-55,cy-15,cx+55,cy-15),fill=(*INK,230),width=8); d.line((cx-55,cy-55,cx+55,cy-55),fill=(*INK,230),width=8)
    ct(d,(cx,cy+130),"CHAIR",lf(FSB,30),INK)
    seal(im,"A CONCEPT WORKS BY EXCLUSION — THE OBJECT BECOMES MANAGEABLE BECAUSE MOST OF IT DISAPPEARS")
def vbn(im,u,t,p): # bottleneck
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for x,y,col in npts(w,h,120,88):
        xx=lerp(x,w*.39,q*.25); yy=lerp(y,cy,q*.45)
        if x<w*.44: d.ellipse((xx-3,yy-3,xx+3,yy+3),fill=(*col,130))
    d.rounded_rectangle((cx-lerp(w*.10,w*.0275,q),cy-h*.15,cx+lerp(w*.10,w*.0275,q),cy+h*.15),radius=8,outline=(*CYAN,230),width=4)
    for i,(l,c) in enumerate([("EDGE",CYAN),("SHAPE",GOLD),("CATEGORY",GREEN)]):
        wbox(d,w*.72+i*w*.08,cy+(i-1)*55,l,c,int(120+100*q),120,34)
    gl(im,pp([(w*.35,cy),(cx,cy),(w*.72,cy)],q),CYAN,5,210,13)
    seal(im,"THE INFORMATION BOTTLENECK — RETAIN WHAT PREDICTS THE TARGET, DISCARD WHAT THE TASK IGNORES")
def vts(im,u,t,p): # tasks
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for i,(l,c,ox,oy) in enumerate([("CLASSIFY",CYAN,-220,-95),("RECONSTRUCT",GOLD,220,-95),("NAVIGATE",GREEN,-220,105),("REMEMBER",VIOLET,220,105)]):
        x,y=cx+ox*q,cy+oy*q; wbox(d,x,y,l,c,220,160,40)
        for k in range(2+i): px=x+math.cos(k*math.tau/max(1,2+i))*42*q; py=y+math.sin(k*math.tau/max(1,2+i))*22*q; d.ellipse((px-5,py-5,px+5,py+5),fill=(*c,180))
        arrow(d,cx,cy,x,y,fill=(*c,170),width=2,head=7)
    gc(im,cx,cy,15,INK,150,10)
    seal(im,"THERE IS NO PURPOSE-FREE COMPRESSED TRUTH — THE GOAL DECIDES WHICH DIFFERENCES SURVIVE")
def vw(im,u,t,p): # worlds
    w,h=im.size; d=ImageDraw.Draw(im); q=ease(u)
    for i,l,c in enumerate([("BOTANIST",GREEN),("CARPENTER",GOLD),("AFRAID",CRIMSON),("CHILD",CYAN)]):
        x=w*(.18+i*.21)
        d.ellipse((x-70,h*.40-120,x+70,h*.40+120),outline=(*c,180),width=4)
        d.line((x,h*.40-30,x,h*.40+65),fill=(*INK,160),width=5)
        d.ellipse((x-38,h*.40-80,x+38,h*.40-5),outline=(*GREEN,120),width=3)
        ct(d,(x,h*.69),l,lf(FSNB,16),c)
    seal(im,"THE FIELD OVERLAPS, THE BOTTLENECK DIFFERS — TRAINING, MEMORY, AND STATE SHAPE THE APPEARING WORLD")

def arrow(d,x1,y1,x2,y2,fill=INK,width=3,head=10):
    d.line((x1,y1,x2,y2),fill=fill,width=width)
    a=math.atan2(y2-y1,x2-x1)
    for s in (-1,1): d.line((x2,y2,x2-math.cos(a+s*.52)*head,y2-math.sin(a+s*.52)*head),fill=fill,width=width)

def vpr(im,u,t,p): # prison
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for ox,oy in [(-190,-100),(-140,80),(0,-140),(145,-70),(190,95),(-20,140)]:
        x,y=lerp(cx+ox,cx,q),lerp(cy+oy,cy,q); d.ellipse((x-8,y-8,x+8,y+8),fill=(*VIOLET,int(150*(1-q*.5))))
    ct(d,(cx,cy),"I FAILED",lf(FSB,int(h*.055)),(*CRIMSON,int(230*q)))
    if q>.55: [d.line((cx+i*42,cy-130,cx+i*42,cy+130),fill=(*INK,int(160*(q-.55)/.45)),width=4) for i in range(-3,4)]
    seal(im,"A SUMMARY BECOMES A PRISON — THE MODEL CONTROLS WHICH FUTURE EVIDENCE CAN STILL APPEAR",c=CRIMSON)

def vfi(im,u,t,p): # final
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.40; q=ease(u)
    for x,y,col in npts(w,h,160,101): d.ellipse((x-2,y-2,x+2,y+2),fill=(*col,int(70+60*q)))
    d.rounded_rectangle((cx-lerp(w*.04,w*.09,q),cy-h*.17,cx+lerp(w*.04,w*.09,q),cy+h*.17),radius=8,outline=(*CYAN,int(220*(1-q*.55))),width=4)
    for rr in range(30,270,32): d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),outline=(*GOLD,int(85*q*(1-rr/300))),width=3)
    if q>.7: ct(d,(cx,h*.70),"JÑĀNAṂ BANDHAḤ",lf(FSB,30),GOLD)
    seal(im,"KNOWLEDGE BINDS BY MAKING THE WORLD SMALL ENOUGH TO USE — WISDOM REMEMBERS THE FIELD WAS NEVER CONTAINED",c=GOLD)

VISUALS={"compress":vc,"triad":vt,"chair":vch,"bottleneck":vbn,"tasks":vts,"worlds":vw,"prison":vpr,"final":vfi}
SCENES=[
    Scene("Too much world","A living organism cannot perceive everything, remember every detail, or test every interpretation before acting.",9.0,"compress",{}),
    Scene("Discard","To survive, it must discard.",5.5,"compress",{}),
    Scene("Usable","The nervous system compresses a world too large to inhabit into distinctions small enough to use.",10.0,"compress",{}),
    Scene("Jñānaṃ bandhaḥ","Knowledge is bondage.",6.5,"final",{}),
    Scene("Not anti-truth","The claim is not that truth enslaves and ignorance liberates.",7.0,"final",{}),
    Scene("Every closure","Every usable knowledge closes a larger field into one determinate world.",8.5,"compress",{}),
    Scene("Contracted knowledge","Cognition divided into knower, known object, and rule.",9.0,"triad",{}),
    Scene("Chair","To recognize a chair, the system ignores almost everything about it.",7.0,"chair",{}),
    Scene("Discarded details","Molecular composition, scratches, history, changing light, and air disappear from the usable concept.",9.5,"chair",{}),
    Scene("Bottleneck","A representation containing every detail would be as difficult to use as the world itself.",10.0,"bottleneck",{}),
    Scene("Info bottleneck","The Information Bottleneck retains information useful for predicting a target while discarding irrelevant variation.",10.0,"bottleneck",{}),
    Scene("Task dependence","Different tasks require different compressions — no single compressed truth independent of purpose.",10.0,"tasks",{}),
    Scene("Different worlds","A botanist sees species, a carpenter sees grain, a frightened person sees exits.",9.0,"worlds",{}),
    Scene("Model as prison","A model mistaken for the final structure of reality becomes a prison.",8.0,"prison",{}),
    Scene("Scores","A school score reduces a student — a credit score reduces a borrower — a border reduces a traveller.",9.5,"worlds",{}),
    Scene("Map and landscape","A map does not need to be false to hide the landscape — it only needs to be the only thing one sees.",10.0,"compress",{}),
    Scene("Transparent concept","A concept becomes transparent when it performs its task without measuring everything.",9.5,"final",{}),
    Scene("Closing","Knowledge binds by making the world small enough to use — wisdom begins when the user remembers the field was never contained.",10.0,"final",{}),
]

def rf(scene,fi,fc,w,h,s):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=bg(w,h,s); VISUALS[scene.visual](im,u,t,scene.params); return im.convert("RGB")
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
    o=O/"knowledge_binds.mp4"
    subprocess.run([ff(),"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cur,3); cur+=s.duration; r["end_seconds"]=round(cur,3); pl.append(r)
    (p:=O/"narration_timeline.json").write_text(json.dumps({"title":"knowledge binds by making the world small enough to use","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
def cs(w,h):
    th=[]; tw,th2=320,int(320*h/w)
    for i,s in enumerate(SCENES,1): nf=max(2,round(s.duration*FPS)); im=rf(s,int(nf*.72),nf,w,h,i*10000+72); im.thumbnail((tw,th2)); th.append((i,s.title,im.copy()))
    sht=Image.new("RGB",(4*tw,math.ceil(len(th)/4)*(th2+48)),IVORY); d=ImageDraw.Draw(sht)
    for i,t,im in th:
        s=i-1; x=(s%4)*tw; y=(s//4)*(th2+48); sht.paste(im,(x,y)); d.text((x+8,y+th2+7),f"{i:02d}  {t}",lf(FSNB,14),INK)
    (p:=O/"contact_sheet.jpg").save(sht,quality=94); return p
def pa():
    p=argparse.ArgumentParser(); p.add_argument("--fps",type=int,default=FPS); p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true")
    return p.parse_args()
def main():
    a=pa()
    for d in (O,FRAMES,SCENES_DIR): d.mkdir(parents=True,exist_ok=True)
    tl=export_tl(); print(f"Timeline: {tl} | Scenes: {len(SCENES)} | Runtime: {sum(s.duration for s in SCENES)/60:.2f}m")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError
        print(rs(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rd=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)"); r=rs(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rd.append(r)
    print(f"Contact: {cs(a.width,a.height)}")
    if not a.preview: print(f"Final: {concat(rd)}")
if __name__=="__main__":
    main()
