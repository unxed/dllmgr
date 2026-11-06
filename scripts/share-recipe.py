#!/usr/bin/env python3
"""Print the link and install command for a dllmgr application recipe."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_fixes  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = "https://github.com/unxed/dllmgr"
RECIPE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
COMMIT = re.compile(r"[0-9a-f]{40}")


def source_revision(root):
    stamp = root / ".dllmgr-revision"
    if stamp.is_file():
        revision = stamp.read_text().strip()
    else:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
            capture_output=True,
            text=True,
        )
        revision = result.stdout.strip()
    if not COMMIT.fullmatch(revision):
        raise ValueError("cannot determine the installed dllmgr commit")
    return revision


def find_recipe(index, requested):
    for entry in index:
        if entry["kind"] != "bundle":
            continue
        recipe_id = entry["id"]
        app = entry.get("application")
        if not app and recipe_id.endswith("-all"):
            app = recipe_id.removesuffix("-all")
        if requested not in (recipe_id, app):
            continue
        path = f"bundles/{recipe_id}.md"
        if (
            not app
            or not RECIPE_ID.fullmatch(app)
            or not RECIPE_ID.fullmatch(recipe_id)
            or entry["path"] != path
        ):
            break
        return app, path
    raise ValueError(f"unknown installable recipe: {requested}")


def install_command(revision, app):
    return (
        '( tmp=$(mktemp -d) && trap \'rm -rf -- "$tmp"\' EXIT && '
        'git -C "$tmp" init -q && '
        f'git -C "$tmp" fetch -q --depth=1 {REPOSITORY}.git {revision} && '
        'git -C "$tmp" checkout -q --detach FETCH_HEAD && '
        'bash "$tmp/install.sh" && "$HOME/.local/bin/dllmgr" fix ' + app + " )"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, prog="dllmgr share")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--url", action="store_true", help="print only the recipe page")
    output.add_argument("--command", action="store_true", help="print only the install command")
    parser.add_argument("recipe", help="application or bundle ID")
    args = parser.parse_args()
    if not RECIPE_ID.fullmatch(args.recipe):
        parser.error("expected a lowercase application or bundle ID")
    try:
        index = catalog_fixes.load_index(ROOT / "catalog" / "index.json")
        app, path = find_recipe(index, args.recipe)
        command = None if args.url else install_command(source_revision(ROOT), app)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    if not args.command:
        print(f"{REPOSITORY}/blob/main/catalog/{path}")
    if command is not None:
        print(command)


if __name__ == "__main__":
    main()
