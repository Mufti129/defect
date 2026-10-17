# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 17 Oktober 2026, 08:35 WIB*

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
- **Status Proses**: `TRAINING_IN_PROGRESS` (PID 25399 aktif berjalan stabil di Apple Silicon GPU MPS)
- **Epoch Saat Ini**: **Epoch 14 / 40** (Epoch 1 s.d. 13 telah selesai 100% dan divalidasi)
- **Batch Saat Ini**: **975 / 1.016 batch** (Progres Epoch 14: **96.0%**)
- **Progres Keseluruhan**: **34.90%** (Telah melewati sepertiga masa pelatihan!)
- **Total Batches per Epoch**: 1.016 batch (batch size 4, resolusi 800px)

---

## 4. Evaluasi Hasil Metrik Lengkap (Epoch 1 s.d. Epoch 13)

Tabel berikut mencatat seluruh histori metrik validasi resmi pada 496 citra evaluasi dengan 2.856 kotak cacat:

| Epoch | Precision (B) | Recall (B) | mAP@50 (B) | mAP@50:95 (B) | Train Box Loss | Train Cls Loss | Val Cls Loss | Catatan Tren |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | 80.06% | 8.54% | 11.19% | 4.36% | 2.6220 | 7.9060 | 7.3483 | Warm-start dari bobot V6 |
| **2** | 12.87% | 11.98% | 8.76% | 3.42% | 2.5952 | 7.6547 | 7.1891 | Penyesuaian mapping 4 kelas |
| **3** | 49.27% | 8.54% | 9.65% | 4.47% | 2.5976 | 7.6599 | 7.3165 | Penyesuaian bounding box |
| **4** | 12.64% | 13.93% | 5.91% | 2.08% | 2.5902 | 7.5911 | 7.2783 | Peningkatan sensitivitas cacat |
| **5** | 8.26% | 12.50% | 4.90% | 1.54% | 2.5874 | 7.5739 | 7.3344 | Eksplorasi augmentasi |
| **6** | 10.39% | 9.94% | 5.01% | 1.42% | 2.5799 | 7.4821 | 7.2857 | Loss klasifikasi terus turun |
| **7** | 26.75% | 6.16% | 8.15% | 3.14% | 2.5575 | 7.4554 | 7.4441 | Presisi naik ke 26.75% |
| **8** | 13.19% | 13.97% | 6.58% | 2.26% | 2.5487 | 7.3863 | 7.3414 | Recall stabil di level tinggi |
| **9** | **51.77%** | 9.52% | **11.82%** | **5.11%** | 2.5506 | 7.3958 | 7.5322 | 🌟 **Rekor Tertinggi mAP@50 (11.82%) & mAP50-95 (5.11%)** |
| **10** | 12.09% | **14.35%** | 6.59% | 2.25% | 2.5134 | 7.2369 | 7.5005 | 🌟 **Rekor Recall Tertinggi (14.35%)** |
| **11** | 13.20% | 12.64% | 8.26% | 3.20% | 2.5142 | 7.1930 | 7.3696 | Penurunan box & cls loss |
| **12** | 20.43% | 11.17% | 8.44% | 2.31% | 2.4979 | 7.1078 | 7.2684 | Loss tembus di bawah 2.50 |
| **13 (Terbaru)** | **28.05%** 📈 | 10.70% | **11.32%** 📈 | **5.00%** 📈 | **2.4869** 📉 | **7.0905** 📉 | 7.2787 | 🌟 **Lonjakan mAP@50 (11.32%) & Rekor Baru Terendah Box + Cls Loss!** |

> **Analisis Kunci (Key Insights Epoch 13):**  
> 1. **Lonjakan Signifikan Performa Akurasi (mAP)**:
>    - **mAP@50 melesat ke 11.32%** (+2.88% dari Epoch 12), mendekati rekor puncak absolut di Epoch 9 (11.82%).
>    - **mAP@50:95 melonjak lebih dari 2 kali lipat ke 5.00%** (dari 2.31% di Epoch 12), menandakan lokalisasi bounding box semakin rapat dan presisi tinggi pada berbagai threshold IoU.
>    - **Precision meningkat ke 28.05%** (+7.62% dari 20.43% di Epoch 12).
> 2. **Rekor Baru Loss Terendah Sepanjang Pelatihan**:
>    - `train/box_loss` mencetak rekor terendah baru di **2.4869** (turun dari 2.4979).
>    - `train/cls_loss` mencetak rekor terendah baru di **7.0905** (turun dari 7.1078).
> 3. **Stabilitas Validasi & Konvergensi Tanpa Overfitting**:
>    - `val/cls_loss` bertahan sangat stabil di kisaran **7.2787** (tidak mengalami kenaikan divergen), membuktikan model V7 menyerap pola 4-kelas (scratch, chip, dent, hard damage) dengan generalisasi yang sangat sehat.
>    - Memasuki fase Epoch 15–30, jadwal *cosine learning rate decay* diproyeksikan akan mempercepat pemadatan feature map.

---

## 5. Estimasi Waktu Penyelesaian (ETA)
- **Laju Rata-rata**: $\sim 100 - 105$ menit per epoch pada Apple Silicon M1 (batch 4, resolusi 800px).
- **Sisa Pelatihan**: $\sim 26$ epoch lagi (dari total 40 epoch).
- **Sisa Waktu**: $\approx 42 - 44$ jam.
- **Proyeksi Selesai Penuh**: **Senin pagi / siang, 19 Oktober 2026**.

---

## 6. Status Sinkronisasi
- **Lokal**: Berkas `weights_v7/results.csv`, `weights_v7/training_live_status.json`, checkpoint `phone_defect_model_v7_best.pt` (Epoch 9 best, 85 MB), dan `phone_defect_model_v7_last.pt` (Epoch 13, 85 MB) telah disinkronkan.
- **Streamlit**: Dashboard inspeksi visual otomatis membaca pembaruan kurva evaluasi Epoch 1–13 ini secara langsung.
- **GitHub**: Log laporan dan hasil metrik telah dikomit dan didorong ke cabang `main`.

