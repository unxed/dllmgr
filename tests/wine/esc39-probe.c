/* #39: when does FastStone start handling Esc, compared with when its image
 * is first on screen?  Starts EXE [IMAGE], then every ~50 ms logs the
 * process's top-level windows (class, rect, visible), the foreground window
 * and whether the screen centre shows the image colour.  With KEY=sendinput
 * it sends one Esc (SendInput) at DELAY_MS after CreateProcess and reports
 * whether the process exits or shows its Esc confirmation
 * (TMessageWithNoMorebox), and when.  KEY=none only observes (for an Esc
 * sent from outside, e.g. xdotool under Wine; MARKER is created at launch).
 *
 * esc39-probe.exe EXE IMAGE|- RRGGBB DELAY_MS sendinput|none MAX_MS [MARKER]
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#define MAXW 64
struct win { HWND hwnd; WCHAR cls[96]; RECT rect; BOOL visible; };
static DWORD pid;
static struct win wins[MAXW];
static int nwins;
static LARGE_INTEGER freq, t0;

static long now_ms(void)
{
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    return (long)((t.QuadPart - t0.QuadPart) * 1000 / freq.QuadPart);
}

static BOOL CALLBACK collect(HWND hwnd, LPARAM unused)
{
    DWORD owner = 0;
    GetWindowThreadProcessId(hwnd, &owner);
    if (owner != pid || nwins >= MAXW) return TRUE;
    wins[nwins].hwnd = hwnd;
    GetClassNameW(hwnd, wins[nwins].cls, 96);
    GetWindowRect(hwnd, &wins[nwins].rect);
    wins[nwins].visible = IsWindowVisible(hwnd);
    nwins++;
    return TRUE;
}

static void describe_hwnd(HWND hwnd, WCHAR *out, size_t n)
{
    DWORD owner = 0;
    WCHAR cls[96] = L"";
    if (!hwnd) { swprintf(out, n, L"none"); return; }
    GetWindowThreadProcessId(hwnd, &owner);
    GetClassNameW(hwnd, cls, 96);
    swprintf(out, n, L"%p:%ls%ls", hwnd, cls, owner == pid ? L"(app)" : L"");
}

static int near_colour(COLORREF c, unsigned rgb)
{
    int dr = (int)GetRValue(c) - (int)((rgb >> 16) & 255);
    int dg = (int)GetGValue(c) - (int)((rgb >> 8) & 255);
    int db = (int)GetBValue(c) - (int)(rgb & 255);
    return abs(dr) + abs(dg) + abs(db) <= 30;
}

static void send_esc(void)
{
    INPUT in[2];
    ZeroMemory(in, sizeof(in));
    in[0].type = in[1].type = INPUT_KEYBOARD;
    in[0].ki.wVk = in[1].ki.wVk = VK_ESCAPE;
    in[0].ki.wScan = in[1].ki.wScan = 0x01;
    in[1].ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(2, in, sizeof(INPUT));
}

/* Sleep while answering messages for the launcher window. */
static void pump_sleep(DWORD ms)
{
    MSG msg;
    DWORD end = GetTickCount() + ms;
    for (;;) {
        DWORD left = (long)(end - GetTickCount()) > 0 ? end - GetTickCount() : 0;
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        if (!left) break;
        MsgWaitForMultipleObjects(0, NULL, FALSE, left, QS_ALLINPUT);
    }
}

/* Be the foreground process before CreateProcess, like a file manager or a
 * terminal the user just typed into: a process started by the foreground
 * process may take the foreground itself.  On a CI runner the console host
 * holds it otherwise and FastStone's windows stay in the background. */
static HWND launcher_foreground(void)
{
    WNDCLASSW wc = {0};
    HWND h, fg;
    DWORD fg_thread, me = GetCurrentThreadId();
    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = GetModuleHandleW(NULL);
    wc.lpszClassName = L"Esc39Launcher";
    wc.hbrBackground = (HBRUSH)GetStockObject(GRAY_BRUSH);
    RegisterClassW(&wc);
    h = CreateWindowExW(0, wc.lpszClassName, L"esc39 launcher", WS_POPUP | WS_VISIBLE,
                        0, 0, 120, 120, NULL, NULL, wc.hInstance, NULL);
    pump_sleep(50);
    fg = GetForegroundWindow();
    fg_thread = fg ? GetWindowThreadProcessId(fg, NULL) : 0;
    if (fg_thread && fg_thread != me) AttachThreadInput(me, fg_thread, TRUE);
    keybd_event(VK_MENU, 0x38, 0, 0);
    keybd_event(VK_MENU, 0x38, KEYEVENTF_KEYUP, 0);
    BringWindowToTop(h);
    SetForegroundWindow(h);
    SetFocus(h);
    if (fg_thread && fg_thread != me) AttachThreadInput(me, fg_thread, FALSE);
    pump_sleep(200);
    return h;
}

int wmain(int argc, WCHAR **argv)
{
    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    WCHAR cmd[4096], prev_wins[8192] = L"#", cur[8192], fgdesc[256], prev_fg[256] = L"#";
    unsigned colour;
    long delay, max_ms, esc_ms = -1, first_image = -1, first_fullscreen = -1;
    long first_tform = -1, exit_ms = -1, confirm_ms = -1, stop_at;
    int sendinput, cx, cy;
    HDC screen;
    WCHAR fg_at_esc[256] = L"-", img_win[256] = L"-";
    const WCHAR *image;

    if (argc < 7) {
        fputs("esc39-probe.exe EXE IMAGE|- RRGGBB DELAY_MS sendinput|none MAX_MS [MARKER]\n", stderr);
        return 2;
    }
    image = wcscmp(argv[2], L"-") ? argv[2] : NULL;
    colour = (unsigned)wcstoul(argv[3], NULL, 16);
    delay = wcstol(argv[4], NULL, 10);
    sendinput = !wcscmp(argv[5], L"sendinput");
    max_ms = wcstol(argv[6], NULL, 10);
    SetProcessDPIAware();
    timeBeginPeriod(1);
    AllowSetForegroundWindow(ASFW_ANY);
    cx = GetSystemMetrics(SM_CXSCREEN) / 2;
    cy = GetSystemMetrics(SM_CYSCREEN) / 2;
    if (image) swprintf(cmd, 4096, L"\"%ls\" \"%ls\"", argv[1], image);
    else swprintf(cmd, 4096, L"\"%ls\"", argv[1]);
    {
        WCHAR d[256];
        HWND launcher = launcher_foreground();
        describe_hwnd(GetForegroundWindow(), d, 256);
        printf("launcher_foreground=%d foreground=%ls\n", GetForegroundWindow() == launcher, d);
    }
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&t0);
    if (!CreateProcessW(argv[1], cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        printf("createprocess_failed=%lu\n", GetLastError());
        return 3;
    }
    if (argc > 7) {
        HANDLE f = CreateFileW(argv[7], GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL);
        if (f != INVALID_HANDLE_VALUE) CloseHandle(f);
    }
    pid = pi.dwProcessId;
    screen = GetDC(NULL);
    printf("start image=%ls delay_ms=%ld key=%ls screen=%dx%d pid=%lu\n",
           image ? image : L"-", delay, argv[5], cx * 2, cy * 2, pid);
    stop_at = max_ms;
    for (;;) {
        long t = now_ms();
        int i, vis_conf = 0;
        size_t len = 0;
        HWND fg, under;
        COLORREF px;

        if (WaitForSingleObject(pi.hProcess, 0) == WAIT_OBJECT_0) {
            exit_ms = t;
            printf("%6ld exit\n", t);
            break;
        }
        nwins = 0;
        EnumWindows(collect, 0);
        cur[0] = 0;
        for (i = 0; i < nwins; i++) {
            struct win *w = &wins[i];
            if (w->visible)
                len += swprintf(cur + len, 8192 - len, L" %ls[%ld,%ld,%ld,%ld]", w->cls,
                                w->rect.left, w->rect.top, w->rect.right, w->rect.bottom);
            if (w->visible && first_fullscreen < 0 && wcsstr(w->cls, L"TFullScreenWindow"))
                first_fullscreen = t;
            if (w->visible && first_tform < 0 && !wcscmp(w->cls, L"TForm"))
                first_tform = t;
            if (w->visible && wcsstr(w->cls, L"TMessageWithNoMore")) vis_conf = 1;
            if (!w->visible && wcsstr(w->cls, L"TMessageWithNoMore") && confirm_ms < 0 && esc_ms >= 0)
                vis_conf = 2;  /* created but hidden (Wine, #40) still means Esc was handled */
            if (len > 7900) break;
        }
        { int hidden = 0;
          for (i = 0; i < nwins; i++) hidden += !wins[i].visible;
          swprintf(cur + len, 8192 - len, L" | hidden=%d", hidden); }
        if (wcscmp(cur, prev_wins)) {
            printf("%6ld windows:%ls\n", t, cur);
            wcscpy(prev_wins, cur);
        }
        fg = GetForegroundWindow();
        describe_hwnd(fg, fgdesc, 256);
        if (wcscmp(fgdesc, prev_fg)) {
            printf("%6ld foreground %ls\n", t, fgdesc);
            wcscpy(prev_fg, fgdesc);
        }
        if (first_image < 0) {
            DWORD owner = 0;
            under = WindowFromPoint((POINT){cx, cy});
            GetWindowThreadProcessId(under ? GetAncestor(under, GA_ROOT) : NULL, &owner);
            px = GetPixel(screen, cx, cy);
            if (px != CLR_INVALID && near_colour(px, colour) && owner == pid) {
                first_image = t;
                describe_hwnd(GetAncestor(under, GA_ROOT), img_win, 256);
                printf("%6ld image_visible centre=%06lx window=%ls\n", t,
                       (unsigned long)((GetRValue(px) << 16) | (GetGValue(px) << 8) | GetBValue(px)), img_win);
            }
        }
        if (vis_conf && confirm_ms < 0 && esc_ms >= 0) {
            confirm_ms = t;
            printf("%6ld confirmation %s\n", t, vis_conf == 1 ? "visible" : "hidden");
            stop_at = t + 300;
        }
        if (sendinput && esc_ms < 0 && delay >= 0 && t >= delay) {
            wcscpy(fg_at_esc, fgdesc);
            send_esc();
            esc_ms = now_ms();
            printf("%6ld esc_sent foreground=%ls\n", esc_ms, fg_at_esc);
            if (stop_at > esc_ms + 4000) stop_at = esc_ms + 4000;
        }
        if (!sendinput && delay >= 0 && esc_ms < 0 && t >= delay) {  /* key sent from outside */
            esc_ms = delay;
            if (stop_at > delay + 4000) stop_at = delay + 4000;
        }
        if (t >= stop_at) break;
        fflush(stdout);
        pump_sleep(t < 4000 ? 40 : 90);
    }
    printf("result delay_ms=%ld esc_ms=%ld fg_at_esc=%ls first_image_ms=%ld image_window=%ls "
           "tform_visible_ms=%ld fullscreen_visible_ms=%ld exit_ms=%ld confirm_ms=%ld outcome=%s\n",
           delay, esc_ms, fg_at_esc, first_image, img_win, first_tform, first_fullscreen,
           exit_ms, confirm_ms,
           delay < 0 ? "observe" : exit_ms >= 0 ? "exit" : confirm_ms >= 0 ? "confirm" : "ignored");
    fflush(stdout);
    ReleaseDC(NULL, screen);
    if (exit_ms < 0) {
        TerminateProcess(pi.hProcess, 0);
        WaitForSingleObject(pi.hProcess, 5000);
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    timeEndPeriod(1);
    return 0;
}
