"""Write a deterministic 16-bit RGB PNG (8x8 random blocks, like ps47) for the #47 zoom test."""
import random, struct, sys, zlib
w, h = int(sys.argv[2]), int(sys.argv[3])
rnd = random.Random(47)
blocks = [[(rnd.randrange(65536), x * 65535 // w, y * 65535 // h) for x in range(0, w, 8)] for y in range(0, h, 8)]
raw = b''.join(b'\0' + b''.join(struct.pack('>HHH', *blocks[y // 8][x // 8]) for x in range(w)) for y in range(h))
def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
open(sys.argv[1], 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 16, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
