/* twopen.exe [product]: list TWAIN sources through twain_32.dll and open/close the one
 * whose ProductName matches (default: the first); prints the results (#74 check) */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "twain.h"
typedef TW_UINT16 (WINAPI *DSMENTRY)(pTW_IDENTITY, pTW_IDENTITY, TW_UINT32, TW_UINT16, TW_UINT16, TW_MEMREF);
int main(int argc, char **argv)
{
    HMODULE dsm = LoadLibraryA("twain_32.dll");
    DSMENTRY entry = dsm ? (DSMENTRY)GetProcAddress(dsm, "DSM_Entry") : NULL;
    TW_IDENTITY app = {0}, src = {0}, pick = {0};
    HWND hwnd = CreateWindowA("STATIC", "tw", 0, 0, 0, 1, 1, 0, 0, 0, 0);
    TW_UINT16 rc; int n = 0, found = 0;
    if (!entry) { printf("no twain_32\n"); return 1; }
    app.Version.MajorNum = 1; app.ProtocolMajor = TWON_PROTOCOLMAJOR; app.ProtocolMinor = TWON_PROTOCOLMINOR;
    app.SupportedGroups = DG_CONTROL | DG_IMAGE; strcpy(app.ProductName, "twopen");
    rc = entry(&app, NULL, DG_CONTROL, DAT_PARENT, MSG_OPENDSM, (TW_MEMREF)&hwnd);
    printf("OPENDSM rc=%u\n", rc);
    for (rc = entry(&app, NULL, DG_CONTROL, DAT_IDENTITY, MSG_GETFIRST, &src); rc == TWRC_SUCCESS;
         rc = entry(&app, NULL, DG_CONTROL, DAT_IDENTITY, MSG_GETNEXT, &src)) {
        printf("source %d: %s / %s / %s\n", n++, src.Manufacturer, src.ProductFamily, src.ProductName);
        if (!found && (argc < 2 || !strcmp(src.ProductName, argv[1]))) { pick = src; found = 1; }
    }
    if (!found) { printf("no matching source\n"); return 2; }
    {
        DWORD t = GetTickCount();
        rc = entry(&app, NULL, DG_CONTROL, DAT_IDENTITY, MSG_OPENDS, &pick);
        printf("OPENDS %s rc=%u (%lu ms)\n", pick.ProductName, rc, GetTickCount() - t);
    }
    if (rc == TWRC_SUCCESS) printf("CLOSEDS rc=%u\n", entry(&app, NULL, DG_CONTROL, DAT_IDENTITY, MSG_CLOSEDS, &pick));
    entry(&app, NULL, DG_CONTROL, DAT_PARENT, MSG_CLOSEDSM, (TW_MEMREF)&hwnd);
    return 0;
}
