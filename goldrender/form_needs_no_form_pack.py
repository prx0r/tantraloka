#!/usr/bin/env python3
from __future__ import annotations
import json,math,subprocess,zipfile
from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=28282
PARCHMENT=(244,240,232); PARCHMENT_LIGHT=(250,247,240); INK=(34,38,44)
UMBER=(78,64,50); GOLD=(206,166,88); GOLD_LIGHT=(244,214,138)
WHITE=(252,250,246); SILVER=(216,222,232); SLATE=(106,118,138)
MIST=(176,186,200); TEAL=(92,146,148); CRIMSON=(154,46,60)
NIGHT=(14,14,22); VIOLET=(120,104,168); SKY_BLUE=(140,170,200)
PEARL=(246,242,236); PALE_GOLD=(252,244,226)
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

def ground(seed,bg=PARCHMENT,glow_col=None):
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
    d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,90),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,70),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,55),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=UMBER)
    if term: tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=CRIMSON)
def dust(im,seed,n=35):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,55))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; duration:float; draw_fn:Callable[[Image.Image,float],None]

def s01_chora(im,t):
    im.paste(ground(SEED+1,PARCHMENT,GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'form needs a place that has no form',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'chōra — the receptacle that receives every form by possessing none',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    for i in range(5):
        r=20+i*40; alpha=int(100*(1-i/5)*prog)
        d.ellipse((cx-r,cy-60-r*0.5,cx+r,cy-60+r*0.5),outline=rgba(GOLD,alpha),width=2)
    glow(im,(cx,cy-60),20,GOLD_LIGHT,int(80*prog),16)
    d.ellipse((cx-8,cy-68,cx+8,cy-52),fill=rgba(WHITE,int(200*prog)))
    d.text((640,505),'before anything can change shape, there must be somewhere for one shape to stop and another to appear',font=SUB_FONT,fill=UMBER,anchor='mm')

def s02_three_kinds(im,t):
    im.paste(ground(SEED+2,PARCHMENT_LIGHT,VIOLET,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'three kinds',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'forms — changing things — the receptacle that receives both',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    labels=['intelligible forms','sensible things','chōra — the receptacle']
    cols=[GOLD,TEAL,VIOLET]
    for i in range(3):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        x=220+i*400; y=cy+10
        d.rounded_rectangle((x-80,y-50,x+80,y+50),radius=12,outline=rgba(cols[i],int(170*p)),fill=rgba(cols[i],int(10*p)),width=2)
        d.text((x,y),labels[i],font=SMALL_FONT,fill=rgba(cols[i],int(190*p)),anchor='mm')
    d.text((640,505),'a third kind without which changing things would have nowhere to appear',font=SUB_FONT,fill=UMBER,anchor='mm')

def s03_gold_shaped(im,t):
    im.paste(ground(SEED+3,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'like gold repeatedly shaped into different objects',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the same substance — many forms — the gold does not become the forms',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    d.ellipse((cx-80,cy-30,cx+80,cy+50),fill=rgba(GOLD,int(30*prog)),outline=rgba(GOLD,int(180*prog)),width=3)
    for i in range(4):
        a=i*math.pi/2; x=cx+math.cos(a)*100*prog; y=cy+math.sin(a)*60*prog
        d.polygon([(x-30,y-20),(x+30,y-10),(x+20,y+20),(x-25,y+15)],outline=rgba(mix(GOLD,TEAL,i/3),int(120*prog)),width=2)
    glow(im,(cx,cy+10),20,GOLD_LIGHT,int(80*prog),14)
    d.text((640,505),'the analogies circle something that cannot be pictured directly',font=SUB_FONT,fill=MIST,anchor='mm')

def s04_morphospace(im,t):
    im.paste(ground(SEED+4,PARCHMENT,TEAL,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'morphospace',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'an abstract space of possible forms',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    for i in range(20):
        u=i/19; x=lerp(150,1130,u); y=cy-40+60*math.sin(u*4+t)*prog
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(TEAL,GOLD,i/19),int(120*prog)))
    # Trajectories through morphospace
    for i in range(4):
        pts=[]
        for j in range(20):
            u=j/19; x=lerp(200,1080,u); y=cy-40+100*math.sin(u*3+i*prog)*prog
            pts.append((x,y))
        reveal=partial(pts,smooth(0.05+i*0.08,0.82,prog))
        if len(reveal)>1: lineglow(im,reveal,mix(TEAL,VIOLET,i/3),2,int(70*prog),5)
    d.text((640,505),'its dimensions represent features along which bodies can vary',font=SUB_FONT,fill=UMBER,anchor='mm')

def s05_mother_face(im,t):
    im.paste(ground(SEED+5,NIGHT,VIOLET,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'a mother without a face',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the receptacle receives by being nothing in particular',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(6):
        r=20+i*30; alpha=int(100*(1-i/6)*prog)
        d.ellipse((cx-r,cy-r*0.6,cx+r,cy+r*0.6),outline=rgba(mix(SLATE,VIOLET,i/5),alpha),width=1)
    glow(im,(cx,cy),30,VIOLET,int(80*prog),18)
    d.text((640,505),'she is not exactly empty — she is available',font=SUB_FONT,fill=MIST,anchor='mm')

def s06_form_change(im,t):
    im.paste(ground(SEED+6,PARCHMENT,GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'fire becomes air — air becomes water',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'the forms change — what receives the change cannot itself be a form',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    elements=[('fire',CRIMSON,1),('air',SKY_BLUE,2),('water',TEAL,3)]
    for lab,col,pos in elements:
        p=clamp(prog*1.5-(pos-1)*0.12)
        if p<=0: continue
        x=lerp(300,980,pos/4); y=cy+10
        d.ellipse((x-30,y-20,x+30,y+20),outline=rgba(col,int(180*p)),fill=rgba(col,int(15*p)),width=2)
        d.text((x,y),lab,font=SMALL_FONT,fill=rgba(col,int(190*p)),anchor='mm')
        if pos<3:
            x2=lerp(300,980,(pos+1)/4)
            lineglow(im,[(x+30,y),(x2-30,y)],GOLD,2,int(80*p),5)
    d.text((640,505),'the receptacle is present wherever form happens without becoming one of the forms',font=SUB_FONT,fill=UMBER,anchor='mm')

def s07_difficult_reasoning(im,t):
    im.paste(ground(SEED+7,WARM_DARK := (20,18,18),GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'known through a kind of difficult, dreamlike reasoning',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'not by clear intellectual grasp',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(12):
        a=i*2*math.pi/12+t*0.05; r=80+40*math.sin(t+i)*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(SLATE,GOLD,i/11),int(80*prog)))
    glow(im,(cx,cy),30,VIOLET,int(90*prog),18)
    d.text((640,505),'it is the condition in which sensible becoming can occur',font=SUB_FONT,fill=MIST,anchor='mm')

def s08_seal(im,t):
    im.paste(ground(SEED+8,PARCHMENT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'form needs a place that has no form',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,105),'without the receptacle — nothing could appear',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    for r,col in [(200,GOLD),(150,VIOLET),(100,TEAL),(50,SILVER)]:
        rr=r*prog
        d.ellipse((cx-rr,cy-60-rr*0.5,cx+rr,cy-60+rr*0.5),outline=rgba(col,int(120-20*(r//50))),width=2)
    glow(im,(cx,cy-60),30,GOLD_LIGHT,int(130*prog),18)
    d.ellipse((cx-12,cy-72,cx+12,cy-48),fill=rgba(WHITE,int(220*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    for i in range(16):
        a=i*2*math.pi/16+t*0.03; x=cx+math.cos(a)*180*prog; y=cy-60+math.sin(a)*120*prog
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,SILVER,i/15),int(120*prog)))
    d.text((640,505),'the receptacle makes appearance possible — by itself appearing as nothing',font=SUB_FONT,fill=UMBER,anchor='mm')

SCENES=[
    Scene('ch01','Chōra','A place that is not exactly place.','Chōra','','opening',['chora','receptacle','form'],'opening','concentric empty rings',6.0,s01_chora),
    Scene('ch02','Three Kinds','Forms, things, and the receptacle.','Tria genera','','structure',['forms','things','receptacle'],'structure','three column medallions',6.0,s02_three_kinds),
    Scene('ch03','Gold Shaped','The same substance receiving many forms.','Aurum','','analogy',['gold','forms','substance'],'analogy','gold mass with changing shapes',6.0,s03_gold_shaped),
    Scene('ch04','Morphospace','Abstract space of possible forms.','Morphos','','space',['morphospace','possible','forms'],'space','wave trajectories in abstract space',6.0,s04_morphospace),
    Scene('ch05','Mother Without a Face','Receiving by being nothing in particular.','Mater','','receptacle',['mother','receptacle','available'],'receptacle','faint expanding concentric rings',6.0,s05_mother_face),
    Scene('ch06','Element Change','Fire, air, water transforming.','Stoicheia','','transformation',['elements','change','transformation'],'transformation','three element medallions with transitions',6.0,s06_form_change),
    Scene('ch07','Difficult Reasoning','Known through dreamlike apprehension.','Logos','','knowing',['dreamlike','reasoning','grasp'],'knowing','faint orbiting points around center',6.0,s07_difficult_reasoning),
    Scene('ch08','The Form-Seal','Form needs a place that has no form.','Chōra-cakra','','seal',['form','placeless-place','seal'],'seal','concentric rings with outer gold and inner silver',6.0,s08_seal),
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
        dust(im,SEED+hash(scene.id)%10000+i,30)
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
    sheet=Image.new('RGB',(4*320,rows*180),color=PARCHMENT)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Form Needs a Place That Has No Form',
        'source_basis':'Expansion Essay — form needs a place that has no form, Tier 1 #4.',
        'style':{'family':'receptacle cosmography','background':'warm parchment','ink':'umber and slate','accent':'gold, violet, teal, silver'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Form Needs a Place That Has No Form\n\nVisualize Plato's chōra: the receptacle that makes appearance possible by itself appearing as nothing.\n\n## Structure\n1. Form needs a place that has no form\n2. Three kinds — forms, things, receptacle\n3. Like gold repeatedly reshaped\n4. Morphospace — space of possible forms\n5. A mother without a face\n6. Fire, air, water — elements transforming\n7. Difficult, dreamlike reasoning\n8. The receptacle makes appearance possible\n\n## Visual rules\n- Warm parchment ground for receptivity.\n- Concentric rings that never close — open availability.\n- Gold for the substrate, violet for the mysterious, teal for forms.\n- Negative space as primary compositional element.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Form Needs a Place\n\n## Differentiation\nThis pack uses open concentric rings and negative space — a vocabulary of availability and receptivity.\n\n## New symbols\n1. concentric empty rings\n2. three column medallions\n3. gold mass with changing shapes\n4. wave trajectories in abstract space\n5. faint expanding concentric rings\n6. three element medallions with transitions\n7. faint orbiting points around center\n8. concentric rings with outer gold and inner silver\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# Form Needs a Place That Has No Form — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES: print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'form_needs_no_form_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); make_zip()
if __name__=='__main__':
    render_all()
