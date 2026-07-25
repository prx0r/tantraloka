#!/usr/bin/env python3
"""
THE DENSITIES OF CONSCIOUSNESS — An Octave of Being
Platinum procedural visual essay — Law of One cosmology.

Adapted from:
The Law of One (Ra Material, 1981-1984)

DESIGN CONTRACT
---------------
• 5–10 seconds per shot.
• Every shot performs the spoken claim as a visible transformation.
• Clean ivory scientific field; no lined manuscript background.
• Each density has a distinct visual language.
• The octave structure is visible in every frame.
• Continuity object: a single photon of white light that is
  prismatically separated into the rays and then recombined.

PALETTE ROLES
-------------
RED     first density / being / ground
ORANGE  second density / growth / movement
YELLOW  third density / self-consciousness / choice
GREEN   fourth density / love / heart
BLUE    fifth density / wisdom / light
INDIGO  sixth density / balance / gateway
VIOLET  seventh density / unity / timeless
GOLD    the Logos / intelligent infinity

OUTPUT
------
output_law_of_one_densities/
"""

from __future__ import annotations

import argparse, json, math, random, shutil, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/HC_Volume_106427611/goldrender/output_law_of_one_densities")
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS = 1280, 720, 10

IVORY = (249, 247, 241); PAPER = (242, 239, 231); INK = (31, 36, 42)
SOFT_INK = (85, 91, 97); SILVER = (180, 187, 191); PALE_SILVER = (224, 228, 228)
WHITE = (255, 254, 250)
RAYS = {  # (name, color, pale, desc)
    1: ("RED", (194, 62, 62), (231, 181, 181), "being"),
    2: ("ORANGE", (211, 136, 65), (235, 207, 171), "growth"),
    3: ("YELLOW", (209, 185, 72), (234, 225, 178), "self"),
    4: ("GREEN", (68, 139, 99), (196, 225, 206), "love"),
    5: ("BLUE", (65, 125, 193), (185, 209, 234), "wisdom"),
    6: ("INDIGO", (85, 70, 165), (206, 199, 235), "gateway"),
    7: ("VIOLET", (158, 84, 175), (223, 197, 235), "unity"),
}
GOLD = (193, 155, 72); PALE_GOLD = (235, 218, 172)
CYAN = (55, 157, 178); PALE_CYAN = (194, 227, 233)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))
def lerp(a, b, t): return a + (b - a) * clamp(t)
def mix(a, b, t):
    t = clamp(t)
    return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))
def smoothstep(a, b, x):
    if a == b: return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a)); return q * q * (3 - 2 * q)
def ease(t): t = clamp(t); return 0.5 - 0.5 * math.cos(math.pi * t)
def pulse(t, speed=1.0, phase=0.0): return 0.5 + 0.5 * math.sin(math.tau * (speed * t + phase))

def font(p, size):
    for c in (p, FONT_SERIF, FONT_SANS):
        try: return ImageFont.truetype(c, size)
        except OSError: pass
    return ImageFont.load_default()

def layer(size): return Image.new("RGBA", size, (0, 0, 0, 0))

def scientific_field(w, h, seed):
    rng = np.random.default_rng(seed)
    base = np.empty((h, w, 3), dtype=np.float32); base[:] = IVORY
    fine = rng.normal(0, 0.95, (h, w, 1)); base += fine
    yy, xx = np.mgrid[0:h, 0:w]
    halo = np.exp(-(((xx-w*0.52)/(w*0.36))**2+((yy-h*0.39)/(h*0.30))**2)*2.1)
    base[..., 0] += halo*1.5; base[..., 1] += halo*4.0; base[..., 2] += halo*5.5
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

def centered(d, xy, text, fnt, fill=INK): d.text(xy, text, font=fnt, fill=fill, anchor="mm")

def border(im):
    w, h = im.size; d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 26, w-26, h-26), radius=18, outline=(*INK, 48), width=2)
    for x, y in ((52, 52), (w-52, 52), (52, h-52), (w-52, h-52)):
        d.line((x-9, y, x+9, y), fill=(*CYAN, 80), width=1)
        d.line((x, y-9, x, y+9), fill=(*CYAN, 80), width=1)

def seal(im, title, subtitle="", color=INK):
    w, h = im.size
    d = ImageDraw.Draw(im)
    tf = font(FONT_SERIF_BOLD, max(22, int(h*0.040)))
    sf = font(FONT_SANS, max(13, int(h*0.019)))
    centered(d, (w/2, h*0.875), title, tf, color)
    if subtitle: centered(d, (w/2, h*0.923), subtitle, sf, SOFT_INK)

def glow_circle(im, x, y, r, color, alpha=170, blur=16):
    gl = layer(im.size)
    ImageDraw.Draw(gl).ellipse((x-r, y-r, x+r, y+r), fill=(*color, int(alpha)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    core = layer(im.size)
    ImageDraw.Draw(core).ellipse((x-r*.38, y-r*.38, x+r*.38, y+r*.38),
                                  fill=(*mix(color, WHITE, .35), min(255, int(alpha)+55)))
    im.alpha_composite(core)

def glow_poly(im, poly, color, alpha=170, blur=16):
    gl = layer(im.size)
    ImageDraw.Draw(gl).polygon(poly, fill=(*color, int(alpha)))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))

def spiral_points(cx, cy, r_start, r_end, turns, phase=0.0, samples=200):
    pts = []
    for i in range(samples):
        q = i / (samples - 1)
        a = q * turns * math.tau + phase
        r = lerp(r_start, r_end, q)
        pts.append((cx + math.cos(a)*r, cy + math.sin(a)*r*0.5))
    return pts


def draw_ray_circle(im, cx, cy, r, level, phase=0.0, alpha=200):
    d = ImageDraw.Draw(im)
    name, color, pale, desc = RAYS[level]
    d.ellipse((cx-r, cy-r*0.5, cx+r, cy+r*0.5), outline=(*color, alpha), width=3)
    pulse_r = r + 4 * math.sin(phase + level)
    d.ellipse((cx-pulse_r, cy-pulse_r*0.5, cx+pulse_r, cy+pulse_r*0.5),
              outline=(*mix(color, WHITE, .3), alpha//2), width=2)

def draw_density_spiral(im, cx, cy, levels, phase=0.0, reveal=1.0):
    d = ImageDraw.Draw(im)
    for i in range(levels):
        q = (i + 1) / levels
        r = 20 + q * 150
        if q > reveal: break
        name, color, pale, desc = RAYS[i + 1]
        sp = spiral_points(cx, cy, r*0.3, r, 2 + i * 0.5, phase + i * 0.3)
        visible = int(len(sp) * min(1.0, (reveal - (i/levels)) * levels))
        if visible > 2:
            d.line(sp[:visible], fill=(*color, int(180 - i * 15)), width=3, joint="curve")


def vis_infinite_creator(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    for i in range(30):
        a = i * math.tau / 30 + t * 0.05
        r2 = 10 + i * 4 * r
        col = (255, 255, 255) if i % 5 == 0 else GOLD
        d.ellipse((cx-r2, cy-r2*0.5, cx+r2, cy+r2*0.5), outline=(*col, int(200-150*i/30)), width=2)
    if r > 0.5:
        q = (r-0.5)*2
        centered(d, (cx, cy), "INTELLIGENT INFINITY",
                 font(FONT_SERIF_BOLD, int(h*0.035)), (*GOLD, int(200*q)))
    seal(im, "THE ONE INFINITE CREATOR", "infinity became aware")

def vis_first_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[1]
    draw_ray_circle(im, cx, cy, 50, 1, t, int(180*r))
    if r > 0.3:
        spark = int(30 * (r - 0.3) / 0.7)
        for i in range(spark):
            a = random.uniform(0, math.tau); rr = random.uniform(10, 55)
            x = cx + math.cos(a) * rr; y = cy + math.sin(a) * rr * 0.5
            d.ellipse((x-2, y-2, x+2, y+2), fill=(*color, int(150 * pulse(t+i))))
    seal(im, "FIRST DENSITY — RED RAY", "the awareness of being — mineral and water")

def vis_second_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[2]
    draw_ray_circle(im, cx, cy, 60, 2, t, int(180*r))
    if r > 0.2:
        n = int(12 * (r - 0.2) / 0.8)
        for i in range(n):
            a = i * math.tau / n + t * 0.3
            r2 = 30 + 15 * math.sin(t + i)
            x = cx + math.cos(a) * r2; y = cy + math.sin(a) * r2 * 0.5
            d.ellipse((x-5, y-5, x+5, y+5), fill=(*pale, 200), outline=(*color, 160), width=2)
    seal(im, "SECOND DENSITY — ORANGE RAY", "growth and striving toward the light")

def vis_third_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[3]
    draw_ray_circle(im, cx, cy, 70, 3, t, int(180*r))
    if r > 0.3:
        q = (r - 0.3) / 0.7
        d.line((cx-30, cy-20, cx+30, cy+20), fill=(*color, int(150*q)), width=3)
        d.line((cx+30, cy-20, cx-30, cy+20), fill=(*color, int(150*q)), width=3)
    seal(im, "THIRD DENSITY — YELLOW RAY", "self-consciousness and the first choice")

def vis_fourth_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[4]
    draw_ray_circle(im, cx, cy, 80, 4, t, int(180*r))
    if r > 0.4:
        q = (r - 0.4) / 0.6
        n_buds = int(8 * q)
        for i in range(n_buds):
            a = i * math.tau / max(1, n_buds) + t * 0.2
            r2 = 40 + 15 * math.sin(t + i)
            x = cx + math.cos(a) * r2; y = cy + math.sin(a) * r2 * 0.5
            d.ellipse((x-8, y-8, x+8, y+8), fill=(*pale, int(180*q)), outline=(*color, int(150*q)), width=2)
            for j in range(3):
                ja = a + (j - 1) * 0.5
                d.line((x, y, x+math.cos(ja)*15, y+math.sin(ja)*10),
                       fill=(*color, int(80*q)), width=2)
    seal(im, "FOURTH DENSITY — GREEN RAY", "love — the heart center — group consciousness")

def vis_fifth_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[5]
    draw_ray_circle(im, cx, cy, 90, 5, t, int(180*r))
    if r > 0.4:
        q = (r - 0.4) / 0.6
        sp = spiral_points(cx, cy, 30, 80*q, 3 + 2*q, t*0.3)
        if len(sp) > 2:
            d.line(sp, fill=(*color, int(150*q)), width=3)
    seal(im, "FIFTH DENSITY — BLUE RAY", "wisdom — light and knowledge merged")

def vis_sixth_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[6]
    draw_ray_circle(im, cx, cy, 100, 6, t, int(180*r))
    if r > 0.5:
        q = (r - 0.5) * 2
        for i in range(6):
            a = i * math.tau / 6 + t * 0.1
            r2 = 40 + 20 * q
            x = cx + math.cos(a) * r2; y = cy + math.sin(a) * r2 * 0.5
            d.line((cx, cy, x, y), fill=(*color, int(100*q)), width=3)
            d.ellipse((x-6, y-6, x+6, y+6), fill=(*pale, int(150*q)), outline=(*color, int(120*q)), width=2)
    seal(im, "SIXTH DENSITY — INDIGO RAY", "balance — the gateway to intelligent infinity")

def vis_seventh_density(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    name, color, pale, desc = RAYS[7]
    draw_ray_circle(im, cx, cy, 110, 7, t, int(180*r))
    if r > 0.6:
        q = (r - 0.6) * 2.5
        glow_circle(im, cx, cy, 40*q, color, int(120*q), 20)
        if q > 0.5:
            centered(d, (cx, cy), "UNITY", font(FONT_SERIF_BOLD, int(h*0.040)),
                     (*mix(WHITE, color, 0.3), int(200*(q-0.5)*2)))
    seal(im, "SEVENTH DENSITY — VIOLET RAY", "union with the One — timeless")

def vis_octave(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx = w*0.50; r = ease(u)
    for level in range(1, 9):
        q = clamp(r * 8 - level + 1)
        if q <= 0: continue
        if level == 8:
            col, pale = GOLD, PALE_GOLD
            lbl = "8TH"
        else:
            name, col, pale, desc = RAYS[level]
            lbl = f"{level}TH"
        y_pos = h * (0.08 + level * 0.09)
        d.ellipse((cx-20*q, y_pos-12*q, cx+20*q, y_pos+12*q),
                  fill=(*pale, int(180*q)), outline=(*col, int(180*q)), width=2)
        if q > 0.5:
            centered(d, (cx, y_pos), lbl, font(FONT_SANS_BOLD, int(h*0.025)), col)
    if r > 0.6:
        centered(d, (cx, h*0.85), "THE GREAT OCTAVE",
                 font(FONT_SERIF_BOLD, int(h*0.030)), GOLD)
    seal(im, "ALL DENSITIES ARE ONE", "the eighth begins the next octave")

def vis_prism(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; rv = ease(u)
    # white light splits into colors
    for i, level in enumerate(range(1, 8)):
        q = clamp(rv * 10 - i)
        if q <= 0: continue
        name, color, pale, desc = RAYS[level]
        x = lerp(cx, w*0.10 + i * w*0.10, q)
        y = cy + (i - 3) * 20 * q
        d.ellipse((x-8, y-8, x+8, y+8), fill=(*color, int(200*q)), outline=(*pale, int(150*q)), width=2)
    # white light
    d.line((w*0.05, cy, cx-20, cy), fill=(*WHITE, int(200*rv)), width=4)
    # prism
    if rv > 0.3:
        q = (rv-0.3)/0.7
        d.polygon([(cx-10, cy-40), (cx+10, cy-40), (cx-10, cy+40)],
                  fill=None, outline=(*SILVER, int(150*q)), width=3)
    seal(im, "THE PRISM OF CONSCIOUSNESS", "one light — infinite refractions")

def vis_harvest(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    for i in range(30):
        q = clamp(r * 30 - i)
        if q <= 0: continue
        a = random.uniform(0, math.tau)
        rr = random.uniform(20, 100) * r
        x = cx + math.cos(a) * rr; y = cy + math.sin(a) * rr * 0.5
        level = random.randint(1, 7)
        name, color, pale, desc = RAYS[level]
        d.ellipse((x-4, y-4, x+4, y+4), fill=(*color, int(150*q)))
    if r > 0.5:
        q = (r-0.5)*2
        d.rounded_rectangle((cx-80, cy-20, cx+80, cy+20), radius=10,
                            fill=(*mix(WHITE, GOLD, 0.05), int(150*q)),
                            outline=(*GOLD, int(150*q)), width=3)
        centered(d, (cx, cy), "THE HARVEST", font(FONT_SANS_BOLD, int(h*0.028)), (*GOLD, int(200*q)))
        centered(d, (cx, cy+30), "sorted by vibration — not by judgment",
                 font(FONT_SANS, int(h*0.016)), SOFT_INK)
    seal(im, "THE HARVEST", "each goes to the density that matches their vibration")

def vis_final(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im); cx, cy = w*0.50, h*0.42; r = ease(u)
    draw_density_spiral(im, cx, cy, 7, t, r)
    if r > 0.6:
        q = (r-0.6)*2.5
        glow_circle(im, cx, cy, 20*q, GOLD, int(120*q), 18)
        if q > 0.5:
            centered(d, (cx, cy), "ONE", font(FONT_SERIF_BOLD, int(h*0.055)),
                     (*GOLD, int(200*(q-0.5)*2)))
    seal(im, "ALL IS ONE", "you are the Creator experiencing itself")


VISUALS = {
    "creator": vis_infinite_creator,
    "first": vis_first_density, "second": vis_second_density,
    "third": vis_third_density, "fourth": vis_fourth_density,
    "fifth": vis_fifth_density, "sixth": vis_sixth_density,
    "seventh": vis_seventh_density, "octave": vis_octave,
    "prism": vis_prism, "harvest": vis_harvest, "final": vis_final,
}


@dataclass
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

SCENES = [
    Scene("Intelligent Infinity","Infinity became aware of itself — the first knowing.",7.0,"creator",{}),
    Scene("The One Creator","The infinite is one. Many-ness is a finite concept.",7.0,"creator",{}),

    Scene("First Density","First density: the awareness of being — mineral, water, fire, wind.",6.5,"first",{}),
    Scene("Red Ray","Wakefulness without self-reference. The foundation.",7.0,"first",{}),

    Scene("Second Density","Second density: growth and striving toward the light.",6.5,"second",{}),
    Scene("Orange Ray","Movement, desire, the beginning of individuation.",7.0,"second",{}),

    Scene("Third Density","Third density: the first consciousness of spirit.",6.5,"third",{}),
    Scene("Yellow Ray","Self-consciousness — and the first choice between STO and STS.",8.0,"third",{}),
    Scene("The Veil","Forgetting is the tool — without it, choice would not be real.",7.5,"third",{}),

    Scene("Fourth Density","Fourth density: love — the green ray.",6.5,"fourth",{}),
    Scene("Green Ray","Variable physicality — consciousness becomes group.",7.0,"fourth",{}),
    Scene("The Heart","From green ray onward, the heart opens into service.",7.0,"fourth",{}),

    Scene("Fifth Density","Fifth density: wisdom — the blue ray.",6.5,"fifth",{}),
    Scene("Blue Ray","Light and knowledge merged — compassion through understanding.",7.0,"fifth",{}),

    Scene("Sixth Density","Sixth density: balance — the indigo ray.",6.5,"sixth",{}),
    Scene("Indigo Ray","STO and STS reconciled — the gateway to intelligent infinity.",8.0,"sixth",{}),

    Scene("Seventh Density","Seventh density: unity — the violet ray.",6.5,"seventh",{}),
    Scene("Violet Ray","Union with the One — timeless — the turning to the next octave.",7.5,"seventh",{}),

    Scene("The Octave","Eight densities form a great octave — the eighth begins the next.",7.0,"octave",{}),
    Scene("Sub-Densities","Within each density are seven sub-densities — infinite recursion.",7.0,"octave",{}),

    Scene("The Prism","White light splits into rays — one source, infinite expressions.",7.0,"prism",{}),
    Scene("One Light","All colors are the same light — all densities are one consciousness.",7.0,"prism",{}),

    Scene("The Harvest","Those finishing the cycle are sorted by their own vibration.",8.0,"harvest",{}),
    Scene("No Judgment","There is no judgment — only resonance. You choose your destination.",7.5,"harvest",{}),

    Scene("Closing","You are the Creator experiencing Itself. The journey is the destination.",8.0,"final",{}),
    Scene("Final Frame","All is One. One is All. You are That.",6.0,"final",{}),
]


def render_frame(scene, fi, fc, w, h, seed):
    u = fi / max(1, fc-1); t = u * scene.duration
    im = scientific_field(w, h, seed)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")

def ffmpeg_path():
    ff = shutil.which("ffmpeg")
    if not ff: raise RuntimeError("ffmpeg required"); return ff

def encode_scene(idx, fps):
    out = SCENES_DIR / f"scene_{idx:03d}.mp4"; fd = FRAMES / f"scene_{idx:03d}"
    subprocess.run([ffmpeg_path(), "-y", "-framerate", str(fps), "-i", str(fd/"%05d.jpg"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(out)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def render_scene(idx, scene, fps, w, h, preview):
    fd = FRAMES / f"scene_{idx:03d}"; fd.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    count = max(2, round(scene.duration * fps))
    if preview:
        for oi, fi in enumerate([0, int(count*.32), int(count*.72), count-1]):
            render_frame(scene, fi, count, w, h, idx*10000+fi).save(fd/f"preview_{oi:02d}.jpg", quality=95)
        return fd
    for fi in range(count):
        p = fd / f"{fi:05d}.jpg"
        if p.exists(): continue
        render_frame(scene, fi, count, w, h, idx*10000+fi).save(p, quality=95, subsampling=0)
    return encode_scene(idx, fps)

def concat(paths):
    cp = OUTPUT / "concat.txt"
    cp.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    final = OUTPUT / "law_of_one_densities.mp4"
    subprocess.run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(cp),
        "-c", "copy", "-movflags", "+faststart", str(final)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return final

def export_timeline():
    cursor = 0.0; recs = []
    for i, s in enumerate(SCENES, 1):
        item = asdict(s); item["scene_id"] = f"scene_{i:03d}"
        item["start_seconds"] = round(cursor, 3); cursor += s.duration
        item["end_seconds"] = round(cursor, 3); recs.append(item)
    p = OUTPUT / "narration_timeline.json"
    p.write_text(json.dumps({"title":"the densities of consciousness","scene_count":len(SCENES),
        "runtime_seconds":round(cursor,3),"shot_duration_range":[5,10],
        "continuity_object":"white light photon prismatically separated into rays",
        "palette_roles":{f"ray_{k}":f"{v[3]}" for k,v in RAYS.items()},"scenes":recs},
        indent=2, ensure_ascii=False), encoding="utf-8")
    return p

def contact_sheet(w, h):
    tw, th = 320, int(320*h/w); cols, rows = 4, math.ceil(len(SCENES)/4); ch = th+48
    sheet = Image.new("RGB", (cols*tw, rows*ch), IVORY); dc = ImageDraw.Draw(sheet)
    lf = font(FONT_SANS_BOLD, 14)
    for i, s in enumerate(SCENES, 1):
        cnt = max(2, round(s.duration*DEFAULT_FPS))
        im = render_frame(s, int(cnt*.72), cnt, w, h, i*10000+72)
        im.thumbnail((tw, th)); sl = i-1
        x, y = (sl%cols)*tw, (sl//cols)*ch
        sheet.paste(im, (x, y)); dc.text((x+9, y+th+7), f"{i:02d}  {s.title}", font=lf, fill=INK)
    p = OUTPUT/"contact_sheet.jpg"; sheet.save(p, quality=94); return p

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fps", type=int, default=DEFAULT_FPS)
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--scene", type=int)
    p.add_argument("--preview", action="store_true")
    p.add_argument("--no-contact-sheet", action="store_true")
    return p.parse_args()

def main():
    a = parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True); FRAMES.mkdir(parents=True, exist_ok=True); SCENES_DIR.mkdir(parents=True, exist_ok=True)
    tl = export_timeline(); total = sum(s.duration for s in SCENES)
    print(f"Timeline: {tl}\nScenes: {len(SCENES)}\nRuntime: {total/60:.2f} min")
    if a.scene:
        if not 1 <= a.scene <= len(SCENES): raise ValueError(f"--scene must be 1..{len(SCENES)}")
        print(render_scene(a.scene, SCENES[a.scene-1], a.fps, a.width, a.height, a.preview)); return
    rendered = []
    for i, s in enumerate(SCENES, 1):
        print(f"[{i:02d}/{len(SCENES):02d}] {s.title} ({s.duration:.1f}s)")
        rendered.append(render_scene(i, s, a.fps, a.width, a.height, a.preview))
    final = concat(rendered); print(f"Final: {final}")
    if not a.no_contact_sheet: print(f"Contact: {contact_sheet(a.width, a.height)}")
    print("Done.")

if __name__ == "__main__": main()
