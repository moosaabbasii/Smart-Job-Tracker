"""Run this once to generate the extension icons: py generate_icons.py"""
import struct, zlib, os

def make_png(size, bg=(13,13,26), accent=(74,144,217)):
    """Generate a simple PNG icon with a briefcase emoji-style design."""
    pixels = []
    cx, cy = size // 2, size // 2
    r_outer = int(size * 0.42)
    r_inner = int(size * 0.28)

    for y in range(size):
        row = []
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx*dx + dy*dy) ** 0.5

            # Outer circle (accent color)
            if dist <= r_outer:
                # Handle strap (top rectangle)
                strap_w = size * 0.22
                strap_h = size * 0.12
                strap_y_top = cy - r_outer * 0.55
                strap_y_bot = strap_y_top + strap_h
                in_strap = (
                    abs(dx) < strap_w / 2 and
                    strap_y_top <= y <= strap_y_bot
                )
                if in_strap:
                    # Strap cutout
                    row += [bg[0], bg[1], bg[2], 255]
                else:
                    t = max(0, (r_outer - dist) / (r_outer * 0.15))
                    t = min(1, t)
                    br = int(accent[0] * t + bg[0] * (1-t))
                    bg2 = int(accent[1] * t + bg[1] * (1-t))
                    bb = int(accent[2] * t + bg[2] * (1-t))
                    row += [br, bg2, bb, 255]
            else:
                row += [bg[0], bg[1], bg[2], 0]
        pixels.append(row)

    # Build PNG bytes
    def pack_chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)

    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    raw  = b''
    for row in pixels:
        raw += b'\x00' + bytes(row)
    idat = zlib.compress(raw)

    return (
        b'\x89PNG\r\n\x1a\n' +
        pack_chunk(b'IHDR', ihdr) +
        pack_chunk(b'IDAT', idat) +
        pack_chunk(b'IEND', b'')
    )

os.makedirs("icons", exist_ok=True)
for size in [16, 48, 128]:
    with open(f"icons/icon{size}.png", "wb") as f:
        f.write(make_png(size))
    print(f"Generated icons/icon{size}.png")

print("Done!")
