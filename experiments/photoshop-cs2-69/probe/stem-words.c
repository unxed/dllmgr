/* #69 stem probe: the words of the stem lab (scripts/measure.py WORDS) in
 * Tahoma -10/-11, regular/bold, DEFAULT_QUALITY (as Photoshop CS2), black on
 * white, TextOutW at (4, y) into a 24-bit 96-DPI DIB -> argv[1] (.bmp).
 * Line k: style (k / 64: 0 regular, 1 bold), size 10 + (k / 32) % 2, word k % 32;
 * line pitch 16 px. Build: i686-w64-mingw32-gcc -O2 -o stem-words.exe stem-words.c -lgdi32 */
#include <windows.h>
#include <stdio.h>
static const WCHAR *words[] = {
    L"Contrast:", L"Brightness:", L"Opacity:", L"Background", L"History", L"Layers",
    L"Channels", L"Preview", L"Fill:", L"Lock:", L"Normal", L"Brushes", L"Histogram",
    L"Navigator", L"Info", L"Paths", L"Actions", L"Swatches", L"Color", L"Styles",
    L"\x041a\x043e\x043d\x0442\x0440\x0430\x0441\x0442:", L"\x042f\x0440\x043a\x043e\x0441\x0442\x044c:",
    L"\x041d\x0435\x043f\x0440\x043e\x0437\x0440\x0430\x0447\x043d\x043e\x0441\x0442\x044c:",
    L"\x0421\x043b\x043e\x0438", L"\x0418\x0441\x0442\x043e\x0440\x0438\x044f", L"\x041a\x0430\x043d\x0430\x043b\x044b",
    L"\x0417\x0430\x043b\x0438\x0432\x043a\x0430:", L"\x041d\x0430\x0432\x0438\x0433\x0430\x0442\x043e\x0440",
    L"\x041a\x0438\x0441\x0442\x0438", L"\x0426\x0432\x0435\x0442", L"\x0421\x0442\x0438\x043b\x0438",
    L"\x041a\x043e\x043d\x0442\x0443\x0440\x044b"};
#define WD 200
#define HT (128 * 16 + 8)
int main(int argc, char **argv)
{
    BITMAPINFO bi = {{sizeof(BITMAPINFOHEADER), WD, HT, 1, 24, BI_RGB}};
    BITMAPFILEHEADER fh = {0x4d42};
    void *bits; RECT r = {0, 0, WD, HT}; FILE *out;
    HDC dc = CreateCompatibleDC(NULL);
    HBITMAP bmp = CreateDIBSection(dc, &bi, DIB_RGB_COLORS, &bits, NULL, 0);
    DWORD size = ((WD * 3 + 3) & ~3) * HT;
    int k;
    SelectObject(dc, bmp);
    FillRect(dc, &r, GetStockObject(WHITE_BRUSH)); SetBkMode(dc, TRANSPARENT);
    for (k = 0; k < 128; k++)
    {
        HFONT f = CreateFontA(-(10 + (k / 32) % 2), 0, 0, 0, k / 64 ? FW_BOLD : FW_NORMAL, 0, 0, 0,
                              DEFAULT_CHARSET, 0, 0, DEFAULT_QUALITY, 0, "Tahoma");
        HFONT o = SelectObject(dc, f);
        TextOutW(dc, 4, 4 + k * 16, words[k % 32], lstrlenW(words[k % 32]));
        SelectObject(dc, o); DeleteObject(f);
    }
    GdiFlush();
    fh.bfOffBits = sizeof(fh) + sizeof(BITMAPINFOHEADER); fh.bfSize = fh.bfOffBits + size;
    out = fopen(argc > 1 ? argv[1] : "stem-words.bmp", "wb");
    fwrite(&fh, sizeof(fh), 1, out); fwrite(&bi.bmiHeader, sizeof(BITMAPINFOHEADER), 1, out); fwrite(bits, size, 1, out); fclose(out);
    return 0;
}
