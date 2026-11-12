> [!IMPORTANT]
> **Export-Control (`EAR` / `EU Dual-Use`) & Institutional Procurement Note (`100% Civilian Open-Source`):**
> * **Zero ITAR / Zero `5D002` Crypto / Exempt `< 30 min` Airframe (`9A012.a.1`):** This airframe (`19–27 min < 30 min` endurance, `10.0 m/s < 12.86 m/s` firmware wind ceiling), its standard single-antenna `u-blox M10` GPS, open Linux `V4L2`/`USB-UVC` capture scripts (`15 CFR § 734.7` published software), and `Ed25519` authentication-only telemetry (`5A002` Note 4 exempt) are **100% outside ITAR and EAR licensing**.
> * **Thermal Camera (`<= 9 Hz` `ECCN 6A993.a` vs. `> 9 Hz` Bench USB-UVC Surrogate):** While the local bench photos below illustrate physical mounting using a COTS `USB-UVC` thermal dongle (`Topdon TC001`), **any cross-border physical shipment or university/institutional build (e.g., Aalto University / SLPS)** must use the plug-compatible **`<= 9 Hz` `FLIR Lepton 3.5` (`8.7 Hz`, `ECCN 6A993.a`, `NLR`) + `PureThermal 3 USB-C`** or **`Teledyne FLIR Boson 320 <= 9 Hz` (`20320A006-9AAX`, `ECCN 6A993.a`)**, which enumerates on the exact same Linux `/dev/video*` `USB-UVC` interface without triggering `ECCN 6A003.b.4` (`> 9 Hz`) export licenses or OFAC SDN vendor restrictions. See [`EAR_ITAR_EU_DUAL_USE_AND_AALTO_PUBLICATION_COMPLIANCE.md`](EAR_ITAR_EU_DUAL_USE_AND_AALTO_PUBLICATION_COMPLIANCE.md).

# Opaslyhty SAR Quadcopter — IKEA-Style Step-by-Step Benchtop Assembly & Wiring Guide (Blocks 1–3)

> **Zero Guesswork Bench Manual (Same Format as the Trail Cam Quickstart Guide):**
> * **Safety Rule #1 (Propellers OFF Indoors):** Keep the 4 black `1045` (`10 × 4.5"`) propellers (`1A` below) **inside their clear plastic bags in the cardboard box** for the entire indoor build (`Blocks 1–3`). Never attach propellers indoors.
> * **Mandatory Remote-Build Tool Rule (`[T05]` Fine-Tip Precision Tweezers & `[T07]` Cyanoacrylate Super Glue Required!):** **Do NOT start this build in a remote location without a pair of fine-tip precision tweezers (`[T05]`, e.g., ESD-15 / Strebito precision tweezers) and a tube of Cyanoacrylate Super Glue (`[T07]`)!** In **`Step 6E`**, you must insert 4 hair-thin (`30 AWG`) tinned wire tips from the `6-pin JST-GH` pigtail into the microscopic `1.25 mm`-pitch holes of the white `4-pin` `Benewake TF02-Pro` connector (`IMG_9545`), and seat micro `JST-GH` plugs into tight `Pixhawk 6C` sockets (`TELEM1` / `PPM-SBUS RC`, `IMG_9553`). And in **`Step 7F`**, because the flat carbon footprint on the outer underside wing (`IMG_9583` & `IMG_9584`) is narrow, **Super Glue (`[T07]`) is the recommended best practice** over spongy double-sided foam tape to give the cantilevered metal `ArduCam` `U`-bracket a rigid, zero-wobble bond.
> * **Loose-First Fastener Rule:** Whenever bolting carbon plates or nylon tube clamps together, **hand-thread all `M3` screws loosely (`2–3 turns` out from snug) first** so every hole aligns without binding, and only tighten them in a diagonal **`X`-pattern** (`1 -> 3 -> 2 -> 4`) at the end of that step.
> * **Strict `Slate-Grey` Empty-Pin Rule:** Any pin, wire, or socket that must remain **UNCONNECTED / EMPTY** (such as the wide `10-pin GPS1` socket or the 2 unused `Yellow & Green` wires on the `TELEM1` LiDAR cable) is marked in **`Slate-Grey` (`EMPTY / DO NOT CONNECT`)**.

![Real Unboxed Holybro X500 V2 Parts on Your Towel: All 12 Part Groups Color-Coded by Assembly Order](assets/block1_real_towel_parts_and_assembly_guide_v2.jpg)

![Group 1 Focus Guide: Center Plates, XT60/XT30 PDB & 4 Motor Arms (M1-M4) with Exact Tag Colors & 4-Step Order](assets/block1_group1_exact_order_and_parts_v2.jpg)

![Group 1 Hardware Decoder: All 11 Screw Bags Identified — Which 5 Bags to Use Now (S1A, S1B, S1C, S2A, S2B) vs. Which 6 Bags to Set Aside](assets/block1_step1_and_step2_exact_screw_bags_v2.jpg)

![Step 1 Macro Hole Map: Move the 4 Screws + Black Hex Standoffs 1 Step Outward to the 4 Green Holes (Inner Hole of Each Diagonal 2-Hole Pair = 44.5mm PDB Square)](assets/block1_step1_move_4_standoffs_to_44mm_pdb_holes_v2.jpg)

![Step 2 Hole Map & Parts to Grab Next: Why We Mount the 4x Slide-Bar Hangers (8x M2.5*6mm) & 2x Landing Gear Legs (8x M3*8mm) Before Closing Top Plate G3](assets/block1_step2_base_plate_holes_and_parts_to_grab_v3.jpg)

![Step 2A Single-Action Visual Guide: Bolt 4x Black Plastic Hangers Underneath G1 Base Plate Using 8x Socket Cap Screw M2.5*6mm](assets/block1_step2a_just_4_hangers_and_8_m25_screws_v1.jpg)

![Step 2B Single-Action Visual Guide: Bolt the 2x Vertical Landing Gear Poles & 2x Foam Skids Underneath G1 Base Plate Using 8x Socket Cap Screw M3*8mm](assets/block1_step2b_bolt_2_landing_gear_legs_v1.jpg)

![Step 2C Single-Action Visual Guide: Slide the 2x Horizontal Foam Landing Skids Onto the Bottom of the 2x Vertical Poles So the Frame Stands Upright on Its Feet](assets/block1_step2c_slide_2_foam_landing_skids_v4.jpg)

![Step 3A Single-Action Visual Guide: Seat 4x Lower Light-Blue Half-Clamps Into the 4 Square Corner Cutouts on Top of G1 Base Plate](assets/block1_step3a_seat_4_lower_blue_clamps_v2.jpg)

![Step 3 Motor Corner Map (M1, M2, M3, M4): Exact Corner Locations on G1 Base Plate Matching G3 "X500 V2" Top Plate](assets/block1_step3_motor_corner_map_m1_m2_m3_m4_v2.jpg)

![Step 3B Single-Action Visual Guide: Move the 4 Clamped Arms On Top of G1 Base Plate, Plug the 4 Yellow XT30 Leads Into the PDB, and Bolt G3 "X500 V2" Top Plate On Top](assets/block1_step3b_move_arms_on_top_of_g1_and_add_g3_top_plate_v4.jpg)

![Step 3C Single-Action Visual Guide: Plug the 4 Yellow XT30 Motor Power Plugs Into the PDB Inside the 19mm Sandwich Gap & Bring the 4 Thin Tagged M1–M4 Signal Wires Up Onto Top Plate G3](assets/block1_step3c_plug_4_xt30s_and_route_4_servo_wires_v2.jpg)

![Step 4A Single-Action Visual Guide: Bolt the 4 Remaining Assembled Hangers Under the Platform Board Using 8x Sunk Screw M2.5*6mm & Slide Onto the 2 Front Slide Bar Ends](assets/block1_step4a_platform_board_and_4_hangers_v2.jpg)

![Step 4B Single-Action Visual Guide: 3-Second 180° Flip of Platform Board + Bolt 2x A-Frame Slide Bar Clips to Battery Mounting Board Using 4x Sunk Screw M2.5*6mm & Snap Onto Slide Bars](assets/block1_step4b_flip_platform_board_and_attach_battery_board_v3.jpg)

![Step 4C Single-Action Visual Guide: Assemble 9. Battery Mounting Board with 2x A-Frame Slide Bar Clips, 4x Sunk Screw M2.5*6mm & White 3M Battery Pad, Then Snap Onto the 2 Carbon Slide Bars](assets/block1_step4c_assemble_and_snap_battery_mounting_board_v4.jpg)

![Step 4D Single-Action Visual Guide: Lay 9. Battery Mounting Board Onto the 4 Gold Brass Threaded Inserts of the 2x A-Frame Slide Bar Clips, Bolt With 4x Sunk Screw M2.5*6mm & Stick On White 3M Battery Pad](assets/block1_step4d_bolt_battery_board_onto_4_gold_brass_inserts_v2.jpg)

![Step 4E Verified Visual Guide: 10. Battery Pad (3M Tacky Silicone Pad) + 2x Black Velcro Straps Installed on 9. Battery Mounting Board (IMG_9229 & IMG_9230)](assets/block1_step4e_battery_pad_and_straps_verified_v2.jpg)

![Block 1 & 2 Visual Action Guide: Spotting Your Unboxed Holybro X500 V2 Parts, Clamping the 4 Carbon Arms & Skids, and Bolting the Motors, Pixhawk 6C & M10 GPS Mast](assets/block1_opaslyhty_x500v2_step_by_step_guide_v3.jpg)

![4-Stage 3D CAD Assembly Overview: Stage 1 Airframe -> Stage 2 Motors & Pixhawk 6C -> Stage 3 Night Pod & Pi 5 -> Stage 4 Thermal Battery Bay](../cad/opaslyhty_x500v2_ikea_assembly_guide_v6.png)

---

## STEP 0: Tools & "Spot Every Part in 3 Seconds" Visual Inventory (`[D01]`–`[D18]`)

### 0.1 Tools to Place on Your Table (`[T01]`–`[T06]`)

| Tool Code | Tool Name | What It Looks Like & What You Use It For |
| :---: | :--- | :--- |
| **`[T01]`** | **`2.0 mm` & `2.5 mm` Hex Drivers** *(Allen keys / precision bits)* | Fits every `M3` socket-head cap screw on the `Holybro X500 V2` carbon frame, arm clamps, motor mounts, and landing skids. |
| **`[T02]`** | **`Loctite 243` Blue Threadlocker** *(Medium-strength removable)* | Put **1 tiny micro-drop** on **metal-to-metal** `M3` bolts (`motor mount screws` + `aluminum standoff screws`). **Never** put `Loctite` on plastic/nylon clamps (it crazes plastic). |
| **`[T03]`** | **`AstroAI` Digital Multimeter** | Used in Block 3 for the mandatory **30-Second `XT60` Continuity / Smoke Check (`> 10 kΩ`)** and **`+5.10V DC` UBEC Check** before plugging in the `Pi 5` or battery. |
| **`[T04]`** | **Flush Side Cutters & `100 mm` Nylon Zip-Ties** | Used to dress the 4 ESC ribbons neatly along the carbon arms and cinch the ventral `Pi 5` + `UBEC` harness. |
| **`[T05]`** | **Fine-Tip Precision Tweezers (`MANDATORY — DO NOT OMIT FOR REMOTE BUILDS!`)** | **Mandatory for `Step 6E` and micro-connector seating:** Required to grip the 4 hair-thin (`30 AWG`) tinned silver wire tips `2–3 mm` behind the tip and push them straight into the tiny `1.25 mm`-pitch holes of the white `4-pin` `Benewake TF02-Pro` plug (`IMG_9545`) without bending them, and to guide `JST-GH` plugs squarely into `Pixhawk 6C` sockets (`IMG_9553`). **Never deploy to a remote build site without fine-tip tweezers!** |
| **`[T06]`** | **`3M ScotchBlue` Painter's Tape / White Paint Marker** | Used to label Motor Arms `#1` (`Front-Right`), `#2` (`Rear-Left`), `#3` (`Front-Left`), `#4` (`Rear-Right`), secure spiraled excess cables along the carbon arms, and mark tightened bolts. |
| **`[T07]`** | **Cyanoacrylate Super Glue (`MANDATORY BEST PRACTICE for Step 7F & Step 8`)** | **Recommended over spongy foam tape for narrow-footprint underside mounts (`Step 7F` & `Step 8`):** Because the flat carbon surface between the landing-gear leg mount and the blue arm clamp (`IMG_9583` & `IMG_9584`) is narrow, Super Glue bonds the metal `ArduCam` `U`-bracket foot and `Step 8` foam standoff shims rigidly with **zero camera wobble (`jello`)**, whereas soft double-sided foam tape flexes on a narrow edge. |
| **`[T08]`** | **Finnish `Fiskars` Classic Orange-Handled Scissors + `ArduCam` Box Closed-Cell EPE Foam (`Step 8`)** | **Mandatory for `Step 8` (`TOPDON TC001` Underside Mounting Behind the Leg):** Used to cut custom fitting standoff shims from the dense black closed-cell packaging foam inside the blue **`ArduCam` box** (`IMG_9614` & `IMG_9616` — **do NOT use** the thin foam from the larger black `Pixhawk` box!) to bridge over the protruding M3 button-head screw heads on the rear underside carbon bay (`IMG_9621`), creating a flush, vibration-isolated, thermally insulated flat surface for super-gluing the `56 × 30 mm` metal back of the `TOPDON TC001` (`IMG_9633`). |

### 0.2 Parts Needed for Block 1, Block 2 & Block 3 (`How to Spot Each Part Instantly`)

| Block | Part ID | Part Name | How to Spot It Instantly in Your Boxes (`Oct 27 Unboxing Photo`) |
| :---: | :---: | :--- | :--- |
| **Block 1** | **`[D14]`** | **`Holybro X500 V2 ARF Kit`** | Medium brown cardboard box (`bottom-center` of your Oct 27 unboxing photo): contains **`2×` square `144 × 144 mm` 3K carbon plates**, **`4× 16 mm` carbon arm tubes**, **`2× 270 mm` carbon landing skids + vertical leg tubes** (`1B`), **`4×` blue bubble-wrap pouches** (`1C` = `2216 920KV` motors pre-soldered to `20A` ESCs), **`M3` hardware ziploc bags** (`1D`), and **`4×` black `1045` propellers in clear bags** (`1A` — **leave in box!**). |
| **Block 1** | **`[D16]`** | **`Holybro Micro M10 GPS + Compass`** | Small round black/gold puck on a **folding carbon-fiber mast pedestal** with a 6-pin white `JST-GH` cable (`plugs into Pixhawk GPS1`). |
| **Block 2** | **`[D15]`** | **`Holybro Pixhawk 6C` + `PM02 V3`** | Rectangular black aluminum/plastic flight controller with a **white forward arrow (`▲`) printed on top** and rows of white `JST-GH` ports (`PWR1`, `TELEM1`, `TELEM2`, `GPS1`, `SERIAL4/5`, `I/O PWM OUT`), paired with the **`PM02 V3` power distribution board** (thick red/black `XT60` battery pigtail + 6-pin `PWR1` ribbon). |
| **Block 2** | **`[D09]`** | **`Benewake TF02-Pro` LiDAR (`40 m`)** | Compact black rectangular optical block (`69 × 41.5 × 26 mm`) with **two round optical lenses on its face** and a 4-wire cable (`Red +5V`, `Black GND`, `Green TX`, `White RX`). |
| **Block 2** | **`[D12]`** | **`MicoAir MTF-02P` Optical Flow + ToF** | Tiny coin-sized (`25 × 16 mm`) downward sensor board with a micro optical flow camera lens + laser ToF window and 4-pin `JST-GH` UART lead. |
| **Block 2** | **`[D10]`** | **`RadioMaster RP3 V2` ELRS Receiver** | Postage-stamp-sized (`22 × 13 mm`) blue/black PCB with **two gold `U.FL` dual-antenna pigtails (`T`-antennas)** and a 4-wire `CRSF` UART harness. |
| **Block 2** | **`[D01]`** | **`MatekSys ELRS-R24-D` / `LR900-F` Telemetry** | Secondary diversity telemetry transceiver module (`TELEM2` port) with dual dipole antennas. |
| **Block 3** | **`[D05]`** | **`Raspberry Pi 5 (8GB)` + `Active Cooler`** | Green credit-card computer with aluminum blower fan heatsink (`[P02]`) — mounts under the ventral payload bay on rubber vibration bobbins. |
| **Block 3** | **`[D06]`** | **`MatekSys BEC12S-PRO` (`5.1V / 5A` UBEC)** | Regulated step-down DC-DC converter board (`Input: 4S 14.8V battery bus` $\rightarrow$ `Output: 5.10V DC / 5A` for the `Raspberry Pi 5`). |
| **Block 3** | **`[D02]`** | **`Arducam IMX462 Starvis` Night Camera** | Square low-light `0.0001 lux` Starvis camera board with M12 wide-angle lens + CSI ribbon to `Raspberry Pi 5 CAM/DISP 0`. |
| **Block 3** | **`[D11]`** | **`TOPDON TC001` (`256×192` LWIR Thermal)** | Silver/grey compact USB-C thermal camera (`25 Hz` radiometric LWIR) — mounts in the `-45°` oblique forward pod and plugs into a blue `USB 3.0` port on the `Raspberry Pi 5`. |

---

## BLOCK 1 (`~2.0 Hours`): Assemble the Carbon Airframe, `270 mm` Landing Skids, `4×` Motors & `M10 GPS` Mast

### Step 1.1 — Unpack Your `Holybro X500 V2` Box (`[D14]`) & Quarantine the Propellers (`Badge 1A`)

1. Open the brown `Holybro X500 V2` box (`Step 1` panel in the visual guide above).
2. **Quarantine the `1045` Propellers (`Badge 1A`):** Pick up the clear plastic bags containing the black `10-inch` propellers (`1A`), place them at the bottom of the empty box lid, and set the box lid **off your worktable**.
3. Lay out on a clean towel:
   * **`2×` Square `144 × 144 × 2.0 mm` 3K Carbon Center Plates** (`Lower Base Plate` + `Upper Deck Plate`).
   * **`4×` Round `16 mm` OD Carbon-Fiber Arm Tubes (`Badge 1B`)** + **`8×` Black Nylon Half-Moon `16 mm` Tube Clamps**.
   * **`2×` Landing Gear Assemblies (`Badge 1B` / `2C`):** `2×` vertical `16 mm` carbon leg tubes pre-fitted into **`2× 270 mm` horizontal carbon skid tubes** with plastic T-joints and foam skid feet.
   * **`4×` Blue Bubble-Wrap Pouches (`Badge 1C`):** Inside each pouch is one **`Holybro 2216 920KV` brushless motor** pre-wired to a **`BLHeli_S 20A` ESC** that slides inside the hollow `16 mm` carbon arm tube.
   * **Hardware Ziploc Bags (`Badge 1D`):** Separate the **`M3 × 8 mm` button-head screws** (for standoffs & motors), **`M3 × 22 mm` socket-head clamp bolts**, **`M3` Nyloc locknuts**, and **`8×` vertical standoffs**.

### Step 1.2 — Bolt the `270 mm` Wide-Stance Landing Skids (`Badge 2C`) Under the Lower Carbon Center Plate

> **Which Way Round Does the Lower Carbon Plate Face?**
> * Look at the two `144 × 144 mm` square carbon plates: the **Lower Center Plate** is the one where the **`PM02 V3` Power Distribution Board** (or battery strap slots and lower landing-gear clamp holes at $x = \pm 66\text{ mm}$) mounts underneath.
> * Pick one flat edge as **`FRONT (NOSE ▲)`** and stick a small piece of **`3M ScotchBlue` tape (`[T06]`)** labeled **`"FRONT ▲"`** on that edge so you never rotate the frame $90^\circ$ mid-build!

1. Flip the **Lower Carbon Center Plate** upside-down on your towel.
2. Position the **left and right `270 mm` carbon landing skid assemblies (`Badge 2C`)** so the two horizontal skid tubes run **parallel to the `FRONT ▲` to `REAR` axis** (spaced `270 mm` apart left-to-right, $y = \pm 135\text{ mm}$).
3. Using your **`2.0 mm` Hex Driver (`[T01]`)** and the landing-gear `M3` mounting screws:
   * Thread all 4 mounting screws per leg **loosely by hand first**.
   * Once both left and right skids sit flat and parallel, apply **1 micro-drop of `Loctite 243` (`[T02]`)** to any metal-threaded insert bolts and tighten snugly.
4. Flip the assembly right-side up onto its skids on the table: confirm all 4 foam skid tips touch the table simultaneously with **`0.0 mm` rock/wobble**.

### Step 1.3 — Thread the `8×` Off-Diagonal Standoffs (`Badge 2A`), Slide In the `4× 16 mm` Carbon Arms (`Badge 2B`) & Bolt the Upper Plate in an `X`-Pattern

1. **Mount the `PM02 V3` Power Distribution Board (`[D15]`) Inside the Center Bay Before Closing the Top Deck:**
   * Before bolting the Upper Carbon Plate on, place the **`PM02 V3` power module** onto the **Lower Carbon Plate** inside the central $r < 54\text{ mm}$ bay with its thick **yellow `XT60` battery pigtail exiting cleanly toward the REAR or LEFT side** (away from the forward camera pod).
   * Secure it with its 4 nylon standoffs / double-sided foam pad.
2. **Thread the `8×` Off-Diagonal Vertical Standoffs (`Badge 2A`) Onto the Lower Plate:**
   * Fasten the `8×` vertical standoffs at the off-diagonal holes ($(\pm 64, \pm 24)\text{ mm}$ and $(\pm 24, \pm 64)\text{ mm}$, which sit `17.3 mm` clear of the $45^\circ$ diagonal arm paths) using `M3 × 8 mm` screws from beneath the Lower Plate.
3. **Slide the `4×` Pre-Wired `2216 920KV` Motor + `20A` ESC Assemblies (`Badge 1C` / `3A`) Into the `4× 16 mm` Carbon Arm Tubes (`Badge 2B`):**
   * Unwrap the 4 blue bubble-wrap pouches (`1C`).
   * For each arm: feed the `20A` ESC's power wires (`Red +`, `Black -`) and 3-pin servo signal plug through the hollow **`16 mm` carbon arm tube (`2B`)** from the outer motor tip toward the inner center-plate end.
   * **Bolt Each `2216 920KV` Motor (`Badge 3A`) Flush to Its Arm Tip (`16 × 16 mm M3` pattern):**
     * Align the 4 threaded `M3` holes on the bottom of the `2216` motor base with the motor mount at the tip of the carbon arm (`z = +26.0 mm`, motor shaft pointing **STRAIGHT UP**).
     * Put **1 tiny micro-drop of `Loctite 243` (`[T02]`)** on each of the 4 short `M3` motor screws.
     * **CRITICAL MOTOR SCREW LENGTH CHECK:** Look through the side slots of the motor base as you thread the 4 screws in—confirm the screw tips **never touch the copper stator windings** inside the motor! Tighten in a diagonal `X`-pattern.
4. **Clamp All 4 Carbon Arms (`45° / 135° / 225° / 315°`) Between the Lower & Upper Carbon Plates (`Badges 2A & 2B`):**
   * Place the lower halves of the **8 black nylon `16 mm` tube clamps** into their locating slots on the Lower Carbon Plate.
   * Lay the 4 carbon arms into the clamps at the 4 diagonal corners ($r = 54\text{..}250\text{ mm}$ for a `500 mm` diagonal motor-to-motor wheelbase) and place the upper halves of the 8 nylon tube clamps over the tubes.
   * **Label the 4 Arms Immediately with `3M` Tape (`[T06]`, Standard ArduCopter Quad-X Order):**
     * **`Arm #1 (FRONT-RIGHT, 45°)`:** Spins **`CCW` (Counter-Clockwise)** $\rightarrow$ plugs into **`MAIN OUT 1`**
     * **`Arm #2 (REAR-LEFT, 225°)`:** Spins **`CCW` (Counter-Clockwise)** $\rightarrow$ plugs into **`MAIN OUT 2`**
     * **`Arm #3 (FRONT-LEFT, 315°)`:** Spins **`CW` (Clockwise)** $\rightarrow$ plugs into **`MAIN OUT 3`**
     * **`Arm #4 (REAR-RIGHT, 135°)`:** Spins **`CW` (Clockwise)** $\rightarrow$ plugs into **`MAIN OUT 4`**
   * Lower the **Upper `144 × 144 mm` Carbon Center Plate (`2A`)** onto the 8 standoffs and arm clamps.
   * Thread all `M3` clamp bolts (into `M3` Nyloc nuts) and standoff screws **loosely by hand first**.
   * Measure from motor-shaft to motor-shaft across both diagonals to verify **`500 mm ± 2 mm`** symmetry and visually check that all 4 motors sit dead-level (`0.0°` twist), then tighten all `M3` bolts in a diagonal **`X`-pattern**.
5. **Connect the 4 ESC Power & Signal Leads Inside the Center Deck (`Step 3C`):**
   * Connect/plug the 4 yellow `XT30` ESC power leads (`M1–M4`) into the `PDB01-V1.3` (`XT60/XT30`) power distribution board inside the `19 mm` center sandwich gap (verifying zero wires loop around the `10 mm` Carbon Slide Bars underneath).
   * Route the 4 three-wire ESC signal plugs (`M1, M2, M3, M4`) up through the front and rear oval slots of `G3: "X500 V2" Top Plate`.
   * **Bench-Proven Mechanical Tip (`Step 3B` Upward-Screw Cantilever Technique):** When bolting the 4 motor arms + 8 light-blue clamps between `G1: Base Plate` and `G3: "X500 V2" Top Plate`, insert all `16× Socket Cap Screw M3*38mm` **from underneath `G1` upward** first — the downward cantilever weight/torque of the 4 hanging motor arms pinches the 16 screw shafts against the holes so they stay in place by themselves while you lower `G3: Top Plate` on top and finger-start each `Flange Locknut M3mm` one revolution per corner before tightening.

### Step 1.3B — Mount the Front `Platform Board` (`12`) & Ventral `Battery Mounting Board` (`9`) on the `10 mm` Carbon Slide Bars (`Steps 4A–4E`)

1. **Front `Platform Board` (`8× Sunk Screw M2.5*6mm` + `4× Hangers with Rubber Rings`, `Steps 4A & 4B`):**
   * Find the side of `12. Platform Board` that has the **8 conical countersunk bevels** around the 8 outer screw holes.
   * Thread `8× Sunk Screw M2.5*6mm` into the countersunk face so all 8 flat heads sit **100% flush**, and bolt the `4×` remaining Black Plastic Hangers (with Rubber Rings seated inside) onto the opposite face (aligning the middle plastic locating pin of each Hanger with the middle hole of each 3-hole group).
   * Slide the 4 Hangers onto the 2 protruding front ends of the `10 mm` Carbon Slide Bars so that **when the drone stands upright on its landing legs, the 4 round Hangers sit ABOVE the board (gripping the 2 bars) and the flat `Platform Board` hangs BELOW the 2 bars**.
2. **Ventral `Battery Mounting Board` (`4× Sunk Screw M2.5*6mm` + `2× A-Frame Slide Bar Clips` + `10. Battery Pad` + `2× Velcro Straps`, `Steps 4C–4E`):**
   * **Bench-Proven Mechanical Tip (`Clips-First Technique`, `IMG_9222`–`IMG_9225`):** Snap the 4 C-hooks of the **`2× A-Frame Slide Bar Clips` (`15. Slide Bar Clip 2pcs`)** directly onto the 2 `10 mm` Carbon Slide Bars underneath `G1: Base Plate` (between the front and rear Upper Hangers) **first**, and slide them outward toward the Upper Hangers to match the hole spacing of `9. Battery Mounting Board`. The 2 Slide Bars hold the 2 A-Frame Clips rock-steady with their **4 gold brass threaded inserts (`#1–#4`)** facing straight up!
   * Lay **`9. Battery Mounting Board`** on top of the 4 gold brass threaded inserts with its **4 conical countersunk bevels facing UP toward you** (when the drone is lying on its back), finger-start `4× Sunk Screw M2.5*6mm` (`1–2 turns loose first`), and tighten all 4 flush.
   * Peel and stick the white oval **`10. Battery Pad` (`3M` tacky silicone pad)** down the center of the flat countersunk face between the 4 flush screws, and thread the **`2× Black Velcro Battery Straps`** through the 4 long side slots.

> [!NOTE]
> **Engineering Rationale — Why Does the Battery Hang Underneath With a Tacky Silicone Pad (`10. Battery Pad`) + Dual Velcro Straps?**
>
> It looks surprisingly simple at first glance, but **a tacky silicone pad (`10. Battery Pad`) + dual Velcro cinch straps on a sliding rail tray** is the standard across research, industrial, and SAR multirotors for five practical engineering reasons:
>
> 1. **Two Different Mechanical Jobs — Straps Hold `Up/Down` Tension, Silicone Pad Holds `Horizontal Shear`:**
>    * The **2 woven nylon Velcro straps** only have to pull the battery **tightly upward** against the flat carbon board (a pair of `20 mm` nylon cinch straps holds **`> 25 kg`** in tension/shear, whereas the flight battery weighs **`~0.5–0.8 kg`**).
>    * Once pinched against the board, the **white `3M` tacky silicone pad** acts like gecko tape — its high coefficient of static friction ($\mu_s > 1.2$) stops the smooth battery wrapper from sliding forward, backward, or sideways during hard pitch/roll braking. *(Without the silicone pad, a smooth battery wrapper could slip along the straps; together, it will not budge a millimeter.)*
> 2. **5-Second Center-of-Gravity (`CG`) Trim Along the `10 mm` Carbon Slide Bars:**
>    * The battery represents **`~40–50%` of the entire aircraft's mass**.
>    * When you mount forward sensors on the front `Platform Board` (such as the `-45°` `TOPDON TC001` thermal + `IMX462 Starvis` low-light pod), the nose moment increases. With Velcro straps and the `A-Frame Clips` riding on the `10 mm` Carbon Slide Bars, you can slide the battery **`10–30 mm` forward or aft** in 5 seconds until the quadcopter balances dead-level at the central thrust axis (`x = 0, y = 0`) so the front motors (`M1, M3`) and rear motors (`M2, M4`) work at equal hover throttle.
> 3. **Universal Pack Geometry (`4S LiPo` Bench Packs vs. Insulated `4S2P 21700` Arctic Packs):**
>    * A rigid molded battery box only accepts one proprietary pack dimension. Dual Velcro straps let you swap seamlessly between a slim bench test pack, a standard `4S 5000 mAh` LiPo, or a thicker Aerogel-insulated **`4S2P 21700` (`Molicel P45B`) cold-weather pack** on the exact same carbon tray.
> 4. **Frees the Top Deck (`G3`) & Maximizes Magnetic Separation From the Compass (`> 100 mm`):**
>    * Suspending the battery **underneath** between the tall vertical landing legs lowers the vertical center of gravity (improving roll/pitch pendulum stability) and leaves the entire top plate (`G3: "X500 V2"`) unobstructed for the **`Pixhawk 6C`** flight controller and folding **`Micro M10 GPS + Compass` mast** — keeping the high-current (`20–40 A`) DC battery leads as far away as possible from the sensitive `IST8310` magnetometer on top.
> 5. **Cell Thermal Expansion & Hard-Landing Energy Absorption:**
>    * Pouch cells expand slightly under high discharge load (which can jam a rigid mechanical latch), and in a hard winter landing on uneven snow/crust, the `A-Frame Slide Bar Clips` + elastomer `Hanger Rubber Rings` + nylon straps flex slightly rather than fracturing the main carbon airframe.

### Step 1.4 — Mount the Folding `Micro M10 GPS + Compass` Mast (`[D16]`, `Badge 3B`) at Rear-Left (`-62, +62 mm`) or Front `Platform Board`

> **Why Rear-Left (`-62, +62 mm`) or Front Pedestal Away From the `XT60/XT30` PDB?**
> * While the flight battery hangs underneath on the ventral `9. Battery Mounting Board`, the `PDB01-V1.3` (`XT60/XT30`) power distribution board sits inside the center `19 mm` deck sandwich. Mounting the folding `M10 GNSS + IST8310` compass mast on its tall carbon pedestal at the **rear-left corner (`x = -62 mm, y = +62 mm`)** (or on the radial starburst slots of the front `Platform Board`) keeps the `IST8310` magnetometer **`> 100 mm` away from the high-current DC bus** (preventing magnetic compass interference) while leaving the center of `G3: "X500 V2" Top Plate` open for the **`Pixhawk 6C`** flight controller!

1. Bolt the folding carbon mast base (`[D16]`, `Badge 3B`) to the **rear-left corner** of the Upper Carbon Center Plate (or front `Platform Board` starburst slots) using the `M3` mounting screws and locknuts.
2. Stick the circular **`Micro M10 GPS` puck** onto the top mast disc using its included `3M` foam pad.
3. **Orientation Check (`✓ CRITICAL`):** Look at the small **arrow (`▲`) printed on top of the `M10 GPS` puck**—it **MUST point straight ahead toward the `FRONT ▲` nose of the drone** (parallel to the `Pixhawk 6C` arrow)!

### Block 1 Check-Off Table (`Verify Before Moving to Block 2`)

| Check | Physical Verification Item | Target Spec |
| :---: | :--- | :--- |
| `[x]` | **Propellers (`1A`) Still in Box?** | All 4 black `1045` propellers are still inside the cardboard box (`0` props on motors, verified in `block1_01`). |
| `[x]` | **Diagonal Wheelbase & Level Arms (`2B`)** | `500 mm` diagonal shaft-to-shaft; all 4 motor shafts point straight up (`0°` twist, verified in `IMG_9203` & `IMG_9206`). |
| `[x]` | **Landing Skid Stance (`2C`)** | `270 mm` track width; sits rock-solid on flat table with zero wobble (`verified in IMG_9129–IMG_9133`). |
| `[x]` | **Front `Platform Board` & Ventral `Battery Board` (`Steps 4A–4E`)** | All `12× Sunk Screw M2.5*6mm` (`8 + 4`) seated 100% flush in countersunk bevels; both flat boards hang below the `10 mm` Slide Bars when standing; `10. Battery Pad` & `2×` Velcro straps installed (`verified in IMG_9220–IMG_9230`). |
| `[x]` | **Motor Screws (`3A`) + `16× M3*38mm` Frame Bolts** | All `16× M3*38mm` arm clamp screws & `Flange Locknuts` tightened; 4 yellow `XT30` plugs seated in `PDB`; 4 thin `M1–M4` signal leads routed up to `G3: Top Plate` (`verified in IMG_9194–IMG_9210`). |
| `[x]` | **`M10 GPS` (`3B`) Arrow Direction** | Mounted on Front `Platform Board` with top arrow (`▲`) pointing straight **`FORWARD`** and `6-pin JST-GH` plugged into `GPS2` (`verified in IMG_9329`). |

---

## BLOCK 2 (`~1.5 Hours`): Mount `Pixhawk 6C` (`[D15]`), Downward `TF02-Pro` LiDAR (`[D09]`), `MTF-02P` Optical Flow (`[D12]`) & Dual Radios

### Step 2.0 — Part Finder: How to Spot Your Step 5, Step 6 & Step 7 Boxes and Bags in 5 Seconds

![Part Finder — How to Spot Your Step 5 Boxes & Bags in 5 Seconds (Pixhawk 6C, Micro M10 GPS & PM02 V3 Power Module)](assets/block2_step5_spot_pixhawk_gps_pm02_boxes_v3.jpg)

![Visual Overview — All Opaslyhty COTS Subsystems for Steps 5–7](assets/opaslyhty_all_cots_subsystems_visual_overview_v1.jpg)

### Step 2.1 — Stick the `Pixhawk 6C` Autopilot (`[D15]`, `Badge 3C`) Dead-Center & Plug In Motors + GPS + Power

![Step 5A — Unbox & Lay Out Your Pixhawk 6C (#1), Micro M10 GPS (#2) & PM02 V3 Power Module (#3)](assets/block2_step5a_unbox_pixhawk_gps_pm02_v2.jpg)

![Step 5B — Plug All 3 Color-Matched Harnesses into Pixhawk 6C on White Towel (Cyan=Power1, Amber=GPS2, Green=I/O PWM OUT)](assets/block2_step5b_final_pwm_plug_v14.jpg)

![Step 5C — Match the 3 Foam Pads to the 3 Modules & Stick Them onto Your Holybro X500 V2 Drone Frame](assets/block2_step5c_stick_3_modules_on_drone_v5.jpg)

![Step 5C Inline Layout Confirmation — Partially Covering the Oval Slots & Custom-Cut 3M VHB Pad](assets/block2_step5c_inline_layout_yes_partially_cover_ok_v1.jpg)

![Step 5D — Plug M1, M2, M3, M4 Motor Cables into PWM OUT Columns 1–4](assets/block2_step5d_plug_4_motors_pwm_out_v2.jpg)

![Step 5E — Step 5D Verified (M1–M4 + M3 Length Limit) & Plug PM02 V3 Female XT60 into Right-Side PDB](assets/block2_step5e_plug_pm02_xt60_into_pdb_v1.jpg)

1. **Mount the `Micro M10 GPS` (`Amber`) on the Front `Platform Board` & Custom-Cut the `3M VHB` Pad for the Center Inline Stack (`Step 5C`):**
   * Stick the grey vibration-isolation foam pad onto the Front `Platform Board` and mount the **`Micro M10 GPS` (`SKU: H12044`)** with its white **`▲` arrow pointing straight `FORWARD`**.
   * Cut a rear strip off the **Large Red `3M VHB` pad** so the main pad sits on the solid flat carbon bridge between the front and rear oval wire slots (leaving both oval wire slots open and free of exposed sticky tape) and the rear strip sits behind it for the **`8-Ch PWM Breakout Board`**.
   * Center the **`Pixhawk 6C`** left-to-right on `G3: "X500 V2" Top Plate` (**`52.5 mm` from the left carbon edge = `52.5 mm` from the right carbon edge**, verified with a steel millimeter ruler in `IMG_9354`–`IMG_9356`) with its top edge aligned right below `"X500 V2"` and its white **`▲` arrow pointing straight `FORWARD` (`0.0°` yaw offset)**.
   * Mount the **`8-Ch PWM Breakout Board`** directly behind the `Pixhawk 6C` with **`PWM OUT | 8 7 6 5 4 3 2 1`** facing the rear edge.
   * **Bench-Proven Mechanical Rule (`M3` Cable Reach Limit, `IMG_9373`–`IMG_9375`):** Never mount the `Pixhawk 6C` and `8-Ch PWM Breakout Board` any further aft than this position (top of `Pixhawk 6C` right below `"X500 V2"`). Because the **`M3` (`Front-Left`, Yellow flag)** cable runs down the left side of the `Pixhawk 6C` and must turn around the back of the `PWM Breakout Board` and cross past `Columns 8, 7, 6, 5, 4` to reach **`Column 3`**, this forward-most inline position is the exact maximum aft limit for `M3` to reach `Column 3` without tension!
2. **Plug In the 3 Core `Holybro` Harnesses (`Step 5B`) & the 4 Motor Signal Leads (`Step 5D`) + `PM02 V3` `XT60` (`Step 5E`):**
   * **`POWER1` (`Cyan`, Row 1 Left, `6-pin JST-GH`):** Plug the `6-pin` `JST-GH`-to-`Clik-Mate` ribbon cable from the **`PM02 V3` Power Module (`SKU: H15010`)** into **`POWER1`** on the `Pixhawk 6C` (do not use the spare taller `DF13` `6-pin` cable included in the `PM02 V3` bag).
   * **`GPS2` (`Amber`, Row 2 Middle, `6-pin JST-GH`):** Plug the `6-pin`-to-`6-pin` `JST-GH` cable from the **`Micro M10 GPS` (`SKU: H12044`, `6-pin` socket: `5V, RX, TX, SCL, SDA, GND`)** directly into **`GPS2` (`Row 2 Middle`, `6-pin`)** on the `Pixhawk 6C` (`GPS2_TYPE = 1`, `SERIAL4_PROTOCOL = 5`). Leave the `10-pin` `GPS1` port (`Row 3 Left`) **`Slate-Grey EMPTY`**.
   * **`I/O PWM OUT [MAIN]` (`Green`, Row 6 Bottom-Right, `10-pin JST-GH`):** Plug the wide `10-pin`-to-`10-pin` ribbon cable between **`I/O PWM OUT [MAIN]`** (`Bottom-Right` on `Pixhawk 6C`) and **`PWM IN`** on the **`8-Ch PWM Breakout Board`**, then plug the 4 ESC 3-pin servo leads vertically into the **right 4 columns (`4, 3, 2, 1`)** of `PWM OUT` with **`WHITE` wire (`Signal`) on the TOP pin** and **`BLACK` wire (`GND`) on the BOTTOM pin** (leaving `Columns 8, 7, 6, 5` on the left **`Slate-Grey EMPTY`**):
     * **`Column 1` (`Far-Right`)** $\leftarrow$ **`M1` (`Front-Right CCW`, `RED` wire flag)**
     * **`Column 2` (`2nd from Right`)** $\leftarrow$ **`M2` (`Rear-Left CCW`, `BLUE/NAVY` wire flag)**
     * **`Column 3` (`3rd from Right`)** $\leftarrow$ **`M3` (`Front-Left CW`, `YELLOW` wire flag)**
     * **`Column 4` (`4th from Right`)** $\leftarrow$ **`M4` (`Rear-Right CW`, `GREEN` wire flag)**
   * **`PM02 V3` `XT60 Female` to `PDB` `XT60 Male` (`Step 5E`, `Verified in IMG_9378 & IMG_9380`):** Look into the `19 mm` center gap on the **RIGHT side** of the airframe (`between M1 Front-Right and M4 Rear-Right`) and plug the beveled **`XT60 Female`** connector of the **`PM02 V3` Power Module** firmly into the big yellow **`XT60 Male` socket** soldered on the right edge of `G2: PDB` (`PDB01-V1.3`), leaving the other `XT60 Male` pigtail dropping down toward the Ventral Battery Tray for the flight battery.

![Step 5E Verified & Part Finder for Step 6 — Downward Sensors & Dual Radios](assets/block2_step5e_verified_and_step6_part_finder_v2.jpg)

### Step 2.2 — Spot & Unbox the 4 Step 6 Packages (`#1 TF02-Pro` `[D09]`, `#2 MTF-02P` `[D12]`, `#3 RadioMaster RP3 V2` `[D10]`, `#4 MicoAir LR900-F` `[D01]`) + Mount & Wire

Before unboxing and plugging in the Step 6 downward sensors and dual radios, spot the **3 white boxes (`#1`, `#2`, `#4`)** and **1 flat clear/silver zip-pouch (`#3`)** in your parts bin:
* **`#1: Benewake TF02-Pro 40m LiDAR` (`[D09]`, `Cyan`, Verified in `IMG_9388` & `IMG_9389`):** Medium white rectangular cardboard box labeled **`Benewake` / `Rangefinder` (`en.benewake.com`)** on the front lid and **`Benewake (Beijing) Co., Ltd.`** on the back.
* **`#2: MicoAir MTF-02P Optical Flow + ToF Sensor` (`[D12]`, `Green`, Verified in `IMG_9385`–`IMG_9389`):** Small square-ish white slide-out matchbox with the navy/cyan **`Mi micoair`** logo on the front and Amazon barcode **`X004GGY1CD` (`Micoair Optical Flow &...ith Ardupilot/PX4/INAV`)** on the back.
* **`#3: RadioMaster RP3 V2 ExpressLRS 2.4GHz Nano Receiver` (`[D10]`, `Yellow`):** **NOT A BOX** — comes in a paper-thin, flat **clear/silver zip-lock hang-pouch (`~110 × 70 mm`) with a black `RADIOMASTER` top header strip** (and a white `X00...` barcode sticker on the back; delivered in the same shipment as `#1` and `#2`).
* **`#4: MicoAir LR900-F 915MHz 30KM Long-Range LoRa Telemetry Radio` (`[D01]`, `Purple`, Verified in `IMG_9385`–`IMG_9389`):** Longer rectangular white slide-out box with the **`Mi micoair`** logo on the front and Amazon barcode **`X0047QCN8L` (`Micoair 915MHz 30KM...Pixhawk/Ardupilot/PX4`)** on the back.

![Step 6 Box & Pouch Finder — Your 3 Found Boxes Verified (#1 TF02-Pro, #2 MTF-02P, #4 LR900-F) & How to Spot the Flat #3 RadioMaster RP3 V2 Zip-Pouch](assets/block2_step6_spot_boxes_and_bags_v5.jpg)

#### Step 6A — Uncover Hidden Accessories in Box `#4` (`MicoAir LR900-F`), Screw On Antenna & Plug Into `TELEM2` (`Row 4, Center`)
1. **Lift out the black foam tray** inside the **`#4` (`MicoAir LR900-F`, `Purple`)** box: underneath are **2× black foldable `915 MHz` SMA antennas**, the **`4-pin to 6-pin JST-GH` Pixhawk telemetry cable**, and a USB-C cable.
2. Pick **1 of the 2 translucent `LR900-F` modules** (both are identical — 1 goes on the Drone, 1 stays in the box for your Ground Laptop) and **screw 1 black foldable `915 MHz` antenna finger-tight onto its gold `SMA` connector BEFORE powering on**.
3. Click the **narrow `4-pin` white plug** into the translucent `LR900-F` module, gently push aside the black/red PWM wires on your **`Pixhawk 6C`**, and click the **wider `6-pin` white plug** into **`TELEM2` (`Row 4, Center 6-Pin Socket`, between `TELEM1` and `TELEM3`)**:

![Step 6A — Lift Foam Tray in Box #4, Screw Black 915MHz Antenna onto 1 Translucent LR900-F Module & Plug 6-Pin End into Pixhawk 6C TELEM2 (Row 4, Center)](assets/block2_step6a_lr900f_antenna_and_telem2_v2.jpg)

#### Step 6B — Verify `Step 6A` (`#4 LR900-F` $\rightarrow$ `TELEM2`) & Connect `#2 MicoAir MTF-02P` Optical Flow Sensor $\rightarrow$ `TELEM3` (`Row 4, Right`)
1. **Pick the `4-Pin to 6-Pin` Cable in Box `#2` (`MicoAir MTF-02P`, `Green`):** Inside the black foam tray of the small white `MTF-02P` box are 3 cables; pull out the **one cable that has a wider `6-pin` Pixhawk plug (with 2 empty middle slots) on one end and a narrow `4-pin` plug on the other end** (`Red/Yellow/Green/Black` wires, matching `IMG_9396`). Leave the other 2 cables (`Slate-Grey`) in the box.
2. **Click the `4-Pin` End Into the `MTF-02P` Sensor Board:** Push the narrow `4-pin` white plug firmly into the white `4-pin` socket on the right edge of the tiny square black `MTF-02P` board.
3. **Click the `6-Pin` End Into `TELEM3` (`Row 4, Right Socket`):** Plug the wider `6-pin` white plug into **`TELEM3` (`Row 4, Right 6-Pin Socket`, immediately to the right of `TELEM2`)**, with the **`Red` (`+5V`) wire on the right side (`Pin 1`)** and **`Black` (`GND`) on the left side (`Pin 6`)**, matching `TELEM2` right next to it:

![Step 6B — Step 6A Verified (#4 LR900-F -> TELEM2) & Connect #2 MicoAir MTF-02P 4-to-6-Pin Cable Into Pixhawk 6C TELEM3 (Row 4, Right)](assets/block2_step6b_mtf02p_to_telem3_v1.jpg)

#### Step 6C — Verify `Step 6B` (`#2 MTF-02P` $\rightarrow$ `TELEM3` in `IMG_9406`) & Check `#1 Benewake TF02-Pro` (`Cyan`) Box Foam + `4-Pin` Plug
1. **Leave `#4 LR900-F` (`Purple`) & `#2 MTF-02P` (`Green`) Un-Taped While Connectors Are Checked:** Both `TELEM2` (`#4 LR900-F`) and `TELEM3` (`#2 MTF-02P`) are verified in `IMG_9406.jpg` with `Red (+5V)` on Right `Pin 1` and `Black (GND)` on Left `Pin 6`. Leave both modules resting loose for a moment so your fingers and tweezers remain unblocked around `Pixhawk 6C`.
2. **Peek Under the Foam in Box `#1` (`Benewake Rangefinder`, `Cyan`) & Lay Out the Spare `4-Pin` Cables:** Lift out the foam insert inside the white `Benewake` box to check for any hidden adapter cable or `M2.5` screw bag, untwist the `TF02-Pro` black cable (`4-pin 1.25mm Molex PicoBlade` plug: `Red=+5V, White=RXD/SDA, Green=TXD/SCL, Black=GND`), and lay the 2 remaining spare `4-pin` cables from Box `#2` (`MTF-02P` foam tray) next to it on the white towel:

![Step 6C — Step 6B Verified (TELEM2 & TELEM3 in IMG_9406) & Check Box #1 Foam + 4-Pin Plugs for #1 Benewake TF02-Pro](assets/block2_step6c_tf02pro_connector_and_box_check_v2.jpg)

3. **No Screws in Box `#1` Is 100% Expected — We Use Your Existing `3M` Foam Pads on the White Towel:**
   * **`#4 MicoAir LR900-F` (`Purple`):** Uses the **Square Red `3M VHB` foam pad** from your `Step 5` white towel (`IMG_9261.JPG`) to stick onto the flat left carbon deck (clear of the motor screw heads, with its black `915 MHz` antenna pointing straight **UP**).
   * **`#2 MicoAir MTF-02P` (`Green`):** Uses the **White `3M` foam pad** included inside Box `#2` directly underneath the `MTF-02P` sensor board (`IMG_9391.JPG`).
   * **`#1 Benewake TF02-Pro` (`Cyan`):** Uses a strip of your **leftover Red `3M VHB` foam tape** on its flat backplate (plus an optional nylon zip-tie loop through one side ear), which isolates the optical lenses from frame vibration without needing any screws!

![Step 6C — Stick Down #4 LR900-F Antenna Box on Top of Left Deck (100% Purple) & Flip #2 MTF-02P Ground Camera onto Underside of Right Deck (100% Green)](assets/block2_step6c_stick_lr900f_top_and_mtf02p_underneath_v4.jpg)

#### Step 6D — `Step 6C` Verified (`IMG_9424`–`IMG_9429`) & 2-Minute Finisher: Stick `#1 Benewake TF02-Pro` (`Cyan`) Under the Front `Platform Board`
1. **`Step 6C` Verified (`IMG_9424`–`IMG_9429`):** `#4 MicoAir LR900-F` (`Purple`) is mounted on the left carbon deck with a custom-cut `3M VHB` pad (`IMG_9417`) and vertical `915 MHz` dipole (`IMG_9427`); `#2 MicoAir MTF-02P` (`Green`) is mounted on the underside of the lower `G2: PDB` carbon deck (`IMG_9425` & `IMG_9426`) aiming straight down (`-90° Nadir`) with zero obstruction.
2. **2-Minute Finisher (`#1 Benewake TF02-Pro`, `Cyan`):** Stick a strip of leftover Red `3M VHB` foam tape onto the flat backplate of `#1 Benewake TF02-Pro` (`Cyan`) and press it onto the underside of the Front `Platform Board` (`IMG_9425`) so its 2 optical lenses point straight down (`-90° Nadir`) at the ground:

![Step 6D — Step 6C Verified (#4 Purple & #2 Green) + 2-Minute Finisher to Stick #1 Benewake TF02-Pro (Cyan) Under Front Platform Board](assets/block2_step6d_verified_and_2min_stick_tf02pro_v1.jpg)

3. **`Step 6D` Nightly Milestone Verified (`IMG_9430`–`IMG_9436`):** `#1 Benewake TF02-Pro` (`Cyan`) is mounted dead-center on the underside of the Front `Platform Board` (`IMG_9432` & `IMG_9436`) with a custom-cut `3M VHB` foam pad (`IMG_9430` & `IMG_9431`), aiming straight down (`-90° Nadir`) with its cable tucked cleanly into the ventral bay:

![Step 6D Verified — All 3 Modules Mounted (#1 TF02-Pro Cyan Under Nose, #2 MTF-02P Green Under Deck, #4 LR900-F Purple on Left Deck)](assets/block2_step6d_nightly_milestone_verified_v2.jpg)

#### Step 6E — Splice `#1 Benewake TF02-Pro` (`Cyan`) `4-Pin` Plug to the `6-Pin JST-GH` Pigtail Using Fine-Tip Tweezers (`[T05]`) & Plug Into `TELEM1` (`Row 4, Left`)

> [!IMPORTANT]
> **MANDATORY TOOL FOR `STEP 6E`: FINE-TIP PRECISION TWEEZERS (`[T05]`)**
> * **Why Bare Fingers Alone Will Fail Here:** The 4 tinned silver tips on the `6-pin JST-GH` pigtail (`Red, White, Blue, Black`) are ultra-thin (`30 AWG`) and must slide straight into the tiny `1.25 mm`-pitch holes of the white `4-pin Molex PicoBlade` plug on the `#1 Benewake TF02-Pro` cable (`IMG_9545`). Trying to push them in by hand from further back on the insulation causes the wire to buckle.
> * **Exact Tweezer Technique (`IMG_9545`–`IMG_9553`):** Grip each wire with **fine-tip precision tweezers (`[T05]`)** just **`2–3 mm` behind the tinned silver tip** and push it straight into its matching hole:
>   * **`RED` tip** $\rightarrow$ **`Hole 1` (`Red` wire = `+5V`)**
>   * **`WHITE` tip** $\rightarrow$ **`Hole 2` (`White` wire = `RXD`)**
>   * **`BLUE` tip** $\rightarrow$ **`Hole 3` (`Green` wire = `TXD`)**
>   * **`BLACK` tip** $\rightarrow$ **`Hole 4` (`Black` wire = `GND`)**
>   * **Skip `Yellow` & `Green` wires (`Slate-Grey`):** Twist the 2 unused middle wires (`Pin 4` & `Pin 5`) neatly back out of the way (`IMG_9552`).
> * Wrap the joined `4-pin` splice tightly in **`3M ScotchBlue` tape (`IMG_9550`)**, spiral the slack around the **Rear-Left (`M2`) carbon arm (`IMG_9555`–`IMG_9557`)**, and click the white `6-pin` plug into **`TELEM1` (`Row 4, Left` — directly 1 row below the wide `10-pin GPS1` socket, `IMG_9553` & `IMG_9560`)**!

![Step 6E Fix — Your #1 LiDAR Cable Splice Is 100% Right! Plug It Into TELEM1 (Row 4, Left — 1 Row Below GPS1)](assets/block2_step6e_tf02_splice_verified_plug_into_telem1_row4_v2.jpg)

![Step 6E Complete! #1 TF02-Pro LiDAR (CYAN) Is Plugged Into TELEM1 & Spiraled on M2 Arm — Plus Next 10-Second Step](assets/block2_step6e_complete_and_next_step_ppm_sbus_or_block3_v2.jpg)

#### Step 6F — Wire & Mount `#3 RadioMaster RP3 V2` ExpressLRS 2.4GHz Nano Receiver (`[D10]`, `Yellow`, Verified in `IMG_9685`–`IMG_9690`)
1. **Remove the Unused `GREEN` Wire & Strip `~5 mm` off `WHITE`, `RED`, `BLACK` Using Precision Wire Strippers (`[T09]`, `IMG_9685`–`IMG_9687`):**
   * Because the `PPM/SBUS RC` harness on the `Pixhawk 6C` uses a `3-pin` servo socket (`Black = GND`, `Red = +5V`, `Yellow = Signal`), untwist and remove the **`GREEN` wire** completely from the 4-wire silicone bundle (`Slate-Grey` — not used).
   * Using the **`24/22 AWG` stranded slot (`STRO 24/22`) of a Precision Wire Stripper (`[T09]`, `IMG_9687`)**, strip `~5 mm` of soft silicone insulation off **both ends** of **`WHITE`**, **`RED`**, and **`BLACK`**, keeping all tinned strands intact.
2. **Thread `WHITE`, `RED`, `BLACK` Through the 3 Gold Through-Holes (`[T]`, `[5V]`, `[-]`) on the `RP3 V2` Board (`Verified in IMG_9689 & IMG_9690`):**
   * Leave the leftmost **`[R]`** gold through-hole **100% EMPTY (`Slate-Grey`)**.
   * Thread the stripped wire tips from underneath the PCB through the remaining 3 gold holes and fold each loop `180°` back over the board edge onto its own insulation (`IMG_9690`):
     * **`[T]` (2nd hole)** $\leftarrow$ **`WHITE` wire**
     * **`[5V]` (3rd hole)** $\leftarrow$ **`RED` (`+5V`) wire**
     * **`[-]` / `[G]` (Outer corner hole)** $\leftarrow$ **`BLACK` (`GND`) wire**
   * **Tweezer-Creased Blue `3M` Tape Partition-Crimp Method (`IMG_9691`–`IMG_9697` — Superior to Loose Heat-Shrink Tube):** Lay the `RP3 V2` PCB edge and the 3 separated wires (`BLACK`, `RED`, `WHITE`) onto the sticky side of a strip of **blue `3M` painter's tape (`[T06]`, `IMG_9691`)**, fold the tape wings over the top, and press the **flat blade of Fine-Tip Tweezers (`[T05]`, `IMG_9692`)** firmly into the valleys between `BLACK` and `RED` and between `RED` and `WHITE`. This bonds top-tape to bottom-tape between each wire (`IMG_9694` & `IMG_9697`), forming 2 solid adhesive partition walls so the 3 wire loops can **never** slide sideways or touch under flight vibration.
3. **Plug the Other Ends Into the Drone's Loose Black `3-Pin` `PPM/SBUS RC` Socket & Tape Both `6 cm` `T`-Antennas Along the Two Perpendicular Carbon Deck Edges (`Verified in IMG_9704–IMG_9710`):**
   * Push the other stripped ends of **`BLACK`**, **`RED`**, and **`WHITE`** into the loose black `3-pin` female socket (`BLACK -> BLACK [GND]`, `RED -> RED [+5V]`, `WHITE -> YELLOW [RC Signal]`, `IMG_9704`), wrap the joint tightly with blue `3M` tape (`IMG_9705`), and tuck it onto the top harness bundle (`IMG_9708`).
   * **Bench-Proven `6 cm` Antenna Reach & Perpendicular Deck-Edge `90°` Diversity Rule (`IMG_9707`–`IMG_9710`):** Because each black coaxial `T`-antenna lead is only `6 cm` (`2.4 inches`) long, it cannot stretch across the `144 mm` carbon deck to two separate arms, and the round `M2` sticker is surrounded by 3 raised metal `M3` button-head screw heads. Instead:
     * **Board Location (`Screw-Free Flat Carbon Rectangle`):** Tape the `RP3 V2` board flat onto the wide-open, screw-free black carbon rectangle between the `Pixhawk 6C`, the clear `#4 LoRa` box, and the white `M2` circle (`IMG_9708`–`IMG_9710`).
     * **Antenna #1 (`Rear/Bottom Carbon Edge —`):** Tape the first black `T`-antenna horizontally along the rear/bottom edge of the carbon top plate (right next to the `#4 LoRa` antenna base, `IMG_9708`).
     * **Antenna #2 (`Right Carbon Edge |`):** Tape the second black `T`-antenna vertically along the right edge of the carbon top plate (`next to M2 / M3`, `IMG_9708`). Because those two carbon plate edges meet at a `90°` corner, the two `T`-bars automatically form a textbook **`90°` (`L`-shape, `—` vs. `|`) orthogonal diversity angle** with zero cable tension and 100% propeller clearance!

![Step 6F Action 1 Verified — Precision Wire Stripper [T09] (IMG_9687) + Textbook Through-Hole Wrap on RP3 V2 (IMG_9690) & Action 2 Plug-In Guide](assets/block2_step6f_part1_wires_on_rp3_verified_and_part2_plug_into_drone_v3.jpg)

![Step 6F Tweezer-Creased Blue 3M Tape Partition Crimp Verified (IMG_9691–9697) & Action 2 Plug-In Guide](assets/block2_step6f_blue_tape_partition_crimp_verified_and_plug_into_drone_v2.jpg)

![Step 6F 11 PM Dead-Simple 2-Box Placement Guide — Box 1 (3-Pin Plug) & Box 2 (Screw-Free Flat Carbon Rectangle)](assets/block2_step6f_11pm_dead_simple_2_steps_v2.jpg)

![Step 6F 100% Complete — 3-Pin RC Plug Splice & Blue Tape Lock (IMG_9704/9705) + RP3 V2 Board & 90° Orthogonal Edge T-Antennas Installed (IMG_9708/9710)](assets/block2_step6f_complete_100pct_hardware_finished_v4.jpg)

Mount both downward range/flow sensors underneath the front/ventral plate aiming **straight down at the ground (`-90° Nadir`)** with an unobstructed view between the `270 mm` landing skids:

| Sensor / Radio | Part Code | Target Port on `Pixhawk 6C` | Exact Pin-by-Pin Wire Color & Crossover Check |
| :--- | :---: | :---: | :--- |
| **`Benewake TF02-Pro` `40 m` LiDAR** *(Aimed straight down `-90°` nadir)* | **`[D09]`** | **`TELEM1` (`SERIAL1`, Row 4 Left)** *(6-pin `JST-GH`, `115200` baud, `RNGFND1_TYPE = 20`, `SERIAL1_PROTOCOL = 9`)* | • **`Pin 1 (+5V, Right)`** $\leftarrow$ `RED` $\rightarrow$ `TF02-Pro` **`RED` (`+5V`)**<br>• **`Pin 2 (TX)`** $\leftarrow$ `WHITE` $\rightarrow$ `TF02-Pro` **`WHITE` (`RXD`)**<br>• **`Pin 3 (RX)`** $\leftarrow$ `BLUE` $\rightarrow$ `TF02-Pro` **`GREEN` (`TXD`)**<br>• **`Pin 4 & 5`** $\leftarrow$ **`Slate-Grey EMPTY`** *(Twist `Yellow & Green` neatly back)*<br>• **`Pin 6 (GND, Left)`** $\leftarrow$ `BLACK` $\rightarrow$ `TF02-Pro` **`BLACK` (`GND`)** |
| **`MicoAir MTF-02P` Optical Flow + ToF** *(Aimed straight down `-90°` nadir, lens clean)* | **`[D12]`** | **`SERIAL5` (`TELEM3` / `USER`)** *(6-pin `JST-GH`, `115200` baud, `FLOW_TYPE = 6`)* | • **`Pin 1 (+5V)`** $\leftarrow$ `MTF-02P` **`RED` (`+5V`)**<br>• **`Pin 2 (TX)`** $\leftarrow$ `MTF-02P` **`RX`**<br>• **`Pin 3 (RX)`** $\leftarrow$ `MTF-02P` **`TX`**<br>• **`Pin 4 & 5`** $\leftarrow$ **`Slate-Grey EMPTY`** *(Leave bare)*<br>• **`Pin 6 (GND)`** $\leftarrow$ `MTF-02P` **`BLACK` (`GND`)** |
| **`RadioMaster RP3 V2` Primary C2 Receiver** *(Mount 2× T-antennas at `90°` on rear arms)* | **`[D10]`** | **`SERIAL6` (`PPM/SBUS RC`, Row 5 Left)** *(`5-pin JST-GH`, `420000` baud `CRSF`)* | • **`+5V`** $\leftarrow$ **`RED`**<br>• **`GND`** $\leftarrow$ **`BLACK`**<br>• **`TX` / `RX`** $\leftarrow$ Cross-wired (`RP3 TX -> FC RX`, `RP3 RX -> FC TX`) |
| **`LR900-F` / `ELRS-R24-D` Telemetry Link** *(Mount dipole vertical on opposite skid)* | **`[D01]`** | **`TELEM2`** *(6-pin `JST-GH`, `57600` / `115200` MAVLink2)* | • **`Pin 1 (+5V)`** $\leftarrow$ **`RED`**<br>• **`Pin 2 (TX)`** $\leftarrow$ **`RX`**<br>• **`Pin 3 (RX)`** $\leftarrow$ **`TX`**<br>• **`Pin 4 & 5 (CTS/RTS)`** $\leftarrow$ **`Slate-Grey EMPTY`**<br>• **`Pin 6 (GND)`** $\leftarrow$ **`BLACK`** |

---

## BLOCK 3 (`~1.0 Hour`): `Raspberry Pi 5` Companion (`[D05]`), Under-Board `USB-C` Link, `5V/5A UBEC` (`[D06]`), Dual Thermal/Starvis Pod & 30-Second Multimeter Smoke Test

### Step 3.1 (`Steps 7A–7C`) — Mount `Raspberry Pi 5` on Double-Stacked `3M` Foam Risers, Route White `USB-C` Link Under the Deck & Dress Harness With White Twist-Tie Ring

1. **`Step 7A` (`Double-Stacked 3M Foam Risers + Blue 3M Painter's Tape Strap`, `IMG_9471`–`IMG_9485`):**
   * Because the `M1` & `M4` arm clamp screw heads sit proud of the right carbon deck (`G3`), stack a double layer of grey `3M` foam strips under the front-edge of the **`Raspberry Pi 5` (`8GB`, `Gold`)** so the PCB clears the screw heads with zero metal-to-solder contact, and secure the front silver USB/Ethernet ports with blue `3M` painter's tape.
2. **`Step 7B` (`Under-Board White USB-C MAVLink2 Link + Front-Right M1 Arm Spiral`, `IMG_9490`–`IMG_9501`):**
   * Because the `Pixhawk 6C` `USB-C` port sits on the lower left edge near the `M10 GPS` mount, route the right-angle **`USB-C` end** of the white cable **underneath the top carbon plate (`G3`)** inside the `19 mm` sandwich gap (`IMG_9491`), plug the **`USB-A` end** into the front `USB 2.0` port of the `Raspberry Pi 5`, and spiral the excess white cable around the **Front-Right (`M1`) carbon arm** (`IMG_9493`).
   * **Bonus Benefit:** Connecting the `Raspberry Pi 5` to `Pixhawk 6C` via `USB-C` (`MAVLink2` virtual USB serial port `/dev/ttyACM0`) leaves **`TELEM1` (`Row 4, Left`) 100% free** for the `#1 Benewake TF02-Pro 40m LiDAR` (`Step 6E`) and prevents any `5V` back-feeding between the `UBEC` and `TELEM1`!
3. **`Step 7C` (`White Twist-Tie Harness Ring + Rear Braided ESC Wire Tuck`, `IMG_9502`–`IMG_9534`):**
   * Gather the loose sensor wires above the `Pixhawk 6C` into a single neat circular loop secured with a **white twist-tie (`IMG_9508`)**, and pull the rear white/black braided `M1–M4` ESC signal wires down through the rear oval carbon slot into the `19 mm` sandwich gap between the plates (`IMG_9532` & `IMG_9534`):

![Step 7B Verified — Under-Board White USB-C Cable Routing & M1 Arm Spiral Wrap](assets/block3_step7b_underboard_usbc_verified_and_status_v2.jpg)

![Step 7C Verified — Same-Angle Before vs After Comparison & Rear Braided ESC Wire Tuck Into 19mm Sandwich Gap](assets/block3_step7c_same_angle_before_after_and_rear_tuck_v2.jpg)

### Step 3.2 — Wire & Mount the `ArduCam B0205` Day/Night IR USB Camera (`[D03]`, `Steps 7D–7F`) & `TOPDON TC001` Thermal Camera (`[D02]`, `Step 8`)

1. **`Step 7D` (`ArduCam 4-Pin USB Cable vs. 3-Pin PPM/SBUS RC Cable`, `IMG_9565`–`IMG_9570`):**
   * Do **not** confuse the black `3-pin` servo end of the `Red/Black/Yellow` RC cable plugged into `PPM/SBUS RC` (`Row 5, Left` on `Pixhawk 6C` — `YELLOW`, which goes to the `#3 RadioMaster RP3 V2` receiver) with the `ArduCam`'s dedicated black USB cable (`GOLD`).
   * Take the black USB cable that came inside the `ArduCam` box (`white 4-pin plug` on one end, `silver USB-A plug` on the other) and click its **white `4-pin` plug** into the matching `4-pin` socket on the back of the **`ArduCam` (`[D03]`)**.
2. **`Step 7E` (`Plug ArduCam USB-A Into Free Top Blue USB 3.0 Port on Raspberry Pi 5`):**
   * Plug the silver `USB-A` end of the `ArduCam` cable into the **already-open top blue `USB 3.0` port** on the `Raspberry Pi 5` (right above the white `USB-C` cable, without disturbing the blue `3M` protective tape).
3. **`Step 7F` (`Spiral Excess Cord on Arm M3 & Super-Glue U-Bracket Foot In Front of Leg`, `IMG_9578`–`IMG_9589`):**
   * Spiral the excess black `ArduCam` USB cable tightly around the **bare Front-Left (`M3`) carbon arm** and secure the coil with **blue `3M` tape (`[T06]`)**.
   * Lay a clear plastic ESD bag underneath the drone to protect the floor/table, pop the clear plastic protective cap off the `ArduCam` lens, and place **3 drops of `Loctite Super Glue Liquid` (`[T07]`)** onto the flat bare carbon strip **in front of the left landing-gear leg mount (`IMG_9588`)**.
   * Orient the `ArduCam` so the **small green daylight-sensor circle (`photoresistor`) faces the open Front Nose (`toward the #1 TF02-Pro LiDAR`, away from the black carbon leg post so the leg never shadows the daylight sensor, `IMG_9589`)**, press the slotted ring of the `U`-bracket foot onto the 3 super-glue drops, and hold firmly for `45–60 seconds` until cured (`IMG_9585` & `IMG_9586`).
4. **`Step 8` (`TOPDON TC001` LWIR Thermal Camera `[D02]` — `ArduCam` Box Foam Shim + Finnish `Fiskars` Scissors `[T08]` + `Loctite Super Glue` `[T07]`, `IMG_9608`–`IMG_9635`):**
   * Connect the blue **`TOPDON TC001` (`256×192` LWIR Thermal Camera `[D02]`)** to the female `USB-C` socket of its included black braided extension cable, peel back the right vertical strip of blue `3M` tape on the front of the **`Raspberry Pi 5`**, plug the silver `USB-A` end into **either BLACK `USB 2.0` port** (`IMG_9608`), press the blue `3M` tape back down, and spiral the excess cable around the **Rear-Left (`M2`) carbon arm** with blue `3M` tape (`IMG_9609`).
   * **Why a Custom Foam Standoff Shim Is Required Behind the Leg (`IMG_9610`–`IMG_9621`):** Because the rear underside carbon bay (`behind the leg post`) has protruding M3 button-head screw heads, the wide (`56 × 30 mm`) rigid aluminum back of the `TOPDON TC001` cannot sit flush directly on the bare carbon.
   * Take the **dense black closed-cell EPE packaging foam block from the blue `ArduCam` box (`IMG_9614`)** *(strictly use the `ArduCam` box foam — do **not** use the thin foam lining from the larger black box)* and use **Finnish `Fiskars` orange-handled scissors (`[T08]`, `IMG_9616`)** to cut fitting foam standoff shims that sit in the flat spaces between the screw heads.
   * Bond the custom-cut `ArduCam` foam shims to the carbon plate **behind the leg** using **`Loctite Super Glue Liquid` (`[T07]`, `IMG_9617`–`IMG_9621`)** to form a raised, screw-clearing, vibration-damping, thermally isolated flat pad.
   * Apply `Loctite Super Glue` to the flat `"TOPDON"` metal back of the `TC001` (`IMG_9622`) and press it firmly onto the raised foam pad **behind the leg (`IMG_9623` & `IMG_9633`)** with its round thermal lens pointing **straight down (`-90°` nadir)**.

![Step 7D Visual Guide — Two Separate Cables: 3-Pin PPM/SBUS RC Cable (YELLOW) vs. 4-Pin ArduCam USB Cable (GOLD)](assets/block3_step7d_two_separate_cables_yellow_rc_vs_gold_arducam_usb_v2.jpg)

![Step 7E Visual Guide — Plug ArduCam Silver USB-A Into Already-Open Top Blue USB 3.0 Port on Raspberry Pi 5](assets/block3_step7e_plug_arducam_into_free_top_usb3_port_v2.jpg)

![Step 7F Visual Guide — Field of View Verification & Arm M3 Spiral Wrap (IMG_9583 & IMG_9584)](assets/block3_step7f_complete_fov_verified_and_lens_cap_tip_v2.jpg)

![Step 7F Complete Visual Guide — 3 Drops of Loctite Super Glue on Carbon Strip (IMG_9588) & Green Daylight Sensor Toward Front Nose (IMG_9589 & IMG_9586)](assets/block3_step7f_loctite_super_glue_and_green_sensor_orientation_v2.jpg)

![Step 7F Final Standing Ground-Clearance Check (>200mm Above Skids) & Underside Map for Option A (TOPDON TC001 — GOLD) & Option B (#3 RadioMaster RP3 V2 — YELLOW)](assets/block3_step7f_final_standing_verified_and_proceed_to_a_and_b_v5.jpg)

![Step 8 Verified — ArduCam Box Foam + Finnish Fiskars Scissors [T08] + Loctite Super Glue [T07] Standoff Shim for TOPDON TC001 [D02] & Next Step 6F (#3 RadioMaster RP3 V2 [D10])](assets/block3_step8_fiskars_foam_shim_verified_and_step6f_rp3_guide_v3.jpg)

5. **`Step 9` (Final Hardware Step — Mounting `#3 RadioMaster RP3 V2` `[D10]` & `2x` Black T-Shaped Antennas at `90°` Along the Deck Edges, `IMG_9704`–`IMG_9710`):**
   * Plug the 3-pin wire splice from your `#3 RadioMaster RP3 V2` (`Black = GND`, `Red = +5V`, `White = T / RC Signal`) into the black 3-pin plug coming from `Pixhawk 6C` `PPM/SBUS RC` (`Black -> Black`, `Red -> Red`, `White -> Yellow`, `IMG_9704`) and wrap the mated 3-pin junction tightly in **blue `3M` painter's tape (`[T10]`, `IMG_9705`)**.
   * Seat the blue-taped `#3 RadioMaster RP3 V2` board onto the flat, screw-free carbon rectangle just above the `M2` sticker and below the `#4 LR900-F` module (`IMG_9708`), then press a strip of **blue `3M` tape** flat over the board to seal and lock it down (`IMG_9709` & `IMG_9710`).
   * Tape **T-Antenna #1 (`Vertical |`)** along the **left carbon deck edge** and **T-Antenna #2 (`Horizontal —`)** along the **bottom/rear carbon deck edge** using blue `3M` tape (`IMG_9708`–`IMG_9710`). This creates a **true `90°` orthogonal L-shape** around the `M2` corner with zero coax strain and `> 120 mm` propeller clearance.

![Final Build Step (Step 9) — 2x Black T-Shaped Antennas Taped at 90° Along Left (|) & Bottom (—) Deck Edges & #3 RP3 V2 Sealed Under Blue 3M Tape (IMG_9708 & IMG_9710)](assets/block3_step9_final_t_antennas_and_rp3_mounted_on_deck_v3.jpg)

![Opaslyhty 100% Completed Airframe — 500 mm Quad-X with 210 mm Finnish Fiskars Scissors [T08] for Scale (IMG_9711) & Overhead/Isometric Views (IMG_9712–IMG_9714)](assets/opaslyhty_100pct_completed_airframe_with_fiskars_scale_v3.jpg)

### Step 3.3 — Mandatory 30-Second Multimeter Smoke Test (`[T03]`) & One-Command Bring-Up

> [!IMPORTANT]
> **NEVER PLUG A BATTERY IN BEFORE RUNNING THESE 2 MULTIMETER CHECKS (`30 SECONDS`):**

1. **Check #1 — `XT60` Zero-Short Resistance Check (`Battery Unplugged`):**
   * Turn your **`AstroAI` Digital Multimeter (`[T03]`)** dial to **`Resistance (Ω / 20kΩ)`**.
   * Touch the **Red probe** to the `+` (rounded) pin and the **Black probe** to the `-` (flat) pin inside the drone's yellow **`XT60` male plug**.
   * **Pass Criterion:** The meter **must read `> 10 kΩ` (or `OL` / climbing as capacitors charge)**—**NEVER `< 100 Ω` or `0.0 Ω`!**
2. **Check #2 — `5.10V DC` UBEC Output Check (`Before Plugging Into Raspberry Pi 5`):**
   * Leave the `5V/5A UBEC` output **unplugged** from the `Raspberry Pi 5`.
   * Connect a `4S` (`14.8V`) bench supply or battery to the `XT60` lead, switch your multimeter to **`DC Volts (V= / 20V)`**, and measure the `UBEC` output plug: confirm it reads **strictly `+5.05V to +5.18V DC`** (never `14.8V`!).
   * Unplug power, connect the verified `5.1V UBEC` output to the `Raspberry Pi 5`, and run the automated bench doctor from your MacBook:
     ```bash
     cd .
     python3 opaslyhty_physical_build/run_guided_bench_doctor.py
     ```
   * Load the verified Arctic SAR parameter file (`configs/pixhawk6c_4s_sar.param` / `firmware/opaslyhty_sar_quad_fc_config.param`) onto the `Pixhawk 6C` via QGroundControl / MAVProxy (`BATT_CRT_VOLT = 12.8V`, `TERRAIN_MARGIN = 25.0 m`, `RNGFND1_TYPE = 20`, `FLOW_TYPE = 6`).
