#!/usr/bin/env python3
"""
STANDARDIZED INSPECTION TRAY & ARUCO FIDUCIAL MARKER GENERATOR
==============================================================
Pusat Gadai Indonesia (PGI) — Defect Detection & Cosmetic Grading

Generates a standardized, printable inspection mat/tray template (A4 format):
- 4 Precision ArUco Fiducial Markers (DICT_4X4_50, IDs 0, 1, 2, 3) at calibrated 30mm x 30mm dimensions.
- Smartphone alignment silhouette box (170mm x 85mm) accommodating devices up to 6.9".
- Metric calibration scales (100mm ruler along X and Y axes).
- Operational SOP guidelines for store and warehouse inspectors.
Outputs:
- PNG format (300 DPI high resolution for direct printing).
"""

import os
import cv2
import numpy as np

# A4 dimensions at 300 DPI: 2480 x 3508 pixels
DPI = 300
MM_TO_INCH = 25.4
PX_PER_MM = DPI / MM_TO_INCH  # ~11.811 pixels per mm

PAGE_W = int(210 * PX_PER_MM)  # 2480 px
PAGE_H = int(297 * PX_PER_MM)  # 3508 px

MARKER_SIZE_MM = 30.0
MARKER_SIZE_PX = int(MARKER_SIZE_MM * PX_PER_MM)


def generate_aruco_marker(marker_id: int, size_px: int, dict_id: int = cv2.aruco.DICT_4X4_50) -> np.ndarray:
    """Generates a single ArUco marker image."""
    dictionary = cv2.aruco.getPredefinedDictionary(dict_id)
    if hasattr(cv2.aruco, "generateImageMarker"):
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, size_px)
    else:
        marker = cv2.aruco.drawMarker(dictionary, marker_id, size_px)
    return cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)


def create_standard_tray_template(output_path: str = "static/tray_marker_template.png") -> str:
    """Creates a high-precision printable A4 inspection tray template."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas = np.full((PAGE_H, PAGE_W, 3), 255, dtype=np.uint8)

    # 1. Header Banner
    cv2.rectangle(canvas, (0, 0), (PAGE_W, int(45 * PX_PER_MM)), (35, 45, 55), -1)
    cv2.putText(
        canvas,
        "PUSAT GADAI INDONESIA - SMARTPHONE INSPECTION & CALIBRATION TRAY",
        (int(15 * PX_PER_MM), int(26 * PX_PER_MM)),
        cv2.FONT_HERSHEY_DUPLEX,
        1.3,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )
    cv2.putText(
        canvas,
        "Standardized Spatial Scale & Homography Template (ArUco DICT_4X4_50 | 30mm Fiducial)",
        (int(15 * PX_PER_MM), int(37 * PX_PER_MM)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (0, 210, 255),
        2,
        cv2.LINE_AA
    )

    # 2. ArUco Marker Positions (4 Corners of the active inspection zone)
    margin_x_mm = 20.0
    margin_y_mm = 58.0
    active_w_mm = 170.0
    active_h_mm = 215.0

    marker_coords = {
        0: (int(margin_x_mm * PX_PER_MM), int(margin_y_mm * PX_PER_MM)),                                    # Top-Left (ID 0)
        1: (int((margin_x_mm + active_w_mm - MARKER_SIZE_MM) * PX_PER_MM), int(margin_y_mm * PX_PER_MM)),  # Top-Right (ID 1)
        2: (int(margin_x_mm * PX_PER_MM), int((margin_y_mm + active_h_mm - MARKER_SIZE_MM) * PX_PER_MM)),  # Bottom-Left (ID 2)
        3: (int((margin_x_mm + active_w_mm - MARKER_SIZE_MM) * PX_PER_MM), int((margin_y_mm + active_h_mm - MARKER_SIZE_MM) * PX_PER_MM)) # Bottom-Right (ID 3)
    }

    for marker_id, (mx, my) in marker_coords.items():
        marker_img = generate_aruco_marker(marker_id, MARKER_SIZE_PX)
        canvas[my:my+MARKER_SIZE_PX, mx:mx+MARKER_SIZE_PX] = marker_img
        # Thin border around marker
        cv2.rectangle(canvas, (mx, my), (mx + MARKER_SIZE_PX, my + MARKER_SIZE_PX), (180, 180, 180), 2)
        # Label
        lbl = f"ArUco ID #{marker_id} ({int(MARKER_SIZE_MM)}mm)"
        cv2.putText(canvas, lbl, (mx, my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1, cv2.LINE_AA)

    # 3. Central Smartphone Placement Box (170mm x 85mm)
    box_w_mm = 85.0
    box_h_mm = 175.0
    box_cx_mm = margin_x_mm + (active_w_mm / 2.0)
    box_cy_mm = margin_y_mm + (active_h_mm / 2.0)

    bx1 = int((box_cx_mm - box_w_mm / 2.0) * PX_PER_MM)
    by1 = int((box_cy_mm - box_h_mm / 2.0) * PX_PER_MM)
    bx2 = int((box_cx_mm + box_w_mm / 2.0) * PX_PER_MM)
    by2 = int((box_cy_mm + box_h_mm / 2.0) * PX_PER_MM)

    # Shaded matte background for phone placement
    cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (242, 245, 248), -1)
    cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (0, 140, 255), 4)

    # Target Crosshairs
    center_px_x = int(box_cx_mm * PX_PER_MM)
    center_px_y = int(box_cy_mm * PX_PER_MM)
    ch_len = int(12 * PX_PER_MM)
    cv2.line(canvas, (center_px_x - ch_len, center_px_y), (center_px_x + ch_len, center_px_y), (0, 140, 255), 2)
    cv2.line(canvas, (center_px_x, center_px_y - ch_len), (center_px_x, center_px_y + ch_len), (0, 140, 255), 2)
    cv2.circle(canvas, (center_px_x, center_px_y), int(5 * PX_PER_MM), (0, 140, 255), 2)

    # Box Labels
    cv2.putText(
        canvas,
        "TEMPATKAN UNIT SMARTPHONE DI SINI (LAYAR MENGHADAP ATAS)",
        (bx1 + int(4 * PX_PER_MM), by1 + int(12 * PX_PER_MM)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (30, 80, 160),
        2,
        cv2.LINE_AA
    )
    cv2.putText(
        canvas,
        "[ FRONT / BACK / SIDE VIEW ALIGNMENT ZONE ]",
        (bx1 + int(10 * PX_PER_MM), by2 - int(8 * PX_PER_MM)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (100, 100, 100),
        1,
        cv2.LINE_AA
    )

    # 4. Metric Calibration Rulers (100mm along X and Y)
    ruler_start_x = bx1
    ruler_y = by2 + int(12 * PX_PER_MM)
    ruler_len_100mm = int(100 * PX_PER_MM)

    cv2.line(canvas, (ruler_start_x, ruler_y), (ruler_start_x + ruler_len_100mm, ruler_y), (0, 0, 0), 3)
    for mm in range(0, 101, 5):
        rx = ruler_start_x + int(mm * PX_PER_MM)
        tick_h = int(6 * PX_PER_MM) if (mm % 10 == 0) else int(3 * PX_PER_MM)
        cv2.line(canvas, (rx, ruler_y), (rx, ruler_y + tick_h), (0, 0, 0), 2)
        if mm % 10 == 0:
            cv2.putText(canvas, str(mm), (rx - int(2 * PX_PER_MM), ruler_y + tick_h + int(5 * PX_PER_MM)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(canvas, "Skala Kalibrasi Fisik: 100 mm", (ruler_start_x + int(25 * PX_PER_MM), ruler_y + int(12 * PX_PER_MM)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

    # 5. SOP Instructions Box at Bottom
    sop_y = int(280 * PX_PER_MM)
    cv2.rectangle(canvas, (int(15 * PX_PER_MM), sop_y), (PAGE_W - int(15 * PX_PER_MM), PAGE_H - int(12 * PX_PER_MM)), (235, 238, 240), -1)
    cv2.rectangle(canvas, (int(15 * PX_PER_MM), sop_y), (PAGE_W - int(15 * PX_PER_MM), PAGE_H - int(12 * PX_PER_MM)), (190, 195, 200), 2)

    sop_title = "STANDAR OPERASIONAL PROSEDUR (SOP) PENGAMBILAN FOTO INSPEKSI:"
    cv2.putText(canvas, sop_title, (int(20 * PX_PER_MM), sop_y + int(8 * PX_PER_MM)),
                cv2.FONT_HERSHEY_DUPLEX, 0.65, (20, 20, 20), 2, cv2.LINE_AA)

    sop_steps = [
        "1. Cetak lembar ini pada kertas A4 tanpa scaling (100% actual size / borderless).",
        "2. Letakkan unit smartphone di dalam kotak oranye. Pastikan minimal satu ArUco Marker terlihat jelas di frame.",
        "3. Ambil 5 sudut foto: Layar Depan (front), Bodi Belakang (back), Samping Kiri (left), Samping Kanan (right), dan Bawah (bottom).",
        "4. Hindari bayangan tangan menutupi marker; sistem AI akan mengkalibrasi dimensi cacat secara otomatis (sub-milimeter)."
    ]
    for i, step in enumerate(sop_steps):
        cv2.putText(canvas, step, (int(20 * PX_PER_MM), sop_y + int((15 + i * 6.5) * PX_PER_MM)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 50, 50), 1, cv2.LINE_AA)

    # Save PNG
    cv2.imwrite(output_path, canvas, [cv2.IMWRITE_PNG_COMPRESSION, 4])
    print(f"[SUCCESS] Standard Tray Marker Template saved at: {output_path}")
    print(f"Dimensions: {PAGE_W}x{PAGE_H} px (A4 @ 300 DPI, Calibrated Marker: {MARKER_SIZE_MM}mm)")
    return output_path


if __name__ == "__main__":
    create_standard_tray_template()
