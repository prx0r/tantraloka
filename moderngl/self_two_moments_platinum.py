#!/usr/bin/env python3
"""
THE SELF APPEARS WHEREVER TWO MOMENTS BELONG TO ONE LIFE
A complete Platinum-house procedural visual essay.

Source:
expansion-essays/01_the_self_appears_wherever_two_moments_belong_to_one_life.md

VISUAL THESIS
-------------
Causal succession can transmit information, but memory adds a first-person
relation: "that happened to me." The film distinguishes traces from ownership,
reconstruction from continuity, and self-luminous awareness from a homunculus.

HOUSE RULES
-----------
• Every scene lasts 5–10 seconds.
• Every scene visibly transforms one state into another.
• Clean ivory scientific/gallery field.
• Sparse labels only.
• No slideshow compositions.
• Mature frame near u=0.72.
• Continuity object: a gold thread linking otherwise vanishing moments.

PALETTE ROLES
-------------
IVORY    open temporal field
CYAN     present cognition / manifestation
GOLD     ownership / continuity / recognition
VIOLET   memory trace / reconstructed past
CRIMSON  error / distortion / broken identity claim
GREEN    successful recognition across difference
INK      determinate content

OUTPUT
------
output_self_two_moments/
  frames/
  scenes/
  self_two_moments.mp4
  narration_timeline.json
  contact_sheet.jpg
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"output_self_two_moments"
FRAMES=OUTPUT/"frames"
SCENES_DIR=OUTPUT/"scenes"
DEFAULT_WIDTH=1280
DEFAULT_HEIGHT=720
DEFAULT_FPS=10

IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT_INK=(86,91,98)
SILVER=(180,187,194); PALE_SILVER=(226,229,232)
CYAN=(57,156,180); PALE_CYAN=(196,227,233)
GOLD=(194,156,72); PALE_GOLD=(236,219,175)
VIOLET=(109,83,153); PALE_VIOLET=(220,211,237)
CRIMSON=(162,58,69); PALE_CRIMSON=(231,198,202)
GREEN=(70,139,99); PALE_GREEN=(198,225,208)

FONT_SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x,lo=0,hi=1): return max(lo,min(hi,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b:return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): t=clamp(t); return .5-.5*math.cos(math.pi*t)

def font(path,size):
    for c in (path,FONT_SERIF,FONT_SANS):
        try:return ImageFont.truetype(c,size)
        except OSError:pass
    return ImageFont.load_default()

def layer(size): return Image.new("RGBA",size,(0,0,0,0))

def field(w,h,seed):
    rng=np.random.default_rng(seed)
    arr=np.empty((h,w,3),dtype=np.float32); arr[:]=IVORY
    arr+=rng.normal(0,.9,(h,w,1))
    yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.39)/(h*.31))**2)*2)
    arr[...,1]+=halo*3.3; arr[...,2]+=halo*5.0
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")

def centered(d,xy,text,f,fill=INK): d.text(xy,text,font=f,fill=fill,anchor="mm")
def seal(im,title,subtitle="",color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    centered(d,(w/2,h*.875),title,font(FONT_SERIF_BOLD,max(22,int(h*.04))),color)
    if subtitle:centered(d,(w/2,h*.923),subtitle,font(FONT_SANS,max(13,int(h*.019))),SOFT_INK)
def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((26,26,w-26,h-26),radius=18,outline=(*INK,45),width=2)

def glow_circle(im,x,y,r,color,alpha=170,blur=14):
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.ellipse((x-r,y-r,x+r,y+r),fill=(*color,alpha))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).ellipse((x-r*.34,y-r*.34,x+r*.34,y+r*.34),
                               fill=(*mix(color,WHITE,.35),min(255,alpha+50)))
    im.alpha_composite(fg)

def glow_line(im,pts,color,width=4,alpha=210,blur=11):
    if len(pts)<2:return
    gl=layer(im.size); gd=ImageDraw.Draw(gl)
    gd.line(pts,fill=(*color,alpha),width=width*3,joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    fg=layer(im.size)
    ImageDraw.Draw(fg).line(pts,fill=(*mix(color,WHITE,.08),min(255,alpha+25)),
                            width=width,joint="curve")
    im.alpha_composite(fg)

def partial(pts,a):
    if not pts:return []
    a=clamp(a)
    if a>=1:return pts
    k=a*(len(pts)-1); i=int(k); f=k-i
    out=list(pts[:i+1])
    if i+1<len(pts):
        p,q=pts[i],pts[i+1]
        out.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return out

def arrow(d,a,b,color=INK,width=3,head=10):
    d.line((*a,*b),fill=color,width=width)
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (-1,1):
        p=(b[0]-math.cos(ang+s*.52)*head,b[1]-math.sin(ang+s*.52)*head)
        d.line((*b,*p),fill=color,width=width)

def draw_room(d,cx,cy,scale,color,alpha=220,age=0.0):
    # perspective room
    left=cx-170*scale; right=cx+170*scale; top=cy-110*scale; bottom=cy+120*scale
    fade=int(alpha*(1-age*.45))
    d.rectangle((left,top,right,bottom),outline=(*color,fade),width=max(2,int(4*scale)))
    d.line((left,top,cx,cy-25*scale,right,top),fill=(*color,fade),width=max(2,int(3*scale)))
    d.line((left,bottom,cx,cy+35*scale,right,bottom),fill=(*color,fade),width=max(2,int(3*scale)))
    # wallpaper stripes distort with age
    for i in range(7):
        x=lerp(left,right,i/6)+math.sin(i*1.7)*8*age
        d.line((x,top,x,bottom),fill=(*VIOLET,int(80*(1-age*.25))),width=2)
    # window
    d.rectangle((cx+55*scale,cy-65*scale,cx+120*scale,cy+10*scale),
                outline=(*CYAN,fade),width=max(2,int(3*scale)))

def draw_vase(d,x,y,scale,color,alpha=220):
    pts=[(x-25*scale,y-45*scale),(x+25*scale,y-45*scale),
         (x+38*scale,y+35*scale),(x,y+55*scale),(x-38*scale,y+35*scale),
         (x-25*scale,y-45*scale)]
    d.line(pts,fill=(*color,alpha),width=max(2,int(4*scale)))
    d.ellipse((x-25*scale,y-52*scale,x+25*scale,y-38*scale),
              outline=(*color,alpha),width=max(2,int(3*scale)))

def vis_room_memory(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.41; q=ease(u)
    # present field summons absent room
    for rr in range(30,230,30):
        d.ellipse((cx-rr,cy-rr*.58,cx+rr,cy+rr*.58),
                  outline=(*VIOLET,int(70*q*(1-rr/260))),width=3)
    draw_room(d,cx,cy,1.0,VIOLET,int(220*q),age=.35)
    if q>.55:
        centered(d,(cx,h*.69),"I WAS THERE",font(FONT_SERIF_BOLD,30),(*GOLD,int(220*q)))
    seal(im,"A ROOM RETURNS WITHOUT RETURNING",
         "the past appears now with a first-person claim")

def vis_discrete_moments(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; q=ease(u)
    xs=[w*.18,w*.34,w*.50,w*.66,w*.82]
    for i,x in enumerate(xs):
        local=clamp(q*len(xs)-i)
        glow_circle(im,x,y,14,[CYAN,VIOLET,GOLD,CRIMSON,GREEN][i],int(150+60*local),10)
        if i<len(xs)-1:
            arrow(d,(x+18,y),(xs[i+1]-18,y),(*SILVER,int(150*local)),2,7)
    seal(im,"A STREAM OF MOMENTARY EVENTS",
         "causal continuity can pass traces forward")

def vis_vase_memory(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.28,h*.40); right=(w*.72,h*.40); q=ease(u)
    draw_vase(d,*left,1.1,CYAN,int(220*(1-smoothstep(.25,.55,u))))
    glow_line(im,partial([left,(w*.50,h*.28),right],q),VIOLET,4,190,12)
    if q>.55:
        draw_vase(d,*right,.85,VIOLET,int(220*q))
        centered(d,(right[0],h*.68),"I SAW THAT",font(FONT_SERIF_BOLD,26),GOLD)
    seal(im,"MEMORY DOES MORE THAN REPRODUCE CONTENT",
         "it recognizes a relation between then and now")

def vis_footprint(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    q=ease(u)
    # foot passes, footprint remains
    foot_x=lerp(w*.18,w*.55,smoothstep(.05,.50,u))
    d.ellipse((foot_x-22,h*.33-45,foot_x+22,h*.33+45),
              outline=(*INK,int(220*(1-smoothstep(.48,.68,u)))),width=4)
    if q>.38:
        alpha=int(220*smoothstep(.38,.75,u))
        d.ellipse((w*.55-22,h*.50-45,w*.55+22,h*.50+45),
                  fill=(*PALE_VIOLET,alpha//2),outline=(*VIOLET,alpha),width=3)
    centered(d,(w*.72,h*.40),"TRACE ≠ OWNER",font(FONT_SERIF_BOLD,28),CRIMSON)
    seal(im,"A FOOTPRINT IS CAUSED BY A FOOT",
         "the footprint does not remember walking")

def vis_beads_thread(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.40; xs=[w*.20,w*.35,w*.50,w*.65,w*.80]; q=ease(u)
    for i,x in enumerate(xs):
        glow_circle(im,x,y,15,[CYAN,VIOLET,GREEN,CRIMSON,CYAN][i],170,10)
    if q>.25:
        pts=[(x,y) for x in xs]
        glow_line(im,partial(pts,(q-.25)/.75),GOLD,5,220,13)
    seal(im,"BEADS DO NOT BECOME A NECKLACE BY CAUSING ONE ANOTHER",
         "a thread must hold the moments together")

def vis_flame_stream(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    xs=[w*.22,w*.40,w*.58,w*.76]; q=ease(u)
    for i,x in enumerate(xs):
        local=clamp(q*len(xs)-i)
        y=h*.45
        d.line((x,y+55,x,y+105),fill=(*INK,int(180*local)),width=5)
        flame=[(x,y-50),(x-28,y+15),(x,y+45),(x+28,y+15),(x,y-50)]
        d.polygon(flame,fill=(*mix(PALE_GOLD,GOLD,.35),int(190*local)),
                  outline=(*GOLD,int(220*local)))
        if i<len(xs)-1:
            arrow(d,(x+35,y),(xs[i+1]-35,y),(*VIOLET,int(160*local)),2,8)
    seal(im,"CONTINUITY WITHOUT AN UNCHANGING SUBSTANCE",
         "a flame can pass from wick to wick")

def vis_dynamic_self(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    # changing contents orbit one stable luminous center
    labels=[("PERCEPTION",CYAN),("MEMORY",VIOLET),("ACTION",GREEN),("FEELING",CRIMSON)]
    for i,(lab,col) in enumerate(labels):
        a=t*.35+i*math.tau/len(labels)
        r=170
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.60
        glow_circle(im,x,y,12,col,160,9)
        centered(d,(x,y+28),lab,font(FONT_SANS_BOLD,13),col)
    glow_circle(im,cx,cy,16,GOLD,190,12)
    for rr in range(35,190,30):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(65*q*(1-rr/210))),width=2)
    seal(im,"PERMANENCE DOES NOT MEAN FROZEN CONTENT",
         "movement appears to one reflexive subject")

def vis_prakasa_vimarsa(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; light=smoothstep(.05,.48,u); reflect=smoothstep(.38,.88,u)
    for rr in range(35,245,32):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(90*light*(1-rr/270))),width=3)
    pts=[]
    for i in range(150):
        q=i/149; a=q*math.tau*1.6+t*.35; r=w*.22*(.25+.75*q)
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r*.60))
    glow_line(im,partial(pts,reflect),CYAN,5,int(120+100*reflect),13)
    centered(d,(w*.28,h*.70),"PRAKĀŚA",font(FONT_SERIF_BOLD,27),GOLD)
    centered(d,(w*.72,h*.70),"VIMARŚA",font(FONT_SERIF_BOLD,27),CYAN)
    seal(im,"ILLUMINATION THAT IMPLICITLY KNOWS ITSELF",
         "the I is operative in how seconds belong together")

def vis_appearance_to(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    objects=[("VASE",CYAN,w*.25,h*.30),("ABSENCE",SILVER,w*.75,h*.30),
             ("MEMORY",VIOLET,w*.25,h*.56),("IDENTIFICATION",GREEN,w*.75,h*.56)]
    for i,(lab,col,x,y) in enumerate(objects):
        local=clamp(q*len(objects)-i)
        glow_circle(im,x,y,11,col,160,9)
        centered(d,(x,y+28),lab,font(FONT_SANS_BOLD,13),col)
        d.line((x,y,cx,cy),fill=(*col,int(95*local)),width=2)
    glow_circle(im,cx,cy,15,GOLD,190,11)
    seal(im,"APPEARANCE IS ALWAYS APPEARANCE-TO",
         "the self is the continuity within which different contents form one sequence")

def vis_distorted_memory(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    # room warps but support remains
    draw_room(d,cx,cy,1.0,mix(VIOLET,CRIMSON,q),210,age=q)
    if q>.55:
        for i in range(5):
            x=w*.25+i*w*.125
            d.line((x,h*.23,x+math.sin(i*2)*28*q,h*.60),
                   fill=(*CRIMSON,int(120*q)),width=3)
    glow_line(im,[(w*.22,h*.68),(w*.78,h*.68)],GOLD,5,200,12)
    seal(im,"CONTENT CAN BE FALSE WHILE THE ACT REMAINS FIRST-PERSON",
         "a distorted mirror still requires a surface")

def vis_neural_reconstruction(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    rng=random.Random(62); q=ease(u)
    nodes=[(rng.uniform(w*.18,w*.82),rng.uniform(h*.20,h*.62)) for _ in range(42)]
    for i,(x,y) in enumerate(nodes):
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*PALE_CYAN,210),outline=(*CYAN,150))
        if i>0 and i%3:
            px,py=nodes[i-1]
            d.line((px,py,x,y),fill=(*SILVER,90),width=2)
    # reactivation pattern
    for i,(x,y) in enumerate(nodes):
        local=clamp(q*8-(i%8))
        if local>0: glow_circle(im,x,y,8,VIOLET,int(100+90*local),8)
    seal(im,"THE PRESENT BRAIN CONSTRUCTS A USABLE PAST",
         "storage, reactivation, context, and prediction shape retrieval")

def vis_mechanism_ownership(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    # mechanism gears
    for i,r in enumerate((48,34,25)):
        x=left[0]+(i-1)*55; y=left[1]+(i%2)*30
        d.ellipse((x-r,y-r,x+r,y+r),outline=(*CYAN,180),width=4)
        for a in range(0,360,45):
            px=x+math.cos(math.radians(a))*r; py=y+math.sin(math.radians(a))*r
            d.line((x,y,px,py),fill=(*CYAN,100),width=2)
    centered(d,(left[0],h*.66),"HOW?",font(FONT_SERIF_BOLD,27),CYAN)
    glow_circle(im,*right,17,GOLD,190,12)
    centered(d,(right[0],h*.66),"MINE?",font(FONT_SERIF_BOLD,27),GOLD)
    glow_line(im,partial([left,(w*.50,h*.25),right],q),VIOLET,4,180,11)
    seal(im,"MECHANISM AND OWNERSHIP ARE NOT IDENTICAL QUESTIONS",
         "how a memory forms may not settle what makes it mine")

def vis_no_homunculus(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    # head outline
    d.ellipse((cx-180,cy-210,cx+180,cy+210),outline=(*INK,170),width=4)
    # tiny observer fades and regress appears
    tiny_alpha=int(220*(1-q))
    d.ellipse((cx-35,cy-55,cx+35,cy+15),outline=(*CRIMSON,tiny_alpha),width=4)
    d.line((cx,cy+15,cx,cy+90),fill=(*CRIMSON,tiny_alpha),width=4)
    if q>.35:
        for rr in range(30,220,30):
            d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                      outline=(*GOLD,int(85*q*(1-rr/250))),width=3)
    seal(im,"THE SELF IS NOT A TINY OBSERVER BEHIND THE BRAIN",
         "the regress ends in knowing that is present without becoming an object")

def vis_face_recognition(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.30,h*.40); right=(w*.70,h*.40); q=ease(u)
    # young and old faces
    for (x,y),age,col in [(left,0,CYAN),(right,1,VIOLET)]:
        d.ellipse((x-65,y-85,x+65,y+85),outline=(*col,190),width=4)
        d.ellipse((x-25,y-20,x-15,y-10),fill=(*INK,180))
        d.ellipse((x+15,y-20,x+25,y-10),fill=(*INK,180))
        d.arc((x-25,y+10,x+25,y+45),15,165,fill=(*INK,150),width=3)
        if age:
            for oy in (-45,0,45):
                d.line((x-48,y+oy,x-25,y+oy+5),fill=(*SILVER,100),width=2)
    glow_line(im,partial([left,(w*.50,h*.25),right],q),GOLD,5,210,13)
    if q>.60:
        centered(d,(w*.50,h*.66),"IT IS YOU",font(FONT_SERIF_BOLD,30),GREEN)
    seal(im,"RECOGNITION HOLDS DIFFERENCE INSIDE IDENTITY",
         "exact repetition is not required")

def vis_child_adult(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    y=h*.42; q=ease(u)
    # child
    d.ellipse((w*.28-25,y-110,w*.28+25,y-60),outline=(*CYAN,190),width=4)
    d.line((w*.28,y-60,w*.28,y+35),fill=(*CYAN,190),width=5)
    d.line((w*.28,y+35,w*.24,y+105),fill=(*CYAN,190),width=4)
    d.line((w*.28,y+35,w*.32,y+105),fill=(*CYAN,190),width=4)
    # adult
    d.ellipse((w*.72-34,y-150,w*.72+34,y-82),outline=(*VIOLET,190),width=4)
    d.line((w*.72,y-82,w*.72,y+55),fill=(*VIOLET,190),width=6)
    d.line((w*.72,y+55,w*.66,y+155),fill=(*VIOLET,190),width=5)
    d.line((w*.72,y+55,w*.78,y+155),fill=(*VIOLET,190),width=5)
    glow_line(im,partial([(w*.28,y),(w*.50,h*.26),(w*.72,y)],q),GOLD,5,210,13)
    seal(im,"CONTINUITY DOES NOT MEAN SAMENESS OF CONTENT",
         "changing states belong to one life")

def vis_ai_question(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    # machine memory graph
    nodes=[(cx-160,cy-80),(cx-40,cy-130),(cx+80,cy-80),(cx+160,cy+10),
           (cx+40,cy+110),(cx-100,cy+100)]
    for i,(x,y) in enumerate(nodes):
        glow_circle(im,x,y,10,CYAN,150,9)
        if i<len(nodes)-1: arrow(d,(x,y),nodes[i+1],(*SILVER,130),2,7)
    centered(d,(cx,h*.68),"I SAW THIS BEFORE",font(FONT_SERIF_BOLD,27),VIOLET)
    if q>.55:
        centered(d,(cx,h*.20),"COMPETENCE ≠ PROVEN SELF-PRESENCE",
                 font(FONT_SANS_BOLD,17),CRIMSON)
    seal(im,"FUNCTIONAL CONTINUITY LEAVES SUBJECTIVITY OPEN",
         "behaviour alone may not settle manifestation to a self")

def vis_meditative_inquiry(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    cx,cy=w*.50,h*.40; q=ease(u)
    contents=[("IMAGE",VIOLET,-170,-80),("EMOTION",CRIMSON,170,-80),
              ("INTERPRETATION",CYAN,-170,95),("AGE",GREEN,170,95)]
    for lab,col,ox,oy in contents:
        x=lerp(cx+ox,cx,q*.40); y=lerp(cy+oy,cy,q*.40)
        centered(d,(x,y),lab,font(FONT_SANS_BOLD,15),(*col,int(210*(1-q*.65))))
    for rr in range(35,220,30):
        d.ellipse((cx-rr,cy-rr*.60,cx+rr,cy+rr*.60),
                  outline=(*GOLD,int(80*q*(1-rr/250))),width=3)
    centered(d,(cx,cy),"WHAT MAKES 'THEN' POSSIBLE NOW?",
             font(FONT_SERIF_BOLD,24),GOLD)
    seal(im,"TURN FROM MEMORY'S CONTENT TO ITS CONTINUITY",
         "awareness spans the difference")

def vis_final(im,u,t,p):
    w,h=im.size; d=ImageDraw.Draw(im)
    left=(w*.25,h*.40); right=(w*.75,h*.40); q=ease(u)
    # past room fades
    draw_room(d,*left,.65,VIOLET,int(200*(1-q*.25)),age=.45)
    glow_circle(im,*right,16,CYAN,180,11)
    glow_line(im,partial([left,(w*.50,h*.25),right],q),GOLD,6,220,14)
    if q>.62:
        centered(d,(w*.50,h*.68),"I WAS THERE",font(FONT_SERIF_BOLD,31),GOLD)
    seal(im,"THE SELF APPEARS WHEREVER TWO MOMENTS BELONG TO ONE LIFE",
         "not as an object travelling between them, but as the luminous thread",GOLD)

VISUALS:dict[str,Callable]={
    "room":vis_room_memory,
    "moments":vis_discrete_moments,
    "vase":vis_vase_memory,
    "footprint":vis_footprint,
    "beads":vis_beads_thread,
    "flame":vis_flame_stream,
    "dynamic":vis_dynamic_self,
    "prakasa":vis_prakasa_vimarsa,
    "appearance_to":vis_appearance_to,
    "distortion":vis_distorted_memory,
    "neural":vis_neural_reconstruction,
    "ownership":vis_mechanism_ownership,
    "homunculus":vis_no_homunculus,
    "recognition":vis_face_recognition,
    "child_adult":vis_child_adult,
    "ai":vis_ai_question,
    "inquiry":vis_meditative_inquiry,
    "final":vis_final,
}

@dataclass
class Scene:
    title:str
    narration:str
    duration:float
    visual:str
    params:dict

SCENES=[
Scene("Lost room","You remember a room that no longer exists.",7.0,"room",{}),
Scene("Changed world","The wallpaper is gone. The people have aged. The body that entered it has replaced most of its material.",9.5,"room",{}),
Scene("First-person claim","Yet the memory arrives with a quiet claim: I was there.",7.5,"room",{}),
Scene("One life","The self appears wherever two moments belong to one life.",7.0,"final",{}),

Scene("Recognition project","Pratyabhijñā asks what must remain present for perception, memory, recognition, exclusion, and action to work.",10.0,"moments",{}),
Scene("Momentary stream","Its Buddhist opponents analyze experience through momentary events joined by causal continuity.",9.0,"moments",{}),
Scene("Memory pressure","Utpaladeva argues that memory reveals a unity causal succession may not fully explain.",9.0,"beads",{}),

Scene("Blue vase","One cognition sees a blue vase. It ends. Later another cognition says: I saw that blue vase.",10.0,"vase",{}),
Scene("Residual trace","The later moment may inherit a residual trace from the earlier one.",7.5,"vase",{}),
Scene("Ownership problem","But causation alone does not obviously produce ownership.",7.5,"footprint",{}),
Scene("Footprint","A footprint can be caused by a foot. The footprint does not remember walking.",8.0,"footprint",{}),
Scene("My past","Why should inherited information appear as my own past?",7.5,"vase",{}),

Scene("Memory relation","Memory does not merely reproduce content. It relates that, then, and by me.",9.0,"vase",{}),
Scene("Necklace","Two beads do not become a necklace because the first caused the second. A thread must hold them together.",10.0,"beads",{}),

Scene("Buddhist answer","The Buddhist answer is sophisticated: continuity need not require an unchanging substance.",9.0,"flame",{}),
Scene("Flame","A flame passes from one wick to another. Later events inherit traces and preserve structure.",9.0,"flame",{}),
Scene("Modern plausibility","Brains change continuously. Memory is reconstructive. Identity may be causal, functional, and narrative.",9.5,"neural",{}),
Scene("Utpaladeva reply","Utpaladeva's Self is not frozen like a stone. It is dynamic consciousness retaining reflexive unity through change.",10.0,"dynamic",{}),

Scene("Vimarśa","This is the force of vimarśa: illumination that implicitly knows itself.",8.0,"prakasa",{}),
Scene("Lamp and consciousness","A lamp reveals objects but does not announce I illuminate. Consciousness can reveal and later relate the revelation to itself.",10.0,"prakasa",{}),
Scene("Operative I","The subject need not say I every second. The I is operative in how seconds belong together.",9.0,"dynamic",{}),

Scene("Appearance-to","A color does not merely appear. It appears to awareness.",7.0,"appearance_to",{}),
Scene("Easy to ignore","The to is easy to ignore because attention is captured by what appears.",7.5,"appearance_to",{}),
Scene("Stage of sequence","The self is not another item beside the vase. It is the continuity in which vase, absence, memory, and identification form one sequence.",10.0,"appearance_to",{}),

Scene("Fallible memory","Human memory changes. Details are lost. Events are reconstructed.",8.0,"distortion",{}),
Scene("False content","People confidently remember events that never happened.",7.0,"distortion",{}),
Scene("Structure remains","Even a mistaken memory still has the form: this belongs to my past.",8.5,"distortion",{}),
Scene("Distorted mirror","The problem concerns the structure of remembering, not perfect storage. A distorted mirror still requires a surface.",10.0,"distortion",{}),

Scene("Neural mechanisms","Neural ensembles change. Synapses strengthen or weaken. Hippocampal systems bind context.",9.5,"neural",{}),
Scene("Reconstruction","Reactivation reconstructs patterns. Prediction shapes retrieval. The present brain creates a usable past.",10.0,"neural",{}),
Scene("Two questions","These mechanisms matter, but mechanism and ownership are not identical questions.",9.0,"ownership",{}),
Scene("How versus mine","The neural process explains how the memory appears. Philosophy asks what makes it mine.",8.5,"ownership",{}),

Scene("Homunculus temptation","The temptation is to place a tiny observer behind the brain.",7.5,"homunculus",{}),
Scene("Regress","But anything seen by an internal observer would require another awareness to know that observer.",9.0,"homunculus",{}),
Scene("Self-luminous awareness","The regress ends not in a miniature soul-object, but in knowing present without becoming another object.",10.0,"homunculus",{}),

Scene("Changed face","You meet someone after many years. The face has changed. The voice is older.",8.0,"recognition",{}),
Scene("Misalignment","For a moment perception and memory do not align.",6.5,"recognition",{}),
Scene("It is you","Then: it is you.",6.0,"recognition",{}),
Scene("Difference inside identity","Recognition does not require exact repetition. It holds difference inside identity.",9.0,"recognition",{}),

Scene("Inward recognition","Pratyabhijñā turns this ordinary power inward.",7.0,"recognition",{}),
Scene("Not become Śiva","The formula is not: I have become Śiva.",6.5,"dynamic",{}),
Scene("Never other","It is: the one appearing as this limited I was never other than Śiva.",8.5,"dynamic",{}),

Scene("Child and adult","The child and adult are not the same state. Past and present are not collapsed.",8.5,"child_adult",{}),
Scene("One life","Continuity does not mean sameness of content. It means changing contents belong to one life.",9.0,"child_adult",{}),
Scene("Unity with variation","Unity is the capacity to sustain real variation without losing the thread.",8.5,"beads",{}),

Scene("Artificial systems","A model can store earlier states. A robot can identify an object encountered yesterday.",8.5,"ai",{}),
Scene("Report","A software agent can report: I saw this before.",6.5,"ai",{}),
Scene("Open question","Does functional continuity produce subjectivity? Behaviour alone may not settle it.",9.5,"ai",{}),
Scene("Competence and presence","Competence is observable. Self-presence is the difficult part.",7.5,"ai",{}),

Scene("Practical turn","The practical use is not to defend every story the ego tells.",7.5,"inquiry",{}),
Scene("Changing contents","Memories, identities, images, emotions, interpretations, and the felt age of the remembered self all change.",9.5,"inquiry",{}),
Scene("What spans difference","What allows that change to be noticed? Awareness spans the difference.",8.0,"inquiry",{}),
Scene("Then now","Not who was I then, but what is present now as the capacity to say then?",9.0,"inquiry",{}),

Scene("Return to room","You remember a room that no longer exists. The room appears again as an event in present consciousness.",9.0,"final",{}),
Scene("Past does not return","The past does not literally return. A current manifestation reaches backward and says: mine.",9.0,"final",{}),
Scene("Causal stream and recognition","A causal stream can pass information forward. Recognition binds the information into one life.",9.5,"final",{}),
Scene("Closing","The self appears wherever two moments belong to one life—not as an object travelling intact between them, but as the luminous thread through which the second can say of the first: I was there.",10.0,"final",{}),
]

def render_frame(scene,fi,count,w,h,seed):
    u=fi/max(1,count-1); t=u*scene.duration
    im=field(w,h,seed); VISUALS[scene.visual](im,u,t,scene.params); border(im)
    return im.convert("RGB")

def ffmpeg():
    x=shutil.which("ffmpeg")
    if not x: raise RuntimeError("ffmpeg required")
    return x

def encode_scene(i,fps):
    out=SCENES_DIR/f"scene_{i:03d}.mp4"
    subprocess.run([ffmpeg(),"-y","-framerate",str(fps),"-i",
                    str(FRAMES/f"scene_{i:03d}"/"%05d.jpg"),
                    "-c:v","libx264","-preset","medium","-crf","18",
                    "-pix_fmt","yuv420p","-movflags","+faststart",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def render_scene(i,s,fps,w,h,preview):
    fd=FRAMES/f"scene_{i:03d}"; fd.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    count=max(2,round(s.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(count*.33),int(count*.72),count-1]):
            render_frame(s,fi,count,w,h,i*10000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(count):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(s,fi,count,w,h,i*10000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(i,fps)

def concatenate(paths):
    txt=OUTPUT/"concat.txt"
    txt.write_text("\n".join(f"file '{p.resolve()}'" for p in paths),encoding="utf-8")
    out=OUTPUT/"self_two_moments.mp4"
    subprocess.run([ffmpeg(),"-y","-f","concat","-safe","0","-i",str(txt),
                    "-c","copy","-movflags","+faststart",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def export_timeline():
    cur=0.0; rec=[]
    for i,s in enumerate(SCENES,1):
        x=asdict(s); x["scene_id"]=f"scene_{i:03d}"; x["start_seconds"]=round(cur,3)
        cur+=s.duration; x["end_seconds"]=round(cur,3); rec.append(x)
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"the self appears wherever two moments belong to one life",
                             "scene_count":len(SCENES),"runtime_seconds":round(cur,3),
                             "shot_duration_range":[5,10],
                             "continuity_object":"gold ownership thread",
                             "scenes":rec},indent=2,ensure_ascii=False),encoding="utf-8")
    return p

def contact_sheet(w,h):
    tw=320; th=int(tw*h/w); cols=4; rows=math.ceil(len(SCENES)/cols)
    sheet=Image.new("RGB",(cols*tw,rows*(th+48)),IVORY)
    d=ImageDraw.Draw(sheet); f=font(FONT_SANS_BOLD,14)
    for i,s in enumerate(SCENES,1):
        c=max(2,round(s.duration*DEFAULT_FPS))
        im=render_frame(s,int(c*.72),c,w,h,i*10000+72); im.thumbnail((tw,th))
        x=((i-1)%cols)*tw; y=((i-1)//cols)*(th+48)
        sheet.paste(im,(x,y)); d.text((x+8,y+th+7),f"{i:02d}  {s.title}",font=f,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; sheet.save(p,quality=94); return p

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--fps",type=int,default=DEFAULT_FPS)
    p.add_argument("--width",type=int,default=DEFAULT_WIDTH)
    p.add_argument("--height",type=int,default=DEFAULT_HEIGHT)
    p.add_argument("--scene",type=int)
    p.add_argument("--preview",action="store_true")
    p.add_argument("--no-contact-sheet",action="store_true")
    return p.parse_args()

def main():
    a=parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True)
    SCENES_DIR.mkdir(parents=True,exist_ok=True)
    print(f"Timeline: {export_timeline()}")
    print(f"Scenes: {len(SCENES)}")
    print(f"Runtime: {sum(s.duration for s in SCENES)/60:.2f} minutes")
    if a.scene:
        if not 1<=a.scene<=len(SCENES): raise ValueError("scene out of range")
        print(render_scene(a.scene,SCENES[a.scene-1],a.fps,a.width,a.height,a.preview)); return
    rendered=[]
    for i,s in enumerate(SCENES,1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        r=render_scene(i,s,a.fps,a.width,a.height,a.preview)
        if not a.preview: rendered.append(r)
    if not a.no_contact_sheet: print(f"Contact sheet: {contact_sheet(a.width,a.height)}")
    if not a.preview: print(f"Final video: {concatenate(rendered)}")

if __name__=="__main__":
    main()
