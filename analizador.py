import streamlit as st
from google import genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "TU_NUEVA_CLAVE_AQUI"

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.5-flash"

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }

    .report-card {
        background-color: white !important; padding: 30px; border-radius: 20px;
        border-top: 10px solid #27ae60 !important; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px; line-height: 1.6;
    }

    .stButton > button {
        width: 100% !important; height: 65px !important;
        border-radius: 15px !important; font-weight: bold !important;
        font-size: 16px !important; color: white !important; border: none !important;
    }

    div[data-testid="column"]:nth-of-type(1) button { background-color: #3498db !important; }
    div[data-testid="column"]:nth-of-type(2) button { background-color: #e67e22 !important; }

    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    [data-testid="stFileUploader"] section {
        background-color: white !important;
        border: 2px dashed #27ae60 !important;
    }
    </style>
""", unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([(page.extract_text() or "") for page in reader.pages])

def preparar_audio(texto):
    tts = gTTS(text=texto, lang='es', slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con cariño y claridad")

uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")

if uploaded_file:
    if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
        with st.spinner("ReciboZen está analizando con el nuevo motor..."):
            try:
                texto_raw = leer_pdf(uploaded_file)

                prompt = f"""
Eres ReciboZen. Analiza esta factura. Separa la respuesta con '---'.

1. Informe detallado para leer, en español claro:
   - Total (€)
   - Consumo (kWh)
   - Potencia (kW)
   - Impuestos
   - Consejo útil

2. Guion de voz alegre, máximo 70 palabras, que empiece con '¡Hola, hola!'.

Factura:
{texto_raw[:3500]}
"""

                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=prompt
                )

                texto = response.text if response.text else "No se pudo generar respuesta."
                partes = texto.split("---", 1)

                analisis = partes[0].strip()
                guion = partes[1].strip() if len(partes) > 1 else analisis[:300]

                st.session_state["analisis"] = analisis
                st.session_state["audio_b64"] = preparar_audio(guion)
                st.session_state["reproducir"] = False

            except Exception as e:
                st.error(f"Error con el nuevo SDK: {e}")

if "analisis" in st.session_state:
    st.markdown(
        f"<div class='report-card'><h3>📋 Informe Zen</h3>{st.session_state['analisis']}</div>",
        unsafe_allow_html=True
    )

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
            f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>',
            height=0
        )

st.markdown("<br><hr><center><small>ReciboZen · 2026 · Versión SDK Pro</small></center>", unsafe_allow_html=True)
