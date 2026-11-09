#!/usr/bin/env python3
"""Make the extracted Wine tree relocatable without root.

Debian/WineHQ binaries hardcode the build-time install prefix ("/opt/wine-stable").
The private sysroot lives somewhere else, so every hardcoded C string that
starts with that prefix is rewritten to a short base directory (default
/tmp/wXXXXXXXX) that the stand creates as a symlink to <sysroot>/opt/wine-stable.

Rewriting is done per whole C string and only when the replacement is not
longer than the original, so no relocation is needed in the ELF.
"""
import argparse
import os
import sys

OLD_PREFIX = b"/opt/wine-stable"


def rewrite(data: bytes, new_base: bytes):
    """Return (new_data, count). Pads the shortened string with NUL bytes."""
    out = bytearray(data)
    count = 0
    pos = 0
    while True:
        start = out.find(OLD_PREFIX, pos)
        if start < 0:
            break
        end = out.find(b"\0", start)
        if end < 0:
            end = len(out)
        old = bytes(out[start:end])
        suffix = old[len(OLD_PREFIX):]
        new = new_base + suffix
        if len(new) <= len(old):
            out[start:end] = new + b"\0" * (len(old) - len(new))
            count += 1
        pos = start + len(old)
    return bytes(out), count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sysroot")
    ap.add_argument("--new-base", default=None,
                    help="replacement prefix, must be shorter than %s" % OLD_PREFIX.decode())
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.new_base:
        new_base = args.new_base.encode()
    else:
        # 8 hex chars keep parallel stands apart while staying short enough
        # for every hardcoded string (".../share/wine/nls" is the longest).
        import hashlib
        tag = hashlib.sha256(os.path.abspath(args.sysroot).encode()).hexdigest()[:8]
        new_base = ("/tmp/w" + tag).encode()
    if len(new_base) >= len(OLD_PREFIX):
        print("new base must be shorter than %s" % OLD_PREFIX.decode(), file=sys.stderr)
        return 2

    total_files = 0
    total_strings = 0
    for root, dirs, files in os.walk(args.sysroot):
        dirs[:] = [d for d in dirs if d not in ("share", "include")]
        for name in files:
            path = os.path.join(root, name)
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            if OLD_PREFIX not in data:
                continue
            new_data, count = rewrite(data, new_base)
            if count:
                total_files += 1
                total_strings += count
                if not args.dry_run:
                    with open(path, "wb") as fh:
                        fh.write(new_data)
    print("patched %d string(s) in %d file(s); new base %s"
          % (total_strings, total_files, new_base.decode()))
    if not args.dry_run:
        link = new_base.decode()
        target = os.path.join(os.path.abspath(args.sysroot), "opt", "wine-stable")
        if os.path.islink(link) or os.path.exists(link):
            os.remove(link)
        os.symlink(target, link)
        print("symlink %s -> %s" % (link, target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
