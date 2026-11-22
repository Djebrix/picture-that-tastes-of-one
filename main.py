#!/usr/bin/env python3
"""One Perfect Apple — a single glossy red apple, drawn pixel by pixel.

Pure Python 3.13 standard library: no randomness, no time, no network.
Writes /output/entry.png (1024x1024 PNG, deterministic: two runs are
byte-identical). One ingredient, one picture, judged on how delicious it
looks.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
OUT = "/output/entry.png"


def clamp(v, lo=0.0, hi=1.0):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3.0 - 2.0 * t)


def mix3(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def write_png(path, w, h, buf):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def draw():
    buf = bytearray(W * H * 3)

    top = (253, 240, 213)      # warm cream
    mid = (243, 217, 164)      # honey at the horizon
    bottom = (224, 180, 118)   # wooden table
    horizon = 0.68

    # --- background: vertical gradient + soft vignette + warm glow ---
    for y in range(H):
        t = y / H
        if t < horizon:
            base = mix3(top, mid, t / horizon)
        else:
            base = mix3(mid, bottom, (t - horizon) / (1.0 - horizon))
        dy = (y - 512.0) / 512.0
        row = y * W * 3
        for x in range(W):
            dx = (x - 512.0) / 512.0
            d2 = dx * dx + dy * dy
            vig = 1.0 - 0.10 * d2
            # warm glow behind the apple
            gd = math.sqrt((x - 512.0) ** 2 + (y - 560.0) ** 2)
            glow = 0.16 * (1.0 - smoothstep(180.0, 430.0, gd))
            r = int(base[0] * vig + (255 - base[0] * vig) * glow * 0.4)
            g = int(base[1] * vig + (228 - base[1] * vig) * glow * 0.4)
            b = int(base[2] * vig + (170 - base[2] * vig) * glow * 0.4)
            i = row + x * 3
            buf[i] = r if r < 255 else 255
            buf[i + 1] = g if g < 255 else 255
            buf[i + 2] = b if b < 255 else 255

    def blend(x, y, r, g, b, a):
        if a <= 0.0 or x < 0 or x >= W or y < 0 or y >= H:
            return
        i = (y * W + x) * 3
        ia = 1.0 - a
        buf[i] = int(buf[i] * ia + r * a)
        buf[i + 1] = int(buf[i + 1] * ia + g * a)
        buf[i + 2] = int(buf[i + 2] * ia + b * a)

    def disc(cx, cy, rad, r, g, b, a):
        x0 = max(0, int(cx - rad) - 1)
        x1 = min(W - 1, int(cx + rad) + 1)
        y0 = max(0, int(cy - rad) - 1)
        y1 = min(H - 1, int(cy + rad) + 1)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                d = math.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rad
                if d < 1.0:
                    blend(xx, yy, r, g, b, a * (1.0 - smoothstep(0.75, 1.0, d)))

    # --- soft shadow on the table ---
    for yy in range(830, 960):
        for xx in range(150, 875):
            ex = (xx - 512.0) / 335.0
            ey = (yy - 895.0) / 58.0
            d = ex * ex + ey * ey
            if d < 1.0:
                blend(xx, yy, 90, 55, 25, 0.34 * (1.0 - smoothstep(0.4, 1.0, d)))

    # warm bounce light on the table beneath the apple
    disc(512, 912, 170, 214, 110, 58, 0.12)
    disc(512, 905, 110, 226, 128, 66, 0.10)

    # --- apple body ---
    acx, acy, arx, ary = 512.0, 580.0, 322.0, 302.0
    bright = (232, 62, 52)
    deep = (138, 18, 18)
    light = (255, 122, 108)
    for yy in range(268, 892):
        ny = (yy - acy) / ary
        row = yy * W * 3
        for xx in range(180, 845):
            nx = (xx - acx) / arx
            d = math.sqrt(nx * nx + ny * ny)
            if d >= 1.0:
                continue
            alpha = clamp((1.0 - d) * 160.0)
            # light comes from the upper left
            lt = clamp(0.5 - 0.5 * (nx * 0.62 + ny * 0.78))
            col = mix3(deep, bright, lt)
            col = mix3(col, light, smoothstep(0.62, 1.0, lt) * 0.55)
            # organic blush variation
            v = 0.5 + 0.5 * math.sin(xx * 0.021 + 1.7) * math.sin(yy * 0.016 + 0.4)
            col = mix3(col, deep, v * 0.22 * smoothstep(0.2, 0.9, 1.0 - lt))
            # rich crimson on the shadow side
            col = mix3(col, (104, 8, 12), smoothstep(0.55, 1.0, 1.0 - lt) * 0.35)
            # darken toward the bottom
            col = mix3(col, deep, smoothstep(0.35, 1.0, ny) * 0.30)
            i = row + xx * 3
            buf[i] = int(buf[i] * (1.0 - alpha) + col[0] * alpha)
            buf[i + 1] = int(buf[i + 1] * (1.0 - alpha) + col[1] * alpha)
            buf[i + 2] = int(buf[i + 2] * (1.0 - alpha) + col[2] * alpha)

    # --- top dimple ---
    disc(512, 292, 46, 120, 20, 16, 0.45)
    disc(512, 296, 26, 96, 16, 14, 0.5)

    # --- leaf (drawn before the stem so the stem overlaps it) ---
    lcx, lcy = 632.0, 238.0
    ang = math.radians(-28.0)
    ca, sa = math.cos(ang), math.sin(ang)
    for yy in range(180, 300):
        for xx in range(520, 745):
            dx, dy = xx - lcx, yy - lcy
            rx = dx * ca + dy * sa
            ry = -dx * sa + dy * ca
            d = math.sqrt((rx / 102.0) ** 2 + (ry / 40.0) ** 2)
            if d >= 1.0:
                continue
            alpha = clamp((1.0 - d) * 60.0)
            lt = clamp(0.5 - 0.5 * (rx / 102.0 * 0.6 + ry / 40.0 * 0.8))
            col = mix3((24, 88, 30), (104, 188, 106), lt)
            i = (yy * W + xx) * 3
            buf[i] = int(buf[i] * (1.0 - alpha) + col[0] * alpha)
            buf[i + 1] = int(buf[i + 1] * (1.0 - alpha) + col[1] * alpha)
            buf[i + 2] = int(buf[i + 2] * (1.0 - alpha) + col[2] * alpha)
    # leaf vein: thin bright central vein with short side veins
    for s in range(-88, 89):
        vx = int(lcx + s * ca)
        vy = int(lcy - s * sa)
        disc(vx, vy, 2, 192, 236, 192, 0.9)
    for s in range(-72, 73, 12):
        bx = int(lcx + s * ca)
        by = int(lcy - s * sa)
        for q in range(1, 10):
            disc(int(bx + q * 1.6 * sa), int(by + q * 1.6 * ca), 1, 178, 224, 178, 0.7)
            disc(int(bx - q * 1.6 * sa), int(by - q * 1.6 * ca), 1, 178, 224, 178, 0.7)

    # --- stem: tapered quadratic curve ---
    p0 = (512.0, 302.0)
    p1 = (498.0, 246.0)
    p2 = (532.0, 196.0)
    for k in range(41):
        t = k / 40.0
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        rad = lerp(15.0, 6.5, t)
        col = mix3((110, 76, 64), (74, 50, 44), t)
        disc(x, y, rad, col[0], col[1], col[2], 0.96)

    # --- glossy highlights ---
    def gloss(cx, cy, rx, ry, angle_deg, peak):
        ang = math.radians(angle_deg)
        ca, sa = math.cos(ang), math.sin(ang)
        x0 = max(0, int(cx - rx) - 2)
        x1 = min(W - 1, int(cx + rx) + 2)
        y0 = max(0, int(cy - ry) - 2)
        y1 = min(H - 1, int(cy + ry) + 2)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                dx, dy = xx - cx, yy - cy
                qx = dx * ca + dy * sa
                qy = -dx * sa + dy * ca
                d = math.sqrt((qx / rx) ** 2 + (qy / ry) ** 2)
                if d < 1.0:
                    blend(xx, yy, 255, 255, 255,
                          peak * (1.0 - smoothstep(0.45, 1.0, d)))

    gloss(408, 432, 122, 74, -25, 0.68)
    gloss(362, 522, 56, 36, -20, 0.34)
    # small intense specular dot inside the main gloss
    gloss(378, 402, 34, 20, -25, 0.78)

    # warm rim light along the lower-right edge of the apple
    for k in range(31):
        ang = math.radians(8.0 + k * 2.2)
        ex = acx + math.cos(ang) * (arx - 7.0)
        ey = acy + math.sin(ang) * (ary - 7.0)
        disc(ex, ey, 7, 255, 178, 118, 0.30)

    return buf


def main():
    buf = draw()
    write_png(OUT, W, H, buf)
    size = os.path.getsize(OUT)
    print(f"wrote {OUT}: {W}x{H}, {size} bytes")


if __name__ == "__main__":
    main()
