# Agent task: stationary mouse release on the FastStone path button (#21)

Continue https://github.com/unxed/dllmgr/issues/21; read its body and **all**
comments first, then docs/handoff.md, docs/development.md and docs/app-isolation.md
from current main. Work in a separate clone/worktree: another agent is actively
investigating the first-open flash (#27), and other worktrees contain preserved
unfinished drafts. Do not reset, stage or commit those files.

## Owner observation

FastStone8.5 x86, Wine11.0, win64 prefix,192DPI. The private faststone-v3 path
button looks better after our fix, but the owner thinks that after releasing the
mouse its pressed appearance remains until the pointer moves. This is not yet
an independently confirmed mismatch with Windows. Do not assume the shipped
pressed-while-dropdown-open correction is wrong.

## Small, bounded scope

1. Extend the existing tests/wine/path-observer.c and pixel/state checks to
   capture mouse-down, stationary release, stationary dwell, movement within
   the button, movement outside, then dropdown dismissal. Record dropped state,
   capture, hover, popup visibility and focused pixel crops. Compare transitions
   within each environment, allowing for different theme palettes/fonts.
2. Run the exact same sequence on real Windows in GitHub CI and stock/patched
   Wine96/192DPI. Existing .github/workflows/path-dropdown.yml, the patch
   patches/dllmgr-21.patch and experiments/path-dropdown/ are the starting point.
3. If Wine differs, add a regression which fails before and passes after the
   smallest correct paint/state fix. Preserve the existing fix and other five
   fixes in the composed recipe. If Windows behaves the same, record evidence
   and explain it; do not manufacture a difference to justify a change.
4. Publish useful increments immediately as small commits to main, authored
   unxed <ivan.sorokin.tech@gmail.com>. Prefer a separate research branch for
   hosted builds, then integrate the tested increment. New binaries must have
   matching source, hashes and exact-SHA terminal CI evidence. Do not replace
   published immutable release assets with different bytes.
5. Deliver through the existing app-private manager; preserve fonts, AVIF,
   settings, unrelated applications and shared DLL hashes. Do not interrupt the
   owner's running application. Update #21/#8 and handoff with exact results,
   failed attempts and remaining acceptance.

## Non-negotiable testing boundary

No test windows, keyboard/mouse input or focus changes on the active desktop.
Use hosted Windows CI or your own invisible X server and disposable Wine prefix.
Never reuse another agent's display/server/prefix; never kill a shared wineserver.
Never patch system Wine or product-prefix system32/syswow64/winsxs. Old unsafe
research installation is permitted only in a disposable test prefix.

The old severe intermittent path-row corruption is a separate unresolved item
in #21. Do not claim this follow-up fixes it. Keep #27, font polishing, performance,
Photoshop and the planned TUI out of this bounded task. Wine feedback, if needed,
is words only, with no code or code links, following the owner's posting policy.
