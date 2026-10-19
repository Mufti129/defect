#!/usr/bin/env python3
"""
MONITOR PROGRESS DATASET V8
===========================
Memantau proses auto-anotasi dan statistik dataset_v8 secara real-time.
"""

import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATUS_FILE = BASE_DIR / "dataset_v8" / "auto_annotation_live_status.json"
YAML_FILE = BASE_DIR / "dataset_v8" / "data_v8.yaml"
IMG_TRAIN = BASE_DIR / "dataset_v8" / "images" / "train"
IMG_VAL = BASE_DIR / "dataset_v8" / "images" / "val"
LBL_TRAIN = BASE_DIR / "dataset_v8" / "labels" / "train"
LBL_VAL = BASE_DIR / "dataset_v8" / "labels" / "val"

def print_status():
    print("=" * 65)
    print(" 📊 MONITOR REAL-TIME: DATASET V8 UNTUK TRAINING MODEL VERSI 8")
    print("=" * 65)

    if not STATUS_FILE.exists():
        print(f" [Info] File status {STATUS_FILE.name} belum tersedia.")
        return

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f" [Error] Gagal membaca status: {e}")
        return

    status = data.get("status", "UNKNOWN")
    proc_u = data.get("processed_units", 0)
    total_u = data.get("total_units", 0)
    pct = data.get("progress_percent", 0.0)
    proc_img = data.get("processed_images", 0)
    total_box = data.get("total_boxes_generated", 0)
    boxes = data.get("box_distribution", {})
    speed = data.get("speed_units_per_sec", 0.0)
    eta = data.get("eta_minutes", 0.0)
    last_up = data.get("last_update", "-")

    train_imgs = len(list(IMG_TRAIN.glob("*.jpg"))) if IMG_TRAIN.exists() else 0
    val_imgs = len(list(IMG_VAL.glob("*.jpg"))) if IMG_VAL.exists() else 0
    train_lbls = len(list(LBL_TRAIN.glob("*.txt"))) if LBL_TRAIN.exists() else 0
    val_lbls = len(list(LBL_VAL.glob("*.txt"))) if LBL_VAL.exists() else 0

    status_icon = "🟢 RUNNING" if status == "RUNNING" else "✅ COMPLETED" if status == "COMPLETED" else "⏸ IDLE/PAUSED"

    print(f" • Status Pipeline      : {status_icon}")
    print(f" • Progress Unit HP     : {pct:.1f}% ({proc_u:,} / {total_u:,} unit)")
    print(f" • Kecepatan            : {speed:.2f} unit/detik")
    print(f" • Estimasi Selesai     : {eta:.1f} menit ({eta/60:.2f} jam)")
    print(f" • Terakhir Diperbarui  : {last_up}")
    print("-" * 65)
    print(" 📂 Total Citra & Label di Disk saat ini:")
    print(f"    - Citra Train       : {train_imgs:,} file")
    print(f"    - Citra Val         : {val_imgs:,} file")
    print(f"    - Total Citra V8    : {train_imgs + val_imgs:,} citra")
    print(f"    - Total File Label  : {train_lbls + val_lbls:,} label (.txt)")
    print("-" * 65)
    print(" 🏷️  Distribusi Bounding Box Baru yang Dihasilkan:")
    for k, v in boxes.items():
        print(f"    - {k:<15}: {v:,} boxes")
    print(f"    - TOTAL DEFECT      : {total_box:,} boxes")
    print("=" * 65)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        try:
            while True:
                print("\033[H\033[J", end="")
                print_status()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nMonitoring dihentikan.")
    else:
        print_status()
