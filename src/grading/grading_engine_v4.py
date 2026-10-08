#!/usr/bin/env python3
"""
HIERARCHICAL DUAL-TIER COSMETIC GRADING ENGINE (V4)
==================================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Detection & Cosmetic Grading

Solves the V3 housing-only collapse by introducing a structured Dual-Tier grading model:
- Tier A: Screen Sub-Grade (front view) — strict standards for scratches & glass integrity.
- Tier B: Housing Sub-Grade (left, right, top, bottom, back) — cosmetic body wear & dents.
- Tier C: Consolidated Overall Grade:
    Final Grade = max(Screen Grade, Housing Grade) + Fast-Fail Veto Safeguards.
"""

import os
import sys
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import cv2
import numpy as np

from defect_detector import DefectDetector, DefectInstance, CLASS_COLORS

# Defect class severity weights
DEFECT_CLASS_WEIGHTS = {
    "scratch": 1.0,
    "dent": 3.0,
    "chip": 3.5,
    "crack": 10.0,
    "broken": 15.0
}

# Zone importance multipliers
ZONE_WEIGHTS = {
    "front": 3.0,     # Main touchscreen interface
    "back": 1.5,      # Back glass or metallic panel
    "bottom": 1.2,    # Bottom frame & ports
    "left": 1.0,      # Side rail
    "right": 1.0,     # Side rail
    "top": 1.0,       # Top frame
}

GRADE_RANKS = {"A": 0, "B": 1, "C": 2, "D": 3}
RANK_TO_GRADE = {0: "A", 1: "B", 2: "C", 3: "D"}


@dataclass
class SubGradeResult:
    grade: str
    dpi: float
    defect_count: int
    defects: List[Dict]
    reasons: List[str]


@dataclass
class UnitGradeResultV4:
    unit_id: str
    overall_grade: str
    screen_result: SubGradeResult
    housing_result: SubGradeResult
    total_dpi: float
    total_defects: int
    is_veto_triggered: bool
    veto_reason: Optional[str]
    elapsed_sec: float
    detections_by_view: Dict[str, List[Dict]]

    def to_dict(self):
        d = asdict(self)
        return d


class GradingEngineV4:
    """
    Model V4 Hierarchical Dual-Tier Grading Engine.
    """
    def __init__(self, detector: Optional[DefectDetector] = None):
        self.detector = detector or DefectDetector()

    def evaluate_screen(self, front_defects: List[DefectInstance]) -> SubGradeResult:
        """
        Evaluates touchscreen display condition.
        Front screen is the primary value driver for recommerce.
        """
        reasons = []
        screen_dpi = 0.0

        for d in front_defects:
            cls_w = DEFECT_CLASS_WEIGHTS.get(d.class_name, 1.0)
            size_factor = max(1.0, d.length_mm / 3.0)
            screen_dpi += (cls_w * ZONE_WEIGHTS["front"] * size_factor)

        # Fast-Fail checks for screen
        for d in front_defects:
            if d.class_name in ["crack", "broken"]:
                reasons.append(f"Screen has structural {d.class_name} ({d.length_mm:.1f}mm). Immediate Grade D.")
                return SubGradeResult(
                    grade="D",
                    dpi=screen_dpi,
                    defect_count=len(front_defects),
                    defects=[d.to_dict() for d in front_defects],
                    reasons=reasons
                )

        if len(front_defects) == 0:
            reasons.append("Screen is pristine (Zero Defect).")
            grade = "A"
        elif screen_dpi <= 4.0 and all(d.class_name == "scratch" and d.length_mm < 3.5 for d in front_defects):
            reasons.append(f"Screen has minor hairline scratch ({screen_dpi:.1f} DPI).")
            grade = "B"
        elif screen_dpi < 15.0:
            reasons.append(f"Screen has noticeable scratches/chips ({screen_dpi:.1f} DPI).")
            grade = "C"
        else:
            reasons.append(f"Screen has excessive scratches ({screen_dpi:.1f} DPI).")
            grade = "D"

        return SubGradeResult(
            grade=grade,
            dpi=round(screen_dpi, 2),
            defect_count=len(front_defects),
            defects=[d.to_dict() for d in front_defects],
            reasons=reasons
        )

    def evaluate_housing(self, housing_defects: List[DefectInstance]) -> SubGradeResult:
        """
        Evaluates body frame and back cover condition across left, right, top, bottom, and back.
        """
        reasons = []
        housing_dpi = 0.0

        for d in housing_defects:
            cls_w = DEFECT_CLASS_WEIGHTS.get(d.class_name, 1.0)
            zone_w = ZONE_WEIGHTS.get(d.view_side, 1.0)
            size_factor = max(1.0, d.length_mm / 3.0)
            housing_dpi += (cls_w * zone_w * size_factor)

        # Fast-Fail checks for housing
        for d in housing_defects:
            if d.class_name == "broken" or (d.class_name == "chip" and d.length_mm >= 4.5):
                reasons.append(f"Housing has severe {d.class_name} on {d.view_side} ({d.length_mm:.1f}mm).")
                return SubGradeResult(
                    grade="D",
                    dpi=housing_dpi,
                    defect_count=len(housing_defects),
                    defects=[d.to_dict() for d in housing_defects],
                    reasons=reasons
                )

        if housing_dpi < 3.0 and len(housing_defects) <= 1:
            reasons.append(f"Housing is like new ({housing_dpi:.1f} DPI).")
            grade = "A"
        elif housing_dpi < 15.0:
            reasons.append(f"Housing has light cosmetic wear ({housing_dpi:.1f} DPI).")
            grade = "B"
        elif housing_dpi < 40.0:
            reasons.append(f"Housing has heavy cosmetic wear/dents ({housing_dpi:.1f} DPI).")
            grade = "C"
        else:
            reasons.append(f"Housing has excessive cosmetic damage ({housing_dpi:.1f} DPI).")
            grade = "D"

        return SubGradeResult(
            grade=grade,
            dpi=round(housing_dpi, 2),
            defect_count=len(housing_defects),
            defects=[d.to_dict() for d in housing_defects],
            reasons=reasons
        )

    def evaluate_unit(self, unit_id: str, view_images: Dict[str, str]) -> UnitGradeResultV4:
        """
        Runs complete multi-view inspection and aggregates screen and housing grades.
        """
        t0 = time.time()
        detections_by_view = {}
        all_defects = []

        for side, path in view_images.items():
            if not os.path.exists(path):
                continue
            defs = self.detector.detect_image(path, view_side=side)
            detections_by_view[side] = defs
            all_defects.extend(defs)

        front_defects = detections_by_view.get("front", [])
        housing_defects = [d for d in all_defects if d.view_side != "front"]

        # Tier A & Tier B
        screen_res = self.evaluate_screen(front_defects)
        housing_res = self.evaluate_housing(housing_defects)

        # Tier C: Consolidation
        screen_rank = GRADE_RANKS[screen_res.grade]
        housing_rank = GRADE_RANKS[housing_res.grade]
        consolidated_rank = max(screen_rank, housing_rank)
        overall_grade = RANK_TO_GRADE[consolidated_rank]

        # Fast-Fail Veto Check on any view
        is_veto = False
        veto_reason = None
        for d in all_defects:
            if d.class_name in ["crack", "broken"]:
                is_veto = True
                veto_reason = f"Fatal defect '{d.class_name}' ({d.length_mm:.1f}mm) detected on {d.view_side}."
                overall_grade = "D"
                break

        elapsed = round(time.time() - t0, 3)
        total_dpi = round(screen_res.dpi + housing_res.dpi, 2)

        return UnitGradeResultV4(
            unit_id=unit_id,
            overall_grade=overall_grade,
            screen_result=screen_res,
            housing_result=housing_res,
            total_dpi=total_dpi,
            total_defects=len(all_defects),
            is_veto_triggered=is_veto,
            veto_reason=veto_reason,
            elapsed_sec=elapsed,
            detections_by_view={s: [d.to_dict() for d in defs] for s, defs in detections_by_view.items()}
        )
