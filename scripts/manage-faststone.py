#!/usr/bin/env python3
"""Switch verified FastStone fix sets while retaining the original undo baseline."""
import argparse
import copy
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ["DLLMGR_TOOLS"])
import override

KNOWN = {"winehq-48872", "winehq-59251", "winehq-59609", "faststone"}


def installed_fix(entry):
    if not entry:
        return None
    managed = entry.get("dllmgr_fix")
    if managed in KNOWN:
        return managed
    legacy = json.loads(Path(__file__).with_name("legacy-59609.json").read_text())
    if entry["new_sha256"] in legacy:
        return "winehq-59609"
    raise override.OverrideError("unrecognized existing FSViewer override; undo it with its original tool first")


def restore(prefix, dest, raw, mode, link, state, registry):
    if link is None:
        override.write_atomic(dest, raw, mode)
    else:
        temp = dest + ".dllmgr-rollback-%d" % os.getpid()
        os.symlink(link, temp)
        os.replace(temp, dest)
    current = override.reg_query(prefix, "FSViewer.exe", "comctl32")
    if registry is None:
        if current is not None:
            override.reg_delete(prefix, "FSViewer.exe", "comctl32")
    else:
        override.reg_add(prefix, "FSViewer.exe", "comctl32", registry)
    override.save_state(prefix, state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["apply", "undo"])
    parser.add_argument("--fix", required=True, choices=sorted(KNOWN))
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--dll")
    parser.add_argument("--slot", default="system")
    args = parser.parse_args()
    prefix = os.path.abspath(args.prefix)
    state = override.load_state(prefix)
    entry = override.find_entry(state, "FSViewer.exe", "comctl32")
    previous = installed_fix(entry)
    if args.command == "undo":
        if previous != args.fix:
            raise override.OverrideError("%s is installed, not %s" % (previous or "no fix", args.fix))
        return override.main(["undo", "--prefix", prefix, "--exe", "FSViewer.exe", "--name", "comctl32"])

    if not args.dll:
        parser.error("apply requires --dll")
    raw = override.unmark(override.read_file(args.dll))
    arch = override.pe_machine(raw)
    dest = os.path.join(override.slot_dir(prefix, args.slot, arch, override.prefix_arch(prefix)), "comctl32.dll")
    if entry:
        if entry["dest"] != dest or override.file_sha(dest) != entry["new_sha256"]:
            raise override.OverrideError("installed DLL or slot changed; use the original undo before switching sets")
        if override.file_sha(entry["backup"]) != entry["orig_sha256"]:
            raise override.OverrideError("original backup is missing or changed")
        if entry["new_sha256"] == override.sha256(raw) and previous == args.fix:
            print("%s is already enabled for FSViewer.exe" % args.fix)
            return 0
        if any(e is not entry and e["dest"] == dest for e in state["entries"]):
            raise override.OverrideError("this DLL is shared by another managed application; cannot switch it")

    # Read everything before the first mutation. A failed switch restores the
    # old installed set, not just the prefix's original DLL.
    old_raw = override.read_file(dest)
    old_mode = os.stat(dest).st_mode & 0o7777
    old_link = os.readlink(dest) if os.path.islink(dest) else None
    old_state = copy.deepcopy(state)
    registry = override.reg_query(prefix, "FSViewer.exe", "comctl32")
    try:
        if entry:
            rc = override.main(["undo", "--prefix", prefix, "--exe", "FSViewer.exe", "--name", "comctl32"])
            if rc:
                raise override.OverrideError("could not remove the previous fix set")
        rc = override.main(["apply", "--prefix", prefix, "--exe", "FSViewer.exe", "--dll", args.dll,
                            "--name", "comctl32.dll", "--slot", args.slot])
        if rc:
            raise override.OverrideError("could not apply %s" % args.fix)
        state = override.load_state(prefix)
        override.find_entry(state, "FSViewer.exe", "comctl32")["dllmgr_fix"] = args.fix
        override.save_state(prefix, state)
    except BaseException:
        restore(prefix, dest, old_raw, old_mode, old_link, old_state, registry)
        raise
    print("Enabled %s for FSViewer.exe" % args.fix)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (override.OverrideError, override.NotPE, override.Placeholder) as error:
        print("dllmgr: %s" % error, file=sys.stderr)
        sys.exit(1)
