#!/usr/bin/env python3
"""Batch render all 369 deepdive files as videos."""
import re, os, subprocess, math, glob, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
FPS = 10
DURATION = 6.0
NFRAMES = int(FPS * DURATION)
PARCHMENT = (240, 230, 208)
INK = (38, 31, 29)
GOLD = (183, 142, 68)
FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
FONT_DEVA = '/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf'

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
    return Image.fromarray(base)

def border(draw, w, h):
    draw.rectangle([12, 12, w-12, h-12], outline=INK, width=2)
    draw.rectangle([18, 18, w-18, h-18], outline=GOLD, width=1)

def wrap(text, font, max_w, draw):
    words = text.split()
    lines = []
    cur = ''
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
    title = ''
    sanskrit = ''
    translation = ''
    
    for line in content.split('\n'):
        if line.startswith('# ') and not line.startswith('## '):
            title = line.replace('# ', '').strip()
            break
    
    # Extract Sanskrit
    if '**Sanskrit:**' in content:
        parts = content.split('**Sanskrit:**')
        if len(parts) > 1:
            block = parts[1]
            m = re.search(r'```\s*\n(.+?)```', block, re.DOTALL)
            if m:
                sanskrit = m.group(1).strip()
    
    # Extract translation
    if '**Dyczkowski Translation:**' in content:
        parts = content.split('**Dyczkowski Translation:**')
        if len(parts) > 1:
            block = parts[1].strip()
            lines = []
            for line in block.split('\n'):
                s = line.strip()
                if s.startswith('**') or s.startswith('---') or s.startswith('###'):
                    break
                if s and not s.startswith('*'):
                    lines.append(s)
            translation = ' '.join(lines)
            translation = re.sub(r'\*+', '', translation)
            translation = re.sub(r'\s+', ' ', translation).strip()
    
    return title, sanskrit, translation

def render_one(md_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    
    with open(md_path) as f:
        content = f.read()
    
    title, sanskrit, translation = parse_deepdive(content)
    scene_id = Path(md_path).stem
    seed = hash(scene_id) % 100000
    
    deva_font = ImageFont.truetype(FONT_DEVA, 28)
    serif_font = ImageFont.truetype(FONT_SERIF, 20)
    bold_font = ImageFont.truetype(FONT_BOLD, 26)
    small_font = ImageFont.truetype(FONT_SERIF, 16)
    wrapper = ImageDraw.Draw(Image.new('RGB', (1,1)))
    
    frames_dir = os.path.join(out_dir, 'frames_' + scene_id)
    os.makedirs(frames_dir, exist_ok=True)
    
    for i in range(NFRAMES):
        t = i / max(1, NFRAMES-1)
        im = parchment(seed + i)
        draw = ImageDraw.Draw(im)
        border(draw, W, H)
        
        # Title
        draw.text((W//2, 30), title, font=bold_font, fill=GOLD, anchor='mt')
        
        # Sanskrit
        if sanskrit:
            lines = wrap(sanskrit, deva_font, W - 80, wrapper)
            y = 90
            for l in lines[:6]:
                draw.text((W//2, y), l, font=deva_font, fill=INK, anchor='mt')
                y += 34
        
        # Translation
        if translation:
            lines = wrap(translation, serif_font, W - 100, wrapper)
            y = 200
            for l in lines[:15]:
                draw.text((W//2, y), l, font=serif_font, fill=INK, anchor='mt')
                y += 26
        
        draw.text((W//2, H - 25), f"Tantrāloka — {scene_id}", font=small_font, fill=GOLD, anchor='mb')
        
        path = os.path.join(frames_dir, f'frame_{i:04d}.jpg')
        im.convert('RGB').save(path, quality=92)
    
    out_mp4 = os.path.join(out_dir, f'{scene_id}.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS),
        '-i', os.path.join(frames_dir, 'frame_%04d.jpg'),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out_mp4], check=True)
    
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    os.rmdir(frames_dir)
    
    return out_mp4

if __name__ == '__main__':
    deepdive_dir = '/root/projects/tantraloka/video-plans/deepdive'
    out_dir = '/root/projects/tantraloka/videos-from-deepdives'
    
    files = sorted(glob.glob(os.path.join(deepdive_dir, '*.md')))
    print(f"Total deepdive files: {len(files)}")
    
    # If specific file given, render just that
    if len(sys.argv) > 1:
        files = [f for f in files if sys.argv[1] in f]
    
    for md in files[:1]:  # Start with 1 to test
        name = Path(md).stem
        out = os.path.join(out_dir, f'{name}.mp4')
        if os.path.exists(out) and os.path.getsize(out) > 100000:
            print(f"✓ {name} (exists)")
            continue
        print(f"Rendering {name}...", end=' ', flush=True)
        render_one(md, out_dir)
        print(f"✓")
