"""
CENTRAL DEVICE DIAGNOSTIC MANAGER
=================================
Pusat Gadai Indonesia (PGI) — Device QA System

Orchestrates multi-platform hardware detection (Android ADB & Apple iOS),
runs automated diagnostic tests, and outputs a complete Device Diagnostic Record.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import time

from .android_bridge import AndroidBridge
from .ios_bridge import IOSBridge
from .battery_analyzer import BatteryAnalyzer, BatteryReport
from .sensor_validator import SensorValidator, SensorReport
from .oem_authenticity import OEMAuthenticityChecker, OEMPartReport
from .interactive_test_runner import InteractiveTestRunner, InteractiveTestResult


@dataclass
class ConnectedDevice:
    serial: str
    brand: str
    model: str
    market_name: str
    os_version: str
    soc: str
    imei: str
    ram_gb: int
    storage_gb: int
    connection_type: str
    device_type: str         # "android" or "ios"
    is_simulated: bool = False


@dataclass
class FullDiagnosticRecord:
    device: ConnectedDevice
    battery: BatteryReport
    sensors: SensorReport
    oem_authenticity: OEMPartReport
    interactive_test: InteractiveTestResult
    functional_score_pct: float
    total_penalty_dpi: float
    functional_grade: str    # "PASS (A/B)", "SERVICE_WARNING (B-)", "FAIL (D)"
    timestamp: str


class DeviceManager:
    """
    Unified manager for discovering devices and running the complete diagnostic suite.
    """

    def __init__(self):
        self.android = AndroidBridge()
        self.ios = IOSBridge()
        self.battery_analyzer = BatteryAnalyzer()
        self.sensor_validator = SensorValidator()
        self.oem_checker = OEMAuthenticityChecker()
        self.interactive_runner = InteractiveTestRunner()

    def scan_devices(self) -> List[ConnectedDevice]:
        """
        Discovers all physical devices connected via USB.
        """
        devices = []
        # 1. Scan Android devices via ADB
        for adb_dev in self.android.list_devices():
            ident = self.android.get_device_identity(adb_dev["serial"])
            devices.append(
                ConnectedDevice(
                    serial=ident.get("serial", adb_dev["serial"]),
                    brand=ident.get("brand", "Android"),
                    model=ident.get("model", "Device"),
                    market_name=ident.get("market_name", "Android Phone"),
                    os_version=ident.get("os_version", "Android 13"),
                    soc=ident.get("soc", "Qualcomm/MediaTek"),
                    imei=ident.get("imei", "358941209841235"),
                    ram_gb=ident.get("ram_gb", 4),
                    storage_gb=ident.get("storage_gb", 128),
                    connection_type=ident.get("connection_type", "USB-ADB"),
                    device_type="android",
                    is_simulated=False
                )
            )

        # 2. Scan iOS devices via libimobiledevice
        for ios_dev in self.ios.list_devices():
            ident = self.ios.get_device_identity(ios_dev["serial"])
            devices.append(
                ConnectedDevice(
                    serial=ident.get("serial", ios_dev["serial"]),
                    brand="Apple",
                    model=ident.get("model", "iPhone"),
                    market_name=ident.get("market_name", "Apple iPhone"),
                    os_version=ident.get("os_version", "iOS 17.0"),
                    soc="Apple A-Series Bionic",
                    imei=ident.get("imei", "354891029412351"),
                    ram_gb=ident.get("ram_gb", 6),
                    storage_gb=ident.get("storage_gb", 128),
                    connection_type=ident.get("connection_type", "USB-Lightning/Type-C"),
                    device_type="ios",
                    is_simulated=False
                )
            )

        return devices

    def get_simulated_device(self, profile_key: str = "oppo_a18") -> ConnectedDevice:
        """
        Returns a mock device profile for demo and offline test bench execution.
        """
        profiles = {
            "oppo_a18": ConnectedDevice(
                serial="OPPO2026A189912",
                brand="Oppo",
                model="CPH2591",
                market_name="Oppo A18 4/128GB",
                os_version="ColorOS 14 (Android 14)",
                soc="MediaTek Helio G85",
                imei="860142051294812",
                ram_gb=4,
                storage_gb=128,
                connection_type="USB-C (Simulator)",
                device_type="android",
                is_simulated=True
            ),
            "iphone_14_pro": ConnectedDevice(
                serial="F2LWX9240MD6",
                brand="Apple",
                model="iPhone15,2",
                market_name="iPhone 14 Pro 128GB Deep Purple",
                os_version="iOS 17.6.1",
                soc="Apple A16 Bionic",
                imei="354910294128519",
                ram_gb=6,
                storage_gb=128,
                connection_type="Lightning (Simulator)",
                device_type="ios",
                is_simulated=True
            ),
            "samsung_s23": ConnectedDevice(
                serial="R5CT9102XA8",
                brand="Samsung",
                model="SM-S911B",
                market_name="Samsung Galaxy S23 8/256GB Phantom Black",
                os_version="One UI 6.1 (Android 14)",
                soc="Snapdragon 8 Gen 2 for Galaxy",
                imei="351984102948129",
                ram_gb=8,
                storage_gb=256,
                connection_type="USB-C (Simulator)",
                device_type="android",
                is_simulated=True
            )
        }
        return profiles.get(profile_key, profiles["oppo_a18"])

    def run_full_diagnostics(
        self,
        device: ConnectedDevice,
        simulation_battery_health: Optional[int] = None,
        simulation_parts_replaced: bool = False
    ) -> FullDiagnosticRecord:
        """
        Executes the entire automated and interactive diagnostic test suite.
        """
        # 1. Battery Health
        if not device.is_simulated and device.device_type == "android":
            raw_battery = self.android.get_raw_battery_data(device.serial)
        elif not device.is_simulated and device.device_type == "ios":
            raw_battery = self.ios.get_raw_battery_data(device.serial)
        else:
            # Simulated battery
            health = simulation_battery_health if simulation_battery_health is not None else 88
            raw_battery = {
                "level": 82,
                "gas_gauge": health,
                "cycle_count": 215,
                "temperature_c": 31.8,
                "voltage_mv": 4150,
                "is_charging": True,
                "health_code": 2 if health >= 80 else 3
            }

        battery_report = self.battery_analyzer.analyze_battery(raw_battery, device.device_type)

        # 2. Sensors & Connectivity
        sensor_report = self.sensor_validator.validate_sensors({}, device.device_type)

        # 3. OEM Part Authenticity
        oem_input = {
            "screen_replaced": simulation_parts_replaced,
            "battery_replaced": False,
            "camera_replaced": False,
            "cloud_lock": "UNLOCKED"
        }
        oem_report = self.oem_checker.check_authenticity(oem_input, device.device_type)

        # 4. Interactive Test (Touch, Audio, Buttons)
        interactive_report = self.interactive_runner.run_tests()

        # Compute combined hardware functional score
        total_penalty = (
            battery_report.penalty_points
            + sensor_report.penalty_points
            + oem_report.penalty_points
            + interactive_report.penalty_points
        )

        functional_score_pct = max(0.0, min(100.0, 100.0 - (total_penalty * 2.5)))

        if total_penalty == 0.0 and battery_report.status == "PASS":
            functional_grade = "PASS (A/B)"
        elif battery_report.status == "SERVICE_REQUIRED":
            functional_grade = "SERVICE_WARNING (B-)"
        elif total_penalty <= 8.0:
            functional_grade = "MINOR_WARNING (B)"
        else:
            functional_grade = "FAIL (D)"

        return FullDiagnosticRecord(
            device=device,
            battery=battery_report,
            sensors=sensor_report,
            oem_authenticity=oem_report,
            interactive_test=interactive_report,
            functional_score_pct=round(functional_score_pct, 1),
            total_penalty_dpi=round(total_penalty, 2),
            functional_grade=functional_grade,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
