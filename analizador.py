import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time

# --- CONFIGURACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "TU_CLAVE_LOCAL"

genai.configure(api_key=API_KEY)

@st.cache_resource
def configurar_ia():
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in modelos:
            if "1.5-flash" in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel(modelos[0])
    except: return None

model = configurar_ia()

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS DEFINITIVO (Simetría y Colores) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    .report-card { 
        background-color: white !important; padding: 30px; border-radius: 20px; 
        border-top: 10px solid #27ae60; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px; line-height: 1.6;
    }
    /* Alineación de botones */
    .stButton > button {
        width: 100% !important; height: 65px !important;
        border-radius: 15px !important; font-weight: bold !important;
        font-size: 16px !important; color: white !important; border: none !important;
    }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    /* Botón de parar en naranja (el segundo de la fila) */
    div[data-testid="column"]:nth-child(2) button { background-color: #e67e22 !important; }
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    [data-testid="stFileUploader"] section { background-color: white !important; border: 2px dashed #27ae60 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio(texto):
    # Ya no quitamos comas ni puntos para que lea los decimales bien (47,03€)
    tts = gTTS(text=texto, lang='es', slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con cariño y claridad")

if model:
    uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")
    if uploaded_file:
        if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
            with st.spinner('Preparando tu Informe Zen...'):
                try:
                    texto_raw = leer_pdf(uploaded_file)
                    # VOLVEMOS AL PROMPT DETALLADO QUE FUNCIONABA
                    prompt = f"""
                    Eres ReciboZen, un experto amable. Analiza esta factura de energía.
                    Escribe un informe detallado con:
                    - Total a pagar (€)
                    - Consumo eléctrico (kWh) y Potencia contratada (kW)
                    - Desglose amigable de Impuestos (IVA e Impuesto Eléctrico)
                    - Un consejo personalizado de ahorro.
                    Usa un lenguaje muy humano y cercano.
                    ---
                    Después escribe un guion de voz MUY ALEGRE de unas 60 palabras que empiece con '¡Hola, hola!' para resumir esto de forma divertida.
                    Texto factura: {texto_raw[:3500]}
                    """
                    response = model.generate_content(prompt).text
                    partes = response.split('---')
                    
                    st.session_state['analisis'] = partes[0].strip()
                    st.session_state['audio_b64'] = preparar_audio(partes[1].strip() if len(partes) > 1 else partes[0])
                    st.session_state['reproducir'] = False
                except Exception as e:
                    st.error(f"Error: {e}")

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
