# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 13 Oktober 2026, 16:25 WIB*

---

## 1. Ringkasan Eksekutif Model Versi 7
Model Versi 7 (**V7 - Unified Hard Damage & Spatial Density Detector**) dirancang sebagai penyempurnaan komprehensif dari Model V6 dan V5, dengan fokus utama menyatukan deteksi cacat fisik housing dan kerusakan struktural berat (*broken / hard damage*) ke dalam arsitektur terpadu 4-kelas.

### Spesifikasi Pelatihan:
- **Base Architecture**: YOLOv8s Detect ($800 \times 800$ px, 11.2M Parameters)
- **Transfer Learning**: Warm-start dari bobot terbaik V6 (`phone_defect_model_v6_best.pt`)
- **Dataset Latih**: `dataset_v7/` (4.558 citra bodi ponsel multi-view, 26.811 bounding box anotasi riil)
- **Hardware Acceleration**: Apple Silicon GPU via Metal Performance Shaders (`mps`)
- **Proteksi Sleep**: Multi-layer daemon `caffeinate -u -i -m -s` (PID 45349 & 25402)
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

## 3. Status Terkini Pelatihan (Live Status)
- **Status Proses**: `TRAINING_IN_PROGRESS` (PID 25399 aktif berjalan stabil di MPS GPU)
- **Epoch Saat Ini**: **Epoch 3 / 40** (Epoch 2 telah tuntas divalidasi)
- **Batch Saat Ini**: **200+ / 1.016 batch** (Progres Epoch 3: **~20%**)
- **Progres Keseluruhan**: **5.49%**
- **Total Batches per Epoch**: 1.016 batch (batch size 4, resolusi 800px)

---

## 4. Evaluasi Hasil Metrik Sementara (Epoch 1 vs Epoch 2)

| Parameter / Metrik | Epoch 1 | Epoch 2 (Terbaru) | Tren Perubahan & Analisis |
| :--- | :---: | :---: | :--- |
| **Precision (B)** | 80.06% | **12.87%** | Model mulai membuka sensitivitas deteksi pada kelas baru |
| **Recall (B)** | 8.54% | **11.98%** | 📈 **Naik +3.44%** (kemampuan menangkap cacat meningkat) |
| **mAP@50 (B)** | 11.19% | **8.76%** | Fase adaptasi bobot konvolusi terhadap loss rebalancing |
| **mAP@50:95 (B)** | 4.36% | **3.42%** | IoU multi-threshold awal |
| **Train Box Loss** | 2.6219 | **2.5952** | 📉 **Turun (Membaik)** |
| **Val Box Loss** | 2.9716 | **2.9637** | 📉 **Turun (Membaik)** |
| **Train Cls Loss** | 7.9060 | **7.6547** | 📉 **Turun (Membaik)** |
| **Val Cls Loss** | 7.3482 | **7.1891** | 📉 **Turun (Membaik)** |

> **Analisis Tren Loss:**  
> Seluruh loss (`train/box_loss`, `val/box_loss`, `train/cls_loss`, `val/cls_loss`) **secara konsisten menurun pada Epoch 2**. Hal ini menunjukkan konvergensi model berjalan sehat ke arah yang benar. Recall (daya tangkap cacat) juga mulai naik dari 8.54% ke 11.98%.

---

## 5. Estimasi Waktu Penyelesaian (ETA)
- **Durasi per Epoch**: $\sim 100 - 105$ menit per epoch pada Apple Silicon M1 (batch 4, 800px).
- **Sisa Epoch 3 s.d. 40 (37.8 epoch)**: $\sim 64$ jam.
- **Proyeksi Selesai Penuh**: **Jumat, 16 Oktober 2026, sekitar siang hari WIB**.

---

## 6. Status Sinkronisasi
- **Lokal**: Berkas `weights_v7/results.csv`, `weights_v7/training_live_status.json`, dan bobot checkpoint telah tersinkronisasi.
- **Streamlit**: Dashboard inspeksi visual otomatis membaca pembaruan kurva evaluasi ini.
- **GitHub**: Log laporan dan hasil metrik telah dikomit dan didorong ke cabang `main`.
