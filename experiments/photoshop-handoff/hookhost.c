#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv)
{
    if(argc<3)return 2;
    HMODULE dll=LoadLibraryA(argv[1]);
    DWORD tid=GetWindowThreadProcessId((HWND)(ULONG_PTR)strtoul(argv[2],NULL,16),NULL);
    HHOOK a=SetWindowsHookExA(WH_CALLWNDPROC,(HOOKPROC)GetProcAddress(dll,"Before@12"),dll,tid);
    HHOOK b=SetWindowsHookExA(WH_CALLWNDPROCRET,(HOOKPROC)GetProcAddress(dll,"After@12"),dll,tid);
    printf("thread=%lu before=%p after=%p error=%lu\n",tid,a,b,GetLastError());fflush(stdout);
    if(!a||!b)return 1;
    MSG msg;while(GetMessageA(&msg,NULL,0,0)>0){TranslateMessage(&msg);DispatchMessageA(&msg);}
    UnhookWindowsHookEx(a);UnhookWindowsHookEx(b);return 0;
}
