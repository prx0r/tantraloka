#!/usr/bin/env python3
import json,math,subprocess,zipfile; from dataclasses import dataclass; from pathlib import Path; from typing import Callable
import numpy as np; from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; FRAMES_ROOT=ROOT/'frames'; SCENES_ROOT=ROOT/'scenes'
W,H=1280,720; FPS=10; SEED=29290
DEEP=(12,14,22); WARM=(18,16,18); GOLD=(206,166,88); GOLD_LIGHT=(246,218,144); WHITE=(252,250,246)
PEARL=(246,243,236); SILVER=(196,204,222); TEAL=(92,146,148); LAVENDER=(170,156,200); SLATE=(90,100,120); MIST=(160,172,192); CORAL=(206,108,100)
FONT_SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'; FONT_SERIF_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE_FONT=ImageFont.truetype(FONT_SERIF_BOLD,30); SUB_FONT=ImageFont.truetype(FONT_SERIF,17); TERM_FONT=ImageFont.truetype(FONT_SERIF_BOLD,21); SMALL_FONT=ImageFont.truetype(FONT_SERIF,14); TINY_FONT=ImageFont.truetype(FONT_SERIF,11)
def clamp(v,lo=0.0,hi=1.0): return max(lo,min(hi,v))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(c1,c2,t): t=clamp(t); return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))
def ease_in_out(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    t=clamp((x-a)/(b-a)); return t*t*(3-2*t)
def rgba(c,a=255): return (*c[:3],int(a)); from PIL import ImageFilter
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
    d.rectangle((28,28,W-28,H-28),outline=rgba(mix(LAVENDER,SILVER,.5),70),width=2)
    d.rectangle((42,42,W-42,H-42),outline=rgba(mix(LAVENDER,SILVER,.3),45),width=1)
    for x,y in [(70,70),(W-70,70),(70,H-70),(W-70,H-70)]: draw_rosette(d,x,y,22,TEAL,GOLD)
def footer(im,title,subtitle,term=None):
    d=ImageDraw.Draw(im); y0=H-112
    d.rounded_rectangle((90,y0,W-90,H-34),radius=14,fill=(10,12,18,200),outline=rgba(mix(LAVENDER,SILVER,.4),45),width=1)
    d.text((122,y0+18),title,font=TITLE_FONT,fill=PEARL)
    d.text((124,y0+58),subtitle,font=SUB_FONT,fill=mix(MIST,PEARL,.3))
    if term: tw=d.textbbox((0,0),term,font=TERM_FONT)[2]; d.text((W-118-tw,y0+24),term,font=TERM_FONT,fill=mix(GOLD_LIGHT,LAVENDER,.5))
def dust(im,seed,n=55):
    rng=np.random.default_rng(seed); ov=layer(); d=ImageDraw.Draw(ov)
    for _ in range(n):
        x=float(rng.uniform(40,W-40)); y=float(rng.uniform(40,H-40))
        r=float(rng.uniform(0.8,2.5)); c=mix(mix(LAVENDER,SILVER,.5),GOLD_LIGHT,rng.uniform(0,1))
        d.ellipse((x-r,y-r,x+r,y+r),fill=rgba(c,int(rng.uniform(12,45))))
    im.alpha_composite(ov)
def w_ground(seed,bg,glow_col,intensity=0.4):
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
    fs=SEED+int(t*9973)%100000; im.paste(w_ground(fs,DEEP,mix(LAVENDER,SILVER,.5),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,255
    d.text((cx,110),'who are you when no one is watching?',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,140),'when the performance stops',font=TERM_FONT,fill=mix(LAVENDER,SILVER,.6),anchor='mm')
    prog=ease_in_out(t)
    draw_glow(im,(cx,cy+25),int(5+25*prog),mix(LAVENDER,GOLD_LIGHT,.5),120,14)
    d.ellipse((cx-10,cy+15,cx+10,cy+35),fill=rgba(WHITE,220))

def sc02(im,t):
    fs=SEED+int(t*9973+500)%100000; im.paste(w_ground(fs,WARM,mix(GOLD,TEAL,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,245
    d.text((cx,90),'the masks we wear',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,120),'you have a face for every room',font=TERM_FONT,fill=mix(GOLD,TEAL,.5),anchor='mm')
    d.text((cx,150),'what remains when every room is empty?',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(5):
        x=cx-120+i*60; d.ellipse((x-18,cy+15,x+18,cy+55),outline=rgba(mix(GOLD,TEAL,i/5),int(130*prog)),width=2)

def sc03(im,t):
    fs=SEED+int(t*9973+1000)%100000; im.paste(w_ground(fs,DEEP,mix(GOLD,LAVENDER,.3),0.3),(0,0))
    d=ImageDraw.Draw(im); cx,cy=W/2,250
    d.text((cx,95),'the watcher behind the watcher',font=TERM_FONT,fill=PEARL,anchor='mm')
    d.text((cx,125),'you think you are the one watching',font=TERM_FONT,fill=mix(GOLD,LAVENDER,.5),anchor='mm')
    d.text((cx,155),'but who watches the watcher?',font=SMALL_FONT,fill=mix(MIST,GOLD,.4),anchor='mm')
    prog=ease_in_out(t)
    for i in range(3):
        r=30+i*30; d.ellipse((cx-r,cy+15-r*0.6,cx+r,cy+15+r*0.6),outline=rgba(mix(SLATE,LAVENDER,.3),int(100*(1-prog*i*0.2))),width=1)
    draw_glow(im,(cx,cy+15),int(5+15*prog),mix(GOLD,WHITE,.5),100,12)
    d.ellipse((cx-5,cy+10,cx+5,cy+20),fill=rgba(WHITE,220))

SCENES=[
    Scene('wa01','The Unwatched Self','Who are you when the performance stops?','Svabhāva','','opening',['self','unwatched','true'],'intro','luminous center in empty room',6.0,sc01),
    Scene('wa02','Many Masks','A face for every room — what remains when empty?','Māyā','','masks',['masks','faces','true self'],'masks','five mask-forms circling center',7.0,sc02),
    Scene('wa03','The Watcher','Who watches the watcher? Endless regress.','Sākṣin','','witness',['watcher','witness','regress'],'witness','nested watcher rings dissolving inward',8.0,sc03),
]

def render_scene(scene:Scene):
    sdir=FRAMES_ROOT/scene.id; sdir.mkdir(parents=True,exist_ok=True)
    nframes=int(FPS*scene.duration)
    expected=[sdir/f'frame_{i:04d}.jpg' for i in range(nframes)]
    for i,path in enumerate(expected):
        if path.exists() and path.stat().st_size>1000: continue
        t=i/max(1,nframes-1)
        im=Image.new('RGBA',(W,H),(0,0,0,0)); scene.draw_fn(im,t)
        dust(im,SEED+hash(scene.id)%10000+i,55); border(im); footer(im,scene.title,scene.subtitle,scene.term)
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
    rows=(len(thumbs)+3)//4; sheet=Image.new('RGB',(4*320,rows*180),color=DEEP)
    for idx,im in enumerate(thumbs): sheet.paste(im,((idx%4)*320,(idx//4)*180))
    sheet.save(ROOT/'contact_sheet.jpg',quality=95)
def write_metadata():
    manifest={'project':'Who Are You When No One Is Watching','source_basis':'Essay 29 — 3 scenes.',
        'style':{'family':'self-inquiry visualization','background':'deep','ink':'lavender, gold, teal'},
        'fps':FPS,'resolution':[W,H],'total_scenes':len(SCENES),'total_duration_seconds':round(sum(s.duration for s in SCENES),1),
        'scenes':[{'id':s.id,'title':s.title,'duration':s.duration} for s in SCENES]}
    (ROOT/'scene_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    (ROOT/'AGENT_KNOWLEDGE_DOSSIER.md').write_text('Who Are You — 3 scenes.\n',encoding='utf-8')
    (ROOT/'STYLE_EVOLUTION.md').write_text('# Who Are You Pack\n',encoding='utf-8')
    (ROOT/'README.md').write_text(f'# Who Are You — {len(SCENES)} scenes ({sum(s.duration for s in SCENES):.0f}s)\n\nRun: python render_pack.py\n',encoding='utf-8')
    (ROOT/'validation.json').write_text(json.dumps({'programs':[],'streams':[{'width':W,'height':H,'r_frame_rate':f'{FPS}/1'}],'format':{'duration':str(sum(s.duration for s in SCENES)),'size':'0'}},indent=2))
def make_zip():
    zpath=ROOT/'who_are_you_pack.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as zf:
        for name in ['who_are_you_animation.mp4','contact_sheet.jpg','scene_manifest.json','AGENT_KNOWLEDGE_DOSSIER.md','STYLE_EVOLUTION.md','render_pack.py','README.md','validation.json']:
            if (ROOT/name).exists(): zf.write(ROOT/name,arcname=name)
        for mp4 in sorted(SCENES_ROOT.glob('*.mp4')): zf.write(mp4,arcname=f'scenes/{mp4.name}')
def render_all():
    FRAMES_ROOT.mkdir(exist_ok=True); SCENES_ROOT.mkdir(exist_ok=True)
    for sc in SCENES: print('Rendering',sc.id,sc.title,f'({sc.duration}s)',flush=True); render_scene(sc)
    concat=ROOT/'concat_list.txt'; concat.write_text('\n'.join([f"file '{(SCENES_ROOT/(sc.id+'.mp4')).as_posix()}'" for sc in SCENES]))
    combined=ROOT/'who_are_you_animation.mp4'
    if not combined.exists() or combined.stat().st_size<100000:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(combined)],check=True)
    make_contact_sheet(); write_metadata(); validate_outputs() if False else None; make_zip()
if __name__=='__main__': render_all()
