# #76: Photoshop CS2 crash at photoshop+0xb249ce (2026-11-11)

Owner, 2026-11-10 13:2x, runtime v18, "I did nothing":
page fault reading 0x76bb1800 at photoshop+0xb249ce, EAX=ECX=0x76bb1800,
EDI=5 (experiments/owner-2026-11-10/crash-backtrace.txt).

## Crash report of the proxy

The dllmgr-27 crash report (04abb5f, runtime v19+) writes `dllmgr76:` lines
to stderr, i.e. the run log `.dllmgr/runs/run-TIME.log` of the prefix (and
`.dllmgr/trampoline-run.log` for the trampoline path); `dllmgr run` repeats
the module in its verdict line. The owner's crash was on v18, before the
report existed; experiments/owner-* holds only the winedbg backtrace, no
`dllmgr76:` report.

## Hypotheses 1 and 2 (system DLL base, unloaded DLL): ruled out

- No module of Photoshop CS2 has bound imports (`objdump -p`: Bound Import
  Directory 0 in Photoshop.exe and every DLL of the install). psapi comes in
  only through Photoshop.exe's delay imports (GetProcessMemoryInfo), resolved
  by name. 0x76bb1800 is not a pointer at all (below).
- Nothing in the backtrace or the stand runs was mapped at 0x76bb0000.

## Cause: a Photoshop hit test that leaves its output unset

Plain-text description of the behaviour (interoperability reading of
Photoshop.exe only, tools: `iat-names.py`, `pe-string.py`, objdump of a few
small windows):

- Photoshop.exe takes user32 through its delay imports
  (`iat-names.py Photoshop.exe` lists them). Its window classes, from
  Photoshop.dll's string table: `PSDocC` (document window), `PSViewC`
  (content view, the child with id 0 of every document and palette window),
  `PSFloatC` (palettes, options bar, splash, Photoshop's own dialogs).
- The function at photoshop+0xb01a90 is the FindWindow of Photoshop's Mac
  layer: (screen point, out window record) -> part code (0 desk, 3 content,
  4 drag, 5 grow). It takes H = WindowFromPoint(point), G = GetParent(H)
  (the owner for popups). H or G of class PSViewC -> content. G of class
  PSDocC or PSFloatC -> part 5 with window GetDlgItem(G, 0). H of class
  PSDocC -> WM_NCHITTEST, then part 4/5 with GetDlgItem(H, 0). The record is
  read from that window (GetWindowLong index 0 and two fields).
  **When GetDlgItem(.., 0) returns NULL it returns the part code but never
  writes the record.**
- Caller photoshop+0x4a0130 (palette code; it is reached from
  photoshop+0x4a0280, which reads GetCursorPos) passes the address of the
  very stack slot that holds the cursor point as the out pointer. With the
  record unwritten, the point is taken as a record pointer: the next function
  (photoshop+0xb249a0) reads record+0x78 and calls a virtual method on what
  it finds there.
- The owner's registers match this exactly: EDI=5 (part "grow", the
  GetDlgItem path), and the stack slot of the record still holds 0x0338010a,
  the cursor point (x=824, y=266 in Photoshop's 1536x864 logical
  coordinates; also kept in the caller's local copy at 0x0022ebcc). Reading
  0x0338010a+0x78 gave heap data 0x76bb1800, which was then dereferenced.

So the crash needs, under the cursor, a window that is (or is owned by / a
child of) a PSDocC or PSFloatC window without a child of id 0, at a moment
when the palette caller runs. The defect is Photoshop's; the trigger state
is what Wine (or the moment) adds.

## Stand work (runtime v21, :134, Muffin, 192 DPI)

- `hit76.c`: lists the PSDocC/PSFloatC/PSViewC windows with GetDlgItem(x,0),
  scans the screen for points where the hit test would hit the empty path,
  and (`0 struct N`) watches the window tree every 50 ms for such windows.
  Positive control: a childless PSFloatC owning a popup is reported.
- `t76.sh` (SCEN unset / owner / drag / fake): startup with the F26 box,
  idle hover sweep with tool tips, File menu, Page Setup, Print with Preview,
  Print (and its "clipping" warning), File > Close; zoom tool, Alt+wheel
  zoom, the owner's crash point idle, Actual Pixels/Fit Screen/Print Size,
  palette well (Brushes), the three screen modes, Tab, document resize;
  palette and toolbox drags. **No crash, no hazard point on screen.** The
  only structural hazard seen: a visible but off-screen childless PSDocC at
  10006,10086 (never under the cursor).
- `fake76.c`: synthetic trigger, a childless window of class PSDocC, or a
  popup owned by a childless PSFloatC (class atoms are shared, so Photoshop
  takes them for its own). The popup reaches the empty path ~900 times in
  15 s, but through other callers of the hit test (+0xa76688, +0x748cd3,
  +0xa73dcf), which survive the unset record; the crashing palette caller
  +0x4a0130 was not reached in any stand scenario (`guard-run.txt`).
  The PSDocC variant did not reach GetDlgItem at all.

Not reproduced: the real trigger window is still unknown. Candidates: a
transient window (shorter than the 50 ms watch) during palette work, or a
window that the owner's longer session had and the stand does not.

## Fix: in-process guard in the dllmgr-27 proxy (implemented)

patches/dllmgr-27/prefill.c, "#76 hit-test guard", on by default,
`DLLMGR76_NO_GUARD=1` turns it off: only for Photoshop.exe 9.0 (link stamp
0x42400fac) the delay-import slot of GetDlgItem gets a hook that acts only
for the call made from the hit test (return address checked, and the call
instruction must go through that very slot). When GetDlgItem(.., 0) is NULL
there and the caller's frame looks as expected (part 4/5, record pointer on
the same stack), it sets record = NULL and part = 0, the hit test's own
answer for HTNOWHERE ("nothing here"), which every caller handles. It logs
`dllmgr76: guard: hit test from exe+0x.. on HWND (class ..)` once per window,
so the owner's next run log names the trigger. `DLLMGR76_TRACE=N` logs the
first N GetDlgItem calls of the hit test (caller, point, window, result).
Checked on the stand: the hook is installed, Photoshop starts and works, the
guard fires on the synthetic trigger and Photoshop stays up (`guard-run.txt`).
It is a workaround for Photoshop's own bug; no Wine patch is involved, so
nothing goes to docs/upstream-outbox.md until the trigger is known (if the
trigger turns out to be a Wine window-tree difference, that is the report).

## Next steps

1. Ship the proxy (next runtime/proxy build) and ask nothing of the owner:
   if the trigger recurs, his run log will hold a `dllmgr76: guard:` line
   with the window class instead of a crash.
2. To reproduce: find what makes Photoshop run photoshop+0x4a0280 (callers
   at +0x4898e1, +0x48a1d8, +0x48c035, +0x4958fd, palette code) and run that
   with `fake76.exe PSFloatC 15 owned` under the cursor and
   `DLLMGR76_TRACE`/`DLLMGR76_NO_GUARD=1` to show crash vs. guard.

Files: `hit76.c`, `fake76.c` (build lines in their headers), `t76.sh`,
`iat-names.py`, `pe-string.py`, `guard-run.txt`.
