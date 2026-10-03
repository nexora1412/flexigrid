"""
FlexiGrid — real-world data layer.
- LIVE solar irradiance & weather from Open-Meteo (free, no API key)
- Real indicative Indian constants: MSEDCL-style ToD tariff, CEA emission factor, DR incentive band
"""
import time
import math
import threading
import requests

# ---------------------------------------------------------------- cities
CITIES = {
    "Pune":    {"lat": 18.52, "lon": 73.86, "feeder": "Baner Feeder R-11",       "discom": "MSEDCL"},
    "Dhule":   {"lat": 20.90, "lon": 74.77, "feeder": "Shramik Nagar Feeder F-03","discom": "MSEDCL"},
    "Nagpur":  {"lat": 21.15, "lon": 79.09, "feeder": "Dharampeth Feeder D-07",  "discom": "MSEDCL"},
    "Mumbai":  {"lat": 19.08, "lon": 72.88, "feeder": "Andheri West Feeder",     "discom": "Adani Electricity"},
}

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# --------------------------------------------------- Indian grid constants
# Indicative MSEDCL-style residential time-of-day tariff (₹/kWh)
def tod_price(hour: int) -> float:
    if 6 <= hour < 9 or 18 <= hour < 22:
        return 8.5     # morning + evening peak
    if 0 <= hour < 6:
        return 6.0     # night off-peak
    return 7.0         # day normal

EXPORT_FIT   = 2.5     # ₹/kWh feed-in tariff for surplus rooftop solar (PM-KUSUM style)
DR_INCENTIVE = 4.0     # ₹/kWh paid to homes that defer load in a DR event (Tata BDR incentive band)
CO2_FACTOR   = 0.82    # kg CO2 per kWh, CEA Indian grid baseline (indicative)

# --------------------------------------------------------------- live data
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 900  # 15 min


def _clear_sky_fallback(city: str):
    """Deterministic clear-sky-ish curve used only if the network is down."""
    c = CITIES[city]
    hours = []
    now = time.localtime()
    for h in range(48):  # 2 days
        hr = h % 24
        # bell between 6:00 and 18:00 peaking ~850 W/m2 at noon
        if 6 <= hr <= 18:
            ghi = 850.0 * math.sin(math.pi * (hr - 6) / 12.0) ** 1.3
        else:
            ghi = 0.0
        hours.append({
            "t": f"D+{h//24} {hr:02d}:00",
            "ghi": round(ghi, 1),
            "cloud": 12 + int(10 * math.sin(h)),
            "temp": 31.0 - 6.0 * math.cos(math.pi * (hr - 14) / 12.0),
        })
    return {"source": "clear-sky model (offline fallback)", "lat": c["lat"], "lon": c["lon"], "hours": hours}


def fetch_weather(city: str) -> dict:
    """48h hourly GHI (W/m2), cloud cover %, temperature for the city. Real data via Open-Meteo."""
    with _cache_lock:
        hit = _cache.get(city)
        if hit and time.time() - hit["at"] < CACHE_TTL:
            return hit["data"]

    c = CITIES[city]
    try:
        r = requests.get(
            OPEN_METEO,
            params={
                "latitude": c["lat"],
                "longitude": c["lon"],
                "hourly": "shortwave_radiation,cloud_cover,temperature_2m",
                "timezone": "Asia/Kolkata",
                "forecast_days": 3,
            },
            timeout=12,
        )
        js = r.json()
        hh = js["hourly"]
        hours = [
            {
                "t": hh["time"][i],
                "ghi": hh["shortwave_radiation"][i] or 0,
                "cloud": hh["cloud_cover"][i] or 0,
                "temp": hh["temperature_2m"][i] or 0,
            }
            for i in range(len(hh["time"]))
        ]
        data = {"source": "Open-Meteo • live", "lat": c["lat"], "lon": c["lon"], "hours": hours}
    except Exception:
        data = _clear_sky_fallback(city)

    with _cache_lock:
        _cache[city] = {"at": time.time(), "data": data}
    return data


def ghi_at(weather: dict, hour_index: int) -> float:
    """GHI (W/m2) at absolute hour index from start of the 48h window."""
    hrs = weather["hours"]
    hour_index = max(0, min(hour_index, len(hrs) - 1))
    return float(hrs[hour_index]["ghi"])


def hour_meta(weather: dict, hour_index: int) -> dict:
    hrs = weather["hours"]
    hour_index = max(0, min(hour_index, len(hrs) - 1))
    return hrs[hour_index]


# ============================================================ REAL TARIFF TABLES
# Sources:
#  • MSEDCL LT I(B) residential — MERC MYT Tariff Order FY 2026-27:
#    energy 0-100 ₹5.05, 101-300 ₹10.25, 301-500 ₹13.80; wheeling ₹1.35/kWh;
#    FAC ₹0.679/kWh; fixed ₹135/mo (1-ph) / ₹435/mo (3-ph); electricity duty 16%.
#    (last slab 501+ ₹15.50 marked as estimate)
#  • Adani Electricity Mumbai domestic — MERC MYT Order FY 2025-26 (eff. 2025-04-01):
#    energy 1-100 ₹4.30, 101-300 ₹7.25, 301-500 ₹11.36, >500 ₹12.94;
#    fixed ₹95/kW/mo; electricity duty 16%.
DISCOM_TARIFFS = {
    "MSEDCL": {
        "order": "MSEDCL LT I(B) — MERC MYT Order FY 2026-27",
        "slabs": [(100, 5.05), (300, 10.25), (500, 13.80), (float("inf"), 15.50)],
        "slab_note": "0-100 ₹5.05 · 101-300 ₹10.25 · 301-500 ₹13.80 · 501+ ₹15.50*",
        "wheeling": 1.35, "fac": 0.679, "duty": 0.16,
        "fixed_monthly": 135.0,
        "source": "merc.gov.in tariff order; billcalculator.in summary",
    },
    "Adani Electricity": {
        "order": "Adani Electricity Mumbai Domestic — MERC MYT Order FY 2025-26",
        "slabs": [(100, 4.30), (300, 7.25), (500, 11.36), (float("inf"), 12.94)],
        "slab_note": "0-100 ₹4.30 · 101-300 ₹7.25 · 301-500 ₹11.36 · 501+ ₹12.94",
        "wheeling": 0.0, "fac": 0.0, "duty": 0.16,
        "fixed_monthly": 95.0,
        "source": "MERC MYT 2025-30 order (eff. 01-04-2025)",
    },
}
SLAB_DAY_SCALE = 1 / 30.0   # monthly slab thresholds pro-rated to a daily cycle


def retail_marginal(discom: str, day_kwh: float) -> float:
    """Marginal retail price (₹/kWh) for the next unit, given today's cumulative
    imported kWh, with monthly slabs pro-rated daily. Includes wheeling, FAC and duty."""
    t = DISCOM_TARIFFS.get(discom, DISCOM_TARIFFS["MSEDCL"])
    energy = t["slabs"][-1][1]
    for cap, rate in t["slabs"]:
        if day_kwh < cap * SLAB_DAY_SCALE:
            energy = rate
            break
    return (energy + t["wheeling"] + t["fac"]) * (1 + t["duty"])


def tariff_table(discom: str) -> dict:
    return DISCOM_TARIFFS.get(discom, DISCOM_TARIFFS["MSEDCL"])


# DISCOM-side avoided cost proxy (₹/kWh) — what reducing import at hour h is worth
# to the utility (marginal power-purchase value, MYT APPC-informed, INDICATIVE).
# Residential LT in Maharashtra is NOT time-of-day billed; flexibility programs are
# valued against this system cost, exactly as in Tata Power's Mumbai DR program.
def avoided_cost(hour: int) -> float:
    if 18 <= hour < 22:
        return 8.0
    if 6 <= hour < 9:
        return 7.5
    if 0 <= hour < 6:
        return 5.0
    return 6.5


# ==================================================== iAWE CALIBRATION ANCHORS
# Real measured facts from the peer-reviewed iAWE dataset/paper used to calibrate
# our home load model (raw traces require manual download from iawe.github.io —
# sandbox-blocked — so we embed the published anchors and expose a CSV upload API).
IAWE = {
    "cite": "Batra, Gulati, Singh, Srivastava — “It’s Different: Insights into home energy consumption in India”, ACM BuildSys 2013 (iAWE, IIIT Delhi)",
    "facts": {
        "duration": "73 days, 1 Hz, 33 sensors, 1 Delhi home",
        "voltage_band_v": [180, 250],
        "daily_kwh_range": [10, 30],
        "note": "frequent outages; dominant fan/AC seasonal share; heavy morning-evening structure",
    },
}
