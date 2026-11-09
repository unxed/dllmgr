/* #36 probe: per-pixel-alpha layered popup (UpdateLayeredWindow, ULW_ALPHA)
 * in a DPI-unaware process. Image 400x300: left half opaque red, right half
 * 50% blue (premultiplied), 40 px transparent margin around.
 *   ulw-alpha.exe [seconds] [managed]   ("managed": WS_SYSMENU, owned) */
#include <windows.h>
#include <stdlib.h>
#include <string.h>

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSW wc = {0};
    HWND owner = NULL, hwnd;
    BITMAPINFO bi = {{sizeof(BITMAPINFOHEADER), 400, -300, 1, 32, BI_RGB}};
    DWORD *bits, end;
    HDC mem = CreateCompatibleDC(NULL);
    HBITMAP dib;
    POINT zero = {0, 0}, pos = {200, 150};
    SIZE size = {400, 300};
    BLENDFUNCTION bf = {AC_SRC_OVER, 0, 255, AC_SRC_ALPHA};
    MSG msg;
    int x, y, secs = atoi(cmd) > 0 ? atoi(cmd) : 20;
    BOOL managed = strstr(cmd, "managed") != NULL;

    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = inst;
    wc.lpszClassName = L"ulw36";
    RegisterClassW(&wc);
    if (managed) owner = CreateWindowExW(0, L"ulw36", L"ulw36 owner", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 900, 700, 0, 0, inst, 0);
    hwnd = CreateWindowExW(WS_EX_LAYERED, L"ulw36", L"ulw36", WS_POPUP | (managed ? WS_SYSMENU : 0),
                           pos.x, pos.y, 400, 300, owner, 0, inst, 0);
    dib = CreateDIBSection(mem, &bi, DIB_RGB_COLORS, (void **)&bits, NULL, 0);
    SelectObject(mem, dib);
    for (y = 0; y < 300; y++)
        for (x = 0; x < 400; x++) {
            DWORD v = 0;
            if (x >= 40 && x < 360 && y >= 40 && y < 260) v = x < 200 ? 0xffff0000 : 0x80000080;
            bits[y * 400 + x] = v;
        }
    if (!UpdateLayeredWindow(hwnd, NULL, &pos, &size, mem, &zero, 0, &bf, ULW_ALPHA)) return 2;
    ShowWindow(hwnd, SW_SHOWNOACTIVATE);
    end = GetTickCount() + secs * 1000;
    while ((int)(end - GetTickCount()) > 0) {
        while (PeekMessageW(&msg, 0, 0, 0, PM_REMOVE)) { TranslateMessage(&msg); DispatchMessageW(&msg); }
        MsgWaitForMultipleObjects(0, NULL, FALSE, 100, QS_ALLINPUT);
    }
    return 0;
}
