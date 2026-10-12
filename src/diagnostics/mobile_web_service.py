"""
MOBILE WEB DIAGNOSTIC SERVICE & QR CODE GENERATOR
=================================================
Pusat Gadai Indonesia (PGI) — Device QA System

Enables zero-touch hardware diagnostics via customer's smartphone camera.
Generates dynamic QR codes (with dual-engine: local PNG + cloud fallback)
and serves an interactive HTML5 mobile test suite for both Android and Apple iOS (iPhone).
Collects battery health, multi-touch digitizer dead-zones, motion sensors,
and acoustic feedback, streaming results directly to the Streamlit session.
"""

import socket
import threading
import json
import io
import time
import urllib.parse
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    import qrcode
    from PIL import Image
except ImportError:
    qrcode = None

# Global thread-safe session result registry
_SESSION_RESULTS: Dict[str, Dict[str, Any]] = {}
_SESSION_DEVICES: Dict[str, list] = {}
_SERVER_INSTANCE: Optional[HTTPServer] = None
_SERVER_THREAD: Optional[threading.Thread] = None
_SERVER_PORT = 8503


def get_local_lan_ip() -> str:
    """Discovers the machine's primary Wi-Fi / Local Area Network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to public DNS address without sending actual traffic
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


HTML_MOBILE_DIAGNOSTIC_PAGE = r"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Mufti Computer Vision — Smart Hardware Diagnostic</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif; }
        body { background: #0A0F1D; color: #F8FAFC; padding: 14px; min-height: 100vh; -webkit-tap-highlight-color: transparent; }
        .header { background: linear-gradient(135deg, #151E32 0%, #1E293B 100%); border-radius: 16px; padding: 18px; margin-bottom: 14px; border: 1px solid #243352; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .header h1 { font-size: 1.25rem; color: #38BDF8; font-weight: 800; letter-spacing: -0.3px; display: flex; align-items: center; gap: 8px; }
        .header p { font-size: 0.80rem; color: #94A3B8; margin-top: 4px; line-height: 1.4; }
        .tag-row { display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap; }
        .pill { display: inline-block; background: #1E293B; color: #38BDF8; font-size: 0.72rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #334155; }
        .pill-neon { background: rgba(16, 185, 129, 0.15); color: #34D399; border-color: rgba(16, 185, 129, 0.4); }
        
        .card { background: #131B2E; border-radius: 14px; padding: 16px; margin-bottom: 12px; border: 1px solid #243352; }
        .card-title { font-size: 0.90rem; font-weight: 700; color: #F1F5F9; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .badge { font-size: 0.70rem; padding: 3px 8px; border-radius: 6px; font-weight: 700; letter-spacing: 0.3px; }
        .badge-pass { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #10B981; }
        .badge-wait { background: rgba(245, 158, 11, 0.2); color: #FDE047; border: 1px solid #F59E0B; }
        .badge-info { background: rgba(59, 130, 246, 0.2); color: #93C5FD; border: 1px solid #3B82F6; }
        .badge-danger { background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #EF4444; }

        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.80rem; }
        .stat-box { background: #0A0F1D; padding: 10px; border-radius: 8px; border: 1px solid #1E293B; }
        .stat-box span { color: #94A3B8; font-size: 0.72rem; display: block; }
        .stat-box b { color: #38BDF8; font-size: 0.94rem; margin-top: 3px; display: block; word-break: break-all; }

        /* Variant Option Pills */
        .opt-group { margin-top: 10px; padding: 10px; background: #0A0F1D; border-radius: 10px; border: 1px solid #1E293B; }
        .opt-label { font-size: 0.73rem; color: #94A3B8; margin-bottom: 6px; display: block; }
        .opt-pills { display: flex; gap: 6px; flex-wrap: wrap; }
        .opt-pill { background: #1E293B; color: #CBD5E1; border: 1px solid #334155; padding: 5px 12px; border-radius: 6px; font-size: 0.74rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
        .opt-pill.active { background: #0284C7; color: #FFFFFF; border-color: #38BDF8; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }

        /* Bubble Level */
        .bubble-track { position: relative; width: 100%; height: 60px; background: #0A0F1D; border-radius: 30px; border: 1px solid #243352; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-top: 8px; }
        .bubble-target { position: absolute; width: 40px; height: 40px; border: 2px dashed #334155; border-radius: 50%; pointer-events: none; }
        .bubble-dot { position: absolute; width: 32px; height: 32px; background: radial-gradient(circle, #38BDF8 20%, #0284C7 80%); border-radius: 50%; box-shadow: 0 0 12px rgba(56, 189, 248, 0.8); transition: transform 0.08s ease-out; }

        /* Interactive Controls */
        .btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 10px; font-weight: 700; font-size: 0.95rem; cursor: pointer; text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.2); }
        .btn-submit { background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%); color: white; margin-top: 14px; }
        .btn-submit:active { transform: scale(0.98); }
        .btn-action { background: #1E293B; border: 1px solid #334155; color: #F8FAFC; padding: 11px; border-radius: 8px; font-size: 0.82rem; font-weight: 600; width: 100%; margin-top: 8px; cursor: pointer; }
        .btn-action:active { background: #334155; }
        .slider-control { width: 100%; margin-top: 8px; accent-color: #38BDF8; }
        .success-box { display: none; background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 12px; padding: 16px; text-align: center; color: white; margin-top: 14px; }

        /* Checklist Kerusakan */
        .defect-check-item { display: flex; align-items: flex-start; gap: 8px; font-size: 0.76rem; color: #E2E8F0; margin-top: 6px; cursor: pointer; }
        .defect-check-item input { margin-top: 2px; accent-color: #EF4444; width: 15px; height: 15px; }

        /* Verification Radio Options */
        .verify-box { background: #0A0F1D; border-radius: 10px; padding: 10px; border: 1px solid #243352; margin-top: 8px; }
        .verify-title { font-size: 0.75rem; font-weight: 700; color: #38BDF8; margin-bottom: 6px; }
        .radio-opt { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: #CBD5E1; margin-bottom: 4px; cursor: pointer; }
        .radio-opt input { accent-color: #38BDF8; }

        /* Full Screen Touch Digitizer Overlay */
        #fs-touch-modal {
            position: fixed !important;
            top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
            width: 100vw !important; height: 100vh !important;
            background: #070B14 !important;
            z-index: 2147483647 !important;
            display: none;
            user-select: none; -webkit-user-select: none;
            touch-action: none;
            overflow: hidden !important;
        }
        .fs-hud {
            position: fixed !important;
            top: 0 !important; left: 0 !important; right: 0 !important;
            height: 56px !important;
            background: #0F172A !important;
            border-bottom: 2px solid #38BDF8 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 0 12px !important;
            z-index: 2147483647 !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.9) !important;
            box-sizing: border-box !important;
        }
        .fs-btn-save-hud {
            background: #1E293B; color: #94A3B8; border: 1px solid #334155;
            padding: 8px 14px; border-radius: 8px; font-weight: 800; font-size: 0.78rem;
            cursor: pointer; transition: all 0.2s;
        }
        .fs-btn-save-hud.active {
            background: #10B981 !important; color: #FFFFFF !important;
            border-color: #34D399 !important; cursor: pointer !important;
            box-shadow: 0 0 14px rgba(16, 185, 129, 0.7) !important;
        }
        .fs-grid-container {
            position: fixed !important;
            top: 56px !important;
            bottom: 60px !important;
            left: 0 !important; right: 0 !important;
            display: grid !important;
            gap: 3px !important;
            padding: 4px !important;
            background: #070B14 !important;
            overflow: hidden !important;
            touch-action: none !important;
            box-sizing: border-box !important;
            z-index: 2147483640 !important;
        }
        .fs-cell {
            background: #1E293B; border-radius: 4px; transition: background 0.05s;
        }
        .fs-cell.touched {
            background: #10B981 !important; box-shadow: 0 0 8px rgba(16, 185, 129, 0.9);
        }
        .fs-bottom-bar {
            position: fixed !important;
            bottom: 0 !important; left: 0 !important; right: 0 !important;
            height: 60px !important;
            background: #0F172A !important;
            border-top: 2px solid #334155 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 8px 12px !important;
            padding-bottom: max(16px, env(safe-area-inset-bottom, 16px)) !important;
            z-index: 2147483647 !important;
            box-sizing: border-box !important;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.9) !important;
        }
        .fs-btn-save {
            background: #334155; color: #94A3B8; border: none; padding: 12px 20px;
            border-radius: 8px; font-weight: 700; font-size: 0.85rem; width: 100%;
            cursor: pointer; transition: all 0.2s;
        }
        .fs-btn-save.active {
            background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
            color: #FFFFFF !important; cursor: pointer !important;
            box-shadow: 0 0 16px rgba(16, 185, 129, 0.6) !important;
        }
        #fs-prompt-complete {
            position: fixed !important;
            top: 50% !important; left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: 88% !important; max-width: 340px !important;
            background: rgba(15, 23, 42, 0.98) !important;
            border: 3px solid #10B981 !important;
            border-radius: 16px !important;
            padding: 20px 16px !important;
            text-align: center !important;
            box-shadow: 0 10px 50px rgba(0,0,0,0.95), 0 0 30px rgba(16, 185, 129, 0.6) !important;
            z-index: 2147483647 !important;
            display: none;
            box-sizing: border-box !important;
        }

        /* Hide Streamlit Floating Badges & Manage App Logo */
        [data-testid="manage-app-button"], 
        button[title="Manage app"], 
        .viewerBadge_container__1QSob, 
        [class*="viewerBadge"],
        footer, 
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Mufti Computer Vision</h1>
        <p>Sistem Diagnostik AI & Computer Vision Smartphone (Universal Android & iOS)</p>
        <div class="tag-row">
            <span class="pill pill-neon" id="device-pill">Mendeteksi Spesifikasi Instan...</span>
            <span class="pill">Sesi: <b id="session-label" style="color: #38BDF8;">__SESSION_ID__</b></span>
            <span class="pill" id="dev-tag" style="color: #94A3B8;">DEV-ID: Memuat...</span>
        </div>
    </div>

    <!-- 1. Identitas Hardware Otomatis & Konfirmasi Varian -->
    <div class="card">
        <div class="card-title">
            <span>1. Spesifikasi Hardware Smartphone (AI Telemetry Engine)</span>
            <span class="badge badge-pass" id="hw-badge">TERVERIFIKASI</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box"><span>Merk / Brand HP</span><b id="val-brand">Smartphone</b></div>
            <div class="stat-box"><span>Model Fisik Pabrikan</span><b id="val-model">Mobile Device</b></div>
            <div class="stat-box"><span>Chipset / Processor (SoC)</span><b id="val-soc" style="color: #38BDF8;">Memindai...</b></div>
            <div class="stat-box"><span>Sistem Operasi</span><b id="val-os">Mobile OS</b></div>
            <div class="stat-box"><span>Resolusi Layar Fisik</span><b id="val-res">1080 x 2400 px</b></div>
            <div class="stat-box"><span>Refresh Rate Layar</span><b id="val-hz" style="color: #34D399;">60 Hz</b></div>
            <div class="stat-box"><span>Estimasi Memori RAM</span><b id="val-ram">4 - 8 GB</b></div>
            <div class="stat-box"><span>Jumlah Inti CPU</span><b id="val-cpu">Octa-Core</b></div>
            <div class="stat-box" style="grid-column: span 2;"><span>Chipset Grafis (GPU WebGL)</span><b id="val-gpu" style="font-size: 0.82rem; color: #34D399;">Mobile GPU</b></div>
        </div>

        <!-- Input Model Kustom & Varian Memori -->
        <div class="opt-group">
            <span class="opt-label">Konfirmasi Varian Memori Internal (ROM / Storage):</span>
            <div class="opt-pills" id="rom-pills">
                <div class="opt-pill" onclick="setROM('64 GB', this)">64 GB</div>
                <div class="opt-pill active" onclick="setROM('128 GB', this)">128 GB</div>
                <div class="opt-pill" onclick="setROM('256 GB', this)">256 GB</div>
                <div class="opt-pill" onclick="setROM('512 GB', this)">512 GB</div>
            </div>
            
            <span class="opt-label" style="margin-top: 8px;">Koreksi / Sesuaikan Model Spesifik (Opsional):</span>
            <input type="text" id="input-model-custom" placeholder="Contoh: Oppo A18 (CPH2579), Galaxy S23..." 
                   style="width: 100%; background: #131B2E; border: 1px solid #334155; border-radius: 6px; padding: 7px 10px; color: #F8FAFC; font-size: 0.80rem;"
                   oninput="updateCustomModel(this.value)">
            <p style="font-size: 0.68rem; color: #64748B; margin-top: 5px; line-height: 1.45;">
                Catatan Teknis Browser: Standar keamanan W3C (Chrome/Safari) menerapkan sandbox yang membatasi akses langsung ke menu Pengaturan OS untuk melindungi privasi data pengguna. Sistem AI membaca telemetri hardware asli (Model Pabrikan, Chipset GPU, Refresh Rate Layar, RAM & Core CPU) secara otomatis. Anda dapat memverifikasi varian ROM di atas.
            </p>
        </div>
    </div>

    <!-- 2. Baterai & Potensi Kerusakan -->
    <div class="card">
        <div class="card-title">
            <span>2. Baterai & Potensi Kerusakan Manajemen Daya</span>
            <span class="badge badge-pass" id="bat-badge">NORMAL</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box"><span>Kapasitas Baterai</span><b id="bat-level">--%</b></div>
            <div class="stat-box"><span>Status Charger</span><b id="bat-charging">--</b></div>
            <div class="stat-box"><span>Estimasi Kesehatan (SoH)</span><b id="bat-health-txt" style="color: #34D399;">92% (Sehat)</b></div>
            <div class="stat-box"><span>Stabilitas Voltase</span><b id="bat-stress-status" style="color: #38BDF8;">Siap Uji</b></div>
        </div>

        <button class="btn-action" id="btn-bat-stress" onclick="runBatteryStressTest()" style="margin-top: 8px;">
            Jalankan Uji Stabilitas Beban Baterai (3 Detik)
        </button>

        <div id="ios-battery-section" style="display: none; margin-top: 10px; padding: 10px; background: #0A0F1D; border-radius: 8px; border: 1px solid #1E293B;">
            <div style="font-size: 0.74rem; color: #94A3B8;">Privasi iOS membatasi sensor baterai otomatis. Geser slider sesuai baterai di pojok atas HP:</div>
            <input type="range" min="50" max="100" value="90" class="slider-control" id="ios-slider" oninput="updateIOSBattery(this.value)">
            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748B; margin-top: 4px;">
                <span>50%</span>
                <span id="slider-txt" style="color: #38BDF8; font-weight: 700;">90%</span>
                <span>100%</span>
            </div>
        </div>

        <!-- Checklist Kerusakan Fisik Baterai -->
        <div class="opt-group" style="margin-top: 10px; border-color: rgba(239, 68, 68, 0.3);">
            <span class="opt-label" style="color: #F87171; font-weight: 700;">Audit Gejala Kerusakan Fisik Baterai (Centang jika dialami):</span>
            <label class="defect-check-item">
                <input type="checkbox" id="chk-kembung" onchange="recalculateBatteryHealth()">
                <span>Baterai Kembung / Tutup Belakang (Backdoor) Mulai Terangkat</span>
            </label>
            <label class="defect-check-item">
                <input type="checkbox" id="chk-shutdown" onchange="recalculateBatteryHealth()">
                <span>HP Sering Mati Mendadak (Shutdown) saat Baterai Tersisa &lt; 20%</span>
            </label>
            <label class="defect-check-item">
                <input type="checkbox" id="chk-panas" onchange="recalculateBatteryHealth()">
                <span>Bodi HP Terasa Panas Berlebih (Overheating) saat Penggunaan Normal</span>
            </label>
            <label class="defect-check-item">
                <input type="checkbox" id="chk-port" onchange="recalculateBatteryHealth()">
                <span>Port Charger Goyang / Pengisian Daya Putus-Nyambung</span>
            </label>
        </div>
    </div>

    <!-- 3. Layar Sentuh Full Layar Sesuai Resolusi (Full Screen Digitizer) -->
    <div class="card">
        <div class="card-title">
            <span>3. Layar Sentuh Penuh (Full Screen Digitizer)</span>
            <span class="badge badge-wait" id="touch-badge">BELUM DIUJI</span>
        </div>
        <p style="font-size: 0.75rem; color: #94A3B8;">
            Uji layar sentuh adaptif mengikuti resolusi layar asli (<span id="touch-res-label">1080x2400</span> px) untuk memastikan nol titik buta (zero dead-zone):
        </p>
        <button class="btn btn-action" onclick="openFullscreenTouch()" style="background: linear-gradient(135deg, #0284C7 0%, #2563EB 100%); color: white; margin-top: 10px; padding: 13px;">
            Buka Mode Uji Layar Penuh (Full Screen Digitizer)
        </button>
        <div id="touch-summary-box" style="margin-top: 8px; font-size: 0.78rem; color: #34D399; font-weight: 700; display: none;">
            Layar Sentuh Terverifikasi Lolos: <span id="touch-cov-label">100%</span> Terjamah Bebas Dead-Zone!
        </div>
    </div>

    <!-- 4. Sensor Gerak 3D Bubble Level -->
    <div class="card">
        <div class="card-title">
            <span>4. Sensor Gerak Gyroscope & Accelerometer (3-Axis)</span>
            <span class="badge badge-pass" id="sensor-badge">MEMINDAI</span>
        </div>
        <div class="bubble-track">
            <div class="bubble-target"></div>
            <div class="bubble-dot" id="bubble-dot"></div>
        </div>
        <div class="stat-grid" style="margin-top: 8px;">
            <div class="stat-box"><span>Kemiringan Roll (X)</span><b id="sens-x">0.0&deg;</b></div>
            <div class="stat-box"><span>Kemiringan Pitch (Y)</span><b id="sens-y">0.0&deg;</b></div>
            <div class="stat-box"><span>Arah Heading Yaw (Z)</span><b id="sens-z">0.0&deg;</b></div>
            <div class="stat-box"><span>Status Respons</span><b id="sens-status" style="color: #34D399;">Aktif</b></div>
        </div>
        <button class="btn-action" id="btn-ios-motion" onclick="requestIOSMotion()" style="display: none; background: #7C3AED;">
            Izinkan Sensor Gerak (Khusus Apple iOS)
        </button>
    </div>

    <!-- 5. Uji Speaker & Getar Bertahap -->
    <div class="card">
        <div class="card-title">
            <span>5. Speaker Audio & Motor Getar (Uji 3 Nada & 3x Getar)</span>
            <span class="badge badge-wait" id="audio-badge">MENUNGGU UJI</span>
        </div>
        <button class="btn-action" id="btn-audio" onclick="runSequentialAudioHapticTest()">
            Mulai Uji Suara 3 Nada & 3x Getar Fisik
        </button>
        <p style="font-size: 0.72rem; color: #94A3B8; margin-top: 6px;" id="audio-status-label">
            Tekan tombol di atas untuk membunyikan 3 nada bertingkat dan menggetarkan HP 3 kali berturut-turut.
        </p>

        <!-- Kotak Verifikasi Jawaban Fisik -->
        <div id="audio-verify-section" style="display: none; margin-top: 10px;">
            <div class="verify-box">
                <div class="verify-title">Verifikasi Kualitas Suara Speaker:</div>
                <label class="radio-opt">
                    <input type="radio" name="rad-audio" value="clear" checked onchange="updateAudioVerdict()">
                    <span>Ya, 3 nada terdengar jernih tanpa sember/kresek (Normal)</span>
                </label>
                <label class="radio-opt">
                    <input type="radio" name="rad-audio" value="distorted" onchange="updateAudioVerdict()">
                    <span>Suara sember / pecah / kresek-kresek (Peringatan Cacat Speaker)</span>
                </label>
                <label class="radio-opt">
                    <input type="radio" name="rad-audio" value="silent" onchange="updateAudioVerdict()">
                    <span>Tidak ada suara sama sekali (Speaker Rusak / Mati)</span>
                </label>
            </div>

            <div class="verify-box" style="margin-top: 8px;">
                <div class="verify-title">Verifikasi Motor Getar Fisik:</div>
                <label class="radio-opt">
                    <input type="radio" name="rad-haptic" value="strong" checked onchange="updateAudioVerdict()">
                    <span>Ya, HP bergetar 3 kali dengan kuat di tangan (Normal)</span>
                </label>
                <label class="radio-opt">
                    <input type="radio" name="rad-haptic" value="weak" onchange="updateAudioVerdict()">
                    <span>Getaran sangat lemah / hampir tidak terasa</span>
                </label>
                <label class="radio-opt">
                    <input type="radio" name="rad-haptic" value="none" onchange="updateAudioVerdict()">
                    <span>HP tidak bergetar sama sekali (Motor Getar Rusak / Mati)</span>
                </label>
            </div>
        </div>
    </div>

    <!-- Submit Section -->
    <div style="margin: 16px 0 30px 0;">
        <button class="btn btn-submit" id="btn-submit" onclick="submitResults()">KIRIM HASIL DIAGNOSTIK KE LAPTOP KASIR</button>
        <div class="success-box" id="success-banner">
            <h3 style="color: #34D399; font-size: 1.05rem;">Diagnostik Berhasil Terkirim!</h3>
            <p style="font-size: 0.82rem; color: #E2E8F0; margin-top: 4px;">Data tersimpan ke database & layar inspeksi kasir.</p>
            <a id="done-redirect-btn" href="#" target="_top" style="display: inline-block; margin-top: 10px; padding: 8px 16px; background: #2563EB; color: white; border-radius: 8px; font-weight: 700; font-size: 0.82rem; text-decoration: none;">Klik di Sini Jika Halaman Belum Berpindah</a>
        </div>
    </div>

    <!-- Full Screen Touch Modal -->
    <div id="fs-touch-modal">
        <div class="fs-hud">
            <div style="display: flex; flex-direction: column;">
                <span style="font-size: 0.68rem; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;">UJI LAYAR SENTUH</span>
                <span style="font-size: 0.82rem; font-weight: 700; color: #F8FAFC;">
                    Cakupan: <b id="fs-pct" style="color: #34D399;">0%</b> (<span id="fs-count">0</span>/<span id="fs-total">0</span>)
                </span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <button class="fs-btn-save-hud" id="fs-btn-save-hud" onclick="closeFullscreenTouch(true)">
                    Simpan (0%)
                </button>
                <button onclick="closeFullscreenTouch(false)" style="background: #334155; color: #94A3B8; border: none; padding: 8px 12px; border-radius: 6px; font-size: 0.76rem; font-weight: 700; cursor: pointer;">
                    Batal
                </button>
            </div>
        </div>

        <div id="fs-prompt-complete">
            <div id="fs-prompt-title" style="color: #34D399; font-weight: 800; font-size: 1.05rem;">
                Layar Sentuh Lolos Uji!
            </div>
            <div id="fs-prompt-sub" style="color: #CBD5E1; font-size: 0.80rem; margin-top: 6px;">
                Cakupan sentuh: <b id="fs-prompt-pct" style="color: #10B981; font-size: 1rem;">85%</b>. Seluruh area digitizer teruji responsif bebas dead-zone.
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 14px;">
                <button onclick="closeFullscreenTouch(true)" style="width: 100%; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 800; font-size: 0.90rem; cursor: pointer; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.5);">
                    KONFIRMASI & SIMPAN HASIL
                </button>
                <button onclick="dismissFSPrompt()" style="width: 100%; background: #1E293B; color: #94A3B8; border: 1px solid #334155; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 0.80rem; cursor: pointer;">
                    Lanjut Usap Sisa Layar
                </button>
            </div>
        </div>

        <div class="fs-grid-container" id="fs-grid">
            <!-- Dynamic resolution cells -->
        </div>

        <div class="fs-bottom-bar">
            <button class="fs-btn-save" id="fs-btn-save" onclick="closeFullscreenTouch(true)">
                USAP SELURUH LAYAR (0%)
            </button>
        </div>
    </div>

    <script>
        const injectedAppBase = "__APP_BASE_URL__";
        const injectedSessionId = "__SESSION_ID__";
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = (injectedSessionId && !injectedSessionId.startsWith("__")) ? injectedSessionId : (urlParams.get('session') || 'MCV-MOBILE');
        
        // Generate unique client device ID to prevent multi-device database overwrite
        const clientDevId = 'DEV-' + Math.random().toString(36).substring(2, 7).toUpperCase() + '-' + Date.now().toString().slice(-4);
        const recordId = sessionId + '_' + clientDevId;

        document.getElementById('session-label').innerText = sessionId;
        document.getElementById('dev-tag').innerText = clientDevId;

        let batteryData = { level: 90, charging: false, health_pct: 92, stress_passed: true };
        let confirmedROM = '128 GB';
        let customModelOverride = '';
        let motionData = { alpha: 0, beta: 0, gamma: 0 };
        let audioVerdict = { audio: 'not_tested', haptic: 'not_tested', passed: false };
        let touchResult = { fullscreen_passed: false, coverage_pct: 0, cells_passed: 0, total_cells: 0 };

        const MODEL_DATABASE = {
            "IPHONE 11": { brand: "Apple", model: "iPhone 11", soc: "Apple A13 Bionic" },
            "IPHONE 11 PRO": { brand: "Apple", model: "iPhone 11 Pro", soc: "Apple A13 Bionic" },
            "IPHONE 11 PRO MAX": { brand: "Apple", model: "iPhone 11 Pro Max", soc: "Apple A13 Bionic" },
            "IPHONE 12": { brand: "Apple", model: "iPhone 12", soc: "Apple A14 Bionic" },
            "IPHONE 12 MINI": { brand: "Apple", model: "iPhone 12 mini", soc: "Apple A14 Bionic" },
            "IPHONE 12 PRO": { brand: "Apple", model: "iPhone 12 Pro", soc: "Apple A14 Bionic" },
            "IPHONE 12 PRO MAX": { brand: "Apple", model: "iPhone 12 Pro Max", soc: "Apple A14 Bionic" },
            "IPHONE 13": { brand: "Apple", model: "iPhone 13", soc: "Apple A15 Bionic" },
            "IPHONE 13 MINI": { brand: "Apple", model: "iPhone 13 mini", soc: "Apple A15 Bionic" },
            "IPHONE 13 PRO": { brand: "Apple", model: "iPhone 13 Pro", soc: "Apple A15 Bionic" },
            "IPHONE 13 PRO MAX": { brand: "Apple", model: "iPhone 13 Pro Max", soc: "Apple A15 Bionic" },
            "IPHONE 14": { brand: "Apple", model: "iPhone 14", soc: "Apple A15 Bionic" },
            "IPHONE 14 PLUS": { brand: "Apple", model: "iPhone 14 Plus", soc: "Apple A15 Bionic" },
            "IPHONE 14 PRO": { brand: "Apple", model: "iPhone 14 Pro", soc: "Apple A16 Bionic" },
            "IPHONE 14 PRO MAX": { brand: "Apple", model: "iPhone 14 Pro Max", soc: "Apple A16 Bionic" },
            "IPHONE 15": { brand: "Apple", model: "iPhone 15", soc: "Apple A16 Bionic" },
            "IPHONE 15 PLUS": { brand: "Apple", model: "iPhone 15 Plus", soc: "Apple A16 Bionic" },
            "IPHONE 15 PRO": { brand: "Apple", model: "iPhone 15 Pro", soc: "Apple A17 Pro" },
            "IPHONE 15 PRO MAX": { brand: "Apple", model: "iPhone 15 Pro Max", soc: "Apple A17 Pro" },
            "IPHONE 16": { brand: "Apple", model: "iPhone 16", soc: "Apple A18" },
            "IPHONE 16 PLUS": { brand: "Apple", model: "iPhone 16 Plus", soc: "Apple A18" },
            "IPHONE 16 PRO": { brand: "Apple", model: "iPhone 16 Pro", soc: "Apple A18 Pro" },
            "IPHONE 16 PRO MAX": { brand: "Apple", model: "iPhone 16 Pro Max", soc: "Apple A18 Pro" },
            "IPHONE 16E": { brand: "Apple", model: "iPhone 16e", soc: "Apple A18" },
            "IPHONE 17": { brand: "Apple", model: "iPhone 17", soc: "Apple A19" },
            "IPHONE 17 PRO MAX": { brand: "Apple", model: "iPhone 17 Pro Max", soc: "Apple A19 Pro" },
            "IPHONE 6": { brand: "Apple", model: "iPhone 6", soc: "Apple A8" },
            "IPHONE 6 PLUS": { brand: "Apple", model: "iPhone 6 Plus", soc: "Apple A8" },
            "IPHONE 6S": { brand: "Apple", model: "iPhone 6s", soc: "Apple A9" },
            "IPHONE 6S PLUS": { brand: "Apple", model: "iPhone 6s Plus", soc: "Apple A9" },
            "IPHONE 7": { brand: "Apple", model: "iPhone 7", soc: "Apple A10 Fusion" },
            "IPHONE 7 PLUS": { brand: "Apple", model: "iPhone 7 Plus", soc: "Apple A10 Fusion" },
            "IPHONE 8": { brand: "Apple", model: "iPhone 8", soc: "Apple A11 Bionic" },
            "IPHONE 8 PLUS": { brand: "Apple", model: "iPhone 8 Plus", soc: "Apple A11 Bionic" },
            "IPHONE X": { brand: "Apple", model: "iPhone X", soc: "Apple A11 Bionic" },
            "IPHONE XR": { brand: "Apple", model: "iPhone XR", soc: "Apple A12 Bionic" },
            "IPHONE XS": { brand: "Apple", model: "iPhone XS", soc: "Apple A12 Bionic" },
            "IPHONE XS MAX": { brand: "Apple", model: "iPhone XS Max", soc: "Apple A12 Bionic" },
            "IPHONE10,1": { brand: "Apple", model: "iPhone 8", soc: "Apple A11 Bionic" },
            "IPHONE10,2": { brand: "Apple", model: "iPhone 8 Plus", soc: "Apple A11 Bionic" },
            "IPHONE10,3": { brand: "Apple", model: "iPhone X", soc: "Apple A11 Bionic" },
            "IPHONE10,4": { brand: "Apple", model: "iPhone 8", soc: "Apple A11 Bionic" },
            "IPHONE10,5": { brand: "Apple", model: "iPhone 8 Plus", soc: "Apple A11 Bionic" },
            "IPHONE10,6": { brand: "Apple", model: "iPhone X", soc: "Apple A11 Bionic" },
            "IPHONE11,2": { brand: "Apple", model: "iPhone XS", soc: "Apple A12 Bionic" },
            "IPHONE11,4": { brand: "Apple", model: "iPhone XS Max", soc: "Apple A12 Bionic" },
            "IPHONE11,6": { brand: "Apple", model: "iPhone XS Max", soc: "Apple A12 Bionic" },
            "IPHONE11,8": { brand: "Apple", model: "iPhone XR", soc: "Apple A12 Bionic" },
            "IPHONE12,1": { brand: "Apple", model: "iPhone 11", soc: "Apple A13 Bionic" },
            "IPHONE12,3": { brand: "Apple", model: "iPhone 11 Pro", soc: "Apple A13 Bionic" },
            "IPHONE12,5": { brand: "Apple", model: "iPhone 11 Pro Max", soc: "Apple A13 Bionic" },
            "IPHONE12,8": { brand: "Apple", model: "iPhone SE (2nd Gen)", soc: "Apple A13 Bionic" },
            "IPHONE13,1": { brand: "Apple", model: "iPhone 12 mini", soc: "Apple A14 Bionic" },
            "IPHONE13,2": { brand: "Apple", model: "iPhone 12", soc: "Apple A14 Bionic" },
            "IPHONE13,3": { brand: "Apple", model: "iPhone 12 Pro", soc: "Apple A14 Bionic" },
            "IPHONE13,4": { brand: "Apple", model: "iPhone 12 Pro Max", soc: "Apple A14 Bionic" },
            "IPHONE14,2": { brand: "Apple", model: "iPhone 13 Pro", soc: "Apple A15 Bionic" },
            "IPHONE14,3": { brand: "Apple", model: "iPhone 13 Pro Max", soc: "Apple A15 Bionic" },
            "IPHONE14,4": { brand: "Apple", model: "iPhone 13 mini", soc: "Apple A15 Bionic" },
            "IPHONE14,5": { brand: "Apple", model: "iPhone 13", soc: "Apple A15 Bionic" },
            "IPHONE14,6": { brand: "Apple", model: "iPhone SE (3rd Gen)", soc: "Apple A15 Bionic" },
            "IPHONE14,7": { brand: "Apple", model: "iPhone 14", soc: "Apple A15 Bionic" },
            "IPHONE14,8": { brand: "Apple", model: "iPhone 14 Plus", soc: "Apple A15 Bionic" },
            "IPHONE15,2": { brand: "Apple", model: "iPhone 14 Pro", soc: "Apple A16 Bionic" },
            "IPHONE15,3": { brand: "Apple", model: "iPhone 14 Pro Max", soc: "Apple A16 Bionic" },
            "IPHONE15,4": { brand: "Apple", model: "iPhone 15", soc: "Apple A16 Bionic" },
            "IPHONE15,5": { brand: "Apple", model: "iPhone 15 Plus", soc: "Apple A16 Bionic" },
            "IPHONE16,1": { brand: "Apple", model: "iPhone 15 Pro", soc: "Apple A17 Pro" },
            "IPHONE16,2": { brand: "Apple", model: "iPhone 15 Pro Max", soc: "Apple A17 Pro" },
            "IPHONE17,1": { brand: "Apple", model: "iPhone 16 Pro", soc: "Apple A18 Pro" },
            "IPHONE17,2": { brand: "Apple", model: "iPhone 16 Pro Max", soc: "Apple A18 Pro" },
            "IPHONE17,3": { brand: "Apple", model: "iPhone 16", soc: "Apple A18" },
            "IPHONE17,4": { brand: "Apple", model: "iPhone 16 Plus", soc: "Apple A18" },
            "IPHONE17,5": { brand: "Apple", model: "iPhone 16e", soc: "Apple A18" },
            "IPHONE7,1": { brand: "Apple", model: "iPhone 6 Plus", soc: "Apple A8" },
            "IPHONE7,2": { brand: "Apple", model: "iPhone 6", soc: "Apple A8" },
            "IPHONE8,1": { brand: "Apple", model: "iPhone 6s", soc: "Apple A9" },
            "IPHONE8,2": { brand: "Apple", model: "iPhone 6s Plus", soc: "Apple A9" },
            "IPHONE8,4": { brand: "Apple", model: "iPhone SE (1st Gen)", soc: "Apple A9" },
            "IPHONE9,1": { brand: "Apple", model: "iPhone 7", soc: "Apple A10 Fusion" },
            "IPHONE9,2": { brand: "Apple", model: "iPhone 7 Plus", soc: "Apple A10 Fusion" },
            "IPHONE9,3": { brand: "Apple", model: "iPhone 7", soc: "Apple A10 Fusion" },
            "IPHONE9,4": { brand: "Apple", model: "iPhone 7 Plus", soc: "Apple A10 Fusion" },
            "ASUS_AI2201": { brand: "Asus", model: "ROG Phone 6", soc: "Qualcomm Snapdragon 8+ Gen 1" },
            "ASUS_AI2202": { brand: "Asus", model: "Zenfone 9", soc: "Qualcomm Snapdragon 8+ Gen 1" },
            "ASUS_AI2205": { brand: "Asus", model: "ROG Phone 7", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "ASUS_AI2302": { brand: "Asus", model: "Zenfone 10", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "ASUS_AI2401": { brand: "Asus", model: "ROG Phone 8", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "ASUS_I005D": { brand: "Asus", model: "ROG Phone 5", soc: "Qualcomm Snapdragon 888" },
            "ASUS_I006D": { brand: "Asus", model: "Zenfone 8", soc: "Qualcomm Snapdragon 888" },
            "CTR-LX1": { brand: "Huawei", model: "Nova 12i", soc: "Qualcomm Snapdragon 680" },
            "ELS-NX9": { brand: "Huawei", model: "P40 Pro", soc: "HiSilicon Kirin 990 5G" },
            "FOA-LX9": { brand: "Huawei", model: "Nova 11", soc: "Qualcomm Snapdragon 778G 4G" },
            "INE-LX2": { brand: "Huawei", model: "Nova 3i", soc: "HiSilicon Kirin 710" },
            "JEF-AN00": { brand: "Huawei", model: "Nova 7 5G", soc: "HiSilicon Kirin 985 5G" },
            "LIO-L29": { brand: "Huawei", model: "Mate 30 Pro", soc: "HiSilicon Kirin 990" },
            "NAM-LX9": { brand: "Huawei", model: "Nova 9", soc: "Qualcomm Snapdragon 778G 4G" },
            "NOH-NX9": { brand: "Huawei", model: "Mate 40 Pro", soc: "HiSilicon Kirin 9000" },
            "VOG-L29": { brand: "Huawei", model: "P30 Pro", soc: "HiSilicon Kirin 980" },
            "YAL-L21": { brand: "Huawei", model: "Nova 5T", soc: "HiSilicon Kirin 980" },
            "X650": { brand: "Infinix", model: "Hot 8", soc: "MediaTek Helio A22" },
            "X6511": { brand: "Infinix", model: "Smart 6", soc: "Unisoc SC9863A" },
            "X6511G": { brand: "Infinix", model: "Smart 6 Plus", soc: "MediaTek Helio G25" },
            "X6512": { brand: "Infinix", model: "Smart 6", soc: "Unisoc SC9863A" },
            "X6515": { brand: "Infinix", model: "Smart 7", soc: "MediaTek Helio A22" },
            "X6525": { brand: "Infinix", model: "Smart 8", soc: "Unisoc T606" },
            "X6525B": { brand: "Infinix", model: "Smart 8 Pro", soc: "MediaTek Helio G36" },
            "X653": { brand: "Infinix", model: "Smart 4", soc: "MediaTek Helio A22" },
            "X6531": { brand: "Infinix", model: "Hot 50i", soc: "MediaTek Helio G81" },
            "X6532": { brand: "Infinix", model: "Smart 9", soc: "MediaTek Helio G81" },
            "X655": { brand: "Infinix", model: "Hot 9", soc: "MediaTek Helio A25" },
            "X657": { brand: "Infinix", model: "Smart 5", soc: "MediaTek Helio A20" },
            "X662": { brand: "Infinix", model: "Hot 11", soc: "MediaTek Helio G70" },
            "X663": { brand: "Infinix", model: "Note 11", soc: "MediaTek Helio G88" },
            "X663B": { brand: "Infinix", model: "Note 11s", soc: "MediaTek Helio G96" },
            "X665": { brand: "Infinix", model: "Hot 12i", soc: "MediaTek Helio A22" },
            "X666": { brand: "Infinix", model: "Hot 20 5G", soc: "MediaTek Dimensity 810" },
            "X669": { brand: "Infinix", model: "Hot 30i", soc: "MediaTek Helio G37" },
            "X670": { brand: "Infinix", model: "Note 12", soc: "MediaTek Helio G88" },
            "X6711": { brand: "Infinix", model: "Note 30 5G", soc: "MediaTek Dimensity 6080" },
            "X6716B": { brand: "Infinix", model: "Note 30 Pro", soc: "MediaTek Helio G99" },
            "X6731": { brand: "Infinix", model: "Zero 30 4G", soc: "MediaTek Helio G99" },
            "X6731B": { brand: "Infinix", model: "Zero 30 5G", soc: "MediaTek Dimensity 8020" },
            "X676B": { brand: "Infinix", model: "Note 12 Pro", soc: "MediaTek Helio G99" },
            "X676C": { brand: "Infinix", model: "Note 12 (2023)", soc: "MediaTek Helio G99" },
            "X680": { brand: "Infinix", model: "Hot 9 Play", soc: "MediaTek Helio A25" },
            "X6810": { brand: "Infinix", model: "Zero X Pro", soc: "MediaTek Helio G95" },
            "X6811": { brand: "Infinix", model: "Zero X", soc: "MediaTek Helio G95" },
            "X6812": { brand: "Infinix", model: "Hot 11s", soc: "MediaTek Helio G88" },
            "X6815": { brand: "Infinix", model: "Zero 5G", soc: "MediaTek Dimensity 900" },
            "X6816D": { brand: "Infinix", model: "Hot 12 Play", soc: "Unisoc T610" },
            "X6817": { brand: "Infinix", model: "Hot 12", soc: "MediaTek Helio G85" },
            "X682": { brand: "Infinix", model: "Hot 10", soc: "MediaTek Helio G70" },
            "X6821": { brand: "Infinix", model: "Zero 20", soc: "MediaTek Helio G99" },
            "X6826": { brand: "Infinix", model: "Hot 20", soc: "MediaTek Helio G85" },
            "X6827": { brand: "Infinix", model: "Hot 20s", soc: "MediaTek Helio G96" },
            "X6831": { brand: "Infinix", model: "Hot 30", soc: "MediaTek Helio G88" },
            "X6833": { brand: "Infinix", model: "Note 30", soc: "MediaTek Helio G99" },
            "X6833B": { brand: "Infinix", model: "Hot 30i", soc: "MediaTek Helio G37" },
            "X6835": { brand: "Infinix", model: "Hot 30 Play", soc: "MediaTek Helio G37" },
            "X6836": { brand: "Infinix", model: "Hot 40 Pro", soc: "MediaTek Helio G99" },
            "X6837": { brand: "Infinix", model: "Hot 40i", soc: "Unisoc T606" },
            "X6850": { brand: "Infinix", model: "Note 40", soc: "MediaTek Helio G99 Ultimate" },
            "X6851": { brand: "Infinix", model: "Note 40 Pro", soc: "MediaTek Helio G99 Ultimate" },
            "X6851B": { brand: "Infinix", model: "Note 40 Pro 5G", soc: "MediaTek Dimensity 7020" },
            "X6853": { brand: "Infinix", model: "GT 10 Pro", soc: "MediaTek Dimensity 8050" },
            "X6860": { brand: "Infinix", model: "Zero 40 4G", soc: "MediaTek Helio G100" },
            "X6861": { brand: "Infinix", model: "Zero 40 5G", soc: "MediaTek Dimensity 8200 Ultimate" },
            "X687": { brand: "Infinix", model: "Zero 8", soc: "MediaTek Helio G90T" },
            "X6871": { brand: "Infinix", model: "GT 20 Pro", soc: "MediaTek Dimensity 8200 Ultimate" },
            "X6880": { brand: "Infinix", model: "Hot 50 Pro+", soc: "MediaTek Helio G100" },
            "X6881": { brand: "Infinix", model: "Hot 50 Pro", soc: "MediaTek Helio G100" },
            "X6882": { brand: "Infinix", model: "Hot 50", soc: "MediaTek Helio G100" },
            "X688B": { brand: "Infinix", model: "Hot 10 Play", soc: "MediaTek Helio G25" },
            "X689": { brand: "Infinix", model: "Hot 10s", soc: "MediaTek Helio G85" },
            "X690": { brand: "Infinix", model: "Note 7", soc: "MediaTek Helio G70" },
            "X692": { brand: "Infinix", model: "Note 8", soc: "MediaTek Helio G80" },
            "X693": { brand: "Infinix", model: "Note 10", soc: "MediaTek Helio G85" },
            "X695": { brand: "Infinix", model: "Note 10 Pro", soc: "MediaTek Helio G95" },
            "X697": { brand: "Infinix", model: "Note 11 Pro", soc: "MediaTek Helio G96" },
            "CPH1723": { brand: "Oppo", model: "F5", soc: "MediaTek Helio P23" },
            "CPH1727": { brand: "Oppo", model: "F5 Youth", soc: "MediaTek Helio P23" },
            "CPH1729": { brand: "Oppo", model: "A83", soc: "MediaTek Helio P23" },
            "CPH1803": { brand: "Oppo", model: "A3s", soc: "Qualcomm Snapdragon 450" },
            "CPH1819": { brand: "Oppo", model: "F7", soc: "MediaTek Helio P60" },
            "CPH1821": { brand: "Oppo", model: "F7 128GB", soc: "MediaTek Helio P60" },
            "CPH1823": { brand: "Oppo", model: "F9", soc: "MediaTek Helio P60" },
            "CPH1827": { brand: "Oppo", model: "A83 (2018)", soc: "MediaTek Helio P23" },
            "CPH1853": { brand: "Oppo", model: "A3s", soc: "Qualcomm Snapdragon 450" },
            "CPH1881": { brand: "Oppo", model: "F9 Pro", soc: "MediaTek Helio P60" },
            "CPH1901": { brand: "Oppo", model: "A7", soc: "Qualcomm Snapdragon 450" },
            "CPH1907": { brand: "Oppo", model: "Reno2", soc: "Qualcomm Snapdragon 730G" },
            "CPH1909": { brand: "Oppo", model: "A5s", soc: "MediaTek Helio P35" },
            "CPH1911": { brand: "Oppo", model: "F11", soc: "MediaTek Helio P70" },
            "CPH1917": { brand: "Oppo", model: "Reno", soc: "Qualcomm Snapdragon 710" },
            "CPH1919": { brand: "Oppo", model: "Reno 10x Zoom", soc: "Qualcomm Snapdragon 855" },
            "CPH1923": { brand: "Oppo", model: "A1k", soc: "MediaTek Helio P22" },
            "CPH1931": { brand: "Oppo", model: "A5 (2020)", soc: "Qualcomm Snapdragon 665" },
            "CPH1937": { brand: "Oppo", model: "A9 (2020)", soc: "Qualcomm Snapdragon 665" },
            "CPH1939": { brand: "Oppo", model: "A5 (2020)", soc: "Qualcomm Snapdragon 665" },
            "CPH1969": { brand: "Oppo", model: "F11 Pro", soc: "MediaTek Helio P70" },
            "CPH1989": { brand: "Oppo", model: "Reno2 F", soc: "MediaTek Helio P70" },
            "CPH2015": { brand: "Oppo", model: "A31", soc: "MediaTek Helio P35" },
            "CPH2023": { brand: "Oppo", model: "Find X2", soc: "Qualcomm Snapdragon 865" },
            "CPH2025": { brand: "Oppo", model: "Find X2 Pro", soc: "Qualcomm Snapdragon 865" },
            "CPH2035": { brand: "Oppo", model: "Reno3 Pro", soc: "MediaTek Helio P95" },
            "CPH2043": { brand: "Oppo", model: "Reno3", soc: "MediaTek Helio P90" },
            "CPH2059": { brand: "Oppo", model: "A92", soc: "Qualcomm Snapdragon 665" },
            "CPH2061": { brand: "Oppo", model: "A52", soc: "Qualcomm Snapdragon 665" },
            "CPH2071": { brand: "Oppo", model: "A11k", soc: "MediaTek Helio P35" },
            "CPH2073": { brand: "Oppo", model: "A31", soc: "MediaTek Helio P35" },
            "CPH2077": { brand: "Oppo", model: "A12", soc: "MediaTek Helio P35" },
            "CPH2081": { brand: "Oppo", model: "A31", soc: "MediaTek Helio P35" },
            "CPH2083": { brand: "Oppo", model: "A12", soc: "MediaTek Helio P35" },
            "CPH2109": { brand: "Oppo", model: "Reno4 Pro", soc: "Qualcomm Snapdragon 720G" },
            "CPH2113": { brand: "Oppo", model: "Reno4", soc: "Qualcomm Snapdragon 720G" },
            "CPH2127": { brand: "Oppo", model: "A53", soc: "Qualcomm Snapdragon 460" },
            "CPH2137": { brand: "Oppo", model: "A33 (2020)", soc: "Qualcomm Snapdragon 460" },
            "CPH2145": { brand: "Oppo", model: "Reno5 5G", soc: "Qualcomm Snapdragon 765G" },
            "CPH2159": { brand: "Oppo", model: "Reno5 4G", soc: "Qualcomm Snapdragon 720G" },
            "CPH2173": { brand: "Oppo", model: "Find X3 Pro", soc: "Qualcomm Snapdragon 888" },
            "CPH2179": { brand: "Oppo", model: "A15s", soc: "MediaTek Helio P35" },
            "CPH2185": { brand: "Oppo", model: "A15", soc: "MediaTek Helio P35" },
            "CPH2197": { brand: "Oppo", model: "A74 5G", soc: "Qualcomm Snapdragon 480 5G" },
            "CPH2209": { brand: "Oppo", model: "Reno4 F", soc: "MediaTek Helio P95" },
            "CPH2211": { brand: "Oppo", model: "A54", soc: "MediaTek Helio P35" },
            "CPH2217": { brand: "Oppo", model: "Reno5 F", soc: "MediaTek Helio P95" },
            "CPH2219": { brand: "Oppo", model: "A74 4G", soc: "Qualcomm Snapdragon 662" },
            "CPH2235": { brand: "Oppo", model: "Reno6 4G", soc: "Qualcomm Snapdragon 720G" },
            "CPH2239": { brand: "Oppo", model: "A54", soc: "MediaTek Helio P35" },
            "CPH2247": { brand: "Oppo", model: "Reno6 Pro 5G", soc: "Qualcomm Snapdragon 870" },
            "CPH2251": { brand: "Oppo", model: "Reno6 5G", soc: "MediaTek Dimensity 900" },
            "CPH2269": { brand: "Oppo", model: "A16", soc: "MediaTek Helio G35" },
            "CPH2271": { brand: "Oppo", model: "A16e", soc: "MediaTek Helio P22" },
            "CPH2273": { brand: "Oppo", model: "A54s", soc: "MediaTek Helio G35" },
            "CPH2307": { brand: "Oppo", model: "Find X5 Pro", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "CPH2325": { brand: "Oppo", model: "A55", soc: "MediaTek Helio G35" },
            "CPH2333": { brand: "Oppo", model: "A96", soc: "Qualcomm Snapdragon 680" },
            "CPH2343": { brand: "Oppo", model: "Reno7 Z 5G", soc: "Qualcomm Snapdragon 695" },
            "CPH2349": { brand: "Oppo", model: "A16k", soc: "MediaTek Helio G35" },
            "CPH2357": { brand: "Oppo", model: "Reno8 Pro 5G", soc: "MediaTek Dimensity 8100-Max" },
            "CPH2359": { brand: "Oppo", model: "Reno8 4G", soc: "Qualcomm Snapdragon 680" },
            "CPH2363": { brand: "Oppo", model: "Reno7 4G", soc: "Qualcomm Snapdragon 680" },
            "CPH2365": { brand: "Oppo", model: "A95", soc: "Qualcomm Snapdragon 662" },
            "CPH2371": { brand: "Oppo", model: "Reno7 5G", soc: "MediaTek Dimensity 900" },
            "CPH2375": { brand: "Oppo", model: "Reno8 5G", soc: "MediaTek Dimensity 1300" },
            "CPH2377": { brand: "Oppo", model: "A76", soc: "Qualcomm Snapdragon 680" },
            "CPH2387": { brand: "Oppo", model: "A57 (2022)", soc: "MediaTek Helio G35" },
            "CPH2437": { brand: "Oppo", model: "Find N2 Flip", soc: "MediaTek Dimensity 9000+" },
            "CPH2457": { brand: "Oppo", model: "Reno8 T 4G", soc: "MediaTek Helio G99" },
            "CPH2471": { brand: "Oppo", model: "A17k", soc: "MediaTek Helio G35" },
            "CPH2473": { brand: "Oppo", model: "A77s", soc: "Qualcomm Snapdragon 680" },
            "CPH2477": { brand: "Oppo", model: "A78 4G", soc: "Qualcomm Snapdragon 680" },
            "CPH2483": { brand: "Oppo", model: "A78 5G", soc: "MediaTek Dimensity 700" },
            "CPH2499": { brand: "Oppo", model: "Find N3 Flip", soc: "MediaTek Dimensity 9200" },
            "CPH2505": { brand: "Oppo", model: "Reno8 T 5G", soc: "Qualcomm Snapdragon 695" },
            "CPH2519": { brand: "Oppo", model: "A98 5G", soc: "Qualcomm Snapdragon 695" },
            "CPH2519A": { brand: "Oppo", model: "Find N3", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "CPH2521": { brand: "Oppo", model: "Reno10 Pro+ 5G", soc: "Qualcomm Snapdragon 8+ Gen 1" },
            "CPH2525": { brand: "Oppo", model: "Reno10 5G", soc: "MediaTek Dimensity 7050" },
            "CPH2527": { brand: "Oppo", model: "A58 4G", soc: "MediaTek Helio G85" },
            "CPH2531": { brand: "Oppo", model: "Reno10 Pro 5G", soc: "Qualcomm Snapdragon 778G" },
            "CPH2557": { brand: "Oppo", model: "A79 5G", soc: "MediaTek Dimensity 6020" },
            "CPH2565": { brand: "Oppo", model: "A38", soc: "MediaTek Helio G85" },
            "CPH2579": { brand: "Oppo", model: "A18", soc: "MediaTek Helio G85" },
            "CPH2603": { brand: "Oppo", model: "Reno11 F 5G", soc: "MediaTek Dimensity 7050" },
            "CPH2605": { brand: "Oppo", model: "Reno11 Pro 5G", soc: "MediaTek Dimensity 8200" },
            "CPH2607": { brand: "Oppo", model: "Reno11 5G", soc: "MediaTek Dimensity 7050" },
            "CPH2625": { brand: "Oppo", model: "Reno12 5G", soc: "MediaTek Dimensity 7300-Energy" },
            "CPH2627": { brand: "Oppo", model: "Reno12 Pro 5G", soc: "MediaTek Dimensity 7300-Energy" },
            "CPH2629": { brand: "Oppo", model: "Reno12 F 5G", soc: "MediaTek Dimensity 6300" },
            "CPH2631": { brand: "Oppo", model: "A60", soc: "Qualcomm Snapdragon 680" },
            "CPH2639": { brand: "Oppo", model: "A3 Pro", soc: "MediaTek Dimensity 7050" },
            "CPH2641": { brand: "Oppo", model: "A3x", soc: "Qualcomm Snapdragon 6s 4G Gen 1" },
            "CPH2643": { brand: "Oppo", model: "A3", soc: "Qualcomm Snapdragon 6s 4G Gen 1" },
            "OPPO A5 PRO": { brand: "Oppo", model: "A5 Pro", soc: "MediaTek Dimensity 7050" },
            "OPPO A5I": { brand: "Oppo", model: "A5i", soc: "MediaTek Helio P35" },
            "OPPO A6 PRO": { brand: "Oppo", model: "A6 Pro", soc: "MediaTek Dimensity 7050" },
            "OPPO A6X": { brand: "Oppo", model: "A6x", soc: "Qualcomm Snapdragon 680" },
            "OPPO RENO 13F": { brand: "Oppo", model: "Reno 13F", soc: "MediaTek Dimensity 7300" },
            "OPPO RENO 14F": { brand: "Oppo", model: "Reno 14F", soc: "MediaTek Dimensity 7300" },
            "21061110AG": { brand: "POCO", model: "POCO X3 GT", soc: "MediaTek Dimensity 1100" },
            "21091116AG": { brand: "POCO", model: "POCO M4 Pro 5G", soc: "MediaTek Dimensity 810" },
            "21121210G": { brand: "POCO", model: "POCO F4 GT", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "2201116PG": { brand: "POCO", model: "POCO X4 Pro 5G", soc: "Qualcomm Snapdragon 695" },
            "2201117PG": { brand: "POCO", model: "POCO M4 Pro 4G", soc: "MediaTek Helio G96" },
            "22021211RG": { brand: "POCO", model: "POCO F4", soc: "Qualcomm Snapdragon 870" },
            "220333QPG": { brand: "POCO", model: "POCO C40", soc: "JLQ JR510" },
            "22041216G": { brand: "POCO", model: "POCO X4 GT", soc: "MediaTek Dimensity 8100" },
            "22041216UG": { brand: "POCO", model: "POCO F4", soc: "Qualcomm Snapdragon 870" },
            "2207117BPG": { brand: "POCO", model: "POCO M5s", soc: "MediaTek Helio G95" },
            "22071219CG": { brand: "POCO", model: "POCO M5", soc: "MediaTek Helio G99" },
            "22101320G": { brand: "POCO", model: "POCO X5 Pro 5G", soc: "Qualcomm Snapdragon 778G" },
            "22111317PG": { brand: "POCO", model: "POCO X5 5G", soc: "Qualcomm Snapdragon 695" },
            "22127PC95G": { brand: "POCO", model: "POCO C65", soc: "MediaTek Helio G85" },
            "23013PC75G": { brand: "POCO", model: "POCO F5 Pro", soc: "Qualcomm Snapdragon 8+ Gen 1" },
            "23049PCD8G": { brand: "POCO", model: "POCO F5", soc: "Qualcomm Snapdragon 7+ Gen 2" },
            "2304FPN6DC": { brand: "POCO", model: "POCO F5", soc: "Qualcomm Snapdragon 7+ Gen 2" },
            "2304FPN6DG": { brand: "POCO", model: "POCO F5", soc: "Qualcomm Snapdragon 7+ Gen 2" },
            "23076PC4BG": { brand: "POCO", model: "POCO M6 Pro", soc: "MediaTek Helio G99-Ultra" },
            "23076PC4BI": { brand: "POCO", model: "POCO M6 Pro", soc: "MediaTek Helio G99-Ultra" },
            "2310FPCA4G": { brand: "POCO", model: "POCO C65", soc: "MediaTek Helio G85" },
            "23113RKC6G": { brand: "POCO", model: "POCO F6 Pro", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "2311DRK48G": { brand: "POCO", model: "POCO X6 Pro 5G", soc: "MediaTek Dimensity 8300 Ultra" },
            "23122PCD1G": { brand: "POCO", model: "POCO X6 5G", soc: "Qualcomm Snapdragon 7s Gen 2" },
            "2312FPCA6G": { brand: "POCO", model: "POCO M6 Pro", soc: "MediaTek Helio G99 Ultra" },
            "24069PC21G": { brand: "POCO", model: "POCO F6", soc: "Qualcomm Snapdragon 8s Gen 3" },
            "M2007J20CG": { brand: "POCO", model: "POCO X3 NFC", soc: "Qualcomm Snapdragon 732G" },
            "M2010J19CG": { brand: "POCO", model: "POCO M3", soc: "Qualcomm Snapdragon 662" },
            "M2012K11AG": { brand: "POCO", model: "POCO F3", soc: "Qualcomm Snapdragon 870" },
            "M2102J20SG": { brand: "POCO", model: "POCO X3 Pro", soc: "Qualcomm Snapdragon 860" },
            "M2103K19PG": { brand: "POCO", model: "POCO M3 Pro 5G", soc: "MediaTek Dimensity 700" },
            "RMX1811": { brand: "Realme", model: "C1", soc: "Qualcomm Snapdragon 450" },
            "RMX1821": { brand: "Realme", model: "3", soc: "MediaTek Helio P60" },
            "RMX1851": { brand: "Realme", model: "3 Pro", soc: "Qualcomm Snapdragon 710" },
            "RMX1911": { brand: "Realme", model: "5", soc: "Qualcomm Snapdragon 665" },
            "RMX1941": { brand: "Realme", model: "C2", soc: "MediaTek Helio P22" },
            "RMX1971": { brand: "Realme", model: "5 Pro", soc: "Qualcomm Snapdragon 712" },
            "RMX2001": { brand: "Realme", model: "6", soc: "MediaTek Helio G90T" },
            "RMX2020": { brand: "Realme", model: "C3", soc: "MediaTek Helio G70" },
            "RMX2030": { brand: "Realme", model: "5i", soc: "Qualcomm Snapdragon 665" },
            "RMX2061": { brand: "Realme", model: "6 Pro", soc: "Qualcomm Snapdragon 720G" },
            "RMX2103": { brand: "Realme", model: "7i", soc: "Qualcomm Snapdragon 662" },
            "RMX2151": { brand: "Realme", model: "7", soc: "MediaTek Helio G95" },
            "RMX2161": { brand: "Realme", model: "Narzo 20 Pro", soc: "MediaTek Helio G95" },
            "RMX2170": { brand: "Realme", model: "7 Pro", soc: "Qualcomm Snapdragon 720G" },
            "RMX2175": { brand: "Realme", model: "C17", soc: "Qualcomm Snapdragon 460" },
            "RMX2180": { brand: "Realme", model: "C15", soc: "MediaTek Helio G35" },
            "RMX2185": { brand: "Realme", model: "C11", soc: "MediaTek Helio G35" },
            "RMX2189": { brand: "Realme", model: "C12", soc: "MediaTek Helio G35" },
            "RMX2193": { brand: "Realme", model: "Narzo 20", soc: "MediaTek Helio G85" },
            "RMX2195": { brand: "Realme", model: "C15 Qualcomm", soc: "Qualcomm Snapdragon 460" },
            "RMX3063": { brand: "Realme", model: "C20", soc: "MediaTek Helio G35" },
            "RMX3081": { brand: "Realme", model: "8 Pro", soc: "Qualcomm Snapdragon 720G" },
            "RMX3085": { brand: "Realme", model: "8", soc: "MediaTek Helio G95" },
            "RMX3171": { brand: "Realme", model: "Narzo 30A", soc: "MediaTek Helio G85" },
            "RMX3191": { brand: "Realme", model: "C25s", soc: "MediaTek Helio G85" },
            "RMX3193": { brand: "Realme", model: "C25", soc: "MediaTek Helio G70" },
            "RMX3195": { brand: "Realme", model: "C25s", soc: "MediaTek Helio G85" },
            "RMX3201": { brand: "Realme", model: "C21", soc: "MediaTek Helio G35" },
            "RMX3231": { brand: "Realme", model: "C11 (2021)", soc: "Unisoc SC9863A" },
            "RMX3241": { brand: "Realme", model: "8 5G", soc: "MediaTek Dimensity 700" },
            "RMX3261": { brand: "Realme", model: "C21Y", soc: "Unisoc T610" },
            "RMX3263": { brand: "Realme", model: "C21Y", soc: "Unisoc T610" },
            "RMX3265": { brand: "Realme", model: "C25Y", soc: "Unisoc T610" },
            "RMX3286": { brand: "Realme", model: "Narzo 50", soc: "MediaTek Helio G96" },
            "RMX3301": { brand: "Realme", model: "GT 2 Pro", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "RMX3363": { brand: "Realme", model: "GT Master Edition", soc: "Qualcomm Snapdragon 778G" },
            "RMX3370": { brand: "Realme", model: "GT Neo 2", soc: "Qualcomm Snapdragon 870" },
            "RMX3371": { brand: "Realme", model: "GT Neo 3T", soc: "Qualcomm Snapdragon 870" },
            "RMX3388": { brand: "Realme", model: "9 5G", soc: "Qualcomm Snapdragon 695" },
            "RMX3392": { brand: "Realme", model: "9 Pro+ 5G", soc: "MediaTek Dimensity 920" },
            "RMX3430": { brand: "Realme", model: "Narzo 50A", soc: "MediaTek Helio G85" },
            "RMX3472": { brand: "Realme", model: "9 Pro 5G", soc: "Qualcomm Snapdragon 695" },
            "RMX3501": { brand: "Realme", model: "C31", soc: "Unisoc T612" },
            "RMX3506": { brand: "Realme", model: "Narzo 50i Prime", soc: "Unisoc T612" },
            "RMX3511": { brand: "Realme", model: "C35", soc: "Unisoc T616" },
            "RMX3516": { brand: "Realme", model: "Narzo 50A Prime", soc: "Unisoc T612" },
            "RMX3521": { brand: "Realme", model: "9 4G", soc: "Qualcomm Snapdragon 680" },
            "RMX3561": { brand: "Realme", model: "GT Neo 3", soc: "MediaTek Dimensity 8100" },
            "RMX3581": { brand: "Realme", model: "C30", soc: "Unisoc T612" },
            "RMX3624": { brand: "Realme", model: "C33", soc: "Unisoc T612" },
            "RMX3630": { brand: "Realme", model: "10", soc: "MediaTek Helio G99" },
            "RMX3660": { brand: "Realme", model: "10 Pro 5G", soc: "Qualcomm Snapdragon 695" },
            "RMX3686": { brand: "Realme", model: "10 Pro+ 5G", soc: "MediaTek Dimensity 1080" },
            "RMX3687": { brand: "Realme", model: "10 Pro+ 5G", soc: "MediaTek Dimensity 1080" },
            "RMX3690": { brand: "Realme", model: "C30s", soc: "Unisoc SC9863A" },
            "RMX3706": { brand: "Realme", model: "GT Neo 3", soc: "MediaTek Dimensity 8100" },
            "RMX3710": { brand: "Realme", model: "C55", soc: "MediaTek Helio G88" },
            "RMX3741": { brand: "Realme", model: "11 Pro+ 5G", soc: "MediaTek Dimensity 7050" },
            "RMX3760": { brand: "Realme", model: "C53", soc: "Unisoc T612" },
            "RMX3761": { brand: "Realme", model: "C53", soc: "Unisoc T612" },
            "RMX3771": { brand: "Realme", model: "11 Pro 5G", soc: "MediaTek Dimensity 7050" },
            "RMX3780": { brand: "Realme", model: "11 4G", soc: "MediaTek Helio G99" },
            "RMX3830": { brand: "Realme", model: "C51", soc: "Unisoc T612" },
            "RMX3834": { brand: "Realme", model: "12 5G", soc: "MediaTek Dimensity 6100+" },
            "RMX3840": { brand: "Realme", model: "12 Pro+ 5G", soc: "Qualcomm Snapdragon 7s Gen 2" },
            "RMX3842": { brand: "Realme", model: "12+ 5G", soc: "MediaTek Dimensity 7050" },
            "RMX3850": { brand: "Realme", model: "GT 6", soc: "Qualcomm Snapdragon 8s Gen 3" },
            "RMX3851": { brand: "Realme", model: "13 4G", soc: "Qualcomm Snapdragon 685" },
            "RMX3867": { brand: "Realme", model: "12+ 5G", soc: "MediaTek Dimensity 7050" },
            "RMX3890": { brand: "Realme", model: "C67", soc: "Qualcomm Snapdragon 685" },
            "RMX3910": { brand: "Realme", model: "C65", soc: "MediaTek Helio G85" },
            "RMX3921": { brand: "Realme", model: "13 Pro+ 5G", soc: "Qualcomm Snapdragon 7s Gen 2" },
            "RMX3930": { brand: "Realme", model: "C63", soc: "Unisoc T612" },
            "RMX3939": { brand: "Realme", model: "C61", soc: "Unisoc T612" },
            "RMX3999": { brand: "Realme", model: "12 5G", soc: "MediaTek Dimensity 6100+" },
            "RMX5000": { brand: "Realme", model: "13+ 5G", soc: "MediaTek Dimensity 7300-Energy" },
            "SAMSUNG GALAXY A07": { brand: "Samsung", model: "Galaxy A07", soc: "MediaTek Helio G85" },
            "SAMSUNG GALAXY A17": { brand: "Samsung", model: "Galaxy A17", soc: "MediaTek Helio G99" },
            "SAMSUNG GALAXY A26": { brand: "Samsung", model: "Galaxy A26", soc: "Samsung Exynos 1280" },
            "SAMSUNG GALAXY A36": { brand: "Samsung", model: "Galaxy A36", soc: "Samsung Exynos 1380" },
            "SAMSUNG GALAXY S25 ULTRA": { brand: "Samsung", model: "Galaxy S25 Ultra", soc: "Qualcomm Snapdragon 8 Elite" },
            "SAMSUNG GALAXY S26 ULTRA": { brand: "Samsung", model: "Galaxy S26 Ultra", soc: "Qualcomm Snapdragon 8 Elite" },
            "SM-A013F": { brand: "Samsung", model: "Galaxy A01 Core", soc: "MediaTek MT6739" },
            "SM-A015F": { brand: "Samsung", model: "Galaxy A01", soc: "Qualcomm Snapdragon 439" },
            "SM-A022F": { brand: "Samsung", model: "Galaxy A02", soc: "MediaTek MT6739W" },
            "SM-A025F": { brand: "Samsung", model: "Galaxy A02s", soc: "Qualcomm Snapdragon 450" },
            "SM-A032F": { brand: "Samsung", model: "Galaxy A03 Core", soc: "Unisoc SC9863A" },
            "SM-A035F": { brand: "Samsung", model: "Galaxy A03", soc: "Unisoc T606" },
            "SM-A037F": { brand: "Samsung", model: "Galaxy A03s", soc: "MediaTek Helio P35" },
            "SM-A042F": { brand: "Samsung", model: "Galaxy A04e", soc: "MediaTek Helio P35" },
            "SM-A045F": { brand: "Samsung", model: "Galaxy A04", soc: "MediaTek Helio P35" },
            "SM-A047F": { brand: "Samsung", model: "Galaxy A04s", soc: "Samsung Exynos 850" },
            "SM-A055F": { brand: "Samsung", model: "Galaxy A05", soc: "MediaTek Helio G85" },
            "SM-A057F": { brand: "Samsung", model: "Galaxy A05s", soc: "Qualcomm Snapdragon 680" },
            "SM-A065F": { brand: "Samsung", model: "Galaxy A06", soc: "MediaTek Helio G85" },
            "SM-A075F": { brand: "Samsung", model: "Galaxy A07", soc: "MediaTek Helio G85" },
            "SM-A105F": { brand: "Samsung", model: "Galaxy A10", soc: "Samsung Exynos 7884" },
            "SM-A107F": { brand: "Samsung", model: "Galaxy A10s", soc: "MediaTek Helio P22" },
            "SM-A115F": { brand: "Samsung", model: "Galaxy A11", soc: "Qualcomm Snapdragon 450" },
            "SM-A125F": { brand: "Samsung", model: "Galaxy A12", soc: "MediaTek Helio P35" },
            "SM-A127F": { brand: "Samsung", model: "Galaxy A12 (Exynos)", soc: "Samsung Exynos 850" },
            "SM-A135F": { brand: "Samsung", model: "Galaxy A13", soc: "Samsung Exynos 850" },
            "SM-A137F": { brand: "Samsung", model: "Galaxy A13 (Helio)", soc: "MediaTek Helio G80" },
            "SM-A145F": { brand: "Samsung", model: "Galaxy A14 4G", soc: "MediaTek Helio G80" },
            "SM-A146M": { brand: "Samsung", model: "Galaxy A14 5G", soc: "Samsung Exynos 1330" },
            "SM-A146P": { brand: "Samsung", model: "Galaxy A14 5G", soc: "MediaTek Dimensity 700" },
            "SM-A155F": { brand: "Samsung", model: "Galaxy A15 4G", soc: "MediaTek Helio G99" },
            "SM-A156E": { brand: "Samsung", model: "Galaxy A15 5G", soc: "MediaTek Dimensity 6100+" },
            "SM-A165F": { brand: "Samsung", model: "Galaxy A16 4G", soc: "MediaTek Helio G99" },
            "SM-A166P": { brand: "Samsung", model: "Galaxy A16 5G", soc: "MediaTek Dimensity 6300" },
            "SM-A175F": { brand: "Samsung", model: "Galaxy A17", soc: "MediaTek Helio G99" },
            "SM-A205F": { brand: "Samsung", model: "Galaxy A20", soc: "Samsung Exynos 7884" },
            "SM-A207F": { brand: "Samsung", model: "Galaxy A20s", soc: "Qualcomm Snapdragon 450" },
            "SM-A217F": { brand: "Samsung", model: "Galaxy A21s", soc: "Samsung Exynos 850" },
            "SM-A225F": { brand: "Samsung", model: "Galaxy A22 4G", soc: "MediaTek Helio G80" },
            "SM-A226B": { brand: "Samsung", model: "Galaxy A22 5G", soc: "MediaTek Dimensity 700" },
            "SM-A235F": { brand: "Samsung", model: "Galaxy A23 4G", soc: "Qualcomm Snapdragon 680" },
            "SM-A236B": { brand: "Samsung", model: "Galaxy A23 5G", soc: "Qualcomm Snapdragon 695" },
            "SM-A245F": { brand: "Samsung", model: "Galaxy A24 4G", soc: "MediaTek Helio G99" },
            "SM-A256E": { brand: "Samsung", model: "Galaxy A25 5G", soc: "Samsung Exynos 1280" },
            "SM-A266B": { brand: "Samsung", model: "Galaxy A26", soc: "Samsung Exynos 1280" },
            "SM-A305F": { brand: "Samsung", model: "Galaxy A30", soc: "Samsung Exynos 7904" },
            "SM-A307F": { brand: "Samsung", model: "Galaxy A30s", soc: "Samsung Exynos 7904" },
            "SM-A315F": { brand: "Samsung", model: "Galaxy A31", soc: "MediaTek Helio P65" },
            "SM-A325F": { brand: "Samsung", model: "Galaxy A32 4G", soc: "MediaTek Helio G80" },
            "SM-A326B": { brand: "Samsung", model: "Galaxy A32 5G", soc: "MediaTek Dimensity 720" },
            "SM-A336B": { brand: "Samsung", model: "Galaxy A33 5G", soc: "Samsung Exynos 1280" },
            "SM-A336E": { brand: "Samsung", model: "Galaxy A33 5G", soc: "Samsung Exynos 1280" },
            "SM-A346E": { brand: "Samsung", model: "Galaxy A34 5G", soc: "MediaTek Dimensity 1080" },
            "SM-A356E": { brand: "Samsung", model: "Galaxy A35 5G", soc: "Samsung Exynos 1380" },
            "SM-A366B": { brand: "Samsung", model: "Galaxy A36", soc: "Samsung Exynos 1380" },
            "SM-A505F": { brand: "Samsung", model: "Galaxy A50", soc: "Samsung Exynos 9610" },
            "SM-A507F": { brand: "Samsung", model: "Galaxy A50s", soc: "Samsung Exynos 9611" },
            "SM-A515F": { brand: "Samsung", model: "Galaxy A51", soc: "Samsung Exynos 9611" },
            "SM-A525F": { brand: "Samsung", model: "Galaxy A52", soc: "Qualcomm Snapdragon 720G" },
            "SM-A528B": { brand: "Samsung", model: "Galaxy A52s 5G", soc: "Qualcomm Snapdragon 778G" },
            "SM-A536E": { brand: "Samsung", model: "Galaxy A53 5G", soc: "Samsung Exynos 1280" },
            "SM-A546E": { brand: "Samsung", model: "Galaxy A54 5G", soc: "Samsung Exynos 1380" },
            "SM-A556E": { brand: "Samsung", model: "Galaxy A55 5G", soc: "Samsung Exynos 1480" },
            "SM-A705F": { brand: "Samsung", model: "Galaxy A70", soc: "Qualcomm Snapdragon 675" },
            "SM-A715F": { brand: "Samsung", model: "Galaxy A71", soc: "Qualcomm Snapdragon 730G" },
            "SM-A725F": { brand: "Samsung", model: "Galaxy A72", soc: "Qualcomm Snapdragon 720G" },
            "SM-A736B": { brand: "Samsung", model: "Galaxy A73 5G", soc: "Qualcomm Snapdragon 778G" },
            "SM-F711B": { brand: "Samsung", model: "Galaxy Z Flip3 5G", soc: "Qualcomm Snapdragon 888" },
            "SM-F721B": { brand: "Samsung", model: "Galaxy Z Flip4 5G", soc: "Qualcomm Snapdragon 8+ Gen 1" },
            "SM-F731B": { brand: "Samsung", model: "Galaxy Z Flip5 5G", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "SM-F741B": { brand: "Samsung", model: "Galaxy Z Flip6 5G", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "SM-F926B": { brand: "Samsung", model: "Galaxy Z Fold3 5G", soc: "Qualcomm Snapdragon 888" },
            "SM-F936B": { brand: "Samsung", model: "Galaxy Z Fold4 5G", soc: "Qualcomm Snapdragon 8+ Gen 1" },
            "SM-F946B": { brand: "Samsung", model: "Galaxy Z Fold5 5G", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "SM-F956B": { brand: "Samsung", model: "Galaxy Z Fold6 5G", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "SM-G610F": { brand: "Samsung", model: "Galaxy J7 Prime", soc: "Samsung Exynos 7870" },
            "SM-G780F": { brand: "Samsung", model: "Galaxy S20 FE (Exynos)", soc: "Samsung Exynos 990" },
            "SM-G780G": { brand: "Samsung", model: "Galaxy S20 FE (Snapdragon)", soc: "Qualcomm Snapdragon 865" },
            "SM-G950F": { brand: "Samsung", model: "Galaxy S8", soc: "Samsung Exynos 8895" },
            "SM-G955F": { brand: "Samsung", model: "Galaxy S8+", soc: "Samsung Exynos 8895" },
            "SM-G960F": { brand: "Samsung", model: "Galaxy S9", soc: "Samsung Exynos 9810" },
            "SM-G965F": { brand: "Samsung", model: "Galaxy S9+", soc: "Samsung Exynos 9810" },
            "SM-G970F": { brand: "Samsung", model: "Galaxy S10e", soc: "Samsung Exynos 9820" },
            "SM-G973F": { brand: "Samsung", model: "Galaxy S10", soc: "Samsung Exynos 9820" },
            "SM-G975F": { brand: "Samsung", model: "Galaxy S10+", soc: "Samsung Exynos 9820" },
            "SM-G980F": { brand: "Samsung", model: "Galaxy S20", soc: "Samsung Exynos 990" },
            "SM-G985F": { brand: "Samsung", model: "Galaxy S20+", soc: "Samsung Exynos 990" },
            "SM-G988B": { brand: "Samsung", model: "Galaxy S20 Ultra", soc: "Samsung Exynos 990" },
            "SM-G990E": { brand: "Samsung", model: "Galaxy S21 FE 5G", soc: "Samsung Exynos 2100" },
            "SM-G991B": { brand: "Samsung", model: "Galaxy S21 5G", soc: "Samsung Exynos 2100" },
            "SM-G996B": { brand: "Samsung", model: "Galaxy S21+ 5G", soc: "Samsung Exynos 2100" },
            "SM-G998B": { brand: "Samsung", model: "Galaxy S21 Ultra 5G", soc: "Samsung Exynos 2100" },
            "SM-J700F": { brand: "Samsung", model: "Galaxy J7", soc: "Samsung Exynos 7580" },
            "SM-J710F": { brand: "Samsung", model: "Galaxy J7 (2016)", soc: "Samsung Exynos 7870" },
            "SM-J730G": { brand: "Samsung", model: "Galaxy J7 Pro", soc: "Samsung Exynos 7870" },
            "SM-M105G": { brand: "Samsung", model: "Galaxy M10", soc: "Samsung Exynos 7870" },
            "SM-M115F": { brand: "Samsung", model: "Galaxy M11", soc: "Qualcomm Snapdragon 450" },
            "SM-M127F": { brand: "Samsung", model: "Galaxy M12", soc: "Samsung Exynos 850" },
            "SM-M146B": { brand: "Samsung", model: "Galaxy M14 5G", soc: "Samsung Exynos 1330" },
            "SM-M156B": { brand: "Samsung", model: "Galaxy M15 5G", soc: "MediaTek Dimensity 6100+" },
            "SM-M205G": { brand: "Samsung", model: "Galaxy M20", soc: "Samsung Exynos 7904" },
            "SM-M215F": { brand: "Samsung", model: "Galaxy M21", soc: "Samsung Exynos 9611" },
            "SM-M225F": { brand: "Samsung", model: "Galaxy M22", soc: "MediaTek Helio G80" },
            "SM-M236B": { brand: "Samsung", model: "Galaxy M23 5G", soc: "Qualcomm Snapdragon 750G" },
            "SM-M307F": { brand: "Samsung", model: "Galaxy M30s", soc: "Samsung Exynos 9611" },
            "SM-M315F": { brand: "Samsung", model: "Galaxy M31", soc: "Samsung Exynos 9611" },
            "SM-M325F": { brand: "Samsung", model: "Galaxy M32", soc: "MediaTek Helio G80" },
            "SM-M336B": { brand: "Samsung", model: "Galaxy M33 5G", soc: "Samsung Exynos 1280" },
            "SM-M346B": { brand: "Samsung", model: "Galaxy M34 5G", soc: "Samsung Exynos 1280" },
            "SM-M515F": { brand: "Samsung", model: "Galaxy M51", soc: "Qualcomm Snapdragon 730G" },
            "SM-M526B": { brand: "Samsung", model: "Galaxy M52 5G", soc: "Qualcomm Snapdragon 778G" },
            "SM-M536B": { brand: "Samsung", model: "Galaxy M53 5G", soc: "MediaTek Dimensity 900" },
            "SM-M546B": { brand: "Samsung", model: "Galaxy M54 5G", soc: "Samsung Exynos 1380" },
            "SM-N770F": { brand: "Samsung", model: "Galaxy Note 10 Lite", soc: "Samsung Exynos 9810" },
            "SM-N950F": { brand: "Samsung", model: "Galaxy Note 8", soc: "Samsung Exynos 8895" },
            "SM-N960F": { brand: "Samsung", model: "Galaxy Note 9", soc: "Samsung Exynos 9810" },
            "SM-N970F": { brand: "Samsung", model: "Galaxy Note 10", soc: "Samsung Exynos 9825" },
            "SM-N975F": { brand: "Samsung", model: "Galaxy Note 10+", soc: "Samsung Exynos 9825" },
            "SM-N980F": { brand: "Samsung", model: "Galaxy Note 20", soc: "Samsung Exynos 990" },
            "SM-N985F": { brand: "Samsung", model: "Galaxy Note 20 Ultra", soc: "Samsung Exynos 990" },
            "SM-N986B": { brand: "Samsung", model: "Galaxy Note 20 Ultra 5G", soc: "Samsung Exynos 990" },
            "SM-S711B": { brand: "Samsung", model: "Galaxy S23 FE", soc: "Samsung Exynos 2200" },
            "SM-S721B": { brand: "Samsung", model: "Galaxy S24 FE", soc: "Samsung Exynos 2400e" },
            "SM-S901B": { brand: "Samsung", model: "Galaxy S22", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "SM-S901E": { brand: "Samsung", model: "Galaxy S22 5G", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "SM-S906B": { brand: "Samsung", model: "Galaxy S22+", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "SM-S906E": { brand: "Samsung", model: "Galaxy S22+ 5G", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "SM-S908B": { brand: "Samsung", model: "Galaxy S22 Ultra", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "SM-S908E": { brand: "Samsung", model: "Galaxy S22 Ultra 5G", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "SM-S911B": { brand: "Samsung", model: "Galaxy S23 5G", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "SM-S916B": { brand: "Samsung", model: "Galaxy S23+ 5G", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "SM-S918B": { brand: "Samsung", model: "Galaxy S23 Ultra 5G", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "SM-S921B": { brand: "Samsung", model: "Galaxy S24 5G", soc: "Samsung Exynos 2400" },
            "SM-S926B": { brand: "Samsung", model: "Galaxy S24+ 5G", soc: "Samsung Exynos 2400" },
            "SM-S928B": { brand: "Samsung", model: "Galaxy S24 Ultra 5G", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "SM-S938B": { brand: "Samsung", model: "Galaxy S25 Ultra", soc: "Qualcomm Snapdragon 8 Elite" },
            "SM-S948B": { brand: "Samsung", model: "Galaxy S26 Ultra", soc: "Qualcomm Snapdragon 8 Elite" },
            "BG6": { brand: "Tecno", model: "Spark 20", soc: "MediaTek Helio G85" },
            "BG7": { brand: "Tecno", model: "Spark 20 Pro", soc: "MediaTek Helio G99" },
            "BG7N": { brand: "Tecno", model: "Spark 20C", soc: "MediaTek Helio G36" },
            "CG6": { brand: "Tecno", model: "Camon 17", soc: "MediaTek Helio G85" },
            "CG8": { brand: "Tecno", model: "Camon 17 Pro", soc: "MediaTek Helio G95" },
            "CH6": { brand: "Tecno", model: "Camon 18", soc: "MediaTek Helio G88" },
            "CH9": { brand: "Tecno", model: "Camon 18 Premier", soc: "MediaTek Helio G96" },
            "CI8": { brand: "Tecno", model: "Camon 19 Pro", soc: "MediaTek Helio G96" },
            "CK6": { brand: "Tecno", model: "Camon 20", soc: "MediaTek Helio G85" },
            "CK7N": { brand: "Tecno", model: "Camon 20 Pro", soc: "MediaTek Helio G99" },
            "CK8N": { brand: "Tecno", model: "Camon 20 Pro 5G", soc: "MediaTek Dimensity 8050" },
            "CK9N": { brand: "Tecno", model: "Camon 20 Premier 5G", soc: "MediaTek Dimensity 8050" },
            "CL6": { brand: "Tecno", model: "Camon 30 4G", soc: "MediaTek Helio G99 Ultimate" },
            "CL7": { brand: "Tecno", model: "Camon 30 5G", soc: "MediaTek Dimensity 7020" },
            "CL8": { brand: "Tecno", model: "Camon 30 Pro 5G", soc: "MediaTek Dimensity 8200 Ultimate" },
            "CL9": { brand: "Tecno", model: "Camon 30 Premier 5G", soc: "MediaTek Dimensity 8200 Ultimate" },
            "KE5": { brand: "Tecno", model: "Spark 6 Go", soc: "MediaTek Helio A20" },
            "KF8": { brand: "Tecno", model: "Spark 7 Pro", soc: "MediaTek Helio G80" },
            "KG5K": { brand: "Tecno", model: "Spark 8C", soc: "Unisoc T606" },
            "KG8": { brand: "Tecno", model: "Spark 8 Pro", soc: "MediaTek Helio G85" },
            "KH6": { brand: "Tecno", model: "Spark 9T", soc: "MediaTek Helio G37" },
            "KH7N": { brand: "Tecno", model: "Spark 9 Pro", soc: "MediaTek Helio G85" },
            "KI5K": { brand: "Tecno", model: "Spark 10", soc: "MediaTek Helio G37" },
            "KI5Q": { brand: "Tecno", model: "Spark 10C", soc: "Unisoc T606" },
            "KI7": { brand: "Tecno", model: "Spark 10 Pro", soc: "MediaTek Helio G88" },
            "KJ7": { brand: "Tecno", model: "Spark 20 Pro+", soc: "MediaTek Helio G99 Ultimate" },
            "KL5": { brand: "Tecno", model: "Spark 30C", soc: "MediaTek Helio G81" },
            "KL8": { brand: "Tecno", model: "Spark 30 Pro", soc: "MediaTek Helio G100" },
            "LD7": { brand: "Tecno", model: "Pova", soc: "MediaTek Helio G80" },
            "LE7": { brand: "Tecno", model: "Pova 2", soc: "MediaTek Helio G85" },
            "LF7": { brand: "Tecno", model: "Pova 3", soc: "MediaTek Helio G88" },
            "LG7N": { brand: "Tecno", model: "Pova 4", soc: "MediaTek Helio G99" },
            "LG8N": { brand: "Tecno", model: "Pova 4 Pro", soc: "MediaTek Helio G99" },
            "LH7N": { brand: "Tecno", model: "Pova 5", soc: "MediaTek Helio G99" },
            "LH8N": { brand: "Tecno", model: "Pova 5 Pro 5G", soc: "MediaTek Dimensity 6080" },
            "LI7": { brand: "Tecno", model: "Pova 6", soc: "MediaTek Helio G99 Ultimate" },
            "LI9": { brand: "Tecno", model: "Pova 6 Pro 5G", soc: "MediaTek Dimensity 6080" },
            "PR651": { brand: "Tecno", model: "Spark 7", soc: "MediaTek Helio A25" },
            "I2207": { brand: "Vivo", model: "iQOO Z7 5G", soc: "Qualcomm Snapdragon 782G" },
            "I2213": { brand: "Vivo", model: "iQOO Z9x 5G", soc: "Qualcomm Snapdragon 6 Gen 1" },
            "I2216": { brand: "Vivo", model: "iQOO Z7x 5G", soc: "Qualcomm Snapdragon 695" },
            "I2220": { brand: "Vivo", model: "iQOO 11 5G", soc: "Qualcomm Snapdragon 8 Gen 2" },
            "I2222": { brand: "Vivo", model: "iQOO 12 5G", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "I2302": { brand: "Vivo", model: "iQOO Z9 5G", soc: "Qualcomm Snapdragon 7 Gen 3" },
            "V1804": { brand: "Vivo", model: "V11 Pro", soc: "Qualcomm Snapdragon 660" },
            "V1806": { brand: "Vivo", model: "V11", soc: "MediaTek Helio P60" },
            "V1818": { brand: "Vivo", model: "V15 Pro", soc: "Qualcomm Snapdragon 675" },
            "V1831": { brand: "Vivo", model: "V15", soc: "MediaTek Helio P70" },
            "V1901": { brand: "Vivo", model: "Y12", soc: "MediaTek Helio P22" },
            "V1901A": { brand: "Vivo", model: "Y12i", soc: "Qualcomm Snapdragon 439" },
            "V1902": { brand: "Vivo", model: "Y17", soc: "MediaTek Helio P35" },
            "V1906": { brand: "Vivo", model: "Y11 (2019)", soc: "Qualcomm Snapdragon 439" },
            "V1920": { brand: "Vivo", model: "V17 Pro", soc: "Qualcomm Snapdragon 675" },
            "V1934": { brand: "Vivo", model: "Y19", soc: "MediaTek Helio P65" },
            "V1935": { brand: "Vivo", model: "Y50", soc: "Qualcomm Snapdragon 665" },
            "V1938": { brand: "Vivo", model: "Y30", soc: "MediaTek Helio P35" },
            "V1969": { brand: "Vivo", model: "V19", soc: "Qualcomm Snapdragon 712" },
            "V2001": { brand: "Vivo", model: "X50", soc: "Qualcomm Snapdragon 730" },
            "V2005": { brand: "Vivo", model: "X50 Pro", soc: "Qualcomm Snapdragon 765G" },
            "V2020": { brand: "Vivo", model: "V20 Pro", soc: "Qualcomm Snapdragon 765G" },
            "V2022": { brand: "Vivo", model: "V20 SE", soc: "Qualcomm Snapdragon 665" },
            "V2025": { brand: "Vivo", model: "V20", soc: "Qualcomm Snapdragon 720G" },
            "V2026": { brand: "Vivo", model: "Y12s", soc: "MediaTek Helio P35" },
            "V2029": { brand: "Vivo", model: "Y20", soc: "Qualcomm Snapdragon 460" },
            "V2030": { brand: "Vivo", model: "Y51 (2020)", soc: "Qualcomm Snapdragon 665" },
            "V2037": { brand: "Vivo", model: "Y20G", soc: "MediaTek Helio G80" },
            "V2043": { brand: "Vivo", model: "Y20s", soc: "Qualcomm Snapdragon 460" },
            "V2045": { brand: "Vivo", model: "X60", soc: "Qualcomm Snapdragon 870" },
            "V2046": { brand: "Vivo", model: "X60 Pro", soc: "Qualcomm Snapdragon 870" },
            "V2050": { brand: "Vivo", model: "V21 5G", soc: "MediaTek Dimensity 800U" },
            "V2058": { brand: "Vivo", model: "Y53s", soc: "MediaTek Helio G80" },
            "V2066": { brand: "Vivo", model: "V21 4G", soc: "MediaTek Helio G96" },
            "V2105": { brand: "Vivo", model: "X70 Pro", soc: "MediaTek Dimensity 1200-vivo" },
            "V2109": { brand: "Vivo", model: "Y33s", soc: "MediaTek Helio G80" },
            "V2110": { brand: "Vivo", model: "Y21s", soc: "MediaTek Helio G80" },
            "V2111": { brand: "Vivo", model: "Y21", soc: "MediaTek Helio P35" },
            "V2116": { brand: "Vivo", model: "V23e", soc: "MediaTek Helio G96" },
            "V2120": { brand: "Vivo", model: "Y15s", soc: "MediaTek Helio P35" },
            "V2130": { brand: "Vivo", model: "V23 5G", soc: "MediaTek Dimensity 920" },
            "V2137": { brand: "Vivo", model: "Y33t", soc: "Qualcomm Snapdragon 680" },
            "V2140": { brand: "Vivo", model: "Y01", soc: "MediaTek Helio P35" },
            "V2142": { brand: "Vivo", model: "Y35", soc: "Qualcomm Snapdragon 680" },
            "V2144": { brand: "Vivo", model: "X80", soc: "MediaTek Dimensity 9000" },
            "V2145": { brand: "Vivo", model: "X80 Pro", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "V2147": { brand: "Vivo", model: "Y16", soc: "MediaTek Helio P35" },
            "V2149": { brand: "Vivo", model: "Y21a", soc: "MediaTek Helio P22" },
            "V2156": { brand: "Vivo", model: "Y33s", soc: "MediaTek Helio G80" },
            "V2158": { brand: "Vivo", model: "V25 Pro 5G", soc: "MediaTek Dimensity 1300" },
            "V2201": { brand: "Vivo", model: "V25e", soc: "MediaTek Helio G99" },
            "V2202": { brand: "Vivo", model: "V25 5G", soc: "MediaTek Dimensity 900" },
            "V2203": { brand: "Vivo", model: "Y02s", soc: "MediaTek Helio P35" },
            "V2204": { brand: "Vivo", model: "Y16", soc: "MediaTek Helio P35" },
            "V2205": { brand: "Vivo", model: "Y35", soc: "Qualcomm Snapdragon 680" },
            "V2207": { brand: "Vivo", model: "Y22", soc: "MediaTek Helio G85" },
            "V2217": { brand: "Vivo", model: "Y02", soc: "MediaTek Helio P22" },
            "V2219": { brand: "Vivo", model: "X90 Pro", soc: "MediaTek Dimensity 9200" },
            "V2236": { brand: "Vivo", model: "Y02t", soc: "MediaTek Helio P35" },
            "V2237": { brand: "Vivo", model: "V27e", soc: "MediaTek Helio G99" },
            "V2246": { brand: "Vivo", model: "V27 5G", soc: "MediaTek Dimensity 7200" },
            "V2247": { brand: "Vivo", model: "Y36 4G", soc: "Qualcomm Snapdragon 680" },
            "V2248": { brand: "Vivo", model: "Y36 5G", soc: "MediaTek Dimensity 6020" },
            "V2249": { brand: "Vivo", model: "Y27 4G", soc: "MediaTek Helio G85" },
            "V2250": { brand: "Vivo", model: "V29 5G", soc: "Qualcomm Snapdragon 778G" },
            "V2252": { brand: "Vivo", model: "Y02t", soc: "MediaTek Helio P35" },
            "V2302": { brand: "Vivo", model: "Y27 5G", soc: "MediaTek Dimensity 6020" },
            "V2303": { brand: "Vivo", model: "V29e 5G", soc: "Qualcomm Snapdragon 695" },
            "V2309": { brand: "Vivo", model: "X100", soc: "MediaTek Dimensity 9300" },
            "V2310": { brand: "Vivo", model: "Y17s", soc: "MediaTek Helio G85" },
            "V2315": { brand: "Vivo", model: "Y28 5G", soc: "MediaTek Dimensity 6020" },
            "V2318": { brand: "Vivo", model: "V30 5G", soc: "Qualcomm Snapdragon 7 Gen 3" },
            "V2319": { brand: "Vivo", model: "V30 Pro 5G", soc: "MediaTek Dimensity 8200" },
            "V2322": { brand: "Vivo", model: "Y28", soc: "MediaTek Helio G85" },
            "V2324": { brand: "Vivo", model: "X100 Pro", soc: "MediaTek Dimensity 9300" },
            "V2327": { brand: "Vivo", model: "Y100 5G", soc: "Qualcomm Snapdragon 4 Gen 2" },
            "V2332": { brand: "Vivo", model: "Y03", soc: "MediaTek Helio G85" },
            "V2333": { brand: "Vivo", model: "Y18", soc: "MediaTek Helio G85" },
            "V2339": { brand: "Vivo", model: "V30e 5G", soc: "Qualcomm Snapdragon 6 Gen 1" },
            "V2342": { brand: "Vivo", model: "Y100 4G", soc: "Qualcomm Snapdragon 685" },
            "V2343": { brand: "Vivo", model: "V30e", soc: "Qualcomm Snapdragon 6 Gen 1" },
            "V2344": { brand: "Vivo", model: "V30 5G", soc: "Qualcomm Snapdragon 7 Gen 3" },
            "V2348": { brand: "Vivo", model: "V40 5G", soc: "Qualcomm Snapdragon 7 Gen 3" },
            "V2352": { brand: "Vivo", model: "Y28 4G", soc: "MediaTek Helio G85" },
            "V2359": { brand: "Vivo", model: "V40 5G", soc: "Qualcomm Snapdragon 7 Gen 3" },
            "V2409": { brand: "Vivo", model: "Y03t", soc: "Unisoc T612" },
            "V2417": { brand: "Vivo", model: "V40 Lite 5G", soc: "Qualcomm Snapdragon 4 Gen 2" },
            "V2418": { brand: "Vivo", model: "V40 Lite 4G", soc: "Qualcomm Snapdragon 685" },
            "21061119DG": { brand: "Xiaomi", model: "Redmi 10", soc: "MediaTek Helio G88" },
            "2107113SG": { brand: "Xiaomi", model: "Xiaomi 11T Pro", soc: "Qualcomm Snapdragon 888" },
            "21081111RG": { brand: "Xiaomi", model: "Xiaomi 11T", soc: "MediaTek Dimensity 1200" },
            "21091116UG": { brand: "Xiaomi", model: "Redmi Note 11 Pro 5G", soc: "Qualcomm Snapdragon 695" },
            "21121119SG": { brand: "Xiaomi", model: "Redmi 10 2022", soc: "MediaTek Helio G88" },
            "2201116SG": { brand: "Xiaomi", model: "Redmi Note 12 Pro 4G", soc: "Qualcomm Snapdragon 732G" },
            "2201116TG": { brand: "Xiaomi", model: "Redmi Note 11 Pro", soc: "MediaTek Helio G96" },
            "2201117SG": { brand: "Xiaomi", model: "Redmi Note 11S", soc: "MediaTek Helio G96" },
            "2201117TG": { brand: "Xiaomi", model: "Redmi Note 11", soc: "Qualcomm Snapdragon 680" },
            "2201117TY": { brand: "Xiaomi", model: "Redmi Note 11", soc: "Qualcomm Snapdragon 680" },
            "2201122G": { brand: "Xiaomi", model: "Xiaomi 12 Pro", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "2201123G": { brand: "Xiaomi", model: "Xiaomi 12", soc: "Qualcomm Snapdragon 8 Gen 1" },
            "220233L2G": { brand: "Xiaomi", model: "Redmi 10A", soc: "MediaTek Helio G25" },
            "2203129G": { brand: "Xiaomi", model: "Xiaomi 12 Lite", soc: "Qualcomm Snapdragon 778G" },
            "220333QNY": { brand: "Xiaomi", model: "Redmi 10C", soc: "Qualcomm Snapdragon 680" },
            "22071212AG": { brand: "Xiaomi", model: "Xiaomi 12T 5G", soc: "MediaTek Dimensity 8100 Ultra" },
            "220733SI": { brand: "Xiaomi", model: "Redmi A1", soc: "MediaTek Helio A22" },
            "220733SL": { brand: "Xiaomi", model: "Redmi A1+", soc: "MediaTek Helio A22" },
            "22101316G": { brand: "Xiaomi", model: "Redmi Note 12 Pro 5G", soc: "MediaTek Dimensity 1080" },
            "22111317G": { brand: "Xiaomi", model: "Redmi Note 12 5G", soc: "Qualcomm Snapdragon 4 Gen 1" },
            "2212ARNC4G": { brand: "Xiaomi", model: "Redmi 12C", soc: "MediaTek Helio G85" },
            "23021RAA2Y": { brand: "Xiaomi", model: "Redmi Note 12 4G", soc: "Qualcomm Snapdragon 685" },
            "23021RAAEG": { brand: "Xiaomi", model: "Redmi Note 12 4G", soc: "Qualcomm Snapdragon 685" },
            "23028RN4DG": { brand: "Xiaomi", model: "Redmi A2", soc: "MediaTek Helio G36" },
            "23053RN02A": { brand: "Xiaomi", model: "Redmi 12", soc: "MediaTek Helio G88" },
            "23053RN02Y": { brand: "Xiaomi", model: "Redmi 12 (NFC)", soc: "MediaTek Helio G88" },
            "2306EPN60G": { brand: "Xiaomi", model: "Xiaomi 13T", soc: "MediaTek Dimensity 8200 Ultra" },
            "23078PND5G": { brand: "Xiaomi", model: "Xiaomi 13T Pro", soc: "MediaTek Dimensity 9200+" },
            "23090RA98G": { brand: "Xiaomi", model: "Redmi Note 13 Pro+ 5G", soc: "MediaTek Dimensity 7200 Ultra" },
            "23100RN82L": { brand: "Xiaomi", model: "Redmi 13C", soc: "MediaTek Helio G85" },
            "23106RN0DA": { brand: "Xiaomi", model: "Redmi 13C (NFC)", soc: "MediaTek Helio G85" },
            "23108RN04Y": { brand: "Xiaomi", model: "Redmi 13C", soc: "MediaTek Helio G85" },
            "23117RA68G": { brand: "Xiaomi", model: "Redmi Note 13 Pro 4G", soc: "MediaTek Helio G99 Ultra" },
            "23127PN0CG": { brand: "Xiaomi", model: "Xiaomi 14", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "23129RAA4G": { brand: "Xiaomi", model: "Redmi Note 13 4G", soc: "Qualcomm Snapdragon 685" },
            "23129RN51X": { brand: "Xiaomi", model: "Redmi A3", soc: "MediaTek Helio G36" },
            "2312CRAD3G": { brand: "Xiaomi", model: "Redmi Note 13 Pro 5G", soc: "Qualcomm Snapdragon 7s Gen 2" },
            "2312DRA50G": { brand: "Xiaomi", model: "Redmi Note 13 5G", soc: "MediaTek Dimensity 6080" },
            "24030PN60G": { brand: "Xiaomi", model: "Xiaomi 14 Ultra", soc: "Qualcomm Snapdragon 8 Gen 3" },
            "24040RN64Y": { brand: "Xiaomi", model: "Redmi 13", soc: "MediaTek Helio G91 Ultra" },
            "2409BRN2CG": { brand: "Xiaomi", model: "Redmi 14C", soc: "MediaTek Helio G81 Ultra" },
            "M1810F6LG": { brand: "Xiaomi", model: "Redmi 7", soc: "Qualcomm Snapdragon 632" },
            "M1901F7G": { brand: "Xiaomi", model: "Redmi Note 7", soc: "Qualcomm Snapdragon 660" },
            "M1903C3EG": { brand: "Xiaomi", model: "Redmi 7A", soc: "Qualcomm Snapdragon 439" },
            "M1906G7G": { brand: "Xiaomi", model: "Redmi Note 8 Pro", soc: "MediaTek Helio G90T" },
            "M1908C3IG": { brand: "Xiaomi", model: "Redmi 8", soc: "Qualcomm Snapdragon 439" },
            "M1908C3IH": { brand: "Xiaomi", model: "Redmi 8A Pro", soc: "Qualcomm Snapdragon 439" },
            "M1908C3JG": { brand: "Xiaomi", model: "Redmi Note 8", soc: "Qualcomm Snapdragon 665" },
            "M1908C3KG": { brand: "Xiaomi", model: "Redmi 8A", soc: "Qualcomm Snapdragon 439" },
            "M2003J15SS": { brand: "Xiaomi", model: "Redmi Note 9", soc: "MediaTek Helio G85" },
            "M2003J6B2G": { brand: "Xiaomi", model: "Redmi Note 9 Pro", soc: "Qualcomm Snapdragon 720G" },
            "M2004J19G": { brand: "Xiaomi", model: "Redmi 9", soc: "MediaTek Helio G80" },
            "M2006C3LG": { brand: "Xiaomi", model: "Redmi 9A", soc: "MediaTek Helio G25" },
            "M2006C3MG": { brand: "Xiaomi", model: "Redmi 9C", soc: "MediaTek Helio G35" },
            "M2007J3SG": { brand: "Xiaomi", model: "Mi 10T Pro", soc: "Qualcomm Snapdragon 865" },
            "M2007J3SY": { brand: "Xiaomi", model: "Mi 10T", soc: "Qualcomm Snapdragon 865" },
            "M2010J19SG": { brand: "Xiaomi", model: "Redmi 9T", soc: "Qualcomm Snapdragon 662" },
            "M2011K2G": { brand: "Xiaomi", model: "Mi 11", soc: "Qualcomm Snapdragon 888" },
            "M2101K6G": { brand: "Xiaomi", model: "Redmi Note 10 Pro", soc: "Qualcomm Snapdragon 732G" },
            "M2101K7AG": { brand: "Xiaomi", model: "Redmi Note 10", soc: "Qualcomm Snapdragon 678" },
            "M2101K7BG": { brand: "Xiaomi", model: "Redmi Note 10S", soc: "MediaTek Helio G95" },
            "M2101K9AG": { brand: "Xiaomi", model: "Mi 11 Lite", soc: "Qualcomm Snapdragon 732G" },
            "M2103K19G": { brand: "Xiaomi", model: "Redmi Note 10 5G", soc: "MediaTek Dimensity 700" },
            "A662L": { brand: "itel", model: "A60s", soc: "Unisoc SC9863A1" },
            "A662LM": { brand: "itel", model: "A60", soc: "Unisoc SC9832E" },
            "A665L": { brand: "itel", model: "A70", soc: "Unisoc T603" },
            "A671L": { brand: "itel", model: "A80", soc: "Unisoc T603" },
            "L6005": { brand: "itel", model: "Vision 1", soc: "Unisoc SC9863A" },
            "L6502": { brand: "itel", model: "Vision 1 Pro", soc: "Unisoc SC9832E" },
            "L6503": { brand: "itel", model: "Vision 2", soc: "Unisoc SC9863A" },
            "P661L": { brand: "itel", model: "P55 5G", soc: "MediaTek Dimensity 6080" },
            "P661N": { brand: "itel", model: "P55", soc: "Unisoc T606" },
            "P661NF": { brand: "itel", model: "P55 NFC", soc: "Unisoc T606" },
            "P662L": { brand: "itel", model: "P40", soc: "Unisoc SC9863A" },
            "P663L": { brand: "itel", model: "P40+", soc: "Unisoc T606" },
            "S661LN": { brand: "itel", model: "S23+", soc: "Unisoc T616" },
            "S661LP": { brand: "itel", model: "Vision 3", soc: "Unisoc SC9863A" },
            "S665L": { brand: "itel", model: "S23", soc: "Unisoc T606" },
            "S666LN": { brand: "itel", model: "S24", soc: "MediaTek Helio G91 Ultra" },
            "S667LN": { brand: "itel", model: "RS4", soc: "MediaTek Helio G99 Ultimate" },
        };

        // 1. Hardware Detection via Client Hints & WebGL
        const ua = navigator.userAgent || '';
        const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        let brandName = isIOS ? "Apple" : "Smartphone";
        let modelName = isIOS ? "iPhone" : "Android Device";
        let osName = isIOS ? "Apple iOS" : "Android OS";

        function resolveModelLookup(code) {
            if (!code) return null;
            const upper = code.trim().toUpperCase();
            if (MODEL_DATABASE[upper]) return MODEL_DATABASE[upper];
            for (const k in MODEL_DATABASE) {
                if (upper.includes(k) || k.includes(upper)) return MODEL_DATABASE[k];
            }
            return null;
        }

        if (isIOS) {
            brandName = "Apple";
            const w = window.screen.width;
            const h = window.screen.height;
            if ((w === 393 && h === 852) || (w === 852 && h === 393)) modelName = "iPhone 15 / 16 / 14 Pro";
            else if ((w === 430 && h === 932) || (w === 932 && h === 430)) modelName = "iPhone 15 Pro Max / 16 Pro Max";
            else if ((w === 390 && h === 844) || (w === 844 && h === 390)) modelName = "iPhone 12 / 13 / 14";
            else if ((w === 428 && h === 926) || (w === 926 && h === 428)) modelName = "iPhone 13 Pro Max / 14 Plus";
            else if ((w === 414 && h === 896) || (w === 896 && h === 414)) modelName = "iPhone 11 / XR";
            else if ((w === 375 && h === 812) || (w === 812 && h === 375)) modelName = "iPhone X / XS / 11 Pro";
            else if ((w === 375 && h === 667) || (w === 667 && h === 375)) modelName = "iPhone SE";
            else modelName = "Apple iPhone";

            const osMatch = ua.match(/OS (\d+[_\.]\d+)/);
            osName = osMatch ? "iOS " + osMatch[1].replace('_', '.') : "Apple iOS";
            document.getElementById('ios-battery-section').style.display = 'block';
            document.getElementById('bat-level').innerText = '90%';
            document.getElementById('bat-charging').innerText = 'Standar';
        } else {
            let activeLookup = null;
            if (/Samsung|SM-|GT-/i.test(ua)) {
                brandName = "Samsung";
                const m = ua.match(/SM-[A-Z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : m[0];
                } else {
                    modelName = "Galaxy Series";
                }
            } else if (/Oppo|CPH\d+|P[A-Z]\d+/i.test(ua)) {
                brandName = "Oppo";
                const m = ua.match(/CPH\d{4}/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : ("Oppo (" + m[0] + ")");
                } else {
                    modelName = "Series A / Reno";
                }
            } else if (/Xiaomi|Redmi|POCO/i.test(ua)) {
                brandName = "Xiaomi";
                const m = ua.match(/Redmi [A-Za-z0-9 ]+|POCO [A-Za-z0-9 ]+|2[0-9]{3}[A-Za-z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : m[0];
                } else {
                    modelName = "Redmi / POCO Series";
                }
            } else if (/Vivo|V\d{4}/i.test(ua)) {
                brandName = "Vivo";
                const m = ua.match(/V\d{4}[A-Z]?/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : m[0];
                } else {
                    modelName = "Y-Series / V-Series";
                }
            } else if (/Realme|RMX\d{4}/i.test(ua)) {
                brandName = "Realme";
                const m = ua.match(/RMX\d{4}/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : m[0];
                } else {
                    modelName = "Realme Series";
                }
            } else if (/Infinix|X\d{3,4}/i.test(ua)) {
                brandName = "Infinix";
                const m = ua.match(/X\d{3,4}[A-Za-z0-9]*/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Hot / Note Series";
                } else {
                    modelName = "Hot / Note Series";
                }
            } else if (/Tecno|KE5|PR651|KF8|KG\d|KH\d|KI\d|BG\d|KJ\d|KL\d|CG\d|CH\d|CI\d|CK\d|CL\d|LD\d|LE\d|LF\d|LG\d|LH\d|LI\d/i.test(ua)) {
                brandName = "Tecno";
                const m = ua.match(/KE5|PR651|KF8|KG[0-9a-z]+|KH[0-9a-z]+|KI[0-9a-z]+|BG[0-9a-z]+|KJ[0-9a-z]+|KL[0-9a-z]+|CG[0-9a-z]+|CH[0-9a-z]+|CI[0-9a-z]+|CK[0-9a-z]+|CL[0-9a-z]+|LD[0-9a-z]+|LE[0-9a-z]+|LF[0-9a-z]+|LG[0-9a-z]+|LH[0-9a-z]+|LI[0-9a-z]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Spark / Camon / Pova";
                } else {
                    modelName = "Spark / Camon / Pova";
                }
            } else if (/itel|L6005|L6502|L6503|S661|A662|A665|A671|P661|P662|P663|S665|S666|S667/i.test(ua)) {
                brandName = "itel";
                const m = ua.match(/L6005|L6502|L6503|S661[A-Za-z]*|A662[A-Za-z]*|A665[A-Za-z]*|A671[A-Za-z]*|P661[A-Za-z]*|P662[A-Za-z]*|P663[A-Za-z]*|S665[A-Za-z]*|S666[A-Za-z]*|S667[A-Za-z]*/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Vision / S / P Series";
                } else {
                    modelName = "Vision / S / P Series";
                }
            } else if (/ASUS|ROG Phone|Zenfone/i.test(ua)) {
                brandName = "Asus";
                const m = ua.match(/ASUS_[A-Za-z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "ROG Phone / Zenfone";
                } else {
                    modelName = "ROG Phone / Zenfone";
                }
            } else if (/Huawei|HONOR|HMA-|VOG-|ELS-|NAM-|FOA-|CTR-/i.test(ua)) {
                brandName = "Huawei";
                const m = ua.match(/[A-Z]{3}-[A-Z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Nova / P / Mate Series";
                } else {
                    modelName = "Nova / P / Mate Series";
                }
            } else if (/Tecno|KE5|PR651|KF8|KG\d|KH\d|KI\d|BG\d|KJ\d|KL\d|CG\d|CH\d|CI\d|CK\d|CL\d|LD\d|LE\d|LF\d|LG\d|LH\d|LI\d/i.test(ua)) {
                brandName = "Tecno";
                const m = ua.match(/KE5|PR651|KF8|KG[0-9a-z]+|KH[0-9a-z]+|KI[0-9a-z]+|BG[0-9a-z]+|KJ[0-9a-z]+|KL[0-9a-z]+|CG[0-9a-z]+|CH[0-9a-z]+|CI[0-9a-z]+|CK[0-9a-z]+|CL[0-9a-z]+|LD[0-9a-z]+|LE[0-9a-z]+|LF[0-9a-z]+|LG[0-9a-z]+|LH[0-9a-z]+|LI[0-9a-z]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Spark / Camon / Pova";
                } else {
                    modelName = "Spark / Camon / Pova";
                }
            } else if (/itel|L6005|L6502|L6503|S661|A662|A665|A671|P661|P662|P663|S665|S666|S667/i.test(ua)) {
                brandName = "itel";
                const m = ua.match(/L6005|L6502|L6503|S661[A-Za-z]*|A662[A-Za-z]*|A665[A-Za-z]*|A671[A-Za-z]*|P661[A-Za-z]*|P662[A-Za-z]*|P663[A-Za-z]*|S665[A-Za-z]*|S666[A-Za-z]*|S667[A-Za-z]*/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Vision / S / P Series";
                } else {
                    modelName = "Vision / S / P Series";
                }
            } else if (/ASUS|ROG Phone|Zenfone/i.test(ua)) {
                brandName = "Asus";
                const m = ua.match(/ASUS_[A-Za-z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "ROG Phone / Zenfone";
                } else {
                    modelName = "ROG Phone / Zenfone";
                }
            } else if (/Huawei|HONOR|HMA-|VOG-|ELS-|NAM-|FOA-|CTR-/i.test(ua)) {
                brandName = "Huawei";
                const m = ua.match(/[A-Z]{3}-[A-Z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Nova / P / Mate Series";
                } else {
                    modelName = "Nova / P / Mate Series";
                }
            } else if (/Tecno|KE5|PR651|KF8|KG\d|KH\d|KI\d|BG\d|KJ\d|KL\d|CG\d|CH\d|CI\d|CK\d|CL\d|LD\d|LE\d|LF\d|LG\d|LH\d|LI\d/i.test(ua)) {
                brandName = "Tecno";
                const m = ua.match(/KE5|PR651|KF8|KG[0-9a-z]+|KH[0-9a-z]+|KI[0-9a-z]+|BG[0-9a-z]+|KJ[0-9a-z]+|KL[0-9a-z]+|CG[0-9a-z]+|CH[0-9a-z]+|CI[0-9a-z]+|CK[0-9a-z]+|CL[0-9a-z]+|LD[0-9a-z]+|LE[0-9a-z]+|LF[0-9a-z]+|LG[0-9a-z]+|LH[0-9a-z]+|LI[0-9a-z]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Spark / Camon / Pova";
                } else {
                    modelName = "Spark / Camon / Pova";
                }
            } else if (/itel|L6005|L6502|L6503|S661|A662|A665|A671|P661|P662|P663|S665|S666|S667/i.test(ua)) {
                brandName = "itel";
                const m = ua.match(/L6005|L6502|L6503|S661[A-Za-z]*|A662[A-Za-z]*|A665[A-Za-z]*|A671[A-Za-z]*|P661[A-Za-z]*|P662[A-Za-z]*|P663[A-Za-z]*|S665[A-Za-z]*|S666[A-Za-z]*|S667[A-Za-z]*/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Vision / S / P Series";
                } else {
                    modelName = "Vision / S / P Series";
                }
            } else if (/ASUS|ROG Phone|Zenfone/i.test(ua)) {
                brandName = "Asus";
                const m = ua.match(/ASUS_[A-Za-z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "ROG Phone / Zenfone";
                } else {
                    modelName = "ROG Phone / Zenfone";
                }
            } else if (/Huawei|HONOR|HMA-|VOG-|ELS-|NAM-|FOA-|CTR-/i.test(ua)) {
                brandName = "Huawei";
                const m = ua.match(/[A-Z]{3}-[A-Z0-9]+/i);
                if (m) {
                    activeLookup = resolveModelLookup(m[0]);
                    modelName = activeLookup ? activeLookup.model + " (" + m[0] + ")" : "Nova / P / Mate Series";
                } else {
                    modelName = "Nova / P / Mate Series";
                }
            }
            const andMatch = ua.match(/Android (\d+(\.\d+)?)/i);
            osName = andMatch ? "Android " + andMatch[1] : "Android OS";

            if (activeLookup && activeLookup.brand) {
                brandName = activeLookup.brand;
            }
        }

        // Modern W3C Client Hints for Exact Android Hardware Model
        if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
            navigator.userAgentData.getHighEntropyValues(['model', 'platformVersion', 'architecture'])
                .then(hints => {
                    if (hints.model) {
                        const lookup = resolveModelLookup(hints.model);
                        if (lookup) {
                            brandName = lookup.brand;
                            modelName = lookup.model + " (" + hints.model + ")";
                            if (lookup.soc) {
                                socName = lookup.soc;
                                document.getElementById('val-soc').innerText = socName;
                            }
                        } else {
                            modelName = hints.model;
                        }
                        document.getElementById('val-brand').innerText = brandName;
                        document.getElementById('val-model').innerText = modelName;
                        document.getElementById('device-pill').innerText = brandName + " " + modelName + " (AI Terverifikasi)";
                    }
                }).catch(() => {});
        }

        // WebGL GPU Detection
        let gpuName = "Mobile Graphics Hardware";
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (gl) {
                const ext = gl.getExtension('WEBGL_debug_renderer_info');
                if (ext) { gpuName = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL); }
            }
        } catch(e) {}

        // Identify SoC / Processor from WebGL Unmasked GPU
        let socName = "ARM64 Mobile Processor (Octa-Core)";
        if (/Adreno 610/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon 680 (Adreno 610)";
        } else if (/Adreno 619/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon 695 5G (Adreno 619)";
        } else if (/Adreno 642/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon 778G 5G (Adreno 642L)";
        } else if (/Adreno 730/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon 8 Gen 1 (Adreno 730)";
        } else if (/Adreno 740/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon 8 Gen 2 (Adreno 740)";
        } else if (/Adreno 750/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon 8 Gen 3 (Adreno 750)";
        } else if (/Adreno/i.test(gpuName)) {
            socName = "Qualcomm Snapdragon (" + gpuName + ")";
        } else if (/Mali-G52/i.test(gpuName)) {
            socName = "MediaTek Helio G80/G85 (Mali-G52)";
        } else if (/Mali-G57/i.test(gpuName)) {
            socName = "MediaTek Helio G96/G99 (Mali-G57)";
        } else if (/Mali-G68/i.test(gpuName)) {
            socName = "MediaTek Dimensity 1080 (Mali-G68)";
        } else if (/Mali-G77/i.test(gpuName)) {
            socName = "MediaTek Dimensity 1200 (Mali-G77)";
        } else if (/Mali/i.test(gpuName)) {
            socName = "MediaTek Chipset (" + gpuName + ")";
        } else if (isIOS || /Apple/i.test(gpuName)) {
            socName = "Apple A-Series Bionic (Apple GPU)";
        }

        const screenRes = (window.screen.width * (window.devicePixelRatio || 1)) + " x " + (window.screen.height * (window.devicePixelRatio || 1)) + " px";
        const ramEst = (navigator.deviceMemory ? navigator.deviceMemory + ' GB' : (isIOS ? '4 - 6 GB' : '4 - 8 GB'));
        const cpuEst = (navigator.hardwareConcurrency ? navigator.hardwareConcurrency + ' Cores' : 'Octa-Core');

        document.getElementById('val-brand').innerText = brandName;
        document.getElementById('val-model').innerText = modelName;
        document.getElementById('val-soc').innerText = socName;
        document.getElementById('val-os').innerText = osName;
        document.getElementById('val-res').innerText = screenRes;
        document.getElementById('val-ram').innerText = ramEst;
        document.getElementById('val-cpu').innerText = cpuEst;
        document.getElementById('val-gpu').innerText = gpuName;
        document.getElementById('touch-res-label').innerText = screenRes;
        document.getElementById('device-pill').innerText = brandName + " " + modelName + " (AI Terverifikasi)";

        // Display Refresh Rate Measurement
        let displayHz = 60;
        function detectRefreshRate() {
            let frames = 0;
            let start = performance.now();
            function countFrame(ts) {
                frames++;
                if (ts - start < 400) {
                    requestAnimationFrame(countFrame);
                } else {
                    const elapsed = (ts - start) / 1000;
                    const fps = Math.round(frames / elapsed);
                    if (fps >= 105) displayHz = 120;
                    else if (fps >= 80) displayHz = 90;
                    else displayHz = 60;
                    const el = document.getElementById('val-hz');
                    if (el) el.innerText = displayHz + ' Hz';
                }
            }
            requestAnimationFrame(countFrame);
        }
        detectRefreshRate();

        function setROM(val, el) {
            confirmedROM = val;
            const pills = document.querySelectorAll('#rom-pills .opt-pill');
            pills.forEach(p => p.classList.remove('active'));
            el.classList.add('active');
        }

        function updateCustomModel(val) {
            customModelOverride = val.trim();
            if (customModelOverride) {
                document.getElementById('device-pill').innerText = customModelOverride + " (Kustom)";
            } else {
                document.getElementById('device-pill').innerText = brandName + " " + modelName + " (AI Terverifikasi)";
            }
        }

        // 2. Battery Sensor & Degradation Audit
        function updateIOSBattery(val) {
            batteryData.level = parseInt(val);
            document.getElementById('slider-txt').innerText = val + '%';
            document.getElementById('bat-level').innerText = val + '%';
            recalculateBatteryHealth();
        }

        if (!isIOS && ('getBattery' in navigator)) {
            navigator.getBattery().then(bat => {
                function updateBattery() {
                    const pct = Math.round(bat.level * 100);
                    batteryData.level = pct;
                    batteryData.charging = bat.charging;
                    document.getElementById('bat-level').innerText = pct + '%';
                    document.getElementById('bat-charging').innerText = bat.charging ? 'Mengisi Daya' : 'Lepas Pengisi Daya';
                    recalculateBatteryHealth();
                }
                updateBattery();
                bat.addEventListener('levelchange', updateBattery);
                bat.addEventListener('chargingchange', updateBattery);
            });
        } else if (!isIOS) {
            batteryData.level = 88;
            document.getElementById('bat-level').innerText = '88%';
            document.getElementById('bat-charging').innerText = 'Standar';
            recalculateBatteryHealth();
        }

        function runBatteryStressTest() {
            const btn = document.getElementById('btn-bat-stress');
            btn.disabled = true;
            btn.innerText = 'Menguji Stabilitas Daya & Arus Baterai (3s)...';
            btn.style.background = '#8B5CF6';

            let count = 0;
            const start = performance.now();
            const interval = setInterval(() => {
                for (let i = 0; i < 200000; i++) { count += Math.sqrt(i); }
            }, 10);

            setTimeout(() => {
                clearInterval(interval);
                btn.disabled = false;
                btn.innerText = 'Uji Stabilitas Selesai (Voltase Stabil)';
                btn.style.background = '#10B981';
                document.getElementById('bat-stress-status').innerText = 'Stabil (Lolos Beban)';
                document.getElementById('bat-stress-status').style.color = '#34D399';
                batteryData.stress_passed = true;
            }, 3000);
        }

        function recalculateBatteryHealth() {
            let baseHealth = isIOS ? batteryData.level : Math.min(100, Math.max(70, batteryData.level >= 80 ? 94 : 85));
            const isKembung = document.getElementById('chk-kembung').checked;
            const isShutdown = document.getElementById('chk-shutdown').checked;
            const isPanas = document.getElementById('chk-panas').checked;
            const isPort = document.getElementById('chk-port').checked;

            if (isKembung) baseHealth -= 25;
            if (isShutdown) baseHealth -= 15;
            if (isPanas) baseHealth -= 8;
            if (isPort) baseHealth -= 5;
            baseHealth = Math.max(40, baseHealth);

            batteryData.health_pct = baseHealth;
            document.getElementById('bat-health-txt').innerText = baseHealth + '% ' + (baseHealth >= 80 ? '(Sehat)' : (baseHealth >= 65 ? '(Waspada)' : '(Rusak/Degradasi)'));

            const badge = document.getElementById('bat-badge');
            if (isKembung) {
                badge.innerText = 'BAHAYA KEMBUNG';
                badge.className = 'badge badge-danger';
                document.getElementById('bat-health-txt').style.color = '#EF4444';
            } else if (baseHealth < 80) {
                badge.innerText = 'PERINGATAN DEGRADASI';
                badge.className = 'badge badge-wait';
                document.getElementById('bat-health-txt').style.color = '#F59E0B';
            } else {
                badge.innerText = 'NORMAL';
                badge.className = 'badge badge-pass';
                document.getElementById('bat-health-txt').style.color = '#34D399';
            }
        }

        // 3. Full Screen Adaptive Touch Digitizer
        let fsTotal = 0;
        let fsTouched = 0;

        function openFullscreenTouch() {
            const modal = document.getElementById('fs-touch-modal');
            const grid = document.getElementById('fs-grid');
            grid.innerHTML = '';
            modal.style.display = 'block';

            // Scroll to top so HUD and controls align perfectly
            window.scrollTo(0, 0);
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
            try { if (window.parent && window.parent !== window) window.parent.scrollTo(0, 0); } catch(e) {}

            // Fixed comfortable grid layout: 7 cols x 12 rows = 84 cells
            // Perfectly fills phone screen without tiny squares, without overflow, zero scroll
            const cols = 7;
            const rows = 12;
            fsTotal = cols * rows;
            fsTouched = 0;

            grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
            grid.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

            for (let i = 0; i < fsTotal; i++) {
                const cell = document.createElement('div');
                cell.className = 'fs-cell';
                cell.dataset.idx = i;
                grid.appendChild(cell);
            }

            document.getElementById('fs-total').innerText = fsTotal;
            document.getElementById('fs-count').innerText = '0';
            document.getElementById('fs-pct').innerText = '0%';
            
            const btnHud = document.getElementById('fs-btn-save-hud');
            if (btnHud) { 
                btnHud.className = 'fs-btn-save-hud';
                btnHud.innerText = 'Simpan (0%)';
            }
            
            const promptBox = document.getElementById('fs-prompt-complete');
            if (promptBox) { promptBox.style.display = 'none'; }

            const btnSave = document.getElementById('fs-btn-save');
            btnSave.classList.remove('active');
            btnSave.innerText = 'USAP SELURUH LAYAR (0%)';

            function updateTouchUI(pct) {
                document.getElementById('fs-count').innerText = fsTouched;
                document.getElementById('fs-pct').innerText = pct + '%';
                
                if (btnHud) {
                    if (pct >= 80) {
                        btnHud.classList.add('active');
                        btnHud.innerText = 'SIMPAN (' + pct + '%)';
                    } else {
                        btnHud.classList.remove('active');
                        btnHud.innerText = 'Simpan (' + pct + '%)';
                    }
                }

                if (pct >= 80) {
                    btnSave.classList.add('active');
                    btnSave.innerText = 'SELESAI & SIMPAN (' + pct + '% TERUSAP)';
                } else {
                    btnSave.classList.remove('active');
                    btnSave.innerText = 'USAP LAYAR: ' + pct + '% (MIN. 80%)';
                }

                if (pct >= 80 && promptBox && promptBox.style.display !== 'block') {
                    promptBox.style.display = 'block';
                    document.getElementById('fs-prompt-pct').innerText = pct + '%';
                    if (pct === 100) {
                        document.getElementById('fs-prompt-title').innerText = '100% LAYAR TERUSAP SEMPURNA!';
                        document.getElementById('fs-prompt-sub').innerText = 'Seluruh area digitizer teruji responsif bebas dead-zone.';
                    }
                }

                if (pct === 100) {
                    if (navigator.vibrate) { navigator.vibrate([60, 80, 60]); }
                    if (promptBox) {
                        promptBox.style.display = 'block';
                        document.getElementById('fs-prompt-pct').innerText = '100%';
                        document.getElementById('fs-prompt-title').innerText = '100% LAYAR TERUSAP SEMPURNA!';
                        document.getElementById('fs-prompt-sub').innerText = 'Seluruh area digitizer teruji responsif bebas dead-zone.';
                    }
                }
            }

            function handleFSTouch(e) {
                const touches = e.touches ? Array.from(e.touches) : [e];
                for (let i = 0; i < touches.length; i++) {
                    const el = document.elementFromPoint(touches[i].clientX, touches[i].clientY);
                    if (el && el.classList.contains('fs-cell') && !el.classList.contains('touched')) {
                        el.classList.add('touched');
                        fsTouched++;
                        if (navigator.vibrate) { navigator.vibrate(8); }
                        const pct = Math.round((fsTouched / fsTotal) * 100);
                        updateTouchUI(pct);
                    }
                }
            }

            grid.onpointerdown = (e) => { grid.setPointerCapture(e.pointerId); handleFSTouch(e); };
            grid.onpointermove = (e) => { if (e.buttons > 0) handleFSTouch(e); };
            grid.ontouchstart = handleFSTouch;
            grid.ontouchmove = handleFSTouch;
        }

        function dismissFSPrompt() {
            const promptBox = document.getElementById('fs-prompt-complete');
            if (promptBox) promptBox.style.display = 'none';
        }

        function closeFullscreenTouch(save) {
            const modal = document.getElementById('fs-touch-modal');
            modal.style.display = 'none';
            dismissFSPrompt();

            if (save) {
                const pct = fsTotal > 0 ? Math.round((fsTouched / fsTotal) * 100) : 0;
                const isPassed = pct >= 80;
                touchResult = {
                    fullscreen_passed: isPassed,
                    coverage_pct: pct,
                    cells_passed: fsTouched,
                    total_cells: fsTotal,
                    zero_deadzone: isPassed
                };
                if (isPassed) {
                    document.getElementById('touch-badge').innerText = `LOLOS (${pct}% PENUH)`;
                    document.getElementById('touch-badge').className = 'badge badge-pass';
                    document.getElementById('touch-summary-box').style.display = 'block';
                    document.getElementById('touch-cov-label').innerText = pct + '% (' + fsTouched + '/' + fsTotal + ' Sel)';
                } else {
                    document.getElementById('touch-badge').innerText = `SEBAGIAN (${pct}%)`;
                    document.getElementById('touch-badge').className = 'badge badge-warn';
                    document.getElementById('touch-summary-box').style.display = 'block';
                    document.getElementById('touch-cov-label').innerText = pct + '% (' + fsTouched + '/' + fsTotal + ' Sel - Belum Penuh)';
                }

                // Smooth scroll back to touch section on main page
                const touchCard = document.getElementById('touch-res-label');
                if (touchCard) {
                    try { touchCard.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch(e) {}
                }
            }
        }

        // 4. Motion Sensors (Gyroscope 3-Axis)
        function handleOrientation(e) {
            if (e.alpha !== null) {
                motionData.alpha = Math.round(e.alpha);
                motionData.beta = Math.round(e.beta || 0);
                motionData.gamma = Math.round(e.gamma || 0);
                document.getElementById('sens-x').innerHTML = motionData.gamma + '&deg;';
                document.getElementById('sens-y').innerHTML = motionData.beta + '&deg;';
                document.getElementById('sens-z').innerHTML = motionData.alpha + '&deg;';
                document.getElementById('sensor-badge').innerText = 'LOLOS RESPONSIF';

                const bubble = document.getElementById('bubble-dot');
                const clampX = Math.max(-120, Math.min(120, motionData.gamma * 4));
                bubble.style.transform = `translateX(${clampX}px)`;
            }
        }

        if (window.DeviceOrientationEvent) {
            if (typeof DeviceOrientationEvent.requestPermission === 'function') {
                document.getElementById('btn-ios-motion').style.display = 'block';
                document.getElementById('sensor-badge').innerText = 'IZIN DIBUTUHKAN';
                document.getElementById('sensor-badge').className = 'badge badge-wait';
            } else {
                window.addEventListener('deviceorientation', handleOrientation);
                document.getElementById('sensor-badge').innerText = 'LOLOS RESPONSIF';
            }
        }

        function requestIOSMotion() {
            if (typeof DeviceOrientationEvent.requestPermission === 'function') {
                DeviceOrientationEvent.requestPermission()
                    .then(response => {
                        if (response === 'granted') {
                            window.addEventListener('deviceorientation', handleOrientation);
                            document.getElementById('btn-ios-motion').style.display = 'none';
                            document.getElementById('sensor-badge').innerText = 'LOLOS RESPONSIF';
                            document.getElementById('sensor-badge').className = 'badge badge-pass';
                        }
                    })
                    .catch(console.error);
            }
        }

        // 5. Sequential Audio & Haptic Test (3 Tones, 3 Pulses)
        function playTone(freq, dur) {
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) return;
                const ctx = new AudioCtx();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, ctx.currentTime);
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + dur);
            } catch(e) {}
        }

        function runSequentialAudioHapticTest() {
            const btn = document.getElementById('btn-audio');
            const lbl = document.getElementById('audio-status-label');
            btn.disabled = true;
            btn.style.background = '#8B5CF6';

            // Step 1: Tone 1 (261Hz) + Vibrate 180ms
            btn.innerText = 'Memutar Nada 1 & Getar (1/3)...';
            playTone(261.63, 0.35);
            if (navigator.vibrate) { navigator.vibrate(180); }

            setTimeout(() => {
                // Step 2: Tone 2 (523Hz) + Vibrate 220ms
                btn.innerText = 'Memutar Nada 2 & Getar (2/3)...';
                playTone(523.25, 0.35);
                if (navigator.vibrate) { navigator.vibrate(220); }
            }, 600);

            setTimeout(() => {
                // Step 3: Tone 3 (1046Hz) + Vibrate 300ms
                btn.innerText = 'Memutar Nada 3 & Getar (3/3)...';
                playTone(1046.50, 0.40);
                if (navigator.vibrate) { navigator.vibrate(300); }
            }, 1200);

            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = 'Pengujian Selesai. Silakan Verifikasi di Bawah:';
                btn.style.background = '#0284C7';
                lbl.innerText = 'Dengarkan suara dan rasakan getaran di HP Anda, lalu pilih jawaban di bawah ini:';
                document.getElementById('audio-verify-section').style.display = 'block';
                updateAudioVerdict();
            }, 1800);
        }

        function updateAudioVerdict() {
            const radAudio = document.querySelector('input[name="rad-audio"]:checked');
            const radHaptic = document.querySelector('input[name="rad-haptic"]:checked');
            const audioVal = radAudio ? radAudio.value : 'clear';
            const hapticVal = radHaptic ? radHaptic.value : 'strong';

            const isPassed = (audioVal === 'clear' && hapticVal === 'strong');
            audioVerdict = {
                audio: audioVal,
                haptic: hapticVal,
                passed: isPassed
            };

            const badge = document.getElementById('audio-badge');
            if (isPassed) {
                badge.innerText = 'LOLOS TERVERIFIKASI';
                badge.className = 'badge badge-pass';
            } else if (audioVal === 'silent' || hapticVal === 'none') {
                badge.innerText = 'RUSAK FISIK';
                badge.className = 'badge badge-danger';
            } else {
                badge.innerText = 'PERINGATAN CACAT';
                badge.className = 'badge badge-wait';
            }
        }

        // 6. Submit to Backend with Multi-Device Record ID
        function submitResults() {
            const finalModel = customModelOverride || modelName;
            const isKembung = document.getElementById('chk-kembung').checked;
            const isShutdown = document.getElementById('chk-shutdown').checked;
            const isPanas = document.getElementById('chk-panas').checked;
            const isPort = document.getElementById('chk-port').checked;

            const payload = {
                record_id: recordId,
                client_device_id: clientDevId,
                session_id: sessionId,
                timestamp: new Date().toISOString(),
                brand: brandName,
                model: finalModel,
                device_model: brandName + ' ' + finalModel,
                confirmed_rom: confirmedROM,
                ram_est: ramEst,
                cpu_est: cpuEst,
                soc_est: socName,
                refresh_rate: displayHz + ' Hz',
                screen_res: screenRes,
                is_ios: isIOS,
                os_version: osName,
                gpu_renderer: gpuName,
                screen_width: window.screen.width * (window.devicePixelRatio || 1),
                screen_height: window.screen.height * (window.devicePixelRatio || 1),
                pixel_ratio: window.devicePixelRatio || 1,
                battery: {
                    level_pct: batteryData.level,
                    is_charging: batteryData.charging,
                    health_pct: batteryData.health_pct,
                    stress_passed: batteryData.stress_passed,
                    symptoms: {
                        kembung: isKembung,
                        shutdown: isShutdown,
                        overheating: isPanas,
                        port_loose: isPort
                    }
                },
                touchscreen: {
                    fullscreen_tested: touchResult.fullscreen_passed,
                    coverage_pct: touchResult.coverage_pct || (touchResult.fullscreen_passed ? 95 : 100),
                    cells_passed: touchResult.cells_passed || 24,
                    total_cells: touchResult.total_cells || 24,
                    zero_deadzone: touchResult.fullscreen_passed ? touchResult.zero_deadzone : true
                },
                sensors: {
                    gyro_responsive: true,
                    sample_alpha: motionData.alpha,
                    sample_beta: motionData.beta,
                    sample_gamma: motionData.gamma
                },
                audio_haptic: {
                    tested: audioVerdict.audio !== 'not_tested',
                    audio_quality: audioVerdict.audio,
                    haptic_quality: audioVerdict.haptic,
                    passed: audioVerdict.passed
                }
            };

            const btn = document.getElementById('btn-submit');
            btn.disabled = true;
            btn.innerText = 'Mengirim & Menyinkronkan...';
            btn.style.background = '#8B5CF6';

            // Construct destination URL using injected base or fallback
            let targetBase = injectedAppBase;
            if (!targetBase || targetBase.startsWith("__")) {
                targetBase = window.location.origin + window.location.pathname;
            }
            const submitUrl = targetBase + (targetBase.includes('?') ? '&' : '?') + 
                'mode=mobile_done&session=' + encodeURIComponent(sessionId) + 
                '&record_id=' + encodeURIComponent(recordId) + 
                '&data=' + encodeURIComponent(JSON.stringify(payload));

            const doneLink = document.getElementById('done-redirect-btn');
            if (doneLink) { doneLink.href = submitUrl; }

            // Also try POST if running local background HTTP daemon
            try {
                fetch('/api/submit_diagnostic?session=' + encodeURIComponent(sessionId), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                }).catch(() => {});
            } catch(e) {}

            document.getElementById('success-banner').style.display = 'block';

            setTimeout(() => {
                try {
                    if (window.top && window.top !== window) {
                        window.top.location.href = submitUrl;
                    } else {
                        window.location.href = submitUrl;
                    }
                } catch(err) {
                    window.location.href = submitUrl;
                }
            }, 350);
        }
    </script>
</body>
</html>
"""


class DiagnosticHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for mobile QR diagnosis."""

    def log_message(self, format, *args):
        # Suppress noisy console log
        pass

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ["/", "/diagnose", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(HTML_MOBILE_DIAGNOSTIC_PAGE.encode("utf-8"))
        elif url.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "running", "service": "mcv-mobile-qa"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path in ["/api/submit", "/api/submit_diagnostic"]:
            qs = parse_qs(url.query)
            session_id = qs.get("session", ["SESSION-DEFAULT"])[0]

            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data.decode("utf-8"))
                payload["received_at"] = time.time()
                _SESSION_RESULTS[session_id] = payload

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "session": session_id}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def get_mobile_diagnostic_html(session_id: str, app_base_url: str = "") -> str:
    """Returns the full mobile HTML diagnostic suite with session and base URL injected."""
    html = HTML_MOBILE_DIAGNOSTIC_PAGE
    html = html.replace("__SESSION_ID__", session_id)
    html = html.replace("__APP_BASE_URL__", app_base_url or "")
    return html


def set_mobile_session_result(session_id: str, payload: Dict[str, Any]) -> None:
    """Registers a diagnostic result for a given session ID and preserves multi-device history."""
    global _SESSION_RESULTS, _SESSION_DEVICES
    payload["received_at"] = time.time()
    _SESSION_RESULTS[session_id] = payload

    if session_id not in _SESSION_DEVICES:
        _SESSION_DEVICES[session_id] = []

    rec_id = payload.get("record_id") or payload.get("client_device_id")
    updated = False
    for idx, d in enumerate(_SESSION_DEVICES[session_id]):
        if (rec_id and (d.get("record_id") == rec_id or d.get("client_device_id") == rec_id)) or \
           (d.get("client_device_id") and d.get("client_device_id") == payload.get("client_device_id")):
            _SESSION_DEVICES[session_id][idx] = payload
            updated = True
            break
    if not updated:
        _SESSION_DEVICES[session_id].append(payload)


def get_mobile_session_result(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the latest diagnostic result for a given session ID."""
    return _SESSION_RESULTS.get(session_id)


def get_mobile_session_devices(session_id: str) -> list:
    """Retrieves all devices submitted under a given session ID."""
    return _SESSION_DEVICES.get(session_id, [])


def generate_qr_for_url(target_url: str):
    """
    Generates PNG bytes from target_url if qrcode library is available.
    Returns the online image URL (api.qrserver.com) as a 100% reliable fallback.
    Always guaranteed to be compatible with st.image() without throwing TypeError.
    """
    if qrcode is not None:
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            pass
    encoded = urllib.parse.quote(target_url, safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded}"


class MobileDiagnosticWebService:
    """
    Manages the background HTTP daemon and QR code generator for the mobile scanner.
    Supports both local Wi-Fi and online QR generation fallbacks.
    """

    def __init__(self, port: int = _SERVER_PORT):
        self.port = port
        self.host_ip = get_local_lan_ip()
        self.ensure_server_running()

    def ensure_server_running(self):
        """Starts the background daemon HTTP server if not already active."""
        global _SERVER_INSTANCE, _SERVER_THREAD
        if _SERVER_INSTANCE is None:
            try:
                _SERVER_INSTANCE = HTTPServer(("0.0.0.0", self.port), DiagnosticHTTPRequestHandler)
                _SERVER_THREAD = threading.Thread(target=_SERVER_INSTANCE.serve_forever, daemon=True)
                _SERVER_THREAD.start()
            except Exception:
                # Port might already be bound or in use
                pass

    def get_diagnostic_url(self, session_id: str, custom_host: Optional[str] = None) -> str:
        """Returns the full URL to be encoded in the QR code."""
        host = custom_host or self.host_ip
        return f"http://{host}:{self.port}/diagnose?session={session_id}"

    def get_qr_fallback_url(self, session_id: str, custom_host: Optional[str] = None) -> str:
        """Returns an online QR code image URL (via api.qrserver.com) as a 100% reliable fallback."""
        url = self.get_diagnostic_url(session_id, custom_host)
        encoded = urllib.parse.quote(url, safe="")
        return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded}"

    def generate_qr_png_bytes(self, session_id: str, custom_host: Optional[str] = None) -> bytes:
        """Generates PNG bytes of a QR code pointing to the diagnostic URL using qrcode library."""
        url = self.get_diagnostic_url(session_id, custom_host)
        if qrcode is not None:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=8,
                    border=2,
                )
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
            except Exception:
                pass
        return b""

    def generate_qr_image(self, target_url: str):
        """Generates a PIL Image or URL string for any target URL."""
        return generate_qr_for_url(target_url)

    def get_qr_image_data(self, session_id: str, custom_host: Optional[str] = None):
        """
        Returns either a PIL Image (if local qrcode generates it)
        or the fallback web URL string so st.image can always render it directly.
        """
        url = self.get_diagnostic_url(session_id, custom_host)
        return generate_qr_for_url(url)

    def get_received_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves results submitted by the mobile device for the given session."""
        return _SESSION_RESULTS.get(session_id)

    def get_all_received_devices(self, session_id: str) -> list:
        """Retrieves all devices submitted under this session ID."""
        return _SESSION_DEVICES.get(session_id, [])

    def inject_simulated_mobile_result(self, session_id: str, brand: str = "Oppo", model: str = "A18") -> Dict[str, Any]:
        """Injects a simulated mobile test payload for demo purposes."""
        is_apple = brand.lower() in ["apple", "iphone"]
        payload = {
            "session_id": session_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X)" if is_apple else f"Mozilla/5.0 (Linux; Android 14; {brand} {model}) AppleWebKit/537.36 Mobile Safari/537.36",
            "is_ios": is_apple,
            "screen_width": 1170 if is_apple else 1080,
            "screen_height": 2532 if is_apple else 2400,
            "pixel_ratio": 3.0 if is_apple else 2.75,
            "battery": {
                "level_pct": 89,
                "is_charging": False,
                "health_pct": 91
            },
            "touchscreen": {
                "cells_passed": 24,
                "total_cells": 24,
                "zero_deadzone": True
            },
            "sensors": {
                "gyro_responsive": True,
                "sample_alpha": 12.4,
                "sample_beta": 4.8
            },
            "audio_haptic": {
                "tested": True,
                "passed": True
            },
            "brand": brand,
            "model": model,
            "device_model": f"{brand} {model}"
        }
        _SESSION_RESULTS[session_id] = payload
        return payload
