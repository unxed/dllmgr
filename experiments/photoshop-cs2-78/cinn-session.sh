#!/bin/sh
# cinn-session.sh CMD...: Xvfb :132 (3072x1728, 192 DPI) + full Cinnamon
# (cinnamon --replace on :132 only) and runs CMD in it.
# Isolation from the owner's session (:0): own HOME/XDG dirs/dconf db
# (env.sh), own session bus (dbus-run-session), no SESSION_MANAGER (XSMP),
# no a11y bus; NM, polkit and SSH agents switched off in the private dconf.
# Cleanup kills only PIDs that carry this run's STAND78 marker.
# needs the agent stand env (HOME/XDG_* isolated from the owner, $B)
. ${ENV_SH:?path to the stand env.sh}
S=${S:-$B/sub10}
unset DBUS_SESSION_BUS_ADDRESS SESSION_MANAGER DESKTOP_AUTOSTART_ID GNOME_KEYRING_CONTROL SSH_AUTH_SOCK
export DISPLAY=:132 NO_AT_BRIDGE=1 STAND78=cinn-$$ S
[ -e /tmp/.X11-unix/X132 ] && { echo ":132 busy"; exit 1; }
Xvfb :132 -screen 0 3072x1728x24 -nolisten tcp -dpi 192 -noreset > $S/xvfb.log 2>&1 &
XP=$!
for i in $(seq 30); do xdpyinfo >/dev/null 2>&1 && break; sleep 1; done
dbus-run-session -- sh -c '
  for k in enable-nm-agent enable-polkit-agent enable-ssh-agent; do gsettings set org.cinnamon $k false; done
  gsettings set org.cinnamon alttab-switcher-style "icons+preview"
  gsettings set org.cinnamon alttab-switcher-delay 100
  cinnamon --replace > $S/cinnamon.log 2>&1 & CP=$!
  echo "cinnamon pid $CP"
  for i in $(seq 40); do xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q "window id" && break; sleep 1; done
  sleep 8
  echo "bus check: $(tr "\0" "\n" < /proc/$CP/environ | grep -E "^(DBUS_SESSION_BUS_ADDRESS|SESSION_MANAGER|DISPLAY|HOME)=" | tr "\n" " ")"
  "$@"; rc=$?
  kill $CP; sleep 2; exit $rc' sh "$@"
rc=$?
kill $XP; wait $XP 2>/dev/null
for p in $(grep -l -a "STAND78=$STAND78" /proc/[0-9]*/environ 2>/dev/null | cut -d/ -f3); do
	[ "$p" = "$$" ] && continue; [ -r /proc/$p/cmdline ] && [ -s /proc/$p/cmdline ] || continue; echo "leftover $p: $(cut -c1-60 /proc/$p/cmdline | tr '\0' ' ')"; kill "$p"
done
exit $rc
