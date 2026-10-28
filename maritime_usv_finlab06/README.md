# Arctic & Baltic Maritime Autonomy & Subsea Cable Watch Stack (`arctic-maritime-usv` / `FIN-LAB-06`, `v0.1` Concept Release)

> **Open-source, 100% Non-Chinese (`EU / UK / CH / US Allied`) Coastal & Offshore Subsea Cable-Route Survey USV, Tethered Fiber-Optic Seabed Sonde, Amphibious Winter Ice-Skimmer & Landfall Watch Stack (`+$160` bench-reusing pontoon surrogate / `€4,650` `1.85 m` solar catamaran / `€11,850` `3.60 m` Sea State 5 wave-piercer). A private, pro-bono free-market COTS build. 🇫🇮🇪🇪 Finnish & Baltic civilian engineering.**
>
> * **GitHub Topics:** `ardurover` · `ardupilot` · `usv` · `maritime-autonomy` · `colregs` · `subsea-cable` · `sidescan-sonar` · `magnetometer` · `ais` · `gnss-denied` · `allied-cots` · `open-hardware` · `gulf-of-finland` · `baltic-sea` · `finland` · `estonia`
> * **Sister Project — Tier 1 (RF-Silent Arctic Trail & Coastal Landfall Node with 1-Way Optical Diode & `[P11-COAST]` / `[P12-BALTIC-100]`):** [`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam)
> * **Sister Project — Tier 2 (Autonomous Wilderness SAR Quadcopter & `FIN-LAB-01` Open Fusion Hub):** [`arctic-trail/karhunkierros-sar-drone`](https://github.com/arctic-trail/karhunkierros-sar-drone) *(Note: this maritime subproject is also published inside [`maritime_usv_finlab06/`](https://github.com/arctic-trail/karhunkierros-sar-drone/tree/main/maritime_usv_finlab06))*
> * **Full Maritime Engineering Charter (`O1–O7`), 5-System Architecture, 3D CAD, Hydrostatics, Sonde Physics, `P8` Sea-Trial Ladder (`8.1–8.5`), Mission `M4 Cable Watch` & 10-Point Risk Register (SSOT):** [**`docs/MARITIME_CHARTER_AND_ARCHITECTURE.md`**](docs/MARITIME_CHARTER_AND_ARCHITECTURE.md)
> * **License:** [`MIT License`](LICENSE)

> [!WARNING]
> **PROJECT STATUS & STRICT 90/10 CIVILIAN BOUNDARY DISCLAIMER (`MIT LICENSE`)**
> * **100% Civilian Intended Use (Observe, Inspect & Report Only — `0` Weapons / `0` Kinetic Effectors):** This repository provides open-source civilian engineering for **subsea power and telecommunications cable-route survey, environmental water-quality monitoring, harbour/fairway safety, and coastal search-and-rescue support**. It contains **zero** weapons, **zero** kinetic or explosive effectors, and **zero** vessel-boarding or non-cooperative interdiction mechanisms. Sovereign military C2, naval boarding, and subsea defence remain strictly outside this repository with cleared national integrators (the `10%` sovereign layer).
> * **Honest Maturity Status Today (`TRL 4–5` Shared Bench Avionics / `TRL 2–3` Maritime Hulls & Autonomy, `0.0` Sea-Trial Hours Sailed):**
>   1. **Hardware Bench-Verified Today (`TRL 4–5`):** The core electronics (`Raspberry Pi 5`, `RP2350 Pico 2`, `ARK FPV` / `Pixhawk 6C`, `100BASE-FX` single-mode optical fiber link, `8,000 mAh 4S2P Molicel P42A` battery, and dual thermal/optical cameras) are physically assembled and bench-tested in our sister repositories.
>   2. **3D CAD, `1:1 mm` Cut Sheets & Software-Simulated Today (`TRL 3`, `10/10` Automated Test Suites Passing):** The parametric `STEP AP214` / `STL` / `GLB` 3D solid CAD assembly (`cad/finlab06a_catamaran_1850mm.step`), `1:1 mm` CNC hull frame cut sheets (`.svg` / `.dxf`), 6-DoF hydrostatics & ITTC-1957 resistance simulator (`usv_hydrodynamics_6dof.py`), Charter 06 (`O1–O7`) fleet relief scheduler, COLREGs navigator, AIS dark-ship & anchor-drag acoustic correlator, winter ice-chart station shifter, and `FIN-LAB-03` littoral GNSS-denied Skerry-Lock navigator (`maritime_autonomy/baltic_maritime_autonomy.py`) pass `10/10` automated unit tests (`python3 -B -m unittest discover -s tests -v`).
>   3. **Unbuilt Physical Hulls (`0` Hulls Built, `0.0` Sea Hours Sailed):** Physical fabrication of the `1.20 m` bench-reusing surrogate (`+$160`), the `1.85 m` Prototype `P8` catamaran (`€4,650`), and the `3.60 m` offshore monohull (`€11,850`), as well as pool and sea trials (`Steps 8.1–8.5` & Mission `M4 Cable Watch`), remain to be physically executed.

---

## 1. Executive Summary: Fulfilling Finnish & Baltic Maritime Needs in Civilian Scope

Across the **Gulf of Finland**, **Archipelago Sea**, **Åland/Gotland**, and **Baltic ports**, repeated anchor-drag incidents against subsea cables and pipelines (*Balticconnector* Oct 2023, *Estlink 2* / *Eagle S* Dec 2024, *Fitburg* Dec 2025), persistent GNSS jamming/spoofing, and `80–100` winter ice days per year create an urgent need for **low-cost, persistent, 100% Non-Chinese civilian maritime surveillance and subsea inspection**.

While NATO's **Task Force X-Baltic (`TFX-B`, June 2025)** proved that uncrewed vessels cut surveillance cost to **`1/3` of crewed frigates**, `TFX-B` achieved `75%` availability for only **`8 hours/day` (`25.0%` of the 24-hour day)**. This subproject (`FIN-LAB-06`) closes that gap through five modular, 100% Non-Chinese COTS systems detailed in [**`docs/MARITIME_CHARTER_AND_ARCHITECTURE.md`**](docs/MARITIME_CHARTER_AND_ARCHITECTURE.md):

1. **`FIN-LAB-06-BENCH` (`+$160` Hardware Delta, Gate 1–2):** Mounts our **already-purchased** in-house `Pixhawk 6C`/`ARK FPV`, `Pi 5`, `Pico 2`, `4S2P Molicel`, `FLIR`/`TC001`, and `SF-T2` optical link onto a `1.20 m` twin-pontoon frame with `2×` IP68 brushless thrusters to run **Steps `8.1` (pool trim/`30°` heel)** and **`8.2` (harbour line `±1 m`)** immediately.
2. **`FIN-LAB-06A` / Prototype `P8` (`1.85 m` Solar/`LiFePO4` Catamaran, `€4,650`, Gate 3):** Fulfils **Gap Map §6B Prototype `P8` & Mission `M4 Cable Watch`** (`36 h` unattended Gulf of Finland cable survey, **`84.1%` simulated availability** vs. `>75%` target, **`0.42 m` cable CEP** via `450 kHz` side-scan sonar + aft-boom `PNI RM3100` 3-axis magnetometer).
3. **`FIN-LAB-06B` (`3.60 m` Self-Righting Wave-Piercing Monohull, `€11,850`, Gate 3–4):** Fulfils **Charter 06 Objective `O1` (`>90%` 24/7 station availability)** across `6` Gulf of Finland stations in **Sea State 5** ($H_s = 3.2\text{ m}$, `AVS = 180°` self-righting in `3.2 s`) and **Polar Night** (`148.9 h` endurance via German `EFOY Pro 2800` `110 W` DMFC), achieving **`96.2%` 24/7 fleet availability** with `14` hulls and `6.0 h` lookahead relief scheduling.
4. **`FIN-LAB-06C` (`[P12-UUV-TETHER]` `100 m` Fiber-Optic Seabed Sonde, `€2,150`) & `FIN-LAB-06D` (Amphibious *Rospuutto* Ice-Skimmer, `€1,890`):** Lowers `RM3100` + `900 kHz` sonar + optical/LWIR camera on `250 µm` `100BASE-FX` single-mode fiber below the `10–30 m` Baltic halocline to `1.5 m` above the `40–80 m` cable trench for a **`+85.6 dB` (`18,963×`) magnetic dipole gradient SNR boost**; `06D` skims across winter fast ice and slush leads (`48 km/h`) during the `80–100` ice-day winter season.
5. **`[P11-COAST]` (`+$145`), `[P12-BALTIC-100]` (`+$210`) & `[P11-COAST-2KM]` (`+$220`) Shore & Seabed Trench Nodes:** Dual-channel VHF AIS + shore radar/EO dark-ship (`>150 m` spoof) detector, under-ice seabed hydrophone with `8× 50/100 Hz` HVDC hum notch filter (`3.2 km` anchor-drag range, **`4.2 s` alert latency** vs. `≤10 min` target), and `2.2 km` Class-1 eye-safe `1550 nm` optical strait bridge.

![2D Orthographic CAD Blueprint of FIN-LAB-06A Prototype P8](docs/images/maritime_cad_blueprint_2d_orthographic_v1.jpg)

![3D CAD Isometric Mesh, GZ(phi) Self-Righting Hydrostatics, ITTC-1957 Polars & Sonde SNR Physics](docs/images/maritime_cad_blueprint_3d_hydrostatics_v1.jpg)

![Charter 06 Fleet Persistence, Winter Ice Handoff & Prototype P8 Sea-Trial Scorecard](docs/images/maritime_charter06_fleet_and_cable_watch_v2.jpg)

---

## 2. Quick-Start: Run the Simulator, CAD Builder & `10/10` Unit Test Suite

```bash
# 1. Run all 10 automated verification suites (Charter 06 O1-O7 + Prototype P8 Steps 8.1-8.5 + CAD/BOM audit)
python3 -B -m unittest discover -s tests -v

# 2. Run the Prototype P8 5-step sea-trial ladder & 6-DoF hydrostatics / cable-tracking simulator
python3 usv_hydrodynamics_6dof.py

# 3. Rebuild the 3D CAD (STEP AP214, STL, GLB), 1:1 mm SVG/DXF cut sheets & ArduRover 4.5+ param file
python3 cad/build_maritime_usv_cad.py

# 4. Regenerate the 3 high-resolution engineering blueprint plates
python3 cad/generate_maritime_blueprints.py
```

---

## 3. Repository Structure (Single Source of Truth)

| File / Directory | Responsibility |
| :--- | :--- |
| [**`docs/MARITIME_CHARTER_AND_ARCHITECTURE.md`**](docs/MARITIME_CHARTER_AND_ARCHITECTURE.md) | **Canonical Maritime Charter (`O1–O7`), 90/10 Civilian Boundary, 5-System Architecture, Sonde Physics, `P8` Sea-Trial Ladder (`8.1–8.5`), Mission `M4 Cable Watch` & 10-Point Risk Register** |
| [`cad/design_params_maritime.json`](cad/design_params_maritime.json) | Single Source of Truth (`SSOT`) dimensions, hydrostatics, mass breakdown, and 100% Non-Chinese Allied/EU BOM (`0.0%` CN) |
| [`cad/build_maritime_usv_cad.py`](cad/build_maritime_usv_cad.py) | Generates `finlab06a_catamaran_1850mm.step` (`STEP AP214`), `.stl`, `.glb`, `1:1 mm` `.svg`/`.dxf` CNC cut sheets, and `ark_fpv_ardurover_45_usv.param` |
| [`cad/generate_maritime_blueprints.py`](cad/generate_maritime_blueprints.py) | Renders the 2D orthographic, 3D hydrostatics/sonde physics, and Charter 06 scorecard plates in `docs/images/` |
| [`maritime_autonomy/baltic_maritime_autonomy.py`](maritime_autonomy/baltic_maritime_autonomy.py) | Implements `GulfOfFinlandReliefScheduler` (`O1`), `COLREGsMaritimeNavigator` (`O2`), `FintrafficAISDarkShipCorrelator` (`O3`), `WinterIceSeasonAdaptationPlanner` (`O4`), and `LittoralGNSSDeniedSkerryNavigator` (`O5`) |
| [`usv_hydrodynamics_6dof.py`](usv_hydrodynamics_6dof.py) | 6-DoF hydrostatics ($GM_T$, $GZ(\phi)$), ITTC-1957 resistance polars, `[P12-UUV-TETHER]` magnetic dipole SNR physics, and `P8` sea-trial ladder (`8.1–8.5`) |
| [`tests/test_maritime_usv_suite.py`](tests/test_maritime_usv_suite.py) | `10/10` automated unit tests verifying every Charter 06 (`O1–O7`) and Gap Map (`P8` / `M4`) requirement |
