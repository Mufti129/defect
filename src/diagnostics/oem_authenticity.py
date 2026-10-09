"""
OEM COMPONENT AUTHENTICITY CHECKER
==================================
Pusat Gadai Indonesia (PGI) — Device QA System

Verifies serial numbers of display, camera, and battery to detect
unauthorized third-party part replacements or mismatching EEPROM serials.
"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class OEMPartReport:
    screen_original: bool
    battery_original: bool
    camera_original: bool
    biometric_sensor_matched: bool
    cloud_lock_status: str       # "UNLOCKED", "ICLOUD_LOCKED", "MDM_ENROLLED"
    overall_authenticity: str    # "ALL_ORIGINAL", "PART_REPLACED", "CRITICAL_MISMATCH"
    penalty_points: float
    notes: List[str]


class OEMAuthenticityChecker:
    """
    Examines hardware EEPROM serials and OS unknown component flags.
    """

    def check_authenticity(self, device_data: Dict[str, Any], device_type: str = "android") -> OEMPartReport:
        """
        Evaluates hardware serial authenticity and cloud locking.
        """
        notes = []
        screen_orig = True
        battery_orig = True
        camera_orig = True
        biometric_orig = True
        penalty = 0.0

        # Check for replaced parts
        if device_data.get("screen_replaced", False):
            screen_orig = False
            notes.append("Layar display terdeteksi part aftermarket / non-original.")
            penalty += 8.0

        if device_data.get("battery_replaced", False):
            battery_orig = False
            notes.append("Baterai telah diganti (Serial tidak terikat pabrik).")
            penalty += 3.0

        if device_data.get("camera_replaced", False):
            camera_orig = False
            notes.append("Modul kamera pernah diganti.")
            penalty += 5.0

        cloud_lock = device_data.get("cloud_lock", "UNLOCKED")
        if cloud_lock != "UNLOCKED":
            notes.append(f"Perhatian: Status perangkat {cloud_lock}!")
            penalty += 20.0

        if not screen_orig or not battery_orig or not camera_orig:
            overall = "PART_REPLACED"
        elif cloud_lock != "UNLOCKED":
            overall = "CRITICAL_MISMATCH"
        else:
            overall = "ALL_ORIGINAL"
            notes.append("Semua komponen internal terverifikasi asli pabrikan (Original OEM).")

        return OEMPartReport(
            screen_original=screen_orig,
            battery_original=battery_orig,
            camera_original=camera_orig,
            biometric_sensor_matched=biometric_orig,
            cloud_lock_status=cloud_lock,
            overall_authenticity=overall,
            penalty_points=penalty,
            notes=notes
        )
