"""Bounded cleanup of affected glyphs, then whole-font ttfautohint; no Wine/UI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "font-lab/candidate/tahomabd.ttf"
ORIGINAL = Path(os.environ["WINE_SOURCE"]) / "fonts/tahomabd.ttf"
AFFECTED = SOURCE.parent / "affected.json"

def draw(font, name):
    glyphs = font.getGlyphSet()
    recording, area = DecomposingRecordingPen(glyphs), AreaPen(glyphs)
    glyphs[name].draw(recording)
    glyphs[name].draw(area)
    return recording.value, area.value


def main():
    start = time.monotonic()
    report = {"success": False, "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    try:
        with (HERE / "cleanup-fontforge.log").open("w") as log:
            subprocess.run(["fontforge", "-lang", "py", "-script", str(HERE / "cleanup-worker.py"),
                            str(SOURCE), str(ORIGINAL), str(AFFECTED), str(HERE)],
                           stdout=log, stderr=subprocess.STDOUT, timeout=120, check=True)
        checks = json.loads((HERE / "cleanup-progress.json").read_text())
        assert len(checks) == 66
        assert not any(r["saved_validation"] & 4 for r in checks)
        source, generated = TTFont(SOURCE), TTFont(HERE / "clean-generated.ttf")
        cmap = source.getBestCmap()
        names = {cmap[int(c[2:], 16)] for c in json.loads(AFFECTED.read_text())}
        for name in names:
            source["glyf"][name] = generated["glyf"][name]
            # Keep advance and bearing exactly; no centering or guessed shift.
        source.recalcTimestamp = False
        clean_path = HERE / "tahomabd-clean-unhinted.ttf"
        source.save(clean_path)
        clean, prior = TTFont(clean_path), TTFont(SOURCE)
        assert clean["hmtx"].metrics == prior["hmtx"].metrics
        untouched = set(prior.getGlyphOrder()) - names
        assert all(clean["glyf"][n].compile(clean["glyf"]) ==
                   prior["glyf"][n].compile(prior["glyf"]) for n in untouched)
        for row in checks:
            name = row["name"]
            _, before_area = draw(prior, name)
            _, after_area = draw(clean, name)
            row.update(before_area=before_area, after_area=after_area,
                       area_change_fraction=(abs(after_area)/abs(before_area)-1) if before_area else None)
        command = [str(HERE / "runtime/usr/bin/ttfautohint"), "--detailed-info",
                   str(clean_path), str(HERE / "clean-hinted-generated.ttf")]
        subprocess.run(command, env=dict(os.environ, LD_LIBRARY_PATH=str(HERE / "runtime/usr/lib/x86_64-linux-gnu")),
                       check=True, timeout=30)
        hinted = TTFont(HERE / "clean-hinted-generated.ttf")
        hinted["head"].fontRevision = .004
        for entry in hinted["name"].names:
            values = {3: "WineTahomaBold-Cyrillic-clean-hints-4",
                      5: "Version 0.004; Cyrillic bold cleaned contours and ttfautohint 1.8.4",
                      6: "WineTahomaBoldCyrillicCleanHints"}
            if entry.nameID in values:
                entry.string = values[entry.nameID].encode(entry.getEncoding())
        hinted.recalcTimestamp = False
        output = HERE / "tahomabd-clean-hints.ttf"
        hinted.save(output)
        final = TTFont(output)
        assert final["hmtx"].metrics == prior["hmtx"].metrics
        assert all(draw(clean,n)[0] == draw(final,n)[0] for n in clean.getGlyphOrder())
        hinted_names = {n for n in final.getGlyphOrder()
                        if hasattr((g := final["glyf"][n]),"program") and g.program.getBytecode()}
        report.update(success=True, output=str(output), sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                      revision=final["head"].fontRevision, affected=checks,
                      all_hmtx_exact=True, unchanged_glyf_exact=len(untouched),
                      hinted_glyphs=len(hinted_names), affected_hinted_glyphs=len(names & hinted_names),
                      final_vs_clean_contours_exact=True, requires_real_GDI_check=True)
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        report["elapsed_seconds"] = time.monotonic()-start
        (HERE / "cleanup-report.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({k:v for k,v in report.items() if k != "affected"},indent=2))

if __name__ == "__main__":
    main()
