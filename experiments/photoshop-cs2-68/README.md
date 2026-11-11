# #68: "Commit the type layer edits before closing?" under the document

Reproduced on the stand (2026-11-10): Type tool, click into the document,
type, Ctrl+W (type-close.sh MODE=type; RT=... runs a local runtime,
KEEP=1 leaves Photoshop running).

Mechanism: Photoshop's document windows are owned popups (X: transient
dialogs of the main frame). The confirmation is mapped with activation,
but Wine maps an activated window *without* _NET_WM_USER_TIME. Muffin's
focus-stealing prevention then sees a new window with no user time that is
not a transient of the focused window (the document), refuses the focus,
marks it _NET_WM_STATE_DEMANDS_ATTENTION and stacks it *below* the focused
document. The later _NET_ACTIVE_WINDOW request is skipped while the window
is still withdrawn (log: "skipping _NET_ACTIVE_WINDOW for withdrawn window").

Fix (patches/dllmgr-68.patch, winex11 window_set_user_time): a window
mapped for activation gets _NET_WM_USER_TIME = the time of the user's last
input in this process (the Ctrl+W), when it has no user time yet. Muffin
then lets it take focus and raises it (before-under-document.png ->
after-on-top.png). A process the user left keeps an old time, so the #43
focus-stealing protection still holds.

## 2026-11-11: recheck with runtime v21 (agent cc-rcnb-52ab, owner's laptop stand)

v21 (`c6d2b6d2...`, contains dllmgr-68.patch), Muffin, Xvfb :132 3072x1728 at
192 DPI. Scripts: v21-close.sh (one scenario; Type tool, click into t46.png,
type "abc", close), v21-all.sh (one stand session per scenario). Each run on
a fresh `cp -a` of prefix-clean (deleted after): prefix-auto's trial is over
and stops at "Activation Required" (not bypassed). prefix-clean brings up the
F26 "program error" box at startup; the script dismisses it and the Updater
Preferences. Crops (X pixels, 50 %), `*-props.txt` (wmctrl, stacking,
_NET_WM_USER_TIME, _NET_WM_STATE), verdicts.txt, trace-excerpts.txt: v21/.

| close by | dialog above document | focused | verdict |
|----------|----------------------|---------|---------|
| Ctrl+W | - | - | not testable here: no dialog, the document stays (see below) |
| File > Close (same command as Ctrl+W) | yes | yes | works |
| Alt+F4 | NO, below the document, DEMANDS_ATTENTION | no | **#68 again** |
| close button of the document frame | NO, below the document, DEMANDS_ATTENTION | no | **#68 again** |
| xclock, back, File > Close | yes (also above xclock) | yes | works |
| xclock, back, click into the text, File > Close | yes | yes | works |
| xclock, back, Alt+F4 (closes the main frame) | yes | NO, focus stays on the main frame | half: visible, keyboard does not go to it |
| xclock, back, close button | yes | yes | works (timing-dependent, see cause) |

Ctrl+W: on this stand every Ctrl shortcut of Photoshop is dead after the
F26 startup box (Ctrl+W, Ctrl+O; also outside the type edit); Alt menus,
plain typing and Wine Notepad's Ctrl+O in the same session work. That is
F26 (stand), not #68. The menu click exercises the same path the patch
covers: the user's last input goes to Photoshop itself.

Cause of the failures (WINEDEBUG=+timestamp,+event,+x11drv with
MUFFIN_VERBOSE=1, trace-excerpts.txt): dllmgr-68 gives the dialog the time of
the process's last own input. With Alt+F4 that is the Alt KeyPress
(330843490); F4 is Muffin's keybinding and never reaches Wine, but it sets
Muffin's last_user_time (330843497). Muffin: "window 0x1200064 focus
prevented by other activity; 330843490 < 330843497" -> "does not focus on
map, and does not place on top on map" -> stacked under the document. With
the frame's close button the click is Muffin's too (dialog 330953961 = the
last typed key, Muffin 330957662 = the button release). On a real keyboard
Alt is pressed long before F4, so Alt+F4 fails every time, not by a few ms.
After switching back from xclock, Alt+F4 closes the main frame; the dialog is
a transient of the focused frame, so Muffin raises it but still refuses focus
for the same reason (331085097 < 331085104).

Wine gets the WM's timestamp with the request: the WM_DELETE_WINDOW client
message carries it (data.l[1]), but handle_wm_protocols (event.c) does not
pass it to note_process_user_time. Proposed fix (not done here): note the
WM_DELETE_WINDOW event time as user time of the process, as
net_active_window_notify already does for _NET_ACTIVE_WINDOW; then the
dialog's time equals Muffin's last_user_time and is no longer "before" it.
Retest these four failing rows after that.
