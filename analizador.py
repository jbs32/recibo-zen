import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time

# --- CONFIGURACIÓN DE SEGURIDAD ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "TU_CLAVE_AQUI"

genai.configure(api_key=API_KEY)

# --- SISTEMA DE FALLO SEGURO PARA MODELOS ---
@st.cache_resource
def conectar_con_ia():
    # Lista de nombres posibles para el mismo modelo en distintas versiones de API
    nombres_modelo = [
        'gemini-1.5-flash', 
        'models/gemini-1.5-flash', 
        'gemini-1.5-flash-latest',
        'models/gemini-pro'
    ]
    
    for nombre in nombres_modelo:
        try:
            m = genai.GenerativeModel(nombre)
            # Intentamos una micro-generación de prueba para validar el nombre
            m.generate_content("hola", generation_config={"max_output_tokens": 1})
            return m
        except:
            continue
    return None

model = conectar_con_ia()

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS DEFINITIVO (Botones Gemelos y Naranja) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    .report-card { 
        background-color: white !important; padding: 30px; border-radius: 20px; 
        border-top: 10px solid #27ae60; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    .stButton > button {
        width: 100% !important; height: 65px !important;
        border-radius: 15px !important; font-weight: bold !important;
        color: white !important; border: none !important;
    }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    
    /* Selector para el botón de PARAR (Naranja) */
    div[data-testid="column"]:nth-of-type(2) button { background-color: #e67e22 !important; }
    
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    [data-testid="stFileUploader"] section { background-color: white !important; border: 2px dashed #27ae60 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio(texto):
    tts = gTTS(text=texto, lang='es', slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con claridad y alegría")

if model is None:
    st.error("No se ha podido establecer conexión con los modelos de Google. Revisa tu API Key.")
else:
    uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")
    if uploaded_file:
        if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
            with st.spinner('Analizando con cariño...'):
                try:
                    time.sleep(1)
                    texto_raw = leer_pdf(uploaded_file)
                    prompt = f"""
                    Eres ReciboZen. Analiza esta factura. Separa con '---':
                    1. Informe detallado: Saludo, Total (€), Consumo (kWh), Potencia (kW), Impuestos y un Consejo.
                    2. Guion de voz alegre (máx 70 palabras) que empiece con '¡Hola, hola!'.
                    Factura: {texto_raw[:3500]}
                    """
                    response = model.generate_content(prompt).text
                    partes = response.split('---')
                    st.session_state['analisis'] = partes[0].strip()
                    st.session_state['audio_b64'] = preparar_audio(partes[1].strip() if len(partes) > 1 else partes[0])
                    st.session_state['reproducir'] = False
                except Exception as e:
                    st.error(f"Aviso técnico: {e}")

if 'analisis' in st.session_state:
    st.markdown(f"<div class='report-card'><h3>📋 Informe Zen</h3>{st.session_state['analisis']}</div>", unsafe_allow_html=True)
    st.write("### 🔊 Versión animada")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ INICIAR AUDIO", use_container_width=True):
            st.session_state['reproducir'] = True
    with col2:
        if st.button("⏹️ PARAR AUDIO", use_container_width=True):
            st.session_state['reproducir'] = False
    
    if st.session_state.get('reproducir'):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=0)

st.markdown("<br><hr><center><small>ReciboZen · 2026</small></center>", unsafe_allow_html=True)
