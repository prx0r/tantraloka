#!/usr/bin/env python3
"""PLATINUM PACK -- The Matter of Wonder"""
from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_matter_wonder")
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
W, H, FPS = 1280, 720, 10

IVORY=(249,247,241); PAPER=(242,239,231); INK=(31,36,42); SOFT_INK=(85,91,97)
SILVER=(180,187,191); PALE_SILVER=(224,228,228); WHITE=(255,254,250)
GOLD=(193,155,72); PALE_GOLD=(235,218,172); CYAN=(55,157,178); PALE_CYAN=(194,227,233)
CRIMSON=(164,57,69); GREEN=(68,139,99); PALE_GREEN=(196,225,206)
VIOLET=(107,82,151); PALE_VIOLET=(218,208,235)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold")
FNS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FNSB=FNS.replace("Sans","Sans-Bold")

def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def pulse(t,s=1.0,p=0.0): return 0.5+0.5*math.sin(math.tau*(s*t+p))
def font(p,s):
    for c in (p,FS,FNS):
        try: return ImageFont.truetype(c,s)
        except: pass
    return ImageFont.load_default()
def layer(s): return Image.new("RGBA",s,(0,0,0,0))
def scientific_field(w,h,seed):
    r=np.random.default_rng(seed)
    b=np.empty((h,w,3),dtype=np.float32); b[:]=IVORY
    b+=r.normal(0,0.95,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
    h2=np.exp(-(((xx-w*0.52)/(w*0.36))**2+((yy-h*0.39)/(h*0.30))**2)*2.1)
    b[...,0]+=h2*1.5;b[...,1]+=h2*4.0;b[...,2]+=h2*5.5
    return Image.fromarray(np.clip(b,0,255).astype(np.uint8),"RGB").convert("RGBA")
def centered(d,xy,t,f,fill=INK): d.text(xy,t,font=f,fill=fill,anchor="mm")
def border(im):
    w2,h2=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w2-26,h2-26),radius=18,outline=(*INK,48),width=2)
    for x,y in ((52,52),(w2-52,52),(52,h2-52),(w2-52,h2-52)):
        d.line((x-9,y,x+9,y),fill=(*CYAN,80),width=1)
        d.line((x,y-9,x,y+9),fill=(*CYAN,80),width=1)
def seal(im,t,s="",c=INK):
    w2,h2=im.size; d=ImageDraw.Draw(im)
    tf=font(FSB,max(22,int(h2*0.040))); sf=font(FNS,max(13,int(h2*0.019)))
    centered(d,(w2/2,h2*0.875),t,tf,c)
    if s: centered(d,(w2/2,h2*0.923),s,sf,SOFT_INK)
def glow_circle(im,x,y,r,c,a=170,b2=16):
    gl=layer(im.size)
    ImageDraw.Draw(gl).ellipse((x-r,y-r,x+r,y+r),fill=(*c,int(a)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(b2)))
    cl=layer(im.size)
    ImageDraw.Draw(cl).ellipse((x-r*.38,y-r*.38,x+r*.38,y+r*.38),fill=(*mix(c,WHITE,.35),min(255,int(a)+55)))
    im.alpha_composite(cl)
def glow_line(im,pts,c,w4=4,a=210,b2=12):
    if len(pts)<2: return
    gl=layer(im.size)
    ImageDraw.Draw(gl).line(pts,fill=(*c,int(a)),width=w4*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(b2)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(c,WHITE,.08),min(255,int(a)+25)),width=w4,joint="curve")
    im.alpha_composite(fg)


def v_panentheism_vs_theis(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"Panentheism vs Theism","Abhinavagupta panentheism")

def v_the_world_as_real(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"The World as Real","Abhinavagupta panentheism")

def v_reflection_not_illus(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"Reflection Not Illusion","Abhinavagupta panentheism")

def v_camatkara_wonder(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"Camatkara Wonder","Abhinavagupta panentheism")

def v_consciousness_and_ma(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"Consciousness and Matter","Abhinavagupta panentheism")

def v_the_ecology_of_wonde(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"The Ecology of Wonder","Abhinavagupta panentheism")

def v_the_body_of_the_abso(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"The Body of the Absolute","Abhinavagupta panentheism")

def v_the_joy_of_being(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*0.50,h*0.42; r=ease(u)
    for j in range(int(10*r)):
        a=j*math.tau/10+t*0.2; rr=25+20*math.sin(t*0.3+j)
        x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*0.5
        d.line((cx,cy,x,y),fill=(*GOLD,int(60*r)),width=2)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*PALE_GOLD,int(150*r)),outline=(*GOLD,int(120*r)),width=2)
    glow_circle(im,cx,cy,15,GOLD,int(150*r),12)
    seal(im,"The Joy of Being","Abhinavagupta panentheism")

VISUALS = {
    "panentheism_vs_theis": v_panentheism_vs_theis,
    "the_world_as_real": v_the_world_as_real,
    "reflection_not_illus": v_reflection_not_illus,
    "camatkara_wonder": v_camatkara_wonder,
    "consciousness_and_ma": v_consciousness_and_ma,
    "the_ecology_of_wonde": v_the_ecology_of_wonde,
    "the_body_of_the_abso": v_the_body_of_the_abso,
    "the_joy_of_being": v_the_joy_of_being,
}

@dataclass
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

SCENES = [
    Scene("Panentheism vs Theism", "Abhinavagupta panentheism", 7.0, "panentheism_vs_theis", {}),
    Scene("The World as Real", "Abhinavagupta panentheism", 7.0, "the_world_as_real", {}),
    Scene("Reflection Not Illusion", "Abhinavagupta panentheism", 7.0, "reflection_not_illus", {}),
    Scene("Camatkara Wonder", "Abhinavagupta panentheism", 7.0, "camatkara_wonder", {}),
    Scene("Consciousness and Matter", "Abhinavagupta panentheism", 7.0, "consciousness_and_ma", {}),
    Scene("The Ecology of Wonder", "Abhinavagupta panentheism", 7.0, "the_ecology_of_wonde", {}),
    Scene("The Body of the Absolute", "Abhinavagupta panentheism", 7.0, "the_body_of_the_abso", {}),
    Scene("The Joy of Being", "Abhinavagupta panentheism", 7.0, "the_joy_of_being", {}),
]

def rf(scene,fi,fc,w2,h2,seed):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=scientific_field(w2,h2,seed)
    VISUALS[scene.visual](im,u,t,scene.params); border(im)
    return im.convert("RGB")
def _ff():
    ff=shutil.which("ffmpeg")
    if not ff: raise RuntimeError("ffmpeg required")
    return ff
def es(idx,fps):
    o=SCENES_DIR/f"scene_{idx:03d}.mp4"; d=FRAMES/f"scene_{idx:03d}"
    subprocess.run([_ff(),"-y","-framerate",str(fps),"-i",str(d/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def rs(idx,s,fps,w2,h2,prev):
    d=FRAMES/f"scene_{idx:03d}"; d.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    cnt=max(2,round(s.duration*fps))
    if prev:
        for oi,fi2 in enumerate([0,int(cnt*.32),int(cnt*.72),cnt-1]):
            rf(s,fi2,cnt,w2,h2,idx*10000+fi2).save(d/f"preview_{oi:02d}.jpg",quality=95)
        return d
    for fi2 in range(cnt):
        p=d/f"{fi2:05d}.jpg"
        if p.exists(): continue
        rf(s,fi2,cnt,w2,h2,idx*10000+fi2).save(p,quality=95,subsampling=0)
    return es(idx,fps)
def concat(paths):
    cp=OUTPUT/"concat.txt"
    cp.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    final=OUTPUT/"matter_wonder.mp4"
    subprocess.run([_ff(),"-y","-f","concat","-safe","0","-i",str(cp),
        "-c","copy","-movflags","+faststart",str(final)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return final
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        item=asdict(s); item["scene_id"]=f"scene_{i:03d}"
        item["start_seconds"]=round(cursor,3); cursor+=s.duration
        item["end_seconds"]=round(cursor,3); recs.append(item)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"The Matter of Wonder","scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"SUBThe Matter of Wonder",
        "palette_roles":{"gold":"camatkara","violet":"the Absolute"},"scenes":recs},
        indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def contact_sheet(w2,h2):
    tw,th=320,int(320*h2/w2); cols,rows=4,math.ceil(len(SCENES)/4); ch=th+48
    s=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(s)
    lf=font(FNSB,14)
    for i,sc in enumerate(SCENES,1):
        cnt=max(2,round(sc.duration*FPS))
        im=rf(sc,int(cnt*.72),cnt,w2,h2,i*10000+72)
        im.thumbnail((tw,th)); sl=i-1
        x,y=(sl%cols)*tw,(sl//cols)*ch
        s.paste(im,(x,y)); d.text((x+9,y+th+7),f"{i:02d}  {sc.title}",font=lf,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; s.save(p,quality=94); return p
def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=FPS)
    p.add_argument("--width",type=int,default=W); p.add_argument("--height",type=int,default=H)
    p.add_argument("--scene",type=int); p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()
def main():
    a=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    tl=export_timeline(); total=sum(s.duration for s in SCENES)
    print(f"Timeline: {tl}\nScenes: {len(SCENES)}\nRuntime: {total/60:.2f} min")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError("--scene 1..{len(SCENES)}")
        print(rs(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        rendered.append(rs(i,s,a.fps,a.width,a.height,a.preview))
    final=concat(rendered); print(f"Final: {final}")
    if not a.no_contact_sheet: print(f"Contact: {contact_sheet(a.width,a.height)}")
    print("Done.")
if __name__=="__main__": main()
