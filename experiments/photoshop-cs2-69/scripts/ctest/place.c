#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef long long LONGLONG; typedef unsigned char BYTE; typedef unsigned int UINT; typedef int BOOL; typedef unsigned short WCHAR; typedef short SHORT; typedef int INT;
#define TRUE 1
#define FALSE 0
#define min(a,b) ((a)<(b)?(a):(b))
typedef struct { int dummy; } DC;
struct cached_font { int n; };
struct cached_glyph { INT linear; SHORT stem_l, stem_r; };
static struct cached_glyph G[64][3];
static int dllmgr69_stem_alpha(void) { return 1; }
static struct cached_glyph *get_cached_glyph( struct cached_font *f, UINT i, UINT flags, UINT ph ) { return &G[i][ph]; }
static struct cached_glyph *cache_glyph_bitmap( DC *dc, struct cached_font *f, UINT i, UINT flags, UINT ph ) { return &G[i][ph]; }
static void agg_place( LONGLONG lin, LONGLONG lin_total, LONGLONG app_total, int *whole, int *phase )
{
    int ideal = (int)(lin * app_total / lin_total);
    int thirds = (ideal * 3 + (ideal >= 0 ? 32 : -32)) / 64;
    *whole = thirds >= 0 ? thirds / 3 : -((2 - thirds) / 3);
    *phase = thirds - *whole * 3;
}

/* dllmgr #69: position of every glyph of an agg run, in thirds of a pixel.
 * With the stem fix (DLLMGR69_STEM) a glyph may also take the third left or
 * right of its place (the first and the last glyph keep theirs): a Viterbi
 * pass picks the choices that keep the white between neighbours as the
 * design has it, counting where the stem warp moved the first and last stem
 * edge of each glyph (cost: 20 gap error^2 + mean displacement^2) */
static BOOL agg_place_run( DC *dc, struct cached_font *font, UINT flags, const WCHAR *str, UINT count,
                           LONGLONG lin_total, LONGLONG app_total, int *thirds )
{
    const LONGLONG inf = (LONGLONG)1 << 60;
    LONGLONG lin = 0, cost[3], next[3], left[3], right[3], prev_right[3];
    struct cached_glyph *glyph;
    BOOL stem = dllmgr69_stem_alpha() != 0;
    BYTE *back = NULL;
    UINT i;
    int d, j;

    if (stem && !(back = malloc( count * 3 ))) stem = FALSE;
    for (i = 0; i < count; i++)
    {
        int ideal, whole, phase;

        if (!(glyph = get_cached_glyph( font, str[i], flags, 0 ))) { free( back ); return FALSE; }
        ideal = (int)(lin * app_total / lin_total);
        agg_place( lin, lin_total, app_total, &whole, &phase );
        thirds[i] = whole * 3 + phase;
        lin += glyph->linear;
        if (!stem) continue;
        for (d = 0; d < 3; d++)
        {
            int q = thirds[i] + d - 1, w = q >= 0 ? q / 3 : -((2 - q) / 3), ph = q - w * 3;
            LONGLONG pos, mean, unary, best = 0;

            if (!(glyph = get_cached_glyph( font, str[i], flags, ph )) &&
                !(glyph = cache_glyph_bitmap( dc, font, str[i], flags, ph ))) { free( back ); return FALSE; }
            pos = w * 64 + (ph * 64 + 1) / 3 - ideal;
            left[d] = pos + glyph->stem_l;
            right[d] = pos + glyph->stem_r;
            mean = (left[d] + right[d]) / 2;
            unary = (i == 0 || i == count - 1) && d != 1 ? inf : mean * mean;
            if (!i) { next[d] = unary; continue; }
            for (j = 0; j < 3; j++)
            {
                LONGLONG v = cost[j] + 20 * (left[d] - prev_right[j]) * (left[d] - prev_right[j]);
                if (!j || v < best) { best = v; back[i * 3 + d] = j; }
            }
            next[d] = min( inf, best + unary );
        }
        memcpy( cost, next, sizeof(cost) );
        memcpy( prev_right, right, sizeof(prev_right) );
    }
    if (stem)
    {
        for (j = 0, d = 1; d < 3; d++) if (cost[d] < cost[j]) j = d;
        for (i = count; i-- > 0;)
        {
            thirds[i] += j - 1;
            if (i) j = back[i * 3 + j];
        }
    }
    free( back );
    return TRUE;
}


int main(void)
{
    int n, i, p; long long lt = 0, at = 0, app; WCHAR str[64]; int th[64];
    while (scanf("%d", &n) == 1)
    {
        lt = at = 0;
        for (i = 0; i < n; i++)
        {
            scanf("%d %lld", &G[i][0].linear, &app);
            for (p = 0; p < 3; p++) { int l, r; scanf("%d %d", &l, &r); G[i][p].stem_l = l; G[i][p].stem_r = r; }
            str[i] = i; lt += G[i][0].linear; at += 64 * app;
        }
        agg_place_run( NULL, NULL, 0, str, n, lt, at, th );
        for (i = 0; i < n; i++) printf("%d ", th[i]);
        printf("\n");
    }
    return 0;
}
