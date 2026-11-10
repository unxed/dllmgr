#!/bin/sh
# Unattended Photoshop CS2 *trial* install into $WINEPREFIX on the sandbox
# stand, replaying the GUI path recorded in docs/sandbox-stand.md.
# Run INSIDE a stand session, with a fresh prefix made by `sandbox-stand.sh prefix`
# (192 DPI; the click coordinates below are client-area pixels at 192 DPI):
#
#   sh scripts/sandbox-stand.sh session sh scripts/sandbox-install-cs2.sh
#
# The owner accepted the CS2 trial EULA for this work (issue #31, 2026-11-08);
# the script presses Accept. It never enters a serial or bypasses activation.
# Known Wine defects on the way are expected (docs/sandbox-findings.md F11-F14):
# the final dialog shows "&Finish" everywhere and msiexec then crashes with
# 0x6a6; the script dismisses that crash dialog.
set -eu
WINE=/opt/wine-stable/bin
STAND_DIR=${STAND_DIR:-/home/claude/work/photoshop-cs2}
INSTALLER=${INSTALLER:-$STAND_DIR/dl/Photoshop_CS2.exe}
SHA=919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea
EXE_SHA=98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30
LOG=$STAND_DIR/install-cs2.log
: "${WINEPREFIX:?}" "${DISPLAY:?}"

step() { echo "== $*"; }
# win REGEX [SECONDS]: print id of a visible window, waiting for it (default 90 s)
win() {
	t=0
	until w=$(xdotool search --onlyvisible --name "$1" 2>/dev/null | tail -1) && [ -n "$w" ]; do
		[ $t -ge "${2:-90}" ] && { echo "timeout waiting for /$1/" >&2; exit 1; }
		sleep 1; t=$((t + 1))
	done
	echo "$w"
}
# painted ID: wait until the window client area is no longer one flat colour
painted() {
	t=0
	while [ "$(import -window "$1" png:- 2>/dev/null | convert png:- -format '%k' info: 2>/dev/null || echo 1)" -le 2 ]; do
		[ $t -ge 60 ] && { echo "window $1 never painted" >&2; exit 1; }
		sleep 1; t=$((t + 1))
	done
	sleep 1
}
click() { xdotool windowactivate --sync "$1" mousemove --window "$1" "$2" "$3" click 1; sleep 1; }

step "verify installer"
echo "$SHA  $INSTALLER" | sha256sum -c -

step "unpack (unzip == WinZip SFX output, verified identical)"
SRC=$STAND_DIR/dl/unpacked
[ -e "$SRC" ] && chmod -R u+w "$SRC"; rm -rf "$SRC"; mkdir -p "$SRC"; unzip -q "$INSTALLER" -d "$SRC"
cd "$SRC/Photoshop CS2"
"$WINE/wine" Setup.exe >"$LOG" 2>&1 &

step "language picker"
w=$(win '^Adobe Photoshop CS2$'); painted "$w"
# The background paints before the controls; Enter sent too early is lost.
sleep 3; click "$w" 622 688   # OK

step "EULA: Accept (trial, owner-approved)"
w=$(win 'License Agreement'); painted "$w"; sleep 2
xdotool windowactivate --sync "$w" key alt+a; sleep 3

step "AutoPlay: Install Photoshop CS2"
w=$(win '^Adobe Photoshop CS2$'); painted "$w"
click "$w" 710 410

step "MSI welcome: Next"
w=$(win 'Photoshop CS2 - Setup' 120); painted "$w"
xdotool windowactivate --sync "$w" key Return; sleep 3

step "Customer information: user Tester, 30-day trial"
w=$(win 'Photoshop CS2 - Setup'); painted "$w"
click "$w" 476 120; xdotool type --delay 30 Tester
click "$w" 212 262
click "$w" 436 419; sleep 3

step "Destination folder: default, Next"
w=$(win 'Photoshop CS2 - Setup'); painted "$w"
click "$w" 436 419; sleep 3

step "File association (996x681 custom dialog): defaults, Next"
w=$(win 'Photoshop CS2 - Setup'); painted "$w"
click "$w" 694 640; sleep 3

step "Ready to install: Install"
w=$(win 'Photoshop CS2 - Setup'); painted "$w"
click "$w" 436 419

step "wait for final dialog (F13: all texts read &Finish)"
w=$(win '&Finish' 900); painted "$w"
click "$w" 448 282   # uncheck the unlabeled checkbox (do not auto-launch)
click "$w" 688 646   # the enabled Finish button

step "dismiss msiexec crash (F14), if it happens"
if w=$(win 'Program Error|Программная ошибка' 30 2>/dev/null); then click "$w" 704 496; fi
"$WINE/wineserver" -w

step "verify"
EXE="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
echo "$EXE_SHA  $EXE" | sha256sum -c -
echo "CS2 trial installed into $WINEPREFIX"
