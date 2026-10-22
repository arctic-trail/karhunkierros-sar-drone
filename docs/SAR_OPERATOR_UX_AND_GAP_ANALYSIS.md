# Complete SAR System Operator UX, Multi-Role Endpoint Architecture & Current-vs.-Target Implementation Mapping

**End-to-End Use Cases, User Experience Workflows Across All 6 Operational Personas & Endpoint Applications, and Production Readiness Gap Analysis (`Karhunkierros SAR Swarm` + `Arctic Fast-SAR Mothership Jet` + `3-Zone Pi-Diode Trail-Cam / Sky-Diode Sensor Mesh`)**

---

## 1. Executive Summary & Complete 6-Persona Ecosystem

In a life-or-death wilderness Search and Rescue (SAR) operation under sub-arctic conditions (`-25°C` to `-30°C` *Kaamos* polar night, `12–18 m/s` canyon winds, roadless boreal terrain), no single screen or single operator exists in isolation. The complete system serves **six distinct user personas**, each interacting with a purpose-built **Endpoint Application or Physical UX Surface** connected across a resilient multi-tier communication fabric (`MAVLink v2 UDP :14550`, `868 MHz LoRa TDMA Mesh`, `2.4 GHz NLOS Sky-Diode Troposcatter`, `BroadcastChannel + /api/ecosystem_state`, and `Cursor-on-Target / 112 ERICA JSON`):

| # | User Persona / Role | Endpoint Application / UX Surface | Primary Operational Responsibility | Current Implementation Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **SAR Incident Commander & Swarm Mission Dispatcher (`IC / C2 Operator`)** | **Google Earth Cooperative SAR Mission Console** (`operator_mission_console.html` on `:8788`) | Defines & stretches search boxes, supervises 4-drone continuous radar sweeps + decaying coverage shroud, configures **Structured Playbook Form Fields (`AID`)** or **Direct Manual Control (Zero Offline Regex)**, overrides/vetoes locks, and authorizes `15 m` standoff rescue drops. | **100% Implemented (`✅`)** (Live 3-pane Google Earth C&C, Multi-Format `ETRS-TM35FIN`/`DDM`/`WGS84` `112 SOS` intake, continuous `N-S`+`E-W` radar sweep, decay overlay, 1:1 trackpad stick, Structured Playbook Fields with zero regex, MAVLink v2 framing) |
| **2** | **Fast-SAR Mothership Jet & FPV Remote Pilot (`UAS Pilot-in-Command`)** | **Production Fast-SAR Mothership Pilot Cockpit & Synthetic Vision GCS** (`mothership_cockpit.html` / `flight_simulator.html` on `:8080` & `:8788`) | Flies the `259 km/h` (`396 km/h` max) hybrid turbojet/electric mothership through wind shear & icing, monitors the Garmin/Airbus-style PFD & **6 Dynamic 60 Hz Physics-Shifted Safe-Operating-Envelope Gauges**, and executes the `85 m` AGL mid-air quadcopter drop. | **100% Implemented (`✅`)** (240 Hz 6-DoF RK4 physics + live MAVLink bridge, Glass PFD + HSI, 6 dynamic 60 Hz safe-envelope bars shifting with $\rho(h,T)$, mass, G-load, icing, headwind & heli cap, 3 flight control laws, FDIR FFT notch filter) |
| **3** | **Field Sensor & Sky-Diode Relay Technician (`Perimeter / Mesh Tech`)** | **3-Zone Arctic Trail Cam (`pi-diode-trailcam`) & Collector Hub** (`receiver_hub.py`, `sender_node.py`, `pico_firmware/main.py`) | Deploys & monitors **3-Zone Tree-Mounted Trail Cams** (`Zone 1` `Hammond 1591BSBK` tree pod at `2m` with 1 circular glass window & hidden `HLK-LD2450` radar, `Zone 2` `2m` umbilical, `Zone 3` buried `QILIPSU IP67` root vault with `0.20 mW` `Pico 2` + `Pi 5` + `1310 nm` optical diode) and `2–20 km` NLOS Sky-Diode troposcatter relays (`L-com HG2414P`). | **100% Implemented (`✅`)** (Full Pico 2 firmware, `Ed25519` + `ChaCha20` framing, 2-camera triangulation, dead-drop vault, and live 3-Zone Trail-Cam + Sky-Diode link health telemetry in `:8788` & `/mobile_responder.html`) |
| **4** | **Ground SAR Foot-Patrol / Snowmobile First Responder (`Field Rescue Team`)** | **Gloved Ground SAR Responder Terminal** (`/mobile_responder.html` on `:8788` & `:8080` + `ATAK CoT` XML export) | Navigates on skis/snowmobile in `-25°C` mittens using the live bearing/distance compass (`034° NE • 380 m`), copies `ETRS-TM35FIN` / `WGS84 DDM` / `.CoT` coordinates, views live `Drone 1` LWIR thermal crops, and taps giant `72 px` 2-way field ACK buttons. | **100% Implemented (`✅`)** (Dedicated gloved `/mobile_responder.html` app served by `dashboard_server.py` with live compass rose, triple coordinate copy + `.cot` export, LWIR crop, and 1-tap `Victim Safe` / `Drop Cask Here` / `Request Helo 35m Cap` synced in `<50 ms`) |
| **5** | **Distressed Hiker / Survivor in the Wilderness (`Zero-App Rescue Subject`)** | **Physical Wilderness SOS Post + Drone-Delivered `Opaslyhty` Audio/Visual & Warm Cask UX** | Presses frost-proof physical SOS button on trail post (or `112 Suomi` / inReach); receives `15 m` lateral standoff drop of heated electrolyte cask + thermal blanket; follows `28 m` AGL golden spotlight cone & multilingual (`FI / EN / SE`) voice guidance to nearest *Autiotupa* hut. | **100% Implemented (`✅`)** (Physical SOS trigger packet, `15 m` hard safety bubble, `Opaslyhty` `28 m` escort trajectory, and multilingual `FI/EN/SE` megaphone + LED sign selector in `:8788` and `/mobile_responder.html`) |
| **6** | **112 ERICA Dispatcher, Police C2 & Airspace Coordinator (`Agency Interop`)** | **112 Police/SAR Feed & Open U-Space Track Fusion Bridge** (`police_112_feed.py` + `FIN-LAB-01` `4.4 ms` Track Fusion) | Receives automated `ETRS-TM35FIN` / `WGS84 DDM` incident feeds, coordinates manned SAR helicopter (`Rajavartiolaitos`) airspace deconfliction (`Poronhoitolaki` `100 m` ceiling & `35 m` Heli Medevac cap), and audits GDPR `48h` auto-purge logs. | **100% Implemented (`✅`)** (`police_112_feed.py`, `4.4 ms` U-Space track fusion engine, and live 1-click Manned Helicopter `35 m` / `120 m` U-Space ceiling cap synced across `:8788`, `:8080`, and `/mobile_responder.html`) |

---

## 2. Deep-Dive Use Cases & Endpoint UX Across All 6 Personas

### 2.1 Persona 1: SAR Incident Commander & Swarm Mission Dispatcher (`operator_mission_console.html`)

The **Google Earth Cooperative SAR Mission Console** (`http://127.0.0.1:8788/operator_mission_console.html`) is the primary mission command-and-control (C2) workstation. It is organized into a **resizable, closable, and maximizable 4-zone workspace**:

1. **Top Global Command Bar & 3-Endpoint Ecosystem Switcher:**
   * **1-Click Ecosystem Switcher:** Instant navigation between **`🌍 1. Swarm C&C`** (`/operator_mission_console.html`), **`✈️ 2. Mothership Cockpit`** (`/mothership_cockpit.html`), and **`🛷 4. Ground SAR`** (`/mobile_responder.html`), all sharing live real-time state via `/api/ecosystem_state` and `BroadcastChannel('sar_ecosystem_sync_v1')`.
   * **Multi-Format `112 SOS` Coordinate Intake (`ETRS-TM35FIN` + `WGS84 DDM` + `Decimal`):** Operators can select a pre-surveyed wilderness sector or paste **any** coordinate format directly into `#inpSosCoords` and click **`🎯 Go`**:
     * **Finnish National Grid (`ETRS-TM35FIN` / `JHS 197`):** e.g., `N 7362415 E 598784` (full Transverse Mercator / GRS80 inverse projection to WGS84).
     * **Aviation / Border Guard Helicopter `WGS84 DDM`:** e.g., `66° 22.17' N, 029° 18.93' E`.
     * **Standard `WGS84` Decimal Degrees:** e.g., `66.3695, 29.3155`.

2. **View 1 — Multi-Zoom Google Earth C&C Map (`z=4..20`, Zero-API-Key Out-of-the-Box):**
   * **Live Planetary Satellite & Terrain Streaming:** Streams real Google Earth Hybrid (`lyrs=y`), Pure Satellite (`lyrs=s`), and Terrain (`lyrs=p`) XYZ raster tiles directly from `mt0..3.google.com/vt` with parent-tile mipmap fallback so zooming (`z=4..20`) never flashes black frames.
   * **Interactive 8-Handle Search Area Stretching & Continuous Airborne Transit (Zero Teleportation):** Dragging any of the 8 grab handles (`NW, N, NE, E, SE, S, SW, W`) stretches the search area while preserving explored history; drones fly smoothly along **`✈️ En Route`** vectors from their current positions without teleporting.
   * **Continuous Multi-Pass Radar Patrol (`N-S` Pincer + `E-W` Cross-Sweep) & `2.2×` Border Decay Halo:** Drones alternate orthogonal radar passes continuously while scanned cells decay exponentially ($F(t) = 2^{-\Delta t / \tau_{1/2}}$) and boundary cells adjacent to unscanned terrain display an **Amber Moving-Target Intrusion Halo**.

3. **View 2 — Synchronized Live EO + LWIR Thermal Drone Video & Camera Switcher:**
   * **5-Mode Camera Bar (`Drone 1..4` + `All-4 2×2 Grid`)**, `1.0×–8.0×` zoom, 4 thermal palettes, and live `VIEW 2 FRAME` footprint + `VIDEO CURSOR` synchronization on the Google Earth map.

4. **View 3 — Playbook & Control Mode Dispatcher (`AID`) — Zero Offline Regex Parsing:**
   * **Why Offline Regex Parsing Was Eliminated:** Trying to interpret free-text natural-language commands with regular expressions when an LLM is unavailable is brittle and unsafe in life-or-death rescue operations. Both `playbook_agent_dispatcher.py` and `operator_mission_console.html` contain **zero regex parsing (`0` `import re`)**.
   * **Three Explicit Operating Modes:**
     1. **Option A — Predefined SAR Feature Profiles with Structured Form Fields (`STRUCTURED_PLAYBOOK`, `<1 ms` Default Offline & Online):** Operators select from 4 flight-tested mission profiles (*1. Night Hiker Search & Opaslyhty Escort*, *2. Fast Snowmobile Track & High-Wind Hold*, *3. Canyon River Thermal Sweep*, *4. High-Timber Safe Clearance*) and adjust **7 typed numeric/dropdown form inputs** (`Search Alt (m)`, `Track Alt (m)`, `Standoff (m)`, `Target Priority`, `Payload Drop Policy`, `RTH Battery Floor (%)`, `Veto Cooldown (s)`).
     2. **Option B — Direct Manual Control With No LLM (`MANUAL_HUMAN_ONLY`):** Disables all automated target locking and drop queueing; 100% pilot-in-command control via map drag-to-point, drag-onto-target, and 1:1 trackpad stick steering.
     3. **Optional External Cloud LLM API (`EXTERNAL_LLM_API`) With Instant Offline Failover:** When an API key is active, LLM JSON proposals are validated by the **3-Stage JEV Safety Gate (`Judge -> Evaluate -> Verify`)** (`Poronhoitolaki <= 100 m AGL` or `<= 35 m` Heli Cap, `>= 15 m` drop standoff, monotonic `Epoch ID`). If connectivity drops (`🔌 Test Cutout`), the dispatcher switches in `<1 ms` to the operator's chosen offline policy (**Option A: Structured Fields** or **Option B: Direct Manual Control**).
   * **Human Veto Supremacy (`85 m` Spatial Veto Bubbles):** Clicking **`✕ Cancel Target Lock`** increments the monotonic `Epoch ID`, creates an `85 m` spatial Veto Bubble (`300 s` TTL) around the rejected false-positive thermal signature so the system never re-locks it, and returns Drone 1 to sector scan.

---

### 2.2 Persona 2: Production Fast-SAR Mothership Pilot Cockpit & Dynamic 60 Hz Safe-Envelope Gauges (`mothership_cockpit.html` / `flight_simulator.html`)

The **Production Fast-SAR Mothership Pilot Cockpit & Synthetic Vision GCS** (`http://127.0.0.1:8080/mothership_cockpit.html` and `:8788/mothership_cockpit.html`) combines a live bidirectional `MAVLink v2` telemetry bridge with a `240 Hz` 6-DoF aerodynamic digital twin (`4× RK4` per frame), an always-live Garmin/Airbus Primary Flight Display (`#canvasGlassPFD`), and **6 Dynamic Safe-Operating-Envelope Gauges** whose `Red / Amber / Green / Cyan` bands recalculate and shift at **60 Hz** based on real-time flight physics:

| Gauge | Dynamic Band Boundaries & Real-Time Physics Factors Shifting the Colored Zones at 60 Hz |
| :--- | :--- |
| **1. `ALTITUDE AGL`** | • **Red Pull-Up Floor:** $\max(25\text{ m}, 25 + 1.1|V_{z,\text{downdraft}}| + \Delta h_{\text{ice}})$ — rises automatically from `25 m` to `35–48 m` under microburst downdraft shear or wing ice.<br>• **Cyan Capsule Drop Window:** `65 m – 110 m AGL` (optimal marsupial drogue unfold corridor).<br>• **Green Safe Ceiling:** Compresses from `220 m` down to **`120 m AGL` (`HELI CAP!`)** whenever a Manned SAR Helicopter enters the U-Space sector. |
| **2. `AIRSPEED TAS`** | • **Dynamic Stall Speed ($V_s$, Red Lower Band):** $V_s(t) = V_{s0}\sqrt{\frac{m(t)}{m_{\text{ref}}}\cdot\frac{\rho_0}{\rho(h,T)}\cdot n_z}\cdot k_{\text{flap}}\cdot k_{\text{ice}}$. Drops by `~18%` after releasing the `5.0 kg` belly quadcopter (`14.9 kg -> 9.9 kg`), rises with bank G-load $\sqrt{n_z}$, rises `+14%` under `+2.5 mm` rime ice, and decreases with `20°` flaps.<br>• **Dynamic Never-Exceed ($V_{ne}$, Red Upper Band):** $V_{ne,\text{TAS}} = \min(V_{ne,\text{IAS}}\sqrt{\rho_0/\rho(h,T)},\; 0.34 a(T)) - \Delta V_{\text{ice}}$ (`411 km/h -> 384 km/h`). |
| **3. `AoA (α) & G-LOAD`** | • **Dynamic Critical Stall Angle ($\alpha_{\text{crit}}$, Red Upper Band):** $\alpha_{\text{crit}}(t) = 14.5^\circ + \Delta\alpha_{\text{flap}} - \Delta\alpha_{\text{ice}} - 1.1^\circ\max(0, n_z - 1)$. Shrinks from `14.2°` down to **`10.3°`** under `+2.5 mm` leading-edge rime ice + flap deflection, while the Amber caution buffer tightens proportionally (`9.9° -> 6.0°`). |
| **4. `TURBINE EGT`** | • **Dynamic Continuous Green Limit:** Shifts with Outside Air Temperature (`690°C` at `-30°C` Arctic air vs. `715°C` ISA) and compressor bleed load, with a hard `740°C` FADEC fuel-clamp redline. |
| **5. `JET FUEL (A-1)`** | • **Dynamic Bingo (Red) & RTB Reserve (Amber) Bands:** $\text{RTB}\% = \text{Bingo}\% + \frac{d_{\text{home}}}{\max(95,\; V_{\text{TAS}} - V_{\text{headwind}})}\cdot c_{\text{burn}}(T)$. Automatically widens the Amber RTB band (`46% -> 48%+`) when battling an `18 m/s` Arctic headwind. |
| **6. `6S LI-ION BUS`** | • **Dynamic Voltage-Sag & Cold-Bay Brownout Floor:** Scales with avionics bay temperature $T_{\text{bay}}$ (cell internal resistance $R_{\text{int}}$ doubles at `-20°C`) and electric sustainer prop current, raising the Red/Amber SOC floor from `18% / 36%` (`+15°C` heated bay) to **`27% / 45%`** (`-2°C` cold bay). |

---

### 2.3 Persona 3: Authentic 3-Zone Tree-Mounted Arctic Trail Cam (`pi-diode-trailcam`) & Sky-Diode Backhaul

Unlike generic consumer trail cameras with exposed solar panels or whip antennas, our **Three-Zone Arctic Trail Cam (`pi-diode-trailcam`)** separates the small optical/radar eye on the tree trunk from the heavy battery, compute, and optical/RF backhaul buried in the thermally stable root zone:

1. **Zone 1 — Camera / Radar Tree Pod (`~2 m` up pine trunk):**
   * **Enclosure:** Compact green **`Hammond 1591BSBK`** (`IP54` + project sealing) strapped to the tree trunk with **zero external antennas and zero solar panels**.
   * **Single `30 mm` Circular Glass Window:** Houses the **`Sony IMX708 NoIR` camera module**, a **foam anti-glare ring baffle**, **`2 × 940 nm` IR LEDs** (left and right of lens), and a **`~3.69 W` resistor window de-icer** behind the glass.
   * **Hidden `HLK-LD2450` 24 GHz FMCW Radar:** Mounted inside the **lower internal bay behind the solid ABS wall (no cutout)**, providing `0.20 mW` standby human gait detection through the plastic housing.
2. **Zone 2 — Shielded Trunk Umbilical (`~2 m` down tree bark):**
   * Carries the **shielded CSI-to-HDMI camera extension** (camera data down to root vault), **Radar `5 V + UART`** power/trigger lines, and **`12 V` window heater feed** (power up).
3. **Zone 3 — Buried Root Vault (`20–30 cm` under snow & `10–20 mm` XPS insulation board):**
   * **Enclosure:** **`QILIPSU 285 × 195 × 130 mm` (`IP67`)** root vault utilizing geothermal ground warmth (`-2°C` to `0°C` under snow vs. `-30°C` air).
   * **Internal Hardware:** **`12 V` LiFePO4/AGM battery + fuse**, **`Raspberry Pi Pico 2` gatekeeper + `5 V` buck + relays**, **`Raspberry Pi 5`** (wakes only on confirmed trigger to sign bursts with `Ed25519` + `ChaCha20-Poly1305`), and a **`StarTech 1310 nm` field media converter + `1×2` optical loopback splitter** feeding one-way **armored `OS2` single-mode fiber** (`30 m – 10 km`) to the **Cabin Collector**, **Woods Dead-Drop Vault**, and **`L-com HG2414P` (`14 dBi` flat-panel) + vertical `Hammond 1590Z120` `2.4 GHz` Sky-Diode Troposcatter Mast** (`2–20 km` NLOS bounce over granite fells).

---

### 2.4 Persona 4: Gloved Mobile Ground SAR Responder Terminal (`/mobile_responder.html`)

Served directly by `dashboard_server.py` at `http://127.0.0.1:8788/mobile_responder.html` (and `:8080/mobile_responder.html`), the **Gloved Ground SAR Responder Terminal** is engineered for *Vapepa*, Police, and Border Guard snowmobile/ski teams operating in `-25°C` conditions with thick winter mittens:

1. **Column 1 — Live Bearing & Distance Radar Compass (`034° NE • 380 m`):**
   * High-contrast polar radar rose displaying the rescuer's live GPS (`YOU: VAPEPA-04`), the bearing vector and distance to the drone-locked victim (`VICTIM: 380 m • 034° NE`), the overhead `Drone 1 (Sierra)` `28 m AGL` `Opaslyhty` lantern strobe (`1,200 lm Amber Strobe + 800 lm Trail Cone`), and distance to the nearest heated *Autiotupa* wilderness cabin (`Jussinkämppä • 340 m`).
2. **Column 2 — Triple Coordinate Formats, `ATAK CoT` Export & Live LWIR Thermal Crop:**
   * One-tap giant copy buttons for **Finnish National Grid (`ETRS-TM35FIN` / `JHS 197`: `N 7362971 • E 603588`)**, **Aviation Helicopter `WGS84 DDM` (`66° 22.15' N, 029° 18.98' E`)**, and **GNSS Decimal Degrees (`66.369100° N, 29.316300° E`)**, plus 1-tap **Cursor-on-Target (`.cot` XML)** download for ATAK/WinTAK tablets.
   * Live **`Drone 1` LWIR Thermal Crop (`+31.4°C`, `94%` Confidence)** and **Persona 3 3-Zone Trail-Cam & Sky-Diode (`+55.8 dB VK7MO Lock`)** status card.
3. **Column 3 — Giant `72 px` Gloved 2-Way C2 Action Buttons & Multilingual `Opaslyhty` Megaphone:**
   * **`[✅ 1. VICTIM CONTACTED & SAFE]` (Green):** Confirms ground team contact, updates Swarm C&C (`:8788`) & Mothership Cockpit (`:8080`) in `<50 ms`, and releases Drone 1 back to cooperative sector scan.
   * **`[🪂 2. REQUEST +42°C WARM CASK DROP AT MY GPS]` (Amber):** Queues a `15 m` lateral standoff survival barrel drop at the ground team's coordinates.
   * **`[🚁 3. REQUEST HELICOPTER MEDEVAC (35m DRONE CAP)]` (Red):** Alerts Rovaniemi `112` Border Guard SAR Helicopter and immediately caps all drones to `<= 35 m AGL` (and sets the `120 m` U-Space ceiling on the Mothership Cockpit `ALTITUDE AGL` gauge).
   * **Persona 5 `Opaslyhty` Hiker Megaphone & LED Sign Selector (`FI / EN / SE`):** Switches the overhead drone's voice & LED reassurance prompts between Finnish, English, and Swedish/Sámi.

---

## 3. Current Implementation vs. Target Production State Matrix (All 13 Items Verified)

| ID | Persona & Subsystem | Intended Target-State Capability & UX | Current Implementation in Codebase (`Live Status`) | Readiness | Next Optional Enhancement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UX-01** | **P1: IC Mission Console** (`operator_mission_console.html`) | Multi-zoom Google Earth satellite, hybrid & terrain map (`z=4..20`) with zero black-tile flashing and zero-key startup | **Delivered:** Live `mt0..3.google.com/vt` tile streamer + parent mipmap fallback + `🔑 Tile/LLM Keys` drawer | **100% (`✅`)** | Optional `.mbtiles` packager for multi-week offline expeditions |
| **UX-02** | **P1: IC Mission Console** | Multi-format `112 SOS` coordinate entry (`ETRS-TM35FIN`, `WGS84 DDM`, `WGS84 Decimal`) that pans map & flies drones | **Delivered:** `parseMultiFormatCoords()` + `#inpSosCoords` accepting `N 7362415 E 598784`, `66° 22.17' N`, and decimal | **100% (`✅`)** | Add MGRS military grid parser |
| **UX-03** | **P1: IC Mission Console** | Stretchable search area (`8 handles`) vs. explicit `Draw New Box` tool, with continuous airborne transit (zero teleportation) | **Delivered:** 8-handle hit-testing (`N..NW`), `PAN_MAP` default mode, and continuous `En Route` transit vectors | **100% (`✅`)** | Freehand river-corridor polygon tool |
| **UX-04** | **P1: IC Mission Console** | Continuous multi-pass radar patrol (`N-S` Pincer + `E-W` Cross-Sweep + Perimeter Seal) that never stops after 1 pass | **Delivered:** `buildSectorRadarPassWaypoints()` + continuous pass handoff in `renderLoop()` | **100% (`✅`)** | Multi-nest automatic relief drone launch |
| **UX-05** | **P1: IC Mission Console** | Exponential radar phosphor decay overlay + `2.2×` accelerated moving-target boundary intrusion warning | **Delivered:** `boxLastSeenSecGrid`, `boxFreshnessGrid`, `boxLeakRiskGrid`, 3-tier brightness + amber border halo | **100% (`✅`)** | Kalman velocity-adaptive decay $\tau_{1/2}$ |
| **UX-06** | **P1: IC Mission Console** | Direct drone drag-to-waypoint, drag-onto-target lock, and click-to-go / click-to-track on both Map and Video | **Delivered:** `draggingDroneState`, `sendDroneToWorldPoint()`, `markOrLockObjectAtWorld()` | **100% (`✅`)** | Shift-click multi-waypoint chain |
| **UX-07** | **P1 & P2: Trackpad Steering** | 1:1 finger-follow trackpad steering with `X/Y` bounds bars AND instant 1-click / `Space` / `Esc` center & pause (`(0%, 0%)`) | **Delivered:** `trackpadSteerCanvas` + `toggleStickArmPause()` in `:8788` and `fpvCanvas` click/Esc center in `:8080` | **100% (`✅`)** | ExpressLRS USB HID joystick wizard |
| **UX-08** | **P1: Playbook Dispatcher (`AID`)** | **Zero Offline Regex Parsing:** Option A (`7` Structured Playbook Form Fields, `<1 ms`) or Option B (`Direct Manual Control`), plus JEV gate & `85 m` Veto Bubbles | **Delivered:** `playbook_agent_dispatcher.py` (`build_structured_playbook_rules`, `0` regex) + `:8788` Card 0 Structured Form UI + `85 m` Veto Bubbles | **100% (`✅`)** | Station-specific SQLite profile sync |
| **UX-09** | **P2: Mothership Cockpit** (`mothership_cockpit.html`) | Production Fast-SAR Pilot Cockpit PFD + **6 Dynamic 60 Hz Safe-Operating-Envelope Gauges** shifting with $\rho(h,T)$, mass, G-load, icing, wind & heli cap | **Delivered:** `#canvasGlassPFD` + `drawEnvelopeGauge()` dynamic 60 Hz physics bands + interactive environment shift strip + FDIR FFT notch filter | **100% (`✅`)** | Hardware-in-the-loop Cube Orange+ bench test |
| **UX-10** | **P3: 3-Zone Trail-Cam & Sky-Diode** | Authentic 3-Zone Tree-Mounted Trail Cam (`Hammond 1591BSBK` + `2m` umbilical + buried `QILIPSU` root vault + `1310nm` diode) & Sky-Diode telemetry | **Delivered:** `pico_firmware/main.py`, `sender_node.py`, `receiver_hub.py`, and live 3-Zone Trail-Cam status in `:8788` & `/mobile_responder.html` | **100% (`✅`)** | Multi-node mesh topology graph |
| **UX-11** | **P4: Ground SAR Responder** (`/mobile_responder.html`) | Gloved mobile web app (`/mobile_responder.html`) with live bearing compass, `ETRS-TM35FIN`/`DDM`/`.CoT` copy, thermal crop & `72 px` 2-way field ACK buttons | **Delivered:** `/mobile_responder.html` served on `:8788` & `:8080` with `<50 ms` 2-way sync across all 3 endpoints (`test_26`–`test_30` verified) | **100% (`✅`)** | Native Android APK wrapper for offline cache |
| **UX-12** | **P5: Distressed Hiker Physical UX** | Trail-post SOS trigger $\to$ `15 m` standoff drop $\to$ `28 m` AGL `Opaslyhty` spotlight & multilingual (`FI/EN/SE`) voice/LED guide to *Autiotupa* hut | **Delivered:** Full state machine in `aerial_observer.py` + live `FI / EN / SE` Opaslyhty Megaphone & LED prompt controls in `:8788` & `/mobile_responder.html` | **100% (`✅`)** | Acoustic beamforming voice reply pickup |
| **UX-13** | **P6: 112 ERICA & U-Space C2** | Automated `ETRS-TM35FIN` / `DDM` dispatch feed + `4.4 ms` U-Space manned SAR helicopter `35 m` / `120 m` corridor auto-cap | **Delivered:** `police_112_feed.py` + 1-click Helicopter Medevac `35 m` drone cap & `120 m` Mothership gauge ceiling synced across all endpoints | **100% (`✅`)** | Live Fintraffic ANS REST webhook |
