#!/usr/bin/env python3
"""
DATASET BUILDER & AUTO-LABELING PIPELINE FOR MODEL VERSI 8 (V8)
==============================================================
Pusat Gadai Indonesia (PGI) — Scaled Smartphone Defect Inspection (>50K Corpus)

Workflow:
1. Target Structure Initialization:
   - dataset_v8/images/{train,val}
   - dataset_v8/labels/{train,val}
   - dataset_v8/data_v8.yaml
2. Anchor Integration (Phase 1):
   - Ingests all 4,558 human-verified images & 26,811 annotations from dataset_v7/
3. Scaled Auto-Labeling (Phase 2):
   - Scans 33,946 clean crops from cropped_new_1024/
   - Ensembles Model V7 Best (Epoch 9) + Model Tambahan (YOLO26m)
   - Applies Unit-Aware 85/15 train/val split (Zero Leakage)
   - Grade-aware confidence gating (filters glare in Grade A, elevates hard_damage in Grade D)
   - Checkpointed & Resumable: writes live status to dataset_v8/auto_annotation_live_status.json
"""

import os
import sys
import json
import time
import shutil
import random
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

import torch
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "dataset_v8"
CROPPED_1024_DIR = BASE_DIR / "cropped_new_1024"
DATASET_V7_DIR = BASE_DIR / "dataset_v7"
STATUS_FILE = OUTPUT_DIR / "auto_annotation_live_status.json"

V8_CLASSES = {
    0: "scratch",
    1: "chip",
    2: "dent",
    3: "hard_damage"
}

def setup_v8_directory_structure():
    """Initializes dataset_v8 directory tree and writes data_v8.yaml."""
    for split in ["train", "val"]:
        (OUTPUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    yaml_content = f"""path: {OUTPUT_DIR.resolve()}
train: images/train
val: images/val

names:
  0: scratch
  1: chip
  2: dent
  3: hard_damage
"""
    yaml_path = OUTPUT_DIR / "data_v8.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f" [V8 Setup] Direktori dataset_v8 & konfigurasi {yaml_path.name} siap.")

def ingest_v7_anchor_data() -> Tuple[int, int]:
    """Ingests human-verified dataset_v7 to preserve ground-truth anchor."""
    print("\n" + "=" * 75)
    print(" ⚓ [FASE 1] MENGIMPOR DATASET ANCHOR DARI V7 (HUMAN GROUND TRUTH)")
    print("=" * 75)

    if not DATASET_V7_DIR.exists():
        print(" [Warning] dataset_v7 tidak ditemukan, melewati Fase 1.")
        return 0, 0

    copied_images = 0
    copied_labels = 0

    for split in ["train", "val"]:
        img_src = DATASET_V7_DIR / "images" / split
        lbl_src = DATASET_V7_DIR / "labels" / split

        img_dst = OUTPUT_DIR / "images" / split
        lbl_dst = OUTPUT_DIR / "labels" / split

        if img_src.exists():
            for f in img_src.iterdir():
                if f.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    dst_file = img_dst / f.name
                    if not dst_file.exists():
                        shutil.copy2(f, dst_file)
                        copied_images += 1

        if lbl_src.exists():
            for f in lbl_src.iterdir():
                if f.suffix.lower() == ".txt":
                    dst_file = lbl_dst / f.name
                    if not dst_file.exists():
                        shutil.copy2(f, dst_file)
                        copied_labels += 1

    print(f" • Citra Anchor V7 Disalin : {copied_images:,} citra")
    print(f" • Label Anchor V7 Disalin : {copied_labels:,} label (.txt)")
    return copied_images, copied_labels

def box_iou(box1: List[float], box2: List[float]) -> float:
    """Calculates IoU between two normalized YOLO boxes [xc, yc, w, h]."""
    x1_min, y1_min = box1[0] - box1[2]/2, box1[1] - box1[3]/2
    x1_max, y1_max = box1[0] + box1[2]/2, box1[1] + box1[3]/2

    x2_min, y2_min = box2[0] - box2[2]/2, box2[1] - box2[3]/2
    x2_max, y2_max = box2[0] + box2[2]/2, box2[1] + box2[3]/2

    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)

    if inter_xmax <= inter_xmin or inter_ymax <= inter_ymin:
        return 0.0

    inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)

    union = area1 + area2 - inter_area
    return inter_area / max(1e-6, union)

def ensemble_predictions(
    res_v7,
    res_tambahan,
    grade: str
) -> List[Tuple[int, float, float, float, float]]:
    """
    Combines predictions from Model V7 and Model Tambahan with Grade-Aware Thresholding.
    Returns list of (class_id, x_center, y_center, width, height).
    """
    raw_candidates = []

    # Threshold adjustments based on physical grade
    if grade == "grade_A":
        min_conf = 0.40
    elif grade == "grade_B":
        min_conf = 0.25
    elif grade == "grade_C":
        min_conf = 0.20
    else:  # grade_D
        min_conf = 0.18

    # 1. Process V7 Predictions (0: scratch, 1: chip, 2: dent, 3: hard_damage)
    if res_v7 and len(res_v7.boxes) > 0:
        boxes = res_v7.boxes.xywhn.cpu().tolist()
        clss = res_v7.boxes.cls.cpu().tolist()
        confs = res_v7.boxes.conf.cpu().tolist()
        for b, c, conf in zip(boxes, clss, confs):
            cid = int(c)
            # Filter glare on grade A
            if grade == "grade_A" and cid == 0 and conf < 0.50:
                continue
            if conf >= min_conf:
                raw_candidates.append({
                    "cid": cid,
                    "bbox": b,
                    "conf": conf,
                    "source": "v7"
                })

    # 2. Process Model Tambahan Predictions (0: Scratch -> 0, 1: Chip -> 1, 2: Hard Damage -> 3)
    map_tambahan = {0: 0, 1: 1, 2: 3}
    if res_tambahan and len(res_tambahan.boxes) > 0:
        boxes = res_tambahan.boxes.xywhn.cpu().tolist()
        clss = res_tambahan.boxes.cls.cpu().tolist()
        confs = res_tambahan.boxes.conf.cpu().tolist()
        for b, c, conf in zip(boxes, clss, confs):
            cid = map_tambahan.get(int(c), -1)
            if cid == -1: continue
            if grade == "grade_A" and cid == 0 and conf < 0.50:
                continue
            # For grade D, elevate Hard Damage detections
            req_conf = min_conf * 0.9 if (grade == "grade_D" and cid == 3) else min_conf
            if conf >= req_conf:
                raw_candidates.append({
                    "cid": cid,
                    "bbox": b,
                    "conf": conf,
                    "source": "tambahan"
                })

    # 3. Non-Maximum Suppression / Deduplication
    raw_candidates.sort(key=lambda x: x["conf"], reverse=True)
    kept = []
    for cand in raw_candidates:
        overlap = False
        for k in kept:
            if box_iou(cand["bbox"], k["bbox"]) > 0.50:
                overlap = True
                break
        if not overlap:
            kept.append(cand)

    # Format to (cid, xc, yc, w, h)
    return [(k["cid"], k["bbox"][0], k["bbox"][1], k["bbox"][2], k["bbox"][3]) for k in kept]

def run_auto_annotation(
    batch_size: int = 16,
    limit_units: int = None,
    device: str = "mps"
):
    setup_v8_directory_structure()
    ingest_v7_anchor_data()

    print("\n" + "=" * 75)
    print(" 🤖 [FASE 2] RUNNING TEACHER-STUDENT AUTO-LABELER PADA CROPPED_NEW_1024")
    print("=" * 75)

    v7_weights = BASE_DIR / "weights_v7" / "phone_defect_model_v7_best.pt"
    if not v7_weights.exists():
        v7_weights = BASE_DIR / "runs" / "detect" / "runs_v7_training" / "defect_v7_model" / "weights" / "best.pt"

    tambahan_weights = BASE_DIR / "model_tambahan.pt"

    if not v7_weights.exists():
        print(f"[ERROR] Bobot V7 tidak ditemukan di {v7_weights}")
        return

    print(f" • Teacher 1 (V7 Best)    : {v7_weights.name}")
    print(f" • Teacher 2 (Tambahan)   : {tambahan_weights.name if tambahan_weights.exists() else 'N/A'}")
    print(f" • Device Akselerasi      : {device.upper()}")

    teacher_v7 = YOLO(str(v7_weights))
    teacher_tambahan = YOLO(str(tambahan_weights)) if tambahan_weights.exists() else None

    # Gather units across grades
    unit_records = []
    for grade_dir in sorted(CROPPED_1024_DIR.iterdir()):
        if grade_dir.is_dir() and grade_dir.name.startswith("grade_"):
            for u_dir in sorted(grade_dir.iterdir()):
                if u_dir.is_dir():
                    images = list(u_dir.glob("*.jpg")) + list(u_dir.glob("*.png"))
                    if images:
                        unit_records.append({
                            "unit_id": u_dir.name,
                            "grade": grade_dir.name,
                            "dir": u_dir,
                            "images": images
                        })

    print(f" • Total Unit HP Ditemukan : {len(unit_records):,} unit")

    # Unit-Aware Train/Val Split (85% Train / 15% Val, Seeded for determinism)
    random.seed(42)
    random.shuffle(unit_records)

    if limit_units and limit_units > 0:
        unit_records = unit_records[:limit_units]
        print(f" • Mode Testing / Limit    : {limit_units:,} unit diproses")

    val_split_idx = int(len(unit_records) * 0.15)
    val_units = set(u["unit_id"] for u in unit_records[:val_split_idx])

    total_images_processed = 0
    total_boxes_generated = 0
    box_counter = {0: 0, 1: 0, 2: 0, 3: 0}
    t_start = time.time()

    # Process in unit batches
    for idx, u in enumerate(unit_records):
        unit_id = u["unit_id"]
        grade = u["grade"]
        split = "val" if unit_id in val_units else "train"

        img_dst_dir = OUTPUT_DIR / "images" / split
        lbl_dst_dir = OUTPUT_DIR / "labels" / split

        # Collect images needing inference in this unit
        imgs_to_process = []
        for img_path in u["images"]:
            target_img_name = f"{grade}_{unit_id}_{img_path.name}"
            target_img_path = img_dst_dir / target_img_name
            target_lbl_path = lbl_dst_dir / f"{Path(target_img_name).stem}.txt"

            if target_lbl_path.exists() and target_img_path.exists():
                total_images_processed += 1
            else:
                imgs_to_process.append((img_path, target_img_path, target_lbl_path))

        # Run Batched Teacher Inference if there are pending images
        if imgs_to_process:
            batch_paths = [str(x[0]) for x in imgs_to_process]
            try:
                batch_res_v7 = teacher_v7.predict(batch_paths, imgsz=800, conf=0.15, device=device, verbose=False)
            except Exception:
                batch_res_v7 = [None] * len(imgs_to_process)

            if teacher_tambahan:
                try:
                    batch_res_tambahan = teacher_tambahan.predict(batch_paths, imgsz=800, conf=0.15, device=device, verbose=False)
                except Exception:
                    batch_res_tambahan = [None] * len(imgs_to_process)
            else:
                batch_res_tambahan = [None] * len(imgs_to_process)

            # Process and write annotations
            for (img_path, target_img_path, target_lbl_path), res_v7, res_tambahan in zip(imgs_to_process, batch_res_v7, batch_res_tambahan):
                pseudo_boxes = ensemble_predictions(res_v7, res_tambahan, grade)

                # Copy Image
                if not target_img_path.exists():
                    shutil.copy2(img_path, target_img_path)

                # Write Label File (even if empty, for background learning)
                with open(target_lbl_path, "w", encoding="utf-8") as f_lbl:
                    for cid, xc, yc, w, h in pseudo_boxes:
                        f_lbl.write(f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
                        box_counter[cid] += 1
                        total_boxes_generated += 1

                total_images_processed += 1

        # Periodic logging and live status update
        if (idx + 1) % 25 == 0 or (idx + 1) == len(unit_records):
            elapsed = time.time() - t_start
            units_per_sec = (idx + 1) / max(1.0, elapsed)
            remaining_sec = (len(unit_records) - (idx + 1)) / max(0.01, units_per_sec)
            pct = ((idx + 1) / len(unit_records)) * 100

            live_stat = {
                "status": "RUNNING" if (idx + 1) < len(unit_records) else "COMPLETED",
                "processed_units": idx + 1,
                "total_units": len(unit_records),
                "progress_percent": round(pct, 1),
                "processed_images": total_images_processed,
                "total_boxes_generated": total_boxes_generated,
                "box_distribution": {V8_CLASSES[k]: v for k, v in box_counter.items()},
                "speed_units_per_sec": round(units_per_sec, 2),
                "eta_minutes": round(remaining_sec / 60, 1),
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                with open(STATUS_FILE, "w", encoding="utf-8") as f_stat:
                    json.dump(live_stat, f_stat, indent=2)
            except Exception:
                pass

            print(f" [{pct:5.1f}%] Unit: {idx+1:,}/{len(unit_records):,} | Citra: {total_images_processed:,} | Kotak: {total_boxes_generated:,} | Speed: {units_per_sec:.2f} u/s | ETA: {remaining_sec/60:.1f} m")

    print("\n" + "=" * 75)
    print(" 🏆 AUTO-LABELING UNTUK DATASET V8 SELESAI!")
    print("=" * 75)
    print(f" • Total Citra Masuk V8   : {total_images_processed:,} citra")
    print(f" • Total Kotak Anotasi    : {total_boxes_generated:,} bboxes")
    for cid, cnt in box_counter.items():
        print(f"    - {V8_CLASSES[cid]:<12}: {cnt:,} boxes")
    print(f" • Lokasi Dataset V8      : {OUTPUT_DIR}")
    print(f" • Status Log             : {STATUS_FILE}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and Auto-Label Dataset V8")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah unit untuk pengujian (default: semua)")
    parser.add_argument("--device", type=str, default="mps" if torch.backends.mps.is_available() else "cpu", help="Device komputasi")

    args = parser.parse_args()
    run_auto_annotation(batch_size=args.batch, limit_units=args.limit, device=args.device)
