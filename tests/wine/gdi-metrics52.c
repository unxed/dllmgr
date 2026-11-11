/* #52b probe: under GDI scaling (DLLMGR52_GDI_SCALE=1) the font metrics an
 * application gets on a scaled window DC must equal those of a plain 96-DPI
 * DC. For each test font, GetTextMetrics, GetOutlineTextMetrics,
 * GetKerningPairs, GetCharWidth32, GetCharABCWidths and GetTextExtentPoint32
 * on a memory DC (plain) and on the window DC of a DPI-unaware window
 * (scaled when GDI scaling is on) are compared field by field.
 * Output: one line per mismatch, then "match: N/M" (M = values compared).
 * Without GDI scaling both DCs are plain, so N = M is the baseline. */
#include <windows.h>
#include <stdio.h>
#include <stddef.h>

static int total, same;

static void cmp(const char *font, const char *what, long a, long b)
{
    total++;
    if (a == b) same++;
    else printf("%s: %s plain %ld scaled %ld\n", font, what, a, b);
}

#define TM(f) cmp(name, "tm." #f, (long)pa->f, (long)pb->f)
static void cmp_tm(const char *name, const TEXTMETRICW *pa, const TEXTMETRICW *pb)
{
    TM(tmHeight); TM(tmAscent); TM(tmDescent); TM(tmInternalLeading); TM(tmExternalLeading);
    TM(tmAveCharWidth); TM(tmMaxCharWidth); TM(tmWeight); TM(tmOverhang);
    TM(tmFirstChar); TM(tmLastChar); TM(tmItalic); TM(tmPitchAndFamily); TM(tmCharSet);
}
#undef TM

#define OTM(f) cmp(name, "otm." #f, (long)pa->f, (long)pb->f)
static void cmp_otm(const char *name, const OUTLINETEXTMETRICW *pa, const OUTLINETEXTMETRICW *pb)
{
    OTM(otmSize); OTM(otmfsSelection); OTM(otmfsType); OTM(otmsCharSlopeRise); OTM(otmsCharSlopeRun);
    OTM(otmItalicAngle); OTM(otmEMSquare); OTM(otmAscent); OTM(otmDescent); OTM(otmLineGap);
    OTM(otmsCapEmHeight); OTM(otmsXHeight); OTM(otmrcFontBox.left); OTM(otmrcFontBox.top);
    OTM(otmrcFontBox.right); OTM(otmrcFontBox.bottom); OTM(otmMacAscent); OTM(otmMacDescent);
    OTM(otmMacLineGap); OTM(otmusMinimumPPEM); OTM(otmptSubscriptSize.x); OTM(otmptSubscriptSize.y);
    OTM(otmptSubscriptOffset.x); OTM(otmptSubscriptOffset.y); OTM(otmptSuperscriptSize.x);
    OTM(otmptSuperscriptSize.y); OTM(otmptSuperscriptOffset.x); OTM(otmptSuperscriptOffset.y);
    OTM(otmsStrikeoutSize); OTM(otmsStrikeoutPosition); OTM(otmsUnderscoreSize);
    OTM(otmsUnderscorePosition);
    cmp_tm(name, &pa->otmTextMetrics, &pb->otmTextMetrics);
}
#undef OTM

static void probe(HDC plain, HDC scaled, const char *face, int height, int weight, BOOL italic)
{
    char name[96];
    HFONT f = CreateFontA(height, 0, 0, 0, weight, italic, 0, 0, DEFAULT_CHARSET, 0, 0,
                          DEFAULT_QUALITY, 0, face);
    HGDIOBJ oa = SelectObject(plain, f), ob = SelectObject(scaled, f);
    TEXTMETRICW ta, tb;
    char oa_buf[1024], ob_buf[1024];
    OUTLINETEXTMETRICW *ota = (void *)oa_buf, *otb = (void *)ob_buf;
    UINT sa, sb;
    DWORD ka, kb, i;
    KERNINGPAIR *pa, *pb;
    static const WCHAR text[] = L"100% Opacity: Background AVAWTo \x041e\x0442\x043a\x0440\x044b\x0442\x044c";
    SIZE za, zb;
    int c;

    snprintf(name, sizeof(name), "%s %d w%d%s", face, height, weight, italic ? " i" : "");

    GetTextMetricsW(plain, &ta); GetTextMetricsW(scaled, &tb);
    cmp_tm(name, &ta, &tb);

    sa = GetOutlineTextMetricsW(plain, sizeof(oa_buf), ota);
    sb = GetOutlineTextMetricsW(scaled, sizeof(ob_buf), otb);
    cmp(name, "otm size", sa, sb);
    if (sa && sb) cmp_otm(name, ota, otb);

    ka = GetKerningPairsW(plain, 0, NULL); kb = GetKerningPairsW(scaled, 0, NULL);
    cmp(name, "kern count", ka, kb);
    if (ka && ka == kb)
    {
        pa = malloc(ka * sizeof(*pa)); pb = malloc(kb * sizeof(*pb));
        GetKerningPairsW(plain, ka, pa); GetKerningPairsW(scaled, kb, pb);
        for (i = 0; i < ka; i++)
        {
            char what[64];
            snprintf(what, sizeof(what), "kern %04x-%04x", pa[i].wFirst, pa[i].wSecond);
            cmp(name, what, pa[i].iKernAmount, pb[i].wFirst == pa[i].wFirst &&
                pb[i].wSecond == pa[i].wSecond ? pb[i].iKernAmount : 0x7fffffff);
        }
        free(pa); free(pb);
    }

    for (c = 0x20; c < 0x7f; c++)
    {
        INT wa, wb; ABC aa, ab; char what[32];
        GetCharWidth32W(plain, c, c, &wa); GetCharWidth32W(scaled, c, c, &wb);
        snprintf(what, sizeof(what), "width '%c'", c); cmp(name, what, wa, wb);
        if (GetCharABCWidthsW(plain, c, c, &aa) && GetCharABCWidthsW(scaled, c, c, &ab))
        {
            snprintf(what, sizeof(what), "abcA '%c'", c); cmp(name, what, aa.abcA, ab.abcA);
            snprintf(what, sizeof(what), "abcB '%c'", c); cmp(name, what, aa.abcB, ab.abcB);
            snprintf(what, sizeof(what), "abcC '%c'", c); cmp(name, what, aa.abcC, ab.abcC);
        }
    }
    GetTextExtentPoint32W(plain, text, lstrlenW(text), &za);
    GetTextExtentPoint32W(scaled, text, lstrlenW(text), &zb);
    cmp(name, "extent cx", za.cx, zb.cx); cmp(name, "extent cy", za.cy, zb.cy);

    SelectObject(plain, oa); SelectObject(scaled, ob); DeleteObject(f);
}

int main(void)
{
    static const struct { const char *face; int height, weight; BOOL italic; } fonts[] = {
        { "Tahoma", -10, FW_NORMAL, 0 }, { "Tahoma", -10, FW_BOLD, 0 }, { "Tahoma", -10, FW_NORMAL, 1 },
        { "Tahoma", -11, FW_NORMAL, 0 }, { "Tahoma", -13, FW_BOLD, 0 }, { "Arial", -11, FW_NORMAL, 0 },
        { "Arial", -16, FW_BOLD, 1 }, { "Times New Roman", -13, FW_NORMAL, 0 },
        { "Courier New", -12, FW_NORMAL, 0 }, { "MS Shell Dlg", 8, FW_NORMAL, 0 },
    };
    HWND w = CreateWindowA("STATIC", "metrics52", WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                           0, 0, 300, 200, 0, 0, 0, 0);
    HDC scaled = GetDC(w), plain = CreateCompatibleDC(NULL);
    BITMAPINFO bi = {{sizeof(bi.bmiHeader), 16, 16, 1, 32, BI_RGB}};
    void *bits;
    MSG msg;
    unsigned i;

    /* a 32-bpp target like the window's: a monochrome one would get bitmap strikes */
    SelectObject(plain, CreateDIBSection(plain, &bi, DIB_RGB_COLORS, &bits, NULL, 0));

    while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
    for (i = 0; i < sizeof(fonts) / sizeof(fonts[0]); i++)
        probe(plain, scaled, fonts[i].face, fonts[i].height, fonts[i].weight, fonts[i].italic);
    printf("match: %d/%d\n", same, total);
    DeleteDC(plain); ReleaseDC(w, scaled); DestroyWindow(w);
    return same == total ? 0 : 1;
}
