#!/usr/bin/env python3
"""
THE DAIMON SPEAKS IN DREAMS — Synesius and the PGM Dream Curriculum
Dream incubation as the primary method of daimonic contact.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
The daimon impresses images on the pneuma (the subtle body) during sleep.
Dream incubation is the deliberate cultivation of this process. By planting
a question before sleep, you seed the imaginal field. The daimon responds
not in words but in images, moods, and narratives that carry precise meaning.

For Synesius of Cyrene, dreams are not side effects of neural activity.
They are the primary channel of daimonic communication. The PGM offers
18 spells for systematic dream incubation.

FILM THESIS
-----------
The modern picture often runs:

sleep → random neural activity → dreams are noise

The daimonic picture can be staged as:

daimon intends communication
→ impresses image on pneuma
→ sleeper receives as dream
→ if remembered, the message reaches waking consciousness
→ the dream changes the dreamer

The bridge between daimon and self is the imaginal body.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a dream-thread from daimon to sleeper.
• Final reveal: the thread is the pneuma — you are the dreamer and the dreamed.

OUTPUT
------
output_dream_incubation/
  frames/
  scenes/
  dream_incubation.mp4
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
OUTPUT = ROOT / "output_dream_incubation"
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
    arr+=rng.normal(0,.9,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
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

def draw_dream_thread(im,cx,cy,progress,color=VIOLET):
    pts=[]
    for i in range(140):
        q=i/139; x=cx-180+q*360
        y=cy+math.sin(q*math.tau*4+progress*math.tau)*(8+24*math.sin(q*math.pi))
        pts.append((x,y))
    glow_line(im,partial(pts,progress),color,3,200,10)


def vis_core(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,VIOLET)
    glow_circle(im,cx,cy,16,VIOLET,int(180*q),12)
    glow_circle(im,cx,cy,8,GOLD,int(160*q),6)
    seal(im,"THE CORE CLAIM","the daimon impresses images on the pneuma during sleep")

def vis_pneuma(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_dream_thread(im,cx,cy,q*.7,CYAN)
    for i in range(15):
        a=i*math.tau/15+t*.08; rad=30+70*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        col=mix(CYAN,PALE_CYAN,.5+.5*math.sin(t+i))
        d.ellipse((x-6*q,y-6*q,x+6*q,y+6*q),fill=(*col,int(160*q)))
    seal(im,"THE IMAGINATIVE PNEUMA","shared medium between soul and daimon — the subtle body of images")

def vis_three(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im); q=ease(u)
    states=[("DREAMLESS",CYAN),("ORDINARY",GOLD),("LUCID",VIOLET)]
    for i,(label,col) in enumerate(states):
        qc=clamp(q*3-i*.15)
        if qc<=0: continue
        x=w*(.25+i*.25)
        glow_circle(im,x,h*.42,12+6*qc,col,int(190*qc),9)
        if qc>.5: centered(d,(x,h*.55),label,font(FONT_SANS_BOLD,int(h*.022)),col)
    seal(im,"THREE DREAM STATES","each has a daimonic function — the continuum of attention")

def vis_synesian(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,GOLD)
    d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(180*q),10)
    for i in range(6):
        a=i*math.tau/6+t*.06; qc=clamp(q*4-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(40+80*qc); y=cy+math.sin(a)*(40+80*qc)*.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(140*qc)),width=2)
    seal(im,"THE SYNESIAN METHOD","a question before sleep seeds the astral body for incubation")

def vis_curriculum(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,VIOLET)
    d=ImageDraw.Draw(im)
    for i in range(6):
        qc=clamp(q*6-i)
        if qc<=0: continue
        y=lerp(h*.20,h*.67,i/5); col=mix(CYAN,GOLD,i/5)
        d.rounded_rectangle((w*.30,y-14,w*.70,y+14),radius=8,
            fill=(*mix(WHITE,col,.15),int(220*qc)),outline=(*col,int(160*qc)),width=2)
        centered(d,(w*.50,y),f"Level {i+1}",font(FONT_SANS_BOLD,int(h*.020)),col)
    seal(im,"PGM DREAM CURRICULUM","18 spells — 6 levels from dream recall to systasis")

def vis_waking(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,CYAN)
    d=ImageDraw.Draw(im)
    d.ellipse((cx-80*q,cy-80*q,cx+80*q,cy+80*q),outline=(*CYAN,int(170*q)),width=3)
    glow_circle(im,cx,cy,14,GOLD,int(160*q),10)
    if q>.5:
        d.ellipse((cx-120*q,cy-120*q,cx+120*q,cy+120*q),
                  outline=(*CYAN,int(100*(q-.5)/.5)),width=2)
    seal(im,"THE EGG RITUAL AS WAKING DREAM","entering the dream state consciously — the systasis")

def vis_practice(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_dream_thread(im,cx,cy,q,GREEN)
    for i in range(4):
        qc=clamp(q*4-i*.1)
        if qc<=0: continue
        x=cx+(i-1.5)*w*.18
        glow_circle(im,x,cy,8+4*qc,GREEN,int(170*qc),8)
        d.line((cx,cy,x,cy),fill=(*GREEN,int(140*qc)),width=2)
    seal(im,"DAILY PRACTICE","write, place under pillow, listen — the discipline of incubation")

def vis_lucid(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,GOLD)
    d=ImageDraw.Draw(im)
    for i in range(10):
        a=i*math.tau/10+t*.06; qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+100*qc); y=cy+math.sin(a)*(20+100*qc)*.35
        d.ellipse((x-6*qc,y-6*qc,x+6*qc,y+6*qc),fill=(*PALE_GOLD,int(150*qc)))
    seal(im,"LUCIDITY ARISES","the dreamer realizes: this is a dream. The daimon smiles.")

def vis_image_seed(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,VIOLET)
    d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,10,GOLD,int(180*q),8)
    for i in range(8):
        a=i*math.tau/8+r*.8; rad=20+60*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        sz=3+4*q; d.ellipse((x-sz,y-sz,x+sz,y+sz),fill=(*PALE_VIOLET,int(140*q)))
    seal(im,"THE IMAGE SEED","a single image planted before sleep — the daimon grows it into a dream")

def vis_dream_forgetting(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,1-q,CRIMSON)
    d=ImageDraw.Draw(im)
    for i in range(8):
        a=i*math.tau/8+t*.1; rad=20+60*(1-q)
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        d.line((cx,cy,x,y),fill=(*CRIMSON,int(160*(1-q))),width=2)
    seal(im,"DREAM FORGETTING","the dream fades upon waking — the veil between worlds closes")

def vis_response(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,VIOLET)
    d=ImageDraw.Draw(im)
    for i in range(3):
        a=(i-1)*.7+t*.1; qc=clamp(q*3-i*.15)
        if qc<=0: continue
        x=cx+math.cos(a)*100*qc; y=cy+math.sin(a)*100*qc
        col=[GOLD,CYAN,GREEN][i]
        d.arc((x-25*qc,y-25*qc,x+25*qc,y+25*qc),0,180+180*qc,fill=(*col,int(180*qc)),width=2)
    seal(im,"THE DAIMON RESPONDS","not always in the dream — sometimes in the feeling upon waking")

def vis_incubation_union(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_dream_thread(im,cx,cy,q,GOLD)
    d=ImageDraw.Draw(im)
    for i in range(12):
        a=i*math.tau/12+t*.04; qc=clamp(q*5-i*.1)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+110*qc); y=cy+math.sin(a)*(30+110*qc)*.35
        d.line((cx,cy,x,y),fill=(*mix(VIOLET,GOLD,i/11),int(170*qc)),width=3)
        glow_circle(im,x,y,6,PALE_GOLD,int(140*qc),6)
    seal(im,"DREAM AND WAKING UNITE","the incubation completes — the daimon speaks in both worlds")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"DREAM RESEARCH",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"INCUBATION TRADITION",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"SCIENCE CONFIRMS: DREAMS CAN BE DIRECTED","incubation works — the question is only how")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("DREAMS ARE ONLY NEURAL NOISE","REFUTED BY INCUBATION SUCCESS",CRIMSON),
        ("THE DAIMON ALWAYS RESPONDS","SUPPORTED — BUT MAY USE SYMBOL",GREEN),
        ("ONE NIGHT IS ENOUGH FOR INCUBATION","PERSISTENCE IS REQUIRED",CRIMSON),
        ("DREAM RECALL CAN BE TRAINED","SUPPORTED BY RESEARCH",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
            fill=(*mix(WHITE,col,.10),int(220*local)),outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DREAM INCUBATION IS A SKILL","it requires patience, practice, and persistence")

VISUALS: dict[str,Callable] = {
    "core":vis_core,"pneuma":vis_pneuma,"three":vis_three,"synesian":vis_synesian,
    "curriculum":vis_curriculum,"waking":vis_waking,"practice":vis_practice,
    "lucid":vis_lucid,"image_seed":vis_image_seed,"dream_forgetting":vis_dream_forgetting,
    "response":vis_response,"incubation_union":vis_incubation_union,
    "bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("The Core Claim","The daimon impresses images on the pneuma during sleep.",9.0,"core",{}),
    Scene("Sleep as Communication","When waking consciousness is quiet, the daimon speaks.",8.5,"core",{}),
    Scene("The Nocturnal Channel","The night is not empty. It is filled with intended images.",8.5,"core",{}),
    Scene("The Imaginative Pneuma","Shared medium between soul and daimon — the subtle body of images.",9.0,"pneuma",{}),
    Scene("The Vehicle of Dreams","The pneuma is the dream body. The daimon impresses upon it.",8.5,"pneuma",{}),
    Scene("The Subtle Medium","Not physical, not mental — the imaginal body is the bridge.",8.5,"pneuma",{}),
    Scene("Three Dream States","Dreamless, ordinary, lucid — each has a daimonic function.",8.5,"three",{}),
    Scene("The Continuum","Attention in sleep varies from total absorption to lucid awareness.",8.0,"three",{}),
    Scene("The Lucid Threshold","When you become aware in the dream, the daimon can speak directly.",8.5,"three",{}),
    Scene("The Synesian Method","A question before sleep seeds the astral body for incubation.",9.0,"synesian",{}),
    Scene("The Question is the Key","A well-formed question is already half the answer in the dream world.",8.5,"synesian",{}),
    Scene("The Seed Thought","The last thought before sleep is the first image of the dream.",8.5,"synesian",{}),
    Scene("PGM Dream Curriculum","18 spells — 6 levels from dream recall to systasis.",9.0,"curriculum",{}),
    Scene("Level 1: Recall","Remembering dreams is the foundation. Without recall, incubation is blind.",8.5,"curriculum",{}),
    Scene("Level 6: Systasis","The goal: entering the dream state consciously while retaining full awareness.",9.5,"curriculum",{}),
    Scene("The Egg Ritual as Waking Dream","Entering the dream state consciously — the systasis.",9.0,"waking",{}),
    Scene("The Luminous Egg","Encased in light, you descend into the dream world with full awareness.",9.0,"waking",{}),
    Scene("The Threshold","The egg is the boundary between waking and dreaming — you cross it consciously.",8.5,"waking",{}),
    Scene("Daily Practice","Write, place under pillow, listen. The discipline of incubation.",8.5,"practice",{}),
    Scene("The Dream Journal","The most important tool. Without recording, the message is lost.",8.0,"practice",{}),
    Scene("Consistency","The daimon responds to regularity. Each night builds on the last.",8.0,"practice",{}),
    Scene("Lucidity Arises","The dreamer realizes: this is a dream. The daimon smiles.",8.5,"lucid",{}),
    Scene("The Awakening Within","To become lucid is to meet the daimon on its own ground.",8.5,"lucid",{}),
    Scene("The Smile","When you realize you are dreaming, the entire dream responds.",8.5,"lucid",{}),
    Scene("The Image Seed","A single image planted before sleep. The daimon grows it into a dream.",9.0,"image_seed",{}),
    Scene("The Power of One Image","One image is enough. The daimon unfolds it into a complete narrative.",8.5,"image_seed",{}),
    Scene("The Symbolic Language","The daimon speaks in symbols because symbols carry more meaning than words.",8.5,"image_seed",{}),
    Scene("Dream Forgetting","The dream fades upon waking. The veil between worlds closes.",8.0,"dream_forgetting",{}),
    Scene("The Fading","Each moment after waking, the dream recedes. The recall window is brief.",8.0,"dream_forgetting",{}),
    Scene("The Discipline of Recall","Recording immediately trains the dream to be remembered.",8.0,"dream_forgetting",{}),
    Scene("The Daimon Responds","Not always in the dream — sometimes in the feeling upon waking.",8.5,"response",{}),
    Scene("The Morning Mood","The dream may fade, but its emotional tone remains. That tone is the message.",8.5,"response",{}),
    Scene("The Day's Guidance","The daimon's response unfolds through the day — in synchronicity and sudden knowing.",8.5,"response",{}),
    Scene("Dream and Waking Unite","The incubation completes. The daimon speaks in both worlds.",9.5,"incubation_union",{}),
    Scene("The Integrated Life","When dream guidance enters waking decisions, life becomes daimonic.",9.5,"incubation_union",{}),
    Scene("The Continuous Thread","The thread from dream to waking becomes unbroken. The daimon is always present.",9.5,"incubation_union",{}),
    Scene("Science Bridge","Dream research confirms directed dreaming and incubation are real phenomena.",8.5,"bridge",{}),
    Scene("The Laboratory","Studies show that dream content can be shaped by pre-sleep suggestion.",8.5,"bridge",{}),
    Scene("The Open Question","If dreams can be directed, what is directing them? The question opens into the daimonic.",9.0,"bridge",{}),
    Scene("Caution","Dream incubation is a skill. It requires patience, practice, and persistence.",8.5,"caution",{}),
    Scene("Not Instant","The daimon does not always respond on the first night. Persistence is the key.",8.0,"caution",{}),
    Scene("Interpretation","Not every dream is a daimonic message. Discernment is part of the practice.",8.5,"caution",{}),
    Scene("Return","The dream-thread weaves through every scene — from daimon to sleeper.",8.0,"core",{}),
    Scene("Closing","The daimon speaks in dreams. The pneuma is the medium. The question is the seed. Nightly practice opens the channel. And when dream and waking unite, the daimon is no longer a visitor — it is who you have become.",10.0,"incubation_union",{}),
]

def render_frame(scene,fi,fc,w,h,seed):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=field(w,h,seed); VISUALS[scene.visual](im,u,t,scene.params); border(im)
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
    o=OUTPUT/"dream_incubation.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; recs=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); recs.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"the daimon speaks in dreams","subtitle":"Synesius and the PGM dream curriculum",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"dream-thread from daimon to sleeper",
        "visual_arc":["core","pneuma","synesian","curriculum","incubation","union"],
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
