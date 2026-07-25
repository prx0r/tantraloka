"""
ModernGL GPU render engine for platinum packs.
Headless: renders to offscreen framebuffer, reads pixels back to PIL Image.

Usage on GPU box:
    python engine.py --pack life_crosses_barriers --preview
    python engine.py --pack life_crosses_barriers --render --width 1920 --height 1080
"""
import argparse, json, math, re, struct, sys, time
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image


SHADER_DIR = Path(__file__).resolve().parent.parent / "shaders"


def load_shader(name: str) -> str:
    path = SHADER_DIR / f"{name}.glsl"
    if not path.exists():
        raise FileNotFoundError(f"Shader not found: {path}")
    src = path.read_text()
    # Resolve #include directives
    def resolve_include(match):
        inc_name = match.group(1)
        inc_path = SHADER_DIR / "include" / f"{inc_name}.glsl"
        if inc_path.exists():
            return inc_path.read_text()
        return f"// missing include: {inc_name}"
    src = re.sub(r'#include\s+"([^"]+)"', resolve_include, src)
    return src


def parse_palette(module) -> list[tuple[float, float, float, float]]:
    """Extract RGBA palette from a pack module's color constants."""
    palette = []
    for name in dir(module):
        if name.isupper() and not name.startswith("_") and not callable(getattr(module, name)):
            val = getattr(module, name)
            if isinstance(val, tuple) and len(val) in (3, 4):
                r, g, b = val[0]/255.0, val[1]/255.0, val[2]/255.0
                a = val[3]/255.0 if len(val) == 4 else 1.0
                palette.append((r, g, b, a))
                if len(palette) >= 16:
                    break
    return palette


class Engine:
    """ModernGL headless render engine. One context per process."""
    
    def __init__(self, width=1280, height=720, samples=4):
        self.width = width
        self.height = height
        
        self.ctx = moderngl.create_standalone_context(backend='egl')
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # HDR framebuffer (fp32, linear)
        self.hdr_fbo = self.ctx.framebuffer([
            self.ctx.renderbuffer((width, height), components=4, samples=samples, dtype='f4'),
        ])
        self.hdr_output = self.ctx.framebuffer([
            self.ctx.renderbuffer((width, height), components=4, dtype='f4'),
        ])
        
        # Fullscreen quad VAO (shared across all shaders)
        self.quad = self._fullscreen_quad()
        
        # Bloom ping-pong buffers
        self.bloom_buffers = {}
        for size in [(w, h) for w, h in [
            (width//2, height//2), (width//4, height//4),
            (width//8, height//8), (width//16, height//16)
        ]]:
            if w > 0 and h > 0:
                self.bloom_buffers[size] = self.ctx.framebuffer([
                    self.ctx.renderbuffer(size, components=4, dtype='f4'),
                ])
    
    def _fullscreen_quad(self):
        """VAO for a fullscreen triangle (covers entire viewport)."""
        buffer = self.ctx.buffer(np.array([
            -1.0, -1.0, 0.0, 0.0,
             3.0, -1.0, 2.0, 0.0,
            -1.0,  3.0, 0.0, 2.0,
        ], dtype='f4'))
        return self.ctx.vertex_array(
            self.ctx.program(
                vertex_shader='''
                    #version 330 core
                    in vec2 in_position;
                    in vec2 in_uv;
                    out vec2 v_uv;
                    void main() {
                        gl_Position = vec4(in_position, 0.0, 1.0);
                        v_uv = in_uv;
                    }
                ''',
                fragment_shader='''
                    #version 330 core
                    out vec4 f_color;
                    void main() { f_color = vec4(1.0); }
                ''',
            ),
            [(buffer, '2f 2f', 'in_position', 'in_uv')],
        )
    
    def render_scene(self, shader_name: str, u: float, t: float, 
                     palette: list | None = None, params: dict | None = None) -> Image.Image:
        """Render one frame at progress u. Returns PIL Image."""
        frag_src = load_shader(shader_name)
        
        prog = self.ctx.program(
            vertex_shader='''
                #version 330 core
                in vec2 in_position;
                in vec2 in_uv;
                out vec2 v_uv;
                void main() {
                    gl_Position = vec4(in_position, 0.0, 1.0);
                    v_uv = in_uv;
                }
            ''',
            fragment_shader=frag_src,
        )
        
        vao = self.ctx.vertex_array(prog, [
            (self.quad.buffer, '2f 2f', 'in_position', 'in_uv'),
        ])
        vao.vertices = 3
        
        # Set uniforms
        prog['u'] = u
        prog['t'] = t
        prog['iResolution'] = (float(self.width), float(self.height))
        
        if palette and 'iPalette' in prog:
            flat = []
            for c in palette[:16]:
                flat.extend(c[:4])
            flat += [0.0] * (64 - len(flat))
            prog['iPalette'].write(struct.pack('16f', *flat[:16]))
        
        if params:
            for k, v in params.items():
                if k in prog:
                    if isinstance(v, (int, float)):
                        prog[k] = v
                    elif isinstance(v, str):
                        prog[k] = int(v) if v.isdigit() else 0
        
        # Render to HDR framebuffer
        self.hdr_fbo.use()
        self.ctx.clear(1.0, 1.0, 1.0, 0.0)
        vao.render()
        
        # Copy to output
        self.ctx.copy_framebuffer(self.hdr_output, self.hdr_fbo)
        
        # Read pixels
        pixels = self.hdr_output.read(components=4, dtype='f4')
        img = Image.frombuffer('RGBA', (self.width, self.height), pixels, 'raw', 'RGBA', 0, -1)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return img.convert('RGB')
    
    def render_bloom(self, img: Image.Image, intensity: float = 0.3, threshold: float = 0.8) -> Image.Image:
        """Apply HDR bloom as post-process."""
        # Convert PIL to numpy float array
        arr = np.array(img, dtype=np.float32) / 255.0
        
        # Extract brights
        lum = np.dot(arr, np.array([0.2126, 0.7152, 0.0722]))
        bright = np.maximum(0.0, lum - threshold) / np.maximum(lum, 1e-6)
        bright_mask = arr * bright[:, :, np.newaxis]
        
        # Simple gaussian blur (can be done as separable passes on GPU)
        kernel = np.array([1, 6, 15, 20, 15, 6, 1], dtype=np.float32)
        kernel = kernel / kernel.sum()
        blurred = bright_mask.copy()
        for _ in range(3):  # multiple blur passes
            # Horizontal
            temp = np.zeros_like(blurred)
            for i in range(-3, 4):
                shift = np.roll(blurred, i, axis=1)
                temp += shift * kernel[i + 3]
            # Vertical
            blurred[:] = 0
            for i in range(-3, 4):
                shift = np.roll(temp, i, axis=0)
                blurred += shift * kernel[i + 3]
        
        # Add bloom back to original
        result = np.clip(arr + blurred * intensity, 0.0, 1.0)
        
        # Tone map (simple Reinhard)
        result = result / (result + 1.0)
        
        # Gamma correct
        result = np.power(result, 1.0 / 2.2)
        
        return Image.fromarray((result * 255).astype(np.uint8))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=str, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--output", type=str, default="output")
    args = parser.parse_args()
    
    # Load pack
    import importlib
    spec = importlib.util.spec_from_file_location("pack", f"../{args.pack}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    palette = parse_palette(mod)
    scenes = mod.SCENES
    
    eng = Engine(args.width, args.height)
    
    for i, scene in enumerate(scenes[:1] if args.preview else scenes, 1):
        title = getattr(scene, 'title', f'scene_{i}')
        visual = getattr(scene, 'visual', None)
        dur = getattr(scene, 'duration', 6.0)
        params = getattr(scene, 'params', {})
        
        if args.preview:
            u = 0.72  # mature frame
            img = eng.render_scene(visual, u, u * dur, palette, params)
            img.save(f"{args.output}/scene_{i:03d}_preview.jpg")
            print(f"  Preview: scene_{i} @ u=0.72")
        else:
            print(f"  Rendering scene {i}/{len(scenes)}: {title}")
            # Not yet implemented for full render


if __name__ == "__main__":
    main()
