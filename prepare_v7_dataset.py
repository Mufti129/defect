#!/usr/bin/env python3
"""
DATA ENGINE BUILDER FOR MODEL VERSI 7 (V7)
==========================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection

Constructs unified 'dataset_v7/' featuring:
1. Unified 4-Class Architecture:
   - 0: scratch      (Fine & coarse surface abrasions)
   - 1: chip         (Frame corner paint chipping & edge peeling)
   - 2: dent         (Body denting/bending without glass breach - Critical for Grade C)
   - 3: hard_damage  (Structural fractures, glass cracks & massive damage - Veto Grade D)
2. Direct Label Merging:
   - Broken + Crack annotations from human ground truth -> hard_damage (3)
   - Dent annotations preserved explicitly -> dent (2)
   - Chip -> chip (1)
   - Scratch -> scratch (0)
3. Hard Damage Enrichment:
   - Utilizes 'model_tambahan.pt' (YOLO26m) high-confidence predictions on Grade D housing
     to inject real hard_damage defect instances into training data.
4. Unit-Aware Leakage Prevention:
   - Splits 85% Train and 15% Validation strictly grouped by physical phone unit ID.
   - Preserves benchmark samples independently.
"""

import os, sys, json, shutil, random, hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set

BASE_DIR = Path('/Users/macbookair/Documents/Project Defect Detections/TES_CROP_HP')
OUTPUT_DIR = BASE_DIR / 'dataset_v7'
SANITIZED_DIR = BASE_DIR / 'data anotasi box defect hp' / 'anotasi_bersih_terfilter_tangan'
WEIGHTS_DIR = BASE_DIR / 'streamlit_inspection_app' / 'weights'

NDJSON_FILES = [
    "allnewdefect-2_bersih_dan_tervalidasi.ndjson",
    "hp-defect-detiction-anotasi-all_bersih_dan_tervalidasi.ndjson",
    "newcny_bersih_dan_tervalidasi.ndjson",
    "newdny_bersih_dan_tervalidasi.ndjson",
    "annotated_grade_d_bersih_dan_tervalidasi.ndjson",
    "sampled_grade_abc_bersih_dan_tervalidasi.ndjson"
]

# Target YOLO Class mapping for V7:
# 0: scratch, 1: chip, 2: dent, 3: hard_damage
# NDJSON raw IDs: 0: Broken, 1: Scratch, 2: Dent, 3: Chip, 4: Crack
MAP_NDJSON_TO_V7 = {
    0: 3,  # NDJSON Broken (0) -> V7 hard_damage (3)
    1: 0,  # NDJSON Scratch (1) -> V7 scratch (0)
    2: 2,  # NDJSON Dent (2)    -> V7 dent (2)
    3: 1,  # NDJSON Chip (3)    -> V7 chip (1)
    4: 3   # NDJSON Crack (4)   -> V7 hard_damage (3)
}

V7_CLASS_NAMES = {
    0: "scratch",
    1: "chip",
    2: "dent",
    3: "hard_damage"
}

IMAGE_SEARCH_DIRS = [
    BASE_DIR / "dataset_v6" / "images" / "train",
    BASE_DIR / "dataset_v6" / "images" / "val",
    BASE_DIR / "dataset_v5_full" / "images" / "train",
    BASE_DIR / "dataset_v5_full" / "images" / "val",
    BASE_DIR / "dataset_v4_real" / "images" / "train",
    BASE_DIR / "dataset_v4_real" / "images" / "val",
    BASE_DIR / "Hasil_Crop_Raw"
]

def index_images() -> Dict[str, Path]:
    print("[1/5] Mengindeks seluruh repositori citra crop bodi HP...")
    img_map = {}
    for d in IMAGE_SEARCH_DIRS:
        if d.exists():
            for root, _, files in os.walk(d):
                if "raw_images" in root or "__MACOSX" in root:
                    continue
                for f in files:
                    fl = f.lower()
                    if fl.endswith(('.jpg', '.jpeg', '.png')):
                        if f not in img_map:
                            img_map[f] = Path(root) / f
    print(f"      Ditemukan {len(img_map):,} citra crop unik terverifikasi.")
    return img_map

def extract_unit_id(fn: str) -> str:
    clean = fn.replace("left_", "").replace("right_", "").replace("top_", "").replace("bottom_", "").replace("front_", "").replace("back_", "")
    parts = clean.split("__")
    if len(parts) >= 2:
        return parts[0]
    return hashlib.md5(clean.encode()).hexdigest()[:12]

def build_v7_dataset():
    print("=" * 75)
    print(" 🛠️  MEMBANGUN DATASET V7 (UNIFIED 4-CLASS & HARD DAMAGE ENRICHMENT)")
    print("=" * 75)

    img_map = index_images()

    train_img_dir = OUTPUT_DIR / "images" / "train"
    val_img_dir = OUTPUT_DIR / "images" / "val"
    train_lbl_dir = OUTPUT_DIR / "labels" / "train"
    val_lbl_dir = OUTPUT_DIR / "labels" / "val"

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    for p in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        p.mkdir(parents=True, exist_ok=True)

    print("\n[2/5] Membaca anotasi bersih, remapping kelas V7, dan grouping per-unit HP...")
    records_by_unit = {}
    total_raw_boxes = 0

    for nd_name in NDJSON_FILES:
        nd_path = SANITIZED_DIR / nd_name
        if not nd_path.exists():
            continue
        with open(nd_path, "r", encoding="utf-8") as f:
            f.readline()  # skip header
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("type") != "image":
                    continue
                fn = item.get("file")
                boxes = item.get("annotations", {}).get("boxes", [])
                if not fn or not boxes:
                    continue
                if fn in ["top.jpg", "right.jpg", "left.jpg", "bottom.jpg", "front.jpg", "back.jpg"]:
                    continue
                if fn not in img_map:
                    continue

                u_id = extract_unit_id(fn)
                if u_id not in records_by_unit:
                    records_by_unit[u_id] = []

                # Remap boxes
                remapped_boxes = []
                for b in boxes:
                    raw_cid = b[0]
                    v7_cid = MAP_NDJSON_TO_V7.get(raw_cid, 0)
                    xc, yc, bw, bh = float(b[1]), float(b[2]), float(b[3]), float(b[4])
                    remapped_boxes.append((v7_cid, xc, yc, bw, bh))
                    total_raw_boxes += 1

                records_by_unit[u_id].append({
                    "file": fn,
                    "src_path": img_map[fn],
                    "boxes": remapped_boxes
                })

    all_units = sorted(list(records_by_unit.keys()))
    random.seed(42)
    random.shuffle(all_units)

    n_val = max(1, int(len(all_units) * 0.15))
    val_units = set(all_units[:n_val])
    train_units = set(all_units[n_val:])

    print(f"      Total Unit Ponsel Unik : {len(all_units):,}")
    print(f"      Unit Training          : {len(train_units):,} unit (85%)")
    print(f"      Unit Validasi          : {len(val_units):,} unit (15%)")

    print("\n[3/5] Mentransfer & menuliskan data gambar serta label format YOLO V7...")
    stats = {
        "train_images": 0,
        "val_images": 0,
        "train_boxes": 0,
        "val_boxes": 0,
        "class_counts": {c: 0 for c in V7_CLASS_NAMES.values()}
    }

    seen_files = set()

    for u_id, items in records_by_unit.items():
        is_val = (u_id in val_units)
        t_img_dir = val_img_dir if is_val else train_img_dir
        t_lbl_dir = val_lbl_dir if is_val else train_lbl_dir

        for it in items:
            fn = it["file"]
            if fn in seen_files:
                continue
            seen_files.add(fn)

            src_p = it["src_path"]
            dst_p = t_img_dir / fn
            if not dst_p.exists():
                shutil.copy2(src_p, dst_p)

            stem = Path(fn).stem
            lbl_p = t_lbl_dir / f"{stem}.txt"

            lines = []
            for b in it["boxes"]:
                cid, xc, yc, bw, bh = b
                cname = V7_CLASS_NAMES[cid]
                stats["class_counts"][cname] += 1
                lines.append(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

            with open(lbl_p, "w") as fp:
                fp.write("\n".join(lines) + "\n")

            if is_val:
                stats["val_images"] += 1
                stats["val_boxes"] += len(lines)
            else:
                stats["train_images"] += 1
                stats["train_boxes"] += len(lines)

                # Minority class oversampling for Train set only (hard_damage x5, dent x2)
                has_hard_damage = any(l.startswith("3 ") for l in lines)
                has_dent = any(l.startswith("2 ") for l in lines)
                os_copies = 5 if has_hard_damage else (2 if has_dent else 0)

                for os_idx in range(os_copies):
                    os_fn = f"{stem}_os{os_idx+1}.jpg"
                    os_dst_img = train_img_dir / os_fn
                    os_lbl_p = train_lbl_dir / f"{stem}_os{os_idx+1}.txt"
                    if not os_dst_img.exists():
                        shutil.copy2(src_p, os_dst_img)
                    with open(os_lbl_p, "w") as fp_os:
                        fp_os.write("\n".join(lines) + "\n")
                    stats["train_images"] += 1
                    stats["train_boxes"] += len(lines)

    # 4. Enrich Hard Damage from model_tambahan on Grade D images
    print("\n[4/5] Menginjeksi pengayaan Hard Damage via Teacher Model (model_tambahan.pt)...")
    m_add_path = WEIGHTS_DIR / 'model_tambahan.pt'
    enriched_count = 0
    if m_add_path.exists():
        from ultralytics import YOLO
        teacher_model = YOLO(str(m_add_path))
        crop_d_path = BASE_DIR / 'Hasil_Crop_Raw' / 'grade_D'
        if crop_d_path.exists():
            grade_d_units = sorted([d.name for d in crop_d_path.iterdir() if d.is_dir() and not d.name.startswith('.')])
            # Select 80 units from index 50 onwards (strictly outside demo_samples)
            enrich_units = grade_d_units[50:130]
            for u in enrich_units:
                u_p = crop_d_path / u
                for img_file in u_p.glob('*.jpg'):
                    if 'front' in img_file.name:  # Focus on housing sides
                        continue
                    res = teacher_model.predict(str(img_file), conf=0.35, verbose=False)[0]
                    hd_boxes = []
                    for box in res.boxes:
                        cname = teacher_model.names[int(box.cls[0])]
                        if cname == 'Hard Damage':
                            b_xywhn = box.xywhn[0].cpu().numpy()
                            hd_boxes.append((3, b_xywhn[0], b_xywhn[1], b_xywhn[2], b_xywhn[3]))

                    if hd_boxes:
                        enrich_fn = f"enrich_hd_{u}_{img_file.name}"
                        enrich_dst_img = train_img_dir / enrich_fn
                        enrich_lbl_p = train_lbl_dir / f"{enrich_dst_img.stem}.txt"
                        shutil.copy2(img_file, enrich_dst_img)
                        enrich_lines = [f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}" for b in hd_boxes]
                        with open(enrich_lbl_p, "w") as fp_en:
                            fp_en.write("\n".join(enrich_lines) + "\n")
                        stats["train_images"] += 1
                        stats["train_boxes"] += len(hd_boxes)
                        stats["class_counts"]["hard_damage"] += len(hd_boxes)
                        enriched_count += len(hd_boxes)
    print(f"      Berhasil menginjeksi {enriched_count} anotasi Hard Damage tambahan ke Training Set!")

    print("\n[5/5] Membuat berkas konfigurasi 'data_v7.yaml'...")
    yaml_path = OUTPUT_DIR / "data_v7.yaml"
    yaml_content = f"""path: {OUTPUT_DIR}
train: images/train
val: images/val

names:
  0: scratch
  1: chip
  2: dent
  3: hard_damage
"""
    with open(yaml_path, "w") as fp_y:
        fp_y.write(yaml_content)

    rep_path = OUTPUT_DIR / "dataset_v7_report.json"
    with open(rep_path, "w") as fp_r:
        json.dump({
            "dataset_name": "dataset_v7",
            "yaml_file": str(yaml_path),
            "total_images": stats["train_images"] + stats["val_images"],
            "train_images": stats["train_images"],
            "val_images": stats["val_images"],
            "total_boxes": stats["train_boxes"] + stats["val_boxes"],
            "train_boxes": stats["train_boxes"],
            "val_boxes": stats["val_boxes"],
            "class_distribution": stats["class_counts"],
            "classes": V7_CLASS_NAMES
        }, fp_r, indent=2)

    print("\n" + "=" * 75)
    print(" ✅ DATASET V7 BERHASIL DIBENTUK DENGAN SUKSES!")
    print("=" * 75)
    print(f" • Lokasi Folder    : {OUTPUT_DIR}")
    print(f" • File YAML        : {yaml_path}")
    print(f" • Total Gambar     : {stats['train_images'] + stats['val_images']:,} ({stats['train_images']:,} Train, {stats['val_images']:,} Val)")
    print(f" • Total Cacat Box  : {stats['train_boxes'] + stats['val_boxes']:,} ({stats['train_boxes']:,} Train, {stats['val_boxes']:,} Val)")
    print(f" • Distribusi Kelas : {stats['class_counts']}")
    print("=" * 75 + "\n")

if __name__ == '__main__':
    build_v7_dataset()
