/* VerInstallFileA/W live in Wine's own version.dll, which a proxy named
 * version.dll cannot forward to. Installers use them; the target apps do not.
 * Report failure without touching files. */
#include <windows.h>
#include <winver.h>

DWORD WINAPI VerInstallFileA(DWORD flags, LPSTR src, LPSTR dst, LPSTR srcdir, LPSTR dstdir, LPSTR curdir,
                             LPSTR tmp, PUINT tmplen)
{
    return VIF_CANNOTREADSRC;
}

DWORD WINAPI VerInstallFileW(DWORD flags, LPWSTR src, LPWSTR dst, LPWSTR srcdir, LPWSTR dstdir, LPWSTR curdir,
                             LPWSTR tmp, PUINT tmplen)
{
    return VIF_CANNOTREADSRC;
}
