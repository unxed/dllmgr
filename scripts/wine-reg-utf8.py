#!/usr/bin/env python3
"""UTF-8 Wine registry frontend for older fix-it-in-wine override helpers."""
import os
import subprocess
import sys

from wine_codepage import decode_stdout, decode_stderr


def main():
    wine = os.environ.get("DLLMGR_WINE", "wine")
    try:
        result = subprocess.run([wine, *sys.argv[1:]], capture_output=True)
    except OSError as error:
        print("cannot run %r: %s" % (wine, error), file=sys.stderr)
        return 127
    os.write(1, decode_stdout(result.stdout).encode("utf-8"))
    os.write(2, decode_stderr(result.stderr).encode("utf-8"))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
