#include <windows.h>
#include <commctrl.h>
int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    HWND w, c, c2;
    MSG msg;
    HFONT f = CreateFontA(-11, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, 0, 0, "Tahoma");
    InitCommonControls();
    w = CreateWindowA("STATIC", "combo", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 300, 150, 0, 0, inst, 0);
    c = CreateWindowA("COMBOBOX", "", WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST, 10, 10, 120, 100, w, 0, inst, 0);
    c2 = CreateWindowA("COMBOBOX", "", WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST, 10, 50, 120, 100, w, 0, inst, 0);
    SendMessageA(c2, WM_SETFONT, (WPARAM)f, 0);
    SendMessageA(c, CB_ADDSTRING, 0, (LPARAM)"Normal"); SendMessageA(c, CB_SETCURSEL, 0, 0);
    SendMessageA(c2, CB_ADDSTRING, 0, (LPARAM)"Normal"); SendMessageA(c2, CB_SETCURSEL, 0, 0);
    SetTimer(0, 0, 8000, 0);
    while (GetMessageA(&msg, 0, 0, 0)) { if (msg.message == WM_TIMER) break; DispatchMessageA(&msg); }
    return 0;
}
