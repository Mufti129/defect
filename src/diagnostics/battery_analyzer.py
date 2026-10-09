"""
BATTERY HEALTH & CHARGING SYSTEM ANALYZER
=========================================
Pusat Gadai Indonesia (PGI) — Device QA System

Evaluates battery wear, health percentage, charging current, cycle count,
and temperature thresholds for secondary device grading.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class BatteryReport:
    health_percentage: int
    cycle_count: int
    status: str             # "PASS", "WARNING", "SERVICE_REQUIRED"
    temperature_c: float
    voltage_mv: int
    is_charging: bool
    wear_level: float       # 0.0 (New) to 1.0 (Completely Depleted)
    recommendation: str
    penalty_points: float   # DPI contribution for grading engine

    @property
    def health_pct(self) -> int:
        return self.health_percentage

    @property
    def level_pct(self) -> int:
        return int(self.health_percentage)

    @property
    def wear_level_desc(self) -> str:
        return self.recommendation


class BatteryAnalyzer:
    """
    Evaluates battery performance data against quality assurance grading standards.
    """

    # Industry standard grading thresholds:
    HEALTH_THRESHOLD_PASS = 85.0
    HEALTH_THRESHOLD_WARNING = 80.0
    MAX_NORMAL_CYCLES = 500

    def analyze_battery(self, raw_data: Dict[str, Any], device_type: str = "android") -> BatteryReport:
        """
        Parses raw battery data into a comprehensive diagnostic report.
        """
        if device_type == "ios":
            level = raw_data.get("level", 88)
            cycle_count = raw_data.get("cycle_count", 180)
            health_pct = min(100, max(50, raw_data.get("gas_gauge", 88)))
            temp_c = raw_data.get("temperature_c", 30.5)
            voltage_mv = raw_data.get("voltage_mv", 4120)
            is_charging = raw_data.get("is_charging", False)
        else:
            # Android
            level = raw_data.get("level", 85)
            voltage_mv = raw_data.get("voltage_mv", 4050)
            temp_c = raw_data.get("temperature_c", 32.0)
            is_charging = raw_data.get("is_charging", False)
            # Estimate health from voltage/cycle heuristic if kernel doesn't expose gas gauge
            health_code = raw_data.get("health_code", 2)
            if health_code == 2:
                health_pct = 90
            elif health_code in [3, 4]:
                health_pct = 76
            else:
                health_pct = 82
            cycle_count = raw_data.get("cycle_count", 210)

        wear_level = round(max(0.0, (100.0 - health_pct) / 100.0), 3)

        if health_pct >= self.HEALTH_THRESHOLD_PASS:
            status = "PASS"
            recommendation = "Kondisi baterai prima (Kapasitas di atas 85%). Layak jual Grade A/B."
            penalty_points = 0.0
        elif health_pct >= self.HEALTH_THRESHOLD_WARNING:
            status = "WARNING"
            recommendation = "Kondisi baterai wajar (80% - 84%). Penurunan kapasitas normal pemakaian."
            penalty_points = 2.0
        else:
            status = "SERVICE_REQUIRED"
            recommendation = "Kesehatan baterai di bawah 80%. Direkomendasikan servis penggantian baterai."
            penalty_points = 6.0

        if temp_c > 45.0:
            status = "WARNING"
            recommendation += " Perhatian: Suhu baterai di atas 45°C (Overheating)."
            penalty_points += 3.0

        return BatteryReport(
            health_percentage=int(health_pct),
            cycle_count=int(cycle_count),
            status=status,
            temperature_c=temp_c,
            voltage_mv=voltage_mv,
            is_charging=is_charging,
            wear_level=wear_level,
            recommendation=recommendation,
            penalty_points=penalty_points
        )
