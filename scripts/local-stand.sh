#!/bin/sh
# Local no-root headless stand for Photoshop CS2 under Wine 11.0.
# All components extracted from .deb into a private sysroot.
# Never touches the owner's desktop DISPLAY or ~/.wine.
# Usage:
#   sh local-stand.sh env          print environment
#   sh local-stand.sh up           start Xvfb + Muffin
#   sh local-stand.sh down         stop Xvfb + Muffin + wineserver
#   sh local-stand.sh prefix       create clean WINEPREFIX (win64, 192 DPI, no Mono/Gecko prompts)
#   sh local-stand.sh session CMD  run CMD inside the stand environment
#   sh local-stand.sh install-cs2  run the full unattended CS2 trial install
set -eu

AGENT_ID=photoshop-cs2-wine11
BASE=${BASE:-/home/ivan/stand/$AGENT_ID}
SR=$BASE/sysroot
STAND_DISPLAY=${STAND_DISPLAY:-:182}
STAND_DIR=$BASE
export STAND_DISPLAY STAND_DIR

if [ -z "${STAND_DISPLAY_SET:-}" ]; then
	sum=$(printf '%s' "$AGENT_ID" | sha256sum | cut -c1-2)
	dec=$(printf '%d' "0x$sum")
	STAND_DISPLAY=":$((100 + dec % 100))"
	export STAND_DISPLAY
fi

export DISPLAY=$STAND_DISPLAY
export WINEPREFIX=${WINEPREFIX:-$BASE/prefix110}
export WINEDEBUG=${WINEDEBUG:-fixme-all}
export WINEDLLOVERRIDES=${WINEDLLOVERRIDES:-mscoree=d}
export GSETTINGS_BACKEND=memory
export XDG_RUNTIME_DIR=$BASE/run
export XDG_CACHE_HOME=$BASE/cache
export XDG_CONFIG_HOME=$BASE/config
export XDG_DATA_HOME=$BASE/data
export PATH=$SR/opt/wine-stable/bin:$SR/usr/bin:$PATH
export LD_LIBRARY_PATH=$SR/usr/lib/x86_64-linux-gnu:$SR/usr/lib/x86_64-linux-gnu/muffin:$SR/lib/x86_64-linux-gnu:$SR/usr/lib/i386-linux-gnu
export FONTCONFIG_PATH=$SR/etc/fonts
export WINE=$SR/opt/wine-stable/bin/wine

# ImageMagick needs coder modules from the sysroot
export MAGICK_CONFIGURE_PATH=$SR/etc/ImageMagick-6
export MAGICK_CODER_MODULE_PATH=$SR/usr/lib/x86_64-linux-gnu/ImageMagick-6.9.12/modules-Q16/coders

mkdir -p "$XDG_RUNTIME_DIR" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$BASE/log" "$BASE/log/shots"
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true

case "${1:-}" in
env)
	env | grep -E '^(DISPLAY|WINEPREFIX|WINE|PATH|LD_LIBRARY|MAGICK)' | sort
	;;
up)
	if [ ! -e "/tmp/.X11-unix/X${STAND_DISPLAY#:}" ]; then
		setsid "$SR/usr/bin/Xvfb" "$STAND_DISPLAY" -screen 0 3072x1728x24 \
			-nolisten tcp -dpi 192 >"$BASE/log/xvfb.log" 2>&1 &
		sleep 3
	fi
	if ! xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q 'window id'; then
		setsid dbus-run-session -- "$SR/usr/bin/muffin" --sm-disable --x11 \
			>"$BASE/log/wm.log" 2>&1 &
		sleep 5
	fi
	xprop -root _NET_SUPPORTING_WM_CHECK _NET_WM_NAME 2>&1 | head -4
	;;
down)
	sh "$BASE/winekill.sh"
	;;
prefix)
	sh "$BASE/winekill.sh"
	rm -rf "$WINEPREFIX"
	mkdir -p "$WINEPREFIX"
	"$SR/opt/wine-stable/bin/wine" wineboot --init >"$BASE/log/wineboot.log" 2>&1
	"$SR/opt/wine-stable/bin/wineserver" -w
	# 192 DPI to match owner's laptop
	"$SR/opt/wine-stable/bin/wine" reg add 'HKLM\System\CurrentControlSet\Hardware Profiles\Current\Software\Fonts' \
		/v LogPixels /t REG_DWORD /d 192 /f
	"$SR/opt/wine-stable/bin/wineserver" -w
	echo "prefix ready: $WINEPREFIX"
	;;
session)
	shift
	exec "$@"
	;;
install-cs2)
	shift
	exec sh "$BASE/install-cs2.sh" "$@"
	;;
*)
	echo "usage: $0 {env|up|down|prefix|session CMD...|install-cs2}" >&2
	exit 2
	;;
esac