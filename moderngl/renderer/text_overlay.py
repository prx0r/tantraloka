"""
text_overlay.py — Post-render text compositing for GLSL scenes.

After the GPU renders a frame, this adds:
  - Scene title (top or bottom seal position)
  - Subtitle / narration label
  - Any fixed labels (MASS, WIDTH, etc.)

Uses Pillow ImageDraw with the pack's original fonts and colors.
This keeps the GLSL shaders fast and pure while restoring all text.

Usage in render loop:
    from text_overlay import compose_text
    frame = compose_text(gpu_frame, "CLIMB", "enough energy to cross",
                         font_path, ink_color)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def load_font(path: str, size: int) -> ImageFont.ImageFont:
    for candidate in (path, FONT_SERIF_BOLD, FONT_SANS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def compose_seal(im: Image.Image, title: str, subtitle: str = "",
                 title_color=(30, 32, 36), subtitle_color=(86, 89, 94)) -> Image.Image:
    """Add seal text at bottom of frame (matching pack's seal() convention)."""
    im = im.copy()
    w, h = im.size
    d = ImageDraw.Draw(im)

    title_font = load_font(FONT_SERIF_BOLD, max(22, int(h * 0.042)))
    sub_font = load_font(FONT_SANS, max(13, int(h * 0.020)))

    d.text((w / 2, h * 0.875), title, font=title_font, fill=title_color, anchor="mm")
    if subtitle:
        d.text((w / 2, h * 0.925), subtitle, font=sub_font, fill=subtitle_color, anchor="mm")

    return im


def compose_label(im: Image.Image, text: str, x: float, y: float,
                  color=(30, 32, 36), size: int | None = None,
                  font_path: str | None = None, anchor: str = "mm") -> Image.Image:
    """Add a text label at normalized position (x, y)."""
    im = im.copy()
    w, h = im.size
    d = ImageDraw.Draw(im)
    font_size = size or max(13, int(h * 0.020))
    font = load_font(font_path or FONT_SANS, font_size)
    d.text((w * x, h * y), text, font=font, fill=color, anchor=anchor)
    return im


def compose_full_scene(im: Image.Image, scene: dict) -> Image.Image:
    """Apply all text for a scene: seal + any fixed labels.
    
    scene dict can have:
      - 'seal_title': str
      - 'seal_subtitle': str  
      - 'labels': list of {'text': str, 'x': float, 'y': float, 'color': tuple, 'size': int}
    """
    if scene.get('seal_title'):
        im = compose_seal(im, scene['seal_title'], scene.get('seal_subtitle', ''))
    
    for label in scene.get('labels', []):
        im = compose_label(im, label['text'], label['x'], label['y'],
                          color=label.get('color', (30, 32, 36)),
                          size=label.get('size'))
    
    return im
