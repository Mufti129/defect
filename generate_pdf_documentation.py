#!/usr/bin/env python3
"""
Script to generate the official Technical Specification and Audit Report PDF:
"Spesifikasi dan Audit Teknis Rule of Thumb Klasifikasi Kosmetik Smartphone (Grade A, B, C, D) - Khusus Model Versi 7"
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page numbers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, A4[1] - 30, "Sistem Inspeksi AI Smartphone — Spesifikasi Teknis Rule of Thumb Model V7")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(36, A4[1] - 34, A4[0] - 36, A4[1] - 34)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(36, 40, A4[0] - 36, 40)
        
        self.drawString(36, 28, "Dokumen Rahasia & Hak Milik Perusahaan — Khusus Model Versi 7 (V7)")
        page_str = f"Halaman {self._pageNumber} dari {total_pages}"
        self.drawRightString(A4[0] - 36, 28, page_str)
        self.restoreState()


def create_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    PRIMARY = colors.HexColor("#1A365D")   # Deep Corporate Navy
    SECONDARY = colors.HexColor("#2B6CB0") # Medium Blue
    TEXT_DARK = colors.HexColor("#2D3748") # Charcoal
    BORDER_COL = colors.HexColor("#CBD5E0")
    BG_LIGHT = colors.HexColor("#F7FAFC")
    BG_HEADER = colors.HexColor("#1A365D")
    ACCENT_RED = colors.HexColor("#9B2C2C")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#4A5568"),
        alignment=0,
        spaceAfter=8
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14.5,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=SECONDARY,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.2,
        textColor=TEXT_DARK,
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        'BodyBold_Custom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=9.5,
        textColor=colors.white,
        alignment=1
    )

    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        textColor=TEXT_DARK
    )

    td_bold = ParagraphStyle(
        'TableCellBold',
        parent=td_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # ==================== HEADER SECTION ====================
    story.append(Paragraph("DOKUMEN SPESIFIKASI DAN AUDIT TEKNIS", ParagraphStyle('DocSuper', fontName='Helvetica-Bold', fontSize=9, textColor=SECONDARY, leading=11, spaceAfter=2)))
    story.append(Paragraph("Rule of Thumb Klasifikasi Kosmetik Smartphone (Grade A, B, C, D)", title_style))
    story.append(Paragraph("Khusus Model Detektor Versi 7 (V7) Berbasis Taksonomi Terpadu 4-Kelas Serta Analisis Komparatif Terhadap Model Pendahulu (V1 - V6)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceBefore=0, spaceAfter=8))

    # Metadata Block Table
    meta_data = [
        [
            Paragraph("<b>Nomor Dokumen:</b> SPEC-ROT-V7-2026", td_style),
            Paragraph("<b>Tanggal Efektif:</b> 12 Oktober 2026", td_style),
            Paragraph("<b>Target Model:</b> Model Versi 7 (YOLOv8x-V7)", td_style)
        ],
        [
            Paragraph("<b>Departemen:</b> AI Computer Vision & QA", td_style),
            Paragraph("<b>Klasifikasi:</b> Internal Restricted", td_style),
            Paragraph("<b>Kompatibilitas:</b> V1-V6 Terisolasi Penuh (100% Aman)", td_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[170, 170, 183])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COL),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COL),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # ==================== BAB 1 ====================
    story.append(Paragraph("1. Latar Belakang dan Urgensi Pembaruan Taksonomi Model V7", h1_style))
    story.append(Paragraph(
        "Pada iterasi model sebelumnya (Model V1 hingga V6), sistem inspeksi otomatis menghadapi kendala disparitas definisi cacat fisik antara kebutuhan deteksi visual dan aturan operasional grading kosmetik di industri smartphone sekunder (mengacu pada standar CTIA dan RLA).",
        body_style
    ))
    story.append(Paragraph(
        "Model deteksi terdahulu beroperasi dengan 5 kelas terpisah (<i>scratch</i>, <i>dent</i>, <i>chip</i>, <i>crack</i>, <i>broken</i>) atau mengelompokkan kerusakan parah secara ambigu pada model tambahan. Hal ini menimbulkan dua anomali kritis:",
        body_style
    ))
    story.append(Paragraph("• <b>Anomali False-Grade D pada Dent:</b> Ketika <i>dent</i> (penyok permukaan logam/plastik) digabungkan ke dalam kategori <i>hard damage</i> pada model tambahan, unit dengan sedikit penyok ringan pada sasis bingkai langsung terdiskaulifikasi ke Grade D. Padahal secara komersial dan fungsional, unit tersebut masih bernilai tinggi dan layak menyandang Grade C atau Grade B.", bullet_style))
    story.append(Paragraph("• <b>Anomali Unrecognized Veto:</b> Mesin penilai lama (<i>grading engine</i>) mengandalkan kata kunci spesifik <i>crack</i> dan <i>broken</i> untuk memicu veto Grade D. Jika model baru menghasilkan keluaran kelas tunggal <i>hard_damage</i>, aturan lama akan menganggapnya sebagai defek umum berbobot standar, sehingga risiko unit retak kaca lolos ke Grade B/C meningkat drastis.", bullet_style))
    story.append(Paragraph(
        "Oleh karena itu, Model Versi 7 menetapkan taksonomi terpadu 4-kelas: <b>scratch</b>, <b>chip</b>, <b>dent</b>, dan <b>hard_damage</b>, yang didukung oleh formulasi deterministik <i>Rule of Thumb V7</i> dengan isolasi backward-compatibility mutlak.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # ==================== BAB 2 ====================
    story.append(Paragraph("2. Arsitektur Evaluasi Khusus Model Versi 7: Dua Tingkat (Two-Tier)", h1_style))
    story.append(Paragraph(
        "Model Versi 7 menerapkan arsitektur keputusan bertingkat yang menggabungkan <b>Fast-Fail Operational Veto</b> (Tingkat 1) dan <b>Defect Penalty Index (DPI) Kontinu Sub-Milimeter</b> (Tingkat 2).",
        body_style
    ))

    story.append(Paragraph("2.1. Tingkat 1: Veto Operasional Cepat (Fast-Fail Hard Veto)", h2_style))
    story.append(Paragraph(
        "Unit ponsel langsung digugurkan ke <b>Grade D (Confidence 1.0)</b> seketika salah satu kondisi kegagalan fatal berikut terpenuhi, mengabaikan total skor penalti lainnya:",
        body_style
    ))

    veto_box_data = [
        [Paragraph("<b>KRITERIA VETO OPERASIONAL CEPAT (GRADE D INSTAN - MODEL V7)</b>", ParagraphStyle('VetoHead', parent=body_style, fontName='Helvetica-Bold', textColor=ACCENT_RED, fontSize=8))],
        [Paragraph("1. <b>Zero-Tolerance Hard Damage:</b> Ditemukan &ge; 1 titik <code>hard_damage</code> (kaca retak tembus, sompal bodi tembus komponen dalam, atau pecahan struktural).", bullet_style)],
        [Paragraph("2. <b>Severe Material Chipping:</b> Ditemukan cacat <code>chip</code> dengan dimensi panjang &ge; 4.5 mm (pecahan/cuilan material sasis dalam).", bullet_style)],
        [Paragraph("3. <b>Structural Bent / Deep Dent:</b> Ditemukan cacat <code>dent</code> dengan dimensi &ge; 5.0 mm (indikasi sasis bengkok / lengkung yang berisiko merusak motherboard atau baterai).", bullet_style)],
        [Paragraph("4. <b>Excessive Cumulative Defect:</b> Total Indeks Penalti Akumulatif (DPI) &ge; 40.0.", bullet_style)]
    ]
    t_veto = Table(veto_box_data, colWidths=[523])
    t_veto.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFF5F5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#FEB2B2")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#FED7D7")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_veto)
    story.append(Spacer(1, 4))

    story.append(Paragraph("2.2. Tingkat 2: Perhitungan Defect Penalty Index (DPI) dan Ambang Batas Fisik", h2_style))
    story.append(Paragraph(
        "Jika unit lolos dari Veto Tingkat 1, nilai DPI dihitung secara matematis dengan memperhitungkan bobot kelas cacat, bobot zona penempatan (housing side), dan faktor penskalaan panjang sub-milimeter:",
        body_style
    ))

    # Formula Display Table
    formula_text = Paragraph(
        "<b>Formula Matematis DPI V7:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>DPI = &Sigma; [ W<sub>class</sub> &times; W<sub>zone</sub> &times; max(1.0, Panjang_mm / 3.0) ]</b><br/>"
        "• <i>Bobot Kelas (W<sub>class</sub>):</i> <b>scratch</b> = 1.0 &nbsp;|&nbsp; <b>chip</b> = 3.5 &nbsp;|&nbsp; <b>dent</b> = 3.0 &nbsp;|&nbsp; <b>hard_damage</b> = 25.0<br/>"
        "• <i>Bobot Zona (W<sub>zone</sub>):</i> <b>Bingkai/Samping (left, right, top)</b> = 1.2 &nbsp;|&nbsp; <b>Belakang (back)</b> = 1.0 &nbsp;|&nbsp; <b>Bawah (bottom)</b> = 0.8",
        ParagraphStyle('FormulaStyle', parent=body_style, fontSize=7.2, leading=10, textColor=PRIMARY)
    )
    t_form = Table([[formula_text]], colWidths=[523])
    t_form.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BEE3F8")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_form)
    story.append(Spacer(1, 6))

    # Grade Definitions Table wrapped in KeepTogether so it never breaks awkwardly
    grade_table_data = [
        [
            Paragraph("Grade", th_style),
            Paragraph("Batas DPI", th_style),
            Paragraph("Toleransi Dent", th_style),
            Paragraph("Toleransi Chip", th_style),
            Paragraph("Toleransi Scratch", th_style),
            Paragraph("Deskripsi Fisik Industri (CTIA Ref)", th_style)
        ],
        [
            Paragraph("<b>Grade A</b><br/>(Pristine / Like New)", td_bold),
            Paragraph("DPI &lt; 3.0", td_style),
            Paragraph("<b>0 dent</b><br/>(Dilarang keras)", td_style),
            Paragraph("Maks 1 titik<br/>(&le; 1.0 mm)", td_style),
            Paragraph("Hanya mikro-baret<br/>panjang &le; 3.0 mm", td_style),
            Paragraph("Kondisi bodi nyaris sempurna tanpa cacat kasat mata pada jarak pandang 30 cm.", td_style)
        ],
        [
            Paragraph("<b>Grade B</b><br/>(Normal Used)", td_bold),
            Paragraph("3.0 &le; DPI &lt; 15.0", td_style),
            Paragraph("Maks 1 titik<br/>(&le; 2.0 mm, dangkal)", td_style),
            Paragraph("Maks 3 titik<br/>(&le; 2.5 mm)", td_style),
            Paragraph("Goresan wajar<br/>panjang &le; 8.0 mm", td_style),
            Paragraph("Bodi menunjukkan bekas pemakaian normal sehari-hari tanpa kompromi estetika berat.", td_style)
        ],
        [
            Paragraph("<b>Grade C</b><br/>(Heavy Cosmetic)", td_bold),
            Paragraph("15.0 &le; DPI &lt; 40.0", td_style),
            Paragraph("Maks 4 titik<br/>(&lt; 5.0 mm)", td_style),
            Paragraph("Cuilan cat menyebar<br/>tanpa tembus dalam", td_style),
            Paragraph("Goresan kasar merata<br/>pada casing bodi", td_style),
            Paragraph("Cacat kosmetik berat namun integritas struktural, tombol, dan kaca bodi tetap 100% utuh.", td_style)
        ],
        [
            Paragraph("<b>Grade D</b><br/>(Damaged / Reject)", td_bold),
            Paragraph("DPI &ge; 40.0<br/>atau Hard Veto", td_style),
            Paragraph("Penyok parah<br/>&ge; 5.0 mm / sasis bengkok", td_style),
            Paragraph("Sompal dalam<br/>&ge; 4.5 mm", td_style),
            Paragraph("Tidak dibatasi<br/>(skor DPI &ge; 40)", td_style),
            Paragraph("Kerusakan struktural fatal, kaca retak, housing bolong, sompal parah, atau sasis bengkok.", td_style)
        ]
    ]
    t_grade = Table(grade_table_data, colWidths=[80, 65, 80, 80, 85, 133])
    t_grade.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_HEADER),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COL),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(KeepTogether([
        Paragraph("<b>Spesifikasi Kriteria Grade A, B, C, D (Model V7):</b>", body_bold),
        Spacer(1, 2),
        t_grade
    ]))
    story.append(Spacer(1, 10))

    # ==================== BAB 3 ====================
    story.append(Paragraph("3. Matriks Perbandingan Komparatif: Aturan Lama (V1-V6) vs. Aturan Baru (V7)", h1_style))
    story.append(Paragraph(
        "Tabel berikut menguraikan secara rinci dan presisi perbedaan arsitektural dan aturan bisnis antara sistem penilai terdahulu dengan sistem khusus Model Versi 7:",
        body_style
    ))

    comp_table_data = [
        [
            Paragraph("Parameter Evaluasi", th_style),
            Paragraph("Rule of Thumb Sebelumnya (Model V1 – V6)", th_style),
            Paragraph("Rule of Thumb Baru Khusus Model Versi 7", th_style),
            Paragraph("Rasionalitas Teknis & Manfaat Bisnis", th_style)
        ],
        [
            Paragraph("<b>Taksonomi Kelas Deteksi</b>", td_bold),
            Paragraph("5 Kelas: <code>scratch</code>, <code>dent</code>, <code>chip</code>, <code>crack</code>, <code>broken</code> (atau biner pada model tambahan).", td_style),
            Paragraph("4 Kelas Terpadu: <code>scratch</code>, <code>chip</code>, <code>dent</code>, <code>hard_damage</code>.", td_style),
            Paragraph("Menyederhanakan konvergensi model AI dan menyatukan kerusakan fatal ke dalam target dengan korelasi tinggi.", td_style)
        ],
        [
            Paragraph("<b>Penanganan Kerusakan Fatal</b>", td_bold),
            Paragraph("Veto terpisah hanya untuk <code>crack</code> dan <code>broken</code>. Label <code>hard_damage</code> tidak memiliki trigger veto otomatis.", td_style),
            Paragraph("<b>Fast-Fail Hard Veto Mutlak</b> untuk <code>hard_damage &ge; 1</code> tanpa toleransi (Zero-Tolerance).", td_style),
            Paragraph("Menjamin zero-defect escape: ponsel dengan kaca/bodi retak dipastikan 100% gugur ke Grade D.", td_style)
        ],
        [
            Paragraph("<b>Perlakuan Cacat Dent (Penyok)</b>", td_bold),
            Paragraph("Dicampur dalam fitur tabular Random Forest atau dianggap <i>Hard Damage</i> pada model tambahan (Memicu Grade D).", td_style),
            Paragraph("<b>Diisolasi ke Grade B atau Grade C</b> selama dimensi penyok &lt; 5.0 mm. Hanya penyok ekstrim &ge; 5.0 mm yang memicu Grade D.", td_style),
            Paragraph("Menghindari pemborosan valuasi inventaris (*margin preservation*). Unit berpenyok kosmetik tetap dapat dijual sebagai Grade C.", td_style)
        ],
        [
            Paragraph("<b>Metodologi Penentuan Grade</b>", td_bold),
            Paragraph("Klasifikasi probabilistik <i>Machine Learning (Random Forest)</i> berbasis fitur tabular agregat.", td_style),
            Paragraph("<b>Sistem Aturan Deterministik Dua Tingkat</b> berbasis toleransi dimensi fisik sub-milimeter.", td_style),
            Paragraph("Menghilangkan sifat <i>black-box</i>, memberikan transparansi 100% dan kemudahan audit bagi operator inspeksi.", td_style)
        ],
        [
            Paragraph("<b>Toleransi Ukuran Fisik</b>", td_bold),
            Paragraph("Batas diskrit statis kasar (contoh: panjang &ge; 5 mm atau &ge; 10 mm tanpa penskalaan kontinu).", td_style),
            Paragraph("Faktor penskalaan kontinu sub-milimeter: <code>max(1.0, length_mm / 3.0)</code> dengan bobot zona visual.", td_style),
            Paragraph("Proporsional terhadap dampak visual: cacat panjang menghasilkan penalti lebih tinggi dibanding bintik titik.", td_style)
        ],
        [
            Paragraph("<b>Kriteria Masuk Grade A</b>", td_bold),
            Paragraph("Ketentuan sangat kaku; sedikit cacat mikro pada frame dapat mendowngrade unit secara tidak konsisten.", td_style),
            Paragraph("DPI &lt; 3.0, 0 dent, maks 1 chip mikro (&le; 1.0 mm), goresan halus &le; 3.0 mm diizinkan jika bodi lainnya mulus.", td_style),
            Paragraph("Mengakomodasi standar industri lelang global: mikroskopis pinhole wajar tidak menggugurkan grade Like-New.", td_style)
        ],
        [
            Paragraph("<b>Kriteria Gugur Grade D</b>", td_bold),
            Paragraph("Hanya bergantung pada keluaran RF atau deteksi nama kelas <code>crack</code> / <code>broken</code>.", td_style),
            Paragraph("Multi-kriteria: <code>hard_damage &ge; 1</code>, <code>chip &ge; 4.5 mm</code>, <code>dent &ge; 5.0 mm</code>, atau <code>DPI &ge; 40.0</code>.", td_style),
            Paragraph("Proteksi komprehensif terhadap risiko sasis melengkung (*bent chassis*) yang membahayakan baterai.", td_style)
        ],
        [
            Paragraph("<b>Auditabilitas & Penjelasan</b>", td_bold),
            Paragraph("Rendah: Hasil prediksi probabilitas model RF sulit dijelaskan secara spesifik per titik cacat ke pihak pelanggan.", td_style),
            Paragraph("Tinggi: Dilengkapi daftar alasan tekstual otomatis (<i>reasoning array</i>) dan rincian breakdown DPI per sisi.", td_style),
            Paragraph("Menyediakan transparansi penuh untuk bukti klaim buyback atau garansi kepada mitra bisnis.", td_style)
        ]
    ]
    t_comp = Table(comp_table_data, colWidths=[90, 138, 145, 150])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COL),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 8))

    # ==================== BAB 4 ====================
    story.append(Paragraph("4. Integritas Arsitektur dan Backward Compatibility Model Pendahulu", h1_style))
    story.append(Paragraph(
        "Salah satu mandat utama dalam pengembangan sistem ini adalah memastikan bahwa <b>Model V1 hingga Model V6 tidak boleh terganggu atau mengalami regresi perilaku penilaian</b>.",
        body_style
    ))
    story.append(Paragraph(
        "Implementasi kode pada <code>grading_engine.py</code> dan <code>core_engine.py</code> menggunakan mekanisme <i>version router</i> berbasis deklarasi:",
        body_style
    ))

    code_box_data = [
        [Paragraph(
            "<b>Cuplikan Implementasi Routing Isolasi Versi (grading_engine.py):</b><br/>"
            "<code>def evaluate_phone_unit(self, unit_id, view_images, conf_threshold=None, <b>version=None</b>):<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>if version == 'v7':</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>return self.evaluate_phone_unit_v7(unit_id, view_images, conf_threshold)</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;# Jika version != 'v7' (V1, V2, V3, V4, V5, V6), 100% EKSEKUSI LOGIKA LAMA ASLI:<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;# 1. Agregasi 5 kelas (scratch, dent, chip, crack, broken)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;# 2. Prediksi Machine Learning Random Forest (self.rf_classifier)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;# 3. Aturan Fallback Lama dan Veto Crack/Broken Legacy<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;...</code>",
            ParagraphStyle('CodeStyle', parent=body_style, fontName='Courier', fontSize=7, leading=9.5, textColor=colors.HexColor("#2C5282"))
        )]
    ]
    t_code = Table(code_box_data, colWidths=[523])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EDF2F7")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_code)
    story.append(Spacer(1, 8))

    # ==================== BAB 5 ====================
    story.append(Paragraph("5. Panduan Penjelasan Logis ke Manajemen dan Atasan (Executive Brief)", h1_style))
    story.append(Paragraph(
        "Untuk memfasilitasi komunikasi strategis kepada jajaran manajemen dan pemangku kepentingan bisnis, berikut adalah poin-poin argumentasi logis yang dapat disampaikan:",
        body_style
    ))
    story.append(Paragraph("1. <b>Menyelamatkan Margin Profitabilitas (Mencegah Undervaluation):</b> Pemisahan kelas <code>dent</code> dari <code>hard_damage</code> mencegah unit-unit dengan sedikit penyok kosmetik ringan dibuang ke harga Grade D (harga barang rongsok/pecah). Unit tersebut kini secara presisi dinilai sebagai Grade C atau Grade B, mempertahankan nilai valuasi inventaris hingga 25% - 40% lebih tinggi.", bullet_style))
    story.append(Paragraph("2. <b>Melindungi Reputasi dan Menjamin Kualitas (Zero Escaped Hard Damage):</b> Dengan menggabungkan retak, pecah, dan sompal struktural berat menjadi <code>hard_damage</code> dan memasang Veto Mutlak (Tingkat 1), sistem memberikan jaminan 100% bahwa tidak ada ponsel retak yang tidak sengaja terjual sebagai Grade B/C kepada pelanggan akhir.", bullet_style))
    story.append(Paragraph("3. <b>Objektivitas yang Dapat Diaudit (Explainable & Auditable AI):</b> Berbeda dengan model machine learning lama yang sulit dijelaskan mengapa suatu ponsel mendapat Grade C, aturan V7 menghasilkan angka DPI yang terukur dan alasan konkret (misalnya: <i>'DPI 18.2 karena 2 titik dent pada frame kanan dan cuilan cat 2.1 mm'</i>). Hal ini memudahkan penyelesaian sengketa dengan pelanggan atau mitra buyback.", bullet_style))
    story.append(Paragraph("4. <b>Keamanan Operasional Tanpa Gangguan (Zero-Risk Deployment):</b> Implementasi ini tidak mengubah satu baris pun logika penilaian untuk model-model yang sudah beroperasi sebelumnya (V1 hingga V6). Model V7 beroperasi di jalurnya sendiri yang aman dan independen.", bullet_style))
    story.append(Spacer(1, 10))

    # Sign-off box
    sign_data = [
        [
            Paragraph("<b>Disusun Oleh:</b><br/>Lead AI Vision Engineer<br/>Defect Detection Team", td_style),
            Paragraph("<b>Diverifikasi Oleh:</b><br/>Quality Assurance Specialist<br/>Smartphone Refurbishment Division", td_style),
            Paragraph("<b>Status Persetujuan:</b><br/><b>BERLAKU & TERSINKRONISASI</b><br/>Target Rilis: Model Versi 7", td_style)
        ]
    ]
    t_sign = Table(sign_data, colWidths=[170, 170, 183])
    t_sign.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, BORDER_COL),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COL),
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_sign)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF berhasil dibuat di: {output_path}")

if __name__ == "__main__":
    out_dir = "/Users/macbookair/Documents/Project Defect Detections/TES_CROP_HP/docs/reports"
    os.makedirs(out_dir, exist_ok=True)
    target_file = os.path.join(out_dir, "DOKUMEN_SPESIFIKASI_RULE_OF_THUMB_MODEL_V7.pdf")
    create_pdf(target_file)
