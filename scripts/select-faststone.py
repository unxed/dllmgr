#!/usr/bin/env python3
"""Select a verified FastStone executable before changing a Wine prefix."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys


def select(catalog, prefix, wine, requested):
    bundle = next(entry for entry in catalog if entry["id"] == "faststone-all")
    program = bundle["programs"][0]
    profiles = [
        profile for profile in bundle["profiles"]
        if profile["wine"] == wine and profile["host_arch"] == platform.machine()
    ]
    if not profiles:
        raise ValueError(f"no verified FastStone profile for {wine} on {platform.machine()}")
    with (prefix / "system.reg").open(encoding="utf-8", errors="replace") as registry:
        prefix_arch = next((line.strip()[6:] for line in registry if line.startswith("#arch=")), "")
    profiles = {profile["exe_sha256"]: profile for profile in profiles if profile["prefix_arch"] == prefix_arch}
    if not profiles:
        raise ValueError(f"no verified FastStone profile for a {prefix_arch or 'unknown architecture'} prefix")

    def walk_error(error):
        raise error

    # Wine scopes the override by executable basename. Check every visible copy
    # in drive_c before installing a rule they would share.
    copies = {
        Path(root) / name
        for root, _, files in os.walk(prefix / "drive_c", onerror=walk_error)
        for name in files
        if name.casefold() == program.casefold()
    }
    if requested is not None:
        if requested.name.casefold() != program.casefold() or not requested.is_file():
            raise ValueError(f"--exe must point to an existing {program}")
        copies.add(requested.absolute())
    if not copies:
        raise ValueError(f"{program} was not found in {prefix / 'drive_c'}; use --exe PATH for portable copies")

    matched = []
    for exe in sorted(copies):
        with exe.open("rb") as binary:
            checksum = hashlib.sha256()
            for block in iter(lambda: binary.read(1024 * 1024), b""):
                checksum.update(block)
            digest = checksum.hexdigest()
        if digest not in profiles:
            raise ValueError(f"{exe} is not a verified FastStone build; the existing overrides were kept")
        matched.append(profiles[digest])
    if any(profile != matched[0] for profile in matched[1:]):
        raise ValueError("FastStone copies in this prefix require different profiles")
    return requested.absolute() if requested else min(copies)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("prefix", type=Path)
    parser.add_argument("wine")
    parser.add_argument("exe", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        print(select(json.loads(args.catalog.read_text()), args.prefix, args.wine, args.exe))
    except (OSError, ValueError) as error:
        parser.exit(2, f"dllmgr: {error}\n")


if __name__ == "__main__":
    main()
