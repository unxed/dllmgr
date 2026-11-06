#!/usr/bin/env bash
# Spike: comctl32 from Wine 11 in the system Wine 9, for one exe only.
# Installs nothing in the system, changes only the prefix, can roll back.
#   ./spike0.sh probe "/path/FSViewer.exe"        # what gets loaded (close the program to get the summary)
#   ./spike0.sh apply wine-stable-i386_11*.deb system|sxs
#   ./spike0.sh undo system|sxs
set -euo pipefail
P="${WINEPREFIX:-$HOME/.wine}"; export WINEPREFIX="$P"
APP="${APP:-FSViewer.exe}"
KEY="HKCU\\Software\\Wine\\AppDefaults\\$APP\\DllOverrides"
sig() { dd if="$1" bs=1 skip=64 count=16 status=none; }
case "${1:-}" in
probe)
  mkdir -p "$P/spike0"
  WINEDEBUG=+loaddll,warn+module wine "$2" >/dev/null 2>"$P/spike0/probe.log" || true
  grep -aE 'comctl32|No implementation' "$P/spike0/probe.log" | sort -u | head -30 ;;
apply)
  mode="$3"; BK="$P/spike0/$mode"
  [ -e "$BK/dest" ] && { echo "already applied: undo $mode"; exit 1; }
  X=$(mktemp -d); trap 'rm -rf "$X"' EXIT; dpkg-deb -x "$2" "$X"
  if [ "$mode" = system ]; then
    src=$(find "$X" -path '*/i386-windows/comctl32.dll')
    grep -q '^#arch=win64' "$P/system.reg" && d=syswow64 || d=system32
    dest="$P/drive_c/windows/$d/comctl32.dll"
  else
    src=$(find "$X" -path '*/i386-windows/comctl32_v6.dll')
    dirs=("$P"/drive_c/windows/winsxs/x86_microsoft.windows.common-controls_6595b64144ccf1df_6.*/)
    [ ${#dirs[@]} -eq 1 ] || { printf 'exactly one directory is required:\n%s\n' "${dirs[@]}"; exit 1; }
    dest="${dirs[0]%/}/comctl32.dll"
  fi
  [ -f "$src" ] && [ -e "$dest" ] || { echo "no src='$src' or dest='$dest'"; exit 1; }
  [ "$(sig "$src")" = "Wine builtin DLL" ] || { echo "src has no builtin mark - stop"; exit 1; }
  mkdir -p "$BK"; cp -a "$dest" "$BK/orig.dll"; echo "$dest" > "$BK/dest"
  rm -f "$dest"                                   # never write through a symlink
  cp "$src" "$dest"
  dd if=/dev/zero of="$dest" bs=1 seek=64 count=32 conv=notrunc status=none
  wine reg add "$KEY" /v comctl32 /d native,builtin /f
  echo "OK: $dest" ;;
undo)
  BK="$P/spike0/$2"; dest=$(cat "$BK/dest")
  rm -f "$dest"; cp -a "$BK/orig.dll" "$dest"; rm "$BK/dest"
  [ -e "$P/spike0/system/dest" ] || [ -e "$P/spike0/sxs/dest" ] || \
    wine reg delete "$KEY" /v comctl32 /f ;;
*) echo "usage: probe <exe> | apply <deb> system|sxs | undo system|sxs"; exit 1 ;;
esac
