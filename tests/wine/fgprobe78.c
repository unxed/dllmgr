/* #78/#82: the Wine side of ps35-palette.ps1. Prints the foreground window,
 * the active/focus windows of the GUI thread of the first top-level window
 * of class argv[1] (default "Photoshop"), and every visible top-level window
 * of that process with styles and owner, one line each.
 * Build: i686-w64-mingw32-gcc -O2 -o fgprobe78.exe fgprobe78.c -luser32 */
#include <windows.h>
#include <stdio.h>

static DWORD target_pid;

static BOOL CALLBACK list(HWND h, LPARAM lp)
{
    DWORD pid;
    char text[128], cls[64];
    RECT r;

    GetWindowThreadProcessId(h, &pid);
    if (pid != target_pid || !IsWindowVisible(h)) return TRUE;
    GetWindowTextA(h, text, sizeof(text));
    GetClassNameA(h, cls, sizeof(cls));
    GetWindowRect(h, &r);
    printf("win %p class=%s text=\"%s\" rect=%ld,%ld-%ld,%ld style=%08lx exstyle=%08lx owner=%p\n",
           h, cls, text, r.left, r.top, r.right, r.bottom, GetWindowLongA(h, GWL_STYLE),
           GetWindowLongA(h, GWL_EXSTYLE), GetWindow(h, GW_OWNER));
    return TRUE;
}

int main(int argc, char **argv)
{
    HWND main_hwnd = FindWindowA(argc > 1 ? argv[1] : "Photoshop", NULL);
    GUITHREADINFO info = {sizeof(info)};
    DWORD tid;

    if (!main_hwnd) { printf("no main window\n"); return 1; }
    tid = GetWindowThreadProcessId(main_hwnd, &target_pid);
    GetGUIThreadInfo(tid, &info);
    printf("main %p foreground %p active %p focus %p flags %lx\n", main_hwnd, GetForegroundWindow(),
           info.hwndActive, info.hwndFocus, info.flags);
    if (argc > 2) EnumWindows(list, 0);
    return 0;
}
