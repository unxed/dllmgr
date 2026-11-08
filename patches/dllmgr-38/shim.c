/* dllmgr issue 38: SetWindowFeedbackSetting / GetWindowFeedbackSetting for
 * Wine versions whose user32 lacks the exports (Wine 11.0, master as of
 * 2026-11). Public Win32 APIs only, no Wine changes; the Wine-side fix is
 * patches/dllmgr-38.patch.
 *
 * Delivered as a proxy DLL the application loads anyway (version.dll, see
 * build.sh). The loader binds an aborting stub to a missing import; before
 * the application runs, this DLL walks the import tables of all loaded
 * modules and of every module loaded later (LdrRegisterDllNotification),
 * finds the thunks named SetWindowFeedbackSetting / GetWindowFeedbackSetting
 * and writes its own implementations into them. It does nothing when user32
 * exports the functions (fixed Wine, Windows).
 *
 * Semantics: as measured on Windows by tests/wine/feedback-get.c (per window
 * and type, NULL config resets, unset reads FALSE with ret 0,
 * GWFS_INCLUDE_ANCESTORS walks the parents, last error untouched). Wine draws
 * no touch/pen feedback, so values only round-trip.
 * DLLMGR38_DEBUG=1: one stderr line per patched slot. DLLMGR38_OFF=1: off. */
#include <windows.h>
#include <winternl.h>
#include <psapi.h>
#include <stdio.h>
#include <wchar.h>

static int debug;
#define TRACE(...) do { if (debug) { fprintf(stderr, "dllmgr38: " __VA_ARGS__); fflush(stderr); } } while (0)

#ifndef GWFS_INCLUDE_ANCESTORS
#define GWFS_INCLUDE_ANCESTORS 1
#endif
#define FEEDBACK_FIRST 1  /* FEEDBACK_TOUCH_CONTACTVISUALIZATION */
#define FEEDBACK_LAST 11  /* FEEDBACK_GESTURE_PRESSANDTAP */

static void prop_name(UINT type, WCHAR *name)
{
    swprintf(name, 32, L"dllmgr_feedback_%u", type);
}

static BOOL WINAPI shim_set(HWND hwnd, UINT type, DWORD flags, UINT32 size, const void *config)
{
    WCHAR name[32];
    if (!IsWindow(hwnd)) {
        SetLastError(ERROR_INVALID_WINDOW_HANDLE);
        return FALSE;
    }
    if (type < FEEDBACK_FIRST || type > FEEDBACK_LAST || flags || (config ? size != sizeof(BOOL) : size)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    prop_name(type, name);
    if (!config) RemovePropW(hwnd, name);
    else SetPropW(hwnd, name, (HANDLE)(ULONG_PTR)(*(const BOOL *)config ? 2 : 1));
    return TRUE;
}

static BOOL WINAPI shim_get(HWND hwnd, UINT type, DWORD flags, UINT32 *size, void *config)
{
    WCHAR name[32];
    ULONG_PTR value = 0;
    HWND win = hwnd;
    DWORD error;

    if (!IsWindow(hwnd)) {
        SetLastError(ERROR_INVALID_WINDOW_HANDLE);
        return FALSE;
    }
    if (!size || type < FEEDBACK_FIRST || type > FEEDBACK_LAST || (flags & ~GWFS_INCLUDE_ANCESTORS)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    if (!config) {
        *size = sizeof(BOOL);
        return TRUE;
    }
    if (*size < sizeof(BOOL)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    prop_name(type, name);
    error = GetLastError();
    while (win && !(value = (ULONG_PTR)GetPropW(win, name)) && (flags & GWFS_INCLUDE_ANCESTORS))
        win = GetAncestor(win, GA_PARENT);
    SetLastError(error);
    *size = sizeof(BOOL);
    *(BOOL *)config = value == 2;
    return value != 0;
}

static const struct { const char *name; void *impl; } shims[] = {
    {"SetWindowFeedbackSetting", (void *)shim_set},
    {"GetWindowFeedbackSetting", (void *)shim_get},
};
static BOOL needed[2];

/* By name through OriginalFirstThunk (MSVC images have it); any import DLL
 * name, so API-set spellings of user32 are covered too. */
static void patch_module(HMODULE module)
{
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    IMAGE_IMPORT_DESCRIPTOR *desc;

    if (!dir->VirtualAddress || !dir->Size) return;
    for (desc = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir->VirtualAddress); desc->Name; desc++) {
        IMAGE_THUNK_DATA *names, *slots;
        if (!desc->OriginalFirstThunk) continue;
        names = (IMAGE_THUNK_DATA *)(base + desc->OriginalFirstThunk);
        slots = (IMAGE_THUNK_DATA *)(base + desc->FirstThunk);
        for (; names->u1.AddressOfData; names++, slots++) {
            IMAGE_IMPORT_BY_NAME *by_name;
            unsigned i;
            DWORD protect;
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal)) continue;
            by_name = (IMAGE_IMPORT_BY_NAME *)(base + names->u1.AddressOfData);
            for (i = 0; i < 2; i++) {
                if (!needed[i] || strcmp((char *)by_name->Name, shims[i].name)) continue;
                if (slots->u1.Function == (ULONG_PTR)shims[i].impl) continue;
                if (!VirtualProtect(&slots->u1.Function, sizeof(void *), PAGE_READWRITE, &protect)) continue;
                slots->u1.Function = (ULONG_PTR)shims[i].impl;
                VirtualProtect(&slots->u1.Function, sizeof(void *), protect, &protect);
                TRACE("patched %s in %p (%s)\n", shims[i].name, module, (char *)(base + desc->Name));
            }
        }
    }
}

/* LDR_DLL_NOTIFICATION_DATA.Loaded: Flags, FullDllName, BaseDllName, DllBase, SizeOfImage */
typedef struct {
    ULONG flags;
    const UNICODE_STRING *full_name, *base_name;
    void *base;
    ULONG size;
} loaded_data;
typedef void (CALLBACK *notify_fn)(ULONG reason, const loaded_data *data, void *context);
typedef NTSTATUS (NTAPI *register_fn)(ULONG flags, notify_fn callback, void *context, void **cookie);

static void CALLBACK on_load(ULONG reason, const loaded_data *data, void *context)
{
    if (reason == 1 /* LDR_DLL_NOTIFICATION_REASON_LOADED */) patch_module((HMODULE)data->base);
}

static void patch_all(void)
{
    HMODULE user32 = GetModuleHandleA("user32.dll"), modules[1024];
    DWORD bytes = 0, i;
    BOOL any = FALSE;
    void *cookie;
    register_fn reg;

    for (i = 0; i < 2; i++) any |= needed[i] = !user32 || !GetProcAddress(user32, shims[i].name);
    if (!any) return;
    if (K32EnumProcessModules(GetCurrentProcess(), modules, sizeof(modules), &bytes))
        for (i = 0; i < bytes / sizeof(HMODULE) && i < 1024; i++) patch_module(modules[i]);
    reg = (register_fn)GetProcAddress(GetModuleHandleA("ntdll.dll"), "LdrRegisterDllNotification");
    if (reg) reg(0, on_load, NULL, &cookie);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, void *reserved)
{
    if (reason != DLL_PROCESS_ATTACH || GetEnvironmentVariableA("DLLMGR38_OFF", NULL, 0)) return TRUE;
    debug = GetEnvironmentVariableA("DLLMGR38_DEBUG", NULL, 0) != 0;
    patch_all();
    return TRUE;
}
