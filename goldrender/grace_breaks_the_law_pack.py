#!/usr/bin/env python3
from __future__ import annotations
import json,math,subprocess,zipfile
from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=30303
NIGHT=(14,14,22); WARM_VOID=(20,18,20); GOLD=(206,166,88); GOLD_LIGHT=(244,214,138)
WHITE=(252,250,246); PEARL=(246,242,236); CRIMSON=(154,46,60); CARDINAL=(186,54,70)
TEAL=(92,146,148); SLATE=(106,118,138); MIST=(176,186,200); SILVER=(216,222,232)
PARCHMENT=(244,240,232); UMBER=(78,64,50); VIOLET=(120,104,168); INK=(34,38,44)
FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'; FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14); TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

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
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CARDINAL,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(12,12,20,200),outline=rgba(SLATE,45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=MIST)
    if term: tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=GOLD_LIGHT)
def dust(im,seed,n=40):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.0))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1)); d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(15,55))))
    im.alpha_composite(ov)

@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; duration:float; draw_fn:Callable[[Image.Image,float],None]

def s01_broken_chain(im,t):
    im.paste(ground(SEED+1,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'grace breaks the law that brought you here',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'it enters where causality cannot reach',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    links=[(x,cy+10) for x in range(300,1001,100)]
    for i,(x,y) in enumerate(links):
        p=clamp(prog*1.3-i*0.06)
        if p<=0: continue
        d.rounded_rectangle((x-18,y-10,x+18,y+10),radius=6,outline=rgba(SLATE,int(150*p)),width=2)
        if i==2 and prog>0.6:
            p2=clamp((prog-0.6)*2.5)
            d.line((x-18,y-8,x+25,y-30),fill=rgba(CARDINAL,int(180*p2)),width=3)
            glow(im,(x+30,y-35),20,GOLD_LIGHT,int(100*p2),14)
            d.text((x+50,y-30),'grace',font=TINY_FONT,fill=rgba(GOLD_LIGHT,int(200*p2)),anchor='mm')
    d.text((640,505),'the law describes the structure — grace is what moves through it',font=SUB_FONT,fill=MIST,anchor='mm')

def s02_sail_and_wind(im,t):
    im.paste(ground(SEED+2,NIGHT,TEAL,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'sail and wind',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the sail does not produce the wind — it receives it',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    pts=[(cx-60,cy+20),(cx-20,cy-50),(cx+20,cy-30),(cx+60,cy+20)]
    d.polygon(pts,outline=rgba(PEARL,int(180*prog)),fill=rgba(PEARL,int(10*prog)),width=2)
    for i in range(6):
        a=-0.5+i*0.2; r=40+80*prog
        x=cx+math.cos(a)*r; y=cy+20+math.sin(a)*r*0.6
        col=mix(TEAL,GOLD_LIGHT,i/5)
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(col,int(80*prog)))
    glow(im,(cx,cy+20),20,GOLD_LIGHT,int(80*prog),14)
    d.text((640,505),'the wind is not earned — the only question is whether the sail is open',font=SUB_FONT,fill=MIST,anchor='mm')

def s03_lightning(im,t):
    im.paste(ground(SEED+3,WARM_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'lightning entering a house',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'sudden, unearned, transformative',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    if prog>0.2:
        p=clamp((prog-0.2)*1.5)
        bolt=[(cx,cy-120),(cx-30,cy-60),(cx+10,cy-30),(cx-20,cy+30),(cx,cy+60)]
        reveal=partial(bolt,p)
        if len(reveal)>1: lineglow(im,reveal,GOLD_LIGHT,5,int(180*p),12)
        glow(im,(cx,cy-120),15,GOLD_LIGHT,int(120*p),14)
    d.text((640,505),'the lightning does not ask permission — it arrives',font=SUB_FONT,fill=MIST,anchor='mm')

def s04_staircase_to_sky(im,t):
    im.paste(ground(SEED+4,NIGHT,VIOLET,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the staircase dissolving into sky',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the lower steps are solid — the higher steps become light',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(8):
        y=430-i*40; w=200-i*20; p=clamp(prog*1.3-i*0.05)
        if p<=0: continue
        col=mix(SLATE,GOLD_LIGHT,i/7)
        alpha=int(180*(1-i/8)*p)
        d.line((cx-w,y,cx+w,y),fill=rgba(col,alpha),width=3)
        if i>0:
            d.line((cx-w,y,cx-w,y+40),fill=rgba(col,int(alpha*0.5)),width=1)
            d.line((cx+w,y,cx+w,y+40),fill=rgba(col,int(alpha*0.5)),width=1)
    glow(im,(cx,90),40,GOLD_LIGHT,int(80*prog),22)
    d.text((640,505),'grace does not cancel the law — it fulfills it by going beyond it',font=SUB_FONT,fill=MIST,anchor='mm')

def s05_freedom(im,t):
    im.paste(ground(SEED+5,PARCHMENT,GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the freedom of grace',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'not the freedom to choose — the freedom to be chosen',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    for i in range(3):
        r=50+i*40*prog; alpha=int(120*(1-i/3)*prog)
        d.ellipse((cx-r,cy-60-r*0.5,cx+r,cy-60+r*0.5),outline=rgba(GOLD,alpha),width=2)
    glow(im,(cx,cy-60),20,GOLD_LIGHT,int(100*prog),16)
    d.ellipse((cx-8,cy-68,cx+8,cy-52),fill=rgba(WHITE,int(200*prog)))
    d.text((640,505),'the gift is not payment — it is not a wage — it is the nature of the source',font=SUB_FONT,fill=UMBER,anchor='mm')

def s06_receptivity(im,t):
    im.paste(ground(SEED+6,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'receptivity',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the only preparation is the willingness to receive',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(5):
        a=lerp(0.1,1.5,0.5+0.5*math.sin(t*2+i))
        x=320+i*170; y=cy+10+40*math.sin(a)*prog
        d.ellipse((x-7,y-7,x+7,y+7),fill=rgba(mix(SLATE,GOLD_LIGHT,i/4),int(100+80*prog)))
    d.text((640,505),'grace is always present — the variable is the openness of the receiver',font=SUB_FONT,fill=MIST,anchor='mm')

def s07_fulfillment(im,t):
    im.paste(ground(SEED+7,WARM_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'fulfillment is sudden silence',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'the search ends not by reaching an object but by the need dissolving',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(6):
        r=30+i*30*(1-0.5*prog); alpha=int(100*(1-i/6)*(1-prog*0.5))
        if alpha<5: continue
        d.ellipse((cx-r,cy-60-r*0.5,cx+r,cy-60+r*0.5),outline=rgba(mix(SLATE,GOLD,i/5),alpha),width=2)
    if prog>0.5:
        p=clamp((prog-0.5)*2)
        glow(im,(cx,cy-60),30,GOLD_LIGHT,int(140*p),20)
        d.ellipse((cx-12,cy-72,cx+12,cy-48),fill=rgba(WHITE,int(220*p)),outline=rgba(GOLD,int(200*p)),width=2)
    d.text((640,505),'the object was never the point — the point was the awakening of capacity',font=SUB_FONT,fill=MIST,anchor='mm')

def s08_seal(im,t):
    im.paste(ground(SEED+8,NIGHT,GOLD,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'grace breaks the law',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,105),'not by destroying it — by revealing what the law was pointing toward',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for r,col in [(210,SLATE),(160,TEAL),(110,GOLD),(60,GOLD_LIGHT)]:
        rr=r*prog
        d.ellipse((cx-rr,cy-60-rr*0.5,cx+rr,cy-60+rr*0.5),outline=rgba(col,int(120-20*(r//50))),width=2)
    glow(im,(cx,cy-60),30,GOLD_LIGHT,int(140*prog),20)
    d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=rgba(WHITE,int(220*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    for i in range(16):
        a=i*2*math.pi/16+t*0.03; x=cx+math.cos(a)*185*prog; y=cy-60+math.sin(a)*125*prog
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,TEAL,i/15),int(120*prog)))
    d.text((640,505),'the law described the container — grace is what fills it',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
    Scene('gr01','Broken Chain','Grace enters where causality cannot reach.','Śaktipāta','','opening',['grace','chain','causality'],'opening','chain with broken link',6.0,s01_broken_chain),
    Scene('gr02','Sail and Wind','Receiving what cannot be earned.','Vāta','','wind',['sail','wind','reception'],'wind','sail shape with wind particles',6.0,s02_sail_and_wind),
    Scene('gr03','Lightning','Sudden, unearned, transformative.','Vidyut','','lightning',['lightning','sudden','transformation'],'lightning','lightning bolt descending',6.0,s03_lightning),
    Scene('gr04','Staircase to Sky','Steps becoming light.','Sopāna','','ascent',['staircase','dissolution','ascent'],'ascent','staircase fading into radiance',6.0,s04_staircase_to_sky),
    Scene('gr05','Freedom of Grace','Not choosing — being chosen.','Svātantrya','','freedom',['freedom','grace','chosen'],'freedom','concentric gold rings with center',6.0,s05_freedom),
    Scene('gr06','Receptivity','The variable is the openness.','Praveśa','','receptivity',['receptivity','openness','receiver'],'receptivity','oscillating nodes along a line',6.0,s06_receptivity),
    Scene('gr07','Fulfillment','The search ends by dissolving.','Pūrti','','fulfillment',['fulfillment','silence','dissolution'],'fulfillment','contracting rings with luminous center',6.0,s07_fulfillment),
    Scene('gr08','The Grace Seal','The law described the container — grace fills it.','Śaktipāta-cakra','','seal',['grace','law','seal'],'seal','four concentric rings with gold center',6.0,s08_seal),
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
    manifest={'project':'Grace Breaks the Law That Brought You Here',
        'source_basis':'Expansion Essay — grace breaks the law, Tier 1 #6.',
        'style':{'family':'grace-reception cosmography','background':'deep night with gold radiance','ink':'slate and mist','accent':'gold, gold-light, teal, cardinal'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Grace Breaks the Law\n\nVisualize śaktipāta: grace that enters where causality cannot reach, received not earned.\n\n## Structure\n1. Grace breaks the chain of causality\n2. The sail receives the wind\n3. Lightning — sudden, unearned\n4. Staircase dissolving into sky\n5. The freedom of being chosen\n6. Receptivity — openness as preparation\n7. Fulfillment as dissolution\n8. The law described the container — grace fills it\n\n## Visual rules\n- Night fields with gold radiance.\n- Chains, sails, lightning, staircases.\n- Gold for grace, teal for the receiving field.\n- The container is never the source.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — Grace Breaks the Law\n\n## Differentiation\nThis pack uses chain, sail, lightning, and staircase imagery — grace entering from beyond the causal order.\n\n## New symbols\n1. chain with broken link\n2. sail shape with wind particles\n3. lightning bolt descending\n4. staircase fading into radiance\n5. concentric gold rings with center\n6. oscillating nodes along a line\n7. contracting rings with luminous center\n8. four concentric rings with gold center\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# Grace Breaks the Law — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES: print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'grace_breaks_the_law_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); make_zip()
if __name__=='__main__':
    render_all()
