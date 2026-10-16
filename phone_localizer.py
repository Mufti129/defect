#!/usr/bin/env python3
"""
STAGE 1: PHONE BODY LOCALIZER & AUTO-CROPPER
=============================================
Detects the exact physical bounding box of the smartphone body,
rectifies camera tilt rotation, auto-crops the phone with proportional margin,
and eliminates background clutter (tables, trousers/pants, floor, boxes).
"""

import os
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional


class PhoneBodyLocalizer:
    def __init__(self, yolo_model_path: Optional[str] = None):
        self.yolo_model = None
        self.yolo_path = None

        candidate_paths = [
            yolo_model_path,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights", "model_detect_body_hp.pt"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_detect_body_hp.pt"),
            "/Users/macbookair/Documents/Project Defect Detections/model_detect_body_hp.pt"
        ]
        for p in candidate_paths:
            if p and os.path.exists(p):
                try:
                    from ultralytics import YOLO
                    self.yolo_model = YOLO(p)
                    self.yolo_path = p
                    break
                except Exception:
                    pass

        self.hand_filter = None
        try:
            from hand_filter import HandFilter
            self.hand_filter = HandFilter()
        except Exception:
            pass

    def detect_angle(self, img: np.ndarray, side: str) -> float:
        """
        Detects tilt angle (in degrees) of the phone edge using centrality-weighted Hough lines.
        """
        h, w = img.shape[:2]
        scale = 0.25
        small = cv2.resize(img, (0, 0), fx=scale, fy=scale)
        sh, sw = small.shape[:2]
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 35, 110)

        if side in ['bottom', 'top']:
            roi_y1 = int(sh * 0.25)
            roi_y2 = int(sh * 0.75)
            roi = edges[roi_y1:roi_y2, :]
            lines = cv2.HoughLinesP(roi, 1, np.pi / 180, threshold=25,
                                    minLineLength=int(sw * 0.06), maxLineGap=15)
            is_horiz = True
        else:
            roi_x1 = int(sw * 0.25)
            roi_x2 = int(sw * 0.75)
            roi = edges[:, roi_x1:roi_x2]
            lines = cv2.HoughLinesP(roi, 1, np.pi / 180, threshold=25,
                                    minLineLength=int(sh * 0.08), maxLineGap=20)
            is_horiz = False

        if lines is None:
            return 0.0

        lines = lines.reshape(-1, 4)
        angles = []
        weights = []
        for x1, y1, x2, y2 in lines:
            dx = x2 - x1
            dy = y2 - y1
            length = np.hypot(dx, dy)
            ang = np.degrees(np.arctan2(dy, dx))
            if is_horiz:
                dev = (ang + 90) % 180 - 90
            else:
                dev = ang % 180 - 90
            if abs(dev) < 25:
                angles.append(dev)
                weights.append(length)

        if not angles:
            return 0.0

        angles = np.array(angles)
        weights = np.array(weights)

        # Robust peak mode via length^2 weighted histogram (bin size 1.5 deg)
        bins = np.arange(-25, 26, 1.5)
        hist, bin_edges = np.histogram(angles, bins=bins, weights=weights**2)
        peak_bin = np.argmax(hist)
        peak_center = (bin_edges[peak_bin] + bin_edges[peak_bin + 1]) / 2
        inliers = np.abs(angles - peak_center) <= 3.0

        if np.any(inliers):
            robust_ang = float(np.clip(np.average(angles[inliers], weights=weights[inliers]**2), -25, 25))
            return robust_ang
        return float(np.clip(np.average(angles, weights=weights), -25, 25))

    def rotate_image(self, img: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotates image around center with border color matching background corners.
        """
        if abs(angle) < 0.2:
            return img
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        cw = max(20, int(w * 0.03))
        ch = max(20, int(h * 0.03))
        corners = np.vstack([
            img[:ch, :cw],
            img[:ch, -cw:],
            img[-ch:, :cw],
            img[-ch:, -cw:]
        ])
        bg_color = [int(c) for c in np.median(corners, axis=(0, 1))]
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=bg_color
        )
        return rotated

    def crop_focused_phone(self, rotated_img: np.ndarray, side: str) -> Tuple[Tuple[int, int, int, int], str]:
        """
        Detects physical phone extremities using continuous edge scanning,
        ensuring the entire phone is preserved with proportional breathing room.
        Returns: ((bx, by, cw, ch), confidence_str)
        """
        h, w = rotated_img.shape[:2]
        scale = 0.25
        small = cv2.resize(rotated_img, (0, 0), fx=scale, fy=scale)
        sh, sw = small.shape[:2]
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)

        confidence = "HIGH_CONFIDENCE"

        if side in ['bottom', 'top']:
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 25,
                                    minLineLength=int(sw * 0.06), maxLineGap=15)
            if lines is None:
                lines = np.array([])
            else:
                lines = lines.reshape(-1, 4)

            # Filter horizontal lines in central vertical band (0.20 to 0.80) with centrality weighting
            h_lines = []
            for x1, y1, x2, y2 in lines:
                dx, dy = abs(x2 - x1), abs(y2 - y1)
                if dx > dy * 2.5:
                    my = (y1 + y2) / 2
                    if sh * 0.20 <= my <= sh * 0.80:
                        center_dist = abs(my - sh * 0.5) / (sh * 0.5)
                        centrality_weight = float(np.exp(-2.5 * (center_dist ** 2)))
                        score = dx * centrality_weight
                        h_lines.append((my, min(x1, x2), max(x1, x2), dx, score))

            if h_lines:
                h_lines.sort(key=lambda l: l[4], reverse=True)

                backbone = None
                for l in h_lines:
                    line_cx = (l[1] + l[2]) / 2
                    if sw * 0.20 <= line_cx <= sw * 0.80:
                        backbone = l
                        break
                if backbone is None:
                    backbone = h_lines[0]

                phone_lines = []
                for l in h_lines:
                    if abs(l[0] - backbone[0]) <= max(25, int(sh * 0.04)):
                        if not (l[2] < backbone[1] - 35 or l[1] > backbone[2] + 35):
                            phone_lines.append(l)

                if not phone_lines:
                    phone_lines = [backbone]

                phone_y_small = int(np.average([l[0] for l in phone_lines], weights=[l[3] for l in phone_lines]))
                line_min_x = min(l[1] for l in phone_lines)
                line_max_x = max(l[2] for l in phone_lines)

                # Scan along horizontal strip around phone_y_small
                strip_h = max(8, int(sh * 0.035))
                strip = edges[max(0, phone_y_small - strip_h):min(sh, phone_y_small + strip_h), :]
                col_act = np.sum(strip > 0, axis=0)

                # Scan leftwards from line_min_x
                curr_left = line_min_x
                gap = 0
                while curr_left > 10:
                    if col_act[curr_left] >= 2:
                        gap = 0
                    else:
                        gap += 1
                        if gap > 8:
                            curr_left += 8
                            break
                    curr_left -= 1

                # Scan rightwards from line_max_x
                curr_right = line_max_x
                gap = 0
                while curr_right < sw - 10:
                    if col_act[curr_right] >= 2:
                        gap = 0
                    else:
                        gap += 1
                        if gap > 8:
                            curr_right -= 8
                            break
                    curr_right += 1

                phone_left = int(curr_left / scale)
                phone_right = int(curr_right / scale)
                phone_cy = int(phone_y_small / scale)
            else:
                confidence = "FALLBACK_PRIOR"
                phone_cy = int(h * 0.50)
                phone_left = int(w * 0.15)
                phone_right = int(w * 0.85)

            phone_w = max(500, phone_right - phone_left)
            margin_x = max(80, int(phone_w * 0.08))
            cw = min(w, phone_w + 2 * margin_x)
            ch = min(h, int(cw / 2.22))

            bx = max(0, min(phone_left - margin_x, w - cw))
            by = max(0, min(phone_cy - ch // 2, h - ch))
            return (bx, by, cw, ch), confidence

        else:
            # Vertical sides (left / right)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 25,
                                    minLineLength=int(sh * 0.08), maxLineGap=20)
            if lines is None:
                lines = np.array([])
            else:
                lines = lines.reshape(-1, 4)

            # Filter vertical lines in central horizontal zone (0.20 to 0.80) with centrality weighting
            v_lines = []
            for x1, y1, x2, y2 in lines:
                dx, dy = abs(x2 - x1), abs(y2 - y1)
                if dy > dx * 3:
                    mx = (x1 + x2) / 2
                    if sw * 0.20 <= mx <= sw * 0.80:
                        if not (max(y1, y2) < sh * 0.25 or min(y1, y2) > sh * 0.85):
                            center_dist = abs(mx - sw * 0.5) / (sw * 0.5)
                            centrality_weight = float(np.exp(-2.5 * (center_dist ** 2)))
                            score = dy * centrality_weight
                            v_lines.append((mx, min(y1, y2), max(y1, y2), dy, score))

            if v_lines:
                v_lines.sort(key=lambda l: l[4], reverse=True)

                backbone = None
                for l in v_lines:
                    line_cy = (l[1] + l[2]) / 2
                    if sh * 0.20 <= line_cy <= sh * 0.80:
                        backbone = l
                        break
                if backbone is None:
                    backbone = v_lines[0]

                phone_lines = []
                for l in v_lines:
                    if abs(l[0] - backbone[0]) <= max(25, int(sw * 0.04)):
                        if not (l[2] < backbone[1] - 40 or l[1] > backbone[2] + 40):
                            phone_lines.append(l)

                if not phone_lines:
                    phone_lines = [backbone]

                phone_x_small = int(np.average([l[0] for l in phone_lines], weights=[l[3] for l in phone_lines]))
                line_min_y = min(l[1] for l in phone_lines)
                line_max_y = max(l[2] for l in phone_lines)

                # Scan along vertical strip around phone_x_small
                strip_w = max(8, int(sw * 0.035))
                strip = edges[:, max(0, phone_x_small - strip_w):min(sw, phone_x_small + strip_w)]
                row_act = np.sum(strip > 0, axis=1)

                curr_top = line_min_y
                gap = 0
                while curr_top > 10:
                    if row_act[curr_top] >= 2:
                        gap = 0
                    else:
                        gap += 1
                        if gap > 8:
                            curr_top += 8
                            break
                    curr_top -= 1

                curr_bot = line_max_y
                gap = 0
                while curr_bot < sh - 10:
                    if row_act[curr_bot] >= 2:
                        gap = 0
                    else:
                        gap += 1
                        if gap > 8:
                            curr_bot -= 8
                            break
                    curr_bot += 1

                phone_top = int(curr_top / scale)
                phone_bottom = int(curr_bot / scale)
                phone_cx = int(phone_x_small / scale)
            else:
                confidence = "FALLBACK_PRIOR"
                phone_cx = int(w * 0.50)
                phone_top = int(h * 0.10)
                phone_bottom = int(h * 0.90)

            phone_h = max(600, phone_bottom - phone_top)
            margin_y = max(60, int(phone_h * 0.06))
            ch = min(h, phone_h + 2 * margin_y)
            # Aspect ratio ~ 0.35 for side view
            cw = min(w, max(220, int(ch * 0.35)))

            by = max(0, min(phone_top - margin_y, h - ch))
            bx = max(0, min(phone_cx - cw // 2, w - cw))
            return (bx, by, cw, ch), confidence

    def crop_focused_surface(self, img: np.ndarray) -> Tuple[np.ndarray, Optional[Tuple[int, int, int, int]]]:
        """
        Detects smartphone body contour on front/back views and crops tightly.
        Uses HandFilter skin segmentation to completely excise human fingers/hands holding the screen.
        """
        h, w = img.shape[:2]
        scale = 800.0 / max(h, w)
        small = cv2.resize(img, (int(w * scale), int(h * scale)))
        sh, sw = small.shape[:2]

        skin_dilated = None
        if self.hand_filter is not None:
            try:
                skin = self.hand_filter.detect_skin_mask(small)
                skin_dilated = cv2.dilate(skin, np.ones((11, 11), np.uint8), iterations=2)
            except Exception:
                pass

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (15, 15), 0)

        ch, cw = max(10, int(sh * 0.04)), max(10, int(sw * 0.04))
        corners = [gray[0:ch, 0:cw], gray[0:ch, -cw:], gray[-ch:, 0:cw], gray[-ch:, -cw:]]
        bg_bright = float(np.median([np.median(c) for c in corners]))

        # Front display glass is dark (typical 20-60). Table/environment is brighter (80-220).
        thresh_val = max(50, min(140, int((bg_bright + 45) / 2)))
        _, thresh = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY_INV)

        # Subtract operator fingers/hands
        if skin_dilated is not None:
            phone_only = cv2.bitwise_and(thresh, cv2.bitwise_not(skin_dilated))
        else:
            phone_only = thresh

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
        closed = cv2.morphologyEx(phone_only, cv2.MORPH_CLOSE, kernel)

        cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_cnts = []
        for c in cnts:
            area = cv2.contourArea(c)
            if area > (sh * sw * 0.06):
                bx, by, bw, bh = cv2.boundingRect(c)
                ar = max(bw, bh) / max(min(bw, bh), 1)
                if 1.35 <= ar <= 2.6:
                    valid_cnts.append((area, bx, by, bw, bh))

        if valid_cnts:
            _, bx, by, bw, bh = max(valid_cnts, key=lambda x: x[0])
            fx = int(bx / scale)
            fy = int(by / scale)
            fw = int(bw / scale)
            fh = int(bh / scale)
            pad_x = int(fw * 0.03)
            pad_y = int(fh * 0.03)
            x1 = max(0, fx - pad_x)
            y1 = max(0, fy - pad_y)
            x2 = min(w, fx + fw + pad_x)
            y2 = min(h, fy + fh + pad_y)
            return img[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)

        # Fallback to general bounding box
        return img, (0, 0, w, h)

    def create_verification_preview(
        self,
        orig_img: np.ndarray,
        cropped_img: np.ndarray,
        tilt_angle: float,
        bbox: Tuple[int, int, int, int],
        confidence: str,
        side: str
    ) -> np.ndarray:
        """
        Generates a side-by-side verification preview showing original with bounding box and cropped result.
        """
        bx, by, bw, bh = bbox
        vis_orig = orig_img.copy()

        # Draw phone body bounding box in green
        cv2.rectangle(vis_orig, (bx, by), (bx + bw, by + bh), (0, 230, 0), 4)
        cv2.putText(vis_orig, f"BODI HP ({side.upper()})", (bx + 8, max(30, by - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 230, 0), 2, cv2.LINE_AA)

        target_h = 500
        r_h, r_w = vis_orig.shape[:2]
        c_h, c_w = cropped_img.shape[:2]

        r_small = cv2.resize(vis_orig, (int(r_w * target_h / max(1, r_h)), target_h))
        c_small = cv2.resize(cropped_img, (int(c_w * target_h / max(1, c_h)), target_h))

        divider = np.full((target_h, 4, 3), (180, 180, 180), dtype=np.uint8)
        body = np.hstack([r_small, divider, c_small])

        banner_h = 44
        total_w = body.shape[1]
        banner = np.full((banner_h, total_w, 3), (35, 30, 45), dtype=np.uint8)

        left_label = f"Foto Mentah (Kemiringan: {tilt_angle:+.1f} deg, Status: {confidence})"
        right_label = f"Hasil Auto-Crop Bodi ({bw}x{bh} px - Latar Terbuang)"

        cv2.putText(banner, left_label, (16, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 255), 2, cv2.LINE_AA)

        right_x_offset = r_small.shape[1] + 16
        cv2.putText(banner, right_label, (right_x_offset, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)

        return np.vstack([banner, body])

    def detect_body_with_yolo(self, img: np.ndarray, side: str) -> Optional[Tuple[int, int, int, int, float]]:
        """
        Uses model_detect_body_hp.pt exclusively for side views (left, right, top, bottom).
        STRICT: NEVER runs on front or back views!
        Returns: (bx, by, bw, bh, confidence) or None if no valid detection.
        """
        side_lower = side.lower()
        # RULE: Never use this model for front, back, or rear views!
        if side_lower in ["front", "back", "rear"]:
            return None

        if self.yolo_model is None:
            return None

        h, w = img.shape[:2]
        try:
            preds = self.yolo_model(img, conf=0.18, iou=0.45, verbose=False)
            boxes = preds[0].boxes
            if boxes is None or len(boxes) == 0:
                return None

            # Pick detection with highest confidence
            best = max(boxes, key=lambda b: float(b.conf[0]))
            conf = float(best.conf[0])
            x1, y1, x2, y2 = [int(v) for v in best.xyxy[0].cpu().numpy()]

            # Add 6% safety margin so buttons, camera bump, and rounded corners are preserved
            bw = x2 - x1
            bh = y2 - y1
            pad_x = int(bw * 0.06)
            pad_y = int(bh * 0.06)

            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(w, x2 + pad_x)
            y2 = min(h, y2 + pad_y)

            return (x1, y1, x2 - x1, y2 - y1, conf)
        except Exception:
            return None

    def localize_and_crop(self, img: np.ndarray, side: str) -> Dict[str, Any]:
        """
        Executes complete Stage 1 localization and auto-cropping for a single view image.
        Returns:
            {
                "cropped_img": np.ndarray (BGR),
                "orig_rotated": np.ndarray (BGR),
                "bbox": (bx, by, bw, bh),
                "tilt_angle": float,
                "confidence": str,
                "preview_img": np.ndarray (BGR side-by-side)
            }
        """
        side_lower = side.lower()

        if side_lower in ["front", "back", "rear"]:
            # STRICT RULE: For front and back, DO NOT use model_detect_body_hp.pt!
            # Use dedicated surface contouring / full panel isolation with HandFilter skin excision
            cropped, bbox = self.crop_focused_surface(img)
            if bbox is None:
                bbox = (0, 0, img.shape[1], img.shape[0])
            ang = 0.0
            conf = "SURFACE_CONTOUR_NO_HANDS"
            rot = img
        else:
            # Side views: left, right, top, bottom
            h, w = img.shape[:2]
            # 1. Straighten camera tilt before detection
            ang = self.detect_angle(img, side_lower)
            if abs(ang) >= 0.8:
                rot = self.rotate_image(img, ang)
            else:
                ang = 0.0
                rot = img

            # 2. Try YOLO Body Detector on straightened image
            yolo_res = self.detect_body_with_yolo(rot, side_lower)
            use_yolo = False
            if yolo_res is not None:
                bx, by, bw, bh, yolo_conf = yolo_res
                # Sanity check: side view profile should not be excessively wide
                if side_lower in ['left', 'right']:
                    if bw <= int(w * 0.45) and yolo_conf >= 0.40:
                        use_yolo = True
                elif side_lower in ['top', 'bottom']:
                    if bh <= int(h * 0.45) and yolo_conf >= 0.40:
                        use_yolo = True

            if use_yolo:
                bbox = (bx, by, bw, bh)
                conf = f"YOLO_BODY_AI (Conf: {yolo_conf:.1%})"
                cropped = rot[by:by+bh, bx:bx+bw]
            else:
                # 3. Algorithmic tilt alignment + edge scanning fallback on straightened image
                bbox, conf = self.crop_focused_phone(rot, side_lower)
                bx, by, bw, bh = bbox

                # Boundary refinement along the thin axis using mid-strip contrast
                gray = cv2.cvtColor(rot, cv2.COLOR_BGR2GRAY)
                if side_lower in ['left', 'right']:
                    mid_y1 = by + int(bh * 0.25)
                    mid_y2 = by + int(bh * 0.75)
                    mid_strip = gray[mid_y1:mid_y2, :]
                    col_means = np.mean(mid_strip, axis=0)
                    phone_cols = np.where(col_means > 40)[0]
                    if len(phone_cols) > 0 and (phone_cols[-1] - phone_cols[0]) < bw:
                        pad_x = max(20, int((phone_cols[-1] - phone_cols[0]) * 0.15))
                        new_x1 = max(0, phone_cols[0] - pad_x)
                        new_x2 = min(w, phone_cols[-1] + pad_x)
                        bx = int(new_x1)
                        bw = int(new_x2 - new_x1)
                        bbox = (bx, by, bw, bh)
                elif side_lower in ['top', 'bottom']:
                    mid_x1 = bx + int(bw * 0.25)
                    mid_x2 = bx + int(bw * 0.75)
                    mid_strip = gray[:, mid_x1:mid_x2]
                    row_means = np.mean(mid_strip, axis=1)
                    phone_rows = np.where(row_means > 40)[0]
                    if len(phone_rows) > 0 and (phone_rows[-1] - phone_rows[0]) < bh:
                        pad_y = max(20, int((phone_rows[-1] - phone_rows[0]) * 0.15))
                        new_y1 = max(0, phone_rows[0] - pad_y)
                        new_y2 = min(h, phone_rows[-1] + pad_y)
                        by = int(new_y1)
                        bh = int(new_y2 - new_y1)
                        bbox = (bx, by, bw, bh)

                cropped = rot[by:by+bh, bx:bx+bw]

        preview = self.create_verification_preview(rot, cropped, ang, bbox, conf, side_lower)

        return {
            "cropped_img": cropped,
            "orig_rotated": rot,
            "bbox": bbox,
            "tilt_angle": ang,
            "confidence": conf,
            "preview_img": preview
        }

