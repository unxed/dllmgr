#include <windows.h>
#include <stdio.h>
int main(void) {
 BOOL aware=SetProcessDPIAware();
 HDC dc=GetDC(NULL);
 typedef UINT (WINAPI *getdpi_t)(void);
 getdpi_t dpi=(getdpi_t)GetProcAddress(GetModuleHandleA("user32.dll"),"GetDpiForSystem");
 printf("SetProcessDPIAware=%d LOGPIXELS=%d,%d GetDpiForSystem=%u screen=%dx%d\n",aware,GetDeviceCaps(dc,LOGPIXELSX),GetDeviceCaps(dc,LOGPIXELSY),dpi?dpi():0,GetSystemMetrics(SM_CXSCREEN),GetSystemMetrics(SM_CYSCREEN));
 ReleaseDC(NULL,dc);return 0;
}
