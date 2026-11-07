#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
static const WCHAR heading1[]=L"Файл, слайдшоу";
static const WCHAR heading2[]=L"Поворот, размеры, текст";
int wmain(int argc,WCHAR **argv)
{
    HDC screen=GetDC(NULL),dc=CreateCompatibleDC(screen);
    BITMAPINFO info={{sizeof(BITMAPINFOHEADER),1300,-220,1,32,BI_RGB}};
    void *bits; HBITMAP bitmap=CreateDIBSection(screen,&info,DIB_RGB_COLORS,&bits,NULL,0);
    HGDIOBJ oldbmp=SelectObject(dc,bitmap),oldfont;HFONT font;DWORD bytes;void *names;
    BITMAPFILEHEADER fileheader={0x4d42,sizeof(fileheader)+sizeof(info.bmiHeader)+1300*220*4,0,0,sizeof(fileheader)+sizeof(info.bmiHeader)};
    FILE *output;int i,private=0;
    if(argc!=3)return 2;
    if(wcscmp(argv[1],L"-")) { private=AddFontResourceExW(argv[1],FR_PRIVATE,NULL);printf("private_faces=%d\n",private);if(!private)return 3; }
    memset(bits,255,1300*220*4);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(0,0,0));
    font=CreateFontW(-36,0,0,0,FW_BOLD,0,0,0,RUSSIAN_CHARSET,0,0,ANTIALIASED_QUALITY,0,L"Tahoma");oldfont=SelectObject(dc,font);
    TextOutW(dc,10,10,heading1,lstrlenW(heading1));TextOutW(dc,10,65,heading2,lstrlenW(heading2));
    bytes=GetFontData(dc,0x656d616e,0,NULL,0);names=malloc(bytes==GDI_ERROR?1:bytes);
    if(bytes!=GDI_ERROR && GetFontData(dc,0x656d616e,0,names,bytes)!=GDI_ERROR){
        const WCHAR *tag=L"WineTahomaBoldCyrillic";int n=lstrlenW(tag),j,k,match=0;
        for(j=0;j+(n*2)<=bytes;j++){for(k=0;k<n;k++)if(((BYTE*)names)[j+2*k]!=0 || ((BYTE*)names)[j+2*k+1]!=tag[k])break;if(k==n)match=1;}
        printf("selected_corrected_font=%d\n",match);
    }
    free(names);
    for(i=0;i<4;i++){
        WCHAR ch[]=L"Файx";SIZE extent;int x,y,ink=0;RECT r={0,120,1300,220};FillRect(dc,&r,(HBRUSH)GetStockObject(WHITE_BRUSH));
        TextOutW(dc,10,125,&ch[i],1);GetTextExtentPoint32W(dc,&ch[i],1,&extent);
        for(y=125;y<180;y++)for(x=10;x<10+extent.cx;x++)if(GetPixel(dc,x,y)!=RGB(255,255,255))ink++;
        printf("U+%04X advance=%ld ink_pixels=%d\n",ch[i],extent.cx,ink);
    }
    output=_wfopen(argv[2],L"wb");if(!output)return 4;
    fwrite(&fileheader,sizeof(fileheader),1,output);fwrite(&info.bmiHeader,sizeof(info.bmiHeader),1,output);fwrite(bits,1300*220*4,1,output);fclose(output);
    SelectObject(dc,oldfont);DeleteObject(font);SelectObject(dc,oldbmp);DeleteObject(bitmap);DeleteDC(dc);ReleaseDC(NULL,screen);
    if(private)RemoveFontResourceExW(argv[1],FR_PRIVATE,NULL);
    return 0;
}
