/* #66: per-glyph monochrome metrics of Tahoma (regular, bold, italic) at
 * 9-16 px as GDI renders them: origin x (left bearing), black box width and
 * advance (GGO_BITMAP). left/width are the inked columns of the bitmap (an
 * outline font's black box may carry empty columns), boxleft/boxwidth the
 * black box as reported. Writes metrics66.csv; run on Windows and Wine. */
#include <windows.h>
#include <stdio.h>
int main(void)
{
    static const MAT2 identity = {{0, 1}, {0, 0}, {0, 0}, {0, 1}};
    HDC dc = CreateCompatibleDC(NULL);
    FILE *out = fopen("metrics66.csv", "w");
    int style, size, ch;
    static char buf[65536];
    if (!out) return 1;
    fprintf(out, "style,size,char,left,width,advance,boxleft,boxwidth\n");
    for (style = 0; style < 3; style++)
        for (size = 9; size <= 16; size++) {
            HFONT f = CreateFontA(-size, 0, 0, 0, style == 1 ? FW_BOLD : FW_NORMAL, style == 2, 0, 0, ANSI_CHARSET,
                                  0, 0, NONANTIALIASED_QUALITY, 0, "Tahoma");
            HFONT o = SelectObject(dc, f);
            for (ch = 0x21; ch < 0x7f; ch++) {
                GLYPHMETRICS gm;
                unsigned x, y, pitch, first = ~0u, last = 0;
                memset(buf, 0, sizeof(buf));
                if (GetGlyphOutlineA(dc, ch, GGO_BITMAP, &gm, sizeof(buf), buf, &identity) == GDI_ERROR) continue;
                pitch = ((gm.gmBlackBoxX + 31) / 32) * 4;
                for (y = 0; y < gm.gmBlackBoxY; y++)
                    for (x = 0; x < gm.gmBlackBoxX; x++)
                        if ((unsigned char)buf[y * pitch + x / 8] & (0x80 >> (x % 8))) {
                            if (x < first) first = x;
                            if (x > last) last = x;
                        }
                if (first == ~0u) first = 0, last = gm.gmBlackBoxX - 1;
                fprintf(out, "%s,%d,%d,%ld,%u,%d,%ld,%u\n", style == 1 ? "bold" : style == 2 ? "italic" : "regular", size, ch,
                        gm.gmptGlyphOrigin.x + (long)first, last - first + 1, gm.gmCellIncX,
                        gm.gmptGlyphOrigin.x, gm.gmBlackBoxX);
            }
            SelectObject(dc, o);
            DeleteObject(f);
        }
    fclose(out);
    return 0;
}
