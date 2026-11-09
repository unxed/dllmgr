/* #44: a DPI-unaware window with a custom 32x32 cursor.
 *   cursor-scale.exe mono|color [seconds]
 * mono:  CreateCursor (AND/XOR planes, crosshair with inverted centre)
 * color: CreateIconIndirect with a 32bpp ARGB bitmap (filled square)
 * The window covers (0,0)-(400,300) in its own (96 DPI) coordinates; the probe
 * script measures the X cursor with XFixes. Windows shows such cursors scaled
 * by the display scale factor; expect 64x64 at 192 DPI with dllmgr-44. */
#include <windows.h>
#include <stdlib.h>
#include <string.h>

static HCURSOR mono_cursor(void)
{
    BYTE and_bits[32 * 4], xor_bits[32 * 4];
    int y;
    memset(and_bits, 0xff, sizeof(and_bits));
    memset(xor_bits, 0, sizeof(xor_bits));
    for (y = 0; y < 32; y++)
    {
        if (y == 15 || y == 16) { memset(and_bits + y * 4, 0, 4); memset(xor_bits + y * 4, 0, 4); continue; }
        and_bits[y * 4 + 1] &= ~0x01; and_bits[y * 4 + 2] &= ~0x80; /* vertical bar x=15,16: black */
    }
    xor_bits[15 * 4 + 1] = xor_bits[16 * 4 + 1] = 0x01;     /* x=15 white on the bar rows */
    and_bits[15 * 4 + 1] |= 0x01; and_bits[16 * 4 + 1] |= 0x01; /* inverted pixel at (15,15),(15,16) */
    return CreateCursor(GetModuleHandleW(NULL), 15, 15, 32, 32, and_bits, xor_bits);
}

static HCURSOR color_cursor(void)
{
    BITMAPINFO bi = {{sizeof(BITMAPINFOHEADER), 32, -32, 1, 32, BI_RGB}};
    DWORD *bits;
    ICONINFO ii = {FALSE, 4, 4, 0, 0};
    HDC hdc = GetDC(0);
    HCURSOR cursor;
    int i;
    ii.hbmColor = CreateDIBSection(hdc, &bi, DIB_RGB_COLORS, (void **)&bits, NULL, 0);
    for (i = 0; i < 32 * 32; i++) bits[i] = (i % 32 < 24 && i / 32 < 24) ? 0xffff0000 : 0;
    ii.hbmMask = CreateBitmap(32, 32, 1, 1, NULL);
    cursor = CreateIconIndirect(&ii);
    ReleaseDC(0, hdc);
    return cursor;
}

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASSW wc = {0};
    HWND hwnd;
    MSG msg;
    DWORD end;
    int secs = 30;
    char *space = strchr(cmd, ' ');
    if (space) secs = atoi(space + 1);
    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = inst;
    wc.lpszClassName = L"cursor44";
    wc.hCursor = strncmp(cmd, "color", 5) ? mono_cursor() : color_cursor();
    if (!wc.hCursor) return 2;
    RegisterClassW(&wc);
    hwnd = CreateWindowExW(0, L"cursor44", L"cursor44", WS_POPUP | WS_VISIBLE, 0, 0, 400, 300, 0, 0, inst, 0);
    if (!hwnd) return 3;
    end = GetTickCount() + secs * 1000;
    while ((int)(end - GetTickCount()) > 0)
    {
        while (PeekMessageW(&msg, 0, 0, 0, PM_REMOVE)) { TranslateMessage(&msg); DispatchMessageW(&msg); }
        MsgWaitForMultipleObjects(0, NULL, FALSE, 100, QS_ALLINPUT);
    }
    return 0;
}
