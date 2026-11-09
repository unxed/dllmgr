# #43: Photoshop CS2 steals the focus back while loading — mechanism

State 2026-11-09 (agent claude-cloud-ada0). focus.sh (sandbox paths): start
Photoshop, after 3 s activate xlogo, log the X focus every 0.5 s.

| WM | result |
|---|---|
| Metacity | focus stays on xlogo for 15 s |
| Muffin (owner's Cinnamon) | after ~17 s the focus goes back to Photoshop (reproduced) |

Trace (+timestamp,+x11drv,+event, Muffin):
- xlogo takes the focus: `X11DRV_FocusOut window 0x1006c ... foreground 0x1006c`
  — Wine keeps Photoshop as its foreground window.
- Later Photoshop changes its active window internally (palettes appear, its
  splash view is turned into a top-level dialog); each change of the Win32
  foreground goes through X11DRV_ActivateWindow -> set_net_active_window ->
  `_NET_ACTIVE_WINDOW` request; Muffin honours it (WM_TAKE_FOCUS), the user is
  pulled back. Metacity apparently ignores these requests.
- Wine 11.0 dlls/winex11.drv/event.c focus_out(): the foreground is reset to the
  desktop only `if (!is_net_supported(_NET_ACTIVE_WINDOW) && !is_current_process_focused())`.
  With an EWMH WM (Muffin, Metacity, mutter, KWin) that never happens, so a
  Wine app that lost the focus to another X client still counts as foreground,
  and any activation inside it is forwarded to the WM. On Windows the foreground
  lock would keep a background process from taking the foreground back.
Tried and rejected: an IAT hook refusing SetForegroundWindow once the process
lost the foreground: 0 refusals (GetForegroundWindow still returns Photoshop's
window, and the activations do not all come from SetForegroundWindow).
Fix options:
1. Wine (winex11): when _NET_ACTIVE_WINDOW on the root changes to a window of
   another client, set the foreground to the desktop (as the non-EWMH path
   does); or do not forward activation requests while the process is not the
   X-focused one. Upstream-worthy (words only). Delivery for Photoshop needs a
   private runtime for Photoshop (today only FastStone has one).
2. PE heuristic in the proxy: Wine sends WM_CANCELMODE to the foreground window
   on FocusOut (focus_out); treat that as "user switched away" and swallow
   activations until the user clicks a Photoshop window again. Fragile.

## Owner decision and root detail (2026-11-09 09:30)

Owner: fix in Wine + deliver through a private runtime.
Root detail: dlls/winex11.drv/window.c set_net_active_window() sends the
`_NET_ACTIVE_WINDOW` client message with source indication 2 ("pager") and
timestamp 0. EWMH: WMs obey pager requests unconditionally, bypassing their
focus-stealing prevention. An application request (source 1) with the time of
the last user input lets the WM refuse background activations while still
granting activations that follow user input in the app. Next: patch, rebuild
winex11.so, test under Muffin with focus.sh.

## Fix: patches/dllmgr-43.patch (verified 2026-11-09)

winex11: a process-wide "last user time" (user input in any of its windows,
or the WM making one of its windows active) is sent with
`_NET_ACTIVE_WINDOW` as an application request (source 1); pager requests
(source 2, timestamp 0) only before any such time exists. Applies on clean
wine-11.0 and together with winehq-60721.patch; built into the private
runtime by tests/wine/app-isolation-build.sh.

Stand (Muffin, Photoshop CS2 on a copy of runtime v3 with the rebuilt
x86_64-unix/winex11.so, new WoW64; scripts focus-rt.sh / focus2.sh):
- runtime v3 winex11 (control): focus back to Photoshop after ~18 s.
- patched: focus stays on xlogo for all 30 s, 2/2; also for 70+ s.
- no switching away: Photoshop gets the focus at startup as before.
- click on the loaded Photoshop window: Photoshop gets the focus back.
  (A click while Photoshop is still loading does nothing with or without the
  patch: its main thread does not process X events then, so it cannot answer
  WM_TAKE_FOCUS.)
Delivery for Photoshop: needs a Photoshop profile in the private runtime
(private-app.py is FastStone-only today). WineHQ: words-only report to write.

## Part 1 of #43: splash stays when the main window is minimized (findings)

mini.sh: minimize the main window 3 s into startup, list visible windows.
- Metacity: main window goes Iconic (WM_STATE 3), the splash stays visible.
  Its X properties are right: WM_TRANSIENT_FOR = main window,
  _NET_WM_WINDOW_TYPE_DIALOG, WM_HINTS input False; the WM itself added
  _NET_WM_STATE_SKIP_PAGER, SKIP_TASKBAR, STICKY. So the WM does not hide this
  transient with its minimized parent.
- Muffin on the stand did not minimize the main window at all (xdotool
  windowminimize; no panel?); the owner sees the same as Metacity.
- Win32 side: owned popups are hidden by ShowWindow(SW_MINIMIZE) of the owner,
  which needs Photoshop's main thread; during loading it neither pumps
  messages nor processes X events, so Wine cannot react in that thread.
  On Windows a non-pumping app does not minimize normally either (ghosting),
  so parity is unclear.
Possible fixes (not started): ask the WM to iconify the X transients of a
window that the WM iconified, from winex11 on any thread that sees the
WM_STATE change (needs a thread that processes events while the app is
busy); or find why the WM keeps a STICKY transient. Parked; owner informed.

## Part 1 under Muffin and the "heartbeat" idea (2026-11-09)

mini-muffin.sh (Muffin stand): minimize 4 s into loading -> main WM_STATE
Iconic, splash stays on screen (reproduced on the owner's WM).
Idea tried: call GetQueueStatus(QS_ALLINPUT) from the splash's own ReleaseDC
calls so Wine reads the X events (WM iconify -> SC_MINIMIZE -> owned popups
hidden). Result: no effect, because after the splash is shaped Photoshop
makes no more ReleaseDC calls through the hooked imports (trace: 0 calls), so
the heartbeat never runs. Code parked in wip-heartbeat.diff. Other heartbeat
sources while loading: the DLL load notification of each plug-in (runs under
the loader lock: risky), text drawing calls on a cached DC.

## Part 1 solved: the splash is an override-redirect window (2026-11-09)

Differential diagnosis under Muffin (mini3/mini-adopt, retransient.py):
- symptom: main window Iconic, splash stays and covers other apps;
- Muffin hides windows whose transient ancestor is minimized
  (meta_window_showing_on_its_workspace, ancestor_is_minimized), so a managed
  transient would be hidden; rewriting WM_TRANSIENT_FOR did not help;
- the splash has no WM_STATE and `Override Redirect State: yes`: Wine maps a
  caption-less popup shown with SWP_NOACTIVATE as unmanaged
  (winex11 is_window_managed), so no WM can hide, restore or restack it, and
  Photoshop's busy thread never runs ShowOwnedPopups. Not a Mint bug.
Fix (prefill proxy, version build): when the shaped splash and its owner are
both visible, add WS_SYSMENU (no visible effect without a caption; makes
winex11 manage the popup) + SWP_FRAMECHANGED. The splash becomes a managed
transient dialog: minimize main -> splash Iconic too, restore -> both back
(minimize-restore-adopt.png); another app activated over it now covers the
splash (over-ctl-vs-adopt.png: left stock, right adopted); full UI after
loading normal; focus not taken. Opt-out: DLLMGR43_NO_ADOPT=1.

## Adoption under the private runtime: rendering broken, disabled there (2026-11-09)

rtcheck.sh (PS-3 installed, plain `wine Photoshop.exe` -> trampoline ->
runtime, Muffin). With the splash managed, minimize/restore and stacking are
right, but the splash is drawn wrong: grey prefill pixels mixed with
Photoshop's paint (runtime-adopt-glitch.png). Same for both variants:
- late adoption (remap when owner visible, in main);
- early adoption (WS_SYSMENU before the first map, wip-adopt-early.diff;
  found: the main window is already visible when the splash is shown, the
  palette shown before it has WS_EX_TOOLWINDOW, the splash ex-style 0x101).
Unmanaged splash under the runtime renders cleanly. So adoption is skipped
when DLLMGR_TARGET_EXE is set (runtime); under stock Wine it stays on
(verified clean there). Next: find why a managed splash + prefill/shaping
renders wrong only with the runtime's winex11/win32u (60721 surface code vs
the WM's reparenting/configure order); first bisect: runtime + adoption with
DLLMGR27_NO_SHAPE=1, then without the prefill capture.

## Runtime + managed splash: bisect (2026-11-09, Muffin)

Build: wip-adopt-early-represent.diff (against 13956cd^: early adoption by
style, DLLMGR27_NO_PREFILL knob, helper thread re-presenting the splash).
rtcheck.sh frames at +1 s, +2 s, after restore; then minimize; then xlogo:

1. Adoption on, no helper thread (runtime-bisect-full-noshape-noprefill.png,
   rows: full / DLLMGR27_NO_SHAPE / + DLLMGR27_NO_PREFILL): with the prefill
   off the managed splash shows NOTHING for the first seconds (grey = main
   window), so the mixed pixels are not the prefill's fault: Photoshop paints
   before the WM has mapped the managed window, X drops that drawing, and the
   busy thread never processes the Expose that would re-present it.
2. Helper thread (copies the splash onto itself every 100 ms for 4 s from
   another thread; marks the surface drawn and flushes it): content shown from
   the first frame, minimize/restore and stacking right.
3. Left: the margin around the card is white
   (runtime-adopt-represent-white-margin.png) although the X window has the
   bounding shape (XShapeGetRectangles: 2662 rects, bbox inside the window).
   Not a Muffin bug: shapetest.py (undecorated window, shape set before or
   after map) is honoured by Muffin. Window is undecorated (_MOTIF_WM_HINTS
   decorations 0), DIALOG, transient, depth 24, parent = root.
   Open: why the shape is ignored on screen for this window only with the
   runtime (stock Wine + late adoption was clean).
4. Same build on stock Wine 11.0 (DLLMGR27_NO_TRAMPOLINE=1): clean shaped
   card, no white margin (stock-adopt-represent-clean.png). So the white margin
   comes from the runtime.
5. Runtime with 60721 part 2 reverted (background pixel 0 instead of None,
   rtdirect.sh, runtime-bg-none-bisect.png left = runtime, right = reverted):
   less white, but white patches remain. Next half: 60721 part 1
   (exposed/painted bounds in win32u) on its own.

## Shipped as the interim fix (owner, 2026-11-09: minimizing matters more than the transparent margin)

wip-adopt-early-represent.diff is now in patches/dllmgr-27/prefill.c (no
runtime gate): runtime-v5-candidate.png (frames +1/+2 s, restore,
minimized, xlogo over the splash). Stock Wine: clean shaped card. Runtime:
white margin; digging continues (next: 60721 part 1 alone).

## Owner rule (2026-11-09): a white margin is acceptable, stale/garbage pixels never

Why 19cf8bf can show garbage: shaping compares the window with the
snapshot taken at show time. Dumps (DLLMGR43_DUMP, 2026-11-09): the
snapshot was mostly WHITE (main window not painted yet), so the white card
equals the "background" and the region cut the card (painted=24..57 % instead
of ~83 %). Pixel diffing against a snapshot is unsafe by design.

Interim (commit after 19cf8bf): the adopted splash gets no snapshot and no
shape; re-present thread kept. 3/3 runtime runs + stock: card, white margin,
no stale pixels, minimize/restore and stacking right (interim-safe-3runs.png).

Final direction found: Photoshop draws the card with AlphaBlend (msimg32,
delay import of Photoshop.exe, AC_SRC_ALPHA) from a premultiplied 32-bit
671x418 bitmap with the real alpha: rounded corners, soft shadow, feather,
transparent margin (alphablend-card-and-alpha.png). Tried: per-pixel-alpha
layered window (UpdateLayeredWindow) from that alpha + the window's opaque
pixels (wip-layered-alphablend.diff): the alpha is right, but Wine shows the
layered splash black and later garbage (layered-garbage.png), on the runtime
and on stock Wine; reading the window back after the first ULW gives black.
Next: find why Wine's ULW on this DPI-virtualized (unaware, 192 DPI) managed
window loses the colours (minimal ULW test program first), or use the alpha
as an exact shape mask (alpha > 0) without snapshot diffing.

## Done: shape from the card's own alpha (2026-11-09)

The AlphaBlend hook (Photoshop.exe delay import of msimg32) shapes the
splash from the card bitmap's alpha (>= 128, DLLMGR36_ALPHA_MIN), in
Photoshop's thread, also when the card is drawn before the splash is shown.
No snapshot, no pixel diffing, nothing on screen is ever read: 3/3 runtime
runs + stock Wine: card with crisp rounded edges and the feather, no margin,
no stale pixels, minimize/restore and stacking right (alpha-shape-3runs.png,
alpha-shape-edges.png). Not reached yet: the soft shadow (cut below alpha
128; true per-pixel alpha needs a working layered window, see above).

## #45 any-Wine workaround in test (2026-11-09)

wip-menu-fade.diff: new menu windows (#32768) shown fully transparent (WS_EX_LAYERED + alpha 0) and made opaque after their first WM_PAINT (fallback 250 ms). Stand burst on stock Wine with/without (DLLMGR45_NO_FADE) running.
Result: stock Wine, Muffin, menu burst: fade 0/40 bad frames (12 menus
revealed after their first paint, 0 by timeout) vs 7/40 without
(DLLMGR45_NO_FADE=1); menus render normally (menu-fade-frames.png). Shipped.

## About box (owner, 2026-11-09 14:49: Help > About Photoshop had a frame)

Same card in a new window (another PSFloatC popup); the alpha shape was
applied only once per process. Now every splash-like window gets its card
shape once (while it has no region): about-shaped.png (stock Wine).

## #36 halo fixed (2026-11-09)

The region was computed for the card at ClientToScreen(dc window)+(dx,dy),
but Photoshop draws through a DC with its own origin: the card really sits
5,5 logical px lower-right (GetDCOrgEx + LPtoDP). The region was shifted
up-left, so white window background showed above the top edge and around
the feather. Now LPtoDP + GetDCOrgEx: splash-halo-before-after.png (left
before, right after; stand, 192 DPI). DLLMGR36_DUMP=1 writes the card as
raw BGRA to C:\dllmgr36-card-WxH.bgra for inspection.
