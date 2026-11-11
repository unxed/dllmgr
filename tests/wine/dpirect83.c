/* dpirect83.c: window coordinates a per-monitor-aware thread gets for a
 * DPI-unaware window (#83). The dllmgr-27 prefill switches its thread to
 * DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE and expects physical pixels from
 * GetWindowRect for Photoshop's (unaware) windows. Windows documents that a
 * per-monitor-aware thread sees physical coordinates. The probe (an unaware
 * process, no manifest) shows a 122x24 popup at logical 268,76 and prints
 * GetWindowRect, GetDpiForWindow and the screen DC's LOGPIXELSY in the
 * default, per-monitor (v1) and per-monitor v2 contexts.
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o dpirect83.exe dpirect83.c -lgdi32 -luser32 */
#include <windows.h>
#include <stdio.h>

static void show(const char *name, HWND hwnd)
{
    RECT r = {0};
    HDC screen = GetDC(NULL);
    GetWindowRect(hwnd, &r);
    printf("%-8s rect=%ld,%ld-%ld,%ld (%ldx%ld) dpi_for_window=%u screen_logpixels=%d\n", name, r.left, r.top,
           r.right, r.bottom, r.right - r.left, r.bottom - r.top, GetDpiForWindow(hwnd),
           GetDeviceCaps(screen, LOGPIXELSY));
    ReleaseDC(NULL, screen);
}

int main(void)
{
    WNDCLASSA wc = {0};
    HWND hwnd;
    DPI_AWARENESS_CONTEXT old;
    wc.lpfnWndProc = DefWindowProcA; wc.hInstance = GetModuleHandleA(NULL);
    wc.hbrBackground = GetStockObject(WHITE_BRUSH); wc.lpszClassName = "dpirect83";
    RegisterClassA(&wc);
    hwnd = CreateWindowExA(WS_EX_TOOLWINDOW, "dpirect83", "", WS_POPUP, 268, 76, 122, 24, NULL, NULL, wc.hInstance, NULL);
    ShowWindow(hwnd, SW_SHOWNOACTIVATE);
    UpdateWindow(hwnd);
    printf("process awareness context %p\n", GetThreadDpiAwarenessContext());
    show("default", hwnd);
    old = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE);
    printf("set PMA v1 -> old %p\n", old);
    show("pma-v1", hwnd);
    old = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    printf("set PMA v2 -> old %p\n", old);
    show("pma-v2", hwnd);
    DestroyWindow(hwnd);
    return 0;
}
