# env.sh (source me inside a stand session): FastStone 8.5 the way
# `dllmgr run faststone` starts it on the cc-rcnb-52ab stand: private runtime
# v21 (package sha256 fe29faf8d280), recipe faststone-v4 comctl32/gdiplus.
B=${B:-/home/unxed/.cache/dllmgr-agent/cc-rcnb-52ab}
export RT=$B/home/.local/share/dllmgr/runtimes/c6d2b6d208f77517fd9f24f00e10a28a2a5f6217aa9656cddda1950b4a38642a
export WINEPREFIX=$B/fs40/prefix
P='C:\dllmgr\apps\faststone-a77fd160eb1fd9a7f197\f8e2332674decdb2f1916d0c1a5fbe1707337919f4474f3ff0e5f8f592cd2385'
export TARGET='Z:\home\unxed\.cache\dllmgr-agent\cc-rcnb-52ab\fs40\FSViewer85\FSViewer.exe'
export BASE_COMCTL32="$P\\comctl32.dll" BASE_GDIPLUS="$P\\gdiplus.dll"
# The owner's locale (ru_RU.UTF-8), as `dllmgr run` inherits it.
export LANG=ru_RU.UTF-8 LC_ALL=
fs_start() {  # fs_start LOG [ARG]: FastStone with an optional folder/file argument
	env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver DLLMGR_TARGET_EXE="$TARGET" \
		DLLMGR_COMCTL32="$BASE_COMCTL32" DLLMGR_GDIPLUS="$BASE_GDIPLUS" WINEDLLOVERRIDES=msimg32=n,b \
		WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine "$TARGET" ${2:+"$2"} > "$1" 2>&1 &
}
fs_kill() { env WINESERVER=$RT/bin/wineserver $RT/bin/wineserver -k 2>/dev/null; sleep 1; }
