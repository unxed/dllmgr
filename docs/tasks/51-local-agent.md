# #51 on the owner's machine: task for a local agent

Read AGENTS.md first (rules, multi-agent protocol, docs/console-agent.md).
Claim this task in docs/multi-agent-protocol.md before starting.

## Problem

Photoshop CS2, dllmgr recipe with runtime v11 installed. A plain start
(`wine Photoshop.exe` from the Photoshop folder, system Wine 11.0 at
/opt/wine-stable) should hand over to the private runtime through the launch
trampoline (proxy version.dll -> `dllmgr run` -> private Wine). On the owner's
machine it does not:

    dllmgr status photoshop-cs2
      Running: pid ... on the system Wine
      Last launches: ... private runtime (inherited environment) ended (exit code 0) after 0.4 s

The private Photoshop ends after 0.4 s with exit code 0; the stock one keeps
running (small cursor etc.). In the cloud stand it works, including
simulations of a late proxy load (experiments/photoshop-cs2-51/README.md:
single-instance mutex "PS3.0.5WIN", DLLMGR51_NO_SIGNAL, DLLMGR51_LATE).
Known difference: the owner's copy is registered (splash shows the user
name), the stand runs the trial with an activation dialog; the owner starts
from far2l.

## Rules for this task

- Do not change ~/.wine. Work on a copy: `cp -a ~/.wine /tmp/dllmgr51-prefix`,
  then `dllmgr fix photoshop-cs2 --prefix /tmp/dllmgr51-prefix` and use
  WINEPREFIX=/tmp/dllmgr51-prefix for every run. Remove the copy at the end.
- Do not open windows on the owner's desktop: run under Xvfb
  (`xvfb-run -a -s "-screen 0 1920x1080x24"` or `Xvfb :77 &` + DISPLAY=:77).
  If Xvfb is missing, stop and ask the owner (sudo apt install xvfb).
- If the problem does not show up on the copy, stop and report that (it then
  depends on something in ~/.wine itself); ask before touching ~/.wine.
- Fail fast: one experiment at a time, record each result.
- Commit everything (scripts, logs trimmed to the relevant part, notes) to
  experiments/photoshop-cs2-51/owner-machine/ and push to main; commit
  messages in English. Logs may hold environment variable values: keep names
  only, never values of tokens or keys.

## Steps

1. Reproduce: plain start on the copy; `dllmgr status photoshop-cs2 --prefix
   /tmp/dllmgr51-prefix` must show "on the system Wine" and the 0.4 s exit.
   Save `.dllmgr/launch.log` and `.dllmgr/trampoline-run.log` of the copy.
2. Stock side: repeat with `DLLMGR27_DEBUG=1` in the environment of the plain
   start; its stderr shows "trampoline armed", "closed single-instance
   mutex", "started ...", and how the wait ended. Note the time between start
   and "trampoline armed" and whether Photoshop windows existed by then
   (`wmctrl -l` / `xdotool search --class Photoshop` in a loop).
3. Private side: start the stock one with `DLLMGR27_NO_TRAMPOLINE=1`, wait
   until its main window exists, then run
   `WINEDEBUG=+loaddll,+process dllmgr run photoshop-cs2 --prefix /tmp/dllmgr51-prefix`
   and save its stderr: does it end after ~0.4 s with code 0, which DLLs load
   before the exit, is VERSION.dll (the proxy) among them and when.
4. If 3 does not explain it: the same with
   `WINEDEBUG=+relay` and a relay filter for the single-instance path, set
   only in the copy's registry (HKCU\Software\Wine\Debug, RelayInclude =
   "kernel32.CreateMutexA;kernel32.CreateMutexW;kernel32.OpenMutexW;user32.FindWindowA;user32.FindWindowW;user32.SendMessageA;user32.SendMessageW;kernel32.ExitProcess;kernel32.GetModuleFileNameW;kernel32.LoadLibraryA").
5. Write experiments/photoshop-cs2-51/owner-machine/README.md: what was run,
   what each step showed, the cause if found (facts, not guesses), and what
   is still unknown. Commit, push, and report the commit to the owner.

Do not fix the trampoline in this task unless the cause is proven by step
2-4; if you do, the fix needs a test switch and a before/after run on the
copy, and goes to patches/dllmgr-27/prefill.c with docs.
