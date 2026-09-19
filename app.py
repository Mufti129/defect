#!/usr/bin/env python3
"""
STREAMLIT INSPECTION WEB APPLICATION
====================================
Interactive multi-view smartphone defect detection, physical measurement,
cosmetic grading, and inspection card generation.
"""

import os
import sys
import io
import json
import time
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import numpy as np
import cv2
import pandas as pd
from PIL import Image

# Setup paths
APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core_engine import StreamlitInspectionEngine

# ---------------------------------------------------------
# Page Configuration & Modern Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Smartphone Inspection & Grading System",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling cards, grade badges, and clean UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .grade-badge-A {
        background: linear-gradient(135deg, #10B981, #059669);
        color: white;
        padding: 18px 24px;
        border-radius: 12px;
        text-align: center;
        font-weight: 800;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
    }
    .grade-badge-B {
        background: linear-gradient(135deg, #F59E0B, #D97706);
        color: white;
        padding: 18px 24px;
        border-radius: 12px;
        text-align: center;
        font-weight: 800;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35);
    }
    .grade-badge-C {
        background: linear-gradient(135deg, #F97316, #EA580C);
        color: white;
        padding: 18px 24px;
        border-radius: 12px;
        text-align: center;
        font-weight: 800;
        box-shadow: 0 4px 14px rgba(249, 115, 22, 0.35);
    }
    .grade-badge-D {
        background: linear-gradient(135deg, #EF4444, #DC2626);
        color: white;
        padding: 18px 24px;
        border-radius: 12px;
        text-align: center;
        font-weight: 800;
        box-shadow: 0 4px 14px rgba(239, 68, 68, 0.35);
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Cached Engine Initialization
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Memuat Model YOLOv8-Seg dan ML Grading Aggregator...")
def get_engine():
    local_weights = APP_DIR / "weights"
    if local_weights.exists() and (local_weights / "phone_defect_model.pt").exists():
        weights_path = local_weights
    else:
        weights_path = PROJECT_DIR / "weights"
    return StreamlitInspectionEngine(weights_dir=str(weights_path))


engine = get_engine()

# ---------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/fluency/96/phone.png", width=64)
st.sidebar.title("Sistem Taksiran AI")
st.sidebar.caption("PGI Computer Vision & ML Grading Platform")

nav_choice = st.sidebar.radio(
    "Navigasi Modul:",
    [
        "🔍 Inspeksi Unit (Upload / Demo)",
        "📂 Batch Folder Testing",
        "📐 Standar Matras (Tray Marker)",
        "ℹ️ Panduan SOP & Arsitektur"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("**Spesifikasi Model Aktif:**")
st.sidebar.markdown("""
- **Defect Model:** `YOLOv8-Seg (Polygon)`
- **Device Scaling:** `ArUco + Dynamic Homography`
- **Grading Engine:** `Random Forest (18 Features)`
- **Safety Rule:** `Fast-Fail Veto Safeguard`
""")


# ---------------------------------------------------------
# Module 1: Single Unit Inspection (Upload or Demo)
# ---------------------------------------------------------
if nav_choice == "🔍 Inspeksi Unit (Upload / Demo)":
    st.markdown('<div class="main-header">📱 Inspeksi Cacat Fisik & Grading Smartphone</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Analisis multi-sudut pandang dengan segmentasi poligon presisi sub-milimeter dan estimasi Grade otomatis.</div>', unsafe_allow_html=True)

    input_mode = st.radio(
        "Pilih Metode Masukan Foto:",
        ["📁 Demo 1-Click (Gunakan Unit Riil Database)", "📤 Upload Foto 5 Sudut Pandang Sendiri"],
        horizontal=True
    )

    unit_id_input = "demo-unit"
    view_files_dict = {}

    local_samples = APP_DIR / "demo_samples"
    if (PROJECT_DIR / "Hasil_Crop_Raw").exists():
        crop_base = PROJECT_DIR / "Hasil_Crop_Raw"
    elif local_samples.exists():
        crop_base = local_samples
    else:
        crop_base = APP_DIR

    if input_mode == "📁 Demo 1-Click (Gunakan Unit Riil Database)":
        col_grade, col_unit = st.columns([1, 2])

        with col_grade:
            target_grade = st.selectbox("Pilih Target Grade:", ["Grade B (Mayoritas)", "Grade A (Mulus)", "Grade C (Aus Wajar)", "Grade D (Cacat Berat)"])
            grade_folder = {
                "Grade A (Mulus)": "grade_A",
                "Grade B (Mayoritas)": "grade_B",
                "Grade C (Aus Wajar)": "grade_C",
                "Grade D (Cacat Berat)": "grade_D"
            }[target_grade]

        with col_unit:
            selected_grade_path = crop_base / grade_folder
            available_units = []
            if selected_grade_path.exists():
                available_units = sorted([d.name for d in selected_grade_path.iterdir() if d.is_dir()])
            
            if available_units:
                chosen_unit = st.selectbox(f"Pilih Sampel Unit Riil ({len(available_units)} tersedia):", available_units[:100])
                unit_id_input = chosen_unit
                unit_dir = selected_grade_path / chosen_unit

                for side in ["front", "back", "left", "right", "top", "bottom"]:
                    p_jpg = unit_dir / f"{side}.jpg"
                    p_png = unit_dir / f"{side}.png"
                    if p_jpg.exists():
                        view_files_dict[side] = str(p_jpg)
                    elif p_png.exists():
                        view_files_dict[side] = str(p_png)
            else:
                st.warning(f"Direktori {selected_grade_path} tidak ditemukan.")

        if view_files_dict:
            st.info(f"Unit terpilih: **{unit_id_input}** ({len(view_files_dict)} sudut foto terdeteksi: {', '.join(view_files_dict.keys())})")
            # Preview thumbnails
            t_cols = st.columns(len(view_files_dict))
            for i, (side, path) in enumerate(view_files_dict.items()):
                with t_cols[i]:
                    st.image(path, caption=side.upper(), use_container_width=True)

    else:
        # Manual Upload Mode
        unit_id_input = st.text_input("Unit ID / No. Seri Smartphone:", value="HP-REAL-TEST-001")
        st.markdown("**Unggah Foto Sudut Pandang (Minimal Front / Layar Depan):**")

        up_col1, up_col2, up_col3, up_col4, up_col5 = st.columns(5)
        
        with up_col1:
            f_front = st.file_uploader("1. Front (Layar)", type=["jpg", "jpeg", "png"], key="up_front")
        with up_col2:
            f_back = st.file_uploader("2. Back (Bodi)", type=["jpg", "jpeg", "png"], key="up_back")
        with up_col3:
            f_left = st.file_uploader("3. Left (Samping Kiri)", type=["jpg", "jpeg", "png"], key="up_left")
        with up_col4:
            f_right = st.file_uploader("4. Right (Samping Kanan)", type=["jpg", "jpeg", "png"], key="up_right")
        with up_col5:
            f_bottom = st.file_uploader("5. Bottom (Bawah/Port)", type=["jpg", "jpeg", "png"], key="up_bottom")

        upload_map = {
            "front": f_front,
            "back": f_back,
            "left": f_left,
            "right": f_right,
            "bottom": f_bottom
        }

        temp_dir = tempfile.mkdtemp(prefix="st_upload_")
        for side, file_obj in upload_map.items():
            if file_obj is not None:
                save_path = os.path.join(temp_dir, f"{side}.jpg")
                with open(save_path, "wb") as f:
                    f.write(file_obj.getbuffer())
                view_files_dict[side] = save_path

    # Trigger Inspection Button
    st.write("")
    run_btn = st.button("🚀 Jalankan Inspeksi & Grading AI", type="primary", use_container_width=True)

    if run_btn:
        if not view_files_dict:
            st.error("Harap pilih atau unggah minimal satu foto sudut pandang smartphone.")
        else:
            with st.spinner("Menjalankan inferensi multi-view YOLOv8-Seg, estimasi spasial ArUco, dan evaluasi Machine Learning..."):
                t0 = time.time()
                report, card_bgr = engine.run_unit_inspection(unit_id_input, view_files_dict)
                elapsed = time.time() - t0

            grade = report.get("final_grade", "D")
            confidence = report.get("grade_confidence", 0.0)
            total_dpi = report.get("total_dpi", 0.0)
            front_dpi = report.get("front_dpi", 0.0)
            defects_count = report.get("total_defects_count", 0)

            st.success(f"Analisis selesai dalam {elapsed:.2f} detik!")

            # -----------------------------------------
            # Top Summary Metrics & Grade Hero
            # -----------------------------------------
            st.divider()
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns([1.5, 1, 1, 1, 1])

            with m_col1:
                badge_html = f"""
                <div class="grade-badge-{grade}">
                    <div style="font-size: 0.85rem; letter-spacing: 0.1em;">HASIL GRADED AI</div>
                    <div style="font-size: 2.8rem; line-height: 1.1;">GRADE {grade}</div>
                    <div style="font-size: 0.85rem; margin-top: 4px;">Keyakinan: {confidence*100:.1f}%</div>
                </div>
                """
                st.markdown(badge_html, unsafe_allow_html=True)

            with m_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Total Cacat</div>
                    <div class="metric-value">{defects_count}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">titik terdeteksi</div>
                </div>
                """, unsafe_allow_html=True)

            with m_col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Total DPI</div>
                    <div class="metric-value">{total_dpi:.1f}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">Defect Penalty</div>
                </div>
                """, unsafe_allow_html=True)

            with m_col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Front DPI</div>
                    <div class="metric-value">{front_dpi:.1f}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">Layar Depan</div>
                </div>
                """, unsafe_allow_html=True)

            with m_col5:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Kecepatan</div>
                    <div class="metric-value">{elapsed:.2f}s</div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">5-sudut pandang</div>
                </div>
                """, unsafe_allow_html=True)

            # -----------------------------------------
            # Inspection Collage Card Visual Display
            # -----------------------------------------
            st.subheader("🖼️ Kartu Hasil Inspeksi Visual (Inspection Card)")
            
            # Convert BGR to RGB for Streamlit
            card_rgb = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2RGB)
            st.image(card_rgb, use_container_width=True, caption=f"Inspection Card - Unit ID: {unit_id_input}")

            # Download Button for the High-Res Card
            is_success, buffer = cv2.imencode(".jpg", card_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            if is_success:
                st.download_button(
                    label="📥 Unduh Kartu Hasil Inspeksi (High-Res JPG)",
                    data=buffer.tobytes(),
                    file_name=f"inspection_card_{unit_id_input}_{grade}.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )

            # -----------------------------------------
            # Detailed Analysis Tabs
            # -----------------------------------------
            st.write("")
            tab1, tab2, tab3 = st.tabs([
                "📊 Rincian Cacat Fisik (Breakdown)",
                "🧠 Penjelasan Keputusan Model AI",
                "📄 Dokumen Data JSON Lengkap"
            ])

            with tab1:
                defects_detail = report.get("defects_detail", [])
                if defects_detail:
                    df_defects = []
                    for idx, d in enumerate(defects_detail, 1):
                        df_defects.append({
                            "No": idx,
                            "Sudut (View)": d.get("view_side", "").upper(),
                            "Jenis Cacat": d.get("class_name", "").capitalize(),
                            "Panjang (mm)": f"{d.get('length_mm', 0.0):.2f} mm",
                            "Luas (mm²)": f"{d.get('area_mm2', 0.0):.2f} mm²",
                            "Confidence": f"{d.get('confidence', 0.0)*100:.1f}%",
                            "Bounding Box": str(d.get("bbox", []))
                        })
                    st.dataframe(pd.DataFrame(df_defects), use_container_width=True)
                else:
                    st.success("🎉 Tidak ditemukan cacat fisik terukur. Unit dalam kondisi mulus (Flawless / Grade A)!")

                # Breakdown counts
                bd = report.get("defect_breakdown", {})
                b_cols = st.columns(5)
                b_cols[0].metric("Dent (Penyok)", bd.get("dent", 0))
                b_cols[1].metric("Scratch (Lecet)", bd.get("scratch", 0))
                b_cols[2].metric("Chip (Gompal)", bd.get("chip", 0))
                b_cols[3].metric("Crack (Retak)", bd.get("crack", 0))
                b_cols[4].metric("Broken (Pecah)", bd.get("broken", 0))

            with tab2:
                st.markdown("#### Faktor Penentu Keputusan:")
                reasons = report.get("reasons", [])
                for r in reasons:
                    st.markdown(f"- 📌 **{r}**")

                st.markdown("#### Distribusi Probabilitas Grade:")
                probs = report.get("grade_probabilities", {})
                if probs:
                    prob_df = pd.DataFrame({
                        "Grade": list(probs.keys()),
                        "Probabilitas": [v * 100 for v in probs.values()]
                    })
                    st.bar_chart(prob_df.set_index("Grade"))

            with tab3:
                st.json(report)
                st.download_button(
                    label="📥 Unduh Laporan JSON",
                    data=json.dumps(report, indent=2),
                    file_name=f"inspection_report_{unit_id_input}.json",
                    mime="application/json"
                )


# ---------------------------------------------------------
# Module 2: Batch Testing from Folder
# ---------------------------------------------------------
elif nav_choice == "📂 Batch Folder Testing":
    st.markdown('<div class="main-header">📂 Batch Inspection & Pengujian Massal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Jalankan pengujian grading otomatis pada puluhan unit smartphone sekaligus dari direktori lokal.</div>', unsafe_allow_html=True)

    default_batch_path = str(PROJECT_DIR / "Hasil_Crop_Raw" / "grade_B")
    batch_dir_str = st.text_input("Path Folder Target Pengujian:", value=default_batch_path)
    limit_units = st.slider("Jumlah Unit yang Akan Diuji:", min_value=2, max_value=50, value=10)

    start_batch = st.button("🚀 Mulai Batch Testing", type="primary")

    if start_batch:
        b_path = Path(batch_dir_str)
        if not b_path.exists():
            st.error(f"Folder '{batch_dir_str}' tidak ditemukan.")
        else:
            unit_dirs = sorted([d for d in b_path.iterdir() if d.is_dir()])[:limit_units]
            if not unit_dirs:
                st.warning("Tidak ada sub-folder unit ditemukan dalam direktori tersebut.")
            else:
                st.info(f"Memulai evaluasi pada {len(unit_dirs)} unit...")
                progress_bar = st.progress(0)
                status_text = st.empty()

                batch_results = []
                t_batch_start = time.time()

                for i, u_dir in enumerate(unit_dirs):
                    status_text.text(f"Memproses unit {i+1}/{len(unit_dirs)}: {u_dir.name}")
                    v_dict = {}
                    for side in ["front", "back", "left", "right", "top", "bottom"]:
                        p_jpg = u_dir / f"{side}.jpg"
                        p_png = u_dir / f"{side}.png"
                        if p_jpg.exists():
                            v_dict[side] = str(p_jpg)
                        elif p_png.exists():
                            v_dict[side] = str(p_png)

                    if v_dict:
                        t_u0 = time.time()
                        report = engine.grading_engine.evaluate_phone_unit(u_dir.name, v_dict)
                        lat = time.time() - t_u0

                        batch_results.append({
                            "Unit ID": u_dir.name,
                            "Predicted Grade": report.get("final_grade"),
                            "Confidence": f"{report.get('grade_confidence', 0.0)*100:.1f}%",
                            "Total DPI": report.get("total_dpi"),
                            "Front DPI": report.get("front_dpi"),
                            "Defects": report.get("total_defects_count"),
                            "Latency (s)": round(lat, 2)
                        })

                    progress_bar.progress((i + 1) / len(unit_dirs))

                total_time = time.time() - t_batch_start
                status_text.text("Batch testing selesai!")

                st.success(f"Berhasil menguji {len(batch_results)} unit dalam {total_time:.2f} detik (Rata-rata: {total_time/len(batch_results):.2f}s per unit).")

                df_batch = pd.DataFrame(batch_results)
                st.dataframe(df_batch, use_container_width=True)

                # Distribution Chart
                grade_counts = df_batch["Predicted Grade"].value_counts().reset_index()
                grade_counts.columns = ["Grade", "Jumlah Unit"]
                st.subheader("Distribusi Grade Hasil Prediksi:")
                st.bar_chart(grade_counts.set_index("Grade"))

                # Download CSV
                csv_bytes = df_batch.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Unduh Ringkasan Hasil Pengujian (CSV)",
                    data=csv_bytes,
                    file_name="batch_inspection_results.csv",
                    mime="text/csv"
                )


# ---------------------------------------------------------
# Module 3: Tray Marker Standardization
# ---------------------------------------------------------
elif nav_choice == "📐 Standar Matras (Tray Marker)":
    st.markdown('<div class="main-header">📐 Standar Matras Inspeksi (Tray Marker A4)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Standarisasi pengambilan gambar untuk akurasi metrik fisik sub-milimeter dan eliminasi bayangan tangan.</div>', unsafe_allow_html=True)

    local_marker = APP_DIR / "static" / "tray_marker_template.png"
    if local_marker.exists():
        marker_path = local_marker
    else:
        marker_path = PROJECT_DIR / "static" / "tray_marker_template.png"

    col_img, col_info = st.columns([1.2, 1])

    with col_img:
        if marker_path.exists():
            st.image(str(marker_path), caption="Template Matras Inspeksi Resmi A4 300 DPI", use_container_width=True)
            with open(str(marker_path), "rb") as f:
                btn = st.download_button(
                    label="📥 Unduh Template Matras Cetak A4 (300 DPI PNG)",
                    data=f.read(),
                    file_name="tray_marker_template_A4_300DPI.png",
                    mime="image/png",
                    type="primary",
                    use_container_width=True
                )
        else:
            st.warning("File template matras belum digenerate.")

    with col_info:
        st.markdown("""
        ### Spesifikasi Teknis Matras:
        - **Ukuran Kertas:** A4 Standar (210 x 297 mm, 300 DPI).
        - **Fiducial Markers:** 4x ArUco Markers (`DICT_4X4_50`, IDs 0, 1, 2, 3) di setiap sudut.
        - **Koreksi Perspektif:** Matriks Homografi 4-titik otomatis merektifikasi kemiringan kamera operator.
        - **Area Peletakan HP:** Kotak siluet 175 x 85 mm (muat seluruh tipe smartphone hingga varian Pro Max / Ultra).
        - **Mistar Metrik:** Mistar fisik 100 mm di tepi horizontal dan vertikal untuk verifikasi kalibrasi manual.

        ### Prosedur Operasional Standar (SOP) di Cabang:
        1. Cetak template ini pada kertas A4 tanpa scale (*Actual Size / 100% scale*).
        2. Letakkan di atas meja inspeksi dengan pencahayaan merata.
        3. Posisikan smartphone di dalam kotak siluet tengah.
        4. Ambil 5 sudut foto (*Front, Back, Left, Right, Bottom*) menggunakan aplikasi kamera inspeksi.
        """)


# ---------------------------------------------------------
# Module 4: Guidelines & Architecture
# ---------------------------------------------------------
elif nav_choice == "ℹ️ Panduan SOP & Arsitektur":
    st.markdown('<div class="main-header">ℹ️ Arsitektur Sistem & Rekomendasi SOP PGI</div>', unsafe_allow_html=True)

    st.markdown("""
    ### 1. SOP Pemeriksaan 2-Tahap di Cabang Gadai
    Untuk mencapai keandalan taksiran tertinggi, terapkan prosedur 2 tahap berikut:

    ```
    [Tahap 1: Checklist Fungsional Cepat (Staf Kasir)]
      └─ Cek Daya: Nyala / Mati?
      └─ Cek Kunci: iCloud / Akun Google terkunci?
      └─ Cek Layar & Sentuh: Berfungsi normal?
      └─ Cek Kamera & Getar: Normal?
         │
         ├── GAGAL ──> LANGSUNG GRADE D (Kerusakan Fungsional Mesin)
         └── LOLOS ──> LANJUT KE TAHAP 2 (AI Visual Inspection)
                         │
                         ▼
    [Tahap 2: AI Computer Vision & ML Grading]
      └─ Foto 5 sudut pada Matras ArUco Standar
      └─ Deteksi Cacat Poligon (YOLOv8-Seg)
      └─ Eliminasi Pantulan Cahaya (Specular Glare Filter)
      └─ ML Grading Aggregator (Random Forest 18 Fitur)
      └─ HASIL: GRADE A, B, atau C Otomatis
    ```

    ---

    ### 2. Ambang Batas Grading Resmi
    - **Grade A (Mint / Flawless):**
      - Bebas dari retak, pecah, atau gompal.
      - Layar depan mulus (DPI Layar $\le 1.5$).
      - Total lecet mikro bodi maksimal 2 titik dengan panjang $< 2.0$ mm.
    - **Grade B (Very Good / Wajar Ringan):**
      - Layar depan bebas retak fisik.
      - Lecet halus pemakaian normal diperbolehkan (panjang lecet $\ge 1.8$ mm ditoleransi).
      - Penyok minor bodi samping $\le 2$ titik kecil ($< 3.5\text{ mm}^2$).
      - Total DPI $< 25.0$.
    - **Grade C (Good / Aus Nyata):**
      - Cacat bodi jamak, cat terkelupas (*chips*), atau penyok samping multipel.
      - Layar bebas retak pecah tembus.
      - Total DPI $25.0 \le \text{DPI} < 50.0$.
    - **Grade D (Faulty / Cacat Berat / Rusak):**
      - Retak layar kaca (*cracks* $\ge 2$ titik atau panjang $\ge 8.0$ mm).
      - Bodi pecah struktural (*broken* $> 0$).
      - Total DPI $\ge 50.0$.
    """)
