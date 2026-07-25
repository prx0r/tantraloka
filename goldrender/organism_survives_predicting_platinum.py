#!/usr/bin/env python3
"""organism_survives_predicting — Platinum visual essay"""
from __future__ import annotations
import argparse,json,math,random,shutil,subprocess
from dataclasses import dataclass,asdict; from pathlib import Path; from typing import Callable
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
ROOT=Path(__file__).resolve().parent; O=ROOT/f"output_{f}"; FRAMES=O/"frames"; SCENES_DIR=O/"scenes"
W,H,FPS=1280,720,10
IVORY=(249,247,241); WHITE=(255,254,250); INK=(29,33,39); SOFT=(86,91,98)
GOLD=(194,156,72); GL=(236,219,175); CYAN=(57,156,180); CRIMSON=(162,58,69); VIOLET=(109,83,153); GREEN=(70,139,99)
FS="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"; FSB=FS.replace("Serif","Serif-Bold"); FSN=FS.replace("Serif","Sans"); FSNB=FSN.replace("Sans","Sans-Bold")
def clamp(x,l=0.0,h=1.0): return max(l,min(h,x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def ss(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0; q=clamp((x-a)/(b-a)); return q*q*(3-2*q)
def ease(t): return .5-.5*math.cos(math.pi*clamp(t))
def lf(p,s):
    for c in (p,FS,FSN):
        try: return ImageFont.truetype(c,s)
        except: continue
    return ImageFont.load_default()
def rl(sz): return Image.new("RGBA",sz,(0,0,0,0))
def bg(w,h,s):
    rng=np.random.default_rng(s); a=np.empty((h,w,3),dtype=np.float32); a[:]=IVORY
    a+=rng.normal(0,.9,(h,w,1)); yy,xx=np.mgrid[0:h,0:w]
    halo=np.exp(-(((xx-w*.5)/(w*.37))**2+((yy-h*.40)/(h*.31))**2)*2.0)
    a[...,1]+=halo*3.5; a[...,2]+=halo*5.0
    im=Image.fromarray(np.clip(a,0,255).astype(np.uint8),"RGB").convert("RGBA")
    for i in range(14): d=ImageDraw.Draw(rl(im.size)); d.rounded_rectangle((20+i*3,20+i*3,w-20-i*3,h-20-i*3),radius=18,outline=(*INK,int(i*.7)),width=2)
    return im
def ct(d,xy,t,f,fill=INK): d.text(xy,t,font=f,fill=fill,anchor="mm")
def seal(im,t,s="",c=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    ct(d,(w/2,h*.875),t,lf(FSB,max(22,int(h*.04))),c)
    if s: ct(d,(w/2,h*.923),s,lf(FSN,max(13,int(h*.019))),SOFT)
def gc(im,x,y,r,col,al=170,bl=14):
    l=rl(im.size); ImageDraw.Draw(l).ellipse((x-r,y-r,x+r,y+r),fill=(*col,al))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(bl)))
    f=rl(im.size); ImageDraw.Draw(f).ellipse((x-r*.35,y-r*.35,x+r*.35,y+r*.35),fill=(*mix(col,WHITE,.35),min(255,al+50)))
    im.alpha_composite(f)
def gl(im,pts,col,w=4,al=210,bl=11):
    if len(pts)<2: return
    l=rl(im.size); ImageDraw.Draw(l).line(pts,fill=(*col,al),width=w*3,joint="curve")
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(bl)))
    f=rl(im.size); ImageDraw.Draw(f).line(pts,fill=(*mix(col,WHITE,.08),min(255,al+20)),width=w,joint="curve")
    im.alpha_composite(f)
def pp(pts,a):
    if not pts: return []; a=clamp(a); k=a*(len(pts)-1); i=int(k); f=k-i; o=list(pts[:i+1])
    if i+1<len(pts): p,q=pts[i],pts[i+1]; o.append((lerp(p[0],q[0],f),lerp(p[1],q[1],f)))
    return o
@dataclass
class Scene: title:str; narration:str; duration:float; visual:str; params:dict
