#!/bin/sh
# #48 flow: real gsettings (dconf), real detached wm-restore, real wineserver -w.
D=/home/claude/work/r48; export HOME=$D/home XDG_CONFIG_HOME=$D/home/.config
P=/tmp/claude-0/-home-claude/71c1be2e-9f14-5b87-94fa-9d3adfcbd591/scratchpad/pfx; mkdir -p $P/.dllmgr
eval $(dbus-launch --sh-syntax); export GSETTINGS_BACKEND=dconf WINEPREFIX=$P WINESERVER=/home/claude/work/rt-cur3/bin/wineserver
g() { gsettings get org.cinnamon.desktop.wm.preferences mouse-button-modifier; }
gsettings set org.cinnamon.desktop.wm.preferences mouse-button-modifier '<Alt>'
python3 -c "
import os, sys, importlib.util as u; sys.path.insert(0, '/home/claude/dllmgr/scripts')
s=u.spec_from_file_location('pa','/home/claude/dllmgr/scripts/private-app.py'); m=u.module_from_spec(s); s.loader.exec_module(m)
from pathlib import Path
m.free_alt_click(Path('$P'), 'photoshop-cs2', dict(os.environ))
os.execv('/home/claude/work/rt-cur3/bin/wine', ['wine', 'cmd', '/c', 'exit'])" &
sleep 1; echo "t=1 running: $(g)"
sleep 1; echo "t=2 app running: $(g)"
until ! pgrep -f "rt-cur3/bin/wineserver" >/dev/null; do sleep 1; done; sleep 2; echo "after server exit: $(g)"; echo "mark: $(ls $P/.dllmgr/wm-modifier 2>&1)"; cat $P/.dllmgr/launch.log
while pgrep -f wm-restore >/dev/null; do sleep 1; done; echo "after restorer: $(g)"; cat $P/.dllmgr/launch.log; ls $P/.dllmgr; kill $DBUS_SESSION_BUS_PID
