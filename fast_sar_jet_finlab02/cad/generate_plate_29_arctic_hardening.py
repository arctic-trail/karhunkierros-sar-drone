#!/usr/bin/env python3
"""
Deterministic Vector/Raster Engineering Plate Generator for Plate 29:
  - docs/images/sar_design_29_dorsal_surge_and_20_arctic_protections_v2.jpg

Combines:
  1. Dorsal Semi-Buried S-Duct Compressor Stall & Surge Prevention (+0 EUR, +12 g, 0 servos)
  2. Coupled Mountain-Wave Gust Window [V_B,min, V_B,max], Cold-Air V_EAS <= 102 m/s Ceiling & Katabatic Escape
  3. 3D OpenCASCADE STL Airframe Callout of Icing, Slush, Hinge-Wipe, Prop 1P & Cryogenic Fuel Protections
  4. Positively Capped 4 mm Pitot Sump, TAT Adiabatic Ram Subtraction, Layer-Mean Baro & Flat-Light/Substorm Fusion
"""

import os
import pathlib
from PIL import Image, ImageDraw, ImageFont
from rasterize_cad_reference_views import load_stl_with_clear_lambda_apex, render_panel, STL_PATH

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_JPG = REPO_ROOT / "docs" / "images" / "sar_design_29_dorsal_surge_and_20_arctic_protections_v3.jpg"

FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def fnt(size: int, bold: bool = False):
    path = FONT_BOLD if bold else FONT_REG
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_badge(d: ImageDraw.ImageDraw, cx: int, cy: int, text: str, bg=(255, 109, 0), r: int = 12):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg, outline=(255, 255, 255), width=2)
    f = fnt(11, bold=True)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2, cy - th / 2 - 1), text, font=f, fill=(255, 255, 255))


def draw_card(
    d: ImageDraw.ImageDraw,
    box,
    title: str,
    lines: list[str],
    border=(0, 212, 255),
    bg=(8, 22, 42),
    title_col=(0, 230, 255),
    title_sz=14,
    body_sz=12,
):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=7, fill=bg, outline=border, width=2)
    ft = fnt(title_sz, bold=True)
    fb = fnt(body_sz, bold=False)
    d.text((x0 + 10, y0 + 7), title, font=ft, fill=title_col)
    cy = y0 + 7 + title_sz + 5
    for ln in lines:
        d.text((x0 + 10, cy), ln, font=fb, fill=(222, 236, 252))
        cy += body_sz + 4


def main():
    W, H = 2400, 1500
    im = Image.new("RGB", (W, H), (6, 14, 26))
    d = ImageDraw.Draw(im)

    # Top Title Banner
    d.rectangle([18, 14, W - 18, 68], fill=(10, 28, 54), outline=(0, 212, 255), width=2)
    d.text(
        (34, 22),
        "PLATE 29 // DORSAL S-DUCT COMPRESSOR SURGE GUARD & 20 EXTREME-ARCTIC PROTECTIONS (v0.1 DESIGN FREEZE)",
        font=fnt(20, bold=True),
        fill=(0, 235, 255),
    )
    d.text(
        (34, 46),
        "3-Iteration First-Principles Physics Synthesis | +18.50 EUR Total Hardware Delta | +39 g (+0.26% MTOW) | 0 Added Servos | Status: CONVERGED_V0_1_FROZEN_FOR_FLIGHT_TEST",
        font=fnt(13, bold=True),
        fill=(140, 255, 190),
    )

    panels = [
        (18, 80, 1188, 775, "1. DORSAL S-DUCT COMPRESSOR STALL & SURGE GUARD (+0 EUR, +12 g, 0 SERVOS)"),
        (1212, 80, 2382, 775, "2. COUPLED GUST WINDOW [V_B,min, V_B,max], COLD V_EAS CEILING & KATABATIC ESCAPE (#9, #10, #16, #19B)"),
        (18, 795, 1188, 1484, "3. 3D STL AIRFRAME MAP: ICING, HINGE-WIPE, PROP 1P & CRYOGENIC FUEL (#2-#6, #13, #14, #17, #18, #20)"),
        (1212, 795, 2382, 1484, "4. CAPPED 4 mm PITOT SUMP, TAT RAM DECONVOLUTION, INVERSION BARO & WHITEOUT VIO (#1, #7, #8, #11, #12, #15, #19A)"),
    ]
    for x0, y0, x1, y1, title in panels:
        d.rectangle([x0, y0, x1, y1], fill=(9, 20, 36), outline=(0, 190, 245), width=2)
        for gx in range(x0 + 40, x1, 40):
            d.line([(gx, y0 + 42), (gx, y1 - 8)], fill=(13, 30, 52), width=1)
        for gy in range(y0 + 42, y1 - 8, 40):
            d.line([(x0 + 8, gy), (x1 - 8, gy)], fill=(13, 30, 52), width=1)
        d.rectangle([x0 + 3, y0 + 3, x1 - 3, y0 + 38], fill=(12, 34, 64), outline=(0, 180, 235), width=1)
        d.text((x0 + 14, y0 + 11), title, font=fnt(15, bold=True), fill=(0, 235, 255))

    # =========================================================================
    # PANEL 1: DORSAL S-DUCT INTAKE & COMPRESSOR SURGE GUARD CUTAWAY
    # =========================================================================
    d.rounded_rectangle([40, 132, 1165, 485], radius=8, fill=(7, 17, 31), outline=(35, 85, 135), width=1)
    # Fuselage dorsal contour
    d.polygon([(70, 405), (1130, 405), (1130, 470), (70, 470)], fill=(22, 48, 78), outline=(90, 150, 210))
    d.text((515, 432), "DORSAL FUSELAGE SPINE (XPS FOAM KEPT < 54 C BY PYROGEL FIREWALL & PURGE)", font=fnt(12, bold=True), fill=(180, 215, 245))
    # Forward Recovery Parachute Bay & Fire bulkhead at X=608 mm
    d.rectangle([75, 408, 378, 466], fill=(16, 40, 68), outline=(0, 212, 255), width=1)
    d.text((92, 430), "Forward Recovery Chute Bay (X = 542.7 mm)", font=fnt(12, bold=True), fill=(140, 230, 255))
    d.rectangle([380, 405, 404, 470], fill=(255, 145, 30), outline=(255, 230, 150), width=2)
    d.text((380, 384), "X=608mm 10mm Pyrogel Firewall (#6)", font=fnt(11, bold=True), fill=(255, 200, 95))

    # 22 mm Boundary-Layer Diverter Channel (left of firewall)
    d.polygon([(75, 362), (365, 362), (365, 384), (75, 384)], fill=(10, 32, 58), outline=(0, 212, 255))
    d.text((84, 366), "22 mm Boundary-Layer Diverter Stand-Off", font=fnt(11, bold=True), fill=(0, 230, 255))

    # S-Duct Outer Cowling & Inner Flow Channel
    d.polygon(
        [(235, 235), (535, 208), (980, 208), (980, 345), (535, 345), (235, 355), (235, 322), (505, 298), (505, 258), (235, 260)],
        fill=(32, 65, 102),
        outline=(130, 195, 250),
    )
    d.polygon([(235, 260), (520, 242), (585, 242), (585, 327), (520, 327), (235, 338)], fill=(14, 42, 74), outline=(0, 215, 255), width=2)

    # 8 W Heated Carbon-Veil Intake Lip (X=520 mm)
    d.ellipse([222, 244, 252, 278], fill=(255, 90, 30), outline=(255, 220, 120), width=2)
    d.ellipse([222, 324, 252, 356], fill=(255, 90, 30), outline=(255, 220, 120), width=2)
    d.text((62, 245), "8 W Carbon-Veil Heated Lip", font=fnt(12, bold=True), fill=(255, 150, 70))
    d.text((62, 262), "(X = 520 mm, Zero Ice Slugs)", font=fnt(11), fill=(235, 210, 190))

    # Passive Spring-Loaded Blow-In Suction Louvers (2x 45x30 mm)
    d.polygon([(355, 224), (435, 216), (428, 248), (350, 238)], fill=(24, 235, 145), outline=(255, 255, 255), width=2)
    d.text((310, 142), "2x 45x30 mm Passive Blow-In Cheek Louvers", font=fnt(13, bold=True), fill=(24, 245, 155))
    d.text((310, 160), "• Crack open passively when dP < -350 Pa (TOGA @ 25.5 m/s)", font=fnt(11), fill=(215, 240, 230))
    d.text((310, 176), "• Cuts low-speed lip separation DC60 by -78% (0.175 -> 0.129)", font=fnt(11), fill=(215, 240, 230))
    d.text((310, 192), "• Sucks flush > 45 m/s cruise (+0 EUR, +12 g, 0 servos)", font=fnt(11), fill=(215, 240, 230))
    d.line([(395, 208), (395, 227)], fill=(24, 245, 155), width=2)

    # 10 mm Radial Bypass FOD Screen (ahead of impeller)
    d.rounded_rectangle([535, 250, 568, 319], radius=10, fill=(45, 90, 130), outline=(255, 215, 70), width=2)
    d.text((545, 354), "10 mm Radial-Bypass FOD Mesh (Anti-Snow Plug)", font=fnt(11, bold=True), fill=(255, 215, 70))

    # JetCat P100-RX-BL / Xicoy X132 Engine Body (X=710..975 mm)
    d.rounded_rectangle([585, 234, 915, 334], radius=8, fill=(195, 85, 30), outline=(255, 220, 160), width=2)
    d.text((612, 254), "JETCAT P100-RX-BL / XICOY X132 (100-132 N)", font=fnt(13, bold=True), fill=(255, 255, 255))
    d.text((612, 274), "Centrifugal Impeller (154k RPM) + Starter Auto-Purge", font=fnt(11), fill=(255, 235, 210))
    d.text((612, 290), "Surge Margin SM = +12.3% (> +11% Floor, 0 Surges)", font=fnt(11, bold=True), fill=(150, 255, 185))

    # 304SS + 10 mm Aerogel Exhaust Trough & Warm Fuel Vent at X=980 mm
    d.polygon([(915, 240), (1135, 228), (1135, 340), (915, 328)], fill=(95, 110, 130), outline=(255, 190, 90), width=2)
    d.text((930, 260), "304SS + 10mm Aerogel", font=fnt(12, bold=True), fill=(255, 225, 160))
    d.text((930, 278), "Ejector Deck (X=975..1220)", font=fnt(11), fill=(230, 235, 245))
    d.ellipse([932, 326, 952, 346], fill=(24, 235, 145), outline=(255, 255, 255), width=2)
    d.text((875, 354), "X=980mm +35 C Warm BL Fuel Vent (#2)", font=fnt(11, bold=True), fill=(24, 245, 155))

    draw_card(
        d,
        (40, 500, 595, 760),
        "COUPLED DC60(alpha, beta, V_IAS) SURGE-MARGIN PHYSICS",
        [
            "• Baseline Unmitigated Risk: At 25.5 m/s slowed drop pass + 11 deg AoA",
            "  + 6 deg crosswind beta, dorsal lip separation raises DC60 -> 0.241,",
            "  collapsing centrifugal surge margin below 8% during a 100% TOGA step.",
            "• Hardware + Software Solution (+0 EUR, +12 g, 0 Servos):",
            "  1. Passive 2x 45x30 mm cheek louvers open at dP < -350 Pa (-78% lip DC60).",
            "  2. 8 W lip carbon-veil heater + 10 mm radial FOD screen bypass gap.",
            "  3. 400 Hz DC60 Slew Limiter modulates throttle ramp du/dt (25%/s -> 15%/s)",
            "     whenever DC60 > 0.11, holding Surge Margin SM = +12.3% (0 Stalls).",
            "  4. Dynamic 22% Flight-Idle Floor (52k RPM) avoids 1.35 s spool-lag knee.",
        ],
        border=(24, 235, 145),
    )
    draw_card(
        d,
        (610, 500, 1165, 760),
        "POST-SHUTDOWN 'CHIMNEY' HEAT-SOAK & INSECT PITOT GUARD (#6, #7)",
        [
            "• #6 Post-Shutdown Buoyant Heat-Soak Interlock (+22 C Summer / Loiter):",
            "  When turbine stops after 680 C dash, ram cooling drops to zero and",
            "  buoyant core heat rises forward toward XPS foam (78 C limit) & nylon",
            "  recovery chute (X = 542.7 mm). Fix: Starter BLDC auto-cooldown purge",
            "  runs until EGT < 95 C + 10 mm Pyrogel firewall at X = 608 mm (<54 C).",
            "• #7 Summer 'Rakka' (Blackfly Swarm) Pitot Chitin-Baking Guard:",
            "  Running the 35 W Pitot heater in +20 C bog insect swarms bakes chitin",
            "  into a permanent carbon plug. Fix: Thermostatic heater cutoff when",
            "  deconvolved (T_SAT - 2.0 C) > +4.0 C + year-round SYNTH_IAS backup.",
        ],
        border=(255, 180, 50),
        title_col=(255, 205, 90),
    )

    # =========================================================================
    # PANEL 2: COUPLED GUST WINDOW [V_B,min, V_B,max], COLD V_EAS & KATABATIC ESCAPE
    # =========================================================================
    gx0, gy0, gx1, gy1 = 1300, 150, 2340, 445
    d.rectangle([1235, 132, 2360, 485], fill=(7, 17, 31), outline=(35, 85, 135), width=1)
    d.line([(gx0, gy1), (gx1, gy1)], fill=(180, 210, 240), width=2)
    d.line([(gx0, gy0), (gx0, gy1)], fill=(180, 210, 240), width=2)

    def vx(v_mps):
        return int(gx0 + ((v_mps - 15.0) / 115.0) * (gx1 - gx0))

    def ny(n_g):
        return int(gy1 - ((n_g - 0.0) / 10.0) * (gy1 - gy0))

    for v_tick in (20, 33, 46, 60, 80, 92.7, 102, 111, 122):
        xp = vx(v_tick)
        d.line([(xp, gy0), (xp, gy1)], fill=(18, 38, 64), width=1)
        d.text((xp - 14, gy1 + 6), f"{v_tick:g}", font=fnt(11, bold=True), fill=(190, 215, 240))
    d.text((1680, gy1 + 23), "Airspeed V (m/s TAS / EAS) — Pratt Gust Load Factor n_z (G)", font=fnt(12, bold=True), fill=(0, 225, 255))

    for n_tick, y_off in ((0, -7), (2, -7), (3.5, 2), (3.8, -13), (5.7, -7), (8, -7), (9.4, -7)):
        yp = ny(n_tick)
        col = (255, 80, 80) if n_tick in (3.8, 5.7) else ((24, 235, 145) if n_tick == 3.5 else (18, 38, 64))
        d.line([(gx0, yp), (gx1, yp)], fill=col, width=2 if n_tick in (3.5, 3.8, 5.7) else 1)
        d.text((gx0 - 52, yp + y_off), f"{n_tick:g} G", font=fnt(11, bold=True), fill=(220, 235, 250))

    # Safe rough-air operating window [V_B,min = 24.4, V_B,max = 33..46 m/s]
    d.rectangle([vx(24.4), ny(3.5), vx(46.0), gy1], fill=(12, 72, 52), outline=(24, 235, 145), width=2)
    d.text((vx(25.0), ny(2.25)), "SAFE ROUGH-AIR GUST WINDOW", font=fnt(11, bold=True), fill=(120, 255, 190))
    d.text((vx(25.0), ny(1.65)), "[V_B,min=24.4 .. V_B,max=33-46 m/s]", font=fnt(11, bold=True), fill=(220, 255, 235))
    d.text((vx(25.0), ny(1.05)), "Peak Rotor Load Clamped <= 3.50 G", font=fnt(11), fill=(220, 255, 235))

    # Cold-air V_EAS <= 102 m/s ceiling at -35 C (placed cleanly in lower-right of chart y=ny(4.8)..gy1)
    d.rectangle([vx(92.7), gy0, vx(122.1), gy1], fill=(52, 18, 28), outline=(255, 90, 90), width=2)
    d.rounded_rectangle([vx(93.2), ny(4.7), vx(121.6), ny(1.1)], radius=6, fill=(75, 20, 32), outline=(255, 120, 120), width=2)
    d.text((vx(94.0), ny(4.45)), "-35 C V_EAS CEILING (#19B)", font=fnt(11, bold=True), fill=(255, 165, 165))
    d.text((vx(94.0), ny(3.85)), "At -35 C (rho/rho0 = 1.210):", font=fnt(11), fill=(255, 225, 225))
    d.text((vx(94.0), ny(3.25)), "111 TAS = 122.1 EAS (+21% q)", font=fnt(11, bold=True), fill=(255, 190, 190))
    d.text((vx(94.0), ny(2.65)), "Dual V_EAS <= 102 m/s clamp", font=fnt(11, bold=True), fill=(140, 255, 190))
    d.text((vx(94.0), ny(2.05)), "caps TAS <= 92.7 m/s (334 km/h)", font=fnt(11, bold=True), fill=(140, 255, 190))

    # Unclamped 7.6 m/s rotor gust load line: n = 1 + 0.0758 * V_TAS
    pts_gust = [(vx(v), ny(min(9.8, 1.0 + 0.0758 * v))) for v in range(20, 115, 5)]
    d.line(pts_gust, fill=(255, 95, 45), width=4)
    d.ellipse([vx(111) - 7, ny(9.41) - 7, vx(111) + 7, ny(9.41) + 7], fill=(255, 50, 50), outline=(255, 255, 255), width=2)
    d.rounded_rectangle([vx(36), ny(9.6), vx(91), ny(8.35)], radius=5, fill=(45, 16, 20), outline=(255, 110, 75), width=1)
    d.text((vx(37.5), ny(9.35)), "Unclamped 7.6 m/s Rotor Gust @ 111 m/s", font=fnt(12, bold=True), fill=(255, 145, 100))
    d.text((vx(37.5), ny(8.80)), "= 7.91-9.41 G in 45 ms (> 3.8 G limit!)", font=fnt(11, bold=True), fill=(255, 210, 190))
    d.ellipse([vx(33.0) - 7, ny(3.50) - 7, vx(33.0) + 7, ny(3.50) + 7], fill=(24, 245, 155), outline=(255, 255, 255), width=2)

    draw_card(
        d,
        (1235, 500, 1790, 760),
        "#9 & #19B: DYNAMIC GUST WINDOW & -35 C V_EAS CEILING",
        [
            "• #9 Mountain-Wave Rotor Gust (U_gust = 7.6 m/s, mu_g = 19.6, K_g = 0.711):",
            "  Because wing chord c = 0.294 m is traversed in 2.6 ms at 111 m/s,",
            "  45 ms gust rise outruns 25 ms KST X10 servos (unclamped 7.9-9.4 G).",
            "  Fix: 20 Hz turbulent-air speed clamp V_MO,gust <= V_B,max (~33-46 m/s)",
            "  keeps load <= 3.50 G; triggers 8 km (2*lambda) Scorer lee rotor standoff.",
            "• #19B Dual High-Speed Ceiling (V_TAS <= 111 m/s AND V_EAS <= 102 m/s):",
            "  Prevents +21% dynamic-pressure (q) & flutter overload in -35 C dense",
            "  polar air by automatically capping sea-level cold dash at 92.7 m/s TAS.",
        ],
        border=(0, 212, 255),
    )
    draw_card(
        d,
        (1805, 500, 2360, 760),
        "#10 KATABATIC ESCAPE & #16 POST-DROP +0.50G UNLOAD",
        [
            "• #10 Katabatic Fell Downdraft (-8.0 m/s vs +6.82 m/s Max Climb):",
            "  Standard TECS altitude-hold pitches up to alpha_prot and stalls in a",
            "  60 deg escape turn (+41% stall speed). Fix: Freezes TECS altitude",
            "  integrator when throttle==100% & h_dot < 0, sets TECS_SPDWEIGHT = 2.0,",
            "  clamps escape bank |phi| <= 30 deg (+7% V_S1), turns 90 deg cross-slope.",
            "• #16 Post-Release +0.503 G Mass-Step & Canopy Snatch Gate:",
            "  5.0 kg drop jumps n_z = 14.95/9.95 = +1.503 G; 400 Hz -2.12 deg pitch",
            "  unload + bumpless TECS mass reschedule & V_IAS+0.65*U_g <= 30 m/s gate.",
        ],
        border=(24, 235, 145),
    )

    # =========================================================================
    # PANEL 3: 3D STL AIRFRAME CALLOUT MAP (ZERO OVERLAP, ZERO CROSSED LEADERS)
    # =========================================================================
    # Render 3D STL in the central corridor (x: 395..810, y: 845..1345) at scale=0.235
    # With yaw=-145 deg, the TAIL is on the LEFT (x~475) and NOSE is on the RIGHT (x~720).
    tris = load_stl_with_clear_lambda_apex(STL_PATH)
    proj3 = render_panel(
        d,
        tris,
        (395, 845, 810, 1345),
        yaw_deg=-145.0,
        pitch_deg=18.0,
        scale=0.235,
        tint="ORANGE",
        draw_tail_edges=True,
    )

    # Left-side points on 3D model ordered top-to-bottom by screen Y
    p_tail_le = proj3((1375.0, -80.0, 115.0))[:2]
    p_wick = proj3((1520.0, 230.0, 25.0))[:2]
    p_wing_hinge = proj3((660.0, 620.0, 12.0))[:2]
    # Right-side points on 3D model ordered top-to-bottom by screen Y (fuel dorsal -> belly -> nose)
    p_fuel = proj3((580.0, -82.0, 35.0))[:2]
    p_belly = proj3((595.0, 0.0, -45.0))[:2]
    p_nose = proj3((15.0, 0.0, 0.0))[:2]

    callouts_p3 = [
        # Left column boxes (x: 34..395) -> point directly to Tail / Aft points on Left of 3D model
        (
            (34, 848, 395, 964),
            p_tail_le,
            "13",
            "#4 & #13 FINSTAD 4 mm TAIL 12 W",
            [
                "• 4mm tail LE ices 9x faster in 10um fog",
                "• 12W tail + 15W wing + 8W lip = 35W bus",
                "• Tail-root KST X10 (<55mm rod, 0.0 CTE)",
            ],
            (255, 130, 60),
        ),
        (
            (34, 976, 395, 1092),
            p_wick,
            "3",
            "#3 1 MOhm BUS & 4x P-STATIC WICKS",
            [
                "• Dry -30C snow charges carbon to 15-30 kV",
                "• Common 1 MOhm ground bus + 4x 35mm",
                "  carbon trailing-tip corona wicks (+3 EUR)",
            ],
            (190, 150, 255),
        ),
        (
            (34, 1104, 395, 1220),
            p_wing_hinge,
            "17",
            "#17 20s HINGE RUNBACK ICE-WIPE",
            [
                "• Unwiped 0.3mm bridge = 3.15 N*m lock",
                "  (3.21x KST X10 stall torque of 0.98 N*m!)",
                "• PTFE seal + 0.5s +/-4 deg wipe -> 0.08 N*m",
            ],
            (0, 225, 255),
        ),
        # Right column boxes (x: 810..1172) -> ordered top-to-bottom matching screen Y (zero crossed lines)
        (
            (810, 848, 1172, 964),
            p_fuel,
            "14",
            "#14 & #20 4 mm FUEL & 0.12% DiEGME",
            [
                "• 4mm FEP/Viton suction line: -16x viscous",
                "  dP at -35C (102 -> 6.38 kPa) + 2.5s shed",
                "• 0.12% DiEGME + warm +25C bay filter",
            ],
            (24, 235, 145),
        ),
        (
            (810, 976, 1172, 1092),
            p_belly,
            "5",
            "#5 SLUSH CAM & t=45s MICRO-PULSE",
            [
                "• PTFE knife-edge lip + 4:1 cam (>120 N)",
                "• Automated t=45s (80m AGL) 0.4s pulse",
                "  shears 0 C slush before -6 C climb freeze",
            ],
            (255, 180, 50),
        ),
        (
            (810, 1104, 1172, 1220),
            p_nose,
            "18",
            "#18 FOLDING NOSE PROP 1P GUARD",
            [
                "• 1 frozen blade @ 4k-8k RPM = 132-526 N!",
                "• Krytox + PTFE pads + <=1,000 RPM/s ramp",
                "• <50ms 1P (>2.5G) ESC cut & 3x pulse-retry",
            ],
            (0, 225, 255),
        ),
    ]

    for box, target_pt, b_txt, title, lines, col in callouts_p3:
        bx0, by0, bx1, by1 = box
        anchor = (bx1 if bx1 < target_pt[0] else bx0, (by0 + by1) // 2)
        d.line([anchor, target_pt], fill=col, width=3)
        tx, ty = int(target_pt[0]), int(target_pt[1])
        d.ellipse([tx - 6, ty - 6, tx + 6, ty + 6], fill=col, outline=(255, 255, 255), width=2)
        draw_card(d, box, "     " + title, lines, border=col, title_col=col, title_sz=13, body_sz=11)
        draw_badge(d, bx0 + 18, by0 + 15, b_txt, bg=(220, 85, 20), r=11)

    draw_card(
        d,
        (34, 1352, 1172, 1472),
        "CUMULATIVE MASS, COST & SERVO DISPOSITION ACROSS ALL 20 PROTECTIONS",
        [
            "• Total Added Hardware Cost: +18.50 EUR (+2 EUR vent, +3 EUR wicks, +2 EUR cam/PTFE, +3 EUR 4mm PTFE Pitot sump, +4 EUR 4mm fuel line, +2.50 EUR hinge/prop PTFE)",
            "• Total Added Airframe Mass: +39 g (+0.26% of 14.95 kg MTOW: +12 g louvers, +5 g vent, +4 g wicks, +6 g Pitot sump, +8 g 4mm fuel line, +4 g PTFE seals)",
            "• Total Added Actuators / Servos: 0 Servos (100% passive pressure louvers, passive coaxial sump, and existing 4x KST X10 + starter BLDC software laws)",
        ],
        border=(24, 235, 145),
        title_col=(140, 255, 190),
    )

    # =========================================================================
    # PANEL 4: CAPPED 4 mm PITOT SUMP, TAT RAM DECONVOLUTION & WHITEOUT/MAG FUSION
    # =========================================================================
    d.rounded_rectangle([1235, 847, 2360, 1085], radius=8, fill=(7, 17, 31), outline=(0, 212, 255), width=2)
    d.text(
        (1252, 856),
        "#12 & #19A: 4 mm PTFE DOWNHILL PITOT LINE + POSITIVELY CAPPED 4 mm (1.5 mL) WATER-TRAP SUMP",
        font=fnt(14, bold=True),
        fill=(0, 235, 255),
    )

    d.rounded_rectangle([1255, 930, 1415, 970], radius=5, fill=(215, 95, 30), outline=(255, 225, 150), width=2)
    d.text((1265, 943), "35W Heated Pitot", font=fnt(12, bold=True), fill=(255, 255, 255))
    d.line([(1415, 950), (1695, 990)], fill=(0, 225, 255), width=8)
    d.text((1422, 922), "4 mm PTFE (>8 deg slope, 0 U-bends)", font=fnt(11, bold=True), fill=(180, 235, 255))
    # Upward dry branch to elevated MS4525DO
    d.line([(1695, 990), (1695, 905), (1795, 905)], fill=(24, 245, 155), width=7)
    d.rounded_rectangle([1795, 882, 2005, 932], radius=6, fill=(16, 68, 52), outline=(24, 245, 155), width=2)
    d.text((1808, 894), "Elevated MS4525DO I2C", font=fnt(12, bold=True), fill=(150, 255, 195))
    d.text((1808, 911), "Dry Gas Column (5.8 Pa)", font=fnt(11), fill=(220, 255, 235))

    # Downward Coaxial 4 mm Sump with Positive Quarter-Turn Ground Cap
    d.rounded_rectangle([1672, 990, 1718, 1055], radius=5, fill=(20, 55, 95), outline=(0, 225, 255), width=2)
    d.rectangle([1666, 1052, 1724, 1070], fill=(255, 180, 40), outline=(255, 255, 255), width=2)
    d.text((1740, 992), "Positively Capped 4 mm (1.5 mL) Sump (#19A):", font=fnt(12, bold=True), fill=(255, 210, 90))
    d.text((1740, 1010), "• 0.0 Pa in-flight ram bleed error (sealed cap)", font=fnt(11), fill=(225, 238, 252))
    d.text((1740, 1027), "• Avoids 342.4 Pa Young-Laplace pinning of open 0.3mm hole", font=fnt(11), fill=(225, 238, 252))
    d.text((1740, 1044), "• Mode C Zero-Variance (Var<0.5 Pa2) + EKF Wind Freeze", font=fnt(11, bold=True), fill=(140, 255, 190))

    draw_card(
        d,
        (1235, 1098, 1790, 1345),
        "#1 & #11: TAT RAM SUBTRACTION & INVERSION BARO",
        [
            "• #11 Adiabatic Ram Heating + Sensor Lag Deconvolution:",
            "  At 111 m/s dash, ram rise dT_ram = r*V^2/(2*c_p) = +5.53 C",
            "  makes -1.0 C freezing rain read +4.53 C on the probe,",
            "  which would falsely trigger the > +4.0 C summer insect",
            "  heater cutoff! Fix: Recovers T_SAT = T_probe - dT_ram + tau*dT/dt",
            "  and requires (T_SAT - 2.0 C) > +4.0 C before heater cutoff.",
            "• #1 & #11 Two-Point Layer-Mean Hypsometric Baro Altitude:",
            "  Fuses surface station T_surf (-35 C) and aircraft T_SAT",
            "  to correct +14.8 m cold-air baro over-reading & +15 K inversions.",
        ],
        border=(255, 180, 50),
        title_col=(255, 210, 95),
    )

    draw_card(
        d,
        (1805, 1098, 2360, 1345),
        "#8 & #15: FLAT-LIGHT LWIR VIO & 77.5 deg MAG GATE",
        [
            "• #15 Polar Flat-Light / Whiteout Optical Starvation:",
            "  Under 8/8 stratus over snow, visible contrast drops to 3.2%",
            "  (SNR = 3.6 < 8.0, 0 Starvis corners). Automatically switches",
            "  VIO to LWIR thermal micro-relief + wind-frozen airdata DR.",
            "• #15 77.5 deg Magnetic Dip (tan I = 4.51) & 1,000 nT Substorms:",
            "  1 deg roll tilt induces 4.51 deg yaw error; gates out RM3100",
            "  when |bank| > 8 deg or |dB_H| > 400 nT -> EKF3-GSF velocity yaw",
            "  + >40 twists/m power harness (<1 cm2 loop = <0.1 deg mag error).",
            "• #8 Midnight-Sun (0-12 deg) Specular Bog Glint Rejection Gate.",
        ],
        border=(190, 150, 255),
        title_col=(215, 185, 255),
    )

    draw_card(
        d,
        (1235, 1352, 2360, 1472),
        "ROUND-3 CONVERGENCE FILTER — SPECULATIVE ITEMS EXPLICITLY REJECTED TO PRESERVE SIMPLICITY",
        [
            "• Rejected #A (Heated Trailing-Edge Hinges / Bleed Piccolo Tubes, +25 W): Replaced by 0 EUR 20 s periodic +/-4 deg mechanical hinge-wipe (#17).",
            "• Rejected #B (Rotating Nose-Spinner Slip-Ring Heater, +45 g): Replaced by PTFE rest pads + <50 ms 1P (>2.5 G) vibration cut & 3x pulse-retry (#18).",
            "• Rejected #C (Active Electric Tank Heaters / Optical Ice-Crystal Sensors): Replaced by 0.12% v/v DiEGME (FSII) + warm +25 C avionics-bay filter (#20).",
        ],
        border=(0, 212, 255),
        title_col=(0, 235, 255),
    )

    OUT_JPG.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT_JPG, quality=95, optimize=True)
    print(f"Saved {OUT_JPG} ({OUT_JPG.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
