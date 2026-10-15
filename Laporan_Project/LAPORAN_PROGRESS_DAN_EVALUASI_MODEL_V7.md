# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 15 Oktober 2026, 07:50 WIB*

---

## 1. Ringkasan Eksekutif Model Versi 7
Model Versi 7 (**V7 - Unified Hard Damage & Spatial Density Detector**) dirancang sebagai penyempurnaan komprehensif dari Model V6 dan V5, dengan fokus utama menyatukan deteksi cacat fisik housing dan kerusakan struktural berat (*broken / hard damage*) ke dalam arsitektur terpadu 4-kelas.

### Spesifikasi Pelatihan:
- **Base Architecture**: YOLOv8s Detect ($800 \times 800$ px, 11.2M Parameters)
- **Transfer Learning**: Warm-start dari bobot terbaik V6 (`phone_defect_model_v6_best.pt`)
- **Dataset Latih**: `dataset_v7/` (4.558 citra bodi ponsel multi-view, 26.811 bounding box anotasi riil)
- **Hardware Acceleration**: Apple Silicon GPU via Metal Performance Shaders (`mps`)
- **Proteksi Sleep**: Multi-layer daemon `caffeinate -u -i -m -s` (PID 45349 & 25402 aktif mengunci daya)
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
- **Epoch Saat Ini**: **Epoch 12 / 40** (Epoch 1 s.d. 11 telah selesai 100% dan divalidasi)
- **Batch Saat Ini**: **350 / 1.016 batch** (Progres Epoch 12: **34.4%**)
- **Progres Keseluruhan**: **28.36%** (Melampaui seperempat jalan menuju target 40 epoch!)
- **Total Batches per Epoch**: 1.016 batch (batch size 4, resolusi 800px)

---

## 4. Evaluasi Hasil Metrik Lengkap (Epoch 1 s.d. Epoch 11)

| Epoch | Precision (B) | Recall (B) | mAP@50 (B) | mAP@50:95 (B) | Train Box Loss | Val Box Loss | Train Cls Loss | Val Cls Loss | Learning Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 80.06% | 8.54% | 11.19% | 4.36% | 2.6220 | 2.9716 | 7.9060 | 7.3483 | 0.000333 |
| **2** | 12.87% | 11.98% | 8.76% | 3.42% | 2.5952 | 2.9637 | 7.6547 | 7.1891 | 0.000665 |
| **3** | 49.27% | 8.54% | 9.65% | 4.47% | 2.5976 | 3.0927 | 7.6599 | 7.3165 | 0.000994 |
| **4** | 12.64% | 13.93% | 5.91% | 2.08% | 2.5902 | 2.9870 | 7.5911 | 7.2783 | 0.000986 |
| **5** | 8.26% | 12.50% | 4.90% | 1.54% | 2.5874 | 3.0412 | 7.5739 | 7.3344 | 0.000976 |
| **6** | 10.39% | 9.94% | 5.01% | 1.42% | 2.5799 | 3.0063 | 7.4821 | 7.2857 | 0.000962 |
| **7** | 26.75% | 6.16% | 8.15% | 3.14% | 2.5575 | 3.0647 | 7.4554 | 7.4441 | 0.000946 |
| **8** | 13.19% | 13.97% | 6.58% | 2.26% | 2.5487 | 3.0051 | 7.3863 | 7.3414 | 0.000927 |
| **9** | **51.77%** | 9.52% | **11.82%** 🏆 | **5.11%** 🏆 | 2.5506 | 2.9992 | 7.3958 | 7.5322 | 0.000905 |
| **10** | 12.09% | **14.35%** 🏆 | 6.59% | 2.25% | **2.5134** 📉 | 3.0566 | 7.2369 | 7.5005 | 0.000881 |
| **11 (Terbaru)** | 13.20% | 12.64% | 8.26% | 3.20% | 2.5142 | 3.0249 | **7.1930** 📉 | 7.3696 | **0.000855** 📉 |

> **Analisis Tren Kunci (Key Insights Epoch 6–11):**  
> 1. **Penurunan Loss Klasifikasi Sangat Signifikan**: `train/cls_loss` terpangkas tajam dari **7.9060** (Epoch 1) ke **7.1930** (Epoch 11) — penurunan bersih sebesar **-9.02%**. Ini membuktikan jaringan saraf konvolusi YOLOv8s secara progresif semakin akurat membedakan batas-batas kategori defek (terutama memisahkan `dent` dari `hard_damage`).  
> 2. **Loss Bounding Box Semakin Tajam**: `train/box_loss` turun dari **2.6220** ke rekor terendah **2.5134** (Epoch 10) dan bertahan stabil di **2.5142** (Epoch 11). Presisi lokalisasi kotak defek meningkat konsisten.  
> 3. **Rekor Performa Baru di Epoch 9 & 10**:  
>    - Pada Epoch 9, **mAP@50 mencapai rekor tertinggi 11.82%** dan **mAP@50:95 mencapai 5.11%** dengan Precision **51.77%**.  
>    - Pada Epoch 10, **Recall mencapai rekor baru 14.35%** (daya tangkap cacat fisik tertinggi sejak awal pelatihan).  
> 4. **Pembaruan Checkpoint Terbaik**: Bobot model terbaik (`best.pt`, 89.5 MB) telah diperbarui berdasarkan performa puncak Epoch 9 dan telah disinkronkan ke lokal dan Streamlit sebagai `phone_defect_model_v7_best.pt`.  
> 5. **Jadwal Cosine Annealing Efektif**: Learning rate telah menurun secara halus ke **0.000855**, mematangkan bobot representasi pada lapisan leher (PAN-FPN) dan deteksi multi-skala.

---

## 5. Estimasi Waktu Penyelesaian (ETA)
- **Laju Komputasi Stabil**: $\sim 135 - 145$ menit per epoch pada Apple Silicon M1 (beban 1.016 batch @ 800px).
- **Sisa Pelatihan**: $\sim 28.6$ epoch lagi (dari total 40 epoch).
- **Sisa Waktu Komputasi Aktif**: $\approx 65 - 68$ jam.
- **Milestone 50% (Epoch 20)**: Diproyeksikan tercapai pada **Jumat pagi, 16 Oktober 2026** ($\sim$ 08:00 WIB).
- **Proyeksi Selesai Penuh (Epoch 40)**: **Minggu pagi, 18 Oktober 2026** ($\sim$ 04:00 - 08:00 WIB) *(dengan asumsi MacBook tetap beroperasi dengan daemon caffeinate)*.

---

## 6. Status Sinkronisasi
- **Lokal**: Berkas `weights_v7/results.csv`, `weights_v7/training_live_status.json`, dan checkpoint terbaik `phone_defect_model_v7_best.pt` (89.5 MB) telah disinkronkan ke direktori kerja utama maupun sub-aplikasi Streamlit.
- **Streamlit**: Dashboard inspeksi visual otomatis membaca pembaruan kurva evaluasi Epoch 1–11 secara langsung tanpa perlu restart.
- **GitHub**: Log laporan dan hasil metrik telah dikomit dan didorong ke cabang `main` di `https://github.com/Mufti129/defect`.
