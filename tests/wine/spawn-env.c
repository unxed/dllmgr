/* #27: CreateProcessW of a Unix program from Wine. Prints WaitForSingleObject
 * result and exit code; sets DLLMGR_T=1 first to test env propagation.
 * wine spawn-env.exe 'Z:\\path\\script' 'args' (see docs/tasks/27-every-launch-path.md) */
#include <windows.h>
#include <stdio.h>
/* argv[1] = app (Windows path), rest of the command line passed on; sets DLLMGR_T=1 */
int wmain(int argc, WCHAR **argv)
{
    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    WCHAR cmd[2048];
    DWORD code = 12345, w;
    swprintf(cmd, 2048, L"\"%ls\" %ls", argv[1], argc > 2 ? argv[2] : L"");
    SetEnvironmentVariableW(L"DLLMGR_T", L"1");
    if (!CreateProcessW(argv[1], cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        printf("CreateProcess failed %lu\n", GetLastError()); return 1;
    }
    w = WaitForSingleObject(pi.hProcess, 5000);
    GetExitCodeProcess(pi.hProcess, &code);
    printf("wait=%lu exit=%lu\n", w, code);
    return 0;
}
