import streamlit as st
from google import genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CONFIGURACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    API_KEY = "TU_NUEVA_CLAVE_AQUI"

# Modelos candidatos en orden de preferencia
CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
]

# Inicializar cliente
client = genai.Client(api_key=API_KEY)

# --- CSS ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label, small, span { color: #2c3e50 !important; }

    .report-card {
        background-color: white !important;
        padding: 30px;
        border-radius: 20px;
        border-top: 10px solid #27ae60 !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px;
        line-height: 1.6;
    }

    .stButton > button {
        width: 100% !important;
        height: 65px !important;
        border-radius: 15px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        color: white !important;
        border: none !important;
    }

    div[data-testid="column"]:nth-of-type(1) button { background-color: #3498db !important; }
    div[data-testid="column"]:nth-of-type(2) button { background-color: #e67e22 !important; }
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }

    [data-testid="stFileUploader"] section {
        background-color: white !important;
        border: 2px dashed #27ae60 !important;
    }

    .mini-box {
        background: white;
        border-radius: 14px;
        padding: 14px 16px;
        border: 1px solid #d9e2ec;
        margin-bottom: 12px;
    }

    .ok { color: #1e8449 !important; font-weight: 700; }
    .warn { color: #b9770e !important; font-weight: 700; }
    .err { color: #c0392b !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)


def leer_pdf(file):
    reader = PdfReader(file)
    textos = []
    for page in reader.pages:
        textos.append(page.extract_text() or "")
    return "".join(textos).strip()


def preparar_audio(texto):
    tts = gTTS(text=texto, lang="es", slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()


def extraer_texto_respuesta(response):
    texto = getattr(response, "text", None)
    if texto:
        return texto.strip()

    # Fallback por si cambia la forma de respuesta
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
    texto = extraer_texto_respuesta(respuesta)
    return texto


def reso
