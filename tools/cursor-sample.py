#!/usr/bin/env python3
"""Passively sample the X11 pointer; never move it, grab it, or activate windows.

Requires python3-xlib. Optional --raw uses xinput and stdbuf, retaining only
RawMotion device IDs and valuators (no titles, key events, or button events).
The raw values are reported by axis number: identify the physical source and
its X/Y axes before normalizing motion; do not add master and slave events.
"""

import argparse
import json
import os
import re
import selectors
import shutil
import subprocess
import sys
import time


def emit(kind, **fields):
    print(json.dumps({"kind": kind, "unix_ns": time.time_ns(),
                      "monotonic_ns": time.monotonic_ns(), **fields}), flush=True)


def window_id(window):
    return getattr(window, "id", window)


def pointer_sample(root, display, xerror):
    pointer = root.query_pointer()
    child = pointer.child
    leaf = window_id(child)
    wm_class = None
    class_window = None
    # A window manager frame may lack WM_CLASS; inspect the child under the
    # pointer, without enumerating unrelated windows or reading their titles.
    for _ in range(16):
        if not hasattr(child, "query_pointer"):
            break
        try:
            candidate = child.get_wm_class()
            if candidate:
                wm_class, class_window = candidate, child.id
            leaf = child.id
            child = child.query_pointer().child
        except xerror.BadWindow:
            break  # The window disappeared between queries.
    emit("pointer", same_screen=bool(pointer.same_screen),
         x=pointer.root_x, y=pointer.root_y, root=root.id,
         root_child=window_id(pointer.child), window=leaf,
         class_window=class_window, wm_class=wm_class,
         focus=window_id(display.get_input_focus().focus))


class RawMotion:
    """Parse only RawMotion blocks from xinput's human-readable stream."""

    def __init__(self):
        self.event = None
        self.count = 0

    def line(self, line):
        if line.startswith("EVENT type"):
            self.flush()
            if "(RawMotion)" in line:
                self.event = {"unix_ns": time.time_ns(),
                              "monotonic_ns": time.monotonic_ns(),
                              "device": None, "source": None, "axes": {}}
        elif self.event is not None:
            device = re.match(r"\s*device:\s*(\d+)\s*\((\d+)\)", line)
            axis = re.match(r"\s*(\d+):\s*([-+\d.eE]+)\s*\(([-+\d.eE]+)\)", line)
            if device:
                self.event.update(device=int(device[1]), source=int(device[2]))
            elif axis:
                self.event["axes"][axis[1]] = {
                    "delta": float(axis[2]), "raw_delta": float(axis[3])}

    def flush(self):
        if self.event is not None:
            emit("raw_motion", **self.event)
            self.count += 1
            self.event = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=15,
                        help="duration in seconds, greater than 0 and at most 60")
    parser.add_argument("--interval-ms", type=int, default=20,
                        help="pointer sampling interval, 10..1000 ms (default 20)")
    parser.add_argument("--raw", action="store_true",
                        help="also retain xinput RawMotion device/axis evidence")
    args = parser.parse_args()
    if not 0 < args.seconds <= 60 or not 10 <= args.interval_ms <= 1000:
        parser.error("require 0 < seconds <= 60 and 10 <= interval-ms <= 1000")
    try:
        from Xlib import display, error
    except ImportError:
        parser.error("python3-xlib is required")

    raw_command = None
    if args.raw:
        if not shutil.which("xinput") or not shutil.which("stdbuf"):
            parser.error("--raw requires xinput and stdbuf; omit it for coordinates only")
        raw_command = ["stdbuf", "-oL", "xinput", "test-xi2", "--root"]
    connection = display.Display()
    root = connection.screen().root
    process = None
    selector = selectors.DefaultSelector()
    raw = RawMotion()
    pending = b""
    try:
        if raw_command:
            process = subprocess.Popen(raw_command, stdout=subprocess.PIPE,
                                       env={**os.environ, "LC_ALL": "C"})
            selector.register(process.stdout, selectors.EVENT_READ)
        emit("start", seconds=args.seconds, interval_ms=args.interval_ms,
             raw_requested=args.raw,
             raw_timestamps="receipt time; not device timestamps",
             note="No physical normalization when RawMotion evidence is absent")
        deadline = time.monotonic() + args.seconds
        next_sample = time.monotonic()
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_sample:
                pointer_sample(root, connection, error)
                next_sample = now + args.interval_ms / 1000
            timeout = max(0, min(next_sample, deadline) - time.monotonic())
            for key, _ in selector.select(timeout):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    emit("raw_stream_closed", note="RawMotion collection ended")
                    continue
                pending += chunk
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    raw.line(line.decode("ascii", errors="replace"))
    except KeyboardInterrupt:
        pass
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()
        raw.flush()
        selector.close()
        connection.close()
        emit("stop", raw_motion_events=raw.count,
             note="Verify physical source and axis IDs before normalizing deltas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
