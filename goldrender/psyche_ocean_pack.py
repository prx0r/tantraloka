#!/usr/bin/env python3
"""YOUR MIND IS AN OCEAN
A Platinum-house procedural visual essay.

Source: expansion-essay30.md — Seth / Jane Roberts, The Nature of the Psyche

DESIGN CONTRACT
---------------
• Every shot lasts 5-10 seconds.
• Every shot visibly performs the narrated operation.
• White scientific field; concept-led color only.
• No static slide layouts and no decorative loops.
• Deep blue = the unbounded psyche
• Gold = conscious awareness / attention
• Cyan = boundaries / beliefs
• Salmon = the physical self
• Green = growth / recognition
• Sparse typography: terms function as seals, never paragraphs.
• Each mature frame around u=0.72 should work as a still.
• Continuity object: the horizon line persists across chapters.
"""

from __future__ import annotations

import argparse, json, math, random, shutil, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output_psyche_ocean"
FRAMES = OUTPUT / "frames"
SCENES_DIR = OUTPUT / "scenes"
DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS = 1280, 720, 10

WHITE = (248, 247, 243); PAPER = (242, 239, 232); INK = (30, 32, 36); SOFT_INK = (86, 89, 94)
DEEP_BLUE = (40, 60, 110); PALE_BLUE = (190, 210, 230); GOLD = (191, 154, 73); PALE_GOLD = (232, 216, 174)
CYAN = (67, 157, 180); PALE_CYAN = (196, 226, 231); SALMON = (198, 110, 100); PALE_SALMON = (230, 195, 190)
GREEN = (72, 135, 101); PALE_GREEN = (196, 222, 206); SILVER = (180, 186, 192)

FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))
def lerp(a, b, t): return a + (b - a) * t
def mix(a, b, t):
    t = clamp(t); return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))
def smoothstep(a, b, x):
    if a == b: return 1.0 if x >= b else 0.0
    q = clamp((x - a) / (b - a)); return q * q * (3.0 - 2.0 * q)
def ease(t): t = clamp(t); return 0.5 - 0.5 * math.cos(math.pi * t)
def ease_out(t): t = clamp(t); return 1.0 - (1.0 - t) ** 3
def pulse(t, hz=1.0, phase=0.0): return 0.5 + 0.5 * math.sin(math.tau * (hz * t + phase))

def load_font(path, size):
    for c in (path, FONT_SERIF, FONT_SANS):
        try: return ImageFont.truetype(c, size)
        except OSError: continue
    return ImageFont.load_default()

def rgba_layer(size): return Image.new("RGBA", size, (0, 0, 0, 0))

def background(width, height, seed):
    rng = np.random.default_rng(seed)
    arr = np.empty((height, width, 3), dtype=np.float32); arr[
    :,
    :,
] = WHITE
    arr += rng.normal(0, 1.0, (height, width, 1))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")

def seal(im, title, subtitle="", color=INK):
    w, h = im.size; d = ImageDraw.Draw(im)
    tf = load_font(FONT_SERIF_BOLD, max(22, int(h * 0.042)))
    sf = load_font(FONT_SANS, max(13, int(h * 0.020)))
    d.text((w/2, h*0.875), title, font=tf, fill=color, anchor="mm")
    if subtitle: d.text((w/2, h*0.925), subtitle, font=sf, fill=SOFT_INK, anchor="mm")

def border(im):
    w, h = im.size; d = ImageDraw.Draw(im)
    d.rounded_rectangle((25, 25, w-25, h-25), radius=17, outline=(*INK, 50), width=2)

def glow_circle(im, cx, cy, radius, color, alpha=180, blur=18):
    lay = rgba_layer(im.size); d = ImageDraw.Draw(lay)
    d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(*color, alpha))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))
    core = rgba_layer(im.size)
    ImageDraw.Draw(core).ellipse((cx-radius*.45, cy-radius*.45, cx+radius*.45, cy+radius*.45), fill=(*mix(color, WHITE, .30), min(255, alpha+40)))
    im.alpha_composite(core)

def glow_line(im, pts, color, width=4, glow=14, alpha=225):
    if len(pts) < 2: return
    lay = rgba_layer(im.size); d = ImageDraw.Draw(lay)
    d.line(pts, fill=(*color, alpha), width=width, joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(glow)))
    im.alpha_composite(lay)

def partial_polyline(points, progress):
    progress = clamp(progress)
    if len(points) < 2: return points
    lengths = [math.dist(a, b) for a, b in zip(points[:-1], points[1:])]
    total = sum(lengths); target = total * progress; out = [points[0]]; walked = 0.0
    for i, length in enumerate(lengths):
        if walked + length <= target: out.append(points[i+1]); walked += length
        else:
            q = 0.0 if length == 0 else (target - walked) / length
            ax, ay = points[i]; bx, by = points[i+1]
            out.append((lerp(ax, bx, q), lerp(ay, by, q))); break
    return out

# Visual modes
def visual_open_psyche(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    # Horizon
    cy = h * 0.50
    d.line((0, cy, w, cy), fill=(*DEEP_BLUE, 120), width=2)
    # Ocean below
    for i in range(60):
        x = w * i / 59
        yy = cy + 15 + 20 * math.sin(i * 0.8 + t)
        alpha = int(80 * prog)
        d.line((x, yy, x+20, yy+8*math.sin(i*0.8+t+0.5)), fill=(*DEEP_BLUE, alpha), width=1)
    # Sky above - open, unbounded
    for i in range(30):
        x = random.uniform(0, w); y = random.uniform(0, cy-20)
        r = random.uniform(1, 3)
        d.ellipse((x-r, y-r, x+r, y+r), fill=(*PALE_GOLD, int(30+120*prog)))
    seal(im, "THE PSYCHE IS NOT A THING", "it has no beginning or ending", DEEP_BLUE)

def visual_psyche_open(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    cy = h * 0.45
    # Waveform of expanding awareness
    pts = []
    for i in range(140):
        q = i / 139
        x = lerp(w*0.10, w*0.90, q)
        amp = lerp(10, 80, prog) * math.sin(q * math.pi * (1 + prog*2))
        y = cy + amp * math.sin(q * math.tau * 3 + t*2)
        pts.append((x, y))
    glow_line(im, partial_polyline(pts, prog), GOLD, 4, 13, 210)
    seal(im, "OPEN-ENDED", "no system is closed — psychological systems least of all", GOLD)

def visual_psyche_wanderer(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    # Figure at center
    cx, cy = w*0.50, h*0.45
    d.ellipse((cx-15, cy-45, cx+15, cy-15), outline=(*SALMON, 200), width=3)
    d.line((cx, cy-15, cx, cy+20), fill=(*SALMON, 200), width=3)
    d.line((cx, cy-5, cx-40, cy+15), fill=(*SALMON, 200), width=3)
    d.line((cx, cy-5, cx+40, cy+15), fill=(*SALMON, 200), width=3)
    # Landscape radiating from the figure
    for i in range(30):
        a = i * 2 * math.pi / 30
        r = lerp(10, 180, prog * (0.5 + 0.5*math.sin(i+t)))
        x = cx + math.cos(a + t*0.3) * r
        y = cy + math.sin(a + t*0.3) * r * 0.6
        col = mix(GOLD, DEEP_BLUE, (r/180))
        d.ellipse((x-3, y-3, x+3, y+3), fill=(*col, int(150*prog)))
    seal(im, "YOU ARE THE WANDERER", "and the vehicle, and the environment", SALMON)

def visual_psyche_boundless(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    # A frame that dissolves
    margin = lerp(60, 10, prog)
    d.rounded_rectangle((margin, margin*0.6, w-margin, h-margin*0.6),
                        radius=20, outline=(*CYAN, int(220*(1-prog))), width=4)
    d.rounded_rectangle((margin+20, margin*0.6+20, w-margin-20, h-margin*0.6-20),
                        radius=14, outline=(*CYAN, int(120*(1-prog))), width=2)
    # Light escaping
    for i in range(20):
        a = i * 2 * math.pi / 20
        r = 180 + 60 * prog
        x = w/2 + math.cos(a) * r
        y = h*0.45 + math.sin(a) * r * 0.5
        glow_circle(im, x, y, 6, GOLD, int(80*prog), 8)
    seal(im, "THE PSYCHE HAS NO WALLS", "it never did", DEEP_BLUE)

def visual_psyche_death(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    # Two states — waking and sleeping — as continuous
    cy = h * 0.45
    # Wave that continues through a "gap"
    pts = []
    for i in range(180):
        q = i / 179
        x = lerp(w*0.08, w*0.92, q)
        gap_start, gap_end = 0.40, 0.55
        in_gap = gap_start < q < gap_end
        if in_gap:
            amp = prog * 15 * math.exp(-8 * abs(q - 0.475) / 0.15)
        else:
            amp = 30 + 10 * math.sin(q * math.tau * 2)
        y = cy + amp * math.sin(q * math.tau * 4 + t*1.5)
        pts.append((x, y))
    glow_line(im, partial_polyline(pts, prog), DEEP_BLUE, 4, 14, 220)
    d.text((w*0.25, h*0.68), "life", font=load_font(FONT_SANS_BOLD, int(h*0.022)), fill=GOLD, anchor="mm")
    d.text((w*0.75, h*0.68), "death", font=load_font(FONT_SANS_BOLD, int(h*0.022)), fill=SOFT_INK, anchor="mm")
    if prog > 0.6:
        d.text((w*0.50, h*0.78), "a transition — nothing is lost",
               font=load_font(FONT_SANS, int(h*0.018)), fill=SOFT_INK, anchor="mm")
    seal(im, "DEATH IS A PHYSICAL BOUNDARY", "not a psychic one", DEEP_BLUE)

def visual_psyche_sexuality(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    # Spectrum — not binary
    cy = h * 0.45
    for i in range(80):
        q = i / 79
        x = lerp(w*0.10, w*0.90, q)
        col = mix(SALMON, DEEP_BLUE, q)
        r = 3 + 4 * math.sin(q * math.tau * 3 + t)
        alpha = int(180 * prog)
        d.ellipse((x-r, cy-r, x+r, cy+r), fill=(*col, alpha))
    d.text((w*0.50, h*0.68), "no strict sexual orientation",
           font=load_font(FONT_SANS_BOLD, int(h*0.020)), fill=SOFT_INK, anchor="mm")
    seal(im, "THE PSYCHE HAS NO GENDER", "every identity label is a costume", SALMON)

def visual_psyche_expression(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    cx, cy = w*0.50, h*0.40
    # Central source
    glow_circle(im, cx, cy, 20, GOLD, 180, 14)
    # Three channels radiating
    channels = [("love", SALMON, -0.15), ("desire", DEEP_BLUE, 0.0), ("art", GREEN, 0.15)]
    for i, (label, col, offset) in enumerate(channels):
        a = prog * 1.2
        end_x = cx + math.sin(offset * math.pi + a) * 220
        end_y = cy + math.cos(offset * math.pi + a) * 120 + 40
        sz = int(8 + 12 * (0.5+0.5*math.sin(t+i)))
        glow_circle(im, end_x, end_y, sz, col, 180, 10)
        d.line((cx, cy, end_x, end_y), fill=(*col, int(180*prog)), width=3)
        d.text((end_x, end_y+25), label, font=load_font(FONT_SANS_BOLD, int(h*0.019)), fill=col, anchor="mm")
    seal(im, "TO REPRESS ANY CHANNEL", "is to impoverish the whole", GOLD)

def visual_psyche_edge(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    cx, cy = w*0.50, h*0.55
    # Vast ocean
    for i in range(100):
        x = w * i / 99
        y_top = cy - 20 * math.sin(i * 0.3 + t)
        alpha = int(60 * prog)
        d.line((x, y_top, x, h), fill=(*DEEP_BLUE, alpha), width=1)
    # Small figure at the edge
    fig_x = w * lerp(0.30, 0.70, prog)
    fig_y = h*0.32
    d.ellipse((fig_x-10, fig_y-25, fig_x+10, fig_y-8), outline=(*SALMON, 200), width=3)
    d.line((fig_x, fig_y-8, fig_x, fig_y+10), fill=(*SALMON, 200), width=3)
    d.line((fig_x, fig_y-3, fig_x-28, fig_y+10), fill=(*SALMON, 200), width=3)
    d.line((fig_x, fig_y-3, fig_x+28, fig_y+10), fill=(*SALMON, 200), width=3)
    # Wall of belief dissolving
    if prog > 0.5:
        p2 = clamp((prog-0.5)*2)
        d.rounded_rectangle((100, 40, w-100, h-40), radius=30,
                            outline=(*CYAN, int(200*(1-p2))), width=4)
        d.text((fig_x, fig_y+40), "belief",
               font=load_font(FONT_SANS_BOLD, int(h*0.018)), fill=CYAN, anchor="mm")
    seal(im, "YOU ARE THE EDGE", "of a vast interior ocean breaking into physical form", DEEP_BLUE)

def visual_psyke_final(im, u, t, p):
    w, h = im.size; d = ImageDraw.Draw(im)
    prog = ease(u)
    cx, cy = w*0.50, h*0.42
    # Expanding rings
    for i in range(6):
        r = lerp(10, 260, prog) * (0.7 + 0.3*math.sin(i+t))
        alpha = int(180 * (1-i/6) * prog)
        d.ellipse((cx-r, cy-r*0.55, cx+r, cy+r*0.55), outline=(*DEEP_BLUE, alpha), width=3)
    # Center light
    glow_circle(im, cx, cy, 20, GOLD, 200, 16)
    for i in range(20):
        a = i * 2 * math.pi / 20
        r = 100 + 60 * math.sin(t + i*0.5)
        x = cx + math.cos(a + t*0.2) * r
        y = cy + math.sin(a + t*0.2) * r * 0.5
        d.ellipse((x-3, y-3, x+3, y+3), fill=(*GOLD, int(150*prog)))
    seal(im, "BECOME THE PSYCHE CONSCIOUSLY", "stop defending the walls that were never there", DEEP_BLUE)

VISUALS = {
    "open": visual_open_psyche,
    "unbounded": visual_psyche_open,
    "wanderer": visual_psyche_wanderer,
    "boundless": visual_psyche_boundless,
    "death": visual_psyche_death,
    "sexuality": visual_psyche_sexuality,
    "expression": visual_psyche_expression,
    "edge": visual_psyche_edge,
    "final": visual_psyke_final,
}

@dataclass
class Scene:
    title: str; narration: str; duration: float; visual: str; params: dict

SCENES =,Scene("The psyche is not a thing", "The psyche is open, unbounded, connected to every other psyche.", 6.0, "open", {})
Scene("Cannot be defined", "Language describes objects — the psyche is the context in which objects appear.", 7.0, "open", {})
Scene("The wanderer", "You are the wanderer — and the vehicle, and the environment.", 8.0, "wanderer", {})
Scene("You form the roads", "You form the roads as you go along — the psyche is not encased.", 7.5, "wanderer", {})
Scene("Open-ended", "No system is closed. Psychological systems least of all.", 6.5, "unbounded", {})
Scene("What is death?", "Death is a physical boundary — not a psychic one. Nothing is lost.", 8.0, "death", {})
Scene("The boundary dissolves", "The psyche holds the living and the dead in the same field.", 7.0, "death", {})
Scene("No gender", "The psyche has no sexual identification — every label is a costume.", 8.0, "sexuality", {})
Scene("Free from orientation", "Except for reproduction, the species is free to arrange its psychology.", 7.5, "sexuality", {})
Scene("Three channels", "Love, desire, art — each a translation of the same energy.", 7.0, "expression", {})
Scene("To repress any channel", "To repress any channel is to impoverish the whole.", 6.5, "expression", {})
Scene("The walls are belief", "The walls you think surround you are made of belief — not reality.", 8.0, "edge", {})
Scene("The edge of the ocean", "You are the edge of a vast interior ocean breaking into physical form.", 8.0, "edge", {})
Scene("Become the psyche", "The open system is a practical reality — experience it directly.", 9.0, "final", {})
Scene("Stop defending walls", "Stop defending the walls that were never there.", 6.0, "final", {})
Scene("The psyche is not a thing", "The psyche is open, unbounded, connected to every other psyche.", 6.0, "open", {})
Scene("Cannot be defined", "Language describes objects — the psyche is the context in which objects appear.", 7.0, "open", {})
Scene("The wanderer", "You are the wanderer — and the vehicle, and the environment.", 8.0, "wanderer", {})
Scene("You form the roads", "You form the roads as you go along — the psyche is not encased.", 7.5, "wanderer", {})
Scene("Open-ended", "No system is closed. Psychological systems least of all.", 6.5, "unbounded", {})
Scene("What is death?", "Death is a physical boundary — not a psychic one. Nothing is lost.", 8.0, "death", {})
Scene("The boundary dissolves", "The psyche holds the living and the dead in the same field.", 7.0, "death", {})
Scene("No gender", "The psyche has no sexual identification — every label is a costume.", 8.0, "sexuality", {})
Scene("Free from orientation", "Except for reproduction, the species is free to arrange its psychology.", 7.5, "sexuality", {})
Scene("Three channels", "Love, desire, art — each a translation of the same energy.", 7.0, "expression", {})
Scene("To repress any channel", "To repress any channel is to impoverish the whole.", 6.5, "expression", {})
Scene("The walls are belief", "The walls you think surround you are made of belief — not reality.", 8.0, "edge", {})
Scene("The edge of the ocean", "You are the edge of a vast interior ocean breaking into physical form.", 8.0, "edge", {})
Scene("Become the psyche", "The open system is a practical reality — experience it directly.", 9.0, "final", {})
Scene("Stop defending walls", "Stop defending the walls that were never there.", 6.0, "final", {})
Scene("The psyche is not a thing", "The psyche is open, unbounded, connected to every other psyche.", 6.0, "open", {})
Scene("Cannot be defined", "Language describes objects — the psyche is the context in which objects appear.", 7.0, "open", {})
Scene("The wanderer", "You are the wanderer — and the vehicle, and the environment.", 8.0, "wanderer", {})
Scene("You form the roads", "You form the roads as you go along — the psyche is not encased.", 7.5, "wanderer", {})
Scene("Open-ended", "No system is closed. Psychological systems least of all.", 6.5, "unbounded", {})
Scene("What is death?", "Death is a physical boundary — not a psychic one. Nothing is lost.", 8.0, "death", {})
Scene("The boundary dissolves", "The psyche holds the living and the dead in the same field.", 7.0, "death", {})
Scene("No gender", "The psyche has no sexual identification — every label is a costume.", 8.0, "sexuality", {})
Scene("Free from orientation", "Except for reproduction, the species is free to arrange its psychology.", 7.5, "sexuality", {})
Scene("Three channels", "Love, desire, art — each a translation of the same energy.", 7.0, "expression", {})
Scene("To repress any channel", "To repress any channel is to impoverish the whole.", 6.5, "expression", {})
Scene("The walls are belief", "The walls you think surround you are made of belief — not reality.", 8.0, "edge", {})
Scene("The edge of the ocean", "You are the edge of a vast interior ocean breaking into physical form.", 8.0, "edge", {})
Scene("Become the psyche", "The open system is a practical reality — experience it directly.", 9.0, "final", {})
Scene("Stop defending walls", "Stop defending the walls that were never there.", 6.0, "final", {}) [
    Scene("The psyche is not a thing", "The psyche is open, unbounded, connected to every other psyche.", 6.0, "open", {}),
    Scene("Cannot be defined", "Language describes objects — the psyche is the context in which objects appear.", 7.0, "open", {}),
    Scene("The wanderer", "You are the wanderer — and the vehicle, and the environment.", 8.0, "wanderer", {}),
    Scene("You form the roads", "You form the roads as you go along — the psyche is not encased.", 7.5, "wanderer", {}),
    Scene("Open-ended", "No system is closed. Psychological systems least of all.", 6.5, "unbounded", {}),
    Scene("What is death?", "Death is a physical boundary — not a psychic one. Nothing is lost.", 8.0, "death", {}),
    Scene("The boundary dissolves", "The psyche holds the living and the dead in the same field.", 7.0, "death", {}),
    Scene("No gender", "The psyche has no sexual identification — every label is a costume.", 8.0, "sexuality", {}),
    Scene("Free from orientation", "Except for reproduction, the species is free to arrange its psychology.", 7.5, "sexuality", {}),
    Scene("Three channels", "Love, desire, art — each a translation of the same energy.", 7.0, "expression", {}),
    Scene("To repress any channel", "To repress any channel is to impoverish the whole.", 6.5, "expression", {}),
    Scene("The walls are belief", "The walls you think surround you are made of belief — not reality.", 8.0, "edge", {}),
    Scene("The edge of the ocean", "You are the edge of a vast interior ocean breaking into physical form.", 8.0, "edge", {}),
    Scene("Become the psyche", "The open system is a practical reality — experience it directly.", 9.0, "final", {}),
    Scene("Stop defending walls", "Stop defending the walls that were never there.", 6.0, "final", {}),
]

def render_frame(scene, frame_index, frame_count, width, height, seed):
    u = frame_index / max(1, frame_count-1)
    t = u * scene.duration
    im = background(width, height, seed)
    VISUALS[scene.visual](im, u, t, scene.params)
    border(im)
    return im.convert("RGB")

def require_ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg required")
    return exe

def encode_scene(si, fps):
    ff = require_ffmpeg()
    fd = FRAMES / f"scene_{si:03d}"
    op = SCENES_DIR / f"scene_{si:03d}.mp4"
    subprocess.run([ff, "-y", "-framerate", str(fps), "-i", str(fd/"%05d.jpg"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(op)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return op

def render_scene(si, scene, fps, width, height, preview):
    fd = FRAMES / f"scene_{si:03d}"; fd.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    fc = max(2, round(scene.duration * fps))
    if preview:
        for oi, fi in enumerate([0, int(fc*.35), int(fc*.72), fc-1]):
            render_frame(scene, fi, fc, width, height, si*1000+fi).save(fd/f"preview_{oi:02d}.jpg", quality=95)
        return fd
    for fi in range(fc):
        p = fd / f"{fi:05d}.jpg"
        if not p.exists():
            render_frame(scene, fi, fc, width, height, si*1000+fi).save(p, quality=95)
    return encode_scene(si, fps)

def concatenate(paths):
    ff = require_ffmpeg()
    cf = OUTPUT / "concat.txt"
    cf.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    op = OUTPUT / "psyche_ocean.mp4"
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(cf), "-c", "copy", "-movflags", "+faststart", str(op)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return op

def export_timeline():
    cursor = 0.0; payload = []
    for i, sc in enumerate(SCENES, 1):
        r = asdict(sc); r["scene_id"] = f"scene_{i:03d}"; r["start"] = round(cursor, 3); r["end"] = round(cursor+sc.duration, 3)
        payload.append(r); cursor += sc.duration
    p = OUTPUT / "narration_timeline.json"
    p.write_text(json.dumps({"title": "your mind is an ocean", "runtime": round(cursor,3), "scenes": payload}, indent=2), encoding="utf-8")
    return p

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fps", type=int, default=DEFAULT_FPS)
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--scene", type=int, default=None)
    p.add_argument("--preview", action="store_true")
    return p.parse_args()

def main():
    args = parse_args()
    for d in (OUTPUT, FRAMES, SCENES_DIR): d.mkdir(parents=True, exist_ok=True)
    export_timeline()
    if args.scene:
        s = SCENES[args.scene-1]; print(render_scene(args.scene, s, args.fps, args.width, args.height, args.preview)); return
    rendered = []
    for i, sc in enumerate(SCENES, 1):
        print(f"[{i:02d}/{len(SCENES):02d}] {sc.title} ({sc.duration:.1f}s)")
        r = render_scene(i, sc, args.fps, args.width, args.height, args.preview)
        if not args.preview: rendered.append(r)
    if not args.preview: print(f"Final: {concatenate(rendered)}")

if __name__ == "__main__": main()
