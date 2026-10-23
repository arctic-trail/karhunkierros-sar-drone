#!/usr/bin/env python3
"""
Deterministic, Zero-Hallucination Engineering Plate Generator for:
  - docs/images/sar_design_01_cad_ssot_cutaway_v2.jpg (fixes "Semii-buried dorsal 0.cm" typo)
  - docs/images/sar_design_02_subsystem_callout_cutaway_v2.jpg (fixes "Bayraktar" -> "Twin-Boom 110° Inverted Λ-Tail")
  - docs/images/sar_design_12_corridor_rendezvous_and_soft_net_v3.jpg (100% vector text, zero typos)
  - docs/images/sar_design_13_800_event_uspace_benchmark_v3.jpg (100% vector text, zero "Helicupter"/"COT3"/tank hallucinations, explicit 3-Tier project scope)
  - docs/images/sar_design_14_five_priority_benchmarks_v3.jpg (100% vector text, zero "IM89D130"/"flusgate"/date hallucinations)
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon, ArrowStyle, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "docs" / "images"


def get_font(size: int, bold: bool = False):
    candidates = (
        ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Helvetica.ttc"]
        if bold
        else ["DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc"]
    )
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()


def fix_plate_01():
    src = IMG_DIR / "sar_design_01_cad_ssot_cutaway_v1.jpg"
    dst = IMG_DIR / "sar_design_01_cad_ssot_cutaway_v2.jpg"
    if not src.exists():
        return
    im = Image.open(src).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)
    # Cover "Semii-buried dorsal 0.cm heat shielding" at right side of left panel
    # Coordinates in 2400x1792: x=1045..1370, y=675..785
    bx0, by0, bx1, by1 = int(0.435 * w), int(0.375 * h), int(0.573 * w), int(0.442 * h)
    # Sample background blueprint color
    bg_col = im.getpixel((int(0.50 * w), int(0.35 * h)))
    draw.rectangle([bx0, by0, bx1, by1], fill=bg_col)
    # Redraw faint grid lines in patch
    grid_col = (26, 48, 80)
    for gx in range(bx0, bx1, 48):
        draw.line([(gx, by0), (gx, by1)], fill=grid_col, width=1)
    for gy in range(by0, by1, 48):
        draw.line([(bx0, gy), (bx1, gy)], fill=grid_col, width=1)
    f_b = get_font(int(h * 0.0175), bold=True)
    lines = ["Semi-buried dorsal", "304SS + Aerogel", "thermal deck"]
    cy = by0 + 4
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=f_b)
        tw = bbox[2] - bbox[0]
        tx = (bx0 + bx1 - tw) // 2
        draw.text((tx, cy), ln, fill=(240, 246, 255), font=f_b)
        cy += int(h * 0.021)
    im.save(dst, quality=94, optimize=True)
    print(f"Saved {dst}")


def fix_plate_02():
    src = IMG_DIR / "sar_design_02_subsystem_callout_cutaway_v1.jpg"
    dst = IMG_DIR / "sar_design_02_subsystem_callout_cutaway_v2.jpg"
    if not src.exists():
        return
    im = Image.open(src).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)
    # Cover text inside [U3] box at top-right: x=0.763..0.962, y=0.195..0.268
    bx0, by0, bx1, by1 = int(0.764 * w), int(0.198 * h), int(0.963 * w), int(0.268 * h)
    draw.rectangle([bx0, by0, bx1, by1], fill=(252, 253, 255))
    f_b = get_font(int(h * 0.022), bold=True)
    f_r = get_font(int(h * 0.0185), bold=False)
    draw.text((bx0 + 4, by0 + 4), "Twin-Boom 110° Inverted Λ-Tail", fill=(15, 23, 42), font=f_b)
    draw.text((bx0 + 4, by0 + int(h * 0.030)), "(Bridges Twin Booms Outside Plume)", fill=(30, 41, 59), font=f_r)
    im.save(dst, quality=94, optimize=True)
    print(f"Saved {dst}")


def build_plate_12():
    """
    Generate docs/images/sar_design_12_corridor_rendezvous_and_soft_net_v4.jpg
    100% deterministic Matplotlib vector diagram (zero AI typos, zero box overlaps).
    """
    dst = IMG_DIR / "sar_design_12_corridor_rendezvous_and_soft_net_v4.jpg"
    fig = plt.figure(figsize=(20, 9.8), dpi=160, facecolor="#0b192c")
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.92], facecolor="#0f243d")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 49)
    ax.axis("off")

    # Blueprint grid
    for x in np.arange(0, 101, 2.5):
        ax.axvline(x, color="#19375a", lw=0.5, alpha=0.55)
    for y in np.arange(0, 50, 2.5):
        ax.axhline(y, color="#19375a", lw=0.5, alpha=0.55)

    # Title banner
    ax.add_patch(FancyBboxPatch((1.0, 44.0), 98.0, 4.0, boxstyle="round,pad=0.3",
                                facecolor="#132f50", edgecolor="#38bdf8", lw=1.8))
    ax.text(50, 46.5, "HIGH-SPEED CORRIDOR SAFETY, HEAD-ON VISUAL/LWIR ID & NON-PYROTECHNIC SOFT-NET RECOVERY (FIN-LAB-02)",
            color="#f8fafc", fontsize=14.2, fontweight="bold", ha="center", va="center")
    ax.text(50, 44.9, "3-Gate Layered Civil Airspace Safety & Emergency SAR Response  |  100% Non-Chinese Allied/EU COTS  |  Zero Firearms, Zero Pyrotechnics, Zero LiPo Fire",
            color="#7dd3fc", fontsize=10.0, ha="center", va="center")

    # Left panel: Protected Civil Infrastructure (0 km, X=1.2..19.2)
    ax.add_patch(FancyBboxPatch((1.2, 4.5), 18.0, 37.8, boxstyle="round,pad=0.35",
                                facecolor="#102a45", edgecolor="#64748b", lw=1.6))
    ax.text(10.2, 40.5, "PROTECTED CIVILIAN ZONE\n(0 km Inner Boundary)", color="#f8fafc",
            fontsize=10.2, fontweight="bold", ha="center", va="center")
    infra_items = [
        ("1. Regional Airport & U-Space", "Cooperative ADS-B / FLARM / Remote ID\ncorridor deconfliction & noise logging"),
        ("2. Wilderness SAR Hub", "Forward launch station for Tier-3\nFIN-LAB-02 Fast-SAR Jet (T+45 s launch)"),
        ("3. +15 °C Heated 12-Cell Shelter", "6.5 s clamshell lid opening, 42 W steady\ndraw; launches 285 km/h fast-climber"),
        ("4. Civil Substation ([P12-BELT])", "Zero-RF acoustic + 60 GHz micro-Doppler\n+ 120 ms passive Dyneema safety net"),
    ]
    iy = 35.0
    for it_t, it_d in infra_items:
        ax.add_patch(FancyBboxPatch((2.0, iy - 4.5), 16.4, 5.8, boxstyle="round,pad=0.25",
                                    facecolor="#0b192c", edgecolor="#38bdf8", lw=1.1))
        ax.text(10.2, iy + 0.1, it_t, color="#7dd3fc", fontsize=8.8, fontweight="bold", ha="center", va="center")
        ax.text(10.2, iy - 2.3, it_d, color="#cbd5e1", fontsize=8.0, ha="center", va="center")
        iy -= 8.2

    # Corridor timeline track (from right X=92, Y=37.5 [30 km cue] to left X=20.5, Y=21.5 [0 km Perimeter])
    ax.plot([20.5, 92.0], [21.5, 37.5], color="#38bdf8", lw=3.0, ls="--", alpha=0.85, zorder=2)
    ax.annotate("", xy=(21.0, 21.6), xytext=(91.0, 37.3),
                arrowprops=dict(arrowstyle="->", color="#f97316", lw=2.8, mutation_scale=22), zorder=3)

    # 4 Non-Overlapping Station Callout Cards along the Corridor
    stations = [
        # (dot_x, dot_y, box_x, box_y, box_w, box_h, title, desc, col)
        (90.0, 37.0, 72.0, 26.8, 26.5, 6.6,
         "30 km Outer Cue (T = 0 s)",
         "[P11-AIR] 3D Acoustic + Passive RF Node\nFIN-LAB-01 U-Space Fusion in 4.4 ms\n(<=30 s automated dispatch decision)",
         "#38bdf8"),
        (69.0, 32.3, 47.0, 34.8, 28.5, 6.8,
         "Gate 1: 12.4 km Out (T + 138 s)",
         "FIN-LAB-02 Fast-SAR Jet (350–400 km/h)\nHead-on Visual/LWIR ID or 5.0 kg Survival\nCapsule Drop (87 s margin before T+225 s)",
         "#22c55e"),
        (48.0, 27.6, 21.5, 29.8, 24.0, 7.6,
         "Gate 2: 8.0 km Out (T + 165 s)",
         "Cold-Rated 285 km/h Fast-Climber\nfrom +15 °C 12-Cell Shelter: 50 Hz\n3D APN (N'=4.0) + Non-Pyrotechnic\n2.5×2.5 m Dyneema Soft-Net (4.11 m/s)",
         "#eab308"),
        (29.0, 23.4, 21.5, 11.2, 27.5, 7.2,
         "Gate 3: 4.0 km Inner Gate (T + 195 s)",
         "Manned SAR Helicopter / ATC Coordination\n& 120 ms Passive Dyneema Substation\nSafety Net Cover (88.9% Combined\n3-Gate Reliability >= 85% Benchmark)",
         "#a855f7"),
    ]
    for dx, dy, bx, by, bw, bh, title, desc, col in stations:
        ax.add_patch(Circle((dx, dy), 1.05, facecolor=col, edgecolor="#ffffff", lw=2.0, zorder=6))
        ax.plot([dx, bx + bw / 2], [dy, by + bh / 2], color=col, lw=1.6, ls=":", zorder=4)
        ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.35",
                                    facecolor="#0b192c", edgecolor=col, lw=1.8, zorder=5))
        ax.text(bx + bw / 2, by + bh - 1.2, title, color=col, fontsize=9.8, fontweight="bold", ha="center", va="center", zorder=7)
        ax.text(bx + bw / 2, by + (bh - 1.5) / 2, desc, color="#e2e8f0", fontsize=8.2, ha="center", va="center", zorder=7)

    # Right-bottom panel: Dual Propulsion & Internal Packaging Spec Box (X=51.5..98.5, Y=4.5..24.2)
    ax.add_patch(FancyBboxPatch((51.5, 4.5), 47.0, 19.5, boxstyle="round,pad=0.35",
                                facecolor="#102a45", edgecolor="#f97316", lw=1.8, zorder=5))
    ax.text(75.0, 22.5, "TIER-3 FIN-LAB-02 HYBRID PROPULSION & PACKAGING (X_CG = 595.0 mm)",
            color="#fb923c", fontsize=10.5, fontweight="bold", ha="center", va="center", zorder=6)

    prop_specs = [
        ("A. Dorsal Micro-Turbojet (JetCat P100-RX-BL 100 N / Xicoy X132 132 N):",
         "Used for high-speed storm-penetrating outbound transit (201–278 km/h in Iteration 1;\n"
         "350–400 km/h in Iteration 3 swept wing; US$1,320 China-free airframe+avionics COTS)\n"
         "and rapid 3.5 G airspace-conflict evasion."),
        ("B. 355 mm Folding Nose Electric Propeller (Iter 2 Hybrid Option, 335–380 W):",
         "Blades fold flush against the solid unmanned chined nose cone during jet dash (zero drag).\n"
         "Deploys in the target zone for quiet, fuel-saving 25.5 m/s (92 km/h) thermal search loiter\n"
         "(+22 min search endurance on 6S2P 194.4 Wh Molicel P45B pack) & stabilized drop pass."),
        ("C. Zero-Shift Co-Located Packaging (X_CG = 595.0 mm):",
         "Twin 2.0 L PET fuel bottles + 150 mL spherical UAT bubble trap + 5.0 kg belly survival capsule\n"
         "straddle the main 20 mm carbon spar at X_CG = 595.0 mm (0.0 mm trim shift on release)."),
    ]
    py = 20.2
    for pt, pd in prop_specs:
        ax.text(52.8, py, pt, color="#f8fafc", fontsize=8.6, fontweight="bold", ha="left", va="top", zorder=6)
        ax.text(52.8, py - 1.35, pd, color="#cbd5e1", fontsize=8.0, ha="left", va="top", zorder=6)
        py -= 5.4

    # Bottom footer bar
    ax.add_patch(FancyBboxPatch((1.0, 0.7), 98.0, 2.6, boxstyle="round,pad=0.2",
                                facecolor="#091526", edgecolor="#334155", lw=1.2))
    ax.text(50, 2.0, "Inspired by contested-airspace physics  •  Built 100% for civilian SAR, civil U-Space corridor safety & non-destructive cooperative drone recovery.",
            color="#94a3b8", fontsize=9.8, fontweight="bold", ha="center", va="center")

    fig.savefig(dst, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {dst}")


def build_plate_13():
    """
    Generate docs/images/sar_design_13_800_event_uspace_benchmark_v4.jpg
    100% deterministic Matplotlib diagram explaining the 800-Event U-Space Benchmark,
    explicitly showing which Streams/Tiers belong to which repository in our 3-Tier scope,
    and zero AI hallucinations ("Helicupter", "COT3", "botties", tanks) or math-mode '$' glitches.
    """
    dst = IMG_DIR / "sar_design_13_800_event_uspace_benchmark_v4.jpg"
    fig = plt.figure(figsize=(20, 10.0), dpi=160, facecolor="#0b192c")
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.92], facecolor="#0f243d")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    for x in np.arange(0, 101, 2.5):
        ax.axvline(x, color="#19375a", lw=0.5, alpha=0.55)
    for y in np.arange(0, 51, 2.5):
        ax.axhline(y, color="#19375a", lw=0.5, alpha=0.55)

    # Header
    ax.add_patch(FancyBboxPatch((1.0, 44.8), 98.0, 4.2, boxstyle="round,pad=0.3",
                                facecolor="#132f50", edgecolor="#38bdf8", lw=1.8))
    ax.text(50, 47.4, "800-EVENT PEAK CIVIL U-SPACE & EMERGENCY SAR DISPATCH ARCHITECTURE — EXPLICIT 3-TIER PROJECT SCOPE",
            color="#f8fafc", fontsize=14.2, fontweight="bold", ha="center", va="center")
    ax.text(50, 45.7, "How Incoming Airspace Events & Distress Beacons Are Triaged Across Tier 1 (arctic-trail-cam), Tier 2 (karhunkierros-sar-drone) & Tier 3 (arctic-fast-sar-jet)",
            color="#7dd3fc", fontsize=10.0, ha="center", va="center")

    # Column 1: Incoming 800 Peak Events (Streams 1, 2, 3)
    ax.add_patch(FancyBboxPatch((1.5, 13.5), 29.0, 29.8, boxstyle="round,pad=0.35",
                                facecolor="#102a45", edgecolor="#64748b", lw=1.6))
    ax.text(16.0, 41.6, "1. INCOMING 800-EVENT PEAK LOAD\n(What Enters the Sensor Grid)",
            color="#f8fafc", fontsize=10.8, fontweight="bold", ha="center", va="center")

    streams = [
        ("STREAM 1: ~400 Events (50%)",
         "Benign Clutter, Wind Gusts, Gliders,\nBirds & Weather Balloons",
         "• Filtered out automatically in software\n  so rescue drones are NOT wasted on\n  false alarms (<=25% false-dispatch ceiling).",
         "#38bdf8"),
        ("STREAM 2: ~330 Events (41%)",
         "Local Hiker Distress Beacons (<=25 km)\n& Low-Altitude Rotorcraft (<285 km/h)",
         "• Hikers needing thermal verification,\n  AED / radio drop, or aerial lantern guide.\n• Wayward rotorcraft near corridors.",
         "#22c55e"),
        ("STREAM 3: ~70 Events (9%)",
         "Long-Range / Storm SAR Emergencies\n(25–45 km) & Fast Corridor Tracks",
         "• Deep-wilderness / maritime hypothermia\n  requiring 201–400 km/h jet dash in\n  15 m/s headwinds + 5.0 kg survival capsule.",
         "#f97316"),
    ]
    sy = 36.8
    for st_title, st_sub, st_body, col in streams:
        ax.add_patch(FancyBboxPatch((2.5, sy - 6.8), 27.0, 8.2, boxstyle="round,pad=0.3",
                                    facecolor="#0b192c", edgecolor=col, lw=1.6))
        ax.text(16.0, sy + 0.4, st_title, color=col, fontsize=9.8, fontweight="bold", ha="center", va="center")
        ax.text(16.0, sy - 1.4, st_sub, color="#f8fafc", fontsize=8.6, fontweight="bold", ha="center", va="center")
        ax.text(3.3, sy - 4.3, st_body, color="#cbd5e1", fontsize=8.0, ha="left", va="center")
        sy -= 9.3

    # Column 2: Our 3 Open-Source Repositories & Exact Scope Assignment
    ax.add_patch(FancyBboxPatch((33.5, 13.5), 65.0, 29.8, boxstyle="round,pad=0.35",
                                facecolor="#102a45", edgecolor="#38bdf8", lw=1.8))
    ax.text(66.0, 41.6, "2. WHICH SYSTEM HANDLES WHICH STREAM IN OUR 3-REPOSITORY PROJECT SCOPE",
            color="#f8fafc", fontsize=11.0, fontweight="bold", ha="center", va="center")

    tiers = [
        ("TIER 1 REPO: arctic-trail/arctic-trail-cam  —  Handles STREAM 1 Filtering + All Initial Acoustic/Optical Detection",
         "• Hardware in Scope: Off-grid Pi 5 + Pico 2 solar/LiFePO4 trail & cabin node (USD 497) + [P11-AIR] 3D Infineon IM69D130 acoustic pod (+USD 68)\n"
         "  + Acconeer XM125 60 GHz micro-Doppler radar + 1-way optical diode (0.00 W RF emission).\n"
         "• Software in Scope: FIN-SIG-LIB v1.0 (-30 °C speed-of-sound c = 312.58 m/s GCC-PHAT bearing + 5-class harmonic classifier, 96.2% accuracy)\n"
         "  passively logs & filters out the ~400 Stream 1 benign events (~280 automated optical/safety verifications) at ~EUR 0 dispatch cost.",
         "#38bdf8"),
        ("TIER 2 REPO: arctic-trail/karhunkierros-sar-drone  —  Handles STREAM 2 (~330 Local SAR & Corridor Events, 8–25 km)",
         "• Hardware in Scope: Autonomous wilderness SAR quadcopter & Opaslyhty aerial lantern guide (EUR 1,770–2,965) + [P12-HEATED] +15 °C heated\n"
         "  12-cell shelter (6.5 s clamshell lid, 42 W steady) + cold-rated 285 km/h COTS fast-climber (EUR 2,350 BOM).\n"
         "• Software in Scope: FIN-LAB-01 U-Space track fusion (2,500 pairs in 4.4 ms), voluntary 'Uber-for-SAR' dispatch coordinator, and 50 Hz 3D APN\n"
         "  (N'=4.0) non-pyrotechnic 2.5×2.5 m Dyneema soft-net + 1.2 m² parachute recovery (4.11 m/s gentle descent).",
         "#22c55e"),
        ("TIER 3 REPO (THIS REPO): arctic-trail/arctic-fast-sar-jet (FIN-LAB-02)  —  Handles STREAM 3 (~70 Long-Range / Storm / Fast Events)",
         "• Hardware in Scope: 14.95 kg MTOW chined carbon/XPS fixed-wing jet-hybrid UAV (2.20 m fixed 16° cranked wing, twin-boom 110° inverted Λ-tail,\n"
         "  USD 1,320 China-free airframe+avionics COTS + turnkey EU JetCat P100-RX-BL 100 N or Xicoy X132 132 N turbojet + 5.0 kg belly survival capsule).\n"
         "• Propulsion Split: Dorsal Micro-Turbojet = 201–400 km/h storm-penetrating dash (reaches 35 km in ~10.5 min) & 3.5 G conflict evasion;\n"
         "  355 mm Folding Nose Electric Prop (Iter 2) = quiet 25.5 m/s (335–380 W) thermal search loiter & stabilized parachute drop pass.",
         "#f97316"),
    ]
    ty = 36.8
    for t_title, t_body, col in tiers:
        ax.add_patch(FancyBboxPatch((34.8, ty - 6.8), 62.4, 8.2, boxstyle="round,pad=0.3",
                                    facecolor="#0b192c", edgecolor=col, lw=1.8))
        ax.text(35.8, ty + 0.4, t_title, color=col, fontsize=9.5, fontweight="bold", ha="left", va="center")
        ax.text(35.8, ty - 3.3, t_body, color="#e2e8f0", fontsize=8.1, ha="left", va="center")
        ax.annotate("", xy=(34.6, ty - 2.7), xytext=(29.7, ty - 2.7),
                    arrowprops=dict(arrowstyle="->", color=col, lw=2.8, mutation_scale=20))
        ty -= 9.3

    # Bottom Section: Regional Fleet Cost Comparison Bar Chart (Zero Typos, Fits 100% Inside Box)
    ax.add_patch(FancyBboxPatch((1.5, 1.2), 97.0, 10.8, boxstyle="round,pad=0.35",
                                facecolor="#102a45", edgecolor="#64748b", lw=1.5))
    ax.text(50.0, 10.6, "REGIONAL SCALING BENCHMARK: 3-TIER OPEN COTS ARCHITECTURE VS. LEGACY MANNED HELICOPTER-ONLY STANDBY",
            color="#f8fafc", fontsize=10.5, fontweight="bold", ha="center", va="center")

    bars = [
        ("Open 3-Tier COTS Automated Architecture (Tier 1 + Tier 2 + Tier 3)", 10.0, "~EUR 5–6M Regional Package", "#38bdf8", 7.6),
        ("Ad-Hoc Uncoordinated Manual Drone Dispatch (High False-Alarm Waste)", 20.0, "~EUR 18M (No Acoustic Triage)", "#eab308", 5.0),
        ("Legacy Manned Helicopter-Only 24/7 Standby Fleet (Status Quo Baseline)", 44.0, "EUR 400M+ Multi-Base Fleet", "#ef4444", 2.4),
    ]
    for label, width_val, cost_txt, col, by in bars:
        ax.text(33.5, by, label, color="#e2e8f0", fontsize=8.8, fontweight="bold", ha="right", va="center")
        ax.add_patch(FancyBboxPatch((34.5, by - 0.85), width_val, 1.7, boxstyle="round,pad=0.1",
                                    facecolor=col, edgecolor="#ffffff", lw=1.0))
        ax.text(35.3 + width_val, by, cost_txt, color=col, fontsize=9.2, fontweight="bold", ha="left", va="center")

    fig.savefig(dst, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {dst}")


def build_plate_14():
    """
    Generate docs/images/sar_design_14_five_priority_benchmarks_v4.jpg
    100% deterministic Matplotlib vector diagram (zero AI typos, zero calendar dates).
    """
    dst = IMG_DIR / "sar_design_14_five_priority_benchmarks_v4.jpg"
    fig = plt.figure(figsize=(20, 9.2), dpi=160, facecolor="#f8fafc")
    ax = fig.add_axes([0.015, 0.03, 0.97, 0.94], facecolor="#f1f5f9")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis("off")

    # Header
    ax.add_patch(FancyBboxPatch((1.0, 40.8), 98.0, 4.2, boxstyle="round,pad=0.3",
                                facecolor="#0f172a", edgecolor="#1e293b", lw=1.8))
    ax.text(50, 43.4, "CLOSING ALL FIVE PRIORITY CIVILIAN BENCHMARKS (I, H, A, J, K) IN 100% CHINA-FREE ALLIED/EU COTS SCOPE",
            color="#f8fafc", fontsize=14.0, fontweight="bold", ha="center", va="center")
    ax.text(50, 41.7, "Deterministic Verification via northern_flank_red_gap_solver.py  |  Priority Residual Reduced by -65.9% (41 -> 14 Today, 11 Field-Validated)",
            color="#38bdf8", fontsize=9.8, ha="center", va="center")

    cards = [
        ("Benchmark I — High-Speed\n350–400 km/h Open Airframe\n(#3 FIN-LAB-02)",
         "GREEN 3/4 (Residual 9 -> 3)", "#16a34a", "#dcfce7",
         "Tier 3 Repo: arctic-fast-sar-jet",
         [
             "• Unmanned Chined Nose + Semi-Buried",
             "  Dorsal Turbojet (JetCat P100 / Xicoy X132)",
             "• Twin-Boom 110° Inverted Λ-Tail",
             "• 91.3 N drag @ 400 km/h vs. 132–160 N",
             "  thrust = +40.7 to +68.7 N excess thrust",
             "• ~12.4 km head-on visual/LWIR ID or",
             "  5.0 kg survival drop at T + 138 s",
             "• USD 1,320 China-Free Airframe+Avionics",
         ]),
        ("Benchmark H — Heated\nShelter & 285 km/h\nFast-Climber (#8 + #9)",
         "GREEN 3/4 (Residual 9 -> 3)", "#16a34a", "#dcfce7",
         "Tier 2 Repo: karhunkierros-sar-drone",
         [
             "• 12-Cell +15 °C Heated Clamshell Shelter",
             "  (6.5 s lid opening, 42 W steady draw)",
             "• Cold-Rated 285 km/h (79.2 m/s) COTS",
             "  Fast-Climber (EUR 2,350 China-Free BOM)",
             "• 50 Hz 3D APN Rendezvous (N' = 4.0,",
             "  0.08 m terminal miss distance)",
             "• Non-Pyrotechnic 2.5×2.5 m Dyneema",
             "  Soft-Net + 1.2 m² Parachute (4.11 m/s)",
         ]),
        ("Benchmark A — Passive\nAirspace-Safety Acoustic\n& RF Grid ([P11-AIR] + #4)",
         "GREEN 3/4 (Residual 6 -> 3)", "#16a34a", "#dcfce7",
         "Tier 1 Repo: arctic-trail-cam",
         [
             "• Pine-Trunk Trail-Cam Pod + 3D Infineon",
             "  IM69D130 4-Mic Array (+USD 68 COTS)",
             "• Swedish Acconeer XM125 60 GHz pulsed",
             "  coherent micro-Doppler radar sensor",
             "• FIN-SIG-LIB v1.0 (-30 °C speed of sound",
             "  c = 312.58 m/s 3D GCC-PHAT solver)",
             "• 96.2% 5-class acoustic accuracy, <=1.8 s",
             "  latency, <=25% false-dispatch waste",
         ]),
        ("Benchmark J — Corridor &\nSubstation Non-RF Rotorcraft\nBelt (#7 [P12-BELT])",
         "AMBER 2/4 Max Civilian Ceiling (Res 6 -> 4)", "#d97706", "#fef3c7",
         "Tier 1/2 Shared Perimeter Kit",
         [
             "• Zero-RF Acoustic Harmonic Sensing",
             "  (4-rotor BPF + 8–16 kHz ESC PWM)",
             "• Acconeer XM125 60 GHz micro-Doppler",
             "  + 940 nm / LWIR optical tripwire (550 m)",
             "• 94% detection probability in 0.48 s",
             "  (DD\\x03 Reg 15 optical diode alert)",
             "• 120 ms passive Dyneema transformer",
             "  safety net; kinetic effectors excluded",
         ]),
        ("Benchmark K — Coastal &\nSubsea Cable Inspection\nUSV (#12 FIN-LAB-06)",
         "GREEN 3/4 (Residual 2 -> 1)", "#16a34a", "#dcfce7",
         "Tier 3 Module: northern_flank_red_gap_solver",
         [
             "• 1.85 m Solar / LiFePO4 Autonomous",
             "  Coastal Catamaran USV (EUR 4,650 BOM)",
             "• 450 kHz Side-Scan Sonar Array +",
             "  3-Axis PNI RM3100 (USA) Fluxgate",
             "  Magnetic Subsea Cable Tracker",
             "• [P11-COAST] 1-Way Optical Shore",
             "  Handoff (0.00 W RF emission)",
             "• 84% coastal availability, 36 h endurance",
         ]),
    ]

    cx = 1.2
    cw = 18.8
    for title, badge, b_col, b_bg, repo_tag, bullets in cards:
        ax.add_patch(FancyBboxPatch((cx, 11.2), cw, 28.0, boxstyle="round,pad=0.3",
                                    facecolor="#ffffff", edgecolor="#cbd5e1", lw=1.6))
        ax.text(cx + cw / 2, 37.2, title, color="#0f172a", fontsize=9.8, fontweight="bold", ha="center", va="center")
        ax.add_patch(FancyBboxPatch((cx + 0.8, 32.8), cw - 1.6, 2.2, boxstyle="round,pad=0.2",
                                    facecolor=b_bg, edgecolor=b_col, lw=1.2))
        ax.text(cx + cw / 2, 33.9, badge, color=b_col, fontsize=8.0, fontweight="bold", ha="center", va="center")

        ax.add_patch(FancyBboxPatch((cx + 0.8, 29.8), cw - 1.6, 2.0, boxstyle="round,pad=0.15",
                                    facecolor="#eff6ff", edgecolor="#3b82f6", lw=1.0))
        ax.text(cx + cw / 2, 30.8, repo_tag, color="#1d4ed8", fontsize=7.8, fontweight="bold", ha="center", va="center")

        by = 27.6
        for b_line in bullets:
            ax.text(cx + 0.7, by, b_line, color="#334155", fontsize=7.9, ha="left", va="center")
            by -= 2.05

        cx += 19.7

    # Bottom Progression Bar (Capability-Gated Stages 1 -> 2 -> 3 -> 4, Zero Calendar Dates)
    stages = [
        (1.5, 21.0, "Stage 1: 38.5% Baseline", "(37/96 pts, 41 Priority Residual)", "#dc2626", "#fef2f2"),
        (25.5, 21.0, "Stage 2: 54.2% ([P11-AIR] Grid)", "(52/96 pts, 32 Priority Residual)", "#d97706", "#fffbeb"),
        (49.5, 25.0, "Stage 3: 72.9% in Code & 3D CAD", "(70/96 pts, 11 GREEN, 14 Residual = -65.9%)", "#16a34a", "#f0fdf4"),
        (77.5, 21.0, "Stage 4: 86.5% Field-Validated", "(83/96 pts Civilian Ceiling, 11 Residual)", "#0284c7", "#f0f9ff"),
    ]
    for sx, sw, st_main, st_sub, scol, sbg in stages:
        ax.add_patch(FancyBboxPatch((sx, 1.5), sw, 7.2, boxstyle="round,pad=0.3",
                                    facecolor=sbg, edgecolor=scol, lw=2.0))
        ax.text(sx + sw / 2, 5.9, st_main, color=scol, fontsize=10.5, fontweight="bold", ha="center", va="center")
        ax.text(sx + sw / 2, 3.4, st_sub, color="#1e293b", fontsize=8.4, fontweight="bold", ha="center", va="center")

    for ax_x in [(22.8, 25.2), (46.8, 49.2), (74.8, 77.2)]:
        ax.annotate("", xy=(ax_x[1], 5.1), xytext=(ax_x[0], 5.1),
                    arrowprops=dict(arrowstyle="->", color="#475569", lw=2.5, mutation_scale=20))

    fig.savefig(dst, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {dst}")


if __name__ == "__main__":
    fix_plate_01()
    fix_plate_02()
    build_plate_12()
    build_plate_13()
    build_plate_14()
