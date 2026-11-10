"""#69 stem lab: exact model of Wine's text=agg / agg-rgb glyph pipeline
(dllmgr-69.patch) on the system FreeType (same 2.13.2 as Wine links), plus
hooks for candidate stem fixes.

Coordinates: 1/64 px (FreeType 26.6) unless a name ends in _px."""
import ctypes, functools, math
import numpy as np
import freetype
import freetype.raw as ftraw

FONTS = '/home/claude/work/rt-cur3/share/wine/fonts/'
REG, BOLD = FONTS + 'tahoma.ttf', FONTS + 'tahomabd.ttf'

LOAD_LIGHT = (freetype.FT_LOAD_TARGET_LIGHT | freetype.FT_LOAD_NO_BITMAP |
              freetype.FT_LOAD_IGNORE_GLOBAL_ADVANCE_WIDTH | freetype.FT_LOAD_PEDANTIC)
LOAD_NORMAL = (freetype.FT_LOAD_TARGET_NORMAL | freetype.FT_LOAD_NO_BITMAP |
               freetype.FT_LOAD_IGNORE_GLOBAL_ADVANCE_WIDTH | freetype.FT_LOAD_PEDANTIC)
LOAD_UNHINTED = freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP

# Shemanarev's soft LCD filter, as dllmgr-69 sets it
_lib = ftraw._lib
_lib.FT_Library_SetLcdFilterWeights.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
_lib.FT_Library_SetLcdFilterWeights(freetype.get_handle(), bytes([28, 57, 85, 57, 28]))

# Wine dibdrv ramp (graphics.c) for 17-level grey glyphs
RAMP = np.array([0, 0x4d, 0x68, 0x7c, 0x8c, 0x9a, 0xa7, 0xb2, 0xbd, 0xc7, 0xd0, 0xd9,
                 0xe1, 0xe9, 0xf0, 0xf8, 0xff], np.float64)


def lut(gamma):
    return np.array([int(255.0 * (c / 255.0) ** (1.0 / gamma) + 0.5) for c in range(256)], np.int32)


class Font:
    def __init__(self, path, ppem):
        self.face = freetype.Face(path)
        self.face.set_pixel_sizes(0, ppem)
        self.ppem = ppem
        self.bold = path.endswith('bd.ttf')
        self.upem = self.face.units_per_EM

    def gid(self, ch):
        return self.face.get_char_index(ord(ch))

    @functools.lru_cache(maxsize=None)
    def metrics(self, ch):
        """(lin, app): unhinted advance in 1/64 px as Wine's DLLMGR69_LINEAR
        returns it, and the application's integer advance in px."""
        f = self.face
        f.load_glyph(self.gid(ch), LOAD_LIGHT)
        lin = f.glyph.linearHoriAdvance >> 10
        if self.bold:  # dllmgr66_advance: rounded design advance
            f.load_glyph(self.gid(ch), freetype.FT_LOAD_NO_SCALE)
            design = f.glyph.metrics.horiAdvance
            app = (design * self.ppem * 64 // self.upem + 32) >> 6
        else:
            f.load_glyph(self.gid(ch), LOAD_LIGHT)
            app = f.glyph.metrics.horiAdvance >> 6
        return lin, app

    def load_points(self, ch, flags=LOAD_LIGHT):
        f = self.face
        f.load_glyph(self.gid(ch), flags)
        ol = f.glyph._FT_GlyphSlot.contents.outline
        n = ol.n_points
        xs = np.array([ol.points[i].x for i in range(n)], np.int64)
        ys = np.array([ol.points[i].y for i in range(n)], np.int64)
        tags = np.array([ol.tags[i] for i in range(n)], np.int64)
        conts = [ol.contours[i] for i in range(ol.n_contours)]
        return xs, ys, tags, conts

    def render(self, ch, xfun=None, mode='gray', flags=LOAD_LIGHT, xscale=1):
        """Render ch with the outline's x coordinates mapped by xfun (array of
        26.6 -> array of 26.6; e.g. a shift). Returns (alpha, left_px, top_px):
        gray: float coverage 0..1 (H, W); rgb: 0..1 (H, W, 3)."""
        f = self.face
        f.load_glyph(self.gid(ch), flags)
        slot = f.glyph._FT_GlyphSlot
        ol = slot.contents.outline
        n = ol.n_points
        if n == 0:
            return None
        if xfun is not None or xscale != 1:
            xs = np.array([ol.points[i].x for i in range(n)], np.int64) * xscale
            if xfun is not None:
                xs = np.asarray(np.round(xfun(xs)), np.int64)
            for i in range(n):
                ol.points[i].x = int(xs[i])
        rm = freetype.FT_RENDER_MODE_LCD if mode == 'rgb' else freetype.FT_RENDER_MODE_NORMAL
        err = ftraw.FT_Render_Glyph(slot, rm)
        assert not err, err
        bm = f.glyph.bitmap
        if bm.rows == 0 or bm.width == 0:
            return None
        a = np.array(bm.buffer, np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width]
        if mode == 'rgb':
            a = a.reshape(bm.rows, bm.width // 3, 3)
        return a, f.glyph.bitmap_left, f.glyph.bitmap_top


# ---------------- Wine's placement (dibdrv/graphics.c agg_place) ----------
def agg_place(lin, lin_total, app_total):
    ideal = int(lin * app_total / lin_total) if lin * app_total >= 0 else -int(-lin * app_total / lin_total)
    thirds = int((ideal * 3 + (32 if ideal >= 0 else -32)) / 64)  # C division truncates
    whole = thirds // 3 if thirds >= 0 else -((2 - thirds) // 3)
    phase = thirds - whole * 3
    return whole, phase


def run_totals(font, text):
    lin_total = sum(font.metrics(c)[0] for c in text)
    app_total = 64 * sum(font.metrics(c)[1] for c in text)
    return lin_total, app_total


def ideal_positions(font, text):
    """exact (unquantised) target pen positions in px, scaled to the app width"""
    lin_total, app_total = run_totals(font, text)
    pos, lin = [], 0
    for c in text:
        pos.append(lin * app_total / lin_total / 64.0)
        lin += font.metrics(c)[0]
    return pos


def wine_positions(font, text):
    """positions (px) the current dllmgr-69 code uses: whole + (0, 21, 43)/64"""
    lin_total, app_total = run_totals(font, text)
    out, lin = [], 0
    for c in text:
        whole, phase = agg_place(lin, lin_total, app_total)
        out.append(whole + ((phase * 64 + 1) // 3) / 64.0)
        lin += font.metrics(c)[0]
    return out


# ---------------- composition and output (black text on white) -----------
def to_pixels(cov, mode, gamma=2.2, levels=True):
    """coverage canvas (0..1) -> sRGB 0..255 float (H, W, 3), as Wine draws it"""
    if mode == 'rgb':
        a = np.round(cov * 255)
        return 255.0 - a  # blend_color, no gamma ramp (FontSmoothingGamma unset)
    v = np.round(cov * 255).astype(np.int32)
    if gamma != 1.0:
        v = lut(gamma)[v]
    lev = (v * 17) // 256 if levels else v * 16 // 255
    out = RAMP[16 - lev]
    out = np.where(lev <= 1, 255.0, out)
    out = np.where(lev >= 16, 0.0, out)
    return np.repeat(out[:, :, None], 3, 2)


def srgb_to_lin(p):
    c = p / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def as_seen(img, t=1.6, x_off=0, y_off=0, k=2):
    """scripts/as-seen.py on the 2x (exact block) upscale of a 1x image; the
    1x image is placed at (x_off, y_off) on the 1x grid (sampling phase).
    k=1: the image is already the 2x frame (native 2x text, #52b)."""
    img = np.pad(img, ((y_off, 0), (x_off, 0), (0, 0)), constant_values=255)
    if k == 'halftone':  # Wine's STRETCH_HALFTONE at 2x (dibdrv halftone_888):
        # dst 2i = src i, dst 2i+1 = bilinear midpoint of src i, i+1
        def up(a, ax):
            nxt = np.concatenate([np.take(a, range(1, a.shape[ax]), ax), np.take(a, [-1], ax)], ax)
            mid = np.floor((a + nxt) / 2 + 0.5)
            return np.stack([a, mid], ax + 1).reshape(a.shape[:ax] + (2 * a.shape[ax],) + a.shape[ax + 1:])
        src = up(up(img, 0), 1)
    else:
        src = np.repeat(np.repeat(img, k, 0), k, 1)
    h, w = src.shape[:2]
    oh, ow = int(h / t), int(w / t)
    u = np.clip(t * (np.arange(ow) + 0.5) - 0.5, 0, w - 1)
    v = np.clip(t * (np.arange(oh) + 0.5) - 0.5, 0, h - 1)
    x0 = np.floor(u).astype(int); x1 = np.minimum(x0 + 1, w - 1); fx = (u - x0)[None, :, None]
    y0 = np.floor(v).astype(int); y1 = np.minimum(y0 + 1, h - 1); fy = (v - y0)[:, None, None]
    top = src[y0][:, x0] * (1 - fx) + src[y0][:, x1] * fx
    bot = src[y1][:, x0] * (1 - fx) + src[y1][:, x1] * fx
    return np.clip(np.floor(top * (1 - fy) + bot * fy + 0.5), 0, 255)
