#!/usr/bin/env python3
"""#66 AGG-style text prototype (M. Shemanarev, "Texts Rasterization Exposures"):
vertical-only hinting (FreeType light), unhinted (fractional) advances,
horizontal subpixel positioning at 1/3 px, optional LCD RGB output with a
soft 5-tap filter, blending in linear light with a coverage gamma.
Renders the probe lines of tests/wine/text-kern66.c (Tahoma 10/11 px bold,
simulated italic, regular) into a BMP-like PNG of the same layout, so it can
be compared pixel by pixel with Windows (kern66-q0.bmp) and Wine.

agg66.py OUT.png REGULAR.ttf BOLD.ttf [--scale N] [--mode rgb|gray] [--gamma G] [--weights a,b,c]
"""
import argparse, math
import numpy as np, freetype
from PIL import Image

WORDS = ["Open", "Background", "History", "Layers", "lena.jpeg"]
W, H = 260, 120

def render(out, regular, bold, scale=1, mode='rgb', gamma=2.2, weights=(1/3, 2/9, 1/9)):
    from fontTools.ttLib import TTFont
    faces = {False: freetype.Face(regular), True: freetype.Face(bold)}
    win_ascent = {False: TTFont(regular)['OS/2'].usWinAscent, True: TTFont(bold)['OS/2'].usWinAscent}
    sub = 3  # horizontal subpixels per pixel
    canvas = np.zeros((H * scale, W * scale * sub), np.float32)  # coverage, 3x wide
    y = 4
    line = ' '.join(WORDS) + ' '
    for style in range(3):
        italic = style == 1
        for size in (10, 11):
            px = size * scale
            is_bold = style == 0
            face = faces[is_bold]
            face.set_pixel_sizes(0, px)
            asc = round(win_ascent[is_bold] * px / face.units_per_EM)
            base = y * scale + asc
            pen = 4.0 * scale  # pixels, fractional
            for ch in line:
                x3 = pen * sub
                ix3 = math.floor(x3); frac = x3 - ix3
                m = freetype.Matrix(int(sub * 65536), int(sub * 0.25 * 65536) if italic else 0, 0, 65536)
                face.set_transform(m, freetype.Vector(int(round(frac * 64)), 0))
                face.load_char(ch, freetype.FT_LOAD_TARGET_LIGHT | freetype.FT_LOAD_NO_BITMAP | freetype.FT_LOAD_FORCE_AUTOHINT)
                face.glyph.render(freetype.FT_RENDER_MODE_NORMAL)
                g = face.glyph; bm = g.bitmap
                if bm.width and bm.rows:
                    a = np.array(bm.buffer, np.float32).reshape(bm.rows, bm.pitch)[:, :bm.width] / 255.0
                    top = base - g.bitmap_top; left = ix3 + g.bitmap_left
                    ys, xs = max(0, -top), max(0, -left)
                    ye, xe = min(bm.rows, canvas.shape[0] - top), min(bm.width, canvas.shape[1] - left)
                    if ye > ys and xe > xs:
                        dst = canvas[top + ys:top + ye, left + xs:left + xe]
                        np.maximum(dst, a[ys:ye, xs:xe], out=dst)  # touching glyphs: no double ink
                pen += face.glyph.linearHoriAdvance / 65536.0  # unhinted advance, scaled to px by FreeType
            face.set_transform(freetype.Matrix(65536, 0, 0, 65536), freetype.Vector(0, 0))
            y += 18
    if mode == 'rgb':
        a, b, c = weights
        k = np.array([c, b, a, b, c], np.float32); k /= k.sum()
        filt = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, canvas)
        cov = filt.reshape(canvas.shape[0], W * scale, sub)  # R, G, B subpixels
    else:
        cov = canvas.reshape(canvas.shape[0], W * scale, sub).mean(2, keepdims=True).repeat(3, 2)
    cov = np.clip(cov, 0, 1) ** (1.0 / gamma)
    lin = 1.0 - cov  # black text on white, blended in linear light
    srgb = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    Image.fromarray((np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('out'); p.add_argument('regular'); p.add_argument('bold')
    p.add_argument('--scale', type=int, default=1); p.add_argument('--mode', default='rgb')
    p.add_argument('--gamma', type=float, default=2.2); p.add_argument('--weights', default='0.3333,0.2222,0.1111')
    o = p.parse_args()
    render(o.out, o.regular, o.bold, o.scale, o.mode, o.gamma, tuple(float(x) for x in o.weights.split(',')))
