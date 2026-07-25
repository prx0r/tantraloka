#!/usr/bin/env python3
"""EVERYTHING IS EMPTY — A DIAGRAMMATIC ESSAY
Nāgārjuna's Mūlamadhyamakakārikā

DESIGN CONTRACT
---------------
• Every shot lasts 5-10 seconds.
• Every shot visibly performs the narrated operation.
• White scientific field; concept-led color only.
• No static slide layouts and no decorative loops.
• Platinum = emptiness-as-capacity, the space that allows
• Gold = dependent arising / relation
• Crimson = the error of grasping
• Cyan = middle way / the path between extremes
• Green = freedom, release
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: the empty cup persists across chapters.
"""

from __future__ import annotations

import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_sunyata"
FRAMES = OUTPUT / "frames"; SCENES_DIR = OUTPUT / "scenes"
W, H, FPS_DEF = 1280, 720, 10

WHITE = (248, 247, 243); INK = (30, 32, 36); SOFT = (86, 89, 94)
PLATINUM = (185, 195, 205); GOLD = (191, 154, 73); PALE_GOLD = (232, 216, 174)
CRIMSON = (158, 57, 66); PALE_CRIMSON = (229, 193, 197)
CYAN = (67, 157, 180); PALE_CYAN = (196, 226, 231)
GREEN = (72, 135, 101); PALE_GREEN = (196, 222, 206)
SILVER = (180, 186, 192)

FSERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FSB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FSANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FSNB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))
def lerp(a, b, t): return a + (b - a) * t
def mix(a, b, t):
    t = clamp(t); return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))
def smoothstep(a, b, x):
    if a == b: return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a)); return q * q * (3.0 - 2.0 * q)
def ease(t): t = clamp(t); return 0.5 - 0.5 * math.cos(math.pi * t)
def ease_out(t): t = clamp(t); return 1.0 - (1.0 - t) ** 3
def lf(path, size):
    for c in (path, FSERIF, FSANS):
        try: return ImageFont.truetype(c, size)
        except OSError: continue
    return ImageFont.load_default()

def rgl(sz): return Image.new("RGBA", sz, (0, 0, 0, 0))

def bg(w, h, seed):
    rng = np.random.default_rng(seed)
    arr = np.empty((h, w, 3), dtype=np.float32); arr[:] = WHITE
    arr += rng.normal(0, 0.8, (h, w, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

def seal(im, title, sub="", color=INK):
    d = ImageDraw.Draw(im); tw, th = im.size
    d.text((tw/2, th*0.875), title, font=lf(FSB, max(22, int(th*0.042))), fill=color, anchor="mm")
    if sub: d.text((tw/2, th*0.925), sub, font=lf(FSANS, max(13, int(th*0.020))), fill=SOFT, anchor="mm")

def border(im):
    w, h = im.size; d = ImageDraw.Draw(im)
    d.rounded_rectangle((25, 25, w-25, h-25), radius=17, outline=(*INK, 50), width=2)

def gc(im, cx, cy, r, color, alpha=180, blur=18):
    lay = rgl(im.size); d = ImageDraw.Draw(lay)
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(*color, alpha))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))
    c2 = rgl(im.size)
    ImageDraw.Draw(c2).ellipse((cx-r*.45, cy-r*.45, cx+r*.45, cy+r*.45), fill=(*mix(color, WHITE, .3), min(255, alpha+40)))
    im.alpha_composite(c2)

def gl(im, pts, color, width=4, glow=14, alpha=225):
    if len(pts) < 2: return
    lay = rgl(im.size); d = ImageDraw.Draw(lay)
    d.line(pts, fill=(*color, alpha), width=width, joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glow))); im.alpha_composite(lay)

def pp(points, prog):
    prog = clamp(prog)
    if len(points) < 2: return points
    ls = [math.dist(a, b) for a, b in zip(points[:-1], points[1:])]
    total = sum(ls); target = total * prog; out = [points[0]]; walked = 0.0
    for i, l in enumerate(ls):
        if walked + l <= target: out.append(points[i+1]); walked += l
        else:
            q = 0.0 if l == 0 else (target - walked) / l
            out.append((lerp(points[i][0], points[i+1][0], q), lerp(points[i][1], points[i+1][1], q)))
            break
    return out

# Visual modes
def v_empty_cup(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    cx, cy = w*0.50, h*0.42
    d.rounded_rectangle((cx-70, cy-45, cx+70, cy+45), radius=20, outline=(*PLATINUM, 200), width=4)
    d.rounded_rectangle((cx-55, cy-30, cx+55, cy+30), radius=14, outline=(*PLATINUM, 120), width=2)
    # Water filling
    fill_h = 55 * prog
    d.rounded_rectangle((cx-55, cy+30-fill_h, cx+55, cy+30), radius=8,
                        fill=(*PALE_CYAN, 180 if prog > 0.1 else 0))
    if prog > 0.7:
        gc(im, cx, cy+35-int(fill_h), 8, GOLD, 180, 8)
    seal(im, "EMPTINESS IS CAPACITY", "a cup must be hollow to hold water", PLATINUM)

def v_dependent_arising(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    # Causal chain as interconnected nodes
    nodes_x = [w*i/7 for i in range(1, 7)]
    nodes_y = [h*0.38 + 15*math.sin(i*1.7) for i in range(6)]
    for i in range(5):
        if prog > i/5:
            d.line((nodes_x[i], nodes_y[i], nodes_x[i+1], nodes_y[i+1]),
                   fill=(*GOLD, 200), width=3)
    for i, (x, y) in enumerate(zip(nodes_x, nodes_y)):
        gc(im, x, y, 12, mix(PLATINUM, GOLD, i/6), 190, 8)
        d.text((x, y), f"{i+1}", font=lf(FSNB, 11), fill=INK, anchor="mm")
    # A flame passes from wick to wick
    if prog > 0.6:
        p2 = clamp((prog-0.6)*2.5)
        for i in range(4):
            x = lerp(nodes_x[1], nodes_x[4], p2)
            offset = (i-1.5)*6
            d.polygon([(x+offset, nodes_y[2]-18), (x+offset-6, nodes_y[2]), (x+offset+3, nodes_y[2])],
                      fill=(*GOLD, int(180*p2)))
    seal(im, "DEPENDENT ARISING", "the flame is real — real as a process, not a thing", GOLD)

def v_time_relation(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    cy = h*0.42
    # A series of moments, each defined by relation to others
    pts = [(w*0.10, cy), (w*0.30, cy-40), (w*0.50, cy), (w*0.70, cy+40), (w*0.90, cy)]
    gl(im, pp(pts, prog), GOLD, 4, 13, 210)
    labels = ["past", "present", "future", "now"]
    xs = [w*0.20, w*0.40, w*0.60, w*0.80]
    for i, (lab, x) in enumerate(zip(labels, xs)):
        if prog > i*0.15:
            d.text((x, cy+60), lab, font=lf(FSNB, int(h*0.019)), fill=SOFT, anchor="mm")
    seal(im, "TIME IS A RELATION", "not a container in which events happen", GOLD)

def v_two_truths(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    # Same ocean, three perspectives
    cy = h*0.38
    for i in range(3):
        x = w*(0.20 + i*0.30)
        sz = lerp(15, 65, prog)
        col = [PLATINUM, CYAN, GOLD][i]
        gc(im, x, cy, int(sz), col, 160, 14)
        d.text((x, cy+sz+20), ["waves", "water", "H\u2082O"][i],
               font=lf(FSNB, int(h*0.020)), fill=col, anchor="mm")
    d.line((w*0.12, cy+sz+50, w*0.88, cy+sz+50), fill=(*SOFT, 80), width=2)
    d.text((w*0.50, cy+sz+70), "one reality — three perspectives",
           font=lf(FSANS, int(h*0.018)), fill=SOFT, anchor="mm")
    seal(im, "TWO TRUTHS", "ultimate and conventional — the same ocean", CYAN)

def v_emptiness_empty(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    cx, cy = w*0.50, h*0.38
    # A ladder reaching the roof
    ladder_pts = [(cx-15, cy+140), (cx-15, cy-60), (cx+15, cy-60), (cx+15, cy+140)]
    d.line((ladder_pts[0], ladder_pts[1]), fill=(*SOFT, 200), width=3)
    d.line((ladder_pts[2], ladder_pts[3]), fill=(*SOFT, 200), width=3)
    for i in range(8):
        y = lerp(cy+120, cy-40, i/7)
        d.line((cx-15, y, cx+15, y), fill=(*SOFT, 160), width=2)
    # Roof
    d.line((cx-100, cy-70, cx+100, cy-70), fill=(*INK, 180), width=4)
    # Foot kicking ladder when prog > 0.5
    if prog > 0.5:
        p2 = clamp((prog-0.5)*2)
        kick_angle = p2 * 0.3
        d.line((cx-15+60*p2, cy+140, cx-15+60*p2-40*p2, cy+140+40*p2),
               fill=(*CRIMSON, 200), width=3)
        d.text((w/2, cy+165), "even emptiness must be emptied",
               font=lf(FSANS, int(h*0.020)), fill=CRIMSON, anchor="mm")
    seal(im, "EMPTINESS OF EMPTINESS", "the ladder must be kicked away", CRIMSON)

def v_no_boundary(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    cx, cy = w*0.50, h*0.42
    # Two domains dissolving
    d.line((cx, 60, cx, h-60), fill=(*SOFT, int(180*(1-prog))), width=3)
    d.text((w*0.25, h*0.18), "sa\u1e43s\u0101ra", font=lf(FSNB, int(h*0.025)), fill=SOFT, anchor="mm")
    d.text((w*0.75, h*0.18), "nirv\u0101\u1e47a", font=lf(FSNB, int(h*0.025)), fill=SOFT, anchor="mm")
    if prog > 0.3:
        p2 = clamp((prog-0.3)/0.7)
        for i in range(40):
            x = lerp(w*0.15, w*0.85, i/39)
            y = h*0.42 + 30*math.sin(i*0.6 + t*2) * p2
            d.ellipse((x-2, y-2, x+2, y+2), fill=(*GOLD, int(100*p2)))
        d.text((w/2, h*0.68), "the boundary between the dream and the waking",
               font=lf(FSANS, int(h*0.018)), fill=GOLD, anchor="mm")
    seal(im, "NO DISTINCTION", "the limit of nirv\u0101\u1e47a is the limit of sa\u1e43s\u0101ra", GOLD)

def v_emptiness_meeting(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    # Two billiard balls that would collide — but instead, transparency allows meeting
    x1 = lerp(w*0.25, w*0.42, prog)
    x2 = lerp(w*0.75, w*0.58, prog)
    d.ellipse((x1-30, h*0.40-30, x1+30, h*0.40+30), outline=(*SOFT, 180), width=3)
    d.ellipse((x2-30, h*0.40-30, x2+30, h*0.40+30), outline=(*SOFT, 180), width=3)
    if abs(x2-x1) < 80:
        p2 = 1 - (abs(x2-x1)/80)
        gc(im, (x1+x2)/2, h*0.40, int(20+30*p2), GOLD, 200, 16)
        d.text((w/2, h*0.60), "meeting", font=lf(FSNB, int(h*0.022)), fill=GOLD, anchor="mm")
        d.text((w/2, h*0.68), "emptiness allows the beloved to enter",
               font=lf(FSANS, int(h*0.017)), fill=SOFT, anchor="mm")
    seal(im, "YOU ARE EMPTY", "that is why you can hold the whole universe", GOLD)

def v_final_recognition(im, u, t, p):
    d = ImageDraw.Draw(im); w, h = im.size; prog = ease(u)
    cx, cy = w*0.50, h*0.40
    # Expanding transparent vessel that contains everything
    for i in range(8):
        r = lerp(20, min(w,h)*0.40, prog) * (0.8+0.2*math.sin(i+t))
        alpha = int(180 * (1-i/8) * prog)
        d.ellipse((cx-r, cy-r*0.55, cx+r, cy+r*0.55), outline=(*PLATINUM, alpha), width=3)
        d.ellipse((cx-r+10, cy-r*0.55+10, cx+r-10, cy+r*0.55-10),
                  outline=(*PLATINUM, alpha//2), width=1)
    gc(im, cx, cy, 25, GOLD, 200, 16)
    # Stars inside the vessel
    for i in range(30):
        a = i*2*math.pi/30
        r = 30 + 80*prog
        x = cx + math.cos(a + t*0.1) * r
        y = cy + math.sin(a + t*0.1) * r * 0.5
        d.ellipse((x-2, y-2, x+2, y+2), fill=(*GOLD, int(100+80*prog)))
    seal(im, "YOU ARE A VERB", "not a thing — the space where existence touches its own hand", PLATINUM)

VS = {
    "cup": v_empty_cup, "arising": v_dependent_arising, "time": v_time_relation,
    "truths": v_two_truths, "ladder": v_emptiness_empty, "boundary": v_no_boundary,
    "meeting": v_emptiness_meeting, "final": v_final_recognition,
}

@dataclass
class Scene:
    title: str; dur: float; vis: str; params: dict
SCENES = [
    Scene("Emptiness is capacity", 6.0, "cup", {}),
    Scene("A cup must be hollow", 6.5, "cup", {}),
    Scene("Dependent arising", 8.0, "arising", {}),
    Scene("A flame passes from wick to wick", 7.5, "arising", {}),
    Scene("Time is a relation", 7.0, "time", {}),
    Scene("None fixed — all real", 6.5, "time", {}),
    Scene("Two truths", 8.0, "truths", {}),
    Scene("One reality, three perspectives", 7.5, "truths", {}),
    Scene("Emptiness of emptiness", 8.0, "ladder", {}),
    Scene("The ladder must be kicked away", 7.0, "ladder", {}),
    Scene("No distinction", 8.0, "boundary", {}),
    Scene("The boundary dissolves", 7.5, "boundary", {}),
    Scene("Emptiness allows meeting", 8.0, "meeting", {}),
    Scene("You are empty", 7.0, "meeting", {}),
    Scene("You are a verb", 8.0, "final", {}),
    Scene("The space where existence touches its own hand", 8.0, "final", {}),
]

def render_frame(sc, fi, fc, w, h, seed):
    u = fi/max(1, fc-1); t = u*sc.dur
    im = bg(w, h, seed)
    VS[sc.vis](im, u, t, sc.params)
    border(im)
    return im.convert("RGB")

def rf():
    exe = shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg required")
    return exe

def enc(si, fps):
    ff = rf()
    fd = FRAMES/f"scene_{si:03d}"; op = SCENES_DIR/f"scene_{si:03d}.mp4"
    subprocess.run([ff, "-y", "-framerate", str(fps), "-i", str(fd/"%05d.jpg"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(op)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return op

def rs(si, sc, fps, w, h, prev):
    fd = FRAMES/f"scene_{si:03d}"; fd.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    fc = max(2, round(sc.dur*fps))
    if prev:
        for oi, fi in enumerate([0, int(fc*.35), int(fc*.72), fc-1]):
            render_frame(sc, fi, fc, w, h, si*1000+fi).save(fd/f"prev_{oi:02d}.jpg", quality=95)
        return fd
    for fi in range(fc):
        p = fd/f"{fi:05d}.jpg"
        if not p.exists(): render_frame(sc, fi, fc, w, h, si*1000+fi).save(p, quality=95)
    return enc(si, fps)

def cat(paths):
    ff = rf(); cf = OUTPUT/"concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    op = OUTPUT/"sunyata_empty.mp4"
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(cf), "-c", "copy",
                    "-movflags", "+faststart", str(op)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return op

def timeline():
    c = 0.0; pl = []
    for i, sc in enumerate(SCENES, 1):
        pl.append({"scene_id": f"scene_{i:03d}", "title": sc.title, "duration": sc.dur,
                    "visual": sc.vis, "start": round(c,3), "end": round(c+sc.dur,3)})
        c += sc.dur
    (OUTPUT/"timeline.json").write_text(json.dumps({"runtime": round(c,3), "scenes": pl}, indent=2), encoding="utf-8")

def main():
    import argparse as ap
    p = ap.ArgumentParser()
    p.add_argument("--fps", type=int, default=FPS_DEF)
    p.add_argument("--width", type=int, default=W)
    p.add_argument("--height", type=int, default=H)
    p.add_argument("--scene", type=int)
    p.add_argument("--preview", action="store_true")
    a = p.parse_args()
    for d in (OUTPUT, FRAMES, SCENES_DIR): d.mkdir(parents=True, exist_ok=True)
    timeline()
    if a.scene:
        s = SCENES[a.scene-1]; print(rs(a.scene, s, a.fps, a.width, a.height, a.preview)); return
    r = []
    for i, sc in enumerate(SCENES, 1):
        print(f"[{i:02d}/{len(SCENES):02d}] {sc.title} ({sc.dur:.1f}s)")
        o = rs(i, sc, a.fps, a.width, a.height, a.preview)
        if not a.preview: r.append(o)
    if not a.preview: print(f"Final: {cat(r)}")
if __name__ == "__main__": main()
