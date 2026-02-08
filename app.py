import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# 1. Cargar variables de entorno
load_dotenv()

# 2. Verificación temprana (clave)
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY no encontrada en el entorno")

# 3. Inicializar app
app = Flask(__name__)
CORS(app)

# 4. Cliente OpenAI
client = OpenAI(api_key=API_KEY)

# 5. SYSTEM PROMPT REBT (núcleo de comportamiento)
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

Cierre obligatorio:
- Finaliza siempre con un consejo práctico de experto basado en experiencia de campo.
"""

# 6. Endpoint de prueba
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# 7. Endpoint principal
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    question = data.get("question")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
    )

    answer = response.choices[0].message.content
    return jsonify({"answer": answer})

# 8. Arranque
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
