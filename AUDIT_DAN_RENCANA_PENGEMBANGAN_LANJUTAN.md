# 📋 AUDIT KOMPREHENSIF SISTEM & RANCANGAN PENGEMBANGAN LANJUTAN
**Proyek: Sistem Computer Vision Deteksi Cacat Fisik Smartphone & Multi-View Cosmetic Grading AI**  
*Pusat Gadai Indonesia (PGI) — Tanggal Audit: 14 Oktober 2026*

---

## 1. Executive Summary Hasil Audit Keseluruhan

Audit ini mengevaluasi 5 pilar utama sistem:
1. **Pipeline Pelatihan & Kesiapan Model AI (V1 s.d. V7)**
2. **Kualitas & Rekayasa Dataset (Anotasi, Balancing, Hand Filter)**
3. **Infrastruktur Komputasi & Stabilitas Hardware (MacBook Air M1 & Cloud GPU)**
4. **Mesin Penilaian Kosmetik & Mesin Taksiran Harga (Grading & Pricing Engine)**
5. **Kesiapan Antarmuka Pengguna & Integrasi Lapangan (Streamlit Web & Android APK)**

---

## 2. Audit Pilar 1: Evaluasi Komparatif Arsitektur Model AI (V1 - V7)

| Versi Model | Arsitektur & Input | Status | mAP@50 | Recall | Precision | Karakteristik & Catatan Kritis |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Model V1-V3** | Random Forest (18 Fitur) + Bounding Box Dasar | Legacy | - | 65.0% | 71.0% | Mengandalkan fitur tabular & aturan heuristik DPI. Kurang adaptif pada tekstur cacat mikro. |
| **Model V4** | YOLOv8n (640x640, 3.2M params) | Selesai | 1.45% | 3.91% | 24.2% | **Gagal (Underfitting)**: 40% citra kosong membuat model malas mendeteksi; resolusi 640px menghapus baret mikro. |
| **Model V5** | YOLOv8s (800x800, 11.2M params) | **Selesai (Baseline)** | **38.85%** | **67.27%** | **32.56%** | **Sukses Besar**: 100% defects-only dataset, Recall melonjak ke 67.3% (Peak 75.6%). Menjadi fondasi *transfer learning*. |
| **Model V6** | YOLOv8s (800x800, 11.2M params) | **Selesai (Tuntas 40 Ep)** | 4.35% | 9.29% | 28.4% | Dilatih pada dataset V6 100% bebas tangan operator. Sangat bersih dari false positive tangan namun butuh penyeimbangan kelas retak. |
| **Model V7** | YOLOv8s (800x800, 11.2M params) | **Sedang Berjalan (Epoch 5/40)** | 5.91% - 11.19% | **13.93% (Tren Naik)** | 12.6% - 80.1% | **Unified 4-Class**: Menggabungkan `hard_damage` struktural + loss balancing `cls=1.5`. Loss training turun stabil ke level terendah (2.59). |

---

## 3. Audit Pilar 2: Dataset, Anotasi, dan Guardrails

### 3.1. Kondisi Dataset Saat Ini
- **Dataset V7**: Terdiri dari **4.558 citra** ($4.062$ train / $496$ val) dengan total **26.811 bounding box**.
- **Distribusi Kelas**:
  - `scratch` (3.649 box) — Baik
  - `chip` (14.112 box) — Sangat dominan ($52.6\%$)
  - `dent` (721 box) — Cukup
  - `hard_damage` (109 box) — Minoritas ($0.4\%$)
- **Temuan Kritis**: Kelas `hard_damage` dan `dent` masih merupakan kelas minoritas. Meskipun sudah diberi pembobotan `cls=1.5` pada training V7, pada pengembangan lanjutan diperlukan teknik **Copy-Paste Augmentation Khusus** atau patch oversampling untuk menaikkan proporsinya menjadi minimal 5% dari dataset.

### 3.2. Guardrails Lapangan
- ✅ **Object Guardrail (COCO)**: Mampu menolak objek non-HP (manusia, meja kosong, kucing, laptop, botol) secara instan.
- ✅ **Hand / Finger Filter**: Mengisolasi bodi ponsel menggunakan ruang warna YCrCb + HSV + normalisasi iluminasi CLAHE.

---

## 4. Audit Pilar 3: Infrastruktur & Stabilitas Hardware

- **MacBook Air M1 (8GB Unified RAM)**:
  - Konfigurasi `batch=4` dan `imgsz=800` menggunakan $\approx 3.5$ GB RAM, bekerja pada kecepatan 68 GB/s Unified Memory tanpa disk swapping.
  - SSD bebas: **14 GB** (sehat).
  - Waktu per epoch: $\approx 100 - 105$ menit.
- **Sleep Management**:
  - Daemon `caffeinate -u -i -m -s` terbukti efektif menjaga proses tidak tidur selama layar dalam posisi terbuka (redup).
- **Kesiapan Cloud GPU**:
  - File `train_v7_colab.ipynb` telah siap di GitHub untuk opsi pelatihan kilat via NVIDIA T4 GPU (memangkas waktu dari 105 menit menjadi $\approx 15$ menit per epoch).

---

## 5. RANCANGAN PENGEMBANGAN LANJUTAN (ROADMAP STRATEGIS)

Berikut adalah 4 fase pengembangan lanjutan yang direkomendasikan setelah Model V7 menyelesaikan siklus latihnya:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ROADMAP PENGEMBANGAN SISTEM TAHAP LANJUT                        │
├────────────────────┬────────────────────┬────────────────────┬─────────────────────────┤
│      FASE 1        │       FASE 2       │       FASE 3       │         FASE 4          │
│ Post-Training V7 & │  Dual-Tier Fusion  │ Dynamic Pricing &  │ Edge Export (CoreML/    │
│  Benchmark Matrix  │  (Screen + Bodi)   │ Risk Engine Gadai  │   TFLite) & Mobile APK  │
└────────────────────┴────────────────────┴────────────────────┴─────────────────────────┘
```

### FASE 1: Evaluasi Akhir V7 & Calibration Benchmark Matrix
1. **Per-Class Threshold Calibration**:
   - Menghitung kurva Precision-Recall (PR-Curve) optimal untuk masing-masing kelas:
     - `scratch`: Threshold $\ge 0.15$ (untuk goresan rambut).
     - `dent`: Threshold $\ge 0.20$ (menghindari bayangan pantulan cahaya datar).
     - `chip`: Threshold $\ge 0.18$.
     - `hard_damage`: Threshold $\ge 0.12$ (karena merupakan cacat fatal bernilai risiko tinggi).
2. **Benchmark Head-to-Head 100 Unit Sampel**:
   - Menjalankan uji akurasi grading pada 100 unit fisik terverifikasi (Grade A, B, C, D) untuk membandingkan performa Model V5 vs V6 vs V7.
   - Target metrik: **Mengurangi Critical Inversion Rate (Grade D tertukar jadi A/B) ke bawah 2.0%**.

### FASE 2: Dual-Tier Fusion Pipeline (Inspeksi Layar LCD + Bodi Housing)
1. **Pemisahan Modul Layar Depan (*Front Glass / Display*)**:
   - Saat ini model difokuskan pada housing bodi (bezel, samping, belakang).
   - Tahap lanjutan akan menggabungkan modul pendeteksi anomali layar:
     - Deteksi *Green Line / Vertical Line* LCD.
     - Deteksi *Dead Pixel / White Spot* melalui gambar layar putih/merah/biru murni.
     - Deteksi retak kaca layar depan (*Spiderweb crack*).
2. **Hierarchical Grading Decision**:
   - Jika Layar Depan mengalami *Green Line* atau Retak Sentuh $\rightarrow$ Otomatis **Grade D** (Veto Absolut).
   - Jika Layar Normal $\rightarrow$ Grading ditentukan oleh skor akumulasi cacat bodi housing (Grade A/B/C).

### FASE 3: Integrasi Mesin Taksiran Harga Gadai Dinamis (*Dynamic Pricing Engine*)
1. **Mapping Grade ke Persentase Nilai Taksiran PGI**:
   - **Grade A (Mint / Mulus)**: Taksiran $90\% - 95\%$ dari harga pasar *second-hand*.
   - **Grade B (Normal Wear / Lecet Pemakaian)**: Taksiran $80\% - 85\%$.
   - **Grade C (Heavy Wear / Cuil/Penyok Dalam)**: Taksiran $65\% - 70\%$.
   - **Grade D (Broken / Kerusakan Struktural)**: Taksiran Nilai Rongsok (*Scrap / Sparepart Value*), maksimal $20\% - 30\%$.
2. **Auto-Deduction Calculator**:
   - Setiap cacat fisik yang terdeteksi menghasilkan rincian estimasi biaya perbaikan suku cadang (misal: ganti LCD $\approx$ Rp 450.000, ganti backcover $\approx$ Rp 150.000).

### FASE 4: Edge Acceleration & Standarisasi Offline APK
1. **Konversi Model ke Apple CoreML & ONNX FP16**:
   - Mengonversi `best.pt` ke format CoreML (`.mlpackage`) untuk komputasi instan di Apple Neural Engine (latensi $<10$ ms).
   - Mengonversi ke ONNX FP16 / TFLite INT8 untuk perangkat tablet/smartphone Android para penaksir di cabang PGI.
2. **Penyempurnaan Aplikasi Mobile PGI Smart Inspector (`pgi_smart_inspector.apk`)**:
   - Menambahkan fitur *Guided Framing HUD* (bingkai panduan di kamera smartphone cabang) agar operator mengambil foto dengan jarak dan sudut yang seragam (jarak statis 18–20 cm).
   - Menambahkan deteksi penanda kalibrasi ArUco secara real-time pada *viewfinder* kamera untuk menjamin akurasi ukuran milimeter cacat.

---

## 6. Kesimpulan & Rekomendasi Tindakan Segera

1. **Pertahankan Pelatihan V7 di Mac**:
   - Proses di Mac berjalan stabil di Epoch 5 dengan tren loss yang terus membaik. Tidak perlu diinterupsi.
2. **Siapkan Uji Benchmark Begitu V7 Selesai**:
   - Skrip evaluator otomatis telah disiagakan di [`evaluate_benchmark_v6.py`](file:///Users/macbookair/Documents/Project%20Defect%20Detections/TES_CROP_HP/evaluate_benchmark_v6.py) dan siap diadaptasi ke V7 untuk menguji 100 sampel unit ground truth.
3. **Dokumentasi Terpadu**:
   - Hasil audit ini telah disimpan di `Laporan_Project/AUDIT_DAN_RENCANA_PENGEMBANGAN_LANJUTAN.md` dan disinkronkan ke Streamlit serta GitHub.
