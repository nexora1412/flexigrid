# ⚡ FlexiGrid — Supabase Setup & Architecture Guide

FlexiGrid integrates **Supabase** for user authentication (Role-Based Access Control) and real-time cloud data storage for feeder telemetry, DR events, and micro-incentive transactions.

## 🚀 Instant Zero-Config Mode
FlexiGrid features a **Resilient Hybrid Data Vault**:
- If Supabase credentials are not yet configured, the system **automatically runs on an embedded high-speed SQLite data store** with pre-seeded demo accounts.
- **Zero crashes, 100% demo-ready** immediately upon cloning!
- When you provide your Supabase URL and Key, it seamlessly switches to **Live Supabase PostgreSQL Cloud** and synchronizes all data.

---

## 🔑 How to Connect Your Supabase Project (3 Easy Steps)

### Step 1: Create a Free Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a free project (e.g. `flexigrid-msedcl`).
2. Go to **Project Settings** → **API** to copy your:
   - **Project URL** (`https://xyzcompany.supabase.co`)
   - **anon / public key** or **service_role key**

### Step 2: Run the SQL Schema Migration
1. In your Supabase Dashboard, click on **SQL Editor** on the left menu.
2. Open the file [`supabase/schema.sql`](supabase/schema.sql) in this repository.
3. Paste the contents into the SQL Editor and click **Run**.
4. This creates:
   - `profiles`: User accounts, roles, home links, UPI IDs
   - `feeder_telemetry`: Real-time net load, solar generation, peak reduction
   - `dr_events`: Intermittency trigger records and load deferred
   - `wallet_transactions`: UPI micro-incentive payout logs
   - `device_registry`: Flexible loads configuration

### Step 3: Configure Environment Variables
You can configure credentials in either of two ways:

#### Option A: In the Web Dashboard (Fastest)
1. Run FlexiGrid and open `http://localhost:8000`.
2. Click the **☁️ Supabase Vault** button in the header.
3. Paste your `SUPABASE_URL` and `SUPABASE_KEY` and click **Save & Connect**.
4. The status badge will instantly turn **🟢 Supabase Cloud (PostgreSQL)**!

#### Option B: In `.env` file
Create a `.env` file in `flexigrid/backend/.env`:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
```

---

## 👥 Demo User Accounts (Pre-configured)

| Role | Email | Password | Home / Feeder | Function |
|---|---|---|---|---|
| **DISCOM Operator** | `operator@msedcl.gov.in` | `msedcl2026` | MSEDCL Feeder R-11 | Full SCADA grid control, OpenADR dispatch, DT health |
| **Society Admin** | `secretary@banerchs.in` | `society2026` | Baner CHS | Community battery management, fairness oversight |
| **Prosumer (Solar)** | `patil@flexigrid.in` | `patil123` | Home H00 (Ramesh Patil) | Device flex toggle, real-time generation, UPI cashout |
| **Prosumer (Standard)** | `deshmukh@flexigrid.in` | `deshmukh123` | Home H01 (Anand Deshmukh)| SMS/Auto DR participation, rewards wallet |

---

## 📊 Available Supabase Endpoints

- `POST /api/auth/signup` — Create new prosumer or utility user
- `POST /api/auth/login` — Sign in and get session JWT
- `GET /api/auth/me` — Current authenticated session
- `POST /api/auth/logout` — Revoke session
- `GET /api/supabase/status` — Health, connection status, row counts
- `POST /api/supabase/config` — Update Supabase URL/key dynamically
- `GET /api/supabase/data` — Real-time telemetry, DR events, wallet logs
- `POST /api/wallet/payout` — Claim instant UPI micro-reward (NPCI mock rail)
