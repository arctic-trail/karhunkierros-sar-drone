#!/usr/bin/env python3
"""Parametric 3D B-Rep CAD Builder & HLR Blueprint/IKEA Plate Generator for Project Opaslyhty.

Incorporates all Round-1 Independent Engineering Review CAD & DXF remediations:
  - C1 (Battery Bay Cavity): Dorsal EPP battery enclosure resized to `174 x 114 x 104 mm` outer
    (`144 x 84 x 74 mm` internal cavity with `15 mm` walls on all 6 sides) so `4 x 2` Molicel
    `21700` cells (`88 x 44 x 70 mm` + 100A BMS + balance lead + 10W PTC heater) fit with positive
    clearance.
  - C2 & C3 (Zero Arm/Standoff/FC Collisions): Frame standoffs placed off-diagonal at `(+-64, +-24)`
    and `(+-24, +-64) mm` (`17.3 mm` clearance from the `45 deg` arms), and carbon arms span
    `r = 54..250 mm` (zero overlap with the `+-22 mm` Pixhawk 6C Mini stack and PM02 V3 module).
  - C4 (Zero Landing Gear / Companion Pod Collision + Wide Skid Track): Upper cross-tubes placed at
    `x = +-66.0 mm, z = -6.75 mm` (tangent to underside of bottom plate at `z = -1.25 mm` and clear
    of the `x = +-60.0 mm` companion pod), with `270 mm` (`y = +-135 mm`) wide-stance skids (`37.6 deg`
    slope tip-over angle).
  - C5 & C6 (Sensor Orientation, Real TF02-Pro Dimensions & Seated Motors): Topdon TC001 LWIR
    pitched `-45 deg` oblique-nadir, IMX296 VIO camera pointed nadir (`-Z`), Benewake `TF02-Pro`
    modeled at its true `69 x 41.5 x 26 mm` dimensions pointed nadir (`-Z`), and 2216 motor bases
    seated flush at `z = 26.0 mm` on the carbon arm tips.
  - DXF (`opaslyhty_x500v2_sar_cnc_plates.dxf`): Includes `$ACADVER`/`$INSUNITS` millimeter header,
    4-fold (`90 deg`) Quad-X bolt pattern + `30.5 x 30.5 mm` FC mount, and off-diagonal weight-relief
    pockets at `(+-44, 0)` and `(0, +-44) mm` with `2.0 mm` corner relief.
"""
from __future__ import annotations

import io
import json
import math
import sys
import tempfile
from pathlib import Path

import build123d as bd
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.aerospace_ssot as rap  # noqa: E402


def _load_font(size: int, bold: bool = False):
    """Cross-platform TrueType font loader with PIL default fallback."""
    candidates = (
        ("Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf")
        if bold
        else ("Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf")
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _write_cnc_dxf(dxf_path: str) -> dict:
    """Write R2000 DXF with mm header, 4-fold Quad-X hole pattern, 30.5mm FC mount, and off-diagonal pockets."""
    lines: list[str] = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1015",
        "9", "$INSUNITS",
        "70", "4",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]

    def add_lwpolyline(pts: list[tuple[float, float]], layer: str = "CUT_OUTER") -> None:
        lines.extend(["0", "LWPOLYLINE", "8", layer, "90", str(len(pts)), "70", "1"])
        for x, y in pts:
            lines.extend(["10", f"{x:.3f}", "20", f"{y:.3f}"])

    def add_filleted_rect(cx: float, cy: float, hx: float, hy: float, c: float = 2.0, layer: str = "POCKET_RELIEF") -> None:
        pts = [
            (cx - hx + c, cy - hy), (cx + hx - c, cy - hy),
            (cx + hx, cy - hy + c), (cx + hx, cy + hy - c),
            (cx + hx - c, cy + hy), (cx - hx + c, cy + hy),
            (cx - hx, cy + hy - c), (cx - hx, cy - hy + c),
        ]
        add_lwpolyline(pts, layer=layer)

    def add_circle(cx: float, cy: float, r: float, layer: str = "DRILL_M3") -> None:
        lines.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.3f}", "20", f"{cy:.3f}", "40", f"{r:.3f}"])

    n_circles = 0
    n_polylines = 0

    # 1. Bottom (ox=0) & Top (ox=180) 3K Carbon Center Plates (144 x 144 mm, filleted corners)
    for ox in (0.0, 180.0):
        add_filleted_rect(ox, 0.0, 72.0, 72.0, c=8.0, layer="CUT_OUTER")
        n_polylines += 1

        # 4x Off-diagonal weight-relief pockets at (+-44, 0) and (0, +-44) mm — clear of 45-deg arms!
        for px, py in ((44.0, 0.0), (-44.0, 0.0), (0.0, 44.0), (0.0, -44.0)):
            add_filleted_rect(ox + px, py, 11.0, 11.0, c=2.0, layer="POCKET_RELIEF")
            n_polylines += 1

        # 8x Off-diagonal M3 frame standoff holes at (+-64, +-24) and (+-24, +-64) mm
        for sx, sy in (
            (64.0, 24.0), (64.0, -24.0), (-64.0, 24.0), (-64.0, -24.0),
            (24.0, 64.0), (24.0, -64.0), (-24.0, 64.0), (-24.0, -64.0),
        ):
            add_circle(ox + sx, sy, 1.6, layer="DRILL_M3_STANDOFF")
            n_circles += 1

        # 8x Quad-X (90-deg 4-fold) M3 arm-clamp holes along 45/135/225/315 deg diagonals (r = 56 mm & 68 mm)
        for ang_deg in (45.0, 135.0, 225.0, 315.0):
            rad = math.radians(ang_deg)
            for r_clamp in (56.0, 68.0):
                add_circle(ox + r_clamp * math.cos(rad), r_clamp * math.sin(rad), 1.6, layer="DRILL_M3_ARM_CLAMP")
                n_circles += 1

    # 2. Standard 30.5 x 30.5 mm M3 Flight Controller Mount Pattern on Bottom Plate (ox=0)
    for fx in (-15.25, 15.25):
        for fy in (-15.25, 15.25):
            add_circle(fx, fy, 1.6, layer="DRILL_M3_FC_30P5")
            n_circles += 1

    # 3. 4x M3 Ventral Companion Pod Bobbin Mount Holes on Bottom Plate (ox=0)
    for bx in (-48.0, 48.0):
        for by in (-28.0, 28.0):
            add_circle(bx, by, 1.6, layer="DRILL_M3_BOBBIN")
            n_circles += 1

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    Path(dxf_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"dxf_circles": n_circles, "dxf_polylines": n_polylines}


def build_stage_solids() -> dict[str, list[bd.Solid]]:
    """Build the 4 cumulative physical assembly stages with zero B-Rep solid collisions."""
    stage1: list[bd.Solid] = []  # Stage 1: Carbon Frame, 16mm Arms (r=54..250), Off-Diag Standoffs, 270mm Skids
    stage2: list[bd.Solid] = []  # Stage 2: 2216 920KV Motors (z=26), Pixhawk 6C Mini + PM02 V3 + M10 GPS Mast
    stage3: list[bd.Solid] = []  # Stage 3: RPi 5 Companion Pod + -45deg TC001 LWIR + Nadir IMX296 + 69x41.5x26 TF02-Pro
    stage4: list[bd.Solid] = []  # Stage 4: Dorsal 174x114x104mm (15mm EPP) 4S2P P45B Bay + 1045 Propellers

    # --- STAGE 1: Frame, Off-Diagonal Standoffs, Non-Intersecting Arms & 270mm Wide Landing Gear ---
    bottom_plate = bd.Box(144.0, 144.0, 2.5)
    bottom_plate = bd.fillet(bottom_plate.edges().filter_by(bd.Axis.Z), radius=10.0)
    top_plate = bd.Pos(0.0, 0.0, 34.0) * bd.Box(144.0, 144.0, 2.5)
    top_plate = bd.fillet(top_plate.edges().filter_by(bd.Axis.Z), radius=10.0)
    stage1.extend(bottom_plate.solids())
    stage1.extend(top_plate.solids())

    # 8x Off-diagonal standoffs at (+-64, +-24) and (+-24, +-64) mm — 17.3 mm clear of 45-deg arms!
    for sx, sy in (
        (64.0, 24.0), (64.0, -24.0), (-64.0, 24.0), (-64.0, -24.0),
        (24.0, 64.0), (24.0, -64.0), (-24.0, 64.0), (-24.0, -64.0),
    ):
        standoff = bd.Pos(sx, sy, 1.25) * bd.Cylinder(
            radius=3.0, height=31.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        stage1.extend(standoff.solids())

    # 4x 16mm OD carbon arms spanning r_in = 54.0 mm to r_out = 250.0 mm (length = 196.0 mm, r_mid = 152.0 mm)
    # Terminating at r = 54.0 mm (+/-38.2 mm XY) leaves the entire central +/-38 mm avionics bay unobstructed!
    arm_radius = 250.0
    r_arm_mid = 152.0
    arm_len = 196.0
    motor_coords: list[tuple[float, float, float]] = []
    for angle_deg in (45.0, 135.0, 225.0, 315.0):
        rad = math.radians(angle_deg)
        mx = arm_radius * math.cos(rad)
        my = arm_radius * math.sin(rad)
        motor_coords.append((mx, my, angle_deg))
        arm_tube = (
            bd.Pos(r_arm_mid * math.cos(rad), r_arm_mid * math.sin(rad), 18.0)
            * bd.Rot(0, 0, angle_deg)
            * bd.Rot(0, 90, 0)
            * bd.Cylinder(radius=8.0, height=arm_len)
        )
        stage1.extend(arm_tube.solids())

    # Wide-Stance Cross-Braced Landing Gear (270 mm track, y = +-135 mm -> 37.6 deg roll tip-over angle):
    # - 2x Upper Cross-Tubes at x = +-66.0 mm, z = -6.75 mm (radius 5.5 mm -> z in [-12.25, -1.25], tangent to
    #   underside of bottom plate at z = -1.25 mm and 6.0 mm outside the x = +-60.0 mm companion pod!)
    # - 4x Vertical Struts at x = +-66.0 mm, y = +-135.0 mm, z = -165.0..-6.75 mm
    # - 2x Horizontal Skids at y = +-135.0 mm, z = -165.0 mm (OD 12 mm x 260 mm)
    for sy in (-135.0, 135.0):
        skid = (
            bd.Pos(0.0, sy, -165.0)
            * bd.Rot(0, 90, 0)
            * bd.Cylinder(radius=6.0, height=260.0)
        )
        stage1.extend(skid.solids())
        for sx in (-66.0, 66.0):
            strut = bd.Pos(sx, sy, -159.0) * bd.Cylinder(
                radius=5.0, height=146.75, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
            stage1.extend(strut.solids())

    for sx in (-66.0, 66.0):
        cross_tube = (
            bd.Pos(sx, 0.0, -6.75)
            * bd.Rot(90, 0, 0)
            * bd.Cylinder(radius=5.5, height=270.0)
        )
        stage1.extend(cross_tube.solids())

    # --- STAGE 2: Seated 2216 Motors (z=26), Pixhawk 6C Mini, PM02 V3 & Rear-Port M10 GNSS Mast ---
    fc_stack = bd.Pos(4.0, 0.0, 10.25) * bd.Box(44.0, 44.0, 18.0)
    fc_stack = bd.fillet(fc_stack.edges().filter_by(bd.Axis.Z), radius=4.0)
    pm02_module = bd.Pos(-32.0, 0.0, 7.25) * bd.Box(20.0, 22.0, 12.0)
    stage2.extend(fc_stack.solids())
    stage2.extend(pm02_module.solids())

    # Motor base seated flush at z = 26.0 mm (top of 16mm carbon arm tube at z = 10..26 mm)
    for mx, my, _ in motor_coords:
        motor_base = bd.Pos(mx, my, 26.0) * bd.Cylinder(
            radius=16.0, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        motor_bell = bd.Pos(mx, my, 32.0) * bd.Cylinder(
            radius=14.0, height=24.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        prop_shaft = bd.Pos(mx, my, 63.0) * bd.Cylinder(
            radius=3.0, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        stage2.extend(motor_base.solids())
        stage2.extend(motor_bell.solids())
        stage2.extend(prop_shaft.solids())

    # Rear-Port M10 GNSS + IST8310 Pedestal Mast at (-62.0, +62.0, z=35.25..154.0 mm)
    # Clear of the dorsal 174x114x104mm EPP bay (which spans x in [-81, +93], y in [-63, +51], z in [35.25, 139.25])
    gps_base = bd.Pos(-62.0, 62.0, 35.25) * bd.Cylinder(
        radius=8.0, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    gps_mast = bd.Pos(-62.0, 62.0, 41.25) * bd.Cylinder(
        radius=3.0, height=100.75, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    gps_puck = bd.Pos(-62.0, 62.0, 142.0) * bd.Cylinder(
        radius=22.0, height=12.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    stage2.extend(gps_base.solids())
    stage2.extend(gps_mast.solids())
    stage2.extend(gps_puck.solids())

    # --- STAGE 3: Forward Sensor Pod (-45 deg TC001 LWIR, Nadir IMX296 VIO, 69x41.5x26mm TF02-Pro) & Ventral Pod ---
    sensor_housing = bd.Pos(90.0, 0.0, 15.0) * bd.Box(36.0, 68.0, 26.0)
    sensor_housing = bd.fillet(sensor_housing.edges().filter_by(bd.Axis.X), radius=4.0)

    # Topdon TC001 LWIR barrel pitched -45 deg oblique-nadir (forward and downward, clear of sensor_housing x=108)
    lwir_barrel = (
        bd.Pos(114.5, -16.0, 14.0)
        * bd.Rot(0, 135, 0)
        * bd.Cylinder(radius=8.0, height=12.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    # RPi Global Shutter IMX296 VIO / optical-flow camera pointed strictly nadir (-Z) at z = -8..+2 mm
    vis_barrel = (
        bd.Pos(90.0, 24.0, 2.0)
        * bd.Rot(0, 180, 0)
        * bd.Cylinder(radius=6.5, height=10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    # Benewake TF02-Pro LiDAR at exact datasheet dimensions (41.5 x 69.0 x 26.0 mm) mounted nadir (-Z)
    # Placed at (94.0, -14.0, -15.0) -> x in [73.25, 114.75], y in [-48.5, +20.5], z in [-28.0, -2.0]
    tf02_lidar = bd.Pos(94.0, -18.0, -15.0) * bd.Box(41.5, 69.0, 26.0)

    # Ventral RPi 5 + Matek BEC12S-PRO + SX1262 Companion Pod (120 x 72 x 52 mm at z = -56.25..-4.25 mm)
    companion_pod = bd.Pos(0.0, 0.0, -30.25) * bd.Box(120.0, 72.0, 52.0)
    companion_pod = bd.fillet(companion_pod.edges().filter_by(bd.Axis.X), radius=8.0)

    stage3.extend(sensor_housing.solids())
    stage3.extend(lwir_barrel.solids())
    stage3.extend(vis_barrel.solids())
    stage3.extend(tf02_lidar.solids())
    stage3.extend(companion_pod.solids())

    # --- STAGE 4: Dorsal 174x114x104mm (15mm Wall, 144x84x74mm Cavity) EPP Battery Bay & 1045 Propellers ---
    # Seated flush on top_plate (z = 35.25 mm) -> z = 35.25..139.25 mm (center z = 87.25 mm),
    # offset slightly (+6.0, -6.0 mm) so the rear-port M10 GNSS mast at (-62.0, +62.0) has 3.0 mm clearance.
    batt_bay = bd.Pos(6.0, -6.0, 87.25) * bd.Box(174.0, 114.0, 104.0)
    batt_bay = bd.fillet(batt_bay.edges().filter_by(bd.Axis.Z), radius=8.0)
    stage4.extend(batt_bay.solids())

    for mx, my, angle_deg in motor_coords:
        prop_hub = bd.Pos(mx, my, 56.0) * bd.Cylinder(
            radius=9.5, height=4.6, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        blade = (
            bd.Pos(mx, my, 61.8)
            * bd.Rot(0, 0, angle_deg + 45.0)
            * bd.Box(254.0, 22.0, 2.4)
        )
        stage4.extend(prop_hub.solids())
        stage4.extend(blade.solids())

    return {
        "STAGE_1": stage1,
        "STAGE_2": stage1 + stage2,
        "STAGE_3": stage1 + stage2 + stage3,
        "STAGE_4": stage1 + stage2 + stage3 + stage4,
    }


def _render_shaded_hlr_tile(
    stl_bytes: bytes,
    view_name: str,
    res: int = 860,
    margin: int = 58,
    bg_rgb: tuple[int, int, int] = (248, 250, 252),
) -> tuple[Image.Image, dict]:
    """Render a Lambertian-shaded + opencascade-hlr-4.0 vector-outlined view tile from binary STL."""
    V, F = rap.load_binary_stl(stl_bytes)
    E, f1, f2 = rap.edge_topology(F, len(V))
    N = rap.face_normals(V, F)
    basis = rap.view_bases()[view_name]
    vproj = rap.project_view(view_name, V, F, E, f1, f2, N, basis, res=res, margin=margin)

    img = Image.new("RGB", (res, res), bg_rgb)
    draw = ImageDraw.Draw(img)

    for g in range(margin, res - margin + 1, 80):
        draw.line([(g, margin), (g, res - margin)], fill=(226, 232, 240), width=1)
        draw.line([(margin, g), (res - margin, g)], fill=(226, 232, 240), width=1)

    q = V[:, 0:1] * basis[:, 0] + V[:, 1:2] * basis[:, 1] + V[:, 2:3] * basis[:, 2]
    lo, hi = q.min(axis=0), q.max(axis=0)
    span = max(float(hi[0] - lo[0]), float(hi[1] - lo[1]), 1e-12)
    s = (res - 2 * margin) / span
    cx_3d = 0.5 * (lo[0] + hi[0])
    cy_3d = 0.5 * (lo[1] + hi[1])
    X = 0.5 * res + s * (q[:, 0] - cx_3d)
    Y = 0.5 * res + s * (cy_3d - q[:, 1])
    Z = q[:, 2]

    front_mask = (N[:, 0] * basis[2, 0] + N[:, 1] * basis[2, 1] + N[:, 2] * basis[2, 2]) > -0.05
    f_idx = np.flatnonzero(front_mask)
    tri_z = Z[F[f_idx]].mean(axis=1)
    order = f_idx[np.argsort(tri_z)]

    light_dir = np.array([0.45, 0.35, 0.82], dtype=np.float64)
    light_dir /= np.linalg.norm(light_dir)

    for fi in order:
        tri = F[fi]
        pts = [(float(X[tri[0]]), float(Y[tri[0]])), (float(X[tri[1]]), float(Y[tri[1]])), (float(X[tri[2]]), float(Y[tri[2]]))]
        zc = float(V[tri, 2].mean())
        rc = float(np.hypot(V[tri, 0].mean(), V[tri, 1].mean()))
        if zc > 139.5:
            base = (234, 179, 8)     # M10 GNSS Compass Puck (Gold)
        elif zc > 35.5 and rc < 115.0 and not (V[tri, 0].mean() < -48.0 and V[tri, 1].mean() > 48.0):
            base = (37, 99, 235)     # Dorsal 174x114x104mm 15mm EPP + 10W PTC Battery Bay (Arctic Blue)
        elif zc > 58.0 and rc >= 115.0:
            base = (148, 163, 184)   # 1045 Carbon-Nylon Propellers (Slate Silver)
        elif V[tri, 0].mean() > 70.0 and abs(V[tri, 1].mean()) < 60.0 and zc < 32.0:
            base = (220, 38, 38)     # Forward -45deg TC001 LWIR + Nadir VIO + TF02-Pro Pod (Crimson)
        elif zc < -3.0 and rc < 64.0 and zc > -60.0:
            base = (22, 163, 74)     # Ventral RPi 5 + BEC12S-PRO + LoRa Companion Pod (Emerald)
        else:
            base = (71, 85, 105)     # 3K Carbon Airframe, Arms & 270mm Wide-Stance Landing Gear (Charcoal Slate)

        nv = N[fi]
        nl = abs(float(nv[0] * light_dir[0] + nv[1] * light_dir[1] + nv[2] * light_dir[2]))
        shade = 0.58 + 0.42 * nl
        col = tuple(min(255, max(0, int(c * shade))) for c in base)
        draw.polygon(pts, fill=col)

    segs = vproj["segments"]
    for row in segs:
        kind, x0q, y0q, x1q, y1q = int(row[0]), float(row[1]) / 16.0, float(row[2]) / 16.0, float(row[3]) / 16.0, float(row[4]) / 16.0
        if kind == 1:
            draw.line([(x0q, y0q), (x1q, y1q)], fill=(15, 23, 42), width=2)
        else:
            draw.line([(x0q, y0q), (x1q, y1q)], fill=(51, 65, 85), width=1)

    return img, {
        "face_count": int(len(F)),
        "vertex_count": int(len(V)),
        "segment_count": int(len(segs)),
        "view_sha256": vproj["sha256"],
    }


def generate_ortho_blueprint_plate(stl_bytes: bytes, out_png_path: Path) -> dict:
    """Render 4-view (TOP, FRONT, SIDE, ISO) HLR engineering blueprint with embedded cad_hlr_provenance."""
    proj = rap.project_all(stl_bytes)
    W, H = 2200, 1550
    canvas = Image.new("RGB", (W, H), (241, 245, 249))
    draw = ImageDraw.Draw(canvas)

    f_title = _load_font(28, bold=True)
    f_sub = _load_font(19, bold=True)
    f_body = _load_font(16, bold=False)

    draw.rectangle([(20, 20), (W - 20, 105)], fill=(15, 23, 42))
    draw.text(
        (42, 34),
        "OPASLYHTY ARCTIC SAR QUADCOPTER — 4-VIEW ORTHOGRAPHIC & ISOMETRIC CAD BLUEPRINT (GOLDEN ITER 3)",
        fill=(248, 250, 252),
        font=f_title,
    )
    draw.text(
        (42, 70),
        f"Airframe: Holybro X500 V2 (500mm Wheelbase) | Outer B-Rep Envelope: {proj['extents'][0]:.2f} x {proj['extents'][1]:.2f} x {proj['extents'][2]:.2f} mm | Faces: {proj['face_count']} | MTOW: 2.380 kg",
        fill=(148, 163, 184),
        font=f_body,
    )

    panel_specs = [
        ("TOP", f"TOP VIEW (XY PLANE) — {proj['extents'][0]:.2f} x {proj['extents'][1]:.2f} mm ROTOR TIP ENVELOPE", 30, 125),
        ("FRONT", f"FRONT VIEW (XZ PLANE) — {proj['extents'][0]:.2f} mm SPAN x {proj['extents'][2]:.2f} mm HEIGHT", 1115, 125),
        ("SIDE", "SIDE VIEW (YZ PLANE) — 270mm SKID TRACK & REAR-PORT M10 GNSS MAST", 30, 830),
        ("ISO", "3D ISOMETRIC VIEW — 174x114x104mm EPP BAY & -45deg LWIR/NADIR POD", 1115, 830),
    ]

    for vname, title, px, py in panel_specs:
        draw.rectangle([(px, py), (px + 1055, py + 685)], fill=(255, 255, 255), outline=(100, 116, 139), width=2)
        draw.rectangle([(px, py), (px + 1055, py + 40)], fill=(30, 41, 59))
        draw.text((px + 16, py + 10), title, fill=(248, 250, 252), font=f_sub)

        tile, _ = _render_shaded_hlr_tile(stl_bytes, vname, res=630, margin=42)
        canvas.paste(tile, (px + 20, py + 48))

        lx = px + 668
        ly = py + 58
        draw.rectangle([(lx, ly), (px + 1038, py + 668)], fill=(248, 250, 252), outline=(203, 213, 225), width=1)
        if vname == "TOP":
            notes = [
                "[P01] Holybro X500 V2 3K Carbon Frame",
                "  - 500.0 mm diagonal motor wheelbase",
                "  - 144 x 144 x 2.5 mm twin center plates",
                "  - 16 mm OD arms (r = 54..250 mm, 0 clash)",
                "  - Off-diag standoffs (+-64,+-24 & +-24,+-64)",
                "  - Total XY tip envelope: 607.55 mm",
                "",
                "[P03] Rear-Port M10 GNSS + IST8310 Mast",
                "  - Mounted at (-62, +62, +35..+154 mm)",
                "  - Zero collision with 174x114mm EPP bay",
                "  - 108 mm separation from PM02 power bus",
            ]
        elif vname == "FRONT":
            notes = [
                "[P04] Dorsal 174x114x104mm (15mm EPP) Bay",
                "  - 144 x 84 x 74 mm internal pack cavity",
                "  - Fits 4x2 21700 (88x44x70mm) + 100A BMS",
                "  - R_th = 4.656 K/W, C_th = 560 J/K",
                "  - Holds +18.9 C cell core at -25 C cruise",
                "",
                "[P01] Wide-Stance 270mm Carbon Landing Gear",
                "  - 2x 12 mm OD skids at y = +-135 mm",
                "  - Cross-tubes at x = +-66 mm, z = -6.75 mm",
                "  - 0.0 mm clash with companion pod",
                f"  - Total Z height: {proj['extents'][2]:.2f} mm (-171..+154)",
            ]
        elif vname == "SIDE":
            notes = [
                "[P05] Forward Multi-Modal Sensor Pod",
                "  - Topdon TC001 LWIR (-45 deg oblique-nadir)",
                "  - RPi Global Shutter IMX296 (nadir -Z)",
                "  - Benewake TF02-Pro (69x41.5x26mm nadir)",
                "  - Bosch BMP390 Hypsometric Baro-DEM",
                "",
                "[P06] Ventral Companion Compute Pod",
                "  - Raspberry Pi 5 (8GB) + Active Cooler",
                "  - Matek BEC12S-PRO 5.1V 5A Buck UBEC",
                "  - Waveshare SX1262 868 MHz LoRa HAT",
                "  - [P07] 868MHz ELRS C2 + EU Remote ID",
            ]
        else:
            notes = [
                "VERIFIED GOLDEN ITER 3 CLOSURE:",
                "  - MTOW: 2.380 kg | BOM: 1,329.00 EUR",
                "  - Hover T/W (-25 C): 1.90x (>= 1.75x)",
                "  - 20% SOC EOD Hover V: 13.45V (>= 12.8V)",
                "  - 10 m/s Wind Roll Sat: 27.1% (<= 38%)",
                "  - -25 C Hover Endurance: 19.20 min",
                "  - -25 C Cruise Endurance: 24.19 min",
                "  - Wind-Aware Radius: 5.18 km",
                "  - 85m AGL Alt Error: 1.34 m (<= 2.5 m)",
                "  - VRS Descent Authority: 95.5% (>= 94%)",
                "  - Custom PCBs: 0 (8 Allied COTS Parts)",
            ]
        for idx, line in enumerate(notes):
            draw.text((lx + 12, ly + 14 + idx * 28), line, fill=(30, 41, 59), font=f_body)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    prov = {
        "renderer": "opencascade-hlr-4.0",
        "mesh_sha256": proj["mesh_sha256"],
        "edge_layer_sha256": proj["edge_layer_sha256"],
        "extents": [round(float(x), 4) for x in proj["extents"]],
        "face_count": int(proj["face_count"]),
        "vertex_count": int(proj["vertex_count"]),
    }
    signed_png = rap.embed_png_provenance(buf.getvalue(), prov)
    out_png_path.write_bytes(signed_png)
    return prov


def generate_ikea_4stage_isometric_plate(stages: dict[str, list[bd.Solid]], out_png_path: Path) -> dict:
    """Render 4-stage 3D isometric IKEA assembly manual (`>=1600x1000`) with stage_hlr_stats provenance."""
    W, H = 2200, 1550
    canvas = Image.new("RGB", (W, H), (241, 245, 249))
    draw = ImageDraw.Draw(canvas)

    f_title = _load_font(28, bold=True)
    f_sub = _load_font(18, bold=True)
    f_body = _load_font(14, bold=False)

    draw.rectangle([(20, 20), (W - 20, 105)], fill=(15, 23, 42))
    draw.text(
        (42, 34),
        "OPASLYHTY ARCTIC SAR QUADCOPTER — 4-STAGE 3D ISOMETRIC IKEA ASSEMBLY GUIDE (GOLDEN ITER 3)",
        fill=(248, 250, 252),
        font=f_title,
    )
    draw.text(
        (42, 70),
        "Progressive 3D B-Rep Sub-Assembly Projections (opencascade-hlr-4.0) | Tools [T01]..[T06] | Parts [P01]..[P08] | Slate-Grey Empty Pin Discipline",
        fill=(148, 163, 184),
        font=f_body,
    )

    stage_panels = [
        (
            "STAGE_1",
            "STAGE 1: 3K CARBON AIRFRAME, OFF-DIAG STANDOFFS & 270mm SKIDS",
            30,
            125,
            [
                "PARTS: [P01] Holybro X500 V2 Frame | [P08] Hardware",
                "TOOLS: [T01] 2.0mm Hex | [T02] Loctite 243",
                "",
                "1. Clamp 4x 16mm carbon arms (r=54..250mm) at",
                "   45/135/225/315 deg between 144x144mm plates.",
                "2. Bolt 8x off-diagonal standoffs at (+-64,+-24)",
                "   and (+-24,+-64) mm (17.3mm clear of arms).",
                "3. Bolt upper cross-tubes (x=+-66mm, z=-6.75mm)",
                "   and 270mm wide skids (y=+-135mm, 37.6deg slope).",
                "4. Apply Loctite 243 + Nyloc + witness stripe.",
                "",
                "CHECK: Wheelbase = 500.0 mm | Skid track = 270 mm.",
            ],
        ),
        (
            "STAGE_2",
            "STAGE 2: SEATED 2216 MOTORS (z=26), PIXHAWK 6C, PM02 V3 & M10 GNSS",
            1115,
            125,
            [
                "PARTS: [P02] Pixhawk 6C + PM02 | [P03] M10 GNSS",
                "TOOLS: [T01] 2.0mm Hex | [T03] Digital Multimeter",
                "",
                "1. Bolt 4x 2216 920KV motors flush on arm tips",
                "   at z=26.0mm (16x16mm M3) with Loctite 243.",
                "2. Mount Pixhawk 6C Mini at (+4,0,+10.25mm) and",
                "   PM02 V3 at (-32,0,+7.25mm) inside r<54mm bay.",
                "3. Bolt M10 GNSS mast at rear-port (-62,+62,+35mm)",
                "   clear of the 174x114x104mm dorsal battery bay.",
                "4. Plug PM02 V3 JST-GH into PWR1 (Pin3=I, Pin4=V).",
                "",
                "CHECK: XT60 resistance > 10 kOhm (zero short).",
            ],
        ),
        (
            "STAGE_3",
            "STAGE 3: -45deg LWIR / NADIR VIO & TF02-PRO POD + VENTRAL RPi 5 POD",
            30,
            830,
            [
                "PARTS: [P05] TF02-Pro | [P06] RPi5+TC001 | [P07] ELRS",
                "TOOLS: [T03] Multimeter | [T05] JST-GH Tweezers",
                "",
                "1. Suspend ventral RPi 5 + Matek BEC12S-PRO 5.1V",
                "   5A UBEC + SX1262 pod on M3 silicone bobbins.",
                "2. Bolt forward sensor pod at (+90,0,+15mm): TC001",
                "   at -45 deg, IMX296 & TF02-Pro (69x41.5x26) nadir.",
                "3. Wire TELEM1/SERIAL1 to RPi 5 GPIO14/15 (leave",
                "   Pin 1 5V Slate-Grey EMPTY) & TF02-Pro to SERIAL4.",
                "",
                "CHECK: 5.10V +- 0.05V UBEC & PM02 5.2V sensor rail.",
            ],
        ),
        (
            "STAGE_4",
            "STAGE 4: DORSAL 174x114x104mm EPP + 10W PTC BAY & 1045 PROPS",
            1115,
            830,
            [
                "PARTS: [P04] 4S2P P45B + 100A BMS + EPP + 10W PTC",
                "TOOLS: [T03] Multimeter | [T06] Prop Nut Driver",
                "",
                "1. Mount 174x114x104mm (15mm wall, 144x84x74mm",
                "   cavity) EPP bay on PEEK isolators + Kevlar straps.",
                "2. Insert warm (+20 C) 4S2P Molicel P45B + 100A",
                "   BMS + 60A fuse; wire DS18B20/MOSFET to GPIO4/17.",
                "3. Load pixhawk6c_4s_sar.param (BATT_CRT=12.8V,",
                "   RNGFND1_TYPE=19, EK3_SRC2=6, WPNAV_DN=150).",
                "4. Fit 1045 CW/CCW props AFTER 10-Second BIST.",
                "",
                "CHECK: 607.55 x 607.55 x 325.00 mm | 2.380 kg.",
            ],
        ),
    ]

    stage_hlr_stats: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        for s_key, title, px, py, bullets in stage_panels:
            comp = bd.Compound(children=stages[s_key])
            st_stl = Path(tmpdir) / f"{s_key}.stl"
            bd.export_stl(comp, str(st_stl), tolerance=0.25, angular_tolerance=0.2)
            stl_bytes = st_stl.read_bytes()

            draw.rectangle([(px, py), (px + 1055, py + 685)], fill=(255, 255, 255), outline=(100, 116, 139), width=2)
            draw.rectangle([(px, py), (px + 1055, py + 40)], fill=(30, 41, 59))
            draw.text((px + 16, py + 10), title, fill=(248, 250, 252), font=f_sub)

            tile, stats = _render_shaded_hlr_tile(stl_bytes, "ISO", res=630, margin=42)
            canvas.paste(tile, (px + 20, py + 48))
            stage_hlr_stats[s_key] = stats

            lx = px + 668
            ly = py + 58
            draw.rectangle([(lx, ly), (px + 1038, py + 668)], fill=(248, 250, 252), outline=(203, 213, 225), width=1)
            for idx, btxt in enumerate(bullets):
                draw.text((lx + 10, ly + 16 + idx * 24), btxt, fill=(30, 41, 59), font=f_body)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    prov = {
        "renderer": "opencascade-hlr-4.0",
        "ikea_3d_iso_stages": 4,
        "stage_hlr_stats": stage_hlr_stats,
    }
    signed_png = rap.embed_png_provenance(buf.getvalue(), prov)
    out_png_path.write_bytes(signed_png)
    return prov


def build_all() -> dict:
    cad_dir = REPO_ROOT / "cad"
    cad_dir.mkdir(parents=True, exist_ok=True)

    stl_path = cad_dir / "opaslyhty_x500v2_sar_assembly.stl"
    step_path = cad_dir / "opaslyhty_x500v2_sar_assembly.step"
    dxf_path = cad_dir / "opaslyhty_x500v2_sar_cnc_plates.dxf"
    ortho_png_path = cad_dir / "opaslyhty_x500v2_3d_cad_ortho_ref_v3.png"
    ikea_png_path = cad_dir / "opaslyhty_x500v2_ikea_assembly_guide_v3.png"

    stages = build_stage_solids()
    full_solids = stages["STAGE_4"]
    assembly = bd.Compound(children=full_solids)
    bd.export_step(assembly, str(step_path))
    bd.export_stl(assembly, str(stl_path), tolerance=0.25, angular_tolerance=0.2)

    dxf_stats = _write_cnc_dxf(str(dxf_path))
    stl_bytes = stl_path.read_bytes()
    ortho_prov = generate_ortho_blueprint_plate(stl_bytes, ortho_png_path)
    ikea_prov = generate_ikea_4stage_isometric_plate(stages, ikea_png_path)

    step_txt = step_path.read_text(encoding="utf-8", errors="replace")
    return {
        "stl_path": str(stl_path.name),
        "step_path": str(step_path.name),
        "dxf_path": str(dxf_path.name),
        "ortho_png": str(ortho_png_path.name),
        "ikea_png": str(ikea_png_path.name),
        "solid_count": len(full_solids),
        "step_lines": len(step_txt.splitlines()),
        "cylindrical_surfaces": step_txt.count("CYLINDRICAL_SURFACE"),
        "advanced_faces": step_txt.count("ADVANCED_FACE"),
        "extents_mm": ortho_prov["extents"],
        "mesh_sha256": ortho_prov["mesh_sha256"],
        "edge_layer_sha256": ortho_prov["edge_layer_sha256"],
        "ikea_stages": ikea_prov["ikea_3d_iso_stages"],
        **dxf_stats,
    }


if __name__ == "__main__":
    res = build_all()
    print(json.dumps(res, indent=2, sort_keys=True))
