/* xsample: judge on-screen flicker from the X server's pixels, independent of
 * Wine's screen DC (which can report surface contents that never reached X,
 * see docs/sandbox-findings.md F18).
 *
 * Samples 9 points (3x3 grid at 25/50/75 %) of the root window via XGetImage
 * until DURATION_MS elapse; phase per sample: image (centre == expected RGB,
 * +-TOL per channel), white / black (all 9 points 0xffffff / 0x000000), else
 * other. Prints only phase transitions plus a summary:
 *   t_ms=... phase=... center=rrggbb
 *   first_image_ms=.. interruptions_after_image=N white=.. black=.. samples=..
 * Exit 0 always on successful sampling; the caller judges the summary
 * (interruptions_after_image must be 0 for a flicker-free first open).
 *
 * Build: gcc -O2 -Wall -o xsample tests/wine/xsample.c -lX11
 * Usage: DISPLAY=:96 ./xsample RRGGBB DURATION_MS [TOL] */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static unsigned long pixel_at(Display *dpy, Window root, int x, int y)
{
    XImage *img = XGetImage(dpy, root, x, y, 1, 1, AllPlanes, ZPixmap);
    unsigned long p;
    if (!img) return 0xff000000UL; /* invalid marker */
    p = XGetPixel(img, 0, 0) & 0xffffff;
    XDestroyImage(img);
    return p;
}

static int close_to(unsigned long a, unsigned long b, int tol)
{
    for (int s = 0; s < 24; s += 8) {
        int d = (int)((a >> s) & 0xff) - (int)((b >> s) & 0xff);
        if (d < -tol || d > tol) return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    Display *dpy;
    Window root;
    XWindowAttributes wa;
    unsigned long expected;
    long duration, start, first_image = -1;
    int tol, samples = 0, interruptions = 0, whites = 0, blacks = 0;
    const char *phase = "none";

    if (argc < 3) {
        fprintf(stderr, "usage: %s RRGGBB DURATION_MS [TOL]\n", argv[0]);
        return 2;
    }
    expected = strtoul(argv[1], NULL, 16);
    duration = atol(argv[2]);
    tol = argc > 3 ? atoi(argv[3]) : 6;
    if (!(dpy = XOpenDisplay(NULL))) return 3;
    root = DefaultRootWindow(dpy);
    XGetWindowAttributes(dpy, root, &wa);
    printf("expected_center=%06lx screen=%dx%d\n", expected, wa.width, wa.height);

    start = now_ms();
    while (now_ms() - start < duration) {
        int xs[3] = {wa.width / 4, wa.width / 2, wa.width * 3 / 4};
        int ys[3] = {wa.height / 4, wa.height / 2, wa.height * 3 / 4};
        int white = 0, black = 0;
        unsigned long center = pixel_at(dpy, root, xs[1], ys[1]);
        const char *now;

        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 3; j++) {
                unsigned long p = (i == 1 && j == 1) ? center : pixel_at(dpy, root, xs[i], ys[j]);
                white += p == 0xffffff;
                black += p == 0x000000;
            }
        samples++;
        if (close_to(center, expected, tol)) now = "image";
        else if (white == 9) now = "white";
        else if (black == 9) now = "black";
        else now = "other";

        if (strcmp(now, phase)) {
            long t = now_ms() - start;
            printf("t_ms=%ld phase=%s center=%06lx\n", t, now, center);
            if (!strcmp(now, "image") && first_image < 0) first_image = t;
            if (first_image >= 0 && strcmp(now, "image")) {
                interruptions++;
                whites += !strcmp(now, "white");
                blacks += !strcmp(now, "black");
            }
            phase = now;
        }
    }
    printf("first_image_ms=%ld interruptions_after_image=%d white=%d black=%d samples=%d\n",
           first_image, interruptions, whites, blacks, samples);
    XCloseDisplay(dpy);
    return 0;
}
