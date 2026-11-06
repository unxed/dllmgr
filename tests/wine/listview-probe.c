#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdint.h>
#include "listview-probe.h"

struct observation
{
    HANDLE process;
    DWORD pid;
    unsigned controls;
};

static BOOL listview_message(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam, DWORD_PTR *result)
{
    return !!SendMessageTimeoutW(hwnd, msg, wparam, lparam, SMTO_ABORTIFHUNG | SMTO_BLOCK, 250, result);
}

struct item32
{
    UINT mask;
    INT item, subitem;
    UINT state, state_mask;
    UINT text;
    INT text_capacity;
};

struct item_probe
{
    union
    {
        RECT rect;
        LVITEMW native;
        struct item32 wow64;
    } value;
    WCHAR text[256];
};

static BOOL item_rectangles(HWND hwnd, HANDLE process, unsigned index, struct item_probe *remote, BOOL wow64)
{
    static const char *const names[] = {"bounds", "icon", "label", "select"};
    unsigned mode;
    for (mode = LVIR_BOUNDS; mode <= LVIR_SELECTBOUNDS; ++mode)
    {
        RECT rect = {mode, 0, 0, 0};
        DWORD_PTR result;
        if (!WriteProcessMemory(process, &remote->value.rect, &rect, sizeof(rect), NULL))
        {
            printf("  item %u: cannot initialize remote RECT (error %lu)\n", index, GetLastError());
            return TRUE;
        }
        if (!listview_message(hwnd, LVM_GETITEMRECT, index, (LPARAM)&remote->value.rect, &result))
        {
            printf("  item %u: LVM_GETITEMRECT timed out (error %lu)\n", index, GetLastError());
            return FALSE;
        }
        if (result && ReadProcessMemory(process, &remote->value.rect, &rect, sizeof(rect), NULL))
            printf("  item %u %s=%ld,%ld,%ld,%ld\n", index, names[mode],
                   rect.left, rect.top, rect.right, rect.bottom);
    }
    {
        struct item_probe request = {0};
        DWORD_PTR result;
        if (wow64)
        {
            request.value.wow64.text = (UINT)(uintptr_t)remote->text;
            request.value.wow64.text_capacity = ARRAYSIZE(request.text);
        }
        else
        {
            request.value.native.pszText = remote->text;
            request.value.native.cchTextMax = ARRAYSIZE(request.text);
        }
        if (WriteProcessMemory(process, remote, &request, sizeof(request), NULL))
        {
            if (!listview_message(hwnd, LVM_GETITEMTEXTW, index, (LPARAM)remote, &result))
            {
                printf("  item %u: LVM_GETITEMTEXTW timed out (error %lu)\n", index, GetLastError());
                return FALSE;
            }
            printf("  item %u label_chars=%u\n", index, (unsigned)result);
        }
    }
    return TRUE;
}

static BOOL CALLBACK inspect_control(HWND hwnd, LPARAM param)
{
    struct observation *probe = (struct observation *)param;
    DWORD pid;
    WCHAR name[64], real_name[64] = {0};
    DWORD_PTR count, selected, result;
    struct item_probe *remote;
    RECT rect;
    unsigned i;
    BOOL completed = TRUE, wow64 = FALSE;

    GetWindowThreadProcessId(hwnd, &pid);
    if (pid != probe->pid || !IsWindowVisible(hwnd)) return TRUE;
    if (!GetClassNameW(hwnd, name, ARRAYSIZE(name))) return TRUE;
    RealGetWindowClassW(hwnd, real_name, ARRAYSIZE(real_name));
    if (lstrcmpiW(name, L"TTntListView") && lstrcmpiW(name, L"TTntListView.UnicodeClass") &&
        lstrcmpiW(name, WC_LISTVIEWW) &&
        lstrcmpiW(real_name, WC_LISTVIEWW)) return TRUE;
    if (!GetWindowRect(hwnd, &rect)) return TRUE;
    ++probe->controls;
    if (!listview_message(hwnd, LVM_GETITEMCOUNT, 0, 0, &count))
    {
        printf("  listview hwnd=%p class='%ls' item count unavailable\n", hwnd, name);
        return TRUE;
    }
    printf("  listview hwnd=%p class='%ls' real_class='%ls' style=%08lx "
           "screen=%ld,%ld,%ld,%ld count=%u\n",
           hwnd, name, real_name, GetWindowLongW(hwnd, GWL_STYLE),
           rect.left, rect.top, rect.right, rect.bottom, (unsigned)count);
    if (listview_message(hwnd, LVM_GETITEMSPACING, FALSE, 0, &result))
        printf("  icon_spacing=%u,%u\n", LOWORD(result), HIWORD(result));
    if (!count) return TRUE;

    remote = VirtualAllocEx(probe->process, NULL, 7 * sizeof(*remote), MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!remote)
    {
        printf("  remote geometry buffer unavailable (error %lu)\n", GetLastError());
        return TRUE;
    }

    IsWow64Process(probe->process, &wow64);
    if (sizeof(void *) == 4) wow64 = FALSE;
    if (wow64 && (uintptr_t)(remote + 7) > UINT32_MAX)
    {
        printf("  remote geometry buffer outside the 32-bit address space\n");
        VirtualFreeEx(probe->process, remote, 0, MEM_RELEASE);
        return TRUE;
    }
    for (i = 0; completed && i < count && i < 6; ++i)
        completed = item_rectangles(hwnd, probe->process, i, remote + i, wow64);
    if (completed && listview_message(hwnd, LVM_GETNEXTITEM, (WPARAM)-1, LVNI_SELECTED, &selected) &&
        selected >= i && selected < count)
        completed = item_rectangles(hwnd, probe->process, (unsigned)selected, remote + i, wow64);

    /* A timed-out message might still use the allocation. The target owns it until exit. */
    if (completed) VirtualFreeEx(probe->process, remote, 0, MEM_RELEASE);

    if (listview_message(hwnd, LVM_GETVIEW, 0, 0, &result))
        printf("  view=%u\n", (unsigned)result);
    return TRUE;
}

static BOOL CALLBACK inspect_top_level(HWND hwnd, LPARAM param)
{
    struct observation *probe = (struct observation *)param;
    DWORD pid;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == probe->pid && IsWindowVisible(hwnd))
    {
        inspect_control(hwnd, param);
        EnumChildWindows(hwnd, inspect_control, param);
    }
    return TRUE;
}

void observe_listviews(const char *stage, HANDLE process, DWORD pid)
{
    struct observation probe = {process, pid, 0};
    printf("listview geometry: %s\n", stage);
    EnumWindows(inspect_top_level, (LPARAM)&probe);
    printf("  visible listviews=%u\n", probe.controls);
    fflush(stdout);
}
