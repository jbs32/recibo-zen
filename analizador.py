import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time

# --- CONFIGURACIÓN SEGURA ---
# Intentamos leer la clave desde Secrets (para la web) o de una variable local
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "PEGA_AQUI_TU_CLAVE_SOLO_PARA_PRUEBAS_LOCALES"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS MEJORADO ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    .report-card { 
        background-color: white !important; padding: 30px; border-radius: 20px; 
        border-top: 10px solid #27ae60; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px; line-height: 1.6;
    }
    .stButton > button {
        width: 100% !important; height: 60px !important; border-radius: 15px !important;
        font-weight: bold !important; font-size: 16px !important; color: white !important; border: none !important;
    }
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    div.stop-btn > div.stButton > button { background-color: #e67e22 !important; }
    [data-testid="stFileUploader"] section { background-color: white !important; border: 2px dashed #27ae60 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio(texto_para_leer):
    tts = gTTS(text=texto_para_leer, lang='es', slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con cariño y alegría")

uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")

if uploaded_file:
    if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
        with st.spinner('ReciboZen está dándole vueltas a los números...'):
            try:
                texto_raw = leer_pdf(uploaded_file)
                prompt_informe = f"Eres ReciboZen. Analiza esta factura de energía de forma detallada pero con lenguaje muy cercano. Explica: 1. Total (€). 2. Consumo vs Potencia. 3. Impuestos explicados fácil. 4. Un consejo de ahorro. Texto: {texto_raw[:3500]}"
                res_informe = model.generate_content(prompt_informe).text
                
                prompt_voz = f"Basándote en este informe: {res_informe}, escribe un guion MUY alegre y desenfadado de máximo 80 palabras. Usa exclamaciones y frases divertidas como ¡Hola, hola! o ¡Menudo recibo tenemos aquí!."
                res_voz = model.generate_content(prompt_voz).text
                
                st.session_state['analisis'] = res_informe
                st.session_state['audio_b64'] = preparar_audio(res_voz)
                st.session_state['reproducir'] = False
            except Exception as e:
                st.error(f"Error de conexión: {e}")

if 'analisis' in st.session_state:
    st.markdown(f"<div class='report-card'><h3>📋 Tu Informe ReciboZen</h3>{st.session_state['analisis']}</div>", unsafe_allow_html=True)
    st.write("### 🔊 Escucha tu versión animada")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ INICIAR AUDIO", type="secondary"):
            st.session_state['reproducir'] = True
    with col2:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("⏹️ PARAR AUDIO", type="secondary"):
            st.session_state['reproducir'] = False
        st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.get('reproducir'):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=0)

st.markdown("<br><hr><center><small>ReciboZen · 2026 · Hecho con alegría ✨</small></center>", unsafe_allow_html=True)
