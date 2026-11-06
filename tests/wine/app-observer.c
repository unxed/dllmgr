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

struct wheel_target
{
    HWND hwnd;
    char class_name[128];
};

static struct wheel_target wheel_target_at_cursor(void)
{
    struct wheel_target target={0};
    POINT point;
    HWND hwnd;
    DWORD owner=0;

    if (!GetCursorPos(&point)) return target;
    hwnd=WindowFromPoint(point);
    GetWindowThreadProcessId(hwnd,&owner);
    GetClassNameA(hwnd,target.class_name,sizeof(target.class_name));
    if (owner==pid && (!lstrcmpiA(target.class_name,"TTntListView.UnicodeClass") ||
                       !lstrcmpiA(target.class_name,"TTntListView") ||
                       !lstrcmpiA(target.class_name,"SysListView32")))
        target.hwnd=hwnd;
    return target;
}

static BOOL scroll_position(HWND hwnd, int bar, int *value)
{
    SCROLLINFO info={sizeof(info),SIF_POS};
    if (!GetScrollInfo(hwnd,bar,&info)) return FALSE;
    *value=info.nPos;
    return TRUE;
}

/* Real pointer input in screen pixels; SetCursorPos alone may not produce
 * WM_MOUSEMOVE under Wine's X11 driver. */
static void pointer(int x, int y, DWORD buttons)
{
    INPUT input={0};
    input.type=INPUT_MOUSE;
    input.mi.dx=MulDiv(x,65535,GetSystemMetrics(SM_CXSCREEN)-1);
    input.mi.dy=MulDiv(y,65535,GetSystemMetrics(SM_CYSCREEN)-1);
    input.mi.dwFlags=MOUSEEVENTF_MOVE|MOUSEEVENTF_ABSOLUTE|buttons;
    SendInput(1,&input,sizeof(input));
    Sleep(15);
}


static void reveal_fullscreen_strip(HWND fullscreen, const RECT *bounds)
{
    int middle=(bounds->left+bounds->right)/2, y;
    int below=bounds->top+MulDiv(80,GetDpiForWindow(fullscreen),96);

    /* Move with real input: FastStone shows the strip on mouse motion, and
     * SetCursorPos may not produce WM_MOUSEMOVE under Wine's X11 driver. */
    pointer(middle,bounds->top+MulDiv(300,GetDpiForWindow(fullscreen),96),0);
    for (y=bounds->top+MulDiv(300,GetDpiForWindow(fullscreen),96);y>bounds->top;y-=MulDiv(20,GetDpiForWindow(fullscreen),96))
        pointer(middle,y,0);
    pointer(middle,bounds->top,0);
    Sleep(800);
    pointer(middle,below,0);
    Sleep(150);
}

/* How long the fullscreen strip stays up under a cursor that does not move.
 * Separates "Wine hides the strip" from "the harness sends no mouse motion". */
static void strip_persistence(void)
{
    struct wheel_target target=wheel_target_at_cursor();
    DWORD start=GetTickCount(), hidden=0;
    POINT cursor={0};

    if (!target.hwnd)
    {
        printf("strip_persistence: no list-view under the cursor after reveal\n");
        return;
    }
    while (GetTickCount()-start<3000)
    {
        if (!IsWindowVisible(target.hwnd))
        {
            hidden=GetTickCount()-start;
            GetCursorPos(&cursor);
            break;
        }
        Sleep(25);
    }
    if (hidden) printf("strip_persistence: hidden_after_ms=%lu cursor=%ld,%ld\n",hidden,cursor.x,cursor.y);
    else printf("strip_persistence: visible_for_ms=3000\n");
}

static void wheel_series(const char *stage, HWND fullscreen, const RECT *bounds, HANDLE process)
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
        struct wheel_target target=wheel_target_at_cursor();
        DWORD start, moved=0;
        int h_before=0, v_before=0, h_after=0, v_after=0;
        BOOL h_ok, v_ok, shown, item_ok;
        POINT item_before={0}, item_after={0};
        UINT sent=0;

        if (!target.hwnd && fullscreen)
        {
            /* FastStone can hide the strip after a wheel event. Reopen it
             * before the next event rather than scrolling the photo viewer. */
            reveal_fullscreen_strip(fullscreen,bounds);
            target=wheel_target_at_cursor();
        }
        h_ok=target.hwnd && scroll_position(target.hwnd,SB_HORZ,&h_before);
        v_ok=target.hwnd && scroll_position(target.hwnd,SB_VERT,&v_before);
        item_ok=target.hwnd && listview_item0_position(target.hwnd,process,&item_before);
        item_after=item_before;
        input.type=INPUT_MOUSE;
        input.mi.dwFlags=MOUSEEVENTF_WHEEL;
        input.mi.mouseData=(DWORD)deltas[i];
        start=GetTickCount();
        if (target.hwnd) sent=SendInput(1,&input,sizeof(input));
        h_after=h_before;
        v_after=v_before;
        do
        {
            Sleep(10);
            if (h_ok) h_ok=scroll_position(target.hwnd,SB_HORZ,&h_after);
            if (v_ok) v_ok=scroll_position(target.hwnd,SB_VERT,&v_after);
            if (item_ok) item_ok=listview_item0_position(target.hwnd,process,&item_after);
            if (!moved && ((h_ok && h_after!=h_before) || (v_ok && v_after!=v_before) ||
                           (item_ok && (item_after.x!=item_before.x || item_after.y!=item_before.y))))
                moved=GetTickCount()-start;
        } while (GetTickCount()-start<500);
        shown=target.hwnd && IsWindowVisible(target.hwnd);
        snprintf(filename,sizeof(filename),"%s-wheel-%u.bmp",stage,i+1);
        printf("%s wheel_%u delta=%d input_queued=%u target='%s' listview_visible_after=%d capture_after_ms=%lu",
               stage,i+1,deltas[i],sent,target.class_name,shown,GetTickCount()-start);
        if (h_ok) printf(" horizontal=%d->%d",h_before,h_after);
        if (v_ok) printf(" vertical=%d->%d",v_before,v_after);
        /* Scroll distance as the user sees it: item 0 moves opposite to the view. */
        if (item_ok) printf(" item0=%ld,%ld->%ld,%ld",item_before.x,item_before.y,item_after.x,item_after.y);
        if (moved) printf(" first_scroll_change_ms=%lu",moved);
        putchar('\n');
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

static BOOL CALLBACK find_fullscreen_notice(HWND child, LPARAM data)
{
    char text[512]="";
    DWORD_PTR length;
    if (SendMessageTimeoutA(child,WM_GETTEXT,sizeof(text),(LPARAM)text,SMTO_ABORTIFHUNG,200,&length) &&
        strstr(text,"first time that you are viewing an image in Full Screen"))
    {
        *(BOOL *)data=TRUE;
        return FALSE;
    }
    return TRUE;
}

static BOOL wait_for_fullscreen_input(HWND fullscreen)
{
    DWORD start=GetTickCount();
    BOOL dismissed=FALSE;

    /* FastStone briefly focuses fullscreen before its first-run notice opens. */
    Sleep(500);
    do
    {
        HWND foreground=GetForegroundWindow();
        DWORD owner=0;
        BOOL notice=FALSE;

        if (foreground==fullscreen && IsWindowEnabled(fullscreen)) return TRUE;
        GetWindowThreadProcessId(foreground,&owner);
        if (owner==pid && !dismissed)
        {
            /* Delphi message forms draw their text with TLabel, which is not a
             * child window, so the text search can miss the notice. Any other
             * window of the application in front of fullscreen is the notice. */
            EnumChildWindows(foreground,find_fullscreen_notice,(LPARAM)&notice);
            if (!notice && foreground!=fullscreen && IsWindowVisible(foreground)) notice=TRUE;
            if (notice && foreground==GetForegroundWindow())
            {
                snapshot("browser-origin-first-run-notice.bmp");
                press_key(VK_RETURN);
                dismissed=TRUE;
            }
        }
        Sleep(50);
    } while (GetTickCount()-start<3000);
    EnumWindows(describe_visible_window,0);
    return FALSE;
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
    reveal_fullscreen_strip(fullscreen,&bounds);
    strip_persistence();
    reveal_fullscreen_strip(fullscreen,&bounds);
    observe_listviews("fullscreen-strip",process,pid);
    wheel_series("fullscreen-strip",fullscreen,&bounds,process);

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
    wheel_series("browser",NULL,NULL,process);
    observe_address(browser);

    SetForegroundWindow(browser);
    press_key('F');
    fullscreen=wait_fullscreen(fullscreen_class);
    dump("fullscreen from browser",fullscreen);
    snapshot("browser-origin-fullscreen.bmp");
    if (!fullscreen) return 0;
    if (!wait_for_fullscreen_input(fullscreen))
    {
        puts("browser_origin_middle_skipped: fullscreen is not in the foreground");
        snapshot("browser-origin-blocked.bmp");
        return 0;
    }

    GetWindowRect(fullscreen,&bounds);
    SetCursorPos((bounds.left+bounds.right)/2,(bounds.top+bounds.bottom)/2);
    middle_click();
    Sleep(1000);
    if (GetExitCodeProcess(process,&code)) printf("browser_origin_middle_process_code=%lu\n",code);
    EnumWindows(describe_visible_window,0);
    snapshot("browser-origin-after-middle.bmp");
    return 0;
}

/* WineHQ 48874 in the real Draw Board: pick the pencil (second button of the
 * third tool row), draw a stroke across the canvas and report its colour.
 * Coordinates are client pixels at 96 DPI, scaled to the window's DPI. */
static void pencil_stroke(HWND draw)
{
    RECT client;
    POINT tool, from, to;
    int dpi=GetDpiForWindow(draw), x, counts[3]={0};
    COLORREF found[3]={0};
    HDC screen;

    if (!dpi) dpi=96;
    GetClientRect(draw,&client);
    tool.x=MulDiv(45,dpi,96); tool.y=MulDiv(140,dpi,96);
    from.x=client.right*2/5; from.y=client.bottom*2/5;
    to.x=client.right*3/5; to.y=client.bottom*2/5;
    ClientToScreen(draw,&tool); ClientToScreen(draw,&from); ClientToScreen(draw,&to);
    SetForegroundWindow(draw);
    pointer(tool.x,tool.y,0);
    pointer(tool.x,tool.y,MOUSEEVENTF_LEFTDOWN);
    pointer(tool.x,tool.y,MOUSEEVENTF_LEFTUP);
    Sleep(500);
    snapshot("draw-pencil-tool.bmp");
    pointer(from.x,from.y,0);
    pointer(from.x,from.y,MOUSEEVENTF_LEFTDOWN);
    for (x=from.x;x<=to.x;x+=MulDiv(8,dpi,96)) pointer(x,from.y,0);
    pointer(to.x,to.y,MOUSEEVENTF_LEFTUP);
    Sleep(500);
    snapshot("draw-pencil-stroke.bmp");

    /* Up to three distinct non-white, non-gray colours on the stroke row. */
    screen=GetDC(NULL);
    for (x=from.x+4;x<to.x-4;x++)
    {
        int dy;
        for (dy=-3;dy<=3;dy++)
        {
            COLORREF c=GetPixel(screen,x,from.y+dy);
            int r=GetRValue(c), g=GetGValue(c), b=GetBValue(c), k;
            if (c==CLR_INVALID || (abs(r-g)<12 && abs(g-b)<12 && r>150)) continue;
            for (k=0;k<3 && counts[k] && found[k]!=c;k++);
            if (k<3) { found[k]=c; counts[k]++; }
        }
    }
    ReleaseDC(NULL,screen);
    printf("pencil tool=%ld,%ld stroke=%ld,%ld->%ld,%ld dpi=%d\n",tool.x,tool.y,from.x,from.y,to.x,to.y,dpi);
    for (x=0;x<3;x++)
        if (counts[x]) printf("pencil_stroke_color=%02x%02x%02x pixels=%d\n",
                              GetRValue(found[x]),GetGValue(found[x]),GetBValue(found[x]),counts[x]);
    if (!counts[0]) puts("pencil_stroke_color=none");
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
    pid=process.dwProcessId;
    printf("app_pid=%04lx\n",pid);
    hwnd=wait_window(NULL,NULL);
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
            if(i) pencil_stroke(draw); /* after the second open is timed */
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
