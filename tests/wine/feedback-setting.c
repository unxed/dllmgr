/* Issue #38 / wine-adobe-installers#6: Photoshop 2024 aborts on
 * USER32.SetWindowFeedbackSetting. Imports the function statically like the
 * application does: on a Wine without the export the loader binds an
 * aborting stub and this program dies with "Unimplemented function ...".
 * Prints: set_feedback ret=N error=E  (expected with the fix: ret=1)
 *         set_feedback_badwnd ret=0 error=1400 (ERROR_INVALID_WINDOW_HANDLE)
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o feedback-setting.exe feedback-setting.c -luser32 */
#include <windows.h>
#include <stdio.h>

int main(void)
{
    HWND hwnd = CreateWindowExW(0, L"STATIC", L"feedback", WS_POPUP, 0, 0, 10, 10, NULL, NULL, NULL, NULL);
    BOOL off = FALSE, ret;

    SetLastError(0xdeadbeef);
    ret = SetWindowFeedbackSetting(hwnd, FEEDBACK_TOUCH_CONTACTVISUALIZATION, 0, sizeof(off), &off);
    printf("set_feedback ret=%d error=%lu\n", ret, ret ? 0 : GetLastError());
    SetLastError(0xdeadbeef);
    ret = SetWindowFeedbackSetting((HWND)0xdead, FEEDBACK_TOUCH_CONTACTVISUALIZATION, 0, sizeof(off), &off);
    printf("set_feedback_badwnd ret=%d error=%lu\n", ret, GetLastError());
    DestroyWindow(hwnd);
    return 0;
}
