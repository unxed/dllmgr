#include <windows.h>
#include <stdio.h>
int main(void)
{
    HMODULE m = LoadLibraryA("msimg32.dll");
    volatile DWORD *p = (DWORD *)((BYTE *)m + 0x1000);
    printf("version %lu, msimg32 at %p\n", GetFileVersionInfoSizeA("kernel32.dll", NULL), m); fflush(stdout);
    FreeLibrary(m);
    return (int)*p;
}
