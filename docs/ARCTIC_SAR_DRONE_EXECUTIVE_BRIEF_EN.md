# Karhunkierros SAR & "Digital Wilderness Hut" (`v1.6` / `v2.0` Concept Release) — End-to-End Wilderness Rescue Chain (Executive Concept Brief)

> **CONCEPT-STAGE STATUS DISCLAIMER & PROJECT ETHOS (`MIT LICENSE` — 🇫🇮 FINNISH ENGINEERING):**
> - **Private, Pro-Bono Free-Market COTS Initiative:** Developed as an independent, private, pro-bono free-market engineering project (`🇫🇮 Finnish engineering`) showing how open commercial off-the-shelf (`COTS`) hardware (`€1,189–€1,329`) and voluntary, decentralized civil-society dispatch ("Uber-for-SAR") can solve Arctic life-safety challenges without waiting for `€50,000+` state procurement programs or intrusive surveillance infrastructure.
> - **Concept & Simulation Stage:** This document presents an **open-source engineering concept, COTS hardware bill-of-materials (`€1,189–€1,329`), and software-simulated reference architecture** (`29/29` unit tests passing in `collector_hub/drone_observer.py`). While the ground trail-camera and collector stack ([`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam)) is bench-verified, **the SAR drone airframe, `-25 °C` winter flight endurance, payload drop, and `+10 °C` roofed station are currently at the concept and simulation stage** and have not yet undergone live flight testing or `Traficom` / `EASA SORA` regulatory certification (see Section 4.3 Readiness Matrix).

> **Core Premise (Why This Saves Lives in Roadless Arctic Wilderness):**
> When a hiker or family becomes lost in roadless boreal or Arctic wilderness (such as Finland's **Karhunkierros** trail in Oulanka / Ruka), the nearest plowed road is often **`8–25 km` away**. **A police van or ambulance cannot drive into roadless forest**, and mobilizing a snowmobile or ski patrol (`Poliisi` / `Rajavartiolaitos` / `Pelastuslaitos` / `Vapepa`) to reach the coordinates typically takes **`1.5–3 hours`**.
>
> In sub-zero winter conditions (`-15 °C to -30 °C`), wet clothing, or darkness, waiting stationary on the ground leads to severe hypothermia in **`30–45 minutes`** — long before a ground rescue team can arrive.
>
> Yet across Finnish Lapland and Koillismaa, the state forestry agency (**Metsähallitus Parks & Wildlife Finland**) maintains a unique network of **`450+` open wilderness huts (*autiotupa*) and day huts**, each equipped with a **wood-burning stove, dry firewood, and warm shelter**, often located just **`0.5–2.5 km`** from the lost party — **provided the hikers can find the trail and direction to the hut in darkness, blowing snow, or active GPS jamming.**

![Karhunkierros SAR (v1.6) — End-to-End Wilderness Rescue Chain (Stages 1–5)](images/arctic_sar_rescue_chain_5_stages_en_v4.jpg)

---

## 1. End-to-End Rescue Chain (Stages 1–5): From Lost on the Trail to a Warm Wilderness Hut

### 3D Isometric Terrain & Operational Overview (Stages 1–5 in Practice)

![Karhunkierros SAR — 3D Terrain View: From Plowed Road End to Roadless Wilderness (Stages 1–5)](images/arctic_sar_isometric_terrain_en_v3.jpg)

```mermaid
flowchart LR
    S1["1. Passive Trail Counter\n(Fibox ARCA 48h ring buffer 0W RF\n+ 940 nm AprilTag atop trail post)"] --> S2["2. SOS Trigger & Launch\n(112 / Trail-post SOS -> +10°C Nest\nOR Mobile Sled / Patrol Van)"]
    S2 --> S3["3. Jam-Proof Search (2–4 min)\n(X500 at 105 m: Thermal/Starvis lock\n+ Optical Flow / LiDAR without GPS)"]
    S3 --> S4["4. Warm Cask (15 m) & Lantern (28 m)\n(+42°C drink cask w/ 25 N fuse,\n28 m above trees 1,500 lm 10° beam)"]
    S4 --> S5["5. Safe in Wilderness Hut (10–25 min)\n(Warm wood stove — or for injured:\n45 m sky strobe + 18 h ground beacon)"]
```

### Stage 1: Lost in Roadless Wilderness & Passive 48h Trail Counter (`Fibox ARCA` + `940 nm` Fiducial)
* **Field Scenario:** A family or hiking group is trekking along an autumn or winter wilderness route (`15–25 km` from the nearest plowed road, unreachable by wheeled vehicles). Darkness, a sudden snow squall, or exhaustion sets in, and the party drifts off the trail or becomes separated.
* **Background Preparation (`PassiveTrailSightingLedger`):** At the base of the wooden trail-junction signpost sits an industrial weatherproof enclosure (**`Fibox ARCA IP67`**), a compact sensor pod at `2 m` height (`PIR` + `24 GHz` FMCW radar + `Starvis` optical camera), and a passive **`940 nm` AprilTag retro-reflective fiducial plate** mounted atop the post. Operating 100% RF-silent (`0.00 W` RF, isolated via a one-way optical fiber diode), the node logs only an anonymous kinematic vector into its local 48-hour volatile ring buffer: *"3 hikers passed junction at 14:20 heading NNE at 1.1 m/s"*. If no official SAR alert occurs, the record auto-purges after 48 hours.

### Stage 2: Calling for Help, "Uber-for-SAR" Open Dispatch & Heated Roofed Nests (`SARDispatchMarketplaceCoordinator`)
* **Strict Humanitarian Trigger (`verify_humanitarian_sar_trigger`):** The system activates **only** upon a verified emergency trigger:
  1. An SOS ping from the hiker's **`112 Suomi`** app or **`Garmin inReach`** satellite communicator,
  2. Pressing the **physical red `112 SOS` button** on a trail post (works even when a smartphone battery has frozen dead at `-25 °C`!), or
  3. An official cryptographic search order (`SAR-ORDER`) from **`Poliisi`** (Police), **`Rajavartiolaitos`** (Border Guard), or **`Pelastuslaitos`** (Rescue Services).
* **Open Task Dispatch ("Uber-for-SAR"), Auto-Prioritization & Human Control Panel:**
  * **Mobile Patrol Drone Units (`MOBILE_PATROL_UNIT` — e.g., Police vans at the plowed road end, Border Guard patrols, Vapepa snowmobile sleds):** Field crews see the open alert on their vehicle terminal (distance, estimated flight ETA, target coordinates) and tap **`[Accept Task]`**, just like an on-call driver accepting a nearby dispatch request.
  * **Automated Roofed Wilderness Stations (`AUTOMATED_ROOFED_NEST`, `+10 °C`):** Stationed drones protected under a heated, motorized snow/freezing-rain roof in **`AUTO_ACCEPT_GEOFENCE`** mode automatically accept alerts within their service radius (`<= 14 km`), open their motorized roof hatch, launch autonomously, close the roof during the flight, and dock back under the roof afterward to recharge.
  * **Multi-Unit Auto-Prioritization & Human Command Override:** When multiple mobile units and roofed stations accept the same alert, the coordinator automatically scores and ranks them (Flight ETA `45%`, Winter Battery Margin `25%`, Sensor/Payload Capability `15%`, Readiness `15%`), assigning the fastest unit as **`#1 PRIMARY_SAR_RESCUER`** and the second-best as **`#2 SECONDARY_BACKUP_INTERCEPT`**. A human incident commander can override automation at any time from the dashboard (`Force Assign`, `Hold Launch`, `Force RTB`) or lock the system to **`MANUAL_COORDINATOR_APPROVAL_ONLY`**.

### Stage 3: High-Speed Transit, GNSS/RF Jamming Bypass & Target Lock (`2–4 Minutes`)
* **Airframe (`Holybro X500 V2` `500 mm` carbon frame + `-40 °C` `8,000 mAh 4S2P` (`14.8 V`, `118.4 Wh`) Ultra-Low-Temp Li-Ion):** Painted in high-visibility **SAR International Orange (`RAL 2005`)** with low-noise 10-inch propellers (`58 dBA`), the rescue drone transits at `105 m` AGL (`65 km/h`) to the search sector in **2–4 minutes**.
* **Operates Through 100% GPS Spoofing & RF Blackout (`evaluate_gnss_rf_jamming_and_weather_resilience`):**
  * **GNSS jamming or spoofing** (increasingly common in northern and eastern border regions) neither halts nor misleads the aircraft: a downward **optical flow sensor (`MicoAir MTF-02P / PMW3901`) and `Benewake TF02-Pro` (`40 m`, `IP65`) LiDAR** continuously measure true ground speed and height above the snow/canopy. If GNSS diverges from optical flow (`> 3.5 m/s`), the flight stack **fences off GNSS (`ekf_gnss_fenced_off_no_flyaway`)** and navigates via optical-inertial dead-reckoning and the `940 nm` AprilTag trail-post fiducials.
  * Even under complete **radio jamming (`RF Blackout`)**, the drone executes the full rescue mission **100% autonomously onboard (`abort_rescue_on_rf_loss = False`)**.
* **Autonomous Search & Target Lock (`OnboardTargetLockSelfGuider`):** The drone's onboard thermal camera (`256×192 LWIR`) and low-light camera (`IMX462 Starvis` + `YOLOv8n`) detect human signatures (including separated tourist groups), distinguish humans from reindeer and moose, and maintain a Kalman-filtered lock across pine-canopy occlusions.

### Stage 4: Warm Cask Delivery (`15 m`) & Above-Canopy `28 m` Elastic Pull-Guidance (`compute_elastic_pull_guidance_vector`)
* **Safe First-Aid Drop onto Open Snow (`15 m` Safety Offset + `25 N` Breakaway Fuse):** The drone selects an open snow patch **at least `15 meters` away** from the hikers and lowers its **insulated warming cask and survival kit** (`+42 °C` warm berry-glucose electrolyte drink on tap, hand warmers, glucose gel packs, aluminized mylar thermal blanket, and two-way emergency button). The payload releases cleanly via a `25 N` magnetic breakaway fuse, and the drone climbs back to `50 m` AGL before playing voice instructions.
* **Above-Canopy `28 m` Elastic Pull-Guidance (*Follow & Elastic Pull to Safety*):**
  * To guarantee the aircraft **never** clips spruce branches in wind or darkness, `TF02-Pro` LiDAR terrain following keeps the drone safely **above the tree crowns (`28 m` AGL)** while tracking the hikers via thermal vision and **"pulling" them along the trail** by projecting a narrow **`10°` (`1,500 lm`) spotlight beam** onto the snow **`15 meters` ahead of the hikers** toward the nearest wilderness hut.
  * If a hiker drifts off the trail (`> 8 m`), the airframe remains safely `>= 15 m` away while sweeping the spotlight closer (`6 m` ahead of the hiker) and issuing voice guidance back onto the packed trail. Whenever the hiker stops to rest, the beam pauses and waits (`10 m` beam offset, `>= 15 m` airframe distance). Upon reaching the wilderness hut (`<= 20 m`), the drone offsets `15 m` to the clearing in front of the cabin (never hovering over the roof or chimney!) and illuminates the cabin door before returning to dock (`RTB_DOCKED_UNDER_ROOF_AND_RECHARGING`).

### Stage 5: Safe Inside the State Wilderness Hut (`10–25 min`) — OR `18-Hour` Beacon for an Immobilized Casualty
* **Case A — Ambulatory Party (`10–25 Minutes` to a Warm Wood Stove):** Following the `1,500 lm` aerial lantern beam, the hikers walk directly into the **Metsähallitus** wilderness hut (or mobile rescue shelter) and light the stove more than **90 minutes before** a ground snowmobile patrol could reach them.
* **Case B — Injured or Exhausted Hiker Who Cannot Walk (`IMMOBILIZED_SHELTER_IN_PLACE`):**
  * If the hiker cannot move within `3 minutes` of receiving the thermal survival kit (e.g., ankle fracture or severe hypothermia), the drone automatically detects immobility and switches its voice guidance to: **`"STAY IN PLACE INSIDE THE THERMAL BLANKET — GROUND RESCUE IS BEING GUIDED TO YOU"`**.
  * The drone ascends to `45 m` AGL as a **high-visibility sky beacon (`1,200 lm` strobe visible `3–5 km` away)**. When flight battery reaches `25%` before ground teams arrive, the drone never abandons the casualty in darkness—it lands in a clearing `15 m` away, disarms its motors, and operates for **`18+ hours` as a low-power ground strobe beacon (`GROUNDED_CLEARING_18HR_LOW_POWER_STROBE_BEACON`)** until the snowmobile patrol arrives.

---

## 2. Timeline Comparison: Freezing Stationary vs. Aerial Lantern Guidance to a Wilderness Hut

| Stage / Metric (`12 km` from road, `-22 °C`, dark forest + GPS jamming) | Without Rescue Drone (Waiting for Ground Patrol) | With Karhunkierros SAR (`v1.6`) Guide Drone (*Guided to State Wilderness Hut*) |
| :--- | :--- | :--- |
| **1. Police Van / Ambulance Road Access** | **Impossible** (`12.0 km` across roadless ridge and river terrain) | **Not required for initial response** — launches from `+10 °C` roofed station (`940 nm` optical diode) or snowmobile sled at road end. |
| **2. First Contact & Operation Under GPS/RF Jamming** | **`~135 minutes`** (`2 h 15 min` for snowmobile/ski patrol to arrive) | **`~2.5 minutes`** (operates without GPS or radio links using `MTF-02P / PMW3901` optical flow, `TF02-Pro` `40 m` LiDAR, and `940 nm` post fiducials). |
| **3. First Aid & Thermal Energy Restoration** | None available until ground patrol arrives | Lowers **onto snow `15 m` away** (`25 N` magnetic fuse) a **warm (`+42 °C`) berry-glucose drink cask, hand warmers, and thermal blanket**. |
| **4. Guidance to Wilderness Hut (`28 m` Aerial Lantern)** | Lost hikers cannot see the trail in darkness or tell which way the hut lies | Flies safely **above the trees (`28 m` AGL) `15 m` ahead**, illuminates the trail with a **`1,500 lm` (`10°`) beam**, waits when hikers rest, and leads directly to the hut door. |
| **5. If Hiker Is Injured and Cannot Walk** | High hypothermia risk in darkness without visual pinpointing | **`45 m` sky strobe beacon** + at `25%` battery lands in a clearing as an **`18+ hour` ground beacon** beside the sheltered casualty. |
| **6. Time to Reach a Warm Stove Under a Roof** | **`135 min`** *(exceeds the `30–45 min` hypothermia window several times over!)* | **`~10–25 minutes`** (**over `110 minutes` before ground teams arrive!**) |

---

## 3. Privacy-by-Design Architecture ("Digital Wilderness Hut")

Even though the system exists purely to save human lives in emergencies, every hardware and software layer is engineered from the ground up to satisfy strict European data-protection standards (GDPR / Data Protection Ombudsman), public right-of-access traditions (*Jokamiehenoikeudet*), and wilderness ethics without compromise:

1. **48-Hour Auto-Purging "Black Box" (`PassiveTrailSightingLedger`):** Trail-side ground nodes (`Fibox ARCA`, sharing 100% of the hardware/software stack with [`arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam)) are completely RF-silent (`0.00 W` RF), **never** use facial recognition or cloud uploads, and automatically overwrite anonymous movement vectors after 48 hours.
2. **Strictly Emergency-Triggered ("Pull, Don't Push"):** The drone launches **only** when a hiker triggers an SOS via `112 Suomi` / `Garmin inReach`, presses the **physical red `112 SOS` button** on a trail post, or when `Poliisi`, `Rajavartiolaitos`, or `Pelastuslaitos` issues a cryptographically signed search order (`SAR-ORDER`).
3. **Jamming-, Freeze-, and Icing-Resilient (`-25 °C` Polar Night, GPS Spoofing & Freezing Drizzle):** Powered by `-40 °C` rated `8,000 mAh 4S2P` (`14.8 V`, `118.4 Wh`) ultra-low-temp Li-Ion cells, hydrophobic propeller coating + automated ice-shedding spin bursts (`ICE_SHED_RPM_BURST`), a `940 nm` optical diode, and spoof-proof optical flow (`MTF-02P / PMW3901`) + `Benewake TF02-Pro` (`40 m`, `IP65`) LiDAR.
4. **Reindeer Herding Act (`Poronhoitolaki 848/1990 § 42`) Wildlife Protection:** Onboard AI distinguishes humans from reindeer and moose; whenever reindeer are detected, the aircraft automatically enforces **`>= 100 m` altitude** and mutes its acoustic speaker.
5. **Hard-Coded `15 m` Horizontal Safety Offset, `28 m` Above-Canopy Floor & `~€1,189` Snap-In COTS Build (Zero Custom PCBs):** Software safety gates prohibit flying closer than `15 m` horizontally to any person, keep the drone at `28 m` AGL above the spruce canopy, and allow the entire aircraft to be assembled in **`~2.5 hours` with zero custom circuit boards** from off-the-shelf plug-and-play modules (`Holybro X500 V2` + `Pixhawk 6C` + `Pi 5` + `USB Thermal/Starvis` + `TF02-Pro 40m LiDAR`, total **`~€1,189`**).

---

## 4. Technical Architecture, COTS BOM (`€1,189` Base / `€1,329` `v2.0`) & Readiness Matrix

### 4.1 Eight-Part Landscape & Snap-In COTS Aircraft (`~2.1 kg` AUW, Zero Custom PCBs)

![One System, Eight Parts Working Across the Landscape](images/arctic_sar_system_8_parts_overview_v1.jpg)

![Snap-In COTS Aircraft Subsystems](images/arctic_sar_aircraft_cots_subsystems_v2.jpg)

| Subsystem Category | Off-the-Shelf Modules (`JST-GH` / `STEMMA QT` / `USB-C` / `XT60`) | Cost (EUR) |
| :--- | :--- | :--- |
| **1. Airframe & Propulsion** | `Holybro X500 V2` `500 mm` carbon frame + `Pixhawk 6C` + `M10` GNSS + `4× 2216 KV920` motors + `1045` props + `RAL 2005` orange arms | `€490` |
| **2. Navigation Sensors (`<= 40 m` AGL)** | `Benewake TF02-Pro` (`40 m`, `IP65`) LiDAR + `MicoAir MTF-02P` (`PMW3901`) optical flow | `€134` |
| **3. Companion Compute & Storage** | `Raspberry Pi 5` (`8 GB`) + active cooler + `27W` buck (`5.1V/5A`) + `SanDisk Industrial 64 GB` | `€117` |
| **4. Dual Vision Payload (`EO + LWIR`)** | `256×192 LWIR` USB-C thermal camera (`25 Hz`) + `Sony IMX462 Starvis` low-light USB camera (`130° FOV`) | `€235` |
| **5. Telemetry & Pilot Override** | `Holybro SiK / RFD868x` (`868 MHz`) or `900 MHz` LoRa + `RadioMaster ER5A V2` (`2.4 GHz ELRS`) + optional `LTE` modem (`+€95`) | `€50` |
| **6. Lantern, Strobe, Audio & Care Drop** | `1,500 lm` (`10°`) spotlight + `1,200 lm` sky strobe + `80 dB` speaker + `25 N` servo breakaway release + `+42 °C` care cask | `€145` |
| **7. Arctic Battery (`-40 °C`) & Fastener Kit** | `8,000 mAh 4S2P` (`14.8 V`, `118.4 Wh`) `-40 °C` Li-Ion (`XT60`) + `2.5 mm` silicone pad + `M3` hardware | `€113` |
| **Base Core Drone Subtotal (`v1.6` Bench Kit)** | **Complete snap-in COTS drone assembly (`~2.5 hours`, zero custom PCBs)** | **`€1,189`** |
| **8. `v2.0` Field-Hardening Additions (`FIN-LAB`)** | Optional `LTE` burst modem (`+€95`) + `31-material` clamp-on EMI ferrite kit (`+€15`) + wireless `UHF/DECT` drop-cask mic (`+€30`) | `+€140` |
| **Hardened `v2.0` Core Aircraft Total** | **Full `v2.0` field-hardened SAR aircraft (excluding optional `€610` `+10 °C` roofed launch nest)** | **`€1,329`** |

### 4.2 Five-Layer Jam-Resilient Navigation Stack, Four-Tier Link Ladder & Canopy Geometry

![Five-Layer Jam-Resilient Navigation Stack](images/arctic_sar_navigation_layers_5tier_v1.jpg)

![Four-Tier Communication Link Ladder & Store-and-Forward](images/arctic_sar_link_ladder_4tier_v1.jpg)

![Above-Canopy Aerial Lantern & Standoff Geometry](images/arctic_sar_opaslyhty_canopy_geometry_v1.jpg)

### 4.3 Readiness & Verification Matrix (Design vs. Simulation vs. Field Validation)

![From Bench to Field: The Validation Ladder (Steps 1–7)](images/arctic_sar_slide28_validation_ladder_v1.jpg)

| Subsystem / Capability | Designed | Simulated / Unit-Tested (`29/29`) | Hardware Bench | Field-Validated | Authorised |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trail Posts & Collector Hub (`arctic-trail-cam` stack)** | Yes | Yes | Yes (`Pi 5` + `Pico` + `LoRa`) | Partial (winter optical/RF) | No (`Metsähallitus` permit pending) |
| **Core SAR Drone Hardware (`X500 V2` + `Pixhawk 6C` + `Pi 5`)** | Yes | Yes (`37` `ArduCopter 4.5+` params) | Bench check (`drone_observer.py`) | No (`-25 °C` flight endurance open) | No (`Traficom SORA` required) |
| **GNSS Spoof Fence & `<= 40 m` Optical Flow / LiDAR Hold** | Yes | Yes (`F01`–`F53` regression suites) | Sensor bench check | No (live jamming flight open) | No |
| **Above-`40 m` Baro-DEM & Thermal/Visual Odometry (`FIN-LAB-01`)** | Yes | Modelled | Not yet flight-tested | No | No |
| **Aerial Lantern (`28 m` AGL, `>= 15 m` Standoff) & `25 N` Drop** | Yes | Yes (`compute_elastic_pull_guidance_vector`) | Mechanical bench | No (local canopy survey required) | No |
| **"Uber-for-SAR" Open Dispatch & `+10 °C` Roofed Nest** | Yes | Yes (`SARDispatchMarketplaceCoordinator`) | Dashboard & API verified | No (winter roof-actuator test open) | No (`Poliisi` / `RVL` / `ERC` MoU) |
| **Marsupial Electric Carrier & Mid-Air Drop (`Cartridge B`)** | Yes (`3D CAD` + `CNC` cut sheets) | Yes (`35/35` tests + `ArduPlane 4.5+` `.param`) | Autonomy & CAD verified | No (live electric carrier & drop test open) | No (`Traficom Specific SORA` required) |

---

## 5. Marsupial Dual-Drone Architecture (`35–45 km` Storm Rescue via Electric Fixed-Wing Carrier)

### 5.1 Why a Standalone Multi-Rotor Hits a Hard Physics Wall at `4.59 km` in a `14 m/s` (`50 km/h`) Arctic Storm
While the standalone `Karhunkierros` quadcopter (`Holybro X500 V2`, `18 m/s` cruise) excels within `0–14 km` of a roadhead or heated trail nest in calm-to-moderate weather, **multi-rotor aerodynamics hit a hard physical wall during severe Arctic fells storms (`14 m/s` / `50.4 km/h` headwind at `-25 °C`):**
* Fighting a `14.0 m/s` headwind at `18.0 m/s` true airspeed yields a net ground speed of only **`4.0 m/s` (`14.4 km/h`)** while drawing `485 W` continuous electrical power.
* Because cold-soaked `-25 °C` battery safety gates enforce a mandatory return-to-base abort at `50%` usable capacity (`47.4 Wh`), a standalone quadcopter is forced to turn back at **`4.59 km`** (`19.1 minutes` outbound) — leaving any hiker stranded **`15–45 km` deep in roadless back-canyons** unreachable until the storm subsides or a `€15,000/hr` manned turbine helicopter can fly.
* Conversely, a fixed-wing electric carrier can dash `35 km` in `11 minutes` at `259 km/h` (`72 m/s`), **but cannot fly below the spruce canopy, cannot hover `15 m` from a casualty to winch down a `+42 °C` glucose cask, and cannot lead a walking survivor at `1.2 m/s` (`4.3 km/h`) along a winding forest trail.**

### 5.2 The "Marsupial" Breakthrough (`Cartridge B`): `259 km/h` Electric Fixed-Wing Carrier Dropping the Folded `Karhunkierros` Quadcopter
In the **`FIN-LAB-02` (`Sled B-Prop`)** cooperative **Marsupial Dual-Drone Architecture**:

1. **Captive Heated Belly-Bay Transit (`0–35 km` in `11.3 Minutes` at `259 km/h`):**
   * The `2.20 m` wingspan twin-boom `110°` inverted $\Lambda$-tail **`FIN-LAB-02` Fixed-Wing Carrier** carries the **folded `Karhunkierros` SAR quadcopter (`3.20 kg` dry + `1.0 kg` `+42 °C` glucose/blanket cask = `4.20 kg`)** inside its insulated ventral belly bay (`580 × 240 × 165 mm`, centered dead on `X_CG = 595.0 mm` for `0.0 mm` pitch-trim shift upon release).
   * During the `11.3-minute` dash (`72 m/s` TAS / `58 m/s` net ground speed against a `14 m/s` storm headwind), a **`28 V` magnetic breakaway umbilical** and **`15 W` PTC heater** keep the captive quadcopter's battery at **`+15.0 °C` and `100.0%` State of Charge (`118.4 Wh`)** — consuming **zero** quadcopter battery during the `35 km` storm transit!
2. **4-Stage Mid-Air Drogue-Stabilized Deployment (`85 m` AGL, `t = 0.0 s` to `2.8 s`):**
   * **Stage 1 (`t = 0.0–0.3 s` — Electric Slow-Down & Spring Ejection):** Over the target canyon (`85 m` AGL), the Fixed-Wing Carrier throttles its aft `12S` electric pusher to idle, slows to **`22.0 m/s` (`79 km/h`)** on its `355 mm` nose electric propeller, opens its ventral clamshell doors, and fires dual `80 N` ejection springs (`2.8 m/s` downward exit velocity, clearing the twin tail booms by `1.85 m` in `0.28 s`).
   * **Stage 2 (`t = 0.3–1.2 s` — Drogue Pitch-Up & Snap-Open Arms):** At `1.5 m` separation, a static line deploys a **`0.35 m²` cruciform ribbon drogue chute**, braking the quadcopter from `22 m/s` to `11 m/s` and pitching its nose upright while torsion springs snap all 4 carbon rotor arms outward into hardened steel detent pins (`hall-effect` lock verified in `0.45 s`).
   * **Stage 3 (`t = 1.2–2.0 s` — Drogue Cutaway & Brushless Motor Spin-Up):** At `t = 1.2 s`, a micro-servo jettisons the drogue chute (`68 m` AGL) and all 4 brushless rotors spin up to full hover thrust by `t = 2.0 s`.
   * **Stage 4 (`t = 2.0–2.8 s` — Hover Lock Above Canopy):** The `Karhunkierros` quadcopter arrests its descent at **`59.6 m` AGL** (`>30 m` above the spruce crowns, `19.6 m` safety margin above the `40 m` floor) with **`99.4%` battery remaining (`117.7 Wh`)** and warm `+14.8 °C` cells!
3. **Cooperative Joint Mission (`320 m` Orbiting Carrier Radio Relay + Under-Canopy Quad Rescue & Nest Recovery):**
   * **Under-Canopy Quadcopter (`15 m` Cask Drop + `28 m` Lantern Walk):** The deployed quadcopter descends into the sheltered canyon floor (where wind beneath the spruce canopy drops from `14 m/s` to `3.5 m/s`), winches the `1.0 kg` `+42 °C` glucose/blanket cask onto open snow `15 m` from the survivor (`3.5 min`), and then guides the walking survivor for **`18 minutes` (`1.3 km`)** via the `28 m` above-canopy **`1,500 lm` (`10°`) aerial lantern beam** directly to the nearest **Metsähallitus** wilderness hut (*autiotupa*).
   * **Overhead Carrier Relay (`320 m` AGL Electric Loiter):** Simultaneously, the `FIN-LAB-02` Carrier climbs to **`320 m` AGL** and orbits quietly at `21 m/s` on **`260 W` nose electric propeller power (`45 min` loiter)** — acting as a high-altitude **`868 MHz` ELRS & Wi-Fi airborne communications relay** (`+28.4 dB` link margin) bridging the deep granite canyon to the `35 km` base station!
   * **Dual Recovery:** Once the survivor is inside the warm wilderness hut, the Fixed-Wing Carrier glides back to base while the `Karhunkierros` quadcopter lands autonomously inside the nearest **`+10 °C` motorized roofed wilderness nest box (`34.2%` battery margin remaining)** to recharge for the next mission.

### 5.3 Complete Range, Speed & Payload Comparison Across All Modular Configurations (`60-Second` Swap)
Because the `FIN-LAB-02` airframe uses a modular **Belly Payload Cartridge (`580 × 240 × 165 mm` centered at `X_CG = 595 mm`)** and a quick-release **Aft Propulsion Sled (`4× M5` bolts)**, a single `$180` CNC foam/carbon airframe shell supports four mission profiles:

| Platform & Modular Configuration | Cruise / Dash Airspeed | Max Range in `14 m/s` (`50 km/h`) Storm Headwind | Max Calm / Hybrid Range | Max Endurance | Primary Payload & Operational Capability | Unit Hardware BOM |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **1. Standalone `Karhunkierros` SAR Quadcopter (`v1.6` / `v2.0`)** | `65 km/h` (`18 m/s`) | **`4.59 km`** *(aborts at 50% SOC due to `4.0 m/s` net groundspeed)* | **`14.0 km`** *(round-trip)* | `32 min` | `1.0 kg` `+42 °C` warm cask winch (`15 m` offset) + `28 m` above-canopy `1,500 lm` lantern walk to hut. | **`€1,189 – €1,329`** |
| **2. `FIN-LAB-02` Carrier + `Cartridge B` (*Marsupial Carrier + Folded SAR Quad*)** | **`259 km/h`** (`72 m/s` dash) / `79 km/h` loiter | **`35 – 45 km` radius** (`11.3 min` transit; quad arrives at `100%` SOC!) | **`90 km`** *(total carrier flight path)* | `45 min` relay + `28 min` quad hover | **Delivers full `Karhunkierros` Quad (`3.2 kg` + `1.0 kg` warm cask) into deep canyon** + `320 m` overhead radio relay (`+28.4 dB`). | **`~€2,450` Carrier + `€1,189` Quad** |
| **3. `FIN-LAB-02` Carrier + `Cartridge A` (*Heavy `5.0 kg` Parachute Survival Pod*)** | **`259 km/h`** (`72 m/s` dash) | **`35 – 55 km` radius** (`11.3 min` to `35 km`) | **`95 km`** | `45 min` loiter + `22 min` dash | Drops **`5.0 kg` heavy survival capsule** (`3.0 L` `+42 °C` drink + `RESTUBE 180` ice flotation + arctic bivvy + `PLB`, `<8.5 m` CEP) + `320 m` sky strobe. | **`~€2,450`** |
| **4. `FIN-LAB-02` Carrier + `Cartridge C` (*Extended-Range Recon & Relay*)** | **`259 km/h`** dash / `76 km/h` electric | **`45 km`** *(storm search box)* | **`165 km`** *(electric cruise)* | **`3.75 hours`** (`225 min`) | Auxiliary battery pack + `1.2 kg` micro survival drop pod + wide-area thermal/Starvis river/fell search. | **`~€2,650`** |
| **5. `FIN-LAB-02` Airframe + `Sled C` (*4-Stroke Canyon Relay Loiter, `<300 km` Capped*)** | `101 km/h` (`28 m/s` loiter) | **`45 km` box** (`6.0 hr` canyon relay orbit) | **`284.5 km`** *(`<= 285 km` EU `<300 km` fuel/geofence cap)* | **`6.0 hours`** | `0.68 kg` capped UAT fuel (`12.9 g/min` burn) + `5.0 kg` rescue/relay payload for 6-hour canyon airborne mesh relay. | **`~$4,100`** |

---

## 6. Pro Bono Pilot & Phased Field Validation (Phases 1–3)

1. **Phases 1–2 (Private Forest Validation — "Lean-To / Cabin = Wilderness Hut"):** Validate first via mobile trunk/sled launch in dense coniferous forest (`€350` camera walk test $\rightarrow$ `€1,189–€1,329` full COTS drone pilot under a safety pilot's RC override).
2. **Phase 3 (Northern Finland Pro Bono Pilot):** Offer the field-proven open-source reference package for joint evaluation with **Metsähallitus Parks & Wildlife Finland** (*Oulanka / Karhunkierros*, *Urho Kekkonen National Park*, *Pallas-Yllästunturi*), **Vapepa** (Voluntary Rescue Service), **Finnish Air Rescue Society (SLPS)**, **Poliisi**, **Rajavartiolaitos**, and regional **Rescue Departments**.
