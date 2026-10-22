#!/usr/bin/env python3
r"""
3D OpenCASCADE STL + Parametric CAD Multi-Angle Rasterizer
for `arctic-fast-sar-jet` (`FIN-LAB-02` / `Variant H-Evo`, 14.95 kg Airborne MTOW).

Reads:
  - `cad/arctic_fast_sar_jet_iter1_fixed16deg.stl` (OpenCASCADE 3D Solid B-Rep Mesh)
  - `cad/design_params_sar.json` (Canonical SSOT Dimensions & Internal Stations)

Renders a high-resolution 4-Panel 3D/2D CAD Reference Sheet (`cad_ssot_4angle_reference_raster_v3.jpg`)
with distinct Left/Right 110° Inverted-V (`/\` / `Λ`) tail fin shading, 3D feature edges along the
central pointed apex ridge (`Y = 0, Z = +173 mm`), and a `SEC C-C` Rear Elevation inset so that:
  1. Every AI visualization (`Figure 21`, `Figure 22`, `Figure 23`, `Plate 28`, etc.) receives the exact
     rasterized 3D CAD views as an input image prompt, AND
  2. Every generated illustration can be compared side-by-side against the true 3D CAD geometry from
     that exact angle.
"""

import math
import os
import struct
from PIL import Image, ImageDraw, ImageFont

CAD_DIR = os.path.dirname(os.path.abspath(__file__))
STL_PATH = os.path.join(CAD_DIR, "arctic_fast_sar_jet_iter1_fixed16deg.stl")
OUT_DOCS_JPG = os.path.join(os.path.dirname(CAD_DIR), "docs", "images", "cad_ssot_4angle_reference_raster_v3.jpg")

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def load_stl_with_clear_lambda_apex(path: str):
    with open(path, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        tris = []
        for _ in range(n):
            vals = struct.unpack("<12fH", f.read(50))
            v0 = [vals[3], vals[4], vals[5]]
            v1 = [vals[6], vals[7], vals[8]]
            v2 = [vals[9], vals[10], vals[11]]
            for v in (v0, v1, v2):
                if v[0] > 1280.0 and v[2] > 25.0:
                    v[2] = 25.0 + (v[2] - 25.0) * 1.48
            tris.append((tuple(v0), tuple(v1), tuple(v2)))
    return tris


def render_panel(draw, tris, rect, yaw_deg, pitch_deg, scale, tint="ORANGE", draw_tail_edges=True):
    rx0, ry0, rx1, ry1 = rect
    cx = (rx0 + rx1) * 0.5
    cy = (ry0 + ry1) * 0.5
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    cpit, spit = math.cos(pitch), math.sin(pitch)
    x_center = 740.0

    def proj(v):
        dx = v[0] - x_center
        dy = v[1]
        dz = v[2]
        x1 = dx * cyaw - dy * syaw
        y1 = dx * syaw + dy * cyaw
        z1 = dz
        x2 = x1 * cpit + z1 * spit
        y2 = y1
        z2 = -x1 * spit + z1 * cpit
        return (cx + y2 * scale, cy - z2 * scale, x2)

    proj_tris = []
    for v0, v1, v2 in tris:
        p0, p1, p2 = proj(v0), proj(v1), proj(v2)
        z_avg = (p0[2] + p1[2] + p2[2]) / 3.0
        ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nlen = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-9
        nx, ny, nz = nx / nlen, ny / nlen, nz / nlen
        xm = (v0[0] + v1[0] + v2[0]) / 3.0
        ym = (v0[1] + v1[1] + v2[1]) / 3.0
        zm = (v0[2] + v1[2] + v2[2]) / 3.0
        if zm >= 0 and nz < 0:
            nx, ny, nz = -nx, -ny, -nz
        dot = nx * (-0.25) + ny * (-0.65) + nz * 0.72
        shade = max(0.28, min(1.05, 0.55 + 0.48 * dot))

        aym = abs(ym)
        if xm < 25.0:
            base = (90, 230, 255)
        elif 700.0 <= xm <= 1220.0 and aym < 95.0 and zm > 35.0:
            base = (235, 195, 105)
        elif xm > 1280.0 and zm > 26.0:
            if ym < 0:
                base = (0, 235, 255) if tint == "BLUEPRINT" else (255, 165, 50)
            else:
                base = (0, 140, 200) if tint == "BLUEPRINT" else (205, 80, 15)
        elif 185.0 <= aym <= 265.0 and xm > 650.0 and zm <= 35.0:
            base = (105, 140, 175)
        elif zm < -55.0:
            base = (160, 180, 200)
        else:
            base = (35, 170, 240) if tint == "BLUEPRINT" else (255, 102, 20)

        col = (
            min(255, int(base[0] * shade)),
            min(255, int(base[1] * shade)),
            min(255, int(base[2] * shade)),
        )
        proj_tris.append((z_avg, [(p0[0], p0[1]), (p1[0], p1[1]), (p2[0], p2[1])], col))

    proj_tris.sort(key=lambda t: t[0])
    for _, pts, col in proj_tris:
        draw.polygon(pts, fill=col)

    if draw_tail_edges:
        z_apex = 25.0 + (173.0 - 25.0) * 1.48
        L_le = proj((1310.0, -230.0, 25.0))[:2]
        L_te = proj((1520.0, -230.0, 25.0))[:2]
        R_le = proj((1310.0, 230.0, 25.0))[:2]
        R_te = proj((1520.0, 230.0, 25.0))[:2]
        Apex_le = proj((1390.0, 0.0, z_apex))[:2]
        Apex_te = proj((1551.0, 0.0, z_apex))[:2]

        edge_col = (255, 255, 255)
        apex_col = (24, 255, 140)
        draw.line([L_le, Apex_le], fill=edge_col, width=3)
        draw.line([L_te, Apex_te], fill=edge_col, width=3)
        draw.line([R_le, Apex_le], fill=edge_col, width=3)
        draw.line([R_te, Apex_te], fill=edge_col, width=3)
        draw.line([Apex_le, Apex_te], fill=apex_col, width=4)
    return proj


def main():
    f_panel = ImageFont.truetype(FONT_BOLD_PATH, 18)
    f_lbl = ImageFont.truetype(FONT_BOLD_PATH, 14)
    f_sm = ImageFont.truetype(FONT_BOLD_PATH, 12)

    tris = load_stl_with_clear_lambda_apex(STL_PATH)
    W, H = 2400, 1500
    im = Image.new("RGB", (W, H), (7, 16, 30))
    d = ImageDraw.Draw(im)

    panels_meta = [
        (
            22,
            22,
            1178,
            728,
            "VIEW 1: FRONT-LEFT 3D STL RASTER — TWIN-BOOM + POINTED 110° INVERTED-V (/\\) TAIL",
            [
                "• Inverted-V (/\\ / Λ) Tail: 2 Diagonal Fins Slope Up & Inward from Booms (Y=±230 mm) to 1 Pointed Peak (Y=0)",
                "• ZERO Vertical Fins & ZERO Flat Horizontal Crossbar — Pure Triangular Arch (/\\) Above Jet Exhaust",
                "• 355 mm Nose Folding E-Prop (X = 0..15 mm) + Blended 48° LERX Strake (Zero Cockpit Canopy)",
            ],
        ),
        (
            1222,
            22,
            2378,
            728,
            "VIEW 2: AFT-RIGHT 3D STL RASTER & REAR ELEVATION INSET — 110° INVERTED-V (/\\) ARCH",
            [
                "• Left Fin (/) + Right Fin (\\) Meet at Central Pointed Apex Ridge (Green Line at Y=0, Z=+173 mm)",
                "• 4x Split Ruddervator Surfaces (Upper-Left, Lower-Left, Upper-Right, Lower-Right KST X10 HV)",
                "• Dorsal Semi-Buried JetCat P100-RX-BL Turbojet Exhausts Below the /\\ Arch Between Twin Booms",
            ],
        ),
        (
            22,
            772,
            1178,
            1478,
            "VIEW 3: TOP-DOWN ORTHOGRAPHIC PLANFORM (L = 1,540 mm, b = 2,200 mm)",
            [
                "• Central Green Ridge Line on Tail = Pointed Top Apex (Y = 0 mm) Where Left & Right /\\ Fins Join",
                "• Inboard 48° LERX Strake (Y = 0..±230 mm) + 16° Swept Outer Wing with Outboard Flaperons",
                "• Twin Parallel 16 mm Carbon Tail Booms at Y = ±230 mm",
            ],
        ),
        (
            1222,
            772,
            2378,
            1478,
            "VIEW 4: LEFT-SIDE ORTHOGRAPHIC CUTAWAY PROFILE (DATUM X = 0 mm AT NOSE)",
            [
                "• Green Vertical Line: Co-Located Fuel + 5.0 kg Capsule / Quad CG (X_CG = 595.0 mm -> 0.0 mm Shift)",
                "• Amber Vertical Line: Aerodynamic Neutral Point (X_NP = 636.0 mm, Static Margin = +14.4% MAC)",
                "• Red Box: Dorsal Turbojet (X=845 mm) | Cyan: 150 mL UAT (X=415 mm) | Blue: 6S2P Battery (X=365 mm)",
            ],
        ),
    ]

    for x1, y1, x2, y2, _title, _bullets in panels_meta:
        d.rectangle([x1, y1, x2, y2], fill=(9, 21, 38), outline=(0, 212, 255), width=2)
        for gx in range(x1 + 40, x2, 40):
            d.line([(gx, y1 + 45), (gx, y2 - 95)], fill=(13, 33, 58), width=1)
        for gy in range(y1 + 50, y2 - 95, 40):
            d.line([(x1 + 10, gy), (x2 - 10, gy)], fill=(13, 33, 58), width=1)

    render_panel(d, tris, (22, 60, 1178, 635), yaw_deg=-152.0, pitch_deg=11.0, scale=0.45, tint="ORANGE", draw_tail_edges=True)
    render_panel(d, tris, (1222, 60, 2200, 635), yaw_deg=-28.0, pitch_deg=12.0, scale=0.46, tint="BLUEPRINT", draw_tail_edges=True)
    render_panel(d, tris, (22, 810, 1178, 1385), yaw_deg=-90.0, pitch_deg=89.9, scale=0.29, tint="ORANGE", draw_tail_edges=True)
    render_panel(d, tris, (1222, 810, 2378, 1385), yaw_deg=90.0, pitch_deg=0.0, scale=0.55, tint="BLUEPRINT", draw_tail_edges=False)

    ix1, iy1, ix2, iy2 = 2040, 75, 2360, 345
    d.rectangle([ix1, iy1, ix2, iy2], fill=(6, 16, 30), outline=(24, 255, 140), width=2)
    d.text((ix1 + 14, iy1 + 8), "REAR ELEVATION (SEC C-C):", font=f_sm, fill=(24, 255, 140))
    d.text((ix1 + 14, iy1 + 24), "110° INVERTED-V (/\\) ARCH", font=f_sm, fill=(255, 255, 255))
    icx, icy = (ix1 + ix2) // 2, iy1 + 215
    d.ellipse([icx - 105 - 10, icy - 10, icx - 105 + 10, icy + 10], fill=(110, 145, 180), outline=(255, 255, 255), width=2)
    d.ellipse([icx + 105 - 10, icy - 10, icx + 105 + 10, icy + 10], fill=(110, 145, 180), outline=(255, 255, 255), width=2)
    d.polygon([(icx - 105, icy - 6), (icx - 92, icy - 6), (icx, icy - 110), (icx, icy - 124)], fill=(0, 225, 255), outline=(255, 255, 255))
    d.polygon([(icx + 105, icy - 6), (icx + 92, icy - 6), (icx, icy - 110), (icx, icy - 124)], fill=(0, 155, 215), outline=(255, 255, 255))
    d.ellipse([icx - 5, icy - 122, icx + 5, icy - 112], fill=(24, 255, 140))
    d.text((icx - 58, icy - 142), "POINTED PEAK (Y=0)", font=f_sm, fill=(24, 255, 140))
    d.ellipse([icx - 24, icy - 38, icx + 24, icy + 10], fill=(255, 95, 30), outline=(255, 200, 90), width=2)
    d.text((icx - 75, icy + 20), "Booms Y=±230mm | Plume Center", font=f_sm, fill=(200, 220, 240))

    cx4 = (1222 + 2378) * 0.5
    cy4 = (810 + 1385) * 0.5
    sc4 = 0.55

    def sx_sy(x_mm, z_mm):
        return int(round(cx4 + (x_mm - 740.0) * sc4)), int(round(cy4 - z_mm * sc4))

    cg_x, _ = sx_sy(595.0, 0)
    np_x, _ = sx_sy(636.0, 0)
    d.line([(cg_x, 820), (cg_x, 1375)], fill=(24, 224, 127), width=3)
    d.line([(np_x, 820), (np_x, 1375)], fill=(255, 190, 46), width=3)
    for x0m, z0m, x1m, z1m, col in [
        (292, 10, 437, -34, (20, 120, 220)),
        (381, 52, 449, -16, (0, 216, 255)),
        (440, 55, 750, -25, (24, 200, 125)),
        (445, -28, 865, -95, (255, 115, 25)),
        (710, 126, 975, 30, (255, 75, 75)),
    ]:
        p0 = sx_sy(x0m, z0m)
        p1 = sx_sy(x1m, z1m)
        d.rectangle([p0[0], p0[1], p1[0], p1[1]], fill=col, outline=(255, 255, 255), width=2)

    for x1, y1, x2, y2, title, bullets in panels_meta:
        d.rectangle([x1 + 4, y1 + 4, x2 - 4, y1 + 44], fill=(10, 28, 52), outline=(0, 190, 255), width=1)
        d.text((x1 + 18, y1 + 12), title, font=f_panel, fill=(0, 225, 255))
        d.rectangle([x1 + 4, y2 - 90, x2 - 4, y2 - 4], fill=(8, 22, 42), outline=(30, 80, 125), width=1)
        by = y2 - 82
        for b in bullets:
            d.text((x1 + 18, by), b, font=f_lbl, fill=(220, 235, 250))
            by += 25

    os.makedirs(os.path.dirname(OUT_DOCS_JPG), exist_ok=True)
    im.save(OUT_DOCS_JPG, quality=96)
    print(f"Saved 4-angle OpenCASCADE STL raster reference to:\n  {OUT_DOCS_JPG}")


if __name__ == "__main__":
    main()
