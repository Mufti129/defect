#!/usr/bin/env python3
"""
CORE INFERENCE & GRADING ENGINE ADAPTER
======================================
Provides a unified interface for the Streamlit web application to run:
1. Multi-version smartphone defect detection (V1, V2, V3, V4, and V5).
2. Physical spatial scaling (ArUco + Dynamic Device Fallback).
3. Machine Learning Cosmetic Grading (Random Forest + Veto Safeguards).
4. High-Resolution Visual Inspection Collage Card generation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import cv2
import numpy as np

# Ensure parent directory is accessible for imports
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from defect_detector import DefectDetector, DefectInstance, CLASS_COLORS
from ml_grading_aggregator import MLGradingAggregator
from grading_engine import GradingEngine, GRADE_COLORS, DEFECT_CLASS_WEIGHTS, ZONE_WEIGHTS
from phone_localizer import PhoneBodyLocalizer
try:
    from object_guardrail import ObjectGuardrail
except Exception:
    class ObjectGuardrail:  # type: ignore
        def __init__(self, *args, **kwargs):
            self.model = None
        def validate_single_image(self, img, *args, **kwargs):
            return {"is_valid": True, "has_phone": True, "detected_non_phone": [], "detected_phone": [], "all_detections": [], "annotated_bgr": img, "rejection_message": None}
        def validate_views(self, view_images, *args, **kwargs):
            return {"is_valid": True, "rejected_views": [], "all_detected_objects": {}, "annotated_previews": {}, "rejection_summary": None}
from db_manager import InspectionDBManager
import tempfile

# -------------------------------------------------------------------------
# MODEL REGISTRY: Definisi 5 Versi Model AI Smartphone Defect Detection
# -------------------------------------------------------------------------
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "v5": {
        "id": "v5",
        "name": "Model Versi 5 (Housing-Only YOLOv8s 1024px - Checkpoint Terbaru)",
        "short_name": "Versi 5 (YOLOv8s 1024px)",
        "badge": "TERBARU (CHECKPOINT TERBAIK)",
        "badge_color": "#8B5CF6",
        "yolo_file": "phone_defect_model_v5_best.pt",
        "ml_file": "ml_grading_model_v3.joblib",
        "arch": "YOLOv8s Detect (1024x1024, 11M Params)",
        "dataset": "dataset_v5_full (1.918 Unit Bodi, Resolusi Asli)",
        "focus": "4 Sisi Housing (Top, Bottom, Left, Right)",
        "status": "Pelatihan Berjalan (Epoch 16/30 Selesai - Recall 68.4%, mAP50 36.1%)",
        "description": "Model resolusi tinggi 1024x1024 arsitektur YOLOv8s untuk ketajaman tekstur cacat mikro pada housing smartphone. Menggunakan checkpoint bobot terbaik dari proses pelatihan yang sedang berjalan (Epoch 16/30, Recall 68.4%, mAP50 36.1%)."
    },
    "v4": {
        "id": "v4",
        "name": "Model Versi 4 (Real Annotated Defect Detector - YOLOv8n)",
        "short_name": "Versi 4 (YOLOv8n Real)",
        "badge": "REAL ANNOTATED",
        "badge_color": "#0284C7",
        "yolo_file": "phone_defect_model_v4.pt",
        "ml_file": "ml_grading_model_v3.joblib",
        "arch": "YOLOv8n Detect (640x640, 3M Params)",
        "dataset": "dataset_v4_real (1.600+ Foto Riil Cacat Teranotasi)",
        "focus": "Bodi & Housing Smartphone",
        "status": "Selesai Dilatih (15 Epochs)",
        "description": "Model deteksi cacat fisik yang dilatih pada 1.600+ citra foto riil teranotasi bodi smartphone (5 kelas: dent, broken, scratch, chip, crack)."
    },
    "v3": {
        "id": "v3",
        "name": "Model Versi 3 (Housing-Only Skala Penuh 1.918 Unit - Random Forest 18 Fitur)",
        "short_name": "Versi 3 (Housing 1.918 Unit)",
        "badge": "REKOMENDASI PRODUKSI",
        "badge_color": "#10B981",
        "yolo_file": "phone_defect_model.pt",
        "ml_file": "ml_grading_model_v3.joblib",
        "arch": "YOLOv8-Seg Polygon + Random Forest 18 Fitur",
        "dataset": "Hasil_Crop_Raw (1.918 Unit / 7.672 Citra Bodi)",
        "focus": "4 Sisi Housing (Top, Bottom, Left, Right)",
        "status": "Teruji & Tervalidasi Stabil (Benchmark 57.0% Akurasi, 80% Recall Grade A)",
        "description": "Model produksi stabil yang dilatih pada 1.918 unit (>9.000 citra crop bodi) dengan 18 fitur spasial housing, Fast-Fail Veto sompal/broken, dan akurasi benchmark 57.0%."
    },
    "v2": {
        "id": "v2",
        "name": "Model Versi 2 (Multi-View 5-Sudut Skala Besar - Front & Body)",
        "short_name": "Versi 2 (Multi-View 5 Sisi)",
        "badge": "MULTI-VIEW 5-SISI",
        "badge_color": "#F59E0B",
        "yolo_file": "phone_defect_model.pt",
        "ml_file": "ml_grading_model_v2.joblib",
        "arch": "YOLOv8-Seg Nano + Random Forest 5-Sudut",
        "dataset": "Kohort 240 Unit Seimbang (1.200 Citra)",
        "focus": "5 Sudut (Front, Back, Left, Right, Bottom)",
        "status": "Model Evaluasi Multi-Sudut Layar",
        "description": "Model hibrida evaluasi 5 sudut pandang (termasuk layar depan Front), dilatih pada kohort seimbang 240 unit (1.200 citra) dengan penalti layar depan."
    },
    "v1": {
        "id": "v1",
        "name": "Model Versi 1 (Baseline Segmentation & Synthetic Heuristics)",
        "short_name": "Versi 1 (Baseline Prototipe)",
        "badge": "BASELINE V1",
        "badge_color": "#64748B",
        "yolo_file": "phone_defect_model.pt",
        "ml_file": "ml_grading_model.joblib",
        "arch": "YOLOv8-Seg Nano + Static Heuristics",
        "dataset": "Dataset Sintetis Awal 120 Sampel",
        "focus": "Universal (5 Sudut)",
        "status": "Prototipe Awal",
        "description": "Model prototipe awal segmentasi cacat poligon pada dataset sintetis 120 sampel, dipadukan dengan aturan penalti heuristik statis."
    }
}


class StreamlitInspectionEngine:
    """
    Singleton-friendly wrapper for fast inspection and card generation in Streamlit.
    Supports dynamic switching between Model Versions V1, V2, V3, V4, and V5.
    """
    def __init__(self, version: str = "v5", weights_dir: Optional[str] = None):
        if version not in MODEL_REGISTRY:
            version = "v3"
        self.version = version
        self.config = MODEL_REGISTRY[version]

        if weights_dir is None:
            local_weights = CURRENT_DIR / "weights"
            parent_weights = PARENT_DIR / "weights"
            if local_weights.exists():
                weights_dir = str(local_weights)
            else:
                weights_dir = str(parent_weights)

        self.weights_dir = weights_dir

        yolo_filename = self.config["yolo_file"]
        ml_filename = self.config["ml_file"]

        yolo_path = os.path.join(weights_dir, yolo_filename)
        if not os.path.exists(yolo_path):
            # Check parent directory fallback
            alt_parent = os.path.join(str(PARENT_DIR), f"weights_{version}", yolo_filename)
            if os.path.exists(alt_parent):
                yolo_path = alt_parent
            else:
                alt_path = os.path.join(weights_dir, "phone_defect_model.pt")
                if os.path.exists(alt_path):
                    yolo_path = alt_path

        ml_path = os.path.join(weights_dir, ml_filename)
        if not os.path.exists(ml_path):
            alt_ml = os.path.join(weights_dir, "ml_grading_model.joblib")
            if os.path.exists(alt_ml):
                ml_path = alt_ml

        print(f"[InspectionEngine] Initializing Model {version.upper()}: {self.config['name']}")
        print(f"                   YOLO: {yolo_path}")
        print(f"                   ML  : {ml_path}")

        # Initialize detector with hardware acceleration (MPS/CPU)
        self.detector = DefectDetector(weights_path=yolo_path)
        self.ml_aggregator = MLGradingAggregator(model_path=ml_path)
        self.grading_engine = GradingEngine(detector=self.detector, ml_aggregator=self.ml_aggregator)
        self.phone_localizer = PhoneBodyLocalizer()
        self.guardrail = ObjectGuardrail()
        self.db_manager = InspectionDBManager()
        self.last_stage1_previews = {}

    def run_unit_inspection(
        self,
        unit_id: str,
        view_images: Dict[str, str],
        conf_threshold: Optional[float] = None,
        use_stage1_crop: bool = True
    ) -> Tuple[Dict[str, Any], np.ndarray, Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """
        Runs complete evaluation across all provided views and generates the visual inspection card.
        Integrates:
        1. Object Guardrail (Rejects non-phone objects: person, bottle, laptop, animal, etc.)
        2. Stage 1 (Phone Body Localizer & Auto-Crop) to eliminate background noise.
        3. Stage 2 (Defect Inspection & Physical Grading).
        4. Persistent Data Bank Logging (SQLite + Storage).

        Returns:
            report: Full inspection JSON dictionary with active model metadata.
            card_bgr: OpenCV BGR image of the generated collage card.
            annotated_views: Dictionary of high-res annotated OpenCV images per view.
            stage1_previews: Dictionary of Stage 1 verification comparison images per view.
        """
        # -------------------------------------------------------------
        # Step 0: Input Object Guardrail (Validate against non-phone objects)
        # -------------------------------------------------------------
        guardrail_res = self.guardrail.validate_views(view_images)
        if not guardrail_res["is_valid"]:
            # Rejected non-phone input! Provide visual feedback and instruct re-input
            report = {
                "unit_id": unit_id,
                "status": "REJECTED_NON_PHONE",
                "is_valid_phone": False,
                "rejection_summary": guardrail_res["rejection_summary"],
                "rejected_views": guardrail_res["rejected_views"],
                "all_detected_objects": guardrail_res["all_detected_objects"],
                "model_version": self.version,
                "model_name": self.config["name"],
                "model_arch": self.config["arch"],
                "model_status": self.config["status"],
                "stage1_enabled": False,
                "final_grade": None,
                "grade_confidence": 0.0,
                "total_dpi": 0.0,
                "frame_dpi": 0.0,
                "bottom_back_dpi": 0.0,
                "total_defects_count": 0,
                "reasons": [guardrail_res["rejection_summary"] or "Objek bukan bodi smartphone."],
                "inspection_time_sec": 0.1
            }
            card_bgr = self._create_guardrail_card(guardrail_res["annotated_previews"], guardrail_res["rejection_summary"])
            # Save rejection record into database bank for dataset audit
            try:
                self.db_manager.save_record(
                    unit_id=unit_id,
                    model_version=self.version,
                    model_name=self.config["name"],
                    is_valid_phone=False,
                    rejection_reason=guardrail_res["rejection_summary"],
                    detected_objects=guardrail_res["all_detected_objects"],
                    report=report,
                    raw_views=view_images,
                    annotated_views_bgr=guardrail_res["annotated_previews"],
                    card_bgr=card_bgr
                )
            except Exception as e:
                print(f"[InspectionEngine] DB save error: {e}")

            return report, card_bgr, guardrail_res["annotated_previews"], {}

        stage1_previews = {}
        stage1_meta = {}
        inspected_views = {}

        if use_stage1_crop:
            stage1_temp_dir = tempfile.mkdtemp(prefix="stage1_crop_")
            for side, p in view_images.items():
                if not os.path.exists(p):
                    continue
                img = cv2.imread(p)
                if img is None:
                    continue
                crop_res = self.phone_localizer.localize_and_crop(img, side)
                crop_path = os.path.join(stage1_temp_dir, f"{side}.jpg")
                cv2.imwrite(crop_path, crop_res["cropped_img"])
                inspected_views[side] = crop_path
                stage1_previews[side] = crop_res["preview_img"]
                stage1_meta[side] = {
                    "bbox": list(crop_res["bbox"]),
                    "tilt_angle": float(round(crop_res["tilt_angle"], 2)),
                    "confidence": str(crop_res["confidence"])
                }
        else:
            inspected_views = view_images

        # Run grading on clean inspected views
        report = self.grading_engine.evaluate_phone_unit(
            unit_id,
            inspected_views,
            conf_threshold=conf_threshold
        )

        # Inject model metadata & Stage 1 results
        report["status"] = "SUCCESS"
        report["is_valid_phone"] = True
        report["model_version"] = self.version
        report["model_name"] = self.config["name"]
        report["model_arch"] = self.config["arch"]
        report["model_status"] = self.config["status"]
        report["stage1_enabled"] = use_stage1_crop
        report["stage1_meta"] = stage1_meta
        if conf_threshold is not None:
            report["conf_threshold_used"] = conf_threshold

        # Generate collage card in memory reusing precomputed defects
        card_bgr, annotated_views = self.generate_card_image(
            report,
            inspected_views,
            conf_threshold=conf_threshold
        )
        # Clean internal objects to ensure JSON serializability
        report.pop("_defect_instances_by_view", None)
        self.last_stage1_previews = stage1_previews

        # Save successful inspection record and images to persistent database bank
        try:
            self.db_manager.save_record(
                unit_id=unit_id,
                model_version=self.version,
                model_name=self.config["name"],
                is_valid_phone=True,
                report=report,
                raw_views=view_images,
                cropped_views=inspected_views if use_stage1_crop else None,
                annotated_views_bgr=annotated_views,
                card_bgr=card_bgr
            )
        except Exception as e:
            print(f"[InspectionEngine] Warning: Could not save record to database: {e}")

        return report, card_bgr, annotated_views, stage1_previews

    def _create_guardrail_card(
        self,
        annotated_views: Dict[str, np.ndarray],
        rejection_reason: Optional[str] = None,
        target_height: int = 450
    ) -> np.ndarray:
        """
        Creates a visual rejection collage showing the detected non-phone objects with a warning header.
        """
        resized_views = []
        for side, img in annotated_views.items():
            if img is None:
                continue
            h, w = img.shape[:2]
            scale = target_height / max(1, h)
            resized = cv2.resize(img, (int(w * scale), target_height))
            
            # Add side header
            header = np.full((36, resized.shape[1], 3), (40, 20, 25), dtype=np.uint8)
            cv2.putText(header, f"SISI {side.upper()} (NON-PHONE)", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            resized_views.append(np.vstack([header, resized]))

        if not resized_views:
            blank = np.zeros((300, 600, 3), dtype=np.uint8)
            cv2.putText(blank, "Input Ditolak - Bukan Bodi Smartphone", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return blank

        # Horizontal collage
        max_h = max(v.shape[0] for v in resized_views)
        padded = []
        for v in resized_views:
            if v.shape[0] < max_h:
                pad = np.zeros((max_h - v.shape[0], v.shape[1], 3), dtype=np.uint8)
                v = np.vstack([v, pad])
            padded.append(v)
            divider = np.full((max_h, 3, 3), (80, 80, 80), dtype=np.uint8)
            padded.append(divider)

        strip = np.hstack(padded[:-1])

        # Top Warning Banner (Red/Crimson)
        banner_h = 60
        banner = np.full((banner_h, strip.shape[1], 3), (25, 20, 180), dtype=np.uint8)
        title = "PERINGATAN: INPUT DITOLAK - TERDETEKSI BUKAN BODI SMARTPHONE"
        sub = "Sistem inspeksi hanya memproses smartphone. Harap masukkan ulang foto bodi HP yang benar."
        cv2.putText(banner, title, (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(banner, sub, (16, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 230, 255), 1, cv2.LINE_AA)

        return np.vstack([banner, strip])

    def generate_card_image(
        self,
        report: Dict[str, Any],
        view_images: Dict[str, str],
        target_height: int = 500,
        conf_threshold: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Renders the high-resolution inspection card image with Grade Badge, metadata,
        and defect bounding boxes/masks across all inspected views. Reuses precomputed
        detections to ensure 100% visual fidelity without redundant inference passes.
        """
        annotated_views_resized = {}
        annotated_views_full = {}

        precomputed_by_view = report.get("_defect_instances_by_view", {})

        for view_side, img_path in view_images.items():
            if not os.path.exists(img_path):
                continue

            img = cv2.imread(img_path)
            if img is None:
                continue

            # Obtain precomputed defects or fallback to dynamic detect
            if view_side in precomputed_by_view:
                defects = precomputed_by_view[view_side]
            else:
                defects = self.detector.detect_image(
                    img_path,
                    view_side=view_side,
                    filter_hands=True,
                    conf_threshold=conf_threshold
                )

            ann = self.detector.draw_defects_on_image(img, defects, hand_mask=None)
            annotated_views_full[view_side] = ann

            # Resize preserving aspect ratio for the composite card
            h, w = ann.shape[:2]
            scale = target_height / max(1, h)
            resized = cv2.resize(ann, (int(w * scale), target_height))
            annotated_views_resized[view_side] = resized

        if not annotated_views_resized:
            blank = np.zeros((300, 600, 3), dtype=np.uint8)
            cv2.putText(blank, "No Valid Views Loaded", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            return blank, {}

        # Preferred order for 4-side housing inspection (or 5-side if front/back included)
        order = ["top", "bottom", "left", "right", "back", "front"]
        view_strip = []
        for side in order:
            if side in annotated_views_resized:
                img_v = annotated_views_resized[side]
                header = np.zeros((40, img_v.shape[1], 3), dtype=np.uint8)
                header[:] = (35, 35, 35)
                cv2.putText(header, side.upper(), (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                combined = np.vstack([header, img_v])
                view_strip.append(combined)

        # Concatenate horizontally
        max_h = max(v.shape[0] for v in view_strip)
        padded_strip = []
        for v in view_strip:
            if v.shape[0] < max_h:
                pad = np.zeros((max_h - v.shape[0], v.shape[1], 3), dtype=np.uint8)
                v = np.vstack([v, pad])
            padded_strip.append(v)

        collage_row = np.hstack(padded_strip)

        # Build Top Banner (Inspection Header & Grade Badge)
        banner_h = 135
        banner_w = collage_row.shape[1]
        banner = np.zeros((banner_h, banner_w, 3), dtype=np.uint8)
        banner[:] = (20, 20, 20)

        grade = report.get("final_grade", "D")
        grade_color = GRADE_COLORS.get(grade, (128, 128, 128))

        # Grade Badge Box
        cv2.rectangle(banner, (20, 15), (145, 120), grade_color, -1)
        cv2.putText(banner, "GRADE", (38, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(banner, f"{grade}", (52, 108), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4)

        # Phone Unit Info & Statistics
        unit_id = report.get("unit_id", "UNKNOWN")
        confidence = report.get("grade_confidence", 0.0)
        cv2.putText(banner, f"UNIT: {unit_id} (Conf: {confidence*100:.1f}%)", (165, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)

        # Model Version Tag on Right Side of Header
        model_tag = f"MODEL: {self.config.get('short_name', self.version.upper())}"
        tag_size = cv2.getTextSize(model_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)[0]
        tag_x = max(165, banner_w - tag_size[0] - 25)
        cv2.putText(banner, model_tag, (tag_x, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (220, 200, 100), 2)

        stat_line = f"Total DPI: {report.get('total_dpi', 0.0)} | Frame DPI: {report.get('frame_dpi', 0.0)} | Defects Found: {report.get('total_defects_count', 0)}"
        cv2.putText(banner, stat_line, (165, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 1)

        breakdown = report.get("defect_breakdown", {})
        breakdown_str = f"Dent: {breakdown.get('dent', 0)} | Scratch: {breakdown.get('scratch', 0)} | Chip: {breakdown.get('chip', 0)} | Crack: {breakdown.get('crack', 0)} | Broken: {breakdown.get('broken', 0)}"
        cv2.putText(banner, breakdown_str, (165, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 180, 180), 1)

        # Combine banner and collage
        final_card = np.vstack([banner, collage_row])
        return final_card, annotated_views_full
