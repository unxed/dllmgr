#define DLLMGR69_STEM_OS   16  /* horizontal oversampling of stem detection */
#define DLLMGR69_STEM_MAX  8   /* glyphs with more stems are left alone */
#define DLLMGR69_STEM_MOVE 48  /* a stem moves at most 0.75 px */

int dllmgr69_stem_alpha(void)
{
    static int alpha = -1;

    if (alpha < 0)
    {
        const char *env = getenv( "DLLMGR69_STEM" );
        int v = env ? atoi( env ) : 0;

        if (v <= 0 || dllmgr52_text_mode() < DLLMGR52_AGG) alpha = 0;
        else if (v == 1) alpha = dllmgr52_text_mode() == DLLMGR52_AGG_RGB ? 128 : 192;
        else alpha = min( v, 256 );
    }
    return alpha;
}

/* left and right edges (26.6, from the glyph origin) of the vertical stems:
 * columns of the outline rasterised 16x wide whose longest run of coverage
 * >= 128 is at least about half an x-height, grouped, at most 0.3 em wide */
static int dllmgr69_find_stems( FT_Outline *outline, int ppem, FT_Pos stems[DLLMGR69_STEM_MAX][2] )
{
    FT_Vector *points = outline->points, *wide;
    FT_Bitmap bitmap;
    FT_BBox cbox;
    BYTE *buf = NULL, *tall = NULL;
    int i, n = 0, w, h, x, y, start, run, best;
    int minrun = max( 3, (ppem * 245 + 500) / 1000 );

    if (outline->n_points <= 0 || ppem <= 0) return 0;
    if (!(wide = malloc( outline->n_points * sizeof(*wide) ))) return 0;
    for (i = 0; i < outline->n_points; i++)
    {
        wide[i].x = points[i].x * DLLMGR69_STEM_OS;
        wide[i].y = points[i].y;
    }
    outline->points = wide;
    pFT_Outline_Get_CBox( outline, &cbox );
    cbox.xMin &= ~63;
    cbox.yMin &= ~63;
    cbox.xMax = (cbox.xMax + 63) & ~63;
    cbox.yMax = (cbox.yMax + 63) & ~63;
    w = (cbox.xMax - cbox.xMin) >> 6;
    h = (cbox.yMax - cbox.yMin) >> 6;
    if (w <= 0 || h <= 0 || w * h > (1 << 20)) goto done;
    if (!(buf = calloc( w, h )) || !(tall = calloc( w, 1 ))) goto done;
    pFT_Outline_Translate( outline, -cbox.xMin, -cbox.yMin );
    memset( &bitmap, 0, sizeof(bitmap) );
    bitmap.rows = h;
    bitmap.width = w;
    bitmap.pitch = w;
    bitmap.pixel_mode = FT_PIXEL_MODE_GRAY;
    bitmap.num_grays = 256;
    bitmap.buffer = buf;
    pFT_Outline_Get_Bitmap( library, outline, &bitmap );

    for (x = 0; x < w; x++)
    {
        for (y = run = best = 0; y < h; y++)
        {
            run = buf[y * w + x] >= 128 ? run + 1 : 0;
            if (run > best) best = run;
        }
        tall[x] = best >= minrun;
    }
    for (x = 0; x < w;)
    {
        if (!tall[x]) { x++; continue; }
        for (start = x; x < w && tall[x]; x++) ;
        if ((x - start) * 10 > 3 * ppem * DLLMGR69_STEM_OS) continue;  /* not a stem */
        if (n == DLLMGR69_STEM_MAX) { n = 0; break; }
        stems[n][0] = ((cbox.xMin >> 6) + start) * (64 / DLLMGR69_STEM_OS);
        stems[n][1] = ((cbox.xMin >> 6) + x) * (64 / DLLMGR69_STEM_OS);
        n++;
    }
done:
    outline->points = points;
    free( wide );
    free( buf );
    free( tall );
    return n;
}

/* knots (old x, new x), 26.6, of the stem warp of a glyph shifted by shift;
 * 0 when a stem would move too far or stems would collide */
static int dllmgr69_stem_knots( FT_Outline *outline, int ppem, FT_Pos shift, int alpha,
                                FT_Pos knots[2 * DLLMGR69_STEM_MAX][2] )
{
    FT_Pos stems[DLLMGR69_STEM_MAX][2];
    int i, n = dllmgr69_find_stems( outline, ppem, stems );

    for (i = 0; i < n; i++)
    {
        FT_Pos l = stems[i][0] + shift, r = stems[i][1] + shift, width = r - l;
        FT_Pos snapped = max( 64, (width + 32) & ~63 );          /* width in whole px */
        FT_Pos left = ((l + r - snapped) / 2 + 32) & ~63;         /* its left edge on the grid */
        FT_Pos c2 = l + r + alpha * (2 * left + snapped - l - r) / 256;  /* 2 x new centre */

        if (labs( c2 - l - r ) > 2 * DLLMGR69_STEM_MOVE) return 0;
        knots[2 * i][0] = l;
        knots[2 * i][1] = (c2 - width) / 2;  /* the stem keeps its width: same ink */
        knots[2 * i + 1][0] = r;
        knots[2 * i + 1][1] = knots[2 * i][1] + width;
        if (i && (l <= knots[2 * i - 1][0] || knots[2 * i][1] < knots[2 * i - 1][1] + alpha * 63 / 256))
            return 0;
    }
    return 2 * n;
}

static void dllmgr69_stem_warp( FT_Outline *outline, FT_Pos knots[][2], int n )
{
    int i, j;

    for (i = 0; i < outline->n_points; i++)
    {
        FT_Pos x = outline->points[i].x;

        if (x <= knots[0][0]) x += knots[0][1] - knots[0][0];
        else if (x >= knots[n - 1][0]) x += knots[n - 1][1] - knots[n - 1][0];
        else
        {
            for (j = 0; x > knots[j + 1][0]; j++) ;
            x = knots[j][1] + (x - knots[j][0]) * (knots[j + 1][1] - knots[j][1]) / (knots[j + 1][0] - knots[j][0]);
        }
        outline->points[i].x = x;
    }
}

