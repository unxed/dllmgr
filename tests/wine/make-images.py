"""Generate public synthetic test images; no photos from the user's machine."""
from pathlib import Path
import struct

folder = Path("images")
folder.mkdir(exist_ok=True)
width, height = 800, 600
pixels = bytes([255, 255, 255]) * width * height
header = b"BM" + struct.pack("<IHHI", 54 + len(pixels), 0, 0, 54)
header += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
(folder / "white.bmp").write_bytes(header + pixels)
