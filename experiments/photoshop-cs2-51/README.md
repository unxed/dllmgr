# #51 plain launch stays on the system Wine

owner-far2l-trace.log (owner, 2026-11-09 15:58, far2l, `wine Photoshop.exe`, fixme/font/AlphaBlend/ReleaseDC filtered out): the trampoline starts the launcher, then nothing at all from it (no Python error, no private-runtime trace line although DLLMGR27_DEBUG is inherited), fallback after 15 s. The stand hands over in under 1.5 s (plain, setsid, pty). Next: launch log (c97e359) + `ps` on the owner machine.

## 2026-11-09 16:03 owner result, 16:10 stand

- Owner (c62e551, far2l GUI, plain `wine Photoshop.exe`): launch log
  `started (parent pid 1)` → `starting the private runtime` → `private
  runtime ended (exit code 1) after 0.3 s`; .dllmgr/trampoline-run.log
  empty. So the private `wine` loader exits 1 in 0.3 s without a word, only
  when started by the trampoline (a manual `dllmgr run` works).
- Stand: far2l 2.6.0 (TTY backend, in tmux) on Ubuntu 24.04, same command
  line: hands over fine (private Photoshop with the runtime's winex11.so,
  stderr captured). Not reproduced yet. The owner runs far2l's GUI backend
  (window title "[cd@/home/unxed]"); next: reproduce with the GUI backend
  and the owner's environment, not more owner runs (owner, 16:03).
- Fixed on the way: the watched run held the prefix lock while Photoshop
  ran (`dllmgr status` blocked); `failed: 0` was a logged SystemExit.

## Plain launch stayed on system Wine (owner log, 2026-11-10)

Owner's .dllmgr/trampoline-run.log: all three attempts of the private
runtime ended at once; the traced one loads Photoshop.dll, PSViews.dll,
PSArt.dll and unloads them, and VERSION.dll (the proxy that signals the
waiting stock process) never loads.

Cause (stand, second.sh, relay trace): Photoshop CS2 is single-instance:
WinMain creates the mutex "PS3.0.5WIN" (and "goingDownForeverPS4.0"); a
second instance that finds it loads Photoshop.dll, unloads it, FindWindow
("Photoshop") and ExitProcess(1). The proxy VERSION.dll is delay-loaded by
Photoshop.exe; on the stand that happens before the mutex check (so the
private instance signals and the stock one exits in time), on the owner's
system it did not, so the private instance met the stock instance's mutex
and quit, three times.

Fix (prefill.c trampoline): before starting the launcher the stock process
closes its handles to these mutexes (found by NtQueryObject names); it
leaves when the private runtime signals or when the mutex exists again
(the private instance created it). Stand, e2e51.sh, signal suppressed
(DLLMGR51_NO_SIGNAL=1, as on the owner's system): without the fix
(DLLMGR51_NO_MUTEX=1) "no signal ... staying on stock Wine", pid on the
system Wine; with it "private runtime holds the single-instance mutex,
exiting", pid on the private runtime. Normal case: "took over" as before.
