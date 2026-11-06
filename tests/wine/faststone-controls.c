/* Behavioral probes for WineHQ 48872 and the wheel part of 59251.
 * Run unchanged on Windows and Wine; the log is the oracle for backports. */
#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <commctrl.h>
#include <uxtheme.h>
#include <stdio.h>

static HWND parent;
static HIMAGELIST images;

static HWND listview(DWORD style, int width, int height, const char *text, int count)
{
    HWND lv = CreateWindowA(WC_LISTVIEWA, "", WS_CHILD | WS_VISIBLE | LVS_SHAREIMAGELISTS | style,
                            0, 0, width, height, parent, NULL, GetModuleHandleA(NULL), NULL);
    LVITEMA item = {0};
    int i;
    SetWindowTheme(lv, L"", L"");
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
    RECT label = {LVIR_LABEL}, selection = {LVIR_SELECTBOUNDS};
    LVITEMA item = {0};
    HDC dc;
    int x, y, painted = 0;
    SendMessageA(lv, LVM_GETITEMRECT, 0, (LPARAM)&label);
    SendMessageA(lv, LVM_GETITEMRECT, 0, (LPARAM)&selection);
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
    DestroyWindow(lv);
}

static void wheel_probe(DWORD view, DWORD align, int delta, int keys)
{
    HWND lv = listview(view | align | LVS_AUTOARRANGE, 400, 150, "item", 200);
    int h0 = GetScrollPos(lv, SB_HORZ), v0 = GetScrollPos(lv, SB_VERT);
    SendMessageA(lv, WM_MOUSEWHEEL, MAKEWPARAM(keys, delta), 0);
    printf("wheel view=%lu align=%lu delta=%d keys=%d: h=%d->%d v=%d->%d\n",
           view, align, delta, keys, h0, GetScrollPos(lv, SB_HORZ), v0, GetScrollPos(lv, SB_VERT));
    DestroyWindow(lv);
}

int main(void)
{
    INITCOMMONCONTROLSEX init = {sizeof(init), ICC_LISTVIEW_CLASSES};
    HBITMAP bitmap;
    HDC dc, mem;
    RECT rect = {0, 0, 32, 32};
    HBRUSH brush = CreateSolidBrush(RGB(0,180,0));
    int i;
    const int deltas[] = {0, -60, -120, -240};
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
    ImageList_Destroy(images); DestroyWindow(parent);
    return 0;
}
