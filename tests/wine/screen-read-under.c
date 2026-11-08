/* #36 mechanism probe: what does a screen-DC read return under a top-level
 * window that has been shown but not painted yet? Photoshop CS2 fakes splash
 * transparency by copying the screen under the splash; on Wine the copy is
 * white. Yellow underlay, then window A (no background brush, never paints
 * while sampled) is shown; BitBlt from GetDC(NULL) at the centre into a memory
 * DC and print that pixel. argv[1]=="prefill" shows A with the dllmgr-27
 * pre-presentation (copy of the screen drawn into A right after ShowWindow).
 * Output: read_under_unpainted rgb=RRGGBB (Windows keeps the underlay visible
 * there, so a faithful read is f0cc5a).
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o screen-read-under.exe screen-read-under.c -lgdi32 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static LRESULT CALLBACK procedure(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    if (message == WM_PAINT) {
        PAINTSTRUCT paint;
        HDC dc = BeginPaint(window, &paint);
        if (GetWindowLongPtrW(window, GWLP_USERDATA) == 1) {
            HBRUSH brush = CreateSolidBrush(RGB(240, 204, 90));
            FillRect(dc, &paint.rcPaint, brush);
            DeleteObject(brush);
        }
        EndPaint(window, &paint);
        return 0;
    }
    if (message == WM_ERASEBKGND) return 1;
    return DefWindowProcW(window, message, wparam, lparam);
}

static void pump_for(DWORD ms)
{
    DWORD start = GetTickCount();
    MSG msg;
    while (GetTickCount() - start < ms) {
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&msg); DispatchMessageW(&msg); }
        Sleep(10);
    }
}

static void show_prefilled(HWND window, int cmd)
{
    RECT r;
    HDC screen, mem, dc;
    HBITMAP bmp, old;
    int w, h;
    GetWindowRect(window, &r);
    w = r.right - r.left; h = r.bottom - r.top;
    screen = GetDC(NULL);
    mem = CreateCompatibleDC(screen);
    bmp = CreateCompatibleBitmap(screen, w, h);
    old = SelectObject(mem, bmp);
    BitBlt(mem, 0, 0, w, h, screen, r.left, r.top, SRCCOPY);
    ReleaseDC(NULL, screen);
    ShowWindow(window, cmd);
    if ((dc = GetDCEx(window, NULL, DCX_WINDOW | DCX_CACHE))) { BitBlt(dc, 0, 0, w, h, mem, 0, 0, SRCCOPY); ReleaseDC(window, dc); }
    GdiFlush();
    SelectObject(mem, old); DeleteObject(bmp); DeleteDC(mem);
}

int main(int argc, char **argv)
{
    WNDCLASSW cls = {0};
    int cx, cy;
    HWND under, a;
    HDC screen, mem;
    HBITMAP bmp, old;
    COLORREF c;

    SetProcessDPIAware();
    cx = GetSystemMetrics(SM_CXSCREEN); cy = GetSystemMetrics(SM_CYSCREEN);
    cls.lpfnWndProc = procedure; cls.hInstance = GetModuleHandleW(NULL); cls.lpszClassName = L"read-under";
    RegisterClassW(&cls);
    under = CreateWindowExW(0, cls.lpszClassName, L"underlay", WS_POPUP, 0, 0, cx, cy, NULL, NULL, cls.hInstance, NULL);
    SetWindowLongPtrW(under, GWLP_USERDATA, 1);
    ShowWindow(under, SW_SHOW); UpdateWindow(under); pump_for(800);

    a = CreateWindowExW(0, cls.lpszClassName, L"unpainted A", WS_POPUP, cx / 4, cy / 4, cx / 2, cy / 2, NULL, NULL,
                        cls.hInstance, NULL);
    if (argc > 1 && !strcmp(argv[1], "prefill")) show_prefilled(a, SW_SHOW);
    else ShowWindow(a, SW_SHOW);
    pump_for(300);

    screen = GetDC(NULL);
    mem = CreateCompatibleDC(screen);
    bmp = CreateCompatibleBitmap(screen, 1, 1);
    old = SelectObject(mem, bmp);
    BitBlt(mem, 0, 0, 1, 1, screen, cx / 2, cy / 2, SRCCOPY);
    c = GetPixel(mem, 0, 0);
    printf("read_under_unpainted rgb=%02x%02x%02x\n", GetRValue(c), GetGValue(c), GetBValue(c));
    SelectObject(mem, old); DeleteObject(bmp); DeleteDC(mem); ReleaseDC(NULL, screen);
    DestroyWindow(a); DestroyWindow(under);
    return 0;
}
