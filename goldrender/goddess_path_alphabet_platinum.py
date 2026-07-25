#!/usr/bin/env python3
"""THE GODDESS IS NOT THE ALPHABET BUT THE PATH THROUGH IT — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_goddess_path"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66); TEAL=(67,157,180)
VIOLET=(130,104,160); PV=(206,196,216); DARK=(24,27,32); LAPIS=(56,76,124); PTE=(196,226,231)
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

GLYPHS=list('अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह')

def v_alphabet_field(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gc(im,cx,cy,20,GL,int(80*pr),14)
    for i,g in enumerate(GLYPHS[:24]):
        a=i*2*math.pi/24; r=100+40*pr
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        q=clamp(pr*1.5-i*.02)
        if q<=0: continue
        ct(d,(x,y),g,lf(DEVA,int(h*.019)),mix(GOLD,TEAL,i/23))
    seal(im,"AN ALPHABET LOOKS COMPLETE WHEN EVERY LETTER IS PRESENT","a mantra proves that completeness is not enough — the same phonemes can be arranged into warning, prayer, or silence")

def v_two_paths(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    # Two different paths through same nodes
    nodes=[]
    for i in range(8):
        a=i*2*math.pi/8; r=140; x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        nodes.append((x,y,i))
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*GOLD,int(170*pr)),outline=(*GOLD,150),width=1)
    # Path 1 (standard order)
    path1=[0,1,2,3,4,5,6,7]
    for pi in range(len(path1)-1):
        q=clamp(pr*2-pi*.12)
        if q<=0: continue
        x1,y1,_=nodes[path1[pi]]; x2,y2,_=nodes[path1[pi+1]]
        d.line((x1,y1,x2,y2),fill=(*TEAL,int(100*q)),width=2)
    # Path 2 (Mālinī order — non-standard)
    path2=[0,3,6,1,4,7,2,5]
    for pi in range(len(path2)-1):
        q=clamp(pr*2.5-pi*.12)
        if q<=0: continue
        x1,y1,_=nodes[path2[pi]]; x2,y2,_=nodes[path2[pi+1]]
        if pr>.3: d.line((x1,y1,x2,y2),fill=(*CRIMSON,int(140*q)),width=3)
    gc(im,cx,cy,15,GL,int(80*pr),12)
    seal(im,"MĀLINĪ USES THE SAME PHONEMES — A DIFFERENT ROUTE","the goddess is not the alphabet — she is the path through it")

def v_garland(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,g in enumerate(GLYPHS[:16]):
        a=-math.pi/2+i*2*math.pi/16; r=lerp(60,170,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        q=clamp(pr*1.5-i*.03)
        if q<=0: continue
        col=mix(CRIMSON,GOLD,i/15)
        d.ellipse((x-14,y-14,x+14,y+14),outline=(*col,int(160*q)),fill=(*mix(IVORY,col,.08),int(120*q)),width=2)
        ct(d,(x,y),g,lf(DEVA,int(h*.020)),col)
    gc(im,cx,cy,20,GL,int(100*pr),14)
    ct(d,(cx,cy),"मालिनी",lf(DEVA,int(h*.030)),CRIMSON)
    seal(im,"THE GODDESS IS A GARLAND OF PHONEMES","mālinī — a non-standard sequence through the same field of possible sound")

def v_matraka(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    d.ellipse((cx-100,cy-80,cx+100,cy+80),outline=(*GOLD,int(170*pr)),width=3)
    for i in range(3):
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        y=cy-40+i*40
        d.ellipse((cx-70,y-14,cx-10,y+14),fill=(*PG,int(100*q)),outline=(*GOLD,int(150*q)),width=1)
    ct(d,(cx-40,cy-40),"MĀTṚKĀ",lf(FSNB,int(h*.020)),GOLD)
    ct(d,(cx+40,cy),"क",lf(DEVA,int(h*.035)),TEAL)
    ct(d,(cx+40,cy+10),"ख",lf(DEVA,int(h*.035)),TEAL)
    seal(im,"THE PHONEMIC MATRIX — THE LITTLE MOTHERS","sounds arranged by place and manner — systematic enough to map embodied speech")

def v_assembly_paths(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    nodes=[]
    for i in range(10):
        x=lerp(200,1080,i/9); y=cy+math.sin(i*1.2)*40
        nodes.append((x,y,i))
        q=clamp(pr*1.5-i*.05)
        if q<=0: continue
        d.ellipse((x-5,y-5,x+5,y+5),fill=(*GOLD,int(170*q)))
    for pi in range(len(nodes)-1):
        q=clamp(pr*2-pi*.08)
        if q<=0: continue
        x1,y1,_=nodes[pi]; x2,y2,_=nodes[pi+1]
        d.line((x1,y1,x2,y2),fill=(*TEAL,int(120*q)),width=2)
    alt_path=[0,2,4,6,8,7,5,3,1,9]
    for pi in range(len(alt_path)-1):
        q=clamp(pr*2.5-pi*.08)
        if q<=0: continue
        x1,y1,_=nodes[alt_path[pi]]; x2,y2,_=nodes[alt_path[pi+1]]
        if pr>.2: d.line((x1,y1,x2,y2),fill=(*CRIMSON,int(140*q)),width=3)
    seal(im,"IDENTICAL ELEMENTS — DIFFERENT ASSEMBLY PATHS","the physical inventory does not determine the semantic outcome — the path selects what becomes possible")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,TEAL),(150,GOLD),(100,CRIMSON),(50,VIOLET)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i,g in enumerate(GLYPHS[:12]):
        a=i*2*math.pi/12+t*.03; r=175*pr; x=cx+math.cos(a)*r; y=cy-60+math.sin(a)*r*.6
        ct(d,(x,y),g,lf(DEVA,int(h*.015)),mix(GOLD,TEAL,i/11))
    seal(im,"THE GODDESS IS NOT THE ALPHABET","she is the path through it — the same field, traversed differently")

VISUALS={"alphabet_field":v_alphabet_field,"two_paths":v_two_paths,"garland":v_garland,"matraka":v_matraka,"assembly_paths":v_assembly_paths,"closing":v_closing}
SCENES=[
    Scene("Alphabet","An alphabet looks complete when every letter is present.",5.0,"alphabet_field",{}),
    Scene("Not Enough","A mantra proves that completeness is not enough — the same phonemes can be arranged into warning, prayer, or silence.",6.0,"alphabet_field",{}),
    Scene("Path","Nothing new needs to be added to the inventory — only the path changes.",5.5,"two_paths",{}),
    Scene("Mālinīvijayottara","The Mālinīvijayottara Tantra places this fact at the centre of a cosmology of sound.",5.5,"alphabet_field",{}),
    Scene("Non-Standard Garland","Mālinī is a non-standard garland of phonemes — the same field traversed through another sequence.",5.5,"garland",{}),
    Scene("Ordinary Order","The ordinary Sanskrit alphabet is systematic — vowels precede consonants, stops move from throat to lips.",5.5,"matraka",{}),
    Scene("Mātṛkā","Tantric traditions call the phonemic matrix mātṛkā — the little mothers from which words and mantras arise.",5.5,"matraka",{}),
    Scene("Deliberately Different","Mālinī uses the same phonemic elements but refuses the ordinary route — a ritual and metaphysical system.",5.5,"garland",{}),
    Scene("Not Fifty-First","It does not add a fifty-first substance to language — it reorganizes access to the existing field.",5.5,"two_paths",{}),
    Scene("Abhinavagupta","Abhinavagupta treats the Mālinīvijayottara as a central authority for Trika practice.",5.5,"alphabet_field",{}),
    Scene("Powers and Levels","Its phonemic order supports mantra, initiation, nyāsa, visualization, and the mapping of letters onto powers.",6.0,"garland",{}),
    Scene("Assembly Paths","Identical elements — different assembly paths.",5.5,"assembly_paths",{}),
    Scene("Physical vs Semantic","The physical inventory does not determine the semantic outcome — the path selects what becomes possible.",5.5,"assembly_paths",{}),
    Scene("Closing","The goddess is not the alphabet — she is the path through it.",6.0,"closing",{}),
    Scene("Final","The same field of possible sound — Mālinī is the route that reveals the goddess.",6.5,"closing",{}),
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
    o=O/"goddess_path_alphabet.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"the goddess is not the alphabet but the path through it","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
