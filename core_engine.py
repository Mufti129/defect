#!/usr/bin/env python3
"""
CORE INFERENCE & GRADING ENGINE ADAPTER
======================================
Provides a unified interface for the Streamlit web application to run:
1. Multi-view phone defect detection (YOLOv8-Seg + Glare & Cluster Filter).
2. Physical spatial scaling (ArUco + Dynamic Device Fallback).
3. Machine Learning Cosmetic Grading (Random Forest 18 features + Veto Safeguards).
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

class StreamlitInspectionEngine:
    """
    Singleton-friendly wrapper for fast inspection and card generation in Streamlit.
    """
    def __init__(self, weights_dir: Optional[str] = None):
        if weights_dir is None:
            # Check local weights folder, then parent weights folder
            local_weights = CURRENT_DIR / "weights"
            parent_weights = PARENT_DIR / "weights"
            if local_weights.exists():
                weights_dir = str(local_weights)
            else:
                weights_dir = str(parent_weights)

        self.weights_dir = weights_dir
        yolo_path = os.path.join(weights_dir, "phone_defect_model.pt")
        ml_path = os.path.join(weights_dir, "ml_grading_model.joblib")

        print(f"[InspectionEngine] Initializing with YOLO: {yolo_path}")
        print(f"[InspectionEngine] Initializing with ML Model: {ml_path}")

        # Initialize detector with optimized CPU inference
        self.detector = DefectDetector(weights_path=yolo_path, device="cpu")
        self.ml_aggregator = MLGradingAggregator(model_path=ml_path)
        self.grading_engine = GradingEngine(detector=self.detector, ml_aggregator=self.ml_aggregator)

    def run_unit_inspection(self, unit_id: str, view_images: Dict[str, str]) -> Tuple[Dict[str, Any], np.ndarray]:
        """
        Runs complete evaluation across all provided views and generates the visual inspection card.

        Returns:
            report: Full inspection JSON dictionary.
            card_bgr: OpenCV BGR image of the generated collage card.
        """
        # Run grading
        report = self.grading_engine.evaluate_phone_unit(unit_id, view_images)

        # Generate collage card in memory
        card_bgr = self.generate_card_image(report, view_images)
        return report, card_bgr

    def generate_card_image(self, report: Dict[str, Any], view_images: Dict[str, str], target_height: int = 500) -> np.ndarray:
        """
        Renders the high-resolution inspection card image with Grade Badge, metadata,
        and defect bounding boxes/masks across all inspected views.
        """
        annotated_views = {}

        for view_side, img_path in view_images.items():
            if not os.path.exists(img_path):
                continue

            img = cv2.imread(img_path)
            if img is None:
                continue

            # Run detection on image with hand masking
            _, hand_mask = self.detector.hand_filter.generate_inspection_mask(img, view_side)
            defects = self.detector.detect_image(img_path, view_side=view_side, filter_hands=True)
            ann = self.detector.draw_defects_on_image(img, defects, hand_mask=hand_mask)

            # Resize preserving aspect ratio
            h, w = ann.shape[:2]
            scale = target_height / max(1, h)
            resized = cv2.resize(ann, (int(w * scale), target_height))
            annotated_views[view_side] = resized

        if not annotated_views:
            # Fallback blank image
            blank = np.zeros((300, 600, 3), dtype=np.uint8)
            cv2.putText(blank, "No Valid Views Loaded", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            return blank

        # Preferred order for housing inspection
        order = ["back", "left", "right", "top", "bottom"]
        view_strip = []
        for side in order:
            if side in annotated_views:
                img_v = annotated_views[side]
                # Side label header
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
        banner_h = 130
        banner_w = collage_row.shape[1]
        banner = np.zeros((banner_h, banner_w, 3), dtype=np.uint8)
        banner[:] = (20, 20, 20)

        grade = report.get("final_grade", "D")
        grade_color = GRADE_COLORS.get(grade, (128, 128, 128))

        # Grade Badge Box
        cv2.rectangle(banner, (20, 15), (145, 115), grade_color, -1)
        cv2.putText(banner, "GRADE", (38, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(banner, f"{grade}", (52, 105), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4)

        # Phone Unit Info & Statistics
        unit_id = report.get("unit_id", "UNKNOWN")
        confidence = report.get("grade_confidence", 0.0)
        cv2.putText(banner, f"UNIT: {unit_id} (Conf: {confidence*100:.1f}%)", (165, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)

        stat_line = f"Total DPI: {report.get('total_dpi', 0.0)} | Frame DPI: {report.get('frame_dpi', 0.0)} | Defects Found: {report.get('total_defects_count', 0)}"
        cv2.putText(banner, stat_line, (165, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 1)

        breakdown = report.get("defect_breakdown", {})
        breakdown_str = f"Dent: {breakdown.get('dent', 0)} | Scratch: {breakdown.get('scratch', 0)} | Chip: {breakdown.get('chip', 0)} | Crack: {breakdown.get('crack', 0)} | Broken: {breakdown.get('broken', 0)}"
        cv2.putText(banner, breakdown_str, (165, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 180, 180), 1)

        # Combine banner and collage
        final_card = np.vstack([banner, collage_row])
        return final_card
