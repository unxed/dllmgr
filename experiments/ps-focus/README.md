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
