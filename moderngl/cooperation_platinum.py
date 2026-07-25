#!/usr/bin/env python3
"""
THE BODY IS A COOPERATIVE VENTURE — Cooperation Before Competition
The body exists through inner cooperation.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
The body does not exist because cells compete. It exists because cells cooperate.
Competition is derivative. Cooperation is the ground. Every cell in your body
trusts every other cell. That trust IS health. Illness is broken communication.

For Silver and Seth: cooperation is not a moral choice. It is the biological
and metaphysical structure of existence. The universe is a gift economy.
Life gives itself to itself through cooperation.

FILM THESIS
-----------
The modern picture often runs:

competition → survival of the fittest → nature is red in tooth and claw

The cooperation-first picture can be staged as:

cooperation is given at birth
→ cells communicate and trust
→ the body emerges as a society
→ competition appears only when cooperation breaks down
→ health is restored cooperation
→ consciousness is a cooperative phenomenon

Cooperation is not something we learn. It is something we are.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a network of cooperating nodes — each node connected to every other.
• Final reveal: the network has no center — cooperation is the structure itself.

OUTPUT
------
output_cooperation/
  frames/
  scenes/
  cooperation.mp4
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
OUTPUT = ROOT / "output_cooperation"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH=1280; DEFAULT_HEIGHT=720; DEFAULT_FPS=10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
CYAN=(57,156,180); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); PALE_GREEN=(196,225,206); CRIMSON=(162,58,69); VIOLET=(109,83,153)
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

def vis_cooperation(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+120*q),cy+math.sin(i*math.tau/40)*(30+120*q)*.35) for i in range(41)]
    glow_line(im,partial(pts,q),GREEN,3,200,12)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+90*qc); y=cy+math.sin(a)*(30+90*qc)*.35
        d.ellipse((x-5*qc,y-5*qc,x+5*qc,y+5*qc),fill=(*PALE_GREEN,int(150*qc)))
    seal(im,"THE BODY EXISTS THROUGH COOPERATION","inner cooperative relationships bind every cell")

def vis_given(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,16,GOLD,int(200*q),14)
    for i in range(6):
        a=i*math.tau/6+r*.3; qc=clamp(q*3-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+80*qc); y=cy+math.sin(a)*(40+80*qc)*.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(150*qc)),width=2)
    seal(im,"COOPERATION IS GIVEN","it is the gift of life — present at birth")

def vis_molecular(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    rng=random.Random(42)
    for i in range(40):
        qc=clamp(q*2-i*.01)
        if qc<=0: continue
        a=rng.uniform(0,math.tau); rad=rng.uniform(20,130)*qc
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        col=CYAN if rng.random()<.4 else (GREEN if rng.random()<.7 else GOLD)
        d.ellipse((x-3*qc,y-3*qc,x+3*qc,y+3*qc),fill=(*col,int(140*qc)))
    glow_circle(im,cx,cy,10,GREEN,int(180*q),9)
    seal(im,"MOLECULAR COOPERATION","the body speaks against chance")

def vis_value(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(190*q),12)
    for i in range(5):
        qc=clamp(q*5-i)
        if qc<=0: continue
        y=lerp(h*.25,h*.62,i/4); width=lerp(40,250,i/4)*qc
        d.line((w*.50-width/2,y,w*.50+width/2,y),fill=(*GOLD,int(180*qc)),width=4)
    seal(im,"VALUE FULFILLMENT","enhancing quality for all species")

def vis_altruism(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        a=i*math.tau/6+t*.06; qc=clamp(q*4-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+100*qc); y=cy+math.sin(a)*(20+100*qc)*.35
        col=mix(GREEN,CYAN,i/5)
        d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        arrow(d,(cx+(x-cx)*.85,cy+(y-cy)*.85),(x,y),col,2,8)
    seal(im,"INNATE ALTRUISM","a natural bent for caring — helpfulness is biological")

def vis_health(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+110*q),cy+math.sin(i*math.tau/30)*(30+110*q)*.35) for i in range(31)]
    glow_line(im,partial(pts,q),GREEN,4,220,14)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+90*qc); y=cy+math.sin(a)*(30+90*qc)*.35
        d.line((cx,cy,x,y),fill=(*GREEN,int(140*qc)),width=2)
    seal(im,"HEALTH AS COOPERATION","illness is broken communication — health is restored dialogue")

def vis_cell_society(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    rng=random.Random(42)
    pts=[]
    for i in range(30):
        a=rng.uniform(0,math.tau); rad=rng.uniform(20,130)*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        col=CYAN if rng.random()<.4 else (GREEN if rng.random()<.7 else GOLD)
        sz=rng.uniform(3,7)*q
        d.ellipse((x-sz,y-sz,x+sz,y+sz),fill=(*col,int(180*q)))
        pts.append((x,y))
    if len(pts)>5:
        for i in range(0,len(pts)-1,2):
            d.line((*pts[i],*pts[i+1]),fill=(*PALE_GREEN,int(60*q)),width=1)
    glow_circle(im,cx,cy,10,GREEN,int(180*q),9)
    seal(im,"THE CELL SOCIETY","the body is a society of trillions — cooperation is the constitution")

def vis_immune(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GREEN,int(180*q),10)
    for i in range(12):
        a=i*math.tau/12+t*.05; qc=clamp(q*4-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        col=mix(CYAN,GREEN,i/11); d.line((cx,cy,x,y),fill=(*col,int(150*qc)),width=2)
        d.ellipse((x-6*qc,y-6*qc,x+6*qc,y+6*qc),fill=(*col,int(140*qc)))
        if qc>.7: centered(d,(x,y+15*qc),f'CELL {i+1}',font(FONT_SANS_BOLD,int(h*.014)),(*col,int(150*qc)))
    seal(im,"THE IMMUNE DIALOGUE","the immune system is not an army — it is a conversation about identity")

def vis_cooperation_gift(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,16,GOLD,int(200*q),14)
    for i in range(8):
        a=i*math.tau/8+t*.05; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+100*qc); y=cy+math.sin(a)*(30+100*qc)*.35
        col=mix(GOLD,GREEN,i/7); d.line((cx,cy,x,y),fill=(*col,int(160*qc)),width=2)
        d.ellipse((x-6*qc,y-6*qc,x+6*qc,y+6*qc),fill=(*col,int(150*qc)))
    seal(im,"COOPERATION IS THE GIFT","life gives itself to itself through cooperation")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"SYMBIOSIS RESEARCH",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"GIFT ECONOMY",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE CONFIRMS: SYMBIOSIS IS THE RULE","competition is local; cooperation is global")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("COOPERATION MEANS NO COMPETITION","NOT SUPPORTED — BOTH EXIST",CRIMSON),
        ("COOPERATION IS THE GROUND","SUPPORTED BY BIOLOGY",GREEN),
        ("COMPETITION IS THE ONLY DRIVER","REFUTED BY SYMBIOTIC RESEARCH",CRIMSON),
        ("THE BODY IS A GIFT ECONOMY","SUPPORTED BY CELLULAR BIOLOGY",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"COOPERATION DOES NOT DENY COMPETITION","it places competition inside a larger context of collaboration")

VISUALS = {
    "cooperation":vis_cooperation,"given":vis_given,"molecular":vis_molecular,
    "value":vis_value,"altruism":vis_altruism,"health":vis_health,
    "cell_society":vis_cell_society,"immune":vis_immune,"gift":vis_cooperation_gift,
    "bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("The Body Exists Through Cooperation","Inner cooperative relationships bind every cell.",9.0,"cooperation",{}),
    Scene("The Cellular Society","Your body is a society of trillions. Cooperation is the constitution.",9.0,"cooperation",{}),
    Scene("The Cooperative Venture","You are not one thing. You are a cooperation that learned to say 'I'.",9.5,"cooperation",{}),
    Scene("Cooperation is Given","It is the gift of life — present at birth.",8.5,"given",{}),
    Scene("The Inborn Trust","A newborn trusts before it learns fear. Cooperation is not learned — it is assumed.",9.0,"given",{}),
    Scene("The Gift of Life","Every cell receives its life from the whole. Nothing is self-made.",9.0,"given",{}),
    Scene("Molecular Cooperation","The body speaks against chance. Molecules work together.",9.0,"molecular",{}),
    Scene("Against Entropy","Cooperation is how life resists entropy. Together, cells create order.",9.0,"molecular",{}),
    Scene("The Molecular Dance","Molecules do not compete. They cooperate to form the dance of life.",9.0,"molecular",{}),
    Scene("Value Fulfillment","Enhancing quality for all species.",9.0,"value",{}),
    Scene("The Common Good","Value fulfillment is the direction of evolution — toward greater cooperation.",9.0,"value",{}),
    Scene("Quality of Life","The psyche moves toward what enhances life. Value is its compass.",9.0,"value",{}),
    Scene("Innate Altruism","A natural bent for caring. Helpfulness is biological.",9.0,"altruism",{}),
    Scene("The Helping Instinct","Altruism is not a cultural invention. It is encoded in life.",9.0,"altruism",{}),
    Scene("The Generous Gene","Genes that cooperate outcompete genes that do not.",9.0,"altruism",{}),
    Scene("Health as Cooperation","Illness is broken communication. Health is restored dialogue.",9.5,"health",{}),
    Scene("The Body Trusts","Every cell trusts the whole. That trust IS health.",9.0,"health",{}),
    Scene("The Healing Dialogue","Restoring communication between cells is the most fundamental healing.",9.5,"health",{}),
    Scene("The Cell Society","The body is a society of trillions. Cooperation is the constitution.",9.5,"cell_society",{}),
    Scene("Collective Intelligence","The body is a swarm intelligence. No single cell knows the whole, but the whole knows itself.",9.5,"cell_society",{}),
    Scene("The Commonwealth","Every cell contributes, every cell receives. The body is a commonwealth.",9.5,"cell_society",{}),
    Scene("The Immune Dialogue","The immune system is not an army — it is a conversation about identity.",9.5,"immune",{}),
    Scene("Identification","The immune system decides what is self and what is not-self. This is the most basic cooperation.",9.5,"immune",{}),
    Scene("The Listening Defense","The immune system does not attack. It listens and responds.",9.0,"immune",{}),
    Scene("Cooperation is the Gift","Life gives itself to itself through cooperation.",10.0,"gift",{}),
    Scene("The Gift Economy", "Cells give without counting. The body is a pure gift economy.",9.5,"gift",{}),
    Scene("The Generous Universe","The universe is not a battlefield. It is a gift exchange.",10.0,"gift",{}),
    Scene("Science Bridge","Symbiosis research shows cooperation is the rule in nature, not the exception.",9.0,"bridge",{}),
    Scene("The Symbiotic Body","Your body contains more bacterial cells than human cells. Cooperation is the rule.",9.5,"bridge",{}),
    Scene("From Biology to Culture","Cooperation scales from cells to societies. It is the same principle.",9.5,"bridge",{}),
    Scene("Caution","Cooperation does not deny competition. It places competition inside a larger context.",9.0,"caution",{}),
    Scene("The Nested View","Competition happens within cooperation. The ground is always collaborative.",9.0,"caution",{}),
    Scene("The Deeper Truth","Before rivalry, there is relationship. Before competition, there is cooperation.",9.0,"caution",{}),
    Scene("Closing","The body is a cooperative venture. It exists because cells cooperate. Competition is derivative. Cooperation is the ground. Every cell trusts every other cell. That trust IS health. Cooperation is not a moral choice. It is the structure of existence. The universe is a gift economy — and you are its giving.",10.0,"gift",{}),
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
    o=OUTPUT/"cooperation.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"; p.write_text(json.dumps({"title":"the body is a cooperative venture",
        "subtitle":"cooperation before competition","scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"network of cooperating nodes — each connected to every other",
        "visual_arc":["cooperation","given","molecular","altruism","health","gift"],
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
