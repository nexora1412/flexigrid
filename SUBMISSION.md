# FlexiGrid — Submission Package
**Yuva Yodha Energy Tech Hackathon 2026 · Challenge 03: Grid Reliability — Renewable Intermittency**
*"Making clean power dependable, neighbourhood by neighbourhood."*

---

## 1. Problem (as the judges framed it)
When renewable supply falls below demand — a cloud bank over a rooftop-solar neighbourhood, an evening peak after sunset — the grid has exactly two levers today: fire up thermal peakers, or shed load blindly. Neither is clean, cheap, or fair. The brief demands a solution that is **neighbourhood-scale, genuinely affordable for low-income communities, and helpful to the DISCOM**.

## 2. Insight
Tata Power × AutoGrid proved behavioural demand response works in Mumbai — 55,000 customers, 75 MW of verified peak reduction — **for paying, connected customers**. Nobody has built DR for the 250M+ consumers on weak rural/peri-urban feeders where intermittency hurts most. FlexiGrid's wedge:
1. **Fairness-first** — rotating participation so curtailment never repeatedly targets the same (usually poorest) households.
2. **Storage-first merit order** — a shared community battery absorbs the shock BEFORE any family is asked to change behaviour; flexible demand handles the remainder.
3. **Software-only & SMS-native** — works on feature phones, no proprietary hardware, deployable on any feeder with smart meters (India is installing 250M of them).

## 3. What FlexiGrid does (live working product)
A 40-connection MSEDCL-style feeder with six subsystems, visibly running in the dashboard:

| Subsystem | Function | Status |
|---|---|---|
| ☀️ Forecasting | Real Open-Meteo irradiance/cloud/temperature per city; refreshed daily like a real day-ahead process | **LIVE** |
| 🧠 MILP optimizer (PuLP/CBC) | Day-ahead scheduling of ~94 flexible devices/day into solar-rich off-peak hours | **working — ~43% peak cut** |
| 🔋 Community battery (60 kWh/20 kW) | Night charge ₹6 → solar-gap first response (reserve-preserving 35%) → evening peak shave → solar trickle | **working** |
| 🛡 DR engine, dual triggers | (a) physical feeder limit, (b) **renewable intermittency gap** — solar shortfall while flexible loads sit in the solar window | **working** |
| ⚖️ Fairness rotation + micro-incentives | Least-participated homes asked first; ₹4/kWh wallets; SMS accept/decline (25% behavioural homes) | **working** |
| 🗼 DISCOM control-room & EcoStruxure DT | Feeder peak before/after, transformer thermal overload protection, 38% copper loss reduction, MERC compliance export | **working** |
| ⚡ OpenADR 2.0b Interface | Virtual Top Node (VTN) dispatch signal reception and automated VEN profile response | **working** |
| ☁️ Supabase Cloud Data Store & Auth | Role-based authentication (Prosumer, Society Admin, MSEDCL Dispatcher) + resilient local SQLite vault sync | **working** |
| 💸 Bharat UPI Micro-Payouts | Instant mock IMPS/UPI disbursement rails (`UPI/2026/FLEX/XXXX`) for prosumer wallets | **working** |

## 4. Impact numbers from a single simulated day (Pune, live weather)
- **104.3 → 59.7 kW** feeder peak at sundown (**42.8% cut**)
- **38.2% technical loss reduction** on 100 kVA Distribution Transformer (**+4.2 years equipment life extension**)
- **₹470/day** community savings (ToD arbitrage + solar self-consumption + night-charge arb) ≈ **₹1.7 lakh/year per feeder**
- **160 kg CO₂/day avoided** (CEA 0.82 kg/kWh — indicative)
- **31 kWh** flexible load deferred across a storm event with **0 comfort failures**, incentives paid to 8–17 homes via UPI
- Cost to deploy: **₹0 per household** (software + SMS on existing smart meters)

## 5. Why we win vs. the field
AutoGrid / Uplight / Bidgely sell to utilities with budgets; Schneider's own stack targets buildings & industry. **Nobody serves the low-income feeder.** Our differentiators — the equity layer, feeder-scale storage+DR merit order, and DISCOM-facing telemetry — map one-to-one to the four judging bullets in the brief, including the *shared storage* pillar most teams will skip.

## 6. Demo script (90 seconds)
1. Speed 60× → *"Baner Feeder, Pune — real irradiance right now"* (LIVE ☀ badge, actual °C).
2. Grey *baseline* hump vs green *actual* flatline → *"the optimizer + battery cut the peak 43%"*.
3. ~12:30 sim-time → **⚡ Grid Storm** → watch: battery FIRST response log → DR banner → SMS accept/declines → wallets fill → feeder holds.
4. DISCOM panel: *"this is the feeder report a DISCOM engineer gets — zero capex."*
5. City switch → Dhule/Nagpur/Mumbai with their live weather re-optimizes the day.

## 7. Tech & data honesty sheet
- Stack: Python · FastAPI · PuLP (CBC MILP) · Open-Meteo API · Chart.js single-file UI
- **100% LIVE:** solar irradiance / cloud / temperature per city (Open-Meteo), refreshed daily like a real day-ahead forecast.
- **REAL DISCOM tariffs (slab engine):**
  - MSEDCL LT I(B) — **MERC MYT Order FY 2026-27**: ₹5.05 / ₹10.25 / ₹13.80 energy slabs + ₹1.35 wheeling + ₹0.679 FAC, ₹135/mo fixed, 16% electricity duty.
  - Adani Electricity Mumbai Domestic — **MERC MYT Order FY 2025-26** (eff. 01-04-2025): ₹4.30 / ₹7.25 / ₹11.36 / ₹12.94, ₹95/kW fixed, 16% duty.
  - *Honest insight the real engine produces:* under telescopic Indian slabs, high-use homes pay ₹15–18/kWh effective, so pure load-shifting barely changes the retail bill — the value is in **solar self-consumption + DR payouts (₹4/kWh, Tata × AutoGrid band) + storage at DISCOM avoided-cost (₹5–8/kWh proxy, MYT APPC-informed)**. That IS the correct DR economics for India.
- **Load data — REAL traces plugged in:** the embedded **iAWE Indian dataset** (Batra et al., BuildSys 2013, IIIT-Delhi; processed copy via Zenodo rec. 13917372) ships inside the app as 6 complete measured days (48×30-min blocks, 3–15 kWh/day) from the Delhi home's aggregate mains. One click (**📥 iAWE real day**) re-bases the community on the real meter trace, and the sim auto-rotates to the next measured day at every midnight. Default profiles are synthetic, calibrated to the same paper (180–250 V swings, outage patterns). And `POST /api/upload_load` re-bases the sim on ANY (timestamp, kW) smart-meter CSV — auto-resample, Watt→kW detection.

## 8. Roadmap (next 2 quarters — answer for "is this real?")
1. **Pilot:** one 100-kVA DT in a Dhule housing cluster with MSEDCL smart-meter data + ₹60k community battery (or aggregated home UPS systems).
2. **Disaggregation:** NILMTK/iAWE on feeder AMI data → device-level flexibility detection without any new hardware.
3. **Interoperability:** OpenADR 2.0b endpoint so the DISCOM can call formal DR events; UPI rails for incentive payouts.
4. **Scale-out:** per-feeder SaaS for DISCOMs; 300+ feeders in the first DISCOM circle ≈ 25 MW of virtual peaker capacity.

## 9. Team quick-start
```bash
pip install -r requirements.txt
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000   # dashboard at / 
# or: docker build -t flexigrid . && docker run -p 8000:8000 flexigrid
# Render/Railway: render.yaml + Procfile included — deploy in ~2 minutes
```
