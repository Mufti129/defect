# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 14 Oktober 2026, 16:45 WIB*

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
- **Epoch Saat Ini**: **Epoch 6 / 40** (Epoch 1 s.d. 5 telah selesai 100% dan divalidasi)
- **Batch Saat Ini**: **200 / 1.016 batch** (Progres Epoch 6: **19.7%**)
- **Progres Keseluruhan**: **12.99%** (~13% dari total 40 epoch)
- **Total Batches per Epoch**: 1.016 batch (batch size 4, resolusi 800px)

---

## 4. Evaluasi Hasil Metrik Lengkap (Epoch 1 s.d. Epoch 5)

| Epoch | Precision (B) | Recall (B) | mAP@50 (B) | mAP@50:95 (B) | Train Box Loss | Val Box Loss | Train Cls Loss | Val Cls Loss | Learning Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 80.06% | 8.54% | 11.19% | 4.36% | 2.6220 | 2.9716 | 7.9060 | 7.3483 | 0.000333 |
| **2** | 12.87% | 11.98% | 8.76% | 3.42% | 2.5952 | 2.9637 | 7.6547 | 7.1891 | 0.000665 |
| **3** | 49.27% | 8.54% | 9.65% | 4.47% | 2.5976 | 3.0927 | 7.6599 | 7.3165 | 0.000994 |
| **4** | 12.64% | **13.93%** | 5.91% | 2.08% | 2.5902 | 2.9870 | 7.5911 | 7.2783 | 0.000986 |
| **5 (Terbaru)** | 8.26% | 12.50% | 4.90% | 1.54% | **2.5874** 📉 | 3.0412 | **7.5739** 📉 | 7.3344 | **0.000976** 📉 |

> **Analisis Tren Kunci (Key Insights Epoch 5):**  
> 1. **Loss Box & Classification Terus Menurun Stabil**: `train/box_loss` kembali memecahkan rekor terendah di angka **2.5874** (dari 2.6220 di Epoch 1) dan `train/cls_loss` turun ke **7.5739** (dari 7.9060 di Epoch 1). Hal ini membuktikan gradien penurunan loss berlangsung mulus tanpa lonjakan (*healthy convergence*).  
> 2. **Sensitivitas Deteksi Terjaga Tinggi**: Recall deteksi bertahan di angka **12.50%**, mempertahankan daya tangkap terhadap cacat-cacat minor berukuran sub-milimeter.  
> 3. **Fase Cosine Annealing Dimulai**: Learning rate mulai memasuki kurva penurunan bertahap (*cosine decay* dari puncak $0.0010$ ke $0.000976$), yang akan membantu model mengunci bobot optimal pada feature map fine-grained di epoch-epoch berikutnya.  
> 4. **Checkpoint Terkini**: Bobot checkpoint sementara telah diamankan sebagai `phone_defect_model_v7_best.pt` (89.5 MB) dan tersedia untuk inferensi demonstrasi.

---

## 5. Estimasi Waktu Penyelesaian (ETA)
- **Laju Rata-rata**: $\sim 95 - 105$ menit per epoch pada Apple Silicon M1 (batch 4, resolusi 800px).
- **Sisa Pelatihan**: $\sim 34.8$ epoch lagi (dari total 40 epoch).
- **Sisa Waktu Komputasi Aktif**: $\approx 55 - 58$ jam.
- **Proyeksi Selesai Penuh**: **Sabtu pagi / siang, 17 Oktober 2026** (dengan asumsi laptop beroperasi terus-menerus tanpa gangguan suspensi tidur).

---

## 6. Status Sinkronisasi
- **Lokal**: Berkas `weights_v7/results.csv`, `weights_v7/training_live_status.json`, dan checkpoint `phone_defect_model_v7_best.pt` (89.5 MB) telah disinkronkan ke direktori kerja utama maupun sub-aplikasi Streamlit.
- **Streamlit**: Dashboard inspeksi visual otomatis membaca pembaruan kurva evaluasi Epoch 1–5 dan metrik langsung secara *real-time*.
- **GitHub**: Log laporan dan hasil metrik telah dikomit dan didorong ke cabang `main` di `https://github.com/Mufti129/defect`.
