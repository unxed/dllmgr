#include <windows.h>
#include <stdio.h>
int wmain(int argc, WCHAR **argv)
{
    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    WCHAR cmd[1024];
    swprintf(cmd, 1024, L"\"%ls\" %ls", argv[1], argv[2]);
    if (!CreateProcessW(argv[1], cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        printf("CreateProcess failed %lu\n", GetLastError());
        return 1;
    }
    WaitForSingleObject(pi.hProcess, 10000);
    DWORD code = 0; GetExitCodeProcess(pi.hProcess, &code);
    printf("started, exit=%lu\n", code);
    return 0;
}
