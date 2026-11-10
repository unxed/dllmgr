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
