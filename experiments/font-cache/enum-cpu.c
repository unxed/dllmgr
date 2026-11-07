#include <windows.h>
#include <stdio.h>
#include <string.h>
static unsigned count;
static int mode;
static unsigned errors;
static unsigned long long checksum;
static void mix(unsigned value){checksum=(checksum^value)*1099511628211ULL;}
static ULONGLONG cpu_time(void)
{
    FILETIME created,exited,kernel,user;ULARGE_INTEGER k,u;
    if(!GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user))return 0;
    k.LowPart=kernel.dwLowDateTime;k.HighPart=kernel.dwHighDateTime;
    u.LowPart=user.dwLowDateTime;u.HighPart=user.dwHighDateTime;
    return k.QuadPart+u.QuadPart;
}
static int CALLBACK visit(const LOGFONTW *lf,const TEXTMETRICW *tm,DWORD type,LPARAM ctx)
{
    HDC dc=(HDC)ctx;HFONT font;HGDIOBJ old;SIZE size;TEXTMETRICW metrics;
    count++;
    if(!mode)return 1;
    font=CreateFontIndirectW(lf);old=SelectObject(dc,font);
    if(!font||!old){errors++;return 0;}
    if(mode==1){if(!GetTextExtentPoint32W(dc,L"The quick brown fox / Текст",26,&size))errors++;else{mix(size.cx);mix(size.cy);}}
    if(mode==3){if(!GetTextMetricsW(dc,&metrics))errors++;else{mix(metrics.tmHeight);mix(metrics.tmWeight);}}
    SelectObject(dc,old);DeleteObject(font);return 1;
}
int main(void)
{
    HDC dc=GetDC(NULL);LOGFONTW lf={0};int round;
    if(!dc)return 3;lf.lfCharSet=DEFAULT_CHARSET;
    for(mode=0;mode<4;mode++)for(round=0;round<2;round++)
    {
        DWORD start=GetTickCount();ULONGLONG cpu=cpu_time();count=0;checksum=14695981039346656037ULL;
        EnumFontFamiliesExW(dc,&lf,visit,(LPARAM)dc,0);
        printf("mode=%d round=%d callbacks=%u wall_ms=%lu cpu_ms=%.1f checksum=%016llx errors=%u\n",mode,round,count,GetTickCount()-start,(cpu_time()-cpu)/10000.0,checksum,errors);
        fflush(stdout);
    }
    ReleaseDC(NULL,dc);return errors?2:0;
}
