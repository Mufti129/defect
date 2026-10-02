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
    def __init__(self):
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
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (25, 25), 0)

        ch, cw = max(10, int(h * 0.03)), max(10, int(w * 0.03))
        corners = [gray[0:ch, 0:cw], gray[0:ch, -cw:], gray[-ch:, 0:cw], gray[-ch:, -cw:]]
        bg_bright = float(np.median([np.median(c) for c in corners]))

        if bg_bright > 130:
            _, thresh = cv2.threshold(blur, int(bg_bright * 0.72), 255, cv2.THRESH_BINARY_INV)
        else:
            _, thresh = cv2.threshold(blur, int(bg_bright * 1.28), 255, cv2.THRESH_BINARY)

        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return img, (0, 0, w, h)

        valid_cnts = []
        for c in cnts:
            area = cv2.contourArea(c)
            if area > (h * w * 0.08):
                bx, by, bw, bh = cv2.boundingRect(c)
                ar = max(bw, bh) / max(min(bw, bh), 1)
                if 1.3 <= ar <= 2.6:
                    valid_cnts.append((area, bx, by, bw, bh))

        if not valid_cnts:
            return img, (0, 0, w, h)

        _, bx, by, bw, bh = max(valid_cnts, key=lambda x: x[0])

        pad_x = int(bw * 0.03)
        pad_y = int(bh * 0.03)
        x1 = max(0, bx - pad_x)
        y1 = max(0, by - pad_y)
        x2 = min(w, bx + bw + pad_x)
        y2 = min(h, by + bh + pad_y)

        return img[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)

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
            cropped, bbox = self.crop_focused_surface(img)
            if bbox is None:
                bbox = (0, 0, img.shape[1], img.shape[0])
            ang = 0.0
            conf = "SURFACE_CONTOUR"
            rot = img
        else:
            ang = self.detect_angle(img, side_lower)
            rot = self.rotate_image(img, ang)
            bbox, conf = self.crop_focused_phone(rot, side_lower)
            bx, by, bw, bh = bbox
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
