#!/usr/bin/env bash
# #39: Esc at fixed delays after FastStone starts, on Windows (git bash) or
# under Wine.  Every run starts from a fresh copy of the portable FastStone
# directory and without FastStone AppData (clean settings, like a first start).
#   esc39-run.sh OUT FSVIEWER85_DIR SMALL_JPG BIG_JPG
# Env: PROBE (./esc39-probe.exe), RUNNER=windows|wine, KEY=sendinput|xdotool (wine only), REPS (3),
#      DELAYS (Esc delays in ms with an image), NONE_DELAYS (without one).
set -uo pipefail
out=$1 src=$2 small=$3 big=$4
RUNNER=${RUNNER:-windows} KEY=${KEY:-sendinput} REPS=${REPS:-3}
DELAYS=${DELAYS:-200 400 600 800 1000 1200 1400 1600 2000 3000}
NONE_DELAYS=${NONE_DELAYS:-200 400 600 1000}
probe=${PROBE:-$PWD/esc39-probe.exe}
mkdir -p "$out"
base=${RUNNER_TEMP:-/tmp}; [ "$RUNNER" = windows ] && base=$(cygpath -u "$base")
work=$(mktemp -d "$base/esc39.XXXXXX")

winpath() { if [ "$RUNNER" = wine ]; then winepath -w "$1"; else cygpath -w "$1"; fi; }
appdata_dirs() {
    if [ "$RUNNER" = wine ]; then
        ls -d "$WINEPREFIX"/drive_c/users/*/AppData/*/FastStone* 2>/dev/null
    else
        ls -d "$(cygpath "$APPDATA")"/FastStone* "$(cygpath "$LOCALAPPDATA")"/FastStone* 2>/dev/null
    fi
}
fresh() {
    rm -rf "$work/app"
    cp -r "$src" "$work/app"
    appdata_dirs | while read -r d; do rm -rf "$d"; done
}
run() {  # NAME IMAGE|- DELAY MAX
    local name=$1 image=$2 delay=$3 max=$4 img=-
    fresh
    [ "$image" = - ] || img=$(winpath "$image")
    local exe; exe=$(winpath "$work/app/FSViewer.exe")
    if [ "$RUNNER" = windows ]; then
        "$probe" "$exe" "$img" f0cc5a "$delay" sendinput "$max" > "$out/$name.txt" 2>&1
    elif [ "$KEY" = sendinput ] || [ "$delay" -lt 0 ]; then
        wine "$probe" "$exe" "$img" f0cc5a "$delay" sendinput "$max" > "$out/$name.txt" 2>&1
    else
        rm -f "$work/launched"
        wine "$probe" "$exe" "$img" f0cc5a "$delay" none "$max" "$(winpath "$work")\\launched" > "$out/$name.txt" 2>&1 &
        local p=$!
        for _ in $(seq 1000); do [ -e "$work/launched" ] && break; sleep 0.01; done
        sleep "$(awk "BEGIN{print $delay/1000}")"
        echo "xdotool_focus=$(xdotool getwindowfocus getwindowname 2>/dev/null)" >> "$out/$name.xdotool"
        xdotool key Escape
        wait $p
    fi
    if [ "$RUNNER" = wine ]; then timeout 20 wineserver -w || true; fi
    grep '^result' "$out/$name.txt" | sed "s/^/$name /" | tee -a "$out/results.txt"
    appdata_dirs | sed "s/^/$name appdata: /" >> "$out/appdata.txt"
}

run warmup "$big" -1 6000
for i in $(seq "$REPS"); do
    for img in small big none; do
        case $img in small) f=$small;; big) f=$big;; none) f=-;; esac
        run "$img-observe-$i" "$f" -1 5000
        delays=$DELAYS; [ "$img" = none ] && delays=$NONE_DELAYS
        for d in $delays; do run "$img-esc$d-$i" "$f" "$d" 9000; done
    done
done
rm -rf "$work"
