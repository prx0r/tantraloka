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
SEED = 67676

PARCHMENT = (244, 240, 232)
PARCHMENT_LIGHT = (250, 247, 240)
INK = (32, 36, 44)
UMBER = (78, 64, 50)
GOLD = (206, 166, 88)
GOLD_LIGHT = (244, 214, 138)
CRIMSON = (154, 46, 60)
CARDINAL = (186, 54, 70)
ROSE = (194, 108, 132)
TEAL = (90, 146, 148)
DEEP_TEAL = (64, 112, 114)
INDIGO = (66, 78, 136)
DEEP_INDIGO = (44, 54, 98)
SLATE = (106, 118, 138)
MIST = (176, 186, 200)
WHITE = (252, 250, 246)
GREEN = (106, 152, 114)
SAFFRON = (224, 152, 56)
SILVER = (216, 222, 232)
VIOLET = (100, 84, 144)
LAVENDER = (166, 148, 196)

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
DEVA_TINY = ImageFont.truetype(FONT_DEVA, 15)


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


def sabda_ground(seed):
    rng=np.random.default_rng(seed)
    base=np.zeros((H,W,3),dtype=np.float32); base[:]=np.array(PARCHMENT,dtype=np.float32)
    coarse=rng.normal(0,1,(40,72)).astype(np.float32)
    cimg=Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255,0,255)))
    cimg=cimg.resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(16))
    carr=(np.asarray(cimg).astype(np.float32)-128)/128
    fine=rng.normal(0,1,(H,W)).astype(np.float32)
    base += carr[...,None]*3.0 + fine[...,None]*0.85
    yy,xx=np.mgrid[0:H,0:W]
    dx=(xx-W/2)/(W/2); dy=(yy-H/2)/(H/2)
    base -= np.clip((dx*dx+dy*dy)*4.5,0,13)[...,None]*0.55
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
    d=ImageDraw.Draw(im); d.rectangle((28,28,W-28,H-28),outline=rgba(UMBER,110),width=2); d.rectangle((42,42,W-42,H-42),outline=rgba(GOLD,80),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: rosette(d,x,y,22,CRIMSON,GOLD)

def footer(im,title,subtitle,term):
    d=ImageDraw.Draw(im); y=H-112
    d.rounded_rectangle((90,y,W-90,H-34),radius=14,fill=(247,244,237,216),outline=rgba(UMBER,55),width=1)
    d.text((122,y+18),title,font=TITLE_FONT,fill=INK)
    d.text((124,y+58),subtitle,font=SUB_FONT,fill=UMBER)
    tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y+24),term,font=TERM_FONT,fill=CARDINAL)

def dust(im,seed,n=45):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(120,W-120)); y=float(rng.uniform(120,H-180)); r=float(rng.uniform(1,2.1))
        c=mix(SILVER,GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(18,60))))
    im.alpha_composite(ov)

GLYPHS = list('अआइईउऊऋॠऌॡएऐओऔअंअःकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह')


@dataclass
class Scene:
    id:str; title:str; subtitle:str; term:str; summary:str; mode:str; tags:list[str]; group:str; technique:str; draw_fn:Callable


def sc01(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-16,cy-16,cx+16,cy+16),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'शब्दराशि',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(14):
        a=i*2*math.pi/14; x=cx+math.cos(a)*185; y=cy+math.sin(a)*126
        ch=GLYPHS[i%len(GLYPHS)]
        d.text((x,y),ch,font=DEVA_TINY,fill=mix(GOLD,TEAL,i/13),anchor='mm')
        lineglow(im,[(cx,cy),(x,y)],mix(GOLD,TEAL,i/13),1,55,4)
    d.text((640,505),'śabdarāśi — the ocean of phonemes that is the cosmos',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc02(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'स्वर',font=DEVA_MED,fill=GOLD,anchor='mm')
    vowels=list('अआइईउऊऋएऐओऔ')
    for i,ch in enumerate(vowels):
        a=-math.pi/2+i*2*math.pi/len(vowels)
        x=cx+math.cos(a)*160; y=cy-10+math.sin(a)*108
        d.text((x,y),ch,font=DEVA_TINY,fill=mix(GOLD,TEAL,i/len(vowels)),anchor='mm')
        lineglow(im,[(cx,cy-10),(x,y)],mix(GOLD,TEAL,i/len(vowels)),2,70,5)
    d.text((640,505),'the vowels are the first articulation — the breath shaped by consciousness',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc03(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),55,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'व्यञ्जन',font=DEVA_SMALL,fill=INDIGO,anchor='mm')
    cons=list('कखगघङचछजझञटठडढणतथदधनपफबभम')
    for i,ch in enumerate(cons):
        a=-math.pi/2+i*2*math.pi/len(cons)
        x=cx+math.cos(a)*175; y=cy-10+math.sin(a)*118
        d.text((x,y),ch,font=DEVA_TINY,fill=mix(INDIGO,ROSE,i/len(cons)),anchor='mm')
        lineglow(im,[(cx,cy-10),(x,y)],mix(INDIGO,ROSE,i/len(cons)),1,55,4)
    d.text((640,505),'the consonants are the structure — the framework of manifestation',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc04(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    for r,col in [(210,GOLD),(160,CRIMSON),(110,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,120),width=2)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'मातृका',font=DEVA_MED,fill=CRIMSON,anchor='mm')
    for i in range(20):
        a=i*2*math.pi/20+t*.03; r=150+30*ease(t)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        ch=GLYPHS[i%len(GLYPHS)]
        d.text((x,y),ch,font=DEVA_TINY,fill=mix(CRIMSON,GOLD_LIGHT,i/19),anchor='mm')
    d.text((640,505),'the mātṛkā — the alphabet as the mother of all form',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc05(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    glow(im,(cx,160),36,GOLD_LIGHT,120,14)
    d.ellipse((cx-12,146,cx+12,174),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,130),'बीज',font=DEVA_SMALL,fill=GOLD,anchor='mm')
    seeds=['ॐ','ह्रीं','श्रीं','क्लीं','हं','सौः']
    for i,ch in enumerate(seeds):
        a=-math.pi/2+i*2*math.pi/6
        x=cx+math.cos(a)*160; y=160+math.sin(a)*108
        col=mix(GOLD,CARDINAL,i/5)
        d.ellipse((x-18,y-18,x+18,y+18),outline=rgba(col,180),fill=rgba(col,20),width=2)
        d.text((x,y),ch,font=DEVA_SMALL,fill=col,anchor='mm')
        seg=partial([(cx,160),(x,y)],smooth(.04+i*.06,.82,t))
        if len(seg)>1:lineglow(im,seg,col,2,75,5)
    d.text((640,505),'bīja-mantras — seed syllables that contain entire worlds of meaning',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc06(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    glow(im,(cx,cy),60,GOLD_LIGHT,130,18)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'वर्ण',font=DEVA_MED,fill=GOLD,anchor='mm')
    for row in range(5):
        for col in range(7):
            idx=row*7+col
            if idx>=len(GLYPHS): break
            x=lerp(200,1080,col/6); y=lerp(160,430,row/4)
            a=smooth(.02+idx*.012,.8,t)
            if a<=0: continue
            d.text((x,y),GLYPHS[idx],font=DEVA_TINY,fill=mix(INDIGO,GOLD,row/4),anchor='mm')
    d.text((640,505),'the alphabet arranged — each phoneme a category of consciousness',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc07(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    glow(im,(cx,cy),50,GOLD_LIGHT,120,16)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy),'शब्द',font=DEVA_MED,fill=GOLD,anchor='mm')
    for i in range(12):
        a=i*2*math.pi/12+t*.04; x=cx+math.cos(a)*180; y=cy+math.sin(a)*122
        ch=GLYPHS[i%len(GLYPHS)]
        d.text((x,y),ch,font=DEVA_TINY,fill=mix(INDIGO,ROSE,i/11),anchor='mm')
        lineglow(im,[(cx,cy),(x,y)],mix(INDIGO,ROSE,i/11),1,55,4)
    d.text((640,505),'the phonemes are not arbitrary — they are the structure of reality',font=SUB_FONT,fill=UMBER,anchor='mm')

def sc08(im,t):
    d=ImageDraw.Draw(im); cx,cy=W/2,270
    glow(im,(cx,cy),70,GOLD_LIGHT,140,22)
    for r,col in [(220,GOLD),(175,CRIMSON),(130,INDIGO),(85,TEAL)]:
        d.ellipse((cx-r,cy-r*.72,cx+r,cy+r*.72),outline=rgba(col,125),width=2)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rgba(WHITE,255),outline=rgba(GOLD,220),width=2)
    d.text((cx,cy-50),'शब्दराशि',font=DEVA_SMALL,fill=CRIMSON,anchor='mm')
    for i in range(16):
        a=-math.pi/2+i*2*math.pi/16+t*.04; x=cx+math.cos(a)*195; y=cy+math.sin(a)*134
        ch=GLYPHS[i%len(GLYPHS)]
        d.text((x,y),ch,font=DEVA_TINY,fill=mix(GOLD,TEAL,i/15),anchor='mm')
    d.text((640,505),'the śabdarāśi seal: the ocean of phonemes as the body of the real',font=SUB_FONT,fill=UMBER,anchor='mm')


SCENES=[
Scene('sr01','The Ocean of Phonemes','The alphabet as cosmos.','Śabdarāśi','The phonemes are cosmic categories that structure reality.','overview',['phonemes','alphabet','cosmos'],'overview','radial phoneme wheel',sc01),
Scene('sr02','The Vowels','The breath shaped by consciousness.','Svara','Vowels as the first articulation of consciousness.','vowels',['vowels','breath','articulation'],'vowels','radial vowel circle',sc02),
Scene('sr03','The Consonants','The framework of manifestation.','Vyañjana','Consonants as the structural framework of reality.','consonants',['consonants','structure','manifestation'],'consonants','radial consonant circle',sc03),
Scene('sr04','Mātṛkā','The alphabet as mother of form.','Mātṛkā','The alphabet as the generating matrix of all categories.','alphabet_mother',['alphabet','matrix','mother'],'matrix','triple ring with alphabet scatter',sc04),
Scene('sr05','Bīja-mantras','Seed syllables of power.','Bīja','Seed mantras contain entire worlds of meaning.','seed_syllables',['bija','seed','mantra'],'mantras','six bīja radial',sc05),
Scene('sr06','The Arrayed Alphabet','Phonemes as categories.','Varṇa-vinyāsa','The alphabet arranged as a grid of cosmic categories.','alphabet_grid',['alphabet','grid','categories'],'structure','five-row alphabet grid',sc06),
Scene('sr07','Phonemes as Reality','Sound is the structure of the real.','Śabda-tattva','Phonemes are not arbitrary — they are ontological categories.','phonemic_reality',['phonemes','reality','structure'],'synthesis','radial phoneme emission',sc07),
Scene('sr08','The Śabdarāśi Seal','The ocean of phonemes as the body of the real.','Śabdarāśi-cakra','Closing seal: the alphabet as the fabric of manifestation.','closing_seal',['seal','phonemes','alphabet'],'seal','quadruple ring with alphabet ring',sc08),
]


def render_scene(sc):
    sd=FRAMES_ROOT/sc.id; sd.mkdir(parents=True,exist_ok=True)
    frames=[sd/f'frame_{i:04d}.jpg' for i in range(NFRAMES)]
    for i,p in enumerate(frames):
        if p.exists() and p.stat().st_size>1000:continue
        t=i/max(1,NFRAMES-1)
        im=sabda_ground(SEED+(hash(sc.id)%10000)+i)
        border(im); dust(im,SEED+i,40); sc.draw_fn(im,t); footer(im,sc.title,sc.subtitle,sc.term)
        im.convert('RGB').save(p,quality=95)
    out=SCENES_ROOT/f'{sc.id}.mp4'
    if not out.exists() or out.stat().st_size<30000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(sd/'frame_%04d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(out)],check=True)

def contact_sheet():
    thumbs=[]; from PIL import Image as IM
    for sc in SCENES:
        p=FRAMES_ROOT/sc.id/f'frame_{int(NFRAMES*.72):04d}.jpg'
        thumbs.append(IM.open(p).convert('RGB').resize((320,180),IM.Resampling.LANCZOS))
    sheet=Image.new('RGB',(1280,360),PARCHMENT)
    for i,im in enumerate(thumbs): sheet.paste(im,((i%4)*320,(i//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)

def metadata():
    manifest={'project':'Tantrāloka — Śabdarāśi: The Ocean of Phonemes','source_basis':'Tantrāloka and Trika phonemic ontology: the alphabet as cosmic categories, vowels as breath, consonants as structure, mātṛkā as generating matrix.','style':{'family':'phonemic manuscript cosmography','background':'warm parchment','ink':'umber and slate','accent':'gold, crimson, teal, indigo, rose','materials':['phoneme wheels','vowel rings','consonant scatter','alphabet grids','bīja medallions','phoneme rings']},'fps':FPS,'resolution':[W,H],'scene_duration_seconds':DURATION,'total_scenes':len(SCENES),'total_duration_seconds':len(SCENES)*DURATION,'scenes':[{'id':s.id,'title':s.title,'subtitle':s.subtitle,'mode':s.mode,'summary':s.summary,'group':s.group,'technique_notes':s.technique,'tags':s.tags,'duration_seconds':DURATION,'output_filename':f'scenes/{s.id}.mp4'} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    catalog={'ids':[s.id for s in SCENES],'titles':{s.id:s.title for s in SCENES},'modes':{s.id:s.mode for s in SCENES},'theme_clusters':{'overview':['sr01'],'vowels_and_consonants':['sr02','sr03'],'matrix_and_seeds':['sr04','sr05'],'arrangement_and_seal':['sr06','sr07','sr08']},'reusability_notes':{'sr01':'Use for phonemic cosmos overview.','sr02':'Use for vowels or breath articulation.','sr03':'Use for consonants or structural framework.','sr04':'Use for mātṛkā or alphabet matrix.','sr05':'Use for bīja-mantras or seed syllables.','sr06':'Use for alphabet grid or arrangement.','sr07':'Use for phonemes as ontological categories.','sr08':'Use as closing phoneme seal.'}}
    (ROOT/'scene_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    dossier='''# AGENT KNOWLEDGE DOSSIER — Śabdarāśi

## Aim
Visualize śabdarāśi: the ocean of phonemes as cosmic categories that structure reality.

## Structure
1. The phonemes are the alphabet of reality
2. Vowels — breath shaped by consciousness
3. Consonants — the structural framework
4. Mātṛkā — the mother matrix
5. Bīja-mantras — seed syllables of power
6. The arranged alphabet
7. Phonemes as ontological categories
8. The seal: the phonemic ocean

## Visual rules
- Parchment ground, manuscript feel.
- Use actual Devanagari glyphs as visual elements.
- Vowel scenes use gold/teal (breath/life).
- Consonant scenes use indigo/rose (structure/form).
- Bīja scenes use cardinal/gold (power).
- Each phoneme is shown as a node in a living matrix.
'''
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text(dossier)
    style='''# STYLE EVOLUTION — Śabdarāśi Pack

## Differentiation
This pack uses actual Devanagari glyphs as primary visual elements — not as labels but as the substance of the composition. Vowels orbit, consonants scatter, bījas radiate.

## New symbols
1. radial phoneme wheel
2. radial vowel circle
3. radial consonant circle
4. triple ring with alphabet scatter
5. six bīja radial
6. five-row alphabet grid
7. radial phoneme emission
8. quadruple ring with alphabet ring
'''
    (ROOT/'STYLE_EVOLUTION.md').write_text(style)
    readme=f'# Tantrāloka — Śabdarāśi Pack\n\n- {W}x{H}, {FPS}fps, {len(SCENES)} scenes\n\nRun: `python render_pack.py`'
    (ROOT/'README.md').write_text(readme)

def validate():
    p=ROOT/'sabda_rasi_animation.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(p)]))
    (ROOT/'validation.json').write_text(json.dumps(info,indent=2))

def make_zip():
    z=ROOT/'sabda_rasi_pack.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
        for n in ['sabda_rasi_animation.mp4','contact_sheet.jpg','scene_manifest.json','scene_catalog.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','sabda_rasi_pack.py','README.md','validation.json']:
            zf.write(ROOT/n,arcname=n)
        for p in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(p,arcname=f'scenes/{p.name}')

def main():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for s in SCENES: print('Rendering',s.id,s.title,flush=True); render_scene(s)
    lst=ROOT/'concat_list.txt'; lst.write_text('\n'.join([f"file '{(SCENES_ROOT/(s.id+'.mp4')).as_posix()}'" for s in SCENES]))
    out=ROOT/'sabda_rasi_animation.mp4'
    if not out.exists() or out.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out)],check=True)
    contact_sheet(); metadata(); validate(); make_zip()

if __name__=='__main__': main()
