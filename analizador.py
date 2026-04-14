import streamlit as st
from google import genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import csv
import os
import re
from datetime import datetime
from html import escape

try:
    import pandas as pd
except Exception:
    pd = None

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="wide")

HISTORY_FILE = "recibozen_historial.csv"
CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
]

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    API_KEY = "TU_NUEVA_CLAVE_AQUI"

client = genai.Client(api_key=API_KEY)

st.markdown("""
<style>
:root {
    --bg: #f4f7f8;
    --surface: #ffffff;
    --surface-2: #f8fbfb;
    --text: #17313a;
    --muted: #5f7480;
    --line: #dbe6ea;
    --primary: #0f766e;
    --primary-2: #0b5e58;
    --soft: #dff4ef;
    --success: #1f8f5f;
    --warn: #a06a17;
    --danger: #ba3a34;
    --shadow: 0 10px 30px rgba(11, 48, 58, 0.08);
    --radius: 20px;
    --radius-sm: 14px;
}

html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top right, #eef8f5 0%, var(--bg) 38%, #f6f8fb 100%) !important;
}

body, p, div, label, li, span, small {
    color: var(--text) !important;
}

.block-container {
    max-width: 1180px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

.hero {
    background: linear-gradient(135deg, rgba(255,255,255,.95), rgba(247,252,251,.9));
    border: 1px solid rgba(15,118,110,.10);
    border-radius: 28px;
    padding: 1.35rem 1.35rem 1.1rem 1.35rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}

.hero-title {
    font-size: clamp(1.9rem, 2.8vw, 3rem);
    line-height: 1.05;
    margin: 0 0 .35rem 0;
    letter-spacing: -0.02em;
}

.hero-sub {
    color: var(--muted) !important;
    font-size: 1.02rem;
    max-width: 60ch;
}

.pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: .55rem;
    margin-top: .9rem;
}

.pill {
    background: var(--soft);
    color: var(--primary) !important;
    border: 1px solid rgba(15,118,110,.12);
    border-radius: 999px;
    padding: .45rem .8rem;
    font-size: .92rem;
    font-weight: 700;
}

.card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 1rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}

.soft-card {
    background: var(--surface-2);
    border: 1px solid #e5eff1;
    border-radius: var(--radius-sm);
    padding: .95rem;
    height: 100%;
}

.metric-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1rem;
    box-shadow: var(--shadow);
    min-height: 132px;
}

.metric-label {
    font-size: .92rem;
    color: var(--muted) !important;
    margin-bottom: .35rem;
    font-weight: 700;
}

.metric-value {
    font-size: clamp(1.55rem, 2.5vw, 2.25rem);
    line-height: 1.05;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.metric-help {
    margin-top: .45rem;
    color: var(--muted) !important;
    font-size: .95rem;
}

.state-good { color: var(--success) !important; font-weight: 800; }
.state-warn { color: var(--warn) !important; font-weight: 800; }
.state-bad  { color: var(--danger) !important; font-weight: 800; }

.section-title {
    font-size: 1.18rem;
    margin-bottom: .8rem;
    font-weight: 800;
}

.summary-box {
    background: linear-gradient(180deg, #fdfefe 0%, #f6fbfa 100%);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1rem;
    box-shadow: var(--shadow);
}

.big-text {
    font-size: 1.06rem;
    line-height: 1.7;
}

.helper-list {
    margin: 0;
    padding-left: 1.15rem;
}

.helper-list li {
    margin-bottom: .5rem;
}

.small-note {
    color: var(--muted) !important;
    font-size: .95rem;
}

.history-table-wrap {
    overflow-x: auto;
    border-radius: 16px;
    border: 1px solid var(--line);
}

.history-table {
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
}

.history-table th, .history-table td {
    text-align: left;
    padding: .82rem .8rem;
    border-bottom: 1px solid #ebf0f2;
    font-size: .95rem;
}

.history-table th {
    background: #f8fbfb;
    color: var(--muted) !important;
    font-weight: 800;
    position: sticky;
    top: 0;
}

.audio-box {
    background: #f8fbfb;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: .8rem;
}

div[data-testid="stFileUploader"] section {
    background: rgba(255,255,255,.82) !important;
    border: 2px dashed rgba(15,118,110,.3) !important;
    border-radius: 18px !important;
}

.stButton > button {
    border-radius: 14px !important;
    height: 52px !important;
    font-weight: 800 !important;
    border: none !important;
}

.stButton > button[kind="primary"] {
    background: var(--primary) !important;
    color: white !important;
}

div[data-testid="column"] .stButton > button {
    background: white !important;
    color: var(--text) !important;
    border: 1px solid var(--line) !important;
}

div[data-testid="column"] .stButton > button:hover,
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
}

.footer-note {
    text-align:center;
    color: var(--muted) !important;
    margin-top: 1rem;
    font-size: .9rem;
}

@media (max-width: 768px) {
    .hero { padding: 1rem; border-radius: 22px; }
    .metric-card { min-height: unset; }
}
</style>
""", unsafe_allow_html=True)


def init_history_file():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "periodo", "empresa", "total_eur", "consumo_kwh",
                "potencia_kw", "impuestos_eur", "consejo", "resumen", "modelo"
            ])


def read_history():
    init_history_file()
    rows = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def save_history_item(item):
    init_history_file()
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            item.get("timestamp", ""),
            item.get("periodo", ""),
            item.get("empresa", ""),
            item.get("total_eur", ""),
            item.get("consumo_kwh", ""),
            item.get("potencia_kw", ""),
            item.get("impuestos_eur", ""),
            item.get("consejo", ""),
            item.get("resumen", ""),
            item.get("modelo", ""),
        ])


def leer_pdf(file):
    reader = PdfReader(file)
    textos = []
    for page in reader.pages:
        textos.append(page.extract_text() or "")
    return "\n".join(textos).strip()


def preparar_audio(texto):
    tts = gTTS(text=texto, lang="es", slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()


def extraer_texto_respuesta(response):
    texto = getattr(response, "text", None)
    if texto:
        return texto.strip()
    try:
        candidates = getattr(response, "candidates", []) or []
        trozos = []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    trozos.append(part_text)
        return "\n".join(trozos).strip()
    except Exception:
        return ""


def modelo_soporta_generate_content(model_obj):
    actions = getattr(model_obj, "supported_actions", None)
    if actions and "generateContent" in actions:
        return True
    old_actions = getattr(model_obj, "supported_generation_methods", None)
    if old_actions and "generateContent" in old_actions:
        return True
    return False


def listar_modelos_validos():
    validos = []
    try:
        for m in client.models.list():
            if modelo_soporta_generate_content(m):
                nombre = getattr(m, "name", "") or ""
                if nombre.startswith("models/"):
                    nombre = nombre.replace("models/", "", 1)
                if nombre:
                    validos.append(nombre)
    except Exception:
        pass
    return validos


def probar_modelo(model_name):
    respuesta = client.models.generate_content(
        model=model_name,
        contents="Responde solo OK"
    )
    return extraer_texto_respuesta(respuesta)


def resolver_modelo():
    errores = []
    for model_name in CANDIDATE_MODELS:
        try:
            _ = probar_modelo(model_name)
            return model_name, errores
        except Exception as e:
            errores.append(f"{model_name}: {e}")

    detectados = listar_modelos_validos()
    prioridad = []
    resto = []
    for m in detectados:
        if "flash" in m:
            prioridad.append(m)
        else:
            resto.append(m)

    for model_name in prioridad + resto:
        if model_name in CANDIDATE_MODELS:
            continue
        try:
            _ = probar_modelo(model_name)
            return model_name, errores
        except Exception as e:
            errores.append(f"{model_name}: {e}")

    raise RuntimeError("No se encontró un modelo compatible con generateContent para esta API key.")


def obtener_modelo_activo():
    if "modelo_activo" not in st.session_state:
        model_name, errores = resolver_modelo()
        st.session_state["modelo_activo"] = model_name
        st.session_state["errores_modelos"] = errores
    return st.session_state["modelo_activo"]


def limpiar_numero(texto):
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    t = t.replace("€", "").replace("EUR", "").replace("eur", "")
    t = t.replace("kWh", "").replace("kw", "").replace("kW", "")
    t = t.replace(" ", "")
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    m = r
