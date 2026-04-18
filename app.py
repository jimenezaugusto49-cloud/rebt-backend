from dotenv import load_dotenv
load_dotenv()

import os
import json
import tempfile
from services.mtd_canarias_generator import generar_mtd_canarias_docx
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from services.calculos import (
    calcular_caida_tension_monofasica,
    extraer_parametros_caida
)
from services.pdf_generator import generar_pdf_informe
from services.mtd_logic import calcular_mtd
from services.mtd_pdf_generator import generar_pdf_mtd

# ─────────────────────────────────────────
# 1. Verificación temprana de API KEY
# ─────────────────────────────────────────
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY no encontrada en el entorno")

# ─────────────────────────────────────────
# 2. Inicializar app Flask
# ─────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── NUEVO ──────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200
# ───────────────────────────────────

# ─────────────────────────────────────────
# 3. Cliente OpenAI (una sola vez)
# ─────────────────────────────────────────
client = OpenAI(api_key=API_KEY)

# ─────────────────────────────────────────
# 4. SYSTEM PROMPT PRINCIPAL (fuente de verdad técnica)
# ─────────────────────────────────────────
SYSTEM_PROMPT = """
Eres REBT Experto, una aplicación técnica profesional de apoyo a electricistas en España.

Tu asesoramiento se rige exclusivamente por:
- Reglamento Electrotécnico para Baja Tensión (REBT)
- ITC-BT vigentes
- Buenas prácticas profesionales en instalaciones eléctricas reales

Estilo y normas de respuesta:
- Responde como una herramienta profesional, no como un asistente conversacional genérico.
- Prioriza respuestas claras, directas y aplicables a pie de obra.
- Da siempre primero la conclusión técnica (sección, calibre, valor final).
- Evita desarrollos teóricos largos, fórmulas extensas o explicaciones académicas salvo que el usuario lo pida explícitamente.
- Usa lenguaje profesional de electricista, no de profesor.
- No expliques procesos internos ni razonamientos paso a paso.
- No uses Markdown complejo ni símbolos matemáticos innecesarios.

Criterio técnico:
- Si faltan datos, asume condiciones habituales según REBT (vivienda, cobre, 230 V, método de instalación común) e indícalo brevemente.
- Cuando exista una sección mínima admisible y otra más recomendable por criterio profesional, indica ambas.
- La recomendación principal debe ser siempre la que evite problemas futuros de caída de tensión, calentamiento o ampliaciones, sin sobredimensionar innecesariamente.
- Explica en una sola frase por qué la opción recomendada es preferible frente a la mínima admisible.
- Cita la ITC-BT aplicable solo cuando aporte valor práctico.
- No inventes normativa ni referencias.
- No incluyas advertencias legales innecesarias.

Reglas de coherencia obligatorias:
- Si el usuario hace referencia a un cálculo o caso anterior, reutiliza exactamente los mismos parámetros salvo que el usuario los modifique.
- No introduzcas nuevas secciones, intensidades o supuestos que no hayan sido mencionados previamente.
- Si faltan datos para un cálculo, solicita los datos faltantes antes de responder.
- No generalices cuando se solicita un cálculo específico.
- No cambies valores entre respuestas consecutivas sin justificarlo.

Cierre obligatorio:
- Finaliza siempre con un consejo práctico de experto basado en experiencia de campo.
"""

# ─────────────────────────────────────────
# 5. PROMPT DE FORMATO PARA PDF
#    Su único trabajo es estructurar en JSON
#    la respuesta técnica que ya dio /ask.
#    NO recalcula ni reinterpreta nada.
# ─────────────────────────────────────────
REPORT_FORMAT_PROMPT = """
Eres un formateador de informes técnicos eléctricos.

Recibirás:
- La consulta original del usuario.
- La respuesta técnica ya validada que se le dio al usuario.

Tu única tarea es estructurar esa información en el siguiente JSON.
No cambies ningún valor técnico. No recalcules nada. No añadas datos nuevos.
Si un campo no tiene información en la respuesta recibida, déjalo vacío ("").

Devuelve EXCLUSIVAMENTE JSON válido, sin texto adicional, sin markdown, sin comentarios.

{
  "titulo": "Informe Técnico de Consulta REBT",
  "fecha": "",
  "tipo_calculo": "",
  "parametros": {},
  "resultado": {},
  "normativa": {},
  "observaciones": "",
  "aviso_legal": "Este informe tiene carácter orientativo y no sustituye la supervisión de un técnico competente ni la normativa vigente."
}
"""

# ─────────────────────────────────────────
# 6. Endpoint principal — fuente de verdad
# ─────────────────────────────────────────
@app.route("/ask", methods=["POST"])
def ask():
    try:
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "Empty body"}), 400

        data = json.loads(raw)
        question = (data.get("question") or "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # ── CAPA DE CÁLCULO DIRECTO ──────────────────────────────
        # Detecta caída de tensión con parámetros completos y
        # responde con cálculo exacto. Si faltan parámetros,
        # deja que la IA pida los datos que faltan.
        if "caída de tensión" in question.lower():
            I, L, S = extraer_parametros_caida(question)

            if I and L and S:
                resultado = calcular_caida_tension_monofasica(I, L, S)
                answer = (
                    f"Caída de tensión: {resultado['delta_v_voltios']} V "
                    f"({resultado['porcentaje']}%). "
                    f"{'Cumple límite 3% en interior.' if resultado['cumple'] else 'No cumple límite 3% en interior.'}"
                )
                return jsonify({"answer": answer})

            # Sin parámetros completos → la IA solicita los datos
            # (no se interrumpe el flujo, cae al bloque de IA abajo)

        # ── CAPA IA CON MEMORIA ──────────────────────────────────
        history = data.get("history", [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in history:
            if msg.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )

        answer = response.choices[0].message.content
        return jsonify({"answer": answer})

    except Exception as e:
        print("ERROR /ask:", e)
        return jsonify({"error": "Error del sistema"}), 500


# ─────────────────────────────────────────
# 7. Endpoint PDF — derivado de /ask
#    Recibe la pregunta Y la respuesta ya
#    generada por /ask. Solo formatea el PDF.
# ─────────────────────────────────────────
@app.route("/generate-report-pdf", methods=["POST"])
def generate_report_pdf():
    tmp_path = None
    try:
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "Empty body"}), 400

        data = json.loads(raw)
        consulta         = (data.get("consulta") or "").strip()
        respuesta_previa = (data.get("respuesta_previa") or "").strip()

        if not consulta:
            return jsonify({"error": "No consulta provided"}), 400
        if not respuesta_previa:
            return jsonify({"error": "No respuesta_previa provided. El PDF debe generarse a partir de una respuesta ya validada por /ask."}), 400

        # El prompt solo formatea; no recalcula nada
        user_content = (
            f"Consulta del usuario:\n{consulta}\n\n"
            f"Respuesta técnica ya validada:\n{respuesta_previa}\n\n"
            f"Estructura esta información en el JSON del informe. No cambies ningún valor técnico."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": REPORT_FORMAT_PROMPT},
                {"role": "user",   "content": user_content}
            ],
            temperature=0.0  # Máxima fidelidad; no queremos variación aquí
        )

        report_content = response.choices[0].message.content
        parsed_json = json.loads(report_content)

        # Generar PDF en archivo temporal y limpiar tras enviarlo
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()

        generar_pdf_informe(parsed_json, tmp_path)

        response_file = send_file(
            tmp_path,
            as_attachment=True,
            download_name="informe_tecnico_REBT.pdf",
            mimetype="application/pdf"
        )
        return response_file

    except json.JSONDecodeError as e:
        print("ERROR JSON al parsear respuesta del modelo:", e)
        return jsonify({"error": "El modelo no devolvió JSON válido para el informe"}), 500

    except Exception as e:
        print("ERROR /generate-report-pdf:", e)
        return jsonify({"error": "Error generando PDF"}), 500

    finally:
        # Limpieza del archivo temporal siempre, incluso si hay error
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ─────────────────────────────────────────
# 8. Arranque local (Render ignora esto)
# ─────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# AÑADIR en los imports de app.py (junto a los otros imports):
# ─────────────────────────────────────────────────────────────
#
# from services.mtd_logic import calcular_mtd
# from services.mtd_pdf_generator import generar_pdf_mtd
#
# ─────────────────────────────────────────────────────────────
# AÑADIR este endpoint al final de app.py, antes del bloque
# if __name__ == "__main__":
# ─────────────────────────────────────────────────────────────

@app.route("/generate-mtd", methods=["POST"])
def generate_mtd():
    tmp_path = None
    try:
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "Empty body"}), 400

        datos = json.loads(raw)

        # Validación mínima de campos obligatorios
        campos_obligatorios = [
            "titular", "dni", "direccion", "municipio", "provincia",
            "superficie", "habitaciones", "banos",
            "instalador_nombre", "instalador_nie", "instalador_num"
        ]
        faltantes = [c for c in campos_obligatorios if not datos.get(c)]
        if faltantes:
            return jsonify({
                "error": f"Faltan campos obligatorios: {', '.join(faltantes)}"
            }), 400

        # Cálculo automático completo
        mtd = calcular_mtd(datos)

        # Generación del PDF
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()

        generar_pdf_mtd(mtd, tmp_path)

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name="MTD_instalacion_electrica.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("ERROR /generate-mtd:", e)
        return jsonify({"error": "Error generando la MTD"}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

# ─────────────────────────────────────────────────────────────
# AÑADIR en los imports de app.py:
# from services.mtd_canarias_generator import generar_mtd_canarias_docx
#
# AÑADIR este endpoint antes del bloque if __name__ == "__main__":
# ─────────────────────────────────────────────────────────────

@app.route("/generate-mtd-canarias", methods=["POST"])
def generate_mtd_canarias():
    tmp_path = None
    try:
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "Empty body"}), 400

        datos = json.loads(raw)

        # Validación mínima
        campos_obligatorios = [
            "titular", "dni", "direccion", "municipio",
            "superficie", "instalador_nombre", "instalador_num",
            "instalador_domicilio", "instalador_localidad",
            "instalador_cp", "instalador_telefono"
        ]
        faltantes = [c for c in campos_obligatorios if not datos.get(c)]
        if faltantes:
            return jsonify({
                "error": f"Faltan campos: {', '.join(faltantes)}"
            }), 400

        # Cálculo automático completo
        from services.mtd_logic import calcular_mtd
        mtd = calcular_mtd(datos)

        # Añadir campos extra que necesita el generador
        mtd["numero_direccion"]    = datos.get("numero_direccion", "")
        mtd["portal_planta"]       = datos.get("portal_planta", "---")
        mtd["cp_instalacion"]      = datos.get("cp_instalacion",
                                        datos.get("instalador_cp", ""))
        mtd["uso"]                 = datos.get("uso", "VIVIENDA UNIFAMILIAR")
        mtd["num_instalacion"]     = datos.get("num_instalacion", "")
        mtd["instalador_domicilio"]    = datos.get("instalador_domicilio", "")
        mtd["instalador_num_domicilio"]= datos.get("instalador_num_domicilio", "")
        mtd["instalador_localidad"]    = datos.get("instalador_localidad", "")
        mtd["instalador_cp"]           = datos.get("instalador_cp", "")
        mtd["instalador_telefono"]     = datos.get("instalador_telefono", "")

        # Generar docx
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_path = tmp.name
        tmp.close()

        from services.mtd_canarias_generator import generar_mtd_canarias_docx
        generar_mtd_canarias_docx(mtd, tmp_path)

        titular_safe = mtd["titular"].replace(" ", "_")[:20]
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f"MTD_Canarias_{titular_safe}.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except FileNotFoundError as e:
        print("ERROR plantilla:", e)
        return jsonify({"error": "Plantilla no encontrada en el servidor"}), 500

    except Exception as e:
        print("ERROR /generate-mtd-canarias:", e)
        return jsonify({"error": "Error generando MTD Canarias"}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)