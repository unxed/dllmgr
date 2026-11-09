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
