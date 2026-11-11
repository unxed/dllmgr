/* #76 synthetic trigger: a window of class argv[1] (default PSDocC) with no
 * child, shown without activation under the cursor for argv[2] seconds
 * (default 20). Window class atoms are shared, so Photoshop CS2's cursor hit
 * test takes it for one of its own document windows, asks GetDlgItem(w, 0)
 * for the view, gets NULL and (unfixed) dereferences the cursor point.
 * With "owned" as argv[3], it instead shows a plain popup owned by a
 * childless window of that class (the "parent" path of the hit test).
 * Build: i686-w64-mingw32-gcc -O2 -o fake76.exe fake76.c -lgdi32 -luser32 */
#include <windows.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    WNDCLASSA wc = {0};
    POINT p;
    HWND w, owner = 0;
    MSG m;
    DWORD end = GetTickCount() + (argc > 2 ? atoi(argv[2]) : 20) * 1000;
    const char *cls = argc > 1 ? argv[1] : "PSDocC";

    SetProcessDPIAware();
    GetCursorPos(&p);
    wc.lpfnWndProc = DefWindowProcA;
    wc.lpszClassName = cls;
    wc.hbrBackground = GetStockObject(GRAY_BRUSH);
    RegisterClassA(&wc);
    if (argc > 3 && !strcmp(argv[3], "owned")) {
        owner = CreateWindowExA(WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE, cls, "owner", WS_POPUP, -500, -500, 10, 10, 0, 0, 0, 0);
        cls = "Static";
    }
    w = CreateWindowExA(WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW, cls, "fake76", WS_POPUP | WS_BORDER,
                        p.x - 100, p.y - 100, 200, 200, owner, 0, 0, 0);
    ShowWindow(w, SW_SHOWNOACTIVATE);
    while (GetTickCount() < end) {
        while (PeekMessageA(&m, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&m);
        Sleep(20);
    }
    return 0;
}
