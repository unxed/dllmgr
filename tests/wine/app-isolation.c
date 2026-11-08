#define UNICODE
#define _UNICODE
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static int check(const WCHAR *name, const WCHAR *variable, int private_expected)
{
    WCHAR actual[32768], expected[32768];
    HMODULE module = LoadLibraryW(name);
    int match;
    if (!module || !GetModuleFileNameW(module, actual, 32768)) return 1;
    if (!GetEnvironmentVariableW(variable, expected, 32768)) return 2;
    match = !wcsicmp(actual, expected);
    wprintf(L"%ls: %ls (%ls)\n", name, actual, match ? L"private" : L"stock");
    return match != private_expected;
}

int wmain(int argc, WCHAR **argv)
{
    int failures, expect_private = argc > 1 && !wcscmp(argv[1], L"private");
    failures = check(L"gdiplus.dll", L"DLLMGR_GDIPLUS", expect_private);
    failures += check(L"comctl32.dll", L"DLLMGR_COMCTL32", expect_private);
    if (argc > 2)
    {
        STARTUPINFOW si = {sizeof(si)};
        PROCESS_INFORMATION pi;
        DWORD code = 1;
        WCHAR command[32768];
        swprintf(command, 32768, L"\"%ls\" stock", argv[2]);
        if (!CreateProcessW(argv[2], command, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) return 3;
        WaitForSingleObject(pi.hProcess, 30000);
        GetExitCodeProcess(pi.hProcess, &code);
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        failures += code != 0;
    }
    return failures ? 1 : 0;
}
