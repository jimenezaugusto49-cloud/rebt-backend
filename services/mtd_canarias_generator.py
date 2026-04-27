"""
mtd_canarias_generator.py
Genera el MTD oficial de Canarias pre-relleno en .docx
usando docxtpl con placeholders {{ }} en la plantilla.
"""

import os
import datetime
from docxtpl import DocxTemplate


PLANTILLA_PATH = os.path.join(
    os.path.dirname(__file__), "plantillas", "MTD_canarias_plantilla.docx"
)


def _generar_memoria_descriptiva(mtd: dict) -> str:
    titular    = mtd.get("titular", "")
    dni        = mtd.get("dni", "")
    direccion  = mtd.get("direccion", "")
    num_dir    = mtd.get("numero_direccion", "")
    portal     = mtd.get("portal_planta", "")
    municipio  = mtd.get("municipio", "")
    isla       = mtd.get("isla", "")
    cp         = mtd.get("cp_instalacion", "")
    superficie = mtd.get("superficie", 0)
    electrif   = mtd.get("electrificacion", "basica")
    iga        = mtd.get("iga_A", 25)
    dif_A      = mtd.get("diferencial_A", 40)
    dif_mA     = mtd.get("diferencial_mA", 30)
    n_circ     = mtd.get("num_circuitos", 5)
    metodo     = mtd.get("metodo_instalacion", "empotrado")

    ubicacion = f"{direccion} {num_dir}".strip()
    if portal:
        ubicacion += f", {portal}"

    return (
        f"Vivienda unifamiliar ubicada en {ubicacion}, {municipio}. "
        f"CP {cp}. Isla de {isla}, propiedad de {titular}, DOI {dni}; "
        f"dispone de una planta con {superficie} m\u00b2 de construcci\u00f3n. "
        f"La instalaci\u00f3n corresponde a electrificaci\u00f3n de grado {electrif.upper()} "
        f"seg\u00fan ITC-BT-25. "
        f"La derivaci\u00f3n individual v\u00eda tuber\u00eda {metodo} desde el contador "
        f"ubicado en CPM sobre fachada hasta el cuadro de protecci\u00f3n y maniobras. "
        f"El cuadro dispone de IGA de {iga} A, dispositivo de protecci\u00f3n contra "
        f"sobretensiones transitorias y permanentes m\u00e1s un interruptor diferencial "
        f"de {dif_mA} mA / {dif_A} A que alimenta a {n_circ} circuitos interiores."
    )


def _preparar_circuitos(circuitos: list, iga: int) -> list:
    """
    Enriquece cada circuito con campos extra para la tabla de la plantilla.
    """
    TUBOS = {1.5: 16, 2.5: 20, 4.0: 20, 6.0: 25}
    resultado = []

    for c in circuitos:
        seccion = c.get("seccion_mm2", 2.5)
        pia     = c.get("pia_A", 16)
        tubo    = TUBOS.get(seccion, 20)

        # Sección del neutro y tierra igual a la fase para BT residencial
        conductores = f"2x{seccion} mm\u00b2 + {seccion} mm\u00b2 T"

        resultado.append({
            "nombre":        c.get("codigo", ""),
            "uso":           c.get("nombre", ""),
            "pia_A":         pia,
            "seccion_mm2":   seccion,
            "conductores":   conductores,
            "tubo_mm":       tubo,
            "magnetotermico": f"IA-{pia}A",
            "longitud_m":    "",   # Opcional — el instalador puede rellenar en Word
            "potencia_w":    "",   # Opcional — calculable si se amplía lógica
        })

    return resultado


def generar_mtd_canarias_docx(mtd: dict, output_path: str):
    """
    Genera el MTD oficial de Canarias pre-relleno.
    mtd: dict de calcular_mtd() enriquecido con campos del instalador.
    output_path: ruta .docx de salida.
    """
    if not os.path.exists(PLANTILLA_PATH):
        raise FileNotFoundError(
            f"Plantilla no encontrada: {PLANTILLA_PATH}\n"
            "Copia MTD_canarias_plantilla.docx a services/plantillas/"
        )

    # ── Fecha ────────────────────────────────────────────────
    fecha      = datetime.datetime.now()
    meses_es   = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    fecha_dia  = str(fecha.day)
    fecha_mes  = meses_es[fecha.month]
    fecha_anio = str(fecha.year)
    municipio  = mtd.get("municipio", "")
    fecha_completa = f"En {municipio}, a {fecha_dia} de {fecha_mes} de {fecha_anio}"

    # ── Potencia ─────────────────────────────────────────────
    potencia_kw = mtd.get("potencia_prevista_kw", 5.75)
    potencia_w  = int(potencia_kw * 1000)

    # ── IGA y conductores DI ─────────────────────────────────
    iga        = mtd.get("iga_A", 25)
    secc_di    = 16 if iga <= 40 else 25
    conductores_di = f"2x{secc_di} mm\u00b2 + {secc_di} mm\u00b2 T Cu"

    # ── Circuitos ────────────────────────────────────────────
    circuitos_raw = mtd.get("circuitos", [])
    circuitos     = _preparar_circuitos(circuitos_raw, iga)
    pias_str      = "-".join(str(c["pia_A"]) for c in circuitos) + " A"

    # ── Memoria descriptiva ──────────────────────────────────
    memoria = _generar_memoria_descriptiva(mtd)

    # ── Tipo/método instalación legibles ─────────────────────
    tipo_map   = {"nueva": "Nueva instalación", "reforma": "Reforma", "ampliacion": "Ampliación"}
    metodo_map = {"empotrado": "Empotrado (tubo corrugado)", "superficie": "En superficie (tubo rígido)"}

    # ── Contexto completo para docxtpl ───────────────────────
    context = {
        # Titular / vivienda
        "titular":              mtd.get("titular", "").upper(),
        "dni":                  mtd.get("dni", "").upper(),
        "direccion":            mtd.get("direccion", "").upper(),
        "numero_direccion":     mtd.get("numero_direccion", ""),
        "portal_planta":        mtd.get("portal_planta", "---"),
        "municipio":            mtd.get("municipio", "").upper(),
        "provincia":            mtd.get("provincia", "").upper(),
        "isla":                 mtd.get("isla", "").upper(),
        "cp_instalacion":       mtd.get("cp_instalacion", ""),
        "referencia_catastral": mtd.get("referencia_catastral", "---"),
        "superficie":           superficie_str(potencia_kw, mtd),
        "num_instalacion":      mtd.get("num_instalacion", ""),
        "uso":                  "VIVIENDA UNIFAMILIAR",

        # Tipo e instalación
        "tipo_instalacion":     tipo_map.get(mtd.get("tipo_instalacion", "nueva"), "Nueva instalación"),
        "metodo_instalacion":   metodo_map.get(mtd.get("metodo_instalacion", "empotrado"), "Empotrado"),
        "toma_tierra":          "Sí" if mtd.get("toma_tierra", True) else "No",

        # Resultados automáticos
        "electrificacion":      mtd.get("electrificacion", "basica").upper(),
        "potencia_prevista_kw": f"{potencia_kw:.2f}",
        "potencia_prevista_w":  str(potencia_w),
        "tension":              "230 V monofásica",
        "iga_A":                str(iga),
        "diferencial_A":        str(mtd.get("diferencial_A", 40)),
        "diferencial_mA":       str(mtd.get("diferencial_mA", 30)),
        "conductores_di":       conductores_di,
        "num_circuitos":        str(mtd.get("num_circuitos", 5)),
        "pias_str":             pias_str,
        "memoria_descriptiva":  memoria,

        # Tabla de circuitos (bucle {% for %})
        "circuitos":            circuitos,

        # Instalador
        "instalador_nombre":    mtd.get("instalador_nombre", "").upper(),
        "instalador_nie":       mtd.get("instalador_nie", "").upper(),
        "instalador_num":       mtd.get("instalador_num", ""),
        "instalador_domicilio": mtd.get("instalador_domicilio", "").upper(),
        "instalador_num_domicilio": mtd.get("instalador_num_domicilio", ""),
        "instalador_localidad": mtd.get("instalador_localidad", "").upper(),
        "instalador_cp":        mtd.get("instalador_cp", ""),
        "instalador_telefono":  mtd.get("instalador_telefono", ""),

        # Fecha
        "fecha_dia":            fecha_dia,
        "fecha_mes":            fecha_mes,
        "fecha_anio":           fecha_anio,
        "fecha_completa":       fecha_completa,
        "lugar_fecha":          fecha_completa,

        # Flags equipamiento (para secciones condicionales {% if %})
        "cocina_electrica":     mtd.get("cocina_electrica", False),
        "aire_acondicionado":   mtd.get("aire_acondicionado", False),
        "calefaccion_electrica":mtd.get("calefaccion_electrica", False),
    }

    # ── Renderizar y guardar ──────────────────────────────────
    doc = DocxTemplate(PLANTILLA_PATH)
    doc.render(context)
    doc.save(output_path)


def superficie_str(potencia_kw, mtd):
    """Devuelve la superficie como string con unidades."""
    sup = mtd.get("superficie", 0)
    return f"{sup} m\u00b2"
