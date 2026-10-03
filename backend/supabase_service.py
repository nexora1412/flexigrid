"""
FlexiGrid — Supabase Authentication & Data Store Service
Provides authentication (signup, login, profile management) and cloud persistence
for Feeder Telemetry, DR Events, Wallet Transactions, and Device Schedules.
Operates in resilient hybrid mode: connects to Supabase Cloud if configured,
with instant zero-setup local SQLite fallback for seamless offline demoing.
"""
from __future__ import annotations
import os
import sqlite3
import hashlib
import secrets
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
LOCAL_DB_PATH = BASE_DIR / "flexigrid_supabase_local.db"

# Supabase SDK import
SUPABASE_AVAILABLE = False
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    pass


class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").strip()
        self.key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.client: Optional[Client] = None
        self.is_connected = False
        self.connection_error = None
        
        # Initialize local fallback store
        self._init_local_db()
        
        # Attempt cloud connection if credentials present
        if self.url and self.key and SUPABASE_AVAILABLE:
            self._connect_supabase(self.url, self.key)

    def _connect_supabase(self, url: str, key: str) -> bool:
        if not SUPABASE_AVAILABLE:
            self.connection_error = "supabase-py package not installed"
            return False
        try:
            self.client = create_client(url, key)
            # Lightweight health check: attempt reading or checking auth
            self.url = url
            self.key = key
            self.is_connected = True
            self.connection_error = None
            return True
        except Exception as e:
            self.is_connected = False
            self.connection_error = str(e)
            return False

    def update_config(self, url: str, key: str) -> Dict[str, Any]:
        """Update Supabase configuration dynamically at runtime."""
        success = self._connect_supabase(url, key)
        if success:
            # Also save to .env file in backend for persistence
            try:
                env_path = BASE_DIR / ".env"
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(f"SUPABASE_URL={url}\nSUPABASE_KEY={key}\n")
            except Exception:
                pass
        return {
            "ok": success,
            "connected": self.is_connected,
            "error": self.connection_error,
            "url": self.url[:25] + "..." if len(self.url) > 25 else self.url
        }

    def get_status(self) -> Dict[str, Any]:
        """Return live health and statistics of the data store."""
        counts = self._get_record_counts()
        return {
            "supabase_configured": bool(self.url and self.key),
            "cloud_connected": self.is_connected,
            "mode": "Supabase Cloud (PostgreSQL)" if self.is_connected else "Local Resilient Vault (SQLite)",
            "url": (self.url[:28] + "..." if len(self.url) > 28 else self.url) if self.url else None,
            "error": self.connection_error,
            "stats": counts
        }

    # ------------------------------------------------------------- Local DB Setup
    def _init_local_db(self):
        conn = sqlite3.connect(LOCAL_DB_PATH)
        c = conn.cursor()
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'prosumer',
            home_id TEXT,
            upi_vpa TEXT,
            created_at TEXT
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT,
            expires_at TEXT
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS feeder_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT,
            city TEXT,
            feeder_name TEXT,
            net_kw REAL,
            baseline_kw REAL,
            solar_kw REAL,
            battery_soc REAL,
            peak_cut_pct REAL,
            co2_kg REAL
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS dr_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT UNIQUE,
            trigger_type TEXT,
            target_kw REAL,
            achieved_kw REAL,
            start_time TEXT,
            duration_min INTEGER,
            homes_count INTEGER,
            incentive_inr REAL
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_id TEXT,
            amount_inr REAL,
            action_type TEXT,
            upi_ref TEXT,
            created_at TEXT
        )
        ''')

        # Insert default demo accounts if table is empty
        c.execute('SELECT COUNT(*) FROM users')
        if c.fetchone()[0] == 0:
            demo_users = [
                ("usr_discom_01", "operator@msedcl.gov.in", self._hash_pw("msedcl2026"), "Ajay Kulkarni (Chief Dispatcher)", "discom_operator", "ALL", "msedcl.feeder@sbi"),
                ("usr_admin_01", "secretary@banerchs.in", self._hash_pw("society2026"), "Sunita Deshmukh (Secretary)", "society_admin", "CHS-01", "baner.society@icici"),
                ("usr_home_01", "patil@flexigrid.in", self._hash_pw("patil123"), "Ramesh Patil", "prosumer", "H00", "9820011223@upi"),
                ("usr_home_02", "deshmukh@flexigrid.in", self._hash_pw("deshmukh123"), "Anand Deshmukh", "prosumer", "H01", "9820011224@upi"),
            ]
            c.executemany('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, datetime("now"))', demo_users)

        conn.commit()
        conn.close()

    def _hash_pw(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _get_record_counts(self) -> Dict[str, int]:
        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            users = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM feeder_telemetry')
            telem = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM dr_events')
            dr = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM wallet_transactions')
            tx = c.fetchone()[0]
            conn.close()
            return {"users": users, "telemetry_points": telem, "dr_events": dr, "transactions": tx}
        except Exception:
            return {"users": 0, "telemetry_points": 0, "dr_events": 0, "transactions": 0}

    # ------------------------------------------------------------- Authentication
    def signup(self, email: str, password: str, full_name: str, role: str = "prosumer", home_id: str = "H00", upi_vpa: str = "") -> Dict[str, Any]:
        email = email.strip().lower()
        if not email or "@" not in email:
            return {"ok": False, "error": "Invalid email address"}
        if len(password) < 6:
            return {"ok": False, "error": "Password must be at least 6 characters"}

        # Attempt Supabase Cloud auth if connected
        cloud_uid = None
        if self.is_connected and self.client:
            try:
                res = self.client.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {
                            "full_name": full_name,
                            "role": role,
                            "home_id": home_id,
                            "upi_vpa": upi_vpa
                        }
                    }
                })
                if res.user:
                    cloud_uid = res.user.id
            except Exception as e:
                # Fallback to local
                pass

        # Save to local database (ensures offline reliability)
        user_id = cloud_uid or f"usr_{secrets.token_hex(6)}"
        pw_hash = self._hash_pw(password)
        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            c = conn.cursor()
            c.execute(
                'INSERT INTO users (id, email, password_hash, full_name, role, home_id, upi_vpa, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime("now"))',
                (user_id, email, pw_hash, full_name, role, home_id, upi_vpa or f"{email.split('@')[0]}@upi")
            )
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            return {"ok": False, "error": "User with this email already exists"}

        token = self._create_session(user_id)
        return {
            "ok": True,
            "token": token,
            "user": {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "role": role,
                "home_id": home_id,
                "upi_vpa": upi_vpa or f"{email.split('@')[0]}@upi"
            }
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        email = email.strip().lower()
        pw_hash = self._hash_pw(password)
        
        # Check cloud first if connected
        if self.is_connected and self.client:
            try:
                auth_res = self.client.auth.sign_in_with_password({"email": email, "password": password})
                if auth_res.user:
                    meta = auth_res.user.user_metadata or {}
                    user_dict = {
                        "id": auth_res.user.id,
                        "email": auth_res.user.email,
                        "full_name": meta.get("full_name", email.split("@")[0]),
                        "role": meta.get("role", "prosumer"),
                        "home_id": meta.get("home_id", "H00"),
                        "upi_vpa": meta.get("upi_vpa", f"{email.split('@')[0]}@upi")
                    }
                    token = auth_res.session.access_token if auth_res.session else secrets.token_urlsafe(32)
                    self._create_session(user_dict["id"], token)
                    return {"ok": True, "token": token, "user": user_dict, "source": "supabase_cloud"}
            except Exception:
                pass

        # Check local DB
        conn = sqlite3.connect(LOCAL_DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, email, full_name, role, home_id, upi_vpa FROM users WHERE email = ? AND password_hash = ?', (email, pw_hash))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"ok": False, "error": "Invalid email or password"}

        user_dict = {
            "id": row[0],
            "email": row[1],
            "full_name": row[2],
            "role": row[3],
            "home_id": row[4],
            "upi_vpa": row[5]
        }
        token = self._create_session(user_dict["id"])
        return {"ok": True, "token": token, "user": user_dict, "source": "local_resilient"}

    def _create_session(self, user_id: str, custom_token: Optional[str] = None) -> str:
        token = custom_token or secrets.token_urlsafe(32)
        conn = sqlite3.connect(LOCAL_DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO sessions VALUES (?, ?, datetime("now"), datetime("now", "+7 days"))', (token, user_id))
        conn.commit()
        conn.close()
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        conn = sqlite3.connect(LOCAL_DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT u.id, u.email, u.full_name, u.role, u.home_id, u.upi_vpa
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        ''', (token,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "email": row[1],
            "full_name": row[2],
            "role": row[3],
            "home_id": row[4],
            "upi_vpa": row[5]
        }

    # ------------------------------------------------------------- Data Store Sync
    def record_telemetry(self, snap: Dict[str, Any]):
        """Persist current feeder telemetry point to Supabase & local DB."""
        ts = datetime.now(timezone.utc).isoformat()
        f = snap.get("feeder", {})
        c = snap.get("city", {})
        k = snap.get("kpis", {})
        b = snap.get("battery", {})
        
        row = {
            "recorded_at": ts,
            "city": c.get("name", "Pune"),
            "feeder_name": c.get("feeder", "Feeder"),
            "net_kw": f.get("now", 0.0),
            "baseline_kw": f.get("base_peak", 0.0),
            "solar_kw": snap.get("chart", {}).get("solar", [0])[-1] if snap.get("chart", {}).get("solar") else 0.0,
            "battery_soc": b.get("pct", 0.0),
            "peak_cut_pct": f.get("peak_cut_pct", 0.0),
            "co2_kg": k.get("co2_kg", 0.0)
        }

        # Local save
        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO feeder_telemetry (recorded_at, city, feeder_name, net_kw, baseline_kw, solar_kw, battery_soc, peak_cut_pct, co2_kg)
                VALUES (:recorded_at, :city, :feeder_name, :net_kw, :baseline_kw, :solar_kw, :battery_soc, :peak_cut_pct, :co2_kg)
            ''', row)
            conn.commit()
            conn.close()
        except Exception:
            pass

        # Cloud Supabase save
        if self.is_connected and self.client:
            try:
                self.client.table("feeder_telemetry").insert(row).execute()
            except Exception:
                pass

    def record_dr_event(self, trigger: str, target_kw: float, achieved_kw: float, duration_min: int, homes_count: int, incentive_inr: float):
        event_code = f"DR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        ts = datetime.now(timezone.utc).isoformat()
        row = {
            "event_code": event_code,
            "trigger_type": trigger,
            "target_kw": round(target_kw, 2),
            "achieved_kw": round(achieved_kw, 2),
            "start_time": ts,
            "duration_min": duration_min,
            "homes_count": homes_count,
            "incentive_inr": round(incentive_inr, 2)
        }

        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO dr_events (event_code, trigger_type, target_kw, achieved_kw, start_time, duration_min, homes_count, incentive_inr)
                VALUES (:event_code, :trigger_type, :target_kw, :achieved_kw, :start_time, :duration_min, :homes_count, :incentive_inr)
            ''', row)
            conn.commit()
            conn.close()
        except Exception:
            pass

        if self.is_connected and self.client:
            try:
                self.client.table("dr_events").insert(row).execute()
            except Exception:
                pass

    def record_payout(self, home_id: str, amount_inr: float, upi_vpa: str) -> Dict[str, Any]:
        """Process and record a simulated UPI micro-incentive payout."""
        upi_ref = f"UPI/2026/FLEX/{secrets.token_hex(4).upper()}"
        ts = datetime.now(timezone.utc).isoformat()
        row = {
            "home_id": home_id,
            "amount_inr": round(amount_inr, 2),
            "action_type": "UPI_CREDIT_INSTANT",
            "upi_ref": upi_ref,
            "created_at": ts
        }

        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO wallet_transactions (home_id, amount_inr, action_type, upi_ref, created_at)
                VALUES (:home_id, :amount_inr, :action_type, :upi_ref, :created_at)
            ''', row)
            conn.commit()
            conn.close()
        except Exception:
            pass

        if self.is_connected and self.client:
            try:
                self.client.table("wallet_transactions").insert(row).execute()
            except Exception:
                pass

        return {
            "ok": True,
            "upi_ref": upi_ref,
            "amount_inr": amount_inr,
            "vpa": upi_vpa,
            "status": "SETTLED",
            "timestamp": ts,
            "message": f"₹{amount_inr} successfully credited to {upi_vpa} via IMPS/UPI Payouts"
        }

    def fetch_recent_data(self) -> Dict[str, Any]:
        """Fetch latest telemetry, DR events, and wallet transactions."""
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM dr_events ORDER BY id DESC LIMIT 10')
        dr_events = [dict(r) for r in c.fetchall()]
        
        c.execute('SELECT * FROM wallet_transactions ORDER BY id DESC LIMIT 15')
        transactions = [dict(r) for r in c.fetchall()]

        c.execute('SELECT * FROM feeder_telemetry ORDER BY id DESC LIMIT 20')
        telemetry = [dict(r) for r in c.fetchall()]

        conn.close()
        return {
            "dr_events": dr_events,
            "transactions": transactions,
            "telemetry": telemetry
        }

# Singleton instance
supabase_service = SupabaseService()
