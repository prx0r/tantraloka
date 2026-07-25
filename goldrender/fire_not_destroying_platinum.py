#!/usr/bin/env python3
"""
THE FIRE IS NOT DESTROYING YOU
A complete Platinum-house procedural visual essay.

Source adapted from:
expansion-essays/04_the_fire_is_not_destroying_you.md

DESIGN CONTRACT
---------------
• Every shot lasts 4-8 seconds.
• Every shot visibly performs the narrated operation.
• Clean ivory field; concept-led color only.
• No static slide layouts and no decorative loops.
• Ivory = the receptive field / the vessel
• Graphite = the unrefined / the part that resists change
• Gold = the goal / what survives every fire
• Crimson = nigredo / breakdown / the painful but necessary
• Amber = the fire that transforms / discrimination
• Emerald = the completed work / integration
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: the crucible vessel — reshaped across chapters.
"""

from __future__ import annotations
import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_fire_not_destroying"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
DW, DH, DFPS = 1280, 720, 10

IVORY = (248, 245, 239); PAPER = (242, 239, 232); WHITE = (252, 251, 248)
INK = (30, 32, 36); SOFT_INK = (86, 89, 94); WARM_GREY = (164, 160, 154)
GRAPHITE = (90, 85, 82); PALE_GRAPHITE = (182, 178, 174)
GOLD = (191, 154, 73); PALE_GOLD = (232, 216, 174); GOLD_LIGHT = (244, 224, 180)
CRIMSON = (158, 57, 66); PALE_CRIMSON = (229, 193, 197)
AMBER = (204, 140, 52); PALE_AMBER = (236, 210, 168)
EMERALD = (52, 130, 90); PALE_EMERALD = (184, 214, 194)
TEAL = (67, 157, 180); PALE_TEAL = (196, 226, 231)
SILVER = (180, 186, 192); LEAD = (116, 114, 112)
DARK = (24, 27, 32); WARM_DARK = (28, 26, 28)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))
def lerp(a,b,t): return a+(b-a)*clamp(t)
def mix(a,b,t): t=clamp(t); return tuple(int(lerp(x,y,t)) for x,y in zip(a,b))
def smoothstep(a,b,x):
    if a==b: return 1.0 if x>=b else 0.0
    q=clamp((x-a)/(b-a)); return q*q*(3.0-2.0*q)
def ease(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1.0-(1.0-t)**3

def load_font(path, size):
    for c in (path, FONT_SERIF, FONT_SANS):
        try: return ImageFont.truetype(c, size)
        except OSError: continue
    return ImageFont.load_default()

def rgba_layer(sz): return Image.new("RGBA", sz, (0,0,0,0))

def background(w, h, seed, bg=IVORY):
    rng = np.random.default_rng(seed)
    arr = np.empty((h, w, 3), dtype=np.float32); arr[:] = bg
    arr += rng.normal(0, 1.15, (h, w, 1))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGB").convert("RGBA")
    e = rgba_layer(im.size); d = ImageDraw.Draw(e)
    for i in range(14): alpha=int(i*0.7); ins=20+i*3; d.rounded_rectangle((ins,ins,w-ins,h-ins),radius=16,outline=(*INK,alpha),width=2)
    im.alpha_composite(e); return im

def ctext(d, xy, text, font, fill=INK): d.text(xy, text, font=font, fill=fill, anchor="mm")

def seal(im, title, subtitle="", color=INK):
    w,h=im.size; d=ImageDraw.Draw(im)
    tf=load_font(FONT_SERIF_BOLD, max(20,int(h*.038)))
    sf=load_font(FONT_SANS, max(11,int(h*.018)))
    ctext(d,(w/2,h*.875),title,tf,color)
    if subtitle: ctext(d,(w/2,h*.925),subtitle,sf,SOFT_INK)

def border(im):
    w,h=im.size; d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,25,w-25,h-25),radius=17,outline=(*INK,40),width=1)

def glow_circle(im,cx,cy,radius,color,alpha=180,blur=18):
    l=rgba_layer(im.size); ImageDraw.Draw(l).ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=(*color,alpha))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(blur)))

def glow_line(im,pts,color,width=4,glow=14,alpha=225):
    if len(pts)<2: return
    l=rgba_layer(im.size); ImageDraw.Draw(l).line(pts,fill=(*color,alpha),width=width,joint="curve")
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(glow))); im.alpha_composite(l)

def partial_polyline(points,progress):
    progress=clamp(progress)
    if len(points)<2: return points
    lengths=[math.dist(a,b) for a,b in zip(points[:-1],points[1:])]; total=sum(lengths)
    target=total*progress; out=[points[0]]; walked=0.0
    for i,ln in enumerate(lengths):
        if walked+ln<=target: out.append(points[i+1]); walked+=ln
        else: q=0.0 if ln==0 else (target-walked)/ln; ax,ay=points[i]; bx,by=points[i+1]; out.append((lerp(ax,bx,q),lerp(ay,by,q))); break
    return out

def crucible_bowl(d, cx, cy, w, h, col, width=3, alpha=210):
    d.arc((cx-w,cy-h,cx+w,cy+h),200,340,fill=(*col,alpha),width=width)
    d.arc((cx-w,cy-h,cx+w,cy+h),20,160,fill=(*col,alpha//2),width=max(1,width-1))
    d.line((cx-w,cy-5,cx-w+12,cy+h//2),fill=(*col,alpha),width=width)
    d.line((cx+w,cy-5,cx+w-12,cy+h//2),fill=(*col,alpha),width=width)

def flame(d, cx, cy, scale, col=AMBER, fill_col=None):
    if fill_col is None: fill_col=(*col,40)
    pts=[(cx,cy-50*scale),(cx-18*scale,cy-5*scale),(cx-6*scale,cy+28*scale),(cx+4*scale,cy+4*scale),(cx+16*scale,cy+34*scale),(cx+30*scale,cy-4*scale)]
    d.polygon(pts,outline=(*col,210),fill=fill_col)

@dataclass
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

def v_what_survives(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    glow_circle(im,cx,cy,15,GRAPHITE,80,10)
    d.ellipse((cx-28,cy-8,cx+28,cy+48),fill=(*PALE_GRAPHITE,160),outline=(*GRAPHITE,180),width=3)
    for i in range(5):
        q=clamp(prog*1.3-i*0.08)
        if q<=0: continue
        r=38+i*25
        d.ellipse((cx-r,cy+20-r*.6,cx+r,cy+20+r*.6),outline=(*mix(GRAPHITE,AMBER,i/4),int(100*q)),width=2)
    if prog>.4:
        p2=clamp((prog-.4)*1.5)
        flame(d,cx,cy+8,.6,AMBER)
    seal(im,"SOME PARTS OF YOU WILL SURVIVE ANYTHING","they adapt — they hide — they learn spiritual language — the impure material has not yet met the right fire")

def v_nigredo(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    for i in range(3):
        q=clamp(prog*1.3-i*0.1)
        if q<=0: continue
        r=90-i*25
        d.ellipse((cx-r,cy+10-r*.6,cx+r,cy+10+r*.6),outline=(*mix(GRAPHITE,CRIMSON,i/2),int(140*q)),width=3)
    for i in range(6):
        a=i*2*math.pi/6; r=lerp(20,90,prog); x=cx+math.cos(a)*r; y=cy+10+math.sin(a)*r*.6
        if prog>.2: d.line((cx,cy+10,int(x),int(y)),fill=(*LEAD,int(100*prog)),width=2)
    seal(im,"NIGREDO — THE BLACKENING","the beautiful surface collapses into darkness — what looked unified reveals incompatible substances hidden inside it")

def v_small_deaths(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    for i in range(6):
        y=140+i*38; phase=t*2.5+i*0.8; amp=20*math.sin(phase)*prog
        col=mix(GRAPHITE,SILVER,.5+.5*math.sin(phase))
        d.line((220,y+amp,1060,y+amp*.3),fill=(*col,int(120*prog)),width=2)
    for i in range(20):
        u2=i/19; x=lerp(200,1080,u2); y=cy+40+20*math.sin(u2*6+t*2)*prog
        d.ellipse((x-2,y-2,x+2,y+2),fill=(*mix(SILVER,LEAD,u2),int(80*prog)))
    seal(im,"MANY SMALL DEATHS BEFORE TRANSFORMATION","the material dissolves and re-forms repeatedly — the vessel was on the furnace, the alchemist inside another vessel")

def v_false_gold(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    d.ellipse((cx-90,cy-50,cx+90,cy+60),outline=(*mix(GOLD,PALE_GOLD,.4),int(180*prog)),width=3)
    d.ellipse((cx-80,cy-40,cx+80,cy+50),fill=(*PALE_GOLD,int(25*prog)))
    for i in range(5):
        q=clamp(prog*1.5-i*0.1)
        if q<=0: continue
        a=-.5+i*.25; x=cx+math.sin(a)*80; y=cy+5+math.cos(abs(a))*45
        d.line((int(x),int(y),int(x+math.sin(a)*20),int(y+math.cos(abs(a))*15)),fill=(*GRAPHITE,int(120*q)),width=3)
    glow_circle(im,cx,cy+5,12,GRAPHITE,int(50*prog),8)
    seal(im,"FALSE GOLD","the part that learns spiritual language while remaining exactly what it was — the surface gleams but the core has not changed")

def v_tria_prima(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    cols=[SILVER,AMBER,GRAPHITE]; labels=["MERCURY","SULPHUR","SALT"]; glows=[SILVER,AMBER,LEAD]
    for i in range(3):
        q=clamp(prog*1.3-i*0.08)
        if q<=0: continue
        a=-math.pi/2+i*2*math.pi/3; x=cx+math.cos(a)*110; y=cy+math.sin(a)*110*.65
        glow_circle(im,x,y,12,glows[i],int(50*q),10)
        d.ellipse((x-35,y-25,x+35,y+25),outline=(*cols[i],int(170*q)),fill=(*cols[i],int(12*q)),width=2)
        ctext(d,(x,y+38),labels[i],load_font(FONT_SANS_BOLD,int(h*.019)),cols[i])
    glow_circle(im,cx,cy,15,mix(GOLD,WHITE,.5),int(80*prog),12)
    d.ellipse((cx-7,cy-7,cx+7,cy+7),fill=(*WHITE,int(200*prog)))
    seal(im,"BODY, SOUL, AND SPIRIT — ONE THING EQUALLY PRESENT","mercury — sulfur — salt — the tria prima: equally present, equally transformed")

def v_the_right_fire(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    crucible_bowl(d,cx,cy+20,100,55,GRAPHITE,4,180)
    if prog>.15:
        p2=clamp((prog-.15)*1.5)
        pts=[(cx,cy-20-30*p2),(cx-22,cy-10-15*p2),(cx-8,cy+5),(cx+12,cy+3),(cx+24,cy-10-10*p2)]
        d.polygon(pts,fill=(*mix(AMBER,GOLD,.3),int(50*p2)),outline=(*mix(AMBER,GOLD,.5),int(160*p2)))
        glow_circle(im,cx,cy-10,int(10+20*p2),mix(AMBER,GOLD,.5),int(80*p2),14)
    seal(im,"THE RIGHT FIRE","it knows what to burn and what to leave — the fire does not hate what it burns, it is completing a transformation")

def v_dross_as_fuel(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    d.ellipse((cx-80,cy-50,cx+80,cy+50),outline=(*mix(GRAPHITE,GOLD,prog),int(160*prog)),width=3)
    for i in range(8):
        a=i*2*math.pi/8+t*.04; r_in=30; r_out=lerp(90,60,prog)
        x1=cx+math.cos(a)*r_in; y1=cy+math.sin(a)*r_in*.6
        x2=cx+math.cos(a)*r_out; y2=cy+math.sin(a)*r_out*.6
        glow_line(im,[(x1,y1),(x2,y2)],mix(LEAD,GOLD,prog),3,int(60+80*prog),5)
    glow_circle(im,cx,cy,int(15+25*prog),GOLD,int(80+80*prog),16)
    d.ellipse((cx-10,cy-10,cx+10,cy+10),fill=(*WHITE,int(200*prog)))
    seal(im,"THE DROSS IS NOT YOUR ENEMY — IT IS FUEL","the goal is not to remove the dross but to see it as fuel")

def v_contraries(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    dx=lerp(60,20,prog)
    d.ellipse((cx-60-dx,cy+20-30,cx-60+dx,cy+20+30),outline=(*mix(CRIMSON,GOLD,.3),int(180*prog)),width=3)
    ctext(d,(cx-60,cy+55),"REASON",load_font(FONT_SANS_BOLD,int(h*.017)),mix(CRIMSON,IVORY,.3))
    d.ellipse((cx+60-dx,cy+20-30,cx+60+dx,cy+20+30),outline=(*mix(TEAL,GOLD,.5),int(180*prog)),width=3)
    ctext(d,(cx+60,cy+55),"ENERGY",load_font(FONT_SANS_BOLD,int(h*.017)),mix(TEAL,IVORY,.3))
    if prog>.6:
        p2=clamp((prog-.6)*2.5)
        glow_circle(im,cx,cy+20,15,mix(GOLD,WHITE,.5),int(120*p2),12)
        d.ellipse((cx-8,cy+12,cx+8,cy+28),fill=(*WHITE,int(220*p2)))
        ctext(d,(cx,cy+55),"THE CHILD OF THE PHILOSOPHERS",load_font(FONT_SANS,int(h*.014)),GOLD)
    seal(im,"WITHOUT CONTRARIES — NO PROGRESSION","hold the opposites together until they generate a third")

def v_marriage(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    x1=lerp(400,600,prog); x2=lerp(880,680,prog)
    glow_circle(im,x1,cy+25,20,mix(GOLD,CRIMSON,.3),int(100*prog),14)
    d.ellipse((x1-14,cy+11,x1+14,cy+39),outline=(*mix(GOLD,CRIMSON,.3),int(180*prog)),width=2)
    glow_circle(im,x2,cy+25,20,mix(PALE_GOLD,SILVER,.5),int(100*prog),14)
    d.ellipse((x2-14,cy+11,x2+14,cy+39),outline=(*mix(PALE_GOLD,SILVER,.5),int(180*prog)),width=2)
    if abs(x1-x2)<40:
        glow_circle(im,cx,cy+25,30,mix(GOLD,WHITE,.5),int(140*prog),16)
        d.ellipse((cx-12,cy+13,cx+12,cy+37),fill=(*WHITE,int(220*prog)))
    seal(im,"THE SUPERCELESTIAL MARRIAGE","soul and body reconciled — not one destroyed for the other")

def v_philosophers_stone(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    for r in [30,50,70,90]:
        d.ellipse((cx-r,cy-r*.6,cx+r,cy+r*.6),outline=(*mix(GRAPHITE,GOLD,.2+.8*prog),120),width=2)
    glow_circle(im,cx,cy,int(10+35*prog),mix(GOLD,PALE_EMERALD,.5),int(150*prog),18)
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=(*WHITE,int(255*prog)),outline=(*mix(GOLD,EMERALD,.6),int(200*prog)),width=2)
    seal(im,"THE PHILOSOPHERS' STONE","a state you can become — not a thing you can hold")

def v_furnace(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    d.ellipse((cx-25,cy+10,cx+25,cy+55),outline=(*LEAD,160),width=3)
    d.line((cx,cy+55,cx,cy+105),fill=(*LEAD,140),width=3)
    d.line((cx,cy+30,cx-45,cy+70),fill=(*LEAD,120),width=2)
    d.line((cx,cy+30,cx+45,cy+70),fill=(*LEAD,120),width=2)
    if prog>.3:
        p2=clamp((prog-.3)/.7)
        glow_circle(im,cx,cy+30,int(10+30*p2),mix(AMBER,GOLD,.5),int(130*p2),16)
        pts=[(cx,cy+20-30*p2),(cx-20,cy+25-5*p2),(cx-8,cy+30+5*p2),(cx+12,cy+28),(cx+22,cy+22)]
        d.polygon(pts,fill=(*mix(AMBER,GOLD,.3),int(60*p2)),outline=(*mix(AMBER,GOLD,.5),int(180*p2)))
    seal(im,"YOU ARE THE FURNACE — THE FIRE IS ALREADY LIT","the work is underway — the only question is whether you will tend it")

def v_synthesis(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    # Crucible becoming luminous
    crucible_bowl(d,cx,cy+10,120,60,mix(GRAPHITE,GOLD,prog),4,170)
    glow_circle(im,cx,cy-20,int(20+50*prog),GOLD,int(120*prog),22)
    d.ellipse((cx-14,cy-34,cx+14,cy-6),fill=(*WHITE,int(220*prog)),outline=(*GOLD,int(200*prog)),width=2)
    if prog>.3:
        p2=clamp((prog-.3)*1.5)
        for i in range(12):
            a=-math.pi/2+(i-6)*.15; x=cx+math.cos(a)*100; y=cy-50+math.sin(a)*80
            glow_line(im,[(cx,cy-30),(int(x),int(y))],mix(GOLD,WHITE,.3),3,int(60*p2),6)
    seal(im,"SOME PARTS OF YOU WILL SURVIVE ALMOST ANYTHING","they are what the fire cannot touch — not through hardness, but through the integration the fire made possible")

def v_integration(im, u, t, p):
    w,h=im.size; d=ImageDraw.Draw(im); cx,cy=w*.50,h*.42; prog=ease(u)
    for i,r in enumerate([180,140,100,65,35]):
        q=clamp(prog*1.3-i*.07)
        if q<=0: continue
        col=mix(GRAPHITE,GOLD,i/4)
        d.ellipse((cx-r,cy-r*.6,cx+r,cy+r*.6),outline=(*col,int(140-20*i)*q),width=4-i)
    glow_circle(im,cx,cy,25,mix(GOLD,EMERALD,.3),int(180*prog),20)
    d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=(*WHITE,255),outline=(*GOLD,220),width=2)
    for i in range(16):
        a=i*2*math.pi/16+t*.03; r=170+20*pulse(t,.5,i)
        x=cx+math.cos(a)*r; y=cy+math.sin(a)*r*.6
        col=mix(GOLD,PALE_EMERALD,i/15)
        d.ellipse((x-4,y-4,x+4,y+4),fill=(*col,int(130*prog)))
    seal(im,"THE FIRE IS NOT DESTROYING YOU","it is revealing what the fire cannot burn — the work is not the removal of the dross but the revelation of the gold")

VISUALS = {
    "what_survives": v_what_survives, "nigredo": v_nigredo,
    "small_deaths": v_small_deaths, "false_gold": v_false_gold,
    "tria_prima": v_tria_prima, "right_fire": v_the_right_fire,
    "dross_as_fuel": v_dross_as_fuel, "contraries": v_contraries,
    "marriage": v_marriage, "stone": v_philosophers_stone,
    "furnace": v_furnace, "synthesis": v_synthesis,
    "integration": v_integration,
}

SCENES = [
    Scene("What Survives","Some parts of you will survive almost anything — new countries, new lovers, breakdowns, revelations.",5.5,"what_survives",{}),
    Scene("They Adapt","They hide — they learn spiritual language — they become more sophisticated while remaining exactly what they were.",5.5,"what_survives",{}),
    Scene("Wrong Fire","The alchemists had a name for this: the impure material had not yet met the right fire.",5.5,"what_survives",{}),
    Scene("Alchemy Remembered Wrong","Alchemy is usually remembered as a failed attempt to manufacture gold — that mistake takes the disguise for the work.",6.0,"what_survives",{}),
    Scene("The Laboratory as Theatre","Metals blackened, dissolved, separated, recombined — the operator watched physical substances lose their forms.",5.5,"nigredo",{}),
    Scene("The Process Watched the Operator","The vessel was on the furnace — the alchemist was inside another vessel.",5.0,"nigredo",{}),
    Scene("Nigredo — Blackening","The material putrefies — its previous structure breaks down.",5.0,"nigredo",{}),
    Scene("Incompatible Substances","What looked unified reveals incompatible substances hidden inside it.",5.0,"nigredo",{}),
    Scene("The Surface Collapses","The beautiful surface collapses into darkness, confusion, decay.",5.0,"nigredo",{}),
    Scene("Does Not Resemble Progress","This does not resemble spiritual progress — it feels like regression, failure, ruin.",5.5,"nigredo",{}),
    Scene("Right Diagnosis","But if the diagnosis is right, the fire is precisely what the material requires.",5.0,"right_fire",{}),
    Scene("Many Deaths","The process demands many deaths before transformation — not one dramatic event.",5.5,"small_deaths",{}),
    Scene("Repeated Dissolution","The material dissolves and re-forms repeatedly — each time slightly altered.",5.5,"small_deaths",{}),
    Scene("The Wheel of Operations","Purification is cyclical — calcination, dissolution, separation, conjunction.",6.0,"small_deaths",{}),
    Scene("False Gold","The part that can simulate transformation without changing — the spiritual bypass.",5.5,"false_gold",{}),
    Scene("Slick Surface","It learns the vocabulary, adopts the posture — the surface gleams, the core remains lead.",5.5,"false_gold",{}),
    Scene("The Fire Exposes","Real fire exposes the difference — the false gold cracks under sustained heat.",5.5,"false_gold",{}),
    Scene("Mercury — Sulfur — Salt","The tria prima: body, soul, and spirit — equally present at the same time.",6.0,"tria_prima",{}),
    Scene("Body","The vessel — the concrete particular — the place where transformation actually occurs.",5.5,"tria_prima",{}),
    Scene("Soul","The animating pattern — the character that persists through change.",5.5,"tria_prima",{}),
    Scene("Spirit","The deepest identity — what the process aims to liberate.",5.0,"tria_prima",{}),
    Scene("The Right Fire","The furnace that knows what to burn and what to leave — active discrimination.",5.5,"right_fire",{}),
    Scene("Not All Heat","Not every fire produces gold — some merely burns without transforming.",5.0,"right_fire",{}),
    Scene("Temperature of Wisdom","The right temperature is a wisdom — it varies with the material and the stage.",5.5,"right_fire",{}),
    Scene("The Dross","The parts you have been trying to eliminate are not mistakes — they are fuel.",5.5,"dross_as_fuel",{}),
    Scene("Fuel","The dross is not your enemy — the fire is not destroying you.",5.0,"dross_as_fuel",{}),
    Scene("Integration","The goal is not removal but integration — the lead must become part of the gold.",6.0,"dross_as_fuel",{}),
    Scene("Without Contraries","Reason and energy — mercy and severity — holding opposites until they generate a third.",6.0,"contraries",{}),
    Scene("The Third","The child of the philosophers — not a compromise but a new level of organization.",5.5,"contraries",{}),
    Scene("Tension","The tension between opposites is not a problem to eliminate — it is the engine of transformation.",5.5,"contraries",{}),
    Scene("Marriage","The reconciliation of body and soul — the supercelestial marriage.",5.5,"marriage",{}),
    Scene("Not Conquest","The spirit does not conquer the flesh — it marries it.",5.0,"marriage",{}),
    Scene("Soul and Body Reconciled","The goal is not liberation from embodiment but the embodiment of what has been liberated.",6.0,"marriage",{}),
    Scene("Philosophers' Stone","A state you can become — not a thing you can hold.",5.5,"stone",{}),
    Scene("Not a Prize","The stone is not a reward for good work — it is the condition of the one who has completed the work.",6.0,"stone",{}),
    Scene("The Furnace","You are the furnace — the fire is already lit.",5.0,"furnace",{}),
    Scene("Already Burning","The work is underway — the only question is whether you will tend it.",5.5,"furnace",{}),
    Scene("Not Someday","Transformation is not someday — it is now, in the heat already present.",5.5,"furnace",{}),
    Scene("Synthesis","Lead, tin, copper, gold — the sequence is not a metaphor for something else.",5.5,"synthesis",{}),
    Scene("Material and Spiritual","The alchemist knew the material and spiritual were one operation — the vessel mirrors the soul.",6.0,"synthesis",{}),
    Scene("What Survives","What emerges from the fire is not the same as what entered — and yet, recognizably, it is.",6.0,"synthesis",{}),
    Scene("Integration","All the previous stages are preserved in the completed work — nothing is wasted.",5.5,"integration",{}),
    Scene("The Completed Work","The stone is not a single color — it contains all colors, all stages, all fires.",6.0,"integration",{}),
    Scene("Closing","The fire is not destroying you — it is revealing what the fire cannot burn.",7.0,"integration",{}),
    Scene("Final","What remains after the fire is not ashes but the form the ashes were always trying to become.",7.5,"integration",{}),
]

def render_frame(scene, fi, fc, w, h, seed):
    u=fi/max(1,fc-1); t=u*scene.duration
    im=background(w,h,seed,mix(IVORY,PAPER,.5))
    VISUALS[scene.visual](im,u,t,scene.params)
    border(im); return im.convert("RGB")

def require_ffmpeg():
    if not (e:=shutil.which("ffmpeg")): raise RuntimeError("ffmpeg required"); return e

def encode_scene(idx, fps):
    ffmpeg=require_ffmpeg(); fd=FRAMES/f"scene_{idx:03d}"; out=SCENES_DIR/f"scene_{idx:03d}.mp4"
    subprocess.run([ffmpeg,"-y","-framerate",str(fps),"-i",str(fd/"%05d.jpg"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def render_scene(idx, scene, fps, w, h, preview):
    fd=FRAMES/f"scene_{idx:03d}"; fd.mkdir(parents=True,exist_ok=True); SCENES_DIR.mkdir(parents=True,exist_ok=True)
    nf=max(2,round(scene.duration*fps))
    if preview:
        for oi,fi in enumerate([0,int(nf*.35),int(nf*.72),nf-1]): render_frame(scene,fi,nf,w,h,idx*1000+fi).save(fd/f"preview_{oi:02d}.jpg",quality=95)
        return fd
    for fi in range(nf):
        p=fd/f"{fi:05d}.jpg"
        if not p.exists(): render_frame(scene,fi,nf,w,h,idx*1000+fi).save(p,quality=95,subsampling=0)
    return encode_scene(idx,fps)

def concat(paths):
    ffmpeg=require_ffmpeg(); c=OUTPUT/"concat.txt"
    c.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    out=OUTPUT/"fire_not_destroying.mp4"
    subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(c),"-c","copy","-movflags","+faststart",str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return out

def export_timeline():
    cur=0.0; payload=[]
    for idx,s in enumerate(SCENES,1):
        r=asdict(s); r["scene_id"]=f"scene_{idx:03d}"; r["start_seconds"]=round(cur,3); r["end_seconds"]=round(cur+s.duration,3)
        payload.append(r); cur+=s.duration
    p=OUTPUT/"narration_timeline.json"
    p.write_text(json.dumps({"title":"the fire is not destroying you","runtime_seconds":round(cur,3),"scene_count":len(SCENES),"palette_roles":{"graphite":"the unrefined","gold":"what survives","crimson":"nigredo","amber":"transformation","emerald":"integration"},"scenes":payload},indent=2,ensure_ascii=False),encoding="utf-8")
    return p

def contact_sheet(w,h):
    thumbs=[]; tw,th=320,int(320*h/w)
    for idx,s in enumerate(SCENES,1):
        nf=max(2,round(s.duration*DFPS)); im=render_frame(s,int(nf*.72),nf,w,h,idx*1000+72); im.thumbnail((tw,th)); thumbs.append((idx,s.title,im.copy()))
    cols=4; rows=math.ceil(len(thumbs)/cols); cell_h=th+48
    sheet=Image.new("RGB",(cols*tw,rows*cell_h),IVORY); d=ImageDraw.Draw(sheet)
    font=load_font(FONT_SANS_BOLD,14)
    for idx,t,im in thumbs:
        s=idx-1; x=(s%cols)*tw; y=(s//cols)*cell_h
        sheet.paste(im,(x,y)); d.text((x+8,y+th+10),f"{idx:02d}  {t}",font=font,fill=INK)
    p=OUTPUT/"contact_sheet.jpg"; sheet.save(p,quality=94); return p

def parse_args():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fps",type=int,default=DFPS); parser.add_argument("--width",type=int,default=DW); parser.add_argument("--height",type=int,default=DH)
    parser.add_argument("--scene",type=int); parser.add_argument("--preview",action="store_true")
    return parser.parse_args()

def main():
    args=parse_args()
    for d in (OUTPUT,FRAMES,SCENES_DIR): d.mkdir(parents=True,exist_ok=True)
    tl=export_timeline(); print(f"Timeline: {tl} | Scenes: {len(SCENES)} | Runtime: {sum(s.duration for s in SCENES)/60:.2f}m")
    if args.scene:
        if not 1<=args.scene<=len(SCENES): raise ValueError
        print(render_scene(args.scene,SCENES[args.scene-1],args.fps,args.width,args.height,args.preview)); return
    rendered=[]
    for idx,s in enumerate(SCENES,1):
        print(f"[{idx:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)"); r=render_scene(idx,s,args.fps,args.width,args.height,args.preview)
        if not args.preview: rendered.append(r)
    print(f"Contact: {contact_sheet(args.width,args.height)}")
    if not args.preview: print(f"Final: {concat(rendered)}")

if __name__=="__main__":
    main()
