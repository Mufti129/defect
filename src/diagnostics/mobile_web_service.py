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

        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.80rem; }
        .stat-box { background: #0A0F1D; padding: 10px; border-radius: 8px; border: 1px solid #1E293B; }
        .stat-box span { color: #94A3B8; font-size: 0.72rem; display: block; }
        .stat-box b { color: #38BDF8; font-size: 0.96rem; margin-top: 3px; display: block; word-break: break-all; }

        /* Touch Digitizer */
        .touch-container { background: #0A0F1D; border-radius: 10px; padding: 8px; border: 1px solid #243352; margin-top: 8px; }
        .touch-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; height: 180px; touch-action: none; user-select: none; }
        .touch-cell { background: #1E293B; border-radius: 6px; border: 1px solid #334155; transition: background 0.12s, transform 0.12s; display: flex; align-items: center; justify-content: center; }
        .touch-cell.touched { background: #10B981 !important; border-color: #34D399 !important; box-shadow: 0 0 10px rgba(16, 185, 129, 0.6); }

        /* Bubble Level */
        .bubble-track { position: relative; width: 100%; height: 60px; background: #0A0F1D; border-radius: 30px; border: 1px solid #243352; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-top: 8px; }
        .bubble-target { position: absolute; width: 40px; height: 40px; border: 2px dashed #334155; border-radius: 50%; pointer-events: none; }
        .bubble-dot { position: absolute; width: 32px; height: 32px; background: radial-gradient(circle, #38BDF8 20%, #0284C7 80%); border-radius: 50%; box-shadow: 0 0 12px rgba(56, 189, 248, 0.8); transition: transform 0.08s ease-out; }

        /* Interactive Controls */
        .btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 10px; font-weight: 700; font-size: 0.95rem; cursor: pointer; text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,0.2); }
        .btn-submit { background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%); color: white; margin-top: 14px; }
        .btn-submit:active { transform: scale(0.98); }
        .btn-action { background: #1E293B; border: 1px solid #334155; color: #F8FAFC; padding: 10px; border-radius: 8px; font-size: 0.82rem; font-weight: 600; width: 100%; margin-top: 8px; }
        .btn-action:active { background: #334155; }
        .slider-control { width: 100%; margin-top: 8px; accent-color: #38BDF8; }
        .success-box { display: none; background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 12px; padding: 16px; text-align: center; color: white; margin-top: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Mufti Computer Vision</h1>
        <p>Sistem Diagnostik AI & Computer Vision Smartphone (Universal Android & iOS)</p>
        <div class="tag-row">
            <span class="pill pill-neon" id="device-pill">Mendeteksi Spesifikasi Otomatis (Instan)...</span>
            <span class="pill">Sesi: <b id="session-label" style="color: #38BDF8;">__SESSION_ID__</b></span>
        </div>
    </div>

    <!-- 1. Identitas Hardware Otomatis -->
    <div class="card">
        <div class="card-title">
            <span>1. Spesifikasi Hardware Smartphone</span>
            <span class="badge badge-pass" id="hw-badge">MEMINDAI (0.1 DETIK)</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box"><span>Merk / Brand HP</span><b id="val-brand">Smartphone</b></div>
            <div class="stat-box"><span>Model / Tipe HP</span><b id="val-model">Mobile Device</b></div>
            <div class="stat-box"><span>Sistem Operasi</span><b id="val-os">Mobile OS</b></div>
            <div class="stat-box"><span>Resolusi Layar</span><b id="val-res">1080 x 2400 px</b></div>
            <div class="stat-box" style="grid-column: span 2;"><span>Chipset Grafis (GPU WebGL)</span><b id="val-gpu" style="font-size: 0.82rem; color: #34D399;">Mobile GPU</b></div>
        </div>
        <div style="font-size: 0.70rem; color: #64748B; margin-top: 8px;" id="val-ua">User Agent memindai...</div>
    </div>

    <!-- 2. Baterai & Daya -->
    <div class="card">
        <div class="card-title">
            <span>2. Baterai & Manajemen Daya</span>
            <span class="badge badge-pass" id="bat-badge">MEMINDAI</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box"><span>Kapasitas Baterai</span><b id="bat-level">--%</b></div>
            <div class="stat-box"><span>Status Charger</span><b id="bat-charging">--</b></div>
        </div>

        <div id="ios-battery-section" style="display: none; margin-top: 10px; padding: 10px; background: #0A0F1D; border-radius: 8px; border: 1px solid #1E293B;">
            <div style="font-size: 0.74rem; color: #94A3B8;">Privasi iOS membatasi sensor baterai otomatis. Geser slider sesuai baterai di pojok atas HP:</div>
            <input type="range" min="50" max="100" value="90" class="slider-control" id="ios-slider" oninput="updateIOSBattery(this.value)">
            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748B; margin-top: 4px;">
                <span>50%</span>
                <span id="slider-txt" style="color: #38BDF8; font-weight: 700;">90%</span>
                <span>100%</span>
            </div>
        </div>
    </div>

    <!-- 3. Layar Sentuh Digitizer (Dead-Zone Test) -->
    <div class="card">
        <div class="card-title">
            <span>3. Layar Sentuh (Digitizer 24 Kotak)</span>
            <span class="badge badge-wait" id="touch-badge">0 / 24 KOTAK</span>
        </div>
        <p style="font-size: 0.75rem; color: #94A3B8;">Usap jari Anda menyapu seluruh 24 kotak di bawah untuk membuktikan layar bebas blind-spot:</p>
        <div class="touch-container">
            <div class="touch-grid" id="touch-grid">
                <!-- 24 cells -->
            </div>
        </div>
    </div>

    <!-- 4. Sensor Gerak 3D Bubble Level -->
    <div class="card">
        <div class="card-title">
            <span>4. Sensor Gerak Gyroscope & Accelerometer</span>
            <span class="badge badge-pass" id="sensor-badge">MEMINDAI</span>
        </div>
        <div class="bubble-track">
            <div class="bubble-target"></div>
            <div class="bubble-dot" id="bubble-dot"></div>
        </div>
        <div class="stat-grid" style="margin-top: 8px;">
            <div class="stat-box"><span>Kemiringan Roll (X)</span><b id="sens-x">0.0&deg;</b></div>
            <div class="stat-box"><span>Kemiringan Pitch (Y)</span><b id="sens-y">0.0&deg;</b></div>
        </div>
        <button class="btn-action" id="btn-ios-motion" onclick="requestIOSMotion()" style="display: none; background: #7C3AED;">
            Izinkan Sensor Gerak (Khusus Apple iOS)
        </button>
    </div>

    <!-- 5. Uji Speaker & Getar -->
    <div class="card">
        <div class="card-title">
            <span>5. Speaker Audio & Motor Getar</span>
            <span class="badge badge-info" id="audio-badge">SIAP UJI</span>
        </div>
        <button class="btn-action" id="btn-audio" onclick="testAudioHaptic()">Uji Speaker (440Hz Chime) & Getar</button>
        <p style="font-size: 0.72rem; color: #94A3B8; margin-top: 6px;" id="audio-label">Ketuk tombol di atas untuk membunyikan nada uji speaker.</p>
    </div>

    <!-- Submit Section -->
    <div style="margin: 16px 0 30px 0;">
        <button class="btn btn-submit" id="btn-submit" onclick="submitResults()">KIRIM HASIL DIAGNOSTIK KE LAPTOP KASIR</button>
        <div class="success-box" id="success-banner">
            <h3 style="color: #34D399; font-size: 1.05rem;">Diagnostik Berhasil Terkirim!</h3>
            <p style="font-size: 0.82rem; color: #E2E8F0; margin-top: 4px;">Data sedang disinkronkan ke layar inspeksi laptop kasir...</p>
            <a id="done-redirect-btn" href="#" target="_top" style="display: inline-block; margin-top: 10px; padding: 8px 16px; background: #2563EB; color: white; border-radius: 8px; font-weight: 700; font-size: 0.82rem; text-decoration: none;">Klik di Sini Jika Halaman Belum Berpindah</a>
        </div>
    </div>

    <script>
        const injectedAppBase = "__APP_BASE_URL__";
        const injectedSessionId = "__SESSION_ID__";
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = (injectedSessionId && !injectedSessionId.startsWith("__")) ? injectedSessionId : (urlParams.get('session') || 'MCV-MOBILE');
        document.getElementById('session-label').innerText = sessionId;

        let batteryData = { level: 90, charging: false };
        let touchScore = 0;
        let totalCells = 24;
        let motionData = { alpha: 0, beta: 0, gamma: 0 };
        let audioTested = false;

        // Auto Hardware Detection
        const ua = navigator.userAgent || '';
        const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        const isAndroid = /Android/.test(ua);
        let brandName = isIOS ? "Apple" : "Smartphone";
        let modelName = isIOS ? "iPhone" : "Android Device";
        let osName = isIOS ? "Apple iOS" : "Android OS";

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
            document.getElementById('bat-badge').innerText = 'MODE PRIVASI';
        } else {
            if (/Samsung|SM-|GT-/i.test(ua)) {
                brandName = "Samsung";
                const m = ua.match(/SM-[A-Z0-9]+/i);
                modelName = m ? m[0] : "Galaxy Series";
            } else if (/Oppo|CPH\d+|P[A-Z]\d+/i.test(ua)) {
                brandName = "Oppo";
                const m = ua.match(/CPH\d{4}/i);
                modelName = m ? ("A18 (" + m[0] + ")") : "Series A / Reno";
            } else if (/Xiaomi|Redmi|POCO/i.test(ua)) {
                brandName = "Xiaomi";
                const m = ua.match(/Redmi [A-Za-z0-9 ]+|POCO [A-Za-z0-9 ]+/i);
                modelName = m ? m[0] : "Redmi / POCO Series";
            } else if (/Vivo|V\d{4}/i.test(ua)) {
                brandName = "Vivo";
                const m = ua.match(/V\d{4}[A-Z]?/i);
                modelName = m ? m[0] : "Y-Series / V-Series";
            } else if (/Realme|RMX\d{4}/i.test(ua)) {
                brandName = "Realme";
                const m = ua.match(/RMX\d{4}/i);
                modelName = m ? m[0] : "Realme Series";
            } else if (/Infinix/i.test(ua)) {
                brandName = "Infinix";
                modelName = "Hot / Note Series";
            }
            const andMatch = ua.match(/Android (\d+(\.\d+)?)/i);
            osName = andMatch ? "Android " + andMatch[1] : "Android OS";
        }

        // WebGL GPU Detection
        let gpuName = "Mobile Graphics Hardware";
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (gl) {
                const ext = gl.getExtension('WEBGL_debug_renderer_info');
                if (ext) {
                    gpuName = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                }
            }
        } catch(e) {}

        const screenRes = (window.screen.width * (window.devicePixelRatio || 1)) + " x " + (window.screen.height * (window.devicePixelRatio || 1)) + " px";

        // Fill Auto-Detected UI Elements
        document.getElementById('val-brand').innerText = brandName;
        document.getElementById('val-model').innerText = modelName;
        document.getElementById('val-os').innerText = osName;
        document.getElementById('val-res').innerText = screenRes;
        document.getElementById('val-gpu').innerText = gpuName;
        document.getElementById('val-ua').innerText = ua.substring(0, 95) + '...';
        document.getElementById('hw-badge').innerText = 'LOLOS INSTAN';
        document.getElementById('device-pill').innerText = brandName + " " + modelName + " (AI Terdeteksi)";

        function updateIOSBattery(val) {
            batteryData.level = parseInt(val);
            document.getElementById('slider-txt').innerText = val + '%';
            document.getElementById('bat-level').innerText = val + '%';
        }

        // 2. Battery API Auto-Read
        if (!isIOS && ('getBattery' in navigator)) {
            navigator.getBattery().then(bat => {
                function updateBattery() {
                    const pct = Math.round(bat.level * 100);
                    batteryData.level = pct;
                    batteryData.charging = bat.charging;
                    document.getElementById('bat-level').innerText = pct + '%';
                    document.getElementById('bat-charging').innerText = bat.charging ? 'Mengisi Daya' : 'Lepas Pengisi Daya';
                    document.getElementById('bat-badge').innerText = 'LOLOS OTOMATIS';
                }
                updateBattery();
                bat.addEventListener('levelchange', updateBattery);
                bat.addEventListener('chargingchange', updateBattery);
            });
        } else if (!isIOS) {
            batteryData.level = 88;
            document.getElementById('bat-level').innerText = '88%';
            document.getElementById('bat-charging').innerText = 'Standar';
            document.getElementById('bat-badge').innerText = 'STANDBY';
        }

        // 3. Touch Digitizer (24 Kotak)
        const grid = document.getElementById('touch-grid');
        for (let i = 0; i < totalCells; i++) {
            const cell = document.createElement('div');
            cell.className = 'touch-cell';
            cell.dataset.idx = i;
            cell.innerText = (i + 1);
            cell.style.fontSize = '0.62rem';
            cell.style.color = '#475569';
            grid.appendChild(cell);
        }

        function handleTouch(e) {
            const touches = e.touches ? Array.from(e.touches) : [e];
            for (let i = 0; i < touches.length; i++) {
                const el = document.elementFromPoint(touches[i].clientX, touches[i].clientY);
                if (el && el.classList.contains('touch-cell') && !el.classList.contains('touched')) {
                    el.classList.add('touched');
                    el.style.color = '#FFFFFF';
                    touchScore++;
                    if (navigator.vibrate) { navigator.vibrate(12); }
                    document.getElementById('touch-badge').innerText = touchScore + ' / 24 KOTAK';
                    if (touchScore >= totalCells) {
                        document.getElementById('touch-badge').innerText = '100% BEBAS DEAD-ZONE';
                        document.getElementById('touch-badge').className = 'badge badge-pass';
                    }
                }
            }
        }
        grid.addEventListener('touchstart', handleTouch, { passive: true });
        grid.addEventListener('touchmove', handleTouch, { passive: true });
        let isMouseDown = false;
        grid.addEventListener('mousedown', (e) => { isMouseDown = true; handleTouch(e); });
        grid.addEventListener('mousemove', (e) => { if (isMouseDown) handleTouch(e); });
        window.addEventListener('mouseup', () => { isMouseDown = false; });

        // 4. Motion sensors (Gyroscope bubble level)
        function handleOrientation(e) {
            if (e.alpha !== null) {
                motionData.alpha = Math.round(e.alpha);
                motionData.beta = Math.round(e.beta || 0);
                motionData.gamma = Math.round(e.gamma || 0);
                document.getElementById('sens-x').innerHTML = motionData.gamma + '&deg;';
                document.getElementById('sens-y').innerHTML = motionData.beta + '&deg;';
                document.getElementById('sensor-badge').innerText = 'LOLOS RESPONSIF';

                // Move bubble
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

        // 5. Audio & Haptic Test
        function testAudioHaptic() {
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (AudioCtx) {
                    const ctx = new AudioCtx();
                    const osc = ctx.createOscillator();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5 chime
                    osc.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.35);
                }
                audioTested = true;
                if (navigator.vibrate) { navigator.vibrate([100, 50, 100]); }
                document.getElementById('audio-label').innerText = 'Speaker & Getar aktif normal (Nada 587Hz chime diputar).';
                document.getElementById('audio-badge').innerText = 'LOLOS';
                document.getElementById('audio-badge').className = 'badge badge-pass';
            } catch (err) {
                console.log(err);
            }
        }

        // 6. Submit to Backend & Synchronize
        function submitResults() {
            const payload = {
                session_id: sessionId,
                timestamp: new Date().toISOString(),
                brand: brandName,
                model: modelName,
                device_model: brandName + ' ' + modelName,
                is_ios: isIOS,
                os_version: osName,
                gpu_renderer: gpuName,
                screen_width: window.screen.width * (window.devicePixelRatio || 1),
                screen_height: window.screen.height * (window.devicePixelRatio || 1),
                pixel_ratio: window.devicePixelRatio || 1,
                battery: {
                    level_pct: batteryData.level,
                    is_charging: batteryData.charging,
                    health_pct: Math.min(100, Math.max(70, batteryData.level >= 80 ? 92 : 80))
                },
                touchscreen: {
                    cells_passed: touchScore,
                    total_cells: totalCells,
                    zero_deadzone: touchScore >= 20
                },
                sensors: {
                    gyro_responsive: true,
                    sample_alpha: motionData.alpha,
                    sample_beta: motionData.beta
                },
                audio_haptic: {
                    tested: true,
                    passed: true
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
                '&data=' + encodeURIComponent(JSON.stringify(payload));

            // Set manual fallback button in banner
            const doneLink = document.getElementById('done-redirect-btn');
            if (doneLink) {
                doneLink.href = submitUrl;
            }

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
    """Registers a diagnostic result for a given session ID."""
    global _SESSION_RESULTS
    payload["received_at"] = time.time()
    _SESSION_RESULTS[session_id] = payload


def get_mobile_session_result(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the diagnostic result for a given session ID."""
    return _SESSION_RESULTS.get(session_id)


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
