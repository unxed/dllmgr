#!/usr/bin/env python3
"""Switch verified FastStone fix sets, with one transaction across all modules."""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ["DLLMGR_TOOLS"])
import override

import catalog_fixes

KNOWN = catalog_fixes.known()
NAMES = {"comctl32", "gdiplus"}


def installed_fix(entry):
    if not entry:
        return None
    managed = entry.get("dllmgr_fix")
    if managed in KNOWN:
        return managed
    legacy = json.loads(Path(__file__).with_name("legacy-59609.json").read_text())
    if override.norm(entry["name"]) == "comctl32" and entry["new_sha256"] in legacy:
        return "winehq-59609"
    raise override.OverrideError("unrecognized existing FSViewer override; undo it with its original tool first")


def snapshot(prefix, dest, name):
    registry = override.reg_query(prefix, "FSViewer.exe", override.norm(name))
    if os.path.lexists(dest):
        raw = override.read_file(dest)
        mode = os.stat(dest).st_mode & 0o7777
        link = os.readlink(dest) if os.path.islink(dest) else None
    else:
        # New file (e.g. appdir slot): nothing to restore on rollback except removal.
        raw = None
        mode = None
        link = None
    return dict(dest=dest, name=name, raw=raw, mode=mode, link=link, registry=registry)


def restore(prefix, files, state):
    for item in files:
        if item["link"] is None:
            if item["raw"] is None:
                # New file we created: remove it on rollback.
                try:
                    os.unlink(item["dest"])
                except FileNotFoundError:
                    pass
            else:
                override.write_atomic(item["dest"], item["raw"], item["mode"])
        else:
            temp = item["dest"] + ".dllmgr-rollback-%d" % os.getpid()
            os.symlink(item["link"], temp)
            os.replace(temp, item["dest"])
        value = override.norm(item["name"])
        current = override.reg_query(prefix, "FSViewer.exe", value)
        if item["registry"] is None:
            if current is not None:
                override.reg_delete(prefix, "FSViewer.exe", value)
        else:
            override.reg_add(prefix, "FSViewer.exe", value, item["registry"])
    override.save_state(prefix, state)


def check_entry(state, entry, dest):
    if not entry:
        return
    installed_fix(entry)
    if entry["dest"] != dest or override.file_sha(dest) != entry["new_sha256"]:
        raise override.OverrideError("installed DLL or slot changed; use the original undo before switching sets")
    if override.file_sha(entry["backup"]) != entry["orig_sha256"]:
        raise override.OverrideError("original backup is missing or changed")
    if any(e is not entry and e["dest"] == dest for e in state["entries"]):
        raise override.OverrideError("this DLL is shared by another managed application; cannot switch it")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["apply","undo"])
    parser.add_argument("--fix",required=True,choices=sorted(KNOWN))
    parser.add_argument("--prefix",required=True)
    parser.add_argument("--dll")
    parser.add_argument("--name",default="comctl32.dll")
    parser.add_argument("--slot",default="system")
    parser.add_argument("--plan",type=Path)
    args = parser.parse_args()
    prefix = os.path.abspath(args.prefix)
    override.prefix_arch(prefix)
    # Lock the directory inode so different spellings of the same prefix serialize.
    fd = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return manage(args, parser, prefix)
    finally:
        os.close(fd)


def manage(args, parser, prefix):
    state = override.load_state(prefix)
    entries = [entry for entry in state["entries"]
               if entry["exe"].lower() == "fsviewer.exe" and override.norm(entry["name"]) in NAMES]
    plan = []
    if args.command == "undo":
        for entry in entries:
            if installed_fix(entry) == args.fix:
                check_entry(state,entry,entry["dest"])
                plan.append(dict(name=entry["name"],dest=entry["dest"],entry=entry))
        if not plan:
            raise override.OverrideError("%s is not installed" % args.fix)
    else:
        modules = json.loads(args.plan.read_text()) if args.plan else [dict(dll=args.dll,name=args.name,slot=args.slot)]
        seen = set()
        for module in modules:
            name = module["name"]
            if override.norm(name) not in NAMES or override.norm(name) in seen or not module.get("dll"):
                parser.error("apply needs unique supported modules and DLL paths")
            seen.add(override.norm(name))
            raw = override.unmark(override.read_file(module["dll"]))
            dest = os.path.join(override.slot_dir(prefix,module["slot"],override.pe_machine(raw),override.prefix_arch(prefix),
                                                  "FSViewer.exe"),name)
            entry = override.find_entry(state,"FSViewer.exe",name)
            check_entry(state,entry,dest)
            plan.append(dict(module,dest=dest,entry=entry,sha256=override.sha256(raw)))
        if not plan:
            parser.error("empty apply plan")
        removals = []
        for entry in entries:
            if override.norm(entry["name"]) in seen:
                continue
            check_entry(state, entry, entry["dest"])
            removals.append(dict(name=entry["name"], dest=entry["dest"], entry=entry))
        if not removals and all(item["entry"] and installed_fix(item["entry"]) == args.fix and
                                item["entry"]["new_sha256"] == item["sha256"] for item in plan):
            print("%s is already enabled for FSViewer.exe" % args.fix)
            return 0
        plan = removals + plan

    files = [snapshot(prefix,item["dest"],item["name"]) for item in plan]
    old_state = copy.deepcopy(state)
    try:
        for item in plan:
            if item["entry"]:
                rc = override.main(["undo","--prefix",prefix,"--exe","FSViewer.exe","--name",item["name"]])
                if rc:
                    raise override.OverrideError("could not remove the previous fix set")
            if "dll" in item:
                rc = override.main(["apply","--prefix",prefix,"--exe","FSViewer.exe","--dll",item["dll"],
                                    "--name",item["name"],"--slot",item["slot"]])
                if rc:
                    raise override.OverrideError("could not apply %s" % args.fix)
                if override.file_sha(item["dest"]) != item["sha256"]:
                    raise override.OverrideError("Wine replaced the installed DLL at %s" % item["dest"])
                updated = override.load_state(prefix)
                override.find_entry(updated,"FSViewer.exe",item["name"])["dllmgr_fix"] = args.fix
                override.save_state(prefix,updated)
    except BaseException:
        restore(prefix,files,old_state)
        raise
    print("%s %s for FSViewer.exe" % ("Enabled" if args.command == "apply" else "Removed",args.fix))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (override.OverrideError,override.NotPE,override.Placeholder) as error:
        print("dllmgr: %s" % error,file=sys.stderr)
        sys.exit(1)
