#!/usr/bin/env python3
"""
MULTI-VIEW SMARTPHONE GRADING ENGINE
===================================
Aggregates defect detections across all smartphone views (front, back, left, right, top, bottom)
and determines the official cosmetic condition: Grade A, B, C, or D.

Grading Logic:
1. Veto Rules (Fast-Fail): Cracks or structural breaks immediately trigger Grade D.
2. Defect Penalty Index (DPI): Zone-weighted severity calculation.
3. Component-Specific Tolerances (Screen vs Housing vs Camera).
4. Automated Visual Inspection Report & JSON Generation.
"""

import os
import sys
import json
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import cv2
import numpy as np

from defect_detector import DefectDetector, DefectInstance, CLASS_COLORS
from ml_grading_aggregator import MLGradingAggregator

# Weights for defect types
DEFECT_CLASS_WEIGHTS = {
    "scratch": 1.0,
    "dent": 3.0,
    "chip": 3.5,
    "crack": 10.0,
    "broken": 15.0
}

# Zone multiplier weights (Screen is most critical)
ZONE_WEIGHTS = {
    "front": 3.0,       # Display screen
    "back": 1.5,        # Back glass / panel
    "left": 1.0,        # Side rail
    "right": 1.0,       # Side rail
    "top": 1.0,         # Top frame
    "bottom": 1.0,      # Bottom frame & ports
}

# Grade color indicators (BGR for OpenCV visualization)
GRADE_COLORS = {
    "A": (34, 139, 34),     # Forest Green (Mint)
    "B": (218, 165, 32),    # Goldenrod / Blue-Green (Very Good)
    "C": (0, 140, 255),     # Dark Orange (Good / Heavy Wear)
    "D": (30, 30, 220),     # Bright Red (Faulty / Broken)
}


class GradingEngine:
    """
    Cosmetic Smartphone Grading Engine (A, B, C, D) based on multi-view defect inspection,
    powered by a trained Machine Learning Aggregator with Fast-Fail Veto Safeguards.
    """
    def __init__(self, detector: Optional[DefectDetector] = None, ml_aggregator: Optional[MLGradingAggregator] = None):
        self.detector = detector or DefectDetector()
        self.ml_aggregator = ml_aggregator or MLGradingAggregator()

    def evaluate_phone_unit(self, unit_id: str, view_images: Dict[str, str]) -> Dict:
        """
        Runs inspection across all available views of a single smartphone unit.
        view_images: {"front": path, "left": path, ...}
        """
        start_time = time.time()
        detections_by_view = {}
        all_defects = []

        # 1. Run detection on each view
        for view_side, img_path in view_images.items():
            if not os.path.exists(img_path):
                continue
            defects = self.detector.detect_image(img_path, view_side=view_side)
            detections_by_view[view_side] = defects
            all_defects.extend(defects)

        # 2. Aggregate statistics
        class_counts = {c: 0 for c in ["scratch", "dent", "chip", "crack", "broken"]}
        for d in all_defects:
            if d.class_name in class_counts:
                class_counts[d.class_name] += 1

        front_defects = detections_by_view.get("front", [])
        back_defects = detections_by_view.get("back", [])
        body_defects = [d for d in all_defects if d.view_side not in ["front", "back"]]

        # 3. Calculate Defect Penalty Index (DPI)
        total_dpi = 0.0
        front_dpi = 0.0
        body_dpi = 0.0

        for d in all_defects:
            cls_w = DEFECT_CLASS_WEIGHTS.get(d.class_name, 1.0)
            zone_w = ZONE_WEIGHTS.get(d.view_side, 1.0)
            size_factor = max(1.0, d.length_mm / 3.0)
            penalty = cls_w * zone_w * size_factor

            total_dpi += penalty
            if d.view_side == "front":
                front_dpi += penalty
            else:
                body_dpi += penalty

        # 4. Predict cosmetic grade using Machine Learning Aggregator with Veto Safeguard
        defects_dict_list = [d.to_dict() for d in all_defects]
        feat_vector = self.ml_aggregator.extract_features_from_inspection(
            defects_dict_list,
            class_counts,
            total_dpi,
            front_dpi,
            body_dpi
        )
        grade, confidence, probs, reasons = self.ml_aggregator.predict_grade(
            feat_vector,
            class_counts
        )

        elapsed_sec = round(time.time() - start_time, 3)

        report = {
            "unit_id": unit_id,
            "final_grade": grade,
            "grade_confidence": round(confidence, 4),
            "grade_probabilities": probs,
            "grading_method": "ML_AGGREGATOR_VETO_SAFEGUARD",
            "total_dpi": round(total_dpi, 2),
            "front_dpi": round(front_dpi, 2),
            "body_dpi": round(body_dpi, 2),
            "total_defects_count": len(all_defects),
            "defect_breakdown": class_counts,
            "reasons": reasons,
            "inspection_time_sec": elapsed_sec,
            "views_inspected": list(view_images.keys()),
            "defects_detail": defects_dict_list
        }
        return report

    def _classify_grade(
        self,
        class_counts: Dict[str, int],
        front_defects: List[DefectInstance],
        body_defects: List[DefectInstance],
        total_dpi: float,
        front_dpi: float
    ) -> Tuple[str, List[str]]:
        reasons = []

        # --- TIER 1: VETO RULES (Immediate Grade D / Hard Caps) ---
        if class_counts.get("broken", 0) > 0:
            reasons.append(f"Veto: Unit memiliki kerusakan struktural parah ({class_counts['broken']} broken).")
            return "D", reasons

        if class_counts.get("crack", 0) > 0:
            reasons.append(f"Veto: Kaca retak terdeteksi ({class_counts['crack']} crack).")
            return "D", reasons

        # --- TIER 2: THRESHOLD-BASED CLASSIFICATION ---
        
        # Check Grade A criteria (Like New / Mint)
        # Condition: Screen 100% flawless, body at most 1 hairline scratch (< 2mm), zero dents, zero chips
        has_front_defect = len(front_defects) > 0
        has_dents = class_counts.get("dent", 0) > 0
        has_chips = class_counts.get("chip", 0) > 0

        if not has_front_defect and not has_dents and not has_chips and total_dpi < 3.0:
            reasons.append("Layar 100% mulus tanpa cacat.")
            reasons.append(f"Bodi kondisi prima (DPI {total_dpi:.1f} < 3.0).")
            return "A", reasons

        # Check Grade B criteria (Very Good)
        # Condition: Screen allows up to 2 micro-scratches (front_dpi < 4.0, zero chips),
        # Body allows minor scratches/micro-dents (total_dpi < 15.0)
        front_scratches_only = all(d.class_name == "scratch" and d.length_mm <= 5.0 for d in front_defects)
        if front_scratches_only and front_dpi < 4.0 and total_dpi < 15.0 and class_counts.get("dent", 0) <= 2:
            if has_front_defect:
                reasons.append(f"Layar memiliki {len(front_defects)} goresan mikro wajar (< 5mm).")
            else:
                reasons.append("Layar mulus.")
            reasons.append(f"Bodi memiliki tanda pemakaian ringan (DPI {total_dpi:.1f} < 15.0).")
            return "B", reasons

        # Check Grade C criteria (Good / Heavy Cosmetic Wear)
        # Condition: Heavy scratches, multiple dents or chips, but NO cracks or broken glass.
        if total_dpi < 40.0:
            reasons.append(f"Pemakaian kosmetik berat: DPI {total_dpi:.1f}.")
            if class_counts.get("dent", 0) > 0:
                reasons.append(f"Terdapat {class_counts['dent']} penyok (dent).")
            if class_counts.get("chip", 0) > 0:
                reasons.append(f"Terdapat {class_counts['chip']} cuil/gompel (chip) pada tepi.")
            if has_front_defect:
                reasons.append(f"Layar memiliki cacat terlihat (front DPI {front_dpi:.1f}).")
            return "C", reasons

        # Otherwise Grade D (Cosmetic or structural failure)
        reasons.append(f"Akumulasi cacat fisik melampaui batas toleransi (DPI {total_dpi:.1f} >= 40.0).")
        return "D", reasons

    def generate_inspection_card(
        self,
        unit_id: str,
        view_images: Dict[str, str],
        report: Dict,
        output_card_path: str
    ):
        """
        Generates a consolidated Multi-View Inspection Collage image with defect overlays,
        grade badge, and quantitative metric table.
        """
        # Load and annotate individual views
        annotated_views = {}
        target_height = 400

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

            # Resize while preserving aspect ratio for collage
            h, w = ann.shape[:2]
            scale = target_height / h
            resized = cv2.resize(ann, (int(w * scale), target_height))
            annotated_views[view_side] = resized

        if not annotated_views:
            return

        # Arrange views: Front in center or standard row
        order = ["front", "left", "right", "top", "bottom", "back"]
        view_strip = []
        for side in order:
            if side in annotated_views:
                img_v = annotated_views[side]
                # Add side label header
                header = np.zeros((35, img_v.shape[1], 3), dtype=np.uint8)
                header[:] = (40, 40, 40)
                cv2.putText(header, side.upper(), (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
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
        banner_h = 120
        banner_w = collage_row.shape[1]
        banner = np.zeros((banner_h, banner_w, 3), dtype=np.uint8)
        banner[:] = (25, 25, 25)

        grade = report["final_grade"]
        grade_color = GRADE_COLORS.get(grade, (128, 128, 128))

        # Grade Badge Box
        cv2.rectangle(banner, (20, 15), (140, 105), grade_color, -1)
        cv2.putText(banner, f"GRADE", (35, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(banner, f"{grade}", (50, 95), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 4)

        # Phone Unit Info & Statistics
        cv2.putText(banner, f"UNIT ID: {unit_id}", (160, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        stat_line = f"Total DPI: {report['total_dpi']} | Front DPI: {report['front_dpi']} | Defects: {report['total_defects_count']}"
        cv2.putText(banner, stat_line, (160, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        breakdown_str = f"Dent: {report['defect_breakdown']['dent']} | Broken: {report['defect_breakdown']['broken']} | Scratch: {report['defect_breakdown']['scratch']} | Chip: {report['defect_breakdown']['chip']} | Crack: {report['defect_breakdown']['crack']}"
        cv2.putText(banner, breakdown_str, (160, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 180, 180), 1)

        # Combine banner and images
        final_card = np.vstack([banner, collage_row])

        os.makedirs(os.path.dirname(output_card_path), exist_ok=True)
        cv2.imwrite(output_card_path, final_card)
        print(f"[GradingEngine] Inspection card saved: {output_card_path}")


if __name__ == "__main__":
    print("Testing GradingEngine with synthetic defects...")
    ge = GradingEngine()
    test_report = ge._classify_grade(
        class_counts={"scratch": 0, "dent": 0, "chip": 0, "crack": 0, "broken": 0},
        front_defects=[],
        body_defects=[],
        total_dpi=0.0,
        front_dpi=0.0
    )
    print("Zero defects grade:", test_report)
