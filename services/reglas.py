# services/reglas.py

# ==========================
# REGLAS TÉCNICAS FIJAS REBT
# ==========================

ITC_BT_25_RULES = {
    "C1_iluminacion": {
        "seccion_mm2": 1.5,
        "proteccion_A": 10
    },
    "C2_tomas_generales": {
        "seccion_mm2": 2.5,
        "proteccion_A": 16
    },
    "C3_cocina_banos": {
        "seccion_mm2": 2.5,
        "proteccion_A": 16
    }
}

MAX_CAIDA_TENSION_INTERIOR = 0.03  # 3%
