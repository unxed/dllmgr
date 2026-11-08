#include <windows.h>
#include <stdio.h>
#include <string.h>
static void logmsg(HWND w, UINT msg, LPARAM lp, const char *phase)
{
    char title[64], cls[100],line[512]; DWORD count;
    if (msg!=WM_WINDOWPOSCHANGING && msg!=WM_WINDOWPOSCHANGED && msg!=WM_GETMINMAXINFO) return;
    if (GetWindowLongW(w,GWL_STYLE)&WS_CHILD) return;
    GetWindowTextA(w,title,sizeof(title));
    if (strcmp(title,"Open")) return;
    GetClassNameA(w,cls,sizeof(cls));
    if (msg==WM_WINDOWPOSCHANGING || msg==WM_WINDOWPOSCHANGED) {
        WINDOWPOS *p=(WINDOWPOS*)lp;
        sprintf(line,"%lu %s hwnd=%p class=%s msg=%x xy=%d,%d size=%d,%d flags=%x\r\n",GetTickCount(),phase,w,cls,msg,p->x,p->y,p->cx,p->cy,p->flags);
    } else if (msg==WM_GETMINMAXINFO) {
        MINMAXINFO *p=(MINMAXINFO*)lp;
        sprintf(line,"%lu %s hwnd=%p class=%s min=%ld,%ld max=%ld,%ld\r\n",GetTickCount(),phase,w,cls,p->ptMinTrackSize.x,p->ptMinTrackSize.y,p->ptMaxTrackSize.x,p->ptMaxTrackSize.y);
    } else return;
    HANDLE f=CreateFileA("Z:\\home\\unxed\\Documents\\Codex\\2026-11-07\\pfl\\work\\photoshop-cs2\\sizehook110.log",FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(f!=INVALID_HANDLE_VALUE){WriteFile(f,line,strlen(line),&count,NULL);CloseHandle(f);}
}
__declspec(dllexport) LRESULT CALLBACK Before(int code,WPARAM wp,LPARAM lp)
{
    if(code>=0){CWPSTRUCT *p=(CWPSTRUCT*)lp;logmsg(p->hwnd,p->message,p->lParam,"before");}
    return CallNextHookEx(NULL,code,wp,lp);
}
__declspec(dllexport) LRESULT CALLBACK After(int code,WPARAM wp,LPARAM lp)
{
    if(code>=0){CWPRETSTRUCT *p=(CWPRETSTRUCT*)lp;logmsg(p->hwnd,p->message,p->lParam,"after");}
    return CallNextHookEx(NULL,code,wp,lp);
}
