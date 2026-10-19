#!/usr/bin/env python3
"""
Surface Area Density & Structural Guardrail Evaluator (V8 Valuation Engine)
==========================================================================
Pusat Gadai Indonesia (PGI) — Automated Cosmetic Defect Valuation

Solves:
1. The Grade C Ambiguity Collapse:
   Differentiates Grade B (isolated scratches) from Grade C (diffuse abrasions)
   using the Surface Area Ratio (SAR) metric across multi-view perspectives.
2. Hard Damage Under-Penalization:
   Enforces a zero-tolerance Veto rule for Grade D structural damage.
"""

from typing import Dict, List, Any, Optional

# V7 / V8 Class Taxonomy
# 0: scratch, 1: chip, 2: dent, 3: hard_damage
CLASS_NAMES = {
    0: "scratch",
    1: "chip",
    2: "dent",
    3: "hard_damage"
}

class SurfaceDensityEvaluator:
    def __init__(
        self,
        sar_grade_c_threshold: float = 3.0,     # >= 3.0% surface scratch ratio indicates Grade C
        min_c_views_required: int = 2,           # Must affect at least 2 views to be Grade C
        hard_damage_veto_conf: float = 0.40,     # Confidence threshold to trigger immediate Grade D veto
        chip_grade_c_threshold: int = 4          # >= 4 heavy chips trigger Grade C
    ):
        self.sar_c_thresh = sar_grade_c_threshold
        self.min_c_views = min_c_views_required
        self.hard_damage_conf = hard_damage_veto_conf
        self.chip_c_thresh = chip_grade_c_threshold

    def compute_view_sar(self, detections: List[Dict[str, Any]], img_w: int = 800, img_h: int = 800) -> float:
        """
        Computes the Surface Area Ratio (SAR) of scratch bboxes relative to image area.
        Bbox format expected: [x1, y1, x2, y2] or normalized [x_c, y_c, w, h].
        """
        total_area = float(img_w * img_h)
        if total_area <= 0:
            return 0.0

        scratch_area = 0.0
        for d in detections:
            cls_id = d.get("class_id", -1)
            # Only consider scratch (0)
            if cls_id == 0:
                bbox = d.get("bbox", [])
                if len(bbox) == 4:
                    # Normalized [xc, yc, w, h]
                    if max(bbox) <= 1.0:
                        w = bbox[2] * img_w
                        h = bbox[3] * img_h
                    else: # Absolute [x1, y1, x2, y2]
                        w = max(0.0, float(bbox[2] - bbox[0]))
                        h = max(0.0, float(bbox[3] - bbox[1]))
                    scratch_area += (w * h)

        sar = (scratch_area / total_area) * 100.0
        return round(sar, 3)

    def evaluate_unit(
        self,
        multi_view_detections: Dict[str, List[Dict[str, Any]]],
        screen_cracked: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates full multi-view unit detections (front, back, left, right, top, bottom)
        and outputs the calculated cosmetic Grade (A, B, C, D) with full explainability.
        """
        view_sar_map = {}
        total_defects = 0
        counts_by_class = {0: 0, 1: 0, 2: 0, 3: 0}
        hard_damage_instances = []

        # 1. Process all views
        for view, dets in multi_view_detections.items():
            sar = self.compute_view_sar(dets)
            view_sar_map[view] = sar

            for d in dets:
                cid = d.get("class_id", -1)
                conf = float(d.get("confidence", 0.0))
                if cid in counts_by_class:
                    counts_by_class[cid] += 1
                    total_defects += 1
                if cid == 3 and conf >= self.hard_damage_conf:
                    hard_damage_instances.append({
                        "view": view,
                        "confidence": conf,
                        "bbox": d.get("bbox")
                    })

        # 2. Check Grade D Veto Guardrail (Structural / Glass breach)
        is_hard_damage_veto = len(hard_damage_instances) > 0 or screen_cracked
        if is_hard_damage_veto:
            reason = "Layar retak / pecah terdeteksi" if screen_cracked else f"Kerusakan struktural berat (Hard Damage) pada sisi {hard_damage_instances[0]['view']} (Conf: {hard_damage_instances[0]['confidence']:.2f})"
            return {
                "final_grade": "Grade D",
                "confidence_score": 0.95,
                "is_veto_applied": True,
                "veto_reason": reason,
                "metrics": {
                    "total_defects": total_defects,
                    "class_counts": {CLASS_NAMES[k]: v for k, v in counts_by_class.items()},
                    "view_sar_map": view_sar_map,
                    "avg_sar": round(sum(view_sar_map.values()) / max(1, len(view_sar_map)), 3),
                    "hard_damage_count": len(hard_damage_instances)
                }
            }

        # 3. Check Grade C Condition (Diffuse Scratches or Heavy Chipping/Dents)
        views_exceeding_sar = [v for v, sar in view_sar_map.items() if sar >= self.sar_c_thresh]
        total_chips = counts_by_class.get(1, 0)
        total_dents = counts_by_class.get(2, 0)
        total_scratches = counts_by_class.get(0, 0)

        is_grade_c = (
            len(views_exceeding_sar) >= self.min_c_views or
            total_chips >= self.chip_c_thresh or
            total_dents >= 2 or
            total_scratches >= 8
        )

        if is_grade_c:
            c_reasons = []
            if len(views_exceeding_sar) >= self.min_c_views:
                c_reasons.append(f"Densitas baret tinggi (SAR >= {self.sar_c_thresh}%) pada {len(views_exceeding_sar)} sisi ({', '.join(views_exceeding_sar)})")
            if total_chips >= self.chip_c_thresh:
                c_reasons.append(f"Titik sompal meluas ({total_chips} titik)")
            if total_dents >= 2:
                c_reasons.append(f"Penyok frame ({total_dents} titik)")
            if total_scratches >= 8:
                c_reasons.append(f"Akumulasi goresan merata ({total_scratches} goresan)")

            return {
                "final_grade": "Grade C",
                "confidence_score": 0.88,
                "is_veto_applied": False,
                "veto_reason": None,
                "explanation": " | ".join(c_reasons),
                "metrics": {
                    "total_defects": total_defects,
                    "class_counts": {CLASS_NAMES[k]: v for k, v in counts_by_class.items()},
                    "view_sar_map": view_sar_map,
                    "avg_sar": round(sum(view_sar_map.values()) / max(1, len(view_sar_map)), 3)
                }
            }

        # 4. Check Grade B Condition (Normal Wear)
        is_grade_b = total_defects > 0 or max(view_sar_map.values(), default=0.0) >= 0.5
        if is_grade_b:
            return {
                "final_grade": "Grade B",
                "confidence_score": 0.90,
                "is_veto_applied": False,
                "veto_reason": None,
                "explanation": f"Baret pemakaian wajar ({total_scratches} goresan, {total_chips} sompal minor)",
                "metrics": {
                    "total_defects": total_defects,
                    "class_counts": {CLASS_NAMES[k]: v for k, v in counts_by_class.items()},
                    "view_sar_map": view_sar_map,
                    "avg_sar": round(sum(view_sar_map.values()) / max(1, len(view_sar_map)), 3)
                }
            }

        # 5. Grade A Condition (Mint / Like New)
        return {
            "final_grade": "Grade A",
            "confidence_score": 0.96,
            "is_veto_applied": False,
            "veto_reason": None,
            "explanation": "Bodi mulus sempurna tanpa cacat signifikan",
            "metrics": {
                "total_defects": 0,
                "class_counts": {CLASS_NAMES[k]: 0 for k in counts_by_class},
                "view_sar_map": view_sar_map,
                "avg_sar": 0.0
            }
        }

if __name__ == "__main__":
    evaluator = SurfaceDensityEvaluator()

    # Test unit with diffuse scratches (Grade C test)
    mock_grade_c_unit = {
        "back": [{"class_id": 0, "confidence": 0.72, "bbox": [0.1, 0.1, 0.3, 0.3]}],
        "left": [{"class_id": 0, "confidence": 0.65, "bbox": [0.2, 0.2, 0.4, 0.4]}],
        "right": [{"class_id": 0, "confidence": 0.60, "bbox": [0.05, 0.05, 0.1, 0.1]}],
    }

    res = evaluator.evaluate_unit(mock_grade_c_unit)
    print("Grade C Test Result:", res["final_grade"])
    print("Explanation         :", res.get("explanation"))
    assert res["final_grade"] == "Grade C", "Grade C evaluation failed!"

    # Test unit with hard damage (Grade D test)
    mock_grade_d_unit = {
        "front": [{"class_id": 3, "confidence": 0.85, "bbox": [0.3, 0.3, 0.7, 0.7]}],
    }
    res_d = evaluator.evaluate_unit(mock_grade_d_unit)
    print("\nGrade D Test Result:", res_d["final_grade"])
    print("Veto Reason         :", res_d.get("veto_reason"))
    assert res_d["final_grade"] == "Grade D", "Grade D veto failed!"
    print("\n[OK] All unit tests in SurfaceDensityEvaluator passed successfully!")
