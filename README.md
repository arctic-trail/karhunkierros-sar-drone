# Karhunkierros SAR & "Digitaalinen Autiotupa" (`v1.6-Round2-Multi-Model-Hardened`) — Autonomous Wilderness Rescue Drone System

![Karhunkierros SAR — Koko pelastusketju vaihe vaiheelta (1–5)](docs/images/karhunkierros_pelastusketju_5_vaihetta.jpg)

![Karhunkierros SAR — Isometrinen maasto- ja käyttönäkymä (Vaiheet 1–5 käytännössä)](docs/images/karhunkierros_sar_isometrinen_maastonakyma.jpg)

> **100% SHARED CAMERA & COLLECTOR STACK WITH [`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam) + ZERO CUSTOM PCBS**
> - **Single Unified Trail Camera Product:** The ground camera node (`pi5_sender_node/`, `pico_gatekeeper/`) and collector hub (`collector_hub/receiver_hub.py`, `collector_hub/subghz_nlos_relay.py`, `collector_hub/dashboard_server.py`, `collector_hub/ui/`) are **100% shared with [`arctic-trail/arctic-trail-cam`](https://github.com/arctic-trail/arctic-trail-cam)** so there is only one trail camera hardware/software product to build and maintain.
> - **100% Snap-In COTS Hardware (Zero Custom PCBs):** Both the ground camera and the SAR drone (`Holybro X500 V2` + `Pixhawk 6C` + `Raspberry Pi 5` + `USB Thermal/Starvis` + `Benewake TF02-Pro 40m IP65 LiDAR` + `MicoAir MTF-02P / Matek PMW3901 Optical Flow` + `8,000 mAh 4S2P 14.8V (118.4 Wh) Ultra-Low-Temp Li-Ion`, **`~€1,189`**) assemble in `~2.5 hours` using standard `JST-GH`, `STEMMA QT / Qwiic`, `USB-C UVC`, and `XT60` connectors with **zero custom circuit boards**.

## Key Documentation & Architecture Guides

1. **[Karhunkierros SAR Pro Bono -konseptimuistio (PDF — All Images Embedded)](docs/KARHUNKIERROS_PRO_BONO_SAR_BRIEF_FI.pdf)** | **[Markdown Source](docs/KARHUNKIERROS_PRO_BONO_SAR_BRIEF_FI.md)** — *Tiettömän taipaleen pelastusketju (Vaiheet 1–5), 3D-isometrinen maastonäkymä & suunnittelu, josta tietosuojavaltuutettukin tykkää.*
2. **[Master Design Evolution, Trade-Off Audit & Stabilization Log (`v1.6-Round2-Multi-Model-Hardened`)](docs/DESIGN_EVOLUTION_AND_STABILIZATION_LOG.md)** — *Chronological log of all 16 design iterations, independent Round-1 and Round-2 multi-model audit remediation (`F01`–`F44`), why we reject custom PCBs in favor of 100% snap-in COTS parts, and the `€1,189` plug-and-play BOM.*
3. **[Comprehensive Technical & Engineering Guide (EN/FI)](docs/AERIAL_OBSERVATION_DRONE_GUIDE.md)** — *Full mathematical, hardware, 65-byte MAVLink v2 (#84), multi-drone swarm, 48h ephemeral ring buffer, Poronhoitolaki compliance, and Finnish ETRS-TM35FIN / Rajavartiolaitos aviation coordinate specification.*

## Quick Verification & CLI Commands

```bash
# Run all 27 automated unit test suites across all 4 test files (24 SAR Drone tests + 3 shared arctic-trail-cam suites)
python3 -B -m unittest discover -s tests -v

# Run the interactive Guided Bench Doctor (including Stage 5 SAR Drone Companion Bench Check)
python3 -B run_guided_bench_doctor.py --self-test --drone-bench

# Run standalone SAR Drone Companion Hardware Bench Check & export 37-parameter ArduCopter 4.5+ .param file
python3 -B collector_hub/drone_observer.py --mode bench-check --export-params /tmp/pixhawk6c_sar.param

# Simulate "Uber-for-SAR" Open-Alert Dispatch Marketplace, Roofed Auto-Stations & Elastic Pull-Guidance
python3 -B collector_hub/drone_observer.py --mode dispatch-marketplace

# Simulate Aerial Lantern & Autiotupa Trail Guide ("Opaslyhty: Seuraa minua autiotuvalle")
python3 -B collector_hub/drone_observer.py --mode lantern-guide

# Simulate Split Tourist Group SAR & Onboard Self-Guidance
python3 -B collector_hub/drone_observer.py --mode sar-tourist-group

# Simulate Multi-Drone Boustrophedon Grid Search
python3 -B collector_hub/drone_observer.py --mode grid-search --num-drones 4
```

## "Uber-for-SAR" Open-Alert Dispatch Marketplace & Automated Roofed Shelters (`SARDispatchMarketplaceCoordinator`)

When a verified `112` / `inReach` / Trail-Post `SOS` alert is issued, the coordination system broadcasts an **Open SAR Task** (`OPEN_FOR_UNIT_ACCEPTANCE`) across two classes of units:
1. **Mobile Patrol Drone Units (`MOBILE_PATROL_UNIT` — e.g., Police vans, Border Guard patrols, Vapepa sleds):** Field crews see the open alert on their vehicle terminal (like an Uber driver seeing a nearby ride request) with distance, flight ETA, and coordinates, and tap **`[Accept Task]`**.
2. **Automated Roofed Wilderness Stations (`AUTOMATED_ROOFED_NEST` — `+10 °C` weather-sealed roofed shelters):** Protect stationed drones under a motorized snow/rain roof. When set to **`AUTO_ACCEPT_GEOFENCE`** mode, stations automatically accept alerts relevant to their location (`<= 14 km`), open their roof hatch, launch autonomously, close the roof while away, deliver the `+42 °C` berry-electrolyte & thermal-blanket package (`15 m` safe offset), **follow and "pull" the hiker to the nearest *autiotupa* at `28 m` above the treetops (`compute_elastic_pull_guidance_vector`)**, and autonomously return to dock and recharge under the roof.
3. **Multi-Unit Auto-Prioritization & Human Control Panel:** If multiple mobile units and roofed stations accept the same alert, the system auto-prioritizes them by Flight ETA (`45%`), Winter Battery Margin (`25%`), Sensor/Payload Capability (`15%`), and Readiness (`15%`), awarding `#1 PRIMARY_SAR_RESCUER` and `#2 SECONDARY_BACKUP_INTERCEPT` — while giving the human coordinator full control via the web dashboard (`collector_hub/ui/index.html`) to switch between **Auto-Prioritize**, **Manual Approval Only**, or **Human Override** (`Assign #1`, `Hold Launch`, `Force Immediate RTB`).

## Aviation, Life-Safety & Experimental Reference Disclaimer

> **IMPORTANT — EXPERIMENTAL OPEN-SOURCE REFERENCE ARCHITECTURE (`MIT LICENSE`):**
> 1. **Not a Certified Aviation or Medical Device:** This repository provides an open-source research and engineering reference design for civilian wilderness search-and-rescue (SAR). It is **not** a certified aircraft, flight-control system, or life-safety appliance, and is provided strictly **"AS IS" without warranty of any kind** (see [`LICENSE`](LICENSE)).
> 2. **Regulatory Compliance & Remote Pilot in Command (`RPIC`):** Operating unmanned aircraft requires compliance with all applicable national aviation and radio-spectrum regulations (including **EASA / Traficom Open & Specific Category SORA** rules in Finland/EU, **FAA Part 107** in the United States, and local airspace authorizations). Never fly autonomously without a qualified safety pilot able to assume immediate manual override, and never deploy in active rescue operations without official authority (`Poliisi` / `Rajavartiolaitos` / `Pelastuslaitos`) authorization.

