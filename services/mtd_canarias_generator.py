"""
mtd_canarias_generator.py
Genera el MTD oficial de Canarias pre-relleno en .docx
usando la plantilla del instalador como base.

IMPORTANTE: Los reemplazos son quirúrgicos por patrón XML exacto
para evitar sustituir valores en sitios incorrectos del documento.
"""

import os
import re
import shutil
import zipfile
import tempfile
import datetime


PLANTILLA_PATH = os.path.join(
    os.path.dirname(__file__), "plantillas", "MTD_canarias_plantilla.docx"
)


def _generar_memoria_descriptiva(mtd: dict) -> str:
    titular     = mtd.get("titular", "")
    dni         = mtd.get("dni", "")
    direccion   = mtd.get("direccion", "")
    num_dir     = mtd.get("numero_direccion", "")
    municipio   = mtd.get("municipio", "")
    isla        = mtd.get("isla", "")
    cp          = mtd.get("cp_instalacion", "")
    superficie  = mtd.get("superficie", 0)
    electrif    = mtd.get("electrificacion", "basica")
    iga         = mtd.get("iga_A", 25)
    dif_A       = mtd.get("diferencial_A", 40)
    dif_mA      = mtd.get("diferencial_mA", 30)
    n_circ      = mtd.get("num_circuitos", 5)
    metodo      = mtd.get("metodo_instalacion", "empotrado")

    return (
        f"Vivienda unifamiliar ubicada en {direccion} {num_dir}, {municipio}. "
        f"CP {cp}. Isla de {isla}, propiedad de {titular}, DOI {dni}; "
        f"dispone de una planta con {superficie} m\u00b2 de construcci\u00f3n. "
        f"La instalaci\u00f3n corresponde a electrificaci\u00f3n de grado {electrif.upper()} "
        f"seg\u00fan ITC-BT-25. "
        f"La derivaci\u00f3n individual v\u00eda tuber\u00eda {metodo} desde el contador "
        f"ubicado en CPM sobre fachada hasta el cuadro de protecci\u00f3n y maniobras. "
        f"El cuadro dispone de IGA de {iga}A, dispositivo de protecci\u00f3n contra "
        f"sobretensiones transitorias y permanentes m\u00e1s un interruptor diferencial "
        f"{dif_mA} mA {dif_A} A que alimenta a {n_circ} circuitos interiores."
    )


def _esc(text: str) -> str:
    """Escapa caracteres XML especiales."""
    return (str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;"))


def _reemplazar_simple(xml: str, original: str, nuevo: str) -> str:
    """Reemplaza texto simple escapando el nuevo valor."""
    return xml.replace(original, _esc(nuevo))


def _reemplazar_patron(xml: str, patron: str, nuevo: str) -> str:
    """Reemplaza usando regex para mayor precisión."""
    return re.sub(patron, _esc(nuevo), xml)


def _procesar_xml(xml: str, mtd: dict) -> str:
    """Aplica todos los reemplazos al XML del documento."""

    fecha       = datetime.datetime.now()
    dia_str     = str(fecha.day)
    mes_str     = fecha.strftime("%B").lower()
    anio_str    = str(fecha.year)
    potencia_w  = int(mtd.get("potencia_prevista_kw", 5.75) * 1000)
    municipio   = mtd.get("municipio", "Las Palmas")
    circuitos   = mtd.get("circuitos", [])
    pias_str    = "-".join(str(c["pia_A"]) for c in circuitos) + "A"
    iga         = mtd.get("iga_A", 25)
    secc_di     = 16 if iga <= 40 else 25
    conductores_di = f"2x{secc_di} mm\u00b2+{secc_di}t mm\u00b2 Cu"
    memoria     = _generar_memoria_descriptiva(mtd)

    # ── Titular ──────────────────────────────────────────────
    xml = _reemplazar_simple(xml,
        "MAR\u00cdA B\u00c1RBARA GEORGIADIS MAZA",
        mtd.get("titular", "").upper())
    xml = _reemplazar_simple(xml,
        "60949506N",
        mtd.get("dni", "").upper())

    # ── Ubicación ─────────────────────────────────────────────
    xml = _reemplazar_simple(xml, "CL EL CHORRO",
        mtd.get("direccion", "").upper())
    xml = _reemplazar_simple(xml, ": 51",
        f": {mtd.get('numero_direccion', '')}")
    xml = _reemplazar_simple(xml, "BJO-IZQ",
        mtd.get("portal_planta", "---"))
    xml = _reemplazar_simple(xml, "S/C DE LA LAGUNA",
        mtd.get("municipio", "").upper())
    xml = _reemplazar_simple(xml, "TENERIFE",
        mtd.get("isla", "TENERIFE").upper())
    xml = _reemplazar_simple(xml, "611-292133",
        mtd.get("instalador_telefono", ""))
    xml = _reemplazar_simple(xml, "38320",
        mtd.get("cp_instalacion", ""))
    xml = _reemplazar_simple(xml, "138 m",
        f"{mtd.get('superficie', '')} m")
    xml = _reemplazar_simple(xml, "VIVIENDA UNIFAMILIAR",
        mtd.get("uso", "VIVIENDA UNIFAMILIAR").upper())

    # ── Potencias ─────────────────────────────────────────────
    # Reemplazar "5750" como valor de celda (evita tocar dimensiones)
    xml = _reemplazar_simple(xml, ">5750<", f">{potencia_w}<")
    xml = _reemplazar_simple(xml, ">5750 W<", f">{potencia_w} W<")
    xml = _reemplazar_simple(xml, "5750 W", f"{potencia_w} W")

    # ── IGA: reemplazar SOLO el run exacto en negrita con el valor 25 ──
    # Cadena exacta encontrada en la plantilla — aparece exactamente 1 vez
    IGA_ORIG = '<w:r><w:rPr><w:b/><w:sz w:val="18"/></w:rPr><w:t>25</w:t></w:r>'
    IGA_NEW  = f'<w:r><w:rPr><w:b/><w:sz w:val="18"/></w:rPr><w:t>{iga}</w:t></w:r>'
    xml = xml.replace(IGA_ORIG, IGA_NEW)

    # ── PIAs ──────────────────────────────────────────────────
    xml = _reemplazar_simple(xml, "10-16-20-25A", pias_str)

    # ── Conductores DI ────────────────────────────────────────
    xml = _reemplazar_simple(xml,
        "2x6 mm\u00b2+6t mm\u00b2 Cu", conductores_di)

    # ── Memoria descriptiva ───────────────────────────────────
    xml = _reemplazar_simple(xml,
        "Viviernda unifamiliar con referencia catastral 4194503CS7449S0001DA, "
        "ubicado en CALLE EL CHORRO 51 BAJO IZQUIERDA. LA CUESTA, SAN CRIST\u00d3BAL "
        "DE LA LAGUNA. CP 38320. SANTA CRUZ DE TENERIFE (Coordenadas UTM Huso 28 "
        "X=374149,49 Y=3149434,78), contrato a nombre de MAR\u00cdA B\u00c1RBARA "
        "GEORGIADIS MAZA, DNI 60949506N; dispone de una planta con 138 m\u00b2 "
        "de construcci\u00f3n.",
        memoria)

    # ── Instalador ────────────────────────────────────────────
    xml = _reemplazar_simple(xml,
        "JOS\u00c9 ALBERTO GONZ\u00c1LEZ GUZM\u00c1N",
        mtd.get("instalador_nombre", "").upper())
    xml = _reemplazar_simple(xml,
        "RI202500240", mtd.get("instalador_num", ""))
    xml = _reemplazar_simple(xml,
        "AVENIDA SAN MAT\u00cdAS",
        mtd.get("instalador_domicilio", "").upper())
    xml = _reemplazar_simple(xml,
        "22-25", mtd.get("instalador_num_domicilio", ""))
    xml = _reemplazar_simple(xml,
        "SAN CRIST\u00d3BAL DE LA LAGUNA",
        mtd.get("instalador_localidad", "").upper())
    xml = _reemplazar_simple(xml,
        "38108", mtd.get("instalador_cp", ""))
    xml = _reemplazar_simple(xml,
        "653-781971", mtd.get("instalador_telefono", ""))

    # ── Número instalación y fecha ────────────────────────────
    xml = _reemplazar_simple(xml,
        "JAGG-26-004", mtd.get("num_instalacion", ""))
    xml = _reemplazar_simple(xml,
        "JAGG-26-003", mtd.get("num_instalacion", ""))
    xml = _reemplazar_simple(xml,
        "JAGG-26-002", mtd.get("num_instalacion", ""))
    xml = _reemplazar_simple(xml,
        "En Santa Cruz de Tenerife, a 25 de febrero de 2026",
        f"En {municipio}, a {dia_str} de {mes_str} de {anio_str}")

    return xml


def generar_mtd_canarias_docx(mtd: dict, output_path: str):
    """
    Genera el MTD oficial de Canarias pre-relleno.
    mtd: dict de calcular_mtd() enriquecido con campos del instalador
    output_path: ruta .docx de salida
    """
    if not os.path.exists(PLANTILLA_PATH):
        raise FileNotFoundError(
            f"Plantilla no encontrada: {PLANTILLA_PATH}\n"
            "Copia MTD_canarias_plantilla.docx a services/plantillas/"
        )

    shutil.copy2(PLANTILLA_PATH, output_path)

    tmp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(output_path, 'r') as z:
            z.extractall(tmp_dir)

        # Procesar document.xml
        doc_path = os.path.join(tmp_dir, "word", "document.xml")
        with open(doc_path, 'r', encoding='utf-8') as f:
            xml = f.read()
        xml = _procesar_xml(xml, mtd)
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(xml)

        # Procesar headers y footers
        word_dir = os.path.join(tmp_dir, "word")
        for fname in os.listdir(word_dir):
            if fname.startswith(("header", "footer")) and fname.endswith(".xml"):
                fpath = os.path.join(word_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    hxml = f.read()
                hxml = _procesar_xml(hxml, mtd)
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(hxml)

        # Reempaquetar
        os.remove(output_path)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    fp = os.path.join(root, file)
                    z.write(fp, os.path.relpath(fp, tmp_dir))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)