"""Build the whole-font ttfautohint experiment without installation or Wine.

Run: python3 build-hints.py
The CLI/library are unpacked under runtime from Ubuntu Noble packages;
no system packages or user font configuration are modified.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "font-lab/candidate/tahomabd.ttf"
ORIGINAL = Path(os.environ["WINE_SOURCE"]) / "fonts/tahomabd.ttf"


def instructions(font):
    return {name: len(glyph.program.getBytecode())
            for name in font.getGlyphOrder()
            if hasattr((glyph := font["glyf"][name]), "program")
            and glyph.program.getBytecode()}


def table_info(font):
    return {tag: len(font[tag].compile(font)) if tag in font else 0
            for tag in ("cvt ", "fpgm", "prep")}


def contours(glyphset, name):
    pen = DecomposingRecordingPen(glyphset)
    glyphset[name].draw(pen)
    return pen.value


def main():
    generated = HERE / "ttfautohint-generated.ttf"
    output = HERE / "tahomabd-all-hints.ttf"
    command = [str(HERE / "runtime/usr/bin/ttfautohint"), "--detailed-info",
               str(SOURCE), str(generated)]
    environment = dict(os.environ,
                       LD_LIBRARY_PATH=str(HERE / "runtime/usr/lib/x86_64-linux-gnu"))
    subprocess.run(command, env=environment, check=True, timeout=60)
    source, original, hinted = TTFont(SOURCE), TTFont(ORIGINAL), TTFont(generated)
    hinted["head"].fontRevision = .003
    for name in hinted["name"].names:
        values = {3: "WineTahomaBold-Cyrillic-all-hints-3",
                  5: "Version 0.003; Cyrillic bold whole-font ttfautohint 1.8.4 experiment",
                  6: "WineTahomaBoldCyrillicAllHints"}
        if name.nameID in values:
            name.string = values[name.nameID].encode(name.getEncoding())
    hinted.recalcTimestamp = False
    hinted.save(output)
    result = TTFont(output)
    assert source.getGlyphOrder() == result.getGlyphOrder()
    assert source["hmtx"].metrics == result["hmtx"].metrics
    before, after = source.getGlyphSet(), result.getGlyphSet()
    assert all(contours(before, name) == contours(after, name) for name in source.getGlyphOrder())
    assert result["head"].fontRevision > source["head"].fontRevision
    affected = [int(code[2:], 16) for code in
                json.loads((SOURCE.parent / "affected.json").read_text())]
    programs = instructions(result)
    report = {
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "command": command, "revision": result["head"].fontRevision,
        "original_hinted_glyphs": len(instructions(original)),
        "source_hinted_glyphs": len(instructions(source)),
        "output_hinted_glyphs": len(programs),
        "affected_hinted_glyphs": sum(result.getBestCmap()[cp] in programs for cp in affected),
        "original_tables": table_info(original), "output_tables": table_info(result),
        "original_cvt": list(original["cvt "].values),
        "glyph_count": len(result.getGlyphOrder()), "all_decomposed_contours_exact": True,
        "all_hmtx_exact": True, "source_gasp": source["gasp"].gaspRange,
        "output_gasp": result["gasp"].gaspRange,
        "requires_real_GDI_check": True,
        "tradeoff": "Whole-font instructions and gasp change Latin and all other scripts too; default x-height boost applies up to 14 ppem."
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
