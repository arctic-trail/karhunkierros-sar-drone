#!/usr/bin/env python3
"""
Standalone 1:1 CNC Hot-Wire Foam-Core, Laser-Cut Bulkhead (.svg / .dxf) &
Carbon-Tube Cut-Schedule Exporter for `arctic-fast-sar-jet` (`FIN-LAB-02`).

Reads `cad/design_params_sar.json` (Single Source of Truth) and generates:
  1. `cad/finlab02_foam_ribs_and_bulkheads_1to1.svg` — True 1:1 mm vector cut sheet
  2. `cad/finlab02_foam_ribs_and_bulkheads_1to1.dxf` — AutoCAD R12 ASCII DXF (4 layers)
  3. `cad/cnc_foam_and_carbon_cut_schedule.json`     — Carbon tube, XPS block & bulkhead BOM
  4. `cad/ark_fpv_arduplane_45_sar_jet.param`        — Turnkey 44-param ArduPlane 4.5+ profile

Allows any university lab, SAR workshop, or maker space with a standard CNC router,
laser cutter, or hot-wire foam cutter to fabricate the $180 mouldless airframe shell
in one weekend without requiring proprietary enterprise CAD software.
"""

import json
import math
import os
import sys
from pathlib import Path

CAD_DIR = Path(__file__).resolve().parent
REPO_DIR = CAD_DIR.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from sar_autonomy.pi_turbine_autonomy import generate_arduplane_ark_fpv_param_profile


def naca_4digit_coords(code: str, chord_mm: float, n_pts: int = 60) -> list[tuple[float, float]]:
    """
    Computes exact closed-loop (upper TE -> LE -> lower TE) airfoil coordinates
    in millimeters for a 4-digit NACA section (e.g. '2412', '2410', '0009' or 'NACA 2412').
    Origin (0, 0) is at the Leading Edge (LE); +X is chordwise aft, +Y is upward thickness.
    """
    digits = code.replace("NACA", "").strip()
    m = int(digits[0]) / 100.0
    p = int(digits[1]) / 10.0
    t = int(digits[2:]) / 100.0

    betas = [math.pi * i / (n_pts - 1) for i in range(n_pts)]
    xs = [0.5 * (1.0 - math.cos(b)) for b in betas]

    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []

    for x in xs:
        yt = 5.0 * t * (
            0.2969 * math.sqrt(max(0.0, x))
            - 0.1260 * x
            - 0.3516 * (x ** 2)
            + 0.2843 * (x ** 3)
            - 0.1036 * (x ** 4)
        )
        if m == 0.0 or p == 0.0:
            yc = 0.0
            dyc_dx = 0.0
        elif x < p:
            yc = (m / (p ** 2)) * (2.0 * p * x - x ** 2)
            dyc_dx = (2.0 * m / (p ** 2)) * (p - x)
        else:
            yc = (m / ((1.0 - p) ** 2)) * ((1.0 - 2.0 * p) + 2.0 * p * x - x ** 2)
            dyc_dx = (2.0 * m / ((1.0 - p) ** 2)) * (p - x)

        theta = math.atan(dyc_dx)
        xu = (x - yt * math.sin(theta)) * chord_mm
        yu = (yc + yt * math.cos(theta)) * chord_mm
        xl = (x + yt * math.sin(theta)) * chord_mm
        yl = (yc - yt * math.cos(theta)) * chord_mm
        upper.append((round(xu, 3), round(yu, 3)))
        lower.append((round(xl, 3), round(yl, 3)))

    return list(reversed(upper)) + lower[1:]


def build_cnc_cut_schedule(params: dict) -> dict:
    """
    Derives the deterministic carbon-tube, XPS hot-wire foam core, and 3mm birch/carbon
    bulkhead cut schedule directly from `cad/design_params_sar.json`.
    """
    wing = params["airframe"]["outer_wing"]
    booms = params["airframe"]["twin_booms"]
    vtail = params["airframe"]["inverted_v_tail"]
    fuse = params["airframe"]["fuselage_and_strake"]
    bay = params["airframe"]["internal_subsystems"]["cg_payload_bay"]

    boom_len_mm = round(booms["x_end_mm"] - booms["x_start_mm"], 1)  # 1085.0 mm

    carbon_tubes = [
        {
            "cut_id": "CF-01",
            "part_name": "Center-Body Main Wing Spar Carry-Through Tube (25% MAC, X=545 mm)",
            "material": "Roll-Wrapped 3K Carbon Tube (20.0 mm OD x 18.0 mm ID, 1.0 mm wall)",
            "od_mm": wing["main_spar_od_mm"],
            "id_mm": wing["main_spar_od_mm"] - 2.0,
            "cut_length_mm": 520.0,
            "quantity": 1,
            "unit_cost_usd": 18.50,
            "notes": "Bonds through Bulkheads F2/F3 and twin boom saddles at Y = +/-230 mm",
        },
        {
            "cut_id": "CF-02",
            "part_name": "Outboard Cranked-Wing Main Spar Tubes (L & R Panels, Y=230..1100 mm)",
            "material": "Roll-Wrapped 3K Carbon Tube (20.0 mm OD x 18.0 mm ID, 1.0 mm wall)",
            "od_mm": wing["main_spar_od_mm"],
            "id_mm": wing["main_spar_od_mm"] - 2.0,
            "cut_length_mm": wing["outer_panel_length_each_mm"],
            "quantity": 2,
            "unit_cost_usd": 24.00,
            "notes": "885.0 mm each; mates with CF-01 via 18.0 mm solid carbon/7075-T6 joiner rod + 72-deg fold pin",
        },
        {
            "cut_id": "CF-03",
            "part_name": "Outboard Wing Aft Anti-Rotation / Flaperon Sub-Spar Tubes (68% Chord)",
            "material": "Pultruded/Roll-Wrapped Carbon Tube (12.0 mm OD x 10.0 mm ID)",
            "od_mm": wing["aft_spar_od_mm"],
            "id_mm": wing["aft_spar_od_mm"] - 2.0,
            "cut_length_mm": 820.0,
            "quantity": 2,
            "unit_cost_usd": 14.00,
            "notes": "Locks wing incidence and carries KST X10 Mini flaperon hinge loads",
        },
        {
            "cut_id": "CF-04",
            "part_name": "Twin Tail Booms (Y = +/-230 mm Outside Central Jet Exhaust Plume)",
            "material": "Roll-Wrapped 3K Carbon Tube (16.0 mm OD x 14.0 mm ID, 1.0 mm wall)",
            "od_mm": booms["carbon_tube_od_mm"],
            "id_mm": booms["carbon_tube_od_mm"] - 2.0,
            "cut_length_mm": boom_len_mm,
            "quantity": 2,
            "unit_cost_usd": 29.00,
            "notes": f"Spans X={booms['x_start_mm']} mm to X={booms['x_end_mm']} mm; routes ruddervator servo leads & 12km fiber option",
        },
        {
            "cut_id": "CF-05",
            "part_name": "110-deg Inverted Lambda-Tail Spar Tubes (35-deg Cant From Horizontal)",
            "material": "Roll-Wrapped Carbon Tube (10.0 mm OD x 8.0 mm ID)",
            "od_mm": 10.0,
            "id_mm": 8.0,
            "cut_length_mm": 295.0,
            "quantity": 2,
            "unit_cost_usd": 11.00,
            "notes": f"Bridges Y=+/-230 mm (Z=+12 mm) to central apex Y=0 mm (Z=+{vtail['apex_z_mm']} mm)",
        },
        {
            "cut_id": "CF-06",
            "part_name": "Main Wing Spar Joiner Rod & Ground-Fold Rig Pins (7075-T6 / Solid Carbon)",
            "material": "18.0 mm OD Solid Carbon Joiner + 2x M6 Quick-Release Ball-Lock Rig Pins",
            "od_mm": 18.0,
            "id_mm": 0.0,
            "cut_length_mm": 320.0,
            "quantity": 2,
            "unit_cost_usd": 16.00,
            "notes": "Pulling aft rig pins allows 72-deg ground transport fold to 680 mm width",
        },
    ]

    wing_ribs = [
        {
            "rib_id": "W1_STRAKE_ROOT",
            "name": "Center-Body Strake Root Template (Y = 130 mm)",
            "span_station_y_mm": 130.0,
            "chord_mm": 420.0,
            "naca_code": wing["airfoil_root"].replace("NACA", "").strip(),
            "main_spar_x_mm": round(420.0 * 0.25, 1),
            "main_spar_od_mm": wing["main_spar_od_mm"],
            "aft_spar_x_mm": round(420.0 * 0.68, 1),
            "aft_spar_od_mm": wing["aft_spar_od_mm"],
        },
        {
            "rib_id": "W2_BOOM_PIVOT",
            "name": "Boom-Junction & Fold-Pivot Root Rib (Y = 230 mm)",
            "span_station_y_mm": wing["pivot_y_mm"],
            "chord_mm": wing["chord_at_pivot_mm"],
            "naca_code": wing["airfoil_root"].replace("NACA", "").strip(),
            "main_spar_x_mm": round(wing["chord_at_pivot_mm"] * 0.25, 1),
            "main_spar_od_mm": wing["main_spar_od_mm"],
            "aft_spar_x_mm": round(wing["chord_at_pivot_mm"] * 0.68, 1),
            "aft_spar_od_mm": wing["aft_spar_od_mm"],
        },
        {
            "rib_id": "W3_MID_INBOARD",
            "name": "Outboard Panel Mid-Inboard Rib (Y = 520 mm)",
            "span_station_y_mm": 520.0,
            "chord_mm": 268.0,
            "naca_code": "2411",
            "main_spar_x_mm": round(268.0 * 0.25, 1),
            "main_spar_od_mm": wing["main_spar_od_mm"],
            "aft_spar_x_mm": round(268.0 * 0.68, 1),
            "aft_spar_od_mm": wing["aft_spar_od_mm"],
        },
        {
            "rib_id": "W4_MID_OUTBOARD",
            "name": "Outboard Panel Mid-Outboard Rib (Y = 810 mm)",
            "span_station_y_mm": 810.0,
            "chord_mm": 236.0,
            "naca_code": "2411",
            "main_spar_x_mm": round(236.0 * 0.25, 1),
            "main_spar_od_mm": wing["main_spar_od_mm"],
            "aft_spar_x_mm": round(236.0 * 0.68, 1),
            "aft_spar_od_mm": wing["aft_spar_od_mm"],
        },
        {
            "rib_id": "W5_WINGTIP",
            "name": "Outboard Panel Wingtip Template (Y = 1100 mm)",
            "span_station_y_mm": 1100.0,
            "chord_mm": wing["tip_chord_mm"],
            "naca_code": wing["airfoil_tip"].replace("NACA", "").strip(),
            "main_spar_x_mm": round(wing["tip_chord_mm"] * 0.25, 1),
            "main_spar_od_mm": wing["main_spar_od_mm"],
            "aft_spar_x_mm": round(wing["tip_chord_mm"] * 0.68, 1),
            "aft_spar_od_mm": wing["aft_spar_od_mm"],
        },
        {
            "rib_id": "T1_LAMBDA_TAIL_ROOT",
            "name": "110-deg Inverted Lambda-Tail Boom-Root Rib (Y = 230 mm)",
            "span_station_y_mm": vtail["boom_root_y_mm"],
            "chord_mm": vtail["boom_root_chord_mm"],
            "naca_code": "0009",
            "main_spar_x_mm": round(vtail["boom_root_chord_mm"] * 0.30, 1),
            "main_spar_od_mm": booms["carbon_tube_od_mm"],
            "aft_spar_x_mm": round(vtail["boom_root_chord_mm"] * 0.68, 1),
            "aft_spar_od_mm": 10.0,
        },
        {
            "rib_id": "T2_LAMBDA_TAIL_APEX",
            "name": "110-deg Inverted Lambda-Tail Centerline Apex Rib (Y = 0 mm, Z = +173 mm)",
            "span_station_y_mm": 0.0,
            "chord_mm": vtail["apex_chord_mm"],
            "naca_code": "0009",
            "main_spar_x_mm": round(vtail["apex_chord_mm"] * 0.30, 1),
            "main_spar_od_mm": 10.0,
            "aft_spar_x_mm": round(vtail["apex_chord_mm"] * 0.68, 1),
            "aft_spar_od_mm": 6.0,
        },
    ]

    bulkheads = [
        {
            "bulkhead_id": "F1_NOSE_FIREWALL",
            "station_x_mm": 120.0,
            "width_mm": 120.0,
            "height_mm": 105.0,
            "material": "3.0 mm Aircraft Birch Plywood / 1.5 mm Carbon-Epoxy Laminate",
            "cutouts": "Ø38.0 mm 3520-500KV Electric Sustainer Motor Mount + 4x Cooling Slots",
        },
        {
            "bulkhead_id": "F2_AVIONICS_AND_BATTERY",
            "station_x_mm": 435.0,
            "width_mm": 250.0,
            "height_mm": 170.0,
            "material": "3.0 mm Aircraft Birch Plywood",
            "cutouts": "120x40 mm Avionics Bay + 86x44 mm Heated 6S2P Battery Slot + Twin Ø16.0 mm Boom Sockets",
        },
        {
            "bulkhead_id": "F3_CG_BAY_FWD_AND_MAIN_SPAR",
            "station_x_mm": 545.0,
            "width_mm": fuse["center_body_width_mm"],
            "height_mm": fuse["max_height_mm"],
            "material": "2x 3.0 mm Doubled Birch Plywood + Carbon Cap Strip",
            "cutouts": f"{bay['width_mm']:.0f}x{bay['height_mm']:.0f} mm Ventral CG Bay Arch + Ø20.0 mm Main Spar Socket + Twin Ø96 mm Fuel Tank Cradles",
        },
        {
            "bulkhead_id": "F4_CG_BAY_AFT_AND_ENGINE_SLED",
            "station_x_mm": 865.0,
            "width_mm": fuse["center_body_width_mm"],
            "height_mm": 180.0,
            "material": "3.0 mm Aircraft Birch Plywood",
            "cutouts": f"{bay['width_mm']:.0f}x{bay['height_mm']:.0f} mm Aft Ventral Bay Arch + 150 mm Universal Dorsal Engine Sled Rails",
        },
        {
            "bulkhead_id": "F5_THERMAL_DECK_AFT_BRIDGE",
            "station_x_mm": 1220.0,
            "width_mm": 220.0,
            "height_mm": 125.0,
            "material": "3.0 mm Birch Plywood + 0.3 mm 304SS / 10 mm Silica-Aerogel Saddle",
            "cutouts": "Ø115 mm Double-Wall Exhaust Trough + Twin Ø16.0 mm Tail-Boom Clamp Bosses",
        },
    ]

    foam_blocks = [
        {"block_id": "XPS-01", "name": "Left & Right Outboard Wing Cores (Y=230..1100 mm, 16-deg Sweep)", "raw_block_mm": "900 x 320 x 50 mm (2x)", "material": "XPS 35 kg/m3 Closed-Cell Foam"},
        {"block_id": "XPS-02", "name": "Inboard 48-deg Leading-Edge Strake Cores (Y=130..230 mm)", "raw_block_mm": "450 x 140 x 60 mm (2x)", "material": "XPS 35 kg/m3 Closed-Cell Foam"},
        {"block_id": "XPS-03", "name": "Chined Blended Center-Body Shell & Nose Cone (X=0..1420 mm)", "raw_block_mm": "720 x 280 x 200 mm (2x)", "material": "XPS 35 kg/m3 Closed-Cell Foam"},
        {"block_id": "XPS-04", "name": "110-deg Inverted Lambda-Tail Panels (L & R)", "raw_block_mm": "310 x 230 x 35 mm (2x)", "material": "XPS 35 kg/m3 Closed-Cell Foam"},
    ]

    carbon_cost = sum(item["unit_cost_usd"] for item in carbon_tubes)
    foam_and_glass_cost = 66.00  # XPS sheets ($24) + 3mm birch ply ($16) + 80g/m2 E-glass & epoxy ($26)

    return {
        "design_id": params["design_id"],
        "version": params["version"],
        "scale": "1:1_MILLIMETERS",
        "overall_wingspan_mm": wing["modes"]["iteration_1_fixed_16deg"]["total_wingspan_mm"],
        "overall_fuselage_length_mm": fuse["length_mm"],
        "airborne_mtow_kg": 14.95,
        "cg_x_mm": bay["x_cg_mm"],
        "total_mouldless_airframe_material_cost_usd": round(carbon_cost + foam_and_glass_cost, 2),
        "carbon_tube_cut_schedule": carbon_tubes,
        "wing_and_tail_hotwire_ribs": wing_ribs,
        "laser_cut_fuselage_bulkheads": bulkheads,
        "xps_foam_billet_schedule": foam_blocks,
    }


def export_svg_cut_sheet(schedule: dict, out_svg_path: Path) -> None:
    """
    Writes a 1:1 millimeter-scaled SVG vector cut sheet (`950 mm x 580 mm`)
    for direct import into LightBurn, Inkscape, Illustrator, or CNC CAM tools.
    """
    w_mm, h_mm = 950, 580
    svg = [
        f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_mm}mm" height="{h_mm}mm" viewBox="0 0 {w_mm} {h_mm}">',
        '  <style>',
        '    .bg { fill: #ffffff; stroke: #1e293b; stroke-width: 0.8; }',
        '    .cut-rib { fill: none; stroke: #dc2626; stroke-width: 0.35; }',
        '    .cut-spar { fill: none; stroke: #2563eb; stroke-width: 0.35; }',
        '    .cut-bulkhead { fill: none; stroke: #059669; stroke-width: 0.40; }',
        '    .cal-box { fill: none; stroke: #0f172a; stroke-width: 0.50; stroke-dasharray: 3,2; }',
        '    .label { font-family: monospace; font-size: 5.5px; fill: #0f172a; }',
        '    .title { font-family: monospace; font-size: 8.0px; font-weight: bold; fill: #0f172a; }',
        '  </style>',
        f'  <rect x="2" y="2" width="{w_mm-4}" height="{h_mm-4}" class="bg"/>',
        '  <text x="15" y="16" class="title">FIN-LAB-02 (ARCTIC-FAST-SAR-JET) // 1:1 CNC HOT-WIRE FOAM RIBS &amp; 3MM BIRCH BULKHEAD CUT SHEET (UNITS: MM, MIT LICENSE)</text>',
        '  <text x="15" y="25" class="label">RED = Airfoil Outer Profile (NACA 2412/2410/0009) | BLUE = Carbon Spar &amp; Boom Sockets (Ø20/Ø16/Ø12/Ø10mm) | GREEN = 3.0mm Plywood Bulkheads (F1-F5)</text>',
        '  <!-- 100.0 mm x 100.0 mm Dimensional Calibration Verification Square -->',
        '  <rect x="825" y="15" width="100.0" height="100.0" class="cal-box"/>',
        '  <text x="830" y="62" class="label">100.0 x 100.0 mm</text>',
        '  <text x="830" y="70" class="label">SCALE CHECK SQUARE</text>',
    ]

    # Place the 7 wing/tail airfoil ribs in the left column (X = 25..470 mm)
    y_cursor = 65.0
    for rib in schedule["wing_and_tail_hotwire_ribs"]:
        pts = naca_4digit_coords(rib["naca_code"], rib["chord_mm"], n_pts=65)
        x0 = 25.0
        y0 = y_cursor
        poly_str = " ".join(f"{x0 + px:.2f},{y0 - py:.2f}" for px, py in pts)
        svg.append(f'  <!-- {rib["rib_id"]}: {rib["name"]} -->')
        svg.append(f'  <polygon points="{poly_str}" class="cut-rib"/>')
        # Main spar & aft spar circles
        r_main = rib["main_spar_od_mm"] / 2.0
        r_aft = rib["aft_spar_od_mm"] / 2.0
        svg.append(f'  <circle cx="{x0 + rib["main_spar_x_mm"]:.2f}" cy="{y0:.2f}" r="{r_main:.2f}" class="cut-spar"/>')
        svg.append(f'  <circle cx="{x0 + rib["aft_spar_x_mm"]:.2f}" cy="{y0:.2f}" r="{r_aft:.2f}" class="cut-spar"/>')
        svg.append(
            f'  <text x="{x0 + 8:.1f}" y="{y0 - r_main - 6:.1f}" class="label">'
            f'{rib["rib_id"]} (Y={rib["span_station_y_mm"]:.0f}mm, c={rib["chord_mm"]:.0f}mm, NACA {rib["naca_code"]}, '
            f'Main Spar Ø{rib["main_spar_od_mm"]:.0f}mm @ X={rib["main_spar_x_mm"]:.1f}mm)</text>'
        )
        y_cursor += 74.0

    # Place the 5 fuselage bulkheads F1-F5 on the right half (X = 485..920 mm)
    bh_positions = [
        (485.0, 45.0),
        (640.0, 45.0),
        (485.0, 245.0),
        (765.0, 245.0),
        (485.0, 445.0),
    ]
    for bh, (bx, by) in zip(schedule["laser_cut_fuselage_bulkheads"], bh_positions):
        bw = bh["width_mm"]
        bh_h = bh["height_mm"]
        cx = bx + bw / 2.0
        cy = by + bh_h / 2.0
        # Outer chined bulkhead octagon
        chamfer = min(28.0, bw * 0.14)
        oct_pts = [
            (bx + chamfer, by),
            (bx + bw - chamfer, by),
            (bx + bw, by + chamfer),
            (bx + bw, by + bh_h - chamfer),
            (bx + bw - chamfer, by + bh_h),
            (bx + chamfer, by + bh_h),
            (bx, by + bh_h - chamfer),
            (bx, by + chamfer),
        ]
        oct_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in oct_pts)
        svg.append(f'  <!-- {bh["bulkhead_id"]} @ X={bh["station_x_mm"]}mm -->')
        svg.append(f'  <polygon points="{oct_str}" class="cut-bulkhead"/>')

        if bh["bulkhead_id"] == "F1_NOSE_FIREWALL":
            svg.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="19.0" class="cut-spar"/>')
            svg.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="7.0" class="cut-bulkhead"/>')
        elif bh["bulkhead_id"] in ("F3_CG_BAY_FWD_AND_MAIN_SPAR", "F4_CG_BAY_AFT_AND_ENGINE_SLED"):
            # Ventral 180 x 145 mm CG payload bay arch cutout (scaled inside bulkhead)
            cut_w = 180.0
            cut_h = 125.0
            svg.append(
                f'  <rect x="{cx - cut_w/2:.1f}" y="{by + bh_h - cut_h:.1f}" '
                f'width="{cut_w:.1f}" height="{cut_h:.1f}" class="cut-bulkhead"/>'
            )
            if bh["bulkhead_id"] == "F3_CG_BAY_FWD_AND_MAIN_SPAR":
                svg.append(f'  <circle cx="{cx:.1f}" cy="{by + 28.0:.1f}" r="10.0" class="cut-spar"/>')
        else:
            # Central lightening / avionics cutout
            cut_w = bw * 0.48
            cut_h = bh_h * 0.42
            svg.append(
                f'  <rect x="{cx - cut_w/2:.1f}" y="{cy - cut_h/2:.1f}" '
                f'width="{cut_w:.1f}" height="{cut_h:.1f}" class="cut-bulkhead"/>'
            )

        svg.append(
            f'  <text x="{bx + 6:.1f}" y="{by - 4:.1f}" class="label">'
            f'{bh["bulkhead_id"]} (X={bh["station_x_mm"]:.0f}mm, {bw:.0f}x{bh_h:.0f}mm)</text>'
        )

    svg.append('</svg>\n')
    out_svg_path.write_text("\n".join(svg), encoding="utf-8")


def export_dxf_cut_sheet(schedule: dict, out_dxf_path: Path) -> None:
    """
    Writes a standard AutoCAD R12 ASCII DXF file (`LINE`, `CIRCLE`, `TEXT`) in 1:1 mm units
    so any CAD/CAM package (Fusion 360, FreeCAD, LightBurn, Mach3, LinuxCNC) imports it cleanly.
    """
    dxf: list[str] = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$INSUNITS",
        "70", "4",  # 4 = Millimeters
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]

    def add_line(layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        dxf.extend([
            "0", "LINE",
            "8", layer,
            "10", f"{x1:.3f}",
            "20", f"{y1:.3f}",
            "30", "0.0",
            "11", f"{x2:.3f}",
            "21", f"{y2:.3f}",
            "31", "0.0",
        ])

    def add_circle(layer: str, cx: float, cy: float, r: float) -> None:
        dxf.extend([
            "0", "CIRCLE",
            "8", layer,
            "10", f"{cx:.3f}",
            "20", f"{cy:.3f}",
            "30", "0.0",
            "40", f"{r:.3f}",
        ])

    def add_text(layer: str, x: float, y: float, text: str, height: float = 4.0) -> None:
        dxf.extend([
            "0", "TEXT",
            "8", layer,
            "10", f"{x:.3f}",
            "20", f"{y:.3f}",
            "30", "0.0",
            "40", f"{height:.2f}",
            "1", text,
        ])

    # 1. 100.0 x 100.0 mm Calibration Square on layer 0_CALIBRATION
    cal_x, cal_y = 825.0, 460.0
    add_line("0_CALIBRATION", cal_x, cal_y, cal_x + 100.0, cal_y)
    add_line("0_CALIBRATION", cal_x + 100.0, cal_y, cal_x + 100.0, cal_y + 100.0)
    add_line("0_CALIBRATION", cal_x + 100.0, cal_y + 100.0, cal_x, cal_y + 100.0)
    add_line("0_CALIBRATION", cal_x, cal_y + 100.0, cal_x, cal_y)
    add_text("4_LABELS", cal_x + 5.0, cal_y + 50.0, "100x100mm_CALIBRATION_SQUARE", 4.0)

    # 2. Wing & Tail Ribs on layer 1_WING_AIRFOIL_RIBS & 2_SPAR_AND_BOOM_HOLES
    y_cursor = 500.0
    for rib in schedule["wing_and_tail_hotwire_ribs"]:
        pts = naca_4digit_coords(rib["naca_code"], rib["chord_mm"], n_pts=65)
        x0 = 25.0
        y0 = y_cursor
        for i in range(len(pts) - 1):
            add_line(
                "1_WING_AIRFOIL_RIBS",
                x0 + pts[i][0],
                y0 + pts[i][1],
                x0 + pts[i + 1][0],
                y0 + pts[i + 1][1],
            )
        add_circle("2_SPAR_AND_BOOM_HOLES", x0 + rib["main_spar_x_mm"], y0, rib["main_spar_od_mm"] / 2.0)
        add_circle("2_SPAR_AND_BOOM_HOLES", x0 + rib["aft_spar_x_mm"], y0, rib["aft_spar_od_mm"] / 2.0)
        add_text(
            "4_LABELS",
            x0 + 5.0,
            y0 + rib["main_spar_od_mm"] / 2.0 + 4.0,
            f"{rib['rib_id']}_c{rib['chord_mm']:.0f}mm_NACA{rib['naca_code']}",
            3.5,
        )
        y_cursor -= 74.0

    # 3. Bulkheads F1-F5 on layer 3_FUSELAGE_BULKHEADS
    bh_positions = [
        (485.0, 380.0),
        (640.0, 380.0),
        (485.0, 175.0),
        (765.0, 175.0),
        (485.0, 20.0),
    ]
    for bh, (bx, by) in zip(schedule["laser_cut_fuselage_bulkheads"], bh_positions):
        bw = bh["width_mm"]
        bh_h = bh["height_mm"]
        chamfer = min(28.0, bw * 0.14)
        oct_pts = [
            (bx + chamfer, by),
            (bx + bw - chamfer, by),
            (bx + bw, by + chamfer),
            (bx + bw, by + bh_h - chamfer),
            (bx + bw - chamfer, by + bh_h),
            (bx + chamfer, by + bh_h),
            (bx, by + bh_h - chamfer),
            (bx, by + chamfer),
            (bx + chamfer, by),
        ]
        for i in range(len(oct_pts) - 1):
            add_line("3_FUSELAGE_BULKHEADS", oct_pts[i][0], oct_pts[i][1], oct_pts[i + 1][0], oct_pts[i + 1][1])
        add_text("4_LABELS", bx + 5.0, by + bh_h + 4.0, f"{bh['bulkhead_id']}_X{bh['station_x_mm']:.0f}mm", 3.5)

    dxf.extend(["0", "ENDSEC", "0", "EOF\n"])
    out_dxf_path.write_text("\n".join(dxf), encoding="utf-8")


def generate_all_cnc_and_arduplane_exports(cad_dir: Path = CAD_DIR) -> dict:
    params_path = cad_dir / "design_params_sar.json"
    params = json.loads(params_path.read_text(encoding="utf-8"))

    schedule = build_cnc_cut_schedule(params)
    svg_path = cad_dir / "finlab02_foam_ribs_and_bulkheads_1to1.svg"
    dxf_path = cad_dir / "finlab02_foam_ribs_and_bulkheads_1to1.dxf"
    json_path = cad_dir / "cnc_foam_and_carbon_cut_schedule.json"
    param_path = cad_dir / "ark_fpv_arduplane_45_sar_jet.param"

    export_svg_cut_sheet(schedule, svg_path)
    export_dxf_cut_sheet(schedule, dxf_path)
    json_path.write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
    param_profile = generate_arduplane_ark_fpv_param_profile(export_path=str(param_path))

    return {
        "svg_path": str(svg_path),
        "dxf_path": str(dxf_path),
        "schedule_json_path": str(json_path),
        "arduplane_param_path": str(param_path),
        "rib_template_count": len(schedule["wing_and_tail_hotwire_ribs"]),
        "bulkhead_count": len(schedule["laser_cut_fuselage_bulkheads"]),
        "carbon_tube_sku_count": len(schedule["carbon_tube_cut_schedule"]),
        "mouldless_airframe_cost_usd": schedule["total_mouldless_airframe_material_cost_usd"],
        "arduplane_parameter_count": param_profile["parameter_count"],
    }


if __name__ == "__main__":
    summary = generate_all_cnc_and_arduplane_exports()
    print("===================================================================================")
    print("  FIN-LAB-02 ARCTIC FAST-SAR JET // 1:1 CNC CUT-SHEET & ARDUPLANE 4.5+ EXPORT PACK")
    print("===================================================================================")
    print(f"  1:1 Vector SVG Sheet : {summary['svg_path']} ({summary['rib_template_count']} Ribs + {summary['bulkhead_count']} Bulkheads)")
    print(f"  1:1 AutoCAD R12 DXF  : {summary['dxf_path']} (Millimeter units, 4 CNC/Laser layers)")
    print(f"  Carbon/Foam Schedule : {summary['schedule_json_path']} (${summary['mouldless_airframe_cost_usd']:.2f} shell materials)")
    print(f"  ArduPlane 4.5+ Param : {summary['arduplane_param_path']} ({summary['arduplane_parameter_count']} parameters)")
    print("===================================================================================")
