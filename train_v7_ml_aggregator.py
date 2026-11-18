#!/usr/bin/env python3
"""
TRAIN ML GRADING AGGREGATOR V7 (24 SPATIAL & DENSITY FEATURES)
=============================================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection

Trains a Cost-Sensitive Multivariate Classifier on 400 balanced ground truth demo units (A, B, C, D).
Solves the Grade C vs Grade B collapse using:
- Scratch spatial density per cm2
- Cross-view penetration ratio (how many sides have damage)
- Dent cluster & severity index
- Hard Damage veto representation
- Balanced class reweighting (RandomForest / GradientBoosting)
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml_grading_aggregator import FEATURE_NAMES_V7, MLGradingAggregator

DEMO_DIR = BASE_DIR / "streamlit_inspection_app" / "demo_samples"
if not DEMO_DIR.exists():
    DEMO_DIR = BASE_DIR / "demo_samples"

WEIGHTS_DIR = BASE_DIR / "streamlit_inspection_app" / "weights"
V7_WEIGHTS_DIR = BASE_DIR / "weights_v7"
CACHE_FILE = BASE_DIR / "reports" / "v7_ml_400_units_defects_cache.json"

GRADES = ["A", "B", "C", "D"]
GRADE_TO_ID = {"A": 0, "B": 1, "C": 2, "D": 3}
ID_TO_GRADE = {0: "A", 1: "B", 2: "C", 3: "D"}

def extract_24_features(unit_defects: List[Dict], total_views_count: int = 5) -> np.ndarray:
    """Computes V7 DPI terms and delegates 24-feature extraction to MLGradingAggregator (DRY)."""
    housing_defects = [d for d in unit_defects if d.get("view_side") != "front"]
    c_counts = {"scratch": 0, "chip": 0, "dent": 0, "hard_damage": 0}
    total_dpi = 0.0
    frame_dpi = 0.0
    bottom_back_dpi = 0.0

    severity_weights = {"scratch": 1.0, "chip": 3.5, "dent": 3.0, "hard_damage": 25.0}
    zone_weights = {"back": 2.0, "bottom": 1.2, "left": 1.0, "right": 1.0, "top": 1.0}

    for d in housing_defects:
        raw_c = d.get("class_name", "scratch").lower()
        c_name = "hard_damage" if raw_c in ["broken", "crack"] else (raw_c if raw_c in c_counts else "scratch")
        c_counts[c_name] += 1
        side = d.get("view_side", "back")
        l_mm = float(d.get("length_mm", 0.0))
        size_f = max(1.0, l_mm / 3.0)
        p = severity_weights.get(c_name, 1.0) * zone_weights.get(side, 1.0) * size_f
        total_dpi += p
        if side in ["left", "right", "top"]:
            frame_dpi += p
        else:
            bottom_back_dpi += p

    return MLGradingAggregator.extract_features_v7(
        defects_detail=unit_defects,
        class_counts=c_counts,
        total_dpi=total_dpi,
        frame_dpi=frame_dpi,
        bottom_back_dpi=bottom_back_dpi,
        total_views_count=total_views_count
    )

def collect_or_load_dataset() -> Tuple[np.ndarray, np.ndarray, List[str]]:
    # Check cache
    if CACHE_FILE.exists():
        print(f"[Dataset] Loading cached detection features from: {CACHE_FILE}")
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
        X = np.array(cache_data["X"], dtype=np.float32)
        y = np.array(cache_data["y"], dtype=np.int64)
        uids = cache_data["uids"]
        print(f"[Dataset] Loaded {len(X)} unit feature vectors from cache.")
        return X, y, uids

    # Run detection on 400 units
    print("[Dataset] Extracting defect features from 400 demo sample units...")
    sys.path.insert(0, str(BASE_DIR))
    from defect_detector import DefectDetector

    # Use V6 best detector or V7 if available
    v7_best = V7_WEIGHTS_DIR / "phone_defect_model_v7_best.pt"
    v6_best = WEIGHTS_DIR / "phone_defect_model_v6_best.pt"
    detector_w = str(v7_best if v7_best.exists() else v6_best)
    print(f"          Using YOLO detector: {detector_w}")

    detector = DefectDetector(weights_path=detector_w, enable_heuristics=False)

    grade_dirs = {"grade_A": "A", "grade_B": "B", "grade_C": "C", "grade_D": "D"}
    valid_sides = ["top", "bottom", "left", "right", "back"]

    X_list = []
    y_list = []
    uids = []

    for g_folder, g_label in grade_dirs.items():
        g_path = DEMO_DIR / g_folder
        if not g_path.exists():
            continue
        unit_dirs = sorted([d for d in g_path.iterdir() if d.is_dir() and not d.name.startswith(".")])
        print(f"          Processing {len(unit_dirs)} units for {g_folder}...")
        for idx, u_dir in enumerate(unit_dirs):
            if (idx + 1) % 20 == 0 or idx == 0 or (idx + 1) == len(unit_dirs):
                print(f"            [{g_folder}] Unit {idx+1}/{len(unit_dirs)}: {u_dir.name}")
            unit_defects = []
            views_found = 0
            for s in valid_sides:
                for ext in [".jpg", ".png", ".jpeg"]:
                    img_p = u_dir / f"{s}{ext}"
                    if img_p.exists():
                        views_found += 1
                        defs = detector.detect_image(str(img_p), view_side=s, filter_hands=True, conf_threshold=0.20)
                        for d in defs:
                            unit_defects.append(d.to_dict())
                        break

            feats = extract_24_features(unit_defects, total_views_count=max(1, views_found))
            X_list.append(feats)
            y_list.append(GRADE_TO_ID[g_label])
            uids.append(u_dir.name)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)

    # Save cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"X": X.tolist(), "y": y.tolist(), "uids": uids}, f)
    print(f"[Dataset] Saved {len(X)} unit records to cache: {CACHE_FILE}")
    return X, y, uids

def train_and_evaluate():
    print("=" * 75)
    print(" 🛠️  TRAINING ML COSMETIC GRADING AGGREGATOR V7 (24 SPATIAL FEATURES)")
    print("=" * 75)

    X, y, uids = collect_or_load_dataset()
    print(f" Total Samples        : {len(X)} units")
    print(f" Feature Vector Shape : {X.shape[1]} features")
    for g in GRADES:
        cnt = np.sum(y == GRADE_TO_ID[g])
        print(f" - Grade {g} count    : {cnt} units")

    # Stratified 5-Fold Cross Validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_accs = []
    cv_adj_accs = []
    y_true_all = []
    y_pred_all = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]

        clf = RandomForestClassifier(
            n_estimators=150,
            max_depth=8,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42 + fold
        )
        clf.fit(X_train, y_train)

        preds = clf.predict(X_val)
        acc = accuracy_score(y_val, preds)
        adj_correct = sum(abs(p - t) <= 1 for p, t in zip(preds, y_val))
        adj_acc = adj_correct / len(y_val)

        cv_accs.append(acc)
        cv_adj_accs.append(adj_acc)
        y_true_all.extend(y_val)
        y_pred_all.extend(preds)

    mean_acc = np.mean(cv_accs) * 100
    mean_adj = np.mean(cv_adj_accs) * 100
    print("\n" + "-" * 75)
    print(f" 5-Fold Stratified CV Exact Accuracy    : {mean_acc:.2f}%")
    print(f" 5-Fold Stratified CV Adjacent Accuracy : {mean_adj:.2f}%")
    print("-" * 75)

    cm = confusion_matrix(y_true_all, y_pred_all)
    print("\nConfusion Matrix (4x4):")
    print("     A    B    C    D")
    for i, g in enumerate(GRADES):
        print(f" {g}: {cm[i][0]:4d} {cm[i][1]:4d} {cm[i][2]:4d} {cm[i][3]:4d}")

    # Recall per grade
    recalls = {}
    for i, g in enumerate(GRADES):
        total_g = sum(cm[i])
        correct_g = cm[i][i]
        rec = (correct_g / total_g * 100) if total_g > 0 else 0.0
        recalls[g] = round(rec, 1)
        print(f" Recall Grade {g} : {rec:.1f}%")

    # Fit final model on 100% of data
    final_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=9,
        min_samples_split=3,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42
    )
    final_model.fit(X, y)

    # Save artifacts
    ROOT_WEIGHTS_DIR = BASE_DIR / "weights"
    ROOT_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    V7_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    dest_root = ROOT_WEIGHTS_DIR / "ml_grading_model_v7.joblib"
    dest_streamlit = WEIGHTS_DIR / "ml_grading_model_v7.joblib"
    dest_v7 = V7_WEIGHTS_DIR / "ml_grading_model_v7.joblib"

    model_payload = {
        "model": final_model,
        "feature_names": FEATURE_NAMES_V7,
        "feature_dim": 24,
        "classes": GRADES,
        "version": "v7",
        "training_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cv_accuracy": round(mean_acc, 2),
        "cv_adj_accuracy": round(mean_adj, 2),
        "per_grade_recall": recalls
    }

    joblib.dump(model_payload, dest_root)
    joblib.dump(model_payload, dest_streamlit)
    joblib.dump(model_payload, dest_v7)
    print(f"\n[Saved] Final ML Model V7 saved to:")
    print(f"  -> {dest_root}")
    print(f"  -> {dest_streamlit}")
    print(f"  -> {dest_v7}")

    # Feature Importance Top 10
    importances = final_model.feature_importances_
    indices = np.argsort(importances)[::-1]
    print("\nTop 10 Most Influential Grading Features:")
    for rank in range(10):
        idx = indices[rank]
        print(f" {rank+1:2d}. {FEATURE_NAMES_V7[idx]:<26} : {importances[idx]*100:.2f}%")

    # Export report
    report_path = BASE_DIR / "reports" / "v7_ml_aggregator_training_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as fp:
        json.dump({
            "model_name": "ML Grading Aggregator V7 (24 Features)",
            "exact_accuracy_cv": round(mean_acc, 2),
            "adjacent_accuracy_cv": round(mean_adj, 2),
            "per_grade_recall": recalls,
            "confusion_matrix": {g: {g2: int(cm[i][j]) for j, g2 in enumerate(GRADES)} for i, g in enumerate(GRADES)},
            "feature_importances": {FEATURE_NAMES_V7[i]: round(float(importances[i]), 4) for i in range(len(FEATURE_NAMES_V7))}
        }, fp, indent=2)
    print(f"[Report] Training report saved to: {report_path}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    train_and_evaluate()
