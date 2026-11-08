/* Issue #38: learn GetWindowFeedbackSetting/SetWindowFeedbackSetting semantics
 * on Windows (reference for a Wine implementation). Functions are resolved at
 * runtime so the probe also runs where they are missing. One line per case:
 *   case=<name> ret=<0|1> error=<code> size=<n> value=<v>
 * Build: x86_64-w64-mingw32-gcc -O2 -Wall -o feedback-get.exe feedback-get.c
 * -DSTATIC_IMPORT: import both functions statically like Photoshop 2024, also
 * import version.dll (so a version.dll proxy such as patches/dllmgr-38 loads)
 * and at the end call them from feedback-late.dll loaded with LoadLibrary:
 *   x86_64-w64-mingw32-gcc -O2 -Wall -DSTATIC_IMPORT -o feedback-static.exe feedback-get.c -lversion
 *   x86_64-w64-mingw32-gcc -O2 -Wall -shared -DLATE_DLL -o feedback-late.dll feedback-get.c
 * On a Wine without the exports (and without the shim) feedback-static.exe
 * aborts at the first call with "Unimplemented function". */
#include <windows.h>
#include <stdio.h>

#ifdef LATE_DLL
__declspec(dllexport) BOOL late_set(HWND hwnd)
{
    BOOL on = TRUE;
    return SetWindowFeedbackSetting(hwnd, FEEDBACK_TOUCH_TAP, 0, sizeof(on), &on);
}
#else

typedef BOOL (WINAPI *set_fn)(HWND, FEEDBACK_TYPE, DWORD, UINT32, const void *);
typedef BOOL (WINAPI *get_fn)(HWND, FEEDBACK_TYPE, DWORD, UINT32 *, void *);
static set_fn pset;
static get_fn pget;

static void get_case(const char *name, HWND hwnd, FEEDBACK_TYPE type, DWORD flags, UINT32 size_in, BOOL use_buffer)
{
    UINT32 size = size_in;
    BOOL value = 0x55;
    BOOL ret;
    SetLastError(0xdeadbeef);
    ret = pget(hwnd, type, flags, &size, use_buffer ? &value : NULL);
    printf("case=%s ret=%d error=%lu size=%u value=%d\n", name, ret, GetLastError(), size, value);
}

static void set_case(const char *name, HWND hwnd, FEEDBACK_TYPE type, DWORD flags, UINT32 size, const void *config)
{
    BOOL ret;
    SetLastError(0xdeadbeef);
    ret = pset(hwnd, type, flags, size, config);
    printf("case=%s ret=%d error=%lu\n", name, ret, GetLastError());
}

int main(void)
{
    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    HWND parent, child;
    BOOL off = FALSE, on = TRUE;

    pset = (set_fn)GetProcAddress(user32, "SetWindowFeedbackSetting");
    pget = (get_fn)GetProcAddress(user32, "GetWindowFeedbackSetting");
    printf("exports set=%d get=%d\n", !!pset, !!pget);
#ifdef STATIC_IMPORT
    GetFileVersionInfoSizeW(L"", NULL);
    pset = SetWindowFeedbackSetting;
    pget = GetWindowFeedbackSetting;
#endif
    if (!pset || !pget) return 0;

    parent = CreateWindowExW(0, L"STATIC", L"parent", WS_POPUP, 0, 0, 50, 50, NULL, NULL, NULL, NULL);
    child = CreateWindowExW(0, L"STATIC", L"child", WS_CHILD, 0, 0, 10, 10, parent, NULL, NULL, NULL);

    get_case("get_default", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
    get_case("get_default_ancestors", child, FEEDBACK_TOUCH_TAP, GWFS_INCLUDE_ANCESTORS, sizeof(BOOL), TRUE);
    set_case("set_off", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(off), &off);
    get_case("get_after_set", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
    get_case("get_child_no_ancestors", child, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
    get_case("get_child_ancestors", child, FEEDBACK_TOUCH_TAP, GWFS_INCLUDE_ANCESTORS, sizeof(BOOL), TRUE);
    get_case("get_size_query", parent, FEEDBACK_TOUCH_TAP, 0, 0, FALSE);
    set_case("set_on", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(on), &on);
    get_case("get_after_on", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
    set_case("set_reset_null", parent, FEEDBACK_TOUCH_TAP, 0, 0, NULL);
    get_case("get_after_reset", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
    set_case("set_bad_size", parent, FEEDBACK_TOUCH_TAP, 0, 1, &off);
    set_case("set_bad_type0", parent, (FEEDBACK_TYPE)0, 0, sizeof(off), &off);
    set_case("set_bad_type99", parent, (FEEDBACK_TYPE)99, 0, sizeof(off), &off);
    set_case("set_bad_flags", parent, FEEDBACK_TOUCH_TAP, 1, sizeof(off), &off);
    set_case("set_bad_hwnd", (HWND)0xdead, FEEDBACK_TOUCH_TAP, 0, sizeof(off), &off);
    set_case("set_null_hwnd", NULL, FEEDBACK_TOUCH_TAP, 0, sizeof(off), &off);
    get_case("get_bad_hwnd", (HWND)0xdead, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
#ifdef STATIC_IMPORT
    {
        HMODULE late = LoadLibraryW(L"feedback-late.dll");
        BOOL (*late_set)(HWND) = late ? (void *)GetProcAddress(late, "late_set") : NULL;
        if (late_set) {
            BOOL ret = late_set(parent);
            get_case("late_get_after_set", parent, FEEDBACK_TOUCH_TAP, 0, sizeof(BOOL), TRUE);
            printf("case=late_set ret=%d\n", ret);
        } else printf("case=late_set missing\n");
    }
#endif
    DestroyWindow(parent);
    return 0;
}
#endif
