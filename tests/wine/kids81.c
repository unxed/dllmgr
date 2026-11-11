/* #81: list the MDI client and the document windows of Photoshop CS2 with
 * their window rects in physical pixels (the probe thread is per-monitor
 * aware) and in the target's logical units (GetWindowRect from an unaware
 * thread would be scaled; we print both through the DPI context switch).
 * Also prints the visible top-level windows of the process whose title has
 * " @ " (a document window that is not an MDI child).
 * Build: i686-w64-mingw32-gcc -O2 -o kids81.exe kids81.c -luser32 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static BOOL CALLBACK cb(HWND h, LPARAM l)
{
    char cls[64], text[128];
    RECT r, c;
    POINT o = {0, 0};

    GetClassNameA(h, cls, sizeof(cls));
    if (!strcmp(cls, "Button") || !strcmp(cls, "Static") || !strcmp(cls, "Edit")) return TRUE;
    GetWindowTextA(h, text, sizeof(text));
    GetWindowRect(h, &r);
    GetClientRect(h, &c);
    ClientToScreen(h, &o);
    printf("%p %-24s parent=%p win=%ld,%ld-%ld,%ld client@%ld,%ld %ldx%ld style=%08lx ex=%08lx vis=%d \"%s\"\n", h, cls,
           GetParent(h), r.left, r.top, r.right, r.bottom, o.x, o.y, c.right, c.bottom,
           GetWindowLongA(h, GWL_STYLE), GetWindowLongA(h, GWL_EXSTYLE), IsWindowVisible(h), text);
    return TRUE;
}

static DWORD target_pid;

static BOOL CALLBACK top_cb(HWND h, LPARAM l)
{
    DWORD pid;
    char text[128];

    GetWindowThreadProcessId(h, &pid);
    if (pid != target_pid || !IsWindowVisible(h)) return TRUE;
    GetWindowTextA(h, text, sizeof(text));
    if (!strstr(text, " @ ")) return TRUE;
    printf("top-level ");
    cb(h, 0);
    printf("  owner=%p\n", GetWindow(h, GW_OWNER));
    return TRUE;
}

int main(int argc, char **argv)
{
    HWND top = FindWindowA(argc > 1 ? argv[1] : "Photoshop", NULL);
    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE);
    if (!top) { printf("no main window\n"); return 1; }
    printf("top %p\n", top);
    EnumChildWindows(top, cb, 0);
    GetWindowThreadProcessId(top, &target_pid);
    EnumWindows(top_cb, 0);
    return 0;
}
