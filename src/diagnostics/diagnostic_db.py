"""
Diagnostic Database Manager (SQLite)
Persistently stores all hardware & software inspection results across sessions,
including mobile web QR diagnostic submissions, USB plug-and-play, and ADB tests.
"""

import os
import json
import sqlite3
import time
from typing import Dict, Any, Optional, List
import pandas as pd


class DiagnosticDatabase:
    """Manages SQLite storage for smartphone hardware and software diagnostic records."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "diagnostic_history.db")
        else:
            self.db_path = db_path
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database schema and migrates old schema if needed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if migration from older session_id UNIQUE constraint is required
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='diagnostic_sessions';")
            tbl_info = cursor.fetchone()
            if tbl_info and tbl_info[0] and "session_id TEXT UNIQUE" in tbl_info[0]:
                try:
                    cursor.execute("ALTER TABLE diagnostic_sessions RENAME TO diagnostic_sessions_old;")
                    cursor.execute("""
                    CREATE TABLE diagnostic_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id TEXT UNIQUE NOT NULL,
                        session_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        brand TEXT,
                        model TEXT,
                        market_name TEXT,
                        device_type TEXT,
                        connection_type TEXT,
                        os_version TEXT,
                        screen_res TEXT,
                        gpu_chipset TEXT,
                        battery_level INTEGER,
                        battery_health INTEGER,
                        battery_charging INTEGER,
                        touch_passed INTEGER,
                        touch_cells_passed INTEGER,
                        touch_total_cells INTEGER,
                        sensors_passed INTEGER,
                        audio_passed INTEGER,
                        oem_status TEXT,
                        penalty_points REAL,
                        functional_score_pct REAL,
                        functional_grade TEXT,
                        raw_json TEXT,
                        notes TEXT
                    );
                    """)
                    cursor.execute("""
                    INSERT INTO diagnostic_sessions (
                        record_id, session_id, created_at, brand, model, market_name, device_type, connection_type,
                        os_version, screen_res, gpu_chipset, battery_level, battery_health, battery_charging,
                        touch_passed, touch_cells_passed, touch_total_cells, sensors_passed, audio_passed,
                        oem_status, penalty_points, functional_score_pct, functional_grade, raw_json, notes
                    )
                    SELECT
                        session_id || '_rec' || id, session_id, created_at, brand, model, market_name, device_type, connection_type,
                        os_version, screen_res, gpu_chipset, battery_level, battery_health, battery_charging,
                        touch_passed, touch_cells_passed, touch_total_cells, sensors_passed, audio_passed,
                        oem_status, penalty_points, functional_score_pct, functional_grade, raw_json, notes
                    FROM diagnostic_sessions_old;
                    """)
                    cursor.execute("DROP TABLE diagnostic_sessions_old;")
                except Exception as ex:
                    print(f"[DiagnosticDB Migration Warning] {ex}")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS diagnostic_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                market_name TEXT,
                device_type TEXT,
                connection_type TEXT,
                os_version TEXT,
                screen_res TEXT,
                gpu_chipset TEXT,
                battery_level INTEGER,
                battery_health INTEGER,
                battery_charging INTEGER,
                touch_passed INTEGER,
                touch_cells_passed INTEGER,
                touch_total_cells INTEGER,
                sensors_passed INTEGER,
                audio_passed INTEGER,
                oem_status TEXT,
                penalty_points REAL,
                functional_score_pct REAL,
                functional_grade TEXT,
                raw_json TEXT,
                notes TEXT
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON diagnostic_sessions(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_record_id ON diagnostic_sessions(record_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON diagnostic_sessions(created_at);")
            conn.commit()

    def save_diagnostic(self, session_id: str, data: Any, record_id: Optional[str] = None) -> bool:
        """
        Saves a diagnostic record or payload dictionary to SQLite.
        Guarantees multi-device isolation using unique record_id.
        Accepts either FullDiagnosticRecord or raw mobile payload dict.
        """
        try:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            brand = "Smartphone"
            model = "Perangkat"
            market_name = "Smartphone"
            device_type = "mobile_web"
            connection_type = "QR Web Scanner"
            os_version = "-"
            screen_res = "-"
            gpu_chipset = "-"
            battery_level = 90
            battery_health = 90
            battery_charging = 0
            touch_passed = 1
            touch_cells_passed = 24
            touch_total_cells = 24
            sensors_passed = 1
            audio_passed = 1
            oem_status = "GENUINE / LOLOS"
            penalty_points = 0.0
            functional_score_pct = 100.0
            functional_grade = "PASS (A/B)"
            raw_json_str = "{}"
            notes = ""

            # Check if data is FullDiagnosticRecord
            if hasattr(data, "device") and hasattr(data, "battery"):
                dev = getattr(data, "device", None)
                bat = getattr(data, "battery", None)
                sens = getattr(data, "sensors", None)
                inter = getattr(data, "interactive_test", None)
                oem = getattr(data, "oem_authenticity", None)

                if dev:
                    brand = dev.brand
                    model = dev.model
                    market_name = dev.market_name
                    device_type = dev.device_type
                    connection_type = dev.connection_type
                    os_version = dev.os_version

                if bat:
                    battery_level = bat.level_pct
                    battery_health = bat.health_pct
                    battery_charging = 1 if bat.is_charging else 0

                if inter:
                    touch_passed = 1 if inter.touch_grid_passed else 0
                    touch_cells_passed = 24 if inter.touch_grid_passed else 18
                    audio_passed = 1 if inter.audio_playback_ok else 0

                if sens:
                    sensors_passed = 1 if getattr(sens, "all_healthy", True) else 0

                if oem:
                    oem_status = getattr(oem, "authenticity_verdict", "ORIGINAL")

                penalty_points = float(getattr(data, "total_penalty_dpi", 0.0))
                functional_score_pct = float(getattr(data, "functional_score_pct", 100.0))
                functional_grade = str(getattr(data, "functional_grade", "PASS (A/B)"))
                raw_json_str = json.dumps({
                    "session_id": session_id,
                    "brand": brand,
                    "model": model,
                    "score": functional_score_pct,
                    "grade": functional_grade
                })

            elif isinstance(data, dict):
                # Payload from mobile web
                brand = data.get("brand", "Smartphone")
                model = data.get("model", "Mobile Client")
                market_name = data.get("device_model", f"{brand} {model}")
                device_type = "ios" if data.get("is_ios") else "android"
                connection_type = "QR Web Scanner (Nol-Sentuh)"
                os_version = data.get("os_version", data.get("user_agent", "Mobile Browser")[:60])
                screen_res = f"{data.get('screen_width', '-')}x{data.get('screen_height', '-')}"
                gpu_chipset = data.get("gpu_renderer", "-")

                bat = data.get("battery", {})
                battery_level = bat.get("level_pct", 90)
                battery_health = bat.get("health_pct", 90)
                battery_charging = 1 if bat.get("is_charging") else 0

                touch = data.get("touchscreen", {})
                touch_passed = 1 if touch.get("zero_deadzone", True) else 0
                touch_cells_passed = touch.get("cells_passed", 24)
                touch_total_cells = touch.get("total_cells", 24)

                sens = data.get("sensors", {})
                sensors_passed = 1 if sens.get("gyro_responsive", True) else 0

                aud = data.get("audio_haptic", {})
                audio_passed = 1 if aud.get("passed", True) else 0

                penalty_points = 0.0 if touch_passed else 15.0
                if battery_health < 80:
                    penalty_points += 10.0
                functional_score_pct = max(0.0, 100.0 - (penalty_points * 2.5))
                functional_grade = "PASS (A/B)" if penalty_points == 0.0 else ("MINOR_WARNING (B)" if penalty_points <= 10.0 else "FAIL (D)")
                raw_json_str = json.dumps(data)

            # Determine unique record_id to avoid multi-device overwrites
            if record_id:
                rec_id = record_id
            elif isinstance(data, dict):
                c_dev_id = data.get("client_device_id") or data.get("device_id")
                rec_id = data.get("record_id") or (f"{session_id}_{c_dev_id}" if c_dev_id else f"{session_id}_{int(time.time() * 1000) % 1000000:06d}")
            else:
                dev_serial = getattr(getattr(data, "device", None), "serial", None)
                rec_id = f"{session_id}_{dev_serial}" if dev_serial else f"{session_id}_{int(time.time() * 1000) % 1000000:06d}"

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO diagnostic_sessions (
                    record_id, session_id, created_at, brand, model, market_name, device_type, connection_type,
                    os_version, screen_res, gpu_chipset, battery_level, battery_health, battery_charging,
                    touch_passed, touch_cells_passed, touch_total_cells, sensors_passed, audio_passed,
                    oem_status, penalty_points, functional_score_pct, functional_grade, raw_json, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    session_id = excluded.session_id,
                    created_at = excluded.created_at,
                    brand = excluded.brand,
                    model = excluded.model,
                    market_name = excluded.market_name,
                    device_type = excluded.device_type,
                    connection_type = excluded.connection_type,
                    os_version = excluded.os_version,
                    screen_res = excluded.screen_res,
                    gpu_chipset = excluded.gpu_chipset,
                    battery_level = excluded.battery_level,
                    battery_health = excluded.battery_health,
                    battery_charging = excluded.battery_charging,
                    touch_passed = excluded.touch_passed,
                    touch_cells_passed = excluded.touch_cells_passed,
                    touch_total_cells = excluded.touch_total_cells,
                    sensors_passed = excluded.sensors_passed,
                    audio_passed = excluded.audio_passed,
                    oem_status = excluded.oem_status,
                    penalty_points = excluded.penalty_points,
                    functional_score_pct = excluded.functional_score_pct,
                    functional_grade = excluded.functional_grade,
                    raw_json = excluded.raw_json,
                    notes = excluded.notes;
                """, (
                    rec_id, session_id, now_str, brand, model, market_name, device_type, connection_type,
                    os_version, screen_res, gpu_chipset, battery_level, battery_health, battery_charging,
                    touch_passed, touch_cells_passed, touch_total_cells, sensors_passed, audio_passed,
                    oem_status, penalty_points, functional_score_pct, functional_grade, raw_json_str, notes
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to save diagnostic record {session_id}: {e}")
            return False

    def get_diagnostic(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single session record by its record_id or session_id (latest)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM diagnostic_sessions WHERE record_id = ? OR session_id = ? ORDER BY id DESC LIMIT 1;",
                    (identifier, identifier)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to fetch session {identifier}: {e}")
        return None

    def get_diagnostics_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves all diagnostic device records submitted under a given session ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM diagnostic_sessions WHERE session_id = ? ORDER BY id DESC;", (session_id,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to fetch devices for session {session_id}: {e}")
            return []

    def get_all_diagnostics(self, limit: int = 100) -> pd.DataFrame:
        """Retrieves recent diagnostic records as a pandas DataFrame."""
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(
                    f"SELECT * FROM diagnostic_sessions ORDER BY id DESC LIMIT {int(limit)};",
                    conn
                )
                return df
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to query all diagnostics: {e}")
            return pd.DataFrame()

    def get_summary_stats(self) -> Dict[str, Any]:
        """Calculates high-level diagnostic statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM diagnostic_sessions;")
                total = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM diagnostic_sessions WHERE functional_grade LIKE '%PASS%';")
                pass_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM diagnostic_sessions WHERE functional_grade LIKE '%FAIL%';")
                fail_count = cursor.fetchone()[0]

                cursor.execute("SELECT AVG(functional_score_pct), AVG(battery_health) FROM diagnostic_sessions;")
                row = cursor.fetchone()
                avg_score = row[0] or 0.0
                avg_bat = row[1] or 0.0

                return {
                    "total_inspections": total,
                    "passed_count": pass_count,
                    "failed_count": fail_count,
                    "avg_score": round(avg_score, 1),
                    "avg_battery_health": round(avg_bat, 1)
                }
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to get summary stats: {e}")
            return {
                "total_inspections": 0,
                "passed_count": 0,
                "failed_count": 0,
                "avg_score": 0.0,
                "avg_battery_health": 0.0
            }

    def delete_diagnostic(self, session_id: str) -> bool:
        """Deletes a diagnostic record by session_id."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM diagnostic_sessions WHERE session_id = ?;", (session_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to delete session {session_id}: {e}")
            return False

    def clear_all(self) -> bool:
        """Clears all records from the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM diagnostic_sessions;")
                conn.commit()
            return True
        except Exception as e:
            print(f"[DiagnosticDB Error] Failed to clear all diagnostics: {e}")
            return False
