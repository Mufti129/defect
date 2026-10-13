# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 13 Oktober 2026*

---

## 1. Ringkasan Eksekutif Model Versi 7
Model Versi 7 (**V7 - Unified Hard Damage & Spatial Density Detector**) dirancang sebagai penyempurnaan komprehensif dari Model V6 dan V5, dengan fokus utama menyatukan deteksi cacat fisik housing dan kerusakan struktural berat (*broken / hard damage*) ke dalam arsitektur terpadu 4-kelas.

### Spesifikasi Pelatihan:
- **Base Architecture**: YOLOv8s Detect ($800 \times 800$ px, 11.2M Parameters)
- **Transfer Learning**: Warm-start dari bobot terbaik V6 (`phone_defect_model_v6_best.pt`)
- **Dataset Latih**: `dataset_v7/` (4.558 citra bodi ponsel multi-view, 26.811 bounding box anotasi riil)
- **Hardware Acceleration**: Apple Silicon GPU via Metal Performance Shaders (`mps`)
- **Proteksi Sleep**: `caffeinate -dms` (PID 25402)
- **Hyperparameter Utama**: Optimizer `AdamW`, `cos_lr=True`, `cls=1.5`, `close_mosaic=10`

---

## 2. Taksonomi 4-Kelas V7 & Distribusi Anotasi
| ID | Kategori Defect | Deskripsi Fisik | Jumlah Box Anotasi |
| :---: | :--- | :--- | :---: |
| `0` | **`scratch`** | Goresan rambut / goresan permukaan cat bodi & kaca | 3.649 |
| `1` | **`chip`** | Cuil, gompal, atau cat terkelupas pada sudut/bezel | 14.112 |
| `2` | **`dent`** | Deformasi lekuk ke dalam pada frame logam/aluminium | 721 |
| `3` | **`hard_damage`** | Kerusakan fisik parah: bodi patah, retak hancur struktural | 109 |
| **Total** | | **Semua Kategori Cacat Teranotasi** | **26.811** |

---

## 3. Status Terkini & Progres Pelatihan (Live Status)
- **Status Proses**: `TRAINING_IN_PROGRESS` (PID 25399 aktif berjalan stabil di MPS)
- **Epoch Saat Ini**: **Epoch 2 / 40**
- **Batch Saat Ini**: **725 / 1.016 batch** (Progres Epoch 2: **71.4%**)
- **Progres Keseluruhan**: **4.28%**
- **Total Batches per Epoch**: 1.016 batch (batch size 4, resolusi 800px)

---

## 4. Hasil Evaluasi Metrik Sementara (Epoch 1 Baseline)
Hasil validasi resmi setelah menyelesaikan Epoch 1 pertama:

| Metrik Evaluasi | Hasil Sementara Epoch 1 | Catatan Analisis |
| :--- | :---: | :--- |
| **Precision (Ketepatan)** | **80.06%** | Sangat tinggi sejak awal berkat transfer learning dari bobot V6 |
| **Recall (Sensitivitas)** | **8.54%** | Wajar di epoch awal karena model baru mulai mengadaptasi mapping kelas baru |
| **mAP@50** | **11.19%** | Baseline awal sebelum fase learning rate decay dan close-mosaic |
| **mAP@50:95 (IoU)** | **4.36%** | Metrik IoU multi-threshold awal |
| **Train Box Loss** | **2.6219** | Regresi bounding box loss training |
| **Val Box Loss** | **2.9716** | Regresi bounding box loss validasi |
| **Train Cls Loss** | **7.9060** | Loss klasifikasi |
| **Val Cls Loss** | **7.3482** | Loss klasifikasi validasi |

---

## 5. Estimasi Waktu Penyelesaian (ETA)
- **Waktu per Epoch**: Rata-rata $\sim 105$ menit ($\sim 1$ jam 45 menit).
- **Sisa Epoch 2**: $\sim 30$ menit.
- **Sisa Epoch 3 s.d. 40 (38 epoch)**: $38 \times 105 \text{ menit} \approx 66.5$ jam.
- **Total Estimasi Sisa Waktu**: **$\sim 67$ jam** (sekitar 2 hari 19 jam).
- **Proyeksi Selesai**: **Kamis, 15 Oktober 2026, $\sim 11:30$ WIB**.

---

## 6. Sinkronisasi Antarmuka & Deployment
- File `training_live_status.json` dan `results.csv` telah disinkronkan secara lokal ke folder aplikasi Streamlit:
  - `streamlit_inspection_app/weights_v7/training_live_status.json`
  - `streamlit_inspection_app/weights_v7/results.csv`
- Dashboard Streamlit pada tab **"Evaluasi Model V7"** akan otomatis membaca live status dan kurva evaluasi ini secara real-time.
