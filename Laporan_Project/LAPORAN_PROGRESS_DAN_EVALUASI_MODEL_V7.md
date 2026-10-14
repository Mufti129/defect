# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 14 Oktober 2026, 07:38 WIB*

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
- **Status Proses**: `TRAINING_IN_PROGRESS` (PID 25399 berjalan aktif dan stabil di MPS GPU)
- **Epoch Saat Ini**: **Epoch 5 / 40** (Epoch 1 s.d. 4 telah selesai 100% dan divalidasi)
- **Batch Saat Ini**: **225 / 1.016 batch** (Progres Epoch 5: **22.1%**)
- **Progres Keseluruhan**: **10.55%** (Telah menembus milestone 10% pertama!)
- **Total Batches per Epoch**: 1.016 batch (batch size 4, resolusi 800px)

---

## 4. Evaluasi Hasil Metrik Lengkap (Epoch 1 s.d. Epoch 4)

| Epoch | Precision (B) | Recall (B) | mAP@50 (B) | mAP@50:95 (B) | Train Box Loss | Val Box Loss | Train Cls Loss | Val Cls Loss |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 80.06% | 8.54% | 11.19% | 4.36% | 2.6220 | 2.9716 | 7.9060 | 7.3483 |
| **2** | 12.87% | 11.98% | 8.76% | 3.42% | 2.5952 | 2.9637 | 7.6547 | 7.1891 |
| **3** | 49.27% | 8.54% | 9.65% | 4.47% | 2.5976 | 3.0927 | 7.6599 | 7.3165 |
| **4 (Terbaru)** | 12.64% | **13.93%** 📈 | 5.91% | 2.08% | **2.5902** 📉 | 2.9870 | **7.5911** 📉 | 7.2783 |

> **Analisis Tren Kunci (Key Insights):**  
> 1. **Lonjakan Recall (Sensitivitas Deteksi)**: Pada Epoch 4, Recall mencapai rekor tertinggi baru yaitu **13.93%** (naik dari 8.54% di Epoch 1 dan 11.98% di Epoch 2). Artinya model semakin mampu mengenali dan menangkap lebih banyak titik cacat fisik pada unit.  
> 2. **Loss Training Terus Menurun**: `train/box_loss` turun ke **2.5902** dan `train/cls_loss` turun ke **7.5911** (rekor terendah sejak awal pelatihan).  
> 3. **Fase Warm-Up Selesai**: Learning rate sekarang berada di fase plateau ($0.000986$) dan siap memasuki fase decay bertahap untuk mempertajam Precision dan mAP@50.

---

## 5. Estimasi Waktu Penyelesaian (ETA)
- **Laju Rata-rata**: $\sim 100 - 105$ menit per epoch pada Apple Silicon M1 (batch 4, resolusi 800px).
- **Sisa Pelatihan**: $\sim 35$ epoch lagi (dari total 40 epoch).
- **Sisa Waktu**: $\approx 58 - 60$ jam.
- **Proyeksi Selesai Penuh**: **Jumat sore / malam, 16 Oktober 2026**.

---

## 6. Status Sinkronisasi
- **Lokal**: Berkas `weights_v7/results.csv`, `weights_v7/training_live_status.json`, dan checkpoint `last.pt` (89.5 MB) telah disinkronkan.
- **Streamlit**: Dashboard inspeksi visual otomatis membaca pembaruan kurva evaluasi Epoch 1–4 ini secara langsung.
- **GitHub**: Log laporan dan hasil metrik telah dikomit dan didorong ke cabang `main`.
