"""
Verification test suite for FlexiGrid backend and Supabase integrations
"""
import sys
import os
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_endpoints():
    print("Testing GET / ...")
    r = client.get("/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "FlexiGrid" in r.text
    print("  -> Passed")

    print("Testing GET /api/state ...")
    r = client.get("/api/state")
    assert r.status_code == 200
    state = r.json()
    assert "feeder" in state
    assert "transformer" in state
    assert "openadr" in state
    assert "battery" in state
    print(f"  -> Passed. Feeder now: {state['feeder']['now']} kW, Peak Cut: {state['feeder']['peak_cut_pct']}%")

    print("Testing GET /api/supabase/status ...")
    r = client.get("/api/supabase/status")
    assert r.status_code == 200
    sb = r.json()
    assert "mode" in sb
    print(f"  -> Passed. Supabase status: {sb['mode']}")

    print("Testing POST /api/auth/login (Demo Operator) ...")
    r = client.post("/api/auth/login", json={"email": "operator@msedcl.gov.in", "password": "msedcl2026"})
    assert r.status_code == 200
    auth_data = r.json()
    assert auth_data.get("ok") is True
    print(f"  -> Passed. Logged in as: {auth_data['user']['full_name']} ({auth_data['user']['role']})")

    print("Testing POST /api/auth/signup (New Consumer) ...")
    r = client.post("/api/auth/signup", json={
        "email": f"test_judge_{int(time.time())}@yuvayodha.in",
        "password": "judgepassword123",
        "full_name": "Hackathon Judge",
        "role": "prosumer",
        "home_id": "H05",
        "upi_vpa": "judge@okhdfcbank"
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    print("  -> Passed. Signup created successfully")

    print("Testing POST /api/openadr/dispatch ...")
    r = client.post("/api/openadr/dispatch", json={"target_kw": 25.0, "duration_min": 60})
    assert r.status_code == 200
    oadr = r.json()
    assert oadr.get("status") == "ACCEPTED"
    print(f"  -> Passed. OpenADR event ID: {oadr.get('event_id')}")

    print("Testing POST /api/sim/scenario (storm) ...")
    r = client.post("/api/sim/scenario", json={"scenario": "storm"})
    assert r.status_code == 200
    print("  -> Passed. Scenario triggered")

    print("Testing POST /api/wallet/payout ...")
    # First get a home with balance
    r_state = client.get("/api/state").json()
    top_home = r_state["leaderboard"][0]
    payout_amt = min(top_home["wallet"], 50.0)
    r = client.post("/api/wallet/payout", json={
        "home_id": top_home["id"],
        "amount_inr": payout_amt,
        "upi_vpa": f"{top_home['name'].lower()}@upi"
    })
    assert r.status_code == 200
    payout = r.json()
    assert payout.get("ok") is True
    print(f"  -> Passed. UPI Payout settled: {payout.get('upi_ref')}")

    print("Testing GET /api/export/report ...")
    r = client.get("/api/export/report")
    assert r.status_code == 200
    rep = r.json()
    assert "regulatory_framework" in rep
    print(f"  -> Passed. Audit report generated for: {rep['feeder']}")

    print("\nALL BACKEND & SUPABASE TESTS PASSED 100%!")

if __name__ == "__main__":
    test_endpoints()
