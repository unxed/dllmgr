#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static LONGLONG frequency;
static double now_ms(void){LARGE_INTEGER q;QueryPerformanceCounter(&q);return q.QuadPart*1000.0/frequency;}
#define MAX_FONTS 128
static LOGFONTW fonts[MAX_FONTS];static unsigned count,limit;
static int CALLBACK collect(const LOGFONTW *lf,const TEXTMETRICW *tm,DWORD type,LPARAM unused)
{fonts[count++]=*lf;return count<limit;}
static void measure(HDC dc)
{
    unsigned i;SIZE size;
    for(i=0;i<count;i++){
        HFONT font=CreateFontIndirectW(fonts+i);HGDIOBJ old=SelectObject(dc,font);
        if(!font || !old || !GetTextExtentPoint32W(dc,L"The quick brown fox / Текст",26,&size)){fputs("font operation failed\n",stderr);exit(2);}
        SelectObject(dc,old);DeleteObject(font);
    }
}
int main(void)
{
    const unsigned limits[]={4,8,12,16,32,128};HDC dc=GetDC(NULL);LOGFONTW lf={0};unsigned i,round;
    {LARGE_INTEGER f;QueryPerformanceFrequency(&f);frequency=f.QuadPart;}
    lf.lfCharSet=DEFAULT_CHARSET;
    for(i=0;i<sizeof(limits)/sizeof(limits[0]);i++){
        double start,first,warm;limit=limits[i];count=0;
        EnumFontFamiliesExW(dc,&lf,collect,0,0);
        start=now_ms();measure(dc);first=now_ms()-start;
        start=now_ms();for(round=0;round<20;round++)measure(dc);warm=now_ms()-start;
        printf("fonts=%u first_ms=%.3f repeated_20_ms=%.3f repeated_per_pass=%.3f\n",count,first,warm,warm/20.0);fflush(stdout);
    }
    ReleaseDC(NULL,dc);return 0;
}
