#!/usr/bin/env python3
import json, sys, os
from pathlib import Path

packs_dir = Path('/root/projects/tantraloka/newpacks')

for pack_dir in sorted(packs_dir.iterdir()):
    if not pack_dir.is_dir():
        continue
    py = pack_dir / 'render_pack.py'
    if not py.exists():
        continue
    
    code = py.read_text()
    
    # Extract SCENES list
    start = code.index('SCENES=[')
    depth = 0
    i = start + 7
    while i < len(code):
        if code[i] == '[': depth += 1
        elif code[i] == ']':
            depth -= 1
            if depth == 0: break
        i += 1
    scenes_code = code[start:i+1]
    
    # We need Scene class and helper functions defined
    # Extract them from the beginning of the file
    prefix = code[:start]
    
    # Build minimal exec environment
    exec_globals = {
        '__builtins__': __builtins__,
        'dataclass': __import__('dataclasses').dataclass,
        'Path': Path,
        'ImageFont': __import__('PIL.ImageFont'),
        'ImageDraw': __import__('PIL.ImageDraw'),
        'ImageFilter': __import__('PIL.ImageFilter'),
        'math': __import__('math'),
        'np': __import__('numpy'),
    }
    
    exec(prefix + '\n' + scenes_code, exec_globals)
    SCENES = exec_globals.get('SCENES', [])
    
    if not SCENES:
        print(f"{pack_dir.name}: no SCENES found")
        continue
    
    manifest = {
        'project': f'Tantraloka — {pack_dir.name}',
        'source_basis': f'Generated from Tantraloka',
        'fps': 10,
        'resolution': [1280, 720],
        'scene_duration_seconds': 4.8,
        'total_scenes': len(SCENES),
        'total_duration_seconds': len(SCENES) * 4.8,
        'scenes': []
    }
    for s in SCENES:
        manifest['scenes'].append({
            'id': s.id,
            'title': s.title,
            'subtitle': s.subtitle,
            'term': s.term,
            'mode': s.mode,
            'tags': s.tags,
            'duration_seconds': 4.8
        })
    
    manifest_path = pack_dir / 'scene_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"{pack_dir.name}: {len(SCENES)} scenes -> {manifest_path.name}")
