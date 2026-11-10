/* #66 palette text probe: the fonts Photoshop CS2's History / Layers palettes
 * use (DLLMGR66_DUMP): Tahoma -10 bold "Open", Tahoma -10 italic
 * "Background", plus a few more words and sizes, ANTIALIASED_QUALITY.
 *   text-kern66.exe        window (stand screenshots)
 *   text-kern66.exe bmp    renders into a 96-DPI DIB and writes kern66.bmp
 *                          (same pixels on Windows and Wine, no screen grab)
 *   text-kern66.exe bmp N  the same with font quality N (0 DEFAULT_QUALITY,
 *                          what Photoshop's palettes use: ClearType when the
 *                          system smooths fonts), writes kern66-qN.bmp */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define W 260
#define H 120
static int quality = ANTIALIASED_QUALITY;
static void paint(HDC dc)
{
    static const char *words[] = {"Open", "Background", "History", "Layers", "lena.jpeg"};
    RECT r = {0, 0, W, H};
    int i, y = 4;
    FillRect(dc, &r, GetStockObject(WHITE_BRUSH));
    SetBkMode(dc, TRANSPARENT);
    for (i = 0; i < 3; i++) {
        int weight = i == 1 ? FW_NORMAL : FW_BOLD, italic = i == 1, size;
        for (size = 10; size <= 11; size++, y += 18) {
            HFONT f = CreateFontA(-size, 0, 0, 0, weight, italic, 0, 0, ANSI_CHARSET, 0, 0, quality, 0, "Tahoma");
            HFONT o = SelectObject(dc, f);
            char line[128];
            int j, n = 0;
            for (j = 0; j < 5; j++) n += sprintf(line + n, "%s ", words[j]);
            if (i == 2) SelectObject(dc, o), DeleteObject(f),
                f = CreateFontA(-size, 0, 0, 0, FW_NORMAL, 0, 0, 0, ANSI_CHARSET, 0, 0, quality, 0, "Tahoma"),
                o = SelectObject(dc, f);
            TextOutA(dc, 4, y, line, n);
            SelectObject(dc, o);
            DeleteObject(f);
        }
    }
}
static LRESULT CALLBACK proc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) { PAINTSTRUCT ps; paint(BeginPaint(w, &ps)); EndPaint(w, &ps); return 0; }
    if (m == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcA(w, m, wp, lp);
}
static int write_bmp(void)
{
    BITMAPINFO bi = {{sizeof(BITMAPINFOHEADER), W, H, 1, 24, BI_RGB}};
    BITMAPFILEHEADER fh = {0x4d42};
    void *bits;
    HDC dc = CreateCompatibleDC(NULL);
    HBITMAP bmp = CreateDIBSection(dc, &bi, DIB_RGB_COLORS, &bits, NULL, 0);
    DWORD size = ((W * 3 + 3) & ~3) * H;
    FILE *out;
    SelectObject(dc, bmp);
    paint(dc);
    GdiFlush();
    fh.bfOffBits = sizeof(fh) + sizeof(BITMAPINFOHEADER);
    fh.bfSize = fh.bfOffBits + size;
    char name[32];
    sprintf(name, quality == ANTIALIASED_QUALITY ? "kern66.bmp" : "kern66-q%d.bmp", quality);
    if (!(out = fopen(name, "wb"))) return 1;
    fwrite(&fh, sizeof(fh), 1, out);
    fwrite(&bi.bmiHeader, sizeof(BITMAPINFOHEADER), 1, out);
    fwrite(bits, size, 1, out);
    fclose(out);
    return 0;
}
int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSA c = {0, proc, 0, 0, inst, 0, LoadCursor(0, IDC_ARROW), 0, 0, "kern"};
    RECT r = {0, 0, W, H}; MSG msg;
    if (strstr(cmd, "bmp")) {
        if (strlen(cmd) > 4) quality = atoi(cmd + 4);
        return write_bmp();
    }
    RegisterClassA(&c); AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    CreateWindowA("kern", "kern", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, r.right - r.left, r.bottom - r.top, 0, 0, inst, 0);
    SetTimer(0, 0, 5000, 0);
    while (GetMessageA(&msg, 0, 0, 0)) { if (msg.message == WM_TIMER) break; DispatchMessageA(&msg); }
    return 0;
}
