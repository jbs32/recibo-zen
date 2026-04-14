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


def resolver_modelo():
    # 1) Probar candidatos conocidos
    errores = []
    for model_name in CANDIDATE_MODELS:
        try:
            _ = probar_modelo(model_name)
            return model_name, errores
        except Exception as e:
            errores.append(f"{model_name}: {e}")

    # 2) Descubrir modelos desde la API
    detectados = listar_modelos_validos()

    # Priorizar flash
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

    raise RuntimeError(
        "No se encontró ningún modelo compatible con generateContent para esta API key.\n\n"
        + "\n".join(errores[:8])
    )


def obtener_modelo_activo():
    if "modelo_activo" not in st.session_state:
        model_name, errores = resolver_modelo()
        st.session_state["modelo_activo"] = model_name
        st.session_state["errores_modelos"] = errores
    return st.session_state["modelo_activo"]


def generar_analisis_factura(texto_raw, model_name):
    prompt = f"""
Eres ReciboZen. Analiza esta factura eléctrica y responde en español claro.

Devuelve DOS PARTES separadas exactamente por:
---

PRIMERA PARTE:
Un informe útil y agradable de leer con:
- Total (€)
- Consumo (kWh)
- Potencia (kW)
- Impuestos
- Consejo práctico para ahorrar o entender mejor la factura

SEGUNDA PARTE:
Un guion de voz alegre, rápido y cercano, de máximo 70 palabras,
que empiece exactamente por:
¡Hola, hola!

Factura:
{texto_raw[:3500]}
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    texto = extraer_texto_respuesta(response)
    if not texto:
        raise RuntimeError("La API respondió sin texto legible.")

    partes = texto.split("---", 1)
    analisis = partes[0].strip()
    guion = partes[1].strip() if len(partes) > 1 else analisis[:300]

    return analisis, guion


# --- UI ---
st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con cariño y claridad")

with st.expander("Diagnóstico del motor IA", expanded=False):
    try:
        modelo = obtener_modelo_activo()
        st.markdown(f"<div class='mini-box'><span class='ok'>Modelo activo:</span> {modelo}</div>", unsafe_allow_html=True)

        errores_previos = st.session_state.get("errores_modelos", [])
        if errores_previos:
            st.markdown("<div class='mini-box'><span class='warn'>Modelos descartados:</span><br>" +
                        "<br>".join(errores_previos[:5]) + "</div>", unsafe_allow_html=True)

        modelos_detectados = listar_modelos_validos()
        if modelos_detectados:
            vista = ", ".join(modelos_detectados[:12])
            st.markdown(f"<div class='mini-box'><span class='ok'>Modelos detectados:</span> {vista}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='mini-box'><span class='warn'>No se pudieron listar modelos.</span></div>", unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"<div class='mini-box'><span class='err'>Diagnóstico:</span> {e}</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")

if uploaded_file:
    if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
        with st.spinner("ReciboZen está analizando tu factura..."):
            try:
                if API_KEY == "TU_NUEVA_CLAVE_AQUI":
                    raise RuntimeError("Falta configurar GOOGLE_API_KEY en Streamlit Secrets.")

                texto_raw = leer_pdf(uploaded_file)
                if not texto_raw:
                    raise RuntimeError("No se pudo extraer texto del PDF.")

                model_name = obtener_modelo_activo()
                analisis, guion = generar_analisis_factura(texto_raw, model_name)

                st.session_state["analisis"] = analisis
                st.session_state["audio_b64"] = preparar_audio(guion)
                st.session_state["reproducir"] = False
                st.session_state["guion_audio"] = guion

            except Exception as e:
                st.error(f"Error con ReciboZen: {e}")

if "analisis" in st.session_state:
    st.markdown(
        f"<div class='report-card'><h3>📋 Informe Zen</h3>{st.session_state['analisis']}</div>",
        unsafe_allow_html=True
    )

    with st.expander("Ver guion del audio", expanded=False):
        st.write(st.session_state.get("guion_audio", ""))

    st.write("### 🔊 Versión animada")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("▶️ INICIAR AUDIO", use_container_width=True):
            st.session_state["reproducir"] = True

    with col2:
        if st.button("⏹️ PARAR AUDIO", use_container_width=True):
            st.session_state["reproducir"] = False

    if st.session_state.get("reproducir"):
        st.components.v1.html(
            f'''
            <audio autoplay controls style="width:100%;">
                <source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3">
            </audio>
            ''',
            height=50
        )

st.markdown("<br><hr><center><small>ReciboZen · 2026 · AutoModel Edition</small></center>", unsafe_allow_html=True)
