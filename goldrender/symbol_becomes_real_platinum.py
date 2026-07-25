#!/usr/bin/env python3
"""A SYMBOL BECOMES REAL WHEN SEVERAL WORLDS COMPILE TO THE SAME FORM — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; O=ROOT/"output_symbol_becomes_real"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(248,245,239); PAPER=(242,239,232); WHITE=(252,251,248); INK=(30,32,36); SOFT_INK=(86,89,94)
GOLD=(191,154,73); PG=(232,216,174); GL=(244,224,180); SILVER=(180,186,192); CRIMSON=(158,57,66)
TEAL=(67,157,180); VIOLET=(130,104,160); PV=(206,196,216); DARK=(24,27,32); LAPIS=(56,76,124)
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
def yantra_ring(d,cx,cy,r,points,col,width=2,rot=0):
    for i in range(points):
        a=rot+i*2*math.pi/points
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
        d.ellipse((x-5,y-5,x+5,y+5),fill=(*col,190),outline=(*col,150),width=1)
def yantra_tri(d,cx,cy,r,col,rot=0,width=2):
    pts=[(cx+math.cos(rot+2*math.pi*i/3)*r,cy+math.sin(rot+2*math.pi*i/3)*r) for i in range(3)]
    d.polygon(pts,outline=(*col,200),width=width)

@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict

def v_mantra_written(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    gc(im,cx,cy,20,GL,int(100*pr),14)
    glyphs=['ॐ','ह्रीं','श्रीं','क्लीं','सौः']
    for i,g in enumerate(glyphs):
        q=clamp(pr*1.5-i*.08)
        if q<=0: continue
        x=cx+(i-2)*95; y=cy
        d.ellipse((x-28,y-28,x+28,y+28),outline=(*GOLD,int(180*q)),fill=(*PG,int(15*q)),width=2)
        ct(d,(x,y),g,lf(FS,int(h*.030)),GOLD)
    seal(im,"A MANTRA CAN BE WRITTEN","phoneme, glyph, number, geometry — one in different media")

def v_compile(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    worlds=[("MANTRA",GOLD,-170,0),("YANTRA",TEAL,0,-60),("DEITY",VIOLET,170,0),("RITUAL",CRIMSON,0,60)]
    for i,(lb,col,dx,dy) in enumerate(worlds):
        q=clamp(pr*1.3-i*.07)
        if q<=0: continue
        x=cx+dx; y=cy+dy
        d.rounded_rectangle((x-65,y-24,x+65,y+24),radius=12,outline=(*col,int(170*q)),fill=(*mix(IVORY,col,.05),int(200*q)),width=2)
        ct(d,(x,y),lb,lf(FSNB,int(h*.018)),col)
    if pr>.6:
        gc(im,cx,cy,22,GL,int(120*pr),16)
        ct(d,(cx,cy),'ॐ',lf(FS,int(h*.036)),GOLD)
    seal(im,"A SYMBOL BECOMES REAL WHEN SEVERAL WORLDS COMPILE TO THE SAME FORM","the identity survives across media")

def v_vidya_yantra(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    yantra_tri(d,cx,cy-90,140,GOLD,rot=-math.pi/2,width=3)
    yantra_tri(d,cx,cy-90,90,GOLD,rot=math.pi/2,width=2)
    for i,r in enumerate([130,100,70,40,15]):
        q=clamp(pr*1.3-i*.08)
        if q<=0: continue
        d.ellipse((cx-r,cy-90-r*.6,cx+r,cy-90+r*.6),outline=(*mix(GOLD,TEAL,i/4),int(140*q)),width=2)
    gc(im,cx,cy-90,15,GL,int(80*pr),12)
    seal(im,"THE VIDYĀ, THE FORM, AND THE YANTRA ARE ONE","not visually identical — operationally inseparable")

def v_recursive_code(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    layers=[("PHONEME",GOLD,0,0),("NUMBER",LAPIS,1,0),("GEOMETRY",TEAL,0,1),("RITUAL",CRIMSON,1,1),("DEITY",VIOLET,.5,.8)]
    for i,(lb,col,gx,gy) in enumerate(layers):
        q=clamp(pr*1.5-i*.06)
        if q<=0: continue
        x=cx+(gx-.5)*280; y=cy+(gy-.5)*180
        d.rectangle((x-50,y-22,x+50,y+22),outline=(*col,int(170*q)),fill=(*mix(IVORY,col,.06),int(200*q)),width=2)
        ct(d,(x,y),lb,lf(FSNB,int(h*.016)),col)
        if i>0:
            px,py=cx+(layers[i-1][2]-.5)*280,cy+(layers[i-1][3]-.5)*180
            d.line((px+50,py,x-50,y),fill=(*col,int(80*q)),width=2)
    seal(im,"THE SEQUENCE CROSSES MEDIA WITHOUT LOSING IDENTITY","sound → number → geometry → rite → presence")

def v_gene_form(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    levels=[("GENE",GOLD,0),("PROTEIN",TEAL,1),("NETWORK",LAPIS,2),("BEHAVIOUR",CRIMSON,3)]
    for i,(lb,col,idx) in enumerate(levels):
        q=clamp(pr*1.3-i*.07)
        if q<=0: continue
        x=cx+(idx-1.5)*200; y=cy
        d.ellipse((x-45,y-35,x+45,y+35),outline=(*col,int(170*q)),fill=(*mix(IVORY,col,.08),int(200*q)),width=2)
        ct(d,(x,y),lb,lf(FSNB,int(h*.017)),col)
        if i>0:
            px=cx+(levels[i-1][2]-1.5)*200
            d.line((px+45,cy,x-45,cy),fill=(*col,int(80*q)),width=2)
    gc(im,cx,cy,18,GL,int(80*pr),14)
    seal(im,"DIFFERENT REPRESENTATIONS — ONE CAUSAL ORGANIZATION","the living form exists through transformations among codes")

def v_compilation(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    sources=[("MANTRA",GOLD,-160,0),("YANTRA",TEAL,160,0),("RITUAL",CRIMSON,0,100),("DEITY",VIOLET,0,-100)]
    for i,(lb,col,dx,dy) in enumerate(sources):
        q=clamp(pr*1.3-i*.07)
        if q<=0: continue
        x=cx+dx; y=cy+dy
        d.ellipse((x-35,y-25,x+35,y+25),outline=(*col,int(160*q)),fill=(*mix(IVORY,col,.06),int(190*q)),width=2)
        ct(d,(x,y),lb,lf(FSNB,int(h*.015)),col)
        d.line((cx,cy,int(x),int(y)),fill=(*col,int(70*q)),width=2)
    gc(im,cx,cy,25,GL,int(140*pr),18)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=(*WHITE,int(220*pr)))
    seal(im,"WHEN DO DIFFERENT REPRESENTATIONS COUNT AS ONE PROCESS?","the question belongs to both theology and systems science")

def v_closing(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.5,h*.42; pr=ease(u)
    for i,(r,c) in enumerate([(200,GOLD),(150,TEAL),(100,VIOLET),(50,CRIMSON)]): rr=r*pr; d.ellipse((cx-rr,cy-60-rr*.5,cx+rr,cy-60+rr*.5),outline=(*c,int(120-20*(r//50))),width=2)
    gc(im,cx,cy-60,30,GL,int(140*pr),20); d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=(*WHITE,int(220*pr)),outline=(*GOLD,int(200*pr)),width=2)
    for i in range(16): a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*185*pr; y=cy-60+math.sin(a)*125*pr; d.ellipse((x-3,y-3,x+3,y+3),fill=(*mix(GOLD,TEAL,i/15),int(120*pr)))
    seal(im,"A SYMBOL BECOMES REAL WHEN SEVERAL WORLDS COMPILE TO THE SAME FORM","the vidyā, the goddess, and the yantra are one — not visually identical, operationally inseparable")

VISUALS={"mantra_written":v_mantra_written,"compile":v_compile,"vidya_yantra":v_vidya_yantra,"recursive_code":v_recursive_code,"gene_form":v_gene_form,"compilation":v_compilation,"closing":v_closing}
SCENES=[
    Scene("Written","A mantra can be written — glyph on page, sound encoded as shape.",5.5,"mantra_written",{}),
    Scene("Spoken","Spoken — vibration moving through air and ear.",5.0,"mantra_written",{}),
    Scene("Visualized","Visualized as geometry — the yantra as sight.",5.0,"mantra_written",{}),
    Scene("Installed","Installed in a body — nyāsa as touch.",5.0,"mantra_written",{}),
    Scene("Emobodied","Emobodied as a deity — presence as relation.",5.0,"mantra_written",{}),
    Scene("Performed","Performed as a ritual — time as medium.",5.0,"mantra_written",{}),
    Scene("One Question","If each version were merely a translation, one could ask which was the original.",5.5,"compile",{}),
    Scene("More Radical","The Śrīvidyā Ratna Sūtras offers a more radical answer: the vidyā, the goddess, and the yantra are one.",6.0,"compile",{}),
    Scene("Compilation","A symbol becomes real when several worlds compile to the same form.",5.5,"compile",{}),
    Scene("Gauḍapāda","Attributed to Gauḍapāda — organizing Tripurasundarī through mantras, yantras, gates, lineages, codes.",5.5,"vidya_yantra",{}),
    Scene("Sound to Number","Consonants represent numbers — vowels function as zero.",5.5,"recursive_code",{}),
    Scene("Number to Geometry","Number determines geometric arrangement — geometry determines ritual relation.",5.5,"recursive_code",{}),
    Scene("Crossing Media","The sequence crosses media without losing identity — sound, number, geometry, rite.",5.5,"recursive_code",{}),
    Scene("Not Digital","This is not digital Tantra — the codes belong to Sanskrit ritual technology.",5.5,"recursive_code",{}),
    Scene("Theological Identity","The identity of vidyā, form, and yantra is theological — yet raises a question systems science also struggles with.",6.0,"compile",{}),
    Scene("One Process","When do different representations count as implementations of one process?",5.5,"compilation",{}),
    Scene("Gene to Trait","A gene sequence, protein shape, regulatory network, and organismal trait preserve one causal organization across levels.",6.0,"gene_form",{}),
    Scene("Recursive Development","Genes influence proteins — proteins alter signalling — signalling reorganizes the tissue — the tissue feeds back on gene expression.",6.0,"gene_form",{}),
    Scene("Genotype Not Pipeline","Genotype-phenotype is not a pipeline — real development is recursive.",5.5,"gene_form",{}),
    Scene("Compilation","Like a symbol compiled into several media — the living form exists through transformations among codes.",6.0,"compilation",{}),
    Scene("Generative Identity","The identity of a biological process may also be operationally inseparable from its many representations.",5.5,"gene_form",{}),
    Scene("Closing","A symbol becomes real when several worlds compile to the same form — not visually identical, operationally inseparable.",6.0,"closing",{}),
    Scene("Final","The vidyā, the form, and the yantra are one — the identity survives across media because the identity is the transformation.",6.5,"closing",{}),
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
    o=O/"symbol_becomes_real.mp4"
    subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return o
def export_tl():
    cur=0.0; pl=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3); pl.append(r); cur+=s.duration
    p=O/"narration_timeline.json"; p.write_text(json.dumps({"title":"a symbol becomes real when several worlds compile to the same form","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"scenes":pl},indent=2,ensure_ascii=False),encoding="utf-8"); return p
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
