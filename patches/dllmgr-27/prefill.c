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
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

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
        if (lstrcmpiA((char *)base + desc->Name, "user32.dll")) continue;
        for (; slot->u1.Function; slot++) {
            DWORD protect;
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
        if (lstrcmpiA((char *)DELAY_PTR(d, d->name), "user32.dll")) continue;
        for (; names->u1.AddressOfData; names++, slots++) {
            DWORD protect;
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal) ||
                strcmp((char *)((IMAGE_IMPORT_BY_NAME *)DELAY_PTR(d, names->u1.AddressOfData))->Name, "ReleaseDC"))
                continue;
            if (!VirtualProtect(&slots->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) continue;
            slots->u1.Function = (ULONG_PTR)release_dc_hook;
            VirtualProtect(&slots->u1.Function, sizeof(void *), protect, &protect);
            TRACE("ReleaseDC hooked in the delay imports of %p\n", (void *)module);
        }
    }
#undef DELAY_PTR
}

typedef struct { ULONG flags; const UNICODE_STRING *full, *base; void *dll; ULONG size; } dll_loaded;
static void CALLBACK on_dll(ULONG reason, const dll_loaded *data, void *context)
{
    if (reason == 1 /* LDR_DLL_NOTIFICATION_REASON_LOADED */) {
        hook_module_release_dc((HMODULE)data->dll);
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
    if (!real_release_dc || GetEnvironmentVariableA("DLLMGR27_NO_SHAPE", NULL, 0)) return;
    if (K32EnumProcessModules(GetCurrentProcess(), modules, sizeof(modules), &bytes))
        for (DWORD i = 0; i < bytes / sizeof(HMODULE) && i < 512; i++) hook_module_release_dc(modules[i]);
    hook_delay_release_dc(GetModuleHandleW(NULL));
    if (reg) reg(0, on_dll, NULL, &cookie);
}

static LRESULT CALLBACK before(int code, WPARAM wparam, LPARAM lparam)
{
    const CWPSTRUCT *m = (const CWPSTRUCT *)lparam;
    if (code == HC_ACTION && shape_pending) shape_tick();
    if (code == HC_ACTION && m->message == WM_WINDOWPOSCHANGING &&
        (((WINDOWPOS *)m->lParam)->flags & SWP_SHOWWINDOW) && top_level_hidden(m->hwnd))
        capture_under(m->hwnd, (WINDOWPOS *)m->lParam);
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
    if (code == HC_ACTION && m->message == WM_WINDOWPOSCHANGED &&
        (((WINDOWPOS *)m->lParam)->flags & SWP_SHOWWINDOW))
        present_capture(m->hwnd);
    return CallNextHookEx(NULL, code, wparam, lparam);
}

static void hook_thread(void)
{
    DWORD tid = GetCurrentThreadId();
    TRACE("hook thread %04lx\n", tid);
    SetWindowsHookExW(WH_CALLWNDPROC, before, self, tid);
    SetWindowsHookExW(WH_CALLWNDPROCRET, after, self, tid);
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

static void trampoline(void)
{
    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    WCHAR *prefix = read_companion(), *app = NULL, *cmd = NULL, *end;
    const WCHAR *args = own_arguments();
    char wait_text[16] = "";
    DWORD wait = 15000, n;
    HANDLE event = NULL;

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
    if (!CreateProcessW(app, cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        TRACE("trampoline: cannot start launcher (error %lu), staying on stock Wine\n", GetLastError());
        goto done;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    TRACE("trampoline: started %ls, waiting %lu ms\n", cmd, wait);
    if (WaitForSingleObject(event, wait) == WAIT_OBJECT_0) {
        TRACE("trampoline: private runtime took over, exiting\n");
        ExitProcess(0);
    }
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
    if (code == HCBT_CREATEWND && tramp_pending) {
        tramp_pending = FALSE;
        UnhookWindowsHookEx(cbt_hook);
        trampoline();
    }
    return CallNextHookEx(NULL, code, wparam, lparam);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, void *reserved)
{
    char mode[8] = "";
    if (GetEnvironmentVariableA("DLLMGR27_OFF", NULL, 0)) return TRUE;
    GetEnvironmentVariableA("DLLMGR27_MODE", mode, sizeof(mode));
    if (reason == DLL_PROCESS_ATTACH) {
        debug = GetEnvironmentVariableA("DLLMGR27_DEBUG", NULL, 0) != 0;
        self = instance;
        /* Started by `dllmgr run` (private runtime with the real fix): tell a
         * waiting stock-Wine trampoline that we are up, and add nothing else. */
        if (GetEnvironmentVariableA("DLLMGR_TARGET_EXE", NULL, 0)) {
            HANDLE event = OpenEventW(EVENT_MODIFY_STATE, FALSE, TRAMP_EVENT);
            TRACE("private runtime: proxy idle, trampoline event %s\n", event ? "set" : "absent");
            if (event) {
                SetEvent(event);
                CloseHandle(event);
            }
            idle = TRUE; /* DisableThreadLibraryCalls is refused for DLLs
                          * with static TLS (mingw's TLS callbacks), as on
                          * Windows, so DLL_THREAD_ATTACH still arrives */
            DisableThreadLibraryCalls(instance);
            return TRUE;
        }
        if (!GetEnvironmentVariableA("DLLMGR27_NO_TRAMPOLINE", NULL, 0)) {
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
