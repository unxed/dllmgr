# FastStone 8.5 shortcuts with the Russian keyboard layout (no issue yet)

Status 2026-11-11 (agent cc-rcnb-52ab): **paused by the owner, partial.**

Question: do FastStone's keyboard shortcuts work when the Russian XKB layout
is active, under the private runtime v21 (package sha256 fe29faf8d280, has the
#49 layout tracking in x86_64-unix/winex11.so) and recipe faststone-v4?
Method of #49 (experiments/photoshop-cs2-49): `setxkbmap ru,us` with the
Russian group locked as group 0 before start; owner's locale ru_RU.UTF-8.

Stand: cc-rcnb-52ab, invisible Xvfb :133 3072x1728 at 192 DPI with Muffin,
prefix fs40/prefix, env exactly as `dllmgr run faststone` (env.sh).

Files:
- fsru.sh NAME LAYOUT GROUP: one run inside a stand session
  (`SD=:133 SDIR=$B/sub4 $B/run.sh sh fsru.sh ru-us ru,us 0`). Starts
  FastStone on a folder with three test JPEGs (mkimg.sh), presses each key
  as a physical keycode, checks the effect by window titles, files on disk
  or screen crops; writes results.tsv. Dialogs are closed with wmctrl -c.
  LATE=1 locks the group only after start (switch while running; not run yet).
- xkey.py: XTest key presser that never changes the XKB group (unlike
  xdotool), `-g N` locks a group first.
- env.sh, mkimg.sh: launch env and test images.
- results-us-ru.tsv: full run, us,ru with US active.

## Results

| Context | Key | us,ru (US active) | ru,us (Russian active) |
|---|---|---|---|
| browser | Ctrl+A (select all; status bar 1 -> 3) | works | works (manual) |
| browser | Ctrl+C, Ctrl+V (files pasted into parent) | works | works (run 1) |
| browser | F2 (rename dialog) | works | works (run 1) |
| rename field | keys g h b d t n + Enter | file `ghbdtn.jpg` | file `привет.jpg` (Cyrillic OK) |
| browser | Ctrl+R (resize dialog) | works | works (run 1) |
| browser | X (crop board) | works | works (manual) |
| browser | Enter (fullscreen viewer) | works | not checked yet |
| viewer | PgDn / PgUp (title changes) | works | not checked yet |
| viewer | KP+, KP-, `+`, `-` (zoom %) | works | not checked yet |
| viewer | S slideshow, Ctrl+R resize, I properties, X crop, D draw, E external program, R/L rotate | works | not checked yet |
| viewer | Esc (back to browser) | works | not checked yet |

So far nothing fails in the Russian layout. The two ru,us script runs that
reported failures were stand failures, not FastStone: Muffin died (white
screen; once right after a `wmctrl -c` of the resize dialog with
`meta_window_set_stack_position_no_sync` assertion in wm.log), after which
every later check failed. Re-done by hand on a fresh session, Ctrl+A and X
work under ru,us.

Notes:
- In the browser Ctrl+C/Ctrl+V copy files (CF_HDROP), not the image; the
  toolbar "up" button follows the folder tree, not the current path, so
  fsru.sh uses back/forward to reach the parent folder.
- In the viewer I shows a docked panel (no window); E with no external
  program shows a notice and then opens Settings; R/L make FastStone ask to
  save on leaving (fsru.sh answers "No").
- The first fullscreen use shows a hint dialog every start, because the
  stand kills wineserver instead of exiting FastStone (settings not saved).

## Next

1. Make the run robust against Muffin crashes: close dialogs with the
   dialog's own title-bar button or with Esc instead of `wmctrl -c`, or rerun
   on crash (check `xprop -root _NET_SUPPORTING_WM_CHECK` + muffin pid).
2. Full ru,us run (`fsru.sh ru-us ru,us 0`), then `LATE=1 fsru.sh us-ru-late
   us,ru 1` (switch to Russian while FastStone runs).
3. For any real failure: rerun with WDBG=+key,+keyboard and say whether the
   VK or the character is wrong.
4. Restore FastStone db files afterwards (the run creates FSIV2.db,
   FSIV2.db-wal, TBSettings.db in the FSViewer85 folder; FSSettings.db is not
   created because FastStone never exits cleanly on the stand).
