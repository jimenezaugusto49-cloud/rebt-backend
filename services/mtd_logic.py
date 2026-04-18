"""
mtd_logic.py
Cerebro de la MTD — toda la lógica automática según REBT / ITC-BT-25
No usa IA. Cálculos deterministas a partir de los datos mínimos del usuario.
"""

# ─────────────────────────────────────────────────────────────
# TABLAS FIJAS ITC-BT-25
# ─────────────────────────────────────────────────────────────

CIRCUITOS_BASICA = [
    {"codigo": "C1", "nombre": "Iluminación",              "pia_A": 10, "seccion_mm2": 1.5},
    {"codigo": "C2", "nombre": "Tomas de uso general",     "pia_A": 16, "seccion_mm2": 2.5},
    {"codigo": "C3", "nombre": "Cocina y horno",           "pia_A": 25, "seccion_mm2": 6.0},
    {"codigo": "C4", "nombre": "Lavadora/lavavajillas/termo","pia_A": 20, "seccion_mm2": 4.0},
    {"codigo": "C5", "nombre": "Baño y auxiliar cocina",   "pia_A": 16, "seccion_mm2": 2.5},
]

CIRCUITOS_ELEVADA_EXTRA = [
    {"codigo": "C6", "nombre": "Tomas adicionales uso general","pia_A": 16, "seccion_mm2": 2.5},
    {"codigo": "C7", "nombre": "Tomas adicionales",            "pia_A": 16, "seccion_mm2": 2.5},
    {"codigo": "C8", "nombre": "Calefacción eléctrica",        "pia_A": 25, "seccion_mm2": 6.0},
    {"codigo": "C9", "nombre": "Aire acondicionado",           "pia_A": 25, "seccion_mm2": 6.0},
    {"codigo": "C10","nombre": "Secadora",                     "pia_A": 16, "seccion_mm2": 2.5},
]

# IGA según potencia prevista (A)
IGA_TABLA = [
    (5750,  25),
    (9200,  40),
    (14000, 63),
    (20000, 80),
]

# ─────────────────────────────────────────────────────────────
# FUNCIONES PRINCIPALES
# ─────────────────────────────────────────────────────────────

def determinar_electrificacion(superficie: float, cocina: bool, clima: bool, calefaccion: bool) -> str:
    """
    ITC-BT-25: Electrificación elevada si superficie > 160 m²
    o si tiene cocina eléctrica, aire acondicionado o calefacción eléctrica.
    """
    if superficie > 160 or cocina or clima or calefaccion:
        return "elevada"
    return "basica"


def calcular_potencia_prevista(electrificacion: str) -> float:
    """
    ITC-BT-10: Potencia mínima por grado de electrificación (W).
    """
    return 9200.0 if electrificacion == "elevada" else 5750.0


def seleccionar_iga(potencia_w: float) -> int:
    """
    Selecciona el IGA (A) según la potencia prevista.
    """
    for limite, iga in IGA_TABLA:
        if potencia_w <= limite:
            return iga
    return 100  # Instalaciones mayores


def generar_circuitos(electrificacion: str, cocina: bool, clima: bool, calefaccion: bool) -> list:
    """
    Genera la lista de circuitos según ITC-BT-25.
    Parte siempre de los 5 circuitos básicos y añade los
    circuitos de electrificación elevada según equipamiento.
    """
    circuitos = list(CIRCUITOS_BASICA)  # Siempre los 5 básicos

    if electrificacion == "elevada":
        # C6 y C7 siempre en elevada
        circuitos.append(CIRCUITOS_ELEVADA_EXTRA[0])  # C6
        circuitos.append(CIRCUITOS_ELEVADA_EXTRA[1])  # C7

        if calefaccion:
            circuitos.append(CIRCUITOS_ELEVADA_EXTRA[2])  # C8
        if clima:
            circuitos.append(CIRCUITOS_ELEVADA_EXTRA[3])  # C9

    # C3 ya cubre cocina eléctrica en básica y elevada
    # Si no hay cocina eléctrica, C3 se mantiene pero se anota
    if not cocina:
        for c in circuitos:
            if c["codigo"] == "C3":
                c = dict(c)
                c["nombre"] = "Cocina/horno (previsto)"

    return circuitos


def calcular_mtd(datos: dict) -> dict:
    """
    Función principal. Recibe los datos mínimos del usuario
    y devuelve el resultado completo de la MTD.

    datos esperados:
    {
        "titular": str,
        "dni": str,
        "direccion": str,
        "municipio": str,
        "provincia": str,
        "referencia_catastral": str (opcional),
        "superficie": float,
        "habitaciones": int,
        "banos": int,
        "cocina_electrica": bool,
        "aire_acondicionado": bool,
        "calefaccion_electrica": bool,
        "tipo_instalacion": str,  # "nueva" | "reforma" | "ampliacion"
        "metodo_instalacion": str,  # "empotrado" | "superficie"
        "toma_tierra": bool,
        "instalador_nombre": str,
        "instalador_nie": str,
        "instalador_num": str,
    }
    """
    superficie      = float(datos.get("superficie", 0))
    cocina          = bool(datos.get("cocina_electrica", False))
    clima           = bool(datos.get("aire_acondicionado", False))
    calefaccion     = bool(datos.get("calefaccion_electrica", False))
    habitaciones    = int(datos.get("habitaciones", 0))
    banos           = int(datos.get("banos", 0))
    tipo_inst       = datos.get("tipo_instalacion", "nueva")
    metodo          = datos.get("metodo_instalacion", "empotrado")
    toma_tierra     = bool(datos.get("toma_tierra", True))

    # Cálculos automáticos
    electrificacion = determinar_electrificacion(superficie, cocina, clima, calefaccion)
    potencia_w      = calcular_potencia_prevista(electrificacion)
    potencia_kw     = potencia_w / 1000
    iga_A           = seleccionar_iga(potencia_w)
    circuitos       = generar_circuitos(electrificacion, cocina, clima, calefaccion)

    # Diferencial siempre 30mA, calibre según IGA
    diferencial_A   = max(40, iga_A)

    return {
        # Datos del titular
        "titular":               datos.get("titular", ""),
        "dni":                   datos.get("dni", ""),
        "direccion":             datos.get("direccion", ""),
        "municipio":             datos.get("municipio", ""),
        "provincia":             datos.get("provincia", ""),
        "referencia_catastral":  datos.get("referencia_catastral", ""),

        # Características de la vivienda
        "superficie":            superficie,
        "habitaciones":          habitaciones,
        "banos":                 banos,
        "cocina_electrica":      cocina,
        "aire_acondicionado":    clima,
        "calefaccion_electrica": calefaccion,
        "tipo_instalacion":      tipo_inst,
        "metodo_instalacion":    metodo,
        "toma_tierra":           toma_tierra,

        # Resultados automáticos
        "electrificacion":       electrificacion,
        "potencia_prevista_kw":  potencia_kw,
        "tension":               "230 V monofásica",
        "iga_A":                 iga_A,
        "diferencial_A":         diferencial_A,
        "diferencial_mA":        30,
        "circuitos":             circuitos,
        "num_circuitos":         len(circuitos),

        # Isla (Canarias)
        "isla":                  datos.get("isla", ""),

        # Datos del instalador
        "instalador_nombre":     datos.get("instalador_nombre", ""),
        "instalador_nie":        datos.get("instalador_nie", ""),
        "instalador_num":        datos.get("instalador_num", ""),
        "instalador_domicilio":  datos.get("instalador_domicilio", ""),
        "instalador_localidad":  datos.get("instalador_localidad", ""),
        "instalador_cp":         datos.get("instalador_cp", ""),
        "instalador_telefono":   datos.get("instalador_telefono", ""),
    }

