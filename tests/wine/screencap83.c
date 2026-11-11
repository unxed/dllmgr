/* screencap83.c: what does a screen-DC read return? (#83, Photoshop CS2
 * slider popup frame). The dllmgr-27 prefill captures the screen under a
 * new caption-less window with GetDC(NULL) + BitBlt in a per-monitor-aware
 * context; this probe does the same for one rectangle and writes the result
 * as a 24-bit BMP, to compare with what X shows (import -window root).
 * Usage: screencap83 X Y W H OUT.bmp   (physical pixels)
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o screencap83.exe screencap83.c -lgdi32 -luser32 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    int x, y, w, h, stride;
    HDC screen, mem;
    HBITMAP dib, old;
    void *bits;
    BITMAPINFO bi = {{sizeof(BITMAPINFOHEADER)}};
    BITMAPFILEHEADER fh = {0x4d42};
    FILE *f;
    if (argc < 6) { fprintf(stderr, "usage: screencap83 X Y W H OUT.bmp\n"); return 2; }
    x = atoi(argv[1]); y = atoi(argv[2]); w = atoi(argv[3]); h = atoi(argv[4]);
    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE);
    bi.bmiHeader.biWidth = w; bi.bmiHeader.biHeight = h;
    bi.bmiHeader.biPlanes = 1; bi.bmiHeader.biBitCount = 24;
    screen = GetDC(NULL);
    mem = CreateCompatibleDC(screen);
    dib = CreateDIBSection(screen, &bi, DIB_RGB_COLORS, &bits, NULL, 0);
    old = SelectObject(mem, dib);
    memset(bits, 0x5a, ((w * 3 + 3) & ~3) * h);
    BitBlt(mem, 0, 0, w, h, screen, x, y, SRCCOPY);
    GdiFlush();
    stride = (w * 3 + 3) & ~3;
    fh.bfOffBits = sizeof(fh) + sizeof(BITMAPINFOHEADER);
    fh.bfSize = fh.bfOffBits + stride * h;
    if (!(f = fopen(argv[5], "wb"))) return 1;
    fwrite(&fh, sizeof(fh), 1, f); fwrite(&bi.bmiHeader, sizeof(BITMAPINFOHEADER), 1, f);
    fwrite(bits, stride, h, f); fclose(f);
    printf("screencap83 %d,%d %dx%d logpixels=%d\n", x, y, w, h, GetDeviceCaps(screen, LOGPIXELSY));
    SelectObject(mem, old); DeleteObject(dib); DeleteDC(mem); ReleaseDC(NULL, screen);
    return 0;
}
