#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=24240

DARK=(14,12,14); WARM=(20,16,14); NIGHT=(16,14,18)
FLAME=(220,120,40); EMBER=(200,80,30); GOLD=(206,166,88)
GOLD_LIGHT=(246,218,144); CRIMSON=(154,44,58); CORAL=(206,108,100)
AMBER=(200,150,60); WHITE=(252,250,246); PEARL=(246,243,236)
SILVER=(196,204,222); TEAL=(92,146,148); SLATE=(90,100,120)
MIST=(160,172,192); BLACKENED=(40,30,25); COOL=(200,220,230)
LAVENDER=(170,156,200)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA='/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30)
SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21)
SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)
DEVA_MED=ImageFont.truetype(FONT_DEVA,26)

def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[
    :3,
    :3,
],int(a))

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
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(FLAME,GOLD,.4),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(FLAME,GOLD,.2),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,CRIMSON,mix(FLAME,GOLD,.5))

def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,10,12,200),outline=rgba(mix(FLAME,GOLD,.3),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,FLAME,.5))

def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.5)); c=mix(mix(FLAME,EMBER,.5),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,50))))
    im.alpha_composite(ov)

def fire_ground(seed,bg,glow_col,intensity=0.5):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base+=carr[...,None]*3.0*intensity+fine[...,None]*0.9*intensity
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*16,0,24)[...,None]
    if glow_col:
        g=np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.38)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.04
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

def draw_flame(d,im,cx,cy,h,t,prog,col=None):
    col=col or mix(FLAME,GOLD,.5)
    p=clamp(prog*1.2)
    if p<=0: return
    hh=h*p
    pts=[(cx,cy-hh),(cx-25,cy-10),(cx-10,cy+10),(cx+12,cy+8),(cx+28,cy-6)]
    d.polygon(pts,fill=rgba(col,int(50*p)),outline=rgba(col,int(200*p)))
    draw_glow(im,(cx,cy-int(hh*0.3)),int(hh*0.3),mix(col,GOLD_LIGHT,.3),int(100*p),14)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(fire_ground(fs,DARK,FLAME,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the buddha gave one sermon',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'everything is on fire',font=TERM_FONT,fill=mix(FLAME,GOLD_LIGHT,.5),anchor='mm')
    prog=ease_in_out(t)
    for i in range(5):
        p=clamp(prog*1.3-i*0.1)
        if p<=0: continue
        x=cx-150+i*75
        draw_flame(d,im,x,cy+40,60+20*math.sin(t+i),t,p,mix(FLAME,AMBER,i/5))
    d.text((640,485),'the all is aflame — with passion, aversion, delusion',font=SUB_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(fire_ground(fs,WARM,EMBER,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the eye is aflame — forms are aflame',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'consciousness at the eye is aflame',font=TERM_FONT,fill=mix(EMBER,GOLD,.5),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx-80,cy+40),20,mix(FLAME,GOLD,.4),int(120*prog),12)
    d.ellipse((cx-80-25,cy+15,cx-80+25,cy+65),outline=rgba(mix(FLAME,EMBER,.6),int(180*prog)),width=2)
    draw_glow(im,(cx+80,cy+40),20,mix(FLAME,GOLD,.4),int(120*prog),12)
    d.ellipse((cx+80-25,cy+15,cx+80+25,cy+65),outline=rgba(mix(FLAME,EMBER,.6),int(180*prog)),width=2)
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        draw_line_glow(im,[(cx-55,cy+40),(cx+55,cy+40)],mix(FLAME,GOLD_LIGHT,.5),3,100,7)
    d.text((640,485),'a man who has never seen fire tries to hold a coal',font=SUB_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(fire_ground(fs,DARK,FLAME,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,240
    d.text((cx,85),'six sense-doors — every surface hot',font=TERM_FONT,fill=PEARL,anchor='mm')
    senses=['eye','ear','nose','tongue','body','intellect']
    s_cols=[mix(FLAME,GOLD,.3),mix(EMBER,GOLD,.4),mix(FLAME,AMBER,.5),mix(CRIMSON,GOLD,.3),mix(FLAME,CORAL,.5),mix(EMBER,CRIMSON,.4)]
    prog=smoothstep(0.05,0.9,t)
    for i in range(6):
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        x=200+i*150
        draw_flame(d,im,x,cy+50,40,t,p,s_cols[i])
        d.text((x,cy+80),senses[i],font=SMALL_FONT,fill=rgba(mix(s_cols[i],GOLD_LIGHT,.3),int(200*p)),anchor='mm')

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(fire_ground(fs,WARM,EMBER,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'the intellect itself is aflame',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'the thinker is as hot as the thought',font=TERM_FONT,fill=mix(EMBER,GOLD,.5),anchor='mm')
    d.text((cx,155),'the mind that thinks it can step back',font=SMALL_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')
    d.text((cx,175),'and observe the flames — is itself the hearth',font=SMALL_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+50),40,mix(FLAME,GOLD,.4),int(100*prog),20)
    d.ellipse((cx-50,cy+15,cx+50,cy+85),outline=rgba(mix(EMBER,FLAME,.6),int(160*prog)),width=2)
    draw_flame(d,im,cx-30,cy+50,50,t,prog,mix(FLAME,GOLD,.5))
    draw_flame(d,im,cx+30,cy+50,35,t,prog,mix(EMBER,GOLD,.4))

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(fire_ground(fs,DARK,mix(FLAME,EMBER,.5),0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,85),'the sequence of release',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'disenchantment → dispassion → release → gnosis',font=TERM_FONT,fill=mix(FLAME,GOLD_LIGHT,.5),anchor='mm')
    stages=['nirveda','virāga','vimutti','aññā']
    s_cols=[mix(FLAME,EMBER,.6),mix(FLAME,AMBER,.5),mix(GOLD,TEAL,.5),mix(COOL,WHITE,.7)]
    prog=smoothstep(0.05,0.9,t)
    for i in range(4):
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        x=260+i*260
        sz=18+6*math.sin(t+i)
        d.ellipse((x-sz,cy+30-sz,x+sz,cy+30+sz),outline=rgba(s_cols[i],int(180*p)),width=2)
        d.text((x,cy+65),stages[i],font=SMALL_FONT,fill=rgba(s_cols[i],int(200*p)),anchor='mm')
        if i<3:
            pts=partial_polyline([(x+sz,cy+30),(x+260-sz,cy+30)],p)
            if len(pts)>1: draw_line_glow(im,pts,mix(s_cols[i],s_cols[i+1],.5),1,60,3)

def sc06(im,t):
    fs=SEED+int(t*9973+2500)%100000; im.paste(fire_ground(fs,WARM,FLAME,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'a burning house',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'at first he tries to save the furniture',font=TERM_FONT,fill=mix(FLAME,GOLD,.5),anchor='mm')
    d.text((cx,145),'then he notices his sleeve is on fire',font=SMALL_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')
    d.text((cx,165),'he walks out. the house collapses. he does not look back.',font=SMALL_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')
    prog=ease_in_out(t)
    pts=[(cx-80,cy+50),(cx-60,cy),(cx+60,cy),(cx+80,cy+50)]
    d.polygon(pts,outline=rgba(mix(FLAME,EMBER,.6),int(180*prog)),width=2)
    if prog>0.3:
        p=clamp((prog-0.3)/0.7)
        for i in range(6):
            draw_flame(d,im,cx-60+i*24,cy+20,30+20*math.sin(t*2+i),t,p,mix(FLAME,AMBER,i/6))
    if prog>0.6:
        p2=clamp((prog-0.6)*2.5)
        d.ellipse((cx+120,cy-10,cx+150,cy+20),outline=rgba(mix(COOL,WHITE,.7),int(200*p2)),width=2)
        d.text((cx+135,cy-15),'free',font=TINY_FONT,fill=rgba(mix(COOL,WHITE,.7),int(200*p2)),anchor='mm')

def sc07(im,t):
    fs=SEED+int(t*9973+3000)%100000; im.paste(fire_ground(fs,WARM,mix(FLAME,GOLD,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,85),'the thousand-petalled lotus',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,115),'one thousand hearts stopped their churning',font=TERM_FONT,fill=mix(FLAME,GOLD_LIGHT,.5),anchor='mm')
    d.text((cx,145),'the letting go was the extinguishing. the extinguishing was the opening.',font=SMALL_FONT,fill=mix(MIST,FLAME,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(20):
        a=i*2*math.pi/20; r=lerp(10,100,prog)
        x=cx+math.cos(a)*r; y=cy+30+math.sin(a)*r*0.55
        col=mix(mix(FLAME,GOLD,.4),mix(COOL,WHITE,.5),prog)
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,int(60+120*prog)))
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        draw_glow(im,(cx,cy+30),int(15+35*p),mix(GOLD_LIGHT,WHITE,.6),int(150*p),18)
        d.ellipse((cx-12,cy+18,cx+12,cy+42),fill=rgba(WHITE,int(255*p)))

def sc08(im,t):
    fs=SEED+int(t*9973+3500)%100000; im.paste(fire_ground(fs,NIGHT,COOL,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,90),'you are the space the fire burns in',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the fire was a guest that has been burning',font=TERM_FONT,fill=mix(COOL,LAVENDER,.5),anchor='mm')
    d.text((cx,150),'your furniture for a lifetime',font=SMALL_FONT,fill=mix(MIST,COOL,.4),anchor='mm')
    d.text((cx,172),'when you see that you are the room, the guest becomes irrelevant',font=SMALL_FONT,fill=mix(MIST,COOL,.4),anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((350,210,930,380),radius=20,outline=rgba(mix(COOL,SILVER,.5),int(180*prog)),width=2)
    draw_glow(im,(cx,cy+35),int(8+20*prog),mix(COOL,GOLD_LIGHT,.4),int(100*prog),14)
    d.ellipse((cx-8,cy+27,cx+8,cy+43),fill=rgba(WHITE,int(220*prog)))
    if prog>0.4:
        p=clamp((prog-0.4)/0.6)
        draw_flame(d,im,cx,cy+30,30,t,p,mix(FLAME,COOL,.2))

def sc09(im,t):
    fs=SEED+int(t*9973+4000)%100000; im.paste(fire_ground(fs,DARK,COOL,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,95),'the seeing of the fire is its end',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'it reveals that you were never the fire',font=TERM_FONT,fill=mix(COOL,LAVENDER,.5),anchor='mm')
    d.text((cx,155),'you were the space — the fire has nothing left to hold',font=SMALL_FONT,fill=mix(MIST,COOL,.4),anchor='mm')
    prog=ease_in_out(t)
    for r in [40,80,120]:
        alpha=int(120*(1-prog))
        d.ellipse((cx-r,cy-r*0.62,cx+r,cy+r*0.62),outline=rgba(mix(FLAME,EMBER,.3),alpha),width=1)
    draw_glow(im,(cx,cy),int(8+35*prog),mix(COOL,WHITE,.7),int(150*prog),22)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,int(255*prog)))
    for i in range(16):
        a=i*2*math.pi/16; r=60+60*prog
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        draw_line_glow(im,[(cx,cy),(int(x),int(y))],mix(COOL,SILVER,i/16),1,50,4)
    d.text((640,480),'the thousand monks became what fire cannot touch',font=SUB_FONT,fill=mix(MIST,COOL,.4),anchor='mm')

SCENES=[,Scene('fs01','Everything Is on Fire','The Buddha gave one sermon: the All is aflame.','Āditta','','opening',['fire','all','burning'],'intro','five flames on dark ground',6.0,sc01)
Scene('fs02','Holding a Coal','The eye, forms, consciousness — all burning.','Sabba','','senses',['eye','fire','contact'],'senses','two burning forms with fiery connection',8.0,sc02)
Scene('fs03','Six Sense-Doors','Every surface hot — no exemption.','Āyatana','','doors',['senses','doors','burning'],'doors','six flames in a row',8.0,sc03)
Scene('fs04','The Intellect Burns','The thinker is as hot as the thought.','Mano','','intellect',['intellect','fire','hearth'],'intellect','mind as hearth with flames rising',8.0,sc04)
Scene('fs05','The Sequence','Disenchantment → dispassion → release → gnosis.','Nirveda','','path',['release','sequence','gnosis'],'path','four stations cooling from fire to clarity',8.0,sc05)
Scene('fs06','The Burning House','He stops saving the furniture — and walks out.','Āgāra','','release',['house','burning','freedom'],'release','house aflame, figure walking away cool',8.0,sc06)
Scene('fs07','The Thousand-Petalled Lotus','One thousand hearts stopped churning.','Sahasrāra','','opening',['lotus','thousand','opening'],'opening','lotus opening from fire into light',8.0,sc07)
Scene('fs08','You Are the Room','The fire was a guest. You are the space.','Ākāśa','','space',['space','witness','room'],'space','empty room with single flame at center',8.0,sc08)
Scene('fs09','What Fire Cannot Touch','The seeing of the fire is its end.','Nibbāna','','seal',['extinguishing','freedom','space'],'seal','cool radiance where fire once was',10.0,sc09)
Scene('fs01','Everything Is on Fire','The Buddha gave one sermon: the All is aflame.','Āditta','','opening',['fire','all','burning'],'intro','five flames on dark ground',6.0,sc01)
Scene('fs02','Holding a Coal','The eye, forms, consciousness — all burning.','Sabba','','senses',['eye','fire','contact'],'senses','two burning forms with fiery connection',8.0,sc02)
Scene('fs03','Six Sense-Doors','Every surface hot — no exemption.','Āyatana','','doors',['senses','doors','burning'],'doors','six flames in a row',8.0,sc03)
Scene('fs04','The Intellect Burns','The thinker is as hot as the thought.','Mano','','intellect',['intellect','fire','hearth'],'intellect','mind as hearth with flames rising',8.0,sc04)
Scene('fs05','The Sequence','Disenchantment → dispassion → release → gnosis.','Nirveda','','path',['release','sequence','gnosis'],'path','four stations cooling from fire to clarity',8.0,sc05)
Scene('fs06','The Burning House','He stops saving the furniture — and walks out.','Āgāra','','release',['house','burning','freedom'],'release','house aflame, figure walking away cool',8.0,sc06)
Scene('fs07','The Thousand-Petalled Lotus','One thousand hearts stopped churning.','Sahasrāra','','opening',['lotus','thousand','opening'],'opening','lotus opening from fire into light',8.0,sc07)
Scene('fs08','You Are the Room','The fire was a guest. You are the space.','Ākāśa','','space',['space','witness','room'],'space','empty room with single flame at center',8.0,sc08)
Scene('fs09','What Fire Cannot Touch','The seeing of the fire is its end.','Nibbāna','','seal',['extinguishing','freedom','space'],'seal','cool radiance where fire once was',10.0,sc09)
Scene('fs01','Everything Is on Fire','The Buddha gave one sermon: the All is aflame.','Āditta','','opening',['fire','all','burning'],'intro','five flames on dark ground',6.0,sc01)
Scene('fs02','Holding a Coal','The eye, forms, consciousness — all burning.','Sabba','','senses',['eye','fire','contact'],'senses','two burning forms with fiery connection',8.0,sc02)
Scene('fs03','Six Sense-Doors','Every surface hot — no exemption.','Āyatana','','doors',['senses','doors','burning'],'doors','six flames in a row',8.0,sc03)
Scene('fs04','The Intellect Burns','The thinker is as hot as the thought.','Mano','','intellect',['intellect','fire','hearth'],'intellect','mind as hearth with flames rising',8.0,sc04)
Scene('fs05','The Sequence','Disenchantment → dispassion → release → gnosis.','Nirveda','','path',['release','sequence','gnosis'],'path','four stations cooling from fire to clarity',8.0,sc05)
Scene('fs06','The Burning House','He stops saving the furniture — and walks out.','Āgāra','','release',['house','burning','freedom'],'release','house aflame, figure walking away cool',8.0,sc06)
Scene('fs07','The Thousand-Petalled Lotus','One thousand hearts stopped churning.','Sahasrāra','','opening',['lotus','thousand','opening'],'opening','lotus opening from fire into light',8.0,sc07)
Scene('fs08','You Are the Room','The fire was a guest. You are the space.','Ākāśa','','space',['space','witness','room'],'space','empty room with single flame at center',8.0,sc08)
Scene('fs09','What Fire Cannot Touch','The seeing of the fire is its end.','Nibbāna','','seal',['extinguishing','freedom','space'],'seal','cool radiance where fire once was',10.0,sc09)
    Scene('fs01','Everything Is on Fire','The Buddha gave one sermon: the All is aflame.','Āditta','','opening',['fire','all','burning'],'intro','five flames on dark ground',6.0,sc01),
    Scene('fs02','Holding a Coal','The eye, forms, consciousness — all burning.','Sabba','','senses',['eye','fire','contact'],'senses','two burning forms with fiery connection',8.0,sc02),
    Scene('fs03','Six Sense-Doors','Every surface hot — no exemption.','Āyatana','','doors',['senses','doors','burning'],'doors','six flames in a row',8.0,sc03),
    Scene('fs04','The Intellect Burns','The thinker is as hot as the thought.','Mano','','intellect',['intellect','fire','hearth'],'intellect','mind as hearth with flames rising',8.0,sc04),
    Scene('fs05','The Sequence','Disenchantment → dispassion → release → gnosis.','Nirveda','','path',['release','sequence','gnosis'],'path','four stations cooling from fire to clarity',8.0,sc05),
    Scene('fs06','The Burning House','He stops saving the furniture — and walks out.','Āgāra','','release',['house','burning','freedom'],'release','house aflame, figure walking away cool',8.0,sc06),
    Scene('fs07','The Thousand-Petalled Lotus','One thousand hearts stopped churning.','Sahasrāra','','opening',['lotus','thousand','opening'],'opening','lotus opening from fire into light',8.0,sc07),
    Scene('fs08','You Are the Room','The fire was a guest. You are the space.','Ākāśa','','space',['space','witness','room'],'space','empty room with single flame at center',8.0,sc08),
    Scene('fs09','What Fire Cannot Touch','The seeing of the fire is its end.','Nibbāna','','seal',['extinguishing','freedom','space'],'seal','cool radiance where fire once was',10.0,sc09),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DARK)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def write_metadata():
    manifest={'project':'Āditta — The Fire You\'re Already Burning In',
        'source_basis':'Expansion Essay 24: "the fire you\'re already burning in" (Buddha\'s Fire Sermon, SN 35.28) — 9 scenes.',
        'style':{'family':'fire / extinguishing visualization','background':'dark and warm','ink':'flame, ember, gold, cool relief'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Fire Sermon — 9 scenes, flame/ember/cool palette.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Fire Sermon Pack — flame/ember/gold/cool-relief palette\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Āditta — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')

def validate_outputs():
    combined=ROOT/'fire_sermon_animation.mp4'
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))

def make_zip():
    zpath=ROOT/'fire_sermon_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['fire_sermon_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')

def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'fire_sermon_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()

if __name__=='__main__':
    render_all()
