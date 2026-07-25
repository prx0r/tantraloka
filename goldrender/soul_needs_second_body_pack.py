#!/usr/bin/env python3
from __future__ import annotations
import json,math,subprocess,zipfile
from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=29292
NIGHT=(14,12,20); DEEP_VIOLET=(48,36,64); VIOLET=(110,90,152)
LAVENDER=(168,152,196); PALE_GOLD=(252,244,226); GOLD=(206,166,88)
GOLD_LIGHT=(244,214,138); WHITE=(252,250,246); PEARL=(246,242,236)
SILVER=(216,222,232); SLATE=(106,118,138); MIST=(176,186,200)
TEAL=(92,146,148); CRIMSON=(154,46,60); ROSE=(192,108,130)
UMBER=(78,64,50); PARCHMENT=(244,240,232); INK=(34,38,44)
FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def rgba(c,a=255): return (*c[:3],int(a))

def ground(seed,bg=NIGHT,glow_col=None):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*3.0+fine[...,None]*0.85
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*5,0,14)[...,None]*0.6
    if glow_col:
        g=np.exp(-(((xx-W/2)/(W*.28))**2+((yy-H*.38)/(H*.24))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.035
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))
def glow(im,xy,r,color,alpha=145,blur=16):
    ov=layer(); d=ImageDraw.Draw(ov); x,y=xy
    d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(color,alpha))
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
def lineglow(im,pts,color,width=3,alpha=145,blur=8):
    ov=layer(); d=ImageDraw.Draw(ov)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(ov.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')
def partial(points,a):
    a=clamp(a); f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points): A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out
def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)
def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,80),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,60),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,10,18,200),outline=rgba(SLATE,45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term: tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(LAVENDER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,55))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; duration:float; draw_fn:Callable[[Image.Image,float],None]

def s01_second_body(im,t):
    im.paste(ground(SEED+1,NIGHT,VIOLET,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the soul needs a second body',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the ochēma-pneuma — a luminous vehicle between intellect and flesh',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    d.ellipse((cx-90,cy-30,cx+90,cy+50),outline=rgba(SLATE,int(160*prog)),width=3)
    d.ellipse((cx-70,cy-15,cx+70,cy+35),outline=rgba(VIOLET,int(140*prog)),width=2)
    glow(im,(cx,cy+10),25,LAVENDER,int(80*prog),14)
    d.ellipse((cx-8,cy+2,cx+8,cy+18),fill=rgba(WHITE,int(180*prog)))
    d.text((640,505),'a vehicle that can receive the intelligible and transmit it to the embodied',font=SUB_FONT,fill=MIST,anchor='mm')

def s02_nested_bodies(im,t):
    im.paste(ground(SEED+2,NIGHT,LAVENDER,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'nested bodies',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'a soul wearing a luminous garment',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i,r in enumerate([140,100,65,35]):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        d.ellipse((cx-r,cy-60-r*0.6,cx+r,cy-60+r*0.6),outline=rgba(mix(LAVENDER,GOLD,i/3),int(150*p)),width=3-i)
        if i==3: glow(im,(cx,cy-60),15,GOLD_LIGHT,int(120*p),12); d.ellipse((cx-6,cy-66,cx+6,cy-54),fill=rgba(WHITE,int(220*p)))
    d.text((640,505),'the vehicle is the interface through which the soul acts on matter',font=SUB_FONT,fill=MIST,anchor='mm')

def s03_colored_glass(im,t):
    im.paste(ground(SEED+3,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'light passing through colored glass',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the vehicle takes on character — shaped by life, by practice, by love',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i,c in enumerate([CRIMSON,TEAL,VIOLET,GOLD]):
        p=clamp(prog*1.5-i*0.1)
        if p<=0: continue
        x=200+i*240
        d.rectangle((x-30,cy-40,x+30,cy+20),outline=rgba(c,int(190*p)),fill=rgba(c,int(15*p)),width=2)
        if i>0:
            lineglow(im,[(x-30,cy-10),(x-240+30,cy-10)],mix(c,cols[i-1] if 'cols' in dir() else GOLD,.5),2,int(50*p),4)
    d.text((640,505),'the vehicle becomes a character — it bears the marks of how it was used',font=SUB_FONT,fill=MIST,anchor='mm')

def s04_dream_space(im,t):
    im.paste(ground(SEED+4,NIGHT,LAVENDER,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'dream-space carried between worlds',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the vehicle is the continuity between waking and sleeping, living and dying',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(8):
        a=i*2*math.pi/8+t*0.05; r=lerp(20,150,prog)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        col=mix(SLATE,LAVENDER,i/7)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,int(100*prog)))
    glow(im,(cx,cy),30,LAVENDER,int(90*prog),16)
    d.text((640,505),'the soul carries its vehicle across the threshold of death',font=SUB_FONT,fill=MIST,anchor='mm')

def s05_character(im,t):
    im.paste(ground(SEED+5,PARCHMENT,VIOLET,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the vehicle as character',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'shaped by every act — it becomes what you have made of yourself',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    d.ellipse((cx-100,cy-50,cx+100,cy+50),outline=rgba(VIOLET,int(160*prog)),width=2)
    for i in range(3):
        y=cy-20+i*30
        lineglow(im,[(cx-80,y),(cx+80,y)],mix(VIOLET,GOLD,i/2),2,int(70*prog),5)
    glow(im,(cx,cy),20,GOLD_LIGHT,int(80*prog),12)
    d.text((640,505),'the vehicle is not a second self — it is the shape the self has grown into',font=SUB_FONT,fill=UMBER,anchor='mm')

def s06_survives(im,t):
    im.paste(ground(SEED+6,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'what survives',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the vehicle carries the memory of the life lived — the character, not the accidents',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    glow(im,(cx,cy-30),30,GOLD_LIGHT,int(100*prog),18)
    d.ellipse((cx-12,cy-42,cx+12,cy-18),fill=rgba(WHITE,int(200*prog)))
    d.ellipse((cx-50,cy-60,cx+50,cy-10),outline=rgba(GOLD,int(160*prog)),width=2)
    for i in range(6):
        a=i*2*math.pi/6; r=lerp(15,80,prog)
        x=cx+math.cos(a)*r; y=cy-30+math.sin(a)*r*0.6
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,LAVENDER,i/5),int(130*prog)))
    d.text((640,505),'the form of a life is not lost — it is translated into the substance of the vehicle',font=SUB_FONT,fill=MIST,anchor='mm')

def s07_interface(im,t):
    im.paste(ground(SEED+7,NIGHT,VIOLET,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'interface between intellect and body',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the vehicle mediates — it is how the eternal touches the temporal',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(2):
        a=i*math.pi; x=cx+math.cos(a)*130
        col=[GOLD,SLATE][i]
        d.ellipse((x-35,cy-50,x+35,cy+30),outline=rgba(col,int(170*prog)),width=2)
        d.text((x,cy+40),['intelligible','sensible'][i],font=TINY_FONT,fill=rgba(col,int(180*prog)),anchor='mm')
    pts=partial([(cx-95,cy-10),(cx+95,cy-10)],prog)
    if len(pts)>1: lineglow(im,pts,VIOLET,3,int(100*prog),7)
    d.text((640,505),'the vehicle is the bridge — it partakes of both realms',font=SUB_FONT,fill=MIST,anchor='mm')

def s08_seal(im,t):
    im.paste(ground(SEED+8,NIGHT,LAVENDER,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'the soul needs a second body',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,105),'the luminous vehicle — the body the soul grows for itself',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for r,col in [(210,SLATE),(160,VIOLET),(110,LAVENDER),(60,GOLD_LIGHT)]:
        rr=r*prog
        d.ellipse((cx-rr,cy-60-rr*0.5,cx+rr,cy-60+rr*0.5),outline=rgba(col,int(120-20*(r//50))),width=2)
    glow(im,(cx,cy-60),30,GOLD_LIGHT,int(130*prog),18)
    d.ellipse((cx-12,cy-72,cx+12,cy-48),fill=rgba(WHITE,int(220*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    for i in range(16):
        a=i*2*math.pi/16+t*0.03; x=cx+math.cos(a)*185*prog; y=cy-60+math.sin(a)*125*prog
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(LAVENDER,WHITE,i/15),int(120*prog)))
    d.text((640,505),'you have been preparing your second body with every act — it is the shape of your becoming',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
    Scene('sb01','Second Body','The ochēma-pneuma between intellect and flesh.','Ochēma-pneuma','','opening',['soul','vehicle','second body'],'opening','nested ellipses',6.0,s01_second_body),
    Scene('sb02','Nested Bodies','A soul wearing a luminous garment.','Endymata','','structure',['nested','garment','luminous'],'structure','three nested ellipses with center glow',6.0,s02_nested_bodies),
    Scene('sb03','Colored Glass','The vehicle takes on character.','Chrōma','','character',['character','glass','light'],'character','four colored rectangles with light',6.0,s03_colored_glass),
    Scene('sb04','Dream Space','Continuity between waking and sleeping.','Oneiros','','dream',['dream','continuity','threshold'],'dream','orbiting points around central glow',6.0,s04_dream_space),
    Scene('sb05','Character','Shaped by every act.','Ēthos','','formation',['character','formation','shape'],'formation','oval with horizontal luminous lines',6.0,s05_character),
    Scene('sb06','What Survives','The form of a life translated into substance.','Epiōn','','survival',['survival','memory','vehicle'],'survival','luminous ellipse with rising nodes',6.0,s06_survives),
    Scene('sb07','Interface','The eternal touching the temporal.','Metaxy','','mediation',['interface','mediation','bridge'],'mediation','two poles with luminous connecting band',6.0,s07_interface),
    Scene('sb08','The Vehicle Seal','The body the soul grows for itself.','Pneuma-cakra','','seal',['vehicle','seal','becoming'],'seal','concentric rings with lavender and gold',6.0,s08_seal),
]

def render_scene(scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    nframes=int(FPS*scene.duration)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    for i,path in enumerate(expected):
        if path.exists() and path.stat().st_size>1000: continue
        t=i/max(1,nframes-1)
        im=Image.new('RGBA',(W,H),(0,0,0,0))
        scene.draw_fn(im,t)
        dust(im,SEED+hash(scene.id)%10000+i,35)
        border(im); footer(im,scene.title,scene.subtitle,scene.term)
        im.convert('RGB').save(path,quality=94)
    out=SCENES_ROOT/f'{scene.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sdir/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def make_contact_sheet():
    thumbs=[]
    for sc in SCENES:
        frame=FRAMES_ROOT/sc.id/f'frame_{int(10*sc.duration*0.72):04d}.jpg'
        if not frame.exists(): frame=FRAMES_ROOT/sc.id/'frame_0000.jpg'
        if not frame.exists(): continue
        thumbs.append(Image.open(frame).convert('RGB').resize((320,180),Image.Resampling.LANCZOS))
    rows=(len(thumbs)+3)//4
    sheet=Image.new('RGB',(4*320,rows*180),color=NIGHT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'The Soul Needs a Second Body',
        'source_basis':'Expansion Essay — the soul needs a second body, Tier 1 #5.',
        'style':{'family':'vehicle cosmography','background':'deep violet night','ink':'slate and mist','accent':'violet, lavender, gold, silver'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — The Soul Needs a Second Body\n\nVisualize the Neoplatonic ochēma-pneuma: the soul's luminous vehicle, the second body that mediates between intellect and flesh, shaped by every act.\n\n## Structure\n1. The soul needs a second body\n2. Nested bodies — the luminous garment\n3. Light through colored glass — character\n4. Dream-space between worlds\n5. The vehicle as character\n6. What survives\n7. Interface between eternal and temporal\n8. The seal: the body the soul grows for itself\n\n## Visual rules\n- Violet and lavender for the subtle vehicle.\n- Gold for the intelligible, slate for the sensible.\n- Nested ellipses for layered embodiment.\n- Luminous glow for the vehicle's radiance.\n- No anthropomorphic figures — abstract bodies of light.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — The Soul Needs a Second Body\n\n## Differentiation\nThis pack uses nested luminous ellipses and vitreous color — a vocabulary of subtle embodiment.\n\n## New symbols\n1. nested ellipses\n2. three nested ellipses with center glow\n3. four colored rectangles with light\n4. orbiting points around central glow\n5. oval with horizontal luminous lines\n6. luminous ellipse with rising nodes\n7. two poles with luminous connecting band\n8. concentric rings with lavender and gold\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# The Soul Needs a Second Body — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES: print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'soul_needs_second_body_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); make_zip()
if __name__=='__main__':
    render_all()
