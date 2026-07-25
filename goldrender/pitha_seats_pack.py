#!/usr/bin/env python3
from __future__ import annotations

import json, math, subprocess, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES_ROOT = ROOT / 'frames'
SCENES_ROOT = ROOT / 'scenes'
W, H = 1280, 720
FPS = 10
DURATION = 4.8
NFRAMES = int(FPS * DURATION)
SEED = 34343

NIGHT = (14, 16, 22)
DEEP_INDIGO = (40, 46, 88)
INDIGO = (66, 74, 132)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
PALE_GOLD = (252, 240, 210)
WHITE = (252, 250, 246)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
ROSE = (194, 108, 132)
TEAL = (90, 146, 148)
DEEP_TEAL = (64, 112, 114)
SLATE = (106, 118, 138)
MIST = (176, 186, 204)
UMBER = (78, 64, 50)
EARTH = (158, 126, 84)
GREEN = (106, 152, 114)
SAFFRON = (224, 152, 56)
SILVER = (216, 222, 232)
PALE_VIOLET = (200, 192, 216)
LAVENDER = (168, 152, 196)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_SERIF_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'
TITLE_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 31)
SUB_FONT = ImageFont.truetype(FONT_SERIF, 18)
TERM_FONT = ImageFont.truetype(FONT_SERIF_BOLD, 22)
SMALL_FONT = ImageFont.truetype(FONT_SERIF, 15)
TINY_FONT = ImageFont.truetype(FONT_SERIF, 11)
DEVA_MED = ImageFont.truetype(FONT_DEVA, 28)
DEVA_SMALL = ImageFont.truetype(FONT_DEVA, 20)


def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def lerp(a,b,t): return a + (b-a)*clamp(t)
def mix(c1,c2,t):
    t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3
def smooth(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3], int(a))


def pitha_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(NIGHT,dtype=np.float32)
    coarse=rng.normal(0,1,(42,76)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*4.0 + fine[...,None]*1.1
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*18,0,26)[...,None]
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
    a=clamp(a)
    if a<=0:return[]
    if a>=1:return points
    f=a*(len(points)-1); i=int(f); q=f-i; out=list(points[:i+1])
    if i+1<len(points):
        A,B=points[i],points[i+1]; out.append((lerp(A[0],B[0],q),lerp(A[1],B[1],q)))
    return out

def rosette(d,cx,cy,r,outer,inner):
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*r*.62; y=cy+math.sin(a)*r*.62
        d.ellipse((x-r*.4,y-r*.4,x+r*.4,y+r*.4),fill=rgba(outer,130),outline=rgba(inner,170),width=1)
    d.ellipse((cx-r*.4,cy-r*.4,cx+r*.4,cy+r*.4),fill=rgba(inner,110),outline=rgba(outer,210),width=2)

def border(im):
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(SLATE,95),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,75),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(12,14,20,208),outline=rgba(SLATE,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=WHITE)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=MIST)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=GOLD_LIGHT)

def dust(im,seed,n=50):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

def pitha_node(d,cx,cy,r,col,label=None,inner=None):
    d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,190),fill=rgba(col,20),width=2)
    if inner: d.ellipse((cx-inner,cy-inner*.72,cx+inner,cy+inner*.72),fill=rgba(inner and col or col,150))
    if label: d.text((cx,cy+30),label,font=TINY_FONT,fill=col,anchor='mm')

def link(d,x1,y1,x2,y2,col):
    d.line((x1,y1,x2,y2),fill=rgba(col,90),width=1)


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'पीठ',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    angles=np.linspace(0,2*math.pi,9)[:-1]
    for i,a in enumerate(angles):
        x=cx+math.cos(a)*180; y=cy+math.sin(a)*120
        col=mix(GOLD,TEAL,i/8)
        pitha_node(d,x,y,12,col,str(i+1),4)
        seg=partial([(cx,cy),(x,y)],smooth(.03+i*.04,.82,t))
        if len(seg)>1:lineglow(im,seg,col,2,70,5)
    d.text((640,505),'the pīṭhas — seats of power scattered through the landscape of consciousness',font=SUB_FONT,fill=MIST,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    nodes=[(cx,cy-90,TEAL),(cx-110,cy-20,CRIMSON),(cx+110,cy-20,GOLD),(cx-70,cy+80,GREEN),(cx+70,cy+80,TEAL)]
    for i,(x,y,col) in enumerate(nodes):
        pitha_node(d,x,y,14,col,str(i+1),5)
        seg=partial([(cx,cy),(x,y)],smooth(.03+i*.05,.8,t))
        if len(seg)>1:lineglow(im,seg,col,2,75,5)
        for j,(x2,y2,col2) in enumerate(nodes):
            if j>i and abs(j-i)>1:
                link(d,x,y,x2,y2,mix(col,col2,.5))
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((640,505),'each seat is a distinct power of consciousness localized in space',font=SUB_FONT,fill=MIST,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy-80),40,SAFFRON,110,14)
    d.ellipse((cx-12,cy-94,cx+12,cy-66),fill=rgba(WHITE,255),outline=rgba(SAFFRON,220),width=2)
    d.text((cx,cy-120),'कामरूप',font=DEVA_SMALL,fill=SAFFRON,anchor='mm')
    for i in range(12):
        a=-math.pi/2+i*2*math.pi/12+t*.04; x=cx+math.cos(a)*170; y=cy+math.sin(a)*115
        pitha_node(d,x,y,8,mix(GOLD,TEAL,i/11),None,3)
        lineglow(im,[(cx,cy-80),(x,y)],mix(GOLD,TEAL,i/11),2,65,5)
    d.text((640,505),'Kāmarūpa — the seat where form arises from desire',font=SUB_FONT,fill=MIST,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx-100,cy),35,GOLD_LIGHT,110,12)
    d.ellipse((cx-114,cy-14,cx-86,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx-100,cy-30),'जालन्धर',font=DEVA_SMALL,fill=GOLD_LIGHT,anchor='mm')
    d.text((cx+100,cy-30),'पूर्णगिरि',font=DEVA_SMALL,fill=TEAL,anchor='mm')
    glow(im,(cx+100,cy),35,TEAL,110,12)
    d.ellipse((cx+86,cy-14,cx+114,cy+14),fill=rgba(WHITE,255),outline=rgba(TEAL,220),width=2)
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*170; y=cy+math.sin(a)*115
        d.ellipse((x-4,y-4,x+4,y+4),fill=rgba(mix(GOLD,TEAL,i/7),150))
    seg=partial([(cx-86,cy),(cx+86,cy)],ease(t))
    if len(seg)>1:lineglow(im,seg,GOLD_LIGHT,3,110,7)
    d.text((640,505),'Jālandhara and Pūrṇagiri — two seats, one current of power',font=SUB_FONT,fill=MIST,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'पीठ',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    rings=[4,8,12,16]
    for ri,n in enumerate(rings):
        r=50+ri*42
        for i in range(n):
            a=-math.pi/2+i*2*math.pi/n+t*.03*(1 if ri%2==0 else -1)
            x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.68
            col=mix(CRIMSON,GOLD,ri/3)
            d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(col,180))
    d.text((640,505),'the seats form concentric circles of power around one center',font=SUB_FONT,fill=MIST,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),60,GOLD_LIGHT,130,20)
    for r,col in [(210,GOLD),(160,CRIMSON),(108,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    for i in range(16):
        a=i*2*math.pi/16+t*.03; x=cx+math.cos(a)*190; y=cy+math.sin(a)*130
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,TEAL,i/15),180))
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'शक्ति',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    d.text((640,505),'the seats are the body of Śakti — power distributed through space',font=SUB_FONT,fill=MIST,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    glow(im,(cx,cy),45,GOLD_LIGHT,120,14)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'संचार',font=DEVA_MED,fill=GOLD_LIGHT,anchor='mm')
    pts=[(cx-140,120,GOLD),(cx-70,190,CRIMSON),(cx+30,160,TEAL),(cx+130,220,GREEN),(cx-100,310,SAFFRON),(cx+50,380,TEAL),(cx-40,430,GOLD)]
    for i,(x,y,col) in enumerate(pts):
        seg=partial([(cx,cy),(x,y)],smooth(.03+i*.04,.78,t))
        if len(seg)>1:lineglow(im,seg,col,2,75,5)
        pitha_node(d,x,y,9,col,str(i+1),3)
    d.text((640,505),'the current flows from seat to seat — a circulation of power without end',font=SUB_FONT,fill=MIST,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    for r,col in [(220,SLATE),(175,GOLD),(130,CRIMSON),(85,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'पीठ',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*135
        d.ellipse((x-5,y-5,x+5,y+5),fill=rgba(mix(GOLD,TEAL,i/15),180))
    d.text((640,505),'the pīṭha seal: power seated in the heart of all places',font=SUB_FONT,fill=MIST,anchor='mm')


SCENES=[
Scene('pi01','The Seats of Power','Śakti distributed through space.','Pīṭha-maṇḍala','Overview: the sacred seats where power abides.','overview',['pitha','seats','power'],'overview','eight-node radial network',sc01),
Scene('pi02','The Nodal Network','Seats connected by lines of power.','Nāḍī-pīṭha','Each seat is a node in a living network of consciousness.','nodal_network',['network','nodes','connections'],'network','five-node interconnected graph',sc02),
Scene('pi03','Kāmarūpa','The seat of formative desire.','Kāmarūpa','Where form arises from the desire of consciousness.','seat_of_form',['desire','form','seat'],'seat','central seat with radiating nodes',sc03),
Scene('pi04','Jālandhara and Pūrṇagiri','Two seats, one current.','Jālandhara-Pūrṇagiri','Two great seats transmitting one power.','paired_seats',['pair','seats','transmission'],'seat','dual node with bridging current',sc04),
Scene('pi05','Concentric Circles of Power','The seats arranged in rings.','Pīṭha-valaya','Power radiates in concentric circles from the center.','concentric_rings',['rings','concentric','radiation'],'structure','four-ring radiating node field',sc05),
Scene('pi06','The Body of Śakti','Power distributed as living presence.','Śakti-pīṭha','The seats are the limbs of the goddess.','body_of_shakti',['shakti','body','distribution'],'synthesis','triple ring with central Devanagari',sc06),
Scene('pi07','Circulation of Power','Current flows from seat to seat.','Śakti-sañcāra','Power circulates through the network without end.','power_circulation',['circulation','current','flow'],'process','seven-node flow path',sc07),
Scene('pi08','The Pīṭha Seal','Power seated in the heart of all places.','Pīṭha-cakra','Closing seal: the seats as one field of distributed awareness.','closing_seal',['seal','pitha','power'],'seal','quadruple ring with sixteen nodes',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=pitha_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,45); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),NIGHT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Pīṭha: The Seats of Power','source_basis':'Tantrāloka and Trika sacred geography: the pīṭhas as seats of Śakti, nodal networks of power.','style':{'family':'sacred-geography cosmography','background':'deep night field','ink':'silver and slate','accent':'gold, crimson, teal, saffron, green','materials':['nodal networks','radial node rings','concentric power circles','transmission arcs','Devanagari station labels']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['pi01'],'individual_seats':['pi03','pi04'],'network_and_structure':['pi02','pi05','pi06'],'circulation_and_seal':['pi07','pi08']},'reusability_notes':{'pi01':'Use for pīṭha overview or sacred geography.','pi02':'Use for nodal networks or power connections.','pi03':'Use for Kāmarūpa or desire-as-form.','pi04':'Use for paired seats or transmission between seats.','pi05':'Use for concentric circles of power.','pi06':'Use for Śakti as distributed presence.','pi07':'Use for circulation or flow of power.','pi08':'Use as closing pīṭha seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Pīṭha

## Aim
Visualize the pīṭhas: the sacred seats of power, nodes where Śakti abides, arranged as a living network of consciousness.

## Structure
1. The seats are nodes of power
2. Nodes form a connected network
3. Kāmarūpa — seat of formative desire
4. Jālandhara — seat of holding
5. Pūrṇagiri — seat of fullness
6. Concentric rings of power
7. Power circulates from seat to seat
8. The seal: all seats as one field

## Visual rules
- Node and network visual language.
- Gold for central seats, crimson for transformative seats, teal for receptive seats.
- Lines connect nodes to show transmission.
- Devanagari station labels.
- No map-like geography — abstract nodal geometry.

## New motifs
- eight-node radial network
- five-node interconnected graph
- central seat with radiating nodes
- dual node with bridging current
- four-ring radiating node field
- triple ring with central Devanagari
- seven-node flow path
- quadruple ring with sixteen nodes
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Pīṭha Pack

## Differentiation
This pack uses nodal network imagery — nodes, connections, concentric power rings — distinct from the elemental dissolution of Bhūtaśuddhi or the light-reflection of Prakāśa-Vimarśa.

## New symbols
1. eight-node radial network
2. five-node interconnected graph
3. central seat with radiating nodes
4. dual node with bridging current
5. four-ring radiating node field
6. triple ring with central Devanagari
7. seven-node flow path
8. quadruple ring with sixteen nodes
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'''# Tantrāloka — Pīṭha: The Seats of Power Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'''
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'pitha_seats_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'pitha_seats_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['pitha_seats_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','pitha_seats_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'pitha_seats_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
