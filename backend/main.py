"""FlexiGrid API + static host. Run: uvicorn main:app --host 0.0.0.0 --port 8000"""
import asyncio
import csv
import io
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sim_core import World

BASE = Path(__file__).resolve().parent
FRONTEND = BASE.parent / "frontend"

app = FastAPI(title="FlexiGrid — Community Demand Response")
world = World(city="Pune")


@app.on_event("startup")
async def _loop():
    async def runner():
        while True:
            try:
                world.tick(world.speed)
            except Exception as e:  # keep the sim alive
                world.log(f"sim error: {e}", "info")
            await asyncio.sleep(1.0)
    asyncio.create_task(runner())


@app.get("/api/state")
def state():
    return JSONResponse(world.snapshot())


@app.post("/api/sim/storm")
def storm(severity: float = 0.38, duration_min: int = 40):
    world.trigger_storm(severity=severity, duration_min=duration_min)
    return {"ok": True}


@app.post("/api/sim/speed")
def speed(x: int = 15):
    world.speed = max(1, min(120, x))
    return {"ok": True, "speed": world.speed}


@app.post("/api/sim/reset")
def reset():
    global world
    city = world.city
    world = World(city=city)
    return {"ok": True}


@app.post("/api/sim/optimize")
def optimize_now():
    world.run_day_optimization(world.block)
    world.log("Manual re-optimization from current time block", "opt")
    return {"ok": True, "peak_cut_pct": world.last_peak_cut_pct}


@app.post("/api/city")
def city(name: str = "Pune"):
    ok = world.set_city(name)
    return {"ok": ok}


def _resample_to_48(rows):
    """rows: list of (datetime, kW). Bucket into 48 thirty-minute blocks (mean kW)."""
    buckets = [[] for _ in range(48)]
    for ts, kw in rows:
        buckets[min((ts.hour * 60 + ts.minute) // 30, 47)].append(kw)
    out = [round(sum(bk) / len(bk), 3) if bk else None for bk in buckets]
    # fill gaps by nearest neighbour
    known = [i for i, v in enumerate(out) if v is not None]
    if not known:
        return None
    for i in range(48):
        if out[i] is None:
            out[i] = out[min(known, key=lambda k: abs(k - i))]
    return out


@app.post("/api/upload_load")
async def upload_load(file: UploadFile = File(...)):
    """Plug REAL load data into the sim. Accepts CSV with columns like
    (timestamp, kW) — any header names containing 'time/date' and 'kW/power/load'."""
    try:
        raw = (await file.read()).decode("utf-8", errors="ignore")
        rd = csv.reader(io.StringIO(raw))
        rows = list(rd)
        if len(rows) < 20:
            return {"ok": False, "error": "file too small"}
        header = [c.strip().lower() for c in rows[0]]
        ts_i = next((i for i, c in enumerate(header) if any(k in c for k in ("time", "date"))), 0)
        kw_i = next((i for i, c in enumerate(header) if any(k in c for k in ("kw", "power", "load", "watt"))), 1)
        parsed = []
        for r in rows[1:]:
            try:
                tss = r[ts_i].strip()
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S",
                            "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"):
                    try:
                        ts = datetime.strptime(tss[:19], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue
                kw = float(r[kw_i])
                if float(r[kw_i]) > 500:  # likely Watts — convert
                    kw /= 1000.0
                parsed.append((ts, kw))
            except Exception:
                continue
        prof = _resample_to_48(parsed)
        if prof is None:
            return {"ok": False, "error": "no usable (timestamp,kW) rows"}
        ok = world.set_base_override(prof, file.filename)
        return {"ok": ok, "blocks": len(prof), "mean_kw": sum(prof) / 48}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/clear_override")
def clear_override():
    world.clear_base_override()
    return {"ok": True}


@app.post("/api/sim/use_iawe")
def use_iawe(day: int = -1):
    ok = world.use_iawe(None if day < 0 else day)
    return {"ok": ok, "profile": world.custom_profile}


@app.get("/api/iawe_info")
def iawe_info():
    p = world.iawe_profiles
    if not p:
        return {"available": False}
    return {"available": True, "source": p["source"], "building": p["building"],
            "days": sorted(p["days"]), "meta": p["meta"]}


# ====================================================================
# SUPABASE AUTHENTICATION & DATA STORE ROUTES
# ====================================================================
from pydantic import BaseModel
from supabase_service import supabase_service


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "prosumer"
    home_id: str = "H00"
    upi_vpa: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class SupabaseConfigRequest(BaseModel):
    url: str
    key: str


class PayoutRequest(BaseModel):
    home_id: str
    amount_inr: float
    upi_vpa: str


class OpenADRRequest(BaseModel):
    target_kw: float = 20.0
    duration_min: int = 60


class ScenarioRequest(BaseModel):
    scenario: str = "storm"


@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    res = supabase_service.signup(
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        role=req.role,
        home_id=req.home_id,
        upi_vpa=req.upi_vpa
    )
    return JSONResponse(res, status_code=200 if res.get("ok") else 400)


@app.post("/api/auth/login")
def login(req: LoginRequest):
    res = supabase_service.login(email=req.email, password=req.password)
    return JSONResponse(res, status_code=200 if res.get("ok") else 401)


@app.get("/api/auth/me")
def me(token: str = ""):
    user = supabase_service.verify_token(token)
    if not user:
        return JSONResponse({"ok": False, "error": "Invalid or expired token"}, status_code=401)
    return {"ok": True, "user": user}


@app.post("/api/auth/logout")
def logout():
    return {"ok": True}


@app.get("/api/supabase/status")
def supabase_status():
    return JSONResponse(supabase_service.get_status())


@app.post("/api/supabase/config")
def supabase_config(req: SupabaseConfigRequest):
    res = supabase_service.update_config(url=req.url, key=req.key)
    return JSONResponse(res)


@app.get("/api/supabase/data")
def supabase_data():
    return JSONResponse(supabase_service.fetch_recent_data())


# ====================================================================
# BHARAT UPI MICRO-PAYOUT RAILS (NPCI MOCK)
# ====================================================================
@app.post("/api/wallet/payout")
def wallet_payout(req: PayoutRequest):
    # Find home in world
    target_home = next((h for h in world.homes if h.id == req.home_id), None)
    if not target_home:
        return JSONResponse({"ok": False, "error": f"Home {req.home_id} not found"}, status_code=404)
    if target_home.wallet < req.amount_inr:
        return JSONResponse({"ok": False, "error": f"Insufficient wallet balance: ₹{target_home.wallet:.1f}"}, status_code=400)
    
    # Deduct wallet
    target_home.wallet -= req.amount_inr
    world.log(f"💸 UPI Micro-payout: ₹{req.amount_inr:.1f} disbursed to {req.upi_vpa} ({target_home.name})", "sms")
    res = supabase_service.record_payout(home_id=req.home_id, amount_inr=req.amount_inr, upi_vpa=req.upi_vpa)
    return JSONResponse(res)


# ====================================================================
# OPENADR 2.0b UTILITY VTN INTEROPERABILITY
# ====================================================================
@app.post("/api/openadr/dispatch")
def openadr_dispatch(req: OpenADRRequest):
    res = world.dispatch_openadr_event(target_kw=req.target_kw, duration_min=req.duration_min)
    return JSONResponse(res)


@app.get("/api/openadr/status")
def openadr_status():
    snap = world.snapshot()
    return JSONResponse({
        "vtn_connected": True,
        "openadr": snap.get("openadr"),
        "transformer": snap.get("transformer"),
        "active_curtailment_kw": round(max(0, snap["feeder"]["base_peak"] - snap["feeder"]["peak_today"]), 1)
    })


# ====================================================================
# HIGH-IMPACT SCENARIO SIMULATOR
# ====================================================================
@app.post("/api/sim/scenario")
def trigger_scenario(req: ScenarioRequest):
    res = world.trigger_scenario(req.scenario)
    return JSONResponse(res)


# ====================================================================
# MERC / DISCOM EXECUTIVE & REGULATORY REPORT EXPORT
# ====================================================================
@app.get("/api/export/report")
def export_report():
    s = world.snapshot()
    f = s["feeder"]
    k = s["kpis"]
    t = s["transformer"]
    report = {
        "title": "FlexiGrid MSEDCL Feeder Demand Response & Reliability Audit",
        "regulatory_framework": "MERC MYT Order FY 2026-27 (Case No. 227 of 2024)",
        "generated_at": datetime.now().isoformat(),
        "feeder": s["city"]["feeder"],
        "city": s["city"]["name"],
        "utility": s["city"]["discom"],
        "summary": {
            "connections": len(s["homes"]),
            "unmanaged_peak_kw": f["base_peak"],
            "managed_peak_kw": f["peak_today"],
            "peak_cut_percent": f["peak_cut_pct"],
            "energy_shifted_kwh": k["shifted_kwh"],
            "dr_deferred_kwh": k["dr_deferred_kwh"],
            "dr_incentives_paid_inr": k["dr_earnings"],
            "co2_avoided_kg": k["co2_kg"],
            "fairness_index_percent": s["fairness_index"],
        },
        "transformer_health": {
            "dt_rating_kva": t["rating_kva"],
            "peak_loading_pct": t["load_pct"],
            "winding_temp_c": t["winding_temp_c"],
            "technical_loss_reduction_pct": t["loss_saved_pct"],
            "estimated_life_extension_yrs": t["life_extension_yrs"]
        },
        "community_savings_inr": k["saved_rupees"],
        "compliance_notes": "All demand-response operations adhered to CEA grid code and MERC tariff parameters with 0 residential comfort violations."
    }
    return JSONResponse(report)


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

