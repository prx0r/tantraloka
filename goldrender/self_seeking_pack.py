#!/usr/bin/env python3
from __future__ import annotations
import json,math,subprocess,zipfile
from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np; from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=28280
DEEP=(12,14,22); WARM=(18,16,18); NIGHT=(14,12,20); GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246)
PEARL=(246,243,236); SILVER=(196,204,222); TEAL=(92,146,148); LAVENDER=(170,156,200); SLATE=(90,100,120); MIST=(160,172,192)
FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'; FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17); TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14); TINY_FONT=ImageFont.truetype(FONT_SERIF,11)
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
    if term: tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,SILVER,.5))
def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.5)); c=mix(mix(GOLD,SILVER,.5),WHITE,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)
def sg_ground(seed,bg,glow_col,intensity=0.4):
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
    fs=SEED+int(t*9973)%100000; im.paste(sg_ground(fs,DEEP,mix(GOLD,SILVER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,110),'try to grab the self — you find nothing',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,140),'try to let go — nothing was ever there',font=TERM_FONT,fill=mix(GOLD,SILVER,.5),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+20),int(5+25*prog),mix(GOLD,WHITE,.5),120,14)
    d.ellipse((cx-10,cy+10,cx+10,cy+30),fill=rgba(WHITE,220))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(sg_ground(fs,WARM,mix(TEAL,GOLD,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,95),'the wave does not grieve',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'when it collapses — it is the ocean',font=TERM_FONT,fill=mix(TEAL,GOLD,.5),anchor='mm')
    d.text((cx,155),'the seeing of this is the end of grief',font=SMALL_FONT,fill=mix(MIST,TEAL,.4),anchor='mm')
    prog=ease_in_out(t)
    pts=bezier((200,380),(400,300),(600,360),(800,300),80)
    reveal=partial_polyline(pts,prog)
    if len(reveal)>1: draw_line_glow(im,reveal,mix(TEAL,GOLD,.5),3,100,6)
    d.line((200,400,1080,400),fill=rgba(mix(TEAL,GOLD,.3),100),width=1)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(sg_ground(fs,NIGHT,mix(GOLD,TEAL,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,90),'two doors — every moment',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'one opens onto a garden of honey',font=TERM_FONT,fill=mix(TEAL,GOLD,.5),anchor='mm')
    d.text((cx,150),'the other onto a long dark corridor',font=TERM_FONT,fill=mix(GOLD,TEAL,.5),anchor='mm')
    prog=ease_in_out(t)
    d.rounded_rectangle((250,210,520,370),radius=12,outline=rgba(mix(TEAL,GOLD,.5),180),width=2)
    d.text((385,290),'pleasant',font=SMALL_FONT,fill=mix(TEAL,GOLD,.5),anchor='mm')
    d.rounded_rectangle((760,210,1030,370),radius=12,outline=rgba(mix(SLATE,LAVENDER,.3),150),width=2)
    d.text((895,290),'good',font=SMALL_FONT,fill=mix(SLATE,LAVENDER,.3),anchor='mm')
    if prog>0.7:
        p=clamp((prog-0.7)*3.3)
        d.ellipse((895,330,895+p*30,340),fill=rgba(mix(GOLD,WHITE,.5),int(150*p)))

def sc04(im,t):
    fs=SEED+int(t*9973+1500)%100000; im.paste(sg_ground(fs,WARM,mix(GOLD,SILVER,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,90),'the chariot of the self',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'the horses are wild — the driver shakes',font=TERM_FONT,fill=mix(GOLD,SILVER,.5),anchor='mm')
    d.text((cx,150),'the passenger sits perfectly still',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    d.ellipse((cx-12,cy+15,cx+12,cy+35),outline=rgba(mix(GOLD,WHITE,.5),200),width=2)
    d.line((cx,cy+35,cx,cy+65),fill=rgba(mix(SLATE,LAVENDER,.3),150),width=2)
    d.line((cx,cy+40,cx-50,cy+60),fill=rgba(mix(SLATE,LAVENDER,.3),120),width=2)
    d.line((cx,cy+40,cx+50,cy+60),fill=rgba(mix(SLATE,LAVENDER,.3),120),width=2)
    draw_glow(im,(cx,cy+25),18,mix(GOLD,WHITE,.5),120,12)

def sc05(im,t):
    fs=SEED+int(t*9973+2000)%100000; im.paste(sg_ground(fs,DEEP,mix(GOLD,WHITE,.4),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,260
    d.text((cx,95),'aum — the sound the universe makes',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'when it opens its mouth',font=TERM_FONT,fill=mix(GOLD,WHITE,.5),anchor='mm')
    d.text((cx,155),'chant it — you remember what you were before birth',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    r=lerp(5,100,prog)
    draw_glow(im,(cx,cy+20),int(r),mix(GOLD,WHITE,.5),int(150*prog),18)
    d.ellipse((cx-12,cy+8,cx+12,cy+32),fill=rgba(WHITE,int(220*prog)))
    for i in range(8):
        a=i*2*math.pi/8; x=cx+math.cos(a)*(r+20); y=cy+20+math.sin(a)*(r+20)*0.55
        d.ellipse((x-3,y-3,x+3,y+3),fill=rgba(mix(GOLD,TEAL,i/8),150))

SCENES=[
    Scene('ss01','Grasp and Let Go','Grab the self — nothing. Let go — nothing was there.','Atman','','opening',['self','grasp','release'],'intro','luminous empty center',6.0,sc01),
    Scene('ss02','The Wave and the Ocean','The wave collapses — the ocean does not grieve.','Advaita','','unity',['wave','ocean','oneness'],'unity','wave rising and falling on still ocean',7.0,sc02),
    Scene('ss03','Two Doors','The pleasant and the good — choose the corridor.','Preyas vs śreyas','','choice',['choice','good','pleasant'],'choice','two doorways with light behind one',8.0,sc03),
    Scene('ss04','The Chariot','Wild horses, shaking driver — the passenger never moves.','Katha upaniṣad','','self',['chariot','horses','self'],'self','chariot with still passenger at center',8.0,sc04),
    Scene('ss05','Aum','The sound you have been making since before birth.','Praṇava','','seal',['aum','sound','source'],'seal','expanding om-symbol with rings',7.0,sc05),
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
    manifest={'project':'The Self That\'s Looking for Itself',
        'source_basis':'Expansion Essay 28 — 5 scenes.', 'style':{'family':'upanishadic self visualization','background':'deep','ink':'gold, silver, teal'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Self Seeking — 5 scenes.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Self Seeking Pack\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Self Seeking — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')
def validate_outputs():
    combined=ROOT/'self_seeking_animation.mp4'; probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration,size','-of','json',str(combined)])
    (ROOT/'validation.json').write_text(json.dumps(json.loads(probe),indent=2))
def make_zip():
    zpath=ROOT/'self_seeking_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['self_seeking_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES:
        print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'self_seeking_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs(); make_zip()
if __name__=='__main__': render_all()
