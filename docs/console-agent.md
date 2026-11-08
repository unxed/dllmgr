# Working from a console agent on the owner's machine

For Claude Code (or any CLI agent) started in a checkout of this repo on the
owner's Linux Mint/Cinnamon laptop. Differences from the cloud sandbox
(docs/sandbox-agent-hints.md) are what matters here.

## What you have and do not have

- The owner's `gh` login: you CAN create releases, comments, PRs. Still
  follow AGENTS.md (no WineHQ posts without approval).
- Wine 11.0 in /opt/wine-stable (WineHQ build, old WoW64: 32-bit apps load
  `lib/wine/i386-unix/*.so`; dllmgr's private runtime uses new WoW64 and
  `x86_64-unix` only).
- The owner's real desktop (Cinnamon = **Muffin, a compositing WM**) on
  DISPLAY :0. Do **not** use it: no windows, no xdotool on :0, no
  `~/.wine`. Everything runs on a private Xvfb display.
- No root by default. `scripts/sandbox-stand.sh install` assumes root and
  apt (and writes Gecko/Mono MSIs into /opt/wine-stable/share/wine): do not
  run it here. Check tools instead and ask the owner to install missing ones:
  `command -v Xvfb metacity xdotool convert import xprop xdpyinfo
  i686-w64-mingw32-gcc x86_64-w64-mingw32-gcc`.
  Without the Gecko/Mono MSIs, a fresh `wineboot -i` shows an install prompt
  that hangs headless: create prefixes with
  `WINEDLLOVERRIDES='mscoree,mshtml='` (Photoshop/FastStone do not need them).
- The owner's own long-lived stand lives in experiments/photoshop-handoff/
  (headless.py, prefix110, unpacked Xvfb). Preserve it; never delete or
  reuse prefix110 for experiments (see docs/photoshop-handoff.md).

## Running the stand without root

All paths are variables; never rely on /home/claude defaults:

    export STAND_DIR=$HOME/.cache/dllmgr-agent/$AGENT_ID      # see protocol doc
    export STAND_DISPLAY=:$AGENT_DISPLAY                       # unique per agent
    export WINEPREFIX=$STAND_DIR/prefix
    export STAND_WM=metacity       # pixel checks need a non-compositing WM
    sh scripts/sandbox-stand.sh session sh scripts/sandbox-stand.sh prefix
    sh scripts/sandbox-stand.sh session <your experiment script>

`session` starts its own Xvfb (-noreset, 3072x1728, 192 DPI) and WM, runs
the command and tears everything down; its exit code is the command's.
Judge pixels from the X server (tests/wine/xsample.c, `import`), not from
Wine's GetPixel (findings F18). Muffin results are not trustworthy for
flicker sampling (F17).

## CS2 and FastStone inputs

- CS2 trial installer: official https URL or the Wayback copy, SHA256 in
  docs/sandbox-stand.md; in CI only the Wayback copy. Unattended install:
  `scripts/sandbox-install-cs2.sh` (inside a session, fresh 192 DPI prefix).
- FastStone 8.5: tests/wine/faststone85.sh (URL + SHA256).
- Reproduce the owner's symptoms with dllmgr exactly as they launch it:
  `dllmgr run faststone -- FILE` uses the private runtime; plain `wine`
  launches do not (docs/tasks/27-every-launch-path.md).
- `dllmgr diag` prints a read-only report (WM, compositor, loaded
  win32u/winex11 modules of a running FSViewer.exe); ask the owner for it
  instead of guessing their setup.

## Building

- PE helpers (tests, proxies): mingw, e.g. `sh patches/dllmgr-27/build.sh`.
- Wine pieces: docs/sandbox-stand.md "Building Wine 11.0 pieces" (needs
  -dev packages; ask the owner). Never install builds into /opt or system
  Wine; drop .so files into a copy of /opt/wine-stable in your STAND_DIR.
- Heavy builds belong in CI (app-isolation.yml); dispatch it rather than
  burning the owner's machine.
