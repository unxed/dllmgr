"""Generate public synthetic test images; no photos from the user's machine."""
from pathlib import Path
import struct

def write_bmp(path, width, height, color, border=None):
    padding = bytes(-width * 3 % 4)
    solid = bytes(color) * width + padding
    pixels = solid * height
    if border:
        edge = bytes(border)
        rim = edge * width + padding
        interior = edge * 4 + bytes(color) * (width - 8) + edge * 4 + padding
        pixels = rim * 4 + interior * (height - 8) + rim * 4
    header = b"BM" + struct.pack("<IHHI", 54 + len(pixels), 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    path.write_bytes(header + pixels)


folder = Path("images")
browser = folder / "browser"
preview = browser / "folder-preview"
preview.mkdir(parents=True, exist_ok=True)
write_bmp(folder / "white.bmp", 800, 600, (255, 255, 255))
write_bmp(preview / "portrait.bmp", 90, 160, (235, 195, 100), (50, 35, 160))
# WineHQ 59251 reproduces with a directory of at least 164 images.
for i in range(164):
    orientation = "portrait" if i % 2 else "landscape"
    width, height = (90, 160) if i % 2 else (160, 90)
    color = (90 + (i * 17) % 150, 205, 240 - (i * 11) % 140)
    name = "01-портрет.bmp" if i == 1 else f"{i:02d}-{orientation}.bmp"
    write_bmp(browser / name, width, height, color, (80, 45, 30))
