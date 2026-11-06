#!/usr/bin/env python3
"""Find the programs of installable recipes in a Wine prefix.

Read-only: it hashes candidate executables, never runs them and never writes.
Each found copy is matched against the recipe's `profiles` (the `when` rows of
docs/data-model.md): exe_sha256, wine, host_arch and prefix_arch.

    detect-apps.py [--exe PATH] PREFIX WINE_TAG
        prints one line per found copy: application, status, path, reason
    detect-apps.py --ready [--exe PATH] PREFIX WINE_TAG
        prints that report to stderr and the ready applications to stdout

An application is ready when every copy of its program in the prefix matches
the same row, because Wine scopes the override by exe name (select-faststone.py).
"""

import argparse
import hashlib
import os
from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_fixes  # noqa: E402

KEYS = ("wine", "host_arch", "prefix_arch")


def prefix_arch(prefix):
    try:
        with (prefix / "system.reg").open(encoding="utf-8", errors="replace") as registry:
            return next((line.strip()[6:] for line in registry if line.startswith("#arch=")), "")
    except OSError:
        return ""


def sha256(path):
    checksum = hashlib.sha256()
    with path.open("rb") as binary:
        for block in iter(lambda: binary.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def find(prefix, names, extra=()):
    """Copies of the named programs under drive_c, plus explicit paths."""
    wanted = {name.casefold() for name in names}
    found = {
        Path(root) / name
        for root, _, files in os.walk(prefix / "drive_c")
        for name in files
        if name.casefold() in wanted
    }
    found.update(Path(path).absolute() for path in extra if Path(path).name.casefold() in wanted)
    return sorted(found)


def match(profiles, digest, system):
    """(row, None) for a matching row, or (None, reason) naming what differs."""
    rows = [row for row in profiles if row.get("exe_sha256") == digest]
    if not rows:
        return None, f"this build ({digest[:12]}) has no verified row"
    for row in rows:
        if all(row.get(key) == system[key] for key in KEYS):
            return row, None
    for key in KEYS:
        measured = sorted({row.get(key) for row in rows})
        if system[key] not in measured:
            return None, f"{key}: verified on {', '.join(map(str, measured))}, this system has {system[key] or 'unknown'}"
    return None, "no single row matches this system"


def detect(index, prefix, wine, extra=(), host_arch=None):
    """[(application, status, path, reason)] and the set of ready applications."""
    system = {"wine": wine, "host_arch": host_arch or platform.machine(), "prefix_arch": prefix_arch(prefix)}
    report, ready = [], set()
    for entry in index:
        app = entry.get("application")
        if entry["kind"] != "bundle" or not app or not entry.get("profiles"):
            continue
        rows = []
        for path in find(prefix, entry.get("programs", []), extra):
            row, reason = match(entry["profiles"], sha256(path), system)
            rows.append(row)
            report.append((app, "ready" if row else "unverified", path, reason))
        if rows and all(row is not None and row == rows[0] for row in rows):
            ready.add(app)
        elif rows and any(rows):
            report.append((app, "blocked", None, "copies with the same exe name need different rows"))
    return report, ready


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ready", action="store_true", help="print ready applications to stdout")
    parser.add_argument("--exe", action="append", default=[], help="also check this executable")
    parser.add_argument("prefix", type=Path)
    parser.add_argument("wine", help="Wine tag, for example wine-11.0")
    args = parser.parse_args()
    report, ready = detect(catalog_fixes.load_index(), args.prefix, args.wine, args.exe)
    out = sys.stderr if args.ready else sys.stdout
    if not report:
        print(f"No program with a recipe was found in {args.prefix / 'drive_c'}.", file=out)
    for app, status, path, reason in report:
        line = f"{app}\t{status}" + (f"\t{path}" if path else "") + (f"\t({reason})" if reason else "")
        print(line, file=out)
    if args.ready:
        for app in sorted(ready):
            print(app)


if __name__ == "__main__":
    main()
