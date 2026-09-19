#!/usr/bin/env python3
"""
HAND & FINGER FILTERING MODULE (PHONE ROI ISOLATION)
===================================================
Eliminates false-positive defect annotations caused by human hands and fingers
holding the smartphone during multi-angle photography.

Features:
1. Multi-Color Space Skin Segmentation: Combines YCrCb and HSV color models to accurately
   isolate fingers regardless of skin tone variations and lighting conditions.
2. Phone Contour / Geometry Extractor: Detects the solid boundaries of the smartphone.
3. Inspection Mask Generator: Generates a binary mask where:
   - 255 = Valid Phone Surface (Active inspection region)
   - 0   = Human Hands / Fingers / Background (Strictly excluded from defect inspection)
4. Defect Hand-Overlap Filter: Drops any candidate defect that intersects with human fingers.
"""

import os
import cv2
import numpy as np
from typing import Tuple, List, Optional


class HandFilter:
    """
    Detects human hands/fingers and generates a clean inspection mask for smartphone bodi.
    """
    def __init__(
        self,
        skin_ycrcb_min: Tuple[int, int, int] = (0, 133, 77),
        skin_ycrcb_max: Tuple[int, int, int] = (255, 173, 127),
        skin_hsv_min: Tuple[int, int, int] = (0, 30, 60),
        skin_hsv_max: Tuple[int, int, int] = (25, 200, 255),
        morph_kernel_size: int = 9
    ):
        self.ycrcb_min = np.array(skin_ycrcb_min, dtype=np.uint8)
        self.ycrcb_max = np.array(skin_ycrcb_max, dtype=np.uint8)
        self.hsv_min = np.array(skin_hsv_min, dtype=np.uint8)
        self.hsv_max = np.array(skin_hsv_max, dtype=np.uint8)
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))

    def detect_skin_mask(self, img: np.ndarray) -> np.ndarray:
        """
        Detects skin pixels using intersection of YCrCb and HSV color spaces,
        enhanced with CLAHE illumination compensation for harsh retail/counter lighting.
        Returns: binary mask (255 = skin, 0 = non-skin)
        """
        # Luminance normalization via CLAHE on LAB color space to counteract glare/shadows
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        norm_lab = cv2.merge((cl, a, b))
        norm_bgr = cv2.cvtColor(norm_lab, cv2.COLOR_LAB2BGR)

        # 1. YCrCb space on normalized image
        ycrcb = cv2.cvtColor(norm_bgr, cv2.COLOR_BGR2YCrCb)
        mask_ycrcb = cv2.inRange(ycrcb, self.ycrcb_min, self.ycrcb_max)

        # 2. HSV space on normalized image
        hsv = cv2.cvtColor(norm_bgr, cv2.COLOR_BGR2HSV)
        mask_hsv = cv2.inRange(hsv, self.hsv_min, self.hsv_max)

        # Intersection gives high precision skin detection
        combined_skin = cv2.bitwise_and(mask_ycrcb, mask_hsv)

        # Morphological filtering to close holes in fingers/knuckles and remove salt noise
        closed = cv2.morphologyEx(combined_skin, cv2.MORPH_CLOSE, self.kernel, iterations=2)
        dilated = cv2.dilate(closed, self.kernel, iterations=2)
        return dilated

    def detect_phone_body_mask(self, img: np.ndarray, view_side: str = "front") -> np.ndarray:
        """
        Estimates the physical smartphone body contour.
        Returns: binary mask (255 = phone body, 0 = external space)
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Otsu thresholding with slight blur
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Invert if background is white
        if np.mean(gray[:20, :20]) > 180:
            thresh = cv2.bitwise_not(thresh)

        # Find largest convex contour representing the phone
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        phone_mask = np.ones((h, w), dtype=np.uint8) * 255

        if contours:
            largest_cnt = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_cnt) > (h * w * 0.25):
                hull = cv2.convexHull(largest_cnt)
                phone_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.drawContours(phone_mask, [hull], -1, 255, -1)

        return phone_mask

    def generate_inspection_mask(self, img: np.ndarray, view_side: str = "front") -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates clean inspection mask where defect search is permitted.
        Returns:
            inspection_mask: 255 = inspectable phone surface, 0 = excluded
            hand_mask: 255 = detected human fingers/skin
        """
        h, w = img.shape[:2]
        hand_mask = self.detect_skin_mask(img)
        phone_mask = self.detect_phone_body_mask(img, view_side)

        # On front view, fingers rarely cover display (usually <1% at edges)
        if view_side == "front":
            # Dilate skin mask slightly at borders only
            skin_coverage = np.mean(hand_mask > 0)
            if skin_coverage < 0.05:
                # Minimal skin detected on front, keep full display active
                pass

        # Inspection region = Phone Body MINUS Hand/Finger Pixels
        # Also dilate hand mask by a safe margin (safety buffer around fingernails/skin edges)
        safety_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        buffered_hand_mask = cv2.dilate(hand_mask, safety_kernel, iterations=1)

        # Inspection mask is where phone_mask is positive AND buffered_hand_mask is 0
        inspection_mask = cv2.bitwise_and(phone_mask, cv2.bitwise_not(buffered_hand_mask))

        # Margin crop: exclude outer 1% boundary of image to avoid border artifact edges
        border_pad_y = max(2, int(h * 0.01))
        border_pad_x = max(2, int(w * 0.01))
        inspection_mask[:border_pad_y, :] = 0
        inspection_mask[-border_pad_y:, :] = 0
        inspection_mask[:, :border_pad_x] = 0
        inspection_mask[:, -border_pad_x:] = 0

        return inspection_mask, hand_mask

    def is_defect_on_hand(self, polygon: List[Tuple[int, int]], hand_mask: np.ndarray, threshold_ratio: float = 0.20) -> bool:
        """
        Checks if a defect polygon overlaps with human fingers.
        If more than threshold_ratio of the defect's area falls within hand_mask, returns True (it's on a hand!).
        """
        if not polygon or len(polygon) < 3:
            return False

        h, w = hand_mask.shape[:2]
        defect_mask = np.zeros((h, w), dtype=np.uint8)
        pts = np.array(polygon, dtype=np.int32)
        cv2.fillPoly(defect_mask, [pts], 255)

        defect_area = np.sum(defect_mask > 0)
        if defect_area == 0:
            return False

        overlap = cv2.bitwise_and(defect_mask, hand_mask)
        overlap_area = np.sum(overlap > 0)

        ratio = overlap_area / float(defect_area)
        return ratio >= threshold_ratio


if __name__ == "__main__":
    import glob
    print("Testing HandFilter on sample smartphone images...")
    hf = HandFilter()

    sample_imgs = glob.glob("Hasil_Crop_NewFolder/*/*_bottom.jpg")[:3]
    for p in sample_imgs:
        im = cv2.imread(p)
        if im is not None:
            insp_mask, hand_mask = hf.generate_inspection_mask(im, "bottom")
            hand_pct = np.mean(hand_mask > 0) * 100
            insp_pct = np.mean(insp_mask > 0) * 100
            print(f"{os.path.basename(p)} -> Hand: {hand_pct:.1f}% | Clean Inspectable Phone: {insp_pct:.1f}%")
