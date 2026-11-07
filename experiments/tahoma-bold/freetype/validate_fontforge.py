import json
import sys
import fontforge

source_path, candidate_path, affected_path = sys.argv[1:]
codes = [int(value[2:], 16) for value in json.load(open(affected_path))]
source = fontforge.open(source_path)
candidate = fontforge.open(candidate_path)
failed = []
max_dy = 0.0
before_flags = {}
after_flags = {}
new_self = []
new_winding = []
flag_changes = []
for code in codes:
    old_glyph = source[code]
    new_glyph = candidate[code]
    old = old_glyph.boundingBox()
    new = new_glyph.boundingBox()
    old_flags = old_glyph.validate(True)
    new_flags = new_glyph.validate(True)
    before_flags[code] = old_flags
    after_flags[code] = new_flags
    if new_flags & 0x4 and not old_flags & 0x4:
        new_self.append(code)
    if new_flags & 0x8 and not old_flags & 0x8:
        new_winding.append(code)
    if old_flags != new_flags:
        flag_changes.append((code, old_flags, new_flags))
    dy = max(abs(old[1] - new[1]), abs(old[3] - new[3]))
    max_dy = max(max_dy, dy)
    if dy > 0.01:
        failed.append((f"U+{code:04X}", old, new))
print(f"FontForge checked {len(codes)} affected glyphs; vertical bbox mismatches >0.01 font unit={len(failed)}; max delta={max_dy:.6f}")
for item in failed:
    print(item)
for bit, label in ((0x4, "self-intersection"), (0x8, "wrong contour winding")):
    before_count = sum(bool(value & bit) for value in before_flags.values())
    after_count = sum(bool(value & bit) for value in after_flags.values())
    added = [f"U+{code:04X}" for code in (new_self if bit == 0x4 else new_winding)]
    print(f"FontForge {label} bit 0x{bit:02X}: before={before_count}, after={after_count}, newly flagged={len(added)} {', '.join(added) if added else '-'}")
for bit in (0x2, 0x10, 0x20, 0x40, 0x40000):
    before_count = sum(bool(value & bit) for value in before_flags.values())
    after_count = sum(bool(value & bit) for value in after_flags.values())
    if before_count or after_count:
        print(f"FontForge other validation bit 0x{bit:05X}: before={before_count}, after={after_count}")
for code, old_flags, new_flags in flag_changes:
    print(f"  U+{code:04X}: before=0x{old_flags:04X}, after=0x{new_flags:04X}")
source.close()
candidate.close()
raise SystemExit(bool(failed))
