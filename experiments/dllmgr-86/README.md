# #86 dllmgr update / upgrade: stand check

`e2e-upgrade.sh` repeats the owner's flow on the headless stand with a copy
of a CS2 prefix and a temporary HOME: dllmgr 981e902 (runtime v22) fixes
Photoshop CS2, `dllmgr set` changes settings, `dllmgr update` installs the tip
of main, `dllmgr upgrade` plans and re-applies.

Result 2026-11-11 (tip 00f0a00, cc-rcnb-52ab):

- update: 132 files verified, `981e902 -> 00f0a00 (20 new commits)`,
  runtime `v22 (0c742a0d3190) -> v23 (e88694ab3821)`, modules unchanged.
- `upgrade --dry-run`: one app, `runtime v22 -> v23`,
  `dllmgr unknown (fixed by an older dllmgr) -> 00f0a00`; answer "n" changes
  nothing; `--yes` re-applies (runtime assembled, launcher and trampoline
  rewritten), a second `upgrade` says up to date.
- `dllmgr status`: runtime v23, trampoline ok, settings `text=gray
  contrast=1.5` kept.
- First run found a bug: a Photoshop.exe running in another prefix held the
  app back; fixed in 00f0a00 (process prefix from its WINEPREFIX/HOME).

Not run on the stand: FastStone (same `private-app.py install` path with
`--fix`; covered by unit tests).
