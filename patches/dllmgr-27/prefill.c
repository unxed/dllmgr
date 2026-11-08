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
#include <stdio.h>

/* DLLMGR27_DEBUG=1: one line per decision on stderr (compact). */
static int debug;
#define TRACE(...) do { if (debug) { fprintf(stderr, "dllmgr27: " __VA_ARGS__); fflush(stderr); } } while (0)

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
        }
        physical_end(old_ctx);
    }
    release_capture(c);
}

static BOOL top_level_hidden(HWND hwnd)
{
    return !(GetWindowLongW(hwnd, GWL_STYLE) & WS_CHILD) && !IsWindowVisible(hwnd);
}

static LRESULT CALLBACK before(int code, WPARAM wparam, LPARAM lparam)
{
    const CWPSTRUCT *m = (const CWPSTRUCT *)lparam;
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

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, void *reserved)
{
    char mode[8] = "";
    if (GetEnvironmentVariableA("DLLMGR27_OFF", NULL, 0)) return TRUE;
    GetEnvironmentVariableA("DLLMGR27_MODE", mode, sizeof(mode));
    if (reason == DLL_PROCESS_ATTACH) {
        debug = GetEnvironmentVariableA("DLLMGR27_DEBUG", NULL, 0) != 0;
        self = instance;
        if (!lstrcmpiA(mode, "iat")) {
            /* legacy mode: only ShowWindow imported by the exe itself */
            DisableThreadLibraryCalls(instance);
            hook_import(GetModuleHandleW(NULL), "user32.dll", "ShowWindow", (void *)show_prefilled,
                        (void **)&real_show_window);
        } else hook_thread();
    } else if (reason == DLL_THREAD_ATTACH && lstrcmpiA(mode, "iat")) {
        hook_thread();
    }
    return TRUE;
}
