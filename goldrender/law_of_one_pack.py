#!/usr/bin/env python3
from __future__ import annotations

import json,math,subprocess,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=27270

DEEP=(10,12,18); WARM=(18,16,18); NIGHT=(14,14,22)
GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246); PEARL=(246,243,236)
SILVER=(196,204,222); TEAL=(92,146,148); LAVENDER=(170,156,200); SLATE=(90,100,120); MIST=(160,172,192)

FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'; FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14); TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

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
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(GOLD,SILVER,.4),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(GOLD,SILVER,.2),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,TEAL,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(10,12,18,200),outline=rgba(mix(GOLD,SILVER,.3),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term:
        tw=d.textbbox((0,0),term,font=TERM_FONT)[2]
        d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,SILVER,.5))
def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.5)); c=mix(mix(GOLD,SILVER,.5),WHITE,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)
def lo_ground(seed,bg,glow_col,intensity=0.4):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(bg,dtype=np.float32)
    coarse=rng.normal(0,1,(44,78)).astype(np.float32); cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32); base+=carr[...,None]*2.8*intensity+fine[...,None]*0.8*intensity
    yy,xx=np.mgrid[0:H,0:W]; dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base-=np.clip((dx*dx+dy*dy)*16,0,24)[...,None]
    if glow_col:
        g=np.exp(-(((xx-W*0.48)/(W*0.30))**2+((yy-H*0.38)/(H*0.24))**2)*2.4)
        for i in range(3): base[...,i]+=g*glow_col[i]*0.035
    return Image.fromarray(np.uint8(np.clip(base,0,255)),'RGB').convert('RGBA')

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str
    mode:str; tags:list[str]; group:str; technique:str
    duration:float; draw_fn:Callable[[Image.Image,float],None]

def sc01(im,t):
    fs=SEED+int(t*9973)%100000; im.paste(lo_ground(fs,DEEP,mix(GOLD,SILVER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,110),'the universe is infinite',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,140),'infinity must be unity',font=TERM_FONT,fill=mix(GOLD,SILVER,.5),anchor='mm')
    d.text((cx,170),'many-ness is a finite concept',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+20),int(5+30*prog),mix(GOLD,WHITE,.5),int(130*prog),18)
    d.ellipse((cx-12,cy+8,cx+12,cy+32),fill=rgba(WHITE,int(220*prog)))
    for i in range(8):
        a=i*2*math.pi/8+t*0.04; r=90+60*prog
        x=cx+math.cos(a)*r; y=cy+20+math.sin(a)*r*0.55
        draw_line_glow(im,[(cx,cy+20),(int(x),int(y))],mix(GOLD,SILVER,i/8),1,50,4)

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(lo_ground(fs,WARM,mix(GOLD,TEAL,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'a room full of mirrors',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'each shows a different image',font=TERM_FONT,fill=mix(GOLD,TEAL,.5),anchor='mm')
    d.text((cx,155),'all reflecting one thing at the center',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(6):
        x=cx-150+i*60; y=cy+30
        p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        d.ellipse((x-18,y-18,x+18,y+18),outline=rgba(mix(GOLD,TEAL,i/6),int(160*p)),width=2)
    draw_glow(im,(cx,cy+30),15,mix(GOLD,WHITE,.5),100,12)
    d.ellipse((cx-6,cy+24,cx+6,cy+36),fill=rgba(WHITE,220))

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(lo_ground(fs,DEEP,mix(LAVENDER,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'there is no right or wrong',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'you are unity — you are infinity',font=TERM_FONT,fill=mix(LAVENDER,GOLD,.5),anchor='mm')
    d.text((cx,155),'you are love/light — you are',font=SMALL_FONT,fill=mix(MIST,LAVENDER,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(30):
        a=i*2*math.pi/30; r=lerp(5,170,prog)
        x=cx+math.cos(a)*r; y=cy+20+math.sin(a)*r*0.55
        col=mix(mix(GOLD,WHITE,.5),mix(LAVENDER,GOLD,.4),i/30)
        d.ellipse((x-2,y-2,x+2,y+2),fill=rgba(col,int(100+80*prog)))
    draw_glow(im,(cx,cy+20),18,mix(GOLD,WHITE,.5),100,12)
    d.ellipse((cx-7,cy+13,cx+7,cy+27),fill=rgba(WHITE,220))

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(lo_ground(fs,NIGHT,mix(GOLD,WHITE,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,95),'infinity became aware',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'this was the next step',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,155),'awareness focused infinity into infinite energy',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    r=lerp(3,200,prog)
    draw_glow(im,(cx,cy),int(r),mix(GOLD,WHITE,.5),int(200*prog),30)
    d.ellipse((cx-int(r*0.4),cy-int(r*0.3),cx+int(r*0.4),cy+int(r*0.3)),fill=rgba(WHITE,int(200*prog)))
    if prog>0.5:
        d.text((cx,cy+int(r*0.5)+20),'intelligent infinity',font=SMALL_FONT,fill=rgba(GOLD_LIGHT,180),anchor='mm')

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(lo_ground(fs,WARM,mix(TEAL,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,95),'the first and primal paradox',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'infinity invested itself in many-ness',font=TERM_FONT,fill=mix(TEAL,GOLD,.5),anchor='mm')
    d.text((cx,155),'the exploration continues infinitely in an eternal present',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(12):
        a=i*2*math.pi/12; r=150*prog
        x=cx+math.cos(a+t*0.05)*r; y=cy+25+math.sin(a+t*0.05)*r*0.55
        col=mix(TEAL,GOLD,i/12)
        draw_line_glow(im,[(cx,cy+25),(int(x),int(y))],col,1,60,4)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,180))
    draw_glow(im,(cx,cy+25),15,mix(GOLD,WHITE,.5),100,12)
    d.ellipse((cx-6,cy+19,cx+6,cy+31),fill=rgba(WHITE,220))

SCENES=[
    Scene('lo01','Infinity Is Unity','The universe is infinite — infinity must be one.','Law of One','','opening',['infinity','unity','one'],'intro','radiant center with rays',6.0,sc01),
    Scene('lo02','A Room of Mirrors','Many images — one source at the center.','Unity','','mirrors',['mirrors','many','one'],'mirrors','six mirrors reflecting one center',7.0,sc02),
    Scene('lo03','You Are Unity','No right or wrong — you are infinity.','Love/light','','identity',['unity','identity','infinity'],'identity','expanding field of light',7.0,sc03),
    Scene('lo04','Infinity Became Aware','The first event — an awakening, not an explosion.','Intelligent infinity','','awakening',['infinity','awareness','logos'],'awakening','radiance expanding from awareness',7.0,sc04),
    Scene('lo05','The Primal Paradox','Infinity chose to explore many-ness — forever.','Logos','','seal',['paradox','infinity','exploration'],'seal','radial branching mandala',8.0,sc05),
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
    sheet=Image.new('RGB',(4*320,rows*180),color=DEEP)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)
def write_metadata():
    manifest={'project':'Law of One — The One Law That Explains Everything',
        'source_basis':'Expansion Essay 27 — 5 scenes.',
        'style':{'family':'law of one / unity visualization','background':'deep void','ink':'gold, silver, teal, lavender'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Law of One — 5 scenes.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Law of One Pack\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Law of One — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')
def validate_outputs():
    combined=ROOT/'law_of_one_animation.mp4'; probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))
def make_zip():
    zpath=ROOT/'law_of_one_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['law_of_one_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'law_of_one_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()
if __name__=='__main__': render_all()
