/* Behavioral probes for WineHQ 48872 and the wheel part of 59251.
 * Run unchanged on Windows and Wine; the log is the oracle for backports. */
#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <string.h>

static HWND parent;
static HIMAGELIST images;
static int check_label, check_wheel, check_position, failures;

static HWND listview(DWORD style, int width, int height, const char *text, int count)
{
    HWND lv = CreateWindowA(WC_LISTVIEWA, "", WS_CHILD | WS_VISIBLE | LVS_SHAREIMAGELISTS | style,
                            0, 0, width, height, parent, NULL, GetModuleHandleA(NULL), NULL);
    LVITEMA item = {0};
    int i;
    {
        static int printed;
        char path[MAX_PATH];
        if (!printed++) {
            GetModuleFileNameA((HMODULE)GetClassLongPtrA(lv,GCLP_HMODULE),path,sizeof(path));
            printf("list-view class module: %s\n",path);
        }
    }
    SendMessageA(lv, LVM_SETIMAGELIST, LVSIL_NORMAL, (LPARAM)images);
    SendMessageA(lv, LVM_SETIMAGELIST, LVSIL_SMALL, (LPARAM)images);
    SendMessageA(lv, LVM_SETBKCOLOR, 0, RGB(255,255,255));
    item.mask = LVIF_TEXT | LVIF_IMAGE;
    item.pszText = (char *)text;
    for (i = 0; i < count; i++)
    {
        item.iItem = i;
        SendMessageA(lv, LVM_INSERTITEMA, 0, (LPARAM)&item);
    }
    SendMessageA(lv, LVM_ARRANGE, LVA_DEFAULT, 0);
    UpdateWindow(lv);
    return lv;
}

static void label_probe(const char *text)
{
    HWND lv = listview(LVS_ICON | LVS_AUTOARRANGE, 400, 300, text, 1);
    RECT label = {LVIR_LABEL}, selection = {LVIR_SELECTBOUNDS}, icon = {LVIR_ICON};
    LVITEMA item = {0};
    HDC dc;
    int x, y, painted = 0;
    SendMessageA(lv, LVM_GETITEMRECT, 0, (LPARAM)&label);
    SendMessageA(lv, LVM_GETITEMRECT, 0, (LPARAM)&selection);
    SendMessageA(lv, LVM_GETITEMRECT, 0, (LPARAM)&icon);
    printf("icon text='%s': rect=(%ld,%ld,%ld,%ld)\n",text,icon.left,icon.top,icon.right,icon.bottom);
    printf("label text='%s': rect=(%ld,%ld,%ld,%ld) selection=(%ld,%ld,%ld,%ld)\n",
           text, label.left, label.top, label.right, label.bottom,
           selection.left, selection.top, selection.right, selection.bottom);
    item.stateMask = LVIS_SELECTED | LVIS_FOCUSED;
    item.state = LVIS_SELECTED | LVIS_FOCUSED;
    SendMessageA(lv, LVM_SETITEMSTATE, 0, (LPARAM)&item);
    SetFocus(lv);
    RedrawWindow(lv, NULL, NULL, RDW_ERASE | RDW_INVALIDATE | RDW_UPDATENOW);
    dc = GetDC(lv);
    for (y = label.top; y < label.bottom; y++)
        for (x = label.left; x < label.right; x++)
            if (GetPixel(dc, x, y) != RGB(255,255,255)) painted++;
    ReleaseDC(lv, dc);
    printf("label selected text='%s': painted pixels=%d\n", text, painted);
    if (check_label && !*text && (label.right <= label.left || painted)) failures++;
    DestroyWindow(lv);
}

static void wheel_probe(DWORD view, DWORD align, int delta, int keys)
{
    HWND lv = listview(view | align | LVS_AUTOARRANGE, 400, 150, "item", 200);
    DWORD scrollbars = GetWindowLongW(lv, GWL_STYLE);
    int h0 = GetScrollPos(lv, SB_HORZ), v0 = GetScrollPos(lv, SB_VERT);
    SendMessageA(lv, WM_MOUSEWHEEL, MAKEWPARAM(keys, delta), 0);
    printf("wheel view=%lu align=%lu delta=%d keys=%d scrollbars=%#lx: h=%d->%d v=%d->%d\n",
           view, align, delta, keys, scrollbars & (WS_HSCROLL | WS_VSCROLL),
           h0, GetScrollPos(lv, SB_HORZ), v0, GetScrollPos(lv, SB_VERT));
    if (check_wheel && view == LVS_ICON && align == LVS_ALIGNLEFT && !keys && delta == -120 &&
        GetScrollPos(lv, SB_HORZ) <= h0) failures++;
    DestroyWindow(lv);
}

static void position_probe(DWORD view)
{
    HWND lv = listview(view | LVS_ALIGNLEFT | LVS_AUTOARRANGE, 400, 150, "item", 200);
    POINT before, after;
    SendMessageA(lv, LVM_GETITEMPOSITION, 150, (LPARAM)&before);
    SendMessageA(lv, LVM_SCROLL, 300, 0);
    SendMessageA(lv, LVM_GETITEMPOSITION, 150, (LPARAM)&after);
    printf("position view=%lu: (%ld,%ld)->(%ld,%ld)\n", view, before.x, before.y, after.x, after.y);
    if (check_position && before.x != after.x) failures++;
    DestroyWindow(lv);
}

int main(int argc, char **argv)
{
    INITCOMMONCONTROLSEX init = {sizeof(init), ICC_LISTVIEW_CLASSES};
    HBITMAP bitmap;
    HDC dc, mem;
    RECT rect = {0, 0, 32, 32};
    HBRUSH brush = CreateSolidBrush(RGB(0,180,0));
    int i;
    const int deltas[] = {0, -60, -120, -240};
    for (i = 1; i < argc; i++)
    {
        if (!strcmp(argv[i], "--check-label")) check_label = 1;
        if (!strcmp(argv[i], "--check-wheel")) check_wheel = 1;
        if (!strcmp(argv[i], "--check-position")) check_position = 1;
    }
    InitCommonControlsEx(&init);
    parent = CreateWindowA("STATIC", "FastStone controls probe", WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                           0, 0, 500, 400, NULL, NULL, GetModuleHandleA(NULL), NULL);
    if (!parent) return 2;
    dc = GetDC(parent); mem = CreateCompatibleDC(dc);
    bitmap = CreateCompatibleBitmap(dc,32,32);
    SelectObject(mem,bitmap); FillRect(mem,&rect,brush);
    images = ImageList_Create(32,32,ILC_COLOR32,1,1);
    ImageList_Add(images,bitmap,NULL);
    DeleteDC(mem); ReleaseDC(parent,dc); DeleteObject(bitmap); DeleteObject(brush);
    label_probe(""); label_probe(" "); label_probe("filename.bmp");
    for (i = 0; i < sizeof(deltas)/sizeof(deltas[0]); i++)
    {
        wheel_probe(LVS_ICON,LVS_ALIGNLEFT,deltas[i],0);
        wheel_probe(LVS_SMALLICON,LVS_ALIGNLEFT,deltas[i],0);
        wheel_probe(LVS_ICON,LVS_ALIGNTOP,deltas[i],0);
    }
    wheel_probe(LVS_ICON,LVS_ALIGNLEFT,-120,MK_CONTROL);
    position_probe(LVS_ICON); position_probe(LVS_SMALLICON);
    ImageList_Destroy(images); DestroyWindow(parent);
    printf("Failures: %d\n", failures);
    return !!failures;
}
