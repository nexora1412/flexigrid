# ⚡ FlexiGrid — Community Demand Response for Bharat
**Yuva Yodha Energy Tech Hackathon 2026 — Challenge 03: Grid Reliability (Renewable Intermittency)**  
*Organized by Schneider Electric India*

> *"Tata Power × AutoGrid proved behavioural DR can shave 75 MW in Mumbai — for paying customers.  
> Bharat's 250M peri-urban & rural consumers have no DR product.  
> FlexiGrid starts with one feeder."*

---

## 🏆 Why FlexiGrid Wins Challenge 03

Schneider Electric India judges evaluate projects against four key pillars:
1. **Bridge Renewable Intermittency**: Dual-trigger Demand Response engine (Feeder Physical Limit + Solar Shortfall Gap) combined with a 60 kWh / 20 kW community battery merit-order dispatch.
2. **Local and Manageable**: Operates at the 40-connection Distribution Transformer (DT) level (100 kVA) with zero grid infrastructure upgrades.
3. **Genuinely Affordable for Low-Income Bharat**: Software-only and SMS-native (Tata BDR style) for feature phones. No proprietary smart plugs or expensive IoT needed.
4. **Direct DISCOM Value**: Real-time transformer thermal loading reduction, copper loss ($I^2R$) savings, OpenADR 2.0b compliance, and MERC MYT tariff regulatory reporting.

---

## 🌟 What's New & Upgraded

- ☁️ **Supabase Authentication & Cloud Data Store**: Full RBAC (Prosumer, Society Admin, MSEDCL Dispatcher) + persistent time-series storage for feeder telemetry, DR events, and micro-incentive transactions. Features a **Zero-Setup Resilient Vault**: runs immediately on embedded SQLite if offline and automatically mirrors to Supabase PostgreSQL when credentials are provided.
- ⚡ **OpenADR 2.0b SCADA Interface**: Virtual Top Node (VTN) / Virtual End Node (VEN) interoperability with standard payload dispatches.
- 🗼 **Schneider EcoStruxure Transformer Health Gauge**: Real-time 100 kVA DT winding temperature rise (°C), thermal overload prevention, and technical copper loss reduction (+4.2 years transformer life extension).
- 💸 **Bharat UPI Instant Micro-Payout Rails**: Direct NPCI/UPI mock payouts (`UPI/2026/FLEX/XXXX`) credited to prosumer bank accounts upon load deferral.
- 🌪 **Multi-Scenario Emergency Simulator**: One-click simulation for Monsoon Cloud Bank (-65% solar), Sunset Duck Curve Cliff, Heatwave Overload (+30% demand), and Microgrid Islanding.
- 📄 **MERC Regulatory & Executive Audit Report Generator**: 1-click JSON and print export for MERC Case No. 227 of 2024 compliance.

---

## 🎬 90-Second Judge Demo Script

1. **Set speed to 60×** and state: *"This is Baner Feeder, Pune — 40 connections on a 100 kVA transformer, pulling live irradiance right now from Open-Meteo."* (Badge confirms `LIVE ☀ OPEN-METEO`).
2. Watch the chart until **mid-morning**: The grey dashed *baseline* humps at noon and 8 PM; the green *actual* is flattened by **~43%**. *"The day-ahead MILP optimizer moved flexible devices directly into solar generation hours."*
3. At **≈12:00–14:00 sim time click ⚡ Grid Storm**: A 65% monsoon cloud bank collapses rooftop solar. The red alert bar appears; the community battery absorbs the initial shock; and within seconds, the **🛡 DR Dispatch** triggers.
4. Point to the **Live Event Feed**: Read aloud: SMS sent → accept/decline → deferrals → *"Shed 13.6 kW across 8 homes — fairness rotation applied"* → wallets credit ₹4/kWh.
5. In the Leaderboard, click **⚡ UPI Cashout** on Ramesh Patil: Watch the simulated UPI payment settle to `patil@upi` with a verified NPCI reference.
6. Switch View to **🗼 DISCOM Dispatcher**: Highlight the **Transformer Health Gauge** showing 38% loss reduction, and trigger an **OpenADR 2.0b Dispatch**.
7. Click **☁️ Supabase Vault**: Show the live cloud synchronization and verified database records.

---

## 📊 Data: What's Real vs Calibrated

| Layer | Source | Status |
|---|---|---|
| **Solar Irradiance / Cloud / Temp** | Open-Meteo API, per city, refreshed hourly like a day-ahead forecast | **100% LIVE** |
| **Retail Tariffs** | **MERC MYT Order FY 2026-27** (MSEDCL LT I-B) & **FY 2025-26** (Adani Mumbai) | **REAL Orders — Telescopic Slab Engine** |
| **Avoided Power Purchase Cost** | ₹5–8/kWh marginal proxy (MYT APPC-informed, Tata Mumbai BDR valuation) | Indicative-Real |
| **Solar Feed-in Tariff (FiT)** | ₹2.5/kWh (PM-KUSUM Component C band) | Indicative-Real |
| **DR Incentive** | ₹4.0/kWh deferred (Tata Power × AutoGrid Mumbai BDR benchmark) | Indicative-Real |
| **Grid CO₂ Baseline** | 0.82 kg/kWh (Central Electricity Authority national factor) | Indicative-Real |
| **Household Load Profiles** | Calibrated against peer-reviewed **iAWE Indian dataset** (Batra et al., ACM BuildSys 2013, IIIT Delhi) | **Metered Benchmark + CSV Drop-in** |

---

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in your browser.

### 3. Run Automated Tests
```bash
python test_app.py
```

---

## ☁️ Supabase Setup (Optional Cloud Sync)

FlexiGrid runs out of the box with zero configuration using its resilient embedded data vault. To sync with your own Supabase project:

1. Create a free project at [supabase.com](https://supabase.com).
2. Run the SQL script [`supabase/schema.sql`](supabase/schema.sql) in the Supabase SQL Editor.
3. In the FlexiGrid UI, click **☁️ Supabase Vault** and enter your Project URL and Key.

See [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) for full instructions and demo credentials.

---

## 🏛️ Architecture

```
flexigrid/
├── backend/
│   ├── main.py              # FastAPI server + Supabase auth + OpenADR + export APIs
│   ├── sim_core.py          # 40-home feeder physics, battery merit order, DR fairness
│   ├── optimizer.py         # PuLP/CBC MILP day-ahead scheduler + greedy fallback
│   ├── data_real.py         # Open-Meteo live stream + MERC MYT tariff tables
│   ├── supabase_service.py  # Supabase client + local SQLite resilient vault
│   └── iawe_profiles.json   # 6 measured days from IIIT-Delhi iAWE dataset
├── frontend/
│   └── index.html           # Dark-mode dashboard (Chart.js), role switcher, modals
├── supabase/
│   └── schema.sql           # PostgreSQL schema with RLS security policies
├── SUPABASE_SETUP.md        # Supabase setup and architecture guide
├── SUBMISSION.md            # Yuva Yodha 2026 hackathon submission document
├── Dockerfile               # Production container image
├── render.yaml              # 1-click cloud deployment config
└── requirements.txt         # Python dependencies
```
