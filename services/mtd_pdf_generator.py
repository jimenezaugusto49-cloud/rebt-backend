"""
mtd_pdf_generator.py
Genera el PDF de la Memoria Técnica de Diseño (MTD)
a partir del resultado de mtd_logic.calcular_mtd()
"""

import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm


# ─────────────────────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────────────────────

def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="Titulo",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,
        spaceAfter=6,
        textColor=colors.HexColor("#1a3a5c"),
    ))
    styles.add(ParagraphStyle(
        name="Subtitulo",
        parent=styles["Normal"],
        fontSize=10,
        alignment=1,
        textColor=colors.HexColor("#444444"),
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="Seccion",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=14,
        spaceAfter=4,
        borderPad=2,
    ))
    styles.add(ParagraphStyle(
        name="Campo",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="Unifilar",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Courier",
        spaceAfter=2,
        leftIndent=20,
    ))
    styles.add(ParagraphStyle(
        name="PieAviso",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#888888"),
        spaceBefore=20,
        alignment=1,
    ))

    return styles


# ─────────────────────────────────────────────────────────────
# ESQUEMA UNIFILAR EN TEXTO (MVP)
# ─────────────────────────────────────────────────────────────

def _generar_unifilar(mtd: dict) -> list:
    """Genera el esquema unifilar como bloque de texto monoespaciado."""
    styles = _build_styles()
    lines = []

    lines.append(Paragraph("[RED DE SUMINISTRO]", styles["Unifilar"]))
    lines.append(Paragraph("     |", styles["Unifilar"]))
    lines.append(Paragraph(f"[IGA {mtd['iga_A']}A]", styles["Unifilar"]))
    lines.append(Paragraph("     |", styles["Unifilar"]))
    lines.append(Paragraph(
        f"[ID {mtd['diferencial_A']}A / {mtd['diferencial_mA']}mA]",
        styles["Unifilar"]
    ))
    lines.append(Paragraph("     |", styles["Unifilar"]))

    circuitos = mtd.get("circuitos", [])
    for i, c in enumerate(circuitos):
        prefijo = "└──" if i == len(circuitos) - 1 else "├──"
        lines.append(Paragraph(
            f"     {prefijo} {c['codigo']} [{c['pia_A']}A - {c['seccion_mm2']}mm²] {c['nombre']}",
            styles["Unifilar"]
        ))

    return lines


# ─────────────────────────────────────────────────────────────
# TABLA DE CIRCUITOS
# ─────────────────────────────────────────────────────────────

def _tabla_circuitos(circuitos: list) -> Table:
    encabezado = ["Circuito", "Descripción", "PIA (A)", "Sección (mm²)"]
    filas = [encabezado]

    for c in circuitos:
        filas.append([
            c["codigo"],
            c["nombre"],
            str(c["pia_A"]),
            str(c["seccion_mm2"]),
        ])

    tabla = Table(filas, colWidths=[30*mm, 80*mm, 30*mm, 35*mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1),(-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN",        (2, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    return tabla


# ─────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────

def generar_pdf_mtd(mtd: dict, output_path: str):
    """
    Genera el PDF de la MTD a partir del dict devuelto por calcular_mtd().
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = _build_styles()
    elements = []
    fecha = datetime.datetime.now().strftime("%d/%m/%Y")

    # ── Cabecera ──────────────────────────────────────────────
    elements.append(Paragraph("MEMORIA TÉCNICA DE DISEÑO (MTD)", styles["Titulo"]))
    elements.append(Paragraph(
        f"Instalación Eléctrica en Baja Tensión · REBT RD 842/2002 · {fecha}",
        styles["Subtitulo"]
    ))

    # ── 1. Datos del titular ──────────────────────────────────
    elements.append(Paragraph("1. DATOS DEL TITULAR", styles["Seccion"]))
    elements.append(Paragraph(f"<b>Nombre:</b> {mtd['titular']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>DNI/NIE:</b> {mtd['dni']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>Dirección:</b> {mtd['direccion']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>Municipio:</b> {mtd['municipio']} ({mtd['provincia']})", styles["Campo"]))
    if mtd.get("referencia_catastral"):
        elements.append(Paragraph(f"<b>Ref. Catastral:</b> {mtd['referencia_catastral']}", styles["Campo"]))

    # ── 2. Datos de la instalación ────────────────────────────
    elements.append(Paragraph("2. DATOS DE LA INSTALACIÓN", styles["Seccion"]))
    elements.append(Paragraph(f"<b>Tipo:</b> {mtd['tipo_instalacion'].capitalize()}", styles["Campo"]))
    elements.append(Paragraph(f"<b>Uso:</b> Vivienda", styles["Campo"]))
    elements.append(Paragraph(f"<b>Tensión:</b> {mtd['tension']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>Método de instalación:</b> {mtd['metodo_instalacion'].capitalize()}", styles["Campo"]))
    elements.append(Paragraph(
        f"<b>Toma de tierra:</b> {'Sí' if mtd['toma_tierra'] else 'No'}",
        styles["Campo"]
    ))

    # ── 3. Características de la vivienda ─────────────────────
    elements.append(Paragraph("3. CARACTERÍSTICAS DE LA VIVIENDA", styles["Seccion"]))
    elements.append(Paragraph(f"<b>Superficie:</b> {mtd['superficie']} m²", styles["Campo"]))
    elements.append(Paragraph(f"<b>Habitaciones:</b> {mtd['habitaciones']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>Baños:</b> {mtd['banos']}", styles["Campo"]))
    elements.append(Paragraph(
        f"<b>Cocina eléctrica:</b> {'Sí' if mtd['cocina_electrica'] else 'No'}",
        styles["Campo"]
    ))
    elements.append(Paragraph(
        f"<b>Aire acondicionado:</b> {'Sí' if mtd['aire_acondicionado'] else 'No'}",
        styles["Campo"]
    ))
    elements.append(Paragraph(
        f"<b>Calefacción eléctrica:</b> {'Sí' if mtd['calefaccion_electrica'] else 'No'}",
        styles["Campo"]
    ))

    # ── 4. Memoria descriptiva ────────────────────────────────
    elements.append(Paragraph("4. MEMORIA DESCRIPTIVA", styles["Seccion"]))
    elements.append(Paragraph(
        f"La presente Memoria Técnica de Diseño describe la instalación eléctrica de "
        f"<b>{mtd['tipo_instalacion']}</b> en vivienda situada en <b>{mtd['direccion']}</b>, "
        f"{mtd['municipio']} ({mtd['provincia']}), con una superficie de <b>{mtd['superficie']} m²</b>.",
        styles["Campo"]
    ))
    elements.append(Paragraph(
        f"La instalación corresponde a electrificación de grado <b>{mtd['electrificacion'].upper()}</b> "
        f"según ITC-BT-25, con una potencia prevista de <b>{mtd['potencia_prevista_kw']} kW</b> "
        f"conforme a ITC-BT-10. El suministro es monofásico a 230 V / 50 Hz.",
        styles["Campo"]
    ))
    elements.append(Paragraph(
        f"La instalación consta de <b>{mtd['num_circuitos']} circuitos independientes</b>, "
        f"protegidos individualmente mediante interruptores magnetotérmicos. "
        f"La protección diferencial se realiza mediante un interruptor diferencial de "
        f"{mtd['diferencial_A']}A / {mtd['diferencial_mA']}mA. "
        f"El Interruptor General Automático (IGA) es de {mtd['iga_A']}A.",
        styles["Campo"]
    ))

    # ── 5. Circuitos y protecciones ───────────────────────────
    elements.append(Paragraph("5. CIRCUITOS Y PROTECCIONES (ITC-BT-25)", styles["Seccion"]))
    elements.append(Spacer(1, 4))
    elements.append(_tabla_circuitos(mtd["circuitos"]))

    # ── 6. Esquema unifilar ───────────────────────────────────
    elements.append(Paragraph("6. ESQUEMA UNIFILAR", styles["Seccion"]))
    elements.append(Spacer(1, 4))
    elements.extend(_generar_unifilar(mtd))

    # ── 7. Datos del instalador ───────────────────────────────
    elements.append(Paragraph("7. DATOS DEL INSTALADOR AUTORIZADO", styles["Seccion"]))
    elements.append(Paragraph(f"<b>Nombre/Empresa:</b> {mtd['instalador_nombre']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>NIF/CIF:</b> {mtd['instalador_nie']}", styles["Campo"]))
    elements.append(Paragraph(f"<b>Nº Instalador:</b> {mtd['instalador_num']}", styles["Campo"]))

    # ── Pie de página ─────────────────────────────────────────
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Documento generado por REBT Experto · Cumple RD 842/2002 · "
        "Este documento tiene carácter orientativo. "
        "El instalador autorizado es responsable de su contenido y legalización.",
        styles["PieAviso"]
    ))

    doc.build(elements)
