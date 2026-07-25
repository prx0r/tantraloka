#!/usr/bin/env python3
"""
DNA IS NOT A BLUEPRINT — It Is a Receiver of Consciousness
The antenna model of genetic expression.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
DNA does not contain a blueprint for the body. It is a receiver — an antenna
that translates consciousness into biological form. The genetic code is not
an instruction set. It is a tuning mechanism that selects which frequency
of consciousness will be expressed as lived experience.

For Seth and Silver: you do not get your DNA from your parents. You receive
it. The Wave adds frequency. DNA is the antenna that converts cosmic
information into biological reality.

FILM THESIS
-----------
The modern picture often runs:

DNA contains genetic instructions
→ the body reads the instructions
→ you are the product of your genes

The antenna model can be staged as:

consciousness exists as a field
→ DNA selects a frequency from the field
→ the frequency is expressed as form
→ you do not get DNA — you receive it
→ your body is a translation of consciousness

Mutation is not random. It is retuning.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a double helix radiating and receiving signals.
• Final reveal: the signal is consciousness — and you are both the antenna and the signal.

OUTPUT
------
output_dna_antenna/
  frames/
  scenes/
  dna_antenna.mp4
  narration_timeline.json
  contact_sheet.jpg
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_dna_antenna"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH=1280; DEFAULT_HEIGHT=720; DEFAULT_FPS=10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
CYAN=(57,156,180); PALE_CYAN=(196,227,233); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); CRIMSON=(162,58,69); VIOLET=(109,83,153); PALE_VIOLET=(218,208,235)
FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)
def font(path,size):
    for c in (path,FONT_SERIF,FONT_SANS):
        try: return ImageFont.truetype(c,size)
        except OSError: pass
    return ImageFont.load_default()
def layer(size): return Image.new("RGBA",size,(0,0,0,0))
def field(w,h,seed):
    rng=np.random.default_rng(seed)
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=IVORY
    arr+=rng.normal(0,.9,(h,w,1)); yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2)
    arr[...,1]+=halo*3.2; arr[...,2]+=halo*4.6
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")
def centered(d,xy,text,fnt,fill=INK): d.text(xy,text,font=fnt,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered(d,(w/2,h*.875),title,font(FONT_SERIF_BOLD,max(22,int(h*.04))),color)
    if subtitle: centered(d,(w/2,h*.923),subtitle,font(FONT_SANS,max(13,int(h*.019))),SOFT_INK)
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,45),width=2)
def glow_circle(im,x,y,r,color,alpha=170,blur=14):
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.ellipse((x-r,y-r,x+r,y+r),fill=(*color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).ellipse((x-r*.34,y-r*.34,x+r*.34,y+r*.34),
        fill=(*mix(color,WHITE,.35),min(255,alpha+50)))
    im.alpha_composite(fg)
def glow_line(im,pts,color,width=4,alpha=210,blur=11):
    if len(pts)<2: return
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.line(pts,fill=(*color,alpha),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(color,WHITE,.08),min(255,alpha+25)),width=width,joint="curve")
    im.alpha_composite(fg)
def partial(pts,a):
    if not pts: return []; a=clamp(a)
    if a>=1: return pts
    k=a*(len(pts)-1); i=int(k); f=k-i
    out=list(pts[:i+1])
    if i+1<len(pts): p,q=pts[i],pts[i+1]; out.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return out
def arrow(d,a,b,color=INK,width=3,head=10):
    d.line((*a,*b),fill=color,width=width)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (-1,1):
        p=(b[0]-math.cos(ang+s*.52)*head,b[1]-math.sin(ang+s*.52)*head)
        d.line((*b,*p),fill=color,width=width)

def vis_superconductor(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(20):
        f=i/19; x=lerp(w*.20,w*.80,f); a=f*math.tau*3+q*math.tau
        y1=cy+math.cos(a)*30; y2=cy+math.cos(a+math.pi)*30
        col=mix(CYAN,PALE_CYAN,.5+.5*math.sin(f*math.tau))
        d.line((x,y1,x,y2),fill=(*col,int(200*q)),width=2)
        d.ellipse((x-4,y1-4,x+4,y1+4),fill=(*CYAN,int(160*q)))
        d.ellipse((x-4,y2-4,x+4,y2+4),fill=(*CYAN,int(160*q)))
    seal(im,"DNA AS SUPERCONDUCTOR","conducts electricity — not just information")

def vis_transceiver(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,VIOLET,int(200*q),12)
    for i in range(8):
        a=i*math.tau/8+t*.06; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        d.line((cx,cy,x,y),fill=(*VIOLET,int(150*qc)),width=2)
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),VIOLET,2,8)
    seal(im,"NEUROTRANSCEIVER FOR THOUGHT","DNA receives and transmits consciousness")

def vis_illusion(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+100*q),cy+math.sin(i*math.tau/30)*(30+100*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),GOLD,3,200,12)
    centered(d,(cx,cy),'LINEAR',font(FONT_SANS_BOLD,int(h*.030)),(*GOLD,int(180*q)))
    centered(d,(cx,cy+35*q),'TIME',font(FONT_SANS_BOLD,int(h*.025)),(*SOFT_INK,int(150*q)))
    seal(im,"THE PROGRAM ILLUSION","linear time is a DNA readout, not the structure of reality")

def vis_strands(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for j in range(2):
        off=j*math.pi
        pts=[(lerp(w*.15,w*.85,i/59),cy+math.sin(i/59*math.tau*4+off+q*math.tau)*20) for i in range(60)]
        glow_line(im,partial(pts,q),mix(CYAN,GOLD,j),width=3,alpha=180,blur=10)
    seal(im,"YOU RECEIVE, NOT GET","the Wave adds frequency — DNA is the antenna")

def vis_removal(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        y=lerp(h*.22,h*.65,i/5); col=mix(GOLD,CRIMSON,i/5)
        d.ellipse((w*.50-15*qc,y-15*qc,w*.50+15*qc,y+15*qc),fill=(*col,int(180*qc)))
    seal(im,"REMOVAL OF KNOWLEDGE CENTERS","Osiris cut apart = DNA frequency reduced")

def vis_antenna(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(40):
        a=i*math.tau/40+t*.04; rad=20+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,3+2*q,GOLD,int(130*q),5)
    glow_circle(im,cx,cy,16,CYAN,int(200*q),12)
    seal(im,"THE ANTENNA MODEL","DNA optimized for reception of consciousness")

def vis_frequency(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for j in range(3):
        pts=[]
        for i in range(80):
            f=i/79; x=lerp(w*.10,w*.90,f); freq=4+j*2
            y=cy+math.sin(f*math.tau*freq+q*t)*15*(1+j*.3)*q
            pts.append((x,y))
        col=mix(CYAN,GOLD,j/2)
        glow_line(im,partial(pts,q),col,width=3-j,alpha=int(180-40*j)*q,blur=10-2*j)
    seal(im,"FREQUENCY IS INFORMATION","DNA receives different frequencies — each is a different reality")

def vis_dna_helix(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for j in range(2):
        off=j*math.pi; pts=[]
        for i in range(60):
            f=i/59; x=lerp(w*.20,w*.80,f)
            y=cy+math.sin(f*math.tau*4+off+q*math.tau)*(20+8*f)*q
            pts.append((x,y))
        col=CYAN if j==0 else GOLD
        glow_line(im,partial(pts,q),col,width=3,alpha=180,blur=10)
        for i in range(0,60,10):
            f=i/59; x=lerp(w*.20,w*.80,f)
            y=cy+math.sin(f*math.tau*4+off+q*math.tau)*(20+8*f)*q
            d.ellipse((x-4*q,y-4*q,x+4*q,y+4*q),fill=(*col,int(160*q)))
    seal(im,"THE DNA HELIX","a double helix of reception — each strand receives a different frequency")

def vis_consciousness_field(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+130*q),cy+math.sin(i*math.tau/40)*(30+130*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),VIOLET,4,220,14)
    for i in range(10):
        a=i*math.tau/10+t*.04; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+120*qc); y=cy+math.sin(a)*(30+120*qc)*.35
        d.line((cx,cy,x,y),fill=(*VIOLET,int(140*qc)),width=2)
        glow_circle(im,x,y,4+2*q,PALE_VIOLET,int(130*qc),6)
    seal(im,"THE CONSCIOUSNESS FIELD","consciousness is not produced by the brain — it is received through DNA")

def vis_light_body(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+130*q),cy+math.sin(i*math.tau/40)*(30+130*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),GOLD,5,230,18)
    for i in range(12):
        a=i*math.tau/12+t*.04; rad=25+120*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        d.ellipse((x-3*q,y-3*q,x+3*q,y+3*q),fill=(*PALE_GOLD,int(140*q)))
    centered(d,(cx,cy),'LIGHT',font(FONT_SERIF_BOLD,int(h*.055)),(*GOLD,int(210*q)))
    seal(im,"THE LIGHT BODY","DNA is the interface between consciousness and matter")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"EPIGENETICS",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"ANTENNA MODEL",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"EPIGENETICS SHOWS GENES ARE NOT DESTINY","the environment influences expression — the antenna model extends this to consciousness")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("DNA IS A BINDING BLUEPRINT","NOT SUPPORTED — ONLY 2% CODES FOR PROTEINS",CRIMSON),
        ("DNA CONDUCTS ELECTRICITY","SUPPORTED BY RESEARCH",GREEN),
        ("CONSCIOUSNESS IS PRODUCED BY DNA","NOT ESTABLISHED — DNA RECEIVES CONSCIOUSNESS",CRIMSON),
        ("MUTATIONS ARE RANDOM","NOT SUPPORTED — MUTATIONS ARE RESPONSIVE",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DNA IS NOT A BLUEPRINT — IT IS A RECEIVER","the antenna model is a hypothesis, not a proven theory")

VISUALS = {
    "superconductor":vis_superconductor,"transceiver":vis_transceiver,"illusion":vis_illusion,
    "strands":vis_strands,"removal":vis_removal,"antenna":vis_antenna,
    "frequency":vis_frequency,"dna_helix":vis_dna_helix,"consciousness_field":vis_consciousness_field,
    "light_body":vis_light_body,"bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("DNA as Superconductor","Conducts electricity — not just information.",8.5,"superconductor",{}),
    Scene("The Electrical Body","DNA conducts electrons. The body is an electrical system.",8.5,"superconductor",{}),
    Scene("More Than Code","The model says DNA is not a blueprint but a receiving system.",8.5,"superconductor",{}),
    Scene("Neurotransceiver for Thought","DNA receives and transmits consciousness.",9.0,"transceiver",{}),
    Scene("The Two-Way Street","DNA is not read-only. It receives and transmits.",8.5,"transceiver",{}),
    Scene("The Cosmic Exchange","You are in constant communication with the field through DNA.",8.5,"transceiver",{}),
    Scene("The Program Illusion","Linear time is a DNA readout, not the structure of reality.",8.5,"illusion",{}),
    Scene("Sequential Readout","DNA reads out sequentially. This creates the illusion of linear time.",9.0,"illusion",{}),
    Scene("The Program Metaphor","The genetic program is a useful metaphor, not a literal instruction set.",8.5,"illusion",{}),
    Scene("You Receive, Not Get","The Wave adds frequency. DNA is the antenna.",9.0,"strands",{}),
    Scene("The Wave Comes","Humanity is receiving a new frequency. DNA is adapting.",9.0,"strands",{}),
    Scene("The Signal and the Antenna","Consciousness is a wave. DNA is the antenna that translates it into form.",9.0,"strands",{}),
    Scene("Removal of Knowledge Centers","Osiris cut apart = DNA frequency reduced.",8.5,"removal",{}),
    Scene("The Fragmentation","The myth of Osiris describes the fragmentation of human DNA frequency.",9.0,"removal",{}),
    Scene("The Reassembly","As Osiris was reassembled, so human DNA can be restored to full reception.",9.0,"removal",{}),
    Scene("The Antenna Model","DNA optimized for reception of consciousness.",9.0,"antenna",{}),
    Scene("The Tuning Fork","DNA is a tuning fork that resonates with specific frequencies of consciousness.",9.0,"antenna",{}),
    Scene("The Optimum Shape","The double helix is the shape of optimal reception.",8.5,"antenna",{}),
    Scene("Frequency is Information","DNA receives different frequencies — each is a different reality.",9.5,"frequency",{}),
    Scene("The Frequency Spectrum","Different states of consciousness correspond to different DNA frequencies.",9.0,"frequency",{}),
    Scene("The Shift","Humanity is shifting frequency. DNA is retuning.",9.5,"frequency",{}),
    Scene("The DNA Helix","A double helix of reception — each strand receives a different frequency.",9.0,"dna_helix",{}),
    Scene("Yin and Yang","One strand receives. The other transmits. The helix is a transceiver.",9.0,"dna_helix",{}),
    Scene("The Two Currents","The two strands carry complementary frequencies. Balance is full reception.",9.0,"dna_helix",{}),
    Scene("The Consciousness Field","Consciousness is not produced by the brain — it is received through DNA.",9.5,"consciousness_field",{}),
    Scene("The Cosmic Signal","The universe transmits. Humanity is learning to receive a new frequency.",9.5,"consciousness_field",{}),
    Scene("Reception vs Production","The difference between believing consciousness is produced or received is everything.",9.5,"consciousness_field",{}),
    Scene("The Light Body","DNA is the interface between consciousness and matter.",9.5,"light_body",{}),
    Scene("The Bridge of Light","DNA is the bridge between the immaterial and the material.",9.5,"light_body",{}),
    Scene("The Luminous Interface","At its deepest level, DNA is made of light — frozen into form.",9.5,"light_body",{}),
    Scene("Science Bridge","Epigenetics shows genes are not destiny. The environment influences expression.",9.0,"bridge",{}),
    Scene("Beyond Epigenetics","The antenna model extends environmental influence to include consciousness.",9.0,"bridge",{}),
    Scene("The Open Question","If consciousness can influence gene expression, what is the limit of this influence?",9.0,"bridge",{}),
    Scene("Caution","DNA is not a blueprint — the antenna model is a hypothesis, not a proven theory.",8.5,"caution",{}),
    Scene("Not a Replacement","The antenna model does not replace molecular biology. It extends it.",8.5,"caution",{}),
    Scene("The Integration","Molecular biology and the antenna model are compatible at different levels.",8.5,"caution",{}),
    Scene("Closing","DNA is not a blueprint. It is a receiver — an antenna that translates consciousness into form. You do not get your DNA. You receive it. The Wave adds frequency. DNA is the tuning fork. And when the signal is fully received, you know: you are not the antenna. You are the signal itself.",10.0,"consciousness_field",{}),
]

def render_frame(s,fi,fc,w,h,seed):
    u=fi/max(1,fc-1); t=u*s.duration
    im=field(w,h,seed); VISUALS[s.visual](im,u,t,s.params); border(im)
    return im.convert("RGB")
def ffmpeg_path():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg required")
    return exe
def encode_scene(idx,fps):
    fd=FRAMES/f"scene_{idx:03d}"; o=SCENES_DIR/f"scene_{idx:03d}.mp4"
    subprocess.run([ffmpeg_path(),"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def render_scene(idx,s,fps,w,h,prev):
    fd=FRAMES/f"scene_{idx:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    cnt=max(2,round(s.duration*fps))
    if prev:
        for oi,fi in enumerate([0,int(cnt*.33),int(cnt*.72),cnt-1]):
            render_frame(s,fi,cnt,w,h,idx*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(cnt):
        p=fd/f"{fi:05d}.jpg"
        if p.exists(): continue
        render_frame(s,fi,cnt,w,h,idx*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(idx,fps)
def concat(paths):
    txt=OUTPUT/"concat.txt"; txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    o=OUTPUT/"dna_antenna.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"DNA is not a blueprint","subtitle":"it is a receiver of consciousness",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"double helix radiating and receiving signals",
        "visual_arc":["superconductor","transceiver","antenna","frequency","light body"],
        "scenes":recs},indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def contact_sheet(w,h):
    tw=320; th=int(tw*h/w); cols=4; rows=math.ceil(len(SCENES)/4); ch=th+48
    s=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(s); lf=font(FONT_SANS_BOLD,14)
    for i,sc in enumerate(SCENES,1):
        cnt=max(2,round(sc.duration*DEFAULT_FPS))
        im=render_frame(sc,int(cnt*.72),cnt,w,h,i*10000+72); im.thumbnail((tw,th))
        sl=i-1; x=(sl%cols)*tw; y=(sl//cols)*ch; s.paste(im,(x,y))
        d.text((x+8,y+th+7),f"{i:02d}  {sc.title}",font=lf,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; s.save(p,quality=94); return p
def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS); p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT); p.add_argument("--scene",type=int)
    p.add_argument("--preview",action="store_true"); p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()
def main():
    a=parse_args(); OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_timeline()}"); print(f"Scenes: {len(SCENES)}"); print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} min")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError("scene out of range")
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rendered.append(r)
    if not a.no_contact_sheet: print(f"Contact: {contact_sheet(a.width,a.height)}")
    if not a.preview: print(f"Final: {concat(rendered)}")
if __name__=="__main__": main()
