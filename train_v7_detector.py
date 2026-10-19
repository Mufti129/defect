#!/usr/bin/env python3
"""
TRAINING PIPELINE FOR MODEL VERSI 7 (V7 - UNIFIED HARD DAMAGE & SPATIAL DENSITY DETECTOR)
========================================================================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection

Trained on dataset_v7/ (26,811 defect boxes across 4,558 multi-view images).
Features:
- Unified 4-Class Architecture:
    0: scratch
    1: chip
    2: dent
    3: hard_damage
- Transfer Learning & Warm Start:
    Initializes from phone_defect_model_v6_best.pt (inherits edge/texture representations and hand-filter knowledge).
- Hardware Acceleration:
    Automatically uses Apple Silicon Metal (MPS), NVIDIA CUDA, or Multi-Core CPU.
- macOS Anti-Sleep:
    Uses caffeinate to prevent sleep during training.
- Live Status Tracking:
    Logs real-time metrics to weights_v7/training_live_status.json.
- Hyperparameters:
    Resolution: 800x800px, AdamW with Cosine LR, cls gain 1.5, close_mosaic=10.
- Automatic Deployment:
    Saves clean weights to weights_v7/ and streamlit_inspection_app/weights/.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
import torch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_DIR = os.path.join(BASE_DIR, "weights_v7")
STREAMLIT_WEIGHTS_DIR = os.path.join(BASE_DIR, "streamlit_inspection_app", "weights")

def detect_optimal_device() -> str:
    if torch.backends.mps.is_available():
        print(" [Hardware] Apple Silicon Metal (MPS) terdeteksi & aktif.")
        return "mps"
    elif torch.cuda.is_available():
        print(f" [Hardware] NVIDIA CUDA GPU ({torch.cuda.get_device_name(0)}) terdeteksi.")
        return "cuda"
    else:
        print(" [Hardware] Tidak ada GPU dedicated, menggunakan CPU multi-threading.")
        return "cpu"

def enable_anti_sleep():
    if sys.platform == "darwin":
        try:
            res = subprocess.run(["pgrep", "caffeinate"], stdout=subprocess.PIPE, text=True)
            if not res.stdout.strip():
                subprocess.Popen(["caffeinate", "-dms", "-w", str(os.getpid())])
                print(" [System] macOS caffeinate anti-sleep aktif otomatis.")
        except Exception as e:
            print(f" [System] Warning anti-sleep: {e}")

def train_model_v7(
    data_yaml: str = None,
    base_model: str = None,
    epochs: int = 40,
    imgsz: int = 800,
    batch_size: int = 4,
    device: str = None,
    project: str = "runs_v7_training",
    name: str = "defect_v7_model",
    auto_prepare: bool = False,
    resume: bool = False
):
    enable_anti_sleep()

    if device is None:
        device = detect_optimal_device()

    if data_yaml is None:
        data_yaml = os.path.join(BASE_DIR, "dataset_v7", "data_v7.yaml")

    if auto_prepare or not os.path.exists(data_yaml):
        print("\n[Data Engine] Membangun dataset V7 terlebih dahulu...")
        from prepare_v7_dataset import build_v7_dataset
        build_v7_dataset()

    os.makedirs(STATUS_DIR, exist_ok=True)
    os.makedirs(STREAMLIT_WEIGHTS_DIR, exist_ok=True)

    if base_model is None:
        v6_best = os.path.join(STREAMLIT_WEIGHTS_DIR, "phone_defect_model_v6_best.pt")
        if os.path.exists(v6_best):
            base_model = v6_best
            print(f" [Transfer Learning] Menggunakan bobot terbaik V6 sebagai warm start: {base_model}")
        else:
            base_model = "yolov8s.pt"
            print(f" [Transfer Learning] Bobot V6 tidak ditemukan, fallback ke: {base_model}")

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] Paket ultralytics diperlukan. Pasang via: pip install ultralytics")
        sys.exit(1)

    print("\n" + "=" * 75)
    print(" 🚀 MEMULAI PELATIHAN MODEL VERSI 7 (V7 - UNIFIED DEFECT & HARD DAMAGE)")
    print("=" * 75)
    print(f" • Arsitektur Base    : {base_model}")
    print(f" • Dataset Config     : {data_yaml}")
    print(f" • Target Epochs      : {epochs}")
    print(f" • Input Resolution   : {imgsz} x {imgsz} px")
    print(f" • Batch Size         : {batch_size}")
    print(f" • Device Akselerasi  : {device.upper()}")
    print(f" • Run Directory      : {project}/{name}")
    print("=" * 75 + "\n")

    if resume:
        candidates = [
            os.path.join("runs", "detect", project, name, "weights", "last.pt"),
            os.path.join(project, name, "weights", "last.pt"),
            os.path.join(STATUS_DIR, "phone_defect_model_v7_last.pt")
        ]
        ckpt = None
        for c in candidates:
            if os.path.exists(c):
                ckpt = c
                break
        if not ckpt:
            print("[ERROR] Checkpoint last.pt tidak ditemukan untuk resume.")
            sys.exit(1)
        print(f" [RESUME] Melanjutkan pelatihan dari checkpoint: {ckpt}")
        model = YOLO(ckpt)
    else:
        model = YOLO(base_model)
    status_file = os.path.join(STATUS_DIR, "training_live_status.json")

    batch_counter = {"current": 0, "last_epoch": -1}

    def on_train_batch_end(trainer):
        ep = getattr(trainer, "epoch", 0) + 1
        total_ep = getattr(trainer, "epochs", epochs)

        if batch_counter["last_epoch"] != ep:
            batch_counter["current"] = 0
            batch_counter["last_epoch"] = ep

        batch_counter["current"] += 1
        batch_i = batch_counter["current"]
        nb = len(trainer.train_loader) if hasattr(trainer, "train_loader") else 1000

        if batch_i % 25 == 0 or batch_i == nb:
            epoch_pct = (batch_i / max(1, nb)) * 100
            overall_pct = ((ep - 1 + (batch_i / max(1, nb))) / max(1, total_ep)) * 100
            try:
                with open(status_file, "w", encoding="utf-8") as f_stat:
                    json.dump({
                        "status": "TRAINING_IN_PROGRESS",
                        "model_version": "V7",
                        "current_epoch": ep,
                        "total_epochs": total_ep,
                        "current_batch": batch_i,
                        "total_batches_per_epoch": nb,
                        "epoch_progress_percent": round(epoch_pct, 1),
                        "overall_progress_percent": round(overall_pct, 2),
                        "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                    }, f_stat, indent=2)
            except Exception:
                pass

    best_metrics = {"best_map50": 0.0, "best_epoch": 0}
    epoch_eval_history = []

    def on_train_epoch_end(trainer):
        ep = getattr(trainer, "epoch", 0) + 1
        total_ep = getattr(trainer, "epochs", epochs)
        print("\n" + "-" * 75)
        print(f" ⏳ [PROGRES V7] SELESAI TRAIN EPOCH {ep} / {total_ep} — Menjalankan Validasi Evaluasi...")
        print("-" * 75)

    def on_fit_epoch_end(trainer):
        ep = getattr(trainer, "epoch", 0) + 1
        total_ep = getattr(trainer, "epochs", epochs)

        metrics_dict = {}
        csv_path = os.path.join(trainer.save_dir, "results.csv")
        if os.path.exists(csv_path):
            try:
                import csv
                with open(csv_path, "r", encoding="utf-8") as f_csv:
                    reader = csv.DictReader(f_csv)
                    rows = list(reader)
                    if rows:
                        last_row = {k.strip(): float(v.strip()) for k, v in rows[-1].items() if v.strip()}
                        metrics_dict = {
                            "precision": round(last_row.get("metrics/precision(B)", 0.0) * 100, 2),
                            "recall": round(last_row.get("metrics/recall(B)", 0.0) * 100, 2),
                            "mAP50": round(last_row.get("metrics/mAP50(B)", 0.0) * 100, 2),
                            "mAP50_95": round(last_row.get("metrics/mAP50-95(B)", 0.0) * 100, 2),
                            "train_box_loss": round(last_row.get("train/box_loss", 0.0), 4),
                            "train_cls_loss": round(last_row.get("train/cls_loss", 0.0), 4),
                            "val_box_loss": round(last_row.get("val/box_loss", 0.0), 4),
                            "val_cls_loss": round(last_row.get("val/cls_loss", 0.0), 4),
                        }
            except Exception:
                pass

        if not metrics_dict and hasattr(trainer, "metrics") and trainer.metrics:
            m = trainer.metrics
            metrics_dict = {
                "precision": round(float(m.get("metrics/precision(B)", 0.0)) * 100, 2),
                "recall": round(float(m.get("metrics/recall(B)", 0.0)) * 100, 2),
                "mAP50": round(float(m.get("metrics/mAP50(B)", 0.0)) * 100, 2),
                "mAP50_95": round(float(m.get("metrics/mAP50-95(B)", 0.0)) * 100, 2),
            }

        cur_map = metrics_dict.get("mAP50", 0.0)
        if cur_map > best_metrics["best_map50"]:
            best_metrics["best_map50"] = cur_map
            best_metrics["best_epoch"] = ep

        epoch_record = {
            "epoch": ep,
            "metrics": metrics_dict,
            "best_mAP50": best_metrics["best_map50"],
            "best_epoch": best_metrics["best_epoch"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        epoch_eval_history.append(epoch_record)

        print("\n" + "=" * 75)
        print(f" 📈 [EVALUASI REAL-TIME V7] HASIL EPOCH {ep} / {total_ep}")
        print("=" * 75)
        print(f"  • mAP@0.5               : {cur_map:.2f}%  (Tertinggi: {best_metrics['best_map50']:.2f}% di Epoch {best_metrics['best_epoch']})")
        print(f"  • mAP@0.5:0.95 (IoU)    : {metrics_dict.get('mAP50_95', 0.0):.2f}%")
        print(f"  • Recall (Sensitivitas) : {metrics_dict.get('recall', 0.0):.2f}%")
        print(f"  • Precision (Ketepatan) : {metrics_dict.get('precision', 0.0):.2f}%")
        print(f"  • Val Box Loss          : {metrics_dict.get('val_box_loss', 0.0)} | Train Box Loss: {metrics_dict.get('train_box_loss', 0.0)}")
        print(f"  • Val Cls Loss          : {metrics_dict.get('val_cls_loss', 0.0)} | Train Cls Loss: {metrics_dict.get('train_cls_loss', 0.0)}")
        print("=" * 75 + "\n")

        try:
            with open(status_file, "w", encoding="utf-8") as f_stat:
                json.dump({
                    "status": "TRAINING_IN_PROGRESS",
                    "model_version": "V7",
                    "current_epoch": ep,
                    "total_epochs": total_ep,
                    "overall_progress_percent": round((ep / max(1, total_ep)) * 100, 2),
                    "latest_evaluation": metrics_dict,
                    "best_metrics": best_metrics,
                    "history": epoch_eval_history,
                    "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f_stat, indent=2)
        except Exception:
            pass

    model.add_callback("on_train_batch_end", on_train_batch_end)
    model.add_callback("on_train_epoch_end", on_train_epoch_end)
    model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

    if resume:
        results = model.train(resume=True)
    else:
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch_size,
            device=device,
            project=project,
            name=name,
            optimizer="AdamW",
            lr0=0.001,
            lrf=0.01,
            cos_lr=True,
            weight_decay=0.0005,
            warmup_epochs=3.0,
            warmup_momentum=0.8,
            degrees=15.0,
            translate=0.08,
            scale=0.35,
            fliplr=0.5,
            flipud=0.0,
            mosaic=1.0,
            copy_paste=0.30,
            cls=1.5,
            close_mosaic=10,
            hsv_h=0.015,
            hsv_s=0.5,
            hsv_v=0.4,
            save=True,
            save_period=5,
            deterministic=False,
            verbose=True
        )

    best_weights_src = os.path.join(project, name, "weights", "best.pt")
    if not os.path.exists(best_weights_src):
        alt_best = os.path.join("runs", "detect", project, name, "weights", "best.pt")
        if os.path.exists(alt_best):
            best_weights_src = alt_best
    if os.path.exists(best_weights_src):
        import shutil
        target_v7 = os.path.join(STATUS_DIR, "phone_defect_model_v7_best.pt")
        target_streamlit = os.path.join(STREAMLIT_WEIGHTS_DIR, "phone_defect_model_v7_best.pt")
        shutil.copy2(best_weights_src, target_v7)
        shutil.copy2(best_weights_src, target_streamlit)
        print(f"\n[DEPLOYMENT] Bobot terbaik V7 berhasil disalin ke:")
        print(f"   -> {target_v7}")
        print(f"   -> {target_streamlit}")

    with open(status_file, "w") as f_stat:
        json.dump({
            "status": "COMPLETED",
            "model_version": "V7",
            "current_epoch": epochs,
            "total_epochs": epochs,
            "overall_progress_percent": 100.0,
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f_stat, indent=2)

    print("\n" + "=" * 75)
    print(" 🏆 PELATIHAN MODEL VERSI 7 SELESAI DENGAN SUKSES!")
    print("=" * 75 + "\n")
    return results

if __name__ == "__main__":
    v6_best = os.path.join(STREAMLIT_WEIGHTS_DIR, "phone_defect_model_v6_best.pt")
    default_model = v6_best if os.path.exists(v6_best) else "yolov8s.pt"

    parser = argparse.ArgumentParser(description="Train Model Versi 7 Unified Defect Detector")
    parser.add_argument("--epochs", type=int, default=40, help="Jumlah total epoch pelatihan (default: 40)")
    parser.add_argument("--batch", type=int, default=4, help="Ukuran batch per iterasi (default: 4)")
    parser.add_argument("--imgsz", type=int, default=800, help="Resolusi gambar input (default: 800)")
    parser.add_argument("--model", type=str, default=default_model, help="Base weights YOLO (default: V6 best or yolov8s.pt)")
    parser.add_argument("--device", type=str, default=None, help="Device komputasi: mps, cuda, atau cpu")
    parser.add_argument("--project", type=str, default="runs_v7_training", help="Direktori hasil run")
    parser.add_argument("--name", type=str, default="defect_v7_model", help="Nama subdirektori eksperimen")
    parser.add_argument("--prepare", action="store_true", help="Otomatis bangun dataset_v7 sebelum train")
    parser.add_argument("--resume", action="store_true", help="Lanjutkan pelatihan dari checkpoint last.pt terakhir")

    args = parser.parse_args()

    train_model_v7(
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        base_model=args.model,
        device=args.device,
        project=args.project,
        name=args.name,
        auto_prepare=args.prepare,
        resume=args.resume
    )
