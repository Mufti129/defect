#!/usr/bin/env python3
"""
OBJECT VALIDATION GUARDRAIL (COCO OBJECT DETECTOR)
===================================================
Detects arbitrary / non-phone objects (person/human, dog/cat/animal, laptop,
bottle/cup, car/vehicle, potted plant, furniture, etc.) to ensure that only
legitimate smartphone bodies are processed by the defect inspection engine.

Provides visual annotation of detected objects and produces structured
rejection reports instructing users to re-input a valid smartphone body.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np

# Path to standard COCO YOLO model
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_COCO_WEIGHTS = PROJECT_DIR / "yolov8n.pt"

# Complete Indonesian mapping for all 80 standard COCO classes
__all__ = ["ObjectGuardrail", "COCO_INDONESIAN_MAP", "NON_PHONE_CLASSES", "GUARDRAIL_COLORS"]

COCO_INDONESIAN_MAP = {
    # 1. Manusia & Aksesoris
    "person": "Manusia / Orang",
    "backpack": "Tas Ransel",
    "umbrella": "Payung",
    "handbag": "Tas Tangan",
    "tie": "Dasi",
    "suitcase": "Koper / Tas Pakaian",

    # 2. Binatang (Fauna)
    "bird": "Burung (Binatang)",
    "cat": "Kucing (Binatang)",
    "dog": "Anjing (Binatang)",
    "horse": "Kuda (Binatang)",
    "sheep": "Domba (Binatang)",
    "cow": "Sapi (Binatang)",
    "elephant": "Gajah (Binatang)",
    "bear": "Beruang (Binatang)",
    "zebra": "Zebra (Binatang)",
    "giraffe": "Jerapah (Binatang)",

    # 3. Komputer & Elektronik (Non-Phone)
    "laptop": "Komputer Laptop",
    "mouse": "Mouse Komputer",
    "keyboard": "Keyboard Komputer",
    "tv": "Televisi / Layar Monitor",
    "microwave": "Microwave",
    "oven": "Oven",
    "toaster": "Pemanggang Roti",
    "refrigerator": "Kulkas",
    "remote": "Remote Control",

    # 4. Wadah, Gelas & Minuman
    "bottle": "Botol Minuman",
    "wine glass": "Gelas Kaca",
    "cup": "Cangkir / Gelas Minuman",
    "bowl": "Mangkuk",
    "fork": "Garpu",
    "knife": "Pisau",
    "spoon": "Sendok",

    # 5. Kendaraan & Lalu Lintas
    "bicycle": "Sepeda",
    "car": "Mobil",
    "motorcycle": "Sepeda Motor",
    "airplane": "Pesawat Terbang",
    "bus": "Bus",
    "train": "Kereta Api",
    "truck": "Truk",
    "boat": "Perahu / Kapal",
    "traffic light": "Lampu Lalu Lintas",
    "fire hydrant": "Hidran Pemadam",
    "stop sign": "Rambu Berhenti",
    "parking meter": "Meteran Parkir",

    # 6. Tumbuhan & Perabot
    "potted plant": "Tanaman / Pot Bunga",
    "vase": "Vas Bunga",
    "chair": "Kursi",
    "couch": "Sofa",
    "bed": "Tempat Tidur",
    "dining table": "Meja Makan",
    "toilet": "Toilet",
    "bench": "Bangku Taman",

    # 7. Makanan & Buah
    "banana": "Pisang (Buah)",
    "apple": "Apel (Buah)",
    "sandwich": "Roti Sandwich",
    "orange": "Jeruk (Buah)",
    "broccoli": "Brokoli (Sayur)",
    "carrot": "Wortel (Sayur)",
    "hot dog": "Hot Dog",
    "pizza": "Pizza",
    "donut": "Donat",
    "cake": "Kue",

    # 8. Olahraga & Hiburan
    "frisbee": "Piring Terbang (Frisbee)",
    "skis": "Papan Ski",
    "snowboard": "Papan Seluncur",
    "sports ball": "Bola Olahraga",
    "kite": "Layang-Layang",
    "baseball bat": "Tongkat Baseball",
    "baseball glove": "Sarung Tangan",
    "skateboard": "Papan Skateboard",
    "surfboard": "Papan Selancar",
    "tennis racket": "Raket Tenis",

    # 9. Lainnya
    "book": "Buku / Dokumen",
    "clock": "Jam Dinding / Arloji",
    "scissors": "Gunting",
    "teddy bear": "Boneka Beruang",
    "hair drier": "Pengering Rambut",
    "toothbrush": "Sikat Gigi",
    "sink": "Wastafel",

    # 10. Smartphone (Target yang Sah)
    "cell phone": "Bodi Smartphone / Handphone"
}

# All COCO classes except cell phone are non-phone objects
NON_PHONE_CLASSES = {k: v for k, v in COCO_INDONESIAN_MAP.items() if k != "cell phone"}

# Specific arbitrary non-phone categories guarded by system (human, animals, laptop, bottle, car, plant, food)
# NOTE: Office furniture (chair, desk/dining table) is intentionally excluded to prevent false rejections on inspection tables
DISALLOWED_COCO_CLASSES = {
    # 1. Manusia / Orang (Selfie / Wajah / Subjek Manusia)
    "person",
    # 2. Binatang / Hewan
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
    # 3. Komputer & Elektronik (Non-HP)
    "laptop", "tv", "mouse", "keyboard", "microwave", "oven", "toaster", "refrigerator",
    # 4. Botol & Wadah Minuman
    "bottle", "cup", "wine glass", "bowl",
    # 5. Kendaraan
    "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    # 6. Tumbuhan & Flora
    "potted plant", "vase",
    # 7. Makanan
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake"
}

# Color palette for guardrail visual annotations (BGR)
GUARDRAIL_COLORS = {
    "person": (0, 0, 230),        # Crimson Red
    "cat": (0, 140, 255),         # Orange Amber
    "dog": (0, 140, 255),         # Orange Amber
    "laptop": (220, 100, 0),      # Blue
    "tv": (220, 100, 0),          # Blue
    "bottle": (0, 165, 255),      # Orange
    "cup": (0, 165, 255),         # Orange
    "potted plant": (50, 180, 50),# Green
    "vase": (50, 180, 50),        # Green
    "car": (180, 50, 200),        # Purple
    "bus": (180, 50, 200),        # Purple
    "motorcycle": (180, 50, 200), # Purple
    "cell phone": (16, 185, 129), # Emerald Green (Valid)
}


class ObjectGuardrail:
    """
    Validates user input images using a pre-trained COCO object detector.
    """
    COCO_INDONESIAN_MAP = COCO_INDONESIAN_MAP
    NON_PHONE_CLASSES = NON_PHONE_CLASSES

    def __init__(self, weights_path: Optional[str] = None):
        resolved_weights = None
        if weights_path and os.path.exists(weights_path):
            resolved_weights = weights_path
        elif (BASE_DIR / "weights" / "yolov8n.pt").exists():
            resolved_weights = str(BASE_DIR / "weights" / "yolov8n.pt")
        elif (PROJECT_DIR / "yolov8n.pt").exists():
            resolved_weights = str(PROJECT_DIR / "yolov8n.pt")
        else:
            resolved_weights = "yolov8n.pt"

        self.weights_path = resolved_weights
        self.model = None
        self.device = "cpu"

        try:
            import torch
            self.device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        except Exception:
            self.device = "cpu"

        try:
            from ultralytics import YOLO
            print(f"[ObjectGuardrail] Loading general object validator: {resolved_weights} (Device: {self.device})")
            self.model = YOLO(resolved_weights)
            # Warmup model
            if self.device in ["mps", "cuda"]:
                try:
                    dummy = np.zeros((320, 320, 3), dtype=np.uint8)
                    self.model.predict(dummy, imgsz=320, verbose=False, device=self.device)
                except Exception:
                    pass
        except Exception as e:
            print(f"[ObjectGuardrail] Error loading YOLO COCO model: {e}")
            self.model = None

    def _draw_label_box(self, img: np.ndarray, text: str, x1: int, y1: int, x2: int, y2: int, color: Tuple[int, int, int]):
        """Draws high-visibility text label pill on image without clipping."""
        h, w = img.shape[:2]
        font_scale = max(0.50, min(0.80, w / 850.0))
        thickness = 2
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

        if y1 >= th + 14:
            bg_y1 = y1 - th - 12
            bg_y2 = y1
            text_y = y1 - 6
        else:
            bg_y1 = y1
            bg_y2 = min(h - 1, y1 + th + 12)
            text_y = bg_y1 + th + 6

        bg_x1 = max(0, x1)
        bg_x2 = min(w - 1, x1 + tw + 16)

        cv2.rectangle(img, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)
        cv2.putText(
            img,
            text,
            (bg_x1 + 8, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA
        )

    def validate_single_image(
        self,
        img: np.ndarray,
        view_side: str = "body",
        conf_thresh: float = 0.25
    ) -> Dict[str, Any]:
        """
        Scans an image for non-phone objects (person, animal, laptop, bottle, vehicle, etc.).
        Returns full detection details, visual annotations, and validation status.
        """
        if self.model is None or img is None:
            return {
                "is_valid": True,
                "has_phone": True,
                "detected_non_phone": [],
                "detected_phone": [],
                "all_detections": [],
                "annotated_bgr": img,
                "rejection_message": None
            }

        h, w = img.shape[:2]
        max_dim = max(h, w)
        if max_dim > 640:
            scale = 640.0 / max_dim
            infer_img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            infer_img = img

        results = self.model.predict(
            infer_img,
            imgsz=640,
            conf=conf_thresh,
            verbose=False,
            device=self.device
        )

        detected_non_phone = []
        detected_phone = []
        all_detections = []
        has_phone = False
        annotated_img = img.copy()

        # Pass 1: Check if genuine cell phone is present
        for res in results:
            if res.boxes is not None and len(res.boxes) > 0:
                for i in range(len(res.boxes)):
                    c_name = self.model.names.get(int(res.boxes.cls[i].item()), "")
                    if c_name == "cell phone":
                        has_phone = True
                        break

        # Pass 2: Annotate and collect all objects
        for res in results:
            if res.boxes is None or len(res.boxes) == 0:
                continue

            for i in range(len(res.boxes)):
                cls_id = int(res.boxes.cls[i].item())
                conf = float(res.boxes.conf[i].item())
                cls_name = self.model.names.get(cls_id, "")
                indo_name = COCO_INDONESIAN_MAP.get(cls_name, cls_name.capitalize())

                box = res.boxes.xyxy[i].cpu().numpy()
                bx1 = max(0, int(box[0] / scale))
                by1 = max(0, int(box[1] / scale))
                bx2 = min(w - 1, int(box[2] / scale))
                by2 = min(h - 1, int(box[3] / scale))
                bw = max(1, bx2 - bx1)
                bh = max(1, by2 - by1)
                box_area = bw * bh
                canvas_area = h * w
                area_ratio = box_area / max(1, canvas_area)

                obj_info = {
                    "class_name": cls_name,
                    "label_id": indo_name,
                    "confidence": round(conf, 3),
                    "bbox": [bx1, by1, bx2, by2],
                    "area_ratio": round(area_ratio, 3)
                }

                if cls_name == "cell phone":
                    detected_phone.append(obj_info)
                    all_detections.append(obj_info)
                    # Draw Emerald Green box for legitimate phone
                    cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), (16, 185, 129), 3)
                    self._draw_label_box(
                        annotated_img,
                        f"BODI HP: SMARTPHONE ({conf*100:.0f}%)",
                        bx1, by1, bx2, by2,
                        (16, 185, 129)
                    )
                    continue

                # Filter out classes that are not in DISALLOWED_COCO_CLASSES (e.g. knife/scissors false positives on metallic bezels)
                if cls_name not in DISALLOWED_COCO_CLASSES:
                    continue

                # Human presence validation:
                # In 4-side housing photography (top, bottom, left, right), operators physically hold or position
                # the phone on the inspection mat. The operator's hands, sleeves, or upper body are naturally visible
                # in the frame, and will be cleanly eliminated by Stage 1 (Phone Body Localizer & Auto-Cropper).
                # Unless the human subject completely dominates the frame as an obvious portrait/selfie (area_ratio >= 0.70),
                # detected person on 4-side views is classified as the legitimate operator and never rejected.
                is_housing_side = view_side.lower() in ["top", "bottom", "left", "right"]
                is_operator = False

                if cls_name == "person":
                    if is_housing_side and area_ratio < 0.70:
                        is_operator = True
                    elif has_phone and area_ratio < 0.65:
                        is_operator = True

                if is_operator:
                    # Draw professional amber box for operator holding/positioning the smartphone
                    cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), (200, 180, 0), 2)
                    self._draw_label_box(
                        annotated_img,
                        f"OPERATOR / TANGAN ({conf*100:.0f}%)",
                        bx1, by1, bx2, by2,
                        (180, 150, 0)
                    )
                    continue

                # Strict Non-phone object detected!
                detected_non_phone.append(obj_info)
                all_detections.append(obj_info)

                color = GUARDRAIL_COLORS.get(cls_name, (0, 0, 220))
                cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), color, 3)
                self._draw_label_box(
                    annotated_img,
                    f"BUKAN HP: {indo_name.upper()} ({conf*100:.0f}%)",
                    bx1, by1, bx2, by2,
                    color
                )

        # Validation status: invalid if any non-phone object was found
        is_valid = len(detected_non_phone) == 0

        rejection_msg = None
        if not is_valid:
            detected_names = list({d["label_id"] for d in detected_non_phone})
            joined_names = ", ".join(detected_names)
            rejection_msg = (
                f"Citra pada sisi '{view_side.upper()}' terdeteksi memuat objek bukan smartphone "
                f"({joined_names}). Sistem AI Guardrail menolak citra ini demi menjaga integritas data valuasi. "
                f"Harap masukkan ulang foto fisik bodi smartphone yang sah."
            )

        return {
            "is_valid": is_valid,
            "has_phone": has_phone,
            "detected_non_phone": detected_non_phone,
            "detected_phone": detected_phone,
            "all_detections": all_detections,
            "annotated_bgr": annotated_img,
            "rejection_message": rejection_msg
        }

    def validate_views(self, view_images: Dict[str, str]) -> Dict[str, Any]:
        """
        Validates all view images for a unit submission.
        Returns:
            {
                "is_valid": bool,
                "rejected_views": List[str],
                "all_detected_objects": Dict[str, List[Dict]],
                "annotated_previews": Dict[str, np.ndarray],
                "rejection_summary": Optional[str]
            }
        """
        rejected_views = []
        all_detected = {}
        annotated_previews = {}
        rejection_reasons = []

        for side, path in view_images.items():
            if not os.path.exists(path):
                continue
            img = cv2.imread(path)
            if img is None:
                continue

            res = self.validate_single_image(img, view_side=side)
            annotated_previews[side] = res["annotated_bgr"]

            if not res["is_valid"]:
                rejected_views.append(side)
                all_detected[side] = res["detected_non_phone"]
                rejection_reasons.append(res["rejection_message"])

        overall_valid = len(rejected_views) == 0
        summary = None
        if not overall_valid:
            summary = " | ".join(rejection_reasons)

        return {
            "is_valid": overall_valid,
            "rejected_views": rejected_views,
            "all_detected_objects": all_detected,
            "annotated_previews": annotated_previews,
            "rejection_summary": summary
        }
