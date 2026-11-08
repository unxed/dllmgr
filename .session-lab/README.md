# Temporary task37 session

Owner requested Actions offload for this chat/task only. Do not merge this branch into main or adopt it as project policy.

Run42529718835 uses the original63f3886 server. Local client now includes [skip ci] in command commits to avoid triggering unrelated push workflows. No runtime/server behavior changed.

Read the live session metadata from session-codex-8c42-42529718835-out:lab-results/session.json. With authenticated gh and this lab.py:

    python3 lab.py request --run 42529718835 '{"action":"snapshot"}'
    python3 lab.py request --run 42529718835 '{"action":"status"}'
    python3 lab.py request --run 42529718835 '{"action":"run","argv":["/opt/wine-stable/bin/wine","/path/from/session/../control/windows-install.exe"],"timeout":120}'
    python3 lab.py request --run 42529718835 '{"action":"stop"}'

Use fresh HWNDs from public enumeration. Results and screenshots download into lab-output/<run>/<request> and remain on unique output branches. Children receive no GitHub token. Run duration60min, idle20min, command timeout<=300sec. Only collaborators able to write the unique command branch can send commands. No installer/app binaries or prefix/trial state are in output branches or uploaded artifacts. The artifact expires after7days; preserve reviewed task evidence in main before finishing.
