# PuTTY task cards (#20) — showcase bootstrap

Nothing is analysed yet; issue #20 lists Wine 57513 (owner: critical) and
https://bugs.winehq.org/buglist.cgi?quicksearch=putty . The owner recalls
57513 as his own report about **Russian keyboard input** in PuTTY; verify
against the bug text before planning the reproducer.

## PT-1 audit (executing agent)

1. Read Wine 57513 fully (all comments, attachments' descriptions); then the
   quicksearch list, keeping only real PuTTY bugs (drop unrelated hits).
2. docs/putty.md: one table row per bug: number, title, Wine version last
   confirmed, symptom in one line, reproducible offline? (yes/no + why).
3. Pin the official PuTTY release (64-bit and 32-bit putty.exe from
   https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html; record
   version + SHA256 like tests/wine/faststone85.sh).
Done when: docs/putty.md table + pinned binaries.
Stop and ask if: a bug needs a real SSH server/network to reproduce (propose
a local sshd in CI and wait for approval).

## PT-2 reproduce 57513 on the stand

Headless stand (STAND_WM=metacity), fresh prefix, PuTTY pinned build. Build a
scripted reproduction that passes on windows-latest and fails on Wine,
judged by X pixels or text, not by eye. Then stop and hand the mechanism
analysis to Opus with the reproducer, logs (+relevant WINEDEBUG channel) and
screenshots.
