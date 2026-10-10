"""
SMARTPHONE INTERNAL HARDWARE & SOFTWARE DIAGNOSTICS
===================================================
Pusat Gadai Indonesia (PGI) — Automated Device QA System

Subsystem for internal smartphone inspection via ADB (Android) and libimobiledevice (iOS).
Evaluates battery health, hardware sensors, connectivity, and component authenticity.
"""

from .device_manager import DeviceManager, ConnectedDevice
from .android_bridge import AndroidBridge
from .ios_bridge import IOSBridge
from .battery_analyzer import BatteryAnalyzer, BatteryReport
from .sensor_validator import SensorValidator, SensorReport
from .oem_authenticity import OEMAuthenticityChecker, OEMPartReport
from .interactive_test_runner import InteractiveTestRunner, InteractiveTestResult
from .usb_detector import USBHardwareDetector, USBHardwareDevice
from .mobile_web_service import (
    MobileDiagnosticWebService,
    get_local_lan_ip,
    set_mobile_session_result,
    get_mobile_session_result,
    generate_qr_for_url
)

__all__ = [
    "DeviceManager",
    "ConnectedDevice",
    "AndroidBridge",
    "IOSBridge",
    "BatteryAnalyzer",
    "BatteryReport",
    "SensorValidator",
    "SensorReport",
    "OEMAuthenticityChecker",
    "OEMPartReport",
    "InteractiveTestRunner",
    "InteractiveTestResult",
    "USBHardwareDetector",
    "USBHardwareDevice",
    "MobileDiagnosticWebService",
    "get_local_lan_ip",
    "set_mobile_session_result",
    "get_mobile_session_result",
    "generate_qr_for_url",
]
