#!/usr/bin/env python3
"""
THE PSYCHE IS NOT A THING — A Gestalt of Aware Energy
Seth and Silver on the psyche as an ever-forming state of being.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
The psyche is not a thing. It is a gestalt of aware energy — an ever-forming
state of being that you create and that creates you. It has no beginning
and no ending. It is pure energy and individuation simultaneously.
It is not in time. Time is in it.

For Seth and Silver: the psyche exists before the body and continues after it.
Personality is not what you have. It is what you ARE — and what you are is
a unique flavor of aware energy that changes state forever.

FILM THESIS
-----------
The modern picture often runs:

the psyche is inside the brain
→ it is produced by neural activity
→ it ends when the brain dies

The Seth/Silver picture can be staged as:

psyche is aware energy
→ it individuates into unique flavors
→ it creates the body, not vice versa
→ it dreams the next day's reality
→ it speaks through symbolism
→ it moves toward value fulfillment
→ it continues after the body dissolves

The psyche is not a product. It is the producer.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a rearranging constellation of luminous points.
• Final reveal: the constellation is aware of itself.

OUTPUT
------
output_psyche_gestalt/
  frames/
  scenes/
  psyche_gestalt.mp4
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
OUTPUT = ROOT / "output_psyche_gestalt"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH=1280; DEFAULT_HEIGHT=720; DEFAULT_FPS=10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
CYAN=(57,156,180); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); CRIMSON=(162,58,69); VIOLET=(109,83,153); PALE_VIOLET=(218,208,235)
PALE_CYAN=(196,227,233)
FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
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

def vis_gestalt(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+120*q),cy+math.sin(i*math.tau/40)*(30+120*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),VIOLET,3,200,12)
    glow_circle(im,cx,cy,14,VIOLET,int(190*q),10)
    seal(im,"GESTALT OF AWARE ENERGY","it is not a thing — no beginning or ending")

def vis_creation(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,16,GOLD,int(200*q),14)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        col=mix(VIOLET,GOLD,i/7); d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        d.ellipse((x-8*qc,y-8*qc,x+8*qc,y+8*qc),outline=(*col,int(140*qc)),width=1)
    seal(im,"YOU CREATE IT AND IT CREATES YOU","an ever-forming state of being")

def vis_energy(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(30):
        a=i*math.tau/30+t*.05; rad=20+100*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*CYAN,int(100*q)))
    glow_circle(im,cx,cy,12,VIOLET,int(180*q),10)
    seal(im,"PURE ENERGY AND INDIVIDUATION","energy becomes its manifestations")

def vis_dreaming(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,VIOLET,int(190*q),12)
    for i in range(6):
        a=i*math.tau/6+t*.08; rad=40+80*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        d.line((cx,cy,x,y),fill=(*PALE_VIOLET,int(140*q)),width=2)
        glow_circle(im,x,y,5+3*q,PALE_VIOLET,int(130*q),6)
    seal(im,"THE DREAMING PSYCHE IS AWAKE","as conscious as in waking — the psyche does not sleep")

def vis_gods(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        y=lerp(h*.22,h*.62,i/5); rad=lerp(12,20,i/5)
        col=mix(GOLD,CRIMSON,i/5)
        glow_circle(im,w*.50,y,rad*qc,col,int(180*qc),8)
        centered(d,(w*.50,y+rad*qc+20),f'GOD {i+1}',font(FONT_SANS_BOLD,int(h*.017)),col)
    seal(im,"PSYCHE, LANGUAGES, AND GODS","beliefs create the gods — they are living structures of psychic energy")

def vis_value(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+110*q),cy+math.sin(i*math.tau/30)*(30+110*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),GOLD,3,200,12)
    for i in range(5):
        a=i*math.tau/5+r*.3; qc=clamp(q*3-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*80*qc; y=cy+math.sin(a)*80*qc*.35
        glow_circle(im,x,y,5+2*q,GREEN,int(140*qc),6)
    seal(im,"VALUE FULFILLMENT","enhancing the quality of life itself — the psyche's purpose")

def vis_psi_field(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(20+130*q),cy+math.sin(i*math.tau/40)*(20+130*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),VIOLET,4,210,14)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+110*qc); y=cy+math.sin(a)*(30+110*qc)*.35
        col=mix(VIOLET,GOLD,i/7); d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        glow_circle(im,x,y,5+3*q,col,int(150*qc),7)
    seal(im,"THE PSYCHIC FIELD","the psyche is a field, not a thing — it extends beyond the individual")

def vis_ocean(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for j in range(5):
        pts=[]
        for i in range(60):
            f=i/59; x=lerp(w*.10,w*.90,f)
            y=cy+math.sin(f*math.tau*(3+j*1.5)+t*1.5+q*math.tau)*(10+j*6)*q
            pts.append((x,y))
        col=mix(VIOLET,CYAN,j/4)
        glow_line(im,partial(pts,q),col,width=2,alpha=int(160-20*j)*q,blur=8+j)
    seal(im,"THE PSYCHE IS AN OCEAN","the surface is your conscious mind — the depths hold all that you are")

def vis_psyche_field(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(30):
        a=i*math.tau/30+t*.04; rad=20+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(VIOLET,CYAN,i/29); d.ellipse((x-3,y-3,x+3,y+3),fill=(*col,int(130*q)))
    glow_circle(im,cx,cy,16,VIOLET,int(200*q),14)
    centered(d,(cx,cy),'~',font(FONT_SERIF_BOLD,int(h*.080)),(*VIOLET,int(200*q)))
    seal(im,"THE PSYCHE AS FIELD","not a thing in time — a field of aware energy that manifests as experience")

def vis_dreaming_psyche(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,18,VIOLET,int(200*q),14)
    for i in range(12):
        a=i*math.tau/12+t*.06; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+110*qc); y=cy+math.sin(a)*(30+110*qc)*.35
        col=mix(VIOLET,GOLD,i/11); d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        d.ellipse((x-6*qc,y-6*qc,x+6*qc,y+6*qc),fill=(*col,int(150*qc)))
        d.ellipse((x-10*qc,y-10*qc,x+10*qc,y+10*qc),outline=(*col,int(100*qc)),width=1)
    seal(im,"THE DREAMING PSYCHE","every night, the psyche weaves the next day — sleep is creative")

def vis_psyche_energy(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(40):
        a=i*math.tau/40+t*.04; rad=20+130*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        col=mix(CYAN,VIOLET,i/39); d.ellipse((x-3,y-3,x+3,y+3),fill=(*col,int(130*q)))
    glow_circle(im,cx,cy,14,VIOLET,int(190*q),12)
    seal(im,"PSYCHIC ENERGY","the psyche is a field of energy that individuates into experience")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"NEUROPLASTICITY",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"PSYCHIC FIELD",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"THE BRAIN IS NOT THE SOURCE OF THE PSYCHE","the brain is the physical interface — the psyche uses the brain")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("THE PSYCHE IS THE BRAIN","NOT SUPPORTED — THE BRAIN IS AN INTERFACE",CRIMSON),
        ("THE PSYCHE CONTINUES AFTER DEATH","CENTRAL CLAIM OF SETH/SILVER",CYAN),
        ("THE PSYCHE IS UNCHANGING","NOT SUPPORTED — IT IS EVER-FORMING",CRIMSON),
        ("THE PSYCHE CREATES THE BODY","SUPPORTED BY PRENATAL PSYCHOLOGY",GREEN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"THE PSYCHE IS NOT IN THE BODY — THE BODY IS IN THE PSYCHE","this is the inversion that changes everything")

VISUALS = {
    "gestalt":vis_gestalt,"creation":vis_creation,"energy":vis_energy,"dreaming":vis_dreaming,
    "gods":vis_gods,"value":vis_value,"psi_field":vis_psi_field,"ocean":vis_ocean,
    "psyche_field":vis_psyche_field,"dreaming_psyche":vis_dreaming_psyche,
    "psyche_energy":vis_psyche_energy,"bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("Gestalt of Aware Energy","It is not a thing — no beginning or ending.",9.0,"gestalt",{}),
    Scene("The Open Gestalt","The psyche never closes. It is always becoming.",9.0,"gestalt",{}),
    Scene("Not a Noun","The psyche is not a noun. It is a verb.",8.5,"gestalt",{}),
    Scene("You Create It and It Creates You","An ever-forming state of being.",9.0,"creation",{}),
    Scene("The Mutual Creation","You shape your psyche and your psyche shapes you. There is no end to the process.",9.0,"creation",{}),
    Scene("The Dance of Formation","The psyche is not fixed. It is the ongoing act of self-formation.",8.5,"creation",{}),
    Scene("Pure Energy and Individuation","Energy becomes its manifestations.",8.5,"energy",{}),
    Scene("The Energy Personality","You are a unique flavor of aware energy, like a distinct color of light.",9.0,"energy",{}),
    Scene("Individuation","Energy individuates into unique patterns. No two psyches are the same.",8.5,"energy",{}),
    Scene("The Dreaming Psyche is Awake","As conscious as in waking — the psyche does not sleep.",9.0,"dreaming",{}),
    Scene("The Dreaming Creates the Day","The psyche works out its next day while you sleep.",8.5,"dreaming",{}),
    Scene("The Nightly Design","Every night, the psyche designs the next day. Sleep is the artist's studio.",8.5,"dreaming",{}),
    Scene("Psyche, Languages, and Gods","Beliefs create the gods. They are living structures of psychic energy.",9.0,"gods",{}),
    Scene("The Gods are Real","Not as external beings — as living structures of psychic energy that shape experience.",9.0,"gods",{}),
    Scene("Myth is Psychic Truth","Myths are not fiction. They are the psyche's autobiography.",9.0,"gods",{}),
    Scene("Value Fulfillment","Enhancing the quality of life itself — the psyche's purpose.",9.5,"value",{}),
    Scene("The Psyche's Purpose","The psyche exists to enhance the quality of experience. Value is its compass.",9.0,"value",{}),
    Scene("Moving Toward Value","The psyche naturally moves toward what enhances life. This movement IS value fulfillment.",9.0,"value",{}),
    Scene("The Psychic Field","The psyche is a field, not a thing — it extends beyond the individual.",9.5,"psi_field",{}),
    Scene("Extended Psyche","Your psyche is not confined to your skull. It extends into your environment.",9.0,"psi_field",{}),
    Scene("Field Interactions","Psyches interact at a distance. This is the basis of telepathy and intuition.",9.0,"psi_field",{}),
    Scene("The Psyche is an Ocean","The surface is your conscious mind — the depths hold all that you are.",9.5,"ocean",{}),
    Scene("The Depths","Below the surface of your conscious mind, the psyche contains everything you have ever been.",9.0,"ocean",{}),
    Scene("The Ocean Floor","At the deepest level, all psyches are connected. The ocean has no bottom.",9.5,"ocean",{}),
    Scene("The Psyche as Field","Not a thing in time — a field of aware energy that manifests as experience.",9.5,"psyche_field",{}),
    Scene("Beyond Space and Time","The psyche is not in space or time. Space and time are forms it takes.",9.5,"psyche_field",{}),
    Scene("The Manifestation","Experience is the psyche's manifestation. The field takes the shape of attention.",9.0,"psyche_field",{}),
    Scene("The Dreaming Psyche","Every night, the psyche weaves the next day. Sleep is creative.",9.0,"dreaming_psyche",{}),
    Scene("The Nightly Art","The psyche does not rest at night. It creates the next day's experiences.",8.5,"dreaming_psyche",{}),
    Scene("The Creative Sleep","Dreaming is not processing. It is creating.",8.5,"dreaming_psyche",{}),
    Scene("Psychic Energy","The psyche is a field of energy that individuates into experience.",9.0,"psyche_energy",{}),
    Scene("Energy Never Dies","The psyche is energy. Energy transforms but does not cease.",9.5,"psyche_energy",{}),
    Scene("The Continuity","The psyche continues after the body. Energy does not disappear — it changes form.",9.5,"psyche_energy",{}),
    Scene("Science Bridge","Neuroplasticity shows the brain changes with experience. But the brain is the interface, not the source.",9.0,"bridge",{}),
    Scene("The Interface Model","If the psyche uses the brain as an interface, brain damage affects reception, not the signal.",9.0,"bridge",{}),
    Scene("The Open Question","Is the mind produced by the brain, or received through it? The evidence for either is not conclusive.",9.0,"bridge",{}),
    Scene("Caution","The psyche is not in the body — the body is in the psyche.",8.5,"caution",{}),
    Scene("The Inversion","This inversion changes everything. You are not a body with a psyche. You are a psyche with a body.",9.0,"caution",{}),
    Scene("The Practice","Know your psyche. It is the only thing you truly have.",8.5,"caution",{}),
    Scene("Closing","The psyche is not a thing. It is a gestalt of aware energy — ever-forming, ever-creating. You create it and it creates you. It has no beginning and no ending. It is pure energy and individuation simultaneously. The body is not its container. The psyche is the container of all experience.",10.0,"psyche_field",{}),
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
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
    o=OUTPUT/"psyche_gestalt.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"the psyche is not a thing","subtitle":"a gestalt of aware energy",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"rearranging constellation of luminous points",
        "visual_arc":["gestalt","creation","energy","dreaming","gods","value","field"],
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
