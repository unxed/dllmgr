/* Observe the official portable application with synthetic images on Windows/Wine.
 * Window mapping/WM_NULL round trips are proxies, not full paint/interaction proofs. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "listview-probe.h"

static DWORD pid;
static HWND found;
static const char *wanted_title;
static const char *wanted_class;
static BOOL CALLBACK find_window(HWND hwnd, LPARAM unused)
{
    DWORD owner;
    RECT rect;
    char title[512]="",class_name[256]="";
    GetWindowThreadProcessId(hwnd,&owner);
    if(owner!=pid || !IsWindowVisible(hwnd) || !GetWindowRect(hwnd,&rect) ||
       rect.right-rect.left<=100 || rect.bottom-rect.top<=100) return TRUE;
    GetWindowTextA(hwnd,title,sizeof(title));
    GetClassNameA(hwnd,class_name,sizeof(class_name));
    if ((!wanted_title && !wanted_class) ||
        (wanted_class && !strcmp(class_name,wanted_class)) ||
        (wanted_title && strstr(title,wanted_title))) { found=hwnd; return FALSE; }
    return TRUE;
}
static HWND wait_window(const char *title, const char *class_name)
{
    DWORD start=GetTickCount();
    wanted_title=title;
    wanted_class=class_name;
    do { found=NULL; EnumWindows(find_window,0); if(found) return found; Sleep(20); } while(GetTickCount()-start<20000);
    return NULL;
}
static void describe(const char *stage, HWND hwnd)
{
    RECT r={0};
    char title[512]="",class_name[256]="";
    GetWindowRect(hwnd,&r); GetWindowTextA(hwnd,title,sizeof(title));
    GetClassNameA(hwnd,class_name,sizeof(class_name));
    printf("%s hwnd=%p class='%s' title='%s' rect=%ld,%ld,%ld,%ld dpi=%u\n",
           stage,hwnd,class_name,title,r.left,r.top,r.right,r.bottom,GetDpiForWindow(hwnd));
}
static BOOL CALLBACK describe_visible_window(HWND hwnd, LPARAM unused)
{
    DWORD owner;
    GetWindowThreadProcessId(hwnd,&owner);
    if (owner==pid && IsWindowVisible(hwnd)) describe("candidate",hwnd);
    return TRUE;
}
static void dump(const char *stage, HWND hwnd)
{
    DWORD_PTR result;
    if (!hwnd) { printf("%s: window not found\n",stage); return; }
    describe(stage,hwnd);
    printf("%s responding=%d\n",stage,!!SendMessageTimeoutA(hwnd,WM_NULL,0,0,SMTO_ABORTIFHUNG,1000,&result));
    fflush(stdout);
}
static void report_timing(const char *stage, DWORD start, HWND hwnd)
{
    DWORD mapped=GetTickCount()-start;
    DWORD_PTR result;
    if (!hwnd) {
        printf("%s_detection_timeout_ms=%lu\n",stage,mapped);
        EnumWindows(describe_visible_window,0);
    } else {
        BOOL responding=!!SendMessageTimeoutA(hwnd,WM_NULL,0,0,SMTO_ABORTIFHUNG,1000,&result);
        printf("%s_to_mapped_ms=%lu\n",stage,mapped);
        if (responding) printf("%s_to_first_wm_null_reply_ms=%lu\n",stage,GetTickCount()-start);
        else printf("%s_wm_null_no_reply\n",stage);
        describe(stage,hwnd);
    }
    fflush(stdout);
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
static void press_key(BYTE key)
{
    keybd_event(key,0,0,0);
    keybd_event(key,0,KEYEVENTF_KEYUP,0);
}

/* The portable browser's address row contains a TTntEdit and an owner-drawn
 * TTntComboBox. Match the generated folder name before touching any control. */
static BOOL CALLBACK find_address(HWND child, LPARAM data)
{
    HWND *address=(HWND *)data;
    WCHAR class_name[128], value[1024];
    DWORD_PTR count;
    size_t length;
    static const WCHAR folder[]=L"\\browser";

    if (!IsWindowVisible(child) || !GetClassNameW(child,class_name,ARRAYSIZE(class_name)) ||
        (!wcsstr(class_name,L"Edit") && !wcsstr(class_name,L"ComboBox")))
        return TRUE;
    if (!SendMessageTimeoutW(child,WM_GETTEXT,ARRAYSIZE(value),(LPARAM)value,
                             SMTO_ABORTIFHUNG,200,&count) || !count || count>=ARRAYSIZE(value))
        return TRUE;

    length=wcslen(value);
    while (length && (value[length-1]==L'\\' || value[length-1]==L'/')) value[--length]=0;
    printf("browser_text_control class=%ls text=%ls\n",class_name,value);
    if (length<ARRAYSIZE(folder)-1 || _wcsicmp(value+length-(ARRAYSIZE(folder)-1),folder))
        return TRUE;
    *address=child;
    return FALSE;
}

static void observe_address(HWND browser)
{
    HWND address=NULL;
    RECT bounds;
    LOGFONTW logical_font;
    DWORD_PTR handle=0;
    DWORD start;

    EnumChildWindows(browser,find_address,(LPARAM)&address);
    if (!address) { puts("browser_address: synthetic folder not found in an edit or combo box"); return; }
    dump("browser_address",address);
    if (GetWindowRect(address,&bounds))
        printf("browser_address_rect=%ld,%ld,%ld,%ld\n",bounds.left,bounds.top,bounds.right,bounds.bottom);
    if (SendMessageTimeoutW(address,WM_GETFONT,0,0,SMTO_ABORTIFHUNG,200,&handle) &&
        handle && GetObjectW((HFONT)handle,sizeof(logical_font),&logical_font))
        printf("browser_address_requested_font=%ls height=%ld weight=%ld charset=%u quality=%u\n",
               logical_font.lfFaceName,logical_font.lfHeight,logical_font.lfWeight,
               logical_font.lfCharSet,logical_font.lfQuality);
    else puts("browser_address_requested_font: unavailable across processes");

    snapshot("browser-address-before-repaint.bmp");
    start=GetTickCount();
    if (!RedrawWindow(address,NULL,NULL,RDW_INVALIDATE|RDW_ERASE|RDW_UPDATENOW))
        printf("browser_address_repaint: failed, error=%lu\n",GetLastError());
    else printf("browser_address_repaint_ms=%lu\n",GetTickCount()-start);
    Sleep(250);
    snapshot("browser-address-after-repaint.bmp");
}

static void observe_left_panel(const RECT *bounds)
{
    SetCursorPos(bounds->left,(bounds->top+bounds->bottom)/2);
    Sleep(800);
    snapshot("fullscreen-left-panel.bmp");
}

static void wheel_series(const char *stage)
{
    static const int deltas[]={-WHEEL_DELTA/2,-WHEEL_DELTA/2,-WHEEL_DELTA,-2*WHEEL_DELTA};
    unsigned i;
    UINT lines=0;
    char filename[100];
    BOOL lines_ok=SystemParametersInfoA(SPI_GETWHEELSCROLLLINES,0,&lines,0);

    printf("%s wheel_lines=%u query_ok=%d\n",stage,lines,lines_ok);
    snprintf(filename,sizeof(filename),"%s-before.bmp",stage);
    snapshot(filename);
    for (i=0;i<sizeof(deltas)/sizeof(deltas[0]);i++)
    {
        INPUT input={0};
        POINT point={0};
        HWND target;
        DWORD owner=0, start;
        char class_name[128]="";
        UINT sent=0;

        target=GetCursorPos(&point) ? WindowFromPoint(point) : NULL;
        GetWindowThreadProcessId(target,&owner);
        GetClassNameA(target,class_name,sizeof(class_name));
        input.type=INPUT_MOUSE;
        input.mi.dwFlags=MOUSEEVENTF_WHEEL;
        input.mi.mouseData=(DWORD)deltas[i];
        start=GetTickCount();
        if (owner==pid) sent=SendInput(1,&input,sizeof(input));
        Sleep(500);
        snprintf(filename,sizeof(filename),"%s-wheel-%u.bmp",stage,i+1);
        printf("%s wheel_%u delta=%d input_queued=%u target='%s' app_window=%d capture_after_ms=%lu\n",
               stage,i+1,deltas[i],sent,class_name,owner==pid,GetTickCount()-start);
        snapshot(filename);
    }
}

static HWND wait_fullscreen(const char *expected_class)
{
    DWORD start=GetTickCount();
    do
    {
        HWND hwnd=GetForegroundWindow();
        DWORD owner=0;
        RECT bounds;
        MONITORINFO monitor={sizeof(monitor)};
        char class_name[256]="";

        GetWindowThreadProcessId(hwnd,&owner);
        if (owner==pid && GetClassNameA(hwnd,class_name,sizeof(class_name)) &&
            !strcmp(class_name,expected_class) && GetWindowRect(hwnd,&bounds) &&
            GetMonitorInfoA(MonitorFromWindow(hwnd,MONITOR_DEFAULTTONEAREST),&monitor) &&
            bounds.left<=monitor.rcMonitor.left && bounds.top<=monitor.rcMonitor.top &&
            bounds.right>=monitor.rcMonitor.right && bounds.bottom>=monitor.rcMonitor.bottom)
            return hwnd;
        Sleep(20);
    } while (GetTickCount()-start<4000);
    return NULL;
}

static void middle_click(void)
{
    mouse_event(MOUSEEVENTF_MIDDLEDOWN,0,0,0,0);
    mouse_event(MOUSEEVENTF_MIDDLEUP,0,0,0,0);
}

static int observe_browser(HWND fullscreen, HANDLE process)
{
    RECT bounds;
    HWND browser;
    DWORD code;
    char fullscreen_class[256]="";

    GetClassNameA(fullscreen,fullscreen_class,sizeof(fullscreen_class));
    SetForegroundWindow(fullscreen);
    GetWindowRect(fullscreen,&bounds);
    observe_left_panel(&bounds);
    SetCursorPos((bounds.left+bounds.right)/2,bounds.top);
    Sleep(800);
    observe_listviews("fullscreen-strip",process,pid);
    wheel_series("fullscreen-strip");

    SetCursorPos((bounds.left+bounds.right)/2,(bounds.top+bounds.bottom)/2);
    SetForegroundWindow(fullscreen);
    press_key(VK_RETURN);
    browser=wait_window("FastStone Image Viewer","TMainFrame");
    dump("browser",browser);
    if (!browser) return 5;
    GetWindowRect(browser,&bounds);
    SetCursorPos(bounds.left+(bounds.right-bounds.left)*3/4,(bounds.top+bounds.bottom)/2);
    Sleep(1000);
    observe_listviews("browser-grid",process,pid);
    wheel_series("browser");
    observe_address(browser);

    SetForegroundWindow(browser);
    press_key('F');
    fullscreen=wait_fullscreen(fullscreen_class);
    dump("fullscreen from browser",fullscreen);
    snapshot("browser-origin-fullscreen.bmp");
    if (!fullscreen) return 0;

    GetWindowRect(fullscreen,&bounds);
    SetCursorPos((bounds.left+bounds.right)/2,(bounds.top+bounds.bottom)/2);
    middle_click();
    Sleep(1000);
    if (GetExitCodeProcess(process,&code)) printf("browser_origin_middle_process_code=%lu\n",code);
    snapshot("browser-origin-after-middle.bmp");
    return 0;
}

int main(int argc,char **argv)
{
    STARTUPINFOA startup={sizeof(startup)}; PROCESS_INFORMATION process;
    DWORD start,code; HWND hwnd,draw; RECT rect; int i,status=0;
    char command[2048];
    if(argc!=4){fprintf(stderr,"app-observer.exe FSViewer.exe image.bmp action(middle|enter|draw|browser|panel)\n");return 2;}
    SetProcessDPIAware();
    printf("capture_screen=%dx%d\n",GetSystemMetrics(SM_CXSCREEN),GetSystemMetrics(SM_CYSCREEN));
    snprintf(command,sizeof(command),"\"%s\" \"%s\"",argv[1],argv[2]);
    start=GetTickCount();
    if(!CreateProcessA(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&startup,&process))return 3;
    pid=process.dwProcessId; hwnd=wait_window(NULL,NULL);
    report_timing("startup",start,hwnd); Sleep(2000); snapshot("initial.bmp");
    if(!hwnd) status=4;
    else if(!strcmp(argv[3],"browser")) status=observe_browser(hwnd,process.hProcess);
    else if(!strcmp(argv[3],"panel"))
    {
        SetForegroundWindow(hwnd);
        if (GetWindowRect(hwnd,&rect)) observe_left_panel(&rect);
    }
    else if(!strcmp(argv[3],"draw"))
    {
        for(i=0;i<2;i++){
            char stage[16];
            DWORD close_start;
            snprintf(stage,sizeof(stage),"draw_%d",i+1);
            SetForegroundWindow(hwnd); start=GetTickCount(); press_key('D');
            /* The Delphi form can paint a caption without exposing it as window text. */
            draw=wait_window("Draw Board","TDrawBoard");
            report_timing(stage,start,draw);Sleep(1000);snapshot(i?"draw-second.bmp":"draw-first.bmp");
            if(!draw)break;
            PostMessageA(draw,WM_CLOSE,0,0);
            close_start=GetTickCount();
            while (IsWindowVisible(draw) && GetTickCount()-close_start<5000) Sleep(20);
            if (IsWindowVisible(draw)) { printf("%s_close_timeout\n",stage); break; }
        }
    }
    else for(i=0;i<2;i++){
        SetForegroundWindow(hwnd);GetWindowRect(hwnd,&rect);SetCursorPos((rect.left+rect.right)/2,(rect.top+rect.bottom)/2);
        if(!strcmp(argv[3],"middle")) middle_click();
        else press_key(VK_RETURN);
        Sleep(1000);GetExitCodeProcess(process.hProcess,&code);printf("after_%d_process_code=%lu\n",i+1,code);
        if(code!=STILL_ACTIVE)break;
        hwnd=wait_window(NULL,NULL);dump("after input",hwnd);snapshot(i?"after-second.bmp":"after-first.bmp");
    }
    TerminateProcess(process.hProcess,status);WaitForSingleObject(process.hProcess,5000);
    CloseHandle(process.hThread);CloseHandle(process.hProcess);return status;
}
