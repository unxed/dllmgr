#!/bin/sh
# Rebuild the headless Photoshop CS2 test stand in a disposable Ubuntu 24.04
# (noble) sandbox, e.g. a Claude cloud session. See docs/sandbox-stand.md.
#
# Usage: sudo sh scripts/sandbox-stand.sh [install|up|prefix|all]
#   install  pinned Wine 11.0 from WineHQ + X/WM tools (needs root, network)
#   up       start Xvfb + Muffin on $STAND_DISPLAY (idempotent)
#   prefix   create a clean $WINEPREFIX without Mono/Gecko
#   all      install + up + prefix (default)
#
# Never point this at the owner's desktop DISPLAY or ~/.wine.
set -eu

WINE_VER=11.0.0.0~noble-1
STAND_DIR=${STAND_DIR:-/home/claude/work/photoshop-cs2}
STAND_DISPLAY=${STAND_DISPLAY:-:92}
export DISPLAY=$STAND_DISPLAY
export WINEPREFIX=${WINEPREFIX:-$STAND_DIR/prefix110}
export WINEDEBUG=${WINEDEBUG:-fixme-all}
export GSETTINGS_BACKEND=memory
WINE=/opt/wine-stable/bin

install_pkgs() {
	dpkg --print-foreign-architectures | grep -qx i386 || dpkg --add-architecture i386
	mkdir -pm755 /etc/apt/keyrings
	curl -fsSL https://dl.winehq.org/wine-builds/winehq.key \
		-o /etc/apt/keyrings/winehq-archive.key
	curl -fsSL https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources \
		-o /etc/apt/sources.list.d/winehq-noble.sources
	apt-get update -qq
	# Pin exactly 11.0: results on other Wine versions must not be reported.
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --install-recommends \
		winehq-stable=$WINE_VER wine-stable=$WINE_VER \
		wine-stable-amd64=$WINE_VER wine-stable-i386=$WINE_VER \
		muffin metacity xdotool x11-utils x11-apps imagemagick dbus-x11
	# Muffin aborts at start without the org.cinnamon.settings-daemon.* schemas.
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
		cinnamon-settings-daemon
	# Official add-ons where stock Wine looks for them, so wineboot installs
	# them silently like a normal desktop Wine (versions from appwiz.cpl).
	mkdir -p /opt/wine-stable/share/wine/gecko /opt/wine-stable/share/wine/mono
	for a in x86 x86_64; do
		f=/opt/wine-stable/share/wine/gecko/wine-gecko-2.47.4-$a.msi
		[ -s "$f" ] || curl -fsS -o "$f" https://dl.winehq.org/wine/wine-gecko/2.47.4/${f##*/}
	done
	f=/opt/wine-stable/share/wine/mono/wine-mono-10.4.1-x86.msi
	[ -s "$f" ] || curl -fsS -o "$f" https://dl.winehq.org/wine/wine-mono/10.4.1/${f##*/}
	"$WINE/wine" --version
}

up() {
	mkdir -p "$STAND_DIR"
	if [ ! -e "/tmp/.X11-unix/X${STAND_DISPLAY#:}" ]; then
		setsid Xvfb "$STAND_DISPLAY" -screen 0 3072x1728x24 -nolisten tcp -dpi 192 \
			>"$STAND_DIR/xvfb.log" 2>&1 &
		sleep 2
	fi
	if ! xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q 'window id'; then
		setsid dbus-run-session -- muffin --sm-disable --x11 >"$STAND_DIR/wm.log" 2>&1 &
		sleep 3
	fi
	xprop -root _NET_SUPPORTING_WM_CHECK
	xdpyinfo | grep -E 'dimensions|resolution'
}

# Self-contained run: own Xvfb + Muffin in the foreground, run "$@" (or just
# hold the session if no command), then tear everything down. Use this as one
# background task per experiment; detached X processes do not survive replies.
session() {
	mkdir -p "$STAND_DIR"
	rm -f "/tmp/.X${STAND_DISPLAY#:}-lock" "/tmp/.X11-unix/X${STAND_DISPLAY#:}"
	Xvfb "$STAND_DISPLAY" -screen 0 3072x1728x24 -nolisten tcp -dpi 192 \
		>"$STAND_DIR/xvfb.log" 2>&1 &
	xpid=$!
	# The socket file appears before Xvfb accepts clients: poll a real client.
	for _ in $(seq 100); do xdpyinfo >/dev/null 2>&1 && break; sleep .1; done
	# STAND_WM: muffin (default; mutter-based, ALWAYS composites) or metacity
	# (with --compositor=none, as in the owner's #27 FastStone stand). Tests that
	# sample pixels through the screen DC need the non-compositing metacity.
	if [ "${STAND_WM:-muffin}" = metacity ]; then
		dbus-run-session -- metacity --sm-disable --compositor=none >"$STAND_DIR/wm.log" 2>&1 &
	else
		dbus-run-session -- muffin --sm-disable --x11 >"$STAND_DIR/wm.log" 2>&1 &
	fi
	wpid=$!
	# set -e is active inside traps too: every teardown step must not fail, or
	# the shell exits with 1 before killing X (that leaked Xvfb/Muffin before).
	trap '"$WINE/wineserver" -k 2>/dev/null || :; pkill -P $wpid 2>/dev/null || :
		kill $wpid $xpid 2>/dev/null || :' EXIT
	trap 'exit 130' INT TERM
	for _ in $(seq 150); do
		xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q 'window id' && break
		sleep .1
	done
	xprop -root _NET_SUPPORTING_WM_CHECK | grep 'window id' ||
		{ echo "session: no WM on $STAND_DISPLAY, see $STAND_DIR/wm.log" >&2; exit 1; }
	rc=0
	if [ $# -gt 0 ]; then "$@" || rc=$?; else wait $xpid || rc=$?; fi
	exit $rc
}

prefix() {
	[ -e "$WINEPREFIX" ] && { echo "exists: $WINEPREFIX (delete it yourself)"; return 0; }
	# Needs a display: run as `session` (sandbox-stand.sh session sh ... prefix)
	# or inside one. Add-ons from install_pkgs are installed silently.
	timeout 600 "$WINE/wineboot" -i >"$STAND_DIR/wineboot.log" 2>&1
	timeout 120 "$WINE/wineserver" -w
	# Owner's stand runs Wine at 192 DPI (winecfg's key); a fresh prefix is 96.
	"$WINE/wine" reg add 'HKLM\System\CurrentControlSet\Hardware Profiles\Current\Software\Fonts' \
		/v LogPixels /t REG_DWORD /d 192 /f
	timeout 120 "$WINE/wineserver" -w
	echo "prefix ready: $WINEPREFIX"
}

case "${1:-all}" in
	install) install_pkgs ;;
	up) up ;;
	prefix) prefix ;;
	session) shift; session "$@" ;;
	all) install_pkgs; up; prefix ;;
	*) echo "usage: $0 [install|up|prefix|session [cmd...]|all]" >&2; exit 2 ;;
esac
