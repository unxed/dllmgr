/* #78: Photoshop's palette raise in miniature. Hidden topmost tooltip A
 * (unowned), hidden topmost popup B owned by the main window, visible
 * palette P owned by main whose WM_WINDOWPOSCHANGING turns HWND_TOP into
 * "after A" (as Photoshop does). SetWindowPos(P, HWND_TOP, SWP_NOACTIVATE):
 * does P become WS_EX_TOPMOST? Variant "nob": without B. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
static HWND A, B, P, M;
static LRESULT CALLBACK palproc(HWND h, UINT msg, WPARAM wp, LPARAM lp)
{
    if (msg == WM_WINDOWPOSCHANGING && h == P)
    {
        WINDOWPOS *wpos = (WINDOWPOS *)lp;
        if (!(wpos->flags & SWP_NOZORDER) && wpos->hwndInsertAfter == HWND_TOP) wpos->hwndInsertAfter = A;
    }
    return DefWindowProcA(h, msg, wp, lp);
}
static void zlist(void)
{
    HWND h;
    for (h = GetTopWindow(0); h; h = GetWindow(h, GW_HWNDNEXT))
    {
        const char *n = h == A ? "A" : h == B ? "B" : h == P ? "P" : h == M ? "M" : NULL;
        if (n) printf("  %s ex=%08lx vis=%d\n", n, GetWindowLongA(h, GWL_EXSTYLE) & 0xff, IsWindowVisible(h));
    }
}
int main(int argc, char **argv)
{
    WNDCLASSA wc = {0};
    int nob = argc > 1 && !strcmp(argv[1], "nob");
    MSG m;
    DWORD t;
    wc.lpfnWndProc = palproc; wc.lpszClassName = "z78b"; wc.hInstance = GetModuleHandleA(0);
    RegisterClassA(&wc);
    M = CreateWindowExA(0, "z78b", "main", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 100, 100, 600, 400, 0, 0, 0, 0);
    A = CreateWindowExA(WS_EX_TOOLWINDOW | WS_EX_TOPMOST, "z78b", "", WS_POPUP | WS_BORDER, 0, 0, 10, 10, 0, 0, 0, 0);
    if (!nob) B = CreateWindowExA(WS_EX_TOPMOST, "z78b", "", WS_POPUP, 5000, 5000, 50, 50, M, 0, 0, 0);
    P = CreateWindowExA(WS_EX_TOOLWINDOW, "z78b", "", WS_POPUP | WS_CAPTION | WS_VISIBLE, 500, 120, 200, 120, M, 0, 0, 0);
    SetForegroundWindow(M);
    for (t = GetTickCount(); GetTickCount() - t < 500; Sleep(10))
        while (PeekMessageA(&m, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&m);
    printf("%s before:\n", nob ? "nob" : "withB"); zlist();
    SetWindowPos(P, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    printf("after SetWindowPos(P, HWND_TOP):\n"); zlist();
    printf("P topmost: %s\n", GetWindowLongA(P, GWL_EXSTYLE) & WS_EX_TOPMOST ? "YES" : "no");
    return 0;
}
