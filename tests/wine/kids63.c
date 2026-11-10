#include <windows.h>
#include <stdio.h>
#include <string.h>
static BOOL CALLBACK cb(HWND h, LPARAM l)
{
    char cls[64]; RECT r; COMBOBOXINFO ci = {sizeof(ci)};
    GetClassNameA(h, cls, sizeof(cls)); GetWindowRect(h, &r);
    if (!strstr(cls, "Combo") && !strstr(cls, "Edit") && (r.top > 190 || r.bottom < 184)) return TRUE;
    printf("%p %-20s parent=%p (%ld,%ld)-(%ld,%ld) style=%08lx ex=%08lx vis=%d\n", h, cls, GetParent(h),
           r.left, r.top, r.right, r.bottom, GetWindowLongA(h, GWL_STYLE), GetWindowLongA(h, GWL_EXSTYLE), IsWindowVisible(h));
    if (GetComboBoxInfo(h, &ci))
        printf("   combo item (%ld,%ld)-(%ld,%ld) button (%ld,%ld)-(%ld,%ld) edit=%p\n", ci.rcItem.left, ci.rcItem.top,
               ci.rcItem.right, ci.rcItem.bottom, ci.rcButton.left, ci.rcButton.top, ci.rcButton.right, ci.rcButton.bottom, ci.hwndItem);
    return TRUE;
}
int main(void)
{
    HWND top = FindWindowA("FastStoneImageViewerMainForm.UnicodeClass", NULL);
    if (!top) top = GetForegroundWindow();
    printf("top %p\n", top);
    EnumChildWindows(top, cb, 0);
    return 0;
}
