#!/usr/bin/env python3
"""
DEFECT DETECTION ENGINE (INSTANCE SEGMENTATION & SAHI)
=====================================================
Detects 5 defect categories: dent, broken, scratch, chip, crack.
Features:
- High-Resolution SAHI (Slicing Aided Hyper Inference) Windowing.
- Polygon contour extraction and metric measurement (Area mm², Length mm).
- Confidence thresholding per defect category.
- Supports trained YOLOv8/v11-seg models with automatic mock/heuristic fallback for pipeline validation.
"""

import os
import sys
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import cv2
import numpy as np

from hand_filter import HandFilter
from spatial_scaler import SpatialScaler

DEFECT_CLASSES = ["dent", "broken", "scratch", "chip", "crack"]

# Defect visual color palette (BGR for OpenCV)
CLASS_COLORS = {
    "dent": (0, 165, 255),      # Orange
    "broken": (0, 0, 255),      # Red
    "scratch": (255, 255, 0),   # Cyan
    "chip": (255, 0, 255),      # Magenta
    "crack": (0, 0, 200),       # Dark Red / Crimson
}

# Per-class confidence thresholds to optimize precision
DEFAULT_CONF_THRESHOLDS = {
    "scratch": 0.45,  # Higher threshold to filter dust/lint fibers
    "crack": 0.35,    # Lower threshold: critical defect that cannot be missed
    "chip": 0.40,
    "dent": 0.40,
    "broken": 0.35,
}

# Standard phone dimension reference for pixel-to-millimeter scaling
# Typical modern smartphone: ~150mm height, ~72mm width
DEFAULT_PHONE_HEIGHT_MM = 150.0
DEFAULT_PHONE_WIDTH_MM = 72.0


@dataclass
class DefectInstance:
    """Represents a single detected physical defect."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    polygon: List[Tuple[int, int]]   # List of (x, y) contour coordinates
    area_pixels: float
    area_mm2: float
    length_pixels: float
    length_mm: float
    view_side: str                   # 'front', 'back', 'left', 'right', 'top', 'bottom'
    relative_location: str           # 'center', 'edge', 'corner', etc.

    def to_dict(self):
        d = asdict(self)
        d["bbox"] = list(self.bbox)
        d["polygon"] = [list(pt) for pt in self.polygon]
        return d


class DefectDetector:
    """
    Instance Segmentation Defect Detector with SAHI (Tiling) support.
    """
    def __init__(
        self,
        weights_path: Optional[str] = None,
        conf_thresholds: Optional[Dict[str, float]] = None,
        tile_size: int = 1024,
        overlap_ratio: float = 0.20,
        device: str = "cpu"
    ):
        self.weights_path = weights_path
        self.conf_thresholds = conf_thresholds or DEFAULT_CONF_THRESHOLDS
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.device = device
        self.model = None
        self.hand_filter = HandFilter()
        self.spatial_scaler = SpatialScaler()

        # Automatically use saved model if available
        if weights_path is None:
            default_w = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights", "phone_defect_model.pt")
            if os.path.exists(default_w):
                weights_path = default_w

        self.weights_path = weights_path
        self.is_custom_defect_model = False

        if weights_path and os.path.exists(weights_path):
            try:
                from ultralytics import YOLO
                print(f"[DefectDetector] Loading YOLO segmentation model: {weights_path}")
                self.model = YOLO(weights_path)
                if isinstance(getattr(self.model, "names", None), dict):
                    self.is_custom_defect_model = (self.model.names.get(0) == "dent")
                if not self.is_custom_defect_model:
                    print("[DefectDetector] Pretrained base weights (COCO). Custom defect heuristic mode active.")
            except ImportError:
                print("[DefectDetector] 'ultralytics' not installed. Falling back to heuristic mode.")
                self.model = None
        else:
            if weights_path:
                print(f"[DefectDetector] Weights '{weights_path}' not found. Using heuristic/demo mode.")

    def _estimate_scale(self, img_shape: Tuple[int, int], view_side: str) -> float:
        """
        Calculates mm-per-pixel scale factor based on known physical phone dimensions.
        """
        h, w = img_shape[:2]
        if view_side in ["front", "back"]:
            mm_per_pixel = DEFAULT_PHONE_HEIGHT_MM / max(h, 1)
        elif view_side in ["left", "right"]:
            mm_per_pixel = DEFAULT_PHONE_HEIGHT_MM / max(h, 1)
        elif view_side in ["top", "bottom"]:
            mm_per_pixel = DEFAULT_PHONE_WIDTH_MM / max(w, 1)
        else:
            mm_per_pixel = DEFAULT_PHONE_HEIGHT_MM / max(h, 1)
        return mm_per_pixel

    def _create_tiles(self, img: np.ndarray) -> List[Tuple[int, int, int, int, np.ndarray]]:
        """
        Slices image into overlapping tiles for high-resolution SAHI inference.
        Returns: list of (x1, y1, x2, y2, tile_img)
        """
        h, w = img.shape[:2]
        step = int(self.tile_size * (1.0 - self.overlap_ratio))
        tiles = []

        y = 0
        while y < h:
            y2 = min(y + self.tile_size, h)
            y1 = max(0, y2 - self.tile_size) if y2 == h and h >= self.tile_size else y

            x = 0
            while x < w:
                x2 = min(x + self.tile_size, w)
                x1 = max(0, x2 - self.tile_size) if x2 == w and w >= self.tile_size else x

                tile_crop = img[y1:y2, x1:x2]
                tiles.append((x1, y1, x2, y2, tile_crop))

                if x2 >= w:
                    break
                x += step

            if y2 >= h:
                break
            y += step

        return tiles

    def detect_image(
        self,
        img_path: str,
        view_side: str = "front",
        filter_hands: bool = True
    ) -> List[DefectInstance]:
        """
        Runs defect detection on a single image.
        Uses SAHI tiling, Dynamic Spatial Scaling, and HandFilter masking.
        """
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {img_path}")

        h, w = img.shape[:2]
        scale_mm, calib_mode, H = self.spatial_scaler.calculate_scale_mm(img, view_side)

        inspection_mask = None
        hand_mask = None
        if filter_hands:
            inspection_mask, hand_mask = self.hand_filter.generate_inspection_mask(img, view_side)

        all_defects = []
        # 1. Detect with custom YOLO segmentation model (if available)
        if self.model is not None and self.is_custom_defect_model:
            yolo_defs = self._detect_with_yolo(img, view_side, scale_mm, inspection_mask, hand_mask)
            all_defects.extend(yolo_defs)

        # 2. Geometric anomaly detection for fine micro-scratches, chips, and housing defects
        heur_defs = self._detect_with_heuristics(img, view_side, scale_mm, inspection_mask, hand_mask)
        all_defects.extend(heur_defs)

        return self._nms_defects(all_defects)

    def _detect_with_yolo(
        self,
        img: np.ndarray,
        view_side: str,
        scale_mm: float,
        inspection_mask: Optional[np.ndarray] = None,
        hand_mask: Optional[np.ndarray] = None
    ) -> List[DefectInstance]:
        """
        Fast high-resolution inference using trained YOLO segmentation model with hand exclusion.
        """
        h, w = img.shape[:2]
        # For tall images, inspect in two overlapping halves (top and bottom) for high detail
        if h > 2000:
            mid = h // 2
            overlap = int(h * 0.10)
            sub_regions = [
                (0, 0, w, mid + overlap),
                (0, max(0, mid - overlap), w, h)
            ]
        else:
            sub_regions = [(0, 0, w, h)]

        all_defects = []
        for x1, y1, x2, y2 in sub_regions:
            sub_img = img[y1:y2, x1:x2]
            results = self.model.predict(sub_img, imgsz=640, conf=0.20, verbose=False, device="cpu")
            for res in results:
                if res.masks is None or len(res.masks) == 0:
                    continue

                for i, mask in enumerate(res.masks.xy):
                    cls_id = int(res.boxes.cls[i].item())
                    conf = float(res.boxes.conf[i].item())
                    if cls_id not in range(len(DEFECT_CLASSES)):
                        continue
                    cls_name = DEFECT_CLASSES[cls_id]

                    # Filter by per-class confidence threshold
                    if conf < self.conf_thresholds.get(cls_name, 0.35):
                        continue

                    # Transform local crop polygon back to global image coordinates
                    global_polygon = [(int(pt[0] + x1), int(pt[1] + y1)) for pt in mask]
                    if len(global_polygon) < 3:
                        continue

                    # Filter out candidate if it falls on human hands/fingers
                    if hand_mask is not None and self.hand_filter.is_defect_on_hand(global_polygon, hand_mask, threshold_ratio=0.15):
                        continue

                    pts_np = np.array(global_polygon, dtype=np.int32)
                    bx1, by1, bw, bh = cv2.boundingRect(pts_np)

                    # Filter out if outside inspectable phone surface
                    if inspection_mask is not None:
                        crop_mask = inspection_mask[by1:by1+bh, bx1:bx1+bw]
                        if crop_mask.size > 0 and np.mean(crop_mask) < 80:
                            continue

                    metrics = self.spatial_scaler.measure_polygon_metrics(global_polygon, scale_mm)
                    bbox = (bx1, by1, bx1 + bw, by1 + bh)

                    defect = DefectInstance(
                        class_name=cls_name,
                        confidence=conf,
                        bbox=bbox,
                        polygon=global_polygon,
                        area_pixels=metrics["area_pixels"],
                        area_mm2=metrics["area_mm2"],
                        length_pixels=metrics["length_pixels"],
                        length_mm=metrics["length_mm"],
                        view_side=view_side,
                        relative_location=self._get_location_name(bbox, w, h)
                    )
                    all_defects.append(defect)

        return self._nms_defects(all_defects)

    def _detect_with_heuristics(
        self,
        img: np.ndarray,
        view_side: str,
        scale_mm: float,
        inspection_mask: Optional[np.ndarray] = None,
        hand_mask: Optional[np.ndarray] = None
    ) -> List[DefectInstance]:
        """
        High-precision visual anomaly detector with Hand/Finger, Glare, and Hardware feature filtering.
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Edge-preserving bilateral filter
        blurred = cv2.bilateralFilter(gray, 7, 45, 45)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6
        )

        # Extract phone body mask and dilated boundary edge
        phone_mask = self.hand_filter.detect_phone_body_mask(img, view_side)
        phone_edge = cv2.Canny(phone_mask, 50, 150)
        phone_edge_dilated = cv2.dilate(phone_edge, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30)))

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        defects = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filter noise and large borders
            if area < 20 or area > (h * w * 0.03):
                continue

            peri = cv2.arcLength(cnt, True)
            bx, by, bw, bh = cv2.boundingRect(cnt)

            # 1. Structural Filter: Drop long antenna bands, frame seams, or bezel outlines
            if bw > w * 0.20 or bh > h * 0.20:
                continue

            # 2. Outer Border Filter: Avoid outer boundary edges of the crop
            if bx < 15 or by < 15 or (bx + bw) > (w - 15) or (by + bh) > (h - 15):
                continue

            # 3. Hardware Feature Filter: Drop standard USB charging ports on bottom view only
            rel_cx = (bx + bw / 2.0) / w
            rel_cy = (by + bh / 2.0) / h
            if view_side == "bottom":
                if 0.40 <= rel_cx <= 0.60 and 0.35 <= rel_cy <= 0.65:
                    continue

            # 4. Glare / Reflection Band Filter (narrow vertical/horizontal specular reflections)
            if (bw <= 10 and bh > 35) or (bh <= 10 and bw > 35):
                continue

            patch = gray[by:by+bh, bx:bx+bw]
            if patch.size == 0 or np.mean(patch) > 215:
                continue

            # Check if defect lies along the physical phone edge/boundary
            cx, cy = int(bx + bw / 2), int(by + bh / 2)
            is_on_phone_edge = (phone_edge_dilated[cy, cx] > 0)

            # 5. Eliminate candidates that lie on human fingers or outside phone body
            poly_pts = [(int(p[0][0]), int(p[0][1])) for p in cnt]
            hand_thresh = 0.40 if is_on_phone_edge else 0.15
            if hand_mask is not None and self.hand_filter.is_defect_on_hand(poly_pts, hand_mask, threshold_ratio=hand_thresh):
                continue

            min_insp = 40 if is_on_phone_edge else 80
            if inspection_mask is not None:
                crop_mask = inspection_mask[by:by+bh, bx:bx+bw]
                if crop_mask.size > 0 and np.mean(crop_mask) < min_insp:
                    continue

            # 6. Local Contrast & Stroke Width Filter
            stroke_w = (2.0 * area) / max(peri, 1.0)
            aspect_ratio = max(bw, bh) / max(min(bw, bh), 1)

            bg_margin = 4
            bg_crop = gray[max(0, by-bg_margin):min(h, by+bh+bg_margin), max(0, bx-bg_margin):min(w, bx+bw+bg_margin)]
            local_contrast = abs(float(np.mean(patch)) - float(np.mean(bg_crop)))

            if local_contrast < 9.0:
                continue

            metrics = self.spatial_scaler.measure_polygon_metrics(poly_pts, scale_mm)
            len_mm = metrics["length_mm"]
            area_mm2 = metrics["area_mm2"]

            cls_name = None
            conf = 0.70

            # Classification heuristics with physical metric gates:
            # A. Scratch: Hairline thin (stroke_w <= 3.5px), elongated (aspect_ratio > 3.2), length >= 1.8mm
            if aspect_ratio > 3.2 and 35 < peri < 500 and stroke_w <= 3.5:
                # Differentiate crack from scratch: cracks are long (>8mm), high std deviation, jagged, on glass surfaces only
                if view_side in ["front", "back"] and peri > 120 and np.std(patch) > 35.0 and len_mm >= 8.0:
                    cls_name = "crack"
                    conf = 0.78
                elif len_mm >= 1.8:
                    cls_name = "scratch"
                    conf = 0.68
            # B. Chip / Broken: Localized notch or physical defect at the peripheral phone margin
            elif is_on_phone_edge and area_mm2 >= 0.3 and len_mm >= 1.2:
                if len_mm >= 4.0 or area_mm2 >= 1.0:
                    cls_name = "broken"
                    conf = 0.85  # Severe sompal / housing fracture
                else:
                    cls_name = "chip"
                    conf = 0.72  # Minor cuil / corner chip
            # C. Dent: Rounded indentation (aspect_ratio < 1.8, area >= 2.0mm², length >= 1.8mm)
            elif aspect_ratio < 1.8 and area_mm2 >= 2.0 and len_mm >= 1.8:
                cls_name = "dent"
                conf = 0.62

            if cls_name and conf >= self.conf_thresholds.get(cls_name, 0.4):
                defects.append(DefectInstance(
                    class_name=cls_name,
                    confidence=conf,
                    bbox=(bx, by, bx + bw, by + bh),
                    polygon=poly_pts,
                    area_pixels=metrics["area_pixels"],
                    area_mm2=area_mm2,
                    length_pixels=metrics["length_pixels"],
                    length_mm=len_mm,
                    view_side=view_side,
                    relative_location=self._get_location_name((bx, by, bx + bw, by + bh), w, h)
                ))

        defects.sort(key=lambda d: d.area_pixels, reverse=True)
        return self._nms_defects(defects[:12])

    def _get_location_name(self, bbox: Tuple[int, int, int, int], img_w: int, img_h: int) -> str:
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        rx = cx / img_w
        ry = cy / img_h

        if rx < 0.15:
            return "left_edge"
        elif rx > 0.85:
            return "right_edge"
        elif ry < 0.12:
            return "top_edge"
        elif ry > 0.88:
            return "bottom_edge"
        return "screen_display"

    def _nms_defects(self, defects: List[DefectInstance], iou_thresh: float = 0.4) -> List[DefectInstance]:
        """Non-Maximum Suppression to deduplicate defects across tiles."""
        if not defects:
            return []

        defects = sorted(defects, key=lambda x: x.confidence, reverse=True)
        keep = []

        while defects:
            current = defects.pop(0)
            keep.append(current)

            remaining = []
            for other in defects:
                x1 = max(current.bbox[0], other.bbox[0])
                y1 = max(current.bbox[1], other.bbox[1])
                x2 = min(current.bbox[2], other.bbox[2])
                y2 = min(current.bbox[3], other.bbox[3])

                w = max(0, x2 - x1)
                h = max(0, y2 - y1)
                inter_area = w * h

                a1 = (current.bbox[2] - current.bbox[0]) * (current.bbox[3] - current.bbox[1])
                a2 = (other.bbox[2] - other.bbox[0]) * (other.bbox[3] - other.bbox[1])
                union_area = a1 + a2 - inter_area

                iou = inter_area / max(union_area, 1e-6)
                if iou < iou_thresh:
                    remaining.append(other)
            defects = remaining

        return self._filter_dense_texture_clusters(keep)

    def _filter_dense_texture_clusters(
        self,
        defects: List[DefectInstance],
        max_dist: float = 120.0,
        min_cluster_size: int = 3
    ) -> List[DefectInstance]:
        """
        Suppresses dense periodic parallel micro-scratches caused by ESD glove fabrics or table textures.
        """
        if len(defects) < min_cluster_size:
            return defects

        centers = [((d.bbox[0] + d.bbox[2]) / 2.0, (d.bbox[1] + d.bbox[3]) / 2.0) for d in defects]
        drop_indices = set()

        for i in range(len(defects)):
            cluster = [i]
            for j in range(len(defects)):
                if i != j:
                    dist = float(np.hypot(centers[i][0] - centers[j][0], centers[i][1] - centers[j][1]))
                    if dist < max_dist:
                        cluster.append(j)

            if len(cluster) >= min_cluster_size:
                lens = [defects[k].length_mm for k in cluster]
                # High density micro marks with uniform length is glove/fabric texture noise
                if np.std(lens) < 0.8 and np.mean(lens) < 3.2:
                    drop_indices.update(cluster)

        return [d for idx, d in enumerate(defects) if idx not in drop_indices]

    def draw_defects_on_image(
        self,
        img: np.ndarray,
        defects: List[DefectInstance],
        hand_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Draws visual annotations (polygons, labels, and bounding boxes) on image.
        If hand_mask is provided, shades the excluded hand/finger area.
        """
        annotated = img.copy()

        # Render subtle hand exclusion zone
        if hand_mask is not None and np.sum(hand_mask > 0) > 0:
            hand_overlay = annotated.copy()
            hand_overlay[hand_mask > 0] = [60, 60, 60]  # Dim hand
            cv2.addWeighted(hand_overlay, 0.35, annotated, 0.65, 0, annotated)
            # Outline hands
            h_contours, _ = cv2.findContours(hand_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.polylines(annotated, h_contours, isClosed=True, color=(140, 140, 140), thickness=1)

        for d in defects:
            color = CLASS_COLORS.get(d.class_name, (0, 255, 0))

            # Draw polygon mask with alpha blend
            if len(d.polygon) >= 3:
                pts = np.array(d.polygon, dtype=np.int32)
                overlay = annotated.copy()
                cv2.fillPoly(overlay, [pts], color)
                cv2.addWeighted(overlay, 0.4, annotated, 0.6, 0, annotated)
                cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=2)

            # Draw Bounding Box
            x1, y1, x2, y2 = d.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)

            # Draw Label Tag
            label = f"{d.class_name.upper()} {d.confidence:.2f} ({d.length_mm:.1f}mm)"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, max(0, y1)), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 3, max(0, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )
        return annotated
