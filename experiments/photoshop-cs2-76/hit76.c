/* #76: find the screen points where Photoshop CS2's cursor hit test would hand
 * back an unset window pointer (the crash at photoshop+0xb249ce).
 *
 * Behaviour of that hit test, from the README of this directory (plain-text
 * description, no vendor code): for the cursor point P it takes
 * H = WindowFromPoint(P) and its parent/owner G = GetParent(H).
 *  - H or G of class PSViewC: a document view, safe.
 *  - G of class PSDocC or PSFloatC: answer "grow" (5) with the window
 *    GetDlgItem(G, 0).
 *  - H of class PSDocC: WM_NCHITTEST on H; HTNOWHERE/HTTRANSPARENT/HTERROR
 *    is safe, the rest answers 4 or 5 with GetDlgItem(H, 0).
 *  - anything else: safe.
 * When GetDlgItem(..., 0) is NULL the output pointer is never written and the
 * caller dereferences whatever its slot held (the cursor point itself).
 *
 * Usage: hit76.exe [STEP] [loop SECONDS] | hit76.exe 0 struct SECONDS
 *   prints every Photoshop window of the three classes with GetDlgItem(x,0),
 *   then every grid point (STEP px, default 8) that hits the hazard, grouped
 *   by window. With "loop N" it repeats once a second for N seconds and
 *   prints only new hazards, plus the hazard at the current cursor position.
 *   "0 struct N" watches the window tree every 50 ms for N seconds (from
 *   before Photoshop starts) and prints every visible window that would be a
 *   hazard wherever the cursor is on it.
 * Build: i686-w64-mingw32-gcc -O2 -o hit76.exe hit76.c -luser32 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static DWORD ps_pid;

static void cls(HWND h, char *buf, int n)
{
    buf[0] = 0;
    if (h) GetClassNameA(h, buf, n);
}

static int is(HWND h, const char *name)
{
    char c[64];
    cls(h, c, sizeof(c));
    return h && !strcmp(c, name);
}

static void describe(HWND h, char *out, int n)
{
    char c[64], t[80];
    RECT r = {0};
    DWORD pid = 0;
    cls(h, c, sizeof(c));
    t[0] = 0;
    if (h) GetWindowTextA(h, t, sizeof(t));
    if (h) GetWindowRect(h, &r);
    if (h) GetWindowThreadProcessId(h, &pid);
    snprintf(out, n, "%p %s \"%s\" %ld,%ld-%ld,%ld style=%08lx ex=%08lx id=%ld pid=%lx", h, c, t,
             r.left, r.top, r.right, r.bottom, h ? GetWindowLongA(h, GWL_STYLE) : 0,
             h ? GetWindowLongA(h, GWL_EXSTYLE) : 0, h ? GetWindowLongA(h, GWLP_ID) : 0, pid);
}

/* 0 = safe; otherwise the window whose GetDlgItem(.., 0) is NULL */
static HWND hazard(POINT p, HWND *hit, int *part)
{
    HWND h = WindowFromPoint(p), g;
    DWORD_PTR res = 0;
    *hit = h;
    *part = 0;
    if (!h) return 0;
    g = GetParent(h);
    if (is(h, "PSViewC") || is(g, "PSViewC")) return 0;
    if (is(g, "PSDocC") || is(g, "PSFloatC")) {
        *part = 5;
        return GetDlgItem(g, 0) ? 0 : g;
    }
    if (is(h, "PSDocC")) {
        if (!SendMessageTimeoutA(h, WM_NCHITTEST, 0, MAKELPARAM(p.x, p.y), SMTO_ABORTIFHUNG, 500, &res)) return 0;
        if ((LONG)res == HTNOWHERE || (LONG)res == HTTRANSPARENT || (LONG)res == HTERROR) return 0;
        *part = ((LONG)res == HTCLIENT || res == HTHSCROLL || res == HTVSCROLL) ? 5 : 4;
        return GetDlgItem(h, 0) ? 0 : h;
    }
    return 0;
}

static BOOL CALLBACK list_child(HWND h, LPARAM depth)
{
    char d[256], k[256];
    HWND item;
    if (!is(h, "PSDocC") && !is(h, "PSFloatC") && !is(h, "PSViewC")) return TRUE;
    item = GetDlgItem(h, 0);
    describe(h, d, sizeof(d));
    describe(item, k, sizeof(k));
    printf("%swin %s vis=%d parent=%p | GetDlgItem(0)=%s\n", depth ? "  " : "", d, IsWindowVisible(h),
           GetParent(h), item ? k : "NULL");
    return TRUE;
}

static BOOL CALLBACK list(HWND h, LPARAM lp)
{
    DWORD pid;
    GetWindowThreadProcessId(h, &pid);
    if (pid != ps_pid) return TRUE;
    list_child(h, 0);
    EnumChildWindows(h, list_child, 1);
    return TRUE;
}

/* structural hazards: visible windows whose parent/owner is a PSDocC or
 * PSFloatC without a child of id 0, and visible PSDocC windows without one;
 * the cursor on such a window crashes Photoshop */
static int nstruct;
static HWND struct_seen[256];
static int report_struct(HWND h, const char *why, HWND bad, int t)
{
    char a[256], b[256];
    int i;
    for (i = 0; i < nstruct; i++) if (struct_seen[i] == h) return 0;
    if (nstruct < 256) struct_seen[nstruct++] = h;
    describe(h, a, sizeof(a));
    describe(bad, b, sizeof(b));
    printf("t=%dms STRUCT %s hit=[%s] owner=%p | no child id 0 in [%s]\n", t, why, a, GetWindow(h, GW_OWNER), b);
    fflush(stdout);
    return 1;
}
static int struct_t;
static BOOL CALLBACK struct_child(HWND h, LPARAM lp)
{
    HWND g;
    if (!IsWindowVisible(h)) return TRUE;
    g = GetParent(h);
    if ((is(g, "PSDocC") || is(g, "PSFloatC")) && !GetDlgItem(g, 0)) report_struct(h, "parent", g, struct_t);
    if (is(h, "PSDocC") && !GetDlgItem(h, 0)) report_struct(h, "self", h, struct_t);
    return TRUE;
}
static BOOL CALLBACK struct_top(HWND h, LPARAM lp)
{
    DWORD pid;
    GetWindowThreadProcessId(h, &pid);
    if (pid != ps_pid) return TRUE;
    struct_child(h, 0);
    EnumChildWindows(h, struct_child, 0);
    return TRUE;
}
static BOOL CALLBACK find_ps(HWND h, LPARAM lp)
{
    if (is(h, "Photoshop") || is(h, "PSFloatC") || is(h, "PSDocC")) {
        GetWindowThreadProcessId(h, &ps_pid);
        return FALSE;
    }
    return TRUE;
}

#define MAXSEEN 256
static HWND seen_hit[MAXSEEN];
static int nseen;

static int scan(int step, int quiet)
{
    int x0 = GetSystemMetrics(SM_XVIRTUALSCREEN), y0 = GetSystemMetrics(SM_YVIRTUALSCREEN);
    int w = GetSystemMetrics(SM_CXVIRTUALSCREEN), hgt = GetSystemMetrics(SM_CYVIRTUALSCREEN);
    int n = 0, i;
    POINT p;
    for (p.y = y0; p.y < y0 + hgt; p.y += step)
        for (p.x = x0; p.x < x0 + w; p.x += step) {
            HWND hit, bad;
            int part;
            char a[256], b[256];
            if (!(bad = hazard(p, &hit, &part))) continue;
            n++;
            for (i = 0; i < nseen; i++) if (seen_hit[i] == hit) break;
            if (i < nseen) continue;
            if (nseen < MAXSEEN) seen_hit[nseen++] = hit;
            describe(hit, a, sizeof(a));
            describe(bad, b, sizeof(b));
            printf("HAZARD at %ld,%ld part=%d hit=[%s] owner=%p | no child id 0 in [%s]\n", p.x, p.y, part, a,
                   GetWindow(hit, GW_OWNER), b);
        }
    if (!quiet) printf("hazard points: %d (step %d, screen %dx%d)\n", n, step, w, hgt);
    fflush(stdout);
    return n;
}

int main(int argc, char **argv)
{
    int step = argc > 1 ? atoi(argv[1]) : 8, secs = 0, t;
    HWND main_hwnd = FindWindowA("Photoshop", NULL);

    if (argc > 3 && !strcmp(argv[2], "struct")) {
        /* watch the window tree every 50 ms for argv[3] seconds, from before
         * Photoshop's first window (splash) on */
        DWORD start = GetTickCount(), end = start + atoi(argv[3]) * 1000;
        while (GetTickCount() < end) {
            if (!ps_pid) EnumWindows(find_ps, 0);
            if (ps_pid) {
                struct_t = GetTickCount() - start;
                EnumWindows(struct_top, 0);
            }
            Sleep(50);
        }
        printf("struct watch done, %d hazard window(s)\n", nstruct);
        return 0;
    }
    if (argc > 3 && !strcmp(argv[2], "loop")) secs = atoi(argv[3]);
    if (!main_hwnd) { printf("no Photoshop main window\n"); return 1; }
    GetWindowThreadProcessId(main_hwnd, &ps_pid);
    if (!secs) {
        EnumWindows(list, 0);
        scan(step, 0);
        return 0;
    }
    for (t = 0; t < secs; t++) {
        POINT c;
        HWND hit, bad;
        int part;
        GetCursorPos(&c);
        if ((bad = hazard(c, &hit, &part))) {
            char a[256], b[256];
            describe(hit, a, sizeof(a));
            describe(bad, b, sizeof(b));
            printf("t=%d CURSOR HAZARD at %ld,%ld part=%d hit=[%s] | [%s]\n", t, c.x, c.y, part, a, b);
        }
        scan(step, 1);
        Sleep(1000);
    }
    return 0;
}
