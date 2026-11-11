/* screendc80.c: where does drawing on a screen DC from a DPI-unaware thread
 * land, and in which coordinates? (#80, Photoshop CS2 palette drag outline)
 *
 * Photoshop CS2 (DPI-unaware) draws its palette drag outline with an XOR pen
 * on GetWindowDC(GetDesktopWindow()) in the coordinates it gets from
 * GetCursorPos/GetWindowRect (virtualized, i.e. logical). This probe draws a
 * rectangle outline at logical (L,T)-(R,B) on several screen DCs from an
 * unaware thread, captures the screen from a per-monitor-aware thread before
 * and after, and prints the bounding box of the changed pixels in physical
 * coordinates. It also prints what the unaware thread sees (metrics, caps).
 *
 * Usage: screendc80 [setscale] -- "setscale" first raises the resolution to
 * the largest mode and the monitor scale to the largest allowed step (via
 * DisplayConfigSetDeviceInfo, the call the Settings app uses), then runs the
 * measurement in a fresh child process. Without it: measure only.
 * Public APIs only; black-box behaviour of Windows.
 */
#include <windows.h>
#include <stdio.h>

#ifndef DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
#define DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 ((HANDLE)-4)
#endif
#define DPI_CTX_UNAWARE ((HANDLE)-1)

static HANDLE (WINAPI *pSetThreadDpiAwarenessContext)(HANDLE);
static UINT (WINAPI *pGetDpiForSystem)(void);
static HRESULT (WINAPI *pGetDpiForMonitor)(HMONITOR, int, UINT *, UINT *);
static HRESULT (WINAPI *pDwmFlush)(void);

static void flush(void)
{
    GdiFlush();
    if (pDwmFlush) pDwmFlush();
    Sleep(300);
    if (pDwmFlush) pDwmFlush();
}

/* capture the whole primary screen in physical pixels (PMv2 thread context) */
static DWORD *capture(int *w, int *h)
{
    HANDLE old = pSetThreadDpiAwarenessContext ? pSetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) : NULL;
    HDC sdc = GetDC(0), mdc = CreateCompatibleDC(sdc);
    BITMAPINFO bi = {{sizeof(BITMAPINFOHEADER)}};
    DWORD *bits;
    HBITMAP bmp;
    *w = GetSystemMetrics(SM_CXSCREEN); *h = GetSystemMetrics(SM_CYSCREEN);
    bi.bmiHeader.biWidth = *w; bi.bmiHeader.biHeight = -*h;
    bi.bmiHeader.biPlanes = 1; bi.bmiHeader.biBitCount = 32;
    bmp = CreateDIBSection(mdc, &bi, DIB_RGB_COLORS, (void **)&bits, NULL, 0);
    SelectObject(mdc, bmp);
    BitBlt(mdc, 0, 0, *w, *h, sdc, 0, 0, SRCCOPY);
    GdiFlush();
    {
        DWORD *copy = malloc((size_t)*w * *h * 4);
        memcpy(copy, bits, (size_t)*w * *h * 4);
        DeleteDC(mdc); DeleteObject(bmp); ReleaseDC(0, sdc);
        if (old) pSetThreadDpiAwarenessContext(old);
        return copy;
    }
}

static void diffbox(const char *what, DWORD *a, DWORD *b, int w, int h)
{
    int l = w, t = h, r = -1, btm = -1, n = 0, x, y;
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++)
            if ((a[y * w + x] ^ b[y * w + x]) & 0xffffff)
            {
                n++;
                l = min(l, x); r = max(r, x);
                t = min(t, y); btm = max(btm, y);
            }
    if (n) printf("%s: changed %d px, physical box %d,%d-%d,%d (%dx%d)\n", what, n, l, t, r + 1, btm + 1, r + 1 - l, btm + 1 - t);
    else printf("%s: nothing changed on screen\n", what);
}

static void outline(HDC hdc, int l, int t, int r, int b)
{
    int rop = SetROP2(hdc, R2_NOT);
    MoveToEx(hdc, l, t, NULL); LineTo(hdc, r - 1, t); LineTo(hdc, r - 1, b - 1);
    LineTo(hdc, l, b - 1); LineTo(hdc, l, t);
    SetROP2(hdc, rop);
}

enum { DC_GETDC0, DC_WINDOWDC_DESKTOP, DC_DCEX_LOCK, DC_CREATEDC };
static const char *dcname[] = { "GetDC(NULL)", "GetWindowDC(GetDesktopWindow())",
    "GetDCEx(desktop,DCX_WINDOW|DCX_CACHE|DCX_LOCKWINDOWUPDATE)", "CreateDC(\"DISPLAY\")" };

static HDC getdc(int kind)
{
    switch (kind)
    {
    case DC_GETDC0: return GetDC(0);
    case DC_WINDOWDC_DESKTOP: return GetWindowDC(GetDesktopWindow());
    case DC_DCEX_LOCK: return GetDCEx(GetDesktopWindow(), 0, DCX_WINDOW | DCX_CACHE | DCX_LOCKWINDOWUPDATE);
    default: return CreateDCA("DISPLAY", NULL, NULL, NULL);
    }
}

static void putdc(int kind, HDC hdc)
{
    if (kind == DC_CREATEDC) DeleteDC(hdc);
    else ReleaseDC(kind == DC_GETDC0 ? 0 : GetDesktopWindow(), hdc);
}

static void measure(void)
{
    int kind, w, h, pass;
    POINT pt;
    RECT rc;
    HMONITOR mon = MonitorFromPoint((POINT){0, 0}, MONITOR_DEFAULTTOPRIMARY);
    UINT mx = 0, my = 0;
    HWND bg;
    /* a plain white window under the drawing area so the XOR is visible */
    HANDLE old = pSetThreadDpiAwarenessContext ? pSetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) : NULL;
    if (pGetDpiForMonitor) pGetDpiForMonitor(mon, 0, &mx, &my);
    printf("PMv2 thread: SM_CXSCREEN=%d SM_CYSCREEN=%d monitor dpi=%u\n",
           GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), mx);
    bg = CreateWindowExA(WS_EX_TOPMOST | WS_EX_TOOLWINDOW, "STATIC", "", WS_POPUP | WS_VISIBLE,
                         0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), 0, 0, 0, 0);
    if (old) pSetThreadDpiAwarenessContext(old);
    if (pSetThreadDpiAwarenessContext) pSetThreadDpiAwarenessContext(DPI_CTX_UNAWARE);
    {
        MSG msg; DWORD end = GetTickCount() + 1000;
        while (GetTickCount() < end) { while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg); Sleep(20); }
    }
    printf("unaware thread: SM_CXSCREEN=%d SM_CYSCREEN=%d system dpi=%u\n",
           GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), pGetDpiForSystem ? pGetDpiForSystem() : 0);
    GetWindowRect(GetDesktopWindow(), &rc);
    printf("unaware thread: desktop window rect %ld,%ld-%ld,%ld\n", rc.left, rc.top, rc.right, rc.bottom);
    SetCursorPos(400, 300); GetCursorPos(&pt);
    printf("unaware thread: SetCursorPos(400,300) -> GetCursorPos %ld,%ld\n", pt.x, pt.y);
    for (kind = 0; kind < 4; kind++)
    {
        HDC hdc = getdc(kind);
        RECT clip;
        int cr = GetClipBox(hdc, &clip);
        printf("%s: HORZRES=%d VERTRES=%d DESKTOPHORZRES=%d LOGPIXELSX=%d clipbox(%d) %ld,%ld-%ld,%ld\n", dcname[kind],
               GetDeviceCaps(hdc, HORZRES), GetDeviceCaps(hdc, VERTRES), GetDeviceCaps(hdc, DESKTOPHORZRES),
               GetDeviceCaps(hdc, LOGPIXELSX), cr, clip.left, clip.top, clip.right, clip.bottom);
        putdc(kind, hdc);
    }
    for (pass = 0; pass < 2; pass++)
        for (kind = 0; kind < 4; kind++)
        {
            DWORD *a, *b;
            HDC hdc;
            char what[200];
            a = capture(&w, &h);
            hdc = getdc(kind);
            if (pass == 0) outline(hdc, 100, 100, 300, 250);
            else PatBlt(hdc, 100, 100, 200, 150, DSTINVERT);
            putdc(kind, hdc);
            flush();
            b = capture(&w, &h);
            snprintf(what, sizeof(what), "%s %s logical 100,100-300,250", dcname[kind],
                     pass ? "PatBlt(DSTINVERT)" : "R2_NOT outline");
            diffbox(what, a, b, w, h);
            hdc = getdc(kind); /* undo */
            if (pass == 0) outline(hdc, 100, 100, 300, 250);
            else PatBlt(hdc, 100, 100, 200, 150, DSTINVERT);
            putdc(kind, hdc);
            flush();
            free(a); free(b);
        }
    DestroyWindow(bg);
}

typedef struct { DISPLAYCONFIG_DEVICE_INFO_HEADER header; int minRel, curRel, maxRel; } DPI_GET;
typedef struct { DISPLAYCONFIG_DEVICE_INFO_HEADER header; int rel; } DPI_SET;

static void setscale(void)
{
    DEVMODEA dm = {0}, best = {0};
    UINT32 np = 0, nm = 0;
    DISPLAYCONFIG_PATH_INFO *paths;
    DISPLAYCONFIG_MODE_INFO *modes;
    DPI_GET g = {{0}};
    DPI_SET s = {{0}};
    int i;
    LONG r;

    dm.dmSize = sizeof(dm);
    for (i = 0; EnumDisplaySettingsA(NULL, i, &dm); i++)
        if (dm.dmBitsPerPel == 32 && (UINT64)dm.dmPelsWidth * dm.dmPelsHeight > (UINT64)best.dmPelsWidth * best.dmPelsHeight)
            best = dm;
    if (best.dmPelsWidth)
    {
        best.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL;
        r = ChangeDisplaySettingsA(&best, 0);
        printf("setscale: largest mode %lux%lu, ChangeDisplaySettings=%ld\n", best.dmPelsWidth, best.dmPelsHeight, r);
    }
    GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, &np, &nm);
    paths = calloc(np, sizeof(*paths)); modes = calloc(nm, sizeof(*modes));
    r = QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, &np, paths, &nm, modes, NULL);
    if (r || !np) { printf("setscale: QueryDisplayConfig=%ld paths=%u\n", r, np); return; }
    g.header.type = (DISPLAYCONFIG_DEVICE_INFO_TYPE)-3; g.header.size = sizeof(g);
    g.header.adapterId = paths[0].sourceInfo.adapterId; g.header.id = paths[0].sourceInfo.id;
    r = DisplayConfigGetDeviceInfo(&g.header);
    printf("setscale: get=%ld minRel=%d curRel=%d maxRel=%d\n", r, g.minRel, g.curRel, g.maxRel);
    s.header.type = (DISPLAYCONFIG_DEVICE_INFO_TYPE)-4; s.header.size = sizeof(s);
    s.header.adapterId = g.header.adapterId; s.header.id = g.header.id; s.rel = g.maxRel;
    r = DisplayConfigSetDeviceInfo(&s.header);
    printf("setscale: set rel=%d -> %ld\n", s.rel, r);
    Sleep(3000);
}

int main(int argc, char **argv)
{
    HMODULE u = GetModuleHandleA("user32.dll"), sh = LoadLibraryA("shcore.dll"), dwm = LoadLibraryA("dwmapi.dll");
    pSetThreadDpiAwarenessContext = (void *)GetProcAddress(u, "SetThreadDpiAwarenessContext");
    pGetDpiForSystem = (void *)GetProcAddress(u, "GetDpiForSystem");
    if (sh) pGetDpiForMonitor = (void *)GetProcAddress(sh, "GetDpiForMonitor");
    if (dwm) pDwmFlush = (void *)GetProcAddress(dwm, "DwmFlush");
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc > 1 && !strcmp(argv[1], "setscale"))
    {
        char cmd[MAX_PATH + 20];
        STARTUPINFOA si = {sizeof(si)};
        PROCESS_INFORMATION pi;
        setscale();
        GetModuleFileNameA(NULL, cmd, MAX_PATH);
        if (CreateProcessA(cmd, NULL, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
        {
            WaitForSingleObject(pi.hProcess, 120000);
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
        }
        return 0;
    }
    measure();
    return 0;
}
