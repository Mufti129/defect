# 📱 Aplikasi Web Inspeksi Cacat Fisik & Cosmetic Grading Housing Smartphone AI (Streamlit)

Aplikasi web interaktif siap deploy (*deployable*) untuk melakukan inspeksi cacat fisik bodi smartphone secara otomatis menggunakan **YOLOv8-Seg (Polygon Instance Segmentation)**, estimasi dimensi fisik sub-milimeter, serta **Machine Learning Cosmetic Grading (Random Forest 18 Fitur dengan Fast-Fail Veto Safeguards)** yang dilatih pada skala penuh (>9.000 citra / 1.918 unit smartphone).

---

## 🚀 Fitur Utama & Pembaruan Terkini

1. **Pipeline Inspeksi 4 Sisi Housing Bodi (*Top, Bottom, Left, Right*):**
   - **Mode Demo 1-Click:** Langsung pilih sampel unit riil dari database (Grade A, B, C, atau D) atau pilih jalan pintas kasus audit investigasi lapangan (*Oppo A5i Sompal, iPhone 13 Pro Max Presisi Bodi, iPhone 16 Mulus*).
   - **Mode Upload Mandiri 4 Sisi:** Unggah foto 4 sisi bodi smartphone secara terpisah dan terstruktur.
2. **Implementasi Hasil Investigasi Teknis & Evaluasi Empiris:**
   - **Gaussian Centrality Weighting:** Memastikan pemotongan bodi terkunci presisi di tengah kanvas, mengeliminasi kesalahan potong meja kosong (*Case 1 Solved*).
   - **Edge-Aware Defect Detection:** Pengecekan posisi cacat terhadap kontur bodi ponsel asli (`phone_edge_dilated`), filter USB khusus sisi `bottom`, dan HandFilter threshold dinaikkan ke 0.40 pada outer edge (*Case 2 Solved*).
   - **Fast-Fail Veto Safeguards:** Menjamin cacat sompal/pecah (`broken` atau `chip >= 4.0mm`) langsung divonis **GRADE D**, mencegah kerugian akibat *over-grading*.
   - **Soft ROI Guided Masking:** Menghindari *hard background removal* yang berisiko meratakan cacat sompal/pecah (*Paradoks Sompal*) dan mematikan kontras bezel gelap.
3. **Modul Knowledge Hub "📑 Laporan Investigasi & Evaluasi Empiris":**
   - Menampilkan dokumentasi lengkap investigasi 2 kasus kritis lapangan, analisis strategis penghapusan background, tabel uji empiris before vs after, serta matriks kebingungan (4x4 Confusion Matrix) benchmark 100 unit.
4. **Visual Inspection Collage Card:**
   - Menghasilkan kartu rangkuman inspeksi visual 4 sisi berkualitas tinggi (dengan badge Grade, rincian DPI, breakdown cacat, dan bounding box/poligon).
   - Tombol unduh langsung gambar kartu inspeksi dalam format High-Res JPEG.
5. **Detail Breakdown Cacat Fisik:**
   - Menampilkan tabel interaktif dimensi cacat: Panjang ($mm$), Luas ($mm^2$), tingkat keparahan, dan zona penalti.
6. **Alasan & Probabilitas Model AI:**
   - Transparansi penuh alasan penetapan Grade (apakah lolos ambang batas atau terkena Veto Rule retak/pecah).
   - Diagram probabilitas klasifikasi per grade ($P(A), P(B), P(C), P(D)$).
7. **Batch Folder Testing (Housing-Only):**
   - Jalankan uji massal pada puluhan unit sekaligus untuk 4 sisi bodi dan unduh ringkasan hasil dalam format CSV.
8. **Standardisasi Matras (Tray Marker A4 300 DPI):**
   - Unduh template matras ArUco standar untuk meja inspeksi di cabang.

---

## 💻 Cara Menjalankan Aplikasi Secara Lokal

### Opsi 1: Menggunakan Script Peluncur Otomatis (Direkomendasikan)
Jalankan perintah berikut di terminal:
```bash
./run_app.sh
```
Aplikasi akan otomatis mendeteksi environment dan membuka antarmuka di:
👉 **`http://localhost:8501`**

### Opsi 2: Menjalankan Manual dengan Streamlit CLI
```bash
# Dari root proyek
.venv/bin/streamlit run streamlit_inspection_app/app.py --server.port 8501
```

---

## 🐳 Cara Deploy Menggunakan Docker

Jika Anda ingin mendeploy aplikasi ini ke cloud server (AWS EC2, Google Cloud Run, Railway, atau VPS internal PGI):

1. **Build Docker Image:**
   ```bash
   cd streamlit_inspection_app
   docker build -t phone-inspection-app:latest .
   ```

2. **Jalankan Kontainer:**
   ```bash
   docker run -d -p 8501:8501 --name phone_grading_system phone-inspection-app:latest
   ```

3. Akses melalui browser pada IP server Anda: `http://<IP-SERVER>:8501`.

---

## 📋 Struktur File Folder `streamlit_inspection_app/`

```
streamlit_inspection_app/
├── app.py                # Antarmuka web utama Streamlit (Versi 3.2 Housing-Only)
├── core_engine.py        # Adapter inferensi YOLOv8-Seg + Random Forest ML
├── defect_detector.py    # Engine deteksi cacat poligon & filter kontur bodi
├── grading_engine.py     # Kalkulasi metrik penalti DPI & koordinasi grading
├── ml_grading_aggregator.py # Model Random Forest & Veto Safeguards
├── hand_filter.py        # Isolasi jari operator berbasis YCrCb + HSV
├── spatial_scaler.py     # Kalibrasi dimensi fisik ArUco & homografi
├── weights/              # Bobot model terlatih (phone_defect_model.pt & ml_grading_model.joblib)
├── demo_samples/         # Sampel unit riil untuk demo cepat (Grade A-D)
├── run_app.sh            # Script bash 1-perintah untuk menjalankan aplikasi
├── requirements.txt      # Daftar dependensi Python
├── Dockerfile            # Konfigurasi containerized deployment
└── README.md             # Dokumentasi teknis dan panduan operasional
```
