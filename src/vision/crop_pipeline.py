#!/usr/bin/env python3
"""
ROTATION-ALIGNED & PROPORTIONAL PHONE-FOCUSED CROPPING PIPELINE
==============================================================
Designed specifically for smartphone defect detection annotation (YOLO, Roboflow, CVAT).
Features:
- Dynamic scan-based physical boundary detection for exact phone extremities.
- Proportional breathing room / margin so phone corners and edges are never cut off.
- Eliminates peripheral clutter (boxes, stickers, other phones on desk).
- Multi-processing support and clean verification previews.
"""

import os
import sys
import shutil
import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
import cv2
import numpy as np

# Script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default directories
DEFAULT_UJI_DIR = os.path.join(BASE_DIR, "Uji Yang mau di crop berdasarkan referensi")
DEFAULT_BACKUP_DIR = os.path.join(BASE_DIR, "Uji Yang mau di crop berdasarkan referensi_ORIGINAL_BACKUP")
DEFAULT_PREVIEW_DIR = os.path.join(BASE_DIR, "verifikasi_preview")
DEFAULT_REPORT_CSV = os.path.join(BASE_DIR, "crop_report.csv")

VALID_SIDES = {'bottom', 'top', 'left', 'right', 'front', 'back', 'rear'}
PRESERVED_SIDES = {'front', 'back', 'rear'}


def detect_angle(img, side):
    """
    Detects the tilt angle (in degrees) of the phone edge in the image.
    Uses Hough lines in the central region where the active phone is held.
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


def rotate_image(img, angle):
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


def crop_focused_phone(rotated_img, side):
    """
    Detects physical phone extremities using continuous edge scanning,
    ensuring the entire phone is preserved with proportional breathing room.
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
            # Sort by centrality-weighted score descending
            h_lines.sort(key=lambda l: l[4], reverse=True)

            # Identify backbone line: highest scoring line in central horizontal zone
            backbone = None
            for l in h_lines:
                line_cx = (l[1] + l[2]) / 2
                if sw * 0.20 <= line_cx <= sw * 0.80:
                    backbone = l
                    break
            if backbone is None:
                backbone = h_lines[0]

            # Group lines belonging to phone bezel: close to backbone in Y and connected in X
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

            # Scan along horizontal strip around phone_y_small to trace rounded corners
            strip_h = max(8, int(sh * 0.035))
            strip = edges[max(0, phone_y_small - strip_h):min(sh, phone_y_small + strip_h), :]
            col_act = np.sum(strip > 0, axis=0)

            # Scan leftwards from line_min_x
            curr_left = line_min_x
            gap = 0
            while curr_left > 10:
                if col_act[curr_left] >= 2:
                    gap = 0
                elif col_act[curr_left] == 1:
                    gap += 1
                    if gap > 8:
                        curr_left += 8
                        break
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
                elif col_act[curr_right] == 1:
                    gap += 1
                    if gap > 8:
                        curr_right -= 8
                        break
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
            phone_cy = int(h * 0.55)
            phone_left = int(w * 0.15)
            phone_right = int(w * 0.85)

        phone_w = max(600, phone_right - phone_left)

        # Proportional framing with space around phone ends:
        margin_x = max(100, int(phone_w * 0.08))
        cw = min(w, phone_w + 2 * margin_x)
        # Aspect ratio ~ 2.22 for balanced, full-view framing
        ch = min(h, int(cw / 2.22))

        bx = max(0, min(phone_left - margin_x, w - cw))
        by = max(0, min(phone_cy - ch // 2, h - ch))

        return (bx, by, cw, ch), confidence

    else:
        # vertical sides (left / right)
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
            # Sort by centrality-weighted score descending
            v_lines.sort(key=lambda l: l[4], reverse=True)

            # Identify backbone line: highest scoring vertical line in central vertical zone
            backbone = None
            for l in v_lines:
                line_cy = (l[1] + l[2]) / 2
                if sh * 0.20 <= line_cy <= sh * 0.80:
                    backbone = l
                    break
            if backbone is None:
                backbone = v_lines[0]

            # Group lines belonging to phone bezel: close to backbone in X and connected in Y
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

            # Scan along vertical strip around phone_x_small to find top and bottom extremities
            strip_w = max(8, int(sw * 0.035))
            strip = edges[:, max(0, phone_x_small - strip_w):min(sw, phone_x_small + strip_w)]
            row_act = np.sum(strip > 0, axis=1)

            # Scan upwards from line_min_y
            curr_top = line_min_y
            gap = 0
            while curr_top > 10:
                if row_act[curr_top] >= 2:
                    gap = 0
                elif row_act[curr_top] == 1:
                    gap += 1
                    if gap > 8:
                        curr_top += 8
                        break
                else:
                    gap += 1
                    if gap > 8:
                        curr_top += 8
                        break
                curr_top -= 1

            # Scan downwards from line_max_y
            curr_bot = line_max_y
            gap = 0
            while curr_bot < sh - 10:
                if row_act[curr_bot] >= 2:
                    gap = 0
                elif row_act[curr_bot] == 1:
                    gap += 1
                    if gap > 8:
                        curr_bot -= 8
                        break
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
            phone_top = int(h * 0.15)
            phone_bottom = int(h * 0.85)

        phone_h = max(800, phone_bottom - phone_top)

        # Proportional framing with space above top and below bottom:
        margin_y = max(100, int(phone_h * 0.08))
        ch = min(h, phone_h + 2 * margin_y)
        # Aspect ratio ~ 0.37 for proportional width with space around buttons
        cw = min(w, int(ch * 0.37))

        by = max(0, min(phone_top - margin_y, h - ch))
        bx = max(0, min(phone_cx - cw // 2, w - cw))

        return (bx, by, cw, ch), confidence


def create_verification_preview(orig_img, cropped_img, tilt_angle, bbox):
    """
    Creates a clean side-by-side comparison with a top metadata banner.
    Draws the crop bounding box on the original image without obstructing the cropped phone.
    """
    bx, by, bw, bh = bbox
    vis_orig = orig_img.copy()

    # Draw bounding box on original image
    cv2.rectangle(vis_orig, (bx, by), (bx + bw, by + bh), (0, 255, 0), 4)

    target_h = 600
    r_h, r_w = vis_orig.shape[:2]
    c_h, c_w = cropped_img.shape[:2]

    r_small = cv2.resize(vis_orig, (int(r_w * target_h / r_h), target_h))
    c_small = cv2.resize(cropped_img, (int(c_w * target_h / c_h), target_h))

    # Add divider line
    divider = np.full((target_h, 3, 3), (200, 200, 200), dtype=np.uint8)
    body = np.hstack([r_small, divider, c_small])

    # Add top banner
    banner_h = 46
    total_w = body.shape[1]
    banner = np.full((banner_h, total_w, 3), (35, 35, 35), dtype=np.uint8)

    left_label = f"Original [Crop: {bw}x{bh}] (Tilt: {tilt_angle:+.1f} deg)"
    right_label = f"Full Phone Crop ({bw}x{bh})"

    cv2.putText(banner, left_label, (16, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    right_x_offset = r_small.shape[1] + 16
    cv2.putText(banner, right_label, (right_x_offset, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    preview_img = np.vstack([banner, body])
    return preview_img


def crop_focused_surface(img):
    """
    Detects the smartphone body contour on front/back views and crops tightly
    with a proportional 3% breathing room, eliminating tabletop clutter/tarps.
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
        return img, None

    valid_cnts = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area > (h * w * 0.08):
            bx, by, bw, bh = cv2.boundingRect(c)
            ar = max(bw, bh) / max(min(bw, bh), 1)
            if 1.3 <= ar <= 2.6:
                valid_cnts.append((area, bx, by, bw, bh))

    if not valid_cnts:
        return img, None

    _, bx, by, bw, bh = max(valid_cnts, key=lambda x: x[0])

    pad_x = int(bw * 0.03)
    pad_y = int(bh * 0.03)
    x1 = max(0, bx - pad_x)
    y1 = max(0, by - pad_y)
    x2 = min(w, bx + bw + pad_x)
    y2 = min(h, by + bh + pad_y)

    return img[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)


def process_single_image(args_tuple):
    """
    Worker function to process a single image file.
    """
    src_path, dst_path, preview_file, side, gen_preview = args_tuple
    file_name = os.path.basename(src_path)
    folder_name = os.path.basename(os.path.dirname(src_path))

    result = {
        'folder': folder_name,
        'filename': file_name,
        'side': side,
        'status': 'UNKNOWN',
        'tilt_deg': 0.0,
        'crop_x': '',
        'crop_y': '',
        'crop_w': '',
        'crop_h': '',
        'confidence': '',
        'message': ''
    }

    try:
        if side in PRESERVED_SIDES:
            img = cv2.imread(src_path)
            if img is not None:
                cropped_surf, bbox = crop_focused_surface(img)
                if bbox is not None:
                    cv2.imwrite(dst_path, cropped_surf, [cv2.IMWRITE_JPEG_QUALITY, 96])
                    result['status'] = 'FOCUSED_SURFACE_CROPPED'
                    result['crop_x'] = bbox[0]
                    result['crop_y'] = bbox[1]
                    result['crop_w'] = bbox[2]
                    result['crop_h'] = bbox[3]
                    result['confidence'] = 'HIGH'
                    result['message'] = f'{side} surface tightly framed (eliminated table background)'
                    return result

            shutil.copy2(src_path, dst_path)
            result['status'] = 'PRESERVED'
            result['confidence'] = 'N/A'
            result['message'] = f'{side} side preserved full resolution'
            return result

        if side not in VALID_SIDES:
            shutil.copy2(src_path, dst_path)
            result['status'] = 'PRESERVED_UNKNOWN_SIDE'
            result['confidence'] = 'N/A'
            result['message'] = f'Unknown side "{side}", preserved full resolution'
            return result

        img = cv2.imread(src_path)
        if img is None:
            result['status'] = 'ERROR'
            result['message'] = 'Unable to read image'
            return result

        # 1. Detect angle
        tilt_angle = detect_angle(img, side)
        result['tilt_deg'] = round(tilt_angle, 2)

        # 2. Rotate / deskew
        rotated_img = rotate_image(img, tilt_angle)

        # 3. Detect phone bounds and crop focused area
        bbox, confidence = crop_focused_phone(rotated_img, side)
        bx, by, bw, bh = bbox
        cropped = rotated_img[by:by + bh, bx:bx + bw]

        # Save cropped image with high quality JPEG
        cv2.imwrite(dst_path, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])

        result['status'] = 'CROPPED'
        result['crop_x'] = bx
        result['crop_y'] = by
        result['crop_w'] = bw
        result['crop_h'] = bh
        result['confidence'] = confidence
        result['message'] = f'Cropped {bw}x{bh} (Tilt: {tilt_angle:+.2f} deg)'

        # 4. Save verification preview if requested
        if gen_preview and preview_file:
            preview_img = create_verification_preview(img, cropped, tilt_angle, bbox)
            cv2.imwrite(preview_file, preview_img, [cv2.IMWRITE_JPEG_QUALITY, 90])

    except Exception as e:
        result['status'] = 'ERROR'
        result['message'] = str(e)

    return result


def parse_side(filename):
    """
    Extracts side identifier from filename.
    """
    base = os.path.splitext(filename)[0].lower()
    parts = base.replace('-', '_').split('_')
    for part in reversed(parts):
        if part in VALID_SIDES:
            return part
    return 'unknown'


def run_pipeline(input_dir, output_dir, preview_dir, report_csv,
                 single_folder=None, no_preview=False, workers=4):
    """
    Main orchestration function.
    """
    print("==================================================")
    print(" PROPORTIONAL PHONE-FOCUSED CROPPING PIPELINE")
    print("==================================================")
    print(f" Input Directory   : {input_dir}")
    print(f" Output Directory  : {output_dir}")
    print(f" Preview Directory : {preview_dir if not no_preview else 'DISABLED'}")
    print(f" Audit Report CSV  : {report_csv}")
    print(f" Parallel Workers  : {workers}")

    if not os.path.exists(input_dir):
        print(f"\nError: Input directory does not exist: {input_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    if not no_preview:
        os.makedirs(preview_dir, exist_ok=True)

    # Detect if input_dir contains nested grade folders (e.g., raw_images/grade_A/unit_id)
    # vs flat unit folders (e.g., Uji Yang mau di crop.../unit_id)
    subdirs = sorted([
        f for f in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, f)) and not f.startswith('.')
    ])

    is_nested_grade_structure = any(s.lower().startswith('grade_') for s in subdirs)
    
    tasks = []
    
    if is_nested_grade_structure:
        print("\nDetected multi-grade hierarchy (e.g. grade_A, grade_B, etc.).")
        grade_dirs = [s for s in subdirs if s.lower().startswith('grade_')]
        for g_name in grade_dirs:
            g_path = os.path.join(input_dir, g_name)
            unit_dirs = sorted([
                u for u in os.listdir(g_path)
                if os.path.isdir(os.path.join(g_path, u)) and not u.startswith('.')
            ])
            if single_folder:
                unit_dirs = [u for u in unit_dirs if u == single_folder]

            for unit_name in unit_dirs:
                src_unit_dir = os.path.join(g_path, unit_name)
                dst_unit_dir = os.path.join(output_dir, g_name, unit_name)
                prev_unit_dir = os.path.join(preview_dir, g_name, unit_name) if not no_preview else None
                os.makedirs(dst_unit_dir, exist_ok=True)
                if prev_unit_dir:
                    os.makedirs(prev_unit_dir, exist_ok=True)

                for file_name in sorted(os.listdir(src_unit_dir)):
                    if not file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        continue
                    src_path = os.path.join(src_unit_dir, file_name)
                    dst_path = os.path.join(dst_unit_dir, file_name)
                    prev_file = os.path.join(prev_unit_dir, f"preview_{file_name}") if prev_unit_dir else None
                    side = parse_side(file_name)
                    tasks.append((src_path, dst_path, prev_file, side, not no_preview))
    else:
        if single_folder:
            target_folders = [single_folder]
        else:
            target_folders = subdirs

        print(f"\nFound {len(target_folders)} unit folder(s) to process.")

        for folder_name in target_folders:
            src_folder = os.path.join(input_dir, folder_name)
            dst_folder = os.path.join(output_dir, folder_name)
            prev_folder = os.path.join(preview_dir, folder_name) if not no_preview else None

            if not os.path.isdir(src_folder):
                continue

            os.makedirs(dst_folder, exist_ok=True)
            if prev_folder:
                os.makedirs(prev_folder, exist_ok=True)

            for file_name in sorted(os.listdir(src_folder)):
                if not file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue

                src_path = os.path.join(src_folder, file_name)
                dst_path = os.path.join(dst_folder, file_name)
                prev_file = os.path.join(prev_folder, f"preview_{file_name}") if prev_folder else None
                side = parse_side(file_name)

                tasks.append((src_path, dst_path, prev_file, side, not no_preview))

    print(f"Total image files queued: {len(tasks)}")

    # Filter out already cropped tasks if destination exists and is non-empty
    pending_tasks = []
    skipped_count = 0
    for t in tasks:
        src_p, dst_p, prev_p, side_name, gen_prev = t
        if os.path.exists(dst_p) and os.path.getsize(dst_p) > 1000:
            skipped_count += 1
        else:
            pending_tasks.append(t)

    if skipped_count > 0:
        print(f"Skipping {skipped_count} image(s) that already exist in output directory.")
        print(f"Remaining images to process: {len(pending_tasks)}")

    results = []
    total_cropped = 0
    total_preserved = 0
    total_errors = 0

    if workers > 1 and len(pending_tasks) > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_single_image, t): t for t in pending_tasks}
            for i, future in enumerate(as_completed(futures), 1):
                res = future.result()
                results.append(res)
                if 'CROPPED' in res['status']:
                    total_cropped += 1
                elif 'PRESERVED' in res['status']:
                    total_preserved += 1
                else:
                    total_errors += 1

                if i % 25 == 0 or i == len(pending_tasks):
                    print(f"  Processed {i}/{len(pending_tasks)} images...")
    else:
        for i, t in enumerate(pending_tasks, 1):
            res = process_single_image(t)
            results.append(res)
            if res['status'] == 'CROPPED':
                total_cropped += 1
            elif 'PRESERVED' in res['status']:
                total_preserved += 1
            else:
                total_errors += 1
            if len(pending_tasks) <= 20:
                print(f"  [{i}/{len(pending_tasks)}] {res['folder']}/{res['filename']} -> {res['status']}: {res['message']}")
            elif i % 25 == 0 or i == len(pending_tasks):
                print(f"  Processed {i}/{len(pending_tasks)} images...")

    # Save CSV Audit Report
    with open(report_csv, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'folder', 'filename', 'side', 'status', 'tilt_deg',
            'crop_x', 'crop_y', 'crop_w', 'crop_h', 'confidence', 'message'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(results, key=lambda x: (x['folder'], x['filename'])):
            writer.writerow(r)

    print("\n==================================================")
    print(" EXECUTION SUMMARY")
    print("==================================================")
    print(f"Total Images in Scope  : {len(tasks)}")
    print(f"Total Skipped (Exist)  : {skipped_count}")
    print(f"Total Newly Processed  : {len(pending_tasks)}")
    print(f"Total Focused Cropped  : {total_cropped}")
    print(f"Total Preserved        : {total_preserved}")
    print(f"Total Errors           : {total_errors}")
    print(f"Cropped Output Dir     : {output_dir}")
    if not no_preview:
        print(f"Verification Previews  : {preview_dir}")
    print(f"Audit Report Saved     : {report_csv}")
    print("Pipeline finished successfully.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Proportional Phone-Focused Cropping Pipeline for Defect Annotation."
    )
    parser.add_argument(
        "--input", "-i", type=str, default=DEFAULT_BACKUP_DIR,
        help=f"Input folder containing uncropped images (default: '{os.path.basename(DEFAULT_BACKUP_DIR)}')"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=DEFAULT_UJI_DIR,
        help=f"Output folder for cropped images (default: '{os.path.basename(DEFAULT_UJI_DIR)}')"
    )
    parser.add_argument(
        "--preview", "-p", type=str, default=DEFAULT_PREVIEW_DIR,
        help=f"Directory to save verification previews (default: '{os.path.basename(DEFAULT_PREVIEW_DIR)}')"
    )
    parser.add_argument(
        "--no-preview", action="store_true",
        help="Disable generating verification preview images"
    )
    parser.add_argument(
        "--report", "-r", type=str, default=DEFAULT_REPORT_CSV,
        help=f"Path for CSV report (default: '{os.path.basename(DEFAULT_REPORT_CSV)}')"
    )
    parser.add_argument(
        "--single-folder", "-s", type=str, default=None,
        help="Process only a specific folder name"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=4,
        help="Number of parallel worker processes (default: 4)"
    )

    args = parser.parse_args()

    # If default input dir doesn't exist, check if UJI_DIR exists and back it up
    if args.input == DEFAULT_BACKUP_DIR and not os.path.exists(DEFAULT_BACKUP_DIR):
        if os.path.exists(DEFAULT_UJI_DIR):
            print(f"Initializing backup from {DEFAULT_UJI_DIR} to {DEFAULT_BACKUP_DIR}...")
            shutil.copytree(DEFAULT_UJI_DIR, DEFAULT_BACKUP_DIR)

    run_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        preview_dir=args.preview,
        report_csv=args.report,
        single_folder=args.single_folder,
        no_preview=args.no_preview,
        workers=args.workers
    )


if __name__ == '__main__':
    main()

