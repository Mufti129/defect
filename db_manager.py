#!/usr/bin/env python3
"""
INSPECTION DATABASE & FIELD DATA BANK MANAGER
==============================================
Manages local SQLite database and persistent image storage for:
1. Historical tracking of all smartphone inspection sessions.
2. Logging of rejected non-phone objects (person, animal, laptop, bottle, etc.).
3. Data bank accumulation for training, fine-tuning, and evaluating Model Versi 6.
4. Exporting datasets (CSV, JSON, SQLite) for engineering and data science teams.
"""

import os
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple
import cv2
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
DATA_DIR = CURRENT_DIR / "data"
DATABASE_PATH = DATA_DIR / "inspection_database.sqlite"
COLLECTED_DIR = DATA_DIR / "collected_data"


class InspectionDBManager:
    """
    Handles SQLite transactions and file storage for inspection records.
    """
    def __init__(self, db_path: Optional[Path] = None, storage_dir: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self.storage_dir = storage_dir or COLLECTED_DIR

        # Ensure directories exist
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.db_path.parent, exist_ok=True)

        self._init_tables()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self):
        """Creates the inspection_records table if it doesn't already exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspection_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                unit_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                model_name TEXT NOT NULL,
                is_valid_phone INTEGER NOT NULL,
                rejection_reason TEXT,
                detected_objects_json TEXT,
                final_grade TEXT,
                grade_confidence REAL,
                total_dpi REAL,
                defects_count INTEGER,
                defect_breakdown_json TEXT,
                elapsed_sec REAL,
                storage_folder TEXT,
                views_count INTEGER,
                views_list TEXT
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON inspection_records (timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_id ON inspection_records (unit_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_final_grade ON inspection_records (final_grade);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_valid ON inspection_records (is_valid_phone);")
            conn.commit()

    def save_record(
        self,
        unit_id: str,
        model_version: str,
        model_name: str,
        is_valid_phone: bool,
        rejection_reason: Optional[str] = None,
        detected_objects: Optional[Dict[str, Any]] = None,
        report: Optional[Dict[str, Any]] = None,
        elapsed_sec: float = 0.0,
        raw_views: Optional[Dict[str, str]] = None,
        cropped_views: Optional[Dict[str, str]] = None,
        annotated_views_bgr: Optional[Dict[str, Any]] = None,
        card_bgr: Optional[Any] = None
    ) -> int:
        """
        Saves a full inspection submission to database and copies images to storage.
        Returns the inserted record ID.
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_folder = datetime.now().strftime("%Y%m%d")
        safe_unit_id = "".join([c if c.isalnum() or c in "-_" else "_" for c in unit_id])

        # Prepare unique storage folder
        target_dir = self.storage_dir / date_folder / f"{safe_unit_id}_{int(datetime.now().timestamp())}"
        os.makedirs(target_dir, exist_ok=True)
        raw_dir = target_dir / "raw"
        crop_dir = target_dir / "cropped"
        ann_dir = target_dir / "annotated"
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(crop_dir, exist_ok=True)
        os.makedirs(ann_dir, exist_ok=True)

        views_saved = []

        # 1. Save raw views
        if raw_views:
            for side, p in raw_views.items():
                if os.path.exists(p):
                    shutil.copy2(p, raw_dir / f"{side}.jpg")
                    views_saved.append(side)

        # 2. Save cropped views (Stage 1)
        if cropped_views:
            for side, p in cropped_views.items():
                if os.path.exists(p):
                    shutil.copy2(p, crop_dir / f"{side}.jpg")

        # 3. Save annotated views
        if annotated_views_bgr:
            for side, img in annotated_views_bgr.items():
                if img is not None:
                    cv2.imwrite(str(ann_dir / f"{side}.jpg"), img)

        # 4. Save composite collage card
        if card_bgr is not None:
            cv2.imwrite(str(target_dir / "composite_card.jpg"), card_bgr)

        # Extract metrics
        final_grade = None
        confidence = 0.0
        total_dpi = 0.0
        defects_count = 0
        defect_breakdown = {}

        if report:
            final_grade = report.get("final_grade")
            confidence = float(report.get("grade_confidence", 0.0))
            total_dpi = float(report.get("total_dpi", 0.0))
            defects_count = int(report.get("total_defects_count", 0))
            defect_breakdown = report.get("defect_breakdown", {})

        det_obj_json = json.dumps(detected_objects or {}, ensure_ascii=False)
        breakdown_json = json.dumps(defect_breakdown, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO inspection_records (
                timestamp, unit_id, model_version, model_name,
                is_valid_phone, rejection_reason, detected_objects_json,
                final_grade, grade_confidence, total_dpi, defects_count,
                defect_breakdown_json, elapsed_sec, storage_folder,
                views_count, views_list
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                timestamp_str,
                unit_id,
                model_version,
                model_name,
                1 if is_valid_phone else 0,
                rejection_reason,
                det_obj_json,
                final_grade,
                confidence,
                total_dpi,
                defects_count,
                breakdown_json,
                round(elapsed_sec, 3),
                str(target_dir),
                len(views_saved),
                ", ".join(views_saved)
            ))
            record_id = cursor.lastrowid
            conn.commit()

        # Save metadata report JSON inside the folder
        with open(target_dir / "inspection_metadata.json", "w", encoding="utf-8") as f:
            meta = {
                "record_id": record_id,
                "timestamp": timestamp_str,
                "unit_id": unit_id,
                "model_version": model_version,
                "model_name": model_name,
                "is_valid_phone": is_valid_phone,
                "rejection_reason": rejection_reason,
                "final_grade": final_grade,
                "grade_confidence": confidence,
                "total_dpi": total_dpi,
                "defects_count": defects_count,
                "defect_breakdown": defect_breakdown,
                "elapsed_sec": elapsed_sec
            }
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return record_id

    def get_recent_records(
        self,
        limit: int = 100,
        filter_status: Optional[str] = None,
        filter_grade: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent inspection records for UI dashboard.
        """
        query = "SELECT * FROM inspection_records WHERE 1=1"
        params = []

        if filter_status == "valid":
            query += " AND is_valid_phone = 1"
        elif filter_status == "rejected":
            query += " AND is_valid_phone = 0"

        if filter_grade and filter_grade != "Semua":
            query += " AND final_grade = ?"
            params.append(filter_grade)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Calculates aggregate metrics for the data bank dashboard.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM inspection_records")
            total_records = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM inspection_records WHERE is_valid_phone = 1")
            valid_phones = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM inspection_records WHERE is_valid_phone = 0")
            rejected_records = cursor.fetchone()[0]

            grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            cursor.execute("""
                SELECT final_grade, COUNT(*) 
                FROM inspection_records 
                WHERE is_valid_phone = 1 AND final_grade IS NOT NULL 
                GROUP BY final_grade
            """)
            for g, count in cursor.fetchall():
                if g in grade_counts:
                    grade_counts[g] = count

            return {
                "total_records": total_records,
                "valid_phones": valid_phones,
                "rejected_records": rejected_records,
                "grade_counts": grade_counts
            }

    def export_to_csv_string(self) -> str:
        """
        Exports the entire database records table to a CSV string.
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM inspection_records ORDER BY id DESC", conn)
            return df.to_csv(index=False)
