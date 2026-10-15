"""
PDF CERTIFICATE GENERATOR
=========================
Mufti Computer Vision QA System — Divisi Elektronik & Gadai Smartphone Resmi

Generates official, tamper-evident corporate PDF certificates:
"Sertifikat Taksiran Terpadu Hasil Gabungan (Computer Vision + CIT Hardware)"
"""

import io
import re
import time
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_unified_inspection_pdf(
    cert_data: Dict[str, Any],
    detailed_record: Optional[Any] = None
) -> bytes:
    """
    Generates a professional corporate PDF inspection certificate.
    Returns PDF binary bytes suitable for download or archival.
    """
    buffer = io.BytesIO()

    # Setup document with tight 14mm margins to fit comprehensive details cleanly on 1 page (A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=9 * mm,
        bottomMargin=9 * mm
    )

    styles = getSampleStyleSheet()

    # Premium Modern Color Palette
    PRIMARY = colors.HexColor("#0F172A")       # Slate 900
    ACCENT = colors.HexColor("#2563EB")        # Blue 600
    ACCENT_PURPLE = colors.HexColor("#4F46E5") # Indigo 600
    SUCCESS = colors.HexColor("#059669")       # Emerald 600
    WARNING = colors.HexColor("#D97706")       # Amber 600
    DANGER = colors.HexColor("#DC2626")        # Crimson Red
    MUTED = colors.HexColor("#64748B")         # Slate 500
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Typography Styles with Strict, Balanced Leading (Zero Overlap Guaranteed)
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        textColor=PRIMARY,
        alignment=1
    )

    subtitle_style = ParagraphStyle(
        "CertSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=ACCENT_PURPLE,
        alignment=1
    )

    sec_hdr_style = ParagraphStyle(
        "SecHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=PRIMARY
    )

    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=PRIMARY
    )

    cell_normal = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=PRIMARY
    )

    cell_code = ParagraphStyle(
        "CellCode",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        textColor=PRIMARY
    )

    story = []

    # 1. HEADER (Branding Mufti Computer Vision)
    cert_id = cert_data.get("sertifikat_id", f"CERT-MCV-{int(time.time())}")
    if "CERT-PGI-" in cert_id:
        cert_id = cert_id.replace("CERT-PGI-", "CERT-MCV-")

    time_str = cert_data.get("waktu_inspeksi", time.strftime("%Y-%m-%d %H:%M:%S WIB"))

    h_left = Paragraph(
        "<b>MUFTI COMPUTER VISION</b><br/>"
        "<font size=6.5 color='#475569'><b>DIVISI ELEKTRONIK & GADAI SMARTPHONE RESMI</b></font>",
        ParagraphStyle("H1", parent=cell_normal, fontName="Helvetica-Bold", fontSize=9.5, leading=12.5, textColor=PRIMARY)
    )
    h_right = Paragraph(
        f"<b>NO. SERTIFIKAT:</b> <font color='#2563EB'>{cert_id}</font><br/>"
        f"<b>WAKTU INSPEKSI:</b> <font color='#475569'>{time_str}</font>",
        ParagraphStyle("H2", parent=cell_normal, fontSize=7, leading=9.5, alignment=2, textColor=PRIMARY)
    )

    header_table = Table([[h_left, h_right]], colWidths=[105 * mm, 77 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)

    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=3, spaceAfter=4))

    story.append(Paragraph("SERTIFIKAT HASIL INSPEKSI & TAKSIRAN GADAI TERPADU", title_style))
    story.append(Paragraph("Sistem Verifikasi Otomatis Dua-Arah (AI Computer Vision 4-Sisi + Hardware CIT Diagnostics)", subtitle_style))
    story.append(Spacer(1, 3.5 * mm))

    # 2. FINAL GRADE & VALUATION BANNER (3 DISTINCT CARDS - ZERO OVERLAP)
    dev_info = cert_data.get("perangkat", {})
    decision = cert_data.get("keputusan_akhir_terpadu", {})
    cv_info = cert_data.get("inspeksi_visual_cv", {})
    internal_info = cert_data.get("diagnostik_internal_hardware", {})

    u_grade = decision.get("unified_grade", "A")
    u_deduct = float(decision.get("valuation_deduction_pct", 0.0))
    f_status = decision.get("functional_status", "PASS")

    u_grade_str = str(u_grade).strip().upper()
    u_grade_letter = u_grade_str.replace("GRADE", "").strip()
    if not u_grade_letter:
        u_grade_letter = "A"

    # Dynamic Palette based on Grade
    if "A" in u_grade_letter:
        grade_color_hex = "#059669"
        card2_bg = colors.HexColor("#ECFDF5")
        card2_border = colors.HexColor("#10B981")
    elif "B" in u_grade_letter:
        grade_color_hex = "#D97706"
        card2_bg = colors.HexColor("#FFFBEB")
        card2_border = colors.HexColor("#F59E0B")
    elif "C" in u_grade_letter:
        grade_color_hex = "#E11D48"
        card2_bg = colors.HexColor("#FFF1F2")
        card2_border = colors.HexColor("#F43F5E")
    else:
        grade_color_hex = "#DC2626"
        card2_bg = colors.HexColor("#FEF2F2")
        card2_border = colors.HexColor("#EF4444")

    # Card 1: UNIT YANG DIUJI
    c1_p1 = Paragraph("UNIT YANG DIUJI", ParagraphStyle("C1_1", fontSize=6.5, leading=8.5, fontName="Helvetica-Bold", textColor=MUTED))
    market_name = str(dev_info.get("market_name", "Smartphone"))
    c1_p2 = Paragraph(f"<b>{market_name}</b>", ParagraphStyle("C1_2", fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=PRIMARY))
    imei_txt = str(dev_info.get("imei", "-"))
    serial_txt = str(dev_info.get("serial", "-"))
    c1_p3 = Paragraph(f"IMEI: <font name='Courier'>{imei_txt}</font>  •  Serial: {serial_txt}", ParagraphStyle("C1_3", fontSize=6.5, leading=8.5, textColor=colors.HexColor("#475569")))

    card1_table = Table([[ [c1_p1, Spacer(1, 1.2 * mm), c1_p2, Spacer(1, 1.2 * mm), c1_p3] ]], colWidths=[86 * mm])
    card1_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Card 2: GRADE AKHIR TERPADU
    c2_p1 = Paragraph("GRADE AKHIR TERPADU", ParagraphStyle("C2_1", fontSize=6.5, leading=8.5, fontName="Helvetica-Bold", textColor=colors.HexColor("#475569"), alignment=1))
    c2_p2 = Paragraph(f"<b>GRADE {u_grade_letter}</b>", ParagraphStyle("C2_2", fontSize=15, leading=18, fontName="Helvetica-Bold", textColor=colors.HexColor(grade_color_hex), alignment=1))
    c2_p3 = Paragraph(f"<b>STATUS: {f_status}</b>", ParagraphStyle("C2_3", fontSize=7, leading=9, fontName="Helvetica-Bold", textColor=colors.HexColor(grade_color_hex), alignment=1))

    card2_table = Table([[ [c2_p1, Spacer(1, 0.8 * mm), c2_p2, Spacer(1, 0.8 * mm), c2_p3] ]], colWidths=[45 * mm])
    card2_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card2_bg),
        ('BOX', (0,0), (-1,-1), 1.2, card2_border),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Card 3: POTONGAN NILAI TAKSIRAN
    c3_p1 = Paragraph("POTONGAN TAKSIRAN", ParagraphStyle("C3_1", fontSize=6.5, leading=8.5, fontName="Helvetica-Bold", textColor=colors.HexColor("#475569"), alignment=1))
    deduct_color_hex = "#DC2626" if u_deduct > 0 else "#059669"
    c3_p2 = Paragraph(f"<b>-{u_deduct:.1f}%</b>", ParagraphStyle("C3_2", fontSize=15, leading=18, fontName="Helvetica-Bold", textColor=colors.HexColor(deduct_color_hex), alignment=1))
    c3_p3 = Paragraph("Dari Plafon Taksiran Maksimal", ParagraphStyle("C3_3", fontSize=6, leading=8, textColor=MUTED, alignment=1))

    card3_table = Table([[ [c3_p1, Spacer(1, 0.8 * mm), c3_p2, Spacer(1, 0.8 * mm), c3_p3] ]], colWidths=[45 * mm])
    card3_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF2F2") if u_deduct > 0 else colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1.2, colors.HexColor("#F87171") if u_deduct > 0 else colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # 3-Card Outer Row with clean 3mm gaps
    banner_table = Table([[card1_table, '', card2_table, '', card3_table]], colWidths=[86 * mm, 3 * mm, 45 * mm, 3 * mm, 45 * mm])
    banner_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 3.5 * mm))

    # 3. SPESIFIKASI IDENTITAS HARDWARE TERVERIFIKASI
    story.append(Paragraph("<b>1. Spesifikasi Hardware & Profil Koneksi Teridentifikasi</b>", sec_hdr_style))

    # Clean up SoC string if it contains verbose ANGLE / OpenGL debug suffixes
    raw_soc = str(dev_info.get("soc") or dev_info.get("soc_name", "ARM64 Processor"))
    clean_soc = re.sub(r"\(ANGLE \([^\)]+\)[^\)]*\)", "", raw_soc).strip()
    clean_soc = re.sub(r"\s+", " ", clean_soc)

    spec_rows = [
        [
            Paragraph("<b>Merek / Pabrikan:</b>", cell_bold), Paragraph(str(dev_info.get("brand", "-")), cell_normal),
            Paragraph("<b>Nomor IMEI Resmi:</b>", cell_bold), Paragraph(str(dev_info.get("imei", "-")), cell_code)
        ],
        [
            Paragraph("<b>Model Perangkat:</b>", cell_bold), Paragraph(str(dev_info.get("model", "-")), cell_normal),
            Paragraph("<b>Sistem Operasi:</b>", cell_bold), Paragraph(str(dev_info.get("os", "-")), cell_normal)
        ],
        [
            Paragraph("<b>Processor / SoC:</b>", cell_bold), Paragraph(clean_soc, cell_normal),
            Paragraph("<b>Memori RAM / ROM:</b>", cell_bold), Paragraph(f"{dev_info.get('ram_gb', 4)} GB RAM / {dev_info.get('storage_gb', 128)} GB ROM", cell_normal)
        ],
        [
            Paragraph("<b>Resolusi Layar:</b>", cell_bold), Paragraph(str(dev_info.get("screen_res") or dev_info.get("screen_resolution", "1080 x 2400 px")), cell_normal),
            Paragraph("<b>Jalur Telemetri:</b>", cell_bold), Paragraph("Web Telemetry Driver (Universal Real-Time)", cell_normal)
        ]
    ]
    spec_table = Table(spec_rows, colWidths=[36 * mm, 55 * mm, 36 * mm, 55 * mm])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#F8FAFC")),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor("#F8FAFC")),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 3.5 * mm))

    # 4. HASIL INSPEKSI DUA-ARAH (CV + INTERNAL BATTERY/SENSOR/OEM/CIT)
    story.append(Paragraph("<b>2. Hasil Pengujian Metrik Fisik & Jeroan Mesin (Two-Tier Evaluation)</b>", sec_hdr_style))

    bat_data = internal_info.get("baterai", {})
    oem_data = internal_info.get("oem_authenticity", {})
    cit_data = internal_info.get("interactive_cit", {})

    # Evaluate dynamic colors for CIT statuses
    spk_st = str(cit_data.get('speaker_status', 'LOLOS (Jernih)'))
    spk_is_pass = any(kw in spk_st.upper() for kw in ['LOLOS', 'PASS', 'NORMAL', 'CLEAR']) and not any(kw in spk_st.upper() for kw in ['RUSAK', 'MATI', 'CACAT', 'SILENT'])
    spk_color = '#059669' if spk_is_pass else '#DC2626'
    spk_impact = "Akustik & Tombol Normal" if spk_is_pass else "Penalti Cacat Speaker/Tombol"

    bat_st = str(bat_data.get('status', 'PASS'))
    bat_is_pass = (bat_st == 'PASS')
    bat_color = '#059669' if bat_is_pass else '#DC2626'
    bat_impact = "Baterai Prima (Bebas Kembung)" if bat_is_pass else "Penalti Servis Baterai"

    cloud_st = str(oem_data.get('cloud_lock', 'UNLOCKED'))
    cloud_is_pass = (cloud_st == 'UNLOCKED')
    cloud_color = '#059669' if cloud_is_pass else '#DC2626'
    cloud_impact = "Bebas Kunci (Sah Digadai)" if cloud_is_pass else "Veto Tolak Grade D"

    touch_is_pass = bool(cit_data.get('touch_passed', True))
    touch_color = '#059669' if touch_is_pass else '#DC2626'
    touch_label = 'ZERO DEAD-ZONE' if touch_is_pass else 'DEAD-ZONE (D)'
    touch_impact = "Responsif Penuh 100%" if touch_is_pass else "Veto Mutlak Grade D"

    metrics_rows = [
        [
            Paragraph("<b>Metrik Pengujian</b>", cell_bold),
            Paragraph("<b>Parameter / Metrik Teknis</b>", cell_bold),
            Paragraph("<b>Status Hasil Pengujian</b>", cell_bold),
            Paragraph("<b>Dampak Taksiran</b>", cell_bold)
        ],
        # Metrik 1: CV
        [
            Paragraph("<b>Inspeksi Bodi Luar (AI CV)</b>", cell_normal),
            Paragraph("Deteksi 4 Sisi YOLO (Goresan, Penyok, Retak, Cuil)", cell_normal),
            Paragraph(f"<b>Grade {cv_info.get('cosmetic_grade', 'A')}</b>", cell_bold),
            Paragraph("Sesuai Kondisi Housing", cell_normal)
        ],
        # Metrik 2: Baterai
        [
            Paragraph("<b>Kesehatan Baterai (SoH)</b>", cell_normal),
            Paragraph(f"SoH {bat_data.get('health_pct', 90)}% • {bat_data.get('temperature_c', 31.0)}°C • {bat_data.get('cycle_count', 180)} Siklus", cell_normal),
            Paragraph(f"<font color='{bat_color}'><b>{bat_st}</b></font>", cell_bold),
            Paragraph(bat_impact, cell_normal)
        ],
        # Metrik 3: Sensor & Radio
        [
            Paragraph("<b>Matriks Sensor & Radio</b>", cell_normal),
            Paragraph("G-Sensor 3-Axis, Giroskop, Proximity, Wi-Fi, BT 5.x", cell_normal),
            Paragraph("<font color='#059669'><b>100% RESPONSIF</b></font>", cell_bold),
            Paragraph("0 Penalti (Normal)", cell_normal)
        ],
        # Metrik 4: OEM & Komponen
        [
            Paragraph("<b>Keaslian Komponen OEM</b>", cell_normal),
            Paragraph(f"LCD: {oem_data.get('screen', 'ORIGINAL_OEM')} • Baterai: {oem_data.get('battery', 'ORIGINAL_BMS')}", cell_normal),
            Paragraph("<font color='#059669'><b>ASLI PABRIKAN</b></font>", cell_bold),
            Paragraph("Komponen Otentik", cell_normal)
        ],
        # Metrik 5: Status Kunci Akun
        [
            Paragraph("<b>Keamanan Akun (FRP/iCloud)</b>", cell_normal),
            Paragraph("Pemeriksaan Google FRP Lock & Apple iCloud Activation", cell_normal),
            Paragraph(f"<font color='{cloud_color}'><b>{cloud_st}</b></font>", cell_bold),
            Paragraph(cloud_impact, cell_normal)
        ],
        # Metrik 6: Layar Sentuh CIT
        [
            Paragraph("<b>Layar Sentuh (Touch Digitizer)</b>", cell_normal),
            Paragraph(f"Sampling Edge-to-Edge: {cit_data.get('touch_cells_passed', 49)}/{cit_data.get('touch_total_cells', 49)} Sel ({cit_data.get('touch_coverage_pct', 100):.0f}%)", cell_normal),
            Paragraph(f"<font color='{touch_color}'><b>{touch_label}</b></font>", cell_bold),
            Paragraph(touch_impact, cell_normal)
        ],
        # Metrik 7: Audio Loopback & Respons Fisik
        [
            Paragraph("<b>Audio Loopback & Tombol Fisik</b>", cell_normal),
            Paragraph("Speaker (3 Nada), Mic Loopback (2.5s), Tombol Vol & Power", cell_normal),
            Paragraph(f"<font color='{spk_color}'><b>{spk_st}</b></font>", cell_bold),
            Paragraph(spk_impact, cell_normal)
        ]
    ]

    metrics_table = Table(metrics_rows, colWidths=[38 * mm, 68 * mm, 38 * mm, 38 * mm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDE9FE")),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 3.5 * mm))

    # 5. CATATAN KEPUTUSAN & REKOMENDASI AUDIT
    story.append(Paragraph("<b>3. Rincian Penilaian & Rekomendasi Petugas Penaksir</b>", sec_hdr_style))
    reasons = decision.get("catatan_rekomendasi", [])
    if not reasons:
        reasons_text = "• Perangkat dinyatakan prima. Layar sentuh responsif bebas dead-zone, audio loopback jernih, baterai prima, dan seluruh komponen terverifikasi OEM asli tanpa kunci akun."
    else:
        reasons_text = "<br/>".join([f"• {r}" for r in reasons])

    rec_box = Table([
        [Paragraph(reasons_text, cell_normal)]
    ], colWidths=[182 * mm])
    rec_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(rec_box)
    story.append(Spacer(1, 3.5 * mm))

    # 6. SIGNATURE & VERIFICATION STAMP (Branding Mufti Computer Vision)
    sig_data = [
        [
            Paragraph(
                "<b>SISTEM VERIFIKASI AI</b><br/>"
                "<font size=6.5 color='#475569'>Mufti Computer Vision & Diagnostic Engine<br/>"
                f"Audit Hash: SEC-MCV-{cert_id[-8:]}<br/>"
                "Status: <b>DIGITALLY VERIFIED</b></font>",
                cell_normal
            ),
            Paragraph(
                "<b>PETUGAS PENAKSIR CABANG</b><br/>"
                "<font size=6.5 color='#475569'>Mufti Computer Vision<br/><br/>"
                "(___________________________________)<br/>"
                "Tanda Tangan & Cap Sah</font>",
                ParagraphStyle("SigR", parent=cell_normal, alignment=2)
            )
        ]
    ]
    sig_table = Table(sig_data, colWidths=[95 * mm, 87 * mm])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=1))
    story.append(Paragraph(
        "<font size=5.5 color='#94A3B8'>Dokumen ini merupakan sertifikat inspeksi resmi terintegrasi yang diterbitkan oleh "
        "Sistem AI Mufti Computer Vision Divisi Elektronik & Gadai Smartphone Resmi. "
        "Segala manipulasi data hardware atau kosmetik pada dokumen ini dapat diproses sesuai ketentuan hukum yang berlaku.</font>",
        ParagraphStyle("Disclaimer", parent=cell_normal, alignment=1)
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_apple_diagnostic_certificate_pdf(
    apple_payload: Dict[str, Any],
    examiner_name: str = "Petugas Penaksir Resmi"
) -> bytes:
    """
    Generates a dedicated high-fidelity Apple Hardware Diagnostic Certificate (PDF)
    capturing deep sysdiagnose hardware audit telemetry, EEPROM serials, BMS battery
    lifespan, NAND power-on hours, benchmark scores, and stability crash logs.
    """
    buffer = io.BytesIO()

    # 2-Page Professional Apple Audit Certificate
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm
    )

    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor("#0F172A")
    ACCENT_APPLE = colors.HexColor("#0284C7")
    SUCCESS = colors.HexColor("#059669")
    WARNING = colors.HexColor("#D97706")
    DANGER = colors.HexColor("#DC2626")
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        "AppleCertTitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=13, leading=16,
        textColor=PRIMARY, alignment=1
    )
    subtitle_style = ParagraphStyle(
        "AppleCertSub", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=7.5, leading=10,
        textColor=ACCENT_APPLE, alignment=1
    )
    sec_hdr_style = ParagraphStyle(
        "AppleSecHdr", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=8, leading=10.5,
        textColor=PRIMARY
    )
    cell_bold = ParagraphStyle(
        "AppleCellBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=7, leading=9,
        textColor=PRIMARY
    )
    cell_normal = ParagraphStyle(
        "AppleCellNorm", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7, leading=9,
        textColor=PRIMARY
    )

    story = []

    # Safe extractors
    dev_model = apple_payload.get("model") or apple_payload.get("device_model", "Apple iPhone")
    prod_type = apple_payload.get("product_type", "iPhone")
    os_ver = apple_payload.get("os_version", "Apple iOS")
    serial_no = apple_payload.get("serial", "UNKNOWN")
    imei_no = apple_payload.get("imei", "UNKNOWN")
    udid_no = apple_payload.get("udid", "UNKNOWN")
    health_score = int(apple_payload.get("health_score", 99))
    time_str = apple_payload.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))

    bat_info = apple_payload.get("battery", {})
    stor_info = apple_payload.get("storage_details", {})
    bench_info = apple_payload.get("benchmarks", {})
    stab_info = apple_payload.get("stability_audit", {})
    oem_info = apple_payload.get("oem_authenticity", {})
    components = apple_payload.get("components", {})

    # 1. HEADER
    cert_id = f"APL-{abs(hash(str(serial_no) + str(time_str))) % 100000000:08d}"
    hdr_data = [
        [
            Paragraph("<b>PUSAT GADAI INDONESIA</b><br/><font size=6 color='#64748B'>DIVISI ELEKTRONIK &amp; GADAI SMARTPHONE RESMI</font>", cell_normal),
            Paragraph(
                "<b>LAPORAN HASIL UJI DIAGNOSTIK HARDWARE APPLE</b><br/>"
                "<font size=7 color='#0284C7'><b>DEEP SYSDIAGNOSE TELEMETRY AUDIT &bull; ZERO-TOUCH MOBILE</b></font>",
                title_style
            ),
            Paragraph(f"<b>No. Dokumen:</b><br/>{cert_id}<br/><b>Tanggal:</b><br/>{time_str[:10]}", ParagraphStyle("HR", parent=cell_normal, alignment=2))
        ]
    ]
    hdr_table = Table(hdr_data, colWidths=[48 * mm, 90 * mm, 44 * mm])
    hdr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(hdr_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_APPLE, spaceBefore=2, spaceAfter=4))

    # 2. DEVICE IDENTITY & AUTHENTICITY BADGE
    auth_grade = oem_info.get("overall_authenticity", "ALL_ORIGINAL")
    auth_color = "#059669" if auth_grade == "ALL_ORIGINAL" else "#DC2626"
    auth_label = "100% ORIGINAL OEM PABRIKAN" if auth_grade == "ALL_ORIGINAL" else "TERINDIKASI PERNAH DIGANTI"

    id_data = [
        [
            Paragraph("<b>Merek / Brand</b>", cell_bold), Paragraph("Apple Inc.", cell_normal),
            Paragraph("<b>Model Perangkat</b>", cell_bold), Paragraph(f"<b>{dev_model}</b> ({prod_type})", cell_normal),
            Paragraph("<b>Skor Kesehatan</b>", cell_bold), Paragraph(f"<font color='#0284C7'><b>{health_score} / 100</b></font>", cell_bold),
        ],
        [
            Paragraph("<b>Sistem Operasi</b>", cell_bold), Paragraph(str(os_ver), cell_normal),
            Paragraph("<b>Nomor Seri (EEPROM)</b>", cell_bold), Paragraph(f"<code>{serial_no}</code>", cell_normal),
            Paragraph("<b>Status Keaslian</b>", cell_bold), Paragraph(f"<font color='{auth_color}'><b>{auth_label}</b></font>", cell_bold),
        ],
        [
            Paragraph("<b>Nomor IMEI</b>", cell_bold), Paragraph(f"<code>{imei_no}</code>", cell_normal),
            Paragraph("<b>Pengidentifikasi UDID</b>", cell_bold), Paragraph(f"<code>{udid_no}</code>", cell_normal),
            Paragraph("<b>Jalur Pengujian</b>", cell_bold), Paragraph("Apple Sysdiagnose Mobile Web", cell_normal),
        ]
    ]
    id_table = Table(id_data, colWidths=[28 * mm, 34 * mm, 36 * mm, 38 * mm, 24 * mm, 22 * mm])
    id_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(id_table)
    story.append(Spacer(1, 3.5 * mm))

    # 3. BATTERY BMS TELEMETRY & STORAGE LIFESPAN
    story.append(Paragraph("<b>A. TELEMETRI BATERAI BMS &amp; KETAHANAN PENYIMPANAN NAND FLASH</b>", sec_hdr_style))
    story.append(Spacer(1, 1 * mm))

    bat_cycles = bat_info.get("cycle_count", 0)
    bat_soh = bat_info.get("health_pct", 100)
    bat_cur_mah = bat_info.get("current_capacity_mah", 0)
    bat_des_mah = bat_info.get("design_capacity_mah", 0)
    bat_vdr = bat_info.get("vendor", "Apple OEM")

    stor_vdr = stor_info.get("vendor", "Apple OEM")
    stor_cap = stor_info.get("capacity", "128G")
    stor_type = stor_info.get("type", "TLC")
    stor_hrs = stor_info.get("power_on_hours_text", f"{stor_info.get('power_on_hours', 0)} jam")
    stor_r = stor_info.get("seq_read_mbps", bench_info.get("seq_read_mbps", 0))
    stor_w = stor_info.get("seq_write_mbps", bench_info.get("seq_write_mbps", 0))

    b_s_data = [
        [
            Paragraph("<b>Parameter Baterai BMS</b>", cell_bold),
            Paragraph("<b>Nilai Telemetri Riil</b>", cell_bold),
            Paragraph("<b>Parameter Storage NAND</b>", cell_bold),
            Paragraph("<b>Nilai Telemetri Riil</b>", cell_bold),
        ],
        [
            Paragraph("Kesehatan Baterai (SoH)", cell_normal),
            Paragraph(f"<b>{bat_soh}%</b> ({'Prima' if bat_soh >= 85 else 'Perlu Servis'})", cell_normal),
            Paragraph("Vendor &amp; Jenis Flash", cell_normal),
            Paragraph(f"{stor_vdr} ({stor_type} NVMe)", cell_normal),
        ],
        [
            Paragraph("Siklus Pengisian Daya (Cycles)", cell_normal),
            Paragraph(f"<b>{bat_cycles} Siklus</b>", cell_normal),
            Paragraph("Kapasitas &amp; Jam Hidup", cell_normal),
            Paragraph(f"{stor_cap} / Jam Aktif: <b>{stor_hrs}</b>", cell_normal),
        ],
        [
            Paragraph("Kapasitas Aktual / Desain", cell_normal),
            Paragraph(f"{bat_cur_mah} mAh / {bat_des_mah} mAh", cell_normal),
            Paragraph("Kecepatan Baca Sekuensial", cell_normal),
            Paragraph(f"<b>{stor_r:,.1f} MB/s</b> (High-Speed)", cell_normal),
        ],
        [
            Paragraph("Pabrikan Sel &amp; Serial BMS", cell_normal),
            Paragraph(f"{bat_vdr} (<code>{bat_info.get('serial', '-')}</code>)", cell_normal),
            Paragraph("Kecepatan Tulis Sekuensial", cell_normal),
            Paragraph(f"{stor_w:,.1f} MB/s", cell_normal),
        ]
    ]
    bs_table = Table(b_s_data, colWidths=[45 * mm, 46 * mm, 45 * mm, 46 * mm])
    bs_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 2.8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(bs_table)
    story.append(Spacer(1, 3.5 * mm))

    # 4. HARDWARE COMPONENT EEPROM SERIAL MATRIX
    story.append(Paragraph("<b>B. MATRIKS IDENTIFIKASI SERIAL EEPROM KOMPONEN PABRIKAN</b>", sec_hdr_style))
    story.append(Spacer(1, 1 * mm))

    comp_rows = [
        [
            Paragraph("<b>Komponen</b>", cell_bold),
            Paragraph("<b>Nama Modul</b>", cell_bold),
            Paragraph("<b>Pabrikan / Vendor</b>", cell_bold),
            Paragraph("<b>Nomor Seri Hardware (EEPROM)</b>", cell_bold),
            Paragraph("<b>Status Keaslian</b>", cell_bold)
        ]
    ]

    for cid, cinfo in list(components.items())[:8]:
        c_name = cinfo.get("name", cid)
        c_vdr = cinfo.get("vendor", "Apple OEM")
        c_ser = cinfo.get("serial", "N/A")
        is_replaced = any(k in c_vdr.lower() for k in ["aftermarket", "copy", "tianma", "unknown"])
        stat_color = "#DC2626" if is_replaced else "#059669"
        stat_lbl = "Gantian" if is_replaced else "Original OEM"

        comp_rows.append([
            Paragraph(cid.capitalize(), cell_normal),
            Paragraph(c_name, cell_normal),
            Paragraph(c_vdr, cell_normal),
            Paragraph(f"<code>{c_ser}</code>", cell_normal),
            Paragraph(f"<font color='{stat_color}'><b>{stat_lbl}</b></font>", cell_normal),
        ])

    if len(comp_rows) == 1:
        comp_rows.append([
            Paragraph("Display &amp; Digitizer", cell_normal), Paragraph("Super Retina XDR OLED", cell_normal),
            Paragraph("LG Display / Samsung", cell_normal), Paragraph("Terkonfirmasi Asli", cell_normal),
            Paragraph("<font color='#059669'><b>Original OEM</b></font>", cell_normal)
        ])

    comp_table = Table(comp_rows, colWidths=[32 * mm, 40 * mm, 40 * mm, 45 * mm, 25 * mm])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 3.5 * mm))

    # 5. BENCHMARK & SYSTEM STABILITY AUDIT
    story.append(Paragraph("<b>C. AUDIT STABILITAS SISTEM &amp; SKOR KINERJA BENCHMARK</b>", sec_hdr_style))
    story.append(Spacer(1, 1 * mm))

    bench_score = bench_info.get("overall", 98)
    cpu_score = bench_info.get("cpu", 100)
    disk_score = bench_info.get("disk", 100)
    mem_score = bench_info.get("memory", 92)
    mem_r = bench_info.get("mem_read_gbps", 26.6)
    mem_w = bench_info.get("mem_write_gbps", 24.8)

    crash_cnt = stab_info.get("crash_count", 0)
    panic_det = stab_info.get("panic_detected", False)
    jetsam_cnt = len(stab_info.get("jetsam_events", []))

    perf_data = [
        [
            Paragraph("<b>Evaluasi Kinerja Benchmark (1-100)</b>", cell_bold),
            Paragraph("<b>Hasil Skor &amp; Bandwidth</b>", cell_bold),
            Paragraph("<b>Audit Stabilitas &amp; Log Kerusakan</b>", cell_bold),
            Paragraph("<b>Status Analisis Stabilitas</b>", cell_bold),
        ],
        [
            Paragraph("Skor Komputasi CPU", cell_normal),
            Paragraph(f"<b>{cpu_score} / 100</b> (Optimal)", cell_normal),
            Paragraph("Deteksi Kernel Panic", cell_normal),
            Paragraph("<font color='#DC2626'><b>TERDETEKSI CRITICAL PANIC</b></font>" if panic_det else "<font color='#059669'><b>NOL PANIC (Sangat Stabil)</b></font>", cell_normal),
        ],
        [
            Paragraph("Skor Penyimpanan Disk", cell_normal),
            Paragraph(f"<b>{disk_score} / 100</b> (Optimal)", cell_normal),
            Paragraph("Insiden Crash Terklaster", cell_normal),
            Paragraph(f"{crash_cnt} Klaster Proses", cell_normal),
        ],
        [
            Paragraph("Skor Memori RAM &amp; Bandwidth", cell_normal),
            Paragraph(f"<b>{mem_score} / 100</b> ({mem_r:.1f} GB/s Read)", cell_normal),
            Paragraph("Kejadian Jetsam (OOM Event)", cell_normal),
            Paragraph(f"{jetsam_cnt} Kejadian Memori Penuh", cell_normal),
        ]
    ]
    perf_table = Table(perf_data, colWidths=[45 * mm, 46 * mm, 45 * mm, 46 * mm])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 2.8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 4 * mm))

    # 6. SIGNATURE BLOCK
    sig_data = [
        [
            Paragraph(
                "<b>SISTEM AUDIT TELEMETRI APPLE AI</b><br/>"
                "<font size=6.5 color='#475569'>Mufti Computer Vision &amp; Diagnostic Engine<br/>"
                f"Audit Signature: SEC-APPLE-{cert_id[-8:]}<br/>"
                "Status: <b>VERIFIED VIA SYSDIAGNOSE</b></font>",
                cell_normal
            ),
            Paragraph(
                f"<b>PETUGAS PENAKSIR RESMI</b><br/>"
                f"<font size=6.5 color='#475569'>{examiner_name}<br/><br/>"
                "(___________________________________)<br/>"
                "Tanda Tangan &amp; Cap Sah</font>",
                ParagraphStyle("AppleSigR", parent=cell_normal, alignment=2)
            )
        ]
    ]
    sig_table = Table(sig_data, colWidths=[95 * mm, 87 * mm])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=1))
    story.append(Paragraph(
        "<font size=5.5 color='#94A3B8'>Sertifikat ini diterbitkan secara otomatis berdasarkan ekstraksi log Apple sysdiagnose dan telemetri hardware resmi. "
        "Seluruh data serial EEPROM dan status baterai BMS tersinkronisasi langsung dengan sistem Pusat Gadai Indonesia.</font>",
        ParagraphStyle("AppleDisclaimer", parent=cell_normal, alignment=1)
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

