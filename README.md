# 📱 Aplikasi Web Inspeksi Cacat & Cosmetic Grading Smartphone AI (Streamlit)

Aplikasi web interaktif siap deploy (*deployable*) untuk melakukan inspeksi cacat fisik smartphone secara otomatis menggunakan **YOLOv8-Seg (Polygon Instance Segmentation)**, estimasi dimensi fisik sub-milimeter, serta **Machine Learning Cosmetic Grading (Random Forest dengan Veto Safeguards)**.

---

## 🚀 Fitur Utama

1. **Inspeksi Interaktif 5 Sudut Pandang (*Front, Back, Left, Right, Bottom*):**
   - **Mode Demo 1-Click:** Langsung pilih sampel unit riil dari database (Grade A, B, C, atau D) tanpa perlu upload manual.
   - **Mode Upload Mandiri:** Unggah foto smartphone dari kamera atau file lokal.
2. **Visual Inspection Collage Card:**
   - Menghasilkan kartu rangkuman inspeksi visual berkualitas tinggi (dengan badge Grade, rincian DPI, breakdown cacat, dan kotak bounding box/poligon).
   - Tombol unduh langsung gambar kartu inspeksi dalam format High-Res JPEG.
3. **Detail Breakdown Cacat Fisik:**
   - Menampilkan tabel interaktif dimensi cacat: Panjang ($mm$), Luas ($mm^2$), tingkat keparahan, dan zona penalti.
4. **Alasan & Probabilitas Model AI:**
   - Transparansi penuh alasan penetapan Grade (apakah lolos ambang batas atau terkena Veto Rule retak/pecah).
   - Diagram probabilitas klasifikasi per grade ($P(A), P(B), P(C), P(D)$).
5. **Batch Folder Testing:**
   - Jalankan uji massal pada puluhan unit sekaligus dan unduh ringkasan hasil dalam format CSV.
6. **Standardisasi Matras (Tray Marker A4 300 DPI):**
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
├── app.py                # Antarmuka web utama Streamlit
├── core_engine.py        # Adapter inferensi YOLOv8-Seg + Random Forest ML
├── run_app.sh            # Script bash 1-perintah untuk menjalankan aplikasi
├── requirements.txt      # Daftar dependensi Python
├── Dockerfile            # Konfigurasi containerized deployment
└── README.md             # Dokumentasi teknis dan panduan operasional
```
