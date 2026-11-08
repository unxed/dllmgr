#!/usr/bin/env python3
"""Small, dependency-free presentation helpers for dllmgr's terminal commands."""

import os
import sys


def use_color():
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def emit(kind, message):
    styles = {"title": "1;36", "step": "36", "ok": "32", "note": "2", "warn": "33"}
    marks = {"title": "dllmgr / Wine fixes", "step": "›", "ok": "✓", "note": "·", "warn": "!"}
    mark = marks[kind]
    line = "dllmgr / Wine fixes" if kind == "title" else f"{mark}  {message}"
    if use_color():
        line = f"\033[{styles[kind]}m{line}\033[0m"
    print(line)


class Progress:
    """One-line progress bar on stderr for slow steps (downloads, copying).

    On a terminal it redraws `› label  [#####.....]  45%  120/266 MB` at most
    ten times a second and ends with a newline; otherwise it prints the label
    once, so logs stay short. total may be 0 (unknown size): then only the
    amount done is shown.
    """

    def __init__(self, label, total=0):
        import time
        self._time = time.monotonic
        self.label, self.total, self.done, self._last = label, total, 0, 0.0
        self.tty = sys.stderr.isatty()
        if not self.tty:
            print(f"›  {label}", file=sys.stderr, flush=True)
        else:
            self._draw()

    def _draw(self):
        mb = lambda n: n / (1024 * 1024)
        if self.total:
            frac = min(self.done / self.total, 1.0)
            bar = "#" * int(frac * 20)
            text = f"\r›  {self.label}  [{bar:.<20}] {frac * 100:3.0f}%  {mb(self.done):.0f}/{mb(self.total):.0f} MB"
        else:
            text = f"\r›  {self.label}  {mb(self.done):.0f} MB"
        sys.stderr.write(text + "\033[K")
        sys.stderr.flush()

    def update(self, amount):
        self.done += amount
        now = self._time()
        if self.tty and now - self._last >= 0.1:
            self._last = now
            self._draw()

    def close(self):
        if self.tty:
            self.done = max(self.done, self.total)
            self._draw()
            sys.stderr.write("\n")
            sys.stderr.flush()


if __name__ == "__main__":
    if len(sys.argv) < 2 or (sys.argv[1] != "title" and len(sys.argv) < 3):
        raise SystemExit("usage: ui.py KIND [MESSAGE]")
    emit(sys.argv[1], " ".join(sys.argv[2:]))
