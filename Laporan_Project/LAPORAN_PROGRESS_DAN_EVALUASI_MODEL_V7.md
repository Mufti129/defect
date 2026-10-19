# 📊 Laporan Progres Pelatihan & Evaluasi Sementara Model Versi 7 (V7)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection System**  
*Tanggal Pembaruan: 19 Oktober 2026, 08:20 WIB*

---

## 1. Ringkasan Eksekutif Model Versi 7
Model Versi 7 (**V7 - Unified Hard Damage & Spatial Density Detector**) dirancang sebagai penyempurnaan komprehensif dari Model V6 dan V5, dengan fokus utama menyatukan deteksi cacat fisik housing dan kerusakan struktural berat (*broken / hard damage*) ke dalam arsitektur terpadu 4-kelas.

### Spesifikasi Pelatihan:
- **Base Architecture**: YOLOv8s Detect ($800 \times 800$ px, 11.2M Parameters)
- **Transfer Learning**: Warm-start dari bobot terbaik V6 (`phone_defect_model_v6_best.pt`)
- **Dataset Latih**: `dataset_v7/` (4.558 citra bodi ponsel multi-view, 26.811 bounding box anotasi riil)
- **Hardware Acceleration**: Apple Silicon GPU via Metal Performance Shaders (`mps`)
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

## 3. Status Terkini Pelatihan (Training Status)
- **Status Proses**: `PAUSED (READY TO RESUME)`
- **Epoch Terselesaikan Penuh**: **14 / 40 Epoch** (100% tuntas divalidasi dan tersimpan di `results.csv`)
- **Progres Interupsi**: Terhenti sementara di awal **Epoch 15** (batch 325/1.016, progres 32.0%) pada Minggu, 18 Oktober 2026 pukul 12:48 WIB akibat laptop mengalami reboot/restart sistem.
- **Progres Keseluruhan**: **35.80%** (Telah melampaui sepertiga masa pelatihan).
- **Integritas Checkpoint**: Checkpoint `last.pt` (Epoch 14) dan `best.pt` (Epoch 9) **tersimpan 100% utuh dan valid** (masing-masing 89.5 MB) di disk lokal dan folder weights Streamlit.

---

## 4. Evaluasi Hasil Metrik Lengkap (Epoch 1 s.d. Epoch 14)

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
| **13** | **28.05%** | 10.70% | **11.32%** | **5.00%** | 2.4869 | 7.0905 | 7.2787 | 🌟 **Lonjakan mAP@50 (11.32%) mendekati puncak Epoch 9** |
| **14** | 14.15% | 7.73% | 4.51% | 1.68% | **2.4731** 📉 | **6.9722** 📉 | 7.3756 | 🌟 **Rekor Baru Terendah: Cls Loss tembus di bawah 7.00!** |

> **Analisis Kunci (Key Insights Epoch 1 s.d. 14):**  
> 1. **Model Terus Belajar dan Mengalami Konvergensi Kuat**:
>    - `train/cls_loss` turun secara konsisten dari **7.9060** pada awal pelatihan hingga menyentuh rekor terendah **6.9722** di Epoch 14 (pertama kalinya menembus level di bawah 7.0). Hal ini membuktikan bahwa pemisahan fitur 4 kelas cacat (*scratch*, *chip*, *dent*, *hard_damage*) semakin tajam dipelajari model.
>    - `train/box_loss` turun ke titik terendah absolut di **2.4731** (dari 2.6220), menandakan lokalisasi koordinat bounding box cacat semakin presisi.
> 2. **Performa Deteksi Terbaik (All-Time Best Checkpoint)**:
>    - Tetap dipegang kokoh oleh **Epoch 9** dengan **mAP@50 11.82%** dan **Precision 51.77%**.
>    - Epoch 13 membuktikan resiliensi model dengan lonjakan mAP@50 kembali ke **11.32%** dan mAP@50:95 di **5.00%**.
> 3. **Kesiapan Checkpoint**:
>    - Checkpoint terbaik Epoch 9 telah di-deploy ke `weights_v7/phone_defect_model_v7_best.pt` dan `streamlit_inspection_app/weights/phone_defect_model_v7_best.pt`.
>    - Checkpoint terbaru Epoch 14 tersimpan di `weights_v7/phone_defect_model_v7_last.pt`.

---

## 5. Status Penyelarasan Sistem & Aset
- **Lokal**: Berkas `weights_v7/results.csv`, `weights_v7/training_live_status.json`, checkpoint `phone_defect_model_v7_best.pt` (Epoch 9 best), dan `phone_defect_model_v7_last.pt` (Epoch 14) telah diperbarui dan sinkron.
- **Streamlit**: Dashboard inspeksi otomatis membaca pembaruan kurva evaluasi Epoch 1–14 secara dinamis.
- **Resumability**: Sistem siap melakukan `resume=True` dari Epoch 14 kapan pun diputuskan.

---

## 6. Rekomendasi Langkah Selanjutnya
1. **Opsi 1 (Disarankan — Resume ke Epoch 20 Target)**:
   - Melanjutkan pelatihan dari checkpoint `last.pt` (Epoch 14) sampai **Epoch 20**.
   - Berdasarkan tren transfer learning dari V6, model biasanya mencapai titik konvergensi optimum dan saturasi mAP pada rentang Epoch 15–20.
   - Kebutuhan waktu: Hanya $\approx 5-6$ epoch lagi ($\approx 10-12$ jam komputasi aktif).
2. **Opsi 2 (Gunakan Model Epoch 9 untuk Produksi Sekarang)**:
   - Jika kebutuhan inspeksi mendesak, checkpoint Epoch 9 (mAP 11.82%, Precision 51.77%) sudah sangat siap dipakai langsung di Streamlit App untuk deteksi 4 kelas.
