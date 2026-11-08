/* Observe only an owned FastStone fullscreen window; never inject input.
 * The explicit synthetic center colour distinguishes painted image from background. */
#define main general_observer_main
#include "app-observer.c"
#undef main

static unsigned rgb(COLORREF color)
{
    return (GetRValue(color)<<16)|(GetGValue(color)<<8)|GetBValue(color);
}

int wmain(int argc, WCHAR **argv)
{
    STARTUPINFOW si={sizeof(si)}; PROCESS_INFORMATION pi;
    WCHAR command[32768]; unsigned expected;
    DWORD start,first_image=0,first_white=0,restored=0,last=99;
    unsigned samples=0,missed=0; HDC screen; int status=0;
    if(argc!=4 || wcslen(argv[1])+wcslen(argv[2])+8>=ARRAYSIZE(command)) {
        fputs("first-open-probe.exe EXE IMAGE RRGGBB\n",stderr);return 2;
    }
    expected=(unsigned)wcstoul(argv[3],NULL,16);
    SetProcessDPIAware();
    swprintf(command,ARRAYSIZE(command),L"\"%ls\" \"%ls\"",argv[1],argv[2]);
    start=GetTickCount();
    if(!CreateProcessW(argv[1],command,NULL,NULL,FALSE,0,NULL,NULL,&si,&pi))return 3;
    pid=pi.dwProcessId;app_process=pi.hProcess;screen=GetDC(NULL);
    printf("expected_center=%06x screen=%dx%d app_pid=%lu\n",expected,
           GetSystemMetrics(SM_CXSCREEN),GetSystemMetrics(SM_CYSCREEN),pid);
    while(GetTickCount()-start<20000) {
        HWND window=GetForegroundWindow();DWORD owner=0,phase=0,now=GetTickCount()-start;
        RECT bounds;WCHAR cls[128];unsigned colors[9],white=0,k=0;BOOL valid=TRUE;
        GetWindowThreadProcessId(window,&owner);
        if(WaitForSingleObject(pi.hProcess,0)==WAIT_OBJECT_0){status=4;break;}
        if(owner!=pid || !GetClassNameW(window,cls,ARRAYSIZE(cls)) ||
           !wcsstr(cls,L"FullScreenWindow") || !GetWindowRect(window,&bounds) ||
           bounds.right-bounds.left<GetSystemMetrics(SM_CXSCREEN) ||
           bounds.bottom-bounds.top<GetSystemMetrics(SM_CYSCREEN)) {
            missed++;Sleep(10);continue;
        }
        for(int y=1;y<=5;y+=2)for(int x=1;x<=5;x+=2) {
            COLORREF pixel=GetPixel(screen,bounds.left+(bounds.right-bounds.left)*x/6,
                                     bounds.top+(bounds.bottom-bounds.top)*y/6);
            if(pixel==CLR_INVALID)valid=FALSE;
            colors[k]=rgb(pixel);
            if(colors[k]==0xffffff)white++;
            k++;
        }
        /* Reject observations spanning a foreground switch. */
        if(!valid || GetForegroundWindow()!=window){missed++;Sleep(10);continue;}
        samples++;
        if(colors[4]==expected)phase=2;
        else if(white==9)phase=3;
        else phase=1;
        if(phase!=last) {
            printf("t_ms=%lu phase=%s center=%06x white_samples=%u/9\n",now,
                   phase==2?"image":phase==3?"white":"other",colors[4],white);
            printf("phase_window=%p style=%08lx exstyle=%08lx\n",window,
                   (unsigned long)GetWindowLongW(window,GWL_STYLE),
                   (unsigned long)GetWindowLongW(window,GWL_EXSTYLE));
            EnumWindows(describe_visible_window,0);
            fflush(stdout);last=phase;
        }
        if(phase==2 && !first_image)first_image=now;
        if(phase==3 && first_image && !first_white) {
            first_white=now;snapshot("white-after-image.bmp");
        }
        if(phase==2 && first_white && !restored) {
            restored=now;snapshot("image-returned.bmp");
        }
        if(first_image && now-first_image>7000)break;
        Sleep(10);
    }
    ReleaseDC(NULL,screen);
    printf("first_image_ms=%lu white_after_image_ms=%lu restored_ms=%lu samples=%u skipped=%u\n",
           first_image,first_white,restored,samples,missed);
    printf("observed_image_white_image=%d\n",!!(first_image && first_white && restored));
    if(!first_image)status=5;
    TerminateProcess(pi.hProcess,0);WaitForSingleObject(pi.hProcess,5000);
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return status;
}
