#!/usr/bin/env python3
"""PRATYABHIJÑĀ — REMEMBER ENLIGHTENMENT — Essay 3
Silver=mirror/reflection, Gold=consciousness/recognition, Cyan=world-appearance
"""
from __future__ import annotations; import argparse,json,math,shutil,subprocess
from dataclasses import dataclass; from pathlib import Path; import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/"output_pratyabhijna"; FR=O/"frames"; SD=O/"scenes"
W,H,FP=1280,720,10; WH=(248,247,243); IK=(30,32,36); ST=(86,89,94)
GD=(191,154,73); PG=(232,216,174); SV=(180,186,192); PS=(224,227,229); CY=(67,157,180); GN=(72,135,101); CR=(158,57,66)
F1="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; F1B="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F2="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; F2B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def cl(x,l=0.0,h=1.0): return max(l,min(h,x))
def le(a,b,t): return a+(b-a)*cl(t)
def mi(a,b,t): t=cl(t); return tuple(int(le(x,y,t)) for x,y in zip(a,b))
def es(t): t=cl(t); return 0.5-0.5*math.cos(math.pi*t)
def lf(p,s):
    for c in (p,F1,F2):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rg(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,sd):
    r=np.random.default_rng(sd); a=np.empty((h,w,3),dtype=np.float32); a[:]=WH
    a+=r.normal(0,0.8,(h,w,1))
    return Image.fromarray(np.clip(a,0,255).astype(np.uint8),"RGB").convert("RGBA")
def se(im,t,s="",c=IK):
    d=ImageDraw.Draw(im); tw,th=im.size
    d.text((tw/2,th*0.875),t,font=lf(F1B,max(22,int(th*0.042))),fill=c,anchor="mm")
    if s: d.text((tw/2,th*0.925),s,font=lf(F2,max(13,int(th*0.020))),fill=ST,anchor="mm")
def bo(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*IK,50),width=2)
def gc(im,cx,cy,r,col,al=180,bl=18):
    lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(*col,al))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(bl)))
    c2=rg(im.size)
    ImageDraw.Draw(c2).ellipse((cx-r*.45,cy-r*.45,cx+r*.45,cy+r*.45),fill=(*mi(col,WH,.3),min(255,al+40)))
    im.alpha_composite(c2)
def gl(im,pts,col,wd=4,glw=14,al=225):
    if len(pts)<2: return; lay=rg(im.size); d=ImageDraw.Draw(lay)
    d.line(pts,fill=(*col,al),width=wd,joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glw))); im.alpha_composite(lay)

def v_recognition(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    d.text((w*.50,h*.38),"pratyabhijñā",font=lf(F1B,int(h*.035)),fill=GD,anchor="mm")
    d.text((w*.50,h*.50),"recognition",font=lf(F2B,int(h*.025)),fill=ST,anchor="mm")
    if pr>.5: d.text((w*.50,h*.65),"seeing what you have always been",font=lf(F2,int(h*.017)),fill=ST,anchor="mm")
    se(im,"ENLIGHTENMENT IS SOMETHING YOU REMEMBER","not something you acquire",GD)

def v_mirror(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    d.rounded_rectangle((w*.38,h*.26,w*.62,h*.54),radius=12,outline=(*SV,int(200*pr)),width=3)
    gc(im,w*.50,h*.40,20,GD,200,14)
    gc(im,w*.50,h*.40,12,WH,180,8)
    if pr>.4: d.text((w*.50,h*.64),"a mirror that generates its own images",font=lf(F2B,int(h*.016)),fill=GD,anchor="mm")
    se(im,"THE DOCTRINE OF REFLECTION","the face it shows comes from its own depth",SV)

def v_sky(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(20):
        a=i*2*math.pi/20; r=le(10,160,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        col1=mi(SV,GD,i/20); d.line(((cx,cy),(int(x),int(y))),fill=(*col1,int(120*pr)),width=1)
    gc(im,cx,cy,22,GD,200,14)
    d.text((cx,cy+55),"all things are reflections in the sky of consciousness",font=lf(F2B,int(h*.014)),fill=SV,anchor="mm")
    se(im,"A REFLECTION CANNOT EXIST APART FROM THE MIRROR","the world manifests mingled with other reflections",SV)

def v_saliva(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    d.ellipse((w*.48,h*.35,w*.52,h*.50),fill=(*PS,200),outline=(*SV,180),width=2)
    d.arc((w*.42,h*.55,w*.58,h*.65),0,180,fill=(*SV,150),width=2)
    d.text((w*.50,h*.62),"taste borrowed from what touches it",font=lf(F2B,int(h*.014)),fill=ST,anchor="mm")
    se(im,"SALIVA CARRIES NO INDEPENDENT TASTE","consciousness lends reality to everything it touches",SV)

def v_aha(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    d.text((w*.50,h*.34),"AHAṀ",font=lf(F1B,int(h*.050)),fill=GD,anchor="mm")
    d.text((w*.50,h*.48),"= I",font=lf(F1B,int(h*.030)),fill=SV,anchor="mm")
    if pr>.6: d.text((w*.50,h*.62),"every perception is one syllable conjugating into the world's grammar",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE ALPHABET OF CONSCIOUSNESS","the letters themselves are acts of recognition",GD)

def v_tattva_reflection(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    for i in range(5):
        q=cl(pr*1.5-i*.1)
        if q<=0: continue
        y=200+i*50
        d.line((w*.30,y,w*.70,y),fill=(*mi(SV,GD,i/5),int(160*q)),width=3)
    d.text((w*.50,h*.70),"each tattva — a different face of the same mirror",font=lf(F2B,int(h*.015)),fill=GD,anchor="mm")
    se(im,"FROM EARTH TO CONSCIOUSNESS","to see a stone as a reflection is to see through the stone",GD)

def v_weight(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    # A stone — heavy, real
    d.ellipse((w*.45,h*.38-20,w*.55,h*.38+20),fill=(*PS,200),outline=(*ST,180),width=3)
    gc(im,w*.50,h*.38,25,GD,150,14)
    d.text((w*.50,h*.58),"the weight of a stone is real",font=lf(F2B,int(h*.016)),fill=ST,anchor="mm")
    d.text((w*.50,h*.68),"so is the light that reveals it",font=lf(F2,int(h*.014)),fill=GD,anchor="mm")
    se(im,"MATTER IS A REAL MANIFESTATION","the reflection grants the world ontological weight",GD)

def v_wonder(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(30):
        a=i*2*math.pi/30; r=le(5,170,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*mi(GD,SV,i/30),int(100+100*pr)))
    gc(im,cx,cy,20,GD,200,12)
    d.text((cx,cy+55),"camatkāra",font=lf(F1B,int(h*.020)),fill=GD,anchor="mm")
    d.text((cx,cy+72),"wonder — astonishment at the world's incandescence",font=lf(F2,int(h*.015)),fill=ST,anchor="mm")
    se(im,"THE WORLD IS A LIVING EXPRESSION","every stone, every breath, every seam of light",GD)

def v_cause(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for r in [40,80,120,160]:
        d.ellipse((cx-r,cy-r*.5,cx+r,cy+r*.5),outline=(*SV,int(80*pr)),width=2)
    gc(im,cx,cy,20,GD,200,12)
    d.text((cx,cy+55),"the cause of reflection is freedom",font=lf(F2B,int(h*.014)),fill=GD,anchor="mm")
    d.text((cx,cy+70),"not compulsion — the Lord's own power",font=lf(F2,int(h*.013)),fill=ST,anchor="mm")
    se(im,"FREE AND COMPLETELY FULL IS THIS LORD","there is nothing that exists that he does not make manifest",GD)

def v_sky_consciousness(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    d.rounded_rectangle((w*.30,h*.22,w*.70,h*.58),radius=10,outline=(*CY,int(180*pr)),width=2)
    # Clouds passing
    for i in range(6):
        x=le(w*.25,w*.75,((pr+i*.15)%1))
        d.ellipse((x-30,cy-15,x+30,cy+15),fill=(*PS,int(120)))
    gc(im,cx,cy,18,GD,180,10)
    d.text((cx,h*.68),"the sky has never been touched by a single cloud",font=lf(F2B,int(h*.015)),fill=GD,anchor="mm")
    se(im,"CONSCIOUSNESS IS THE SKY","thoughts and feelings are clouds",CY)

def v_mirror_no_edge(im,u,t,p):
    d=ImageDraw.Draw(im); w,h=im.size; pr=es(u)
    cx,cy=w*.50,h*.38
    for i in range(12):
        a=i*2*math.pi/12; r=le(10,180,pr)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.5
        d.line(((cx,cy),(int(x),int(y))),fill=(*mi(SV,GD,i/12),int(120*pr)),width=2)
    gc(im,cx,cy,25,GD,200,14)
    if pr>.5: d.text((cx,cy+55),"the mirror has no edge",font=lf(F1B,int(h*.020)),fill=GD,anchor="mm")
    d.text((cx,cy+72),"the seeking was the mirror looking at itself",font=lf(F2,int(h*.014)),fill=ST,anchor="mm")
    se(im,"YOU WERE NEVER SEPARATE","the reflection has no independent life",GD)

VS={"recognition":v_recognition,"mirror":v_mirror,"sky":v_sky,"saliva":v_saliva,"aha":v_aha,
    "tattva":v_tattva_reflection,"weight":v_weight,"wonder":v_wonder,"cause":v_cause,
    "sky_con":v_sky_consciousness,"edge":v_mirror_no_edge}
@dataclass
class Sc: title:str; dur:float; vis:str
SCENES=[
    Sc("Remember enlightenment",6.0,"recognition"),Sc("Pratyabhijna — seeing what you always were",5.5,"recognition"),
    Sc("A mirror that generates its own images",7.0,"mirror"),Sc("The face comes from its own depth",6.5,"mirror"),
    Sc("All is reflection",7.0,"sky"),Sc("Cannot exist apart from the mirror",6.5,"sky"),
    Sc("Borrowed reality",6.0,"saliva"),Sc("Consciousness lends reality",5.5,"saliva"),
    Sc("AHAṀ",6.0,"aha"),Sc("Every perception is one syllable",5.5,"aha"),
    Sc("Each tattva — one face of the mirror",7.0,"tattva"),Sc("Seeing through the stone",6.5,"tattva"),
    Sc("The weight of a stone is real",6.0,"weight"),Sc("So is the light that reveals it",5.5,"weight"),
    Sc("Camatkara",7.0,"wonder"),Sc("Astonishment at the world's incandescence",6.5,"wonder"),
    Sc("The cause of reflection is freedom",7.0,"cause"),Sc("Not compulsion — the Lord's own power",6.5,"cause"),
    Sc("Consciousness is the sky",7.0,"sky_con"),Sc("Clouds pass — the sky remains untouched",6.5,"sky_con"),
    Sc("The mirror has no edge",7.0,"edge"),Sc("The seeking was the mirror looking at itself",6.5,"edge"),

    Sc("The reflection cannot exist apart from the medium",7.0,"sky"),
    Sc("It manifests mingled with other reflections",6.5,"sky"),
    Sc("Like a face in a mirror — like taste in saliva",7.0,"saliva"),
    Sc("Like an echo in the sky",6.5,"saliva"),
    Sc("The cause of reflection is the Supreme Lord's power",7.0,"cause"),
    Sc("Otherwise called freedom",6.5,"cause"),
    Sc("Free and completely full is this Lord",7.0,"cause"),
    Sc("There is nothing that exists He does not make manifest",7.0,"cause"),
    Sc("The Awakened One should apply the fifty kinds",7.0,"tattva"),
    Sc("Of reflective awareness free of thought constructs",6.5,"tattva"),
    Sc("Beholding the Earth principle reflected within",7.0,"tattva"),
    Sc("It assumes Bhairava's nature",6.5,"tattva"),
    Sc("The same procedure applied to all principles",7.0,"tattva"),
    Sc("From water up to the supreme principle",6.5,"tattva"),
    Sc("The fifty kinds — the Divine Means",7.0,"tattva"),
    Sc("The weight of a stone is real",6.0,"weight"),
    Sc("So is the light that reveals it",5.5,"weight"),
    Sc("The two are the same reality at different densities",7.0,"weight"),
    Sc("The world is a living expression of the divine",7.0,"wonder"),
    Sc("Every stone, every breath, every seam of light",6.5,"wonder"),
    Sc("The ground does — quieter, stiller, more itself",7.0,"wonder"),
    Sc("The Power that Sustains Everything",7.0,"cause"),
    Sc("Is the ground of all manifestation",6.5,"cause"),
    Sc("Everything appears within Siva like a reflection",7.0,"sky"),
    Sc("Or like an image in a dream",6.5,"sky"),
    Sc("The relationship is that of consciousness to its own self-manifestation",8.0,"mirror"),
    Sc("By His freedom, Siva can manifest what does not exist",8.0,"mirror"),
    Sc("The sakti that appears as the ground is one with Siva",8.0,"mirror"),
    Sc("The letter A stands for Anuttara",7.0,"aha"),
    Sc("Its power is the unfolding perception of all things",6.5,"aha"),
    Sc("In their fundamental nature as pure self-awareness",7.0,"aha"),
    Sc("AHAṀ of Bhairava — the supreme perceiver",6.5,"aha"),
    Sc("It encompasses the energies from A to H",7.0,"aha"),
    Sc("The liberated soul's only purpose",7.0,"recognition"),
    Sc("Is to elevate others",6.5,"recognition"),
    Sc("The yogi free of thought constructs",7.0,"recognition"),
    Sc("Beholding Siva reflected in the uncreated mirror",7.0,"recognition"),
    Sc("Becomes by himself spontaneously Bhairava",6.5,"recognition"),
    Sc("From this point — means and goal persist only subtly",7.0,"recognition"),
    Sc("The distinction between knower and knowing blurs",7.0,"recognition"),
    Sc("The uncreated mirror is the act of reflection itself",7.0,"edge"),
    Sc("Without beginning, without end",6.5,"edge"),
    Sc("The mirror shows that seeing and being are the same act",7.0,"edge"),
    Sc("All is reflection in the Sky of Consciousness",7.0,"sky_con"),
    Sc("Consciousness is the sky — thoughts are clouds",6.5,"sky_con"),
    Sc("The sky has never been touched by a single one",7.0,"sky_con"),
    Sc("When you see that the sky is the space that allows them",7.0,"sky_con"),
    Sc("You have understood",5.5,"sky_con"),


    Sc("The mirror that generates its own images",7.0,"mirror"),
    Sc("The face comes from its own depth",6.5,"mirror"),
    Sc("Cannot exist apart from the mirror",7.0,"sky"),
    Sc("All things are reflections",6.5,"sky"),
    Sc("A reflection cannot manifest separately",7.0,"sky"),
    Sc("Consciousness lends reality",6.5,"saliva"),
    Sc("The world tastes real only because consciousness lends it reality",7.0,"saliva"),
    Sc("AHAṀ — one syllable conjugating",6.5,"aha"),
    Sc("The letters are acts of recognition",7.0,"aha"),
    Sc("Each tattva — a different face",6.5,"tattva"),
    Sc("To see a stone as a reflection of awareness",7.0,"tattva"),

    Sc("Seeing what you have always been",6.0,"recognition"),
    Sc("The mirror — a face that comes from its own depth",6.5,"mirror"),
    Sc("The hinge between glass and consciousness",6.5,"mirror"),
    Sc("Saliva carries no independent taste",6.5,"saliva"),
    Sc("The world tastes real because consciousness lends it reality",7.0,"saliva"),
    Sc("Reflections carry weight, presence, texture",7.0,"weight"),
    Sc("Their substance is the mirror that holds them",6.5,"weight"),
    Sc("Inseparable as heat from a coal",6.5,"weight"),
    Sc("The Buddhist idealists named them unreal",7.0,"weight"),
    Sc("The Tantric eye finds them real as the mirror's own content",7.5,"weight"),
    Sc("A fulfilled person does not reach",6.5,"recognition"),
    Sc("Their hands are open — holding nothing costs nothing",7.0,"recognition"),
    Sc("He who enters repeatedly into this state of penetration",7.5,"recognition"),
    Sc("Attains Bhairava's state — liberation in this life",7.0,"recognition"),
    Sc("The liberated soul's only purpose is to elevate others",8.0,"recognition"),
    Sc("Each tattva — a different face of the same mirror",7.0,"tattva"),
    Sc("To see through the stone — and the stone remains whole",7.5,"tattva"),
    Sc("Perhaps more whole than before",6.5,"tattva"),
]
def rf(sc,fi,fc,w,h,sd):
    u=fi/max(1,fc-1); t=u*sc.dur; im=bg(w,h,sd); VS[sc.vis](im,u,t,{}); bo(im); return im.convert("RGB")
def ff():
    e=shutil.which("ffmpeg")
    if not e: raise RuntimeError("ffmpeg required"); return e
def en(si,fps):
    e=ff(); fd=FR/f"sc_{si:03d}"; op=SD/f"sc_{si:03d}.mp4"
    subprocess.run([e,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(op)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return op
def rs(si,sc,fps,w,h,pv):
    fd=FR/f"sc_{si:03d}"; fd.mkdir(parents=True,exist_ok=True); SD.mkdir(parents=True,exist_ok=True)
    fc=max(2,round(sc.dur*fps))
    if pv:
        for oi,fi in enumerate([0,int(fc*.35),int(fc*.72),fc-1]): rf(sc,fi,fc,w,h,si*1000+fi).save(fd/f"pv_{oi:02d}.jpg",quality=95); return fd
    for fi in range(fc): p=fd/f"{fi:05d}.jpg"
    if not p.exists(): rf(sc,fi,fc,w,h,si*1000+fi).save(p,quality=95)
    return en(si,fps)
def ct(pths):
    e=ff(); cf=O/"concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in pths),encoding="utf-8"); op=O/"pratyabhijna.mp4"
    subprocess.run([e,"-y","-f","concat","-safe","0","-i",str(cf),"-c","copy","-movflags","+faststart",str(op)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return op
def tl():
    c=0.0; pl=[]
    for i,sc in enumerate(SCENES,1):
        pl.append({"id":f"sc_{i:03d}","title":sc.title,"dur":sc.dur,"start":round(c,3),"end":round(c+sc.dur,3)}); c+=sc.dur
    (O/"timeline.json").write_text(json.dumps({"runtime":round(c,3),"scenes":pl},indent=2),encoding="utf-8")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=FP); p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true"); a=p.parse_args()
    for d in (O,FR,SD): d.mkdir(parents=True,exist_ok=True); tl()
    if a.scene: s=SCENES[a.scene-1]; print(rs(a.scene,s,a.fps,a.width,a.height,a.preview)); return
    r=[]
    for i,sc in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {sc.title} ({sc.dur:.1f}s)"); o=rs(i,sc,a.fps,a.width,a.height,a.preview)
        if not a.preview: r.append(o)
    if not a.preview: print(f"Final: {ct(r)}")
if __name__=="__main__": main()
