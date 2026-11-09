/* GDI scaling invariant probe: every non-text primitive drawn on a GDI-scaled
 * window must equal the exact k x k block upscale of the 96-DPI drawing.
 * Rows: pens of width 0..3 (solid, inside-frame), rectangles, frames,
 * edges, XOR lines drawn twice (must vanish), a line over a filled block. */
#include <windows.h>
static void paint(HDC dc)
{
    RECT r = {0, 0, 320, 200};
    int i, y;
    FillRect(dc, &r, GetStockObject(WHITE_BRUSH));
    for (i = 0; i < 4; i++) {
        HPEN p = CreatePen(PS_SOLID, i, RGB(200, 0, 0)), o = SelectObject(dc, p);
        y = 10 + i * 8;
        MoveToEx(dc, 10, y, NULL); LineTo(dc, 90, y);          /* horizontal */
        MoveToEx(dc, 100 + i * 8, 10, NULL); LineTo(dc, 100 + i * 8, 40); /* vertical */
        SelectObject(dc, o); DeleteObject(p);
        p = CreatePen(PS_INSIDEFRAME, i, RGB(0, 0, 200)); o = SelectObject(dc, p);
        SelectObject(dc, GetStockObject(NULL_BRUSH));
        Rectangle(dc, 140 + i * 40, 10, 170 + i * 40, 40);
        SelectObject(dc, o); DeleteObject(p);
    }
    /* a 1-px line over a filled block: must cover the block's whole row */
    r.left = 10; r.top = 50; r.right = 90; r.bottom = 70;
    FillRect(dc, &r, GetStockObject(GRAY_BRUSH));
    MoveToEx(dc, 10, 69, NULL); LineTo(dc, 90, 69);
    r.left = 100; r.top = 50; r.right = 160; r.bottom = 70;
    FrameRect(dc, &r, GetStockObject(BLACK_BRUSH));
    r.left = 170; r.right = 230; DrawEdge(dc, &r, EDGE_SUNKEN, BF_RECT);
    r.left = 240; r.right = 300; DrawEdge(dc, &r, EDGE_RAISED, BF_RECT | BF_MIDDLE);
    /* XOR drawn twice must vanish (Photoshop's outlines, #46) */
    SetROP2(dc, R2_NOT);
    for (i = 0; i < 2; i++) {
        MoveToEx(dc, 10, 80, NULL); LineTo(dc, 90, 80); LineTo(dc, 90, 110); LineTo(dc, 10, 80);
        Rectangle(dc, 100, 80, 160, 110);
    }
    SetROP2(dc, R2_COPYPEN);
    r.left = 170; r.top = 80; r.right = 230; r.bottom = 110;
    InvertRect(dc, &r);
    PatBlt(dc, 240, 80, 60, 30, DSTINVERT);
    Ellipse(dc, 10, 120, 90, 160);
    RoundRect(dc, 100, 120, 160, 160, 10, 10);
}
static LRESULT CALLBACK proc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) { PAINTSTRUCT ps; paint(BeginPaint(w, &ps)); EndPaint(w, &ps); return 0; }
    if (m == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcA(w, m, wp, lp);
}
int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSA c = {0, proc, 0, 0, inst, 0, LoadCursor(0, IDC_ARROW), 0, 0, "prims"};
    RECT r = {0, 0, 320, 200};
    MSG msg;
    RegisterClassA(&c);
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    CreateWindowA("prims", "prims", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, r.right - r.left, r.bottom - r.top, 0, 0, inst, 0);
    SetTimer(0, 0, 6000, 0);
    while (GetMessageA(&msg, 0, 0, 0)) { if (msg.message == WM_TIMER) break; DispatchMessageA(&msg); }
    return 0;
}
