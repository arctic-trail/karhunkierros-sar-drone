# Complete SAR System Operator UX, Multi-Role Endpoint Architecture & Current-vs.-Target Implementation Mapping

**End-to-End Use Cases, User Experience Workflows Across All 6 Operational Personas & Endpoint Applications, and Production Readiness Gap Analysis (`Karhunkierros SAR Swarm` + `Arctic Fast-SAR Mothership Jet` + `Trail-Cam / Sky-Diode Sensor Mesh`)**

---

## 1. Executive Summary & Complete 6-Persona Ecosystem

In a life-or-death wilderness Search and Rescue (SAR) operation under sub-arctic conditions (`-25°C` to `-30°C` *Kaamos* polar night, `12–18 m/s` canyon winds, roadless boreal terrain), no single screen or single operator exists in isolation. The complete system serves **six distinct user personas**, each interacting with a purpose-built **Endpoint Application or Physical UX Surface** connected across a resilient multi-tier communication fabric (`MAVLink v2 UDP :14550`, `868 MHz LoRa TDMA Mesh`, `2.4 GHz NLOS Sky-Diode Troposcatter`, and `Cursor-on-Target / 112 ERICA JSON`):

| # | User Persona / Role | Endpoint Application / UX Surface | Primary Operational Responsibility | Current Implementation Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **SAR Incident Commander & Swarm Mission Dispatcher (`IC / C2 Operator`)** | **Google Earth Cooperative SAR Mission Console** (`operator_mission_console.html` on `:8788`) | Defines & stretches search boxes, supervises 4-drone continuous radar sweeps + decaying coverage shroud, compiles natural-language AI playbooks (`AID`), overrides/vetoes locks, and authorizes `15 m` standoff rescue drops. | **92% Implemented** (Live 3-pane Google Earth C&C, continuous `N↕S`+`E↔W` radar sweep, decay overlay, 1:1 trackpad stick, AID compiler, MAVLink v2 framing) |
| **2** | **Fast-SAR Mothership Jet & FPV Remote Pilot (`UAS Pilot-in-Command`)** | **6-DoF Flight Simulator, Glass Cockpit PFD & FPV Pilot Workstation** (`flight_simulator.html` on `:8080` + `:8765` HID bridge) | Flies the `259 km/h` (`396 km/h` max) hybrid turbojet/electric mothership through wind shear & icing, monitors the Garmin/Airbus-style PFD & 6 color-coded operating envelope gauges, and executes the `85 m` AGL mid-air quadcopter drop. | **94% Implemented** (240 Hz 6-DoF RK4 physics, live Glass PFD + HSI, 6 operating envelope bars, 3 flight control laws, 1:1 trackpad bounds + 1-click safe center) |
| **3** | **Field Sensor & Sky-Diode Relay Technician (`Perimeter / Mesh Tech`)** | **Collector Hub & Ground-Sensor Alert Triage Service** (`receiver_hub.py`, `sender_node.py`, `pico_firmware/main.py`) | Deploys & monitors `0.20 mW` standby trail-cam nodes (`HLK-LD2450` 24 GHz radar, `QMC5883L` mag, geophone, `MLX90640` thermal) and `2–20 km` NLOS Sky-Diode troposcatter relays; verifies `Ed25519` cryptographic alerts. | **88% Implemented** (Full Pico 2 firmware, `Ed25519` + `ChaCha20` framing, 2-camera triangulation, dead-drop vault; needs unified live web health tab in `:8788`) |
| **4** | **Ground SAR Foot-Patrol / Snowmobile First Responder (`Field Rescue Team`)** | **Mobile / Gloved Field Responder Companion App** (`ATAK CoT` / Mobile Web Offline Map + Handheld `PELASTUS-NUOLI` OLED Sight) | Navigates on skis/snowmobile to the live drone-tracked victim coordinates, views thermal target thumbnails, coordinates with the overhead `Opaslyhty` lantern drone, and logs victim medical triage on contact. | **45% Implemented** (Backend generates `ETRS-TM35FIN` & `DDM` coordinates + JSON alert payloads; dedicated mobile-responsive gloved responder view & 2-way field ACK buttons are Target State P0) |
| **5** | **Distressed Hiker / Survivor in the Wilderness (`Zero-App Rescue Subject`)** | **Physical Wilderness SOS Post + Drone-Delivered `Opaslyhty` Audio/Visual & Warm Cask UX** | Presses frost-proof physical SOS button on trail post (or `112 Suomi` / inReach); receives `15 m` lateral standoff drop of heated electrolyte cask + thermal blanket; follows `28 m` AGL golden spotlight cone to nearest *Autiotupa* hut. | **85% Implemented** (Physical SOS trigger packet, `15 m` hard safety bubble, `Opaslyhty` `28 m` escort trajectory & audio/LED state machine verified in `test_14`–`test_18`) |
| **6** | **112 ERICA Dispatcher, Police C2 & Airspace Coordinator (`Agency Interop`)** | **112 Police/SAR Feed & Open U-Space Track Fusion Bridge** (`police_112_feed.py` + `FIN-LAB-01` `4.4 ms` Track Fusion) | Receives automated `ETRS-TM35FIN` / `WGS84 DDM` incident feeds, coordinates manned SAR helicopter (`Rajavartiolaitos`) airspace deconfliction (`Poronhoitolaki` `100 m` ceiling), and audits GDPR `48h` auto-purge logs. | **80% Implemented** (`police_112_feed.py` & `4.4 ms` U-Space track fusion engine verified; live manned-helicopter ADS-B/FLARM corridor auto-hold in `:8788` is Target State P1) |

---

## 2. Deep-Dive Use Cases & Endpoint UX Across All 6 Personas

### 2.1 Persona 1: SAR Incident Commander & Swarm Mission Dispatcher (`operator_mission_console.html`)

The **Google Earth Cooperative SAR Mission Console** (`http://127.0.0.1:8788/operator_mission_console.html`) is the primary mission command-and-control (C2) workstation. It is organized into a **resizable, closable, and maximizable 4-zone workspace**:

1. **Top Global Command Bar:**
   * **Operational Sector Preset & Arbitrary `112 SOS` Coordinate Intake:** Operators can either select a pre-surveyed wilderness sector (*Oulanka Canyon / Kiutaköngäs*, *Ruka Fell / Valtavaara*, *Kitkajoki / Jyrävä*, *Hautajärvi North Boundary*) or type/paste any real-world GPS coordinate pair (`Lat, Lon`, e.g., `66.3695, 29.3155`) into the **`112 SOS`** input box and click **`📍 Go`**. This immediately pans the Google Earth satellite engine to the emergency location, re-centers the search box, and tasks all airborne drones to fly continuously from their current positions to the new distress coordinates.
   * **Workspace Layout Pills & Simulation Speed Controls:** One-click toggles for **View 1 (Google Earth Map)**, **View 2 (Drone Video)**, **Terrain Elevation Profile**, **View 3 (Controls Sidebar)**, and **`↺ Reset Views`**, plus `1× / 2× / 4×` simulation/replay speed.

2. **View 1 — Multi-Zoom Google Earth C&C Map (`z=4..20`, Zero-API-Key Out-of-the-Box):**
   * **Live Planetary Satellite & Terrain Streaming:** Streams real Google Earth Hybrid (`lyrs=y`), Pure Satellite (`lyrs=s`), and Terrain (`lyrs=p`) XYZ raster tiles directly from `mt0..3.google.com/vt` with an automatic parent-tile mipmap fallback so zooming (`z=4` continental down to `z=20` meter-level) never flashes black frames. Works with **zero API key required** out-of-the-box, while offering a **`🔑 Tile/LLM Keys`** drawer for optional enterprise Google Maps Platform keys (`AIza...`) or LLM keys (`sk-...`).
   * **Interactive Search Area Stretching vs. Intentional Redraw:**
     * By default, the map operates in **`🖐️ Pan / Drag Drone / Stretch Box`** mode. The active search box displays **8 grab handles (`◻`)** on all 4 corners (`NW, NE, SW, SE`) and all 4 edges (`N, S, E, W`). Dragging any handle stretches the search area in real time without resetting explored history.
     * Redrawing a search box from scratch requires explicitly clicking **`📐 Draw New Box: ON`**, preventing accidental click-drags from wiping out an active search.
     * Whenever a box is stretched or redrawn, **drones never teleport**—they fly smoothly along a visible **`✈️ En Route (Xm)`** transit vector from their previous airborne position to the nearest entry corner of their updated sector.
   * **Continuous Multi-Pass Radar Patrol & Moving-Target Counter-Infiltration:**
     * Drones **never stop after a single pass**. As soon as a drone finishes Pass #1 (`N↕S Pincer #1`), it automatically increments its pass counter and launches Pass #2 (`E↔W Cross #2`, an orthogonal side-to-side sweep starting from the corner closest to the drone's current position), alternating continuously like a rotating radar.
     * Operators can switch between 4 cooperative patrol geometries: **`🔄 Pincer N↕S + E↔W Cross (Anti-Leak)`**, **`🛡️ Perimeter Seal -> Interior Sweep`**, **`↕️ Continuous Reciprocal N↕S Strips`**, and **`🧱 Synchronized Line-Abreast Wall`**.
   * **Exponential Radar Phosphor Decay & Moving-Target Boundary Intrusion Halo:**
     * Because a lost hiker ($1.5\text{ m/s}$) or snowmobile ($10\text{–}20\text{ m/s}$) can move from an unscanned area into an already-scanned area after a drone passes, scanned cells **exponentially decay (darken)** over time ($F(t) = 2^{-\Delta t / \tau_{1/2}}$, with selectable half-lives of `32s Fast`, `55s Standard`, `120s Slow`, or `Static`).
     * Scanned cells that border **unscanned or expired territory** decay **`2.2×` faster** and render a dashed **Amber Moving-Target Intrusion Risk border** until refreshed by a live camera pass.
   * **Direct Drone Drag-to-Point & Drag-to-Target:** Operators can grab any drone icon directly on the map and drag it to any terrain coordinate (to fly there immediately) or drop it onto a detected person/vehicle (to lock and track that target), or use the **`📍 Send Drone to Point`** and **`🎯 Mark Object to Track`** toolbar tools on either the Map or Drone Video.

3. **View 2 — Synchronized Live EO + LWIR Thermal Drone Video & Camera Switcher:**
   * **5-Mode Camera Bar:** Instant switching between **Drone 1 (Sierra)**, **Drone 2 (Tango)**, **Drone 3 (Uniform)**, **Drone 4 (Victor)**, and an **All-4 (`2×2` Quad Grid)** view where clicking any quadrant expands that drone.
   * **Map $\leftrightarrow$ Video Footprint Synchronization:** Whichever drone is selected in View 2 is highlighted on the View 1 map with a **bold white sensor circle and inner rectangular camera footprint box (`VIEW 2 FRAME`)**. Moving the cursor inside View 2 projects a live cyan reticle (`VIDEO CURSOR`) at the exact corresponding ground coordinate on View 1.
   * **Optical/Thermal Sensor Controls:** `1.0×` to `8.0×` digital/optical zoom (`+`/`-` buttons or mouse wheel) and 4 sensor palettes (`EO + Thermal Fusion`, `FLIR White-Hot`, `FLIR Black-Hot`, and `Night Vision Green`).

4. **View 3 — Mission Controls, Trackpad Steering, AI Playbook Dispatcher (`AID`) & MAVLink v2 Bridge:**
   * **Card 0 (`🤖 AI Playbook Dispatcher — AID`):** Natural-language SAR operations playbook editor & deterministic compiler (`<1 ms` offline execution with `Judge -> Evaluate -> Verify` safety gates). Supports 4 execution modes (`Auto: Offline Playbook`, `Auto: LLM + JEV Gate`, `Advisory Only`, `AID OFF: Manual`), a 1-click **`🔌 Test No-API Cutout`** button, and **Human Veto Supremacy** (canceling a target lock creates a spatial `85 m` veto bubble so the AI never fights the human operator).
   * **Card 0B (`🕹️ Trackpad & Stick Steering — X/Y Bounds`):** Real-time 2D stick bounds pad (`[-100%..+100%]` on both X and Y axes with live dashed projection bars). Includes **1-Click / `Space` / `Esc` Instant Center & Pause (`(0%, 0%)`)** so the operator can stop steering and move their cursor out of the box without pulling the drone to one side.
   * **Card 1 (`Continuous Radar Patrol & Decay`):** Patrol pattern selector, scan decay half-life selector (`32s / 55s / 120s / Static`), AGL altitude/swath selector (`40m / 55m / 85m`), live `Fresh vs. Fading / Leak Risk` readout, and `QGC WPL 110` `.waypoints` export.
   * **Card 2 & Card 3 (`Target Tracking Assignment` & `Cancelable 15m Payload Drop`):** 1-click target lock cancelation (`✕ Cancel Target Lock` on both the map banner and sidebar) and a two-step **Cancelable Payload Drop workflow** (`Queue Drop 15m from Target` $\to$ inspect orange parachute pin on map $\to$ `✕ Cancel Pending Drop` or `⚡ Confirm & Release Now`).
   * **Card 4 (`Field Hardware & MAVLink v2 Bridge`):** Live `MAVLink v2` (`0xFD` magic, `CRC-16/MCRF4XX`) hex packet telemetry log, `COMMAND_LONG (#76)` / `SET_POSITION_TARGET_GLOBAL_INT (#86)` / `MISSION_ITEM_INT (#73)` dispatch, and WebRTC/UVC USB hardware video capture (`navigator.mediaDevices.getUserMedia`).

---

### 2.2 Persona 2: Fixed-Wing Fast-SAR Mothership & Marsupial Pilot (`flight_simulator.html`)

When an SOS call arrives `35–113 km` away in deep wilderness where a quadcopter (`25 m/s` max speed, `35 min` cold battery limit) cannot reach against an `18 m/s` Arctic headwind, the **Fast-SAR Hybrid Mothership Jet (`259 km/h` cruise, `396 km/h` dash)** launches first, carrying the folded rescue quadcopter warm (`+15°C`) inside its internal ventral belly bay. The remote pilot operates **`flight_simulator.html`** (`http://127.0.0.1:8080/flight_simulator.html`):

1. **Left 3D / CFD / FPV Viewport (`#canvasAircraft3D`):**
   * Supports 10 camera and aerodynamic modes: **`🕹️ FPV Cockpit`**, **`📟 Glass PFD`**, **`🎯 SAR Operator OSD`**, **`🌗 FPV + 3D Split`**, **`3D Iso`**, **`2D Airfoil CFD`**, **`Split 3D+2D`**, **`Side`**, **`Top`**, and **`Front`**.
   * Runs a **240 Hz 12-state Newton-Euler 6-DoF rigid-body flight physics engine** (`4× RK4` sub-steps per `60 FPS` frame) modeling nonlinear stall/post-stall buffet, asymmetric spin departure, `1.35 s` micro-turbojet spool lag, leading-edge ice accretion, microburst wind shear, and 3 flight control laws:
     * **`[1] Direct Law (Raw Servos)`:** Unfiltered stick-to-ruddervator/flaperon mixing for manual pilot proficiency & upset recovery training.
     * **`[2] Alternate Law (SAS Gyro Damper)`:** Pitch/roll rate damping (`p, q, r`).
     * **`[3] Normal Law (AI-Assisted RC Envelope Protection)`:** Airbus-style bank angle limit (`±55°`), AoA stall floor protection (`α ≤ 11.5°`), automatic pitch trim, and wings-level auto-capture when hands-off.
2. **Right-Sidebar Primary Flight Instruments (`#canvasGlassPFD`):**
   * Always-live **Garmin G1000 / Airbus Primary Flight Display** showing scrolling **Indicated Airspeed (IAS) tape** with red stall barber-pole, **Artificial Horizon (ADI)** with sky/ground shading, pitch ladder (`±20°`), bank roll pointer, yellow aircraft reference symbol, green **Flight Path Vector (FPV)**, **Altitude AGL & VSI tape** with `25 m` red terrain floor, and a **360° Rotating Horizontal Situation Indicator (HSI)** with wind vector and waypoint bug.
3. **Six Color-Coded Safe Operating Envelope Gauges:**
   * Replace legacy static text readouts with tri-color (`Red Danger` / `Amber Caution` / `Green Safe` / `White Flap Arc`) operating envelope bars, live needle pointers, limit tick labels, and plain-English margin callouts:
     1. **`ALTITUDE AGL` (`0–280 m`):** `25 m` hard tree/terrain floor, `65 m` drop window, and time-to-impact pull-up alert.
     2. **`AIRSPEED TAS` (`60–420 km/h`):** Live stall speed $V_s$ (`94–105 km/h`), white flap arc (`94–185 km/h`), safe cruise (`131–330 km/h`), and red $V_{ne}$ (`396 km/h`).
     3. **`AoA (α) & G-LOAD` (`-6°..+18°`):** Live stall margin (`+14.2°` vs. $\alpha_{\text{stall}} = 14.5^\circ$) and structural G-load (`-1.5G..+4.0G`).
     4. **`TURBINE EGT & RPM` (`200–950°C`):** FADEC kerostart relight status, continuous thrust (`0–200 N`), and `850°C` Inconel turbine limit.
     5. **`FUEL + UAT HOPPER` (`0–100%`):** Main tank kg, Affine-Breguet headwind range reserve, and `180 mL` anti-air-bubble UAT status.
     6. **`6S BATTERY & BAY TEMP` (`0–100%`):** Li-Ion SOC, `24.4 V` DC bus, and `-30°C` PTC heated avionics bay thermal margin (`+15°C`).

---

### 2.3 Personas 3, 4, 5 & 6: Field Sensor Tech, Mobile Ground SAR Team, Distressed Survivor & 112/U-Space Authorities

1. **Persona 3 — Field Sensor & Sky-Diode Relay Technician (`sender_node.py` + `receiver_hub.py` + `pico_firmware`):**
   * Manages unattended wilderness trail posts (`0.20 mW` sleep power via `TPL5110` timer + `RP2040` gatekeeper) that wake only when dual-stage physical triggers confirm a target (`24 GHz HLK-LD2450` human gait or `QMC5883L` magnetic vehicle signature + `BME280` frost-suppression gate).
   * Captures `OV5647` / `MLX90640` bursts, signs every frame on-device with `Ed25519` (`PyNaCl`) + `ChaCha20-Poly1305`, and transmits across `2–20 km` non-line-of-sight granite ridges via the `2.4 GHz` **Sky-Diode Troposcatter/Diffraction Relay** (`SE2576L` 1W PA $\to$ `L-com HG2414P` 14 dBi patch) or `868 MHz` LoRa TDMA mesh into `receiver_hub.py`.
2. **Persona 4 — Ground SAR Foot-Patrol / Snowmobile First Responder:**
   * Needs a **gloved, high-contrast mobile tactical view** (`ATAK CoT` or mobile web endpoint `/mobile_responder.html`) showing:
     * Own GPS position vs. the lost hiker's live drone-tracked coordinates (`ETRS-TM35FIN` & distance/bearing arrow).
     * Live thermal thumbnail cropped from the overhead drone or trail camera.
     * Overhead `Opaslyhty` drone status (`"Guiding hiker 240m NW toward Oulanka Hut at 1.3 m/s"`).
     * Three giant glove-friendly action buttons: **`✅ Victim Reached (Safe)`**, **`🚑 Request Helicopter Medevac`**, and **`🪂 Request Warm Cask Drop Here`**.
3. **Persona 5 — Distressed Hiker / Survivor (Zero-App Physical UX):**
   * A hypothermic hiker with a dead or frozen phone battery cannot install an app or scan a QR code. Their UX is **100% physical and sensory**:
     * **Step 1 (Distress Trigger):** Press the recessed, frost-proof red piezo SOS button on a Karhunkierros trail post (or trigger `112 Suomi`).
     * **Step 2 (Safe Standoff Arrival & Warm Cask Delivery):** The `RAL 2005` orange drone arrives overhead, halts outside a **hard-coded `15 m` lateral safety radius**, sounds a calm Finnish/English/Sámi voice announcement, and releases the insulated oak/EPP survival barrel (`+40°C` electrolyte drink + thermal blanket + chemical hand-warmers) onto clear snow `15 m` away before climbing back to `50 m` AGL.
     * **Step 3 (`Opaslyhty` Aerial Lantern Escort):** The drone flies at `28 m` AGL (just above the `18 m` spruce canopy), projecting a bright warm golden LED spotlight cone onto the snowy trail `15 m` ahead of the hiker, pausing whenever the hiker rests, and leading them step-by-step to the nearest heated *Autiotupa* wilderness cabin.
4. **Persona 6 — 112 ERICA Dispatch, Police C2 & Airspace U-Space Coordinator:**
   * Receives standardized JSON/CoT packets from [`police_112_feed.py`](../collector_hub/police_112_feed.py) containing dual coordinate systems: **Finnish National Grid `ETRS-TM35FIN` (`N, E` meters)** for ground police/Vapepa units and **Aviation `WGS84 DDM` (`DD° MM.MM'`)** for *Rajavartiolaitos* (Border Guard) SAR helicopters.
   * Integrates with the **`FIN-LAB-01` Open U-Space Track Fusion Engine (`4.4 ms` latency)** to enforce `Poronhoitolaki` (`100 m` AGL ceiling) and automatically command drones to descend/hold when a manned rescue helicopter enters the canyon sector.

---

## 3. Current Implementation vs. Target Production State Matrix

The table below maps **every intended capability across all 6 personas** against the **exact current implementation in the repository today** and defines the remaining work to reach **100% field-ready production**:

| ID | Persona & Subsystem | Intended Target-State Capability & UX | Current Implementation in Codebase (`Live Status`) | Readiness | Remaining Gap to 100% Target State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UX-01** | **P1: IC Mission Console** (`operator_mission_console.html`) | Multi-zoom Google Earth satellite, hybrid & terrain map (`z=4..20`) with zero black-tile flashing and zero-key startup | **Implemented:** Live `mt0..3.google.com/vt` tile streamer + parent mipmap fallback + `🔑 Tile/LLM Keys` drawer (`L1470–L1630`) | **100% (`✅`)** | Add offline local `.mbtiles` / IndexedDB disk tile cache pre-seeder for 100% air-gapped field laptops without cellular/Starlink backhaul. |
| **UX-02** | **P1: IC Mission Console** | Arbitrary `112 SOS` GPS coordinate entry (`Lat, Lon`) that pans map and flies drones from current positions | **Implemented:** Top-bar `112 SOS` input (`#inpSosCoords`) + `jumpToEmergencyCoords()` (`L3195–L3235`) | **100% (`✅`)** | Also accept direct `ETRS-TM35FIN` (`N 7362410, E 603820`) and `WGS84 DDM` (`66° 22.17' N`) paste formats in the same input box. |
| **UX-03** | **P1: IC Mission Console** | Stretchable search area (`8 handles`) vs. explicit `Draw New Box` tool, with continuous airborne transit (zero teleportation) | **Implemented:** 8-handle hit-testing (`N,S,E,W,NW,NE,SW,SE`), `PAN_MAP` default mode, and `recomputeAutoMission(false, false)` continuous transit (`L3390–L3545`) | **100% (`✅`)** | Support arbitrary rotated polygon / river-corridor search boxes in addition to axis-aligned rectangles. |
| **UX-04** | **P1: IC Mission Console** | Continuous multi-pass radar patrol (`N↕S` Pincer + `E↔W` Cross-Sweep + Perimeter Seal) that never stops after 1 pass | **Implemented:** `buildSectorRadarPassWaypoints()` + continuous pass handoff in `renderLoop()` (`L1852–L1913`, `L3995–L4045`) | **100% (`✅`)** | Auto-handover sector to relief drone when battery SOC drops below `30%` (`test_07` logic exists in Python; wire live into `:8788` UI). |
| **UX-05** | **P1: IC Mission Console** | Exponential radar phosphor decay overlay + `2.2×` accelerated moving-target boundary intrusion warning | **Implemented:** `boxLastSeenSecGrid`, `boxFreshnessGrid`, `boxLeakRiskGrid`, 3-tier satellite brightness + amber dashed boundary (`L1786–L1850`, `L4060–L4145`) | **100% (`✅`)** | Couple decay rate $\tau_{1/2}$ dynamically to the target's measured Kalman velocity vector from `aerial_observer.py`. |
| **UX-06** | **P1: IC Mission Console** | Direct drone drag-to-waypoint, drag-onto-target lock, and click-to-go / click-to-track on both Map and Video | **Implemented:** `draggingDroneState`, `sendDroneToWorldPoint()`, `markOrLockObjectAtWorld()` (`L3018–L3085`, `L3430–L3505`) | **100% (`✅`)** | Allow shift-clicking multiple waypoints to queue a custom multi-leg patrol route for a single drone. |
| **UX-07** | **P1 & P2: Trackpad Steering** | 1:1 finger-follow trackpad steering with `X/Y` axis vs. `±100%` bounds bars AND instant 1-click / `Space` / `Esc` center & pause (`(0%, 0%)`) | **Implemented:** `trackpadSteerCanvas` + `toggleStickArmPause()` in `:8788` (`L3670–L3920`) and `fpvCanvas` click/Esc center in `:8080` (`L9119–L9265`) | **100% (`✅`)** | Bind physical USB RC controller (`Mode 2` ExpressLRS USB HID joystick) calibration wizard in `:8788` console. |
| **UX-08** | **P1: AI Playbook Dispatcher (`AID`)** | Natural-language playbook editor, `<1 ms` offline AST compiler, optional LLM JEV gate, and spatial Human Veto Bubbles | **Implemented:** `playbook_agent_dispatcher.py` + `:8788` Card 0 UI + `aidState.vetoBubbles` (`L940–L1018`, `L2490–L2735`) | **100% (`✅`)** | Persist custom operator playbooks to local SQLite/JSON profiles per rescue station. |
| **UX-09** | **P2: Fast-SAR Jet Pilot (`flight_simulator.html`)** | Always-live Glass Cockpit PFD (`#canvasGlassPFD` IAS/ADI/Alt/VSI/HSI) + 6 color-coded safe operating envelope gauges | **Implemented:** Compact & full-viewport Glass PFD (`L8045–L8288`) + `drawEnvelopeGauge()` 6-bar suite (`L4775–L5255`) | **100% (`✅`)** | Add live bidirectional MAVLink telemetry binding so `flight_simulator.html` can act as a real-time digital-twin ground station for a physical ArduPlane jet. |
| **UX-10** | **P3: Field Sensor & Sky-Diode Tech** | Cryptographic trail-cam alert ingestion (`Ed25519` + `ChaCha20`), 2-camera triangulation, and Sky-Diode link health | **Partial (`88%`):** Python backend (`receiver_hub.py`, `sender_node.py`, `pico_firmware/main.py`) is 100% implemented & tested | **88% (`🟡`)** | Embed a live **"Ground Sensors & Sky-Diode Link Health"** drawer inside `operator_mission_console.html` showing node battery V, RSSI/SNR, and raw trail-cam burst photos. |
| **UX-11** | **P4: Mobile Ground SAR Responder** | Gloved smartphone/tablet web app (`/mobile_responder.html`) + `ATAK CoT` feed with victim bearing arrow & 1-tap field ACKs | **Partial (`45%`):** Backend computes `ETRS-TM35FIN` & `DDM` feeds (`police_112_feed.py`), but no dedicated mobile responder HTML view exists yet | **45% (`🔴 P0 Gap`)** | Build `/mobile_responder.html` served by `dashboard_server.py` with giant gloved buttons (`Victim Contacted`, `Medical Status`, `Request Drop Here`) synced live to View 1 map. |
| **UX-12** | **P5: Distressed Hiker Physical UX** | Trail-post SOS trigger $\to$ `15 m` standoff drop $\to$ `28 m` AGL `Opaslyhty` spotlight & voice trail guide to *Autiotupa* hut | **Implemented in Sim & Logic (`85%`):** Full state machine in `aerial_observer.py` (`test_14`–`test_18`) + live visualization in `:8788` | **85% (`🟡`)** | Add operator audio/LED message selector in `:8788` Card 2 (`Finnish / English / Sámi / Siren`) to trigger onboard megaphone & LED sign prompts. |
| **UX-13** | **P6: 112 ERICA & U-Space Deconfliction** | Automated `ETRS-TM35FIN` / `DDM` dispatch feed + `4.4 ms` U-Space manned SAR helicopter corridor auto-hold | **Partial (`80%`):** `police_112_feed.py` & `FIN-LAB-01` fusion engine verified; not yet visualized on `:8788` map | **80% (`🟡 P1 Gap`)** | Render live manned SAR helicopter (`Rajavartiolaitos` ADS-B/U-Space) intrusion cylinder on `:8788` map with 1-click **" descend All Drones to 35m Hold"**. |

---

## 4. Prioritized Engineering Roadmap to 100% Production Readiness

1. **Sprint P0 (Immediate Field-Critical UX Completion — 48 Hours):**
   * **Build Mobile Ground Responder Endpoint (`/mobile_responder.html`):** Gloved smartphone/tablet view served by `dashboard_server.py` showing live distance/bearing to the drone-tracked hiker, thermal crop preview, and 1-tap `Victim Reached` / `Request Drop at My GPS` buttons that immediately update the Incident Commander's map in `operator_mission_console.html`.
   * **Multi-Format Coordinate Parser in `112 SOS` Bar:** Accept `WGS84 Decimal` (`66.3695, 29.3155`), `WGS84 Aviation DDM` (`66° 22.17' N, 029° 18.93' E`), and `Finnish ETRS-TM35FIN` (`N 7362410 E 603820`) seamlessly in `#inpSosCoords`.
2. **Sprint P1 (Hardware-in-the-Loop & Airspace Safety Integration — Week 1):**
   * **Live Ground-Sensor & Sky-Diode Health Drawer in `:8788`:** Stream live trail-post triggers (`NODE-NORTH-01`, battery voltage, `2.4 GHz` Sky-Diode SNR, and verified `Ed25519` photo bursts) directly onto the Google Earth C&C map.
   * **Manned Helicopter ADS-B / U-Space Geozone Overlay:** Display incoming *Rajavartiolaitos* SAR helicopters on View 1 and automatically enforce the `Poronhoitolaki` (`100 m` AGL) ceiling and `35 m` AGL emergency altitude hold.
3. **Sprint P2 (Offline Air-Gapped Resilience & Multi-Sortie Relief — Week 2):**
   * **Offline `.mbtiles` Satellite & DEM Cache Packager:** One-click pre-download of `z=12..19` Google Earth / NLS Finland orthophotos for the selected `15 km × 15 km` wilderness sector so field laptops operate with zero internet connectivity.
   * **Automated `<30%` Battery Relief Drone Handover in `:8788`:** Visually animate a fresh standby drone launching from the roadhead nest to seamlessly take over `Opaslyhty` trail guidance or sector radar patrol before the active drone's battery reaches `25%` SOC.
