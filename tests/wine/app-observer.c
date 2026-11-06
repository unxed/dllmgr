/* Observe the official portable application with synthetic images on Windows/Wine.
 * Window mapping/WM_NULL round trips are proxies, not full paint/interaction proofs. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static DWORD pid;
static HWND found;
static const char *wanted;
static BOOL CALLBACK find_window(HWND hwnd, LPARAM unused)
{
    DWORD owner;
    RECT rect;
    char title[512];
    GetWindowThreadProcessId(hwnd,&owner);
    GetWindowRect(hwnd,&rect);
    GetWindowTextA(hwnd,title,sizeof(title));
    if (owner==pid && IsWindowVisible(hwnd) && rect.right-rect.left>100 && rect.bottom-rect.top>100 &&
        (!wanted || strstr(title,wanted))) { found=hwnd; return FALSE; }
    return TRUE;
}
static HWND wait_window(const char *title)
{
    DWORD start=GetTickCount();
    wanted=title;
    do { found=NULL; EnumWindows(find_window,0); if(found) return found; Sleep(20); } while(GetTickCount()-start<20000);
    return NULL;
}
static void dump(const char *stage, HWND hwnd)
{
    RECT r={0}; char title[512]=""; DWORD_PTR result;
    GetWindowRect(hwnd,&r); GetWindowTextA(hwnd,title,sizeof(title));
    printf("%s hwnd=%p title='%s' rect=%ld,%ld,%ld,%ld responding=%d\n",stage,hwnd,title,r.left,r.top,r.right,r.bottom,
           !!SendMessageTimeoutA(hwnd,WM_NULL,0,0,SMTO_ABORTIFHUNG,1000,&result)); fflush(stdout);
}
static void snapshot(const char *name)
{
    int w=GetSystemMetrics(SM_CXSCREEN),h=GetSystemMetrics(SM_CYSCREEN);
    HDC screen=GetDC(NULL),mem=CreateCompatibleDC(screen);
    BITMAPINFO info={{sizeof(BITMAPINFOHEADER),w,-h,1,32,BI_RGB}};
    void *bits; HBITMAP bmp=CreateDIBSection(screen,&info,DIB_RGB_COLORS,&bits,NULL,0);
    HGDIOBJ old=SelectObject(mem,bmp);
    BITMAPFILEHEADER header={0x4d42,sizeof(header)+sizeof(info.bmiHeader)+w*h*4,0,0,sizeof(header)+sizeof(info.bmiHeader)};
    FILE *file;
    BitBlt(mem,0,0,w,h,screen,0,0,SRCCOPY);
    file=fopen(name,"wb"); if(file){fwrite(&header,sizeof(header),1,file);fwrite(&info.bmiHeader,sizeof(info.bmiHeader),1,file);fwrite(bits,w*h*4,1,file);fclose(file);}
    SelectObject(mem,old); DeleteObject(bmp); DeleteDC(mem); ReleaseDC(NULL,screen);
}
int main(int argc,char **argv)
{
    STARTUPINFOA startup={sizeof(startup)}; PROCESS_INFORMATION process;
    DWORD start,code; HWND hwnd,draw; RECT rect; int i;
    char command[2048];
    if(argc!=4){fprintf(stderr,"app-observer.exe FSViewer.exe image.bmp action(middle|enter|draw)\n");return 2;}
    snprintf(command,sizeof(command),"\"%s\" \"%s\"",argv[1],argv[2]);
    start=GetTickCount();
    if(!CreateProcessA(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&startup,&process))return 3;
    pid=process.dwProcessId; hwnd=wait_window(NULL);
    printf("startup_to_mapped_ms=%lu\n",GetTickCount()-start); dump("initial",hwnd); Sleep(2000); snapshot("initial.bmp");
    if(!hwnd){TerminateProcess(process.hProcess,1);return 4;}
    if(!strcmp(argv[3],"draw"))
    {
        for(i=0;i<2;i++){
            SetForegroundWindow(hwnd); start=GetTickCount(); keybd_event('D',0,0,0); keybd_event('D',0,KEYEVENTF_KEYUP,0);
            draw=wait_window("Draw Board");printf("draw_%d_to_mapped_ms=%lu\n",i+1,GetTickCount()-start);dump("draw",draw);Sleep(1000);snapshot(i?"draw-second.bmp":"draw-first.bmp");
            if(!draw)break;
            PostMessageA(draw,WM_CLOSE,0,0);Sleep(1000);
        }
    }
    else for(i=0;i<2;i++){
        SetForegroundWindow(hwnd);GetWindowRect(hwnd,&rect);SetCursorPos((rect.left+rect.right)/2,(rect.top+rect.bottom)/2);
        if(!strcmp(argv[3],"middle")){mouse_event(MOUSEEVENTF_MIDDLEDOWN,0,0,0,0);mouse_event(MOUSEEVENTF_MIDDLEUP,0,0,0,0);}
        else {keybd_event(VK_RETURN,0,0,0);keybd_event(VK_RETURN,0,KEYEVENTF_KEYUP,0);}
        Sleep(1000);GetExitCodeProcess(process.hProcess,&code);printf("after_%d_process_code=%lu\n",i+1,code);
        if(code!=STILL_ACTIVE)break;
        hwnd=wait_window(NULL);dump("after input",hwnd);snapshot(i?"after-second.bmp":"after-first.bmp");
    }
    TerminateProcess(process.hProcess,0);WaitForSingleObject(process.hProcess,5000);
    CloseHandle(process.hThread);CloseHandle(process.hProcess);return 0;
}
