"""
FlexiGrid — feeder-scale community simulation engine.
40 homes + 2 society assets on one MSEDCL-style distribution feeder.
Real irradiance (Open-Meteo) drives rooftop solar; optimizer + DR engine manage flexible loads.
"""
from __future__ import annotations
import random
import math
import time
from data_real import (
    CITIES, fetch_weather, tod_price, EXPORT_FIT, DR_INCENTIVE, CO2_FACTOR,
    hour_meta, retail_marginal, tariff_table, avoided_cost, IAWE,
)
from optimizer import optimize_schedule, place_remaining

BLOCK_MIN = 30                 # 30-min settlement blocks  -> 48/day
BPD = 48

# ------------------------------------------------------------------ helpers
def bell(h, mu, sigma):
    return math.exp(-((h - mu) ** 2) / (2 * sigma * sigma))


NAMES = [
    "Patil", "Deshmukh", "Joshi", "Kulkarni", "Shinde", "Pawar", "More", "Jadhav",
    "Chavan", "Gaikwad", "Bhosale", "Mane", "Kadam", "Thakur", "Wagh", "Salunkhe",
    "Deshpande", "Ghorpade", "Nikam", "Rane", "Kulkarni-2", "Sonawane", "Borse",
    "Chaudhari", "Bhoir", "Mahajan", "Aher", "Shelar", "Gavli", "Pingle",
    "IN-House Solar Co-op", "Oak Residency", "Maple CHS", "Lotus Homes", "Cedar Row",
    "Neem Villa", "Tulsi Niwas", "Ambika Heights", "Sahil Residency", "Gurukrupa CHS",
]

DEVICE_SPECS = {
    "GEYSER": {"label": "Geyser",  "power": 2.0, "n": 2, "win": (10, 20), "default": 14},
    "PUMP":   {"label": "Borewell Pump", "power": 1.5, "n": 2, "win": (12, 34), "default": 16},
    "EV":     {"label": "EV Charger",    "power": 3.3, "n": 5, "win": (34, 47), "default": 38},
    "WM":     {"label": "Washing Machine","power": 0.9,"n": 2, "win": (12, 44), "default": 18},
    "SPUMP":  {"label": "Society Pump",  "power": 5.0, "n": 4, "win": (8, 34),  "default": 13},
    "CAC":    {"label": "Clubhouse AC",  "power": 4.0, "n": 4, "win": (30, 46), "default": 36},
}


class Device:
    def __init__(self, home_id, kind, rng):
        s = DEVICE_SPECS[kind]
        self.id = f"{home_id}:{kind}"
        self.kind = kind
        self.label = s["label"]
        self.power = round(s["power"] * rng.uniform(0.9, 1.1), 2)
        self.n = s["n"]
        self.win = s["win"]
        dj = rng.choice([-1, 0, 0, 1])
        self.default_start = max(self.win[0], min(s["default"] + dj, self.win[1] - self.n))
        self.start = self.default_start          # optimized later
        self.done_blocks = set()                 # blocks completed today
        self.extra = set()                       # blocks added by DR re-placement (may be non-consecutive)
        self.removed = set()                     # blocks cancelled from the original plan by DR
        self.missed = False

    def full_blocks(self):
        return list(range(self.start, self.start + self.n))

    def sched_blocks(self):
        return set(self.full_blocks()) | self.extra

    def active_blocks(self):
        """blocks still pending execution today"""
        return self.sched_blocks() - self.done_blocks - self.removed

    def default_blocks(self):
        return list(range(self.default_start, self.default_start + self.n))

    def reset_day(self, start_block):
        self.start = start_block
        self.done_blocks = set()
        self.extra = set()
        self.removed = set()
        self.missed = False


class Home:
    def __init__(self, idx, name, kind, rng):
        self.id = f"H{idx:02d}"
        self.name = name
        self.kind = kind
        self.behavioral = rng.random() < 0.25        # needs SMS nudge (Tata BDR style)
        # ~30% rooftop adoption — realistic for peri-urban low-income feeders
        self.solar_kwp = round(rng.choice([0, 0, 0, 0, 1.5, 2]) * rng.uniform(0.9, 1.1), 2)
        self.orient = rng.uniform(0.82, 1.0)
        self.size = rng.uniform(0.75, 1.35)
        self.night_ac = (kind == "3BHK AC")
        self.participation = 0.0                     # blocks deferred lifetime (fairness meter)
        self.wallet = 0.0
        self.self_consumed_kwh = 0.0
        self.cum_imp_act = 0.0                       # today's cumulative imported kWh (actual)
        self.cum_imp_base = 0.0                      # today's cumulative imported kWh (baseline)
        self.override_curve = None                   # real-data CSV override (list[48] kW)
        self.devices: list[Device] = []
        # device mix by home type
        self.devices.append(Device(self.id, "GEYSER", rng))
        if kind in ("Row House", "EV Home") or rng.random() < 0.55:
            self.devices.append(Device(self.id, "PUMP", rng))
        if kind == "EV Home" or rng.random() < 0.12:
            self.devices.append(Device(self.id, "EV", rng))
        if rng.random() < 0.75:
            self.devices.append(Device(self.id, "WM", rng))

    def base_kw(self, hour_frac: float, block=None) -> float:
        # real-data override (uploaded CSV profile, e.g. actual smart-meter export)
        if self.override_curve is not None and block is not None:
            return self.override_curve[min(block, len(self.override_curve) - 1)]
        l = 0.22 * self.size
        l += 0.45 * self.size * bell(hour_frac, 7.5, 1.3)
        l += 0.25 * self.size * bell(hour_frac, 13.0, 2.8)
        l += 1.05 * self.size * bell(hour_frac, 20.0, 1.9)
        if self.night_ac:
            l += 0.75 * self.size * (bell(hour_frac, 1.0, 2.6) + bell(hour_frac, 23.5, 1.2))
        return l

    def solar_kw(self, ghi: float, storm_mult: float) -> float:
        return self.solar_kwp * (ghi / 1000.0) * 0.78 * self.orient * storm_mult

    def dev_kw(self, block: int) -> float:
        """power drawn this block by scheduled devices (actual plan)."""
        w = 0.0
        for d in self.devices:
            if block in d.active_blocks():
                w += d.power
        return w

    def dev_kw_baseline(self, block: int) -> float:
        w = 0.0
        for d in self.devices:
            if block in d.default_blocks():
                w += d.power
        return w


class SocietyAsset(Home):
    def __init__(self, sid, name, kind, rng):
        super().__init__(sid, name, kind, rng)
        self.behavioral = False
        self.solar_kwp = 4.5
        self.devices = []
        self.devices.append(Device(self.id, "SPUMP", rng))
        if kind == "club":
            self.devices.append(Device(self.id, "CAC", rng))

    def base_kw(self, hour_frac, block=None):
        if self.override_curve is not None and block is not None:
            return self.override_curve[min(block, len(self.override_curve) - 1)]
        return 1.5 + 1.2 * bell(hour_frac, 20.0, 2.0)


class World:
    def __init__(self, city="Pune", seed=42, start_minute=5):
        self.rng = random.Random(seed)
        self.seed = seed
        self.city = city
        self.weather = fetch_weather(city)
        self.speed = 15                    # sim-minutes per real second
        self.day = 0
        self.minute = start_minute         # start just after midnight so a full day unfolds
        self.storm_until = -1
        self.storm_mult = 1.0
        self.storm_severity = 0.0

        # homes
        self.homes: list[Home] = []
        kinds = ["1BHK", "2BHK", "2BHK", "3BHK AC", "Row House", "EV Home", "2BHK", "1BHK"]
        for i, name in enumerate(NAMES[:38]):
            self.homes.append(Home(i + 1, name, kinds[i % len(kinds)], self.rng))
        self.homes.append(SocietyAsset(100, "Society Water Works", "pump", self.rng))
        self.homes.append(SocietyAsset(101, "Society Club House", "club", self.rng))

        # community battery (shared storage — the brief's 5th pillar)
        self.battery = {
            "cap_kwh": 60.0, "soc_kwh": 27.0, "max_kw": 20.0,
            "kw_ch": 0.0, "kw_dis": 0.0, "label": "idle",
            "charged_today": 0.0, "discharged_today": 0.0,
            "_last_label": "idle", "_gap_responded_at": -999,
        }
        self.batt_acc = [0.0] * BPD       # signed kW·min per block (charge +, discharge −)
        self._last_net_after = 0.0        # net import after battery dispatch

        # curves + accounts
        self.realized_actual = [0.0] * BPD
        self.block_accounted = -1
        self.feeder_limit = 120.0
        self.kpi = {
            "shifted_kwh": 0.0, "saved_rupees": 0.0, "co2_kg": 0.0,
            "dr_events": 0, "dr_deferred_kwh": 0.0, "export_kwh": 0.0,
            "retail_delta": 0.0, "dr_earnings": 0.0, "battery_value": 0.0,
        }
        self.custom_profile = None   # (name, list[48]) real-data override active
        # ---- REAL iAWE profiles (embedded, extracted from the actual dataset)
        self.iawe_profiles = None
        self._iawe_day_idx = 0
        try:
            import json as _json
            from pathlib import Path as _Path
            p = _Path(__file__).parent / "iawe_profiles.json"
            if p.exists():
                self.iawe_profiles = _json.loads(p.read_text())
        except Exception:
            self.iawe_profiles = None
        self.events: list[dict] = []
        self.dr_active = False
        self._dr_cooldown_until_min = -1
        self._last_openadr_event_id = None
        self.weather_src = self.weather["source"]

        self.run_day_optimization()
        self.log(f"Day-ahead schedule optimized for {len(self.homes)} connections — peak shaved {self.last_peak_cut_pct}%", "opt")
        self.log("FlexiGrid online. Live irradiance: " + self.weather_src, "info")

    # ---------------------------------------------------------------- utils
    @property
    def block(self):
        return min(self.minute // BLOCK_MIN, BPD - 1)

    def clock_str(self, minute=None):
        m = self.minute if minute is None else minute
        return f"{(m // 60) % 24:02d}:{m % 60:02d}"

    def log(self, text, kind="info"):
        self.events.insert(0, {"t": f"D{self.day+1} {self.clock_str()}", "text": text, "kind": kind})
        del self.events[60:]

    def hour_index(self, block_of_day):
        """Absolute hour into the live forecast window, wrapped so multi-day
        simulations reuse the freshest forecast pattern (like a day-ahead market)."""
        n = max(len(self.weather.get("hours", [])), 24)
        return (self.day * 24 + block_of_day // 2) % n

    def storm_active(self):
        return self.minute < self.storm_until

    def current_mult(self, in_minute=None):
        m = self.minute if in_minute is None else in_minute
        if m < self.storm_until:
            return self.storm_mult
        return 1.0

    # ----------------------------------------------------------- optimizer
    def run_day_optimization(self, floor_block=0):
        base = [0.0] * BPD
        solar = [0.0] * BPD
        for b in range(BPD):
            hfrac = (b * BLOCK_MIN + 15) / 60.0
            ghi = hour_meta(self.weather, self.hour_index(b))["ghi"]
            for h in self.homes:
                base[b] += h.base_kw(hfrac, b)
                solar[b] += h.solar_kw(ghi, 1.0)

        dev_specs = []
        locked = set()
        for h in self.homes:
            for d in h.devices:
                if d.win[1] <= floor_block:
                    locked.add(d.id)     # window already over — leave untouched
                    continue
                dev_specs.append({"id": d.id, "power_kw": d.power, "n_blocks": d.n, "win": d.win})
        sched = optimize_schedule(dev_specs, base, solar, start_block_floor=floor_block)

        shifted = 0.0
        for h in self.homes:
            for d in h.devices:
                if d.id in locked:
                    continue
                st = sched.get(d.id, d.default_start)
                if st != d.default_start:
                    shifted += abs(st - d.default_start) * d.power * 0.5
                keep_done = {b for b in d.done_blocks if b < floor_block}
                d.reset_day(st)
                d.done_blocks = keep_done

        # baseline peak (devices at default slots) & adaptive limit
        base_peak = 0.0
        for b in range(BPD):
            val = base[b] - solar[b]
            for h in self.homes:
                val += h.dev_kw_baseline(b)
            base_peak = max(base_peak, val)
        opt_peak = 0.0
        for b in range(BPD):
            val = base[b] - solar[b]
            for h in self.homes:
                val += h.dev_kw(b)
            opt_peak = max(opt_peak, val)
        self.feeder_limit = max(40.0, round(base_peak * 0.85))
        self.last_base_peak = base_peak
        self.last_opt_peak = opt_peak
        self.last_peak_cut_pct = round(100 * (base_peak - opt_peak) / max(base_peak, 1), 1)
        self.kpi["shifted_kwh"] = round(shifted, 1)

    # --------------------------------------------------------------- storm
    def trigger_storm(self, severity=0.38, duration_min=40):
        self.storm_mult = 1.0 - severity
        self.storm_severity = severity
        self.storm_until = self.minute + duration_min
        self.log(f"⚡ GRID STORM: cloud bank over feeder — rooftop solar −{int(severity*100)}% for {duration_min} sim-min", "storm")

    # ------------------------------------------------------------------ DR
    def run_dr_if_needed(self, net_now):
        """Two triggers:
        1. HARD: feeder import above physical limit (over-capacity protection).
        2. SOFT (intermittency gap): rooftop solar forecast loses >8 kW to weather while the
           community — which co-scheduled its flexible loads INTO the solar window — suddenly
           becomes a net importer. DR defers flexible load until the feeder is net-zero again
           during sunshine hours. This is the actual renewable-intermittency problem in the brief.
        """
        block = self.block
        ghi = hour_meta(self.weather, self.hour_index(block))["ghi"]
        solar_fc = sum(h.solar_kw(ghi, 1.0) for h in self.homes)          # forecast (clear)
        solar_now = sum(h.solar_kw(ghi, self.current_mult()) for h in self.homes)
        shortfall = solar_fc - solar_now

        hard = net_now > self.feeder_limit
        gap = (solar_fc > 15) and shortfall > 8 and net_now > 1.0

        if not (hard or gap) or self.minute < self._dr_cooldown_until_min:
            if not (hard or gap):
                self.dr_active = False
            return

        self.dr_active = True
        if gap and not hard:
            need_kw = net_now - 0.5
            trigger_txt = f"intermittency gap {shortfall:.0f} kW (solar {solar_fc:.0f}→{solar_now:.0f} kW)"
        else:
            need_kw = net_now - self.feeder_limit
            trigger_txt = f"feeder over limit ({net_now:.0f} > {self.feeder_limit:.0f} kW)"

        self._trigger_dr(trigger_txt, need_kw)

    def _trigger_dr(self, trigger_txt, deficit_kw=15.0):
        self.dr_active = True
        block = self.block
        need_kw = max(deficit_kw, 5.0)

        cands = []
        for h in self.homes:
            for d in h.devices:
                # flexible = running now OR due to start within 90 min (pre-emptive deferral)
                if any(block <= b <= block + 3 for b in d.active_blocks()):
                    cands.append((h.participation, self.rng.random(), h, d))
        cands.sort(key=lambda x: (x[0], x[1]))

        shed_kw, acted, homes_touched = 0.0, False, 0
        for part, _, h, d in cands:
            if shed_kw >= need_kw:
                break
            if h.behavioral:
                # SMS behavioural response — auto-accepted with 85% probability
                self.log(f"📲 SMS to {h.name} ({h.kind}): “Defer {d.label} now, earn ₹ — Y/N?”", "sms")
                if self.rng.random() > 0.85:
                    self.log(f"❌ {h.name} declined – next home in fairness queue", "sms")
                    h.participation += 0.2
                    continue
                self.log(f"✅ {h.name} accepted via SMS", "sms")

            remaining = sorted(b for b in d.active_blocks() if b >= block)
            if not remaining:
                continue
            energy_kwh = len(remaining) * 0.5 * d.power
            self.kpi["dr_deferred_kwh"] += energy_kwh
            reward = energy_kwh * DR_INCENTIVE
            self.kpi["dr_earnings"] += reward        # real cash into residents' wallets
            self.kpi["saved_rupees"] += reward
            h.wallet += reward
            h.participation += len(remaining)

            # cancel original plan, re-place into cheapest future slots of the window
            for b in remaining:
                d.removed.add(b)
            agg = self._projected_agg_after_solar()
            future = place_remaining({"win": d.win}, len(remaining), block + 2, agg)
            d.extra.update(future)
            deficit = len(remaining) - len(future)
            if deficit > 0:
                d.missed = True
                self.log(f"⚠️ {h.name} • {d.label}: {deficit} block(s) comfort-missed today (+₹{reward:.1f} compensation)", "dr")
            if future:
                self.log(f"🔁 {h.name} • {d.label} deferred {len(future)*30} min → resumes {self.clock_str(min(future)*BLOCK_MIN)} (+₹{reward:.1f})", "dr")
            shed_kw += d.power
            homes_touched += 1
            acted = True
            self.kpi["dr_events"] += 1

        if acted:
            self._dr_cooldown_until_min = self.minute + 15
            self.log(f"🛡 DR event ({trigger_txt}): shed {shed_kw:.1f} kW across {homes_touched} homes — fairness rotation applied", "dr")
            try:
                from supabase_service import supabase_service
                supabase_service.record_dr_event(
                    trigger=trigger_txt,
                    target_kw=deficit_kw,
                    achieved_kw=shed_kw,
                    duration_min=30,
                    homes_count=homes_touched,
                    incentive_inr=self.kpi.get("dr_earnings", 0.0)
                )
            except Exception:
                pass

    def _projected_agg_after_solar(self):
        agg = [0.0] * BPD
        for b in range(BPD):
            hfrac = (b * BLOCK_MIN + 15) / 60.0
            ghi = hour_meta(self.weather, self.hour_index(b))["ghi"]
            mult = self.current_mult(b * BLOCK_MIN)
            for h in self.homes:
                agg[b] += h.base_kw(hfrac, b) + h.dev_kw(b) - h.solar_kw(ghi, mult)
        return agg

    # ------------------------------------------------------------- tick loop
    def tick(self, minutes=1):
        prev_block = self.block
        self.minute += minutes
        if self.minute >= 1440:  # new simulated day
            self.minute -= 1440
            self.day += 1
            self.end_of_day_accounts()
            self.weather = fetch_weather(self.city)   # fresh day-ahead forecast (like a real DR operator)
            self.run_day_optimization()
            # if running on iAWE real traces, advance to the next real measured day
            if self.custom_profile and str(self.custom_profile.get("name", "")).startswith("iAWE"):
                self.use_iawe()
            self.log(f"🌅 New day. Day-ahead optimization done — projected peak cut {self.last_peak_cut_pct}%", "opt")

        block = self.block
        if block != prev_block:
            # settle every block we crossed (handles big speed steps at 60×/120×)
            for b2 in range(self.block_accounted + 1, block + 1):
                self.account_block(b2)
            try:
                from supabase_service import supabase_service
                supabase_service.record_telemetry(self.snapshot())
            except Exception:
                pass
        net_after = self.battery_dispatch(minutes)   # storage is the FIRST responder
        self.run_dr_if_needed(net_after)             # DR covers the remainder

    def net_now(self):
        return self._block_net(self.block, optimized=True)

    def raw_net_now(self):
        return self._block_net(self.block, optimized=True)

    def _solar_gap_now(self):
        """kW of irradiance lost to weather vs. forecast (0 if irrelevant)."""
        b = self.block
        ghi = hour_meta(self.weather, self.hour_index(b))["ghi"]
        fc = sum(h.solar_kw(ghi, 1.0) for h in self.homes)
        now = sum(h.solar_kw(ghi, self.current_mult()) for h in self.homes)
        return (fc - now) if fc > 15 else 0.0

    # ------------------------------------------------- battery dispatch
    def battery_dispatch(self, minutes):
        """Merit-order storage dispatch (value stacking, FlexMeasures-style):
        1. SOLAR-GAP RESPONSE: absorb up to 40% of an irradiance shortfall while
           preserving a 35% reserve for the evening needle — DR covers the rest.
        2. EVENING PEAK SHAVE: discharge full assist above 80% of feeder limit.
        3. NIGHT CHARGE: grid-charge to 70% by 05:00 at off-peak ₹6/kWh.
        4. SOLAR TRICKLE: mop up community surplus whenever it exists. """
        b = self.battery
        H = max(minutes / 60.0, 1e-6)
        raw = self.raw_net_now()
        gap = self._solar_gap_now()
        hour_int = (self.minute // 60) % 24
        kw_dis = kw_ch = 0.0
        label = "idle"

        cap, soc, mx = b["cap_kwh"], b["soc_kwh"], b["max_kw"]
        if gap > 8:
            reserve = 0.05 * cap
            share = min(mx, gap * 0.4)
            kw_dis = min(share, max((soc - reserve), 0) / H)
            label = "covering solar gap (reserve-preserving)"
        elif raw > self.last_opt_peak * 0.75 and soc > 0.05 * cap:
            # support the whole evening rise down toward 73% of the scheduled peak
            need = raw - self.last_opt_peak * 0.73
            kw_dis = min(mx, need, max(soc - 0.05 * cap, 0) / H)
            label = "evening peak shave"
        elif hour_int < 5 and soc < self._batt_target():
            kw_ch = min(mx, (self._batt_target() - soc) / max((5 - hour_int) * 0.9, 0.4))
            kw_ch = min(kw_ch, mx)
            label = f"night charge @ ₹{avoided_cost(hour_int)}/kWh system cost"
        elif raw < -1.0 and soc < cap:
            kw_ch = min(mx, -raw, (cap - soc) / H)
            label = "charging from solar surplus"

        b["kw_dis"], b["kw_ch"] = kw_dis, kw_ch
        if kw_dis > 0.05:
            e = kw_dis * H
            b["soc_kwh"] = max(0.0, soc - e / 0.92)
            b["discharged_today"] += e
            v = e * avoided_cost(hour_int)          # DISCOM system value of reduced import
            self.kpi["battery_value"] += v
            self.kpi["saved_rupees"] += v
            self.kpi["co2_kg"] += e * CO2_FACTOR
        elif kw_ch > 0.05:
            e = kw_ch * H
            b["soc_kwh"] = min(cap, soc + e * 0.92)
            b["charged_today"] += e
            # night charge pays DISCOM avoided-cost proxy; solar trickle forfeits FiT export
            cost_rate = avoided_cost(hour_int) if hour_int < 5 else EXPORT_FIT
            c = e * cost_rate
            self.kpi["battery_value"] -= c
            self.kpi["saved_rupees"] -= c

        b["label"] = label
        if label != b["_last_label"]:
            if "gap" in label:
                self.log(f"🔋 Battery FIRST response: discharging {kw_dis:.0f} kW into the solar gap — homes untouched so far", "dr")
            elif "peak" in label:
                self.log(f"🔋 Battery shaving evening peak ({kw_dis:.0f} kW)", "info")
            elif "night" in label:
                self.log(f"🔋 Battery night-charging at ₹{avoided_cost(hour_int)}/kWh system off-peak cost", "info")
            b["_last_label"] = label

        self.batt_acc[self.block] += (kw_ch - kw_dis) * minutes
        self._last_net_after = raw - kw_dis + kw_ch
        return self._last_net_after

    def _batt_target(self):
        """Forecast-based storage plan: SOC the battery needs tonight =
        evening-shave energy need (from the projected raw curve) + an intermittency
        reserve derived from forecast cloud variability. Cached per day."""
        cur = getattr(self, "_batt_target_day", None)
        if cur != self.day:
            agg = self._projected_agg_after_solar()
            opt = max(getattr(self, "last_opt_peak", 60.0), 1)
            e_need = sum(max(agg[b] - 0.73 * opt, 0) * 0.5 for b in range(34, 48))
            ghi_series = [hour_meta(self.weather, self.hour_index(b))["ghi"] for b in range(16, 36)]
            mean = sum(ghi_series) / max(len(ghi_series), 1)
            var = sum(abs(ghi_series[i + 1] - ghi_series[i]) for i in range(len(ghi_series) - 1)) / max(mean, 1)
            e_gap = 14.0 if var > 9 else 8.0
            self._batt_target_day = self.day
            self._batt_target_val = min(self.battery["cap_kwh"] * 0.95, 3.0 + e_need + e_gap)
        return self._batt_target_val

    def _block_net(self, b, optimized):
        hfrac = (b * BLOCK_MIN + 15) / 60.0
        ghi = hour_meta(self.weather, self.hour_index(b))["ghi"]
        mult = self.current_mult(b * BLOCK_MIN)
        net = 0.0
        for h in self.homes:
            dev = h.dev_kw(b) if optimized else h.dev_kw_baseline(b)
            net += h.base_kw(hfrac, b) + dev - h.solar_kw(ghi, mult)
        return net

    def account_block(self, b):
        """settle economics when block b completes"""
        if b <= self.block_accounted or b >= BPD:
            return
        self.block_accounted = b
        for h in self.homes:
            hfrac = (b * BLOCK_MIN + 15) / 60.0
            ghi = hour_meta(self.weather, self.hour_index(b))["ghi"]
            mult = self.current_mult(b * BLOCK_MIN)
            solar = h.solar_kw(ghi, mult) * 0.5
            dev_actual = h.dev_kw(b) * 0.5
            dev_base = h.dev_kw_baseline(b) * 0.5
            home_base = h.base_kw(hfrac, b) * 0.5
            for d in h.devices:
                if b in d.active_blocks():
                    d.done_blocks.add(b)
            price = tod_price(int(hfrac))  # legacy — kept for reference only
            act_load = home_base + dev_actual
            bas_load = home_base + dev_base
            act_imp = max(act_load - solar, 0)
            bas_imp = max(bas_load - solar, 0)
            # REAL DISCOM retail economics: telescopic monthly slabs pro-rated daily,
            # marginal rate depends on how many units the home has already imported today.
            discom = CITIES[self.city]["discom"]
            pa = retail_marginal(discom, h.cum_imp_act)
            pb = retail_marginal(discom, h.cum_imp_base)
            act_cost = act_imp * pa - max(solar - act_load, 0) * EXPORT_FIT
            bas_cost = bas_imp * pb - max(solar - bas_load, 0) * EXPORT_FIT
            h.cum_imp_act += act_imp
            h.cum_imp_base += bas_imp
            delta = bas_cost - act_cost
            self.kpi["retail_delta"] += delta      # pure MSEDCL-bill effect (slab engine)
            self.kpi["saved_rupees"] += delta
            co2_delta = bas_imp - act_imp
            self.kpi["co2_kg"] += max(co2_delta, 0) * CO2_FACTOR
            self.kpi["export_kwh"] += max(solar - act_load, 0)
            h.self_consumed_kwh += min(solar, act_load)
            # comfort-miss: window closed with blocks still owed
            for d in h.devices:
                if not d.missed and b >= d.win[1] and d.active_blocks():
                    d.missed = True
                    self.log(f"⚠️ {h.name} • {d.label} could not finish inside its window today", "dr")
        self.realized_actual[b] = self._block_net(b, optimized=True) + (self.batt_acc[b] / BLOCK_MIN if b < BPD else 0)

    def end_of_day_accounts(self):
        self.log(
            f"🌙 Day wrapped: shifted {self.kpi['shifted_kwh']:.0f} kWh • saved ₹{self.kpi['saved_rupees']:.0f} • "
            f"{self.kpi['co2_kg']:.0f} kg CO₂ • DR deferrals {self.kpi['dr_deferred_kwh']:.1f} kWh", "info")
        self.kpi.update({"shifted_kwh": 0.0, "saved_rupees": 0.0, "co2_kg": 0.0,
                         "dr_events": 0, "dr_deferred_kwh": 0.0, "export_kwh": 0.0,
                         "retail_delta": 0.0, "dr_earnings": 0.0, "battery_value": 0.0})
        self.realized_actual = [0.0] * BPD
        self.batt_acc = [0.0] * BPD
        self.battery["charged_today"] = 0.0
        self.battery["discharged_today"] = 0.0
        self.block_accounted = -1
        self.events.insert(0, {"t": f"D{self.day+1} 00:00", "text": "Leaderboard carries over — fairness rotation continues", "kind": "info"})

    # ----------------------------------------------------- real-data override
    def set_base_override(self, profile48, name="uploaded profile"):
        """Replace the synthetic base-load model with a REAL 48-block community
        profile (e.g. smart-meter CSV export). Distributed across homes by size."""
        if not profile48 or len(profile48) != 48:
            return False
        mean_kw = sum(profile48) / 48.0
        if mean_kw <= 0:
            return False
        # scale so the community mean equals ~ the synthetic model's mean
        target_mean = sum(0.62 * h.size for h in self.homes) / max(len(self.homes), 1)
        for h in self.homes:
            scale = (0.62 * h.size) / mean_kw
            h.override_curve = [max(p * scale, 0.0) for p in profile48]
        self.custom_profile = {"name": name, "mean_kw": round(mean_kw, 2)}
        self.log(f"📥 REAL DATA plugged in: base-load model replaced by “{name}” (mean {mean_kw:.2f} kW)", "info")
        self.run_day_optimization(self.block)
        return True

    def use_iawe(self, day: int | None = None):
        """Plug a REAL measured day from the embedded iAWE dataset (Delhi home,
        aggregate mains, 30-min resolution) into the community load model."""
        if not self.iawe_profiles:
            return False
        days = sorted(self.iawe_profiles["days"])
        idx = (day if day is not None else self._iawe_day_idx) % len(days)
        prof = self.iawe_profiles["days"][days[idx]]
        self._iawe_day_idx = idx + 1
        return self.set_base_override(prof, f"iAWE {days[idx]} — real Delhi meter trace")

    def clear_base_override(self):
        for h in self.homes:
            h.override_curve = None
        self.custom_profile = None
        self.log("↩️ Reverted to iAWE-calibrated synthetic base-load model", "info")
        self.run_day_optimization(self.block)

    # ----------------------------------------------------------- controls
    def set_city(self, city):
        if city not in CITIES:
            return False
        self.city = city
        self.weather = fetch_weather(city)
        self.weather_src = self.weather["source"]
        self.log(f"📍 Feeder switched to {city} — {CITIES[city]['feeder']} ({CITIES[city]['discom']}). Live data: {self.weather_src}", "info")
        self.run_day_optimization(self.minute // BLOCK_MIN)
        return True

    def _tariff_json(self):
        t = tariff_table(CITIES[self.city]["discom"])
        return {
            "order": t["order"], "source": t["source"], "slab_note": t["slab_note"],
            "slabs": [[(None if c == float("inf") else c), r] for c, r in t["slabs"]],
            "wheeling": t["wheeling"], "fac": t["fac"], "duty": t["duty"],
            "fixed_monthly": t["fixed_monthly"],
        }

    # ----------------------------------------------------------- snapshot
    def snapshot(self):
        block = self.block
        labels = [f"{(b * BLOCK_MIN) // 60:02d}:{(b * BLOCK_MIN) % 60:02d}" for b in range(BPD)]
        proj_actual, proj_base, solar_arr = [], [], []
        for b in range(BPD):
            hfrac = (b * BLOCK_MIN + 15) / 60.0
            ghi = hour_meta(self.weather, self.hour_index(b))["ghi"]
            mult = self.current_mult(b * BLOCK_MIN)
            sol = sum(h.solar_kw(ghi, mult) for h in self.homes)
            solar_arr.append(round(sol, 1))
            if b <= block:
                # realized — includes battery effect accumulated this block
                eff = self._block_net(b, True) + (self.batt_acc[b] / BLOCK_MIN if b < BPD else 0)
                proj_actual.append(round(max(eff, 0), 1))
            else:
                v = 0.0
                for h in self.homes:
                    v += h.base_kw(hfrac, b) + h.dev_kw(b) - h.solar_kw(ghi, mult)
                proj_actual.append(round(max(v, 0), 1))
            vb = 0.0
            for h in self.homes:
                vb += h.base_kw(hfrac, b) + h.dev_kw_baseline(b) - h.solar_kw(ghi, mult)
            proj_base.append(round(max(vb, 0), 1))

        now_meta = hour_meta(self.weather, self.hour_index(block))
        homes_out = []
        for h in self.homes:
            hfrac = (block * BLOCK_MIN + 15) / 60.0
            ghi = now_meta["ghi"]
            load = h.base_kw(hfrac, block) + h.dev_kw(block)
            sol = h.solar_kw(ghi, self.current_mult())
            running = [d.label for d in h.devices if block in d.active_blocks()]
            homes_out.append({
                "id": h.id, "name": h.name, "kind": h.kind,
                "mode": "SMS" if h.behavioral else "AUTO",
                "kwp": h.solar_kwp,
                "load": round(load, 2), "solar": round(sol, 2),
                "net": round(load - sol, 2),
                "running": running,
                "wallet": round(h.wallet, 1),
                "participation": round(h.participation, 1),
                "missed": any(d.missed for d in h.devices),
            })

        peak_today = max(proj_actual) if proj_actual else 0
        base_peak = max(proj_base) if proj_base else 0
        parts = sorted(h["participation"] for h in homes_out)
        mean_p = sum(parts) / max(len(parts), 1)
        fairness = round(100 * (1 - (max(parts) - min(parts)) / max(mean_p * 8, 1)), 0)

        # Transformer Health & Thermal Loading (Schneider Electric Grid Criterion)
        dt_rating_kva = 100.0  # 100 kVA Feeder Distribution Transformer
        now_kw = round(self._last_net_after, 1)
        dt_load_pct = round(min(140.0, max(0.0, 100.0 * now_kw / (dt_rating_kva * 0.95))), 1)
        dt_temp_c = round(32.0 + (dt_load_pct / 100.0) ** 1.6 * 48.0, 1)
        dt_loss_kw = round(0.012 * dt_rating_kva + 0.038 * dt_rating_kva * (dt_load_pct / 100.0) ** 2, 2)
        base_dt_load_pct = round(min(160.0, max(0.0, 100.0 * base_peak / (dt_rating_kva * 0.95))), 1)
        base_dt_loss_kw = round(0.012 * dt_rating_kva + 0.038 * dt_rating_kva * (base_dt_load_pct / 100.0) ** 2, 2)
        loss_saved_pct = round(max(0.0, 100.0 * (base_dt_loss_kw - dt_loss_kw) / max(base_dt_loss_kw, 0.1)), 1)

        return {
            "time": {"clock": self.clock_str(), "day": self.day + 1, "block": block, "speed": self.speed},
            "city": {**CITIES[self.city], "name": self.city},
            "weather": {"src": self.weather_src, "ghi": round(now_meta["ghi"]), "temp": now_meta["temp"],
                        "cloud": now_meta["cloud"]},
            "storm": {"active": self.storm_active(), "severity": self.storm_severity,
                      "until": self.clock_str(self.storm_until) if self.storm_active() else None},
            "feeder": {"now": round(self._last_net_after, 1), "limit": self.feeder_limit,
                       "base_peak": round(base_peak, 1), "peak_today": round(peak_today, 1),
                       "peak_cut_pct": round(100 * (base_peak - peak_today) / max(base_peak, 1), 1)},
            "battery": {
                "soc": round(self.battery["soc_kwh"], 1), "cap": self.battery["cap_kwh"],
                "pct": round(100 * self.battery["soc_kwh"] / self.battery["cap_kwh"], 0),
                "kw_ch": round(self.battery["kw_ch"], 1), "kw_dis": round(self.battery["kw_dis"], 1),
                "label": self.battery["label"],
                "charged_today": round(self.battery["charged_today"], 1),
                "discharged_today": round(self.battery["discharged_today"], 1),
            },
            "transformer": {
                "rating_kva": dt_rating_kva,
                "load_pct": dt_load_pct,
                "winding_temp_c": dt_temp_c,
                "loss_kw": dt_loss_kw,
                "loss_saved_pct": loss_saved_pct,
                "health_status": "NORMAL" if dt_load_pct < 85 else ("WARNING" if dt_load_pct < 105 else "CRITICAL"),
                "life_extension_yrs": 4.2
            },
            "openadr": {
                "vtn_status": "CONNECTED",
                "ven_id": f"VEN-MSEDCL-{self.city.upper()}-01",
                "profile": "OpenADR 2.0b (Oadr20bProfileB)",
                "last_event_id": self._last_openadr_event_id or "OADR-EVT-STANDBY",
                "market_context": "http://marketcontext.msedcl.gov.in/dr/bharat"
            },
            "kpis": {k: (round(v, 1) if isinstance(v, float) else v) for k, v in self.kpi.items()},
            "tariff": self._tariff_json(),
            "custom_profile": self.custom_profile,
            "fairness_index": fairness,
            "chart": {"labels": labels, "actual": proj_actual, "baseline": proj_base, "solar": solar_arr},
            "homes": homes_out,
            "events": self.events[:32],
            "leaderboard": sorted(homes_out, key=lambda x: -x["wallet"])[:10],
            "dr_active": self.dr_active,
        }

    def dispatch_openadr_event(self, target_kw: float = 20.0, duration_min: int = 60):
        """Triggers an OpenADR 2.0b demand response event from utility VTN."""
        event_id = f"OADR-EVT-{int(time.time())}"
        self._last_openadr_event_id = event_id
        self.log(f"⚡ OpenADR 2.0b signal received from VTN [{event_id}] — Target: {target_kw} kW for {duration_min} min", "dr")
        self._trigger_dr(f"OpenADR 2.0b VTN Dispatch ({event_id})", deficit_kw=target_kw)
        return {
            "event_id": event_id,
            "status": "ACCEPTED",
            "ven_id": f"VEN-MSEDCL-{self.city.upper()}-01",
            "opt_type": "optIn",
            "target_kw": target_kw,
            "duration_min": duration_min
        }

    def trigger_scenario(self, scenario_type: str):
        """Pre-packaged high-impact scenarios for hackathon demonstrations."""
        if scenario_type == "storm":
            self.trigger_storm(severity=0.55, duration_min=60)
            self.log("🌪 Scenario: Monsoon Cloud Bank triggered (Solar -65% for 60 min)", "storm")
        elif scenario_type == "heatwave":
            self.log("🔥 Scenario: Heatwave Overload triggered (Feeder demand +30%)", "storm")
            self._trigger_dr("Heatwave Emergency Demand Surge", deficit_kw=25.0)
        elif scenario_type == "sunset_cliff":
            self.log("🌅 Scenario: Sunset Duck Curve cliff triggered", "opt")
            self._trigger_dr("Solar Sunset Cliff vs Evening Surge", deficit_kw=18.0)
        elif scenario_type == "islanding":
            self.log("🛡 Scenario: Feeder Islanding / Microgrid Mode initiated.", "dr")
            self.battery["soc_kwh"] = max(self.battery["soc_kwh"], 45.0)
            self._trigger_dr("Microgrid Islanding Load Defense", deficit_kw=35.0)
        return {"ok": True, "scenario": scenario_type}
