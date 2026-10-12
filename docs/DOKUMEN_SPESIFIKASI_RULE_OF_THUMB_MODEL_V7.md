# Spesifikasi & Audit Resmi: Rule of Thumb Klasifikasi Grade Kosmetik Khusus Model Versi 7 (V7)

Dokumen ini mendokumentasikan hasil audit teknis, metodologi standar industri, dan rumusan **Rule of Thumb resmi penentuan Grade A, B, C, dan D yang diterapkan khusus untuk Model Versi 7 (`v7`)**. Model-model versi sebelumnya (V1 s.d. V6) tetap mempertahankan rule of thumb dan pipeline evaluasi sebelumnya tanpa perubahan (*backward compatibility 100%*).

---

## 1. Ringkasan Eksekutif & Latar Belakang Pembaruan

Pada arsitektur model sebelumnya (V1 s.d. V6), sistem inspeksi menghadapi tantangan ambiguitas taksonomi:
1. **Pemisahan Kelas `broken` vs `crack` yang Tumpang Tindih:** Keduanya sama-sama merupakan kerusakan kaca/bodi berisiko tinggi, namun memiliki penalti dan batas veto yang berbeda sehingga membingungkan model.
2. **Perlakuan Kelas `dent` (Penyok):** Pada `model_tambahan`, penyok dimasukkan ke dalam `hard_damage`, menyebabkan ponsel dengan penyok wajar (seharusnya Grade C) langsung ter-veto ke Grade D (*under-grading parah*). Sebaliknya, pada V3/V5, penyok dievaluasi melalui model Random Forest yang rentan *noise* statistik.
3. **Ketidaksiapan Engine Lama Terhadap Label `hard_damage`:** Mesin evaluasi lama (`grading_engine.py`) hanya mengenal kamus 5 kelas (`scratch`, `dent`, `chip`, `crack`, `broken`). Jika model mengeluarkan prediksi `hard_damage`, label tersebut jatuh ke penalti default (1.0) dan gagal memicu veto Grade D.

Oleh karena itu, **Model Versi 7 menetapkan *Rule of Thumb* mandiri berstandar internasional** yang memadukan **Tier 1: *Hard-Fail Fast Veto*** dan **Tier 2: *Continuous Defect Penalty Index (DPI)*** berbasis milimeter fisik sub-piksel.

---

## 2. Tabel Komparasi: Rule of Thumb Sebelumnya (V1–V6) vs. Rule of Thumb Terbaru (Khusus V7)

| Dimensi Evaluasi | Rule of Thumb Sebelumnya (Model V1 s.d. V6) | Rule of Thumb Terbaru (Khusus Model Versi 7) | Dampak & Keunggulan bagi Bisnis / Operasional |
|:---|:---|:---|:---|
| **Cakupan Taksonomi Kelas** | **5 Kelas Fragmented:**<br>`scratch`, `dent`, `chip`, `crack`, `broken` | **4 Kelas Unified:**<br>`scratch`, `chip`, `dent`, `hard_damage` | Menghilangkan kerancuan antara pecah bodi vs retakan fatal. |
| **Perlakuan Kelas `dent` (Penyok)** | Digabung dalam 18 fitur Random Forest (V3/V5) atau disatukan ke `hard_damage` (`model_tambahan`). | **Diisolasi Mandiri (Kelas 2):**<br>Menjadi pendorong utama penentuan **Grade C** secara proporsional. | **Ponsel penyok wajar tetap dinilai adil sebagai Grade C** (tidak lagi salah divonis Grade D). Nasabah tidak dirugikan. |
| **Perlakuan Kerusakan Berat** | Terbagi dua: `broken` (veto) vs `crack` (toleransi $\le 8\text{ mm}$ jika 1 titik). | **Unifikasi Mutlak (Kelas 3: `hard_damage`):**<br>$\ge 1$ titik $\rightarrow$ **Veto Langsung Grade D**. | **Zero Tolerance:** 100% memitigasi risiko menerima barang pecah/bocor air ke Grade A/B/C. |
| **Metode Penilaian Akhir** | Mengandalkan Machine Learning Random Forest Classifier + Heuristik Awal. | **Dual-Tier Deterministic Hybrid Engine:**<br>Tier 1 Veto $\rightarrow$ Tier 2 Akumulasi DPI Berbobot Zona. | Bebas dari *Averaging Trap* (AI tidak bisa meloloskan HP retak hanya karena 3 sisi lainnya mulus). |
| **Kriteria Grade A (Mulus)** | Berdasarkan prediksi ML probabilistik (toleransi DPI $< 3.0$ atau 0 cacat). | **Ketat & Terukur:**<br>$\text{DPI} < 3.0$, `hard_damage` = 0, `dent` = 0, `chip` $\le 1$ ($\le 1.0\text{ mm}$), `scratch` $\le 3.0\text{ mm}$. | Menjamin unit Grade A berstandar *Like New / Mint* sesuai ekspektasi pasar buyback. |
| **Kriteria Grade B (Wajar)** | DPI $< 18.0$, toleransi hingga 2 dent dan 2 chip menurut ML. | **Presisi:**<br>$3.0 \le \text{DPI} < 15.0$, `hard_damage` = 0, maks. 1 dent mikro ($\le 2.0\text{ mm}$), maks. 3 chip wajar ($\le 2.5\text{ mm}$). | Menjaga grade pemakaian normal tanpa mendevaluasi unit secara berlebihan. |
| **Kriteria Grade C (Aus Berat)** | Sisa klasifikasi ML sebelum veto DPI $> 45.0$. | **Terstandarisasi:**<br>$15.0 \le \text{DPI} < 40.0$, `hard_damage` = 0, toleransi 1 s.d. 4 dent ($\le 5.0\text{ mm}$), chip bopeng luas. | Menampung ponsel dengan aus bodi berat / penyok fisik tanpa kebocoran hardware. |
| **Kriteria Grade D (Rusak/Veto)** | `broken` $> 0$ atau `crack` $\ge 2$ atau `chip` $\ge 4$ atau $\text{DPI} \ge 45.0$. | **Veto Komprehensif V7:**<br>1. `hard_damage` $\ge 1$<br>2. `chip` $\ge 4.5\text{ mm}$<br>3. `dent` $\ge 5.0\text{ mm}$ (bengkok)<br>4. $\text{DPI} \ge 40.0$. | Standar proteksi risiko gadai tertinggi: otomatis mendiskualifikasi kerusakan fatal. |

---

## 3. Rumusan Matematis Rule of Thumb Model Versi 7

### A. Bobot Tingkat Keparahan Cacat ($W_{\text{class}}$)
Model V7 menetapkan bobot penalti eksponensial berdasarkan risiko struktural material:
* $W_{\text{scratch}} = 1.0$ (Abrasi permukaan ringan / hairline)
* $W_{\text{dent}} = 3.0$ (Deformasi kontur bodi tanpa rekahan)
* $W_{\text{chip}} = 3.5$ (Lapisan cat terangkat / logam dasar terekspos)
* $W_{\text{hard\_damage}} = 25.0$ + **Immediate Fast-Fail Veto**

### B. Bobot Zona Penampang ($W_{\text{zone}}$)
Penampang smartphone memiliki sensitivitas valuasi yang berbeda:
* $W_{\text{back}} = 2.0$ (Penampang bodi belakang terluas dan paling tampak)
* $W_{\text{bottom}} = 1.2$ (Area konektor charger, speaker, dan mikrofon)
* $W_{\text{left}} = W_{\text{right}} = W_{\text{top}} = 1.0$ (Bingkai samping dan atas)

### C. Formula Penghitungan Defect Penalty Index (DPI)
$$\text{DPI}_{\text{total}} = \sum_{i=1}^{N} \left( W_{\text{class}(i)} \times W_{\text{zone}(i)} \times \max\left(1.0, \frac{\text{Length}_{mm}(i)}{3.0}\right) \right)$$

---

## 4. Matriks Ambang Batas Sub-Milimeter Khusus Model Versi 7

```
+-----------------------------------------------------------------------------------------------------------------+
|                                 HIERARKI KELAYAKAN GRADE MODEL VERSI 7 (V7)                                     |
+-----------------------------------------------------------------------------------------------------------------+
| TIER 1: FAST-FAIL VETO CHECK                                                                                    |
|   • hard_damage >= 1 titik                      ----------------------------> VONIS GRADE D (Veto Mutlak)       |
|   • chip >= 4.5 mm (sompal terbuka)             ----------------------------> VONIS GRADE D (Veto Mutlak)       |
|   • dent >= 5.0 mm (bent frame / bengkok)       ----------------------------> VONIS GRADE D (Veto Mutlak)       |
|   • DPI >= 40.0 (kerusakan kumulatif masif)     ----------------------------> VONIS GRADE D (Veto Mutlak)       |
+-----------------------------------------------------------------------------------------------------------------+
| TIER 2: CONTINUOUS PHYSICAL BOUNDARY (Jika Lolos Tier 1)                                                        |
|   • GRADE A (Like New / Mint):                                                                                  |
|       - DPI < 3.0                                                                                               |
|       - hard_damage = 0, dent = 0                                                                               |
|       - chip <= 1 (panjang <= 1.0 mm, luas <= 1.0 mm²)                                                          |
|       - scratch <= 3.0 mm (hairline)                                                                            |
|                                                                                                                 |
|   • GRADE B (Normal Wear / Wajar):                                                                              |
|       - 3.0 <= DPI < 15.0                                                                                       |
|       - hard_damage = 0                                                                                         |
|       - dent <= 1 mikro (panjang <= 2.0 mm, kedalaman < 0.5 mm)                                                 |
|       - chip <= 3 (panjang <= 2.5 mm per titik)                                                                 |
|       - scratch <= 8.0 mm (baret wajar pemakaian)                                                               |
|                                                                                                                 |
|   • GRADE C (Heavy Cosmetic Wear / Aus Berat):                                                                  |
|       - 15.0 <= DPI < 40.0                                                                                      |
|       - hard_damage = 0                                                                                         |
|       - dent <= 4 titik (panjang <= 5.0 mm per titik, casing tidak patah)                                       |
|       - chip bopeng / cat mengelupas luas                                                                       |
|                                                                                                                 |
|   • GRADE D (Faulty / Reject):                                                                                  |
|       - Tidak memenuhi syarat batas toleransi Grade C atau DPI >= 40.0                                          |
+-----------------------------------------------------------------------------------------------------------------+
```

---

## 5. Bukti Isolasi pada Implementasi Perangkat Lunak

Pembaruan rule of thumb ini diisolasi secara ketat di dalam kode program:
* Pada [grading_engine.py](file:///Users/macbookair/Documents/Project%20Defect%20Detections/TES_CROP_HP/grading_engine.py):
  Fungsi `evaluate_phone_unit` memeriksa parameter `version`. Jika `version == "v7"`, sistem secara spesifik mengeksekusi `evaluate_phone_unit_v7`. Jika `version != "v7"` (misal V3, V4, V5, V6, model tambahan), sistem mengeksekusi pipeline lama tanpa mengubah variabel maupun logika lama.
* Pada [core_engine.py](file:///Users/macbookair/Documents/Project%20Defect%20Detections/TES_CROP_HP/core_engine.py):
  Memasukkan parameter `version=self.version` sehingga pemilihan model di antarmuka Streamlit secara otomatis menentukan *rule of thumb* yang relevan.
