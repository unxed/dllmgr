/* dllmgr issue 27 workaround, public Win32 APIs only, no Wine changes.
 *
 * Delivered as a proxy msimg32.dll next to the application (load order
 * msimg32=n,b for that exe): its exports forward to gdi32 exactly like Wine's
 * own msimg32. On process attach it replaces user32!ShowWindow in the main
 * module's import table with show_prefilled(): when a hidden top-level window
 * is shown, the screen under it is copied first and drawn into the window
 * right after ShowWindow, then flushed. The first thing presented is the old
 * screen contents (what Windows shows until the application paints) instead of
 * Wine's 0xff-initialised surface, which an X Expose otherwise presents as a
 * white flash. The application still receives its WM_PAINT. A ~1 frame black
 * (the X window background before the first flush) cannot be removed from the
 * PE side; see patches/winehq-60721.patch for the Wine-side fix.
 *
 * Build (i686 for 32-bit FastStone): see build.sh. */
#include <windows.h>
#include <winternl.h>
#include <psapi.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include <string.h>

/* DLLMGR27_DEBUG=1: one line per decision on stderr (compact). */
static int debug;
#define TRACE(...) do { if (debug) { fprintf(stderr, "dllmgr27[%04lx]: ", GetCurrentProcessId()); fprintf(stderr, __VA_ARGS__); fflush(stderr); } } while (0)

static BOOL (WINAPI *real_show_window)(HWND, int);

/* Capture and draw in physical pixels on both sides. In a DPI-unaware app
 * (Photoshop CS2) Wine scales window coordinates; mixing a logical capture
 * with a scaled window DC showed a 2x enlarged copy in small windows.
 * Resolved at runtime: user32 of Windows < 10 / old Wine lacks these. */
typedef DPI_AWARENESS_CONTEXT (WINAPI *set_ctx_fn)(DPI_AWARENESS_CONTEXT);
static set_ctx_fn set_thread_dpi_ctx;
static UINT (WINAPI *dpi_for_window)(HWND);

static DPI_AWARENESS_CONTEXT physical_begin(void)
{
    if (!set_thread_dpi_ctx) {
        HMODULE user32 = GetModuleHandleA("user32.dll");
        set_thread_dpi_ctx = (set_ctx_fn)GetProcAddress(user32, "SetThreadDpiAwarenessContext");
        dpi_for_window = (void *)GetProcAddress(user32, "GetDpiForWindow");
    }
    return set_thread_dpi_ctx ? set_thread_dpi_ctx(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE) : NULL;
}

static void physical_end(DPI_AWARENESS_CONTEXT old)
{
    if (old && set_thread_dpi_ctx) set_thread_dpi_ctx(old);
}

void WINAPI vSetDdrawflag(void)
{
}

static BOOL shows(int cmd)
{
    return cmd != SW_HIDE && cmd != SW_MINIMIZE && cmd != SW_SHOWMINIMIZED &&
           cmd != SW_SHOWMINNOACTIVE && cmd != SW_FORCEMINIMIZE;
}

static BOOL WINAPI show_prefilled(HWND window, int cmd)
{
    RECT rect;
    HDC screen, mem = NULL, dc;
    HBITMAP bitmap = NULL, old = NULL;
    int w = 0, h = 0;
    BOOL ret;

    if (!shows(cmd) || IsWindowVisible(window) || (GetWindowLongW(window, GWL_STYLE) & WS_CHILD) ||
        !GetWindowRect(window, &rect))
        return real_show_window(window, cmd);

    /* SW_MAXIMIZE / SW_SHOWMAXIMIZED change the rect: take the work area
     * of the window's monitor as the target. */
    if (cmd == SW_MAXIMIZE) {
        MONITORINFO info = {sizeof(info)};
        if (GetMonitorInfoW(MonitorFromWindow(window, MONITOR_DEFAULTTONEAREST), &info)) rect = info.rcWork;
    }
    w = rect.right - rect.left;
    h = rect.bottom - rect.top;
    if (w > 0 && h > 0 && (screen = GetDC(NULL))) {
        if ((mem = CreateCompatibleDC(screen)) && (bitmap = CreateCompatibleBitmap(screen, w, h))) {
            old = SelectObject(mem, bitmap);
            BitBlt(mem, 0, 0, w, h, screen, rect.left, rect.top, SRCCOPY);
        }
        ReleaseDC(NULL, screen);
    }

    ret = real_show_window(window, cmd);

    if (bitmap) {
        RECT now;
        /* draw where the window actually ended up, relative to its window DC */
        if (GetWindowRect(window, &now) && (dc = GetDCEx(window, NULL, DCX_WINDOW | DCX_CACHE))) {
            BitBlt(dc, rect.left - now.left, rect.top - now.top, w, h, mem, 0, 0, SRCCOPY);
            ReleaseDC(window, dc);
        }
        GdiFlush();
        SelectObject(mem, old);
        DeleteObject(bitmap);
    }
    if (mem) DeleteDC(mem);
    return ret;
}

/* Replace the main module's import slots that hold the address of dll!name.
 * Matching by resolved address, not by import name: Borland/Delphi images
 * have no OriginalFirstThunk, and by the time DllMain runs FirstThunk already
 * holds addresses (reading them as name RVAs crashed the loader). */
static BOOL hook_import(HMODULE module, const char *dll, const char *name, void *hook, void **real)
{
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    IMAGE_IMPORT_DESCRIPTOR *desc;
    HMODULE target_module = GetModuleHandleA(dll);
    ULONG_PTR target = target_module ? (ULONG_PTR)GetProcAddress(target_module, name) : 0;
    BOOL found = FALSE;

    if (!target || !dir->VirtualAddress) return FALSE;
    for (desc = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir->VirtualAddress); desc->Name; desc++) {
        IMAGE_THUNK_DATA *slot;
        for (slot = (IMAGE_THUNK_DATA *)(base + desc->FirstThunk); slot->u1.Function; slot++) {
            DWORD protect;
            if (slot->u1.Function != target) continue;
            if (!VirtualProtect(&slot->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) continue;
            *real = (void *)target;
            slot->u1.Function = (ULONG_PTR)hook;
            VirtualProtect(&slot->u1.Function, sizeof(void *), protect, &protect);
            found = TRUE;
        }
    }
    return found;
}

/* Message-hook mode (default): works for whatever module creates the windows
 * (Photoshop's UI lives in DLLs, its exe imports no user32). Per-thread hooks
 * only, never global ones, so other processes are untouched. A window shown
 * via ShowWindow or SetWindowPos(SWP_SHOWWINDOW) gets WM_WINDOWPOSCHANGING
 * (still hidden: capture the screen under its target rect) and then
 * WM_WINDOWPOSCHANGED (shown, not painted yet: draw the capture, flush). */
struct capture { HWND hwnd; HDC mem; HBITMAP bitmap, old; RECT rect; };
static struct capture captures[16];
static HINSTANCE self;

static struct capture *find_capture(HWND hwnd)
{
    for (int i = 0; i < 16; i++) if (captures[i].hwnd == hwnd) return &captures[i];
    return NULL;
}

static void release_capture(struct capture *c)
{
    SelectObject(c->mem, c->old);
    DeleteObject(c->bitmap);
    DeleteDC(c->mem);
    c->hwnd = NULL;
}

static void capture_under(HWND hwnd, const WINDOWPOS *pos)
{
    if (GetEnvironmentVariableA("DLLMGR27_NO_PREFILL", NULL, 0)) return; /* no screen snapshot (diagnostics) */
    struct capture *c = find_capture(NULL);
    RECT rect;
    HDC screen;
    int w, h;

    char cls[64] = "";
    GetClassNameA(hwnd, cls, sizeof(cls));
    TRACE("capture tid=%04lx hwnd=%p class=%s flags=%04x\n", GetCurrentThreadId(), (void *)hwnd, cls, pos->flags);
    UINT app_dpi = dpi_for_window ? dpi_for_window(hwnd) : 96;  /* in the app's own context */
    DPI_AWARENESS_CONTEXT old_ctx;
    if (!c || find_capture(hwnd)) return;
#ifdef DLLMGR27_CAPTIONLESS_ONLY
    /* Photoshop build (version.dll): only the splash needs the prefill. Its
     * "Adobe Activation" dialog never paints its own body: with the prefill
     * it showed the window behind as background, stock Wine shows white
     * (owner A/B, 2026-11-09). Windows with a caption are left alone. */
    if ((GetWindowLongW(hwnd, GWL_STYLE) & WS_CAPTION) == WS_CAPTION) return;
    /* #83: Photoshop's tool windows (palettes, toolbox, options bar and its
     * Opacity/Flow slider popups) paint themselves completely; the popup
     * paints its 3D frame as non-client area, which Wine does before
     * WM_WINDOWPOSCHANGED, so the snapshot presented there replaced the frame.
     * The snapshot itself comes from the wrong place under Wine's DPI
     * virtualization (GetWindowRect stays logical in a per-monitor-aware
     * thread, the screen DC is physical): the owner saw the menu bar text
     * around the popup. The splash, the one window that needs the snapshot,
     * is not a tool window. */
    if (GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW) return;
#endif
    old_ctx = physical_begin();
    if (!GetWindowRect(hwnd, &rect)) { physical_end(old_ctx); return; }
    {
        /* WINDOWPOS is in the app's coordinates; convert to physical. */
        HDC probe = GetDC(NULL);
        UINT phys_dpi = probe ? GetDeviceCaps(probe, LOGPIXELSY) : app_dpi;  /* aware context: real DPI */
        if (probe) ReleaseDC(NULL, probe);
        if (!(pos->flags & SWP_NOMOVE))
            OffsetRect(&rect, MulDiv(pos->x, phys_dpi, app_dpi) - rect.left, MulDiv(pos->y, phys_dpi, app_dpi) - rect.top);
        if (!(pos->flags & SWP_NOSIZE)) {
            rect.right = rect.left + MulDiv(pos->cx, phys_dpi, app_dpi);
            rect.bottom = rect.top + MulDiv(pos->cy, phys_dpi, app_dpi);
        }
    }
    w = rect.right - rect.left; h = rect.bottom - rect.top;
    if (w <= 0 || h <= 0 || !(screen = GetDC(NULL))) { physical_end(old_ctx); return; }
    c->mem = CreateCompatibleDC(screen);
    c->bitmap = c->mem ? CreateCompatibleBitmap(screen, w, h) : NULL;
    if (c->bitmap) {
        c->old = SelectObject(c->mem, c->bitmap);
        BitBlt(c->mem, 0, 0, w, h, screen, rect.left, rect.top, SRCCOPY);
        c->rect = rect;
        c->hwnd = hwnd;
    } else if (c->mem) DeleteDC(c->mem);
    ReleaseDC(NULL, screen);
    physical_end(old_ctx);
}

/* Issue 36 (Photoshop CS2 splash): the app composes its splash (card, feather,
 * shadow) over whatever its window holds and leaves the margin untouched. With
 * the prefill that margin is a frozen snapshot of the screen. Once the app has
 * finished painting, cut the pixels still identical to the snapshot out of the
 * window (SetWindowRgn), so the margin becomes truly see-through. Only
 * top-level windows without a caption; windows painted completely (menus, main
 * windows, FastStone's forms) are left alone. DLLMGR27_NO_SHAPE=1 disables it. */
struct shape { HWND hwnd; HDC mem; HBITMAP bitmap, old; RECT rect; int tries; LONG last; DWORD when; };
static struct shape shapes[4];
static LONG shape_pending;  /* cheap check in the hooks */
static HWND splash;         /* the shaped splash (#36), adopted for #43 */

#ifdef DLLMGR27_CAPTIONLESS_ONLY
/* #43 part 1: Wine maps a caption-less popup shown without activation as an
 * override-redirect X window, so the WM cannot hide it with its minimized
 * owner, and Photoshop's busy thread never runs ShowOwnedPopups. A popup with
 * WS_SYSMENU is managed by winex11 (no visible change without a caption).
 * 1. adopt_early: the first caption-less, owned, non-tool popup of at least
 *    200x100 (the startup splash; palettes are WS_EX_TOOLWINDOW) gets
 *    WS_SYSMENU before it is mapped, so it is mapped managed from the start
 *    (switching a mapped window to managed remaps it: visible glitches).
 * 2. The WM maps it some time after Wine asked; what Photoshop painted
 *    before that never reaches the screen and the busy thread never handles
 *    the Expose: represent_thread copies the splash onto itself from another
 *    thread every 100 ms for 4 s (marks the surface drawn and flushes it).
 * 3. adopt_owner_shown: if the owner was unmapped when the splash was mapped,
 *    the WM could not resolve WM_TRANSIENT_FOR; a WS_DISABLED toggle makes
 *    winex11 set the hint again once the owner is shown.
 * Known: under the private runtime the margin around the card is white (the
 * shape is set but not honoured on screen; experiments/ps-focus/README.md).
 * DLLMGR43_NO_ADOPT=1 turns it off. */
static HWND early;
static HWND adopted;
static DWORD WINAPI represent_thread(void *arg);

/* the startup splash: owned, caption-less, non-tool popup (palettes are
 * WS_EX_TOOLWINDOW); WS_SYSMENU is ours once adopted */
static BOOL splash_like(HWND hwnd)
{
    LONG style = GetWindowLongW(hwnd, GWL_STYLE);
    return GetWindow(hwnd, GW_OWNER) && !(style & WS_CHILD) && (style & WS_CAPTION) != WS_CAPTION &&
           (style & WS_POPUP) && !(GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW);
}

static void adopt_early(HWND hwnd, const WINDOWPOS *pos)
{
    LONG style = GetWindowLongW(hwnd, GWL_STYLE);
    HWND owner = GetWindow(hwnd, GW_OWNER);
    RECT r;
    int w, h;
    if (early || !splash_like(hwnd) || (style & WS_SYSMENU) || GetEnvironmentVariableA("DLLMGR43_NO_ADOPT", NULL, 0))
        return;
    GetWindowRect(hwnd, &r);
    w = (pos->flags & SWP_NOSIZE) ? r.right - r.left : pos->cx;
    h = (pos->flags & SWP_NOSIZE) ? r.bottom - r.top : pos->cy;
    if (w < 200 || h < 100) return;
    early = adopted = hwnd;
    SetWindowLongW(hwnd, GWL_STYLE, style | WS_SYSMENU);
    TRACE("adopt: startup popup %p (owner %p) will be mapped managed\n", (void *)hwnd, (void *)owner);
    if (!GetEnvironmentVariableA("DLLMGR43_NO_REPRESENT", NULL, 0)) {
        HANDLE t = CreateThread(NULL, 0, represent_thread, hwnd, 0, NULL);
        if (t) CloseHandle(t);
    }
}

/* The WM maps a managed window some time after Wine asked for it; what
 * Photoshop painted before that point never reaches the screen, and its busy
 * thread does not process the Expose that would re-present it. A helper
 * thread copies the splash onto itself (marks the whole surface drawn and
 * flushes it) every 100 ms for a few seconds. */
static DWORD WINAPI represent_thread(void *arg)
{
    HWND hwnd = arg;
    int i;
    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    for (i = 0; i < 40 && IsWindow(hwnd); i++) {
        RECT r;
        HDC dc;
        Sleep(100);
        if (!IsWindowVisible(hwnd) || !GetWindowRect(hwnd, &r)) continue;
        if ((dc = GetDCEx(hwnd, NULL, DCX_WINDOW | DCX_CACHE))) {
            BitBlt(dc, 0, 0, r.right - r.left, r.bottom - r.top, dc, 0, 0, SRCCOPY);
            ReleaseDC(hwnd, dc);
            GdiFlush();
        }
    }
    return 0;
}

static void adopt_owner_shown(HWND shown)
{
    LONG style;
    if (!early || !IsWindow(early) || GetWindow(early, GW_OWNER) != shown) return;
    style = GetWindowLongW(early, GWL_STYLE);
    SetWindowLongW(early, GWL_STYLE, style ^ WS_DISABLED);
    SetWindowLongW(early, GWL_STYLE, style);
    TRACE("adopt: owner %p shown, WM_TRANSIENT_FOR of %p set again\n", (void *)shown, (void *)early);
    early = NULL;
}
#else
static const HWND adopted;
static void adopt_early(HWND hwnd, const WINDOWPOS *pos) {}
static void adopt_owner_shown(HWND shown) {}
#endif
static int (WINAPI *real_release_dc)(HWND, HDC);

static void shape_release(struct shape *s)
{
    SelectObject(s->mem, s->old);
    DeleteObject(s->bitmap);
    DeleteDC(s->mem);
    s->hwnd = NULL;
}

static DWORD *read_bits(HDC src, int x, int y, int w, int h)
{
    BITMAPINFO bi = {{sizeof(bi.bmiHeader), w, -h, 1, 32, BI_RGB}};
    DWORD *bits = NULL, *copy = NULL;
    HDC mem = CreateCompatibleDC(src);
    HBITMAP dib = mem ? CreateDIBSection(mem, &bi, DIB_RGB_COLORS, (void **)&bits, NULL, 0) : NULL;
    if (dib) {
        HGDIOBJ old = SelectObject(mem, dib);
        BitBlt(mem, 0, 0, w, h, src, x, y, SRCCOPY);
        GdiFlush();
        if ((copy = HeapAlloc(GetProcessHeap(), 0, (SIZE_T)w * h * 4))) memcpy(copy, bits, (SIZE_T)w * h * 4);
        SelectObject(mem, old);
        DeleteObject(dib);
    }
    if (mem) DeleteDC(mem);
    return copy;
}

/* Region of the pixels that differ, one rectangle per run in each row. */
static HRGN changed_region(const DWORD *a, const DWORD *b, int w, int h)
{
    DWORD cap = 1024, n = 0;
    RGNDATA *data = HeapAlloc(GetProcessHeap(), 0, sizeof(RGNDATAHEADER) + cap * sizeof(RECT));
    HRGN rgn = NULL;
    for (int y = 0; data && y < h; y++)
        for (int x = 0; x < w; ) {
            int start;
            while (x < w && (a[y * w + x] & 0xffffff) == (b[y * w + x] & 0xffffff)) x++;
            if (x >= w) break;
            start = x;
            while (x < w && (a[y * w + x] & 0xffffff) != (b[y * w + x] & 0xffffff)) x++;
            if (n == cap) {
                RGNDATA *bigger = HeapReAlloc(GetProcessHeap(), 0, data, sizeof(RGNDATAHEADER) + cap * 2 * sizeof(RECT));
                if (!bigger) { HeapFree(GetProcessHeap(), 0, data); return NULL; }
                data = bigger; cap *= 2;
            }
            SetRect((RECT *)data->Buffer + n++, start, y, x, y + 1);
        }
    if (data) {
        data->rdh.dwSize = sizeof(RGNDATAHEADER);
        data->rdh.iType = RDH_RECTANGLES;
        data->rdh.nCount = n;
        data->rdh.nRgnSize = n * sizeof(RECT);
        SetRect(&data->rdh.rcBound, 0, 0, w, h);
        rgn = ExtCreateRegion(NULL, sizeof(RGNDATAHEADER) + n * sizeof(RECT), data);
        HeapFree(GetProcessHeap(), 0, data);
    }
    return rgn;
}

#ifdef DLLMGR27_CAPTIONLESS_ONLY
/* #36: Photoshop draws the splash card with AlphaBlend from a premultiplied
 * 32-bit bitmap that carries the real alpha (rounded corners, shadow, the
 * feather reaching out of the card, transparent margin). The adopted splash
 * is shaped from that alpha directly (alpha >= DLLMGR36_ALPHA_MIN, default
 * 128): exact, independent of what is on the screen, so nothing stale can
 * ever show. Runs in Photoshop's own thread (winex11 applies window regions
 * only there). DLLMGR36_NO_ALPHA_SHAPE=1 keeps the white margin. */
static BOOL (WINAPI *real_alpha_blend)(HDC, int, int, int, int, HDC, int, int, int, int, BLENDFUNCTION);

static BOOL WINAPI alpha_blend_hook(HDC dst, int dx, int dy, int dw, int dh, HDC src, int sx, int sy, int sw, int sh,
                                    BLENDFUNCTION bf)
{
    BOOL ret = real_alpha_blend(dst, dx, dy, dw, dh, src, sx, sy, sw, sh, bf);
    HRGN have = NULL;
    HWND hwnd, root;
    BITMAP bm;
    RECT wr;
    POINT p = {dx, dy};
    int w, h, x, y, min = 128;
    char value[16];
    DWORD *mask, *none, *all;
    HBITMAP bmp;

    if ((LONGLONG)sw * sh > 100000)
        TRACE("AlphaBlend %dx%d ret=%d adopted=%p fmt=%d sca=%d dst hwnd=%p root=%p\n", sw, sh, ret, (void *)adopted,
              bf.AlphaFormat, bf.SourceConstantAlpha, (void *)WindowFromDC(dst),
              (void *)(WindowFromDC(dst) ? GetAncestor(WindowFromDC(dst), GA_ROOT) : 0));
    /* the card may be drawn before the splash is shown (and adopted); the
     * About box (Help > About Photoshop) is the same card in a new window:
     * shape every such window once (while it has no region yet) */
    if (!ret || bf.AlphaFormat != AC_SRC_ALPHA || bf.SourceConstantAlpha != 255 ||
        sw != dw || sh != dh || !(hwnd = WindowFromDC(dst)) || !(root = GetAncestor(hwnd, GA_ROOT)) ||
        !splash_like(root) || GetEnvironmentVariableA("DLLMGR43_NO_ADOPT", NULL, 0) ||
        !(bmp = GetCurrentObject(src, OBJ_BITMAP)) || !GetObjectW(bmp, sizeof(bm), &bm) || bm.bmBitsPixel != 32 ||
        !GetWindowRect(root, &wr) || GetEnvironmentVariableA("DLLMGR36_NO_ALPHA_SHAPE", NULL, 0))
        return ret;
    w = wr.right - wr.left; h = wr.bottom - wr.top;
    if ((LONGLONG)sw * sh * 2 < (LONGLONG)w * h) return ret;  /* the card, not an icon */
    have = CreateRectRgn(0, 0, 0, 0);
    if (have && GetWindowRgn(root, have) != ERROR) { DeleteObject(have); return ret; }  /* shaped already */
    if (have) DeleteObject(have);
    if (GetEnvironmentVariableA("DLLMGR36_ALPHA_MIN", value, sizeof(value)) && atoi(value) > 0) min = atoi(value);
    {   /* device position of the card: the DC may have its own origin */
        POINT org = {0, 0}, c = {0, 0};
        LPtoDP(dst, &p, 1);
        if (GetDCOrgEx(dst, &org)) { p.x += org.x; p.y += org.y; }
        else ClientToScreen(hwnd, &p);
        ClientToScreen(hwnd, &c);
        TRACE("card at dc %d,%d: device+org %ld,%ld (client origin %ld,%ld)\n", dx, dy, p.x, p.y, c.x, c.y);
    }
    p.x -= wr.left; p.y -= wr.top;
    mask = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)w * h * 4);
    none = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)w * h * 4);
    all = HeapAlloc(GetProcessHeap(), 0, (SIZE_T)bm.bmWidth * bm.bmHeight * 4);
    if (mask && none && all) {
        /* top-down request: orientation-safe */
        BITMAPINFO bi = {{sizeof(bi.bmiHeader), bm.bmWidth, -bm.bmHeight, 1, 32, BI_RGB}};
        if (GetDIBits(src, bmp, 0, bm.bmHeight, all, &bi, DIB_RGB_COLORS)) {
            HRGN rgn;
            if (GetEnvironmentVariableA("DLLMGR36_DUMP", value, sizeof(value))) {  /* debug: raw BGRA card */
                char path[64];
                HANDLE f;
                DWORD done;
                wsprintfA(path, "C:\\dllmgr36-card-%dx%d.bgra", bm.bmWidth, bm.bmHeight);
                f = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL);
                if (f != INVALID_HANDLE_VALUE) {
                    WriteFile(f, all, bm.bmWidth * bm.bmHeight * 4, &done, NULL);
                    CloseHandle(f);
                }
            }
            for (y = 0; y < sh && sy + y < bm.bmHeight; y++)
                for (x = 0; x < sw && sx + x < bm.bmWidth; x++)
                    if (p.y + y >= 0 && p.y + y < h && p.x + x >= 0 && p.x + x < w &&
                        (int)(all[(sy + y) * bm.bmWidth + sx + x] >> 24) >= min)
                        mask[(p.y + y) * w + p.x + x] = 1;
            if ((rgn = changed_region(mask, none, w, h))) {
                if (debug) {  /* #36: the region as built, and spot checks at the feather's notch */
                    DWORD sz = GetRegionData(rgn, 0, NULL);
                    TRACE("alpha region: %lu bytes, mask(12,60)=%lu (14,60)=%lu, in rgn: %d %d\n", sz,
                          mask[60 * w + 12], mask[60 * w + 14], PtInRegion(rgn, 12, 60), PtInRegion(rgn, 14, 60));
                }
                if (SetWindowRgn(root, rgn, TRUE)) {
                    RECT cr;
                    POINT o = {0, 0};
                    int edge = 0;
                    /* #36: the card is premultiplied and blended over the window's
                     * white background, so its soft edge (alpha min..254) came out
                     * whitish next to the shape's border. Inside the shape such a
                     * pixel stands for the card alone: paint its own colour. */
                    if (!GetEnvironmentVariableA("DLLMGR36_NO_EDGE_FIX", NULL, 0))
                        for (y = 0; y < sh && sy + y < bm.bmHeight; y++)
                            for (x = 0; x < sw && sx + x < bm.bmWidth; x++) {
                                DWORD c = all[(sy + y) * bm.bmWidth + sx + x];
                                int a = c >> 24;
                                if (a >= min && a < 255) {
                                    int r = ((c >> 16) & 0xff) * 255 / a, g = ((c >> 8) & 0xff) * 255 / a, b = (c & 0xff) * 255 / a;
                                    SetPixel(dst, dx + x, dy + y, RGB(r > 255 ? 255 : r, g > 255 ? 255 : g, b > 255 ? 255 : b));
                                    edge++;
                                }
                            }
                    TRACE("alpha shape: %d soft edge pixels painted opaque\n", edge);
                    GetClientRect(root, &cr);
                    ClientToScreen(root, &o);
                    TRACE("alpha shape: %p from the card %dx%d at %ld,%ld, alpha >= %d; window %ld,%ld %ldx%ld client at %ld,%ld style %08lx\n",
                          (void *)root, sw, sh, p.x, p.y, min, wr.left, wr.top, (long)w, (long)h, o.x, o.y,
                          GetWindowLongW(root, GWL_STYLE));
                }
                else DeleteObject(rgn);
            }
        }
    }
    HeapFree(GetProcessHeap(), 0, mask);
    HeapFree(GetProcessHeap(), 0, none);
    HeapFree(GetProcessHeap(), 0, all);
    return ret;
}
#endif

/* Runs in the window's own thread, from the ReleaseDC and message hooks:
 * winex11 applies a window region only there, and Photoshop's main thread
 * does not pump messages while the splash is up (it paints it directly), so
 * neither timers nor another thread can do it. At most every 20 ms. */
static void shape_tick(void)
{
    LONG left = 0;
    for (int i = 0; i < 4; i++) {
        struct shape *s = &shapes[i];
        int w = s->rect.right - s->rect.left, h = s->rect.bottom - s->rect.top;
        DWORD *was = NULL, *now = NULL;
        DPI_AWARENESS_CONTEXT old_ctx;
        RECT where;
        HDC dc;
        LONG changed = 0;

        if (!s->hwnd || GetWindowThreadProcessId(s->hwnd, NULL) != GetCurrentThreadId()) {
            if (s->hwnd) left++;
            continue;
        }
        if (GetTickCount() - s->when < 20) { left++; continue; }
        s->when = GetTickCount();
        if (!IsWindowVisible(s->hwnd) || ++s->tries > 300) { shape_release(s); continue; }
        old_ctx = physical_begin();
        if (GetWindowRect(s->hwnd, &where) && EqualRect(&where, &s->rect) &&
            (dc = GetDCEx(s->hwnd, NULL, DCX_WINDOW | DCX_CACHE))) {
            now = read_bits(dc, 0, 0, w, h);
            real_release_dc(s->hwnd, dc);
            was = read_bits(s->mem, 0, 0, w, h);
        }
        if (!now || !was) {
            shape_release(s);
        } else {
            for (LONG k = 0; k < (LONG)w * h; k++) changed += (now[k] & 0xffffff) != (was[k] & 0xffffff);
            TRACE("shape tick hwnd=%p try=%d painted=%ld/%ld\n", (void *)s->hwnd, s->tries, changed, (LONG)w * h);
            /* Photoshop fills the whole card at once and later only redraws
             * text inside it: shape as soon as a real part is painted */
            if (changed > (LONG)w * h / 10) {
                /* a splash-like window leaves its outer edge untouched (the
                 * margin reaches the window border); palettes and dialogs
                 * paint their own frame there, so they are never cut */
                LONG edge = 0, edge_changed = 0;
                for (int x = 0; x < w; x++) {
                    edge += 2;
                    edge_changed += (now[x] & 0xffffff) != (was[x] & 0xffffff);
                    edge_changed += (now[(h - 1) * w + x] & 0xffffff) != (was[(h - 1) * w + x] & 0xffffff);
                }
                for (int y = 1; y < h - 1; y++) {
                    edge += 2;
                    edge_changed += (now[y * w] & 0xffffff) != (was[y * w] & 0xffffff);
                    edge_changed += (now[y * w + w - 1] & 0xffffff) != (was[y * w + w - 1] & 0xffffff);
                }
                TRACE("shape edge hwnd=%p changed=%ld/%ld\n", (void *)s->hwnd, edge_changed, edge);
                if (changed <= (LONG)w * h * 97 / 100 && edge_changed * 2 < edge) {
                    HRGN rgn = changed_region(now, was, w, h);
                    TRACE("shape hwnd=%p %dx%d painted=%ld%%\n", (void *)s->hwnd, w, h, changed * 100 / ((LONG)w * h));
                    if (rgn && !SetWindowRgn(s->hwnd, rgn, TRUE)) DeleteObject(rgn);
                    else if (rgn) splash = s->hwnd;
                }
                shape_release(s);
            } else {
                s->last = changed;
                left++;
            }
        }
        HeapFree(GetProcessHeap(), 0, now);
        HeapFree(GetProcessHeap(), 0, was);
        physical_end(old_ctx);
    }
    shape_pending = left;
}

/* Keep the capture for shaping instead of dropping it; TRUE if taken over. */
static BOOL shape_later(struct capture *c, const RECT *now)
{
    struct shape *s = NULL;
    LONG style = GetWindowLongW(c->hwnd, GWL_STYLE);
    TRACE("shape check hwnd=%p style=%08lx now=%ld,%ld-%ld,%ld cap=%ld,%ld-%ld,%ld\n", (void *)c->hwnd, style,
          now->left, now->top, now->right, now->bottom, c->rect.left, c->rect.top, c->rect.right, c->rect.bottom);
    if (GetEnvironmentVariableA("DLLMGR27_NO_SHAPE", NULL, 0) || (style & (WS_CHILD | WS_CAPTION)) == WS_CAPTION ||
        (GetWindowLongW(c->hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW) ||
        (style & WS_CHILD) || !EqualRect(now, &c->rect) || c->rect.right - c->rect.left < 200 ||
        c->rect.bottom - c->rect.top < 100)
        return FALSE;
    for (int i = 0; i < 4 && !s; i++) if (!shapes[i].hwnd) s = &shapes[i];
    if (!s || !real_release_dc) return FALSE;
    TRACE("shape candidate hwnd=%p\n", (void *)c->hwnd);
    s->hwnd = c->hwnd; s->mem = c->mem; s->bitmap = c->bitmap; s->old = c->old; s->rect = c->rect;
    s->tries = 0; s->last = -1; s->when = 0;
    c->hwnd = NULL;
    shape_pending = 1;
    return TRUE;
}

static void present_capture(HWND hwnd)
{
    struct capture *c = find_capture(hwnd);
    RECT now;
    HDC dc;

    if (!c) return;
    TRACE("present hwnd=%p\n", (void *)hwnd);
    {
        DPI_AWARENESS_CONTEXT old_ctx = physical_begin();
        if (GetWindowRect(hwnd, &now) && (dc = GetDCEx(hwnd, NULL, DCX_WINDOW | DCX_CACHE))) {
            BitBlt(dc, c->rect.left - now.left, c->rect.top - now.top, c->rect.right - c->rect.left,
                   c->rect.bottom - c->rect.top, c->mem, 0, 0, SRCCOPY);
            ReleaseDC(hwnd, dc);
            GdiFlush();
            if (shape_later(c, &now)) {
                physical_end(old_ctx);
                return;
            }
        }
        physical_end(old_ctx);
    }
    release_capture(c);
}

static BOOL top_level_hidden(HWND hwnd)
{
    return !(GetWindowLongW(hwnd, GWL_STYLE) & WS_CHILD) && !IsWindowVisible(hwnd);
}


/* Photoshop paints the splash text directly (GetDC/ReleaseDC) while its main
 * thread does not pump messages, so ReleaseDC is the reliable moment in the
 * window's own thread. Import slots of user32!ReleaseDC are replaced in every
 * module, also in ones loaded later (LdrRegisterDllNotification). */

static int WINAPI release_dc_hook(HWND hwnd, HDC dc)
{
    int ret = real_release_dc(hwnd, dc);
    if (shape_pending) shape_tick();
    return ret;
}

static void hook_module_release_dc(HMODULE module)
{
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    IMAGE_IMPORT_DESCRIPTOR *desc;

    if (module == self || !dir->VirtualAddress || !real_release_dc) return;
    for (desc = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir->VirtualAddress); desc->Name; desc++) {
        IMAGE_THUNK_DATA *slot = (IMAGE_THUNK_DATA *)(base + desc->FirstThunk);
        if (lstrcmpiA((char *)base + desc->Name, "user32.dll") && lstrcmpiA((char *)base + desc->Name, "msimg32.dll"))
            continue;
        for (; slot->u1.Function; slot++) {
            DWORD protect;
#ifdef DLLMGR27_CAPTIONLESS_ONLY
            if (real_alpha_blend && slot->u1.Function == (ULONG_PTR)real_alpha_blend) {
                if (!VirtualProtect(&slot->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) continue;
                slot->u1.Function = (ULONG_PTR)alpha_blend_hook;
                VirtualProtect(&slot->u1.Function, sizeof(void *), protect, &protect);
                continue;
            }
#endif
            if (slot->u1.Function != (ULONG_PTR)real_release_dc) continue;
            if (!VirtualProtect(&slot->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) continue;
            slot->u1.Function = (ULONG_PTR)release_dc_hook;
            VirtualProtect(&slot->u1.Function, sizeof(void *), protect, &protect);
            if (debug) {
                char name[MAX_PATH] = "";
                GetModuleFileNameA(module, name, sizeof(name));
                TRACE("ReleaseDC hooked in %s\n", name);
            }
        }
    }
}

/* Photoshop.exe takes user32 through its delay-import table (resolved on first
 * call, after our DllMain): point that slot at the hook directly. */
static void hook_delay_release_dc(HMODULE module)
{
    typedef struct { DWORD attrs, name, hmod, iat, nt, bound, unload, stamp; } delay_desc;
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT];
    delay_desc *d;
#define DELAY_PTR(d, v) ((d)->attrs & 1 ? base + (v) : (BYTE *)(ULONG_PTR)(v))
    if (!dir->VirtualAddress || !real_release_dc) return;
    for (d = (delay_desc *)(base + dir->VirtualAddress); d->name; d++) {
        IMAGE_THUNK_DATA *names = (IMAGE_THUNK_DATA *)DELAY_PTR(d, d->nt), *slots = (IMAGE_THUNK_DATA *)DELAY_PTR(d, d->iat);
        const char *dll = (char *)DELAY_PTR(d, d->name), *want = "ReleaseDC";
        void *hook = release_dc_hook;
        if (lstrcmpiA(dll, "user32.dll")) {
#ifdef DLLMGR27_CAPTIONLESS_ONLY
            if (lstrcmpiA(dll, "msimg32.dll") || !real_alpha_blend) continue;
            want = "AlphaBlend";
            hook = alpha_blend_hook;
#else
            continue;
#endif
        }
        for (; names->u1.AddressOfData; names++, slots++) {
            DWORD protect;
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal) ||
                strcmp((char *)((IMAGE_IMPORT_BY_NAME *)DELAY_PTR(d, names->u1.AddressOfData))->Name, want))
                continue;
            if (!VirtualProtect(&slots->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) continue;
            slots->u1.Function = (ULONG_PTR)hook;
            VirtualProtect(&slots->u1.Function, sizeof(void *), protect, &protect);
            TRACE("%s hooked in the delay imports of %p\n", want, (void *)module);
        }
    }
#undef DELAY_PTR
}

#ifdef DLLMGR27_CAPTIONLESS_ONLY
/* #62: CoolType (Photoshop's text engine) falls back to the PostScript fonts
 * MyriadPro-Regular, Myriad-Roman and TimesNewRomanPSMT (then ArialMT). A
 * Windows system always has the last two; a Wine prefix has none of them, so
 * the default text style gets a NULL font, Photoshop throws an internal
 * assertion (SLOCoolTypeFont.cpp:1633) and, once its preferences exist, a
 * start with a document dies with "hardware or system error". The names are
 * pointed at fonts every Wine prefix can resolve instead (Liberation, which
 * matches Arial / Times New Roman metrics, else Wine's own Tahoma).
 * DLLMGR62_NO_FONT_FIX=1 turns it off. */
static int CALLBACK font_family_found(const LOGFONTA *lf, const TEXTMETRICA *tm, DWORD type, LPARAM found)
{
    *(int *)found = 1;
    return 0;
}

static int font_family_exists(const char *family)
{
    LOGFONTA lf;
    int found = 0;
    HDC dc = GetDC(NULL);
    memset(&lf, 0, sizeof(lf));
    lf.lfCharSet = DEFAULT_CHARSET;
    lstrcpynA(lf.lfFaceName, family, LF_FACESIZE);
    EnumFontFamiliesExA(dc, &lf, (FONTENUMPROCA)font_family_found, (LPARAM)&found, 0);
    ReleaseDC(NULL, dc);
    return found;
}

static void replace_font_name(BYTE *start, SIZE_T size, const char *from, const char *to)
{
    SIZE_T from_len = strlen(from) + 1, to_len = strlen(to) + 1, i;
    if (to_len > from_len) return;
    for (i = 0; i + from_len <= size; i++) {
        DWORD protect;
        if (memcmp(start + i, from, from_len) || (i && start[i - 1])) continue;
        if (!VirtualProtect(start + i, from_len, PAGE_READWRITE, &protect)) continue;
        memset(start + i, 0, from_len);
        memcpy(start + i, to, to_len);
        VirtualProtect(start + i, from_len, protect, &protect);
        TRACE("CoolType default font %s -> %s\n", from, to);
    }
}

static void cooltype_default_fonts(HMODULE module)
{
    char name[MAX_PATH] = "";
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt;
    IMAGE_SECTION_HEADER *sec;
    const char *sans, *serif;
    int len, i;

    len = GetModuleFileNameA(module, name, sizeof(name));
    if (len < 12 || lstrcmpiA(name + len - 12, "CoolType.dll") || GetEnvironmentVariableA("DLLMGR62_NO_FONT_FIX", NULL, 0))
        return;
    sans = font_family_exists("Liberation Sans") ? "LiberationSans" : "WineTahoma";
    serif = font_family_exists("Liberation Serif") ? "LiberationSerif" : sans;
    nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    sec = IMAGE_FIRST_SECTION(nt);
    for (i = 0; i < nt->FileHeader.NumberOfSections; i++, sec++) {
        BYTE *start = base + sec->VirtualAddress;
        SIZE_T size = min(sec->Misc.VirtualSize, sec->SizeOfRawData);
        if (sec->Characteristics & IMAGE_SCN_MEM_EXECUTE || !(sec->Characteristics & IMAGE_SCN_MEM_READ)) continue;
        replace_font_name(start, size, "MyriadPro-Regular", sans);
        replace_font_name(start, size, "Myriad-Roman", strlen(sans) < 12 ? sans : "WineTahoma");
        replace_font_name(start, size, "TimesNewRomanPSMT", serif);
    }
}
#endif

typedef struct { ULONG flags; const UNICODE_STRING *full, *base; void *dll; ULONG size; } dll_loaded;
static void CALLBACK on_dll(ULONG reason, const dll_loaded *data, void *context)
{
    if (reason == 1 /* LDR_DLL_NOTIFICATION_REASON_LOADED */) {
        hook_module_release_dc((HMODULE)data->dll);
#ifdef DLLMGR27_CAPTIONLESS_ONLY
        cooltype_default_fonts((HMODULE)data->dll);
#endif
    }
}

static void hook_release_dc(void)
{
    HMODULE modules[512];
    DWORD bytes = 0;
    void *cookie;
    NTSTATUS (NTAPI *reg)(ULONG, void *, void *, void **) =
        (void *)GetProcAddress(GetModuleHandleA("ntdll.dll"), "LdrRegisterDllNotification");
    real_release_dc = (void *)GetProcAddress(GetModuleHandleA("user32.dll"), "ReleaseDC");
#ifdef DLLMGR27_CAPTIONLESS_ONLY
    real_alpha_blend = (void *)GetProcAddress(LoadLibraryA("msimg32.dll"), "AlphaBlend");
#endif
    if (!real_release_dc || GetEnvironmentVariableA("DLLMGR27_NO_SHAPE", NULL, 0)) return;
    if (K32EnumProcessModules(GetCurrentProcess(), modules, sizeof(modules), &bytes))
        for (DWORD i = 0; i < bytes / sizeof(HMODULE) && i < 512; i++) hook_module_release_dc(modules[i]);
    hook_delay_release_dc(GetModuleHandleW(NULL));
    if (reg) reg(0, on_dll, NULL, &cookie);
}

#ifdef DLLMGR27_CAPTIONLESS_ONLY
/* #45: a new menu window is on screen (black under a compositing WM) before
 * Photoshop has painted it. It is shown fully transparent instead and made
 * opaque as soon as its first WM_PAINT has returned (or after 250 ms at the
 * latest, from a helper thread), so the black frame never reaches the screen.
 * DLLMGR45_NO_FADE=1 turns it off. */
static HWND fading[8];

static DWORD WINAPI reveal_later(void *arg)
{
    HWND hwnd = arg;
    int i;
    Sleep(250);
    for (i = 0; i < 8; i++)
        if (InterlockedCompareExchangePointer((void **)&fading[i], NULL, hwnd) == hwnd && IsWindow(hwnd)) {
            SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA);
            TRACE("menu %p revealed by timeout\n", (void *)hwnd);
        }
    return 0;
}

static void fade_in_begin(HWND hwnd)
{
    char cls[16] = "";
    int i;
    HANDLE t;
    if (!GetClassNameA(hwnd, cls, sizeof(cls)) || strcmp(cls, "#32768") ||
        GetEnvironmentVariableA("DLLMGR45_NO_FADE", NULL, 0))
        return;
    for (i = 0; i < 8; i++)
        if (!InterlockedCompareExchangePointer((void **)&fading[i], hwnd, NULL)) break;
    if (i == 8) return;
    SetWindowLongW(hwnd, GWL_EXSTYLE, GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED);
    SetLayeredWindowAttributes(hwnd, 0, 0, LWA_ALPHA);
    if ((t = CreateThread(NULL, 0, reveal_later, hwnd, 0, NULL))) CloseHandle(t);
}

static void fade_in_painted(HWND hwnd)
{
    int i;
    for (i = 0; i < 8; i++)
        if (fading[i] == hwnd && InterlockedCompareExchangePointer((void **)&fading[i], NULL, hwnd) == hwnd) {
            SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA);
            TRACE("menu %p revealed after its first paint\n", (void *)hwnd);
        }
}
#else
static void fade_in_begin(HWND hwnd) {}
static void fade_in_painted(HWND hwnd) {}
#endif

/* #71: the last few UI events (top-level windows shown, buttons clicked),
 * printed by exit_report: an "orderly exit" then says which dialog and
 * button led to it (e.g. "Quit" in "Adobe Activation"). */
#define RECENT 8
static struct { DWORD tick; char text[200]; } recent[RECENT];
static LONG recent_next;

static void remember(const char *what, HWND hwnd, HWND parent)
{
    WCHAR title[64] = L"", ptitle[64] = L"";
    char t[100], pt[100];
    LONG slot = InterlockedIncrement(&recent_next) % RECENT;
    GetWindowTextW(hwnd, title, ARRAYSIZE(title));
    if (parent) GetWindowTextW(parent, ptitle, ARRAYSIZE(ptitle));
    WideCharToMultiByte(CP_UTF8, 0, title, -1, t, sizeof(t), NULL, NULL);
    WideCharToMultiByte(CP_UTF8, 0, ptitle, -1, pt, sizeof(pt), NULL, NULL);
    recent[slot].tick = GetTickCount();
    if (parent) snprintf(recent[slot].text, sizeof(recent[slot].text), "%s \"%s\" in \"%s\"", what, t, pt);
    else snprintf(recent[slot].text, sizeof(recent[slot].text), "%s \"%s\"", what, t);
}

static LRESULT CALLBACK before(int code, WPARAM wparam, LPARAM lparam)
{
    const CWPSTRUCT *m = (const CWPSTRUCT *)lparam;
    if (code == HC_ACTION && shape_pending) shape_tick();
    if (code == HC_ACTION && m->message == WM_WINDOWPOSCHANGING &&
        (((WINDOWPOS *)m->lParam)->flags & SWP_SHOWWINDOW) && top_level_hidden(m->hwnd)) {
        adopt_early(m->hwnd, (WINDOWPOS *)m->lParam);
        fade_in_begin(m->hwnd);
        /* the adopted splash gets no snapshot and no shape: under the private
         * runtime the shape is computed from a half-painted window (the WM
         * maps it late) and cuts the card, and a snapshot is stale content;
         * a plain white margin is the safe interim (owner, 2026-11-09) */
        if (m->hwnd != adopted) capture_under(m->hwnd, (WINDOWPOS *)m->lParam);
    }
    return CallNextHookEx(NULL, code, wparam, lparam);
}

static LRESULT CALLBACK after(int code, WPARAM wparam, LPARAM lparam)
{
    const CWPRETSTRUCT *m = (const CWPRETSTRUCT *)lparam;
    if (debug && code == HC_ACTION && m->message == WM_GETMINMAXINFO) {
        /* diagnostic only (#35): what minimum size a window asks for */
        const MINMAXINFO *mm = (const MINMAXINFO *)m->lParam;
        char cls[64] = "";
        GetClassNameA(m->hwnd, cls, sizeof(cls));
        TRACE("minmax hwnd=%p class=%s min=%ldx%ld max=%ldx%ld\n", (void *)m->hwnd, cls,
              mm->ptMinTrackSize.x, mm->ptMinTrackSize.y, mm->ptMaxTrackSize.x, mm->ptMaxTrackSize.y);
    }
    if (code == HC_ACTION && m->message == WM_COMMAND && HIWORD(m->wParam) == BN_CLICKED && m->lParam)
        remember("clicked", (HWND)m->lParam, m->hwnd);
    if (code == HC_ACTION && m->message == WM_WINDOWPOSCHANGED &&
        (((WINDOWPOS *)m->lParam)->flags & SWP_SHOWWINDOW)) {
        if (!(GetWindowLongW(m->hwnd, GWL_STYLE) & WS_CHILD) && GetWindowTextLengthW(m->hwnd))
            remember("shown", m->hwnd, NULL);
        present_capture(m->hwnd);
        adopt_owner_shown(m->hwnd);
    }
    if (code == HC_ACTION && (m->message == WM_PAINT || m->message == WM_PRINTCLIENT)) fade_in_painted(m->hwnd);
    return CallNextHookEx(NULL, code, wparam, lparam);
}

/* Message timeline (#47, DLLMGR_MSGLOG=seconds, off by default): a
 * WH_GETMESSAGE hook records every message the thread removes from its queue
 * (time in 0.1 ms, message, window, wParam) once %TEMP%\dllmgr-msglog-go
 * exists, for `seconds`; then %TEMP%\dllmgr-msglog-<pid>.txt is written.
 * Same proxy on Wine and Windows, so the two timelines can be compared. */
#define MSGLOG_MAX 20000
static struct { DWORD t; UINT msg; DWORD hwnd; DWORD wparam; DWORD tid; } msglog[MSGLOG_MAX];
static LONG msglog_n;
static volatile LONG msglog_on;
static LARGE_INTEGER msglog_freq, msglog_start;

static LRESULT CALLBACK msglog_hook(int code, WPARAM wparam, LPARAM lparam)
{
    if (code == HC_ACTION && wparam == PM_REMOVE && msglog_on) {
        const MSG *m = (const MSG *)lparam;
        LONG i = InterlockedIncrement(&msglog_n) - 1;
        if (i < MSGLOG_MAX) {
            LARGE_INTEGER now;
            QueryPerformanceCounter(&now);
            msglog[i].t = (DWORD)((double)(now.QuadPart - msglog_start.QuadPart) * 10000.0 / (double)msglog_freq.QuadPart);  /* no 64-bit division: it would pull in libgcc_s */
            msglog[i].msg = m->message;
            msglog[i].hwnd = (DWORD)(ULONG_PTR)m->hwnd;
            msglog[i].wparam = (DWORD)m->wParam;
            msglog[i].tid = GetCurrentThreadId();
        }
    }
    return CallNextHookEx(NULL, code, wparam, lparam);
}

static DWORD WINAPI msglog_writer(void *arg)
{
    char value[16], path[MAX_PATH], go[MAX_PATH], line[128];
    DWORD got;
    LONG i, n;
    HANDLE file;
    GetEnvironmentVariableA("DLLMGR_MSGLOG", value, sizeof(value));
    GetTempPathA(sizeof(go) - 40, go);
    lstrcpyA(path, go);
    wsprintfA(line, "%sdllmgr-msglog-alive-%lu", go, GetCurrentProcessId());  /* shows that the proxy loaded */
    CloseHandle(CreateFileA(line, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL));
    lstrcatA(go, "dllmgr-msglog-go");
    while (GetFileAttributesA(go) == INVALID_FILE_ATTRIBUTES) Sleep(20);
    QueryPerformanceFrequency(&msglog_freq);
    QueryPerformanceCounter(&msglog_start);
    msglog_on = 1;
    Sleep((atoi(value) > 0 ? atoi(value) : 5) * 1000);
    msglog_on = 0;
    Sleep(50);
    n = msglog_n < MSGLOG_MAX ? msglog_n : MSGLOG_MAX;
    wsprintfA(path + lstrlenA(path), "dllmgr-msglog-%lu.txt", GetCurrentProcessId());
    file = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, 0, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    for (i = 0; i < n; i++) {
        wsprintfA(line, "%lu.%lu %04lx %04x %08lx %lx\r\n", msglog[i].t / 10, msglog[i].t % 10, msglog[i].tid,
                  msglog[i].msg, msglog[i].hwnd, msglog[i].wparam);
        WriteFile(file, line, lstrlenA(line), &got, NULL);
    }
    CloseHandle(file);
    return 0;
}

static void msglog_thread_hook(void)
{
    if (GetEnvironmentVariableA("DLLMGR_MSGLOG", NULL, 0))
        SetWindowsHookExW(WH_GETMESSAGE, msglog_hook, self, GetCurrentThreadId());
}


static void hook_thread(void)
{
    DWORD tid = GetCurrentThreadId();
    TRACE("hook thread %04lx\n", tid);
    SetWindowsHookExW(WH_CALLWNDPROC, before, self, tid);
    SetWindowsHookExW(WH_CALLWNDPROCRET, after, self, tid);
    msglog_thread_hook();
}

/* Trampoline (issue 27, docs/tasks/27-every-launch-path.md): a stock-Wine
 * start of the exe relaunches itself through the private runtime when a
 * companion file "<this dll name>.dllmgr" exists next to the proxy. Its one
 * line (UTF-8) is a Windows command-line prefix whose first, double-quoted
 * token is the launcher, e.g.
 *   "Z:\home\u\dllmgr\dllmgr" run faststone --
 * The exe's own arguments are appended unchanged. Facts it relies on: Wine
 * starts Unix programs with CreateProcessW but gives no waitable handle and
 * passes only the original Unix environment, so the private process reports
 * success by setting a named event instead (see DllMain). */
#define TRAMP_EVENT L"dllmgr27-trampoline"
static BOOL tramp_pending, idle;
static HHOOK cbt_hook;

static WCHAR *read_companion(void)
{
    WCHAR path[MAX_PATH + 16], *dot, *text = NULL;
    char buf[4096];
    DWORD got = 0, i;
    HANDLE file;
    int len;

    if (!GetModuleFileNameW(self, path, MAX_PATH) || !(dot = wcsrchr(path, '.'))) return NULL;
    lstrcpyW(dot, L".dllmgr");
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (file == INVALID_HANDLE_VALUE) return NULL;
    if (ReadFile(file, buf, sizeof(buf) - 1, &got, NULL)) {
        for (i = 0; i < got && buf[i] != '\r' && buf[i] != '\n'; i++);
        got = i;
    } else got = 0;
    CloseHandle(file);
    if (got && buf[0] == '"' && (len = MultiByteToWideChar(CP_UTF8, 0, buf, got, NULL, 0)) > 0 &&
        (text = HeapAlloc(GetProcessHeap(), 0, (len + 1) * sizeof(WCHAR)))) {
        MultiByteToWideChar(CP_UTF8, 0, buf, got, text, len);
        text[len] = 0;
    }
    return text;
}

/* Arguments of the current process: GetCommandLineW minus argv[0]. */
static const WCHAR *own_arguments(void)
{
    const WCHAR *p = GetCommandLineW();
    if (*p == '"') {
        for (p++; *p && *p != '"'; p++);
        if (*p) p++;
    } else while (*p && *p != ' ' && *p != '\t') p++;
    while (*p == ' ' || *p == '\t') p++;
    return p;
}

/* #51: Photoshop CS2 keeps one instance with the named mutex "PS3.0.5WIN"
 * (created in WinMain before Photoshop.dll); a second instance that finds it
 * exits at once. The private instance only tells us it is up once its own
 * copy of this proxy is loaded, which happens late on some systems (it is
 * delay-loaded), so it could find our mutex first and quit, and we stayed on
 * stock Wine. Close our handles to the single-instance mutexes before
 * starting the launcher; the private instance then creates them, and seeing
 * the mutex again also tells us it took over. Returns how many were closed. */
static const WCHAR *const instance_mutexes[] = {L"PS3.0.5WIN", L"goingDownForeverPS4.0"};

static int close_instance_mutexes(void)
{
    typedef NTSTATUS (WINAPI *query_object_fn)(HANDLE, int, void *, ULONG, ULONG *);
    query_object_fn query = (query_object_fn)GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtQueryObject");
    union { UNICODE_STRING name; BYTE buf[1024]; } info;
    ULONG i, j, len, closed = 0;
    HANDLE probe;

    if (!query || GetEnvironmentVariableA("DLLMGR51_NO_MUTEX", NULL, 0)) return 0;
    for (j = 0; j < ARRAYSIZE(instance_mutexes); j++) {  /* only when it exists at all */
        if (!(probe = OpenMutexW(SYNCHRONIZE, FALSE, instance_mutexes[j]))) continue;
        CloseHandle(probe);
        for (i = 4; i < 0x10000; i += 4) {
            /* 1 = ObjectNameInformation */
            if (query((HANDLE)(ULONG_PTR)i, 1, &info, sizeof(info) - sizeof(WCHAR), &len) < 0 || !info.name.Buffer) continue;
            len = info.name.Length / sizeof(WCHAR);
            if (len >= (ULONG)lstrlenW(instance_mutexes[j]) &&
                !lstrcmpW(info.name.Buffer + len - lstrlenW(instance_mutexes[j]), instance_mutexes[j]) &&
                (len == (ULONG)lstrlenW(instance_mutexes[j]) || info.name.Buffer[len - lstrlenW(instance_mutexes[j]) - 1] == '\\')) {
                CloseHandle((HANDLE)(ULONG_PTR)i);
                closed++;
                TRACE("trampoline: closed single-instance mutex %ls (handle %#lx)\n", instance_mutexes[j], i);
            }
        }
    }
    return closed;
}

/* #51 (owner machine, experiments/photoshop-cs2-51/owner-machine): the
 * trampoline can run after Photoshop's main window (class "Photoshop")
 * exists; the private instance then finds it with FindWindow and exits 0 in
 * 0.3 s, before it could signal. Move this process's windows of the
 * application's main class under a hidden window of ours while we wait:
 * FindWindow only sees top-level and message-only windows (message-only does
 * not help, Wine and Windows both find those). Give them back if the private
 * runtime does not take over. */
#define TRAMP_MAX_HIDDEN 16
static HWND tramp_hidden[TRAMP_MAX_HIDDEN], tramp_holder;
static int tramp_hidden_count;

static BOOL CALLBACK hide_main_window(HWND hwnd, LPARAM lparam)
{
    char cls[64];
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == GetCurrentProcessId() && tramp_hidden_count < TRAMP_MAX_HIDDEN &&
        GetClassNameA(hwnd, cls, sizeof(cls)) && !lstrcmpA(cls, "Photoshop") && hwnd != tramp_holder &&
        (tramp_holder || (tramp_holder = CreateWindowExA(0, "STATIC", "dllmgr51", WS_POPUP, 0, 0, 0, 0,
                                                         NULL, NULL, NULL, NULL))) &&
        SetParent(hwnd, tramp_holder)) {
        tramp_hidden[tramp_hidden_count++] = hwnd;
        TRACE("trampoline: main window %p moved under %p\n", (void *)hwnd, (void *)tramp_holder);
    }
    return TRUE;
}

static void restore_main_windows(void)
{
    while (tramp_hidden_count) {
        HWND hwnd = tramp_hidden[--tramp_hidden_count];
        SetParent(hwnd, NULL);
        TRACE("trampoline: main window %p restored\n", (void *)hwnd);
    }
    if (tramp_holder) DestroyWindow(tramp_holder);
    tramp_holder = NULL;
}

/* The private instance owns the single-instance mutex again: it took over. */
static BOOL instance_mutex_back(void)
{
    HANDLE probe = OpenMutexW(SYNCHRONIZE, FALSE, instance_mutexes[0]);
    if (!probe) return FALSE;
    CloseHandle(probe);
    return TRUE;
}

static void trampoline(void)
{
    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    WCHAR *prefix = read_companion(), *app = NULL, *cmd = NULL, *end;
    const WCHAR *args = own_arguments();
    char wait_text[16] = "";
    DWORD wait = 15000, n, waited, poll = 100;
    HANDLE event = NULL;
    int mutexes;

    if (!prefix || !(end = wcschr(prefix + 1, '"'))) goto done;
    n = end - prefix - 1;
    app = HeapAlloc(GetProcessHeap(), 0, (n + 1) * sizeof(WCHAR));
    cmd = HeapAlloc(GetProcessHeap(), 0, (lstrlenW(prefix) + lstrlenW(args) + 2) * sizeof(WCHAR));
    if (!app || !cmd) goto done;
    memcpy(app, prefix + 1, n * sizeof(WCHAR));
    app[n] = 0;
    lstrcpyW(cmd, prefix);
    if (*args) {
        lstrcatW(cmd, L" ");
        lstrcatW(cmd, args);
    }
    if (GetEnvironmentVariableA("DLLMGR27_TRAMP_WAIT", wait_text, sizeof(wait_text))) wait = atoi(wait_text);
    if (!(event = CreateEventW(NULL, TRUE, FALSE, TRAMP_EVENT))) goto done;
    ResetEvent(event);
    mutexes = close_instance_mutexes();
    if (!GetEnvironmentVariableA("DLLMGR51_NO_HIDE", NULL, 0)) EnumWindows(hide_main_window, 0);
    if (!CreateProcessW(app, cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        TRACE("trampoline: cannot start launcher (error %lu), staying on stock Wine\n", GetLastError());
        restore_main_windows();
        goto done;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    TRACE("trampoline: started %ls, waiting %lu ms\n", cmd, wait);
    if (GetEnvironmentVariableA("DLLMGR51_POLL_MS", wait_text, sizeof(wait_text)))  /* test switch: slow mutex polling */
        poll = atoi(wait_text);
    for (waited = 0; waited < wait; waited += poll) {
        if (WaitForSingleObject(event, poll) == WAIT_OBJECT_0) {
            TRACE("trampoline: private runtime took over, exiting\n");
            ExitProcess(0);
        }
        if (mutexes && instance_mutex_back()) {
            TRACE("trampoline: private runtime holds the single-instance mutex, exiting\n");
            ExitProcess(0);
        }
    }
    restore_main_windows();
    TRACE("trampoline: no signal from the private runtime, staying on stock Wine\n");
done:
    if (event) CloseHandle(event);
    HeapFree(GetProcessHeap(), 0, prefix);
    HeapFree(GetProcessHeap(), 0, app);
    HeapFree(GetProcessHeap(), 0, cmd);
}

/* Before the first window of the process exists (Delphi creates its hidden
 * application window first): relaunch, so nothing is shown twice. */
static LRESULT CALLBACK cbt(int code, WPARAM wparam, LPARAM lparam)
{
    char late[16];
    /* DLLMGR51_LATE=N: test switch, as if this proxy loaded after the
     * application's main window existed (owner's system): skip until a
     * window of class "Photoshop" exists */
    if (code == HCBT_CREATEWND && tramp_pending && GetEnvironmentVariableA("DLLMGR51_LATE", late, sizeof(late)) &&
        !FindWindowA("Photoshop", NULL))
        return CallNextHookEx(NULL, code, wparam, lparam);
    if (code == HCBT_CREATEWND && tramp_pending) {
        tramp_pending = FALSE;
        UnhookWindowsHookEx(cbt_hook);
        trampoline();
    }
    return CallNextHookEx(NULL, code, wparam, lparam);
}

/* #71: when the process ends through ExitProcess, the exiting thread runs
 * our DLL_PROCESS_DETACH: report who called it (return addresses as
 * module+offset) and which of the process's windows were still visible, on
 * stderr, which `dllmgr run` keeps in .dllmgr/runs/. One line per item,
 * prefix "dllmgr71:". Costs nothing while the program runs.
 * DLLMGR71_OFF=1 turns it off. */
static BOOL CALLBACK exit_window(HWND hwnd, LPARAM lparam)
{
    DWORD pid = 0;
    WCHAR title[128];
    char utf8[400];
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid != GetCurrentProcessId() || !IsWindowVisible(hwnd)) return TRUE;
    if (!GetWindowTextW(hwnd, title, ARRAYSIZE(title))) return TRUE;
    WideCharToMultiByte(CP_UTF8, 0, title, -1, utf8, sizeof(utf8), NULL, NULL);
    fprintf(stderr, "dllmgr71: visible window \"%s\"%s\n", utf8, hwnd == GetForegroundWindow() ? " (foreground)" : "");
    (*(int *)lparam)++;
    return *(int *)lparam < 12;
}

static void exit_report(void)
{
    void *frames[24];
    USHORT n = RtlCaptureStackBackTrace(1, ARRAYSIZE(frames), frames, NULL), i;
    int windows = 0;
    fprintf(stderr, "dllmgr71: process exit (ExitProcess), thread %04lx, callers:", GetCurrentThreadId());
    for (i = 0; i < n; i++) {
        HMODULE module = NULL;
        char name[MAX_PATH] = "?", *base;
        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                               frames[i], &module) && module)
            GetModuleFileNameA(module, name, sizeof(name));
        base = strrchr(name, '\\') ? strrchr(name, '\\') + 1 : name;
        fprintf(stderr, " %s+0x%lx", base, (unsigned long)((BYTE *)frames[i] - (BYTE *)module));
    }
    fprintf(stderr, "\n");
    for (i = 1; i <= RECENT; i++) {
        LONG slot = (recent_next + i) % RECENT;
        if (recent[slot].tick)
            fprintf(stderr, "dllmgr71: %.1f s before exit: %s\n", (GetTickCount() - recent[slot].tick) / 1000.0, recent[slot].text);
    }
    EnumWindows(exit_window, (LPARAM)&windows);
    fflush(stderr);
}

/* #76 crash report (DLLMGR76_OFF=1 turns it off): a module load/unload log
 * (LdrRegisterDllNotification) and a vectored exception handler that, for an
 * access violation raised in the main executable, writes to stderr (the run
 * log) the fault address, its memory state, whether it lies in a module that
 * was unloaded earlier, the last module events and the recent window events
 * of #71. It only logs (EXCEPTION_CONTINUE_SEARCH), at most 4 times. */
#define MODLOG 96
static struct { DWORD tick, base, size; char load; char name[48]; } modlog[MODLOG];
static LONG modlog_next;

typedef struct { ULONG Flags; const UNICODE_STRING *FullDllName; const UNICODE_STRING *BaseDllName; void *DllBase; ULONG SizeOfImage; } DLLMGR_DLL_NOTIFY;
typedef NTSTATUS (NTAPI *LDRREGISTER)(ULONG, void (CALLBACK *)(ULONG, const DLLMGR_DLL_NOTIFY *, void *), void *, void **);

static void CALLBACK dll_notify(ULONG reason, const DLLMGR_DLL_NOTIFY *data, void *context)
{
    LONG i = (InterlockedIncrement(&modlog_next) - 1) % MODLOG;
    int n = 0;
    modlog[i].tick = GetTickCount();
    modlog[i].base = (DWORD)(ULONG_PTR)data->DllBase;
    modlog[i].size = data->SizeOfImage;
    modlog[i].load = reason == 1;
    if (data->BaseDllName && data->BaseDllName->Buffer)
        n = WideCharToMultiByte(CP_UTF8, 0, data->BaseDllName->Buffer, data->BaseDllName->Length / sizeof(WCHAR),
                                modlog[i].name, sizeof(modlog[i].name) - 1, NULL, NULL);
    modlog[i].name[n > 0 ? n : 0] = 0;
}

static void crash_say(const char *text)
{
    DWORD written;
    WriteFile(GetStdHandle(STD_ERROR_HANDLE), text, lstrlenA(text), &written, NULL);
}

static LONG CALLBACK crash_handler(EXCEPTION_POINTERS *info)
{
    static LONG reports;
    EXCEPTION_RECORD *rec = info->ExceptionRecord;
    HMODULE exe = GetModuleHandleA(NULL);
    MEMORY_BASIC_INFORMATION mem;
    char line[300];
    DWORD addr, now = GetTickCount();
    LONG i, last;
    if (rec->ExceptionCode != EXCEPTION_ACCESS_VIOLATION || rec->NumberParameters < 2) return EXCEPTION_CONTINUE_SEARCH;
    if (!VirtualQuery(exe, &mem, sizeof(mem))) return EXCEPTION_CONTINUE_SEARCH;
    {
        MEMORY_BASIC_INFORMATION code;
        if (!VirtualQuery(rec->ExceptionAddress, &code, sizeof(code)) || code.AllocationBase != (void *)exe)
            return EXCEPTION_CONTINUE_SEARCH;
    }
    if (InterlockedIncrement(&reports) > 4) return EXCEPTION_CONTINUE_SEARCH;
    addr = (DWORD)rec->ExceptionInformation[1];
    if (!VirtualQuery((void *)(ULONG_PTR)addr, &mem, sizeof(mem))) mem.State = 0;
    wsprintfA(line, "dllmgr76: access violation in main exe +0x%lx, %s 0x%08lx (memory %s), thread %04lx\n",
              (DWORD)((BYTE *)rec->ExceptionAddress - (BYTE *)exe),
              rec->ExceptionInformation[0] == 1 ? "writing" : rec->ExceptionInformation[0] == 8 ? "executing" : "reading", addr,
              mem.State == MEM_FREE ? "free" : mem.State == MEM_RESERVE ? "reserved" : mem.State == MEM_COMMIT ? "committed" : "?",
              GetCurrentThreadId());
    crash_say(line);
    last = modlog_next;
    for (i = 0; i < MODLOG && i < last; i++) {
        LONG k = (last - 1 - i) % MODLOG;
        if (addr >= modlog[k].base && addr - modlog[k].base < modlog[k].size) {
            wsprintfA(line, "dllmgr76: 0x%08lx is inside %s %s %lu ms ago (base 0x%08lx size 0x%lx)\n", addr, modlog[k].name,
                      modlog[k].load ? "loaded" : "UNLOADED", now - modlog[k].tick, modlog[k].base, modlog[k].size);
            crash_say(line);
            break;
        }
    }
    for (i = last > 12 ? last - 12 : 0; i < last; i++) {
        LONG k = i % MODLOG;
        wsprintfA(line, "dllmgr76: %lu ms before: %s %s 0x%08lx-0x%08lx\n", now - modlog[k].tick,
                  modlog[k].load ? "load" : "unload", modlog[k].name, modlog[k].base, modlog[k].base + modlog[k].size);
        crash_say(line);
    }
    for (i = 1; i <= RECENT; i++) {
        LONG slot = (recent_next + i) % RECENT;
        if (recent[slot].tick) {
            wsprintfA(line, "dllmgr76: %lu ms before: %s\n", now - recent[slot].tick, recent[slot].text);
            crash_say(line);
        }
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

static void start_crash_report(void)
{
    void *cookie;
    LDRREGISTER reg = (LDRREGISTER)GetProcAddress(GetModuleHandleA("ntdll.dll"), "LdrRegisterDllNotification");
    if (GetEnvironmentVariableA("DLLMGR76_OFF", NULL, 0)) return;
    if (reg) reg(0, dll_notify, NULL, &cookie);
    AddVectoredExceptionHandler(1, crash_handler);
}

#ifdef DLLMGR27_CAPTIONLESS_ONLY
/* #76 hit-test guard (on by default, DLLMGR76_NO_GUARD=1 turns it off;
 * experiments/photoshop-cs2-76/README.md). Photoshop.exe 9.0 (link stamp
 * 0x42400fac) finds the window under the cursor with a hit test at
 * exe+0xb01a90 (screen point, out window record -> part code). For a window
 * of its document or palette class it asks GetDlgItem(w, 0) for the content
 * view; when there is none it returns part 4/5 but never writes the record,
 * and one caller then takes the cursor point for a record pointer (crash at
 * exe+0xb249ce). The exe's delay-import slot of GetDlgItem gets a hook that
 * acts only for calls made through that slot from the hit test: when the
 * answer is NULL, the record is set to NULL and the hit test returns through
 * a stub that makes its part code 0, its own "nothing here" answer, which
 * every caller handles. One "dllmgr76: guard:" line per such window on
 * stderr (the run log). DLLMGR76_TRACE=N logs the first N such calls. */
#define PS9_STAMP 0x42400fac
#define PS9_HIT_TEST 0xb01a90
#define PS9_HIT_TEST_SPAN 0x1000  /* the GetDlgItem calls lie in the hit test's own body */

static BYTE *guard_exe, *guard_code_end;
static void **guard_slot;
static HWND (WINAPI *real_get_dlg_item)(HWND, int);
static LONG guard_trace;
static HWND guard_logged[32];
static LONG guard_logged_n;
static DWORD *guard_where;  /* stack slot of the hit test's return address while redirected */
static void *volatile guard_return __asm__("dllmgr76_guard_return") __attribute__((used));

/* The redirected hit test returns here: part code 0, then on to its caller
 * (the stack is as the hit test left it, whatever its calling convention). */
void guard_nothing(void) __asm__("dllmgr76_guard_nothing");
__asm__(".text\n"
        "dllmgr76_guard_nothing:\n"
        "\tpushl dllmgr76_guard_return\n"
        "\tmovl $0, dllmgr76_guard_return\n"
        "\txorl %eax, %eax\n"
        "\tret\n");

/* a return address right after "call exe+PS9_HIT_TEST" (E8 rel32) */
static BOOL returns_from_hit_test(BYTE *ret)
{
    if (ret < guard_exe + 5 || ret >= guard_code_end) return FALSE;
    return ret[-5] == 0xe8 && ret + *(INT32 *)(ret - 4) == guard_exe + PS9_HIT_TEST;
}

static HWND WINAPI get_dlg_item_guard(HWND hwnd, int id)
{
    HWND ret = real_get_dlg_item(hwnd, id);
    BYTE *from = __builtin_return_address(0);
    DWORD *frame = __builtin_frame_address(0), *top, *p, *out, caller = 0;
    char line[300], cls[64], ocls[64];
    HWND other;
    LONG i;

    __asm__("movl %%fs:4, %0" : "=r"(top));  /* NT_TIB StackBase */
    /* only "call [slot]" (FF 15 slot) from the hit test's body */
    if (ret || id || from < guard_exe + PS9_HIT_TEST + 6 || from >= guard_exe + PS9_HIT_TEST + PS9_HIT_TEST_SPAN ||
        from[-6] != 0xff || from[-5] != 0x15 || *(void ***)(from - 4) != guard_slot)
        return ret;
    cls[0] = ocls[0] = 0;
    /* the hit test's own frame: its return address into a caller, then its
     * arguments (point, out record pointer); the record lies on the stack */
    for (p = frame + 2, out = NULL; p + 3 <= top && p < frame + 2 + 1024; p++)
        if (returns_from_hit_test((BYTE *)(ULONG_PTR)*p)) {
            out = (DWORD *)(ULONG_PTR)p[2];
            caller = *p;
            break;
        }
    if (guard_trace > 0 && InterlockedDecrement(&guard_trace) >= 0) {
        GetClassNameA(hwnd, cls, sizeof(cls));
        if (out) wsprintfA(line, "dllmgr76: trace: hit test from exe+0x%lx point %08lx: GetDlgItem(%p %s, 0) = NULL, record at %p (frame %p, stack top %p)\n",
                           caller - (DWORD)(ULONG_PTR)guard_exe, p[1], (void *)hwnd, cls, (void *)out, (void *)p, (void *)top);
        else wsprintfA(line, "dllmgr76: trace: hit test at exe+0x%lx: GetDlgItem(%p %s, 0) = NULL, frame not found\n",
                       (DWORD)(from - guard_exe), (void *)hwnd, cls);
        crash_say(line);
    }
    if (!out || out <= p + 2 || out >= top || ((ULONG_PTR)out & 3)) return ret;
    /* one redirect at a time; a stale one of this thread (the hit test was
     * left without returning) no longer has the stub in its slot */
    if (InterlockedCompareExchangePointer((void **)&guard_return, (void *)(ULONG_PTR)caller, NULL)) {
        DWORD *where = guard_where;
        if (!where || where <= frame || where >= top || *where == (DWORD)(ULONG_PTR)guard_nothing) return ret;
        guard_return = NULL;
        if (InterlockedCompareExchangePointer((void **)&guard_return, (void *)(ULONG_PTR)caller, NULL)) return ret;
    }
    *out = 0;
    guard_where = p;
    *p = (DWORD)(ULONG_PTR)guard_nothing;

    for (i = 0; i < guard_logged_n && i < (LONG)ARRAYSIZE(guard_logged); i++)
        if (guard_logged[i] == hwnd) return ret;
    if ((i = InterlockedIncrement(&guard_logged_n) - 1) >= (LONG)ARRAYSIZE(guard_logged)) return ret;
    guard_logged[i] = hwnd;
    other = GetParent(hwnd);
    GetClassNameA(hwnd, cls, sizeof(cls));
    if (other) GetClassNameA(other, ocls, sizeof(ocls));
    wsprintfA(line, "dllmgr76: guard: hit test from exe+0x%lx on %p (class %s, parent/owner %p %s) without a view child; answered 'nothing here'\n",
              caller - (DWORD)(ULONG_PTR)guard_exe, (void *)hwnd, cls, (void *)other, ocls);
    crash_say(line);
    return ret;
}

static void start_hit_test_guard(void)
{
    typedef struct { DWORD attrs, name, hmod, iat, nt, bound, unload, stamp; } delay_desc;
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT];
    IMAGE_SECTION_HEADER *sec = IMAGE_FIRST_SECTION(nt);
    char value[16];
    delay_desc *d;
    int i;

    if (GetEnvironmentVariableA("DLLMGR76_NO_GUARD", NULL, 0) || nt->FileHeader.TimeDateStamp != PS9_STAMP ||
        !dir->VirtualAddress || !(real_get_dlg_item = (void *)GetProcAddress(GetModuleHandleA("user32.dll"), "GetDlgItem")))
        return;
    if (GetEnvironmentVariableA("DLLMGR76_TRACE", value, sizeof(value))) guard_trace = atoi(value);
    for (i = 0; i < nt->FileHeader.NumberOfSections; i++, sec++)
        if (PS9_HIT_TEST >= sec->VirtualAddress && PS9_HIT_TEST < sec->VirtualAddress + sec->Misc.VirtualSize &&
            (sec->Characteristics & IMAGE_SCN_MEM_EXECUTE))
            guard_code_end = base + sec->VirtualAddress + sec->Misc.VirtualSize;
    if (!guard_code_end) return;
    guard_exe = base;
#define DELAY_PTR(d, v) ((d)->attrs & 1 ? base + (v) : (BYTE *)(ULONG_PTR)(v))
    for (d = (delay_desc *)(base + dir->VirtualAddress); d->name && !guard_slot; d++) {
        IMAGE_THUNK_DATA *names = (IMAGE_THUNK_DATA *)DELAY_PTR(d, d->nt), *slots = (IMAGE_THUNK_DATA *)DELAY_PTR(d, d->iat);
        if (lstrcmpiA((char *)DELAY_PTR(d, d->name), "user32.dll")) continue;
        for (; names->u1.AddressOfData; names++, slots++) {
            DWORD protect;
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal) ||
                strcmp((char *)((IMAGE_IMPORT_BY_NAME *)DELAY_PTR(d, names->u1.AddressOfData))->Name, "GetDlgItem"))
                continue;
            if (!VirtualProtect(&slots->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) break;
            slots->u1.Function = (ULONG_PTR)get_dlg_item_guard;
            VirtualProtect(&slots->u1.Function, sizeof(void *), protect, &protect);
            guard_slot = (void **)&slots->u1.Function;
            break;
        }
    }
#undef DELAY_PTR
    if (guard_trace > 0) {
        char line[160];
        wsprintfA(line, "dllmgr76: trace: guard %s (GetDlgItem delay slot %p)\n", guard_slot ? "installed" : "NOT installed",
                  (void *)guard_slot);
        crash_say(line);
    }
}
#else
static void start_hit_test_guard(void) {}
#endif


/* Sampling profiler (DLLMGR_SAMPLE=ms[,seconds[,delay|go]], off by default): a thread
 * suspends the main thread every few ms and records EIP plus the first
 * frames of its EBP chain. Works under wow64 where perf/gdb/winedbg cannot
 * see the 32-bit stack. Addresses are resolved to module+offset only after
 * sampling, never while the main thread is suspended (it may hold the
 * loader or heap lock). Output: %TEMP%\dllmgr-sample-<pid>.txt, one line per
 * sample "ms frame0 frame1 ...". */
#define SAMPLE_DEPTH 6
#define SAMPLE_MAX 20000
static DWORD sample_buf[SAMPLE_MAX][SAMPLE_DEPTH + 1];

static void sample_name(DWORD addr, char *out, int size)
{
    HMODULE mod;
    char path[MAX_PATH], *base;
    if (!addr) { lstrcpynA(out, "-", size); return; }
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (const char *)(ULONG_PTR)addr, &mod) && GetModuleFileNameA(mod, path, sizeof(path))) {
        base = strrchr(path, '\\');
        wsprintfA(out, "%s+0x%lx", base ? base + 1 : path, addr - (DWORD)(ULONG_PTR)mod);
    }
    else wsprintfA(out, "0x%08lx", addr);
}

static DWORD sample_tid[SAMPLE_MAX];

/* one sample of one thread (suspended by the caller): EIP + EBP chain */
static void sample_thread(HANDLE thread, DWORD tid, DWORD t, int *n)
{
    CONTEXT ctx;
    DWORD ebp, frame[2];
    SIZE_T read;
    int d;
    ctx.ContextFlags = CONTEXT_CONTROL;
    if (*n >= SAMPLE_MAX || !GetThreadContext(thread, &ctx)) return;
    sample_buf[*n][0] = t;
    sample_tid[*n] = tid;
    sample_buf[*n][1] = ctx.Eip;
    ebp = ctx.Ebp;
    for (d = 2; d <= SAMPLE_DEPTH; d++) {
        if (!ReadProcessMemory(GetCurrentProcess(), (void *)(ULONG_PTR)ebp, frame, sizeof(frame), &read) || read != sizeof(frame) || frame[0] <= ebp) {
            for (; d <= SAMPLE_DEPTH; d++) sample_buf[*n][d] = 0;
            break;
        }
        sample_buf[*n][d] = frame[1];
        ebp = frame[0];
    }
    (*n)++;
}

/* DLLMGR_SAMPLE_ALL=1: every thread of the process (Photoshop renders in worker threads) */
static void sample_all_threads(DWORD t, int *n)
{
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    THREADENTRY32 te;
    DWORD pid = GetCurrentProcessId(), self = GetCurrentThreadId();
    if (snap == INVALID_HANDLE_VALUE) return;
    te.dwSize = sizeof(te);
    if (Thread32First(snap, &te)) do {
        HANDLE thread;
        if (te.th32OwnerProcessID != pid || te.th32ThreadID == self) continue;
        if (!(thread = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT, FALSE, te.th32ThreadID))) continue;
        if (SuspendThread(thread) != (DWORD)-1) {
            sample_thread(thread, te.th32ThreadID, t, n);
            ResumeThread(thread);
        }
        CloseHandle(thread);
    } while (Thread32Next(snap, &te));
    CloseHandle(snap);
}

static DWORD WINAPI sampler(void *arg)
{
    HANDLE thread = arg;
    char value[32], *comma, line[512], name[128], path[MAX_PATH];
    int interval, seconds = 10, n = 0, i, d;
    BOOL all = GetEnvironmentVariableA("DLLMGR_SAMPLE_ALL", NULL, 0) != 0;
    DWORD start = GetTickCount(), got, main_tid = GetThreadId(thread);
    HANDLE file;
    GetEnvironmentVariableA("DLLMGR_SAMPLE", value, sizeof(value));
    interval = atoi(value) > 0 ? atoi(value) : 10;
    if ((comma = strchr(value, ',')) && atoi(comma + 1) > 0) seconds = atoi(comma + 1);
    if (comma && (comma = strchr(comma + 1, ','))) {
        if (!lstrcmpiA(comma + 1, "go")) {  /* third field "go": start when Z:\tmp\dllmgr-sample-go exists */
            while (GetFileAttributesA("Z:\\tmp\\dllmgr-sample-go") == INVALID_FILE_ATTRIBUTES) Sleep(50);
            start = GetTickCount();
        }
        else if (atoi(comma + 1) > 0) {  /* third field: start after N s */
            Sleep(atoi(comma + 1) * 1000);
            start = GetTickCount();
        }
    }
    while (n < SAMPLE_MAX && GetTickCount() - start < (DWORD)seconds * 1000) {
        Sleep(interval);
        if (all) sample_all_threads(GetTickCount() - start, &n);
        else {
            if (SuspendThread(thread) == (DWORD)-1) break;
            sample_thread(thread, main_tid, GetTickCount() - start, &n);
            ResumeThread(thread);
        }
    }
    GetTempPathA(sizeof(path) - 40, path);
    wsprintfA(path + lstrlenA(path), "dllmgr-sample-%lu.txt", GetCurrentProcessId());
    file = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, 0, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    for (i = 0; i < n; i++) {
        if (all) wsprintfA(line, "%lu t%04lx%s", sample_buf[i][0], sample_tid[i], sample_tid[i] == main_tid ? "m" : "");
        else wsprintfA(line, "%lu", sample_buf[i][0]);
        for (d = 1; d <= SAMPLE_DEPTH; d++) {
            sample_name(sample_buf[i][d], name, sizeof(name));
            lstrcatA(line, " ");
            lstrcatA(line, name);
        }
        lstrcatA(line, "\r\n");
        WriteFile(file, line, lstrlenA(line), &got, NULL);
    }
    CloseHandle(file);
    return 0;
}

static void start_sampler(void)
{
    HANDLE thread;
    if (!GetEnvironmentVariableA("DLLMGR_SAMPLE", NULL, 0)) return;
    if (DuplicateHandle(GetCurrentProcess(), GetCurrentThread(), GetCurrentProcess(), &thread,
                        THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_LIMITED_INFORMATION, FALSE, 0))
        CloseHandle(CreateThread(NULL, 0, sampler, thread, 0, NULL));
}


/* #73: FastStone's "Association Settings" button calls
 * ShellExecuteA("open", "control", "/name Microsoft.DefaultPrograms ..."),
 * which does nothing in Wine. With DLLMGR73_ASSOC set by dllmgr (a Unix
 * command line), the proxy runs it instead: dllmgr's own file-type dialog. */
static HINSTANCE (WINAPI *real_shell_execute_a)(HWND, LPCSTR, LPCSTR, LPCSTR, LPCSTR, INT);

static HINSTANCE WINAPI shell_execute_assoc(HWND hwnd, LPCSTR op, LPCSTR file, LPCSTR params, LPCSTR dir, INT show)
{
    char command[1024], line[1100];
    if (file && !lstrcmpiA(file, "control") && params && strstr(params, "Microsoft.DefaultPrograms") &&
        GetEnvironmentVariableA("DLLMGR73_ASSOC", command, sizeof(command)) && !strchr(command, '"')) {
        STARTUPINFOA si = { sizeof(si) };
        PROCESS_INFORMATION pi;
        wsprintfA(line, "/bin/sh -c \"%s\"", command);
        if (CreateProcessA("Z:\\bin\\sh", line, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
            return (HINSTANCE)33;
        }
    }
    return real_shell_execute_a(hwnd, op, file, params, dir, show);
}


BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, void *reserved)
{
    char mode[8] = "";
    if (reason == DLL_PROCESS_DETACH && reserved && !GetEnvironmentVariableA("DLLMGR71_OFF", NULL, 0)) {
        exit_report();
        return TRUE;
    }
    if (reason == DLL_PROCESS_ATTACH) { start_sampler(); start_crash_report(); }  /* diagnostics, also with the proxy off */
    if (reason == DLL_PROCESS_ATTACH) start_hit_test_guard();  /* #76: crash guard, also with the proxy off */
    if (reason == DLL_PROCESS_ATTACH && GetEnvironmentVariableA("DLLMGR_MSGLOG", NULL, 0))
        CloseHandle(CreateThread(NULL, 0, msglog_writer, NULL, 0, NULL));
    if ((reason == DLL_PROCESS_ATTACH || reason == DLL_THREAD_ATTACH) && GetEnvironmentVariableA("DLLMGR27_OFF", NULL, 0)) {
        if (!self) self = instance;
        msglog_thread_hook();  /* the timeline also with the proxy off (reference runs on Windows) */
    }
    if (GetEnvironmentVariableA("DLLMGR27_OFF", NULL, 0)) return TRUE;
    GetEnvironmentVariableA("DLLMGR27_MODE", mode, sizeof(mode));
    if (reason == DLL_PROCESS_ATTACH) {
        debug = GetEnvironmentVariableA("DLLMGR27_DEBUG", NULL, 0) != 0;
        self = instance;
        /* #73: before the early return below: `dllmgr run` sets both
         * DLLMGR73_ASSOC and DLLMGR_TARGET_EXE */
        if (GetEnvironmentVariableA("DLLMGR73_ASSOC", NULL, 0))
            hook_import(GetModuleHandleW(NULL), "shell32.dll", "ShellExecuteA", (void *)shell_execute_assoc,
                        (void **)&real_shell_execute_a);
        /* Started by `dllmgr run` (private runtime with the real fix): tell a
         * waiting stock-Wine trampoline that we are up, and add nothing else. */
        if (GetEnvironmentVariableA("DLLMGR_TARGET_EXE", NULL, 0)) {
            /* DLLMGR51_NO_SIGNAL: test switch, as if this proxy loaded too late */
            HANDLE event = GetEnvironmentVariableA("DLLMGR51_NO_SIGNAL", NULL, 0) ? NULL : OpenEventW(EVENT_MODIFY_STATE, FALSE, TRAMP_EVENT);
            TRACE("private runtime: trampoline event %s\n", event ? "set" : "absent");
            if (event) {
                SetEvent(event);
                CloseHandle(event);
            }
#ifndef DLLMGR27_ACTIVE_IN_RUNTIME
            idle = TRUE; /* DisableThreadLibraryCalls is refused for DLLs
                          * with static TLS (mingw's TLS callbacks), as on
                          * Windows, so DLL_THREAD_ATTACH still arrives */
            DisableThreadLibraryCalls(instance);
            return TRUE;
#endif
            /* Photoshop build: the splash shaping is not in the runtime, so
             * stay active there; only the trampoline is not armed. */
        }
        else if (!GetEnvironmentVariableA("DLLMGR27_NO_TRAMPOLINE", NULL, 0)) {
            WCHAR *companion = read_companion();
            if (companion) {
                HeapFree(GetProcessHeap(), 0, companion);
                tramp_pending = TRUE;
                cbt_hook = SetWindowsHookExW(WH_CBT, cbt, instance, GetCurrentThreadId());
                TRACE("trampoline armed\n");
            }
        }
        if (!lstrcmpiA(mode, "iat")) {
            /* legacy mode: only ShowWindow imported by the exe itself */
            DisableThreadLibraryCalls(instance);
            hook_import(GetModuleHandleW(NULL), "user32.dll", "ShowWindow", (void *)show_prefilled,
                        (void **)&real_show_window);
        } else {
            hook_thread();
            hook_release_dc();
        }
    } else if (reason == DLL_THREAD_ATTACH && !idle && lstrcmpiA(mode, "iat")) {
        hook_thread();
    }
    return TRUE;
}
