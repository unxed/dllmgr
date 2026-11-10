/* #78: top-level windows of the Photoshop process in z-order (EnumWindows
 * order), first line in fgprobe78's format. */
#include <windows.h>
#include <stdio.h>
static DWORD pid;
static BOOL CALLBACK cb(HWND h, LPARAM l)
{
    DWORD p; char cls[64], txt[64]; RECT r;
    GetWindowThreadProcessId(h, &p);
    if (p != pid) return TRUE;
    GetClassNameA(h, cls, sizeof(cls)); GetWindowTextA(h, txt, sizeof(txt)); GetWindowRect(h, &r);
    printf("z %p %-12s vis=%d ex=%08lx st=%08lx owner=%p (%ld,%ld)-(%ld,%ld) \"%s\"\n", h, cls, IsWindowVisible(h),
           GetWindowLongA(h, GWL_EXSTYLE), GetWindowLongA(h, GWL_STYLE), GetWindow(h, GW_OWNER),
           r.left, r.top, r.right, r.bottom, txt);
    return TRUE;
}
int main(void)
{
    HWND m = FindWindowA("Photoshop", NULL);
    GUITHREADINFO gi = {sizeof(gi)};
    if (!m) { printf("no main\n"); return 1; }
    GetWindowThreadProcessId(m, &pid);
    GetGUIThreadInfo(GetWindowThreadProcessId(m, NULL), &gi);
    printf("main %p foreground %p active %p focus %p\n", m, GetForegroundWindow(), gi.hwndActive, gi.hwndFocus);
    EnumWindows(cb, 0);
    return 0;
}
