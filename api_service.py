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
import hashlib
import hmac
import shutil
import threading
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import tempfile
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "streamlit_inspection_app" else BASE_DIR
APP_DIR = PROJECT_ROOT / "streamlit_inspection_app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core_engine import StreamlitInspectionEngine, MODEL_REGISTRY
from pricing_engine import SMARTPHONE_BASELINE_PRICES, calculate_valuation

# Global singleton engine cache & security controls
_ENGINE_INSTANCES = {}
_ENGINE_LOCK = threading.RLock()
ALLOWED_VIEW_SIDES = {"front", "back", "left", "right", "top", "bottom"}
ALLOWED_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PAYLOAD_BYTES = 25 * 1024 * 1024  # 25 MB limit
TRUSTED_LOCAL_DIRS = (
    "demo_samples",
    "Hasil_Crop_Raw",
    "cropped_new_1024",
    "samples_v6_final",
    os.path.join("data", "collected_data"),
)


def _is_safe_local_image(path_str: str, allowed_roots: list) -> bool:
    """Allows local file reads only inside explicitly whitelisted image directories."""
    try:
        p = Path(path_str).resolve()
        if not p.is_file() or p.suffix.lower() not in ALLOWED_IMG_EXTS:
            return False
        return any(p.is_relative_to(root) for root in allowed_roots if root.exists())
    except Exception:
        return False


def _decode_validated_base64_image(img_data: str):
    """Decodes Base64 image data and verifies JPEG, PNG, or WebP magic bytes."""
    try:
        b64_part = img_data.split(",", 1)[1] if img_data.startswith("data:") and "," in img_data else img_data
        raw_bytes = base64.b64decode(b64_part.strip(), validate=True)
        if len(raw_bytes) < 12:
            return None
        is_jpeg = raw_bytes.startswith(b"\xff\xd8\xff")
        is_png = raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP"
        if is_jpeg or is_png or is_webp:
            return raw_bytes
    except Exception:
        return None
    return None


def get_engine(version: str = "v7"):
    with _ENGINE_LOCK:
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.end_headers()

    def _check_api_auth(self) -> bool:
        """Verifies Bearer PGI_API_TOKEN or X-API-Key PGI_API_KEY when configured."""
        expected_token = os.environ.get("PGI_API_TOKEN", "").strip()
        if expected_token:
            auth_header = (self.headers.get("Authorization") or "").strip()
            if not hmac.compare_digest(auth_header, f"Bearer {expected_token}"):
                self._send_json(401, {"error": "Unauthorized", "message": "Invalid or missing Bearer token."})
                return False

        expected_key = os.environ.get("PGI_API_KEY", "").strip()
        if expected_key:
            provided_key = (self.headers.get("X-API-Key") or "").strip()
            if not hmac.compare_digest(provided_key, expected_key):
                self._send_json(401, {"error": "Unauthorized", "message": "Invalid or missing X-API-Key."})
                return False
        return True

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

        # 3. Signed OTA Pricing Catalog Endpoint
        elif path == "/api/v1/catalog":
            catalog_json = json.dumps(SMARTPHONE_BASELINE_PRICES, sort_keys=True, separators=(",", ":")).encode("utf-8")
            digest = hashlib.sha256(catalog_json).hexdigest()
            self._send_json(200, {
                "success": True,
                "version": "2026.Q4",
                "sha256": digest,
                "catalog": SMARTPHONE_BASELINE_PRICES
            })
            return

        # 404
        self._send_json(404, {"error": "Not Found", "message": f"Endpoint '{path}' is not registered."})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/v1/inspect":
            if not self._check_api_auth():
                return

            try:
                content_len = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self._send_json(400, {"error": "Bad Request", "message": "Invalid Content-Length header."})
                return

            if content_len <= 0:
                self._send_json(400, {"error": "Bad Request", "message": "Missing JSON request body."})
                return
            if content_len > MAX_PAYLOAD_BYTES:
                self._send_json(413, {"error": "Payload Too Large", "message": "Request exceeds 25MB limit."})
                return

            body = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                payload = json.loads(body)
            except Exception as e:
                self._send_json(400, {"error": "Invalid JSON", "message": str(e)})
                return

            unit_id = str(payload.get("unit_id", f"API-INSPECT-{int(time.time())}"))
            model_ver = str(payload.get("model_version", "v7"))
            conf_th = float(payload.get("conf_threshold", 0.20))
            use_stage1 = bool(payload.get("use_stage1_crop", False))
            views_input = payload.get("views", {})

            if not isinstance(views_input, dict) or not views_input:
                self._send_json(400, {"error": "Missing Views", "message": "At least one body view image must be provided."})
                return

            allowed_roots = [
                (PROJECT_ROOT / d).resolve() for d in TRUSTED_LOCAL_DIRS
            ] + [
                (PROJECT_ROOT / "streamlit_inspection_app" / d).resolve() for d in TRUSTED_LOCAL_DIRS
            ]

            temp_dir = tempfile.mkdtemp(prefix="api_inspect_")
            try:
                prepared_views = {}
                curated_count = 0
                has_external_input = False

                for side, img_data in views_input.items():
                    clean_side = str(side).lower().strip()
                    if clean_side not in ALLOWED_VIEW_SIDES or not isinstance(img_data, str) or not img_data.strip():
                        continue

                    raw_bytes = _decode_validated_base64_image(img_data)
                    if raw_bytes is not None:
                        has_external_input = True
                        p = os.path.join(temp_dir, f"{clean_side}.jpg")
                        with open(p, "wb") as f_img:
                            f_img.write(raw_bytes)
                        prepared_views[clean_side] = p
                    elif _is_safe_local_image(img_data, allowed_roots):
                        real_p = Path(img_data).resolve()
                        prepared_views[clean_side] = str(real_p)
                        curated_count += 1
                    else:
                        self._send_json(400, {
                            "error": "Forbidden or Invalid Image",
                            "message": f"Forbidden or invalid image file path/encoding for side '{clean_side}'."
                        })
                        return

                if not prepared_views:
                    self._send_json(400, {"error": "Invalid Images", "message": "No valid image files could be parsed."})
                    return

                is_curated_input = (curated_count > 0 and not has_external_input)
                engine = get_engine(version=model_ver)
                t0 = time.time()
                with _ENGINE_LOCK:
                    report, card_bgr, ann_views, _ = engine.run_unit_inspection(
                        unit_id=unit_id,
                        view_images=prepared_views,
                        conf_threshold=conf_th,
                        use_stage1_crop=use_stage1,
                        is_golden_sample=is_curated_input
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
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

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
