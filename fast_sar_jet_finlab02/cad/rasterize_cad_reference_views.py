#!/usr/bin/env python3
"""
Zero-Dependency 3D OpenCASCADE STL + Parametric CAD Multi-Angle Rasterizer
for `arctic-fast-sar-jet` (`FIN-LAB-02` / `Variant H-Evo`, 14.95 kg Airborne MTOW).

Reads:
  - `cad/arctic_fast_sar_jet_iter1_fixed16deg.stl` (OpenCASCADE 3D Solid B-Rep Mesh)
  - `cad/design_params_sar.json` (Canonical SSOT Dimensions & Internal Stations)

Renders a high-resolution 4-Panel 3D/2D CAD Reference Sheet PNG (`cad_ssot_4angle_reference_raster_v1.png`)
using pure Python (`struct` + `zlib` Z-buffer triangle rasterizer, zero external dependencies) so that:
  1. Every AI visualization (`Figure 21`, `Figure 22`, `Figure 23`, `Plate 28`, etc.) receives the exact
     rasterized 3D CAD views as an input image prompt, AND
  2. Every generated illustration can be compared side-by-side against the true 3D CAD geometry from
     that exact angle.
"""

import json
import math
import os
import struct
import zlib

CAD_DIR = os.path.dirname(os.path.abspath(__file__))
STL_PATH = os.path.join(CAD_DIR, "arctic_fast_sar_jet_iter1_fixed16deg.stl")
PARAMS_PATH = os.path.join(CAD_DIR, "design_params_sar.json")
OUT_DOCS_PNG = os.path.join(os.path.dirname(CAD_DIR), "docs", "images", "cad_ssot_4angle_reference_raster_v2.jpg")


def load_binary_stl(path: str):
    """Load triangles [(n, v0, v1, v2), ...] from binary STL."""
    triangles = []
    with open(path, "rb") as f:
        _header = f.read(80)
        count_bytes = f.read(4)
        if len(count_bytes) < 4:
            return triangles
        num_tris = struct.unpack("<I", count_bytes)[0]
        for _ in range(num_tris):
            data = f.read(50)
            if len(data) < 50:
                break
            vals = struct.unpack("<12fH", data)
            n = (vals[0], vals[1], vals[2])
            v0 = (vals[3], vals[4], vals[5])
            v1 = (vals[6], vals[7], vals[8])
            v2 = (vals[9], vals[10], vals[11])
            triangles.append((n, v0, v1, v2))
    return triangles


class CanvasRGB:
    def __init__(self, width: int, height: int, bg=(8, 18, 33)):
        self.w = width
        self.h = height
        self.buf = bytearray(bg * (width * height))
        self.zbuf = [float("-inf")] * (width * height)

    def set_px(self, x: int, y: int, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            idx = (y * self.w + x) * 3
            self.buf[idx] = color[0]
            self.buf[idx + 1] = color[1]
            self.buf[idx + 2] = color[2]

    def draw_rect(self, x0: int, y0: int, x1: int, y1: int, fill=None, outline=None):
        xa, xb = max(0, min(x0, x1)), min(self.w - 1, max(x0, x1))
        ya, yb = max(0, min(y0, y1)), min(self.h - 1, max(y0, y1))
        if fill:
            row_bytes = bytes(fill) * (xb - xa + 1)
            for y in range(ya, yb + 1):
                start = (y * self.w + xa) * 3
                self.buf[start : start + len(row_bytes)] = row_bytes
        if outline:
            for x in range(xa, xb + 1):
                self.set_px(x, ya, outline)
                self.set_px(x, yb, outline)
            for y in range(ya, yb + 1):
                self.set_px(xa, y, outline)
                self.set_px(xb, y, outline)

    def draw_line(self, x0: float, y0: float, x1: float, y1: float, color, thickness: int = 1):
        ix0, iy0, ix1, iy1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(ix1 - ix0)
        dy = -abs(iy1 - iy0)
        sx = 1 if ix0 < ix1 else -1
        sy = 1 if iy0 < iy1 else -1
        err = dx + dy
        while True:
            if thickness <= 1:
                self.set_px(ix0, iy0, color)
            else:
                r = thickness // 2
                for oy in range(-r, r + 1):
                    for ox in range(-r, r + 1):
                        self.set_px(ix0 + ox, iy0 + oy, color)
            if ix0 == ix1 and iy0 == iy1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                ix0 += sx
            if e2 <= dx:
                err += dx
                iy0 += sy

    def fill_triangle_z(self, p0, p1, p2, color):
        """Rasterize 2D projected triangle with Z-buffer."""
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        x2, y2, z2 = p2
        min_x = max(0, int(math.floor(min(x0, x1, x2))))
        max_x = min(self.w - 1, int(math.ceil(max(x0, x1, x2))))
        min_y = max(0, int(math.floor(min(y0, y1, y2))))
        max_y = min(self.h - 1, int(math.ceil(max(y0, y1, y2))))
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-6:
            return
        inv_d = 1.0 / denom
        c0, c1, c2 = color
        for py in range(min_y, max_y + 1):
            yc = py + 0.5
            row_off = py * self.w
            for px in range(min_x, max_x + 1):
                xc = px + 0.5
                w0 = ((y1 - y2) * (xc - x2) + (x2 - x1) * (yc - y2)) * inv_d
                if w0 < 0.0:
                    continue
                w1 = ((y2 - y0) * (xc - x2) + (x0 - x2) * (yc - y2)) * inv_d
                if w1 < 0.0:
                    continue
                w2 = 1.0 - w0 - w1
                if w2 < 0.0:
                    continue
                z = w0 * z0 + w1 * z1 + w2 * z2
                idx = row_off + px
                if z > self.zbuf[idx]:
                    self.zbuf[idx] = z
                    b_idx = idx * 3
                    self.buf[b_idx] = c0
                    self.buf[b_idx + 1] = c1
                    self.buf[b_idx + 2] = c2

    def save_png(self, path: str):
        raw_rows = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw_rows.append(0)  # Filter type 0 (None)
            start = y * stride
            raw_rows.extend(self.buf[start : start + stride])

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            )

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        idat = zlib.compress(bytes(raw_rows), level=6)
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(png)


def render_mesh_view(canvas: CanvasRGB, tris, rect, yaw_deg: float, pitch_deg: float, scale: float, tint_mode="ORANGE"):
    """Project and Z-buffer shade the OpenCASCADE STL triangles into `rect = (rx0, ry0, rx1, ry1)`."""
    rx0, ry0, rx1, ry1 = rect
    cx = (rx0 + rx1) * 0.5
    cy = (ry0 + ry1) * 0.5
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    cpit, spit = math.cos(pitch), math.sin(pitch)

    # Center of aircraft mesh around X=720 mm, Y=0, Z=0
    x_center = 720.0
    light_dir = (0.35, -0.45, 0.82)

    def proj(v):
        dx = v[0] - x_center
        dy = v[1]
        dz = v[2]
        # Rotate by yaw around Z
        x1 = dx * cyaw - dy * syaw
        y1 = dx * syaw + dy * cyaw
        z1 = dz
        # Rotate by pitch around Y
        x2 = x1 * cpit + z1 * spit
        y2 = y1
        z2 = -x1 * spit + z1 * cpit
        sx = cx + y2 * scale
        sy = cy - z2 * scale
        return (sx, sy, x2)

    for n, v0, v1, v2 in tris:
        p0 = proj(v0)
        p1 = proj(v1)
        p2 = proj(v2)
        # Compute normal for shading
        ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        nlen = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-9
        nx, ny, nz = nx / nlen, ny / nlen, nz / nlen
        diff = abs(nx * light_dir[0] + ny * light_dir[1] + nz * light_dir[2])
        shade = 0.32 + 0.68 * diff

        # Color by sub-component coordinate (Propeller, Engine, Booms, Tail, Wing/Fuselage)
        xm = (v0[0] + v1[0] + v2[0]) / 3.0
        ym = abs(v0[1] + v1[1] + v2[1]) / 3.0
        zm = (v0[2] + v1[2] + v2[2]) / 3.0

        if xm < 25.0:
            # 355 mm Nose Folding Propeller & Spinner (Cyan-Silver)
            base_c = (80, 220, 255)
        elif 700.0 <= xm <= 1220.0 and ym < 95.0 and zm > 35.0:
            # Dorsal JetCat P100-RX-BL Turbojet & 304SS/Aerogel Thermal Deck (Metallic Gold/Steel)
            base_c = (230, 195, 110)
        elif xm > 1280.0 and zm > 18.0:
            # Connected 110-deg Inverted Lambda-Tail Arch (High-Contrast Cyan/Orange Highlight)
            base_c = (0, 225, 255) if tint_mode == "BLUEPRINT" else (255, 145, 35)
        elif 185.0 <= ym <= 265.0 and xm > 650.0 and zm < 35.0:
            # Twin 16mm Carbon Tail Booms at Y = +/-230 mm
            base_c = (95, 130, 165)
        elif zm < -55.0:
            # Detachable 3-Wheel Tundra Drop-Dolly
            base_c = (160, 180, 200)
        else:
            # RAL 2005 Fluorescent SAR Orange Wing & Blended Strake Center-Body
            base_c = (35, 175, 245) if tint_mode == "BLUEPRINT" else (255, 102, 18)

        c = (
            min(255, int(base_c[0] * shade)),
            min(255, int(base_c[1] * shade)),
            min(255, int(base_c[2] * shade)),
        )
        canvas.fill_triangle_z(p0, p1, p2, c)


def main():
    tris = load_binary_stl(STL_PATH)
    W, H = 1920, 1200
    cv = CanvasRGB(W, H, bg=(7, 16, 30))

    # Draw 4 quadrant panels
    panels = [
        (20, 20, 945, 580),     # Panel 1: 3D Front-Left Isometric (matches Fig 22 & Plate 28)
        (975, 20, 1900, 580),   # Panel 2: 3D Aft-Right Isometric (shows Connected 110-deg Inverted Lambda-Tail Arch)
        (20, 600, 945, 1180),   # Panel 3: Top Orthographic Planform (matches Fig 23 Planview)
        (975, 600, 1900, 1180), # Panel 4: Left Side Orthographic Profile + Internal Cutaway Stations (matches Fig 21)
    ]
    for p in panels:
        cv.draw_rect(p[0], p[1], p[2], p[3], fill=(11, 24, 44), outline=(0, 212, 255))

    # Panel 1: Front-Left 3D Isometric (Orange SAR Livery)
    render_mesh_view(cv, tris, panels[0], yaw_deg=-132.0, pitch_deg=26.0, scale=0.36, tint_mode="ORANGE")

    # Panel 2: Aft-Right 3D Isometric (Blueprint Cyan/Orange showing 110-deg Inverted Lambda-Tail Arch)
    render_mesh_view(cv, tris, panels[1], yaw_deg=-42.0, pitch_deg=24.0, scale=0.36, tint_mode="BLUEPRINT")

    # Panel 3: Top-Down Orthographic Planform (Nose Up, Tail Down)
    render_mesh_view(cv, tris, panels[2], yaw_deg=-90.0, pitch_deg=89.9, scale=0.24, tint_mode="ORANGE")

    # Panel 4: Left-Side Orthographic Profile (Yaw=+90 -> Nose on LEFT at X=0, Tail on RIGHT at X=1540)
    render_mesh_view(cv, tris, panels[3], yaw_deg=90.0, pitch_deg=0.0, scale=0.46, tint_mode="BLUEPRINT")

    # Overlay internal CAD stations on Panel 4 (Left Side Profile: X_center=720 -> sx = cx + (x - 720)*scale, sy = cy - z*scale)
    rx0, ry0, rx1, ry1 = panels[3]
    cx = (rx0 + rx1) * 0.5
    cy = (ry0 + ry1) * 0.5
    sc = 0.46

    def sx_sy(x_mm, z_mm):
        return int(round(cx + (x_mm - 720.0) * sc)), int(round(cy - z_mm * sc))

    # Draw CG vertical datum line at X_CG = 595.0 mm (Green) and Neutral Point X_NP = 636.0 mm (Amber)
    cg_x, _ = sx_sy(595.0, 0)
    np_x, _ = sx_sy(636.0, 0)
    cv.draw_line(cg_x, ry0 + 40, cg_x, ry1 - 40, (24, 224, 127), thickness=2)
    cv.draw_line(np_x, ry0 + 40, np_x, ry1 - 40, (255, 190, 46), thickness=2)

    # Draw internal boxes on Side Profile:
    # 1. 6S2P Battery (X=292..437, Z=-34..+10)
    x0, y0 = sx_sy(292, 10)
    x1, y1 = sx_sy(437, -34)
    cv.draw_rect(x0, y0, x1, y1, fill=(20, 120, 220), outline=(255, 255, 255))
    # 2. UAT 150mL Spherical Hopper (X=381..449, Z=-16..+52)
    x0, y0 = sx_sy(381, 52)
    x1, y1 = sx_sy(449, -16)
    cv.draw_rect(x0, y0, x1, y1, fill=(0, 216, 255), outline=(255, 255, 255))
    # 3. Twin 2.0L PET Fuel Tanks at X_CG=595mm (X=440..750, Z=-25..+55)
    x0, y0 = sx_sy(440, 55)
    x1, y1 = sx_sy(750, -25)
    cv.draw_rect(x0, y0, x1, y1, fill=(24, 200, 125), outline=(255, 255, 255))
    # 4. Ventral 420x180x145mm Capsule/Quad Bay at X_CG=595mm (X=445..865, Z=-95..-28)
    x0, y0 = sx_sy(445, -28)
    x1, y1 = sx_sy(865, -95)
    cv.draw_rect(x0, y0, x1, y1, fill=(255, 115, 25), outline=(255, 255, 255))
    # 5. Dorsal JetCat P100-RX-BL Turbojet (X=710..975, Z=+30..+126)
    x0, y0 = sx_sy(710, 126)
    x1, y1 = sx_sy(975, 30)
    cv.draw_rect(x0, y0, x1, y1, fill=(255, 75, 75), outline=(255, 255, 255))

    cv.save_png(OUT_DOCS_PNG)
    print(f"Saved 4-angle OpenCASCADE STL raster reference to:\n  {OUT_DOCS_PNG}")


if __name__ == "__main__":
    main()
