# services/calculos.py

from services.reglas import MAX_CAIDA_TENSION_INTERIOR

def calcular_caida_tension_monofasica(I, L, S, V=230, resistividad=0.0175):
    """
    I = corriente en amperios
    L = longitud en metros (solo ida)
    S = sección en mm2
    """

    delta_v = (2 * L * I * resistividad) / S
    porcentaje = delta_v / V

    return {
        "delta_v_voltios": round(delta_v, 2),
        "porcentaje": round(porcentaje * 100, 2),
        "cumple": porcentaje <= MAX_CAIDA_TENSION_INTERIOR
    }

import re

def extraer_parametros_caida(texto):
    """
    Extrae corriente (A), longitud (m) y sección (mm2) del texto.
    """

    texto = texto.lower()

    corriente = None
    longitud = None
    seccion = None

    # Corriente
    match_i = re.search(r'(\d+)\s*a', texto)
    if match_i:
        corriente = float(match_i.group(1))

    # Longitud
    match_l = re.search(r'(\d+)\s*m', texto)
    if match_l:
        longitud = float(match_l.group(1))

    # Sección mm2
    match_s = re.search(r'(\d+(?:\.\d+)?)\s*mm2', texto)
    if match_s:
        seccion = float(match_s.group(1))

    return corriente, longitud, seccion
