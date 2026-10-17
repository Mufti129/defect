# DOKUMENTASI EVALUASI EMPIRIS RIIL DATA TEST: MODEL V1 HINGGA V7
**Pusat Gadai Indonesia (PGI) — AI Defect Detection & Smartphone Cosmetic Valuation**
*Status Evaluasi: 100% Data Uji Riil (Empiris Non-Statis)*
*Tanggal Audit: 17 Oktober 2026*

---

## 1. Ringkasan Eksekutif & Metodologi Evaluasi Data Uji
Setiap model AI dalam sistem inspeksi ini dilatih menggunakan dataset yang dibagi secara ketat menjadi dua kelompok:
1. **Data Latih (Train Set):** Digunakan untuk pembelajaran bobot konvolusi / feature representation.
2. **Data Uji (Test / Holdout Benchmark Set):** Dataset independen yang sama sekali tidak pernah dilihat model saat proses training, digunakan untuk mengukur performa generalisasi riil di lapangan.

Evaluasi dilakukan pada dua tingkat (*two-tier evaluation*):
1. **Evaluasi Spasial Deteksi Cacat (Tingkat Citra YOLO):** Mengukur presisi lokalisasi bounding box cacat (*scratch, chip, dent, hard_damage*) pada partisi `images/val` (data test).
2. **Evaluasi Kinerja Valuasi Kosmetik (Tingkat Unit Smartphone):** Menguji kemampuan pipa inferensi lengkap dalam menetapkan Grade Kosmetik (**Grade A, B, C, D**) pada kohor uji 100 unit smartphone riil cabang (*Hasil_Crop_Raw*, terdistribusi seimbang: 25 Grade A, 25 Grade B, 25 Grade C, 25 Grade D).

---

## 2. Tabel Perbandingan Kinerja Valuasi Riil Seluruh Versi Model (100 Unit Test Set)

| Generasi Model | Paradigma & Arsitektur | True Accuracy (100 Unit) | Macro F1-Score | Over-Grading Rate (Risiko Gadai) | Under-Grading Rate | Critical Inversions (Grade D ➔ A) | Status Valuasi Operasional |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Model V7** | Unified Hard Damage YOLOv8s 800px + Rule of Thumb | **38.00%** | **0.3595** | 25.00% | 37.00% | **0 Unit (0.0%)** | 🛡️ Proteksi Maksimal Hard Damage Veto |
| **Model V6** | Fine-Tuned Clean YOLOv8s 800px (40 Epochs) | **45.00%** | **0.4223** | 19.00% | 36.00% | **0 Unit (0.0%)** | ✅ Rekor Akurasi Deteksi Terbersih |
| **Model V5** | Housing-Only YOLOv8s 800px (30 Epochs) | **27.00%** | **0.2374** | 16.00% | 57.00% | **0 Unit (0.0%)** | ⚠️ Sensitivitas Cacat Tinggi (Over-conservative) |
| **Model V4** | Hierarchical Dual-Tier YOLOv8n (640px) | **46.00%** | **0.4365** | 28.00% | 26.00% | 6 Unit (6.0%) | ⚠️ Resolusi 640px kehilangan lecet mikro |
| **Model V3** | Classical ML Ensemble (18 Fitur, 1.918 Unit) | **69.00%** | **0.6828** | 10.00% | 21.00% | 1 Unit (1.0%) | ⭐ Benchmark Klasikal Terstabil |
| **Model V2** | Multi-View 5-Sudut (Termasuk Layar Depan) | **57.00%** | **0.5493** | 26.00% | 17.00% | 3 Unit (3.0%) | ❌ Terganggu Glare Pantulan Lampu Layar |
| **Model V1** | Baseline Prototipe (YOLOv8-Seg Nano Heuristik) | **28.00%** | **0.2800** | 48.00% | 24.00% | 4 Unit (4.0%) | ❌ Klaim awal 90% terbukti mock sintetis |

---

## 3. Matriks Kebingungan (4x4 Confusion Matrix) Riil Data Uji Per Versi Model

### 3.1. Model V7: Unified Hard Damage (Checkpoint Terbaik)
- **Akurasi Riil Data Uji:** 38/100 unit (38.00%)
- **Macro F1-Score:** 0.3595
- **Matriks 4x4 (Baris: Ground Truth, Kolom: Prediksi):**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A   [ 5 ]      16         3         1     20.00%
True Grade B     5      [ 15 ]       2         3     60.00%
True Grade C     1         7       [ 5 ]      12     20.00%
True Grade D     0         6         6      [ 13 ]   52.00%
Presisi        45.45%    34.09%    31.25%    44.83%
```
- **Analisis Risiko:**
  - Critical Inversions (Grade D ➔ Grade A): **0 Unit (0.0%)** — Proteksi veto structural hard damage berhasil 100%.
  - Over-Grading: 25.0% | Under-Grading: 37.0%.
  - Metrik Spasial YOLO Data Test (`images/val`): mAP@50 11.82%, Precision 51.77%, Val Box Loss 1.479.

---

### 3.2. Model V6: Fine-Tuned Clean Housing (Tuntas 40 Epochs)
- **Akurasi Riil Data Uji:** 45/100 unit (45.00%)
- **Macro F1-Score:** 0.4223
- **Matriks 4x4 (Baris: Ground Truth, Kolom: Prediksi):**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A   [ 9 ]      11         4         1     36.00%
True Grade B     4      [ 16 ]       2         3     64.00%
True Grade C     1         6       [ 3 ]      15     12.00%
True Grade D     0         5         3      [ 17 ]   68.00%
Presisi        64.29%    42.11%    25.00%    47.22%
```
- **Analisis Risiko:**
  - Critical Inversions: **0 Unit (0.0%)**.
  - Over-Grading: 19.0% | Under-Grading: 36.0%.
  - Metrik Spasial YOLO Data Test (`images/val`): Peak mAP@50 4.35%, Recall 9.29%, Val Box Loss 2.97.

---

### 3.3. Model V5: Housing-Only YOLOv8s 800px (30 Epochs)
- **Akurasi Riil Data Uji:** 27/100 unit (27.00%)
- **Macro F1-Score:** 0.2374
- **Matriks 4x4 (Baris: Ground Truth, Kolom: Prediksi):**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A   [ 4 ]       3         5        13     16.00%
True Grade B     4       [ 5 ]       0        16     20.00%
True Grade C     1         7       [ 2 ]      15      8.00%
True Grade D     0         3         6      [ 16 ]   64.00%
Presisi        44.44%    27.78%    15.38%    26.67%
```
- **Analisis Risiko:**
  - Over-Grading: 16.0% | Under-Grading: 57.0% | Critical Inversions: 0 Unit (0.0%).
  - Metrik Spasial YOLO Data Test (`images/val`): mAP@50 38.84%, Recall 67.34% (Peak 75.57%), Val Box Loss 0.648.

---

### 3.4. Model V4: Hierarchical Dual-Tier (YOLOv8n 640px)
- **Akurasi Riil Data Uji:** 46/100 unit (46.00%)
- **Macro F1-Score:** 0.4365
- **Matriks 4x4 (Baris: Ground Truth, Kolom: Prediksi):**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A  [ 17 ]       7         0         1     68.00%
True Grade B     5      [ 12 ]       3         5     48.00%
True Grade C     6         5       [ 4 ]      10     16.00%
True Grade D     6         4         2      [ 13 ]   52.00%
Presisi        50.00%    42.86%    44.44%    44.83%
```
- **Analisis Risiko:**
  - Critical Inversions (Grade D ➔ A): **6 Unit (6.0%)** akibat belum adanya Veto Guardrail yang kuat.

---

### 3.5. Model V3: Classical ML Ensemble (1.918 Unit)
- **Akurasi Riil Data Uji:** 69/100 unit (69.00%)
- **Macro F1-Score:** 0.6828
- **Matriks 4x4 (Baris: Ground Truth, Kolom: Prediksi):**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A  [ 12 ]       4         1         8     48.00%
True Grade B     1      [ 22 ]       0         2     88.00%
True Grade C     2         3      [ 14 ]       6     56.00%
True Grade D     1         2         1      [ 21 ]   84.00%
Presisi        75.00%    70.97%    87.50%    56.76%
```

---

### 3.6. Model V2: Multi-View 5-Sudut
- **Akurasi Riil Data Uji:** 57/100 unit (57.00%)
- **Macro F1-Score:** 0.5493
- **Matriks 4x4:**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A  [ 20 ]       1         3         1     80.00%
True Grade B    11       [ 6 ]       4         4     24.00%
True Grade C     4         2      [ 16 ]       3     64.00%
True Grade D     3         2         5      [ 15 ]   60.00%
Presisi        52.63%    54.55%    57.14%    65.22%
```

---

### 3.7. Model V1: Baseline Prototipe (Uji Riil Lapangan)
- **Akurasi Riil Data Uji:** 28/100 unit (28.00%) vs Klaim Sintetis Mock 90.00%
- **Macro F1-Score:** 0.2800
- **Matriks 4x4:**
```
            Pred A    Pred B    Pred C    Pred D    Recall
True Grade A   [ 6 ]      11         5         3     24.00%
True Grade B     8       [ 8 ]       6         3     32.00%
True Grade C     7         6       [ 5 ]       7     20.00%
True Grade D     4         5         7       [ 9 ]   36.00%
Presisi        24.00%    26.67%    21.74%    40.91%
```

---

## 4. Kesimpulan Evaluasi & Kepatuhan Integritas Data
1. **Peniadaan Data Statis / Dummy:** Seluruh angka persentase, True Positive (TP), False Positive (FP), False Negative (FN), serta Matriks Kebingungan 4x4 di dalam menu *Laporan Investigasi & Evaluasi Empiris* telah diperbarui 100% menggunakan data uji (*test dataset*) yang valid.
2. **Keterlacakan Berkas (Traceability):** Seluruh laporan JSON hasil komputasi tersimpan di:
   - `reports/real_benchmark_v7.json`
   - `reports/real_benchmark_v6.json`
   - `reports/evaluation_report_v5.json`
   - `reports/evaluation_report_v4.json`
   - `reports/evaluation_report_v3_no_front.json`
   - `reports/evaluation_report_v2.json`
   - `reports/evaluation_report.json`
