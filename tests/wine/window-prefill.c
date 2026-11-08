/* #27 workaround feasibility on STOCK Wine, public APIs only: before showing a
 * new top-level window, copy the screen under it; right after ShowWindow draw
 * that copy into the window and GdiFlush, so the first thing presented is the
 * old screen contents (what Windows shows until the app paints), not Wine's
 * white initial surface or the black X background. The app still gets its
 * WM_PAINT (window DC drawing does not validate the update region).
 *
 * Same scenario as window-first-paint.c: yellow underlay, then a popup that
 * does not paint for ~0.7 s while messages are pumped, then paints yellow.
 * argv[1] == "prefill" enables the workaround. Judge with tests/wine/xsample
 * (X pixels): any non-yellow phase after the first yellow is a failure.
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o window-prefill.exe window-prefill.c -lgdi32 */
#include <windows.h>
#include <string.h>

static BOOL paint_popup;

static LRESULT CALLBACK procedure(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    if (message == WM_NCCREATE)
        SetWindowLongPtrW(window, GWLP_USERDATA, (LONG_PTR)((CREATESTRUCTW *)lparam)->lpCreateParams);
    if (message == WM_PAINT) {
        PAINTSTRUCT paint;
        HDC dc = BeginPaint(window, &paint);
        if (!GetWindowLongPtrW(window, GWLP_USERDATA) || paint_popup) {
            HBRUSH brush = CreateSolidBrush(RGB(240, 204, 90));
            FillRect(dc, &paint.rcPaint, brush);
            DeleteObject(brush);
        }
        EndPaint(window, &paint);
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

static void pump_for(DWORD milliseconds)
{
    DWORD start = GetTickCount();
    MSG message;
    while (GetTickCount() - start < milliseconds) {
        while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
        Sleep(10);
    }
}

/* The workaround: ShowWindow with the old screen contents pre-presented. */
static BOOL show_prefilled(HWND window, int cmd)
{
    RECT rect;
    HDC screen, mem, dc;
    HBITMAP bitmap, old;
    int w, h;
    BOOL ret;

    GetWindowRect(window, &rect);
    w = rect.right - rect.left;
    h = rect.bottom - rect.top;
    screen = GetDC(NULL);
    mem = CreateCompatibleDC(screen);
    bitmap = CreateCompatibleBitmap(screen, w, h);
    old = SelectObject(mem, bitmap);
    BitBlt(mem, 0, 0, w, h, screen, rect.left, rect.top, SRCCOPY);
    ReleaseDC(NULL, screen);

    ret = ShowWindow(window, cmd);

    if ((dc = GetDCEx(window, NULL, DCX_WINDOW | DCX_CACHE))) {
        BitBlt(dc, 0, 0, w, h, mem, 0, 0, SRCCOPY);
        ReleaseDC(window, dc);
    }
    GdiFlush();
    SelectObject(mem, old);
    DeleteObject(bitmap);
    DeleteDC(mem);
    return ret;
}

int main(int argc, char **argv)
{
    WNDCLASSW cls = {0};
    HWND bottom, popup;
    int width, height;
    DWORD style = WS_POPUP | WS_CLIPSIBLINGS | WS_CLIPCHILDREN;
    BOOL prefill = argc > 1 && !strcmp(argv[1], "prefill");

    SetProcessDPIAware();
    width = GetSystemMetrics(SM_CXSCREEN);
    height = GetSystemMetrics(SM_CYSCREEN);
    cls.lpfnWndProc = procedure;
    cls.hInstance = GetModuleHandleW(NULL);
    cls.lpszClassName = L"dllmgr-prefill"; /* no class background brush */
    if (!RegisterClassW(&cls)) return 2;
    bottom = CreateWindowExW(0, cls.lpszClassName, L"synthetic underlay", style, 0, 0, width, height,
                             NULL, NULL, cls.hInstance, NULL);
    if (!bottom) return 3;
    ShowWindow(bottom, SW_SHOW);
    UpdateWindow(bottom);
    pump_for(1500);

    popup = CreateWindowExW(WS_EX_CONTROLPARENT, cls.lpszClassName, L"delayed-paint popup", style, 0, 0,
                            width, height, bottom, NULL, cls.hInstance, (void *)1);
    if (!popup) return 4;
    if (prefill) show_prefilled(popup, SW_SHOW);
    else ShowWindow(popup, SW_SHOW);
    pump_for(700);
    SetWindowPos(popup, HWND_TOP, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE);
    pump_for(300);
    paint_popup = TRUE;
    InvalidateRect(popup, NULL, FALSE);
    UpdateWindow(popup);
    pump_for(1000);
    DestroyWindow(popup);
    DestroyWindow(bottom);
    return 0;
}
