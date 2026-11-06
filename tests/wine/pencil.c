/* Does GDI+ inherit the HDC's GDI ROP2? WineHQ 48874 candidate reproducer. */
#include <windows.h>
#include <gdiplus.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    GdiplusStartupInput input = {1, NULL, FALSE, FALSE};
    ULONG_PTR token;
    int i, depth, failures = 0;
    const int modes[] = {R2_COPYPEN, R2_BLACK, R2_WHITE, R2_NOTXORPEN};
    GpPointF points[] = {{10,50}, {90,50}};
    if (GdiplusStartup(&token,&input,NULL) != Ok) return 2;
    for (depth = 24; depth <= 32; depth += 8)
    for (i = 0; i < sizeof(modes)/sizeof(modes[0]); i++)
    {
        BITMAPINFO info = {{sizeof(BITMAPINFOHEADER),100,-100,1,depth,BI_RGB}};
        HDC dc = CreateCompatibleDC(NULL);
        void *bits;
        HBITMAP bitmap = CreateDIBSection(dc,&info,DIB_RGB_COLORS,&bits,NULL,0);
        HGDIOBJ old = SelectObject(dc,bitmap);
        GpGraphics *graphics;
        GpPen *pen;
        GpStatus status;
        COLORREF color;
        memset(bits,255,100*100*(depth/8));
        SetROP2(dc,modes[i]);
        GdipCreateFromHDC(dc,&graphics);
        GdipSetSmoothingMode(graphics,5);
        GdipCreatePen1(0xffff0000,3.0,UnitWorld,&pen);
        GdipSetPenLineCap197819(pen,LineCapRound,LineCapRound,DashCapFlat);
        GdipSetPenLineJoin(pen,LineJoinRound);
        status = GdipDrawLines(graphics,pen,points,2);
        GdipDeletePen(pen); GdipDeleteGraphics(graphics);
        color = GetPixel(dc,50,50);
        printf("depth=%d ROP2=%d status=%d pixel=%06lx preserved-ROP2=%d\n",depth,modes[i],status,color,GetROP2(dc));
        if (status != Ok || color != RGB(255,0,0) || GetROP2(dc) != modes[i]) failures++;
        SelectObject(dc,old); DeleteObject(bitmap); DeleteDC(dc);
    }
    GdiplusShutdown(token);
    printf("Failures: %d\n",failures);
    return argc > 1 && !strcmp(argv[1],"--check") ? !!failures : 0;
}
