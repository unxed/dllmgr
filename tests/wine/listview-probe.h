#ifndef FASTSTONE_LISTVIEW_PROBE_H
#define FASTSTONE_LISTVIEW_PROBE_H

/* Log Win32 ListView geometry without changing FastStone's selection. */
void observe_listviews(const char *stage, HANDLE process, DWORD pid);

/* Client position of item 0. Unlike GetScrollInfo, this also works for
 * another process's list-view under Wine, so wheel scrolling can be measured. */
BOOL listview_item0_position(HWND hwnd, HANDLE process, POINT *position);

#endif
