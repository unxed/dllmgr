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

static BOOL (WINAPI *real_show_window)(HWND, int);

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

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, void *reserved)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(instance);
        if (!GetEnvironmentVariableA("DLLMGR27_OFF", NULL, 0))
            hook_import(GetModuleHandleW(NULL), "user32.dll", "ShowWindow", (void *)show_prefilled,
                        (void **)&real_show_window);
    }
    return TRUE;
}
