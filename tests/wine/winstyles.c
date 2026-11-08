/* Public-API observer: list visible top-level windows with class, title, styles,
 * rect, window-region type and layered attributes. Used for #36 (Photoshop
 * splash) to see which Wine path the splash takes; no input, no hooks.
 * Usage: winstyles.exe [repeat_count] [interval_ms]
 * Build: i686-w64-mingw32-gcc -O2 -Wall -o winstyles.exe winstyles.c -lgdi32 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

static BOOL CALLBACK show(HWND hwnd, LPARAM lparam)
{
    char cls[128], title[128];
    RECT rect;
    HRGN rgn = CreateRectRgn(0, 0, 0, 0);
    int rgn_type;
    COLORREF key = 0;
    BYTE alpha = 0;
    DWORD flags = 0, pid = 0;
    LONG ex = GetWindowLongW(hwnd, GWL_EXSTYLE);

    if (!IsWindowVisible(hwnd)) { DeleteObject(rgn); return TRUE; }
    GetClassNameA(hwnd, cls, sizeof(cls));
    GetWindowTextA(hwnd, title, sizeof(title));
    GetWindowRect(hwnd, &rect);
    GetWindowThreadProcessId(hwnd, &pid);
    rgn_type = GetWindowRgn(hwnd, rgn);
    if (ex & WS_EX_LAYERED) GetLayeredWindowAttributes(hwnd, &key, &alpha, &flags);
    printf("hwnd=%p pid=%lu class=\"%s\" title=\"%s\" style=%08lx ex=%08lx rect=%ld,%ld-%ld,%ld rgn=%d"
           " layered=%d key=%06lx alpha=%u lwa=%lu\n",
           (void *)hwnd, pid, cls, title, (unsigned long)GetWindowLongW(hwnd, GWL_STYLE), (unsigned long)ex,
           rect.left, rect.top, rect.right, rect.bottom, rgn_type, !!(ex & WS_EX_LAYERED),
           (unsigned long)key, alpha, flags);
    DeleteObject(rgn);
    return TRUE;
}

int main(int argc, char **argv)
{
    int count = argc > 1 ? atoi(argv[1]) : 1, interval = argc > 2 ? atoi(argv[2]) : 500;
    for (int i = 0; i < count; i++) {
        printf("--- snapshot %d t=%lu\n", i, GetTickCount());
        EnumWindows(show, 0);
        fflush(stdout);
        Sleep(interval);
    }
    return 0;
}
