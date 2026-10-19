#!/usr/bin/env python3
"""
Corpus Inventory & Scaled Dataset Analyzer (>50,000 Images)
===========================================================
Pusat Gadai Indonesia (PGI) — AI Defect Inspection System

Indexes and analyzes all phone image collections across:
1. cropped_new_1024/ (33,946 cropped 1024px images from 6,813 units)
2. Hasil_Crop_Raw/ & raw_images/ (19,000+ images)
3. dataset_v7/ & dataset_v5_full/ (Annotated sets)
4. ~/Downloads/semua_crop.zip (Ongoing / completed downloads)
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOWNLOADS_DIR = Path.home() / "Downloads"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def scan_folder(folder_path: Path, name: str) -> Dict[str, Any]:
    if not folder_path.exists():
        return {"name": name, "exists": False, "total_images": 0, "units": 0, "size_mb": 0.0}

    total_images = 0
    total_bytes = 0
    units = set()
    grades = {"grade_A": 0, "grade_B": 0, "grade_C": 0, "grade_D": 0, "unassigned": 0}

    for root, dirs, files in os.walk(folder_path):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in IMAGE_EXTENSIONS:
                total_images += 1
                try:
                    total_bytes += p.stat().st_size
                except Exception:
                    pass

                # Extract unit ID & grade from directory structure
                parts = p.parts
                grade_found = False
                for part in parts:
                    for g in ["grade_A", "grade_B", "grade_C", "grade_D"]:
                        if g in part.lower():
                            grades[g] += 1
                            grade_found = True
                            break
                    if grade_found:
                        break
                if not grade_found:
                    grades["unassigned"] += 1

                # Unit tracking
                parent_name = p.parent.name
                if "__" in parent_name or len(parent_name) > 10:
                    units.add(parent_name)

    return {
        "name": name,
        "path": str(folder_path),
        "exists": True,
        "total_images": total_images,
        "estimated_units": len(units) if units else total_images // 5,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "grades": grades
    }

def check_download_status() -> Dict[str, Any]:
    candidates = list(DOWNLOADS_DIR.glob("semua_crop.zip*"))
    if not candidates:
        return {"status": "NOT_FOUND", "size_mb": 0.0}

    target = candidates[0]
    is_in_progress = target.name.endswith(".crdownload") or target.name.endswith(".part")
    size_mb = round(target.stat().st_size / (1024 * 1024), 2)

    return {
        "filename": target.name,
        "status": "IN_PROGRESS" if is_in_progress else "DOWNLOAD_COMPLETE",
        "size_mb": size_mb,
        "is_ready": not is_in_progress,
        "path": str(target)
    }

def run_inventory_audit() -> Dict[str, Any]:
    print("=" * 75)
    print(" 📦 INVENTARISASI KORPUS DATASET BESAR (>50.000 GAMBAR) PGI")
    print("=" * 75 + "\n")

    targets = [
        ("Cropped 1024px Collection", BASE_DIR / "cropped_new_1024"),
        ("Hasil Crop Raw Repository", BASE_DIR / "Hasil_Crop_Raw"),
        ("Raw Images Store", BASE_DIR / "raw_images"),
        ("Model V7 Training Dataset", BASE_DIR / "dataset_v7" / "images"),
        ("V5 Full Corpus", BASE_DIR / "dataset_v5_full" / "images"),
        ("Submodule Demo Samples", BASE_DIR / "streamlit_inspection_app" / "demo_samples"),
    ]

    results = []
    total_images_all = 0
    total_mb_all = 0.0

    for name, p in targets:
        info = scan_folder(p, name)
        results.append(info)
        total_images_all += info["total_images"]
        total_mb_all += info["size_mb"]
        status_str = f"{info['total_images']:,} citra ({info['size_mb']:.1f} MB)" if info['exists'] else "Tidak ditemukan"
        print(f" • {name:<28}: {status_str}")

    download_info = check_download_status()
    print("\n" + "-" * 75)
    print(f" 📥 Status Unduhan Tambahan (semua_crop.zip):")
    print(f"   • File   : {download_info.get('filename', 'Belum ada')}")
    print(f"   • Ukuran : {download_info.get('size_mb', 0.0):,.1f} MB")
    print(f"   • Status : {download_info.get('status', 'N/A')}")
    print("-" * 75 + "\n")

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_indexed_images": total_images_all,
        "total_storage_mb": round(total_mb_all, 2),
        "target_threshold": 50000,
        "is_50k_exceeded": total_images_all >= 50000,
        "download_status": download_info,
        "repositories": results
    }

    report_path = BASE_DIR / "reports" / "large_scale_corpus_inventory.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f" 🎯 TOTAL CITRA TERINDEX LOKAL : {total_images_all:,} GAMBAR ({total_mb_all/1024:.2f} GB)")
    print(f" 🚀 Target Skala 50K Terpenuhi  : {'YA (100% Siap Model V8)' if total_images_all >= 50000 else 'Menunggu Unduhan'}")
    print(f" 📄 Laporan Disimpan            : {report_path}")
    print("=" * 75 + "\n")

    return summary

if __name__ == "__main__":
    run_inventory_audit()
