import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64

# --- CONFIGURACIÓN DE SEGURIDAD ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_AQUI"

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS BLINDADO (FUERZA COLORES ZEN) ---
st.markdown("""
    <style>
    /* Forzamos el fondo claro en toda la app */
    .stApp {
        background-color: #f0f4f8 !important;
    }
    
    /* Forzamos que todos los textos sean oscuros y legibles */
    h1, h2, h3, p, span, div, label {
        color: #2c3e50 !important;
    }

    /* Tarjeta del Informe */
    .report-card { 
        background-color: #ffffff !important; 
        padding: 30px; 
        border-radius: 20px; 
        border-top: 10px solid #27ae60; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        color: #2c3e50 !important;
    }

    /* Botones - Ajuste de colores y visibilidad */
    .stButton>button { 
        width: 100%; height: 65px; border-radius: 15px; 
        font-weight: bold !important; font-size: 18px !important;
        border: none !important;
        color: white !important; /* Texto del botón siempre blanco */
    }

    /* Botón Analizar (Verde) */
    .stButton > button[kind="primary"] { 
        background-color: #27ae60 !important; 
    }

    /* Botón Escuchar (Azul) */
    .stButton > button[kind="secondary"] { 
        background-color: #3498db !important; 
    }

    /* Botón Parar (Naranja) */
    div.row-widget.stButton.stop-btn > button {
        background-color: #e67e22 !important;
    }

    /* Caja de subida de archivos */
    [data-testid="stFileUploader"] section {
        background-color: #ffffff !important;
        border: 2px dashed #27ae60 !important;
        border-radius: 15px !important;
    }
    
    /* Texto dentro de la caja de subida */
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] div {
        color: #2c3e50 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio_base64(texto):
    texto_limpio = texto.replace('*', '').replace('#', '')
    tts = gTTS(text=texto_limpio, lang='es', slow=False)
    archivo_audio = io.BytesIO()
    tts.write_to_fp(archivo_audio)
    archivo_audio.seek(0)
    return base64.b64encode(archivo_audio.read()).decode()

# --- INTERFAZ ---
st.title("🧘 ReciboZen")
st.write("### Su factura explicada con claridad y paz")

uploaded_file = st.file_uploader("Cargue su PDF aquí", type="pdf")

if uploaded_file is not None:
    if st.button("🚀 ANALIZAR MI FACTURA", type="primary"):
        with st.spinner('ReciboZen está analizando...'):
            try:
                texto_factura = leer_pdf(uploaded_file)
                prompt = f"Analiza esta factura de energía para una persona mayor. Tono amable. Indica Total (€), Consumo (kWh) y Potencia. Da consejos de ahorro. Texto: {texto_factura[:4000]}"
                response = model.generate_content(prompt)
                st.session_state['analisis'] = response.text
                st.session_state['audio_b64'] = preparar_audio_base64(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

    if 'analisis' in st.session_state:
        st.markdown(f"<div class='report-card'><h3>📋 Informe ReciboZen</h3>{st.session_state['analisis']}</div>", unsafe_allow_html=True)
        
        st.markdown("### **3. Escuchar la explicación**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔊 ESCUCHAR", type="secondary", use_container_width=True):
                st.session_state['reproducir'] = True
        with col2:
            st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
            if st.button("⏹️ PARAR", type="secondary", use_container_width=True):
                st.session_state['reproducir'] = False
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get('reproducir', False):
            audio_html = f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>'
            st.components.v1.html(audio_html, height=0)

st.markdown("<br><hr><center><small style='color: #7f8c8d !important;'>ReciboZen · 2026</small></center>", unsafe_allow_html=True)
