#!/usr/bin/env python3
from __future__ import annotations
import json,math,subprocess,zipfile
from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=27272
NIGHT=(12,14,22); WARM_VOID=(18,16,20); PALE_FIELD=(232,228,220)
GOLD=(206,166,88); GOLD_LIGHT=(244,214,138); WHITE=(252,250,246); PEARL=(246,242,236)
CRIMSON=(154,46,60); ROSE=(192,108,130); TEAL=(92,146,148); SLATE=(106,118,138)
MIST=(176,186,200); SILVER=(216,222,232); PARCHMENT=(244,240,232); UMBER=(78,64,50)
VIOLET=(120,104,168); SKY_BLUE=(140,170,200); INK=(34,38,44)
FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17)
TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14)
TINY_FONT=ImageFont.truetype(FONT_SERIF,11)

def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
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
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(10,12,20,200),outline=rgba(SLATE,45),width=1)
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

def s01_selection(im,t):
    im.paste(ground(SEED+1,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'something is selecting your reality',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'before you know you have made a choice',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(30):
        u=i/29; x=lerp(100,1180,u); y=lerp(150,430,0.5+0.5*math.sin(u*3))
        alpha=int(60*(1-abs(u-0.5)))
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(SLATE,alpha))
    glow(im,(cx,cy),35,GOLD_LIGHT,int(120*prog),18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,int(200*prog)))
    d.text((640,505),'the universe does not simply appear — it is admitted',font=SUB_FONT,fill=MIST,anchor='mm')

def s02_field_divides(im,t):
    im.paste(ground(SEED+2,PALE_FIELD,GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'one field divides into center and edge',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'that division is the beginning of a world',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    for i in range(8):
        r=30+i*25*prog; alpha=int(100*(1-i/8)*prog)
        if alpha<5: continue
        d.ellipse((cx-r,cy-40-r*0.5,cx+r,cy-40+r*0.5),outline=rgba(GOLD,alpha),width=2)
    glow(im,(cx,cy-40),20,GOLD_LIGHT,int(100*prog),14)
    d.ellipse((cx-8,cy-48,cx+8,cy-32),fill=rgba(WHITE,int(200*prog)))
    d.text((640,505),'choose one thing — it brightens — everything else becomes background',font=SUB_FONT,fill=UMBER,anchor='mm')

def s03_prakasha_vimarsha(im,t):
    im.paste(ground(SEED+3,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'prakāśa — vimarśa',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,105),'light and reflection — together they form living awareness',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    d.ellipse((cx-140,cy-80,cx+140,cy+60),outline=rgba(GOLD,int(160*prog)),width=3)
    glow(im,(cx-50,cy-10),25,GOLD,int(100*prog),14)
    glow(im,(cx+50,cy-10),25,SILVER,int(80*prog),14)
    pts1=partial([(cx-50,cy-10),(cx-20,cy-40)],prog)
    pts2=partial([(cx+50,cy-10),(cx+20,cy+20)],prog)
    if len(pts1)>1: lineglow(im,pts1,GOLD,2,int(100*prog),5)
    if len(pts2)>1: lineglow(im,pts2,SILVER,2,int(80*prog),5)
    d.text((cx-50,cy-55),'prakāśa',font=SMALL_FONT,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+50,cy+45),'vimarśa',font=SMALL_FONT,fill=SILVER,anchor='mm')
    d.text((640,505),'light alone would reveal everything but recognize nothing',font=SUB_FONT,fill=MIST,anchor='mm')

def s04_your_name(im,t):
    im.paste(ground(SEED+4,WARM_VOID,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'your name in the crowd',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'it finds the center — every act of attention is a smaller version of this',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(25):
        u=i/24; x=lerp(120,1160,u); y=lerp(160,420,0.3+0.4*math.sin(u*5))
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(SLATE,TEAL,u),int(80)))
    if prog>0.3:
        p=clamp((prog-0.3)*1.5)
        glow(im,(cx,cy),40,GOLD_LIGHT,int(150*p),20)
        d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,int(220*p)))
        for i in range(12):
            a=i*2*math.pi/12; x=cx+math.cos(a)*60; y=cy+math.sin(a)*60
            d.ellipse((x-6,y-6,x+6,y+6),fill=rgba(GOLD_LIGHT,int(160*p)))
    d.text((640,505),'one sound comes forward — it was physically no louder than the others',font=SUB_FONT,fill=MIST,anchor='mm')

def s05_gap(im,t):
    im.paste(ground(SEED+5,WARM_VOID,VIOLET,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the gap between perceptions',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'what survives the gap is more fundamental than any content',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(3):
        y=190+i*60; p=clamp(prog*1.3-i*0.08)
        if p<=0: continue
        d.rectangle((250,y-8,1060,y+8),outline=rgba(SLATE,int(80*p)),width=1)
        d.ellipse((400,y-15,440,y+15),fill=rgba(mix(VIOLET,GOLD,i/2),int(120*p)))
        d.ellipse((840,y-15,880,y+15),fill=rgba(mix(GOLD,TEAL,i/2),int(120*p)))
    if prog>0.6:
        p=clamp((prog-0.6)*2.5)
        glow(im,(cx,cy-10),30,VIOLET,int(80*p),16)
        d.text((cx,cy+30),'the gap is not empty — it is the source',font=TINY_FONT,fill=rgba(VIOLET,int(200*p)),anchor='mm')
    d.text((640,505),'a sound disappears — it becomes potential, unclaimed presence',font=SUB_FONT,fill=MIST,anchor='mm')

def s06_admitted(im,t):
    im.paste(ground(SEED+6,NIGHT,GOLD,0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'the universe is admitted',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,110),'not created — consciousness decides what becomes real',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    # Gate/aperture
    for i in range(5):
        r=lerp(10,180,prog)-i*30; alpha=int(120*(1-i/5)*prog)
        if r<10 or alpha<5: continue
        d.arc((cx-r,cy-60-r*0.5,cx+r,cy-60+r*0.5),200,340,fill=rgba(mix(SLATE,GOLD,i/4),alpha),width=2)
    glow(im,(cx,cy-60),15+30*prog,GOLD_LIGHT,int(100+80*prog),16)
    d.ellipse((cx-10,cy-70,cx+10,cy-50),fill=rgba(WHITE,int(220*prog)))
    d.text((640,505),'attention is how consciousness says: this, here, now',font=SUB_FONT,fill=MIST,anchor='mm')

def s07_selection(im,t):
    im.paste(ground(SEED+7,PALE_FIELD,GOLD,0.2),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,80),'one field — infinite possible worlds',font=TERM_FONT,fill=INK,anchor='mm')
    d.text((cx,110),'attention selects one',font=SMALL_FONT,fill=UMBER,anchor='mm')
    prog=ease(t)
    for i in range(16):
        a=i*2*math.pi/16; r=120+30*ease(1-prog)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*0.6
        col=mix(SLATE,GOLD,i/15)
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(col,int(80+80*prog)))
    glow(im,(cx,cy),25+20*prog,GOLD_LIGHT,int(80+120*prog),16)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=rgba(WHITE,int(220*prog)))
    d.text((640,505),'the chosen thing brightens — everything else becomes background',font=SUB_FONT,fill=UMBER,anchor='mm')

def s08_seal(im,t):
    im.paste(ground(SEED+8,NIGHT,GOLD,0.4),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,75),'consciousness is the self',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,105),'caitanyam ātmā — the one who possesses and the thing possessed both appear inside awareness',font=SMALL_FONT,fill=MIST,anchor='mm')
    prog=ease(t)
    for i in range(3):
        r=50+i*55*prog; alpha=int(120*(1-i/3)*prog)
        d.ellipse((cx-r,cy-60-r*0.6,cx+r,cy-60+r*0.6),outline=rgba(mix(GOLD,SILVER,i/2),alpha),width=2)
    glow(im,(cx,cy-60),20+40*prog,GOLD_LIGHT,int(120+100*prog),20)
    d.ellipse((cx-14,cy-74,cx+14,cy-46),fill=rgba(WHITE,int(220*prog)),outline=rgba(GOLD,int(200*prog)),width=2)
    for i in range(14):
        a=i*2*math.pi/14+t*0.03; x=cx+math.cos(a)*180; y=cy-60+math.sin(a)*120
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,WHITE,i/13),int(130*prog)))
    d.text((640,505),'the luminous field aware of itself — fold upon fold, saying: this, here, now',font=SUB_FONT,fill=MIST,anchor='mm')

SCENES=[
    Scene('at01','The Selection','Something selects your reality before you know it.','Svīkāra','','opening',['selection','attention','reality'],'opening','field of dots with central bindu',6.0,s01_selection),
    Scene('at02','Field Divides','One field becomes center and edge.','Kṣetra','','division',['field','center','edge'],'division','concentric rings emerging from center',6.0,s02_field_divides),
    Scene('at03','Prakāśa-Vimarśa','Light and reflection forming awareness.','Prakāśa-vimarśa','','structure',['light','reflection','awareness'],'structure','ellipse with dual glowing centers',6.0,s03_prakasha_vimarsha),
    Scene('at04','Your Name','The sound that finds the center.','Nāma','','attention',['name','center','recognition'],'attention','scatter field with central burst',6.0,s04_your_name),
    Scene('at05','The Gap','What survives between perceptions.','Antara','','gap',['gap','source','potential'],'gap','two nodes with empty space between',6.0,s05_gap),
    Scene('at06','Admitted','The universe does not appear — it is admitted.','Praveśa','','admission',['admission','gate','reality'],'admission','aperture opening from center',6.0,s06_admitted),
    Scene('at07','Selection','Infinite possible worlds — attention chooses one.','Vikalpa','','selection',['selection','worlds','attention'],'selection','orbiting nodes with center selection',6.0,s07_selection),
    Scene('at08','The Awareness Seal','The luminous field aware of itself.','Caitanya-cakra','','seal',['awareness','self','light'],'seal','concentric rings with radiant center',6.0,s08_seal),
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
    manifest={'project':'The Universe Is Hiding Inside Your Attention',
        'source_basis':'Expansion Essay — the universe is hiding inside your attention, Tier 1 #3.',
        'style':{'family':'attentional-field cosmography','background':'deep night and pale field','ink':'slate and mist','accent':'gold, gold-light, violet, teal'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),
        'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — The Universe Is Hiding Inside Your Attention\n\nVisualize the Kashmir Śaiva doctrine of attention: prakāśa-vimarśa, field dividing into center and edge, the universe admitted not created.\n\n## Structure\n1. Something selects your reality before you know it\n2. One field divides into center and edge\n3. Prakāśa and vimarśa — light and reflection\n4. Your name in the crowd — attention finds the center\n5. The gap between perceptions — what survives\n6. The universe is admitted, not created\n7. Infinite possible worlds — selection\n8. The luminous field aware of itself\n\n## Visual rules\n- Night fields with gold radiance for awareness.\n- Concentric rings and apertures for attention.\n- Scatter fields for the undifferentiated.\n- Golden central bindu for selected reality.'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier,encoding='utf-8')
    style='''# STYLE EVOLUTION — The Universe Is Hiding Inside Your Attention\n\n## Differentiation\nThis pack uses attentional-field imagery — concentric rings, scatter dots, apertures — distinct from the alchemical crucibles of the Fire pack.\n\n## New symbols\n1. field of dots with central bindu\n2. concentric rings emerging from center\n3. ellipse with dual glowing centers\n4. scatter field with central burst\n5. two nodes with empty space between\n6. aperture opening from center\n7. orbiting nodes with center selection\n8. concentric rings with radiant center\n'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style,encoding='utf-8')
    readme=f'# The Universe Is Hiding Inside Your Attention — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n'
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES: print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'universe_hiding_in_attention_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); make_zip()
if __name__=='__main__':
    render_all()
