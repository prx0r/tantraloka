#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=20202

VOID=(14,16,22); DEEP=(16,18,26); WARM=(20,18,20)
CRYSTAL=(200,215,230); SILVER=(196,204,222); WHITE=(252,250,246)
PEARL=(246,243,236); GOLD=(206,166,88); GOLD_LIGHT=(246,218,144)
TEAL=(92,146,148); SLATE=(90,100,120); MIST=(160,172,192)
LAVENDER=(170,156,200); CORAL=(206,108,100); TRANSPARENT=(240,245,250)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA='/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30)
SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21)
SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3],int(a))

def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))

def draw_glow(im,xy,radius,color,alpha=145,blur=16):
    gl=layer(); d=ImageDraw.Draw(gl); x,y=xy
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))

def draw_line_glow(im,pts,color,width=3,alpha=145,blur=8):
    gl=layer(); d=ImageDraw.Draw(gl)
    d.line(pts,fill=rgba(color,alpha),width=max(1,width*3),joint='curve')
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts,fill=rgba(color,min(255,alpha+70)),width=width,joint='curve')

def partial_polyline(points,amount):
    amount=clamp(amount)
    if amount<=0: return []
    if amount>=1: return points
    f=amount*(len(points)-1); idx=int(f); frac=f-idx; out=list(points[:idx+1])
    if idx+1<len(points): a,b=points[idx],points[idx+1]; out.append((lerp(a[0],b[0],frac),lerp(a[1],b[1],frac)))
    return out

def bezier(p0,p1,p2,p3,n=100):
    pts=[]
    for i in range(n):
        t=i/(n-1); u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def draw_rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=2*math.pi*i/8; x=cx+math.cos(a)*r*0.62; y=cy+math.sin(a)*r*0.62
        d.ellipse((x-r*0.42,y-r*0.42,x+r*0.42,y+r*0.42),fill=rgba(outer,145),outline=rgba(inner,180),width=1)
    d.ellipse((cx-r*0.42,cy-r*0.42,cx+r*0.42,cy+r*0.42),fill=rgba(inner,120),outline=rgba(outer,220),width=2)

def border(im):
    d=ImageDraw.Draw(im)
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(CRYSTAL,SILVER,.5),60),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(CRYSTAL,SILVER,.3),35),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,TEAL,GOLD)

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,14,20,200),outline=rgba(mix(CRYSTAL,SILVER,.4),35),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.2))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,CRYSTAL,.5))

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.0)); c=mix(CRYSTAL,SILVER,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(10,35))))
    im.alpha_composite(ov)

def sunya_ground(seed,bg,glow_col,intensity=0.4):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*2.5*intensity+fine[...,None]*0.7*intensity
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*16,0,22)[...,None]
    if glow_col:
        g=np.exp(-(((xx-W*0.48)/(W*0.28))**2+((yy-H*0.40)/(H*0.22))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.03
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(sunya_ground(fs,VOID,CRYSTAL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'emptiness — a word that sounds like absence',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'but means capacity',font=TERM_FONT,fill=mix(CRYSTAL,GOLD_LIGHT,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy),int(10+40*prog),mix(CRYSTAL,GOLD_LIGHT,.2),int(100*prog),20)
    d.ellipse((cx-60,cy-30,cx+60,cy+30),outline=rgba(mix(CRYSTAL,SILVER,.7),int(180*prog)),width=2)
    d.ellipse((cx-50,cy-20,cx+50,cy+20),outline=rgba(mix(CRYSTAL,SILVER,.4),int(120*prog)),width=1)
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        draw_glow(im,(cx,cy),15,mix(GOLD_LIGHT,WHITE,.5),int(150*p),14)
        d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=rgba(WHITE,int(255*p)))
    d.text((640,480),'a cup must be hollow to hold water. emptiness is what allows.',font=SUB_FONT,fill=mix(MIST,CRYSTAL,.5),anchor='mm')

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(sunya_ground(fs,DEEP,mix(CRYSTAL,GOLD,.2),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'whatever arises dependently is empty',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'that is dependently designated, and is the middle way',font=SMALL_FONT,fill=mix(CRYSTAL,GOLD_LIGHT,.3),anchor='mm')
    d.text((cx,145),'(mūlamadhyamakakārikā 24:18)',font=TINY_FONT,fill=mix(SLATE,CRYSTAL,.5),anchor='mm')
    prog=ease_in_out(t)
    for i in range(5):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        x=cx-120+i*60
        d.ellipse((x-6,i*12+180-6,x+6,i*12+180+6),fill=rgba(mix(GOLD_LIGHT,CRYSTAL,i/5),int(180*p)))
        if i>0:
            draw_line_glow(im,[(cx-120+(i-1)*60,(i-1)*12+180),(x,i*12+180)],mix(GOLD,CRYSTAL,.5),1,50,3)
    d.text((640,475),'dependent arising: a flame passes from wick to wick',font=SUB_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(sunya_ground(fs,VOID,mix(CRYSTAL,TEAL,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'time is a relation between events',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'not a container in which events happen',font=TERM_FONT,fill=mix(CRYSTAL,TEAL,.5),anchor='mm')
    prog=ease_in_out(t)
    pts=bezier((200,380),(400,280),(600,360),(800,280),80)
    reveal=partial_polyline(pts,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,mix(CRYSTAL,GOLD_LIGHT,.4),2,90,6)
    for i in range(4):
        x=200+i*200
        d.ellipse((x-4,360-4,x+4,360+4),fill=rgba(mix(GOLD,TEAL,i/4),200))
        d.text((x,375),['past','present','future','now'][i],font=TINY_FONT,fill=mix(CRYSTAL,PEARL,.4),anchor='mm')
    d.text((640,485),'none fixed. none independent. all real.',font=SUB_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(sunya_ground(fs,WARM,mix(CRYSTAL,GOLD,.2),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'two truths',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the same ocean — waves, water, h2o',font=TERM_FONT,fill=mix(CRYSTAL,GOLD,.5),anchor='mm')
    d.text((cx,145),'ultimate and conventional — two perspectives on one reality',font=SMALL_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(3):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        x=320+i*300; y=cy+40
        d.ellipse((x-40,y-25,x+40,y+25),outline=rgba(mix(CRYSTAL,GOLD,i/3),int(170*p)),width=2)
        d.text((x,y),['waves','water','h\u2082o'][i],font=SMALL_FONT,fill=rgba(mix(CRYSTAL,PEARL,i/3),int(200*p)),anchor='mm')
        if i>0:
            draw_line_glow(im,[(x-80,y),(x-40,y)],mix(CRYSTAL,GOLD,.4),1,50,3)
    d.text((640,480),'it does not hide behind the visible. it stands open.',font=SUB_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(sunya_ground(fs,DEEP,mix(CRYSTAL,SILVER,.5),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'emptiness itself is empty',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the ladder must be kicked away',font=TERM_FONT,fill=mix(CRYSTAL,SILVER,.6),anchor='mm')
    d.text((cx,150),'do not mistake the finger for the moon',font=SMALL_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,380),30,mix(GOLD_LIGHT,CRYSTAL,.5),int(80*prog),16)
    d.ellipse((cx-10,370,cx+10,390),fill=rgba(WHITE,int(200*prog)))
    ladder=bezier((640,260),(620,300),(660,320),(640,380),60)
    reveal=partial_polyline(ladder,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,mix(CRYSTAL,GOLD,.4),3,110,7)
    for i in range(5):
        y=280+i*20
        d.line((int(620+20*prog-i*2),y,int(660-20*prog+i*2),y),fill=rgba(mix(CRYSTAL,GOLD,.3),int(120*prog)),width=1)

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(sunya_ground(fs,VOID,mix(CRYSTAL,TEAL,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'no distinction between sa\u1e43s\u0101ra and nirv\u0101\u1e47a',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'the limit of nirv\u0101\u1e47a is the limit of sa\u1e43s\u0101ra',font=TERM_FONT,fill=mix(CRYSTAL,TEAL,.5),anchor='mm')
    d.text((cx,145),'(m\u016blamadhyamakak\u0101rik\u0101 25:19-20)',font=TINY_FONT,fill=mix(SLATE,CRYSTAL,.5),anchor='mm')
    prog=ease_in_out(t)
    d.line((200,300,1080,300),fill=rgba(mix(SLATE,CRYSTAL,.3),120),width=2)
    d.text((250,280),'sa\u1e43s\u0101ra',font=TINY_FONT,fill=mix(SLATE,TEAL,.4),anchor='mm')
    d.text((1030,280),'nirv\u0101\u1e47a',font=TINY_FONT,fill=mix(TEAL,GOLD,.5),anchor='mm')
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        for i in range(30):
            x=lerp(300,980,i/30)
            y=300+30*math.sin(i*0.8+t*2)*p
            d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(mix(CRYSTAL,GOLD_LIGHT,.3),int(80*p)))
        d.line((200,300,1080,300),fill=rgba(mix(GOLD,WHITE,.5),int(180*p)),width=3)
    d.text((640,480),'nirv\u0101\u1e47a is not a place — it is the moment you stop running',font=SUB_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(sunya_ground(fs,WARM,mix(CRYSTAL,CORAL,.2),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'a man dreaming of being chased',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'wakes up. the chasing stops.',font=TERM_FONT,fill=mix(CRYSTAL,CORAL,.4),anchor='mm')
    d.text((cx,145),'he saw through the dream — the boundary was itself a construction',font=SMALL_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-60,cy-30,cx+60,cy+50),outline=rgba(mix(SLATE,CRYSTAL,.3),150),width=2)
    d.text((cx,cy+10),'dream',font=SMALL_FONT,fill=mix(SLATE,CRYSTAL,.3),anchor='mm')
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        d.ellipse((cx-80,cy-50,cx+80,cy+70),outline=rgba(mix(CRYSTAL,GOLD_LIGHT,.5),int(160*p)),width=2)
        draw_glow(im,(cx,cy+10),25,mix(GOLD_LIGHT,WHITE,.5),int(120*p),16)
        d.ellipse((cx-10,cy,cx+10,cy+20),fill=rgba(WHITE,int(255*p)))
        d.text((cx,cy+50),'awake',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(sunya_ground(fs,VOID,mix(CRYSTAL,LAVENDER,.2),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'if you had a fixed, permanent self',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'you could never truly meet another',font=TERM_FONT,fill=mix(CRYSTAL,LAVENDER,.5),anchor='mm')
    d.text((cx,145),'you could only collide — two billiard balls in the dark',font=SMALL_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(2):
        dx=lerp(80,0,prog)*(1 if i==0 else -1)
        x=cx+dx
        col=mix(CRYSTAL,CORAL if i==0 else TEAL,.3)
        d.ellipse((x-25,cy+15,x+25,cy+65),outline=rgba(col,int(180*prog)),width=2)
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        draw_glow(im,(cx,cy+40),20,mix(GOLD_LIGHT,WHITE,.5),int(140*p),14)
        d.ellipse((cx-8,cy+32,cx+8,cy+48),fill=rgba(WHITE,int(255*p)))
        d.text((cx,cy+80),'meeting',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,int(200*p)),anchor='mm')

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(sunya_ground(fs,WARM,mix(CRYSTAL,GOLD,.2),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,85),'the cup is empty — that is why it can hold wine',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'you are empty — that is why you can hold the whole universe',font=TERM_FONT,fill=mix(CRYSTAL,GOLD,.5),anchor='mm')
    d.text((cx,150),'you are not a thing. you are a verb.',font=SMALL_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+20),int(10+50*prog),mix(CRYSTAL,GOLD_LIGHT,.3),int(130*prog),30)
    d.ellipse((cx-70,cy-30,cx+70,cy+70),outline=rgba(mix(CRYSTAL,GOLD,.5),int(180*prog)),width=2)
    d.ellipse((cx-55,cy-15,cx+55,cy+55),outline=rgba(mix(CRYSTAL,GOLD,.3),int(120*prog)),width=1)
    if prog>0.7:
        p=clamp((prog-0.7)*3.3)
        d.ellipse((cx-15,cy+5,cx+15,cy+35),fill=rgba(mix(GOLD_LIGHT,WHITE,.5),int(200*p)))
        for i in range(12):
            a=i*2*math.pi/12; r=100+40*p
            x=cx+math.cos(a)*r; y=cy+20+math.sin(a)*r*0.55
            draw_line_glow(im,[(cx,cy+20),(int(x),int(y))],mix(GOLD_LIGHT,CRYSTAL,i/12),1,50,4)
    d.text((640,485),'you are the space where existence touches its own hand',font=SUB_FONT,fill=mix(MIST,CRYSTAL,.4),anchor='mm')

SCENES=[
    Scene('nv01','Emptiness Is Capacity','A cup must be hollow to hold water.','Śūnyatā','','opening',['emptiness','capacity','space'],'intro','empty vessel with inner glow',6.0,sc01),
    Scene('nv02','Dependent Arising','Whatever arises dependently is empty — the middle way.','Pratītyasamutpāda','','arising',['dependent','arising','emptiness'],'doctrine','causal chain of dependent origination',8.0,sc02),
    Scene('nv03','Time Is a Relation','Not a container — a relation between events.','Kāla','','time',['time','relation','events'],'time','wave connecting past-present-future',8.0,sc03),
    Scene('nv04','Two Truths','Ultimate and conventional — one reality, two perspectives.','Satyadvaya','','truths',['ultimate','conventional','perspective'],'truths','three views of the same ocean',8.0,sc04),
    Scene('nv05','Emptiness of Emptiness','Even emptiness must be emptied — kick away the ladder.','Śūnyatā-śūnyatā','','meta',['emptiness','ladder','release'],'meta','ladder being kicked away at roof',8.0,sc05),
    Scene('nv06','No Distinction','The limit of nirvāṇa is the limit of saṃsāra.','Advaya','','nondual',['samsara','nirvana','nondual'],'nondual','boundary dissolving between two domains',8.0,sc06),
    Scene('nv07','The Dreamer Wakes','Nirvāṇa is not a place — it is the moment you stop running.','Bodhi','','awakening',['dream','waking','stopping'],'awakening','dream boundary dissolving into waking',8.0,sc07),
    Scene('nv08','Emptiness Allows Meeting','If you were fixed, you could never truly meet another.','Saṅgati','','meeting',['meeting','emptiness','openness'],'meeting','two forms meeting through transparency',8.0,sc08),
    Scene('nv09','You Are a Verb','Empty — therefore holding the whole universe.','Kriyā','','seal',['verb','space','holding'],'seal','transparent vessel containing cosmos',10.0,sc09),
]

def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    nframes=int(FPS*scene.duration)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    for i,path in enumerate(expected):
        if path.exists() and path.stat().st_size>1000: continue
        t=i/max(1,nframes-1)
        im=Image.new('RGBA',(W,H),(0,0,0,0))
        scene.draw_fn(im,t)
        dust(im,SEED+hash(scene.id)%10000+i,55)
        border(im); footer(im,scene.title,scene.subtitle,scene.term)
        im.convert('RGB').save(path,quality=95)
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
    sheet=Image.new('RGB',(4*320,rows*180),color=VOID)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Śūnyatā — Everything Is Empty',
        'source_basis':'Expansion Essay 20: "everything is empty" (Nāgārjuna, MMK) — 9 scenes.',
        'style':{'family':'crystal / transparency visualization','background':'deep void','ink':'crystal, silver-white, gold-light'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Sunyata — 9 scenes, crystal/transparency palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Sunyata Pack — crystal/silver-white/transparent palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Śūnyatā — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'emptiness_nagarjuna_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'emptiness_nagarjuna_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['emptiness_nagarjuna_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'emptiness_nagarjuna_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
