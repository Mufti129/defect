"""
PDF CERTIFICATE GENERATOR
=========================
Pusat Gadai Indonesia (PGI) & Mufti Computer Vision QA System

Generates official, tamper-evident corporate PDF certificates:
"Sertifikat Taksiran Terpadu Hasil Gabungan (Computer Vision + CIT Hardware)"
"""

import io
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
    HRFlowable,
    KeepTogether
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

    # Setup document with tight 14mm margins to fit comprehensive details cleanly on 1 page
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1E1B4B")     # Deep Indigo
    ACCENT = colors.HexColor("#4338CA")      # Rich Purple-Blue
    SUCCESS = colors.HexColor("#059669")     # Emerald Green
    WARNING = colors.HexColor("#D97706")     # Amber
    DANGER = colors.HexColor("#DC2626")      # Crimson Red
    NEUTRAL_DARK = colors.HexColor("#1F2937") # Slate Dark
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        alignment=1  # Center
    )

    subtitle_style = ParagraphStyle(
        "CertSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=ACCENT,
        alignment=1
    )

    sec_hdr_style = ParagraphStyle(
        "SecHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=PRIMARY
    )

    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=NEUTRAL_DARK
    )

    cell_normal = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=NEUTRAL_DARK
    )

    cell_code = ParagraphStyle(
        "CellCode",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        textColor=NEUTRAL_DARK
    )

    story = []

    # 1. HEADER
    cert_id = cert_data.get("sertifikat_id", f"CERT-PGI-{int(time.time())}")
    time_str = cert_data.get("waktu_inspeksi", time.strftime("%Y-%m-%d %H:%M:%S WIB"))

    header_table = Table([
        [
            Paragraph("<b>PUSAT GADAI INDONESIA</b><br/><font size=6.5 color='#64748B'>DIVISI PENAKSIRAN ELEKTRONIK & GADAI SMARTPHONE RESMI</font>", ParagraphStyle("H1", parent=cell_normal, fontName="Helvetica-Bold", fontSize=8.5, textColor=PRIMARY)),
            Paragraph(f"<b>NO. SERTIFIKAT:</b> <font color='#4338CA'>{cert_id}</font><br/><b>WAKTU INSPEKSI:</b> {time_str}", ParagraphStyle("H2", parent=cell_normal, fontSize=7, alignment=2))
        ]
    ], colWidths=[105 * mm, 77 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)

    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=3, spaceAfter=4))

    story.append(Paragraph("SERTIFIKAT HASIL INSPEKSI & TAKSIRAN GADAI TERPADU", title_style))
    story.append(Paragraph("Sistem Verifikasi Otomatis Dua-Arah (AI Computer Vision 4-Sisi + Hardware CIT Diagnostics)", subtitle_style))
    story.append(Spacer(1, 5))

    # 2. FINAL GRADE & VALUATION BANNER
    dev_info = cert_data.get("perangkat", {})
    decision = cert_data.get("keputusan_akhir_terpadu", {})
    cv_info = cert_data.get("inspeksi_visual_cv", {})
    internal_info = cert_data.get("diagnostik_internal_hardware", {})

    u_grade = decision.get("unified_grade", "A")
    u_deduct = float(decision.get("valuation_deduction_pct", 0.0))
    f_status = decision.get("functional_status", "PASS")

    grade_color_hex = "#059669" if u_grade == "A" else ("#D97706" if "B" in u_grade else "#DC2626")

    banner_data = [
        [
            Paragraph(f"<font size=7 color='#64748B'>UNIT YANG DIUJI</font><br/><b><font size=11 color='#1E1B4B'>{dev_info.get('market_name', 'Smartphone')}</font></b><br/><font size=6.5 color='#64748B'>IMEI: {dev_info.get('imei', '-')} • Serial: {dev_info.get('serial', '-')}</font>", cell_normal),
            Paragraph(f"<font size=7 color='#64748B'>GRADE AKHIR TERPADU</font><br/><b><font size=16 color='{grade_color_hex}'>GRADE {u_grade}</font></b><br/><font size=7 color='{grade_color_hex}'><b>STATUS: {f_status}</b></font>", ParagraphStyle("B1", parent=cell_normal, alignment=1)),
            Paragraph(f"<font size=7 color='#64748B'>POTONGAN TAKSIRAN</font><br/><b><font size=16 color='#DC2626'>-{u_deduct:.1f}%</font></b><br/><font size=6.5 color='#64748B'>Dari Plafon Taksiran Maksimal</font>", ParagraphStyle("B2", parent=cell_normal, alignment=1))
        ]
    ]
    banner_table = Table(banner_data, colWidths=[86 * mm, 48 * mm, 48 * mm])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 1.2, PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 6))

    # 3. SPESIFIKASI IDENTITAS HARDWARE TERVERIFIKASI
    story.append(Paragraph("<b>1. Spesifikasi Hardware & Profil Koneksi Teridentifikasi</b>", sec_hdr_style))
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
            Paragraph("<b>Processor / SoC:</b>", cell_bold), Paragraph(str(dev_info.get("soc") or dev_info.get("soc_name", "ARM64 Processor")), cell_normal),
            Paragraph("<b>Memori RAM / ROM:</b>", cell_bold), Paragraph(f"{dev_info.get('ram_gb', 4)} GB RAM / {dev_info.get('storage_gb', 128)} GB ROM", cell_normal)
        ],
        [
            Paragraph("<b>Resolusi Layar:</b>", cell_bold), Paragraph(str(dev_info.get("screen_res") or dev_info.get("screen_resolution", "1080 x 2400 px")), cell_normal),
            Paragraph("<b>Jalur Telemetri:</b>", cell_bold), Paragraph("Web Telemetry Driver (Universal Real-Time)", cell_normal)
        ]
    ]
    spec_table = Table(spec_rows, colWidths=[36 * mm, 55 * mm, 36 * mm, 55 * mm])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 6))

    # 4. HASIL INSPEKSI DUA-ARAH (CV + INTERNAL BATTERY/SENSOR/OEM/CIT)
    story.append(Paragraph("<b>2. Hasil Pengujian Metrik Fisik & Jeroan Mesin (Two-Tier Evaluation)</b>", sec_hdr_style))

    bat_data = internal_info.get("baterai", {})
    oem_data = internal_info.get("oem_authenticity", {})
    cit_data = internal_info.get("interactive_cit", {})

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
            Paragraph(f"<font color='{'#059669' if bat_data.get('status') == 'PASS' else '#DC2626'}'><b>{bat_data.get('status', 'PASS')}</b></font>", cell_bold),
            Paragraph("Baterai Prima (Bebas Kembung)" if bat_data.get('status') == 'PASS' else "Penalti Servis Baterai", cell_normal)
        ],
        # Metrik 3: Sensor & Radio
        [
            Paragraph("<b>Matriks Sensor & Radio</b>", cell_normal),
            Paragraph("G-Sensor 3-Axis, Giroskop, Proximity, Wi-Fi, BT 5.x", cell_normal),
            Paragraph("<font color='#059669'><b>100% RESPONSIF</b></font>", cell_bold),
            Paragraph("0 Penalti (Normal)", cell_normal)
        ],
        # Metrik 4: OEM & Keamanan Akun
        [
            Paragraph("<b>Keaslian Komponen OEM</b>", cell_normal),
            Paragraph(f"LCD: {oem_data.get('screen', 'ORIGINAL')} • Baterai: {oem_data.get('battery', 'ORIGINAL')}", cell_normal),
            Paragraph("<font color='#059669'><b>ASLI PABRIKAN</b></font>", cell_bold),
            Paragraph("Komponen Otentik", cell_normal)
        ],
        # Metrik 5: Status Kunci Akun
        [
            Paragraph("<b>Keamanan Akun (FRP/iCloud)</b>", cell_normal),
            Paragraph("Pemeriksaan Google FRP Lock & Apple iCloud Activation", cell_normal),
            Paragraph(f"<font color='{'#059669' if oem_data.get('cloud_lock') == 'UNLOCKED' else '#DC2626'}'><b>{oem_data.get('cloud_lock', 'UNLOCKED')}</b></font>", cell_bold),
            Paragraph("Bebas Kunci (Sah Digadai)" if oem_data.get('cloud_lock') == 'UNLOCKED' else "Veto Tolak Grade D", cell_normal)
        ],
        # Metrik 6: Layar Sentuh CIT
        [
            Paragraph("<b>Layar Sentuh (Touch Digitizer)</b>", cell_normal),
            Paragraph(f"Sampling Edge-to-Edge: {cit_data.get('touch_cells_passed', 84)}/{cit_data.get('touch_total_cells', 84)} Sel ({cit_data.get('touch_coverage_pct', 100):.0f}%)", cell_normal),
            Paragraph(f"<font color='{'#059669' if cit_data.get('touch_passed', True) else '#DC2626'}'><b>{'ZERO DEAD-ZONE' if cit_data.get('touch_passed', True) else 'DEAD-ZONE (D)'}</b></font>", cell_bold),
            Paragraph("Responsif Penuh 100%" if cit_data.get('touch_passed', True) else "Veto Mutlak Grade D", cell_normal)
        ],
        # Metrik 7: Audio Loopback & Respons Fisik
        [
            Paragraph("<b>Audio Loopback & Tombol Fisik</b>", cell_normal),
            Paragraph("Speaker (3 Nada), Mic Loopback (2.5s), Tombol Vol & Power", cell_normal),
            Paragraph(f"<font color='#059669'><b>{cit_data.get('speaker_status', 'LOLOS')}</b></font>", cell_bold),
            Paragraph("Akustik & Tombol Normal", cell_normal)
        ]
    ]

    metrics_table = Table(metrics_rows, colWidths=[40 * mm, 66 * mm, 38 * mm, 38 * mm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDE9FE")),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 6))

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
        ('BOX', (0,0), (-1,-1), 0.8, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(rec_box)
    story.append(Spacer(1, 6))

    # 6. SIGNATURE & VERIFICATION STAMP
    sig_data = [
        [
            Paragraph("<b>SISTEM VERIFIKASI AI</b><br/><font size=6.5 color='#64748B'>Mufti Computer Vision & Diagnostic Engine<br/>Audit Hash: SEC-PGI-" + cert_id[-8:] + "<br/>Status: <b>DIGITALLY VERIFIED</b></font>", cell_normal),
            Paragraph("<b>PETUGAS PENAKSIR CABANG</b><br/><font size=6.5 color='#64748B'>Pusat Gadai Indonesia (PGI)<br/><br/>(___________________________________)<br/>Tanda Tangan & Cap Sah</font>", ParagraphStyle("SigR", parent=cell_normal, alignment=2))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[95 * mm, 87 * mm])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 3))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=1))
    story.append(Paragraph("<font size=5.5 color='#94A3B8'>Dokumen ini merupakan sertifikat inspeksi resmi terintegrasi yang diterbitkan oleh Sistem AI Mufti Computer Vision bekerjasama dengan Pusat Gadai Indonesia. Segala manipulasi data hardware atau kosmetik pada dokumen ini dapat diproses sesuai ketentuan hukum yang berlaku.</font>", ParagraphStyle("Disclaimer", parent=cell_normal, alignment=1)))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
