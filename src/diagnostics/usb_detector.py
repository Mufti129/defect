"""
USB HARDWARE AUTO-DETECTOR
==========================
Pusat Gadai Indonesia (PGI) — Device QA System

Plug & Play hardware detection for connected smartphones without requiring
Developer Options or USB Debugging enabled on the device.
Interrogates the host operating system USB subsystem (macOS, Linux, Windows).
"""

import subprocess
import shutil
import re
import json
import platform
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# Known Smartphone Hardware Manufacturer Vendor IDs (USB-IF registered)
SMARTPHONE_VENDOR_MAP: Dict[str, Dict[str, str]] = {
    "0x05ac": {"brand": "Apple", "company": "Apple Inc.", "os": "ios"},
    "0x04e8": {"brand": "Samsung", "company": "Samsung Electronics", "os": "android"},
    "0x22d4": {"brand": "Oppo", "company": "OPPO Mobile Telecommunications", "os": "android"},
    "0x2717": {"brand": "Xiaomi", "company": "Xiaomi Communications", "os": "android"},
    "0x2d95": {"brand": "Vivo", "company": "Vivo Mobile Communication", "os": "android"},
    "0x2a70": {"brand": "Realme", "company": "Realme Chongqing Mobile", "os": "android"},
    "0x18d1": {"brand": "Google", "company": "Google LLC (Pixel)", "os": "android"},
    "0x12d1": {"brand": "Huawei", "company": "Huawei Technologies", "os": "android"},
    "0x22b8": {"brand": "Motorola", "company": "Motorola / Lenovo", "os": "android"},
    "0x1782": {"brand": "Infinix / Tecno", "company": "Transsion Holdings", "os": "android"},
    "0x0e8d": {"brand": "MediaTek / itel", "company": "MediaTek Platform", "os": "android"},
    "0x0fce": {"brand": "Sony", "company": "Sony Mobile", "os": "android"},
    "0x1004": {"brand": "LG", "company": "LG Electronics", "os": "android"},
    "0x2e04": {"brand": "Nokia", "company": "HMD Global", "os": "android"},
}


@dataclass
class USBHardwareDevice:
    """Represents a smartphone detected via raw host USB bus."""
    vendor_name: str
    brand: str
    product_name: str
    vendor_id: str
    product_id: str
    serial_number: str
    device_type: str             # "android" or "ios"
    connection_speed: str        # e.g. "Up to 480 Mb/s"
    is_charging: bool = True
    bus_path: str = ""
    mtp_mode_active: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        prod = self.product_name if self.product_name else "Smartphone Unit"
        return f"[{self.brand.upper()}] {prod} (SN: {self.serial_number[:12]}...)"


class USBHardwareDetector:
    """
    Scans the host system's USB bus controller to detect connected smartphones
    instantaneously without ADB or user-granted permissions.
    """

    def __init__(self):
        self.os_type = platform.system().lower()

    def scan_usb_devices(self) -> List[USBHardwareDevice]:
        """
        Executes native host OS commands to enumerate all physical USB devices.
        Filters for known smartphone vendor identifiers.
        """
        detected: List[USBHardwareDevice] = []

        if self.os_type == "darwin":
            detected = self._scan_macos()
        elif self.os_type == "linux":
            detected = self._scan_linux()
        elif self.os_type == "windows":
            detected = self._scan_windows()

        return detected

    def _scan_macos(self) -> List[USBHardwareDevice]:
        """Enumerates macOS USB buses using system_profiler and ioreg."""
        devices: List[USBHardwareDevice] = []

        # 1. Primary: system_profiler SPUSBDataType in JSON format
        try:
            res = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=4
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                root_items = data.get("SPUSBDataType", [])
                flattened = self._flatten_macos_usb_items(root_items)

                for item in flattened:
                    dev = self._evaluate_usb_item(item)
                    if dev:
                        devices.append(dev)
        except Exception:
            pass

        # 2. Fallback: ioreg registry scan if system_profiler returns empty
        if not devices:
            try:
                res_ioreg = subprocess.run(
                    ["ioreg", "-p", "IOUSB", "-w0", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=4
                )
                if res_ioreg.returncode == 0:
                    devices.extend(self._parse_ioreg_output(res_ioreg.stdout))
            except Exception:
                pass

        return devices

    def _flatten_macos_usb_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recursively extracts all devices from the nested macOS USB tree."""
        flattened: List[Dict[str, Any]] = []
        for it in items:
            flattened.append(it)
            if "_items" in it and isinstance(it["_items"], list):
                flattened.extend(self._flatten_macos_usb_items(it["_items"]))
        return flattened

    def _evaluate_usb_item(self, item: Dict[str, Any]) -> Optional[USBHardwareDevice]:
        """Checks if a USB entity matches any registered smartphone vendor."""
        name = str(item.get("_name", ""))
        vendor_id_raw = str(item.get("vendor_id", "")).lower()
        product_id = str(item.get("product_id", "")).lower()
        serial_num = str(item.get("serial_num", ""))
        speed = str(item.get("speed", "Up to 480 Mb/s"))
        mfr = str(item.get("manufacturer", ""))

        # Normalize vendor_id
        matched_vid_info = None
        for vid, info in SMARTPHONE_VENDOR_MAP.items():
            if vid.lower() in vendor_id_raw or info["brand"].lower() in name.lower() or info["brand"].lower() in mfr.lower():
                matched_vid_info = (vid, info)
                break

        # Also detect generic "iPhone", "iPad", or "Android" in device names
        if not matched_vid_info:
            if "iphone" in name.lower():
                matched_vid_info = ("0x05ac", SMARTPHONE_VENDOR_MAP["0x05ac"])
            elif "samsung" in name.lower() or "galaxy" in name.lower():
                matched_vid_info = ("0x04e8", SMARTPHONE_VENDOR_MAP["0x04e8"])
            elif "oppo" in name.lower():
                matched_vid_info = ("0x22d4", SMARTPHONE_VENDOR_MAP["0x22d4"])
            elif "xiaomi" in name.lower() or "redmi" in name.lower() or "poco" in name.lower():
                matched_vid_info = ("0x2717", SMARTPHONE_VENDOR_MAP["0x2717"])
            elif "vivo" in name.lower():
                matched_vid_info = ("0x2d95", SMARTPHONE_VENDOR_MAP["0x2d95"])
            elif "realme" in name.lower():
                matched_vid_info = ("0x2a70", SMARTPHONE_VENDOR_MAP["0x2a70"])

        if matched_vid_info:
            vid_key, info = matched_vid_info
            return USBHardwareDevice(
                vendor_name=info["company"],
                brand=info["brand"],
                product_name=name if name else f"{info['brand']} Device",
                vendor_id=vid_key,
                product_id=product_id if product_id else "0x0001",
                serial_number=serial_num if serial_num else f"USB-{vid_key[2:]}-{int(abs(hash(name)) % 1000000):06d}",
                device_type=info["os"],
                connection_speed=speed,
                is_charging=True,
                mtp_mode_active="mtp" in name.lower() or "file" in name.lower(),
                details=item
            )
        return None

    def _parse_ioreg_output(self, output: str) -> List[USBHardwareDevice]:
        """Fallback parser for raw ioreg text output."""
        devices: List[USBHardwareDevice] = []
        blocks = output.split("+-o ")
        for block in blocks:
            name_line = block.splitlines()[0] if block.splitlines() else ""
            vid_match = re.search(r'"idVendor"\s*=\s*(\d+)', block)
            pid_match = re.search(r'"idProduct"\s*=\s*(\d+)', block)
            serial_match = re.search(r'"kUSBSerialNumberString"\s*=\s*"([^"]+)"', block)

            if vid_match:
                vid_hex = f"0x{int(vid_match.group(1)):04x}"
                if vid_hex in SMARTPHONE_VENDOR_MAP:
                    info = SMARTPHONE_VENDOR_MAP[vid_hex]
                    sn = serial_match.group(1) if serial_match else f"USB-{vid_hex[2:]}-890123"
                    devices.append(USBHardwareDevice(
                        vendor_name=info["company"],
                        brand=info["brand"],
                        product_name=name_line.split("@")[0].strip(),
                        vendor_id=vid_hex,
                        product_id=f"0x{int(pid_match.group(1)):04x}" if pid_match else "0x0000",
                        serial_number=sn,
                        device_type=info["os"],
                        connection_speed="480 Mb/s (High-Speed)",
                        is_charging=True
                    ))
        return devices

    def _scan_linux(self) -> List[USBHardwareDevice]:
        """Enumerates Linux USB devices via lsusb."""
        devices: List[USBHardwareDevice] = []
        lsusb = shutil.which("lsusb")
        if not lsusb:
            return devices
        try:
            res = subprocess.run([lsusb], capture_output=True, text=True, timeout=3)
            for line in res.stdout.splitlines():
                m = re.search(r"ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)", line)
                if m:
                    vid = f"0x{m.group(1).lower()}"
                    pid = f"0x{m.group(2).lower()}"
                    desc = m.group(3).strip()
                    if vid in SMARTPHONE_VENDOR_MAP:
                        info = SMARTPHONE_VENDOR_MAP[vid]
                        devices.append(USBHardwareDevice(
                            vendor_name=info["company"],
                            brand=info["brand"],
                            product_name=desc if desc else f"{info['brand']} Device",
                            vendor_id=vid,
                            product_id=pid,
                            serial_number=f"USB-{vid[2:]}-{pid[2:]}",
                            device_type=info["os"],
                            connection_speed="High-Speed USB 2.0"
                        ))
        except Exception:
            pass
        return devices

    def _scan_windows(self) -> List[USBHardwareDevice]:
        """Stub for Windows PnP query if run on Windows server."""
        return []

    def get_simulated_plugged_device(self, profile: str = "oppo_a18") -> USBHardwareDevice:
        """
        Provides realistic Plug & Play USB descriptor simulation for testing
        and demonstration without a physical phone plugged into the USB port.
        """
        profiles = {
            "oppo_a18": USBHardwareDevice(
                vendor_name="OPPO Mobile Telecommunications Corp., Ltd.",
                brand="Oppo",
                product_name="OPPO A18 4/128GB (CPH2591)",
                vendor_id="0x22d4",
                product_id="0x7680",
                serial_number="OPPO259188201948",
                device_type="android",
                connection_speed="480 Mb/s (High Speed USB 2.0)",
                is_charging=True,
                mtp_mode_active=True,
                details={"capacity_gb": 128, "bus_power_ma": 500}
            ),
            "samsung_s23": USBHardwareDevice(
                vendor_name="Samsung Electronics Co., Ltd.",
                brand="Samsung",
                product_name="Samsung Galaxy S23 5G (SM-S911B)",
                vendor_id="0x04e8",
                product_id="0x6860",
                serial_number="R5CW200P98J",
                device_type="android",
                connection_speed="5000 Mb/s (SuperSpeed USB 3.2)",
                is_charging=True,
                mtp_mode_active=True,
                details={"capacity_gb": 256, "bus_power_ma": 900}
            ),
            "iphone_14_pro": USBHardwareDevice(
                vendor_name="Apple Inc.",
                brand="Apple",
                product_name="Apple iPhone 14 Pro 128GB (A2890)",
                vendor_id="0x05ac",
                product_id="0x12a8",
                serial_number="F2LL8190MD6R",
                device_type="ios",
                connection_speed="480 Mb/s (Lightning USB)",
                is_charging=True,
                mtp_mode_active=False,
                details={"capacity_gb": 128, "bus_power_ma": 500}
            )
        }
        return profiles.get(profile, profiles["oppo_a18"])
