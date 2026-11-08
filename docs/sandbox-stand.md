# Sandbox stand (Claude cloud session)

New session? Start with [sandbox-agent-hints.md](sandbox-agent-hints.md).

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
- Push works once the repo is attached with push access through the session's
  GitHub app (`add_repo` with `access: push`); that clone lives at
  `/home/claude/dllmgr`. The anonymous read-only clone cannot push.

## Working mode in this sandbox

Maximum autonomy (owner, 2026-11-08): push every finished small atomic change
straight to `main` from `/home/claude/dllmgr`, without waiting or batching,
per [development.md](development.md). Problems hit along the way go to
[sandbox-findings.md](sandbox-findings.md) and are fixed last, after the
already existing bugs.

## Rebuild

    sh scripts/sandbox-stand.sh install    # once per sandbox
    sh scripts/sandbox-stand.sh session sh scripts/sandbox-stand.sh prefix  # clean prefix, once
    sh scripts/sandbox-stand.sh session CMD...   # every experiment

Every experiment is one self-contained `session` run: it starts its own
Xvfb + Muffin, waits for a real WM, runs CMD (a script doing wine + xdotool
steps + `import -window root` screenshots), returns CMD's exit code and
tears down X, Muffin and wineserver. Only the prefix and logs persist.
Use a separate STAND_DISPLAY (e.g. `:93`) for throwaway checks. Smoke test
verified 2026-11-08: Wine Notepad gets a decorated window in ~2 s (first
wine start in a fresh prefix ~20 s). `up` is legacy and only good for a
quick look within one reply.

Result: Wine 11.0 (`/opt/wine-stable`, WineHQ `11.0.0.0~noble-1`, pinned),
Xvfb `:92` 3072x1728x24 at 192 DPI, Muffin as WM (it ALWAYS composites, being
mutter-based; `STAND_WM=metacity` gives Metacity `--compositor=none`, the
owner's #27 setup, needed for screen-DC pixel sampling), clean
prefix `/home/claude/work/photoshop-cs2/prefix110`. Ubuntu's own wine is 9.0
and must not be used for reports.

## Pitfalls found

- Muffin dies at startup with `Settings schema
  'org.cinnamon.settings-daemon.peripherals.touchscreen' is not installed`;
  fix: `cinnamon-settings-daemon` (`--no-install-recommends`).
- `wineboot -i` hangs forever on the invisible Mono download prompt
  (`control.exe appwiz.cpl install_mono`). Decision (2026-11-08): `install`
  puts the official Gecko 2.47.4 (x86, x86_64) and Mono 10.4.1 MSIs into
  `/opt/wine-stable/share/wine/{gecko,mono}`, so wineboot installs them
  silently, like stock Wine on a desktop where the prompt is accepted. Closer
  to the owner's prefix than disabling `mscoree,mshtml`. Prefix: ~1.8 GB.
- Processes detached with `setsid`/`&` (Xvfb, Muffin) are killed a few
  minutes after the assistant's reply ends, and a background shell task is
  capped at ~2 h. Hence no long-lived desktop: use `session` per experiment;
  run it as a background task if it outlasts one reply.
- The X socket file appears before Xvfb accepts clients; starting Muffin
  then fails with `Unable to open display`. `session` polls `xdpyinfo`.
- dbus `Failed to set fd limit` and xkbcomp keysym warnings are harmless.
- `experiments/photoshop-handoff/headless.py` hardcodes the owner's unpacked
  Xvfb path and the repo-relative prefix; do not run it as-is here. The
  script above starts the same Xvfb+Muffin session without launching Photoshop.

## CS2 trial install steps (sandbox, 2026-11-08)

Automated: `sandbox-stand.sh session sh scripts/sandbox-install-cs2.sh` on a
fresh 192 DPI prefix (verified end to end into `prefix-auto`, a few minutes).
The manual path it replays:

All inside one `session` on `:93` with the prefix at 192 DPI.

1. `wine Photoshop_CS2.exe` -> WinZip Self-Extractor (690x380 at 192 DPI),
   default folder `Photoshop TryOut` (relative to the cwd), Enter = Unzip,
   "404 file(s) unzipped successfully", OK, Close. It does not start setup.
2. `wine "Photoshop TryOut/Photoshop CS2/Setup.exe"` -> 1342x1080 window, blank
   white for a few seconds, then language picker (North American English), OK.
3. License Agreement dialog (Accept/Decline). Accepting it needs the owner's
   explicit yes in chat; it is not implied by "install CS2".

`shot.sh` style helper used: list visible windows with geometry via
`xdotool search --onlyvisible --name .`, `import -window root`, crop.

## Building Wine 11.0 pieces in the sandbox (#27 research)

    apt-get install -y build-essential flex bison gettext pkg-config \
      gcc-mingw-w64-x86-64 gcc-mingw-w64-i686 libx11-dev libxext-dev \
      libxrender-dev libxrandr-dev libxi-dev libxcomposite-dev libxcursor-dev \
      libxfixes-dev libxinerama-dev libfreetype-dev libfontconfig-dev \
      libgnutls28-dev libdbus-1-dev
    git clone --depth 1 --branch wine-11.0 https://github.com/wine-mirror/wine wine-11.0
    mkdir wine-build64 && cd wine-build64 && ../wine-11.0/configure --enable-win64 \
      --without-wayland --without-vulkan --without-opengl --without-gstreamer \
      --without-pulse --without-alsa --without-cups --without-sane --without-krb5 \
      --without-netapi --without-oss --without-pcap --without-usb --without-v4l2 \
      --without-gphoto --without-capi --without-xxf86vm --without-osmesa \
      --without-sdl --without-udev --without-unwind
    make -j3 dlls/win32u/win32u.so dlls/winex11.drv/winex11.so   # ~40 s each

Test a rebuilt `.so` in a copy (`cp -a /opt/wine-stable work/wine-exp`, drop it
into `lib/wine/x86_64-unix/`), never in `/opt`. WineHQ packages use old WoW64:
32-bit apps (FastStone) load `i386-unix/*.so`, which needs a separate i386 build.
FastStone 8.5: https://www.faststonesoft.net/DN/FSViewer85.zip, SHA256 in
tests/wine/faststone85.sh.

## Installer

Official `Photoshop_CS2.exe`, 345,068,035 bytes,
SHA256 `919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea`
(EXE inside: `98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30`).

    curl -fsS -o Photoshop_CS2.exe \
      https://download.adobe.com/pub/adobe/photoshop/win/cs2/Photoshop_CS2.exe
    sha256sum Photoshop_CS2.exe

- Use https: the `http://` form fails in the sandbox (the proxy does not
  resolve plain-HTTP hosts). Verified 2026-11-08: size and SHA256 match.
- Fallback mirror (owner-supplied, not reachable from the sandbox because
  `web.archive.org` resets every connection there):
  https://web.archive.org/web/20240522171734/http://download.adobe.com/pub/adobe/photoshop/win/cs2/Photoshop_CS2.exe
- Keep it at `/home/claude/work/photoshop-cs2/dl/`, outside the repo; never
  commit or upload the installer or prefix contents.
