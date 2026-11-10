/* #78: owned tool window raised with SetWindowPos(HWND_TOP, SWP_NOACTIVATE)
 * while a hidden topmost popup exists; print whether it became topmost. */
#include <windows.h>
#include <stdio.h>
static void show(const char *tag, HWND h)
{
    printf("%-28s exstyle %08lx\n", tag, GetWindowLongA(h, GWL_EXSTYLE));
}
int main(int argc, char **argv)
{
    WNDCLASSA wc = {0};
    HWND main, pal, pal2, over;
    int hidden_over = argc < 2 || argv[1][0] != 'n';
    wc.lpfnWndProc = DefWindowProcA; wc.lpszClassName = "z78"; wc.hInstance = GetModuleHandleA(0);
    RegisterClassA(&wc);
    main = CreateWindowExA(0, "z78", "main", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 100, 100, 600, 400, 0, 0, 0, 0);
    pal = CreateWindowExA(WS_EX_TOOLWINDOW, "z78", "", WS_POPUP | WS_CAPTION | WS_VISIBLE, 500, 120, 200, 120, main, 0, 0, 0);
    pal2 = CreateWindowExA(WS_EX_TOOLWINDOW, "z78", "", WS_POPUP | WS_CAPTION | WS_VISIBLE, 500, 260, 200, 120, main, 0, 0, 0);
    if (hidden_over)
        over = CreateWindowExA(WS_EX_TOOLWINDOW | WS_EX_TOPMOST, "z78", "", WS_POPUP | WS_BORDER | WS_DISABLED, 0, 0, 1152, 648, main, 0, 0, 0);
    SetForegroundWindow(main);
    { MSG m; DWORD t = GetTickCount(); while (GetTickCount() - t < 500) { while (PeekMessageA(&m, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&m); Sleep(10); } }
    show("before", pal);
    SetWindowPos(pal, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    show("after HWND_TOP", pal);
    SetWindowPos(pal2, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    show("pal2 after HWND_TOP", pal2);
    show("pal after pal2 raised", pal);
    return 0;
}
