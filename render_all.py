#!/usr/bin/env python3
"""Match deepdive files to goldrender scenes and render videos."""
import re, os, sys, subprocess, math, glob
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
FPS = 10
DURATION = 6.0
NFRAMES = int(FPS * DURATION)
PARCHMENT = (240, 230, 208)
PARCHMENT_LIGHT = (248, 242, 226)
INK = (38, 31, 29)
UMBER = (76, 58, 45)
CRIMSON = (142, 43, 55)
SAFFRON = (204, 148, 57)
GOLD = (183, 142, 68)
GOLD_LIGHT = (235, 206, 128)
INDIGO = (52, 66, 107)
SLATE = (92, 97, 104)
WHITE = (250, 246, 237)
LOTUS_PINK = (191, 110, 132)

FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'

def layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def rgba(c, a=255):
    return (*c[:3], int(a))

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def lerp(a, b, t):
    return a + (b-a) * clamp(t)

def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))

def ease_in_out(t):
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi*t)

def smoothstep(a, b, x):
    if a == b: return 1.0 if x >= b else 0.0
    t = clamp((x-a)/(b-a))
    return t*t*(3-2*t)

def parchment(seed):
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = np.array(PARCHMENT, dtype=np.float32)
    coarse = rng.normal(0, 1, (40, 70)).astype(np.float32)
    cimg = Image.fromarray(np.uint8(np.clip((coarse-coarse.min())/(np.ptp(coarse)+1e-6)*255, 0, 255)))
    cimg = cimg.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    carr = (np.asarray(cimg).astype(np.float32)-128)/128
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += carr[..., None]*4.5 + fine[..., None]*1.6
    base = np.clip(base, 0, 255).astype(np.uint8)
    return Image.fromarray(base).convert('RGBA')

def draw_glow(im, xy, radius, color, alpha=160, blur=16):
    gl = layer(); d = ImageDraw.Draw(gl)
    x, y = xy
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgba(color, alpha))
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)

def draw_line_glow(im, pts, color, width=3, alpha=160, blur=10):
    gl = layer(); d = ImageDraw.Draw(gl)
    d.line(pts, fill=rgba(color, alpha), width=max(1, width*3), joint='curve')
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(gl)
    ImageDraw.Draw(im).line(pts, fill=rgba(color, min(255, alpha+70)), width=width, joint='curve')

def border(im):
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, W-28, H-28), outline=rgba(UMBER, 140), width=2)
    d.rectangle((42, 42, W-42, H-42), outline=rgba(GOLD, 120), width=1)

def wrap(text, font, max_w, draw):
    words = text.split()
    lines = []; cur = ''
    for w in words:
        test = cur + ' ' + w if cur else w
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def parse_deepdive(content):
    title = ''; sanskrit = ''; translation = ''
    for line in content.split('\n'):
        if line.startswith('# ') and not line.startswith('## '):
            title = line.replace('# ', '').strip()
            break
    if '**Sanskrit:**' in content:
        block = content.split('**Sanskrit:**')[1]
        m = re.search(r'```\s*\n(.+?)```', block, re.DOTALL)
        if m: sanskrit = m.group(1).strip()
    if '**Dyczkowski Translation:**' in content:
        block = content.split('**Dyczkowski Translation:**')[1].strip()
        lines = []
        for line in block.split('\n'):
            s = line.strip()
            if s.startswith('**') or s.startswith('---') or s.startswith('###'): break
            if s and not s.startswith('*'): lines.append(s)
        translation = ' '.join(lines)
        translation = re.sub(r'\*+', '', translation)
        translation = re.sub(r'\s+', ' ', translation).strip()
    return title, sanskrit, translation

def render_one(md_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(md_path) as f: content = f.read()
    title, sanskrit, translation = parse_deepdive(content)
    scene_id = Path(md_path).stem
    seed = hash(scene_id) % 100000
    
    if not translation:
        print(f"  SKIP: {scene_id} (no translation)")
        return None
    
    deva_font = ImageFont.truetype(FONT_DEVA, 26)
    serif_font = ImageFont.truetype(FONT_SERIF, 19)
    bold_font = ImageFont.truetype(FONT_BOLD, 28)
    small_font = ImageFont.truetype(FONT_SERIF, 14)
    wrapper = ImageDraw.Draw(Image.new('RGB', (1,1)))
    
    frames_dir = os.path.join(out_dir, f'frames_{scene_id}')
    os.makedirs(frames_dir, exist_ok=True)
    
    for i in range(NFRAMES):
        t = i / max(1, NFRAMES-1)
        im = parchment(seed + i)
        draw = ImageDraw.Draw(im)
        border(im)
        
        # Animated accent line
        prog = ease_in_out(t)
        draw.line((60, 72 + prog*50, W-60, 72 + prog*50), fill=rgba(GOLD, 200), width=2)
        
        # Title
        tw = draw.textbbox((0, 0), title, font=bold_font)
        draw.text((W//2, 40), title, font=bold_font, fill=INK, anchor='mt')
        
        # Sanskrit if available
        y_offset = 90
        if sanskrit:
            lines = wrap(sanskrit.strip(), deva_font, W - 100, wrapper)
            for l in lines[:4]:
                draw.text((W//2, y_offset), l, font=deva_font, fill=CRIMSON, anchor='mt')
                y_offset += 32
            y_offset += 10
        
        # Translation text with fade-in
        if translation:
            max_lines = int(prog * 20)
            lines = wrap(translation, serif_font, W - 100, wrapper)
            for idx, l in enumerate(lines[:min(max_lines, 18)]):
                alpha = min(255, int(255 * clamp((t * 2 - idx * 0.05))))
                draw.text((W//2, y_offset + idx * 26), l, font=serif_font, fill=rgba(INK, alpha), anchor='mt')
        
        # Footer
        draw.text((W//2, H - 25), scene_id, font=small_font, fill=GOLD, anchor='mb')
        
        path = os.path.join(frames_dir, f'frame_{i:04d}.jpg')
        im.convert('RGB').save(path, quality=92)
    
    out_mp4 = os.path.join(out_dir, f'{scene_id}.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS),
        '-i', os.path.join(frames_dir, 'frame_%04d.jpg'),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out_mp4], check=True)
    
    for f in os.listdir(frames_dir): os.remove(os.path.join(frames_dir, f))
    os.rmdir(frames_dir)
    return out_mp4

if __name__ == '__main__':
    deepdive_dir = '/root/projects/tantraloka/video-plans/deepdive'
    out_dir = '/root/projects/tantraloka/videos-from-deepdives'
    files = sorted(glob.glob(os.path.join(deepdive_dir, '*.md')))
    
    start_at = sys.argv[2] if len(sys.argv) > 2 else ''
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    
    done = 0
    for md in files:
        name = Path(md).stem
        if start_at and start_at not in name: continue
        out = os.path.join(out_dir, f'{name}.mp4')
        if os.path.exists(out) and os.path.getsize(out) > 50000:
            print(f"✓ {name}")
            done += 1
            continue
        print(f"▶ {name}...", end=' ', flush=True)
        render_one(md, out_dir)
        print(f"OK")
        done += 1
        if done >= limit: break
    
    print(f"\nDone: {done} videos")
    if done > 0:
        print(f"Output: {out_dir}/")
        total_size = sum(os.path.getsize(os.path.join(out_dir, f)) for f in os.listdir(out_dir) if f.endswith('.mp4'))
        print(f"Total: {total_size/1024/1024:.1f} MB")
