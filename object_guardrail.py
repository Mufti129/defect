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

# Classes that are strictly NON-PHONE objects and must trigger rejection
NON_PHONE_CLASSES = {
    # Humans & Animals
    "person": "Manusia / Orang",
    "cat": "Kucing / Hewan",
    "dog": "Anjing / Hewan",
    "horse": "Hewan",
    "sheep": "Hewan",
    "cow": "Hewan",
    "elephant": "Hewan",
    "bear": "Hewan",
    "zebra": "Hewan",
    "giraffe": "Hewan",
    "bird": "Burung / Hewan",

    # Electronics & Office (Strict Non-phone)
    "laptop": "Komputer Laptop",
    "keyboard": "Keyboard Komputer",
    "mouse": "Mouse Komputer",
    "tv": "Televisi / Monitor",
    "microwave": "Microwave",
    "oven": "Oven",
    "toaster": "Pemanggang Roti",
    "refrigerator": "Kulkas",

    # Containers & Food
    "bottle": "Botol Minuman",
    "wine glass": "Gelas",
    "cup": "Cangkir / Gelas",
    "bowl": "Mangkuk",
    "banana": "Buah Pisang",
    "apple": "Buah Apel",
    "sandwich": "Makanan",
    "orange": "Buah Jeruk",
    "pizza": "Makanan",
    "donut": "Donat",
    "cake": "Kue",

    # Vehicles & Outdoors
    "bicycle": "Sepeda",
    "car": "Mobil",
    "motorcycle": "Sepeda Motor",
    "airplane": "Pesawat",
    "bus": "Bus",
    "train": "Kereta",
    "truck": "Truk",
    "boat": "Perahu",
    "traffic light": "Lampu Lalu Lintas",

    # Nature & Furniture
    "potted plant": "Tanaman / Tumbuhan",
    "chair": "Kursi",
    "couch": "Sofa",
    "bed": "Tempat Tidur",
    "toilet": "Toilet",
    "book": "Buku / Dokumen",
    "vase": "Vas Bunga",
    "teddy bear": "Boneka"
}

# Color palette for guardrail visual annotations (BGR)
GUARDRAIL_COLORS = {
    "person": (0, 0, 230),        # Red
    "laptop": (220, 100, 0),      # Blue
    "bottle": (0, 165, 255),      # Orange
    "potted plant": (50, 180, 50),# Green
    "car": (180, 50, 200),        # Purple
    "animal": (0, 140, 255)       # Amber
}


class ObjectGuardrail:
    """
    Validates user input images using a pre-trained COCO object detector.
    """
    def __init__(self, weights_path: Optional[str] = None):
        if weights_path is None:
            weights_path = str(DEFAULT_COCO_WEIGHTS)

        self.weights_path = weights_path
        self.model = None
        self.device = "cpu"

        try:
            import torch
            self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        except Exception:
            self.device = "cpu"

        if os.path.exists(weights_path):
            try:
                from ultralytics import YOLO
                print(f"[ObjectGuardrail] Loading general object validator: {weights_path} (Device: {self.device})")
                self.model = YOLO(weights_path)
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
        else:
            print(f"[ObjectGuardrail] Weights '{weights_path}' not found. Guardrail running in bypass mode.")

    def validate_single_image(
        self,
        img: np.ndarray,
        view_side: str = "body",
        conf_thresh: float = 0.28
    ) -> Dict[str, Any]:
        """
        Scans a single view image for disallowed non-phone objects.
        Returns:
            {
                "is_valid": bool,
                "detected_non_phone": List[Dict], # [{class, indonesian_label, conf, bbox}]
                "annotated_bgr": np.ndarray,
                "rejection_message": Optional[str]
            }
        """
        if self.model is None or img is None:
            return {
                "is_valid": True,
                "detected_non_phone": [],
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
        has_phone = False
        annotated_img = img.copy()

        # Check first if cell phone is present in any box
        for res in results:
            if res.boxes is not None and len(res.boxes) > 0:
                for i in range(len(res.boxes)):
                    c_name = self.model.names.get(int(res.boxes.cls[i].item()), "")
                    if c_name == "cell phone":
                        has_phone = True
                        break

        for res in results:
            if res.boxes is None or len(res.boxes) == 0:
                continue

            for i in range(len(res.boxes)):
                cls_id = int(res.boxes.cls[i].item())
                conf = float(res.boxes.conf[i].item())
                cls_name = self.model.names.get(cls_id, "")

                if cls_name == "cell phone":
                    continue

                box = res.boxes.xyxy[i].cpu().numpy()
                bx1 = int(box[0] / scale)
                by1 = int(box[1] / scale)
                bx2 = int(box[2] / scale)
                by2 = int(box[3] / scale)
                bw = max(1, bx2 - bx1)
                bh = max(1, by2 - by1)
                box_area = bw * bh
                canvas_area = h * w
                area_ratio = box_area / max(1, canvas_area)

                # For human person:
                # If a phone is present, person is the operator holding the device (handled by HandFilter)
                # If no phone is present, only reject if person is a dominant subject (selfie/portrait: conf >= 0.65 and area_ratio >= 0.40)
                if cls_name == "person":
                    if has_phone or area_ratio < 0.40 or conf < 0.65:
                        continue

                # Check if this object belongs to non-phone category
                if cls_name in NON_PHONE_CLASSES:
                    # Require minimum confidence and minimum area to avoid spurious micro-boxes
                    if conf < 0.35 or area_ratio < 0.05:
                        continue

                    indo_name = NON_PHONE_CLASSES[cls_name]
                    detected_non_phone.append({
                        "class_name": cls_name,
                        "label_id": indo_name,
                        "confidence": round(conf, 3),
                        "bbox": [bx1, by1, bx2, by2],
                        "area_ratio": round(area_ratio, 3)
                    })

                    # Draw prominent rejection annotation on image
                    color = GUARDRAIL_COLORS.get(cls_name, (0, 0, 220))
                    cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), color, 3)
                    
                    label_text = f"BUKAN HP: {indo_name.upper()} ({conf*100:.0f}%)"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                    
                    lbl_y1 = max(0, by1 - th - 12)
                    lbl_y2 = by1
                    cv2.rectangle(annotated_img, (bx1, lbl_y1), (bx1 + tw + 16, lbl_y2), color, -1)
                    cv2.putText(
                        annotated_img,
                        label_text,
                        (bx1 + 8, lbl_y2 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.60,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )

        is_valid = len(detected_non_phone) == 0

        rejection_msg = None
        if not is_valid:
            detected_names = list({d["label_id"] for d in detected_non_phone})
            joined_names = ", ".join(detected_names)
            rejection_msg = (
                f"Citra pada sisi '{view_side.upper()}' terdeteksi memuat objek bukan smartphone "
                f"({joined_names}). Sistem hanya menerima foto fisik bodi ponsel. "
                f"Harap masukkan ulang foto bodi HP yang benar."
            )

        return {
            "is_valid": is_valid,
            "detected_non_phone": detected_non_phone,
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
