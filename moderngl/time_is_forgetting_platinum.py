#!/usr/bin/env python3
"""
Time Is Produced By Forgetting
Time as the forgetting of simultaneity.
Platinum procedural visual essay.

DESIGN CONTRACT
--------------
5-10 seconds per shot, each visibly performs the narrated operation.
Clean ivory scientific field; concept-led color.
No static slide layouts or decorative loops.
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_time_is_forgetting")
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH = 1280; DEFAULT_HEIGHT = 720; DEFAULT_FPS = 10
IVORY = (249,247,241); PAPER = (242,239,231); INK = (31,36,42); SOFT_INK = (85,91,97)
SILVER = (180,187,191); PALE_SILVER = (224,228,228)
CYAN = (55,157,178); PALE_CYAN = (194,227,233)
GOLD = (193,155,72); PALE_GOLD = (235,218,172)
CRIMSON = (164,57,69); PALE_CRIMSON = (231,198,201)
GREEN = (68,139,99); PALE_GREEN = (196,225,206)
VIOLET = (107,82,151); PALE_VIOLET = (218,208,235)
LAPIS = (56,76,124); VOID = (24,28,34); WHITE = (255,254,250)
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3
def pulse(t,speed=1.0,phase=0.0): return 0.5+0.5*math.sin(math.tau*(speed*t+phase))
def load_font(path,size):
    for c in (path,FONT_SERIF,FONT_SANS):
        try: return ImageFont.truetype(c,size)
        except OSError: pass
    return ImageFont.load_default()
def rgba_layer(size): return Image.new("RGBA",size,(0,0,0,0))
def scientific_field(w,h,seed):
    rng=np.random.default_rng(seed)
    base=np.empty((h,w,3),dtype=np.float32); base[:]=IVORY
    fine=rng.normal(0,0.95,(h,w,1)); base+=fine
    yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*0.52)/(w*0.36))**2+((yy-h*0.39)/(h*0.30))**2)*2.1)
    base[...,0]+=halo*1.5; base[...,1]+=halo*4.0; base[...,2]+=halo*5.5
    base=np.clip(base,0,255).astype(np.uint8)
    return Image.fromarray(base,"RGB").convert("RGBA")
def centered_text(draw,xy,text,font,fill=INK): draw.text(xy,text,font=font,fill=fill,anchor="mm")
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,48),width=2)
    for x,y in ((52,52),(w-52,52),(52,h-52),(w-52,h-52)):
        d.line((x-9,y,x+9,y),fill=(*CYAN,80),width=1); d.line((x,y-9,x,y+9),fill=(*CYAN,80),width=1)
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    tf=load_font(FONT_SERIF_BOLD,max(22,int(h*0.040)))
    sf=load_font(FONT_SANS,max(13,int(h*0.019)))
    centered_text(d,(w/2,h*0.875),title,tf,color)
    if subtitle: centered_text(d,(w/2,h*0.923),subtitle,sf,SOFT_INK)
def glow_line(im,points,color,width=4,alpha=210,blur=12):
    if len(points)<2: return
    gl=rgba_layer(im.size)
    ImageDraw.Draw(gl).line(points,fill=(*color,int(alpha)),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=rgba_layer(im.size)
    ImageDraw.Draw(fg).line(points,fill=(*mix(color,WHITE,0.08),min(255,int(alpha)+25)),width=width,joint="curve")
    im.alpha_composite(fg)
def glow_circle(im,x,y,r,color,alpha=170,blur=16):
    gl=rgba_layer(im.size)
    ImageDraw.Draw(gl).ellipse((x-r,y-r,x+r,y+r),fill=(*color,int(alpha)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    core=rgba_layer(im.size)
    ImageDraw.Draw(core).ellipse((x-r*0.38,y-r*0.38,x+r*0.38,y+r*0.38),fill=(*mix(color,WHITE,0.35),min(255,int(alpha)+55)))
    im.alpha_composite(core)
def arrow(draw,a,b,color=INK,width=3,head=10):
    draw.line((*a,*b),fill=color,width=width)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (-1,1):
        p=(b[0]-math.cos(ang+s*0.53)*head,b[1]-math.sin(ang+s*0.53)*head)
        draw.line((*b,*p),fill=color,width=width)
def partial(points,amount):
    amount=clamp(amount)
    if not points: return []
    if amount>=1: return list(points)
    target=amount*(len(points)-1); idx=int(target); frac=target-idx
    out=list(points[:idx+1])
    if idx+1<len(points):
        a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out


def vis_simultaneous_vis(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,20,GOLD,int(220*r),16)
    for i in range(12):
        a=i*math.tau/12+t*0.05; q=clamp(r*4-i*0.06)
        if q<=0: continue
        x=cx+math.cos(a)*(20+120*q); y=cy+math.sin(a)*(20+120*q)*0.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(160*q)),width=2)
    seal(im,'ALL MOMENTS COEXIST','the universe is a single act of consciousness',GOLD)

def vis_forgetting(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+100*r),cy+math.sin(i*math.tau/40)*(30+100*r)*0.35) for i in range(41)]
    glow_line(im,partial(pts,1-r),CRIMSON,width=3,alpha=180,blur=10)
    glow_circle(im,cx,cy,10,GOLD,int(150*(1-r)),8)
    seal(im,'FORGETTING PRODUCES SEQUENCE','when you cannot perceive all at once, time is born',CRIMSON)

def vis_spanda_pulse(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pulse_r=30+20*math.sin(t*1.5)
    glow_circle(im,cx,cy,pulse_r*(0.5+r*0.5),GOLD,int(180*r),12)
    for i in range(6):
        a=i*math.tau/6+t*0.08; rad=40+80*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(150*r)),width=2)
    seal(im,'THE PULSE OF CONSCIOUSNESS','Spanda IS time - the vibration of awareness',GOLD)

def vis_kalagrasa(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(20):
        q=clamp(r*2-i*0.03)
        if q<=0: continue
        a=i*math.tau/20+t*0.05; rad=20+100*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        d.ellipse((x-4*q,y-4*q,x+4*q,y+4*q),fill=(*CYAN,int(140*q)))
    glow_circle(im,cx,cy,14,GOLD,int(180*r),10)
    seal(im,'CONSUMING TIME','the power of time is consumed in the pulse of awareness',CYAN)

def vis_past_vis(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(3):
        q=clamp(r*3-i*0.1)
        if q<=0: continue
        x=w*(0.20+i*0.15); col=mix(SOFT_INK,GOLD,i/2)
        d.ellipse((x-12*q,cy-12*q,x+12*q,cy+12*q),fill=(*col,int(180*q)))
    seal(im,'THE PAST IS NOT GONE','hidden - recoverable, mutable',GOLD)

def vis_future_vis(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(5):
        a=i*math.tau/5+r*0.6; q=clamp(r*3-i*0.08)
        if q<=0: continue
        x=cx+math.cos(a)*(50+100*q); y=cy+math.sin(a)*(50+100*q)*0.35
        col=mix(CYAN,VIOLET,i/4); d.line((cx,cy,x,y),fill=(*col,int(160*q)),width=2)
        glow_circle(im,x,y,6+3*q,col,int(150*q),7)
    seal(im,'THE FUTURE IS NOT YET','another region of the same landscape',VIOLET)

def vis_now_vis(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,18,GOLD,int(220*r),16)
    centered_text(d,(cx,cy),'NOW',load_font(FONT_SERIF_BOLD,int(h*0.070)),(*GOLD,int(200*r)))
    for i in range(8):
        a=i*math.tau/8+t*0.06; rad=40+110*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        glow_circle(im,x,y,5+3*r,PALE_GOLD,int(140*r),6)
    seal(im,'THE ETERNAL NOW','the spacious present - all time contained in this moment',GOLD)

def vis_time_spiral(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/60*r*5)*(30+100*r),cy+math.sin(i*math.tau/60*r*5)*(30+100*r)*0.35) for i in range(61)]
    glow_line(im,partial(pts,r),GOLD,width=4,alpha=220,blur=14)
    for i in range(6):
        a=i*math.tau/6+r*0.8; rad=30+90*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(140*r)),width=2)
    seal(im,'TIME IS A SPIRAL','not a line - every moment returns transformed',CYAN)



def vis_eternal_return(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/50*r*4)*(30+120*r),cy+math.sin(i*math.tau/50*r*4)*(30+120*r)*0.35) for i in range(51)]
    glow_line(im,partial(pts,r),GOLD,width=4,alpha=220,blur=14)
    for i in range(8):
        a=i*math.tau/8+t*0.05; rad=40+100*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        d.ellipse((x-4*r,y-4*r,x+4*r,y+4*r),fill=(*PALE_GOLD,int(140*r)))
        d.line((cx,cy,x,y),fill=(*CYAN,int(130*r)),width=2)
    seal(im,'ETERNAL RETURN','not that events repeat - that every moment contains all moments',GOLD)

def vis_time_wave(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for j in range(3):
        pts=[]
        for i in range(80):
            q=i/79; x=lerp(w*0.10,w*0.90,q)
            y=cy+math.sin(q*math.tau*(3+j*2)+t*2+r*math.tau)*(15+10*j)*r
            pts.append((x,y))
        glow_line(im,partial(pts,r),mix(CYAN,GOLD,j/2),width=2+j,alpha=int(160-20*j)*r,blur=8+2*j)
    seal(im,'THE WAVE OF TIME','time is not a line - it is a wave interference pattern',CYAN)


def vis_kaala(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(12):
        a=i*math.tau/12+t*0.05; q=clamp(r*6-i*0.04)
        if q<=0: continue
        x=cx+math.cos(a)*(20+120*q); y=cy+math.sin(a)*(20+120*q)*0.35
        col=mix(CYAN,CRIMSON,i/11); d.line((cx,cy,x,y),fill=(*col,int(160*q)),width=2)
        d.ellipse((x-5*q,y-5*q,x+5*q,y+5*q),fill=(*col,int(150*q)))
    glow_circle(im,cx,cy,12,GOLD,int(180*r),10)
    seal(im,'KAALA - COSMIC TIME','not the time of clocks - the time that is the pulse of consciousness itself',GOLD)

def vis_simultaneity(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/40)*(30+130*r),cy+math.sin(i*math.tau/40)*(30+130*r)*0.35) for i in range(41)]
    glow_line(im,partial(pts,r),GOLD,width=5,alpha=230,blur=16)
    for i in range(10):
        a=i*math.tau/10+t*0.04; rad=20+100*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        glow_circle(im,x,y,5+3*r,PALE_GOLD,int(150*r),6)
    centered_text(d,(w*0.50,h*0.20),'ALL AT ONCE',load_font(FONT_SERIF_BOLD,int(h*0.035)),(*GOLD,int(200*r)))
    seal(im,'SIMULTANEITY','the universe is a single act - time is the illusion of sequence',GOLD)


def vis_time_depth(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(5):
        q=clamp(r*5-i)
        if q<=0: continue
        y=lerp(h*0.22,h*0.62,i/4); col=mix(GOLD,CRIMSON,i/4)
        d.ellipse((cx-60*q,y-15*q,cx+60*q,y+15*q),outline=(*col,int(180*q)),width=2)
        centered_text(d,(cx+80*q,y),f'DEPTH {i+1}',load_font(FONT_SANS_BOLD,int(h*0.017)),col)
    seal(im,'THE DEPTHS OF TIME','time has depth - the present moment contains all moments as potential',GOLD)

VISUALS = {
    "simultaneous_vis": vis_simultaneous_vis,
    "forgetting": vis_forgetting,
    "spanda_pulse": vis_spanda_pulse,
    "kalagrasa": vis_kalagrasa,
    "past_vis": vis_past_vis,
    "future_vis": vis_future_vis,
    "now_vis": vis_now_vis,
    "time_spiral": vis_time_spiral,
}


SCENES = [
    Scene("All Moments Coexist", "The universe is a single act of consciousness.", 7.0, "simultaneous_vis", {}),
    Scene("Forgetting Produces Sequence", "When you cannot perceive all at once, time is born.", 7.5, "forgetting", {}),
    Scene("The Pulse of Consciousness", "Spanda IS time - the vibration of awareness.", 7.5, "spanda_pulse", {}),
    Scene("Consuming Time", "The power of time is consumed in the pulse of awareness.", 7.5, "kalagrasa", {}),
    Scene("The Past is Not Gone", "Hidden - recoverable, mutable.", 7.0, "past_vis", {}),
    Scene("The Future is Not Yet", "Another region of the same landscape.", 7.0, "future_vis", {}),
    Scene("The Eternal Now", "The spacious present - all time contained in this moment.", 8.5, "now_vis", {}),
    Scene("Time is a Spiral", "Not a line - every moment returns transformed.", 8.0, "time_spiral", {}),
    Scene("Forgetting is a Gift", "Without forgetting, every moment would be eternal.", 7.5, "forgetting", {}),
    Scene("Duration is Rhythm", "Not measured by clocks - felt as pulse of awareness.", 7.5, "spanda_pulse", {}),
    Scene("The Arrow of Attention", "Attention moves through simultaneity, creating sequence.", 8.0, "time_spiral", {}),
    Scene("Kalagrasa: Eating Time", "Shiva consumes time itself - liberation from sequence.", 9.0, "kalagrasa", {}),
    Scene("Past and Future Meet", "In the eternal now, past and future touch.", 8.5, "now_vis", {}),
    Scene("The Spacious Present", "When you stop making time, you find yourself in the timeless.", 9.0, "time_spiral", {}),
    Scene("Time is Forgetting", "What we call time is the memory of a unity we can no longer see.", 9.5, "forgetting", {}),
    Scene("The Spiral of Time", "Time does not move in a line. It spirals, returning at each turn.", 8.0, "time_spiral", {}),
    Scene("Simultaneity and Sequence", "Sequence is simultaneity viewed through the lens of forgetting.", 8.5, "simultaneous_vis", {}),
    Scene("The Rhythm of Awareness", "Consciousness pulses. Between pulses, time disappears.", 8.0, "spanda_pulse", {}),
    Scene("Memory as Re-creation", "Every act of memory is a new act of creation in the present.", 8.5, "past_vis", {}),
    Scene("The Future is Probable", "Not predetermined - a distribution of possibilities collapsed by attention.", 8.5, "future_vis", {}),
    Scene("Eternal Return", "Not that events repeat. That every moment contains all moments.", 9.0, "now_vis", {}),
    Scene("Time is the Pulse of Love", "What moves through time is attention. Attention is love.", 9.5, "spanda_pulse", {}),


    Scene("Eternal Return", "Not that events repeat - that every moment contains all moments.", 9.0, "eternal_return", {}),
    Scene("The Wave of Time", "Time is not a line - it is a wave interference pattern.", 8.5, "time_wave", {}),
    Scene("The Eye of the Now", "The present is not a point. It is a field of infinite depth.", 9.0, "now_vis", {}),
    Scene("Attention Creates Sequence", "Without attention, all moments coexist. Attention strings them into time.", 8.5, "spanda_pulse", {}),
    Scene("Forgetting is Compassion", "Could you bear to remember every moment? Forgetting is mercy.", 8.5, "forgetting", {}),


    Scene("The Spiral Memory", "Memory is not storage. It is a spiral that returns to the same point at a different level.", 8.5, "time_spiral", {}),
    Scene("The Pulse of Now", "Between heartbeats, between breaths, there is no time. Only the pulse of awareness.", 8.5, "spanda_pulse", {}),
    Scene("The Gift of Forgetting", "Forgetting is not a flaw. It is the condition of new experience.", 8.5, "forgetting", {}),


    Scene("Kaala - Cosmic Time","Not the time of clocks - the time that is the pulse of consciousness itself.",8.5,"kaala",{}),
    Scene("Simultaneity","The universe is a single act - time is the illusion of sequence.",9.0,"simultaneity",{}),
    Scene("The Spiral Remembers","Time spirals, and at each return, you are more awake.",9.0,"time_spiral",{}),
    Scene("Forgetting is the Gift","Without forgetting, every moment would be eternal. Forgetting is mercy.",9.5,"forgetting",{}),


    Scene("The Depths of Time","Time has depth - the present moment contains all moments as potential.",8.5,"time_depth",{}),
    Scene("The Still Point","At the center of the spiral of time is the still point. You are that point.",9.0,"now_vis",{}),
    Scene("Memory Creates Future","The way you remember the past shapes the future you can perceive.",8.5,"past_vis",{}),


    Scene("Additional Scene 1","Deepening the exploration of this theme.",8.0,"time_vis",{}),
    Scene("Additional Scene 2","Deepening the exploration of this theme.",8.0,"time_vis",{}),
    Scene("Additional Scene 3","Deepening the exploration of this theme.",8.0,"time_vis",{}),

    Scene("The Question of Time","What is time? Not a line - a question consciousness asks itself.",8.5,"spanda_pulse",{}),

]


@dataclass
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

def render_frame(scene,fi,fc,w,h,seed):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=scientific_field(w,h,seed)
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im); return im.convert("RGB")

def ffmpeg_path():
    ff=shutil.which("ffmpeg")
    if not ff: raise RuntimeError("ffmpeg required")
    return ff

def encode_scene(si,fps):
    out=SCENES_DIR/f"scene_{si:03d}.mp4"; fd=FRAMES/f"scene_{si:03d}"
    subprocess.run([ffmpeg_path(),"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def render_scene(si,scene,fps,w,h,preview):
    fd=FRAMES/f"scene_{si:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    count=max(2,round(scene.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(count*.35),int(count*.72),count-1]):
            render_frame(scene,fi,count,w,h,si*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(count):
        p=fd/f"{fi:05d}.jpg"
        if p.exists(): continue
        render_frame(scene,fi,count,w,h,si*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(si,fps)

def concat(paths):
    cp=OUTPUT/"concat.txt"; cp.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    final=OUTPUT/"time_is_forgetting.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(cp),"-c","copy","-movflags","+faststart",str(final)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return final

def export_timeline():
    cursor=0.0; records=[]
    for i,s in enumerate(SCENES,1):
        item=asdict(s); item["scene_id"]=f"scene_{i:03d}"; item["start_seconds"]=round(cursor,3)
        cursor+=s.duration; item["end_seconds"]=round(cursor,3); records.append(item)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"Time Is Produced By Forgetting","scene_count":len(SCENES),"runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],"continuity_object":"tightening spiral of forgetting",
        "palette_roles":{"gold":"simultaneity", "cyan":"sequence", "crimson":"forgetting"},
        "scenes":records},indent=2,ensure_ascii=False),encoding="utf-8")
    return p

def contact_sheet(w,h):
    tw,th=320,int(320*h/w); cols,rows=4,math.ceil(len(SCENES)/cols); ch=th+48
    sheet=Image.new("RGB",(cols*tw,rows*ch),IVORY); d=ImageDraw.Draw(sheet)
    lf=load_font(FONT_SANS_BOLD,14)
    for i,s in enumerate(SCENES,1):
        cnt=max(2,round(s.duration*DEFAULT_FPS))
        im=render_frame(s,int(cnt*.72),cnt,w,h,i*10000+72); im.thumbnail((tw,th))
        sl=i-1; x,y=(sl%cols)*tw,(sl//cols)*ch; sheet.paste(im,(x,y))
        d.text((x+9,y+th+7),f"{{i:02d}}  {{s.title}}",font=lf,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; sheet.save(p,quality=94); return p

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS); p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT); p.add_argument("--scene",type=int,default=None)
    p.add_argument("--preview",action="store_true"); p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()

def main():
    a=parse_args(); OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    tl=export_timeline(); total=sum(s.duration for s in SCENES)
    print(f"Timeline: {{tl}}"); print(f"Scenes: {{len(SCENES)}}"); print(f"Runtime: {{total/60:.2f}} min")
    if a.scene is not None:
        if not 1<=a.scene<=len(SCENES): raise ValueError(f"--scene must be 1..{{len(SCENES)}}")
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{{i:02d}}/{{len(SCENES):02d}}] {{s.title}} ({{s.duration:.1f}}s)")
        rendered.append(render_scene(i,s,a.fps,a.width,a.height,a.preview))
    final=concat(rendered); print(f"Final: {{final}}")
    if not a.no_contact_sheet: print(f"Contact sheet: {{contact_sheet(a.width,a.height)}}")
    print("Done.")

if __name__=="__main__": main()

