/* curwatch SECONDS: print the X cursor image (size, hotspot, name, hash) whenever it changes, with ms timestamps (#70) */
#include <X11/Xlib.h>
#include <X11/extensions/Xfixes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
static long ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000 + t.tv_nsec / 1000000; }
int main(int argc, char **argv)
{
    Display *d = XOpenDisplay(NULL);
    long start = ms(), limit = (argc > 1 ? atol(argv[1]) : 10) * 1000;
    unsigned long last = 0;
    if (!d) return 1;
    while (ms() - start < limit) {
        XFixesCursorImage *c = XFixesGetCursorImage(d);
        unsigned long h = 1469598103934665603UL; int i;
        if (!c) break;
        for (i = 0; i < c->width * c->height; i++) h = (h ^ (unsigned long)c->pixels[i]) * 1099511628211UL;
        if (h != last) {
            printf("%6ld ms  %dx%d hot %d,%d serial %lu name %s hash %016lx\n", ms() - start, c->width, c->height,
                   c->xhot, c->yhot, c->cursor_serial, c->name ? c->name : "-", h);
            fflush(stdout); last = h;
        }
        XFree(c); usleep(20000);
    }
    return 0;
}
