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

# Ajustamos el nombre al formato que requiere la API v1beta para evitar el 404
# Usamos el alias 'gemini-1.5-flash-latest' que es el más estable
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS (Simetría y Naranja Blindado) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    .report-card { 
        background-color: white !important; padding: 30px; border-radius: 20px; 
        border-top: 10px solid #27ae60; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px; line-height: 1.6;
    }
    .stButton > button {
        width: 100% !important; height: 65px !important;
        border-radius: 15px !important; font-weight: bold !important;
        font-size: 16px !important; color: white !important; border: none !important;
    }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    /* Selector preciso para el botón de Parar */
    div[data-testid="stHorizontalBlock"] div:nth-child(2) button {
        background-color: #e67e22 !important;
    }
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
st.write("### Tu factura explicada con cariño y claridad")

uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")

if uploaded_file:
    if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
        with st.spinner('ReciboZen está analizando...'):
            try:
                # Una pequeña pausa para evitar saturar la API
                time.sleep(1)
                texto_raw = leer_pdf(uploaded_file)
                
                prompt = f"""
                Eres ReciboZen. Analiza esta factura.
                Separa con '---' dos partes:
                1. Un informe muy detallado y visual para leer. Incluye: Saludo, Total a pagar (€), Consumo (kWh), Potencia (kW) e Impuestos. Termina con un consejo de ahorro.
                2. Un guion de voz MUY ALEGRE (máx 70 palabras) que empiece con '¡Hola, hola!'.
                Factura: {texto_raw[:3500]}
                """
                
                response = model.generate_content(prompt).text
                if "---" in response:
                    partes = response.split('---')
                    st.session_state['analisis'] = partes[0].strip()
                    st.session_state['audio_b64'] = preparar_audio(partes[1].strip())
                else:
                    st.session_state['analisis'] = response
                    st.session_state['audio_b64'] = preparar_audio(response[:150])
                
                st.session_state['reproducir'] = False
            except Exception as e:
                st.error(f"Error técnico: {e}")

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
