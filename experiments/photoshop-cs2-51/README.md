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
