/* rgn.exe: popup 40x20 at 100,100 with a region built from 1-row rectangles,
 * row 5 has two spans [2,4) and [8,40); other rows [0,40). Waits 8 s. (#36: X shape check) */
#include <windows.h>
int WINAPI WinMain(HINSTANCE i, HINSTANCE p, LPSTR c, int s)
{
    WNDCLASSA wc = {0, DefWindowProcA, 0, 0, i, 0, 0, (HBRUSH)GetStockObject(WHITE_BRUSH), 0, "rgn"};
    HWND w; MSG m; DWORD n = 0; int y;
    struct { RGNDATAHEADER h; RECT r[64]; } d;
    RegisterClassA(&wc);
    w = CreateWindowExA(0, "rgn", "rgn", WS_POPUP, 100, 100, 40, 20, 0, 0, i, 0);
    for (y = 0; y < 20; y++) {
        if (y == 5) { SetRect(&d.r[n++], 2, y, 4, y + 1); SetRect(&d.r[n++], 8, y, 40, y + 1); }
        else SetRect(&d.r[n++], 0, y, 40, y + 1);
    }
    d.h.dwSize = sizeof(d.h); d.h.iType = RDH_RECTANGLES; d.h.nCount = n; d.h.nRgnSize = n * sizeof(RECT);
    SetRect(&d.h.rcBound, 0, 0, 40, 20);
    SetWindowRgn(w, ExtCreateRegion(NULL, sizeof(d.h) + n * sizeof(RECT), (RGNDATA *)&d), TRUE);
    ShowWindow(w, SW_SHOW);
    {   /* the region Wine keeps for the window */
        HRGN r = CreateRectRgn(0, 0, 0, 0); char t[128];
        GetWindowRgn(w, r);
        wsprintfA(t, "rgn: in(3,5)=%d in(5,5)=%d in(9,5)=%d bytes=%lu\n", PtInRegion(r, 3, 5), PtInRegion(r, 5, 5), PtInRegion(r, 9, 5), GetRegionData(r, 0, NULL));
        OutputDebugStringA(t); { DWORD wr; WriteFile(GetStdHandle(STD_ERROR_HANDLE), t, lstrlenA(t), &wr, NULL); }
    }
    SetTimer(0, 0, 8000, 0);
    while (GetMessageA(&m, 0, 0, 0)) { if (m.message == WM_TIMER) break; DispatchMessageA(&m); }
    return 0;
}
