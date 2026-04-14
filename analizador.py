import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time
import re

# --- CONFIGURACIÓN ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "TU_CLAVE_LOCAL"

genai.configure(api_key=API_KEY)

@st.cache_resource
def configurar_ia():
    try:
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m_name in modelos_disponibles:
            if "1.5-flash" in m_name: return genai.GenerativeModel(m_name)
        return genai.GenerativeModel(modelos_disponibles[0])
    except: return None

model = configurar_ia()

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS RADICAL PARA ALINEACIÓN Y COLORES ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    
    .report-card { 
        background-color: white !important; padding: 30px; border-radius: 20px; 
        border-top: 10px solid #27ae60; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }

    /* Forzamos que la fila de columnas no tenga márgenes extraños */
    [data-testid="column"] {
        display: flex;
        align-items: flex-start;
    }

    .stButton > button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 15px !important;
        color: white !important;
        border: none !important;
        margin: 0 !important;
    }
    
    /* Botón Iniciar (Azul) */
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    
    /* Botón Parar (Naranja) - Ahora con selector de posición para evitar desalineación */
    div[data-testid="column"]:nth-child(2) button {
        background-color: #e67e22 !important;
    }

    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    [data-testid="stFileUploader"] section { background-color: white !important; border: 2px dashed #27ae60 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio_veloz(texto):
    # Truco para acelerar: eliminamos signos que causan pausas largas
    texto_veloz = texto.replace(',', '').replace('...', ' ').replace('\n', ' ')
    # Limpiamos emojis para que gTTS no intente leerlos
    texto_veloz = re.sub(r'[^\w\s!.?€]', '', texto_veloz)
    
    tts = gTTS(text=texto_veloz, lang='es', slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con alegría")

if model:
    uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")

    if uploaded_file:
        if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
            with st.spinner('Analizando...'):
                try:
                    time.sleep(0.5)
                    texto_raw = leer_pdf(uploaded_file)
                    prompt = f"""
                    Analiza esta factura. Separa con '---':
                    1. Informe visual para leer (Total, Consumo, Potencia, Impuestos).
                    2. Guion de voz MUY ALEGRE y ENÉRGICO (máx 60 palabras). Usa frases cortas. Sin muchas comas.
                    Factura: {texto_raw[:3000]}
                    """
                    response = model.generate_content(prompt).text
                    partes = response.split('---')
                    
                    st.session_state['analisis'] = partes[0].strip()
                    st.session_state['audio_b64'] = preparar_audio_veloz(partes[1].strip() if len(partes) > 1 else partes[0])
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
