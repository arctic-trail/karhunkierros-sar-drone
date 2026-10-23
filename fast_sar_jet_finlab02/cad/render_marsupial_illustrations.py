#!/usr/bin/env python3
"""
Render 100% CAD-Matched Marsupial Dual-Drone Mission Illustrations (EN & FI, _v2)
with Crisp TrueType Typography, Numbered Badges, and Clean Callout Cards.
"""

import os
import pathlib
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
BRAIN_DIR = os.environ.get("SAR_ARTWORK_CACHE_DIR", os.path.join(REPO_ROOT, "docs", "images"))
JET_IMG_DIR = os.path.join(REPO_ROOT, "docs", "images")
QUAD_IMG_DIR = JET_IMG_DIR
QUAD_SUB_IMG_DIR = JET_IMG_DIR


def get_font(size: int, bold: bool = False):
    candidates = (
        ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Helvetica.ttc"]
        if bold
        else ["DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_callout_box(
    draw: ImageDraw.ImageDraw,
    box_xy,
    title: str,
    lines: list,
    border_color=(0, 212, 255),
    bg_color=(9, 22, 42, 236),
    badge_num: str = None,
    badge_bg=(255, 109, 0),
    title_color=(255, 255, 255),
    body_color=(212, 228, 247),
    title_size=19,
    body_size=15,
):
    x0, y0, x1, y1 = box_xy
    draw.rounded_rectangle(box_xy, radius=8, fill=bg_color, outline=border_color, width=2)
    f_title = get_font(title_size, bold=True)
    f_body = get_font(body_size, bold=False)

    tx = x0 + 12
    if badge_num is not None:
        r = 13
        cx, cy = x0 + 20, y0 + 20
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=badge_bg, outline=(255, 255, 255), width=2)
        f_badge = get_font(15, bold=True)
        bbox = draw.textbbox((0, 0), badge_num, font=f_badge)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - bw / 2, cy - bh / 2 - 2), badge_num, font=f_badge, fill=(255, 255, 255))
        tx = x0 + 40

    draw.text((tx, y0 + 9), title, font=f_title, fill=title_color)
    curr_y = y0 + 9 + title_size + 6
    for line in lines:
        draw.text((x0 + 12, curr_y), line, font=f_body, fill=body_color)
        curr_y += body_size + 4


def draw_leader(draw: ImageDraw.ImageDraw, start_xy, end_xy, color=(0, 212, 255), width=3):
    draw.line([start_xy, end_xy], fill=color, width=width)
    ex, ey = end_xy
    r = 5
    draw.ellipse((ex - r, ey - r, ex + r, ey + r), fill=color, outline=(255, 255, 255), width=2)


def render_plate_a_cutaway_and_drop():
    raw_path = os.path.join(BRAIN_DIR, "raw_marsupial_cutaway_and_4stage_drop_v4_1792639377935.jpg")
    base = Image.open(raw_path).convert("RGB")
    W, H = 2752, 1536
    img = base.resize((W, H), Image.Resampling.LANCZOS)

    # Clean tiny orange pod at the bottom tip of the detached drogue chute in Stage 3 (x=1830..1895, y=785..838)
    bg_sample = img.getpixel((1920, 810))
    patch_draw = ImageDraw.Draw(img)
    patch_draw.polygon([(1830, 785), (1896, 785), (1896, 838), (1830, 838)], fill=bg_sample)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Header bar
    d.rectangle((0, 0, W, 114), fill=(7, 17, 34, 248))
    d.line([(0, 114), (W, 114)], fill=(0, 212, 255, 255), width=3)

    f_h1 = get_font(31, bold=True)
    f_sub = get_font(20, bold=False)
    d.text(
        (28, 18),
        "MARSUPIAL DUAL-DRONE ARCHITECTURE (CARTRIDGE B: FIN-LAB-02 JET + FOLDED SAR QUAD)",
        font=f_h1,
        fill=(255, 255, 255),
    )
    d.text(
        (28, 62),
        "CAD Single Source of Truth: Connected 110° Inverted Λ-Tail • 48° Strake + 16° Wing (2.20 m) • 355 mm Nose Prop • +15 °C Heated Belly Bay • 4-Stage Drop",
        font=f_sub,
        fill=(0, 212, 255),
    )

    # Panel headers
    d.rounded_rectangle((28, 130, 1295, 178), radius=6, fill=(14, 34, 64, 235), outline=(0, 212, 255), width=2)
    d.text(
        (44, 141),
        "LEFT: 3D CAD CUTAWAY — FOLDED KARHUNKIERROS QUAD IN HEATED BELLY BAY",
        font=get_font(21, bold=True),
        fill=(255, 204, 77),
    )

    d.rounded_rectangle((1330, 130, 2724, 178), radius=6, fill=(14, 34, 64, 235), outline=(0, 212, 255), width=2)
    d.text(
        (1346, 141),
        "RIGHT: 4-STAGE MID-AIR DEPLOYMENT (85 m AGL) & 320 m OVERHEAD RELAY ORBIT",
        font=get_font(21, bold=True),
        fill=(255, 204, 77),
    )

    # Left panel callouts
    draw_leader(d, (460, 285), (710, 435), color=(0, 212, 255), width=3)
    draw_leader(d, (460, 285), (566, 558), color=(0, 212, 255), width=3)
    draw_callout_box(
        d,
        (36, 195, 650, 325),
        "CAD-Locked Airframe & Propulsion (FIN-LAB-02)",
        [
            "• Connected 110° Inverted Λ-Tail Arch outside jet plume",
            "• 48° Inboard LERX Strake + 16° Outer Wing (2.20 m span)",
            "• Dorsal JetCat P100-RX (72 m/s dash) + 355 mm Nose Prop",
        ],
        border_color=(0, 212, 255),
    )

    draw_leader(d, (360, 1085), (432, 756), color=(255, 165, 0), width=3)
    draw_leader(d, (550, 1085), (484, 960), color=(255, 165, 0), width=3)
    draw_callout_box(
        d,
        (36, 1085, 860, 1265),
        "Insulated Belly Bay (580 × 240 × 165 mm at X_CG = 595 mm)",
        [
            "• Carries Folded Karhunkierros Quad (3.20 kg + 1.0 kg Warm Cask)",
            "• 28 V Breakaway Magnetic Umbilical keeps Quad at 100% SOC",
            "• 15 W PTC + Turbine Bleed Air keeps Battery at +15 °C in -30 °C",
            "• Zero Pitch Trim Shift on Release (mounted dead-center at CG)",
        ],
        border_color=(255, 165, 0),
    )

    draw_callout_box(
        d,
        (36, 1285, 1295, 1508),
        "WHY THE MARSUPIAL JET-QUAD ARCHITECTURE SOLVES ARCTIC STORM RESCUE",
        [
            "• Standalone Multi-Rotor Wall: In a 14 m/s (50 km/h) freezing headwind, a standalone quadcopter nets only 4.0 m/s",
            "  groundspeed and hits its 50% battery turnaround limit at 4.59 km (cannot reach a 12–45 km back-canyon SOS).",
            "• Marsupial Breakthrough: The FIN-LAB-02 Jet dashes 35 km in 11.3 min at 259 km/h (72 m/s TAS) above the weather,",
            "  then drops the warm (+15 °C), 100% charged Quad directly over the canyon for under-canopy hover & lantern escort!",
        ],
        border_color=(80, 250, 123),
        title_color=(80, 250, 123),
    )

    # Right panel 4-stage badges & callouts
    # Stage 1: Belly Release pointing directly to the falling folded quadcopter at (1835, 395)
    draw_leader(d, (2060, 295), (1845, 385), color=(255, 109, 0), width=3)
    draw_callout_box(
        d,
        (1980, 195, 2720, 355),
        " Belly Release at 85 m AGL (22 m/s)",
        [
            "• Jet slows to 22 m/s on nose electric prop",
            "• Dual-servo pins pull; 80 N springs eject Quad",
            "• 1.85 m tail clearance in t = 0.28 s (0° pitch trim)",
        ],
        border_color=(255, 109, 0),
        badge_num="1",
    )

    # Stage 2: Drogue & Snap-Open Arms pointing to (1975, 595)
    draw_leader(d, (1850, 620), (1975, 595), color=(0, 212, 255), width=3)
    draw_callout_box(
        d,
        (1340, 540, 1945, 705),
        " Drogue Pitch-Up & Arm Unfold (t = 1.1 s)",
        [
            "• 0.35 m² ribbon drogue brakes quad to 11 m/s",
            "• Torsion springs snap 4 carbon arms to X-lock",
            "• EKF3 aligns attitude & baro/altimeter in air",
        ],
        border_color=(0, 212, 255),
        badge_num="2",
    )

    # Stage 3: Drogue Jettison & Motor Ignition pointing to the spinning-up quadcopter at (2030, 760)
    draw_leader(d, (1860, 825), (2025, 765), color=(0, 212, 255), width=3)
    draw_callout_box(
        d,
        (1340, 780, 1875, 945),
        " Chute Cutaway & Motor Ignition (t = 2.0 s)",
        [
            "• Micro-servo releases drogue at 68 m AGL",
            "• 4 brushless rotors spin up to hover thrust",
            "• Zero descent below 52 m AGL (>30 m above trees)",
        ],
        border_color=(0, 212, 255),
        badge_num="3",
    )

    # Stage 4: Joint Canyon Rescue + 320 m Orbiting Relay
    draw_leader(d, (2150, 1290), (2395, 1055), color=(80, 250, 123), width=3)
    draw_leader(d, (2350, 1290), (2490, 505), color=(80, 250, 123), width=3)
    draw_callout_box(
        d,
        (1620, 1285, 2724, 1508),
        " Joint Mission: 15 m Cask Winch + 28 m Lantern Walk + 320 m Jet Relay",
        [
            "• Quad descends into canyon: lowers 1.0 kg +42 °C glucose/blanket cask at 15 m standoff,",
            "  then leads survivor at 28 m height (15 m ahead) to the nearest heated wilderness hut.",
            "• Mothership Jet climbs to 320 m orbit on 260 W nose prop (45 min loiter), acting as an",
            "  airborne 868 MHz ELRS & Wi-Fi relay over the canyon ridges (+28.4 dB link margin).",
        ],
        border_color=(80, 250, 123),
        badge_num="4",
        badge_bg=(40, 180, 90),
    )

    final_img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    for out_dir in [JET_IMG_DIR, QUAD_IMG_DIR, QUAD_SUB_IMG_DIR]:
        os.makedirs(out_dir, exist_ok=True)
        for old_n in ["sar_marsupial_cutaway_and_4stage_drop_v1.jpg", "sar_marsupial_cutaway_and_4stage_drop_v2.jpg"]:
            old_p = os.path.join(out_dir, old_n)
            if os.path.exists(old_p):
                os.remove(old_p)
        out_path = os.path.join(out_dir, "sar_marsupial_cutaway_and_4stage_drop_v3.jpg")
        final_img.save(out_path, quality=94, subsampling=0)
        print("Saved:", out_path)

    zoom_crop = final_img.crop((1300, 180, 2720, 1250))
    zoom_crop.save(os.path.join(BRAIN_DIR, "zoom_marsupial_plate_a_v3_check.jpg"), quality=92)


def render_plate_b_6stage_storyboard(lang="en"):
    raw_v3_path = os.path.join(BRAIN_DIR, "raw_marsupial_6stage_storyboard_ssot_v3_1792639414691.jpg")
    raw_v1_path = os.path.join(BRAIN_DIR, "raw_marsupial_6stage_storyboard_cad_matched_1792639347356.jpg")

    base_v3 = Image.open(raw_v3_path).convert("RGB")
    base_v1 = Image.open(raw_v1_path).convert("RGB")

    # Splice bottom half of Column 6 from base_v1 resized to fit exact Column 6 lower box (x=1136..1356, y=380..670)
    col6_src = base_v1.crop((1150, 462, 1370, 690)).resize((220, 290), Image.Resampling.LANCZOS)
    base_v3.paste(col6_src, (1136, 380))
    # Draw clean dark panel border around Column 6 lower box in 1x before upscaling
    d1 = ImageDraw.Draw(base_v3)
    d1.rectangle((1134, 378, 1357, 671), outline=(15, 23, 34), width=3)

    W, H = 2752, 1536
    img = base_v3.resize((W, H), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    d.rectangle((0, 0, W, 156), fill=(9, 20, 38, 248))
    d.line([(0, 156), (W, 156)], fill=(255, 140, 0, 255), width=3)
    d.rectangle((0, 1345, W, H), fill=(9, 20, 38, 248))
    d.line([(0, 1345), (W, 1345)], fill=(0, 212, 255, 255), width=3)

    if lang == "en":
        main_title = "END-TO-END MARSUPIAL DUAL-DRONE WILDERNESS RESCUE CHAIN (35–45 KM IN 14 M/S STORM)"
        sub_title = "How the 259 km/h FIN-LAB-02 Mothership Jet Transports, Drops, Relays & Recovers the Karhunkierros SAR Quadcopter"
        cols = [
            (
                "1",
                "SOS & JET LAUNCH",
                "0 min • Roadhead Launch",
                [
                    "• Hiker triggers SOS post or",
                    "  LoRa/thermal camera alert.",
                    "• FIN-LAB-02 Jet launches off",
                    "  wheeled dolly carrying folded",
                    "  Quad inside +15 °C belly bay.",
                ],
            ),
            (
                "2",
                "259 KM/H STORM DASH",
                "11.3 min • 35 km Transit",
                [
                    "• Jet pierces 14 m/s (50 km/h)",
                    "  blizzard headwind at 72 m/s.",
                    "• Captive Quad stays at +15 °C",
                    "  & 100% SOC via 28V umbilical",
                    "  (0% quad battery used!).",
                ],
            ),
            (
                "3",
                "85 M MID-AIR DROP",
                "11.5 min • Canyon Entry",
                [
                    "• Jet slows to 22 m/s on nose",
                    "  prop & opens ventral doors.",
                    "• Drogue chute brakes Quad;",
                    "  4 carbon arms snap open &",
                    "  rotors lock hover in 2.8 s.",
                ],
            ),
            (
                "4",
                "320 M RELAY + CASK",
                "13.0 min • +42 °C Aid Drop",
                [
                    "• Jet orbits at 320 m on 260 W",
                    "  nose prop as 868 MHz relay.",
                    "• Quad flies under spruce canopy",
                    "  & winches 1 kg +42 °C glucose",
                    "  cask + bivvy 15 m from hiker.",
                ],
            ),
            (
                "5",
                "28 M LANTERN ESCORT",
                "15–32 min • Trail Guide",
                [
                    "• Quad climbs to 28 m above",
                    "  trees, shining spotlight cone",
                    "  15 m ahead of walking hiker.",
                    "• Guides survivor step-by-step",
                    "  while Jet returns to base.",
                ],
            ),
            (
                "6",
                "WARM HUT & NEST DOCK",
                "35 min • Safe Recovery",
                [
                    "• Survivor enters heated log",
                    "  wilderness hut (Autiotupa).",
                    "• Quad lands inside +10 °C",
                    "  motorized roofed trail nest",
                    "  box to recharge (34% SOC).",
                ],
            ),
        ]
    else:
        main_title = "KAKSOISDROONIN (EMO-SUIHKUKONE + NELIKOPTERI) PELASTUSKETJU (35–45 KM MYRSKYSSÄ)"
        sub_title = "Kuinka 259 km/h FIN-LAB-02 -emosuihkulennokki kuljettaa, pudottaa, linkittää ja palauttaa Karhunkierros-nelikopterin"
        cols = [
            (
                "1",
                "SOS & EMOKONEEN LÄHTÖ",
                "0 min • Lähtö tieltä",
                [
                    "• Vaeltaja painaa SOS-nappia",
                    "  tai lämpökamera havaitsee.",
                    "• FIN-LAB-02 nousee vaunulta",
                    "  nelikopteri taitettuna +15 °C",
                    "  lämmitettyyn maharuumaan.",
                ],
            ),
            (
                "2",
                "259 KM/H MYRSKYLENTO",
                "11,3 min • 35 km siirtymä",
                [
                    "• Emokone lentää 72 m/s läpi",
                    "  14 m/s (50 km/h) vastatuulen.",
                    "• Nelikopterin akku pysyy",
                    "  +15 °C:ssa ja 100 % täynnä",
                    "  28 V napajohdon avulla.",
                ],
            ),
            (
                "3",
                "PUDOTUS 85 M KORKEUDESTA",
                "11,5 min • Kanjonin yllä",
                [
                    "• Emokone hidastaa 22 m/s",
                    "  nokkapotkurilla ja avaa luukut.",
                    "• Jarruvarjo vakauttaa kopterin,",
                    "  4 vartta lukittuu auki ja",
                    "  roottorit käynnistyvät 2,8 s.",
                ],
            ),
            (
                "4",
                "320 M LINKKI + TYNNYRI",
                "13,0 min • +42 °C apupaketti",
                [
                    "• Emokone kaartelee 320 m:ssä",
                    "  260 W sähköpotkurilla linkkinä.",
                    "• Kopteri laskee 1 kg +42 °C",
                    "  glukoositynnyrin & lämpöpussin",
                    "  15 m päähän pelastettavasta.",
                ],
            ),
            (
                "5",
                "28 M VALOLYHTYSAATTO",
                "15–32 min • Polkuopastus",
                [
                    "• Kopteri nousee 28 m puiden",
                    "  ylle ja valaisee polun 15 m",
                    "  kävelijän eteen kohti tupaa.",
                    "• Emokone palaa tukikohtaan",
                    "  tai jatkaa linkkikaartoa.",
                ],
            ),
            (
                "6",
                "AUTIOTUPA & PESÄTELAKKA",
                "35 min • Turvassa tuvassa",
                [
                    "• Vaeltaja pääsee lämpimään",
                    "  autiotupaan kamiinan ääreen.",
                    "• Nelikopteri laskeutuu +10 °C",
                    "  avautuvaan maastopesään",
                    "  latautumaan (34 % varausta).",
                ],
            ),
        ]

    d.text((28, 14), main_title, font=get_font(30, bold=True), fill=(255, 255, 255))
    d.text((28, 54), sub_title, font=get_font(19, bold=False), fill=(0, 212, 255))

    # Align exactly with the 6 artwork column borders: [34, 476, 924, 1372, 1820, 2268, 2714]
    col_edges = [34, 476, 924, 1372, 1820, 2268, 2714]
    for i, (num, title, subtitle, bullets) in enumerate(cols):
        x0, x1 = col_edges[i] + 3, col_edges[i + 1] - 3
        d.rounded_rectangle((x0, 88, x1, 150), radius=6, fill=(16, 36, 68, 245), outline=(0, 212, 255), width=2)
        cx, cy, r = x0 + 22, 119, 15
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 109, 0), outline=(255, 255, 255), width=2)
        f_num = get_font(16, bold=True)
        nb = d.textbbox((0, 0), num, font=f_num)
        d.text((cx - (nb[2] - nb[0]) / 2, cy - (nb[3] - nb[1]) / 2 - 2), num, font=f_num, fill=(255, 255, 255))
        d.text((x0 + 44, 94), title, font=get_font(17, bold=True), fill=(255, 255, 255))
        d.text((x0 + 44, 120), subtitle, font=get_font(14, bold=False), fill=(255, 204, 77))

        d.rounded_rectangle((x0, 1352, x1, 1528), radius=6, fill=(14, 31, 58, 245), outline=(0, 212, 255), width=2)
        by = 1362
        f_b = get_font(15, bold=False)
        for line in bullets:
            d.text((x0 + 10, by), line, font=f_b, fill=(224, 238, 255))
            by += 31

    final_img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    old_fname = f"sar_marsupial_6stage_whole_mission_{lang}_v1.jpg"
    fname = f"sar_marsupial_6stage_whole_mission_{lang}_v2.jpg"
    for out_dir in [JET_IMG_DIR, QUAD_IMG_DIR, QUAD_SUB_IMG_DIR]:
        os.makedirs(out_dir, exist_ok=True)
        old_p = os.path.join(out_dir, old_fname)
        if os.path.exists(old_p):
            os.remove(old_p)
        out_path = os.path.join(out_dir, fname)
        final_img.save(out_path, quality=94, subsampling=0)
        print("Saved:", out_path)


if __name__ == "__main__":
    render_plate_a_cutaway_and_drop()
    render_plate_b_6stage_storyboard("en")
    render_plate_b_6stage_storyboard("fi")
