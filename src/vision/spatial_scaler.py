#!/usr/bin/env python3
"""
DYNAMIC SPATIAL SCALER & HOMOGRAPHY MODULE
===========================================
Solves the static DPI limitations by providing:
1. ArUco Fiducial Marker Detection (DICT_4X4_50 / DICT_5X5_100).
2. Homography Matrix Transformation: Rectifies perspective parallax distortion.
3. Dynamic Device Contour Scaling: Adaptively computes mm-per-pixel ratio from
   the detected phone extremities when physical markers are absent.
4. Polygon Metric Measurement: Sub-pixel surface area (mm²) using Green's theorem /
   Shoelace formula, avoiding bounding-box overestimation.
"""

import math
from typing import Tuple, List, Optional, Dict
import cv2
import numpy as np

# Standard smartphone reference dimensions (mm)
DEFAULT_PHONE_HEIGHT_MM = 150.0
DEFAULT_PHONE_WIDTH_MM = 72.0
DEFAULT_PHONE_THICKNESS_MM = 8.5
DEFAULT_ARUCO_SIZE_MM = 20.0  # Standard 20mm x 20mm fiducial marker


class SpatialScaler:
    """
    Dual-mode spatial calibrator:
    - Primary: ArUco Fiducial Marker + Homography Matrix.
    - Fallback: Dynamic Device Contour Scaling.
    """
    def __init__(
        self,
        aruco_size_mm: float = DEFAULT_ARUCO_SIZE_MM,
        phone_height_mm: float = DEFAULT_PHONE_HEIGHT_MM,
        phone_width_mm: float = DEFAULT_PHONE_WIDTH_MM,
        phone_thickness_mm: float = DEFAULT_PHONE_THICKNESS_MM,
        aruco_dict_id: int = cv2.aruco.DICT_4X4_50
    ):
        self.aruco_size_mm = aruco_size_mm
        self.phone_height_mm = phone_height_mm
        self.phone_width_mm = phone_width_mm
        self.phone_thickness_mm = phone_thickness_mm

        # Initialize ArUco detector (compatible with OpenCV 4.7+ and legacy)
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_id)
        if hasattr(cv2.aruco, "ArucoDetector"):
            params = cv2.aruco.DetectorParameters()
            self.aruco_detector = cv2.aruco.ArucoDetector(self.aruco_dict, params)
            self._use_new_aruco = True
        else:
            self.aruco_params = cv2.aruco.DetectorParameters_create()
            self._use_new_aruco = False

    def detect_aruco(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Detects ArUco fiducial markers in the image.
        Returns: (corners, ids)
        """
        if self._use_new_aruco:
            corners, ids, _ = self.aruco_detector.detectMarkers(img)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(img, self.aruco_dict, parameters=self.aruco_params)

        if ids is not None and len(ids) > 0:
            return corners, ids
        return None, None

    def compute_homography_from_aruco(
        self,
        corners: np.ndarray,
        marker_size_mm: Optional[float] = None
    ) -> Optional[np.ndarray]:
        """
        Computes the 3x3 homography matrix that maps image pixel coordinates
        to rectified metric coordinates (in mm) based on the ArUco marker.
        """
        size_mm = marker_size_mm or self.aruco_size_mm
        if corners is None or len(corners) == 0:
            return None

        pts_src = corners[0].reshape(4, 2).astype(np.float32)

        pts_dst = np.array([
            [0.0, 0.0],
            [size_mm, 0.0],
            [size_mm, size_mm],
            [0.0, size_mm]
        ], dtype=np.float32)

        H, _ = cv2.findHomography(pts_src, pts_dst)
        return H

    def detect_phone_contour(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Extracts the physical outer contour of the smartphone body.
        Uses adaptive multi-scale edge and thresholding.
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Otsu threshold
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Ensure phone body is foreground (white)
        corners = [gray[0:15, 0:15], gray[0:15, -15:], gray[-15:, 0:15], gray[-15:, -15:]]
        bg_brightness = np.mean([np.mean(c) for c in corners])
        if bg_brightness > 160:
            thresh = cv2.bitwise_not(thresh)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        min_area = h * w * 0.15
        valid = [c for c in contours if cv2.contourArea(c) > min_area]
        if not valid:
            return None

        largest = max(valid, key=cv2.contourArea)
        return cv2.convexHull(largest)

    def calculate_scale_mm(
        self,
        img: np.ndarray,
        view_side: str = "front"
    ) -> Tuple[float, str, Optional[np.ndarray]]:
        """
        Calculates the dynamic mm-per-pixel scale factor for the given image.
        Returns:
            scale_mm_per_px: float
            calibration_mode: str ("ARUCO_HOMOGRAPHY", "DYNAMIC_CONTOUR", "FRAME_FALLBACK")
            homography_matrix: Optional[np.ndarray]
        """
        h, w = img.shape[:2]

        # 1. Check for ArUco Marker
        corners, ids = self.detect_aruco(img)
        if corners is not None and len(corners) > 0:
            pts = corners[0].reshape(4, 2)
            edge_lengths = [
                np.linalg.norm(pts[i] - pts[(i + 1) % 4]) for i in range(4)
            ]
            mean_edge_px = float(np.mean(edge_lengths))
            if mean_edge_px > 5.0:
                scale = self.aruco_size_mm / mean_edge_px
                H = self.compute_homography_from_aruco(corners)
                return scale, "ARUCO_HOMOGRAPHY", H

        # 2. Dynamic Contour Scaling
        phone_cnt = self.detect_phone_contour(img)
        if phone_cnt is not None:
            rect = cv2.minAreaRect(phone_cnt)
            (cx, cy), (dim1, dim2), angle = rect
            cnt_length_px = max(dim1, dim2)

            if cnt_length_px > 50:
                if view_side in ["front", "back", "left", "right"]:
                    scale = self.phone_height_mm / cnt_length_px
                elif view_side in ["top", "bottom"]:
                    scale = self.phone_width_mm / cnt_length_px
                else:
                    scale = self.phone_height_mm / cnt_length_px

                return float(scale), "DYNAMIC_CONTOUR", None

        # 3. Fallback: Frame Reference Dimension
        if view_side in ["front", "back", "left", "right"]:
            scale = self.phone_height_mm / max(h, 1)
        elif view_side in ["top", "bottom"]:
            scale = self.phone_width_mm / max(w, 1)
        else:
            scale = self.phone_height_mm / max(h, 1)

        return float(scale), "FRAME_FALLBACK", None

    def measure_polygon_metrics(
        self,
        polygon_coords: List[Tuple[int, int]],
        scale_mm: float
    ) -> Dict[str, float]:
        """
        Calculates high-precision sub-millimeter metrics for a defect polygon mask:
        - area_pixels & area_mm² (Green's theorem / Shoelace contourArea)
        - length_pixels & length_mm (Half perimeter / principal axis approximation)
        - equivalent_diameter_mm
        """
        pts_np = np.array(polygon_coords, dtype=np.int32)
        if len(pts_np) < 3:
            return {
                "area_pixels": 0.0,
                "area_mm2": 0.0,
                "length_pixels": 0.0,
                "length_mm": 0.0,
                "equivalent_diameter_mm": 0.0
            }

        area_px = float(cv2.contourArea(pts_np))
        perimeter_px = float(cv2.arcLength(pts_np, closed=True))
        area_mm2 = area_px * (scale_mm ** 2)

        rect = cv2.minAreaRect(pts_np)
        major_axis_px = float(max(rect[1])) if max(rect[1]) > 0 else (perimeter_px / 2.0)
        length_mm = major_axis_px * scale_mm
        eq_diam_mm = math.sqrt(max(0.0, 4.0 * area_mm2 / math.pi))

        return {
            "area_pixels": round(area_px, 2),
            "area_mm2": round(area_mm2, 4),
            "length_pixels": round(major_axis_px, 2),
            "length_mm": round(length_mm, 3),
            "perimeter_pixels": round(perimeter_px, 2),
            "equivalent_diameter_mm": round(eq_diam_mm, 3)
        }


if __name__ == "__main__":
    scaler = SpatialScaler()
    print("SpatialScaler module loaded successfully.")
