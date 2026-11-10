/* #66 kerning probe: Tahoma -11 "Open"/"Background": plain, bold font,
 * double-struck (x, x+1), and with lpDx from GetCharWidth32. */
#include <windows.h>
static void row(HDC dc, int y, HFONT f, const char *s, int mode)
{
    INT dx[32]; int n = lstrlenA(s), i;
    HFONT o = SelectObject(dc, f);
    for (i = 0; i < n; i++) { INT w; GetCharWidth32A(dc, (BYTE)s[i], (BYTE)s[i], &w); dx[i] = w + (mode == 3); }
    if (mode == 0 || mode == 1) TextOutA(dc, 10, y, s, n);
    if (mode == 1) TextOutA(dc, 11, y, s, n);
    if (mode >= 2) { ExtTextOutA(dc, 10, y, 0, NULL, s, n, dx); if (mode == 3) ExtTextOutA(dc, 11, y, 0, NULL, s, n, dx); }
    SelectObject(dc, o);
}
static LRESULT CALLBACK proc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(w, &ps); RECT r; int i;
        /* as Photoshop's History / Layers palettes (DLLMGR66_DUMP): Tahoma -10, ANTIALIASED_QUALITY */
        HFONT reg = CreateFontA(-10, 0, 0, 0, FW_BOLD, 0, 0, 0, ANSI_CHARSET, 0, 0, ANTIALIASED_QUALITY, 0, "Tahoma");
        HFONT bold = CreateFontA(-10, 0, 0, 0, FW_NORMAL, 1, 0, 0, ANSI_CHARSET, 0, 0, ANTIALIASED_QUALITY, 0, "Tahoma");
        GetClientRect(w, &r); FillRect(dc, &r, GetStockObject(WHITE_BRUSH)); SetBkMode(dc, TRANSPARENT);
        row(dc, 5, reg, "Open", 0); row(dc, 20, bold, "Background", 0); row(dc, 35, reg, "Background", 0);
        DeleteObject(reg); DeleteObject(bold); EndPaint(w, &ps); return 0;
    }
    if (m == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcA(w, m, wp, lp);
}
int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSA c = {0, proc, 0, 0, inst, 0, LoadCursor(0, IDC_ARROW), 0, 0, "kern"};
    RECT r = {0, 0, 190, 85}; MSG msg;
    RegisterClassA(&c); AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    CreateWindowA("kern", "kern", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, r.right - r.left, r.bottom - r.top, 0, 0, inst, 0);
    SetTimer(0, 0, 5000, 0);
    while (GetMessageA(&msg, 0, 0, 0)) { if (msg.message == WM_TIMER) break; DispatchMessageA(&msg); }
    return 0;
}
