#!/usr/bin/env python3
"""Resolve a recipe or fix ID to its fixes, using catalog/index.json only.

The bundle frontmatter is the single list of fixes for an application; the
installer, the tests and the release read it from here instead of copying it.

    catalog_fixes.py faststone        -> winehq-48872 winehq-48874 ...
    catalog_fixes.py winehq-59609     -> winehq-59609
    catalog_fixes.py --release faststone wine-11.0 -> faststone-v2
"""
import json
import re
from pathlib import Path
import sys

INDEX = Path(__file__).resolve().parent.parent / "catalog" / "index.json"
FORMAT = 1


def load_index(path=INDEX):
    """Entries of catalog/index.json; refuses a format this copy cannot read."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError(f"{path}: unsupported catalog format; update dllmgr")
    return data["entries"]


def resolve(requested, index=None):
    index = index if index is not None else load_index()
    for entry in index:
        if entry["kind"] == "fix" and entry["id"] == requested:
            return [requested]
        if entry["kind"] == "bundle" and requested in (entry["id"], entry.get("application")):
            return list(entry["fixes"])
    raise KeyError(requested)


def release(requested, wine, index=None):
    """The bundle profile or individual fix's immutable prebuilt release."""
    index = index if index is not None else load_index()
    for entry in index:
        if entry["kind"] == "fix" and entry["id"] == requested:
            binaries = entry.get("binaries")
            if not binaries:
                return entry["id"]
            prefix = "https://github.com/unxed/dllmgr/releases/tag/"
            tag = binaries.removeprefix(prefix)
            if not binaries.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", tag):
                raise ValueError(f"{requested}: unsupported binary release URL")
            return tag
        if entry["kind"] == "bundle" and requested in (entry["id"], entry.get("application")):
            for profile in entry.get("profiles", []):
                if profile["wine"] == wine and profile.get("release"):
                    return profile["release"]
    raise KeyError(f"{requested} on {wine}")


def known(index=None):
    """Every ID accepted by resolve() for installable application bundles."""
    index = index if index is not None else load_index()
    ids = set()
    for entry in index:
        if entry["kind"] == "bundle" and entry.get("application"):
            ids.add(entry["application"])
            ids.update(entry["fixes"])
    return ids


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--release":
        try:
            print(release(sys.argv[2], sys.argv[3]))
        except KeyError:
            sys.exit(f"no prebuilt release for {sys.argv[2]} on {sys.argv[3]}")
        return
    if len(sys.argv) != 2:
        sys.exit("usage: catalog_fixes.py RECIPE_OR_FIX_ID")
    try:
        print(" ".join(resolve(sys.argv[1])))
    except KeyError:
        sys.exit(f"unknown fix set: {sys.argv[1]}")


if __name__ == "__main__":
    main()
