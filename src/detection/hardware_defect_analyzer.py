"""
HARDWARE DEFECT DISAMBIGUATOR & MATERIAL GUARD
=============================================
Pusat Gadai Indonesia (PGI) — Smartphone Quality Assurance System

Evaluates candidate defect detections against physical hardware components:
1. Identifies and suppresses false positives on normal cavities (USB ports, speakers, screws).
2. Detects genuine hardware damage (bent port rim, punctured speaker mesh, stripped screws).
3. Applies physical material guards (reclassifies impossible glass cracks on metal chassis).
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from src.detection.hardware_locator import HardwareComponent


def calculate_box_overlap(
    box1: Tuple[int, int, int, int], 
    box2: Tuple[int, int, int, int]
) -> Dict[str, float]:
    """
    Calculates intersection, union, IoU, and containment ratios between two bounding boxes.
    box format: (x1, y1, x2, y2)
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    inter_x1 = max(x1_1, x1_2)
    inter_y1 = max(y1_1, y1_2)
    inter_x2 = min(x2_1, x2_2)
    inter_y2 = min(y2_1, y2_2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = float(inter_w * inter_h)

    area1 = float(max(1, (x2_1 - x1_1) * (y2_1 - y1_1)))
    area2 = float(max(1, (x2_2 - x1_2) * (y2_2 - y1_2)))
    union_area = area1 + area2 - inter_area

    iou = inter_area / max(union_area, 1.0)
    containment_1_in_2 = inter_area / area1  # Proportion of box1 inside box2
    containment_2_in_1 = inter_area / area2  # Proportion of box2 inside box1

    return {
        "inter_area": inter_area,
        "iou": iou,
        "containment_in_target": containment_1_in_2,
        "target_containment": containment_2_in_1,
        "area1": area1,
        "area2": area2
    }


class HardwareDefectDisambiguator:
    """
    Disambiguates candidate defects against known smartphone hardware components.
    """

    def __init__(self):
        pass

    def disambiguate_defects(
        self,
        defects: List[Any],  # List of DefectInstance
        hardware_components: List[HardwareComponent],
        view_side: str,
        img_w: int,
        img_h: int
    ) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """
        Filters and annotates defects by comparing them with physical hardware boundaries.
        Returns:
            - validated_defects: List[DefectInstance]
            - audit_log: List[Dict] with reasons for dropped/reclassified defects
        """
        validated_defects: List[Any] = []
        audit_log: List[Dict[str, Any]] = []

        for defect in defects:
            dbx1, dby1, dbx2, dby2 = defect.bbox
            d_area = max(1.0, float((dbx2 - dbx1) * (dby2 - dby1)))
            d_cls = defect.class_name.lower()
            aspect_ratio = max(dbx2 - dbx1, dby2 - dby1) / max(min(dbx2 - dbx1, dby2 - dby1), 1)

            # --- RULE 1: PHYSICAL MATERIAL GUARD ---
            # Side frames (bottom, top, left, right) are metal/plastic; cannot have crystalline glass shatter ('broken'/'crack')
            if view_side in ["bottom", "top", "left", "right"]:
                if d_cls in ["broken", "crack"]:
                    if aspect_ratio >= 2.2:
                        defect.class_name = "scratch"
                        audit_log.append({
                            "action": "reclassified_material",
                            "from": d_cls,
                            "to": "scratch",
                            "reason": "Linear defect on metal/plastic frame converted to scratch"
                        })
                    else:
                        defect.class_name = "chip"
                        audit_log.append({
                            "action": "reclassified_material",
                            "from": d_cls,
                            "to": "chip",
                            "reason": "Chassis impact defect converted from broken to chip"
                        })

            # Check overlap against all detected hardware components on this view
            is_suppressed = False
            is_true_hardware_damage = False
            matched_hardware_name = None

            for comp in hardware_components:
                overlap = calculate_box_overlap(defect.bbox, comp.bbox)
                c_in_hw = overlap["containment_in_target"]

                if c_in_hw > 0.40:
                    matched_hardware_name = comp.name

                    # --- EVALUATION A: Defect is strictly inside normal component cavity ---
                    # If defect is fully or mostly contained inside the component cavity without abnormal enlargement
                    if c_in_hw >= 0.70 and overlap["area1"] <= (comp.area_pixels * 1.35):
                        # This is a normal cavity (USB slot, speaker hole, screw) misidentified as a defect
                        is_suppressed = True
                        audit_log.append({
                            "action": "suppressed_normal_hardware",
                            "component": comp.name,
                            "containment": c_in_hw,
                            "bbox": defect.bbox,
                            "reason": f"Defect falls {c_in_hw*100:.1f}% inside normal {comp.name} cavity"
                        })
                        break

                    # --- EVALUATION B: Genuine Hardware Damage (Rim Overflow / Severe Deformation) ---
                    # If the defect overflows past the component rim significantly onto the chassis
                    elif c_in_hw >= 0.40 and overlap["area1"] > (comp.area_pixels * 1.40):
                        is_true_hardware_damage = True
                        defect.relative_location = f"damaged_{comp.name}_rim"
                        audit_log.append({
                            "action": "flagged_hardware_damage",
                            "component": comp.name,
                            "containment": c_in_hw,
                            "bbox": defect.bbox,
                            "reason": f"Defect overflows {comp.name} rim, indicating physical chassis damage"
                        })
                        break

            # If not suppressed as normal hardware cavity, retain the defect
            if not is_suppressed:
                validated_defects.append(defect)

        return validated_defects, audit_log
