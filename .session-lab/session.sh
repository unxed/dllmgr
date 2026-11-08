#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$LAB_OUT" "$STAND_DIR/dl" "$STAND_DIR/control"
sh scripts/sandbox-stand.sh prefix > "$LAB_OUT/prefix.log" 2>&1
/opt/wine-stable/bin/wine reg add 'HKCU\Control Panel\Desktop' /v LogPixels /t REG_DWORD /d 192 /f >> "$LAB_OUT/prefix.log" 2>&1
for helper in windows-install product-state; do
    libs=-luser32
    [ "$helper" != product-state ] || libs=-lmsi
    i686-w64-mingw32-gcc -O2 -s "experiments/cs2-debian-installation/$helper.c" -o "$STAND_DIR/control/$helper.exe" "$libs"
done
set +e
timeout 1500 sh scripts/sandbox-install-cs2.sh > "$LAB_OUT/installer-steps.log" 2>&1
install_rc=$?
set -e
cp "$STAND_DIR/install-cs2.log" "$LAB_OUT/install-cs2.log" || true
import -window root "$LAB_OUT/after-install.png"
printf '%s\n' "$install_rc" > "$LAB_OUT/installer-harness-exit.txt"
/opt/wine-stable/bin/wine "$STAND_DIR/control/product-state.exe" > "$LAB_OUT/product-state.txt" 2>&1 || true
if [ "$install_rc" != 0 ]; then exit "$install_rc"; fi
app="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
sha256sum "$app/Photoshop.exe" > "$LAB_OUT/installed-exe.sha256"
(cd "$app" && /opt/wine-stable/bin/wine Photoshop.exe > "$LAB_OUT/photoshop.log" 2>&1) &
printf '%s\n' "$!" > "$LAB_OUT/photoshop-launch.pid"
python3 .session-lab/lab.py serve --minutes 60
