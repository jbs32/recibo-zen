import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time

# --- CONFIGURACIÓN DE SEGURIDAD ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_AQUI"

genai.configure(api_key=GOOGLE_API_KEY)

# Ajuste de nombre para máxima compatibilidad en la nube
model = genai.GenerativeModel('gemini-1.5-flash-001')

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS TOTAL (BLINDAJE CONTRA MODO OSCURO) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, span, div, label, .stMarkdown { color: #2c3e50 !important; }

    [data-testid="stFileUploader"] section {
        background-color: white !important;
        border: 2px dashed #27ae60 !important;
        color: #2c3e50 !important;
    }
    
    [data-testid="stFileUploaderSmallFileDropzone"], 
    [data-testid="stFileUploaderDropzone"] {
        background-color: white !important;
        color: #2c3e50 !important;
    }

    .report-card { 
        background-color: white !important; 
        padding: 30px; 
        border-radius: 20px; 
        border-top: 10px solid #27ae60; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        color: #2c3e50 !important;
    }

    .stButton>button { height: 65px; border-radius: 15px; font-weight: bold !important; color: white !important; }
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    div.row-widget.stButton.stop-btn > button { background-color: #e67e22 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio_base64(texto):
    tts = gTTS(text=texto.replace('*', '').replace('#', ''), lang='es')
    archivo_audio = io.BytesIO()
    tts.write_to_fp(archivo_audio)
    archivo_audio.seek(0)
    return base64.b64encode(archivo_audio.read()).decode()

st.title("🧘 ReciboZen")
st.write("### Su factura explicada con claridad y paz")

uploaded_file = st.file_uploader("Cargue su factura en PDF", type="pdf")

if uploaded_file:
    if st.button("🚀 ANALIZAR MI FACTURA", type="primary"):
        with st.spinner('ReciboZen está leyendo los datos...'):
            try:
                time.sleep(1)
                texto_factura = leer_pdf(uploaded_file)
                # El modelo 1.5 es excelente resumiendo
                prompt = f"Eres ReciboZen. Analiza esta factura de energía para una persona mayor. Indica Importe Total, Consumo y Potencia. Sé amable y directo. Texto: {texto_factura[:3500]}"
                response = model.generate_content(prompt)
                st.session_state['analisis'] = response.text
                st.session_state['audio_b64'] = preparar_audio_base64(response.text)
            except Exception as e:
                st.error(f"Aviso técnico: {e}")

if 'analisis' in st.session_state:
    st.markdown(f"<div class='report-card'><h3>📋 Informe ReciboZen</h3>{st.session_state['analisis']}</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔊 ESCUCHAR", type="secondary", use_container_width=True):
            st.session_state['reproducir'] = True
    with col2:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("⏹️ PARAR", type="secondary", use_container_width=True):
            st.session_state['reproducir'] = False
        st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.get('reproducir'):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=0)

st.markdown("<br><hr><center><small style='color: #7f8c8d !important;'>ReciboZen · 2026</small></center>", unsafe_allow_html=True)
