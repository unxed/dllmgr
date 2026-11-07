#include <windows.h>
#include <stdio.h>
static unsigned count;
static int CALLBACK visit(const LOGFONTW *lf,const TEXTMETRICW *tm,DWORD type,LPARAM ctx)
{
    count++;
    if(ctx){ HDC dc=(HDC)ctx;HFONT f=CreateFontIndirectW(lf);HGDIOBJ old=SelectObject(dc,f);SIZE size;
        GetTextExtentPoint32W(dc,L"The quick brown fox / Текст",26,&size);SelectObject(dc,old);DeleteObject(f); }
    return 1;
}
int main(void){HDC dc=GetDC(NULL);LOGFONTW lf={0};int mode,round;lf.lfCharSet=DEFAULT_CHARSET;
    for(mode=0;mode<2;mode++)for(round=0;round<2;round++){DWORD start=GetTickCount();count=0;
        EnumFontFamiliesExW(dc,&lf,visit,mode?(LPARAM)dc:0,0);
        printf("metrics=%d round=%d callbacks=%u ms=%lu\n",mode,round,count,GetTickCount()-start);}
    ReleaseDC(NULL,dc);return 0;}
