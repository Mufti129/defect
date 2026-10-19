#!/usr/bin/env python3
"""
ENTERPRISE REST API SERVICE FOR PGI CORE SYSTEM INTEGRATION
===========================================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection & Valuation

Exposes standard HTTP REST endpoints for seamless integration with:
- PGI Core Pawn Banking / ERP System
- Point of Sale (POS) Cashier Terminals
- Branch Mobile App / Field Inspector Tablets

Endpoints:
  GET  /api/v1/health   -> Service and model health status
  GET  /api/v1/pricing  -> Instant market price and loan disbursement calculation
  POST /api/v1/inspect  -> Full automated multi-view defect inspection & grading

Usage:
  python3 api_service.py --port 8504
"""

import os
import sys
import json
import time
import base64
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import tempfile
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "streamlit_inspection_app"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core_engine import StreamlitInspectionEngine, MODEL_REGISTRY
from pricing_engine import SMARTPHONE_BASELINE_PRICES, calculate_valuation

# Global singleton engine cache
_ENGINE_INSTANCES = {}

def get_engine(version: str = "v7"):
    if version not in _ENGINE_INSTANCES:
        print(f"[API Engine] Instantiating Inspection Engine: {version}")
        _ENGINE_INSTANCES[version] = StreamlitInspectionEngine(version=version)
    return _ENGINE_INSTANCES[version]

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class DefectInspectionAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        # 1. Health check
        if path == "/api/v1/health":
            self._send_json(200, {
                "status": "UP",
                "service": "PGI Automated Smartphone Defect Inspection & Valuation REST API",
                "version": "4.2-Enterprise",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "available_models": list(MODEL_REGISTRY.keys()),
                "default_model": "v7"
            })
            return

        # 2. Instant Valuation Pricing Query
        elif path == "/api/v1/pricing":
            brand = params.get("brand", ["Apple"])[0]
            model_name = params.get("model", ["iPhone 13"])[0]
            capacity = params.get("capacity", ["128GB"])[0]
            grade = params.get("grade", ["B"])[0].upper()
            hardware_score = float(params.get("health_score", [95.0])[0])

            val = calculate_valuation(
                brand=brand,
                model=model_name,
                storage=capacity,
                cosmetic_grade=grade,
                hardware_health_percent=hardware_score
            )
            self._send_json(200, {
                "success": True,
                "query": {
                    "brand": brand,
                    "model": model_name,
                    "capacity": capacity,
                    "grade": grade,
                    "hardware_health_score": hardware_score
                },
                "valuation": val
            })
            return

        # 404
        self._send_json(404, {"error": "Not Found", "message": f"Endpoint '{path}' is not registered."})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/v1/inspect":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self._send_json(400, {"error": "Bad Request", "message": "Missing JSON request body."})
                return

            body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception as e:
                self._send_json(400, {"error": "Invalid JSON", "message": str(e)})
                return

            unit_id = payload.get("unit_id", f"API-INSPECT-{int(time.time())}")
            model_ver = payload.get("model_version", "v7")
            conf_th = float(payload.get("conf_threshold", 0.20))
            use_stage1 = bool(payload.get("use_stage1_crop", False))
            views_input = payload.get("views", {})

            if not views_input:
                self._send_json(400, {"error": "Missing Views", "message": "At least one body view image must be provided."})
                return

            # Prepare image paths (supports local file paths or Base64 encoded strings)
            temp_dir = tempfile.mkdtemp(prefix="api_inspect_")
            prepared_views = {}

            for side, img_data in views_input.items():
                if isinstance(img_data, str) and os.path.exists(img_data):
                    prepared_views[side] = img_data
                elif isinstance(img_data, str) and len(img_data) > 100:
                    # Treat as base64
                    try:
                        if "," in img_data:
                            img_data = img_data.split(",", 1)[1]
                        raw_bytes = base64.b64decode(img_data)
                        p = os.path.join(temp_dir, f"{side}.jpg")
                        with open(p, "wb") as f_img:
                            f_img.write(raw_bytes)
                        prepared_views[side] = p
                    except Exception as e:
                        print(f"[API] Error decoding base64 for {side}: {e}")

            if not prepared_views:
                self._send_json(400, {"error": "Invalid Images", "message": "No valid image files could be parsed."})
                return

            try:
                engine = get_engine(version=model_ver)
                t0 = time.time()
                report, card_bgr, ann_views, _ = engine.run_unit_inspection(
                    unit_id=unit_id,
                    view_images=prepared_views,
                    conf_threshold=conf_th,
                    use_stage1_crop=use_stage1,
                    is_golden_sample=True
                )
                elapsed = round(time.time() - t0, 3)

                # Optional Valuation calculation
                dev_info = payload.get("device_info", {})
                brand = dev_info.get("brand", "Apple")
                model_name = dev_info.get("model", "iPhone 13")
                capacity = dev_info.get("capacity", "128GB")
                health_score = float(dev_info.get("health_score", 95.0))
                grade = report.get("final_grade", "B")

                val_result = calculate_valuation(
                    brand=brand,
                    model=model_name,
                    storage=capacity,
                    cosmetic_grade=grade,
                    hardware_health_percent=health_score
                )

                response_data = {
                    "success": True,
                    "unit_id": unit_id,
                    "final_grade": grade,
                    "grade_confidence": report.get("grade_confidence", 0.0),
                    "grade_probabilities": report.get("grade_probabilities", {}),
                    "total_dpi": report.get("total_dpi", 0.0),
                    "total_defects_count": report.get("total_defects_count", 0),
                    "defect_breakdown": report.get("defect_breakdown", {}),
                    "reasons": report.get("reasons", []),
                    "inspection_latency_sec": elapsed,
                    "model_version_used": model_ver,
                    "valuation": val_result,
                    "defects_detail": report.get("defects_detail", [])[:15]
                }
                self._send_json(200, response_data)

            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json(500, {"error": "Inspection Error", "message": str(e)})

        else:
            self._send_json(404, {"error": "Not Found", "message": f"Endpoint '{path}' is not registered."})

def run_api_server(host: str = "0.0.0.0", port: int = 8504):
    server = ThreadedHTTPServer((host, port), DefectInspectionAPIHandler)
    print("=" * 75)
    print(f" 🚀 PGI ENTERPRISE REST API SERVICE RUNNING ON http://{host}:{port}")
    print("=" * 75)
    print(f" • Health Check : GET  http://localhost:{port}/api/v1/health")
    print(f" • Price Query  : GET  http://localhost:{port}/api/v1/pricing?brand=Apple&model=iPhone%2013&grade=B")
    print(f" • Full Inspect : POST http://localhost:{port}/api/v1/inspect")
    print("=" * 75 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[API] Server stopping...")
        server.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PGI Defect Inspection REST API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding host")
    parser.add_argument("--port", type=int, default=8504, help="Binding port (default: 8504)")
    args = parser.parse_args()
    run_api_server(host=args.host, port=args.port)
