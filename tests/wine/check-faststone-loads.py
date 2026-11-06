"""Check Wine's module-load trace for the observed FastStone x86 process."""

from pathlib import Path
import re
import sys


def main(observations, trace):
    process = re.search(r"^app_pid=([0-9a-f]+)$", observations.read_text(), re.MULTILINE)
    if not process:
        sys.exit("Missing FastStone process ID")
    prefix = process[1].lower() + ":"
    expected = {
        "comctl32.dll": r"\\winsxs\\x86_microsoft.windows.common-controls_6595b64144ccf1df_6\.",
        "gdiplus.dll": r"\\syswow64\\gdiplus\.dll\"",
    }
    for line in trace.read_text(errors="replace").splitlines():
        entry = line.lower()
        if not (entry.startswith(prefix) and ":trace:loaddll:" in entry and entry.endswith(": native")):
            continue
        # Wine escapes path separators in its debug strings.
        entry = entry.replace("\\\\", "\\")
        for name, path in list(expected.items()):
            if re.search(path, entry) and f'{name}"' in entry:
                print(line)
                del expected[name]
    if expected:
        sys.exit("Missing native FastStone x86 loads: " + ", ".join(expected))


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:]))
