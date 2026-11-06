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


if __name__ == "__main__":
    if len(sys.argv) < 2 or (sys.argv[1] != "title" and len(sys.argv) < 3):
        raise SystemExit("usage: ui.py KIND [MESSAGE]")
    emit(sys.argv[1], " ".join(sys.argv[2:]))
