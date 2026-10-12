"""
COMMERCIAL SMARTPHONE MODEL LOOKUP DATABASE
===========================================
Pusat Gadai Indonesia & Mufti Computer Vision QA System

Provides official commercial brand, marketing model name, processor (SoC),
and typical memory configurations for 130+ smartphone models prevalent in Indonesia.
Supports exact and fuzzy model code lookups (e.g. CPH2579 -> Oppo A18, SM-A055F -> Samsung Galaxy A05).
"""

from typing import Dict, Any, Optional
import re

COMMERCIAL_DEVICE_DATABASE: Dict[str, Dict[str, Any]] = {
    # --- OPPO ---
    "CPH2579": {"brand": "Oppo", "model": "A18", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 128},
    "CPH2565": {"brand": "Oppo", "model": "A38", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 128},
    "CPH2527": {"brand": "Oppo", "model": "A58 4G", "soc": "MediaTek Helio G85", "ram_gb": 6, "storage_gb": 128},
    "CPH2477": {"brand": "Oppo", "model": "A78 4G", "soc": "Qualcomm Snapdragon 680", "ram_gb": 8, "storage_gb": 256},
    "CPH2483": {"brand": "Oppo", "model": "A78 5G", "soc": "MediaTek Dimensity 700", "ram_gb": 8, "storage_gb": 128},
    "CPH2387": {"brand": "Oppo", "model": "A57", "soc": "MediaTek Helio G35", "ram_gb": 4, "storage_gb": 64},
    "CPH2269": {"brand": "Oppo", "model": "A16", "soc": "MediaTek Helio G35", "ram_gb": 3, "storage_gb": 32},
    "CPH2271": {"brand": "Oppo", "model": "A16e", "soc": "MediaTek Helio P22", "ram_gb": 3, "storage_gb": 32},
    "CPH2185": {"brand": "Oppo", "model": "A15", "soc": "MediaTek Helio P35", "ram_gb": 3, "storage_gb": 32},
    "CPH2179": {"brand": "Oppo", "model": "A15s", "soc": "MediaTek Helio P35", "ram_gb": 4, "storage_gb": 64},
    "CPH2083": {"brand": "Oppo", "model": "A12", "soc": "MediaTek Helio P35", "ram_gb": 3, "storage_gb": 32},
    "CPH2077": {"brand": "Oppo", "model": "A12", "soc": "MediaTek Helio P35", "ram_gb": 4, "storage_gb": 64},
    "CPH1937": {"brand": "Oppo", "model": "A9 (2020)", "soc": "Qualcomm Snapdragon 665", "ram_gb": 8, "storage_gb": 128},
    "CPH1939": {"brand": "Oppo", "model": "A5 (2020)", "soc": "Qualcomm Snapdragon 665", "ram_gb": 3, "storage_gb": 64},
    "CPH1909": {"brand": "Oppo", "model": "A5s", "soc": "MediaTek Helio P35", "ram_gb": 3, "storage_gb": 32},
    "CPH1923": {"brand": "Oppo", "model": "A1k", "soc": "MediaTek Helio P22", "ram_gb": 2, "storage_gb": 32},
    "CPH2219": {"brand": "Oppo", "model": "A74 4G", "soc": "Qualcomm Snapdragon 662", "ram_gb": 6, "storage_gb": 128},
    "CPH2211": {"brand": "Oppo", "model": "A54", "soc": "MediaTek Helio P35", "ram_gb": 4, "storage_gb": 128},
    "CPH2239": {"brand": "Oppo", "model": "A54", "soc": "MediaTek Helio P35", "ram_gb": 6, "storage_gb": 128},
    "CPH2359": {"brand": "Oppo", "model": "Reno8 4G", "soc": "Qualcomm Snapdragon 680", "ram_gb": 8, "storage_gb": 256},
    "CPH2375": {"brand": "Oppo", "model": "Reno8 5G", "soc": "MediaTek Dimensity 1300", "ram_gb": 8, "storage_gb": 256},
    "CPH2457": {"brand": "Oppo", "model": "Reno8 T 4G", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 256},
    "CPH2505": {"brand": "Oppo", "model": "Reno8 T 5G", "soc": "Qualcomm Snapdragon 695", "ram_gb": 8, "storage_gb": 256},
    "CPH2525": {"brand": "Oppo", "model": "Reno10 5G", "soc": "MediaTek Dimensity 7050", "ram_gb": 8, "storage_gb": 256},
    "CPH2531": {"brand": "Oppo", "model": "Reno10 Pro 5G", "soc": "Qualcomm Snapdragon 778G", "ram_gb": 12, "storage_gb": 256},
    "CPH2607": {"brand": "Oppo", "model": "Reno11 5G", "soc": "MediaTek Dimensity 7050", "ram_gb": 8, "storage_gb": 256},
    "CPH2603": {"brand": "Oppo", "model": "Reno11 F 5G", "soc": "MediaTek Dimensity 7050", "ram_gb": 8, "storage_gb": 256},
    "CPH2625": {"brand": "Oppo", "model": "Reno12 5G", "soc": "MediaTek Dimensity 7300-Energy", "ram_gb": 12, "storage_gb": 256},
    "CPH2629": {"brand": "Oppo", "model": "Reno12 F 5G", "soc": "MediaTek Dimensity 6300", "ram_gb": 8, "storage_gb": 256},
    "CPH2307": {"brand": "Oppo", "model": "Find X5 Pro", "soc": "Qualcomm Snapdragon 8 Gen 1", "ram_gb": 12, "storage_gb": 256},

    # --- SAMSUNG ---
    "SM-A032F": {"brand": "Samsung", "model": "Galaxy A03 Core", "soc": "Unisoc SC9863A", "ram_gb": 2, "storage_gb": 32},
    "SM-A035F": {"brand": "Samsung", "model": "Galaxy A03", "soc": "Unisoc T606", "ram_gb": 3, "storage_gb": 32},
    "SM-A042F": {"brand": "Samsung", "model": "Galaxy A04e", "soc": "MediaTek Helio P35", "ram_gb": 3, "storage_gb": 32},
    "SM-A045F": {"brand": "Samsung", "model": "Galaxy A04", "soc": "MediaTek Helio P35", "ram_gb": 4, "storage_gb": 64},
    "SM-A047F": {"brand": "Samsung", "model": "Galaxy A04s", "soc": "Samsung Exynos 850", "ram_gb": 4, "storage_gb": 64},
    "SM-A055F": {"brand": "Samsung", "model": "Galaxy A05", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 64},
    "SM-A057F": {"brand": "Samsung", "model": "Galaxy A05s", "soc": "Qualcomm Snapdragon 680", "ram_gb": 6, "storage_gb": 128},
    "SM-A065F": {"brand": "Samsung", "model": "Galaxy A06", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 64},
    "SM-A135F": {"brand": "Samsung", "model": "Galaxy A13", "soc": "Samsung Exynos 850", "ram_gb": 4, "storage_gb": 128},
    "SM-A145F": {"brand": "Samsung", "model": "Galaxy A14 4G", "soc": "MediaTek Helio G80", "ram_gb": 4, "storage_gb": 128},
    "SM-A146P": {"brand": "Samsung", "model": "Galaxy A14 5G", "soc": "MediaTek Dimensity 700", "ram_gb": 6, "storage_gb": 128},
    "SM-A146M": {"brand": "Samsung", "model": "Galaxy A14 5G", "soc": "Samsung Exynos 1330", "ram_gb": 6, "storage_gb": 128},
    "SM-A155F": {"brand": "Samsung", "model": "Galaxy A15 4G", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 128},
    "SM-A156E": {"brand": "Samsung", "model": "Galaxy A15 5G", "soc": "MediaTek Dimensity 6100+", "ram_gb": 8, "storage_gb": 256},
    "SM-A235F": {"brand": "Samsung", "model": "Galaxy A23", "soc": "Qualcomm Snapdragon 680", "ram_gb": 6, "storage_gb": 128},
    "SM-A245F": {"brand": "Samsung", "model": "Galaxy A24", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 128},
    "SM-A256E": {"brand": "Samsung", "model": "Galaxy A25 5G", "soc": "Samsung Exynos 1280", "ram_gb": 8, "storage_gb": 256},
    "SM-A336B": {"brand": "Samsung", "model": "Galaxy A33 5G", "soc": "Samsung Exynos 1280", "ram_gb": 8, "storage_gb": 128},
    "SM-A346E": {"brand": "Samsung", "model": "Galaxy A34 5G", "soc": "MediaTek Dimensity 1080", "ram_gb": 8, "storage_gb": 128},
    "SM-A356E": {"brand": "Samsung", "model": "Galaxy A35 5G", "soc": "Samsung Exynos 1380", "ram_gb": 8, "storage_gb": 256},
    "SM-A525F": {"brand": "Samsung", "model": "Galaxy A52", "soc": "Qualcomm Snapdragon 720G", "ram_gb": 8, "storage_gb": 128},
    "SM-A528B": {"brand": "Samsung", "model": "Galaxy A52s 5G", "soc": "Qualcomm Snapdragon 778G", "ram_gb": 8, "storage_gb": 256},
    "SM-A536E": {"brand": "Samsung", "model": "Galaxy A53 5G", "soc": "Samsung Exynos 1280", "ram_gb": 8, "storage_gb": 128},
    "SM-A546E": {"brand": "Samsung", "model": "Galaxy A54 5G", "soc": "Samsung Exynos 1380", "ram_gb": 8, "storage_gb": 256},
    "SM-A556E": {"brand": "Samsung", "model": "Galaxy A55 5G", "soc": "Samsung Exynos 1480", "ram_gb": 8, "storage_gb": 256},
    "SM-S901B": {"brand": "Samsung", "model": "Galaxy S22", "soc": "Qualcomm Snapdragon 8 Gen 1", "ram_gb": 8, "storage_gb": 128},
    "SM-S906B": {"brand": "Samsung", "model": "Galaxy S22+", "soc": "Qualcomm Snapdragon 8 Gen 1", "ram_gb": 8, "storage_gb": 256},
    "SM-S908B": {"brand": "Samsung", "model": "Galaxy S22 Ultra", "soc": "Qualcomm Snapdragon 8 Gen 1", "ram_gb": 12, "storage_gb": 256},
    "SM-S911B": {"brand": "Samsung", "model": "Galaxy S23", "soc": "Qualcomm Snapdragon 8 Gen 2 for Galaxy", "ram_gb": 8, "storage_gb": 128},
    "SM-S916B": {"brand": "Samsung", "model": "Galaxy S23+", "soc": "Qualcomm Snapdragon 8 Gen 2 for Galaxy", "ram_gb": 8, "storage_gb": 256},
    "SM-S918B": {"brand": "Samsung", "model": "Galaxy S23 Ultra", "soc": "Qualcomm Snapdragon 8 Gen 2 for Galaxy", "ram_gb": 12, "storage_gb": 256},
    "SM-S711B": {"brand": "Samsung", "model": "Galaxy S23 FE", "soc": "Samsung Exynos 2200", "ram_gb": 8, "storage_gb": 128},
    "SM-S921B": {"brand": "Samsung", "model": "Galaxy S24", "soc": "Samsung Exynos 2400", "ram_gb": 8, "storage_gb": 256},
    "SM-S926B": {"brand": "Samsung", "model": "Galaxy S24+", "soc": "Samsung Exynos 2400", "ram_gb": 12, "storage_gb": 256},
    "SM-S928B": {"brand": "Samsung", "model": "Galaxy S24 Ultra", "soc": "Qualcomm Snapdragon 8 Gen 3 for Galaxy", "ram_gb": 12, "storage_gb": 256},
    "SM-F711B": {"brand": "Samsung", "model": "Galaxy Z Flip3 5G", "soc": "Qualcomm Snapdragon 888", "ram_gb": 8, "storage_gb": 128},
    "SM-F721B": {"brand": "Samsung", "model": "Galaxy Z Flip4", "soc": "Qualcomm Snapdragon 8+ Gen 1", "ram_gb": 8, "storage_gb": 128},
    "SM-F731B": {"brand": "Samsung", "model": "Galaxy Z Flip5", "soc": "Qualcomm Snapdragon 8 Gen 2 for Galaxy", "ram_gb": 8, "storage_gb": 256},
    "SM-F741B": {"brand": "Samsung", "model": "Galaxy Z Flip6", "soc": "Qualcomm Snapdragon 8 Gen 3 for Galaxy", "ram_gb": 12, "storage_gb": 256},
    "SM-F926B": {"brand": "Samsung", "model": "Galaxy Z Fold3 5G", "soc": "Qualcomm Snapdragon 888", "ram_gb": 12, "storage_gb": 256},
    "SM-F936B": {"brand": "Samsung", "model": "Galaxy Z Fold4", "soc": "Qualcomm Snapdragon 8+ Gen 1", "ram_gb": 12, "storage_gb": 256},
    "SM-F946B": {"brand": "Samsung", "model": "Galaxy Z Fold5", "soc": "Qualcomm Snapdragon 8 Gen 2 for Galaxy", "ram_gb": 12, "storage_gb": 256},
    "SM-F956B": {"brand": "Samsung", "model": "Galaxy Z Fold6", "soc": "Qualcomm Snapdragon 8 Gen 3 for Galaxy", "ram_gb": 12, "storage_gb": 256},

    # --- XIAOMI / REDMI / POCO ---
    "23129RAA4G": {"brand": "Xiaomi", "model": "Redmi Note 13 4G", "soc": "Qualcomm Snapdragon 685", "ram_gb": 8, "storage_gb": 128},
    "23117RA68G": {"brand": "Xiaomi", "model": "Redmi Note 13 5G", "soc": "MediaTek Dimensity 6080", "ram_gb": 8, "storage_gb": 256},
    "2312DRA50G": {"brand": "Xiaomi", "model": "Redmi Note 13 Pro 5G", "soc": "Qualcomm Snapdragon 7s Gen 2", "ram_gb": 8, "storage_gb": 256},
    "23090RA98G": {"brand": "Xiaomi", "model": "Redmi Note 13 Pro+ 5G", "soc": "MediaTek Dimensity 7200-Ultra", "ram_gb": 12, "storage_gb": 512},
    "23028RN4DG": {"brand": "Xiaomi", "model": "Redmi 12C", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 64},
    "23053RN02A": {"brand": "Xiaomi", "model": "Redmi 12", "soc": "MediaTek Helio G88", "ram_gb": 8, "storage_gb": 128},
    "23053RN02Y": {"brand": "Xiaomi", "model": "Redmi 12", "soc": "MediaTek Helio G88", "ram_gb": 8, "storage_gb": 256},
    "23108RN04Y": {"brand": "Xiaomi", "model": "Redmi 13C", "soc": "MediaTek Helio G85", "ram_gb": 6, "storage_gb": 128},
    "23106RN0DA": {"brand": "Xiaomi", "model": "Redmi 13C", "soc": "MediaTek Helio G85", "ram_gb": 8, "storage_gb": 256},
    "24040RN64Y": {"brand": "Xiaomi", "model": "Redmi 13", "soc": "MediaTek Helio G91-Ultra", "ram_gb": 8, "storage_gb": 128},
    "2409BRN2CG": {"brand": "Xiaomi", "model": "Redmi 14C", "soc": "MediaTek Helio G81-Ultra", "ram_gb": 6, "storage_gb": 128},
    "2201117TY": {"brand": "Xiaomi", "model": "Redmi Note 11", "soc": "Qualcomm Snapdragon 680", "ram_gb": 4, "storage_gb": 128},
    "2201117TG": {"brand": "Xiaomi", "model": "Redmi Note 11", "soc": "Qualcomm Snapdragon 680", "ram_gb": 6, "storage_gb": 128},
    "2201116TG": {"brand": "Xiaomi", "model": "Redmi Note 11S", "soc": "MediaTek Helio G96", "ram_gb": 8, "storage_gb": 128},
    "22071212AG": {"brand": "Xiaomi", "model": "Redmi Note 11 Pro 5G", "soc": "Qualcomm Snapdragon 695", "ram_gb": 8, "storage_gb": 128},
    "23021RAA2Y": {"brand": "Xiaomi", "model": "Redmi Note 12 4G", "soc": "Qualcomm Snapdragon 685", "ram_gb": 4, "storage_gb": 128},
    "22111317G": {"brand": "Xiaomi", "model": "Redmi Note 12 5G", "soc": "Qualcomm Snapdragon 4 Gen 1", "ram_gb": 6, "storage_gb": 128},
    "22101316G": {"brand": "Xiaomi", "model": "Redmi Note 12 Pro 5G", "soc": "MediaTek Dimensity 1080", "ram_gb": 8, "storage_gb": 256},
    "23049PCD8G": {"brand": "POCO", "model": "POCO X5 5G", "soc": "Qualcomm Snapdragon 695", "ram_gb": 6, "storage_gb": 128},
    "23122PCD1G": {"brand": "POCO", "model": "POCO X6 5G", "soc": "Qualcomm Snapdragon 7s Gen 2", "ram_gb": 12, "storage_gb": 256},
    "2311DRK48G": {"brand": "POCO", "model": "POCO X6 Pro 5G", "soc": "MediaTek Dimensity 8300-Ultra", "ram_gb": 12, "storage_gb": 512},
    "22041216UG": {"brand": "POCO", "model": "POCO F4", "soc": "Qualcomm Snapdragon 870", "ram_gb": 8, "storage_gb": 256},
    "2304FPN6DC": {"brand": "POCO", "model": "POCO F5", "soc": "Qualcomm Snapdragon 7+ Gen 2", "ram_gb": 8, "storage_gb": 256},
    "2304FPN6DG": {"brand": "POCO", "model": "POCO F5", "soc": "Qualcomm Snapdragon 7+ Gen 2", "ram_gb": 12, "storage_gb": 256},
    "24069PC21G": {"brand": "POCO", "model": "POCO F6", "soc": "Qualcomm Snapdragon 8s Gen 3", "ram_gb": 12, "storage_gb": 512},
    "23076PC4BI": {"brand": "POCO", "model": "POCO M6 Pro", "soc": "MediaTek Helio G99-Ultra", "ram_gb": 8, "storage_gb": 256},
    "23076PC4BG": {"brand": "POCO", "model": "POCO M6 Pro", "soc": "MediaTek Helio G99-Ultra", "ram_gb": 8, "storage_gb": 256},
    "22127PC95G": {"brand": "POCO", "model": "POCO C65", "soc": "MediaTek Helio G85", "ram_gb": 6, "storage_gb": 128},

    # --- REALME ---
    "RMX3760": {"brand": "Realme", "model": "C53", "soc": "Unisoc T612", "ram_gb": 6, "storage_gb": 128},
    "RMX3761": {"brand": "Realme", "model": "C53", "soc": "Unisoc T612", "ram_gb": 8, "storage_gb": 256},
    "RMX3710": {"brand": "Realme", "model": "C55", "soc": "MediaTek Helio G88", "ram_gb": 6, "storage_gb": 128},
    "RMX3834": {"brand": "Realme", "model": "12 5G", "soc": "MediaTek Dimensity 6100+", "ram_gb": 8, "storage_gb": 256},
    "RMX3840": {"brand": "Realme", "model": "12 Pro+ 5G", "soc": "Qualcomm Snapdragon 7s Gen 2", "ram_gb": 8, "storage_gb": 256},
    "RMX3842": {"brand": "Realme", "model": "12+ 5G", "soc": "MediaTek Dimensity 7050", "ram_gb": 8, "storage_gb": 256},
    "RMX3630": {"brand": "Realme", "model": "10", "soc": "MediaTek Helio G99", "ram_gb": 4, "storage_gb": 128},
    "RMX3686": {"brand": "Realme", "model": "10 Pro 5G", "soc": "Qualcomm Snapdragon 695", "ram_gb": 8, "storage_gb": 128},
    "RMX3687": {"brand": "Realme", "model": "10 Pro+ 5G", "soc": "MediaTek Dimensity 1080", "ram_gb": 8, "storage_gb": 128},
    "RMX3511": {"brand": "Realme", "model": "C35", "soc": "Unisoc T616", "ram_gb": 4, "storage_gb": 64},
    "RMX3501": {"brand": "Realme", "model": "C31", "soc": "Unisoc T612", "ram_gb": 3, "storage_gb": 32},
    "RMX3261": {"brand": "Realme", "model": "C21Y", "soc": "Unisoc T610", "ram_gb": 3, "storage_gb": 32},
    "RMX3263": {"brand": "Realme", "model": "C21Y", "soc": "Unisoc T610", "ram_gb": 4, "storage_gb": 64},
    "RMX3201": {"brand": "Realme", "model": "C25", "soc": "MediaTek Helio G70", "ram_gb": 4, "storage_gb": 64},
    "RMX3191": {"brand": "Realme", "model": "C25s", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 128},
    "RMX3231": {"brand": "Realme", "model": "C11 (2021)", "soc": "Unisoc SC9863A", "ram_gb": 2, "storage_gb": 32},
    "RMX2185": {"brand": "Realme", "model": "C11 (2020)", "soc": "MediaTek Helio G35", "ram_gb": 2, "storage_gb": 32},
    "RMX2195": {"brand": "Realme", "model": "C15", "soc": "MediaTek Helio G35", "ram_gb": 3, "storage_gb": 64},
    "RMX3706": {"brand": "Realme", "model": "GT Neo 3", "soc": "MediaTek Dimensity 8100", "ram_gb": 8, "storage_gb": 256},
    "RMX3850": {"brand": "Realme", "model": "GT 6", "soc": "Qualcomm Snapdragon 8s Gen 3", "ram_gb": 12, "storage_gb": 256},

    # --- VIVO ---
    "V2310": {"brand": "Vivo", "model": "Y27 5G", "soc": "MediaTek Dimensity 6020", "ram_gb": 6, "storage_gb": 128},
    "V2249": {"brand": "Vivo", "model": "Y27 4G", "soc": "MediaTek Helio G85", "ram_gb": 6, "storage_gb": 128},
    "V2322": {"brand": "Vivo", "model": "Y28", "soc": "MediaTek Helio G85", "ram_gb": 6, "storage_gb": 128},
    "V2324": {"brand": "Vivo", "model": "Y28", "soc": "MediaTek Helio G85", "ram_gb": 8, "storage_gb": 128},
    "V2303": {"brand": "Vivo", "model": "V29 5G", "soc": "Qualcomm Snapdragon 778G", "ram_gb": 8, "storage_gb": 256},
    "V2318": {"brand": "Vivo", "model": "V29e", "soc": "Qualcomm Snapdragon 695", "ram_gb": 8, "storage_gb": 256},
    "V2344": {"brand": "Vivo", "model": "V30 5G", "soc": "Qualcomm Snapdragon 7 Gen 3", "ram_gb": 8, "storage_gb": 256},
    "V2343": {"brand": "Vivo", "model": "V30e", "soc": "Qualcomm Snapdragon 6 Gen 1", "ram_gb": 8, "storage_gb": 128},
    "V2359": {"brand": "Vivo", "model": "V40 5G", "soc": "Qualcomm Snapdragon 7 Gen 3", "ram_gb": 8, "storage_gb": 256},
    "V2250": {"brand": "Vivo", "model": "V27 5G", "soc": "MediaTek Dimensity 7200", "ram_gb": 8, "storage_gb": 256},
    "V2246": {"brand": "Vivo", "model": "V27e", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 256},
    "V2201": {"brand": "Vivo", "model": "V25 5G", "soc": "MediaTek Dimensity 900", "ram_gb": 8, "storage_gb": 256},
    "V2202": {"brand": "Vivo", "model": "V25e", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 128},
    "V2144": {"brand": "Vivo", "model": "T1 5G", "soc": "MediaTek Dimensity 810", "ram_gb": 4, "storage_gb": 128},
    "V2145": {"brand": "Vivo", "model": "T1 Pro 5G", "soc": "Qualcomm Snapdragon 778G", "ram_gb": 8, "storage_gb": 128},
    "V2158": {"brand": "Vivo", "model": "Y02", "soc": "MediaTek Helio P22", "ram_gb": 3, "storage_gb": 32},
    "V2236": {"brand": "Vivo", "model": "Y02t", "soc": "MediaTek Helio P35", "ram_gb": 4, "storage_gb": 64},
    "V2333": {"brand": "Vivo", "model": "Y03", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 64},
    "V2120": {"brand": "Vivo", "model": "Y15s", "soc": "MediaTek Helio P35", "ram_gb": 3, "storage_gb": 32},
    "V2147": {"brand": "Vivo", "model": "Y16", "soc": "MediaTek Helio P35", "ram_gb": 3, "storage_gb": 32},
    "V2237": {"brand": "Vivo", "model": "Y17s", "soc": "MediaTek Helio G85", "ram_gb": 4, "storage_gb": 64},
    "V2111": {"brand": "Vivo", "model": "Y21", "soc": "MediaTek Helio P35", "ram_gb": 4, "storage_gb": 64},
    "V2156": {"brand": "Vivo", "model": "Y33s", "soc": "MediaTek Helio G80", "ram_gb": 8, "storage_gb": 128},
    "V2142": {"brand": "Vivo", "model": "Y35", "soc": "Qualcomm Snapdragon 680", "ram_gb": 8, "storage_gb": 128},
    "V2252": {"brand": "Vivo", "model": "Y36", "soc": "Qualcomm Snapdragon 680", "ram_gb": 8, "storage_gb": 256},
    "V2043": {"brand": "Vivo", "model": "Y20", "soc": "Qualcomm Snapdragon 460", "ram_gb": 3, "storage_gb": 64},

    # --- INFINIX & TECNO ---
    "X6525": {"brand": "Infinix", "model": "Smart 8", "soc": "Unisoc T606", "ram_gb": 4, "storage_gb": 64},
    "X6515": {"brand": "Infinix", "model": "Smart 7", "soc": "Unisoc SC9863A1", "ram_gb": 3, "storage_gb": 64},
    "X6512": {"brand": "Infinix", "model": "Smart 6", "soc": "Unisoc SC9863A", "ram_gb": 2, "storage_gb": 32},
    "X6831": {"brand": "Infinix", "model": "Hot 30", "soc": "MediaTek Helio G88", "ram_gb": 8, "storage_gb": 128},
    "X6833B": {"brand": "Infinix", "model": "Hot 30i", "soc": "MediaTek Helio G37", "ram_gb": 8, "storage_gb": 128},
    "X6836": {"brand": "Infinix", "model": "Hot 40 Pro", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 256},
    "X6837": {"brand": "Infinix", "model": "Hot 40i", "soc": "Unisoc T606", "ram_gb": 8, "storage_gb": 256},
    "X688B": {"brand": "Infinix", "model": "Hot 10 Play", "soc": "MediaTek Helio G25", "ram_gb": 2, "storage_gb": 32},
    "X6816D": {"brand": "Infinix", "model": "Hot 12 Play", "soc": "Unisoc T610", "ram_gb": 4, "storage_gb": 64},
    "X6817": {"brand": "Infinix", "model": "Hot 20i", "soc": "MediaTek Helio G25", "ram_gb": 4, "storage_gb": 64},
    "X6711": {"brand": "Infinix", "model": "Note 30 5G", "soc": "MediaTek Dimensity 6080", "ram_gb": 8, "storage_gb": 256},
    "X6716B": {"brand": "Infinix", "model": "Note 30 Pro", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 256},
    "X6850": {"brand": "Infinix", "model": "Note 40", "soc": "MediaTek Helio G99 Ultimate", "ram_gb": 8, "storage_gb": 256},
    "X6851": {"brand": "Infinix", "model": "Note 40 Pro", "soc": "MediaTek Helio G99 Ultimate", "ram_gb": 8, "storage_gb": 256},
    "X6853": {"brand": "Infinix", "model": "GT 10 Pro", "soc": "MediaTek Dimensity 8050", "ram_gb": 8, "storage_gb": 256},
    "X6871": {"brand": "Infinix", "model": "GT 20 Pro", "soc": "MediaTek Dimensity 8200 Ultimate", "ram_gb": 12, "storage_gb": 256},
    "KI5Q": {"brand": "Tecno", "model": "Spark 10C", "soc": "Unisoc T606", "ram_gb": 4, "storage_gb": 64},
    "KI7": {"brand": "Tecno", "model": "Spark 10 Pro", "soc": "MediaTek Helio G88", "ram_gb": 8, "storage_gb": 128},
    "BG6": {"brand": "Tecno", "model": "Spark 20", "soc": "MediaTek Helio G85", "ram_gb": 8, "storage_gb": 256},
    "BG7": {"brand": "Tecno", "model": "Spark 20 Pro", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 256},
    "LH8N": {"brand": "Tecno", "model": "Camon 20 Pro", "soc": "MediaTek Helio G99", "ram_gb": 8, "storage_gb": 256},
}


def lookup_commercial_model(raw_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Looks up a device identifier (model code, marketing tag, or user agent snippet)
    against the commercial smartphone database.
    """
    if not raw_identifier:
        return None

    cleaned = str(raw_identifier).strip().upper()

    # 1. Exact match
    if cleaned in COMMERCIAL_DEVICE_DATABASE:
        item = COMMERCIAL_DEVICE_DATABASE[cleaned]
        return {
            "brand": item["brand"],
            "model": item["model"],
            "market_name": f"{item['brand']} {item['model']}",
            "soc": item["soc"],
            "ram_gb": item["ram_gb"],
            "storage_gb": item["storage_gb"],
            "code": cleaned
        }

    # 2. Substring matching
    for code, item in COMMERCIAL_DEVICE_DATABASE.items():
        if code in cleaned:
            return {
                "brand": item["brand"],
                "model": item["model"],
                "market_name": f"{item['brand']} {item['model']}",
                "soc": item["soc"],
                "ram_gb": item["ram_gb"],
                "storage_gb": item["storage_gb"],
                "code": code
            }

    # 3. Regex search for model patterns
    oppo_match = re.search(r"CPH\d{4}", cleaned)
    if oppo_match and oppo_match.group(0) in COMMERCIAL_DEVICE_DATABASE:
        code = oppo_match.group(0)
        item = COMMERCIAL_DEVICE_DATABASE[code]
        return {
            "brand": item["brand"],
            "model": item["model"],
            "market_name": f"{item['brand']} {item['model']}",
            "soc": item["soc"],
            "ram_gb": item["ram_gb"],
            "storage_gb": item["storage_gb"],
            "code": code
        }

    samsung_match = re.search(r"SM-[A-Z0-9]+", cleaned)
    if samsung_match:
        cand = samsung_match.group(0)
        if cand in COMMERCIAL_DEVICE_DATABASE:
            item = COMMERCIAL_DEVICE_DATABASE[cand]
            return {
                "brand": item["brand"],
                "model": item["model"],
                "market_name": f"{item['brand']} {item['model']}",
                "soc": item["soc"],
                "ram_gb": item["ram_gb"],
                "storage_gb": item["storage_gb"],
                "code": cand
            }
        # Base model without regional suffix (e.g. SM-A055F -> SM-A055)
        for code, item in COMMERCIAL_DEVICE_DATABASE.items():
            if code.startswith(cand[:7]):
                return {
                    "brand": item["brand"],
                    "model": item["model"],
                    "market_name": f"{item['brand']} {item['model']}",
                    "soc": item["soc"],
                    "ram_gb": item["ram_gb"],
                    "storage_gb": item["storage_gb"],
                    "code": code
                }

    realme_match = re.search(r"RMX\d{4}", cleaned)
    if realme_match and realme_match.group(0) in COMMERCIAL_DEVICE_DATABASE:
        code = realme_match.group(0)
        item = COMMERCIAL_DEVICE_DATABASE[code]
        return {
            "brand": item["brand"],
            "model": item["model"],
            "market_name": f"{item['brand']} {item['model']}",
            "soc": item["soc"],
            "ram_gb": item["ram_gb"],
            "storage_gb": item["storage_gb"],
            "code": code
        }

    vivo_match = re.search(r"V\d{4}[A-Z]?", cleaned)
    if vivo_match and vivo_match.group(0) in COMMERCIAL_DEVICE_DATABASE:
        code = vivo_match.group(0)
        item = COMMERCIAL_DEVICE_DATABASE[code]
        return {
            "brand": item["brand"],
            "model": item["model"],
            "market_name": f"{item['brand']} {item['model']}",
            "soc": item["soc"],
            "ram_gb": item["ram_gb"],
            "storage_gb": item["storage_gb"],
            "code": code
        }

    return None
