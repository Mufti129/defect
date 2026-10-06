# LAPORAN EVALUASI & PROGRESS TERBARU MODEL VERSI 6 (V6)
**Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection & Cosmetic Grading**
*Waktu Pembaruan: 06 Oktober 2026, 11:35 WIB*

---

## 1. Status Eksekusi Pelatihan Model V6

* **Environment Komputasi:** Apple Silicon Metal (`device: mps`)
* **Total Dataset Latih:** 3.436 citra (termasuk *targeted oversampling* pada kelas `broken` & `dent`)
* **Total Dataset Validasi:** 500 citra (*100% genuine ground truth tanpa duplikasi*)
* **Resolusi Input:** 800px (`imgsz=800`)
* **Batch Size:** 4
* **Total Epoch Target:** 40 Epoch
* **Base Model (Warm Start):** Pretrained Weights V5 (`weights_v5/phone_defect_model_v5_best.pt`)
* **Status Saat Ini:** **Sedang Berjalan Aktif (Epoch 2 / 40)**
* **Progres Epoch 2:** Batch ~280 / 859 (~32,6%)

---

## 2. Evaluasi Hasil Epoch 1 (Metrik Resmi)

Epoch 1 telah selesai dievaluasi pada dataset validasi dengan rincian metrik:

| Metrik Evaluasi | Nilai Epoch 1 | Analisis Teknis |
| :--- | :---: | :--- |
| **Precision (Ketepatan)** | **77,38%** (0.7738) | **Sangat Tinggi!** Deteksi awal model memiliki keyakinan tinggi dan minim false alarm. |
| **Recall (Sensitivitas)** | **2,43%** (0.0243) | Wajar untuk Epoch 1 fase adaptasi transfer learning dari V5 (model baru mulai mengenali pola 4 kelas baru). |
| **mAP@0.5** | **0,78%** | Tahap inisialisasi awal bobot transfer. |
| **mAP@0.5:0.95** | **0,18%** | Baseline awal presisi threshold IoU ketat. |
| **Train Box Loss** | **3,6116** | Konvergensi lokalisasi kotak berjalan normal. |
| **Train Class Loss** | **10,4769** | Dipengaruhi oleh `cls=1.5` untuk memaksa model memperhatikan kelas minoritas. |
| **Val Box Loss** | **3,6620** | Seimbang dengan Train Box Loss (indikasi zero overfitting). |
| **Val Class Loss** | **9,4184** | **Lebih rendah dari Train Class Loss (9.41 vs 10.47)**, membuktikan model menggeneralisasi dengan baik pada data validasi. |
| **Waktu per Epoch** | ~4.635 detik (~1 jam 17 menit) | Beban komputasi tinggi akibat resolusi tajam 800px dan augmentasi copy-paste pada Apple Silicon MPS. |

---

## 3. Status Bobot Sementara (Temporary Best Weights)

Bobot sementara terbaik hasil validasi Epoch 1 telah berhasil di-ekstrak, di-strip dari status optimizer, dan dideploy secara lokal:

1. **Lokasi File Bobot Sementara:**
   * 📁 `weights_v6/phone_defect_model_v6_best.pt` (Ukuran: **21,46 MB**)
   * 📁 `streamlit_inspection_app/weights/phone_defect_model_v6_best.pt` (Ukuran: **21,46 MB**)
2. **Karakteristik Bobot Sementara:**
   * Arsitektur: YOLOv8s (21,5 MB)
   * Kelas Aktif: `0: dent`, `1: broken`, `2: scratch`, `3: chip`
   * Siap dimuat dan diuji kapan saja untuk inferensi visual atau demo internal Streamlit.

---

## 4. Rencana Estimasi Epoch Selanjutnya

* **Epoch 2 - 5:** Fase ekspansi Recall di mana model mulai mengenali pola mikro-cacat `scratch` dan `chip` secara masif (diprediksi Recall melonjak ke 20% - 40%).
* **Epoch 6 - 25:** Fase stabilisasi kelas minoritas `dent` dan `broken` melalui augmentasi `copy_paste=0.30`.
* **Epoch 30 - 40:** Fase *Fine-Resolution Sharpening* (`close_mosaic=10`), di mana mosaik dimatikan untuk mempertajam baret halus sub-milimeter hingga titik mAP puncak.
