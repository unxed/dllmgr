/* Regression probe for #27 expose changes: a window whose content was already
 * painted must show that content again after another window covered it and
 * went away, WITHOUT a new WM_PAINT (Wine re-sends the surface pixels on
 * Expose). Paints a yellow window once (later WM_PAINTs draw red, so a repaint
 * is distinguishable), covers its centre with a blue popup, destroys the popup,
 * pumps messages, samples the screen centre.
 * Output: stage=... rgb=RRGGBB; exit 0 if the final centre is yellow (old
 * pixels restored) or red (app repainted; still correct), 1 otherwise.
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o window-occlusion.exe window-occlusion.c -lgdi32 */
#include <windows.h>
#include <stdio.h>

static int paints;

static LRESULT CALLBACK proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    if (message == WM_PAINT) {
        PAINTSTRUCT paint;
        HDC dc = BeginPaint(window, &paint);
        BOOL is_cover = GetWindowLongPtrW(window, GWLP_USERDATA) == 2;
        HBRUSH brush = CreateSolidBrush(is_cover ? RGB(0, 0, 255) : paints++ ? RGB(255, 0, 0) : RGB(240, 204, 90));
        FillRect(dc, &paint.rcPaint, brush);
        DeleteObject(brush);
        EndPaint(window, &paint);
        return 0;
    }
    if (message == WM_ERASEBKGND) return 1;
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

static COLORREF sample(const char *stage)
{
    HDC dc = GetDC(NULL);
    COLORREF color = GetPixel(dc, GetSystemMetrics(SM_CXSCREEN) / 2, GetSystemMetrics(SM_CYSCREEN) / 2);
    ReleaseDC(NULL, dc);
    printf("stage=%s rgb=%02x%02x%02x paints=%d\n", stage, GetRValue(color), GetGValue(color),
           GetBValue(color), paints);
    fflush(stdout);
    return color;
}

int main(void)
{
    WNDCLASSW cls = {0};
    int cx = GetSystemMetrics(SM_CXSCREEN), cy = GetSystemMetrics(SM_CYSCREEN);
    HWND main_window;
    COLORREF final;

    cls.lpfnWndProc = proc;
    cls.hInstance = GetModuleHandleW(NULL);
    cls.lpszClassName = L"occlusion-probe";
    RegisterClassW(&cls);

    main_window = CreateWindowExW(0, cls.lpszClassName, L"occluded", WS_POPUP, cx / 4, cy / 4, cx / 2, cy / 2,
                                  NULL, NULL, cls.hInstance, NULL);
    SetWindowLongPtrW(main_window, GWLP_USERDATA, 1);
    ShowWindow(main_window, SW_SHOW);
    UpdateWindow(main_window);
    pump_for(500);
    sample("painted");

    /* An external X client (scripts/: xlogo over the screen centre, then
     * killed) covers and uncovers the window meanwhile; this pumps messages
     * so the Expose is processed like in a real app. */
    pump_for(4000);
    final = sample("uncovered");

    DestroyWindow(main_window);
    return final == RGB(240, 204, 90) || final == RGB(255, 0, 0) ? 0 : 1;
}
