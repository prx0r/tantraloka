#!/usr/bin/env python3
"""
THE UNIVERSE IS HIDING INSIDE YOUR ATTENTION
A complete Platinum-house procedural visual essay.

DESIGN CONTRACT
• Every shot lasts 4-8 seconds and performs the narrated operation.
• Clean ivory-white field; concept-led colour only.
• Ivory = receptive field of awareness
• Gold = attended / selected reality
• Silver = background / unclaimed presence
• Graphite = the field before selection
• Violet = the gap between perceptions
• Sparse typography — terms as seals, never paragraphs.
• Each mature frame (u=0.72) works as a still.
• Continuity object: the gold bindu of attention persists across chapters.
"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict
from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_attention_hiding"
FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10

IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248)
INK=(30,32,36); SOFT_INK=(86,89,94); GRAPHITE=(90,85,82); PALE_G=(182,178,174)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192)
VIOLET=(130,104,160); PV=(206,196,216); TEAL=(67,157,180); CRIMSON=(158,57,66)
DARK=(24,27,32)

FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold")
FSN="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FSNB=FSN.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)

def lf(path,s):
    for c in (path,FS,FSN):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()

def rl(sz): return Image.new("RGBA",sz,(0,0,0,0))

def bg(w,h,s,bg=IVORY):
    rng=np.random.default_rng(s)
    a=np.empty((h,w,3),dtype=np.float32); a[:]=bg
    a+=rng.normal(0,1.15,(h,w,1)); a=np.clip(a,0,255).astype(np.uint8)
    im=Image.fromarray(a,"RGB").convert("RGBA")
    e=rl(im.size); d=ImageDraw.Draw(e)
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
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

def v_selection(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(30):
        u2=i/29; x=lerp(100,1180,u2); y=lerp(150,430,.5+.5*math.sin(u2*3))
        al=int(60*(1-abs(u2-.5)))
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*GRAPHITE,al))
    gc(im,cx,cy,35,GL,int(120*pr),18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=(*WHITE,int(200*pr)))
    seal(im,"SOMETHING IS SELECTING YOUR REALITY BEFORE YOU KNOW IT","the universe does not simply appear — it is admitted")

def v_field_divides(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(8):
        r=30+i*25*pr; al=int(100*(1-i/8)*pr)
        if al<5: continue
        d.ellipse((cx-r,cy-40-r*.5,cx+r,cy-40+r*.5),outline=(*GOLD,al),width=2)
    gc(im,cx,cy-40,20,GL,int(100*pr),14)
    d.ellipse((cx-8,cy-48,cx+8,cy-32),fill=(*WHITE,int(200*pr)))
    seal(im,"ONE FIELD DIVIDES INTO CENTER AND EDGE","choose one thing — it brightens — everything else becomes background")

def v_prakasha_vimarsha(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    d.ellipse((cx-140,cy-80,cx+140,cy+60),outline=(*GOLD,int(160*pr)),width=3)
    gc(im,cx-50,cy-10,25,GOLD,int(100*pr),14); gc(im,cx+50,cy-10,25,SILVER,int(80*pr),14)
    ct(d,(cx-50,cy-55),"PRAKĀŚA",lf(FSNB,int(h*.017)),GL)
    ct(d,(cx+50,cy+45),"VIMARŚA",lf(FSNB,int(h*.017)),SILVER)
    seal(im,"LIGHT AND REFLECTION — LIVING AWARENESS","light alone would reveal everything but recognize nothing")

def v_your_name(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(25):
        u2=i/24; x=lerp(120,1160,u2); y=lerp(160,420,.3+.4*math.sin(u2*5))
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*mix(GRAPHITE,TEAL,u2),80))
    if pr>.3:
        p2=clamp((pr-.3)*1.5)
        gc(im,cx,cy,40,GL,int(150*p2),20)
        d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=(*WHITE,int(220*p2)))
        for i in range(12):
            a=i*2*math.pi/12; x=cx+math.cos(a)*60; y=cy+math.sin(a)*60
            d.ellipse((x-6,y-6,x+6,y+6),fill=(*GL,int(160*p2)))
    seal(im,"YOUR NAME IN THE CROWD","one sound comes forward — it was physically no louder than the others — it finds the center")

def v_gap(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(3):
        y=190+i*60; q=clamp(pr*1.3-i*0.08)
        if q<=0: continue
        d.rectangle((250,y-8,1060,y+8),outline=(*GRAPHITE,int(80*q)),width=1)
        d.ellipse((400,y-15,440,y+15),fill=(*mix(VIOLET,GOLD,i/2),int(120*q)))
        d.ellipse((840,y-15,880,y+15),fill=(*mix(GOLD,TEAL,i/2),int(120*q)))
    if pr>.6:
        p2=clamp((pr-.6)*2.5)
        gc(im,cx,cy-5,30,VIOLET,int(80*p2),16)
        ct(d,(cx,cy+30),"THE GAP IS NOT EMPTY — IT IS THE SOURCE",lf(FSN,int(h*.015)),VIOLET)
    seal(im,"THE GAP BETWEEN PERCEPTIONS","what survives the gap is more fundamental than any content")

def v_admitted(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(5):
        r=lerp(10,180,pr)-i*30; al=int(120*(1-i/5)*pr)
        if r<10 or al<5: continue
        d.arc((cx-r,cy-60-r*.5,cx+r,cy-60+r*.5),200,340,fill=(*mix(GRAPHITE,GOLD,i/4),al),width=2)
    gc(im,cx,cy-60,15+30*pr,GL,int(100+80*pr),16)
    d.ellipse((cx-10,cy-70,cx+10,cy-50),fill=(*WHITE,int(220*pr)))
    seal(im,"THE UNIVERSE IS ADMITTED — NOT CREATED","consciousness decides what becomes real")

def v_infinite_possible(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(16):
        a=i*2*math.pi/16; r=120+30*ease(1-pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GRAPHITE,GOLD,i/15)
        d.ellipse((x-5,y-5,x+5,y+5),fill=(*col,int(80+80*pr)))
    gc(im,cx,cy,25+20*pr,GL,int(80+120*pr),16)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=(*WHITE,int(220*pr)))
    seal(im,"INFINITE POSSIBLE WORLDS — ATTENTION CHOOSES ONE","the chosen thing brightens — everything else becomes background")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; pr=ease(u)
    for i in range(3):
        r=50+i*55*pr; al=int(120*(1-i/3)*pr)
        d.ellipse((cx-r,cy-60-r*.6,cx+r,cy-60+r*.6),outline=(*mix(GOLD,SILVER,i/2),al),width=2)
    gc(im,cx,cy-60,20+40*pr,GL,int(120+100*pr),20)
    d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(14):
        a=i*2*math.pi/14+t*.03; x=cx+math.cos(a)*180; y=cy-60+math.sin(a)*120
        d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,WHITE,i/13),int(130*pr)))
    seal(im,"CAITANYAM ĀTMĀ — CONSCIOUSNESS IS THE SELF","the luminous field aware of itself — fold upon fold, saying: this, here, now")

VISUALS={
    "selection":v_selection,"field_divides":v_field_divides,"prakasha_vimarsha":v_prakasha_vimarsha,
    "your_name":v_your_name,"gap":v_gap,"admitted":v_admitted,"infinite_possible":v_infinite_possible,"closing":v_closing,
}

SCENES=[
    Scene("Selection","Something is selecting your reality before you know you have made a choice.",5.0,"selection",{}),
    Scene("Attention","A sound in the next room disappears — the pressure of your clothes vanishes until mentioned.",5.5,"selection",{}),
    Scene("A Memory Waits","A memory waits in darkness — one smell opens the door and the whole lost world returns.",5.5,"selection",{}),
    Scene("Attention Is Dangerous","Kashmir Śaivism treats attention as far more dangerous than a flashlight.",5.0,"selection",{}),
    Scene("The Universe Is Admitted","The universe does not simply appear — it is admitted.",5.0,"admitted",{}),
    Scene("Close Your Eyes","Sounds — sensations — thoughts — choose one thing — the chosen brightens.",5.5,"field_divides",{}),
    Scene("Center and Edge","Everything else becomes background, potential, unclaimed presence.",5.0,"field_divides",{}),
    Scene("The Beginning of a World","One field has divided itself into center and edge — that division is the beginning of a world.",5.5,"field_divides",{}),
    Scene("Prakāśa — Illumination","The capacity for anything to appear — light that reveals.",5.0,"prakasha_vimarsha",{}),
    Scene("Vimarśa — Reflective Awareness","The capacity of consciousness to know that it appears — reflection that feels itself.",5.0,"prakasha_vimarsha",{}),
    Scene("Together They Form Life","Light alone would reveal everything but recognize nothing — together they form living awareness.",5.5,"prakasha_vimarsha",{}),
    Scene("Consciousness Is the Self","caitanyam ātmā — the possessor, the possessed, and the act of possession all appear inside consciousness.",6.0,"prakasha_vimarsha",{}),
    Scene("The Crowded Station","Hundreds of faces, sounds, announcements — then someone speaks your name.",5.5,"your_name",{}),
    Scene("The Name Finds the Center","It was physically no louder — yet it acquires a different kind of reality.",5.5,"your_name",{}),
    Scene("Attention Moves Reality","Every act of attention is a smaller version of this — a world reorganised around a sound.",5.5,"your_name",{}),
    Scene("The Gap Between Thoughts","A thought ends — before the next arises — what is that space?",5.0,"gap",{}),
    Scene("Not Empty","The gap is not empty — it is the source from which the next world will be selected.",5.5,"gap",{}),
    Scene("The Pulsation of Awareness","Perceptions come and go — what survives the gap is more fundamental than any content.",5.5,"gap",{}),
    Scene("You Are Not the Perceiver","You are not the perceiver — you are the field in which perceiving happens.",5.5,"gap",{}),
    Scene("Infinite Possibilities","The field contains infinite possible worlds — attention selects one.",5.5,"infinite_possible",{}),
    Scene("Selection Is Responsibility","To attend to something is to bring it forward — to neglect is to let it recede.",5.5,"infinite_possible",{}),
    Scene("The World You Inhabit","The world you inhabit is the one your attention has chosen — moment by moment.",5.5,"infinite_possible",{}),
    Scene("The Luminous Field","Fold upon fold — consciousness saying: this, here, now.",5.0,"closing",{}),
    Scene("Closure","The universe is hiding inside your attention — you have been looking through the wrong end of the telescope.",6.0,"closing",{}),
    Scene("Final","Something is selecting your reality before you know it — and that something is what you are.",6.5,"closing",{}),
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
    ff=req_ff(); c=O/"concat.txt"
    c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    o=O/"universe_hiding_in_attention.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o

def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3)
        pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"
    p.write_text(json.dumps({"title":"the universe is hiding inside your attention","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"palette_roles":{"gold":"attended reality","silver":"background","graphite":"the field","violet":"the gap"},"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8")
    return p

def cs(w,h):
    th=[]; tw,th2=320,int(320*h/w)
    for idx,s in enumerate(SCENES,1):
        nf=max(2,round(s.duration*FPS)); im=rf(s,int(nf*.72),nf,w,h,idx*1000+72); im.thumbnail((tw,th2)); th.append((idx,s.title,im.copy()))
    cols=4; rows=math.ceil(len(th)/cols); ch=th2+48
    sheet=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(sheet)
    font=lf(FSNB,14)
    for idx,tt,im in th:
        s=idx-1; x=(s%cols)*tw; y=(s//cols)*ch
        sheet.paste(im,(x,y)); d.text((x+8,y+th2+10),f"{idx:02d}  {tt}",font=font,fill=INK)
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
