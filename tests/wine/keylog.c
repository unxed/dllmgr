/* Keyboard probe (#20 / Wine 57513, also for Far #18): a focused window that
 * prints one line per keyboard/IME message it receives:
 *   msg=<name> wp=<hex> lp=<hex> [chr=U+XXXX] [ime=<GCS_RESULTSTR as U+...>]
 * plus the keyboard layout (HKL) at start. WM_IME_COMPOSITION results are read
 * with ImmGetCompositionStringW, as PuTTY does; DefWindowProc then turns them
 * into WM_IME_CHAR/WM_CHAR. Exits after 15 s.
 * Argument "first": create and destroy a top-level window before the main
 * one, like PuTTY does (Wine 57513: the IME result is then lost).
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -municode -o keylog.exe keylog.c -limm32 */
#include <windows.h>
#include <imm.h>
#include <stdio.h>

static const char *name(UINT m)
{
    switch (m) {
    case WM_KEYDOWN: return "WM_KEYDOWN"; case WM_KEYUP: return "WM_KEYUP";
    case WM_CHAR: return "WM_CHAR"; case WM_DEADCHAR: return "WM_DEADCHAR";
    case WM_SYSKEYDOWN: return "WM_SYSKEYDOWN"; case WM_SYSCHAR: return "WM_SYSCHAR";
    case WM_UNICHAR: return "WM_UNICHAR";
    case WM_IME_STARTCOMPOSITION: return "WM_IME_STARTCOMPOSITION";
    case WM_IME_ENDCOMPOSITION: return "WM_IME_ENDCOMPOSITION";
    case WM_IME_COMPOSITION: return "WM_IME_COMPOSITION";
    case WM_IME_CHAR: return "WM_IME_CHAR"; case WM_IME_NOTIFY: return "WM_IME_NOTIFY";
    case WM_IME_SETCONTEXT: return "WM_IME_SETCONTEXT"; case WM_INPUTLANGCHANGE: return "WM_INPUTLANGCHANGE";
    case WM_IME_KEYDOWN: return "WM_IME_KEYDOWN";
    }
    return NULL;
}

static LRESULT CALLBACK proc(HWND hwnd, UINT m, WPARAM wp, LPARAM lp)
{
    const char *n = name(m);
    if (n) {
        printf("msg=%s wp=%llx lp=%llx", n, (unsigned long long)wp, (unsigned long long)lp);
        if (m == WM_CHAR || m == WM_IME_CHAR || m == WM_UNICHAR) printf(" chr=U+%04X", (unsigned)wp);
        if (m == WM_IME_COMPOSITION && (lp & GCS_RESULTSTR)) {
            HIMC imc = ImmGetContext(hwnd);
            WCHAR buf[64];
            LONG bytes = imc ? ImmGetCompositionStringW(imc, GCS_RESULTSTR, buf, sizeof(buf)) : -1;
            printf(" ime=");
            for (LONG i = 0; i < bytes / 2; i++) printf("U+%04X ", buf[i]);
            if (imc) ImmReleaseContext(hwnd, imc);
        }
        printf("\n");
        fflush(stdout);
    }
    if (m == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcW(hwnd, m, wp, lp);
}

int wmain(int argc, WCHAR **argv)
{
    WNDCLASSW wc = {0};
    MSG msg;
    HWND hwnd;
    wc.lpfnWndProc = proc;
    wc.hInstance = GetModuleHandleW(NULL);
    wc.lpszClassName = L"keylog";
    RegisterClassW(&wc);
    if (argc > 1 && !lstrcmpW(argv[1], L"first")) {
        HWND first = CreateWindowW(L"keylog", L"first", WS_OVERLAPPEDWINDOW, 0, 0, 100, 100,
                                   NULL, NULL, wc.hInstance, NULL);
        ImmReleaseContext(first, ImmGetContext(first));
        DestroyWindow(first);
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) DispatchMessageW(&msg);
        printf("first window created and destroyed\n");
    }
    hwnd = CreateWindowW(L"keylog", L"keylog", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 100, 100, 400, 200,
                         NULL, NULL, wc.hInstance, NULL);
    printf("hkl=%p\n", GetKeyboardLayout(0));
    fflush(stdout);
    SetTimer(hwnd, 1, 15000, NULL);
    while (GetMessageW(&msg, NULL, 0, 0)) {
        if (msg.message == WM_TIMER) break;
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return 0;
}
