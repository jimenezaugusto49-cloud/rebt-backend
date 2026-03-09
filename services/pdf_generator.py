from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import datetime


def _iter_dict_field(value):
    """
    Devuelve los pares (k, v) de un campo que debería ser dict.
    Si el modelo devuelve un string o None en lugar de dict, lo trata
    como observación de texto libre en lugar de romper con .items().
    """
    if isinstance(value, dict):
        return value.items()
    return []  # Vacío; el llamador puede mostrar el valor como texto si lo desea


def _safe_str(value):
    """Convierte cualquier valor a string seguro para Paragraph."""
    if value is None:
        return ""
    if isinstance(value, dict):
        # Si por alguna razón llega un dict donde se espera string, lo serializa legible
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def generar_pdf_informe(data: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elements = []
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='TituloCentro',
        parent=styles['Heading1'],
        alignment=1
    ))

    # ── Título ────────────────────────────────────────────────
    titulo = _safe_str(data.get("titulo")) or "Informe Técnico REBT"
    elements.append(Paragraph(titulo, styles['TituloCentro']))
    elements.append(Spacer(1, 12))

    # ── Fecha ─────────────────────────────────────────────────
    fecha = _safe_str(data.get("fecha")) or datetime.datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"<b>Fecha:</b> {fecha}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # ── Tipo de cálculo ───────────────────────────────────────
    tipo = _safe_str(data.get("tipo_calculo"))
    if tipo:
        elements.append(Paragraph(f"<b>Tipo de cálculo:</b> {tipo}", styles['Normal']))
        elements.append(Spacer(1, 12))

    # ── Parámetros ────────────────────────────────────────────
    parametros = data.get("parametros")
    if parametros:
        elements.append(Paragraph("<b>Parámetros:</b>", styles['Heading2']))
        for k, v in _iter_dict_field(parametros):
            elements.append(Paragraph(f"{k}: {_safe_str(v)}", styles['Normal']))
        elements.append(Spacer(1, 12))

    # ── Resultado ─────────────────────────────────────────────
    resultado = data.get("resultado")
    if resultado:
        elements.append(Paragraph("<b>Resultado:</b>", styles['Heading2']))
        for k, v in _iter_dict_field(resultado):
            elements.append(Paragraph(f"{k}: {_safe_str(v)}", styles['Normal']))
        elements.append(Spacer(1, 12))

    # ── Normativa ─────────────────────────────────────────────
    normativa = data.get("normativa")
    if normativa:
        elements.append(Paragraph("<b>Normativa aplicada:</b>", styles['Heading2']))
        for k, v in _iter_dict_field(normativa):
            elements.append(Paragraph(f"{k}: {_safe_str(v)}", styles['Normal']))
        elements.append(Spacer(1, 12))

    # ── Observaciones ─────────────────────────────────────────
    observaciones = _safe_str(data.get("observaciones"))
    if observaciones:
        elements.append(Paragraph("<b>Observaciones:</b>", styles['Heading2']))
        elements.append(Paragraph(observaciones, styles['Normal']))
        elements.append(Spacer(1, 12))

    # ── Aviso legal ───────────────────────────────────────────
    aviso = _safe_str(data.get("aviso_legal"))
    if aviso:
        elements.append(Paragraph("<b>Aviso legal:</b>", styles['Heading2']))
        elements.append(Paragraph(aviso, styles['Normal']))

    doc.build(elements)