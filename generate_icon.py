"""
generate_icon.py - app_icon.ico 생성 (build.bat에서 자동 실행)
"""
import math, os, struct, zlib


def make_png():
    W = H = 64
    cx = cy = 32.0
    rows = []
    for y in range(H):
        row = bytearray([0])
        for x in range(W):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            R = 29.0
            if dist > R + 1.5:
                row += b'\x00\x00\x00\x00'
                continue
            t = min(dist / R, 1.0)
            rc = int(100 - t * 25)
            gc = int(180 - t * 40)
            bc = int(240 - t * 40)
            alpha = min(255, max(0, int(255 * (R + 1.5 - dist) / 1.5)))
            angle = math.degrees(math.atan2(-dy, dx))
            on_white = dist < 4.5
            if not on_white:
                for arc_r, arc_w in [(9.5, 2.2), (17.0, 2.2), (24.5, 2.2)]:
                    if abs(dist - arc_r) < arc_w and 25 <= angle <= 155:
                        on_white = True
                        break
            row += bytes([255, 255, 255, alpha] if on_white else [rc, gc, bc, alpha])
        rows.append(bytes(row))

    raw  = b''.join(rows)
    comp = zlib.compress(raw, 6)

    def chunk(name, data):
        body = name + data
        return (struct.pack('>I', len(data)) + body
                + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>II', W, H) + bytes([8, 6, 0, 0, 0]))
            + chunk(b'IDAT', comp)
            + chunk(b'IEND', b''))


def make_ico(png_data):
    header = struct.pack('<HHH', 0, 1, 1)
    entry  = struct.pack('<BBBBHHII', 64, 64, 0, 0, 1, 32, len(png_data), 6 + 16)
    return header + entry + png_data


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    with open(out, 'wb') as f:
        f.write(make_ico(make_png()))
    print(f"  Icon saved: {out}")
