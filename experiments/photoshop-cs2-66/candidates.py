#!/usr/bin/env python3
"""#66 font research: how close each installed font's monochrome advances are
to Windows' Tahoma (regular / bold) at 9-13 px, measured with FreeType
(hinted mono, as GDI without smoothing). Lower is better."""
import csv, sys, glob, freetype
W = {(r['style'], int(r['size']), int(r['char'])): int(r['advance']) for r in csv.DictReader(open(sys.argv[1]))}
files = sorted(set(glob.glob('/usr/share/fonts/**/*.[ot]tf', recursive=True) +
                   glob.glob('/home/claude/work/rt-cur3/share/wine/fonts/*.ttf') + glob.glob('/home/claude/work/xo/ex/XO_Tahion/XO_Tahion/TTF/*.ttf') + glob.glob('/home/claude/work/xo/gf/*.ttf')))
rows = []
for path in files:
    try:
        f = freetype.Face(path)
    except Exception:
        continue
    if not f.is_scalable: continue
    bold = bool(f.style_flags & freetype.FT_STYLE_FLAG_BOLD); italic = bool(f.style_flags & freetype.FT_STYLE_FLAG_ITALIC)
    if italic: continue
    style = 'bold' if bold else 'regular'
    mism = tot = 0; wsum = nsum = 0
    try:
        for size in (9, 10, 11, 12, 13):
            f.set_pixel_sizes(0, size)
            for ch in range(0x21, 0x7f):
                if f.get_char_index(ch) == 0: raise ValueError('missing')
                f.load_char(chr(ch), freetype.FT_LOAD_TARGET_MONO)
                adv = (f.glyph.advance.x + 32) >> 6
                w = W[(style, size, ch)]
                tot += 1; mism += adv != w; wsum += w; nsum += adv
    except Exception:
        continue
    rows.append((mism / tot, abs(nsum - wsum) / wsum, style, f.family_name.decode(errors='replace'), path))
for style in ('regular', 'bold'):
    print('==', style, '(advance mismatch share, total width error, family, file)')
    for r in sorted(x for x in rows if x[2] == style)[:12]:
        print(f"  {r[0]:.2f} {r[1]:.3f}  {r[3]:28s} {r[4]}")
