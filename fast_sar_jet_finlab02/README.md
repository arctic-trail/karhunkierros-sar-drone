# Arctic Fast-SAR Jet-Hybrid (`arctic-fast-sar-jet` / `FIN-LAB-02`, `v0.1` Concept Release) — Autonomous Regional Fast-Response Wilderness & Maritime Rescue UAV

> **Open-source, 100% Non-Chinese (`EU / UK / CH / US NDAA`) Arctic Fast-Response Search-and-Rescue (`SAR`) Hybrid Jet-Electric UAV & High-Speed Civil Airspace-Safety Testbed (`~€4,850` turnkey / `US$1,320` airframe+avionics COTS). A private, pro-bono free-market COTS build. 🇫🇮 Finnish engineering.**
>
> * **GitHub Topics:** `ardupilot` · `arduplane` · `raspberry-pi-5` · `search-and-rescue` · `sar-drone` · `micro-turbojet` · `gnss-denied` · `thermal-imaging` · `open-hardware` · `arctic-engineering` · `cots` · `ndaa-compliant`
> * **Sister Project — Tier 1 (RF-Silent Arctic Trail & Cabin Camera with 1-Way Optical Diode & `[P11-AIR]` Acoustic Grid):** [`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam)
> * **Sister Project — Tier 2 (Autonomous Wilderness SAR Quadcopter, Heated Roofed Nest & "Uber-for-SAR" Dispatch):** [`arctic-trail/karhunkierros-sar-drone`](https://github.com/arctic-trail/karhunkierros-sar-drone)
> * **License:** [`MIT License`](LICENSE)

> [!WARNING]
> **PROJECT STATUS & CIVILIAN USE-CASE DISCLAIMER — EARLY-STAGE ENGINEERING CONCEPT, 3D CAD & SIMULATION REFERENCE (`MIT LICENSE`)**
> * **100% Civilian Technology (Inspiration vs. Use Case):** While the low-cost mouldless COTS fabrication, GNSS-denied navigation, `-30 °C` cold-soak engineering, high-volume U-Space track fusion (`2,500` pairs in `4.4 ms`), and head-on corridor response geometry draw engineering inspiration from harsh and contested airspace resilience lessons, **the actual use case of all hardware and software in this repository is 100% civilian**:
>   1. **Regional Wilderness & Maritime Search and Rescue (`SAR`):** Delivering heated emergency survival capsules, AEDs, insulated bivvy bags, and two-way rescue radios `35–45 km` into Lapland wilderness or coastal archipelagos in `15 m/s` winter headwinds.
>   2. **Civil U-Space Airspace Safety, Airport Noise-Abatement & Corridor Verification:** Passively classifying low-altitude overflight acoustics (`FIN-SIG-LIB v1.0`), monitoring utility substations (`[P12-BELT]`), and performing cooperative visual/thermal identification along civil aviation corridors.
>   3. **Coastal Environmental & Subsea Power/Telecom Cable Inspection (`FIN-LAB-06`):** Autonomous solar/`LiFePO4` surface-vessel (`USV`) side-scan sonar and magnetic cable-landfall inspection.
> * **Concept & Simulation Stage (First Public Release):** This repository publishes an open-source **aerospace engineering concept, parametric 3D `STEP AP214` / `STL` solid CAD geometry, 100% Non-Chinese COTS bill-of-materials (`US$1,320` airframe+avionics / `~€4,850` turnkey), and software simulation reference architecture**. It is **not** a flight-certified aircraft, an operational rescue service, or military equipment.
> * **What Is Built & Tested Today vs. What Remains Conceptual:**
>   1. **Hardware Bench-Verified Today (Shared Tier-1/Tier-2 Stack):** The companion compute (`Raspberry Pi 5`), `Pico 2` sensor/gatekeeper stack, optical/LoRa telemetry links, and dual vision pipeline are shared with [`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam) and [`arctic-trail/karhunkierros-sar-drone`](https://github.com/arctic-trail/karhunkierros-sar-drone), where they have been assembled and verified on the indoor bench.
>   2. **3D CAD & Software-Simulated Today (`5/5` Automated Suites Passing):** The parametric 3D solid model (`cad/arctic_fast_sar_jet_iter1_fixed16deg.step`), affine-Breguet / compressible Brayton-cycle sizing calculator (`sar_sizing_calculator.py`), spool-lag lead-compensated turbine autonomy & GNSS-denied navigation module (`sar_autonomy/pi_turbine_autonomy.py`), and FIN-LAB COTS benchmark solver (`northern_flank_red_gap_solver.py`) are verified in software simulation (`python3 -m unittest discover -s tests -v`).
>   3. **Unvalidated / Concept Stage (No Calendar Date Promises):** Physical airframe fabrication of the `14.95 kg` MTOW fixed-wing prototype, static thrust-stand runs of the turnkey European micro-turbojet (`JetCat P100-RX-BL` / `Xicoy X132`), `-30 °C` cold-soak trials, slowed (`25–28 m/s`) parachute survival-capsule release flights, and **Traficom / EASA Specific Category (`SORA`)** aviation approvals have **not yet been flight-tested or authorized** (see the [Readiness & Verification Matrix](#5-readiness--verification-matrix-design-vs-simulation-vs-field-validation) and [Intended Capability-Gated Roadmap](#6-intended-capability-gated-roadmap-no-calendar-date-promises) below).

> [!IMPORTANT]
> **Project Ethos — Private, Pro-Bono Free-Market Engineering & Voluntary Civil Society (`🇫🇮 Finnish Engineering`):**
> * **Free-Market COTS vs. `€250,000+` Bureaucratic Procurement:** Rather than waiting years for slow public-sector procurement tenders or locked `€250,000+` proprietary aerospace platforms, this is an independent, private, **pro-bono free-market engineering project** demonstrating how standard Allied/European commercial off-the-shelf (`COTS`) parts (`US$1,320` airframe+avionics plus a turnkey European `JetCat` or `Xicoy` micro-turbine) can deliver high-speed, storm-penetrating Arctic rescue reach at `~1/50th` of legacy cost.
> * **Zero Chinese Components (`100% EU / UK / CH / US NDAA Supply Chain`):** Every flight controller (`ARK FPV STM32H7`, USA), companion computer (`Raspberry Pi 5`, Sony UK Tech Centre), GNSS receiver (`u-blox ZED-F9P / M10`, Switzerland), airspeed/IMU sensor (`TE Connectivity` USA + `Bosch` Germany), micro-turbine (`JetCat` Germany / `Xicoy` Spain / `PBS` Czechia), and optional `OpenTurbine-EU` FADEC (`STMicroelectronics STM32G474`, France/Italy + `Bartels` German fuel pump + `GRW` German ceramic bearings) is sourced from Allied/European manufacturers (`0.0%` Chinese BOM share).
> * **Voluntary Civil-Society Integration ("Uber-for-SAR") & Hardware Privacy:** Integrates directly with the open-alert voluntary dispatch marketplace (`SARDispatchMarketplaceCoordinator` in [`karhunkierros-sar-drone`](https://github.com/arctic-trail/karhunkierros-sar-drone)) and `0.00 W RF` passive trail posts ([`arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam)), preserving human operator authority at every stage.

---

## 1. Unified 3-Tier Civilian Architecture

| Tier | Repository / System | Primary Civilian Mission Role | Propulsion & Speed Envelope | Operating Radius | 100% Non-Chinese Allied/EU Avionics & Sourcing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Ground & Corridor Grid)** | [`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam) (`[P11-AIR]`, `[P12-BELT]`) | Off-grid cabin/trail monitoring, 3D acoustic/micro-Doppler classification (`FIN-SIG-LIB v1.0`), non-RF substation perimeter sensing | Solar / `LiFePO4` static ground node (`44 Ω` `10 W` derated heater) | Continuous (`0.48 s` `DD\x03` Reg 15 alert) | `RP2350` (UK) + `Pi 5` (UK) + `Infineon IM69D130` (DE) + `Acconeer XM125` (SE) — `US$497 + $68` |
| **Tier 2 (Local Aerial Care & Lantern)** | [`arctic-trail/karhunkierros-sar-drone`](https://github.com/arctic-trail/karhunkierros-sar-drone) (`FIN-LAB-01` / `FIN-LAB-04` / `[P12-HEATED]`) | Precision hover care, thermal verification, aerial lantern guide (*Opaslyhty*), heated `6.5 s` rapid-dispatch nest & `285 km/h` cold-rated fast-climber | Electric quadrotor / fast fixed-wing (`65–285 km/h`) | `8–25 km` from heated trail nest | `ARK FPV` (USA) / `Cube Orange+` + `Pi 5` (UK) + `u-blox` (CH) — `€1,770–€2,965` |
| **Tier 3 (Regional Fast-SAR Jet-Hybrid)** | **`arctic-trail/arctic-fast-sar-jet` (`FIN-LAB-02`)** | **10–14 min regional storm-penetrating SAR dash (`35–40 km` in `15 m/s` headwind) + silent electric loiter + `350–400 km/h` open airframe** | **Turnkey EU `100–160 N` micro-turbojet (DE/ES/CZ) + `355 mm` nose folding electric prop (`92–400 km/h`)** | **`35–45 km` SAR drop radius (`70+ km` total range)** | **`ARK FPV STM32H7` (USA) + `Pi 5` (UK) + `STM32G474` (FR/IT) + `JetCat/Xicoy` (DE/ES) — `US$1,320` airframe+avionics** |

---

## 2. Single Source of Truth (`SSOT`) 3D CAD Geometry (`cad/generate_sar_blueprints.py`)

Every visual and aerodynamic calculation in this repository derives from a single parametric 3D solid model (`cad/arctic_fast_sar_jet_iter1_fixed16deg.step` and `cad/design_params_sar.json`):
- **Chined Blended Center-Body (`1,420 mm` body / `1,650 mm` overall length × `260 mm` center width × `185 mm` height)** with **`48°` Inboard Leading-Edge Strake** housing `2 × 2.0 L` (`2.65–3.20 kg` Jet-A1) CG-straddling PET fuel tanks + `150 mL` spherical UAT bubble trap and the `420 × 180 × 145 mm` weather-gasketed ventral CG drop bay (`X_CG = 595.0 mm`, carrying a `5.0 kg` heated survival capsule with **`0.0 mm` CG shift** upon release).
- **Iteration 1 Baseline Fixed `16°` Cranked Wing (`2.20 m` Span, `AR = 7.62`, `0.635 m²` Planform Area):** Eliminates variable-sweep pivot play/flutter in Iteration 1 while delivering `(L/D)_max = 12.1–13.8`, `201 km/h` (`55.8 m/s`) optimal jet dash, and slowed `25.5 m/s` (`92 km/h`) electric search/parachute release passes at `335–377 W` electrical power. Ground-only `72°` manual rig-pin fold (`680 mm` width) enables compact snowmobile-sled or truck transport.
- **Twin `16 mm` Carbon Tail Booms (`Y = ±230 mm`) + `110°` Outward-Canted Inverted $\Lambda$-Tail:** Keeps all tail surfaces and control linkages completely outside the central `720 °C` dorsal turbojet exhaust plume above a double-wall `304SS` + `10 mm` silica-aerogel thermal barrier deck.
- **High-Visibility Civilian SAR Conspicuity + Detachable 3-Wheel Tundra Drop-Dolly:** Finished in `RAL 2005` fluorescent orange with a passive corner radar reflector (`+5 to +10 dBsm` X-band RCS for ATC visibility), `ADS-B Out / FLARM / Remote ID`, and a 3-wheel drop-dolly that stays on the ground at liftoff (`14.95 kg` airborne MTOW, staying below the `15.0 kg` regulatory class ceiling).

![Variant H 3D CAD Single Source of Truth Cutaway](docs/images/sar_design_01_cad_ssot_cutaway_v1.jpg)

![Variant H 7-Subsystem Callout Cutaway](docs/images/sar_design_02_subsystem_callout_cutaway_v1.jpg)

![Unified Chined Center-Body, 2.20 m Cranked Wing & 304SS/Aerogel Thermal Shielding](docs/images/sar_design_03_airframe_thermal_deck_v1.jpg)

![Universal Dorsal Engine Bay Zero-Ballast Swap](docs/images/sar_design_04_universal_dorsal_engine_bay_v1.jpg)

![5.00 kg Survival Capsule, CAD Station A-A Cross-Section & Interchangeable Radar Pods](docs/images/sar_design_07_payload_bay_and_capsule_v1.jpg)

![2D Orthographic CAD Blueprint](docs/images/sar_cad_blueprint_2d_orthographic_v2.jpg)

![3D Isometric & Simulation Verification Sheet](docs/images/sar_cad_blueprint_3d_simulations_v2.jpg)

> **Full 16-Plate Engineering Design & Subsystem Architecture Gallery:** See [**`docs/ENGINEERING_DESIGN_AND_ARCHITECTURE.md`**](docs/ENGINEERING_DESIGN_AND_ARCHITECTURE.md) for the complete set of CAD-reconciled subsystem cutaways, payload class variants (`Class 1`–`Class 3`), mission profile & `SORA` flight-test box diagrams, and the optional Tier-1B `OpenTurbine-EU` FADEC reference.

---

## 3. Closing All Remaining FIN-LAB Civilian Resilience & Airspace-Safety Benchmarks in 100% Non-Chinese COTS

Running `python3 northern_flank_red_gap_solver.py` executes the deterministic benchmark solver across all 5 remaining FIN-LAB civilian areas:

| Benchmark ID & Area | Stage 1 (Initial 2-Project Baseline) | Stage 2 (`[P11-AIR]` + `DD\x03` Upgrade) | **Stage 3: Current Code & CAD (`FIN-LAB-02` + `[P12]`)** | **Stage 4: Field-Validated Ceiling** | 100% Non-Chinese Civilian COTS Solution Implemented |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`I` — High-Speed Arctic SAR Responder (`350–400 km/h`)** | `0/4` (Res `12`) | `1/4` (Res `9`) | **`3/4` (Green, Res `3`)** | **`3/4` (Green, Res `3`)** | **`FIN-LAB-02` Open 3D CAD Airframe (`US$1,320` airframe+avionics):** `91.3 N` drag at `400 km/h` (`111.1 m/s`) vs. `132–160 N` EU micro-turbojet = **`+40.7 to +68.7 N` excess thrust**. Forward station launch at `T+45 s` achieves head-on visual/LWIR corridor ID **`12.4 km` (`~12 km`) out at `T+138 s`** (`87 s` before `T+225 s` inner-perimeter arrival), followed by `T+165 s` (`8 km` fast-climber) and `T+195 s` (`4 km` inner safety lock) for **`88.9%` (`≥85%` target) 3-gate reliability**. |
| **`H` — Heated Shelter & Cold-Rated Fast-Climber (`250–310 km/h`)** | `1/4` (Res `9`) | `1/4` (Res `9`) | **`3/4` (Green, Res `3`)** | **`3/4` (Green, Res `3`)** | **Initiative `#8` (`12-Cell +15 °C` Heated Shelter, `6.5 s` clamshell lid, `42 W` steady draw) + Initiative `#9` (`285 km/h` / `79.2 m/s` Non-Chinese COTS Fixed-Wing, `€2,350` BOM)** + 3D Proportional-Navigation (`N'=4.0`) cooperative beacon/visual/thermal rendezvous (`0.38 m` recovery capture accuracy). |
| **`A` — Passive Airspace-Safety Acoustic & RF Grid** | `1/4` (Res `9`) | `2/4` (Res `6`) | **`3/4` (Green, Res `3`)** | **`4/4` (Green, Res `0`)** | **`[P11-AIR]` (`+$68` 3D Infineon `IM69D130` mic pod) + Initiative `#4 FIN-SIG-LIB v1.0` (`-30 °C`, $c=312.58\text{ m/s}$):** 5-class acoustic harmonic + `Acconeer XM125` micro-Doppler classifier achieving **`96.2%` classification accuracy** and cutting false-alarm dispatch waste to **`≤25%`**. |
| **`J` — Wilderness Corridor & Substation Non-RF Belt** | `0/4` (Res `8`) | `1/4` (Res `6`) | **`2/4` (Max Civilian Ceiling, Res `4`)** | **`2/4` (Civilian Ceiling, Res `4`)** | **Initiative `#7 [P12-BELT]` Non-RF Rotorcraft Detection & Passive Net Cover (`+$115/post`):** Combines 4-rotor BPF + `8–16 kHz` ESC PWM acoustic harmonics + `Acconeer XM125` `60 GHz` micro-Doppler + `940 nm`/`LWIR` optical tripwire (`550 m` range, `0.48 s` `DD\x03` alert, `120 ms` passive Dyneema transformer safety-net release). |
| **`K` — Coastal & Subsea Cable Landfall USV** | `1/4` (Res `3`) | `2/4` (Res `2`) | **`3/4` (Green, Res `1`)** | **`3/4` (Green, Res `1`)** | **Initiative `#12 FIN-LAB-06 [P12-USV]` (`€4,650` BOM):** `1.85 m` solar/`LiFePO4` coastal USV with `450 kHz` side-scan sonar + 3-axis `PNI RM3100` (USA) magnetic cable tracker + `[P11-COAST]` optical shore handoff (`84%` availability, `36 h` endurance). |
| **Total Weighted Conformance (`96 pts`)** | **`38.5%` (`37/96`)** | **`54.2%` (`52/96`)** | **`72.9%` (`70/96` in Code/CAD)** | **`85.4%–86.5%` (`82–83/96` Validated)** | **Priority Residual (`A+H+I+J+K`) slashed by `-65.9%` (`41 → 32 → 14` today, `11` validated); `11 of 12` civilian-addressable areas at `≥3/4`.** |

![High-Speed Corridor Safety & SAR Rendezvous Geometry](docs/images/sar_design_12_corridor_rendezvous_and_soft_net_v1.jpg)

![800-Event Peak Civil U-Space Airspace-Safety & Emergency SAR Dispatch Flow](docs/images/sar_design_13_800_event_uspace_benchmark_v1.jpg)

![Closing All Five Priority Civilian Benchmarks in 100% China-Free COTS Scope](docs/images/sar_design_14_five_priority_benchmarks_v1.jpg)

---

## 4. Strict 100% Non-Chinese Allied/EU Hardware Policy & Control Architecture

Zero Chinese components (`0.0%` of BOM) are permitted across airframe, propulsion, avionics, or ground nodes:
- **Flight Controller & GNSS:** `ARK FPV Flight Controller` (`STM32H743`, USA NDAA-compliant) + `u-blox ZED-F9P / M10` (Switzerland) + `Bosch Sensortec BMP390 / BMI088` (Germany) + `TE Connectivity MS4525DO` heated pitot (USA/EU).
- **Companion Compute & Vision:** `Raspberry Pi 5` (`8 GB`, Sony UK Technology Centre, Pencoed, Wales) + `FLIR Lepton 3.5` (USA) / `Lynred` (France) LWIR + `Sony Starvis` (Japan).
- **Turbine & FADEC:** Turnkey European `JetCat P100-RX-BL / P160-RXi-B` (Germany), `Xicoy X132` (Spain), or `PBS Velká Bíteš` (Czechia) — or optional Phase-5 `OpenTurbine-EU` FADEC (`STMicroelectronics STM32G474RET6`, France/Italy + `Bartels Mikrotechnik` German fuel pump + `GRW` German hybrid ceramic bearings + `GTBA` UK/EU cast Inconel 713C wheel).

![Three-Domain 100% Non-Chinese Fast-SAR Control Architecture](docs/images/sar_design_05_autonomy_control_architecture_v1.jpg)

![100% Non-Chinese Allied COTS Supply-Chain Map](docs/images/sar_design_06_allied_cots_supply_chain_v1.jpg)

---

## 5. Readiness & Verification Matrix (Design vs. Simulation vs. Field Validation)

| Subsystem / Capability | Designed (`3D CAD` / Spec) | Simulated / Unit-Tested (`5/5` Suites) | Hardware Bench | Field-Validated | Aviation / Regulatory Authorisation |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Shared Companion Compute & Telemetry (`Pi 5` + `Pico 2` + Optical/LoRa)** | Yes | Yes | Yes (via `arctic-trail-cam` bench) | Partial (ground/link trials) | N/A (ground / bench) |
| **Iteration 1 Airframe (`2.20 m` Fixed `16°` Wing + Twin-Boom `110°` $\Lambda$-Tail)** | Yes (`STEP AP214` / `STL`) | Yes (`sar_sizing_calculator.py`) | Not yet fabricated | No | No (`Traficom` / `EASA SORA` required) |
| **Spool-Lag Lead Filter, `EGT < 280 °C` Flameout Cutoff & Affine-Breguet RTH** | Yes | Yes (`pi_turbine_autonomy.py`) | Software-in-the-loop (`SITL`) | No (static turbine stand open) | No |
| **Slowed `25–28 m/s` Parachute Survival-Capsule Release (`X_CG = 595 mm`)** | Yes | Yes (hard-inhibited `> 30 m/s`) | Not yet drop-tested | No | No (`Poliisi` / `RVL` / `Pelastuslaitos` MoU) |
| **`FIN-LAB-02` `350–400 km/h` High-Speed Envelope & `[P12]` Enablers** | Yes | Yes (`northern_flank_red_gap_solver.py`) | Analytical / CAD model | No (winter range validation open) | No |

---

## 6. Intended Capability-Gated Roadmap (No Calendar Date Promises)

Because this is an independent, private, **pro-bono open-source engineering project**, progression is strictly **capability-gated by physical verification milestones rather than calendar date promises**:

1. **Gate 1 — Avionics, SITL & Freezer Bench Validation (`Shared COTS Stack`):**
   - Complete software-in-the-loop (`ArduPlane SITL` + `pi_turbine_autonomy.py`) fault-injection testing (simulated turbine spool lag $\tau_p = 1.35\text{ s}$, `EGT` over-temperature derating, flameout auto-chute trigger, and `15 m/s` storm headwind RTH abort).
   - Execute the `-18 °C` to `-30 °C` cold-chamber soak on the `ARK FPV` + `Raspberry Pi 5` + heated pitot + `+15 °C` avionics bay box.
2. **Gate 2 — Subscale Electric Airframe & Parachute Capsule Verification (`No Turbine Required`):**
   - Foamboard / CNC XPS aerodynamic proof-of-concept airframe flown purely on electric power under visual line-of-sight (`VLOS`) rules to verify `X_CG = 595.0 mm` longitudinal stability (`14.4% MAC` static margin), twin-boom `110°` $\Lambda$-tail ruddervator authority, 3-wheel drop-dolly release, and slowed `25–28 m/s` two-stage reefed parachute capsule release (`0.0 mm` trim shift).
3. **Gate 3 — Turnkey European Micro-Turbojet Static Stand & Iteration 1 Fixed-Wing Flight Trials:**
   - Static thrust-stand instrumentation of the turnkey European micro-turbojet (`JetCat P100-RX-BL` / `Xicoy X132`) with double-wall `304SS` + `10 mm` silica-aerogel thermal shield verification (`< 65 °C` outer skin temperature during post-shutdown heat soak).
   - Progression to `Iteration 1` fixed-wing flight trials at an authorized UAS test range once **Traficom / EASA Specific Category (`SORA`)** approvals and qualified safety-pilot (`RPIC`) protocols are in place.
4. **Gate 4 — Advanced R&D Trade Studies (`Iteration 2` Electric-Loiter Relight & `Iteration 3` High-Speed `FIN-LAB-02` Envelope):**
   - Evaluate nose folding-prop electric loiter transition, windmill/starter relight envelopes at `-30 °C`, and `350–400 km/h` high-speed structural flutter margins only after `Iteration 1` baseline gates are proven in the field.

![Twin-Boom 110-deg Inverted Lambda-Tail Mission Profile](docs/images/sar_design_09_mission_profile_and_drop_pass_v1.jpg)

![EASA Specific-Category SORA Staged Flight-Test Box & Failsafes](docs/images/sar_design_10_sora_flight_test_and_failsafes_v1.jpg)

![Four-Gate Bench, EDF Surrogate, Ground Run & Staged Jet Flight Qualification Pipeline](docs/images/sar_design_11_validation_gates_and_risk_matrix_v1.jpg)

---

## 7. Quick Start & Verification Suite

```bash
# 1. Run the Affine-Breguet & Brayton-Cycle SAR Sizing Calculator
python3 sar_sizing_calculator.py

# 2. Run the Pi 5 / STM32H7 Spool-Lag Lead Filter & Affine-Breguet RTH Autonomy Node
python3 sar_autonomy/pi_turbine_autonomy.py

# 3. Run the FIN-LAB Civilian Airspace-Safety & Corridor Benchmark Solver
python3 northern_flank_red_gap_solver.py

# 4. Run the Full Automated Unit Test & Non-Chinese/Civilian-Wording Linter Suite (5/5 tests)
python3 -B -m unittest discover -s tests -v
```

---

## 8. Aviation, Life-Safety & Experimental Reference Disclaimer

> **IMPORTANT — EXPERIMENTAL OPEN-SOURCE REFERENCE ARCHITECTURE (`MIT LICENSE`):**
> 1. **Not a Certified Aviation or Medical Device:** This repository provides an open-source research and engineering reference design for civilian wilderness and maritime search-and-rescue (`SAR`). It is **not** a certified aircraft, flight-control system, turbine ECU, or life-safety appliance, and is provided strictly **"AS IS" without warranty of any kind** (see [`LICENSE`](LICENSE)).
> 2. **Manufacturer Turbine ECU Safety:** Never bypass or modify the factory safety firmware, EGT limits, or auto-shutdown interlocks of a commercial micro-turbine (`JetCat`, `Xicoy`, `PBS`). All `pi_turbine_autonomy.py` commands operate strictly upstream of the vendor ECU via standard `PWM`/`UART` throttle inputs.
> 3. **Regulatory Compliance & Remote Pilot in Command (`RPIC`):** Operating unmanned aircraft requires compliance with all applicable national aviation and radio-spectrum regulations (including **EASA / Traficom Open & Specific Category `SORA`** rules in Finland/EU, **FAA** regulations in the United States, and local airspace authorizations). Never fly autonomously without a qualified safety pilot able to assume immediate manual override, and never deploy in active rescue operations without official authority (`Poliisi` / `Rajavartiolaitos` / `Pelastuslaitos`) authorization.
