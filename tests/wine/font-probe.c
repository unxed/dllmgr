/* Read-only font enumeration/selection timings, without changing prefix settings. */
#include <windows.h>
#include <stdio.h>
static unsigned count;
static int CALLBACK family(const LOGFONTA *font,const TEXTMETRICA *metrics,DWORD type,LPARAM arg)
{ count++;return 1; }
int main(void)
{
    HDC dc=GetDC(NULL); LOGFONTA font={0}; DWORD start; int i;
    font.lfCharSet=DEFAULT_CHARSET;
    for(i=0;i<3;i++){
        count=0;start=GetTickCount();EnumFontFamiliesExA(dc,&font,(FONTENUMPROCA)family,0,0);
        printf("enumeration_%d entries=%u elapsed_ms=%lu\n",i+1,count,GetTickCount()-start);
    }
    for(i=0;i<4;i++){
        const WCHAR text[]=L"Rotation, sizes, text / Поворот, размеры, текст";
        HFONT selected=CreateFontA(i<2?-14:-28,0,0,0,i%2?FW_BOLD:FW_NORMAL,0,0,0,DEFAULT_CHARSET,0,0,DEFAULT_QUALITY,0,"Tahoma");
        HFONT old=SelectObject(dc,selected);char name[128];TEXTMETRICA metrics;SIZE size;
        GetTextFaceA(dc,sizeof(name),name);GetTextMetricsA(dc,&metrics);GetTextExtentPoint32W(dc,text,lstrlenW(text),&size);
        printf("selected=%s height=%ld weight=%ld text_width=%ld text_height=%ld\n",name,metrics.tmHeight,metrics.tmWeight,size.cx,size.cy);
        SelectObject(dc,old);DeleteObject(selected);
    }
    ReleaseDC(NULL,dc);return 0;
}
