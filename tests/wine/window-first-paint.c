/* Public-API diagnostic for #27: reveal an unpainted popup over a painted one.
 * Observations only: uninitialized pixels are not asserted as a Windows contract. */
#include <windows.h>
#include <stdio.h>

static BOOL paint_popup;
static LRESULT CALLBACK procedure(HWND window,UINT message,WPARAM wparam,LPARAM lparam)
{
    if(message==WM_NCCREATE)
        SetWindowLongPtrW(window,GWLP_USERDATA,(LONG_PTR)((CREATESTRUCTW *)lparam)->lpCreateParams);
    if(message==WM_PAINT) {
        PAINTSTRUCT paint;HDC dc=BeginPaint(window,&paint);
        if(!GetWindowLongPtrW(window,GWLP_USERDATA) || paint_popup) {
            HBRUSH brush=CreateSolidBrush(RGB(240,204,90));
            FillRect(dc,&paint.rcPaint,brush);DeleteObject(brush);
        }
        EndPaint(window,&paint);return 0;
    }
    return DefWindowProcW(window,message,wparam,lparam);
}
static void sample(const char *stage)
{
    HDC dc=GetDC(NULL);
    COLORREF color=GetPixel(dc,GetSystemMetrics(SM_CXSCREEN)/2,GetSystemMetrics(SM_CYSCREEN)/2);
    ReleaseDC(NULL,dc);
    printf("stage=%s rgb=%02x%02x%02x valid=%d\n",stage,
           GetRValue(color),GetGValue(color),GetBValue(color),color!=CLR_INVALID);
    fflush(stdout);
}
int main(void)
{
    WNDCLASSW cls={0};HWND bottom,popup;
    int width,height;DWORD style=WS_POPUP|WS_CLIPSIBLINGS|WS_CLIPCHILDREN;
    SetProcessDPIAware();width=GetSystemMetrics(SM_CXSCREEN);height=GetSystemMetrics(SM_CYSCREEN);
    cls.lpfnWndProc=procedure;cls.hInstance=GetModuleHandleW(NULL);
    cls.lpszClassName=L"dllmgr-first-paint"; /* No class background brush. */
    if(!RegisterClassW(&cls))return 2;
    bottom=CreateWindowExW(0,cls.lpszClassName,L"synthetic underlay",style,
                          0,0,width,height,NULL,NULL,cls.hInstance,NULL);
    if(!bottom)return 3;
    ShowWindow(bottom,SW_SHOW);UpdateWindow(bottom);GdiFlush();Sleep(100);
    sample("painted-underlay");
    popup=CreateWindowExW(WS_EX_CONTROLPARENT,cls.lpszClassName,L"delayed-paint popup",style,
                         0,0,width,height,bottom,NULL,cls.hInstance,(void *)1);
    if(!popup){DestroyWindow(bottom);return 4;}
    ShowWindow(popup,SW_SHOW);GdiFlush();Sleep(50);sample("shown-before-paint");
    Sleep(250);sample("still-unpainted");
    paint_popup=TRUE;InvalidateRect(popup,NULL,FALSE);UpdateWindow(popup);
    GdiFlush();Sleep(100);sample("painted-popup");
    DestroyWindow(popup);DestroyWindow(bottom);return 0;
}
