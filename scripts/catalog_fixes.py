#!/usr/bin/env python3
"""Resolve a recipe or fix ID to its fixes, using catalog/index.json only.

The bundle frontmatter is the single list of fixes for an application; the
installer, the tests and the release read it from here instead of copying it.

    catalog_fixes.py faststone        -> winehq-48872 winehq-48874 ...
    catalog_fixes.py winehq-59609     -> winehq-59609
"""
import json
from pathlib import Path
import sys

INDEX = Path(__file__).resolve().parent.parent / "catalog" / "index.json"


def resolve(requested, index=None):
    index = index if index is not None else json.loads(INDEX.read_text(encoding="utf-8"))
    for entry in index:
        if entry["kind"] == "fix" and entry["id"] == requested:
            return [requested]
        if entry["kind"] == "bundle" and requested in (entry["id"], entry.get("application")):
            return list(entry["fixes"])
    raise KeyError(requested)


def known(index=None):
    """Every ID accepted by resolve() for installable application bundles."""
    index = index if index is not None else json.loads(INDEX.read_text(encoding="utf-8"))
    ids = set()
    for entry in index:
        if entry["kind"] == "bundle" and entry.get("application"):
            ids.add(entry["application"])
            ids.update(entry["fixes"])
    return ids


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: catalog_fixes.py RECIPE_OR_FIX_ID")
    try:
        print(" ".join(resolve(sys.argv[1])))
    except KeyError:
        sys.exit(f"unknown fix set: {sys.argv[1]}")


if __name__ == "__main__":
    main()
