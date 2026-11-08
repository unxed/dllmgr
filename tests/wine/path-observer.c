/* Black-box FastStone path combo probe. Only the process we launch receives input. */
#define main general_observer_main
#include "app-observer.c"
#undef main
#include <uxtheme.h>

static HWND combo;
static int classic;
static BOOL CALLBACK find_combo(HWND child, LPARAM unused)
{
    WCHAR cls[128],text[2048]; DWORD_PTR result=0; size_t n;
    if (!IsWindowVisible(child) || !GetClassNameW(child,cls,ARRAYSIZE(cls))) return TRUE;
    if (!wcsstr(cls,L"ComboBox")) return TRUE;
    if (!SendMessageTimeoutW(child,WM_GETTEXT,ARRAYSIZE(text),(LPARAM)text,
                             SMTO_ABORTIFHUNG,500,&result)) return TRUE;
    n=wcslen(text); while(n && (text[n-1]==L'\\' || text[n-1]==L'/')) text[--n]=0;
    printf("combo_candidate class=%ls chars=%llu\n",cls,(unsigned long long)n);
    if(n>=8 && !_wcsicmp(text+n-8,L"\\browser")) {combo=child;return FALSE;}
    return TRUE;
}
static int crop(const char *name, RECT r)
{
    int w=r.right-r.left,h=r.bottom-r.top;
    HDC screen=GetDC(NULL),mem=CreateCompatibleDC(screen);void *bits;
    BITMAPINFO info={{sizeof(BITMAPINFOHEADER),w,-h,1,32,BI_RGB}};
    HBITMAP bmp=CreateDIBSection(screen,&info,DIB_RGB_COLORS,&bits,NULL,0);
    HGDIOBJ old; FILE *f; int ok=0;
    BITMAPFILEHEADER header={0x4d42,sizeof(header)+sizeof(info.bmiHeader)+w*h*4,0,0,sizeof(header)+sizeof(info.bmiHeader)};
    if(!bmp || !mem || w<=0 || h<=0) return 0;
    old=SelectObject(mem,bmp);
    if(BitBlt(mem,0,0,w,h,screen,r.left,r.top,SRCCOPY) && (f=fopen(name,"wb"))) {
        ok=fwrite(&header,sizeof(header),1,f)==1 && fwrite(&info.bmiHeader,sizeof(info.bmiHeader),1,f)==1 && fwrite(bits,w*h*4,1,f)==1;
        fclose(f);
    }
    SelectObject(mem,old);DeleteObject(bmp);DeleteDC(mem);ReleaseDC(NULL,screen);return ok;
}
static int capture_state(const char *stage, HWND browser)
{
    COMBOBOXINFO ci={sizeof(ci)}; GUITHREADINFO gi={sizeof(gi)};
    RECT r,button; DWORD_PTR dropped=0; char name[100];
    if(!GetWindowRect(combo,&r) || !GetComboBoxInfo(combo,&ci)) {
        printf("%s combo_info_failed=%lu\n",stage,GetLastError()); return 0;
    }
    GetGUIThreadInfo(GetWindowThreadProcessId(browser,NULL),&gi);
    SendMessageTimeoutA(combo,CB_GETDROPPEDSTATE,0,0,SMTO_ABORTIFHUNG,500,&dropped);
    button=ci.rcButton;
    printf("stage=%s dropped=%llu button_state=%lu focus_combo=%d capture_combo=%d list_visible=%d combo_rect=%ld,%ld,%ld,%ld button=%ld,%ld,%ld,%ld\n",
           stage,(unsigned long long)dropped,ci.stateButton,gi.hwndFocus==combo,gi.hwndCapture==combo,IsWindowVisible(ci.hwndList),
           r.left,r.top,r.right,r.bottom,button.left,button.top,button.right,button.bottom);
    /* Fixed region includes the synthetic path, dropdown and a little background. */
    r.bottom=min(r.bottom+MulDiv(320,GetDpiForWindow(combo),96),GetSystemMetrics(SM_CYSCREEN));
    snprintf(name,sizeof(name),"%s.bmp",stage);fflush(stdout);return crop(name,r);
}
static BOOL CALLBACK child_geometry(HWND child, LPARAM unused)
{
    char cls[128]; RECT r;
    if(IsWindowVisible(child) && GetClassNameA(child,cls,sizeof(cls)) && GetWindowRect(child,&r))
        printf("child class=%s rect=%ld,%ld,%ld,%ld\n",cls,r.left,r.top,r.right,r.bottom);
    return TRUE;
}
static int observe_path(HWND first)
{
    HWND browser; RECT r; POINT p; COMBOBOXINFO ci={sizeof(ci)}; INPUT event={0}; int ok=1,held=0;
    if(!activate_owned_window(first)) return 7;
    describe("initial_window",first);
    GetWindowRect(first,&r);crop("initial-window.bmp",r);
    press_key(VK_RETURN); Sleep(1200);
    browser=wait_window("FastStone Image Viewer","FastStoneImageViewerMainForm");
    if(!browser || !activate_owned_window(browser)) return 4;
    /* Match the application client area, excluding OS-specific decorations. */
    ShowWindow(browser,SW_RESTORE);
    for(int attempt=0;attempt<2;attempt++) {
        RECT client,outer;GetClientRect(browser,&client);GetWindowRect(browser,&outer);
        int width=MulDiv(900,GetDpiForWindow(browser),96);
        int height=MulDiv(600,GetDpiForWindow(browser),96);
        SetWindowPos(browser,NULL,20,20,width+outer.right-outer.left-client.right,
                     height+outer.bottom-outer.top-client.bottom,SWP_NOZORDER|SWP_NOACTIVATE);
    }
    Sleep(500);
    EnumChildWindows(browser,find_combo,0);
    if(!combo) {
        puts("synthetic_path_combo_not_found");describe("after_enter",browser);
        EnumWindows(describe_visible_window,0);EnumChildWindows(browser,child_geometry,0);
        GetWindowRect(browser,&r);crop("missing-combo-window.bmp",r);return 5;
    }
    if(!GetComboBoxInfo(combo,&ci) || !GetWindowRect(combo,&r)) return 6;
    if(classic && IsThemeActive()) {
        HRESULT hr=SetWindowTheme(combo,L" ",L" ");
        printf("classic_theme_result=%08lx\n",(unsigned long)hr);
        if(FAILED(hr))return 10;
        RedrawWindow(combo,NULL,NULL,RDW_INVALIDATE|RDW_ERASE|RDW_UPDATENOW|RDW_ALLCHILDREN);
        Sleep(250);
    }
    printf("control_themed=%d global_themed=%d\n",GetWindowTheme(combo)!=NULL,IsThemeActive());
    if(classic && GetWindowTheme(combo)) {puts("classic_control_still_themed");return 10;}
    describe("path_combo",combo);
    {
        WCHAR file[MAX_PATH],color[128],size[128];RECT client;
        HRESULT hr=GetCurrentThemeName(file,ARRAYSIZE(file),color,ARRAYSIZE(color),size,ARRAYSIZE(size));
        GetClientRect(browser,&client);
        printf("client=%ldx%ld theme_hr=%08lx theme_color=%ls theme_size=%ls classic=%d\n",
               client.right,client.bottom,(unsigned long)hr,SUCCEEDED(hr)?color:L"",SUCCEEDED(hr)?size:L"",classic);
    }
    printf("combo_style=%08lx dpi=%u\n",GetWindowLongA(combo,GWL_STYLE),GetDpiForWindow(combo));
    p.x=r.right-GetSystemMetrics(SM_CXVSCROLL)/2-2;p.y=(r.top+r.bottom)/2;
    ok=capture_state("00-initial",browser);
    pointer(p.x,p.y,0);Sleep(250);ok=ok && capture_state("01-hover",browser);
    event.type=INPUT_MOUSE;
    if(!activate_owned_window(browser)) return 7;
    event.mi.dwFlags=MOUSEEVENTF_LEFTDOWN;held=SendInput(1,&event,sizeof(event))==1;
    if(!held)return 8;
    Sleep(250);ok=capture_state("02-down",browser) && ok;
    Sleep(750);ok=capture_state("03-held",browser) && ok;
    event.mi.dwFlags=MOUSEEVENTF_LEFTUP;SendInput(1,&event,sizeof(event));held=0;
    Sleep(250);ok=capture_state("04-up",browser) && ok;
    /* Owner follow-up: mouse-up alone must be observed separately from motion. */
    Sleep(750);ok=capture_state("04-stationary",browser) && ok;
    pointer(p.x-2,p.y,0);Sleep(250);ok=capture_state("04-move-inside",browser) && ok;
    pointer(r.left-20,r.top-20,0);Sleep(250);ok=capture_state("04-move-outside",browser) && ok;
    pointer(p.x,p.y,0);Sleep(250);ok=capture_state("04-return",browser) && ok;
    /* Repeat on the same button; release is unconditional even after a capture failure. */
    if(!activate_owned_window(browser)) return 7;
    event.mi.dwFlags=MOUSEEVENTF_LEFTDOWN;held=SendInput(1,&event,sizeof(event))==1;
    if(!held)return 8;
    Sleep(250);ok=capture_state("05-second-down",browser) && ok;
    event.mi.dwFlags=MOUSEEVENTF_LEFTUP;SendInput(1,&event,sizeof(event));held=0;
    Sleep(250);ok=capture_state("06-second-up",browser) && ok;
    if(!activate_owned_window(browser))return 7;
    press_key(VK_ESCAPE);Sleep(250);ok=capture_state("07-escape",browser) && ok;
    return ok?0:9;
}
int main(int argc,char **argv)
{
    STARTUPINFOW startup={sizeof(startup)};PROCESS_INFORMATION process;WCHAR command[4096],**args;
    HWND hwnd;int n,status;
    if(argc!=3 && argc!=4){fputs("path-observer.exe FSViewer.exe synthetic-browser-image [classic]\n",stderr);return 2;}
    classic=argc==4 && !strcmp(argv[3],"classic");if(argc==4 && !classic)return 2;
    SetProcessDPIAware();setvbuf(stdout,NULL,_IONBF,0);
    args=CommandLineToArgvW(GetCommandLineW(),&n);if(!args || n!=argc)return 2;
    if(wcslen(args[1])+wcslen(args[2])+6>=ARRAYSIZE(command)){LocalFree(args);return 2;}
    swprintf(command,ARRAYSIZE(command),L"\"%ls\" \"%ls\"",args[1],args[2]);LocalFree(args);
    if(!CreateProcessW(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&startup,&process))return 3;
    pid=process.dwProcessId;app_process=process.hProcess;
    hwnd=wait_window(NULL,NULL);Sleep(1000);
    status=hwnd?observe_path(hwnd):4;
    TerminateProcess(process.hProcess,status);WaitForSingleObject(process.hProcess,5000);
    CloseHandle(process.hThread);CloseHandle(process.hProcess);
    return status;
}
