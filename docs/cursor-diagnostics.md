# Passive cursor diagnostics

The owner's slow physical pointer over FastStone is not yet reproduced by
a measured physical-motion sample. Do not infer pointer acceleration from
synthetic motion or from the two coordinate spaces at 192 DPI.

Two bounded helpers collect evidence without moving the pointer, activating
windows, grabbing input or changing mouse settings:

```sh
python3 tools/cursor-sample.py --seconds 30 --raw > cursor-x11.jsonl &
i686-w64-mingw32-gcc -O2 -Wall -Wextra -Werror \
  tests/wine/cursor-probe.c -o cursor-probe.exe -luser32
WINEDEBUG=-all wine cursor-probe.exe --seconds 30 > cursor-wine.jsonl
wait
```

The X11 helper requires python3-xlib; `--raw` also requires xinput and
stdbuf. It retains coordinates, window IDs/classes and RawMotion device/axis
values, excluding titles, key events and button events. Keep raw captures
private until reviewed. Start both samplers together, then physically move
the mouse across FastStone and a comparison window. Pause at each endpoint
for at least 150 ms: Wine can cache cursor position for 100 ms.

Identify the physical RawMotion source and X/Y axes before comparing physical
deltas with screen travel. Master and slave events can describe the same
motion; adding them doubles the input. Raw timestamps are receipt times.
The Wine helper records aware/unaware coordinates, clipping, cursor info and
mouse parameters. Its DPI changes affect only its own thread and are restored.
Wine 11's GetPhysicalCursorPos aliases GetCursorPos, so it supplies no
independent physical-motion check.

Both helpers compiled/started successfully on the local laptop. A two-second
stationary smoke check produced valid JSONL and no RawMotion events; it
verifies collection only, not the reported slow-pointer symptom.
