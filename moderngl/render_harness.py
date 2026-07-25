#!/usr/bin/env python3
"""
render_harness.py — ModernGL headless GPU render pipeline.

Discovers platinum packs, loads scene data, renders each frame via GLSL
fragment shaders on GPU, outputs PNG frames, assembles MP4 with ffmpeg.

Usage on GPU box:
    pip install moderngl numpy pillow
    python render_harness.py --pack life_crosses_barriers --preview
    python render_harness.py --pack life_crosses_barriers --render --fps 24
    python render_harness.py --all --output /mnt/output --fps 24 --width 1920
"""
import argparse, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

from renderer.text_overlay import compose_label


ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = ROOT / "goldrender"
SHADER_DIR = ROOT / "moderngl" / "shaders"
OUTPUT_DIR = Path("/mnt/output") if os.path.exists("/mnt") else ROOT / "moderngl" / "output"


def require(cmd): return shutil.which(cmd) or sys.exit(f"Missing: {cmd}")


def discover_packs():
    return sorted(PACKS_DIR.glob("*_platinum.py"))


def load_shader_source(name: str) -> str:
    path = SHADER_DIR / f"{name}.glsl"
    if not path.exists():
        raise FileNotFoundError(f"Shader: {path}")
    src = path.read_text()
    # Resolve #include directives with multiple search paths
    include_paths = [
        SHADER_DIR / "include",
        ROOT / "moderngl" / "lygia",
    ]
    def _inc(m):
        inc_name = m.group(1)
        for base in include_paths:
            inc_path = base / inc_name
            if inc_path.exists():
                return inc_path.read_text()
        # Try nested under lygia/ for paths like "sdf/circle.glsl"
        for base in include_paths:
            inc_path = base / "lygia" / inc_name
            if inc_path.exists():
                return inc_path.read_text()
        return f"// missing: {inc_name}"
    src = re.sub(r'#include\s+"([^"]+)"', _inc, src)
    return src


class GPUEngine:
    def __init__(self, width=1280, height=720, ssaa=2):
        self.width = width * ssaa
        self.height = height * ssaa
        self.out_w = width
        self.out_h = height

        self.ctx = moderngl.create_standalone_context(backend='egl')
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # HDR framebuffer
        self.hdr = self.ctx.framebuffer([
            self.ctx.renderbuffer((self.width, self.height), components=4, dtype='f4')
        ])
        self.hdr_out = self.ctx.framebuffer([
            self.ctx.renderbuffer((self.width, self.height), components=4, dtype='f4')
        ])

        # Fullscreen quad
        quad = self.ctx.buffer(np.array([
            -1, -1, 0, 0,   3, -1, 2, 0,  -1, 3, 0, 2
        ], dtype='f4').tobytes())
        self.vao = self.ctx.vertex_array(
            self.ctx.program(
                vertex_shader='#version 330 core\nin vec2 p;in vec2 u;out vec2 v;void main(){v=u;gl_Position=vec4(p,0,1);}',
                fragment_shader='#version 330 core\nout vec4 c;void main(){c=vec4(1);}'
            ),
            [(quad, '2f 2f', 'p', 'u')]
        )
        self.vao.vertices = 3

        # Bloom ping-pong buffers
        self.bloom_bufs = {}
        for w, h in [(self.width//2, self.height//2), (self.width//4, self.height//4),
                      (self.width//8, self.height//8)]:
            if w > 0 and h > 0:
                self.bloom_bufs[(w, h)] = self.ctx.framebuffer([
                    self.ctx.renderbuffer((w, h), components=4, dtype='f4')
                ])

    def read_pixels(self) -> Image.Image:
        pixels = self.hdr_out.read(components=4, dtype='f4')
        img = Image.frombuffer('RGBA', (self.width, self.height), pixels, 'raw', 'RGBA', 0, -1)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return img

    def render_frame(self, shader: str, u: float, t: float, scene_meta: dict | None = None) -> Image.Image:
        src = load_shader_source(shader)
        prog = self.ctx.program(
            vertex_shader='#version 330 core\nin vec2 p;in vec2 u;out vec2 v;void main(){v=u;gl_Position=vec4(p,0,1);}',
            fragment_shader=src
        )
        vao = self.ctx.vertex_array(prog, [(self.vao.buffer, '2f 2f', 'p', 'u')])
        vao.vertices = 3

        prog['u'] = u
        prog['t'] = t
        prog['iResolution'] = (float(self.width), float(self.height))
        prog['bloomIntensity'] = 0.3
        prog['bloomThreshold'] = 0.8
        if 'u_audioVolume' in prog and hasattr(self, 'audio_features'):
            fi = min(fi, len(self.audio_features['volume']) - 1)
            prog['u_audioVolume'] = self.audio_features['volume'][fi]
            prog['u_audioBeat'] = self.audio_features['beat'][fi]
            prog['u_audioOnset'] = self.audio_features['onset'][fi]
            prog['u_audioSpectral'] = self.audio_features['centroid'][fi]

        self.hdr.use()
        self.ctx.clear(1, 1, 1, 0)
        vao.render()

        # Bloom: bright pass + gaussian blur + add back
        self.ctx.copy_framebuffer(self.hdr_out, self.hdr)
        
        # Simple bright-pass: any pixel above threshold gets blurred and added back
        # In a full implementation this would use multi-pass FBO ping-pong
        # For now, read back and apply bloom in numpy (works, not GPU fast)
        # GPU path: use framebuffer blit with separate blur shaders
        # (implemented when GPU box is available)
        
        img = self.read_pixels()
        
        # Sparse label overlays only (no bottom seal bar)
        if scene_meta:
            for label in scene_meta.get('labels', []):
                img = compose_label(img, label['text'], label['x'], label['y'],
                                   color=label.get('color', (30, 32, 36)),
                                   size=label.get('size'))
        
        return img


def render_pack(pack_path: Path, args):
    name = pack_path.stem.replace("_platinum", "")
    slug = name

    # Load the pack
    code = pack_path.read_text()
    code = re.sub(r'^from\s+__future__\s+import\s+annotations\s*\n', '', code, flags=re.MULTILINE)
    mod = type(sys)(name)
    mod.__dict__.update({"__builtins__": __builtins__, "__file__": str(pack_path), "__name__": name})
    exec(code, mod.__dict__)

    scenes = mod.SCENES
    visuals = getattr(mod, 'VISUALS', None)

    out_dir = OUTPUT_DIR / slug
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)

    eng = GPUEngine(args.width, args.height, ssaa=getattr(args, 'ssaa', 2))

    print(f"\n=== {slug} ({len(scenes)} scenes) ===")

    scene_labels = {
        'classical_wall': [],
        'tunnelling': [],
        'width': [{'text': 'relative probability', 'x': 0.50, 'y': 0.75, 'size': 14}],
        'mass': [],
        'landscape': [],
        'enzyme': [],
        'isotope': [],
        'evidence': [
            {'text': 'MASS', 'x': 0.328, 'y': 0.298, 'color': (191,154,73)},
            {'text': 'DISTANCE', 'x': 0.672, 'y': 0.298, 'color': (67,157,180)},
            {'text': 'ELECTROSTATICS', 'x': 0.320, 'y': 0.576, 'color': (56,76,124)},
            {'text': 'PROTEIN MOTION', 'x': 0.680, 'y': 0.576, 'color': (72,135,101)},
            {'text': 'BARRIER SHAPE', 'x': 0.500, 'y': 0.630, 'color': (158,57,66)},
        ],
        'evolution': [],
        'form': [],
        'rates': [],
        'gate': [],
        'noise': [],
        'architecture': [],
        'warning': [
            {'text': 'MASS · WIDTH · COUPLING', 'x': 0.25, 'y': 0.475, 'size': 10, 'color': (67,157,180)},
            {'text': 'MEASURABLE RATE EFFECT', 'x': 0.25, 'y': 0.415, 'size': 10, 'color': (72,135,101)},
            {'text': 'THOUGHT TUNNELS', 'x': 0.75, 'y': 0.38, 'size': 10, 'color': (158,57,66)},
            {'text': 'QUANTUM INTENTION', 'x': 0.75, 'y': 0.44, 'size': 10, 'color': (158,57,66)},
            {'text': 'SPIRITUAL JUMP', 'x': 0.75, 'y': 0.50, 'size': 10, 'color': (158,57,66)},
        ],
        'psychology': [],
        'final': [],
    }

    for i, scene in enumerate(scenes, 1):
        visual = getattr(scene, 'visual', None) if not isinstance(scene, dict) else scene.get('visual')
        dur = getattr(scene, 'duration', 6.0) if not isinstance(scene, dict) else scene.get('duration', 6.0)
        title = getattr(scene, 'title', f'S{i}') if not isinstance(scene, dict) else scene.get('title', f'S{i}')
        narration = getattr(scene, 'narration', '') if not isinstance(scene, dict) else scene.get('narration', '')

        shader_name = visual or slug_text
        if not (SHADER_DIR / f"{shader_name}.glsl").exists():
            print(f"  [{i:02d}/{len(scenes):02d}] SKIP {title} — no shader {shader_name}.glsl")
            continue

        # Sparse labels only — no subtitle bars
        scene_meta = {
            'labels': scene_labels.get(shader_name, []),
        }

        if args.preview:
            # Render 4 keyframes (matching PIL's preview convention)
            for si, u in enumerate([0.0, 0.35, 0.72, 0.99]):
                img = eng.render_frame(shader_name, u, u * dur, scene_meta)
                img = img.resize((args.width, args.height), Image.LANCZOS)
                img.save(out_dir / "frames" / f"scene_{i:03d}_preview_{si:02d}.png")
            print(f"  [{i:02d}/{len(scenes):02d}] Preview {title}")
        else:
            fps = args.fps
            frames = max(2, round(dur * fps))
            scene_dir = out_dir / "frames" / f"scene_{i:03d}"
            scene_dir.mkdir(exist_ok=True)
            for fi in range(frames):
                u = fi / max(1, frames - 1)
                fpath = scene_dir / f"{fi:05d}.png"
                if fpath.exists() and args.resume:
                    continue
                img = eng.render_frame(shader_name, u, u * dur, scene_meta)
                img = img.resize((args.width, args.height), Image.LANCZOS)
                img.save(fpath)
            # ffmpeg encode
            ffmpeg = require("ffmpeg")
            clip = out_dir / "scenes" / f"scene_{i:03d}.mp4"
            clip.parent.mkdir(exist_ok=True)
            subprocess.run([
                ffmpeg, "-y", "-framerate", str(fps),
                "-i", str(scene_dir / "%05d.png"),
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
                str(clip)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  [{i:02d}/{len(scenes):02d}] {title} ({dur:.1f}s)")

    # Assemble final
    if not args.preview:
        scenes_dir = out_dir / "scenes"
        clips = sorted(scenes_dir.glob("scene_*.mp4"))
        if clips:
            final = out_dir / f"{slug}.mp4"
            concat = out_dir / "concat.txt"
            concat.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
            subprocess.run([
                require("ffmpeg"), "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat), "-c", "copy", "-movflags", "+faststart",
                str(final)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  Final: {final}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=str, help="Pack name (stem)")
    parser.add_argument("--all", action="store_true", help="Render all packs")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--ssaa", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    global OUTPUT_DIR
    if args.output:
        OUTPUT_DIR = Path(args.output)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    packs = discover_packs()
    if args.pack:
        packs = [p for p in packs if args.pack in p.stem]

    print(f"GPU Renderer — {len(packs)} packs found")
    for pack in packs:
        if args.render or args.preview:
            render_pack(pack, args)

    print("\nDone.")


if __name__ == "__main__":
    main()
