#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_OUTLINE_H
typedef unsigned char BYTE;
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define pFT_Outline_Get_CBox FT_Outline_Get_CBox
#define pFT_Outline_Translate FT_Outline_Translate
#define pFT_Outline_Get_Bitmap FT_Outline_Get_Bitmap
enum { DLLMGR52_AGG = 5, DLLMGR52_AGG_RGB = 6 };
static int dllmgr52_text_mode(void) { return DLLMGR52_AGG_RGB; }
static FT_Library library;
#include "helpers.inc"
/* usage: harness font ppem alpha codepoint... ; prints per codepoint and phase the knots and warped xs */
int main(int argc, char **argv)
{
    FT_Face face; int ppem = atoi(argv[2]), alpha = atoi(argv[3]), a, ph, i, n;
    FT_Init_FreeType(&library);
    FT_New_Face(library, argv[1], 0, &face);
    FT_Set_Pixel_Sizes(face, 0, ppem);
    for (a = 4; a < argc; a++)
        for (ph = 0; ph < 3; ph++)
        {
            FT_Pos knots[2 * DLLMGR69_STEM_MAX][2], shift = (ph * 64 + 1) / 3;
            FT_Load_Glyph(face, FT_Get_Char_Index(face, strtoul(argv[a], 0, 0)),
                          FT_LOAD_TARGET_LIGHT | FT_LOAD_NO_BITMAP | FT_LOAD_IGNORE_GLOBAL_ADVANCE_WIDTH | FT_LOAD_PEDANTIC);
            n = dllmgr69_stem_knots(&face->glyph->outline, ppem, shift, alpha, knots);
            printf("%s %d K", argv[a], ph);
            for (i = 0; i < n; i++) printf(" %ld,%ld", knots[i][0], knots[i][1]);
            FT_Outline_Translate(&face->glyph->outline, shift, 0);
            if (n) dllmgr69_stem_warp(&face->glyph->outline, knots, n);
            printf(" X");
            for (i = 0; i < face->glyph->outline.n_points; i++) printf(" %ld", face->glyph->outline.points[i].x);
            printf("\n");
        }
    return 0;
}
