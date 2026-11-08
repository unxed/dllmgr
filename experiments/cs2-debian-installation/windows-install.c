#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
static DWORD target;
static BOOL CALLBACK dump(HWND w, LPARAM depth)
{
    char text[512],cls[128]; RECT r; DWORD pid;
    GetWindowThreadProcessId(w,&pid);
    if (!depth && target && pid!=target) return TRUE;
    GetWindowTextA(w,text,sizeof(text)); GetClassNameA(w,cls,sizeof(cls)); GetWindowRect(w,&r);
    printf("%*s%p pid=%lu id=%d visible=%d rect=%ld,%ld,%ld,%ld style=%08lx ex=%08lx class=%s text=%s\n",
           (int)depth*2,"",w,pid,GetDlgCtrlID(w),IsWindowVisible(w),r.left,r.top,r.right-r.left,r.bottom-r.top,
           (unsigned long)GetWindowLongW(w,GWL_STYLE),(unsigned long)GetWindowLongW(w,GWL_EXSTYLE),cls,text);
    if (!depth) EnumChildWindows(w,dump,1);
    return TRUE;
}
int main(int argc,char **argv)
{
    if (argc>2 && !strcmp(argv[1],"check")) {
        LRESULT state=SendMessageA((HWND)(ULONG_PTR)strtoul(argv[2],NULL,16),BM_GETCHECK,0,0);
        printf("BM_GETCHECK=%ld\n",(long)state); return 0;
    }
    if (argc>3 && !strcmp(argv[1],"text")) {
        LRESULT ok=SendMessageA((HWND)(ULONG_PTR)strtoul(argv[2],NULL,16),WM_SETTEXT,0,(LPARAM)argv[3]);
        printf("WM_SETTEXT=%ld error=%lu\n",(long)ok,GetLastError()); return !ok;
    }
    if (argc>4 && !strcmp(argv[1],"size")) {
        BOOL ok=SetWindowPos((HWND)(ULONG_PTR)strtoul(argv[2],NULL,16),NULL,0,0,atoi(argv[3]),atoi(argv[4]),SWP_NOMOVE|SWP_NOACTIVATE|SWP_NOZORDER);
        printf("SetWindowPos=%d error=%lu\n",ok,GetLastError());return !ok;
    }
    if (argc>2 && !strcmp(argv[1],"close")) {
        PostMessageA((HWND)(ULONG_PTR)strtoul(argv[2],NULL,16),WM_CLOSE,0,0); return 0;
    }
    if (argc>2 && !strcmp(argv[1],"click")) {
        PostMessageA((HWND)(ULONG_PTR)strtoul(argv[2],NULL,16),BM_CLICK,0,0); return 0;
    }
    target=argc>1?strtoul(argv[1],NULL,0):0;
    EnumWindows(dump,0);
    return 0;
}
