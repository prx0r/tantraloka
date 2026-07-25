#!/usr/bin/env python3
"""
MEETING YOUR OWN DAIMON — The 5-Stage Path to the Inner Guide
Socrates, Crowley, the PGM, and the Holy Guardian Angel.

An original Platinum-house procedural visual essay.

CENTRAL CLAIM
-------------
Every person has a daimon — a higher aspect of their own being that
guides, challenges, and accompanies them through life. The daimon is
not an external entity. It is your own deeper self, experienced as other
so that relationship becomes possible.

The path to the daimon has five stages: stillness, purification, threshold,
encounter, and integration. This is the structure of every genuine
spiritual initiation.

FILM THESIS
-----------
The modern picture often runs:

I am alone → I think → I decide → I act

The daimonic picture can be staged as:

I am not alone
→ there is a voice older than my thoughts
→ I must become still to hear it
→ I must purify my attention
→ the false self must step aside
→ the encounter happens
→ two wills become one

The goal is not to contact the daimon. The goal is to become it.

HOUSE RULES
-----------
• Every shot lasts 5-10 seconds.
• Every shot performs a visible transformation.
• Clean ivory gallery field.
• No slideshow compositions.
• Sparse labels only.
• Mature frame near u=0.72.
• Continuity object: a thread of recognition — violet-gold line through every scene.
• Final reveal: the thread connects you to yourself.

OUTPUT
------
output_daimon_encounter/
  frames/
  scenes/
  daimon_encounter.mp4
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
OUTPUT = ROOT / "output_daimon_encounter"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH = 1280; DEFAULT_HEIGHT = 720; DEFAULT_FPS = 10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
SILVER=(180,187,194); CYAN=(57,156,180); GOLD=(194,156,72); PALE_GOLD=(236,219,175)
GREEN=(70,139,99); CRIMSON=(162,58,69); VIOLET=(109,83,153); PALE_VIOLET=(218,208,235)
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
def ease(t):
    t=clamp(t); return .5-.5*math.cos(math.pi*t)
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
    ImageDraw.Draw(fg).line(pts,fill=(*mix(color,WHITE,.08),min(255,alpha+25)),
        width=width,joint="curve")
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

def draw_thread(im,cx,cy,progress,color=VIOLET):
    pts=[]
    for i in range(120):
        q=i/119; a=q*math.tau*3+progress*math.tau
        x=cx-150+q*300; y=cy+math.sin(a)*(10+20*math.sin(q*math.pi))
        pts.append((x,y))
    glow_line(im,partial(pts,progress),color,3,200,10)

def draw_stages(im,cx,cy,progress,colors,count=5):
    d=ImageDraw.Draw(im)
    for i in range(count):
        a=i*math.tau/count+progress*.3
        q=clamp(progress*count-i*.12)
        if q<=0: continue
        x=cx+math.cos(a)*(50+100*q); y=cy+math.sin(a)*(50+100*q)*.35
        col=colors[i%len(colors)]
        d.line((cx,cy,x,y),fill=(*col,int(170*q)),width=3)
        glow_circle(im,x,y,8+4*q,col,int(160*q),8)


def vis_foundation(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,CYAN)
    glow_circle(im,cx,cy,14,CYAN,int(170*q),10)
    seal(im,"FOUNDATION: STILLNESS","you cannot contact the daimon until you can hear it speak")

def vis_purification(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q*.6,CYAN)
    for i in range(20):
        qc=q-i*.03
        if qc<=0: continue
        a=random.Random(i).uniform(0,math.tau)
        rad=random.Random(i+100).uniform(20,140)*qc
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.4
        d.ellipse((x-3*qc,y-3*qc,x+3*qc,y+3*qc),fill=(*PALE_CYAN,int(120*qc)))
    seal(im,"PURIFICATION: REDUCING NOISE","the daimon is always speaking — learn to hear through the static")

def vis_threshold(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,CRIMSON)
    d=ImageDraw.Draw(im)
    d.ellipse((cx-120*q,cy-80*q,cx+120*q,cy+80*q),outline=(*CRIMSON,int(180*q)),width=3)
    glow_circle(im,cx,cy,10,CRIMSON,int(160*q),9)
    seal(im,"THE THRESHOLD: EGO SUSPENSION","the false self must step aside — the I that thinks is not the I that knows")

def vis_encounter(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,VIOLET)
    glow_circle(im,cx,cy,20+10*q,VIOLET,int(200*q),14)
    glow_circle(im,cx,cy,12,GOLD,int(180*q),8)
    if q>.5:
        d=ImageDraw.Draw(im)
        centered(d,(cx,cy),"I AM YOU",font(FONT_SERIF_BOLD,int(h*.07)),
                 (*GOLD,int(200*(q-.5)/.5)))
    seal(im,"THE ENCOUNTER: RECOGNITION","the distinction dissolves — you meet the one who has always been with you")

def vis_integration(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,GREEN)
    d=ImageDraw.Draw(im)
    for i in range(3):
        qc=clamp(q*3-i*.15)
        if qc<=0: continue
        x=cx+(i-1)*w*.15
        glow_circle(im,x,cy,10+6*qc,mix(GREEN,GOLD,i/2),int(180*qc),9)
        d.line((cx,cy,x,cy),fill=(*GREEN,int(150*qc)),width=3)
    seal(im,"INTEGRATION: COMMUNION","the daimon becomes accessible — a daily companion on the inner path")

def vis_abramelin(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,VIOLET)
    d=ImageDraw.Draw(im)
    for i in range(12):
        a=i*math.tau/12+t*.05
        qc=clamp(q*3-i*.06)
        if qc<=0: continue
        x=cx+math.cos(a)*(50+90*qc); y=cy+math.sin(a)*(50+90*qc)*.35
        d.line((cx,cy,x,y),fill=(*VIOLET,int(160*qc)),width=2)
        d.ellipse((x-10*qc,y-10*qc,x+10*qc,y+10*qc),outline=(*GOLD,int(140*qc)),width=2)
    seal(im,"THE ABRAMELIN OPERATION","six-month retreat to direct vision — the classic daimon path")

def vis_samekh(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,GOLD)
    pentagram=[]
    for i in range(5):
        a=i*math.tau/5-math.pi/2
        x=cx+math.cos(a)*80*q; y=cy+math.sin(a)*80*q
        pentagram.append((x,y))
    for i in range(5):
        a,b=pentagram[i],pentagram[(i+2)%5]
        if q>.2: d.line((*a,*b),fill=(*GOLD,int(200*q)),width=2)
    seal(im,"LIBER SAMEKH","Crowley's barbarous names — the invocation of the Holy Guardian Angel")

def vis_pgm(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,VIOLET)
    d=ImageDraw.Draw(im)
    d.ellipse((cx-80*q,cy-80*q,cx+80*q,cy+80*q),outline=(*VIOLET,int(180*q)),width=3)
    glow_circle(im,cx,cy,14,GOLD,int(180*q),10)
    if q>.6:
        d.ellipse((cx-100*q,cy-100*q,cx+100*q,cy+100*q),
                  outline=(*CYAN,int(120*(q-.6)/.4)),width=2)
    seal(im,"PGM SYSTASIS","the egg ritual — meeting your own daimon in the dream body")

def vis_daimon_voice(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,VIOLET)
    d=ImageDraw.Draw(im)
    for i in range(10):
        a=i*math.tau/10+t*.07
        qc=clamp(q*4-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(30+70*qc); y=cy+math.sin(a)*(30+70*qc)*.35
        d.ellipse((x-5*qc,y-5*qc,x+5*qc,y+5*qc),fill=(*PALE_VIOLET,int(150*qc)))
    seal(im,"THE DAIMON'S VOICE","not a voice in the head — a knowing that arrives as if from outside")

def vis_two_wills(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx1,cy1=w*.35,h*.40; cx2,cy2=w*.65,h*.40; q=ease(u)
    draw_thread(im,cx1,cy1,q*.5,CRIMSON)
    draw_thread(im,cx2,cy2,q*.5,GOLD)
    if q>.3:
        pts=[]
        for i in range(60):
            f=i/59; x=lerp(cx1+60,cx2-60,f)
            y=lerp(cy1,cy2,f)+math.sin(f*math.tau*2+t)*20
            pts.append((x,y))
        glow_line(im,partial(pts,(q-.3)*1.4),PALE_GOLD,width=2,alpha=160,blur=8)
    seal(im,"TWO WILLS BECOME ONE","the personal will meets the daimonic will — the dialogue of alignment")

def vis_daily_dialogue(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    d=ImageDraw.Draw(im)
    draw_thread(im,cx,cy,q,GREEN)
    for i in range(6):
        a=i*math.tau/6+t*.06; rad=40+60*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*.35
        glow_circle(im,x,y,6,PALE_GREEN,int(140*q),6)
    seal(im,"DAILY DIALOGUE","write, listen, respond — the relationship deepens through practice")

def vis_union(im,u,t,p):
    w,h=im.size; cx,cy=w*.50,h*.40; q=ease(u)
    draw_thread(im,cx,cy,q,GOLD)
    d=ImageDraw.Draw(im)
    for i in range(8):
        a=i*math.tau/8+t*.04
        qc=clamp(q*3-i*.08)
        if qc<=0: continue
        x=cx+math.cos(a)*(20+120*qc); y=cy+math.sin(a)*(20+120*qc)*.35
        d.line((cx,cy,x,y),fill=(*mix(VIOLET,GOLD,i/7),int(170*qc)),width=3)
        glow_circle(im,x,y,7,PALE_GOLD,int(150*qc),7)
    seal(im,"THE UNION","the daimon and the self become one — you are what you sought")

def vis_bridge(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    xs=[left[0]-80,left[0],left[0]+80]
    for i,x in enumerate(xs): glow_circle(im,x,left[1],10,[VIOLET,CYAN,GREEN][i],145,8)
    for rr in range(35,150,25):
        d.ellipse((right[0]-rr,right[1]-rr*.62,right[0]+rr,right[1]+rr*.62),
                  outline=(*GOLD,int(75*q*(1-rr/170))),width=3)
    centered(d,(left[0],h*.68),"PSYCHOLOGY OF THE SELF",font(FONT_SANS_BOLD,13),CYAN)
    centered(d,(right[0],h*.68),"DAIMONIC TRADITION",font(FONT_SANS_BOLD,13),GOLD)
    glow_line(im,partial([left,(w*.50,h*.20),right],q),VIOLET,4,170,11)
    seal(im,"JUNG'S SELF, HILLMAN'S SOUL, SOCRATES' DAIMON","the same phenomenon described in different languages")

def vis_caution(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rows=[
        ("THE DAIMON IS NOT A SPIRIT GUIDE","IT IS YOUR OWN DEEPER SELF",CRIMSON),
        ("THE ENCOUNTER IS SAFE WITH PREPARATION","SUPPORTED BY TRADITION",GREEN),
        ("THE DAIMON REPLACES THE EGO","NOT SUPPORTED — IT INTEGRATES WITH IT",CRIMSON),
        ("DAILY PRACTICE IS ESSENTIAL","SUPPORTED BY ALL TRADITIONS",CYAN),
    ]
    q=ease(u)
    for i,(claim,status,col) in enumerate(rows):
        local=clamp(q*len(rows)-i); y=h*(.23+i*.13)
        d.rounded_rectangle((w*.14,y-28,w*.86,y+28),radius=14,
                            fill=(*mix(WHITE,col,.10),int(220*local)),
                            outline=(*col,int(180*local)),width=2)
        centered(d,(w*.39,y),claim,font(FONT_SANS_BOLD,14),INK)
        centered(d,(w*.74,y),status,font(FONT_SANS_BOLD,14),col)
    seal(im,"DO NOT APPROACH LIGHTLY","the daimon path is the most rewarding — and the most demanding")

VISUALS: dict[str,Callable] = {
    "foundation":vis_foundation,"purification":vis_purification,"threshold":vis_threshold,
    "encounter":vis_encounter,"integration":vis_integration,"abramelin":vis_abramelin,
    "samekh":vis_samekh,"pgm":vis_pgm,"daimon_voice":vis_daimon_voice,
    "two_wills":vis_two_wills,"daily_dialogue":vis_daily_dialogue,"union":vis_union,
    "bridge":vis_bridge,"caution":vis_caution,
}

@dataclass
class Scene:
    title:str; narration:str; duration:float; visual:str; params:dict

SCENES = [
    Scene("Foundation: Stillness","You cannot contact the daimon until you can hear it speak.",8.5,"foundation",{}),
    Scene("The First Requirement","Silence is not empty. It is the medium of the daimon's voice.",8.5,"foundation",{}),
    Scene("The Inner Quiet","When the inner noise stops, a new sound emerges.",8.0,"foundation",{}),
    Scene("Purification: Reducing Noise","The daimon is always speaking. Learn to hear through the static.",8.5,"purification",{}),
    Scene("Clearing the Channel","Desire, fear, expectation — all static. Purification is clearing the line.",8.5,"purification",{}),
    Scene("The Still Voice","It was always there. You were just too loud to hear it.",8.0,"purification",{}),
    Scene("The Threshold: Ego Suspension","The false self must step aside. The I that thinks is not the I that knows.",9.0,"threshold",{}),
    Scene("The Gatekeeper","The daimon guards the threshold. To pass, you must leave your story behind.",8.5,"threshold",{}),
    Scene("The Death Before the Meeting","Part of you must die before the daimon can be met.",8.5,"threshold",{}),
    Scene("The Encounter: Recognition","The distinction dissolves. You meet the one who has always been with you.",9.0,"encounter",{}),
    Scene("I Am You","The daimon's first words: 'I am you.' Not a separate being. Your own deeper self.",9.0,"encounter",{}),
    Scene("The Familiar Stranger","You have known this presence your whole life. Now you know its name.",8.5,"encounter",{}),
    Scene("Integration: Communion","The daimon becomes accessible — a daily companion on the inner path.",8.5,"integration",{}),
    Scene("The Ongoing Relationship","Meeting is not the end. It is the beginning of a new kind of life.",8.5,"integration",{}),
    Scene("The Two Become One","Personal will and daimonic will align. The dialogue becomes a duet.",9.0,"integration",{}),
    Scene("The Abramelin Operation","Six-month retreat to direct vision. The classic daimon path.",9.0,"abramelin",{}),
    Scene("The Sacred Retreat","Isolation from the world to meet the world within.",8.5,"abramelin",{}),
    Scene("The Six Months","Daily invocation, purification, and surrender. The structure is the technique.",8.5,"abramelin",{}),
    Scene("Liber Samekh","Crowley's barbarous names — the invocation of the Holy Guardian Angel.",8.5,"samekh",{}),
    Scene("The Barbarous Names","Words that bypass the rational mind and speak directly to the deep self.",8.0,"samekh",{}),
    Scene("The Invocation","You do not summon the daimon. You invoke your own higher nature.",8.5,"samekh",{}),
    Scene("PGM Systasis","The egg ritual. Meeting your own daimon in the dream body.",9.0,"pgm",{}),
    Scene("The Egg of Light","Encased in a luminous egg, you descend into the dream world to meet your guide.",9.0,"pgm",{}),
    Scene("The Dream Body","The pneuma carries you. The daimon waits in the imaginal realm.",8.5,"pgm",{}),
    Scene("The Daimon's Voice","Not a voice in the head — a knowing that arrives as if from outside.",8.5,"daimon_voice",{}),
    Scene("The Quality of Knowing","It is not thought. It is not feeling. It is direct knowing with a personal signature.",8.5,"daimon_voice",{}),
    Scene("Learning the Language","The daimon speaks in symbol, synchronicity, and sudden insight.",8.5,"daimon_voice",{}),
    Scene("Two Wills Become One","The personal will meets the daimonic will. The dialogue of alignment.",9.0,"two_wills",{}),
    Scene("The Conflict","At first, the two wills oppose. The personal wants safety. The daimon wants growth.",8.5,"two_wills",{}),
    Scene("The Resolution","When the two wills align, action becomes effortless and inevitable.",8.5,"two_wills",{}),
    Scene("Daily Dialogue","Write, listen, respond. The relationship deepens through practice.",8.5,"daily_dialogue",{}),
    Scene("The Journal","Writing to the daimon and receiving responses — the most practical technique.",8.5,"daily_dialogue",{}),
    Scene("Consistency","The daimon responds to regularity. Daily practice builds the bridge.",8.0,"daily_dialogue",{}),
    Scene("The Union","The daimon and the self become one. You are what you sought.",9.5,"union",{}),
    Scene("The Goal","Not contact with the daimon. Becoming the daimon.",9.5,"union",{}),
    Scene("The Integrated Life","When the union is complete, every act is daimonic. Life becomes sacred.",9.5,"union",{}),
    Scene("Science Bridge","Jung's Self, Hillman's soul, Socrates' daimon — same phenomenon, different languages.",9.0,"bridge",{}),
    Scene("The Psychological Daimon","Modern psychology describes the same reality: a deeper intelligence within.",8.5,"bridge",{}),
    Scene("The Open Question","Is the daimon intrapsychic or transpersonal? The traditions say: both.",9.0,"bridge",{}),
    Scene("Caution","The daimon path is the most rewarding — and the most demanding.",8.5,"caution",{}),
    Scene("Not a Shortcut","The daimon does not solve your problems. It shows you who lives them.",8.5,"caution",{}),
    Scene("The Commitment","Once you meet the daimon, you cannot unmeet it. The path has no return.",9.0,"caution",{}),
    Scene("Return","The thread of recognition weaves through every scene.",8.0,"encounter",{}),
    Scene("The Thread is You","The violet-gold line connects you to yourself. It was always there.",8.5,"union",{}),
    Scene("Closing","Every person has a daimon — a higher aspect of their own being. The path has five stages: stillness, purification, threshold, encounter, and integration. The goal is not to contact the daimon. The goal is to become it.",10.0,"union",{}),
]

def render_frame(scene,fi,fc,w,h,seed):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=field(w,h,seed); VISUALS[scene.visual](im,u,t,scene.params); border(im)
    return im.convert("RGB")
def ffmpeg_path():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg is required but was not found on PATH")
    return exe
def encode_scene(index,fps):
    fd=FRAMES/f"scene_{index:03d}"; o=SCENES_DIR/f"scene_{index:03d}.mp4"
    subprocess.run([ffmpeg_path(),"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(o)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def render_scene(index,scene,fps,w,h,preview):
    fd=FRAMES/f"scene_{index:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    cnt=max(2,round(scene.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(cnt*.33),int(cnt*.72),cnt-1]):
            render_frame(scene,fi,cnt,w,h,index*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(cnt):
        p=fd/f"{fi:05d}.jpg"
        if p.exists(): continue
        render_frame(scene,fi,cnt,w,h,index*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(index,fps)
def concatenate(paths):
    txt=OUTPUT/"concat.txt"; txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    o=OUTPUT/"daimon_encounter.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(o)],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return o
def export_timeline():
    cursor=0.0; records=[]
    for i,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{i:03d}"; r["start_seconds"]=round(cursor,3)
        cursor+=s.duration; r["end_seconds"]=round(cursor,3); records.append(r)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"meeting your own daimon","subtitle":"the 5-stage path to the inner guide",
        "scene_count":len(SCENES),"runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"thread of recognition — violet-gold line weaving through every scene",
        "visual_arc":["stillness","purification","threshold","encounter","integration","union"],
        "scenes":records},indent=2,ensure_ascii=False),encoding="utf-8")
    return p
def make_contact_sheet(w,h):
    tw=320; th=int(tw*h/w); cols=4; rows=math.ceil(len(SCENES)/cols); ch=th+48
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
    print(f"Timeline: {export_timeline()}"); print(f"Scenes: {len(SCENES)}"); print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError("scene out of range")
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rendered.append(r)
    if not a.no_contact_sheet: print(f"Contact sheet: {make_contact_sheet(a.width,a.height)}")
    if not a.preview: print(f"Final video: {concatenate(rendered)}")
if __name__=="__main__": main()
