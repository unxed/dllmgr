/* #52 probe: how GDI text looks in a non-DPI-aware window at 192 DPI.
 * Rows: the owner's problem words in the dialog font (MS Shell Dlg 8 pt),
 * Tahoma 8 pt, Arial 11 px and Courier New 8 pt, each with DEFAULT_QUALITY
 * (what Photoshop dialogs use), NONANTIALIASED, ANTIALIASED and CLEARTYPE.
 * Build: i686-w64-mingw32-gcc -O2 -o text-aa.exe text-aa.c -mwindows -lgdi32
 * Run under the stand with tests/wine/text-aa.sh. */
#include <windows.h>

static const char *faces[] = { "MS Shell Dlg", "Tahoma", "Arial", "Courier New" };
static const int heights[] = { -11, -11, -11, -11 };  /* 8 pt at 96 DPI */
static const struct { BYTE q; const char *name; } quality[] = {
    { DEFAULT_QUALITY, "default" }, { NONANTIALIASED_QUALITY, "nonaa" },
    { ANTIALIASED_QUALITY, "aa" }, { CLEARTYPE_QUALITY, "cleartype" },
};
static const char sample[] = "pt Sharp Regular FreeMono  Brush: Hardness 100%";

static LRESULT CALLBACK proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    if (msg == WM_PAINT) {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(hwnd, &ps);
        int f, q, y = 4;
        SetBkMode(dc, TRANSPARENT);
        for (f = 0; f < 4; f++)
            for (q = 0; q < 4; q++) {
                char label[64];
                HFONT font = CreateFontA(heights[f], 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET,
                                         0, 0, quality[q].q, 0, faces[f]);
                HGDIOBJ old = SelectObject(dc, font);
                wsprintfA(label, "%-12s %-9s", faces[f], quality[q].name);
                TextOutA(dc, 4, y, label, lstrlenA(label));
                TextOutA(dc, 150, y, sample, lstrlenA(sample));
                SelectObject(dc, old);
                DeleteObject(font);
                y += 16;
            }
        EndPaint(hwnd, &ps);
        return 0;
    }
    if (msg == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcA(hwnd, msg, wp, lp);
}

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSA wc = { 0, proc, 0, 0, inst, 0, LoadCursor(0, IDC_ARROW), (HBRUSH)(COLOR_BTNFACE + 1), 0, "textaa" };
    MSG msg;
    RegisterClassA(&wc);
    ShowWindow(CreateWindowA("textaa", "text-aa", WS_OVERLAPPEDWINDOW, 0, 0, 480, 300, 0, 0, inst, 0), SW_SHOW);
    while (GetMessageA(&msg, 0, 0, 0)) DispatchMessageA(&msg);
    return 0;
}
