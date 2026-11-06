/* Passive, bounded cursor sampling: no window, input injection or settings writes.
 * Build: i686-w64-mingw32-gcc -O2 -Wall -Wextra cursor-probe.c -o cursor-probe.exe -luser32
 * Run: cursor-probe.exe --seconds 15 --interval-ms 20
 * Changes only this helper thread's DPI context, restoring it before each print.
 * Wine 11 GetPhysicalCursorPos aliases GetCursorPos; it is not a physical check.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef HANDLE (WINAPI *set_thread_dpi_fn)(HANDLE);

static ULONGLONG unix_ms(void)
{
    FILETIME value;
    ULARGE_INTEGER ticks;
    GetSystemTimeAsFileTime(&value);
    ticks.LowPart = value.dwLowDateTime;
    ticks.HighPart = value.dwHighDateTime;
    return (ticks.QuadPart - 116444736000000000ULL) / 10000;
}

static int number(const char *text, int min, int max)
{
    char *end;
    long value = strtol(text, &end, 10);
    return *text && !*end && value >= min && value <= max ? (int)value : -1;
}

int main(int argc, char **argv)
{
    int seconds = 15, interval = 20, i;
    ULONGLONG start;
    LARGE_INTEGER frequency;
    set_thread_dpi_fn set_dpi;
    for (i = 1; i < argc; i++)
    {
        if (!strcmp(argv[i], "--help"))
        {
            puts("cursor-probe.exe [--seconds 1..60] [--interval-ms 10..1000]\n"
                 "No visible window, mouse movement, focus changes or settings writes.\n"
                 "All rectangles/info use per-monitor-v2; unaware coordinates are separate.");
            return 0;
        }
        if (i + 1 < argc && !strcmp(argv[i], "--seconds"))
            seconds = number(argv[++i], 1, 60);
        else if (i + 1 < argc && !strcmp(argv[i], "--interval-ms"))
            interval = number(argv[++i], 10, 1000);
        else
        {
            fputs("Unknown or incomplete option; use --help\n", stderr);
            return 2;
        }
    }
    if (seconds < 1 || interval < 10)
    {
        fputs("Require seconds 1..60 and interval-ms 10..1000\n", stderr);
        return 2;
    }
    set_dpi = (set_thread_dpi_fn)(void *)GetProcAddress(GetModuleHandleA("user32.dll"),
                                                      "SetThreadDpiAwarenessContext");
    if (!set_dpi)
    {
        fputs("SetThreadDpiAwarenessContext unavailable; cannot label coordinates reliably\n", stderr);
        return 1;
    }
    QueryPerformanceFrequency(&frequency);
    printf("{\"kind\":\"start\",\"unix_ms\":%llu,\"seconds\":%d,"
           "\"interval_ms\":%d,\"qpc_frequency\":%lld,"
           "\"info_context\":\"per-monitor-v2\"}\n",
           unix_ms(), seconds, interval, frequency.QuadPart);
    fflush(stdout);
    start = GetTickCount64();
    while (GetTickCount64() - start < (ULONGLONG)seconds * 1000)
    {
        POINT aware = {0}, unaware = {0};
        RECT clip = {0};
        CURSORINFO info = {0};
        int mouse[3] = {0}, speed = 0;
        BOOL pos_ok, unaware_ok, clip_ok, info_ok, mouse_ok, speed_ok;
        HANDLE original, previous;
        LARGE_INTEGER counter;
        ULONGLONG timestamp;
        original = set_dpi((HANDLE)(INT_PTR)-4); /* PER_MONITOR_AWARE_V2 */
        if (!original)
        {
            fputs("Cannot enter per-monitor-v2 context\n", stderr);
            return 1;
        }
        QueryPerformanceCounter(&counter);
        timestamp = unix_ms();
        info.cbSize = sizeof(info);
        pos_ok = GetCursorPos(&aware);
        clip_ok = GetClipCursor(&clip);
        info_ok = GetCursorInfo(&info);
        mouse_ok = SystemParametersInfoA(SPI_GETMOUSE, 0, mouse, 0);
        speed_ok = SystemParametersInfoA(SPI_GETMOUSESPEED, 0, &speed, 0);
        previous = set_dpi((HANDLE)(INT_PTR)-1); /* UNAWARE */
        unaware_ok = previous ? GetCursorPos(&unaware) : FALSE;
        if (!set_dpi(original))
        {
            fputs("Cannot restore helper DPI context\n", stderr);
            return 1;
        }
        printf("{\"kind\":\"cursor\",\"unix_ms\":%llu,\"qpc\":%lld,"
               "\"aware_ok\":%d,\"aware\":[%ld,%ld],"
               "\"unaware_ok\":%d,\"unaware\":[%ld,%ld],"
               "\"clip_ok\":%d,\"clip\":[%ld,%ld,%ld,%ld],"
               "\"info_ok\":%d,\"cursor_flags\":%lu,\"cursor_handle\":\"%p\","
               "\"cursor_info_pos\":[%ld,%ld],"
               "\"mouse_ok\":%d,\"mouse\":[%d,%d,%d],\"speed_ok\":%d,\"speed\":%d}\n",
               timestamp, counter.QuadPart, pos_ok, aware.x, aware.y,
               unaware_ok, unaware.x, unaware.y, clip_ok,
               clip.left, clip.top, clip.right, clip.bottom,
               info_ok, info.flags, (void *)info.hCursor, info.ptScreenPos.x, info.ptScreenPos.y,
               mouse_ok, mouse[0], mouse[1], mouse[2], speed_ok, speed);
        fflush(stdout);
        {
            ULONGLONG elapsed = GetTickCount64() - start;
            ULONGLONG duration = (ULONGLONG)seconds * 1000;
            if (elapsed < duration)
                Sleep((DWORD)(duration - elapsed < (ULONGLONG)interval ?
                              duration - elapsed : (ULONGLONG)interval));
        }
    }
    printf("{\"kind\":\"stop\",\"unix_ms\":%llu}\n", unix_ms());
    return 0;
}
