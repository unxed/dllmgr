/* GDI scaling stage 3 probe: window bits kept across a resize that
 * recreates the window surface must be the current pixels. The first paint
 * is red, every later paint green; after growing the window the old area
 * must stay red (copied), the new area green. Stale bits show as another
 * colour. Then a scroll by (30, 20): the red area must move with it. */
#include <windows.h>
static int painted;
static LRESULT CALLBACK proc(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(w, &ps);
        HBRUSH b = CreateSolidBrush(painted++ ? RGB(0, 160, 0) : RGB(200, 0, 0));
        FillRect(dc, &ps.rcPaint, b); DeleteObject(b);
        MoveToEx(dc, 0, 0, NULL); LineTo(dc, 150, 100);   /* a mark inside the kept area */
        EndPaint(w, &ps); return 0;
    }
    if (m == WM_ERASEBKGND) return 1;
    if (m == WM_TIMER && wp == 1) { SetWindowPos(w, 0, 0, 0, 500, 400, SWP_NOMOVE | SWP_NOZORDER); KillTimer(w, 1); SetTimer(w, 2, 1500, 0); return 0; }
    if (m == WM_TIMER && wp == 2) { ScrollWindowEx(w, 30, 20, NULL, NULL, NULL, NULL, SW_INVALIDATE); KillTimer(w, 2); return 0; }
    if (m == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcA(w, m, wp, lp);
}
int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSA c = {0, proc, 0, 0, inst, 0, LoadCursor(0, IDC_ARROW), 0, 0, "resize"};
    MSG msg; HWND w;
    RegisterClassA(&c);
    w = CreateWindowA("resize", "resize", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 200, 150, 0, 0, inst, 0);
    SetTimer(w, 1, 2500, 0);
    SetTimer(0, 0, 7000, 0);
    while (GetMessageA(&msg, 0, 0, 0)) { if (msg.message == WM_TIMER && !msg.hwnd) break; DispatchMessageA(&msg); }
    return 0;
}
