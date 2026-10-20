# Arctic Trail Cam System — IKEA-Style Manual Part 1: Indoor Benchtop Assembly & Bring-Up (Stages 1–3)

> **Zero Electronics Experience Required:** This manual is written like an IKEA assembly guide. You do **not** need to know how to solder or read circuit schematics. Simply match each part in your hands to its **`[P##]` Part Code**, check the **"Which Way Round Does It Fit?"** box before plugging anything in, and follow each numbered step in order.
>
> * Single pin reference: [Wiring & Pinout Schedule](AERIAL_OBSERVATION_DRONE_GUIDE.md)
> * Full hardware parts list: [Hardware Configuration & BOM](AERIAL_OBSERVATION_DRONE_GUIDE.md)
> * Next manual after bench bring-up: [Part 2 — Enclosure Build, Camouflage & Tree Installation (Stages 4–6)](AERIAL_OBSERVATION_DRONE_GUIDE.md)

---

## Step 0: Check Your Parts (`[P01]`–`[P24]`) & Identify Your 3 "Raspberry Pi" Boards

Full itemized part prices (`[P01]`–`[P24]`) and tool specifications (`[T01]`–`[T12]`) are maintained in **[`HARDWARE_SPECS_AND_BOM.md`](AERIAL_OBSERVATION_DRONE_GUIDE.md)**.
* **Stages 1–2 (Indoor Core Benchtop — `$233.37`):** Use **`[P01]`**, **`[P02]`**, **`[P04]`–`[P10]`**, **`[P23]`** (`Cat6` Ethernet cables), **`[P24]`** (`USB-C` Gigabit Ethernet adapter), and household tools **`[T01]`–`[T03]`** (fingernails/tweezers, your laptop, and a small steel screwdriver/key).
* **Stage 3 (Optical Fiber Data Diode — `+$169.30` / `$402.67` total):** Adds **`[P13]`–`[P16]`** and **`[P19]`** (plus the 2nd `Cat6` Ethernet cable in **`[P23]`**).
* **Leave the `12V 12Ah` Battery (`[P17]`) in its box during Stages 1–3!** On the indoor table, power **`Raspberry Pi 5 [P01]`** with its included `27W USB-C` wall adapter and **`Raspberry Pi Pico 2 [P07]`** via its Micro-USB data cable + USB-C adapter from your laptop (`[T02]`).

![Real-World Benchtop Unboxed Parts & Sub-Assemblies Overview (Photo 22)](images/real_build/stage2_05_bench_overview_boxes_and_boards.jpg)

### How to Identify Your 3 "Raspberry Pi" Boards at a Glance (DO NOT Mix Them Up!)

You have **three different green circuit boards** with "Raspberry Pi" in their name. Look at the physical ports on each board before starting so you never confuse them:

| Board Code & Exact Name | Physical Size & Shape | How to Spot It Instantly in 3 Seconds | What Role It Plays in This Build |
| :--- | :--- | :--- | :--- |
| **`[P01]` `Raspberry Pi 5 (8GB)` (`$80.00`)** *(Primary Camera Computer — **USE THIS BOARD!**)* | Credit-card size (`85 × 56 mm`), flat underside with MicroSD slot | 1. Silver **Gigabit Ethernet port is on the BOTTOM-RIGHT corner** (below the blue USB 3.0 ports).<br>2. Has **two narrow vertical beige/brown `22-pin` slots labeled `CAM/DISP 0` & `CAM/DISP 1`** between the micro-HDMI ports and Ethernet.<br>3. Has **two round mounting holes** beside the silver CPU for the **`[P02]` Active Cooler** + a white 4-pin `FAN` socket (`J11`) at top-right. | **Main Field Camera & AI Computer (Stages 1–6).** All `[P02]` Active Cooler, `[P03]` Hailo-8L, and `[P06]` `22-pin` Camera Ribbon steps use **this exact board (`Raspberry Pi 5 8GB [P01]`)**. |
| **`[P01-ALT]` `Raspberry Pi 4 Model B (8GB)` (`$75.00`)** *(Secondary Board — **SET ASIDE**)* | Credit-card size (`85 × 56 mm`), looks similar to Pi 5 at first glance! | 1. Silver **Gigabit Ethernet port is on the TOP-RIGHT corner** (above the blue USB 3.0 ports — the exact opposite of the Pi 5!).<br>2. Has only **one wide (`15-pin`) white/black `CAMERA` slot**.<br>3. Has **NO mounting holes** and **NO 4-pin `FAN` socket** for the Pi 5 Active Cooler (`[P02]`). | **Do NOT use for the `22-pin` camera cable `[P06]` or Active Cooler `[P02]`!** Keep this Pi 4 aside as a spare or for a remote Collector Hub (`Variant 3B`). |
| **`[P07]` `Raspberry Pi Pico 2 (RP2350H)` (`$6.00`)** *(Tiny Gatekeeper Microcontroller)* | Stick-of-gum size (`51 × 21 mm`, $1/4$ the size of Pi 5) | 1. Has **40 long metal legs soldered down both long edges** (`20 legs on the left`, `20 legs on the right`) so it presses into the white **Solderless Breadboard (`[P09]`)**.<br>2. Has a tiny silver **Micro-USB port** at one end and a tiny white button labeled **`BOOTSEL`**.<br>3. **Has NO MicroSD card slot** and NO Ethernet/HDMI ports! | **Always-On `<4 mW` Sensor Gatekeeper (Stages 1–6).** Plugs into the white breadboard (`[P09]`), reads the `QMC5883L` magnetometer (`[P08]`) & radar (`[P11]`), and wakes the Pi 5 (`[P01]`). |

---

## STAGE 1: Prepare the `Raspberry Pi 5 (8GB)` (`[P01]`), Flash the MicroSD (`[P04]`) & Flash the `Pico 2` (`[P07]`)

### Step 1.1 — Snap the Active Cooler (`[P02]`) onto the `Raspberry Pi 5 (8GB)` (`[P01]`)

1. Unplug all power cables from the **`Raspberry Pi 5 (8GB)` (`[P01]`)** and set it flat on the table with the silver USB and Ethernet ports facing right. *(Confirm you are holding the **`Raspberry Pi 5 (8GB)` `[P01]`**—its silver Ethernet port is at the **bottom-right corner**, and you will see **two empty round mounting holes** on either side of the silver processor chip.)*
2. Pick up the **Pi 5 Official Active Cooler (`[P02]`)** and turn it upside down.
3. **CRITICAL:** Use your fingernail or tweezers (`[T01]`) to **peel off the clear plastic protective sheet** covering the pink/blue sticky thermal pads on the bottom of the cooler.
4. Hold the cooler right-side up over the **`Raspberry Pi 5 (8GB)` (`[P01]`)** so the two white plastic push-pins line up with the **two round mounting holes** on either side of the silver processor chip.
5. Press both white push-pins straight down with your thumbs until you hear two crisp **`CLICK`** sounds.
6. **Pop out the factory plastic dust cap from `J11` & plug in the 4-wire fan cable:** Look at the tiny white **4-pin `FAN` socket (`J11`)** at the top-right corner of the **`Raspberry Pi 5 (8GB)` (`[P01]`)** (between the black USB 2.0 ports and the 40 gold GPIO pins). A brand-new `Raspberry Pi 5` ships with a tiny removable cream-white plastic **pick-and-place dust cap** sitting inside `J11`. Use a fine tip, fingernails, or tweezers (`[T01]`) to gently lift and pop that tiny plastic cap straight up out of `J11`, then push the white 4-pin connector on the cooler's **4-wire cable** (`black/red/yellow/blue`) straight down into the open `J11` socket. *Which way it fits:* The tiny raised plastic guides on one side of the plug slide into the matching notch on the socket—do not force it upside down.

![Real-World Build Log — Stage 1.1 Part 1: Installing Active Cooler Heatsink on Pi 5 (Photos 1–7, 1 Step Per Row)](images/real_build/stage1_real_world_cooler_part1_heatsink.jpg)

![Real-World Build Log — Stage 1.1 Part 2: Removing J11 Factory Dust Cap & Seating 4-Wire Fan Plug (Photos 8–11, 1 Step Per Row)](images/real_build/stage1_real_world_cooler_part2_fan_plug.jpg)

* **Documented Real-World Stage 1.1 Prototype Build Photos (`11` Chronological Shots, `Photos 1–11`):**
  1. [Photo 1 (`stage1_01_unboxed_parts.jpg`)](images/real_build/stage1_01_unboxed_parts.jpg) — **Step 1.0:** Unboxed `Raspberry Pi 5 [P01]`, `Official Active Cooler [P02]`, and `Raspberry Pi Pico 2 With Headers [P07]` (`SKU 828988`, 40 pins pre-soldered) on the anti-static cloth.
  2. [Photo 2 (`stage1_02_peeling_thermal_film.jpg`)](images/real_build/stage1_02_peeling_thermal_film.jpg) — **Step 1.1A:** Peeling the clear protective backing sheet off the 3 blue thermal pads on the underside of `Official Active Cooler [P02]`.
  3. [Photo 3 (`stage1_03_cooler_top_alignment.jpg`)](images/real_build/stage1_03_cooler_top_alignment.jpg) — **Step 1.1B (Before Clicking Pins In):** Top-down alignment of `Active Cooler [P02]` (`6×7` bare aluminum fin grid on left, offset circular radial blower fan on right) positioned lightly over `Raspberry Pi 5 [P01]`.
  4. [Photo 4 (`stage1_04_hdmi_camdisp_clearance.jpg`)](images/real_build/stage1_04_hdmi_camdisp_clearance.jpg) — **Step 1.1C (Before Clicking Pins In):** Checking the bottom-left white spring push-pin by `USB-C` and clearance beside the two `22-pin` `CAM/DISP 0 & 1` ribbon slots prior to pressing the pins down.
  5. [Photo 5 (`stage1_07_fan_socket_j11_closeup.jpg`)](images/real_build/stage1_07_fan_socket_j11_closeup.jpg) — **Step 1.1D (Before Clicking Pins In):** Checking the top-right white spring push-pin aligned over its upper PCB mounting hole and locating the cream-white `J11` 4-pin `FAN` socket right beside the top `USB 2.0` port.
  6. [Photo 6 (`stage1_05_gpio_side_profile_pins_locked.jpg`)](images/real_build/stage1_05_gpio_side_profile_pins_locked.jpg) — **Step 1.1E (Push-Pins Clicked In):** Press both white push-pins straight down (`CLICK!`). Side profile along the 40-pin GPIO header confirming both white push-pin barbs clicked completely through the underside of the `Raspberry Pi 5` PCB with blue thermal pads compressed flat.
  7. [Photo 7 (`stage1_06_ports_edge_profile.jpg`)](images/real_build/stage1_06_ports_edge_profile.jpg) — **Step 1.1F (Push-Pins Clicked In):** Port-edge profile along `USB-C`, dual `micro-HDMI`, `CAM/DISP`, and Gigabit Ethernet confirming the bottom-left push-pin barb is locked through the PCB and the heatsink sits level.
  8. [Photo 8 (`stage1_07b_pointing_at_j11_dust_cap.jpg`)](images/real_build/stage1_07b_pointing_at_j11_dust_cap.jpg) — **Step 1.1G:** With both push-pins locked in, pointing at the tiny cream-white factory plastic pick-and-place dust cap sitting inside the `J11` 4-pin `FAN` socket.
  9. [Photo 9 (`stage1_07c_prying_j11_dust_cap.jpg`)](images/real_build/stage1_07c_prying_j11_dust_cap.jpg) — **Step 1.1H:** Gently levering and popping the tiny cream-white factory dust cap straight up out of the `J11` `FAN` socket.
  10. [Photo 10 (`stage1_07d_j11_cap_removed_socket_open.jpg`)](images/real_build/stage1_07d_j11_cap_removed_socket_open.jpg) — **Step 1.1I:** Removed factory dust cap held in the right hand, exposing the 4 vertical metal pins inside the open `J11` `FAN` socket on `Raspberry Pi 5 [P01]` (left hand).
  11. [Photo 11 (`stage1_07e_fan_cable_plugged_into_j11.jpg`)](images/real_build/stage1_07e_fan_cable_plugged_into_j11.jpg) — **Step 1.1J:** White 4-pin fan plug (`black/red/yellow/blue`) seated all the way down into `J11` beside the top `USB 2.0` port — **Active Cooler `[P02]` installation 100% complete!**

### Step 1.2 — Flash the MicroSD Card (`[P04]`) for the `Raspberry Pi 5 (8GB)` (`[P01]`) on Your MacBook Pro (`[T02]`)

1. **Plug the SD card into your MacBook Pro (`[T02]`):** Slide the **`SanDisk 64GB` MicroSD card (`[P04]`)** into its SD adapter sleeve and push it into the **SDXC slot on the right side of your MacBook Pro** (or plug your USB MicroSD card reader into a **`USB-C` port on the side of your MacBook Pro**).
2. **Open Terminal on your MacBook Pro:** Press **`⌘ Cmd + Space`** on your MacBook Pro keyboard to open Spotlight Search, type **`Terminal`**, and press **`Enter` (`Return`)**.
3. **Launch Raspberry Pi Imager from Terminal:** Type this exact command in Terminal and press **`Enter`**:
   ```bash
   open -a "Raspberry Pi Imager"
   ```
   *(If Raspberry Pi Imager is not installed yet, type `brew install --cask raspberry-pi-imager && open -a "Raspberry Pi Imager"` and press **`Enter`**).*
4. Follow the exact screens below in the Raspberry Pi Imager window (click each choice in order):
   * **Screen 1 — Choose Device:** Click **`Raspberry Pi 5`** (for your `Raspberry Pi 5 (8GB) [P01]`).
   * **Screen 2 — Choose OS:** Click **`Raspberry Pi OS (other)`** $\rightarrow$ select **`Raspberry Pi OS Lite (64-bit)`** (no desktop needed, boots fastest).
   * **Screen 3 — Choose Storage:** Select your `SanDisk 64GB` MicroSD card (`[P04]`).
   * **Screen 4 — OS Customisation (`Edit Settings`):**
     * **Hostname:** Check **`Set hostname:`** and type `trailcam-node`
     * **Username & Password:** Check **`Set username and password:`** $\rightarrow$ type username `pi` and password `trailcam` (or your own password).
     * **Wireless LAN (Bench Setup Only):** Check **"Configure wireless LAN"** and enter your home Wi-Fi name (`SSID`) and password so your MacBook Pro can talk to the Pi 5 over Wi-Fi during initial setup.
     * **Services Tab:** Click the **`SERVICES`** tab at the top $\rightarrow$ check **"Enable SSH"** and select **"Use password authentication"**.
   * **Screen 5 — Write:** Click **`SAVE`** $\rightarrow$ click **`YES`** $\rightarrow$ enter your MacBook Pro password when prompted, and wait ~2 minutes until Raspberry Pi Imager says **"Write Successful — You can now remove the SD card from the reader"**.

````carousel
![Step 1: Choose Device](images/flashing_steps/step01_device_select.png)
<!-- slide -->
![Step 2: Choose OS Category](images/flashing_steps/step03_os_other.png)
<!-- slide -->
![Step 3: Select Raspberry Pi OS Lite 64-bit](images/flashing_steps/step04_os_lite_64bit.png)
<!-- slide -->
![Step 4: Set Hostname trailcam-node](images/flashing_steps/step07_hostname_trailcam_node.png)
<!-- slide -->
![Step 5: Set Username and Password](images/flashing_steps/step09_user_pi.png)
<!-- slide -->
![Step 6: Enable SSH](images/flashing_steps/step11_ssh_enable.png)
<!-- slide -->
![Step 7: Write Complete](images/flashing_steps/step17_write_complete.png)
````

### Step 1.3 — Insert the MicroSD Card (`[P04]`) into the Underside of the `Raspberry Pi 5 (8GB)` (`[P01]`)

* **Which board & where the slot is:**
  * The MicroSD card (`[P04]`) goes into the **`Raspberry Pi 5 (8GB)` (`[P01]`)**—*not* the tiny `Pico 2` (`[P07]`), which has no SD slot.
  * On the **`Raspberry Pi 5 (8GB)` (`[P01]`)**, the metal MicroSD card slot is on the **flat green UNDERSIDE (bottom face)** of the board, under the left edge opposite the USB/Ethernet ports.
* **Which way it fits (`✓ CORRECT` — See Panel 1 of the Isometric Orientation Guide):**
  1. Flip the **`Raspberry Pi 5 (8GB)` (`[P01]`)** **upside down** so you are looking at the flat green underside of the board.
  2. Hold the **`SanDisk 64GB` MicroSD card (`[P04]`)** so its **shiny gold metal contact teeth face UP toward the green `Raspberry Pi 5` circuit board** (and the printed red/grey SanDisk label faces DOWN toward the tabletop, away from the green board).
  3. Slide the card straight into the silver metal slot until it stops flat (`~12 mm` deep). Flip the **`Raspberry Pi 5 (8GB)` (`[P01]`)** back right-side up.

### Step 1.4 — Plug the `Pico` into Your MacBook Pro (`[T02]`) & Flash MicroPython from Terminal

1. Take a **Micro-USB data cable** (with a `USB-C` plug or `USB-A to USB-C` adapter on the computer end). Plug the **`USB-C` end into a USB-C port on the left side of your MacBook Pro (`[T02]`)** (right beside the `esc` / `tab` / `caps lock` keys)—leave the small **Micro-USB end** unplugged in your hand.
2. Pick up the stick-of-gum-sized **`Raspberry Pi Pico 2 with Headers` (`[P07]`, 40 metal legs underneath)** *(or your bare Pico from the silver bag to test Stage 1)*. Find the tiny white rectangular button on top of the board labeled **`BOOTSEL`** (near the silver Micro-USB port).
3. **Press and hold down the white `BOOTSEL` button with your fingertip**, and **while still holding `BOOTSEL` down**, push the **Micro-USB plug** **firmly all the way in** (past the 2 tiny silver retention barbs on the metal tongue) into the Pico's silver Micro-USB port. Release your finger after 1 second.
4. Go to the **Terminal window on your MacBook Pro**, copy-paste this **exact command** (which flashes the all-in-one `arctic_trailcam_pico2_complete.uf2` containing **both** official MicroPython `v1.25.0` **and** pre-loaded `main.py` + `test_qmc5883l.py` at `0x10100000` with zero macOS metadata files), and press **`Enter`**:
   ```bash
   export COPYFILE_DISABLE=1; UF2="pi-diode-trailcam/pico_gatekeeper/arctic_trailcam_pico2_complete.uf2"; xattr -c "$UF2" 2>/dev/null; if command -v picotool >/dev/null 2>&1; then picotool load -v -x "$UF2" && echo "SUCCESS: Flashed Pico 2 (RP2350) with MicroPython v1.25.0 + main.py + test_qmc5883l.py!"; elif [ -d /Volumes/RP2350 ]; then mdutil -i off /Volumes/RP2350 >/dev/null 2>&1; rm -rf /Volumes/RP2350/.Spotlight-V100 /Volumes/RP2350/.fseventsd /Volumes/RP2350/._* 2>/dev/null; cp -X "$UF2" /Volumes/RP2350/ && echo "SUCCESS: Flashed Pico 2 (RP2350)!"; else echo "Pico drive not found — unplug USB-C, hold white BOOTSEL button, and plug back in!"; fi
   ```
5. **What you should see:** Terminal prints **`Verifying Flash: 100% OK`** and **`SUCCESS: Flashed Pico 2 (RP2350) with MicroPython v1.25.0 + main.py + test_qmc5883l.py!`** — installing both MicroPython and the complete Gatekeeper application in one single step!

![Real-World Prototype Build Log — Stage 1 Step 1.4 Flashing Pico 2 on MacBook Pro (Photos 12–17 in Chronological Order, 1 Step Per Row)](images/real_build/stage1_real_world_pico2_usb_setup.jpg)

* **Documented Real-World Stage 1 `Pico 2 [P07]` & `MacBook Pro [T02]` USB Setup & `BOOTSEL` Flashing Photos (`6` Chronological Shots Connecting `Pico 2` Once With `BOOTSEL` Pressed, `Photos 12–17`):**
  12. [Photo 12 (`stage1_13_usb_c_adapter_in_macbook_pro.jpg`)](images/real_build/stage1_13_usb_c_adapter_in_macbook_pro.jpg) — **Step 1.4A (Pico Unplugged):** Plugging the rectangular `USB-A` cable + silver `USB-A to USB-C` adapter into the left-side `USB-C` (`Thunderbolt`) port of the MacBook Pro (`[T02]`) beside `esc` / `tab` / `caps lock`, leaving the small Micro-USB end unplugged in your hand.
  13. [Photo 13 (`stage1_08_pico2_micro_usb_alignment.jpg`)](images/real_build/stage1_08_pico2_micro_usb_alignment.jpg) — **Step 1.4B (Pico Unplugged):** Holding `Pico 2 With Headers [P07]` (`SKU 828988`, 40 pre-soldered metal legs pointing down) and aligning the trapezoid key of the unplugged Micro-USB plug to the `Pico 2 [P07]` socket (`narrow flat face toward top of PCB / BOOTSEL`, `wider beveled face toward the 40 long metal header pins`).
  14. [Photo 14 (`stage1_14_pressing_bootsel_button.jpg`)](images/real_build/stage1_14_pressing_bootsel_button.jpg) — **Step 1.4C (Pico Unplugged):** Pressing and holding down the white **`BOOTSEL` button** on `Pico 2 With Headers [P07]` with the index fingertip before inserting the Micro-USB plug.
  15. [Photo 15 (`stage1_15_plugging_cord_while_holding_bootsel.jpg`)](images/real_build/stage1_15_plugging_cord_while_holding_bootsel.jpg) — **Step 1.4D (Connecting With `BOOTSEL` Held):** Pushing the Micro-USB plug straight into `Pico 2 [P07]` with the bottom hand **while keeping the white `BOOTSEL` button pressed down** with the top hand.
  16. [Photo 16 (`stage1_09_pico2_top_bootsel_view.jpg`)](images/real_build/stage1_09_pico2_top_bootsel_view.jpg) — **Step 1.4E (Connected — Depth Check):** Release `BOOTSEL` 1 second after plugging in and check insertion depth on `Pico 2 [P07]` — push firmly past the halfway friction catch so the 2 tiny silver retention barbs on the Micro-USB tongue slide inside the socket!
  17. [Photo 17 (`stage1_11_pico2_side_profile_over_stage1_bench.jpg`)](images/real_build/stage1_11_pico2_side_profile_over_stage1_bench.jpg) — **Step 1.4F (Connected — Flashing UF2):** `Pico 2 With Headers [P07]` flashed in `BOOTSEL` mode via `picotool load -v -x arctic_trailcam_pico2_complete.uf2` (`Verifying Flash: 100% OK`, bundling `MicroPython v1.25.0 + main.py + test_qmc5883l.py` at `0x10100000`) over the Stage 1 work cloth.

---

## STAGE 2: Exact Hole-by-Hole Breadboard (`[P09]`) & `Raspberry Pi 5 (8GB)` (`[P01]`) Wiring (`7 Wires Total`)

> [!CAUTION]
> **UNPLUG ALL USB POWER CABLES FIRST!** Never plug or unplug breadboard wires while the `Raspberry Pi 5 (8GB)` (`[P01]`) or `Raspberry Pi Pico 2` (`[P07]`) is plugged into power.

Look at the **Real-World Golden-Path Top-Down Breadboard (`Photo 57`) & Complete Powered System (`Photo 58`)** below. Every single connection is listed by its exact **Row Number (`1–30`)**, **Column Letter (`a–j`)**, and **Empty-Hole Landmark Count**.

![Real-World Golden-Path Top-Down Breadboard Verification (Photo 57)](images/real_build/stage2_41_completed_breadboard_topdown_golden.jpg)

### How Your Half-Size Breadboard (`[P09]`) Works (In 20 Seconds)

* Turn the white breadboard (`[P09]`) so **`Row 1` is at the TOP** and **`Row 30` is at the BOTTOM**.
* Down the middle runs a deep vertical groove called the **center canyon (ravine)**.
* On the **left side** of the canyon, in any single row (for example, `Row 6`), the 5 holes **`a6`, `b6`, `c6`, `d6`, `e6`** are connected together underneath by one hidden metal clip.
* On the **right side** of the canyon, in any single row (for example, `Row 5`), the 5 holes **`f5`, `g5`, `h5`, `i5`, `j5`** are connected together underneath by a separate metal clip.
* The left side (`a–e`) and right side (`f–j`) are **not** connected to each other across the center canyon.

### Step 2.1 — Press the `Raspberry Pi Pico 2` (`[P07]`) into `Rows 1–20` (`Columns b & h` — **DONE in Photos 18–23!**)

1. Hold the **`Raspberry Pi Pico 2 With Headers` (`[P07]`)** over the top of the breadboard (`[P09]`) so its **silver Micro-USB port points UP at `Row 1`**.
2. Line up the **left row of 20 metal legs** over **Column `b`, `Rows 1 to 20`** (`Hole b1` at the top down to `Hole b20`).
3. Line up the **right row of 20 metal legs** over **Column `h`, `Rows 1 to 20`** (`Hole h1` at the top down to `Hole h20`).
4. Check that the green `Pico 2` board bridges straight across the center canyon, leaving **1 open column on the left (`Column a`: `a1–a20`)** and **2 open columns on the right (`Columns i, j`: `i1–j20`)** in every row from `1` to `20`.
5. Press straight down firmly and evenly with both thumbs until the black plastic pin strips sit completely flat against the white breadboard surface (verified in `Photos 18–23` below!).

![Real-World Build Log — Stage 2.1: Seating Pico 2 With Headers in Breadboard & Side-by-Side Layout Next to Pi 5 (Photos 18–23, 1 Step Per Row)](images/real_build/stage2_real_world_pico2_on_breadboard.jpg)

* **Documented Real-World Stage 2.1 `Breadboard [P09]` + `Pico 2 [P07]` Seating Photos (`6` Chronological Shots, `Photos 18–23`):**
  18. [Photo 18 (`stage2_01_empty_breadboard_30rows.jpg`)](images/real_build/stage2_01_empty_breadboard_30rows.jpg) — **Step 2.1A:** Holding the empty `30-Row` **`Inland 400-Hole Half-Size Breadboard [P09]`** vertically (`Row 1` at top, `Row 30` at bottom, center ravine between `Column e` and `Column f`, plus outer red `+` and blue `-` power rails).
  19. [Photo 19 (`stage2_02_pico2_top_alignment_rows1_to_20.jpg`)](images/real_build/stage2_02_pico2_top_alignment_rows1_to_20.jpg) — **Step 2.1B:** Top-down alignment of **`Raspberry Pi Pico 2 With Headers [P07]`** across the center ravine (`Rows 1 to 20`), with the silver Micro-USB port overhanging `Row 1` at the top.
  20. [Photo 20 (`stage2_03_pico2_angled_seated_in_breadboard.jpg`)](images/real_build/stage2_03_pico2_angled_seated_in_breadboard.jpg) — **Step 2.1C:** Angled inspection after pressing `Pico 2 [P07]` straight down into `Rows 1–20`, leaving open holes beside the Pico on both left and right, with `Rows 21–30` completely open below.
  21. [Photo 21 (`stage2_04_pico2_side_profile_flush_on_breadboard.jpg`)](images/real_build/stage2_04_pico2_side_profile_flush_on_breadboard.jpg) — **Step 2.1D:** Side-profile seating check confirming the black plastic header strip of `Pico 2 [P07]` is pressed 100% flush against the white plastic face of `Breadboard [P09]` with zero exposed silver pin metal.
  22. [Photo 22 (`stage2_05_bench_overview_boxes_and_boards.jpg`)](images/real_build/stage2_05_bench_overview_boxes_and_boards.jpg) — **Step 2.1E:** Full benchtop overview showing the component boxes, `SanDisk 64GB MicroSD Card [P04]` (in blue/black pack), and `QMC5883L [P08]` (in silver anti-static bag) at top, and the two assembled sub-units (`Breadboard + Pico 2` on left, `Raspberry Pi 5 + Active Cooler` on right) at bottom.
  23. [Photo 23 (`stage2_06_topdown_breadboard_pico2_next_to_pi5.jpg`)](images/real_build/stage2_06_topdown_breadboard_pico2_next_to_pi5.jpg) — **Step 2.1F:** High-resolution close-up of `Breadboard [P09] + Pico 2 [P07]` (`Rows 1–20`) side-by-side next to `Raspberry Pi 5 [P01] + Official Active Cooler [P02]`.

### Step 2.2 — Pre-Stage & Plug the 7 Unique Rainbow Jumper Wires (`[P10]`) Into `Pico 2` & `Column f`

> [!IMPORTANT]
> **Unit #2 Zero-Wrong-Turns Mechanical Pre-Check (Before Plugging Anything In):**
> 1. **Pre-Stage 2 Separate Groups on the Table (`Photo 33`):** Your `ELEGOO` box contains 3 different 40-wire ribbons (`Male-to-Male`, `Male-to-Female`, `Female-to-Female`). Peel and lay out **two distinct groups** flat on the table before wiring:
>    * **Group A — 4 `Male-to-Male` (`Pin-to-Pin`) wires** (sharp metal pins on **both** ends): **`Red`, `Black`, `Yellow`, `Blue`** (for breadboard-to-breadboard `W1–W4`).
>    * **Group B — 3 `Male-to-Female` (`Pin-to-Socket`) wires** (sharp pin on one end, hollow black socket on the other end): **`Purple`, `Green`, `Orange`** (for breadboard-to-Raspberry Pi 5 `W5–W7`).
> 2. **How to Push Pins Into Brand-New Stiff Breadboard Clips Without Bending Tips (`Photo 35`):** Never push a jumper wire down while holding the soft colored wire insulation. Always pinch the **square black plastic housing `2 mm` above the metal pin tip** and push **straight down vertically (`90°`)**. If a pin ever bends, squeeze it flat between smooth flat-nose pliers (`Photo 35`).
> 3. **Why `W1–W4` Go Into `Column f` (`Rows 24–27`) (`Photo 41`):** Always plug the lower ends of `Red`, `Black`, `Yellow`, and `Blue` into **`Column f`** (`f24, f25, f26, f27` — the innermost column right next to the center ravine). That leaves **`Columns g, h, i` open** and gives full clearance for the `GY-271` compass module in **`Column j` (`j24..j28`)**!

![Real-World Build Log — Step 2.2: Pre-Staging ELEGOO Jumpers, Pliers Straightening & Wiring Pico 2 (Photos 31–37, 1 Step Per Row)](images/real_build/stage2_real_world_jumpers_part1.jpg)

Check off each wire (`[ ]`) as you push its metal pin straight into the exact hole listed below:

| Check | Wire ID & Color | Wire Type | Plug END 1 Into Breadboard Hole... | Plug END 2 Into... | What This Wire Does |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `[ ]` | **`W1` — RED** | Male-to-Male *(pin both ends)* | **`Hole j5`** *(Right side, Row 5 = `Pico 2` Pin 36 `3V3_OUT`)* | **`Hole f24`** *(Inner-right Col `f`, Row 24 = `GY-271 VCC`)* | Sends safe `3.3V` power from `Pico 2` to Magnetometer. |
| `[ ]` | **`W2` — BLACK** | Male-to-Male *(pin both ends)* | **`Hole j3`** *(Right side, Row 3 = `Pico 2` Pin 38 `GND`)* | **`Hole f25`** *(Inner-right Col `f`, Row 25 = `GY-271 GND`)* | Connects Ground (`0V`) to Magnetometer. |
| `[ ]` | **`W4` — YELLOW** | Male-to-Male *(pin both ends)* | **`Hole a7`** *(Left side open Col `a`, Row 7 = `Pico 2` Pin 7 `GP5 SCL`)* | **`Hole f26`** *(Inner-right Col `f`, Row 26 = `GY-271 SCL`)* | Carries `I2C` Magnetic Clock (`SCL`). |
| `[ ]` | **`W3` — BLUE** | Male-to-Male *(pin both ends)* | **`Hole a6`** *(Left side open Col `a`, Row 6 = `Pico 2` Pin 6 `GP4 SDA`)* | **`Hole f27`** *(Inner-right Col `f`, Row 27 = `GY-271 SDA`)* | Carries `I2C` Magnetic Data (`SDA`). |
| `[ ]` | **`W5` — PURPLE** | Male-to-Female *(pin + socket)* | **Pin end $\rightarrow$ `Hole a11`** *(Left side open Col `a`, Row 11 = `Pico 2` Pin 11 `GP8 TX`)* | **Socket end $\rightarrow$ `Raspberry Pi 5 [P01]` `Pin 10` (`GPIO15 RX`)** *(**5th pin down** on the **outer-right column** of Pi 5)* | Sends `TRIG,...` wake reason from `Pico 2` to `Raspberry Pi 5`. |
| `[ ]` | **`W6` — ORANGE** | Male-to-Female *(pin + socket)* | **Pin end $\rightarrow$ `Hole a4`** *(Left side open Col `a`, Row 4 = `Pico 2` Pin 4 `GP2 DONE`)* | **Socket end $\rightarrow$ `Raspberry Pi 5 [P01]` `Pin 16` (`GPIO23`)** *(**8th pin down** on the **outer-right column** of Pi 5)* | Sends `DONE` signal from `Raspberry Pi 5` back to `Pico 2`. |
| `[ ]` | **`W7` — GREEN** | Male-to-Female *(pin + socket)* | **Pin end $\rightarrow$ `Hole a13`** *(Left side open Col `a`, Row 13 = `Pico 2` Pin 13 `GND`)* | **Socket end $\rightarrow$ `Raspberry Pi 5 [P01]` `Pin 14` (`GND`)** *(**7th pin down** on the **outer-right column** of Pi 5)* | Shared Ground reference between `Pico 2` and `Raspberry Pi 5`. |

> [!TIP]
> **How to Count the 3 Pins on the `Raspberry Pi 5 (8GB)` (`[P01]`) Without Ever Touching the Wrong Column:**
> 1. Look at the **2 long vertical columns of 20 gold pins (`40 pins total`)** along the right edge of the `Raspberry Pi 5`.
> 2. **CRITICAL:** The **INNER-LEFT column** (right next to the silver heatsink fins) must stay **100% BARE / EMPTY**! Look **ONLY** at the **OUTER-RIGHT column of gold pins** (the column closest to the outer right green edge of the Pi 5 circuit board).
> 3. Starting from the **very top-right outer corner pin (`Pin 2`)**, count straight down that **OUTER-RIGHT column**:
>    * `1st outer pin (Pin 2)` — leave bare
>    * `2nd outer pin (Pin 4)` — leave bare
>    * `3rd outer pin (Pin 6)` — leave bare
>    * `4th outer pin (Pin 8)` — leave bare
>    * **`5th outer pin (Pin 10)` $\rightarrow$ Push `W5 PURPLE` Female socket straight down onto this pin!**
>    * `6th outer pin (Pin 12)` — **SKIP 1 PIN (leave bare!)**
>    * **`7th outer pin (Pin 14)` $\rightarrow$ Push `W7 GREEN` Female socket straight down onto this pin!**
>    * **`8th outer pin (Pin 16)` $\rightarrow$ Push `W6 ORANGE` Female socket straight down onto this pin!**

### Step 2.3 — Lock the `HiLetgo GY-271` (`QMC5883L`, `[P08]`) Compass Into `Column j` (`Rows 24–28`) Facing RIGHT

1. Take the **`HiLetgo GY-271` (`HW-246` / `QMC5883L`, `[P08]`)** blue breakout board and its **`5-Pin Black Header Strip`** out of the pink anti-static pouch (`Photo 34`).
2. Hold the 5-pin header strip so the **`SHORT GOLD PINS` point UP** and the **`LONG GOLD PINS` point DOWN** (`Photo 38`).
3. **Secure Electrical Contact on the `GY-271` Through-Holes (Solder or Safe Zero-Solder Workarounds — NEVER Bend/Twist Pins With Pliers!):**
   * **WARNING — DO NOT Bend or Twist the Gold Header Pins With Pliers:** Cheap `2.54 mm` header pins are made of brittle cast brass—bending or twisting them with pliers (`even 20°–90°`) will snap the pins off! Keep the header pins `100%` straight (`0°`).
   * **Best Practice (If a Soldering Iron Is Available):** Slide the blue `GY-271` board onto the 5 straight short gold pins (`chip & white labels facing UP`) and touch a small drop of solder to the **4 active pins (`VCC, GND, SCL, SDA`)**.
   * **If NO Soldering Iron Is Available (3 Safe Zero-Solder Workarounds):**
     1. **Workaround A — Aluminum Foil Conductive Sleeve (`Cold-Solder Press-Fit`):** Fold a narrow `2 mm × 10 mm` strip of standard kitchen aluminum foil over the tips of the 4 straight short gold pins (`VCC, GND, SCL, SDA` — keep individual foil wraps separate so adjacent pins don't touch!) and press the blue `GY-271` board straight down over them. The soft aluminum compresses into the `0.18 mm` hole gap around each pin for `100%` metal-to-metal contact with zero pin-bending stress.
     2. **Workaround B — Wooden Toothpick Wedge:** Slide the blue `GY-271` board onto the straight 5-pin header, then gently push the pointed tip of a wooden toothpick into the gap on one side of each of the 4 active holes (`VCC, GND, SCL, SDA`) so the silver PCB ring is wedged tightly against the straight gold pin, and lock with a dab of `Permatex Black Silicone [T11]`.
     3. **Workaround C — Direct Jumper-Pin Through-Hole Pinning *(Also works if your 5-pin header broke!)*:** Skip the 5-pin header strip completely! Place the blue `GY-271` board's 4 active holes (`VCC, GND, SCL, SDA`) directly over breadboard **`Column j` (`Holes j24, j25, j26, j27`)** and push the bottom metal pins of your 4 jumper wires (`W1 Red`, `W2 Black`, `W4 Yellow`, `W3 Blue`) **straight through the 4 holes of the blue `GY-271` board down into the breadboard holes** (`j24–j27`), wedging them snug with a toothpick tip or silicone dab.
4. Slide the 5 holes of the blue `GY-271` board (`VCC, GND, SCL, SDA, DRDY`) down onto the **`SHORT GOLD PINS`** with the **black square sensor chip and printed white letters facing UP** and the **blue board hanging out to the RIGHT** (`Photo 40`).
5. Push the 5 **`LONG GOLD PINS`** straight down into **`Column j`, `Rows 24–28`** (`Photo 41` & `Photo 42`) so that the blue `GY-271` board hangs out to the **right** over the `+`/`-` power rails (with zero crowding against the wires in `Column f`):
   * **`Hole j24` (`VCC`)** $\leftrightarrow$ matches **`RED` (`f24`)**
   * **`Hole j25` (`GND`)** $\leftrightarrow$ matches **`BLACK` (`f25`)**
   * **`Hole j26` (`SCL`)** $\leftrightarrow$ matches **`YELLOW` (`f26`)**
   * **`Hole j27` (`SDA`)** $\leftrightarrow$ matches **`BLUE` (`f27`)**
   * **`Hole j28` (`DRDY`)** $\leftrightarrow$ hangs 1 hole lower in `Row 28` with **no wire needed**!

> [!CAUTION]
> **Two Critical Real-World Breadboard Rules (`Empty-Hole Counting` & `Hook-Shaped Pin Risk`):**
> 1. **Do NOT Trust the Printed Row Numbers (`1–30`) — Count Empty Holes From the Ends Instead (`compass_5pin_vs_4wires_1hole_shift_fix_v2.jpg`):**
>    * On `ELEGOO` / `zyamy` 30-row breadboards, the printed black numbers (`1–30`) do not align cleanly with the physical holes. Always align by counting **empty holes** from the green `Pico 2` (`Row 20`) and the bottom edge of the breadboard (`Row 30`):
>    * **In `Column f` (`4 Wires: Red, Black, Yellow, Blue`):** Leave **3 empty holes** below the green `Pico 2` (`f21, f22, f23`), and leave **3 empty holes** at the bottom of `Column f` (`f28, f29, f30`).
>    * **In `Column j` (`5-Pin Compass Strip: VCC, GND, SCL, SDA, DRDY`):** Because the Compass strip has **5 pins** (including the unused 5th `DRDY` pin at the bottom) while there are only **4 wires**, you must leave **3 empty holes** below the green `Pico 2` (`j21, j22, j23`) and **ONLY 2 EMPTY HOLES at the bottom of `Column j` (`j29, j30`)**! *(If you leave 3 empty bottom holes under the 5-pin strip, the entire Compass shifts 1 hole UP so `Red (+3.3V)` lands on `Compass GND (Pin #2)`!)*
> 2. **Watch Out for "Hook-Shaped" Bent Jumper Pins Inside Stiff Holes (`stage2_38` & `stage2_39`):**
>    * If a male jumper pin feels mushy or resists going all the way down into a stiff new breadboard hole, pull it back out and inspect the metal tip (`stage2_38_blue_wire_hook_pin_risk.jpg`). A pin tip that bends into a **J-hook shape** either rides on top of the internal spring clip without making electrical contact (open circuit) or curves sideways inside the slot where it can touch/short against an adjacent pin. Always squeeze any hooked or curved jumper pin flat between the smooth jaws of your flat-nose pliers (`stage2_39_straightening_hook_pin_with_pliers.jpg`) before re-inserting straight down (`90°`).

![GY-271 Compass Assembly Steps & Hole Map](images/real_build/stage2_05c_gy271_compass_assembly_steps.jpg)

![Compass 5-Pin vs 4-Wire 1-Hole Shift Fix Guide](images/real_build/compass_5pin_vs_4wires_1hole_shift_fix_v2.jpg)

![Real-World Build Log — Step 2.3A: GY-271 5-Pin Header Inspection & Seating in Column j Facing Right (Photos 38–42, 1 Step Per Row)](images/real_build/stage2_real_world_gy271_compass_part2a.jpg)

![Real-World Build Log — Step 2.3B: Raspberry Pi 5 Outer-Right GPIO Column Verification & Full Stage 2.3 Assembly (Photos 43–46, 1 Step Per Row)](images/real_build/stage2_real_world_pi5_gpio_part2b.jpg)

* **Documented Real-World Steps 2.2 & 2.3 `7-Color Jumper Wiring [P10]` + `GY-271 Compass [P08]` + `Pi 5 GPIO` Golden-Path Photos (`16` Chronological Shots, `Photos 31–46`):**
  31. [Photo 31 (`stage2_14_elegoo_jumpers_flatlay.jpg`)](images/real_build/stage2_14_elegoo_jumpers_flatlay.jpg) — **Step 2.2A:** Flat-lay overview of the `ELEGOO` 3-ribbon jumper wire box, `Breadboard [P09] + Pico 2 [P07]`, and `Raspberry Pi 5 [P01]`.
  32. [Photo 32 (`stage2_15_unpacked_40wire_jumper_ribbon.jpg`)](images/real_build/stage2_15_unpacked_40wire_jumper_ribbon.jpg) — **Step 2.2B:** Unpacked 40-wire rainbow jumper ribbon next to `Breadboard + Pico 2` and `Raspberry Pi 5`.
  33. [Photo 33 (`stage2_16_4_male_male_and_3_male_female_wires_selected.jpg`)](images/real_build/stage2_16_4_male_male_and_3_male_female_wires_selected.jpg) — **Step 2.2C:** Pre-staging the **2 separate wire groups** flat on the table: **4 `Male-to-Male` (`Pin-to-Pin`) wires** (`Red, Black, Yellow, Blue`) and **3 `Male-to-Female` (`Pin-to-Socket`) wires** (`Purple, Green, Orange`).
  34. [Photo 34 (`stage2_17_unboxed_gy271_compass_and_5pin_header.jpg`)](images/real_build/stage2_17_unboxed_gy271_compass_and_5pin_header.jpg) — **Step 2.2D:** Unboxed `HiLetgo GY-271 (QMC5883L) [P08]` blue compass PCB (`VCC, GND, SCL, SDA, DRDY`) and its 5-pin male header strip above the labeled ESD pouch.
  35. [Photo 35 (`stage2_18_straightening_jumper_pin_with_pliers.jpg`)](images/real_build/stage2_18_straightening_jumper_pin_with_pliers.jpg) — **Step 2.2E:** Using smooth flat-nose pliers (`HYCHIKA` kit) to keep male jumper pins dead-straight (`90°`) before vertical insertion.
  36. [Photo 36 (`stage2_19_w1_to_w4_wired_on_breadboard_top_view.jpg`)](images/real_build/stage2_19_w1_to_w4_wired_on_breadboard_top_view.jpg) — **Step 2.2F:** Overhead view of all 7 rainbow wires seated in `Column a` (`a4=Orange, a6=Blue, a7=Yellow, a11=Purple, a13=Green`) and `Column j` (`j3=Black, j5=Red`) alongside `Pico 2`.
  37. [Photo 37 (`stage2_20_all_7_wires_on_breadboard_rows_visible.jpg`)](images/real_build/stage2_20_all_7_wires_on_breadboard_rows_visible.jpg) — **Step 2.2G:** Angled inspection of the full breadboard wiring with all row numbers visible.
  38. [Photo 38 (`stage2_21_holding_5pin_header_short_up_long_down.jpg`)](images/real_build/stage2_21_holding_5pin_header_short_up_long_down.jpg) — **Step 2.3A:** Holding the 5-pin header strip with the **`SHORT GOLD PINS` pointing UP** and **`LONG GOLD PINS` pointing DOWN**.
  39. [Photo 39 (`stage2_22_pliers_zigzag_bend_for_snug_unsoldered_fit.jpg`)](images/real_build/stage2_22_pliers_zigzag_bend_for_snug_unsoldered_fit.jpg) — **Step 2.3B (`CAUTION — Do NOT Bend Brittle Brass Header Pins`):** Inspecting the 4 active short pins (`VCC, GND, SCL, SDA`) — solder the 4 pins or use an aluminum-foil sleeve / wooden toothpick wedge (never bend the short brass header pins with pliers, as they snap easily!).
  40. [Photo 40 (`stage2_23_gy271_slid_onto_5pin_header.jpg`)](images/real_build/stage2_23_gy271_slid_onto_5pin_header.jpg) — **Step 2.3C:** `GY-271` PCB (`VCC, GND, SCL, SDA, DRDY` facing up) seated onto the 5-pin header flush against the black plastic collar.
  41. [Photo 41 (`stage2_24_w1_to_w4_in_col_f_and_5pin_strip_in_col_j.jpg`)](images/real_build/stage2_24_w1_to_w4_in_col_f_and_5pin_strip_in_col_j.jpg) — **Step 2.3D:** Seating `W1–W4` (`Red, Black, Yellow, Blue`) in **`Column f` (`f24..f27`)** and the 5-pin header in **`Column j` (`j24..j28`)** with 3 open holes (`Cols g, h, i`) between them.
  42. [Photo 42 (`stage2_25_completed_breadboard_with_gy271_in_col_j_facing_right.jpg`)](images/real_build/stage2_25_completed_breadboard_with_gy271_in_col_j_facing_right.jpg) — **Step 2.3E:** Completed breadboard with the blue `GY-271` board seated in `Column j` (`Rows 24–28`) hanging out to the **right** over the `+`/`-` power rails!
  43. [Photo 43 (`stage2_26_pi5_gpio_outer_column_verified_side_view.jpg`)](images/real_build/stage2_26_pi5_gpio_outer_column_verified_side_view.jpg) — **Step 2.3F:** Verified side view of the `Raspberry Pi 5 [P01]` 40-pin GPIO header showing all 20 inner-column pins bare and the 3 jumper sockets seated on the **Outer-Right column** (`#1–#4` bare, `#5 = Purple`, `#6` bare, `#7 = Green`, `#8 = Orange`).
  44. [Photo 44 (`stage2_27_pi5_gpio_outer_column_verified_angled_view.jpg`)](images/real_build/stage2_27_pi5_gpio_outer_column_verified_angled_view.jpg) — **Step 2.3G:** Angled verification of the `Raspberry Pi 5 [P01]` Outer-Right GPIO column (`Purple, skip 1, Green, Orange`) and `Active Cooler [P02]`.
  45. [Photo 45 (`stage2_28_pi5_gpio_and_cam_disp0_top_view.jpg`)](images/real_build/stage2_28_pi5_gpio_and_cam_disp0_top_view.jpg) — **Step 2.3H:** Close-up top view of `Raspberry Pi 5 [P01]` showing the verified Outer-Right GPIO wiring (`Purple, skip 1, Green, Orange`) and the vertical `J4 CAM/DISP 0` camera slot ready for Step 2.4.
  46. [Photo 46 (`stage2_29_completed_stage2_3_full_assembly_golden.jpg`)](images/real_build/stage2_29_completed_stage2_3_full_assembly_golden.jpg) — **Step 2.3I:** Full golden-path benchtop overview of the completed Stage 2.3 hardware assembly (`Breadboard + Pico 2 + GY-271 + 7-wire harness + Raspberry Pi 5` with `SanDisk 64GB MicroSD` seated underneath and `Camera Module 3` box staged on the table).

![Stage 2.3 Verified & Next Steps (Steps 2.4–2.6)](images/real_build/stage2_3_verified_and_next_steps.jpg)


### Step 2.4 — Connect the Official `200mm` Orange Camera Ribbon Cable (`[P06]`) Between `Raspberry Pi 5` (`J4 CAM/DISP 0`) & `Camera Module 3 NoIR Wide` (`[P05]`)

Make sure the **`Raspberry Pi 5 (8GB)` (`[P01]`)** is **unplugged from power** while connecting the ribbon cable.

#### Step 2.4A — Lock the **NARROW End (`22-Pin Mini`, `11.5 mm`)** Into `J4 (CAM/DISP 0)` on the `Raspberry Pi 5` (`Photos 47–50`)
1. **Identify the Two Ends & Two Sides of the Orange `Raspberry Pi 5 Camera Cable (Standard - Mini | 200mm)` (`[P06]`, `Photos 48–49`):**
   * **End 1 — NARROW End (`22-Pin Mini`, `11.5 mm` wide, printed `"Mini | 200mm"`):** Plugs into **`J4 (CAM/DISP 0)`** on the **`Raspberry Pi 5`**.
   * **End 2 — WIDE End (`15-Pin Standard`, `16.0 mm` wide, printed `"CE FC"`):** Plugs into the **`Camera Module 3 NoIR Wide` (`[P05]`)**.
   * **Notice that both black stiffeners are on the SAME side (`Side A`) and both sets of shiny gold metal teeth are on the SAME side (`Side B`).**
2. **Locate `J4 (CAM/DISP 0)` on the `Raspberry Pi 5`:** Look between the Micro-HDMI ports and the silver Gigabit Ethernet port. There are two vertical beige-and-brown slots side-by-side: use the **UPPER slot (`J4`, labeled `CAM/DISP 0`)**.
3. **Open the Brown Vertical Wedge Latch (`1.5 mm` ONLY — Do NOT Pull Out or Tilt):** Use two fingernails (or the tips of your tweezers) on both the left and right ears of the dark-brown plastic latch on `J4` to lift it **straight up (`90°`) by ONLY `1.5 mm`** until it loosens. *(Never pry at an angle or pull the brown wedge completely out of its thin side tracks.)*
4. **Insert the Narrow `22-Pin` End & Press Evenly on a Flat Box to Lock (`Photo 50`):**
   * Slide the **narrow `22-pin` end (`"Mini | 200mm"`)** straight down into `J4 (CAM/DISP 0)` with:
     * **SHINY GOLD TEETH facing RIGHT (toward the silver Ethernet port)**
     * **BLACK STIFFENER + WHITE `"Mini | 200mm"` TEXT facing LEFT (toward the Micro-HDMI ports)**
   * Support the underside of the `Raspberry Pi 5` flat on top of the white `27W USB-C Power Supply` box and press straight down (`90°`) evenly across the top of the brown latch using the flat back/spine of your tweezers until the brown latch sits flush.

![Ribbon Cable Both Sides & J4 Slot Guide](images/real_build/ribbon_both_sides_and_j4_slot_guide_v1.jpg)

#### Step 2.4B — Swap the Factory White Ribbon on `Camera Module 3 NoIR Wide` (`[P05]`) for the **WIDE End (`15-Pin Standard`, `16.0 mm`)** of Your Orange Ribbon (`Photos 51–58`)
1. **Inspect the Factory White Ribbon Orientation First (`Photo 51`):** Take the **`Raspberry Pi Camera Module 3 NoIR Wide` (`[P05]`)** out of its silver anti-static bag and turn the small square board over onto its back (`PCB side`). Notice how the factory white `Pi 4` ribbon is seated: its **colored stiffener tape (`Blue`) faces `UP`** (on the same side as the brown plastic slide-latch, facing away from the black camera PCB), while its **metal contact teeth face `DOWN` against the black camera PCB** (where the 15 internal silver contact pins are soldered).
2. **Slide the Camera Latch Out `1.5 mm` & Remove the Factory White Ribbon (`Photo 52`):** Use two thumbnails on the left and right ears of the camera's brown horizontal plastic latch to slide it straight out by **ONLY `1.5 mm`** (do not pull it off). Pull the factory white ribbon straight out and set it back in the box.
3. **Insert the Wide `15-Pin` End (`"CE FC"`) of Your Orange Ribbon & Lock (`Photo 53`):**
   * Hold the back of the black camera PCB facing you and orient the **wide `15-pin` end (`"CE FC"`)** of your orange ribbon so that:
     * **SHINY GOLD CONTACT TEETH face `DOWN` against the black camera circuit board** (touching the 15 internal solder pins on the board side).
     * **BLACK STIFFENER + WHITE `"CE FC"` LETTERS face `UP` (away from the camera circuit board, on the brown-latch side — matching the blue tape on the factory white ribbon!).**
   * Push the tip of the wide orange ribbon **`2 mm` deep inside the slot** so that **zero shiny gold teeth are visible outside the connector**, then push both ears of the brown plastic slide-latch straight back in (`1.5 mm`) until locked flush (`Photo 53`).

![Real-World Build Log — Step 2.4: 200mm Orange Camera Ribbon Side A/B, Pi 5 J4 Lock & Camera Module 3 Lock (Photos 47–53, 1 Step Per Row)](images/real_build/stage2_real_world_camera_ribbon_part3a.jpg)

![Step 2.4B Verified & Step 2.5 USB + Power Connection Guide](images/real_build/stage2_4b_verified_and_step2_5_usb_power_guide_v1.jpg)

![Real-World Build Log — Step 2.4C–2.6: J-Hook Pin Check, 3 vs 2 Empty Bottom Holes Verification & Powered Benchtop System (Photos 54–58, 1 Step Per Row)](images/real_build/stage2_real_world_pin_check_and_golden_part3b.jpg)

* **Documented Real-World Step 2.4 & Final Stage 2 Verification Golden-Path Photos (`12` Chronological Shots, `Photos 47–58`):**
  47. [Photo 47 (`stage2_30a_three_white_boxes_golden.jpg`)](images/real_build/stage2_30a_three_white_boxes_golden.jpg) — **Step 2.4A-1:** The 3 white boxes for Stage 2.4–2.6: `Raspberry Pi 27W USB-C Power Supply`, `Raspberry Pi 5 Camera Cable (Standard - Mini | 200mm) [P06]`, and `Raspberry Pi Camera Module 3 NoIR Wide [P05]`.
  48. [Photo 48 (`stage2_32_flat_camera_ribbon_wide_vs_narrow_ends.jpg`)](images/real_build/stage2_32_flat_camera_ribbon_wide_vs_narrow_ends.jpg) — **Step 2.4A-2 (`Side A` — Black Stiffener & Printed Text Side):** Left = Wide `15-pin Standard` end (`"CE FC"`, for Camera); Right = Narrow `22-pin Mini` end (`"Mini | 200mm"`, for Pi 5 `J4`).
  49. [Photo 49 (`stage2_33_flat_camera_ribbon_gold_teeth_side.jpg`)](images/real_build/stage2_33_flat_camera_ribbon_gold_teeth_side.jpg) — **Step 2.4A-3 (`Side B` — Shiny Gold Contact Teeth Side):** Both sets of gold teeth (`15-pin` left, `22-pin` right) are on this side.
  50. [Photo 50 (`stage2_34_pi5_j4_ribbon_seated_and_locked.jpg`)](images/real_build/stage2_34_pi5_j4_ribbon_seated_and_locked.jpg) — **Step 2.4A-4:** Narrow `22-pin Mini` end seated `2 mm` deep into `J4 (CAM/DISP 0)` on `Raspberry Pi 5 [P01]` (gold teeth facing silver Ethernet port, black stiffener facing Micro-HDMI) with the brown vertical latch pressed flush.
  51. [Photo 51 (`stage2_35_camera_module3_factory_white_ribbon.jpg`)](images/real_build/stage2_35_camera_module3_factory_white_ribbon.jpg) — **Step 2.4B-1:** Inspecting the factory white ribbon on the back of `Camera Module 3 NoIR Wide [P05]` (blue stiffener facing up on latch side, metal teeth facing down against the black camera PCB).
  52. [Photo 52 (`stage2_36_camera_module3_white_ribbon_removed.jpg`)](images/real_build/stage2_36_camera_module3_white_ribbon_removed.jpg) — **Step 2.4B-2:** Sliding the camera's brown horizontal latch out by `1.5 mm` and removing the factory white `Pi 4` ribbon.
  53. [Photo 53 (`stage2_37_camera_module3_orange_ribbon_seated_and_locked.jpg`)](images/real_build/stage2_37_camera_module3_orange_ribbon_seated_and_locked.jpg) — **Step 2.4B-3:** Completed `Step 2.4B` — Wide `15-pin` end of the orange `Pi 5` ribbon seated `2 mm` deep inside `Camera Module 3 NoIR Wide [P05]` (`black stiffener + white "CE FC" letters` facing up on the brown-latch side, all 15 shiny gold teeth facing down against the black camera PCB with zero teeth exposed outside, and brown latch pushed closed).
  54. [Photo 54 (`stage2_38_blue_wire_hook_pin_risk.jpg`)](images/real_build/stage2_38_blue_wire_hook_pin_risk.jpg) — **Step 2.4C-1:** Inspecting a bent "J-hook" tip on the blue `SDA` jumper pin (`W3`) after meeting resistance in a stiff breadboard hole.
  55. [Photo 55 (`stage2_39_straightening_hook_pin_with_pliers.jpg`)](images/real_build/stage2_39_straightening_hook_pin_with_pliers.jpg) — **Step 2.4C-2:** Straightening the hooked jumper pin flat (`90°`) with smooth flat-nose pliers so it seats cleanly inside the breadboard spring clip without shorting against neighboring rows.
  56. [Photo 56 (`stage2_40_compass_shifted_down_2_empty_bottom_holes_closeup.jpg`)](images/real_build/stage2_40_compass_shifted_down_2_empty_bottom_holes_closeup.jpg) — **Step 2.4D-1:** Close-up verification of the golden-path hole-counting rule at the bottom of the breadboard: **`3 empty bottom holes` (`f28, f29, f30`) under the 4 wires in `Column f`** and **`2 empty bottom holes` (`j29, j30`) under the 5-pin `GY-271` Compass strip in `Column j`**.
  57. [Photo 57 (`stage2_41_completed_breadboard_topdown_golden.jpg`)](images/real_build/stage2_41_completed_breadboard_topdown_golden.jpg) — **Step 2.4D-2:** Straight-down overhead verification of the completed golden-path breadboard (`Pico 2` in `Rows 1–20`, `3 empty rows 21–23`, `W1–W4` in `f24–f27` with `3 empty bottom holes`, and `GY-271` in `j24–j28` with `2 empty bottom holes`).
  58. [Photo 58 (`stage2_42_complete_benchtop_system_powered_golden.jpg`)](images/real_build/stage2_42_complete_benchtop_system_powered_golden.jpg) — **Step 2.5/2.6 Golden-Path Overview:** Complete Stage 2 benchtop hardware assembly (`Breadboard + Pico 2 + GY-271 + 7 rainbow wires + Raspberry Pi 5 + 200mm Orange Camera Ribbon + Camera Module 3 NoIR Wide`) powered and ready for live telemetry.


### Step 2.5 — Connect `Pico 2` (`[P07]`), Pre-Stage Refactored Code onto `SanDisk 64GB MicroSD` (`[P04]` — **DONE in Photos 24–30!**) & Test `QMC5883L` (`0x0d`)

1. **Connect Micro-USB to `Pico 2 [P07]` on `Breadboard [P09]` & Pre-Stage Refactored `pi5_sender_node/` Code onto `SanDisk 64GB MicroSD [P04]` with Zero macOS Metadata (`DONE — Photos 24–30`):**
   * Plug the black Micro-USB data cable (`CORD 1`) firmly all the way into `Pico 2 [P07]` on `Breadboard [P09]` (`Photo 24`).
   * Slide the **`SanDisk 64GB MicroSD Card [P04]`** into the **`SanDisk microSD Adapter`** (`Photos 25–27`) and insert it into the **right-side SDXC slot of your MacBook Pro (`[T02]`)** (`Photo 28`).
   * On `/Volumes/bootfs`, our automated staging helper (`stage_sd_card_without_macos_metadata()` in `run_guided_bench_doctor.py`) disables macOS Spotlight indexing (`mdutil -i off /Volumes/bootfs`), writes the refactored [`pi5_sender_node/`](../pi5_sender_node/sender_node.py) files as pure byte streams (`COPYFILE_DISABLE=1`, zero `._*` or `.DS_Store` files), enables `dtparam=uart0=on` & `enable_uart=1` in `config.txt`, configures `cloud-init` (`user-data`) to auto-install `/home/pi/pi5_sender_node`, and safely ejects `/Volumes/bootfs`.
   * Flip **`Raspberry Pi 5 [P01]`** upside down (`FCC ID: 2ABCB-RPI5`) and slide the `SanDisk 64GB MicroSD Card [P04]` into the underside metal `J9` slot with the **shiny gold contact teeth facing UP toward the green Pi 5 board** (`Photos 29–30`).

![Real-World Build Log — Stage 2.5: Connecting Micro-USB to Pico 2, Staging Refactored Code onto SanDisk 64GB MicroSD & Seating into Raspberry Pi 5 (Photos 24–30)](images/real_build/stage2_real_world_sd_and_usb_prep.jpg)

* **Documented Real-World Stage 2.5 `Pico 2 [P07]` USB Cord, `SanDisk 64GB MicroSD [P04]` Adapter, MacBook Pro Staging & `Raspberry Pi 5 [P01]` Insertion Photos (`7` Chronological Shots, `Photos 24–30`):**
  24. [Photo 24 (`stage2_07_micro_usb_cord_connected_to_breadboard_pico2.jpg`)](images/real_build/stage2_07_micro_usb_cord_connected_to_breadboard_pico2.jpg) — **Step 2.5A:** Connecting the black Micro-USB data cord (`CORD 1`) to `Pico 2 [P07]` on `Breadboard [P09]` **without holding `BOOTSEL`** (push the Micro-USB plug firmly all the way in past the 2 tiny silver retention barbs!).
  25. [Photo 25 (`stage2_08_sandisk_64gb_microsd_and_adapter.jpg`)](images/real_build/stage2_08_sandisk_64gb_microsd_and_adapter.jpg) — **Step 2.5B:** Holding the black `SanDisk microSD Adapter` in the left hand and the red/grey `SanDisk Ultra Plus 64GB MicroSD Card [P04]` in the right hand.
  26. [Photo 26 (`stage2_09_sliding_microsd_into_adapter.jpg`)](images/real_build/stage2_09_sliding_microsd_into_adapter.jpg) — **Step 2.5C:** Sliding the `SanDisk 64GB MicroSD Card [P04]` into the bottom slot of the `SanDisk Adapter` with both printed labels facing up.
  27. [Photo 27 (`stage2_10_microsd_seated_flush_in_adapter.jpg`)](images/real_build/stage2_10_microsd_seated_flush_in_adapter.jpg) — **Step 2.5D:** Pushing the `SanDisk 64GB MicroSD Card [P04]` all the way flush into the bottom of the `SanDisk Adapter`.
  28. [Photo 28 (`stage2_11_sd_adapter_in_macbook_pro_slot.jpg`)](images/real_build/stage2_11_sd_adapter_in_macbook_pro_slot.jpg) — **Step 2.5E:** Inserting the `SanDisk Adapter + 64GB MicroSD Card [P04]` into the right-side SDXC slot of the `MacBook Pro [T02]` beside the `delete`, `\`, `return`, and `shift` keys.
  29. [Photo 29 (`stage2_12_sliding_microsd_into_pi5_underside_slot.jpg`)](images/real_build/stage2_12_sliding_microsd_into_pi5_underside_slot.jpg) — **Step 2.5F:** Sliding the updated `SanDisk Ultra PLUS 64GB MicroSD Card [P04]` into the metal `J9` underside slot of `Raspberry Pi 5 [P01]` (`FCC ID: 2ABCB-RPI5`), with shiny gold contact teeth facing UP toward the green board and the red-and-grey printed label facing away.
  30. [Photo 30 (`stage2_13_microsd_seated_flush_in_pi5_underside_slot.jpg`)](images/real_build/stage2_13_microsd_seated_flush_in_pi5_underside_slot.jpg) — **Step 2.5G:** `SanDisk 64GB MicroSD Card [P04]` pushed all the way in and seated flush inside the `Raspberry Pi 5 [P01]` underside `J9` slot — 100% ready for first boot!

2. **Upload Gatekeeper Code to `Pico 2` (`[P07]`) & Test the `QMC5883L` Magnetometer (`0x0d`):**
   * Plug the **Micro-USB data cable** (`Photo 24`) from the **`Raspberry Pi Pico 2` (`[P07]`)** into a **`USB-C` port on your MacBook Pro (`[T02]`)** *(do NOT hold `BOOTSEL` once MicroPython has been flashed via `picotool load -v -x`)*.
   * Go to **Terminal on your MacBook Pro**, type this exact command from the project folder, and press **`Enter`**:

```bash
mpremote run pi-diode-trailcam/pico_gatekeeper/test_qmc5883l.py
```

3. **What you should see:**
   * Terminal prints **`Found QMC5883L at 0x0d`** (decimal `[13]`) and a steady stream of `X / Y / Z / Delta` magnetic readings.
   * Pick up your **small steel screwdriver (`[T03]`)** and wave it within `3 cm` of the `QMC5883L` sensor (`[P08]`). You will immediately see **`<-- [MAG TRIGGER]`** appear on your MacBook Pro screen!
4. Press **`Ctrl + C`** on your MacBook Pro keyboard to stop the test, then copy the gatekeeper firmware onto the `Pico 2` by typing these exact commands and pressing **`Enter`**:

```bash
mpremote fs cp pi-diode-trailcam/pico_gatekeeper/main.py :main.py
mpremote reset
```

> **Note on Sensor Profiles:** At boot, `main.py` automatically detects connected sensors (`FULL_TRIPLE` when both `0x0d` and `0x48` are present, or `MAG_RADAR_DUTY` when only `0x0d` is present). To test automatic single-sensor magnetic wake on the bench before connecting the `HLK-LD2450` radar, either plug a jumper wire from **Breadboard `Hole a19` (`GP14`) to `Hole a18` (`GND`)** at boot or set `BENCH_MAG_ONLY = True` in `pico_gatekeeper/main.py` (`PROFILE_BENCH_MAG_ONLY`).

### Step 2.6 — Plug Power & Ethernet into `Raspberry Pi 5 (8GB)` (`[P01]`), Copy the Sender Software & Send Your First Live Alert on Your MacBook Pro

1. Plug the official **`27W USB-C` power supply** into a wall outlet and plug its `USB-C` cord into the **`USB-C PWR IN` port on the `Raspberry Pi 5 (8GB)` (`[P01]`)**. Wait **`45 seconds`** for it to boot.
2. In **Terminal on your MacBook Pro**, type these two commands one at a time (pressing **`Enter`** after each line, and entering your Pi password `trailcam` when asked) to install the required packages on the `Raspberry Pi 5` and copy the sender folder (with `COPYFILE_DISABLE=1` so no macOS `._*` files are transferred):

```bash
ssh pi@trailcam-node.local "sudo apt update && sudo apt install -y python3-opencv python3-nacl python3-serial python3-picamera2"
COPYFILE_DISABLE=1 scp -r pi-diode-trailcam/pi5_sender_node pi@trailcam-node.local:~/pi_sender_node
```

3. Enable the hardware UART serial port on the `Raspberry Pi 5` (`dtparam=uart0=on`, `enable_uart=1` with serial login console disabled) by typing this exact command in Terminal and pressing **`Enter`**:

```bash
ssh pi@trailcam-node.local "sudo raspi-config nonint do_serial_hw 0 && sudo raspi-config nonint do_serial_cons 1 && sudo reboot"
```

4. Plug a **Cat6 Ethernet cable** between the **`Raspberry Pi 5 (8GB)` (`[P01]`) Gigabit Ethernet port** and your **MacBook Pro's USB-C Ethernet adapter**. Set your MacBook Pro's Ethernet adapter IP address to **`10.10.0.100`** (subnet mask `255.255.255.0` / `/24`, allowing UDP port `5514`). *(In MacBook Pro Terminal, type `networksetup -listallhardwareports` and press **`Enter`** to see your adapter name, then type e.g. `sudo ifconfig en8 10.10.0.100 netmask 255.255.255.0 up` and press **`Enter`**.)*
5. In **Terminal Window #1 on your MacBook Pro**, type this single command and press **`Enter`** to verify your setup, start both the Collector Receiver and Live Web Dashboard (`http://127.0.0.1:8123`), and open your browser automatically (or start the two servers manually below; `ALLOW_EXAMPLE_KEYS=1` is for isolated bench testing only—before field deployment, generate unique keys with `python3 pi5_sender_node/generate_keys.py --node NODE-NORTH-01 --write-node-key ./node_key.json --register-hub ./verified_alerts/authorized_nodes.json`):

```bash
python3 pi-diode-trailcam/run_guided_bench_doctor.py --start-hub --open-browser
```

```bash
# Or manually in Terminal Tab 1 on your MacBook Pro (Collector Receiver):
cd pi-diode-trailcam
ALLOW_EXAMPLE_KEYS=1 python3 collector_hub/receiver_hub.py --out-dir ./verified_alerts
```

```bash
# And manually in Terminal Tab 2 on your MacBook Pro (Live Web Dashboard):
cd pi-diode-trailcam
python3 collector_hub/dashboard_server.py --alerts-dir ./verified_alerts --port 8123
```

6. Open a new tab in **Terminal on your MacBook Pro** (press **`⌘ Cmd + T`**), type this exact command, and press **`Enter`** to trigger a live camera capture from the **`Raspberry Pi 5 (8GB)` (`[P01]`)** (`BENCH_TEST_MODE=1` keeps the Pi 5 powered on after sending so your SSH session does not shut down):

```bash
ssh pi@trailcam-node.local "cd ~/pi_sender_node && sudo BENCH_TEST_MODE=1 RECEIVER_IP=10.10.0.100 python3 sender_node.py"
```

7. **What you should see (`✓ STAGE 2 SUCCESS CHECK`):**
   * Open **`http://127.0.0.1:8123`** in your web browser.
   * Your live camera photo appears in the dashboard gallery with a green **`Ed25519 VERIFIED`** badge!
   * Check `verified_alerts/alerts_journal.jsonl` and confirm `"camera_ok": true`, and verify that UART telemetry (`TRIG,...`) and the `DONE` signal (`GPIO23 -> GP2`) were recorded.

---

## STAGE 3: Snap Together the 1-Way Optical Fiber Data Diode (`[P13]`–`[P16]`, `[P19]`)

Once your copper Ethernet bench test works, replace the direct Cat6 cable with the **One-Way Optical Fiber Data Diode**. Every connection is a tool-free **`CLICK`** snap-fit.

![Stage 3 Golden-Path Complete: All 8 Green LEDs Lit & Clean Separated Architecture](images/real_build/stage3_golden_8_green_leds_verified_v3.jpg)

> [!CAUTION]
> **THREE CRITICAL REAL-WORLD RULES FOR `StarTech MCMGBSCSM10` (`[P13]`) & `SC/UPC` FIBER (`Photos 59–83`):**
> 1. **5V ONLY POWER RULE:** Both black `StarTech` Media Converters operate on **strictly `+5.0V DC` (center-positive)**. Power them using the included `5V` wall adapters (`Photo 61`) or the **`StarTech USB-to-Type-M` `5V` barrel cables (`[P19]`)** plugged into a `5V` USB port. **NEVER connect `12V` battery power directly to the Media Converter barrel jack!**
> 2. **SLIDE THE FRONT `LFP` SWITCH DOWN TO `OFF` BEFORE PLUGGING IN `5V` POWER (`Photos 79–81`):**
>    * Each `StarTech MCMGBSCSM10` ships from the factory with its tiny front **`LFP` (`Link Fault Pass-Through`) slide switch** in the **`ON` (`UP`)** position (`Photo 79`).
>    * Because Collector **Box #2** has its **`TX` port intentionally empty (air-gapped)**, leaving `LFP = ON` causes Box #2 to think the fiber link is broken and **shut down its RJ45 Ethernet port** (leaving only 1 green `PWR` LED lit!).
>    * **Before plugging in `5V` power** (or followed immediately by unplugging/re-plugging the rear `5V` barrel plug for `3 seconds`, since the chip **only reads the `LFP` switch at power-on boot**), slide the **`LFP` switch DOWN to `OFF`** on **both Box #1 and Box #2** (`Photo 80` & `Photo 81`)!
> 3. **PUSH EVERY BLUE `SC/UPC` PLUG PAST ITS INTERNAL SPRING UNTIL IT `CLICKS` (`Photos 74–75`):**
>    * Every blue `SC/UPC` fiber plug has a sliding outer rectangular shell and a spring-loaded white ceramic tip inside. If you stop pushing when you first feel the spring, the plug sits `3–4 mm` too shallow (`Photo 74` bottom) and will not link. Push straight in until the internal metal clip **clicks and locks** (`~1 mm` gap inside the Blue Coupler `[P15]`, or `~7 mm` of blue plastic remaining outside the `StarTech` front face).

### Step 3.1 — Unbox the Converters, Connect Cat6 Ethernet & Unzip One Single Yellow Fiber Strand (`Photos 59–73`)

1. **Set Up Both Media Converters & Cat6 Ethernet Cables (`Photos 59–64`):**
   * Set **Media Converter #1 (`[P13]` — Field / Pi 5 Side)** next to the **`Raspberry Pi 5` (`[P01]`)**, and set **Media Converter #2 (`[P13]` — Collector / MacBook Side)** across the table toward your MacBook Pro.
   * **Slide the front `LFP` switch DOWN to `OFF` on both Box #1 and Box #2.**
   * Plug the **Black Cat6 Ethernet Cable (`[P23]`)** from the **`Raspberry Pi 5` Ethernet port** into **Media Converter #1 `RJ45`** (`Photo 63`).
   * Plug the **Blue Cat6 Ethernet Cable (`[P23]`)** from **Media Converter #2 `RJ45`** into your **MacBook Pro's `USB-C` Gigabit Ethernet adapter (`[P24]`)** (`Photo 63` & `Photo 64`).
2. **Prepare the `1×2` Optical Splitter (`[P14]`) & Blue `SC/UPC` Coupler (`[P15]`) (`Photos 65–67`):**
   * Unbag the **`Duttek 1×2 Single-Mode SC/UPC` Optical Splitter (`[P14]`)** (`Photo 66`). Notice its **3 color-coded cords**:
     * **`WHITE` Cord (`1× Input`):** Receives `100%` of Field Box #1's outbound `1310 nm` laser from **`Box #1 TX`**.
     * **`BLUE` Cord (`Output Leg 1`):** Loops `50%` of the laser right back into **`Box #1 RX`** (local carrier-detect loopback).
     * **`ORANGE` Cord (`Output Leg 2`):** Sends the identical `50%` laser copy out to the **Blue `SC/UPC` Coupler (`[P15]`)** (`Photo 67`).
3. **Convert the Duplex Yellow Fiber (`[P16]`) Into a True Single-Strand 1-Way Fiber (`Photos 68–73`):**
   * Unbag the 2-meter **Yellow `Tripp Lite` Duplex OS2 Single-Mode Fiber Cable (`[P16]`)** (`Photo 68`). Because it ships as a 2-strand zip-cord, separate **one single yellow strand** so there is physically **zero return fiber** between the two boxes:
     1. Slip a small screwdriver tip or tweezers (`[T01]`) under the center tab of the **outer plastic duplex bridge clip** at both ends of the yellow cable and pop the clips off (`Photo 69` & `Photo 70`). *(Only remove the outer figure-8 bridge clip—leave the main blue rectangular connector shells on the plugs!)*
     2. Locate the **white wrap-around adhesive label** near one end of the yellow cord (`Photo 78`) and peel or snip through the paper label between the two yellow jackets (`Photo 71` — never cut the yellow jacket!).
     3. Gently pull the two yellow fiber strands apart along the thin center zip-cord web from end to end (`Photo 72`), coil your **single yellow strand** in a loose loop ($\ge 60\text{ mm}$ diameter, wider than a soda can, `Photo 73`), and store the 2nd yellow strand as a spare.

![Real-World Build Log — Stage 3 Part 1: Unboxing Media Converters, 5V Power Bricks & Ethernet Cabling (Photos 59–64, 1 Step Per Row)](images/real_build/stage3_real_world_unboxing_and_cables_part1.jpg)

![Real-World Build Log — Stage 3 Part 2: Preparing 1x2 Optical Splitter, Blue Coupler & Unzipping Single-Strand Yellow Fiber (Photos 65–71, 1 Step Per Row)](images/real_build/stage3_real_world_fiber_prep_and_unzip_part2.jpg)

### Step 3.2 — Click the Fiber Diode Together in Order & Verify All 8 Green LEDs (`4 on Box #1 + 4 on Box #2`, `Photos 74–83`)

Pull the clear plastic **dust caps** off the blue square `SC/UPC` fiber plugs right before clicking each one in. Match the **raised plastic key tab** on each blue plug to the keyway slot (`facing UP` on both `StarTech` boxes, and aligned with the U-slot on the `Blue Coupler [P15]`):

1. **`[Click 1]` Mate `ORANGE` Splitter Leg + `YELLOW` Fiber Inside the `Blue SC/UPC Coupler` (`[P15]`, `Photo 74`):**
   * Push the **`ORANGE` splitter output plug** into one end of the **Blue `SC/UPC` Coupler (`[P15]`)** and one end of your **single `YELLOW` OS2 fiber strand (`[P16]`)** into the opposite end of the Blue Coupler (both raised key tabs lined up with the coupler's U-slot).
   * **Depth Check:** Push both blue plugs firmly toward the center flange until both internal clips **click and lock** (`~1 mm` gap to the center flange on both sides).
2. **`[Click 2]` Collector Inbound Fiber (`Box #2 RX`, `Photo 81`):**
   * Plug the far end of the **single `YELLOW` OS2 fiber strand** (`key tab facing UP`) firmly into the **`RX` (Receive — right optical port)** on **Media Converter #2 (MacBook Side)** until it clicks past the internal spring.
   * **Physical Return-Path Air Gap:** Leave the **`TX` (Transmit — left optical port)** on **Media Converter #2 `100%` EMPTY / UNPLUGGED** (`Photo 81`)!
3. **`[Click 3]` Field Local Loopback (`Box #1 RX`, `Photo 75`):**
   * Plug the **`BLUE` splitter output leg** (`key tab facing UP`) firmly into the **`RX` (Receive — right optical port)** on **Media Converter #1 (Pi 5 Side)** until it clicks.
4. **`[Click 4]` Power Up Both Boxes & Plug `WHITE` Splitter Input Into `Box #1 TX` LAST (`Photos 75 & 80–83`):**
   * Plug the **`5V DC` barrel power cables** into both **Box #1** and **Box #2** (confirming both `LFP` switches are slid **DOWN to `OFF`**; if you slid `LFP` to `OFF` while powered, unplug and re-plug the `5V` barrel plug for `3 seconds` so the chip boots with `LFP = OFF`, lighting up `3 green LEDs` on Box #2 as shown in `Photo 80`).
   * Now push the **`WHITE` splitter input plug** (`key tab facing UP`) firmly into the **`TX` (Transmit — left optical port)** on **Media Converter #1** (`Photo 75`)!
   * *(**Why plug `WHITE` into `Box #1 TX` last?** In `1000BASE-LX` Gigabit fiber, when `Box #1` first detects light returning on its `RX` port, it transmits a short `Clause 37` optical auto-negotiation burst (`/C1/ -> /C2/ -> IDLE`). Plugging `WHITE` into `Box #1 TX` **after** `Box #2 RX` is already connected—or unplugging and re-plugging `WHITE` for `2 seconds`—forces `Box #1` to broadcast a fresh optical handshake simultaneously to both `Box #1 RX` and `Box #2 RX`, locking **all 4 green LEDs solid ON** on both boxes at the exact same instant!)*
5. **What you should see (`✓ STAGE 3 SUCCESS CHECK — 8/8 GREEN LEDS SOLID ON`, `Photos 81–83`):**
   * **Field Box #1 (Pi 5 Side):** All **4 green LEDs** (`Fiber LNK/ACT`, `TP LNK/ACT`, `PWR`, `1000`) are **solid GREEN** (`Photo 75` & `Photo 82`).
   * **Collector Box #2 (MacBook Side):** All **4 green LEDs** (`Fiber LNK/ACT`, `TP LNK/ACT`, `PWR`, `1000`) are **solid GREEN** (`Photo 81` & `Photo 83`), with `TX` completely empty!
   * Run the manual alert command from Step 2.6 (`sudo BENCH_TEST_MODE=1 RECEIVER_IP=10.10.0.100 python3 sender_node.py`): a verified JPEG alert arrives on **`http://127.0.0.1:8123`** across a **100% physically unidirectional strand of glass**!

![Real-World Build Log — Stage 3 Part 3: Unzipping Single Yellow Strand, Seating Blue Coupler & Lighting All 4 LEDs on Box #1 (Photos 72–77, 1 Step Per Row)](images/real_build/stage3_real_world_coupler_and_box1_part3.jpg)

![Real-World Build Log — Stage 3 Part 4: Sliding LFP Switch to OFF, Power-Cycling, Handshake Sync & Verifying All 8 Green LEDs (Photos 78–83, 1 Step Per Row)](images/real_build/stage3_real_world_lfp_off_and_golden_8leds_part4.jpg)

* **Documented Real-World Stage 3 `1-Way Optical Fiber Data Diode` Prototype Build Photos (`25` Chronological Shots, `Photos 59–83`):**
  59. [Photo 59 (`stage3_01_four_fiber_and_power_packages_staged.jpg`)](images/real_build/stage3_01_four_fiber_and_power_packages_staged.jpg) — **Step 3.0A:** Staging the 4 optical and power packages (`StarTech USB-to-Type-M 5V` barrel cables `[P19]`, `Duttek 1×2 SC/UPC` splitter `[P14]`, `Tripp Lite 2m OS2` yellow fiber `[P16]`, and `Cable Matters Blue SC/UPC` couplers `[P15]`).
  60. [Photo 60 (`stage3_02_two_startech_media_converter_boxes.jpg`)](images/real_build/stage3_02_two_startech_media_converter_boxes.jpg) — **Step 3.0B:** Staging the two identical `StarTech MCMGBSCSM10` Gigabit Ethernet to Single-Mode `SC` Fiber Media Converter boxes (`[P13]`, `1310 nm`, `10 km`).
  61. [Photo 61 (`stage3_03_unboxed_startech_converters_with_5v_power_bricks.jpg`)](images/real_build/stage3_03_unboxed_startech_converters_with_5v_power_bricks.jpg) — **Step 3.0C:** Unboxed `StarTech MCMGBSCSM10` metal chassis (`Box #1` and `Box #2`) with their included `+5.0V DC` center-positive wall adapters.
  62. [Photo 62 (`stage3_04_startech_front_ports_and_5v_dc_jack_closeup.jpg`)](images/real_build/stage3_04_startech_front_ports_and_5v_dc_jack_closeup.jpg) — **Step 3.0D:** Close-up inspection of the front `SC` optical ports (with black rubber dust cap installed), 4 status LEDs, `LFP` slide switch, `RJ45` jack, and rear `+5V DC` barrel jack.
  63. [Photo 63 (`stage3_05_both_startech_boxes_ethernet_cables_connected.jpg`)](images/real_build/stage3_05_both_startech_boxes_ethernet_cables_connected.jpg) — **Step 3.1A:** Connecting the Black `Cat6` Ethernet cable (`[P23]`) between `Raspberry Pi 5 [P01]` and Field `Box #1`, and the Blue `Cat6` Ethernet cable (`[P23]`) to Collector `Box #2`.
  64. [Photo 64 (`stage3_06_blue_ethernet_in_macbook_usbc_adapter.jpg`)](images/real_build/stage3_06_blue_ethernet_in_macbook_usbc_adapter.jpg) — **Step 3.1B:** Plugging the Blue `Cat6` Ethernet cable from Collector `Box #2` into the `USB-C` Gigabit Ethernet adapter (`[P24]`) on the MacBook Pro (`[T02]`).
  65. [Photo 65 (`stage3_07_duttek_blue_and_orange_plugs_caps_removed.jpg`)](images/real_build/stage3_07_duttek_blue_and_orange_plugs_caps_removed.jpg) — **Step 3.1C:** Pulling the clear plastic dust caps off the `Blue` (Output Leg 1) and `Orange` (Output Leg 2) `SC/UPC` plugs of the `Duttek 1×2` splitter (`[P14]`).
  66. [Photo 66 (`stage3_08_duttek_splitter_all_three_cords_white_blue_orange.jpg`)](images/real_build/stage3_08_duttek_splitter_all_three_cords_white_blue_orange.jpg) — **Step 3.1D:** All 3 color-coded `SC/UPC` cords of the `1×2` Optical Splitter (`[P14]`) uncapped and identified (`White` = `1× Input` from `Box #1 TX`; `Blue` = `Output Leg 1` to `Box #1 RX`; `Orange` = `Output Leg 2` to `Blue Coupler [P15]`).
  67. [Photo 67 (`stage3_09_blue_sc_coupler_black_dust_caps_removed.jpg`)](images/real_build/stage3_09_blue_sc_coupler_black_dust_caps_removed.jpg) — **Step 3.1E:** Removing both black protective dust caps from the `Blue Cable Matters SC/UPC` female-to-female simplex coupler (`[P15]`).
  68. [Photo 68 (`stage3_10_yellow_duplex_fiber_cable_unbagged.jpg`)](images/real_build/stage3_10_yellow_duplex_fiber_cable_unbagged.jpg) — **Step 3.1F:** Unbagging the 2-meter `Tripp Lite` Duplex Yellow `OS2` Single-Mode `SC/SC` patch cable (`[P16]`).
  69. [Photo 69 (`stage3_11_prying_open_duplex_clip_on_yellow_fiber.jpg`)](images/real_build/stage3_11_prying_open_duplex_clip_on_yellow_fiber.jpg) — **Step 3.1G:** Gently popping off the outer plastic duplex joining clip holding the two blue `SC/UPC` plugs together.
  70. [Photo 70 (`stage3_12_duplex_clip_removed_two_yellow_fiber_plugs_separated.jpg`)](images/real_build/stage3_12_duplex_clip_removed_two_yellow_fiber_plugs_separated.jpg) — **Step 3.1H:** Outer plastic duplex clip removed, separating the two individual blue `SC/UPC` connector plugs cleanly.
  71. [Photo 71 (`stage3_13b_peeling_white_wrap_label_to_separate_yellow_strands.jpg`)](images/real_build/stage3_13b_peeling_white_wrap_label_to_separate_yellow_strands.jpg) — **Step 3.1I:** Peeling off the white adhesive wrap-around cable label with tweezers (`[T01]`) so the two yellow fiber strands can unzip cleanly.
  72. [Photo 72 (`stage3_14_unzipping_duplex_yellow_fiber_into_single_strand.jpg`)](images/real_build/stage3_14_unzipping_duplex_yellow_fiber_into_single_strand.jpg) — **Step 3.1J:** Pulling the two yellow `OS2` fiber strands apart along the center zip-cord web to isolate a single unidirectional fiber strand.
  73. [Photo 73 (`stage3_15_single_yellow_fiber_strand_ready_caps_removed.jpg`)](images/real_build/stage3_15_single_yellow_fiber_strand_ready_caps_removed.jpg) — **Step 3.1K:** Single 2-meter yellow `OS2` fiber strand coiled loosely ($\ge 60\text{ mm}$ bend diameter) with clear dust caps removed from both blue `SC/UPC` ends.
  74. [Photo 74 (`stage3_16_blue_coupler_joining_orange_splitter_and_yellow_fiber.jpg`)](images/real_build/stage3_16_blue_coupler_joining_orange_splitter_and_yellow_fiber.jpg) — **Step 3.1L:** Mating the `Orange` splitter leg (top) and single `Yellow` fiber strand (bottom) inside the `Blue SC/UPC Coupler [P15]` (push both plugs all the way in until both internal clips click!).
  75. [Photo 75 (`stage3_17_pi_startech_box1_white_tx_blue_rx_all_4_green_leds.jpg`)](images/real_build/stage3_17_pi_startech_box1_white_tx_blue_rx_all_4_green_leds.jpg) — **Step 3.1M:** Close-up of Field `Box #1` (`Pi 5` side) with `White` in `TX`, `Blue` loopback in `RX`, and Black `Cat6` in `RJ45` — **all 4 green LEDs (`Fiber LNK/ACT`, `TP LNK/ACT`, `PWR`, `1000`) glowing solid green!**
  76. [Photo 76 (`stage3_18_field_side_topdown_pi5_breadboard_box1_splitter_coupler.jpg`)](images/real_build/stage3_18_field_side_topdown_pi5_breadboard_box1_splitter_coupler.jpg) — **Step 3.1N:** Top-down view of the Field Side (`Breadboard + Pico 2 + GY-271 + Pi 5 + Camera Module 3 + Box #1 + 1×2 Splitter + Blue Coupler`).
  77. [Photo 77 (`stage3_19_field_side_angled_box1_4_green_leds_and_splitter.jpg`)](images/real_build/stage3_19_field_side_angled_box1_4_green_leds_and_splitter.jpg) — **Step 3.1O:** Angled view of the Field Side showing all 4 green LEDs glowing on `Box #1` alongside the `1×2` Optical Splitter (`[P14]`).
  78. [Photo 78 (`stage3_13a_locating_white_wrap_label_on_yellow_duplex_cord.jpg`)](images/real_build/stage3_13a_locating_white_wrap_label_on_yellow_duplex_cord.jpg) — **Step 3.2A:** Inspecting the yellow fiber jacket and key-tab orientation before seating the far end into Collector `Box #2 RX`.
  79. [Photo 79 (`stage3_20_macbook_box2_lfp_on_only_pwr_led_before_switch_off.jpg`)](images/real_build/stage3_20_macbook_box2_lfp_on_only_pwr_led_before_switch_off.jpg) — **Step 3.2B (Diagnostic Landmark — `LFP = ON`):** Close-up of Collector `Box #2` showing why leaving the factory `LFP` switch in `ON` (`UP`) holds the converter in Link Fault Pass-Through lockout (only 1 green `PWR` LED lit, disabling `RJ45`).
  80. [Photo 80 (`stage3_21_lfp_switched_off_power_cycled_3_green_leds_ethernet_up.jpg`)](images/real_build/stage3_21_lfp_switched_off_power_cycled_3_green_leds_ethernet_up.jpg) — **Step 3.2C (`LFP = OFF` + Power-Cycle Reset):** After sliding `LFP` **DOWN to `OFF`** and unplugging/re-plugging the `5V DC` barrel plug for `3 seconds`, `TP LNK/ACT` and `1000` light up green (`3 green LEDs` on `Box #2`).
  81. [Photo 81 (`stage3_22_macbook_startech_box2_all_4_green_leds_rx_verified_closeup.jpg`)](images/real_build/stage3_22_macbook_startech_box2_all_4_green_leds_rx_verified_closeup.jpg) — **Step 3.2D (`ALL 4 GREEN LEDS LIT ON BOX #2`):** Macro close-up of Collector `Box #2` after re-plugging `White` (`Box #1 TX`) for `2 seconds` to sync the `1000BASE-X` optical handshake — **all 4 green LEDs (`Fiber LNK/ACT`, `TP LNK/ACT`, `PWR`, `1000`) solid green, Yellow fiber in `RX`, and `TX` `100%` empty air-gap!**
  82. [Photo 82 (`stage3_23_full_benchtop_angled_both_boxes_all_8_green_leds.jpg`)](images/real_build/stage3_23_full_benchtop_angled_both_boxes_all_8_green_leds.jpg) — **Step 3.2E:** Full angled benchtop verification showing **all 4 green LEDs on Field Box #1 (left)** and **all 4 green LEDs on Collector Box #2 (right)** glowing simultaneously (`8/8` green LEDs!).
  83. [Photo 83 (`stage3_24_full_benchtop_clean_separated_bundles_golden_overview.jpg`)](images/real_build/stage3_24_full_benchtop_clean_separated_bundles_golden_overview.jpg) — **Step 3.2F (Golden-Path Stage 3 Overview):** Cleanly separated top-down overview of the complete Stage 3 system (`Collector Box #2` at top, `Field Box #1 + Pi 5 + Camera + Breadboard + Pico 2 + GY-271` at bottom-left, and `1×2 Splitter + Blue Coupler + Yellow OS2 Fiber Loop` at right).

---

## Step 5: Unpowered Enclosure Dry Fit & Next Steps

Before drilling or wiring the outdoor battery, place the actual `12V 12Ah` battery (`[P17]`) and mounting components inside the `QILIPSU` enclosure (`[P21]`) **without connecting the battery terminals**. Verify board clearances, fiber loop radii ($\ge 30\text{ mm}$, wider than a soda can), lid closure, insulation, and service access.

---

## Step 6: Post-Stage 2 Engineering Assessment, Zero-Redesign Vibration Locking & Quantitative Field Risk Matrix

### 6.1 Why We Keep the Exact COTS Breadboard (`[P09]`) & `2.54mm` Wiring (Zero Custom PCBs, Zero Second Design)
1. **Supply-Chain Anonymity & OPSEC:** Ordering a custom PCB from a fabrication house (`JLCPCB`, `PCBWay`, `OSH Park`) creates a permanent, uniquely identifiable digital trail (`Gerber` layout files + account + payment + shipping record) and produces a custom-etched circuit board that forensically links any recovered field unit back to a single batch order. By contrast, `ELEGOO` `30-row` solderless breadboards (`[P09]`) and standard `2.54 mm` jumper ribbons (`[P10]`) are sold in millions of generic hobbyist kits worldwide—giving the hardware **100% COTS plausible deniability and zero custom fabrication footprint**.
2. **Cost & Modification Agility:** In low-to-medium quantities (`1–20 units`), custom PCBs do **not** reduce total cost once connectors, assembly, and shipping are counted (`~$15–$35` vs. `$1.50` for a COTS breadboard), yet they freeze your pinout in fiberglass. If you ever want to swap a sensor or reassign a GPIO pin in the field, a custom PCB requires cutting traces or waiting weeks for a re-spin, whereas the breadboard lets you move a wire in `5 seconds`.
3. **Zero Second Build:** Switching from the Stage 2 breadboard to a different soldered breakout board for field deployment would force you to **build and re-test a second hardware design from scratch**. Instead, we keep the **exact breadboard assembly you already built and verified in Stage 2** (`100% identical hole and pin layout`) and mechanically lock its connections in place in `2 minutes` using materials already in your kit (`[T11]`).

### 6.2 How to Make Your Exact Current Breadboard Build 100% Car & Snowmobile Vibration-Proof (Zero Re-Wiring)
Why do standard single-pin (`1x1`) Dupont jumpers loosen during vehicle or snowmobile transport?
* **90% of pull-outs** happen when the Breadboard and the `Raspberry Pi 5` slide or bounce *relative to each other*, pulling on the `W5–W7` bridge wires.
* **10% of pull-outs** happen when high-frequency engine/track vibration (`20–200 Hz`) causes isolated `1x1` plastic housings to rock side-to-side and slowly walk upward.

Apply this **3-Step In-Place Mechanical Lock** directly to your finished Stage 2 build **without unplugging a single wire**:
1. **Rigid Co-Mounting on the Same Backplate (`QILIPSU [P21]` Grid Plate):** Peel the backing off the `3M` double-sided foam tape on the underside of your `30-Row Breadboard [P09]` and press it firmly onto the rigid white ABS mounting grid plate right next to the `Raspberry Pi 5 [P01]` (`3 cm` apart), then pass a nylon zip-tie around the breadboard waist through the grid holes as a mechanical backup. Because both boards are locked to the **same rigid plate**, there is **zero relative movement** between the Breadboard and `Pi 5` over rough terrain.
2. **Bind Adjacent `1x1` Jumper Shells into Multi-Pin Blocks (`3M Tape [T11]` or `1x4` Housing):** Wrap one tight turn of `3M` tape (`[T11]`) around the 4 adjacent black plastic jumper housings in `Column f` (`Rows 24–27`: `Red, Black, Yellow, Blue`), around the `Pico 2` left-column housings (`Col a`), and around the 3 `Pi 5` GPIO sockets (`Pins 10, 14, 16`). When adjacent `1x1` housings are bound into a unified block, individual pins cannot tilt or pivot, increasing pull-out resistance by **`4x`**. *(Optional COTS upgrade for future units: lift the tiny plastic retention tab on each `1x1` shell with tweezers, slide the metal crimp terminal out, and click all 4 sensor wires into a single standard `1x4` `2.54mm` Dupont plastic block housing so it snaps in as a single 4-pin plug!)*
3. **Peelable Elastomeric Damper Bead (`Permatex Black Silicone [T11]` — Already in Your Kit):** Squeeze a small `2 mm` bead of **`Permatex RTV Black Silicone [T11]`** along the seam where the black plastic jumper housings meet the face of the breadboard, where the blue `GY-271` PCB meets its 5-pin header, and where the 3 female sockets meet the `Pi 5` GPIO header. It cures into a flexible, sub-zero-rated (`-54°C to +204°C`) rubber vibration damper that survives `10G+` snowmobile shocks—yet **peels off cleanly in one piece with tweezers** if you ever want to service or modify a wire!

### 6.3 Comprehensive Quantitative System & Technical Risk Assessment (Based on Stage 2 Physical Build Findings)

The table below quantifies every remaining technical risk across the physical mounts, electrical contacts, optical viewport, camera focus pipeline, and cold-weather power budget—showing the **Unmitigated Failure Probability**, **Mitigated Failure Probability**, **Severity (`1–5`)**, **Exact Physical Location**, and **Concrete COTS Mitigation**:

| # | Risk Category & Exact Physical Location / Mount | Lesson Learned Today / Failure Mechanism | Unmitigated Risk (%) | Mitigated Risk (%) | Severity (`1–5`) | Concrete Zero-Redesign COTS Mitigation |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **R1** | **Breadboard & GPIO Jumper Walk-Out (`Col f f24–f27`, `Col a`, `Pi 5 Pins 10/14/16`)** | Individual `1x1` Dupont pins can pivot and back out under `20–200 Hz` snowmobile/car vibration or relative board motion. | **65%** | **< 2%** | **5 (Critical)** | **Co-mount `Breadboard [P09]` (`3M` backing + zip-tie) & `Pi 5 [P01]` on the same `QILIPSU` grid plate + bind adjacent `1x1` shells with `3M` tape + apply a peelable `2 mm` `Permatex Silicone [T11]` bead across shell bases.** |
| **R2** | **Internal "J-Hook" Bent Jumper Pin Tip (`Breadboard Spring Clips, e.g. Blue W3 f27`)** | Pushing a soft square pin into a stiff new breadboard hole at a slight angle bends the tip into a hook (`stage2_38`), causing an intermittent open circuit or sideways short to the next row. | **30%** | **< 1%** | **4 (High)** | **Inspect and flatten any curved pin at `90°` with smooth flat-nose pliers (`stage2_39`) before insertion; verify `0x0d` I2C response before applying silicone damper bead.** |
| **R3** | **Unsoldered `GY-271` Compass Through-Holes (`Col j Rows 24–28`, `Pins 1–4`)** | Loose through-holes (`1.0 mm` hole vs. `0.64 mm` pin) on an unsoldered header lose `SDA`/`SCL` contact (`[]` on `i2c.scan()`), and bending brittle brass header pins with pliers snaps them. | **80%** | **< 1%** | **5 (Critical)** | **Solder the 4 active pins (`VCC, GND, SCL, SDA`) — or if no soldering iron is available, use an aluminum-foil conductive sleeve, a wooden toothpick wedge, or pin the 4 jumper wires directly through the PCB holes into `Col j` (NEVER bend brittle brass header pins with pliers!).** |
| **R4** | **`CSI` Ribbon Micro-Creep in Vertical `J4 (CAM/DISP 0)` & `Camera Module 3` ZIF Latches** | `200mm` orange ribbon (`[P06]`) has stiff spring tension; pulling on the ribbon during Zone 1 pod mounting can tug the `1.5 mm` brown friction wedge loose. | **25%** | **< 1%** | **5 (Critical)** | **Seat ribbon `2 mm` deep (zero gold teeth visible), lock brown latch flush, and add a `3M` tape strain-relief loop anchoring the orange ribbon to the enclosure wall `3 cm` behind each connector so zero tension reaches the latch.** |
| **R5** | **`Pico 2` Micro-USB Port (`J1`) Detent & Cable Leverage (`Breadboard Row 1`)** | The `Pico 2` Micro-USB socket has tight metal locking barbs; a stiff USB cord can lever `Row 1` of the `Pico 2` upward out of the breadboard. | **20%** | **< 1%** | **4 (High)** | **Push Micro-USB plug 100% flush past the 2 retention barbs while holding `Pico 2` down with two fingers; in Stage 5 field deployment, power flows via breadboard rail + zip-tied cable strain relief.** |
| **R6** | **Camera Autofocus Hunting on Foreground Pine Needles / Snowflakes (`Camera Module 3 NoIR Wide [P05]`)** | By default, `IMX708` motorized PDAF focuses on the closest high-contrast twig or falling snowflake (`0.2 m`), blurring a person or vehicle at `5–15 m` on the trail and dropping YOLO recall. | **50%** | **< 2%** | **4 (High)** | **Lock the VCM lens in [`sender_node.py`](../pi5_sender_node/sender_node.py) to Fixed Hyperfocal Mode (`AfMode = 0`, `LensPosition = 0.5` diopters = `2.0 m` focus center), keeping everything from `1.0 m` to $\infty$ razor-sharp with `0 ms` focus delay.** |
| **R7** | **Motion Blur on Walking/Running Targets at Dusk (`IMX708` Auto-Exposure Slow Shutter)** | In low light under forest canopy, default auto-exposure slows shutter speed to `1/15 s` (`66 ms`), smearing a walking person (`1.5 m/s`) across `10 cm` of pixels. | **45%** | **< 3%** | **3 (Medium)** | **Cap maximum exposure time in `picamera2` controls to `ExposureTime <= 8000` (`1/125 s` day/dusk) or `12000` (`1/80 s` night IR) and let analog gain (`AnalogueGain = 1.0–8.0`) compensate so every frame is crisp.** |
| **R8** | **Internal `940nm` IR LED Glare Reflecting Off the `30mm` Glass Viewport (`Zone 1 Pod [P20]`)** | If the 2 side `940nm` IR LEDs shine onto the inside surface of the `30mm` glass disc (`[T11]`), internal reflection washes out the central `IMX708` lens with a white fog halo at night. | **60%** | **< 2%** | **4 (High)** | **Press the included black neoprene foam baffle ring (`[P20]`) tightly around the central camera lens barrel so it butts flush against the glass disc, optically isolating the lens from the side IR LEDs.** |
| **R9** | **`SC/UPC` Fiber Ferrule Dust Contamination or Micro-Bend Loss (`Zone 3 Optical Diode [P13]–[P16]`)** | A single skin-oil smudge on the `9 µm` single-mode glass core or bending the yellow fiber tighter than a `30 mm` radius attenuates the `1310 nm` laser link. | **20%** | **< 1%** | **4 (High)** | **Keep white dust caps on until the exact second of clicking (`[Click 1–3]`), never touch the white ceramic tip, and coil excess fiber in wide loops ($\ge 60\text{ mm}$ diameter, wider than a soda can) inside `QILIPSU [P21]`.** |
| **R10** | **Sub-Zero Battery Voltage Sag During `Pi 5` Cold Boot (`-25°C` Boreal Winter)** | Surface air at `-30°C` reduces `12V` lead-acid/AGM capacity by `~40%` and raises internal resistance during the `Pi 5` `2.5A` boot surge. | **35%** | **< 2%** | **4 (High)** | **Bury `Zone 3 Vault [P21]` `20–30 cm` underground beneath forest moss/snow with `10–20 mm` closed-cell foam insulation (holding soil/vault temperature at `-2°C to -8°C` year-round) + `5V` buck converter headroom.** |

### 6.4 Real-Time Raspberry Pi 5 YOLO Object Detection, Aspect-Ratio Letterboxing & "No-Vanish" Persistence Tracking (`Photos 84–86`)

To support real-time human, cell-phone, and camouflaged/fallen-target detection directly on the **Raspberry Pi 5 (`4× Cortex-A76 @ 2.40 GHz`)** without requiring an external GPU, [`sender_node.py`](../pi5_sender_node/sender_node.py) and [`collector_hub/ui/index.html`](../collector_hub/ui/index.html) implement a 3-stage detection and persistence pipeline:

1. **Physical Raspberry Pi 5 CPU ONNX Runtime Benchmarks (`4× Cortex-A76 @ 2.40 GHz`):**
   * **`yolov8n.onnx` (`640×640`):** `167.4 ms/frame` (`5.97 FPS`) — high-detail single-frame burst verification.
   * **`yolov8n_416.onnx` (`416×416`):** `66.0 ms/frame` (`15.16 FPS`) — balanced real-time tracking.
   * **`yolov8n_320.onnx` (`320×320`):** `39.1 ms/frame` (`25.58 FPS`) — full real-time `25+ FPS` streaming (`1.18 s` for `30` frames).
   * **`yolov8n_256.onnx` (`256×256`):** `23.4 ms/frame` (`42.68 FPS`) — ultra-fast `30+ FPS` real-time gatekeeping (`0.70 s` for `30` frames).
2. **Aspect-Ratio Letterboxing (`letterbox_image` — `16.3×` Confidence Gain on Horizontal Targets):**
   * Naive `cv2.resize(frame, (640, 640))` squishes `16:9` (`1920×1080`) or `9:16` (`480×848`) frames by `1.77×`, crushing horizontal or crouched targets down to `0.0038` (`0.38%`). Preserving `1:1` aspect ratio with `(114, 114, 114)` letterbox padding increases fallen/floor human confidence by **`16.3×`**.
3. **Target-Count Conservation ("No-Vanish" Persistence Zone) + `90°` Fallen-Pose Probing (`86×` Confidence Gain):**
   * [`NoVanishPersistenceTracker`](../pi5_sender_node/sender_node.py) tracks peak human count inside the camera's field of view and monitors frame borders (`border_margin = 0.06`). If the standing count drops without a border exit (because a subject crouched, went prone, or blended into floor/forest clutter), the tracker locks a **`NO-VANISH ZONE`** around the last interior coordinates and runs [`probe_rotated_90_roi`](../pi5_sender_node/sender_node.py) (`cv2.ROTATE_90_COUNTERCLOCKWISE`), aligning horizontal fallen subjects with YOLOv8's vertical human prior and boosting confidence **`86×`** (`0.0038 -> 0.3273`).
4. **Documented Boreal Trail Live-Stream Detection Captures (`Photos 84–86`):**
   * 84. [Photo 84 (`stage4_01_boreal_trail_yolo_standing_lock.png`)](images/real_build/stage4_01_boreal_trail_yolo_standing_lock.png) — **Frame 556 (`18.5s`):** Real-time multi-person boreal forest trail tracking (`PERSON 0.87`, `PERSON 0.79`) with active `NO-VANISH ZONE (2/2 CONSERVED IN FOV)` conservation overlay.
   * 85. [Photo 85 (`stage4_02_boreal_trail_yolo_crouch_transition.png`)](images/real_build/stage4_02_boreal_trail_yolo_crouch_transition.png) — **Frame 684 (`22.8s`):** Mid-transition tracking (`PERSON 0.86`, `PERSON 0.54 [LETTERBOX 16.3x]`) maintaining `NO-VANISH ZONE (2/2 CONSERVED IN FOV)` lock as Subject #2 crouches behind snow-covered fern clutter.
   * 86. [Photo 86 (`stage4_03_boreal_trail_yolo_no_vanish_90deg_probe.png`)](images/real_build/stage4_03_boreal_trail_yolo_no_vanish_90deg_probe.png) — **Frame 742 (`24.8s`):** Continuous conservation tracking (`PERSON 0.85`, `PERSON (90° CCW ROI) 0.72 [86x GAIN]`) via `probe_rotated_90_roi` as Subject #2 goes horizontal/prone on the snowy forest floor.

---

* Proceed to **[Part 2: IKEA-Style Enclosure Build, Camouflage & Tree Installation Manual (Stages 4–6)](AERIAL_OBSERVATION_DRONE_GUIDE.md)** for step-by-step instructions to build the weatherproof pods, wire the `12V` battery safely, camouflage the tree unit, and run the complete system in the field.
* Follow the **[Field Testing & Validation Plan](DESIGN_EVOLUTION_AND_STABILIZATION_LOG.md)** for full off-grid acceptance checks.
* The **[`200 m – 20 km` All-Weather Troposcatter & Canopy-Bounce Relay (`sky-diode-relay` `Build D`)](AERIAL_OBSERVATION_DRONE_GUIDE.md)** is assembled separately in `~35–45 minutes` (zero soldering) and is not required for Stages 1–3 indoor camera/fiber bring-up.
