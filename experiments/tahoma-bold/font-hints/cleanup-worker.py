"""FontForge-only cleanup worker; build-clean.py enforces its timeout."""
import json
import sys
from pathlib import Path
import fontforge

source, original, affected, directory = sys.argv[1:]
out = Path(directory)
f, old = fontforge.open(source), fontforge.open(original)
report = []
for cp in [int(code[2:], 16) for code in json.loads(Path(affected).read_text())]:
    g = f[cp]
    advance = g.width
    before = g.validate(True)
    record = {"codepoint": f"U+{cp:04X}", "name": g.glyphname,
              "original_validation": old[cp].validate(True),
              "before_validation": before, "before_bbox": g.boundingBox(),
              "before_points": sum(len(c) for c in g.foreground),
              "advance": advance, "stage": "starting"}
    report.append(record)
    def checkpoint(stage):
        record["stage"] = stage
        (out / "cleanup-progress.json").write_text(json.dumps(report, indent=2) + "\n")
        print(record["codepoint"], stage, flush=True)
    if before & 4:
        checkpoint("removeOverlap")
        g.removeOverlap()
    if before & 12:
        checkpoint("correctDirection")
        g.correctDirection()
    if before & 32:
        checkpoint("addExtrema")
        g.addExtrema()
    g.round()
    # Integer TTF coordinates may reintroduce a tiny crossing; one bounded retry.
    if g.validate(True) & 4:
        checkpoint("retryRemoveOverlap")
        g.removeOverlap()
        g.correctDirection()
        g.round()
    g.width = advance
    record.update(after_validation=g.validate(True), after_bbox=g.boundingBox(),
                  after_points=sum(len(c) for c in g.foreground))
    checkpoint("done")
f.generate(str(out / "clean-generated.ttf"), flags=("no-hints",))
f.close()
# Validate the actual reloaded TTF, not just fractional in-memory curves.
f = fontforge.open(str(out / "clean-generated.ttf"))
for record in report:
    cp = int(record["codepoint"][2:], 16)
    record["saved_validation"] = f[cp].validate(True)
f.close()
(out / "cleanup-progress.json").write_text(json.dumps(report, indent=2) + "\n")
if any(r["saved_validation"] & 4 for r in report):
    sys.exit("Self-intersections remain after saving")
