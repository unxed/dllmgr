# Sandbox stand (Claude cloud session)

How to rebuild the headless Photoshop CS2 stand from zero in a fresh,
disposable sandbox, so a reset session does not have to rediscover it.
Complements docs/photoshop-handoff.md (owner's laptop stand) and issue #31.

## Sandbox facts (2026-11-08)

- Ubuntu 24.04 noble, x86_64, root, 2 CPUs, 7.8 GB RAM, ~31 GB free disk.
- Ephemeral: the prefix, installer and packages are lost on reset. Rebuild with
  `scripts/sandbox-stand.sh`; nothing here is a substitute for the owner's
  `prefix110` results.
- Network goes through an egress proxy. The owner must allow domains on
  claude.ai (Settings > Capabilities). Was needed: `dl.winehq.org`.
- `gh` works only through REST (`gh api ...`), GraphQL is blocked; issue
  comments of unattached repos are not readable that way. WebFetch of the issue
  page works but is rate-limited (retry once, one page at a time).
- The session can clone this repo but cannot push: deliver commits as
  `git format-patch` to the owner.

## Rebuild

    sh scripts/sandbox-stand.sh            # install + up + prefix
    sh scripts/sandbox-stand.sh up         # after a reset of X processes only

Result: Wine 11.0 (`/opt/wine-stable`, WineHQ `11.0.0.0~noble-1`, pinned),
Xvfb `:92` 3072x1728x24 at 192 DPI, Muffin as WM (no compositing), clean
prefix `/home/claude/work/photoshop-cs2/prefix110`. Ubuntu's own wine is 9.0
and must not be used for reports.

## Pitfalls found

- Muffin dies at startup with `Settings schema
  'org.cinnamon.settings-daemon.peripherals.touchscreen' is not installed`;
  fix: `cinnamon-settings-daemon` (`--no-install-recommends`).
- `wineboot -i` hangs forever on the invisible Mono install prompt
  (`control.exe appwiz.cpl install_mono`); fix:
  `WINEDLLOVERRIDES='mscoree,mshtml='` at prefix creation. CS2 does not need
  Mono/Gecko. If a later bug turns out to depend on them, record that.
- dbus `Failed to set fd limit` and xkbcomp keysym warnings are harmless.
- `experiments/photoshop-handoff/headless.py` hardcodes the owner's unpacked
  Xvfb path and the repo-relative prefix; do not run it as-is here. The
  script above starts the same Xvfb+Muffin session without launching Photoshop.

## Installer: OPEN

Expected: official `Photoshop_CS2.exe`, 345,068,035 bytes,
SHA256 `919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea`
(EXE inside: `98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30`).
From the sandbox `web.archive.org` resets every connection (even with all
domains allowed) while `archive.org` answers; `download.adobe.com` gives 403.
The exact snapshot URL is not recorded in this repo yet. Record it here once
known, and always verify the SHA256 before running anything.
