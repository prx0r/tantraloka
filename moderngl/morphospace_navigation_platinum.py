#!/usr/bin/env python3
"""
Cells Navigate Possible Forms
Levin's basal cognition in morphogenesis.
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
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_morphospace_navigation")
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


def vis_planaria(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(180*r),10)
    for i in range(8):
        a=i*math.tau/8+t*0.06; q=clamp(r*4-i*0.08)
        if q<=0: continue
        x=cx+math.cos(a)*(30+90*q); y=cy+math.sin(a)*(30+90*q)*0.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(160*q)),width=2)
    seal(im,'A FLATWORM REMEMBERS','cut it - pieces know what to become',GOLD)

def vis_field(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(40):
        a=i*math.tau/40+t*0.05; rad=30+90*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.4
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*CYAN,int(100*r)))
    glow_circle(im,cx,cy,16,CYAN,int(190*r),12)
    seal(im,'THE BIOELECTRIC FIELD','voltage carries pattern across cells',CYAN)

def vis_memory(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,12,GOLD,int(180*r),10)
    for i in range(10):
        a=i*math.tau/10+t*0.06; q=clamp(r*4-i*0.06)
        if q<=0: continue
        x=cx+math.cos(a)*(20+90*q); y=cy+math.sin(a)*(20+90*q)*0.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(140*q)),width=2)
        d.ellipse((x-5*q,y-5*q,x+5*q,y+5*q),outline=(*PALE_GOLD,int(130*q)),width=1)
    seal(im,'PATTERN MEMORY WITHOUT BRAIN','the body remembers a shape it is not wearing',GOLD)

def vis_xenobot(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(12):
        a=i*math.tau/12+t*0.06; q=clamp(r*3-i*0.06)
        if q<=0: continue
        x=cx+math.cos(a)*(30+80*q); y=cy+math.sin(a)*(30+80*q)*0.35
        d.ellipse((x-10*q,y-10*q,x+10*q,y+10*q),fill=(*mix(CYAN,GREEN,i/11),int(180*q)))
    seal(im,'XENOBOTS','cells reorganize without genetic modification',GREEN)

def vis_morphospace(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    rng=random.Random(42)
    for i in range(80):
        q=clamp(r*2-i*0.008)
        if q<=0: continue
        a=rng.uniform(0,math.tau); rad=rng.uniform(20,150)*q
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.4
        col=GOLD if rng.random()<0.3 else (CYAN if rng.random()<0.5 else PALE_SILVER)
        d.ellipse((x-3*q,y-3*q,x+3*q,y+3*q),fill=(*col,int(120*q)))
    glow_circle(im,cx,cy,12,GOLD,int(200*r),12)
    seal(im,'THE MORPHOSPACE','all possible body plans as attractors',GOLD)

def vis_agency(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(8):
        a=i*math.tau/8+t*0.05; q=clamp(r*4-i*0.1)
        if q<=0: continue
        x=cx+math.cos(a)*(30+90*q); y=cy+math.sin(a)*(30+90*q)*0.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(160*q)),width=2)
        arrow(d,(cx+(x-cx)*0.85,cy+(y-cy)*0.85),(x,y),CYAN,2,8)
    seal(im,'DIVERSE INTELLIGENCE','cells navigate, decide, communicate',CYAN)

def vis_implication(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    glow_circle(im,cx,cy,14,GOLD,int(200*r),12)
    centered_text(d,(w*0.50,h*0.20),'GENES',load_font(FONT_SANS_BOLD,int(h*0.030)),SOFT_INK)
    centered_text(d,(w*0.50,h*0.60),'FIELD',load_font(FONT_SANS_BOLD,int(h*0.030)),CYAN)
    if r>0.4:
        for i in range(3):
            x=lerp(w*0.30,w*0.70,i/2); q=clamp((r-0.4)*5-i*0.1)
            if q<=0: continue
            d.ellipse((x-6*q,cy-6*q,x+6*q,cy+6*q),fill=(*GREEN,int(150*q)))
    seal(im,'GENES ARE NOT THE BLUEPRINT','the field carries the plan',GOLD)

def vis_repair(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); mode=p.get('mode','wound')
    if mode=='wound':
        glow_circle(im,cx,cy,20,CRIMSON,int(200*r),14)
        d=ImageDraw.Draw(im)
        for i in range(8):
            a=i*math.tau/8+t*0.1; x=cx+math.cos(a)*30*(1+r); y=cy+math.sin(a)*30*(1+r)*0.4
            d.line((cx,cy,x,y),fill=(*CRIMSON,int(140*r)),width=2)
        seal(im,'WOUND IS PATTERN LOSS','injury disrupts the bioelectric map',CRIMSON)
    else:
        d=ImageDraw.Draw(im)
        for i in range(20):
            a=i*math.tau/20+t*0.04; rad=20+80*r
            x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.4
            glow_circle(im,x,y,4+3*r,GREEN,int(140*r),6)
        glow_circle(im,cx,cy,14,GREEN,int(200*r),12)
        seal(im,'REPAIR RESTORES THE FIELD','voltage returns - the body remembers',GREEN)

def vis_navigation(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    for i in range(6):
        a=i*math.tau/6+r*0.5; rad=30+90*r
        x=cx+math.cos(a)*rad; y=cy+math.sin(a)*rad*0.35
        d.line((cx,cy,x,y),fill=(*mix(CYAN,GREEN,i/5),int(160*r)),width=2)
        glow_circle(im,x,y,6+3*r,mix(CYAN,GREEN,i/5),int(150*r),7)
    glow_circle(im,cx,cy,10,GOLD,int(190*r),9)
    seal(im,'CELLS NAVIGATE POSSIBLE FORMS','by sensing the space of what they can become',GOLD)

def vis_form_cognition(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pts=[(cx+math.cos(i*math.tau/30)*(30+120*r),cy+math.sin(i*math.tau/30)*(30+120*r)*0.35) for i in range(31)]
    glow_line(im,partial(pts,r),GOLD,width=4,alpha=220,blur=14)
    for i in range(4):
        a=i*math.tau/4+r*0.5; x=cx+math.cos(a)*90*r; y=cy+math.sin(a)*90*r*0.35
        d.line((cx,cy,x,y),fill=(*CYAN,int(150*r)),width=2)
        glow_circle(im,x,y,6+3*r,CYAN,int(150*r),7)
    seal(im,'FORM IS COGNITION','every body is a thought made visible',GOLD)



def vis_landscape(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    pts=[]
    for i in range(60):
        q=i/59; x=lerp(w*0.10,w*0.90,q)
        y=cy+math.sin(q*math.tau*3+r*math.tau)*30*math.exp(-((q-0.5)/0.2)**2)
        pts.append((x,y))
    glow_line(im,partial(pts,r),CYAN,width=3,alpha=180,blur=10)
    for i in range(5):
        a=i*math.tau/5+r*0.3; q=clamp(r*3-i*0.12)
        if q<=0: continue
        x=cx+math.cos(a)*(50+90*q); y=cy+math.sin(a)*(50+90*q)*0.35
        d.line((cx,cy,x,y),fill=(*GOLD,int(150*q)),width=2)
        glow_circle(im,x,y,6+3*r,GOLD,int(150*q),7)
    seal(im,'THE LANDSCAPE OF FORM','morphospace is a terrain with valleys of stable form',GOLD)

def vis_collective_field(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    r=ease(u); rng=random.Random(42)
    for i in range(20):
        a=i*math.tau/20+t*0.05; rad=30+100*r
        x=w*0.50+math.cos(a)*rad; y=h*0.42+math.sin(a)*rad*0.40
        for j in range(5):
            aa=a+j*math.tau/5; rr=rad*0.3
            xx=x+math.cos(aa)*rr; yy=y+math.sin(aa)*rr*0.4
            d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=(*CYAN,int(100*r)))
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*mix(CYAN,GREEN,0.5+0.5*math.sin(t+i)),int(160*r)))
    seal(im,'COLLECTIVE BIOELECTRIC FIELD','cells communicate through voltage - the body is a conversation',CYAN)

def vis_target_form(im,u,t,p):
    w,h=im.size; cx,cy=w*0.50,h*0.42; r=ease(u); d=ImageDraw.Draw(im)
    rad=60+40*math.sin(t*0.8)
    d.ellipse((cx-rad*r,cy-rad*r*0.6,cx+rad*r,cy+rad*r*0.6),outline=(*GOLD,int(200*r)),width=3)
    for i in range(12):
        a=i*math.tau/12+t*0.06; q=clamp(r*3-i*0.06)
        if q<=0: continue
        x=cx+math.cos(a)*(rad+50*q); y=cy+math.sin(a)*(rad+50*q)*0.5
        d.line((cx+math.cos(a)*rad*r,cy+math.sin(a)*rad*r*0.6,x,y),fill=(*GOLD,int(140*q)),width=2)
        glow_circle(im,x,y,4+2*q,PALE_GOLD,int(130*q),5)
    seal(im,'THE TARGET FORM','the organism navigates toward an attractor in morphospace',GOLD)

VISUALS = {
    "planaria": vis_planaria,
    "field": vis_field,
    "memory": vis_memory,
    "xenobot": vis_xenobot,
    "morphospace": vis_morphospace,
    "agency": vis_agency,
    "implication": vis_implication,
    "repair": vis_repair,
    "navigation": vis_navigation,
    "form_cognition": vis_form_cognition,
}


SCENES = [
    Scene("A Flatworm Remembers", "Cut it - pieces know what to become. The field remembers the whole.", 7.0, "planaria", {}),
    Scene("The Bioelectric Field", "Voltage carries pattern across cells. The body's map is electrical.", 7.5, "field", {}),
    Scene("Pattern Memory Without Brain", "The body remembers a shape it is not wearing. Memory is not only neural.", 8.0, "memory", {}),
    Scene("Xenobots", "Cells reorganize without genetic modification. Form follows field.", 7.5, "xenobot", {}),
    Scene("The Morphospace", "All possible body plans as attractors. Cells navigate the space of form.", 8.0, "morphospace", {}),
    Scene("Diverse Intelligence", "Cells navigate, decide, communicate. Basal cognition at every scale.", 7.5, "agency", {}),
    Scene("Genes Are Not the Blueprint", "The field carries the plan. Genes are the toolkit, not the architect.", 8.0, "implication", {}),
    Scene("Wound is Pattern Loss", "Injury disrupts the bioelectric map. The field flickers.", 7.0, "repair", {"mode": "wound"}),
    Scene("Repair Restores the Field", "Voltage returns. The body remembers its target shape.", 7.5, "repair", {"mode": "heal"}),
    Scene("Cells Navigate Possible Forms", "Not by instruction - by sensing the space of what they can become.", 8.5, "navigation", {}),
    Scene("Memory is Distributed", "Every cell carries a fragment of the body's self-image.", 8.0, "memory", {}),
    Scene("The Target Morphology", "A golden attractor in morphospace - the form the system seeks.", 8.0, "morphospace", {}),
    Scene("Healing is Navigation", "Wound healing is a journey across morphospace, guided by the field.", 8.5, "navigation", {}),
    Scene("Basal Cognition", "Intelligence does not begin with neurons. It begins with cells solving problems.", 9.0, "agency", {}),
    Scene("Form is Function in Space", "The shape a body takes is the solution to a problem the cells solved together.", 9.0, "navigation", {}),
    Scene("The Field Remembers", "Injury does not erase the target. The field holds the memory of wholeness.", 8.0, "memory", {}),
    Scene("Cells Solve Problems", "A cell is not a machine. It is a problem-solver with a goal.", 8.5, "agency", {}),
    Scene("Bioelectric Computation", "Voltage patterns are a computational medium. Cells compute form.", 8.5, "field", {}),
    Scene("The Body is a Democracy", "Every cell votes on the shape of the whole. Cooperation is computation.", 9.0, "agency", {}),
    Scene("Regeneration is Memory", "A salamander regrows a limb because the field remembers the arm.", 8.5, "repair", {"mode": "heal"}),
    Scene("Form is Intelligent", "The shape of a body is a solution to a problem. Form is cognition expressed.", 9.0, "navigation", {}),
    Scene("Form is Cognition", "Every body is a thought made visible. Morphospace is the mind of the cell.", 9.0, "form_cognition", {}),
    Scene("The Morphic Field", "Memory is not stored in the brain alone. The field carries the pattern.", 8.5, "morphospace", {}),
    Scene("The Field Remembers", "Injury does not erase the target. The field holds the memory of wholeness.", 8.0, "memory", {}),
    Scene("Cells Solve Problems", "A cell is not a machine. It is a problem-solver with a goal.", 8.5, "agency", {}),
    Scene("Bioelectric Computation", "Voltage patterns are a computational medium. Cells compute form.", 8.5, "field", {}),
    Scene("The Body is a Democracy", "Every cell votes on the shape of the whole. Cooperation is computation.", 9.0, "agency", {}),
    Scene("Regeneration is Memory", "A salamander regrows a limb because the field remembers the arm.", 8.5, "repair", {"mode": "heal"}),
    Scene("Form is Intelligent", "The shape of a body is a solution to a problem. Form is cognition expressed.", 9.0, "navigation", {}),
    Scene("The Morphic Field", "Memory is not stored in the brain alone. The field carries the pattern.", 8.5, "morphospace", {}),


    Scene("The Landscape of Form", "Morphospace is a terrain with valleys of stable form. Cells settle into attractors.", 8.5, "landscape", {}),
    Scene("Collective Bioelectric Field", "Cells communicate through voltage. The body is a conversation.", 8.0, "collective_field", {}),
    Scene("The Target Form", "The organism navigates toward an attractor in morphospace. Form is a destination.", 8.5, "target_form", {}),
    Scene("Every Cell Remembers", "Each cell carries the memory of the whole body. The field distributes the image.", 8.5, "memory", {}),
    Scene("Wound Healing as Navigation", "Healing is re-navigation. The cell finds its way back to the target form.", 9.0, "navigation", {}),
    Scene("The Body's Self-Image", "The bioelectric field is the body's self-representation. It is what the body thinks it is.", 9.0, "field", {}),
    Scene("Morphogenesis is Learning", "Building a body is a learning process. The organism learns its own shape.", 9.5, "landscape", {}),


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
    final=OUTPUT/"morphospace_navigation.mp4"
    subprocess.run([ffmpeg_path(),"-y","-f","concat","-safe","0","-i",str(cp),"-c","copy","-movflags","+faststart",str(final)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return final

def export_timeline():
    cursor=0.0; records=[]
    for i,s in enumerate(SCENES,1):
        item=asdict(s); item["scene_id"]=f"scene_{i:03d}"; item["start_seconds"]=round(cursor,3)
        cursor+=s.duration; item["end_seconds"]=round(cursor,3); records.append(item)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"Cells Navigate Possible Forms","scene_count":len(SCENES),"runtime_seconds":round(cursor,3),
        "shot_duration_range":[5,10],"continuity_object":"navigating particle in morphospace",
        "palette_roles":{"cyan":"bioelectric field", "gold":"target form", "green":"repair", "crimson":"wound"},
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

