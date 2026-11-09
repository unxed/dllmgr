#!/bin/sh
# #48 live check: Muffin with the dconf backend on :96; xev sees Alt+click
# only when the window modifier is not Alt; switched live via gsettings.
D=/home/claude/work/r48; export DISPLAY=:96 HOME=$D/home XDG_CONFIG_HOME=$D/home/.config
mkdir -p $XDG_CONFIG_HOME
pkill -f 'Xvfb :96' ; rm -f /tmp/.X96-lock; sleep 1
Xvfb :96 -screen 0 1024x768x24 >/dev/null 2>&1 & sleep 2
eval $(dbus-launch --sh-syntax); export GSETTINGS_BACKEND=dconf
gsettings set org.cinnamon.desktop.wm.preferences mouse-button-modifier '<Alt>'
muffin --sm-disable --x11 >$D/wm.log 2>&1 & sleep 4
xev -geometry 400x300+100+100 -event button > $D/xev.log 2>&1 & sleep 3
click() { xdotool mousemove 300 250; xdotool keydown alt; xdotool click 1; xdotool keyup alt; sleep 1; }
click; echo "modifier Alt: presses seen $(grep -c ButtonPress $D/xev.log)"
python3 -c "import sys; sys.path.insert(0,'/home/claude/dllmgr/scripts'); import importlib.util as u; s=u.spec_from_file_location('pa','/home/claude/dllmgr/scripts/private-app.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print('gsettings via module:', m.gsettings('get', m.WM_SCHEMA, m.WM_KEY))"
gsettings set org.cinnamon.desktop.wm.preferences mouse-button-modifier '<Super>'; sleep 1
click; echo "modifier Super: presses seen $(grep -c ButtonPress $D/xev.log)"
kill %3 %2 %1 2>/dev/null; kill $DBUS_SESSION_BUS_PID
