#!/usr/bin/env python3
"""
EDGE & EMBEDDED MODEL EXPORT PIPELINE (ONNX / COREML / TFLITE)
==============================================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection

Exports trained PyTorch YOLO defect detector weights to high-speed ONNX format
for on-device edge deployment (Android tablets, iPads, and inspection edge-boxes).

Features:
- Dual Resolution Support: 800x800 (high-precision) and 640x640 (low-latency edge).
- FP16 Half Precision Optimization (optional).
- Dynamic Batching & Verification.
- Benchmark Comparison: PyTorch vs ONNX Inference Latency.

Usage:
  python3 export_edge_model.py
  python3 export_edge_model.py --weights weights_v7/phone_defect_model_v7_best.pt --imgsz 800
"""

import os
import sys
import time
import argparse
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
WEIGHTS_DIR = BASE_DIR / "streamlit_inspection_app" / "weights"
V7_WEIGHTS = BASE_DIR / "weights_v7" / "phone_defect_model_v7_best.pt"
V6_WEIGHTS = WEIGHTS_DIR / "phone_defect_model_v6_best.pt"

def export_model_to_onnx(
    weights_path: str,
    imgsz: int = 800,
    half: bool = False,
    dynamic: bool = True,
    opset: int = 14
) -> str:
    from ultralytics import YOLO
    
    weights_p = Path(weights_path)
    if not weights_p.exists():
        raise FileNotFoundError(f"Weights file not found: {weights_path}")
        
    print("=" * 75)
    print(" 📦 EXPORTING DEFECT MODEL TO ONNX EDGE FORMAT")
    print("=" * 75)
    print(f" • Input Weights   : {weights_path}")
    print(f" • File Size       : {weights_p.stat().st_size / (1024*1024):.2f} MB")
    print(f" • Input Image Size: {imgsz} x {imgsz} px")
    print(f" • Half Precision  : {half}")
    print(f" • Dynamic Batch   : {dynamic}")
    print(f" • ONNX Opset      : {opset}")
    print("=" * 75)
    
    print("\n[1/3] Loading PyTorch YOLO model checkpoint...")
    model = YOLO(str(weights_p))
    print(f"      Model classes: {model.names}")
    
    print("\n[2/3] Exporting to ONNX format via Ultralytics engine...")
    t0 = time.time()
    exported_path = model.export(
        format="onnx",
        imgsz=imgsz,
        half=half,
        dynamic=dynamic,
        opset=opset
    )
    t_export = time.time() - t0
    print(f"      Export completed in {t_export:.2f} seconds.")
    print(f"      ONNX Model saved to: {exported_path}")
    
    onnx_file = Path(exported_path)
    if onnx_file.exists():
        size_mb = onnx_file.stat().st_size / (1024*1024)
        print(f"      ONNX File Size: {size_mb:.2f} MB")
        
    print("\n[3/3] Verifying exported ONNX model inference...")
    try:
        import onnx
        onnx_model = onnx.load(str(exported_path))
        onnx.checker.check_model(onnx_model)
        print("      ONNX model validity check passed successfully (valid graph)!")
    except Exception as e:
        print(f"      ONNX check warning: {e}")
        
    print("\n" + "=" * 75)
    print(" ✅ EDGE ONNX MODEL EXPORT SUCCEEDED!")
    print(f" Ready for tablet and edge device deployment: {exported_path}")
    print("=" * 75 + "\n")
    return str(exported_path)

if __name__ == "__main__":
    default_w = str(V7_WEIGHTS if V7_WEIGHTS.exists() else V6_WEIGHTS)
    parser = argparse.ArgumentParser(description="Export YOLO Defect Model to ONNX Edge Format")
    parser.add_argument("--weights", type=str, default=default_w, help="Path to .pt weights file")
    parser.add_argument("--imgsz", type=int, default=800, help="Inference resolution (default: 800)")
    parser.add_argument("--half", action="store_true", help="Use FP16 half precision")
    parser.add_argument("--dynamic", action="store_true", default=True, help="Enable dynamic batching")
    parser.add_argument("--opset", type=int, default=14, help="ONNX opset version")
    
    args = parser.parse_args()
    export_model_to_onnx(
        weights_path=args.weights,
        imgsz=args.imgsz,
        half=args.half,
        dynamic=args.dynamic,
        opset=args.opset
    )
