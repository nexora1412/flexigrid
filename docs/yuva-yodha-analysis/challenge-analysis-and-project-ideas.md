# Yuva Yodha Energy Tech Hackathon 2026 — Challenge Analysis & Project Playbook
*Organiser: Schneider Electric India | Source: yuvayodhatech.com/challenges*

---

## Executive Summary — Which Challenge Should You Pick?

| Challenge | Judging Heat | Skill Profile | Hardware Needed? | Demo-ability | Recommended For |
|---|---|---|---|---|---|
| 01 Agriculture | 🔥🔥🔥 Very crowded | App + ML + simple IoT | Optional (can simulate) | ★★★★☆ | Teams with Android/ML skills |
| 02 Buildings | 🔥🔥 Medium | Full-stack + data viz + ML | No (simulators/synthetic data OK) | ★★★★★ | Software-heavy teams |
| 03 Grid | 🔥 Less crowded | Data science + optimisation + dashboards | No | ★★★★☆ | Analytical/EEE-mix teams ⭐ |
| 04 Manufacturing | 🔥🔥 Medium | IoT + edge + dashboards | 1 cheap sensor kit helps | ★★★★☆ | Teams with hardware comfort |

**Strategic insight:** Challenge 01 (Agriculture) will attract the most teams — harder to stand out. **Challenge 03 (Grid Reliability) is the least crowded and most "Schneider Electric-native"** (their core business is energy management + grid tech). A polished grid-flexibility or demand-response MVP is the highest leverage pick. Challenge 02 is the safest software-only pick with a killer live demo potential.

---

## CHALLENGE 01 — Sustainable Agriculture
**Tagline:** Energy, Water & Productivity | "Feeding a billion people cleanly, efficiently, and resiliently."

### What judges explicitly want
1. **Reduce energy and water intensity** — smarter irrigation scheduling, efficient pumping
2. **Minimize post-harvest losses** — low-cost sensing, controlled storage, logistics analytics (15–20% losses today!)
3. **Empower the smallholder** — vernacular (Marathi/Hindi), voice-first, works on cheap phones + poor connectivity
4. **Climate resilience** — data-driven adaptation to erratic rainfall/heat

### Reality check
- 40%+ of India's workforce is in agriculture; 90% of freshwater goes to farms. Big impact story.
- Crowded track — your differentiator must be **energy angle** (most teams forget it and just build another "crop advisory app"). The challenge is *Energy Tech* first.

### 💡 Project Ideas

#### Project 1A — "SolarPump Scheduler" (Energy + Water INTENSITY focus) ⭐
**Concept:** An offline-first app + optional ESP32 controller that tells farmers *when* to run their pump based on solar generation forecast, soil moisture need, and electricity tariff windows — cutting both energy and water waste.
- **Features:**
  - Irrigation schedule optimized against (a) IMD weather/rain forecast, (b) crop water requirement, (c) solar availability / off-peak tariff hours
  - WhatsApp/SMS bot interface in Marathi + voice notes (no literacy needed)
  - Optional: ₹800 ESP32 + soil-moisture sensor live demo on a plant pot
  - Dashboard showing litres of water saved + kWh shifted to solar hours
- **Stack:** Python (FastAPI) + Telegram/WhatsApp bot + ESP32 (optional) + Prophet/sklearn for moisture-evapotranspiration model + SQLite
- **Demo trick:** Live pot-plant demo — pour water, sensor reads, app updates recommendation in real time.
- **Why it wins:** Hits *all four* judging criteria with the energy angle front and center.
- **Difficulty:** 🟡 Medium | **Team fit:** App dev + basic ML + optional maker

#### Project 1B — "ColdLink" Post-Harvest Loss Guardian
**Concept:** Low-cost monitoring + analytics for village-level produce storage — tracks temperature/humidity/ethylene of stored produce, predicts spoilage risk, and matches surplus to nearby buyers/mandis *before* it rots.
- **Features:** Spoilage-risk score per crate; "sell-by routing" (nearest mandi with best price via Agmarknet/eNAM data); SMS alerts; solar-powered sensor node concept
- **Stack:** Node/Python backend + DHT22/MQ-3 sensors (or simulated) + eNAM price data + simple React dashboard
- **Why it wins:** Post-harvest loss (15–20%) is explicitly named in the brief; few teams touch it.
- **Difficulty:** 🟡 Medium

#### Project 1C — "MandiMind" — Crop-Choice Decision Support
**Concept:** Vernacular voice assistant that recommends *what to grow* based on local mandi demand trends, water availability forecast, and risk — so farmers don't all plant the same crop and crash prices.
- **Stack:** Open Agmarknet/data.gov.in mandi price datasets + IMD rainfall data + LLM-powered Marathi voice interface
- **Difficulty:** 🟢 Easy-Medium (pure software)

---

## CHALLENGE 02 — Smart Buildings
**Tagline:** Energy Efficiency & Occupant Experience | "Making every square metre smarter, greener, and more comfortable."

### What judges explicitly want
1. Cut energy waste *measurably* without sacrificing comfort
2. Improve occupant experience (thermal comfort, IAQ, lighting)
3. Data-driven management — actionable visibility for owners
4. **Grid integration** — shift flexible loads off-peak, demand-response readiness

### Reality check
- Buildings = 33% of electricity consumption. Real-time performance data is usually missing → even a good *visibility + nudge* product is valuable.
- Perfect software-only track. You can generate a synthetic building dataset and still demo beautifully.

### 💡 Project Ideas

#### Project 2A — "WattWise" Plug-Level Energy Intelligence ⭐ (Top software pick)
**Concept:** AI that disaggregates a building's single energy meter into appliance-level insights ( NILM — Non-Intrusive Load Monitoring), flags waste ("AC ran 3 hrs in empty rooms"), and auto-suggests demand-response actions.
- **Features:**
  - Upload smart-meter CSV (or live simulated feed) → appliance breakdown
  - Waste detector: after-hours HVAC, phantom loads, inefficient scheduling
  - "Shift-this-load" panel quantifying ₹ saved by moving loads off-peak
  - Occupant comfort score (temperature/CO₂ inrush simulation)
- **Stack:** Python + pretrained NILM toolkit (nilmtk) or a small LSTM autoencoder + React dashboard + synthetic data from public datasets (UK-DALE / AMPds / Pecan Street)
- **Demo trick:** Two phones/laptops — one "building simulator" streaming readings, one dashboard reacting live. Judges love real-time.
- **Why it wins:** Ticks every bullet in the brief; the demand-response panel = the "grid integration" requirement most teams will skip.
- **Difficulty:** 🟠 Medium-Hard (ML), but synthetic data removes risk

#### Project 2B — "ComfortIQ" — Campus/Office Comfort + Efficiency Twin
**Concept:** QR-code based occupant feedback ("too hot/too cold/stuffy") fused with room sensor data (or BMS export) to tune HVAC setpoints — classic 20-30% HVAC savings story with wellbeing metrics.
- **Features:** Heatmap of comfort complaints, setpoint recommendation engine, energy-vs-comfort tradeoff slider for facility managers
- **Stack:** Simple PWA + FastAPI + scikit-learn + floor-plan SVG visualisation
- **Demo trick:** Put QR codes on the judges' table — they scan, submit comfort votes, watch the dashboard adapt live. Extremely memorable.
- **Difficulty:** 🟢 Easy-Medium | Best effort-to-wow ratio in the whole hackathon

#### Project 2C — "Zero-Waste Retrofit Recommender"
**Concept:** Audit-lite tool: building manager inputs floor area, equipment list, and bills → model ranks retrofit options (LED, VFDs, envelope sealing, scheduling) by payback period and emission cuts.
- **Stack:** Rules + regression models + clean UI | **Difficulty:** 🟢 Easy

---

## CHALLENGE 03 — Grid Reliability ⭐⭐ (BEST STRATEGIC PICK)
**Tagline:** Renewable Intermittency | "Making clean power dependable, neighbourhood by neighbourhood."

### What judges explicitly want
1. Bridge intermittency gaps — keep power reliable when renewables dip
2. **Local and manageable** — neighbourhood/district scale, minimal grid intervention
3. **Genuinely affordable** — viable for low-income urban/peri-urban communities
4. **Support the DISCOM** — forecasting/demand-response signals, reduce technical losses

### Reality check
- This is Schneider Electric's *home turf* (their solutions page literally links Power & Grid here). Judges can immediately map your solution to their products.
- Fewer teams have the confidence to touch grid + optimisation → much better odds.
- All-simulatable: open datasets exist for solar generation (NREL, Kaggle solar) and load curves (Pecan Street, UCI household power, CEA India reports).

### 💡 Project Ideas

#### Project 3A — "FlexiGrid" Community Demand-Response Engine ⭐⭐ (Flagship pick)
**Concept:** A neighbourhood "energy traffic controller": forecasts next-day solar vs. feeder load, then automatically schedules *flexible community loads* (water heaters, pumps, EVs, common-area cooling) into solar-rich hours — and pays participants micro-rewards (₹ credits) for shifting.
- **Features:**
  - Solar generation forecast (weather API in → PV model out)
  - Feeder load forecast (LSTM/Prophet on open load data)
  - **Optimiser:** shifts deferrable loads to minimise renewable-curtailment and peak imports (linear programming via PuLP/OR-Tools — visually impressive)
  - Community dashboard: "Your society shifted 42 kWh off-peak, saved ₹310, avoided 34 kg CO₂"
  - DISCOM view: feeder-level flexibility report + loss-reduction hints
  - Gamified fairness: rotating participation so no household is always inconvenienced → directly answers the *affordability/equity* criterion
- **Stack:** Python + Prophet/LSTM + PuLP (LP optimisation) + streamlit/react dashboard + MQTT-simulated device feed
- **Demo trick:** Live "grid storm" button — simulate a cloud bank passing (solar drops 60%) and watch the optimiser re-balance the neighbourhood in real time. Jaw-dropping demo.
- **Why it wins:** Hits *all four* judging criteria; namedrops the DISCOM angle; optimisation + forecasting shows real technical depth; the equity/reward layer shows product maturity.
- **Difficulty:** 🟠 Medium-Hard | **Team fit:** 1 data-science person + 1 full-stack person

#### Project 3B — "SunCast" Hyperlocal Solar Nowcasting
**Concept:** 15-min-ahead solar generation forecast for rooftop clusters using sky-image analysis (cheap camera) + satellite/weather data, feeding alerts to societies/battery systems before dips.
- **Stack:** OpenCV + CNN on sky images (or all-software using Open-Meteo satellite nowcast only) + alert API
- **Difficulty:** 🟠 Medium-Hard | Great if someone loves computer vision

#### Project 3C — "GridGuard" Feeder Anomaly & Theft/Loss Detector
**Concept:** Analyse feeder smart-meter data to flag technical losses, overloading risk, and abnormal consumption — an early-warning console for DISCOMs.
- **Stack:** Isolation Forest / autoencoders + geospatial feeder map UI
- **Why it wins:** "Reduce technical losses" is literally in the brief; anomaly detection is well-trodden (low risk).
- **Difficulty:** 🟡 Medium

---

## CHALLENGE 04 — Smart Manufacturing
**Tagline:** Industrial Energy & Process Efficiency | "Decarbonising the factory floor without compromising competitiveness."

### What judges explicitly want
1. Reduce *specific energy consumption* (kWh per unit of output)
2. Real-time visibility via **affordable, easy-to-deploy** tools (remember: SMEs!)
3. Quantify decarbonisation opportunities (fuel switching, renewable integration)
4. Viable for small manufacturers with limited capital

### Reality check
- 35–40% of India's energy goes to industry; energy = 15–30% of production cost.
- SME framing is everything: a ₹500-crore-plant solution will *lose* to a ₹5,000-sensor solution.
- Demo hack: bring a ₹1,000 clamp-sensor/ESP32 or just simulate a motor/compressor load from public data.

### 💡 Project Ideas

#### Project 4A — "FactoryPulse Lite" — ₹5k SME Energy Doctor ⭐
**Concept:** A plug-and-play kit: one current sensor on the main incomer + tiny edge box → the software learns machine "fingerprints" (idle/run/load-change), computes kWh-per-unit-produced, and sends the owner a daily WhatsApp report with the top 3 savings actions ranked by ₹ payback.
- **Features:**
  - Machine-state detection from aggregate current signal (edge ML)
  - kWh/unit KPI + baseline drift alerts ("Compressor now uses 12% more for same output — check leaks")
  - **Predictive maintenance:** vibration/current anomaly flags before motor failure
  - Solar/renewable ROI calculator ("your load profile suits a 10 kW rooftop — payback 3.2 yrs")
- **Stack:** ESP32 + SCT-013 sensor (or recorded motor-current datasets e.g. from Kaggle) + Python edge inference + WhatsApp/telegram bot + lightweight dashboard
- **Demo trick:** Hair dryer/drill on a bench with the clamp meter — turn it on/off, dashboard shows state detection + cost live. Physical demos beat slideware.
- **Why it wins:** SME affordability + real-time visibility + predictive maintenance + decarbonisation — the complete brief in one box.
- **Difficulty:** 🟡 Medium (if hardware) / 🟢 Easy-Medium (pure simulation)

#### Project 4B — "ShiftSmart" Energy-Aware Production Scheduler
**Concept:** Re-sequence production jobs so energy-hungry steps run in off-peak/solar hours without missing delivery deadlines — saves 10–20% on bills with zero capital spend.
- **Stack:** Constraint optimisation (OR-Tools) + Gantt-chart UI + tariff calendar
- **Difficulty:** 🟡 Medium | Pure software, very demo-able

#### Project 4C — "CarbonLedger SME"
**Concept:** Dead-simple Scope-1/2 emissions tracker for SMEs: input fuel/energy bills → emission hotspots + ranked reduction actions + one-page report for their B2B customers (who increasingly demand it).
- **Difficulty:** 🟢 Easy | Good backup idea

---

## 🏆 Final Shortlist — What We Should Actually Build

| Rank | Project | Track | Effort | Wow Factor | Winning Logic |
|---|---|---|---|---|---|
| 🥇 | **FlexiGrid — Community Demand-Response Engine** | 03 Grid | Medium-High | 🔥🔥🔥 | Least crowded track, Schneider's core domain, optimisation demo is spectacular, hits affordability + DISCOM criteria |
| 🥈 | **WattWise — Plug-Level Energy Intelligence** | 02 Buildings | Medium | 🔥🔥🔥 | Safest software-only pick, real-time two-screen demo, demand-response panel differentiates |
| 🥉 | **FactoryPulse Lite — SME Energy Doctor** | 04 Manufacturing | Medium | 🔥🔥🔥 | Hardware bench demo + WhatsApp report = judges *feel* the SME story |
| 4 | **ComfortIQ** | 02 Buildings | Low | 🔥🔥 | Best effort-to-wow ratio; live QR-code audience demo |
| 5 | **SolarPump Scheduler** | 01 Agriculture | Medium | 🔥🔥 | Strong all-criteria fit, but crowded track |

**Recommendation:** If the team has analytics/optimisation appetite → **FlexiGrid**. If the team is strong in general full-stack + ML → **WattWise**. If anyone has Arduino/ESP32 experience → **FactoryPulse Lite** (physical demos are rare and memorable).

---

## Universal Winning Playbook (applies to any track)

1. **Lead with energy numbers.** This is an *Energy Tech* hackathon — every screen of your product should quantify **kWh saved, ₹ saved, kg CO₂ avoided**. Teams that build generic apps lose.
2. **Speak Schneider Electric's language.** Study their EcoStruxure platform / the "Get Inspired" links on the challenge pages (Home Energy Management, Power & Grid, F&B Automation). Mirror their vocabulary (demand response, feeder flexibility, specific energy consumption) in your pitch.
3. **Affordability is a scored criterion everywhere.** Add a literal "Bill of Materials / cost per user" slide — most teams won't.
4. **Live demo > video > slides.** Simulate if you can't bring hardware, but make it *live and reacting* (a simulation button that changes the world state in front of judges).
5. **India-context data:** use IMD weather, eNAM/Agmarknet mandi prices, CEA/DISCOM reports, data.gov.in — name-drop the exact dataset in your pitch for credibility.
6. **Vernacular + low-connectivity = bonus points** in every track (WhatsApp bots are the cheapest way to show this).
7. **End with a deployment path:** "Pilot with one housing society / one MSME cluster in MIDC / one taluka" — judges reward a believable next step over vague scale claims.

---

## Data & Resource Links (free)
- **Weather/solar:** Open-Meteo API, IMD, NREL NSRDB
- **Building load data:** UK-DALE, AMPds, Pecan Street Dataport (free academic tier), UCI Individual Household Electric Power Consumption
- **Grid:** CEA (cea.nic.in) reports, Kaggle Indian power-system datasets
- **Agriculture:** eNAM / Agmarknet mandi prices, data.gov.in crop datasets, Soil Health Card data
- **Manufacturing/Motor data:** Kaggle motor-current & bearing-fault datasets (e.g., CWRU, IMS)
- **Optimisation:** Google OR-Tools, PuLP (free, Python)
- **NILM:** nilmtk open-source toolkit
- **Bots:** Telegram Bot API (free), WhatsApp Cloud API (free tier)
